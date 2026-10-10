"""Single public entry for staged data preparation; currently metadata only."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import urllib.request
import zlib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=["metadata"])
    parser.add_argument("--source-manifest", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    root = args.output_root.resolve()
    project = Path(__file__).resolve().parent
    if root != project and project not in root.parents:
        parser.error("output-root must remain inside the Thesis project")
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
    error = None
    try:
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
                elif parent in parents:
                    scan["duplicate_parent_rows"] += 1
                else:
                    parents.add(parent)
                for name, value in item.items():
                    field = fields.setdefault(name, {"present": 0, "empty": 0, "types": Counter()})
                    field["present"] += 1
                    field["types"]["null" if value is None else type(value).__name__] += 1
                    if ((isinstance(value, str) and not value.strip()) or
                            (isinstance(value, (list, dict)) and not value)):
                        field["empty"] += 1
        scan["gzip_verified"] = True
        if scan["lines"] == 0:
            raise ValueError("metadata source contains no records")
    except (OSError, EOFError, zlib.error, ValueError) as exc:
        error = {"kind": type(exc).__name__, "message": str(exc)}
    download["sha256"] = digest.hexdigest()
    scan["unique_parents"] = len(parents)
    for field in fields.values():
        field["missing"] = scan["records"] - field["present"]
    needs_review = (scan["invalid_json_rows"] + scan["non_object_rows"]
                    + scan["invalid_parent_rows"]) > 0
    report = {
        "stage": "metadata",
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
        "fields": fields,
        "error": error,
    }
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    record.write_text(text, encoding="utf-8")
    print(text, end="")
    return 2 if error or needs_review else 0


if __name__ == "__main__":
    raise SystemExit(main())
