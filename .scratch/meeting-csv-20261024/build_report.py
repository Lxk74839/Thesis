"""Create a simple Word meeting brief using stdlib OOXML in the Thesis environment."""
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile,ZIP_DEFLATED
import json,struct,xml.etree.ElementTree as ET
ROOT=Path(r'D:\Work\Codex\Project\Thesis')
BUILD=ROOT/'.scratch/meeting-csv-20261024'; OUT=ROOT/'reports/组会汇报与100用户数据_20261024'
stats=json.loads((BUILD/'data-summary.json').read_text(encoding='utf-8'))['checks']
assert stats['用户总数']==100 and stats['历史评论记录']==123 and stats['用户候选关联数']==149276
blocks=[
('title','Thesis项目周组会汇报'),
('subtitle','2026年10月24日'),
('body','本周重点是交付100名用户的联合数据集CSV文件，并推进推荐算法的真实调用。数据已整理成可直接用Excel或WPS查看的行列表，新算法的效果对照仍在联调。'),
('section','工作内容'),
('body','已完成谷物商品与评论整理、开发集和测试集划分，以及商品、模拟批次、生命周期事件和证据材料之间的关联。各方法使用同一份用户历史和候选商品，留出评论单独保存，用作独立评价答案。'),
('body','旧版100用户、18个场景的实验已形成5,000条终态记录，其中4,752条成功、248条模型失败。现有结果尚未显示多智能体方法优于规则方法，因此算法改进重点转向候选商品的语义匹配、短历史偏好的置信度、证据质量融合和反馈修订。'),
('body','MACRec农产品适配基线B0和改进方法I1已完成代码实现及本地测试。真实调用中的多步检索和调度仍有协议问题，新一轮B0与I1主对照尚未完成，暂不报告两者的效果差异。'),
('section','数据集的解决方案'),
('body','真实商品和评论来自Amazon Reviews 2023食品类别，筛选范围限定为谷物及其相关商品。由于缺少与这些评论对应的真实批次材料，数据方案是在同一商品标识下建立模拟批次、生命周期事件和证据材料。评论用于描述偏好，材料用于检验推荐时的资格判断和依据核验。'),
('body','本次沿用已冻结的100名测试来源账户，导出123条输入历史评论和100条留出评价评论。候选商品目录包含1,494个父商品，用户与候选商品共有149,276条关联。用户总表恰好100行，评论表和关联表根据实际记录逐行保存，所有文件均以列表示属性。'),
('body','同商品模拟供应链包含1,494个批次、8,964个生命周期事件、11,952份证据材料和22410条本地模拟登记。事件覆盖采收、包装、仓储、检验、运输和零售六个阶段。数据中的SIM字段明确标识模拟来源，历史评论仍属于真实父商品，不解释为对模拟批次的购买或评价。'),
('body','18个实验场景对应1,800条用户与场景绑定。正常材料只保留一套，其余场景用变化明细表示，便于对比缺失、冲突或权限等条件变化。模拟登记采用本地记录，区块链实际部署与联合验证仍属于后续工作。'),
('image',''),
('caption','历史评论CSV预览，显示前三条记录；评论文本仅展示前90个字符。'),
('body','查看时先打开“01_用户总表_100行.csv”，再查看历史评论、商品目录和用户候选关联表。通过商品标识可继续连接模拟批次、事件和材料；留出评价评论及场景构造信息分别存放，避免直接进入推荐模型。'),
('section','后续工作'),
('body','先补齐检索操作、参数结构和管理调度的完整调用链验证，完成固定16名开发用户的B0与I1配对对照。根据真实结果判断算法改进是否有效，再冻结方法和参数。'),
('body','随后在相同100名用户上开展新方法的正式对照、异常场景和消融实验，分别检查推荐准确性、证据变化下的表现及各改进组件的作用。之后接入区块链登记与核验模块，完成联合验证，并据实际结果更新论文的实验、讨论和结论。')]
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def paragraph(kind,text):
    size={'title':36,'subtitle':21,'section':28,'body':24,'caption':20}[kind]
    font='Microsoft YaHei' if kind in ['title','section'] else '宋体'
    bold='<w:b/>' if kind in ['title','section'] else ''
    align='center' if kind in ['title','subtitle','caption'] else 'both' if kind=='body' else 'left'
    before=180 if kind=='section' else 0
    after=150 if kind=='title' else 110 if kind in ['section','body'] else 80
    keep='<w:keepNext/>' if kind in ['title','subtitle','section'] else ''
    indent='<w:ind w:firstLine="480"/>' if kind=='body' else ''
    line='312' if kind=='body' else '280'
    return f'<w:p><w:pPr><w:pStyle w:val="Normal"/>{keep}<w:widowControl/><w:jc w:val="{align}"/><w:spacing w:before="{before}" w:after="{after}" w:line="{line}" w:lineRule="auto"/>{indent}</w:pPr><w:r><w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:eastAsia="{font}"/>{bold}<w:color w:val="000000"/><w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'
image=(BUILD/'csv-preview.png').read_bytes(); width,height=struct.unpack('>II',image[16:24]); cx=int(6.25*914400); cy=round(cx*height/width)
picture=f'''<w:p><w:pPr><w:jc w:val="center"/><w:keepNext/><w:spacing w:before="100" w:after="40"/></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="1" name="历史评论CSV数据预览" descr="固定100名用户数据集历史评论表的前三条记录，评论展示前90个字符"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="csv-preview.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rIdImage1"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'''
body=''.join(picture if kind=='image' else paragraph(kind,text) for kind,text in blocks)
body+='<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1247" w:bottom="1134" w:left="1247" w:header="0" w:footer="0" w:gutter="0"/></w:sectPr>'
document=f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body>{body}</w:body></w:document>'''
styles=f'''<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体"/><w:sz w:val="24"/><w:lang w:val="zh-CN" w:eastAsia="zh-CN"/></w:rPr></w:rPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>'''
rels='''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rIdSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/><Relationship Id="rIdImage1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/csv-preview.png"/></Relationships>'''
content_types='''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/></Types>'''
rootrels='''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
path=OUT/'周组会汇报_20261024.docx'
with ZipFile(path,'w',ZIP_DEFLATED) as z:
    for name,value in {'[Content_Types].xml':content_types,'_rels/.rels':rootrels,'word/document.xml':document,'word/styles.xml':styles,'word/_rels/document.xml.rels':rels,'word/settings.xml':f'<w:settings xmlns:w="{W}"><w:defaultTabStop w:val="420"/></w:settings>','word/media/csv-preview.png':image}.items(): z.writestr(name,value)
with ZipFile(path) as z:
    assert z.testzip() is None
    xml=ET.fromstring(z.read('word/document.xml'))
    text=''.join(xml.itertext())
    assert not any(p in text for p in ['我们','我方','本人'])
    assert len(xml.findall('.//{'+W+'}tbl'))==0 and len(xml.findall('.//{'+W+'}hyperlink'))==0
    assert [t for k,t in blocks if k=='section']==['工作内容','数据集的解决方案','后续工作']
    assert all(s.attrib.get('{'+W+'}val')=='Normal' for s in xml.findall('.//{'+W+'}pStyle'))
(BUILD/'report-content.json').write_text(json.dumps(blocks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'word':str(path),'characters':sum(len(t) for k,t in blocks),'sections':3,'native_tables':0,'hyperlinks':0,'first_person_terms':0,'images':1},ensure_ascii=False))