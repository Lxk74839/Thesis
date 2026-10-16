"""Bind the reused whole-source checks and accepted waterfall; no source rescan."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / '.scratch/data-preparation/verification/ticket14-20261016'
PREFIX = '.scratch/data-preparation/verification/'


def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def digest(name):
    with (ROOT / name).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


names = [PREFIX + n for n in ('metadata-source-check.json', 'review-check.json',
 'grain-A-1.1.15-check.json', 'grain-A-1.1.15-reviews-check.json',
 'semantic-sample-grain-A-1.1.15-acceptance.md', 'ticket08-1.0.1-target-mutation-check.json')]
names += ['records/sources/amazon-2023-grocery-metadata.json',
 'records/sources/amazon-2023-grocery-reviews.json',
 '.scratch/data-preparation/scope-revision-results-grain-A-1.1.15.md',
 '.scratch/data-preparation/ticket12-final-experiment-protocol-review-20261016.md',
 '.scratch/data-preparation/ticket12-final-experiment-protocol-confirmation-20261016.md']
subprocess.run(['git', 'diff', '--exit-code', '3c565eb', '--', *names], cwd=ROOT, check=True)
meta, review = [load(f'records/sources/amazon-2023-grocery-{kind}.json') for kind in ('metadata', 'reviews')]
meta_check, review_check, cat_check, selected_check = [load(n) for n in names[:4]]
selected = load('records/reviews/grain-A-1.1.15-review-diagnostics-1.0.0.json')
cat = load('records/catalog/grain-A-1.1.15.json')
assert digest(names[6]) == meta_check['source_record_sha256']
assert digest(names[7]) == selected['source_record_sha256']
assert meta_check['independent_raw_sha256'] == meta['download']['sha256'] == cat['source_sha256']
assert review_check['raw_sha256'] == review_check['independent_powershell_sha256'] == review['download']['sha256'] == selected['source_sha256']
assert cat_check['catalog_sha256'] == cat['catalog_sha256']
assert cat_check['migration_sha256'] == cat['migration_sha256']
assert cat_check['counts'] == cat['counts'] and cat_check['source_rows'] == meta['scan']['records']
assert selected_check['extract_sha256'] == selected['extract_sha256']
assert selected_check['matched_reviews'] == selected['raw']['reviews']
assert selected_check['source_rows'] == review['scan']['records']
assert selected_check['unique_accounts'] == selected['raw']['unique_accounts']
assert digest(names[9]) == 'd2b22af021b2e3b7a25046927c122ba653fe52691bc90c964b5f5edf6b7da4ca'
result = {'status': 'passed', 'baseline': '3c565eb',
 'files': [{'path': n, 'sha256': digest(n)} for n in names],
 'source_binding': 'source checks -> exact source records -> compressed digests -> catalog/extraction checks',
 'source_scans_reexecuted': 0,
 'qualification_waterfall': [
  {'stage': 'distinct_source_accounts', 'accounts': 53576},
  {'stage': 'valid_time_and_unique_latest_parent', 'accounts': 53576},
  {'stage': 'latest_unseen_parent', 'accounts': 53300},
  {'stage': 'latest_unseen_rating_ge4_nonblank_text', 'accounts': selected_check['candidate_potential_accounts']},
  {'stage': 'accepted_positive_history_qualified', 'accounts': 1603},
  {'stage': 'development', 'accounts': 320}, {'stage': 'test_pool', 'accounts': 1283}],
 'waterfall_basis': 'accepted04/05 original chronology diagnostics plus accepted06 final exclusions; no new rule',
 'source_review_anomaly': {'retained_full_source_rating_zero_rows': 1, 'selected_invalid_rating_rows': selected['quality']['invalid_rating_rows']}}
with (OUT / 'upstream-source-reuse.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
    stream.write('\n')
print(json.dumps({'status': result['status'], 'extra_bound_files': len(names),
 'source_scans_reexecuted': 0, 'waterfall': result['qualification_waterfall']}))
