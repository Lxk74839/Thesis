import csv
import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(r'D:\Work\Codex\Project\Thesis')
BUILD=ROOT/'.scratch/meeting-final-focus-20261024'
META=json.loads((BUILD/'package.json').read_text(encoding='utf-8'))
PACK=Path(META['output'])
TARGET=ROOT/'reports/组会材料_实验结果_数据集_卡通提示词模板_20261024.zip'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
doc=PACK/'周组会汇报_实验结果_数据集_智能体设计.docx'
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
with zipfile.ZipFile(doc) as word:
    assert word.testzip() is None
    tree=ET.fromstring(word.read('word/document.xml'))
    text=''.join(tree.itertext())
    assert '我们' not in text and not tree.findall('.//'+W+'tbl') and not tree.findall('.//'+W+'hyperlink')
    assert all(p.attrib[W+'val']=='Normal' for p in tree.findall('.//'+W+'pStyle'))
    for section in ('实验与结果','数据集简介','多智能体设计与提示词'):
        assert section in text
    media=[word.read(name) for name in word.namelist() if name.startswith('word/media/')]
    assert len(media)==4
    assert META['screenshot_sha256'] in {hashlib.sha256(raw).hexdigest() for raw in media}
    assert (PACK/'配图/用户画像智能体_卡通提示词模板.png').read_bytes() in media
assert sha(PACK/'实验结果/终端结果截图.png')==META['screenshot_sha256']
for name,count in [('01_商品评论与生命周期_100行展示.csv',100),('02_商品评论与生命周期_完整123条.csv',123)]:
    path=PACK/'数据集'/name
    with path.open(encoding='utf-8-sig',newline='') as stream:
        rows=list(csv.DictReader(stream))
    assert len(rows)==count and len(rows[0])==42 and len({r['用户编号'] for r in rows})==100
    source=ROOT/'reports/组会修订材料_字段详解与多智能体设计_20261024/01_CSV数据与字段说明'/name
    assert sha(path)==sha(source)
assert len(list(BUILD.glob('brief-page-*.png')))==3
files=sorted(p for p in PACK.rglob('*') if p.is_file())
assert len(list(PACK.glob('*.docx')))==1
assert not any(p.suffix.lower() in ('.py','.ps1','.js','.mjs','.exe','.bat','.sh') for p in files)
with zipfile.ZipFile(TARGET,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for path in files:
        archive.write(path,Path(PACK.name)/path.relative_to(PACK))
with zipfile.ZipFile(TARGET) as archive:
    assert archive.testzip() is None and len(archive.infolist())==len(files)
summary={'zip':str(TARGET),'size_mib':round(TARGET.stat().st_size/1024**2,3),'sha256':sha(TARGET),
         'word_pages':3,'sections':3,'images_in_word':4,'one_cartoon_agent':True,
         'terminal_screenshot_unmodified':True,'dataset_records':[100,123],'dataset_columns':42,
         'source_code_files':0,'new_recommendation_model_calls':0,'files':len(files)}
(BUILD/'delivery-validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
