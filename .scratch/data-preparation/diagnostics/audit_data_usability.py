"""Read-only profiling of accepted artifacts; not a catalog preparation stage."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
assert Path(sys.executable).resolve() == (ROOT / '.conda/envs/Thesis/python.exe').resolve()
VERSION = 'usability-04-05-draft-01'
OUT = ROOT / 'data/diagnostics' / VERSION
OUT.mkdir(parents=True, exist_ok=True)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads((ROOT / path).read_text('utf-8'))


def words(terms):
    return re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(t) for t in sorted(terms, key=len, reverse=True)) + r')(?!\w)', re.I)


def fields(item):
    if isinstance(item.get('title'), str):
        yield 'title', item['title']
    for key in ('features', 'description'):
        for index, value in enumerate(item.get(key) or []):
            if isinstance(value, str):
                yield f'{key}[{index}]', value
    for key, value in (item.get('details') or {}).items():
        if isinstance(value, str):
            yield 'details.' + key, value


catalog = load('records/catalog/grain-A-1.0.6.json')
source = load('records/sources/amazon-2023-grocery-metadata.json')
reviews = load('records/reviews/grain-A-1.0.6-review-diagnostics-1.0.0.json')
config = load('config/grain-A-v1.json')
preserved_paths = ['config/grain-A-v1.json', 'catalog.py', 'prepare_data.py', 'review_diagnostics.py',
                   '.scratch/data-preparation/spec.md', '.scratch/data-preparation/product-scope-proposal.md',
                   'records/catalog/grain-A-1.0.6.json', 'records/reviews/grain-A-1.0.6-review-diagnostics-1.0.0.json',
                   '.scratch/data-preparation/verification/catalog-04-check.json',
                   '.scratch/data-preparation/verification/review-extract-05-check.json',
                   '.scratch/data-preparation/verification/code-review-04.md',
                   '.scratch/data-preparation/verification/code-review-05.md']
before = {path: digest(ROOT / path) for path in preserved_paths}
for name in ('catalog', 'audit', 'pending'):
    assert digest(ROOT / catalog[name + '_path']) == catalog[name + '_sha256']
assert digest(ROOT / source['raw_path']) == catalog['source_sha256']
assert digest(ROOT / reviews['extract_path']) == reviews['extract_sha256']
assert before['config/grain-A-v1.json'] == catalog['scope_sha256']

reasons = Counter()
cross = defaultdict(Counter)
gate = Counter()
all_source = Counter()
ingredient_keys = Counter()
alias_counts = defaultdict(Counter)
first_examples = defaultdict(list)
hash_examples = defaultdict(list)
special_examples = {}
grain_patterns = {key: words(value) for key, value in config['grains'].items()}
alias_terms = ('poha', 'powa', 'avalakki', 'hato mugi', 'hatomugi', 'job’s tears', 'jasmine',
               'dalia', 'daliya', 'ragi', 'bajra', 'jowar', 'barnyard millet', 'foxtail millet',
               'little millet', 'kodo millet', 'proso millet')
alias_patterns = {term: words([term]) for term in alias_terms}
ingredients = re.compile(r'\bingredients?\b|\bcontains only\b|\bnothing else is added\b|\bmade (?:from|of) only\b|配料|原料', re.I)
physical = re.compile(r'\b(?:long|short|medium)[ -]grain\b|\b(?:whole|raw|hulled|pearled|rolled|cracked|flattened|steel[ -]cut)\b|\b(?:kernels|groats|berries|flakes|grits)\b|精米|米粒|麦粒|燕麦片', re.I)
non_scope = re.compile(r'\b(?:paper|wrappers?|boxes|trays|pudding|tempeh|sauce|sugar|decorations?|toppers|spices?|puffs?|crisps?|crunch|seasoning|soup|bouillon|baby food|utensils?|cookers?)\b', re.I)
ingredient_role = re.compile(r'\b(?:serve|served|recipe|recipes|add|allergen|allergens|may contain|made in a facility|use for|used for)\b', re.I)
quality_percentage = re.compile(r'100\s*(?:%|percent)\s*(?:natural|organic|whole|premium|pure|satisfaction|money|edible)', re.I)
reason_layers = {'missing_composition': 'composition_gate', 'unresolved_composition': 'composition_parse_or_fact',
                 'weak_identity': 'insufficient_identity_or_form', 'form_not_verified': 'insufficient_identity_or_form'}
known_ids = {'B08Q44XV13', 'B09TS94RVG', 'B0BMSZCYM7', 'B0BYLK9168', 'B0BWMCLXRL',
             'B087C4WM17', 'B0019L8I58', 'B088PZLRK7', 'B07TTJYHGX', 'B0BDV6ZTHR',
             'B00JM1DP32', 'B07CVXGQN4', 'B0BR1CCPC3', 'B09H3TZL9L', 'B00KBRUYVM'}

profile_path = OUT / 'pending-profile.jsonl'
with gzip.open(ROOT / source['raw_path'], 'rb') as raw, (ROOT / catalog['audit_path']).open(encoding='utf-8') as audit, (ROOT / catalog['pending_path']).open(encoding='utf-8') as pending, profile_path.open('w', encoding='utf-8', newline='\n') as out:
    for line_number, raw_line in enumerate(raw, 1):
        item = json.loads(raw_line)
        decision = json.loads(next(audit))
        assert decision['source_line'] == line_number and decision['parent_asin'] == item['parent_asin']
        all_source[decision['status']] += 1
        text = list(fields(item))
        ingredient_key_fields = [key for key, value in (item.get('details') or {}).items() if re.search('ingredient|composition|材料|原料|配料', key, re.I)]
        all_source['ingredient_like_details_key'] += bool(ingredient_key_fields)
        all_source['ingredient_lexeme_in_text'] += any(ingredients.search(value) for _, value in text)
        if decision['status'] != 'pending':
            continue
        row = json.loads(next(pending))
        assert row['metadata'] == item and row['source_line'] == line_number
        assert all(row[key] == value for key, value in decision.items())
        reason = row['reason']
        reasons[reason] += 1
        title = item.get('title') or ''
        title_crops = [key for key, expression in grain_patterns.items() if expression.search(title)]
        signal_fields = [{'field': field, 'text': value} for field, value in text if ingredients.search(value)]
        flags = {
            'single_title_crop_family': len(title_crops) == 1,
            'null_current_crop': row['crop'] is None,
            'explicit_physical_word_in_title': bool(physical.search(title)),
            'non_scope_object_word_in_title': bool(non_scope.search(title)),
            'ingredient_like_details_key': bool(ingredient_key_fields),
            'ingredient_lexeme_in_text': bool(signal_fields),
            'html_in_ingredient_text': any('<' in ref['text'] for ref in signal_fields),
            'use_or_allergen_language': any(ingredient_role.search(value) for _, value in text),
            'quality_or_marketing_percentage': any(quality_percentage.search(value) for _, value in text),
            'features_present': bool(item.get('features')),
            'description_present': bool(item.get('description')),
        }
        for flag, present in flags.items():
            cross[reason][flag] += present
        for key in ingredient_key_fields:
            ingredient_keys[key] += 1
        aliases = [term for term, expression in alias_patterns.items() if expression.search(title)]
        for term in aliases:
            alias_counts[term][reason] += 1
        if reason == 'missing_composition':
            gate['all'] += 1
            gate['null_current_crop'] += row['crop'] is None
            gate['non_scope_object_word_in_title'] += flags['non_scope_object_word_in_title']
            gate['single_crop_physical_no_non_scope_title_signal'] += (len(title_crops) == 1 and flags['explicit_physical_word_in_title'] and not flags['non_scope_object_word_in_title'])
            gate['single_crop_no_non_scope_title_signal'] += (len(title_crops) == 1 and not flags['non_scope_object_word_in_title'])
        profile = {'parent_asin': row['parent_asin'], 'source_line': line_number,
                   'source_sha256': catalog['source_sha256'], 'source_line_sha256': hashlib.sha256(raw_line).hexdigest(),
                   'existing_status': row['status'], 'existing_reason': reason,
                   'diagnostic_layer': reason_layers.get(reason, 'processing_or_conflict_signal'),
                   'title_crop_families': title_crops, 'flags': flags, 'alias_terms': aliases,
                   'ingredient_signal_fields': signal_fields, 'review_admission': 'not_evaluated',
                   'new_scope_decision': 'not_made', 'diagnostic_version': VERSION}
        out.write(json.dumps(profile, ensure_ascii=False, sort_keys=True) + '\n')
        sample = {**profile, 'metadata': item, 'existing_decision': decision}
        if len(first_examples[reason]) < 1:
            first_examples[reason].append(sample)
        key = hashlib.sha256(row['parent_asin'].encode()).hexdigest()
        hash_examples[reason].append((key, sample))
        hash_examples[reason].sort(key=lambda pair: pair[0])
        del hash_examples[reason][2:]
        if row['parent_asin'] in known_ids:
            special_examples[row['parent_asin']] = sample
    assert not audit.readline() and not pending.readline()
assert line_number == catalog['scan']['rows'] == 603274
assert {key: all_source[key] for key in ('included', 'excluded', 'pending')} == catalog['counts']
assert sum(reasons.values()) == catalog['counts']['pending']
layers = Counter()
for reason, count in reasons.items():
    layers[reason_layers.get(reason, 'processing_or_conflict_signal')] += count
samples = {row['parent_asin']: row for group in first_examples.values() for row in group}
samples.update({row['parent_asin']: row for pairs in hash_examples.values() for _, row in pairs})
samples.update(special_examples)
sample_path = OUT / 'representative-records.json'
sample_path.write_text(json.dumps(sorted(samples.values(), key=lambda row: row['source_line']), ensure_ascii=False, sort_keys=True, indent=2) + '\n', 'utf-8')
after = {path: digest(ROOT / path) for path in preserved_paths}
assert after == before
baseline = load('.scratch/data-preparation/verification/original-materials.json')
assert all(digest(ROOT / row['path']) == row['sha256'] for row in baseline['files'])
result = {'version': VERSION, 'status': 'draft_diagnostic_not_approved',
          'generated_at_utc': datetime.now(timezone.utc).isoformat(), 'interpreter': sys.executable, 'python': sys.version,
          'source_sha256': catalog['source_sha256'], 'source_rows': line_number,
          'all_source': all_source, 'pending_reasons': reasons, 'reason_layers': layers,
          'composition_gate': gate, 'cross_signals': cross, 'ingredient_like_pending_details_keys': ingredient_keys,
          'title_alias_counts': alias_counts,
          'sampling_method': 'First source row plus two lexicographically smallest SHA256(parent_asin) values per existing reason, supplemented with named raw examples. Not a probability or complete semantic audit.',
          'representative_count': len(samples),
          'profile_path': profile_path.relative_to(ROOT).as_posix(), 'profile_sha256': digest(profile_path),
          'representative_path': sample_path.relative_to(ROOT).as_posix(), 'representative_sha256': digest(sample_path),
          'preserved_sha256': after, 'original_material_count': len(baseline['files']), 'original_materials_unchanged': True,
          'accepted_reviews': {'reviews': reviews['raw']['reviews'], 'accounts': reviews['raw']['unique_accounts'], 'history': reviews['history']},
          'generator_sha256': digest(Path(__file__)),
          'limitations': ['Flags are discovery leads, not semantic membership judgments.', 'Composition gate counts reflect the existing mutually exclusive reason, not every hidden rejection cause.', 'Existing accepted catalog/reviews and user histories were not rebuilt.', 'No review count, rating, model outcome or eligibility parameter is used in metadata profiling.']}
destination = ROOT / '.scratch/data-preparation/verification/usability-04-05-draft-01.json'
destination.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n', 'utf-8')
print(json.dumps({key: result[key] for key in ('status', 'source_rows', 'pending_reasons', 'reason_layers', 'composition_gate', 'title_alias_counts', 'representative_count', 'original_materials_unchanged')}, ensure_ascii=False, indent=2))
