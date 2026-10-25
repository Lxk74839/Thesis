"""Read-only source and template inventory for surgical results insertion."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parents[2]
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'}
source = ROOT / 'manuscript/论文初稿_推荐算法与精简实验修订版_20261023.docx'
baseline = ROOT / 'manuscript/论文初稿_表达与实验结构修订版_20261010.docx'
for file, name in ((source, 'revised-template-text.txt'), (baseline, 'required-baseline-text.txt')):
    with ZipFile(file) as z:
        doc = E.fromstring(z.read('word/document.xml'))
        body = doc.find('w:body', NS)
        text = '\n'.join(str(i) + ': ' + ''.join(t.text or '' for t in node.iter()
            if t.tag in ('{' + NS['w'] + '}t', '{' + NS['m'] + '}t')) for i, node in enumerate(body))
    Path(__file__).with_name(name).write_text(text, encoding='utf-8')
with ZipFile(source) as z:
    package = {n: {'bytes': len(z.read(n)), 'sha256': hashlib.sha256(z.read(n)).hexdigest()} for n in z.namelist()}
inventory = {'reference': str(source), 'reference_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'parts': package, 'read_only_source': 'E:/工作/成果/小论文/初稿/论文初稿.docx'}
Path(__file__).with_name('document-inventory.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'template_sha256': inventory['reference_sha256'], 'parts': len(package)}))
