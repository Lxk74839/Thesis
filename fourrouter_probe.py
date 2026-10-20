"""Local setup and PUBLIC fixture preparation. No live sender or token counter."""
import copy
import json
from pathlib import Path
import sys


PROJECT = Path(__file__).resolve().parent
PUBLIC_CONFIG = PROJECT / '.scratch/ticket14-live-integration-20261020/B-4router/config.draft.json'
LOCAL_CREDENTIAL = PROJECT / '.secrets/4router.json'


def _public_binding(path):
    binding = json.loads(Path(path).read_text(encoding='utf-8-sig'))['model_binding']
    expected = {'channel': '4Router', 'base_url': 'https://4router.net/v1', 'model_id': 'gpt-6-luna'}
    if any(binding.get(k) != v for k, v in expected.items()):
        raise ValueError('invalid_public_configuration')
    return {k: binding[k] for k in expected}


def check_config(*, public_path=PUBLIC_CONFIG, credential_path=LOCAL_CREDENTIAL):
    filled, valid = False, False
    try:
        data = json.loads(Path(credential_path).read_text(encoding='utf-8-sig'))
        key = data['api_key']
        filled = isinstance(key, str) and bool(key.strip())
        valid = (set(data) == {'api_key'} and isinstance(key, str)
                 and not any(c.isspace() or not 33 <= ord(c) <= 126 for c in key))
    except (OSError, ValueError, TypeError, KeyError):
        pass
    try:
        _public_binding(public_path)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        valid = False
    return {'api_key_filled': filled, 'local_config_valid': valid}


def prepare_probe(*, public_path=PUBLIC_CONFIG):
    binding = _public_binding(public_path)
    request = {'model': binding['model_id'], 'store': False, 'stream': False,
        'max_output_tokens': 256, 'parallel_tool_calls': False,
        'input': [{'role': 'user', 'content':
            'PUBLIC fictional protocol test. Read PUBLIC-REF-1, then report PUBLIC-OK.'}],
        'tools': [{'type': 'function', 'name': 'read_evidence', 'strict': True, 'parameters': {
            'type': 'object', 'properties': {'evidence_refs': {'type': 'array',
                'items': {'type': 'string', 'enum': ['PUBLIC-REF-1']}, 'minItems': 1, 'maxItems': 1}},
            'required': ['evidence_refs'], 'additionalProperties': False}}],
        'tool_choice': {'type': 'function', 'name': 'read_evidence'},
        'text': {'format': {'type': 'json_schema', 'name': 'PUBLIC_protocol_probe', 'strict': True,
            'schema': {'type': 'object', 'properties': {
                'probe': {'type': 'string', 'enum': ['PUBLIC-4ROUTER']},
                'result': {'type': 'string', 'enum': ['PUBLIC-OK']}},
                'required': ['probe', 'result'], 'additionalProperties': False}}}}
    return {'status': 'prepared_offline', 'input_scope': 'PUBLIC_fictional_only',
        'endpoint': binding['base_url'] + '/responses', 'request': request,
        'max_generate_requests': 2, 'max_count_requests': 0, 'cost': None,
        'execution_authorized': False}


def run_fixture_probe(transport, *, public_path=PUBLIC_CONFIG):
    """Test-only external transport injection; never establishes live provenance."""
    prepared = prepare_probe(public_path=public_path)
    request = prepared['request']
    result = {'provenance': 'fixture', 'provider_requests_sent': 0, 'fixture_calls': 0, 'cost': None}
    stage = 'first_response'
    try:
        result['fixture_calls'] += 1
        first = transport(prepared['endpoint'], copy.deepcopy(request))
        if first['status'] != 'completed' or first['model'] != request['model'] or len(first['output']) != 1:
            raise ValueError('invalid_first_response')
        call = first['output'][0]
        if (call['type'] != 'function_call' or call['name'] != 'read_evidence'
                or not isinstance(call['call_id'], str) or not call['call_id'].strip()
                or json.loads(call['arguments']) != {'evidence_refs': ['PUBLIC-REF-1']}):
            raise ValueError('invalid_tool_call')
        request['input'].extend([copy.deepcopy(call), {'type': 'function_call_output',
            'call_id': call['call_id'], 'output': json.dumps({'marker': 'PUBLIC-OK'})}])
        request['tool_choice'] = 'none'
        stage = 'final_response'
        result['fixture_calls'] += 1
        final = transport(prepared['endpoint'], copy.deepcopy(request))
        if final['status'] != 'completed' or final['model'] != request['model'] or len(final['output']) != 1:
            raise ValueError('invalid_final_response')
        message = final['output'][0]
        if message['type'] != 'message' or len(message['content']) != 1:
            raise ValueError('invalid_final_message')
        content = message['content'][0]
        if (content['type'] != 'output_text' or json.loads(content['text']) != {
                'probe': 'PUBLIC-4ROUTER', 'result': 'PUBLIC-OK'}):
            raise ValueError('invalid_structured_output')
        return result | {'status': 'fixture_passed'}
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return result | {'status': 'fixture_failed', 'error': stage}


def main(argv=None, *, public_path=PUBLIC_CONFIG, credential_path=LOCAL_CREDENTIAL):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ['check']:
        result = check_config(public_path=public_path, credential_path=credential_path)
        print(json.dumps(result))
        return 0 if result['local_config_valid'] else 2
    if argv == ['prepare']:
        try:
            result = prepare_probe(public_path=public_path)
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            result = {'status': 'invalid_public_configuration'}
        print(json.dumps(result))
        return 0 if result['status'] == 'prepared_offline' else 2
    if argv == ['probe']:
        print(json.dumps({'status': 'contract_confirmation_required', 'provider_requests_sent': 0,
            'max_generate_requests_proposed': 2, 'max_count_requests_proposed': 0, 'cost': None,
            'required_contract_changes': ['PUBLIC_probe_without_preflight_count',
                'explicit_acceptance_of_unknown_cost_and_request_caps']}))
        return 2
    print(json.dumps({'status': 'invalid_command'}))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
