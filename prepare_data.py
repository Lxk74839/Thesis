"""Single public entry for staged source acquisition and diagnostics."""

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
from http.client import HTTPException
import json
from pathlib import Path
import re
import urllib.request
import zlib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=["metadata", "reviews", "catalog", "review_extract", "review_clean"])
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--metadata-record", type=Path)
    parser.add_argument("--scope-config", type=Path)
    parser.add_argument("--catalog-record", type=Path)
    parser.add_argument("--previous-catalog-record", type=Path)
    parser.add_argument("--review-record", type=Path)
    parser.add_argument("--cleaning-config", type=Path)
    args = parser.parse_args()
    root = args.output_root.resolve()
    project = Path(__file__).resolve().parent
    if root != project and project not in root.parents:
        parser.error("output-root must remain inside the Thesis project")
    if args.stage == "review_clean":
        if args.catalog_record is None or args.review_record is None or args.cleaning_config is None:
            parser.error("review_clean requires catalog-record, review-record and cleaning-config")
        from review_cleaning import clean_reviews
        try:
            return clean_reviews(args.catalog_record, args.review_record, args.cleaning_config, root)
        except (OSError, ValueError) as exc:
            print(json.dumps({"stage": "review_clean", "status": "cleaning_incomplete",
                              "error": {"kind": type(exc).__name__, "message": str(exc)}}))
            return 2
    if args.stage == "review_extract":
        if args.catalog_record is None or args.review_record is None:
            parser.error("review_extract requires catalog-record and review-record")
        from review_diagnostics import extract_reviews
        try:
            return extract_reviews(args.catalog_record, args.review_record, root)
        except (OSError, EOFError, zlib.error, ValueError) as exc:
            print(json.dumps({"stage": "review_extract", "status": "extraction_incomplete",
                              "error": {"kind": type(exc).__name__, "message": str(exc)}}))
            return 2
    if args.stage == "catalog":
        if args.metadata_record is None or args.scope_config is None:
            parser.error("catalog requires metadata-record and scope-config")
        from catalog import build_catalog
        try:
            return build_catalog(args.metadata_record, args.scope_config, root, args.previous_catalog_record)
        except (OSError, EOFError, zlib.error, ValueError) as exc:
            print(json.dumps({"stage": "catalog", "status": "catalog_incomplete",
                              "error": {"kind": type(exc).__name__, "message": str(exc)}}))
            return 2
    if args.source_manifest is None:
        parser.error("source acquisition requires source-manifest")
    source = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    source_id = source["id"]
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", source_id):
        parser.error("source id must be a single safe filename component")
    raw = root / "data" / "raw" / (source_id + ".partial")
    record = root / "records" / "sources" / (source_id + ".json")
    diagnostic = root / "data" / "diagnostics" / (source_id + ".errors.jsonl")
    raw.parent.mkdir(parents=True, exist_ok=True)
    record.parent.mkdir(parents=True, exist_ok=True)
    diagnostic.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(b"")
    diagnostic.write_text("", encoding="utf-8")
    digest = hashlib.sha256()
    download = {"bytes": 0}
    fields = {
        name: {"present": 0, "empty": 0, "types": Counter()}
        for name in source["documented_fields"]
    }
    scan = {"lines": 0, "records": 0, "first_parent_asin": None,
            "last_parent_asin": None, "gzip_verified": False,
            "invalid_json_rows": 0, "non_object_rows": 0, "invalid_parent_rows": 0,
            "unique_parents": 0, "duplicate_parent_rows": 0}
    parents = set()
    metadata_parents = set()
    association = {"matched_review_rows": 0, "unmatched_review_rows": 0,
                   "asin_differs_from_parent_rows": 0} if args.stage == "reviews" else None
    time = {"field": "timestamp", "unit": source.get("time_unit"), "timezone": "UTC",
            "min_raw": None, "max_raw": None, "min_utc": None, "max_utc": None,
            "min_line": None, "max_line": None, "valid_rows": 0,
            "invalid_reasons": Counter(),
            "nonzero_millisecond_rows": 0} if args.stage == "reviews" else None
    review_diagnostics = {"invalid_rating_rows": 0, "invalid_asin_rows": 0,
                          "invalid_user_rows": 0, "invalid_text_rows": 0,
                          "anomalous_records": 0} if args.stage == "reviews" else None
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    error = None
    try:
        if args.stage == "reviews":
            if source.get("time_unit") != "milliseconds":
                raise ValueError("reviews require the documented time_unit milliseconds")
            if args.metadata_record is None:
                raise ValueError("reviews require a metadata source record")
            metadata_record = json.loads(args.metadata_record.read_text(encoding="utf-8"))
            if metadata_record["stage"] != "metadata" or metadata_record["status"] != "diagnostic_complete":
                raise ValueError("reviews require a complete, verified metadata source")
            metadata_raw = (args.metadata_record.resolve().parent.parents[1] / metadata_record["raw_path"]).resolve()
            if project not in metadata_raw.parents:
                raise ValueError("metadata raw path must remain inside the Thesis project")
            with metadata_raw.open("rb") as metadata_bytes:
                metadata_sha256 = hashlib.file_digest(metadata_bytes, "sha256").hexdigest()
            if metadata_sha256 != metadata_record["download"]["sha256"]:
                raise ValueError("metadata checksum differs from its verified source record")
            with gzip.open(metadata_raw, "rb") as metadata_stream:
                metadata_parents = {json.loads(line)["parent_asin"] for line in metadata_stream}
            association["metadata_source_sha256"] = metadata_sha256
        with urllib.request.urlopen(source["url"], timeout=60) as response:
            download["resolved_url"] = response.geturl()
            download["headers"] = dict(response.headers)
            download["http_status"] = getattr(response, "status", None)
            if download["http_status"] not in (None, 200) or response.headers.get("Content-Range"):
                raise ValueError("partial HTTP response is not a complete source")
            size = response.headers.get("Content-Length")
            download["content_length"] = int(size) if size is not None else None
            with raw.open("wb") as destination:
                while chunk := response.read(1024 * 1024):
                    destination.write(chunk)
                    digest.update(chunk)
                    download["bytes"] += len(chunk)
            if size is not None and download["bytes"] != int(size):
                raise ValueError("download byte count differs from Content-Length")
        downloaded = raw.with_name(source_id + "-" + digest.hexdigest() + ".jsonl.gz")
        raw.replace(downloaded)
        raw = downloaded
        with gzip.open(raw, "rb") as stream, diagnostic.open("w", encoding="utf-8") as issues:
            for line in stream:
                scan["lines"] += 1
                try:
                    item = json.loads(line)
                except ValueError as exc:
                    scan["invalid_json_rows"] += 1
                    issues.write(json.dumps({"line": scan["lines"],
                                             "reason": type(exc).__name__}) + "\n")
                    continue
                if not isinstance(item, dict):
                    scan["non_object_rows"] += 1
                    issues.write(json.dumps({"line": scan["lines"],
                                             "reason": "non_object"}) + "\n")
                    continue
                scan["records"] += 1
                parent = item.get("parent_asin")
                if scan["records"] == 1:
                    scan["first_parent_asin"] = parent
                scan["last_parent_asin"] = parent
                if not isinstance(parent, str) or not parent.strip():
                    scan["invalid_parent_rows"] += 1
                    issues.write(json.dumps({"line": scan["lines"],
                                             "reason": "invalid_parent_asin"}) + "\n")
                elif parent in parents and args.stage == "metadata":
                    scan["duplicate_parent_rows"] += 1
                else:
                    parents.add(parent)
                if association is not None and isinstance(parent, str) and parent.strip():
                    key = "matched_review_rows" if parent in metadata_parents else "unmatched_review_rows"
                    association[key] += 1
                    asin = item.get("asin")
                    if isinstance(asin, str) and asin.strip() and asin != parent:
                        association["asin_differs_from_parent_rows"] += 1
                if time is not None:
                    reasons = []
                    timestamp = item.get("timestamp")
                    reason = ("missing" if "timestamp" not in item else
                              "null" if timestamp is None else
                              "not_integer" if type(timestamp) is not int else None)
                    if reason is None:
                        try:
                            utc = epoch + timedelta(milliseconds=timestamp)
                        except OverflowError:
                            reason = "unrepresentable"
                    if reason:
                        time["invalid_reasons"][reason] += 1
                        reasons.append("timestamp_" + reason)
                    else:
                        time["valid_rows"] += 1
                        time["nonzero_millisecond_rows"] += timestamp % 1000 != 0
                        for boundary in ("min", "max"):
                            previous = time[boundary + "_raw"]
                            if previous is None or (timestamp < previous if boundary == "min" else timestamp > previous):
                                time[boundary + "_raw"] = timestamp
                                time[boundary + "_utc"] = utc.isoformat(timespec="milliseconds")
                                time[boundary + "_line"] = scan["lines"]
                    rating = item.get("rating")
                    invalid = {
                        "rating": type(rating) not in (int, float) or not 1 <= rating <= 5,
                        "asin": not isinstance(item.get("asin"), str) or not item["asin"].strip(),
                        "user": not isinstance(item.get("user_id"), str) or not item["user_id"].strip(),
                        "text": not isinstance(item.get("text"), str),
                    }
                    for name, bad in invalid.items():
                        if bad:
                            review_diagnostics["invalid_" + name + "_rows"] += 1
                            reasons.append("invalid_" + name)
                    if not isinstance(parent, str) or not parent.strip():
                        reasons.append("invalid_parent_asin")
                    elif parent not in metadata_parents:
                        reasons.append("unmatched_parent_asin")
                    if reasons:
                        review_diagnostics["anomalous_records"] += 1
                        issues.write(json.dumps({"line": scan["lines"], "reasons": reasons}) + "\n")
                for name, value in item.items():
                    field = fields.setdefault(name, {"present": 0, "empty": 0, "types": Counter()})
                    field["present"] += 1
                    field["types"]["null" if value is None else type(value).__name__] += 1
                    if ((isinstance(value, str) and not value.strip()) or
                            (isinstance(value, (list, dict)) and not value)):
                        field["empty"] += 1
        scan["gzip_verified"] = True
        if scan["lines"] == 0:
            raise ValueError("source contains no records")
    except (OSError, EOFError, HTTPException, zlib.error, ValueError) as exc:
        error = {"kind": type(exc).__name__, "message": str(exc)}
    download["sha256"] = digest.hexdigest()
    scan["unique_parents"] = len(parents)
    if association is not None:
        association["unmatched_unique_parents"] = len(parents - metadata_parents)
        association["metadata_parents_with_reviews"] = len(parents & metadata_parents)
        association["metadata_parents_without_reviews"] = len(metadata_parents - parents)
    for field in fields.values():
        field["missing"] = scan["records"] - field["present"]
    needs_review = (scan["invalid_json_rows"] + scan["non_object_rows"]
                    + scan["invalid_parent_rows"]) > 0 or bool(
                        review_diagnostics and review_diagnostics["anomalous_records"])
    report = {
        "stage": args.stage,
        "status": "source_incomplete" if error else
                  ("needs_review" if needs_review else "diagnostic_complete"),
        "formal_package_status": "not_built",
        "source": source,
        "download": download,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_path": raw.relative_to(root).as_posix(),
        "record_path": record.relative_to(root).as_posix(),
        "diagnostic_path": diagnostic.relative_to(root).as_posix(),
        "scan": scan,
        "association": association,
        "time": time,
        "review_diagnostics": review_diagnostics,
        "fields": fields,
        "error": error,
    }
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    record.write_text(text, encoding="utf-8")
    print(text, end="")
    return 2 if error or needs_review else 0


if __name__ == "__main__":
    raise SystemExit(main())
