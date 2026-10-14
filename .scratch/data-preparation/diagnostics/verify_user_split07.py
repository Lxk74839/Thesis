"""Independent ticket 07 audit and CLI reproduction, without production imports.

Run from Thesis with its Conda environment. Private challenge copies stay in .tmp;
only an aggregate audit is written to verification. This is not a preparation API.
"""
from collections import Counter
import contextlib
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[3]
PREFIX = '.scratch/data-preparation/verification/'
SALT = 'Thesis-ticket07-grain-A-1.1.15-review-cleaning-1.0.0-split-v1'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def rows(path):
    return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines()]


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2)+'\n').encode())


def binding(path):
    return {'path': str(path), 'sha256': digest(path)}


def shown_users(value, mapping, seen, depth=0):
    if depth > 15:
        return
    if isinstance(value, dict):
        if value.get('task_id') in mapping and {'full_top','title_only_top','review_only_top'} <= value.keys():
            seen.add(mapping[value['task_id']])
        for item in value.values():
            shown_users(item, mapping, seen, depth+1)
    elif isinstance(value, list):
        for item in value:
            shown_users(item, mapping, seen, depth+1)
    elif isinstance(value, str) and any(k in value for k in ('task_id','full_top','content')):
        decoder = json.JSONDecoder()
        with contextlib.suppress(ValueError):
            parsed = json.loads(value)
            if parsed != value:
                shown_users(parsed, mapping, seen, depth+1)
                return
        position = 0
        while position < len(value):
            positions = [n for n in (value.find('{',position),value.find('[',position)) if n >= 0]
            if not positions:
                break
            start = min(positions)
            try:
                parsed, position = decoder.raw_decode(value,start)
            except ValueError:
                position = start+1
            else:
                shown_users(parsed,mapping,seen,depth+1)


def invoke(cleaning, config, output, log, refs=None):
    command = [sys.executable,str(ROOT/'prepare_data.py'),'--stage','user_split',
               '--cleaning-record',str(cleaning),'--split-config',str(config),'--output-root',str(output)]
    if refs:
        command += ['--group-refs',str(refs)]
    result = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    (ROOT/PREFIX/log).write_bytes((result.stdout+result.stderr).encode('utf-8'))
    assert result.returncode == 0, 'Public CLI challenge failed; inspect its aggregate log'
    return json.loads(result.stdout)


def main():
    assert Path(sys.prefix).resolve() == ROOT/'.conda/envs/Thesis'
    clean_path = ROOT/'records/cleaning/grain-A-1.1.15-review-cleaning-1.0.0.json'
    config_path = ROOT/'config/user-split-1.0.0.json'
    record_path = ROOT/'records/splits/grain-A-1.1.15-user-split-1.0.0.json'
    clean, config, report = load(clean_path), load(config_path), load(record_path)
    fact_path = ROOT/config['exposure_manifest']['path']
    fact = load(fact_path)
    assert digest(fact_path) == config['exposure_manifest']['sha256']
    assert config['salt'] == SALT and config['scheme'] == 'A' and config['development_divisor'] == 5
    qualified = {r['user_id']:r for r in rows(ROOT/clean['accounts_path']) if r['status']=='qualified'}
    assert len(qualified) == 1603
    for name in ('accounts','exposure'):
        data = (ROOT/report[name+'_path']).read_bytes()
        assert data and not data.startswith(b'\xef\xbb\xbf') and b'\r' not in data and data.endswith(b'\n')
        assert digest(ROOT/report[name+'_path']) == report[name+'_sha256']
    assigned_rows = rows(ROOT/report['accounts_path'])
    assigned = {r['user_id']:r for r in assigned_rows}
    assert len(assigned_rows) == len(assigned) == 1603 and assigned.keys() == qualified.keys()

    original_sets = {}
    for name in ('legacy_qualification','legacy_mechanism','legacy_corpus'):
        source = Path(fact['evidence'][name]['path'])
        assert digest(source) == fact['evidence'][name]['sha256']
        data = rows(source) if name=='legacy_corpus' else load(source)
        original_sets[name] = {r['user_id'] for r in data}
        assert original_sets[name] == set(fact['sets'][name])
    preference = Path(fact['evidence']['legacy_preference']['path'])
    assert digest(preference) == fact['evidence']['legacy_preference']['sha256']
    hashes = {r['user_hash'] for r in rows(preference)}
    old_preferences = {u for u in original_sets['legacy_corpus'] if hashlib.sha256(('Plan_Thesis-parent-grain-v1-20261002|'+u).encode()).hexdigest() in hashes}
    assert old_preferences == set(fact['sets']['legacy_preference']) and len(old_preferences)==134
    log_binding = fact['evidence']['legacy_log_2257']
    prefix_digest = hashlib.sha256()
    with Path(log_binding['path']).open('rb') as stream:
        for _ in range(2257):
            line = next(stream)
            prefix_digest.update(line)
    assert prefix_digest.hexdigest() == log_binding['prefix_sha256'] == '436cb895013f6aeac8a98d00b13c51fd5e1666d8a02e7be707241d888741d566'
    task_users = {r['task_id']:r['user_id'] for r in load(fact['evidence']['legacy_mechanism']['path'])}
    observed = set()
    shown_users(json.loads(line)['payload']['output'],task_users,observed)
    assert len(observed)==8 and observed == {r['user_id'] for r in fact['observed_agent_results']}
    assert len(observed & qualified.keys())==2
    forced = (original_sets['legacy_qualification'] | original_sets['legacy_mechanism']) & qualified.keys()
    assert len(forced)==16

    # SQL defines the approved quota and order independently of production code.
    db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE account(uid TEXT PRIMARY KEY, h TEXT, old INTEGER)')
    db.executemany('INSERT INTO account VALUES(?,?,?)',[(u,hashlib.sha256((SALT+'\0'+u).encode()).hexdigest(),int(u in forced)) for u in qualified])
    expected = dict(db.execute("SELECT uid, CASE WHEN old OR uid IN (SELECT uid FROM account WHERE old=0 ORDER BY h COLLATE BINARY, CAST(uid AS BLOB) LIMIT 304) THEN 'dev' ELSE 'test' END FROM account"))
    assert all(assigned[u]['split']==group for u,group in expected.items())
    assert [r['user_id'] for r in assigned_rows] == [r[0] for r in db.execute('SELECT uid FROM account ORDER BY h COLLATE BINARY, CAST(uid AS BLOB)')]
    assert all(assigned[u]['split_hash']==h for u,h in db.execute('SELECT uid,h FROM account'))
    development = {u for u,v in expected.items() if v=='dev'}
    testing = {u for u,v in expected.items() if v=='test'}
    assert len(development)==320 and len(testing)==1283 and not development & testing
    assert development | testing == qualified.keys() and forced <= development
    assert len(development-forced)==304
    for u,r in assigned.items():
        assert r['assignment_reason']==('legacy_forced' if u in forced else 'hash_fill' if u in development else 'hash_remainder')

    exposure_rows = rows(ROOT/report['exposure_path'])
    exposures = {r['user_id']:r for r in exposure_rows}
    assert len(exposures)==len(exposure_rows)==1603 and exposures.keys()==qualified.keys()
    for u,r in exposures.items():
        assert all(r[k+'_member']==(u in values) for k,values in {**original_sets,'legacy_preference':old_preferences}.items())
        assert r['agent_account_result_view']==('observed' if u in observed else 'unknown')
        assert r['human_account_result_view']=='unknown' and r['current_program_processing']=='observed'
        assert r['legacy_program_processing']==('observed' if u in original_sets['legacy_corpus'] else 'unknown')
        assert r['aggregate_review']=='current_stage1_cohort_observed'
    prior = load(ROOT/'.scratch/data-preparation/verification/ticket07-stage1-aggregates.json')['plans']['A_force_old_exploratory_development_20pct']
    for name,users in [('dev',development),('test',testing)]:
        actual = report['groups'][name]
        for key,old_key in [('accounts','accounts'),('history_depth_distribution','history_depth_frequency'),('history_parent_products','positive_history_products'),('target_parent_products','target_products'),('target_crops','target_crops'),('target_top1_accounts','target_top1_accounts')]:
            assert actual[key]==prior[name][old_key]
        assert actual['known_agent_result_accounts']==len(users & observed)
        assert actual['legacy_exploratory_accounts']==len(users & forced)
        assert actual['legacy_corpus_accounts']==len(users & original_sets['legacy_corpus'])
    assert report['groups']['dev']['legacy_corpus_accounts']==43 and report['groups']['test']['legacy_corpus_accounts']==70
    assert all(report[k]==v for k,v in {'formal_package_status':'not_built','model_input_status':'not_released','sim_status':'not_built','sample_sufficiency':'not_determined','blind_test_claim':False}.items())
    public_text = record_path.read_text('utf-8')+(ROOT/PREFIX/'ticket07-formal-run.txt').read_text('utf-8')
    assert not any(u in public_text for u in qualified)

    work = Path(tempfile.mkdtemp(prefix='ticket07-independent-',dir=ROOT/'.tmp'))
    repeated = invoke(clean_path,config_path,work/'reproduce','ticket07-reproduce-run.txt')
    for name in ('accounts','exposure'):
        assert (ROOT/report[name+'_path']).read_bytes()==(work/'reproduce'/repeated[name+'_path']).read_bytes()

    refs = work/'normal-refs.jsonl'
    reference_rows = [{'reference_id':f'{kind}-{i:04}', 'user_id':u} for i,u in enumerate(sorted(qualified)) for kind in ('root','scene','repeat')]
    refs.write_bytes(b''.join((json.dumps(r)+'\n').encode() for r in reference_rows))
    ref_report = invoke(clean_path,config_path,work/'reference-output','ticket07-reference-run.txt',refs)

    copied = work/'order-input'
    for name in ('clean','text','quarantine','products','accounts','audit'):
        destination = copied/clean[name+'_path']
        destination.parent.mkdir(parents=True,exist_ok=True)
        if name=='accounts':
            destination.write_bytes(b''.join(reversed((ROOT/clean[name+'_path']).read_bytes().splitlines(keepends=True))))
        else:
            shutil.copyfile(ROOT/clean[name+'_path'],destination)
    catalog_record = load(ROOT/clean['catalog_record_path'])
    save(copied/clean['catalog_record_path'],catalog_record)
    destination = copied/catalog_record['catalog_path']
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/catalog_record['catalog_path'],destination)
    changed_clean = {**clean,'accounts_sha256':digest(copied/clean['accounts_path']),
                     'catalog_record_sha256':digest(copied/clean['catalog_record_path'])}
    copied_clean = copied/'records/cleaning'/clean_path.name
    save(copied_clean,changed_clean)
    acceptance = load(ROOT/config['cleaning_acceptance']['path'])
    clean_relative = clean_path.relative_to(ROOT).as_posix()
    acceptance['dependencies_sha256'] = {(k if k in (clean_relative,clean['catalog_record_path']) else str(ROOT/k)):v for k,v in acceptance['dependencies_sha256'].items()}
    acceptance['dependencies_sha256'][clean_relative] = digest(copied_clean)
    acceptance['dependencies_sha256'][clean['catalog_record_path']] = changed_clean['catalog_record_sha256']
    acceptance['component_sha256']['accounts'] = changed_clean['accounts_sha256']
    copied_acceptance = copied/'records/cleaning/acceptance.json'
    save(copied_acceptance,acceptance)
    erratum = load(ROOT/config['cleaning_erratum']['path'])
    erratum['affected_record_sha256'] = digest(copied_clean)
    erratum['component_format_checks']['accounts']['sha256'] = changed_clean['accounts_sha256']
    copied_erratum = copied/'records/cleaning/erratum.json'
    save(copied_erratum,erratum)
    changed_fact = {**fact,'account_component_sha256':changed_clean['accounts_sha256'],
                    'sets':{k:list(reversed(v)) for k,v in fact['sets'].items()},
                    'observed_agent_results':list(reversed(fact['observed_agent_results']))}
    copied_fact = copied/'data/exposure.json'
    save(copied_fact,changed_fact)
    changed_config = {**config,'cleaning_acceptance':binding(copied_acceptance),'cleaning_erratum':binding(copied_erratum),'exposure_manifest':binding(copied_fact)}
    copied_config = copied/'config/user-split-1.0.0.json'
    save(copied_config,changed_config)
    reversed_refs = work/'reversed-refs.jsonl'
    reversed_refs.write_bytes(b''.join(reversed(refs.read_bytes().splitlines(keepends=True))))
    ordered_report = invoke(copied_clean,copied_config,work/'order-output','ticket07-order-run.txt',reversed_refs)
    for name in ('accounts','exposure'):
        assert (ROOT/report[name+'_path']).read_bytes()==(work/'order-output'/ordered_report[name+'_path']).read_bytes()
    first_refs = (work/'reference-output'/ref_report['references_path']).read_bytes()
    assert first_refs==(work/'order-output'/ordered_report['references_path']).read_bytes()
    projected = rows(work/'order-output'/ordered_report['references_path'])
    assert len(projected)==4809 and all(r['split']==expected[r['user_id']] for r in projected)
    assert ordered_report['counts']['qualified_accounts']==1603 and ordered_report['counts']['reference_rows']==4809
    protect = load(ROOT/'.tmp/ticket07-implementation-protection.json')
    assert all(digest(p)==h for p,h in protect.items())
    private_paths = [fact_path,ROOT/report['accounts_path'],ROOT/report['exposure_path']]
    ignored = subprocess.run(['git','check-ignore','--stdin'],input='\n'.join(map(str,private_paths))+'\n',capture_output=True,text=True,cwd=ROOT)
    assert ignored.returncode==0 and len(ignored.stdout.splitlines())==3
    result = {'status':'independent_checks_passed','production_imports':False,
              'implementation_commit':report['code_commit'],'review_baseline':'e2617ada7a182685fef00567dbf064fc096d46f4',
              'qualified_accounts':1603,'development_accounts':320,'test_accounts':1283,'forced_development':16,'hash_fill_development':304,
              'intersection':0,'full_qualification_coverage':True,'all_assignments_match_independent_sql':True,
              'all_exposure_rows_match_original_sources':True,'old_source_counts':{k:len(v) for k,v in {**original_sets,'legacy_preference':old_preferences}.items()},
              'observed_agent_accounts_lower_bound':2,'unknown_agent_reading_accounts':1601,'unknown_human_reading_accounts':1603,
              'legacy_test_corpus_accounts_unknown':70,'stable_components_byte_identical':True,
              'source_row_order_invariant':True,'exposure_set_order_invariant':True,'reference_order_invariant':True,
              'reference_rows_checked':4809,'references_inherit_group':True,'protected_sources_unchanged':len(protect),
              'private_data_git_ignored':True,'public_record_and_log_contain_no_account_identifiers':True,
              'component_sha256':{n:report[n+'_sha256'] for n in ('accounts','exposure')},
              'reference_projection_sha256':digest(work/'order-output'/ordered_report['references_path']),
              'challenge_workspace':str(work),'verifier_sha256':digest(Path(__file__)),
              'sample_sufficiency':'not_determined','joint_package':'not_built'}
    save(ROOT/PREFIX/'user-split-1.0.0-independent-check.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
