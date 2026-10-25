"""Assemble the confirmed meeting package from existing project data and code."""
import csv,json,hashlib,shutil,ast
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(r'D:\Work\Codex\Project\Thesis'); BUILD=ROOT/'.scratch/meeting-evidence-20261024'
OUT=ROOT/'reports/组会完整材料_商品评论与生命周期_20261024'
PREV=ROOT/'reports/组会汇报与100用户数据_20261024/100用户CSV数据集'
DATA=OUT/'01_商品评论与生命周期数据'; CODE=OUT/'02_代码与离线运行'; INPUT=CODE/'replay_inputs'; RESULTS=OUT/'04_运行截图与结果'
for p in [DATA,CODE,INPUT,RESULTS,CODE/'src_snapshot',INPUT/'profiles',INPUT/'scenes']:p.mkdir(parents=True,exist_ok=True)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def readcsv(path):
 with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def writecsv(path,rows):
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\r\n');w.writeheader();w.writerows(rows)
def utc(ms):return datetime.fromtimestamp(ms/1000,timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ') if ms is not None else ''
base=ROOT/'data/sim/grain-A-1.1.15/sim-normal-1.0.0'
events={};materials={}
for line in (base/'events.jsonl').read_text().splitlines():
 r=json.loads(line);events.setdefault(r['parent_asin'],{})[r['stage']]=r
for line in (base/'materials.jsonl').read_text().splitlines():
 r=json.loads(line);materials.setdefault(r['parent_asin'],{})[r['kind']]=r
history=readcsv(PREV/'02_历史评论.csv'); products={r['商品标识']:r for r in readcsv(PREV/'03_商品目录.csv')}; users=readcsv(PREV/'01_用户总表_100行.csv')
full=[]
for h in history:
 p=h['商品标识']; e=events[p]; m=materials[p]; assert len(e)==6 and len(m)==8
 f={k:v['facts'] for k,v in m.items()}; c=products[p]
 row={'用户编号':h['用户编号'],'商品标识':p,'商品名称':h['商品标题'],'商品类型':h['作物类型'],'店铺名称':c['店铺名称'],'品牌':c['品牌_元数据原文'],'评分':h['评分'],'评论时间UTC':h['评论时间UTC'],'商品评论_完整文本':h['评论文本'],'SIM批次编号':c['模拟批次标识'],
 'SIM采收开始UTC':utc(e['harvest']['event_start_ms']),'SIM采收完成UTC':utc(f['harvest_record']['harvested_at_ms']),'SIM采收地区':f['harvest_record']['origin_area_id'],'SIM采收主体':e['harvest']['actor_id'],
 'SIM包装时间UTC':utc(f['packaging_binding']['packaged_at_ms']),'SIM包装状态':f['packaging_binding']['package_condition'],'SIM包装数量':f['packaging_binding']['quantity_units'],'SIM包装单位':f['packaging_binding']['unit'],
 'SIM仓储开始UTC':utc(f['storage_log']['coverage_start_ms']),'SIM仓储结束UTC':utc(f['storage_log']['coverage_end_ms']),'SIM仓储方式':';'.join(s['mode'] for s in f['storage_log']['segments']),
 'SIM抽样时间UTC':utc(f['inspection_sample']['sampled_at_ms']),'SIM检验样本编号':f['inspection_sample']['sample_id'],'SIM检验开始UTC':utc(f['inspection_report']['test_started_at_ms']),'SIM检验完成UTC':utc(f['inspection_report']['test_completed_at_ms']),'SIM检验项目':';'.join(f['inspection_report']['test_scope']),'SIM检验结论':f['inspection_report']['conclusion'],
 'SIM运输发运UTC':utc(f['transport_dispatch']['departed_at_ms']),'SIM运输到货UTC':utc(f['transport_receipt']['arrived_at_ms']),'SIM运输起点':f['transport_dispatch']['from_location_id'],'SIM运输终点':f['transport_dispatch']['to_location_id'],'SIM运输交接状态':f['transport_receipt']['handover_status'],
 'SIM零售地点':f['retail_status']['location_id'],'SIM在售状态':f['retail_status']['status'],'SIM库存数量':f['retail_status']['stock_units'],'SIM零售观测UTC':utc(f['retail_status']['observed_at_ms']),'SIM在售有效开始UTC':utc(m['retail_status']['valid_from_ms']),'SIM在售有效截止UTC':utc(m['retail_status']['valid_to_ms']),
 'SIM生命周期阶段数':len(e),'真实记录来源':'Amazon Reviews 2023','生命周期来源':'SIM 同商品模拟供应链','商品批次关联说明':'父商品相同的实验关联 不表示历史真实购买此批次'}
 assert row['商品评论_完整文本']==h['评论文本'] and row['商品名称']==products[p]['商品标题']
 full.append(row)
assert len(full)==123 and len({r['用户编号'] for r in full})==100
latest={}
for row in full:
 if row['用户编号'] not in latest or row['评论时间UTC']>latest[row['用户编号']]['评论时间UTC']:latest[row['用户编号']]=row
shown=[latest[u['用户编号']] for u in users];assert len(shown)==100
writecsv(DATA/'01_商品评论与生命周期_100行展示.csv',shown)
writecsv(DATA/'02_商品评论与生命周期_完整123条.csv',full)
dictionary=[]
for key in full[0]:
 origin='真实商品或历史评论' if not key.startswith('SIM') and key not in ['生命周期来源','商品批次关联说明'] else '同商品SIM基准'
 dictionary.append({'列名':key,'数据来源':origin,'说明':('从源毫秒时间戳转换为UTC' if 'UTC' in key else '保留原完整历史评论，不截断' if key=='商品评论_完整文本' else '每条真实历史评论对应的同商品模拟阶段属性' if key.startswith('SIM') else key)})
writecsv(DATA/'03_属性字段说明.csv',dictionary)
(DATA/'先看主表.txt').write_text('这次的主表是具体商品与评论记录，不是账户汇总。\n\n01号表每用户选最近一条可见历史评论，共100行；02号表保留原100名用户的全部123条冻结历史评论。两表均有商品名称、完整评论、评分和六阶段生命周期属性。\n\nSIM前缀表示现有模拟供应链属性，未补造真实产地、质检、物流或购买批次。完整评论不截断。生命周期时间与历史评论时间分别保留；它们是同商品的实验关联。\n\n留出目标评论仍在补充关系表的仅评价目录，不混入此处历史评论。正常SIM基准相同会出现重复值，这不是实物批次实测差异。\n\n两表均为UTF-8 BOM标准CSV，可用Excel或WPS打开。表较宽，可横向查看采收、包装、仓储、检验、运输、零售各列。',encoding='utf-8-sig')
shutil.copytree(PREV,OUT/'05_补充关系表',dirs_exist_ok=True)
# Exact original source snapshots, without credential directories or runtime environments.
source_manifest=[]
for src in sorted(ROOT.glob('*.py')):
 raw=src.read_bytes();target=CODE/'src_snapshot'/src.name;target.write_bytes(raw)
 source_manifest.append({'source':src.name,'sha256':sha(raw),'bytes':len(raw)})
for name in ['environment.yml','environment-win-64.lock.txt']:
 shutil.copyfile(ROOT/name,CODE/name)
(CODE/'SOURCE_MANIFEST.json').write_text(json.dumps({'git_commit':'e37110d','note':'生产源码原样快照，离线重放只调用personalized_recommendation.py纯算法。','files':source_manifest},ensure_ascii=False,indent=2),encoding='utf-8')
# Minimal lossless ranking inputs consumed by the original deterministic host; model profiles are original files.
legacy=ROOT/'data/recommendation-runtime-audit/personalized-compact-0.1.0'; plan=ROOT/'data/recommendation-runtime-audit/ticket12-100x18/plan'
scenes=[json.loads(x) for x in (plan/'scenes.jsonl').read_text().splitlines()]
manifest={'kind':'actual-saved-profile-host-replay','no_new_model_calls':True,'source_configuration_id':'9d0c8eb73b8ad0788eed05d0654353aa5154db348c7f974b78cfd24190a81fdf','profiles':[],'scenes':[]}
for p in sorted((legacy/'profiles').glob('*.json')):
 raw=p.read_bytes();shutil.copyfile(p,INPUT/'profiles'/p.name);manifest['profiles'].append({'file':p.name,'sha256':sha(raw)})
for s in scenes:
 path=legacy/'scenes'/(s['snapshot']['sha256']+'.json'); raw=path.read_bytes(); obs=json.loads(raw)
 saved={'label':s['label'],'arm':s['arm'],'source_snapshot':s['snapshot'],'original_cache_sha256':sha(raw),'candidates':{p:{'eligible':r['eligible'],'state':r['state'],'sim_batch_id':r['sim_batch_id'],'stock':{k:r.get('stock',{}).get(k) for k in ['supported','value','quality']}} for p,r in obs['candidates'].items()}}
 target=INPUT/'scenes'/(s['label']+'.json');target.write_text(json.dumps(saved,ensure_ascii=False,separators=(',',':')),encoding='utf-8');manifest['scenes'].append({'label':s['label'],'arm':s['arm'],'file':s['label']+'.json','sha256':sha(target.read_bytes()),'original_cache_sha256':sha(raw)})
expected=[]
for task in sorted((legacy/'tasks').glob('*.json')):
 raw=task.read_bytes();r=json.loads(raw)
 expected.append({k:r[k] for k in ['task_key','root_task_id','method','scene','status','topK']}|{'source_file_sha256':sha(raw)})
assert len(expected)==5000 and len(manifest['profiles'])==300
(INPUT/'expected_results.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in expected),encoding='utf-8')
(INPUT/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copyfile(ROOT/'.scratch/compact-execution-9d0c8eb7/results.md',RESULTS/'旧版100用户_原始独立评价报告.md')
shutil.copyfile(ROOT/'.scratch/compact-execution-9d0c8eb7/scene-results.csv',RESULTS/'旧版100用户_原始逐场景评价.csv')
current=ROOT/'.scratch/task16-execution-v2-20261023/protocol-v2-20261024'
for name in ['results.md','new-failure-evidence.json','result-summary.json','closing-status.json']:
 shutil.copyfile(current/name,RESULTS/('MACRec_v2_'+name))
# Source notes and exact prompts extracted from current code and sent requests.
shutil.copytree(BUILD/'prompts',OUT/'03_六角色提示词',dirs_exist_ok=True)
shutil.copyfile(BUILD/'prompt-and-build-notes.md',OUT/'03_六角色提示词/提示词与搭建流程_源码核对.md')
info={'user_count':100,'full_rows':123,'display_rows':100,'attribute_columns':len(full[0]),'source_modules':len(source_manifest),'legacy_reference_records':len(expected),'original_profiles':len(manifest['profiles']),'scenes':len(scenes),'new_model_calls':0,'output':str(OUT)}
(BUILD/'package-data.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(info,ensure_ascii=False))