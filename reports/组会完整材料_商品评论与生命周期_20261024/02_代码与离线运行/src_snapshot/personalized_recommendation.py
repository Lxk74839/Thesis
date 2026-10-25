"""Source-grounded preferences and deterministic ranking; no labels or host IO."""
import math
import re
import unicodedata

VERSION = 'personalized-recommendation-0.1.0'
ROLES = ('需求解析', '用户画像', '农产品画像', '生命周期追溯', '推荐管理', '推荐依据核验')
ROLE_TASK = {
    '单智能体': 'Infer, check observability and consolidate tentative preferences in one pass.',
    '需求解析': 'Identify aspects explicitly liked in history; do not invent a current request.',
    '用户画像': 'Select and weight the supported tentative preferences; distinguish praise from complaints.',
    '农产品画像': 'Check the selected attributes against the available catalog fields and coverage.',
    '生命周期追溯': 'Remove preference interpretations that require unavailable batch facts; leave lifecycle verification to host tools.',
    '推荐管理': 'Consolidate the prior checked selections into the profile used for scoring.',
    '推荐依据核验': 'Verify every interpretation against history; correct unsupported selections and describe corrections.'}
FORMS = (('flour', r'\bflour\b'), ('flakes', r'\b(?:flakes|rolled|flaked)\b'),
         ('puffed', r'\b(?:puffed|popped|popcorn)\b'), ('bran', r'\bbran\b'),
         ('grain', r'\b(?:grain|grains|kernel|kernels|groats)\b'))
STOP = set('the and for with from of in to by pack bags bag ounce ounces oz pound pounds lb lbs '
           'gram grams kg g count food foods natural organic certified certification gluten free non gmo '
           'rice oats oat wheat corn millet barley grain grains flour flakes rolled whole kernel kernels '
           'brand premium product products quality kosher vegan healthy fresh'.split())


def product_attributes(product):
    title = unicodedata.normalize('NFKC', product['title']).casefold()
    form = next((value for value, pattern in FORMS if re.search(pattern, title)), None)
    return {'crop': product['crop'], 'form': form, 'title': title}


def profile_options(history, catalog):
    products = {p['parent_asin']: p for p in catalog}
    options = []
    for i, h in enumerate(history):
        product = products[h['parent_asin']]
        attributes = product_attributes(product)
        for dimension in ('crop', 'form'):
            if attributes[dimension] is not None:
                options.append({'option_id': 'h%d:%s' % (i, dimension), 'dimension': dimension,
                    'value': attributes[dimension], 'source': {'history_index': i,
                        'parent_asin': h['parent_asin'], 'field': 'crop' if dimension == 'crop' else 'title'}})
        terms = sorted(set(re.findall(r'\b[a-z]{3,24}\b', attributes['title'])) - STOP)[:24]
        options.extend({'option_id': 'h%d:term:%s' % (i, term), 'dimension': 'title_term', 'value': term,
            'source': {'history_index': i, 'parent_asin': h['parent_asin'], 'field': 'title'}} for term in terms)
    return options


def analyze_profile(history, catalog, *, method, invoke=None):
    """Prepare a reusable history-only profile; material facts remain host-owned."""
    options = profile_options(history, catalog)
    if method == 'R':
        profile = {'selections': [{'option_id': o['option_id'], 'weight': 1} for o in options]}
        return {'profile': profile, 'before_feedback': profile, 'stages': []}
    if method not in ('S', 'M') or invoke is None:
        raise ValueError('profile_model_required')
    products = {p['parent_asin']: p for p in catalog}
    context = {'history': [{'history_index': i, 'parent_asin': h['parent_asin'],
        'text': h.get('text', h.get('review_text', ''))[:2000], 'rating': h.get('rating'),
        'title': products[h['parent_asin']]['title']} for i, h in enumerate(history)],
        'options': options,
        'attribute_coverage': {d: sum(product_attributes(p)[d] is not None for p in catalog)
                               for d in ('crop', 'form')}, 'catalog_count': len(catalog)}
    stages, current, before = [], {'selections': []}, None
    for role in ROLES if method == 'M' else ('单智能体',):
        result = invoke({'role': role, 'context': context, 'previous': current, 'role_task': ROLE_TASK[role],
            'instruction': 'Select only option_id values from options, with weights in (0,1]. '
                'Infer tentative preferences only from earlier positive history. Empty selections mean unknown. '
                'Use text to distinguish liked aspects from incidental words; title occurrence alone is not an explicit preference. '
                'Do not infer batch quality, origin or certification. Lifecycle evidence is verified by host tools; '
                'Product analyst checks whether selected aspects are observable. Manager consolidates preferences. '
                'Verifier corrects unsupported interpretations in one pass, describing any changes in issues. '
                'Return exactly selections (option_id,weight) and issues (array of strings).'})
        if (not isinstance(result, dict) or set(result) != {'selections', 'issues'}
                or not isinstance(result['issues'], list) or any(not isinstance(s, str) for s in result['issues'])):
            raise ValueError('invalid_profile_response')
        proposed = {'selections': result['selections']}
        run_task({'C': [], 'base_scores': [], 'K': 0}, catalog=catalog, history=history,
                 profile=proposed, scene={})
        if role == '推荐依据核验':
            before = current
            if proposed != current and not result['issues']:
                raise ValueError('unexplained_profile_revision')
        current = proposed
        stages.append({'role': role, **result})
    return {'profile': current, 'before_feedback': before or current, 'stages': stages}


def run_task(task, *, catalog, history, profile, scene, mode='full', alpha=.5, invoke=None):
    """Rank the full fixed C using acquired qualification and referenced preferences."""
    if profile is None:
        analyzed = analyze_profile(history, catalog, method=task['method'], invoke=invoke)
        result = run_task(task, catalog=catalog, history=history, profile=analyzed['profile'],
                          scene=scene, mode=mode, alpha=alpha)
        result['before_feedback'] = run_task(task, catalog=catalog, history=history,
            profile=analyzed['before_feedback'], scene=scene, mode=mode, alpha=alpha)
        result['profile_analysis'] = analyzed
        return result
    if (mode not in ('full', 'uniform_weights', 'no_quality', 'mean_quality', 'base')
            or type(alpha) not in (int, float) or not math.isfinite(alpha) or not 0 <= alpha <= 1
            or type(task['K']) is not int or task['K'] < 0
            or len(task['C']) != len(set(task['C'])) or len(task['C']) != len(task['base_scores'])
            or any(type(b) not in (int, float) or not math.isfinite(b) or not 0 <= b <= 1 for b in task['base_scores'])
            or set(profile) != {'selections'} or not isinstance(profile['selections'], list)):
        raise ValueError('invalid_ranking_input')
    options = {p['option_id']: p for p in profile_options(history, catalog)}
    selected = []
    for item in profile['selections']:
        if (set(item) != {'option_id', 'weight'} or item['option_id'] not in options
                or type(item['weight']) not in (int, float) or not math.isfinite(item['weight'])
                or not 0 < item['weight'] <= 1):
            raise ValueError('unsupported_preference')
        selected.append((options[item['option_id']], item['weight']))
    if len({p['option_id'] for p, _ in selected}) != len(selected):
        raise ValueError('duplicate_preference')
    if mode == 'base':
        selected = []
    elif task.get('prefer_stock') is True:
        selected.append(({'option_id': 'request:stock', 'dimension': 'stock',
            'source': {'field': 'request', 'source_kind': 'experiment_design'}}, 1))
    if mode == 'uniform_weights':
        selected = [(p, 1) for p, _ in selected]
    total = math.fsum(w for _, w in selected)
    products = {p['parent_asin']: p for p in catalog}
    rows, qualities = [], []
    for parent in task['C']:
        stock = scene.get(parent, {}).get('stock', {})
        if stock.get('supported') is True:
            if any(type(stock.get(k)) not in (int, float) or not math.isfinite(stock[k])
                   or not 0 <= stock[k] <= maximum for k, maximum in (('value', 100), ('quality', 1))):
                raise ValueError('invalid_stock_evidence')
            qualities.append(stock['quality'])
    mean = math.fsum(qualities) / len(qualities) if qualities else 0
    for parent, base in zip(task['C'], task['base_scores']):
        attributes = product_attributes(products[parent])
        components = []
        for p, w in selected:
            if p['dimension'] == 'stock':
                stock = scene.get(parent, {}).get('stock', {})
                supported = stock.get('supported') is True
                match = stock['value'] / 100 if supported else 0
                quality = stock['quality'] if supported else 0
                if mode == 'no_quality':
                    quality = float(supported)
                elif mode == 'mean_quality':
                    quality = mean if supported else 0
            else:
                if p['dimension'] == 'title_term':
                    match = float(bool(re.search(r'\b' + re.escape(p['value']) + r'\b', attributes['title'])))
                    quality = 1.0
                else:
                    match = float(attributes[p['dimension']] == p['value'])
                    quality = float(attributes[p['dimension']] is not None)
            components.append({'option_id': p['option_id'], 'dimension': p['dimension'],
                'source': p['source'], 'weight': w / total, 'match': match, 'quality': quality})
        contribution = math.fsum(c['weight'] * c['match'] * c['quality'] for c in components)
        score = alpha * base + (1 - alpha) * contribution if selected else base
        rows.append({'parent_asin': parent, 'base': base, 'score': round(score, 12),
                     'eligible': scene.get(parent, {}).get('eligible') is True, 'components': components})
    ordered = sorted((r for r in rows if r['eligible']),
                     key=lambda r: (-r['score'], -r['base'], r['parent_asin'].encode()))
    return {'version': VERSION, 'mode': mode, 'topK': [r['parent_asin'] for r in ordered[:task['K']]],
            'candidates': rows, 'candidate_count': len(rows), 'eligible_count': len(ordered)}
