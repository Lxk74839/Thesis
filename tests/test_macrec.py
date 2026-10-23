"""Confirmed S1-S5 public seams; external model responses are public fixtures."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import time
import unittest


def source_fixture():
    return {'scope': 'public_fixture', 'catalog': [
        {'parent_asin': 'H', 'title': 'rolled oats', 'crop': 'oats'},
        {'parent_asin': 'A', 'title': 'oat flakes', 'crop': 'oats'},
        {'parent_asin': 'B', 'title': 'corn flour', 'crop': 'corn'}],
        'cohort': [{'root_task_id': 'u', 'split': 'dev', 'split_hash': '0' * 64}],
        'roots': [{'root_task_id': 'u', 'history_cutoff_exclusive_ms': 100,
            'history': [{'parent_asin': 'H', 'text': 'I prefer rolled oats.', 'rating': 5,
                'timestamp_ms': 10}]}],
        'observations': {'V00': {p: {'parent_asin': p, 'eligible': True, 'state': 'Supported',
            'stock': {'supported': False}, 'source': 'SIM'} for p in ('A', 'B')}},
        'candidates': [{'root_task_id': 'u', 'C': ['A', 'B'], 'b': [.1, .9],
            'batches': ['SIM-A', 'SIM-B']}]}


def i1_model(preferences, matches):
    actions = iter([{'action': name, 'data': {}} for name in ('User', 'Items', 'Search', 'Finish')])
    searched = False

    def model(request):
        nonlocal searched
        kind = request['kind']
        if kind == 'interpret':
            return {'preferences': []}
        if kind == 'thought':
            return {'thought': 'Compare supported preferences and every candidate.'}
        if kind == 'action':
            return next(actions)
        if kind == 'reflect':
            return {'revise': False, 'issues': []}
        if request['role'] == '用户画像':
            return {'action': 'Finish', 'data': {'preferences': preferences}}
        if request['role'] == '农产品画像':
            return {'action': 'Finish', 'data': {'matches': matches}}
        if not searched:
            searched = True
            return {'action': 'Lookup', 'data': {}}
        return {'action': 'Finish', 'data': {'analysis': 'Acquired allowed evidence.'}}
    return model


def preference_fixture():
    return [{'id': 'rolled', 'attribute': 'form', 'value': 'rolled oats', 'weight': 1,
        'supports': [{'ref': 'h0.text', 'quote': 'I prefer rolled oats.', 'stance': 1}]}]


def matches_fixture():
    return [{'candidate': p, 'aspect': 'rolled', 'match': m, 'preference_refs': ['h0.text'],
        'references': [{'ref': 'c:' + p + ':title', 'quote': quote}]}
        for p, m, quote in (('A', 1, 'oat flakes'), ('B', 0, 'corn flour'))]


class Preparation(unittest.TestCase):
    def test_freeze_cli_prepares_real_nonempty_stages_and_identical_paired_inputs_without_authorizing(self):
        result = subprocess.run([sys.executable, '-B', 'macrec_experiment.py', 'freeze'],
            cwd=Path.cwd(), capture_output=True, text=True, encoding='utf-8', timeout=1800)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout.splitlines()[-1])
        from macrec_experiment import read_ref
        plan = read_ref(report['plan'])
        self.assertEqual(len(plan['panel']), 16)
        self.assertEqual([len(s['units']) for s in plan['stages']], [1,32,16,32,1,32,32,16,16,32,16,32,1])
        self.assertEqual(sum(s['max_calls'] for s in plan['stages']), 6944)
        self.assertFalse(report['execution_authorized'])
        self.assertEqual(report['model_api_calls'], 0)
        main = next(s for s in plan['stages'] if s['id'] == 'v00-main')
        for root in plan['panel']:
            pair = [u for u in main['units'] if u['root_id'] == root]
            self.assertEqual({u['method'] for u in pair}, {'B0', 'I1'})
            self.assertEqual(pair[0]['task'], pair[1]['task'])
            self.assertEqual(pair[0]['materials'], pair[1]['materials'])
            self.assertEqual(pair[0]['parameter_stage'], pair[1]['parameter_stage'])
        from macrec_experiment import execute_unit, store
        from task16_control import Session
        base = Path.cwd() / '.tmp/task16-execution'
        with tempfile.TemporaryDirectory(dir=base) as temp:
            directory = Path(temp)
            (directory / 'budget.json').write_text(json.dumps({'max_calls': 6944,
                'max_new_bytes': 10 * 1024**3, 'dispatch_deadline_utc': time.time() + 120,
                'deadline_utc': time.time() + 200}), encoding='utf-8')
            offline = plan['stages'][0]['units'][0]
            session = Session(directory, namespace='local-stages', phase='offline', unit=offline['id'], limit=0)
            prepared = read_ref(execute_unit(offline, session)['result'])
            self.assertEqual(prepared['users'], 320)
            store(directory / 'run-plan.json', plan | {'session_dir': directory.relative_to(Path.cwd()).as_posix()})
            unit = next(s for s in plan['stages'] if s['id'] == 'evaluate-v00')['units'][0]
            evaluation_session = Session(directory, namespace='local-stages', phase='evaluate-v00', unit=unit['id'], limit=0)
            evaluated = read_ref(execute_unit(unit, evaluation_session)['result'])
            report = read_ref(evaluated['report'])
            self.assertEqual(report['summary']['groups']['I1/V00']['states']['not_started'], 16)
            self.assertIsNone(report['summary']['groups']['I1/V00']['metrics']['10']['HR'])

    def test_real_preparation_freezes_320_and_the_existing_hash_panel_without_model_authorization(self):
        result = subprocess.run([sys.executable, '-B', 'macrec_experiment.py', 'prepare'],
            cwd=Path.cwd(), capture_output=True, text=True, encoding='utf-8', timeout=900)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip())
        report = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(report['users'], 320)
        self.assertEqual(report['panel_users'], 16)
        self.assertEqual(report['model_api_calls'], 0)
        self.assertFalse(report['execution_authorized'])
        self.assertFalse((Path.cwd() / 'data/recommendation-runtime-audit/macrec-agri-dev-task16/authorization.json').exists())

    def test_hashed_public_tables_do_not_open_an_unrelated_private_reference(self):
        from macrec_experiment import prepare
        base = Path.cwd() / '.tmp/task16-execution'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            tables = {}
            for name, value in source_fixture().items():
                if name == 'scope':
                    continue
                path = Path(temp) / (name + '.json')
                raw = json.dumps(value).encode()
                path.write_bytes(raw)
                tables[name] = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            prepared = prepare({'scope': 'public_fixture', 'tables': tables,
                'private_reference': {'path': '.secrets/forbidden', 'sha256': '0' * 64}},
                'public_fixture', {'weights': [1, 1, 1], 'M': 1})
            self.assertEqual(prepared['panel'], ['u'])
            self.assertNotIn('private_reference', str(prepared))

    def test_private_target_changes_do_not_change_prepared_model_inputs(self):
        from macrec_experiment import prepare
        sources = source_fixture()
        other = copy.deepcopy(sources)
        other['roots'][0].update(target='B', target_text='private label', target_rating=1)
        other['reference'] = {'target': 'A', 'state': 'Refuted'}
        options = {'weights': [1, 1, 1], 'M': 1}
        before = prepare(sources, 'public_fixture', options)
        after = prepare(other, 'public_fixture', options)
        self.assertEqual(before, after)
        self.assertEqual(len(before['tasks']['u']['D']), 1)
        self.assertNotIn('target', str(before))

    def test_three_content_views_use_catalog_idf_and_average_rank_rrf(self):
        from macrec_experiment import prepare
        sources = source_fixture()
        sources['catalog'][0].update(title='oats')
        sources['catalog'][1].update(title='oats')
        sources['catalog'][2].update(title='corn')
        sources['roots'][0]['history'][0]['text'] = 'oats'
        task = prepare(sources, 'public_fixture', {'weights': [1, 1, 1], 'M': 1})['tasks']['u']
        self.assertAlmostEqual(task['content_components']['word']['A'], .9922778767136677)
        self.assertAlmostEqual(task['content_components']['bm25']['A'], .6462549902128865)
        self.assertEqual(task['D'], ['A'])
        self.assertEqual(task['prior'], {'A': 1, 'B': 0})


class Collaboration(unittest.TestCase):
    def test_history_confidence_deduplicates_parents_and_shrinks_with_opposing_evidence(self):
        from macrec_experiment import prepare
        from macrec_recommendation import run_task
        cases = [([('H1',1),('H1',1)], .5, 1, 0),
            ([('H1',1),('H2',1)], 2/3, 2, 0),
            ([('H1',1),('H1',1),('H2',1),('H3',-1)], .25, 2, 1),
            ([('H1',1),('H1',-1)], None, 0, 0)]
        for evidence_rows, expected, plus, minus in cases:
            task = prepare(source_fixture(), 'public_fixture', {'weights': [1,1,1], 'M': 2})['tasks']['u']
            task['history'] = [{'parent_asin': p, 'text': 'I prefer rolled oats.' if sign == 1 else 'I avoid rolled oats.',
                'rating': 5, 'timestamp_ms': i} for i, (p,sign) in enumerate(evidence_rows)]
            pref = preference_fixture()
            pref[0]['supports'] = [{'ref': 'h%d.text' % i, 'quote': row['text'], 'stance': sign}
                for i, (row, (_,sign)) in enumerate(zip(task['history'], evidence_rows))]
            result = run_task(task, method='I1', invoke=i1_model(pref, matches_fixture() if expected is not None else []),
                evidence=lambda ids: {p: {'parent_asin': p, 'eligible': True} for p in ids},
                policy={'lambda': .75, 'tau': 1})
            self.assertEqual(result['status'], 'ok')
            if expected is None:
                self.assertEqual(result['preferences'], [])
            else:
                self.assertAlmostEqual(result['preferences'][0]['c'], expected)
                self.assertEqual((result['preferences'][0]['n_plus'], result['preferences'][0]['n_minus']), (plus, minus))

    def test_200_candidate_six_aspect_comparison_keeps_complete_sources_inside_the_controller_wire_limit(self):
        from macrec_experiment import BusinessClient
        from macrec_recommendation import run_task
        from task16_control import Session, encoded
        base = Path.cwd() / '.tmp/task16-execution'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            directory = Path(temp)
            (directory / 'budget.json').write_text(json.dumps({'max_calls': 100,
                'max_new_bytes': 10 * 1024**3, 'dispatch_deadline_utc': time.time() + 120,
                'deadline_utc': time.time() + 200}), encoding='utf-8')
            words = ['oats','flour','rolled','flakes','puffed','bran']
            quote = 'I prefer oats flour rolled flakes puffed bran.'
            ids = ['P%03d' % i for i in range(200)]
            title = 'PUBLIC oats flour rolled flakes puffed bran ' + 'grain catalog description ' * 4
            task = {'root_task_id': 'PUBLIC-200', 'C': ids, 'D': ids, 'K': 10,
                'history': [{'parent_asin': 'H', 'text': quote + ' Review context.' * 400,
                    'rating': 5, 'timestamp_ms': 10}], 'request': {'preferences': [], 'necessary': ['c1','c2']},
                'catalog': {p: {'parent_asin': p,'title': title + p,'crop': 'oats'} for p in ids},
                'prior': dict.fromkeys(ids, .5)}
            prefs = [{'id': w,'attribute': 'title_term','value': w,'weight': 1,
                'supports': [{'ref': 'h0.text','quote': quote,'stance': 1}]} for w in words]
            wires = []
            actions = iter(['User','Search','Items','Finish'])
            def transport(wire):
                wires.append(copy.deepcopy(wire))
                request = json.loads(wire['input'][1]['content'])
                if request['kind'] == 'interpret': response = {'preferences': []}
                elif request['kind'] == 'thought': response = {'thought': 'Compare all candidates.'}
                elif request['kind'] == 'action': response = {'action': next(actions),'data': {}}
                elif request['kind'] == 'reflect': response = {'revise': False,'issues': []}
                elif request['role'] == '用户画像': response = {'action': 'Finish','data': {'preferences': prefs}}
                elif request['role'] == '农产品画像': response = {'action': 'Finish','data': {
                    'matrix': [[i,[.75]*6,['title']*6] for i in range(200)]}}
                else: response = ({'action': 'Lookup','data': {}} if request['context']['internal_step'] == 0
                    else {'action': 'Finish','data': {'analysis': 'Verified shared SIM source.'}})
                return {'status': 'completed','model': 'gpt-6-luna','usage': {'input_tokens': 100,'output_tokens': 20},
                    'output': [{'type': 'message','content': [{'type': 'output_text',
                    'text': json.dumps({'data_json': json.dumps(response)})}]}]}
            evidence = lambda selected: {p: {'parent_asin': p,'sim_batch_id': 'SIM-'+p,
                'eligible': True,'state': 'Supported','stock': {'supported': True,'value': 75,'quality': .6,
                    'components': {'C': {'numerator': 1,'denominator': 1},'T': .2,
                        'T_fraction': {'numerator': 1,'denominator': 5},'A': {'numerator': 2,'denominator': 2}}},
                'source': 'SIM','material_scope_sha256': 'a'*64} for p in selected}
            session = Session(directory, namespace='PUBLIC-200', phase='v00-main', unit='I1', limit=37)
            result = run_task(task, method='I1', invoke=BusinessClient(session, {'effort':'medium','quota':'full'},
                transport=transport), evidence=evidence, policy={'lambda': .5,'tau': 3})
            self.assertEqual(result['status'], 'ok', result.get('reason'))
            self.assertEqual(len(result['components']), 200)
            self.assertTrue(all(len(r['terms']) == 6 for r in result['components'].values()))
            self.assertLessEqual(max(len(encoded(w)) for w in wires), 131072)
            self.assertEqual(len(json.loads(wires[-1]['input'][1]['content'])['context']['allowed']['candidates']), 200)

    def test_feedback_must_point_to_an_actual_allowed_source_before_a_second_trial(self):
        from macrec_experiment import prepare
        from macrec_recommendation import run_task
        task = prepare(source_fixture(), 'public_fixture', {'weights': [1,1,1], 'M': 2})['tasks']['u']
        original = i1_model(preference_fixture(), matches_fixture())
        def model(request):
            if request['kind'] == 'reflect':
                return {'revise': True, 'issues': [{'candidate': 'A', 'aspect': 'rolled',
                    'reference': 'c:OUTSIDE:title', 'problem': 'Unsupported external source.'}]}
            return original(request)
        result = run_task(task, method='I1', invoke=model,
            evidence=lambda ids: {p: {'parent_asin': p, 'eligible': True} for p in ids},
            policy={'lambda': .5, 'tau': 3})
        self.assertEqual(result['status'], 'failed_protocol')
        self.assertEqual(len(result['versions']), 1)

    def test_malformed_model_match_rows_fail_one_task_without_becoming_a_pipeline_exception(self):
        from macrec_experiment import prepare
        from macrec_recommendation import run_task
        task = prepare(source_fixture(), 'public_fixture', {'weights': [1,1,1], 'M': 2})['tasks']['u']
        result = run_task(task, method='I1', invoke=i1_model(preference_fixture(), [{'candidate': 'A'}]),
            evidence=lambda ids: {p: {'parent_asin': p, 'eligible': True} for p in ids},
            policy={'lambda': .5, 'tau': 3})
        self.assertEqual(result['status'], 'failed_protocol')
        self.assertEqual(result['topK'], [])

    def test_unobserved_negative_attribute_cannot_be_treated_as_satisfied(self):
        from macrec_experiment import prepare
        from macrec_recommendation import run_task
        task = prepare(source_fixture(), 'public_fixture', {'weights': [1,1,1], 'M': 2})['tasks']['u']
        task['history'][0]['text'] = 'I avoid crunchy.'
        task['prior'] = {'A': .4, 'B': .6}
        proposed = [{'id': 'crunch', 'attribute': 'title_term', 'value': 'crunchy', 'weight': 1,
            'supports': [{'ref': 'h0.text', 'quote': 'I avoid crunchy.', 'stance': -1}]}]
        matches = matches_fixture()
        for row in matches:
            row['aspect'] = 'crunch'
        result = run_task(task, method='I1', invoke=i1_model(proposed, matches),
            evidence=lambda ids: {p: {'parent_asin': p, 'eligible': True} for p in ids},
            policy={'lambda': .75, 'tau': 1})
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['topK'], ['B','A'])
        self.assertEqual([result['components'][p]['terms'][0]['o'] for p in ('A','B')], [0,0])
        self.assertEqual(result['components']['A']['score'], .4)

    def test_known_model_failures_are_terminal_and_the_initial_error_burst_stops_new_requests(self):
        from macrec_experiment import prepare, execute_unit, store
        from task16_control import Session, call_counts
        base = Path.cwd() / '.tmp/task16-execution'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            directory = Path(temp)
            (directory / 'budget.json').write_text(json.dumps({'max_calls': 100,
                'max_new_bytes': 10 * 1024**3, 'dispatch_deadline_utc': time.time() + 120,
                'deadline_utc': time.time() + 200}), encoding='utf-8')
            task = prepare(source_fixture(), 'public_fixture', {'weights': [1,1,1], 'M': 2})['tasks']['u']
            material = store(directory / 'material.json', {'candidates': {p: {'parent_asin': p,
                'eligible': True, 'stock': {'supported': False}, 'source': 'SIM'} for p in ('A','B')}})
            model = store(directory / 'model.json', {'effort': 'medium','quota': 'full'})
            for i in range(3):
                current_task = task | {'root_task_id': 'u' + str(i)}
                unit = {'id': 'u' + str(i), 'root_id': current_task['root_task_id'], 'phase': 'v00-main',
                    'operation': 'recommend', 'method': 'I1', 'scene': 'V00', 'limit': 37,
                    'task': store(directory / (str(i) + '.json'), current_task), 'materials': material,
                    'model': model, 'policy': {'lambda': .5, 'tau': 3}}
                session = Session(directory, namespace='error-burst', phase='v00-main', unit=unit['id'], limit=37)
                session.transport = lambda wire: {'status': 'failed', 'usage': None}
                if i < 2:
                    self.assertEqual(execute_unit(unit, session)['status'], 'failed_model')
                else:
                    with self.assertRaisesRegex(ValueError, '^task16_business_error_burst$'):
                        execute_unit(unit, session)
            self.assertEqual(call_counts(directory)[0]['attempts'], 2)

    def test_worker_selects_one_shared_configuration_only_after_all_32_business_probes(self):
        from macrec_experiment import prepare, execute_unit, store, read_ref
        from task16_control import Session
        base = Path.cwd() / '.tmp/task16-execution'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            directory = Path(temp)
            (directory / 'budget.json').write_text(json.dumps({'max_calls': 100,
                'max_new_bytes': 10 * 1024**3, 'dispatch_deadline_utc': time.time() + 120,
                'deadline_utc': time.time() + 200}), encoding='utf-8')
            task = prepare(source_fixture(), 'public_fixture', {'weights': [1,1,1], 'M': 2})['tasks']['u']
            material = store(directory / 'material.json', {'candidates': {p: {'parent_asin': p,
                'eligible': True, 'state': 'Supported', 'stock': {'supported': False}, 'source': 'SIM'} for p in ('A','B')}})
            parameters = []
            def transport(wire):
                request = json.loads(wire['input'][1]['content'])
                shape = request['kind'] if request['kind'] != 'agent' else request['role']
                if shape == 'interpret':
                    response = {'necessary': ['c1','c2'], 'preferences': []}
                elif shape == 'action':
                    bad = wire['reasoning']['effort'] == 'low' and wire['max_output_tokens'] == 2048
                    response = {'action': 'Finish', 'data': {'ranking': [0] if bad else [0,1]}}
                elif shape == '用户画像':
                    response = {'action': 'Finish', 'data': {'preferences': preference_fixture()}}
                else:
                    response = {'action': 'Finish', 'data': {'matches': matches_fixture()}}
                return {'status': 'completed', 'model': 'gpt-6-luna', 'usage': {'input_tokens': 100, 'output_tokens': 20},
                    'output': [{'type': 'message', 'content': [{'type': 'output_text',
                    'text': json.dumps({'data_json': json.dumps(response)})}]}]}
            for user in ('u','v'):
                current_task = task | {'root_task_id': user}
                task_ref = store(directory / (user + '.json'), current_task)
                for effort in ('low','medium'):
                    for quota in ('half','full'):
                        user_probe = None
                        cfg = store(directory / (effort + quota + '.json'), {'effort': effort, 'quota': quota})
                        for shape in ('interpret','action','User','Items'):
                            unit = {'id': user+effort+quota+shape, 'root_id': user, 'phase': 'parameters',
                                'operation': 'probe', 'method': 'B0' if shape == 'action' else 'I1',
                                'scene': 'V00', 'shape': shape, 'task': task_ref, 'materials': material, 'model': cfg, 'limit': 1}
                            if shape == 'Items':
                                unit['user_probe'] = user_probe
                            session = Session(directory, namespace='32-parameters', phase='parameters', unit=unit['id'], limit=1)
                            session.transport = transport
                            execute_unit(unit, session)
                            parameters.append(unit)
                            if shape == 'User':
                                user_probe = unit
            current = {'id': 'u-I1', 'root_id': 'u', 'phase': 'v00-main', 'operation': 'recommend',
                'method': 'I1', 'scene': 'V00', 'task': parameters[0]['task'], 'materials': material,
                'parameter_stage': store(directory / 'parameters.json', parameters),
                'model_contract': store(directory / 'contract.json', {'selection_priority':
                    [['medium','full'], ['low','full'], ['medium','half'], ['low','half']]}),
                'policy': {'lambda': .5, 'tau': 3}, 'limit': 37}
            external = i1_model(preference_fixture(), matches_fixture())
            def main_transport(wire):
                response = external(json.loads(wire['input'][1]['content']))
                return {'status': 'completed', 'model': 'gpt-6-luna', 'usage': {'input_tokens': 100, 'output_tokens': 20},
                    'output': [{'type': 'message', 'content': [{'type': 'output_text',
                    'text': json.dumps({'data_json': json.dumps(response)})}]}]}
            session = Session(directory, namespace='32-parameters', phase='v00-main', unit=current['id'], limit=37)
            session.transport = main_transport
            result = read_ref(execute_unit(current, session)['result'])
            self.assertEqual(result['model_configuration'], {'effort': 'medium', 'quota': 'full'})
            self.assertEqual(result['status'], 'ok')
            (directory / 'budget.json').write_text(json.dumps({'max_calls': 6944,
                'max_new_bytes': 10 * 1024**3, 'dispatch_deadline_utc': time.time() + 1,
                'deadline_utc': time.time() + 7201}), encoding='utf-8')
            another = current | {'id': 'u-I1-late'}
            late_session = Session(directory, namespace='32-parameters', phase='v00-main', unit=another['id'], limit=37)
            late_session.transport = main_transport
            with self.assertRaisesRegex(ValueError, '^task16_insufficient_remaining_time$'):
                execute_unit(another, late_session)

    def test_auxiliary_worker_keeps_the_compact_six_profile_protocol_and_scene_replay(self):
        from macrec_experiment import prepare, execute_unit, store, read_ref
        from task16_control import Session, call_counts
        base = Path.cwd() / '.tmp/task16-execution'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            directory = Path(temp)
            (directory / 'budget.json').write_text(json.dumps({'max_calls': 100,
                'max_new_bytes': 10 * 1024**3, 'dispatch_deadline_utc': time.time() + 120,
                'deadline_utc': time.time() + 200}), encoding='utf-8')
            task = prepare(source_fixture(), 'public_fixture', {'weights': [1, 1, 1], 'M': 2})['tasks']['u']
            material = store(directory / 'material.json', {'candidates': {p: {'parent_asin': p,
                'eligible': True, 'state': 'Supported', 'stock': {'supported': False}, 'source': 'SIM'} for p in ('A', 'B')}})
            unit = {'id': 'u-M', 'root_id': 'u', 'operation': 'auxiliary', 'phase': 'auxiliary',
                'scene': 'V00', 'method': 'M', 'limit': 6, 'task': store(directory / 'task.json', task),
                'materials': material, 'evidence': dict.fromkeys(('V00', 'Q1', 'Q2'), material),
                'model': store(directory / 'model.json', {'effort': 'medium', 'quota': 'full'})}
            wires = []
            def transport(wire):
                wires.append(copy.deepcopy(wire))
                return {'status': 'completed', 'model': 'gpt-6-luna', 'usage': {'input_tokens': 100, 'output_tokens': 20},
                    'output': [{'type': 'message', 'content': [{'type': 'output_text',
                    'text': json.dumps({'data_json': json.dumps({'selections': [], 'issues': []})})}]}]}
            session = Session(directory, namespace='compact-aux', phase='auxiliary', unit=unit['id'], limit=6)
            session.transport = transport
            report = execute_unit(unit, session)
            result = read_ref(report['result'])
            self.assertEqual(result['method'], 'M')
            self.assertEqual(set(result['scene_results']), {'V00', 'Q1', 'Q2'})
            self.assertEqual(call_counts(directory)[0]['successful'], 6)
            self.assertTrue(all(w['max_output_tokens'] == 1400 and 'reasoning' not in w for w in wires))
            self.assertNotIn('MACRec', result['protocol'])

    def test_feature_stage_selects_scoring_components_without_sending_six_system_runs(self):
        from macrec_experiment import prepare, execute_unit, store, read_ref
        from task16_control import Session, call_counts
        base = Path.cwd() / '.tmp/task16-execution'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            directory = Path(temp)
            (directory / 'budget.json').write_text(json.dumps({'max_calls': 100,
                'max_new_bytes': 10 * 1024**3, 'dispatch_deadline_utc': time.time() + 120,
                'deadline_utc': time.time() + 200}), encoding='utf-8')
            task = prepare(source_fixture(), 'public_fixture', {'weights': [1, 1, 1], 'M': 2})['tasks']['u']
            task['prior'] = {'A': .4, 'B': .6}
            materials = store(directory / 'materials.json', {'candidates': {p: {'parent_asin': p,
                'eligible': True, 'state': 'Supported', 'stock': {'supported': False}, 'source': 'SIM'} for p in ('A', 'B')}})
            common = {'root_id': 'u', 'scene': 'V00', 'task': store(directory / 'task.json', task),
                'materials': materials, 'model': store(directory / 'model.json', {'effort': 'medium', 'quota': 'full'})}
            feature = common | {'id': 'u-features', 'phase': 'features-v00', 'operation': 'features',
                'method': 'A-feedback', 'limit': 18, 'policy': {'lambda': .5, 'tau': 3}}
            feature_session = Session(directory, namespace='feature-main', phase='features-v00', unit=feature['id'], limit=18)
            def transport_for(model):
                def send(wire):
                    answer = model(json.loads(wire['input'][1]['content']))
                    return {'status': 'completed', 'model': 'gpt-6-luna', 'usage': {'input_tokens': 100, 'output_tokens': 50},
                        'output': [{'type': 'message', 'content': [{'type': 'output_text',
                        'text': json.dumps({'data_json': json.dumps(answer)})}]}]}
                return send
            feature_session.transport = transport_for(i1_model(preference_fixture(), matches_fixture()))
            prefix = execute_unit(feature, feature_session)
            prefix_result = read_ref(prefix['result'])
            self.assertEqual(prefix_result['status'], 'ok')
            self.assertNotIn('reflect', [r['kind'] for r in prefix_result['trajectory']])
            after_prefix = call_counts(directory)[0]['attempts']
            current = common | {'id': 'u-I1', 'phase': 'v00-main', 'operation': 'recommend', 'method': 'I1',
                'limit': 37, 'feature_stage': store(directory / 'features.json', [feature]),
                'evaluation_contract': store(directory / 'reference.json', {'targets': {'u': 'A'},
                    'states': {'V00': {'A': 'Supported', 'B': 'Supported'}}})}
            session = Session(directory, namespace='feature-main', phase='v00-main', unit=current['id'], limit=37)
            session.transport = transport_for(i1_model(preference_fixture(), matches_fixture()))
            final = read_ref(execute_unit(current, session)['result'])
            self.assertEqual(final['policy'], {'lambda': .5, 'tau': 1})
            self.assertEqual(final['topK'], ['A', 'B'])
            self.assertEqual(final['policy_selection']['trials'], 6)
            self.assertLess(call_counts(directory)[0]['attempts'], after_prefix + 37)

    def test_parameter_worker_checks_a_complete_real_candidate_permutation(self):
        from macrec_experiment import prepare, execute_unit, store, read_ref
        from task16_control import Session
        base = Path.cwd() / '.tmp/task16-execution'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            directory = Path(temp)
            (directory / 'budget.json').write_text(json.dumps({'max_calls': 100,
                'max_new_bytes': 10 * 1024**3, 'dispatch_deadline_utc': time.time() + 120,
                'deadline_utc': time.time() + 200}), encoding='utf-8')
            task = prepare(source_fixture(), 'public_fixture', {'weights': [1, 1, 1], 'M': 2})['tasks']['u']
            unit = {'id': 'u-medium-full-action', 'root_id': 'u', 'operation': 'probe',
                'shape': 'action', 'phase': 'parameters', 'scene': 'V00', 'method': 'B0', 'limit': 1,
                'task': store(directory / 'task.json', task), 'materials': store(directory / 'materials.json',
                    {'candidates': {p: {'parent_asin': p, 'eligible': True, 'state': 'Supported',
                        'stock': {'supported': False}, 'source': 'SIM'} for p in ('A', 'B')}}),
                'model': store(directory / 'model.json', {'effort': 'medium', 'quota': 'full'})}
            for invalid in (True, False):
                current = unit | {'id': unit['id'] + ('-bad' if invalid else '-good')}
                session = Session(directory, namespace=current['id'], phase='parameters', unit=current['id'], limit=1)
                session.transport = lambda wire: {'status': 'completed', 'model': 'gpt-6-luna',
                    'usage': {'input_tokens': 200, 'output_tokens': 80}, 'output': [{'type': 'message',
                    'content': [{'type': 'output_text', 'text': json.dumps({'data_json': json.dumps(
                        {'action': 'Finish', 'data': {'ranking': [0] if invalid else [1, 0]}})})}]}]}
                report = execute_unit(current, session)
                result = read_ref(report['result'])
                self.assertEqual(report['status'], 'failed_protocol' if invalid else 'ok')
                self.assertEqual(result['passed'], not invalid)
                self.assertEqual(result['configuration'], {'effort': 'medium', 'quota': 'full'})

    def test_generic_praise_cannot_create_a_weighted_preference(self):
        from macrec_experiment import prepare
        from macrec_recommendation import run_task
        task = prepare(source_fixture(), 'public_fixture', {'weights': [1, 1, 1], 'M': 2})['tasks']['u']
        task['history'][0]['text'] = 'I love this product.'
        proposed = [{'id': 'generic', 'attribute': 'title_term', 'value': 'product', 'weight': 1,
            'supports': [{'ref': 'h0.text', 'quote': 'I love this product.', 'stance': 1}]}]
        result = run_task(task, method='I1', invoke=i1_model(proposed, []),
            evidence=lambda ids: {p: {'parent_asin': p, 'eligible': True} for p in ids},
            policy={'lambda': .5, 'tau': 3})
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['preferences'], [])
        self.assertTrue(all(r['score'] == task['prior'][p] for p, r in result['components'].items()))

    def test_b0_requires_an_actual_analysis_and_search_observation_before_publication(self):
        from macrec_experiment import prepare
        from macrec_recommendation import run_task
        task = prepare(source_fixture(), 'public_fixture', {'weights': [1, 1, 1], 'M': 2})['tasks']['u']
        def model(request):
            if request['kind'] == 'action':
                return {'action': 'Finish', 'data': {'ranking': task['D']}}
            if request['kind'] == 'reflect':
                return {'revise': False, 'issues': []}
            return {'thought': 'Premature result.'}
        result = run_task(task, method='B0', invoke=model,
            evidence=lambda ids: {p: {'parent_asin': p, 'eligible': True} for p in ids}, policy={})
        self.assertEqual(result['status'], 'failed_protocol')
        self.assertEqual(result['topK'], [])

    def test_real_worker_publishes_replayable_algorithm_result_from_verified_inputs(self):
        from macrec_experiment import prepare, execute_unit, store, read_ref
        from task16_control import Session
        base = Path.cwd() / '.tmp/task16-execution'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            directory = Path(temp)
            (directory / 'budget.json').write_text(json.dumps({'max_calls': 100,
                'max_new_bytes': 10 * 1024**3, 'dispatch_deadline_utc': time.time() + 120,
                'deadline_utc': time.time() + 200}), encoding='utf-8')
            task = prepare(source_fixture(), 'public_fixture', {'weights': [1, 1, 1], 'M': 2})['tasks']['u']
            task['prior'] = {'A': .4, 'B': .6}
            task_ref = store(directory / 'task.json', task)
            materials = store(directory / 'evidence.json', {'candidates': {p: {'parent_asin': p,
                'eligible': True, 'state': 'Supported', 'stock': {'supported': False}, 'source': 'SIM'} for p in ('A', 'B')}})
            cfg = store(directory / 'config.json', {'effort': 'medium', 'quota': 'full'})
            unit = {'id': 'u-I1-V00', 'root_id': 'u', 'operation': 'recommend', 'phase': 'v00-main',
                'method': 'I1', 'scene': 'V00', 'limit': 37, 'task': task_ref, 'materials': materials,
                'model': cfg, 'policy': {'lambda': .75, 'tau': 1}}
            external = i1_model(preference_fixture(), matches_fixture())

            def transport(wire):
                answer = external(json.loads(wire['input'][1]['content']))
                return {'status': 'completed', 'model': 'gpt-6-luna', 'output': [{'type': 'message',
                    'content': [{'type': 'output_text', 'text': json.dumps({'data_json': json.dumps(answer)})}]}],
                    'usage': {'input_tokens': 100, 'output_tokens': 50}}

            session = Session(directory, namespace='worker-public', phase='v00-main', unit=unit['id'], limit=37)
            session.transport = transport
            report = execute_unit(unit, session)
            result = read_ref(report['result'])
            self.assertEqual(report['status'], 'ok')
            self.assertEqual(result['method'], 'I1')
            self.assertEqual(result['topK'], ['A', 'B'])
            self.assertAlmostEqual(result['components']['A']['score'], .625)
            self.assertEqual(result['binding_id'], report['binding_id'])
            self.assertEqual(execute_unit(unit, session), report)
            self.assertFalse((directory / 'authorization.json').exists())
            plan = store(directory / 'plan.json', {'session_dir': directory.relative_to(Path.cwd()).as_posix(),
                'panel': ['u'], 'stages': [{'id': 'v00-main', 'units': [unit]}]})
            reference = store(directory / 'reference.json', {'targets': {'u': 'A'},
                'states': {'V00': {'A': 'Supported', 'B': 'Supported'}}})
            evaluated = subprocess.run([sys.executable, '-B', 'macrec_evaluation.py', 'report',
                '--inputs', plan['path'], '--references', reference['path'], '--output', str(directory / 'evaluation.json')],
                cwd=Path.cwd(), capture_output=True, text=True, encoding='utf-8', timeout=30)
            self.assertEqual(evaluated.returncode, 0, evaluated.stderr)
            final_report = json.loads((directory / 'evaluation.json').read_bytes())
            self.assertEqual(final_report['summary']['groups']['I1/V00']['metrics']['10']['HR'], 1)
            self.assertEqual(final_report['summary']['groups']['I1/V00']['recall'], 1)

    def test_controller_backed_business_client_replays_real_wire_and_expands_source_indexes(self):
        from macrec_experiment import prepare, BusinessClient
        from macrec_recommendation import run_task
        from task16_control import Session, call_counts
        base = Path.cwd() / '.tmp/task16-execution'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            directory = Path(temp)
            (directory / 'budget.json').write_text(json.dumps({'max_calls': 100,
                'max_new_bytes': 10 * 1024**3, 'dispatch_deadline_utc': time.time() + 120,
                'deadline_utc': time.time() + 200}), encoding='utf-8')
            task = prepare(source_fixture(), 'public_fixture', {'weights': [1, 1, 1], 'M': 2})['tasks']['u']
            task['prior'] = {'A': .4, 'B': .6}
            requests = []
            actions = iter(['User', 'Items', 'Search', 'Finish'])

            def transport(wire):
                requests.append(copy.deepcopy(wire))
                request = json.loads(wire['input'][1]['content'])
                kind, role = request['kind'], request['role']
                if kind == 'interpret':
                    response = {'preferences': []}
                elif kind == 'thought':
                    response = {'thought': 'Compare all allowed candidates.'}
                elif kind == 'reflect':
                    response = {'revise': False, 'issues': []}
                elif kind == 'action':
                    response = {'action': next(actions), 'data': {}}
                elif role == '用户画像':
                    response = {'action': 'Finish', 'data': {'preferences': preference_fixture()}}
                elif role == '农产品画像':
                    candidates = request['context']['allowed']['candidates']
                    response = {'action': 'Finish', 'data': {'matrix': [
                        [i, [1 if p['parent_asin'] == 'A' else 0], ['title']] for i, p in enumerate(candidates)]}}
                else:
                    response = ({'action': 'Lookup', 'data': {}} if request['context']['internal_step'] == 0
                        else {'action': 'Finish', 'data': {'analysis': 'Read SIM evidence.'}})
                body = {'data_json': json.dumps(response)}
                return {'status': 'completed', 'model': 'gpt-6-luna', 'output': [{'type': 'message',
                    'content': [{'type': 'output_text', 'text': json.dumps(body)}]}],
                    'usage': {'input_tokens': 100, 'output_tokens': 50}}

            session = Session(directory, namespace='public-business', phase='v00-main', unit='u-I1', limit=37)
            client = BusinessClient(session, {'effort': 'medium', 'quota': 'full'}, transport=transport)
            evidence = lambda ids: {p: {'parent_asin': p, 'eligible': True,
                'state': 'Supported', 'stock': {'supported': False}, 'source': 'SIM'} for p in ids}
            result = run_task(task, method='I1', invoke=client, evidence=evidence, policy={'lambda': .75, 'tau': 1})
            self.assertEqual(result['topK'], ['A', 'B'])
            self.assertAlmostEqual(result['components']['A']['score'], .625)
            count = len(requests)
            replay = run_task(task, method='I1', invoke=client, evidence=evidence, policy={'lambda': .75, 'tau': 1})
            self.assertEqual(replay, result)
            self.assertEqual(len(requests), count)
            self.assertEqual(call_counts(directory)[0]['successful'], count)
            self.assertTrue(all(r['reasoning']['effort'] == 'medium' for r in requests))
            self.assertEqual(requests[0]['max_output_tokens'], 2048)
            self.assertNotIn('target', json.dumps(requests))

    def test_real_evidence_tools_supply_quality_components_and_material_bound_observations(self):
        from tests.evidence_fixtures import EvidenceFixture
        from macrec_experiment import EvidenceTools
        from macrec_recommendation import run_task
        base = Path.cwd() / '.tmp/task16-execution'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            fixture = EvidenceFixture(temp).quality()
            ids = ['PUBLIC-A', 'PUBLIC-B']
            task = {'root_task_id': 'PUBLIC-ROOT', 'history': [], 'C': ids, 'D': ids, 'K': 10,
                'catalog': {p: {'parent_asin': p, 'title': 'corn grain', 'crop': 'corn'} for p in ids},
                'prior': dict(zip(ids, [.9, .6])), 'request': {'necessary': ['c1', 'c2'], 'preferences': []}}
            actions = iter([{'action': 'User', 'data': {}}, {'action': 'Search', 'data': {}},
                {'action': 'Finish', 'data': {'ranking': ids}}])
            search = iter([{'action': 'Lookup', 'data': {}}, {'action': 'Finish', 'data': {'analysis': 'Read actual sources.'}}])

            def model(request):
                if request['kind'] == 'interpret':
                    return {'preferences': []}
                if request['kind'] == 'thought':
                    return {'thought': 'Inspect.'}
                if request['kind'] == 'action':
                    return next(actions)
                if request['kind'] == 'agent':
                    if request['role'] == '用户画像':
                        return {'action': 'Finish', 'data': {'analysis': 'History is empty; preference unknown.'}}
                    return next(search)
                return {'revise': False, 'issues': []}

            tools = EvidenceTools(fixture.snapshot_ref, {'PUBLIC-A': 'BATCH-A', 'PUBLIC-B': 'BATCH-B'}, quality=True)
            result = run_task(task, method='B0', invoke=model, evidence=tools, policy={})
            self.assertEqual(result['status'], 'ok')
            self.assertEqual(result['observations']['PUBLIC-A']['sim_batch_id'], 'BATCH-A')
            self.assertAlmostEqual(result['observations']['PUBLIC-A']['stock']['quality'], .6)
            self.assertEqual(result['observations']['PUBLIC-A']['stock']['components']['C']['numerator'], 1)
            self.assertGreater(result['observations']['PUBLIC-A']['tool_usage']['physical_tools'], 0)

    def test_quality_ablation_keeps_unknown_stock_unknown_and_never_bypasses_eligibility(self):
        from macrec_experiment import prepare
        from macrec_recommendation import run_task
        task = prepare(source_fixture(), 'public_fixture', {'weights': [1, 1, 1], 'M': 2})['tasks']['u']
        task['prior'] = {'A': .4, 'B': .6}
        task['request']['preferences'] = [{'attribute': 'retail_stock', 'value': 'higher', 'weight': 1}]
        matches = [{'candidate': p, 'aspect': 'explicit-0', 'match': m, 'preference_refs': ['r:0'],
            'references': [{'ref': 's:' + p, 'quote': str(value)}]}
            for p, m, value in (('A', 1, 7), ('B', 0, 1))]
        evidence = lambda ids: {p: {'parent_asin': p, 'eligible': p == 'B',
            'state': 'Supported' if p == 'B' else 'Pending',
            'stock': {'supported': p == 'B', 'value': 1, 'quality': .2}, 'source': 'SIM'} for p in ids}
        result = run_task(task, method='A-quality', invoke=i1_model([], matches), evidence=evidence,
            policy={'lambda': .5, 'tau': 3})
        self.assertEqual(result['topK'], ['B'])
        self.assertEqual(result['components']['A']['score'], .4)
        self.assertEqual(result['components']['A']['terms'][0]['o'], 0)
        self.assertAlmostEqual(result['components']['B']['score'], .3)

    def test_semantic_ablation_uses_literal_observable_attributes_and_changes_the_order(self):
        from macrec_experiment import prepare
        from macrec_recommendation import run_task
        task = prepare(source_fixture(), 'public_fixture', {'weights': [1, 1, 1], 'M': 2})['tasks']['u']
        task['prior'] = {'A': .4, 'B': .6}
        evidence = lambda ids: {p: {'parent_asin': p, 'eligible': True, 'state': 'Supported',
            'stock': {'supported': False}, 'source': 'SIM'} for p in ids}
        result = run_task(task, method='A-semantic', invoke=i1_model(preference_fixture(), matches_fixture()),
            evidence=evidence, policy={'lambda': .75, 'tau': 1})
        self.assertEqual(result['topK'], ['B', 'A'])
        self.assertAlmostEqual(result['components']['A']['score'], .25)

    def test_confidence_ablation_removes_only_the_supported_history_shrinkage(self):
        from macrec_experiment import prepare
        from macrec_recommendation import run_task
        task = prepare(source_fixture(), 'public_fixture', {'weights': [1, 1, 1], 'M': 2})['tasks']['u']
        task['prior'] = {'A': .4, 'B': .6}
        evidence = lambda ids: {p: {'parent_asin': p, 'eligible': True, 'state': 'Supported',
            'stock': {'supported': False}, 'source': 'SIM'} for p in ids}
        result = run_task(task, method='A-confidence', invoke=i1_model(preference_fixture(), matches_fixture()),
            evidence=evidence, policy={'lambda': .75, 'tau': 1})
        self.assertAlmostEqual(result['components']['A']['score'], .85)
        self.assertEqual(result['components']['A']['terms'][0]['c'], 1)

    def test_located_feedback_revises_scores_and_no_feedback_keeps_the_identical_prefix(self):
        from macrec_experiment import prepare
        from macrec_recommendation import run_task
        task = prepare(source_fixture(), 'public_fixture', {'weights': [1, 1, 1], 'M': 2})['tasks']['u']
        task['prior'] = {'A': .4, 'B': .6}
        wrong = matches_fixture()
        wrong[0]['match'], wrong[1]['match'] = 0, 1
        request_sets, results = [], []
        for method in ('I1', 'A-feedback'):
            original = i1_model(preference_fixture(), wrong)
            requests = []

            def model(request):
                requests.append(copy.deepcopy(request))
                if request['kind'] == 'reflect':
                    return {'revise': True, 'issues': [{'candidate': 'A', 'aspect': 'rolled',
                        'reference': 'c:A:title', 'problem': 'Check rolled oats versus oat flakes.'}]}
                if request['kind'] == 'action' and request['context']['state']['trial'] == 1:
                    return {'action': 'Finish', 'data': {'revisions': matches_fixture()}}
                return original(request)

            evidence = lambda ids: {p: {'parent_asin': p, 'eligible': True, 'state': 'Supported',
                'stock': {'supported': False}, 'source': 'SIM'} for p in ids}
            results.append(run_task(task, method=method, invoke=model, evidence=evidence,
                policy={'lambda': .75, 'tau': 1}))
            request_sets.append(requests)
        self.assertEqual([v['topK'] for v in results[0]['versions']], [['B', 'A'], ['A', 'B']])
        self.assertEqual(results[1]['topK'], ['B', 'A'])
        self.assertEqual(request_sets[0][:len(request_sets[1])], request_sets[1])
        self.assertNotIn('reflect', [r['kind'] for r in request_sets[1]])

    def test_explicit_stock_preference_uses_production_quality_and_zero_quality_returns_to_prior(self):
        from macrec_experiment import prepare
        from macrec_recommendation import run_task
        task = prepare(source_fixture(), 'public_fixture', {'weights': [1, 1, 1], 'M': 2})['tasks']['u']
        task['prior'] = {'A': .4, 'B': .6}
        task['request']['preferences'] = [{'attribute': 'retail_stock', 'value': 'higher', 'weight': 1}]
        matches = [{'candidate': p, 'aspect': 'explicit-0', 'match': m, 'preference_refs': ['r:0'],
            'references': [{'ref': 's:' + p, 'quote': str(value)}]}
            for p, m, value in (('A', 1, 7), ('B', 0, 1))]
        observed = []
        for quality in (1, 0):
            evidence = lambda ids: {p: {'parent_asin': p, 'eligible': True, 'state': 'Supported',
                'stock': {'supported': True, 'value': 7 if p == 'A' else 1, 'quality': quality},
                'source': 'SIM'} for p in ids}
            result = run_task(task, method='I1', invoke=i1_model([], matches), evidence=evidence,
                policy={'lambda': .5, 'tau': 3})
            self.assertEqual(result['status'], 'ok')
            observed.append(result)
        self.assertAlmostEqual(observed[0]['components']['A']['score'], .7)
        self.assertEqual(observed[0]['topK'], ['A', 'B'])
        self.assertEqual(observed[1]['topK'], ['B', 'A'])
        self.assertEqual(observed[1]['components']['A']['score'], .4)
        self.assertEqual(observed[1]['components']['A']['terms'][0]['c'], 1)

    def test_i1_semantic_matches_and_short_history_weight_change_the_actual_ranking(self):
        from macrec_experiment import prepare
        from macrec_recommendation import run_task
        task = prepare(source_fixture(), 'public_fixture', {'weights': [1, 1, 1], 'M': 2})['tasks']['u']
        task['prior'] = {'A': .4, 'B': .6}
        evidence = lambda ids: {p: {'parent_asin': p, 'eligible': True, 'state': 'Supported',
            'stock': {'supported': False}, 'source': 'SIM'} for p in ids}
        result = run_task(task, method='I1', invoke=i1_model(preference_fixture(), matches_fixture()),
            evidence=evidence, policy={'lambda': .75, 'tau': 1})
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['topK'], ['A', 'B'])
        self.assertAlmostEqual(result['components']['A']['score'], .625)
        self.assertAlmostEqual(result['components']['B']['score'], .375)
        self.assertEqual(result['components']['A']['terms'][0]['c'], .5)

    def test_b0_search_observation_and_reflection_change_the_second_solution(self):
        from macrec_experiment import prepare
        from macrec_recommendation import run_task
        task = prepare(source_fixture(), 'public_fixture', {'weights': [1, 1, 1], 'M': 2})['tasks']['u']
        requests = []
        actions = iter([{'action': 'User', 'data': {}}, {'action': 'Search', 'data': {}},
            {'action': 'Finish', 'data': {'ranking': ['B', 'A']}},
            {'action': 'Finish', 'data': {'ranking': ['A', 'B']}}])
        search = iter([{'action': 'Lookup', 'data': {'candidates': ['A', 'B']}},
            {'action': 'Finish', 'data': {'analysis': 'Read actual SIM stock observation.'}}])

        def model(request):
            requests.append(copy.deepcopy(request))
            if request['kind'] == 'interpret':
                return {'preferences': []}
            if request['kind'] == 'thought':
                return {'thought': 'Compare allowed sources.'}
            if request['kind'] == 'action':
                return next(actions)
            if request['kind'] == 'agent':
                if request['role'] == '用户画像':
                    return {'action': 'Finish', 'data': {'analysis': 'Prefer rolled oats, supported by h0.text.'}}
                return next(search)
            return {'revise': True, 'issues': ['Compare A with the observed source again.']}

        evidence = lambda ids: {p: {'parent_asin': p, 'eligible': True, 'state': 'Supported',
            'stock': {'supported': True, 'value': 7, 'quality': 1}, 'source': 'SIM'} for p in ids}
        result = run_task(task, method='B0', invoke=model, evidence=evidence, policy={})
        self.assertEqual(result['topK'], ['A', 'B'])
        self.assertEqual([v['ranking'] for v in result['versions']], [['B', 'A'], ['A', 'B']])
        next_action = [r for r in requests if r['kind'] == 'action'][2]
        self.assertIn('Read actual SIM stock', str(next_action))
        self.assertIn('observed source again', str([r for r in requests if r['kind'] == 'action'][-1]))


class IndependentEvaluation(unittest.TestCase):
    def test_old_r_s_m_handwritten_metric_examples_remain_equal_and_na_stays_na(self):
        from tests.test_experiment_evaluation import example
        from experiment_evaluation import score_task as old_score
        from macrec_evaluation import score_task
        for method in ('R','S','M'):
            task, execution, reference = example(method=method)
            new_task = {'root_task_id': task['root_task_id'], 'method': method, 'scene': 'V00',
                'C': task['C'], 'D': task['C'], 'binding_id': 'PUBLIC'}
            observed = {'status': 'ok', 'topK': execution['delivered'], 'binding_id': 'PUBLIC',
                'observations': {p: {'eligible': True} for p in execution['G']}}
            independent = {'target': reference['target'], 'states': reference['states'], 'binding_id': 'PUBLIC'}
            self.assertEqual(score_task(new_task, observed, independent)['metrics'], old_score(task, execution, reference)['metrics'])
            reference['states']['b'] = 'Refuted'
            independent['states']['b'] = 'Refuted'
            current = score_task(new_task, observed, independent)
            self.assertIsNone(current['metrics']['10']['SJ_NDCG'])
            self.assertEqual(current['metrics'], old_score(task, execution, reference)['metrics'])
        c = ['PUBLIC-%02d' % i for i in range(12)]
        task = {'root_task_id': 'u', 'method': 'I1', 'scene': 'V00', 'C': c, 'D': c, 'binding_id': 'PUBLIC'}
        current = score_task(task, {'status':'ok','topK':c[:10],'binding_id':'PUBLIC',
            'observations': {p:{'eligible':True} for p in c}},
            {'target':c[10],'states':dict.fromkeys(c,'Supported'),'binding_id':'PUBLIC'})
        self.assertEqual(current['recall'], 1)
        self.assertEqual(current['metrics']['10']['NDCG_P'], 0)

    def test_real_reference_cli_exports_only_existing_development_identities(self):
        base = Path.cwd() / '.tmp/task16-execution'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            output = Path(temp) / 'development-reference.json'
            result = subprocess.run([sys.executable, '-B', 'macrec_evaluation.py', 'references',
                '--output', str(output)], cwd=Path.cwd(), capture_output=True, text=True,
                encoding='utf-8', timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary['users'], 320)
            self.assertEqual(summary['test_users_exported'], 0)
            cohort = json.loads((Path.cwd() / summary['cohort']['path']).read_bytes())
            self.assertEqual(len(cohort), 320)
            self.assertTrue(all(set(row) == {'root_task_id', 'split', 'split_hash'} and row['split'] == 'dev' for row in cohort))
            self.assertEqual(len({row['split_hash'] for row in cohort}), 320)

    def test_selection_cli_keeps_all_content_trials_and_reports_recall_without_inserting_target(self):
        base = Path.cwd() / '.tmp/task16-execution'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            directory = Path(temp)
            inputs, reference = directory / 'inputs.json', directory / 'reference.json'
            inputs.write_text(json.dumps(source_fixture()), encoding='utf-8')
            reference.write_text(json.dumps({'targets': {'u': 'A'},
                'states': {'V00': {'A': 'Supported', 'B': 'Supported'}}}), encoding='utf-8')
            output = directory / 'selection.json'
            result = subprocess.run([sys.executable, '-B', 'macrec_evaluation.py', 'select',
                '--inputs', str(inputs), '--references', str(reference), '--output', str(output)],
                cwd=Path.cwd(), capture_output=True, text=True, encoding='utf-8', timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.exists())
            chosen = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(len(chosen['trials']), 3)
            self.assertEqual(chosen['M'], 50)
            self.assertEqual([r['M'] for r in chosen['coverage']], [50, 100, 200])
            self.assertEqual(chosen['users'], 1)
            self.assertEqual(chosen['offline']['summary']['planned_rows'], 3)
            self.assertEqual(set(chosen['offline']['summary']['groups']), {'CB/V00', 'CB-D/V00', 'R/V00'})
            self.assertTrue(all(r['status'] == 'scored' for r in chosen['offline']['scores']))

    def test_bootstrap_uses_user_pairs_and_prespecified_ndcg_contrast(self):
        from macrec_evaluation import score_task, summarize
        tasks, scores = [], []
        for user in ('u', 'v'):
            for method in ('B0', 'I1'):
                task = {'root_task_id': user, 'method': method, 'scene': 'V00', 'C': ['A', 'B'],
                    'D': ['A', 'B'], 'binding_id': user}
                reference = {'target': 'A', 'states': {'A': 'Supported', 'B': 'Supported'}, 'binding_id': user}
                observation = {'status': 'ok', 'topK': ['A', 'B'] if method == 'I1' else ['B', 'A'],
                    'binding_id': user, 'observations': {p: {'eligible': True} for p in ('A', 'B')}}
                tasks.append(task)
                scores.append(score_task(task, observation, reference))
        comparison = summarize({'users': ['u', 'v'], 'tasks': tasks}, scores)['comparisons']['I1-B0']
        self.assertEqual(comparison['users'], 2)
        self.assertEqual(comparison['confidence'], .95)
        self.assertAlmostEqual(comparison['point'], .36907024642854247)
        self.assertAlmostEqual(comparison['interval'][0], .36907024642854247)
        self.assertEqual(comparison['interval'][0], comparison['interval'][1])

    def test_summary_reports_recall_and_all_users_and_does_not_score_unstarted_as_observed_zero(self):
        from macrec_evaluation import score_task, summarize
        first = {'root_task_id': 'u', 'method': 'I1', 'scene': 'V00', 'C': ['A', 'B'],
            'D': ['A', 'B'], 'binding_id': 'u'}
        second = first | {'root_task_id': 'v', 'D': ['B'], 'binding_id': 'v'}
        ref = {'target': 'A', 'states': {'A': 'Supported', 'B': 'Supported'}}
        one = {'status': 'ok', 'topK': ['B', 'A'], 'binding_id': 'u',
            'observations': {p: {'eligible': True} for p in ('A', 'B')}}
        two = one | {'topK': ['B'], 'binding_id': 'v'}
        scores = [score_task(first, one, ref | {'binding_id': 'u'}),
            score_task(second, two, ref | {'binding_id': 'v'})]
        report = summarize({'users': ['u', 'v'], 'tasks': [first, second]}, scores)['groups']['I1/V00']
        self.assertEqual(report['users'], 2)
        self.assertEqual(report['recall'], .5)
        self.assertEqual(report['metrics']['10']['HR'], .5)
        self.assertAlmostEqual(report['metrics']['10']['NDCG_P'], .31546487678572877)
        scores[1] = score_task(second, None, ref | {'binding_id': 'v'})
        incomplete = summarize({'users': ['u', 'v'], 'tasks': [first, second]}, scores)['groups']['I1/V00']
        self.assertIsNone(incomplete['metrics']['10']['HR'])
        self.assertEqual(incomplete['conservative_lower_bound']['10']['HR'], .5)
        self.assertEqual(incomplete['states']['not_started'], 1)

    def test_rank_two_failure_and_unresolved_have_distinct_independent_scores(self):
        from macrec_evaluation import score_task
        task = {'root_task_id': 'u', 'method': 'I1', 'scene': 'V00', 'C': ['A', 'B'],
            'D': ['A', 'B'], 'binding_id': 'binding-u'}
        reference = {'target': 'A', 'states': {'A': 'Supported', 'B': 'Supported'}, 'binding_id': 'binding-u'}
        observed = {'status': 'ok', 'topK': ['B', 'A'], 'binding_id': 'binding-u',
            'observations': {p: {'eligible': True, 'state': 'Supported'} for p in ('A', 'B')}}
        scored = score_task(task, observed, reference)
        self.assertEqual(scored['method'], 'I1')
        self.assertEqual(scored['metrics']['1']['HR'], 0)
        self.assertAlmostEqual(scored['metrics']['5']['NDCG_P'], .6309297535714575)
        self.assertEqual(score_task(task, observed | {'status': 'failed_model'}, reference)['metrics']['10']['HR'], 0)
        self.assertIsNone(score_task(task, observed | {'status': 'unresolved'}, reference)['metrics']['10']['HR'])
        self.assertEqual(score_task(task, None, reference)['status'], 'not_started')




if __name__ == '__main__':
    unittest.main(verbosity=2)
