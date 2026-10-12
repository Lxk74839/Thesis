"""Independent byte reconciliation and SQL diagnostics oracle; no production imports."""

from collections import Counter
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
record_path = ROOT / "records/reviews/grain-A-1.0.6-review-diagnostics-1.0.0.json"
report = json.loads(record_path.read_text("utf-8"))
catalog = json.loads((ROOT / "records/catalog/grain-A-1.0.6.json").read_text("utf-8"))
source = json.loads((ROOT / "records/sources/amazon-2023-grocery-reviews.json").read_text("utf-8"))
assert report["status"] == "extraction_complete" and catalog["status"] == "catalog_complete"
assert report["source_sha256"] == source["download"]["sha256"]
assert report["catalog_sha256"] == catalog["catalog_sha256"]
assert report["source_record_sha256"] == hashlib.sha256((ROOT / "records/sources/amazon-2023-grocery-reviews.json").read_bytes()).hexdigest()
assert report["catalog_record_sha256"] == hashlib.sha256((ROOT / "records/catalog/grain-A-1.0.6.json").read_bytes()).hexdigest()
for name in ("prepare_data.py", "review_diagnostics.py"):
    assert report["producer_sha256"][name] == hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
for name in ("extract", "references", "groups", "errors", "cleaning", "history"):
    path = (ROOT / report[name + "_path"]).resolve()
    assert ROOT in path.parents
    with path.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == report[name + "_sha256"]
with (ROOT / source["raw_path"]).open("rb") as stream:
    assert hashlib.file_digest(stream, "sha256").hexdigest() == source["download"]["sha256"]
with (ROOT / catalog["catalog_path"]).open("rb") as stream:
    assert hashlib.file_digest(stream, "sha256").hexdigest() == catalog["catalog_sha256"]
products = {row["parent_asin"]: 0 for row in map(json.loads, (ROOT / catalog["catalog_path"]).read_text("utf-8").splitlines())}
database = sqlite3.connect(":memory:")
database.execute("CREATE TABLE reviews(n INTEGER, user TEXT, parent TEXT, stamp INTEGER, rating REAL, text TEXT, normalized TEXT, object TEXT, quad_facts TEXT, time_facts TEXT, valid_text INTEGER, valid_rating INTEGER, valid_time INTEGER, valid_ids INTEGER)")
selected = []
with gzip.open(ROOT / source["raw_path"], "rb") as raw, (ROOT / report["extract_path"]).open("rb") as extract, (ROOT / report["references_path"]).open(encoding="utf-8") as references:
    for source_line, line in enumerate(raw, 1):
        item = json.loads(line)
        assert isinstance(item, dict) and isinstance(item["parent_asin"], str) and item["parent_asin"].strip()
        parent = item["parent_asin"]
        if parent not in products:
            continue
        assert extract.readline() == line
        reference = json.loads(next(references))
        assert reference == {"selected_row": len(selected) + 1, "source_line": source_line, "line_sha256": hashlib.sha256(line).hexdigest()}
        products[parent] += 1
        selected.append((source_line, item))
        # Actual source fields have been measured; unexpected drift fails this oracle.
        assert type(item["timestamp"]) is int and isinstance(item["user_id"], str) and item["user_id"].strip()
        assert isinstance(item["text"], str) and isinstance(item["asin"], str) and item["asin"].strip()
        stamp = item["timestamp"]
        utc = datetime.fromtimestamp(stamp // 1000, timezone.utc) + timedelta(microseconds=1000 * (stamp % 1000))
        assert utc.year >= 1
        quad_facts = {key: value for key, value in item.items() if key not in ("user_id", "parent_asin", "timestamp", "text")}
        time_facts = {key: value for key, value in item.items() if key not in ("user_id", "parent_asin", "timestamp")}
        database.execute("INSERT INTO reviews VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            source_line, item["user_id"], parent, stamp, item["rating"], item["text"], unicodedata.normalize("NFC", item["text"]).strip(),
            json.dumps(item, sort_keys=True, ensure_ascii=False), json.dumps(quad_facts, sort_keys=True), json.dumps(time_facts, sort_keys=True),
            bool(item["text"].strip()), type(item["rating"]) in (int, float) and 1 <= item["rating"] <= 5, 1, 1))
    assert not extract.readline() and not references.readline()
assert source_line == 14318520 == report["scan"]["lines"] == report["scan"]["records"]
assert report["scan"]["gzip_verified"] and report["scan"]["matched_rows"] == len(selected)
assert report["scan"]["other_parent_rows"] == source_line - len(selected)
assert all(report["scan"][name] == 0 for name in ("invalid_json_rows", "non_object_rows", "invalid_parent_rows"))
assert products == report["product_review_counts"]

def numbers(query):
    return {row[0] for row in database.execute(query)}

def population(kept):
    if not kept:
        return (0, 0, 0)
    placeholders = ",".join("?" for _ in kept)
    return database.execute(f"SELECT count(*),count(distinct parent),count(distinct user) FROM reviews WHERE n IN ({placeholders})", list(kept)).fetchone()

all_numbers = numbers("SELECT n FROM reviews")
baseline = population(all_numbers)
assert (report["raw"]["reviews"], report["raw"]["products_with_reviews"], report["raw"]["unique_accounts"]) == baseline
assert report["raw"]["products_without_reviews"] == sum(count == 0 for count in products.values())
kept = {
    "nonblank_text": numbers("SELECT n FROM reviews WHERE valid_text"),
    "valid_rating": numbers("SELECT n FROM reviews WHERE valid_rating"),
    "valid_time": numbers("SELECT n FROM reviews WHERE valid_time"),
    "valid_identifiers": numbers("SELECT n FROM reviews WHERE valid_ids"),
    "exact_object_dedup": numbers("SELECT min(n) FROM reviews GROUP BY object"),
    "raw_quad_conflict_quarantine": numbers("SELECT n FROM reviews WHERE (user,parent,stamp,text) IN (SELECT user,parent,stamp,text FROM reviews GROUP BY user,parent,stamp,text HAVING count(distinct quad_facts)=1)"),
    "nfc_strip_quad_safe_dedup": numbers("SELECT min(n) FROM reviews GROUP BY user,parent,stamp,normalized HAVING count(distinct quad_facts)=1"),
    "equal_time_conflict_quarantine": numbers("SELECT n FROM reviews WHERE (user,parent,stamp) IN (SELECT user,parent,stamp FROM reviews GROUP BY user,parent,stamp HAVING count(distinct time_facts)=1)"),
}
valid = kept["nonblank_text"] & kept["valid_rating"] & kept["valid_time"] & kept["valid_identifiers"]
kept["combined_raw"] = valid & kept["exact_object_dedup"] & kept["raw_quad_conflict_quarantine"]
kept["combined_nfc"] = valid & kept["nfc_strip_quad_safe_dedup"]
for name, members in kept.items():
    reviews, active_products, users = population(members)
    expected = {"kept_reviews": reviews, "lost_reviews": baseline[0] - reviews,
                "kept_products_with_reviews": active_products, "lost_products_with_reviews": baseline[1] - active_products,
                "kept_accounts": users, "lost_accounts": baseline[2] - users, "catalog_products_retained": len(products)}
    assert report["candidate_cleaning"]["scenarios"][name] == expected, name
with (ROOT / report["cleaning_path"]).open(encoding="utf-8") as stream:
    for number, _ in selected:
        row = json.loads(next(stream))
        assert row["source_line"] == number
        assert set(row["candidate_removed_by"]) == {name for name, members in kept.items() if number not in members}
    assert not stream.readline()
for mode, keys, facts in (("raw_quad", "user,parent,stamp,text", "quad_facts"), ("nfc_strip_quad", "user,parent,stamp,normalized", "quad_facts"), ("same_product_equal_time", "user,parent,stamp", "time_facts")):
    groups = list(database.execute(f"SELECT count(*),count(distinct {facts}) FROM reviews GROUP BY {keys}"))
    expected = {"duplicate_groups": sum(size > 1 for size, _ in groups), "duplicate_member_rows": sum(size for size, _ in groups if size > 1),
                "duplicate_excess_rows": sum(size - 1 for size, _ in groups if size > 1), "conflict_groups": sum(facts > 1 for _, facts in groups),
                "conflict_member_rows": sum(size for size, facts in groups if facts > 1), "ungroupable_rows": 0}
    assert report["duplicates"][mode] == expected, mode
exact = list(database.execute("SELECT count(*) FROM reviews GROUP BY object HAVING count(*)>1"))
assert report["duplicates"]["exact_object_duplicate_groups"] == len(exact)
assert report["duplicates"]["exact_object_excess_rows"] == sum(size - 1 for (size,) in exact)
assert report["quality"]["empty_text_rows"] == len(all_numbers - kept["nonblank_text"])
assert report["quality"]["invalid_rating_rows"] == len(all_numbers - kept["valid_rating"])
assert report["quality"]["invalid_time_rows"] == report["quality"]["invalid_identifier_rows"] == report["quality"]["invalid_text_rows"] == 0
for field, summary in report["quality"]["fields"].items():
    assert summary["missing"] == 0 and sum(summary["types"].values()) == len(selected)

hist = {name: Counter() for name in ("reviews_per_account", "distinct_products_per_account", "strict_prior_reviews", "strict_prior_products", "latest_unseen_products")}
excluded = Counter()
positive_depth = Counter()
multiple = unique_unseen = potential = 0
for user, depth, distinct_parents, latest in database.execute("SELECT user,count(*),count(distinct parent),max(stamp) FROM reviews GROUP BY user"):
    prior = list(database.execute("SELECT n,parent,rating,valid_text FROM reviews WHERE user=? AND stamp<?", (user, latest)))
    targets = list(database.execute("SELECT parent,object,rating,valid_text FROM reviews WHERE user=? AND stamp=?", (user, latest)))
    target_parents = {row[0] for row in targets}
    seen = {row[1] for row in prior}
    unseen = target_parents - seen
    for name, value in (("reviews_per_account", depth), ("distinct_products_per_account", distinct_parents), ("strict_prior_reviews", len(prior)), ("strict_prior_products", len(seen)), ("latest_unseen_products", len(unseen))):
        hist[name][str(value)] += 1
    multiple += len(target_parents) > 1
    unique_unseen += len(target_parents) == 1 and bool(unseen)
    reason = ("multiple_latest_parents" if len(target_parents) != 1 else "latest_fact_conflict" if len({row[1] for row in targets}) != 1 else
              "latest_seen_product" if not unseen else "latest_not_positive" if not (4 <= targets[0][2] <= 5 and targets[0][3]) else None)
    if reason:
        excluded[reason] += 1
    else:
        potential += 1
        parents = {parent for n, parent, rating, valid_text in prior if n in kept["equal_time_conflict_quarantine"] and n in kept["raw_quad_conflict_quarantine"] and 4 <= rating <= 5 and valid_text}
        positive_depth[str(len(parents))] += 1
for name, histogram in hist.items():
    assert report["history"][name] == dict(histogram), name
assert report["history"]["multiple_latest_parent_accounts"] == multiple
assert report["history"]["unique_latest_unseen_accounts_with_known_time"] == unique_unseen
assert report["history"]["accounts_with_invalid_time"] == report["history"]["accounts_without_valid_time"] == 0
candidate = report["history"]["manuscript_positive_candidate"]
assert candidate["potential_accounts"] == potential and candidate["prior_positive_products"] == dict(positive_depth) and candidate["excluded_reasons"] == dict(excluded)
assert candidate["approval"] == report["candidate_cleaning"]["approval"] == "not_approved" and candidate["minimum_prior_products"] is None
for name, sql in (("min", "min"), ("max", "max")):
    value = database.execute(f"SELECT {sql}(stamp) FROM reviews").fetchone()[0]
    expected = (datetime.fromtimestamp(value // 1000, timezone.utc) + timedelta(microseconds=1000 * (value % 1000))).isoformat(timespec="milliseconds")
    assert report["time"][name + "_raw"] == value and report["time"][name + "_utc"] == expected
assert report["time"]["cutoff"] is None and report["time"]["cutoff_approval"] == "not_approved"
baseline_materials = json.loads((ROOT / ".scratch/data-preparation/verification/original-materials.json").read_text("utf-8"))["files"]
assert all(hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() == row["sha256"] for row in baseline_materials)
assert hashlib.sha256((ROOT / ".scratch/data-preparation/spec.md").read_bytes()).hexdigest() == "2fa128e9a1d692468d56ad22035e25332573289be0e4d6f4c25821df0ed6f976"
assert report["formal_clean_status"] == report["formal_package_status"] == "not_built" and report["model_input_status"] == "not_released" and report["sample_sufficiency"] == "not_determined"
result = {"status": "independent_review_reconciliation_passed", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
          "source_rows": source_line, "matched_reviews": len(selected), "catalog_products": len(products),
          "products_without_reviews": sum(count == 0 for count in products.values()), "unique_accounts": baseline[2],
          "last_match_source_line": selected[-1][0], "extract_sha256": report["extract_sha256"],
          "candidate_potential_accounts": potential, "candidate_prior_positive_products": positive_depth,
          "oracle": "Full-source parent selection with byte-by-byte extraction reconciliation; independent SQLite grouping, membership, losses and chronology.",
          "original_materials_unchanged": True, "original_material_count": len(baseline_materials), "spec_unchanged": True,
          "limitations": "Account IDs do not prove independent natural people. Unapproved candidate results do not establish formal qualification or sample sufficiency."}
(ROOT / ".scratch/data-preparation/verification/review-extract-05-check.json").write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", "utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
