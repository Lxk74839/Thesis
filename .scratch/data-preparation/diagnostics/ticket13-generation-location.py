"""One-off CLI exception location; prints only source line and missing field name."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]


def locate(frame, event, argument):
    if frame.f_code.co_filename != str(ROOT/'joint_tasks.py'):
        return None
    if event=='exception' and argument[0] is KeyError:
        print('joint_tasks.py',frame.f_lineno,'missing field',str(argument[1]),file=sys.stderr)
    return locate


sys.argv[0]=str(ROOT/'prepare_data.py')
sys.path.insert(0,str(ROOT))
sys.settrace(locate)
runpy.run_path(sys.argv[0],run_name='__main__')
