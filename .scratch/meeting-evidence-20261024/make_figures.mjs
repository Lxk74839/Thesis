import fs from 'node:fs/promises';
import sharp from 'sharp';
import {Workbook} from '@oai/artifact-tool';
const root='D:/Work/Codex/Project/Thesis';
const pack=root+'/reports/组会完整材料_商品评论与生命周期_20261024';
const out=pack+'/04_运行截图与结果';
const csv=await fs.readFile(pack+'/01_商品评论与生命周期数据/01_商品评论与生命周期_100行展示.csv','utf8');
const wb=await Workbook.fromCSV(csv,{sheetName:'主表'});
const all=wb.worksheets.getItem('主表').getRange('A1:AP3').values;
const header=all[0]; const first=Object.fromEntries(header.map((h,i)=>[h,all[1][i]]));
await fs.writeFile(root+'/.scratch/meeting-evidence-20261024/example-record.json',JSON.stringify(first,null,2));
async function grid(name,matrix,widths,height,filename){
 const s=wb.worksheets.add(name);const cols=matrix[0].length;const last=String.fromCharCode(64+cols);const address='A1:'+last+matrix.length;
 s.getRange(address).values=matrix;s.showGridLines=true;
 s.getRange(address).format.font={name:'Microsoft YaHei',size:15,color:'#17202A'};
 s.getRange(address).format.wrapText=true;s.getRange(address).format.verticalAlignment='center';
 s.getRange('A1:'+last+'1').format.fill='#294A64';s.getRange('A1:'+last+'1').format.font={name:'Microsoft YaHei',size:15,bold:true,color:'#FFFFFF'};
 s.getRange('A1:'+last+'1').format.rowHeightPx=40;
 s.getRange('A2:'+last+matrix.length).format.rowHeightPx=height;
 for(let i=0;i<cols;i++){const c=String.fromCharCode(65+i);s.getRange(c+'1:'+c+matrix.length).format.columnWidthPx=widths[i];}
 s.getRange(address).format.borders={preset:'all',style:'thin',color:'#D5DFE6'};
 wb.recalculate();const png=await wb.render({sheetName:name,range:address,scale:1.6,format:'png'});
 await fs.writeFile(out+'/'+filename,new Uint8Array(await png.arrayBuffer()));
}
await grid('商品评论预览',[['用户编号','商品名称','评分','完整商品评论'],...all.slice(1).map(r=>[r[0],r[2],r[6],r[8]])],[90,380,60,630],150,'01_商品名称与完整评论_CSV视图.png');
const life=[['环节','主表中的具体属性','同一商品实际导出值'],
 ['采收','采收地区、完成时间',first['SIM采收地区']+'\n'+first['SIM采收完成UTC']],
 ['包装','包装状态、数量、时间',first['SIM包装状态']+'；'+first['SIM包装数量']+' '+first['SIM包装单位']+'\n'+first['SIM包装时间UTC']],
 ['仓储','仓储方式、起止时间',first['SIM仓储方式']+'\n'+first['SIM仓储开始UTC']+' 至 '+first['SIM仓储结束UTC']],
 ['检验','检验项目、结论、完成时间',first['SIM检验项目']+'；'+first['SIM检验结论']+'\n'+first['SIM检验完成UTC']],
 ['运输','起讫地、发运和到货时间',first['SIM运输起点']+' 至 '+first['SIM运输终点']+'\n'+first['SIM运输发运UTC']+' 至 '+first['SIM运输到货UTC']],
 ['零售','在售状态、库存、有效截止',first['SIM在售状态']+'；库存 '+first['SIM库存数量']+'\n'+first['SIM在售有效截止UTC']]];
await grid('六阶段属性预览',life,[110,270,650],80,'02_同商品六阶段属性_CSV视图.png');
const escape=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
async function textImage(title,lines,filename,footer){
 const width=1440;const step=42;const height=145+lines.length*step+75;
 let svg='<svg xmlns="http://www.w3.org/2000/svg" width="'+width+'" height="'+height+'"><rect width="100%" height="100%" fill="white"/><text x="40" y="50" font-family="Microsoft YaHei" font-size="31" font-weight="bold" fill="#17202A">'+escape(title)+'</text><text x="40" y="90" font-family="Microsoft YaHei" font-size="22" fill="#555">真实日志内容排版 非终端截图</text>';
 lines.forEach((l,i)=>{svg+='<text x="40" y="'+(145+i*step)+'" font-family="Microsoft YaHei,Consolas" font-size="26" fill="#111">'+escape(l)+'</text>';});
 svg+='<text x="40" y="'+(height-28)+'" font-family="Microsoft YaHei" font-size="20" fill="#666">'+escape(footer)+'</text></svg>';
 await sharp(Buffer.from(svg)).png().toFile(out+'/'+filename);
}
const log=(await fs.readFile(out+'/本地重放/本地重放_实际输出.txt','utf8')).replace(/^\uFEFF/,'').trim().split(/\r?\n/);
await textImage('5000条任务本地重放 实际运行输出',log,'03_完整真实运行日志_非终端截图.png','原始文本：本地重放/本地重放_实际输出.txt');
const excerpt=log.filter(l=>/^时间 |^固定用户 |^范围 |^[RSM] HR|^完成 |^实际推荐|^新增模型|^旧版结果/.test(l));
await textImage('运行结果核对 日志节选',excerpt,'04_真实运行结果节选_非终端截图.png','全部文字摘自本次实际执行日志；复用原模型画像。');
const dataLog=(await fs.readFile(out+'/主表生成_实际输出.txt','utf8')).replace(/^\uFEFF/,'').trim().split(/\r?\n/);
await textImage('商品评论与生命周期关联 实际输出',dataLog,'05_主表生成日志_非终端截图.png','原始文本：主表生成_实际输出.txt');
console.log(JSON.stringify({data_columns:header.length,actual_data_views:2,actual_log_images:3,formatting_label:'非终端截图',example_product:first['商品标识']}));