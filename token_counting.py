"""Full-input receipts, never local text estimates or implicit supplier calls."""
import copy
import json
from pathlib import Path
import argparse
import os
import time

from provider_openai import canonical, send_count, sha, verify_prepared

BINDING_KEYS = ('prepared_id', 'wire_sha256', 'count_payload_sha256', 'model_id', 'project_id',
                'mapper_version', 'tool_schema_sha256', 'role_schema_sha256')
ROOT = Path(__file__).resolve().parent


def project_path(value):
    path = Path(value).absolute()
    if not path.resolve().is_relative_to(ROOT):
        raise ValueError('outside_project')
    for parent in (path, *path.parents):
        if parent.exists() and (parent.is_symlink() or parent.is_junction()
                or getattr(parent.stat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError('reparse_path')
    return path.resolve()


def write_new(path, value):
    with project_path(path).open('x', encoding='utf-8') as stream:
        stream.write(canonical(value) + '\n')


def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []


def append(path, value):
    with project_path(path).open('a', encoding='utf-8') as stream:
        stream.write(canonical(value) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def validate_manifest(manifest):
    if (manifest['schema_version'] != 'openai-count-manifest-0.1.0' or manifest['complete'] is not True
            or manifest['manifest_id'] != sha({k: v for k, v in manifest.items() if k != 'manifest_id'})):
        raise ValueError('invalid_manifest')
    refs, plan, entries = manifest['references'], manifest['plan'], manifest['entries']
    per_root = {}
    for ref in refs:
        per_root[ref['run_id']] = per_root.get(ref['run_id'], 0) + 1
    if any(n > 17 for n in per_root.values()) or len(entries) > 108800:
        raise ValueError('count_planning_cap_exceeded')
    if {r['run_id'] for r in refs} != {r['run_id'] for r in plan['roots'] if r['method'] in ('S', 'M')}:
        raise ValueError('incomplete_model_root_coverage')
    if plan['scope'] == 'T0_controlled_catalog':
        roots = plan['roots']
        accounts, views = {r.get('account_id') for r in roots}, {r.get('view_id') for r in roots}
        if (len(roots) != 9600 or len(accounts) != 320 or len(views) != 10 or None in accounts or None in views
                or {(r['account_id'], r['view_id'], r['method']) for r in roots}
                != {(a, v, m) for a in accounts for v in views for m in ('R', 'S', 'M')}):
            raise ValueError('incomplete_T0_scope')
    if (sorted(canonical({k: v for k, v in r.items() if k != 'prepared_id'}) for r in refs)
            != sorted(canonical(e) for e in plan['expected']) or set(entries) != {r['prepared_id'] for r in refs}):
        raise ValueError('incomplete_catalog')
    for key, prepared in entries.items():
        if not verify_prepared(prepared) or key != prepared['prepared_id'] or prepared['project_id'] != plan['project_id']:
            raise ValueError('invalid_prepared')
    return manifest


def export_manifest(source):
    rows = [json.loads(line) for line in project_path(source).read_text(encoding='utf-8').splitlines()]
    plan, entries, references = rows[0]['plan'], {}, []
    if (plan['schema_version'] != 'openai-count-plan-0.1.0' or plan['scope'] not in ('public_fixture', 'T0_controlled_catalog')
            or len({r['run_id'] for r in plan['roots']}) != len(plan['roots'])):
        raise ValueError('invalid_plan')
    roots = {r['run_id']: r['method'] for r in plan['roots']}
    if any(m not in ('R', 'S', 'M') for m in roots.values()):
        raise ValueError('invalid_method')
    for prepared in rows[1:]:
        source = prepared['source']
        if (not verify_prepared(prepared) or prepared['project_id'] != plan['project_id']
                or roots.get(source['run_id']) not in ('S', 'M')):
            raise ValueError('invalid_prepared')
        entries.setdefault(prepared['prepared_id'], prepared)
        references.append({**source, 'prepared_id': prepared['prepared_id']})
    expected = sorted(canonical(e) for e in plan['expected'])
    actual = sorted(canonical({k: v for k, v in r.items() if k != 'prepared_id'}) for r in references)
    if expected != actual or len(actual) != len(set(actual)):
        raise ValueError('incomplete_catalog')
    result = {'schema_version': 'openai-count-manifest-0.1.0', 'plan': plan, 'entries': entries,
              'references': references, 'complete': True, 'provider_requests_sent': 0}
    result['manifest_id'] = sha(result)
    return validate_manifest(result)


class InputCounter:
    def __init__(self, project_id, *, sender=None, fixture_count=None, directory=None, clock=None,
                 https_factory=None, credential=None, credential_path=None, manifest_path=None):
        self.project_id = project_id
        self.sender = sender
        self.fixture_count = fixture_count
        self.receipts = {}
        self.directory = project_path(directory) if directory is not None else None
        self.clock = clock or (lambda: int(time.time() * 1000))
        self.https_factory, self.credential = https_factory, credential
        self.credential_path = credential_path
        self.manifest_path = project_path(manifest_path) if manifest_path is not None else (
            self.directory / 'manifest.json' if self.directory is not None else None)

    def _state(self):
        manifest = validate_manifest(json.loads(self.manifest_path.read_bytes()))
        journal = read_lines(self.directory / 'count-journal.jsonl')
        intents = {r['attempt_id']: r for r in journal if r['kind'] == 'intent'}
        results = {r['attempt_id']: r for r in journal if r['kind'] == 'result'}
        if (len(intents) != sum(r['kind'] == 'intent' for r in journal)
                or len(results) != sum(r['kind'] == 'result' for r in journal)
                or len(journal) != len(intents) + len(results) or not set(results) <= set(intents)):
            raise ValueError('invalid_count_ledger')
        for index, (key, intent) in enumerate(intents.items()):
            if key != manifest['manifest_id'] + ':count:' + str(index) or intent['manifest_id'] != manifest['manifest_id']:
                raise ValueError('invalid_count_sequence')
        receipts = read_lines(self.directory / 'count-receipts.jsonl')
        if len({r['receipt_id'] for r in receipts}) != len(receipts):
            raise ValueError('duplicate_count_receipt')
        for receipt in receipts:
            intent, result = intents[receipt['attempt_id']], results[receipt['attempt_id']]
            prepared = manifest['entries'][receipt['prepared_id']]
            fixture_origin = intent['transport_origin'] in ('injected_sender', 'injected_https')
            if (receipt['receipt_id'] != sha({k: v for k, v in receipt.items() if k != 'receipt_id'})
                    or result.get('receipt') != receipt or intent['manifest_id'] != manifest['manifest_id']
                    or receipt['manifest_id'] != manifest['manifest_id']
                    or any(receipt[k] != prepared[k] or receipt[k] != intent[k] for k in BINDING_KEYS)
                    or receipt['basis'] != intent['basis'] or receipt['returned_model'] is not None
                    or receipt['basis'] != ('fixture' if fixture_origin else 'official_input_tokens')
                    or receipt['provider_requests_sent'] != int(not fixture_origin)
                    or intent['permit_scope'] != ('fixture_count' if fixture_origin else 'external_count')
                    or type(receipt['input_tokens']) is not int or receipt['input_tokens'] < 0
                    or receipt['raw_response']['body'] != {'object': 'response.input_tokens', 'input_tokens': receipt['input_tokens']}):
                raise ValueError('unregistered_receipt')
            if not fixture_origin:
                approval = json.loads(project_path(intent['authorization_ref']).read_bytes())
                if (intent['transport_origin'] != 'stdlib_https' or approval.get('approved') is not True
                        or approval.get('schema_version') != 'openai-count-execution-authorization-0.1.0'
                        or approval.get('permit_sha256') != intent['permit_sha256']
                        or approval.get('fee_evidence_sha256') != intent['fee_evidence_sha256']):
                    raise ValueError('unregistered_official_receipt')
        return manifest, intents, results, receipts

    def count(self, prepared, *, authorization):
        if not verify_prepared(prepared) or prepared['project_id'] != self.project_id:
            return {'status': 'invalid_prepared', 'input_tokens': None, 'basis': None}
        if authorization is not None:
            if self.directory is None:
                return {'status': 'permission_denied', 'input_tokens': None, 'basis': None}
            lock = self.directory / 'count-inflight.json'
            try:
                with lock.open('x', encoding='utf-8') as stream:
                    stream.write(canonical({'pid': os.getpid(), 'prepared_id': prepared['prepared_id']}))
            except FileExistsError:
                return {'status': 'count_inflight', 'input_tokens': None, 'basis': None}
            try:
                return self._external(prepared, authorization)
            finally:
                lock.unlink()
        if self.fixture_count is not None:
            if type(self.fixture_count) is not int or self.fixture_count < 0:
                return {'status': 'invalid_count', 'input_tokens': None, 'basis': 'fixture'}
            receipt = {k: prepared[k] for k in BINDING_KEYS}
            receipt.update(schema_version='openai-count-receipt-0.1.0', status='counted',
                input_tokens=self.fixture_count, basis='fixture', returned_model=None,
                provider_requests_sent=0, raw_response={'object': 'response.input_tokens', 'input_tokens': self.fixture_count})
            receipt['receipt_id'] = sha(receipt)
            self.receipts[receipt['receipt_id']] = copy.deepcopy(receipt)
            return copy.deepcopy(receipt)
        if self.directory is not None:
            try:
                _, _, _, receipts = self._state()
                for receipt in receipts:
                    if all(receipt[k] == prepared[k] for k in BINDING_KEYS):
                        return copy.deepcopy(receipt)
            except (ValueError, TypeError, KeyError, OSError):
                return {'status': 'invalid_receipt', 'input_tokens': None, 'basis': None}
        return {'status': 'count_missing', 'input_tokens': None, 'basis': None}

    def _external(self, prepared, permit):
        denied = {'status': 'permission_denied', 'input_tokens': None, 'basis': None}
        try:
            manifest, intents, results, receipts = self._state()
            rate, now = permit['rate'], self.clock()
            fixture_transport = self.sender is not None or self.https_factory is not None
            scope, basis = ('fixture_count', 'fixture') if fixture_transport else ('external_count', 'official_input_tokens')
            if (permit['schema_version'] != 'openai-count-permit-0.1.0' or permit['enabled'] is not True
                    or permit['scope'] != scope
                    or not permit['authorization_ref'] or permit['project_id'] != self.project_id
                    or permit['model_id'] != prepared['model_id'] or permit['manifest_id'] != manifest['manifest_id']
                    or permit['endpoint'] != 'https://api.openai.com/v1/responses/input_tokens'
                    or project_path(permit['journal_path']) != self.directory / 'count-journal.jsonl'
                    or prepared['prepared_id'] not in manifest['entries']
                    or any(type(permit[k]) is not int for k in ('max_calls', 'started_ms', 'deadline_ms', 'budget_microusd'))
                    or not 0 < permit['max_calls'] <= min(108800, len(manifest['entries']))
                    or not 0 <= now - permit['started_ms'] < permit['deadline_ms'] - permit['started_ms'] <= 86400000
                    or rate['currency'] != 'USD' or rate['unit'] != 'request' or rate['basis'] != ('fixture' if fixture_transport else 'official_docs')
                    or len(rate['evidence_sha256']) != 64
                    or any(type(rate[k]) is not int or rate[k] < 0 for k in ('success_microusd', 'failure_microusd'))):
                return denied
            if not fixture_transport:
                approval = json.loads(project_path(permit['authorization_ref']).read_bytes())
                roots = manifest['plan']['roots']
                if (approval.get('schema_version') != 'openai-count-execution-authorization-0.1.0'
                        or approval.get('approved') is not True or approval.get('permit_sha256') != sha(permit)
                        or approval.get('fee_evidence_sha256') != rate['evidence_sha256']
                        or manifest['plan']['scope'] != 'T0_controlled_catalog' or len(roots) != 9600
                        or any(sum(r['method'] == method for r in roots) != 3200 for method in ('R', 'S', 'M'))
                        or self.credential_path is None or project_path(self.credential_path) != project_path(permit['credential_path'])):
                    return denied
            for receipt in receipts:
                if all(receipt[k] == prepared[k] for k in BINDING_KEYS):
                    return copy.deepcopy(receipt)
            held = max(rate['success_microusd'], rate['failure_microusd'])
            spent = sum(results[key]['cost_microusd'] if key in results and results[key]['cost_microusd'] is not None
                        else intent['held_microusd'] for key, intent in intents.items())
            if any(key not in results or results[key]['status'] != 'counted' for key in intents):
                return {'status': 'count_stage_halted', 'input_tokens': None, 'basis': None,
                    'held_unknown_microusd': sum(intent['held_microusd'] for key, intent in intents.items()
                        if key not in results or results[key]['cost_microusd'] is None)}
            if (len(intents) >= permit['max_calls'] or spent + held > permit['budget_microusd']
                    or len(prepared['count_utf8'].encode('utf-8')) > 16 * 1024**2):
                return denied
        except (ValueError, TypeError, KeyError, AttributeError, OSError):
            return denied
        attempt = manifest['manifest_id'] + ':count:' + str(len(intents))
        intent = {k: prepared[k] for k in BINDING_KEYS}
        intent.update(kind='intent', attempt_id=attempt, manifest_id=manifest['manifest_id'], basis=basis,
            held_microusd=held, started_ms=now, permit_sha256=sha(permit), permit_scope=scope,
            transport_origin='injected_sender' if self.sender is not None else 'injected_https' if self.https_factory is not None else 'stdlib_https',
            authorization_ref=permit['authorization_ref'], fee_evidence_sha256=rate['evidence_sha256'])
        journal_path = self.directory / 'count-journal.jsonl'
        append(journal_path, intent)
        raw, status, cost = None, 'count_failed', None
        try:
            deadline = min(now + 30000, permit['deadline_ms'])
            if self.sender is not None:
                raw = self.sender(prepared['count_utf8'], deadline_ms=deadline)
            else:
                credential = self.credential if fixture_transport else project_path(self.credential_path).read_text(encoding='utf-8').strip()
                raw = send_count(prepared['count_utf8'], deadline_ms=deadline, credential=credential,
                                 clock=self.clock, connection_factory=self.https_factory)
            body = raw['body']
            cost = None if 'read_error' in raw else rate['failure_microusd']
            if (raw.get('boundary_error') or raw['status_code'] != 200 or set(body) != {'object', 'input_tokens'}
                    or body['object'] != 'response.input_tokens' or type(body['input_tokens']) is not int
                    or body['input_tokens'] < 0 or self.clock() > min(now + 30000, permit['deadline_ms'])
                    or len(canonical(raw).encode('utf-8')) > 1024**2):
                raise ValueError('invalid_or_late_count')
            status, cost = 'counted', rate['success_microusd']
            receipt = {k: prepared[k] for k in BINDING_KEYS}
            receipt.update(schema_version='openai-count-receipt-0.1.0', status=status, basis=basis,
                input_tokens=body['input_tokens'], returned_model=None, manifest_id=manifest['manifest_id'],
                attempt_id=attempt, provider_requests_sent=int(not fixture_transport), raw_response=raw, counted_at_ms=self.clock())
            receipt['receipt_id'] = sha(receipt)
        except (ValueError, TypeError, KeyError, OSError, TimeoutError) as exc:
            receipt = None
            raw = raw if raw is not None else {'exception': str(exc)}
        append(journal_path, {'kind': 'result', 'attempt_id': attempt, 'status': status,
            'cost_microusd': cost, 'receipt': receipt, 'raw_response': raw, 'finished_ms': self.clock()})
        if receipt is not None:
            append(self.directory / 'count-receipts.jsonl', receipt)
            return copy.deepcopy(receipt)
        return {'status': status, 'input_tokens': None, 'basis': basis, 'raw_response': raw,
                'provider_requests_sent': int(not fixture_transport)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export')
    export.add_argument('--prepared', required=True)
    export.add_argument('--output', required=True)
    imported = commands.add_parser('import')
    imported.add_argument('--manifest', required=True)
    imported.add_argument('--receipts', required=True)
    imported.add_argument('--output', required=True)
    counted = commands.add_parser('count')
    counted.add_argument('--manifest', required=True)
    counted.add_argument('--permit', required=True)
    counted.add_argument('--journal', required=True)
    counted.add_argument('--credential-file')
    args = parser.parse_args(argv)
    try:
        if args.command == 'export':
            manifest = export_manifest(args.prepared)
            write_new(args.output, manifest)
            summary = {'status': 'exported', 'manifest_id': manifest['manifest_id'],
                'references': len(manifest['references']), 'unique': len(manifest['entries']), 'provider_requests_sent': 0}
        elif args.command == 'import':
            manifest_path, receipts_path = project_path(args.manifest), project_path(args.receipts)
            manifest = validate_manifest(json.loads(manifest_path.read_bytes()))
            if receipts_path != manifest_path.parent / 'count-receipts.jsonl':
                raise ValueError('unregistered_receipt_path')
            counter = InputCounter(manifest['plan']['project_id'], directory=manifest_path.parent, manifest_path=manifest_path)
            _, _, _, receipts = counter._state()
            by_prepared = {r['prepared_id']: r for r in receipts}
            missing = [key for key in manifest['entries'] if key not in by_prepared]
            totals = {r['run_id']: 0 for r in manifest['plan']['roots']}
            for ref in manifest['references']:
                i = by_prepared.get(ref['prepared_id'], {}).get('input_tokens')
                root = ref['run_id']
                totals[root] = None if i is None or totals[root] is None else totals[root] + i
            official = (manifest['plan']['scope'] == 'T0_controlled_catalog' and bool(manifest['entries']) and not missing
                        and all(r['basis'] == 'official_input_tokens' for r in receipts))
            summary = {'status': 'incomplete' if missing else 'imported_official' if official else 'imported_fixture',
                'manifest_id': manifest['manifest_id'], 'official_complete': official,
                'references': len(manifest['references']), 'unique': len(manifest['entries']), 'missing': missing,
                'per_root_input_tokens': totals, 'provider_requests_sent': 0}
            write_new(args.output, summary)
        else:
            path = project_path(args.manifest)
            manifest = validate_manifest(json.loads(path.read_bytes()))
            permit = json.loads(project_path(args.permit).read_bytes())
            if project_path(args.journal) != path.parent / 'count-journal.jsonl':
                raise ValueError('journal_mismatch')
            counter = InputCounter(manifest['plan']['project_id'], directory=path.parent,
                                   manifest_path=path, credential_path=args.credential_file)
            summary = {'status': 'counted', 'provider_requests_sent': 0, 'counted': 0}
            for prepared in manifest['entries'].values():
                receipt = counter.count(prepared, authorization=permit)
                summary['provider_requests_sent'] += receipt.get('provider_requests_sent', 0)
                if receipt['status'] != 'counted':
                    summary['status'] = receipt['status']
                    break
                summary['counted'] += 1
        print(canonical(summary))
        return 0 if summary['status'] in ('exported', 'imported_official', 'imported_fixture', 'counted') else 2
    except (ValueError, TypeError, KeyError, IndexError, OSError) as exc:
        print(canonical({'status': 'rejected', 'reason': str(exc), 'provider_requests_sent': 0}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
