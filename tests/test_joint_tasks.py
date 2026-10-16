"""Ticket13 public CLI seams. Expected outcomes are independent public literals."""
import json
import hashlib
import hmac
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from joint_fixtures import JointFixture, wire

ROOT = Path(__file__).resolve().parents[1]


class JointTasksTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'.tmp')
        self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name)

    def prepare(self, fixture, output='output', probe=None):
        if probe is None:
            observations=[]
            for i,task in enumerate(fixture.tasks):
                root=task['task_id']
                for view in fixture.views:
                    handle=hmac.new(b'k'*32,b'Thesis:joint-session-0.1.0\0'+wire([
                        root,view['material_version'],view['snapshot_id'],view['request_profile_id']]),hashlib.sha256).hexdigest()
                    observations.append({'session_task_id':handle,'operation':'model_request','arguments':{}})
                challenges=[('candidate_page',{'order':'parent','cursor':None}),
                    ('read_resource',{'path':fixture.cfg['inputs']['preference_evaluation']['path']}),
                    ('read_resource',{'path':'data/private-nonexistent-target.jsonl'}),
                    ('invoke_tool',{'name':'private_evaluator','role':'evaluator'}),
                    ('model_request',{'root_task_id':fixture.tasks[(i+1)%len(fixture.tasks)]['task_id']}),
                    ('candidate_page',{'order':'parent','cursor':'forged-cross-session-cursor'})]
                observations += [{'session_task_id':root,'operation':op,'arguments':args} for op,args in challenges]
            probe=ROOT/fixture.rows('full-probe.jsonl',observations)['path']
        command=[sys.executable,str(ROOT/'prepare_data.py'),'--stage','joint_tasks',
                 '--joint-config',str(fixture.root/'config.json'),'--output-root',str(self.work/output)]
        if probe:command+=['--access-probe',str(probe)]
        return subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')

    def verify(self, output='output', audit='audit'):
        return subprocess.run([sys.executable,str(ROOT/'.scratch/data-preparation/diagnostics/verify_joint13.py'),
            '--record',str(self.work/output/'records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0.json'),
            '--audit-root',str(self.work/audit)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')

    def test_missing_joint_inputs_return_stable_json(self):
        result = subprocess.run([sys.executable, str(ROOT/'prepare_data.py'), '--stage', 'joint_tasks'],
                                cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid_arguments')

    def test_one_shared_root_package_preserves_business_objects(self):
        fixture=JointFixture(self.work)
        result=self.prepare(fixture)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        record=json.loads(result.stdout)
        self.assertEqual(record['status'],'joint_tasks_prepared')
        self.assertEqual(record['counts']['roots'],4)
        self.assertEqual(record['counts']['parents'],3)
        self.assertEqual(record['counts']['business_batches'],3)

    def test_base_scores_use_full_unseen_candidates_and_hand_worked_text(self):
        fixture=JointFixture(self.work)
        result=self.prepare(fixture)
        self.assertEqual(result.returncode,0,result.stdout)
        record=json.loads(result.stdout)
        score_path=self.work/'output'/record['components']['base-scores.jsonl']['path']
        scores=[json.loads(line) for line in score_path.read_bytes().splitlines()]
        self.assertEqual(len(scores),4)
        self.assertEqual(scores[0]['C'],['DEMO-A','DEMO-B'])
        self.assertEqual(scores[0]['b'],[1.0,0.0])
        self.assertEqual(scores[0]['score_version'],'char3-tfidf-history-1.0.0')

    def test_future_history_cannot_enter_joint_input(self):
        fixture=JointFixture(self.work)
        fixture.tasks[0]['history'][0]['timestamp_ms']=fixture.tasks[0]['history_cutoff_exclusive_ms']
        fixture.refresh()
        result=self.prepare(fixture)
        self.assertEqual(result.returncode,2,result.stdout)
        self.assertEqual(json.loads(result.stdout)['error']['code'],'binding_mismatch')

    def test_all_views_share_root_history_candidates_and_base_scores(self):
        fixture=JointFixture(self.work)
        result=self.prepare(fixture)
        record=json.loads(result.stdout)
        bindings=self.work/'output'/record['components']['view-bindings.jsonl']['path']
        rows=[json.loads(line) for line in bindings.read_bytes().splitlines()]
        self.assertEqual(len(rows),40)
        first=[r for r in rows if r['root_task_id']==fixture.tasks[0]['task_id']]
        self.assertEqual(len({r['root_input_sha256'] for r in first}),1)
        self.assertEqual(len({r['base_scores_sha256'] for r in first}),1)
        self.assertEqual([r['planned_methods'] for r in first[:8]],[['R','S','M']]*8)
        self.assertTrue(all(r['execution_budget'] is None and not r['execution_authorized'] for r in rows))

    def test_actual_model_request_and_candidate_page_only_expose_allowlisted_data(self):
        fixture=JointFixture(self.work,extra_products=33)
        probe=fixture.rows('probe.jsonl',[
            {'session_task_id':fixture.tasks[0]['task_id'],'operation':'model_request','arguments':{}},
            {'session_task_id':fixture.tasks[0]['task_id'],'operation':'candidate_page','arguments':{'order':'parent','cursor':None}}])
        result=self.prepare(fixture,probe=ROOT/probe['path'])
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        record=json.loads(result.stdout)
        path=self.work/'output'/record['components']['private/access-probe.jsonl']['path']
        responses=[json.loads(line)['response'] for line in path.read_bytes().splitlines()]
        request=responses[0]['request']
        self.assertEqual(request['tools'],[])
        self.assertNotIn('PRIVATE_TARGET_CANARY',json.dumps(request))
        page=responses[1]
        self.assertEqual(len(page['candidates']),32)
        self.assertEqual(page['total_candidates'],35)
        self.assertIsNotNone(page['next_cursor'])

    def test_config_cannot_authorize_execution_or_change_frozen_budget(self):
        fixture=JointFixture(self.work)
        fixture.cfg['budget']['execution_authorized']=True
        (self.work/'config.json').write_bytes(wire(fixture.cfg)+b'\n')
        result=self.prepare(fixture)
        self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['error']['code'],'invalid_config')

    def test_identical_reuse_keeps_original_record_and_rejects_changed_output(self):
        fixture=JointFixture(self.work)
        first=self.prepare(fixture)
        self.assertEqual(first.returncode,0,first.stdout)
        record_path=self.work/'output/records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0.json'
        before=record_path.read_bytes(),record_path.stat().st_mtime_ns
        second=self.prepare(fixture)
        self.assertEqual(second.returncode,0,second.stdout)
        self.assertEqual((record_path.read_bytes(),record_path.stat().st_mtime_ns),before)
        record=json.loads(first.stdout)
        target=self.work/'output'/record['components']['base-scores.jsonl']['path']
        target.write_bytes(b'changed\n')
        last=self.prepare(fixture)
        self.assertEqual(last.returncode,2)
        self.assertEqual(json.loads(last.stdout)['error']['code'],'output_conflict')
        self.assertEqual(target.read_bytes(),b'changed\n')

    def test_independent_preference_reference_stays_at_parent_level(self):
        fixture=JointFixture(self.work)
        self.assertEqual(self.prepare(fixture).returncode,0)
        result=self.verify()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        reference=[json.loads(line) for line in (self.work/'audit/preference-reference.jsonl').read_bytes().splitlines()]
        self.assertEqual(len(reference),4)
        self.assertEqual({r['target_parent'] for r in reference},{'DEMO-A','DEMO-B'})
        self.assertTrue(all('sim_batch_id' not in r and 'target_review' not in r for r in reference))

    def test_q_cohort_is_new_and_does_not_copy_old_p0_n8(self):
        fixture=JointFixture(self.work)
        self.assertEqual(self.prepare(fixture).returncode,0)
        result=self.verify()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        check=json.loads((self.work/'audit/check.json').read_bytes())
        self.assertEqual(check['nQ'],3)
        self.assertEqual(check['n8_from_P0'],2)
        self.assertEqual(check['sample_sufficiency'],'not_determined')
        coverage=json.loads((self.work/'audit/coverage.json').read_bytes())
        self.assertAlmostEqual(coverage['test']['UQ']['target_concentration']['hhi'],5/9)
        self.assertEqual(coverage['test']['UQ']['history_depth_groups'],{'1':3,'2':0,'3+':0})

    def test_resealed_q_answers_do_not_replace_accepted_independent_source(self):
        fixture=JointFixture(self.work)
        fixture.q_rows[0]['source_citations']['inspection_report']['sha256']='b'*64
        qref=fixture.input('quality_reference',fixture.rows('reference/quality.jsonl',fixture.q_rows))
        fixture.input('quality_reference_summary',fixture.write('reference/quality-summary.json',{
            'status':'passed','version':'quality-reference-0.1.0','references':len(fixture.q_rows),'reference_sha256':qref['sha256']}))
        (self.work/'config.json').write_bytes(wire(fixture.cfg)+b'\n')
        self.assertEqual(self.prepare(fixture).returncode,0)
        result=self.verify()
        self.assertEqual(result.returncode,2,result.stdout)
        self.assertEqual(json.loads(result.stdout)['error']['code'],'reference_source_mismatch')

    def test_complete_raw_comments_remain_in_trusted_bundle_with_count_reconciliation(self):
        fixture=JointFixture(self.work)
        result=self.prepare(fixture)
        record=json.loads(result.stdout)
        self.assertEqual(record['counts']['raw_comment_rows'],2)
        self.assertEqual(record['counts']['clean_comment_rows'],1)
        manifest_path=self.work/'output'/record['components']['package-manifest.json']['path']
        manifest=json.loads(manifest_path.read_bytes())
        self.assertEqual(manifest['source_components']['raw_reviews']['records'],2)
        self.assertNotIn('raw_reviews',json.loads((self.work/'output'/record['components']['model/manifest.json']['path']).read_bytes())['components'])

    def test_independent_audit_rejects_resealed_model_candidate_truncation(self):
        fixture=JointFixture(self.work)
        result=self.prepare(fixture)
        record=json.loads(result.stdout)
        output=self.work/'output'
        target=output/record['components']['model/candidates.jsonl']['path']
        values=[json.loads(line) for line in target.read_bytes().splitlines()]
        for key in ('C','b','batches','background_statistics'):
            values[0][key]=values[0][key][:1]
        target.write_bytes(b''.join(wire(r)+b'\n' for r in values))
        def update(ref,file):
            raw=file.read_bytes()
            ref.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        update(record['components']['model/candidates.jsonl'],target)
        manifest_path=output/record['components']['model/manifest.json']['path']
        manifest=json.loads(manifest_path.read_bytes())
        update(manifest['components']['candidates.jsonl'],target)
        manifest_path.write_bytes(wire(manifest)+b'\n')
        update(record['components']['model/manifest.json'],manifest_path)
        (output/'records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0.json').write_bytes(wire(record)+b'\n')
        checked=self.verify()
        self.assertEqual(checked.returncode,2,checked.stdout)
        self.assertEqual(json.loads(checked.stdout)['error']['code'],'joint_projection_mismatch')

    def test_new_q_coverage_preserves_legacy_exposure_and_unknown_status(self):
        fixture=JointFixture(self.work)
        self.assertEqual(self.prepare(fixture).returncode,0)
        result=self.verify()
        self.assertEqual(result.returncode,0,result.stdout)
        coverage=json.loads((self.work/'audit/coverage.json').read_bytes())
        self.assertEqual(coverage['test']['UQ']['legacy_exposure']['legacy_corpus_accounts'],1)
        self.assertEqual(coverage['test']['UQ']['legacy_exposure']['unknown_human_result_accounts'],3)

    def test_q_reference_citation_must_resolve_to_same_actual_object(self):
        fixture=JointFixture(self.work)
        fixture.q_rows[0]['source_citations']['inspection_report']['sha256']='b'*64
        qref=fixture.input('quality_reference',fixture.rows('reference/quality.jsonl',fixture.q_rows))
        summary=fixture.input('quality_reference_summary',fixture.write('reference/quality-summary.json',{
            'status':'passed','version':'quality-reference-0.1.0','references':len(fixture.q_rows),'reference_sha256':qref['sha256']}))
        fixture.input('quality_acceptance',fixture.write('records/quality-acceptance.json',{
            'status':'accepted','generation_record':fixture.cfg['inputs']['quality'],
            'validation':{'independent_full_reference':{'status':'passed','evidence':summary}}}))
        (self.work/'config.json').write_bytes(wire(fixture.cfg)+b'\n')
        self.assertEqual(self.prepare(fixture).returncode,0)
        result=self.verify()
        self.assertEqual(result.returncode,2,result.stdout)
        self.assertEqual(json.loads(result.stdout)['error']['code'],'reference_citation_mismatch')

    def test_output_root_cannot_write_inside_readonly_input_directory(self):
        fixture=JointFixture(self.work)
        result=self.prepare(fixture,output='inputs')
        self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['error']['code'],'invalid_path')

    def test_prepared_record_binds_actual_runtime_and_source_commit(self):
        fixture=JointFixture(self.work)
        result=self.prepare(fixture)
        record=json.loads(result.stdout)
        self.assertEqual(record['runtime']['python_version'],'3.13.16')
        self.assertEqual(Path(record['runtime']['conda_prefix']).resolve(),ROOT/'.conda/envs/Thesis')
        self.assertEqual(len(record['code_commit']),40)
        self.assertIsInstance(record['worktree_dirty'],bool)

    def test_malformed_page_order_is_denied_without_host_error(self):
        fixture=JointFixture(self.work)
        probe=fixture.rows('probe.jsonl',[{'session_task_id':fixture.tasks[0]['task_id'],
            'operation':'candidate_page','arguments':{'order':['parent'],'cursor':None}}])
        result=self.prepare(fixture,probe=ROOT/probe['path'])
        self.assertEqual(result.returncode,0,result.stdout)
        record=json.loads(result.stdout)
        file=self.work/'output'/record['components']['private/access-probe.jsonl']['path']
        self.assertEqual(json.loads(file.read_bytes())['response'],{'status':'access_denied'})

    def test_independent_audit_rejects_private_field_inside_resealed_request(self):
        fixture=JointFixture(self.work)
        probe=fixture.rows('probe.jsonl',[{'session_task_id':fixture.tasks[0]['task_id'],
            'operation':'model_request','arguments':{}}])
        result=self.prepare(fixture,probe=ROOT/probe['path'])
        record=json.loads(result.stdout)
        output=self.work/'output'
        file=output/record['components']['private/access-probe.jsonl']['path']
        value=json.loads(file.read_bytes())
        payload=json.loads(value['response']['request']['messages'][0]['content'])
        payload['request']['private_target']='PRIVATE_TARGET_CANARY'
        payload['input_fingerprint']=hashlib.sha256(wire({k:v for k,v in payload.items() if k!='input_fingerprint'})).hexdigest()
        value['response']['request']['messages'][0]['content']=wire(payload).decode()
        raw=wire(value)+b'\n'
        file.write_bytes(raw)
        record['components']['private/access-probe.jsonl'].update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        (output/'records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0.json').write_bytes(wire(record)+b'\n')
        result=self.verify()
        self.assertEqual(result.returncode,2,result.stdout)
        self.assertEqual(json.loads(result.stdout)['error']['code'],'unsafe_model_request')

    def test_private_target_mutation_leaves_scores_projection_and_actual_request_unchanged(self):
        fixture=JointFixture(self.work)
        probe=fixture.rows('probe.jsonl',[{'session_task_id':fixture.tasks[0]['task_id'],'operation':'model_request','arguments':{}}])
        first=self.prepare(fixture,probe=ROOT/probe['path'])
        self.assertEqual(first.returncode,0,first.stdout)
        before=json.loads(first.stdout)
        target=fixture.evaluations[0]
        target['target_parent_asin']='DEMO-B' if target['target_parent_asin']=='DEMO-A' else 'DEMO-A'
        target['target_rating']=4
        target['target_review']={'parent_asin':target['target_parent_asin'],'rating':4,'text':'PRIVATE_DIFFERENT_TARGET'}
        target['reference_answer']['positive_parent_asins']=[target['target_parent_asin']]
        fixture.refresh()
        second=self.prepare(fixture,output='changed-private-target',probe=ROOT/probe['path'])
        self.assertEqual(second.returncode,0,second.stdout)
        after=json.loads(second.stdout)
        names=[k for k in before['components'] if k.startswith('model/') or k in ('base-scores.jsonl','private/access-probe.jsonl')]
        self.assertEqual({k:before['components'][k]['sha256'] for k in names},
                         {k:after['components'][k]['sha256'] for k in names})
        self.assertNotEqual(before['config']['sha256'],after['config']['sha256'])

    def test_resource_and_cross_session_challenges_have_identical_denial(self):
        fixture=JointFixture(self.work)
        current,other=fixture.tasks[0]['task_id'],fixture.tasks[1]['task_id']
        probes=[{'session_task_id':current,'operation':'read_resource','arguments':{'path':value}}
                for value in (fixture.cfg['inputs']['preference_evaluation']['path'],'private/nonexistent.jsonl','old-index','C:/outside')]
        probes += [{'session_task_id':current,'operation':'invoke_tool','arguments':{'name':'evaluate','role':'evaluator'}},
                   {'session_task_id':current,'operation':'model_request','arguments':{'root_task_id':other}},
                   {'session_task_id':current,'operation':'candidate_page','arguments':{'order':'parent','cursor':'forged'}}]
        probe=fixture.rows('probe.jsonl',probes)
        result=self.prepare(fixture,probe=ROOT/probe['path'])
        self.assertEqual(result.returncode,0,result.stdout)
        record=json.loads(result.stdout)
        file=self.work/'output'/record['components']['private/access-probe.jsonl']['path']
        self.assertEqual([json.loads(r)['response'] for r in file.read_bytes().splitlines()],[{'status':'access_denied'}]*7)

    def test_candidate_paging_uses_returned_cursor_to_reach_entire_catalog(self):
        fixture=JointFixture(self.work,extra_products=33)
        probe=fixture.rows('probe.jsonl',[{'session_task_id':fixture.tasks[0]['task_id'],'operation':'candidate_page',
            'arguments':{'order':'parent','cursor':None}}])
        first=json.loads(self.prepare(fixture,probe=ROOT/probe['path']).stdout)
        file=self.work/'output'/first['components']['private/access-probe.jsonl']['path']
        page=json.loads(file.read_bytes())['response']
        next_probe=fixture.rows('next-probe.jsonl',[{'session_task_id':fixture.tasks[0]['task_id'],'operation':'candidate_page',
            'arguments':{'order':'parent','cursor':page['next_cursor']}}])
        second=self.prepare(fixture,output='page-two',probe=ROOT/next_probe['path'])
        self.assertEqual(second.returncode,0,second.stdout)
        record=json.loads(second.stdout)
        file=self.work/'page-two'/record['components']['private/access-probe.jsonl']['path']
        final=json.loads(file.read_bytes())['response']
        self.assertEqual(len(final['candidates']),3)
        self.assertIsNone(final['next_cursor'])
        self.assertEqual([r['parent_asin'] for r in page['candidates']+final['candidates']],fixture.tasks[0]['candidate_parent_asins'])

    def test_constant_content_and_single_candidate_have_half_score(self):
        fixture=JointFixture(self.work)
        for p in fixture.products:p.update(title='AAA',crop='rice')
        fixture.refresh()
        first=json.loads(self.prepare(fixture).stdout)
        scores=self.work/'output'/first['components']['base-scores.jsonl']['path']
        self.assertTrue(all(json.loads(r)['b']==[.5,.5] for r in scores.read_bytes().splitlines()))
        for task in fixture.tasks:
            task['seen_parent_asins']=['DEMO-B','DEMO-H'];task['candidate_parent_asins']=['DEMO-A']
            task['background_statistics']=task['background_statistics'][:1]
        fixture.refresh()
        second=self.prepare(fixture,output='single')
        self.assertEqual(second.returncode,0,second.stdout)
        ref=json.loads(second.stdout)['components']['base-scores.jsonl']['path']
        self.assertTrue(all(json.loads(r)['b']==[.5] for r in (self.work/'single'/ref).read_bytes().splitlines()))

    def test_missing_q_reference_key_is_failure_and_never_semantic_na(self):
        fixture=JointFixture(self.work)
        fixture.q_rows.pop()
        fixture.refresh()
        self.assertEqual(self.prepare(fixture).returncode,0)
        result=self.verify()
        self.assertEqual(result.returncode,2,result.stdout)
        self.assertEqual(json.loads(result.stdout)['error']['code'],'incomplete_reference_keys')
        self.assertFalse((self.work/'audit/check.json').exists())

    def test_new_parser_argument_keeps_existing_stage_missing_input_dispatch(self):
        for stage in ('sim_normal','evidence_scenarios','quality_fusion','preference_tasks'):
            with self.subTest(stage=stage):
                result=subprocess.run([sys.executable,str(ROOT/'prepare_data.py'),'--stage',stage,
                    '--output-root',str(self.work/'legacy')],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
                self.assertEqual(result.returncode,2)
                self.assertEqual(json.loads(result.stdout)['stage'],stage)

    def test_independent_audit_rejects_resealed_false_raw_comment_count(self):
        fixture=JointFixture(self.work)
        record=json.loads(self.prepare(fixture).stdout)
        output=self.work/'output'
        file=output/record['components']['package-manifest.json']['path']
        manifest=json.loads(file.read_bytes())
        manifest['source_components']['raw_reviews']['records']=99
        raw=wire(manifest)+b'\n'
        file.write_bytes(raw)
        record['components']['package-manifest.json'].update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        (output/'records/joint-tasks/grain-A-1.1.15-joint-task-package-0.1.0.json').write_bytes(wire(record)+b'\n')
        result=self.verify()
        self.assertEqual(result.returncode,2,result.stdout)
        self.assertEqual(json.loads(result.stdout)['error']['code'],'source_graph_mismatch')

    def test_staging_directory_junction_is_rejected_before_any_publication(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'data/joint-audit/joint-task-package-0.1.0') as external:
            self.work=Path(external)
            fixture=JointFixture(self.work)
            temporary=ROOT/'.tmp'
            backup=ROOT/('.tmp-ticket13-'+self.work.name)
            self.assertEqual(temporary.parent,ROOT)
            self.assertEqual(backup.parent,ROOT)
            temporary.rename(backup)
            try:
                subprocess.run(['cmd','/c','mklink','/J',str(temporary),str(backup)],
                               capture_output=True,check=True)
                result=self.prepare(fixture)
            finally:
                if temporary.is_junction():temporary.rmdir()
                backup.rename(temporary)
            self.assertEqual(result.returncode,2,result.stdout)
            self.assertEqual(json.loads(result.stdout)['error']['code'],'invalid_path')
            self.assertFalse((self.work/'output/records').exists())

    def test_q_version_outside_accepted_normal_v1_scope_is_rejected(self):
        fixture=JointFixture(self.work)
        view=fixture.views[8]
        citation=fixture.q_rows[0]['source_citations']['inspection_report']
        folder=(ROOT/view['snapshot']['path']).parent
        originals=[json.loads(line) for line in (folder/'materials.jsonl').read_bytes().splitlines()]
        original=next(r for r in originals if r['evidence_id']==citation['evidence_id'])
        original['version']=2
        citation['sha256']=hashlib.sha256(wire(original)).hexdigest()
        registrations=[json.loads(line) for line in (folder/'registrations.jsonl').read_bytes().splitlines()]
        next(r for r in registrations if r['registration_id']==citation['registration_id'])['content_sha256']=citation['sha256']
        snapshot=json.loads((folder/'snapshot.json').read_bytes())
        for name,values in (('materials.jsonl',originals),('registrations.jsonl',registrations)):
            binding=fixture.rows('facts/Q1/'+name,values)
            snapshot['components'][name]={k:v for k,v in binding.items() if k!='path'}
        view['snapshot']=fixture.write('facts/Q1/snapshot.json',snapshot)
        fixture.refresh()
        self.assertEqual(self.prepare(fixture).returncode,0)
        result=self.verify()
        self.assertEqual(result.returncode,2,result.stdout)
        self.assertEqual(json.loads(result.stdout)['error']['code'],'reference_scope_mismatch')

    def test_independent_acceptance_requires_actual_full_root_probe_coverage(self):
        fixture=JointFixture(self.work)
        self.assertEqual(self.prepare(fixture,probe=False).returncode,0)
        result=self.verify()
        self.assertEqual(result.returncode,2,result.stdout)
        self.assertEqual(json.loads(result.stdout)['error']['code'],'incomplete_probe_coverage')
        self.assertFalse((self.work/'audit/check.json').exists())

    def test_duplicate_probe_counts_cannot_replace_distinct_view_coverage(self):
        fixture=JointFixture(self.work)
        self.assertEqual(self.prepare(fixture).returncode,0)
        values=[json.loads(line) for line in (self.work/'inputs/full-probe.jsonl').read_bytes().splitlines()]
        values[9]=values[0]
        probe=fixture.rows('missing-one-view-probe.jsonl',values)
        self.assertEqual(self.prepare(fixture,output='partial',probe=ROOT/probe['path']).returncode,0)
        result=self.verify(output='partial')
        self.assertEqual(result.returncode,2,result.stdout)
        self.assertEqual(json.loads(result.stdout)['error']['code'],'incomplete_probe_coverage')

    def test_accepted_scenario_snapshot_inherits_principal_from_bound_policy(self):
        fixture=JointFixture(self.work)
        for view in fixture.views[:8]:
            snapshot=json.loads((ROOT/view['snapshot']['path']).read_bytes())
            snapshot.pop('read_principal_id',None)
            view['snapshot']=fixture.write('facts/'+view['label']+'/snapshot.json',snapshot)
        fixture.refresh()
        result=self.prepare(fixture)
        self.assertEqual(result.returncode,0,result.stdout)
        self.assertEqual(self.verify().returncode,0)
