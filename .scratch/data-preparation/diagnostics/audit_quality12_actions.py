"""Independent public fixture audit; no production scoring/state imports."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
AUDIT=ROOT/'data/quality-fusion-audit/20261016'


def check(condition,code):
    if not condition:raise ValueError(code)


def original(state,parent,key):
    raw=state['acquired']['candidates'][parent]['originals'][key]['bytes_hex']
    return json.loads(bytes.fromhex(raw))


def main():
    traces=[json.loads(line) for line in (AUDIT/'action-fixture-traces.jsonl').read_bytes().splitlines()]
    check(len(traces)==9,'trace_count');transitions=0;budget_cells=0
    for trace in traces:
        states=trace['states'];first,last=states[0],states[-1];mode=trace['mode']
        check(first['fixture']=='public_deterministic_adapter','fixture_marker')
        packs=first['acquired']['candidates']
        initial=3+sum(len(p['registrations'])+len(p['originals']) for p in packs.values())
        check(first['budget']['used']['logical_tools']==initial,'bootstrap_logical_count')
        for before,after in zip(states,states[1:]):
            transitions+=1
            check(before['binding']==after['binding'] and before['mode']==after['mode'],'immutable_binding')
            for key,limit in after['budget']['limits'].items():
                used,reserved,remaining=(after['budget'][group][key] for group in ('used','reserved','remaining'))
                check(used>=before['budget']['used'][key] and used>=0 and reserved>=0 and remaining>=0,'monotonic_budget')
                check(used+reserved+remaining==limit,'root_budget_conservation');budget_cells+=1
            check(after['budget']['used']['model_calls']==after['budget']['used']['input_tokens']==after['budget']['used']['output_tokens']==0,'zero_models')
        if trace['fixture']=='F':
            draft=last['drafts'][0]['content'];item=draft['items'][0];parent=item['parent_asin']
            check(original(last,parent,item['stock_citation'])['kind']=='inspection_report','F_initial_wrong_attribute')
            check(last['issues'][0]['code']=='wrong_attribute_citation','F_actual_issue')
            if mode=='no_feedback':
                check(last['terminal']=='blocked_evidence' and len(last['drafts'])==1 and not last['revisions'],'F_disabled')
                check(all(not s['visible_issues'] for s in states),'F_hidden')
            else:
                check(len(last['drafts'])==2 and len(last['revisions'])==1,'F_revision_count')
                fixed=last['drafts'][1]['content']['items'][0]
                raw=original(last,parent,fixed['stock_citation'])
                check(raw['kind']=='retail_status' and raw['facts']['stock_units']==fixed['stock_value'],'F_actual_repair')
                check(last['revisions'][0]['old']==item['stock_citation'] and last['revisions'][0]['new']==fixed['stock_citation'],'F_old_new')
                check(last['terminal']=='released' and last['delivered']==[parent],'F_release')
        elif trace['fixture']=='A':
            pending=states[1]['pending'];expected='R1.inspection_sample' if mode=='fixed' else 'R5.retail_status'
            check(pending['executed_slot']==expected,'A_router')
            for key in pending['target_ids']:
                check(original(last,pending['parent_asin'],key)['kind']==expected.split('.')[1],'A_actual_return')
            check(last['budget']['used']['logical_tools']==initial+1 and last['budget']['remaining']['logical_tools']==1,'A_single_unit')
        else:
            check(len(last['drafts'])==1 and not last['revisions'],'B_no_free_repair')
            if mode!='no_feedback':check(last['terminal']=='incomplete_budget' and last['budget']['remaining']['logical_tools']==0,'B_root_stop')
            else:check(last['terminal']=='blocked_evidence','B_no_feedback_gate')
    summary={'status':'passed','fixtures':len(traces),'transitions':transitions,'budget_cells':budget_cells,
        'real_model_benefit':'not_measured','model_API_calls':0,
        'trace_sha256':hashlib.sha256((AUDIT/'action-fixture-traces.jsonl').read_bytes()).hexdigest()}
    (AUDIT/'action-independent-summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,sort_keys=True))


if __name__=='__main__':main()
