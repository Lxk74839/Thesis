"""Read-only ticket 07 analysis; emit aggregates only, never assignments or model data.

This is supporting evidence for an unapproved proposal, not a data preparation stage.
Run with the project's Thesis Conda environment, from the project root.
"""
import hashlib
import json
import math
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT.parent.parent / "CodexPlan" / "Plan_Thesis"
SALT = "Thesis-ticket07-grain-A-1.1.15-review-cleaning-1.0.0-split-v1"
OLD_SALT = "Plan_Thesis-parent-grain-v1-20261002"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rows(path):
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def summary(values):
    values = sorted(values)
    return {"n": len(values), "min": values[0], "median": median(values),
            "p90_nearest_rank": values[math.ceil(len(values)*.9)-1],
            "p95_nearest_rank": values[math.ceil(len(values)*.95)-1],
            "max": values[-1], "mean": mean(values)}


def concentration(counts):
    ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    n = sum(counts.values())
    hhi = sum((v/n)**2 for v in counts.values())
    return {"units": n, "products": len(counts), "hhi": hhi,
            "inverse_hhi": 1/hhi, "singletons": sum(v == 1 for v in counts.values()),
            "top_counts": {str(k): sum(v for _, v in ranked[:k]) for k in (1, 5, 10, 20)},
            "top10": [{"parent_asin": p, "count": v} for p, v in ranked[:10]],
            "frequency": dict(sorted(Counter(counts.values()).items()))}


def ordered(users):
    return sorted(users, key=lambda u: (hashlib.sha256(SALT.encode()+b"\0"+u.encode()).digest(), u.encode()))


def main():
    assert Path(sys.prefix).resolve() == ROOT / ".conda/envs/Thesis"
    record = load(ROOT / "records/cleaning/grain-A-1.1.15-review-cleaning-1.0.0.json")
    acceptance = load(ROOT / "records/cleaning/grain-A-1.1.15-review-cleaning-1.0.0-acceptance.json")
    erratum = load(ROOT / "records/cleaning/grain-A-1.1.15-review-cleaning-1.0.0-format-erratum.json")
    inputs = {str(ROOT/p): s for p, s in acceptance["dependencies_sha256"].items()}
    inputs.update({str(ROOT/record[k+"_path"]): record[k+"_sha256"]
                   for k in ("accounts", "clean", "text", "products", "quarantine", "audit")})
    assert all(sha(p) == s for p, s in inputs.items()), "Accepted input changed"
    assert sha(ROOT / erratum["affected_record_path"]) == erratum["affected_record_sha256"]
    for path in ("AGENTS.md", ".scratch/data-preparation/spec.md",
                 ".scratch/data-preparation/issues/07-user-split-diagnostics.md",
                 ".scratch/data-preparation/ticket06-acceptance-review-cleaning-1.0.0.md",
                 "records/cleaning/grain-A-1.1.15-review-cleaning-1.0.0-acceptance.json",
                 "research/数据修复方案与验收草案_20261010.md",
                 "manuscript/论文初稿_表达与实验结构修订版_20261010.docx"):
        inputs[str(ROOT/path)] = sha(ROOT/path)
    accounts = {r["user_id"]: r for r in rows(ROOT / record["accounts_path"])}
    eligible = {u: a for u, a in accounts.items() if a["status"] == "qualified"}
    assert len(accounts) == 53576 and len(eligible) == 1603
    catalog_record = load(ROOT / record["catalog_record_path"])
    catalog = {r["parent_asin"]: r for r in rows(ROOT / catalog_record["catalog_path"])}
    review_record = load(ROOT / record["source_record_path"])
    assert sha(ROOT/catalog_record["catalog_path"]) == catalog_record["catalog_sha256"]
    assert sha(ROOT/review_record["extract_path"]) == record["source_extract_sha256"]
    inputs[str(ROOT/catalog_record["catalog_path"])] = catalog_record["catalog_sha256"]
    inputs[str(ROOT/review_record["extract_path"])] = record["source_extract_sha256"]
    clean = list(rows(ROOT / record["clean_path"]))
    texts = list(rows(ROOT / record["text_path"]))
    prior = defaultdict(list)
    for r in clean:
        u = r["review"]["user_id"]
        if u in eligible and r["timestamp_ms"] < eligible[u]["latest_timestamp_ms"]:
            prior[u].append(r)
    positive = {u: [r for r in hist if r["review"]["rating"] >= 4 and r["review"]["text"].strip()]
                for u, hist in prior.items()}
    targets = Counter(a["target_parent_asin"] for a in eligible.values())
    hist_products = Counter(p for a in eligible.values() for p in a["prior_positive_parent_asins"])
    seen_products = Counter(p for a in eligible.values() for p in a["seen_parent_asins"])
    for u, a in eligible.items():
        assert {r["review"]["parent_asin"] for r in prior[u]} == set(a["seen_parent_asins"])
        assert {r["review"]["parent_asin"] for r in positive[u]} == set(a["prior_positive_parent_asins"])
        assert len(a["prior_positive_parent_asins"]) == a["prior_positive_product_count"] >= 1
        assert a["target_parent_asin"] not in a["seen_parent_asins"]
    qualified_latest = defaultdict(list)
    for r in clean:
        u = r["review"]["user_id"]
        if u in eligible and r["timestamp_ms"] == eligible[u]["latest_timestamp_ms"]:
            qualified_latest[u].append(r["review"])
    assert len(qualified_latest) == len(eligible)
    assert all(len({r["parent_asin"] for r in rs}) == 1 and
               all(r["rating"] >= 4 and r["text"].strip() for r in rs)
               for rs in qualified_latest.values())
    # Independent SQL aggregation checks the Python account/product/time grouping.
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE a(u TEXT PRIMARY KEY,t INTEGER,p TEXT)")
    db.executemany("INSERT INTO a VALUES(?,?,?)", [(u,a["latest_timestamp_ms"],a["target_parent_asin"]) for u,a in eligible.items()])
    db.execute("CREATE TABLE r(u TEXT,p TEXT,t INTEGER,r REAL,txt TEXT)")
    db.executemany("INSERT INTO r VALUES(?,?,?,?,?)", [(x["review"]["user_id"],x["review"]["parent_asin"],x["timestamp_ms"],x["review"]["rating"],x["review"]["text"]) for x in clean])
    sql_depth = Counter(x[0] for x in db.execute("SELECT COUNT(DISTINCT r.p) FROM a JOIN r ON a.u=r.u WHERE r.t<a.t AND r.r>=4 AND LENGTH(TRIM(r.txt))>0 GROUP BY a.u"))
    assert sql_depth == Counter(a["prior_positive_product_count"] for a in eligible.values())
    assert db.execute("SELECT COUNT(DISTINCT p) FROM a").fetchone()[0] == len(targets)
    sql_prior = db.execute("SELECT COUNT(*) FROM a JOIN r ON a.u=r.u WHERE r.t<a.t").fetchone()[0]
    assert sql_prior == sum(map(len, prior.values()))

    old_manifest = OLD / "repair_20261002/protocol/split_manifest.jsonl"
    old_prototype = OLD / "feasibility/prototype_tasks.json"
    old_reviews = OLD / "feasibility/expanded/reviews_grain.jsonl"
    old_qualification = OLD / "feasibility/expanded/temporal_eligible_users.json"
    old_initial_reviews = OLD / "feasibility/reviews_grain.jsonl"
    for p in (old_manifest, old_prototype, old_reviews, old_qualification, old_initial_reviews):
        inputs[str(p)] = sha(p)
    old_split = {r["user_hash"]: r["split"] for r in rows(old_manifest)}
    old_raw = {r["user_id"] for r in rows(old_reviews)}
    old_task = {u for u in old_raw if hashlib.sha256((OLD_SALT+"|"+u).encode()).hexdigest() in old_split}
    assert len(old_split) == len(old_task) == 134
    old_mechanism = {r["user_id"] for r in load(old_prototype)}
    old_union = old_task | old_mechanism
    old_qualified = {r["user_id"] for r in load(old_qualification)}
    old_initial = {r["user_id"] for r in rows(old_initial_reviews)}
    old_exploratory = old_qualified | old_mechanism
    assert old_task <= old_qualified and old_mechanism <= old_qualified <= old_raw
    overlap = {label: {"old_total_accounts": len(users), "in_current_source": len(users & accounts.keys()),
                       "in_current_qualified": len(users & eligible.keys())}
               for label, users in (("preference134", old_task), ("mechanism19", old_mechanism),
                                    ("task_union", old_union), ("qualification165", old_qualified),
                                    ("initial_corpus", old_initial), ("exploratory_union", old_exploratory),
                                    ("raw_corpus", old_raw))}
    overlap["legacy_dev_test_qualified"] = dict(Counter(old_split[hashlib.sha256((OLD_SALT+"|"+u).encode()).hexdigest()] for u in old_task & eligible.keys()))
    overlap["preference_mechanism_intersection"] = len(old_task & old_mechanism)
    overlap["task_union_qualified_exclusion_reasons"] = dict(Counter(reason for u in old_union & accounts.keys() if u not in eligible for reason in accounts[u]["reasons"]))
    labels_path = OLD / "repair_20261002/protocol/evaluation_labels.jsonl"
    inputs[str(labels_path)] = sha(labels_path)
    old_labels = {r["task_id"]: r["target_item"] for r in rows(labels_path)}
    old_task_ids = {r["user_hash"]: r["task_id"] for r in rows(old_manifest)}
    overlap["preference_targets_same_vs_changed"] = dict(Counter(
        "same" if old_labels[old_task_ids[hashlib.sha256((OLD_SALT+"|"+u).encode()).hexdigest()]] == eligible[u]["target_parent_asin"] else "changed"
        for u in old_task & eligible.keys()))

    def group_summary(users):
        counts = Counter(eligible[u]["target_parent_asin"] for u in users)
        return {"accounts": len(users), "old_task_accounts": len(users & old_union),
                "old_exploratory_accounts": len(users & old_exploratory),
                "old_raw_accounts": len(users & old_raw), "target_products": len(counts),
                "positive_history_products": len({p for u in users for p in eligible[u]["prior_positive_parent_asins"]}),
                "history_depth_frequency": dict(sorted(Counter(eligible[u]["prior_positive_product_count"] for u in users).items())),
                "target_crops": dict(sorted(Counter(catalog[eligible[u]["target_parent_asin"]]["crop"] for u in users).items())),
                "target_top1_accounts": max(counts.values()),
                "target_singletons": sum(n == 1 for n in counts.values())}

    plans = {}
    pool = set(eligible)
    for label, forced, excluded, denominator in (
        ("A_force_old_exploratory_development_20pct", pool & old_exploratory, set(), 5),
        ("B_exclude_old_exploratory_20pct", set(), pool & old_exploratory, 5),
        ("C_unrestricted_hash_20pct", set(), set(), 5),
        ("D_exclude_old_raw_corpus_20pct", set(), pool & old_raw, 5),
        ("E_force_old_exploratory_development_30pct", pool & old_exploratory, set(), None),
    ):
        included = pool - excluded
        n_dev = len(included)//denominator if denominator else len(included)*3//10
        assert len(forced) <= n_dev
        dev = forced | set(ordered(included-forced)[:n_dev-len(forced)])
        test = included-dev
        assert not dev & test and dev | test == included
        ds, ts = group_summary(dev), group_summary(test)
        plans[label] = {"included": len(included), "excluded": len(excluded), "forced_development": len(forced),
                        "dev": ds, "test": ts,
                        "shared_target_products": len({eligible[u]["target_parent_asin"] for u in dev}&{eligible[u]["target_parent_asin"] for u in test})}

    crop_rows = []
    for crop in sorted({r["crop"] for r in catalog.values()}):
        crop_rows.append({"crop": crop, "catalog_products": sum(r["crop"] == crop for r in catalog.values()),
                          "history_products": sum(catalog[p]["crop"] == crop for p in hist_products),
                          "target_products": sum(catalog[p]["crop"] == crop for p in targets),
                          "target_accounts": sum(n for p,n in targets.items() if catalog[p]["crop"] == crop)})
    target_years = Counter(datetime.fromtimestamp(a["latest_timestamp_ms"]/1000, timezone.utc).year for a in eligible.values())
    all_history = [r for hist in prior.values() for r in hist]
    raw_count = Counter(r["user_id"] for r in rows(ROOT/review_record["extract_path"]))
    old_paths = {"manifest": str(old_manifest), "prototype": str(old_prototype), "raw_reviews": str(old_reviews),
                 "qualification": str(old_qualification), "initial_reviews": str(old_initial_reviews), "labels": str(labels_path)}
    result = {
        "status": "diagnostic_only_unapproved_no_assignment_output", "salt_proposal": SALT,
        "analysis_code_sha256": sha(__file__),
        "runtime": {"python": sys.version.split()[0], "interpreter": sys.executable},
        "inputs_sha256": inputs, "legacy_paths": old_paths,
        "accepted_component_count": 6, "acceptance_dependency_count": len(acceptance["dependencies_sha256"]),
        "account_exclusions": dict(Counter(reason for a in accounts.values() for reason in a["reasons"])),
        "row_counts": {"raw": sum(raw_count.values()), "clean": len(clean), "valid_text": len(texts),
                       "valid_text_accounts": len({r["review"]["user_id"] for r in texts}),
                       "valid_text_products": len({r["review"]["parent_asin"] for r in texts}),
                       "qualified_raw": sum(raw_count[u] for u in eligible),
                       "qualified_clean": sum(len(rs) for rs in prior.values())+sum(map(len,qualified_latest.values())),
                       "qualified_prior_clean": len(all_history), "qualified_prior_positive_text": sum(map(len,positive.values())),
                       "qualified_prior_valid_text": sum(bool(r["review"]["text"].strip()) for r in all_history),
                       "qualified_prior_below4": sum(r["review"]["rating"] < 4 for r in all_history)},
        "coverage": {"catalog_products": len(catalog), "target_products": len(targets),
                     "positive_history_products": len(hist_products), "all_prior_products": len(seen_products),
                     "history_target_shared_products": len(hist_products.keys() & targets.keys()),
                     "history_target_union_products": len(hist_products.keys() | targets.keys()),
                     "target_only_products": len(targets.keys()-hist_products.keys()),
                     "history_only_products": len(hist_products.keys()-targets.keys())},
        "hist_depth_products": summary([a["prior_positive_product_count"] for a in eligible.values()]),
        "hist_depth_frequency": dict(sorted(Counter(a["prior_positive_product_count"] for a in eligible.values()).items())),
        "hist_reviews_positive": summary([len(positive[u]) for u in eligible]),
        "hist_reviews_all": summary([len(prior[u]) for u in eligible]),
        "seen_products": summary([len(a["seen_parent_asins"]) for a in eligible.values()]),
        "hist_span_days": summary([(eligible[u]["latest_timestamp_ms"]-min(r["timestamp_ms"] for r in positive[u]))/86400000 for u in eligible]),
        "target_time_utc": {"min": min(a["latest_timestamp_ms"] for a in eligible.values()),
                            "max": max(a["latest_timestamp_ms"] for a in eligible.values()),
                            "year_frequency": dict(sorted(target_years.items()))},
        "positive_history_time_ms": {"min": min(r["timestamp_ms"] for rs in positive.values() for r in rs),
                                     "max": max(r["timestamp_ms"] for rs in positive.values() for r in rs)},
        "target_concentration": concentration(targets), "history_concentration": concentration(hist_products),
        "crops": crop_rows, "overlap": overlap, "plans": plans,
        "verification": {"all_input_digests_match": True, "qualified_unique_accounts": len(eligible),
                         "all_account_histories_match": True, "sql_history_depth_matches": True,
                         "sql_prior_clean_rows": sql_prior, "no_assignment_manifest_written": True},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
