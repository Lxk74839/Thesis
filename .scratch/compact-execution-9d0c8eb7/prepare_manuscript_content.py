"""Populate the manuscript's result slots from the independent, immutable evaluation."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
r = json.loads((HERE / 'results.json').read_bytes())
s = json.loads(Path(r['evaluation_summary_ref']['path']).read_bytes())
assert r['terminal'] == 'complete' and r['tasks_recorded'] == 5000
assert all(c['interval'][0] <= 0 <= c['interval'][1] for c in r['primary_comparisons'].values())
real, comparisons, feedback = r['real_preference_all16V'], r['primary_comparisons'], r['feedback']
resources = r['resources']
f = lambda x: f'{x:.6f}'
ci = lambda v: '[' + ', '.join(f(x) for x in v) + ']'
metric = lambda method, k, name: real[method][str(k)][name]['estimate']
quality = {row['scene']: row for row in r['quality_scenes']}
fb = feedback['exploratory_at10']
components = r['component_preference_all16V']

content = {'replace': {}, 'insert_after_111': []}
p = content['replace']
p['1'] = (
    '摘要：针对农产品推荐中用户偏好与分散生命周期材料难以共同参与决策的问题，提出一种基于区块链与多智能体技术的农产品可信推荐方法。'
    '方法由全链路证据管理与多智能体推荐两个模块组成，通过同商品关联组织真实评论与模拟生命周期记录。需求解析、推荐管理、用户画像、农产品画像、'
    '生命周期追溯和推荐依据核验六角色形成有来源的画像，结合基础分、偏好匹配与证据质量排序，并以必要条件限制候选资格。采用画像准备、共享材料核验和'
    '全候选场景回放，在固定100个测试账户、18场景中形成5,000条终态记录，其中248条模型失败均保留。16个V场景的R、S、M方法NDCG@10分别为'
    f"{metric('R', 10, 'NDCG_P'):.4f}、{metric('S', 10, 'NDCG_P'):.4f}和{metric('M', 10, 'NDCG_P'):.4f}。"
    '四项预定主比较的区间均包含0，未支持多角色画像或质量组件的总体正收益；核验前后的小幅变化仅作探索性结果。'
    '本轮验证了可审计的计算与评价流程，尚不能证明推荐效果优越或现实商品安全；Fabric账本接入与性能仍待后续验证。')
p['88'] = '4 实验与结果'
p['65'] = (
    '当前100用户协议将画像生成限制为最多700次，场景采用固定画像回放；新增实验产物总额不超过10GiB，运行和评价共用24小时截止。'
    '达到限制时保留已完成、失败和未完成任务，不减少评价分母。上述为预设资源停止条件，本轮已完成的实际生成次数、耗时与新增空间见第5.3节。')
p['89'] = (
    '实验围绕三个问题组织：结构化画像是否改善偏好推荐，材料质量是否改变合格候选比较，画像核验是否产生有益修订。'
    '本轮已完成固定100个测试账户、全部18场景的一轮正式运行和独立评价，分别报告真实留出目标的偏好指标、SIM资格核对和评分组件结果。'
    '公开功能核验用于检查实现，正式对照用于估计本样本中的表现，二者不混为同一种证据。')
p['104'] = (
    '材料枚举、读取与核验记录在共享预处理项下，画像请求Token仅采用供应商实际返回的usage，缺失保持未知；小型收据与原件引用代替逐步复制完整材料和状态。'
    '运行与评价共用新增10GiB和24小时上限，生成尝试最多700次，使用单一模型工作进程。失败响应归入传输／协议类，本地画像校验另记；'
    '现有收据没有HTTP细分故障原因，不将该分类进一步推断为某种供应商故障。已完成或未决请求均不得自动重发。')
p['108'] = (
    '上述功能核验验证程序是否按定义处理偏好、材料和失败，不估计真实用户满意度，也不将测试断言数量当成独立实验样本。'
    '本轮继承受审候选的35项必要测试及Standards／Spec双轴审查，正式模型结果另见4.4节；没有因正式指标不利而修改参数、名单或补跑失败请求。')
p['111'] = (
    '正式入口按冻结顺序处理100个测试账户，每人50条方法任务，独立入口在运行结束后读取真实留出目标与场景参考。'
    '5,000条任务均具备终态，其中4,752条为ok、248条为模型失败，未完成、未启动、未决及评价流水线错误均为0；86位用户的全部方法均成功。'
    'R、S、M分别有100、98、88个成功画像，模型失败仍保留在全体用户指标中。546条任务的约束参考不适用，该标记不删除其真实偏好评价。')
p['113'] = (
    '本轮100个账户中，85个只涉及1个不同的正向历史商品，9个涉及2个，5个涉及3个，1个涉及5个，历史长度中位数为1；留出目标涉及57个父商品。'
    '因此偏好属于既定grain-A目录内的短历史推断，18个派生场景不增加独立用户数。原8场景共同适用人群U8为86人，Q共同适用人群UQ为100人，'
    '不据区间宽度或指标结果追加、删除账户，也不声称100用户已达到既有样本充分性目标。')
p['115'] = (
    '数据来源见Amazon Reviews 2023官方项目[26]。实现协议为personalized-compact-0.1.0，配置摘要为9d0c8eb7，受审代码候选为4e63a107；'
    '完整配置、代码摘要、原计划标识和数据引用保存在本地运行记录。冻结100账户与18场景清单沿用原计划，提示词与输入摘要在启动前核对。'
    '生成响应、失败终态、画像修订、共享材料及逐任务结果保留首次收据，评价输出和资源账另存；复现材料尚未公开归档。')
p['120'] = (
    '数据范围为既定grain-A目录和父商品层短历史推荐，尚不覆盖全部农产品、具体SKU和真实批次购买。R在本轮真实偏好指标上较高，M未显示总体优势；'
    'M与S分别有12和2个失败画像，主比较包含这些实际失败。成功画像上的组件描述不能替代全体用户的端到端结果。'
    '库存偏好是Q场景的受控请求，质量中的覆盖度和一致性在既有质量场景中通常为常量，不能据此宣称三项质量因子的独立贡献均已验证。'
    '标题词仍可能反映品牌或偶然描述，当前固定样本和条件区间也不支持跨品类或总体满意度推广。')
p['122'] = (
    '画像准备和固定材料核验的成本均纳入本轮资源账。共记录676次生成尝试，663次取得符合响应结构的返回、13次传输／协议失败，无未决；'
    '另有1次核验角色变更画像但没有说明原因，被本地主机拒收，故共14个失败画像。未知用量不按成功请求均值填补。'
    f"已知输入Token为{resources['native_usage']['input_tokens']['known_subtotal']:,}，输出为{resources['native_usage']['output_tokens']['known_subtotal']:,}，"
    f"合计{resources['native_usage']['total_tokens']['known_subtotal']:,}，13次请求的用量未知；单价与总费用为null。"
    f"运行{resources['run_seconds']:.1f}秒，独立评价{resources['evaluation_seconds']:.1f}秒，二者合计{resources['run_plus_evaluation_seconds']:.1f}秒；"
    f"共享预算起算至评价结束{resources['shared_budget_elapsed_seconds']:.1f}秒，包含阶段间等待{resources['between_stages_wait_seconds']:.1f}秒。"
    f"运行与评价产物{resources['experiment_output_bytes']:,}字节（约{resources['experiment_output_bytes']/1024**2:.2f}MiB，不含论文排版文件），未触及上限。"
    '共享材料预处理另有914,328次逻辑工具调用、53,784次物理工具调用，属于本地材料操作，不计作供应商生成调用。'
    '同一画像跨场景复用，3,400个模型方法任务不等于3,400次API生成；离线场景回放也不代表逐场景实时六角色取证。')
# Source counts are taken from the actual shared-preprocessing ledger, not estimates.
p['122'] = p['122'].replace('914,328', f"{resources['shared_preprocessing']['logical_tools']:,}").replace(
    '53,784', f"{resources['shared_preprocessing']['physical_tools']:,}")
p['125'] = (
    '本轮正式执行已完成，现有结果不支持直接宣称方法优越。后续工作应在独立开发资料上检查画像稳定性、失败传播及基础分与偏好贡献的关系，'
    '如需改变模型、提示词、参数或运行协议，应另行冻结设计并采用独立评价，不能反复使用本轮测试目标调参。'
    '预训练语义编码器、BPR或LightGCN仍仅为后续比较方向，本轮没有实施这些训练或填入其预期结果。')
p['130'] = (
    '本轮完成固定100用户18场景的一轮运行与独立评价，保留全部5,000条终态及248条失败。R的真实偏好NDCG@10高于S和M，'
    'M−S、M−R和两项质量组件主比较的98.75%边际区间均包含0，尚未获得总体提升证据。88个成功M画像中的16个发生选项或权重变化，'
    '反馈差值较小且探索性区间包含0，不能作为确定收益。SIM材料下的零违规支持本轮规则响应检查，不证明现实商品安全。'
    '七个主公式、双模块和六角色保留其计算与审计作用，Fabric部署及性能仍为后续工作。')

blocks = content['insert_after_111']
def para(text):
    blocks.append({'paragraph': text})
def add_table(caption, rows, widths):
    blocks.extend([{'caption': caption}, {'rows': rows, 'widths': widths}])

para('表5使用全部100用户的16个V场景，先在用户内等权平均，再在用户间等权平均；失败按冻结评价口径计入。'
     'HR和NDCG使用真实单个留出目标，数值不是SIM资格命中率。Q1/Q2只有M及其组件，不计入R/S/M三方法对照。')
rows = [['方法', 'HR@1', 'NDCG@1', 'HR@5', 'NDCG@5', 'HR@10', 'NDCG@10']]
for method in ('R', 'S', 'M'):
    rows.append([method] + [f'{metric(method, k, m):.4f}' for k in (1, 5, 10) for m in ('HR', 'NDCG_P')])
add_table('表5 真实留出目标偏好指标（16个V场景，n=100）', rows, [900] + [1362] * 6)
e = r['exploratory_real_preference_at10']
para('作为描述性不确定性报告，NDCG@10的95%用户重采样区间分别为R '
     f"{ci(e['R_NDCG_P']['interval'])}、S {ci(e['S_NDCG_P']['interval'])}、M {ci(e['M_NDCG_P']['interval'])}。"
     '这些区间未经多重比较调整，预定的四项主比较另见表6。M的HR@10略高于S，但NDCG@10较低，R的两项指标均较高，不能概括为M总体改善。')
labels = {'C1': 'C1 M−S', 'C2': 'C2 M−R', 'C3': 'C3 完整−无质量', 'C4': 'C4 完整−均值质量'}
rows = [['比较', 'n', '均值差', '98.75%边际区间']]
for label in ('C1', 'C2', 'C3', 'C4'):
    c = comparisons[label]
    rows.append([labels[label], str(c['n']), f(c['estimate']), ci(c['interval'])])
add_table('表6 预定成对比较（SJ-NDCG@10）', rows, [2200, 600, 1800, 4472])
para('C1、C2在原8场景共同适用人群U8上比较，C3、C4在Q1/Q2共同适用人群UQ上比较；'
     '50,000次成对用户重采样和98.75%边际区间对应近似家族同时覆盖95%，条件于固定资料。四个区间均包含0，未支持预定的总体正收益。'
     'U8的86人由独立参考适用性确定，其中11人存在保留的模型失败，共88条原8场景失败任务；该86人不是排除失败后的成功用户子集。')
rows = [['组件', 'Q1（n=100）', 'Q2（n=100）', '两场景均值']]
for mode in ('full', 'no_quality', 'mean_quality'):
    values = [quality[q]['components'][mode] for q in ('Q1', 'Q2')]
    rows.append([mode] + [f(v) for v in values] + [f(sum(values)/2)])
add_table('表7 质量评分组件的真实目标SJ-NDCG@10', rows, [2400, 2224, 2224, 2224])
para('Q1/Q2的独立参考均适用100人，主比较保留12个M画像失败产生的零值。质量组件基于同一实际画像、资格集合与材料重算；'
     '完整质量在Q1低于无质量及均值质量，在Q2高于二者，两场景平均差未取得明确正收益。'
     '在88个成功M锚点中，完整质量相对无质量的前10序列分别在Q1的87项、Q2的88项任务改变，说明质量进入排序；排序变化本身不等于真实偏好改善。')
rows = [['组件／画像', '条件人数', 'HR@10', 'NDCG@10']]
for mode in ('full', 'base', 'uniform_weights', 'no_quality', 'mean_quality', 'no_feedback'):
    a = components[mode]['10']
    rows.append([mode, str(a['NDCG_P']['n']), f(a['HR']['observed_complete_user_mean']), f(a['NDCG_P']['observed_complete_user_mean'])])
add_table('表8 M成功画像上的评分与画像前缀组件（16个V场景）', rows, [2440, 1200, 2716, 2716])
para('表8仅限88个具备完整组件的成功M画像，不是排除失败后的主结果。V场景没有Q库存质量偏好，no_quality与mean_quality在这些场景与full相同；'
     'uniform_weights改变了29/1,408条任务的前10序列，但本轮汇总命中与折扣值相同。'
     f"核验前后有{feedback['selection_or_weight_changed']}/{feedback['successful_M_profiles']}个画像的选项或权重变化，前10集合在67/1,408条V任务变化。"
     f"核验后的NDCG@10由{fb['no_feedback_NDCG_P']['estimate']:.6f}变为{fb['full_NDCG_P']['estimate']:.6f}，"
     f"差值{fb['delta_NDCG_P']['estimate']:.6f}，探索性95%成对区间{ci(fb['delta_NDCG_P']['interval'])}；"
     f"HR@10差值{fb['delta_HR']['estimate']:.6f}，区间{ci(fb['delta_HR']['interval'])}。"
     '区间下界为0，且未经多重比较调整，仅支持小幅、条件性的观察，不能据此确认反馈收益。')
para('SIM独立参考核对中，47,520个推荐项次（跨任务累计）的违规数为0，248条失败任务没有输出；没有将失败空输出写成合格推荐。'
     '5,000条任务中546条约束参考不适用，仍保留其真实偏好指标。该结果支持本轮SIM规则核对，不能替代真实安全检验或用户满意度证据。')

(HERE / 'manuscript-content.json').write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'replacement_paragraphs': len(p), 'inserted_tables': sum('rows' in b for b in blocks)}, ensure_ascii=False))
