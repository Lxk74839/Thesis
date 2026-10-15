"""One-time, project-local initialization of the explicitly approved ticket08 inputs."""

import hashlib
import hmac
import json
from pathlib import Path
import secrets


ROOT = Path(__file__).resolve().parents[3]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8'))


def main():
    version = 'preference-task-1.0.0'
    private = ROOT / 'data/task-inputs' / version
    private.mkdir(parents=True, exist_ok=True)
    key_path = private / 'id-key.bin'
    if not key_path.exists():
        with key_path.open('xb') as stream:
            stream.write(secrets.token_bytes(32))
    key = key_path.read_bytes()
    assert len(key) == 32
    split = json.loads((ROOT / 'records/splits/grain-A-1.1.15-user-split-1.0.0.json').read_text('utf-8'))
    assignments = [json.loads(line) for line in (ROOT / split['accounts_path']).read_text('utf-8').splitlines()]
    dev = sorted(r['user_id'] for r in assignments if r['split'] == 'dev')[:2]
    ids = [hmac.new(key, version.encode() + b'\0' + u.encode(), hashlib.sha256).hexdigest() for u in dev]
    for name in ('private-canary.txt', 'old-index/canary.txt', 'old-cache/canary.txt'):
        path = private / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open('xb') as stream:
                stream.write(('PRIVATE_TICKET08_' + name.replace('/', '_') + '_NEVER_EXPORT\n').encode())
    probes = [{'session_task_id': ids[0], 'operation': 'model_request', 'arguments': {}}]
    paths = ['data/raw', 'data/cleaning/grain-A-1.1.15/review-cleaning-1.0.0/reviews.jsonl',
             split['accounts_path'], split['exposure_path'], str(key_path),
             'data/preference-tasks/grain-A-1.1.15/preference-task-1.0.0/private/evaluation.jsonl',
             '../private/evaluation.jsonl', 'C:/unknown/no-file', 'https://example.invalid',
             *[str(private / p) for p in ('private-canary.txt', 'old-index/canary.txt', 'old-cache/canary.txt')]]
    probes += [{'session_task_id': ids[0], 'operation': 'read_resource', 'arguments': {'path': p}} for p in paths]
    probes += [{'session_task_id': ids[0], 'operation': 'invoke_tool', 'arguments': {'name': name,
                'arguments': {'command': 'SYNTHETIC_DO_NOT_EXECUTE'}}} for name in (
                'read_file', 'file_search', 'exec_command', 'python', 'sql', 'http', 'web', 'mcp', 'connector', 'evaluator')]
    probes += [{'session_task_id': ids[0], 'operation': 'model_request', 'arguments': {'task_id': ids[1]}},
               {'session_task_id': ids[0], 'operation': 'model_request', 'arguments': {'role': 'evaluator'}},
               {'session_task_id': '0' * 64, 'operation': 'model_request', 'arguments': {}}]
    probe_path = private / 'access-probe-1.0.0.jsonl'
    encoded = b''.join((json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode() for r in probes)
    if probe_path.exists():
        assert probe_path.read_bytes() == encoded
    else:
        with probe_path.open('xb') as stream:
            stream.write(encoded)

    def binding(relative):
        return {'path': relative, 'sha256': digest(ROOT / relative)}

    config = {'version': version, 'approval': 'approved', 'input_profile': 'text_portrait_trial_v1',
              'text_policy_version': 'finite-text-1.0.0', 'access_profile': 'api_only_no_host_io_v1',
              'upstream_acceptances': {k: binding(v) for k, v in {
                  'cleaning': 'records/cleaning/grain-A-1.1.15-review-cleaning-1.0.0-acceptance.json',
                  'cleaning_erratum': 'records/cleaning/grain-A-1.1.15-review-cleaning-1.0.0-format-erratum.json',
                  'split': 'records/splits/grain-A-1.1.15-user-split-1.0.0-acceptance.json'}.items()},
              'identity_key': binding(key_path.relative_to(ROOT).as_posix()),
              'contract_version': {'version': version,
                  'approved_document_sha256': '21c7cf2aa1b06c520564c5cfc18cd45eaab6d9f1e403bb7731ad94d58930b22a'}}
    config_path = ROOT / 'config' / (version + '.json')
    if config_path.exists():
        assert json.loads(config_path.read_text('utf-8')) == config
    else:
        save(config_path, config)
    print(json.dumps({'status': 'approved_inputs_frozen', 'rules_version': version,
                      'probe_requests': len(probes), 'private_key_content_logged': False}))


if __name__ == '__main__':
    main()
