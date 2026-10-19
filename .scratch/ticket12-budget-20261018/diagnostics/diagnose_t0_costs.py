"""PUBLIC-only diagnostic through the existing t0_catalog prepare CLI; no production edits."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
WORK = ROOT / '.tmp/ticket12-t0/diagnosis-20261019'
LEDGER = ROOT / 'data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl'
BASE_SECONDS = 207.9693715001922
DATA_CAP = 250 * 1024**2  # Other diagnostic scripts/reports/logs have a separate 6MiB margin.


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sizes():
    return {p: p.stat().st_size for p in WORK.rglob('*') if p.is_file()}


def save(path, value):
    path.write_bytes(raw(value) + b'\n')


def write_gate():
    """Check bytes before writes, including JSONL streams. Never touch existing real artifacts."""
    known = sizes()
    original = io.open

    class File:
        def __init__(self, stream, path):
            self.stream, self.path = stream, path

        def __getattr__(self, name):
            return getattr(self.stream, name)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def write(self, value):
            length = len(value.encode(self.stream.encoding or 'utf-8')) if isinstance(value, str) else len(value)
            extent = max(known.get(self.path, 0), self.stream.tell() + length)
            if sum(known.values()) - known.get(self.path, 0) + extent > DATA_CAP:
                raise OSError('diagnostic_250MiB_data_gate')
            known[self.path] = extent
            return self.stream.write(value)

    def opened(file, mode='r', *args, **kwargs):
        if not isinstance(file, (str, bytes, os.PathLike)) or not any(c in mode for c in 'wax+'):
            return original(file, mode, *args, **kwargs)
        path = Path(file).absolute()
        if not path.is_relative_to(WORK):
            raise OSError('diagnostic_write_outside_PUBLIC_work')
        stream = original(file, mode, *args, **kwargs)
        if 'w' in mode or 'x' in mode:
            known[path] = 0
        return File(stream, path)

    io.open = opened


def fixture(case):
    from tests.test_t0_catalog import CatalogTests
    from tests.runtime_fixtures import RuntimeFixture
    work = WORK / ('public-' + case)
    work.mkdir()
    helper = CatalogTests()
    helper.work = work
    authorization, auth, ids = helper.public_authorization()
    facts = RuntimeFixture(work / 'sources/public-facts')
    helper.with_facts(auth, facts, ids)
    auth['sources']['accounts'] = helper.save('sources/accounts.jsonl',
        raw({'user_id': 'PUBLIC-DEV-A', 'split': 'dev'}) + b'\n', True)
    if case == 'longH':
        rows = [json.loads(row) for row in (work / 'sources/roots.jsonl').read_bytes().splitlines()]
        for row in rows:
            row['history'][0]['text'] += ' PUBLIC history' * 512
            row['H_sha256'] = hashlib.sha256(raw(row['history'])).hexdigest()
        auth['sources']['model_roots'] = helper.save('sources/roots.jsonl',
            b''.join(raw(row) + b'\n' for row in rows), True)
    helper.save('authorization.json', auth)
    return authorization


class Stages:
    """Exclusive wall attribution; nested serialization/hash/I/O leave their caller's bucket."""
    def __init__(self):
        self.stack = ['other']
        self.seconds, self.calls = {}, {}
        self.overhead = 0
        self.last = time.perf_counter()

    def __call__(self, frame, event, arg):
        entered = time.perf_counter()
        current = self.stack[-1]
        self.seconds[current] = self.seconds.get(current, 0) + entered - self.last
        if event in ('call', 'c_call'):
            name = frame.f_code.co_name if event == 'call' else getattr(arg, '__name__', '')
            filename = Path(frame.f_code.co_filename).name
            phase = None
            if event == 'call':
                if filename == 't0_catalog.py' and name == '_dependency':
                    phase = 'dependency_probe'
                elif filename == 'recommendation_runner.py' and name == 'compose_role_request':
                    phase = 'message_compose'
                elif name in ('canonical', 'encoded') and filename in ('provider_openai.py', 'evidence_access.py'):
                    phase = 'serialization'
                elif filename == 'encoder.py' or name == 'dumps' and filename == '__init__.py':
                    phase = 'serialization'
                elif name in ('sha', 'digest') and filename in ('provider_openai.py', 'evidence_access.py'):
                    phase = 'digest'
                elif filename in ('model_adapter.py', 'provider_openai.py') and name == 'prepare':
                    phase = 'adapter_mapping_copy'
                elif filename == 't0_catalog.py' and name in ('_trace', '_prefix', '_replace', '_visible', '_template_ids', '_planned_template'):
                    phase = 'trace_rebind_plan'
            else:
                owner = getattr(arg, '__self__', None)
                if name in ('openssl_sha256', 'update', 'hexdigest', 'digest') and ('hash' in type(owner).__module__ or name == 'openssl_sha256'):
                    phase = 'digest'
                elif name in ('write', 'flush', 'close', '__exit__') and type(owner).__module__ == '_io':
                    if any(c in getattr(owner, 'mode', '') for c in 'wax+'):
                        phase = 'file_write'
                elif name == 'open' and any(c in str(frame.f_locals.get('mode', 'r')) for c in 'wax+'):
                    phase = 'file_write'
            self.stack.append(phase or current)
            if phase:
                self.calls[phase] = self.calls.get(phase, 0) + 1
        elif event in ('return', 'c_return', 'c_exception') and len(self.stack) > 1:
            self.stack.pop()
        finished = time.perf_counter()
        self.overhead += finished - entered
        self.last = finished


def observe(directory):
    coverage = json.loads((directory / 'coverage.json').read_bytes())
    total = duplicate = 0
    representations = []
    for path in (directory / 'objects').glob('*.json'):
        value = json.loads(path.read_bytes())
        w, p = raw(value['wire_body']), raw(value['count_body'])
        assert w == value['wire_utf8'].encode() and p == value['count_utf8'].encode()
        duplicate += len(w) + len(p)
        total += path.stat().st_size
        representations.append(4)
    return {'plans': coverage['plans'], 'N': coverage['N'], 'U': coverage['U'],
        'wire_bytes': coverage['original_wire_bytes'], 'payload_bytes': coverage['original_count_payload_bytes'],
        'object_file_bytes': total, 'redundant_full_representation_bytes': duplicate,
        'full_W_P_representations_per_object': sorted(set(representations)),
        'storage_over_W_plus_P': total / (coverage['original_wire_bytes'] + coverage['original_count_payload_bytes']),
        'feedback': 'RED_repeated_complete_payloads' if duplicate else 'GREEN_no_redundant_complete_payloads'}


def parent(case):
    started = time.perf_counter()
    assert os.environ['THESIS_RESOURCE_DOMAIN'] == 'offline'
    used = sum(json.loads(row)['seconds'] for row in LEDGER.read_text().splitlines()) - BASE_SECONDS
    assert used < 116, 'diagnostic_120_second_gate'
    WORK.mkdir(parents=True, exist_ok=True)
    state_path = WORK / 'state.json'
    state = json.loads(state_path.read_bytes()) if state_path.exists() else {'reserved_plans': 0, 'cases': []}
    assert case not in state['cases'] and state['reserved_plans'] + 3 <= 12, 'PUBLIC_12_plan_gate'
    authorization = WORK / 'public-baseline/authorization.json' if case in ('repeat', 'profile') else fixture(case)
    state['reserved_plans'] += 3
    state['cases'].append(case)
    save(state_path, state)
    target = WORK / ('catalog-' + case)
    env = dict(os.environ, THESIS_RESOURCE_DEADLINE_UNIX=str(min(
        float(os.environ['THESIS_RESOURCE_DEADLINE_UNIX']), time.time() + 116 - used - (time.perf_counter() - started))))
    log = WORK / (case + '-cli.txt')
    with log.open('xb') as stream:
        child = subprocess.Popen([sys.executable, '-B', str(Path(__file__)), '--child',
            '--case', case, '--authorization', str(authorization), '--output', str(target)],
            cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, env=env)
        try:
            code = child.wait(timeout=max(.1, 116 - used - (time.perf_counter() - started)))
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            save(WORK / (case + '-result.json'), {'status': 'diagnostic_time_gate', 'case': case})
            return 2
    assert code == 0, log.read_text(encoding='utf-8')[-2000:]
    result = {'case': case, 'cli_seconds': time.perf_counter() - started, **observe(target)}
    stage_file = WORK / (case + '-stages.json')
    if stage_file.exists():
        result['stages'] = json.loads(stage_file.read_bytes())
    result['diagnostic_work_bytes'] = sum(sizes().values())
    save(WORK / (case + '-result.json'), result)
    print(json.dumps(result, sort_keys=True))
    return 1 if result['feedback'].startswith('RED') else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True, choices=('baseline', 'repeat', 'profile', 'longH'))
    parser.add_argument('--child', action='store_true')
    parser.add_argument('--authorization')
    parser.add_argument('--output')
    args = parser.parse_args()
    if args.child:
        write_gate()
        sys.argv = ['t0_catalog', 'prepare', '--authorization', args.authorization, '--output', args.output]
        stages = Stages() if args.case in ('profile', 'longH') else None
        started = time.perf_counter()
        if stages:
            sys.setprofile(stages)
        try:
            runpy.run_module('t0_catalog', run_name='__main__')
        finally:
            if stages:
                sys.setprofile(None)
                save(WORK / (args.case + '-stages.json'), {'exclusive_seconds': stages.seconds,
                    'entry_calls': stages.calls, 'callback_overhead_seconds': stages.overhead,
                    'instrumented_cli_seconds': time.perf_counter() - started,
                    'accounting': 'exclusive wall; nested recognized phases override their caller; callback overhead excluded'})
        return 0
    return parent(args.case)


if __name__ == '__main__':
    raise SystemExit(main())
