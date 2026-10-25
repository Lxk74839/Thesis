"""Final local integrity and document checks; no provider access or experiment rerun."""
import hashlib
import json
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as E
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from compact_experiment import OUTPUT, load_config

cfg = load_config()
r = json.loads((HERE / 'results.json').read_bytes())
assert hashlib.sha256(Path(r['evaluation_summary_ref']['path']).read_bytes()).hexdigest() == r['evaluation_summary_ref']['sha256']
refs = [json.loads(line) for line in (OUTPUT / 'artifacts.jsonl').read_bytes().splitlines()]
assert len({ref['path'] for ref in refs}) == len(refs)
for ref in refs:
    raw = (ROOT / ref['path']).read_bytes()
    assert len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256']
assert not list(OUTPUT.rglob('*.pending'))
keys = {json.loads(line)['task_key'] for line in (ROOT / cfg['plan_directory'] / 'tasks.jsonl').read_bytes().splitlines()}
assert keys == {p.stem for p in (OUTPUT / 'tasks').glob('*.json')} and len(keys) == 5000
assert len(list((OUTPUT / 'calls').glob('*.intent.json'))) == len(list((OUTPUT / 'calls').glob('*.result.json'))) == 676
assert r['evaluation_counts'] == {'executed_failed': 248, 'missing_records': 0, 'not_started': 0,
    'pipeline_errors': 0, 'planned_tasks': 5000, 'reference_NA': 546, 'unresolved': 0}
doc = ROOT / 'manuscript/论文初稿_compact正式结果_9d0c8eb7.docx'
check = json.loads((HERE / 'manuscript-check.json').read_bytes())
assert hashlib.sha256(doc.read_bytes()).hexdigest() == check['sha256']
content = json.loads((HERE / 'manuscript-content.json').read_bytes())
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
with zipfile.ZipFile(doc) as z:
    body = E.fromstring(z.read('word/document.xml')).find(W + 'body')
    tables = body.findall(W + 'tbl')[-4:]
    expected = [b['rows'] for b in content['insert_after_111'] if 'rows' in b]
    for table, rows in zip(tables, expected):
        actual = [[''.join(cell.itertext()) for cell in row.findall(W + 'tc')] for row in table.findall(W + 'tr')]
        assert actual == rows
    assert '正式运行尚未开展' not in ''.join(body.itertext())
pages = json.loads((HERE / 'final-render-hashes.json').read_bytes())
assert len(pages) == 17
for name, digest in pages.items():
    assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest
source = ROOT / 'manuscript/论文初稿_推荐算法与精简实验修订版_20261023.docx'
assert hashlib.sha256(source.read_bytes()).hexdigest() == 'cd2ef686719d765c9c7148408803bd257153c4ed29ba03ba7b9a1879d14c3647'
assert hashlib.sha256(Path('E:/工作/成果/小论文/初稿/论文初稿.docx').read_bytes()).hexdigest() == 'e09436082eb3cea837e81b89551da6d36b6e9f0ce213eb2d94065329bbc3e027'
experiment_bytes = sum(p.stat().st_size for p in OUTPUT.rglob('*') if p.is_file())
scratch_bytes = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
total = experiment_bytes + scratch_bytes + doc.stat().st_size
assert total < cfg['max_new_bytes'] and r['resources']['shared_budget_elapsed_seconds'] < 24 * 3600
result = {'terminal': 'complete_with_retained_failures', 'checked_epoch': time.time(),
    'configuration_id': cfg['configuration_id'], 'bound_code_and_plan_files': 'PASS',
    'immutable_receipts_checked': len(refs), 'task_matrix': '5000/5000', 'request_receipts': '676/676',
    'independent_evaluation': 'PASS; 248 failed tasks retained; zero missing/unresolved/pipeline errors',
    'manuscript_tables_match_results': True, 'math_paragraphs_preserved': 17,
    'numbered_main_formulas_preserved': 7, 'pages_visually_checked': list(range(1, 18)),
    'final_visual_rechecks': [7, 13], 'source_documents_unchanged': True,
    'experiment_output_bytes': experiment_bytes, 'execution_scratch_bytes': scratch_bytes,
    'final_docx_bytes': doc.stat().st_size, 'total_new_artifact_bytes_at_snapshot': total,
    'storage_scope': 'experiment/evaluation output + this execution scratch including QA + final DOCX; excludes pre-existing sources',
    'docx': str(doc), 'docx_sha256': check['sha256'], 'pricing': None, 'cost': None,
    'resume_required': False, 'additional_provider_calls': 0}
(HERE / 'final-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
