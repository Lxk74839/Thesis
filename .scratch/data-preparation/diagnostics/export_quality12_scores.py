"""Production interface observation on synthetic catalog b, never account/test labels."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from quality_fusion import rank_quality


def wire(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    record=json.loads((ROOT/'records/sim-quality/grain-A-1.1.15-sim-quality-fusion-0.1.0.json').read_bytes())
    audit=ROOT/'data/quality-fusion-audit/20261016/formal'
    output=audit/'production-observations.jsonl'
    conditions=[(a,[(1-t)/2,t,(1-t)/2],'full') for a in (.25,.5,.75) for t in (.25,.5,.75)]
    conditions += [(a,[.25,.5,.25],'no_quality') for a in (.25,.5,.75)]
    conditions += [(.5,[.25,.5,.25],'mean_quality'),(1,[.25,.5,.25],'boundary')]
    with output.open('xb') as stream:
        for view in record['views']:
            folder=(ROOT/view['snapshot_path']).parent
            snapshot=json.loads((folder/'snapshot.json').read_bytes())
            registrations=[json.loads(line) for line in (folder/'registrations.jsonl').read_bytes().splitlines()]
            objects={}
            for name,key in (('batches.jsonl','sim_batch_id'),('events.jsonl','event_id'),('materials.jsonl','evidence_id')):
                objects.update({r[key]:r for r in map(json.loads,(folder/name).read_bytes().splitlines())})
            parents=sorted(snapshot['scope_sha256'],key=lambda p:p.encode())
            scores=[0]+[.5]*(len(parents)-2)+[1]
            binding={'schema_version':'fusion-binding-0.1.0','task_id':'PUBLIC-CATALOG-COMPONENT-CHECK',
                'C':parents,'C_sha256':sha(wire(parents)),'H_sha256':sha(b'public-no-user-history'),
                'base_scores':scores,'base_score_version':'public-synthetic-endpoints-0.1.0',
                'base_score_sha256':sha(wire(list(zip(parents,scores)))),'snapshot_id':snapshot['snapshot_id'],
                'verify_at_ms':snapshot['verify_at_ms'],'principal_id':'SIM-VERIFIER',
                'contract_sha256':snapshot['contract_sha256'],'K':10,
                'preference':{'source':'experiment_design','dimensions':['retail_stock'],'weights':{'retail_stock':1}}}
            acquired={'snapshot':snapshot,'policy_bytes':(folder/'policy.json').read_bytes(),
                'actions_bytes':(folder/'actions.jsonl').read_bytes(),
                'candidates':{p:{'registrations':[r for r in registrations if r['parent_asin']==p],
                    'originals':{key:wire(row) for key,row in objects.items() if row['parent_asin']==p}} for p in parents}}
            for alpha,beta,mode in conditions:
                binding.update(alpha=alpha,beta=beta,mode=mode)
                result=rank_quality(binding,acquired)
                stream.write(wire({'fixture':'synthetic_catalog_component_check','binding':binding,'result':result})+b'\n')
    print(json.dumps({'status':'exported','reranks':len(conditions)*len(record['views']),
        'accounts':0,'model_API_calls':0,'bytes':output.stat().st_size,'sha256':sha(output.read_bytes())},sort_keys=True))


if __name__=='__main__':main()
