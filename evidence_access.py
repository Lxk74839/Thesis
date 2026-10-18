"""Host-bound acquisition of SIM facts; no evaluation data or model access."""
import copy
import math
import os
import hashlib
import json
from pathlib import Path
import secrets
import stat
import threading
import time

PROJECT = Path(__file__).resolve().parent
FILES = {'batches.jsonl', 'events.jsonl', 'materials.jsonl', 'registrations.jsonl',
         'actions.jsonl', 'change-actions.jsonl', 'policy.json'}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate_key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('invalid_number')
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


class LocalEvidenceSource:
    """A read-only adapter pinned to one snapshot and its declared fact files."""
    def __init__(self, snapshot_ref):
        self.snapshot_ref = copy.deepcopy(snapshot_ref)
        self.setup = {'bytes': 0, 'file_reads': 0}
        self.material_kinds = {}

    def _file(self, path, ref):
        path = (PROJECT / path).absolute()
        if '..' in path.parts:
            raise ValueError('source_integrity_error')
        for item in (path, *path.parents):
            if item.exists() and (item.is_symlink() or item.is_junction()
                    or getattr(item.lstat(), 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                raise ValueError('source_integrity_error')
            if item == PROJECT:
                break
        if not path.is_relative_to(PROJECT) or not path.is_file():
            raise ValueError('source_integrity_error')
        raw = path.read_bytes()
        self.setup['bytes'] += len(raw)
        self.setup['file_reads'] += 1
        if len(raw) != ref['bytes'] or digest(raw) != ref['sha256']:
            raise ValueError('source_integrity_error')
        return raw, {'component_path': path.relative_to(PROJECT).as_posix(),
                     'component_sha256': ref['sha256'], 'bytes': len(raw)}

    def list(self, parent, batch, *, binding):
        raw, origin = self._file(self.snapshot_ref['path'], self.snapshot_ref)
        snapshot = decode(raw)
        if snapshot['snapshot_id'] != binding['snapshot_id'] or snapshot['verify_at_ms'] != binding['verify_at_ms']:
            raise ValueError('source_integrity_error')
        context = {'snapshot': {'raw_utf8': raw.decode('utf-8'), 'source': origin}}
        directory = Path(self.snapshot_ref['path']).parent
        raw_policy, policy_origin = self._file(directory / 'policy.json', snapshot['components']['policy.json'])
        policy = decode(raw_policy)
        if (policy['policy_id'] != snapshot['policy_id'] or policy['read_principal_id'] != binding['principal_id']
                or snapshot.get('read_principal_id', binding['principal_id']) != binding['principal_id']):
            raise ValueError('source_integrity_error')
        context['policy'] = {'raw_utf8': raw_policy.decode('utf-8'), 'source': policy_origin}
        registrations = []
        for name, ref in snapshot['components'].items():
            if name not in FILES:
                raise ValueError('source_integrity_error')
            if name == 'policy.json':
                continue
            content, source = self._file(directory / name, ref)
            if name == 'materials.jsonl':
                self.material_kinds = {(row['evidence_id'], row['version']): row['kind']
                                       for row in (decode(value) for value in content.splitlines())}
            if name in ('actions.jsonl', 'change-actions.jsonl'):
                context['actions_scope'] = {'empty': not content, 'raw_utf8': '' if not content else None,
                                             'source': source}
            if name == 'registrations.jsonl':
                registration_source = source
                offset = 0
                for line, value in enumerate(content.splitlines(keepends=True), 1):
                    row = decode(value)
                    if type(row['sequence']) is not int or type(row['registered_at_ms']) is not int:
                        raise ValueError('source_integrity_error')
                    if (row['parent_asin'] == parent and row['sim_batch_id'] == batch
                            and row['sequence'] <= snapshot['cutoff_sequence']
                            and row['registered_at_ms'] <= snapshot['sealed_at_ms']):
                        registrations.append({'record': row, 'raw_utf8': value.rstrip(b'\n').decode('utf-8'),
                            'source': {**source, 'line': line, 'offset': offset}})
                    offset += len(value)
        return context, registrations, {'empty': not registrations, 'source': {**registration_source,
            'scope_parent_asin': parent, 'scope_sim_batch_id': batch, 'scope_records': len(registrations),
            'cutoff_sequence': snapshot['cutoff_sequence'], 'sealed_at_ms': snapshot['sealed_at_ms']}}

    def read(self, registrations):
        raw, _ = self._file(self.snapshot_ref['path'], self.snapshot_ref)
        snapshot = decode(raw)
        directory = Path(self.snapshot_ref['path']).parent
        names = {'batch': ('batches.jsonl', 'sim_batch_id'), 'event': ('events.jsonl', 'event_id'),
                 'material': ('materials.jsonl', 'evidence_id'),
                 'change_action': ('change-actions.jsonl' if 'change-actions.jsonl' in snapshot['components'] else 'actions.jsonl', 'action_id')}
        objects = {}
        origins = {}
        for name, identity in {names[r['target_kind']] for r in registrations}:
            content, origin = self._file(directory / name, snapshot['components'][name])
            origins[name] = origin
            offset = 0
            for line, value in enumerate(content.splitlines(keepends=True), 1):
                row = decode(value)
                objects[(name, row[identity], row.get('version', 1) if identity == 'action_id' else row['version'])] = {
                    'status': 'ok', 'raw_utf8': value.rstrip(b'\n').decode('utf-8'),
                    'sha256': digest(value.rstrip(b'\n')), 'bytes': len(value.rstrip(b'\n')),
                    'source': {**origin, 'line': line, 'offset': offset}}
                offset += len(value)
        return [objects.get((names[r['target_kind']][0], r['target_id'], r['version']),
            {'status': 'unavailable', 'source': {**origins[names[r['target_kind']][0]],
                'lookup_target_id': r['target_id'], 'lookup_version': r['version'], 'found': False}}) for r in registrations]


class RootBudget:
    """One host-owned ledger, including final capacity; no provider defaults."""
    resources = ('model_calls', 'input_tokens', 'output_tokens', 'logical_tools', 'physical_tools',
                 'candidates', 'retries', 'elapsed_ms', 'cost_microusd')

    def __init__(self, binding, limits, final_reserve, *, clock, journal_path):
        self.binding = copy.deepcopy(binding)
        self.limits = copy.deepcopy(limits)
        self.final_reserve = copy.deepcopy(final_reserve)
        for table in (limits, final_reserve):
            if set(table) != set(self.resources) or any(type(v) is not int or v < 0 for v in table.values()):
                raise ValueError('invalid_budget')
        if any(final_reserve[k] > limits[k] for k in self.resources):
            raise ValueError('invalid_final_reserve')
        self.clock = clock
        self.started = clock()
        self.usage = dict.fromkeys(self.resources, 0)
        self.reservations = {}
        self.receipts = []
        self.lock = threading.RLock()
        self.final_started = False
        self.halted = None
        self.journal_path = Path(journal_path).resolve()
        if not any(self.journal_path.is_relative_to(PROJECT / folder) for folder in
                   ('.tmp/recommendation-runtime', 'data/recommendation-runtime-audit')):
            raise ValueError('invalid_journal_path')
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        with self.journal_path.open('x', encoding='utf-8') as stream:
            stream.write(encoded({'kind': 'init', 'binding': self.binding,
                                  'limits': limits, 'final_reserve': final_reserve}).decode() + '\n')
            stream.flush()
            os.fsync(stream.fileno())

    def _record(self, value):
        with self.journal_path.open('a', encoding='utf-8') as stream:
            stream.write(encoded(value).decode() + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        self.receipts.append(copy.deepcopy(value))

    def _tick(self):
        elapsed = math.ceil(self.clock() - self.started)
        if elapsed < self.usage['elapsed_ms']:
            raise ValueError('non_monotonic_clock')
        self.usage['elapsed_ms'] = elapsed

    def reserve(self, operation, upper_bound, *, phase, retry_of):
        with self.lock:
            self._tick()
            if phase not in ('work', 'final') or self.final_started and phase != 'final':
                raise ValueError('invalid_budget_phase')
            if not set(upper_bound) <= set(self.resources) or any(type(v) is not int or v < 0 for v in upper_bound.values()):
                raise ValueError('invalid_reservation')
            held = {k: upper_bound.get(k, 0) for k in self.resources}
            if retry_of is not None:
                prior = self.reservations.get(retry_of)
                if prior is None or prior['settled'] is None or prior['status'] == 'ok':
                    raise ValueError('invalid_retry')
                held['retries'] = 1
            if self.halted:
                result = {'status': self.halted, 'operation': operation}
                self._record(result)
                return result
            outstanding = self._held()
            reserve = self.final_reserve if phase == 'work' else dict.fromkeys(self.resources, 0)
            allowed = all(self.usage[k] + outstanding[k] + held[k] + reserve[k] <= self.limits[k] for k in self.resources)
            status = 'reserved' if allowed else ('deadline_exceeded' if self.usage['elapsed_ms'] + held['elapsed_ms']
                + reserve['elapsed_ms'] > self.limits['elapsed_ms'] else 'budget_exhausted')
            result = {'status': status, 'operation': operation, 'phase': phase, 'retry_of': retry_of,
                      'reservation_id': self.binding['run_id'] + ':' + str(len(self.receipts)), 'held': held,
                      'usage_before': self.usage.copy(), 'held_before': outstanding,
                      'final_reserve_applied': reserve.copy()}
            self._record(result)
            if allowed:
                self.reservations[result['reservation_id']] = {'held': held, 'settled': None, 'status': 'pending',
                    'operation': copy.deepcopy(operation), 'phase': phase}
                self.final_started = phase == 'final'
            return copy.deepcopy(result)

    def settle(self, reservation_id, observation):
        with self.lock:
            self._tick()
            entry = self.reservations.get(reservation_id)
            previous = entry['settled'] if entry else None
            if entry is None or previous is not None and (all(v is not None for v in previous.values())
                    or observation.get('authoritative_receipt') != reservation_id):
                raise ValueError('invalid_or_settled_reservation')
            actual = {k: observation['usage'].get(k, None if entry['held'][k] else 0)
                      for k in self.resources if k != 'elapsed_ms'}
            if entry['held']['retries']:
                actual['retries'] = 1
            if any(v is not None and (type(v) is not int or v < 0) for v in actual.values()):
                raise ValueError('invalid_usage')
            if previous is not None and (any(v is None for v in actual.values())
                    or any(v is not None and actual[k] != v for k, v in previous.items())):
                raise ValueError('invalid_authoritative_usage')
            unknown = any(v is None for v in actual.values())
            result = {'status': 'unresolved' if unknown else 'settled', 'reservation_id': reservation_id, 'usage': actual,
                      'observation': copy.deepcopy(observation), 'usage_before': self.usage.copy(),
                      'released': {k: max(0, entry['held'][k] - v) if v is not None else 0 for k, v in actual.items()},
                      'unresolved': {k: entry['held'][k] for k, v in actual.items() if v is None}}
            self._record(result)
            for key, value in actual.items():
                if previous is None or previous[key] is None:
                    self.usage[key] += value if value is not None else 0
            entry.update(settled=actual, status=observation['status'])
            if self.halted == 'usage_unresolved' and self.audit_view()['usage_exact']:
                self.halted = None
            if unknown:
                self.halted = 'usage_unresolved'
            elif observation.get('late') or self.usage['elapsed_ms'] > self.limits['elapsed_ms']:
                self.halted = 'deadline_exceeded'
            elif (any(self.usage[k] > self.limits[k] for k in self.resources)
                    or any(v > entry['held'][k] for k, v in actual.items())):
                self.halted = 'budget_exhausted'
            return copy.deepcopy(result)

    def _held(self):
        return {k: sum(v['held'][k] for v in self.reservations.values() if v['settled'] is None
                      or k != 'elapsed_ms' and v['settled'].get(k) is None) for k in self.resources}

    def audit_view(self):
        with self.lock:
            self._tick()
            held = self._held()
            return copy.deepcopy({'binding': self.binding, 'limits': self.limits, 'final_reserve': self.final_reserve,
                'usage': self.usage, 'held': held, 'reservations': self.reservations, 'receipts': self.receipts,
                'halted': self.halted, 'usage_exact': not any(held.values()) and all(
                    v['settled'] is not None and all(x is not None for x in v['settled'].values())
                    for v in self.reservations.values()),
                'overrun': {k: max(0, self.usage[k] + held[k] - self.limits[k]) for k in self.resources}})


class EvidenceSession:
    """The model-facing interface accepts only bound list/read/page operations."""
    version = 'restricted-evidence-0.1.0'

    @staticmethod
    def tool_schemas(*, batch=False):
        inputs = [('list_evidence', 'cursor', {'type': ['string', 'null']}),
                  ('read_evidence', 'evidence_refs', {'type': 'array', 'items': {'type': 'string'},
                    'minItems': 1, 'maxItems': 32, 'uniqueItems': True})]
        schemas = [{'name': name, 'version': EvidenceSession.version, 'input_schema': {'type': 'object',
            'properties': {key: shape}, 'required': [key], 'additionalProperties': False}} for name, key, shape in inputs]
        if batch:
            properties = {'schema_version': {'enum': ['acquisition-batch-0.1.0']},
                'start_candidate': {'type': 'string'}, 'candidate_limit': {'type': 'integer', 'minimum': 1, 'maximum': 32},
                'claim_ids': {'type': 'array', 'items': {'type': 'string'}, 'uniqueItems': True},
                'max_list_pages': {'type': 'integer', 'minimum': 1},
                'max_read_batches': {'type': 'integer', 'minimum': 1},
                'stop_policy': {'enum': ['first_10_qualified', 'fixed_prefix']}}
            schemas.append({'name': 'acquire_batch', 'version': 'restricted-evidence-batch-0.1.0',
                'input_schema': {'type': 'object', 'properties': properties,
                                 'required': list(properties), 'additionalProperties': False}})
        return schemas

    def __init__(self, binding, source, *, limits, final_reserve, joint=None, clock=None, sleeper=time.sleep, root_budget=None):
        self.root_budget = root_budget
        if root_budget is not None:
            if (any(binding[k] != root_budget.binding[k] for k in
                    ('run_id', 'root_task_id', 'snapshot_id', 'principal_id', 'verify_at_ms'))
                    or limits != root_budget.limits or final_reserve != root_budget.final_reserve
                    or clock is not None and clock is not root_budget.clock
                    or getattr(root_budget, 'evidence_attached', False)):
                raise ValueError('root_budget_binding_mismatch')
            root_budget.evidence_attached = True
            clock = root_budget.clock
        self.root_reservations = {}
        self.binding = copy.deepcopy(binding)
        self.source = source
        self.joint = joint
        self.limits = copy.deepcopy(limits)
        self.final_reserve = copy.deepcopy(final_reserve)
        self.secret = secrets.token_bytes(32)
        self.scope_seed = self.secret + encoded({key: binding[key] for key in
            ('run_id', 'root_task_id', 'parent_asin', 'sim_batch_id', 'principal_id', 'snapshot_id', 'verify_at_ms', 'necessary_clauses')})
        self.acquired = {'binding': copy.deepcopy(binding), 'context': {}, 'candidates': {}}
        if joint is not None:
            if (joint.root['root_task_id'] != binding['root_task_id'] or binding['parent_asin'] not in joint.candidates['C']
                    or joint.candidates['batches'][joint.candidates['C'].index(binding['parent_asin'])] != binding['sim_batch_id']):
                raise ValueError('joint_binding_mismatch')
            self.acquired['candidate_binding'] = {'C': joint.candidates['C'][:], 'base_scores': joint.candidates['b'][:]}
        self.refs = {}
        self.cursors = {}
        self.cache = {}
        self.receipts = []
        self.usage = dict.fromkeys(('logical_tools', 'physical_tools', 'candidates', 'retries', 'elapsed_ms'), 0)
        self.clock = clock or (lambda: time.monotonic() * 1000)
        self.sleeper = sleeper
        self.started = root_budget.started if root_budget is not None else self.clock()
        self.stopped = None
        self.lock = root_budget.lock if root_budget is not None else threading.RLock()
        self.seen_candidates = set()
        self.history = {}
        self.failed_continuations = {}
        self.provenance = {}
        self.unsettled_reservations = {}
        for table in (self.limits, self.final_reserve):
            if any(type(value) is not int or value < 0 for value in table.values()):
                raise ValueError('invalid_budget')
        if not {'logical_tools', 'physical_tools', 'elapsed_ms'} <= set(self.final_reserve):
            raise ValueError('missing_final_reserve')

    def dispatch(self, operation, arguments, *, actor_role='host'):
        with self.lock:
            if operation == 'acquire_batch':
                return self._acquire_batch(arguments, actor_role)
            if operation not in ('list_evidence', 'read_evidence', 'candidate_page'):
                return self._execute('denied_operation', {}, actor_role)
            retry_of = next((self.failed_continuations[key] for key in self._request_keys(operation, arguments)
                             if key in self.failed_continuations), None)
            return self._execute(operation, arguments, actor_role, retry_of)

    def _acquire_batch(self, plan, actor_role):
        root = self.root_budget
        fields = {'schema_version', 'start_candidate', 'candidate_limit', 'claim_ids',
                  'max_list_pages', 'max_read_batches', 'stop_policy'}
        if (root is None or self.joint is None or root.binding.get('orchestration') != 'batch32-0.1.0'
                or root.binding['method'] not in ('S', 'M')
                or actor_role != ('单智能体' if root.binding['method'] == 'S' else '生命周期追溯')
                or not isinstance(plan, dict) or set(plan) != fields
                or plan['schema_version'] != 'acquisition-batch-0.1.0'
                or plan['start_candidate'] != self.binding['parent_asin']
                or self.acquired.get('assessments', {}).get(self.binding['parent_asin'], {}).get('advance_allowed')
                or plan['claim_ids'] != self.binding['necessary_clauses']
                or any(type(plan[k]) is not int or plan[k] < 1
                       for k in ('candidate_limit', 'max_list_pages', 'max_read_batches'))
                or plan['candidate_limit'] > 32
                or plan['stop_policy'] != ('first_10_qualified' if self.binding['arm'] == 'necessary' else 'fixed_prefix')):
            return self._execute('denied_operation', {}, actor_role)
        steps, processed, assessments, observations = [], [], {}, []

        def step(operation, arguments):
            parent = self.binding['parent_asin']
            result = (self.assess_current() if operation == 'assess_current' else
                      self.advance_current() if operation == 'advance_current' else
                      self.dispatch(operation, arguments, actor_role=actor_role) if operation != 'begin_batch' else
                      self._execute(operation, arguments, actor_role))
            steps.append({'candidate_id': parent, **{k: copy.deepcopy(result['receipt'][k]) for k in
                          ('operation', 'receipt_id', 'root_reservation_id', 'status', 'usage_delta')}})
            return result

        result = step('begin_batch', {})
        order = self.joint.orders['base']
        goal = min(len(order), root.binding['prefix_limit'] if self.binding['arm'] == 'quality' else self.limits['candidates'])
        position = order.index(self.binding['parent_asin'])
        pages = reads = 0
        stop_reason = 'batch_limit'
        for _ in range(min(plan['candidate_limit'], max(0, goal - position))):
            if result['status'] != 'ok':
                break
            entries, items, cursor = [], [], None
            while True:
                if pages >= plan['max_list_pages']:
                    result = {'status': 'batch_plan_exhausted'}
                    break
                result = step('list_evidence', {'cursor': cursor})
                pages += 1
                if result['status'] != 'ok':
                    break
                entries.extend(result['entries'])
                cursor = result['next_cursor']
                if cursor is None:
                    break
            entries.sort(key=lambda r: (r['target_kind'], r['target_id'].encode(), r['version']))
            for offset in range(0, len(entries), 32):
                if result['status'] != 'ok':
                    break
                if reads >= plan['max_read_batches']:
                    result = {'status': 'batch_plan_exhausted'}
                    break
                result = step('read_evidence', {'evidence_refs': [r['evidence_ref'] for r in entries[offset:offset + 32]]})
                reads += 1
                items.extend(result.get('items', []))
                if any(item['status'] in ('io_error', 'not_attempted') for item in result.get('items', [])):
                    result = {**result, 'status': 'io_error'}
            if result['status'] == 'ok':
                result = step('assess_current', {})
                if result['status'] == 'ok':
                    parent = self.binding['parent_asin']
                    assessments[parent] = result['assessment']
                    observations.append({'candidate_id': parent, 'entries': entries, 'items': items,
                                         'assessment_receipt_id': steps[-1]['receipt_id']})
                    if result['assessment']['advance_allowed']:
                        processed.append(parent)
                    else:
                        result = {'status': 'current_incomplete'}
            if result['status'] != 'ok':
                break
            position += 1
            eligible = sum(a['eligible'] for a in self.acquired['assessments'].values())
            if self.binding['arm'] == 'necessary' and eligible >= root.binding['K']:
                stop_reason = 'first_10_qualified'
                break
            if position >= goal:
                stop_reason = 'complete_C' if position == len(order) else (
                    'quality_prefix' if self.binding['arm'] == 'quality' else 'candidate_prefix')
                break
            result = step('advance_current', {})
        return {'status': result['status'], 'plan_sha256': digest(encoded(plan)),
                'processed': processed, 'assessments': assessments, 'observations': observations,
                'steps': steps, 'stop_reason': stop_reason, 'usage_after': root.audit_view()['usage']}

    def _request_keys(self, operation, arguments):
        if not isinstance(arguments, dict):
            return []
        scope = digest(self.scope_seed)
        if operation == 'read_evidence' and isinstance(arguments.get('evidence_refs'), list):
            return [(scope, operation, ref) for ref in arguments['evidence_refs'] if isinstance(ref, str) and ref in self.refs]
        if operation == 'list_evidence' and set(arguments) == {'cursor'} and (
                arguments['cursor'] is None or isinstance(arguments['cursor'], str)):
            return [(scope, operation, arguments['cursor'])]
        return []

    def assess_current(self):
        with self.lock:
            return self._execute('assess_current', {}, '推荐依据核验')

    def advance_current(self):
        with self.lock:
            return self._execute('advance_current', {}, 'host')

    def retry(self, request_id):
        with self.lock:
            prior = self.history.get(request_id)
            if prior is None or not prior['retryable']:
                return self._execute('retry', {}, 'host')
            return self._execute(prior['operation'], prior['arguments'], prior['actor_role'], request_id)

    def _estimate(self, operation, arguments):
        logical, physical = 1, 0
        if operation == 'candidate_page':
            logical = 32
        if operation == 'list_evidence' and isinstance(arguments, dict) and set(arguments) == {'cursor'}:
            logical = 32 + (3 if not self.acquired['context'] else 0)
            physical = 1
        if operation == 'read_evidence' and isinstance(arguments, dict) and set(arguments) == {'evidence_refs'}:
            refs = arguments['evidence_refs']
            if isinstance(refs, list) and 1 <= len(refs) <= 32 and all(isinstance(r, str) and r in self.refs for r in refs):
                logical = len(refs)
                physical = int(any(r not in self.cache for r in refs))
        return {'logical_tools': logical, 'physical_tools': physical}

    def _shared_execute(self, operation, arguments, actor_role, retry_of):
        root = self.root_budget
        self.usage = root.usage.copy()
        before = self.usage.copy()
        held = self._estimate(operation, arguments)
        candidate = operation in ('list_evidence', 'read_evidence') and self.binding['parent_asin'] not in self.seen_candidates
        held.update(candidates=int(candidate), retries=int(retry_of is not None),
                    elapsed_ms=45000 + ((1000, 2000)[min(self.usage['retries'], 1)] if retry_of else 0))
        reservation = root.reserve(operation, held, phase='work', retry_of=self.root_reservations.get(retry_of))
        if reservation['status'] != 'reserved':
            self.stopped = reservation['status']
        result = self._execute(operation, arguments, actor_role, retry_of, _shared=False)
        receipt = result['receipt']
        receipt['root_reservation_id'] = reservation['reservation_id']
        self.receipts[-1]['root_reservation_id'] = reservation['reservation_id']
        if reservation['status'] == 'reserved':
            actual = {**receipt['usage_delta'], 'candidates': self.usage['candidates'] - before['candidates'],
                      'retries': self.usage['retries'] - before['retries']}
            if receipt['reservation']['unresolved']:
                actual['logical_tools'] = None
            root.settle(reservation['reservation_id'], {'status': result['status'], 'usage': actual,
                                                      'late': receipt['late']})
            self.root_reservations[receipt['receipt_id']] = reservation['reservation_id']
        self.usage = root.usage.copy()
        result['receipt']['root_usage_after'] = copy.deepcopy(self.usage)
        self.receipts[-1]['root_usage_after'] = copy.deepcopy(self.usage)
        return result

    def _execute(self, operation, arguments, actor_role, retry_of=None, *, _shared=True):
        if self.root_budget is not None and _shared:
            return self._shared_execute(operation, arguments, actor_role, retry_of)
        before = copy.deepcopy(self.usage)
        operation_binding = copy.deepcopy(self.binding)
        receipt_id = digest(self.scope_seed + str(len(self.receipts)).encode())
        self.adapter_request_id = receipt_id + ':1'
        self.delta = {'logical_tools': 0, 'physical_tools': 0}
        started = self.clock()
        held = self._estimate(operation, arguments)
        backoff_ms = (1000, 2000)[min(self.usage['retries'], 1)] if retry_of is not None else 0
        held['elapsed_ms'] = 45000 + backoff_ms
        deadline = min(started + held['elapsed_ms'], self.started + self.limits['elapsed_ms'] - self.final_reserve['elapsed_ms'])
        admitted = not self.stopped and all(self.usage[key] + held[key] + self.final_reserve[key] <= self.limits[key]
                                           for key in ('logical_tools', 'physical_tools'))
        is_candidate = operation in ('list_evidence', 'read_evidence') and self.binding['parent_asin'] not in self.seen_candidates
        admitted = admitted and self.usage['candidates'] + int(is_candidate) <= self.limits['candidates']
        time_available = started - self.started + held['elapsed_ms'] + self.final_reserve['elapsed_ms'] <= self.limits['elapsed_ms']
        admitted = admitted and time_available
        admitted = admitted and (retry_of is None or self.usage['retries'] < self.limits['retries'])
        if not admitted and not self.stopped:
            self.stopped = 'deadline_exceeded' if not time_available else 'budget_exhausted'
        try:
            if admitted and retry_of is not None:
                self.usage['retries'] += 1
                self.sleeper(backoff_ms / 1000)
                if self.clock() >= deadline:
                    self.stopped = 'deadline_exceeded'
            result = self._dispatch(operation, arguments) if admitted and not self.stopped else {'status': self.stopped or 'budget_exhausted'}
        except (ValueError, KeyError, TypeError, UnicodeError, FileNotFoundError):
            self.stopped = 'source_integrity_error'
            result = {'status': self.stopped}
        except OSError:
            result = {'status': 'io_error'}
        if admitted and result['status'] != 'ok' and not self.delta['logical_tools'] and not result.get('items'):
            self.delta['logical_tools'] = 1
        if self.delta['physical_tools'] and is_candidate:
            self.seen_candidates.add(self.binding['parent_asin'])
            self.usage['candidates'] += 1
        for key, value in self.delta.items():
            self.usage[key] += value
        finished = self.clock()
        late = admitted and finished > deadline
        if late:
            result['status'] = 'deadline_exceeded'
            self.stopped = 'deadline_exceeded'
        unknown = any(item.get('usage_known') is False for item in result.get('items', []))
        if unknown:
            self.stopped = 'io_error'
            result['status'] = 'io_error'
            self.unsettled_reservations[receipt_id] = held.copy()
        if self.stopped:
            self.acquired['halted'] = self.stopped
        self.usage['elapsed_ms'] = finished - self.started
        settled = {**self.delta, 'elapsed_ms': finished - started}
        receipt = {'receipt_id': receipt_id, 'request_id': receipt_id, 'retry_of': retry_of,
            'operation': operation, 'status': result['status'], 'actor_role': actor_role,
            'requested_refs': [ref for ref in arguments.get('evidence_refs', []) if isinstance(ref, str) and ref in self.refs]
                if isinstance(arguments, dict) and isinstance(arguments.get('evidence_refs', []), list) else [],
            'scope_handle': digest(self.scope_seed), 'started_at_ms': started, 'finished_at_ms': finished,
            'deadline_at_ms': deadline,
            'late': late, 'usage_delta': self.delta.copy(), 'root_usage_before': before,
            'root_usage_after': self.usage.copy(), 'response_bytes': 0,
            'reservation': {'held': held if admitted else dict.fromkeys(held, 0),
                            'settled': dict.fromkeys(held) if unknown else settled if admitted else dict.fromkeys(held, 0),
                            'released': {key: max(0, held[key] - settled[key]) for key in held} if admitted and not unknown else dict.fromkeys(held, 0),
                            'unresolved': unknown},
            'usage_exact': not self.unsettled_reservations,
            'items': []}
        for item in self.acquired['context'].values():
            item.setdefault('receipt_id', receipt_id)
        for pack in self.acquired['candidates'].values():
            for item in [*pack['registrations'], *pack['originals'].values(), *pack['attempts'].values(),
                         *pack.get('enumeration_observations', [])]:
                item.setdefault('receipt_id', receipt_id)
        observations = [(kind, item, None) for kind, item in self.acquired['context'].items()
                        if item['receipt_id'] == receipt_id]
        for row in result.get('entries', []):
            observations.append(('registration', self.refs[row['evidence_ref']], row['evidence_ref']))
        pack = self.acquired['candidates'].get(operation_binding['parent_asin'], {})
        for observation in pack.get('enumeration_observations', []):
            if observation['empty'] and observation['receipt_id'] == receipt_id:
                observations.append(('empty_registration_scope', observation, None))
        for row in result.get('items', []):
            ref = row['evidence_ref']
            observations.append(('original', pack['attempts'][ref], ref))
        for kind, item, ref in observations:
            origin = item.get('source') or self.refs[ref]['source']
            source_ref = digest(self.scope_seed + encoded(origin))
            self.provenance[source_ref] = origin
            adapter_id = item.get('adapter_request_id') or (self.adapter_request_id if self.delta['physical_tools'] else None)
            item.update(source_ref=source_ref, adapter_request_id=adapter_id)
            receipt['items'].append({'kind': kind, 'evidence_ref': ref, 'source_ref': source_ref,
                'status': item.get('status', 'ok'), 'cache_hit': item.get('cache_hit', False),
                'adapter_request_id': adapter_id})
            for visible in [*result.get('entries', []), *result.get('items', [])]:
                if ref is not None and visible['evidence_ref'] == ref:
                    visible['source_ref'] = source_ref
        result['receipt'] = receipt
        while receipt['response_bytes'] != len(encoded(result)):
            receipt['response_bytes'] = len(encoded(result))
        self.receipts.append(copy.deepcopy({**receipt, 'binding': operation_binding}))
        self.history[receipt_id] = {'operation': operation, 'arguments': copy.deepcopy(arguments), 'actor_role': actor_role,
            'retryable': result['status'] in ('io_error', 'deadline_exceeded') or
                         any(v['status'] in ('io_error', 'deadline_exceeded') for v in result.get('items', []))}
        if admitted:
            item_status = {item['evidence_ref']: item['status'] for item in result.get('items', [])}
            for key in self._request_keys(operation, arguments):
                status = item_status.get(key[2], result['status'])
                if status in ('io_error', 'deadline_exceeded'):
                    self.failed_continuations[key] = receipt_id
                elif (key[2] in item_status and status in ('ok', 'unavailable', 'access_denied')) or (
                        operation == 'list_evidence' and result['status'] == 'ok'):
                    self.failed_continuations.pop(key, None)
        return result

    def _dispatch(self, operation, arguments):
        if operation == 'begin_batch':
            self.delta['logical_tools'] = 1
            return {'status': 'ok'}
        if operation == 'advance_current':
            self.delta['logical_tools'] = 1
            current = self.acquired.get('assessments', {}).get(self.binding['parent_asin'], {})
            if not current.get('advance_allowed') or self.joint is None:
                return {'status': 'current_incomplete'}
            order = self.joint.orders['base']
            position = order.index(self.binding['parent_asin']) + 1
            if position == len(order):
                return {'status': 'end_of_candidates'}
            parent = order[position]
            batch = self.joint.candidates['batches'][self.joint.candidates['C'].index(parent)]
            self.binding.update(parent_asin=parent, sim_batch_id=batch)
            self.scope_seed = self.secret + encoded({key: self.binding[key] for key in
                ('run_id', 'root_task_id', 'parent_asin', 'sim_batch_id', 'principal_id', 'snapshot_id', 'verify_at_ms', 'necessary_clauses')})
            self.refs.clear()
            self.cursors.clear()
            return {'status': 'ok'}
        if operation == 'assess_current':
            from evidence_verification import assess_evidence
            self.delta['logical_tools'] = 1
            assessment = assess_evidence(self.binding, self.acquired)
            self.acquired.setdefault('assessments', {})[self.binding['parent_asin']] = assessment
            return {'status': 'ok', 'assessment': assessment}
        if operation == 'candidate_page' and self.joint is not None:
            result = self.joint.dispatch(operation, arguments)
            self.delta['logical_tools'] += len(result.get('candidates', []))
            return result
        if operation == 'read_evidence' and isinstance(arguments, dict) and set(arguments) == {'evidence_refs'}:
            refs = arguments['evidence_refs']
            if not isinstance(refs, list) or not 1 <= len(refs) <= 32 or any(not isinstance(r, str) for r in refs):
                return {'status': 'invalid_request'}
            if len(set(refs)) != len(refs) or any(r not in self.refs for r in refs):
                return {'status': 'access_denied'}
            policy = json.loads(self.acquired['context']['policy']['raw_utf8'])
            allowed = [r for r in refs if self._allowed(self.refs[r]['record'], policy)]
            fetched = {}
            uncached = [r for r in allowed if r not in self.cache]
            if uncached:
                self.delta['physical_tools'] += 1
                fetched = dict(zip(uncached, self.source.read([self.refs[r]['record'] for r in uncached])))
                for row in fetched.values():
                    row['adapter_request_id'] = self.adapter_request_id
            results = [{**((self.cache.get(ref) or fetched[ref]) if ref in allowed else {'status': 'access_denied'}),
                        'cache_hit': ref in allowed and ref in self.cache} for ref in refs]
            for ref in uncached:
                if fetched[ref]['status'] == 'ok':
                    self.cache[ref] = copy.deepcopy(fetched[ref])
            self.delta['logical_tools'] += sum(item['status'] != 'not_attempted' for item in results)
            pack = self.acquired['candidates'][self.binding['parent_asin']]
            items = []
            for ref, result in zip(refs, results):
                item = {**result, 'evidence_ref': ref}
                pack['attempts'][ref] = item
                if item['status'] == 'ok':
                    pack['originals'][ref] = {**item, 'registration': self.refs[ref]['record']}
                items.append({k: v for k, v in item.items() if k != 'source'})
            return {'status': 'ok', 'items': items}
        if operation != 'list_evidence' or not isinstance(arguments, dict) or set(arguments) != {'cursor'}:
            return {'status': 'access_denied'}
        cursor = arguments['cursor']
        if cursor is not None and (not isinstance(cursor, str) or cursor not in self.cursors):
            return {'status': 'access_denied'}
        offset = 0 if cursor is None else self.cursors[cursor]
        parent, batch = self.binding['parent_asin'], self.binding['sim_batch_id']
        self.delta['physical_tools'] += 1
        context, registrations, scope_observation = self.source.list(parent, batch, binding=self.binding)
        if not self.acquired['context']:
            self.delta['logical_tools'] += len(context)
            self.acquired['context'] = context
        policy = json.loads(context['policy']['raw_utf8'])
        if policy['read_principal_id'] != self.binding['principal_id']:
            return {'status': 'access_denied'}
        done = offset + 32 >= len(registrations)
        pack = self.acquired['candidates'].setdefault(parent, {'registrations': [], 'enumeration_complete': False,
            'originals': {}, 'attempts': {}, 'enumeration_observations': []})
        pack['enumeration_complete'] = pack['enumeration_complete'] or done
        pack['enumeration_observations'].append({**scope_observation, 'terminal': done, 'offset': offset})
        entries = []
        for item in registrations[offset:offset + 32]:
            row = {key: value for key, value in item['record'].items() if key != 'sequence'}
            row['evidence_ref'] = digest(self.scope_seed + encoded(row))
            item['evidence_ref'] = row['evidence_ref']
            if row['evidence_ref'] not in self.refs:
                pack['registrations'].append(item)
            self.refs[row['evidence_ref']] = item
            entries.append(row)
        self.delta['logical_tools'] += max(1, len(entries))
        next_cursor = None if done else digest(self.scope_seed + b'cursor' + str(offset + 32).encode())
        if next_cursor:
            self.cursors[next_cursor] = offset + 32
        return {'status': 'ok', 'scope_handle': digest(self.scope_seed), 'entries': entries,
                'enumeration_complete': done, 'next_cursor': next_cursor}

    def _allowed(self, registration, policy):
        kind = registration['target_kind']
        permitted = kind in policy['read_scope']['target_kinds'] or (
            kind == 'change_action' and 'material' in policy['read_scope']['target_kinds']
            and policy['status_change_authority'] == 'issuer_own_lineage_only')
        if kind == 'material':
            known = self.source.material_kinds.get((registration['target_id'], registration['version']))
            possible = {known} if known is not None else set(next((row['material_kinds'] for row in policy['issuers']
                if row['issuer_id'] == registration['issuer_id']), []))
            permitted = permitted and bool(possible) and possible <= set(policy['read_scope']['material_kinds'])
        return permitted and not any(row['principal_id'] == self.binding['principal_id']
            and row['target_kind'] == kind and row['target_id'] == registration['target_id']
            and row['version'] == registration['version'] for row in policy.get('read_denials', []))

    def audit_view(self):
        if self.root_budget is not None:
            with self.root_budget.lock:
                self.root_budget._tick()
                self.usage = self.root_budget.usage.copy()
        return copy.deepcopy({'acquired': self.acquired, 'setup': self.source.setup,
                              'receipts': self.receipts, 'usage': self.usage, 'provenance': self.provenance,
                              'unsettled_reservations': self.unsettled_reservations})
