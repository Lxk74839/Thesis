"""Pure evidence assessment; inputs are host-acquired facts, never reference answers."""
import hashlib
import json

STAGES = ('harvest', 'packaging', 'storage', 'inspection', 'transport', 'retail')
MATERIAL_STAGE = {'harvest_record': 'harvest', 'packaging_binding': 'packaging', 'storage_log': 'storage',
    'inspection_sample': 'inspection', 'inspection_report': 'inspection',
    'transport_dispatch': 'transport', 'transport_receipt': 'transport', 'retail_status': 'retail'}


def integer(value):
    return type(value) is int and value >= 0


def _unassessed():
    return {'assessment_status': 'unassessed', 'evidence_state': None,
            'eligible': False, 'advance_allowed': False,
            'completion': {'enumeration_complete': False, 'required_reads_complete': False,
                           'version_checks_complete': False, 'attempts_settled': False},
            'claims': {}, 'accepted': [], 'rejected': []}


def _reason(row, reg, policy, binding, raw, snapshot):
    if hashlib.sha256(raw).hexdigest() != reg['content_sha256']:
        return 'digest_mismatch'
    if (reg['source'] != 'SIM' or reg['receipt_status'] != 'accepted'
            or reg['registrar_id'] != policy['registrar_id'] or reg['registry_backend'] != 'local_sim_registry'):
        return 'invalid_registration'
    if not (integer(reg['sequence']) and 1 <= reg['sequence'] <= snapshot['cutoff_sequence']
            and integer(reg['registered_at_ms']) and reg['registered_at_ms'] <= snapshot['sealed_at_ms'] <= binding['verify_at_ms']):
        return 'invalid_registration_time'
    kind = reg['target_kind']
    if kind not in policy['read_scope']['target_kinds'] and kind != 'change_action':
        return 'read_denied'
    if any(r['principal_id'] == binding['principal_id'] and r['target_kind'] == kind
           and r['target_id'] == reg['target_id'] and r['version'] == reg['version'] for r in policy.get('read_denials', [])):
        return 'read_denied'
    identity = {'batch': 'sim_batch_id', 'event': 'event_id', 'material': 'evidence_id', 'change_action': 'action_id'}[kind]
    version = row.get('version', 1) if kind == 'change_action' else row['version']
    schema = 'sim-change-action-1.0.0' if kind == 'change_action' else 'sim-' + kind + '-1.0.0'
    if (row['schema_version'] != schema or row['source'] != 'SIM' or row[identity] != reg['target_id'] or type(version) is not int
            or version != reg['version'] or version < 1
            or row['parent_asin'] != reg['parent_asin'] or row['parent_asin'] != binding['parent_asin']
            or row['sim_batch_id'] != reg['sim_batch_id'] or row['sim_batch_id'] != binding['sim_batch_id']
            or row.get('event_id') != reg['event_id']):
        return 'object_mismatch'
    issuer = row.get('issuer_id', row.get('actor_id'))
    authority = next((a for a in policy['issuers'] if a['issuer_id'] == issuer), {})
    if issuer != reg['issuer_id']:
        return 'issuer_mismatch'
    if kind == 'batch':
        if not authority.get('may_create_batch') or not integer(row['created_at_ms']) or row['created_at_ms'] > reg['registered_at_ms']:
            return 'invalid_batch'
    elif kind == 'event':
        if (row['stage'] not in authority.get('event_stages', []) or not integer(row['event_start_ms'])
                or not integer(row['event_end_ms']) or not row['event_start_ms'] <= row['event_end_ms'] <= reg['registered_at_ms']):
            return 'invalid_event'
    elif kind == 'material':
        if row['kind'] not in policy['read_scope']['material_kinds']:
            return 'read_denied'
        if row['kind'] not in authority.get('material_kinds', []):
            return 'unauthorized_issuer'
        if not integer(row['issued_at_ms']) or row['issued_at_ms'] > reg['registered_at_ms']:
            return 'invalid_issue_time'
        if row['kind'] == 'retail_status':
            if (row['temporal_mode'] != 'current_assertion' or not integer(row.get('valid_from_ms'))
                    or not integer(row.get('valid_to_ms')) or not row['valid_from_ms'] <= binding['verify_at_ms'] < row['valid_to_ms']):
                return 'current_interval_not_applicable'
        elif row['temporal_mode'] != 'historical_fact':
            return 'invalid_temporal_mode'
    elif kind == 'change_action':
        if (type(row['target_version']) is not int or row['target_version'] < 1
                or row['action_type'] not in ('revokes', 'supersedes') or row['target_kind'] != 'material'
                or (row['action_type'] == 'revokes' and row['supersedes_version'] is not None)
                or (row['action_type'] == 'supersedes' and
                    (type(row['supersedes_version']) is not int or row['supersedes_version'] < 1))):
            return 'invalid_action'
        if (not integer(row['issued_at_ms']) or not integer(row['effective_from_ms'])
                or row['issued_at_ms'] > reg['registered_at_ms'] or row['issued_at_ms'] > row['effective_from_ms']):
            return 'invalid_action_time'
    return None


def _versioned(objects, pack, policy, binding, snapshot):
    regs = {}
    ambiguous = set()
    for item in pack['registrations']:
        reg = item['record']
        if reg['target_kind'] != 'material':
            continue
        key = (reg['target_id'], reg['version'])
        if key in regs:
            ambiguous.add(reg['target_id'])
        if (type(reg['version']) is int and reg['version'] > 0 and reg['receipt_status'] == 'accepted'
                and reg['issuer_id'] in {row['issuer_id'] for row in policy['issuers']}
                and reg['registrar_id'] == policy['registrar_id'] and integer(reg['sequence'])
                and reg['sequence'] <= snapshot['cutoff_sequence'] and integer(reg['registered_at_ms'])
                and reg['registered_at_ms'] <= snapshot['sealed_at_ms']):
            regs[key] = reg
    actions = [row for row in objects if row['schema_version'] == 'sim-change-action-1.0.0']
    legal = []
    for action in actions:
        target = regs.get((action['target_id'], action['target_version']))
        if (target and action['target_kind'] == 'material' and action['issuer_id'] == target['issuer_id']
                and action['event_id'] == target['event_id'] and action['effective_from_ms'] <= binding['verify_at_ms']
                and policy['status_change_authority'] == 'issuer_own_lineage_only'):
            legal.append(action)
    heads = {identity: 1 for identity, version in regs if version == 1 and identity not in ambiguous}
    applied = []
    for action in sorted(legal, key=lambda row: row['target_version']):
        identity = action['target_id']
        old = regs.get((identity, action.get('supersedes_version')))
        new = regs.get((identity, action['target_version']))
        if (action['action_type'] == 'supersedes' and old and new and type(action['target_version']) is int
                and action['target_version'] == action.get('supersedes_version', -1) + 1
                and heads.get(identity) == action['supersedes_version'] and old['issuer_id'] == new['issuer_id']
                and old['event_id'] == new['event_id'] and old['registered_at_ms'] <= new['registered_at_ms']):
            heads[identity] = action['target_version']
            applied.append(action)
    revoked = {(action['target_id'], action['target_version']) for action in legal
               if action['action_type'] == 'revokes' and action['supersedes_version'] is None}
    applied += [action for action in legal if action['action_type'] == 'revokes' and action['supersedes_version'] is None]
    unresolved_events = {item['record']['event_id'] for item in pack['registrations']
        if item['record']['target_kind'] == 'change_action' and item['evidence_ref'] not in pack['originals']}
    return [row for row in objects if (row['schema_version'] not in ('sim-material-1.0.0', 'sim-change-action-1.0.0'))
            or row in applied or (row['schema_version'] == 'sim-material-1.0.0' and
            (heads.get(row['evidence_id']) == row['version'] and (row['evidence_id'], row['version']) not in revoked
             and row['event_id'] not in unresolved_events))]


def _path(material, objects, binding):
    events = {row['event_id']: row for row in objects if row['schema_version'] == 'sim-event-1.0.0'}
    batch = next((row for row in objects if row['schema_version'] == 'sim-batch-1.0.0'
                  and row['sim_batch_id'] == binding['sim_batch_id']), None)
    event = events.get(material['event_id'])
    if event is None or event['stage'] != MATERIAL_STAGE.get(material['kind']) or material['issued_at_ms'] < event['event_start_ms']:
        return False
    while event:
        position = STAGES.index(event['stage'])
        if position == 0:
            return bool(batch and not event['predecessor_event_ids'] and batch['created_at_ms'] <= event['event_start_ms'])
        predecessors = event['predecessor_event_ids']
        previous = events.get(predecessors[0]) if len(predecessors) == 1 else None
        if previous is None or previous['stage'] != STAGES[position - 1] or previous['event_end_ms'] > event['event_start_ms']:
            return False
        event = previous
    return False


def _inspection_pair(sample, report, event):
    try:
        left, right = sample['facts'], report['facts']
        times = (left['sampled_at_ms'], right['test_started_at_ms'], right['test_completed_at_ms'])
        return (event is not None and all(integer(value) for value in times)
            and left['sample_id'] == right['sample_id'] and sample['event_id'] == report['event_id']
            and event['event_start_ms'] <= times[0] <= times[1] <= times[2] <= event['event_end_ms']
            and times[0] <= sample['issued_at_ms'] and times[2] <= report['issued_at_ms']
            and isinstance(right['test_scope'], list) and 'SIM-Q1' in right['test_scope'])
    except (KeyError, TypeError):
        return False


def _completion(claim, pack, objects, policy, context):
    kinds = {'inspection_sample', 'inspection_report'} if claim == 'c1' else {'retail_status'}
    anchor = 'inspection' if claim == 'c1' else 'retail'
    stages = set(STAGES[:STAGES.index(anchor) + 1])
    authorities = {row['issuer_id']: row for row in policy['issuers']}
    event_stages = {row['event_id']: row['stage'] for row in objects if row['schema_version'] == 'sim-event-1.0.0'}
    anchor_ids = {event for event, stage in event_stages.items() if stage == anchor}
    for item in pack['registrations']:
        reg = item['record']
        if reg['target_kind'] == 'event' and anchor in authorities.get(reg['issuer_id'], {}).get('event_stages', []):
            anchor_ids.add(reg['target_id'])
    required = []
    actions = []
    for item in pack['registrations']:
        reg = item['record']
        authority = authorities.get(reg['issuer_id'], {})
        kind = reg['target_kind']
        if kind == 'batch':
            needed = True
        elif kind == 'event':
            possible = {event_stages[reg['target_id']]} if reg['target_id'] in event_stages else set(authority.get('event_stages', []))
            needed = not possible or bool(possible & stages)
        elif kind == 'material':
            needed = reg['event_id'] in anchor_ids or bool(set(authority.get('material_kinds', [])) & kinds)
        else:
            needed = reg['event_id'] in anchor_ids
            if needed:
                actions.append(item['evidence_ref'])
        if needed:
            required.append(item['evidence_ref'])
    return {'enumeration_complete': pack['enumeration_complete'],
        'required_reads_complete': all(ref in pack['originals'] for ref in required),
        'version_checks_complete': 'actions_scope' in context and all(ref in pack['originals'] for ref in actions),
        'attempts_settled': all(pack['attempts'].get(ref, {}).get('status') in ('ok', 'unavailable', 'access_denied') for ref in required)}


def assess_evidence(binding, acquired):
    result = _unassessed()
    if not binding['necessary_clauses'] or any(c not in ('c1', 'c2') for c in binding['necessary_clauses']):
        raise ValueError('unsupported_request')
    if any(acquired['binding'][key] != binding[key] for key in
           ('run_id', 'root_task_id', 'snapshot_id', 'principal_id', 'verify_at_ms')):
        raise ValueError('acquired_binding_mismatch')
    pack = acquired['candidates'].get(binding['parent_asin'])
    if not pack or not pack['attempts']:
        return result
    context = acquired['context']
    policy = json.loads(context['policy']['raw_utf8'])
    snapshot = json.loads(context['snapshot']['raw_utf8'])
    if (snapshot['snapshot_id'] != binding['snapshot_id'] or snapshot['verify_at_ms'] != binding['verify_at_ms']
            or policy['read_principal_id'] != binding['principal_id'] or snapshot['policy_id'] != policy['policy_id']):
        raise ValueError('context_binding_mismatch')
    objects = []
    for item in pack['registrations']:
        ref = item['evidence_ref']
        if ref not in pack['originals']:
            attempt = pack['attempts'].get(ref, {})
            result['rejected'].append({'target_id': item['record']['target_id'], 'version': item['record']['version'],
                'evidence_ref': ref, 'receipt_id': attempt.get('receipt_id', item['receipt_id']),
                'source': attempt.get('source', item['source']), 'pointer': '/',
                'reason': attempt.get('status', 'unacquired')})
    for item in pack['originals'].values():
        raw = item['raw_utf8'].encode('utf-8')
        reg = item['registration']
        try:
            row = json.loads(raw)
            reason = _reason(row, reg, policy, binding, raw, snapshot)
        except (ValueError, KeyError, TypeError):
            reason = 'invalid_original'
        citation = {'target_id': reg['target_id'], 'version': reg['version'], 'evidence_ref': item['evidence_ref'],
            'receipt_id': item['receipt_id'], 'source': item['source'], 'pointer': '/facts' if reg['target_kind'] == 'material' else '/'}
        if reason:
            result['rejected'].append({**citation, 'reason': reason})
        else:
            objects.append(row)
            result['accepted'].append(citation)
    effective = _versioned(objects, pack, policy, binding, snapshot)
    removed = {(row['evidence_id'], row['version']) for row in objects
               if row['schema_version'] == 'sim-material-1.0.0' and row not in effective}
    inactive_actions = {(row['action_id'], 1) for row in objects
                        if row['schema_version'] == 'sim-change-action-1.0.0' and row not in effective}
    for citation in result['accepted'][:]:
        if (citation['target_id'], citation['version']) in removed | inactive_actions:
            result['accepted'].remove(citation)
            result['rejected'].append({**citation, 'reason': 'inactive_or_invalid_action'
                if (citation['target_id'], citation['version']) in inactive_actions else 'inactive_or_unresolved_version'})
    materials = [row for row in effective if row['schema_version'] == 'sim-material-1.0.0' and _path(row, effective, binding)]
    samples = [row for row in materials if row['kind'] == 'inspection_sample']
    reports = [row for row in materials if row['kind'] == 'inspection_report']
    retail = [row for row in materials if row['kind'] == 'retail_status']
    events = {row['event_id']: row for row in objects if row['schema_version'] == 'sim-event-1.0.0'}
    matching_reports = [r for s in samples for r in reports
                        if _inspection_pair(s, r, events.get(r['event_id']))]
    support = {'c1': any(r['facts']['conclusion'] == 'pass' for r in matching_reports),
        'c2': any(row['facts']['status'] == 'on_sale' and row['valid_from_ms'] <= row['facts']['observed_at_ms']
                  < row['valid_to_ms'] and row['facts']['observed_at_ms'] <= row['issued_at_ms'] for row in retail)}
    refute = {'c1': any(r['facts']['conclusion'] == 'fail' for r in matching_reports), 'c2': False}
    for claim in binding['necessary_clauses']:
        completion = _completion(claim, pack, objects, policy, context)
        complete = all(completion.values())
        state = 'Conflict' if support[claim] and refute[claim] else 'Refuted' if refute[claim] else 'Supported' if support[claim] and complete else 'Pending'
        result['claims'][claim] = {'evidence_state': state, 's': int(support[claim]), 'r': int(refute[claim]), 'completion': completion.copy()}
    completion = {key: all(c['completion'][key] for c in result['claims'].values()) for key in completion}
    states = [c['evidence_state'] for c in result['claims'].values()]
    state = 'Conflict' if 'Conflict' in states else 'Refuted' if 'Refuted' in states else 'Supported' if all(c == 'Supported' for c in states) else 'Pending'
    result.update(assessment_status='assessed', evidence_state=state, eligible=state == 'Supported' and not acquired.get('halted'),
                  advance_allowed=completion['enumeration_complete'] and completion['attempts_settled']
                                  and not acquired.get('halted'), completion=completion)
    return result


def rank_acquired_quality(binding, acquired):
    """Convert only acquired normal-v1 facts; freeze qualification independently of prefetch."""
    from quality_fusion import rank_quality
    scope = acquired['binding']
    if (binding['task_id'] != scope['root_task_id'] or binding['snapshot_id'] != scope['snapshot_id']
            or binding['principal_id'] != scope['principal_id'] or binding['verify_at_ms'] != scope['verify_at_ms']
            or binding['C'] != acquired['candidate_binding']['C']
            or binding['base_scores'] != acquired['candidate_binding']['base_scores']):
        raise ValueError('quality_binding_mismatch')
    context = acquired['context']
    actions = context.get('actions_scope', {})
    if actions.get('raw_utf8') != '':
        raise ValueError('unsupported_quality_scope')
    scoring = {'snapshot': json.loads(context['snapshot']['raw_utf8']),
        'policy_bytes': context['policy']['raw_utf8'].encode('utf-8'),
        'actions_bytes': actions['raw_utf8'].encode('utf-8'), 'candidates': {}}
    for parent, pack in acquired['candidates'].items():
        if not pack['enumeration_complete']:
            continue
        scoring['candidates'][parent] = {'registrations': [row['record'] for row in pack['registrations']],
            'originals': {row['registration']['target_id']: row['raw_utf8'].encode('utf-8') for row in pack['originals'].values()}}
    result = rank_quality(binding, scoring)
    actual = {parent for parent, assessment in acquired.get('assessments', {}).items()
              if assessment['eligible'] and assessment['evidence_state'] == 'Supported' and assessment['advance_allowed']}
    if not actual <= set(result['G']):
        raise ValueError('quality_qualification_mismatch')
    result['raw_eligible'] = result['G']
    result['G'] = [parent for parent in binding['C'] if parent in actual]
    result['order'] = [parent for parent in result['order'] if parent in actual]
    result['topK'] = result['order'][:binding['K']]
    result['root_halted'] = acquired.get('halted')
    return result
