"""Independent byte checks for the offline native adapter, without production imports."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'data/recommendation-runtime-audit/20261018-batch'
BEFORE = AUDIT / 'model-protected-before.json'
EDITABLE = {'model_adapter.py', 'recommendation_runner.py',
            '.scratch/ticket12-budget-20261018/diagnostics/run_check.py'}


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


mode = sys.argv[1]
if mode == 'delivery':
    cases = (AUDIT / 'cases' / sys.argv[2]).resolve()
    assert cases.is_relative_to(AUDIT / 'cases')
    def canonical(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    def digest(value):
        return hashlib.sha256(canonical(value).encode()).hexdigest()
    audits, intents, injected_http = [], 0, 0
    prepared_files = list(cases.rglob('prepared.json'))
    assert prepared_files
    for path in prepared_files:
        prepared = json.loads(path.read_bytes())
        assert digest(prepared['wire_body']) == prepared['wire_sha256']
        assert digest(prepared['count_body']) == prepared['count_payload_sha256']
        assert prepared['wire_utf8'] == canonical(prepared['wire_body'])
    for path in sorted(cases.rglob('audit.json')):
        audit = json.loads(path.read_bytes())
        assert audit['binding']['execution_kind'] == 'openai_native_fixture'
        assert all(m['response']['provider_requests_sent'] == 0 and m['usage_basis'] == 'fixture' for m in audit['messages'])
        prepared = {p['prepared']['source']['request_id']: p for p in audit['preparations']}
        for message in audit['messages']:
            request, response = message['request'], message['response']
            p, count = prepared[request['request_id']]['prepared'], prepared[request['request_id']]['count']
            assert p['wire_sha256'] == digest(p['wire_body']) and p['count_payload_sha256'] == digest(p['count_body'])
            assert p['wire_body']['model'] == 'gpt-5.4-mini-2026-03-17' and p['wire_body']['reasoning'] == {'effort': 'none'}
            assert request['prepared_id'] == p['prepared_id'] and request['count_receipt_id'] == count['receipt_id']
            assert count['basis'] == 'fixture' and count['input_tokens'] == request['input_token_upper_bound'] == 100
            assert response['usage']['input_tokens'] == response['raw_response']['body']['usage']['input_tokens'] == 100
            assert message['root_reservation_id'] in audit['budget']['reservations']
        usage = audit['budget']['usage']
        assert usage['model_calls'] == sum(int(m['response']['attempted']) for m in audit['messages'])
        assert usage['input_tokens'] == sum(m['response']['usage']['input_tokens'] for m in audit['messages'])
        publication = path.parent / 'publication.json'
        if audit['terminal'] == 'released':
            assert (usage['model_calls'], usage['input_tokens'], usage['output_tokens']) == (9, 900, 270)
            delivered = json.loads(publication.read_bytes())
            assert delivered['G'] == audit['G'] and delivered['cursor'] == audit['cursor']
            assert [i['parent_asin'] for i in delivered['draft']['items']] == audit['delivered']
        else:
            assert audit['terminal'] == 'incomplete_count' and not publication.exists() and not usage['model_calls']
        audits.append({'path': path.relative_to(ROOT).as_posix(), 'terminal': audit['terminal'], 'calls': usage['model_calls']})
    for path in cases.rglob('count-journal.jsonl'):
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        for row in rows:
            if row['kind'] == 'intent':
                intents += 1
                assert row['transport_origin'] in ('injected_sender', 'injected_https')
                injected_http += row['transport_origin'] == 'injected_https'
            elif row.get('receipt'):
                assert row['receipt']['provider_requests_sent'] == 0
    assert len(audits) == 4 and injected_http and intents
    files = {p.relative_to(ROOT).as_posix(): {'bytes': p.stat().st_size, 'sha256': fingerprint(p)}
             for p in sorted(cases.rglob('*')) if p.is_file()}
    report = {'status': 'passed', 'candidate': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'public_audits': audits, 'fixture_intent_records': intents, 'injected_https_records': injected_http,
        'provider_requests_sent': 0, 'files': files,
        'scope': 'offline_public_fixture_only_no_T0_no_capacity_no_supplier_availability'}
    with (AUDIT / ('model-delivery-' + sys.argv[2] + '.json')).open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, sort_keys=True)
    print(json.dumps({'status': 'passed', 'public_audits': len(audits), 'files': len(files), 'provider_requests_sent': 0}))
elif mode == 'before':
    paths = {ROOT / p for p in subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
             if p not in EDITABLE}
    paths.update(p for folder in ('reports', 'manuscript', 'research')
                 for p in (ROOT / folder).rglob('*') if p.is_file())
    values = {p.relative_to(ROOT).as_posix(): fingerprint(p) for p in sorted(paths)}
    with BEFORE.open('x', encoding='utf-8') as stream:
        json.dump(values, stream, sort_keys=True)
    print(json.dumps({'protected_files': len(values)}))
else:
    values = json.loads(BEFORE.read_bytes())
    changed = [p for p, sha in values.items() if not (ROOT / p).is_file() or fingerprint(ROOT / p) != sha]
    result = {'status': 'failed' if changed else 'passed', 'files': len(values), 'changed': changed}
    with (AUDIT / ('model-protected-' + mode + '.json')).open('x', encoding='utf-8') as stream:
        json.dump(result, stream, sort_keys=True)
    print(json.dumps(result))
    if changed:
        raise SystemExit(2)
