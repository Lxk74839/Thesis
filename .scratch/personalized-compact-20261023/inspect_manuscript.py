"""Read-only source inventory for the revision; run with the bundled artifact runtime."""
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
from lxml import etree as E

source = Path('E:/工作/成果/小论文/初稿/论文初稿.docx')
with ZipFile(source) as z:
    doc = E.fromstring(z.read('word/document.xml'))
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'}
body = doc.find('w:body', ns)
for i, node in enumerate(body):
    text = ''.join(node.xpath('.//w:t/text() | .//m:t/text()', namespaces=ns))
    if text:
        print(i, E.QName(node).localname, text[:500])
print(json.dumps({'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'math_blocks': len(doc.xpath('//m:oMath', namespaces=ns)),
    'tables': len(doc.xpath('//w:tbl', namespaces=ns))}))
