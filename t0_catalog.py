"""Offline, synthetic T0-A request directory. This module has no sender or counter."""
import argparse
import copy
from collections import Counter
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import subprocess
import time

from evidence_access import EvidenceSession, LocalEvidenceSource, decode, digest, encoded
from joint_access import JointSession
from model_adapter import ModelAdapter
from provider_openai import MODEL
from recommendation_runner import COMPOSER_VERSION, compose_role_request

PROJECT = Path(__file__).resolve().parent
BASE = '88e8b8028bd40fb8a5c3f8fda994cbe9eef1324a'
AUTH_KEYS = set('schema_version approved scope contract human_confirmation base candidate program_acceptance '
                'sources budget_candidate resource_ledger api_limits'.split())
SOURCE_KEYS = set('accounts identity_key model_roots model_candidates model_catalog view_bindings'.split())
TOKENS = re.compile(rb'"(?:[^"\\]|\\.)*"|[{}\[\]:,]')
SCRIPT = 't0-controlled-trace-0.1.0'
VIEWS = ('V00', 'V01', 'V03', 'V05', 'V06', 'V07', 'V09', 'V12', 'Q1', 'Q2')
CONTROL = '.scratch/ticket12-budget-20261018/'
DEV_PINS = {
    'joint_config': ('config/joint-task-package-0.1.0.json', 'c8f6655ff21f189f28df316559208e29975eb3fa315c1373b50ec2802a4e6382'),
    'joint_record': ('records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0.json', '2226fb160a0e25cdf4c1ecf3b7bf213197de144bbd97286311b0bf0f58f9eb58'),
    'joint_acceptance': ('records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0-acceptance.json', '9937ff98a530b0b51cb072fc9d055da9bc11f006dcca8ac4296500bed3200976'),
    'split_record': ('records/splits/grain-A-1.1.15-user-split-1.0.0.json', '2da2aede2c3057c914621bfaf40d2d5ba81b3ad1a1b694451213ea8358a21131'),
    'split_acceptance': ('records/splits/grain-A-1.1.15-user-split-1.0.0-acceptance.json', '8af692d6409c8136bd67e6d5fbb696c9e725e53aea958ea639417153382d45ad'),
    'preference_config': ('config/preference-task-1.0.1.json', '834a19ed0d369d5e0e56a0243b23bf708c8e76798d882eff118adc3449ee4b2f')}
IMPLEMENTATION = ('t0_catalog.py', 'model_adapter.py', 'recommendation_runner.py', 'evidence_access.py',
    CONTROL + 'diagnostics/run_check.py', CONTROL + 'diagnostics/check_t0_catalog_delivery.py')
LIMITS = {'model_calls': 17, 'input_tokens': 192000, 'output_tokens': 24000, 'logical_tools': 4096,
    'physical_tools': 256, 'candidates': 64, 'retries': 2, 'elapsed_ms': 900000, 'cost_microusd': 252017}
FINAL = {'model_calls': 1, 'input_tokens': 8000, 'output_tokens': 1500, 'logical_tools': 1,
    'physical_tools': 0, 'candidates': 0, 'retries': 0, 'elapsed_ms': 60000, 'cost_microusd': 12751}


class _DigestStream:
    def __init__(self, path, recompute):
        self.stream = None if recompute else path.open('xb')
        self.sha, self.bytes = hashlib.sha256(), 0
        self.records, self.operations = 0, 0

    def write(self, raw):
        self.sha.update(raw)
        self.bytes += len(raw)
        self.records += 1
        if self.stream:
            self.stream.write(raw)

    def close(self):
        if self.stream:
            self.stream.flush()
            self.stream.close()

    def info(self):
        return {'bytes': self.bytes, 'sha256': self.sha.hexdigest()}


def _budget(method):
    limits, final = LIMITS.copy(), FINAL.copy()
    if method == 'R':
        for key in ('model_calls', 'input_tokens', 'output_tokens', 'cost_microusd'):
            limits[key] = final[key] = 0
    return {'version': 'B02-A+B03', 'limits': limits, 'final_reserve': final,
        'single_request': {'input_tokens': 96000, 'output_cap': 8192, 'elapsed_ms': 45000},
        'final_request': {'input_tokens': 8000, 'output_cap': 1500, 'elapsed_ms': 45000},
        'program_final_commit_seal_ms_each': 5000, 'batch_limit': 32, 'backoff_ms': [1000, 2000],
        'provenance': 'unapproved_T0_validation_candidate', 'spending_authorized': False}


def _clause_ids(view):
    return [c['clause_id'] if isinstance(c, dict) else c for c in view['request']['necessary_clauses']]


def _queue(parents, scores):
    return [parent for parent, score in sorted(zip(parents, scores), key=lambda pair: (-pair[1], pair[0].encode()))]


def _replace(value, replacements):
    if isinstance(value, dict):
        return {replacements.get(k, k): _replace(v, replacements) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace(v, replacements) for v in value]
    return replacements.get(value, value) if isinstance(value, str) else value


def _planned_template(value, namespace):
    replacements = {}
    ids = {'receipt_id', 'request_id', 'adapter_request_id', 'evidence_ref', 'scope_handle', 'source_ref', 'next_cursor'}
    def visit(item):
        if isinstance(item, dict):
            for key in item:
                val = item[key]
                if key in ids and isinstance(val, str) and val not in replacements:
                    replacements[val] = namespace + ':' + str(len(replacements))
                visit(val)
        elif isinstance(item, list):
            for val in item:
                visit(val)
    visit(value)
    return _replace(value, replacements)


def _dependency(view, parent, batch, source, dependencies, probes, cache):
    identity = [view['label'], view['snapshot'], view['principal_id'], view['verify_at_ms'],
                view['request'], parent, batch]
    template_id = digest(encoded(identity))
    if template_id in cache:
        return cache[template_id]
    started = time.perf_counter()
    binding = {'run_id': 'template:' + template_id, 'root_task_id': 'template:' + template_id,
        'parent_asin': parent, 'sim_batch_id': batch, 'snapshot_id': view['snapshot_id'],
        'verify_at_ms': view['verify_at_ms'], 'principal_id': view['principal_id'],
        'necessary_clauses': _clause_ids(view)}
    session = EvidenceSession(binding, source, limits={'logical_tools': 4096, 'physical_tools': 256,
        'candidates': 64, 'retries': 2, 'elapsed_ms': 900000},
        final_reserve={'logical_tools': 1, 'physical_tools': 0, 'elapsed_ms': 60000}, clock=lambda: 0)
    operations, entries, cursor = [], [], None
    try:
        while True:
            result = session.dispatch('list_evidence', {'cursor': cursor})
            operations.append({'operation': 'list_evidence', 'arguments': {'cursor': cursor}, 'result': result})
            _require(result['status'] == 'ok', 'dependency_list_failed')
            entries.extend(result['entries'])
            cursor = result['next_cursor']
            if cursor is None:
                break
        entries.sort(key=lambda r: (r['target_kind'], r['target_id'].encode(), r['version']))
        for offset in range(0, len(entries), 32):
            args = {'evidence_refs': [r['evidence_ref'] for r in entries[offset:offset + 32]]}
            result = session.dispatch('read_evidence', args)
            operations.append({'operation': 'read_evidence', 'arguments': args, 'result': result})
            _require(result['status'] == 'ok', 'dependency_read_failed')
        result = session.assess_current()
        operations.append({'operation': 'assess_current', 'arguments': {}, 'result': result})
        _require(result['status'] == 'ok' and result['assessment']['advance_allowed'], 'dependency_assessment_incomplete')
    finally:
        audit = session.audit_view()
        probes.operations += len(operations)
        probes.write(encoded({'template_id': template_id, 'provenance': 'actual_template_probe_with_synthetic_clock',
            'wall_seconds': time.perf_counter() - started, 'operations': operations, 'audit': audit}) + b'\n')
        probes.stream.flush()
    stable = _planned_template({'operations': operations, 'acquired': audit['acquired']}, 'synthetic-template:' + template_id)
    template = {'template_id': template_id, 'provenance': 'derived_from_actual_production_template_probe',
        'scope': identity, **stable}
    dependencies.write(encoded(template) + b'\n')
    cache[template_id] = template
    return template


def _prefix(view, candidate, run_id, sources, dependencies, probes, cache, method):
    order = _queue(candidate['C'], candidate['b'])
    batches = dict(zip(candidate['C'], candidate['batches']))
    processed, steps, refs, eligible, cells = [], [], [], [], []
    usage = {'logical_tools': 0, 'physical_tools': 0, 'candidates': 0}
    acquired = {'context': {}, 'candidates': {}, 'assessments': {}}
    stop = None
    for parent in order[:64]:
        if view['label'] not in sources:
            sources[view['label']] = LocalEvidenceSource(view['snapshot'], indexed=True)
        batch = batches[parent]
        template = _dependency(view, parent, batch, sources[view['label']], dependencies, probes, cache)
        namespace = 'synthetic-plan:' + digest(encoded([run_id, parent]))
        # Rebind deterministic template IDs into this root/method; never reuse another root's receipt.
        rebound = _replace(template, {s: namespace + s.split(':')[-1] for s in _template_ids(template)})
        cells.append(rebound)
        if method != 'R' and len(processed) % 32 == 0:
            usage['logical_tools'] += 1
            steps.append({'candidate_id': parent, 'operation': 'begin_batch', 'status': 'ok',
                'receipt_id': namespace + ':begin', 'usage_delta': {'logical_tools': 1, 'physical_tools': 0},
                'provenance': 'synthetic_planned_cold'})
        context_count = len(rebound['acquired']['context'])
        acquired['context'] = acquired['context'] or rebound['acquired']['context']
        acquired['candidates'][parent] = rebound['acquired']['candidates'][parent]
        assessment = rebound['operations'][-1]['result']['assessment']
        acquired['assessments'][parent] = assessment
        refs.append(template['template_id'])
        for index, operation in enumerate(rebound['operations']):
            receipt = operation['result']['receipt']
            delta = receipt['usage_delta'].copy()
            if processed and index == 0:
                delta['logical_tools'] -= context_count
            for key in ('logical_tools', 'physical_tools'):
                usage[key] += delta[key]
            steps.append({'candidate_id': parent, 'operation': operation['operation'],
                'receipt_id': receipt['receipt_id'], 'template_id': template['template_id'],
                'status': operation['result']['status'], 'usage_delta': delta,
                'provenance': 'synthetic_planned_cold'})
        processed.append(parent)
        usage['candidates'] += 1
        if assessment['eligible']:
            eligible.append(parent)
        if view['arm'] == 'necessary' and len(eligible) == 10:
            stop = 'first_10_qualified'
            break
        if len(processed) < min(len(order), 64):
            usage['logical_tools'] += 1
            steps.append({'candidate_id': parent, 'operation': 'advance_current', 'status': 'ok',
                'receipt_id': namespace + ':advance', 'usage_delta': {'logical_tools': 1, 'physical_tools': 0},
                'provenance': 'synthetic_planned_cold'})
    stop = stop or ('complete_C' if len(processed) == len(order) else
                    'quality_prefix' if view['arm'] == 'quality' else 'candidate_prefix')
    return {'processed': processed, 'steps': steps, 'stop_reason': stop, 'planned_cold_usage': usage,
            'dependency_refs': refs, 'G': eligible, 'acquired': acquired, 'cells': cells}


def _template_ids(value):
    found = set()
    def visit(item):
        if isinstance(item, dict):
            for key, val in item.items():
                visit(key)
                visit(val)
        elif isinstance(item, list):
            for val in item:
                visit(val)
        elif isinstance(item, str) and item.startswith('synthetic-template:'):
            found.add(item)
    visit(value)
    return found


def _visible(value):
    """Replace host provenance locations by opaque references, keeping acquired original bytes."""
    if isinstance(value, list):
        return [_visible(v) for v in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, val in value.items():
        if key == 'source' and isinstance(val, dict):
            result['source_ref'] = 'synthetic-source:' + digest(encoded(val))
        else:
            result[key] = _visible(val)
    return result


def _quality(binding, view, acquired):
    if view['arm'] != 'quality' or not acquired['candidates']:
        return {}, [p for p in binding['C'] if p in acquired['assessments'] and acquired['assessments'][p]['eligible']]
    from evidence_verification import rank_acquired_quality
    from quality_fusion import RULES
    acquired['binding'] = {'root_task_id': binding['root_task_id'], 'snapshot_id': view['snapshot_id'],
        'principal_id': view['principal_id'], 'verify_at_ms': view['verify_at_ms']}
    acquired['candidate_binding'] = {'C': binding['C'], 'base_scores': binding['base_scores']}
    fusion = {'schema_version': 'fusion-binding-0.1.0', 'task_id': binding['root_task_id'],
        'C': binding['C'], 'C_sha256': digest(encoded(binding['C'])), 'H_sha256': binding['H_sha256'],
        'base_scores': binding['base_scores'], 'base_score_version': 'char3-tfidf-history-1.0.0',
        'base_score_sha256': binding['base_score_sha256'], 'snapshot_id': view['snapshot_id'],
        'verify_at_ms': view['verify_at_ms'], 'principal_id': view['principal_id'],
        'contract_sha256': digest(encoded(RULES)), 'K': 10, 'alpha': .5, 'beta': [.25, .5, .25], 'mode': 'full',
        'preference': {'source': 'experiment_design', 'dimensions': ['retail_stock'], 'weights': {'retail_stock': 1}}}
    ranked = rank_acquired_quality(fusion, acquired)
    return {r['parent_asin']: {k: r[k] for k in ('z', 'm', 'q', 'stock_state')} for r in ranked['candidates']}, ranked['order']


def _trace(binding, view, initial, prefix):
    """One declared synthetic path, including two format failures and one bounded feedback."""
    state = {'queue': _queue(binding['C'], binding['base_scores']),
        'cursor': 0, 'stop_reason': None, 'assessments': {}, 'G': [], 'drafts': [], 'visible_issues': [],
        'messages': [], 'batches': [], 'profile_batch_start': 0, 'input_projection_sha256': digest(encoded(initial))}
    acquired = {'context': {}, 'candidates': {}, 'assessments': {}}
    quality, ordered = {}, []
    def request(role, kind, stage):
        return compose_role_request(binding=binding, state=state, acquired=acquired, initial_messages=initial,
            quality=quality, ordered=ordered, role=role, kind=kind, stage=stage,
            output_cap=1500 if kind == 'final_submit' else 8192,
            request_id=binding['run_id'] + ':message:' + str(len(state['messages'])), protocol=COMPOSER_VERSION)
    def emit(logical, data=None, calls=None, failure=False):
        message = {'role': 'assistant', 'content': None if calls or failure else {'kind': logical['output_kind'], 'data': data},
                   'tool_requests': calls or []}
        response = {'status': 'format_error' if failure else 'ok', 'message': message,
                    'raw': '{synthetic malformed' if failure else None}
        stage = next(m['content']['runtime']['stage'] for m in reversed(logical['messages'])
            if m['role'] == 'user' and isinstance(m['content'], dict) and 'runtime' in m['content'])
        yield logical, response, stage
        # The composer only needs the previous stage and successful output, not another copy of each full W.
        state['messages'].append({'role': logical['role'], 'role_message_id': logical['request_id'],
            'request': {'output_kind': logical['output_kind'], 'messages': [{'role': 'user', 'content': {'runtime': {'stage': stage}}}]},
            'response': response})
        return message
    for role in ('需求解析', '用户画像'):
        logical = request(role, 'analysis', role)
        yield from emit(logical, failure=True)
        retry = copy.deepcopy(logical)
        retry.update(request_id=binding['run_id'] + ':message:' + str(len(state['messages'])),
                     attempt_id=binding['run_id'] + ':message:' + str(len(state['messages'])), reply_to=logical['request_id'])
        retry['messages'].append({'role': 'user', 'content': {'retry_of': logical['request_id'], 'error': 'format'}})
        observations = [] if role == '需求解析' else [{'pointer': '/H', 'value': decode(initial[0]['content'].encode())['H'],
                                                       'preference_status': 'history_fact'}]
        yield from emit(retry, {'necessary_clauses': binding['necessary_clauses'], 'observations': observations})
    for offset in range(0, max(1, len(prefix['processed'])), 32):
        parents = prefix['processed'][offset:offset + 32]
        dispatch = request('推荐管理', 'dispatch', 'dispatch')
        target = '单智能体' if binding['method'] == 'S' else '生命周期追溯'
        yield from emit(dispatch, {'candidate': parents[0] if parents else None, 'to': target,
            'claim_ids': binding['necessary_clauses'], **({'candidate_limit': 32} if parents else {})})
        logical = request('生命周期追溯', 'acquire', 'acquire')
        if parents:
            cells = prefix['cells'][offset:offset + 32]
            plan = {'schema_version': 'acquisition-batch-0.1.0', 'start_candidate': parents[0], 'candidate_limit': 32,
                'claim_ids': binding['necessary_clauses'], 'max_list_pages': sum(sum(o['operation'] == 'list_evidence' for o in c['operations']) for c in cells),
                'max_read_batches': max(1, sum(sum(o['operation'] == 'read_evidence' for o in c['operations']) for c in cells)),
                'stop_policy': 'fixed_prefix' if view['arm'] == 'quality' else 'first_10_qualified'}
            call = {'call_id': logical['attempt_id'] + ':batch', 'name': 'acquire_batch', 'arguments': plan}
            message = yield from emit(logical, calls=[call])
            batch_steps = [s for s in prefix['steps'] if s['candidate_id'] in parents]
            observations = []
            for parent, cell in zip(parents, cells):
                acquired['context'] = acquired['context'] or cell['acquired']['context']
                acquired['candidates'][parent] = cell['acquired']['candidates'][parent]
                assessment = cell['operations'][-1]['result']['assessment']
                state['assessments'][parent] = acquired['assessments'][parent] = assessment
                observations.append({'candidate_id': parent,
                    'entries': [e for o in cell['operations'] for e in o['result'].get('entries', [])],
                    'items': [i for o in cell['operations'] for i in o['result'].get('items', [])],
                    'assessment_receipt_id': cell['operations'][-1]['result']['receipt']['receipt_id']})
            state['profile_batch_start'] = len(state['batches'])
            batch = {'status': 'ok', 'plan_sha256': digest(encoded(plan)), 'processed': parents,
                'assessments': {p: state['assessments'][p] for p in parents}, 'observations': observations,
                'steps': batch_steps, 'stop_reason': prefix['stop_reason'] if offset + len(parents) == len(prefix['processed']) else 'batch_limit',
                'usage_after': {'input_tokens': None, 'output_tokens': None, 'cost_microusd': None},
                'provenance': 'synthetic_planned_cold'}
            state['batches'].append(batch)
            state['cursor'] += len(parents)
            state['G'] = [p for p in state['queue'] if state['assessments'].get(p, {}).get('eligible')]
            if batch['stop_reason'] != 'batch_limit':
                state['stop_reason'] = batch['stop_reason']
            quality, ordered = _quality(binding, view, acquired)
            if view['arm'] != 'quality':
                ordered = [p for p in state['queue'] if p in state['G']]
            continuation = copy.deepcopy(logical)
            continuation.update(request_id=binding['run_id'] + ':message:' + str(len(state['messages'])),
                attempt_id=binding['run_id'] + ':message:' + str(len(state['messages'])), reply_to=logical['request_id'])
            continuation['messages'].extend([message, {'role': 'tool', 'tool_call_id': call['call_id'], 'content': _visible(batch)}])
            yield from emit(continuation, {'done': True, 'plan_sha256': batch['plan_sha256'], 'processed': parents})
        else:
            state['stop_reason'] = 'complete_C'
            yield from emit(logical, {'done': True})
        profile = request('农产品画像', 'analysis', '农产品画像')
        context = profile['messages'][-1]['content']['runtime']
        observations = []
        for parent in parents or [None]:
            assessment = state['assessments'].get(parent)
            attributes = []
            for fact in context['facts'].get(parent, []):
                row = fact['data']
                keys = ('conclusion',) if row.get('kind') == 'inspection_report' else ('status', 'stock_units') if row.get('kind') == 'retail_status' else ()
                for key in keys:
                    if key in row['facts']:
                        attributes.append({'attribute': key, 'value': row['facts'][key],
                            'unit': row['facts'].get('unit') if key == 'stock_units' else None,
                            'citation': {**fact['citation'], 'pointer': '/facts/' + key}})
            observations.append({'candidate_id': parent, **({'assessment_receipt_id': context['assessment_receipts'][parent]} if parents else {'assessment': None}),
                'quality': quality.get(parent), 'attributes': attributes,
                'unknown': ['empty_C'] if parent is None else [c for c, v in assessment['claims'].items() if v['evidence_state'] != 'Supported']
                    + (['retail_stock'] if quality.get(parent) and not quality[parent]['z'] else [])})
        yield from emit(profile, {'necessary_clauses': binding['necessary_clauses'], 'observations': observations})
    draft_request = request('推荐管理', 'draft', 'draft')
    context = draft_request['messages'][-1]['content']['runtime']
    reason_text = {'inspection_supported': '检验必要条件有完整有效支持（SIM）。',
                   'on_sale_supported': '核验时点的在售必要条件有完整有效支持（SIM）。'}
    items = [{'parent_asin': p, 'sim_batch_id': context['candidate_batches'][p], 'reasons': [
        {'claim_id': c, 'kind': 'inspection_supported' if c == 'c1' else 'on_sale_supported', 'value': True,
         'unit': None, 'text': reason_text['inspection_supported' if c == 'c1' else 'on_sale_supported'],
         'citations': [f['citation'] for f in context['facts'][p]
             if f['citation']['evidence_ref'] in {a['evidence_ref'] for a in state['assessments'][p]['accepted']}]}
        for c in binding['necessary_clauses']]}
        for p in ordered[:10]]
    if items:
        items[0]['reasons'][0]['text'] = 'SIM synthetic statement awaiting the declared correction'
    draft = {'draft_id': binding['run_id'] + ':d0', 'parent_draft_id': None, 'items': items}
    yield from emit(draft_request, draft)
    state['drafts'].append(draft)
    issues = []
    if items:
        issues = [{'issue_id': draft['draft_id'] + ':synthetic-issue', 'draft_id': draft['draft_id'],
            'candidate_id': items[0]['parent_asin'], 'claim_id': binding['necessary_clauses'][0],
            'pointer': '/items/0/reasons/0/text', 'code': 'synthetic_statement_repair', 'blocking': True,
            'allowed_actions': ['revise_and_resubmit'], 'verifier': 'model',
            'source_receipts': [f['citation']['receipt_id'] for f in context['facts'][items[0]['parent_asin']]]}]
    yield from emit(request('推荐依据核验', 'verification', 'verification'), {'issues': issues})
    if issues:
        state['visible_issues'] = issues
        revised = copy.deepcopy(draft)
        revised.update(draft_id=binding['run_id'] + ':d1', parent_draft_id=draft['draft_id'])
        revised['items'][0]['reasons'][0]['text'] = reason_text[revised['items'][0]['reasons'][0]['kind']]
        yield from emit(request('推荐管理', 'draft', 'revision'), revised)
        state['drafts'].append(revised)
        yield from emit(request('推荐依据核验', 'verification', 'verification'), {'issues': []})
        state['visible_issues'] = []
    yield from emit(request('推荐管理', 'final_submit', 'final_submit'), {'draft_id': state['drafts'][-1]['draft_id']})


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _time_available():
    _require(float(os.environ.get('THESIS_RESOURCE_DEADLINE_UNIX', '0')) - time.time() > 30,
             'resource_closeout_required')


def _path(value):
    path = Path(value)
    _require('..' not in path.parts, 'unsafe_path')
    path = path if path.is_absolute() else PROJECT / path
    _require(path.is_relative_to(PROJECT), 'unsafe_path')
    for part in (path, *path.parents):
        if part.exists():
            _require(not part.is_symlink() and not part.is_junction()
                     and not (part.lstat().st_file_attributes & 1024), 'reparse_path')
        if part == PROJECT:
            break
    return path


def _checked(ref):
    _require(isinstance(ref, dict) and {'path', 'sha256'} <= set(ref) <= {'path', 'sha256', 'bytes'}, 'invalid_source_ref')
    path = _path(ref['path'])
    sha, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(chunk)
            size += len(chunk)
    _require(sha.hexdigest() == ref['sha256'] and ('bytes' not in ref or size == ref['bytes']), 'source_integrity_error')
    return path


def _content(ref):
    """For small files, including the identity key, read and authenticate exactly once."""
    raw = _path(ref['path']).read_bytes()
    _require(digest(raw) == ref['sha256'] and ('bytes' not in ref or len(raw) == ref['bytes']), 'source_integrity_error')
    return raw


def _development_authorization(auth):
    sources = auth['sources']
    _require(set(sources) == SOURCE_KEYS | set(DEV_PINS) | {'model_manifest'}, 'development_source_not_accepted')
    for role, (path, sha) in DEV_PINS.items():
        _require(sources[role]['path'] == path and sources[role]['sha256'] == sha, 'development_source_not_accepted')
    _require(auth['contract']['path'] == CONTROL + 't0-a-implementation-confirmation-20261018.md'
        and auth['contract']['sha256'] == '5d0e8e3f8e9b8130214d1202de736a73d2fa1bb2a09cb0a52d759067a81e957f'
        and auth['human_confirmation']['path'] == CONTROL + 'authorization-t0-a-20261018.md'
        and auth['human_confirmation']['sha256'] == '887699ecd2bfadceb7114bd6d94403152a0dfe2a9b088e5ce32548dd75fdeef8',
        'human_confirmation_mismatch')
    _require(auth['program_acceptance']['path'] == CONTROL + 'acceptance-t0-a-program-20261018.json',
             'program_acceptance_path_not_allowed')
    _require(os.environ.get('THESIS_RESOURCE_DOMAIN') == 't0' and auth['resource_ledger'] ==
        'data/recommendation-runtime-audit/ticket12-t0/resource-ledger.jsonl'
        and _path(os.environ.get('THESIS_RESOURCE_LEDGER', '')) == _path(auth['resource_ledger']), 'resource_domain_mismatch')
    records = {role: decode(_content(sources[role])) for role in DEV_PINS}
    accepted, record = records['joint_acceptance'], records['joint_record']
    _require(accepted['status'] == 'accepted_joint_preparation_component_only'
        and accepted['generation_record']['sha256'] == sources['joint_record']['sha256'], 'development_source_not_accepted')
    for role, name in {'model_roots': 'model/roots.jsonl', 'model_candidates': 'model/candidates.jsonl',
        'model_catalog': 'model/catalog.jsonl', 'model_manifest': 'model/manifest.json', 'view_bindings': 'view-bindings.jsonl'}.items():
        expected = record['components'][name]
        _require(all(sources[role].get(k) == expected[k] == accepted['components'][name][k]
                     for k in ('path', 'bytes', 'sha256')), 'development_source_not_accepted')
    _require(sources['accounts']['path'] == 'data/splits/grain-A-1.1.15/user-split-1.0.0/accounts.jsonl'
        and sources['accounts']['sha256'] == '05fbfdfcb5829fe09c71279748d9707ac1e25c8af6d496113ed804c221c2cbb4'
        and sources['identity_key']['path'] == 'data/task-inputs/preference-task-1.0.0/id-key.bin'
        and sources['identity_key']['sha256'] == 'd625d273299725dbd986e906d6573b0b32b626f928df64d95dfea8c3662af426'
        and sources['identity_key']['bytes'] == 32, 'development_source_not_accepted')
    _checked(sources['model_manifest'])
    acceptance = decode(_content(auth['program_acceptance']))
    _require(acceptance.get('status') == 'T0_A_program_accepted' and acceptance.get('base') == BASE
        and acceptance.get('candidate') == auth['candidate'] and re.fullmatch('[0-9a-f]{40}', auth['candidate'])
        and set(acceptance.get('source_sha256', {})) == set(IMPLEMENTATION), 'program_acceptance_required')
    for name, sha in acceptance['source_sha256'].items():
        _require(digest(_path(name).read_bytes()) == sha, 'program_source_changed')
    for axis in ('Standards', 'Spec'):
        review = acceptance['reviews'][axis]
        _require(re.fullmatch(re.escape(CONTROL) + 'verification-t0-a-' + axis.lower() + '-[0-9a-f]{7}\\.md',
                             review['record']['path']), 'review_path_not_allowed')
        _checked(review['record'])
        _require(review['candidate'] == auth['candidate'] and review['blocking_findings'] == 0, 'program_review_required')
    changed = subprocess.check_output(['git', 'diff', '--name-only', auth['candidate'], '--', *IMPLEMENTATION], cwd=PROJECT)
    _require(not changed.strip(), 'program_source_changed')


def _top_root(raw):
    """Lexical byte scan only: no history/candidate body is deserialized here."""
    depth, key, waiting, found = 0, None, False, []
    for match in TOKENS.finditer(raw):
        token = match[0]
        if token in (b'{', b'['):
            depth += 1
            if depth == 1:
                waiting = True
        elif token in (b'}', b']'):
            depth -= 1
        elif depth == 1:
            if token == b',':
                waiting, key = True, None
            elif token.startswith(b'"'):
                if waiting:
                    key, waiting = json.loads(token), False
                elif key == 'root_task_id':
                    found.append(json.loads(token))
                    key = None
    _require(depth == 0 and len(found) == 1 and isinstance(found[0], str), 'ambiguous_root_id')
    return found[0]


def _selected(ref, roots, multiple=False, source_index=None):
    selected, seen = [], set()
    with _checked(ref).open('rb') as stream:
        offset = 0
        for line, raw in enumerate(stream, 1):
            root = _top_root(raw)
            if root not in roots:
                offset += len(raw)
                continue
            row = decode(raw)
            _require(multiple or root not in seen, 'duplicate_source_root')
            seen.add(root)
            selected.append(row)
            if source_index is not None:
                source_index.append({'component': ref, 'root_task_id': root, 'line': line, 'offset': offset, 'bytes': len(raw)})
            offset += len(raw)
    _require(seen == roots, 'missing_source_root')
    return selected


def _authorization(path):
    try:
        path = _path(path)
        if not path.exists():
            raise FileNotFoundError
        _require(any(path.is_relative_to(PROJECT / root) for root in ('data/ticket12-t0', '.tmp/ticket12-t0'))
            and re.fullmatch('authorization(?:-[a-z0-9-]+)?\\.json', path.name), 'authorization_path_not_allowed')
        auth = decode(path.read_bytes())
    except FileNotFoundError:
        raise ValueError('authorization_unavailable') from None
    _require(isinstance(auth, dict) and set(auth) == AUTH_KEYS, 'invalid_authorization')
    _require(auth['schema_version'] == 't0-a-authorization-0.1.0' and auth['approved'] is True
        and auth['base'] == BASE and auth['budget_candidate'] == 'B02-A+B03'
        and auth['api_limits'] == {'count': 0, 'generate': 0, 'other': 0}, 'invalid_authorization')
    if auth['scope'] == 'development_catalog_only':
        _development_authorization(auth)
        _checked(auth['contract'])
        _checked(auth['human_confirmation'])
        return auth
    _require(auth['scope'] == 'public_catalog_test' and auth['candidate'] == 'PUBLIC', 'development_acceptance_required')
    _require(set(auth['sources']) == SOURCE_KEYS, 'invalid_source_set')
    _require(path.is_relative_to(PROJECT / '.tmp/ticket12-t0'), 'public_authorization_path_not_allowed')
    parent = path.parent
    for role, name in (('contract', 'PUBLIC-contract.md'), ('human_confirmation', 'PUBLIC-confirmation.md'),
                       ('program_acceptance', 'PUBLIC-acceptance.json')):
        _require(_path(auth[role]['path']) == parent / name, 'public_metadata_path_not_allowed')
    for ref in auth['sources'].values():
        _require(_path(ref['path']).is_relative_to(parent), 'public_source_outside_fixture')
    _require(os.environ.get('THESIS_RESOURCE_DOMAIN') == 'offline' and auth['resource_ledger'] ==
        'data/recommendation-runtime-audit/20261018-batch/resource-ledger.jsonl', 'resource_domain_mismatch')
    for role in ('contract', 'human_confirmation', 'program_acceptance'):
        _checked(auth[role])
    return auth


def _compile(auth, output, *, recompute=False):
    _time_available()
    sources = auth['sources']
    if recompute:
        first = decode((output / 'source-index.json').read_bytes())
        _require(first['selection_sources'] == {k: sources[k] for k in ('accounts', 'identity_key')}, 'selection_binding_changed')
        _checked(sources['accounts'])
        roots = set(first['selected_roots'])
    else:
        accounts = [decode(raw) for raw in _content(sources['accounts']).splitlines()]
        key = _content(sources['identity_key'])
        roots = {hmac.new(key, b'preference-task-1.0.1\0' + r['user_id'].encode(), hashlib.sha256).hexdigest()
                 for r in accounts if r['split'] == 'dev'}
        del key, accounts
    _require(bool(roots), 'no_development_roots')
    development = auth['scope'] == 'development_catalog_only'
    _require(not development or len(roots) == 320, 'development_root_count_mismatch')
    intervals = []
    model_roots = {r['root_task_id']: r for r in _selected(sources['model_roots'], roots, source_index=intervals)}
    candidates = {r['root_task_id']: r for r in _selected(sources['model_candidates'], roots, source_index=intervals)}
    views = _selected(sources['view_bindings'], roots, multiple=True, source_index=intervals)
    view_keys = [(v['root_task_id'], v['label']) for v in views]
    _require(len(view_keys) == len(set(view_keys)), 'duplicate_source_view')
    if development:
        _require(set(view_keys) == {(root, label) for root in roots for label in VIEWS}, 'missing_development_view')
        cfg = decode(_content(sources['joint_config']))
        for view in views:
            source_view = next(v for v in cfg['views'] if v['label'] == view['label'])
            _require(all(view[k] == v for k, v in source_view.items()) and view['principal_id'] == cfg['principal_id']
                and view['verify_at_ms'] == cfg['verify_at_ms'] and view['K'] == 10, 'view_binding_mismatch')
    else:
        source_parent = _path(sources['model_roots']['path']).parent
        for view in views:
            if 'snapshot' in view:
                _require(_path(view['snapshot']['path']).is_relative_to(source_parent), 'public_snapshot_outside_fixture')
    products = [decode(raw) for raw in _checked(sources['model_catalog']).read_bytes().splitlines()]
    adapter = ModelAdapter(None, capability_binding={'execution_kind': 't0_development_catalog',
        'model_id': MODEL, 'provenance': 'synthetic', 'project_id': 'UNBOUND-T0-DEV-CATALOG'})
    role_schema_generator_sha = digest((PROJECT / 'provider_openai.py').read_bytes())
    if not recompute:
        (output / 'objects').mkdir()
        (output / 'checks').mkdir()
    indexes, cache, objects = {}, {}, {}
    totals = dict.fromkeys(('plans', 'N', 'U', 'original_wire_bytes', 'original_count_payload_bytes',
        'unique_wire_bytes', 'unique_count_payload_bytes', 'missing_objects', 'failed_plans', 'excess_plans'), 0)
    by_method, by_view_method, by_terminal = Counter(), Counter(), Counter()
    components, reasons = {}, []
    source_index = {'schema_version': 't0-host-source-index-0.1.0', 'selected_roots': sorted(roots),
        'selection_sources': {k: sources[k] for k in ('accounts', 'identity_key')}, 'intervals': intervals}
    raw = encoded(source_index) + b'\n'
    if not recompute:
        (output / 'source-index.json').write_bytes(raw)
    components['source-index.json'] = {'bytes': len(raw), 'sha256': digest(raw)}
    stream = _DigestStream(output / 'roots.jsonl', recompute)
    requests = _DigestStream(output / 'requests.jsonl', recompute)
    dependencies = _DigestStream(output / 'dependencies.jsonl', recompute)
    probes = _DigestStream(output / ('checks/probes-recompute.jsonl' if recompute else 'checks/probes.jsonl'), False)
    active = None
    try:
        for view in sorted(views, key=lambda r: (r['root_task_id'], r['label'])):
            _time_available()
            root_id = view['root_task_id']
            root, candidate = model_roots[root_id], candidates[root_id]
            _require(root['H_sha256'] == digest(encoded(root['history']))
                and root['C_sha256'] == digest(encoded(candidate['C']))
                and len(candidate['C']) == len(candidate['b']) == len(candidate['batches']) == len(candidate['background_statistics']),
                'projection_binding_mismatch')
            _require(root['base_scores_sha256'] == digest(encoded(list(zip(candidate['C'], candidate['b']))))
                and len(set(candidate['C'])) == len(candidate['C']) and set(candidate['C']) <= {p['parent_asin'] for p in products}
                and (not development or 1488 <= len(candidate['C']) <= 1493), 'candidate_binding_mismatch')
            joint = JointSession(root, candidate, products, view, 'synthetic-session:' + digest(encoded([root_id, view['label']])))
            initial = copy.deepcopy(joint.dispatch('model_request', {})['request']['messages'])
            payload = decode(initial[0]['content'].encode())
            payload['H'] = payload.pop('history')
            payload.pop('input_fingerprint')
            payload['input_fingerprint'] = digest(encoded(payload))
            initial[0]['content'] = encoded(payload).decode()
            for method in ('R', 'S', 'M'):
                run_id = 'synthetic:' + digest(encoded([root_id, view['label'], method]))
                request_count, output_caps, repairs, feedback = 0, 0, 0, 0
                prefix = None
                active = {'root_task_id': root_id, 'view_label': view['label'], 'method': method, 'repeat': 1,
                    'run_id': run_id, 'C_count': len(candidate['C']), 'C_sha256': root['C_sha256'], 'H_sha256': root['H_sha256'],
                    'base_scores_sha256': root['base_scores_sha256']}
                prefix = _prefix(view, candidate, run_id, indexes, dependencies, probes, cache, method)
                if method != 'R':
                    binding = {'run_id': run_id, 'root_task_id': root_id, 'method': method, 'arm': view['arm'],
                        'execution_kind': 't0_development_catalog', 'orchestration': 'batch32-0.1.0',
                        'C': candidate['C'], 'base_scores': candidate['b'], 'batches': candidate['batches'],
                        'base_score_sha256': root['base_scores_sha256'], 'H_sha256': root['H_sha256'],
                        'K': 10, 'necessary_clauses': _clause_ids(view)}
                    for logical, response, stage in _trace(binding, view, initial, prefix):
                        _time_available()
                        prepared = adapter.prepare(logical)
                        _require(prepared['status'] == 'prepared', 'catalog_prepare_failed')
                        pid = prepared['prepared_id']
                        wb, pb = prepared['wire_bytes'], len(prepared['count_utf8'].encode())
                        totals['N'] += 1
                        totals['original_wire_bytes'] += wb
                        totals['original_count_payload_bytes'] += pb
                        if pid not in objects:
                            raw = encoded({**prepared, 'catalog_metadata': {'provenance': 'synthetic',
                                'tool_versions': {t['name']: t['version'] for t in logical['tools']},
                                'role_schema_generator_sha256': role_schema_generator_sha}}) + b'\n'
                            if not recompute:
                                (output / 'objects' / (pid + '.json')).write_bytes(raw)
                            objects[pid] = {'bytes': len(raw), 'sha256': digest(raw)}
                            totals['unique_wire_bytes'] += wb
                            totals['unique_count_payload_bytes'] += pb
                        request_count += 1
                        output_caps += logical['max_output_tokens']
                        repairs += response['status'] == 'format_error'
                        feedback += stage == 'revision'
                        semantic = ('推荐管理' if logical['output_kind'] in ('draft', 'dispatch', 'final_submit') else
                            '生命周期追溯' if logical['output_kind'] == 'acquire' else
                            '推荐依据核验' if logical['output_kind'] == 'verification' else stage)
                        requests.write(encoded({'root_task_id': root_id, 'view_label': view['label'], 'method': method,
                            'prepared_id': pid, 'semantic_role': semantic, 'effective_role': logical['role'],
                            'stage': stage, 'output_kind': logical['output_kind'], 'source': prepared['source'],
                            'script_response': response, 'provenance': 'synthetic', 'script_version': SCRIPT,
                            'input_tokens': None, 'output_tokens': None, 'cost_microusd': None,
                            'wire_bytes': wb, 'count_payload_bytes': pb, 'dependency_refs': prefix['dependency_refs']}) + b'\n')
                        _require(wb <= 16 * 1024**2 and pb <= 16 * 1024**2, 'body_limit_exceeded')
                        _require(request_count <= 17 and totals['N'] <= 108800, 'model_slot_limit_exceeded')
                # Program work and protected final are planned, never executed here.
                programs = ['submit_draft', 'verify_draft'] + (['patch', 'verify_draft'] if feedback else []) + ['final', 'commit', 'seal_audit']
                for operation in programs:
                    logical_cost = 0 if operation in ('commit', 'seal_audit') else 1
                    prefix['planned_cold_usage']['logical_tools'] += logical_cost
                    prefix['steps'].append({'operation': operation, 'candidate_id': None,
                        'receipt_id': run_id + ':program:' + str(len(prefix['steps'])), 'status': 'planned_only',
                        'phase': 'final' if operation in ('final', 'commit', 'seal_audit') else 'work',
                        'usage_delta': {'logical_tools': logical_cost, 'physical_tools': 0}, 'provenance': 'synthetic_planned_cold'})
                budget = _budget(method)
                excess = [k for k in ('logical_tools', 'physical_tools', 'candidates')
                    if prefix['planned_cold_usage'][k] > budget['limits'][k]]
                if request_count > budget['limits']['model_calls']:
                    excess.append('model_calls')
                totals['excess_plans'] += bool(excess)
                terminal = 'planned_nonempty_draft' if prefix['G'] else 'planned_no_supported_candidate'
                plan = {'root_task_id': root_id, 'view_label': view['label'], 'method': method, 'repeat': 1,
                    'run_id': run_id, 'C_count': len(candidate['C']), 'C_sha256': root['C_sha256'],
                    'H_sha256': root['H_sha256'], 'base_scores_sha256': root['base_scores_sha256'],
                    'candidate_source_sha256': sources['model_candidates']['sha256'],
                    'request_count': request_count, 'format_repairs': repairs, 'feedback_rounds': feedback,
                    'sum_requested_output_caps': output_caps, 'dynamic_budget_admission': None,
                    'complete_input_tokens': None if method != 'R' else 0, 'actual_output_tokens': None if method != 'R' else 0,
                    'actual_generation_cost_microusd': None if method != 'R' else 0,
                    'budget_candidate': budget, 'execution_budget': None, 'execution_authorized': False,
                    'planned_terminal': terminal, 'candidate_excess': excess, 'provenance': 'synthetic',
                    **{k: v for k, v in prefix.items() if k not in ('acquired', 'cells')}}
                stream.write(encoded(plan) + b'\n')
                if not recompute:
                    stream.stream.flush()
                    requests.stream.flush()
                totals['plans'] += 1
                by_method[method] += 1
                by_view_method[view['label'] + '/' + method] += 1
                by_terminal[terminal] += 1
                active = None
    except (ValueError, OSError, KeyError, TypeError, KeyboardInterrupt) as exc:
        reason = str(exc) if type(exc) is ValueError else 'interrupted' if isinstance(exc, KeyboardInterrupt) else type(exc).__name__
        reasons.append(reason)
        totals['failed_plans'] += 1
        if active is not None:
            partial = {**active, 'failure_reason': reason, 'planned_terminal': 'T0_A_incomplete',
                'request_count': request_count, 'sum_requested_output_caps': output_caps,
                'format_repairs': repairs, 'feedback_rounds': feedback, 'provenance': 'synthetic',
                'budget_candidate': _budget(method), 'execution_budget': None, 'execution_authorized': False,
                'complete_input_tokens': None if method != 'R' else 0, 'actual_output_tokens': None if method != 'R' else 0,
                **({k: v for k, v in prefix.items() if k not in ('acquired', 'cells')} if prefix is not None else {})}
            stream.write(encoded(partial) + b'\n')
            totals['plans'] += 1
            by_method[method] += 1
            by_view_method[view['label'] + '/' + method] += 1
            by_terminal['T0_A_incomplete'] += 1
    finally:
        for name, target in (('roots.jsonl', stream), ('requests.jsonl', requests), ('dependencies.jsonl', dependencies)):
            target.close()
            components[name] = target.info()
        probes.close()
    totals['U'] = len(objects)
    coverage = {**totals, 'expected_plans': len(views) * 3, 'by_method': dict(by_method),
        'by_view_method': dict(by_view_method), 'by_terminal': dict(by_terminal),
        'missing_plans': len(views) * 3 - totals['plans'], 'duplicate_plans': 0, 'missing_stages': int(bool(reasons)),
        'complete_input_tokens': None, 'actual_output_tokens': None, 'actual_generation_cost_microusd': None,
        'candidate_validation': 'failed' if totals['excess_plans'] else 'unknown_tokens_and_dynamic_admission',
        'complete': totals['plans'] == len(views) * 3 and not reasons, 'reasons': reasons}
    raw = encoded(coverage) + b'\n'
    if not recompute:
        (output / 'coverage.json').write_bytes(raw)
    components['coverage.json'] = {'bytes': len(raw), 'sha256': digest(raw)}
    for pid, info in objects.items():
        components['objects/' + pid + '.json'] = info
    catalog = {'schema_version': 'T0-request-catalog-0.1.0', 'scope': auth['scope'], 'base': BASE,
        'candidate': auth['candidate'], 'sources': auth['sources'], 'provenance': 'synthetic', 'script_version': SCRIPT,
        'composer_version': COMPOSER_VERSION, 'model_id': MODEL, 'mapper_version': 'openai-responses-mapper-0.1.0',
        'supplier_project_status': 'unbound', 'external_count_ready': False, 'project_id': 'UNBOUND-T0-DEV-CATALOG',
        'execution_budget': None, 'execution_authorized': False, 'budget_candidate': 'B02-A+B03',
        'acceptance_kind': 'declared_development_catalog_only' if development else 'public_synthetic_only',
        'complete': coverage['complete'], 'missing': coverage['missing_plans'], 'components': components}
    raw_catalog = encoded(catalog) + b'\n'
    if recompute:
        original = decode((output / 'catalog.json').read_bytes())
        changed = sorted(name for name in set(original['components']) | set(components)
            if original['components'].get(name) != components.get(name))
        match = digest((output / 'catalog.json').read_bytes()) == digest(raw_catalog)
        result = {'status': 'stable_content_reproduced' if match else 'stable_content_mismatch', 'match': match,
            'recomputed_catalog_sha256': digest(raw_catalog), 'recomputed_components': len(components),
            'recomputed_N': totals['N'], 'recomputed_U': totals['U'], 'changed_components': changed, 'selection_index_reused': True,
            'identity_key_read': False, 'second_catalog_written': False, 'provider_api_calls': {'count': 0, 'generate': 0, 'other': 0}}
        (output / 'checks/reproduction.json').write_bytes(encoded(result) + b'\n')
        return {**result, 'complete': match}
    (output / 'catalog.json').write_bytes(raw_catalog)
    return {'status': ('T0_A_catalog_prepared_only' if development else 'PUBLIC_synthetic_catalog_prepared_only') if coverage['complete'] else 'T0_A_incomplete',
        'complete': coverage['complete'], 'reasons': reasons, 'coverage': coverage, 'catalog_sha256': digest(raw_catalog),
        'actual_template_probes': probes.records, 'actual_template_dispatches': probes.operations,
        'actual_source_io': {v: source.setup for v, source in indexes.items()}}



def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare')
    prepare.add_argument('--authorization', required=True)
    prepare.add_argument('--output', required=True)
    prepare.add_argument('--recompute-digests', action='store_true', help='Recompute stable content without writing a second catalog')
    args = parser.parse_args(argv)
    try:
        output = _path(args.output)
    except (ValueError, OSError):
        print(json.dumps({'status': 'T0_A_incomplete', 'reasons': ['unsafe_output_path']}))
        return 2
    allowed = (PROJECT / 'data/ticket12-t0', PROJECT / '.tmp/ticket12-t0')
    if not any(output.is_relative_to(p) and output != p for p in allowed):
        print(json.dumps({'status': 'T0_A_incomplete', 'reasons': ['output_not_allowed']}))
        return 2
    if output.exists() and not args.recompute_digests:
        print(json.dumps({'status': 'T0_A_incomplete', 'reasons': ['output_already_exists']}))
        return 2
    if args.recompute_digests:
        if not (output / 'run.json').is_file() or not decode((output / 'run.json').read_bytes()).get('complete'):
            print(json.dumps({'status': 'T0_A_incomplete', 'reasons': ['complete_original_required']}))
            return 2
        if (output / 'checks/reproduction.json').exists() or (output / 'checks/probes-recompute.jsonl').exists():
            print(json.dumps({'status': 'T0_A_incomplete', 'reasons': ['reproduction_already_attempted']}))
            return 2
    else:
        output.mkdir(parents=True)
    try:
        report = _compile(_authorization(args.authorization), output, recompute=args.recompute_digests)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        reason = str(exc) if type(exc) is ValueError else type(exc).__name__
        report = {'status': 'T0_A_incomplete', 'complete': False, 'reasons': [reason]}
    report['provider_api_calls'] = {'count': 0, 'generate': 0, 'other': 0}
    report_path = output / ('checks/reproduction-failure.json' if args.recompute_digests else 'run.json')
    if not args.recompute_digests or not report.get('match'):
        report_path.write_text(json.dumps(report, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(report, sort_keys=True))
    return 0 if report['complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
