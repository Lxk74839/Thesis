"""Reorder the meeting report around experiments, data, and one illustrated agent."""
import ast
import csv
import hashlib
import json
import struct
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

ROOT=Path(r'D:\Work\Codex\Project\Thesis')
BUILD=ROOT/'.scratch/meeting-final-focus-20261024'
META=json.loads((BUILD/'package.json').read_text(encoding='utf-8'))
PACK=Path(META['output'])
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
# Reuse only the existing document-writing helpers, without running the older report builder.
source=ROOT/'.scratch/meeting-revision-20261024/build_documents.py'
module=ast.parse(source.read_text(encoding='utf-8'))
functions=[node for node in module.body if isinstance(node,ast.FunctionDef) and node.name in ('paragraph','image_xml','write_doc')]
assert len(functions)==3
exec(compile(ast.Module(body=functions,type_ignores=[]),str(source),'exec'),globals())

blocks=[
 ('title','Thesis项目组会汇报'),
 ('subtitle','实验记录截至2026年10月24日'),
 ('section','实验与结果'),
 ('body','已完成旧版Compact的100用户、18场景实验。对比规则画像R、单次大模型画像S和六角色依次分析画像M；各方案使用同一批用户与候选商品，按同一口径评价。'),
 ('body','原实验累计676次模型生成请求，运行与评价约2小时17分，形成5000条任务记录，其中4752条成功、248条模型失败。下图为本次使用已保存画像进行的离线复算：5000条状态及Top10与原记录一致，耗时117.86秒，未新增模型请求。'),
 ('image',str(PACK/'实验结果/终端结果截图.png')),
 ('caption','真实终端截图。HR与NDCG汇总16个V场景，Q1、Q2另做质量相关评价。'),
 ('field','R规则画像。HR@10＝0.217500；NDCG@10＝0.121012。'),
 ('field','S单次模型画像。HR@10＝0.195625；NDCG@10＝0.108129。'),
 ('field','M六角色画像。HR@10＝0.205625；NDCG@10＝0.102365。'),
 ('body','HR@10衡量目标商品能否进入前10名，NDCG@10进一步考虑排位。目前R的两项数值最高；M的HR略高于S，但NDCG低于S，尚未证实总体提升。下一步重点改进动态协作与偏好匹配，完成新B0与I1对照；这部分尚未完成。'),
 ('pagebreak',''),
 ('section','数据集简介'),
 ('body','数据采用真实谷物商品与评论，加同商品的模拟供应链材料。已固定100名用户，主表包括商品名称、完整评论、评分及六阶段属性，共42列；100行版每用户选最近一条历史评论，123条版保留这批用户的全部冻结历史。'),
 ('image',str(PACK/'配图/数据集样例.png')),
 ('caption','数据样例中的真实商品名称、评分和完整评论。'),
 ('body','真实评论先对应父商品标识，再连接该商品的SIM批次。采收、包装、仓储、检验、运输、零售属性与评论放在同一行，便于联合使用用户偏好和生命周期材料。SIM表示模拟材料，不代表该用户实际购买过该模拟批次。'),
 ('image',str(PACK/'配图/数据集_六阶段样例.png')),
 ('caption','同一条商品记录的六阶段属性示例；主CSV中这些属性位于同一行。'),
 ('body','这123条历史记录涉及75个不同商品，完整候选目录有1494个商品。异常和无关变化组成18个受控场景；留出目标只供评价使用。两份CSV随包提供，可直接打开查看行和列。'),
 ('pagebreak',''),
 ('section','多智能体设计与提示词'),
 ('body','系统设置需求解析、推荐管理、用户画像、农产品画像、生命周期追溯和推荐依据核验六个角色。这里以用户画像智能体为例：读取历史评论和可选属性，提取有依据的偏好，输出选项及权重，交给后续角色继续处理。'),
 ('image',str(PACK/'配图/用户画像智能体_卡通提示词模板.png')),
 ('caption','用户画像智能体提示词模板，按既有英文提示词整理的中文展示图。'),
 ('body','提示词主要约束三点：只选择给定属性；没有充分依据时保留空结果；不从评论中猜测批次质量、产地或认证。这样可以减少无依据的偏好推断。模板原文另附TXT，便于复制和调整。'),
]
document=write_doc('周组会汇报_实验结果_数据集_智能体设计.docx',blocks)

with (PACK/'数据集/01_商品评论与生命周期_100行展示.csv').open(encoding='utf-8-sig',newline='') as stream:
    shown=list(csv.DictReader(stream))
with (PACK/'数据集/02_商品评论与生命周期_完整123条.csv').open(encoding='utf-8-sig',newline='') as stream:
    full=list(csv.DictReader(stream))
assert len(shown)==100 and len(full)==123 and len(shown[0])==42
assert len({r['用户编号'] for r in full})==100
assert hashlib.sha256((PACK/'实验结果/终端结果截图.png').read_bytes()).hexdigest()==META['screenshot_sha256']
(PACK/'阅读说明.txt').write_text(
 '组会材料阅读顺序\n\n'
 '先打开Word，按“实验与结果—数据集简介—多智能体设计与提示词”阅读。\n'
 '实验结果使用原100用户18场景实验记录，以及用户提供的真实终端截图。截图为保存画像上的离线复算，不是再次发送模型请求。\n'
 '数据集目录提供100行展示版和原100用户全部123条冻结历史，两份均42列；完整评论未截断，生命周期字段明确标为SIM。\n'
 '最后以用户画像智能体举例，卡通图为既有英文提示词的中文展示模板。仅展示单个智能体，不附六角色流程长篇说明。\n'
 '配图目录保留卡通PNG及图像生成提示词；卡通图由内置imagegen生成，已核对正文文字。\n'
 '本包不含项目源码、运行脚本或逐字段长篇附件，未修改生产项目和原始实验。\n',encoding='utf-8-sig')
(BUILD/'documents.json').write_text(json.dumps(document,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(document,ensure_ascii=False,indent=2))
