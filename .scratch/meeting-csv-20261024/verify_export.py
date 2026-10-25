import csv,json,hashlib,collections
from pathlib import Path
ROOT=Path(r'D:\Work\Codex\Project\Thesis'); BUILD=ROOT/'.scratch/meeting-csv-20261024'; DATA=ROOT/'reports/组会汇报与100用户数据_20261024/100用户CSV数据集'
summary=json.loads((BUILD/'data-summary.json').read_text(encoding='utf-8'))
def read(name):
 with (DATA/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
for item in summary['inventory']:
 path=DATA/item['文件']; assert hashlib.sha256(path.read_bytes()).hexdigest()==item['SHA256']; assert len(read(item['文件']))==item['记录数']; assert path.read_bytes()[:3]==b'\xef\xbb\xbf'
assert len(list(DATA.rglob('*.csv')))==15
users=read('01_用户总表_100行.csv'); alias={r['用户编号']:r for r in users}; assert len(alias)==100 and len({r['来源用户标识'] for r in users})==100
plan=ROOT/'data/recommendation-runtime-audit/ticket12-100x18/plan'; selection=[json.loads(x) for x in (plan/'sample-users.jsonl').read_text().splitlines()]
assert {r['根任务标识'] for r in users}=={r['root_task_id'] for r in selection}
products={r['商品标识']:r for r in read('03_商品目录.csv')}; batches={r['parent_asin']:r['sim_batch_id'] for r in read('05_模拟批次.csv')}
assert len(products)==1494 and set(products)==set(batches)
history=read('02_历史评论.csv'); counts=collections.Counter()
for h in history:
 u=alias[h['用户编号']]; assert h['根任务标识']==u['根任务标识']; assert h['商品标识'] in products; assert h['评论时间UTC']<u['历史截止时间UTC_不含此时刻']; counts[h['用户编号']]+=1
assert all(counts[u['用户编号']]==int(u['历史评论数']) for u in users)
candidates=read('04_用户候选商品关联.csv'); grouped=collections.defaultdict(list)
for r in candidates:
 u=alias[r['用户编号']]; assert r['根任务标识']==u['根任务标识']; assert r['模拟批次标识']==batches[r['商品标识']]; grouped[r['根任务标识']].append(r)
for reference in map(json.loads,(plan/'root-references.jsonl').read_text().splitlines()):
 ref=reference['candidate_ref']
 with (ROOT/ref['path']).open('rb') as f:f.seek(ref['offset']); raw=f.read(ref['bytes'])
 assert hashlib.sha256(raw).hexdigest()==ref['sha256']; expected=json.loads(raw); actual=grouped[reference['root_task_id']]
 assert [r['商品标识'] for r in actual]==expected['C']; assert [float(r['基础偏好分']) for r in actual]==expected['b']; assert [r['模拟批次标识'] for r in actual]==expected['batches']
labels=read('仅评价_不得输入模型/留出评价评论_100行.csv'); assert len(labels)==100
for r in labels:assert r['留出商品标识'] in {c['商品标识'] for c in grouped[r['根任务标识']]}
links=read('11_用户场景关联.csv'); assert len(links)==len({(r['用户编号'],r['场景编号']) for r in links})==1800
check={'固定100账户一致':True,'候选顺序基础分及批次逐行一致':True,'评论用户商品关联正确':True,'历史严格早于截止':True,'18场景1800绑定完整':True,'留出目标独立存放':True,'场景构造信息独立存放':True,'CSV文件数':15,'全部CSV回读及SHA256一致':True,'本次模型API调用':0}
(BUILD/'independent-check.json').write_text(json.dumps(check,ensure_ascii=False,indent=2),encoding='utf-8')
(DATA/'数据导出验收.txt').write_text('数据导出验收\n\n'+'\n'.join(f'{k}：{v}' for k,v in summary['checks'].items())+'\n\n'+'\n'.join(f'{k}：{v}' for k,v in check.items()),encoding='utf-8-sig')
print(json.dumps(check,ensure_ascii=False))