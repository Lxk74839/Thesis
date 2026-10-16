"""Compare observations against previously persisted independent raw reference.

No import of production scoring/state functions and no allocation/diagnostic answers.
"""
from fractions import Fraction
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
AUDIT=ROOT/'data/quality-fusion-audit/20261016/formal'


def check(ok,code):
    if not ok:raise ValueError(code)


def main():
    refs={}
    for line in (AUDIT/'raw-reference.jsonl').read_bytes().splitlines():
        row=json.loads(line);refs.setdefault(row['snapshot_id'],{})[row['parent_asin']]=row
    runs=[];comparisons=0;citations=0
    for line in (AUDIT/'production-observations.jsonl').read_bytes().splitlines():
        run=json.loads(line);b,result=run['binding'],run['result'];raw=refs[b['snapshot_id']]
        check(set(b['C'])==set(raw) and len(b['C'])==len(raw),'C_closure')
        check(b['base_scores']==[0]+[.5]*(len(raw)-2)+[1],'synthetic_b_only')
        beta=list(map(Fraction,b['beta']));alpha=Fraction(b['alpha']);qualities={}
        for parent in b['C']:
            r=raw[parent];t=Fraction(**r['T']);a=Fraction(r['A']['numerator'],2)
            qualities[parent]=beta[0]+beta[1]*t+beta[2]*a
        mean=sum(qualities.values(),Fraction())/len(raw)
        expected={}
        for parent,base,actual in zip(b['C'],b['base_scores'],result['candidates']):
            r=raw[parent];q=qualities[parent]
            effective=Fraction(1) if b['mode']=='no_quality' else mean if b['mode']=='mean_quality' else q
            m=Fraction(r['x'],100);contribution=effective*m
            score=round(float(alpha*Fraction(base)+(1-alpha)*contribution),12)
            check(actual['parent_asin']==parent and actual['eligible'] and actual['stock_state']=='Supported','identity_state')
            for field in ('x','z','C','A'):check(actual[field]==r[field],'raw_field_'+field)
            for field,value in (('T',Fraction(**r['T'])),('q',q),('m',m),('effective_q',effective),('contribution',contribution),('score',score)):
                check(abs(actual[field]-float(value))<=1e-12,'numeric_'+field);comparisons+=1
            check(Fraction(**actual['T_fraction'])==Fraction(**r['T']),'time_denominator')
            check(actual['citations']['retail_stock']=={'evidence_id':r['stock_evidence_id'],'pointer':'/facts/stock_units'},'citation');citations+=1
            expected[parent]=score
        order=sorted(expected,key=lambda p:(-expected[p],p.encode()))
        check(result['order']==order and result['topK']==order[:10] and set(result['G'])==set(raw),'order_G')
        check(result['mean_quality']['denominator']==len(raw) and abs(result['mean_quality']['value']-float(mean))<1e-12,'mean_denominator')
        runs.append(run)
    check(len(runs)==28,'conditions')
    paired=0
    for first in runs[:14]:
        mate=next(r for r in runs[14:] if (r['binding']['mode'],r['binding']['alpha'],r['binding']['beta'])==
                  (first['binding']['mode'],first['binding']['alpha'],first['binding']['beta']))
        if first['binding']['mode']=='no_quality':
            check(first['result']['order']==mate['result']['order'],'no_q_pair_order')
            check([r['score'] for r in first['result']['candidates']]==[r['score'] for r in mate['result']['candidates']],'no_q_pair_score')
            paired+=1
    summary={'status':'passed','independent_reference':'quality-reference-0.1.0','reranks':len(runs),
        'candidate_rows':sum(len(r['result']['candidates']) for r in runs),'numeric_comparisons':comparisons,
        'citation_checks':citations,'no_quality_paired_conditions':paired,'accounts':0,'model_API_calls':0,
        'production_observations_sha256':hashlib.sha256((AUDIT/'production-observations.jsonl').read_bytes()).hexdigest()}
    (AUDIT/'parity-summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,sort_keys=True))


if __name__=='__main__':main()
