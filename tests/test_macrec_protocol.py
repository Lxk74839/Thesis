"""Protocol regressions from immutable real replies; transports are offline replays."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
import subprocess
import shutil
import sys

PROJECT = Path(__file__).resolve().parents[1]
AUDIT = PROJECT / '.scratch/task16-execution-v2-20261023/protocol-v2-20261024'


def captures():
    rows = json.loads((AUDIT / 'real-response-manifest.json').read_bytes())
    for row in rows:
        for key in ('request', 'response'):
            raw = (PROJECT / row[key]['path']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != row[key]['sha256']:
                raise AssertionError('Historical response changed')
    return rows


class RoleProtocol(unittest.TestCase):
    def test_all_14_historical_business_payloads_retain_their_original_probe_verdict_offline(self):
        from macrec_protocol import decode, strict_json
        from macrec_experiment import read_unit_result, OUTPUT
        plan = json.loads((OUTPUT/'execution-revisions/full-before-v00-20261024/run-plan.json').read_bytes())
        accepted = 0
        for row in captures():
            wire = json.loads((PROJECT/row['request']['path']).read_bytes())
            request = json.loads(wire['input'][1]['content'])
            response = json.loads((PROJECT/row['response']['path']).read_bytes())
            text = ''.join(p['text'] for o in response['output'] if o['type']=='message' for p in o['content'] if p['type']=='output_text')
            unit = next(u for s in plan['stages'] for u in s['units'] if u['id']==row['unit'])
            historical = read_unit_result(OUTPUT,unit)
            try:
                decode(strict_json(text)['data_json'],request)
                passed = True
            except ValueError:
                passed = False
            with self.subTest(request=row['id'][:10]):
                self.assertEqual(passed,historical['passed'])
            accepted += passed
        self.assertEqual(accepted,6)
        self.assertEqual(len(captures()),14)

    def test_freeze_v2_keeps_inputs_and_old_records_with_eight_fixed_probes_and_58_active_units(self):
        result = subprocess.run([sys.executable,'-B','macrec_experiment.py','freeze-protocol-v2'],cwd=PROJECT,
            capture_output=True,text=True,encoding='utf-8',timeout=120)
        self.assertEqual(result.returncode,0,result.stderr)
        metadata = json.loads(result.stdout.splitlines()[-1])
        from macrec_experiment import read_ref
        plan = read_ref(metadata['plan'])
        previous = read_ref(plan['execution']['previous_execution'])
        self.assertEqual(plan['panel'],previous['panel'])
        self.assertEqual(plan['model_index'],previous['model_index'])
        self.assertEqual([len(s['units']) for s in plan['stages'][:5]],[1,8,16,32,1])
        self.assertEqual(plan['execution']['max_calls'],1504)
        self.assertEqual(plan['execution']['retained_legacy_calls'],14)
        self.assertEqual(plan['business_protocol'],'macrec-agri-v2')
        for unit in plan['stages'][1]['units']:
            self.assertEqual(read_ref(unit['model']),{'effort':'medium','quota':'full'})
        before = {(u['root_id'],u['method']):u for u in previous['stages'][3]['units']}
        for unit in plan['stages'][3]['units']:
            for field in ('root_id','method','task','catalog','materials','scene','limit'):
                self.assertEqual(unit[field],before[unit['root_id'],unit['method']][field])
        self.assertFalse((PROJECT/'data/recommendation-runtime-audit/macrec-agri-dev-task16/protocol-bindings/macrec-agri-v2/authorization.json').exists())
        self.assertEqual(len(captures()),14)

    def test_fixed_medium_full_eight_business_probes_select_one_configuration_for_main(self):
        from macrec_experiment import prepare, store, execute_unit, read_ref
        from task16_control import Session
        from tests.test_macrec import source_fixture, native_fixture, i1_model, preference_fixture, matches_fixture
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp/task16-execution') as temp:
            directory = Path(temp)
            (directory/'budget.json').write_text(json.dumps({'max_calls':1504,'max_new_bytes':10*1024**3,
                'dispatch_deadline_utc':time.time()+3600,'deadline_utc':time.time()+7200}), encoding='utf-8')
            task = prepare(source_fixture(),'public_fixture',{'weights':[1,1,1],'M':2})['tasks']['u']
            model = store(directory/'model.json',{'effort':'medium','quota':'full'})
            material = store(directory/'material.json',{'candidates':{p:{'parent_asin':p,'eligible':True,
                'stock':{'supported':False}} for p in ('A','B')}})
            wires, parameters = [], []
            main_model = i1_model(preference_fixture(),matches_fixture())
            def transport(wire):
                wires.append(wire)
                request = json.loads(wire['input'][1]['content'])
                if request['kind']=='interpret':
                    value = {'necessary':['c1','c2'],'preferences':[],'unknown':[]}
                elif request['context'].get('business_probe'):
                    data = ({'ranking':[1,0]} if request['kind']=='action' else
                        {'preferences':preference_fixture()} if request['role']=='用户画像' else {'matches':matches_fixture()})
                    value = {'action':'Finish','data':data}
                else:
                    value = main_model(request)
                return {'status':'completed','usage':{'input_tokens':100,'output_tokens':40},
                    'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(native_fixture(wire,value))}]}]}
            for root in ('u','v'):
                task_ref = store(directory/(root+'.json'), task | {'root_task_id':root})
                user = None
                for shape in ('interpret','action','User','Items'):
                    unit = {'id':root+'-'+shape+'-v2','root_id':root,'phase':'parameters','operation':'probe',
                        'business_protocol':'macrec-agri-v2','shape':shape,'method':'B0' if shape=='action' else 'I1',
                        'scene':'V00','limit':1,'model':model,'task':task_ref,'materials':material}
                    if shape=='Items':
                        unit['user_probe'] = user
                    session = Session(directory,namespace='fixed-eight-v2',phase='parameters',unit=unit['id'],limit=1)
                    session.transport = transport
                    self.assertTrue(read_ref(execute_unit(unit,session)['result'])['passed'])
                    parameters.append(unit)
                    if shape=='User':
                        user = unit
            main = {k:v for k,v in parameters[0].items() if k not in ('shape','model')}
            main.update(id='u-I1-v2',root_id='u',operation='recommend',phase='v00-main',method='I1',limit=37,
                policy={'lambda':.5,'tau':3},parameter_stage=store(directory/'parameters.json',parameters),
                model_contract=store(directory/'contract.json',{'selection_priority':[['medium','full']]}))
            session = Session(directory,namespace='fixed-eight-v2',phase='v00-main',unit=main['id'],limit=37)
            session.transport = transport
            result = read_ref(execute_unit(main,session)['result'])
            self.assertEqual(result['status'],'ok')
            self.assertEqual(result['model_configuration'],{'effort':'medium','quota':'full'})
            self.assertEqual(len(parameters),8)
            self.assertTrue(all(w['reasoning']['effort']=='medium' for w in wires))

    def test_new_protocol_health_preserves_but_does_not_inherit_old_error_burst(self):
        from macrec_experiment import BusinessClient
        from task16_control import Session
        legacy_health = PROJECT/'data/recommendation-runtime-audit/macrec-agri-dev-task16/business-health'
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp/task16-execution') as temp:
            directory = Path(temp)
            (directory/'business-health').mkdir()
            failures = sorted((p for p in legacy_health.glob('*.json') if not json.loads(p.read_bytes())['ok']),
                key=lambda p:json.loads(p.read_bytes())['at'])[-3:]
            for path in failures:
                shutil.copyfile(path, directory/'business-health'/path.name)
            old = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (directory/'business-health').glob('*.json')}
            (directory/'budget.json').write_text(json.dumps({'max_calls':10,'max_new_bytes':10*1024**3,
                'dispatch_deadline_utc':time.time()+120,'deadline_utc':time.time()+240}), encoding='utf-8')
            session = Session(directory,namespace='new-health',phase='parameters',unit='u',limit=8)
            client = BusinessClient(session,{'effort':'medium','quota':'full'},transport=lambda body:{
                'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':
                '{"necessary":["c1","c2"],"preferences":[],"unknown":[]}'}]}]})
            request = {'kind':'interpret','role':'需求解析','context':{'allowed':{
                'session':'first','request':{'necessary':['c1','c2'],'preferences':[]}}}}
            self.assertEqual(client(request)['preferences'],[])
            client.validated(True)
            for i in range(4):
                request['context']['allowed']['session'] = str(i)
                client.transport = lambda body:{'status':'completed','output':[{'type':'message',
                    'content':[{'type':'output_text','text':'{}'}]}]}
                with self.assertRaisesRegex(ValueError, '^task16_business_error_burst$' if i==3 else '^macrec_business_response_shape:'):
                    client(request)
            self.assertEqual(old,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (directory/'business-health').glob('*.json')})
            self.assertEqual(len(list((directory/'business-health/macrec-agri-v2').glob('*.json'))),4)

    def test_known_wrappers_explain_old_failures_without_changing_historical_records(self):
        source = subprocess.check_output(['git','show','8004ae8aba1b40b662001c5078521074c6509674:macrec_experiment.py'], cwd=PROJECT)
        legacy = {'__name__':'historical_client_offline','__file__':str(PROJECT/'macrec_experiment.py')}
        exec(compile(source, str(PROJECT/'macrec_experiment.py'), 'exec'), legacy)
        from task16_control import Session
        plan = json.loads((PROJECT/'data/recommendation-runtime-audit/macrec-agri-dev-task16/execution-revisions/full-before-v00-20261024/run-plan.json').read_bytes())
        for prefix in ('162efcef1b','558ef1a786'):
            capture = next(r for r in captures() if r['id'].startswith(prefix))
            unit = next(u for s in plan['stages'] for u in s['units'] if u['id']==capture['unit'])
            original = json.loads((PROJECT/capture['response']['path']).read_bytes())
            for unwrap in (False, True):
                with self.subTest(request=prefix, offline_unwrap=unwrap), tempfile.TemporaryDirectory(dir=PROJECT/'.tmp/task16-execution') as temp:
                    directory = Path(temp)
                    (directory/'budget.json').write_text(json.dumps({'max_calls':2,'max_new_bytes':10*1024**3,
                        'dispatch_deadline_utc':time.time()+120,'deadline_utc':time.time()+240}), encoding='utf-8')
                    reply = copy.deepcopy(original)
                    if unwrap:
                        part = next(p for o in reply['output'] if o['type']=='message' for p in o['content'] if p['type']=='output_text')
                        business = json.loads(json.loads(part['text'])['data_json'])
                        part['text'] = json.dumps({'data_json':json.dumps(business['action'])})
                    session = Session(directory, namespace='historical-offline-only', phase='parameters', unit=unit['id'], limit=1)
                    cfg = legacy['read_ref'](unit['model'])
                    client = legacy['BusinessClient'](session, cfg, transport=lambda wire:reply)
                    result = legacy['probe'](unit, session, legacy['task_for'](unit), client, cfg)
                    self.assertEqual(result['passed'], unwrap)
        self.assertEqual(len(captures()),14)

    def test_native_json_rejects_real_malformed_reply_duplicate_fields_and_role_wrappers(self):
        from macrec_experiment import BusinessClient
        from task16_control import Session
        malformed = next(r for r in captures() if r['id'].startswith('c29ce160cb'))
        original = json.loads((PROJECT/malformed['response']['path']).read_bytes())
        text = ''.join(p['text'] for o in original['output'] if o['type']=='message' for p in o['content'] if p['type']=='output_text')
        historical_inner = json.loads(text)['data_json']
        cases = [historical_inner, '{"necessary":["c1","c2"],"preferences":[],"preferences":[],"unknown":[]}',
            '{"interpret":{"necessary":["c1","c2"],"preferences":[],"unknown":[]}}',
            '{"necessary":["c1","c2"],"preferences":[],"unknown":[],"extra":NaN}']
        for raw in cases:
            with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp/task16-execution') as temp:
                directory = Path(temp)
                (directory/'budget.json').write_text(json.dumps({'max_calls':2,'max_new_bytes':10*1024**3,
                    'dispatch_deadline_utc':time.time()+120,'deadline_utc':time.time()+240}), encoding='utf-8')
                response = {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':raw}]}]}
                client = BusinessClient(Session(directory,namespace='strict',phase='parameters',unit='u',limit=1),
                    {'effort':'medium','quota':'full'},transport=lambda wire:response)
                with self.assertRaisesRegex(ValueError,'^macrec_business_response_shape:'):
                    client({'kind':'interpret','role':'需求解析','context':{'allowed':{
                        'request':{'necessary':['c1','c2'],'preferences':[]}}}})

    def test_native_roles_lookup_and_complete_matrix_drive_the_unchanged_i1_score(self):
        from macrec_experiment import BusinessClient, prepare
        from macrec_recommendation import run_task
        from task16_control import Session
        from tests.test_macrec import source_fixture, preference_fixture
        task = prepare(source_fixture(), 'public_fixture', {'weights':[1,1,1],'M':2})['tasks']['u']
        task['prior'] = {'A':.4,'B':.6}
        with tempfile.TemporaryDirectory(dir=PROJECT / '.tmp/task16-execution') as temp:
            directory = Path(temp)
            (directory/'budget.json').write_text(json.dumps({'max_calls':40,'max_new_bytes':10*1024**3,
                'dispatch_deadline_utc':time.time()+120,'deadline_utc':time.time()+240}), encoding='utf-8')
            actions, searched = iter(['User','Search','Items','Finish']), False
            wires = []
            def transport(wire):
                nonlocal searched
                wires.append(wire)
                request = json.loads(wire['input'][1]['content'])
                kind, role = request['kind'], request['role']
                if kind == 'interpret':
                    value = {'necessary':['c1','c2'],'preferences':[],'unknown':[]}
                elif kind == 'thought':
                    value = {'thought':'Compare the actual supported evidence.'}
                elif kind == 'reflect':
                    value = {'revise':False,'issues':[]}
                elif kind == 'action':
                    action = next(actions)
                    value = {'action':action,'data':{'revisions_matrix':[]} if action=='Finish' else {'instruction':'Use allowed sources.'}}
                elif role == '用户画像':
                    value = {'action':'Finish','data':{'preferences':preference_fixture()}}
                elif role == '生命周期追溯':
                    value = {'action':'Finish','data':{'analysis':'Read actual SIM observations.'}} if searched else {
                        'action':'Lookup','data':{'candidates':[0,1]}}
                    searched = True
                else:
                    value = {'action':'Finish','data':{'matrix':[{'i':i,'m':[1 if c['parent_asin']=='A' else 0],'f':[0]}
                        for i,c in enumerate(request['context']['allowed']['candidates'])]}}
                return {'status':'completed','usage':{'input_tokens':100,'output_tokens':40},
                    'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(value)}]}]}
            client = BusinessClient(Session(directory, namespace='native', phase='v00-main', unit='u', limit=37),
                {'effort':'medium','quota':'full'}, transport=transport)
            result = run_task(task, method='I1', invoke=client,
                evidence=lambda ids:{p:{'parent_asin':p,'eligible':True,'stock':{'supported':False}} for p in ids},
                policy={'lambda':.75,'tau':1})
            self.assertEqual(result['status'],'ok',result.get('reason'))
            self.assertEqual(result['topK'],['A','B'])
            self.assertAlmostEqual(result['components']['A']['score'], .625)
            self.assertTrue(all('data_json' not in w['text']['format']['schema']['properties'] for w in wires))

    def test_probe_and_main_filter_the_same_unsupported_real_preferences_including_empty_profiles(self):
        from macrec_experiment import prepare, store, execute_unit, read_ref
        from macrec_recommendation import run_task
        from tests.test_macrec import source_fixture, i1_model
        from task16_control import Session
        row = next(r for r in captures() if r['id'].startswith('b547a34806'))
        wire = json.loads((PROJECT / row['request']['path']).read_bytes())
        original = json.loads((PROJECT / row['response']['path']).read_bytes())
        text = ''.join(p['text'] for o in original['output'] if o['type']=='message' for p in o['content'] if p['type']=='output_text')
        proposed = json.loads(json.loads(text)['data_json'])['data']['preferences']
        for empty in (False, True):
            prefs = proposed[1:] if empty else proposed
            with self.subTest(empty=empty), tempfile.TemporaryDirectory(dir=PROJECT / '.tmp/task16-execution') as temp:
                directory = Path(temp)
                (directory / 'budget.json').write_text(json.dumps({'max_calls':2,'max_new_bytes':10*1024**3,
                    'dispatch_deadline_utc':time.time()+120,'deadline_utc':time.time()+240}), encoding='utf-8')
                task = prepare(source_fixture(), 'public_fixture', {'weights':[1,1,1],'M':2})['tasks']['u']
                task['history'] = json.loads(wire['input'][1]['content'])['context']['allowed']['history']
                unit = {'id':'User','root_id':'u','phase':'parameters','operation':'probe','shape':'User',
                    'method':'I1','scene':'V00','limit':1,'task':store(directory/'task.json',task),
                    'model':store(directory/'model.json',{'effort':'medium','quota':'full'}),
                    'materials':store(directory/'material.json',{'candidates':{p:{'parent_asin':p,
                        'eligible':True,'stock':{'supported':False}} for p in ('A','B')}})}
                session = Session(directory, namespace='consistent-profile', phase='parameters', unit='User', limit=1)
                session.transport = lambda body:{'status':'completed','usage':{'input_tokens':100,'output_tokens':50},
                    'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(
                        {'action':'Finish','data':{'preferences':prefs}})}]}]}
                result = read_ref(execute_unit(unit, session)['result'])
                self.assertTrue(result['passed'])
                self.assertEqual(len(result['validated_preferences']), 0 if empty else 1)
                self.assertEqual(len(result['rejected_preferences']), 1)
                matches = [] if empty else [{'candidate':p,'aspect':'p1','match':m,
                    'preference_refs':['h0.text'],'references':[{'ref':'c:'+p+':crop','quote':crop}]}
                    for p,m,crop in (('A',1,'oats'),('B',0,'corn'))]
                main = run_task(task, method='I1', invoke=i1_model(prefs,matches),
                    evidence=lambda ids:{p:{'parent_asin':p,'eligible':True} for p in ids}, policy={'lambda':.5,'tau':3})
                self.assertEqual(main['status'],'ok')
                self.assertEqual(main['preferences'], result['validated_preferences'])
                self.assertEqual(main['rejected_preferences'], result['rejected_preferences'])

    def test_real_oats_lover_preference_affects_ranking_without_losing_negation_or_conflict_guards(self):
        from macrec_experiment import prepare
        from macrec_recommendation import run_task
        from tests.test_macrec import source_fixture, i1_model
        row = next(r for r in captures() if r['id'].startswith('b547a34806'))
        wire = json.loads((PROJECT / row['request']['path']).read_bytes())
        logical = json.loads(wire['input'][1]['content'])
        reply = json.loads((PROJECT / row['response']['path']).read_bytes())
        text = ''.join(p['text'] for o in reply['output'] if o['type']=='message' for p in o['content'] if p['type']=='output_text')
        proposed = json.loads(json.loads(text)['data_json'])['data']['preferences'][:1]
        cases = [('actual', logical['context']['allowed']['history'], proposed, True),
            ('negated', [{'parent_asin':'H','text':'I am not an oats lover.'}],
                [proposed[0] | {'supports':[{'ref':'h0.text','quote':'not an oats lover','stance':1}]}], False),
            ('conflict', [{'parent_asin':'H','text':'As an oats lover. I avoid oats.'}],
                [proposed[0] | {'supports':[{'ref':'h0.text','quote':'As an oats lover','stance':1},
                    {'ref':'h0.text','quote':'I avoid oats','stance':-1}]}], False)]
        for name, history, prefs, supported in cases:
            task = prepare(source_fixture(), 'public_fixture', {'weights':[1,1,1],'M':2})['tasks']['u']
            task['history'], task['prior'] = history, {'A':.4,'B':.6}
            matches = [{'candidate':p,'aspect':'p1','match':m,'preference_refs':['h0.text'],
                'references':[{'ref':'c:'+p+':crop','quote':crop}]}
                for p,m,crop in (('A',1,'oats'),('B',0,'corn'))] if supported else []
            with self.subTest(case=name):
                result = run_task(task, method='I1', invoke=i1_model(prefs,matches),
                    evidence=lambda ids:{p:{'parent_asin':p,'eligible':True} for p in ids}, policy={'lambda':.75,'tau':1})
                self.assertEqual(result['status'],'ok')
                self.assertEqual(result['topK'], ['A','B'] if supported else ['B','A'])
                self.assertEqual(len(result['preferences']), int(supported))

    def test_interpreter_sends_only_the_current_request_not_history_or_candidates(self):
        from macrec_experiment import BusinessClient, prepare
        from tests.test_macrec import source_fixture
        from task16_control import Session
        task = prepare(source_fixture(), 'public_fixture', {'weights':[1,1,1], 'M':2})['tasks']['u']
        with tempfile.TemporaryDirectory(dir=PROJECT / '.tmp/task16-execution') as temp:
            directory = Path(temp)
            (directory / 'budget.json').write_text(json.dumps({'max_calls':2,'max_new_bytes':10*1024**3,
                'dispatch_deadline_utc':time.time()+120,'deadline_utc':time.time()+240}), encoding='utf-8')
            wires = []
            def transport(wire):
                wires.append(wire)
                return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text',
                    'text':json.dumps({'necessary':['c1','c2'],'preferences':[],'unknown':[]})}]}]}
            client = BusinessClient(Session(directory, namespace='interpret', phase='parameters', unit='u', limit=1),
                {'effort':'medium','quota':'full'}, transport=transport)
            reply = client({'kind':'interpret','role':'需求解析','context':{'trial':0,'allowed':{
                'session':'u','request':task['request'],'history':task['history'],
                'candidates':[task['catalog'][p] for p in task['D']]}}})
            self.assertEqual(reply['preferences'], [])
            sent = json.loads(wires[0]['input'][1]['content'])
            self.assertEqual(set(sent['context']['allowed']), {'session','request'})
            self.assertNotIn('I prefer rolled oats.', json.dumps(sent))

    def test_all_14_real_replays_use_business_field_schemas_instead_of_an_unchecked_string(self):
        from macrec_experiment import BusinessClient
        from task16_control import Session
        rows = captures()
        self.assertEqual(len(rows), 14)
        for row in rows:
            with self.subTest(request=row['id'][:10]), tempfile.TemporaryDirectory(dir=PROJECT / '.tmp/task16-execution') as temp:
                directory = Path(temp)
                (directory / 'budget.json').write_text(json.dumps({'max_calls': 2, 'max_new_bytes': 10 * 1024**3,
                    'dispatch_deadline_utc': time.time()+120, 'deadline_utc': time.time()+240}), encoding='utf-8')
                original = json.loads((PROJECT / row['request']['path']).read_bytes())
                logical = json.loads(original['input'][1]['content'])
                # Captures already contain the wire table. Evidence is irrelevant to this schema regression.
                logical['context']['state']['observations'] = {}
                response = json.loads((PROJECT / row['response']['path']).read_bytes())
                wires = []
                def replay(wire):
                    wires.append(copy.deepcopy(wire))
                    return response
                session = Session(directory, namespace='offline-real-replay', phase='parameters', unit=row['id'], limit=1)
                client = BusinessClient(session, {'effort': 'medium', 'quota': 'full'}, transport=replay)
                try:
                    client(logical)
                except ValueError:
                    pass  # An old invalid reply is not promoted to a new successful response.
                self.assertEqual(len(wires), 1)
                schema = wires[0]['text']['format']['schema']
                self.assertNotIn('data_json', schema['properties'])
                self.assertIn('necessary' if logical['kind'] == 'interpret' else 'action', schema['properties'])
        self.assertEqual(len(captures()), 14)


if __name__ == '__main__':
    unittest.main(verbosity=2)
