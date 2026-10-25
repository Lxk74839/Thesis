"""Package only the final meeting materials after reviewing all three pages."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(r'D:\Work\Codex\Project\Thesis')
BUILD = ROOT / '.scratch/meeting-role-refinement-20261025'
PACKAGE = ROOT / 'reports/组会汇报_角色完善版_20261025'
OUTPUT = ROOT / 'reports/组会材料_学术风格角色完善版_20261025.zip'
assert not OUTPUT.exists(), 'Preserve any previously delivered archive.'
for page in range(1, 4):
    assert (BUILD / f'final-page-{page}.png').is_file()
files = sorted(path for path in PACKAGE.rglob('*') if path.is_file())
assert len(list(PACKAGE.glob('*.docx'))) == 1
assert len(list((PACKAGE / '数据集').glob('*.csv'))) == 2
assert not any('卡通' in path.name for path in files)
assert not any(path.suffix.lower() in ('.py', '.js', '.ps1', '.pdf') for path in files)
with zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in files:
        archive.write(path, (Path(PACKAGE.name) / path.relative_to(PACKAGE)).as_posix())
with zipfile.ZipFile(OUTPUT) as archive:
    assert archive.testzip() is None
    assert len(archive.namelist()) == len(files)
summary = {'archive': str(OUTPUT), 'files': len(files), 'bytes': OUTPUT.stat().st_size,
           'sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
           'qa_pages_visually_reviewed': 3,
           'contents': [path.relative_to(PACKAGE).as_posix() for path in files]}
(BUILD / 'final-package.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
