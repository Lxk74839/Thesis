"""Verify the revised, code-free material package and record the screenshot limitation."""
import csv
import hashlib
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(r'D:\Work\Codex\Project\Thesis')
BUILD = ROOT / '.scratch/meeting-revision-20261024'
CONTENT = json.loads((BUILD / 'content.json').read_text(encoding='utf-8'))
PACK = Path(CONTENT['package'])
OLD = ROOT / 'reports/组会完整材料_商品评论与生命周期_20261024'
ZIP = ROOT / 'reports/组会修订材料_无代码_字段详解与六角色设计_20261024.zip'

def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

data = PACK / '01_CSV数据与字段说明'
columns, shown = read_csv(data / '01_商品评论与生命周期_100行展示.csv')
full_columns, full = read_csv(data / '02_商品评论与生命周期_完整123条.csv')
_, fields = read_csv(data / '03_42个字段逐项详解.csv')
assert columns == full_columns and len(columns) == len(fields) == 42
assert len(shown) == 100 and len(full) == 123
assert len({r['用户编号'] for r in shown}) == len({r['用户编号'] for r in full}) == 100
assert len({r['商品标识'] for r in full}) == 75
assert sum(r['品牌'] == '' for r in full) == 106
assert sum(r['店铺名称'] == '' for r in full) == 2
assert [r['字段'] for r in fields] == columns
for name in ('01_商品评论与生命周期_100行展示.csv','02_商品评论与生命周期_完整123条.csv'):
    assert sha(data / name) == sha(OLD / '01_商品评论与生命周期数据' / name)
for item in CONTENT['fields']:
    assert fields[item['序号']-1]['实际示例'] == item['实际示例']

result_root = PACK / '03_终端截图与真实结果'
result = json.loads((result_root / '离线重放/replay-result.json').read_text(encoding='utf-8'))
_, tasks = read_csv(result_root / '离线重放/01_任务重放核对.csv')
assert len(tasks) == result['tasks'] == result['matched_original_tasks'] == 5000
assert all(r['与原结果一致'] == 'True' for r in tasks)
assert len({(r['用户编号'],r['方法'],r['场景']) for r in tasks}) == 5000
assert result['statuses'] == {'ok':4752,'failed_model':248}
assert result['new_model_api_calls'] == 0 and result['network_or_child_attempts'] == []
for metric in result['metrics']:
    byuser = defaultdict(list)
    for row in tasks:
        if row['方法'] == metric['方法'] and row['场景'].startswith('V'):
            byuser[row['用户编号']].append(row)
    assert len(byuser) == 100 and all(len(part) == 16 for part in byuser.values())
    for key in ('HR@10','NDCG@10'):
        actual = sum(sum(float(r[key]) for r in part)/16 for part in byuser.values())/100
        assert math.isclose(actual, metric[key], abs_tol=1e-12)

namespace = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
doc_paths = sorted(PACK.glob('*.docx'))
assert len(doc_paths) == 2
text_by_name = {}
for document in doc_paths:
    with zipfile.ZipFile(document) as word:
        assert word.testzip() is None
        tree = ET.fromstring(word.read('word/document.xml'))
        text = ''.join(tree.itertext()); text_by_name[document.name] = text
        assert '我们' not in text
        assert not tree.findall('.//w:tbl',namespace) and not tree.findall('.//w:hyperlink',namespace)
        assert all(p.attrib['{'+namespace['w']+'}val'] == 'Normal' for p in tree.findall('.//w:pStyle',namespace))
appendix = text_by_name['CSV字段逐项详解与六角色提示词.docx']
for i, field in enumerate(CONTENT['fields'], 1):
    assert f'{i:02} {field["字段"]}。' in appendix
for role in CONTENT['roles']:
    assert role['role'] in appendix
    for variant in role['variants']:
        assert variant['prompt'] in appendix
for name in ('01_数据关联与联合评价','02_六角色协作与宿主核验'):
    svg = PACK / '02_多智能体提示词与设计' / (name+'.svg')
    ET.fromstring(svg.read_text(encoding='utf-8'))
    assert (svg.with_suffix('.png')).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
assert len(list(BUILD.glob('brief-page-*.png'))) == 2
assert len(list(BUILD.glob('appendix-page-*.png'))) == 10

screenshot_note = (
    '真实终端运行与截图状态\n\n'
    '本次已在本机Windows Terminal中执行Thesis环境下的真实离线重放，5000条任务与原记录一致。\n'
    f"运行耗时{result['elapsed_seconds']:.2f}秒，新增模型API调用0。指标实际输出和完整原始日志均保留。\n\n"
    '终端窗口标题：Thesis Offline Evaluation 20261024。窗口仍保留结果。\n'
    '可用的窗口截图接口均未返回该终端；系统截图选择层也未向自动化工具开放。\n'
    '因此本包没有取得终端截图，未将日志排版图或流程图标成真实终端截图。\n\n'
    '如需补入：切换到该终端，手动按Win+Shift+S并选择窗口截图，保存PNG到本目录即可。\n'
    '保存后的截图需由本机用户另行插入Word或压缩包。无需再次运行模型或付费API。\n'
)
(result_root / '终端截图状态与补充方式.txt').write_text(screenshot_note,encoding='utf-8-sig')
readme = (
    'Thesis组会修订材料 无代码版\n\n'
    '阅读顺序\n'
    '1. 周组会汇报：2页，保持工作内容、数据集的解决方案、后续工作三个部分。\n'
    '2. CSV字段逐项详解与六角色提示词：10页，逐列解释42个字段，含示例、来源、用途和设计图。\n'
    '3. 01_CSV数据与字段说明：100行展示版、原100用户的123条完整历史版，以及42行字段详解。\n'
    '4. 02_多智能体提示词与设计：公共提示词、六角色业务原文、旧版实验对应提示词，及两张PNG/SVG流程图。\n'
    '5. 03_终端截图与真实结果：本次实际终端输出、重放结果、旧版独立评价与新版未完成记录。\n'
    '6. 04_补充关系表：保留原商品、用户、候选、SIM材料、场景与仅评价标签的关系表。\n\n'
    '已移除交付包中的源码、运行脚本和环境安装文件；项目本体与旧材料包未删除或修改。\n'
    '所有Word仅用直接字号和粗体区分层次，无Word原生表格、超链接或第一人称“我们”。\n\n'
    '理解数据\n'
    '每行是一条真实历史评论，加同商品正常SIM材料的属性。100行与123条来自同一批100名用户。\n'
    '完整历史涉及75个不同商品，完整候选目录为1494个商品。42列是数据字段，不是算法超参数。\n'
    '品牌106条为空，店铺2条为空。字段详解中的不同取值数包含空白；空值数另列。\n'
    '正常SIM采用统一基准时间和状态，18场景变化在关系表另存。没有声称真实购买模拟批次。\n\n'
    '运行证据\n'
    '5000条任务与原记录逐条一致；4752成功、248模型失败，失败如实保留。新增API调用为0。\n'
    'HR和NDCG先对每用户的16个V场景平均，再对100名用户等权平均。Q1/Q2另做质量评价。\n'
    '真实终端已运行并保留，但截图接口未提供终端窗口，因此终端截图尚未取得；详见结果目录说明。\n'
    '新MACRec B0/I1主对照仍未完成，原R/S/M结果不充作新版结果；本地SIM不充作Fabric实链部署。\n'
)
(PACK / '请先阅读.txt').write_text(readme,encoding='utf-8-sig')

assert sha(ROOT / 'reports/组会完整材料_含商品级数据代码提示词与运行结果_20261024.zip') == 'af0745c60c03e55ea788479d5825816a9e4eeb9332d652dcb8740c7cea4769bc'
paths = sorted(p for p in PACK.rglob('*') if p.is_file())
for path in paths:
    assert path.suffix.lower() not in {'.py','.pyc','.ps1','.sh','.bat','.exe','.mjs','.js','.yml','.yaml'}
    assert not {'.secrets','node_modules','.conda','__pycache__','.scratch'}.intersection(path.relative_to(PACK).parts)
with zipfile.ZipFile(ZIP,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for path in paths:
        archive.write(path,Path(PACK.name)/path.relative_to(PACK))
with zipfile.ZipFile(ZIP) as archive:
    assert archive.testzip() is None and len(archive.infolist()) == len(paths)
summary = {'archive':str(ZIP),'size_mib':round(ZIP.stat().st_size/1024**2,3),'sha256':sha(ZIP),
           'files':len(paths),'word_pages':[2,10],'csv_rows':[100,123],'fields_explained':42,
           'roles':6,'normal_prompt_variants':sum(len(r['variants']) for r in CONTENT['roles']),
           'design_figures':2,'code_files':0,'actual_replay_matched_tasks':5000,'new_model_api_calls':0,
           'terminal_screenshot':'not_acquired; actual terminal retained; no fabricated screenshot'}
(BUILD/'delivery-validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
