"""Public deterministic F/A/B fixtures; no model calls or model benefit claims."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from quality_fixtures import scoring_fixture

PROJECT=Path(__file__).resolve().parents[1]
LIMITS={'model_calls':0,'input_tokens':0,'output_tokens':0,'logical_tools':200,
        'physical_tools':30,'candidates':4,'elapsed_ms':1000,'cost_microusd':0,'retries':2}


def start(binding,acquired,mode='full',limits=None,available=None):
    from recommendation_actions import advance_action
    slots={p:{slot:[k for k,r in pack['originals'].items() if json.loads(r).get('kind')==slot.split('.')[1]]
              for slot in ('R1.inspection_sample','R1.inspection_report','R5.retail_status','stock.transport_dispatch','stock.transport_receipt')}
           for p,pack in (available or acquired)['candidates'].items()}
    return advance_action(None,{'kind':'init','fixture':'public_deterministic_adapter',
        'binding':binding,'acquired':acquired,'mode':mode,'limits':limits or LIMITS,
        'slots':slots,'final_reserve':{'logical_tools':1},'deadline_ms':1000,'at_ms':0})


def step(state,kind,role='推荐管理',**values):
    from recommendation_actions import advance_action
    return advance_action(state,{'kind':kind,'role':role,'task_id':state['binding']['task_id'],
        'snapshot_id':state['binding']['snapshot_id'],'at_ms':state['at_ms']+1,**values})


def wrong_draft(state):
    parent=state['binding']['C'][0]
    pack=state['acquired']['candidates'][parent]
    report=next(k for k,r in pack['originals'].items() if json.loads(r).get('kind')=='inspection_report')
    return {'draft_id':'PUBLIC-D0','parent_draft_id':None,'items':[
        {'parent_asin':parent,'stock_value':25,'stock_citation':report,'reason':'公开库存原文引用'}]}


class ActionTests(unittest.TestCase):
    def test_state_tampering_pending_work_and_cross_task_events_cannot_bypass_contract(self):
        from recommendation_actions import ActionError
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            binding,acquired=scoring_fixture(Path(temp));state=start(binding,acquired)
            for key,value in (('cursor',3),('mode','fixed'),('G',['DEMO-B'])):
                changed=copy.deepcopy(state);changed[key]=value
                with self.subTest(key=key),self.assertRaises(ActionError):step(changed,'submit_draft',draft=wrong_draft(state))
            with self.assertRaises(ActionError):step(state,'submit_draft',task_id='OTHER',draft=wrong_draft(state))
            with self.assertRaises(ActionError):step(state,'submit_draft',role='假角色',draft=wrong_draft(state))
            partial=copy.deepcopy(acquired);parent=binding['C'][0]
            key=next(k for k,r in partial['candidates'][parent]['originals'].items() if json.loads(r).get('kind')=='retail_status')
            partial['candidates'][parent]['originals'].pop(key)
            pending=step(start(binding,partial,available=acquired),'acquire','生命周期追溯',parent_asin=parent,slot='R5.retail_status',action_id='PENDING')
            with self.assertRaises(ActionError):step(pending,'submit_draft',draft=wrong_draft(state))
            self.assertEqual(state['drafts'],[])

    def test_candidate_cursor_follows_fixed_b_queue_and_cannot_skip_unfinished_candidate(self):
        from recommendation_actions import ActionError
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            binding,acquired=scoring_fixture(Path(temp));state=start(binding,acquired)
            with self.assertRaises(ActionError):step(state,'assess_current','推荐依据核验',parent_asin='DEMO-B')
            state=step(state,'assess_current','推荐依据核验',parent_asin='DEMO-HI')
            self.assertEqual((state['cursor'],state['processed'],state['G']),(1,['DEMO-HI'],['DEMO-HI']))
            with self.assertRaises(ActionError):step(state,'assess_current','推荐依据核验',parent_asin='DEMO-LO')
            state=step(state,'assess_current','推荐依据核验',parent_asin='DEMO-A')
            self.assertEqual(state['cursor'],2)
            draft=wrong_draft(start(binding,acquired))
            state=step(state,'submit_draft',draft=draft)
            state=step(state,'verify_draft','推荐依据核验')
            self.assertEqual(state['cursor'],2)

    def test_common_gate_no_feedback_has_no_repair_bypass_and_empty_is_not_success(self):
        import hashlib
        from recommendation_actions import ActionError
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            binding,acquired=scoring_fixture(Path(temp))
            state=start(binding,acquired,'no_feedback')
            state=step(state,'submit_draft',draft=wrong_draft(state))
            state=step(state,'verify_draft','推荐依据核验')
            self.assertEqual(state['visible_issues'],[])
            self.assertEqual(state['issues'][0]['code'],'wrong_attribute_citation')
            with self.assertRaises(ActionError):step(state,'revise_and_resubmit',issue_id=state['issues'][0]['issue_id'])
            state=step(state,'finalize')
            self.assertEqual((state['terminal'],state['delivered']),('blocked_evidence',[]))
            self.assertEqual(len(state['drafts']),1)
            for empty_pool in (False,True):
                b,a=copy.deepcopy((binding,acquired))
                if empty_pool:
                    b.update(C=[],base_scores=[])
                    b['C_sha256']=b['base_score_sha256']=hashlib.sha256(b'[]').hexdigest()
                    a['candidates']={}
                state=start(b,a)
                state=step(state,'submit_draft',draft={'draft_id':'EMPTY','parent_draft_id':None,'items':[]})
                state=step(state,'verify_draft','推荐依据核验')
                state=step(state,'finalize')
                self.assertEqual(state['terminal'],'valid_empty' if empty_pool else 'blocked_evidence')

    def test_failures_retries_deadlines_and_final_reserve_share_one_root_budget(self):
        from recommendation_actions import ActionError
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            binding,available=scoring_fixture(Path(temp));partial=copy.deepcopy(available)
            parent=binding['C'][0]
            retail=next(k for k,r in partial['candidates'][parent]['originals'].items() if json.loads(r).get('kind')=='retail_status')
            partial['candidates'][parent]['originals'].pop(retail)
            state=start(binding,partial,limits={**LIMITS,'logical_tools':125},available=available)
            state=step(state,'acquire','生命周期追溯',parent_asin=parent,slot='R5.retail_status',action_id='FAIL')
            state=step(state,'settle','生命周期追溯',action_id='FAIL',success=False,originals={})
            self.assertEqual(state['budget']['used']['logical_tools'],123)
            state=step(state,'acquire','生命周期追溯',parent_asin=parent,slot='R5.retail_status',action_id='RETRY',retry_of='FAIL')
            state=step(state,'settle','生命周期追溯',action_id='RETRY',success=True,
                originals={retail:available['candidates'][parent]['originals'][retail]})
            self.assertEqual(state['budget']['used']['logical_tools'],124)
            self.assertEqual(state['budget']['used']['retries'],1)
            before=copy.deepcopy(state['acquired'])
            stopped=step(state,'submit_draft',draft=wrong_draft(state))
            self.assertEqual(stopped['terminal'],'incomplete_budget')
            self.assertEqual(stopped['acquired'],before)
            self.assertEqual(stopped['budget']['remaining']['logical_tools'],1)
            checked=step(stopped,'finalize')
            self.assertEqual(checked['terminal'],'incomplete_budget')
            self.assertIn('release_check',checked)
            self.assertEqual(checked['budget']['remaining']['logical_tools'],0)
            late=step(start(binding,available),'submit_draft',draft=wrong_draft(start(binding,available)),at_ms=1001)
            self.assertEqual(late['terminal'],'incomplete_deadline')
            self.assertEqual(late['drafts'],[])
            self.assertEqual(late['at_ms'],1001)
            self.assertEqual(late['budget']['used']['elapsed_ms'],1001)
            self.assertEqual(late['budget']['overrun']['elapsed_ms'],1)
            self.assertEqual(step(late,'finalize')['terminal'],'incomplete_deadline')

    def test_routing_executes_different_real_slots_under_same_single_read_budget(self):
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            binding,available=scoring_fixture(Path(temp))
            partial=copy.deepcopy(available);parent=binding['C'][0]
            for key,raw in list(partial['candidates'][parent]['originals'].items()):
                if json.loads(raw).get('kind') in ('inspection_sample','retail_status'):
                    partial['candidates'][parent]['originals'].pop(key)
            limits={**LIMITS,'logical_tools':123}
            results={}
            for mode in ('full','no_feedback','fixed'):
                state=start(binding,partial,mode,limits,available)
                initial_used=copy.deepcopy(state['budget']['used'])
                state=step(state,'acquire','生命周期追溯',parent_asin=parent,slot='R5.retail_status',action_id='PUBLIC-A1')
                pending=state['pending']
                expected='R1.inspection_sample' if mode=='fixed' else 'R5.retail_status'
                self.assertEqual(pending['executed_slot'],expected)
                self.assertEqual(state['budget']['reserved']['logical_tools'],1)
                self.assertEqual(state['budget']['used']['logical_tools'],initial_used['logical_tools'])
                originals={k:available['candidates'][parent]['originals'][k] for k in pending['target_ids']}
                state=step(state,'settle','生命周期追溯',action_id='PUBLIC-A1',success=True,originals=originals)
                self.assertEqual(state['budget']['used']['logical_tools'],initial_used['logical_tools']+1)
                self.assertEqual(state['budget']['reserved']['logical_tools'],0)
                self.assertEqual(state['receipts'][-1]['executed_slot'],expected)
                self.assertTrue(all(k in state['acquired']['candidates'][parent]['originals'] for k in originals))
                results[mode]=state
            self.assertEqual(results['full']['acquired'],results['no_feedback']['acquired'])
            self.assertNotEqual(results['full']['acquired'],results['fixed']['acquired'])

    def test_feedback_preserves_drafts_and_requires_actual_issue_bound_citation_revision(self):
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            binding,acquired=scoring_fixture(Path(temp))
            for mode in ('full','fixed'):
                with self.subTest(mode=mode):
                    state=start(binding,acquired,mode)
                    initial=wrong_draft(state)
                    state=step(state,'submit_draft',draft=initial)
                    state=step(state,'verify_draft','推荐依据核验')
                    self.assertEqual(state['visible_issues'][0]['code'],'wrong_attribute_citation')
                    issue=state['visible_issues'][0]
                    correct=next(k for k,r in acquired['candidates'][binding['C'][0]]['originals'].items() if json.loads(r).get('kind')=='retail_status')
                    state=step(state,'revise_and_resubmit',issue_id=issue['issue_id'],draft_id='PUBLIC-D1',
                               pointer='/items/0/stock_citation',value=correct)
                    self.assertEqual(state['drafts'][0]['content'],initial)
                    self.assertEqual(state['drafts'][1]['content']['items'][0]['stock_citation'],correct)
                    self.assertEqual(state['revisions'][0]['old'],initial['items'][0]['stock_citation'])
                    self.assertEqual(state['revisions'][0]['issue_id'],issue['issue_id'])
                    state=step(state,'verify_draft','推荐依据核验')
                    self.assertEqual(state['visible_issues'],[])
                    state=step(state,'finalize')
                    self.assertEqual((state['terminal'],state['delivered']),('released',[binding['C'][0]]))
                    self.assertGreater(state['budget']['used']['logical_tools'],0)

    def test_initial_state_binds_root_and_never_invents_six_role_messages(self):
        from recommendation_actions import advance_action, ActionError
        with tempfile.TemporaryDirectory(dir=PROJECT/'.tmp') as temp:
            binding,acquired=scoring_fixture(Path(temp))
            state=start(binding,acquired)
            self.assertEqual(state['version'],'collaboration-action-contract-0.1.0')
            self.assertEqual(state['fixture'],'public_deterministic_adapter')
            self.assertEqual(state['binding'],binding)
            self.assertEqual((state['cursor'],state['drafts'],state['terminal']),(0,[],None))
            self.assertEqual(state['budget']['used']['logical_tools'],123)
            self.assertEqual(state['budget']['used']['physical_tools'],7)
            self.assertEqual(state['budget']['used']['model_calls'],0)
            self.assertEqual(state['receipts'][0]['operation'],'fixture_bootstrap')
            with self.assertRaises(ActionError):start(binding,acquired,'six_model_runner')
            bad=copy.deepcopy(acquired);bad['actions_bytes']=b'{}\n'
            with self.assertRaises(ActionError):start(binding,bad)
