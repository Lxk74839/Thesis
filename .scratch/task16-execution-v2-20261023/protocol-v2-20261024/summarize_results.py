"""Summarize independently scored results and immutable runtime evidence; no API calls."""
import csv
import json
import sys
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
PROJECT = AUDIT.parents[2]
sys.path.insert(0,str(PROJECT))
from macrec_experiment import OUTPUT, read_unit_result, file_ref, store
from task16_control import read, request_rows

plan = read(OUTPUT/'run-plan.json')
start, end = read(AUDIT/'pre-start-status.json'), read(AUDIT/'status-after-stop.json')
info = read(AUDIT/'post-stop-evaluation.json')
report = read(PROJECT/info['report']['path'])
evidence = read(AUDIT/'new-failure-evidence.json')
uncertain = [r for r in evidence if (r.get('provider_diagnostic') or {}).get('http_diagnostic',{}).get('send_state')=='unknown']
unknown_units = {r['unit'] for r in uncertain}
audit_rows = [{'request_id':r['request_id'],'disposition':'unresolved_do_not_resend',
    'recorded_terminal_status':r['terminal_status'],'response':r['response'],
    'reason':'provider http_diagnostic.send_state=unknown; historical terminal is retained unchanged'} for r in uncertain]
uncertain_ref = store(OUTPUT/'protocol-bindings/macrec-agri-v2/uncertain-send-audit.json',audit_rows)
attempts = request_rows(OUTPUT)
features = dict.fromkeys(('ok','failed_protocol','exhausted','unknown_send','interrupted','not_started'),0)
for unit in plan['stages'][2]['units']:
    result = read_unit_result(OUTPUT,unit)
    if unit['id'] in unknown_units:
        state = 'unknown_send'
    elif result is None:
        state = 'interrupted' if any(r['unit']==unit['id'] for r in attempts) else 'not_started'
    elif result['status']=='ok':
        state = 'ok'
    elif 'exhausted' in result.get('reason',''):
        state = 'exhausted'
    else:
        state = 'failed_protocol'
    features[state] += 1
scores = {(r['root_task_id'],r['method']):r for r in report['scores'] if r['scene']=='V00'}
pairs = []
for root in plan['panel']:
    b, i = scores[root,'B0'], scores[root,'I1']
    row = {'root_task_id':root,'B0_status':b['execution_status'],'I1_status':i['execution_status']}
    for key,metric in (('HR10','HR'),('NDCG10','NDCG_P')):
        left,right = b['metrics']['10'][metric],i['metrics']['10'][metric]
        row.update({'B0_'+key:left,'I1_'+key:right,'delta_'+key:right-left if left is not None and right is not None else None})
    pairs.append(row)
(AUDIT/'paired-v00.json').write_text(json.dumps(pairs,indent=2),encoding='utf-8')
with (AUDIT/'paired-v00.csv').open('w',newline='',encoding='utf-8-sig') as stream:
    writer = csv.DictWriter(stream,fieldnames=list(pairs[0]))
    writer.writeheader()
    writer.writerows({k:'NA' if v is None else v for k,v in r.items()} for r in pairs)
methods = {}
for method in ('CB','B0','I1'):
    group = report['summary']['groups'][method+'/V00']
    methods[method] = {'users':group['users'],'states':group['execution_states'],'metrics10':group['metrics']['10']}
usage, prior = end['usage'], start['usage']
summary = {'execution_status':end['status'],'main_comparison_completed':False,'methods':methods,
    'probes':{'real_passed':8,'new_physical_requests':sum(r['phase']=='parameters' and r['namespace']==plan['namespace'] for r in attempts),
        'configuration':{'effort':'medium','quota':'full'}},'features':features,
    'physical_attempts_cumulative':end['calls']['attempts'],'physical_attempts_this_version':end['calls']['attempts']-start['calls']['attempts'],
    'recorded_control_counts':end['calls'],'audited_unknown_send':len(uncertain),'uncertain_audit':uncertain_ref,
    'usage_cumulative':usage,'known_usage_this_version':{k:usage[k]-prior[k] for k in ('input_tokens','output_tokens','cached_input_tokens')},
    'cost':{'known_uncached_input_and_output_basic_CNY':((usage['input_tokens']-usage['cached_input_tokens'])*.045+usage['output_tokens']*.225)/1e6,
        'cached_input_CNY_per_M':None,'extra_multiplier':None,'fixed_fees':None,'actual_invoice_CNY':None,
        'note':'one physical request has unknown usage/send state; subtotal is not a bill'},
    'model_seconds_this_version':end['timing']['model_seconds']-start['timing']['model_seconds'],
    'api_latency_sum_this_version':end['timing']['request_latency_sum_seconds']-start['timing']['request_latency_sum_seconds'],
    'evaluation_report':info['report'],'paired_valid_users':0,'paired_deltas':'all NA',
    'recall_dev320':.6875,'recall_panel16':.75,'later_experiments_executed':False}
(AUDIT/'result-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
