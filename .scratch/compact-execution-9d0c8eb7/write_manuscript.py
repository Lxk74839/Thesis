"""Patch only approved result slots; retain all other DOCX bytes and math paragraphs."""
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as E
import xml.parsers.expat
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'manuscript/论文初稿_推荐算法与精简实验修订版_20261023.docx'
OUTPUT = ROOT / 'manuscript/论文初稿_compact正式结果_9d0c8eb7.docx'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
M = '{http://schemas.openxmlformats.org/officeDocument/2006/math}'
E.register_namespace('w', W[1:-1])
E.register_namespace('m', M[1:-1])
E.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')


def spans(raw):
    """Byte ranges of direct body children, without rewriting the XML envelope."""
    parser = xml.parsers.expat.ParserCreate()
    stack, rows, current = [], [], None

    def start(name, attrs):
        nonlocal current
        if stack and stack[-1] == 'w:body':
            current = parser.CurrentByteIndex
        stack.append(name)

    def end(name):
        nonlocal current
        if len(stack) >= 2 and stack[-2] == 'w:body':
            at = parser.CurrentByteIndex
            stop = raw.index(b'>', at) + 1 if raw[at:at + 2] == b'</' else at
            rows.append((current, stop))
            current = None
        stack.pop()

    parser.StartElementHandler, parser.EndElementHandler = start, end
    parser.Parse(raw, True)
    return rows


def serialize(element):
    return E.tostring(element, encoding='utf-8', short_empty_elements=True)


def paragraph(template, text):
    p = E.Element(W + 'p', template.attrib)
    props = template.find(W + 'pPr')
    if props is not None:
        p.append(copy.deepcopy(props))
    r = E.SubElement(p, W + 'r')
    style = template.find('.//' + W + 'rPr')
    if style is not None:
        r.append(copy.deepcopy(style))
    E.SubElement(r, W + 't', {'{http://www.w3.org/XML/1998/namespace}space': 'preserve'}).text = text
    return p


def table(template, rows, widths):
    assert sum(widths) == 9072 and all(len(row) == len(widths) for row in rows)
    t = E.Element(W + 'tbl')
    props = copy.deepcopy(template.find(W + 'tblPr'))
    props.find(W + 'tblW').attrib.update({W + 'type': 'dxa', W + 'w': '9072'})
    t.append(props)
    grid = E.SubElement(t, W + 'tblGrid')
    for width in widths:
        E.SubElement(grid, W + 'gridCol', {W + 'w': str(width)})
    for index, row in enumerate(rows):
        tr = E.SubElement(t, W + 'tr')
        trpr = E.SubElement(tr, W + 'trPr')
        E.SubElement(trpr, W + 'cantSplit')
        if index == 0:
            E.SubElement(trpr, W + 'tblHeader')
        for value, width in zip(row, widths):
            cell = E.SubElement(tr, W + 'tc')
            cp = E.SubElement(cell, W + 'tcPr')
            E.SubElement(cp, W + 'tcW', {W + 'type': 'dxa', W + 'w': str(width)})
            E.SubElement(cp, W + 'vAlign', {W + 'val': 'center'})
            if index == 0:
                borders = E.SubElement(cp, W + 'tcBorders')
                E.SubElement(borders, W + 'bottom', {W + 'val': 'single', W + 'sz': '4', W + 'color': '000000'})
            p = E.SubElement(cell, W + 'p')
            pp = E.SubElement(p, W + 'pPr')
            if index == 0:
                E.SubElement(pp, W + 'keepNext')
            E.SubElement(pp, W + 'widowControl')
            E.SubElement(pp, W + 'spacing', {W + 'before': '20', W + 'after': '20', W + 'line': '320', W + 'lineRule': 'exact'})
            E.SubElement(pp, W + 'ind', {W + 'firstLine': '0'})
            E.SubElement(pp, W + 'jc', {W + 'val': 'left' if width == widths[0] and len(str(value)) > 14 else 'center'})
            r = E.SubElement(p, W + 'r')
            rp = E.SubElement(r, W + 'rPr')
            E.SubElement(rp, W + 'rFonts', {W + 'ascii': 'Times New Roman', W + 'hAnsi': 'Times New Roman', W + 'eastAsia': 'SimSun'})
            if index == 0:
                E.SubElement(rp, W + 'b')
            E.SubElement(rp, W + 'color', {W + 'val': '000000'})
            E.SubElement(rp, W + 'sz', {W + 'val': '21'})
            E.SubElement(r, W + 't').text = str(value)
    return t


def main():
    inventory = json.loads((HERE / 'document-inventory.json').read_bytes())
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == inventory['reference_sha256']
    content = json.loads((HERE / 'manuscript-content.json').read_bytes())
    with zipfile.ZipFile(SOURCE) as source:
        raw = source.read('word/document.xml')
        body = E.fromstring(raw).find(W + 'body')
        ranges = spans(raw)
        assert len(ranges) == len(body)
        replacements = {int(i): text for i, text in content['replace'].items()}
        math_indices = [i for i, child in enumerate(body) if child.findall('.//' + M + 'oMath')]
        assert not set(math_indices) & set(replacements)
        inserts = b''
        for block in content['insert_after_111']:
            if 'caption' in block:
                element = paragraph(body[37], block['caption'])
            elif 'paragraph' in block:
                element = paragraph(body[111], block['paragraph'])
            else:
                element = table(body.find(W + 'tbl'), block['rows'], block['widths'])
            inserts += serialize(element)
        chunks, cursor, retained_math = [], 0, []
        for index, (a, b) in enumerate(ranges):
            chunks.append(raw[cursor:a])
            chunks.append(serialize(paragraph(body[index], replacements[index])) if index in replacements else raw[a:b])
            if index in math_indices:
                retained_math.append(hashlib.sha256(raw[a:b]).hexdigest())
            if index == 111:
                chunks.append(inserts)
            cursor = b
        chunks.append(raw[cursor:])
        updated = b''.join(chunks)
        result_body = E.fromstring(updated).find(W + 'body')
        result_math = [hashlib.sha256(updated[a:b]).hexdigest() for a, b in spans(updated)
                       if updated[a:b].find(b'<m:oMath') >= 0]
        assert result_math == retained_math
        assert ''.join(result_body[0].itertext()) == '一种基于区块链与多智能体技术的农产品可信推荐方法'
        with zipfile.ZipFile(OUTPUT, 'w', compression=zipfile.ZIP_DEFLATED) as target:
            for item in source.infolist():
                target.writestr(item, updated if item.filename == 'word/document.xml' else source.read(item.filename))
    with zipfile.ZipFile(SOURCE) as before, zipfile.ZipFile(OUTPUT) as after:
        changed_parts = [name for name in before.namelist() if before.read(name) != after.read(name)]
        assert changed_parts == ['word/document.xml']
    original = Path(inventory['read_only_source'])
    checks = {'output': str(OUTPUT), 'sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        'source_unchanged': hashlib.sha256(SOURCE.read_bytes()).hexdigest() == inventory['reference_sha256'],
        'original_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
        'changed_package_parts': changed_parts, 'raw_math_paragraphs_preserved': len(retained_math),
        'seven_numbered_main_formula_source_indices': [29, 41, 55, 58, 68, 71, 75],
        'replaced_body_indices': sorted(replacements), 'new_tables': sum('rows' in b for b in content['insert_after_111'])}
    assert checks['source_unchanged'] and checks['original_sha256'] == 'e09436082eb3cea837e81b89551da6d36b6e9f0ce213eb2d94065329bbc3e027'
    (HERE / 'manuscript-check.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(checks, ensure_ascii=False))


if __name__ == '__main__':
    main()
