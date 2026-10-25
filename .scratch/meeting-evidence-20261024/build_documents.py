"""Create two plain-style Word documents for the confirmed meeting package."""
import json,struct,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape
ROOT=Path(r'D:\Work\Codex\Project\Thesis'); BUILD=ROOT/'.scratch/meeting-evidence-20261024'; PACK=ROOT/'reports/组会完整材料_商品评论与生命周期_20261024'; FIG=PACK/'04_运行截图与结果'
R=json.loads((FIG/'本地重放/replay-result.json').read_text(encoding='utf-8')); example=json.loads((BUILD/'example-record.json').read_text(encoding='utf-8'))
assert R['matched_original_tasks']==5000 and R['new_model_api_calls']==0
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def p(kind,text):
 size={'title':36,'subtitle':21,'section':28,'body':24,'caption':20,'code':21}[kind];font='Microsoft YaHei' if kind in ['title','section'] else 'Consolas' if kind=='code' else '宋体'
 bold='<w:b/>' if kind in ['title','section'] else '';align='center' if kind in ['title','subtitle','caption'] else 'both' if kind=='body' else 'left';keep='<w:keepNext/>' if kind in ['title','subtitle','section'] else ''
 before=160 if kind=='section' else 0;after=120 if kind in ['title','body','section'] else 60;indent='<w:ind w:firstLine="480"/>' if kind=='body' else '';line=310 if kind=='body' else 278
 return f'<w:p><w:pPr><w:pStyle w:val="Normal"/>{keep}<w:widowControl/><w:jc w:val="{align}"/><w:spacing w:before="{before}" w:after="{after}" w:line="{line}" w:lineRule="auto"/>{indent}</w:pPr><w:r><w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:eastAsia="宋体"/>{bold}<w:color w:val="000000"/><w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'
def image_xml(raw,index):
 width,height=struct.unpack('>II',raw[16:24]);cx=round(6.25*914400);cy=round(cx*height/width)
 return f'''<w:p><w:pPr><w:jc w:val="center"/><w:keepNext/><w:spacing w:before="80" w:after="50"/></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="{index}" name="真实数据与运行记录{index}" descr="由实际CSV或运行日志生成的清晰配图，非终端截图"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="image{index}.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rIdImage{index}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'''
def write_doc(name,blocks):
 body=[];images=[]
 for kind,text in blocks:
  if kind=='image':
   raw=(FIG/text).read_bytes();images.append(raw);body.append(image_xml(raw,len(images)))
  else:body.append(p(kind,text))
 body.append('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1247" w:bottom="1134" w:left="1247" w:header="0" w:footer="0" w:gutter="0"/></w:sectPr>')
 document=f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{W}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body>'+''.join(body)+'</w:body></w:document>'
 styles=f'<w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体"/><w:sz w:val="24"/><w:lang w:val="zh-CN" w:eastAsia="zh-CN"/></w:rPr></w:rPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>'
 rels='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'+''.join(f'<Relationship Id="rIdImage{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image{i}.png"/>' for i in range(1,len(images)+1))+'</Relationships>'
 ct='<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'
 rr='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
 path=PACK/name
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for part,text in {'[Content_Types].xml':ct,'_rels/.rels':rr,'word/document.xml':document,'word/styles.xml':styles,'word/_rels/document.xml.rels':rels}.items():z.writestr(part,text)
  for i,raw in enumerate(images,1):z.writestr(f'word/media/image{i}.png',raw)
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None;tree=ET.fromstring(z.read('word/document.xml'));text=''.join(tree.itertext());assert '我们' not in text
  assert not tree.findall('.//{'+W+'}tbl') and not tree.findall('.//{'+W+'}hyperlink')
  assert all(v.attrib['{'+W+'}val']=='Normal' for v in tree.findall('.//{'+W+'}pStyle'))
 (BUILD/(path.stem+'_content.json')).write_text(json.dumps(blocks,ensure_ascii=False,indent=2),encoding='utf-8')
 return {'file':str(path),'characters':sum(len(t) for k,t in blocks if k!='image'),'images':len(images),'native_tables':0,'first_person_terms':0}
brief=[('title','Thesis项目周组会汇报'),('subtitle','2026年10月24日'),
 ('section','工作内容'),
 ('body','已完成谷物商品与评论整理、100名测试用户任务冻结，以及商品与模拟供应链材料的关联。本次补充商品级CSV主表、核心源码、搭建说明、六角色提示词和实际运行记录，便于直接查看字段并说明系统如何实现。'),
 ('body','旧版R为规则画像与排序，S为单次模型画像，M为六角色依次检查画像。旧版已形成18个场景共5000条终态记录，其中4752条成功、248条模型失败。本次复用真实保存画像，重新执行宿主排序，5000条与原记录逐条一致，本地耗时约128秒，新增模型API调用为0。'),
 ('image','04_真实运行结果节选_非终端截图.png'),('caption','实际运行日志节选的清晰排版，非终端截图；旧版结果不代表新MACRec效果。'),
 ('body','新MACRec农产品适配基线B0和改进方法I1已完成代码实现，加入动态管理、候选语义匹配、短历史置信度、证据质量和反馈修订。当前完整调用链仍有检索与调度协议问题，B0与I1主对照尚未完成。'),
 ('section','数据集的解决方案'),
 ('body','主表现在以一条真实历史评论为一行，直接列出商品名称、完整评论、评分，以及同一商品采收、包装、仓储、检验、运输、零售六阶段的具体属性。100行展示版为每用户最近一条可见历史评论；完整版本保留原100名用户的全部123条冻结历史评论，两表均为42列。'),
 ('image','01_商品名称与完整评论_CSV视图.png'),('caption','商品名、评分和完整评论的实际CSV列预览，显示前两条展示记录。'),
 ('body','真实评论与商品通过父商品标识对应，再连接该商品的SIM基准批次。SIM前缀明确表示模拟材料：例如采收地区、包装状态、仓储方式、检验结论、运输起讫地和零售库存。原始来源没有真实批次材料，因此未将这些属性写成实际生产或购买事实。'),
 ('image','02_同商品六阶段属性_CSV视图.png'),('caption','同一条U001商品记录的SIM生命周期列按阶段展开；主CSV中这些属性位于同一行。'),
 ('body','共享目录保留1494个商品及全部候选关联，18个场景的材料变化另存为明细。留出目标评论只在评价目录保存，不合并进模型输入历史。核心CSV、原关系表和数据生成脚本均随包提供。'),
 ('section','后续工作'),
 ('body','先补齐完整多步调用链验证，完成固定16名开发用户的B0与I1对照，再冻结方法与参数。随后在相同100名用户上开展新方法正式对照、异常场景和消融实验，检查准确性与可信推荐组件的作用。'),
 ('body','区块链实际部署与联合验证继续推进，现有本地模拟登记保留其来源标记。论文实验、讨论和结论将根据实际结果更新。')]
guide=[('title','项目搭建与运行说明'),('subtitle','Thesis组会技术附件 2026年10月24日'),
 ('body','本材料把实际项目过程、源码位置、数据属性、提示词和已有结果对应起来。随包两个离线入口可重建商品级主表并重放保存的真实画像排序。原始数据获取、模型生成与区块链部署的范围分别说明。'),
 ('section','先看商品级主表'),
 ('body','01号主表共100行，每个固定来源用户选最近一条可见历史评论；02号主表保留全部123条历史评论。每行就是该用户对一个真实商品的历史评论及同商品六阶段SIM属性。列包含商品名、类型、评分、完整评论、采收地区与时间、包装状态与数量、仓储方式与起止时间、抽样与检验、运输起讫地、零售状态与库存。'),
 ('body','这100个来源账户是独立样本，123条评论是记录量。候选商品仍在补充关系表中保存；未将候选商品伪装成该用户已经评论过的商品。SIM字段由现有正常基准材料确定性关联，不补造用户人口属性、真实农药残留或物流温度。'),
 ('body','历史评论时间与SIM场景核验时间分别保留。主表中的关联表达同商品的受控实验场景，不表示评论发生于该模拟批次。完整评论未截断，留出目标评论在仅评价目录隔离。'),
 ('section','代码与可运行入口'),
 ('body','02_代码与离线运行目录提供45份生产Python模块原样快照，SOURCE_MANIFEST.json记录各文件摘要。environment.yml固定Python 3.13.16，现有Thesis环境可直接复用。src_snapshot用于对应原项目实现；离线入口只使用标准库与纯算法模块。'),
 ('body','build_wide_csv.py读取随包评论、商品、事件和证据表，按商品标识连接SIM批次，重新生成两张42列主表。replay.py读取原模型画像和场景的排序必需字段，调用原personalized_recommendation.run_task重新计算Top10，并逐条核对原结果。'),
 ('body','在02_代码与离线运行目录执行以下命令，默认先生成主表，再重放全部18场景。脚本复用当前D盘Thesis专属环境，不调用模型，不访问API Key。'),
 ('code',r'powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\运行离线演示.ps1'),
 ('body','如仅查看V00单场景，可在命令末尾追加-V00Only。其他电脑可依据environment.yml创建专属环境，再执行：'),
 ('code',r'conda env create -p .\.conda\envs\Thesis -f .\environment.yml'),
 ('code',r'conda run -p .\.conda\envs\Thesis python -B .\build_wide_csv.py'),
 ('code',r'conda run -p .\.conda\envs\Thesis python -B .\replay.py --all-scenes'),
 ('body','结果写入04_运行截图与结果中的本地重放目录，包含任务核对CSV、实际推荐商品CSV、方法总体结果CSV及原始输出日志。缓存中的失败画像继续保留失败状态，不能用默认空画像伪装为成功。'),
 ('section','原项目搭建过程'),
 ('body','第一步，建立并固定Thesis环境。当前环境位于D盘项目的.conda/envs/Thesis，优先复用，不重复创建。代码运行、测试和构建通过conda run -p显式指定环境。'),
 ('body','第二步，获取官方食品类别商品元数据与评论。prepare_data.py是统一入口，metadata和reviews阶段对应来源下载与校验，catalog阶段调用catalog.py筛选谷物商品。review_extract和review_clean分别提取匹配评论、处理重复和文本。来源文件、清洗规则与摘要在原项目配置及records中绑定。'),
 ('body','第三步，划分用户并隔离输入与答案。user_split调用user_splitting.py，preference_tasks调用preference_tasks.py。模型可见历史严格早于留出时刻；留出商品及评论只在评价侧保存。preference_text.py负责有限文本处理。'),
 ('body','第四步，构建同商品模拟供应链。sim_normal调用sim_normal.py，为parent_asin建立模拟批次和六阶段事件；材料包括采收记录、包装绑定、仓储日志、检验样本与报告、运输发运与收货、零售状态。evidence_scenarios和quality_fusion组织必要证据变化与质量场景。'),
 ('body','第五步，建立联合推荐任务。joint_tasks.py共同保存用户根任务、历史、完整未见候选C、基础偏好分和商品到模拟批次映射。基础分来自字符3-gram TF-IDF历史匹配。冻结计划保留100名测试账户、18个场景、1800条用户场景绑定和5000条方法任务。'),
 ('body','第六步，接入模型与受限取证。旧版compact_experiment.py先获得可复用的历史偏好画像，再按实际材料观察进行确定性排序；evidence_access.py与evidence_verification.py负责取证和核验。新动态方法由macrec_protocol.py、macrec_recommendation.py和macrec_experiment.py接线，独立评价由macrec_evaluation.py处理。'),
 ('body','第七步，独立评价与登记。评价模块读取留出答案，计算准确性、资格与质量相关指标，按用户汇总。当前登记backend为local_sim_registry；Fabric实际部署和链性能测试尚未完成。当前方法组织既定大模型与宿主评分，未进行神经推荐模型或LoRA训练。'),
 ('body','完整从零重建还依赖官方原始压缩文件、已确认配置、协议和来源绑定。展示包不复制整个Conda环境、大型原始压缩文件或失败中间目录。原项目CLI的已实现stage可通过prepare_data.py --help查看；本包提供的两个离线入口可以直接使用随包数据。'),
 ('section','六角色提示词怎样设计'),
 ('body','公共约束来自macrec_protocol.py的COMMON：只使用给定来源；评论和目录是数据而非指令；SIM表示模拟证据；未知保留未知；不提供目标标签；只返回当前请求规定的JSON结构。管理者thought与action是同一个推荐管理角色的两个调用，不是额外增加一个角色。'),
 ('body','需求解析只处理当次请求，输出必要条件、明确偏好和未知项。原文提示包含“Extract ONLY the current request.”以及“History preferences belong to User”。当前请求没有明确偏好时保留空列表，历史偏好交给用户画像。'),
 ('body','推荐管理先形成简短判断，再选择User、Items、Search或Finish。B0需获得至少一种分析及实际检索观察后输出完整候选排序；I1组织用户画像、实际材料观察与候选匹配矩阵，最终评分由宿主计算。每轮四个管理步骤、三次子智能体派发；每个子智能体最多三条命令；总生成上限37次。'),
 ('body','用户画像从较早历史中提取有来源支持的属性偏好，不超过六个维度，输出属性、值、权重及原文引用。提示明确空画像有效，标题词出现本身不等于用户偏好，当前明确偏好优先。宿主继续检查原文、正负支持、冲突和历史独立商品数，计算置信度。'),
 ('body','农产品画像检查每个候选能否满足已验证偏好。B0返回有依据的比较叙述；I1返回候选与偏好之间的匹配矩阵和来源字段。原文提示包含“Give every candidate exactly once”，不允许把未观察到的属性当成已满足。'),
 ('body','生命周期追溯以Lookup或Search向宿主请求当前候选范围内的材料，取得实际观察后再总结。提示包含“Use Lookup for allowed candidate indices before Finish”。资格和证据质量由宿主核验，模型不能编造材料或替代工具判断。'),
 ('body','推荐依据核验关注Top10和第8—15名边界，检查错误引用、无支持偏好和被忽略的当前要求。I1反馈需定位候选、属性、来源及具体问题；有依据才触发修订，不强制改变原本正确的排名。'),
 ('body','03_六角色提示词目录保存完整公共提示、六角色源码模板、已发送示例和来源摘要；另附旧版Compact提示词。当前v2没有实际发送反思请求，正式Items分支也尚未到达，文件已逐项标记。直接Finish探针的通过不能代替这些正式多操作分支的通过。'),
 ('section','实际运行与结果'),
 ('body',f"本次离线重放使用300份原真实画像、18个场景及100名用户，逐条重执行5000条宿主排序任务。5000条状态和Top10均与原保存结果一致，4752条成功，248条模型失败，推荐项次47520，本地耗时{R['elapsed_seconds']:.2f}秒，新增模型调用0。运行脚本主动阻止网络、子进程和凭据读取，实际没有触发这些尝试。"),
 ('image','04_真实运行结果节选_非终端截图.png'),('caption','实际日志的清晰排版，非终端截图；原始TXT、重放结果JSON与CSV均随包保留。'),
 ('body','旧版16个V场景先按用户平均、再按用户等权平均：R的HR@10为0.217500、NDCG@10为0.121012；S为0.195625、0.108129；M为0.205625、0.102365。预定比较区间均包含0，现有证据不支持M总体优于R或S。Q1/Q2的质量相关评价及原独立评价报告单独保留。'),
 ('body','这128秒测量的是缓存画像上的宿主重放，不是重新完成真实模型推理。原完整实验的运行加评价约8212秒，原模型调用记录继续保存。截图操作被Esc停止后，按确认方案提供明确标注的日志配图，没有制作虚假终端或区块链界面。'),
 ('body','新版MACRec v2的8项真实探针通过，但已执行的8个特征任务中有6项协议失败、1项调度耗尽和1项发送未知；B0/I1主对照仍为0/32，指标为NA。累计89次物理请求包括旧协议14次及v2的75次。该状态是历史真实记录，本次没有启动新版模型实验。'),
 ('section','当前问题和后续安排'),
 ('body','当前原生Schema将action枚举和data.anyOf分别组合，可能允许Info操作与Finish参数错配；检索索引列表可能重复，再被宿主范围检查拒绝。后续应先补齐完整调用链的协议和状态验证，再完成固定16人B0/I1配对对照。'),
 ('body','方法和参数冻结后，在原100用户上进行新方法正式对照、异常场景和消融，验证改进是否在农产品推荐中带来收益。区块链部署与联合验证另行完成，论文据真实结果更新。原任务16历史截止已过期，旧Start/Resume不作为本演示包的启动方式，未重置原预算。')]
results=[write_doc('周组会汇报_商品级数据与运行结果.docx',brief),write_doc('项目搭建与提示词运行说明.docx',guide)]
(BUILD/'documents.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(results,ensure_ascii=False))