"""Approved preference trial preparation; public use is through prepare_data.py."""

import json
from pathlib import Path
import hashlib
import hmac
import re
import sys
import tempfile
from datetime import datetime, timezone
from collections import Counter, defaultdict
from contextlib import ExitStack
from preference_text import project_text, TextError
from preference_access import ModelSession


PROJECT = Path(__file__).resolve().parent


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def strict_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate_json_key')
        value[key] = item
    return value


def reject_constant(value):
    raise ValueError('nonfinite_json_number')


def read_json(path):
    value = json.loads(path.read_text('utf-8'), object_pairs_hook=strict_object, parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise TaskError('invalid_task')
    return value


def read_rows(path):
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            value = json.loads(line, object_pairs_hook=strict_object, parse_constant=reject_constant)
            if not isinstance(value, dict):
                raise TaskError('invalid_task')
            yield value


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as stream:
        for row in rows:
            stream.write(json_bytes(row))


def project_path(path):
    path = Path(path).absolute()
    if path.drive.startswith('\\\\') or any(':' in p for p in path.parts[1:]):
        raise TaskError('invalid_task')
    resolved = path.resolve()
    if resolved != PROJECT and PROJECT not in resolved.parents:
        raise TaskError('invalid_task')
    for part in (path, *path.parents):
        if part == PROJECT.parent:
            break
        if part.is_symlink() or part.is_junction():
            raise TaskError('invalid_task')
    return resolved


def bound_path(base, binding):
    if (not isinstance(binding, dict) or set(binding) != {'path', 'sha256'}
            or not isinstance(binding['path'], str) or not isinstance(binding['sha256'], str)
            or not re.fullmatch('[0-9a-f]{64}', binding['sha256'])):
        raise TaskError('dependency_mismatch')
    path = project_path(base / binding['path'])
    if not path.is_file() or sha256(path) != binding['sha256']:
        raise TaskError('dependency_mismatch')
    return path


def load_inputs(cleaning_record, split_record, task_config):
    cleaning_record, split_record, task_config = map(project_path, (cleaning_record, split_record, task_config))
    rules = read_json(task_config)
    fixed = {'approval': 'approved', 'input_profile': 'text_portrait_trial_v1',
             'text_policy_version': 'finite-text-1.0.0', 'access_profile': 'api_only_no_host_io_v1'}
    if (not isinstance(rules, dict) or set(rules) != {*fixed, 'version', 'upstream_acceptances', 'identity_key', 'contract_version'}
            or any(rules.get(k) != v for k, v in fixed.items())
            or not isinstance(rules['version'], str) or not re.fullmatch(r'preference-task-\d+\.\d+\.\d+', rules['version'])
            or rules['contract_version'] != {'version': 'preference-task-1.0.0',
                'approved_document_sha256': '21c7cf2aa1b06c520564c5cfc18cd45eaab6d9f1e403bb7731ad94d58930b22a'}):
        raise TaskError('unapproved_protocol')
    source_root = cleaning_record.parent.parents[1]
    if split_record.parent.parents[1] != source_root:
        raise TaskError('dependency_mismatch')
    config_root = task_config.parent.parent
    accepts = rules['upstream_acceptances']
    if not isinstance(accepts, dict) or set(accepts) != {'cleaning', 'cleaning_erratum', 'split'}:
        raise TaskError('dependency_mismatch')
    ca, erratum, sa = [read_json(bound_path(config_root, accepts[n])) for n in ('cleaning', 'cleaning_erratum', 'split')]
    clean, split = read_json(cleaning_record), read_json(split_record)
    if (clean.get('stage') != 'review_clean' or clean.get('status') != 'cleaning_complete'
            or clean.get('formal_clean_status') != 'built' or clean.get('user_qualification_status') != 'complete'
            or ca.get('status') != 'accepted_ticket06_cleaning_and_qualification_only'
            or ca.get('counts') != clean.get('counts')
            or ca.get('dependencies_sha256', {}).get(cleaning_record.relative_to(source_root).as_posix()) != sha256(cleaning_record)
            or erratum.get('type') != 'metadata_erratum' or erratum.get('affected_field') != 'stable_serialization'
            or erratum.get('affected_record_sha256') != sha256(cleaning_record)
            or project_path(source_root / erratum.get('affected_record_path', '')) != cleaning_record):
        raise TaskError('dependency_mismatch')
    components = {}
    for name in ('clean', 'text', 'accounts', 'products', 'quarantine', 'audit'):
        path = bound_path(source_root, {'path': clean[name + '_path'], 'sha256': clean[name + '_sha256']})
        check = erratum.get('component_format_checks', {}).get(name, {})
        if (ca.get('component_sha256', {}).get(name) != sha256(path) or check.get('sha256') != sha256(path)
                or project_path(source_root / check.get('path', '')) != path):
            raise TaskError('dependency_mismatch')
        components[name] = path
    catalog_record_path = bound_path(source_root, {'path': clean['catalog_record_path'], 'sha256': clean['catalog_record_sha256']})
    catalog_record = read_json(catalog_record_path)
    components['catalog'] = bound_path(source_root, {'path': catalog_record['catalog_path'], 'sha256': catalog_record['catalog_sha256']})
    components['clean_rules'] = bound_path(source_root, {'path': clean['rules_path'], 'sha256': clean['rules_sha256']})
    if (split.get('stage') != 'user_split' or split.get('status') != 'split_complete'
            or split.get('user_split_status') != 'complete' or sa.get('status') != 'accepted_ticket07_split_component_only'
            or sa.get('counts') != split.get('counts') or sa.get('rules_version') != split.get('rules_version')
            or split.get('cleaning_record_sha256') != sha256(cleaning_record)
            or split.get('scope_version') != clean.get('scope_version')
            or split.get('catalog_sha256') != catalog_record['catalog_sha256']
            or clean.get('catalog_sha256') != catalog_record['catalog_sha256']
            or sa.get('dependencies_sha256', {}).get(split_record.relative_to(source_root).as_posix()) != sha256(split_record)):
        raise TaskError('dependency_mismatch')
    for name in ('accounts', 'exposure'):
        components['split_' + name] = bound_path(source_root, {'path': split[name + '_path'], 'sha256': split[name + '_sha256']})
        if sa.get('component_sha256', {}).get(name) != split[name + '_sha256']:
            raise TaskError('dependency_mismatch')
    components['identity_key'] = bound_path(config_root, rules['identity_key'])
    if len(components['identity_key'].read_bytes()) != 32:
        raise TaskError('dependency_mismatch')
    if not isinstance(clean.get('scope_version'), str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', clean['scope_version']):
        raise TaskError('dependency_mismatch')
    return rules, clean, split, components


def build_roots(rules, clean, split, components, parents):
    account_rows = list(read_rows(components['accounts']))
    split_rows = list(read_rows(components['split_accounts']))
    accounts = {a['user_id']: a for a in account_rows if a['status'] == 'qualified'}

    def invalid(users, code='invalid_task'):
        users = sorted(set(users))
        raise TaskError(code, {'accounts': len(users)},
                        [{'record_type': 'input_failure', 'source_user_id': u, 'code': code} for u in users])

    duplicates = [u for u, n in Counter(a['user_id'] for a in account_rows).items() if n > 1]
    if duplicates:
        invalid(duplicates)
    assignments = {a['user_id']: a for a in split_rows}
    mismatch = accounts.keys() ^ assignments.keys()
    if mismatch or len(assignments) != len(split_rows):
        invalid(mismatch or accounts.keys())
    if (len(account_rows) != clean['counts']['raw_accounts'] or len(accounts) != clean['counts']['qualified_accounts']
            or len(accounts) != split['counts']['qualified_accounts']
            or len(account_rows) != split['counts']['source_accounts']
            or sum(a['split'] == 'dev' for a in split_rows) != split['counts']['dev_accounts']
            or sum(a['split'] == 'test' for a in split_rows) != split['counts']['test_accounts']
            or any(a['split'] not in ('dev', 'test') for a in split_rows)
            or any(a['status'] not in ('qualified', 'excluded') for a in account_rows)):
        invalid(accounts)
    ledger, valid = defaultdict(list), defaultdict(list)
    cutoff = clean['window']['cutoff_exclusive_ms']
    clean_rules = read_json(components['clean_rules'])
    fixed = {'positive_min_rating': 4, 'minimum_prior_positive_products': 1,
             'cutoff_exclusive_ms': 1694550038852, 'seen_products': 'all_strict_prior_raw'}
    if any(type(clean_rules.get(k)) is not type(v) or clean_rules.get(k) != v for k, v in fixed.items()) or cutoff != clean_rules['cutoff_exclusive_ms']:
        raise TaskError('dependency_mismatch')
    for row in read_rows(components['clean']):
        review = row.get('review')
        if (not isinstance(review, dict) or not isinstance(review.get('user_id'), str) or not review['user_id']
                or review.get('parent_asin') not in parents or type(row.get('timestamp_ms')) is not int
                or not 0 <= row['timestamp_ms'] < cutoff or review.get('timestamp') != row['timestamp_ms']
                or type(review.get('rating')) not in (int, float) or not 1 <= review['rating'] <= 5
                or not isinstance(review.get('text'), str)):
            invalid(accounts)
        ledger[row['review']['user_id']].append(row)
    clean_fingerprints = {json_bytes(r) for rows in ledger.values() for r in rows}
    valid_fingerprints = set()
    for row in read_rows(components['text']):
        fingerprint = json_bytes(row)
        if fingerprint not in clean_fingerprints or fingerprint in valid_fingerprints or not row['review']['text'].strip():
            invalid(accounts)
        valid_fingerprints.add(fingerprint)
        valid[row['review']['user_id']].append(row)
    if (len(clean_fingerprints) != sum(map(len, ledger.values()))
            or valid_fingerprints != {json_bytes(r) for rows in ledger.values() for r in rows if r['review']['text'].strip()}):
        invalid(accounts)
    quarantine = defaultdict(list)
    for row in read_rows(components['quarantine']):
        quarantine[row['review']['user_id']].append(row)
    bad_time, bad_history = [], []
    for user, account in accounts.items():
        time = account.get('latest_timestamp_ms')
        seen = account.get('seen_parent_asins')
        values = ledger[user] + quarantine[user]
        if (type(time) is not int or not 0 <= time < cutoff or not isinstance(seen, list)
                or any(type(r.get('timestamp_ms')) is not int for r in values)
                or not values or max(r['timestamp_ms'] for r in values) != time
                or set(seen) != {r['review']['parent_asin'] for r in values if r['timestamp_ms'] < time}
                or len(seen) != len(set(seen)) or not set(seen) <= set(parents)
                or account.get('target_parent_asin') in seen
                or {r['review']['parent_asin'] for r in values if r['timestamp_ms'] == time} != {account.get('target_parent_asin')}):
            bad_time.append(user)
            continue
        target = [r for r in ledger[user] if r['timestamp_ms'] == time]
        positive = {r['review']['parent_asin'] for r in valid[user] if r['timestamp_ms'] < time and r['review']['rating'] >= 4}
        if (len(target) != 1 or target[0]['review']['rating'] < 4 or not target[0]['review']['text'].strip()
                or positive != set(account.get('prior_positive_parent_asins', []))
                or len(positive) != account.get('prior_positive_product_count') or not positive):
            bad_history.append(user)
    if bad_time or bad_history:
        invalid(bad_time + bad_history, 'invalid_time_or_candidate' if bad_time else 'invalid_task')
    background = [r for user, rows in ledger.items() if user not in assignments for r in rows]
    failures = []
    key = components['identity_key'].read_bytes()
    identities = {u: hmac.new(key, rules['version'].encode('utf-8') + b'\0' + u.encode('utf-8'), hashlib.sha256).hexdigest() for u in accounts}
    for user in sorted(accounts, key=lambda u: identities[u]):
        account = accounts[user]
        time = account['latest_timestamp_ms']
        target = [r for r in ledger[user] if r['timestamp_ms'] == time and r['review']['parent_asin'] == account['target_parent_asin']]
        if len(target) != 1:
            raise TaskError('invalid_task', {'accounts': 1})
        prior = sorted([r for r in valid[user] if r['timestamp_ms'] < time and r['review']['rating'] >= 4],
                       key=lambda r: (r['timestamp_ms'], r['review']['parent_asin'].encode('utf-8'), json_bytes(r['review'])))
        task_id = identities[user]
        history, history_audits = [], []
        for i, row in enumerate(prior):
            try:
                text, text_audit = project_text(row['review']['text'], 'history_body', user)
            except (TextError, UnicodeError):
                failures.append({'record_type': 'input_failure', 'source_user_id': user,
                    'code': 'text_processing_error', 'json_pointer': f'/history/{i}/text',
                    'source_references': row['source_references']})
                continue
            history.append({'parent_asin': row['review']['parent_asin'], 'timestamp_ms': row['timestamp_ms'],
                            'rating': row['review']['rating'], 'text': text})
            history_audits.append({**text_audit, 'json_pointer': f'/history/{i}/text',
                                   'source_component_sha256': clean['text_sha256'],
                                   'source_references': row['source_references']})
        if len(history) != len(prior):
            continue
        task = {'schema_version': 'preference-model-input-1.0.0', 'task_id': task_id,
                'catalog_version': clean['scope_version'], 'text_policy_version': rules['text_policy_version'],
                'metadata_time_basis': 'collection_snapshot', 'history_cutoff_exclusive_ms': time,
                'request': {'source': 'experiment_template', 'text': '根据较早正向评论和商品标题，对完整候选谷物商品按偏好排序。'},
                'history': history, 'seen_parent_asins': sorted(account['seen_parent_asins'], key=lambda p: p.encode('utf-8')),
                'candidate_parent_asins': [p for p in parents if p not in set(account['seen_parent_asins'])],
                'background_statistics': []}
        interactions, people, positive = Counter(), defaultdict(set), defaultdict(set)
        visible_times = []
        for row in background:
            if row['timestamp_ms'] < time:
                review = row['review']
                parent, account_id = review['parent_asin'], review['user_id']
                interactions[parent] += 1
                people[parent].add(account_id)
                if review['rating'] >= 4:
                    positive[parent].add(account_id)
                visible_times.append(row['timestamp_ms'])
        task['background_statistics'] = [{'parent_asin': p, 'interaction_count': interactions[p],
            'account_count': len(people[p]), 'positive_account_count': len(positive[p])}
            for p in task['candidate_parent_asins']]
        evaluation = {'task_id': task_id, 'source_user_id': user, 'split': assignments[user]['split'],
                      'target_timestamp_ms': time, 'target_parent_asin': account['target_parent_asin'],
                      'target_rating': target[0]['review']['rating'], 'target_review': target[0]['review'],
                      'target_source_references': target[0]['source_references'],
                      'reference_answer': {'positive_parent_asins': [account['target_parent_asin']],
                                           'other_candidates': 'unobserved_unlabeled'}}
        audit = {'record_type': 'task', 'task_id': task_id, 'history': history_audits, 'background': {
                'pool_events': len(background), 'visible_events': len(visible_times),
                'min_timestamp_ms': min(visible_times, default=None), 'max_timestamp_ms': max(visible_times, default=None),
                'excluded_accounts_sha256': hashlib.sha256(json_bytes(sorted(assignments))).hexdigest()}}
        yield task, evaluation, audit
    if failures:
        raise TaskError('text_processing_error', {'accounts': len({f['source_user_id'] for f in failures}),
                        'history_events': len(failures)}, failures)


class TaskError(ValueError):
    def __init__(self, code, counts=None, failures=None):
        super().__init__(code)
        self.code = code
        self.counts = counts or {}
        self.failures = failures or []


def probe_channel(base, probe):
    manifest = read_json(project_path(base / 'model/manifest.json'))
    if set(manifest) != {'schema_version', 'text_policy_version', 'components'} or set(manifest['components']) != {'catalog.jsonl', 'tasks.jsonl'}:
        raise TaskError('unsafe_model_view')
    paths = {name: bound_path(base / 'model', {'path': name, 'sha256': value['sha256']})
             for name, value in manifest['components'].items()}
    try:
        requests = list(read_rows(project_path(probe)))
    except (OSError, ValueError):
        raise TaskError('invalid_probe') from None
    if not requests or any(not isinstance(r, dict) or set(r) != {'session_task_id', 'operation', 'arguments'}
           or not isinstance(r['session_task_id'], str) or not re.fullmatch('[0-9a-f]{64}', r['session_task_id'])
           or r['operation'] not in ('model_request', 'read_resource', 'invoke_tool')
           or not isinstance(r['arguments'], dict) for r in requests):
        raise TaskError('invalid_probe')
    wanted = {r['session_task_id'] for r in requests}
    catalog = list(read_rows(paths['catalog.jsonl']))
    sessions = {}
    try:
        for task in read_rows(paths['tasks.jsonl']):
            if task['task_id'] in wanted:
                sessions[task['task_id']] = ModelSession(task, catalog)
    except ValueError:
        raise TaskError('unsafe_model_view') from None
    for index, request in enumerate(requests):
        session = sessions.get(request['session_task_id'])
        response = session.dispatch(request['operation'], request['arguments']) if session else {'status': 'access_denied'}
        yield {'probe_index': index, 'operation': request['operation'], 'response': response}


def write_bundle(base, rules, clean, split, components, products, catalog_audits, access_probe):
    write_rows(base / 'model/catalog.jsonl', products)
    counts = Counter(catalog_products=len(products))
    text_counts = {kind: Counter(fields=0, raw_codepoints=0, processed_codepoints=0,
                                raw_utf8_bytes=0, processed_utf8_bytes=0, changed_fields=0)
                   for kind in ('product_title', 'history_body')}
    operations = {kind: Counter() for kind in text_counts}

    def count_text(kind, audit):
        text_counts[kind]['fields'] += 1
        for name in ('raw_codepoints', 'processed_codepoints', 'raw_utf8_bytes', 'processed_utf8_bytes'):
            text_counts[kind][name] += audit[name]
        text_counts[kind]['changed_fields'] += audit['original_sha256'] != audit['processed_sha256']
        text_counts[kind]['max_raw_codepoints'] = max(text_counts[kind]['max_raw_codepoints'], audit['raw_codepoints'])
        text_counts[kind]['max_processed_codepoints'] = max(text_counts[kind]['max_processed_codepoints'], audit['processed_codepoints'])
        operations[kind].update(audit['operations'])

    with ExitStack() as stack:
        files = []
        for name in ('model/tasks.jsonl', 'private/evaluation.jsonl', 'private/task-audit.jsonl'):
            path = base / name
            path.parent.mkdir(parents=True, exist_ok=True)
            files.append(stack.enter_context(path.open('wb')))
        for audit in sorted(catalog_audits, key=lambda a: a['parent_asin'].encode('utf-8')):
            files[2].write(json_bytes(audit))
            count_text('product_title', audit)
        for task, evaluation, audit in build_roots(rules, clean, split, components, [p['parent_asin'] for p in products]):
            try:
                ModelSession(task, products)
            except ValueError:
                raise TaskError('unsafe_model_view') from None
            for stream, row in zip(files, (task, evaluation, audit)):
                stream.write(json_bytes(row))
            counts['root_tasks'] += 1
            counts['history_events'] += len(task['history'])
            counts[evaluation['split'] + '_accounts'] += 1
            counts['candidate_references'] += len(task['candidate_parent_asins'])
            counts['max_history_codepoints_per_task'] = max(counts['max_history_codepoints_per_task'],
                                                           sum(len(h['text']) for h in task['history']))
            for item in audit['history']:
                count_text('history_body', item)
    manifest = {'schema_version': 'preference-model-input-1.0.0', 'text_policy_version': rules['text_policy_version'],
                'components': {name: {'sha256': sha256(base / 'model' / name)} for name in ('catalog.jsonl', 'tasks.jsonl')}}
    (base / 'model/manifest.json').write_bytes(json_bytes(manifest))
    if access_probe is not None:
        write_rows(base / 'private/access-probe.jsonl', probe_channel(base, access_probe))
    return dict(counts), {k: {**v, 'operations': dict(operations[k])} for k, v in text_counts.items()}


def _prepare_tasks(cleaning_record, split_record, task_config, root, access_probe=None):
    root = project_path(root)
    rules, clean, split, components = load_inputs(cleaning_record, split_record, task_config)
    if access_probe is not None:
        access_probe = project_path(access_probe)
    signature = {'inputs_sha256': {name: sha256(project_path(path)) for name, path in (
        ('cleaning_record', cleaning_record), ('split_record', split_record), ('task_config', task_config))},
        'access_probe_sha256': sha256(access_probe) if access_probe is not None else None,
        'producer_sha256': {name: sha256(PROJECT / name) for name in (
            'prepare_data.py', 'preference_tasks.py', 'preference_text.py', 'preference_access.py')}}
    base = project_path(root / 'data/preference-tasks' / clean['scope_version'] / rules['version'])
    record_path = project_path(root / 'records/preference-tasks' / (clean['scope_version'] + '-' + rules['version'] + '.json'))
    names = {'catalog': 'model/catalog.jsonl', 'tasks': 'model/tasks.jsonl', 'model_manifest': 'model/manifest.json',
             'evaluation': 'private/evaluation.jsonl', 'audit': 'private/task-audit.jsonl'}
    if access_probe is not None:
        names['access_probe'] = 'private/access-probe.jsonl'
    if record_path.exists():
        try:
            old = read_json(project_path(record_path))
            if old['signature'] != signature or set(old['components']) != set(names):
                raise ValueError()
            for name, relative in names.items():
                path = bound_path(root, old['components'][name])
                if path != project_path(base / relative):
                    raise ValueError()
        except (OSError, ValueError, KeyError, TypeError):
            raise TaskError('output_conflict') from None
        print(json.dumps(old, sort_keys=True))
        return 0
    if base.exists():
        raise TaskError('output_conflict')
    products, catalog_audits, failures = [], [], []
    catalog = list(read_rows(components['catalog']))
    if len(catalog) != clean['counts']['catalog_products'] or len({r['parent_asin'] for r in catalog}) != len(catalog):
        raise TaskError('invalid_task', {'products': abs(len(catalog) - clean['counts']['catalog_products']),
                        'accounts': clean['counts']['qualified_accounts']})
    for row in catalog:
        try:
            title, audit = project_text(row['metadata']['title'], 'product_title')
        except (TextError, UnicodeError) as exc:
            failures.append({'record_type': 'input_failure', 'parent_asin': row['parent_asin'],
                'code': str(exc) if isinstance(exc, TextError) else 'text_processing_error',
                'source_line': row.get('source_line'), 'json_pointer': '/metadata/title'})
            continue
        products.append({'parent_asin': row['parent_asin'], 'title': title, 'crop': row['crop']})
        catalog_audits.append({**audit, 'record_type': 'catalog_text', 'parent_asin': row['parent_asin'],
                               'json_pointer': '/metadata/title', 'source_component_sha256': clean['catalog_sha256'],
                               'source_line': row.get('source_line'), 'source_sha256': row.get('source_sha256')})
    if failures:
        bad = {f['parent_asin'] for f in failures}
        parents = {r['parent_asin'] for r in catalog}
        affected = [a['user_id'] for a in read_rows(components['accounts']) if a['status'] == 'qualified'
                    and bad & ((parents - set(a['seen_parent_asins'])) | set(a['prior_positive_parent_asins']))]
        for failure in failures:
            failure['affected_source_accounts'] = affected
        raise TaskError('embedded_dynamic_unhandled' if any(f['code'] == 'embedded_dynamic_unhandled' for f in failures)
                        else 'text_processing_error', {'products': len(failures), 'accounts': len(affected)}, failures)
    products.sort(key=lambda p: p['parent_asin'].encode('utf-8'))
    (PROJECT / '.tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ticket08-', dir=PROJECT / '.tmp') as temporary:
        staged = Path(temporary) / 'bundle'
        counts, text_summary = write_bundle(staged, rules, clean, split, components, products, catalog_audits, access_probe)
        bindings = {name: {'path': (base / relative).relative_to(root).as_posix(),
                           'sha256': sha256(staged / relative)} for name, relative in names.items()}
        base.parent.mkdir(parents=True, exist_ok=True)
        staged.rename(base)
    report = {'stage': 'preference_tasks', 'status': 'preference_trial_prepared',
              'rules_version': rules['version'], 'input_profile': rules['input_profile'],
              'text_policy_version': rules['text_policy_version'], 'access_profile': rules['access_profile'],
              'counts': counts, 'text_summary': text_summary, 'signature': signature, 'components': bindings,
              'construction_failures': {'products': 0, 'history_events': 0, 'accounts': 0},
              'sources': {name: {'path': project_path(path).relative_to(PROJECT).as_posix(),
                                 'sha256': signature['inputs_sha256'][name]} for name, path in (
                  ('cleaning_record', cleaning_record), ('split_record', split_record), ('task_config', task_config))},
              'record_path': record_path.relative_to(root).as_posix(),
              'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'runtime': {'python': sys.version.split()[0], 'executable': sys.executable},
              'input_contract_status': 'validated', 'text_processing_status': 'validated',
              'model_input_status': 'prepared_not_executed', 'interaction_training_status': 'not_built',
              'access_probe_status': 'completed' if access_probe is not None else 'not_run',
              'capabilities': ModelSession.capabilities(), 'access_isolation_acceptance': 'pending_independent_acceptance',
              'formal_package_status': 'not_built', 'sim_status': 'not_built',
              'sample_sufficiency': 'not_determined', 'model_execution_status': 'not_run'}
    record_path.parent.mkdir(parents=True, exist_ok=True)
    with record_path.open('xb') as stream:
        stream.write(json_bytes(report))
    print(json.dumps(report, sort_keys=True))
    return 0


def prepare_tasks(cleaning_record, split_record, task_config, root, access_probe=None):
    try:
        return _prepare_tasks(cleaning_record, split_record, task_config, root, access_probe)
    except TaskError as exc:
        if exc.failures:
            path = project_path(root) / 'data/preference-failures' / (sha256(task_config) + '.jsonl')
            if not path.exists():
                write_rows(path, exc.failures)
        raise
