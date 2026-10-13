import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest


PROJECT = Path(__file__).resolve().parents[1]


class MetadataPreparationTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=PROJECT / ".tmp")
        self.addCleanup(self.work.cleanup)
        self.output = Path(self.work.name)

    def prepare(self, payload, url=None, stage="metadata", time_unit="milliseconds"):
        source_file = self.output / "fixture.jsonl.gz"
        source_file.write_bytes(payload)
        source = self.output / "source.json"
        source.write_text(json.dumps({
            "id": "fixture-" + stage,
            "dataset": "interface-fixture",
            "kind": "item_metadata" if stage == "metadata" else "user_reviews",
            "url": url or source_file.as_uri(),
            "documentation": "interface-fixture",
            "documented_fields": {
                "parent_asin": "str", "title": "str",
                "categories": "list", "description": "list",
            } if stage == "metadata" else {
                "parent_asin": "str", "asin": "str", "user_id": "str",
                "rating": "float", "title": "str", "text": "str",
                "timestamp": "int",
            },
            "time_unit": time_unit if stage == "reviews" else None,
        }), encoding="utf-8")
        arguments = ["--metadata-record", str(
            self.output / "records/sources/fixture-metadata.json"
        )] if stage == "reviews" else []
        run = subprocess.run(
            [sys.executable, str(PROJECT / "prepare_data.py"),
             "--stage", stage, "--source-manifest", str(source),
             "--output-root", str(self.output), *arguments],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8",
        )
        return run

    def serve(self, payload, status=200, length=None, truncated_chunks=False):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(handler):
                handler.send_response(status)
                if truncated_chunks:
                    handler.send_header("Transfer-Encoding", "chunked")
                else:
                    handler.send_header("Content-Length", str(
                        len(payload) if length is None else length))
                handler.end_headers()
                if truncated_chunks:
                    handler.wfile.write(f"{len(payload):x}\r\n".encode() + payload + b"\r\n")
                else:
                    handler.wfile.write(payload)

            def log_message(handler, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{server.server_port}/metadata.gz"

    def catalog(self, rows):
        metadata = self.prepare(gzip.compress(
            b"".join(json.dumps(row).encode() + b"\n" for row in rows), mtime=0,
        ))
        self.assertEqual(metadata.returncode, 0, metadata.stderr)
        return self.run_catalog()

    def run_catalog(self, config=None, previous=None):
        return subprocess.run(
            [sys.executable, str(PROJECT / "prepare_data.py"), "--stage", "catalog",
             "--metadata-record", str(self.output / "records/sources/fixture-metadata.json"),
             "--scope-config", str(config or PROJECT / "config/grain-A-v1.json"),
             "--output-root", str(self.output),
             *(["--previous-catalog-record", str(previous)] if previous else [])],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8",
        )

    def identity_catalog(self, rows):
        legacy = self.catalog(rows)
        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        version = json.loads(legacy.stdout)["scope_version"]
        return self.run_catalog(PROJECT / "config/grain-A-1.1.2.json",
                                previous=self.output / "records/catalog" / (version + ".json"))

    def test_identity_catalog_admits_explicit_grain_with_unknown_composition(self):
        run = self.identity_catalog([
            {"parent_asin": "RAW", "title": "Raw brown rice kernels", "rating_number": 0},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        products = [json.loads(line) for line in (self.output / report["catalog_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([(row["parent_asin"], row["composition_status"]) for row in products],
                         [("RAW", "not_disclosed")])

    def test_identity_catalog_title_negation_cannot_supply_identity(self):
        run = self.identity_catalog([
            {"parent_asin": "NO", "title": "No Raw Rice Grain"},
            {"parent_asin": "FREE", "title": "Wheat-free raw oat groats"},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["status"] for row in audit], ["pending", "included"])
        self.assertEqual(audit[0]["identity_evidence"], [])
        self.assertEqual(audit[0]["counter_evidence"], [{"field": "title", "text": "No Raw Rice Grain"}])

    def test_identity_catalog_checks_identity_conflicts_without_repeated_form_words(self):
        run = self.identity_catalog([
            {"parent_asin": "CONFLICT", "title": "Raw rice kernels", "description": ["This product is wheat."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual((audit[0]["status"], audit[0]["reason"]), ("pending", "field_identity_conflict"))
        self.assertIn({"field": "description[0]", "text": "This product is wheat."}, audit[0]["counter_evidence"])

    def test_identity_catalog_checks_direct_outside_crop_without_a_fixed_prefix(self):
        run = self.identity_catalog([
            {"parent_asin": "OUTSIDE", "title": "Raw rice grain", "description": ["The grain in this bag is quinoa."]},
            {"parent_asin": "USE", "title": "Raw rice grain", "description": ["Serve with quinoa."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["pending", "included"])
        self.assertIn({"field": "description[0]", "text": "The grain in this bag is quinoa."}, audit[0]["counter_evidence"])

    def test_identity_catalog_use_clause_cannot_hide_the_sold_mixture(self):
        run = self.identity_catalog([
            {"parent_asin": "MIX", "title": "Raw rice grain", "description": ["This grain blend contains rice and quinoa and is perfect for dinner."]},
            {"parent_asin": "RECIPE", "title": "Raw rice grain", "description": ["For this recipe, combine rice and quinoa for dinner."]},
            {"parent_asin": "TWO", "title": "Raw rice grain", "description": ["This grain blend contains rice and wheat and is ideal for dinner."]},
            {"parent_asin": "MAKING", "title": "Raw rice grain", "description": ["This grain blend contains rice and quinoa, making it perfect for dinner."]},
            {"parent_asin": "BAKING", "title": "Raw rice grain", "description": ["This product is wheat for baking."]},
            {"parent_asin": "USE_ONLY", "title": "Raw rice grain", "description": ["Our rice is perfect for a recipe with quinoa grain."]},
            {"parent_asin": "AFTER", "title": "Raw rice grain", "description": ["Perfect for dinner; this product is wheat."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["excluded", "included", "excluded", "excluded", "pending", "included", "pending"])
        self.assertIn({"field": "description[0]", "text": "This grain blend contains rice and quinoa and is perfect for dinner."}, audit[0]["counter_evidence"])

    def test_identity_catalog_title_flavor_is_not_undisclosed_plain_grain(self):
        run = self.identity_catalog([
            {"parent_asin": "FLAVOR", "title": "Whole Grain Oatmeal Apple Cinnamon"},
            {"parent_asin": "USE", "title": "Raw Rice Grain for Cinnamon Recipes"},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["status"] for row in audit], ["excluded", "included"])
        self.assertEqual(audit[0]["counter_evidence"], [{"field": "title", "text": "Whole Grain Oatmeal Apple Cinnamon"}])

    def test_identity_catalog_storage_directions_cannot_prove_sold_form(self):
        run = self.identity_catalog([
            {"parent_asin": "STORE", "title": "Arborio Rice", "description": ["Store in a cool, dry place."]},
            {"parent_asin": "DIRECT", "title": "Arborio Rice", "description": ["This product contains uncooked rice. Store in a cool, dry place."]},
            {"parent_asin": "STORE_SHORT", "title": "Arborio Rice", "description": ["Store dry."]},
            {"parent_asin": "KEEP_SHORT", "title": "Arborio Rice", "description": ["Keep dry."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["pending", "included", "pending", "pending"])
        self.assertEqual(audit[0]["form_evidence"], [])

    def test_identity_catalog_does_not_infer_form_from_category_or_ingredients(self):
        run = self.identity_catalog([
            {"parent_asin": "UNKNOWN_FORM", "title": "Arborio Rice", "categories": ["Dried Grains & Rice"],
             "details": {"Ingredients": "Rice", "Item Weight": "2.2 lb"}},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual((audit[0]["status"], audit[0]["reason"]), ("pending", "form_not_verified"))

    def test_identity_catalog_uses_direct_fields_without_fixed_prefix(self):
        run = self.identity_catalog([
            {"parent_asin": "DIRECT", "title": "Pantry Essentials", "features": ["Contains 17.6 oz of uncooked rice"]},
            {"parent_asin": "USE", "title": "Pantry Essentials", "description": ["Serve with raw barley groats."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        products = [json.loads(line) for line in (self.output / report["catalog_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["parent_asin"] for row in products], ["DIRECT"])
        self.assertEqual(products[0]["identity_evidence"][0]["field"], "features[0]")

    def test_identity_catalog_recognizes_the_sold_object_before_grain_words(self):
        rows = [
            {"parent_asin": "SAUCE", "title": "Kim Chee Fried Rice Sauce (pkg)"},
            {"parent_asin": "TRAY", "title": "Snappy Popcorn Trays", "description": ["Our popcorn is grown from whole grain corn."]},
            {"parent_asin": "HONEY", "title": "Local Hive from L.R Rice, Raw Honey", "features": ["100% honey"]},
            {"parent_asin": "STARTER", "title": "Wira Ragi Tempeh Starter"},
        ]
        run = self.identity_catalog(rows)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["status"] for row in audit], ["excluded"] * 4)
        self.assertEqual(audit[0]["counter_evidence"][0]["text"], "Kim Chee Fried Rice Sauce (pkg)")

    def test_identity_catalog_separates_marketing_percentages_from_composition(self):
        run = self.identity_catalog([
            {"parent_asin": "QUALITY", "title": "Raw brown rice kernels", "features": ["100% PREMIUM QUALITY - our short grain rice.", "100% SATISFACTION"]},
            {"parent_asin": "ORIGIN", "title": "Raw Arborio Rice", "features": ["100% Italian"]},
            {"parent_asin": "DECLARED", "title": "Raw brown rice kernels", "features": ["100% pure brown rice"]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([(r["status"], r["composition_status"]) for r in audit],
                         [("included", "not_disclosed"), ("included", "not_disclosed"), ("included", "declared_single_grain")])

    def test_identity_catalog_keeps_ingredient_continuations_but_not_cooking_directions(self):
        run = self.identity_catalog([
            {"parent_asin": "SALT", "title": "Raw rice kernels", "details": {"Ingredients": "Rice\nSalt"}},
            {"parent_asin": "COOK", "title": "Raw rice kernels", "features": ["Ingredients: Rice. Cooking instructions: Add salt and oil."]},
            {"parent_asin": "UNKNOWN", "title": "Raw rice kernels", "features": ["Ingredients: Rice. Unknown addition."]},
            {"parent_asin": "CONFLICT", "title": "Raw rice kernels", "features": ["Ingredients: Rice. Ingredients: Wheat."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([(r["status"], r["composition_status"]) for r in audit],
                         [("excluded", "declared_outside_scope"), ("included", "declared_single_grain"),
                          ("pending", "unresolved"), ("pending", "conflict")])

    def test_identity_catalog_resolves_known_names_without_collapsing_millet_species(self):
        run = self.identity_catalog([
            {"parent_asin": "COIX", "title": "Hato Mugi (Job’s Tears), Raw", "features": ["INGREDIENTS: HATO MUGI", "This is an ancient whole grain."]},
            {"parent_asin": "BARNYARD", "title": "Raw Barnyard Millet", "features": ["Ingredients: Pearled Raw Barnyard Millet"], "categories": ["Dried Grains & Rice", "Millet"]},
            {"parent_asin": "FONIO", "title": "Fonio Super-Grain", "features": ["Nothing else is added, just 100% pure organic fonio grain."], "categories": ["Dried Grains & Rice", "Millet"]},
            {"parent_asin": "MIX", "title": "Ragi and Bajra Whole Grain Combo", "details": {"Ingredients": "Ragi\nBajra"}},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([(r["status"], r["composition_status"]) for r in audit],
                         [("included", "declared_single_grain")] * 3 + [("excluded", "declared_outside_scope")])
        self.assertEqual([r["crop"] for r in audit[:3]], ["coix", "barnyard_millet", "fonio"])

    def test_identity_catalog_admits_dry_flakes_but_keeps_processing_counterevidence(self):
        run = self.identity_catalog([
            {"parent_asin": "FLAKES", "title": "TAJ Poha Flattened Rice Thick"},
            {"parent_asin": "FLOUR_CONFLICT", "title": "Rani Poha Flattened Rice", "features": ["PREMIUM Gourmet Food Grade Flour"]},
            {"parent_asin": "PRETREATED", "title": "Parboiled Medium Grain Rice"},
            {"parent_asin": "SEASONED", "title": "Masala Poha Flattened Rice"},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["included", "pending", "pending", "excluded"])
        self.assertEqual(audit[1]["counter_evidence"][0]["text"], "PREMIUM Gourmet Food Grade Flour")

    def test_identity_catalog_retains_real_counterevidence_but_ignores_context_roles(self):
        run = self.identity_catalog([
            {"parent_asin": "CONFLICT", "title": "Raw rice grain", "description": ["The grain in this bag is wheat."]},
            {"parent_asin": "FACILITY", "title": "Raw rice grain", "description": ["This product is processed in a facility with wheat. Serve with rye bread."]},
            {"parent_asin": "NEGATED", "title": "Raw rice grain", "description": ["This product is not raw rice grain."]},
            {"parent_asin": "FEED", "title": "Raw Pearl Millet Whole Grain", "features": ["Bird Seed and Feed"]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["pending", "included", "pending", "pending"])
        self.assertEqual(audit[0]["reason"], "field_identity_conflict")
        self.assertEqual(audit[2]["identity_evidence"], [{"field": "title", "text": "Raw rice grain"}])

    def test_identity_catalog_blocks_explicit_mixtures_and_partial_composition(self):
        run = self.identity_catalog([
            {"parent_asin": "MULTI", "title": "Rice and Wheat Whole Grain"},
            {"parent_asin": "ADDED", "title": "Whole Grain Oats Cup", "features": ["Made with oats, egg whites and blueberries."]},
            {"parent_asin": "PARTIAL", "title": "Raw oat groats", "features": ["Made with oats."]},
            {"parent_asin": "FLOUR", "title": "Rice Flour", "features": ["Ingredients: Rice. Unknown addition."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["excluded", "excluded", "pending", "excluded"])
        self.assertEqual(audit[1]["composition_status"], "declared_outside_scope")
        self.assertEqual(audit[2]["composition_status"], "unresolved")

    def test_identity_catalog_records_every_old_new_decision_and_preserves_old_artifacts(self):
        legacy = self.catalog([
            {"parent_asin": "NEW", "title": "Raw rice kernels"},
            {"parent_asin": "OUT", "title": "Coffee Beans"},
            {"parent_asin": "SALT", "title": "Raw rice kernels", "details": {"Ingredients": "Rice\nSalt"}},
        ])
        before = json.loads(legacy.stdout)
        previous = self.output / "records/catalog" / (before["scope_version"] + ".json")
        old_record_bytes = previous.read_bytes()
        old_audit_bytes = (self.output / before["audit_path"]).read_bytes()
        run = self.run_catalog(PROJECT / "config/grain-A-1.1.2.json", previous=previous)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        changes = [json.loads(line) for line in (self.output / report["migration_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([(r["parent_asin"], r["old"]["status"], r["new"]["status"]) for r in changes],
                         [("NEW", "pending", "included"), ("OUT", "excluded", "excluded"), ("SALT", "pending", "excluded")])
        self.assertEqual(changes[0]["new"]["composition_status"], "not_disclosed")
        self.assertEqual(report["migration_counts"], {"pending->included": 1, "excluded->excluded": 1, "pending->excluded": 1})
        self.assertEqual(previous.read_bytes(), old_record_bytes)
        self.assertEqual((self.output / before["audit_path"]).read_bytes(), old_audit_bytes)

    def test_identity_catalog_does_not_turn_brand_inventory_or_texture_into_counterevidence(self):
        run = self.identity_catalog([
            {"parent_asin": "BRAND", "title": "Quick Oats", "description": ["We pride ourselves on our ability to craft granola, snack bars, and oatmeal. Everyone should enjoy a satisfying meal."]},
            {"parent_asin": "TEXTURE", "title": "Long Grain Basmati Rice", "description": ["It is not sticky like other varieties of rice."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["included", "included"])

    def test_identity_catalog_does_not_hide_feed_counterevidence_inside_use_language(self):
        run = self.identity_catalog([
            {"parent_asin": "FEED", "title": "Raw Pearl Millet Whole Grain", "features": ["A blend of Nutrition & Flavor: Our bajra is Indian millet, known for its nutty flavor and high nutritional value.", "Bird Seed and Feed: Bajra is a popular bird seed and feed, making it an excellent choice for bird lovers."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual((audit[0]["status"], audit[0]["reason"]), ("pending", "field_food_use_conflict"))

    def test_identity_catalog_recognizes_explicit_partial_ingredient_information(self):
        run = self.identity_catalog([
            {"parent_asin": "CUP", "title": "Whole Grain Oats Cup", "description": ["We use core ingredients like egg whites, fruit, nuts and gluten-free oats in every cup."]},
            {"parent_asin": "SWEET", "title": "Crunchy Flax Cereal", "features": ["Sweetened with fruit juice and Honey"]},
            {"parent_asin": "PARTIAL", "title": "Raw rice kernels", "features": ["Our core ingredients like rice are carefully selected."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([(r["status"], r["composition_status"]) for r in audit],
                         [("excluded", "declared_outside_scope"), ("excluded", "declared_outside_scope"), ("pending", "unresolved")])

    def test_identity_catalog_keeps_real_category_conflict_for_condiment_objects(self):
        run = self.identity_catalog([
            {"parent_asin": "CONFLICT", "title": "Red Bean Seasoning", "categories": ["Rice Dishes", "Seasoned Rice"]},
            {"parent_asin": "TEA", "title": "Genmaicha Green Tea with Rice", "categories": ["Tea", "Matcha"]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["pending", "excluded"])
        self.assertTrue(any(r["text"] == "Seasoned Rice" for r in audit[0]["counter_evidence"]))

    def test_identity_catalog_distinguishes_canned_vegetables_from_container_material(self):
        run = self.identity_catalog([
            {"parent_asin": "VEG", "title": "Whole Kernel White Corn, 15 oz Cans", "description": ["This is canned vegetables."], "categories": ["Vegetables", "Corn"]},
            {"parent_asin": "RAW", "title": "Raw Corn Kernels", "details": {"Container": "Metal can"}},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["excluded", "included"])

    def test_identity_catalog_excludes_only_sold_millet_types_not_title_alternatives(self):
        run = self.identity_catalog([
            {"parent_asin": "PURE", "title": "Raw fonio grain, alternative to rice and quinoa"},
            {"parent_asin": "MIX", "title": "Hulled Millet | Foxtail, Kodo, Little, Barnyard, Proso | Alternative to Rice and Quinoa"},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["included", "excluded"])
        self.assertEqual(audit[0]["crop"], "fonio")
        self.assertEqual(audit[1]["reason"], "sold_multiple_grains")

    def test_identity_catalog_keeps_conflicting_same_crop_ingredient_declarations_pending(self):
        run = self.identity_catalog([
            {"parent_asin": "CONFLICT", "title": "Raw rice kernels", "features": ["Ingredients: Rice.", "Ingredients: Rice, Salt."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual((audit[0]["status"], audit[0]["composition_status"]), ("pending", "conflict"))

    def test_identity_catalog_partial_lists_are_not_conflicting_complete_formulas(self):
        run = self.identity_catalog([
            {"parent_asin": "PARTIAL", "title": "Whole Grain Oats", "features": ["Ingredients like oats, egg whites and nuts."], "description": ["Simple ingredients like oats, egg whites and almonds make breakfast easy."]},
            {"parent_asin": "CONFLICT", "title": "Raw rice grain", "details": {"Ingredients": "Rice"}, "features": ["Sweetened with honey."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([(r["status"], r["composition_status"]) for r in audit], [("excluded", "declared_outside_scope"), ("pending", "conflict")])

    def test_identity_catalog_free_of_ingredient_claim_is_not_an_added_flavor(self):
        run = self.identity_catalog([
            {"parent_asin": "FREE", "title": "Flattened Rice, Salt-Free"},
            {"parent_asin": "CONFLICT", "title": "Flattened Rice, Salt-Free", "features": ["Food Grade Flour"]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["included", "pending"])
        self.assertEqual(audit[0]["composition_status"], "not_disclosed")

    def test_identity_catalog_negative_ingredient_claim_does_not_add_that_ingredient(self):
        run = self.identity_catalog([
            {"parent_asin": "NO", "title": "Raw rice kernels", "features": ["Ingredients: Rice. No sugar."]},
            {"parent_asin": "SALT", "title": "Raw rice kernels", "features": ["Ingredients: Rice. Salt."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([(r["status"], r["composition_status"]) for r in audit], [("included", "declared_single_grain"), ("excluded", "declared_outside_scope")])

    def test_identity_catalog_not_only_statement_keeps_actual_added_ingredients(self):
        run = self.identity_catalog([
            {"parent_asin": "ADDED", "title": "Raw rice kernels", "features": ["Ingredients: Rice. Not only rice but salt."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual((audit[0]["status"], audit[0]["composition_status"]), ("excluded", "declared_outside_scope"))

    def test_identity_catalog_preserves_purpose_and_texture_without_false_conflicts(self):
        run = self.identity_catalog([
            {"parent_asin": "FONIO", "title": "Fonio Super-Grain", "features": ["VERSATILE & EASY TO USE: Cooks in 3 minutes - a great alterative rice, quinoa or couscous."], "categories": ["Dried Grains & Rice", "Millet"]},
            {"parent_asin": "TEXTURE", "title": "Short Grain Brown Rice", "features": ["Our glutinous, high starch brown rice is sure to result in a soft and chewy texture that is perfect for foods like risotto."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["included", "included"])
        self.assertTrue(all(r["context_evidence"] for r in audit))

    def test_identity_catalog_rebuilds_counterevidence_by_clause_not_whole_field(self):
        run = self.identity_catalog([
            {"parent_asin": "USE", "title": "Raw rice grain", "description": ["This product is raw rice grain. Serve with wheat bread."]},
            {"parent_asin": "CONFLICT", "title": "Raw rice grain", "description": ["This product is raw rice flour. Serve with wheat bread."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["included", "pending"])
        self.assertEqual(audit[0]["counter_evidence"], [])

    def test_identity_catalog_brand_inventory_and_free_from_lists_cannot_supply_identity(self):
        run = self.identity_catalog([
            {"parent_asin": "BRAND", "title": "Raw Golden Flax Seeds", "features": ["Shop our other trusted categories: Grains, Flours, Oats and Chocolates."]},
            {"parent_asin": "FREE", "title": "Gluten-Free Pretzel Twists", "features": ["Our grain free snacks are also free from dairy, sesame, egg, soy, corn and sugar."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertTrue(all(r["status"] != "included" for r in audit))
        self.assertTrue(all(not r["identity_evidence"] for r in audit))

    def test_identity_catalog_keeps_head_ambiguity_and_category_conflict_after_field_identity(self):
        run = self.identity_catalog([
            {"parent_asin": "BLEND", "title": "8 Blended Whole Grain Rice"},
            {"parent_asin": "CONFLICT", "title": "Pantry Essentials", "description": ["White corn kernels"], "categories": ["Vegetables", "Corn"]},
            {"parent_asin": "UNPOPPED", "title": "Pantry Essentials", "description": ["White corn kernels"], "categories": ["Snack Foods", "Popcorn", "Unpopped"]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["pending", "pending", "included"])

    def test_identity_catalog_direct_additions_and_water_canning_block_plain_grain(self):
        run = self.identity_catalog([
            {"parent_asin": "ADDED", "title": "Butternut Squash Risotto", "description": ["We blend premium short grain Arborio rice with squash, savory herbs and spices."]},
            {"parent_asin": "WATER", "title": "Corn kernels", "features": ["White corn kernels; Canned in water"]},
            {"parent_asin": "CAN", "title": "Raw corn kernels in metal can"},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["excluded", "excluded", "included"])

    def test_identity_catalog_later_ambiguous_description_cannot_erase_explicit_outside_form(self):
        run = self.identity_catalog([
            {"parent_asin": "CAN", "title": "Whole Kernel White Corn", "description": ["Canned vegetables. Delicately flavored corn varieties."], "categories": ["Vegetables", "Corn"]},
            {"parent_asin": "REVERSED", "title": "Whole Kernel White Corn", "description": ["Delicately flavored corn varieties. Canned vegetables."], "categories": ["Vegetables", "Corn"]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["excluded", "excluded"])

    def test_identity_catalog_inline_ingredients_are_not_hidden_by_prose(self):
        run = self.identity_catalog([
            {"parent_asin": "INLINE", "title": "Mini Wafers", "description": ["Pack of 8. A premium product, Ingredients: Sugar, wheat fiber milled, butter and vanilla."]},
            {"parent_asin": "RECIPE", "title": "Raw rice grain", "description": ["Recipe ingredients: Salt and wheat."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["excluded", "included"])

    def test_identity_catalog_style_climate_and_processed_heads_do_not_prove_grain_form(self):
        run = self.identity_catalog([
            {"parent_asin": "STYLE", "title": "Old Fashioned Sweet Sorghum", "categories": ["Syrups"]},
            {"parent_asin": "CLIMATE", "title": "Foxtail Millet", "description": ["This annual grain grows in dry climates."]},
            {"parent_asin": "MALT", "title": "Whole Grain Malted Barley"},
            {"parent_asin": "SPAWN", "title": "King Oyster Mushroom Grain Spawn", "description": ["Our grain spawn is grown on organic rye berries."]},
            {"parent_asin": "MEAL", "title": "Triticale Cereal/Meal", "features": ["100% Whole Grain"]},
            {"parent_asin": "OATS", "title": "Old-Fashioned Oats"},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["pending", "pending", "pending", "excluded", "excluded", "included"])

    def test_identity_catalog_checks_all_field_counterevidence_after_collecting_identity(self):
        run = self.identity_catalog([
            {"parent_asin": "PARBOILED", "title": "Pantry Essentials", "features": ["Parboiled rice grain."]},
            {"parent_asin": "MALT", "title": "Raw barley grain", "features": ["Malted barley grain."]},
            {"parent_asin": "FEED", "title": "Pantry Essentials", "features": ["Bird seed and feed."], "description": ["Raw pearl millet grain."]},
            {"parent_asin": "WATER", "title": "Pantry Essentials", "features": ["Canned in water"], "description": ["White corn kernels"]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([r["status"] for r in audit], ["pending", "pending", "pending", "excluded"])
        self.assertTrue(all(r["counter_evidence"] for r in audit))

    def test_extract_reuses_identity_catalog_and_keeps_raw_low_empty_and_zero(self):
        catalog = self.identity_catalog([
            {"parent_asin": "RAW", "title": "Raw rice kernels"},
            {"parent_asin": "ZERO", "title": "Raw oat groats"},
            {"parent_asin": "OTHER", "title": "Rice Sauce"},
        ])
        self.assertEqual(catalog.returncode, 0, catalog.stderr)
        report = json.loads(catalog.stdout)
        first = b'{"parent_asin":"RAW", "asin":"V1","user_id":"U1","rating":1,"text":"","timestamp":1609459200000}\n'
        other = b'{"parent_asin":"OTHER","asin":"RAW","user_id":"U2","rating":5,"text":"outside","timestamp":1609459200001}\n'
        last = b'{"parent_asin":"RAW","asin":"V3","user_id":"U3","rating":5,"text":"fresh","timestamp":1609459200002}\n'
        self.prepare(gzip.compress(first + other + last, mtime=0), stage="reviews")
        run = subprocess.run(
            [sys.executable, str(PROJECT / "prepare_data.py"), "--stage", "review_extract",
             "--catalog-record", str(self.output / "records/catalog" / (report["scope_version"] + ".json")),
             "--review-record", str(self.output / "records/sources/fixture-reviews.json"),
             "--output-root", str(self.output)], cwd=PROJECT, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        extracted = json.loads(run.stdout)
        self.assertEqual((self.output / extracted["extract_path"]).read_bytes(), first + last)
        self.assertEqual(extracted["product_review_counts"], {"RAW": 2, "ZERO": 0})
        self.assertEqual(extracted["raw"]["unique_accounts"], 2)
        self.assertEqual(extracted["formal_clean_status"], "not_built")

    def extract(self, body, parents=("A", "B", "ZERO")):
        catalog = self.catalog([
            {"parent_asin": parent, "title": "Rice", "features": ["Ingredients: Rice"]}
            for parent in parents
        ])
        self.assertEqual(catalog.returncode, 0, catalog.stderr)
        self.prepare(gzip.compress(body, mtime=0), stage="reviews")
        return self.run_extract()

    def run_extract(self):
        version = json.loads((PROJECT / "config/grain-A-v1.json").read_text("utf-8"))["version"]
        return subprocess.run(
            [sys.executable, str(PROJECT / "prepare_data.py"), "--stage", "review_extract",
             "--catalog-record", str(self.output / "records/catalog" / (version + ".json")),
             "--review-record", str(self.output / "records/sources/fixture-reviews.json"),
             "--output-root", str(self.output)],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8",
        )

    def test_extract_keeps_all_parent_reviews_original_bytes_and_zero_products(self):
        first = b'{"parent_asin":"A", "asin":"VARIANT", "user_id":"U1","rating":1,"text":"","timestamp":1609459200000}\n'
        unrelated = b'{"parent_asin":"OTHER","asin":"A","user_id":"U2","rating":5,"text":"outside","timestamp":1609459200001}\n'
        last = b'{"parent_asin":"B","asin":"V2","user_id":"U3","rating":5,"text":" untouched ","timestamp":1609459200002}\n'
        run = self.extract(first + unrelated + last)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report["status"], "extraction_complete")
        self.assertEqual(report["scan"]["lines"], 3)
        self.assertTrue(report["scan"]["gzip_verified"])
        self.assertEqual((self.output / report["extract_path"]).read_bytes(), first + last)
        self.assertEqual(report["product_review_counts"], {"A": 1, "B": 1, "ZERO": 0})
        refs = [json.loads(line) for line in (self.output / report["references_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["source_line"] for row in refs], [1, 3])
        self.assertEqual(report["formal_clean_status"], "not_built")

    def test_extract_reports_duplicates_and_fact_conflicts_without_resolving_them(self):
        row = {"parent_asin": "A", "asin": "V", "user_id": "U", "rating": 1, "title": "", "text": "same", "timestamp": 1609459200000}
        conflict = {**row, "rating": 5}
        ungroupable = {"parent_asin": "B", "rating": 5, "text": "missing key"}
        body = b"".join(json.dumps(value).encode() + b"\n" for value in (row, row, conflict, ungroupable))
        run = self.extract(body)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual((self.output / report["extract_path"]).read_bytes(), body)
        self.assertEqual(report["raw"]["unique_accounts"], 1)
        self.assertEqual(report["duplicates"]["exact_object_excess_rows"], 1)
        self.assertEqual(report["duplicates"]["raw_quad"], {
            "duplicate_groups": 1, "duplicate_member_rows": 3, "duplicate_excess_rows": 2,
            "conflict_groups": 1, "conflict_member_rows": 3, "ungroupable_rows": 1,
        })
        groups = [json.loads(line) for line in (self.output / report["groups_path"]).read_text("utf-8").splitlines()]
        self.assertEqual(groups[0]["source_lines"], [1, 2, 3])
        self.assertEqual(groups[0]["conflicting_fields"], ["rating"])
        self.assertEqual(report["cleaning_status"], "rules_not_approved")

    def test_extract_diagnoses_nfc_and_edge_space_only_as_unapproved_candidate(self):
        row = {"parent_asin": "A", "asin": "V", "user_id": "U", "rating": 5, "text": " café ", "timestamp": 1609459200000}
        body = b"".join(json.dumps(value, ensure_ascii=False).encode() + b"\n" for value in (row, {**row, "text": "cafe\u0301"}))
        run = self.extract(body)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report["duplicates"]["raw_quad"]["duplicate_groups"], 0)
        self.assertEqual(report["duplicates"]["nfc_strip_quad"]["duplicate_groups"], 1)
        self.assertEqual(report["duplicates"]["nfc_strip_quad"]["conflict_groups"], 0)
        self.assertEqual(report["candidate_normalization"]["approval"], "not_approved")
        self.assertEqual(report["candidate_normalization"]["changed_text_rows"], 2)
        self.assertEqual((self.output / report["extract_path"]).read_bytes(), body)

    def test_extract_reaches_end_but_blocks_completeness_for_unknown_bad_source_rows(self):
        first = b'{"parent_asin":"A","text":"first"}\n'
        last = b'{"parent_asin":"B","text":"last"}\n'
        run = self.extract(first + b'{broken\n[]\n{"asin":"A"}\n{"parent_asin":"OTHER"}\n' + last)
        self.assertNotEqual(run.returncode, 0)
        report = json.loads(run.stdout)
        self.assertEqual(report["status"], "extraction_incomplete")
        self.assertTrue(report["scan"]["gzip_verified"])
        self.assertEqual((report["scan"]["lines"], report["scan"]["records"], report["scan"]["matched_rows"]), (6, 4, 2))
        self.assertEqual((report["scan"]["invalid_json_rows"], report["scan"]["non_object_rows"], report["scan"]["invalid_parent_rows"]), (1, 1, 1))
        self.assertEqual((self.output / report["extract_path"]).read_bytes(), first + last)
        errors = [json.loads(line) for line in (self.output / report["errors_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["source_line"] for row in errors], [2, 3, 4])

    def test_extract_reports_single_and_combined_cleaning_losses_without_clean_output(self):
        row = {"parent_asin": "A", "asin": "V", "user_id": "U1", "rating": 5, "text": "ok", "timestamp": 1609459200000}
        values = [row, row, {**row, "parent_asin": "B", "user_id": "U2", "rating": 1, "text": ""},
                  {**row, "parent_asin": "B", "user_id": "U3", "rating": 0, "timestamp": "1609459200000"},
                  {"parent_asin": "B", "rating": 5, "text": "ok", "timestamp": 1609459200002}]
        run = self.extract(b"".join(json.dumps(value).encode() + b"\n" for value in values))
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report["quality"]["invalid_time_rows"], 1)
        self.assertEqual(report["quality"]["invalid_rating_rows"], 1)
        self.assertEqual(report["quality"]["empty_text_rows"], 1)
        self.assertEqual(report["quality"]["fields"]["user_id"]["missing"], 1)
        separate = report["candidate_cleaning"]["scenarios"]
        self.assertEqual(separate["nonblank_text"]["lost_reviews"], 1)
        self.assertEqual(separate["nonblank_text"]["lost_accounts"], 1)
        self.assertEqual(separate["valid_rating"]["lost_reviews"], 1)
        self.assertEqual(separate["valid_time"]["lost_reviews"], 1)
        self.assertEqual(separate["exact_object_dedup"]["lost_reviews"], 1)
        self.assertEqual(separate["combined_raw"]["kept_reviews"], 1)
        self.assertEqual(separate["combined_raw"]["lost_products_with_reviews"], 1)
        self.assertEqual(separate["combined_raw"]["lost_accounts"], 2)
        self.assertEqual(separate["combined_raw"]["catalog_products_retained"], 3)
        self.assertEqual(report["candidate_cleaning"]["approval"], "not_approved")
        self.assertEqual(report["raw"]["reviews"], 5)
        self.assertEqual(report["formal_clean_status"], "not_built")

    def test_extract_history_uses_strict_time_all_seen_interactions_and_accounts(self):
        template = {"asin": "V", "rating": 1, "text": "", "timestamp": 1}
        values = [
            {**template, "parent_asin": "A", "user_id": "U1"},
            {**template, "parent_asin": "B", "user_id": "U1", "timestamp": 2},
            {**template, "parent_asin": "A", "user_id": "U2"},
            {**template, "parent_asin": "A", "user_id": "U2", "timestamp": 2},
            {**template, "parent_asin": "A", "user_id": "U3", "timestamp": 3},
            {**template, "parent_asin": "B", "user_id": "U3", "timestamp": 3},
            {**template, "parent_asin": "A", "user_id": "U4", "timestamp": None},
            {**template, "parent_asin": "B", "user_id": "U4", "timestamp": 5},
        ]
        run = self.extract(b"".join(json.dumps(row).encode() + b"\n" for row in values))
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        history = report["history"]
        self.assertEqual(history["reviews_per_account"], {"2": 4})
        self.assertEqual(history["distinct_products_per_account"], {"1": 1, "2": 3})
        self.assertEqual(history["strict_prior_reviews"], {"0": 2, "1": 2})
        self.assertEqual(history["strict_prior_products"], {"0": 2, "1": 2})
        self.assertEqual(history["latest_unseen_products"], {"0": 1, "1": 2, "2": 1})
        self.assertEqual(history["multiple_latest_parent_accounts"], 1)
        self.assertEqual(history["accounts_with_invalid_time"], 1)
        self.assertEqual(history["unique_latest_unseen_accounts_with_known_time"], 1)
        self.assertEqual(report["sample_sufficiency"], "not_determined")
        self.assertEqual(report["model_input_status"], "not_released")

    def test_extract_positive_candidate_never_searches_back_or_ignores_seen_ties_conflicts(self):
        template = {"asin": "V", "rating": 5, "text": "ok", "timestamp": 1}
        values = []
        for user in ("U1", "U2", "U3", "U5", "U6", "U7"):
            values.append({**template, "parent_asin": "A", "user_id": user,
                           "timestamp": None if user == "U6" else 1,
                           "rating": 1 if user in ("U2", "U7") else 5,
                           "text": "" if user in ("U2", "U7") else "ok"})
            values.append({**template, "parent_asin": "A" if user == "U2" else "B", "user_id": user,
                           "timestamp": 2, "rating": 1 if user == "U1" else 5})
        values.extend([{**template, "parent_asin": parent, "user_id": "U4", "timestamp": 2} for parent in ("A", "B")])
        values.append({**template, "parent_asin": "B", "user_id": "U5", "timestamp": 2, "rating": 1})
        run = self.extract(b"".join(json.dumps(row).encode() + b"\n" for row in values))
        self.assertEqual(run.returncode, 0, run.stderr)
        candidate = json.loads(run.stdout)["history"]["manuscript_positive_candidate"]
        self.assertEqual(candidate["approval"], "not_approved")
        self.assertEqual(candidate["rating_min"], 4)
        self.assertEqual(candidate["potential_accounts"], 2)
        self.assertEqual(candidate["prior_positive_products"], {"0": 1, "1": 1})
        self.assertEqual(candidate["excluded_reasons"], {
            "latest_not_positive": 1, "latest_seen_product": 1, "multiple_latest_parents": 1,
            "latest_fact_conflict": 1, "unreliable_time": 1,
        })
        self.assertIsNone(candidate["minimum_prior_products"])

    def test_extract_requires_verified_same_sources_and_reproduces_stable_artifacts(self):
        body = b'{"parent_asin":"A","asin":"V","user_id":"U","rating":5,"text":"ok","timestamp":1609459200000}\n'
        first = self.extract(body)
        self.assertEqual(first.returncode, 0, first.stderr)
        report = json.loads(first.stdout)
        repeated = json.loads(self.run_extract().stdout)
        for name in ("extract", "references", "groups", "errors", "cleaning", "history"):
            self.assertEqual(repeated[name + "_sha256"], report[name + "_sha256"])
        version = report["scope_version"]
        catalog_file = self.output / "records/catalog" / (version + ".json")
        source_file = self.output / "records/sources/fixture-reviews.json"
        catalog = json.loads(catalog_file.read_text("utf-8"))
        source = json.loads(source_file.read_text("utf-8"))
        changes = [
            (catalog_file, {**catalog, "status": "rejected_pre_release"}, "catalog"),
            (source_file, {**source, "time": {**source["time"], "unit": "seconds"}}, "milliseconds"),
            (source_file, {**source, "scan": {**source["scan"], "lines": 2}}, "count"),
            (source_file, {**source, "association": {**source["association"], "metadata_source_sha256": "wrong"}}, "metadata"),
        ]
        for path, changed, expected in changes:
            original = path.read_bytes()
            with self.subTest(expected=expected):
                path.write_text(json.dumps(changed), "utf-8")
                run = self.run_extract()
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected, json.loads(run.stdout)["error"]["message"])
            path.write_bytes(original)

        for key, relative in (("catalog", catalog["catalog_path"]), ("reviews", source["raw_path"])):
            path = self.output / relative
            original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with self.subTest(tampered=key):
                run = self.run_extract()
                self.assertNotEqual(run.returncode, 0)
                self.assertIn("checksum", json.loads(run.stdout)["error"]["message"])
            path.write_bytes(original)

    def test_extract_equal_time_product_conflicts_do_not_inflate_positive_history(self):
        base = {"parent_asin": "A", "asin": "V", "user_id": "U", "rating": 5, "text": "liked", "timestamp": 1}
        values = [base, {**base, "rating": 1, "text": "disliked"}, {**base, "parent_asin": "B", "timestamp": 2}]
        run = self.extract(b"".join(json.dumps(row).encode() + b"\n" for row in values))
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report["duplicates"]["raw_quad"]["conflict_groups"], 0)
        self.assertEqual(report["duplicates"]["same_product_equal_time"]["conflict_groups"], 1)
        self.assertEqual(report["history"]["manuscript_positive_candidate"]["prior_positive_products"], {"0": 1})
        self.assertEqual(report["candidate_cleaning"]["scenarios"]["equal_time_conflict_quarantine"]["lost_reviews"], 2)

    def test_extract_time_diagnosis_preserves_invalid_values_and_does_not_apply_cutoff(self):
        base = {"parent_asin": "A", "asin": "V", "user_id": "U", "rating": 5, "text": "ok"}
        values = [{**base, "timestamp": value} for value in (1609459200123, 1609459200000, 10**30)]
        body = b"".join(json.dumps(row).encode() + b"\n" for row in values)
        run = self.extract(body)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual((self.output / report["extract_path"]).read_bytes(), body)
        self.assertEqual(report["time"]["min_raw"], 1609459200000)
        self.assertEqual(report["time"]["max_raw"], 1609459200123)
        self.assertEqual(report["time"]["max_utc"], "2021-01-01T00:00:00.123+00:00")
        self.assertEqual(report["time"]["valid_rows"], 2)
        self.assertEqual(report["quality"]["invalid_time_reasons"], {"unrepresentable": 1})
        self.assertEqual(report["time"]["cutoff_approval"], "not_approved")
        self.assertIsNone(report["time"]["cutoff"])

    def test_catalog_uses_identity_and_composition_and_includes_last_product(self):
        run = self.catalog([
            {"parent_asin": "COFFEE", "title": "Coffee"},
            {"parent_asin": "LAST", "title": "Brown Rice", "categories": ["Dried Grains & Rice"],
             "features": ["Ingredients: Brown rice"], "rating_number": 0},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        products = [json.loads(line) for line in (self.output / report["catalog_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([item["parent_asin"] for item in products], ["LAST"])
        self.assertEqual(products[0]["source_lines"], [2])
        self.assertEqual(products[0]["composition_evidence"][0]["text"], "Ingredients: Brown rice")
        self.assertEqual(report["counts"], {"included": 1, "excluded": 1, "pending": 0})

    def test_catalog_keeps_missing_or_incomplete_composition_pending(self):
        run = self.catalog([
            {"parent_asin": "TITLE_ONLY", "title": "Brown Rice"},
            {"parent_asin": "UNKNOWN_ADDITION", "title": "White Rice",
             "features": ["Ingredients: Rice, vitamin blend"]},
            {"parent_asin": "WEAK", "title": "Healthy Pantry",
             "description": ["A good companion for rice dishes."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report["counts"], {"included": 0, "excluded": 0, "pending": 3})
        decisions = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([item["reason"] for item in decisions],
                         ["missing_composition", "unresolved_composition", "weak_identity"])
        self.assertEqual(len((self.output / report["pending_path"]).read_text("utf-8").splitlines()), 3)

    def test_catalog_distinguishes_sold_food_from_free_claims_and_recipe_words(self):
        cases = [
            ("SNACK", "Rice Krispies Treats", "Ingredients: Rice", "excluded"),
            ("FLOUR", "Rice Flour", "Ingredients: Rice", "excluded"),
            ("SEED", "Wheat Grain Seeds for planting", "Ingredients: Wheat", "excluded"),
            ("PSEUDO", "Organic Quinoa", "May contain wheat", "excluded"),
            ("OATS", "Wheat-free Rolled Oats", "Ingredients: Organic oats", "included"),
            ("RECIPE", "Wheat Berries for bread recipes", "Ingredients: Wheat", "included"),
        ]
        run = self.catalog([{"parent_asin": parent, "title": title, "features": [feature]}
                            for parent, title, feature, _ in cases])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([(row["parent_asin"], row["status"]) for row in audit],
                         [(parent, status) for parent, _, _, status in cases])

    def test_catalog_quarantines_identity_form_and_processing_conflicts(self):
        run = self.catalog([
            {"parent_asin": "CATEGORY", "title": "Brown Teff Grain", "features": ["Ingredients: Teff"],
             "categories": ["Dried Grains & Rice", "Buckwheat"]},
            {"parent_asin": "FORM", "title": "Barley Flakes", "features": ["Ingredients: Barley"],
             "categories": ["Flours & Meals"]},
            {"parent_asin": "BLEND", "title": "Rice Blend", "features": ["Ingredients: Rice"]},
            {"parent_asin": "FORTIFIED", "title": "Enriched White Rice", "features": ["Ingredients: Rice"]},
            {"parent_asin": "DISAGREE", "title": "Wheat Berries", "features": ["Ingredients: Rice"]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report["counts"], {"included": 0, "excluded": 0, "pending": 5})
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual(audit[0]["reason"], "category_identity_conflict")
        self.assertEqual(audit[0]["counter_evidence"], [{"field": "categories[1]", "text": "Buckwheat"}])
        self.assertEqual(audit[1]["reason"], "category_form_conflict")

    def test_catalog_merges_exact_duplicates_and_quarantines_late_parent_conflict(self):
        first = {"parent_asin": "EXACT", "title": "Rice", "features": ["Ingredients: Rice"]}
        run = self.catalog([first, first,
            {"parent_asin": "CONFLICT", "title": "Rice", "features": ["Ingredients: Rice"]},
            {"parent_asin": "CONFLICT", "title": "Wheat Berries", "features": ["Ingredients: Wheat"]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report["counts"], {"included": 1, "excluded": 0, "pending": 1})
        catalog = [json.loads(line) for line in (self.output / report["catalog_path"]).read_text("utf-8").splitlines()]
        self.assertEqual(catalog[0]["source_lines"], [1, 2])
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["source_line"] for row in audit], [1, 2, 3, 4])
        self.assertEqual([row["reason"] for row in audit[2:]], ["parent_metadata_conflict"] * 2)
        self.assertEqual([row["source_lines"] for row in audit[2:]], [[3, 4], [3, 4]])
        self.assertEqual(report["scan"], {"rows": 4, "unique_parents": 2, "gzip_verified": True,
                                         "duplicate_parent_rows": 2, "conflicting_parents": 1})

    def test_catalog_rejects_unverified_or_tampered_metadata(self):
        acquired = self.prepare(gzip.compress(b'{"parent_asin":"R","title":"Rice"}\n', mtime=0))
        original = json.loads(acquired.stdout)
        path = self.output / original["record_path"]
        for fault in ("status", "gzip", "checksum", "row_count"):
            with self.subTest(fault=fault):
                record = json.loads(acquired.stdout)
                if fault == "status":
                    record["status"] = "source_incomplete"
                elif fault == "gzip":
                    record["scan"]["gzip_verified"] = False
                elif fault == "checksum":
                    record["download"]["sha256"] = "0" * 64
                else:
                    record["scan"]["lines"] = 2
                path.write_text(json.dumps(record), "utf-8")
                run = self.run_catalog()
                self.assertNotEqual(run.returncode, 0, run.stdout)
                self.assertEqual(json.loads(run.stdout)["status"], "catalog_incomplete")
                version = json.loads((PROJECT / "config/grain-A-v1.json").read_text("utf-8"))["version"]
                self.assertFalse((self.output / "records/catalog" / (version + ".json")).exists())

    def test_catalog_reproduces_digest_and_rejects_rule_change_under_same_version(self):
        run = self.catalog([{"parent_asin": "R", "title": "Rice", "features": ["Ingredients: Rice"]}])
        self.assertEqual(run.returncode, 0, run.stderr)
        first = json.loads(run.stdout)
        repeated = self.run_catalog()
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(json.loads(repeated.stdout)["catalog_sha256"], first["catalog_sha256"])
        altered = json.loads((PROJECT / "config/grain-A-v1.json").read_text("utf-8"))
        altered["forms"].append("new research form")
        config = self.output / "changed-config.json"
        config.write_text(json.dumps(altered), "utf-8")
        rejected = self.run_catalog(config)
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
        retained = json.loads((self.output / "records/catalog" / (first["scope_version"] + ".json")).read_text("utf-8"))
        self.assertEqual(retained["scope_sha256"], first["scope_sha256"])
        self.assertEqual(retained["catalog_sha256"], first["catalog_sha256"])

    def test_catalog_uses_affirmative_identity_and_complete_composition_across_fields(self):
        run = self.catalog([
            {"parent_asin": "DESCRIPTION", "title": "Pantry Essentials",
             "description": ["This product is barley groats.", "Ingredients: Barley"]},
            {"parent_asin": "DETAILS", "title": "Wheat Berries", "details": {"Ingredients": "Whole wheat"}},
            {"parent_asin": "PERCENT", "title": "Brown Rice", "features": ["100% Organic brown rice"]},
            {"parent_asin": "CATEGORY_ONLY", "title": "Pantry Essentials", "categories": ["Dried Grains & Rice"]},
            {"parent_asin": "MIXED", "title": "Rice and Wheat Grain", "features": ["Ingredients: Rice, wheat"]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["status"] for row in audit], ["included", "included", "pending", "pending", "excluded"])
        self.assertEqual(audit[0]["identity_evidence"][0]["field"], "description[0]")
        self.assertEqual(audit[4]["reason"], "mixed_composition")

    def test_catalog_requires_form_and_retains_counterevidence_outside_title(self):
        run = self.catalog([
            {"parent_asin": "CATEGORY", "title": "Rice", "features": ["Ingredients: Rice"],
             "categories": ["Breads & Bakery"]},
            {"parent_asin": "FORM_UNKNOWN", "title": "Sorghum Food", "features": ["Ingredients: Sorghum"]},
            {"parent_asin": "RAW_CORN", "title": "Corn Kernels", "features": ["Ingredients: Corn"],
             "categories": ["Snack Foods", "Popcorn", "Unpopped"]},
            {"parent_asin": "DESCRIPTION", "title": "Rice", "features": ["Ingredients: Rice"],
             "description": ["This product is rice flour."]},
            {"parent_asin": "ENRICHED", "title": "White Rice", "features": ["Ingredients: Rice", "Enriched with vitamins"]},
            {"parent_asin": "CHINESE", "title": "有机大米"},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["status"] for row in audit], ["pending", "pending", "included", "pending", "pending", "pending"])
        self.assertEqual(audit[1]["reason"], "form_not_verified")
        self.assertTrue(audit[2]["form_evidence"])

    def test_catalog_does_not_treat_quality_percentage_as_complete_ingredients(self):
        run = self.catalog([
            {"parent_asin": "RICE", "title": "Brown Rice", "features": ["100% natural organic whole grain rice"]},
            {"parent_asin": "SQUARES", "title": "Soft-Baked Oatmeal Squares, Peanut Butter",
             "features": ["100% natural whole grain oats"], "categories": ["Oatmeal"]},
            {"parent_asin": "SEVEN", "title": "Microwavable Rice, Mixture of Seven Whole Grains",
             "features": ["100% natural organic whole grain basmati rice"]},
            {"parent_asin": "PURE", "title": "Brown Rice", "features": ["100% pure brown rice"]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["status"] for row in audit], ["pending", "excluded", "pending", "included"])

    def test_catalog_keeps_same_family_variety_mixture_pending(self):
        run = self.catalog([
            {"parent_asin": "MILLET", "title": "Millet Grain", "features": ["Ingredients: Ragi, bajra"]},
            {"parent_asin": "RICE", "title": "Rice", "features": ["Ingredients: Brown rice, red rice"]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report["counts"], {"included": 0, "excluded": 0, "pending": 2})

    def test_catalog_preserves_component_lists_in_dedicated_ingredient_fields(self):
        run = self.catalog([
            {"parent_asin": "MILLET", "title": "Millet Grain", "details": {"Ingredients": "Ragi\nBajra"}},
            {"parent_asin": "RICE", "title": "Rice", "details": {"Ingredient": "Brown rice. Red rice."}},
            {"parent_asin": "REPEATED", "title": "Rice", "details": {"Ingredients": "Ingredients: Rice. Ingredients: Rice."}},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["status"] for row in audit], ["pending", "pending", "included"])

    def test_catalog_keeps_ambiguous_alias_and_leaf_category_clues_pending(self):
        run = self.catalog([
            {"parent_asin": "POHA", "title": "Poha THIN - 2lb"},
            {"parent_asin": "JASMINE", "title": "Jasmine Dragon Pearl"},
            {"parent_asin": "LEAF", "title": "Pantry Essentials", "categories": ["Wheat Berries"]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        audit = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual(report["counts"], {"included": 0, "excluded": 0, "pending": 3})
        self.assertEqual(audit[0]["discovery_evidence"], [{"field": "title", "text": "Poha THIN - 2lb"}])
        self.assertEqual(audit[2]["discovery_evidence"], [{"field": "categories[0]", "text": "Wheat Berries"}])

    def test_catalog_quarantines_conflicting_later_composition_statements(self):
        run = self.catalog([
            {"parent_asin": "CONFLICT", "title": "Rice",
             "features": ["Ingredients: Rice. Ingredients: Wheat."]},
            {"parent_asin": "LATER", "title": "Rice",
             "features": ["Store in a dry place. Ingredients: Rice. Ingredients: Wheat."]},
            {"parent_asin": "COOKING", "title": "Rice",
             "features": ["Ingredients: Rice. Serve with wheat bread."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        decisions = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["status"] for row in decisions], ["pending", "pending", "included"])
        self.assertEqual(decisions[0]["reason"], "composition_declaration_conflict")
        self.assertEqual(decisions[1]["composition_evidence"][0]["text"], "Store in a dry place. Ingredients: Rice. Ingredients: Wheat.")

    def test_catalog_quarantines_explicit_outside_or_negated_identity(self):
        run = self.catalog([
            {"parent_asin": "OUTSIDE", "title": "Rice", "features": ["Ingredients: Rice"],
             "description": ["This product is quinoa."]},
            {"parent_asin": "NEGATED", "title": "Rice", "features": ["Ingredients: Rice"],
             "description": ["This product is not rice."]},
            {"parent_asin": "LATER", "title": "Rice", "features": ["Ingredients: Rice"],
             "description": ["Keep dry. This product is quinoa."]},
            {"parent_asin": "ONLY_NEGATIVE", "title": "Pantry food",
             "description": ["This product is not rice."], "features": ["Ingredients: Rice"]},
            {"parent_asin": "SAFE", "title": "Oat groats", "features": ["Ingredients: Oats"],
             "description": ["This product is wheat-free oats."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        decisions = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["status"] for row in decisions], ["pending", "pending", "pending", "pending", "included"])
        self.assertEqual(decisions[0]["reason"], "field_identity_conflict")
        self.assertEqual(decisions[1]["counter_evidence"][0]["text"], "This product is not rice.")

    def test_catalog_checks_all_content_of_dedicated_ingredient_fields(self):
        run = self.catalog([
            {"parent_asin": "MULTILINE", "title": "Rice", "details": {"Ingredients": "Rice\nSalt"}},
            {"parent_asin": "SENTENCES", "title": "Rice", "details": {"Ingredients": "Rice. Salt."}},
            {"parent_asin": "PURE", "title": "Rice", "details": {"Ingredients": "Rice"}},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        decisions = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["status"] for row in decisions], ["pending", "pending", "included"])
        self.assertEqual(decisions[0]["composition_evidence"][0]["text"], "Rice\nSalt")

    def test_catalog_does_not_treat_negated_identity_with_articles_as_positive(self):
        run = self.catalog([
            {"parent_asin": "NOT_A", "title": "Rice", "features": ["Ingredients: Rice"],
             "description": ["This product is not a rice product."]},
            {"parent_asin": "NOT_ANY", "title": "Rice", "features": ["Ingredients: Rice"],
             "description": ["This product is not any kind of rice."]},
            {"parent_asin": "ONLY_NEGATIVE", "title": "Pantry", "features": ["Ingredients: Rice"],
             "description": ["This product is not a rice product."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        decisions = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["status"] for row in decisions], ["pending", "pending", "pending"])
        self.assertFalse(decisions[2]["identity_evidence"])

    def test_catalog_does_not_exempt_specific_crop_category_conflicts(self):
        run = self.catalog([
            {"parent_asin": "BARLEY", "title": "Pearled Barley", "features": ["Ingredients: Barley"],
             "categories": ["Grocery", "Oatmeal"]},
            {"parent_asin": "OATS", "title": "Oat groats", "features": ["Ingredients: Oats"],
             "categories": ["Grocery", "Oatmeal"]},
            {"parent_asin": "WHEAT", "title": "Wheat Berries", "features": ["Ingredients: Wheat"],
             "categories": ["Grocery", "Dried Grains & Rice"]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        decisions = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["status"] for row in decisions], ["pending", "included", "included"])
        self.assertEqual(decisions[0]["counter_evidence"], [{"field": "categories[1]", "text": "Oatmeal"}])

    def test_catalog_negated_title_does_not_prove_positive_identity(self):
        run = self.catalog([
            {"parent_asin": "NEGATIVE_TITLE", "title": "Not a rice product", "features": ["Ingredients: Rice"]},
            {"parent_asin": "ABSENCE", "title": "Food without any kind of rice", "features": ["Ingredients: Rice"]},
            {"parent_asin": "SAFE", "title": "Rice without preservatives", "features": ["Ingredients: Rice"]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        decisions = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["status"] for row in decisions], ["pending", "pending", "included"])

    def test_catalog_checks_unprefixed_composition_continuations_in_all_fields(self):
        run = self.catalog([
            {"parent_asin": "FEATURE", "title": "Rice", "features": ["Ingredients: Rice\nSalt"]},
            {"parent_asin": "DESCRIPTION", "title": "Rice", "description": ["Ingredients: Rice\nSalt"]},
            {"parent_asin": "SENTENCE", "title": "Rice", "features": ["Ingredients: Rice. Salt."]},
            {"parent_asin": "COOKING", "title": "Rice", "features": ["Ingredients: Rice\nDirections: Serve with wheat bread."]},
            {"parent_asin": "LATER", "title": "Rice", "features": ["Ingredients: Rice\nDirections: Store dry.\nIngredients: Wheat"]},
            {"parent_asin": "FRONT", "title": "Rice", "features": ["Store dry.\nIngredients: Rice"]},
            {"parent_asin": "NOT_DIRECTIONS", "title": "Rice", "features": ["Ingredients: Rice. Store-bought salt."]},
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        decisions = [json.loads(line) for line in (self.output / report["audit_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([row["status"] for row in decisions], ["pending", "pending", "pending", "included", "pending", "included", "pending"])
        self.assertEqual(decisions[0]["composition_evidence"][0]["text"], "Ingredients: Rice\nSalt")

    def test_full_source_includes_last_record_and_field_diagnostics(self):
        payload = gzip.compress(
            b'{"parent_asin":"FIRST","title":"Tea","categories":[]}\n'
            b'{"parent_asin":"MIDDLE","title":"Coffee","categories":null}\n'
            b'{"parent_asin":"LAST","title":"Barley grain","categories":["Grains"],"description":["Whole barley"]}\n',
            mtime=0,
        )
        run = self.prepare(payload)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(
            (report["status"], report["scan"]["records"],
             report["scan"]["first_parent_asin"], report["scan"]["last_parent_asin"]),
            ("diagnostic_complete", 3, "FIRST", "LAST"),
        )
        self.assertEqual(report["fields"]["description"]["missing"], 2)
        self.assertEqual(report["fields"]["categories"]["types"], {"list": 2, "null": 1})
        self.assertEqual((self.output / report["raw_path"]).read_bytes(), payload)

    def test_source_record_keeps_bytes_identity_and_checksum_outside_data(self):
        run = self.prepare(gzip.compress(
            b'{"parent_asin":"ONLY","title":"Rice"}\n', mtime=0,
        ))
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report["download"]["bytes"], 56)
        self.assertEqual(report["source"]["dataset"], "interface-fixture")
        self.assertTrue(report["record_path"].startswith("records/sources/"))
        recorded = json.loads((self.output / report["record_path"]).read_text("utf-8"))
        self.assertEqual(recorded["download"]["sha256"],
                         "05f8cf1d29212ac509860be316f5e49633661145870c073c5046809b63ce9785")

    def test_bad_gzip_trailer_is_diagnostic_failure_and_raw_is_preserved(self):
        good = gzip.compress(b'{"parent_asin":"ONLY","title":"Rice"}\n', mtime=0)
        bad_crc = good[:-8] + bytes([good[-8] ^ 1]) + good[-7:]
        for payload in (good[:-8], bad_crc):
            with self.subTest(payload=payload):
                run = self.prepare(payload)
                self.assertNotEqual(run.returncode, 0)
                report = json.loads(run.stdout)
                self.assertEqual(report["status"], "source_incomplete")
                self.assertFalse(report["scan"]["gzip_verified"])
                self.assertEqual((self.output / report["raw_path"]).read_bytes(), payload)

    def test_partial_or_short_http_response_cannot_pass_full_source_gate(self):
        payload = gzip.compress(b'{"parent_asin":"ONLY"}\n', mtime=0)
        for status, length in ((206, len(payload)), (200, len(payload) + 10)):
            with self.subTest(status=status, length=length):
                run = self.prepare(payload, self.serve(payload, status, length))
                report = json.loads(run.stdout)
                self.assertNotEqual(run.returncode, 0)
                self.assertEqual(report["status"], "source_incomplete")
                self.assertIsNotNone(report["error"])

    def test_bad_rows_are_located_and_later_records_still_get_diagnosed(self):
        run = self.prepare(gzip.compress(
            b'{"parent_asin":"FIRST"}\n'
            b'{"broken"\n'
            b'[]\n'
            b'\xff\n'
            b'{"parent_asin":"LAST","categories":"unexpected"}\n',
            mtime=0,
        ))
        report = json.loads(run.stdout)
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(
            (report["scan"]["lines"], report["scan"]["records"],
             report["scan"]["invalid_json_rows"], report["scan"]["non_object_rows"],
             report["scan"]["last_parent_asin"]),
            (5, 2, 2, 1, "LAST"),
        )
        issues = [json.loads(line) for line in
                  (self.output / report["diagnostic_path"]).read_text("utf-8").splitlines()]
        self.assertEqual([issue["line"] for issue in issues], [2, 3, 4])

    def test_missing_parent_and_duplicate_parent_are_audited_without_cleaning(self):
        run = self.prepare(gzip.compress(
            b'{"title":"No parent"}\n'
            b'{"parent_asin":null}\n'
            b'{"parent_asin":"REAL","categories":null}\n'
            b'{"parent_asin":"REAL","categories":"unexpected"}\n', mtime=0,
        ))
        report = json.loads(run.stdout)
        self.assertEqual(
            (report["status"], report["scan"]["records"],
             report["scan"]["invalid_parent_rows"],
             report["scan"]["unique_parents"], report["scan"]["duplicate_parent_rows"]),
            ("needs_review", 4, 2, 1, 1),
        )
        self.assertEqual(report["fields"]["parent_asin"]["missing"], 1)
        self.assertEqual(report["fields"]["categories"]["types"], {"null": 1, "str": 1})

    def test_failed_refresh_keeps_previously_verified_raw_bytes(self):
        payload = gzip.compress(b'{"parent_asin":"ORIGINAL"}\n', mtime=0)
        first = json.loads(self.prepare(payload).stdout)
        failed = self.prepare(payload[:-8])
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual((self.output / first["raw_path"]).read_bytes(), payload)

    def test_null_empty_and_undocumented_fields_are_reported_without_casting(self):
        run = self.prepare(gzip.compress(
            b'{"parent_asin":"A","title":"","categories":[]}\n'
            b'{"parent_asin":"B","title":" ","categories":["Grains"],"description":null,"extra":{}}\n',
            mtime=0,
        ))
        report = json.loads(run.stdout)
        self.assertEqual(report["fields"]["title"]["empty"], 2)
        self.assertEqual(report["fields"]["categories"]["empty"], 1)
        self.assertEqual(
            (report["fields"]["description"]["missing"],
             report["fields"]["description"]["types"]),
            (1, {"null": 1}),
        )
        self.assertEqual(report["fields"]["extra"]["types"], {"dict": 1})

    def test_empty_gzip_cannot_be_accepted_as_a_complete_metadata_source(self):
        run = self.prepare(gzip.compress(b"", mtime=0))
        report = json.loads(run.stdout)
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(report["status"], "source_incomplete")
        self.assertTrue(report["scan"]["gzip_verified"])
        self.assertEqual(report["scan"]["lines"], 0)

    def test_truncated_chunked_http_response_gets_a_machine_diagnostic(self):
        payload = gzip.compress(b'{"parent_asin":"ONLY"}\n', mtime=0)
        run = self.prepare(payload, self.serve(payload, truncated_chunks=True))
        self.assertNotEqual(run.returncode, 0)
        report = json.loads(run.stdout)
        self.assertEqual(report["status"], "source_incomplete")
        self.assertEqual(report["error"]["kind"], "IncompleteRead")
        self.assertFalse(report["scan"]["gzip_verified"])

    def test_download_failure_has_only_this_attempts_row_diagnostics(self):
        payload = gzip.compress(b'{"parent_asin":"ONLY"}\n', mtime=0)
        for previous_errors in (False, True):
            with self.subTest(previous_errors=previous_errors):
                if previous_errors:
                    self.prepare(gzip.compress(b'{"parent_asin":"OLD"}\n{broken\n', mtime=0))
                run = self.prepare(payload, self.serve(b"", status=503))
                report = json.loads(run.stdout)
                self.assertEqual(report["status"], "source_incomplete")
                self.assertEqual(report["scan"]["lines"], 0)
                issues = self.output / report["diagnostic_path"]
                self.assertTrue(issues.is_file())
                self.assertEqual(issues.read_text("utf-8"), "")

    def test_complete_reviews_reach_last_record_and_preserve_original_bytes(self):
        self.prepare(gzip.compress(
            b'{"parent_asin":"FIRST"}\n{"parent_asin":"LAST"}\n', mtime=0))
        payload = gzip.compress(
            b'{"parent_asin":"FIRST","asin":"V1","user_id":"U1","rating":1.0,"title":" raw ","text":"","timestamp":1609459200123}\n'
            b'{"parent_asin":"LAST","asin":"V2","user_id":"U2","rating":5.0,"title":"End","text":" unchanged ","timestamp":1609459200456}\n',
            mtime=0,
        )
        run = self.prepare(payload, stage="reviews")
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual((report["stage"], report["scan"]["records"],
                          report["scan"]["last_parent_asin"]), ("reviews", 2, "LAST"))
        self.assertEqual((self.output / report["raw_path"]).read_bytes(), payload)
        self.assertEqual(report["fields"]["text"]["empty"], 1)

    def test_reviews_join_parent_metadata_without_falling_back_to_variant(self):
        self.prepare(gzip.compress(b'{"parent_asin":"A"}\n{"parent_asin":"B"}\n', mtime=0))
        run = self.prepare(gzip.compress(
            b'{"parent_asin":"A","asin":"V1"}\n'
            b'{"parent_asin":"A","asin":"V2"}\n'
            b'{"parent_asin":"UNKNOWN","asin":"A"}\n'
            b'{"asin":"A"}\n'
            b'{"parent_asin":null,"asin":"B"}\n', mtime=0), stage="reviews")
        report = json.loads(run.stdout)
        association = report["association"]
        self.assertEqual((association["matched_review_rows"],
                          association["unmatched_review_rows"],
                          association["unmatched_unique_parents"]), (2, 1, 1))
        self.assertEqual((association["metadata_parents_with_reviews"],
                          association["metadata_parents_without_reviews"]), (1, 1))
        self.assertEqual(report["scan"]["invalid_parent_rows"], 2)
        self.assertEqual(association["asin_differs_from_parent_rows"], 3)
        self.assertEqual(report["scan"]["records"], 5)

    def test_review_milliseconds_map_to_utc_without_losing_subsecond_values(self):
        self.prepare(gzip.compress(b'{"parent_asin":"A"}\n', mtime=0))
        run = self.prepare(gzip.compress(
            b'{"parent_asin":"A","timestamp":1609459200123}\n'
            b'{"parent_asin":"A","timestamp":1609459200000}\n', mtime=0), stage="reviews")
        time = json.loads(run.stdout)["time"]
        self.assertEqual(time["unit"], "milliseconds")
        self.assertEqual((time["min_raw"], time["min_utc"]),
                         (1609459200000, "2021-01-01T00:00:00.000+00:00"))
        self.assertEqual((time["max_raw"], time["max_utc"]),
                         (1609459200123, "2021-01-01T00:00:00.123+00:00"))
        self.assertEqual(time["nonzero_millisecond_rows"], 1)

    def test_review_anomalies_are_separate_and_do_not_stop_later_diagnosis(self):
        self.prepare(gzip.compress(b'{"parent_asin":"A"}\n', mtime=0))
        rows = [
            {"parent_asin":"A", "asin":"V", "user_id":"U", "rating":0, "title":"", "text":""},
            {"parent_asin":"A", "asin":"V", "user_id":"U", "rating":1, "title":"", "text":"", "timestamp":None},
            {"parent_asin":"A", "asin":"V", "user_id":"U", "rating":1, "title":"", "text":"", "timestamp":"1609459200000"},
            {"parent_asin":"A", "asin":"V", "user_id":"U", "rating":1, "title":"", "text":"", "timestamp":True},
            {"parent_asin":"A", "asin":"V", "user_id":"U", "rating":1, "title":"", "text":{}, "timestamp":10**30},
            {"parent_asin":"A", "rating":5, "title":"", "text":"ok", "timestamp":1609459200000},
        ]
        body = ("\n".join(json.dumps(row) for row in rows) +
                '\n{broken\n[]\n{"parent_asin":"A","asin":"V","user_id":"U","rating":1,"title":"End","text":"valid","timestamp":1609459200123}\n').encode()
        run = self.prepare(gzip.compress(body, mtime=0), stage="reviews")
        self.assertNotEqual(run.returncode, 0)
        report = json.loads(run.stdout)
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual((report["scan"]["lines"], report["scan"]["records"],
                          report["scan"]["invalid_json_rows"], report["scan"]["non_object_rows"]), (9, 7, 1, 1))
        self.assertEqual(report["time"]["invalid_reasons"],
                         {"missing":1, "null":1, "not_integer":2, "unrepresentable":1})
        self.assertEqual(report["time"]["valid_rows"], 2)
        self.assertEqual(report["review_diagnostics"]["invalid_rating_rows"], 1)
        self.assertEqual(report["review_diagnostics"]["invalid_asin_rows"], 1)
        self.assertEqual(report["review_diagnostics"]["invalid_user_rows"], 1)
        self.assertEqual(report["review_diagnostics"]["invalid_text_rows"], 1)
        self.assertEqual(report["fields"]["timestamp"]["missing"], 1)
        self.assertEqual(report["time"]["max_line"], 9)

    def test_review_join_rejects_metadata_bytes_changed_since_verified_record(self):
        metadata = json.loads(self.prepare(gzip.compress(
            b'{"parent_asin":"A"}\n', mtime=0)).stdout)
        (self.output / metadata["raw_path"]).write_bytes(gzip.compress(
            b'{"parent_asin":"OTHER"}\n', mtime=0))
        run = self.prepare(gzip.compress(
            b'{"parent_asin":"A","timestamp":1609459200000}\n', mtime=0), stage="reviews")
        self.assertNotEqual(run.returncode, 0)
        report = json.loads(run.stdout)
        self.assertEqual(report["status"], "source_incomplete")
        self.assertIn("metadata checksum", report["error"]["message"])
        self.assertEqual(report["scan"]["lines"], 0)

    def test_review_time_unit_must_be_explicitly_supported_not_guessed(self):
        self.prepare(gzip.compress(b'{"parent_asin":"A"}\n', mtime=0))
        for unit in (None, "seconds"):
            with self.subTest(unit=unit):
                run = self.prepare(gzip.compress(
                    b'{"parent_asin":"A","timestamp":1609459200000}\n', mtime=0),
                    stage="reviews", time_unit=unit)
                self.assertNotEqual(run.returncode, 0)
                report = json.loads(run.stdout)
                self.assertEqual(report["status"], "source_incomplete")
                self.assertIn("time_unit", report["error"]["message"])
                self.assertEqual(report["scan"]["lines"], 0)

    def test_oversized_rating_is_diagnosed_without_aborting_the_full_review_scan(self):
        self.prepare(gzip.compress(b'{"parent_asin":"A"}\n', mtime=0))
        body = (json.dumps({"parent_asin": "A", "asin": "V", "user_id": "U",
                            "rating": 10**400, "title": "", "text": "", "timestamp": 1609459200000}) +
                '\n{"parent_asin":"A","asin":"V","user_id":"U","rating":5,"title":"End","text":"ok","timestamp":1609459200123}\n').encode()
        run = self.prepare(gzip.compress(body, mtime=0), stage="reviews")
        report = json.loads(run.stdout)
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(report["scan"]["records"], 2)
        self.assertTrue(report["scan"]["gzip_verified"])
        self.assertEqual(report["review_diagnostics"]["invalid_rating_rows"], 1)
        self.assertEqual(report["time"]["max_line"], 2)


if __name__ == "__main__":
    unittest.main()
