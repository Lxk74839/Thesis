"""Hash-only integrity audit of protected materials and retained run records."""
import hashlib
import json
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
PROJECT = AUDIT.parents[2]
OUTPUT = PROJECT/'data/recommendation-runtime-audit/macrec-agri-dev-task16'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def verify(rows, root):
    checked = []
    for row in rows:
        path = root/row['path']
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        checked.append({'path':path.relative_to(PROJECT).as_posix(),
            'expected_sha256':row['sha256'],'actual_sha256':actual,
            'unchanged':actual == row['sha256']})
    return {'count':len(checked),'passed':all(r['unchanged'] for r in checked),'files':checked}


prior = PROJECT/'.scratch/macrec-algorithm-20261023/implementation-20261024'
checks = {}
for name in ('protected-check','draft-protection','upstream-check'):
    root = PROJECT/'.scratch/macrec-algorithm-20261023/sources' if name=='upstream-check' else PROJECT
    checks[name] = verify(read(prior/(name+'.json'))['files'],root)
checks['old-run-immutable'] = verify(read(OUTPUT/'execution-revisions/v00-v1-before-protocol-v2/immutable-records.json'),PROJECT)
manifest = read(AUDIT/'real-response-manifest.json')
checks['original-14-requests-responses'] = verify([r[key] for r in manifest for key in ('request','response')],PROJECT)
seal = read(OUTPUT/'review-seal.json')
checks['sealed-code-and-reviews'] = verify(seal['code']+seal['reviews'],PROJECT)
result = {'passed':all(r['passed'] for r in checks.values()),'checks':checks}
(AUDIT/'source-protection.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':result['passed'],'checks':{k:{'count':v['count'],'passed':v['passed']} for k,v in checks.items()}}))
