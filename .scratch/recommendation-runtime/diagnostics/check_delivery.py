"""Independent public artifact oracle. No runtime/ledger/verifier imports or execution."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'data/recommendation-runtime-audit/20261017'
CASES = {
    'normal-R': ('released', ['PUBLIC-A'], 1),
    'normal-S': ('released', ['PUBLIC-A'], 1),
    'normal-M': ('released', ['PUBLIC-A'], 1),
    'quality-four': ('released', ['PUBLIC-B', 'PUBLIC-A', 'PUBLIC-HI', 'PUBLIC-LO'], 4),
    'stock-feedback': ('released', ['PUBLIC-A'], 1),
    'necessary-twelve': ('released', ['PUBLIC-A%02d' % i for i in range(1, 11)], 10),
    'quality-twelve': ('released', ['PUBLIC-A%02d' % i for i in range(1, 11)], 12),
    'unassessed-quality': ('failed_protocol', [], 0),
    'unknown-usage': ('failed_model', [], 0),
    'full-empty': ('valid_empty', [], 2),
    'prefix-empty': ('blocked_evidence', [], 1),
    'bad-order': ('blocked_evidence', [], 2),
    'bad-source': ('failed_source', [], 0),
}


def wire(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def check(name, directory):
    result = json.loads((directory / 'result.json').read_bytes())
    state = json.loads((directory / 'audit.json').read_bytes())
    journal = [json.loads(line) for line in (directory / 'budget.jsonl').read_bytes().splitlines()]
    terminal, delivered, cursor = CASES[name]
    require((result['terminal'], result['delivered'], result['cursor']) == (terminal, delivered, cursor), name + ': terminal/list/cursor')
    require(state['terminal'] == terminal and state['G'] == result['G'], name + ': audit state')
    require(result['release_scope'] == 'public_fixture_only' and result['provider_requests_sent'] == 0, name + ': scope')
    binding = result['binding']
    require(binding == journal[0]['binding'] and binding['execution_budget'] is None and binding['execution_authorized'] is False, name + ': binding')
    require(result['queue'] == sorted(binding['C'], key=lambda p: (-binding['base_scores'][binding['C'].index(p)], p.encode())), name + ': queue')
    require(binding['C_sha256'] == sha(wire(binding['C'])) and binding['base_score_sha256'] == sha(wire(list(zip(binding['C'], binding['base_scores'])))), name + ': fixed C/b')
    expected_g = [p for p in result['queue'][:cursor] if result['assessments'][p]['eligible']]
    require(result['G'] == expected_g, name + ': explicit actual G')
    for parent in result['G']:
        assessment = result['assessments'][parent]
        require(assessment['evidence_state'] == 'Supported' and assessment['advance_allowed'], name + ': incomplete G')
    totals = dict.fromkeys(result['budget']['usage'], 0)
    pending = {}
    for record in journal[1:]:
        status = record['status']
        if status == 'reserved':
            identity = record['reservation_id']
            require(identity not in pending, name + ': duplicate reservation')
            pending[identity] = record['held']
            for dimension in totals:
                require(record['usage_before'][dimension] + record['held_before'][dimension] + record['held'][dimension]
                    + record['final_reserve_applied'][dimension] <= journal[0]['limits'][dimension], name + ': admission conservation')
        elif status in ('settled', 'unresolved'):
            held = pending.pop(record['reservation_id'])
            for key, value in record['usage'].items():
                if value is None:
                    require(record['unresolved'].get(key) == held[key], name + ': unknown released')
                else:
                    totals[key] += value
    require(not pending, name + ': unobserved side effect')
    for key, total in totals.items():
        if key != 'elapsed_ms':
            require(total == result['budget']['usage'][key], name + ': ledger ' + key)
    messages = result['messages']
    require(totals['model_calls'] == sum(int(m['response']['attempted']) for m in messages), name + ': attempts')
    if binding['method'] == 'R':
        require(not messages and all(totals[k] == 0 for k in ('model_calls', 'input_tokens', 'output_tokens', 'cost_microusd')), name + ': R model zero')
    elif terminal in ('released', 'valid_empty'):
        roles = {'单智能体'} if binding['method'] == 'S' else {'需求解析', '推荐管理', '用户画像', '农产品画像', '生命周期追溯', '推荐依据核验'}
        require(set(result['roles_completed']) == roles and bool(result['dispatches']), name + ': roles/dispatch')
    for message in messages:
        request, response = message['request'], message['response']
        require(message['provenance'] == response['provenance'] == 'scripted' and response['provider_requests_sent'] == 0, name + ': provenance')
        require(request['input_token_upper_bound'] == len(wire({'messages': request['messages'], 'tools': request['tools']})), name + ': full serialized input')
        require(request['run_id'] == binding['run_id'] and request['model_id'] is None, name + ': model identity')
        for visible in request['messages']:
            text = json.dumps(visible, ensure_ascii=False)
            require(not any(token in text for token in ('PRIVATE_TARGET_CANARY', 'component_path', 'raw_path')), name + ': private content')
    evidence = state['evidence']
    require(totals['physical_tools'] == sum(r['usage_delta']['physical_tools'] for r in evidence['receipts']), name + ': physical requests')
    for parent, pack in evidence['acquired']['candidates'].items():
        require(parent in result['queue'], name + ': evidence outside C')
        for original in pack['originals'].values():
            raw = original['raw_utf8'].encode()
            require(sha(raw) == original['sha256'] == original['registration']['content_sha256'], name + ': original digest')
            source = ROOT / original['source']['component_path']
            require(source.resolve().is_relative_to(AUDIT / 'micro'), name + ': fixture boundary')
            require(raw == source.read_bytes().splitlines()[original['source']['line'] - 1], name + ': exact original bytes')
    published = directory / 'publication.json'
    if terminal in ('released', 'valid_empty'):
        require(result['budget']['usage_exact'] and not result['budget']['halted'], name + ': unclosed budget')
        publication = json.loads(published.read_bytes())
        require([i['parent_asin'] for i in publication['draft']['items']] == delivered, name + ': published whole table')
        require(publication['draft_sha256'] == sha(wire(result['drafts'][-1])) and publication['draft'] == result['drafts'][-1], name + ': changed draft')
        require(publication['A_sha256'] == sha(wire(evidence['acquired'])), name + ': acquired anchor')
        require(publication['G'] == result['G'] and publication['cursor'] == cursor, name + ': published G/cursor')
        for item in publication['draft']['items']:
            require(item['sim_batch_id'] == binding['batches'][binding['C'].index(item['parent_asin'])], name + ': batch')
            for reason in item['reasons']:
                for citation in reason['citations']:
                    original = evidence['acquired']['candidates'][item['parent_asin']]['originals'][citation['evidence_ref']]
                    require(citation['receipt_id'] == original['receipt_id'] and citation['version'] == original['registration']['version'], name + ': citation receipt')
                    if reason['kind'] == 'retail_stock':
                        require(citation['pointer'] == '/facts/stock_units' and json.loads(original['raw_utf8'])['facts']['stock_units'] == reason['value'] == 75, name + ': stock repair')
    else:
        require(not published.exists() and result['publication_path'] is None, name + ': failure published')
    if result['components']:
        components = result['components']
        require(len({c['anchor_sha256'] for c in components.values()}) == 1, name + ': split anchors')
        for component in components.values():
            anchor = component['anchor']
            require(component['anchor_sha256'] == sha(wire(anchor)) and anchor['A_sha256'] == sha(wire(evidence['acquired'])), name + ': component digest')
            require(anchor['G'] == result['G'] and anchor['terminal'] == terminal, name + ': component G/terminal')
            if terminal == 'released':
                require(anchor['publication_record_sha256'] == sha(published.read_bytes()), name + ': publication fingerprint')
            else:
                require(component['status'] == 'anchor_failed', name + ': component salvaged')
        if terminal == 'released':
            require(components['full']['topK'] == delivered, name + ': full differs')
    if name == 'quality-four':
        expected = {'full': [.675, .75, .5, 0], 'no_quality': [.825, .8, .5, 0], 'mean_quality': [.703125, .6375, .5, 0]}
        for mode, scores in expected.items():
            require([r['score'] for r in result['components'][mode]['candidates']] == scores, 'H09 hand scores')
        require(result['components']['mean_quality']['mean_quality'] == {'value': .675, 'denominator': 4}, 'H09 hand mean')
    if name.endswith('twelve'):
        require(len(binding['C']) == 12 and len(evidence['acquired']['candidates']) == cursor, 'H02 complete C/actual prefix')
    if name == 'stock-feedback':
        require(result['feedback_round'] == 1 and len(result['drafts']) == 2 and bool(result['revisions']), 'H07 actual revision')
    if name == 'unknown-usage':
        require(totals['model_calls'] == 1 and not result['budget']['usage_exact'] and result['budget']['held']['output_tokens'] > 0, 'H12 unknown hold')
    return {'terminal': terminal, 'cursor': cursor, 'delivered': delivered, 'provider_requests_sent': 0}


folder = (AUDIT / sys.argv[1]).resolve()
require(folder.is_relative_to(AUDIT / 'micro'), 'only public micro artifacts')
summaries = {name: check(name, folder / name / 'runs/1') for name in CASES}
files = {p.relative_to(folder).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
         for p in sorted(folder.rglob('*')) if p.is_file()}
report = {'status': 'passed', 'oracle': 'stdlib_only_literal_public_artifact_check', 'cases': summaries, 'files': files}
sources = ['evidence_access.py', 'model_adapter.py', 'recommendation_runner.py', 'tests/runtime_fixtures.py',
    'tests/test_root_budget.py', 'tests/test_model_adapter.py', 'tests/test_recommendation_runner.py',
    '.scratch/recommendation-runtime/spec.md', '.scratch/recommendation-runtime/confirmation.md',
    '.scratch/recommendation-runtime/diagnostics/run_check.py', '.scratch/recommendation-runtime/diagnostics/protect_scope.py',
    '.scratch/recommendation-runtime/diagnostics/check_delivery.py']
report['source_sha256'] = {p: sha((ROOT / p).read_bytes()) for p in sources}
with (AUDIT / (sys.argv[2] + '.json')).open('x', encoding='utf-8') as stream:
    json.dump(report, stream, ensure_ascii=False, sort_keys=True)
print(json.dumps({'status': 'passed', 'cases': len(summaries), 'manifest_files': len(files)}))
