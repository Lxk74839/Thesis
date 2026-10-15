"""Independent full ticket08 audit and CLI challenges; no production imports.

Uses SQL for background counts, a br-only reference for the observed real text,
and byte comparisons for fresh-root reproduction and a private target mutation.
Only aggregate results leave project-local private data/temporary directories.
"""

from collections import Counter, defaultdict
import ast
import hashlib
import hmac
from html import unescape
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[3]
VERIFY = ROOT / '.scratch/data-preparation/verification'
MAIN = 'records/preference-tasks/grain-A-1.1.15-preference-task-1.0.1.json'
CLEAN = 'records/cleaning/grain-A-1.1.15-review-cleaning-1.0.0.json'
SPLIT = 'records/splits/grain-A-1.1.15-user-split-1.0.0.json'
CONFIG = 'config/preference-task-1.0.1.json'
PROBE = 'data/task-inputs/preference-task-1.0.1/access-probe-1.0.0.jsonl'


def load(path):
    return json.loads(Path(path).read_text('utf-8'))


def rows(path):
    with Path(path).open(encoding='utf-8') as stream:
        for line in stream:
            yield json.loads(line)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def text_hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(value))


def save_rows(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as stream:
        for value in values:
            stream.write(encoded(value))


def reference_text(source, kind, user=None):
    """The real admitted corpus has br tags only; anything else stops this audit.

    This deliberately does not reproduce the production HTMLParser. Non-br,
    comments, script/style and malformed HTML behavior is covered by hand-written
    expected strings through the public CLI, not claimed as a universal oracle.
    """
    source.encode('utf-8', errors='strict')
    stages = []
    current = source

    def step(name, value):
        nonlocal current
        if value != current:
            stages.append((name, current, value))
        current = value

    step('line_endings', current.replace('\r\n', '\n').replace('\r', '\n'))
    # A title's literal "<500g>" is ordinary text, not an HTML tag.
    tags = re.findall(r'<[A-Za-z!/][^>]*>', current)
    assert all(re.fullmatch(r'<br\s*/?\s*>', tag, re.I) for tag in tags), 'reference_text_has_unexpected_tag'
    step('html', unescape(re.sub(r'<br\s*/?\s*>', '\n', current, flags=re.I)))
    step('controls', re.sub('[\x00-\x08\x0b-\x1f\x7f]', '', current))
    link_pattern = r'''\b(?:https?://|ftp://|www\.)[^\s<>"']+'''
    step('links', re.sub(link_pattern, lambda m: '[LINK]' + m[0][len(m[0].rstrip('.,;:!?)]}')):], current, flags=re.I))
    step('emails', re.sub(r'(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9.-])', '[EMAIL]', current))
    step('phones', re.sub(r'(?<![A-Za-z0-9])(?:\+?1[ \t.-]?)?(?:\(\d{3}\)|\d{3})[ \t.-]?\d{3}[ \t.-]?\d{4}(?![A-Za-z0-9])', '[PHONE]', current))
    if user:
        step('source_user', current.replace(user, '[USER]'))
    lines = [' '.join(line.split()) for line in current.split('\n')]
    step('whitespace', re.sub('\n{3,}', '\n\n', '\n'.join(lines)).strip())
    if kind == 'product_title':
        step('commercial_tail', re.sub(r'\s*[-–—|]?\s*Ships Free over \$\d+(?:\.\d+)?\s*$', '', current, flags=re.I).strip())
    return current, stages


def audit_text(source, processed, trace, kind, user=None):
    expected, stages = reference_text(source, kind, user)
    assert processed == expected, 'full_text_projection_mismatch'
    assert trace['original_sha256'] == text_hash(source) and trace['processed_sha256'] == text_hash(expected), 'text_trace_hash_mismatch'
    assert trace['text_policy_version'] == 'finite-text-1.0.0', 'text_trace_version_mismatch'
    for prefix, value in (('raw', source), ('processed', expected)):
        assert trace[prefix + '_codepoints'] == len(value), 'text_length_mismatch'
        assert trace[prefix + '_utf8_bytes'] == len(value.encode('utf-8')), 'text_byte_length_mismatch'
    assert len(stages) == len(trace['stages']), 'text_stage_count_mismatch'
    for actual, (name, before, after) in zip(trace['stages'], stages):
        assert actual['stage'] == name and actual['input_sha256'] == text_hash(before) and actual['output_sha256'] == text_hash(after), 'text_stage_hash_mismatch'
        assert actual['coordinate'] == 'stage_input_output_unicode_codepoints', 'text_coordinate_mismatch'
        a0 = b0 = 0
        for edit in actual['edits']:
            a, end_a, b, end_b = [edit[k] for k in ('input_start', 'input_end', 'output_start', 'output_end')]
            assert a0 <= a <= end_a <= len(before) and b0 <= b <= end_b <= len(after), 'text_edit_bounds_mismatch'
            assert before[a0:a] == after[b0:b], 'text_unreported_edit'
            assert edit['operation'] in ('replace', 'insert', 'delete'), 'text_edit_operation_mismatch'
            if edit['operation'] == 'insert': assert a == end_a and b < end_b, 'text_insert_mismatch'
            if edit['operation'] == 'delete': assert b == end_b and a < end_a, 'text_delete_mismatch'
            a0, b0 = end_a, end_b
        assert before[a0:] == after[b0:], 'text_unreported_tail_edit'
    return len(source), len(expected)


def invoke(cleaning, split, config, output, probe, log):
    result = subprocess.run([sys.executable, str(ROOT / 'prepare_data.py'), '--stage', 'preference_tasks',
        '--cleaning-record', str(cleaning), '--split-record', str(split), '--task-config', str(config),
        '--output-root', str(output), '--access-probe', str(probe)], cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    (VERIFY / log).write_bytes((result.stdout + result.stderr).encode('utf-8'))
    assert result.returncode == 0, 'independent_cli_challenge_failed_see_aggregate_log'
    return json.loads(result.stdout)


def compare_components(left_root, left, right_root, right, names=None):
    names = names or sorted(left['components'])
    result = {}
    for name in names:
        a, b = left_root / left['components'][name]['path'], right_root / right['components'][name]['path']
        assert digest(a) == digest(b), 'stable_component_byte_mismatch'
        with a.open('rb') as first, b.open('rb') as second:
            while True:
                x, y = first.read(1024 * 1024), second.read(1024 * 1024)
                assert x == y, 'stable_component_direct_byte_mismatch'
                if not x: break
        result[name] = {'sha256': digest(a), 'bytes': a.stat().st_size, 'direct_bytes_equal': True}
    return result


def full_audit(main):
    cleaning, split, config = [load(ROOT / p) for p in (CLEAN, SPLIT, CONFIG)]
    catalog_record = load(ROOT / cleaning['catalog_record_path'])
    original_catalog = {p['parent_asin']: p for p in rows(ROOT / catalog_record['catalog_path'])}
    parents = sorted(original_catalog, key=lambda p: p.encode('utf-8'))
    products = list(rows(ROOT / main['components']['catalog']['path']))
    assert len(products) == len(parents) == 1494, 'catalog_total_mismatch'
    assert [p['parent_asin'] for p in products] == parents, 'catalog_membership_or_order_mismatch'
    product_map = {p['parent_asin']: p for p in products}
    clean = list(rows(ROOT / cleaning['clean_path']))
    valid = list(rows(ROOT / cleaning['text_path']))
    qualifications = {p['user_id']: p for p in rows(ROOT / cleaning['accounts_path']) if p['status'] == 'qualified'}
    assignments = {p['user_id']: p['split'] for p in rows(ROOT / split['accounts_path'])}
    assert qualifications.keys() == assignments.keys() and len(assignments) == 1603, 'root_account_membership_mismatch'
    assert Counter(assignments.values()) == {'dev': 320, 'test': 1283}, 'split_total_mismatch'
    ledger, text_ledger = defaultdict(list), defaultdict(list)
    for r in clean: ledger[r['review']['user_id']].append(r)
    for r in valid: text_ledger[r['review']['user_id']].append(r)
    for r in rows(ROOT / cleaning['quarantine_path']): ledger[r['review']['user_id']].append(r)
    evaluations = {r['task_id']: r for r in rows(ROOT / main['components']['evaluation']['path'])}
    key = (ROOT / config['identity_key']['path']).read_bytes()
    identity = {hmac.new(key, config['version'].encode() + b'\0' + u.encode(), hashlib.sha256).hexdigest(): u for u in assignments}
    assert evaluations.keys() == identity.keys() and len(evaluations) == 1603, 'private_evaluation_coverage_mismatch'
    traces = list(rows(ROOT / main['components']['audit']['path']))
    title_trace = {r['parent_asin']: r for r in traces if r['record_type'] == 'catalog_text'}
    task_trace = {r['task_id']: r for r in traces if r['record_type'] == 'task'}
    assert len(traces) == 1494 + 1603 and task_trace.keys() == identity.keys() and title_trace.keys() == product_map.keys(), 'private_audit_coverage_mismatch'
    text_lengths = {kind: Counter() for kind in ('product_title', 'history_body')}
    for product in products:
        parent = product['parent_asin']
        original = original_catalog[parent]
        assert set(product) == {'parent_asin', 'title', 'crop'} and product['crop'] == original['crop'], 'catalog_field_or_crop_mismatch'
        trace = title_trace[parent]
        assert trace['source_component_sha256'] == cleaning['catalog_sha256'] and trace['source_line'] == original['source_line'], 'catalog_private_source_mismatch'
        assert trace['json_pointer'] == '/metadata/title', 'catalog_pointer_mismatch'
        raw, processed = audit_text(original['metadata']['title'], product['title'], trace, 'product_title')
        text_lengths['product_title'].update(fields=1, raw_codepoints=raw, processed_codepoints=processed)
    db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE events (u TEXT, p TEXT, t INTEGER, r REAL)')
    db.executemany('INSERT INTO events VALUES (?,?,?,?)', [(r['review']['user_id'], r['review']['parent_asin'], r['timestamp_ms'], r['review']['rating']) for r in clean])
    db.execute('CREATE TABLE excluded (u TEXT PRIMARY KEY)')
    db.executemany('INSERT INTO excluded VALUES (?)', [(u,) for u in assignments])
    db.execute('CREATE TABLE background AS SELECT * FROM events e WHERE NOT EXISTS (SELECT 1 FROM excluded x WHERE x.u=e.u)')
    db.execute('CREATE INDEX background_time ON background(t)')
    pool = db.execute('SELECT COUNT(*),COUNT(DISTINCT u) FROM background').fetchone()
    assert pool == (52937, 51973), 'background_pool_mismatch'
    totals = Counter()
    candidates_lengths, seen_lengths, visible_lengths = [], [], []
    task_hashes = {}
    wire_tasks = {}
    probe_ids = {r['session_task_id'] for r in rows(ROOT / PROBE) if r['operation'] == 'model_request' and r['arguments'] == {}}
    root_keys = {'schema_version','task_id','catalog_version','text_policy_version','metadata_time_basis',
                'history_cutoff_exclusive_ms','request','history','seen_parent_asins','candidate_parent_asins','background_statistics'}
    for number, task in enumerate(rows(ROOT / main['components']['tasks']['path']), 1):
        task_id = task['task_id']
        assert task_id in identity and task_id not in task_hashes, 'duplicate_or_unknown_root'
        user = identity[task_id]
        account, evaluation, trace = qualifications[user], evaluations[task_id], task_trace[task_id]
        time = account['latest_timestamp_ms']
        assert set(task) == root_keys and task['schema_version'] == 'preference-model-input-1.0.0', 'task_schema_mismatch'
        assert task['catalog_version'] == 'grain-A-1.1.15' and task['text_policy_version'] == 'finite-text-1.0.0', 'task_versions_mismatch'
        assert task['metadata_time_basis'] == 'collection_snapshot' and task['history_cutoff_exclusive_ms'] == time < 1694550038852, 'time_or_snapshot_mismatch'
        assert task['request'] == {'source':'experiment_template','text':'根据较早正向评论和商品标题，对完整候选谷物商品按偏好排序。'}, 'fixed_request_mismatch'
        assert max(r['timestamp_ms'] for r in ledger[user]) == time, 'target_is_not_latest'
        seen = sorted({r['review']['parent_asin'] for r in ledger[user] if r['timestamp_ms'] < time}, key=lambda p:p.encode())
        candidates = [p for p in parents if p not in seen]
        assert set(account['seen_parent_asins']) == set(seen) and task['seen_parent_asins'] == seen, 'complete_raw_seen_mismatch'
        assert task['candidate_parent_asins'] == candidates and account['target_parent_asin'] in candidates, 'full_candidate_or_natural_target_mismatch'
        target = [r for r in text_ledger[user] if r['timestamp_ms'] == time]
        assert len(target) == 1 and target[0]['review']['parent_asin'] == account['target_parent_asin'], 'private_target_source_mismatch'
        assert evaluation['source_user_id'] == user and evaluation['split'] == assignments[user], 'private_identity_or_split_mismatch'
        assert evaluation['target_timestamp_ms'] == time and evaluation['target_parent_asin'] == account['target_parent_asin'], 'private_target_mismatch'
        assert evaluation['target_rating'] == target[0]['review']['rating'] and evaluation['target_review'] == target[0]['review'], 'private_target_review_mismatch'
        assert evaluation['target_source_references'] == target[0]['source_references'], 'private_target_trace_mismatch'
        assert evaluation['reference_answer'] == {'positive_parent_asins':[account['target_parent_asin']], 'other_candidates':'unobserved_unlabeled'}, 'reference_answer_mismatch'
        history = sorted([r for r in text_ledger[user] if r['timestamp_ms'] < time and r['review']['rating'] >= 4],
                         key=lambda r: (r['timestamp_ms'], r['review']['parent_asin'].encode(), encoded(r['review'])))
        assert len(task['history']) == len(history) == len(trace['history']) and history, 'complete_history_mismatch'
        assert {r['review']['parent_asin'] for r in history} == set(account['prior_positive_parent_asins']), 'history_qualification_mismatch'
        for i, (actual, source, text_trace) in enumerate(zip(task['history'], history, trace['history'])):
            assert set(actual) == {'parent_asin','timestamp_ms','rating','text'}, 'history_schema_mismatch'
            assert actual['parent_asin'] == source['review']['parent_asin'] and actual['timestamp_ms'] == source['timestamp_ms'] < time, 'history_association_or_time_mismatch'
            assert type(actual['rating']) in (int,float) and actual['rating'] == source['review']['rating'] in (4,5), 'historical_rating_mismatch'
            assert text_trace['source_component_sha256'] == cleaning['text_sha256'] and text_trace['source_references'] == source['source_references'], 'history_private_source_mismatch'
            assert text_trace['json_pointer'] == f'/history/{i}/text', 'history_pointer_mismatch'
            raw, processed = audit_text(source['review']['text'], actual['text'], text_trace, 'history_body', user)
            text_lengths['history_body'].update(fields=1, raw_codepoints=raw, processed_codepoints=processed)
            totals['rating_' + str(int(actual['rating']))] += 1
        sql = {p:(n,u,pos) for p,n,u,pos in db.execute('SELECT p,COUNT(*),COUNT(DISTINCT u),COUNT(DISTINCT CASE WHEN r>=4 THEN u END) FROM background WHERE t<? GROUP BY p', (time,))}
        actual_stats = task['background_statistics']
        assert [s['parent_asin'] for s in actual_stats] == candidates, 'background_candidate_coverage_mismatch'
        for stat in actual_stats:
            assert set(stat) == {'parent_asin','interaction_count','account_count','positive_account_count'}, 'background_schema_mismatch'
            assert tuple(stat[k] for k in ('interaction_count','account_count','positive_account_count')) == sql.get(stat['parent_asin'], (0,0,0)), 'independent_sql_background_mismatch'
        visible = db.execute('SELECT COUNT(*),MIN(t),MAX(t) FROM background WHERE t<?', (time,)).fetchone()
        assert (trace['background']['visible_events'], trace['background']['min_timestamp_ms'], trace['background']['max_timestamp_ms']) == visible, 'private_background_time_evidence_mismatch'
        assert trace['background']['pool_events'] == pool[0], 'private_background_pool_mismatch'
        assert trace['background']['excluded_accounts_sha256'] == hashlib.sha256(encoded(sorted(assignments))).hexdigest(), 'private_exclusion_digest_mismatch'
        totals['root_tasks'] += 1
        totals[assignments[user] + '_accounts'] += 1
        totals['history_events'] += len(history)
        totals['candidate_references'] += len(candidates)
        candidates_lengths.append(len(candidates)); seen_lengths.append(len(seen)); visible_lengths.append(visible[0])
        task_hashes[task_id] = text_hash(encoded(task).decode())
        if task_id in probe_ids: wire_tasks[task_id] = task
        if number % 400 == 0: print(json.dumps({'checkpoint':'full_row_sql_and_text','roots_checked':number}), flush=True)
    db.close()
    assert list(task_hashes) == sorted(identity) and len(task_hashes) == 1603, 'root_order_or_coverage_mismatch'
    assert totals == {'root_tasks':1603,'dev_accounts':320,'test_accounts':1283,'history_events':1845,
                      'candidate_references':2393008,'rating_4':194,'rating_5':1651}, 'expected_real_totals_mismatch'
    assert (min(candidates_lengths),max(candidates_lengths),min(seen_lengths),max(seen_lengths)) == (1488,1493,1,6), 'candidate_or_seen_extrema_mismatch'
    for kind, lengths in text_lengths.items():
        assert all(main['text_summary'][kind][k] == v for k,v in lengths.items()), 'receipt_text_totals_mismatch'
    probes, requests = list(rows(ROOT / main['components']['access_probe']['path'])), list(rows(ROOT / PROBE))
    assert len(probes) == len(requests) == 26, 'probe_coverage_mismatch'
    canaries = [(ROOT / 'data/task-inputs/preference-task-1.0.1' / name).read_text('utf-8').strip()
                for name in ('private-canary.txt','old-index/canary.txt','old-cache/canary.txt')]
    for expected, actual in zip(requests, probes):
        if expected['operation'] == 'model_request' and expected['arguments'] == {} and expected['session_task_id'] in wire_tasks:
            response = actual['response']
            assert response['status'] == 'ok' and set(response['request']) == {'messages','tools'}, 'actual_request_channels_mismatch'
            request = response['request']
            assert request['tools'] == [] and len(request['messages']) == 1 and request['messages'][0]['role'] == 'user', 'actual_messages_or_tools_mismatch'
            payload = json.loads(request['messages'][0]['content'])
            task = wire_tasks[expected['session_task_id']]
            needed = set(task['candidate_parent_asins']) | {h['parent_asin'] for h in task['history']}
            assert payload == {**task,'products':[product_map[p] for p in parents if p in needed]}, 'actual_wire_payload_mismatch'
        else:
            assert actual['response'] == {'status':'access_denied'}, 'actual_dispatch_denial_mismatch'
        assert not any(c in json.dumps(actual) for c in canaries), 'private_canary_reachable'
    tree = ast.parse((ROOT / 'preference_access.py').read_text('utf-8'))
    imports = [n for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]
    assert len(imports) == 1 and isinstance(imports[0],ast.Import) and [a.name for a in imports[0].names] == ['json'], 'api_channel_has_extra_imports'
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ('open','exec','eval','__import__','getattr') for n in ast.walk(tree)), 'api_channel_has_host_io_or_dynamic_dispatch'
    assert main['capabilities'] == {'host_io':False,'tools':[],'indices':[]}, 'capability_contract_mismatch'
    assert main['formal_package_status'] == main['sim_status'] == main['interaction_training_status'] == 'not_built', 'unapproved_stage_executed'
    assert main['model_execution_status'] == 'not_run' and main['sample_sufficiency'] == 'not_determined', 'invalid_execution_or_sufficiency_claim'
    for component in main['components'].values():
        path = ROOT / component['path']
        assert digest(path) == component['sha256'], 'component_hash_mismatch'
        with path.open('rb') as stream:
            assert not stream.read(3).startswith(b'\xef\xbb\xbf'), 'stable_component_has_bom'
            stream.seek(0)
            for line in stream:
                assert b'\r' not in line and line.endswith(b'\n') and encoded(json.loads(line)) == line, 'stable_component_serialization_mismatch'
    return {'status':'passed','counts':dict(totals),'background_pool_events':pool[0],'background_pool_accounts':pool[1],
            'removed_evaluation_events':len(clean)-pool[0],'candidate_min':min(candidates_lengths),'candidate_max':max(candidates_lengths),
            'background_visible_min':min(visible_lengths),'background_visible_max':max(visible_lengths),
            'text_totals':{k:dict(v) for k,v in text_lengths.items()},'checked_background_rows':totals['candidate_references'],
            'api_probe_requests':len(probes),'api_allowed_requests':1,'api_denials':len(probes)-1,
            'api_scope':'request_construction_and_default_deny_dispatch_only','os_acl_isolation_claim':False,
            'private_canary_hits':0,'api_channel_host_io_imports':0}, evaluations, qualifications, clean, valid


def target_mutation(main, evaluations, qualifications, clean, valid, temporary):
    """Private metamorphic fixture copied from real data; official inputs untouched."""
    source = temporary / 'mutated-input'
    source.mkdir()
    original_clean, original_split, config = [load(ROOT / p) for p in (CLEAN,SPLIT,CONFIG)]
    chosen = next(r for r in evaluations.values() if r['split'] == 'dev')
    user, time = chosen['source_user_id'], chosen['target_timestamp_ms']
    original_catalog = load(ROOT / original_clean['catalog_record_path'])
    catalog_parents = sorted(r['parent_asin'] for r in rows(ROOT / original_catalog['catalog_path']))
    parent = next(p for p in catalog_parents if p not in qualifications[user]['seen_parent_asins'] and p != chosen['target_parent_asin'])
    new_references = None
    for collection in (clean,valid):
        for r in collection:
            if r['review']['user_id'] == user and r['timestamp_ms'] == time:
                r['review'].update(parent_asin=parent, asin='synthetic-target-variant',
                    rating=4.0 if chosen['target_rating'] == 5 else 5.0,
                    text='SYNTHETIC_TARGET_CHANGE_NEVER_USED_BY_INPUT')
                for ref in r['source_references']: ref['line_sha256'] = text_hash(encoded(r['review']).decode())
                new_references = r['source_references']
    accounts = list(rows(ROOT / original_clean['accounts_path']))
    for a in accounts:
        if a['user_id'] == user: a.update(target_parent_asin=parent, target_source_references=new_references)
    modified = {'clean':clean,'text':valid,'accounts':accounts}
    for name in ('clean','text','accounts','products','quarantine','audit'):
        old = ROOT / original_clean[name + '_path']
        if name in modified:
            path = source / 'data' / (name + '.jsonl')
            save_rows(path, modified[name])
        else: path = old
        original_clean[name + '_path'] = str(path)
        original_clean[name + '_sha256'] = digest(path)
    # A copied catalog record must still resolve its unchanged catalog from ROOT.
    original_catalog['catalog_path'] = str(ROOT / original_catalog['catalog_path'])
    catalog_path = source / 'records/catalog/fixture-catalog.json'
    save(catalog_path, original_catalog)
    original_clean.update(catalog_record_path=str(catalog_path), catalog_record_sha256=digest(catalog_path))
    original_clean['rules_path'] = str(ROOT / original_clean['rules_path'])
    clean_path = source / CLEAN
    save(clean_path,original_clean)
    ca = load(ROOT / config['upstream_acceptances']['cleaning']['path'])
    ca['dependencies_sha256'][CLEAN] = digest(clean_path)
    ca['component_sha256'] = {n:original_clean[n+'_sha256'] for n in ('clean','text','accounts','products','quarantine','audit')}
    erratum = load(ROOT / config['upstream_acceptances']['cleaning_erratum']['path'])
    erratum.update(affected_record_path=CLEAN,affected_record_sha256=digest(clean_path))
    for n, check in erratum['component_format_checks'].items():
        check.update(path=original_clean[n+'_path'],sha256=original_clean[n+'_sha256'])
    original_split['cleaning_record_sha256'] = digest(clean_path)
    for n in ('accounts','exposure'): original_split[n+'_path'] = str(ROOT / original_split[n+'_path'])
    split_path = source / SPLIT
    save(split_path, original_split)
    sa = load(ROOT / config['upstream_acceptances']['split']['path'])
    sa['dependencies_sha256'][SPLIT] = digest(split_path)
    for name, value in (('cleaning',ca),('cleaning_erratum',erratum),('split',sa)):
        path = source / 'records' / (name + '-fixture-acceptance.json')
        save(path,value)
        config['upstream_acceptances'][name] = {'path':str(path),'sha256':digest(path)}
    config['identity_key']['path'] = str(ROOT / config['identity_key']['path'])
    config_path = source / CONFIG
    save(config_path,config)
    output = temporary / 'mutated-output'
    result = invoke(clean_path,split_path,config_path,output,ROOT/PROBE,'ticket08-1.0.1-target-mutation-cli.json')
    compared = compare_components(ROOT,main,output,result,('catalog','tasks','model_manifest','access_probe'))
    assert digest(ROOT/main['components']['evaluation']['path']) != digest(output/result['components']['evaluation']['path']), 'mutation_did_not_change_private_evaluation'
    return {'status':'passed','mutated_accounts':1,'fixture_origin':'private_copy_of_real_dev_target',
            'changed_fields':['target_parent_asin','target_variant','target_rating','target_text','target_source_binding'],
            'held_fixed':['account','HMAC_key','version','T','history','seen','catalog','07_assignments','background'],
            'all_model_components_and_actual_request_probe_unchanged':compared,'private_evaluation_changed':True,
            'official_source_writes':0,'model_calls':0}


def main():
    assert Path(sys.executable).resolve() == ROOT / '.conda/envs/Thesis/python.exe', 'wrong_environment'
    main_record = load(ROOT / MAIN)
    assert sys.argv[1:] in ([],['--resume-target']), 'unknown_diagnostic_arguments'
    resume = bool(sys.argv[1:])
    if resume:
        assert load(VERIFY/'ticket08-1.0.1-independent-full-check.json')['status'] == 'passed'
        assert load(VERIFY/'ticket08-1.0.1-reproduction-check.json')['status'] == 'passed'
        cleaning = load(ROOT/CLEAN)
        evaluations = {r['task_id']:r for r in rows(ROOT/main_record['components']['evaluation']['path'])}
        qualifications = {r['user_id']:r for r in rows(ROOT/cleaning['accounts_path']) if r['status']=='qualified'}
        clean,valid = [list(rows(ROOT/cleaning[n+'_path'])) for n in ('clean','text')]
    else:
        audit, evaluations, qualifications, clean, valid = full_audit(main_record)
        save(VERIFY/'ticket08-1.0.1-independent-full-check.json',audit)
        print(json.dumps({'checkpoint':'full_row_audit_passed','counts':audit['counts']}),flush=True)
    with tempfile.TemporaryDirectory(prefix='ticket08-independent-',dir=ROOT/'.tmp') as temp:
        temporary = Path(temp)
        if not resume:
            output = temporary / 'fresh-output'
            reproduction = invoke(ROOT/CLEAN,ROOT/SPLIT,ROOT/CONFIG,output,ROOT/PROBE,'ticket08-1.0.1-reproduction-cli.json')
            compared = compare_components(ROOT,main_record,output,reproduction)
            save(VERIFY/'ticket08-1.0.1-reproduction-check.json', {'status':'passed','fresh_empty_root':True,
                 'same_frozen_key':True,'stable_components':compared,'runtime_metadata_compared':False})
            print(json.dumps({'checkpoint':'fresh_root_byte_reproduction_passed','components':len(compared)}),flush=True)
        mutation = target_mutation(main_record,evaluations,qualifications,clean,valid,temporary)
        save(VERIFY/'ticket08-1.0.1-target-mutation-check.json',mutation)
        print(json.dumps({'checkpoint':'private_target_mutation_passed','all_model_components_identical':True}),flush=True)
    protection = load(ROOT/'.tmp/ticket08-implementation-protection.json')
    changed = [p for p,h in protection['sha256'].items() if not Path(p).is_file() or digest(p) != h]
    assert not changed and len(protection['sha256']) == 707, 'protected_source_changed'
    assert digest(ROOT/'.scratch/data-preparation/ticket08-stage1-field-isolation-review-draft-20261015.md') == '21c7cf2aa1b06c520564c5cfc18cd45eaab6d9f1e403bb7731ad94d58930b22a', 'approved_draft_changed'
    save(VERIFY/'ticket08-1.0.1-protection-check.json', {'status':'passed','protected_files':707,'changed_files':0,
         'approved_draft_sha256':'21c7cf2aa1b06c520564c5cfc18cd45eaab6d9f1e403bb7731ad94d58930b22a',
         'baseline':protection['baseline'],'authorized_existing_changes':protection['authorized_existing_changes']})
    print(json.dumps({'status':'independent_acceptance_checks_passed','protected_files':707,'model_calls':0}),flush=True)


if __name__ == '__main__':
    main()
