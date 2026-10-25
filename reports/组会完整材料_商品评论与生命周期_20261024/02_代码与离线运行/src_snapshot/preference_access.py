"""Pure API request construction and default-deny model capability dispatch.

This module receives the approved view only. It has no filesystem, index,
network, shell, evaluation loader, or model execution operation.
"""

import json


REQUEST = '根据较早正向评论和商品标题，对完整候选谷物商品按偏好排序。'
TASK_KEYS = {'schema_version', 'task_id', 'catalog_version', 'text_policy_version', 'metadata_time_basis',
             'history_cutoff_exclusive_ms', 'request', 'history', 'seen_parent_asins',
             'candidate_parent_asins', 'background_statistics'}


def require(condition):
    if not condition:
        raise ValueError('unsafe_model_view')


def identifiers(values):
    require(isinstance(values, list) and all(isinstance(v, str) and v for v in values))
    require(values == sorted(set(values), key=lambda v: v.encode('utf-8')))
    return set(values)


class ModelSession:
    def __init__(self, task, catalog):
        require(isinstance(task, dict) and set(task) == TASK_KEYS)
        require(task['schema_version'] == 'preference-model-input-1.0.0'
                and task['text_policy_version'] == 'finite-text-1.0.0'
                and task['metadata_time_basis'] == 'collection_snapshot')
        require(isinstance(task['task_id'], str) and len(task['task_id']) == 64
                and all(c in '0123456789abcdef' for c in task['task_id']))
        time = task['history_cutoff_exclusive_ms']
        require(type(time) is int)
        require(task['request'] == {'source': 'experiment_template', 'text': REQUEST})
        require(isinstance(catalog, list))
        for product in catalog:
            require(isinstance(product, dict) and set(product) == {'parent_asin', 'title', 'crop'})
            require(all(isinstance(v, str) and v for v in product.values()))
        products = {p['parent_asin']: p for p in catalog}
        require(len(products) == len(catalog))
        seen = identifiers(task['seen_parent_asins'])
        candidates = identifiers(task['candidate_parent_asins'])
        require(seen <= products.keys() and candidates == products.keys() - seen)
        require(isinstance(task['history'], list) and bool(task['history']))
        history_parents = set()
        for event in task['history']:
            require(isinstance(event, dict) and set(event) == {'parent_asin', 'timestamp_ms', 'rating', 'text'})
            require(event['parent_asin'] in seen and type(event['timestamp_ms']) is int and event['timestamp_ms'] < time)
            require(type(event['rating']) in (int, float) and event['rating'] in (4, 5))
            require(isinstance(event['text'], str) and bool(event['text']))
            history_parents.add(event['parent_asin'])
        require(isinstance(task['background_statistics'], list))
        require([s.get('parent_asin') for s in task['background_statistics']] == task['candidate_parent_asins'])
        for stat in task['background_statistics']:
            require(set(stat) == {'parent_asin', 'interaction_count', 'account_count', 'positive_account_count'})
            require(all(type(stat[k]) is int and stat[k] >= 0 for k in ('interaction_count', 'account_count', 'positive_account_count')))
            require(stat['positive_account_count'] <= stat['account_count'] <= stat['interaction_count'])
        payload = {**task, 'products': [products[p] for p in sorted(candidates | history_parents, key=lambda p: p.encode('utf-8'))]}
        self._content = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

    @staticmethod
    def capabilities():
        return {'host_io': False, 'tools': [], 'indices': []}

    def dispatch(self, operation, arguments):
        if operation == 'model_request' and arguments == {}:
            return {'status': 'ok', 'request': {'messages': [{'role': 'user', 'content': self._content}], 'tools': []}}
        return {'status': 'access_denied'}
