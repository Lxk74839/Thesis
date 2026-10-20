"""Freeze the approved dev-only reference list; never execute or evaluate accounts."""
import hashlib
import json
import re

from evidence_access import PROJECT, digest, encoded
from experiment_runner import AUDIT, accepted_sources, _scan, _write

SCOPE = 'ticket14-dev-pilot-0.1.0'
D1 = '015b0ca5bdc7b75fd7714222a065ff02e02b6eda723c60b7396ab7a2e8b0b88e'
DESTINATION = PROJECT / 'data/recommendation-runtime-audit/ticket14-development/pilot'


def main():
    sources = accepted_sources()
    dev, membership, cohort_sha, offset = [], None, hashlib.sha256(), 0
    with (PROJECT / sources['cohort']['path']).open('rb') as stream:
        for line, raw in enumerate(stream, 1):
            cohort_sha.update(raw)
            root = re.search(rb'"task_id":"([0-9a-f]{64})"', raw).group(1).decode()
            split = re.search(rb'"split":"(dev|test)"', raw).group(1).decode()
            if split == 'dev':
                dev.append(root)
            if root == D1:
                if split != 'dev':
                    raise ValueError('pilot_not_development')
                membership = {'path': sources['cohort']['path'], 'offset': offset, 'bytes': len(raw),
                              'line': line, 'sha256': digest(raw)}
            offset += len(raw)
    if len(dev) != 320 or min(dev) != D1 or cohort_sha.hexdigest() != sources['cohort']['sha256']:
        raise ValueError('development_projection_mismatch')
    frozen_raw = (AUDIT / 'plan/plan.json').read_bytes()
    frozen = json.loads(frozen_raw)
    users = [json.loads(raw)['root_task_id'] for raw in (AUDIT / 'plan/sample-users.jsonl').read_bytes().splitlines()]
    if D1 in users or len(users) != 100:
        raise ValueError('pilot_test_overlap')
    scenes = [json.loads(raw) for raw in (AUDIT / 'plan/scenes.jsonl').read_bytes().splitlines()]
    root_ref, candidate_ref, root, views = None, None, None, {}
    for role in ('roots', 'candidates', 'view_bindings'):
        for row, ref in _scan(sources[role]):
            if row['root_task_id'] != D1:
                continue
            if role == 'roots':
                root, root_ref = row, ref
            elif role == 'candidates':
                candidate_ref = ref
            else:
                views[row['label']] = ref
    if root is None or candidate_ref is None or len(views) != 10:
        raise ValueError('missing_development_source')
    relations, tasks = [], []
    selected = {'V00': ('R', 'S', 'M'), 'V01': ('M',), 'V05': ('M',), 'V06': ('M',), 'Q1': ('M',), 'Q2': ('M',)}
    for scene in scenes:
        # Only the accepted original ten views have joint per-root rows. Added views
        # inherit the accepted request identity, with their exact frozen snapshot.
        relation = {'binding_id': digest(encoded([SCOPE, D1, scene['view_id']])),
                    'root_task_id': D1, 'view_id': scene['view_id']}
        if scene['label'] in views:
            relation['existing_binding_ref'] = views[scene['label']]
        else:
            relation['request_template_ref'] = views['V00']
        relations.append(relation)
        for method in selected.get(scene['label'], ()):
            tasks.append({'task_key': digest(encoded([SCOPE, D1, scene['view_id'], method, 1])),
                'binding_id': relation['binding_id'], 'method': method, 'repeat': 1, 'uses_model': method != 'R'})
    if DESTINATION.exists():
        raise ValueError('pilot_output_exists')
    DESTINATION.mkdir(parents=True)
    proof = {'root_task_id': D1, 'split': 'dev', 'membership_source_ref': membership,
        'cohort_sha256': sources['cohort']['sha256'], 'selection_rule': 'dev_task_id_ASCII_first',
        'development_count': 320, 'formal_users': 100, 'formal_overlap': 0, 'target_or_states_projected': False}
    proof_ref = _write(DESTINATION / 'membership.json', [proof]) | {
        'path': (DESTINATION / 'membership.json').relative_to(PROJECT).as_posix()}
    components = {name: _write(DESTINATION / name, rows) for name, rows in {
        'tasks.jsonl': tasks, 'user-scenarios.jsonl': relations, 'scenes.jsonl': scenes,
        'root-references.jsonl': [{'root_task_id': D1, 'root_ref': root_ref, 'candidate_ref': candidate_ref,
            **{k: root[k] for k in ('C_sha256', 'H_sha256', 'base_scores_sha256')}}],
        'sample-users.jsonl': [{'root_task_id': D1, 'split': 'dev'}]}.items()}
    manifest = {'schema_version': SCOPE, 'source_scope': 'development_pilot', 'parent_plan_id': frozen['plan_id'],
        'parent_plan_ref': {'path': (AUDIT / 'plan/plan.json').relative_to(PROJECT).as_posix(),
                            'bytes': len(frozen_raw), 'sha256': digest(frozen_raw)},
        'sources': sources, 'membership_ref': proof_ref, 'components': components,
        'counts': {'users': 1, 'tasks': 8, 'model_tasks': 7, 'formal_overlap': 0},
        'model_binding': dict.fromkeys(('model_id', 'channel', 'base_url', 'pricing', 'api_budget')),
        'execution_authorized': False, 'provider_requests_sent': 0, 'recommendation_runs': 0}
    manifest['pilot_id'] = digest(encoded(manifest))
    _write(DESTINATION / 'manifest.json', [manifest])
    print(json.dumps({'status': 'frozen_development_only', 'pilot_id': manifest['pilot_id'],
                      'counts': manifest['counts'], 'provider_requests_sent': 0}))


if __name__ == '__main__':
    main()
