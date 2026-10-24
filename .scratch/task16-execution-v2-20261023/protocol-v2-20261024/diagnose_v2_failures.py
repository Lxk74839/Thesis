"""Read-only post-stop evidence; never sends a request or changes a recorded outcome."""
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT))
from macrec_experiment import OUTPUT, read_unit_result, file_ref
from macrec_protocol import strict_json, check, contract
from task16_control import read, request_rows

plan = read(OUTPUT/'run-plan.json')
attempts = request_rows(OUTPUT)
evidence = []
for unit in plan['stages'][2]['units']:
    result = read_unit_result(OUTPUT,unit)
    if result is None or result['status']=='ok':
        continue
    rows = [r for r in attempts if r['unit']==unit['id'] and r['namespace']==plan['namespace']]
    if not rows:
        continue
    last = max(rows,key=lambda r:r['started'])
    request_path = OUTPUT/'calls'/(last['request_id']+'.request.json')
    response_path = OUTPUT/'calls'/(last['request_id']+'.response.json')
    terminal = read(OUTPUT/'calls'/(last['request_id']+'.terminal.json'))
    wire, response = read(request_path), read(response_path)
    logical = strict_json(wire['input'][1]['content'])
    row = {'unit':unit['id'],'reason':result['reason'],'request_id':last['request_id'],
        'kind':logical['kind'],'role':logical['role'],'request':file_ref(request_path),
        'response':file_ref(response_path),'terminal_status':terminal['status'],
        'response_status':response.get('status'),'usage_known':bool(response.get('usage'))}
    text = ''.join(p['text'] for o in response.get('output',[]) if o.get('type')=='message'
        for p in o.get('content',[]) if p.get('type')=='output_text')
    if text:
        try:
            value = strict_json(text)
            row.update(action=value.get('action'),data_fields=sorted(value.get('data',{})))
            try:
                check(value,wire['text']['format']['schema'])
                row['emitted_schema_accepts'] = True
            except ValueError as exc:
                row.update(emitted_schema_accepts=False,schema_error=str(exc))
            _,_,variants = contract(logical)
            if variants and value.get('action') in variants:
                try:
                    check(value['data'],variants[value['action']],'$.data')
                    row['selected_operation_schema_accepts'] = True
                except ValueError as exc:
                    row.update(selected_operation_schema_accepts=False,operation_error=str(exc))
            ids = value.get('data',{}).get('candidates')
            if isinstance(ids,list):
                n = len(logical['context']['allowed']['candidates'])
                row.update(candidate_count=len(ids),unique_candidate_count=len(set(ids)),
                    duplicate_indices=sorted({i for i in ids if ids.count(i)>1}),
                    out_of_range_indices=[i for i in ids if type(i) is not int or not 0<=i<n],
                    raw_excerpt=text[:140],raw_tail=text[-180:])
            else:
                row['raw_excerpt'] = text[:600]
        except (ValueError,TypeError,KeyError) as exc:
            row['decode_error'] = str(exc)
    else:
        row['provider_diagnostic'] = response.get('diagnostic')
    evidence.append(row)
destination = Path(__file__).with_name('new-failure-evidence.json')
destination.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{k:r.get(k) for k in ('request_id','role','action','reason','candidate_count',
    'unique_candidate_count','data_fields','emitted_schema_accepts','selected_operation_schema_accepts',
    'response_status','provider_diagnostic')} for r in evidence],ensure_ascii=False))
