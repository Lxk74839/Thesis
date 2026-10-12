"""Raw parent-review extraction and provisional diagnostics through the public CLI."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import unicodedata


VERSION = "review-diagnostics-1.0.0"


def valid_time(value):
    if type(value) is not int:
        return None
    try:
        return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=value)
    except OverflowError:
        return None


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def checked_file(record, relative, expected):
    path = (record.resolve().parent.parents[1] / relative).resolve()
    if Path(__file__).resolve().parent not in path.parents:
        raise ValueError("source path must remain inside the Thesis project")
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise ValueError("checksum differs from the verified record")
    return path


def review_groups(rows):
    objects = defaultdict(list)
    modes = {"raw_quad": defaultdict(list), "nfc_strip_quad": defaultdict(list), "same_product_equal_time": defaultdict(list)}
    for number, row in rows:
        objects[canonical(row)].append(number)
        if (isinstance(row.get("user_id"), str) and row["user_id"].strip()
                and valid_time(row.get("timestamp")) is not None):
            identity = (row["user_id"], row["parent_asin"], row["timestamp"])
            for mode, quads in modes.items():
                if mode == "same_product_equal_time":
                    quads[identity].append((number, row))
                    continue
                if not isinstance(row.get("text"), str):
                    continue
                text = unicodedata.normalize("NFC", row["text"]).strip() if mode == "nfc_strip_quad" else row["text"]
                quads[(*identity, text)].append((number, row))
    details = []
    summaries = {}
    for mode, quads in modes.items():
        summary = Counter(duplicate_groups=0, duplicate_member_rows=0, duplicate_excess_rows=0,
                          conflict_groups=0, conflict_member_rows=0,
                          ungroupable_rows=len(rows) - sum(map(len, quads.values())))
        for members in quads.values():
            fields = set().union(*(row.keys() for _, row in members)) - {"user_id", "parent_asin", "timestamp"}
            if mode != "same_product_equal_time":
                fields.discard("text")
            conflicts = sorted(field for field in fields if len({canonical([field in row, row.get(field)]) for _, row in members}) > 1)
            if len(members) > 1:
                summary["duplicate_groups"] += 1
                summary["duplicate_member_rows"] += len(members)
                summary["duplicate_excess_rows"] += len(members) - 1
            if conflicts:
                summary["conflict_groups"] += 1
                summary["conflict_member_rows"] += len(members)
            details.append({"kind": mode, "source_lines": [number for number, _ in members], "conflicting_fields": conflicts})
        summaries[mode] = summary
    exact = [members for members in objects.values() if len(members) > 1]
    details.extend({"kind": "exact_object", "source_lines": members, "conflicting_fields": []} for members in exact)
    return {"exact_object_duplicate_groups": len(exact), "exact_object_excess_rows": sum(len(members) - 1 for members in exact),
            **summaries}, details


def counts(rows):
    return {"reviews": len(rows), "products_with_reviews": len({row["parent_asin"] for _, row in rows}),
            "unique_accounts": len({row["user_id"] for _, row in rows if isinstance(row.get("user_id"), str) and row["user_id"].strip()})}


def cleaning_diagnostics(rows, groups, products, documented_fields):
    fields = {name: {"missing": 0, "empty": 0, "types": Counter()} for name in documented_fields}
    failures = {"nonblank_text": set(), "valid_rating": set(), "valid_time": set(), "valid_identifiers": set()}
    time_reasons = Counter()
    for number, row in rows:
        for field, summary in fields.items():
            if field not in row:
                summary["missing"] += 1
            else:
                value = row[field]
                summary["types"][type(value).__name__] += 1
                summary["empty"] += value in (None, "", [], {})
        if not isinstance(row.get("text"), str) or not row["text"].strip():
            failures["nonblank_text"].add(number)
        rating = row.get("rating")
        if type(rating) not in (int, float) or not 1 <= rating <= 5:
            failures["valid_rating"].add(number)
        if valid_time(row.get("timestamp")) is None:
            failures["valid_time"].add(number)
            time_reasons["missing" if "timestamp" not in row else "null" if row["timestamp"] is None else
                         "not_integer" if type(row["timestamp"]) is not int else "unrepresentable"] += 1
        if any(not isinstance(row.get(key), str) or not row[key].strip() for key in ("user_id", "asin")):
            failures["valid_identifiers"].add(number)
    drops = {name: set(numbers) for name, numbers in failures.items()}
    drops.update(exact_object_dedup=set(), raw_quad_conflict_quarantine=set(), nfc_strip_quad_safe_dedup=set(), equal_time_conflict_quarantine=set())
    for group in groups:
        members = group["source_lines"]
        if group["kind"] == "exact_object":
            drops["exact_object_dedup"].update(members[1:])
        elif group["kind"] == "raw_quad" and group["conflicting_fields"]:
            drops["raw_quad_conflict_quarantine"].update(members)
        elif group["kind"] == "nfc_strip_quad":
            drops["nfc_strip_quad_safe_dedup"].update(members if group["conflicting_fields"] else members[1:])
        elif group["kind"] == "same_product_equal_time" and group["conflicting_fields"]:
            drops["equal_time_conflict_quarantine"].update(members)
    invalid = set().union(*failures.values())
    drops["combined_raw"] = invalid | drops["exact_object_dedup"] | drops["raw_quad_conflict_quarantine"]
    drops["combined_nfc"] = invalid | drops["nfc_strip_quad_safe_dedup"]
    baseline = counts(rows)
    scenarios = {}
    for name, removed in drops.items():
        kept = counts([(number, row) for number, row in rows if number not in removed])
        scenarios[name] = {"kept_reviews": kept["reviews"], "lost_reviews": baseline["reviews"] - kept["reviews"],
                           "kept_products_with_reviews": kept["products_with_reviews"],
                           "lost_products_with_reviews": baseline["products_with_reviews"] - kept["products_with_reviews"],
                           "kept_accounts": kept["unique_accounts"], "lost_accounts": baseline["unique_accounts"] - kept["unique_accounts"],
                           "catalog_products_retained": len(products)}
    quality = {"fields": fields, "invalid_rating_rows": len(failures["valid_rating"]),
               "invalid_time_rows": len(failures["valid_time"]), "invalid_time_reasons": time_reasons,
               "invalid_identifier_rows": len(failures["valid_identifiers"]),
               "invalid_text_rows": sum(not isinstance(row.get("text"), str) for _, row in rows),
               "empty_text_rows": sum(isinstance(row.get("text"), str) and not row["text"].strip() for _, row in rows),
               "rating_values": Counter(canonical(row.get("rating")) for _, row in rows)}
    audit = [{"source_line": number, "failed_checks": [name for name, failed in failures.items() if number in failed],
              "candidate_removed_by": [name for name, removed in drops.items() if number in removed]} for number, _ in rows]
    return quality, {"approval": "not_approved", "scenarios": scenarios}, audit


def positive_text(row):
    return (type(row.get("rating")) in (int, float) and 4 <= row["rating"] <= 5
            and isinstance(row.get("text"), str) and bool(row["text"].strip())
            and isinstance(row.get("asin"), str) and bool(row["asin"].strip()))


def history_diagnostics(rows, groups):
    users = defaultdict(list)
    for number, row in rows:
        if isinstance(row.get("user_id"), str) and row["user_id"].strip():
            users[row["user_id"]].append((number, row))
    distributions = {name: Counter() for name in ("reviews_per_account", "distinct_products_per_account",
                                                 "strict_prior_reviews", "strict_prior_products", "latest_unseen_products")}
    summary = Counter(accounts_with_invalid_time=0, accounts_without_valid_time=0,
                      multiple_latest_parent_accounts=0, unique_latest_unseen_accounts_with_known_time=0)
    audit = []
    candidate = {"approval": "not_approved", "rating_min": 4, "minimum_prior_products": None,
                 "potential_accounts": 0, "prior_positive_products": Counter(), "excluded_reasons": Counter()}
    conflicted = {number for group in groups if group["kind"] in ("raw_quad", "same_product_equal_time") and group["conflicting_fields"] for number in group["source_lines"]}
    for user, values in users.items():
        distributions["reviews_per_account"][str(len(values))] += 1
        distributions["distinct_products_per_account"][str(len({row["parent_asin"] for _, row in values}))] += 1
        timed = [(number, row) for number, row in values if valid_time(row.get("timestamp")) is not None]
        unknown = len(values) - len(timed)
        summary["accounts_with_invalid_time"] += bool(unknown)
        if not timed:
            summary["accounts_without_valid_time"] += 1
            candidate["excluded_reasons"]["unreliable_time"] += 1
            audit.append({"user_id": user, "latest_timestamp": None, "raw_review_count": len(values),
                          "unknown_time_rows": unknown, "manuscript_candidate_status": "unreliable_time"})
            continue
        latest = max(row["timestamp"] for _, row in timed)
        prior = [(number, row) for number, row in timed if row["timestamp"] < latest]
        latest_rows = [(number, row) for number, row in timed if row["timestamp"] == latest]
        latest_parents = {row["parent_asin"] for _, row in latest_rows}
        seen = {row["parent_asin"] for _, row in prior}
        unseen = latest_parents - seen
        distributions["strict_prior_reviews"][str(len(prior))] += 1
        distributions["strict_prior_products"][str(len(seen))] += 1
        distributions["latest_unseen_products"][str(len(unseen))] += 1
        summary["multiple_latest_parent_accounts"] += len(latest_parents) > 1
        summary["unique_latest_unseen_accounts_with_known_time"] += not unknown and len(latest_parents) == 1 and bool(unseen)
        reason = ("unreliable_time" if unknown else "multiple_latest_parents" if len(latest_parents) != 1 else
                  "latest_fact_conflict" if len({canonical(row) for _, row in latest_rows}) > 1 else
                  "latest_seen_product" if not unseen else
                  "latest_not_positive" if not positive_text(latest_rows[0][1]) else None)
        positive_parents = {row["parent_asin"] for number, row in prior if number not in conflicted and positive_text(row)}
        if reason:
            candidate["excluded_reasons"][reason] += 1
        else:
            candidate["potential_accounts"] += 1
            candidate["prior_positive_products"][str(len(positive_parents))] += 1
        audit.append({"user_id": user, "latest_timestamp": latest, "raw_review_count": len(values),
                      "unknown_time_rows": unknown, "strict_prior_review_count": len(prior),
                      "strict_prior_product_count": len(seen), "latest_parent_count": len(latest_parents),
                      "latest_unseen_parent_count": len(unseen), "prior_positive_product_count": len(positive_parents),
                      "manuscript_candidate_status": reason or "conditional_potential"})
    return {**distributions, **summary, "qualification_status": "not_determined", "manuscript_positive_candidate": candidate,
            "basis": "All selected raw interactions; time distributions use representable timestamps. Unknown-time accounts cannot establish a reliable target."}, audit


def extract_reviews(catalog_record, review_record, root):
    catalog = json.loads(catalog_record.read_text("utf-8"))
    source = json.loads(review_record.read_text("utf-8"))
    if catalog["stage"] != "catalog" or catalog["status"] != "catalog_complete":
        raise ValueError("extraction requires an accepted complete catalog")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", catalog["scope_version"]):
        raise ValueError("catalog version must be a single safe filename component")
    if source["stage"] != "reviews" or source["status"] not in ("diagnostic_complete", "needs_review") or source["error"] or not source["scan"]["gzip_verified"]:
        raise ValueError("extraction requires a fully acquired and gzip-verified review source")
    if source["time"]["unit"] != "milliseconds" or source["source"].get("time_unit") != "milliseconds":
        raise ValueError("reviews require the documented time unit milliseconds")
    if source["association"]["metadata_source_sha256"] != catalog["source_sha256"]:
        raise ValueError("review association and catalog require the same metadata source")
    catalog_path = checked_file(catalog_record, catalog["catalog_path"], catalog["catalog_sha256"])
    catalog_rows = [json.loads(line) for line in catalog_path.read_text("utf-8").splitlines()]
    products = {row["parent_asin"]: 0 for row in catalog_rows}
    if len(products) != len(catalog_rows) or len(products) != catalog["counts"]["included"] or any(row["status"] != "included" for row in catalog_rows):
        raise ValueError("catalog identities or counts are inconsistent")
    raw = checked_file(review_record, source["raw_path"], source["download"]["sha256"])
    record = root / "records/reviews" / (catalog["scope_version"] + "-" + VERSION + ".json")
    producer = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ("prepare_data.py", "review_diagnostics.py")}
    if record.exists():
        previous = json.loads(record.read_text("utf-8"))
        if previous["catalog_sha256"] != catalog["catalog_sha256"] or previous["source_sha256"] != source["download"]["sha256"] or previous["producer_sha256"] != producer:
            raise ValueError("changed source or implementation requires a new diagnostic version")
    directory = root / "data/reviews" / catalog["scope_version"] / VERSION
    directory.mkdir(parents=True, exist_ok=True)
    extract_path = directory / "raw-matched.jsonl"
    references_path = directory / "source-references.jsonl"
    groups_path = directory / "groups.jsonl"
    errors_path = directory / "source-errors.jsonl"
    cleaning_path = directory / "candidate-cleaning-audit.jsonl"
    history_path = directory / "account-history-diagnostics.jsonl"
    rows = []
    scan = Counter(lines=0, records=0, matched_rows=0, other_parent_rows=0,
                   invalid_json_rows=0, non_object_rows=0, invalid_parent_rows=0)
    with gzip.open(raw, "rb") as stream, extract_path.open("wb") as destination, references_path.open("w", encoding="utf-8", newline="\n") as references, errors_path.open("w", encoding="utf-8", newline="\n") as errors:
        for number, line in enumerate(stream, 1):
            scan["lines"] += 1
            try:
                item = json.loads(line)
            except ValueError:
                scan["invalid_json_rows"] += 1
                errors.write(canonical({"source_line": number, "reason": "invalid_json"}) + "\n")
                continue
            if not isinstance(item, dict):
                scan["non_object_rows"] += 1
                errors.write(canonical({"source_line": number, "reason": "non_object"}) + "\n")
                continue
            scan["records"] += 1
            parent = item.get("parent_asin")
            if not isinstance(parent, str) or not parent.strip():
                scan["invalid_parent_rows"] += 1
                errors.write(canonical({"source_line": number, "reason": "invalid_parent_asin"}) + "\n")
            elif parent in products:
                destination.write(line)
                products[parent] += 1
                scan["matched_rows"] += 1
                rows.append((number, item))
                references.write(json.dumps({"selected_row": scan["matched_rows"], "source_line": number,
                                             "line_sha256": hashlib.sha256(line).hexdigest()}, sort_keys=True) + "\n")
            else:
                scan["other_parent_rows"] += 1
    scan["gzip_verified"] = True
    if scan["lines"] != source["scan"]["lines"] or scan["records"] != source["scan"]["records"]:
        raise ValueError("full review scan count differs from the source record")
    complete = not any(scan[name] for name in ("invalid_json_rows", "non_object_rows", "invalid_parent_rows"))
    duplicates, groups = review_groups(rows)
    groups_path.write_text("".join(canonical(group) + "\n" for group in groups), "utf-8")
    quality, cleaning, cleaning_audit = cleaning_diagnostics(rows, groups, products, source["source"]["documented_fields"])
    cleaning_path.write_text("".join(canonical(row) + "\n" for row in cleaning_audit), "utf-8")
    history, history_audit = history_diagnostics(rows, groups)
    history_path.write_text("".join(canonical(row) + "\n" for row in history_audit), "utf-8")
    timestamps = [row["timestamp"] for _, row in rows if valid_time(row.get("timestamp")) is not None]
    time = {"unit": "milliseconds", "timezone": "UTC", "valid_rows": len(timestamps),
            "cutoff": None, "cutoff_approval": "not_approved"}
    for name, value in (("min", min(timestamps, default=None)), ("max", max(timestamps, default=None))):
        time[name + "_raw"] = value
        time[name + "_utc"] = valid_time(value).isoformat(timespec="milliseconds") if value is not None else None
    report = {"stage": "review_extract", "status": "extraction_complete" if complete else "extraction_incomplete", "scan": scan,
              "scope_version": catalog["scope_version"], "diagnostic_version": VERSION,
              "source_sha256": source["download"]["sha256"], "catalog_sha256": catalog["catalog_sha256"],
              "producer_sha256": producer, "source_status": source["status"],
              "source_record_sha256": hashlib.sha256(review_record.read_bytes()).hexdigest(),
              "catalog_record_sha256": hashlib.sha256(catalog_record.read_bytes()).hexdigest(),
              "time": time,
              "product_review_counts": products,
              "raw": {**counts(rows), "catalog_products": len(products), "products_without_reviews": sum(value == 0 for value in products.values())},
              "quality": quality, "candidate_cleaning": cleaning,
              "history": history,
              "duplicates": duplicates, "cleaning_status": "rules_not_approved",
              "candidate_normalization": {"approval": "not_approved", "form": "NFC", "strip_edges": True,
                                          "unicode_version": unicodedata.unidata_version,
                                          "changed_text_rows": sum(isinstance(row.get("text"), str) and row["text"] != unicodedata.normalize("NFC", row["text"]).strip() for _, row in rows)},
              "formal_clean_status": "not_built", "formal_package_status": "not_built",
              "model_input_status": "not_released", "sample_sufficiency": "not_determined",
              "generated_at_utc": datetime.now(timezone.utc).isoformat()}
    for name, path in (("extract", extract_path), ("references", references_path), ("groups", groups_path), ("errors", errors_path), ("cleaning", cleaning_path), ("history", history_path)):
        report[name + "_path"] = path.relative_to(root).as_posix()
        with path.open("rb") as stream:
            report[name + "_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    record.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    record.write_text(text, "utf-8")
    print(text, end="")
    return 0 if complete else 2
