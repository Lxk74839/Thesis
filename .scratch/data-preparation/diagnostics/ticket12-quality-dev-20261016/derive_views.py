"""Once-only independent reference of the generated normal-derived views."""
from collections import Counter
from fractions import Fraction
import support
from support import ROOT,HERE,canonical,load,write,guard,resources,verify_inputs
from reference import derive, FILES

OUT=ROOT/'data/diagnostics/ticket12-quality-dev-20261016'


def main():
    allowed=[OUT/'generated/receipt.json',HERE/'support.py',HERE/'reference.py',HERE/'derive_views.py']
    allowed += [OUT/'generated'/v/n for v in ('Q1','Q2') for n in FILES+('snapshot.json',)]
    guard(allowed,OUT/'reference')
    if (OUT/'reference').exists():
        raise RuntimeError('reference_already_attempted')
    support.PRIOR_SECONDS=load(OUT/'generated/receipt.json')['resources']['cumulative_compute_seconds']
    (OUT/'reference').mkdir()
    rows_by_view={}; summaries={}
    for view in ('Q1','Q2'):
        rows=derive(OUT/'generated'/view)
        rows_by_view[view]={r['parent_asin']:r for r in rows}
        if len(rows)!=1494 or not all(r['eligible'] and r['z']==1 and r['graph_complete'] for r in rows):
            raise ValueError('derived_eligibility_or_stock_support_failure')
        with (OUT/'reference'/('rows-'+view+'.jsonl')).open('xb') as stream:
            for row in rows:stream.write(canonical(row)+b'\n')
        exact=lambda r,key:str(Fraction(**r[key]))
        summaries[view]={'objects':len(rows),'eligible':sum(r['eligible'] for r in rows),
            'stock_state_counts':dict(Counter(r['stock_state'] for r in rows)),
            'stock_counts':dict(Counter(str(r['x']) for r in rows)),
            'm_counts':dict(Counter(exact(r,'m') for r in rows)),
            'C_counts':dict(Counter(exact(r,'C') for r in rows)),
            'T_counts':dict(Counter(exact(r,'T') for r in rows)),
            'A_counts':dict(Counter(exact(r,'A') for r in rows)),
            'C_denominator_counts':dict(Counter(str(r['C']['denominator']) for r in rows)),
            'A_denominator_counts':dict(Counter(str(r['A']['denominator']) for r in rows)),
            'q_counts_by_beta_T':{b:dict(Counter(str(Fraction(**r['q_by_beta_T'][b])) for r in rows)) for b in ('0.25','0.5','0.75')},
            'citations':sum(len(r['cites']) for r in rows),'citation_admissibility_errors':sum(bool(c['admissibility_reasons']) for r in rows for c in r['cites']),
            'missing_A_checks':sum(not value for r in rows for value in r['A_checks'])}
    if set(rows_by_view['Q1']) != set(rows_by_view['Q2']):
        raise ValueError('paired_parent_mismatch')
    for parent,row in rows_by_view['Q1'].items():
        other=rows_by_view['Q2'][parent]
        if not (row['x']==other['x'] and row['eligible']==other['eligible']
                and row['C']==other['C'] and row['A']==other['A']
                and Fraction(**row['T'])+Fraction(**other['T'])==1):
            raise ValueError('paired_fact_mismatch')
    verify_inputs()
    write(OUT/'reference/summary.json',{'status':'derived_from_raw_not_assignment','views':summaries,
          'paired_x_C_A_eligibility_unchanged':1494,'paired_T_sum_equals_one':1494,
          'reference_source_reads':support.READS,'allocation_rows_read':0,'account_or_b_reads':0,
          'resources':resources()})
    print('Independent reference derived 2,988 rows; allocation table and all account data unread.',flush=True)


if __name__=='__main__':
    try:main()
    except Exception as error:
        folder=OUT/'reference'
        if folder.exists() and not (folder/'failure.json').exists():
            write(folder/'failure.json',{'status':'failed_preserved','type':type(error).__name__,'reason':str(error)})
        raise
