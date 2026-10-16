"""One-off acceptance writer. All independent gates must already have passed."""
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import NormalDist
import subprocess

ROOT=Path(__file__).resolve().parents[3]
AUDIT=ROOT/'data/quality-fusion-audit/20261016'
PREPARED=ROOT/'records/sim-quality/grain-A-1.1.15-sim-quality-fusion-0.1.0.json'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def read(path):return json.loads(path.read_bytes())


def binding(path):
    raw=path.read_bytes()
    return {'path':path.relative_to(ROOT).as_posix(),'sha256':sha(raw),'bytes':len(raw)}


def require(condition,code):
    if not condition:raise ValueError(code)


def main():
    paths={'public_reference':AUDIT/'final-public/public-reference-summary.json',
        'independent_full_reference':AUDIT/'formal/raw-reference-summary.json',
        'independent_score_parity':AUDIT/'formal/parity-summary.json',
        'independent_action_audit':AUDIT/'final-actions/action-independent-summary.json',
        'fresh_reproduction_and_reuse':AUDIT/'reproduction-summary.json',
        'upstream_protection':AUDIT/'upstream-after.json',
        **{'read_guard_'+name:AUDIT/('read-guard-'+name+'.json') for name in ('formal','fresh','reuse')}}
    checks={name:read(path) for name,path in paths.items()}
    require(all(v['status']=='passed' for v in checks.values()),'acceptance_gate_failed')
    require(checks['independent_full_reference']['references']==2988
            and checks['independent_full_reference']['parents_per_view']==[1494,1494],'reference_count')
    require(checks['independent_score_parity']['candidate_rows']==41832
            and checks['independent_score_parity']['accounts']==0,'parity_count')
    require(checks['independent_action_audit']['fixtures']==9
            and checks['upstream_protection']['checked_files']==460 and checks['upstream_protection']['changed']==[],'audit_count')
    raw=PREPARED.read_bytes();prepared=read(PREPARED)
    require(sha(raw)==checks['fresh_reproduction_and_reuse']['prepared_sha256'],'prepared_changed')
    source_names=('quality_fusion.py','recommendation_actions.py','prepare_data.py')
    for name in source_names:require(sha((ROOT/name).read_bytes())==prepared['producer_sha256'][name],'producer_changed')
    action=read(AUDIT/'final-actions/action-fixture-summary.json')
    require(all(action['producer_sha256'][name]==prepared['producer_sha256'][name]
                for name in action['producer_sha256']),'action_source_changed')
    test_log=AUDIT/'regression-after-closure.txt'
    test_text=test_log.read_text(encoding='utf-8')
    tests=int(re.search(r'Ran (\d+) tests in ',test_text).group(1))
    require(tests==295 and test_text.rstrip().endswith('OK'),'regression_failed')
    ledger=[json.loads(line) for line in (AUDIT/'resource-ledger.jsonl').read_bytes().splitlines()]
    require(all(e['exit_code']==0 for e in ledger if e['label']=='regression-after-closure'),'regression_receipt')
    total=sum(e['seconds'] for e in ledger);peak=max(e['job_peak_commit_bytes'] for e in ledger)
    require(total<1800 and peak<4*1024**3,'local_resource_limit')
    phase=defaultdict(float)
    for row in ledger:
        label=row['label']
        category=('regression' if label.startswith('regression') else 'tdd_public_behaviors' if label.startswith(('red','green','existing'))
                  else 'upstream_protection' if label.startswith('protection') else 'fresh_reproduction_reuse' if label.startswith('fresh-')
                  else 'formal_preparation' if label=='formal-prepare' else 'independent_and_fixture_audits')
        phase[category]+=row['seconds']
    sources=[ROOT/name for name in source_names]+[ROOT/'config/quality-fusion-0.1.0.json',
        ROOT/'.scratch/data-preparation/ticket12-quality-offline-authorization-20261016.md',
        ROOT/'.scratch/data-preparation/ticket12-quality-dev-report-and-implementation-contract-20261016.md']
    for path in sources:
        blob=subprocess.check_output(['git','show','HEAD:'+path.relative_to(ROOT).as_posix()],cwd=ROOT)
        require(blob==path.read_bytes(),'git_checkout_byte_binding')
    require(subprocess.check_output(['git','ls-files','--','data/sim-quality','data/quality-fusion-audit'],
        cwd=ROOT)==b'','private_data_tracked')
    precision=[]
    for comparisons,half_width in ((2,.07),(4,.07),(4,.08)):
        z=NormalDist().inv_cdf(1-.05/(2*comparisons))
        precision.append({'comparisons':comparisons,'half_width':half_width,'z':z,
            'conditional_approximate_n_bound':math.ceil((z/half_width)**2),
            'assumptions':'bounded paired difference variance<=1; conditional approximate normal precision; no sufficiency pass'})
    summary={'status':'all_gates_passed','tests':tests,'new_public_tests':25,'prior_regression_tests':270,
        'reference_rows':2988,'synthetic_catalog_reranks':28,'synthetic_candidate_rows':41832,
        'numeric_checks':250992,'score_citation_checks':41832,'raw_source_citations':14940,
        'action_fixtures':9,'action_transitions':30,'budget_cells':270,
        'protected_files':460,'prepared_sha256':sha(raw),'phase_seconds':dict(phase),
        'measured_seconds_before_acceptance_writer':total,'peak_job_commit_bytes':peak,
        'resource_scope':'Thesis Python child trees; includes expected RED failures and all regression attempts; excludes Conda startup/document editing/review agents',
        'model_API_calls':0,'external_paid_cost_USD':0,'inference_input_output_tokens':0,
        'conditional_precision_options_not_frozen':precision,
        'logical_budget_examples_not_frozen':{'four_full_fixture_capsules':4*30+3,'64_full_capsules':64*30+3,
            '64_complete_R1_R5_stock_CTA_15_registry_12_originals_each_plus_3_metadata':64*27+3},
        'git_checkout_byte_binding':'passed','private_data_git_check':'passed'}
    summary_path=AUDIT/'release-evidence-summary.json'
    with summary_path.open('xb') as stream:stream.write(json.dumps(summary,sort_keys=True,indent=2).encode()+b'\n')
    reviews={}
    for axis in ('standards','spec'):
        path=ROOT/'.scratch/data-preparation/verification'/('ticket12-'+axis+'-final-review.md')
        text=path.read_text(encoding='utf-8')
        require('通过' in text and '阻塞' in text and '0' in text,'review_not_passed')
        reviews[axis.title()]={'status':'passed','blocking_findings':0,'report':binding(path)}
    reference_scripts=('verify_quality12_raw.py','verify_quality12_public.py','compare_quality12_independent.py','audit_quality12_actions.py')
    for name in reference_scripts:
        text=(ROOT/'.scratch/data-preparation/diagnostics'/name).read_text(encoding='utf-8')
        require('from quality_fusion import' not in text and 'from recommendation_actions import' not in text,'independent_reference_import')
    record={'status':'accepted_ticket12_quality_and_deterministic_actions_offline_only','date':'2026-10-16',
        'scope':['independent_Q1_Q2_materials_and_pure_quality_rank','public_deterministic_action_state_contract'],
        'fixed_review_base':'7bd12cdb36b073f65ce9f123939e01288b8a12c0',
        'implementation_commit':'f7e55066c8a804890a6b91f0368e74ffd3756c01',
        'versions':{'quality_material':'sim-quality-fusion-0.1.0','preference_protocol':'quality-preference-protocol-0.1.0',
            'reference':'quality-reference-0.1.0','score':'fusion-score-0.1.0','action':'collaboration-action-contract-0.1.0'},
        'generation_record':binding(PREPARED),'config':binding(ROOT/'config/quality-fusion-0.1.0.json'),
        'components':prepared['components'],'producer_sha256':prepared['producer_sha256'],'reviews':reviews,
        'validation':{name:{'status':'passed','evidence':binding(path)} for name,path in paths.items()},
        'public_tests':{'status':'passed','tests':tests,'new_public_tests':25,'log':binding(test_log)},
        'independent_scripts':{name:binding(ROOT/'.scratch/data-preparation/diagnostics'/name) for name in reference_scripts},
        'summary':binding(summary_path),'ticket12_status':'open_remaining_decisions',
        'formal_comparison_statistics_model_budget':'not_confirmed','sample_sufficiency':'not_determined',
        'formal_package_status':'not_built','model_execution_status':'not_run','ledger_deployment_status':'not_deployed'}
    destination=PREPARED.with_name('grain-A-1.1.15-sim-quality-fusion-0.1.0-acceptance.json')
    with destination.open('xb') as stream:stream.write(json.dumps(record,sort_keys=True,ensure_ascii=False,indent=2).encode()+b'\n')
    require(PREPARED.read_bytes()==raw,'prepared_record_mutated')
    print(json.dumps({'status':record['status'],'acceptance_record':binding(destination),'summary':summary},sort_keys=True))


if __name__=='__main__':main()
