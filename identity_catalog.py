"""Source-declared grain identities with separate composition disclosure."""

import re

from catalog import classify_legacy, pattern, text_fields


COMPONENT_SEPARATOR = r"\s*(?:,\s*(?:and|or)?|\band\b|\bor\b)\s*"


def composition_component(config):
    components = [*config["non_grain_ingredients"], *config["outside_crops"],
                  *(alias for aliases in config["grains"].values() for alias in aliases)]
    return r"(?:(?:" + pattern(config["composition_modifiers"]).pattern + r")[ -]+)*(?:" + pattern(components).pattern + ")"


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
        ("use_comparison_or_brand_context", r"\b(?:serve|served|enjoy|enjoying|recipe|recipes|pair|pairing|use with|(?:can|should|to) be (?:cooked|combined|mixed)|often cooked with|can be coated|can be topped|baking|make|making|perfect for|ideal for|ground into|alternative|alterative|easy to use|less sticky|our company|this is because|cooking instructions|directions|to cook|add|nutrition facts|want to eat)\b"),
        ("brand_or_texture_context", r"\b(?:founded|our story|we pride|our ability|began as|shop our other|our product line|nutrition & flavor|nutty flavor|nutritional value|not sticky|high starch|high-starch|when cooked|while cooking|freshly cooked (?:luster|gloss|stickiness))\b"),
        ("storage_context", r"^\s*(?:store|keep|storage|refrigerate)\b|\b(?:keep refrigerated|refrigerate after)\b"),
        ("botanical_or_comparison_context", r"\b(?:annual grain|species of|compared to|dry climate|growing in|known as the southern oatmeal|preferred over)\b"),
    ):
        match = re.search(expression, text, re.I)
        if match:
            matches.append((role, match.start()))
    return min(matches, key=lambda match: match[1]) if matches else None


def source_statements(item, config):
    component = composition_component(config)
    continued_component = re.compile(COMPONENT_SEPARATOR + component, re.I)
    for field, text in text_fields(item):
        for clause in re.split(r"(?<=[.!?;])\s*|\n", text):
            role = context_role(clause)
            if field == "title":
                purpose = re.search(r"\b(?:for|use with|great with|alternative to|substitute for)\b", clause, re.I)
                if purpose and (not role or purpose.start() < role[1]):
                    role = ("use_comparison_or_brand_context", purpose.start())
            direct = clause[:role[1]] if role else clause
            negative_terms = re.compile(pattern([*config["processing_claims"], *config["non_grain_ingredients"],
                                      *config["excluded_forms"], *config["outside_form_statements"],
                                      *config["nonfood"], *config["outside_crops"]]).pattern + r"|mixed\s+with\s+" + component, re.I)
            negated_positions = []
            for negative in reversed(list(re.finditer(r"\b(?:not(?!\s+only\b)|no|without)\s+", direct, re.I))):
                claim = negative_terms.match(direct, negative.end())
                if claim:
                    end = claim.end()
                    while continuation := continued_component.match(direct, end):
                        end = continuation.end()
                    direct = direct[:negative.start()] + " " + direct[end:]
                    negated_positions.append(negative.start())
            negative = re.match(r"\s*(?:not|no|without)\b", clause, re.I)
            if negated_positions:
                role = ("negative_nonidentity_claim", min(negated_positions))
            elif negative and pattern(config["identity_forms"]).match(clause[negative.end():].lstrip()):
                role = ("negative_form_claim", negative.start())
            elif negative and not re.match(r"\s*not\s+only\b", clause, re.I) and not grain_crops(clause, config):
                role = ("negative_nonidentity_claim", negative.start())
                direct = clause[:negative.start()]
            yield {"field": field, "text": text}, clause, re.sub(r"\b[\w]+[- ]free\b", " ", direct, flags=re.I), role


def affirmative_composition(value, config):
    component = composition_component(config)
    component_list = component + r"(?:" + COMPONENT_SEPARATOR + component + ")*"
    negative = r"(?:" + pattern([*config["identity_negations"], "no added", "free from", "free of", "does not contain", "contains no"]).pattern + r")\s*(?:mixed\s+with\s+)?" + component_list
    value = re.sub(negative, " ", value, flags=re.I)
    return re.sub(component + r"[- ]free\b", " ", value, flags=re.I)


def affirmative_identity(text, config):
    for negative in pattern(config["identity_negations"]).finditer(text):
        if not negative.group().isascii() or ((negative.start() == 0 or text[negative.start() - 1] != "-") and text[negative.end():negative.end() + 1].isspace()):
            return text[:negative.start()]
    return text


def sold_form_text(ref, fragment):
    if ref["field"].lower() in ("details.ingredients", "details.ingredient"):
        return ""
    material = re.search(r"\bingredients?\b|\bmade (?:from|of|with)\b", fragment, re.I)
    return fragment[:material.start()] if material else fragment


def composition_disclosure(item, config):
    declarations = []
    for field, text in text_fields(item):
        dedicated = field.lower() in ("details.ingredients", "details.ingredient")
        values = []
        active = []
        active_partial = False
        for fragment in re.split(r"(?<=[.!?])\s*|\n", text):
            fragment = fragment.strip()
            if not fragment:
                continue
            match = pattern(config["composition_prefixes"]).match(fragment)
            if not match:
                inline = re.search(r"\bingredients?\s*:", fragment, re.I)
                if inline and not context_role(fragment[:inline.start()]):
                    match = inline
            if not match:
                complete = re.search(r"\b(?:made of|made from)\s+100\s*%", fragment, re.I)
                if complete and not context_role(fragment[:complete.start()]):
                    match = complete
            if not match and not active:
                partial = re.search("|".join(config["partial_composition_patterns"]), fragment, re.I)
                if partial and not context_role(fragment[:partial.start()]):
                    match = partial
            boundary = context_role(fragment) if active and not match else None
            if match:
                if active:
                    values.append((active, active_partial))
                value = re.sub(r"^[\s:=-]*(?:is|are)?\s*", "", fragment[match.end():], flags=re.I)
                active = [] if match.group().startswith("100") and pattern(config["percentage_quality_prefixes"]).match(value) else [value]
                active_partial = bool(pattern(config["partial_composition_prefixes"]).search(fragment) or re.search("|".join(config["partial_composition_patterns"]), fragment, re.I))
            elif active and (pattern(config["composition_end_prefixes"]).match(fragment) or (boundary and boundary[1] == 0) or (pattern(config["identity_negations"]).match(fragment) and not re.match(r"not\s+only\b", fragment, re.I))):
                values.append((active, active_partial))
                active = []
            elif active:
                active.append(fragment)
            elif dedicated and not values:
                active = [fragment]
        if active:
            values.append((active, active_partial))
        for fragments, partial in values:
            value = affirmative_composition("\n".join(fragments).rstrip(".!?"), config)
            crops = grain_crops(value, config)
            outside = pattern([*config["outside_crops"], *config["non_grain_ingredients"]]).search(value)
            remainder = value
            remainder = pattern([alias for aliases in config["grains"].values() for alias in aliases]).sub(" ", remainder)
            remainder = pattern(config["composition_modifiers"]).sub(" ", remainder)
            remainder = re.sub(r"100\s*%|[\s,;:().!\-]", "", remainder)
            components = {part.strip().lower() for part in re.split(r"[,;\n]", value) if part.strip()}
            status = ("declared_outside_scope" if outside or len(crops) > 1 else
                      "unresolved" if not crops or remainder or len(components) > 1 or partial else "declared_single_grain")
            declarations.append((status, crops, {"field": field, "text": text, "declaration_parts": fragments, "partial_declaration": partial}))
    if not declarations:
        return "not_disclosed", set(), []
    known = {(tuple(sorted(crops)), tuple(sorted(match.group().lower() for match in pattern([*config["outside_crops"], *config["non_grain_ingredients"]]).finditer(affirmative_composition("\n".join(ref["declaration_parts"]), config)))))
             for status, crops, ref in declarations if status != "unresolved" and not ref["partial_declaration"]}
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
    affirmative = affirmative_identity(title, config)
    affirmative = re.sub(r"\b[\w]+[- ]free\b", " ", affirmative, flags=re.I)
    sold = re.split(r"\b(?:for|use with|great with|alternative to|substitute for)\b", affirmative, maxsplit=1, flags=re.I)[0]
    title_use = re.search(r"\bwhen cooked\b", sold, re.I)
    if title_use:
        sold = sold[:title_use.start()]
    crops = grain_crops(sold, config)
    if pattern(config["outside_objects"]).search(sold):
        decision.update(status="excluded", reason="sold_object_outside_scope", crop=None,
                        identity_evidence=[], form_evidence=[], counter_evidence=[{"field": "title", "text": title}])
        added_components = crops and any(
            min(grain.end(), addition.end()) <= join.start() and join.end() <= max(grain.start(), addition.start())
            for grain in pattern([alias for aliases in config["grains"].values() for alias in aliases]).finditer(sold)
            for addition in pattern(config["non_grain_ingredients"]).finditer(sold)
            for join in re.finditer(r"\b(?:with|and|contains|added|infused with)\b", sold, re.I))
        if added_components:
            decision["composition_status"] = "declared_outside_scope"
            if composition_status in ("declared_single_grain", "conflict"):
                decision.update(status="pending", reason="composition_declaration_conflict", composition_status="conflict",
                                counter_evidence=[*decision["counter_evidence"], *composition])
        categories = item.get("categories") or []
        if pattern(["sauce", "seasoning", "seasonings"]).search(sold) and categories and grain_crops(categories[-1], config):
            decision.update(status="pending", reason="category_form_conflict",
                            counter_evidence=[*decision["counter_evidence"], {"field": f"categories[{len(categories) - 1}]", "text": categories[-1]}])
        return decision
    if crops and pattern([*config["non_grain_ingredients"], *config["outside_crops"]]).search(sold):
        decision.update(status="excluded", reason="sold_added_ingredient_or_outside_crop",
                        composition_status="declared_outside_scope", counter_evidence=[{"field": "title", "text": title}])
        if composition_status in ("declared_single_grain", "conflict"):
            decision.update(status="pending", reason="composition_declaration_conflict", composition_status="conflict",
                            counter_evidence=[*decision["counter_evidence"], *composition])
        return decision
    title_negative = re.search(r"\b(?:not|no|without)\s+(?:raw\s+)?", title, re.I)
    if title_negative and pattern([alias for aliases in config["grains"].values() for alias in aliases]).match(title[title_negative.end():]):
        if not crops or crops & grain_crops(title[title_negative.end():], config):
            decision.update(status="pending", reason="title_identity_negation", counter_evidence=[{"field": "title", "text": title}])
    if len(crops) > 1:
        decision.update(status="excluded", reason="sold_multiple_grains", crop=None,
                        composition_status="declared_outside_scope", counter_evidence=[{"field": "title", "text": title}])
        if composition_status in ("declared_single_grain", "conflict"):
            decision.update(status="pending", reason="composition_declaration_conflict", composition_status="conflict",
                            counter_evidence=[*decision["counter_evidence"], *composition])
        return decision
    if decision["reason"] == "excluded_form" and not pattern(config["excluded_forms"]).search(sold):
        decision.update(status="pending", reason="form_not_verified", counter_evidence=[])
    statements = list(source_statements(item, config))
    if decision["reason"] == "excluded_form":
        conflicting_shapes = [*config["solid_sale_shapes"], *(["raw", "uncooked"] if pattern(["cooked"]).search(sold) else [])]
        shapes = [ref for ref, _, fragment, _ in statements if ref["field"] != "title"
                  and pattern(conflicting_shapes).search(affirmative_identity(sold_form_text(ref, fragment), config))]
        if shapes:
            decision.update(status="pending", reason="field_form_conflict",
                            counter_evidence=[{"field": "title", "text": title}, *shapes])
    if decision["reason"] == "outside_crop":
        identities = [ref for ref, _, fragment, _ in statements if ref["field"] != "title"
                      and grain_crops(affirmative_identity(fragment, config), config)]
        if identities:
            decision.update(status="pending", reason="field_identity_conflict",
                            identity_evidence=[*decision["identity_evidence"], *identities])
    if decision["status"] == "excluded" and decision["reason"] in ("nonfood", "excluded_form", "outside_crop", "no_scope_evidence"):
        return decision
    forms = [{"field": "title", "text": title}] if crops and pattern(config["identity_forms"]).search(sold) else []
    if crops:
        decision["identity_evidence"] = [{"field": "title", "text": title}]
    decision["context_evidence"] = []
    if decision["reason"] in ("field_identity_conflict", "field_form_conflict", "ambiguous_processing_or_mix", "composition_declaration_conflict") and decision["counter_evidence"]:
        # Legacy stores an entire field; rebuild these facts from each source clause below.
        decision.update(status="pending", reason="form_not_verified", counter_evidence=[])
    affirmative_forms = set()
    sale_shapes = {}
    for ref, _, fragment, _ in statements:
        affirmative = affirmative_identity(sold_form_text(ref, fragment), config)
        for shape, terms in config.get("explicit_sale_shapes", {}).items():
            if pattern(terms).search(affirmative):
                sale_shapes.setdefault(shape, []).append(ref)
        form_names = {match.group().lower().replace("-", " ") for match in pattern(config["identity_forms"]).finditer(affirmative)}
        if form_names:
            affirmative_forms.update(form_names)
            crops.update(grain_crops(affirmative, config))
    crops = narrow_grains(crops, config)
    outside_facts = []
    for ref, clause, fragment, role in statements:
        negated_use = re.search(r"\b(?:not|no|without)\s+", fragment, re.I)
        if crops and (not role or role[0] != "allergen_or_facility") and pattern(config["nonfood"]).search(fragment) and not (negated_use and pattern(config["nonfood"]).match(fragment[negated_use.end():])):
            decision.update(status="pending", reason="field_food_use_conflict",
                            counter_evidence=[*decision["counter_evidence"], ref])
        if role:
            decision["context_evidence"].append({**ref, "role": role[0], "clause_text": clause, "context_start": role[1]})
        boundary = context_role(clause)
        free_direct = clause[:boundary[1]] if boundary else clause
        free_claims = [(crop, match) for crop, aliases in config["grains"].items()
                       if (match := re.search(r"(?:" + pattern(aliases).pattern + r")[- ]free\b", free_direct, re.I))]
        if free_claims:
            decision["context_evidence"].append({**ref, "role": "negative_identity_claim", "clause_text": clause,
                                                 "context_start": min(match.start() for _, match in free_claims)})
            if crops & {crop for crop, _ in free_claims}:
                decision.update(status="pending", reason="field_identity_conflict",
                                counter_evidence=[*decision["counter_evidence"], ref])
        if not fragment.strip():
            continue
        if crops and pattern(config["processing_claims"]).search(fragment):
            decision.update(status="pending", reason="field_processing_ambiguity",
                            counter_evidence=[*decision["counter_evidence"], ref])
        if crops and pattern(config["outside_form_statements"]).search(fragment):
            outside_facts.append(("sold_form_outside_scope", ref))
            decision.update(status="excluded", reason="sold_form_outside_scope",
                            counter_evidence=[*decision["counter_evidence"], ref])
        found = grain_crops(fragment, config)
        if crops and pattern(config["outside_crops"]).search(fragment):
            decision.update(status="pending", reason="field_identity_conflict",
                            counter_evidence=[*decision["counter_evidence"], ref])
        contrast = re.search(r"\bnot\s+only\s+(.+?)\s+but\b", fragment, re.I)
        composition_fragment = affirmative_composition(fragment, config)
        grain_names = [alias for aliases in config["grains"].values() for alias in aliases]
        direct_with = any(min(grain.end(), addition.end()) <= join.start() and join.end() <= max(grain.start(), addition.start())
                          for grain in pattern(grain_names).finditer(composition_fragment)
                          for join in re.finditer(r"\bwith\b", composition_fragment, re.I)
                          for addition in pattern([*grain_names, *config["non_grain_ingredients"], *config["outside_crops"]]).finditer(composition_fragment))
        mixture = re.search(r"\b(?:blend|blended|mixture|mix|mixed|contains|consists of|made from|infused with)\b", fragment, re.I) or direct_with or (contrast and grain_crops(contrast[1], config))
        mixture_text = composition_fragment if mixture else fragment
        if (crops or found) and mixture and (len(grain_crops(mixture_text, config)) > 1 or pattern([*config["outside_crops"], *config["non_grain_ingredients"]]).search(mixture_text)):
            outside_facts.append(("sold_mixture_outside_scope", ref))
            decision.update(status="excluded", reason="sold_mixture_outside_scope",
                            composition_status="declared_outside_scope", counter_evidence=[*decision["counter_evidence"], ref])
            if composition_status == "declared_single_grain":
                composition_status = "conflict"
                decision["composition_status"] = "conflict"
            continue
        negative = re.search(r"(?:\b(?:not|no|without)\s+(?:raw\s+)?|不包含|不含|不是|并非)\s*", fragment, re.I)
        negated = fragment[negative.end():] if negative else ""
        negated_forms = {"raw"} if negative and re.search(r"\braw\s*$", negative.group(), re.I) else set()
        while modifier := pattern(config["identity_forms"]).match(negated):
            negated_forms.add(modifier.group().lower().replace("-", " "))
            negated = negated[modifier.end():].lstrip()
        negated_grain = pattern([alias for aliases in config["grains"].values() for alias in aliases]).match(negated)
        if negative and negated_grain:
            if not crops or crops & grain_crops(negated_grain.group(), config):
                decision.update(status="pending", reason="field_identity_conflict")
                if ref not in decision["counter_evidence"]:
                    decision["counter_evidence"].append(ref)
            continue
        if negative and negated_forms:
            if negated_forms & affirmative_forms:
                decision.update(status="pending", reason="field_form_conflict")
                if ref not in decision["counter_evidence"]:
                    decision["counter_evidence"].append(ref)
            continue
        if crops and (pattern(config["excluded_forms"]).search(fragment) or fragment.strip() in config["excluded_categories"]):
            decision.update(status="pending", reason="field_form_conflict",
                            counter_evidence=[*decision["counter_evidence"], ref])
        if crops and found and len(narrow_grains(crops | found, config)) > 1:
            decision.update(status="pending", reason="field_identity_conflict",
                            counter_evidence=[*decision["counter_evidence"], ref])
        affirmative = affirmative_identity(sold_form_text(ref, fragment), config)
        positive = grain_crops(affirmative, config)
        if (positive or crops) and pattern(config["identity_forms"]).search(affirmative):
            crops.update(positive)
            if ref not in decision["identity_evidence"]:
                decision["identity_evidence"].append(ref)
            if ref not in forms:
                forms.append(ref)
    crops = narrow_grains(crops, config)
    if outside_facts:
        decision.update(status="excluded", reason=outside_facts[0][0],
                        counter_evidence=[*decision["counter_evidence"], *(ref for _, ref in outside_facts)])
    if len(sale_shapes) > 1 and decision["status"] != "excluded":
        decision.update(status="pending", reason="field_form_conflict",
                        counter_evidence=[*decision["counter_evidence"], *(ref for values in sale_shapes.values() for ref in values)])
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
        decision.update(status="pending", reason="composition_declaration_conflict", composition_status="conflict",
                        counter_evidence=[*decision["counter_evidence"], *composition])
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
