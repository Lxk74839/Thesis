"""Independent joint association audit. Standard library; no production imports."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import hmac
import itertools
import json
import math
import os
from pathlib import Path
import stat
import sys
import unicodedata
from statistics import median

ROOT = Path(__file__).resolve().parents[3]
VERSION = 'joint-reference-0.1.0'


def insist(condition, code):
    if not condition:
        raise ValueError(code)


def wire(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':'), allow_nan=False).encode()


def no_duplicates(pairs):
    result = {}
    for key,value in pairs:
        insist(key not in result,'duplicate_json_key')
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw, object_pairs_hook=no_duplicates,
                      parse_constant=lambda _: insist(False,'nonfinite_json'))


def path(value):
    target = Path(os.path.abspath(ROOT/value))
    insist(target==ROOT or ROOT in target.parents,'invalid_path')
    for ancestor in (target,*target.parents):
        insist(not ancestor.is_symlink() and not ancestor.is_junction(),'invalid_path')
        if ancestor.exists():
            insist(not getattr(ancestor.lstat(),'st_file_attributes',0) & stat.FILE_ATTRIBUTE_REPARSE_POINT,'invalid_path')
    return target


def info(file):
    sha = hashlib.sha256()
    size = lines = 0
    with file.open('rb') as stream:
        while block := stream.read(1024*1024):
            sha.update(block)
            size += len(block)
            lines += block.count(b'\n')
    return {'path':file.relative_to(ROOT).as_posix(),'bytes':size,'records':lines,'sha256':sha.hexdigest()}


def bound(binding, cache):
    file = path(binding['path'])
    if file not in cache:
        cache[file] = info(file)
    insist(all(binding[k]==cache[file][k] for k in ('sha256','bytes','records') if k in binding),'component_binding_mismatch')
    return file


def entries(file):
    with file.open('rb') as stream:
        for number,raw in enumerate(stream,1):
            yield parse(raw), {'component_sha256':info_cache[file]['sha256'],
                              'path':file.relative_to(ROOT).as_posix(),'line':number,'row_sha256':hashlib.sha256(raw).hexdigest()}


def save(file, value):
    with file.open('xb') as stream:
        stream.write(wire(value)+b'\n')


info_cache = {}


def distribution(values):
    values = sorted(values)
    if not values:
        return {'n':0,'mean':None,'median':None,'p90':None,'p95':None,'max':None}
    return {'n':len(values),'mean':math.fsum(values)/len(values),'median':median(values),
            'p90':values[math.ceil(.9*len(values))-1],'p95':values[math.ceil(.95*len(values))-1],'max':values[-1]}


def coverage(ids, tasks, evaluations, catalog, exposure):
    targets = Counter(evaluations[key]['target_parent_asin'] for key in ids)
    ranked = sorted(targets,key=lambda p:(-targets[p],p.encode()))
    n = len(ids)
    depths = [len({h['parent_asin'] for h in tasks[key]['history']}) for key in ids]
    times = [evaluations[key]['target_timestamp_ms'] for key in ids]
    crops = Counter(catalog[evaluations[key]['target_parent_asin']]['crop'] for key in ids)
    years = Counter(str(datetime.fromtimestamp(t/1000,timezone.utc).year) for t in times)
    return {'accounts':n,'history_depth_groups':{'1':depths.count(1),'2':depths.count(2),'3+':sum(d>=3 for d in depths)},
        'history_distinct_parents':distribution(depths),
        'history_events':distribution([len(tasks[key]['history']) for key in ids]),
        'effective_history_texts':distribution([sum(bool(h['text'].strip()) for h in tasks[key]['history']) for key in ids]),
        'history_parent_coverage':len({h['parent_asin'] for key in ids for h in tasks[key]['history']}),
        'target_concentration':{'distinct_parents':len(targets),'cluster_size_histogram':dict(sorted(Counter(targets.values()).items())),
            'top_counts':{str(k):sum(targets[p] for p in ranked[:k]) for k in (1,5,10,20)},
            'top_shares':{str(k):sum(targets[p] for p in ranked[:k])/n if n else None for k in (1,5,10,20)},
            'hhi':math.fsum((v/n)**2 for v in targets.values()) if n else None},
        'target_crop':{crop:crops[crop] for crop in sorted({p['crop'] for p in catalog.values()})},
        'target_UTC_year':{str(y):years[str(y)] for y in range(min(map(int,years),default=0),max(map(int,years),default=-1)+1)},
        'target_time_UTC':{'min':datetime.fromtimestamp(min(times)/1000,timezone.utc).isoformat() if times else None,
                           'max':datetime.fromtimestamp(max(times)/1000,timezone.utc).isoformat() if times else None},
        'legacy_exposure':{'legacy_corpus_accounts':sum(exposure[k]['legacy_corpus_member'] for k in ids),
            'known_agent_result_accounts':sum(exposure[k]['agent_account_result_view']=='observed' for k in ids),
            'unknown_agent_result_accounts':sum(exposure[k]['agent_account_result_view']=='unknown' for k in ids),
            'known_human_result_accounts':sum(exposure[k]['human_account_result_view']=='observed' for k in ids),
            'unknown_human_result_accounts':sum(exposure[k]['human_account_result_view']=='unknown' for k in ids)},
        'limitations':['conditional_on_fixed_catalog_materials_and_source_accounts','shared_products_and_materials',
                       'sparse_history','fixed_SIM_time_is_not_historical_supply_chain_validation','legacy_exposure_not_new_blind_test']}


def verify_projection(config, inputs, components):
    catalog_rows = [v for v,_ in entries(inputs['preference_catalog'])]
    catalog = {v['parent_asin']:v for v in catalog_rows}
    scenario_record = parse(inputs['scenarios'].read_bytes())
    request_file = bound(scenario_record['components']['requests.jsonl'],info_cache)
    request_rows = [r for r,_ in entries(request_file) if r['profile_id']=='R1_AND_R5_SIM_Q1_ON_SALE']
    insist(len(request_rows)==1,'joint_view_binding_mismatch')
    approved_request = request_rows[0]
    def counts(text):
        text = ' '.join(unicodedata.normalize('NFKC',text).casefold().split())
        return Counter([text] if 0<len(text)<3 else [text[i:i+3] for i in range(len(text)-2)])
    documents = {p:counts(v['title']+' '+v['crop']) for p,v in catalog.items()}
    frequency = Counter(token for tokens in documents.values() for token in tokens)
    idf = {token:1+math.log((len(catalog)+1)/(frequency[token]+1)) for token in sorted(frequency)}
    def vector(tokens):
        weighted = {token:(1+math.log(tokens[token]))*idf[token] for token in sorted(tokens) if token in idf}
        length = math.sqrt(math.fsum(v*v for v in weighted.values()))
        return {token:v/length for token,v in weighted.items()} if length else {}
    vectors = {p:vector(tokens) for p,tokens in documents.items()}
    manifest = parse(components['model/manifest.json'].read_bytes())
    insist(set(manifest)=={'schema_version','components'} and set(manifest['components'])=={'catalog.jsonl','roots.jsonl','candidates.jsonl'},'unsafe_model_manifest')
    for name,ref in manifest['components'].items():
        actual = info_cache[components['model/'+name]]
        insist(ref=={'bytes':actual['bytes'],'sha256':actual['sha256']},'model_manifest_binding')
    insist([v for v,_ in entries(components['model/catalog.jsonl'])]==catalog_rows,'joint_projection_mismatch')
    normal = parse(inputs['normal'].read_bytes())
    batch_file = bound(normal['components']['batches.jsonl'],info_cache)
    batches = {r['parent_asin']:r['sim_batch_id'] for r,_ in entries(batch_file)}
    expected_maps = [{'parent_asin':p,'sim_batch_id':batches[p]} for p in sorted(catalog,key=lambda x:x.encode())]
    insist([v for v,_ in entries(components['candidate-map.jsonl'])]==expected_maps,'joint_projection_mismatch')
    paths = [inputs['preference_tasks'],components['roots.jsonl'],components['base-scores.jsonl'],components['model/roots.jsonl'],components['model/candidates.jsonl']]
    root_details = {}
    candidate_references = 0
    for values in itertools.zip_longest(*(entries(p) for p in paths)):
        insist(all(v is not None for v in values),'joint_projection_mismatch')
        original,root,score,model,candidates = [v[0] for v in values]
        key = original['task_id']
        c = original['candidate_parent_asins']
        h = original['history']
        hsha = hashlib.sha256(wire(h)).hexdigest()
        csha = hashlib.sha256(wire(c)).hexdigest()
        insist(root['root_task_id']==score['root_task_id']==model['root_task_id']==candidates['root_task_id']==key
                and root['C']==score['C']==candidates['C']==c
                and root['history']==model['history']==h
                and root['seen_parent_asins']==model['seen_parent_asins']==original['seen_parent_asins']
                and root['history_cutoff_exclusive_ms']==model['history_cutoff_exclusive_ms']==original['history_cutoff_exclusive_ms'],
                'joint_projection_mismatch')
        insist(c==[p for p in catalog if p not in set(original['seen_parent_asins'])]
                and all(event['timestamp_ms']<original['history_cutoff_exclusive_ms'] for event in h),'joint_projection_mismatch')
        profile = {}
        for event in h:
            product = catalog[event['parent_asin']]
            event_vector = vector(counts(' '.join([event['text'],product['title'],product['crop']])))
            for token,value in event_vector.items():
                profile[token] = profile.get(token,0)+event['rating']/5*value
        length = math.sqrt(math.fsum(profile[t]**2 for t in sorted(profile)))
        profile = {t:profile[t]/length for t in sorted(profile)} if length else {}
        raw = [round(math.fsum(value*profile.get(token,0) for token,value in vectors[p].items()),12) for p in c]
        lo,hi = min(raw,default=0),max(raw,default=0)
        expected = [round((v-lo)/(hi-lo),12) if hi!=lo else .5 for v in raw]
        insist(len(score['b'])==len(raw)==len(score['b_raw'])
                and all(type(v) in (int,float) and math.isfinite(v) for v in score['b']+score['b_raw'])
                and all(abs(a-b)<=1e-12 for a,b in zip(score['b'],expected))
                and all(abs(a-b)<=1e-12 for a,b in zip(score['b_raw'],raw)), 'base_score_mismatch')
        bsha = hashlib.sha256(wire(list(zip(c,score['b'])))).hexdigest()
        safe_root = {'schema_version':'joint-model-input-0.1.0','root_task_id':key,'history':h,
            'seen_parent_asins':original['seen_parent_asins'],'history_cutoff_exclusive_ms':original['history_cutoff_exclusive_ms'],
            'metadata_time_basis':'collection_snapshot','text_policy_version':'finite-text-1.0.0',
            'catalog_version':config['catalog_version'],'candidate_count':len(c),'C_sha256':csha,'H_sha256':hsha,
            'base_scores_sha256':bsha,'score_version':'char3-tfidf-history-1.0.0'}
        insist(model==safe_root and candidates=={'root_task_id':key,'C':c,'b':score['b'],
            'batches':[batches[p] for p in c],'background_statistics':original['background_statistics']},'joint_projection_mismatch')
        insist(root['H_sha256']==hsha and root['C_sha256']==csha and root['base_scores_sha256']==bsha
                and root['root_input_sha256']==hashlib.sha256(wire({k:v for k,v in original.items() if k!='request'})).hexdigest(),
                'joint_projection_mismatch')
        root_details[key] = {'H_sha256':hsha,'C_sha256':csha,'base_scores_sha256':bsha,
                             'root_input_sha256':root['root_input_sha256'],'safe_root':safe_root}
        position = {p:i for i,p in enumerate(c)}
        base_order = sorted(c,key=lambda p:(-score['b'][position[p]],p.encode()))
        root_details[key]['page_heads'] = {order:[{**catalog[p], 'sim_batch_id':batches[p],
            'base_score':score['b'][position[p]],'background_statistics':original['background_statistics'][position[p]]}
            for p in ordered[:32]] for order,ordered in (('parent',c),('base',base_order))}
        candidate_references += len(c)
    seen_views = set()
    views = {(v['view_id'],v['snapshot_id']):v for v in config['views']}
    for value,_ in entries(components['view-bindings.jsonl']):
        key = value['root_task_id']
        vk = (value['view_id'],value['snapshot_id'])
        insist(key in root_details and vk in views and (key,vk) not in seen_views,'joint_view_binding_mismatch')
        seen_views.add((key,vk))
        insist(all(value[k]==v for k,v in root_details[key].items() if k in ('H_sha256','C_sha256','base_scores_sha256','root_input_sha256'))
                and all(value[k]==v for k,v in views[vk].items())
                and value['execution_budget'] is None and value['execution_authorized'] is False
                and value['budget_candidate']==config['budget']['candidate'] and value['K']==10
                and value['principal_id']=='SIM-VERIFIER' and value['verify_at_ms']==1791417600000,
                'joint_view_binding_mismatch')
        quality = views[vk]['arm']=='quality'
        insist(value['request']==approved_request and value['alpha']==(.5 if quality else 1)
                and value['beta']==[.25,.5,.25] and value['planned_methods']==(['M'] if quality else ['R','S','M'])
                and value['candidate_map_sha256']==hashlib.sha256(wire(batches)).hexdigest()
                and value['preference']=={'source':'experiment_design','dimensions':['retail_stock'] if quality else [],
                    'weights':{'retail_stock':1} if quality else {}},'joint_view_binding_mismatch')
        unsigned = {k:v for k,v in value.items() if k!='common_binding_sha256'}
        insist(value['common_binding_sha256']==hashlib.sha256(wire(unsigned)).hexdigest(),'joint_view_binding_mismatch')
    insist(len(seen_views)==len(root_details)*len(views),'joint_view_binding_mismatch')
    key_bytes = inputs['identity_key'].read_bytes()
    handles = {}
    for value,_ in entries(components['private/session-map.jsonl']):
        root = value['root_task_id']
        vk = value['view_id'],value['snapshot_id']
        insist(root in root_details and vk in views,'joint_session_binding_mismatch')
        view = views[vk]
        expected = hmac.new(key_bytes,b'Thesis:joint-session-0.1.0\0'+wire([root,view['material_version'],
            view['snapshot_id'],view['request_profile_id']]),hashlib.sha256).hexdigest()
        insist(value['session_handle']==expected and expected not in handles,'joint_session_binding_mismatch')
        handles[expected]=(root,view)
    insist(len(handles)==len(seen_views),'joint_session_binding_mismatch')
    default_handles = {root:handle for handle,(root,view) in handles.items() if view['view_id']==config['views'][0]['view_id']}
    actual_requests = denied = 0
    request_handles, page_roots = set(), set()
    denial_coverage = defaultdict(set)
    for observation,_ in entries(components['private/access-probe.jsonl']):
        response = observation['response']
        probe = observation['probe']
        sid = probe['session_task_id']
        bound_handle = sid if sid in handles else default_handles.get(sid)
        if bound_handle is None:
            insist(response=={'status':'access_denied'},'unsafe_model_request')
            denied += 1
            continue
        if response.get('status')=='access_denied':
            insist(response=={'status':'access_denied'},'unsafe_denial')
            insist(not (probe['operation']=='model_request' and probe['arguments']=={}),'unexpected_request_denial')
            denied += 1
            root,_ = handles[bound_handle]
            op,args = probe['operation'],probe['arguments']
            if op=='read_resource' and args=={'path':config['inputs']['preference_evaluation']['path']}:
                denial_coverage[root].add('existing_private')
            elif op=='read_resource' and args=={'path':'data/private-nonexistent-target.jsonl'}:
                insist(not (ROOT/'data/private-nonexistent-target.jsonl').exists(),'probe_resource_not_absent')
                denial_coverage[root].add('absent_private')
            elif op=='invoke_tool' and args=={'name':'private_evaluator','role':'evaluator'}:
                denial_coverage[root].add('arbitrary_tool')
            elif op=='model_request' and set(args)=={'root_task_id'} and args['root_task_id'] in root_details and args['root_task_id']!=root:
                denial_coverage[root].add('cross_root')
            elif op=='candidate_page' and args=={'order':'parent','cursor':'forged-cross-session-cursor'}:
                denial_coverage[root].add('forged_cursor')
        elif observation['probe']['operation']=='model_request':
            request = response['request']
            insist(request['tools']==[] and len(request['messages'])==1
                    and request['messages'][0]['role']=='user','unsafe_model_request')
            payload = parse(request['messages'][0]['content'])
            handle = payload['session_handle']
            insist(handle==bound_handle and probe['arguments']=={},'unsafe_model_request')
            root,view = handles[handle]
            allowed = set(root_details[root]['safe_root']) | {'session_handle','K','verify_at_ms','request','source_disclosure',
                'alpha','beta','preference','tool_version','model_version','prompt_version','input_fingerprint'}
            insist(set(payload)==allowed and all(payload[k]==v for k,v in root_details[root]['safe_root'].items()),'unsafe_model_request')
            quality = view['arm']=='quality'
            insist(payload['request']=={'source':'experiment_design','text':approved_request['design_text'],
                        'necessary_clauses':approved_request['necessary_clauses']}
                    and payload['preference']=={'source':'experiment_design','dimensions':['retail_stock'] if quality else [],
                        'weights':{'retail_stock':1} if quality else {}}
                    and payload['alpha']==(.5 if quality else 1) and payload['beta']==[.25,.5,.25]
                    and payload['K']==10 and payload['verify_at_ms']==1791417600000 and payload['source_disclosure']=='SIM'
                    and all(payload[k]=='pending' for k in ('tool_version','model_version','prompt_version')), 'unsafe_model_request')
            unsigned = {k:v for k,v in payload.items() if k!='input_fingerprint'}
            insist(payload['input_fingerprint']==hashlib.sha256(wire(unsigned)).hexdigest(),'unsafe_model_request')
            actual_requests += 1
            request_handles.add(handle)
        elif probe['operation']=='candidate_page':
            root,_ = handles[bound_handle]
            args = probe['arguments']
            insist(set(args)=={'order','cursor'} and args['order'] in ('parent','base')
                    and set(response)=={'status','candidates','total_candidates','next_cursor'}
                    and response['status']=='ok' and response['total_candidates']==root_details[root]['safe_root']['candidate_count'],
                    'unsafe_candidate_page')
            if args['cursor'] is None:
                insist(response['candidates']==root_details[root]['page_heads'][args['order']],'unsafe_candidate_page')
                if args['order']=='parent':page_roots.add(root)
        else:
            insist(False,'unsafe_model_request')
    insist(request_handles==set(handles) and page_roots==set(root_details)
            and all(denial_coverage[root]=={'existing_private','absent_private','arbitrary_tool','cross_root','forged_cursor'}
                    for root in root_details),'incomplete_probe_coverage')
    return {'all_root_projections_checked':len(root_details),'complete_candidate_references':candidate_references,
            'actual_request_probes':actual_requests,'actual_denials':denied,'score_tolerance':1e-12}


def verify_sources(config, inputs, components, record):
    manifest = parse(components['package-manifest.json'].read_bytes())
    insist(manifest['sources']==config['inputs'] and manifest['views']==config['views'],'source_graph_mismatch')
    expected = {role:dict(info_cache[file]) for role,file in inputs.items()}
    for role in ('catalog','selected','cleaning','split'):
        source_record = parse(inputs[role].read_bytes())
        for key,value in source_record.items():
            digest_key = key[:-5]+'_sha256' if key.endswith('_path') else ''
            if digest_key in source_record and isinstance(value,str):
                file = bound({'path':value,'sha256':source_record[digest_key]},info_cache)
                expected[role+':'+key] = dict(info_cache[file])
    insist(manifest['source_components']==expected,'source_graph_mismatch')
    for role in ('normal','scenarios','quality'):
        source_record = parse(inputs[role].read_bytes())
        insist(manifest['upstream_components'][role]==source_record['components'],'source_graph_mismatch')
        for ref in source_record['components'].values():
            bound(ref,info_cache)
        acceptance = parse(inputs[role+'_acceptance'].read_bytes())
        insist(acceptance['generation_record']['sha256']==config['inputs'][role]['sha256'],'source_graph_mismatch')
    original_preference = parse(inputs['preference'].read_bytes())
    acceptance = parse(inputs['preference_acceptance'].read_bytes())
    insist(acceptance['status']=='accepted_ticket08_preference_trial_api_only'
            and acceptance['record_sha256']==config['inputs']['preference']['sha256'],'source_graph_mismatch')
    for role in ('catalog','tasks','evaluation'):
        insist(original_preference['components'][role]['sha256']==acceptance['component_sha256'][role]
                ==config['inputs']['preference_'+role]['sha256'],'source_graph_mismatch')
    selected = parse(inputs['selected'].read_bytes())
    cleaned = parse(inputs['cleaning'].read_bytes())
    insist(record['counts']['raw_comment_rows']==selected['scan']['matched_rows']==info_cache[inputs['raw_reviews']]['records']
            and record['counts']['clean_comment_rows']==cleaned['counts']['clean_reviews']==info_cache[inputs['clean_reviews']]['records'],
            'source_graph_mismatch')
    insist(record['formal_package_status']=='not_released' and record['sample_sufficiency']=='not_determined'
            and record['runtime_adapter_status']=='not_accepted' and record['execution_budget_status']=='unvalidated'
            and record['model_execution_status']=='not_run' and record['ledger_deployment_status']=='not_deployed',
            'invalid_joint_record')
    insist(set(record['producer_sha256'])=={'prepare_data.py','joint_tasks.py','joint_access.py'}
            and all(info(path(name))['sha256']==sha for name,sha in record['producer_sha256'].items()),'joint_producer_mismatch')


def associate_q(audit, config, inputs, tasks, evaluations):
    scenario_acceptance = parse(inputs['scenarios_acceptance'].read_bytes())
    quality_acceptance = parse(inputs['quality_acceptance'].read_bytes())
    insist(scenario_acceptance['independent_reference']['reference']['sha256']==config['inputs']['scenario_reference']['sha256']
            and quality_acceptance['validation']['independent_full_reference']['status']=='passed'
            and quality_acceptance['validation']['independent_full_reference']['evidence']['sha256']
                ==config['inputs']['quality_reference_summary']['sha256'],'reference_source_mismatch')
    for role,acceptance in (('scenarios',scenario_acceptance),('quality',quality_acceptance)):
        insist(acceptance['generation_record']['sha256']==config['inputs'][role]['sha256'],'reference_source_mismatch')
    normal = parse(inputs['normal'].read_bytes())
    batch_path = bound(normal['components']['batches.jsonl'],info_cache)
    batches = {v['parent_asin']:v['sim_batch_id'] for v,_ in entries(batch_path)}
    catalog = {v['parent_asin']:v for v,_ in entries(inputs['preference_catalog'])}
    insist(set(batches)==set(catalog),'candidate_batch_coverage')
    by_snapshot = {v['snapshot_id']:v for v in config['views']}
    by_view = {v['view_id']:v for v in config['views']}
    states = {v['label']:{} for v in config['views']}
    reference_rows = []
    for row,source in entries(inputs['scenario_reference']):
        if row['view_id'] not in by_view or row['request_profile_id']!='R1_AND_R5_SIM_Q1_ON_SALE':
            continue
        view = by_view[row['view_id']]
        parent = row['parent_asin']
        insist(view['arm']=='necessary' and row['snapshot_id']==view['snapshot_id']
                and parent in batches and row['sim_batch_id']==batches[parent],'reference_scope_mismatch')
        state = row['candidate_state']
        insist(state in ('Supported','Pending','Refuted','Conflict') and type(row['eligible']) is bool
                and row['eligible']==(state=='Supported') and parent not in states[view['label']],'reference_state_or_duplicate')
        states[view['label']][parent] = state
        reference_rows.append({'reference_version':VERSION,'material_version':view['material_version'],'view':view['view_id'],
            'snapshot':view['snapshot_id'],'profile':view['request_profile_id'],'parent':parent,'batch':batches[parent],
            'clauses':{'source_pointer':'/clauses'},'candidate_state':state,'eligible':row['eligible'],'source_reference_ref':source})
    qsummary = parse(inputs['quality_reference_summary'].read_bytes())
    insist(qsummary['status']=='passed' and qsummary['version']=='quality-reference-0.1.0'
            and qsummary['reference_sha256']==config['inputs']['quality_reference']['sha256'],'reference_scope_mismatch')
    quality_record = parse(inputs['quality'].read_bytes())
    quality_facts = {}
    for view in config['views']:
        if view['arm']!='quality':
            continue
        snapshot_file = bound(view['snapshot'],info_cache)
        snapshot = parse(snapshot_file.read_bytes())
        insist(snapshot['snapshot_id']==view['snapshot_id'] and snapshot['protocol_version']=='quality-preference-protocol-0.1.0',
                'reference_scope_mismatch')
        files = {}
        for name,expected in snapshot['components'].items():
            file = path(snapshot_file.parent/name)
            references = [ref for ref in quality_record['components'].values() if path(ref['path'])==file]
            insist(len(references)==1,'reference_scope_mismatch')
            bound(references[0],info_cache)
            insist(all(info_cache[file][k]==expected[k] for k in ('bytes','records','sha256')),'reference_scope_mismatch')
            files[name]=file
        insist(info_cache[files['actions.jsonl']]['bytes']==0,'reference_scope_mismatch')
        for name in ('batches.jsonl','events.jsonl','policy.json'):
            insist(info_cache[files[name]]['sha256']==normal['components'][name]['sha256'],'reference_scope_mismatch')
        for name in ('batches.jsonl','events.jsonl','materials.jsonl','registrations.jsonl'):
            insist(all(type(r.get('version')) is int and r['version']==1 for r,_ in entries(files[name])),
                    'reference_scope_mismatch')
        originals = {r['evidence_id']:r for r,_ in entries(files['materials.jsonl'])}
        registrations = {r['registration_id']:r for r,_ in entries(files['registrations.jsonl'])}
        events = {r['event_id']:r for r,_ in entries(files['events.jsonl'])}
        quality_facts[view['snapshot_id']] = (originals,registrations,events)
    for row,source in entries(inputs['quality_reference']):
        insist(row['snapshot_id'] in by_snapshot,'reference_scope_mismatch')
        view = by_snapshot[row['snapshot_id']]
        parent = row['parent_asin']
        insist(view['arm']=='quality' and parent in batches and parent not in states[view['label']]
                and row['eligible'] is True and type(row['z']) is int and row['z']==1
                and set(row['source_citations'])=={'inspection_sample','inspection_report','retail_status','transport_dispatch','transport_receipt'},
                'reference_scope_mismatch')
        originals,registrations,events = quality_facts[row['snapshot_id']]
        for kind,citation in row['source_citations'].items():
            insist(citation['evidence_id'] in originals and citation['registration_id'] in registrations
                    and citation['event_id'] in events,'reference_citation_mismatch')
            original = originals[citation['evidence_id']]
            registration = registrations[citation['registration_id']]
            event = events[citation['event_id']]
            insist(original['kind']==kind and original['parent_asin']==registration['parent_asin']==event['parent_asin']==parent
                    and original['sim_batch_id']==registration['sim_batch_id']==event['sim_batch_id']==batches[parent]
                    and original['event_id']==registration['event_id']==citation['event_id']
                    and registration['target_id']==citation['evidence_id']
                    and hashlib.sha256(wire(original)).hexdigest()==citation['sha256']==registration['content_sha256'],
                    'reference_citation_mismatch')
        states[view['label']][parent] = 'Supported'
        reference_rows.append({'reference_version':VERSION,'material_version':view['material_version'],'view':view['view_id'],
            'snapshot':view['snapshot_id'],'profile':view['request_profile_id'],'parent':parent,'batch':batches[parent],
            'clauses':{'c1':'Supported','c2':'Supported','mapping':'accepted_normal_v1_Q_only'},
            'candidate_state':'Supported','eligible':True,'source_reference_ref':source})
    insist(all(set(s)==set(catalog) for s in states.values()),'incomplete_reference_keys')
    with (audit/'sim-reference-index.jsonl').open('xb') as stream:
        for value in sorted(reference_rows,key=lambda r:tuple(r[k].encode() for k in ('material_version','view','profile','parent'))):
            stream.write(wire(value)+b'\n')
    p0 = parse(inputs['p0_aggregate'].read_bytes())
    insist(p0['reference_binding']['sha256']==config['inputs']['scenario_reference']['sha256']
            and p0['private_audit_components']['account-applicability.jsonl']['sha256']==config['inputs']['p0_applicability']['sha256'],
            'baseline_binding_mismatch')
    old_roots = set()
    for row,_ in entries(inputs['p0_applicability']):
        key = row['task_id']
        insist(key in evaluations and key not in old_roots and row['split']==evaluations[key]['split']
                and row['target_parent_asin']==evaluations[key]['target_parent_asin']
                and row['target_timestamp_ms']==evaluations[key]['target_timestamp_ms'],'baseline_binding_mismatch')
        old_roots.add(key)
    insist(old_roots==set(tasks),'baseline_binding_mismatch')
    applicable = set()
    groups = {'dev':[],'test':[]}
    with (audit/'q-applicability.jsonl').open('xb') as stream:
        for key in sorted(tasks):
            task, evaluation = tasks[key], evaluations[key]
            target = evaluation['target_parent_asin']
            group = evaluation['split']
            groups[group].append(key)
            for label in ('Q1','Q2'):
                for parent in task['candidate_parent_asins']:
                    insist(parent in states[label],'incomplete_reference_keys')
                state = states[label][target]
                view = next(v for v in config['views'] if v['label']==label)
                stream.write(wire({'reference_version':VERSION,'root':key,'group':group,'view':view['view_id'],
                    'snapshot':view['snapshot_id'],'profile':view['request_profile_id'],'target_parent':target,
                    'target_batch':batches[target],'IDCG_E':int(state=='Supported'),'applicable':state=='Supported',
                    'NA_reason':None if state=='Supported' else state,
                    'source_sha256':config['inputs']['quality_reference']['sha256']})+b'\n')
            if all(states[label][target]=='Supported' for label in ('Q1','Q2')):
                applicable.add(key)
    with (audit/'uq-mask.jsonl').open('xb') as stream:
        for key in sorted(tasks):
            stream.write(wire({'root':key,'applicable':key in applicable and evaluations[key]['split']=='test'})+b'\n')
    split_record = parse(inputs['split'].read_bytes())
    exposure_file = bound({'path':split_record['exposure_path'],'sha256':split_record['exposure_sha256']},info_cache)
    exposures = {r['user_id']:r for r,_ in entries(exposure_file)}
    insist(all(e['source_user_id'] in exposures for e in evaluations.values()),'missing_legacy_exposure')
    exposure = {key:exposures[e['source_user_id']] for key,e in evaluations.items()}
    insist(all(type(e['legacy_corpus_member']) is bool and e['agent_account_result_view'] in ('observed','unknown')
                and e['human_account_result_view'] in ('observed','unknown') for e in exposure.values()),'invalid_legacy_exposure')
    cover = {group:{'pool':coverage(ids,tasks,evaluations,catalog,exposure),
                    'UQ':coverage([k for k in ids if k in applicable],tasks,evaluations,catalog,exposure)} for group,ids in groups.items()}
    save(audit/'coverage.json',cover)
    n_q = sum(k in applicable for k in groups['test'])
    return {'nQ':n_q,'nQ_dev':sum(k in applicable for k in groups['dev']),
            'n8_from_P0':p0['groups']['test']['n_J_all_main_views'],'Q_pool':{g:len(ids) for g,ids in groups.items()},
            'Q_NA':{g:len(ids)-sum(k in applicable for k in ids) for g,ids in groups.items()},
            'planned_n_975_Q':'met' if n_q>=975 else 'planned_n_not_met','reference_rows':len(reference_rows),
            'planned_n_975_8':'met' if p0['groups']['test']['n_J_all_main_views']>=975 else 'planned_n_not_met',
            'Q_by_view':{label:{g:{'applicable':sum(states[label][evaluations[k]['target_parent_asin']]=='Supported' for k in ids),
                                   'NA':sum(states[label][evaluations[k]['target_parent_asin']]!='Supported' for k in ids)}
                                for g,ids in groups.items()} for label in ('Q1','Q2')},
            'P0_reused':config['inputs']['p0_aggregate'],'P0_recomputed':False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--record', required=True)
    parser.add_argument('--audit-root', required=True)
    args = parser.parse_args()
    audit = path(args.audit_root)
    insist(not audit.exists() or (audit.is_dir() and not any(audit.iterdir())),'audit_root_not_fresh')
    audit.mkdir(parents=True,exist_ok=True)
    try:
        record_path = path(args.record)
        record = parse(record_path.read_bytes())
        insist(record['status']=='joint_tasks_prepared' and record['schema_version']=='joint-record-0.1.0','invalid_joint_record')
        output = path(record['output_root'])
        insist(record_path==output/'records/joint-tasks'/(record['catalog_version']+'-'+record['package_version']+'.json'),'record_layout_mismatch')
        config = parse(bound(record['config'],info_cache).read_bytes())
        inputs = {role:bound(ref,info_cache) for role,ref in config['inputs'].items()}
        components = {name:bound({**ref,'path':(output/ref['path']).relative_to(ROOT).as_posix()},info_cache)
                      for name,ref in record['components'].items()}
        verify_sources(config,inputs,components,record)
        projection = verify_projection(config,inputs,components)
        insist(record['counts']['roots']==projection['all_root_projections_checked']
                and record['counts']['planned_view_bindings']==projection['all_root_projections_checked']*len(config['views']),
                'joint_count_mismatch')
        tasks = {}
        for row,source in entries(inputs['preference_tasks']):
            key = row['task_id']
            insist(key not in tasks,'duplicate_root')
            tasks[key] = {k:row[k] for k in ('history','history_cutoff_exclusive_ms','seen_parent_asins','candidate_parent_asins')}
        seen = set()
        evaluations = {}
        with (audit/'preference-reference.jsonl').open('xb') as stream:
            for value,source in entries(inputs['preference_evaluation']):
                key = value['task_id']
                insist(key in tasks and key not in seen,'preference_root_key_mismatch')
                seen.add(key)
                task = tasks[key]
                evaluations[key] = {k:value[k] for k in ('target_parent_asin','target_timestamp_ms','split','source_user_id')}
                target = value['target_parent_asin']
                insist(value['target_timestamp_ms']==task['history_cutoff_exclusive_ms']
                        and target in task['candidate_parent_asins'] and target not in task['seen_parent_asins']
                        and value['split'] in ('dev','test'),'preference_target_binding_mismatch')
                insist(value['target_review']['parent_asin']==target and value['target_rating']>=4
                        and value['reference_answer']=={'positive_parent_asins':[target],'other_candidates':'unobserved_unlabeled'},
                        'preference_source_mismatch')
                stream.write(wire({'reference_version':VERSION,'root':key,'group':value['split'],
                    'target_parent':target,'T':value['target_timestamp_ms'],'source_ref':source})+b'\n')
        insist(seen==set(tasks),'missing_preference_root')
        association = associate_q(audit,config,inputs,tasks,evaluations)
        result = {'status':'passed_joint_association_only','reference_version':VERSION,'roots':len(tasks),
                  **association,
                  'projection_validation':projection,
                  'sample_sufficiency':'not_determined','model_API_calls':0,
                  'components':{p.name:info(p) for p in audit.iterdir() if p.is_file()},
                  'program':info(Path(__file__).resolve()),'record':info(record_path)}
        save(audit/'check.json',result)
        print(json.dumps({'status':result['status'],'roots':len(tasks),'nQ':result['nQ'],'n8_from_P0':result['n8_from_P0']},sort_keys=True))
        return 0
    except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError):
        error = sys.exception()
        code = str(error) if isinstance(error,ValueError) else type(error).__name__
        save(audit/'failure-check.json',{'status':'failed','code':code,'complete_reference':False})
        print(json.dumps({'status':'joint_reference_incomplete','error':{'code':code}},sort_keys=True))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
