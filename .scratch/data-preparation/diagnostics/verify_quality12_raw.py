"""Independent normal-v1 quality reference. Standard library; no production imports.

Answers come from raw originals/registry/path/policy/time. Allocation and exported
production scores are checked only after reference facts have been reconstructed.
"""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
VERSION='quality-reference-0.1.0'
STAGES=('harvest','packaging','storage','inspection','transport','retail')
KINDS={'harvest_record':'harvest','packaging_binding':'packaging','storage_log':'storage',
       'inspection_sample':'inspection','inspection_report':'inspection',
       'transport_dispatch':'transport','transport_receipt':'transport','retail_status':'retail'}


def wire(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check(condition,code):
    if not condition:raise ValueError(code)


def unique(pairs):
    result={}
    for key,value in pairs:
        check(key not in result,'duplicate_key');result[key]=value
    return result


def parse(raw):
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda value:check(False,'nonfinite'))


def reconstruct(folder):
    raw={name:(folder/name).read_bytes() for name in
         ('batches.jsonl','events.jsonl','materials.jsonl','registrations.jsonl','policy.json','actions.jsonl','snapshot.json')}
    snap=parse(raw['snapshot.json']);policy=parse(raw['policy.json'])
    check(snap['snapshot_id']=='qf_'+sha(b'Thesis-quality-fusion:snapshot\0'+wire({k:v for k,v in snap.items() if k!='snapshot_id'})), 'snapshot_digest')
    check(raw['actions.jsonl']==b'' and snap['protocol_version']=='quality-preference-protocol-0.1.0','normal_v1_only')
    for name,info in snap['components'].items():
        check(sha(raw[name])==info['sha256'] and len(raw[name])==info['bytes'] and len(raw[name].splitlines())==info['records'],'component_digest')
    rows={name:[parse(line) for line in content.splitlines()] for name,content in raw.items()}
    for name,values in rows.items():
        check(b''.join(wire(row)+b'\n' for row in values)==raw[name],'canonical_bytes')
    regs=rows['registrations.jsonl'];objects={}
    for name,key in (('batches.jsonl','sim_batch_id'),('events.jsonl','event_id'),('materials.jsonl','evidence_id')):
        for row in rows[name]:
            check(row[key] not in objects,'duplicate_object');objects[row[key]]=row
    index={r['target_id']:r for r in regs}
    check(len(index)==len(regs)==len(objects) and set(index)==set(objects),'closed_registration')
    check([r['sequence'] for r in regs]==list(range(1,len(regs)+1)) and snap['cutoff_sequence']==len(regs),'cutoff_sequence')
    check(policy['read_principal_id']==snap['read_principal_id']=='SIM-VERIFIER'
          and policy['policy_id']==snap['policy_id'] and policy['read_scope']['scope']=='current_snapshot_only','principal')
    authorities={a['issuer_id']:a for a in policy['issuers']}
    check(len(authorities)==len(policy['issuers']),'issuer_identity')
    tau,sealed=snap['verify_at_ms'],snap['sealed_at_ms']
    for key,row in objects.items():
        reg=index[key];kind=reg['target_kind'];issuer=row.get('issuer_id',row.get('actor_id'))
        check(reg['content_sha256']==sha(wire(row)) and reg['version']==row['version']==1
              and type(row['version']) is int and type(reg['version']) is int,'object_digest_version')
        check(row['source']==reg['source']=='SIM' and reg['receipt_status']=='accepted'
              and reg['registry_backend']=='local_sim_registry' and reg['registrar_id']==policy['registrar_id'],'receipt')
        check((reg['parent_asin'],reg['sim_batch_id'],reg['event_id'],reg['issuer_id'])==
              (row['parent_asin'],row['sim_batch_id'],row.get('event_id'),issuer),'identity')
        check(type(reg['registered_at_ms']) is int and reg['registered_at_ms']<=sealed<=tau,'registration_time')
        check(kind in policy['read_scope']['target_kinds'],'read_kind')
        auth=authorities[issuer]
        if kind=='material':
            check(row['kind'] in KINDS and row['kind'] in auth['material_kinds']
                  and row['kind'] in policy['read_scope']['material_kinds'],'material_permission')
            event=objects[row['event_id']]
            check(event['stage']==KINDS[row['kind']] and index[event['event_id']]['registered_at_ms']<=reg['registered_at_ms'],'material_event')
            check(event['event_start_ms']<=row['issued_at_ms']<=reg['registered_at_ms'],'issue_time')
            check(row['temporal_mode']==('current_assertion' if row['kind']=='retail_status' else 'historical_fact'),'temporal_mode')
        elif kind=='event':
            check(row['stage'] in auth['event_stages'] and row['event_start_ms']<=row['event_end_ms']<=reg['registered_at_ms'],'event_authority_time')
        else:
            check(kind=='batch' and auth['may_create_batch'] and row['created_at_ms']<=reg['registered_at_ms'],'batch_authority')
    facts=[]
    parents=sorted(snap['scope_sha256'],key=lambda p:p.encode())
    check(len(rows['batches.jsonl'])==len(parents),'parent_count')
    for parent in parents:
        scoped=[r for r in regs if r['parent_asin']==parent]
        check(sha(wire(scoped))==snap['scope_sha256'][parent],'scope_closure')
        batch=[objects[r['target_id']] for r in scoped if r['target_kind']=='batch']
        check(len(batch)==1 and len(scoped)==15,'normal_scope')
        batch=batch[0];group=[objects[r['target_id']] for r in scoped]
        check(all(r['sim_batch_id']==batch['sim_batch_id'] for r in group),'parent_batch')
        events={r['stage']:r for r in group if 'stage' in r}
        materials={r['kind']:r for r in group if 'kind' in r}
        check(set(events)==set(STAGES) and set(materials)==set(KINDS),'normal_slots')
        previous=None
        for stage in STAGES:
            event=events[stage]
            check(event['predecessor_event_ids']==([previous['event_id']] if previous else []),'predecessor')
            check((previous['event_end_ms'] if previous else batch['created_at_ms'])<=event['event_start_ms'],'path_time')
            previous=event
        sample,report=(materials[k] for k in ('inspection_sample','inspection_report'))
        check(sample['facts']['sample_id']==report['facts']['sample_id'] and report['facts']['conclusion']=='pass'
              and report['facts']['test_scope']==['SIM-Q1'],'R1')
        check(sample['facts']['sampled_at_ms']<=report['facts']['test_started_at_ms']<=report['facts']['test_completed_at_ms']<=report['issued_at_ms'],'sample_time')
        dispatch,receipt,retail=(materials[k] for k in ('transport_dispatch','transport_receipt','retail_status'))
        check(all(dispatch['facts'][k]==receipt['facts'][k] for k in ('transport_segment_id','from_location_id','to_location_id','quantity_units','unit')),'arrival_route')
        check(dispatch['facts']['departed_at_ms']<=receipt['facts']['arrived_at_ms']<=retail['facts']['observed_at_ms']
              and receipt['facts']['handover_status']=='accepted','arrival_time')
        rf=retail['facts'];x=rf['stock_units']
        check(type(x) is int and 0<=x<=100 and rf['unit']=='SIM_PACK' and rf['status']=='on_sale','stock_R5')
        start,end=retail['valid_from_ms'],retail['valid_to_ms']
        check(start<=tau<end and start<=rf['observed_at_ms']<end and rf['observed_at_ms']<=retail['issued_at_ms'],'stock_time')
        temporal=Fraction(end-tau,end-start)
        checks=[retail['parent_asin']==receipt['parent_asin'] and retail['sim_batch_id']==receipt['sim_batch_id'],
                rf['location_id']==receipt['facts']['to_location_id'] and rf['unit']==receipt['facts']['unit']]
        a=Fraction(sum(checks),2);m=Fraction(x,100)
        quality=Fraction(1,4)+temporal/2+a/4
        facts.append({'parent_asin':parent,'x':x,'z':1,'C':{'numerator':1,'denominator':1},
            'T':{'numerator':temporal.numerator,'denominator':temporal.denominator},
            'A':{'numerator':sum(checks),'denominator':2},'q':float(quality),'m':float(m),
            'eligible':True,'stock_evidence_id':retail['evidence_id'],'stock_sha256':index[retail['evidence_id']]['content_sha256']})
    return snap,facts,rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--record',default='records/sim-quality/grain-A-1.1.15-sim-quality-fusion-0.1.0.json')
    parser.add_argument('--output-root',default='.');parser.add_argument('--audit-name',default='formal')
    args=parser.parse_args();root=(ROOT/args.output_root).resolve();record=parse((ROOT/args.record).read_bytes())
    audit=ROOT/'data/quality-fusion-audit/20261016'/args.audit_name;audit.mkdir(parents=True,exist_ok=True)
    output=[];worlds=[]
    for view in record['views']:
        folder=(root/view['snapshot_path']).parent
        snap,facts,rows=reconstruct(folder)
        output.extend({'snapshot_id':snap['snapshot_id'],**f} for f in facts)
        worlds.append((snap,facts,rows))
    # Persist the independent answers before checking allocation or any score export.
    with (audit/'raw-reference.jsonl').open('xb') as stream:
        for row in output:stream.write(wire(row)+b'\n')
    ordered=sorted([f['parent_asin'] for f in worlds[0][1]],key=lambda p:(sha(b'Thesis-ticket12-quality-v1\0' + b'20261016\0' + p.encode()),p.encode()))
    combinations=[(x,t) for x in (25,50,75,100) for t in (Fraction(1,5),Fraction(4,5))]
    assigned={p:combinations[i%8] for i,p in enumerate(ordered)}
    for wi,(_,facts,_) in enumerate(worlds):
        for fact in facts:
            x,t=assigned[fact['parent_asin']];t=1-t if wi else t
            check((fact['x'],Fraction(**fact['T']))==(x,t),'SHA_allocation')
    # Verify copied upstream bytes and the exact two allowed material-field changes.
    original_record=parse((ROOT/record['inputs']['normal_record']['path']).read_bytes())
    baseline={name:(ROOT/info['path']).read_bytes() for name,info in original_record['components'].items()}
    for view,(_,_,rows) in zip(record['views'],worlds):
        folder=(root/view['snapshot_path']).parent
        for name in ('batches.jsonl','events.jsonl','policy.json'):
            check((folder/name).read_bytes()==baseline[name],'upstream_copy')
        original_materials=[parse(line) for line in baseline['materials.jsonl'].splitlines()]
        for before,after in zip(original_materials,rows['materials.jsonl']):
            before=parse(wire(before));after=parse(wire(after))
            if before['kind']=='retail_status':
                after['facts']['stock_units']=before['facts']['stock_units'];after['valid_to_ms']=before['valid_to_ms']
            check(before==after,'unapproved_material_change')
        for before,after in zip(map(parse,baseline['registrations.jsonl'].splitlines()),rows['registrations.jsonl']):
            after=dict(after);after['content_sha256']=before['content_sha256'];check(before==after,'unapproved_registration_change')
    summary={'version':VERSION,'status':'passed','views':len(worlds),'references':len(output),
        'parents_per_view':[len(w[1]) for w in worlds],'histogram':dict(Counter(str((r['x'],r['T']['numerator'],r['T']['denominator'])) for r in output)),
        'all_C_one':all(r['C']=={'numerator':1,'denominator':1} for r in output),
        'all_A_one':all(r['A']=={'numerator':2,'denominator':2} for r in output),
        'reference_sha256':sha((audit/'raw-reference.jsonl').read_bytes()),'model_API_calls':0}
    (audit/'raw-reference-summary.json').write_bytes(wire(summary)+b'\n');print(json.dumps(summary,sort_keys=True))


if __name__=='__main__':main()
