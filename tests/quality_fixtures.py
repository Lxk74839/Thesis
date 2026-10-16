"""Public four-product baseline via the already accepted normal public CLI."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]


def wire(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def put(path, value, rows=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b''.join(wire(row)+b'\n' for row in value) if rows else wire(value)+b'\n')
    return path


def binding(path):
    return {'path':path.relative_to(PROJECT).as_posix(), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def normal_fixture(root):
    cfg = json.loads((PROJECT/'config/sim-normal-1.0.0.json').read_bytes())
    catalog = put(root/'inputs/catalog.jsonl', [{'parent_asin':p,'crop':'rice','status':'included'}
                  for p in ('DEMO-A','DEMO-B','DEMO-HI','DEMO-LO')], rows=True)
    record = put(root/'inputs/catalog-record.json', {'stage':'catalog','status':'catalog_complete',
        'scope_version':'grain-A-1.1.15','counts':{'included':4},
        'catalog_path':catalog.relative_to(PROJECT).as_posix(),'catalog_sha256':binding(catalog)['sha256']})
    cfg['catalog_binding'].update(record_path=binding(record)['path'],record_sha256=binding(record)['sha256'],
        component_sha256=binding(catalog)['sha256'],expected_parent_count=4)
    config = put(root/'inputs/normal-config.json',cfg)
    result = subprocess.run([sys.executable,str(PROJECT/'prepare_data.py'),'--stage','sim_normal',
        '--catalog-record',str(record),'--sim-config',str(config),'--output-root',str(root/'normal')],
        cwd=PROJECT,capture_output=True,text=True,encoding='utf-8')
    if result.returncode:
        raise AssertionError(result.stdout+result.stderr)
    normal = json.loads(result.stdout)
    normal_record = root/'normal/records/sim/grain-A-1.1.15-sim-normal-1.0.0.json'
    acceptance = json.loads((PROJECT/'records/sim/grain-A-1.1.15-sim-normal-1.0.0-acceptance.json').read_bytes())
    acceptance['generation_record'] = binding(normal_record)
    acceptance['components'] = normal['components']
    acceptance['approved_contract']['config'] = binding(config)
    acceptance['independent_reference'].update(audited_batches=4,
        state_counts={'Supported':4,'Refuted':0,'Pending':0,'Conflict':0})
    accepted = put(root/'inputs/normal-acceptance.json',acceptance)
    quality = json.loads((PROJECT/'config/quality-fusion-0.1.0.json').read_bytes())
    quality['normal_binding'] = {key:binding(path) for key,path in [('record',normal_record),('acceptance',accepted),('config',config)]}
    return normal_record, put(root/'inputs/quality-config.json',quality), normal


def scoring_fixture(root):
    """Hand-set HI/A/B/LO stock/time values from the approved public example."""
    normal_record, config, normal = normal_fixture(root)
    rows = {name:[json.loads(line) for line in (root/'normal'/info['path']).read_bytes().splitlines()]
            for name,info in normal['components'].items()}
    stock={'DEMO-HI':25,'DEMO-A':75,'DEMO-B':100,'DEMO-LO':25}
    for row in rows['materials.jsonl']:
        if row['kind']=='retail_status':
            row['facts']['stock_units']=stock[row['parent_asin']]
            row['valid_to_ms']=1791590400000 if row['parent_asin']=='DEMO-B' else 1791428400000
    objects={row['sim_batch_id']:row for row in rows['batches.jsonl']}
    objects.update({row['event_id']:row for row in rows['events.jsonl']})
    objects.update({row['evidence_id']:row for row in rows['materials.jsonl']})
    for reg in rows['registrations.jsonl']:
        reg['content_sha256']=hashlib.sha256(wire(objects[reg['target_id']])).hexdigest()
    rules=json.loads(config.read_bytes())['rules']
    snap={'schema_version':'quality-snapshot-0.1.0','source':'SIM','protocol_version':'quality-preference-protocol-0.1.0',
          'verify_at_ms':1791417600000,'sealed_at_ms':1791375000000,'cutoff_sequence':60,
          'policy_id':rows['policy.json'][0]['policy_id'],'read_principal_id':'SIM-VERIFIER',
          'rules':rules,'contract_sha256':hashlib.sha256(wire(rules)).hexdigest(),
          'scope_sha256':{p:hashlib.sha256(wire([r for r in rows['registrations.jsonl'] if r['parent_asin']==p])).hexdigest() for p in stock},
          'components':{'policy.json':{'sha256':hashlib.sha256(wire(rows['policy.json'][0])+b'\n').hexdigest()},
                        'actions.jsonl':{'sha256':hashlib.sha256(b'').hexdigest(),'bytes':0,'records':0}}}
    snap['snapshot_id']='qf_'+hashlib.sha256(b'Thesis-quality-fusion:snapshot\0'+wire(snap)).hexdigest()
    acquired={'snapshot':snap,'policy_bytes':wire(rows['policy.json'][0])+b'\n','actions_bytes':b'',
              'candidates':{p:{'registrations':[r for r in rows['registrations.jsonl'] if r['parent_asin']==p],
                    'originals':{key:wire(row) for key,row in objects.items() if row['parent_asin']==p}} for p in stock}}
    parents=['DEMO-HI','DEMO-A','DEMO-B','DEMO-LO'];scores=[1,.9,.6,0]
    bind={'schema_version':'fusion-binding-0.1.0','task_id':'DEMO-ROOT','C':parents,
          'C_sha256':hashlib.sha256(wire(parents)).hexdigest(),'H_sha256':hashlib.sha256(b'PUBLIC-H').hexdigest(),
          'base_scores':scores,'base_score_version':'public-worked-example',
          'base_score_sha256':hashlib.sha256(wire(list(zip(parents,scores)))).hexdigest(),
          'snapshot_id':snap['snapshot_id'],'verify_at_ms':snap['verify_at_ms'],'principal_id':'SIM-VERIFIER',
          'contract_sha256':snap['contract_sha256'],'K':10,'alpha':.5,'beta':[.25,.5,.25],'mode':'full',
          'preference':{'source':'experiment_design','dimensions':['retail_stock'],'weights':{'retail_stock':1}}}
    return bind, acquired


def reseal(binding, acquired, update_original_hashes=True):
    """Public fixture changes are separately sealed; not a production oracle."""
    snap=acquired['snapshot']
    snap['components']['policy.json']['sha256']=hashlib.sha256(acquired['policy_bytes']).hexdigest()
    for parent,pack in acquired['candidates'].items():
        if update_original_hashes:
            for reg in pack['registrations']:
                if reg['target_id'] in pack['originals']:
                    reg['content_sha256']=hashlib.sha256(pack['originals'][reg['target_id']]).hexdigest()
        snap['scope_sha256'][parent]=hashlib.sha256(wire(pack['registrations'])).hexdigest()
    snap.pop('snapshot_id')
    snap['snapshot_id']='qf_'+hashlib.sha256(b'Thesis-quality-fusion:snapshot\0'+wire(snap)).hexdigest()
    binding['snapshot_id']=snap['snapshot_id']
