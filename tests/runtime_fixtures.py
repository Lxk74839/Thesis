"""Public handwritten facts and explicit synthetic limits, never real task data."""
import copy
from pathlib import Path

from evidence_access import EvidenceSession, LocalEvidenceSource, RootBudget, digest, encoded
from joint_access import JointSession
from tests.evidence_fixtures import EvidenceFixture


class ScriptedTransport:
    """Chooses requests only from messages; UTF-8 counts are synthetic test units."""
    def __init__(self, mutate=None, empty_acquisition=False):
        self.requests = []
        self.mutate = mutate
        self.empty_acquisition = empty_acquisition

    def __call__(self, request):
        self.requests.append(copy.deepcopy(request))
        messages = request['messages']
        context_index = max(i for i, m in enumerate(messages) if m['role'] == 'user'
                            and isinstance(m['content'], dict) and 'runtime' in m['content'])
        context = messages[context_index]['content']['runtime']
        kind = request['output_kind']
        calls, data = [], {}
        if kind == 'analysis':
            data = {'necessary_clauses': ['c1', 'c2'], 'observations': []}
        elif kind == 'dispatch':
            data = {'candidate': context['current'], 'to': '单智能体' if context['method'] == 'S' else '生命周期追溯',
                    'claim_ids': ['c1', 'c2']}
        elif kind == 'acquire' and not self.empty_acquisition and context['current'] is not None:
            results = [m['content'] for m in messages[context_index + 1:] if m['role'] == 'tool']
            pages = [r for r in results if 'entries' in r]
            read_refs = {i['evidence_ref'] for r in results for i in r.get('items', [])
                         if i['status'] not in ('io_error', 'not_attempted')}
            if not pages or pages[-1]['next_cursor'] is not None:
                calls = [{'call_id': request['attempt_id'] + ':list', 'name': 'list_evidence',
                          'arguments': {'cursor': pages[-1]['next_cursor'] if pages else None}}]
            else:
                remaining = [e['evidence_ref'] for p in pages for e in p['entries'] if e['evidence_ref'] not in read_refs]
                if remaining:
                    calls = [{'call_id': request['attempt_id'] + ':read', 'name': 'read_evidence',
                              'arguments': {'evidence_refs': remaining[:32]}}]
                else:
                    data = {'done': True}
        elif kind == 'acquire':
            data = {'done': True}
        elif kind == 'draft':
            items = []
            for parent in context['ordered']:
                citations = [f['citation'] for f in context['facts'][parent]]
                reasons = [{'claim_id': 'c1', 'kind': 'inspection_supported', 'value': True, 'unit': None,
                            'text': '检验必要条件有完整有效支持（SIM）。', 'citations': copy.deepcopy(citations)},
                           {'claim_id': 'c2', 'kind': 'on_sale_supported', 'value': True, 'unit': None,
                            'text': '核验时点的在售必要条件有完整有效支持（SIM）。', 'citations': copy.deepcopy(citations)}]
                items.append({'parent_asin': parent, 'sim_batch_id': context['candidate_batches'][parent], 'reasons': reasons})
            previous = context['draft']
            data = {'draft_id': request['run_id'] + (':d1' if previous else ':d0'),
                    'parent_draft_id': previous['draft_id'] if previous else None, 'items': items}
        elif kind == 'verification':
            data = {'issues': []}
        elif kind == 'final_submit':
            data = {'draft_id': context['draft']['draft_id']}
        message = {'role': 'assistant', 'content': None if calls else {'kind': kind, 'data': data}, 'tool_requests': calls}
        raw = {'request_id': request['request_id'], 'model_id': None, 'finish_reason': 'tool_calls' if calls else 'stop',
               'message': message, 'usage': {'input_tokens': len(encoded({'messages': messages, 'tools': request['tools']})),
                   'output_tokens': len(encoded(message)), 'cost_microusd': 0}, 'error': None}
        if self.mutate:
            self.mutate(request, raw, context)
        return raw

    def adapter(self):
        from model_adapter import ModelAdapter
        return ModelAdapter(self, capability_binding={'execution_kind': 'scripted_public', 'model_id': None, 'provenance': 'scripted'})


class RuntimeFixture:
    def __init__(self, root):
        self.root = Path(root)
        self.facts = EvidenceFixture(self.root / 'facts').normal()
        self.parents = ['PUBLIC-A']
        self.scores = [.9]
        self.batches = ['BATCH-A']
        self.counter = 0
        self.now = [0]
        self.history = []

    def candidates(self, parents, scores=None):
        originals = copy.deepcopy(self.facts.rows)
        self.parents = list(parents)
        self.scores = list(scores) if scores is not None else [round(1 - i / 20, 12) for i in range(len(parents))]
        self.batches = ['BATCH-' + p.removeprefix('PUBLIC-') for p in self.parents]
        def renamed(value, parent):
            suffix = parent.removeprefix('PUBLIC-')
            if isinstance(value, dict):
                return {k: renamed(v, parent) for k, v in value.items()}
            if isinstance(value, list):
                return [renamed(v, parent) for v in value]
            if isinstance(value, str):
                for old, new in (('PUBLIC-A', parent), ('BATCH-A', 'BATCH-' + suffix),
                    ('SAMPLE-A', 'SAMPLE-' + suffix), ('E-', 'E-' + suffix + '-'),
                    ('D-', 'D-' + suffix + '-'), ('RETAIL-A', 'RETAIL-' + suffix), ('SEGMENT-A', 'SEGMENT-' + suffix)):
                    value = value.replace(old, new)
            return value
        self.facts.rows = {name: [renamed(row, p) for p in self.parents for row in rows
                                if row['parent_asin'] == 'PUBLIC-A'] for name, rows in originals.items()}
        self.seal()
        return self

    def quality(self, parents=('PUBLIC-A', 'PUBLIC-B'), scores=None):
        self.facts = EvidenceFixture(self.root / 'quality-facts').quality()
        self.candidates(parents, scores)
        stocks = {'PUBLIC-A': 75, 'PUBLIC-B': 100, 'PUBLIC-HI': 0, 'PUBLIC-LO': 0}
        for row in self.facts.rows['materials.jsonl']:
            if row['kind'] == 'retail_status':
                row['facts']['stock_units'] = stocks.get(row['parent_asin'], 75)
                row['valid_to_ms'] = 4600 if row['parent_asin'] == 'PUBLIC-B' else 1225
        self.seal()
        return self

    def seal(self):
        self.facts.register_all()
        self.facts.seal()
        if getattr(self.facts, 'is_quality', False):
            snapshot = copy.deepcopy(self.facts.snapshot)
            snapshot['scope_sha256'] = {p: digest(encoded([r for r in self.facts.registrations if r['parent_asin'] == p]))
                                        for p in self.parents}
            snapshot.pop('snapshot_id')
            snapshot['snapshot_id'] = 'qf_' + digest(b'Thesis-quality-fusion:snapshot\0' + encoded(snapshot))
            raw = encoded(snapshot) + b'\n'
            (self.facts.root / 'snapshot.json').write_bytes(raw)
            self.facts.snapshot = snapshot
            self.facts.snapshot_ref = {'path': str(self.facts.root / 'snapshot.json'), 'bytes': len(raw), 'sha256': digest(raw)}

    def make(self, method='R', *, model=None, limits=None, final_reserve=None, arm='necessary', prefix=None,
             binding_changes=None, source_type=LocalEvidenceSource):
        from recommendation_runner import RecommendationRun
        self.counter += 1
        output = self.root / 'runs' / str(self.counter)
        binding = {'schema_version': 'rsm-run-0.1.0',
            'run_id': 'PUBLIC-RUN-' + digest(str(self.root.resolve()).encode())[:16] + '-' + str(self.counter),
            'root_task_id': 'PUBLIC-ROOT', 'method': method, 'repeat_id': 1, 'arm': arm,
            'execution_kind': 'scripted_public', 'fixture': 'public_runtime_adapter',
            'execution_budget': None, 'execution_authorized': False,
            'C': self.parents[:], 'base_scores': self.scores[:], 'batches': self.batches[:],
            'C_sha256': digest(encoded(self.parents)),
            'base_score_sha256': digest(encoded(list(zip(self.parents, self.scores)))),
            'H_sha256': digest(encoded(self.history)), 'necessary_clauses': ['c1', 'c2'], 'K': 10,
            'snapshot_id': self.facts.snapshot['snapshot_id'], 'verify_at_ms': 1000,
            'principal_id': 'SIM-VERIFIER', 'prefix_limit': prefix, 'fusion': None}
        if arm == 'quality':
            binding['fusion'] = {'schema_version': 'fusion-binding-0.1.0', 'task_id': binding['root_task_id'],
                **{k: copy.deepcopy(binding[k]) for k in ('C', 'C_sha256', 'H_sha256', 'base_scores', 'base_score_sha256',
                    'snapshot_id', 'verify_at_ms', 'principal_id', 'K')},
                'base_score_version': 'public-runtime-example', 'contract_sha256': digest(encoded(self.facts.rules)),
                'alpha': .5, 'beta': [.25, .5, .25], 'mode': 'full',
                'preference': {'source': 'experiment_design', 'dimensions': ['retail_stock'], 'weights': {'retail_stock': 1}}}
        binding.update(binding_changes or {})
        resources = dict.fromkeys(RootBudget.resources, 10000000)
        resources.update(model_calls=1000, candidates=100, retries=2, elapsed_ms=600000)
        reserve = dict.fromkeys(RootBudget.resources, 0)
        reserve.update(model_calls=1, input_tokens=1000000, output_tokens=100000, logical_tools=1, elapsed_ms=1000)
        if method == 'R':
            for key in ('model_calls', 'input_tokens', 'output_tokens', 'cost_microusd'):
                resources[key] = reserve[key] = 0
        resources.update(limits or {})
        reserve.update(final_reserve or {})
        joint = JointSession({'root_task_id': 'PUBLIC-ROOT', 'H': copy.deepcopy(self.history), 'S': [], 'H_sha256': binding['H_sha256']},
            {'C': self.parents[:], 'b': self.scores[:], 'batches': self.batches[:],
             'background_statistics': [{} for p in self.parents]},
            [{'parent_asin': p, 'title': p, 'crop': 'rice'} for p in self.parents],
            {'arm': arm, 'request': {'design_text': 'PUBLIC R1 AND R5', 'necessary_clauses': ['c1', 'c2']}},
            'PUBLIC-SESSION')
        if not self.parents:
            binding['safe_initial_messages'] = joint.dispatch('model_request', {})['request']['messages']
        budget = RootBudget(binding, resources, reserve, clock=lambda: self.now[0], journal_path=output / 'budget.jsonl')
        evidence_binding = {k: binding[k] for k in ('run_id', 'root_task_id', 'snapshot_id',
            'principal_id', 'verify_at_ms', 'arm', 'necessary_clauses')}
        position = joint.orders['base'][0] if self.parents else None
        evidence_binding.update(parent_asin=position, sim_batch_id=self.batches[self.parents.index(position)] if position else None)
        session = EvidenceSession(evidence_binding, source_type(self.facts.snapshot_ref),
            limits=resources, final_reserve=reserve, root_budget=budget, joint=joint if self.parents else None,
            sleeper=lambda seconds: self.now.__setitem__(0, self.now[0] + seconds * 1000))
        return RecommendationRun(binding, evidence=session, model=model, root_budget=budget, output_root=output)
