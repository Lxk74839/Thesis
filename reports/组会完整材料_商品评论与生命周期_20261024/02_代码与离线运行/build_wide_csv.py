"""Build concrete review plus six-stage attributes from the packaged CSV source tables."""
import csv,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent; PACK=HERE.parent; SRC=PACK/'05_补充关系表'; OUT=PACK/'01_商品评论与生命周期数据'
def read(name):
 with (SRC/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def when(ms):return datetime.fromtimestamp(int(ms)/1000,timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ') if ms else ''
def write(name,rows):
 p=OUT/name
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\r\n');writer.writeheader();writer.writerows(rows)
 return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 history=read('02_历史评论.csv');users=read('01_用户总表_100行.csv');catalog={r['商品标识']:r for r in read('03_商品目录.csv')};events={};materials={}
 for row in read('06_生命周期事件.csv'):events.setdefault(row['parent_asin'],{})[row['stage']]=row
 for row in read('07_证据材料.csv'):materials.setdefault(row['parent_asin'],{})[row['kind']]=row
 rows=[]
 for h in history:
  p=h['商品标识'];c=catalog[p];e=events[p];m=materials[p]
  assert len(e)==6 and len(m)==8
  assert all(v['sim_batch_id']==c['模拟批次标识'] and v['source']=='SIM' for v in [*e.values(),*m.values()])
  f=lambda kind,key:m[kind].get('facts.'+key,'')
  rows.append({'用户编号':h['用户编号'],'商品标识':p,'商品名称':h['商品标题'],'商品类型':h['作物类型'],'店铺名称':c['店铺名称'],'品牌':c['品牌_元数据原文'],'评分':h['评分'],'评论时间UTC':h['评论时间UTC'],'商品评论_完整文本':h['评论文本'],'SIM批次编号':c['模拟批次标识'],
   'SIM采收开始UTC':when(e['harvest']['event_start_ms']),'SIM采收完成UTC':when(f('harvest_record','harvested_at_ms')),'SIM采收地区':f('harvest_record','origin_area_id'),'SIM采收主体':e['harvest']['actor_id'],
   'SIM包装时间UTC':when(f('packaging_binding','packaged_at_ms')),'SIM包装状态':f('packaging_binding','package_condition'),'SIM包装数量':f('packaging_binding','quantity_units'),'SIM包装单位':f('packaging_binding','unit'),
   'SIM仓储开始UTC':when(f('storage_log','coverage_start_ms')),'SIM仓储结束UTC':when(f('storage_log','coverage_end_ms')),'SIM仓储方式':f('storage_log','segments[0].mode'),
   'SIM抽样时间UTC':when(f('inspection_sample','sampled_at_ms')),'SIM检验样本编号':f('inspection_sample','sample_id'),'SIM检验开始UTC':when(f('inspection_report','test_started_at_ms')),'SIM检验完成UTC':when(f('inspection_report','test_completed_at_ms')),'SIM检验项目':f('inspection_report','test_scope[0]'),'SIM检验结论':f('inspection_report','conclusion'),
   'SIM运输发运UTC':when(f('transport_dispatch','departed_at_ms')),'SIM运输到货UTC':when(f('transport_receipt','arrived_at_ms')),'SIM运输起点':f('transport_dispatch','from_location_id'),'SIM运输终点':f('transport_dispatch','to_location_id'),'SIM运输交接状态':f('transport_receipt','handover_status'),
   'SIM零售地点':f('retail_status','location_id'),'SIM在售状态':f('retail_status','status'),'SIM库存数量':f('retail_status','stock_units'),'SIM零售观测UTC':when(f('retail_status','observed_at_ms')),'SIM在售有效开始UTC':when(m['retail_status']['valid_from_ms']),'SIM在售有效截止UTC':when(m['retail_status']['valid_to_ms']),
   'SIM生命周期阶段数':len(e),'真实记录来源':'Amazon Reviews 2023','生命周期来源':'SIM 同商品模拟供应链','商品批次关联说明':'父商品相同的实验关联 不表示历史真实购买此批次'})
 assert len(rows)==123 and len({r['用户编号'] for r in rows})==100
 latest={}
 for row in rows:
  if row['用户编号'] not in latest or row['评论时间UTC']>latest[row['用户编号']]['评论时间UTC']:latest[row['用户编号']]=row
 display=[latest[u['用户编号']] for u in users]
 hashes={name:write(name,part) for name,part in [('01_商品评论与生命周期_100行展示.csv',display),('02_商品评论与生命周期_完整123条.csv',rows)]}
 log='Thesis 商品评论与六阶段属性关联\n'+'\n'.join([f'来源账户：{len(users)}',f'完整历史评论记录：{len(rows)}',f'每用户一条展示记录：{len(display)}',f'每条记录属性列：{len(rows[0])}','商品名称与完整评论：逐条保留','采收 包装 仓储 检验 运输 零售：每条记录6阶段','商品与SIM批次关联：全部一致','新增模型API调用：0','全部输出来自冻结CSV来源，未补造真实供应链字段。'])+'\n'
 (PACK/'04_运行截图与结果'/'主表生成_实际输出.txt').write_text(log,encoding='utf-8-sig')
 print(log);print(json.dumps(hashes,ensure_ascii=False))
if __name__=='__main__':main()