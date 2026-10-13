"""Aggregate hypothetical rule impacts; does not build a clean view or user tasks."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
VERSION = sys.argv[1]
record_path = ROOT / "records/reviews" / (VERSION + "-review-diagnostics-1.0.0.json")
record = json.loads(record_path.read_text("utf-8"))
assert record["status"] == "extraction_complete"
for name in ("references", "groups"):
    with (ROOT / record[name + "_path"]).open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == record[name + "_sha256"]
raw_path = ROOT / record["extract_path"]
with raw_path.open("rb") as stream:
    assert hashlib.file_digest(stream, "sha256").hexdigest() == record["extract_sha256"]
refs = [json.loads(line) for line in (ROOT / record["references_path"]).read_text("utf-8").splitlines()]
rows = [(ref["source_line"], json.loads(line)) for ref, line in zip(refs, raw_path.read_text("utf-8").splitlines(), strict=True)]
groups = [json.loads(line) for line in (ROOT / record["groups_path"]).read_text("utf-8").splitlines()]
conflicted = {n for group in groups if group["kind"] in ("raw_quad", "same_product_equal_time") and group["conflicting_fields"] for n in group["source_lines"]}
exact_excess = {n for group in groups if group["kind"] == "exact_object" for n in group["source_lines"][1:]}
joint_removed = conflicted | exact_excess
joint_text_rows = [(n, row) for n, row in rows if n not in joint_removed
                   and row["text"].strip() and 1 <= row["rating"] <= 5]
joint_text_option = {"rule": "Nonblank valid-rating text, exact-object dedup and both raw-quad/equal-time fact-conflict quarantine; diagnostic counts only.",
                     "kept_reviews": len(joint_text_rows), "lost_reviews": len(rows) - len(joint_text_rows),
                     "kept_accounts": len({r["user_id"] for _, r in joint_text_rows}),
                     "kept_active_products": len({r["parent_asin"] for _, r in joint_text_rows}),
                     "catalog_products_retained": len(record["product_review_counts"]),
                     "formal_clean_view": "not_built"}


def alternatives(values, minimum_rating):
    accounts = defaultdict(list)
    for number, row in values:
        # Source facts have been independently checked before this script is run.
        assert type(row["timestamp"]) is int and isinstance(row["text"], str)
        accounts[row["user_id"]].append((number, row))
    prior_all, prior_positive, excluded = Counter(), Counter(), Counter()
    for interactions in accounts.values():
        latest = max(row["timestamp"] for _, row in interactions)
        target = [(n, row) for n, row in interactions if row["timestamp"] == latest]
        prior = [(n, row) for n, row in interactions if row["timestamp"] < latest]
        target_parents = {r["parent_asin"] for _, r in target}
        seen = {r["parent_asin"] for _, r in prior}
        if len(target_parents) != 1:
            excluded["multiple_latest_parents"] += 1
        elif len({json.dumps(r, sort_keys=True) for _, r in target}) != 1:
            excluded["latest_fact_conflict"] += 1
        elif not (target_parents - seen):
            excluded["latest_seen_product"] += 1
        elif not (minimum_rating <= target[0][1]["rating"] <= 5 and target[0][1]["text"].strip()):
            excluded["latest_not_positive_text"] += 1
        else:
            all_valid = {r["parent_asin"] for n, r in prior if n not in conflicted and r["text"].strip() and 1 <= r["rating"] <= 5}
            positive = {r["parent_asin"] for n, r in prior if n not in conflicted and r["text"].strip() and minimum_rating <= r["rating"] <= 5}
            prior_all[len(all_valid)] += 1
            prior_positive[len(positive)] += 1
    return {"latest_conditional_accounts": sum(prior_all.values()), "excluded_reasons": excluded,
            "history_impact": [{"minimum_distinct_prior_products": minimum,
                                "accounts_with_valid_text_history": sum(n for depth, n in prior_all.items() if depth >= minimum),
                                "accounts_with_positive_text_history": sum(n for depth, n in prior_positive.items() if depth >= minimum)}
                               for minimum in (0, 1, 2, 3, 5)],
            "prior_all_valid_text_depth": prior_all, "prior_positive_depth": prior_positive}


ratings = {str(value): alternatives(rows, value) for value in (3, 4, 5)}
assert ratings["4"]["latest_conditional_accounts"] == record["history"]["manuscript_positive_candidate"]["potential_accounts"]
assert {str(k): v for k, v in ratings["4"]["prior_positive_depth"].items()} == record["history"]["manuscript_positive_candidate"]["prior_positive_products"]
cutoff = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
cut_rows = [(n, row) for n, row in rows if row["timestamp"] < cutoff]
assert len(cut_rows) <= len(rows)
result = {"status": "hypothetical_options_not_approved", "scope_version": VERSION,
          "generated_at_utc": datetime.now(timezone.utc).isoformat(),
          "extract_sha256": record["extract_sha256"], "record_sha256": hashlib.sha256(record_path.read_bytes()).hexdigest(),
          "producer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "joint_text_option": joint_text_option,
          "rating_options": ratings,
          "cutoff_alternative": {"timestamp_ms": cutoff, "endpoint": "exclusive", "utc": "2023-01-01T00:00:00Z",
                                 "justification": "Illustrates limiting retrospective data to the end of calendar 2022; does not claim later source observations are invalid or that 2022 coverage is complete.",
                                 "kept_reviews": len(cut_rows), "lost_reviews": len(rows) - len(cut_rows),
                                 "kept_accounts": len({r["user_id"] for _, r in cut_rows}),
                                 "kept_active_products": len({r["parent_asin"] for _, r in cut_rows}),
                                 "rating4_conditional": alternatives(cut_rows, 4)},
          "limitations": ["No cutoff, rating threshold or history requirement is approved.",
                          "All earlier interactions determine seen products, including low ratings and empty text.",
                          "Account IDs do not demonstrate independent people or statistical sufficiency.",
                          "No user split, private target labels, formal clean view or model input is generated."]}
destination = ROOT / ".scratch/data-preparation/verification" / (VERSION + "-ticket06-options.json")
destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
