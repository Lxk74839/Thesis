"""Read the required manuscript without modifying its bytes."""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

root = Path(__file__).resolve().parents[3]
source = root / 'manuscript/论文初稿_表达与实验结构修订版_20261010.docx'
with zipfile.ZipFile(source) as archive:
    tree = ET.fromstring(archive.read('word/document.xml'))
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'}
paragraphs = [''.join(n.text or '' for n in p.iter()
                      if n.tag in {f'{{{ns["w"]}}}t', f'{{{ns["m"]}}}t'})
              for p in tree.findall('.//w:p', ns)]
target = root / '.scratch/data-preparation/verification/ticket14-20261016/manuscript-readonly.txt'
with target.open('x', encoding='utf-8') as stream:
    stream.write('\n'.join(paragraphs) + '\n')
print(json.dumps({'python': sys.version, 'prefix': sys.prefix, 'paragraphs': len(paragraphs),
                  'manuscript_sha256': hashlib.file_digest(source.open('rb'), 'sha256').hexdigest(),
                  'extracted_path': str(target.relative_to(root))}, ensure_ascii=False))
