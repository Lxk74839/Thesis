"""Update the single-agent illustration and its source note in the meeting copy."""
import csv
import hashlib
import json
import shutil
import struct
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(r'D:\Work\Codex\Project\Thesis')
BUILD = ROOT / '.scratch/meeting-role-refinement-20261025'
meta = json.loads((BUILD / 'revision.json').read_text(encoding='utf-8'))
OLD, NEW = Path(meta['old']), Path(meta['new'])
DOCNAME = '周组会汇报_实验结果_数据集_智能体设计.docx'
image_source = Path(r'C:\Users\Kane\.codex\generated_images\01a0c1d6-59c8-7c31-8cf8-cf428333a080\exec-db9edeb1-45bb-4112-9499-a86d43b7cd10.png')
image_target = NEW / '配图/用户画像智能体_学术风格.png'
assert NEW.resolve().is_relative_to((ROOT / 'reports').resolve())
shutil.copyfile(image_source, image_target)
prompt = (BUILD / 'literature-informed-image-edit-prompt.txt').read_text(encoding='utf-8')
(NEW / '配图/学术图修改提示词.txt').write_text(prompt, encoding='utf-8-sig')

ns = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
}
for prefix, uri in ns.items():
    ET.register_namespace(prefix, uri)
with zipfile.ZipFile(OLD / DOCNAME) as source:
    entries = {item.filename: (item, source.read(item.filename)) for item in source.infolist()}
tree = ET.fromstring(entries['word/document.xml'][1])
rels = ET.fromstring(entries['word/_rels/document.xml.rels'][1])
targets = {}
for relation in rels:
    name = 'word/' + relation.get('Target', '')
    if name in entries and hashlib.sha256(entries[name][1]).hexdigest() == meta['old_image_sha256']:
        targets[relation.get('Id')] = name
assert len(targets) == 1
width, height = struct.unpack('>II', image_target.read_bytes()[16:24])
cy = round(6.60 * 914400)
cx = round(cy * width / height)
assert cx <= round(6.15 * 914400)
changed = 0
for inline in tree.findall('.//wp:inline', ns):
    blip = inline.find('.//a:blip', ns)
    if blip is None or blip.get('{' + ns['r'] + '}embed') not in targets:
        continue
    inline.find('wp:extent', ns).attrib.update(cx=str(cx), cy=str(cy))
    inline.find('.//a:xfrm/a:ext', ns).attrib.update(cx=str(cx), cy=str(cy))
    inline.find('wp:docPr', ns).set('descr', '用户画像智能体的固定指令、动态输入和输出约定，采用学术指令块排版')
    changed += 1
assert changed == 1
old_caption = '用户画像智能体提示词模板，按既有英文提示词整理的中文展示图。'
new_caption = '用户画像智能体指令的中文展示。版式参考AgentCF附录C.1与RecMind附录A，具体字段按项目协议定义。'
old_final = '提示词主要约束三点：只选择给定属性；没有充分依据时保留空结果；不从评论中猜测批次质量、产地或认证。这样可以减少无依据的偏好推断。模板原文另附TXT，便于复制和调整。'
new_final = '该角色只选择给定属性；证据不足时保留未知；不从评论中推断批次质量、产地或认证。图中同时列出职责、协作关系、输入变量和输出约定。完整指令与文献位置另附文字说明。'
replacements = {old_caption: new_caption, old_final: new_final}
count = 0
for node in tree.findall('.//w:t', ns):
    if node.text in replacements:
        node.text = replacements[node.text]
        count += 1
assert count == len(replacements)
document = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
media = next(iter(targets.values()))
with zipfile.ZipFile(NEW / DOCNAME, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name, (item, raw) in entries.items():
        archive.writestr(item, document if name == 'word/document.xml' else image_target.read_bytes() if name == media else raw)

role_file = NEW / '用户画像智能体_角色定义与提示词.txt'
previous = role_file.read_text(encoding='utf-8-sig')
original = previous[previous.index('原system'):]
figure_text = prompt.split('EXACT FIGURE TEXT:\n\n', 1)[1].split('\n\nEND EXACT FIGURE TEXT.', 1)[0]
role_file.write_text(
    '用户画像智能体角色定义与提示词\n\n中文展示版\n\n' + figure_text +
    '\n\n说明\n图为既有Compact指令和输入协议的中文整理，图示排版不改变实验提示词或运行配置。JSON中的0.8只作格式示例；weight表示偏好权重，不表示置信概率。\n'
    'history为可见历史评论与评分；options包含option_id、dimension、value和source；previous为前序画像结果；attribute_coverage为crop与form覆盖统计；catalog_count为目录商品数。\n'
    '原始英文指令如下，供对应核对。\n\n' + original,
    encoding='utf-8-sig')

(NEW / '版式参考说明.txt').write_text(
    '用户画像智能体图的文献依据\n\n'
    '1. AgentCF，arXiv:2310.09233v1，附录C.1，PDF第12页，延续至第13页。\n'
    '原文以横线分区，粗体标出智能体及指令与响应，连续列出身份、记忆占位符、步骤、注意事项和输出字段。该部分没有图号或表号。\n'
    'https://arxiv.org/pdf/2310.09233v1#page=12\n\n'
    '2. RecMind，NAACL Findings 2024正式版，附录A，PDF第12页，印刷页4362。\n'
    '原文用粗体小标题、工具项目符号及花括号变量组织指令，并明确输入和输出要求。该附录不是带图号的完整提示词图。\n'
    'https://aclanthology.org/2024.findings-naacl.271.pdf#page=12\n\n'
    '本图采用一个连续指令框，分为固定指令、动态输入和输出约定；只参考上述论文的指令组织与排版方式，中文职责和字段来自Thesis现有Compact角色及协议。\n'
    'AgentCF的CD选择、记忆优化和RecMind的SQL、搜索工具不属于本用户画像角色，未加入图中。角色定义不是上述论文提供的农产品算法，图也不表示新增实验结果。\n',
    encoding='utf-8-sig')
(NEW / '阅读说明.txt').write_text(
    '组会材料 学术风格角色完善版\n\n'
    'Word按实验与结果、数据集简介、多智能体设计与提示词三个部分阅读。\n'
    '终端截图展示旧版100用户18场景的缓存离线复算；方法指标与两份CSV沿用已核对材料。\n'
    '100行展示版覆盖100名用户；123条版保留同批用户的全部冻结历史，两份均42列。真实商品评论与同商品SIM生命周期属性位于同一行。\n'
    '单个用户画像智能体图采用论文附录中的指令块方式；职责完整，按固定指令、动态输入、输出约定组织。文献位置及参考范围见版式参考说明。\n'
    '配图为内置imagegen编辑的PNG，随包提供图像编辑提示词和角色指令文字。\n'
    '本次材料修订未新增推荐模型调用，不附项目源码。\n', encoding='utf-8-sig')

sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
unchanged = ['实验结果/终端结果截图.png', '实验结果/方法指标.csv',
             '数据集/01_商品评论与生命周期_100行展示.csv', '数据集/02_商品评论与生命周期_完整123条.csv',
             '配图/数据集样例.png', '配图/数据集_六阶段样例.png']
for relative in unchanged:
    assert sha(NEW / relative) == sha(OLD / relative), relative
rows = []
for filename, expected in [('01_商品评论与生命周期_100行展示.csv', 100), ('02_商品评论与生命周期_完整123条.csv', 123)]:
    with (NEW / '数据集' / filename).open(encoding='utf-8-sig', newline='') as stream:
        records = list(csv.DictReader(stream))
    assert len(records) == expected and len(records[0]) == 42
    assert len({row['用户编号'] for row in records}) == 100
    rows.append(len(records))
with zipfile.ZipFile(NEW / DOCNAME) as archive:
    assert archive.testzip() is None
    result = ET.fromstring(archive.read('word/document.xml'))
    text = ''.join(result.itertext())
    assert '我们' not in text and '提示词模板' not in text
    assert not result.findall('.//w:tbl', ns) and not result.findall('.//w:hyperlink', ns)
    assert all(node.get('{' + ns['w'] + '}val') == 'Normal' for node in result.findall('.//w:pStyle', ns))
    for name, (_, raw) in entries.items():
        if name not in ('word/document.xml', media):
            assert archive.read(name) == raw, name
assert not any(path.suffix.lower() in ('.py', '.js', '.ps1', '.ipynb') for path in NEW.rglob('*') if path.is_file())
summary = {'document': str(NEW / DOCNAME), 'image': str(image_target),
           'csv_rows': rows, 'csv_columns': 42, 'unchanged_files_checked': len(unchanged),
           'new_model_api_calls': 0, 'source_pages': ['AgentCF C.1 PDF12', 'RecMind A PDF12 / p4362']}
(BUILD / 'final-document.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
