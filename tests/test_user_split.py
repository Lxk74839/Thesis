import json
import hashlib
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]


class UserSplitTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=PROJECT / '.tmp')
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)

    def write(self, relative, value):
        path = self.root / 'input' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((json.dumps(value, sort_keys=True) + '\n').encode('utf-8'))
        return path

    def binding(self, path):
        return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    def fixture(self):
        users = [f'fixture-user-{n:03}' for n in range(1, 12)]
        accounts = [{'user_id': u, 'status': 'qualified', 'prior_positive_product_count': 1,
                     'prior_positive_parent_asins': ['H'], 'seen_parent_asins': ['H'],
                     'target_parent_asin': 'T'} for u in users]
        self.account_path = self.root / 'input/data/accounts.jsonl'
        self.account_path.parent.mkdir(parents=True)
        self.account_path.write_bytes(b''.join((json.dumps(r)+'\n').encode() for r in accounts))
        cat = self.root / 'input/data/catalog.jsonl'
        cat.write_bytes(b'{"parent_asin":"H","crop":"oats"}\n{"parent_asin":"T","crop":"rice"}\n')
        cat_record = self.write('records/catalog/catalog.json', {'catalog_path': 'data/catalog.jsonl', 'catalog_sha256': self.binding(cat)['sha256']})
        self.clean = {'stage': 'review_clean', 'status': 'cleaning_complete', 'scope_version': 'fixture',
                      'rules_version': 'review-cleaning-1.0.0', 'formal_clean_status': 'built',
                      'user_qualification_status': 'complete', 'catalog_record_path': 'records/catalog/catalog.json',
                      'catalog_record_sha256': self.binding(cat_record)['sha256'],
                      'counts': {'raw_accounts': 11, 'qualified_accounts': 11, 'catalog_products': 2}}
        for name in ('clean', 'text', 'quarantine', 'products', 'accounts', 'audit'):
            path = self.account_path if name == 'accounts' else self.root / f'input/data/{name}.jsonl'
            if name != 'accounts': path.write_bytes(b'')
            self.clean[name+'_path'] = path.relative_to(self.root/'input').as_posix()
            self.clean[name+'_sha256'] = self.binding(path)['sha256']
        self.clean_path = self.write('records/cleaning/clean.json', self.clean)
        self.acceptance = {'status': 'accepted_ticket06_cleaning_and_qualification_only',
                           'counts': self.clean['counts'], 'dependencies_sha256': {'records/cleaning/clean.json': self.binding(self.clean_path)['sha256']},
                           'component_sha256': {n:self.clean[n+'_sha256'] for n in ('clean','text','quarantine','products','accounts','audit')}}
        self.acceptance_path = self.write('records/cleaning/acceptance.json', self.acceptance)
        self.erratum = {'type': 'metadata_erratum', 'affected_field': 'stable_serialization',
                        'affected_record_path': 'records/cleaning/clean.json',
                        'affected_record_sha256': self.binding(self.clean_path)['sha256'],
                        'component_format_checks': {n:{'path':self.clean[n+'_path'],'sha256':self.clean[n+'_sha256']} for n in ('clean','text','quarantine','products','accounts','audit')}}
        self.erratum_path = self.write('records/cleaning/erratum.json', self.erratum)
        sets = {'legacy_qualification': [users[0]], 'legacy_mechanism': [users[0]],
                'legacy_preference': [users[0]], 'legacy_corpus': [users[0],users[4]]}
        self.fact = {'version': 'legacy-exposure-1.0.0', 'access_scope': 'preparation_evaluation_only',
                     'account_component_sha256': self.clean['accounts_sha256'], 'sets': sets,
                     'observed_agent_results': [{'user_id':users[0],'evidence':'legacy_log_2257'}],
                     'evidence': {**{k:{'account_count':len(v),'sha256':'0'*64,'path':'fixture'} for k,v in sets.items()},
                                  'legacy_log_2257':{'line':2257,'prefix_sha256':'0'*64},
                                  'current_aggregate':{'kind':'account_cohort_aggregate_review'}}}
        self.fact_path = self.write('data/exposure.json', self.fact)
        self.rules = json.loads((PROJECT/'config/user-split-1.0.0.json').read_text('utf-8'))
        self.rules.update(cleaning_acceptance=self.binding(self.acceptance_path), cleaning_erratum=self.binding(self.erratum_path), exposure_manifest=self.binding(self.fact_path))
        self.rules_path = self.write('config/user-split-1.0.0.json', self.rules)

    def run_split(self, output='output', refs=None):
        return subprocess.run([sys.executable, str(PROJECT/'prepare_data.py'), '--stage','user_split',
                               '--cleaning-record',str(self.clean_path),'--split-config',str(self.rules_path),
                               '--output-root',str(self.root/output),
                               *(['--group-refs',str(refs)] if refs else [])],
                              capture_output=True,text=True,encoding='utf-8',cwd=PROJECT)

    def refresh_fixture(self):
        records = [json.loads(s) for s in self.account_path.read_text('utf-8').splitlines()]
        self.clean['accounts_sha256'] = self.binding(self.account_path)['sha256']
        self.clean['counts'].update(raw_accounts=len(records),qualified_accounts=sum(r['status']=='qualified' for r in records))
        self.clean_path = self.write('records/cleaning/clean.json',self.clean)
        self.acceptance.update(counts=self.clean['counts'],dependencies_sha256={'records/cleaning/clean.json':self.binding(self.clean_path)['sha256']},
                               component_sha256={n:self.clean[n+'_sha256'] for n in ('clean','text','quarantine','products','accounts','audit')})
        self.acceptance_path = self.write('records/cleaning/acceptance.json',self.acceptance)
        self.erratum.update(affected_record_sha256=self.binding(self.clean_path)['sha256'],
                            component_format_checks={n:{'path':self.clean[n+'_path'],'sha256':self.clean[n+'_sha256']} for n in ('clean','text','quarantine','products','accounts','audit')})
        self.erratum_path = self.write('records/cleaning/erratum.json',self.erratum)
        self.fact['account_component_sha256'] = self.clean['accounts_sha256']
        self.fact_path = self.write('data/exposure.json',self.fact)
        self.rules.update(cleaning_acceptance=self.binding(self.acceptance_path),cleaning_erratum=self.binding(self.erratum_path),exposure_manifest=self.binding(self.fact_path))
        self.rules_path = self.write('config/user-split-1.0.0.json',self.rules)

    def test_approved_split_preserves_old_account_and_fills_floor_development_slots(self):
        self.fixture()
        result = self.run_split()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual((report['stage'],report['status']),('user_split','split_complete'))
        assigned = [json.loads(s) for s in (self.root/'output'/report['accounts_path']).read_text('utf-8').splitlines()]
        self.assertEqual({r['user_id'] for r in assigned if r['split']=='dev'}, {'fixture-user-001','fixture-user-002'})
        self.assertEqual((report['counts']['qualified_accounts'],report['counts']['dev_accounts'],report['counts']['test_accounts']), (11,2,9))
        self.assertEqual(next(r['split_hash'] for r in assigned if r['user_id']=='fixture-user-001'), 'c0b0f92cdb739fb58f60dd59087228d311af1b4e1d65f8aad86b6b503b86dc90')

    def test_unapproved_rule_changes_cannot_publish_a_split(self):
        self.fixture()
        original = dict(self.rules)
        changes = {'approval':'draft','scheme':'B','salt':'another-salt','hash':'sha1',
                   'hash_input':'trim_user','sort':'source_order','development_divisor':True,
                   'rounding':'nearest','legacy_policy':'allow_test','unknown_reading_policy':'unexposed',
                   'version':'../overwrite'}
        for key,value in changes.items():
            with self.subTest(key=key):
                self.rules = {**original,key:value}
                self.rules_path = self.write('config/user-split-1.0.0.json',self.rules)
                result = self.run_split('invalid-'+key)
                self.assertEqual(result.returncode,2)
                self.assertEqual(json.loads(result.stdout)['error']['message'],'rules_not_approved')
                self.assertFalse((self.root/('invalid-'+key)/'records/splits').exists())

    def test_bound_source_and_component_bytes_cannot_be_changed(self):
        self.fixture()
        paths = [self.root/'input'/self.clean[n+'_path'] for n in ('clean','text','quarantine','products','accounts','audit')]
        paths += [self.fact_path,self.acceptance_path,self.erratum_path,self.root/'input/data/catalog.jsonl']
        for n,path in enumerate(paths):
            with self.subTest(component=path.name):
                before = path.read_bytes()
                try:
                    path.write_bytes(before+b' ')
                    result = self.run_split('tampered-'+str(n))
                    self.assertEqual(result.returncode,2)
                    self.assertIn('checksum',json.loads(result.stdout)['error']['message'])
                    self.assertFalse((self.root/('tampered-'+str(n))/'records/splits').exists())
                finally:
                    path.write_bytes(before)

    def test_acceptance_erratum_and_exposure_must_bind_the_same_cleaning(self):
        self.fixture()
        cases = [('cleaning_acceptance','status','unaccepted'),
                 ('cleaning_acceptance','counts',{'raw_accounts':11,'qualified_accounts':10,'catalog_products':2}),
                 ('cleaning_acceptance','component_sha256',{}),
                 ('cleaning_acceptance','dependencies_sha256',{}),
                 ('cleaning_erratum','type','unrelated'),
                 ('cleaning_erratum','affected_record_sha256','0'*64),
                 ('cleaning_erratum','component_format_checks',{}),
                 ('exposure_manifest','account_component_sha256','0'*64)]
        originals = {'cleaning_acceptance':self.acceptance,'cleaning_erratum':self.erratum,'exposure_manifest':self.fact}
        paths = {'cleaning_acceptance':self.acceptance_path,'cleaning_erratum':self.erratum_path,'exposure_manifest':self.fact_path}
        base_rules = copy.deepcopy(self.rules)
        for n,(binding,key,value) in enumerate(cases):
            with self.subTest(binding=binding,key=key):
                changed = {**originals[binding],key:value}
                paths[binding].write_bytes((json.dumps(changed)+'\n').encode())
                self.rules = {**base_rules,binding:self.binding(paths[binding])}
                self.rules_path = self.write('config/user-split-1.0.0.json',self.rules)
                result = self.run_split('unaccepted-'+str(n))
                self.assertEqual(result.returncode,2)
                self.assertEqual(json.loads(result.stdout)['status'],'split_incomplete')
                self.assertFalse((self.root/('unaccepted-'+str(n))/'records/splits').exists())
                paths[binding].write_bytes((json.dumps(originals[binding],sort_keys=True)+'\n').encode())

    def test_illegal_or_duplicate_source_identities_cannot_disappear_from_pool(self):
        self.fixture()
        original = [json.loads(s) for s in self.account_path.read_text('utf-8').splitlines()]
        for n,value in enumerate([None,17,{},'   ','fixture-user-002']):
            with self.subTest(kind=type(value).__name__):
                records = copy.deepcopy(original)
                records[0]['user_id'] = value
                self.account_path.write_bytes(b''.join((json.dumps(r)+'\n').encode() for r in records))
                self.refresh_fixture()
                result = self.run_split('bad-identity-'+str(n))
                self.assertEqual(result.returncode,2)
                self.assertEqual(json.loads(result.stdout)['error']['message'],'invalid_or_duplicate_account_identity')
                self.assertFalse((self.root/('bad-identity-'+str(n))/'records/splits').exists())

    def test_exposure_facts_are_validated_and_unknown_reading_is_preserved(self):
        self.fixture()
        original = copy.deepcopy(self.fact)
        for n,kind in enumerate(['duplicate','wrong_type','missing_set','bad_count','bad_evidence','known_outside','scope']):
            with self.subTest(kind=kind):
                self.fact = copy.deepcopy(original)
                if kind=='duplicate': self.fact['sets']['legacy_corpus'].append('fixture-user-005')
                if kind=='wrong_type': self.fact['sets']['legacy_qualification'] = 'fixture-user-001'
                if kind=='missing_set': self.fact['sets'].pop('legacy_preference')
                if kind=='bad_count': self.fact['evidence']['legacy_corpus']['account_count'] = 99
                if kind=='bad_evidence': self.fact['observed_agent_results'][0]['evidence'] = 'absent'
                if kind=='known_outside': self.fact['observed_agent_results'][0]['user_id'] = 'fixture-user-005'
                if kind=='scope': self.fact['access_scope'] = 'model_visible'
                self.refresh_fixture()
                result = self.run_split('bad-exposure-'+str(n))
                self.assertEqual(result.returncode,2)
                self.assertEqual(json.loads(result.stdout)['status'],'split_incomplete')
        self.fact = original
        self.refresh_fixture()
        result = self.run_split('valid-exposure')
        self.assertEqual(result.returncode,0,result.stdout)
        report = json.loads(result.stdout)
        exposed = {r['user_id']:r for s in (self.root/'valid-exposure'/report['exposure_path']).read_text('utf-8').splitlines() if (r:=json.loads(s))}
        self.assertEqual((exposed['fixture-user-001']['agent_account_result_view'],exposed['fixture-user-005']['agent_account_result_view']),('observed','unknown'))
        self.assertTrue(exposed['fixture-user-005']['legacy_corpus_member'])
        self.assertEqual({r['human_account_result_view'] for r in exposed.values()},{'unknown'})

    def test_legacy_development_over_quota_blocks_instead_of_changing_ratio(self):
        self.fixture()
        self.fact['sets']['legacy_qualification'] = ['fixture-user-001','fixture-user-003','fixture-user-004']
        self.fact['sets']['legacy_corpus'] += ['fixture-user-003','fixture-user-004']
        for key in ('legacy_qualification','legacy_corpus'):
            self.fact['evidence'][key]['account_count'] = len(self.fact['sets'][key])
        self.refresh_fixture()
        result = self.run_split()
        self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['error']['message'],'forced_development_exceeds_quota')
        self.assertFalse((self.root/'output/records/splits').exists())

    def test_references_inherit_accounts_and_never_increase_account_counts(self):
        self.fixture()
        rows = [{'reference_id':r,'user_id':u} for r,u in [('root','fixture-user-001'),('scene','fixture-user-001'),('repeat','fixture-user-001'),('other','fixture-user-005')]]
        refs = self.root/'refs.jsonl'
        refs.write_bytes(b''.join((json.dumps(r)+'\n').encode() for r in rows))
        result = self.run_split(refs=refs)
        self.assertEqual(result.returncode,0,result.stdout)
        report = json.loads(result.stdout)
        projected = [json.loads(s) for s in (self.root/'output'/report['references_path']).read_text('utf-8').splitlines()]
        self.assertEqual({r['reference_id']:r['split'] for r in projected},{'root':'dev','scene':'dev','repeat':'dev','other':'test'})
        self.assertEqual((report['counts']['qualified_accounts'],report['counts']['dev_accounts'],report['counts']['test_accounts'],report['counts']['reference_rows']),(11,2,9,4))
        for n,bad in enumerate([rows+[rows[0]],rows+[{'reference_id':'unknown','user_id':'not-in-pool'}],rows+[{'reference_id':None,'user_id':'fixture-user-001'}]]):
            with self.subTest(invalid_refs=n):
                refs.write_bytes(b''.join((json.dumps(r)+'\n').encode() for r in bad))
                failed = self.run_split('invalid-refs-'+str(n),refs=refs)
                self.assertEqual(failed.returncode,2)
                self.assertEqual(json.loads(failed.stdout)['error']['message'],'invalid_group_reference')
                self.assertFalse((self.root/('invalid-refs-'+str(n))/'records/splits').exists())

    def test_same_version_reuses_verified_bytes_and_rejects_changes_or_damage(self):
        self.fixture()
        first = self.run_split()
        self.assertEqual(first.returncode,0,first.stdout)
        report = json.loads(first.stdout)
        record = self.root/'output'/report['record_path']
        before = record.read_bytes()
        repeated = self.run_split()
        self.assertEqual(repeated.returncode,0,repeated.stdout)
        self.assertEqual(json.loads(repeated.stdout),report)
        self.assertEqual(record.read_bytes(),before)
        refs = self.root/'refs.jsonl'
        refs.write_text('{"reference_id":"new","user_id":"fixture-user-001"}\n',encoding='utf-8')
        changed = self.run_split(refs=refs)
        self.assertEqual(changed.returncode,2)
        self.assertFalse((self.root/'output'/report['accounts_path']).parent.joinpath('reference-groups.jsonl').exists())
        self.assertEqual(record.read_bytes(),before)
        accounts = self.root/'output'/report['accounts_path']
        accounts.write_bytes(b'corrupted\n')
        damaged = self.run_split()
        self.assertEqual(damaged.returncode,2)
        self.assertEqual(accounts.read_bytes(),b'corrupted\n')
        self.assertEqual(record.read_bytes(),before)

    def test_initial_input_paths_and_output_root_must_stay_in_project(self):
        self.fixture()
        for flag in ('--cleaning-record','--split-config','--group-refs'):
            with self.subTest(flag=flag):
                arguments = {'--cleaning-record':str(self.clean_path),'--split-config':str(self.rules_path)}
                arguments[flag] = str(PROJECT.parent/'outside-input-must-not-be-read.json')
                command = [sys.executable,str(PROJECT/'prepare_data.py'),'--stage','user_split','--output-root',str(self.root/'outside-input')]
                for key,value in arguments.items(): command += [key,value]
                result = subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
                self.assertEqual(result.returncode,2)
                self.assertEqual(json.loads(result.stdout)['error']['message'],'input_path_outside_project')
        result = subprocess.run([sys.executable,str(PROJECT/'prepare_data.py'),'--stage','user_split','--cleaning-record',str(self.clean_path),'--split-config',str(self.rules_path),'--output-root',str(PROJECT.parent/'outside-output-must-not-exist')],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,2)
        self.assertIn('output-root must remain inside',result.stderr)

    def test_invalid_qualification_product_relations_fail_without_disclosing_labels(self):
        self.fixture()
        rows = [json.loads(s) for s in self.account_path.read_text('utf-8').splitlines()]
        original = copy.deepcopy(rows)
        for n,field,value in [(0,'target_parent_asin','PRIVATE_TARGET_MARKER'),(1,'prior_positive_product_count',2),(2,'seen_parent_asins',['H','T'])]:
            with self.subTest(field=field):
                rows = copy.deepcopy(original)
                rows[0][field] = value
                self.account_path.write_bytes(b''.join((json.dumps(r)+'\n').encode() for r in rows))
                self.refresh_fixture()
                result = self.run_split('invalid-relations-'+str(n))
                self.assertEqual(result.returncode,2)
                self.assertEqual(json.loads(result.stdout)['error']['message'],'qualification_catalog_mismatch')
                self.assertNotIn('PRIVATE_TARGET_MARKER',result.stdout+result.stderr)
                self.assertNotIn('fixture-user-001',result.stdout+result.stderr)
                self.assertFalse((self.root/('invalid-relations-'+str(n))/'records/splits').exists())

    def test_malformed_nested_metadata_returns_machine_failure(self):
        self.fixture()
        originals = {'cleaning_acceptance':self.acceptance,'cleaning_erratum':self.erratum,'exposure_manifest':self.fact}
        paths = {'cleaning_acceptance':self.acceptance_path,'cleaning_erratum':self.erratum_path,'exposure_manifest':self.fact_path}
        base_rules = copy.deepcopy(self.rules)
        for n,(binding,field) in enumerate([('cleaning_acceptance','component_sha256'),('cleaning_erratum','component_format_checks'),('exposure_manifest','evidence')]):
            with self.subTest(binding=binding):
                changed = copy.deepcopy(originals[binding])
                if binding=='exposure_manifest': changed[field]['legacy_corpus'] = []
                else: changed[field] = []
                paths[binding].write_bytes((json.dumps(changed)+'\n').encode())
                self.rules = {**base_rules,binding:self.binding(paths[binding])}
                self.rules_path = self.write('config/user-split-1.0.0.json',self.rules)
                result = self.run_split('malformed-'+str(n))
                self.assertEqual(result.returncode,2)
                self.assertEqual(json.loads(result.stdout)['status'],'split_incomplete')
                self.assertNotIn('Traceback',result.stderr)
                paths[binding].write_bytes((json.dumps(originals[binding],sort_keys=True)+'\n').encode())

    def test_incomplete_existing_output_is_preserved_without_publishing(self):
        self.fixture()
        partial = self.root/'output/records/splits/fixture-user-split-1.0.0.json.partial'
        partial.parent.mkdir(parents=True)
        partial.write_bytes(b'previous-incomplete-attempt\n')
        result = self.run_split()
        self.assertEqual(result.returncode,2)
        self.assertEqual(partial.read_bytes(),b'previous-incomplete-attempt\n')
        self.assertFalse((self.root/'output/data/splits').exists())
        self.assertFalse(partial.with_suffix('').exists())

    def test_split_requires_explicit_cleaning_record_and_rules(self):
        result = subprocess.run(
            [sys.executable, str(PROJECT / 'prepare_data.py'), '--stage', 'user_split',
             '--output-root', str(self.root)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2)
        self.assertIn('user_split requires cleaning-record and split-config', result.stderr)
        self.assertFalse((self.root / 'records/splits').exists())


if __name__ == '__main__':
    unittest.main()
