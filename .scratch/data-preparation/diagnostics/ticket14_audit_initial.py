"""Ticket14: bind accepted evidence and reconcile stored counts; no generation/scoring."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / '.scratch/data-preparation/verification/ticket14-20261016'
BASE = '3c565eb9fd5e4240bbcc214111655ca394a0a3a8'
PREFIX = '.scratch/data-preparation/verification/'
JOINT = 'data/joint-tasks/grain-A-1.1.15/joint-task-package-0.1.0/'
REF = 'data/joint-reference/grain-A-1.1.15/joint-task-package-0.1.0/joint-reference-0.1.0/'


def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def save(name, value):
    with (OUT / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def fingerprint(name):
    path = ROOT / name
    digest = hashlib.sha256()
    size = lines = 0
    with path.open('rb') as stream:
        while block := stream.read(4 * 1024**2):
            digest.update(block)
            size += len(block)
            if path.suffix == '.jsonl':
                lines += block.count(b'\n')
    return {'path': name, 'bytes': size, 'sha256': digest.hexdigest(),
            **({'records': lines} if path.suffix == '.jsonl' else {})}


assert Path(sys.prefix).resolve() == (ROOT / '.conda/envs/Thesis').resolve()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == BASE
assert load(PREFIX + 'ticket13-delivery-evidence.json')['sample_sufficiency'] == 'not_determined'
expected = {}
contexts = {}


def add(binding, origin):
    name = binding['path'].replace('\\', '/')
    path = ROOT / name
    if not path.is_absolute() or ROOT not in path.resolve().parents:
        raise ValueError('non_project_binding')
    item = {k: binding[k] for k in ('sha256', 'bytes', 'records') if k in binding}
    if path.suffix != '.jsonl':
        item.pop('records', None)  # JSON/program records use mixed logical/physical conventions.
    prior = expected.setdefault(name, {})
    for key, value in item.items():
        if key in prior and prior[key] != value:
            raise ValueError(f'conflicting_binding:{name}:{key}')
        prior[key] = value
    contexts.setdefault(name, set()).add(origin)


def collect(value, origin):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str):
            add(value, origin)
        for child in value.values():
            collect(child, origin)
    elif isinstance(value, list):
        for child in value:
            collect(child, origin)


freeze_name = PREFIX + 'ticket13-delivery-evidence.json'
add({'path': freeze_name, 'sha256': '02e50d4ca97b1f64e898227591ad8c368ee1dd492e05c2614132245969344545'}, 'baseline13')
evidence_files = [freeze_name,
 'records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0-acceptance.json',
 'records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0.json',
 JOINT + 'package-manifest.json', REF + 'check.json',
 'records/sim/grain-A-1.1.15-sim-normal-1.0.0-acceptance.json',
 'records/sim-scenarios/grain-A-1.1.15-sim-scenarios-1.0.0-acceptance.json',
 'records/sim-quality/grain-A-1.1.15-sim-quality-fusion-0.1.0-acceptance.json']
for name in evidence_files:
    collect(load(name), name)
for name in ('amazon-2023-grocery-metadata', 'amazon-2023-grocery-reviews'):
    record = load(f'records/sources/{name}.json')
    add({'path': record['raw_path'], 'bytes': record['download']['bytes'],
         'sha256': record['download']['sha256']}, f'records/sources/{name}.json')
for entry in load(PREFIX + 'original-materials.json')['files']:
    add(entry, PREFIX + 'original-materials.json')
for name in ('review-cleaning-1.0.0', 'user-split-1.0.0', 'ticket08-1.0.1'):
    suffix = '-independent-full-check.json' if name == 'ticket08-1.0.1' else '-independent-check.json'
    file = PREFIX + name + suffix
    # These reports are already bound by the accepted 06/07/08 dependency lists.
    for record_name in (
      'records/cleaning/grain-A-1.1.15-review-cleaning-1.0.0-acceptance.json',
      'records/splits/grain-A-1.1.15-user-split-1.0.0-acceptance.json',
      'records/preference-tasks/grain-A-1.1.15-preference-task-1.0.1-acceptance.json'):
        deps = load(record_name).get('dependencies_sha256', {})
        if file in deps:
            add({'path': file, 'sha256': deps[file]}, record_name)
assert all(PREFIX + n in expected for n in (
 'review-cleaning-1.0.0-independent-check.json',
 'user-split-1.0.0-independent-check.json',
 'ticket08-1.0.1-independent-full-check.json'))

receipts, failures = [], []
for index, (name, binding) in enumerate(sorted(expected.items()), 1):
    actual = fingerprint(name)
    mismatches = [key for key, value in binding.items() if actual.get(key) != value]
    item = {**actual, 'origins': sorted(contexts[name]), 'mismatches': mismatches}
    if name.endswith('id-key.bin'):
        item.pop('sha256')
        item['digest_redacted'] = True
    receipts.append(item)
    if mismatches:
        failures.append({'path': name, 'fields': mismatches})
    if index % 80 == 0:
        print(f'bound_files_checked={index}', flush=True)
save('binding-receipts.json', receipts)
save('binding-summary.json', {'status': 'passed' if not failures else 'failed',
 'files': len(receipts), 'bytes': sum(r['bytes'] for r in receipts), 'failures': failures,
 'method': 'streamed_current_bytes_and_JSONL_line_counts_against_accepted_bindings',
 'no_generation_no_scoring_no_reproduction': True})
if failures:
    print(json.dumps({'binding_failures': failures}))
    raise SystemExit(2)

sources = [load(f'records/sources/amazon-2023-grocery-{kind}.json') for kind in ('metadata', 'reviews')]
catalog = load('records/catalog/grain-A-1.1.15.json')
selected = load('records/reviews/grain-A-1.1.15-review-diagnostics-1.0.0.json')
clean = load('records/cleaning/grain-A-1.1.15-review-cleaning-1.0.0.json')
split = load('records/splits/grain-A-1.1.15-user-split-1.0.0.json')
pref = load(PREFIX + 'ticket08-1.0.1-independent-full-check.json')
p0 = load(PREFIX + 'ticket12-p0-20261016-aggregate.json')
coverage = load(REF + 'coverage.json')
joint = load(REF + 'check.json')
equations = []


def equal(name, left, right, evidence):
    equations.append({'name': name, 'left': left, 'right': right,
                      'passed': left == right, 'evidence': evidence})


equal('metadata_scope_partition', sources[0]['scan']['records'], sum(catalog['counts'].values()), 'catalog')
equal('metadata_review_parent_partition', sources[0]['scan']['unique_parents'],
      sum(sources[1]['association'][key] for key in ('metadata_parents_with_reviews', 'metadata_parents_without_reviews')), 'source_reviews')
equal('review_source_partition', sources[1]['scan']['records'],
      selected['scan']['matched_rows'] + selected['scan']['other_parent_rows'], 'selected')
equal('source_to_clean', selected['raw']['reviews'],
      clean['counts']['clean_reviews'] + clean['duplicates']['excess_rows'] + clean['counts']['quarantined_source_rows'], 'clean')
equal('window_partition', clean['window']['raw_rows'],
      clean['window']['in_window_rows'] + clean['window']['outside_window_rows'], 'clean')
equal('account_qualification_partition', clean['counts']['raw_accounts'],
      clean['counts']['qualified_accounts'] + sum(clean['account_exclusions'].values()), 'clean')
equal('account_split', clean['counts']['qualified_accounts'],
      split['counts']['dev_accounts'] + split['counts']['test_accounts'], 'split')
equal('background_account_partition', clean['counts']['raw_accounts'],
      pref['background_pool_accounts'] + pref['counts']['root_tasks'], '08_full_check')
equal('background_event_partition', clean['counts']['clean_reviews'],
      pref['background_pool_events'] + pref['removed_evaluation_events'], '08_full_check')
equal('complete_candidate_partition', pref['counts']['root_tasks'] * catalog['counts']['included'],
      pref['counts']['candidate_references'] + 1845, '08_complete_C_equals_catalog_minus_all_seen')
equal('candidate_reuse', pref['counts']['candidate_references'],
      joint['projection_validation']['complete_candidate_references'], '13_check')
equal('root_conservation', pref['counts']['root_tasks'], joint['roots'], '13_check')
equal('view_bindings', joint['roots'] * 10, load(freeze_name)['counts']['planned_view_bindings'], '13_freeze')
equal('Q_association_rows', joint['roots'] * 2, load(freeze_name)['counts']['q_association_rows'], '13_freeze')
equal('reference_index_rows', catalog['counts']['included'] * 10, joint['reference_rows'], '13_check')

status_counts, reasons = Counter(), Counter()
accounts = unique_targets = 0
with (ROOT / clean['accounts_path']).open(encoding='utf-8') as stream:
    for line in stream:
        row = json.loads(line)
        accounts += 1
        unique_targets += row['target_parent_asin'] is not None
        status_counts[row['status']] += 1
        reasons.update(row['reasons'])
equal('stored_account_dispositions_cover_source_accounts', accounts, clean['counts']['raw_accounts'], 'clean/accounts_path')
equal('stored_exclusion_reasons_match_accepted', dict(reasons), clean['account_exclusions'], 'clean/accounts_path')
row_dispositions = Counter()
with (ROOT / clean['audit_path']).open(encoding='utf-8') as stream:
    for line in stream:
        row_dispositions[json.loads(line)['disposition']] += 1
equal('all_matched_source_rows_have_disposition', sum(row_dispositions.values()), selected['raw']['reviews'], 'clean/audit_path')
for group in ('dev', 'test'):
    for cohort in ('pool', 'UQ'):
        item = coverage[group][cohort]
        n = item['accounts']
        for name, values in (('history', item['history_depth_groups']), ('crop', item['target_crop']), ('year', item['target_UTC_year'])):
            equal(f'{group}_{cohort}_{name}_partition', sum(values.values()), n, '13_coverage')
    equal(f'{group}_Q_pool_matches_split', joint['Q_pool'][group], split['counts'][f'{group}_accounts'], 'split+13')
    equal(f'{group}_U8_partition', p0['groups'][group]['n_J_all_main_views'] + p0['groups'][group]['n_not_all_main_applicable'], joint['Q_pool'][group], 'P0+13')
    equal(f'{group}_Q_and_old_pool_coverage', coverage[group]['pool']['target_crop'], p0['groups'][group]['pool']['target_crop_counts'], 'P0+13_coverage')
save('conservation.json', {'equations': equations, 'all_passed': all(e['passed'] for e in equations),
 'stored_account_statuses': dict(status_counts), 'stored_exclusion_reasons': dict(reasons),
 'accounts_with_unique_target_field': unique_targets, 'stored_source_dispositions': dict(row_dispositions),
 'rules_recomputed': False, 'private_account_identifiers_exported': False})
save('coverage-reused.json', {'Q': coverage, 'U8': {g: p0['groups'][g]['U_J'] for g in ('dev', 'test')},
 'original8_per_view': {g: p0['groups'][g]['per_view'] for g in ('dev', 'test')},
 'outside_U8': p0['groups']['test']['outside_U_J'],
 'n8': joint['n8_from_P0'], 'nQ': joint['nQ'], 'planning_required': 975,
 'actual_effect_intervals': 'not_determined_not_run', 'sufficiency': 'not_determined'})
names = subprocess.check_output(['git', 'ls-tree', '-rz', '--name-only', BASE], cwd=ROOT).decode().split('\0')
allowed = {'.scratch/data-preparation/issues/14-full-data-acceptance.md', '.scratch/data-preparation/map.md'}
protected = [fingerprint(n) for n in names if n and n not in allowed]
save('protected-current-before.json', protected)
print(json.dumps({'binding_files': len(receipts), 'binding_bytes': sum(r['bytes'] for r in receipts),
 'conservation_checks': len(equations), 'failed_equations': [e['name'] for e in equations if not e['passed']],
 'account_statuses': dict(status_counts), 'unique_target_fields': unique_targets,
 'source_row_dispositions': dict(row_dispositions), 'n8': joint['n8_from_P0'], 'nQ': joint['nQ'],
 'protected_tracked_files': len(protected)}))
raise SystemExit(0 if all(e['passed'] for e in equations) else 2)
