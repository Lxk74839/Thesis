"""Replace only the third-page agent figure and its captions in a sibling Word copy."""
import hashlib
import json
import struct
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(r'D:\Work\Codex\Project\Thesis')
BUILD=ROOT/'.scratch/meeting-role-refinement-20261025'
META=json.loads((BUILD/'revision.json').read_text(encoding='utf-8'))
OLD=Path(META['old']); NEW=Path(META['new'])
DOCNAME='周组会汇报_实验结果_数据集_智能体设计.docx'
IMAGE=NEW/'配图/用户画像智能体_学术风格.png'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
namespaces={
 'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
 'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
 'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
 'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
 'pic':'http://schemas.openxmlformats.org/drawingml/2006/picture',
}
for prefix,uri in namespaces.items():
    ET.register_namespace(prefix,uri)

with zipfile.ZipFile(OLD/DOCNAME) as source:
    entries={info.filename:(info,source.read(info.filename)) for info in source.infolist()}
tree=ET.fromstring(entries['word/document.xml'][1])
rels=ET.fromstring(entries['word/_rels/document.xml.rels'][1])
targets={}
for rel in rels:
    target=rel.attrib.get('Target','')
    name='word/'+target
    if name in entries and hashlib.sha256(entries[name][1]).hexdigest()==META['old_image_sha256']:
        targets[rel.attrib['Id']]=name
assert len(targets)==1
width,height=struct.unpack('>II',IMAGE.read_bytes()[16:24])
cy=round(6.60*914400); cx=round(cy*width/height)
assert cx<=round(6.15*914400)
changed=0
for inline in tree.findall('.//wp:inline',namespaces):
    blip=inline.find('.//a:blip',namespaces)
    if blip is None or blip.attrib.get('{'+namespaces['r']+'}embed') not in targets:
        continue
    inline.find('wp:extent',namespaces).attrib.update(cx=str(cx),cy=str(cy))
    inline.find('.//a:xfrm/a:ext',namespaces).attrib.update(cx=str(cx),cy=str(cy))
    inline.find('wp:docPr',namespaces).set('descr','用户画像智能体角色与提示词设计的学术风格图')
    changed+=1
assert changed==1
old_caption='用户画像智能体提示词模板，按既有英文提示词整理的中文展示图。'
new_caption='用户画像智能体角色与提示词设计，明确身份、目标、职责、协作关系及能力边界。'
captions=0
for text in tree.findall('.//w:t',namespaces):
    if text.text==old_caption:
        text.text=new_caption; captions+=1
    elif text.text and '模板原文另附TXT' in text.text:
        text.text=text.text.replace('模板原文另附TXT','角色与提示词原文另附TXT')
assert captions==1
document=ET.tostring(tree,encoding='utf-8',xml_declaration=True)
replacement=next(iter(targets.values()))
with zipfile.ZipFile(NEW/DOCNAME,'w',zipfile.ZIP_DEFLATED) as archive:
    for name,(info,raw) in entries.items():
        archive.writestr(info,document if name=='word/document.xml' else IMAGE.read_bytes() if name==replacement else raw)
with zipfile.ZipFile(NEW/DOCNAME) as archive:
    assert archive.testzip() is None
    result=ET.fromstring(archive.read('word/document.xml'))
    text=''.join(result.itertext())
    assert '我们' not in text and '提示词模板' not in text
    assert not result.findall('.//w:tbl',namespaces) and not result.findall('.//w:hyperlink',namespaces)
    # Earlier experiments, dataset figures, and all other document parts stay byte-identical.
    for name,(_,raw) in entries.items():
        if name not in ('word/document.xml',replacement):
            assert archive.read(name)==raw

old_template=NEW/'用户画像智能体提示词模板.txt'
new_template=NEW/'用户画像智能体_角色定义与提示词.txt'
template_text=old_template.read_text(encoding='utf-8-sig')
template_text=template_text.replace('用户画像智能体提示词模板','用户画像智能体角色定义与提示词',1)
new_template.write_text(template_text,encoding='utf-8-sig')
assert old_template.parent.resolve()==NEW.resolve()
old_template.unlink()
discarded=NEW/'配图/卡通图修改提示词.txt'
if discarded.exists():
    assert discarded.parent.resolve()==(NEW/'配图').resolve()
    discarded.unlink()
(NEW/'阅读说明.txt').write_text(
 '组会材料 学术风格角色完善版\n\n'
 'Word保持三部分：实验与结果、数据集简介、多智能体设计与提示词。\n'
 '本版只完善用户画像智能体的角色定义和图示，实验终端截图、实验指标和两份数据CSV沿用已核对版本。\n'
 '图仅保留标题“用户画像智能体”，采用白底、深色正文、深蓝分区；角色含身份定位、工作目标、核心职责、协作关系和能力边界。\n'
 '配图为内置imagegen编辑的学术风格PNG；角色与提示词TXT以及图像修改提示词随包保留。\n'
 '未新增推荐模型调用；不附项目源码，先前材料和生产项目未覆盖。\n',encoding='utf-8-sig')
for relative in ('实验结果/终端结果截图.png','实验结果/方法指标.csv','数据集/01_商品评论与生命周期_100行展示.csv','数据集/02_商品评论与生命周期_完整123条.csv'):
    assert sha(NEW/relative)==sha(OLD/relative)
assert sha(OLD/'配图/用户画像智能体_卡通提示词模板.png')==META['old_image_sha256']
summary={'document':str(NEW/DOCNAME),'image':str(IMAGE),'role_dimensions':5,'unchanged_document_parts':len(entries)-2}
(BUILD/'updated-document.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
