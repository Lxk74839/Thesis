"""Create the confirmed plain-font Word report and detailed explanation appendix."""
import json
import re
import struct
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

ROOT = Path(r'D:\Work\Codex\Project\Thesis')
BUILD = ROOT / '.scratch/meeting-revision-20261024'
CONTENT = json.loads((BUILD / 'content.json').read_text(encoding='utf-8'))
PACK = Path(CONTENT['package'])
DESIGN = PACK / '02_多智能体提示词与设计'
DATA = PACK / '01_CSV数据与字段说明'
RESULT = json.loads((PACK / '03_终端截图与真实结果/离线重放/replay-result.json').read_text(encoding='utf-8'))
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
assert RESULT['matched_original_tasks'] == 5000

def paragraph(kind, text):
    size = {'title': 36, 'subtitle': 21, 'section': 28, 'subsection': 24,
            'body': 24, 'field': 22, 'prompt': 21, 'caption': 20}[kind]
    bold = kind in ('title', 'section', 'subsection')
    align = 'center' if kind in ('title', 'subtitle', 'caption') else 'both' if kind in ('body', 'field') else 'left'
    keep = '<w:keepNext/>' if bold or kind == 'subtitle' else ''
    first = '<w:ind w:firstLine="480"/>' if kind == 'body' else ''
    before = 140 if kind in ('section', 'subsection') else 0
    after = 120 if kind in ('body', 'title', 'section') else 80
    font = 'Microsoft YaHei' if bold else 'Times New Roman' if kind == 'prompt' else '宋体'
    line = 310 if kind == 'body' else 280 if kind == 'field' else 265
    prop = f'<w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:eastAsia="宋体"/>{"<w:b/>" if bold else ""}<w:color w:val="000000"/><w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
    if kind == 'field':
        lead, rest = text.split('。', 1)
        content = f'<w:r>{prop[:-8]}<w:b/></w:rPr><w:t xml:space="preserve">{escape(lead)}。</w:t></w:r><w:r>{prop}<w:t xml:space="preserve">{escape(rest)}</w:t></w:r>'
    else:
        content = f'<w:r>{prop}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'
    return f'<w:p><w:pPr><w:pStyle w:val="Normal"/>{keep}<w:widowControl/><w:wordWrap w:val="0"/><w:jc w:val="{align}"/><w:spacing w:before="{before}" w:after="{after}" w:line="{line}" w:lineRule="auto"/>{first}</w:pPr>{content}</w:p>'

def image_xml(raw, index, description):
    width, height = struct.unpack('>II', raw[16:24])
    cx = round(6.15 * 914400); cy = round(cx * height / width)
    if cy > 5.65 * 914400:
        cx = round(cx * 5.65 * 914400 / cy); cy = round(5.65 * 914400)
    return f'<w:p><w:pPr><w:jc w:val="center"/><w:keepNext/><w:spacing w:before="80" w:after="40"/></w:pPr><w:r><w:drawing><wp:inline><wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="{index}" name="说明图{index}" descr="{escape(description)}"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="image{index}.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rIdImage{index}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'

def write_doc(name, blocks):
    body = []; images = []
    for kind, value in blocks:
        if kind == 'image':
            path = Path(value); raw = path.read_bytes(); images.append(raw)
            body.append(image_xml(raw, len(images), path.stem))
        elif kind == 'pagebreak':
            body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
        else:
            body.append(paragraph(kind, value))
    body.append('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1050" w:right="1190" w:bottom="1050" w:left="1190" w:header="0" w:footer="0" w:gutter="0"/></w:sectPr>')
    document = f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{W}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body>'+''.join(body)+'</w:body></w:document>'
    styles = f'<w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体"/><w:sz w:val="24"/><w:lang w:val="zh-CN" w:eastAsia="zh-CN"/></w:rPr></w:rPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>'
    rels = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'+''.join(f'<Relationship Id="rIdImage{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image{i}.png"/>' for i in range(1, len(images)+1))+'</Relationships>'
    types = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'
    root_rels = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    target = PACK / name
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for part, value in {'[Content_Types].xml': types, '_rels/.rels': root_rels, 'word/document.xml': document,
                            'word/styles.xml': styles, 'word/_rels/document.xml.rels': rels}.items():
            archive.writestr(part, value)
        for i, raw in enumerate(images, 1):
            archive.writestr(f'word/media/image{i}.png', raw)
    with zipfile.ZipFile(target) as archive:
        tree = ET.fromstring(archive.read('word/document.xml'))
        assert archive.testzip() is None and '我们' not in ''.join(tree.itertext())
        assert not tree.findall('.//{'+W+'}tbl') and not tree.findall('.//{'+W+'}hyperlink')
    (BUILD / (target.stem+'_content.json')).write_text(json.dumps(blocks, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'file': str(target), 'images': len(images), 'characters': sum(len(v) for k,v in blocks if k not in ('image','pagebreak'))}

brief = [
 ('title','Thesis项目周组会汇报'), ('subtitle','2026年10月24日'),
 ('section','工作内容'),
 ('body','已整理真实谷物商品与评论，冻结100名测试用户，并通过商品标识把评论、候选商品与同商品的模拟生命周期材料关联起来。已形成商品级CSV、字段说明、六角色提示词和设计图，便于查看具体数据并说明推荐过程。'),
 ('body',f"旧版已完成18个场景共5000条方法任务，其中4752条成功、248条模型失败。本次在真实终端复用原模型画像，重新执行宿主排序，5000条结果与原记录一致，耗时{RESULT['elapsed_seconds']:.2f}秒，新增模型API调用为0。"),
 ('body','R为规则画像，S为单次模型画像，M为依次执行六角色的画像方式。16个V场景按用户等权汇总的结果如下：'),
 ('field','R规则画像。HR@10＝0.217500；NDCG@10＝0.121012。'),
 ('field','S单次模型画像。HR@10＝0.195625；NDCG@10＝0.108129。'),
 ('field','M六角色画像。HR@10＝0.205625；NDCG@10＝0.102365。'),
 ('body','原比较区间包含0，现阶段不能宣布M总体更好。'),
 ('body','新MACRec农产品适配基线B0与改进方法I1已实现动态管理、候选语义匹配、短历史置信度、证据质量和反馈修订。当前完整调用链仍有协议问题，B0与I1的主对照尚未完成；上述旧版指标与新版分别记录。'),
 ('section','数据集的解决方案'),
 ('body','CSV以一条真实历史评论为一行，包含商品名、完整评论、评分，以及同商品采收、包装、仓储、检验、运输、零售的具体属性，共42列。100行版每用户选最近一条可见历史评论；123条版保留同一批100名用户的全部冻结历史评论，涉及75个不同历史商品。完整候选目录另有1494个商品。'),
 ('image',str(DATA / '01_商品名称与完整评论_CSV视图.png')),
 ('caption','真实CSV的商品名称与完整评论列预览。生命周期属性在同一行的后续列中。'),
 ('body','连接顺序为真实评论对应父商品，再连接该父商品的SIM批次及六阶段材料。这样可以在同一推荐任务中同时使用用户偏好和该商品的生命周期观察。SIM属性沿用正常基准，异常材料和无关变化另存18场景明细；用户留出目标只在独立评价侧使用。'),
 ('image',str(DESIGN / '01_数据关联与联合评价.png')),
 ('caption','真实评论、同商品SIM材料与独立评价的连接方式。'),
 ('body','字段详解逐一说明数据含义、原始来源、实际示例和用途。例如SIM_PACK是模拟包装单位，SIM-Q1是模拟检验项目，品牌空白表示来源缺失。正常基准采用统一时间和状态，因此不同商品会出现相同SIM值；这些值用于受控实验，不表示真实批次实测差异。'),
 ('section','后续工作'),
 ('body','先补齐新方法的完整调用链验证，完成固定16名开发用户的B0与I1对照，再冻结方法和参数。在原100名用户上开展正式对比、异常场景和消融实验，检验推荐准确性、排名质量与可信推荐组件的作用。'),
 ('body','继续完成区块链实际部署及联合验证。当前为本地SIM登记，后续依据真实运行结果更新论文实验、讨论与结论。')
]

appendix = [('title','CSV字段详解与多智能体设计'), ('subtitle','Thesis组会说明附件 2026年10月24日'),
 ('body','本附件逐一解释两份CSV的42个字段，并列出六角色的职责、输入输出、完整业务提示词与协作方式。终端结果属于旧版Compact；当前MACRec设计及未完成状态另行标注。材料不附项目源码。'),
 ('section','先理解一行记录'),
 ('body','100行版与123条版使用相同42列，覆盖同一批100名冻结用户。一行表示一条真实历史评论及同商品的正常SIM生命周期属性。100行版每用户取最近一条历史，123条版保留全部冻结历史。两者不是两组用户，也不是重新抽样。'),
 ('body','完整123条历史涉及75个不同商品；1494是完整候选目录的商品数。品牌有106条空白，店铺有2条空白。历史评分当前仅含4和5，不能把这份冻结历史当成包含全部评分分布的原始评论库。'),
 ('body','UTC时间末尾的Z表示世界协调时间，换算日本时间需加9小时。历史评论时间来自真实记录；SIM日期是受控场景时钟，不强行改成历史购买时间。CSV中的空白表示缺失，不自动当作0、合格或不合格。'),
 ('body','42列是数据字段。推荐权重、阈值和调用步数属于算法或运行参数，不在这42列中。主表平铺是为了便于查看，原商品、事件、材料、场景与候选关系表仍随包保留。')]
groups = {1:'账户商品与评论字段',10:'模拟批次及采收包装字段',19:'仓储与检验字段',28:'运输与零售字段',39:'阶段数与来源字段'}
for field in CONTENT['fields']:
    n = field['序号']
    if n in groups:
        appendix.append(('section', groups[n]))
    example = field['实际示例']
    # Keep complete example values, including real product names and comment text.
    text = f"{n:02} {field['字段']}。{field['含义']} 示例：{example}。{field['用途与注意点']} 来源：{field['来源']}；格式：{field['格式']}。"
    appendix.append(('field', text))
appendix += [
 ('body','这份主表展示正常SIM基准，因此多个生命周期列只有一种取值。变化不通过随机补造产地、温度或检测数据实现，而是保留在既有场景明细中；比较时固定真实用户、历史和候选，只改变协议规定的材料或状态。'),
 ('section','六角色如何配合'),
 ('body','当前设计保持需求解析、推荐管理、用户画像、农产品画像、生命周期追溯、推荐依据核验六个角色。推荐管理的Thought与Action是同一角色的两个业务调用。分析与工具观察返回管理者后，再决定下一步；模型提出分析与取证需求，宿主执行材料核验和I1计分。'),
 ('image',str(DESIGN / '02_六角色协作与宿主核验.png')),
 ('caption','当前MACRec协作设计示意。完整闭环与B0/I1效果对照仍待验证。'),
 ('body','B0是MACRec在农产品任务中的有界适配基线，由管理者结合分析和实际取证观察形成排名。I1增加有依据的结构化偏好、候选语义匹配、短历史置信度、证据质量及定位反馈，最终由宿主计分。改进已经实现，效果是否提高须由相同用户和候选的对照实验检验。'),
 ('body','提示词按“公共提示＋所选角色业务提示”组合。以下保留实际英文原文；B0与I1按实验方法选择相应版本。未发送的模板与已发送的请求均注明状态，未把探针成功当成完整协作成功。'),
 ('subsection','公共提示词原文')]
for line in CONTENT['common'].splitlines():
    appendix.append(('prompt',line))
for role in CONTENT['roles']:
    appendix.append(('section',role['role']))
    appendix += [('body','职责与设计：'+role['design']),('body','输入：'+role['input']+' 输出：'+role['output'])]
    for variant in role['variants']:
        appendix.append(('subsection',variant['title']))
        state = '来自真实请求，发送不代表该用户任务最终成功。' if '保存了' in variant['status'] else '当前实现中的业务模板，未找到本版此分支的真实发送记录。'
        appendix.append(('field','调用状态。'+state))
        appendix.append(('prompt',variant['prompt']))
appendix += [
 ('section','旧版指标对应哪一组提示词'),
 ('body','终端展示的R、S、M来自已完成的Compact实验。它先获得可复用的偏好画像，再按场景进行宿主重排；M依次检查六角色。它与上图所示的新MACRec动态工具协作是不同版本。对应的公共instruction与六角色原文如下。')]
old_text = (DESIGN / '07_旧版Compact_对应HR与NDCG的提示词.md').read_text(encoding='utf-8-sig')
for chunk in re.split(r'^## ',old_text,flags=re.M):
    blocks = re.findall(r'```text\s*\n(.*?)\n```',chunk,flags=re.S)
    if not blocks:
        continue
    if chunk.startswith('# '):
        for title, block in zip(('旧版传输层system','旧版共同instruction'),blocks):
            appendix += [('subsection',title),('prompt',block.strip())]
    else:
        appendix += [('subsection',chunk.splitlines()[0].strip()),('prompt',blocks[0].strip())]
appendix += [
 ('section','HR与NDCG怎样理解'),
 ('body','本项目每个用户任务有一个留出目标商品。HR@10表示目标是否进入前10名：进入记1，未进入或任务失败记0。NDCG@10进一步考虑命中的位置：目标排第r名且r不超过10时记1/log2(r+1)，否则记0；本单目标设置的理想值为1。'),
 ('body','汇总时先对同一用户的16个V场景求平均，再对100名用户等权平均；Q1和Q2另做质量相关评价。R的HR@10为0.217500、NDCG@10为0.121012；S为0.195625、0.108129；M为0.205625、0.102365。多场景记录不增加独立用户数。'),
 ('body',f"本次离线重放共5000条任务，全部与原状态及Top10一致；4752条成功、248条原模型失败，实际推荐项次47520，本地耗时{RESULT['elapsed_seconds']:.2f}秒。这里重新执行的是缓存画像上的宿主排序，没有重新调用大模型，新增API调用为0。"),
 ('body','这些结果未证明旧版M总体优于R或S，也不能充当新B0/I1结果。当前新MACRec主对照尚未完成，HR和NDCG仍为NA；后续完成开发集对照并冻结参数后，再开展相同100用户的正式比较。')]

outputs = [write_doc('周组会汇报_无代码修订版.docx',brief),write_doc('CSV字段逐项详解与六角色提示词.docx',appendix)]
(BUILD / 'documents.json').write_text(json.dumps(outputs,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(outputs,ensure_ascii=False,indent=2))
