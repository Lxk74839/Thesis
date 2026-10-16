"""Once-only target-blind generation. Reads no users, H, targets, b or models."""
from collections import Counter
import json
from pathlib import Path
import support
from support import ROOT, HERE, canonical, digest, read, load, write, guard, resources, verify_inputs

OUT = ROOT/'data/diagnostics/ticket12-quality-dev-20261016'
NORMAL = ROOT/'data/sim/grain-A-1.1.15/sim-normal-1.0.0'
CATALOG = ROOT/'data/preference-tasks/grain-A-1.1.15/preference-task-1.0.1/model/catalog.jsonl'
RECORD = ROOT/'records/sim/grain-A-1.1.15-sim-normal-1.0.0.json'
ACCEPT = ROOT/'records/sim/grain-A-1.1.15-sim-normal-1.0.0-acceptance.json'
NAMES = ('batches.jsonl','events.jsonl','materials.jsonl','registrations.jsonl','policy.json')
TAG = b'Thesis-ticket12-quality-snapshot-v1\0'


def main():
    guard([RECORD, ACCEPT, CATALOG, HERE/'support.py', HERE/'generate_views.py',
           OUT/'public-example/generation-gate.json']+[NORMAL/n for n in NAMES+('snapshot.json',)], OUT/'generated')
    if (OUT/'generated').exists():
        raise RuntimeError('generation_already_attempted')
    passed = load(OUT/'public-example/generation-gate.json')
    if passed['status'] != 'passed':
        raise RuntimeError('public_example_not_passed')
    support.PRIOR_SECONDS = passed['resources']['cumulative_compute_seconds']
    (OUT/'generated').mkdir()
    record = load(RECORD,'8694d35a342f6c198bc1db1a0d2ee4b5cad8e09a17e13aed72dacd23eb907715')
    acceptance = load(ACCEPT,'831c951af0e09f0d041354579d0fa3713cb3deeb52c8328fe8574e347a0a338c')
    if 'record_sha256' in acceptance and acceptance['record_sha256'] != digest(RECORD.read_bytes()):
        raise ValueError('accepted_normal_binding')
    catalog = [json.loads(line) for line in read(CATALOG, '30cf9a8c3cde2f2b7e9d8037b760922a36f478c9fcbcbd0248f279d581ab5339').splitlines()]
    parents = [r['parent_asin'] for r in catalog]
    if len(parents) != len(set(parents)) or len(parents) != 1494:
        raise ValueError('catalog_count')
    raw = {name:read(NORMAL/name, record['components'][name]['sha256']) for name in NAMES}
    normal_snap = load(NORMAL/'snapshot.json', record['components']['snapshot.json']['sha256'])
    ordered = sorted(parents, key=lambda p:(digest(b'Thesis-ticket12-quality-v1\0' + b'20261016\0' + p.encode('utf-8')),p.encode('utf-8')))
    combinations = [(x,t) for x in (25,50,75,100) for t in (1,4)] # T numerator over 5
    assignment = {p:combinations[rank%8] for rank,p in enumerate(ordered)}
    baseline_materials = [json.loads(line) for line in raw['materials.jsonl'].splitlines()]
    baseline_regs = [json.loads(line) for line in raw['registrations.jsonl'].splitlines()]
    actual_parents = {r['parent_asin'] for r in baseline_materials}
    if actual_parents != set(parents):
        raise ValueError('normal_catalog_binding')
    views = {}
    for view in ('Q1','Q2'):
        folder = OUT/'generated'/view
        folder.mkdir()
        materials = json.loads(json.dumps(baseline_materials))
        changed = {}
        for row in materials:
            if row['kind'] != 'retail_status':
                continue
            stock,t_num = assignment[row['parent_asin']]
            if view == 'Q2':
                t_num = 5-t_num
            row['facts']['stock_units'] = stock
            span = normal_snap['verify_at_ms']-row['valid_from_ms']
            remain_numerator = span*t_num
            if remain_numerator % (5-t_num):
                raise ValueError('noninteger_expiration')
            row['valid_to_ms'] = normal_snap['verify_at_ms'] + remain_numerator//(5-t_num)
            changed[row['evidence_id']] = digest(canonical(row))
        regs = [dict(row) for row in baseline_regs]
        for row in regs:
            if row['target_id'] in changed:
                row['content_sha256'] = changed[row['target_id']]
        files = {name:raw[name] for name in ('batches.jsonl','events.jsonl','policy.json')}
        files['materials.jsonl'] = b''.join(canonical(r)+b'\n' for r in materials)
        files['registrations.jsonl'] = b''.join(canonical(r)+b'\n' for r in regs)
        files['actions.jsonl'] = b''
        components = {}
        for name,value in files.items():
            with (folder/name).open('xb') as stream:
                stream.write(value)
            components[name] = {'bytes':len(value),'records':len(value.splitlines()),'sha256':digest(value)}
        snap = {'schema_version':'quality-diagnostic-snapshot-0.1.0','status':'research_only_not_accepted',
                'source':'SIM','parent_snapshot_id':normal_snap['snapshot_id'],
                'catalog_version':normal_snap['catalog_version'],'protocol_version':normal_snap['protocol_version'],
                'verify_at_ms':normal_snap['verify_at_ms'],'sealed_at_ms':normal_snap['sealed_at_ms'],
                'cutoff_sequence':normal_snap['cutoff_sequence'],'policy_id':normal_snap['policy_id'],
                'read_principal_id':'SIM-VERIFIER','components':components}
        snap['snapshot_id'] = 'qd_' + digest(TAG+canonical(snap))
        write(folder/'snapshot.json',snap)
        views[view] = {'snapshot_id':snap['snapshot_id'],'changed_retail_originals':len(changed),
                       'bytes':sum(c['bytes'] for c in components.values())+(folder/'snapshot.json').stat().st_size}
        resources()
    with (OUT/'generated/allocation-private.jsonl').open('xb') as stream:
        for rank,parent in enumerate(ordered):
            x,t=assignment[parent]
            stream.write(canonical({'parent_asin':parent,'sha256_rank':rank,'assignment_digest':digest(b'Thesis-ticket12-quality-v1\0' + b'20261016\0'+parent.encode()),'stock_units':x,'Q1_T_numerator_over_5':t,'Q2_T_numerator_over_5':5-t})+b'\n')
    verify_inputs()
    write(OUT/'generated/receipt.json',{'status':'generated_research_only','views':views,
          'assignment_rule':'SHA256(domain,NUL,seed,NUL,parent), digest then UTF8 parent; rank mod8; x asc then T asc',
          'combination_counts':dict(Counter(f'{x}:{t}/5' for x,t in assignment.values())),
          'generation_reads':support.READS,'forbidden_user_history_target_score_model_reads':0,
          'resources':resources()})
    print('Generated two isolated quality views; no user/history/target/b/model input.',flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        folder=OUT/'generated'
        if folder.exists() and not (folder/'failure.json').exists():
            write(folder/'failure.json',{'status':'failed_preserved','type':type(error).__name__,'reason':str(error)})
        raise
