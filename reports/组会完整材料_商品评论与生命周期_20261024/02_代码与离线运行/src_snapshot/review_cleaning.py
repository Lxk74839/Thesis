"""Approved review cleaning through the project's single preparation entry."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import re
import subprocess
import sys

from review_diagnostics import canonical, checked_file, valid_time


def file_sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fact_reasons(row):
    reasons = ['invalid_' + name for name in ('user_id', 'asin')
               if not isinstance(row.get(name), str) or not row[name].strip()]
    if valid_time(row.get('timestamp')) is None:
        reasons.append('invalid_timestamp')
    if type(row.get('rating')) not in (int, float) or not 1 <= row['rating'] <= 5:
        reasons.append('invalid_rating')
    if not isinstance(row.get('text'), str):
        reasons.append('invalid_text')
    return reasons


def account_eligibility(raw_rows, windowed, unknown, text, rules):
    accounts = defaultdict(list)
    usable = {ref['source_line'] for entry in text for ref in entry['source_references']}
    for row, ref in windowed:
        if isinstance(row.get('user_id'), str) and row['user_id'].strip():
            accounts[row['user_id']].append((row, ref))
    unsafe = {row['user_id'] for row, _ in unknown if isinstance(row.get('user_id'), str) and row['user_id'].strip()}
    result = []
    raw_users = {row['user_id'] for row in raw_rows if isinstance(row.get('user_id'), str) and row['user_id'].strip()}
    for user in sorted(raw_users):
        values = accounts[user]
        latest = max((row['timestamp'] for row, _ in values), default=None) if user not in unsafe else None
        targets = [(row, ref) for row, ref in values if row['timestamp'] == latest] if latest is not None else []
        parents = {row['parent_asin'] for row, _ in targets}
        prior = [(row, ref) for row, ref in values if row['timestamp'] < latest] if latest is not None else []
        seen = {row['parent_asin'] for row, _ in prior}
        positive = {row['parent_asin'] for row, ref in prior if ref['source_line'] in usable
                    and row['rating'] >= rules['positive_min_rating']}
        target = targets[0][0] if targets else {}
        reason = ('unreliable_time' if user in unsafe else
                  'no_window_interactions' if latest is None else
                  'multiple_latest_parents' if len(parents) != 1 else
                  'latest_fact_conflict' if len({canonical(row) for row, _ in targets}) != 1 else
                  'latest_invalid_facts' if any(fact_reasons(row) for row, _ in targets) else
                  'latest_seen_product' if target['parent_asin'] in seen else
                  'latest_not_positive_text' if not (target['rating'] >= rules['positive_min_rating'] and target['text'].strip()) else
                  'insufficient_positive_history' if len(positive) < rules['minimum_prior_positive_products'] else None)
        result.append({'user_id': user, 'status': 'excluded' if reason else 'qualified',
                       'reasons': [reason] if reason else [], 'latest_timestamp_ms': latest,
                       'target_parent_asin': target['parent_asin'] if len(parents) == 1 else None,
                       'target_source_references': [ref for _, ref in targets],
                       'prior_positive_product_count': len(positive)})
        result[-1]['seen_parent_asins'] = sorted(seen)
        result[-1]['prior_positive_parent_asins'] = sorted(positive)
    return result


def clean_reviews(catalog_record, review_record, cleaning_config, root):
    catalog = json.loads(catalog_record.read_text('utf-8'))
    source = json.loads(review_record.read_text('utf-8'))
    rules = json.loads(cleaning_config.read_text('utf-8'))
    approved = {'approval': 'approved', 'cutoff_exclusive_ms': 1694550038852,
                'time_unit': 'milliseconds', 'timezone': 'UTC', 'text_policy': 'original',
                'deduplication': 'complete_object', 'conflict_groups': ['raw_quad', 'same_product_equal_time'],
                'positive_min_rating': 4, 'minimum_prior_positive_products': 1,
                'latest_interaction': 'windowed_raw', 'seen_products': 'all_strict_prior_raw', 'catalog_policy': 'retain_all'}
    unsupported = [key for key, value in approved.items() if type(rules.get(key)) is not type(value) or rules.get(key) != value]
    if not isinstance(rules.get('version'), str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*', rules['version']):
        unsupported.append('version')
    if unsupported:
        print(json.dumps({'stage': 'review_clean', 'status': 'rules_not_approved',
                          'unapproved_fields': unsupported, 'formal_clean_status': 'not_built'}))
        return 2
    if catalog['stage'] != 'catalog' or catalog['status'] != 'catalog_complete':
        raise ValueError('cleaning requires a complete catalog')
    if source['stage'] != 'review_extract' or source['status'] != 'extraction_complete' or not source['scan']['gzip_verified']:
        raise ValueError('cleaning requires a complete extraction')
    if source['scope_version'] != catalog['scope_version'] or source['catalog_sha256'] != catalog['catalog_sha256'] or source['catalog_record_sha256'] != hashlib.sha256(catalog_record.read_bytes()).hexdigest():
        raise ValueError('extraction and catalog provenance do not match')
    catalog_path = checked_file(catalog_record, catalog['catalog_path'], catalog['catalog_sha256'])
    parents = [json.loads(line)['parent_asin'] for line in catalog_path.read_text('utf-8').splitlines()]
    if len(set(parents)) != len(parents) or len(parents) != catalog['counts']['included'] or set(parents) != set(source['product_review_counts']):
        raise ValueError('catalog identities or extraction product counts are inconsistent')
    raw = checked_file(review_record, source['extract_path'], source['extract_sha256'])
    refs_path = checked_file(review_record, source['references_path'], source['references_sha256'])
    refs = [json.loads(line) for line in refs_path.read_text('utf-8').splitlines()]
    raw_lines = raw.read_bytes().splitlines(keepends=True)
    rows = [json.loads(line) for line in raw_lines]
    if len(rows) != source['raw']['reviews'] or len(rows) != source['scan']['matched_rows'] or len(refs) != len(rows):
        raise ValueError('extraction row and reference counts are inconsistent')
    last_source_line = 0
    for number, (line, row, ref) in enumerate(zip(raw_lines, rows, refs, strict=True), 1):
        if ref['selected_row'] != number or not last_source_line < ref['source_line'] <= source['scan']['lines'] or ref['line_sha256'] != hashlib.sha256(line).hexdigest() or row['parent_asin'] not in parents:
            raise ValueError('extraction source-line provenance is inconsistent')
        last_source_line = ref['source_line']
    groups_path = checked_file(review_record, source['groups_path'], source['groups_sha256'])
    groups = [json.loads(line) for line in groups_path.read_text('utf-8').splitlines()]
    conflicts = {}
    for group in groups:
        if group['kind'] in ('raw_quad', 'same_product_equal_time') and group['conflicting_fields']:
            for number in group['source_lines']:
                conflicts.setdefault(number, []).append(group['kind'] + '_fact_conflict')
    cutoff = rules['cutoff_exclusive_ms']
    project = Path(__file__).resolve().parent
    provenance = {'scope_version': catalog['scope_version'], 'rules_sha256': file_sha256(cleaning_config),
                  'catalog_sha256': catalog['catalog_sha256'], 'source_extract_sha256': source['extract_sha256'],
                  'source_record_sha256': file_sha256(review_record), 'catalog_record_sha256': file_sha256(catalog_record),
                  'producer_sha256': {name: file_sha256(project / name) for name in ('prepare_data.py', 'review_cleaning.py', 'review_diagnostics.py')}}
    record_path = root / 'records/cleaning' / (catalog['scope_version'] + '-' + rules['version'] + '.json')
    if record_path.exists():
        previous = json.loads(record_path.read_text('utf-8'))
        if any(previous[key] != value for key, value in provenance.items()):
            raise ValueError('changed inputs or implementation require a new cleaning version')
        for name in ('clean', 'text', 'quarantine', 'products', 'accounts', 'audit'):
            checked_file(record_path, previous[name + '_path'], previous[name + '_sha256'])
        print(json.dumps(previous, ensure_ascii=False, sort_keys=True))
        return 0
    directory = root / 'data/cleaning' / catalog['scope_version'] / rules['version']
    directory.mkdir(parents=True, exist_ok=True)
    clean_path = directory / 'reviews.jsonl'
    quarantine_path = directory / 'quarantine.jsonl'
    text_path = directory / 'valid-text.jsonl'
    products_path = directory / 'products.jsonl'
    accounts_path = directory / 'account-eligibility.jsonl'
    audit_path = directory / 'source-row-audit.jsonl'
    objects = {}
    in_window = 0
    windowed = []
    unknown = []
    for row, ref in zip(rows, refs, strict=True):
        utc = valid_time(row.get('timestamp'))
        if utc is None or row['timestamp'] < cutoff:
            if utc is None:
                unknown.append((row, ref))
            else:
                in_window += 1
                windowed.append((row, ref))
            key = canonical(row)
            if key not in objects:
                objects[key] = {'review': row, 'timestamp_ms': row.get('timestamp'),
                                'timestamp_utc': utc.isoformat(timespec='milliseconds') if utc is not None else None,
                                'source_references': []}
            objects[key]['source_references'].append(ref)
    clean = list(objects.values())
    quarantine = []
    for entry in clean:
        reasons = sorted(set(fact_reasons(entry['review'])) | {reason for ref in entry['source_references'] for reason in conflicts.get(ref['source_line'], [])})
        if reasons:
            entry['reasons'] = reasons
            quarantine.append(entry)
    clean = [entry for entry in clean if 'reasons' not in entry]
    clean_path.write_text(''.join(canonical(row) + '\n' for row in clean), 'utf-8')
    quarantine_path.write_text(''.join(canonical(row) + '\n' for row in quarantine), 'utf-8')
    text = [entry for entry in clean if isinstance(entry['review']['text'], str) and entry['review']['text'].strip()
            and type(entry['review']['rating']) in (int, float) and 1 <= entry['review']['rating'] <= 5]
    text_path.write_text(''.join(canonical(row) + '\n' for row in text), 'utf-8')
    raw_counts = Counter(row['parent_asin'] for row in rows)
    clean_counts = Counter(entry['review']['parent_asin'] for entry in clean)
    text_counts = Counter(entry['review']['parent_asin'] for entry in text)
    products = [{'parent_asin': parent, 'raw_reviews': raw_counts[parent],
                 'clean_reviews': clean_counts[parent], 'text_reviews': text_counts[parent]}
                for parent in sorted(source['product_review_counts'])]
    products_path.write_text(''.join(canonical(row) + '\n' for row in products), 'utf-8')
    accounts = account_eligibility(rows, windowed, unknown, text, rules)
    accounts_path.write_text(''.join(canonical(row) + '\n' for row in accounts), 'utf-8')
    audit = []
    for row, ref in zip(rows, refs, strict=True):
        entry = objects.get(canonical(row))
        representative = entry['source_references'][0]['source_line'] if entry else None
        disposition = ('outside_window' if entry is None else 'quarantined' if 'reasons' in entry else
                       'duplicate_copy' if ref['source_line'] != representative else 'retained')
        reasons = entry['reasons'] if entry and 'reasons' in entry else (
            ['outside_window'] if entry is None else ['exact_object_duplicate'] if disposition == 'duplicate_copy' else [])
        text_reasons = (entry['reasons'] if entry and 'reasons' in entry else ['outside_window'] if entry is None else
                        ['blank_text'] if not row['text'].strip() else [])
        audit.append({'source_reference': ref, 'disposition': disposition, 'reasons': reasons,
                      'representative_source_line': representative, 'text_exclusion_reasons': text_reasons})
    audit_path.write_text(''.join(canonical(row) + '\n' for row in audit), 'utf-8')
    report = {'stage': 'review_clean', 'status': 'cleaning_complete',
              **provenance, 'record_path': record_path.relative_to(root).as_posix(),
              'rules_version': rules['version'], 'clean_path': clean_path.relative_to(root).as_posix(),
              'quarantine_path': quarantine_path.relative_to(root).as_posix(),
              'text_path': text_path.relative_to(root).as_posix(),
              'products_path': products_path.relative_to(root).as_posix(),
              'accounts_path': accounts_path.relative_to(root).as_posix(),
              'audit_path': audit_path.relative_to(root).as_posix(),
              'counts': {'raw_accounts': len(accounts), 'qualified_accounts': sum(row['status'] == 'qualified' for row in accounts),
                         'clean_reviews': len(clean), 'text_reviews': len(text), 'quarantined_objects': len(quarantine),
                         'quarantined_source_rows': sum(len(row['source_references']) for row in quarantine),
                         'catalog_products': len(products)},
              'account_exclusions': Counter(row['reasons'][0] for row in accounts if row['reasons']),
              'window': {'cutoff_exclusive_ms': cutoff, 'raw_rows': len(rows),
                         'in_window_rows': in_window, 'outside_window_rows': len(rows) - in_window - len(unknown)},
              'unknown_time_rows': len(unknown),
              'duplicates': {'groups': sum(len(row['source_references']) > 1 for row in objects.values()),
                             'excess_rows': in_window + len(unknown) - len(objects)}}
    for name, path in {'clean': clean_path, 'text': text_path, 'quarantine': quarantine_path,
                       'products': products_path, 'accounts': accounts_path, 'audit': audit_path}.items():
        report[name + '_sha256'] = file_sha256(path)
    report.update(formal_clean_status='built', user_qualification_status='complete', user_split_status='not_built',
                  model_input_status='not_released', sim_status='not_built', sample_sufficiency='not_determined',
                  formal_package_status='not_built', access_scope='preparation_evaluation_only',
                  rules_path=cleaning_config.resolve().relative_to(project).as_posix(),
                  source_record_path=review_record.resolve().relative_to(project).as_posix(),
                  catalog_record_path=catalog_record.resolve().relative_to(project).as_posix(),
                  generated_at_utc=datetime.now(timezone.utc).isoformat(),
                  runtime={'python': sys.version, 'interpreter': sys.executable},
                  code_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=project, text=True).strip(),
                  stable_serialization='UTF-8 canonical JSON, sorted keys, LF; source order, lexical product/account order; no random sampling')
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n', 'utf-8')
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0
