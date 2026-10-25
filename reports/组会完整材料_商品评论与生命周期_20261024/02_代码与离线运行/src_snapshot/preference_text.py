"""Finite, label-independent text projection for the approved trial profile."""

from collections import Counter
from difflib import SequenceMatcher
import hashlib
from html.parser import HTMLParser
import re


POLICY = 'finite-text-1.0.0'
URL = re.compile(r'''(?i)\b(?:https?://|ftp://|www\.)[^\s<>"']+''')
EMAIL = re.compile(r'(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9.-])')
PHONE = re.compile(r'(?<![A-Za-z0-9])(?:\+?1[ \t.-]?)?(?:\(\d{3}\)|\d{3})[ \t.-]?\d{3}[ \t.-]?\d{4}(?![A-Za-z0-9])')
SHIPPING = re.compile(r'(?i)\s*[-–—|]?\s*Ships Free over \$\d+(?:\.\d+)?\s*$')
DYNAMIC = [re.compile(p, re.I) for p in (
    r'\b[0-5](?:\.\d+)?\s*(?:out\s+of\s+5(?:\s+stars?)?|stars?)\b',
    r'\b[\d,]+\s+(?:customer\s+)?(?:ratings?|reviews?)\b',
    r'(?:[$£€]\s*\d+(?:[.,]\d+)*|\b(?:USD|EUR|GBP)\s*\d+(?:[.,]\d+)*|\b\d+(?:[.,]\d+)*\s*(?:USD|EUR|GBP|dollars?)\b)')]


class TextError(ValueError):
    pass


class PlainText(HTMLParser):
    blocks = {'br', 'p', 'div', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
              'table', 'tr', 'td', 'th', 'blockquote', 'section', 'article', 'header', 'footer', 'hr'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = None
        self.counts = Counter()

    def handle_starttag(self, tag, attrs):
        self.counts['html_tags'] += 1
        if tag in ('script', 'style'):
            self.hidden = tag
        elif self.hidden is None and tag in self.blocks:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag == self.hidden:
            self.hidden = None
        elif self.hidden is None and tag in self.blocks and tag not in ('br', 'hr'):
            self.parts.append('\n')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in ('br', 'hr'):
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.hidden is None:
            self.parts.append(data)

    def handle_comment(self, data):
        self.counts['html_comments'] += 1


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def project_text(source, kind, source_user=None):
    if not isinstance(source, str):
        raise TextError('text_processing_error')
    source.encode('utf-8', errors='strict')
    current = source
    trace = []
    counts = Counter()

    def change(stage, value):
        nonlocal current
        if current != value:
            edits = [{'operation': op, 'input_start': a, 'input_end': b, 'output_start': c, 'output_end': d}
                     for op, a, b, c, d in SequenceMatcher(None, current, value, autojunk=False).get_opcodes() if op != 'equal']
            trace.append({'stage': stage, 'coordinate': 'stage_input_output_unicode_codepoints',
                          'input_sha256': digest(current), 'output_sha256': digest(value), 'edits': edits})
        current = value

    change('line_endings', current.replace('\r\n', '\n').replace('\r', '\n'))
    parser = PlainText()
    parser.feed(current)
    parser.close()
    if parser.hidden:
        raise TextError('text_processing_error')
    counts.update(parser.counts)
    counts['entity_forms'] = len(re.findall(r'&(?:#\d+|#x[0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]+);', current))
    change('html', ''.join(parser.parts))
    counts['controls_removed'] = sum(ord(c) < 32 and c not in '\t\n' or ord(c) == 127 for c in current)
    change('controls', ''.join(c for c in current if not (ord(c) < 32 and c not in '\t\n' or ord(c) == 127)))

    def link(match):
        value = match.group()
        return '[LINK]' + value[len(value.rstrip('.,;:!?)]}')):]

    value, counts['links_redacted'] = URL.subn(link, current)
    change('links', value)
    value, counts['emails_redacted'] = EMAIL.subn('[EMAIL]', current)
    change('emails', value)
    value, counts['phones_redacted'] = PHONE.subn('[PHONE]', current)
    change('phones', value)
    if source_user:
        counts['source_users_redacted'] = current.count(source_user)
        change('source_user', current.replace(source_user, '[USER]'))
    value = '\n'.join(re.sub(r'[^\S\n]+', ' ', line).strip() for line in current.split('\n'))
    change('whitespace', re.sub(r'\n{3,}', '\n\n', value).strip())
    if kind == 'product_title':
        value, counts['commercial_tails_removed'] = SHIPPING.subn('', current)
        change('commercial_tail', value.strip())
        if any(pattern.search(current) for pattern in DYNAMIC):
            raise TextError('embedded_dynamic_unhandled')
    if not current or not re.sub(r'\[(?:LINK|EMAIL|PHONE|USER)\]', '', current).strip():
        raise TextError('text_processing_error')
    return current, {'text_policy_version': POLICY, 'original_sha256': digest(source), 'processed_sha256': digest(current),
                     'raw_codepoints': len(source), 'processed_codepoints': len(current),
                     'raw_utf8_bytes': len(source.encode('utf-8')), 'processed_utf8_bytes': len(current.encode('utf-8')),
                     'operations': {k: v for k, v in counts.items() if v}, 'stages': trace}
