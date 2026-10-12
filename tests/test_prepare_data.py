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

    def run_catalog(self, config=None):
        return subprocess.run(
            [sys.executable, str(PROJECT / "prepare_data.py"), "--stage", "catalog",
             "--metadata-record", str(self.output / "records/sources/fixture-metadata.json"),
             "--scope-config", str(config or PROJECT / "config/grain-A-v1.json"),
             "--output-root", str(self.output)],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8",
        )

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
