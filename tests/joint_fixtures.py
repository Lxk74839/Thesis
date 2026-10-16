"""Handwritten public upstream-shaped records; never production-generated answers."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'R1_AND_R5_SIM_Q1_ON_SALE'


def wire(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


class JointFixture:
    def __init__(self, root, extra_products=0):
        self.root = root
        self.cfg = json.loads((ROOT/'config/joint-task-package-0.1.0.json').read_bytes())
        self.cfg['inputs'] = {}
        self.products = [{'parent_asin': p, 'title': title, 'crop': crop}
                         for p, title, crop in [('DEMO-A','AAA','rice'), ('DEMO-B','BBB','corn'), ('DEMO-H','AAA','rice')]]
        self.products += [{'parent_asin':f'DEMO-Z{i:02}', 'title':'ZZZ', 'crop':'oats'} for i in range(extra_products)]
        self.products.sort(key=lambda p:p['parent_asin'].encode())
        self.batches = [{'parent_asin':p['parent_asin'], 'sim_batch_id':'SIM-'+p['parent_asin'], 'source':'SIM','version':1} for p in self.products]
        candidates = [p['parent_asin'] for p in self.products if p['parent_asin']!='DEMO-H']
        self.tasks = []
        self.evaluations = []
        for i, target in enumerate(('DEMO-A','DEMO-A','DEMO-B','DEMO-A')):
            task_id = hashlib.sha256(f'DEMO-ACCOUNT-{i}'.encode()).hexdigest()
            self.tasks.append({'schema_version':'preference-model-input-1.0.0', 'task_id':task_id,
                'catalog_version':'grain-A-1.1.15', 'text_policy_version':'finite-text-1.0.0',
                'metadata_time_basis':'collection_snapshot','history_cutoff_exclusive_ms':1577836800000,
                'request':{'source':'experiment_template','text':'public old request'},
                'history':[{'parent_asin':'DEMO-H','timestamp_ms':1577750400000,'rating':5,'text':'AAA'}],
                'seen_parent_asins':['DEMO-H'],'candidate_parent_asins':candidates,
                'background_statistics':[{'parent_asin':p,'interaction_count':0,'account_count':0,'positive_account_count':0} for p in candidates]})
            self.evaluations.append({'task_id':task_id,'source_user_id':f'DEMO-ACCOUNT-{i}',
                'split':'dev' if i==0 else 'test','target_parent_asin':target,'target_timestamp_ms':1577836800000,
                'target_rating':5,'target_review':{'parent_asin':target,'text':'PRIVATE_TARGET_CANARY','rating':5},
                'target_source_references':[{'source_line':i+1}],
                'reference_answer':{'positive_parent_asins':[target],'other_candidates':'unobserved_unlabeled'}})
        self.tasks.sort(key=lambda r:r['task_id'])
        self.evaluations.sort(key=lambda r:r['task_id'])
        self.views=[]
        self.scenario_rows=[]
        self.q_rows=[]
        for label in ('V00','V01','V03','V05','V06','V07','V09','V12','Q1','Q2'):
            files = {}
            kinds=('inspection_sample','inspection_report','retail_status','transport_dispatch','transport_receipt')
            originals=[]; events=[]; registrations=[]
            for product in self.products:
                p=product['parent_asin']
                for kind in kinds:
                    event_id='event-'+kind+'-'+p
                    evidence_id='evidence-'+kind+'-'+p
                    original={'source':'SIM','parent_asin':p,'sim_batch_id':'SIM-'+p,'event_id':event_id,
                        'evidence_id':evidence_id,'kind':kind,'version':1,'facts':{'conclusion':'pass'}}
                    originals.append(original)
                    events.append({'source':'SIM','event_id':event_id,'parent_asin':p,'sim_batch_id':'SIM-'+p,'version':1})
                    registrations.append({'source':'SIM','registration_id':'reg-'+kind+'-'+p,'target_id':evidence_id,
                        'parent_asin':p,'sim_batch_id':'SIM-'+p,'event_id':event_id,
                        'content_sha256':hashlib.sha256(wire(original)).hexdigest(),'version':1})
            for name, rows in [('batches.jsonl',self.batches), ('events.jsonl',events),
                               ('materials.jsonl',originals),('registrations.jsonl',registrations),('actions.jsonl',[])]:
                files[name] = self.rows('facts/'+label+'/'+name,rows)
            files['policy.json'] = self.write('facts/'+label+'/policy.json',{'read_principal_id':'SIM-VERIFIER'})
            snap = {'snapshot_id':'snapshot-'+label,'verify_at_ms':1791417600000,'read_principal_id':'SIM-VERIFIER',
                    'protocol_version':'quality-preference-protocol-0.1.0' if label.startswith('Q') else 'sim-evidence-protocol-1.0.0',
                    'components':{k:{x:v for x,v in ref.items() if x!='path'} for k,ref in files.items()}}
            if not label.startswith('Q'):del snap['read_principal_id']
            snapshot=self.write('facts/'+label+'/snapshot.json',snap)
            material='sim-quality-fusion-0.1.0' if label.startswith('Q') else 'sim-scenarios-1.0.0'
            self.views.append({'label':label,'arm':'quality' if label.startswith('Q') else 'necessary',
                'material_version':material,'view_id':'opaque-'+label,'snapshot':snapshot,
                'snapshot_id':snap['snapshot_id'],'request_profile_id':PROFILE})
            for product in self.products:
                parent=product['parent_asin']
                state='Supported'
                if parent=='DEMO-B':
                    state={'V01':'Pending','V03':'Pending','V05':'Refuted','V06':'Conflict','V07':'Pending','V09':'Refuted'}.get(label,'Supported')
                citations={k:{'evidence_id':'evidence-'+k+'-'+parent,'registration_id':'reg-'+k+'-'+parent,
                    'event_id':'event-'+k+'-'+parent,'sha256':hashlib.sha256(wire(next(
                        r for r in originals if r['evidence_id']=='evidence-'+k+'-'+parent))).hexdigest()} for k in kinds}
                if label.startswith('Q'):
                    self.q_rows.append({'snapshot_id':snap['snapshot_id'],'parent_asin':parent,'eligible':True,
                        'source_citations':citations,'x':25,'z':1,'C':{'numerator':1,'denominator':1},
                        'T':{'numerator':1,'denominator':5},'A':{'numerator':2,'denominator':2},'q':.6,'m':.25})
                else:
                    self.scenario_rows.append({'view_id':'opaque-'+label,'snapshot_id':snap['snapshot_id'],
                        'request_profile_id':PROFILE,'parent_asin':parent,'sim_batch_id':'SIM-'+parent,
                        'candidate_state':state,'eligible':state=='Supported','clauses':{'c1':{'state':state},'c2':{'state':'Supported'}}})
        self.cfg['views']=self.views
        self.input('identity_key',self.raw('id-key.bin',b'k'*32))
        self.refresh()

    def raw(self, name, content):
        path=self.root/'inputs'/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(content)
        return {'path':path.relative_to(ROOT).as_posix(),'bytes':len(content),'records':content.count(b'\n'),'sha256':hashlib.sha256(content).hexdigest()}

    def write(self, name, value):
        return self.raw(name,wire(value)+b'\n')

    def rows(self, name, values):
        return self.raw(name,b''.join(wire(row)+b'\n' for row in values))

    def input(self, name, binding):
        self.cfg['inputs'][name]=binding
        return binding

    def refresh(self):
        catalog=self.input('preference_catalog',self.rows('model/catalog.jsonl',self.products))
        tasks=self.input('preference_tasks',self.rows('model/tasks.jsonl',self.tasks))
        evaluation=self.input('preference_evaluation',self.rows('private/evaluation.jsonl',self.evaluations))
        self.input('preference_audit',self.rows('private/task-audit.jsonl',[]))
        self.input('preference_model_manifest',self.write('model/manifest.json',{'components':{'catalog.jsonl':catalog,'tasks.jsonl':tasks}}))
        pref={'components':{'catalog':catalog,'tasks':tasks,'evaluation':evaluation},'counts':{'accounts':len(self.tasks)},
              'rules_version':'preference-task-1.0.1'}
        prefref=self.input('preference',self.write('records/preference.json',pref))
        self.input('preference_acceptance',self.write('records/preference-acceptance.json',{
            'status':'accepted_ticket08_preference_trial_api_only','record_sha256':prefref['sha256'],
            'component_sha256':{k:v['sha256'] for k,v in pref['components'].items()}}))
        normal={'components':{'batches.jsonl':self.rows('normal/batches.jsonl',self.batches)}}
        for name in ('events.jsonl','policy.json'):
            normal['components'][name]=self.raw('normal/'+name,(self.root/'inputs/facts/Q2'/name).read_bytes())
        normalref=self.input('normal',self.write('records/normal.json',normal))
        self.input('normal_acceptance',self.write('records/normal-acceptance.json',{'status':'accepted','generation_record':normalref}))
        for role in ('scenarios','quality'):
            components={}
            for view in self.views:
                if (role=='quality') != (view['arm']=='quality'):continue
                folder=(ROOT/view['snapshot']['path']).parent
                for file in folder.iterdir():
                    raw=file.read_bytes();components[file.relative_to(self.root/'inputs').as_posix()]={
                        'path':file.relative_to(ROOT).as_posix(),'bytes':len(raw),'records':len(raw.splitlines()),'sha256':hashlib.sha256(raw).hexdigest()}
            requests=self.rows('facts/'+role+'/requests.jsonl',[{'profile_id':PROFILE,'source':'experiment_design',
                'design_text':'public controlled request','necessary_clauses':[{'clause_id':'c1'},{'clause_id':'c2'}]}])
            components['requests.jsonl']=requests
            rec={'components':components,'views':[v for v in self.views if (v['arm']=='quality')==(role=='quality')]}
            rec_ref=self.input(role,self.write('records/'+role+'.json',rec))
            self.input(role+'_acceptance',self.write('records/'+role+'-acceptance.json',{'status':'accepted','generation_record':rec_ref}))
        raw=self.input('raw_reviews',self.rows('reviews/raw.jsonl',[{'parent_asin':'DEMO-H','rating':1,'text':''}]*2))
        self.input('review_sources',self.rows('reviews/sources.jsonl',[{'source_line':1},{'source_line':2}]))
        self.input('clean_reviews',self.rows('reviews/clean.jsonl',[{'parent_asin':'DEMO-H'}]))
        self.input('clean_audit',self.rows('reviews/audit.jsonl',[{'source_line':1},{'source_line':2}]))
        self.input('clean_accounts',self.rows('reviews/accounts.jsonl',[]))
        self.input('catalog',self.write('records/catalog.json',{'catalog_version':'grain-A-1.1.15'}))
        self.input('selected',self.write('records/selected.json',{'extract_path':raw['path'],'extract_sha256':raw['sha256'],'scan':{'matched_rows':2}}))
        self.input('cleaning',self.write('records/cleaning.json',{'counts':{'clean_reviews':1},'source_extract_sha256':raw['sha256']}))
        for role in ('cleaning_acceptance','cleaning_erratum','split','split_acceptance'):
            self.input(role,self.write('records/'+role+'.json',{'status':'accepted'}))
        exposure=self.rows('private/exposure.jsonl',[{'user_id':e['source_user_id'],
            'legacy_corpus_member':e['target_parent_asin']=='DEMO-B','agent_account_result_view':'unknown',
            'human_account_result_view':'unknown'} for e in self.evaluations])
        self.input('split',self.write('records/split.json',{'status':'accepted',
            'exposure_path':exposure['path'],'exposure_sha256':exposure['sha256']}))
        sref=self.input('scenario_reference',self.rows('reference/scenario.jsonl',self.scenario_rows))
        qref=self.input('quality_reference',self.rows('reference/quality.jsonl',self.q_rows))
        self.input('quality_reference_summary',self.write('reference/quality-summary.json',{'status':'passed',
            'version':'quality-reference-0.1.0','references':len(self.q_rows),'reference_sha256':qref['sha256']}))
        self.p0=[]
        for e in self.evaluations:
            self.p0.append({'task_id':e['task_id'],'split':e['split'],'target_parent_asin':e['target_parent_asin'],
                'target_timestamp_ms':e['target_timestamp_ms'],'history_distinct_parent_count':1,
                'applicability':{'all_main_applicable':e['target_parent_asin']!='DEMO-B','by_view':{}}})
        p0ref=self.input('p0_applicability',self.rows('reference/p0-applicability.jsonl',self.p0))
        self.input('p0_aggregate',self.write('reference/p0.json',{'groups':{'dev':{'n_pool':1,'n_J_all_main_views':1},
            'test':{'n_pool':3,'n_J_all_main_views':2}},'reference_binding':{'path':sref['path'],'sha256':sref['sha256']},
            'private_audit_components':{'account-applicability.jsonl':{'sha256':p0ref['sha256']}}}))
        for role in ('scenarios','quality'):
            acceptance={'status':'accepted','generation_record':self.cfg['inputs'][role]}
            if role=='scenarios':
                acceptance['independent_reference']={'reference':sref}
            else:
                acceptance['validation']={'independent_full_reference':{'status':'passed',
                    'evidence':self.cfg['inputs']['quality_reference_summary']}}
            self.input(role+'_acceptance',self.write('records/'+role+'-acceptance.json',acceptance))
        path=self.root/'config.json'
        path.write_bytes(wire(self.cfg)+b'\n')
        return path
