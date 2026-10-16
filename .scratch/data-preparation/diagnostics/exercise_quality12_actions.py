"""Execute the approved public F/A/B adapters; actual state transitions, zero models."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from quality_fixtures import scoring_fixture
from test_recommendation_actions import LIMITS,start,step,wrong_draft


def encode(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),
                      default=lambda raw:{'bytes_hex':raw.hex()}).encode()


def main():
    audit=ROOT/'data/quality-fusion-audit/20261016'
    traces=[]
    with tempfile.TemporaryDirectory(dir=ROOT/'.tmp') as temp:
        binding,available=scoring_fixture(Path(temp));parent=binding['C'][0]
        retail=next(k for k,r in available['candidates'][parent]['originals'].items() if json.loads(r).get('kind')=='retail_status')
        for mode in ('full','no_feedback','fixed'):
            state=start(binding,available,mode)
            states=[state]
            state=step(state,'submit_draft',draft=wrong_draft(state));states.append(state)
            state=step(state,'verify_draft','推荐依据核验');states.append(state)
            if mode!='no_feedback':
                issue=state['visible_issues'][0]
                state=step(state,'revise_and_resubmit',issue_id=issue['issue_id'],draft_id='PUBLIC-D1',pointer=issue['pointer'],value=retail);states.append(state)
                state=step(state,'verify_draft','推荐依据核验');states.append(state)
            state=step(state,'finalize');states.append(state)
            traces.append({'fixture':'F','mode':mode,'states':states})
        partial=copy.deepcopy(available)
        for key,raw in list(partial['candidates'][parent]['originals'].items()):
            if json.loads(raw).get('kind') in ('inspection_sample','retail_status'):
                partial['candidates'][parent]['originals'].pop(key)
        for mode in ('full','no_feedback','fixed'):
            state=start(binding,partial,mode,{**LIMITS,'logical_tools':123},available);states=[state]
            state=step(state,'acquire','生命周期追溯',parent_asin=parent,slot='R5.retail_status',action_id='PUBLIC-A1');states.append(state)
            originals={k:available['candidates'][parent]['originals'][k] for k in state['pending']['target_ids']}
            state=step(state,'settle','生命周期追溯',action_id='PUBLIC-A1',success=True,originals=originals);states.append(state)
            traces.append({'fixture':'A','mode':mode,'states':states})
        for mode in ('full','no_feedback','fixed'):
            state=start(binding,available,mode,{**LIMITS,'logical_tools':126});states=[state]
            state=step(state,'submit_draft',draft=wrong_draft(state));states.append(state)
            state=step(state,'verify_draft','推荐依据核验');states.append(state)
            if mode!='no_feedback':
                issue=state['visible_issues'][0]
                state=step(state,'revise_and_resubmit',issue_id=issue['issue_id'],draft_id='PUBLIC-D1',pointer=issue['pointer'],value=retail);states.append(state)
            state=step(state,'finalize');states.append(state)
            traces.append({'fixture':'B','mode':mode,'states':states})
    path=audit/'action-fixture-traces.jsonl'
    with path.open('xb') as stream:
        for trace in traces:stream.write(encode(trace)+b'\n')
    summary={'status':'executed_public_fixtures','fixtures':len(traces),'states':sum(len(t['states']) for t in traces),
             'model_API_calls':0,'real_model_benefit':'not_measured','trace_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (audit/'action-fixture-summary.json').write_bytes(encode(summary)+b'\n');print(json.dumps(summary,sort_keys=True))


if __name__=='__main__':main()
