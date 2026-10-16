"""Public hand-built originals first; no accepted data or user reads."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import support
from support import ROOT,HERE,canonical,digest,write,guard,resources
from reference import derive, TAG, STAGES, KINDS

OUT=ROOT/'data/diagnostics/ticket12-quality-dev-20261016/public-example'
TAU=1791417600000
FROM=1791374400000


def fixture():
    batch_rows=[]; events=[]; materials=[]
    stage_actors=['PRODUCER','PACKER','WAREHOUSE','LAB','CARRIER','RETAIL']
    issuer_kinds={'PRODUCER':['harvest_record'],'PACKER':['packaging_binding'],
                  'WAREHOUSE':['storage_log'],'SAMPLER':['inspection_sample'],
                  'LAB':['inspection_report'],'CARRIER':['transport_dispatch'],
                  'RECEIVER':['transport_receipt'],'RETAIL':['retail_status']}
    policy={'source':'SIM','policy_id':'DEMO-POLICY','read_principal_id':'SIM-VERIFIER',
            'read_scope':{'target_kinds':['batch','event','material'],'material_kinds':list(KINDS),'scope':'current_snapshot_only'},
            'registrar_id':'DEMO-REGISTRY','issuers':[
                {'issuer_id':'DEMO-'+actor,'may_create_batch':actor=='PRODUCER',
                 'event_stages':[stage for stage,who in zip(STAGES,stage_actors) if who==actor],
                 'material_kinds':kinds} for actor,kinds in issuer_kinds.items()]}
    for name,stock,t in [('HI',25,Fraction(1,5)),('A',75,Fraction(1,5)),('B',100,Fraction(4,5)),('LO',25,Fraction(1,5))]:
        parent='DEMO-'+name; batch=parent+'-BATCH'
        common={'parent_asin':parent,'sim_batch_id':batch,'source':'SIM','version':1}
        batch_rows.append({**common,'issuer_id':'DEMO-PRODUCER','created_at_ms':FROM-7*86400000})
        starts={stage:FROM-(6-i)*86400000 for i,stage in enumerate(STAGES)}
        starts['retail']=FROM
        ends={stage:start+(6 if stage=='inspection' else 1)*3600000 for stage,start in starts.items()}
        ends['retail']=FROM
        for i,stage in enumerate(STAGES):
            events.append({**common,'event_id':parent+'-'+stage,'stage':stage,
                           'actor_id':'DEMO-'+stage_actors[i],'event_start_ms':starts[stage],
                           'event_end_ms':ends[stage],
                           'predecessor_event_ids':[parent+'-'+STAGES[i-1]] if i else []})
        ins=starts['inspection']; trans=starts['transport']; arrived=ends['transport']
        values=[('inspection_sample','inspection','SAMPLER',ins+600000,{'sample_id':parent+'-SAMPLE','sampled_at_ms':ins+300000}),
                ('inspection_report','inspection','LAB',ins+10800000,{'sample_id':parent+'-SAMPLE','test_scope':['SIM-Q1'],
                  'test_started_at_ms':ins+1800000,'test_completed_at_ms':ins+7200000,'conclusion':'pass'}),
                ('transport_dispatch','transport','CARRIER',trans+300000,{'transport_segment_id':parent+'-TRIP',
                  'from_location_id':'DEMO-WH','to_location_id':'DEMO-SHOP','unit':'SIM_PACK','quantity_units':100,'departed_at_ms':trans}),
                ('transport_receipt','transport','RECEIVER',arrived+300000,{'transport_segment_id':parent+'-TRIP',
                  'from_location_id':'DEMO-WH','to_location_id':'DEMO-SHOP','unit':'SIM_PACK','quantity_units':100,
                  'arrived_at_ms':arrived,'handover_status':'accepted'}),
                ('retail_status','retail','RETAIL',FROM+300000,{'stock_units':stock,'observed_at_ms':FROM,
                  'status':'on_sale','location_id':'DEMO-SHOP','unit':'SIM_PACK'})]
        for kind,stage,issuer,issued,facts in values:
            row={**common,'evidence_id':parent+'-'+kind,'event_id':parent+'-'+stage,'kind':kind,
                 'issuer_id':'DEMO-'+issuer,'issued_at_ms':issued,'facts':facts,
                 'temporal_mode':'current_assertion' if kind=='retail_status' else 'historical_fact'}
            if kind=='retail_status':
                row.update(valid_from_ms=FROM,valid_to_ms=TAU+int((TAU-FROM)*t/(1-t)))
            materials.append(row)
    return {'batches.jsonl':batch_rows,'events.jsonl':events,'materials.jsonl':materials,'policy.json':policy}


def save(folder,data,stale=None,remove_registration=False):
    folder.mkdir()
    events={r['event_id']:r for r in data['events.jsonl']}
    regs=[]
    for name,typ,idkey in [('batches.jsonl','batch','sim_batch_id'),('events.jsonl','event','event_id'),('materials.jsonl','material','evidence_id')]:
        for row in data[name]:
            when=row['created_at_ms']+60000 if typ=='batch' else row['event_end_ms']+60000 if typ=='event' else max(row['issued_at_ms']+60000,events[row['event_id']]['event_end_ms']+120000)
            key=row[idkey]
            regs.append({'target_id':key,'target_kind':typ,'registration_id':'DEMO-REG-'+key,
                         'source':'SIM','version':1,'event_id':row.get('event_id'),
                         'parent_asin':row['parent_asin'],'sim_batch_id':row['sim_batch_id'],
                         'issuer_id':row.get('issuer_id',row.get('actor_id')),'receipt_status':'accepted',
                         'registered_at_ms':when,'registrar_id':'DEMO-REGISTRY','registry_backend':'local_sim_registry',
                         'content_sha256':stale if key=='DEMO-A-retail_status' and stale else digest(canonical(row))})
    if remove_registration:
        regs=[r for r in regs if r['target_id']!='DEMO-A-retail_status']
    regs.sort(key=lambda r:(r['registered_at_ms'],r['target_id']))
    for i,row in enumerate(regs,1):row['sequence']=i
    allfiles={**data,'registrations.jsonl':regs,'actions.jsonl':[]}
    components={}
    for name,rows in allfiles.items():
        raw=canonical(rows)+b'\n' if name=='policy.json' else b''.join(canonical(r)+b'\n' for r in rows)
        with (folder/name).open('xb') as stream:stream.write(raw)
        components[name]={'sha256':digest(raw),'bytes':len(raw),'records':len(raw.splitlines())}
    snap={'schema_version':'quality-diagnostic-snapshot-0.1.0','status':'public_demo_only','source':'SIM',
          'verify_at_ms':TAU,'sealed_at_ms':FROM+600000,'cutoff_sequence':len(regs),
          'policy_id':'DEMO-POLICY','read_principal_id':'SIM-VERIFIER','components':components}
    snap['snapshot_id']='qd_'+digest(TAG+canonical(snap))
    write(folder/'snapshot.json',snap)


def main():
    guard([HERE/'support.py',HERE/'reference.py',HERE/'public_examples.py'],OUT)
    OUT.mkdir(parents=True,exist_ok=False)
    base=fixture()
    save(OUT/'base',base)
    result=derive(OUT/'base')
    by={r['parent_asin']:r for r in result}
    b={'DEMO-HI':1.,'DEMO-A':.9,'DEMO-B':.6,'DEMO-LO':0.}
    assert all(r['eligible'] and r['z']==1 and r['C']=={'numerator':1,'denominator':1}
               and r['A']=={'numerator':2,'denominator':2} for r in result)
    q={p:Fraction(**r['q_by_beta_T']['0.5']) for p,r in by.items()}
    m={p:Fraction(**r['m']) for p,r in by.items()}
    full={p:round(.5*b[p]+.5*float(q[p]*m[p]),12) for p in b}
    noq={p:round(.5*b[p]+.5*float(m[p]),12) for p in b}
    mean=sum(q.values())/4
    ctrl={p:round(.5*b[p]+.5*float(mean*m[p]),12) for p in b}
    order=lambda scores:sorted(scores,key=lambda p:(-scores[p],p.encode()))
    assert order(full)==['DEMO-B','DEMO-A','DEMO-HI','DEMO-LO']
    assert order(noq)==order(ctrl)==['DEMO-A','DEMO-B','DEMO-HI','DEMO-LO']
    assert full['DEMO-A']==.675 and full['DEMO-B']==.75 and mean==Fraction(27,40)
    cases=[]
    for case in ('stale_digest','wrong_unit','denied_retail','expired','zero_interval','wrong_batch','stock_conflict','missing_receipt','missing_registration'):
        data=deepcopy(base)
        stock=next(r for r in data['materials.jsonl'] if r['evidence_id']=='DEMO-A-retail_status')
        old=digest(canonical(stock))
        if case=='stale_digest':stock['facts']['stock_units']=50
        if case=='wrong_unit':stock['facts']['unit']='KG'
        if case=='denied_retail':data['policy.json']['read_scope']['material_kinds'].remove('retail_status')
        if case=='expired':stock['valid_to_ms']=TAU
        if case=='zero_interval':stock['valid_to_ms']=stock['valid_from_ms']
        if case=='wrong_batch':stock['sim_batch_id']='DEMO-WRONG-BATCH'
        if case=='stock_conflict':
            other=deepcopy(stock);other['evidence_id']+='-OTHER';other['facts']['stock_units']=50
            data['materials.jsonl'].append(other)
        if case=='missing_receipt':
            data['materials.jsonl']=[r for r in data['materials.jsonl'] if r['evidence_id']!='DEMO-A-transport_receipt']
        save(OUT/case,data,old if case=='stale_digest' else None,case=='missing_registration')
        try:
            rows=derive(OUT/case)
        except ValueError as error:
            assert case=='missing_registration' and str(error)=='registration_scope_not_complete'
            cases.append({'case':case,'expected_scope_rejection':True});continue
        actual=next(r for r in rows if r['parent_asin']=='DEMO-A')
        if case=='missing_receipt':
            assert actual['z']==1 and actual['C']['numerator']==1 and actual['A']=={'numerator':0,'denominator':2}
        else:
            assert actual['z']==0
        if case=='stock_conflict':assert actual['stock_state']=='Conflict' and actual['eligible']
        cases.append({'case':case,'z':actual['z'],'A':actual['A'],'eligible':actual['eligible']})
    # A larger score increase of another candidate can worsen one's rank despite T increasing.
    assert .5*.9+.5*.6*.25 > .5*.3+.5*.6*1
    assert .5*.9+.5*.9*.25 < .5*.3+.5*.9*1
    write(OUT/'result.json',{'status':'passed','all_ids_public_demo':True,'raw_reference_rows':4,
          'full_order':order(full),'noq_order':order(noq),'mean_control_order':order(ctrl),
          'mean_q':str(mean),'full_scores':full,'negative_cases':cases,
          'rank_direction_is_relative_not_individual_monotonicity':True,'resources':resources()})
    print('Public raw-material example and nine negative cases passed before real generation.',flush=True)


if __name__=='__main__':
    try:main()
    except Exception as error:
        if OUT.exists() and not (OUT/'failure.json').exists():
            write(OUT/'failure.json',{'status':'failed_preserved','type':type(error).__name__,'reason':str(error)})
        raise
