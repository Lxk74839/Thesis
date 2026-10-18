"""Handwritten public native requests and explicit fixture units; never a tokenizer."""
import copy
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys

MODEL = 'gpt-5.4-mini-2026-03-17'
PROJECT = Path(__file__).resolve().parents[1]
BINDING = {'execution_kind': 'openai_native_fixture', 'model_id': MODEL,
           'provenance': 'fixture', 'project_id': 'PUBLIC-PROJECT'}
FINAL_SCHEMA = {'type': 'object', 'properties': {'kind': {'type': 'string', 'enum': ['final_submit']},
    'data': {'type': 'object', 'properties': {'draft_id': {'type': 'string'}},
             'required': ['draft_id'], 'additionalProperties': False}},
    'required': ['kind', 'data'], 'additionalProperties': False}


def request():
    return {'schema_version': 'rsm-model-request-0.3.0', 'execution_kind': 'openai_native_fixture',
        'request_id': 'PUBLIC-REQUEST', 'attempt_id': 'PUBLIC-ATTEMPT', 'run_id': 'PUBLIC-RUN',
        'session_id': 'PUBLIC-RUN:推荐管理', 'role': '推荐管理', 'reply_to': None,
        'model_id': MODEL, 'messages': [{'role': 'system', 'content': '公开协议\nSIM'},
            {'role': 'user', 'content': {'H': ['rice'], 'C': ['PUBLIC-A']}},
            {'role': 'assistant', 'content': None, 'tool_requests': [
                {'call_id': 'PUBLIC-CALL', 'name': 'list_evidence', 'arguments': {'cursor': None}}]},
            {'role': 'tool', 'tool_call_id': 'PUBLIC-CALL', 'content': {'entries': [], 'next_cursor': None}}],
        'tools': [{'name': 'list_evidence', 'version': 'restricted-evidence-0.1.0',
            'input_schema': {'type': 'object', 'properties': {'cursor': {'type': ['string', 'null']}},
                             'required': ['cursor'], 'additionalProperties': False}}],
        'output_kind': 'final_submit', 'output_schema': copy.deepcopy(FINAL_SCHEMA),
        'max_output_tokens': 1500, 'input_token_upper_bound': 0,
        'deadline_ms': 45000, 'reservation_id': 'PUBLIC-RESERVATION'}


def case_directory(name):
    parent = PROJECT / 'data/recommendation-runtime-audit/20261018-batch/cases' / os.environ['THESIS_BATCH_CHECK_LABEL']
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=name + '-', dir=parent))


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, allow_nan=False)


def native_response():
    return {'status_code': 200, 'headers': {'x-request-id': 'PUBLIC-HTTP-ID'}, 'body': {
        'id': 'PUBLIC-RESPONSE-ID', 'model': MODEL, 'service_tier': 'default', 'status': 'completed',
        'output': [{'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text',
            'text': '{"kind":"final_submit","data":{"draft_id":"PUBLIC-DRAFT"}}'}]}],
        'usage': {'input_tokens': 100, 'input_tokens_details': {'cached_tokens': 40, 'cache_write_tokens': 0},
                  'output_tokens': 30, 'output_tokens_details': {'reasoning_tokens': 20}, 'total_tokens': 130},
        'error': None, 'incomplete_details': None}}


def reserved_native(sender, *, now=None):
    from evidence_access import RootBudget
    from model_adapter import ModelAdapter
    from token_counting import InputCounter
    root = case_directory('native-invoke')
    limits = dict.fromkeys(RootBudget.resources, 0)
    limits.update(model_calls=2, input_tokens=1000, output_tokens=2000, cost_microusd=100000, elapsed_ms=60000)
    now = [0] if now is None else now
    budget = RootBudget({'run_id': 'PUBLIC-RUN', 'project_id': 'PUBLIC-PROJECT'}, limits,
        dict.fromkeys(RootBudget.resources, 0), clock=lambda: now[0], journal_path=root / 'budget.jsonl')
    counter = InputCounter('PUBLIC-PROJECT', fixture_count=100)
    adapter = ModelAdapter(sender, capability_binding=BINDING, counter=counter, root_budget=budget)
    req = request()
    prepared = adapter.prepare(req)
    count = counter.count(prepared, authorization=None)
    reservation = budget.reserve({'kind': 'model', 'request_id': req['request_id'],
        'prepared_id': prepared['prepared_id'], 'wire_sha256': prepared['wire_sha256'],
        'count_receipt_id': count['receipt_id']}, {'model_calls': 1, 'input_tokens': 100,
        'output_tokens': 1500, 'cost_microusd': 6825, 'elapsed_ms': 45000}, phase='final', retry_of=None)
    req.update(prepared_id=prepared['prepared_id'], count_receipt_id=count['receipt_id'],
               input_token_upper_bound=100, reservation_id=reservation['reservation_id'])
    return adapter, req, root


def export_catalog(root, prepared_rows):
    source = root / 'prepared.jsonl'
    plan = {'schema_version': 'openai-count-plan-0.1.0', 'scope': 'public_fixture', 'project_id': 'PUBLIC-PROJECT',
        'roots': [{'run_id': p['source']['run_id'], 'method': 'M'} for p in prepared_rows],
        'expected': [p['source'] for p in prepared_rows]}
    plan['roots'] = list({r['run_id']: r for r in plan['roots']}.values())
    source.write_text('\n'.join(json.dumps(row, ensure_ascii=False) for row in [{'plan': plan}, *prepared_rows]) + '\n', encoding='utf-8')
    target = root / 'manifest.json'
    proc = subprocess.run([sys.executable, '-B', '-m', 'token_counting', 'export', '--prepared', str(source),
        '--output', str(target)], cwd=PROJECT, capture_output=True, text=True, encoding='utf-8')
    return proc, target


def count_permit(root, manifest):
    return {'schema_version': 'openai-count-permit-0.1.0', 'enabled': True, 'scope': 'fixture_count',
        'authorization_ref': 'PUBLIC-FIXTURE-ONLY', 'project_id': 'PUBLIC-PROJECT', 'model_id': MODEL,
        'manifest_id': manifest['manifest_id'], 'endpoint': 'https://api.openai.com/v1/responses/input_tokens',
        'max_calls': len(manifest['entries']), 'started_ms': 0, 'deadline_ms': 30000, 'budget_microusd': 5,
        'journal_path': str(root / 'count-journal.jsonl'),
        'rate': {'currency': 'USD', 'unit': 'request', 'success_microusd': 2, 'failure_microusd': 3,
                 'evidence_sha256': 'a' * 64, 'basis': 'fixture'}}


class NativeScriptedSender:
    """Public model substitute consumes the exact native wire; usage is literal fixture units."""
    def __init__(self):
        from tests.test_batched_recommendation import BatchTransport
        self.script = BatchTransport()
        self.wires = []

    def __call__(self, body, *, deadline_ms):
        wire = json.loads(body)
        self.wires.append(wire)
        messages = []
        for item in wire['input']:
            if 'role' in item:
                try:
                    content = json.loads(item['content'])
                except ValueError:
                    content = item['content']
                messages.append({'role': item['role'], 'content': content})
            elif item['type'] == 'function_call':
                messages.append({'role': 'assistant', 'content': None, 'tool_requests': [
                    {'call_id': item['call_id'], 'name': item['name'], 'arguments': json.loads(item['arguments'])}]})
            else:
                messages.append({'role': 'tool', 'tool_call_id': item['call_id'], 'content': json.loads(item['output'])})
        kind = wire['text']['format']['name'].removeprefix('rsm_')
        n = len(self.wires)
        logical = {'messages': messages, 'tools': wire['tools'], 'output_kind': kind,
            'request_id': 'PUBLIC-SENDER-' + str(n), 'attempt_id': 'PUBLIC-SENDER-' + str(n), 'run_id': 'PUBLIC-SENDER'}
        message = self.script(logical)['message']
        response = native_response()
        response['body']['id'] = 'PUBLIC-NATIVE-' + str(n)
        response['body']['usage']['input_tokens_details']['cached_tokens'] = 0
        if message['tool_requests']:
            response['body']['output'] = [{'type': 'function_call', 'call_id': c['call_id'], 'name': c['name'],
                'arguments': json.dumps(c['arguments'])} for c in message['tool_requests']]
        else:
            response['body']['output'][0]['content'][0]['text'] = json.dumps(message['content'], ensure_ascii=False)
        return response
