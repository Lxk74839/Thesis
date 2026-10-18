"""Independently inspect persisted public batch artifacts, without importing production."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'data/recommendation-runtime-audit/20261018-batch'
cases = (AUDIT / 'cases' / sys.argv[1]).resolve()
assert cases.is_relative_to(AUDIT / 'cases')
candidate = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '--',
    'recommendation_runner.py', 'model_adapter.py', 'evidence_access.py',
    'tests/test_batched_recommendation.py'], cwd=ROOT)
audits = []
literal_checks = set()
for path in sorted(cases.rglob('audit.json')):
    audit = json.loads(path.read_bytes())
    assert audit['binding']['fixture'] == 'public_runtime_adapter' and audit['binding']['execution_kind'] == 'scripted_public'
    messages = audit['messages']
    assert all(m['response']['provider_requests_sent'] == 0 and m['usage_basis'] == 'synthetic' for m in messages)
    known_calls = sum(int(m['response']['attempted']) for m in messages)
    assert audit['budget']['usage']['model_calls'] == known_calls
    for batch in audit['batches']:
        assert len(batch['processed']) <= 32
        assert batch['role_message_id'] in {m['role_message_id'] for m in messages}
        assert all(s['root_reservation_id'] is not None for s in batch['steps'])
    used = audit['evidence']['acquired']['candidates']
    for pack in used.values():
        for original in pack['originals'].values():
            raw = original['raw_utf8'].encode('utf-8')
            assert hashlib.sha256(raw).hexdigest() == original['sha256'] == original['registration']['content_sha256']
            source = Path(original['source']['component_path']).resolve()
            assert source.is_relative_to(cases)
            assert source.read_bytes().splitlines()[original['source']['line'] - 1] == raw
    publication = path.parent / 'publication.json'
    if audit['terminal'] in ('released', 'valid_empty'):
        delivered = json.loads(publication.read_bytes())
        assert delivered['G'] == audit['G'] and delivered['cursor'] == audit['cursor']
        assert [i['parent_asin'] for i in delivered['draft']['items']] == audit['delivered']
        assert delivered['draft_sha256'] == hashlib.sha256(json.dumps(delivered['draft'],
            sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        assert len(audit['profiled_candidates']) == len(set(audit['profiled_candidates']))
        assert set(audit['profiled_candidates']) == set(audit['assessments'])
        assert not audit['budget']['held']['output_tokens']
        if audit['components']:
            assert audit['components']['full']['topK'] == audit['delivered']
    else:
        assert not publication.exists()
        if audit['components']:
            assert all(c['status'] == 'anchor_failed' for c in audit['components'].values())
    parent = path.parents[2].name
    if parent.startswith('four_quality_candidates_'):
        assert (known_calls, audit['cursor']) == (9, 4)
        literal_checks.add('four')
    if parent.startswith('batch_messages_preserve_'):
        assert (known_calls, audit['cursor']) == (9, 12)
        literal_checks.add('twelve')
    if parent.startswith('sixty_four_prefix_uses_t'):
        assert (known_calls, audit['cursor'], len(audit['binding']['C'])) == (13, 64, 66)
        literal_checks.add('sixty_four')
    audits.append({'path': path.relative_to(ROOT).as_posix(), 'terminal': audit['terminal'],
        'calls': known_calls, 'cursor': audit['cursor'], 'candidate_count': len(audit['binding']['C'])})
assert audits and literal_checks == {'four', 'twelve', 'sixty_four'}
files = {p.relative_to(ROOT).as_posix(): {'bytes': p.stat().st_size,
    'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(cases.rglob('*')) if p.is_file()}
report = {'status': 'passed', 'candidate': candidate, 'public_audits': audits, 'files': files,
    'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
        ('recommendation_runner.py', 'model_adapter.py', 'evidence_access.py', 'tests/test_batched_recommendation.py')},
    'limits': 'offline_scripted_only_not_T0_or_token_capacity', 'oracle': 'stdlib_public_original_bytes_and_literal_counts'}
with (AUDIT / (sys.argv[2] + '.json')).open('x', encoding='utf-8') as stream:
    json.dump(report, stream, ensure_ascii=False, sort_keys=True)
print(json.dumps({'status': 'passed', 'candidate': candidate, 'audits': len(audits), 'files': len(files)}))
