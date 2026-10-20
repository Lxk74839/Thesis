"""Archive the already-created PUBLIC example, without running a recommendation."""
import json
from pathlib import Path
from evidence_access import PROJECT, digest, encoded
from experiment_io import load_evaluation_inputs
from experiment_evaluation import score_task, summarize

directory = PROJECT / '.scratch/ticket14-live-integration-20261020'
example = json.loads((directory / 'public-example.json').read_bytes())
plan, observations = load_evaluation_inputs(Path(example['plan']['path']).parent,
    execution_index=example['execution_index'], reference_sources=example['reference_sources'])
scores = [score_task(**o) for o in observations]
summary = summarize(plan, scores)
assert summary['status'] == 'incomplete' and summary['counts']['not_started'] == 49
assert summary['comparisons']['C1']['estimate'] is None
for name, raw in (('public-task-scores-final-v2.jsonl', b''.join(encoded(s) + b'\n' for s in scores)),
                  ('public-summary-final-v2.json', encoded(summary) + b'\n')):
    with (directory / name).open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'path': name, 'bytes': len(raw), 'sha256': digest(raw), 'scope': 'public_fixture_only'}))
