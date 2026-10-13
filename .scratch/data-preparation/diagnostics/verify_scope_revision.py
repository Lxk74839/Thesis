"""Independent full-source migration and literal evidence audit; no production imports."""

from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
VERSION = sys.argv[1] if len(sys.argv) > 1 else "grain-A-1.1.0"
report = json.loads((ROOT / "records/catalog" / (VERSION + ".json")).read_text("utf-8"))
source = json.loads((ROOT / "records/sources/amazon-2023-grocery-metadata.json").read_text("utf-8"))
prior = json.loads((ROOT / report["previous_record_path"]).read_text("utf-8"))
assert report["status"] == "catalog_complete"
assert report["source_sha256"] == prior["source_sha256"] == source["download"]["sha256"]
assert report["scope_sha256"] == hashlib.sha256((ROOT / "config" / (VERSION + ".json")).read_bytes()).hexdigest()
assert report["previous_record_sha256"] == hashlib.sha256((ROOT / report["previous_record_path"]).read_bytes()).hexdigest()
assert report["previous_audit_sha256"] == prior["audit_sha256"]
for name in ("catalog", "audit", "pending", "migration"):
    with (ROOT / report[name + "_path"]).open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == report[name + "_sha256"]
for name, digest in report["producer_sha256"].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest

included = {r["parent_asin"]: r for r in map(json.loads, (ROOT / report["catalog_path"]).read_text("utf-8").splitlines())}
cases = json.loads((ROOT / ".scratch/data-preparation/diagnostics/usability-case-review-20261012.json").read_text("utf-8"))["annotations"]
expected = {r["parent_asin"]: ("included" if r["group"] in ("I", "P") else "excluded" if r["group"] == "X" else "pending") for r in cases}
# The original U note identifies Almond & Vanilla and missing form evidence.
# The explicit sold flavor combination is now handled like the reviewed Apple Cinnamon
# title under the approved seasoning exclusion, without inventing a full composition list.
expected["B08L737QS1"] = "excluded"
case_results = []
counts, reasons, transitions, compositions, included_compositions, crops = (Counter() for _ in range(6))
references = 0
unknown_examples = {}
declaration_examples = []
with gzip.open(ROOT / source["raw_path"], "rb") as raw, (ROOT / report["audit_path"]).open(encoding="utf-8") as audit, (ROOT / prior["audit_path"]).open(encoding="utf-8") as old, (ROOT / report["migration_path"]).open(encoding="utf-8") as migration, (ROOT / report["pending_path"]).open(encoding="utf-8") as pending:
    for number, raw_line in enumerate(raw, 1):
        item, decision, previous, change = json.loads(raw_line), json.loads(next(audit)), json.loads(next(old)), json.loads(next(migration))
        parent = item["parent_asin"]
        assert decision["parent_asin"] == previous["parent_asin"] == change["parent_asin"] == parent
        assert decision["source_line"] == previous["source_line"] == change["source_line"] == number
        assert decision["source_lines"] == change["source_lines"] == [number]  # Verified unique-parent source fact.
        assert change["source_sha256"] == decision["source_sha256"] == report["source_sha256"]
        assert decision["scope_version"] == VERSION
        assert change["old"] == {k: previous[k] for k in ("status", "reason", "crop", "scope_version")}
        assert change["new"] == {k: decision[k] for k in ("status", "reason", "crop", "scope_version", "composition_status")}
        assert change["old_audit_line"] == change["new_audit_line"] == number
        assert change["migration_reason"] == previous["reason"] + " -> " + decision["reason"]
        for kind in ("identity_evidence", "form_evidence", "composition_evidence", "counter_evidence", "discovery_evidence", "context_evidence"):
            for ref in decision.get(kind, []):
                field = ref["field"]
                index = re.fullmatch(r"(features|description|categories)\[(\d+)\]", field)
                original = item[index[1]][int(index[2])] if index else item["details"][field[8:]] if field.startswith("details.") else item[field]
                assert ref["text"] == original
                if "clause_text" in ref:
                    assert ref["clause_text"] in original
                    assert 0 <= ref["context_start"] <= len(ref["clause_text"])
                for part in ref.get("declaration_parts", []):
                    assert part in original
                references += 1
        counts[decision["status"]] += 1
        reasons[decision["reason"]] += 1
        transitions[previous["status"] + "->" + decision["status"]] += 1
        compositions[decision["composition_status"]] += 1
        if parent in expected:
            assert decision["status"] == expected[parent], (parent, expected[parent], decision)
            case_results.append({"parent_asin": parent, "status": decision["status"], "source_line": number})
        if decision["status"] == "included":
            assert included[parent] == {**decision, "metadata": item}
            assert decision["identity_evidence"] and decision["form_evidence"] and not decision["counter_evidence"]
            assert decision["composition_status"] in ("not_disclosed", "declared_single_grain")
            assert bool(decision["composition_evidence"]) == (decision["composition_status"] == "declared_single_grain")
            crops[decision["crop"]] += 1
            included_compositions[decision["composition_status"]] += 1
            sample = {"parent_asin": parent, "source_line": number, "title": item["title"], "decision": decision, "metadata": item}
            if decision["composition_status"] == "not_disclosed":
                # Lowest hash cases within each crop: deterministic, not a probability or prevalence estimate.
                values = unknown_examples.setdefault(decision["crop"], [])
                values.append((hashlib.sha256(parent.encode()).hexdigest(), sample))
                values.sort(key=lambda pair: pair[0])
                del values[5:]
            else:
                declaration_examples.append(sample)
        elif decision["status"] == "pending":
            assert json.loads(next(pending)) == {**decision, "metadata": item}
    assert not audit.readline() and not old.readline() and not migration.readline() and not pending.readline()
assert number == 603274 == report["scan"]["rows"] == sum(counts.values())
assert report["scan"]["unique_parents"] == number and report["scan"]["gzip_verified"]
assert dict(counts) == report["counts"] and dict(reasons) == report["reasons"]
assert dict(transitions) == report["migration_counts"]
assert dict(compositions) == report["composition_counts"] and dict(included_compositions) == report["included_composition_counts"]
assert len(included) == counts["included"] and len(case_results) == len(expected) == 41
assert report["composition_verification"] == "source_declaration_only_not_independently_verified"
assert report["supply_chain_verification"] == "not_performed"
assert report["model_input_status"] == "not_released" and report["sample_sufficiency"] == "not_determined"
protection = json.loads((ROOT / ".scratch/data-preparation/verification/scope-revision-protection.json").read_text("utf-8"))
for relative, digest in protection["protected_sha256"].items():
    with (ROOT / relative).open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == digest, relative
rejected_components = 0
for receipt in (ROOT / ".scratch/data-preparation/verification").glob("grain-A-1.1.*-rejection.json"):
    for relative, digest in json.loads(receipt.read_text("utf-8"))["preserved_sha256"].items():
        with (ROOT / relative).open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == digest, relative
        rejected_components += 1
result = {"status": "independent_scope_revision_audit_passed", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
          "scope_version": VERSION, "source_rows": number, "counts": counts, "migration_counts": transitions,
          "composition_counts": compositions, "included_composition_counts": included_compositions, "included_crop_counts": crops,
          "literal_source_references_checked": references, "known_semantic_cases_checked": case_results,
          "catalog_sha256": report["catalog_sha256"], "migration_sha256": report["migration_sha256"],
          "protected_files_unchanged": len(protection["protected_sha256"]), "original_materials_unchanged": 26,
          "rejected_version_components_unchanged": rejected_components,
          "limitations": "All source/migration accounting checked; 41 fixed semantic cases checked. New population still requires documented semantic spot checks, not an assertion of exhaustive human adjudication."}
destination = ROOT / ".scratch/data-preparation/verification" / (VERSION + "-check.json")
destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8")
sample_path = ROOT / "data/diagnostics" / (VERSION + "-semantic-sample.json")
sample_path.write_text(json.dumps({"unknown_by_crop": {crop: [s for _, s in values] for crop, values in unknown_examples.items()}, "all_declared_single_grain": declaration_examples}, ensure_ascii=False, indent=2), "utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
