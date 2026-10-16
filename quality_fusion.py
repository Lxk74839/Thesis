"""Normal-v1 SIM stock quality preparation and pure scoring (no model or IO in rank)."""
import copy
import json
import math
import os
from pathlib import Path
import tempfile
import uuid

from sim_normal import PROJECT, SimError, digest, json_bytes, read_json, safe_path, unique_object
from sim_scenarios import load_baseline

VERSION = 'sim-quality-fusion-0.1.0'
SNAPSHOT_TAG = b'Thesis-quality-fusion:snapshot\0'
ASSIGNMENT = {'domain':'Thesis-ticket12-quality-v1','seed':'20261016',
              'stocks':[25,50,75,100],'T_numerators':[1,4],'T_denominator':5}
RULES = {'attribute':'retail_stock','source':'experiment_design','weight':1,'stock_scale':100,
         'C_slots':['retail_status'],'A_checks':['same_parent_batch','same_location_unit'],
         'main_alpha':.5,'main_beta':[.25,.5,.25],'alpha_grid':[.25,.5,.75],
         'beta_T_grid':[.25,.5,.75],'score_decimals':12}
APPROVAL = {
    'report': {'path':'.scratch/data-preparation/ticket12-quality-dev-report-and-implementation-contract-20261016.md',
               'sha256':'5249861c92b1403836bc9b5e70b45d800a6ba8dc424a4e9c74c92c998cac88ca'},
    'authorization': {'path':'.scratch/data-preparation/ticket12-quality-offline-authorization-20261016.md',
                      'sha256':'f4d08021ce2bebf9246fba6fa161a7549c1352775d611b80b367597ebf5fa163'}}


class QualityError(ValueError):
    """A closed-scope quality contract violation."""


def need(condition, code):
    if not condition:
        raise QualityError(code)


def _decode(raw):
    try:
        return json.loads(raw, object_pairs_hook=unique_object,
                          parse_constant=lambda value: need(False, 'invalid_number'))
    except (ValueError, TypeError):
        raise QualityError('invalid_original_json') from None


def _acquired_objects(parent, pack, snapshot, policy):
    """Authenticate an acquired scoped subset; missing original bytes stay missing."""
    regs=pack['registrations']
    need(digest(json_bytes(regs))==snapshot['scope_sha256'][parent], 'incomplete_scope')
    index={r['target_id']:r for r in regs}
    need(len(index)==len(regs), 'duplicate_registration')
    batches=[r['target_id'] for r in regs if r['target_kind']=='batch']
    need(len(batches)==1, 'unsupported_scope')
    batch=batches[0]
    tau,sealed=snapshot['verify_at_ms'],snapshot['sealed_at_ms']
    authorities={r['issuer_id']:r for r in policy['issuers']}
    objects={}
    for reg in regs:
        need(type(reg['version']) is int and reg['version']==1, 'unsupported_scope')
        need(reg['parent_asin']==parent and reg['sim_batch_id']==batch and reg['source']=='SIM'
             and reg['receipt_status']=='accepted' and reg['registrar_id']==policy['registrar_id']
             and reg['registry_backend']=='local_sim_registry', 'invalid_registration')
        need(type(reg['registered_at_ms']) is int and reg['registered_at_ms']<=sealed<=tau, 'invalid_time')
    for key,raw in pack['originals'].items():
        need(key in index, 'unregistered_original')
        row=_decode(raw);reg=index[key];typ=reg['target_kind']
        need(json_bytes(row)==raw and digest(raw)==reg['content_sha256'], 'digest_mismatch')
        identity='sim_batch_id' if typ=='batch' else 'event_id' if typ=='event' else 'evidence_id'
        issuer=row.get('issuer_id',row.get('actor_id'))
        need(row[identity]==key and row['parent_asin']==parent and row['sim_batch_id']==batch
             and row.get('event_id')==reg['event_id'] and issuer==reg['issuer_id'] and row['source']=='SIM', 'object_mismatch')
        need(type(row['version']) is int and row['version']==1, 'unsupported_scope')
        need(typ in policy['read_scope']['target_kinds'], 'read_denied')
        authority=authorities.get(issuer,{})
        if typ=='material':
            need(row['kind'] in policy['read_scope']['material_kinds'], 'read_denied')
            need(row['kind'] in authority.get('material_kinds',[]), 'unauthorized_issuer')
            need(type(row['issued_at_ms']) is int and row['issued_at_ms']<=reg['registered_at_ms'], 'invalid_time')
            if row['kind']=='retail_status':
                need(row['temporal_mode']=='current_assertion' and type(row['valid_from_ms']) is int
                     and type(row['valid_to_ms']) is int and row['valid_from_ms']<=tau<row['valid_to_ms'], 'invalid_interval')
                observed=row['facts']['observed_at_ms']
                need(type(observed) is int and row['valid_from_ms']<=observed<row['valid_to_ms']
                     and observed<=row['issued_at_ms'], 'invalid_time')
                need(row['facts']['status']=='on_sale', 'unsupported_necessary_value')
                need(type(row['facts']['stock_units']) is int and 0<=row['facts']['stock_units']<=100
                     and row['facts']['unit']=='SIM_PACK', 'invalid_stock')
            else:
                need(row['temporal_mode']=='historical_fact', 'unsupported_temporal_rule')
            if row['kind']=='inspection_report':
                need(row['facts']['conclusion']=='pass' and row['facts']['test_scope']==['SIM-Q1'], 'unsupported_necessary_value')
        elif typ=='event':
            need(row['stage'] in authority.get('event_stages',[]), 'unauthorized_issuer')
            need(row['event_start_ms']<=row['event_end_ms']<=reg['registered_at_ms'], 'invalid_time')
        else:
            need(typ=='batch' and authority.get('may_create_batch') is True, 'unauthorized_issuer')
            need(row['created_at_ms']<=reg['registered_at_ms'], 'invalid_time')
        objects[key]=row
    stages=('harvest','packaging','storage','inspection','transport','retail')
    events={r['stage']:r for key,r in objects.items() if index[key]['target_kind']=='event'}
    need(set(events)<=set(stages) and len(events)==sum(index[k]['target_kind']=='event' for k in objects), 'unsupported_scope')
    for stage,event in events.items():
        prev=stages.index(stage)-1
        if prev>=0 and stages[prev] in events:
            predecessor=events[stages[prev]]
            need(event['predecessor_event_ids']==[predecessor['event_id']]
                 and predecessor['event_end_ms']<=event['event_start_ms'], 'invalid_event_path')
        elif prev<0:
            need(event['predecessor_event_ids']==[], 'invalid_event_path')
    for key,row in objects.items():
        if index[key]['target_kind']=='material':
            event=objects.get(row['event_id'])
            if event is not None:
                need(index[row['event_id']]['target_kind']=='event'
                     and index[row['event_id']]['registered_at_ms']<=index[key]['registered_at_ms'], 'invalid_event_dependency')
    materials={r['kind']:r for k,r in objects.items() if index[k]['target_kind']=='material'}
    sample,report=materials.get('inspection_sample'),materials.get('inspection_report')
    if sample and report:
        need(sample['facts']['sample_id']==report['facts']['sample_id']
             and sample['facts']['sampled_at_ms']<=report['facts']['test_started_at_ms']
             <=report['facts']['test_completed_at_ms']<=report['issued_at_ms'], 'invalid_inspection')
    dispatch,receipt=materials.get('transport_dispatch'),materials.get('transport_receipt')
    if dispatch and receipt:
        need(all(dispatch['facts'][k]==receipt['facts'][k] for k in
                 ('transport_segment_id','from_location_id','to_location_id','quantity_units','unit'))
             and receipt['facts']['handover_status']=='accepted'
             and dispatch['facts']['departed_at_ms']<=receipt['facts']['arrived_at_ms']<=receipt['issued_at_ms'], 'invalid_arrival')
    necessary={'inspection_sample','inspection_report','retail_status'}
    closed=all(r['target_id'] in objects for r in regs if r['target_kind']=='material'
               and necessary.intersection(authorities.get(r['issuer_id'],{}).get('material_kinds',[])))
    return list(objects.values()), batch in objects and set(events)==set(stages) and closed


def prepare_quality(sim_record, config_path, output_root):
    """Preserve an independent failure record without changing previous outputs."""
    try:
        return _prepare_quality(sim_record,config_path,output_root)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        code=str(exc) if isinstance(exc,QualityError) else exc.code if isinstance(exc,SimError) else 'io_error' if isinstance(exc,OSError) else 'invalid_input'
        failure=safe_path(PROJECT/'data/sim-quality/failures'/str(uuid.uuid4())/'failure.json')
        failure.parent.mkdir(parents=True)
        failure.write_bytes(json_bytes({'stage':'quality_fusion','status':'quality_fusion_incomplete','error':{'code':code}})+b'\n')
        error=QualityError(code)
        error.failure_record=failure.relative_to(PROJECT).as_posix()
        raise error from None


def _prepare_quality(sim_record, config_path, output_root):
    """Prepare new material bytes; never publish acceptance or read user tasks."""
    sim_record, config_path, output_root = map(safe_path, (sim_record, config_path, output_root))
    config = read_json(config_path)
    need(set(config) == {'schema_version','version','normal_binding','approval_binding','assignment','rules'}, 'invalid_config')
    need(config['schema_version']=='quality-fusion-config-0.1.0' and config['version']==VERSION
         and config['assignment']==ASSIGNMENT and config['rules']==RULES, 'unapproved_quality_contract')
    need(config['approval_binding']==APPROVAL, 'unapproved_quality_contract')
    for info in APPROVAL.values():
        need(digest(safe_path(info['path']).read_bytes())==info['sha256'], 'unapproved_quality_contract')
    normal, original_files, rows, paths, source_root = load_baseline(sim_record,config)
    parents = sorted(row['parent_asin'] for row in rows['batches.jsonl'])
    ordered = sorted(parents,key=lambda p:(digest(b'Thesis-ticket12-quality-v1\0'+b'20261016\0'+p.encode()),p.encode()))
    combinations = [(x,t) for x in (25,50,75,100) for t in (1,4)]
    allocation = {p:combinations[index%8] for index,p in enumerate(ordered)}
    relative = Path('data/sim-quality') / normal['catalog_version'] / VERSION
    destination = safe_path(output_root/relative)
    record_path = safe_path(output_root/'records/sim-quality'/f"{normal['catalog_version']}-{VERSION}.json")
    files = {}; views = []
    for label in ('Q1','Q2'):
        view_id = 'q_' + digest(b'Thesis-quality-fusion:view\0'+label.encode())
        prefix = 'views/'+view_id+'/'
        materials = copy.deepcopy(rows['materials.jsonl'])
        hashes = {}
        for row in materials:
            if row['kind']=='retail_status':
                x,t = allocation[row['parent_asin']]
                if label=='Q2':
                    t=5-t
                row['facts']['stock_units']=x
                row['valid_to_ms']=normal['sim_verify_at_ms']+(normal['sim_verify_at_ms']-row['valid_from_ms'])*t//(5-t)
                hashes[row['evidence_id']]=digest(json_bytes(row))
        registrations = copy.deepcopy(rows['registrations.jsonl'])
        for row in registrations:
            if row['target_id'] in hashes:
                row['content_sha256']=hashes[row['target_id']]
        values = {name:original_files[name] for name in ('batches.jsonl','events.jsonl','policy.json')}
        values.update({'materials.jsonl':b''.join(json_bytes(row)+b'\n' for row in materials),
                       'registrations.jsonl':b''.join(json_bytes(row)+b'\n' for row in registrations),
                       'actions.jsonl':b''})
        scopes = {p:digest(json_bytes([r for r in registrations if r['parent_asin']==p])) for p in parents}
        snap = {'schema_version':'quality-snapshot-0.1.0','source':'SIM','protocol_version':'quality-preference-protocol-0.1.0',
                'parent_snapshot_id':normal['snapshot_id'],'catalog_version':normal['catalog_version'],
                'verify_at_ms':normal['sim_verify_at_ms'],'sealed_at_ms':rows['snapshot.json'][0]['sealed_at_ms'],
                'cutoff_sequence':len(registrations),'policy_id':rows['policy.json'][0]['policy_id'],
                'read_principal_id':'SIM-VERIFIER','rules':RULES,'contract_sha256':digest(json_bytes(RULES)),
                'scope_sha256':scopes,'components':{name:{'sha256':digest(raw),'bytes':len(raw),'records':len(raw.splitlines())} for name,raw in values.items()}}
        snap['snapshot_id']='qf_'+digest(SNAPSHOT_TAG+json_bytes(snap))
        values['snapshot.json']=json_bytes(snap)+b'\n'
        files.update({prefix+name:raw for name,raw in values.items()})
        views.append({'view_id':view_id,'snapshot_id':snap['snapshot_id'],
                      'snapshot_path':(relative/prefix/'snapshot.json').as_posix()})
    files['view-index.jsonl']=b''.join(json_bytes(v)+b'\n' for v in views)
    files['private/allocation.jsonl']=b''.join(json_bytes({'parent_asin':p,'rank':i,'x':allocation[p][0],
        'Q1_T_numerator_over_5':allocation[p][1],'Q2_T_numerator_over_5':5-allocation[p][1]})+b'\n' for i,p in enumerate(ordered))
    inputs = {key:{'path':path.relative_to(PROJECT).as_posix(),'sha256':digest(path.read_bytes())}
              for key,path in {'quality_config':config_path,**{'normal_'+k:v for k,v in paths.items()}}.items()}
    producers = {name:digest((PROJECT/name).read_bytes()) for name in ('quality_fusion.py','prepare_data.py','recommendation_actions.py')}
    record = {'stage':'quality_fusion','status':'prepared_pending_independent_acceptance','version':VERSION,
              'counts':{'parents':len(parents),'views':2},'views':views,'inputs':inputs,'producer_sha256':producers,
              'components':{name:{'path':(relative/name).as_posix(),'sha256':digest(raw),'bytes':len(raw),'records':len(raw.splitlines())} for name,raw in files.items()},
              'independent_acceptance':'pending_separate_record','formal_package_status':'not_built',
              'model_execution_status':'not_run','ledger_deployment_status':'not_deployed','sample_sufficiency':'not_determined'}
    if record_path.exists():
        need(read_json(record_path)==record, 'output_conflict')
        for name,raw in files.items():
            target=safe_path(destination/name)
            need(target.is_file() and target.read_bytes()==raw, 'output_conflict')
        return record
    need(not destination.exists(), 'output_conflict')
    staging = Path(tempfile.mkdtemp(prefix='quality-fusion-',dir=PROJECT/'.tmp'))
    for name,raw in files.items():
        target=staging/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
    destination.parent.mkdir(parents=True,exist_ok=True)
    os.rename(staging,destination)
    record_path.parent.mkdir(parents=True,exist_ok=True)
    with record_path.open('xb') as stream:
        stream.write(json_bytes(record)+b'\n')
    return record


def rank_quality(binding, acquired):
    """Score supplied normal-v1 facts only; this function performs no IO."""
    fields={'schema_version','task_id','C','C_sha256','H_sha256','base_scores','base_score_version',
            'base_score_sha256','snapshot_id','verify_at_ms','principal_id','contract_sha256','K','alpha','beta','mode','preference'}
    need(set(binding)==fields and binding['schema_version']=='fusion-binding-0.1.0', 'invalid_binding')
    numeric=lambda v: type(v) in (int,float) and math.isfinite(v)
    parents,scores=binding['C'],binding['base_scores']
    need(isinstance(parents,list) and all(isinstance(p,str) and p for p in parents)
         and len(set(parents))==len(parents) and len(parents)==len(scores), 'invalid_candidates')
    need(all(numeric(b) and 0<=b<=1 for b in scores) and numeric(binding['alpha']) and 0<=binding['alpha']<=1
         and len(binding['beta'])==3 and all(numeric(b) and b>=0 for b in binding['beta'])
         and type(binding['K']) is int and binding['K']>0, 'invalid_number')
    need(binding['C_sha256']==digest(json_bytes(parents))
         and binding['base_score_sha256']==digest(json_bytes(list(zip(parents,scores)))), 'binding_mismatch')
    preference=binding['preference']
    need(set(preference)=={'source','dimensions','weights'} and preference['source']=='experiment_design'
         and len(set(preference['dimensions']))==len(preference['dimensions'])
         and set(preference['weights'])==set(preference['dimensions'])
         and all(numeric(w) and w>=0 for w in preference['weights'].values()), 'invalid_preference')
    need(binding['mode'] in ('full','no_quality','mean_quality','boundary'), 'invalid_mode')
    need(binding['mode']!='boundary' or binding['alpha']==1, 'invalid_boundary')
    snapshot=acquired['snapshot']
    need(type(binding['verify_at_ms']) is int and binding['verify_at_ms']==snapshot['verify_at_ms'], 'time_mismatch')
    need(snapshot['snapshot_id']=='qf_'+digest(SNAPSHOT_TAG+json_bytes({k:v for k,v in snapshot.items() if k!='snapshot_id'}))
         and binding['snapshot_id']==snapshot['snapshot_id'], 'snapshot_mismatch')
    need(snapshot['rules']==RULES and snapshot['contract_sha256']==digest(json_bytes(RULES))
         and binding['contract_sha256']==snapshot['contract_sha256'], 'contract_mismatch')
    need(acquired['actions_bytes']==b'' and snapshot['components']['actions.jsonl']['records']==0, 'unsupported_scope')
    need(digest(acquired['policy_bytes'])==snapshot['components']['policy.json']['sha256'], 'policy_mismatch')
    policy=_decode(acquired['policy_bytes'])
    need(policy['policy_id']==snapshot['policy_id'] and policy['read_principal_id']==binding['principal_id']==snapshot['read_principal_id']
         and policy['read_scope']['scope']=='current_snapshot_only', 'read_denied')
    rows=[]
    tau=binding['verify_at_ms']
    for parent,base in zip(binding['C'],binding['base_scores']):
        supplied=acquired['candidates'].get(parent)
        originals,graph= _acquired_objects(parent,supplied,snapshot,policy) if supplied is not None else ([],False)
        materials={r['kind']:r for r in originals if 'kind' in r}
        stocks=[r for r in originals if r.get('kind')=='retail_status'] if graph else []
        retail=stocks[0] if stocks else None
        conflict=len({(r['facts']['stock_units'],r['facts']['location_id']) for r in stocks})>1
        supported=retail is not None and not conflict
        x=retail['facts']['stock_units'] if supported else None
        t=(retail['valid_to_ms']-tau)/(retail['valid_to_ms']-retail['valid_from_ms']) if supported else 0
        complete=int(supported)
        arrival=materials.get('transport_receipt') if 'transport_dispatch' in materials else None
        checks=[bool(supported and arrival and retail['parent_asin']==arrival['parent_asin']
                     and retail['sim_batch_id']==arrival['sim_batch_id']),
                bool(supported and arrival and retail['facts']['location_id']==arrival['facts']['to_location_id']
                     and retail['facts']['unit']==arrival['facts']['unit'])]
        reasons=[]
        if not supported:
            reasons.append('conflicting_stock' if conflict else 'unacquired_stock_or_path')
        if arrival is None:
            reasons.append('unacquired_arrival')
        a=sum(checks)/2
        beta_total=math.fsum(binding['beta'])
        q=complete*math.fsum([binding['beta'][0]*complete,binding['beta'][1]*t,binding['beta'][2]*a])/beta_total if beta_total else 0
        if not beta_total:
            reasons.append('zero_beta_denominator')
        effective=complete if binding['mode']=='no_quality' else q
        m=x/100 if supported else 0
        eligible=bool(retail and 'inspection_sample' in materials and 'inspection_report' in materials)
        weights=preference['weights']
        total_weight=math.fsum(weights.values())
        factor=weights.get('retail_stock',0)/total_weight if total_weight else 0
        reasons.extend('unsupported_attribute:'+d for d in preference['dimensions'] if d!='retail_stock')
        if not total_weight:
            reasons.append('no_applicable_preference')
        contribution=effective*m*factor
        rows.append({'parent_asin':parent,'eligible':eligible,'x':x,'z':complete,
            'stock_state':'Conflict' if conflict else 'Supported' if supported else 'Unassessed','reasons':reasons,
            'citations':{'retail_stock':{'evidence_id':retail['evidence_id'],'pointer':'/facts/stock_units'}} if supported else {},
            'C':{'numerator':complete,'denominator':1},'T':t,'A':{'numerator':sum(checks),'denominator':2},
            'T_fraction':{'numerator':retail['valid_to_ms']-tau,'denominator':retail['valid_to_ms']-retail['valid_from_ms']} if supported else {'numerator':0,'denominator':0},
            'q':q,'effective_q':effective,'m':m,'contribution':contribution,
            'score':round(binding['alpha']*base+(1-binding['alpha'])*contribution,12)})
    supported=[r['q'] for r in rows if r['z']]
    mean=math.fsum(supported)/len(supported) if supported else 0
    if binding['mode']=='mean_quality':
        for row,base in zip(rows,binding['base_scores']):
            row['effective_q']=row['z']*mean
            row['contribution']=row['effective_q']*row['m']*factor
            row['score']=round(binding['alpha']*base+(1-binding['alpha'])*row['contribution'],12)
    ordered=sorted((r for r in rows if r['eligible']),key=lambda r:(-r['score'],r['parent_asin'].encode()))
    return {'version':'fusion-score-0.1.0','binding_sha256':digest(json_bytes(binding)),
            'candidates':rows,'order':[r['parent_asin'] for r in ordered],
            'G':[r['parent_asin'] for r in rows if r['eligible']],
            'topK':[r['parent_asin'] for r in ordered[:binding['K']]],
            'mean_quality':{'value':mean,'denominator':len(supported)}}
