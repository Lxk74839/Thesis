"""Read-only scope comparison; all rules below are proposals pending D1/D3 approval.

This internal diagnostic produces no formal product catalog and is not a second
public data preparation interface. Run only with the Thesis prefix.
"""
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
record = json.loads((ROOT / "records/sources/amazon-2023-grocery-metadata.json").read_text("utf-8"))
cereal = r"rice|basmati|jasmine|arborio|carnaroli|oats?|oatmeal|wheat|barley|rye|corn|maize|popcorn|millet|sorghum|teff|fonio|triticale|spelt|einkorn|emmer|kamut|khorasan|farro|bulgur|freekeh|poha|jowar|bajra|ragi|adlay|coix|job.s tears"
pseudo = r"quinoa|buckwheat|amaranth|kaniwa|canihua|kasha"
grain = re.compile(r"\b(?:" + cereal + "|" + pseudo + r")\b", re.I)
cereal_pattern = re.compile(r"\b(?:" + cereal + r")\b", re.I)
pseudo_pattern = re.compile(r"\b(?:" + pseudo + r")\b", re.I)
flour = re.compile(r"\b(flour|flours|cornmeal|masa|atta|semolina)\b|\b(corn|maize|wheat|barley|oat|rice|rye|millet|sorghum|teff|spelt|buckwheat)\s+meals?\b", re.I)
form = re.compile(r"\b(rice|basmati|arborio|carnaroli|berries|groats|kernels|grains?|hulled|pearled|pearl|cracked|rolled|steel[- ]cut|quick oats|old[- ]fashioned|poha|bulgur|farro|freekeh|grits|polenta)\b", re.I)
blend = re.compile(r"\b(blend|mix|mixed|variety|assorted|bundle|kits?|multigrain|multi[- ]grain|seasoned|flavou?r(?:ed)?|masala|pilaf|saffron|risotto)\b", re.I)
prepared = re.compile(r"\b(pasta|noodles?|bread|cookies?|crackers?|chips?|cakes?|candy|chocolate|milk|tea|soup|syrup|vinegar|oil|starch|protein|malt|extract|powder|instant|ready|cooked|popped|microwave)\b", re.I)
nonfood = re.compile(r"\b(pet|bird|feed|seed for planting|seeds for planting|cat litter|wheatgrass|barley grass|supplement|candle|soap|shampoo|incense)\b", re.I)
aliases = {name: family for family, names in {
    "rice": "rice basmati jasmine arborio carnaroli poha",
    "wheat": "wheat spelt einkorn emmer kamut khorasan farro bulgur freekeh",
    "oats": "oat oats oatmeal", "corn": "corn maize popcorn",
    "millet": "millet bajra ragi", "sorghum": "sorghum jowar",
    "coix": "coix adlay", "buckwheat": "buckwheat kasha",
    "quinoa": "quinoa kaniwa canihua",
}.items() for name in names.split()}
counts = Counter()
examples = {}
category_conflicts = Counter()
audit = ROOT / "data/diagnostics/scope-04-draft.jsonl"
audit.parent.mkdir(parents=True, exist_ok=True)
last_candidate = None
with gzip.open(ROOT / record["raw_path"], "rt", encoding="utf-8") as stream, audit.open("w", encoding="utf-8") as output:
    for line_number, line in enumerate(stream, 1):
        item = json.loads(line)
        title = item.get("title") or ""
        categories = item.get("categories") or []
        detail_text = json.dumps({key: item.get(key) for key in ("description", "features", "details")}, ensure_ascii=False)
        # Negated crop names do not identify the sold commodity.
        positive_title = re.sub(r"\b(?:" + cereal + "|" + pseudo + r")[ -]free\b", "", title, flags=re.I)
        title_cereal = bool(cereal_pattern.search(positive_title))
        title_pseudo = bool(pseudo_pattern.search(positive_title))
        crop_groups = {aliases.get(hit.lower(), "coix" if hit.lower().startswith("job") else hit.lower())
                       for hit in grain.findall(positive_title)}
        dry_category = "Dried Grains & Rice" in categories
        oat_category = "Oatmeal" in categories
        flour_category = "Flours & Meals" in categories
        raw_kernel_category = "Unpopped" in categories
        category_grain = dry_category or oat_category or flour_category or raw_kernel_category
        title_grain = title_cereal or title_pseudo
        evidence_grain = bool(grain.search(detail_text))
        processed_category = any(part in categories for part in (
            "Pasta & Noodles", "Breads & Bakery", "Rice Dishes", "Snack Foods",
            "Candy & Chocolate", "Beverages", "Vegetables", "Soups, Stocks & Broths"))
        # Unpopped kernels have a snack category but can be a raw grain commodity.
        if raw_kernel_category:
            processed_category = False
        category_crop_conflict = None
        if title_grain and dry_category:
            terminal = categories[-1]
            if terminal in ("Quinoa", "Buckwheat") and title_cereal and not title_pseudo:
                category_crop_conflict = "true_cereal_in_pseudo_category"
            if terminal == "Wheat Berries" and title_pseudo and not title_cereal:
                category_crop_conflict = "pseudo_in_wheat_category"
            if category_crop_conflict:
                category_conflicts[category_crop_conflict] += 1
        if not (title_grain or category_grain or evidence_grain):
            status = "outside_evidence_pool"
        elif not title_grain:
            status = "pending_category_or_description_only"
        elif nonfood.search(title):
            status = "excluded_nonfood_or_supplement"
        elif processed_category:
            status = "excluded_processed_category"
        elif category_crop_conflict:
            status = "pending_category_crop_conflict"
        elif blend.search(title) or len(crop_groups) > 1:
            status = "pending_blend_or_seasoning"
        elif prepared.search(title):
            status = "pending_prepared_or_usage_words"
        elif flour.search(title):
            status = "true_cereal_flour_candidate" if title_cereal else "pseudo_flour_candidate"
        elif form.search(title) or dry_category or raw_kernel_category:
            status = "true_cereal_primary_candidate" if title_cereal else "pseudo_primary_candidate"
            if flour_category:
                status = "pending_category_form_conflict"
        else:
            status = "pending_form_not_explicit"
        counts[status] += 1
        entry = {"source_line": line_number, "parent_asin": item["parent_asin"], "status": status,
                 "title": title, "categories": categories, "title_crop_hits": grain.findall(positive_title),
                 "description_feature_detail_hit": evidence_grain}
        output.write(json.dumps(entry, ensure_ascii=False) + "\n")
        sample = examples.setdefault(status, [])
        if len(sample) < 3:
            sample.append(entry)
        if status.endswith("candidate"):
            last_candidate = entry
result = {"status": "draft_rules_not_approved", "formal_catalog": "not_built",
          "generated_at_utc": datetime.now(timezone.utc).isoformat(), "metadata_rows": sum(counts.values()),
          "metadata_sha256": record["download"]["sha256"], "counts": counts,
          "category_conflict_signals": category_conflicts, "examples": examples, "last_candidate": last_candidate,
          "query_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "audit_path": audit.relative_to(ROOT).as_posix()}
with audit.open("rb") as data:
    result["audit_sha256"] = hashlib.file_digest(data, "sha256").hexdigest()
(ROOT / ".scratch/data-preparation/verification/scope-04-draft.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8")
print(json.dumps({key: value for key, value in result.items() if key != "examples"}, ensure_ascii=False, indent=2))
