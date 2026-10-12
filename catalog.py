"""Metadata-only scope decisions, called through prepare_data.py."""

from collections import Counter
from datetime import datetime, timezone
from functools import cache
import gzip
import hashlib
import json
from pathlib import Path
import re


def pattern(words):
    return compiled_pattern(tuple(words))


@cache
def compiled_pattern(words):
    latin = [re.escape(word) for word in sorted(words, key=len, reverse=True) if word.isascii()]
    other = [re.escape(word) for word in words if not word.isascii()]
    return re.compile("|".join([r"(?<!\w)(?:" + "|".join(latin) + r")(?!\w)", *other]), re.I)


def text_fields(item):
    if isinstance(item.get("title"), str):
        yield "title", item["title"]
    for name in ("features", "description"):
        for index, value in enumerate(item.get(name) or []):
            if isinstance(value, str):
                yield f"{name}[{index}]", value
    for name, value in (item.get("details") or {}).items():
        if isinstance(value, str):
            yield "details." + name, value


def classify(item, config):
    title = item.get("title") or ""
    affirmative = pattern(config["identity_negations"]).split(title, maxsplit=1)[0]
    affirmative = re.sub(r"\b[\w]+[- ]free\b", " ", affirmative, flags=re.I)
    sold_title = re.split(r"\b(?:for|use with|great with)\b", affirmative, maxsplit=1, flags=re.I)[0]
    grain_patterns = {crop: pattern(aliases) for crop, aliases in config["grains"].items()}
    crops = [crop for crop, expression in grain_patterns.items() if expression.search(sold_title)]
    fields = list(text_fields(item))
    discovery_pattern = pattern([alias for aliases in config["grains"].values() for alias in aliases] + config["discovery_only_terms"])
    discovery_evidence = [{"field": field, "text": text} for field, text in fields if discovery_pattern.search(text)]
    discovery_evidence.extend({"field": f"categories[{index}]", "text": part}
                              for index, part in enumerate(item.get("categories") or [])
                              if part in config["primary_categories"] or discovery_pattern.search(part))
    discovery = bool(discovery_evidence)
    if not discovery and not pattern(config["outside_crops"]).search(sold_title):
        reason = ("nonfood" if pattern(config["nonfood"]).search(affirmative) else
                  "excluded_form" if pattern(config["excluded_forms"]).search(sold_title) else "no_scope_evidence")
        return {"status": "excluded", "reason": reason, "crop": None,
                "identity_evidence": [], "composition_evidence": [], "form_evidence": [],
                "discovery_evidence": [],
                "counter_evidence": [{"field": "title", "text": title}] if reason != "no_scope_evidence" else []}
    identity = [{"field": "title", "text": title}] if crops else []
    identity_conflicts = []
    for field, text in fields:
        if field == "title":
            continue
        for fragment in re.split(r"(?<=[.!?])\s*|\n", text):
            if not pattern(config["identity_prefixes"]).match(fragment.strip()):
                continue
            statement = re.sub(r"\b[\w]+[- ]free\b", " ", fragment, flags=re.I)
            negative = bool(pattern(config["identity_negations"]).search(statement))
            if negative:
                statement = ""  # Unresolved negation scope cannot establish positive identity.
            found = [crop for crop, expression in grain_patterns.items() if expression.search(statement)]
            negated = {crop for crop, expression in grain_patterns.items() if expression.search(fragment)} - set(found)
            if pattern(config["outside_crops"]).search(statement) or negated.intersection(crops):
                identity_conflicts.append({"field": field, "text": text})
            if found:
                identity.append({"field": field, "text": text})
                crops = list(dict.fromkeys([*crops, *found]))
    form = [{"field": "title", "text": title}] if pattern(config["forms"]).search(sold_title) else []
    form.extend(evidence for evidence in identity if evidence["field"] != "title" and pattern(config["forms"]).search(evidence["text"]))
    composition = []
    composition_crops = set()
    declarations = set()
    unresolved = False
    component_mix = False
    prefix = pattern(config["composition_prefixes"])
    modifiers = pattern(config["composition_modifiers"])
    for field, text in fields:
        declarations_in_field = []
        active = None
        dedicated = field.lower() in ("details.ingredients", "details.ingredient")
        for fragment in re.split(r"(?<=[.!?])\s*|\n", text):
            if not fragment.strip():
                continue
            fragment = fragment.strip()
            if prefix.match(fragment) or dedicated:
                if active is not None:
                    declarations_in_field.append(active)
                active = fragment
            elif active is not None:
                if pattern(config["composition_end_prefixes"]).match(fragment):
                    declarations_in_field.append(active)
                    active = None
                else:
                    active += "\n" + fragment
        if active is not None:
            declarations_in_field.append(active)
        for fragment in declarations_in_field:
            match = prefix.match(fragment.strip())
            value = fragment.strip()[match.end():] if match else fragment
            value = re.sub(r"^[\s:=-]*(?:is|are)?\s*", "", value, flags=re.I).rstrip(".!?")
            if match and match.group().startswith("100") and pattern(config["percentage_quality_prefixes"]).match(value):
                continue  # Whole-grain/organic quality claims do not disclose all ingredients.
            present = {crop for crop, expression in grain_patterns.items() if expression.search(value)}
            if pattern(config["outside_crops"]).search(value):
                present.add("outside_scope")
            remainder = value
            for expression in grain_patterns.values():
                remainder = expression.sub(" ", remainder)
            remainder = pattern(config["outside_crops"]).sub(" ", remainder)
            remainder = modifiers.sub(" ", remainder)
            remainder = re.sub(r"100\s*%|[\s,;:()\-]", "", remainder)
            unresolved |= not present or bool(remainder)
            component_mix |= len(present) == 1 and not remainder and bool(re.search(r"[,;\n]", value))
            composition_crops.update(present)
            declarations.add(frozenset(present))
            composition.append({"field": field, "text": text})
            if not remainder and len(present) == 1 and pattern(config["forms"]).search(value):
                form.append({"field": field, "text": text})
    counter = []
    categories = item.get("categories") or []
    category_conflict = None
    if categories and (crops or pattern(config["outside_crops"]).search(sold_title)):
        leaf = categories[-1]
        if leaf not in config["generic_categories"] and leaf != "Flours & Meals":
            leaf_crops = {crop for crop, expression in grain_patterns.items() if expression.search(leaf)}
            if (leaf_crops and leaf_crops != set(crops)) or (crops and pattern(config["outside_crops"]).search(leaf)):
                category_conflict = "category_identity_conflict"
                counter = [{"field": f"categories[{len(categories) - 1}]", "text": leaf}]
        if crops and "Flours & Meals" in categories and not pattern(config["excluded_forms"]).search(sold_title):
            category_conflict = "category_form_conflict"
            counter = [{"field": f"categories[{categories.index('Flours & Meals')}]", "text": "Flours & Meals"}]
        if crops and "Unpopped" not in categories and not pattern(config["excluded_forms"]).search(sold_title):
            for index, category in enumerate(categories):
                if category in config["excluded_categories"]:
                    category_conflict = "category_form_conflict"
                    counter.append({"field": f"categories[{index}]", "text": category})
    field_conflicts = [evidence for evidence in identity if evidence["field"] != "title" and pattern(config["excluded_forms"]).search(evidence["text"])]
    processing = [{"field": field, "text": text} for field, text in fields if field != "title"
                  and pattern(config["processing_claims"]).search(re.sub(r"\b(?:not|no|without)\s+\w+", " ", text, flags=re.I))]
    if identity_conflicts:
        status, reason = "pending", "field_identity_conflict"
        counter = identity_conflicts
    elif category_conflict:
        status, reason = "pending", category_conflict
    elif pattern(config["nonfood"]).search(affirmative):
        status, reason = "excluded", "nonfood"
        counter = [{"field": "title", "text": title}]
    elif pattern(config["excluded_forms"]).search(sold_title):
        status, reason = "excluded", "excluded_form"
        counter = [{"field": "title", "text": title}]
    elif pattern(config["outside_crops"]).search(sold_title) and not crops:
        status, reason = "excluded", "outside_crop"
        counter = [{"field": "title", "text": title}]
    elif not crops:
        status, reason = ("pending", "weak_identity") if discovery else ("excluded", "no_scope_evidence")
    elif field_conflicts:
        status, reason = "pending", "field_form_conflict"
        counter = field_conflicts
    elif len(declarations) > 1:
        status, reason = "pending", "composition_declaration_conflict"
        counter = composition
    elif len(composition_crops) > 1 and not unresolved:
        status, reason = "excluded", "mixed_composition"
    elif component_mix:
        status, reason = "pending", "component_mix_not_resolved"
        counter = composition
    elif pattern(config["ambiguous_forms"]).search(sold_title) or processing:
        status, reason = "pending", "ambiguous_processing_or_mix"
        counter = processing or [{"field": "title", "text": title}]
    elif not form:
        status, reason = "pending", "form_not_verified"
    elif not composition:
        status, reason = "pending", "missing_composition"
    elif unresolved or len(crops) != 1 or composition_crops != set(crops):
        status, reason = "pending", "unresolved_composition"
    else:
        status, reason = "included", "identity_and_composition"
    return {"status": status, "reason": reason, "crop": crops[0] if len(crops) == 1 else None,
            "identity_evidence": identity, "composition_evidence": composition,
            "discovery_evidence": discovery_evidence,
            "counter_evidence": counter, "form_evidence": form}


def build_catalog(source_record, scope_config, root):
    source = json.loads(source_record.read_text(encoding="utf-8"))
    config = json.loads(scope_config.read_text(encoding="utf-8"))
    if source["stage"] != "metadata" or source["status"] != "diagnostic_complete" or source["error"] or not source["scan"]["gzip_verified"]:
        raise ValueError("catalog requires complete verified metadata")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", config["version"]):
        raise ValueError("scope version must be a single safe filename component")
    raw = (source_record.resolve().parent.parents[1] / source["raw_path"]).resolve()
    if Path(__file__).resolve().parent not in raw.parents:
        raise ValueError("metadata raw path must remain inside the Thesis project")
    with raw.open("rb") as stream:
        source_sha = hashlib.file_digest(stream, "sha256").hexdigest()
    if source_sha != source["download"]["sha256"]:
        raise ValueError("metadata checksum differs from the source record")
    scope_sha = hashlib.sha256(scope_config.read_bytes()).hexdigest()
    record = root / "records" / "catalog" / (config["version"] + ".json")
    if record.exists():
        previous = json.loads(record.read_text(encoding="utf-8"))
        if previous["source_sha256"] != source_sha or previous["scope_sha256"] != scope_sha:
            raise ValueError("changed source or rules require a new catalog version")
    parents = {}
    conflicts = set()
    rows = 0
    with gzip.open(raw, "rb") as stream:
        for rows, line in enumerate(stream, 1):
            item = json.loads(line)
            signature = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()
            parent = item["parent_asin"]
            if parent not in parents:
                parents[parent] = (signature, [rows])
            else:
                previous, references = parents[parent]
                references.append(rows)
                if previous != signature:
                    conflicts.add(parent)
    if rows != source["scan"]["lines"] or rows != source["scan"]["records"] or not rows:
        raise ValueError("metadata scan count differs from the source record")
    directory = root / "data" / "catalog" / config["version"]
    directory.mkdir(parents=True, exist_ok=True)
    catalog_path = directory / "catalog.jsonl"
    audit_path = directory / "audit.jsonl"
    pending_path = directory / "pending.jsonl"
    counts = Counter(included=0, excluded=0, pending=0)
    reasons = Counter()
    with gzip.open(raw, "rb") as stream, catalog_path.open("w", encoding="utf-8", newline="\n") as catalog, audit_path.open("w", encoding="utf-8", newline="\n") as audit, pending_path.open("w", encoding="utf-8", newline="\n") as pending:
        for line_number, line in enumerate(stream, 1):
            item = json.loads(line)
            decision = {"parent_asin": item["parent_asin"], **classify(item, config),
                        "source_line": line_number, "source_lines": parents[item["parent_asin"]][1],
                        "source_sha256": source_sha, "scope_version": config["version"]}
            if item["parent_asin"] in conflicts:
                decision.update(status="pending", reason="parent_metadata_conflict")
            first = decision["source_lines"][0] == line_number
            if first:
                counts[decision["status"]] += 1
                reasons[decision["reason"]] += 1
            audit.write(json.dumps(decision, ensure_ascii=False, sort_keys=True) + "\n")
            if decision["status"] == "included" and first:
                catalog.write(json.dumps({**decision, "metadata": item}, ensure_ascii=False, sort_keys=True) + "\n")
            elif decision["status"] == "pending":
                pending.write(json.dumps({**decision, "metadata": item}, ensure_ascii=False, sort_keys=True) + "\n")
    report = {"stage": "catalog", "status": "catalog_complete", "counts": counts,
              "reasons": reasons,
              "scan": {"rows": rows, "unique_parents": len(parents), "gzip_verified": True,
                       "duplicate_parent_rows": rows - len(parents), "conflicting_parents": len(conflicts)},
              "scope_version": config["version"], "source_sha256": source_sha,
              "scope_sha256": scope_sha,
              "catalog_path": catalog_path.relative_to(root).as_posix(),
              "audit_path": audit_path.relative_to(root).as_posix(),
              "pending_path": pending_path.relative_to(root).as_posix(),
              "generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "producer_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                  for name in ("catalog.py", "prepare_data.py")},
              "model_input_status": "not_released", "sample_sufficiency": "not_determined",
              "formal_package_status": "not_built"}
    for name, path in (("catalog", catalog_path), ("audit", audit_path), ("pending", pending_path)):
        with path.open("rb") as stream:
            report[name + "_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    record.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    record.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0
