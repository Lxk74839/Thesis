"""Source-declared grain identities with separate composition disclosure."""

import re

from catalog import classify_legacy, pattern, text_fields


def narrow_grains(crops, config):
    return crops - {config["grain_parents"][crop] for crop in crops if crop in config["grain_parents"]}


def grain_crops(text, config):
    text = re.sub(r"\b[\w]+[- ]free\b", " ", text, flags=re.I)
    found = {crop for crop, aliases in config["grains"].items() if pattern(aliases).search(text)}
    if "millet" in found and re.search(r"\b(?:foxtail|kodo|little|barnyard|proso)\s*,\s*(?:foxtail|kodo|little|barnyard|proso)\b", text, re.I):
        found.update(crop for name, crop in config["short_millet_names"].items() if pattern([name]).search(text))
    return narrow_grains(found, config)


def context_role(text):
    matches = []
    for role, expression in (
        ("allergen_or_facility", r"\b(?:facility|allergen|may contain|manufactured in|free from|free of|does not contain|contains no|grain[- ]free)\b"),
        ("use_comparison_or_brand_context", r"\b(?:serve|served|recipe|recipes|pair|pairing|use with|cooked with|combined with|baking|make|making|perfect for|ideal for|ground into|alternative|alterative|easy to use|less sticky|our company|this is because|cooking instructions|directions|to cook|add|nutrition facts)\b"),
        ("brand_or_texture_context", r"\b(?:founded|our story|we pride|our ability|began as|shop our other|our product line|not sticky|high starch|high-starch|when cooked|while cooking)\b"),
        ("storage_context", r"^\s*(?:store|keep|storage|refrigerate)\b|\b(?:keep refrigerated|refrigerate after)\b"),
        ("botanical_or_comparison_context", r"\b(?:annual grain|species of|compared to|dry climate|growing in)\b"),
    ):
        match = re.search(expression, text, re.I)
        if match:
            matches.append((role, match.start()))
    return min(matches, key=lambda match: match[1]) if matches else None


def composition_disclosure(item, config):
    declarations = []
    for field, text in text_fields(item):
        dedicated = field.lower() in ("details.ingredients", "details.ingredient")
        values = []
        active = []
        for fragment in re.split(r"(?<=[.!?])\s*|\n", text):
            fragment = fragment.strip()
            if not fragment:
                continue
            match = pattern(config["composition_prefixes"]).match(fragment)
            if not match and not active:
                inline = re.search(r"\bingredients?\s*:", fragment, re.I)
                if inline and not context_role(fragment[:inline.start()]):
                    match = inline
            if not match and not active:
                match = re.search("|".join(config["partial_composition_patterns"]), fragment, re.I)
            if match:
                if active:
                    values.append(active)
                value = re.sub(r"^[\s:=-]*(?:is|are)?\s*", "", fragment[match.end():], flags=re.I)
                active = [] if match.group().startswith("100") and pattern(config["percentage_quality_prefixes"]).match(value) else [value]
            elif active and (pattern(config["composition_end_prefixes"]).match(fragment) or pattern(config["identity_negations"]).match(fragment)):
                values.append(active)
                active = []
            elif active:
                active.append(fragment)
            elif dedicated and not values:
                active = [fragment]
        if active:
            values.append(active)
        for fragments in values:
            value = "\n".join(fragments).rstrip(".!?")
            crops = grain_crops(value, config)
            outside = pattern([*config["outside_crops"], *config["non_grain_ingredients"]]).search(value)
            remainder = value
            remainder = pattern([alias for aliases in config["grains"].values() for alias in aliases]).sub(" ", remainder)
            remainder = pattern(config["composition_modifiers"]).sub(" ", remainder)
            remainder = re.sub(r"100\s*%|[\s,;:().!\-]", "", remainder)
            components = {part.strip().lower() for part in re.split(r"[,;\n]", value) if part.strip()}
            status = ("declared_outside_scope" if outside or len(crops) > 1 else
                      "unresolved" if not crops or remainder or len(components) > 1 or pattern(config["partial_composition_prefixes"]).search(text) or re.search("|".join(config["partial_composition_patterns"]), text, re.I) else "declared_single_grain")
            declarations.append((status, crops, {"field": field, "text": text, "declaration_parts": fragments}))
    if not declarations:
        return "not_disclosed", set(), []
    known = {(tuple(sorted(crops)), tuple(sorted(match.group().lower() for match in pattern([*config["outside_crops"], *config["non_grain_ingredients"]]).finditer("\n".join(ref["declaration_parts"])))))
             for status, crops, ref in declarations if status != "unresolved" and not (pattern(config["partial_composition_prefixes"]).search(ref["text"]) or re.search("|".join(config["partial_composition_patterns"]), ref["text"], re.I))}
    status = ("conflict" if len(known) > 1 or ({"declared_single_grain", "declared_outside_scope"} <= {status for status, _, _ in declarations}) else
              "unresolved" if any(status == "unresolved" for status, _, _ in declarations) else
              "declared_outside_scope" if any(status == "declared_outside_scope" for status, _, _ in declarations) else
              "declared_single_grain")
    return status, set().union(*(crops for _, crops, _ in declarations)), [ref for _, _, ref in declarations]


def classify_identity(item, config):
    decision = classify_legacy(item, config)
    composition_status, composition_crops, composition = composition_disclosure(item, config)
    decision.update(composition_status=composition_status, composition_evidence=composition)
    title = item.get("title", "")
    affirmative = pattern(config["identity_negations"]).split(title, maxsplit=1)[0]
    affirmative = re.sub(r"\b[\w]+[- ]free\b", " ", affirmative, flags=re.I)
    sold = re.split(r"\b(?:for|use with|great with|alternative to|substitute for)\b", affirmative, maxsplit=1, flags=re.I)[0]
    if pattern(config["outside_objects"]).search(sold):
        decision.update(status="excluded", reason="sold_object_outside_scope", crop=None,
                        identity_evidence=[], form_evidence=[], counter_evidence=[{"field": "title", "text": title}])
        categories = item.get("categories") or []
        if pattern(["sauce", "seasoning", "seasonings"]).search(sold) and categories and grain_crops(categories[-1], config):
            decision.update(status="pending", reason="category_form_conflict",
                            counter_evidence=[*decision["counter_evidence"], {"field": f"categories[{len(categories) - 1}]", "text": categories[-1]}])
        return decision
    crops = grain_crops(sold, config)
    if crops and pattern([*config["non_grain_ingredients"], *config["outside_crops"]]).search(sold):
        decision.update(status="excluded", reason="sold_added_ingredient_or_outside_crop",
                        composition_status="declared_outside_scope", counter_evidence=[{"field": "title", "text": title}])
        return decision
    title_negative = re.search(r"\b(?:not|no|without)\s+(?:raw\s+)?", title, re.I)
    if title_negative and pattern([alias for aliases in config["grains"].values() for alias in aliases]).match(title[title_negative.end():]):
        if not crops or crops & grain_crops(title[title_negative.end():], config):
            decision.update(status="pending", reason="title_identity_negation", counter_evidence=[{"field": "title", "text": title}])
    if len(crops) > 1:
        decision.update(status="excluded", reason="sold_multiple_grains", crop=None,
                        composition_status="declared_outside_scope", counter_evidence=[{"field": "title", "text": title}])
        return decision
    if decision["status"] == "excluded" and decision["reason"] in ("nonfood", "excluded_form", "outside_crop", "no_scope_evidence"):
        return decision
    forms = [{"field": "title", "text": title}] if crops and pattern(config["identity_forms"]).search(sold) else []
    if crops:
        decision["identity_evidence"] = [{"field": "title", "text": title}]
    decision["context_evidence"] = []
    if decision["reason"] in ("field_identity_conflict", "field_form_conflict") and decision["counter_evidence"]:
        # Legacy stores an entire field; rebuild these facts from each source clause below.
        decision.update(status="pending", reason="form_not_verified", counter_evidence=[])
    for field, text in text_fields(item):
        if field == "title":
            continue
        for fragment in re.split(r"(?<=[.!?;])\s*|\n", text):
            ref = {"field": field, "text": text}
            role = context_role(fragment)
            negated_use = re.search(r"\b(?:not|no|without)\s+", fragment, re.I)
            if crops and (not role or role[0] != "allergen_or_facility") and pattern(config["nonfood"]).search(fragment) and not (negated_use and pattern(config["nonfood"]).match(fragment[negated_use.end():])):
                decision.update(status="pending", reason="field_food_use_conflict",
                                counter_evidence=[*decision["counter_evidence"], ref])
            if role:
                decision["context_evidence"].append({**ref, "role": role[0], "context_start": role[1]})
                fragment = fragment[:role[1]]
            if not fragment.strip():
                continue
            fragment = re.sub(r"\b[\w]+[- ]free\b", " ", fragment, flags=re.I)
            if crops and pattern(config["outside_form_statements"]).search(fragment):
                decision.update(status="excluded", reason="sold_form_outside_scope",
                                counter_evidence=[*decision["counter_evidence"], ref])
            found = grain_crops(fragment, config)
            if crops and pattern(config["outside_crops"]).search(fragment):
                decision.update(status="pending", reason="field_identity_conflict",
                                counter_evidence=[*decision["counter_evidence"], ref])
            if (crops or found) and re.search(r"\b(?:blend|blended|mixture|mix|contains|consists of|made from|infused with)\b", fragment, re.I) and (len(found) > 1 or pattern([*config["outside_crops"], *config["non_grain_ingredients"]]).search(fragment)):
                decision.update(status="excluded", reason="sold_mixture_outside_scope",
                                composition_status="declared_outside_scope", counter_evidence=[*decision["counter_evidence"], ref])
                continue
            negative = re.search(r"\b(?:not|no|without)\s+(?:raw\s+)?", fragment, re.I)
            if negative and pattern([alias for aliases in config["grains"].values() for alias in aliases]).match(fragment[negative.end():]):
                if crops & found:
                    decision.update(status="pending", reason="field_identity_conflict",
                                    counter_evidence=[*decision["counter_evidence"], ref])
                continue
            if crops and pattern(config["excluded_forms"]).search(fragment):
                decision.update(status="pending", reason="field_form_conflict",
                                counter_evidence=[*decision["counter_evidence"], ref])
            if crops and found and len(narrow_grains(crops | found, config)) > 1:
                decision.update(status="pending", reason="field_identity_conflict",
                                counter_evidence=[*decision["counter_evidence"], ref])
            if (found or crops) and pattern(config["identity_forms"]).search(fragment):
                crops.update(found)
                decision["identity_evidence"].append(ref)
                forms.append(ref)
    crops = narrow_grains(crops, config)
    categories = item.get("categories") or []
    if decision["reason"] == "category_identity_conflict" and categories:
        leaf = grain_crops(categories[-1], config)
        if len(crops) == 1 and leaf and leaf <= crops | {config["grain_parents"][crop] for crop in crops if crop in config["grain_parents"]}:
            decision.update(status="pending", reason="form_not_verified", counter_evidence=[])
    decision["form_evidence"] = forms
    if crops and decision["status"] != "excluded":
        if pattern(config["ambiguous_forms"]).search(sold):
            decision.update(status="pending", reason="ambiguous_processing_or_mix",
                            counter_evidence=[*decision["counter_evidence"], {"field": "title", "text": title}])
        if "Unpopped" not in categories:
            for index, category in enumerate(categories):
                if category in config["excluded_categories"]:
                    decision.update(status="pending", reason="category_form_conflict",
                                    counter_evidence=[*decision["counter_evidence"], {"field": f"categories[{index}]", "text": category}])
    if composition_status == "conflict":
        decision.update(status="pending", reason="composition_declaration_conflict", counter_evidence=[*decision["counter_evidence"], *composition])
    elif composition_status == "declared_outside_scope":
        decision.update(status="excluded", reason="declared_outside_composition", counter_evidence=composition)
    elif composition_status == "unresolved":
        decision.update(status="pending", reason="unresolved_composition", counter_evidence=[*decision["counter_evidence"], *composition])
    elif composition_status == "declared_single_grain" and crops and composition_crops != crops:
        decision.update(status="pending", reason="identity_composition_conflict", counter_evidence=composition)
    elif decision["reason"] in ("missing_composition", "weak_identity", "form_not_verified", "unresolved_composition", "identity_and_composition") and forms and len(crops) == 1:
        decision.update(status="included", reason="identity_form_" + composition_status)
    elif decision["status"] == "included" and not forms:
        decision.update(status="pending", reason="form_not_verified")
    decision["crop"] = next(iter(crops)) if len(crops) == 1 else None
    return decision
