"""Offline host-ranking replay using actual saved profiles. No model/HTTP client is loaded."""
import argparse,csv,json,math,sys,time,hashlib,collections
from pathlib import Path
from datetime import datetime,timezone,timedelta
HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parent
sys.dont_write_bytecode=True
blocked_calls=[]
def offline_guard(event,args):
 if event.startswith('socket.') or event=='subprocess.Popen':
  blocked_calls.append(event);raise RuntimeError('Offline demo prohibits network and child processes')
 if event=='open' and args and isinstance(args[0],(str,bytes)) and '.secrets' in str(args[0]):raise RuntimeError('Credential access is prohibited')
sys.addaudithook(offline_guard)
sys.path.insert(0,str(HERE/'src_snapshot'))
from personalized_recommendation import run_task

def csvread(path):
 with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def csvwrite(path,rows):
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\r\n');w.writeheader();w.writerows(rows)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--all-scenes',action='store_true');p.add_argument('--results-dir',type=Path);args=p.parse_args()
 out=args.results_dir or PACKAGE/'04_运行截图与结果'/'本地重放';out.mkdir(parents=True,exist_ok=True)
 data=PACKAGE/'05_补充关系表';inputs=HERE/'replay_inputs'
 log=(out/'本地重放_实际输出.txt').open('w',encoding='utf-8-sig')
 def say(s):print(s,flush=True);log.write(s+'\n');log.flush()
 started=time.perf_counter();say('Thesis 本地真实缓存重放');say('时间 '+datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds'));say('本次复用已保存的真实画像；重新执行原宿主排序，不重新调用模型。')
 users=csvread(data/'01_用户总表_100行.csv');alias={r['根任务标识']:r['用户编号'] for r in users};assert len(alias)==100
 catalog=[{'parent_asin':r['商品标识'],'title':r['商品标题'],'crop':r['作物类型']} for r in csvread(data/'03_商品目录.csv')];products={p['parent_asin']:p for p in catalog}
 histories=collections.defaultdict(list)
 for r in csvread(data/'02_历史评论.csv'):histories[r['根任务标识']].append({'parent_asin':r['商品标识'],'rating':float(r['评分']),'timestamp_ms':int(r['评论时间毫秒']),'text':r['评论文本']})
 candidate_inputs=collections.defaultdict(lambda:{'C':[],'base_scores':[],'K':10})
 for r in csvread(data/'04_用户候选商品关联.csv'):
  t=candidate_inputs[r['根任务标识']];t['C'].append(r['商品标识']);t['base_scores'].append(float(r['基础偏好分']))
 labels={r['根任务标识']:r['留出商品标识'] for r in csvread(data/'仅评价_不得输入模型/留出评价评论_100行.csv')}
 manifest=json.loads((inputs/'MANIFEST.json').read_text(encoding='utf-8'))
 expected=[json.loads(x) for x in (inputs/'expected_results.jsonl').read_text(encoding='utf-8').splitlines()]
 if not args.all_scenes:expected=[r for r in expected if r['scene']=='V00']
 order={f'V{i:02}':i for i in range(16)}|{'Q1':16,'Q2':17}
 expected.sort(key=lambda r:(alias[r['root_task_id']],order[r['scene']],r['method']))
 scene_cache={};profiles={}
 for meta in manifest['scenes']:
  path=inputs/'scenes'/meta['file'];assert digest(path)==meta['sha256'];scene_cache[meta['label']]=json.loads(path.read_text(encoding='utf-8'))
 for meta in manifest['profiles']:
  path=inputs/'profiles'/meta['file'];assert digest(path)==meta['sha256'];profiles[meta['file']]=json.loads(path.read_text(encoding='utf-8'))
 say(f"固定用户 {len(users)}；商品 {len(catalog)}；历史评论 {sum(map(len,histories.values()))}")
 say(f"范围 {'18场景全部5000任务' if args.all_scenes else 'V00单场景300任务'}；原画像文件 {len(profiles)}")
 rows=[];ranked_rows=[];matched=0
 for index,reference in enumerate(expected,1):
  root=reference['root_task_id'];method=reference['method'];scene_label=reference['scene'];profile=profiles[root+'-'+method+'.json']
  status=profile['status'];ranking=[];scores={}
  if status=='ok':
   task=candidate_inputs[root]|{'prefer_stock':scene_cache[scene_label]['arm']=='quality'}
   actual=run_task(task,catalog=catalog,history=histories[root],profile=profile['profile'],scene=scene_cache[scene_label]['candidates'],mode='full',alpha=.5)
   ranking=actual['topK'];scores={r['parent_asin']:r['score'] for r in actual['candidates'] if r['parent_asin'] in ranking}
  same=status==reference['status'] and ranking==reference['topK'];matched+=int(same)
  assert same, 'Replay differs from original task '+reference['task_key']
  rank=ranking.index(labels[root])+1 if labels[root] in ranking else None
  rows.append({'用户编号':alias[root],'方法':method,'场景':scene_label,'执行状态':status,'与原结果一致':same,'HR@10':int(rank is not None),'NDCG@10':0. if rank is None else 1/math.log2(rank+1),'根任务标识':root,'原任务标识':reference['task_key']})
  ranked_rows.extend({'用户编号':alias[root],'方法':method,'场景':scene_label,'推荐名次':i,'商品标识':parent,'商品名称':products[parent]['title'],'宿主重放评分':scores[parent],'模型输出来源':'原真实画像缓存 无新增模型调用'} for i,parent in enumerate(ranking,1))
  if index%1000==0:say(f'重放进度 {index}/{len(expected)}；一致 {matched}')
 metrics=[]
 for method in ['R','S','M']:
  part=[r for r in rows if r['方法']==method and r['场景'].startswith('V')]
  byuser=collections.defaultdict(list)
  for r in part:byuser[r['用户编号']].append(r)
  hr=sum(sum(r['HR@10'] for r in items)/len(items) for items in byuser.values())/len(byuser)
  ndcg=sum(sum(r['NDCG@10'] for r in items)/len(items) for items in byuser.values())/len(byuser)
  metrics.append({'方法':method,'独立用户数':len(byuser),'V场景数':len({r['场景'] for r in part}),'成功任务数':sum(r['执行状态']=='ok' for r in part),'失败任务数':sum(r['执行状态']!='ok' for r in part),'HR@10':hr,'NDCG@10':ndcg,'口径':'先按用户平均V场景 再按用户等权平均；原终结失败计0'})
  say(f'{method} HR@10={hr:.6f} NDCG@10={ndcg:.6f}')
 if args.all_scenes:
  for m,(hr,ndcg) in zip(metrics,[(.2175,.121012),(.195625,.108129),(.205625,.102365)]):assert abs(m['HR@10']-hr)<1e-9 and abs(m['NDCG@10']-ndcg)<.00000051
 csvwrite(out/'01_任务重放核对.csv',rows);csvwrite(out/'02_实际重放推荐商品.csv',ranked_rows);csvwrite(out/'03_方法总体结果.csv',metrics)
 states=dict(collections.Counter(r['执行状态'] for r in rows));elapsed=time.perf_counter()-started
 result={'kind':'actual-saved-profile-host-replay','users':100,'tasks':len(rows),'ranked_item_occurrences':len(ranked_rows),'statuses':states,'matched_original_tasks':matched,'new_model_api_calls':0,'network_or_child_attempts':blocked_calls,'elapsed_seconds':elapsed,'metrics':metrics,'current_macrec_v2':'主对照未完成；本次不运行新B0/I1，不将旧版结果充作新版结果'}
 (out/'replay-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 say(f"完成 {len(rows)}；原结果一致 {matched}/{len(rows)}；状态 {states}")
 say(f'实际推荐项次 {len(ranked_rows)}；本地耗时 {elapsed:.2f} 秒')
 say('新增模型API调用 0；未读取API Key；无网络与子进程尝试。')
 say('旧版结果未显示M总体优于R；新版MACRec B0/I1仍未完成主对照。')
 log.close()
if __name__=='__main__':main()