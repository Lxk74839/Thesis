"""Export the existing fixed test100 cohort to plain CSV; no model calls or source edits."""
import csv, json, hashlib, collections, sys
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(r'D:\Work\Codex\Project\Thesis')
sys.path.insert(0,str(ROOT))
from preference_text import project_text
BUILD=ROOT/'.scratch/meeting-csv-20261024'
OUT=ROOT/'reports/组会汇报与100用户数据_20261024'
DATA=OUT/'100用户CSV数据集'
DATA.mkdir(parents=True,exist_ok=True)
PLAN=ROOT/'data/recommendation-runtime-audit/ticket12-100x18/plan'
SIM=ROOT/'data/sim/grain-A-1.1.15/sim-normal-1.0.0'
provenance=[]; inventory=[]; descriptions={}; checks={}
def sha(raw): return hashlib.sha256(raw).hexdigest()
def getfile(path, expected=None, *, mode='完整文件SHA256'):
    path=Path(path); raw=path.read_bytes(); digest=sha(raw)
    if expected is not None: assert digest==expected, str(path)
    key=(str(path),digest,mode)
    if key not in seen_files:
        seen_files.add(key); provenance.append({'来源文件':str(path.relative_to(ROOT)).replace('\\','/'),'校验方式':mode,'SHA256':digest,'字节数':len(raw)})
    return raw
seen_files=set()
def jl(path, expected=None): return [json.loads(s) for s in getfile(path,expected).decode('utf-8-sig').splitlines() if s.strip()]
def refrow(ref):
    with (ROOT/ref['path']).open('rb') as f: f.seek(ref['offset']); raw=f.read(ref['bytes'])
    assert sha(raw)==ref['sha256']
    provenance.append({'来源文件':ref['path'],'校验方式':f"冻结行片段 第{ref['line']}行 偏移{ref['offset']}",'SHA256':sha(raw),'字节数':len(raw)})
    return json.loads(raw)
def utc(ms): return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def flatten(value,prefix=''):
    if isinstance(value,dict):
        result={}
        if not value and prefix: result[prefix]=''
        for k,v in value.items(): result.update(flatten(v,f'{prefix}.{k}' if prefix else k))
        return result
    if isinstance(value,list):
        if not value:return {prefix:''}
        result={}
        for i,v in enumerate(value): result.update(flatten(v,f'{prefix}[{i}]'))
        return result
    return {prefix:value}
def csvout(name,rows,note,fields=None):
    rows=list(rows); fields=fields or list(dict.fromkeys(k for row in rows for k in row))
    path=DATA/name; path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='raise',lineterminator='\r\n'); writer.writeheader(); writer.writerows(rows)
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f); back=list(reader)
    assert len(back)==len(rows) and reader.fieldnames==fields
    assert all(None not in r for r in back)
    inventory.append({'文件':name,'记录数':len(rows),'列数':len(fields),'说明':note,'SHA256':sha(path.read_bytes()),'字节数':path.stat().st_size})
    descriptions[name]={'fields':fields,'note':note}
    return rows
plan=json.loads(getfile(PLAN/'plan.json'))
parts={name:jl(PLAN/name,meta['sha256']) for name,meta in plan['components'].items()}
selected=sorted(parts['sample-users.jsonl'],key=lambda r:r['selection_rank'])
ids=[r['root_task_id'] for r in selected]; assert len(ids)==len(set(ids))==100
aliases={root:f'U{i:03}' for i,root in enumerate(ids,1)}
refs={r['root_task_id']:r for r in parts['root-references.jsonl']}
roots={r:refrow(refs[r]['root_ref']) for r in ids}
candidates={r:refrow(refs[r]['candidate_ref']) for r in ids}
private=jl(ROOT/plan['sources']['cohort']['path'],plan['sources']['cohort']['sha256'])
evalrows={r['task_id']:r for r in private if r['task_id'] in aliases}
assert len(evalrows)==100 and len({r['source_user_id'] for r in evalrows.values()})==100
assert {r['split'] for r in evalrows.values()}=={'test'}
safe_catalog={r['parent_asin']:r for r in jl(ROOT/plan['sources']['catalog']['path'],plan['sources']['catalog']['sha256'])}
rich={r['parent_asin']:r for r in jl(ROOT/'data/catalog/grain-A-1.1.15/catalog.jsonl')}
assert set(safe_catalog)<=set(rich)
batchmap={r['parent_asin']:r['sim_batch_id'] for r in jl(ROOT/plan['sources']['candidate_map']['path'],plan['sources']['candidate_map']['sha256'])}
base_snapshot=json.loads(getfile(SIM/'snapshot.json'))
base={}
for component,meta in base_snapshot['components'].items():
    raw=getfile(SIM/component,meta['sha256'])
    base[component]=[json.loads(s) for s in raw.decode().splitlines()] if component.endswith('.jsonl') else json.loads(raw)
assert len(safe_catalog)==1494 and len(batchmap)==1494
user_table=[]; history_table=[]; cand_table=[]; target_table=[]
for root_id in ids:
    alias=aliases[root_id]; r=roots[root_id]; c=candidates[root_id]; e=evalrows[root_id]; history=r['history']
    assert history and r['candidate_count']==len(c['C'])==len(c['b'])==len(c['batches'])
    assert len(c['C'])==len(set(c['C'])) and not(set(c['C'])&set(r['seen_parent_asins']))
    assert e['target_parent_asin'] in c['C'] and e['target_timestamp_ms']==r['history_cutoff_exclusive_ms']
    assert all(h['timestamp_ms']<r['history_cutoff_exclusive_ms'] for h in history)
    user_table.append({'用户编号':alias,'根任务标识':root_id,'来源用户标识':e['source_user_id'],'数据分组':e['split'],'历史评论数':len(history),'历史不同商品数':len(set(h['parent_asin'] for h in history)),'候选商品数':len(c['C']),'场景数':18,'最早历史时间UTC':utc(min(h['timestamp_ms'] for h in history)),'最近历史时间UTC':utc(max(h['timestamp_ms'] for h in history)),'历史截止时间UTC_不含此时刻':utc(r['history_cutoff_exclusive_ms']),'数据来源':'Amazon Reviews 2023 真实来源账户'})
    for i,h in enumerate(history,1):
        p=h['parent_asin']; cat=safe_catalog[p]
        history_table.append({'用户编号':alias,'根任务标识':root_id,'历史序号':i,'商品标识':p,'作物类型':cat['crop'],'商品标题':cat['title'],'评分':h['rating'],'评论时间UTC':utc(h['timestamp_ms']),'评论时间毫秒':h['timestamp_ms'],'评论文本':h['text'],'数据来源':'REAL_REVIEW','文本口径':'冻结模型可见的历史评论文本'})
    stats={v['parent_asin']:v for v in c['background_statistics']}
    for order,(p,b,batch) in enumerate(zip(c['C'],c['b'],c['batches']),1):
        assert p in safe_catalog and batch==batchmap[p]
        cand_table.append({'用户编号':alias,'根任务标识':root_id,'候选序号_非推荐名次':order,'商品标识':p,'模拟批次标识':batch,'基础偏好分':b,'截止前背景交互数':stats[p]['interaction_count'],'截止前背景账户数':stats[p]['account_count'],'截止前背景正向账户数':stats[p]['positive_account_count'],'关联类型':'同商品实验映射 不表示真实批次购买'})
    tr=e['target_review']
    target_table.append({'用户编号':alias,'根任务标识':root_id,'留出商品标识':e['target_parent_asin'],'留出子商品标识':tr.get('asin'),'留出评分':e['target_rating'],'留出时间UTC':utc(e['target_timestamp_ms']),'留出时间毫秒':e['target_timestamp_ms'],'留出评论标题':tr.get('title'),'留出评论文本':tr.get('text'),'验证购买标记':tr.get('verified_purchase'),'用途':'仅独立评价 不得输入推荐模型','其他候选标签':'未观测 未标注 不等于负反馈'})
csvout('01_用户总表_100行.csv',user_table,'每行一个冻结来源账户，共100行；不含留出目标商品。')
csvout('02_历史评论.csv',history_table,'每行一条冻结历史评论；同一用户可以有多行。')
product_table=[]
for p in sorted(safe_catalog):
    raw=rich[p]; meta=raw['metadata']; details=meta.get('details') or {}; cat=safe_catalog[p]
    assert project_text(meta['title'],'product_title')[0]==cat['title']
    product_table.append({'商品标识':p,'作物类型':cat['crop'],'商品标题':cat['title'],'店铺名称':meta.get('store'),'品牌_元数据原文':details.get('Brand'),'包装信息_元数据原文':details.get('Package Information'),'商品重量_元数据原文':details.get('Item Weight'),'模拟批次标识':batchmap[p],'元数据原文件行号':raw.get('source_line'),'元数据时间口径':'collection_snapshot','数据来源':'REAL_PRODUCT_METADATA'})
csvout('03_商品目录.csv',product_table,'每行一个真实父商品；SIM映射列是实验关联。未导出价格和全局聚合评分作为偏好输入。')
csvout('04_用户候选商品关联.csv',cand_table,'每行一个用户与候选商品的关联，含冻结基础分。候选序号不是模型排序。')
for filename,component,note in [('05_模拟批次.csv','batches.jsonl','每行一个同商品SIM基准批次。'),('06_生命周期事件.csv','events.jsonl','每行一个SIM事件，分harvest、packaging、storage、inspection、transport、retail六阶段。'),('07_证据材料.csv','materials.jsonl','每行一份SIM证据；facts等对象展开为独立属性列，数组按索引展开。'),('08_模拟登记记录.csv','registrations.jsonl','每行一条本地SIM登记，registry_backend为local_sim_registry；不是Fabric实际交易。')]:
    csvout(filename,[flatten(r) for r in base[component]],note)
policy=flatten(base['policy.json'])
csvout('09_访问与核验规则.csv',[{'属性路径':k,'属性值':v,'数据来源':'SIM_POLICY'} for k,v in policy.items()],'每行一个基准核验与访问规则属性。')
scenes=parts['scenes.jsonl']; byview={s['view_id']:s['label'] for s in scenes}; scenario_table=[]; changes=[]
KEYS={'batches.jsonl':'sim_batch_id','events.jsonl':'event_id','materials.jsonl':'evidence_id','registrations.jsonl':'registration_id'}
def indexed(rows,component):
    key=KEYS.get(component)
    values={((str(r.get(key)) if key else str(r.get('action_id',r.get('change_id',sha(json.dumps(r,sort_keys=True,separators=(',',':')).encode()))))),r.get('version',1)):r for r in rows}
    assert len(values)==len(rows),component
    return values
base_index={k:indexed(v,k) for k,v in base.items() if k.endswith('.jsonl')}
MISSING=object()
def typename(v): return 'missing' if v is MISSING else 'null' if v is None else 'boolean' if isinstance(v,bool) else 'integer' if isinstance(v,int) else 'number' if isinstance(v,float) else 'string'
for scene in scenes:
    ref=scene['snapshot']; snap_path=ROOT/ref['path']; snap=json.loads(getfile(snap_path,ref['sha256']))
    start=len(changes)
    for component,meta in snap['components'].items():
        raw=getfile(snap_path.parent/component,meta['sha256'])
        if component in base_snapshot['components'] and meta['sha256']==base_snapshot['components'][component]['sha256']:continue
        if component=='policy.json': old_index={('policy',1):base[component]}; new_index={('policy',1):json.loads(raw)}
        elif component.endswith('.jsonl'):
            new_index=indexed([json.loads(x) for x in raw.decode().splitlines() if x],component); old_index=base_index.get(component,{})
        else:continue
        for key in sorted(old_index.keys()|new_index.keys()):
            old,new=old_index.get(key),new_index.get(key)
            if old==new:continue
            before=flatten(old) if old is not None else {}; after=flatten(new) if new is not None else {}
            operation='新增记录' if old is None else '删除记录' if new is None else '修改字段'
            parent=(new or old).get('parent_asin','')
            for field in sorted(before.keys()|after.keys()):
                a,b=before.get(field,MISSING),after.get(field,MISSING)
                if a is not MISSING and b is not MISSING and type(a)==type(b) and a==b:continue
                changes.append({'场景编号':scene['label'],'数据表':component,'记录标识':key[0],'记录版本':key[1],'商品标识':parent,'变化类型':operation,'属性路径':field,'原值类型':typename(a),'原值':'' if a is MISSING else a,'新值类型':typename(b),'新值':'' if b is MISSING else b,'数据来源':'SIM_SCENARIO'})
    scenario_table.append({'场景编号':scene['label'],'场景分支':scene['arm'],'场景视图标识':scene['view_id'],'快照标识':scene['snapshot_id'],'基准场景':'V00','核验时间UTC':utc(snap['verify_at_ms']),'核验时间毫秒':snap['verify_at_ms'],'截止登记序号':snap['cutoff_sequence'],'政策标识':snap['policy_id'],'协议版本':snap['protocol_version'],'相对正常基准变化属性数':len(changes)-start,'数据来源':'SIM'})
    print(f"SCENE {scene['label']}: {len(changes)-start} changed attributes",flush=True)
csvout('10_实验场景.csv',scenario_table,'每行一个冻结场景，共18行；正常基准V00，变化通过12号表表达。')
user_scenes=[{'用户编号':aliases[r['root_task_id']],'根任务标识':r['root_task_id'],'场景编号':byview[r['view_id']],'场景视图标识':r['view_id'],'绑定标识':r['binding_id']} for r in parts['user-scenarios.jsonl']]
assert len(user_scenes)==1800 and len({(r['用户编号'],r['场景编号']) for r in user_scenes})==1800
csvout('11_用户场景关联.csv',user_scenes,'每行一个用户与场景绑定，共100×18=1800行；不增加独立用户数。')
csvout('场景管理_不得输入模型/12_场景变化属性.csv',changes,'每行一个相对正常基准的字段变化。结合05—09号基准表恢复场景，避免复制18份相同记录。missing表示属性不存在，null表示原记录明确为空。')
csvout('仅评价_不得输入模型/留出评价评论_100行.csv',target_table,'每行一个来源用户的留出评价记录。仅评价侧使用，与历史评论隔离。')
common={'parent_asin':'真实父商品标识，是评论与同商品SIM关联键','sim_batch_id':'模拟批次标识，不是历史真实购买批次','event_id':'模拟生命周期事件标识','evidence_id':'模拟证据材料标识','registration_id':'本地模拟登记标识','source':'来源标记，SIM表示模拟记录','version':'来源记录版本','stage':'生命周期阶段英文代码','actor_id':'模拟阶段执行主体','issuer_id':'模拟记录出具者','registry_backend':'登记实现，local_sim_registry表示本地模拟登记','temporal_mode':'材料时间语义','kind':'证据材料种类','schema_version':'来源数据结构版本','content_sha256':'登记对象内容的SHA256摘要','sequence':'本地模拟登记顺序','receipt_status':'本地模拟登记状态','target_kind':'登记对象类型','target_id':'登记对象标识','根任务标识':'冻结推荐任务标识，同一用户各表保持一致','用户编号':'展示编号U001至U100，顺序来自冻结selection_rank','数据来源':'保留真实来源与SIM构造的区分'}
dictionary=[]
for name,meta in descriptions.items():
 for field in meta['fields']:
    meaning=common.get(field,field)
    if field.endswith('_ms') or field.endswith('毫秒'): meaning+='；单位为Unix毫秒'
    if 'UTC' in field: meaning+='；按UTC表示，末尾Z为UTC'
    if field.startswith('facts.'): meaning='来源证据facts中对应属性：'+field[6:]
    if '[' in field: meaning+='；方括号为来源数组位置，不是JSON字符串'
    dictionary.append({'文件':name,'列名':field,'含义或来源':meaning,'每行表示':meta['note']})
csvout('13_字段说明.csv',dictionary,'每行解释一个CSV列及该表记录粒度。')
csvout('14_来源与校验.csv',provenance,'每行一项已校验的源文件或冻结行片段。没有读写API凭据。')
checks={'用户总数':len(user_table),'来源账户唯一数':len({r['来源用户标识'] for r in user_table}),'历史评论记录':len(history_table),'历史不同父商品':len({r['商品标识'] for r in history_table}),'真实父商品总数':len(product_table),'用户候选关联数':len(cand_table),'模拟批次数':len(base['batches.jsonl']),'生命周期事件数':len(base['events.jsonl']),'证据材料数':len(base['materials.jsonl']),'模拟登记数':len(base['registrations.jsonl']),'场景数':len(scenes),'用户场景绑定数':len(user_scenes),'场景变化属性记录数':len(changes),'留出评价记录数':len(target_table),'CSV文件数':len(inventory),'缺失商品关联':0,'目标商品不在候选':0,'历史晚于截止':0,'开发集用户混入':0,'模型API新增调用':0}
assert checks['CSV文件数']==15
assert {r['parent_asin'] for r in base['batches.jsonl']}==set(safe_catalog)
for component in ['events.jsonl','materials.jsonl','registrations.jsonl']:
 assert all(r['parent_asin'] in batchmap and r['sim_batch_id']==batchmap[r['parent_asin']] and r['source']=='SIM' for r in base[component])
events={r['event_id'] for r in base['events.jsonl']}
assert all(r['event_id'] in events for r in base['materials.jsonl'])
report={'date':'2026-10-24','source_plan_id':plan['plan_id'],'sampling_rule':plan['sampling_rule'],'seed':plan['seed'],'checks':checks,'inventory':inventory,'source_files_checked':len(provenance),'history_count_distribution':dict(collections.Counter(r['历史评论数'] for r in user_table)),'crop_distribution':dict(collections.Counter(r['作物类型'] for r in product_table)),'exports_are_new_copies':True,'original_files_modified':False}
(BUILD/'data-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
notes=['100用户CSV数据集使用说明','日期：2026年10月24日','',f"固定计划：{plan['plan_id']}",f"抽样规则：{plan['sampling_rule']}，种子：{plan['seed']}。沿用原100名测试来源账户，没有重新抽样。",'', '先打开01_用户总表_100行.csv，可直接看到100行用户记录。再打开02_历史评论.csv查看每条历史评论，03_商品目录.csv查看商品属性。04号表通过用户编号、商品标识、模拟批次标识连接用户与候选。','', '全部CSV采用UTF-8 BOM、逗号分隔，首行是列名。评论中的逗号、引号和换行按标准CSV转义。统计记录数应使用CSV阅读器，不能按文本物理行计数。Excel或WPS可直接打开；长标识请按文本查看。', '', '用户总表为100行；同一用户可有多条评论和许多候选，其他明细行数因此大于100。18个场景对应1800条用户场景绑定，独立来源账户仍为100。', '', '05—08号表是正常SIM基准。06号表的harvest、packaging、storage、inspection、transport、retail分别表示采收、包装、仓储、检验、运输、零售。07号表facts.*为已存在的模拟证据属性，非新编造的真实生产材料。08号表是local_sim_registry记录，未将其写成真实Fabric链上交易。', '', '10号表列出全部18个冻结场景。12号表按记录标识、版本和属性路径列出相对基准的增删改，结合05—09号表表达场景材料变化，减少重复存储。字段数组使用[n]展开为列或属性路径，没有把整段嵌套JSON放进单元格。', '', '真实历史评论只关联父商品。商品到SIM批次是实验映射，不表示该账户真实购买或评价过模拟批次。真实评论时间与SIM场景核验时间是不同时间轴，分别保留。', '', '仅评价_不得输入模型目录保存100条留出目标及其原始评论，只用于独立评价，不得合并回历史评论或输入推荐模型。没有把未观测候选标注为真实负反馈。', '', '此包为冻结数据的可读CSV导出，适合组会展示和外部分析。项目现有运行器仍读取原冻结任务包；导出不修改样本、协议、数据或历史实验结果。场景变化表包含实验构造信息，仅供场景管理，不得直接作为推荐模型输入。不能将整个CSV包一次性输入模型。100名账户的评论口径是冻结任务中123条较早历史评论及100条留出评论，并非这些账户的全部Amazon活动。', '', '缺失属性留空，未把未知值填成0。UTC时间由源毫秒时间戳确定性转换。13号表说明列含义，14号表列出输入来源与SHA256校验。', '', '实际导出规模：']
notes += [f'{k}：{v}' for k,v in checks.items()]
notes += ['', '文件清单：']+[f"{r['文件']}：{r['记录数']}条记录，{r['列数']}列" for r in inventory]
(DATA/'请先阅读.txt').write_text('\n'.join(notes),encoding='utf-8-sig')
print(json.dumps(checks,ensure_ascii=False),flush=True)