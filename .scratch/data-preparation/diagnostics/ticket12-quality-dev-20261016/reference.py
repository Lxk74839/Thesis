"""Independent raw-material diagnostic reference. Never reads allocation or b.

Limited to the authorized v1 normal-derived branch: no revocations/replacements.
Unexpected action/version scope is rejected, not treated as accepted upstream.
"""
from collections import Counter, defaultdict
from fractions import Fraction
import json
from pathlib import Path
from support import canonical, digest, read, load, write, resources

TAG = b'Thesis-ticket12-quality-snapshot-v1\0'
FILES = ('batches.jsonl', 'events.jsonl', 'materials.jsonl', 'registrations.jsonl', 'actions.jsonl', 'policy.json')
STAGES = ('harvest', 'packaging', 'storage', 'inspection', 'transport', 'retail')
KINDS = ('harvest_record', 'packaging_binding', 'storage_log', 'inspection_sample',
         'inspection_report', 'transport_dispatch', 'transport_receipt', 'retail_status')


def ratio(value):
    return {'numerator': value.numerator, 'denominator': value.denominator}


def derive(folder):
    """Derive facts from sealed raw bytes, registry, graph, and policy only."""
    folder = Path(folder)
    snap = load(folder/'snapshot.json')
    core = {k: v for k, v in snap.items() if k != 'snapshot_id'}
    if snap['snapshot_id'] != 'qd_' + digest(TAG + canonical(core)):
        raise ValueError('snapshot_identity_mismatch')
    if set(snap['components']) != set(FILES):
        raise ValueError('incomplete_snapshot_scope')
    objects = {}; raw_hash = {}; groups = defaultdict(list); regs = {}
    for name in FILES:
        binding = snap['components'][name]
        raw = read(folder/name, binding['sha256'])
        lines = raw.splitlines(keepends=True)
        if binding['bytes'] != len(raw) or binding['records'] != len(lines):
            raise ValueError('component_count_or_size')
        if name == 'policy.json':
            policy = json.loads(raw)
            continue
        if name == 'actions.jsonl':
            if raw:
                raise ValueError('actions_outside_diagnostic_v1')
            continue
        for line in lines:
            row = json.loads(line)
            if line != canonical(row) + b'\n':
                raise ValueError('noncanonical_original')
            if name == 'registrations.jsonl':
                key = row['target_id']
                if key in regs:
                    raise ValueError('duplicate_registration')
                regs[key] = row
            else:
                key = row['sim_batch_id'] if name == 'batches.jsonl' else row['event_id'] if name == 'events.jsonl' else row['evidence_id']
                if key in objects:
                    raise ValueError('duplicate_object_id')
                objects[key] = row; raw_hash[key] = digest(line[:-1])
                groups[row['parent_asin']].append(key)
        resources()
    if set(objects) != set(regs):
        raise ValueError('registration_scope_not_complete')
    sequence = sorted(r['sequence'] for r in regs.values())
    if sequence != list(range(1, len(regs)+1)) or snap['cutoff_sequence'] != len(regs):
        raise ValueError('registry_sequence_gap')
    if policy['policy_id'] != snap['policy_id'] or policy['source'] != 'SIM':
        raise ValueError('policy_identity')
    if policy['read_principal_id'] != snap['read_principal_id'] or policy['read_scope']['scope'] != 'current_snapshot_only':
        raise ValueError('principal_or_scope')
    tau, sealed = snap['verify_at_ms'], snap['sealed_at_ms']
    if not isinstance(tau, int) or not isinstance(sealed, int) or sealed > tau:
        raise ValueError('invalid_snapshot_time')
    issuers = {i['issuer_id']: i for i in policy['issuers']}

    def kind(row):
        return 'material' if 'evidence_id' in row else 'event' if 'event_id' in row else 'batch'

    def admissible(key, batch_id):
        row = objects[key]; reg = regs[key]; typ = kind(row)
        issuer = row.get('issuer_id', row.get('actor_id'))
        actor = issuers.get(issuer, {})
        event_id = row.get('event_id')
        checks = {
            'raw_digest': raw_hash[key] == reg['content_sha256'],
            'registry_identity': reg['target_kind'] == typ and reg['parent_asin'] == row['parent_asin']
                and reg['sim_batch_id'] == row['sim_batch_id'] == batch_id
                and reg['issuer_id'] == issuer and reg['event_id'] == event_id,
            'accepted_registration': reg['receipt_status'] == 'accepted'
                and reg['registrar_id'] == policy['registrar_id']
                and reg['registry_backend'] == 'local_sim_registry',
            'v1_scope': row['version'] == reg['version'] == 1 and row['source'] == reg['source'] == 'SIM',
            'read_permission': typ in policy['read_scope']['target_kinds']
                and (typ != 'material' or row['kind'] in policy['read_scope']['material_kinds']),
            'registered_before_seal': reg['registered_at_ms'] <= sealed <= tau}
        if typ == 'batch':
            checks['issuer_authority'] = actor.get('may_create_batch', False)
            checks['creation_time'] = row['created_at_ms'] <= reg['registered_at_ms']
        elif typ == 'event':
            checks['issuer_authority'] = row['stage'] in actor.get('event_stages', [])
            checks['event_time'] = row['event_start_ms'] <= row['event_end_ms'] <= reg['registered_at_ms']
        else:
            checks['issuer_authority'] = row['kind'] in actor.get('material_kinds', [])
            event = objects.get(event_id, {})
            checks['material_event_identity'] = event.get('parent_asin') == row['parent_asin'] and event.get('sim_batch_id') == batch_id
            checks['issuance_time'] = row['issued_at_ms'] <= reg['registered_at_ms']
            checks['event_registered_first'] = event_id in regs and regs[event_id]['registered_at_ms'] <= reg['registered_at_ms']
            if row['temporal_mode'] == 'current_assertion':
                lo, hi = row['valid_from_ms'], row['valid_to_ms']
                checks['current_interval'] = lo < hi and lo <= tau < hi
            elif row['temporal_mode'] != 'historical_fact':
                checks['known_temporal_mode'] = False
        return [name for name, passed in checks.items() if not passed]

    output = []
    for parent in sorted(groups, key=lambda p: p.encode('utf-8')):
        keys = groups[parent]
        batches = [k for k in keys if kind(objects[k]) == 'batch']
        if len(batches) != 1:
            raise ValueError('batch_coverage')
        batch_id = batches[0]
        reasons = {key: admissible(key, batch_id) for key in keys}
        stages = {objects[k]['stage']: k for k in keys if kind(objects[k]) == 'event'}
        if set(stages) != set(STAGES) or sum(kind(objects[k])=='event' for k in keys) != 6:
            raise ValueError('event_stage_coverage')
        graph_ok = not reasons[batch_id]
        previous = None
        for stage in STAGES:
            key = stages[stage]; event = objects[key]
            expected = [] if previous is None else [previous]
            graph_ok &= not reasons[key] and event['predecessor_event_ids'] == expected
            if previous:
                graph_ok &= objects[previous]['event_end_ms'] <= event['event_start_ms']
            previous = key
        materials = defaultdict(list)
        for key in keys:
            row = objects[key]
            if kind(row) == 'material':
                materials[row['kind']].append(key)
        if set(materials) - set(KINDS):
            raise ValueError('unknown_material_kind')

        def usable(name):
            expected_stage = 'retail' if name == 'retail_status' else 'transport' if name in ('transport_receipt','transport_dispatch') else 'inspection'
            return [k for k in materials[name] if not reasons[k] and graph_ok and objects[k]['event_id'] == stages[expected_stage]]

        sample, report = usable('inspection_sample'), usable('inspection_report')
        conclusions = []
        for rk in report:
            r = objects[rk]; facts = r['facts']
            matches = [objects[sk] for sk in sample if objects[sk]['facts']['sample_id'] == facts['sample_id']]
            if len(matches) != 1 or facts['test_scope'] != ['SIM-Q1']:
                continue
            s = matches[0]
            inspection = objects[stages['inspection']]
            if (inspection['event_start_ms'] <= s['facts']['sampled_at_ms'] <= facts['test_started_at_ms']
                    <= facts['test_completed_at_ms'] <= inspection['event_end_ms']
                    and s['facts']['sampled_at_ms'] <= s['issued_at_ms'] and facts['test_completed_at_ms'] <= r['issued_at_ms']):
                conclusions.append(facts['conclusion'])
        r1 = 'Supported' if conclusions and set(conclusions) == {'pass'} else 'Conflict' if set(conclusions) == {'pass', 'fail'} else 'Refuted' if conclusions and set(conclusions) == {'fail'} else 'Pending'
        retail, receipt = usable('retail_status'), usable('transport_receipt')
        dispatch = usable('transport_dispatch')
        transport = objects[stages['transport']]
        receipt = [key for key in receipt if objects[key]['facts'].get('handover_status')=='accepted'
                   and transport['event_start_ms'] <= objects[key]['facts']['arrived_at_ms'] <= transport['event_end_ms']
                   and objects[key]['facts']['arrived_at_ms'] <= objects[key]['issued_at_ms']
                   and any(all(objects[key]['facts'][f] == objects[dk]['facts'][f]
                               for f in ('transport_segment_id','from_location_id','to_location_id','unit'))
                           and objects[dk]['facts']['departed_at_ms'] <= objects[key]['facts']['arrived_at_ms'] for dk in dispatch)]
        statuses = {objects[k]['facts']['status'] for k in retail}
        r5 = 'Supported' if statuses == {'on_sale'} else 'Pending' # other R5 vocab is outside this normal-derived diagnostic
        stocks = []
        for key in retail:
            row = objects[key]; f = row['facts']; observed = f['observed_at_ms']
            if (type(f.get('stock_units')) is int and 0 <= f['stock_units'] <= 100 and f.get('unit') == 'SIM_PACK'
                    and row['valid_from_ms'] <= observed < row['valid_to_ms']
                    and observed <= row['issued_at_ms'] <= regs[key]['registered_at_ms'] <= sealed):
                stocks.append(key)
        values = {objects[k]['facts']['stock_units'] for k in stocks}
        z = int(len(values) == 1)
        state = 'Supported' if z else 'Conflict' if len(values)>1 else 'Pending'
        x = next(iter(values)) if z else None
        complete = int(bool(stocks))
        # Equal current supports use the minimum remaining fraction (conservative).
        t = min((Fraction(objects[k]['valid_to_ms']-tau, objects[k]['valid_to_ms']-objects[k]['valid_from_ms']) for k in stocks), default=Fraction(0))
        a_checks = [False, False]
        if stocks and receipt:
            a_checks[0] = all(objects[k]['parent_asin'] == parent and objects[k]['sim_batch_id'] == batch_id for k in stocks+receipt)
            a_checks[1] = all(objects[r]['facts']['to_location_id'] == objects[s]['facts']['location_id']
                              and objects[r]['facts']['unit'] == objects[s]['facts']['unit'] for r in receipt for s in stocks)
        agreement = Fraction(sum(a_checks), 2)
        q = {str(float(bt)): ratio(z*((1-bt)/2*complete+bt*t+(1-bt)/2*agreement)) for bt in (Fraction(1,4),Fraction(1,2),Fraction(3,4))}
        cites = []
        paths = {'retail_status':['/facts/stock_units','/facts/observed_at_ms','/facts/unit','/facts/location_id','/valid_from_ms','/valid_to_ms'],
                 'transport_receipt':['/facts/transport_segment_id','/facts/arrived_at_ms','/facts/to_location_id','/facts/unit'],
                 'transport_dispatch':['/facts/transport_segment_id','/facts/departed_at_ms','/facts/to_location_id','/facts/unit'],
                 'inspection_sample':['/facts/sample_id','/facts/sampled_at_ms'],
                 'inspection_report':['/facts/sample_id','/facts/test_scope','/facts/test_started_at_ms','/facts/test_completed_at_ms','/facts/conclusion']}
        for name in paths:
            for key in materials[name]:
                row = objects[key]
                cites.append({'evidence_id': key, 'kind': name, 'content_sha256': raw_hash[key],
                              'registration_id': regs[key]['registration_id'], 'event_id': row['event_id'],
                              'field_paths': paths[name],
                              'admissibility_reasons': reasons[key]})
        output.append({'parent_asin':parent,'sim_batch_id':batch_id,'snapshot_id':snap['snapshot_id'],
                       'necessary_states':{'R1':r1,'R5':r5},'eligible':r1==r5=='Supported',
                       'stock_state':state,'x':x,'z':z,'C':{'numerator':complete,'denominator':1},
                       'T':ratio(t),'A':{'numerator':sum(a_checks),'denominator':2},
                       'A_checks':a_checks,'q_by_beta_T':q,'m':ratio(Fraction(x,100) if z else Fraction(0)),
                       'cites':cites,'graph_complete':bool(graph_ok)})
        if len(output)%100 == 0:
            resources()
    return output
