"""Validate the confirmed meeting deliverables and create a portable archive."""
import csv
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(r'D:\Work\Codex\Project\Thesis')
PACK = ROOT / 'reports/组会完整材料_商品评论与生命周期_20261024'
BUILD = ROOT / '.scratch/meeting-evidence-20261024'
ARCHIVE = ROOT / 'reports/组会完整材料_含商品级数据代码提示词与运行结果_20261024.zip'

def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

data = PACK / '01_商品评论与生命周期数据'
columns, shown = read_csv(data / '01_商品评论与生命周期_100行展示.csv')
full_columns, full = read_csv(data / '02_商品评论与生命周期_完整123条.csv')
_, history = read_csv(PACK / '05_补充关系表/02_历史评论.csv')
_, dictionary = read_csv(data / '03_属性字段说明.csv')
assert len(columns) == 42 and columns == full_columns
assert [r['列名'] for r in dictionary] == columns
assert len(shown) == 100 and len(full) == len(history) == 123
assert len({r['用户编号'] for r in full}) == len({r['用户编号'] for r in shown}) == 100
assert all(None not in r and None not in r.values() for r in full)
for actual, original in zip(full, history):
    for output_field, input_field in [
        ('用户编号', '用户编号'), ('商品标识', '商品标识'),
        ('商品名称', '商品标题'), ('商品评论_完整文本', '评论文本'),
        ('评分', '评分'), ('评论时间UTC', '评论时间UTC')
    ]:
        assert actual[output_field] == original[input_field]
    assert actual['SIM生命周期阶段数'] == '6'
    assert actual['生命周期来源'] == 'SIM 同商品模拟供应链'
    assert actual['SIM批次编号'] and actual['SIM采收地区'] and actual['SIM检验结论']
latest = {}
for row in full:
    if row['用户编号'] not in latest or row['评论时间UTC'] > latest[row['用户编号']]['评论时间UTC']:
        latest[row['用户编号']] = row
assert all(row == latest[row['用户编号']] for row in shown)

code = PACK / '02_代码与离线运行'
manifest = json.loads((code / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
assert len(manifest['files']) == 45
for item in manifest['files']:
    snapshot = code / 'src_snapshot' / item['source']
    assert sha(snapshot) == item['sha256'] == sha(ROOT / item['source'])
inputs = code / 'replay_inputs'
input_manifest = json.loads((inputs / 'MANIFEST.json').read_text(encoding='utf-8'))
assert len(input_manifest['profiles']) == 300 and len(input_manifest['scenes']) == 18
for kind in ('profiles', 'scenes'):
    for item in input_manifest[kind]:
        assert sha(inputs / kind / item['file']) == item['sha256']
with (inputs / 'expected_results.jsonl').open(encoding='utf-8') as stream:
    assert sum(1 for line in stream if line.strip()) == 5000

replay = PACK / '04_运行截图与结果/本地重放'
result = json.loads((replay / 'replay-result.json').read_text(encoding='utf-8'))
assert result['tasks'] == result['matched_original_tasks'] == 5000
assert result['statuses'] == {'ok': 4752, 'failed_model': 248}
assert result['new_model_api_calls'] == 0 and result['network_or_child_attempts'] == []
assert len(read_csv(replay / '01_任务重放核对.csv')[1]) == 5000
assert len(read_csv(replay / '02_实际重放推荐商品.csv')[1]) == 47520

namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
documents = sorted(PACK.glob('*.docx'))
assert len(documents) == 2
for document in documents:
    with zipfile.ZipFile(document) as word:
        xml = word.read('word/document.xml')
        tree = ET.fromstring(xml)
        assert not tree.findall('.//w:tbl', namespace)
        assert not tree.findall('.//w:hyperlink', namespace)
        paragraphs = [''.join(p.itertext()) for p in tree.findall('.//w:t', namespace)]
        text = ''.join(paragraphs)
        assert '我们' not in text and '咱们' not in text
        for style in tree.findall('.//w:pStyle', namespace):
            assert style.attrib.get('{' + namespace['w'] + '}val') == 'Normal'
        assert '非终端截图' in text
        for name in word.namelist():
            if name.endswith('.rels'):
                assert b'TargetMode="External"' not in word.read(name)

old_archive = ROOT / 'reports/组会汇报及100用户CSV_20261024.zip'
assert sha(old_archive) == '0924ce56a9092836d8c64fb2640c6b24e30e165c3b4fb7c46404d53857522dc9'

validation = (
    '组会完整材料验收\n\n'
    '主表：100行展示、123条完整历史记录，均为42列，覆盖原100名用户。\n'
    '商品名、评分、时间及完整评论与冻结来源逐项一致；生命周期为同商品SIM材料。\n'
    '源码：45份生产模块原样副本，摘要与当前源文件一致。画像300份、场景18份均通过摘要核验。\n'
    '本地运行：5000条任务逐条一致，4752成功、248原模型失败；新增API调用0。\n'
    'Word：主汇报2页、技术说明4页，均已逐页渲染检查；无Word原生表格、超链接或第一人称“我们”。\n'
    '配图：CSV真实数据视图及真实日志内容排版。运行日志配图明确标注“非终端截图”。\n'
    '新版MACRec B0/I1主对照未完成，材料保留该状态；本次没有启动新模型实验。\n'
    '原组会压缩包未修改。\n'
)
(PACK / '验收说明.txt').write_text(validation, encoding='utf-8-sig')
files = sorted(p for p in PACK.rglob('*') if p.is_file())
for path in files:
    parts = path.relative_to(PACK).parts
    assert not any(p in {'.secrets', '.conda', 'node_modules', '__pycache__', '.tmp'} for p in parts)
    assert path.suffix.lower() not in {'.pyc', '.pyo'}
    assert path.stat().st_size < 100 * 1024 * 1024

with zipfile.ZipFile(ARCHIVE, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
    for path in files:
        bundle.write(path, Path(PACK.name) / path.relative_to(PACK))
with zipfile.ZipFile(ARCHIVE) as bundle:
    assert bundle.testzip() is None
    assert len(bundle.infolist()) == len(files)
summary = {
    'package': str(PACK), 'archive': str(ARCHIVE), 'archive_sha256': sha(ARCHIVE),
    'archive_mib': round(ARCHIVE.stat().st_size / 1024 ** 2, 3),
    'files': len(files), 'extension_counts': dict(Counter(p.suffix for p in files)),
    'display_rows': len(shown), 'full_rows': len(full), 'columns': len(columns),
    'source_files_verified': 45, 'replay_matched_tasks': 5000,
    'new_model_api_calls': 0, 'word_visual_qa_pages': 6,
}
(BUILD / 'delivery-validation.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
