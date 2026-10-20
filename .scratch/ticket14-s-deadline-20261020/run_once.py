"""New control directory for the one explicitly authorized S retry."""
import importlib.util
from pathlib import Path
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
spec = importlib.util.spec_from_file_location('inherited_S_control',
    ROOT / '.scratch/ticket14-s-engineering-20261020/run_once.py')
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)
from p1_engineering import RETRY_AUTHORIZATION

p1 = control.p1
RUN_ID = 'P1-D1-V00-S-' + RETRY_AUTHORIZATION
ensure_first_execution = control.ensure_first_execution


if __name__ == '__main__':
    if sys.stdin.buffer.readline() != b'GO\n':
        raise SystemExit(2)
    control.PACKAGE = PACKAGE
    control.AUTHORIZATION = RETRY_AUTHORIZATION
    control.RUN_ID = RUN_ID
    raise SystemExit(control.main())
