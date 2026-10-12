"""Independent artifact/source audit; never classifies or selects products."""

from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
report = json.loads((ROOT / "records/catalog/grain-A-1.0.5.json").read_text("utf-8"))
source = json.loads((ROOT / "records/sources/amazon-2023-grocery-metadata.json").read_text("utf-8"))
assert source["download"]["sha256"] == "ea678886c259d762fac3df5016c34dacd01bd0cc7f0f7aef51cc943f2326bad2"
assert report["source_sha256"] == source["download"]["sha256"]
assert report["scope_sha256"] == hashlib.sha256((ROOT / "config/grain-A-v1.json").read_bytes()).hexdigest()
assert hashlib.sha256((ROOT / ".scratch/data-preparation/spec.md").read_bytes()).hexdigest() == "2fa128e9a1d692468d56ad22035e25332573289be0e4d6f4c25821df0ed6f976"
for name in ("catalog", "audit", "pending"):
    with (ROOT / report[name + "_path"]).open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == report[name + "_sha256"]

included = {row["parent_asin"]: row for row in map(json.loads, (ROOT / report["catalog_path"]).read_text("utf-8").splitlines())}
assert set(included) == {"B09S5HJV3W", "B01BCJ2M0S", "B0B53M8WS2", "B089N9636M", "B0014GZCQQ",
                         "B005HVDZS6", "B00CQAYHQ0", "B01K9F6QQ2", "B0078DQPZG", "B0861CPXR2",
                         "B00CYV2DV2", "B005IPSNMY", "B07CGS1MRR"}
counts = Counter()
reasons = Counter()
pending_rows = 0
references_checked = 0
last = None
with gzip.open(ROOT / source["raw_path"], "rb") as raw, (ROOT / report["audit_path"]).open(encoding="utf-8") as audit:
    for line_number, raw_line in enumerate(raw, 1):
        item = json.loads(raw_line)
        decision = json.loads(next(audit))
        assert decision["parent_asin"] == item["parent_asin"]
        assert decision["source_line"] == line_number and decision["source_lines"] == [line_number]
        assert decision["source_sha256"] == report["source_sha256"]
        assert decision["scope_version"] == "grain-A-1.0.5"
        for kind in ("identity_evidence", "composition_evidence", "form_evidence", "counter_evidence", "discovery_evidence"):
            for evidence in decision[kind]:
                field = evidence["field"]
                indexed = re.fullmatch(r"(features|description|categories)\[(\d+)\]", field)
                original = item[indexed[1]][int(indexed[2])] if indexed else (
                    item["details"][field.removeprefix("details.")] if field.startswith("details.") else item[field])
                assert evidence["text"] == original
                references_checked += 1
        counts[decision["status"]] += 1
        reasons[decision["reason"]] += 1
        pending_rows += decision["status"] == "pending"
        if decision["status"] == "included":
            product = included[item["parent_asin"]]
            assert product["metadata"] == item and product["status"] == "included"
            assert product["identity_evidence"] and product["composition_evidence"] and product["form_evidence"]
            assert not product["counter_evidence"]
            last = {"line": line_number, "parent_asin": item["parent_asin"]}
    assert not audit.readline()
assert line_number == 603274 == sum(counts.values())
assert dict(counts) == report["counts"] and dict(reasons) == report["reasons"]
assert len(included) == counts["included"]
with (ROOT / report["pending_path"]).open(encoding="utf-8") as pending:
    assert sum(1 for _ in pending) == pending_rows

mechanical = Counter()
mechanical_reasons = Counter()
outside_mechanical = []
with (ROOT / "data/diagnostics/scope-04-draft.jsonl").open(encoding="utf-8") as draft, (ROOT / report["audit_path"]).open(encoding="utf-8") as audit:
    for draft_line, audit_line in zip(draft, audit, strict=True):
        prior, decision = json.loads(draft_line), json.loads(audit_line)
        assert prior["parent_asin"] == decision["parent_asin"]
        if prior["status"] == "true_cereal_primary_candidate":
            mechanical[decision["status"]] += 1
            mechanical_reasons[decision["reason"]] += 1
        elif decision["status"] == "included":
            outside_mechanical.append(decision["parent_asin"])
assert sum(mechanical.values()) == 5372
baseline = json.loads((ROOT / ".scratch/data-preparation/verification/original-materials.json").read_text("utf-8"))
unchanged = all(hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() == row["sha256"] for row in baseline["files"])
assert unchanged
result = {"status": "independent_artifact_audit_passed", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
          "counts": counts, "reasons": reasons, "source_rows": line_number, "literal_evidence_references_checked": references_checked,
          "last_included_source": last, "mechanical_A_outcomes": mechanical,
          "mechanical_A_reasons": mechanical_reasons, "included_outside_mechanical_A": len(outside_mechanical),
          "catalog_sha256": report["catalog_sha256"], "scope_sha256": report["scope_sha256"],
          "original_materials_unchanged": unchanged, "original_material_count": len(baseline["files"]),
          "limitations": "Checks all source locations, summaries and set accounting; does not substitute for independent semantic adjudication of pending products."}
destination = ROOT / ".scratch/data-preparation/verification/catalog-04-check.json"
destination.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", "utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
