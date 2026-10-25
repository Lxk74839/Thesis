import json,hashlib
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
ROOT=Path(r'D:\Work\Codex\Project\Thesis'); BUILD=ROOT/'.scratch/meeting-csv-20261024'; OUT=ROOT/'reports/组会汇报与100用户数据_20261024'; DATA=OUT/'100用户CSV数据集'
check=json.loads((BUILD/'independent-check.json').read_text(encoding='utf-8'))
assert check['全部CSV回读及SHA256一致'] and len(list(DATA.rglob('*.csv')))==15
assert len(list(BUILD.glob('report-page-*.png')))==2
qa={'word_pages':2,'all_pages_visually_reviewed':True,'word_has_three_plain_sections':True,'native_word_tables':0,'hyperlinks':0,'first_person_terms':0,'data_preview_included':True,'render_backend':'Microsoft Word read-only PDF export and bundled Poppler PNG render','csv_check':check,'dataset_source':'frozen original test100 cohort','new_model_api_calls':0}
(BUILD/'delivery-check.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
archive=ROOT/'reports/组会汇报及100用户CSV_20261024.zip'
files=sorted(p for p in OUT.rglob('*') if p.is_file())
with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,Path(OUT.name)/p.relative_to(OUT))
with ZipFile(archive) as z:
 assert z.testzip() is None
 assert len([n for n in z.namelist() if n.endswith('.csv')])==15
 assert len([n for n in z.namelist() if n.endswith('.docx')])==1
 assert not any('.secrets' in n or n.endswith(('.py','.mjs','.pdf')) for n in z.namelist())
summary={'archive':str(archive),'archive_MiB':round(archive.stat().st_size/1024**2,2),'archive_bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'word':str(OUT/'周组会汇报_20261024.docx'),'user_csv':str(DATA/'01_用户总表_100行.csv'),'csv_count':15,'csv_total_MiB':round(sum(p.stat().st_size for p in DATA.rglob('*.csv'))/1024**2,2),'word_pages':2,'users':100,'history_records':123,'target_records':100}
(BUILD/'delivery.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))