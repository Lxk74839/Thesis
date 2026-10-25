"""Frozen development preparation and task16 worker; importing never sends a model request."""
import hashlib
import json
import math
import re
import unicodedata
import os
import uuid
import argparse
import inspect
import subprocess
import sys
import time
import threading
from collections import Counter
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
OUTPUT = PROJECT / 'data/recommendation-runtime-audit/macrec-agri-dev-task16'
PUBLIC = PROJECT / '.tmp/task16-execution'


def tokens(text):
    return re.findall(r'[a-z]+|[0-9]+', unicodedata.normalize('NFKC', text).casefold())


def terms(words):
    return Counter([('w', w) for w in words] + [('b', a, b) for a, b in zip(words, words[1:])])


def normalized(values):
    length = math.sqrt(sum(v * v for v in values.values()))
    return {k: v / length for k, v in values.items()} if length else {}


def content_index(catalog):
    words = {p: tokens(row['title'] + ' ' + row['crop']) for p, row in catalog.items()}
    frequencies = {p: terms(w) for p, w in words.items()}
    df = Counter(term for freq in frequencies.values() for term in freq)
    idf = {term: math.log((1 + len(catalog)) / (1 + count)) + 1 for term, count in df.items()}
    vectors = {p: normalized({t: n * idf[t] for t, n in freq.items()}) for p, freq in frequencies.items()}
    unigram_df = Counter(w for ws in words.values() for w in set(ws))
    return {'words': words, 'idf': idf, 'vectors': vectors, 'df': unigram_df,
        'avglen': sum(map(len, words.values())) / len(words), 'N': len(words)}


def content_scores(c, history, catalog, char3, index, weights):
    query, bm_query = {}, Counter()
    for h in history:
        product = catalog[h['parent_asin']]
        words = tokens(h['text'] + ' ' + product['title'] + ' ' + product['crop'])
        vector = normalized({t: n * index['idf'][t] for t, n in terms(words).items() if t in index['idf']})
        for term, value in vector.items():
            query[term] = query.get(term, 0) + h['rating'] / 5 * value
        for word, count in Counter(words).items():
            bm_query[word] += h['rating'] / 5 * count / len(words)
    query = normalized(query)
    views = {'char3': char3, 'word': {}, 'bm25': {}}
    for p in c:
        views['word'][p] = sum(value * index['vectors'][p].get(t, 0) for t, value in query.items())
        freq = Counter(index['words'][p])
        length = len(index['words'][p])
        score = 0
        for word, weight in bm_query.items():
            if freq[word]:
                df = index['df'][word]
                idf = math.log(1 + (index['N'] - df + .5) / (df + .5))
                score += weight * idf * freq[word] * 2.2 / (freq[word] + 1.2 * (.25 + .75 * length / index['avglen']))
        views['bm25'][p] = score
    rrf = dict.fromkeys(c, 0.)
    for weight, scores in zip(weights, views.values()):
        ordered = sorted(c, key=lambda p: -round(scores[p], 12))
        left = 0
        while left < len(ordered):
            right = left + 1
            while right < len(ordered) and round(scores[ordered[right]], 12) == round(scores[ordered[left]], 12):
                right += 1
            rank = (left + 1 + right) / 2
            for p in ordered[left:right]:
                rrf[p] += weight / (60 + rank)
            left = right
    lo, hi = min(rrf.values()), max(rrf.values())
    prior = {p: (v - lo) / (hi - lo) if history and hi > lo else .5 for p, v in rrf.items()}
    return prior, views


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def read_ref(ref):
    path = (PROJECT / ref['path']).absolute()
    if path.resolve() != path or not path.is_relative_to(PROJECT) or '.secrets' in path.parts:
        raise ValueError('macrec_source_scope')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ref['sha256'] or 'bytes' in ref and len(raw) != ref['bytes']:
        raise ValueError('macrec_source_changed')
    return json.loads(raw)


def file_ref(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {'path': path.relative_to(PROJECT).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def store(path, value):
    path = Path(path).absolute()
    if path.resolve() != path or not (path.is_relative_to(OUTPUT) or path.is_relative_to(PUBLIC)):
        raise ValueError('macrec_output_scope')
    raw = encoded(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError('macrec_immutable_artifact_changed')
        return file_ref(path)
    temporary = path.with_name('.' + uuid.uuid4().hex + '.pending')
    with temporary.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.rename(temporary, path)
    return file_ref(path)


class EvidenceTools:
    """A material-only, shared list/read/assessment adapter. No private reference access."""
    def __init__(self, snapshot_ref, mapping, *, quality=False):
        from evidence_access import LocalEvidenceSource
        self.snapshot_ref = snapshot_ref
        self.snapshot = read_ref(snapshot_ref)
        self.source = LocalEvidenceSource(snapshot_ref, indexed=True)
        self.mapping, self.quality = dict(mapping), quality
        self.rows, self.audits = {}, {}
        directory = (PROJECT / snapshot_ref['path']).parent
        self.stamps = {directory / name: (directory / name).stat().st_mtime_ns
            for name in self.snapshot['components']}

    def __call__(self, ids):
        from evidence_access import EvidenceSession
        if any(path.stat().st_mtime_ns != stamp for path, stamp in self.stamps.items()):
            raise ValueError('macrec_evidence_changed')
        for parent in ids:
            if parent in self.rows:
                continue
            binding = {'run_id': 'macrec-material-' + self.snapshot_ref['sha256'],
                'root_task_id': 'macrec-material-' + self.snapshot_ref['sha256'],
                'snapshot_id': self.snapshot['snapshot_id'], 'verify_at_ms': self.snapshot['verify_at_ms'],
                'principal_id': 'SIM-VERIFIER', 'parent_asin': parent, 'sim_batch_id': self.mapping[parent],
                'arm': 'quality' if self.quality else 'necessary', 'necessary_clauses': ['c1', 'c2']}
            session = EvidenceSession(binding, self.source,
                limits={'logical_tools': 10000, 'physical_tools': 1000, 'candidates': 1, 'retries': 0, 'elapsed_ms': 120000},
                final_reserve={'logical_tools': 0, 'physical_tools': 0, 'elapsed_ms': 0})
            cursor, refs = None, []
            while True:
                listed = session.dispatch('list_evidence', {'cursor': cursor}, actor_role='生命周期追溯')
                if listed['status'] != 'ok':
                    raise ValueError('macrec_evidence_list_failed')
                refs.extend(row['evidence_ref'] for row in listed['entries'])
                cursor = listed['next_cursor']
                if cursor is None:
                    break
            for offset in range(0, len(refs), 32):
                read = session.dispatch('read_evidence', {'evidence_refs': refs[offset:offset + 32]}, actor_role='生命周期追溯')
                if read['status'] != 'ok' or any(r['status'] in ('io_error', 'not_attempted') for r in read.get('items', [])):
                    raise ValueError('macrec_evidence_read_failed')
            assessed = session.assess_current()
            if assessed['status'] != 'ok':
                raise ValueError('macrec_evidence_assessment_failed')
            assessment, audit = assessed['assessment'], session.audit_view()
            stock = {'supported': False}
            if self.quality:
                from evidence_verification import rank_acquired_quality
                from quality_fusion import RULES
                acquired = audit['acquired']
                acquired['candidate_binding'] = {'C': [parent], 'base_scores': [.5]}
                fusion = {'schema_version': 'fusion-binding-0.1.0', 'task_id': binding['root_task_id'],
                    'C': [parent], 'C_sha256': digest([parent]), 'H_sha256': digest([]), 'base_scores': [.5],
                    'base_score_sha256': digest([(parent, .5)]), 'base_score_version': 'macrec-quality-only',
                    'contract_sha256': digest(RULES), **{k: binding[k] for k in ('snapshot_id', 'verify_at_ms', 'principal_id')},
                    'K': 1, 'alpha': .5, 'beta': [.25, .5, .25], 'mode': 'full',
                    'preference': {'source': 'experiment_design', 'dimensions': ['retail_stock'], 'weights': {'retail_stock': 1}}}
                ranked = rank_acquired_quality(fusion, acquired)['candidates'][0]
                stock = {'supported': ranked['z'] == 1 and ranked['stock_state'] == 'Supported',
                    'value': ranked['x'], 'quality': ranked['q'],
                    'components': {k: ranked[k] for k in ('C', 'T', 'T_fraction', 'A')}}
            self.rows[parent] = {'parent_asin': parent, 'sim_batch_id': self.mapping[parent],
                'eligible': assessment['eligible'], 'state': assessment['evidence_state'], 'stock': stock,
                'source': 'SIM', 'material_scope_sha256': digest(binding),
                'accepted_proofs': [{'ref': 'proof:' + str(i), 'sha256': digest(row)}
                    for i, row in enumerate(assessment['accepted'])], 'tool_usage': audit['usage']}
            self.audits[parent] = {'binding': binding, 'assessment': assessment, 'usage': audit['usage'],
                'provenance': audit['provenance'], 'receipts': audit['receipts'], 'acquired_sha256': digest(audit['acquired'])}
        return {p: self.rows[p] for p in ids}


def prepare(source_manifest, scope, configuration):
    """S1: project accepted public inputs; labels are never consumed by this seam."""
    if scope not in ('public_fixture', 'dev320') or source_manifest['scope'] != scope:
        raise ValueError('macrec_scope')
    if 'tables' in source_manifest:
        source_manifest = {'scope': scope, **{name: read_ref(source_manifest['tables'][name])
            for name in ('catalog', 'roots', 'candidates', 'cohort')}}
    catalog = {p['parent_asin']: {k: p[k] for k in ('parent_asin', 'title', 'crop')}
        for p in source_manifest['catalog']}
    index = content_index(catalog)
    cohort = sorted((r for r in source_manifest['cohort'] if r['split'] == 'dev'),
        key=lambda r: (bytes.fromhex(r['split_hash']), r.get('tie_break', r['root_task_id']).encode('utf-8')))
    if scope == 'dev320' and len(cohort) != 320:
        raise ValueError('macrec_development_count')
    roots = {r['root_task_id']: r for r in source_manifest['roots']}
    candidates = {r['root_task_id']: r for r in source_manifest['candidates']}
    tasks = {}
    for member in cohort:
        key = member['root_task_id']
        root, row = roots[key], candidates[key]
        history = [{k: h[k] for k in ('parent_asin', 'text', 'rating', 'timestamp_ms')} for h in root['history']]
        c, scores, batches = row['C'], row['b'], row['batches']
        if (len(c) != len(set(c)) or not len(c) == len(scores) == len(batches)
                or set(c) & {h['parent_asin'] for h in history}
                or any(h['timestamp_ms'] >= root['history_cutoff_exclusive_ms'] for h in history)
                or any(type(b) not in (int, float) or not math.isfinite(b) or not 0 <= b <= 1 for b in scores)):
            raise ValueError('macrec_candidate_or_history_binding')
        prior, components = content_scores(c, history, catalog, dict(zip(c, scores)), index, configuration['weights'])
        recalled = sorted(c, key=lambda p: (-prior[p], p.encode('utf-8')))[:configuration['M']]
        order = sorted(recalled, key=lambda p: hashlib.sha256(
            b'macrec-shared-order-v1\0' + key.encode() + b'\0' + p.encode()).digest())
        tasks[key] = {'root_task_id': key, 'history': history, 'C': c[:], 'D': order,
            'batches': dict(zip(c, batches)), 'prior': prior, 'char3': dict(zip(c, scores)),
            'content_components': components,
            'history_cutoff_exclusive_ms': root['history_cutoff_exclusive_ms'],
            'request': {'necessary': ['c1', 'c2'], 'preferences': [], 'source': 'experiment_design'},
            'catalog': {p: catalog[p] for p in set(c) | {h['parent_asin'] for h in history}}, 'K': 10}
        if 'request' in root:
            request = root['request']
            tasks[key]['request'].update(design_text=request['design_text'],
                necessary_details=request['necessary_clauses'])
    return {'scope': scope, 'tasks': tasks, 'panel': [r['root_task_id'] for r in cohort[:16]],
        'selection': {'weights': configuration['weights'], 'M': configuration['M']}}


def preparation_budget():
    from task16_control import budget_at, new_bytes, DEFAULT_SESSION, instant
    budget = budget_at(DEFAULT_SESSION)
    if time.time() >= instant(budget['deadline_utc']):
        raise ValueError('macrec_original_deadline_expired')
    if new_bytes(DEFAULT_SESSION, force=True) + 32 * 1024**2 >= budget['max_new_bytes']:
        raise ValueError('macrec_shared_storage_limit')


def evaluation_process(command, *args, activity_directory=OUTPUT):
    started = time.time()
    try:
        result = subprocess.run([sys.executable, '-B', str(PROJECT / 'macrec_evaluation.py'), command, *map(str, args)],
            cwd=PROJECT, capture_output=True, text=True, encoding='utf-8', timeout=1800)
    finally:
        ended = time.time()
        store(activity_directory / 'activity' / ('evaluation-' + uuid.uuid4().hex + '.json'),
            {'category': 'evaluation', 'start': started, 'end': ended, 'heartbeat': ended,
                'generation': 'business-evaluation', 'command': command})
    if result.returncode:
        raise ValueError('macrec_independent_evaluation_failed:' + result.stderr[-1200:])
    return json.loads(result.stdout)


def material_cache(scene, mapping):
    identity = {'snapshot': scene['snapshot'], 'principal': 'SIM-VERIFIER', 'mapping': digest(mapping),
        'quality': scene['arm'] == 'quality', 'clauses': ['c1', 'c2'], 'beta': [.25, .5, .25]}
    path = OUTPUT / 'prepared/materials' / (digest(identity) + '.json')
    if path.exists():
        cached = read_ref(file_ref(path))
        checksum = cached.pop('content_sha256')
        if cached['binding'] != identity or checksum != digest(cached):
            raise ValueError('macrec_material_cache_changed')
        snapshot = read_ref(scene['snapshot'])
        directory = (PROJECT / scene['snapshot']['path']).parent
        for name, ref in snapshot['components'].items():
            with (directory / name).open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != ref['sha256']:
                    raise ValueError('macrec_material_source_changed')
        return file_ref(path)
    tools = EvidenceTools(scene['snapshot'], mapping, quality=identity['quality'])
    tools(list(mapping))
    body = {'binding': identity, 'candidates': tools.rows, 'audits': tools.audits}
    return store(path, body | {'content_sha256': digest(body)})


def prepare_files():
    """Real accepted-data preparation. Independent children alone read private targets."""
    from experiment_runner import accepted_sources, _scan
    from formal_runtime import load_config
    preparation_budget()
    content_code = digest({'content': [inspect.getsource(f) for f in (tokens, terms, normalized, content_index, content_scores, prepare)],
        'independent_evaluator': file_ref(PROJECT / 'macrec_evaluation.py')})
    destination = OUTPUT / 'prepared' / ('model-index.' + content_code + '.json')
    if destination.exists():
        index = read_ref(file_ref(destination))
        for ref in [index['catalog'], index['cohort'], index['selection'], index['offline_selection'], *index['tasks'].values(), *index['evidence'].values()]:
            read_ref(ref)
        return {'status': 'prepared', 'users': 320, 'panel_users': 16, 'model_api_calls': 0,
            'execution_authorized': False, 'model_index': file_ref(destination)}
    original = accepted_sources()
    refs = evaluation_process('references', '--output', OUTPUT / 'private/development-reference.json')
    cohort = read_ref(refs['cohort'])
    users = {row['root_task_id'] for row in cohort}
    templates = {row['root_task_id']: row for row, _ in _scan(original['view_bindings'])
        if row['root_task_id'] in users and row['label'] == 'V00'}
    roots = []
    for row, _ in _scan(original['roots']):
        if row['root_task_id'] in users:
            template = templates[row['root_task_id']]
            if any(row[k] != template[k] for k in ('C_sha256', 'H_sha256', 'base_scores_sha256')):
                raise ValueError('macrec_accepted_view_binding')
            if digest(row['history']) != row['H_sha256']:
                raise ValueError('macrec_accepted_history_binding')
            roots.append(row | {'request': template['request']})
    candidates = []
    for row, _ in _scan(original['candidates']):
        if row['root_task_id'] in users:
            root = next(r for r in roots if r['root_task_id'] == row['root_task_id'])
            if digest(row['C']) != root['C_sha256'] or digest(list(zip(row['C'], row['b']))) != root['base_scores_sha256']:
                raise ValueError('macrec_accepted_candidate_binding')
            candidates.append({k: row[k] for k in ('root_task_id', 'C', 'b', 'batches')})
    catalog = [row for row, _ in _scan(original['catalog'])]
    mapping = {row['parent_asin']: row['sim_batch_id'] for row, _ in _scan(original['candidate_map'])}
    if len(roots) != 320 or len(candidates) != 320 or len(catalog) != 1494:
        raise ValueError('macrec_accepted_scope_count')
    tables = {name: store(OUTPUT / 'prepared' / ('table-' + name + '.json'), value)
        for name, value in (('roots', roots), ('candidates', candidates), ('catalog', catalog))}
    tables['cohort'] = refs['cohort']
    cfg = load_config(validate_code=False)
    scenes = [row for row, _ in _scan(cfg['plan_files']['scenes.jsonl'])]
    evidence = {}
    for scene in scenes:
        preparation_budget()
        evidence[scene['label']] = material_cache(scene, mapping)
        print(json.dumps({'stage': 'material_preparation', 'scene': scene['label'], 'completed': len(evidence), 'total': 18}), flush=True)
    source = {'scope': 'dev320', 'tables': tables, 'evidence': evidence, 'scenes': scenes,
        'accepted_sources': original, 'independent_contract': refs['references']}
    source_ref = store(OUTPUT / 'prepared/source-tables.json', source)
    selection = evaluation_process('select', '--inputs', PROJECT / source_ref['path'],
        '--references', PROJECT / refs['references']['path'],
        '--output', OUTPUT / 'evaluation' / ('offline-selection.' + content_code + '.json'),
        '--safe-output', OUTPUT / 'prepared' / ('content-configuration.' + content_code + '.json'))
    prepared = prepare(source, 'dev320', selection['configuration'])
    task_refs = {}
    for root, task in prepared['tasks'].items():
        compact = {k: v for k, v in task.items() if k != 'catalog'}
        task_refs[root] = store(OUTPUT / 'prepared/tasks' / (digest(compact) + '.json'), compact)
    index = {'scope': 'dev320', 'catalog': tables['catalog'], 'cohort': tables['cohort'],
        'source_manifest': source_ref, 'tasks': task_refs, 'panel': prepared['panel'], 'evidence': evidence,
        'scenes': scenes, 'selection': selection['configuration_ref'], 'offline_selection': selection['selection_ref'], 'content_code_sha256': content_code,
        'history_depth': {u: len({h['parent_asin'] for h in t['history']}) for u, t in prepared['tasks'].items()}}
    index_ref = store(destination, index)
    preparation_budget()
    return {'status': 'prepared', 'users': 320, 'panel_users': 16, 'model_api_calls': 0,
        'execution_authorized': False, 'model_index': index_ref}


def freeze_plan():
    from task16_control import PHASES
    prepared = prepare_files()
    index = read_ref(prepared['model_index'])
    panel = store(OUTPUT / 'prepared' / ('panel.' + digest(index['panel']) + '.json'), index['panel'])
    contract = {'channel': '4Router', 'base_url': 'https://4router.net/v1', 'model': 'gpt-6-luna',
        'efforts': ['low', 'medium'], 'quotas': ['half', 'full'], 'role_quotas': ROLE_QUOTAS,
        'selection_priority': [['medium', 'full'], ['low', 'full'], ['medium', 'half'], ['low', 'half']],
        'requirements': 'all eight business probes for a configuration pass scope, sources, completion and usage',
        'http_timeout_seconds': 120, 'automatic_retries': 0, 'max_request_bytes': 131072,
        'max_response_bytes': 262144, 'max_root_calls': 37, 'max_parallel_roots': 2}
    model_contract = store(OUTPUT / 'prepared' / ('model-contract.' + digest(contract) + '.json'), contract)
    parameters = []
    for root in index['panel'][:2]:
        for effort in ('low', 'medium'):
            for quota in ('half', 'full'):
                model = store(OUTPUT / 'prepared/configs' / (effort + '-' + quota + '.json'),
                    {'effort': effort, 'quota': quota})
                user_probe = None
                for shape in ('interpret', 'action', 'User', 'Items'):
                    unit = {'id': root + '-' + effort + '-' + quota + '-' + shape, 'root_id': root,
                        'phase': 'parameters', 'operation': 'probe', 'shape': shape, 'limit': 1,
                        'method': 'B0' if shape == 'action' else 'I1', 'scene': 'V00',
                        'task': index['tasks'][root], 'catalog': index['catalog'],
                        'materials': index['evidence']['V00'], 'model': model}
                    if shape == 'Items':
                        unit['user_probe'] = user_probe
                    parameters.append(unit)
                    if shape == 'User':
                        user_probe = unit
    parameter_ref = store(OUTPUT / 'prepared' / ('parameters.' + digest(parameters) + '.json'), parameters)
    reference = file_ref(OUTPUT / 'private/development-reference.json')
    features = []
    for root in index['panel']:
        features.append({'id': root + '-features', 'root_id': root, 'phase': 'features-v00', 'operation': 'features',
            'method': 'A-feedback', 'scene': 'V00', 'limit': 18, 'task': index['tasks'][root],
            'catalog': index['catalog'], 'materials': index['evidence']['V00'], 'parameter_stage': parameter_ref,
            'model_contract': model_contract, 'policy': {'lambda': .5, 'tau': 3}})
    feature_ref = store(OUTPUT / 'prepared' / ('features.' + digest(features) + '.json'), features)
    stages = []
    for phase, maximum in PHASES:
        units = []
        if phase == 'offline':
            units = [{'id': 'validate-frozen-development', 'root_id': 'offline', 'phase': phase,
                'operation': 'offline', 'limit': 0, 'model_index': prepared['model_index']}]
        elif phase == 'parameters':
            units = parameters
        elif phase == 'features-v00':
            units = features
        elif phase.startswith('evaluate-'):
            units = [{'id': phase, 'root_id': phase, 'phase': phase, 'operation': 'evaluate', 'limit': 0,
                'evaluation_contract': reference, 'stage': 'v00' if phase == 'evaluate-v00' else 'final'}]
        else:
            scenes = ('Q1', 'Q2') if phase == 'quality' else ('Q1',) if phase == 'q1' else ('Q2',) if phase == 'q2' else ('V00',)
            for position, root in enumerate(index['panel']):
                methods = (('S', 'M') if phase == 'auxiliary' else
                    (('B0', 'I1') if position % 2 == 0 else ('I1', 'B0')) if phase in ('v00-main', 'q1', 'q2')
                    else ('A-' + phase,))
                for scene in scenes:
                    for method in methods:
                        unit = {'id': root + '-' + method + '-' + scene, 'root_id': root, 'phase': phase,
                            'operation': 'auxiliary' if phase == 'auxiliary' else 'recommend', 'method': method,
                            'scene': scene, 'quality': scene in ('Q1', 'Q2'),
                            'limit': (1 if method == 'S' else 6) if phase == 'auxiliary' else 37,
                            'task': index['tasks'][root], 'catalog': index['catalog'], 'materials': index['evidence'][scene],
                            'parameter_stage': parameter_ref, 'model_contract': model_contract,
                            'feature_stage': feature_ref, 'evaluation_contract': reference}
                        if phase == 'auxiliary':
                            unit['evidence'] = {s: index['evidence'][s] for s in ('V00', 'Q1', 'Q2')}
                        units.append(unit)
        stages.append({'id': phase, 'max_calls': maximum, 'units': units,
            'category': 'development' if phase == 'offline' else 'evaluation' if phase.startswith('evaluate-') else 'model'})
    recall = read_ref(index['offline_selection'])
    recall_ref = store(OUTPUT / 'prepared' / ('recall.' + index['content_code_sha256'] + '.json'),
        {k: recall[k] for k in ('users', 'M', 'weights', 'coverage', 'trials')})
    evidence_ref = store(OUTPUT / 'prepared' / ('evidence.' + digest(index['evidence']) + '.json'), index['evidence'])
    sources = [(panel, 'panel'), (prepared['model_index'], 'candidates'), (recall_ref, 'recall'),
        (evidence_ref, 'evidence'), (model_contract, 'model')]
    for path, role in (('.scratch/macrec-algorithm-20261023/spec.md', 'algorithm_spec'),
            ('.scratch/macrec-algorithm-20261023/sources/SOURCE_LOCK.json', 'upstream_lock'),
            ('.scratch/macrec-algorithm-20261023/acceptance.md', 'evaluation_contract'),
            ('.scratch/task16-execution-v2-20261023/spec.md', 'execution_spec')):
        sources.append((file_ref(PROJECT / path), role))
    plan = {'schema': 'task16-run-plan/1', 'kind': 'live', 'namespace': 'task16-macrec-agri-v1',
        'session_dir': OUTPUT.relative_to(PROJECT).as_posix(), 'worker': file_ref(PROJECT / 'macrec_experiment.py'),
        'panel_users': 16, 'panel': index['panel'], 'model_index': prepared['model_index'],
        'offline_selection': index['offline_selection'], 'model_contract': model_contract,
        'evaluation_reference': reference, 'stages': stages,
        'sources': [ref | {'role': role} for ref, role in sources]}
    plan_ref = store(OUTPUT / 'prepared' / ('frozen-plan.' + digest(plan) + '.json'), plan)
    return {'status': 'frozen_unsealed', 'plan': plan_ref, 'model_api_calls': 0, 'execution_authorized': False,
        'users': 320, 'panel_users': 16, 'slots': sum(len(s['units']) for s in stages), 'max_calls': 6944}


def freeze_protocol_v2():
    from macrec_protocol import VERSION
    from task16_control import worker_active, request_rows
    if worker_active(OUTPUT):
        raise ValueError('task16_worker_already_active')
    preparation_budget()
    archive = OUTPUT / 'execution-revisions/v00-v1-before-protocol-v2'
    archive.mkdir(parents=True, exist_ok=True)
    for name in ('run-plan.json','review-seal.json','run-binding.json','authorization.json','worker.json'):
        destination = archive / name
        if not destination.exists():
            raw = (OUTPUT / name).read_bytes()
            with destination.open('xb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
    history_path = archive / 'immutable-records.json'
    if not history_path.exists():
        records = [file_ref(p) for name in ('calls','request-index','units','results','halts','supervisions')
            for p in sorted((OUTPUT/name).glob('*.json'))]
        records += [file_ref(p) for p in sorted((OUTPUT/'business-health').glob('*.json'))]
        store(history_path, records)
    for ref in read_ref(file_ref(history_path)):
        read_ref(ref)
    previous_ref = file_ref(archive/'run-plan.json')
    previous = read_ref(previous_ref)
    plan = json.loads(encoded(previous))
    contract = read_ref(previous['model_contract']) | {'business_protocol':VERSION,
        'efforts':['medium'],'quotas':['full'],'selection_priority':[['medium','full']],
        'requirements':'two original roots x four Finish business shapes; all eight pass; unsupported preferences filtered identically to main'}
    contract_ref = store(OUTPUT/'prepared'/('fixed-model-v2.'+digest(contract)+'.json'),contract)
    parameters = []
    for root in plan['panel'][:2]:
        user = None
        for shape in ('interpret','action','User','Items'):
            old = next(u for u in previous['stages'][1]['units'] if u['root_id']==root and u['shape']==shape
                and read_ref(u['model']) == {'effort':'medium','quota':'full'})
            unit = {k:v for k,v in old.items() if k != 'user_probe'}
            unit.update(id=old['id']+'-'+VERSION,business_protocol=VERSION)
            if shape == 'Items':
                unit['user_probe'] = user
            parameters.append(unit)
            if shape == 'User':
                user = unit
    parameter_ref = store(OUTPUT/'prepared'/('parameters-v2.'+digest(parameters)+'.json'),parameters)
    for stage in plan['stages'][:5]:
        if stage['id'] == 'parameters':
            stage.update(max_calls=8,units=parameters)
            continue
        for unit in stage['units']:
            unit.update(id=unit['id']+'-'+VERSION,business_protocol=VERSION)
            if 'parameter_stage' in unit:
                unit.update(parameter_stage=parameter_ref,model_contract=contract_ref)
    feature_ref = store(OUTPUT/'prepared'/('features-v2.'+digest(plan['stages'][2]['units'])+'.json'),plan['stages'][2]['units'])
    for unit in plan['stages'][3]['units']:
        unit['feature_stage'] = feature_ref
    retained = sum(r['namespace'] == previous['namespace'] for r in request_rows(OUTPUT))
    if retained != 14:
        raise ValueError('task16_legacy_call_count_changed')
    plan.update(business_protocol=VERSION,namespace='task16-'+VERSION,worker=file_ref(PROJECT/'macrec_experiment.py'),
        model_contract=contract_ref)
    plan['execution'] = plan['execution'] | {'version':'v00-protocol-v2-20261024',
        'previous_execution':previous_ref,'previous_seal':file_ref(archive/'review-seal.json'),
        'retained_legacy_calls':retained,'historical_records':file_ref(history_path)}
    plan['sources'] = [(contract_ref | {'role':'model'}) if r['role']=='model' else r for r in plan['sources']]
    plan['sources'] += [file_ref(PROJECT/'macrec_protocol.py') | {'role':'business_protocol'},
        file_ref(PROJECT/'.scratch/task16-execution-v2-20261023/protocol-v2-20261024/spec.md') | {'role':'protocol_spec'}]
    ref = store(OUTPUT/'prepared'/('protocol-v2-plan.'+digest(plan)+'.json'),plan)
    return {'status':'frozen_unsealed','plan':ref,'active_units':58,'new_probe_limit':8,
        'retained_legacy_calls':retained,'cumulative_max_calls':1504,'api_calls_sent_by_preparation':0}


ROLE_QUOTAS = {'interpret': 2048, 'thought': 2048, 'action': 4096, 'reflect': 4096,
    '用户画像': 8192, '农产品画像': 8192, '生命周期追溯': 4096, 'auxiliary': 1400}

def compact_context(request):
    """Lossless source table plus bounded decision summaries; full traces remain on the host."""
    context = json.loads(encoded(request['context']))
    allowed = context.get('allowed', {})
    if request['kind'] == 'interpret':
        return {'allowed': {k: allowed[k] for k in ('session', 'request') if k in allowed},
            'trial': context.get('trial', context.get('state', {}).get('trial', 0))}
    candidates = allowed.get('candidates', [])
    positions = {row['parent_asin']: i for i, row in enumerate(candidates)}
    state = context.get('state', {})

    def observations_table(rows):
        packed = []
        for p, row in rows.items():
            stock, values = row.get('stock', {}), []
            components = stock.get('components', {})
            for name in ('C', 'T_fraction', 'A'):
                part = components.get(name)
                values.append([part['numerator'], part['denominator']] if isinstance(part, dict) else None)
            packed.append([positions[p], row.get('sim_batch_id'), row.get('eligible'), row.get('state'),
                [stock.get('supported', False), stock.get('value'), stock.get('quality'), values[0],
                    components.get('T'), values[1], values[2]], row.get('material_scope_sha256'), row.get('source')])
        return {'columns': ['candidate_index','sim_batch_id','eligible','state','stock','material_scope_sha256','source'],
            'stock_columns': ['supported','value','quality','C_fraction','T','T_fraction','A_fraction'], 'rows': packed}

    for name, analysis in state.get('analyses', {}).items():
        if name == 'Items' and 'matches' in analysis:
            matches = analysis['matches']
            aspects = [p['id'] for p in state.get('preferences', [])]
            if isinstance(matches, list) and all(isinstance(r, dict) and r.get('candidate') in positions
                    and r.get('aspect') in aspects and isinstance(r.get('references', []), list)
                    and all(isinstance(ref, dict) for ref in r.get('references', [])) for r in matches):
                grouped = {}
                for row in matches:
                    p = row['candidate']
                    codes = {'c:' + p + ':title': 0, 'c:' + p + ':crop': 1, 's:' + p: 2}
                    refs = [codes.get(ref.get('ref'), ref.get('ref')) for ref in row.get('references', [])]
                    grouped.setdefault(p, {})[row['aspect']] = (row.get('match'), refs[0] if len(refs) == 1 else refs)
                if len(matches) == len(candidates) * len(aspects) and all(set(v) == set(aspects) for v in grouped.values()):
                    analysis['matches'] = {'aspects': aspects, 'rows': [[positions[p], [v[a][0] for a in aspects],
                        [v[a][1] for a in aspects]] for p, v in grouped.items()]}
    for key in ('observations',):
        if key in state:
            state[key] = observations_table(state[key])
    for container, key in ((state, 'solution'), (context, 'solution')):
        solution = container.get(key)
        if isinstance(solution, dict):
            focus = set(solution.get('ranking', [])[:15])
            container[key] = {k: solution[k] for k in ('trial', 'ranking', 'topK', 'preferences') if k in solution}
            container[key]['scores'] = [[p, c['score']] for p, c in solution.get('components', {}).items()]
            components = {p: c for p, c in solution.get('components', {}).items() if p in focus}
            for p, component in components.items():
                for term in component['terms']:
                    for cite in term.get('references', []):
                        product = next((r for r in candidates if r['parent_asin'] == p), {})
                        if cite.get('ref') == 'c:' + p + ':title' and cite.get('quote') == product.get('title'):
                            cite.pop('quote')
                        elif cite.get('ref') == 'c:' + p + ':crop' and cite.get('quote') == product.get('crop'):
                            cite.pop('quote')
            container[key]['focus_components'] = components
    if context.get('solution') == state.get('solution') and 'solution' in state:
        context['solution'] = {'from': 'state.solution'}
    if 'trajectory' in context:
        context['trajectory'] = [{k: row[k] for k in ('role', 'kind', 'request_sha256') if k in row}
            | {'output_sha256': digest(row.get('output')), 'action': row.get('output', {}).get('action')}
            for row in context['trajectory']]
    observation = context.get('observation')
    if isinstance(observation, dict) and observation and set(observation) <= set(positions):
        context['observation'] = {'from': 'state.observations', 'candidates': list(observation)}
    return context


class BusinessClient:
    """Model boundary: every physical request is journalled by the accepted controller."""
    def __init__(self, session, configuration, *, transport=None):
        self.session, self.configuration, self.transport = session, configuration, transport
        self.pending = None

    def validated(self, ok):
        if self.pending is not None:
            model_health(self.session.directory, self.pending, ok)
            self.pending = None

    def __call__(self, request):
        from macrec_protocol import contract, decode, VERSION
        kind = request['kind']
        configuration = self.configuration
        if configuration['effort'] not in ('low', 'medium') or configuration['quota'] not in ('half', 'full'):
            raise ValueError('macrec_model_configuration')
        quota = ROLE_QUOTAS.get(request['role'], ROLE_QUOTAS.get(kind, 4096))
        if kind == 'auxiliary':
            quota = 1400
        elif configuration['quota'] == 'half':
            quota //= 2
        schema, prompt, _ = contract(request)
        wire = {'model': 'gpt-6-luna', 'store': False, 'stream': False, 'max_output_tokens': quota,
            'input': [{'role': 'system', 'content': prompt},
                {'role': 'user', 'content': encoded({'role': request['role'], 'kind': kind,
                    'context': compact_context(request)}).decode('utf-8')}],
            'text': {'format': {'type': 'json_schema', 'name': 'macrec_business_v2', 'strict': True, 'schema': schema}}}
        if kind != 'auxiliary':
            wire['reasoning'] = {'effort': configuration['effort']}
        if len(encoded(wire)) > 128 * 1024:
            raise ValueError('macrec_request_size:' + kind + ':' + request['role'] + ':' + str(len(encoded(wire))))

        def send(body):
            if self.transport:
                return self.transport(body)
            from provider_fourrouter import make_sender, response_diagnostic
            sender = make_sender(clock=lambda: time.time() * 1000, max_request_bytes=128 * 1024,
                http_timeout_seconds=120, max_response_bytes=256 * 1024)
            envelope = sender(encoded(body).decode('utf-8'), deadline_ms=time.time() * 1000 + 120000)
            result = envelope.get('body')
            if (envelope.get('http_status') != 200 or envelope.get('_business_capture_forbidden')
                    or not isinstance(result, dict) or result.get('model') != body['model']):
                return {'status': 'failed', 'reason': 'provider_response',
                    'usage': result.get('usage') if isinstance(result, dict) else None,
                    'diagnostic': response_diagnostic(envelope, failure=True)}
            return result

        health_id = digest({'namespace': self.session.namespace, 'wire': wire})
        model_health(self.session.directory)
        try:
            reply = self.session.invoke(wire, send, dependencies={'business_protocol': VERSION})
        except ValueError as exc:
            if str(exc).startswith(('task16_failed', 'task16_unresolved')):
                model_health(self.session.directory, health_id, False)
            raise
        self.pending = health_id
        self.last_usage = reply.get('usage')
        try:
            text = ''.join(part['text'] for item in reply['output'] if item['type'] == 'message'
                for part in item['content'] if part['type'] == 'output_text')
            value = decode(text, request)
            context = request['context']
            candidates = context.get('allowed', {}).get('candidates', [])
            data = value.get('data', {})
            if not isinstance(data, dict):
                raise ValueError()
            if request['kind'] == 'agent' and request['role'] == '生命周期追溯' and 'candidates' in data:
                data['candidates'] = [candidates[i]['parent_asin'] for i in data['candidates']]
            if request['kind'] == 'reflect' and request['context'].get('allowed', {}).get('protocol') != 'B0':
                for issue in value['issues']:
                    issue['candidate'] = candidates[issue['candidate']]['parent_asin']
            if isinstance(data.get('ranking'), list) and all(type(i) is int for i in data['ranking']):
                indices = data['ranking']
                if len(indices) != len(candidates) or set(indices) != set(range(len(candidates))):
                    raise ValueError()
                data['ranking'] = [candidates[i]['parent_asin'] for i in indices]
            for source, destination in (('matrix', 'matches'), ('revisions_matrix', 'revisions')):
                if source not in data:
                    continue
                prefs = context['state']['preferences']
                rows = []
                matrix = [[r['i'], r['m'], [(['title','crop','stock','unknown'][f]) for f in r['f']]]
                    for r in data.pop(source)]
                if (not isinstance(matrix, list) or any(not isinstance(row, list) or len(row) != 3
                        or type(row[0]) is not int or not 0 <= row[0] < len(candidates)
                        or not isinstance(row[1], list) or not isinstance(row[2], list) for row in matrix)):
                    raise ValueError()
                indices = [row[0] for row in matrix]
                if len(set(indices)) != len(indices) or source == 'matrix' and set(indices) != set(range(len(candidates))):
                    raise ValueError()
                for i, values, fields in matrix:
                    if type(i) is not int or not 0 <= i < len(candidates) or len(values) != len(prefs) or len(fields) != len(prefs):
                        raise ValueError()
                    candidate = candidates[i]
                    parent = candidate['parent_asin']
                    for pref, m, field in zip(prefs, values, fields):
                        cites = []
                        if field in ('title', 'crop'):
                            cites = [{'ref': 'c:' + parent + ':' + field, 'quote': candidate[field]}]
                        elif field == 'stock':
                            stock = context['state']['observations'].get(parent, {}).get('stock', {})
                            if stock.get('supported'):
                                cites = [{'ref': 's:' + parent, 'quote': str(stock['value'])}]
                        rows.append({'candidate': parent, 'aspect': pref['id'], 'match': m,
                            'preference_refs': [s['ref'] for s in pref['supports']], 'references': cites})
                data[destination] = rows
            return value
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            self.validated(False)
            raise ValueError('macrec_business_response_shape:' + str(exc)) from None


MATERIALS = {}
DECISIONS = threading.RLock()
HEALTH = {}


def model_health(directory, request_id=None, ok=None, protocol='macrec-agri-v2'):
    if protocol not in ('macrec-agri-v1', 'macrec-agri-v2'):
        raise ValueError('macrec_protocol_version')
    path = directory / 'business-health'
    if protocol != 'macrec-agri-v1':
        path /= protocol
    key = (directory, protocol)
    with DECISIONS:
        events = HEALTH.get(key)
        if events is None:
            events = {p.stem: json.loads(p.read_bytes()) for p in path.glob('*.json')}
            HEALTH[key] = events
        if request_id is not None:
            if request_id not in events:
                row = {'ok': ok, 'at': time.time(), 'protocol': protocol}
                store(path / (request_id + '.json'), row)
                events[request_id] = row
            return
        ordered = sorted(events.values(), key=lambda r: r['at'])
        streak = 0
        for event in reversed(ordered):
            if event['ok']:
                break
            streak += 1
        if streak >= 3 or streak >= 2 and not any(e['ok'] for e in ordered):
            raise ValueError('task16_business_error_burst')


def task_for(unit):
    task = read_ref(unit['task'])
    if 'catalog' not in task:
        catalog = {r['parent_asin']: r for r in read_ref(unit['catalog'])}
        task['catalog'] = {p: catalog[p] for p in set(task['C']) | {h['parent_asin'] for h in task['history']}}
    if unit.get('quality'):
        task['request']['preferences'] = [{'attribute': 'retail_stock', 'value': 'higher',
            'weight': 1, 'source': 'experiment_design'}]
    return task


def material_for(ref):
    path = PROJECT / ref['path']
    key = (str(path), ref['sha256'])
    stamp = (path.stat().st_size, path.stat().st_mtime_ns)
    cached = MATERIALS.get(key)
    if cached and cached['stamp'] != stamp:
        raise ValueError('macrec_material_changed')
    if cached is None:
        body = read_ref(ref)
        stamps = {}
        if 'binding' in body:
            checksum = body.pop('content_sha256')
            if checksum != digest(body):
                raise ValueError('macrec_material_cache_changed')
            snapshot_ref = body['binding']['snapshot']
            snapshot = read_ref(snapshot_ref)
            for name, component in snapshot['components'].items():
                component_path = (PROJECT / snapshot_ref['path']).parent / name
                with component_path.open('rb') as stream:
                    if hashlib.file_digest(stream, 'sha256').hexdigest() != component['sha256']:
                        raise ValueError('macrec_material_source_changed')
                stamps[component_path] = (component_path.stat().st_size, component_path.stat().st_mtime_ns)
        elif not path.is_relative_to(PUBLIC):
            raise ValueError('macrec_material_binding_required')
        cached = {'rows': body['candidates'], 'stamp': stamp, 'components': stamps}
        MATERIALS[key] = cached
    if any((p.stat().st_size, p.stat().st_mtime_ns) != value for p, value in cached['components'].items()):
        raise ValueError('macrec_material_source_changed')
    return cached['rows']


def binding_for(unit, task):
    return digest({'root': task['root_task_id'], 'C': task['C'], 'D': task['D'],
        'history': task['history'], 'prior': task['prior'], 'batches': task['batches'],
        'scene': unit['scene'], 'materials': unit['materials']['sha256']})


def probe(unit, session, task, client, configuration):
    from macrec_recommendation import preferences, rank_i1, ROLES
    shape = unit['shape']
    allowed = {'session': task['root_task_id'], 'history': task['history'], 'request': task['request'],
        'candidates': [task['catalog'][p] | {'prior': task['prior'][p]} for p in task['D']],
        'protocol': 'B0' if shape == 'action' else 'I1'}
    observed = material_for(unit['materials'])
    state = {'analyses': {}, 'observations': {p: observed[p] for p in task['D']}, 'trial': 0}
    context = {'allowed': allowed, 'state': state, 'internal_step': 0,
        'business_probe': 'Perform this business shape in one response; Finish directly, no tool request. '
            'For manager Action supply the entire candidate permutation, for User sourced preferences, '
            'for Items the full indexed matrix, for interpreter necessary [c1,c2] and preferences.'}
    if shape == 'Items':
        dependency = unit['user_probe']
        previous = read_unit_result(session.directory, dependency)
        if previous is None or not previous.get('passed'):
            return {'status': 'failed_model', 'passed': False, 'reason': 'user_probe_failed',
                'configuration': configuration, 'shape': shape, 'model_calls': 0}
        raw = previous['response']['data']['preferences']
        state['preferences'], _ = preferences(task, raw, 3)
        state['analyses'] = {'User': {'preferences': raw}, 'Search': {'analysis': 'actual acquired observations'}}
    kind = 'agent' if shape in ('User', 'Items') else shape
    request = {'role': ROLES.get(shape, ROLES.get(kind)), 'kind': kind, 'context': context}
    try:
        answer = client(request)
        profile_validation = {}
        usage = client.last_usage or {}
        if any(type(usage.get(k)) is not int or usage[k] < 0 for k in ('input_tokens', 'output_tokens')):
            raise ValueError('macrec_probe_usage_unknown')
        if shape == 'action':
            ranking = answer.get('data', {}).get('ranking')
            if answer.get('action') != 'Finish' or not isinstance(ranking, list) or len(ranking) != len(task['D']) or set(ranking) != set(task['D']):
                raise ValueError('macrec_probe_permutation')
        elif shape in ('User', 'Items'):
            if answer.get('action') != 'Finish':
                raise ValueError('macrec_probe_finish_required')
            if shape == 'User':
                valid, rejected = preferences(task, answer['data']['preferences'], 3)
                profile_validation = {'validated_preferences': valid, 'rejected_preferences': rejected}
            else:
                state['analyses']['Items'] = answer['data']
                rank_i1(task, state, {'lambda': .5, 'tau': 3})
        elif set(answer.get('necessary', [])) != {'c1', 'c2'} or answer.get('preferences') != task['request']['preferences']:
            raise ValueError('macrec_probe_interpretation')
        client.validated(True)
        return {'status': 'ok', 'passed': True, 'response': answer, 'configuration': configuration,
            'shape': shape, 'usage': usage, 'model_calls': 1, **profile_validation}
    except (ValueError, KeyError, TypeError) as exc:
        if str(exc).startswith('task16_unresolved') or str(exc).startswith('task16_') and not str(exc).startswith('task16_failed'):
            raise
        client.validated(False)
        return {'status': 'failed_model' if str(exc).startswith('task16_failed') else 'failed_protocol',
            'passed': False, 'reason': str(exc), 'configuration': configuration, 'shape': shape, 'model_calls': 1}


def read_unit_result(directory, unit):
    report_path = directory / 'results' / (digest(unit) + '.report.json')
    if not report_path.exists():
        return None
    report = read_ref(file_ref(report_path))
    return read_ref(report['result'])


def policy_for(unit, directory):
    if 'policy' in unit:
        return unit['policy'], None
    from macrec_recommendation import preferences, rank_i1
    with DECISIONS:
        identity = digest({'features': unit['feature_stage'],
            'algorithm': file_ref(PROJECT / 'macrec_recommendation.py'),
            'evaluator': file_ref(PROJECT / 'macrec_evaluation.py')})
        destination = directory / 'decisions' / ('policy.' + identity + '.json')
        if not destination.exists():
            units = read_ref(unit['feature_stage'])
            prefixes = [(u, read_unit_result(directory, u)) for u in units]
            if any(result is None for _, result in prefixes):
                raise ValueError('task16_features_not_complete')
            if not any(result['status'] == 'ok' for _, result in prefixes):
                raise ValueError('task16_no_valid_features')
            trials = []
            for strength in (.25, .5, .75):
                for tau in (1, 3):
                    policy, rows = {'lambda': strength, 'tau': tau}, []
                    for prefix_unit, result in prefixes:
                        task = task_for(prefix_unit)
                        binding = binding_for(prefix_unit, task)
                        descriptor = {k: task[k] for k in ('root_task_id', 'C', 'D')}
                        descriptor.update(method='I1', scene='V00', binding_id=binding)
                        if result['status'] == 'ok':
                            valid, _ = preferences(task, result['preferences'], tau)
                            state = {'preferences': valid, 'observations': result['observations'],
                                'analyses': {'User': {}, 'Search': {}, 'Items': {'matches': result['matches']}}}
                            ranking, components = rank_i1(task, state, policy)
                            observed = {'status': 'ok', 'binding_id': binding, 'ranking': ranking,
                                'topK': [p for p in ranking if result['observations'][p]['eligible']][:10],
                                'components': components, 'observations': result['observations']}
                        else:
                            observed = {'status': result['status'], 'binding_id': binding, 'topK': []}
                        rows.append({'task': descriptor, 'observed': observed})
                    trials.append({'policy': policy, 'rows': rows})
            inputs = store(directory / 'decisions' / ('components.' + identity + '.json'),
                {'users': [u['root_id'] for u in units], 'trials': trials})
            evaluation_process('grid', '--inputs', PROJECT / inputs['path'],
                '--references', PROJECT / unit['evaluation_contract']['path'],
                '--reference-sha', unit['evaluation_contract']['sha256'],
                '--output', directory / 'evaluation' / ('grid.' + identity + '.json'),
                '--safe-output', destination, activity_directory=directory)
        selected = read_ref(file_ref(destination))
        return {k: selected[k] for k in ('lambda', 'tau')}, {'trials': 6, 'selection_id': identity}


def v00_forecast(session, latencies, now):
    from task16_control import read, request_rows, execution_stages, observed_unit, sha, instant
    path = session.directory / 'run-plan.json'
    if not path.exists():
        return None
    plan = read(path)
    if not plan.get('execution'):
        return None
    budget = session.budget
    attempts = request_rows(session.directory)
    available = max(0, min(budget['max_calls'], plan['execution']['max_calls']) - len(attempts))
    plan_sha = sha(path.read_bytes())
    mean = sum(latencies) / len(latencies)
    stages, dispatch_work, local_work, remaining_calls = [], 0., 0., 0
    for stage in execution_stages(plan):
        if stage['category'] == 'evaluation':
            stages.append({'id': stage['id'], 'remaining_calls': 0, 'seconds': 600.})
            continue
        phase_attempts = [a for a in attempts if a['phase'] == stage['id']
            and (plan.get('business_protocol') != 'macrec-agri-v2' or a['namespace'] == plan['namespace'])]
        allowance = max(0, stage['max_calls'] - len(phase_attempts))
        roots = {}
        for pending in stage['units']:
            receipt = observed_unit(session.directory, pending, plan_sha)
            if receipt and receipt['status'] != 'unresolved' or read_unit_result(session.directory, pending) is not None:
                continue
            used = sum(a['unit'] == pending['id'] for a in phase_attempts)
            calls = min(max(0, pending['limit'] - used), allowance, available)
            allowance -= calls
            available -= calls
            root = roots.setdefault(pending['root_id'], {'calls': 0, 'units': 0})
            root['calls'] += calls
            root['units'] += 1
        lanes = [0., 0.]
        for root in roots.values():
            local = root['calls'] * .5 + root['units'] * 5
            lanes[lanes.index(min(lanes))] += root['calls'] * mean + local
            local_work += local
        calls = sum(r['calls'] for r in roots.values())
        seconds = max(lanes)
        stages.append({'id': stage['id'], 'remaining_calls': calls, 'roots': len(roots), 'seconds': seconds})
        remaining_calls += calls
        dispatch_work += seconds
    dispatch_remaining = instant(budget['dispatch_deadline_utc']) - now
    total_remaining = instant(budget['deadline_utc']) - now
    return {'at': now, 'attempts': len(attempts), 'scope': plan['execution']['version'], 'stages': stages,
        'mean_probe_seconds': mean, 'max_probe_seconds': max(latencies),
        'remaining_cold_calls': remaining_calls, 'remaining_dispatch_seconds': dispatch_remaining,
        'remaining_total_seconds': total_remaining, 'dispatch_work_seconds': dispatch_work,
        'local_processing_seconds': local_work, 'evaluation_reserve_seconds': 600.,
        'total_seconds': dispatch_work + 600.,
        'insufficient': dispatch_work > dispatch_remaining or dispatch_work + 600. > total_remaining,
        'assumption': 'selected eight probe latencies; serial stage barriers and each root, two root workers; '
            '0.5s per call plus 5s per unfinished unit host allowance; 600s evaluation reserve; estimate, not guarantee'}


def model_for(unit, session):
    fixed = unit.get('business_protocol') == 'macrec-agri-v2'
    if 'model' in unit:
        configuration = read_ref(unit['model'])
        if fixed and configuration != {'effort':'medium','quota':'full'}:
            raise ValueError('task16_fixed_model_configuration')
        return configuration
    from task16_control import request_rows, read, budget_at, instant
    with DECISIONS:
        units = read_ref(unit['parameter_stage'])
        if len(units) != (8 if fixed else 32) or len({u['root_id'] for u in units}) != 2:
            raise ValueError('task16_parameter_matrix_incomplete')
        results = [(u, read_unit_result(session.directory, u)) for u in units]
        if any(result is None for _, result in results):
            raise ValueError('task16_parameters_not_complete')
        contract = read_ref(unit['model_contract'])
        if fixed and contract['selection_priority'] != [['medium','full']]:
            raise ValueError('task16_fixed_model_configuration')
        trials = []
        for effort, quota in contract['selection_priority']:
            cfg = {'effort': effort, 'quota': quota}
            rows = [(u, r) for u, r in results if read_ref(u['model']) == cfg]
            shapes = {(u['root_id'], u['shape']) for u, _ in rows}
            passed = len(rows) == 8 and len(shapes) == 8 and all(r.get('passed') for _, r in rows)
            trials.append({'configuration': cfg, 'passed': passed,
                'states': [{'id': u['id'], 'status': r['status'], 'passed': r.get('passed', False)} for u, r in rows]})
        selected = next((r['configuration'] for r in trials if r['passed']), None)
        identity = digest({'parameters': unit['parameter_stage'], 'contract': unit['model_contract']})
        store(session.directory / 'decisions' / ('model.' + identity + '.json'),
            {'selected': selected, 'trials': trials, 'note': 'requested effort; provider compliance is not independently established'})
        if selected is None:
            raise ValueError('task16_no_model_configuration_passed')
        accepted_units = {u['id'] for u, r in results if read_ref(u['model']) == selected and r.get('passed')}
        attempts = request_rows(session.directory)
        latencies = []
        for attempt in attempts:
            if attempt['unit'] in accepted_units:
                terminal = read(session.directory / 'calls' / (attempt['request_id'] + '.terminal.json'))
                latencies.append(max(0, terminal['completed'] - attempt['started']))
        if len(latencies) != 8:
            raise ValueError('task16_parameter_latency_incomplete')
        budget = budget_at(session.directory)
        now = time.time()
        remaining = instant(budget['dispatch_deadline_utc']) - now
        if remaining <= 0:
            raise ValueError('task16_dispatch_deadline')
        estimate = max(0, budget['max_calls'] - len(attempts)) * sum(latencies) / len(latencies) / 2
        forecast = {'at': now, 'attempts': len(attempts), 'mean_probe_seconds': sum(latencies) / len(latencies),
            'remaining_dispatch_seconds': remaining, 'remaining_cold_calls': max(0, budget['max_calls'] - len(attempts)),
            'optimistic_two_parallel_seconds': estimate, 'insufficient': estimate > remaining,
            'assumption': 'selected configuration probes; ideal two independent roots; estimate, not a completion guarantee'}
        scoped = v00_forecast(session, latencies, now)
        if scoped is not None:
            forecast = scoped
        store(session.directory / 'forecasts' / (uuid.uuid4().hex + '.json'), forecast)
        if forecast['insufficient']:
            raise ValueError('task16_insufficient_remaining_time')
        return selected


def auxiliary(unit, task, client):
    from personalized_recommendation import analyze_profile, run_task as compact_rank
    catalog = list(task['catalog'].values())
    calls = 0
    def invoke(request):
        nonlocal calls
        client.validated(True)  # The previous compact stage passed its original validator.
        calls += 1
        return client({'kind': 'auxiliary', 'role': request['role'], 'context': request})
    try:
        analyzed = analyze_profile(task['history'], catalog, method=unit['method'], invoke=invoke)
    except (ValueError, TypeError, KeyError) as exc:
        if str(exc).startswith('task16_') and not str(exc).startswith('task16_failed'):
            raise
        client.validated(False)
        return {'status': 'failed_model' if str(exc).startswith('task16_failed') else 'failed_protocol',
            'method': unit['method'], 'reason': str(exc), 'scene_results': {}, 'model_calls': calls}
    client.validated(True)
    scenes = {}
    for label in ('V00', 'Q1', 'Q2'):
        current = unit | {'scene': label, 'materials': unit['evidence'][label]}
        observed = material_for(current['materials'])
        observed = {p: observed[p] for p in task['C']}
        result = compact_rank({'C': task['C'], 'base_scores': [task['char3'][p] for p in task['C']],
            'K': 10, 'method': unit['method'], 'prefer_stock': label in ('Q1', 'Q2')}, catalog=catalog,
            history=task['history'], profile=analyzed['profile'], scene=observed)
        scenes[label] = result | {'status': 'ok', 'method': unit['method'], 'observations': observed,
            'binding_id': binding_for(current, task), 'scene': label, 'root_task_id': task['root_task_id']}
    return {'status': 'ok', 'method': unit['method'], 'protocol': 'compact-personalized-v1',
        'profile_analysis': analyzed, 'scene_results': scenes, 'model_calls': len(analyzed['stages'])}


def validate_inputs(index):
    if index['scope'] != 'dev320' or len(index['tasks']) != 320 or len(index['panel']) != 16:
        raise ValueError('macrec_frozen_scope_changed')
    cohort = read_ref(index['cohort'])
    if index['panel'] != [r['root_task_id'] for r in sorted(cohort, key=lambda r: bytes.fromhex(r['split_hash']))[:16]]:
        raise ValueError('macrec_frozen_panel_changed')
    for ref in [index['catalog'], index['selection'], index['source_manifest'], index['offline_selection'], *index['tasks'].values()]:
        read_ref(ref)
    for ref in read_ref(index['source_manifest'])['tables'].values():
        read_ref(ref)
    for ref in index['evidence'].values():
        material_for(ref)
    return {'status': 'ok', 'users': 320, 'panel_users': 16, 'material_scenes': len(index['evidence']),
        'model_calls': 0, 'checks': 'frozen bytes, original cohort/order and material-source bindings; no re-cleaning'}


def save_unit(unit, directory, result):
    ref = store(directory / 'results' / (digest(unit) + '.json'), result)
    report = {'status': result['status'], 'result': ref, 'model_calls': result.get('model_calls', 0)}
    report.update({k: result[k] for k in ('binding_id', 'root_task_id', 'method', 'scene') if k in result})
    store(directory / 'results' / (digest(unit) + '.report.json'), report)
    return report


def validate_plan(plan):
    """Called once before dispatch or reuse, including a resumed coordinator."""
    if plan.get('kind') == 'live' and plan.get('business_protocol') != 'macrec-agri-v2':
        raise ValueError('task16_protocol_version_invalid')
    validate_inputs(read_ref(plan['model_index']))
    configs = {digest(u['model']): u['model'] for stage in plan['stages'] for u in stage['units'] if 'model' in u}
    for ref in configs.values():
        read_ref(ref)
    return {'status': 'ok', 'model_calls': 0}


def execute_unit(unit, session):
    """S4 real business worker. A supplied transport is only the external test boundary."""
    from macrec_recommendation import run_task
    destination = session.directory / 'results' / (digest(unit) + '.report.json')
    if destination.exists():
        if 'materials' in unit:
            task_for(unit)
            material_for(unit['materials'])
        if 'model' in unit:
            read_ref(unit['model'])
        report = read_ref(file_ref(destination))
        read_ref(report['result'])
        return report
    if unit['operation'] == 'offline':
        return save_unit(unit, session.directory, validate_inputs(read_ref(unit['model_index'])))
    if unit['operation'] == 'evaluate':
        reference = unit['evaluation_contract']
        evaluation_directory = session.directory/'evaluation'
        if unit.get('business_protocol'):
            evaluation_directory /= unit['business_protocol']
        report = evaluation_process('report', '--inputs', session.directory / 'run-plan.json',
            '--references', PROJECT / reference['path'], '--reference-sha', reference['sha256'],
            '--stage', unit['stage'], '--output', evaluation_directory / (unit['stage'] + '.json'),
            activity_directory=session.directory)
        return save_unit(unit, session.directory, {'status': 'ok', 'report': report['report'],
            'analysis_status': report['status'], 'model_calls': 0})
    if unit['operation'] not in ('recommend', 'probe', 'features', 'auxiliary'):
        raise ValueError('macrec_unknown_operation')
    task = task_for(unit)
    material_for(unit['materials'])
    configuration = model_for(unit, session)
    client = BusinessClient(session, configuration, transport=getattr(session, 'transport', None))

    def evidence(ids):
        rows = material_for(unit['materials'])
        return {p: rows[p] for p in ids}

    if unit['operation'] == 'probe':
        result = probe(unit, session, task, client, configuration)
    elif unit['operation'] == 'auxiliary':
        result = auxiliary(unit, task, client)
    else:
        policy, selection = policy_for(unit, session.directory)
        result = run_task(task, method=unit['method'], invoke=client, evidence=evidence, policy=policy)
        result.update(policy=policy, policy_selection=selection)
    result.update(root_task_id=unit['root_id'], scene=unit['scene'], binding_id=binding_for(unit, task),
        task_sha256=unit['task']['sha256'], material_sha256=unit['materials']['sha256'], model_configuration=configuration)
    return save_unit(unit, session.directory, result)


def preparation_guard(event, args):
    if event.startswith('socket.'):
        raise PermissionError('macrec_preparation_network_denied')
    if event == 'open' and isinstance(args[0], (str, bytes)) and '.secrets' in str(args[0]):
        raise PermissionError('macrec_preparation_credentials_denied')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'freeze', 'freeze-protocol-v2'])
    args = parser.parse_args()
    sys.addaudithook(preparation_guard)
    result = freeze_protocol_v2() if args.command == 'freeze-protocol-v2' else freeze_plan() if args.command == 'freeze' else prepare_files()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
