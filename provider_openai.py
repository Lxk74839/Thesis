"""One Responses wire contract. No generation HTTP sender or credential discovery."""
import copy
import hashlib
import json
import http.client
import base64

MODEL = 'gpt-5.4-mini-2026-03-17'
MAPPER = 'openai-responses-mapper-0.1.0'
PROFILE_SCHEMA_VERSION = 'rsm-profile-references-0.1.0'
PRODUCT_OBJECT_VERSION = 'acquired-product-object-0.3.0'
RANKING_ISSUE_VERSION = 'ranking-issue-proof-0.1.0'


def send_count(body, *, deadline_ms, credential, clock, connection_factory=None):
    """A single count POST. No redirects, retry, environment keys, or other endpoints."""
    remaining = min(30, (deadline_ms - clock()) / 1000)
    if remaining <= 0 or not credential or '\r' in credential or '\n' in credential:
        raise ValueError('invalid_count_deadline_or_credential')
    connection = (connection_factory or http.client.HTTPSConnection)('api.openai.com', timeout=remaining)
    try:
        connection.request('POST', '/v1/responses/input_tokens', body=body.encode('utf-8'), headers={
            'Content-Type': 'application/json', 'Authorization': 'Bearer ' + credential})
        response = connection.getresponse()
        envelope = {'status_code': response.status, 'headers': {k.lower(): v for k, v in response.getheaders()}, 'body': None}
        try:
            raw = response.read(1024**2 + 1)
        except (OSError, http.client.HTTPException) as exc:
            envelope['read_error'] = str(exc)
            raw = getattr(exc, 'partial', b'')[:1024**2 + 1]
        try:
            envelope['raw_utf8'] = raw.decode('utf-8')
        except UnicodeDecodeError:
            envelope['raw_base64'] = base64.b64encode(raw).decode('ascii')
        if 'read_error' in envelope:
            envelope['boundary_error'] = 'count_read_error'
        elif len(raw) > 1024**2 or clock() > deadline_ms:
            envelope['boundary_error'] = 'count_response_limit'
        else:
            try:
                envelope['body'] = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                envelope['boundary_error'] = 'invalid_count_json'
        return envelope
    finally:
        connection.close()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def object_schema(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def array_schema(items):
    return {'type': 'array', 'items': items}


def shape(value, *, fixed=False):
    if isinstance(value, dict):
        return object_schema({k: shape(v, fixed=fixed) for k, v in value.items()})
    if isinstance(value, list):
        options = list({canonical(shape(v, fixed=fixed)): shape(v, fixed=fixed) for v in value}.values())
        result = array_schema(options[0] if len(options) == 1 else {'anyOf': options} if options else {'type': ['string', 'number', 'boolean', 'null']})
        if fixed:
            result.update(minItems=len(value), maxItems=len(value))
        return result
    result = {'type': 'null' if value is None else 'boolean' if type(value) is bool else
            'number' if type(value) in (int, float) else 'string'}
    if fixed:
        result['enum'] = [value]
    return result


def role_output_schema(role, kind, messages):
    context = next(m['content']['runtime'] for m in reversed(messages)
                   if m['role'] == 'user' and isinstance(m['content'], dict) and 'runtime' in m['content'])
    text, nullable, scalar = {'type': 'string'}, {'type': ['string', 'null']}, {'type': ['string', 'number', 'boolean', 'null']}
    strings = array_schema(text)
    clause_ids = {'type': 'array', 'items': {'type': 'string', 'enum': context['necessary_clauses']},
        'minItems': len(context['necessary_clauses']), 'maxItems': len(context['necessary_clauses'])}
    citation = object_schema({'evidence_ref': text, 'receipt_id': text, 'target_id': text,
                              'version': {'type': 'integer'}, 'pointer': text})
    if kind == 'analysis':
        observation = object_schema({})
        if context['stage'] == '用户画像':
            observation = object_schema({'pointer': text,
                'preference_status': {'type': 'string', 'enum': ['unknown', 'history_fact']}})
        elif context['stage'] == '农产品画像':
            quality = list({canonical(shape(q)): shape(q) for q in context['quality'].values()}.values()) or [{'type': 'null'}]
            key = 'assessment_receipt_id' if context.get('profile_candidates') else 'assessment'
            assessment = text if key == 'assessment_receipt_id' else shape(context['assessments'].get(context['current']))
            observation = object_schema({'candidate_id': nullable, key: assessment, 'quality': {'anyOf': quality},
                'attributes': array_schema(object_schema({'attribute': text, 'citation': citation})),
                'unknown': strings})
            if context.get('bound_profile_contract') and context.get('profile_candidates'):
                options = []
                for parent in context['profile_candidates']:
                    references = []
                    for fact in context['facts'].get(parent, []):
                        for attribute, source in (('conclusion', 'inspection_report'),
                                ('status', 'retail_status'), ('stock_units', 'retail_status')):
                            if fact['data'].get('kind') != source or attribute not in fact['data']['facts']:
                                continue
                            bound = fact['citation'] | {'pointer': '/facts/' + attribute}
                            references.append(object_schema({'attribute': {'type': 'string', 'enum': [attribute]},
                                'citation': object_schema({k: shape(v) | {'enum': [v]} for k, v in bound.items()})}))
                    attributes = array_schema({'anyOf': references} if references else object_schema({}))
                    attributes.update(minItems=len(references), maxItems=len(references))
                    options.append(object_schema({'candidate_id': {'type': 'string', 'enum': [parent]},
                        'assessment_receipt_id': {'type': 'string', 'enum': [context['assessment_receipts'][parent]]},
                        'quality': shape(context['quality'].get(parent), fixed=True), 'attributes': attributes, 'unknown': strings}))
                observation = {'anyOf': options}
        observations = array_schema(observation)
        if (context.get('bound_profile_contract') == PRODUCT_OBJECT_VERSION
                and context['stage'] == '农产品画像' and context.get('profile_candidates')):
            observations = object_schema({parent: object_schema({k: v for k, v in option['properties'].items()
                if k != 'candidate_id'}) for parent, option in zip(context['profile_candidates'], options)})
        data = object_schema({'necessary_clauses': clause_ids, 'observations': observations})
        if context.get('bound_profile_contract') and context['stage'] == '农产品画像' and context.get('profile_candidates'):
            if context.get('bound_profile_contract') != PRODUCT_OBJECT_VERSION:
                observations.update(minItems=len(context['profile_candidates']), maxItems=len(context['profile_candidates']))
    elif kind == 'dispatch':
        data = object_schema({'candidate': {'type': ['string', 'null'], 'enum': [context['current']]},
            'to': {'type': 'string', 'enum': ['单智能体' if context['method'] == 'S' else '生命周期追溯']},
            'claim_ids': copy.deepcopy(clause_ids),
            **({'candidate_limit': {'type': 'integer', 'enum': [context.get('batch_limit', 32)]}}
                if context['current'] is not None else {})})
    elif kind == 'acquire':
        data = object_schema({'done': {'type': 'boolean', 'enum': [True]}, **({'plan_sha256': text, 'processed': strings}
                             if context['current'] is not None else {})})
        if context.get('acquisition_contract') and context['current'] is not None:
            result = next((m['content'] for m in reversed(messages) if m['role'] == 'tool'
                and isinstance(m['content'], dict) and 'processed' in m['content'] and 'plan_sha256' in m['content']), None)
            if result is not None:
                data['properties']['plan_sha256'] = text | {'enum': [result['plan_sha256']]}
                data['properties']['processed'] = array_schema(text | {'enum': result['processed']}) | {
                    'minItems': len(result['processed']), 'maxItems': len(result['processed'])}
    elif kind == 'draft':
        reason = object_schema({'claim_id': text, 'kind': text, 'value': scalar, 'unit': nullable,
                                'text': text, 'citations': array_schema(citation)})
        data = object_schema({'draft_id': text, 'parent_draft_id': nullable,
            'items': array_schema(object_schema({'parent_asin': text, 'sim_batch_id': text, 'reasons': array_schema(reason)}))})
        if context.get('bound_draft_contract'):
            items = []
            for parent in context['ordered']:
                refs = [key for key, row in context['citation_catalog'].items()
                    if row['candidate_id'] == parent and row.get('source_kind') == 'verified_claim_bundle']
                reasons = []
                for claim, name, sentence in (('c1', 'inspection_supported', '检验必要条件有完整有效支持（SIM）。'),
                        ('c2', 'on_sale_supported', '核验时点的在售必要条件有完整有效支持（SIM）。')):
                    reasons.append(object_schema({'claim_id': text | {'enum': [claim]}, 'kind': text | {'enum': [name]},
                        'value': {'type': 'boolean', 'enum': [True]}, 'unit': {'type': 'null'},
                        'text': text | {'enum': [sentence]},
                        'citations': array_schema(text | {'enum': refs}) | {'minItems': 1, 'maxItems': 1}}))
                for name in ('base_preference', 'retail_stock'):
                    available = [key for key, row in context['citation_catalog'].items()
                        if row['candidate_id'] == parent and row.get('source_kind') == name]
                    if not available or name == 'retail_stock' and not context.get('quality_arm'):
                        continue
                    value = (context['base_preferences'][parent]['value'] if name == 'base_preference' else
                        next(f['data']['facts']['stock_units'] for f in context['facts'][parent]
                            if f['data'].get('kind') == 'retail_status'))
                    sentence = ('偏好基础分为%.12f。' % value if name == 'base_preference' else '可售库存为%d单位（SIM）。' % value)
                    reasons.append(object_schema({'claim_id': text | {'enum': [name]}, 'kind': text | {'enum': [name]},
                        'value': shape(value) | {'enum': [value]}, 'unit': shape(None if name == 'base_preference' else 'units') |
                            {'enum': [None if name == 'base_preference' else 'units']},
                        'text': text | {'enum': [sentence]}, 'citations': array_schema(text | {'enum': available})}))
                items.append(object_schema({'parent_asin': text | {'enum': [parent]},
                    'sim_batch_id': text | {'enum': [context['candidate_batches'][parent]]},
                    'reasons': array_schema({'anyOf': reasons})}))
            data['properties']['items'] = array_schema({'anyOf': items} if items else object_schema({}))
            data['properties']['items'].update(minItems=len(items), maxItems=len(items))
            if 'draft_identifiers' in context:
                for key, value in context['draft_identifiers'].items():
                    data['properties'][key] = shape(value) | {'enum': [value]}
    elif kind == 'verification':
        data = object_schema({'issues': array_schema(object_schema({'issue_id': text, 'draft_id': text,
            'candidate_id': nullable, 'claim_id': nullable, 'pointer': text, 'code': text, 'blocking': {'type': 'boolean'},
            'allowed_actions': {'type': 'array', 'items': {'type': 'string', 'enum': ['revise_and_resubmit']},
                'minItems': 1, 'maxItems': 1},
            'verifier': {'type': 'string', 'enum': ['model']}, 'source_receipts': strings}))})
        if 'verification_receipts' in context:
            issue = data['properties']['issues']['items']
            issue['properties']['draft_id'] = text | {'enum': [context['draft']['draft_id']]}
            receipts = context['verification_receipts']
            issue['properties']['source_receipts'] = array_schema(text | {'enum': receipts}) if receipts else strings | {'maxItems': 0}
            def paths(value, base):
                result = [base or '/']
                children = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else []
                for key, child in children:
                    result.extend(paths(child, base + '/' + str(key).replace('~', '~0').replace('/', '~1')))
                return result
            issue['properties']['candidate_id'] = nullable | {'enum': [None, *[i['parent_asin'] for i in context['draft']['items']]]}
            issue['properties']['claim_id'] = nullable | {'enum': [None, *sorted({r['claim_id'] for i in context['draft']['items']
                for r in i['reasons']})]}
            issue['properties']['pointer'] = text | {'enum': paths(context['draft'], '')}
            if context.get('ranking_issue_contract') == RANKING_ISSUE_VERSION:
                order = array_schema(text | {'enum': context['G']})
                order['maxItems'] = len(context['ordered'])
                proof = object_schema({'observed_order': copy.deepcopy(order),
                    'claimed_expected_order': copy.deepcopy(order),
                    'basis': object_schema({'scope': text | {'enum': ['actual_G_full']},
                        'G_sha256': text, 'fusion_sha256': text}),
                    'first_difference': {'type': 'integer', 'minimum': 0, 'maximum': len(context['ordered'])}})
                issue['properties'].update(category=text | {'enum': ['ranking', 'evidence']},
                    ranking_evidence={'anyOf': [{'type': 'null'}, proof]})
                issue['required'] = list(issue['properties'])
    else:
        data = object_schema({'draft_id': text})
        if context.get('bound_profile_contract') and context.get('draft'):
            data['properties']['draft_id'] = text | {'enum': [context['draft']['draft_id']]}
    return object_schema({'kind': {'type': 'string', 'enum': [kind]}, 'data': data})


def closed_schema(schema):
    if not isinstance(schema, dict) or not set(schema) <= {
            'type', 'properties', 'required', 'additionalProperties', 'items', 'enum', 'anyOf',
            'description', 'minimum', 'maximum', 'minItems', 'maxItems', 'uniqueItems'}:
        raise ValueError('unsupported_schema')
    kinds = schema.get('type', [])
    kinds = kinds if isinstance(kinds, list) else [kinds]
    if 'object' in kinds:
        if (schema.get('additionalProperties') is not False or not isinstance(schema.get('properties'), dict)
                or set(schema.get('required', [])) != set(schema['properties'])):
            raise ValueError('open_schema')
        for child in schema['properties'].values():
            closed_schema(child)
    if 'array' in kinds:
        closed_schema(schema['items'])
    for child in schema.get('anyOf', []):
        closed_schema(child)
    if not kinds and schema.get('enum') and all(isinstance(v, str) for v in schema['enum']):
        schema['type'] = 'string'
    elif not kinds and not schema.get('anyOf'):
        raise ValueError('missing_schema_type')


def prepare(request, project_id):
    return prepare_responses(request, project_id, model_id=MODEL, mapper=MAPPER, legacy_options=True)


def prepare_responses(request, project_id, *, model_id, mapper, legacy_options=False,
                      protocol_items=None, include_reasoning=False):
    request = copy.deepcopy(request)
    closed_schema(request['output_schema'])
    if request['output_schema'].get('type') != 'object':
        raise ValueError('invalid_role_schema')
    for tool in request['tools']:
        if not {'name', 'version', 'input_schema'} <= set(tool) <= {'name', 'version', 'input_schema', 'description'}:
            raise ValueError('invalid_tool_schema')
        closed_schema(tool['input_schema'])
    items = []
    for index, message in enumerate(request['messages']):
        content = message['content']
        text = content if isinstance(content, str) else canonical(content)
        if protocol_items is not None and index in protocol_items:
            items.extend(copy.deepcopy(protocol_items[index]))
        elif message['role'] == 'tool':
            items.append({'type': 'function_call_output', 'call_id': message['tool_call_id'], 'output': text})
        elif message.get('tool_requests'):
            items.extend({'type': 'function_call', 'call_id': c['call_id'], 'name': c['name'],
                          'arguments': canonical(c['arguments'])} for c in message['tool_requests'])
        else:
            items.append({'role': message['role'], 'content': text})
    tools = [{'type': 'function', 'name': t['name'], 'description': t.get('description', t['name']),
              'parameters': copy.deepcopy(t['input_schema']), 'strict': True} for t in request['tools']]
    wire = {'model': model_id, 'input': items, 'tools': tools,
        'text': {'format': {'type': 'json_schema', 'name': 'rsm_' + request['output_kind'],
                           'strict': True, 'schema': copy.deepcopy(request['output_schema'])}},
        'reasoning': {'effort': 'none'}, 'parallel_tool_calls': False,
        'tool_choice': 'auto' if tools else 'none',
        'max_output_tokens': request['max_output_tokens'], 'store': False, 'stream': False}
    if legacy_options:
        wire.update(truncation='disabled', service_tier='default')
    if include_reasoning:
        wire['include'] = ['reasoning.encrypted_content']
    count = {k: copy.deepcopy(v) for k, v in wire.items()
             if k not in ('max_output_tokens', 'service_tier', 'store', 'stream')}
    result = {'schema_version': 'openai-prepared-0.1.0', 'status': 'prepared', 'model_id': model_id,
        'project_id': project_id, 'mapper_version': mapper, 'tool_schema_sha256': sha(request['tools']),
        'role_schema_sha256': sha(request['output_schema']), 'wire_body': wire, 'count_body': count,
        'wire_utf8': canonical(wire), 'count_utf8': canonical(count),
        'wire_sha256': sha(wire), 'count_payload_sha256': sha(count), 'input_tokens': None, 'missing': [],
        'source': {k: request[k] for k in ('run_id', 'request_id', 'attempt_id', 'session_id', 'role', 'output_kind')}}
    result['wire_bytes'] = len(result['wire_utf8'].encode('utf-8'))
    result['prepared_id'] = sha({k: result[k] for k in ('wire_sha256', 'count_payload_sha256',
        'mapper_version', 'tool_schema_sha256', 'role_schema_sha256', 'project_id')})
    return result


def verify_prepared(prepared):
    try:
        wire, count = prepared['wire_body'], prepared['count_body']
        if (set(wire) != {'model', 'input', 'tools', 'text', 'reasoning', 'parallel_tool_calls', 'tool_choice',
                         'truncation', 'max_output_tokens', 'service_tier', 'store', 'stream'}
                or wire['reasoning'] != {'effort': 'none'} or wire['parallel_tool_calls'] is not False
                or wire['truncation'] != 'disabled' or wire['service_tier'] != 'default'
                or wire['store'] is not False or wire['stream'] is not False
                or type(wire['max_output_tokens']) is not int or not 0 < wire['max_output_tokens'] <= 128000
                or wire['tool_choice'] != ('auto' if wire['tools'] else 'none')
                or not isinstance(wire['input'], list) or not wire['input'] or not isinstance(wire['tools'], list)
                or set(wire['text']) != {'format'} or set(wire['text']['format']) != {'type', 'name', 'strict', 'schema'}
                or wire['text']['format']['type'] != 'json_schema' or wire['text']['format']['strict'] is not True
                or wire['text']['format']['name'] != 'rsm_' + prepared['source']['output_kind']
                or prepared['wire_bytes'] != len(prepared['wire_utf8'].encode('utf-8'))
                or prepared['wire_bytes'] > 16 * 1024**2):
            return False
        pending, seen = set(), set()
        tool_map = {tool['name']: tool for tool in wire['tools']}
        for item in wire['input']:
            if 'role' in item:
                if pending or set(item) != {'role', 'content'} or item['role'] not in ('system', 'user', 'assistant') or not isinstance(item['content'], str):
                    return False
            elif item.get('type') == 'function_call':
                if (set(item) != {'type', 'call_id', 'name', 'arguments'} or not isinstance(item['arguments'], str)
                        or not isinstance(item['call_id'], str) or not item['call_id'] or item['call_id'] in seen
                        or item['name'] not in tool_map or not matches(json.loads(item['arguments']), tool_map[item['name']]['parameters'])):
                    return False
                pending.add(item['call_id'])
                seen.add(item['call_id'])
            elif set(item) != {'type', 'call_id', 'output'} or item.get('type') != 'function_call_output' or not isinstance(item['output'], str):
                return False
            else:
                if item['call_id'] not in pending:
                    return False
                pending.remove(item['call_id'])
        if pending:
            return False
        for tool in wire['tools']:
            if (set(tool) != {'type', 'name', 'description', 'parameters', 'strict'} or tool['type'] != 'function'
                    or tool['strict'] is not True or tool['name'] not in ('list_evidence', 'read_evidence', 'candidate_page', 'acquire_batch')):
                return False
            closed_schema(copy.deepcopy(tool['parameters']))
        closed_schema(copy.deepcopy(wire['text']['format']['schema']))
        return (prepared['schema_version'] == 'openai-prepared-0.1.0' and prepared['status'] == 'prepared'
            and prepared['model_id'] == wire['model'] == MODEL and prepared['mapper_version'] == MAPPER
            and prepared['wire_utf8'] == canonical(wire) and prepared['count_utf8'] == canonical(count)
            and prepared['wire_sha256'] == sha(wire) and prepared['count_payload_sha256'] == sha(count)
            and count == {k: v for k, v in wire.items()
                          if k not in ('max_output_tokens', 'service_tier', 'store', 'stream')}
            and prepared['role_schema_sha256'] == sha(wire['text']['format']['schema'])
            and prepared['prepared_id'] == sha({k: prepared[k] for k in ('wire_sha256', 'count_payload_sha256',
                'mapper_version', 'tool_schema_sha256', 'role_schema_sha256', 'project_id')}))
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def cost_microusd(input_tokens, output_tokens, cached=0):
    return (750 * (input_tokens - cached) + 75 * cached + 4500 * output_tokens + 999) // 1000


def matches(value, schema):
    if 'anyOf' in schema:
        return any(matches(value, child) for child in schema['anyOf'])
    types = schema['type'] if isinstance(schema['type'], list) else [schema['type']]
    kind = ('null' if value is None else 'boolean' if type(value) is bool else 'integer' if type(value) is int
            else 'number' if type(value) is float else 'string' if isinstance(value, str)
            else 'array' if isinstance(value, list) else 'object' if isinstance(value, dict) else None)
    if kind not in types and not (kind == 'integer' and 'number' in types):
        return False
    if 'enum' in schema and value not in schema['enum']:
        return False
    if kind == 'object':
        return set(value) == set(schema['properties']) and all(matches(v, schema['properties'][k]) for k, v in value.items())
    if kind == 'array':
        return (schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', len(value))
                and (not schema.get('uniqueItems') or len({canonical(v) for v in value}) == len(value))
                and all(matches(v, schema['items']) for v in value))
    if kind in ('integer', 'number'):
        return schema.get('minimum', value) <= value <= schema.get('maximum', value)
    return True


def normalized_usage(envelope):
    body = envelope['body']
    usage = body['usage']
    i, o = usage['input_tokens'], usage['output_tokens']
    c, r = usage['input_tokens_details']['cached_tokens'], usage['output_tokens_details']['reasoning_tokens']
    if (any(type(v) is not int or v < 0 for v in (i, o, c, r)) or c > i or r > o
            or usage.get('total_tokens') != i + o or usage['input_tokens_details'].get('cache_write_tokens', 0) != 0):
        raise ValueError('unknown_usage')
    return {'input_tokens': i, 'output_tokens': o, 'cost_microusd': cost_microusd(i, o, c),
            'cached_input_tokens': c, 'reasoning_output_tokens': r}


def terminal_error(envelope):
    status, body = envelope.get('status_code'), envelope.get('body')
    output = body.get('output', []) if isinstance(body, dict) else []
    output = output if isinstance(output, list) else []
    if isinstance(body, dict) and (body.get('usage') is not None or 'model' in body or 'service_tier' in body):
        if body.get('model') != MODEL or body.get('service_tier') != 'default':
            return 'provider_binding_mismatch', 'capability'
    if any(isinstance(item, dict) and item.get('type') not in ('message', 'function_call', 'reasoning') for item in output):
        return 'unsupported_provider_tool', 'capability'
    if status in (401, 403):
        return 'auth', 'auth'
    if status == 429:
        return 'rate_limit', 'rate_limit'
    if type(status) is int and status >= 500:
        return 'transport', 'transport'
    if not isinstance(body, dict):
        return 'format_error', 'format'
    if body.get('status') == 'incomplete':
        return 'truncated', 'truncated'
    if any(isinstance(c, dict) and c.get('type') == 'refusal' for item in output
           if isinstance(item, dict) and item.get('type') == 'message' and isinstance(item.get('content'), list)
           for c in item['content']):
        return 'refusal', 'refusal'
    return 'format_error', 'format'


def normalize(envelope, request):
    body = envelope['body']
    usage = normalized_usage(envelope)
    if body['model'] != MODEL or body['service_tier'] != 'default' or envelope['status_code'] != 200:
        raise ValueError('provider_binding_mismatch')
    if any(item.get('type') not in ('message', 'function_call', 'reasoning') for item in body['output']):
        raise ValueError('unsupported_provider_tool')
    text = ''.join(c['text'] for item in body['output'] if item['type'] == 'message'
                   for c in item['content'] if c['type'] == 'output_text')
    calls = [{'call_id': item['call_id'], 'name': item['name'], 'arguments': json.loads(item['arguments'])}
             for item in body['output'] if item['type'] == 'function_call']
    content = None if calls and not text else json.loads(text)
    canonical(content)
    if (body['status'] != 'completed' or calls and content is not None or not calls and
            (set(content) != {'kind', 'data'} or content['kind'] != request['output_kind'] or not isinstance(content['data'], dict))):
        raise ValueError('invalid_output')
    if not calls and not matches(content, request['output_schema']):
        raise ValueError('invalid_role_output')
    return {'status': 'ok', 'request_id': request['request_id'], 'attempted': True,
        'message': {'role': 'assistant', 'content': content, 'tool_requests': calls},
        'usage': usage,
        'raw_usage': copy.deepcopy(body['usage']), 'raw_response': copy.deepcopy(envelope), 'usage_known': True,
        'provider_request_id': envelope.get('headers', {}).get('x-request-id'),
        'provider_response_id': body['id'], 'returned_model': body['model'], 'service_tier': body['service_tier'],
        'usage_basis': 'fixture', 'provenance': 'fixture', 'provider_requests_sent': 0, 'error': None}
