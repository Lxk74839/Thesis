"""Ticket12 public preparation/rank interfaces; expected values are public literals."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from quality_fixtures import normal_fixture, scoring_fixture, reseal, wire

PROJECT = Path(__file__).resolve().parents[1]


class QualityCLITests(unittest.TestCase):
    def test_quality_stage_reports_missing_inputs_as_json(self):
        result = subprocess.run([sys.executable, str(PROJECT/'prepare_data.py'), '--stage', 'quality_fusion'],
                                cwd=PROJECT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_arguments')

    def test_prepares_two_independent_quality_views(self):
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            root = Path(temp)
            normal, config, _ = normal_fixture(root)
            output = root/'output'
            result = subprocess.run([sys.executable,str(PROJECT/'prepare_data.py'),'--stage','quality_fusion',
                '--sim-record',str(normal),'--quality-config',str(config),'--output-root',str(output)],
                cwd=PROJECT,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            record = json.loads(result.stdout)
            self.assertEqual(record['status'],'prepared_pending_independent_acceptance')
            self.assertEqual(record['inputs']['quality_config']['path'],config.relative_to(PROJECT).as_posix())
            self.assertEqual(record['inputs']['normal_record']['path'],normal.relative_to(PROJECT).as_posix())
            self.assertEqual(set(record['producer_sha256']),{'prepare_data.py','quality_fusion.py','recommendation_actions.py'})
            self.assertEqual(record['counts'],{'parents':4,'views':2})
            self.assertEqual(record['independent_acceptance'],'pending_separate_record')
            self.assertEqual(len(record['views']),2)
            for view in record['views']:
                snapshot = json.loads((output/view['snapshot_path']).read_bytes())
                self.assertEqual(snapshot['schema_version'],'quality-snapshot-0.1.0')
                materials = [json.loads(line) for line in (output/Path(view['snapshot_path']).parent/'materials.jsonl').read_bytes().splitlines()]
                self.assertEqual(sorted(r['facts']['stock_units'] for r in materials if r['kind']=='retail_status'),[25,25,50,50])

    def test_identical_reuse_preserves_prepared_record_and_rejects_changed_output(self):
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            root=Path(temp)
            normal,config,_=normal_fixture(root)
            cmd=[sys.executable,str(PROJECT/'prepare_data.py'),'--stage','quality_fusion','--sim-record',str(normal),
                 '--quality-config',str(config),'--output-root',str(root/'output')]
            first=subprocess.run(cmd,cwd=PROJECT,capture_output=True,text=True)
            self.assertEqual(first.returncode,0,first.stdout)
            record=json.loads(first.stdout)
            path=root/'output/records/sim-quality/grain-A-1.1.15-sim-quality-fusion-0.1.0.json'
            before=path.read_bytes()
            second=subprocess.run(cmd,cwd=PROJECT,capture_output=True,text=True)
            self.assertEqual(second.returncode,0,second.stdout)
            self.assertEqual(path.read_bytes(),before)
            target=root/'output'/record['components']['view-index.jsonl']['path']
            target.write_bytes(b'changed')
            third=subprocess.run(cmd,cwd=PROJECT,capture_output=True,text=True)
            failure=json.loads(third.stdout)
            self.assertEqual(failure['error']['code'],'output_conflict')
            self.assertTrue((PROJECT/failure['failure_record']).is_file())
            self.assertEqual(target.read_bytes(),b'changed')
            self.assertEqual(path.read_bytes(),before)


class QualityRankTests(unittest.TestCase):
    def test_rejects_wrong_material_stage_pre_event_issue_late_batch_and_pre_arrival_stock(self):
        from quality_fusion import rank_quality,QualityError
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            original=scoring_fixture(Path(temp))
            for case in ('wrong_stage','pre_event_issue','late_batch','pre_arrival_stock'):
                with self.subTest(case=case):
                    bind,acquired=copy.deepcopy(original);pack=acquired['candidates']['DEMO-A']
                    objects={k:json.loads(v) for k,v in pack['originals'].items()}
                    retail=next(r for r in objects.values() if r.get('kind')=='retail_status')
                    if case=='wrong_stage':
                        event=next(r for r in objects.values() if r.get('stage')=='inspection')
                        retail['event_id']=event['event_id']
                        next(r for r in pack['registrations'] if r['target_id']==retail['evidence_id'])['event_id']=event['event_id']
                    if case=='pre_event_issue':
                        sample=next(r for r in objects.values() if r.get('kind')=='inspection_sample')
                        sample['issued_at_ms']=objects[sample['event_id']]['event_start_ms']-1
                    if case=='late_batch':
                        batch=next(r for r in objects.values() if 'created_at_ms' in r)
                        batch['created_at_ms']=next(r['event_start_ms'] for r in objects.values() if r.get('stage')=='harvest')+1
                        next(r for r in pack['registrations'] if r['target_kind']=='batch')['registered_at_ms']=batch['created_at_ms']+1
                    if case=='pre_arrival_stock':
                        arrived=next(r['facts']['arrived_at_ms'] for r in objects.values() if r.get('kind')=='transport_receipt')
                        retail['valid_from_ms']=arrived-2;retail['facts']['observed_at_ms']=arrived-1
                    pack['originals']={k:wire(v) for k,v in objects.items()};reseal(bind,acquired)
                    with self.assertRaises(QualityError):rank_quality(bind,acquired)

    def test_pure_computation_is_repeatable_and_never_reads_missing_originals_or_host_files(self):
        from quality_fusion import rank_quality,QualityError
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            bind,acquired=scoring_fixture(Path(temp));before=copy.deepcopy((bind,acquired))
            with patch('builtins.open',side_effect=AssertionError('unexpected_host_IO')),patch.object(Path,'open',side_effect=AssertionError('unexpected_host_IO')):
                first=rank_quality(bind,acquired)
                self.assertEqual(rank_quality(bind,acquired),first)
            self.assertEqual((bind,acquired),before)
            other=copy.deepcopy(acquired);other['snapshot']['verify_at_ms']+=1
            with self.assertRaises(QualityError):rank_quality(bind,other)

    def test_unread_registered_stock_prevents_false_scope_closure_and_empty_C_is_defined(self):
        import hashlib
        from quality_fusion import rank_quality
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            bind,acquired=scoring_fixture(Path(temp))
            pack=acquired['candidates']['DEMO-A']
            reg=copy.deepcopy(next(r for r in pack['registrations'] if r['target_kind']=='material' and json.loads(pack['originals'][r['target_id']])['kind']=='retail_status'))
            reg.update(target_id='UNREAD-RETAIL',registration_id='UNREAD-REG',sequence=999)
            pack['registrations'].append(reg)
            reseal(bind,acquired)
            a=next(r for r in rank_quality(bind,acquired)['candidates'] if r['parent_asin']=='DEMO-A')
            self.assertEqual((a['stock_state'],a['z'],a['eligible']),('Unassessed',0,False))
            bind.update(C=[],base_scores=[],mode='mean_quality')
            bind['C_sha256']=bind['base_score_sha256']=hashlib.sha256(b'[]').hexdigest()
            self.assertEqual(rank_quality(bind,acquired)['topK'],[])

    def test_empty_unknown_preferences_and_zero_beta_keep_denominators_and_boundary_is_stable(self):
        import hashlib
        from quality_fusion import rank_quality
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            original=scoring_fixture(Path(temp))
            for case in ('empty','unknown','zero_beta','boundary','tie'):
                with self.subTest(case=case):
                    bind,acquired=copy.deepcopy(original)
                    if case=='empty':bind['preference'].update(dimensions=[],weights={})
                    if case=='unknown':bind['preference'].update(dimensions=['retail_stock','taste'],weights={'retail_stock':1,'taste':1})
                    if case=='zero_beta':bind['beta']=[0,0,0]
                    if case=='boundary':bind.update(alpha=1,mode='boundary')
                    if case=='tie':
                        bind.update(alpha=1,mode='boundary',base_scores=[.5,.5,.5,.5])
                        bind['base_score_sha256']=hashlib.sha256(wire(list(zip(bind['C'],bind['base_scores'])))).hexdigest()
                    result=rank_quality(bind,acquired)
                    a=next(r for r in result['candidates'] if r['parent_asin']=='DEMO-A')
                    if case=='empty':self.assertEqual((a['contribution'],a['score']),(0,.45))
                    if case=='unknown':
                        self.assertAlmostEqual(a['contribution'],.225,places=12)
                        self.assertIn('unsupported_attribute:taste',a['reasons'])
                    if case=='zero_beta':
                        self.assertEqual((a['q'],a['score']),(0,.45))
                        self.assertIn('zero_beta_denominator',a['reasons'])
                    if case=='boundary':self.assertEqual(result['order'],['DEMO-HI','DEMO-A','DEMO-B','DEMO-LO'])
                    if case=='tie':self.assertEqual(result['order'],['DEMO-A','DEMO-B','DEMO-HI','DEMO-LO'])

    def test_rejects_mutated_binding_nonfinite_values_and_private_answer_fields(self):
        from quality_fusion import rank_quality, QualityError
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            original=scoring_fixture(Path(temp))
            changes=[('alpha',float('nan')),('alpha',1.1),('beta',[-1,1,1]),('beta',[True,0,0]),
                     ('K',True),('K',0),('base_scores',[1,.9]),('base_scores',[1,float('inf'),.6,0]),
                     ('C',['DEMO-A']*4),('verify_at_ms',1),('snapshot_id','OTHER'),('eligible',True),
                     ('preference',{'source':'experiment_design','dimensions':['retail_stock'],'weights':{'retail_stock':-1}})]
            for key,value in changes:
                with self.subTest(key=key,value=value):
                    bind,acquired=copy.deepcopy(original);bind[key]=value
                    with self.assertRaises(QualityError):rank_quality(bind,acquired)

    def test_stock_same_attribute_checks_unit_conflict_and_arrival_consistency(self):
        from quality_fusion import rank_quality, QualityError
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            original=scoring_fixture(Path(temp))
            for case in ('location','unit','conflict','route','sample'):
                with self.subTest(case=case):
                    bind,acquired=copy.deepcopy(original)
                    pack=acquired['candidates']['DEMO-A']
                    kind='transport_receipt' if case=='route' else 'inspection_report' if case=='sample' else 'retail_status'
                    key=next(k for k,r in pack['originals'].items() if json.loads(r).get('kind')==kind)
                    row=json.loads(pack['originals'][key])
                    if case=='location':row['facts']['location_id']='OTHER-LOCATION'
                    if case=='unit':row['facts']['unit']='kg'
                    if case=='route':row['facts']['transport_segment_id']='OTHER-ROUTE'
                    if case=='sample':row['facts']['sample_id']='OTHER-SAMPLE'
                    if case=='conflict':
                        row['evidence_id']='PUBLIC-CONFLICT'
                        row['facts']['stock_units']=25
                        reg=copy.deepcopy(next(r for r in pack['registrations'] if r['target_id']==key))
                        reg.update(target_id='PUBLIC-CONFLICT',registration_id='PUBLIC-REG',sequence=999)
                        pack['registrations'].append(reg)
                        key='PUBLIC-CONFLICT'
                    pack['originals'][key]=wire(row)
                    reseal(bind,acquired)
                    if case in ('unit','route','sample'):
                        with self.assertRaises(QualityError):rank_quality(bind,acquired)
                    else:
                        result=rank_quality(bind,acquired)
                        a=next(r for r in result['candidates'] if r['parent_asin']=='DEMO-A')
                        if case=='location':
                            self.assertEqual((a['A'],a['q']),({'numerator':1,'denominator':2},.475))
                        else:
                            self.assertEqual((a['stock_state'],a['z'],a['q'],a['m']),('Conflict',0,0,0))
                            self.assertTrue(a['eligible'])

    def test_unacquired_receipt_keeps_two_check_denominator_and_unread_retail_cannot_score(self):
        from quality_fusion import rank_quality
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            bind,acquired=scoring_fixture(Path(temp))
            pack=acquired['candidates']['DEMO-A']
            receipt=next(k for k,r in pack['originals'].items() if json.loads(r).get('kind')=='transport_receipt')
            pack['originals'].pop(receipt)
            result=rank_quality(bind,acquired)
            a=next(r for r in result['candidates'] if r['parent_asin']=='DEMO-A')
            self.assertEqual(a['A'],{'numerator':0,'denominator':2})
            self.assertEqual(a['q'],.35)
            self.assertIn('unacquired_arrival',a['reasons'])
            self.assertEqual(a['citations']['retail_stock']['pointer'],'/facts/stock_units')
            retail=next(k for k,r in pack['originals'].items() if json.loads(r).get('kind')=='retail_status')
            pack['originals'].pop(retail)
            result=rank_quality(bind,acquired)
            a=next(r for r in result['candidates'] if r['parent_asin']=='DEMO-A')
            self.assertEqual((a['z'],a['q'],a['m'],a['eligible']),(0,0,0,False))
            self.assertEqual(a['stock_state'],'Unassessed')
            self.assertNotIn('DEMO-A',result['G'])

    def test_public_stock_quality_changes_qualified_order_with_exact_scores(self):
        from quality_fusion import rank_quality
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            binding,acquired=scoring_fixture(Path(temp))
            result=rank_quality(binding,acquired)
            self.assertEqual(result['order'],['DEMO-B','DEMO-A','DEMO-HI','DEMO-LO'])
            rows={r['parent_asin']:r for r in result['candidates']}
            self.assertEqual(rows['DEMO-A']['score'],.675)
            self.assertEqual(rows['DEMO-B']['score'],.75)
            self.assertEqual((rows['DEMO-A']['q'],rows['DEMO-B']['q']),(.6,.9))
            self.assertEqual(rows['DEMO-A']['C'],{'numerator':1,'denominator':1})
            self.assertEqual(rows['DEMO-A']['A'],{'numerator':2,'denominator':2})
            self.assertEqual(rows['DEMO-A']['m'],.75)

    def test_no_quality_changes_only_q_weighting(self):
        from quality_fusion import rank_quality
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            bind,acquired=scoring_fixture(Path(temp))
            bind['mode']='no_quality'
            result=rank_quality(bind,acquired)
            self.assertEqual(result['order'],['DEMO-A','DEMO-B','DEMO-HI','DEMO-LO'])
            a=next(r for r in result['candidates'] if r['parent_asin']=='DEMO-A')
            self.assertEqual((a['score'],a['q'],a['effective_q']),(.825,.6,1))

    def test_mean_quality_uses_same_supported_candidate_denominator(self):
        from quality_fusion import rank_quality
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            bind,acquired=scoring_fixture(Path(temp))
            bind['mode']='mean_quality'
            result=rank_quality(bind,acquired)
            self.assertEqual(result['mean_quality'],{'value':.675,'denominator':4})
            self.assertEqual(result['order'],['DEMO-A','DEMO-B','DEMO-HI','DEMO-LO'])
            a=next(r for r in result['candidates'] if r['parent_asin']=='DEMO-A')
            self.assertEqual(a['score'],.703125)

    def test_only_admissible_normal_v1_originals_can_support_scoring(self):
        from quality_fusion import rank_quality, QualityError
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            original_b,original_a=scoring_fixture(Path(temp))
            for case in ('digest','batch','permission','expiry','v2','actions','event_path'):
                with self.subTest(case=case):
                    bind,acquired=copy.deepcopy((original_b,original_a))
                    pack=acquired['candidates']['DEMO-A']
                    key=next(k for k,raw in pack['originals'].items() if json.loads(raw).get('kind')=='retail_status')
                    row=json.loads(pack['originals'][key])
                    if case=='digest':row['facts']['stock_units']=50
                    if case=='batch':row['sim_batch_id']='WRONG'
                    if case=='expiry':row['valid_to_ms']=bind['verify_at_ms']
                    if case=='v2':row['version']=2
                    pack['originals'][key]=wire(row)
                    if case=='permission':
                        policy=json.loads(acquired['policy_bytes'])
                        policy['read_scope']['material_kinds'].remove('retail_status')
                        acquired['policy_bytes']=wire(policy)+b'\n'
                    if case=='actions':acquired['actions_bytes']=b'{}\n'
                    if case=='event_path':
                        ekey=next(k for k,raw in pack['originals'].items() if json.loads(raw).get('stage')=='retail')
                        event=json.loads(pack['originals'][ekey]);event['predecessor_event_ids']=[]
                        pack['originals'][ekey]=wire(event)
                    reseal(bind,acquired,case!='digest')
                    with self.assertRaises(QualityError):rank_quality(bind,acquired)
