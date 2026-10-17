"""Handwritten public evidence, not generated SIM or a four-state oracle."""
import hashlib
import json
from pathlib import Path


def wire(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class EvidenceFixture:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.parent = 'PUBLIC-A'
        self.batch = 'BATCH-A'
        self.rows = {name: [] for name in ('batches.jsonl', 'events.jsonl', 'materials.jsonl', 'actions.jsonl')}
        self.add('batches.jsonl', {'schema_version': 'sim-batch-1.0.0', 'source': 'SIM',
            'parent_asin': self.parent, 'sim_batch_id': self.batch, 'version': 1,
            'issuer_id': 'SIM-PRODUCER', 'created_at_ms': 1})
        self.policy = {'schema_version': 'sim-policy-1.0.0', 'source': 'SIM', 'policy_id': 'PUBLIC-POLICY',
            'identity_mode': 'simulated_allowlist_no_crypto', 'registrar_id': 'SIM-REGISTRY',
            'read_principal_id': 'SIM-VERIFIER', 'issuers': [{'issuer_id': 'SIM-PRODUCER',
                'may_create_batch': True, 'event_stages': [], 'material_kinds': []}],
            'read_scope': {'target_kinds': ['batch', 'event', 'material'], 'material_kinds': [],
                           'scope': 'current_snapshot_only'}, 'status_change_authority': 'issuer_own_lineage_only'}
        self.registrations = []
        self.register_all()
        self.seal()

    def add(self, name, row):
        self.rows[name].append(row)
        return row

    def register_all(self):
        self.registrations = []
        for name, kind, identity in [('batches.jsonl', 'batch', 'sim_batch_id'),
                ('events.jsonl', 'event', 'event_id'), ('materials.jsonl', 'material', 'evidence_id'),
                ('actions.jsonl', 'change_action', 'action_id')]:
            for row in self.rows[name]:
                self.registrations.append({'schema_version': 'sim-scenario-registration-1.0.0' if kind == 'change_action' else 'sim-registration-1.0.0', 'source': 'SIM',
                    'registry_backend': 'local_sim_registry', 'registration_id': 'REG-' + row[identity] + str(row.get('version', 1)),
                    'target_kind': kind, 'target_id': row[identity], 'version': row.get('version', 1),
                    'parent_asin': row['parent_asin'], 'sim_batch_id': row['sim_batch_id'],
                    'event_id': row.get('event_id'), 'issuer_id': row.get('issuer_id', row.get('actor_id')),
                    'content_sha256': sha(wire(row)), 'registrar_id': 'SIM-REGISTRY',
                    'receipt_status': 'accepted', 'registered_at_ms': row.get('issued_at_ms', row.get('event_end_ms', 1)) + 1,
                    'sequence': len(self.registrations) + 1})

    def seal(self, snapshot_updates=None):
        files = {name: b''.join(wire(row) + b'\n' for row in rows) for name, rows in self.rows.items()}
        if not getattr(self, 'is_quality', False):
            files['change-actions.jsonl'] = files.pop('actions.jsonl')
        files['registrations.jsonl'] = b''.join(wire(row) + b'\n' for row in self.registrations)
        files['policy.json'] = wire(self.policy) + b'\n'
        components = {name: {'bytes': len(raw), 'records': raw.count(b'\n'), 'sha256': sha(raw)} for name, raw in files.items()}
        self.snapshot = {'schema_version': 'sim-scenario-snapshot-1.0.0', 'source': 'SIM',
            'verify_at_ms': 1000, 'sealed_at_ms': 900, 'cutoff_sequence': len(self.registrations),
            'policy_id': self.policy['policy_id'], 'components': components}
        self.snapshot.update(snapshot_updates or {})
        if getattr(self, 'is_quality', False):
            self.snapshot.update(schema_version='quality-snapshot-0.1.0', read_principal_id='SIM-VERIFIER',
                rules=self.rules, contract_sha256=sha(wire(self.rules)),
                scope_sha256={p: sha(wire([r for r in self.registrations if r['parent_asin'] == p]))
                              for p in ('PUBLIC-A', 'PUBLIC-B')})
            self.snapshot['snapshot_id'] = 'qf_' + sha(b'Thesis-quality-fusion:snapshot\0' + wire(self.snapshot))
        else:
            self.snapshot['snapshot_id'] = 'n_' + sha(b'Thesis-SIM-1:scenario_snapshot\0' + wire(self.snapshot))
        files['snapshot.json'] = wire(self.snapshot) + b'\n'
        for name, raw in files.items():
            (self.root / name).write_bytes(raw)
        self.snapshot_ref = {'path': str(self.root / 'snapshot.json'), 'bytes': len(files['snapshot.json']),
                             'sha256': sha(files['snapshot.json'])}

    def binding(self, **changes):
        return {'run_id': 'PUBLIC-RUN', 'root_task_id': 'PUBLIC-ROOT', 'parent_asin': self.parent,
            'sim_batch_id': self.batch, 'snapshot_id': self.snapshot['snapshot_id'], 'principal_id': 'SIM-VERIFIER',
            'verify_at_ms': 1000, 'arm': 'necessary', 'necessary_clauses': ['c1', 'c2'], **changes}

    def session(self, **changes):
        from evidence_access import EvidenceSession, LocalEvidenceSource
        options = {'limits': {'logical_tools': 4096, 'physical_tools': 512, 'candidates': 64,
                             'retries': 2, 'elapsed_ms': 600000},
                   'final_reserve': {'logical_tools': 2, 'physical_tools': 1, 'elapsed_ms': 1}}
        options.update(changes)
        return EvidenceSession(self.binding(), LocalEvidenceSource(self.snapshot_ref), **options)

    def normal(self):
        stages = ('harvest', 'packaging', 'storage', 'inspection', 'transport', 'retail')
        actors = ('SIM-PRODUCER', 'SIM-PACKER', 'SIM-WAREHOUSE', 'SIM-LAB', 'SIM-CARRIER', 'SIM-RETAIL')
        for index, (stage, actor) in enumerate(zip(stages, actors)):
            self.add('events.jsonl', {'schema_version': 'sim-event-1.0.0', 'source': 'SIM',
                'parent_asin': self.parent, 'sim_batch_id': self.batch, 'version': 1,
                'event_id': 'E-' + stage, 'stage': stage, 'actor_id': actor,
                'event_start_ms': 10 + index * 20, 'event_end_ms': 20 + index * 20 if index < 5 else 110,
                'predecessor_event_ids': ['E-' + stages[index - 1]] if index else []})
        for kind, actor, event, issued, facts in [
            ('inspection_sample', 'SIM-SAMPLER', 'inspection', 82, {'sample_id': 'SAMPLE-A', 'sampled_at_ms': 72}),
            ('inspection_report', 'SIM-LAB', 'inspection', 84, {'sample_id': 'SAMPLE-A', 'test_scope': ['SIM-Q1'],
                'test_started_at_ms': 74, 'test_completed_at_ms': 78, 'conclusion': 'pass'}),
            ('retail_status', 'SIM-RETAIL', 'retail', 112, {'observed_at_ms': 110, 'location_id': 'RETAIL-A',
                'status': 'on_sale', 'stock_units': 75, 'unit': 'SIM_PACK'})]:
            row = {'schema_version': 'sim-material-1.0.0', 'source': 'SIM', 'parent_asin': self.parent,
                'sim_batch_id': self.batch, 'version': 1, 'evidence_id': 'D-' + kind, 'kind': kind,
                'issuer_id': actor, 'event_id': 'E-' + event, 'issued_at_ms': issued, 'facts': facts,
                'temporal_mode': 'current_assertion' if kind == 'retail_status' else 'historical_fact'}
            if kind == 'retail_status':
                row.update(valid_from_ms=100, valid_to_ms=2000)
            self.add('materials.jsonl', row)
        self.policy['issuers'] = [{'issuer_id': actor, 'may_create_batch': actor == 'SIM-PRODUCER',
            'event_stages': [stage for stage, source in zip(stages, actors) if source == actor],
            'material_kinds': [row['kind'] for row in self.rows['materials.jsonl'] if row['issuer_id'] == actor]}
            for actor in (*actors, 'SIM-SAMPLER')]
        self.policy['read_scope']['material_kinds'] = [row['kind'] for row in self.rows['materials.jsonl']]
        self.register_all()
        self.seal()
        return self

    def revise(self, conclusion='fail'):
        import copy
        report = next(r for r in self.rows['materials.jsonl'] if r['kind'] == 'inspection_report')
        newer = copy.deepcopy(report)
        newer.update(version=2, issued_at_ms=300)
        newer['facts']['conclusion'] = conclusion
        self.add('materials.jsonl', newer)
        self.add('actions.jsonl', {'schema_version': 'sim-change-action-1.0.0', 'source': 'SIM',
            'action_id': 'ACTION-REVISE', 'action_type': 'supersedes',
            'target_kind': 'material', 'target_id': report['evidence_id'], 'target_version': 2,
            'supersedes_version': 1, 'parent_asin': self.parent, 'sim_batch_id': self.batch,
            'event_id': report['event_id'], 'issuer_id': 'SIM-LAB', 'issued_at_ms': 400, 'effective_from_ms': 400})
        self.register_all()
        self.seal()
        return self

    def revoke(self, version=1, effective=400):
        self.add('actions.jsonl', {'schema_version': 'sim-change-action-1.0.0', 'source': 'SIM',
            'action_id': 'ACTION-REVOKE', 'action_type': 'revokes', 'target_kind': 'material',
            'target_id': 'D-inspection_report', 'target_version': version, 'supersedes_version': None,
            'parent_asin': self.parent, 'sim_batch_id': self.batch, 'event_id': 'E-inspection',
            'issuer_id': 'SIM-LAB', 'issued_at_ms': 400, 'effective_from_ms': effective})
        self.register_all()
        self.seal()
        return self

    def quality(self):
        self.normal()
        additions = [
            ('harvest_record', 'harvest', 'SIM-PRODUCER', 22, {'origin_area_id': 'AREA-1'}),
            ('packaging_binding', 'packaging', 'SIM-PACKER', 42, {'package_condition': 'intact'}),
            ('storage_log', 'storage', 'SIM-WAREHOUSE', 62, {'segments': []}),
            ('transport_dispatch', 'transport', 'SIM-CARRIER', 101, {'transport_segment_id': 'SEGMENT-A',
                'from_location_id': 'WAREHOUSE-A', 'to_location_id': 'RETAIL-A', 'quantity_units': 100,
                'unit': 'SIM_PACK', 'departed_at_ms': 90}),
            ('transport_receipt', 'transport', 'SIM-RECEIVER', 102, {'transport_segment_id': 'SEGMENT-A',
                'from_location_id': 'WAREHOUSE-A', 'to_location_id': 'RETAIL-A', 'quantity_units': 100,
                'unit': 'SIM_PACK', 'arrived_at_ms': 100, 'handover_status': 'accepted'})]
        self.policy['issuers'].append({'issuer_id': 'SIM-RECEIVER', 'may_create_batch': False,
                                      'event_stages': [], 'material_kinds': []})
        for kind, stage, actor, issued, facts in additions:
            self.add('materials.jsonl', {'schema_version': 'sim-material-1.0.0', 'source': 'SIM',
                'parent_asin': 'PUBLIC-A', 'sim_batch_id': 'BATCH-A', 'version': 1,
                'evidence_id': 'D-' + kind, 'kind': kind, 'issuer_id': actor, 'event_id': 'E-' + stage,
                'issued_at_ms': issued, 'temporal_mode': 'historical_fact', 'facts': facts})
            next(row for row in self.policy['issuers'] if row['issuer_id'] == actor)['material_kinds'].append(kind)
            self.policy['read_scope']['material_kinds'].append(kind)
        next(row for row in self.rows['materials.jsonl'] if row['kind'] == 'retail_status')['valid_to_ms'] = 1225
        def second(value):
            if isinstance(value, dict):
                return {key: second(item) for key, item in value.items()}
            if isinstance(value, list):
                return [second(item) for item in value]
            if isinstance(value, str):
                for left, right in [('PUBLIC-A', 'PUBLIC-B'), ('BATCH-A', 'BATCH-B'), ('SAMPLE-A', 'SAMPLE-B'),
                                    ('E-', 'E-B-'), ('D-', 'D-B-'), ('RETAIL-A', 'RETAIL-B'), ('SEGMENT-A', 'SEGMENT-B')]:
                    value = value.replace(left, right)
            return value
        for name in self.rows:
            self.rows[name].extend(second(row) for row in self.rows[name][:])
        retail_b = next(row for row in self.rows['materials.jsonl'] if row['parent_asin'] == 'PUBLIC-B' and row['kind'] == 'retail_status')
        retail_b['valid_to_ms'] = 4600
        retail_b['facts']['stock_units'] = 100
        self.rules = {'attribute': 'retail_stock', 'source': 'experiment_design', 'weight': 1, 'stock_scale': 100,
            'C_slots': ['retail_status'], 'A_checks': ['same_parent_batch', 'same_location_unit'],
            'main_alpha': .5, 'main_beta': [.25, .5, .25], 'alpha_grid': [.25, .5, .75],
            'beta_T_grid': [.25, .5, .75], 'score_decimals': 12}
        self.is_quality = True
        self.register_all()
        self.seal()
        return self

    def fusion_binding(self):
        parents, scores = ['PUBLIC-A', 'PUBLIC-B'], [.9, .6]
        return {'schema_version': 'fusion-binding-0.1.0', 'task_id': 'PUBLIC-ROOT', 'C': parents,
            'C_sha256': sha(wire(parents)), 'H_sha256': sha(b'PUBLIC-H'), 'base_scores': scores,
            'base_score_version': 'public-worked-example', 'base_score_sha256': sha(wire(list(zip(parents, scores)))),
            'snapshot_id': self.snapshot['snapshot_id'], 'verify_at_ms': 1000, 'principal_id': 'SIM-VERIFIER',
            'contract_sha256': sha(wire(self.rules)), 'K': 10, 'alpha': .5, 'beta': [.25, .5, .25], 'mode': 'full',
            'preference': {'source': 'experiment_design', 'dimensions': ['retail_stock'], 'weights': {'retail_stock': 1}}}

    def joint(self):
        from joint_access import JointSession
        return JointSession({'root_task_id': 'PUBLIC-ROOT'},
            {'C': ['PUBLIC-A', 'PUBLIC-B'], 'b': [.9, .6], 'batches': ['BATCH-A', 'BATCH-B'],
             'background_statistics': [{}, {}]},
            [{'parent_asin': p, 'title': p, 'crop': 'rice'} for p in ('PUBLIC-A', 'PUBLIC-B')],
            {'arm': 'quality', 'request': {'design_text': 'PUBLIC', 'necessary_clauses': []}}, 'PUBLIC-HANDLE')


def acquire_all(session):
    entries = []
    cursor = None
    while True:
        page = session.dispatch('list_evidence', {'cursor': cursor})
        if page['status'] != 'ok':
            raise AssertionError(page['status'])
        entries.extend(page['entries'])
        cursor = page['next_cursor']
        if cursor is None:
            break
    for offset in range(0, len(entries), 32):
        result = session.dispatch('read_evidence', {'evidence_refs': [r['evidence_ref'] for r in entries[offset:offset + 32]]})
        if result['status'] != 'ok':
            raise AssertionError(result['status'])
    return entries
