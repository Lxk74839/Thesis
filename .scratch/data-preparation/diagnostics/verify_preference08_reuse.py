"""CLI idempotence and retained first-release byte checks for ticket08."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    assert Path(sys.executable).resolve() == ROOT / '.conda/envs/Thesis/python.exe'
    final = ROOT / 'records/preference-tasks/grain-A-1.1.15-preference-task-1.0.1.json'
    before = final.read_bytes()
    expected = json.loads(before)
    result = subprocess.run([sys.executable, str(ROOT/'prepare_data.py'), '--stage', 'preference_tasks',
        '--cleaning-record', 'records/cleaning/grain-A-1.1.15-review-cleaning-1.0.0.json',
        '--split-record', 'records/splits/grain-A-1.1.15-user-split-1.0.0.json',
        '--task-config', 'config/preference-task-1.0.1.json', '--output-root', '.',
        '--access-probe', 'data/task-inputs/preference-task-1.0.1/access-probe-1.0.0.jsonl'],
        cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    assert result.returncode == 0 and json.loads(result.stdout) == expected, 'real_cli_reuse_changed_receipt'
    assert final.read_bytes() == before, 'real_cli_reuse_changed_record_bytes'
    old_path = ROOT/'records/preference-tasks/grain-A-1.1.15-preference-task-1.0.0.json'
    old = json.loads(old_path.read_text('utf-8'))
    rejected = json.loads(old_path.with_name(old_path.stem+'-acceptance.json').read_text('utf-8'))
    assert digest(old_path) == rejected['record_sha256'], 'rejected_record_was_changed'
    for component in old['components'].values():
        assert digest(ROOT/component['path']) == component['sha256'], 'rejected_component_was_changed'
    configs = [json.loads((ROOT/'config'/('preference-task-'+v+'.json')).read_text('utf-8')) for v in ('1.0.0','1.0.1')]
    assert configs[0]['identity_key'] == configs[1]['identity_key'], 'patch_did_not_reuse_frozen_key'
    report = {'status':'passed','real_cli_reuse_receipt_equal':True,'record_bytes_unchanged':True,
              'rejected_1_0_0_components_unchanged':len(old['components']),'same_frozen_key_binding':True,
              'record_sha256':digest(final),'recommendation_model_calls':0}
    path = ROOT/'.scratch/data-preparation/verification/ticket08-1.0.1-reuse-check.json'
    path.write_bytes((json.dumps(report,sort_keys=True,separators=(',',':'))+'\n').encode())
    print(json.dumps(report,sort_keys=True))


if __name__ == '__main__':
    main()
