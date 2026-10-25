"""Assemble data and prompt explanations; production inputs remain read only."""
import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(r'D:\Work\Codex\Project\Thesis')
BUILD = ROOT / '.scratch/meeting-revision-20261024'
OLD = ROOT / 'reports/组会完整材料_商品评论与生命周期_20261024'
OUT = ROOT / 'reports/组会修订材料_字段详解与多智能体设计_20261024'
DATA = OUT / '01_CSV数据与字段说明'
PROMPTS = OUT / '02_多智能体提示词与设计'
RESULTS = OUT / '03_终端截图与真实结果'
for path in (BUILD, DATA, PROMPTS, RESULTS / '离线重放'):
    path.mkdir(parents=True, exist_ok=True)
for name in ('01_商品评论与生命周期_100行展示.csv', '02_商品评论与生命周期_完整123条.csv'):
    shutil.copyfile(OLD / '01_商品评论与生命周期数据' / name, DATA / name)
shutil.copytree(OLD / '05_补充关系表', OUT / '04_补充关系表', dirs_exist_ok=True)
for name in ('旧版100用户_原始独立评价报告.md', '旧版100用户_原始逐场景评价.csv',
             'MACRec_v2_results.md', 'MACRec_v2_result-summary.json', 'MACRec_v2_closing-status.json'):
    shutil.copyfile(OLD / '04_运行截图与结果' / name, RESULTS / name)
for name in ('01_商品名称与完整评论_CSV视图.png', '02_同商品六阶段属性_CSV视图.png'):
    shutil.copyfile(OLD / '04_运行截图与结果' / name, DATA / name)

def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

full = read_csv(DATA / '02_商品评论与生命周期_完整123条.csv')
shown = read_csv(DATA / '01_商品评论与生命周期_100行展示.csv')
example = shown[0]
# Each entry explains this exported attribute rather than inventing a new measurement.
specs = [
 ('用户编号', '文本', '为本次冻结的100个来源账户分配的展示编号；同一账户的多条评论沿用同一编号。', '冻结账户映射', '用于把评论、候选和评价结果对应起来；不是用户名，也不是新的独立用户。'),
 ('商品标识', '文本', 'Amazon父商品标识parent_asin，表示评论所属的商品对象。', '真实评论及商品元数据', '连接商品目录与SIM批次的主关联键；不是批次号，不能把一个父商品当成某次真实生产批次。'),
 ('商品名称', '文本', '该父商品在来源元数据中的完整标题，保留英文原文。', '真实商品元数据', '用于识别商品及可观察的品类、形态等；标题中的产地或认证字样不是独立核验结论。'),
 ('商品类型', '分类文本', '筛选规则依据商品标题、成分和类别等信息形成的谷物类别；当前有corn玉米、rice稻米、oats燕麦、wheat小麦、barley大麦、millet小米。', '项目商品筛选与分类结果', '用于目录筛选和偏好匹配；它是规则分类结果，不是来源自带的实验检测标签。'),
 ('店铺名称', '文本 可空', '来源元数据提供的店铺或商店名称。', '真实商品元数据', '不等同于生产企业、农场或品牌。空白表示该字段缺失，不补造名称。'),
 ('品牌', '文本 可空', '来源元数据中可取得的品牌原文。', '真实商品元数据', '品牌缺失时留空，不能用店铺名自动补成品牌。完整123条中106条为空。'),
 ('评分', '数值 1至5', '该条真实评论给出的星级；5.0与5含义相同。', '真实评论rating', '这是用户反馈，不是算法预测分或可信分。本冻结历史当前只出现4和5，不代表原始全库没有低分。'),
 ('评论时间UTC', 'UTC时间', '该条历史评论的原始时间戳转换为UTC；末尾Z表示UTC。', '真实评论毫秒时间戳', '用于时间切分，历史须早于留出时刻。它与2026年的SIM材料时间分别保存，日本时间需加9小时。'),
 ('商品评论_完整文本', '文本', '保留该条冻结历史评论的完整正文，未按展示长度截断。', '冻结后的真实历史评论文本', '用于核对偏好提取；100行展示版仅选择记录，不改写正文。原始评论中的普通称赞不能自动推成具体属性偏好。'),
 ('SIM批次编号', '文本标识', '为该父商品确定性建立的正常场景模拟批次；b_后面是生成标识。', '既有SIM批次表', '把采收至零售材料归到同一批次；并非来源提供的真实商品批号，也不是区块高度或交易哈希。'),
 ('SIM采收开始UTC', 'UTC时间', '模拟采收阶段事件的开始时间。', 'SIM采收事件event_start_ms', '用于生命周期先后关系及事件覆盖核验，不表示真实采收发生于该时刻。'),
 ('SIM采收完成UTC', 'UTC时间', '模拟采收记录中的采收完成时刻。', 'SIM采收记录harvested_at_ms', '可与开始、包装等时刻比较，检查时间关系。'),
 ('SIM采收地区', '文本标识', '模拟采收地区对象编号；SIM-AREA-01是统一测试地区。', 'SIM采收记录origin_area_id', '不对应某个已核验省市或农场，不是地理坐标。'),
 ('SIM采收主体', '文本标识', '负责模拟采收事件的角色或主体编号。', 'SIM采收事件actor_id', 'SIM-PRODUCER表示模拟生产主体，不是来源商品的真实生产商名称。'),
 ('SIM包装时间UTC', 'UTC时间', '模拟包装绑定材料中的包装时刻。', 'SIM包装材料packaged_at_ms', '用于连接采收后包装与后续仓储；不等于商品上架或评论时刻。'),
 ('SIM包装状态', '分类文本', '模拟包装状况；当前正常基准的intact表示包装完整。', 'SIM包装材料package_condition', '异常实验可改变相关证据或状态；此正常主表不含实拍包装检测。'),
 ('SIM包装数量', '数值', '该模拟批次包装材料登记的数量，正常基准为100。', 'SIM包装材料quantity_units', '需与包装单位一起理解，不是100公斤、100条评论或实际销量。'),
 ('SIM包装单位', '分类文本', '包装数量所用的模拟计量单位；SIM_PACK表示模拟包装单位。', 'SIM包装材料unit', '因此100 SIM_PACK是受控场景数量，不能转换成真实重量。'),
 ('SIM仓储开始UTC', 'UTC时间', '模拟仓储日志覆盖区间的开始。', 'SIM仓储日志coverage_start_ms', '与结束时间共同定义该日志覆盖的时期，不是凭据登记时间。'),
 ('SIM仓储结束UTC', 'UTC时间', '模拟仓储日志覆盖区间的结束。', 'SIM仓储日志coverage_end_ms', '用于判断后续流程是否有仓储材料覆盖；不能单凭有日期就宣称实际仓储合规。'),
 ('SIM仓储方式', '分类文本', '模拟仓储片段的方式；SIM_DRY表示预设的干燥仓储模式。', 'SIM仓储日志segments中的mode', '这是模式标记，没有提供真实温度、湿度或传感器曲线。'),
 ('SIM抽样时间UTC', 'UTC时间', '模拟检验样本被采集的时刻。', 'SIM检验样本sampled_at_ms', '与检验起止时刻共同检查样本和报告时间关系。'),
 ('SIM检验样本编号', '文本标识', '模拟抽样材料的样本对象编号；s_后为生成标识。', 'SIM检验样本sample_id', '把样本与检验报告关联；不是用户编号、真实实验室流水号或链上交易号。'),
 ('SIM检验开始UTC', 'UTC时间', '模拟检验报告中的测试开始时刻。', 'SIM检验报告test_started_at_ms', '用于核验抽样在先、检验在后的过程关系。'),
 ('SIM检验完成UTC', 'UTC时间', '模拟检验报告中的测试完成时刻。', 'SIM检验报告test_completed_at_ms', '表示场景中报告完成的时间，不是本次程序计算耗时。'),
 ('SIM检验项目', '分类文本', '场景预设的模拟测试项目代号；SIM-Q1是协议中的检验项目标识。', 'SIM检验报告test_scope', '不代表某项真实农残、重金属或国家标准测试，未附实测浓度。'),
 ('SIM检验结论', '分类文本', '模拟报告的结论；正常基准pass表示该测试规则通过。', 'SIM检验报告conclusion', '它不等于实物质量认证，不是模型预测正确与否，也不是HR命中。'),
 ('SIM运输发运UTC', 'UTC时间', '模拟运输发运材料中的出发时刻。', 'SIM运输发运departed_at_ms', '与到货时间共同定义运输持续时间。'),
 ('SIM运输到货UTC', 'UTC时间', '模拟收货材料中该运输段到达的时刻。', 'SIM运输收货arrived_at_ms', '用于核验运输时序，不是订单签收的真实记录。'),
 ('SIM运输起点', '文本标识', '模拟运输的起始地点对象，当前为SIM-WAREHOUSE-01。', 'SIM运输发运from_location_id', '表示模拟仓库，不是已核验的实际仓库地址。'),
 ('SIM运输终点', '文本标识', '模拟运输的目的地点对象，当前为SIM-RETAIL-01。', 'SIM运输发运to_location_id', '用于与零售地点做一致性检查，主表不含真实GPS轨迹。'),
 ('SIM运输交接状态', '分类文本', '模拟收货材料的交接状态；accepted表示场景中已接收。', 'SIM运输收货handover_status', '不表示消费者本人已经收货，也不是API请求被服务商接收。'),
 ('SIM零售地点', '文本标识', '模拟零售状态所对应的地点对象。', 'SIM零售材料location_id', '可与运输终点核对；不是用户位置或店铺名称。'),
 ('SIM在售状态', '分类文本', '模拟零售观测中的商品状态；on_sale表示该场景为在售。', 'SIM零售材料status', '这是该模拟批次在指定观测时刻的状态，不是当前Amazon网页实时库存。'),
 ('SIM库存数量', '数值', '模拟零售观测中的库存单位数，正常基准为100。', 'SIM零售材料stock_units', '用于在售与库存偏好的受控实验，不是销量、评论量或模型置信度。'),
 ('SIM零售观测UTC', 'UTC时间', '模拟零售状态被观测、记录的时间。', 'SIM零售材料observed_at_ms', '用于判断材料的新鲜程度；不同于数据集下载时间和本次截图时间。'),
 ('SIM在售有效开始UTC', 'UTC时间', '该条模拟零售材料的有效区间起点。', 'SIM零售材料valid_from_ms', '评价时需结合核验时刻判断是否有效；不代表保质期起点。'),
 ('SIM在售有效截止UTC', 'UTC时间', '该条模拟零售材料的有效区间终点。', 'SIM零售材料valid_to_ms', '在有效区间外不应继续当作当前在售证据；不是食品保质期或生产日期。'),
 ('SIM生命周期阶段数', '整数', '该商品在正常SIM基准中关联的生命周期事件阶段数量，当前为6。', 'SIM事件按商品计数', '六阶段为采收、包装、仓储、检验、运输、零售；不是智能体数或证据材料数，材料类型实际为8种。'),
 ('真实记录来源', '文本', '标注商品与历史评论所用的数据集名称Amazon Reviews 2023。', '数据来源声明', '2023表示数据集版本名称；不要求每条评论都发表于2023年。'),
 ('生命周期来源', '文本', '标注生命周期属性来自同商品SIM供应链材料。', 'SIM来源声明', '与真实记录来源分列，便于直接区分真实反馈和受控场景材料。'),
 ('商品批次关联说明', '文本', '明确连接关系是父商品相同的实验关联。', '本表关联口径说明', '防止把历史评论误认成对SIM批次的真实购买评价；没有把两个无关商品硬拼在一起。'),
]
assert [x[0] for x in specs] == list(full[0]) and len(specs) == 42
fields = []
for index, (name, kind, meaning, source, use) in enumerate(specs, 1):
    values = {r[name] for r in full}
    fields.append({'序号': index, '字段': name, '格式': kind, '含义': meaning,
                   '实际示例': example[name] or '空白（来源未提供）', '来源': source,
                   '用途与注意点': use, '完整123条中的空值数': sum(r[name] == '' for r in full),
                   '完整123条中的不同取值数': len(values)})
with (DATA / '03_42个字段逐项详解.csv').open('w', encoding='utf-8-sig', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(fields[0]), lineterminator='\r\n')
    writer.writeheader(); writer.writerows(fields)

role_specs = {
 '需求解析': ('当前请求及允许的条件编号。', '必要条件necessary、明确偏好preferences、未知项unknown。',
             '把当前请求与历史偏好分开，避免把以前喜欢的商品当成此次硬要求。当前未明确偏好时允许为空。'),
 '推荐管理': ('解析结果、已完成的分析、工具实际返回和当前求解状态。', '简短判断Thought，以及User、Items、Search或Finish中的一个Action。',
             '决定下一步需要谁分析、需要哪些材料；Thought和Action属于同一角色。B0输出排序，I1组织匹配矩阵并由宿主计分。'),
 '用户画像': ('可见历史评论、允许的商品属性，以及当次明确偏好。', '最多六项属性偏好，附权重、精确历史引用和正负立场。',
             '从评论中找真正有依据的偏好；没有依据可返回空画像。宿主继续检查引用和冲突，并按独立历史商品支持计算置信度。'),
 '农产品画像': ('候选商品目录、验证后的偏好，以及已经取得的库存观察。', 'B0输出有来源的比较；I1输出每个候选与每项偏好的匹配值m和来源码f。',
             '负责商品和偏好的对应。m取0、0.25、0.5、0.75、1或未知；f区分标题、类别、库存、未知。未知不能当作满足。'),
 '生命周期追溯': ('允许访问的候选编号及当前工具观察。', 'Lookup或Search材料请求；实际观察到材料后形成总结。',
             '模型提出取证需求，宿主工具检查来源、批次、材料和时序，计算资格与质量；模型不能自行编造检测结论。'),
 '推荐依据核验': ('当前解、协作轨迹、来源引用，重点是Top10与第8至15名边界。', '是否需要修改revise，以及定位到候选、属性、引用和问题的issues。',
             '只在发现有依据的问题时建议修订，不为产生变化而强制改排名。当前v2尚未真正发送该反思分支。'),
}
source_prompts = OLD / '03_六角色提示词'
common = (source_prompts / '00_公共约束原文.txt').read_text(encoding='utf-8-sig').strip()
(PROMPTS / '00_公共提示词原文.txt').write_text(common + '\n', encoding='utf-8-sig')
roles = []
for index, (role, details) in enumerate(role_specs.items(), 1):
    source_path = source_prompts / f'{index:02}_{role}.md'
    source_text = source_path.read_text(encoding='utf-8-sig')
    variants = []
    for chunk in re.split(r'^## ', source_text, flags=re.M)[1:]:
        title = chunk.splitlines()[0].strip()
        if '探针' in title:
            continue
        found = re.search(r'```text\s*\n(.*?)\n```', chunk, flags=re.S)
        if not found:
            continue
        complete = found.group(1).strip()
        assert complete.startswith(common)
        business = complete[len(common):].strip()
        state = re.search(r'^状态：(.*)$', chunk, flags=re.M)
        variants.append({'title': title, 'prompt': business, 'status': state.group(1).strip() if state else ''})
    assert variants, role
    info = {'role': role, 'input': details[0], 'output': details[1], 'design': details[2], 'variants': variants}
    roles.append(info)
    text = f'# {role}\n\n输入：{details[0]}\n\n输出：{details[1]}\n\n设计：{details[2]}\n\n下列业务提示须接在00号公共提示词之后，两者合起来才是完整system提示词。B0和I1按实验方法分别选用。\n'
    for variant in variants:
        text += f"\n## {variant['title']}\n\n{variant['status']}\n\n{variant['prompt']}\n"
    (PROMPTS / f'{index:02}_{role}_设计与完整业务提示词.md').write_text(text, encoding='utf-8-sig')
shutil.copyfile(source_prompts / '07_旧版Compact六角色.md', PROMPTS / '07_旧版Compact_对应HR与NDCG的提示词.md')
shutil.copyfile(source_prompts / '提示词来源清单.json', PROMPTS / '提示词来源清单.json')

intro = (
 '两份CSV均覆盖同一批冻结的100名用户：100行版每用户选最近一条可见历史评论；123条版保留全部冻结历史。\n'
 '一行是一条历史评论及其父商品关联的正常SIM属性，42列不是算法超参数。\n'
 '完整123条覆盖75个不同历史商品；完整候选目录另有1494个商品，不能混淆。品牌106条为空、店铺2条为空。\n'
 '正常SIM采用统一的基准时间、包装、仓储、检验和库存，因此多个商品出现相同值是场景设定；18场景变化另见补充关系表。\n'
 'SIM时间不强行与历史评论时间对齐；该关联不表示用户购买过模拟批次。目标评论保留在仅评价目录。\n'
 'UTF-8 BOM标准CSV，逗号分隔，含逗号或换行的正文按CSV引号规则保存。用Excel或WPS按CSV规则打开即可。\n'
)
(DATA / '请先了解数据含义.txt').write_text(intro, encoding='utf-8-sig')
provenance = {'source_package': str(OLD), 'users': 100, 'display_records': 100,
              'full_records': 123, 'history_products': 75, 'candidate_products': 1494,
              'columns': 42, 'source_csv_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in DATA.glob('0[12]_*.csv')}, 'new_model_api_calls': 0}
(OUT / '数据来源与文件校验.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding='utf-8')
(BUILD / 'content.json').write_text(json.dumps({'fields': fields, 'roles': roles, 'common': common, 'intro': intro,
                                              'example': example, 'package': str(OUT)}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'package': str(OUT), 'fields': len(fields), 'roles': len(roles),
                  'normal_prompt_variants': sum(len(r['variants']) for r in roles), 'code_files_copied': 0}, ensure_ascii=False))
