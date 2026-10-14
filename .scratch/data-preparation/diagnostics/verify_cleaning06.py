"""Independent SQL reconciliation of the frozen 05 extraction; no production imports."""

from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[3]
VERSION = sys.argv[1]
record_path = ROOT / 'records/cleaning' / ('grain-A-1.1.15-' + VERSION + '.json')
report = json.loads(record_path.read_text('utf-8'))
source = json.loads((ROOT / report['source_record_path']).read_text('utf-8'))
catalog = json.loads((ROOT / report['catalog_record_path']).read_text('utf-8'))
rules = json.loads((ROOT / report['rules_path']).read_text('utf-8'))


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


assert report['status'] == 'cleaning_complete'
assert rules['cutoff_exclusive_ms'] == 1694550038852 and rules['positive_min_rating'] == 4 and rules['minimum_prior_positive_products'] == 1
assert report['rules_sha256'] == digest(ROOT / report['rules_path'])
assert report['source_record_sha256'] == digest(ROOT / report['source_record_path'])
assert report['catalog_record_sha256'] == digest(ROOT / report['catalog_record_path'])
assert report['catalog_sha256'] == catalog['catalog_sha256'] == source['catalog_sha256']
for name, expected in report['producer_sha256'].items():
    assert digest(ROOT / name) == expected
for name in ('clean', 'text', 'quarantine', 'products', 'accounts', 'audit'):
    assert digest(ROOT / report[name + '_path']) == report[name + '_sha256']
assert digest(ROOT / source['extract_path']) == source['extract_sha256'] == report['source_extract_sha256']
assert digest(ROOT / source['references_path']) == source['references_sha256']
assert digest(ROOT / catalog['catalog_path']) == catalog['catalog_sha256']
parents = {json.loads(line)['parent_asin'] for line in (ROOT / catalog['catalog_path']).read_text('utf-8').splitlines()}
assert len(parents) == 1494 == catalog['counts']['included']
raw_lines = (ROOT / source['extract_path']).read_bytes().splitlines(keepends=True)
refs = [json.loads(line) for line in (ROOT / source['references_path']).read_text('utf-8').splitlines()]
original = {}
reference = {}
database = sqlite3.connect(':memory:')
database.execute('CREATE TABLE reviews(n INTEGER PRIMARY KEY,user TEXT,parent TEXT,stamp INTEGER,rating REAL,text TEXT,object TEXT,quad TEXT,timefacts TEXT)')
for ordinal, (line, ref) in enumerate(zip(raw_lines, refs, strict=True), 1):
    row = json.loads(line)
    number = ref['source_line']
    assert ref['selected_row'] == ordinal and ref['line_sha256'] == hashlib.sha256(line).hexdigest()
    assert row['parent_asin'] in parents and type(row['timestamp']) is int
    assert all(isinstance(row[key], str) and row[key].strip() for key in ('user_id', 'asin'))
    assert isinstance(row['text'], str) and type(row['rating']) in (int, float) and 1 <= row['rating'] <= 5
    # The accepted real snapshot has no invalid facts; negative cases are public CLI fixtures.
    original[number], reference[number] = row, ref
    object_text = json.dumps(row, sort_keys=True)
    quad = json.dumps({k: v for k, v in row.items() if k not in ('user_id', 'parent_asin', 'timestamp', 'text')}, sort_keys=True)
    timefacts = json.dumps({k: v for k, v in row.items() if k not in ('user_id', 'parent_asin', 'timestamp')}, sort_keys=True)
    database.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?,?,?,?)', (number, row['user_id'], row['parent_asin'], row['timestamp'], row['rating'], row['text'], object_text, quad, timefacts))
assert len(original) == 56903 == source['raw']['reviews']
assert database.execute('SELECT count(distinct user) FROM reviews').fetchone()[0] == 53576
assert source['scan']['lines'] == 14318520 and source['scan']['gzip_verified']
database.execute('CREATE INDEX account_time ON reviews(user,stamp)')
database.execute('CREATE INDEX complete_object ON reviews(object)')
database.create_function('nonblank', 1, lambda value: int(bool(value.strip())))
conflict_quads = database.execute('SELECT user,parent,stamp,text FROM reviews GROUP BY user,parent,stamp,text HAVING count(distinct quad)>1').fetchall()
conflict_times = database.execute('SELECT user,parent,stamp FROM reviews GROUP BY user,parent,stamp HAVING count(distinct timefacts)>1').fetchall()
assert conflict_quads == conflict_times == []
assert database.execute('SELECT count(*) FROM reviews WHERE stamp>=1694550038852').fetchone()[0] == 0
groups = list(database.execute('SELECT min(n),object,count(*) FROM reviews GROUP BY object ORDER BY min(n)'))
assert len(groups) == 56427 and sum(size - 1 for _, _, size in groups) == 476
expected_clean = []
for number, obj, _ in groups:
    members = [n for (n,) in database.execute('SELECT n FROM reviews WHERE object=? ORDER BY n', (obj,))]
    stamp = original[number]['timestamp']
    utc = (datetime.fromtimestamp(stamp // 1000, timezone.utc) + timedelta(milliseconds=stamp % 1000)).isoformat(timespec='milliseconds')
    expected_clean.append({'review': original[number], 'source_references': [reference[n] for n in members], 'timestamp_ms': stamp, 'timestamp_utc': utc})


def artifact(name):
    return [json.loads(line) for line in (ROOT / report[name + '_path']).read_text('utf-8').splitlines()]


assert artifact('clean') == expected_clean
expected_text = [entry for entry in expected_clean if entry['review']['text'].strip()]
assert len(expected_text) == 56363 and artifact('text') == expected_text
assert artifact('quarantine') == []
raw_products = Counter(row['parent_asin'] for row in original.values())
clean_products = Counter(entry['review']['parent_asin'] for entry in expected_clean)
text_products = Counter(entry['review']['parent_asin'] for entry in expected_text)
assert artifact('products') == [{'parent_asin': p, 'raw_reviews': raw_products[p], 'clean_reviews': clean_products[p], 'text_reviews': text_products[p]} for p in sorted(parents)]
representatives = {ref['source_line']: entry['source_references'][0]['source_line'] for entry in expected_clean for ref in entry['source_references']}
audit = artifact('audit')
assert len(audit) == len(original)
for entry, (number, row) in zip(audit, original.items(), strict=True):
    primary = representatives[number]
    duplicate = number != primary
    assert entry == {'source_reference': reference[number], 'disposition': 'duplicate_copy' if duplicate else 'retained',
                     'reasons': ['exact_object_duplicate'] if duplicate else [], 'representative_source_line': primary,
                     'text_exclusion_reasons': [] if row['text'].strip() else ['blank_text']}
accounts = artifact('accounts')
assert len(accounts) == 53576
expected_reasons = Counter()
expected_qualified = 0
for entry, (user, latest) in zip(accounts, database.execute('SELECT user,max(stamp) FROM reviews GROUP BY user ORDER BY user'), strict=True):
    targets = list(database.execute('SELECT n,parent,object,rating,text FROM reviews WHERE user=? AND stamp=? ORDER BY n', (user, latest)))
    target_parents = {parent for _, parent, _, _, _ in targets}
    seen = {parent for (parent,) in database.execute('SELECT DISTINCT parent FROM reviews WHERE user=? AND stamp<?', (user, latest))}
    positive = {parent for (parent,) in database.execute('SELECT DISTINCT parent FROM reviews WHERE user=? AND stamp<? AND rating>=4 AND nonblank(text)', (user, latest))}
    reason = ('multiple_latest_parents' if len(target_parents) != 1 else 'latest_fact_conflict' if len({obj for _, _, obj, _, _ in targets}) != 1 else
              'latest_seen_product' if targets[0][1] in seen else 'latest_not_positive_text' if targets[0][3] < 4 or not targets[0][4].strip() else
              'insufficient_positive_history' if len(positive) < 1 else None)
    if reason:
        expected_reasons[reason] += 1
    else:
        expected_qualified += 1
    assert entry == {'user_id': user, 'status': 'excluded' if reason else 'qualified', 'reasons': [reason] if reason else [],
                     'latest_timestamp_ms': latest, 'target_parent_asin': targets[0][1] if len(target_parents) == 1 else None,
                     'target_source_references': [reference[n] for n, _, _, _, _ in targets], 'seen_parent_asins': sorted(seen),
                     'prior_positive_parent_asins': sorted(positive), 'prior_positive_product_count': len(positive)}
assert expected_qualified == 1603
assert dict(expected_reasons) == report['account_exclusions']
assert report['counts'] == {'raw_accounts': 53576, 'qualified_accounts': 1603, 'clean_reviews': 56427, 'text_reviews': 56363,
                            'quarantined_objects': 0, 'quarantined_source_rows': 0, 'catalog_products': 1494}
assert report['duplicates'] == {'groups': 443, 'excess_rows': 476}
assert report['window'] == {'cutoff_exclusive_ms': 1694550038852, 'raw_rows': 56903, 'in_window_rows': 56903, 'outside_window_rows': 0}
assert report['unknown_time_rows'] == 0
assert report['formal_clean_status'] == 'built' and report['user_qualification_status'] == 'complete'
assert report['user_split_status'] == report['sim_status'] == report['formal_package_status'] == 'not_built'
assert report['model_input_status'] == 'not_released' and report['sample_sufficiency'] == 'not_determined'
protection = json.loads((ROOT / '.scratch/data-preparation/verification/ticket06-protection.json').read_text('utf-8'))
for relative, expected in protection['protected_sha256'].items():
    assert digest(ROOT / relative) == expected, relative
result = {'status': 'independent_cleaning_qualification_audit_passed', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
          'rules_version': VERSION, 'source_full_review_rows_reused': 14318520, 'rows_read_for_06': len(original),
          'clean_reviews': len(expected_clean), 'text_reviews': len(expected_text), 'catalog_products': len(parents),
          'raw_accounts': len(accounts), 'qualified_accounts': expected_qualified, 'excluded_accounts': len(accounts) - expected_qualified,
          'account_exclusions': expected_reasons, 'text_accounts': len({e['review']['user_id'] for e in expected_text}),
          'protected_files_unchanged': len(protection['protected_sha256']), 'original_materials_unchanged': protection['original_count'],
          'verification_program_sha256': digest(Path(__file__)), 'cleaning_record_sha256': digest(record_path),
          'oracle': 'Independent SQLite complete-object grouping, chronology and memberships; all output rows, references and source dispositions checked.',
          'limitations': 'Actual accepted 05 snapshot has no invalid facts or conflicts; negative cases covered by public CLI fixtures. Account qualification is not statistical sufficiency or a user split.'}
destination = ROOT / '.scratch/data-preparation/verification' / (VERSION + '-independent-check.json')
assert not destination.exists()
destination.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n', 'utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
