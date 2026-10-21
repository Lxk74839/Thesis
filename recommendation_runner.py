"""Host-owned bounded recommendation protocol on acquired facts, not an experiment CLI."""
import copy
import json
import math
import os
from pathlib import Path

from evidence_access import PROJECT, digest, encoded
from evidence_verification import assess_evidence, rank_acquired_quality
from quality_fusion import RULES

COMPOSER_VERSION = 'rsm-role-composer-0.1.0'


def compose_role_request(*, binding, state, acquired, initial_messages, quality, ordered,
                         role, kind, stage, output_cap, request_id, protocol, history=None):
    """Pure shared projection and message/schema composition; grants no execution capability."""
    from evidence_access import EvidenceSession
    from provider_openai import MODEL, role_output_schema
    batched = binding.get('orchestration') == 'batch32-0.1.0'
    queue = state['queue']
    def originals(pack):
        values = pack['originals'].values()
        return sorted(values, key=lambda o: (o['registration']['target_kind'],
            o['registration']['target_id'].encode('utf-8'), o['registration']['version'],
            o['evidence_ref'].encode('utf-8'))) if binding['execution_kind'] == 'on_demand_public' else values
    facts = {parent: [{'data': json.loads(o['raw_utf8']), 'citation': {
        'evidence_ref': o['evidence_ref'], 'receipt_id': o['receipt_id'],
        'target_id': o['registration']['target_id'], 'version': o['registration']['version'], 'pointer': '/'}}
        for o in originals(pack)] for parent, pack in acquired['candidates'].items()}
    context = {'stage': stage, 'method': binding['method'],
        'current': queue[state['cursor']] if state['cursor'] < len(queue) and state['stop_reason'] is None else None,
        'necessary_clauses': binding['necessary_clauses'], 'facts': facts,
        'history': json.loads(initial_messages[0]['content'])['H'] if initial_messages else [],
        'assessments': {p: {k: a[k] for k in ('assessment_status', 'evidence_state', 'eligible',
            'advance_allowed', 'completion', 'claims')} for p, a in state['assessments'].items()}, 'quality': quality,
        'ordered': ordered[:binding['K']], 'G': state['G'][:],
        'candidate_batches': dict(zip(binding['C'], binding['batches'])),
        'base_preferences': {p: {'value': b, 'citation': {
            'evidence_ref': 'safe-base:' + binding['base_score_sha256'],
            'receipt_id': 'input:' + state['input_projection_sha256'], 'target_id': p,
            'version': 1, 'pointer': '/base_score'}} for p, b in zip(binding['C'], binding['base_scores'])},
        'draft': state['drafts'][-1] if state['drafts'] else None, 'issues': state['visible_issues'],
        'forwards': [{'role': m['role'], 'role_message_id': m['role_message_id'],
            'content': m['response']['message']['content']} for m in state['messages']
            if m['response']['status'] == 'ok' and m['response']['message']['content'] is not None]}
    if batched:
        context.update(batch_limit=32, quality_arm=binding['arm'] == 'quality',
            profile_candidates=[p for batch in state['batches'][state.get('profile_batch_start', 0):] for p in batch['processed']],
            assessment_receipts={s['candidate_id']: s['receipt_id'] for batch in state['batches']
                for s in batch['steps'] if s['operation'] == 'assess_current' and s['status'] == 'ok'})
        latest = {}
        for message in state['messages']:
            if message['response']['status'] != 'ok' or message['response']['message']['content'] is None:
                continue
            request = message['request']
            frame = next(m['content']['runtime'] for m in reversed(request['messages'])
                         if m['role'] == 'user' and isinstance(m['content'], dict) and 'runtime' in m['content'])
            latest[(request['output_kind'], frame['stage'])] = {'role': message['role'], 'stage': frame['stage'],
                'role_message_id': message['role_message_id'], 'content': message['response']['message']['content']}
        context['forwards'] = list(latest.values())
    effective = '单智能体' if binding['method'] == 'S' else role
    messages = copy.deepcopy(history) if history is not None else [
        {'role': 'system', 'content': {'protocol': protocol, 'source_disclosure': 'SIM',
            'execution_kind': binding['execution_kind']}}, *copy.deepcopy(initial_messages)]
    messages.append({'role': 'user', 'content': {'runtime': context}})
    tools = EvidenceSession.tool_schemas(batch=batched) + [{'name': 'candidate_page', 'version': 'joint-page-0.1.0',
        'input_schema': {'type': 'object', 'properties': {'order': {'enum': ['parent', 'base']},
            'cursor': {'type': ['string', 'null']}}, 'required': ['order', 'cursor'], 'additionalProperties': False}}]
    tools = tools if kind == 'acquire' and queue else []
    return {'schema_version': 'rsm-model-prepare-0.1.0', 'execution_kind': binding['execution_kind'],
        'request_id': request_id, 'attempt_id': request_id, 'run_id': binding['run_id'],
        'session_id': binding['run_id'] + ':' + effective, 'role': effective,
        'reply_to': state['messages'][-1]['role_message_id'] if state['messages'] else None,
        'model_id': ('gpt-6-luna' if binding['execution_kind'] == 'fourrouter_responses' else
                     None if binding['execution_kind'] == 'on_demand_public' else MODEL), 'messages': messages, 'tools': tools, 'output_kind': kind,
        'output_schema': role_output_schema(effective, kind, messages), 'max_output_tokens': output_cap}


def pointer_value(value, pointer):
    if pointer == '/':
        return value
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ValueError('invalid_pointer')
    for part in pointer[1:].split('/'):
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) and part.isdecimal() else value[part]
    return value


def _draft_shape(draft):
    return (isinstance(draft, dict) and set(draft) == {'draft_id', 'parent_draft_id', 'items'}
        and isinstance(draft['draft_id'], str) and bool(draft['draft_id'])
        and (draft['parent_draft_id'] is None or isinstance(draft['parent_draft_id'], str))
        and isinstance(draft['items'], list))


class RunStop(Exception):
    def __init__(self, terminal, reason):
        self.terminal, self.reason = terminal, reason
        super().__init__(reason)


class RecommendationRun:
    version = 'rsm-runner-0.1.0'

    def __init__(self, binding, *, evidence, model, root_budget, output_root):
        self.binding = copy.deepcopy(binding)
        self.batched = binding.get('orchestration') == 'batch32-0.1.0'
        self.native_fixture = binding.get('execution_kind') == 'openai_native_fixture'
        self.fourrouter = binding.get('execution_kind') == 'fourrouter_responses'
        self.on_demand = binding.get('execution_kind') == 'on_demand_public'
        self.evidence, self.model, self.budget = evidence, model, root_budget
        self.output_root = Path(output_root).resolve()
        if self.output_root != root_budget.journal_path.parent or evidence.root_budget is not root_budget:
            raise ValueError('runtime_root_mismatch')
        self.queue = sorted(binding['C'], key=lambda p: (-binding['base_scores'][binding['C'].index(p)], p.encode()))
        self.state = {'run_id': binding['run_id'], 'binding': copy.deepcopy(binding), 'queue': self.queue[:],
            'cursor': 0, 'current_candidate': evidence.binding['parent_asin'], 'G': [], 'assessments': {}, 'drafts': [], 'issues': [], 'revisions': [],
            'messages': [], 'dispatches': [], 'feedback_round': 0, 'roles_completed': [],
            'visible_issues': [],
            'versions': {'baseline': '6ac5c2cddde6973b9743e3e17f5c264840f42854', 'runner': self.version,
                'adapter': 'rsm-model-adapter-0.1.0', 'tools': evidence.version, 'prompt': 'rsm-safe-prompt-0.1.0',
                'contract_sha256': '8982a92d8541f8bc52b31824924527abd66b87910cde4e13124abc27b90b6fa8',
                'implementation_candidate': binding.get('implementation_candidate', 'development_worktree')},
            'terminal': None, 'reason': None, 'stop_reason': None, 'delivered': [], 'components': None}
        if self.batched:
            self.state.update(batches=[], profiled_candidates=[])
            self.state['versions'].update(baseline='ac4874c7218ea1a795ddf992a9c23d133766a293',
                runner='rsm-runner-batch-0.1.0', adapter='rsm-model-adapter-batch-0.1.0',
                tools='restricted-evidence-batch-0.1.0', prompt='rsm-batch-safe-prompt-0.1.0',
                contract_sha256='2c2376c3965a5910b4b2a89b081a87b4f8634ecfd6c9907cdf727831eb5a838b')
        self.result = None
        if self.native_fixture or self.fourrouter:
            self.state['preparations'] = []
            self.state['versions'].update(baseline='023a6cc5b906541f01b56cfd805594719bfac557',
                runner='rsm-runner-native-fixture-0.1.0', adapter='rsm-model-adapter-native-0.1.0',
                prompt='rsm-native-fixture-prompt-0.1.0',
                contract_sha256='9cfd918e4b0e3e6316e2e0a62e6a42c8518c38ed990751448b2cbb215fcee08e')
            if self.model is not None and self.model.root_budget is None:
                self.model.root_budget = root_budget
        if self.on_demand:
            self.state['preparations'] = []
            self.state['versions'].update(runner='rsm-runner-on-demand-fixture-0.1.0',
                adapter='rsm-model-adapter-on-demand-fixture-0.1.0')
        if self.fourrouter:
            self.state['versions'].update(baseline='1d688a3ddee04f634773ad62204a69f45fd55f19',
                runner='rsm-runner-4router-0.1.0', adapter='rsm-model-adapter-4router-0.1.0', prompt=COMPOSER_VERSION)
        self.histories = {}
        self.call_ids = set()
        self.profile_batch_start = 0
        self.initial_messages = copy.deepcopy(evidence.joint.dispatch('model_request', {})['request']['messages']
            if evidence.joint is not None else binding.get('safe_initial_messages', []))
        if binding.get('assembled_input_sha256'):
            self.initial_messages = copy.deepcopy(binding['safe_initial_messages'])
        for message in self.initial_messages:
            payload = json.loads(message['content'])
            payload['verify_at_ms'] = binding['verify_at_ms']
            payload.pop('input_fingerprint')
            payload['input_fingerprint'] = digest(encoded(payload))
            message['content'] = encoded(payload).decode()
        self.state['input_projection_sha256'] = digest(encoded(self.initial_messages))

    def _preflight(self):
        b = self.binding
        execution_scope = (b['fixture'] == 'public_runtime_adapter'
                           and b['execution_budget'] is None and b['execution_authorized'] is False)
        if self.fourrouter and b.get('fixture') is None:
            from p1_runtime import D1, PILOT_ID, TASK_KEYS
            execution_scope = (b['plan_source_scope'] == 'development_pilot' and b['root_task_id'] == D1
                and b.get('pilot_id') == PILOT_ID and b.get('task_key') == TASK_KEYS.get(b['method'])
                and b['execution_authorized'] is True and b['execution_budget'] == self.budget.limits)
        valid = (b == self.budget.binding and b['schema_version'] == ('rsm-run-0.4.0' if self.fourrouter else 'rsm-run-0.3.0' if self.on_demand else 'rsm-run-0.2.0' if self.native_fixture else 'rsm-run-0.1.0')
            and b['execution_kind'] in ('scripted_public', 'openai_native_fixture', 'on_demand_public', 'fourrouter_responses') and execution_scope
            and b['method'] in ('R', 'S', 'M') and b['arm'] in ('necessary', 'quality')
            and type(b['K']) is int and b['K'] == 10 and b['necessary_clauses'] == ['c1', 'c2']
            and len(b['C']) == len(set(b['C'])) == len(b['base_scores']) == len(b['batches'])
            and all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in b['base_scores'])
            and b['C_sha256'] == digest(encoded(b['C']))
            and b['base_score_sha256'] == digest(encoded(list(zip(b['C'], b['base_scores'])))))
        for message in self.initial_messages:
            payload = json.loads(message['content'])
            valid = (valid and payload['root_task_id'] == b['root_task_id']
                and payload['H_sha256'] == b['H_sha256'] == digest(encoded(payload['H']))
                and [clause['clause_id'] if isinstance(clause, dict) else clause
                     for clause in payload['request']['necessary_clauses']] == b['necessary_clauses'])
        source = Path(self.evidence.source.snapshot_ref['path']).resolve()
        if b.get('assembled_input_sha256'):
            valid = (valid and self.state['input_projection_sha256'] == b['assembled_input_sha256']
                and b['source_snapshot_ref'] == self.evidence.source.snapshot_ref)
        if self.on_demand:
            valid = (valid and b.get('plan_source_scope') == 'public_fixture'
                and b['root_task_id'].startswith('PUBLIC-')
                and source.is_relative_to(PROJECT / '.tmp/recommendation-runtime'))
        if self.fourrouter and b['fixture'] == 'public_runtime_adapter':
            valid = (valid and b['root_task_id'].startswith('PUBLIC-')
                and source.is_relative_to(PROJECT / '.tmp/recommendation-runtime')
                and (self.model is None or self.model.binding.get('provenance') == 'fixture'))
        source_error = None
        if self.fourrouter and b.get('fixture') is None:
            from p1_runtime import frozen_snapshot_error
            source_error = frozen_snapshot_error(b, self.evidence.source.snapshot_ref)
            valid = valid and source_error is None
        else:
            valid = valid and any(source.is_relative_to(PROJECT / p) for p in
                                  ('.tmp/recommendation-runtime', 'data/recommendation-runtime-audit'))
        if b['C']:
            joint = self.evidence.joint
            valid = valid and joint is not None and (joint.candidates['C'], joint.candidates['b'], joint.candidates['batches']) == (b['C'], b['base_scores'], b['batches'])
            valid = valid and self.evidence.binding['parent_asin'] == self.queue[0]
        elif b['method'] != 'R':
            valid = valid and isinstance(b.get('safe_initial_messages'), list) and bool(b['safe_initial_messages'])
        if b['arm'] == 'quality':
            valid = valid and type(b['prefix_limit']) is int and b['prefix_limit'] > 0 and isinstance(b['fusion'], dict)
            fusion = b['fusion'] if isinstance(b['fusion'], dict) else {}
            valid = (valid and set(fusion) == {'schema_version', 'task_id', 'C', 'C_sha256', 'H_sha256', 'base_scores',
                'base_score_version', 'base_score_sha256', 'snapshot_id', 'verify_at_ms', 'principal_id',
                'contract_sha256', 'K', 'alpha', 'beta', 'mode', 'preference'}
                and fusion.get('schema_version') == 'fusion-binding-0.1.0'
                and fusion.get('contract_sha256') == digest(encoded(RULES))
                and isinstance(fusion.get('base_score_version'), str) and bool(fusion['base_score_version'])
                and fusion.get('alpha') == .5 and fusion.get('beta') == [.25, .5, .25]
                and fusion.get('mode') == 'full' and fusion.get('task_id') == b['root_task_id']
                and fusion.get('preference') == {'source': 'experiment_design', 'dimensions': ['retail_stock'],
                                                'weights': {'retail_stock': 1}}
                and all(fusion.get(k) == b[k] for k in ('C', 'C_sha256', 'H_sha256', 'base_scores',
                    'base_score_sha256', 'snapshot_id', 'verify_at_ms', 'principal_id', 'K')))
        if b['method'] == 'R':
            valid = valid and all(self.budget.limits[k] == self.budget.final_reserve[k] == 0 for k in
                                  ('model_calls', 'input_tokens', 'output_tokens', 'cost_microusd'))
        else:
            valid = valid and self.model is not None
            if self.native_fixture or self.fourrouter:
                valid = (valid and self.batched and self.model.binding.get('project_id') == b.get('project_id')
                    and self.model.binding.get('execution_kind') == ('fourrouter_responses' if self.fourrouter else 'openai_native_fixture')
                    and self.model.root_budget is self.budget and (self.model.counter is not None
                        or self._S_engineering()))
                if self.fourrouter and b.get('fixture') is None:
                    valid = (valid and self.model.binding.get('provenance') == '4router'
                             and self.model.binding.get('execution_authorized') is True)
            if self.on_demand:
                valid = (valid and self.model.binding.get('execution_kind') == 'on_demand_public'
                    and self.model.binding.get('model_id') is None and self.model.counter is not None)
        if not valid:
            raise RunStop('failed_protocol', source_error or 'runtime_preflight_failed')

    def _S_engineering(self):
        from p1_engineering import SEngineeringBudget, authorized
        return type(self.budget) is SEngineeringBudget and self.model is not None and authorized(self.model.binding)

    def _check_tool(self, result):
        if result['status'] == 'ok':
            return result
        reason = result['status']
        terminal = {'budget_exhausted': 'incomplete_budget', 'deadline_exceeded': 'incomplete_deadline',
                    'source_integrity_error': 'failed_source'}.get(reason, 'failed_protocol')
        raise RunStop(terminal, reason)

    def _program(self, operation, callback, *, phase='work', logical=1):
        elapsed_upper = 45000
        if self.batched and phase == 'final':
            remaining = max(0, self.budget.limits['elapsed_ms'] - math.ceil(self.budget.clock() - self.budget.started))
            elapsed_upper = min(elapsed_upper, remaining // {'final': 3, 'commit': 2, 'seal_audit': 1}[operation])
        elif self.batched:
            elapsed_upper = min(elapsed_upper, max(0, self.budget.limits['elapsed_ms']
                - math.ceil(self.budget.clock() - self.budget.started) - self.budget.final_reserve['elapsed_ms']))
        reservation = self.budget.reserve(operation, {'logical_tools': logical, 'elapsed_ms': elapsed_upper}, phase=phase, retry_of=None)
        self._check_tool(reservation if reservation['status'] != 'reserved' else {'status': 'ok'})
        started = self.budget.clock()
        try:
            result = callback()
        except Exception:
            self.budget.settle(reservation['reservation_id'], {'status': 'failed', 'usage': {'logical_tools': logical}})
            raise
        self.budget.settle(reservation['reservation_id'], {'status': 'ok', 'usage': {'logical_tools': logical},
                                                       'late': self.budget.clock() - started > elapsed_upper})
        if self.budget.halted:
            self._check_tool({'status': self.budget.halted})
        return result

    def _rule_acquire(self):
        entries, cursor = [], None
        while True:
            result = self._check_tool(self.evidence.dispatch('list_evidence', {'cursor': cursor}, actor_role='host'))
            entries.extend(result['entries'])
            cursor = result['next_cursor']
            if cursor is None:
                break
        entries.sort(key=lambda r: (r['target_kind'], r['target_id'].encode(), r['version']))
        for offset in range(0, len(entries), 32):
            self._check_tool(self.evidence.dispatch('read_evidence',
                {'evidence_refs': [r['evidence_ref'] for r in entries[offset:offset + 32]]}, actor_role='host'))

    def _order(self):
        if self.binding['arm'] == 'quality' and self.state['G']:
            return self._rank('full')['order']
        return [p for p in self.queue if p in self.state['G']]

    def _rank(self, mode):
        if not self.queue:
            return {'order': [], 'topK': [], 'candidates': [], 'G': [], 'raw_eligible': [],
                    'mean_quality': {'value': 0, 'denominator': 0, 'reason': 'no_supported_candidates'}}
        try:
            result = rank_acquired_quality({**self.binding['fusion'], 'mode': mode}, self.evidence.audit_view()['acquired'])
        except ValueError as exc:
            raise RunStop('failed_protocol', str(exc)) from None
        if set(result['G']) != set(self.state['G']):
            raise RunStop('failed_protocol', 'quality_actual_G_mismatch')
        return result

    def _components(self):
        acquired = self.evidence.audit_view()['acquired']
        anchor = {'run_id': self.binding['run_id'], 'root_task_id': self.binding['root_task_id'],
            'snapshot_id': self.binding['snapshot_id'], 'A_sha256': digest(encoded(acquired)),
            'G': self.state['G'][:], 'C_sha256': self.binding['C_sha256'],
            'base_score_sha256': self.binding['base_score_sha256'], 'cursor': self.state['cursor'],
            'stop_reason': self.state['stop_reason'], 'terminal': self.state['terminal'],
            'H_sha256': self.binding['H_sha256'], 'repeat_id': self.binding['repeat_id'],
            'fusion_sha256': digest(encoded(self.binding['fusion'])),
            'publication_record_sha256': self.state.get('publication_record_sha256'),
            'original_terminal': self.state.get('anchor_original_terminal', self.state['terminal']),
            'anchor_consistency': self.state.get('anchor_consistency', 'not_applicable'),
            'execution_kind': self.binding['execution_kind'],
            'anchor_kind': '4router_responses' if self.fourrouter else 'native_provider_fixture' if self.native_fixture else 'scripted_protocol_fixture'}
        failed = self.state['terminal'] not in ('released', 'valid_empty')
        components = {}
        for mode in ('full', 'no_quality', 'mean_quality'):
            replay = {'order': [], 'topK': [], 'candidates': []} if failed else self._rank(mode)
            components[mode] = {**replay, 'anchor': copy.deepcopy(anchor), 'anchor_sha256': digest(encoded(anchor)),
                'status': 'anchor_failed' if failed else 'computed',
                'failure_rule': 'F1_zero_if_reference_applicable' if failed else None}
        if not failed and components['full']['topK'] != self.state['delivered']:
            self.state['anchor_original_terminal'] = self.state['terminal']
            self.state['anchor_consistency'] = 'failed'
            raise RunStop('failed_protocol', 'full_publication_mismatch')
        return components

    def _composed(self, role, kind, stage, *, history=None):
        quality = ({r['parent_asin']: {k: r[k] for k in ('z', 'm', 'q', 'stock_state')}
                    for r in self._rank('full')['candidates']} if self.binding['arm'] == 'quality' and self.state['assessments'] else {})
        return compose_role_request(binding=self.binding,
            state={**self.state, 'profile_batch_start': self.profile_batch_start},
            acquired=self.evidence.audit_view()['acquired'], initial_messages=self.initial_messages,
            quality=quality, ordered=self._order(), role=role, kind=kind, stage=stage,
            output_cap=1500 if kind == 'final_submit' else 8192,
            request_id=self.binding['run_id'] + ':message:' + str(len(self.state['messages'])),
            protocol=self.state['versions']['runner'] if self.native_fixture or self.fourrouter else self.version, history=history)

    def _context(self, stage):
        return self._composed('需求解析', 'analysis', stage)['messages'][-1]['content']['runtime']

    def _base_preference(self, parent):
        return {'value': self.binding['base_scores'][self.binding['C'].index(parent)], 'citation': {
            'evidence_ref': 'safe-base:' + self.binding['base_score_sha256'],
            'receipt_id': 'input:' + self.state['input_projection_sha256'], 'target_id': parent,
            'version': 1, 'pointer': '/base_score'}}

    def _analysis(self, role):
        data = self._role(role, 'analysis', role)
        if (set(data) != {'necessary_clauses', 'observations'} or data['necessary_clauses'] != self.binding['necessary_clauses']
                or not isinstance(data['observations'], list)):
            raise RunStop('failed_protocol', 'changed_request')
        if role == '需求解析':
            self._complete(role)
            return
        context = self._context(role)
        observations = data['observations']
        try:
            if not observations:
                raise ValueError('missing_profile')
            if role == '用户画像':
                for item in observations:
                    if (set(item) != {'pointer', 'value', 'preference_status'} or not isinstance(item['pointer'], str)
                            or not (item['pointer'] == '/H' or item['pointer'].startswith('/H/'))
                            or item['preference_status'] not in ('unknown', 'history_fact')
                            or encoded(pointer_value({'H': context['history']}, item['pointer'])) != encoded(item['value'])):
                        raise ValueError('unbound_history')
                self._complete(role)
                return
            batch_profile = self.batched and bool(self.queue)
            parents = context['profile_candidates'] if batch_profile else [context['current']]
            if len(observations) != len(parents):
                raise ValueError('missing_candidate_profile')
            for current, item in zip(parents, observations):
                assessment, quality = context['assessments'].get(current), context['quality'].get(current)
                unknown = (['empty_C'] if current is None else [c for c, v in assessment['claims'].items()
                    if v['evidence_state'] != 'Supported'] + (['retail_stock'] if quality and not quality['z'] else []))
                assessment_key = 'assessment_receipt_id' if batch_profile else 'assessment'
                assessment_value = context['assessment_receipts'][current] if batch_profile else assessment
                if (set(item) != {'candidate_id', assessment_key, 'quality', 'attributes', 'unknown'}
                        or item['candidate_id'] != current or encoded(item[assessment_key]) != encoded(assessment_value)
                        or encoded(item['quality']) != encoded(quality)
                        or item['unknown'] != unknown or not isinstance(item['attributes'], list)):
                    raise ValueError('unbound_product_profile')
                facts = context['facts'].get(current, [])
                attributes = {'conclusion': 'inspection_report', 'status': 'retail_status', 'stock_units': 'retail_status'}
                expected = {(f['citation']['evidence_ref'], key) for f in facts for key, kind in attributes.items()
                            if f['data'].get('kind') == kind and key in f['data']['facts']}
                seen = set()
                for attribute in item['attributes']:
                    if set(attribute) != {'attribute', 'value', 'unit', 'citation'}:
                        raise ValueError('invalid_attribute')
                    key, citation = attribute['attribute'], attribute['citation']
                    fact = next(f for f in facts if f['citation']['evidence_ref'] == citation['evidence_ref'])
                    pair = (citation['evidence_ref'], key)
                    if (pair not in expected or pair in seen or encoded(citation) != encoded({**fact['citation'], 'pointer': '/facts/' + key})
                            or encoded(attribute['value']) != encoded(fact['data']['facts'][key])
                            or attribute['unit'] != (fact['data']['facts'].get('unit') if key == 'stock_units' else None)):
                        raise ValueError('invalid_attribute_binding')
                    seen.add(pair)
                if seen != expected:
                    raise ValueError('missing_attributes')
            if batch_profile:
                self.state['profiled_candidates'].extend(parents)
            self._complete(role)
        except (ValueError, KeyError, TypeError, IndexError, StopIteration):
            raise RunStop('failed_protocol', 'invalid_profile') from None

    def _complete(self, role):
        role = '单智能体' if self.binding['method'] == 'S' else role
        if role not in self.state['roles_completed']:
            self.state['roles_completed'].append(role)

    def _invoke(self, role, kind, messages, tools):
        retry_of = None
        while True:
            number = len(self.state['messages'])
            message_id = self.binding['run_id'] + ':message:' + str(number)
            engineering = self._S_engineering()
            input_upper = None if engineering else len(encoded({'messages': messages, 'tools': tools}))
            backoff = (1000, 2000)[min(self.budget.usage['retries'], 1)] if retry_of else 0
            elapsed_upper = 45000 + backoff
            if engineering:
                from p1_engineering import http_window_ms
                elapsed_upper = http_window_ms(self.model.binding) + 15000
            if self.batched:
                remaining = self.budget.limits['elapsed_ms'] - math.ceil(self.budget.clock() - self.budget.started)
                if kind != 'final_submit':
                    remaining -= self.budget.final_reserve['elapsed_ms']
                elapsed_upper = max(backoff + 1, min(elapsed_upper, remaining))
            native = None
            prepared, count = None, None
            output_cap, cost_upper = 100000, 0
            if self.on_demand:
                from provider_openai import role_output_schema
                logical = {'schema_version': 'rsm-model-prepare-0.1.0', 'execution_kind': 'on_demand_public',
                    'request_id': message_id, 'attempt_id': message_id, 'run_id': self.binding['run_id'],
                    'session_id': self.binding['run_id'] + ':' + role, 'role': role,
                    'reply_to': self.state['messages'][-1]['role_message_id'] if self.state['messages'] else None,
                    'model_id': None, 'messages': copy.deepcopy(messages), 'tools': copy.deepcopy(tools),
                    'output_kind': kind, 'output_schema': role_output_schema(role, kind, messages),
                    'max_output_tokens': output_cap}
                prepared = self.model.prepare(logical)
                if prepared['status'] != 'prepared':
                    raise RunStop('failed_protocol', 'on_demand_prepare_failed')
                count = self.model.counter.count(prepared, authorization=None)
                if count['status'] != 'counted' or count['basis'] != 'fixture':
                    raise RunStop('incomplete_count', count['status'])
                input_upper = count['input_tokens']
            if self.native_fixture or self.fourrouter:
                if self.fourrouter:
                    from provider_fourrouter import MODEL, contract_missing, upper_cost as cost_microusd, role_output_schema
                    missing = contract_missing(self.model.binding, self.model.counter)
                    if missing:
                        raise RunStop('not_started', ','.join(missing))
                else:
                    from provider_openai import MODEL, cost_microusd, role_output_schema
                available = self.budget.audit_view()
                output_resource = 'request_output_tokens' if engineering else 'output_tokens'
                output_left = available['limits'][output_resource] - available['usage'][output_resource] - available['held'][output_resource]
                if kind != 'final_submit':
                    output_left -= available['final_reserve'][output_resource]
                output_cap = min(1500 if kind == 'final_submit' else 8192, output_left)
                if self.fourrouter:
                    output_cap = min(output_cap, self.model.binding['max_output_tokens'])
                if output_cap <= 0:
                    raise RunStop('incomplete_budget', 'output_capacity_exhausted')
                native = {'schema_version': 'rsm-model-request-0.3.0', 'execution_kind': self.binding['execution_kind'],
                    'request_id': message_id, 'attempt_id': message_id, 'run_id': self.binding['run_id'],
                    'session_id': self.binding['run_id'] + ':' + role, 'role': role,
                    'reply_to': self.state['messages'][-1]['role_message_id'] if self.state['messages'] else None,
                    'model_id': MODEL, 'messages': copy.deepcopy(messages), 'tools': copy.deepcopy(tools), 'output_kind': kind,
                    'output_schema': role_output_schema(role, kind, messages), 'max_output_tokens': output_cap,
                    'input_token_upper_bound': None if engineering else 0, 'deadline_ms': int(self.budget.clock() + elapsed_upper), 'reservation_id': 'unreserved'}
                prepared = self.model.prepare(native)
                if prepared['status'] != 'prepared':
                    raise RunStop('failed_protocol', 'native_prepare_failed')
                if self.fourrouter and prepared.get('missing'):
                    raise RunStop('not_started', ','.join(prepared['missing']))
                if engineering:
                    from provider_fourrouter import prepared_diagnostic
                    self.state['preparations'].append({'prepared': prepared_diagnostic(prepared), 'count': None,
                        'count_reason': 'single_S_authorization_waiver'})
                else:
                    count = self.model.counter.count(prepared, authorization=None)
                    if self.fourrouter:
                        from provider_fourrouter import prepared_diagnostic
                    self.state['preparations'].append({'prepared': prepared_diagnostic(prepared) if self.fourrouter else prepared,
                        'count': count})
                    if count['status'] != 'counted' or count['basis'] != (
                            'verified_full_input' if self.fourrouter and self.model.binding.get('provenance') != 'fixture' else 'fixture'):
                        raise RunStop('incomplete_count', count['status'])
                    input_upper = count['input_tokens']
                    cost_upper = (cost_microusd(input_upper, output_cap, pricing=self.model.binding['pricing'])
                                  if self.fourrouter else cost_microusd(input_upper, output_cap))
                native.update(prepared_id=prepared['prepared_id'], count_receipt_id=None if engineering else count['receipt_id'])
            intent = {'kind': 'model', 'role': role, 'request_id': message_id,
                      'messages': copy.deepcopy(messages), 'tools': copy.deepcopy(tools), 'output_kind': kind}
            if self.on_demand:
                intent = {'kind': 'model', 'role': role, 'request_id': message_id, 'output_kind': kind,
                          'prepared_id': prepared['prepared_id'], 'count_receipt_id': count['receipt_id']}
            if native is not None:
                intent.update(prepared_id=prepared['prepared_id'], wire_sha256=prepared['wire_sha256'], count_receipt_id=None if engineering else count['receipt_id'])
            reservation = self.budget.reserve(intent,
                ({'model_calls': 1, 'request_output_tokens': output_cap, 'elapsed_ms': elapsed_upper} if engineering else
                 {'model_calls': 1, 'input_tokens': input_upper, 'output_tokens': output_cap,
                  'cost_microusd': cost_upper, 'elapsed_ms': elapsed_upper}),
                phase='final' if kind == 'final_submit' else 'work', retry_of=retry_of)
            self._check_tool(reservation if reservation['status'] != 'reserved' else {'status': 'ok'})
            started = self.budget.clock()
            if backoff:
                self.evidence.sleeper(backoff / 1000)
            request = {'schema_version': 'rsm-model-request-0.2.0' if self.batched else 'rsm-model-request-0.1.0',
                'execution_kind': self.binding['execution_kind'],
                'request_id': message_id, 'attempt_id': message_id, 'run_id': self.binding['run_id'],
                'session_id': self.binding['run_id'] + ':' + role, 'role': role,
                'reply_to': self.state['messages'][-1]['role_message_id'] if self.state['messages'] else None,
                'model_id': None, 'messages': copy.deepcopy(messages), 'tools': tools, 'output_kind': kind,
                'max_output_tokens': 100000, 'input_token_upper_bound': input_upper,
                'deadline_ms': int(started + elapsed_upper), 'reservation_id': reservation['reservation_id']}
            if native is not None:
                request = {**native, 'input_token_upper_bound': input_upper,
                    'deadline_ms': int(started + elapsed_upper), 'reservation_id': reservation['reservation_id']}
                if engineering:
                    from p1_engineering import reservation_deadline, http_window_ms
                    request['deadline_ms'] = int(min(started + http_window_ms(self.model.binding),
                        reservation_deadline(self.budget, reservation['reservation_id'])))
            if self.on_demand:
                request.update(prepared_id=prepared['prepared_id'], count_receipt_id=count['receipt_id'])
                request['output_schema'] = copy.deepcopy(logical['output_schema'])
                request_ref = self._trace_ref('request', request)
                self.state['preparations'].append({'prepared_id': prepared['prepared_id'],
                    'count': count, 'request_ref': request_ref})
            response = self.model.invoke(request)
            if self.on_demand:
                response_ref = self._trace_ref('response', response['raw_response'])
            late = self.budget.clock() > request['deadline_ms']
            usage = {k: response['usage'].get(k) for k in ('input_tokens', 'output_tokens', 'cost_microusd')}
            if (self.native_fixture or self.fourrouter or self.on_demand) and response['status'] == 'usage_mismatch':
                # Keep the conflicting provider usage in the response and the root reservation unresolved.
                usage = dict.fromkeys(usage)
            usage['model_calls'] = int(response['attempted'])
            observation = {'status': response['status'], 'usage': usage, 'late': late,
                'request': copy.deepcopy(request), 'response': copy.deepcopy(response)}
            if self.on_demand:
                observation = {'status': response['status'], 'usage': usage, 'late': late,
                    'request_ref': request_ref, 'response_ref': response_ref}
            self.budget.settle(reservation['reservation_id'], observation)
            self.state['messages'].append({'role_message_id': message_id, 'role': role, 'request': request,
                'response': copy.deepcopy(response), 'root_reservation_id': reservation['reservation_id'],
                'provenance': response['provenance'], 'usage_basis': response['usage_basis']})
            if self.on_demand:
                self.state['messages'][-1].update(request_ref=request_ref, response_ref=response_ref)
            if self.budget.halted or late:
                raise RunStop('incomplete_deadline' if late or self.budget.halted == 'deadline_exceeded' else 'failed_model',
                              self.budget.halted or 'deadline_exceeded')
            if response['status'] == 'ok':
                return response['message']
            if not response.get('error', {}).get('retryable') or not response.get('usage_known'):
                raise RunStop('failed_model', response['status'])
            retry_of = reservation['reservation_id']
            messages.append({'role': 'user', 'content': {'retry_of': message_id, 'error': response['error']['category']}})

    def _role(self, role, kind, stage):
        role = '单智能体' if self.binding['method'] == 'S' else role
        composed = self._composed(role, kind, stage,
            history=None if self.batched else self.histories.get(role))
        history, tools = composed['messages'], composed['tools']
        self.histories[role] = history
        while True:
            message = self._invoke(role, kind, history, tools if kind == 'acquire' and self.queue else [])
            history.append(copy.deepcopy(message))
            calls = message['tool_requests']
            if not calls:
                return copy.deepcopy(message['content']['data'])
            for call in calls:
                if call['call_id'] in self.call_ids:
                    raise RunStop('failed_protocol', 'reused_tool_call_id')
                self.call_ids.add(call['call_id'])
                if self.batched and call['name'] == 'acquire_batch':
                    used = sum(len(b['processed']) for b in self.state['batches'][self.profile_batch_start:])
                    if call['arguments']['candidate_limit'] > 32 - used:
                        raise RunStop('failed_protocol', 'batch_dispatch_exhausted')
                result = self.evidence.dispatch(call['name'], call['arguments'], actor_role=role)
                if self.batched and call['name'] == 'acquire_batch' and 'processed' in result:
                    self.state['batches'].append({k: copy.deepcopy(result[k]) for k in
                        ('plan_sha256', 'processed', 'steps', 'stop_reason', 'status')})
                    self.state['batches'][-1].update(role_message_id=self.state['messages'][-1]['role_message_id'],
                                                  tool_call_id=call['call_id'])
                    self.state['assessments'].update(result['assessments'])
                    self.state['G'] = [p for p in self.queue if self.state['assessments'].get(p, {}).get('eligible')]
                    self.state['cursor'] += len(result['processed'])
                    self.state['current_candidate'] = self.evidence.binding['parent_asin']
                    if result['stop_reason'] != 'batch_limit':
                        self.state['stop_reason'] = result['stop_reason']
                if result['status'] not in ('ok', 'io_error', 'access_denied', 'invalid_request') or self.budget.halted:
                    self._check_tool(result)
                history.append({'role': 'tool', 'tool_call_id': call['call_id'], 'content': result})

    def _model_acquire(self):
        manager = self._role('推荐管理', 'dispatch', 'dispatch')
        target = '单智能体' if self.binding['method'] == 'S' else '生命周期追溯'
        batch_dispatch = self.batched and bool(self.queue)
        if (set(manager) != {'candidate', 'to', 'claim_ids'} | ({'candidate_limit'} if batch_dispatch else set())
                or batch_dispatch and (type(manager['candidate_limit']) is not int or manager['candidate_limit'] != 32)
                or manager['to'] != target
                or manager['candidate'] != (self.queue[self.state['cursor']] if self.queue else None)
                or manager['claim_ids'] != self.binding['necessary_clauses']):
            raise RunStop('failed_protocol', 'invalid_dispatch')
        self.state['dispatches'].append({'from': '单智能体' if self.binding['method'] == 'S' else '推荐管理',
            'role_message_id': self.state['messages'][-1]['role_message_id'], **copy.deepcopy(manager)})
        self._complete('推荐管理')
        batch_start = len(self.state['batches']) if self.batched else 0
        self.profile_batch_start = batch_start
        trace = self._role('生命周期追溯', 'acquire', 'acquire')
        expected = {'done': True}
        if self.batched and self.queue:
            batches = self.state['batches'][batch_start:]
            if not batches:
                raise RunStop('failed_protocol', 'missing_batch_acquisition')
            expected.update(plan_sha256=batches[-1]['plan_sha256'], processed=[p for b in batches for p in b['processed']])
        if trace != expected:
            raise RunStop('failed_protocol', 'invalid_trace_completion')
        self._complete('生命周期追溯')

    def _rule_draft(self):
        items = []
        acquired = self.evidence.audit_view()['acquired']
        for parent in self._order()[:self.binding['K']]:
            citations = [{k: c[k] for k in ('evidence_ref', 'receipt_id', 'target_id', 'version', 'pointer')}
                         for c in acquired['assessments'][parent]['accepted']]
            reasons = [{'claim_id': 'c1', 'kind': 'inspection_supported', 'value': True, 'unit': None,
                        'text': '检验必要条件有完整有效支持（SIM）。', 'citations': citations},
                       {'claim_id': 'c2', 'kind': 'on_sale_supported', 'value': True, 'unit': None,
                        'text': '核验时点的在售必要条件有完整有效支持（SIM）。', 'citations': citations}]
            items.append({'parent_asin': parent, 'sim_batch_id': self.binding['batches'][self.binding['C'].index(parent)],
                          'reasons': reasons})
        return {'draft_id': self.binding['run_id'] + ':d0', 'parent_draft_id': None, 'items': items}

    def _issue(self, draft, pointer, code, parent=None, claim=None):
        return {'issue_id': str(draft.get('draft_id')) + ':' + code + ':' + pointer,
            'draft_id': draft.get('draft_id'), 'candidate_id': parent, 'claim_id': claim, 'pointer': pointer,
            'code': code, 'blocking': True, 'allowed_actions': ['revise_and_resubmit'],
            'verifier': 'program', 'source_receipts': [r['receipt_id'] for r in self.evidence.audit_view()['receipts']]}

    def _draft_issues(self, draft):
        issues = []
        acquired = self.evidence.audit_view()['acquired']
        if not _draft_shape(draft):
            return [self._issue(draft if isinstance(draft, dict) else {}, '/', 'invalid_draft')]
        identifiers = [i.get('parent_asin') if isinstance(i, dict) else None for i in draft['items']]
        if identifiers != self._order()[:self.binding['K']] or len(identifiers) > self.binding['K']:
            issues.append(self._issue(draft, '/items', 'invalid_order_or_count'))
        for index, item in enumerate(draft['items']):
            if (not isinstance(item, dict) or set(item) != {'parent_asin', 'sim_batch_id', 'reasons'}
                    or not isinstance(item['parent_asin'], str) or not isinstance(item['reasons'], list)):
                issues.append(self._issue(draft, '/items/' + str(index), 'invalid_item'))
                continue
            parent = item['parent_asin']
            if parent not in self.state['G'] or parent not in self.binding['C']:
                issues.append(self._issue(draft, '/items/' + str(index), 'outside_actual_G', parent))
                continue
            batch = self.binding['batches'][self.binding['C'].index(parent)]
            if item['sim_batch_id'] != batch:
                issues.append(self._issue(draft, '/items/%d/sim_batch_id' % index, 'wrong_batch', parent))
            proof = assess_evidence({**self.evidence.binding, 'parent_asin': parent, 'sim_batch_id': batch}, acquired)
            if not proof['eligible'] or not proof['advance_allowed']:
                issues.append(self._issue(draft, '/items/' + str(index), 'qualification_changed', parent))
            accepted = {r['evidence_ref'] for r in proof['accepted']}
            originals = acquired['candidates'].get(parent, {}).get('originals', {})
            kinds = [r.get('kind') if isinstance(r, dict) else None for r in item['reasons']]
            if (not {'inspection_supported', 'on_sale_supported'} <= set(k for k in kinds if isinstance(k, str))
                    or len(set(k for k in kinds if isinstance(k, str))) != len(kinds)):
                issues.append(self._issue(draft, '/items/%d/reasons' % index, 'missing_or_duplicate_reason', parent))
            for offset, reason in enumerate(item['reasons']):
                values = []
                pointer = '/items/%d/reasons/%d/citations' % (index, offset)
                if (not isinstance(reason, dict) or set(reason) != {'claim_id', 'kind', 'value', 'unit', 'text', 'citations'}
                        or not isinstance(reason['citations'], list) or not isinstance(reason['kind'], str)
                        or not isinstance(reason['claim_id'], str)):
                    issues.append(self._issue(draft, '/items/%d/reasons/%d' % (index, offset), 'invalid_reason', parent))
                    continue
                if reason['kind'] == 'base_preference':
                    base = self._base_preference(parent)
                    if (reason['claim_id'] != 'base_preference' or type(reason['value']) not in (int, float)
                            or reason['value'] != base['value'] or reason['unit'] is not None
                            or reason['text'] != '偏好基础分为%.12f。' % base['value']
                            or reason['citations'] != [base['citation']]
                            or type(reason['citations'][0]['version']) is not int):
                        issues.append(self._issue(draft, '/items/%d/reasons/%d' % (index, offset),
                                                  'invalid_base_preference', parent, reason['claim_id']))
                    continue
                templates = {'inspection_supported': ('c1', '检验必要条件有完整有效支持（SIM）。'),
                             'on_sale_supported': ('c2', '核验时点的在售必要条件有完整有效支持（SIM）。')}
                template = templates.get(reason['kind']) if isinstance(reason['kind'], str) else None
                stock = reason['kind'] == 'retail_stock'
                stock_support = (next((r for r in self._rank('full')['candidates'] if r['parent_asin'] == parent), {})
                                 if stock and self.binding['arm'] == 'quality' else {})
                valid = (reason['claim_id'] == 'retail_stock' and self.binding['arm'] == 'quality'
                    and stock_support.get('z') == 1 and stock_support.get('stock_state') == 'Supported'
                    and type(reason['value']) is int and reason['value'] >= 0 and reason['unit'] == 'units'
                    and reason['text'] == '可售库存为%d单位（SIM）。' % reason['value']) if stock else (
                    template is not None and reason['claim_id'] == template[0] and reason['value'] is True
                    and reason['unit'] is None and reason['text'] == template[1])
                if not valid:
                    issues.append(self._issue(draft, '/items/%d/reasons/%d' % (index, offset), 'unsupported_reason', parent, reason['claim_id']))
                for citation in reason['citations']:
                    original = originals.get(citation.get('evidence_ref')) if isinstance(citation, dict) and isinstance(citation.get('evidence_ref'), str) else None
                    if (original is None or set(citation) != {'evidence_ref', 'receipt_id', 'target_id', 'version', 'pointer'}
                            or citation['evidence_ref'] not in accepted or citation.get('receipt_id') != original['receipt_id']
                            or citation.get('target_id') != original['registration']['target_id']
                            or type(citation.get('version')) is not int or citation.get('version') != original['registration']['version']):
                        issues.append(self._issue(draft, pointer, 'invalid_citation', parent, reason['claim_id']))
                    else:
                        row = json.loads(original['raw_utf8'])
                        try:
                            value = pointer_value(row, citation['pointer'])
                            if stock and (row.get('kind') != 'retail_status' or citation['pointer'] != '/facts/stock_units'
                                          or type(value) is not int or value != reason['value']):
                                issues.append(self._issue(draft, pointer, 'wrong_attribute_citation', parent, reason['claim_id']))
                            if not stock and citation['pointer'] not in ('/', '/facts'):
                                issues.append(self._issue(draft, pointer, 'wrong_attribute_citation', parent, reason['claim_id']))
                            values.append(row)
                        except (KeyError, ValueError, TypeError, IndexError):
                            issues.append(self._issue(draft, pointer, 'invalid_pointer', parent, reason['claim_id']))
                required = {'inspection_supported': {'inspection_sample', 'inspection_report'},
                            'on_sale_supported': {'retail_status'}, 'retail_stock': {'retail_status'}}.get(reason['kind'], set())
                if not required <= {v.get('kind') for v in values}:
                    issues.append(self._issue(draft, pointer, 'wrong_attribute_citation', parent, reason['claim_id']))
                if reason['kind'] in ('inspection_supported', 'on_sale_supported'):
                    refs = {c['evidence_ref'] for c in reason['citations'] if isinstance(c, dict)
                            and isinstance(c.get('evidence_ref'), str) and c['evidence_ref'] in accepted}
                    # Dependencies must also be explicitly cited somewhere in this item.
                    refs.update(c['evidence_ref'] for r in item['reasons'] if isinstance(r, dict)
                        and isinstance(r.get('citations'), list) for c in r['citations'] if isinstance(c, dict)
                        and isinstance(c.get('evidence_ref'), str) and c['evidence_ref'] in accepted
                        and originals[c['evidence_ref']]['registration']['target_kind'] != 'material')
                    pack = acquired['candidates'][parent]
                    cited_view = {**acquired, 'candidates': {**acquired['candidates'], parent: {**pack,
                        'originals': {ref: original for ref, original in originals.items() if ref in refs}}}}
                    claim = 'c1' if reason['kind'] == 'inspection_supported' else 'c2'
                    cited = assess_evidence({**self.evidence.binding, 'parent_asin': parent, 'sim_batch_id': batch,
                                             'necessary_clauses': [claim]}, cited_view)['claims'][claim]
                    if cited['s'] != 1 or cited['r'] != 0:
                        issues.append(self._issue(draft, pointer, 'citation_does_not_support_claim', parent, claim))
        return issues

    def _review(self):
        draft = self.state['drafts'][-1]
        model_issues = []
        if self.binding['method'] != 'R':
            verification = self._role('推荐依据核验', 'verification', 'verification')
            if set(verification) != {'issues'} or not isinstance(verification['issues'], list):
                raise RunStop('failed_protocol', 'invalid_verification')
            model_issues = verification['issues']
            receipts = {r['receipt_id'] for r in self.evidence.audit_view()['receipts']}
            seen = set()
            for issue in model_issues:
                try:
                    valid = (isinstance(issue, dict) and set(issue) == {'issue_id', 'draft_id', 'candidate_id',
                        'claim_id', 'pointer', 'code', 'blocking', 'allowed_actions', 'verifier', 'source_receipts'}
                        and isinstance(issue['issue_id'], str) and bool(issue['issue_id']) and issue['issue_id'] not in seen
                        and issue['draft_id'] == draft['draft_id'] and issue['verifier'] == 'model'
                        and type(issue['blocking']) is bool and isinstance(issue['code'], str) and bool(issue['code'])
                        and issue['allowed_actions'] == ['revise_and_resubmit']
                        and isinstance(issue['source_receipts'], list) and set(issue['source_receipts']) <= receipts)
                    if not valid:
                        raise ValueError('invalid_issue')
                    pointer_value(draft, issue['pointer'])
                    if issue['candidate_id'] is not None:
                        position = [i['parent_asin'] for i in draft['items']].index(issue['candidate_id'])
                        scope = '/items/' + str(position)
                        if issue['pointer'] != scope and not issue['pointer'].startswith(scope + '/'):
                            raise ValueError('invalid_issue_scope')
                        if issue['claim_id'] is not None:
                            claim = [r['claim_id'] for r in draft['items'][position]['reasons']].index(issue['claim_id'])
                            scope += '/reasons/' + str(claim)
                            if issue['pointer'] != scope and not issue['pointer'].startswith(scope + '/'):
                                raise ValueError('invalid_claim_scope')
                    elif issue['claim_id'] is not None:
                        raise ValueError('unbound_claim')
                    seen.add(issue['issue_id'])
                except (KeyError, ValueError, TypeError, IndexError):
                    raise RunStop('failed_protocol', 'invalid_model_issue') from None
            self.state.setdefault('model_verifications', []).append({'draft_id': draft['draft_id'],
                'role_message_id': self.state['messages'][-1]['role_message_id'], 'issues': copy.deepcopy(model_issues)})
            self._complete('推荐依据核验')
        issues = self._program('verify_draft', lambda: self._draft_issues(draft)) + model_issues
        self.state['issues'].extend(copy.deepcopy(issues))
        self.state['visible_issues'] = copy.deepcopy(issues)
        return any(i['blocking'] for i in issues)

    def _revise(self):
        old = self.state['drafts'][-1]
        self.state['feedback_round'] = 1
        new = self._role('推荐管理', 'draft', 'revision')
        if not _draft_shape(new) or not _draft_shape(old):
            raise RunStop('failed_protocol', 'invalid_revision_payload')
        if new['parent_draft_id'] != old['draft_id'] or new['draft_id'] == old['draft_id']:
            raise RunStop('failed_protocol', 'invalid_revision_binding')
        changes = []
        def difference(left, right, pointer):
            if type(left) is dict and type(right) is dict and set(left) == set(right):
                for key in left:
                    difference(left[key], right[key], pointer + '/' + key)
            elif type(left) is list and type(right) is list and len(left) == len(right):
                for i, (a, b) in enumerate(zip(left, right)):
                    difference(a, b, pointer + '/' + str(i))
            elif left != right:
                changes.append((pointer, copy.deepcopy(left), copy.deepcopy(right)))
        difference(old['items'], new['items'], '/items')
        for pointer, before, after in changes:
            issue = next((i for i in self.state['visible_issues'] if pointer == i['pointer']
                          or pointer.startswith(i['pointer'] + '/')), None)
            if issue is None:
                raise RunStop('failed_protocol', 'revision_outside_issue')
            self.state['revisions'].append({'issue_id': issue['issue_id'], 'pointer': pointer, 'old': before,
                'new': after, 'parent_draft_id': old['draft_id'], 'draft_id': new['draft_id']})
        self._program('patch', lambda: self.state['drafts'].append(copy.deepcopy(new)))
        self._review()
        if not changes:
            issue = self._issue(new, '/', 'no_revision')
            self.state['issues'].append(issue)
            self.state['visible_issues'].append(issue)

    def _final_gate(self, draft):
        budget = self.budget.audit_view()
        pending = [r for r in budget['reservations'].values() if r['settled'] is None]
        if (budget['halted'] or len(pending) != 1 or pending[0]['operation'] != 'final'
                or pending[0]['phase'] != 'final' or any(r['settled'] is not None and
                    any(v is None for v in r['settled'].values()) for r in budget['reservations'].values())):
            raise RunStop('failed_protocol', 'unfinished_root_work')
        expected_roles = (set() if self.binding['method'] == 'R' else {'单智能体'} if self.binding['method'] == 'S'
            else {'需求解析', '推荐管理', '用户画像', '农产品画像', '生命周期追溯', '推荐依据核验'})
        if set(self.state['roles_completed']) != expected_roles:
            raise RunStop('failed_protocol', 'incomplete_roles')
        if self.batched and self.binding['method'] != 'R' and (
                set(self.state['profiled_candidates']) != set(self.state['assessments'])
                or len(self.state['profiled_candidates']) != len(set(self.state['profiled_candidates']))):
            raise RunStop('failed_protocol', 'incomplete_candidate_profiles')
        self._empty_gate(draft)
        issues = self._draft_issues(draft) + [i for i in self.state['visible_issues'] if i['blocking']]
        issues = list({i['issue_id']: i for i in issues}.values())
        self.state['release_check'] = {'issues': copy.deepcopy(issues), 'draft_id': draft['draft_id']}
        if issues:
            raise RunStop('blocked_evidence', 'final_gate_blocked')

    def run(self):
        if self.result is not None:
            return copy.deepcopy(self.result)
        release_scope = 'development_pilot' if self.fourrouter and self.binding['fixture'] is None else 'public_fixture_only'
        committed = False
        stage = 'work'
        audit_path = self.output_root / 'audit.json'
        try:
            self._preflight()
            if (self.output_root / 'publication.json').exists() or audit_path.exists():
                raise RunStop('failed_protocol', 'publication_already_exists')
            if self.binding['method'] != 'R':
                for role in ('需求解析', '用户画像'):
                    self._analysis(role)
            goal = min(len(self.queue), self.binding['prefix_limit'] if self.binding['arm'] == 'quality' else self.budget.limits['candidates'])
            if not self.queue and self.binding['method'] != 'R':
                self._model_acquire()
                self._analysis('农产品画像')
            while self.state['cursor'] < goal:
                if self.batched and self.binding['method'] != 'R':
                    self._model_acquire()
                    self._analysis('农产品画像')
                    if self.state['stop_reason'] is not None:
                        break
                    continue
                if self.binding['method'] == 'R':
                    self._rule_acquire()
                else:
                    self._model_acquire()
                assessment = self._check_tool(self.evidence.assess_current())['assessment']
                parent = self.queue[self.state['cursor']]
                self.state['assessments'][parent] = assessment
                if not assessment['advance_allowed']:
                    raise RunStop('failed_protocol', 'current_incomplete')
                if assessment['eligible']:
                    self.state['G'].append(parent)
                if self.binding['method'] != 'R':
                    self._analysis('农产品画像')
                self.state['cursor'] += 1
                if self.binding['arm'] == 'necessary' and len(self.state['G']) == self.binding['K']:
                    self.state['stop_reason'] = 'first_10_qualified'
                    break
                if self.state['cursor'] == goal:
                    break
                if self.state['cursor'] < len(self.queue):
                    self._check_tool(self.evidence.advance_current())
                    self.state['current_candidate'] = self.evidence.binding['parent_asin']
            self.state['stop_reason'] = self.state['stop_reason'] or ('complete_C' if goal == len(self.queue) else
                'quality_prefix' if self.binding['arm'] == 'quality' else 'candidate_prefix')
            proposal = self._rule_draft() if self.binding['method'] == 'R' else self._role('推荐管理', 'draft', 'draft')
            draft = self._program('submit_draft', lambda: proposal)
            self.state['drafts'].append(draft)
            if not _draft_shape(draft) or draft['parent_draft_id'] is not None:
                raise RunStop('failed_protocol', 'invalid_draft_payload')
            if self._review() and self.binding['method'] != 'R':
                self._revise()
            draft = self.state['drafts'][-1]
            if self.binding['method'] != 'R':
                submitted = self._role('推荐管理', 'final_submit', 'final_submit')
                if submitted != {'draft_id': draft['draft_id']}:
                    raise RunStop('failed_protocol', 'unverified_final_draft')
            self._program('final', lambda: self._final_gate(draft), phase='final')
            self.state['terminal'] = 'released' if draft['items'] else 'valid_empty'
            self.state['delivered'] = [i['parent_asin'] for i in draft['items']]
            if self.binding['method'] == 'M' and self.binding['arm'] == 'quality':
                self.state['anchor_consistency'] = 'passed'
                self.state['components'] = self._components()
            publication = {'run_id': self.binding['run_id'], 'release_scope': release_scope,
                'terminal': self.state['terminal'], 'draft': draft, 'draft_sha256': digest(encoded(draft)),
                'G': self.state['G'], 'cursor': self.state['cursor'], 'budget': self.budget.audit_view(),
                'A_sha256': digest(encoded(self.evidence.audit_view()['acquired'])),
                'component_record': 'audit.json' if self.state['components'] else None,
                'budget_snapshot': 'before_record_commit', 'settlement_journal': 'budget.jsonl'}
            def commit():
                nonlocal committed
                staging = self.output_root / 'publication.pending'
                with staging.open('xb') as stream:
                    stream.write(encoded(publication) + b'\n')
                    stream.flush()
                    os.fsync(stream.fileno())
                os.rename(staging, self.output_root / 'publication.json')
                committed = True
            self._program('commit', commit, phase='final', logical=0)
            self.state['publication_record_sha256'] = digest(encoded(publication) + b'\n')
            if self.state['components']:
                for component in self.state['components'].values():
                    component['anchor']['publication_record_sha256'] = self.state['publication_record_sha256']
                    component['anchor_sha256'] = digest(encoded(component['anchor']))
            stage = 'audit'
            self._program('seal_audit', lambda: self._write_audit(audit_path), phase='final', logical=0)
        except RunStop as exc:
            self.state.update(terminal=exc.terminal, reason=exc.reason, delivered=[])
        except OSError:
            self.state.update(terminal='failed_protocol', reason='audit_seal_failed' if stage == 'audit' else 'publication_failed', delivered=[])
        if committed and self.state['terminal'] not in ('released', 'valid_empty'):
            (self.output_root / 'publication.json').rename(self.output_root / 'publication.failed.json')
        if self.binding['method'] == 'M' and self.binding['arm'] == 'quality' and self.state['terminal'] not in ('released', 'valid_empty'):
            self.state['components'] = self._components()
        if self.state['terminal'] not in ('released', 'valid_empty'):
            if audit_path.exists() or stage == 'audit':
                audit_path = self.output_root / 'audit.failed.json'
            try:
                self._write_audit(audit_path)
            except OSError:
                audit_path = None
        self.result = {**copy.deepcopy(self.state), 'budget': self.budget.audit_view(),
            'release_scope': release_scope, 'provider_requests_sent': 0,
            'publication_path': str(self.output_root / 'publication.json') if self.state['terminal'] in ('released', 'valid_empty') else None,
            'audit_path': str(audit_path) if audit_path else None}
        return copy.deepcopy(self.result)

    def _write_audit(self, path):
        if self.on_demand and 'acquired_ref' not in self.state:
            self.state['acquired_ref'] = self._trace_ref('acquired', self.evidence.audit_view()['acquired'])
        view = self.audit_view()
        if self.on_demand:
            view['messages'] = [{k: copy.deepcopy(v) for k, v in message.items()
                if k not in ('request', 'response')} | {'response_summary': {k: copy.deepcopy(v)
                    for k, v in message['response'].items() if k not in ('raw_response', 'message')}}
                for message in self.state['messages']]
            def references(value):
                if isinstance(value, dict):
                    return {k: references(v) for k, v in value.items() if k != 'raw_utf8'} | (
                        {'raw_sha256': digest(value['raw_utf8'].encode()), 'raw_bytes': len(value['raw_utf8'].encode())}
                        if isinstance(value.get('raw_utf8'), str) else
                        {'raw_utf8': None} if 'raw_utf8' in value else {})
                return [references(item) for item in value] if isinstance(value, list) else value
            view = references(view)
        with path.open('xb') as stream:
            stream.write(encoded(view) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())

    def _trace_ref(self, kind, value):
        raw = encoded(value) + b'\n'
        directory = self.output_root / 'trace'
        directory.mkdir(exist_ok=True)
        path = directory / (kind + '-' + digest(raw) + '.json')
        if path.exists():
            if path.read_bytes() != raw:
                raise OSError('trace_binding_mismatch')
        else:
            with path.open('xb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        return {'path': path.relative_to(PROJECT).as_posix(), 'sha256': digest(raw), 'bytes': len(raw)}

    def audit_view(self):
        return copy.deepcopy({**self.state, 'evidence': self.evidence.audit_view(), 'budget': self.budget.audit_view(),
            'settlement_journal': 'budget.jsonl', 'budget_snapshot': 'at_audit_serialization'})

    def _empty_gate(self, draft):
        if not draft['items'] and self.state['cursor'] != len(self.queue):
            raise RunStop('blocked_evidence', 'empty_unproven')
