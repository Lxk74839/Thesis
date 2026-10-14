"""Approved account split component, reached through prepare_data.py only."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


PROJECT = Path(__file__).resolve().parent


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path):
    value = json.loads(path.read_text('utf-8'))
    if not isinstance(value, dict):
        raise ValueError('expected_json_object')
    return value


def read_rows(path):
    rows = [json.loads(line) for line in path.read_text('utf-8').splitlines()]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError('expected_json_object_rows')
    return rows


def project_file(path):
    path = path.resolve()
    if PROJECT not in path.parents:
        raise ValueError('input_path_outside_project')
    return path


def bound_path(base, binding):
    path = project_file(base / binding['path'])
    if sha256(path) != binding['sha256']:
        raise ValueError('source_checksum_mismatch')
    return path


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def split_users(cleaning_record, split_config, root, group_refs=None):
    cleaning_record = project_file(cleaning_record)
    split_config = project_file(split_config)
    if group_refs is not None:
        group_refs = project_file(group_refs)
    clean = read_json(cleaning_record)
    rules = read_json(split_config)
    approved = {'approval': 'approved', 'scheme': 'A',
                'salt': 'Thesis-ticket07-grain-A-1.1.15-review-cleaning-1.0.0-split-v1',
                'hash': 'sha256', 'hash_input': 'utf8_salt_nul_exact_user_id',
                'sort': 'digest_bytes_then_user_id_utf8_bytes', 'development_divisor': 5,
                'rounding': 'floor', 'legacy_policy': 'force_exploratory_to_dev',
                'unknown_reading_policy': 'retain_unknown_allow_other_legacy'}
    if any(type(rules.get(k)) is not type(v) or rules.get(k) != v for k, v in approved.items()) or not isinstance(rules.get('version'), str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*', rules['version']):
        raise ValueError('rules_not_approved')
    source_root = cleaning_record.resolve().parent.parents[1]
    config_root = split_config.resolve().parent.parent
    acceptance = read_json(bound_path(config_root, rules['cleaning_acceptance']))
    erratum = read_json(bound_path(config_root, rules['cleaning_erratum']))
    if (not isinstance(clean.get('counts'), dict) or not isinstance(acceptance.get('component_sha256'), dict)
            or not isinstance(acceptance.get('dependencies_sha256'), dict)
            or not isinstance(erratum.get('component_format_checks'), dict)):
        raise ValueError('invalid_cleaning_acceptance_metadata')
    if (clean.get('stage') != 'review_clean' or clean.get('status') != 'cleaning_complete'
            or clean.get('formal_clean_status') != 'built' or clean.get('user_qualification_status') != 'complete'
            or not isinstance(clean.get('scope_version'), str)
            or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*', clean['scope_version'])
            or acceptance.get('status') != 'accepted_ticket06_cleaning_and_qualification_only'
            or acceptance.get('counts') != clean.get('counts')):
        raise ValueError('cleaning_not_accepted')
    clean_sha = sha256(cleaning_record)
    dependencies = acceptance.get('dependencies_sha256', {})
    if dependencies.get(cleaning_record.resolve().relative_to(source_root).as_posix()) != clean_sha:
        raise ValueError('acceptance_does_not_bind_cleaning_record')
    for relative, digest in dependencies.items():
        bound_path(source_root, {'path': relative, 'sha256': digest})
    if (erratum.get('type') != 'metadata_erratum' or erratum.get('affected_field') != 'stable_serialization'
            or erratum.get('affected_record_sha256') != clean_sha
            or (source_root / erratum.get('affected_record_path', '')).resolve() != cleaning_record.resolve()):
        raise ValueError('cleaning_erratum_mismatch')
    fact_path = bound_path(config_root, rules['exposure_manifest'])
    fact = read_json(fact_path)
    if fact.get('account_component_sha256') != clean['accounts_sha256']:
        raise ValueError('exposure_qualification_binding_mismatch')
    components = {name: bound_path(source_root, {'path': clean[name+'_path'], 'sha256': clean[name+'_sha256']})
                  for name in ('clean', 'text', 'quarantine', 'products', 'accounts', 'audit')}
    for name, path in components.items():
        description = erratum.get('component_format_checks', {}).get(name, {})
        if (acceptance.get('component_sha256', {}).get(name) != clean[name+'_sha256']
                or description.get('sha256') != clean[name+'_sha256']
                or (source_root / description.get('path', '')).resolve() != path):
            raise ValueError('accepted_component_binding_mismatch')
    accounts_path = components['accounts']
    all_accounts = read_rows(accounts_path)
    seen = set()
    for account in all_accounts:
        user = account.get('user_id')
        if not isinstance(user, str) or not user.strip() or user in seen:
            raise ValueError('invalid_or_duplicate_account_identity')
        seen.add(user)
        if account.get('status') not in ('qualified', 'excluded'):
            raise ValueError('invalid_qualification_status')
    qualified = {a['user_id']: a for a in all_accounts if a['status'] == 'qualified'}
    if len(all_accounts) != clean['counts']['raw_accounts'] or len(qualified) != clean['counts']['qualified_accounts'] or not qualified:
        raise ValueError('qualification_counts_mismatch')
    set_names = ('legacy_qualification', 'legacy_mechanism', 'legacy_corpus', 'legacy_preference')
    if (fact.get('version') != 'legacy-exposure-1.0.0' or fact.get('access_scope') != 'preparation_evaluation_only'
            or not isinstance(fact.get('sets'), dict) or set(fact['sets']) != set(set_names)
            or not isinstance(fact.get('evidence'), dict) or 'current_aggregate' not in fact['evidence']):
        raise ValueError('invalid_exposure_manifest')
    legacy = {}
    for name in set_names:
        values = fact['sets'][name]
        description = fact['evidence'].get(name, {})
        if (not isinstance(values, list) or any(not isinstance(u, str) or not u.strip() for u in values)
                or len(set(values)) != len(values) or not isinstance(description, dict)
                or description.get('account_count') != len(values)):
            raise ValueError('invalid_exposure_manifest')
        legacy[name] = set(values)
    if not (legacy['legacy_qualification'] | legacy['legacy_mechanism'] | legacy['legacy_preference']) <= legacy['legacy_corpus']:
        raise ValueError('invalid_exposure_membership')
    forced = qualified.keys() & (legacy['legacy_qualification'] | legacy['legacy_mechanism'])
    observed = {}
    if not isinstance(fact.get('observed_agent_results'), list):
        raise ValueError('invalid_result_exposure_evidence')
    for observation in fact['observed_agent_results']:
        if (not isinstance(observation, dict) or not isinstance(observation.get('user_id'), str)
                or observation['user_id'] not in legacy['legacy_corpus'] or observation['user_id'] in observed
                or observation.get('evidence') not in fact['evidence']):
            raise ValueError('invalid_result_exposure_evidence')
        observed[observation['user_id']] = observation['evidence']
    if not observed.keys() & qualified.keys() <= forced:
        raise ValueError('known_result_exposure_outside_approved_development_set')
    digests = {u: hashlib.sha256(rules['salt'].encode('utf-8') + b'\0' + u.encode('utf-8')).digest() for u in qualified}
    ordered = sorted(qualified, key=lambda u: (digests[u], u.encode('utf-8')))
    dev_count = len(qualified) // 5
    if len(forced) > dev_count:
        raise ValueError('forced_development_exceeds_quota')
    development = forced | set([u for u in ordered if u not in forced][:dev_count-len(forced)])
    assignments = [{'user_id': u, 'split_hash': digests[u].hex(),
                    'split': 'dev' if u in development else 'test',
                    'assignment_reason': 'legacy_forced' if u in forced else 'hash_fill' if u in development else 'hash_remainder'}
                   for u in ordered]
    references = []
    if group_refs is not None:
        identifiers = set()
        for reference in read_rows(group_refs):
            identity = reference.get('reference_id')
            user = reference.get('user_id')
            if (set(reference) != {'reference_id', 'user_id'} or not isinstance(identity, str)
                    or not identity.strip() or identity in identifiers or not isinstance(user, str) or user not in qualified):
                raise ValueError('invalid_group_reference')
            identifiers.add(identity)
            references.append({'reference_id': identity, 'user_id': user, 'split': 'dev' if user in development else 'test'})
        references.sort(key=lambda row: row['reference_id'].encode('utf-8'))
    exposures = []
    for u in ordered:
        evidence = [k for k, values in legacy.items() if u in values]
        if u in observed:
            evidence.append(observed[u])
        exposures.append({'user_id': u, **{k + '_member': u in values for k, values in legacy.items()},
                          'current_program_processing': 'observed',
                          'legacy_program_processing': 'observed' if u in legacy['legacy_corpus'] else 'unknown',
                          'aggregate_review': 'current_stage1_cohort_observed',
                          'agent_account_result_view': 'observed' if u in observed else 'unknown',
                          'human_account_result_view': 'unknown', 'evidence': sorted(evidence + ['current_aggregate'])})
    catalog_record_path = bound_path(source_root, {'path': clean['catalog_record_path'], 'sha256': clean['catalog_record_sha256']})
    catalog_record = read_json(catalog_record_path)
    catalog_rows = read_rows(bound_path(source_root, {'path': catalog_record['catalog_path'], 'sha256': catalog_record['catalog_sha256']}))
    catalog = {r['parent_asin']: r for r in catalog_rows}
    if len(catalog) != len(catalog_rows) or len(catalog) != clean['counts']['catalog_products']:
        raise ValueError('qualification_catalog_mismatch')
    for account in qualified.values():
        history = account.get('prior_positive_parent_asins')
        seen_products = account.get('seen_parent_asins')
        if (not isinstance(history, list) or not isinstance(seen_products, list)
                or any(not isinstance(p, str) or p not in catalog for p in history + seen_products)
                or len(set(history)) != len(history) or not history
                or type(account.get('prior_positive_product_count')) is not int
                or account['prior_positive_product_count'] != len(history)
                or account.get('target_parent_asin') not in catalog
                or account['target_parent_asin'] in seen_products or not set(history) <= set(seen_products)):
            raise ValueError('qualification_catalog_mismatch')

    def statistics(users):
        targets = Counter(qualified[u]['target_parent_asin'] for u in users)
        return {'accounts': len(users), 'legacy_exploratory_accounts': len(users & forced),
                'legacy_corpus_accounts': len(users & legacy['legacy_corpus']),
                'known_agent_result_accounts': len(users & observed.keys()),
                'unknown_agent_result_accounts': len(users - observed.keys()),
                'unknown_human_result_accounts': len(users),
                'history_depth_distribution': Counter(qualified[u]['prior_positive_product_count'] for u in users),
                'history_parent_products': len({p for u in users for p in qualified[u]['prior_positive_parent_asins']}),
                'target_parent_products': len(targets),
                'target_crops': Counter(catalog[qualified[u]['target_parent_asin']]['crop'] for u in users),
                'target_top1_accounts': max(targets.values(), default=0),
                'target_hhi': sum((n/len(users))**2 for _, n in sorted(targets.items()))}

    version = rules['version']
    scope = clean['scope_version']
    directory = root / 'data/splits' / scope / version
    record_path = root / 'records/splits' / (scope + '-' + version + '.json')
    if any(root not in path.resolve().parents or path.resolve() != path.absolute()
           for path in (directory, record_path, record_path.with_suffix('.json.partial'))):
        raise ValueError('output_path_outside_output_root')
    paths = {'accounts': directory / 'accounts.jsonl', 'exposure': directory / 'exposure.jsonl'}
    payloads = {'accounts': b''.join(json_bytes(row) for row in assignments),
                'exposure': b''.join(json_bytes(row) for row in exposures)}
    if group_refs is not None:
        paths['references'] = directory / 'reference-groups.jsonl'
        payloads['references'] = b''.join(json_bytes(row) for row in references)
    report = {'stage': 'user_split', 'status': 'split_complete', 'user_split_status': 'complete',
              'scope_version': scope, 'rules_version': version, 'release_status': 'split_component_only',
              'access_scope': 'preparation_evaluation_only', 'formal_package_status': 'not_built',
              'model_input_status': 'not_released', 'sim_status': 'not_built',
              'sample_sufficiency': 'not_determined', 'blind_test_claim': False,
              'record_path': record_path.relative_to(root).as_posix(),
              'rules_sha256': sha256(split_config), 'cleaning_record_sha256': sha256(cleaning_record),
              'cleaning_acceptance_sha256': rules['cleaning_acceptance']['sha256'],
              'cleaning_erratum_sha256': rules['cleaning_erratum']['sha256'],
              'cleaning_component_sha256': {name: clean[name+'_sha256'] for name in components},
              'catalog_record_sha256': clean['catalog_record_sha256'], 'catalog_sha256': catalog_record['catalog_sha256'],
              'exposure_manifest_sha256': sha256(fact_path),
              'group_refs_sha256': sha256(group_refs) if group_refs is not None else None,
              'producer_sha256': {name: sha256(PROJECT / name) for name in ('prepare_data.py', 'user_splitting.py')},
              'counts': {'source_accounts': len(all_accounts), 'qualified_accounts': len(qualified),
                         'dev_accounts': len(development), 'test_accounts': len(qualified)-len(development),
                         'forced_dev_accounts': len(forced), 'hash_fill_dev_accounts': len(development-forced),
                         'reference_rows': len(references)},
              'groups': {'dev': statistics(development), 'test': statistics(qualified.keys()-development)},
              'source_account_counts': {k: len(v) for k, v in legacy.items()},
              'source_evidence': fact['evidence'],
              'runtime': {'python': sys.version, 'interpreter': sys.executable},
              'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT, text=True).strip(),
              'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'stable_serialization': 'UTF-8 without BOM; explicit LF; compact sorted-key JSON; digest then exact user UTF-8 bytes'}
    for name, path in paths.items():
        report[name+'_path'] = path.relative_to(root).as_posix()
        report[name+'_sha256'] = hashlib.sha256(payloads[name]).hexdigest()
    report = json.loads(json_bytes(report))
    if record_path.exists():
        previous = read_json(record_path)
        stable_keys = report.keys() - {'generated_at_utc', 'code_commit'}
        if set(previous) != set(report) or any(previous.get(k) != report[k] for k in stable_keys):
            raise ValueError('existing_split_provenance_mismatch_requires_new_version')
        if any(not path.is_file() or sha256(path) != report[name+'_sha256'] for name, path in paths.items()):
            raise ValueError('existing_split_component_checksum_mismatch')
        print(json.dumps(previous, ensure_ascii=False, sort_keys=True))
        return 0
    if directory.exists() or record_path.with_suffix('.json.partial').exists():
        raise ValueError('split_output_already_exists_without_record')
    directory.mkdir(parents=True)
    for name, path in paths.items():
        path.write_bytes(payloads[name])
    record_path.parent.mkdir(parents=True, exist_ok=True)
    partial = record_path.with_suffix('.json.partial')
    partial.write_bytes(json_bytes(report))
    partial.replace(record_path)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0
