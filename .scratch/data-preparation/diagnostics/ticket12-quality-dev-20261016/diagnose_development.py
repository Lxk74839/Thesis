"""One authorized 8,320-sort development structural diagnostic, not an eval."""
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import support
from support import ROOT,HERE,canonical,digest,read,load,write,guard,resources,verify_inputs,summary

OUT=ROOT/'data/diagnostics/ticket12-quality-dev-20261016'
P0=ROOT/'.scratch/data-preparation/diagnostics/ticket12-p0-readonly-20261016.py'
P0_DEV=ROOT/'data/evaluation-audit/ticket12-p0-20261016/development-score-audit.jsonl'
CATALOG=ROOT/'data/preference-tasks/grain-A-1.1.15/preference-task-1.0.1/model/catalog.jsonl'
TASKS=ROOT/'data/preference-tasks/grain-A-1.1.15/preference-task-1.0.1/model/tasks.jsonl'
ALPHAS=(.25,.5,.75)
BETAS=(.25,.5,.75)
REORDER_COUNT=0


def rank(parents,b,alpha,q,m):
    global REORDER_COUNT
    if REORDER_COUNT>=8320:
        raise RuntimeError('authorized_reorder_count_exhausted')
    scores=[round(alpha*base+(1-alpha)*quality*match,12) for base,quality,match in zip(b,q,m)]
    order=tuple(sorted(range(len(parents)),key=lambda i:(-scores[i],parents[i].encode())))
    positions=[0]*len(parents)
    for pos,index in enumerate(order):positions[index]=pos
    counts=Counter(scores)
    REORDER_COUNT+=1
    return {'scores':scores,'order':order,'positions':positions,
            'ties_excess':len(parents)-len(counts),
            'tied_candidates':sum(n for n in counts.values() if n>1),
            'tie_pairs':sum(n*(n-1)//2 for n in counts.values()),
            'order_hash':digest(canonical([parents[i] for i in order])),
            'scores_hash':digest(canonical(list(zip(parents,scores))))}


def compare(left,right):
    n=len(left['order'])
    moves=[abs(a-b) for a,b in zip(left['positions'],right['positions'])]
    return {'same_order':left['order']==right['order'],
            'same_top10_order':left['order'][:10]==right['order'][:10],
            'same_top10_set':set(left['order'][:10])==set(right['order'][:10]),
            'top10_intersection':len(set(left['order'][:10])&set(right['order'][:10])),
            'candidate_count':n,'changed_positions':sum(v>0 for v in moves),
            'mean_absolute_rank_shift':math.fsum(moves)/n,'max_absolute_rank_shift':max(moves)}


def main():
    # Import definitions only; P0 main/joins/OOV/S diagnostics are never invoked.
    read(P0,'0b9e65363a664123f0b634bf790c582ea66c113de7b112395a4cc0abb9bf956f')
    spec=importlib.util.spec_from_file_location('previous_diagnostic_definitions',P0)
    previous=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    guard([P0,P0_DEV,CATALOG,TASKS,HERE/'support.py',HERE/'diagnose_development.py',
           OUT/'reference/summary.json']+[OUT/'reference'/('rows-'+v+'.jsonl') for v in ('Q1','Q2')],OUT/'development')
    if (OUT/'development').exists():
        raise RuntimeError('development_diagnostic_already_attempted')
    support.PRIOR_SECONDS=load(OUT/'reference/summary.json')['resources']['cumulative_compute_seconds']
    (OUT/'development').mkdir()
    old_rows=[json.loads(line) for line in read(P0_DEV,'3f05d0aee66a1fecbb9f24a86197e6b3c0115d70169193e1eb42fb854fff3c33').splitlines()]
    expected={r['task_id']:{k:r[k] for k in ('scores_sha256','complete_C_count')} for r in old_rows}
    del old_rows
    if len(expected)!=320:
        raise ValueError('development_account_binding')
    catalog_rows=[json.loads(line) for line in read(CATALOG,'30cf9a8c3cde2f2b7e9d8037b760922a36f478c9fcbcbd0248f279d581ab5339').splitlines()]
    catalog={r['parent_asin']:r for r in catalog_rows}
    reference={v:{r['parent_asin']:r for r in [json.loads(line) for line in read(OUT/'reference'/('rows-'+v+'.jsonl')).splitlines()]} for v in ('Q1','Q2')}
    if any(set(rows)!=set(catalog) for rows in reference.values()):
        raise ValueError('quality_matrix_coverage')
    tasks={}; source_digest=hashlib.sha256(); source_bytes=0; skipped=0
    with TASKS.open('rb') as stream:
        for line in stream:
            source_digest.update(line);source_bytes+=len(line)
            match=re.search(rb'"task_id":"([0-9a-f]{64})"',line)
            if not match:
                raise ValueError('opaque_task_key_missing')
            key=match.group(1).decode('ascii')
            if key not in expected:
                skipped+=1
                continue # do not decode test H, requests, or candidates
            row=json.loads(line)
            if key in tasks:
                raise ValueError('duplicate_development_root')
            tasks[key]={k:row[k] for k in ('task_id','history','candidate_parent_asins')}
            if len(tasks)%40==0:resources()
    if source_digest.hexdigest()!='bb8b3de3d8223515da235ef20877b405edfb937234035967cb8abd8b5cd1cb26' or set(tasks)!=set(expected) or skipped!=1283:
        raise ValueError('accepted_task_container_binding')
    support.READS[TASKS.relative_to(ROOT).as_posix()]={'sha256':source_digest.hexdigest(),'bytes':source_bytes}
    docs={p:previous.grams(catalog[p]['title']+' '+catalog[p]['crop']) for p in sorted(catalog)}
    df=Counter(g for counts in docs.values() for g in counts)
    idf={g:math.log((len(catalog)+1)/(df[g]+1))+1 for g in sorted(df)}
    vectors={p:previous.tfidf(docs[p],idf) for p in sorted(docs)}
    agg=defaultdict(list); directions=defaultdict(Counter); qbars=defaultdict(list)
    run_ties=defaultdict(list); payloads=defaultdict(list); mismatch_q=0; basematches=0
    runs=(OUT/'development/runs.jsonl').open('xb')
    pairs=(OUT/'development/comparisons.jsonl').open('xb')
    bases=(OUT/'development/base-score-cache.jsonl').open('xb')

    def record_comparison(key,left,right,task_id):
        values=compare(left,right)
        agg[key].append(values)
        pairs.write(canonical({'task_id':task_id,'comparison':key,**values})+b'\n')
        return values

    for num,task_id in enumerate(sorted(tasks),1):
        task=tasks[task_id]
        scored=previous.development_score(task,catalog,idf,vectors)
        if digest(canonical(scored['scores']))!=expected[task_id]['scores_sha256'] or len(scored['scores'])!=expected[task_id]['complete_C_count']:
            raise ValueError('prior_base_score_mismatch')
        basematches+=1
        parents=[p for p,b in scored['scores']]; b=[b for p,b in scored['scores']]; n=len(parents)
        base_order=tuple(sorted(range(n),key=lambda i:(-b[i],parents[i].encode())))
        positions=[0]*n
        for pos,i in enumerate(base_order):positions[i]=pos
        base_rank={'order':base_order,'positions':positions}
        bases.write(canonical({'task_id':task_id,'base_scores':scored['scores'],
                               'base_order_sha256':digest(canonical([parents[i] for i in base_order])),
                               'prior_P0_scores_sha256':expected[task_id]['scores_sha256']})+b'\n')
        rankings={}
        for view in ('Q1','Q2'):
            attrs=[reference[view][p] for p in parents]
            if not all(r['eligible'] and r['z']==1 for r in attrs):
                raise ValueError('unexpected_development_eligibility')
            m=[r['x']/100 for r in attrs]
            qs={}
            for bt in BETAS:
                values=[]
                for r in attrs:
                    c=r['C']['numerator']/r['C']['denominator']; t=r['T']['numerator']/r['T']['denominator']; a=r['A']['numerator']/r['A']['denominator']
                    q=r['z']*((1-bt)/2*c+bt*t+(1-bt)/2*a)
                    independent=float(Fraction(**r['q_by_beta_T'][str(bt)]))
                    if abs(q-independent)>1e-12 or abs(r['x']/100-float(Fraction(**r['m'])))>1e-12:
                        mismatch_q+=1
                    values.append(q)
                qs[bt]=values
            qbar=math.fsum(qs[.5])/n # all z=1; denominator is this exact full C
            qbars[view].append(qbar)
            modes=[('full',alpha,bt) for alpha in ALPHAS for bt in BETAS]+[('noq',alpha,None) for alpha in ALPHAS]+[('mean',.5,.5)]
            for mode,alpha,bt in modes:
                q=qs[bt] if mode=='full' else [1.]*n if mode=='noq' else [qbar]*n
                ranked=rank(parents,b,alpha,q,m)
                rankings[(view,mode,alpha,bt)]=ranked
                key=f'{view}/{mode}/alpha={alpha}/betaT={bt}'
                values=record_comparison(key+'/vs_base',ranked,base_rank,task_id)
                run_ties[key].append({k:ranked[k] for k in ('ties_excess','tied_candidates','tie_pairs')})
                runs.write(canonical({'task_id':task_id,'view':view,'mode':mode,'alpha':alpha,'beta_T':bt,
                    'candidate_count':n,'qbar':qbar if mode=='mean' else None,
                    **{k:ranked[k] for k in ('order_hash','scores_hash','ties_excess','tied_candidates','tie_pairs')},
                    'top10':[parents[i] for i in ranked['order'][:10]]})+b'\n')
            for alpha in ALPHAS:
                for bt in BETAS:
                    record_comparison(f'{view}/full_vs_noq/alpha={alpha}/betaT={bt}',rankings[(view,'full',alpha,bt)],rankings[(view,'noq',alpha,None)],task_id)
            record_comparison(view+'/main/full_vs_mean',rankings[(view,'full',.5,.5)],rankings[(view,'mean',.5,.5)],task_id)
            record_comparison(view+'/main/noq_vs_mean',rankings[(view,'noq',.5,None)],rankings[(view,'mean',.5,.5)],task_id)
            fact_rows=[{k:r[k] for k in ('parent_asin','x','z','C','T','A','m','cites')}|{'q_main':qs[.5][i]} for i,r in enumerate(attrs)]
            payloads[view+'/full_C_fact_matrix_bytes'].append(len(canonical(fact_rows)))
            payloads[view+'/b_first_32_fact_page_bytes'].append(len(canonical([fact_rows[i] for i in base_order[:32]])))
        for mode,alpha,bt in [('full',a,t) for a in ALPHAS for t in BETAS]+[('noq',a,None) for a in ALPHAS]+[('mean',.5,.5)]:
            left=rankings[('Q1',mode,alpha,bt)];right=rankings[('Q2',mode,alpha,bt)]
            key=f'Qpair/{mode}/alpha={alpha}/betaT={bt}'
            result=record_comparison(key,left,right,task_id)
            if mode=='noq' and (not result['same_order'] or left['scores']!=right['scores']):
                raise ValueError('noq_changed_under_T_only_swap')
            if mode=='full':
                for i,p in enumerate(parents):
                    one=reference['Q1'][p];two=reference['Q2'][p]
                    dt=float(Fraction(**two['T'])-Fraction(**one['T']))
                    actual=right['scores'][i]-left['scores'][i]
                    expected_delta=(1-alpha)*bt*dt*one['x']/100
                    which='T_up' if dt>0 else 'T_down'
                    direction=directions[key+'/'+which]
                    direction['candidate_references']+=1
                    direction['score_direction_correct']+=int(actual*dt>0)
                    direction['score_delta_formula_mismatch']+=int(abs(actual-expected_delta)>2e-12)
                    change=left['positions'][i]-right['positions'][i]
                    direction['rank_improved' if change>0 else 'rank_worsened' if change<0 else 'rank_unchanged']+=1
        if num%40==0:
            print(f'Development structural reranks: {num}/320 accounts, {REORDER_COUNT}/8320.',flush=True)
            resources()
    for stream in (runs,pairs,bases):stream.close()
    if REORDER_COUNT!=8320 or mismatch_q or basematches!=320:
        raise ValueError('diagnostic_count_or_reference_mismatch')
    summaries={}
    for key,values in agg.items():
        total=sum(v['candidate_count'] for v in values)
        summaries[key]={'paired_runs':len(values),'same_order':sum(v['same_order'] for v in values),
            'same_top10_order':sum(v['same_top10_order'] for v in values),
            'same_top10_set':sum(v['same_top10_set'] for v in values),
            'candidate_references':total,'changed_positions':sum(v['changed_positions'] for v in values),
            'top10_intersection':summary([v['top10_intersection'] for v in values]),
            'account_changed_fraction':summary([v['changed_positions']/v['candidate_count'] for v in values]),
            'account_mean_absolute_rank_shift':summary([v['mean_absolute_rank_shift'] for v in values])}
    verify_inputs()
    write(OUT/'development/summary.json',{'status':'completed_structural_diagnostic_not_recommendation_performance',
          'accounts':320,'test_accounts_decoded_or_scored':0,'test_container_rows_skipped_without_decode':skipped,
          'base_score_hash_matches_prior_P0':basematches,'P0_main_or_target_joins_executed':False,
          'reorders':{'full':5760,'no_quality':1920,'main_mean_quality':640,'total':REORDER_COUNT},
          'alpha1':'references_fixed_base_order_no_fusion_run','reference_q_m_mismatches':mismatch_q,
          'mean_quality_denominator':'same full C with supported stock; all z=1 in this diagnostic',
          'qbar':{key:summary(v) for key,v in qbars.items()},'comparisons':summaries,
          'ties':{key:{metric:summary([v[metric] for v in values]) for metric in ('ties_excess','tied_candidates','tie_pairs')} for key,values in run_ties.items()},
          'Q1_Q2_direction':dict(directions),'payload_bytes':{key:summary(values) for key,values in payloads.items()},
          'input_bindings':support.READS,'resources':resources(),
          'limits':{'model_calls':0,'API_calls':0,'external_paid_calls':0,'recommendation_effectiveness_metrics':0,
                    'production_entry_added':False,'accepted_published':False,'P1':False,'ticket13':False}})
    print('Completed exactly 8,320 structural reranks; no target labels or test performance read.',flush=True)


if __name__=='__main__':
    try:main()
    except Exception as error:
        folder=OUT/'development'
        if folder.exists() and not (folder/'failure.json').exists():
            write(folder/'failure.json',{'status':'failed_preserved','type':type(error).__name__,'reason':str(error),
                                      'reorders_completed_before_failure':REORDER_COUNT})
        raise
