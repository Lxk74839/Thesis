"""S2 bounded MACRec adaptation and evidence-based ranking; no host IO or labels."""
import copy
import hashlib
import json
import math
import re

ROLES = {'interpret': '需求解析', 'thought': '推荐管理', 'action': '推荐管理',
    'reflect': '推荐依据核验', 'User': '用户画像', 'Items': '农产品画像', 'Search': '生命周期追溯'}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def reference(task, ref, observations=None):
    if not isinstance(ref, str):
        return None
    match = re.fullmatch(r'h(\d+)\.text', ref)
    if match and int(match[1]) < len(task['history']):
        row = task['history'][int(match[1])]
        return {'kind': 'history', 'parent': row['parent_asin'], 'text': row['text']}
    match = re.fullmatch(r'r:(\d+)', ref)
    if match and int(match[1]) < len(task['request'].get('preferences', [])):
        row = task['request']['preferences'][int(match[1])]
        return {'kind': 'request', 'parent': None, 'text': str(row['value'])}
    if ref.startswith('s:') and observations and ref[2:] in observations:
        parent = ref[2:]
        stock = observations[parent].get('stock', {})
        if stock.get('supported') and type(stock.get('quality')) in (int, float) and 0 <= stock['quality'] <= 1:
            return {'kind': 'stock', 'parent': parent, 'field': 'retail_stock',
                'text': str(stock['value']), 'quality': stock['quality']}
    parts = ref.split(':')
    if len(parts) == 3 and parts[0] == 'c' and parts[1] in task['D'] and parts[2] in ('title', 'crop'):
        return {'kind': 'catalog', 'parent': parts[1], 'field': parts[2],
            'text': task['catalog'][parts[1]][parts[2]]}
    return None


def preferences(task, proposed, tau, variant='I1'):
    if not isinstance(proposed, list) or len(proposed) > 6:
        raise ValueError('macrec_profile_dimensions')
    explicit = task['request'].get('preferences', [])
    result = [{'id': 'explicit-' + str(i), 'attribute': row['attribute'], 'value': row['value'],
        'weight': row.get('weight', 1), 'c': 1., 'polarity': row.get('polarity', 1),
        'n_plus': 0, 'n_minus': 0, 'supports': [{'ref': 'r:' + str(i), 'quote': str(row['value']), 'stance': 1}]}
        for i, row in enumerate(explicit)]
    rejected = []
    for pref in proposed:
        if (not isinstance(pref, dict) or not isinstance(pref.get('id'), str) or not pref['id']
                or not isinstance(pref.get('value'), str) or not pref['value']
                or not isinstance(pref.get('supports', []), list)
                or any(not isinstance(s, dict) for s in pref.get('supports', []))):
            raise ValueError('macrec_profile_shape')
        weight = pref.get('weight')
        if type(weight) not in (int, float) or not math.isfinite(weight) or weight < 0:
            raise ValueError('macrec_profile_weight')
        if pref.get('attribute') not in ('crop', 'form', 'title_term', 'retail_stock'):
            rejected.append({'id': pref.get('id'), 'reason': 'unsupported_attribute'})
            continue
        if pref['attribute'] in {row['attribute'] for row in explicit}:
            continue
        parents, accepted = {}, []
        for cite in pref.get('supports', []):
            source = reference(task, cite.get('ref'))
            quote = cite.get('quote')
            stance = cite.get('stance')
            if (not source or source['kind'] != 'history' or not isinstance(quote, str) or not quote
                    or quote not in source['text'] or stance not in (-1, 1)):
                continue
            words = set(re.findall('[a-z]+', quote.casefold()))
            value = set(re.findall('[a-z]+', pref['value'].casefold()))
            if not value - {'this', 'it', 'product', 'products', 'quality', 'good', 'great', 'excellent', 'stuff'}:
                continue
            positive = bool(words & {'prefer','prefers','preferred','love','loves','loved','lover','lovers',
                'like','likes','liked','enjoy','enjoys','enjoyed','want','wants','wanted'})
            negative = bool(words & {'hate','hates','hated','dislike','dislikes','disliked',
                'avoid','avoids','avoided','not','never','too'})
            if not value or not value <= words or positive == negative or stance != (1 if positive else -1):
                continue
            parents.setdefault(source['parent'], set()).add(stance)
            accepted.append(copy.deepcopy(cite))
        signs = [next(iter(signs)) for signs in parents.values() if len(signs) == 1]
        plus, minus = signs.count(1), signs.count(-1)
        n = plus + minus
        if not n or plus == minus:
            rejected.append({'id': pref.get('id'), 'reason': 'unknown_or_conflicting_preference'})
            continue
        result.append({k: pref[k] for k in ('id', 'attribute', 'value', 'weight')} | {
            'supports': accepted, 'n_plus': plus, 'n_minus': minus,
            'polarity': 1 if plus > minus else -1,
            'c': 1. if variant == 'A-confidence' else abs(plus - minus) / (n + tau)})
    if len({p['id'] for p in result}) != len(result):
        raise ValueError('macrec_duplicate_aspect')
    if len(result) > 6:
        raise ValueError('macrec_profile_dimensions')
    total = sum(p['weight'] for p in result)
    return ([p | {'weight': p['weight'] / total} for p in result] if total else []), rejected


def match_rows(task, prefs, rows, *, partial=False):
    if not isinstance(rows, list):
        raise ValueError('macrec_match_matrix_required')
    if any(not isinstance(r, dict) or any(not isinstance(r.get(k), str) for k in ('candidate', 'aspect'))
            or not isinstance(r.get('references', []), list)
            or any(not isinstance(ref, dict) for ref in r.get('references', []))
            or not isinstance(r.get('preference_refs', []), list)
            or any(not isinstance(ref, str) for ref in r.get('preference_refs', [])) for r in rows):
        raise ValueError('macrec_match_row_shape')
    matches = {(r['candidate'], r['aspect']): r for r in rows}
    expected = {(p, a['id']) for p in task['D'] for a in prefs}
    if len(matches) != len(rows) or not set(matches) <= expected or not partial and set(matches) != expected:
        raise ValueError('macrec_incomplete_matches')
    if any(row.get('match') not in (None, 0, .25, .5, .75, 1) or isinstance(row.get('match'), bool) for row in rows):
        raise ValueError('macrec_match_value')
    return matches


def rank_i1(task, state, policy, variant='I1'):
    if not {'User', 'Items', 'Search'} <= set(state['analyses']) or not state['observations']:
        raise ValueError('macrec_incomplete_i1_analysis')
    prefs = state['preferences']
    matches = match_rows(task, prefs, state['analyses']['Items'].get('matches'))
    components = {}
    for p in task['D']:
        b, adjustment, terms = task['prior'][p], 0., []
        for pref in prefs:
            row = matches[p, pref['id']]
            m = row.get('match')
            cited = [reference(task, ref.get('ref'), state['observations']) for ref in row.get('references', [])]
            source_kind = 'stock' if pref['attribute'] == 'retail_stock' else 'catalog'
            expected_field = 'crop' if pref['attribute'] == 'crop' else 'title'
            valid = (m is not None and bool(cited) and all(source and source['kind'] == source_kind
                and source['parent'] == p and isinstance(ref.get('quote'), str) and bool(ref['quote'])
                and (source_kind == 'stock' or source.get('field') == expected_field)
                and ref['quote'] in source['text'] for source, ref in zip(cited, row.get('references', [])))
                and bool(row.get('preference_refs')) and set(row['preference_refs']) <= {s['ref'] for s in pref['supports']})
            if valid and source_kind == 'catalog':
                visible_words = set(re.findall('[a-z]+', task['catalog'][p][expected_field].casefold()))
                desired_words = set(re.findall('[a-z]+', pref['value'].casefold()))
                if (pref['attribute'] == 'title_term' and not desired_words <= visible_words
                        or pref['attribute'] == 'form' and not visible_words &
                            {'flour', 'flakes', 'flaked', 'rolled', 'grain', 'grains', 'groats', 'kernels', 'kernel', 'puffed', 'popped', 'popcorn', 'bran'}):
                    m, valid = None, False
            if valid and variant == 'A-semantic' and source_kind == 'catalog':
                words = set(re.findall('[a-z]+', task['catalog'][p][expected_field].casefold()))
                wanted = set(re.findall('[a-z]+', pref['value'].casefold()))
                present = bool(wanted) and wanted <= words
                observable = pref['attribute'] == 'crop' or present or (
                    pref['attribute'] == 'form' and bool(words & {'flour', 'flakes', 'rolled', 'grain', 'puffed', 'bran'}))
                m = (int(present) if pref['polarity'] == 1 else int(not present)) if observable else None
                if pref['polarity'] == -1 and not present and pref['attribute'] != 'crop':
                    m = None
                valid = m is not None
            q = min(source.get('quality', 1.) for source in cited) if valid else 0.
            if valid and variant == 'A-quality':
                q = 1.
            o = int(valid)
            delta = pref['weight'] * pref['c'] * o * q * (m - b) if valid else 0.
            adjustment += delta
            terms.append({'aspect': pref['id'], 'w': pref['weight'], 'c': pref['c'],
                'm': m, 'q': q, 'o': o, 'delta': delta, 'references': row.get('references', [])})
        score = b + policy.get('lambda', .5) * adjustment
        components[p] = {'prior': b, 'score': score, 'sorting_score': round(score, 12), 'terms': terms}
    ranked = sorted(task['D'], key=lambda p: (-components[p]['sorting_score'], -task['prior'][p], p.encode()))
    return ranked, components


def run_task(task, *, method, invoke, evidence, policy):
    """Confirmed S2 seam. Models propose; the host owns scope and publication."""
    if method not in ('B0', 'I1', 'A-feedback', 'A-confidence', 'A-semantic', 'A-quality'):
        raise ValueError('macrec_unknown_method')
    improved = method != 'B0'
    d = task['D']
    visible = {'session': task['root_task_id'], 'history': task['history'],
        'history_catalog': [task['catalog'][p] for p in dict.fromkeys(h['parent_asin'] for h in task['history']) if p in task['catalog']],
        'candidates': [task['catalog'][p] | {'prior': task['prior'][p]} for p in d],
        'request': task['request'], 'protocol': 'I1' if improved else 'B0',
        'scoring': (policy | {'ablation': method if method.startswith('A-') and method != 'A-feedback' else 'full'}) if improved else None}
    state = {'analyses': {}, 'observations': {}, 'feedback': None}
    trajectory, versions = [], []
    calls = 0

    def validated(ok=True):
        observer = getattr(invoke, 'validated', None)
        if observer is not None:
            observer(ok)

    def ask(kind, context, *, agent=None):
        nonlocal calls
        if calls >= 37:
            raise ValueError('macrec_solver_exhausted')
        calls += 1
        request = {'role': ROLES[agent or kind], 'kind': kind,
            'context': copy.deepcopy(context)}
        reply = invoke(request)
        if not isinstance(reply, dict):
            raise ValueError('macrec_response_object_required')
        trajectory.append({'role': request['role'], 'kind': kind,
            'request_sha256': hashlib.sha256(encoded(request)).hexdigest(), 'output': copy.deepcopy(reply)})
        return reply

    def acquire(ids):
        if (not isinstance(ids, list) or any(not isinstance(p, str) for p in ids)
                or len(ids) != len(set(ids)) or not set(ids) <= set(d)):
            raise ValueError('macrec_evidence_scope')
        observed = evidence(ids)
        if set(observed) != set(ids) or any(row['parent_asin'] != p for p, row in observed.items()):
            raise ValueError('macrec_evidence_binding')
        state['observations'].update(copy.deepcopy(observed))
        return observed

    try:
        answer = None
        for trial in range(2):
            state['trial'] = trial
            state['interpretation'] = ask('interpret', {'allowed': visible, 'trial': trial})
            validated()
            dispatched, current = 0, None
            for step in range(4):
                context = {'allowed': visible, 'state': state, 'step': step}
                thought = ask('thought', context)
                validated()
                action = ask('action', context | {'decision': thought})
                name, data = action.get('action'), action.get('data', {})
                if not isinstance(data, dict):
                    raise ValueError('macrec_action_data_shape')
                if name == 'Finish':
                    if not improved:
                        if (not {'User', 'Items'} & set(state['analyses']) or 'Search' not in state['analyses']
                                or not state['observations']):
                            raise ValueError('macrec_incomplete_b0_collaboration')
                        ranking = data.get('ranking')
                        if (not isinstance(ranking, list) or any(not isinstance(p, str) for p in ranking)
                                or len(ranking) != len(d) or set(ranking) != set(d)):
                            raise ValueError('macrec_complete_permutation_required')
                        components = {}
                    else:
                        revisions = data.get('revisions', [])
                        changed_rows = match_rows(task, state.get('preferences', []), revisions, partial=True)
                        if revisions:
                            previous = state['analyses'].get('Items', {}).get('matches', [])
                            changed = match_rows(task, state.get('preferences', []), previous)
                            changed.update(changed_rows)
                            state['analyses']['Items']['matches'] = list(changed.values())
                        ranking, components = rank_i1(task, state, policy, method)
                    current = {'trial': trial, 'ranking': ranking, 'topK': [], 'components': components}
                    if improved:
                        current.update(preferences=copy.deepcopy(state['preferences']),
                            matches=copy.deepcopy(state['analyses']['Items']['matches']),
                            rejected_preferences=copy.deepcopy(state.get('rejected_preferences', [])))
                    validated()
                    break
                if name not in ('User', 'Items', 'Search') or dispatched >= 3:
                    raise ValueError('macrec_dispatch_exhausted_or_invalid')
                dispatched += 1
                validated()
                observation = None
                for internal in range(3):
                    reply = ask('agent', {'allowed': visible, 'state': state, 'instruction': data,
                        'observation': observation, 'internal_step': internal}, agent=name)
                    operation = reply.get('action')
                    arguments = reply.get('data', {})
                    if not isinstance(arguments, dict):
                        raise ValueError('macrec_agent_data_shape')
                    if operation == 'Finish':
                        state['analyses'][name] = arguments
                        if improved and name == 'User':
                            state['preferences'], state['rejected_preferences'] = preferences(
                                task, arguments.get('preferences'), policy.get('tau', 1), method)
                        if improved and name == 'Items':
                            match_rows(task, state.get('preferences', []), arguments.get('matches'))
                        validated()
                        break
                    if name == 'User' and operation in ('Info', 'History'):
                        observation = {'history': visible['history'], 'request': visible['request']}
                    elif name == 'Items' and operation in ('Info', 'Catalog'):
                        observation = {'candidates': visible['candidates']}
                    elif name == 'Search' and operation in ('Lookup', 'Search'):
                        observation = acquire(arguments.get('candidates', d))
                    else:
                        raise ValueError('macrec_agent_tool_denied')
                    validated()
                    trajectory.append({'role': ROLES[name], 'kind': 'observation', 'output': copy.deepcopy(observation)})
                else:
                    state['analyses'][name] = {'status': 'internal_exhausted'}
            if current is not None:
                observed = acquire(d)
                current['topK'] = [p for p in current['ranking'] if observed[p]['eligible']][:task['K']]
                versions.append(copy.deepcopy(current))
                answer = current
                state['solution'] = copy.deepcopy(current)
            if trial == 1 or method == 'A-feedback':
                break
            feedback = ask('reflect', {'allowed': visible, 'state': state, 'solution': current,
                'trajectory': trajectory})
            if not isinstance(feedback.get('revise'), bool) or not isinstance(feedback.get('issues'), list):
                raise ValueError('macrec_invalid_reflection')
            if improved and feedback['revise'] and (not feedback['issues'] or any(
                    not isinstance(issue, dict) or issue.get('candidate') not in d
                    or any(not isinstance(issue.get(k), str) or not issue[k]
                        for k in ('aspect', 'reference', 'problem')) for issue in feedback['issues'])):
                raise ValueError('macrec_unlocated_feedback')
            if improved and feedback['revise']:
                for issue in feedback['issues']:
                    source = reference(task, issue['reference'], state['observations'])
                    if (issue['aspect'] not in {'ranking', *(p['id'] for p in state.get('preferences', []))}
                            or not source or source['kind'] in ('catalog', 'stock') and source['parent'] != issue['candidate']):
                        raise ValueError('macrec_feedback_source_denied')
            state['feedback'] = feedback
            validated()
            if not feedback['revise']:
                break
        if answer is None:
            raise ValueError('macrec_solver_exhausted')
        return {'method': method, 'status': 'ok', **answer, 'versions': versions,
            'trajectory': trajectory, 'model_calls': calls, 'observations': state['observations']}
    except ValueError as exc:
        known_model_failure = str(exc).startswith('task16_failed')
        if not str(exc).startswith('macrec_') and not known_model_failure:
            raise
        validated(False)
        return {'method': method, 'status': 'failed_model' if known_model_failure or 'exhausted' in str(exc) else 'failed_protocol',
            'reason': str(exc), 'topK': [], 'ranking': [], 'versions': versions,
            'trajectory': trajectory, 'model_calls': calls, 'observations': state['observations']}
