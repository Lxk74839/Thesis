"""Run only the public quality CLI with an audited, target-blind read allowlist."""
import argparse
import json
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from quality_fusion import APPROVAL


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',default='.')
    parser.add_argument('--label',required=True);args=parser.parse_args()
    config=ROOT/'config/quality-fusion-0.1.0.json'
    cfg=json.loads(config.read_bytes())
    normal=ROOT/cfg['normal_binding']['record']['path']
    record=json.loads(normal.read_bytes())
    allowed={config,normal,*(ROOT/i['path'] for i in cfg['normal_binding'].values()),
             *(ROOT/i['path'] for i in record['components'].values()),*(ROOT/i['path'] for i in APPROVAL.values()),
             *(ROOT/name for name in ('prepare_data.py','quality_fusion.py','recommendation_actions.py','sim_normal.py','sim_scenarios.py'))}
    allowed={p.resolve() for p in allowed};runtime=Path(sys.prefix).resolve()
    output=(ROOT/args.output_root).resolve()
    writes=[output/'data/sim-quality',output/'records/sim-quality',ROOT/'data/sim-quality/failures',ROOT/'.tmp',ROOT/'data/quality-fusion-audit']
    reads=[];denied=[]
    def audit(event,values):
        if event in ('subprocess.Popen','os.system','socket.connect','socket.bind'):
            raise RuntimeError('quality_prepare_forbidden_capability:'+event)
        if event!='open' or not isinstance(values[0],(str,bytes)):return
        path=Path(values[0]).resolve();mode=values[1] or '';flags=values[2]
        writing=any(c in mode for c in 'wax+') or bool(flags & (0x1|0x2|0x100|0x200|0x400))
        if writing:
            if not any(path.is_relative_to(p) for p in writes):
                denied.append(str(path));raise RuntimeError('quality_prepare_write_denied')
        elif path not in allowed and not path.is_relative_to(runtime) and not path.is_relative_to(output/'data/sim-quality') and not path.is_relative_to(output/'records/sim-quality'):
            denied.append(str(path));raise RuntimeError('quality_prepare_read_denied')
        elif path.is_relative_to(ROOT) and not path.is_relative_to(runtime):reads.append(path.relative_to(ROOT).as_posix())
    sys.addaudithook(audit)
    sys.argv=[str(ROOT/'prepare_data.py'),'--stage','quality_fusion','--sim-record',str(normal),
              '--quality-config',str(config),'--output-root',str(output)]
    code=0
    try:runpy.run_path(str(ROOT/'prepare_data.py'),run_name='__main__')
    except SystemExit as exc:code=exc.code or 0
    finally:
        evidence={'status':'passed' if code==0 and not denied else 'failed','read_paths':sorted(set(reads)),
            'denied':denied,'model_API_calls':0,'guard':'allowlist_no_tasks_targets_history_b_or_subprocess_network'}
        path=ROOT/'data/quality-fusion-audit/20261016'/('read-guard-'+args.label+'.json')
        with path.open('xb') as stream:stream.write(json.dumps(evidence,sort_keys=True).encode()+b'\n')
        print(json.dumps({'guard_status':evidence['status'],'unique_project_read_paths':len(set(reads)),'denied_count':len(denied)},sort_keys=True))
    raise SystemExit(code)


if __name__=='__main__':main()
