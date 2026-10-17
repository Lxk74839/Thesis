"""Ten fixed-source probes, not T0, recommendation runs, or an effect evaluation."""
import hashlib
import hmac
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from evidence_access import EvidenceSession, LocalEvidenceSource
from evidence_verification import rank_acquired_quality
from joint_access import JointSession

OUT = ROOT / 'data/evidence-forensics-audit/20261016' / sys.argv[1]
OUT.mkdir(exist_ok=False)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked(ref):
    file = ROOT / ref['path']
    assert file.is_file() and digest(file) == ref['sha256']
    if 'bytes' in ref:
        assert file.stat().st_size == ref['bytes']
    return file


def load(path):
    return json.loads((ROOT / path).read_bytes())


def rows(path):
    with path.open('rb') as stream:
        for line in stream:
            yield json.loads(line)


def put(name, value):
    file = OUT / name
    with file.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True)
        stream.write('\n')
    return {'path': file.relative_to(ROOT).as_posix(), 'bytes': file.stat().st_size, 'sha256': digest(file)}


def audit_sources(audit):
    """Independent byte/offset and receipt conservation audit; no producer helpers."""
    acquired = audit['acquired']
    items = list(acquired['context'].values())
    for pack in acquired['candidates'].values():
        items += pack['registrations'] + list(pack['originals'].values())
    checked_files = {}
    for item in items:
        if item.get('raw_utf8') is None:
            continue
        origin = item['source']
        file = ROOT / origin['component_path']
        if file not in checked_files:
            assert digest(file) == origin['component_sha256']
            checked_files[file] = origin['component_sha256']
        raw = item['raw_utf8'].encode('utf-8')
        with file.open('rb') as stream:
            stream.seek(origin.get('offset', 0))
            assert stream.read(len(raw)) == raw
        assert item['receipt_id'] in {row['receipt_id'] for row in audit['receipts']}
    for dimension in ('logical_tools', 'physical_tools'):
        assert sum(row['usage_delta'][dimension] for row in audit['receipts']) == audit['usage'][dimension]
    requests = {item['adapter_request_id'] for receipt in audit['receipts'] for item in receipt['items']
                if item['adapter_request_id'] is not None}
    assert len(requests) == audit['usage']['physical_tools']
    assert not audit['unsettled_reservations']
    return {'byte_offsets_and_sha256': 'passed', 'receipt_conservation': 'passed',
            'actual_fact_objects_checked': len(items), 'distinct_source_files': len(checked_files)}


results = []
try:
    cfg = load('config/joint-task-package-0.1.0.json')
    record = load('records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0.json')
    preference = load('config/preference-task-1.0.1.json')
    split = load('records/splits/grain-A-1.1.15-user-split-1.0.0.json')
    # Selection uses assignment metadata only: no target, evaluation, masks or reference files.
    identity_key = checked(preference['identity_key']).read_bytes()
    assignment_file = checked({'path': split['accounts_path'], 'sha256': split['accounts_sha256']})
    dev_roots = [hmac.new(identity_key, preference['version'].encode() + b'\0' + row['user_id'].encode(),
                          hashlib.sha256).hexdigest() for row in rows(assignment_file) if row['split'] == 'dev']
    chosen = min(dev_roots, key=lambda value: value.encode())
    files = {name: checked(ref) for name, ref in record['components'].items()
             if name in ('model/roots.jsonl', 'model/candidates.jsonl', 'model/catalog.jsonl', 'view-bindings.jsonl')}
    root = next(row for row in rows(files['model/roots.jsonl']) if row['root_task_id'] == chosen)
    candidates = next(row for row in rows(files['model/candidates.jsonl']) if row['root_task_id'] == chosen)
    catalog = list(rows(files['model/catalog.jsonl']))
    view_bindings = {row['snapshot_id']: row for row in rows(files['view-bindings.jsonl']) if row['root_task_id'] == chosen}
    labels = ['V00', 'V01', 'V03', 'V05', 'V06', 'V07', 'V09', 'V12', 'Q1', 'Q2']
    assert [view['label'] for view in cfg['views']] == labels
    for number, view in enumerate(cfg['views']):
        start = time.perf_counter()
        linked = view_bindings[view['snapshot_id']]
        handle = hmac.new(identity_key, b'Thesis:joint-session-0.1.0\0' + json.dumps([
            chosen, view['material_version'], view['snapshot_id'], view['request_profile_id']],
            ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode(), hashlib.sha256).hexdigest()
        joint = JointSession(root, candidates, catalog, linked, handle)
        parent = joint.orders['base'][0]
        batch = candidates['batches'][candidates['C'].index(parent)]
        binding = {'run_id': 'forensic-contract-probe-' + str(number), 'root_task_id': chosen,
            'parent_asin': parent, 'sim_batch_id': batch, 'snapshot_id': view['snapshot_id'],
            'material_version': view['material_version'], 'principal_id': cfg['principal_id'],
            'verify_at_ms': cfg['verify_at_ms'], 'arm': view['arm'],
            'necessary_clauses': [c['clause_id'] for c in linked['request']['necessary_clauses']]}
        session = EvidenceSession(binding, LocalEvidenceSource(view['snapshot']), joint=joint,
            limits={'logical_tools': 4096, 'physical_tools': 512, 'candidates': 1, 'retries': 0, 'elapsed_ms': 60000},
            final_reserve={'logical_tools': 2, 'physical_tools': 1, 'elapsed_ms': 1000})
        page = session.dispatch('candidate_page', {'order': 'base', 'cursor': None})
        assert page['status'] == 'ok' and page['candidates'][0]['parent_asin'] == parent
        entries, cursor = [], None
        while True:
            page = session.dispatch('list_evidence', {'cursor': cursor})
            assert page['status'] == 'ok', page['status']
            entries.extend(page['entries'])
            cursor = page['next_cursor']
            if cursor is None:
                break
        for offset in range(0, len(entries), 32):
            response = session.dispatch('read_evidence', {'evidence_refs': [e['evidence_ref'] for e in entries[offset:offset + 32]]})
            assert response['status'] == 'ok', response['status']
        cached = session.dispatch('read_evidence', {'evidence_refs': [entries[0]['evidence_ref']]})
        assert cached['receipt']['usage_delta']['physical_tools'] == 0
        assessment_response = session.assess_current()
        assert assessment_response['status'] == 'ok', assessment_response['status']
        audit = session.audit_view()
        independent = audit_sources(audit)
        quality = []
        if view['arm'] == 'quality':
            snapshot = json.loads(audit['acquired']['context']['snapshot']['raw_utf8'])
            fusion = {'schema_version': 'fusion-binding-0.1.0', 'task_id': chosen, 'C': candidates['C'],
                'C_sha256': root['C_sha256'], 'H_sha256': root['H_sha256'], 'base_scores': candidates['b'],
                'base_score_version': root['score_version'], 'base_score_sha256': root['base_scores_sha256'],
                'snapshot_id': binding['snapshot_id'], 'verify_at_ms': binding['verify_at_ms'],
                'principal_id': binding['principal_id'], 'contract_sha256': snapshot['contract_sha256'],
                'K': 10, 'alpha': .5, 'beta': [.25, .5, .25],
                'preference': {'source': 'experiment_design', 'dimensions': ['retail_stock'], 'weights': {'retail_stock': 1}}}
            for mode in ('full', 'no_quality', 'mean_quality'):
                scored = rank_acquired_quality({**fusion, 'mode': mode}, audit['acquired'])
                current = next(row for row in scored['candidates'] if row['parent_asin'] == parent)
                quality.append({'mode': mode, 'current_fields': current,
                    'mean_quality': scored['mean_quality'], 'actual_G_count': len(scored['G'])})
        assert session.audit_view() == audit
        evidence = put(view['label'] + '-actual-a.json', audit)
        results.append({'label_admin_only': view['label'], 'status': 'passed', 'root': chosen, 'candidate': parent,
            'binding': binding, 'safe_input_fingerprint': json.loads(joint.request['messages'][0]['content'])['input_fingerprint'],
            'existing_tools_unchanged': joint.request['tools'] == [], 'actual_A': evidence,
            'assessment': assessment_response['assessment'], 'independent': independent,
            'usage': audit['usage'], 'setup': audit['setup'], 'quality_conversion': quality,
            'local_seconds': time.perf_counter() - start})
        put(view['label'] + '-summary.json', results[-1])
        print(json.dumps({'source': view['label'], 'status': 'passed', 'state': assessment_response['assessment']['evidence_state'],
                          'logical': audit['usage']['logical_tools'], 'physical': audit['usage']['physical_tools']}), flush=True)
    put('probe-summary.json', {'status': 'passed', 'selection': 'lexical_first_dev_root_and_fixed_b_queue_first_candidate',
        'sources': results, 'test_limits_only': True, 'T0_executed': False, 'recommendation_runs': 0,
        'private_gold_or_targets_read': False, 'source_regeneration': False,
        'coverage_limit': 'one predetermined candidate; no assumption it belongs to the anomaly set; H01-H14 cover semantics'})
except Exception as exc:
    if 'session' in globals():
        put('failed-source-actual-a.json', session.audit_view())
    put('probe-failure.json', {'status': 'failed', 'completed_sources': [row['label_admin_only'] for row in results],
        'error_type': type(exc).__name__, 'message': str(exc)})
    raise
