"""Bounded public deterministic action fixtures, not a model runner or anomaly verifier."""
import copy
import json

from quality_fusion import QualityError, rank_quality
from sim_normal import digest, json_bytes

VERSION='collaboration-action-contract-0.1.0'
RESOURCES=('model_calls','input_tokens','output_tokens','logical_tools','physical_tools',
           'candidates','elapsed_ms','cost_microusd','retries')
ROLES=('需求解析','推荐管理','用户画像','农产品画像','生命周期追溯','推荐依据核验')
SLOTS=('R1.inspection_sample','R1.inspection_report','R5.retail_status',
       'stock.transport_dispatch','stock.transport_receipt')


class ActionError(ValueError):
    """Illegal action/state binding; caller retains its unchanged previous state."""


def require(condition,code):
    if not condition:
        raise ActionError(code)


def _state_hash(state):
    return digest(json.dumps({k:v for k,v in state.items() if k!='state_sha256'},sort_keys=True,
        ensure_ascii=False,separators=(',',':'),allow_nan=False,default=lambda raw:{'bytes_hex':raw.hex()}).encode())


def _sealed(state):
    state['state_sha256']=_state_hash(state)
    return state


def _charge(state,event,cost,final=False,reserve=False):
    budget=state['budget'];before=copy.deepcopy(budget)
    cost={k:cost.get(k,0) for k in RESOURCES}
    cost['elapsed_ms']=event['at_ms']-state['at_ms']
    allowed=all(cost[k]+(0 if final else budget['final_reserve'][k])<=budget['remaining'][k]
                for k in RESOURCES if not (k=='elapsed_ms' and final and state['terminal'] in ('incomplete_budget','incomplete_deadline')))
    late=event['at_ms']>state['deadline_ms'] and not final
    if late:
        allowed=False
        state['terminal']='incomplete_deadline'
    elif not allowed:
        state['terminal']='incomplete_budget'
    for key in RESOURCES:
        if allowed or key=='elapsed_ms':
            budget['reserved' if reserve and key!='elapsed_ms' else 'used'][key]+=cost[key]
            budget['remaining'][key]=max(0,budget['limits'][key]-budget['used'][key]-budget['reserved'][key])
    budget['overrun']={k:max(0,budget['used'][k]+budget['reserved'][k]-budget['limits'][k]) for k in RESOURCES}
    state['at_ms']=event['at_ms']
    state['receipts'].append({'operation':event['kind'],'fixture':state['fixture'],
        'status':('reserved' if reserve else 'executed') if allowed else ('rejected_deadline' if late else 'rejected_budget'),'at_ms':event['at_ms'],
        'usage':cost if allowed else {**dict.fromkeys(RESOURCES,0),'elapsed_ms':cost['elapsed_ms']},'budget_before':before,'budget_after':copy.deepcopy(budget)})
    return allowed


def _draft_issues(state):
    draft=state['drafts'][-1]['content']
    result=rank_quality(state['binding'],state['acquired'])
    rows={r['parent_asin']:r for r in result['candidates']}
    issues=[]
    for index,item in enumerate(draft['items']):
        parent=item['parent_asin'];row=rows[parent]
        raw=state['acquired']['candidates'].get(parent,{}).get('originals',{}).get(item['stock_citation'])
        original=json.loads(raw) if raw else None
        code='necessary_unassessed' if not row['eligible'] else (
            'wrong_attribute_citation' if original is None or original.get('kind')!='retail_status' else
            'wrong_stock_value' if item['stock_value']!=row['x'] else None)
        if code:
            issues.append({'issue_id':draft['draft_id']+':'+str(index)+':'+code,'draft_id':draft['draft_id'],
                'candidate_id':parent,'claim_id':'stock','attribute_id':'retail_stock',
                'pointer':'/items/'+str(index)+('/stock_value' if code=='wrong_stock_value' else '/stock_citation'),
                'code':code,'blocking':True,'locator':item['stock_citation'],
                'allowed_actions':['revise_and_resubmit'],'verifier':'推荐依据核验'})
    return issues


def advance_action(state,event):
    """Return a new state, never mutate the caller's binding, evidence or budget."""
    if state is None:
        require(event['kind']=='init' and event['fixture']=='public_deterministic_adapter', 'fixture_only')
        require(event['mode'] in ('full','no_feedback','fixed'), 'invalid_mode')
        try:
            rank_quality(event['binding'],event['acquired'])
        except QualityError as exc:
            raise ActionError(str(exc)) from None
        limits=event['limits']
        require(set(limits)==set(RESOURCES) and all(type(v) is int and v>=0 for v in limits.values()), 'invalid_limits')
        require(all(limits[k]==0 for k in ('model_calls','input_tokens','output_tokens','cost_microusd')), 'models_not_authorized')
        reserve={k:event['final_reserve'].get(k,0) for k in RESOURCES}
        require(all(type(v) is int and 0<=v<=limits[k] for k,v in reserve.items())
                and reserve['logical_tools']>=1, 'invalid_final_reserve')
        for parent,slots in event['slots'].items():
            require(parent in event['binding']['C'] and set(slots)==set(SLOTS), 'invalid_slot_scope')
            ids=[key for values in slots.values() for key in values]
            regs={r['target_id'] for r in event['acquired']['candidates'][parent]['registrations'] if r['target_kind']=='material'}
            require(len(ids)==len(set(ids)) and set(ids)<=regs, 'invalid_slot_scope')
        initialized={'version':VERSION,'fixture':event['fixture'],'binding':copy.deepcopy(event['binding']),
                'binding_sha256':digest(json_bytes(event['binding'])),'acquired':copy.deepcopy(event['acquired']),
                'mode':event['mode'],'cursor':0,'processed':[],'drafts':[],'issues':[],
                'slots':copy.deepcopy(event['slots']),'visited':[],
                'queue':[p for p,b in sorted(zip(event['binding']['C'],event['binding']['base_scores']),key=lambda pair:(-pair[1],pair[0].encode()))],
                'G':[],
                'visible_issues':[],'revisions':[],'receipts':[],'feedback_round':0,'pending':None,
                'terminal':None,'delivered':[],'phase':'initial','deadline_ms':event['deadline_ms'],'at_ms':event['at_ms'],
                'budget':{'limits':copy.deepcopy(limits),'used':dict.fromkeys(RESOURCES,0),
                          'reserved':dict.fromkeys(RESOURCES,0),'remaining':copy.deepcopy(limits),'final_reserve':reserve}}
        packs=event['acquired']['candidates']
        bootstrap={'logical_tools':3+sum(len(p['registrations'])+len(p['originals']) for p in packs.values()),
                   'physical_tools':3+len(packs),'candidates':len(packs)}
        # Each supplied fixture capsule is an explicit batch request; every returned registry/original counts.
        _charge(initialized,{**event,'kind':'fixture_bootstrap'},bootstrap)
        initialized['visited']=list(packs)
        return _sealed(initialized)
    require(state['state_sha256']==_state_hash(state), 'changed_protocol_state')
    stopping=state['terminal'] in ('incomplete_budget','incomplete_deadline')
    require((state['terminal'] is None or stopping and event['kind']=='finalize' and 'release_check' not in state)
            and state['binding_sha256']==digest(json_bytes(state['binding'])), 'closed_or_changed_task')
    require(event['task_id']==state['binding']['task_id'] and event['snapshot_id']==state['binding']['snapshot_id'], 'event_binding_mismatch')
    require(event['role'] in ROLES and type(event['at_ms']) is int and event['at_ms']>=state['at_ms'], 'invalid_actor_or_time')
    require(state['pending'] is None or event['kind']=='settle', 'pending_action_must_settle')
    next_state=copy.deepcopy(state)
    kind=event['kind']
    if kind=='assess_current':
        require(event['role']=='推荐依据核验' and state['phase']=='initial' and state['pending'] is None, 'invalid_phase')
        require(state['cursor']<len(state['queue']) and event['parent_asin']==state['queue'][state['cursor']], 'outside_current_candidate')
        if _charge(next_state,event,{'logical_tools':1}):
            result=rank_quality(state['binding'],state['acquired'])
            parent=event['parent_asin']
            if parent in result['G']:
                next_state['processed'].append(parent)
                if parent not in next_state['G']:next_state['G'].append(parent)
                next_state['cursor']+=1
            else:
                next_state['receipts'][-1]['status']='unassessed_no_advance'
    elif kind=='acquire':
        require(event['role']=='生命周期追溯' and state['pending'] is None
                and state['phase'] in ('initial','feedback'), 'invalid_phase')
        parent=event['parent_asin']
        require(state['cursor']<len(state['queue']) and parent==state['queue'][state['cursor']], 'outside_current_candidate')
        originals=state['acquired']['candidates'][parent]['originals']
        slots=state['slots'][parent]
        missing=[s for s in SLOTS if slots[s] and any(k not in originals for k in slots[s])]
        require(event['slot'] in missing, 'slot_already_acquired_or_illegal')
        executed=missing[0] if state['mode']=='fixed' else event['slot']
        targets=[k for k in slots[executed] if k not in originals]
        require(all(r.get('action_id')!=event['action_id'] for r in state['receipts']), 'duplicate_action')
        retry=event.get('retry_of')
        if retry:
            require(any(r.get('action_id')==retry and r['status']=='failed' and r['executed_slot']==executed for r in state['receipts']), 'invalid_retry')
        cost={'logical_tools':len(targets),'physical_tools':1,'candidates':int(parent not in state['visited']),'retries':int(bool(retry))}
        if _charge(next_state,event,cost,reserve=True):
            next_state['pending']={'action_id':event['action_id'],'parent_asin':parent,'requested_slot':event['slot'],
                'executed_slot':executed,'target_ids':targets,'cost':cost,'snapshot_id':event['snapshot_id']}
    elif kind=='settle':
        pending=state['pending']
        require(event['role']=='生命周期追溯' and pending is not None and event['action_id']==pending['action_id'], 'invalid_receipt_binding')
        require(type(event['success']) is bool and (set(event['originals'])==set(pending['target_ids']) if event['success'] else not event['originals']), 'invalid_receipt_objects')
        on_time=_charge(next_state,event,{})
        if pending is not None:
            for key,value in pending['cost'].items():
                next_state['budget']['reserved'][key]-=value
                next_state['budget']['used'][key]+=value
            if pending['parent_asin'] not in next_state['visited']:
                next_state['visited'].append(pending['parent_asin'])
            success=event['success'] and on_time
            if success:
                try:
                    for raw in event['originals'].values():
                        require(json.loads(raw)['kind']==pending['executed_slot'].split('.')[1], 'wrong_slot_original')
                    next_state['acquired']['candidates'][pending['parent_asin']]['originals'].update(event['originals'])
                    rank_quality(state['binding'],next_state['acquired'])
                except (QualityError,ActionError,ValueError,KeyError,TypeError):
                    next_state['acquired']=copy.deepcopy(state['acquired'])
                    next_state['terminal']='failed_protocol'
                    success=False
            next_state['pending']=None
            next_state['receipts'][-1].update(status='executed' if success else 'failed',action_id=pending['action_id'],
                requested_slot=pending['requested_slot'],executed_slot=pending['executed_slot'],
                target_sha256={k:digest(v) for k,v in event['originals'].items()},
                usage={k:pending['cost'].get(k,0) for k in RESOURCES},budget_after=copy.deepcopy(next_state['budget']))
    elif kind=='submit_draft':
        require(event['role']=='推荐管理' and next_state['phase']=='initial', 'invalid_phase')
        draft=event['draft']
        require(set(draft)=={'draft_id','parent_draft_id','items'} and draft['parent_draft_id'] is None, 'invalid_draft')
        allowed=state['queue'][:state['cursor']+1]
        require(len({i['parent_asin'] for i in draft['items']})==len(draft['items'])
                and all(i['parent_asin'] in allowed and set(i)=={'parent_asin','stock_value','stock_citation','reason'} for i in draft['items']), 'outside_processed_prefix')
        if _charge(next_state,event,{'logical_tools':1}):
            next_state['drafts'].append({'content':copy.deepcopy(draft),'snapshot_id':state['binding']['snapshot_id'],
                'score_version':'fusion-score-0.1.0','budget':copy.deepcopy(next_state['budget'])})
            next_state['phase']='draft'
    elif kind=='verify_draft':
        require(event['role']=='推荐依据核验' and state['phase']=='draft', 'invalid_phase')
        if _charge(next_state,event,{'logical_tools':1}):
            issues=_draft_issues(next_state)
            next_state['issues'].extend(issues)
            next_state['visible_issues']=issues if state['mode']!='no_feedback' else []
            eligible=rank_quality(state['binding'],state['acquired'])['G']
            for item in state['drafts'][-1]['content']['items']:
                if item['parent_asin'] in eligible and item['parent_asin'] not in next_state['G']:
                    next_state['G'].append(item['parent_asin'])
            next_state['phase']='feedback' if issues and state['mode']!='no_feedback' else 'final'
    elif kind=='revise_and_resubmit':
        require(event['role']=='推荐管理' and state['phase']=='feedback' and state['mode']!='no_feedback'
                and state['feedback_round']==0, 'feedback_disabled_or_exhausted')
        issue=next((i for i in state['visible_issues'] if i['issue_id']==event['issue_id']),None)
        require(issue is not None and issue['pointer']==event['pointer'], 'invalid_issue_binding')
        draft=copy.deepcopy(state['drafts'][-1]['content'])
        _,_,index,key=event['pointer'].split('/')
        require(key in ('stock_citation','stock_value'), 'illegal_patch')
        old=draft['items'][int(index)][key]
        require(old!=event['value'] and event['draft_id']!=draft['draft_id'], 'no_revision')
        if _charge(next_state,event,{'logical_tools':1}):
            draft.update(parent_draft_id=draft['draft_id'],draft_id=event['draft_id'])
            draft['items'][int(index)][key]=event['value']
            next_state['drafts'].append({'content':draft,'snapshot_id':state['binding']['snapshot_id'],
                'score_version':'fusion-score-0.1.0','budget':copy.deepcopy(next_state['budget'])})
            next_state['revisions'].append({'issue_id':issue['issue_id'],'pointer':event['pointer'],
                'old':old,'new':event['value'],'parent_draft_id':draft['parent_draft_id'],'draft_id':draft['draft_id']})
            next_state['feedback_round']=1
            next_state['phase']='draft'
    elif kind=='finalize':
        require(event['role']=='推荐管理' and (state['phase']=='final' or stopping), 'invalid_phase')
        if _charge(next_state,event,{'logical_tools':1},final=True):
            issues=_draft_issues(next_state) if state['drafts'] else [{'code':'no_verified_draft'}]
            delivered=[i['parent_asin'] for i in state['drafts'][-1]['content']['items']] if state['drafts'] else []
            result=rank_quality(state['binding'],state['acquired'])
            next_state['release_check']={'issues':issues,'G':state['G'],'fixture':state['fixture']}
            ordered=[p for p in result['order'] if p in state['G']][:state['binding']['K']]
            if stopping:
                next_state['terminal']=state['terminal']
            elif issues or len(delivered)>state['binding']['K'] or delivered!=ordered:
                next_state['terminal']='blocked_evidence'
            elif not delivered:
                # This normal-v1 arm has no negative necessary state; only a complete empty C is valid empty.
                next_state['terminal']='valid_empty' if not state['binding']['C'] else 'blocked_evidence'
            else:
                next_state['terminal']='released'
            next_state['delivered']=delivered if next_state['terminal']=='released' else []
    else:
        raise ActionError('unsupported_event')
    return _sealed(next_state)
