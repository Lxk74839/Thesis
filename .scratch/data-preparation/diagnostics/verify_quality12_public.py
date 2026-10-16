"""Independent raw-reference check of the public worked example before formal audit."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tests'))
from quality_fixtures import scoring_fixture,wire

spec=importlib.util.spec_from_file_location('independent_quality_raw',Path(__file__).with_name('verify_quality12_raw.py'))
reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)


def write_view(folder,acquired,corrupt=None):
    folder.mkdir()
    originals={k:json.loads(raw) for pack in acquired['candidates'].values() for k,raw in pack['originals'].items()}
    regs=sorted([r for pack in acquired['candidates'].values() for r in pack['registrations']],key=lambda r:r['sequence'])
    if corrupt=='unit':
        next(r for r in originals.values() if r.get('kind')=='retail_status')['facts']['unit']='kg'
    elif corrupt=='sample':
        next(r for r in originals.values() if r.get('kind')=='inspection_report')['facts']['sample_id']='WRONG'
    elif corrupt=='expiry':
        next(r for r in originals.values() if r.get('kind')=='retail_status')['valid_to_ms']=acquired['snapshot']['verify_at_ms']
    for r in regs:r['content_sha256']=hashlib.sha256(wire(originals[r['target_id']])).hexdigest()
    raw={}
    for name,key in (('batches.jsonl','sim_batch_id'),('events.jsonl','stage'),('materials.jsonl','kind')):
        values=[r for r in originals.values() if key in r and
            (name!='batches.jsonl' or 'created_at_ms' in r)]
        raw[name]=b''.join(wire(r)+b'\n' for r in values)
    raw.update({'registrations.jsonl':b''.join(wire(r)+b'\n' for r in regs),
                'policy.json':acquired['policy_bytes'],'actions.jsonl':b''})
    snap=copy.deepcopy(acquired['snapshot']);snap.pop('snapshot_id')
    snap['components']={n:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v),'records':len(v.splitlines())} for n,v in raw.items()}
    snap['scope_sha256']={p:hashlib.sha256(wire([r for r in regs if r['parent_asin']==p])).hexdigest() for p in acquired['candidates']}
    snap['snapshot_id']='qf_'+hashlib.sha256(b'Thesis-quality-fusion:snapshot\0'+wire(snap)).hexdigest()
    raw['snapshot.json']=wire(snap)+b'\n'
    for name,value in raw.items():(folder/name).write_bytes(value)


def main():
    with tempfile.TemporaryDirectory(dir=ROOT/'.tmp') as temp:
        root=Path(temp);binding,acquired=scoring_fixture(root)
        write_view(root/'public',acquired)
        snap,facts,_=reference.reconstruct(root/'public')
        byid={r['parent_asin']:r for r in facts}
        assert (byid['DEMO-A']['x'],byid['DEMO-A']['q'],byid['DEMO-A']['m'])==(75,.6,.75)
        assert (byid['DEMO-B']['x'],byid['DEMO-B']['q'],byid['DEMO-B']['m'])==(100,.9,1)
        for case in ('unit','sample','expiry'):
            write_view(root/case,acquired,case)
            try:reference.reconstruct(root/case)
            except ValueError:pass
            else:raise AssertionError('independent_negative_accepted:'+case)
    summary={'status':'passed','public_candidates':4,'independent_negative_cases':3,
             'expected_source':'approved_worked_example_and_contract','model_API_calls':0}
    path=ROOT/'data/quality-fusion-audit/20261016/public-reference-summary.json'
    with path.open('xb') as stream:stream.write(wire(summary)+b'\n')
    print(json.dumps(summary,sort_keys=True))


if __name__=='__main__':main()
