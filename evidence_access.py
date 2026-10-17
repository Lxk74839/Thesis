"""Host-bound acquisition of SIM facts; no evaluation data or model access."""
import copy
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

    def list(self, parent, batch):
        raw, origin = self._file(self.snapshot_ref['path'], self.snapshot_ref)
        snapshot = decode(raw)
        context = {'snapshot': {'raw_utf8': raw.decode('utf-8'), 'source': origin}}
        directory = Path(self.snapshot_ref['path']).parent
        registrations = []
        for name, ref in snapshot['components'].items():
            if name not in FILES:
                raise ValueError('source_integrity_error')
            content, source = self._file(directory / name, ref)
            if name == 'materials.jsonl':
                self.material_kinds = {(row['evidence_id'], row['version']): row['kind']
                                       for row in (decode(value) for value in content.splitlines())}
            if name == 'policy.json':
                context['policy'] = {'raw_utf8': content.decode('utf-8'), 'source': source}
            if name in ('actions.jsonl', 'change-actions.jsonl'):
                context['actions_scope'] = {'empty': not content, 'raw_utf8': '' if not content else None,
                                             'source': source}
            if name == 'registrations.jsonl':
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
        return context, registrations

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


class EvidenceSession:
    """The model-facing interface accepts only bound list/read/page operations."""
    version = 'restricted-evidence-0.1.0'

    @staticmethod
    def tool_schemas():
        inputs = [('list_evidence', 'cursor', {'type': ['string', 'null']}),
                  ('read_evidence', 'evidence_refs', {'type': 'array', 'items': {'type': 'string'},
                    'minItems': 1, 'maxItems': 32, 'uniqueItems': True})]
        return [{'name': name, 'version': EvidenceSession.version, 'input_schema': {'type': 'object',
            'properties': {key: shape}, 'required': [key], 'additionalProperties': False}} for name, key, shape in inputs]

    def __init__(self, binding, source, *, limits, final_reserve, joint=None, clock=None, sleeper=time.sleep):
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
        self.started = self.clock()
        self.stopped = None
        self.lock = threading.RLock()
        self.seen_candidates = set()
        self.history = {}
        self.provenance = {}
        self.unsettled_reservations = {}
        for table in (self.limits, self.final_reserve):
            if any(type(value) is not int or value < 0 for value in table.values()):
                raise ValueError('invalid_budget')
        if not {'logical_tools', 'physical_tools', 'elapsed_ms'} <= set(self.final_reserve):
            raise ValueError('missing_final_reserve')

    def dispatch(self, operation, arguments, *, actor_role='host'):
        with self.lock:
            if operation not in ('list_evidence', 'read_evidence', 'candidate_page'):
                return self._execute('denied_operation', {}, actor_role)
            return self._execute(operation, arguments, actor_role)

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

    def _execute(self, operation, arguments, actor_role, retry_of=None):
        before = copy.deepcopy(self.usage)
        operation_binding = copy.deepcopy(self.binding)
        receipt_id = digest(self.scope_seed + str(len(self.receipts)).encode())
        self.adapter_request_id = receipt_id + ':1'
        self.delta = {'logical_tools': 0, 'physical_tools': 0}
        started = self.clock()
        held = self._estimate(operation, arguments)
        admitted = not self.stopped and all(self.usage[key] + held[key] + self.final_reserve[key] <= self.limits[key]
                                           for key in held)
        is_candidate = operation in ('list_evidence', 'read_evidence') and self.binding['parent_asin'] not in self.seen_candidates
        admitted = admitted and self.usage['candidates'] + int(is_candidate) <= self.limits['candidates']
        admitted = admitted and started - self.started + self.final_reserve['elapsed_ms'] <= self.limits['elapsed_ms']
        admitted = admitted and (retry_of is None or self.usage['retries'] < self.limits['retries'])
        if not admitted and not self.stopped:
            self.stopped = 'deadline_exceeded' if started - self.started >= self.limits['elapsed_ms'] else 'budget_exhausted'
        try:
            if admitted and retry_of is not None:
                self.sleeper((1, 2)[min(self.usage['retries'], 1)])
                if self.clock() - self.started + self.final_reserve['elapsed_ms'] > self.limits['elapsed_ms']:
                    self.stopped = 'deadline_exceeded'
                    admitted = False
            result = self._dispatch(operation, arguments) if admitted else {'status': self.stopped or 'budget_exhausted'}
        except (ValueError, KeyError, TypeError, UnicodeError, FileNotFoundError):
            self.stopped = 'source_integrity_error'
            result = {'status': self.stopped}
        except OSError:
            result = {'status': 'io_error'}
        if admitted and result['status'] != 'ok' and not self.delta['logical_tools']:
            self.delta['logical_tools'] = 1
        if self.delta['physical_tools'] and is_candidate:
            self.seen_candidates.add(self.binding['parent_asin'])
            self.usage['candidates'] += 1
        if admitted and retry_of is not None:
            self.usage['retries'] += 1
        for key, value in self.delta.items():
            self.usage[key] += value
        finished = self.clock()
        late = admitted and (finished - self.started > self.limits['elapsed_ms'] or finished - started > 45000)
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
        receipt = {'receipt_id': receipt_id, 'request_id': receipt_id, 'retry_of': retry_of,
            'operation': operation, 'status': result['status'], 'actor_role': actor_role,
            'requested_refs': [ref for ref in arguments.get('evidence_refs', []) if isinstance(ref, str) and ref in self.refs]
                if isinstance(arguments, dict) and isinstance(arguments.get('evidence_refs', []), list) else [],
            'scope_handle': digest(self.scope_seed), 'started_at_ms': started, 'finished_at_ms': finished,
            'late': late, 'usage_delta': self.delta.copy(), 'root_usage_before': before,
            'root_usage_after': self.usage.copy(), 'response_bytes': 0,
            'reservation': {'held': held if admitted else dict.fromkeys(held, 0),
                            'settled': dict.fromkeys(held) if unknown else self.delta.copy(),
                            'released': {key: held[key] - self.delta[key] for key in held} if admitted and not unknown else dict.fromkeys(held, 0),
                            'unresolved': unknown},
            'usage_exact': not self.unsettled_reservations,
            'items': []}
        for item in self.acquired['context'].values():
            item.setdefault('receipt_id', receipt_id)
        for pack in self.acquired['candidates'].values():
            for item in [*pack['registrations'], *pack['originals'].values(), *pack['attempts'].values()]:
                item.setdefault('receipt_id', receipt_id)
        observations = [(kind, item, None) for kind, item in self.acquired['context'].items()
                        if item['receipt_id'] == receipt_id]
        for row in result.get('entries', []):
            observations.append(('registration', self.refs[row['evidence_ref']], row['evidence_ref']))
        pack = self.acquired['candidates'].get(operation_binding['parent_asin'], {})
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
        return result

    def _dispatch(self, operation, arguments):
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
            self.delta['logical_tools'] += len(results)
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
        context, registrations = self.source.list(parent, batch)
        if not self.acquired['context']:
            self.delta['logical_tools'] += len(context)
            self.acquired['context'] = context
        policy = json.loads(context['policy']['raw_utf8'])
        if policy['read_principal_id'] != self.binding['principal_id']:
            return {'status': 'access_denied'}
        done = offset + 32 >= len(registrations)
        pack = self.acquired['candidates'].setdefault(parent, {'registrations': [], 'enumeration_complete': False,
                                                              'originals': {}, 'attempts': {}})
        pack['enumeration_complete'] = pack['enumeration_complete'] or done
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
        return copy.deepcopy({'acquired': self.acquired, 'setup': self.source.setup,
                              'receipts': self.receipts, 'usage': self.usage, 'provenance': self.provenance,
                              'unsettled_reservations': self.unsettled_reservations})
