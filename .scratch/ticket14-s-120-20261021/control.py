"""This S grant's cumulative send/cap ledger; no retries or sample expansion."""
import json
from pathlib import Path

A5_RUN = 'P1-D1-V00-S-S-COMPLETE-ONCE-20261021-A5'


def requests(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()] if Path(path).exists() else []


def claim_request(path, body, run_id):
    rows = requests(path)
    cap = body['max_output_tokens']
    extended = run_id == A5_RUN
    own = [r for r in rows if r['run_id'] == run_id]
    if (body.get('model') != 'gpt-6-luna' or type(cap) is not int or not 0 < cap <= 8192
            or len(rows) >= (17 if extended else 12)
            or sum(r['output_cap'] for r in rows) + cap > (132572 if extended else 98304)
            or extended and (len(own) >= 12 or sum(r['output_cap'] for r in own) + cap > 91612)):
        raise OSError('cumulative_S_generation_limit')
    # Claimed before the external worker, never refunded after an uncertain send.
    with Path(path).open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'run_id': run_id, 'sequence': len(rows) + 1, 'output_cap': cap}) + '\n')
        stream.flush()


def execution_used(package):
    return sum(json.loads(line)['seconds'] for attempt in ('A1', 'A2', 'A3', 'A4', 'A5')
        for line in ((Path(package) / attempt / 'execution-resources.jsonl').read_text().splitlines()
                     if (Path(package) / attempt / 'execution-resources.jsonl').exists() else []))
