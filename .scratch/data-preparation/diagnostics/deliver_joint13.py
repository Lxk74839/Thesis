"""Ticket13 delivery evidence through public S1/S2; never computes model outcomes."""
import argparse
from datetime import datetime, timezone
import filecmp
import hashlib
import hmac
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = 'joint-task-package-0.1.0'
AUDIT = ROOT/'data/joint-audit'/PACKAGE
CONFIG = ROOT/'config'/f'{PACKAGE}.json'
RECORD = ROOT/'records/joint-tasks'/f'grain-A-1.1.15-{PACKAGE}.json'
REFERENCE = ROOT/'data/joint-reference/grain-A-1.1.15'/PACKAGE/'joint-reference-0.1.0'
PROBE = ROOT/'data/joint-inputs'/PACKAGE/'access-probe.jsonl'
BASE = 'cfec0e5bb3b04ac46ab76e4b2ddb5f7b36e7d1e1'


def wire(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def read(file):
    return json.loads(file.read_bytes())


def save(file, value):
    file.parent.mkdir(parents=True,exist_ok=True)
    with file.open('xb') as stream:stream.write(wire(value)+b'\n')


def info(file):
    with file.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'path':file.relative_to(ROOT).as_posix(),'bytes':file.stat().st_size,'sha256':sha}


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf-8').strip()


def insist(condition, code):
    if not condition:raise ValueError(code)


def upstream_files():
    allowed = {'prepare_data.py','.gitattributes','.scratch/data-preparation/issues/13-joint-task-package.md',
               '.scratch/data-preparation/map.md'}
    files = {ROOT/name for name in git('ls-tree','-r','--name-only',BASE).splitlines() if name not in allowed}
    for directory in ('data','research','manuscript'):
        for file in (ROOT/directory).rglob('*'):
            if file.is_file() and not file.is_symlink() and not file.is_junction():
                relative = file.relative_to(ROOT).parts
                if directory=='data' and relative[1] in ('joint-audit','joint-inputs','joint-tasks','joint-reference'):
                    continue
                files.add(file)
    return sorted(files,key=lambda p:p.relative_to(ROOT).as_posix())


def protect(before):
    file = AUDIT/'upstream-before.json'
    if before:
        values = [info(p) for p in upstream_files()]
        save(file,{'files':values,'count':len(values),'bytes':sum(v['bytes'] for v in values)})
        return {'status':'protected_baseline_saved','files':len(values),'bytes':sum(v['bytes'] for v in values)}
    baseline = read(file)
    changed = [v['path'] for v in baseline['files'] if info(ROOT/v['path'])!=v]
    current = {p.relative_to(ROOT).as_posix() for p in upstream_files()}
    insist(current=={v['path'] for v in baseline['files']},'upstream_file_set_changed')
    prefix = (AUDIT/'gitattributes-prefix.bin').read_bytes()
    prefix_ok = (ROOT/'.gitattributes').read_bytes().startswith(prefix)
    result = {'status':'passed' if not changed and prefix_ok else 'failed','changed':changed,
              'files':baseline['count'],'bytes':baseline['bytes'],'gitattributes_original_prefix_unchanged':prefix_ok}
    save(AUDIT/'upstream-after.json',result)
    insist(result['status']=='passed','upstream_changed')
    return result


def make_probes():
    cfg = read(CONFIG)
    key = (ROOT/cfg['inputs']['identity_key']['path']).read_bytes()
    insist(len(key)==32,'identity_key_length')
    ids = []
    with (ROOT/cfg['inputs']['preference_tasks']['path']).open('rb') as stream:
        for line in stream:ids.append(json.loads(line)['task_id'])
    count = 0
    PROBE.parent.mkdir(parents=True,exist_ok=True)
    with PROBE.open('xb') as stream:
        def write(session, operation, arguments):
            nonlocal count
            stream.write(wire({'session_task_id':session,'operation':operation,'arguments':arguments})+b'\n')
            count += 1
        for i,root in enumerate(ids):
            for view in cfg['views']:
                handle = hmac.new(key,b'Thesis:joint-session-0.1.0\0'+wire([root,view['material_version'],
                    view['snapshot_id'],view['request_profile_id']]),hashlib.sha256).hexdigest()
                write(handle,'model_request',{})
            write(root,'candidate_page',{'order':'parent','cursor':None})
            for resource in (cfg['inputs']['preference_evaluation']['path'],'data/private-nonexistent-target.jsonl'):
                write(root,'read_resource',{'path':resource})
            write(root,'invoke_tool',{'name':'private_evaluator','role':'evaluator'})
            write(root,'model_request',{'root_task_id':ids[(i+1)%len(ids)]})
            write(root,'candidate_page',{'order':'parent','cursor':'forged-cross-session-cursor'})
    result = {'status':'prepared_private_probes','roots':len(ids),'probes':count,'model_API_calls':0,'component':info(PROBE)}
    save(AUDIT/'probe-plan.json',result)
    return result


def command(arguments, log):
    result = subprocess.run([sys.executable,*arguments],cwd=ROOT,capture_output=True)
    with (AUDIT/log).open('xb') as stream:stream.write(result.stdout+result.stderr)
    insist(result.returncode==0,'public_cli_failed_'+log)
    return json.loads(result.stdout)


def reproduce():
    original = read(RECORD)
    original_record = RECORD.read_bytes(),RECORD.stat().st_mtime_ns
    old_times = {name:(ROOT/ref['path']).stat().st_mtime_ns for name,ref in original['components'].items()}
    fresh_root = ROOT/'.tmp'/('ticket13-reproduction-'+git('rev-parse','--short','HEAD'))
    insist(not fresh_root.exists(),'reproduction_root_not_fresh')
    args = ['prepare_data.py','--stage','joint_tasks','--joint-config',str(CONFIG),'--access-probe',str(PROBE),'--output-root']
    fresh = command([*args,str(fresh_root)],'fresh-generation.txt')
    insist(set(fresh['components'])==set(original['components']),'reproduction_component_set')
    comparisons = []
    for name,ref in original['components'].items():
        new_ref = fresh['components'][name]
        a,b = ROOT/ref['path'],fresh_root/new_ref['path']
        insist(filecmp.cmp(a,b,shallow=False),'reproduction_bytes_'+name)
        comparisons.append({'component':name,'bytes':a.stat().st_size,'sha256':ref['sha256']})
    fresh_record = fresh_root/'records/joint-tasks'/RECORD.name
    fresh_audit = ROOT/'data/joint-reference/grain-A-1.1.15'/PACKAGE/'reproduction-reference-0.1.0'
    command(['.scratch/data-preparation/diagnostics/verify_joint13.py','--record',str(fresh_record),
             '--audit-root',str(fresh_audit)],'fresh-reference.txt')
    stable_reference = sorted(p.name for p in REFERENCE.iterdir() if p.is_file() and p.name!='check.json')
    insist(stable_reference==sorted(p.name for p in fresh_audit.iterdir() if p.is_file() and p.name!='check.json'),
            'reproduction_reference_set')
    for name in stable_reference:
        insist(filecmp.cmp(REFERENCE/name,fresh_audit/name,shallow=False),'reproduction_reference_bytes_'+name)
    reused = command([*args,str(ROOT)],'consistent-reuse.txt')
    insist(reused==original and (RECORD.read_bytes(),RECORD.stat().st_mtime_ns)==original_record,'reuse_record_changed')
    insist(all((ROOT/ref['path']).stat().st_mtime_ns==old_times[name] for name,ref in original['components'].items()),
            'reuse_component_mtime_changed')
    result = {'status':'passed','stable_components':comparisons,'stable_component_count':len(comparisons),
              'stable_component_bytes':sum(v['bytes'] for v in comparisons),'stable_reference_files':stable_reference,
              'fresh_record':info(fresh_record),'fresh_reference_check':info(fresh_audit/'check.json'),
              'original_prepared_unchanged':True,'reuse_mtime_unchanged':True}
    save(AUDIT/'reproduction-and-reuse.json',result)
    return {k:v for k,v in result.items() if k!='stable_components'}


def accept():
    record = read(RECORD)
    reference_check = read(REFERENCE/'check.json')
    reproduction = read(AUDIT/'reproduction-and-reuse.json')
    protection = read(AUDIT/'upstream-after.json')
    reviews_path = ROOT/'.scratch/data-preparation/verification/ticket13-review-summary.json'
    reviews = read(reviews_path)
    insist(reference_check['status']=='passed_joint_association_only' and reproduction['status']==protection['status']=='passed',
            'delivery_gates_not_passed')
    insist(reviews['base']==BASE and all(reviews[axis]['blockers']==0 for axis in ('standards','spec')),'review_blockers')
    for axis in ('standards','spec'):
        insist(info(ROOT/reviews[axis]['report']['path'])==reviews[axis]['report'],'review_report_changed')
    for name,sha in record['producer_sha256'].items():
        reviewed = subprocess.check_output(['git','show',reviews['candidate']+':'+name],cwd=ROOT)
        insist(hashlib.sha256(reviewed).hexdigest()==sha==info(ROOT/name)['sha256'],'reviewed_producer_mismatch')
    insist(reference_check['record']['sha256']==info(RECORD)['sha256'],'reference_prepared_mismatch')
    ledger = (AUDIT/'resource-ledger.jsonl').read_bytes()
    resource_snapshot = AUDIT/'resources-before-acceptance.jsonl'
    with resource_snapshot.open('xb') as stream:stream.write(ledger)
    usage = [json.loads(line) for line in ledger.splitlines()]
    insist(sum(v['seconds'] for v in usage)<1800 and all(v['job_peak_commit_bytes']+v.get('guard_reserve_bytes',0)<=4*1024**3 for v in usage),
            'resource_limit_not_met')
    acceptance = {'schema_version':'joint-acceptance-0.1.0','status':'accepted_joint_preparation_component_only',
        'accepted_at_utc':datetime.now(timezone.utc).isoformat(),'generation_record':info(RECORD),
        'producer_sha256':record['producer_sha256'],'components':record['components'],
        'independent_reference':{'check':info(REFERENCE/'check.json'),'components':reference_check['components'],
                                  'program':reference_check['program']},
        'validation':{'reproduction':info(AUDIT/'reproduction-and-reuse.json'),
                      'upstream_protection':info(AUDIT/'upstream-after.json'),'reviews':info(reviews_path)},
        'counts':record['counts'],'nQ':reference_check['nQ'],'nQ_dev':reference_check['nQ_dev'],
        'n8_from_P0':reference_check['n8_from_P0'],'P0_recomputed':False,
        'planning_counts':{'Q':reference_check['planned_n_975_Q'],'original8':reference_check['planned_n_975_8']},
        'sample_sufficiency':'not_determined','runtime_adapter_status':'not_accepted','execution_budget_status':'unvalidated',
        'formal_package_status':'not_released','model_execution_status':'not_run','ledger_deployment_status':'not_deployed',
        'resources_before_finalization':info(resource_snapshot),'finalization_resource_account':'shared_resource_ledger_appends_after_this_process',
        'limitations':['data_preparation_only','not_independent_people_proof','not_formal_joint_execution','not_ticket14_or_15_acceptance']}
    output = RECORD.with_name(RECORD.stem+'-acceptance.json')
    save(output,acceptance)
    return {'status':acceptance['status'],'acceptance':info(output),'nQ':acceptance['nQ'],'n8_from_P0':acceptance['n8_from_P0']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase',choices=['protect-before','probes','reproduce','protect-after','accept'])
    args=parser.parse_args()
    try:
        actions={'protect-before':lambda:protect(True),'probes':make_probes,'reproduce':reproduce,
                 'protect-after':lambda:protect(False),'accept':accept}
        print(json.dumps(actions[args.phase](),sort_keys=True,ensure_ascii=False))
        return 0
    except (OSError,ValueError,KeyError,TypeError):
        error=sys.exception()
        print(json.dumps({'status':'delivery_incomplete','error':str(error) if isinstance(error,ValueError) else type(error).__name__}))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
