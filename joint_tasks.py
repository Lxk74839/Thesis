"""Joint preparation behind prepare_data.py; upstream data is immutable."""
from datetime import datetime, timezone
from collections import Counter, defaultdict
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import stat
import sys
import subprocess
import tempfile
import unicodedata
import uuid
from joint_access import JointSession

ROOT = Path(__file__).resolve().parent
PACKAGE = 'joint-task-package-0.1.0'
CONTRACT = 'd279bbeda1e406569e2c186e23988a3402a8946cab3ba8dee2a716ad76056221'
PROFILE = 'R1_AND_R5_SIM_Q1_ON_SALE'
INPUTS = set('catalog selected cleaning cleaning_acceptance cleaning_erratum split split_acceptance preference preference_acceptance normal normal_acceptance scenarios scenarios_acceptance quality quality_acceptance preference_catalog preference_tasks preference_evaluation preference_audit preference_model_manifest identity_key raw_reviews review_sources clean_reviews clean_audit clean_accounts scenario_reference quality_reference quality_reference_summary p0_aggregate p0_applicability'.split())


def require(condition, code='binding_mismatch'):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(content):
    return hashlib.sha256(content).hexdigest()


def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'invalid_config')
        value[key] = item
    return value


def decode(content):
    return json.loads(content, object_pairs_hook=unique,
                      parse_constant=lambda _: require(False, 'invalid_config'))


def project_path(value):
    path = Path(os.path.abspath(ROOT / value))
    require(path == ROOT or ROOT in path.parents, 'invalid_path')
    for ancestor in (path, *path.parents):
        require(not ancestor.is_symlink() and not ancestor.is_junction(), 'invalid_path')
        if ancestor.exists():
            require(not getattr(ancestor.lstat(),'st_file_attributes',0) & stat.FILE_ATTRIBUTE_REPARSE_POINT, 'invalid_path')
    return path


def file_info(path):
    sha = hashlib.sha256()
    size = count = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            sha.update(block)
            size += len(block)
            count += block.count(b'\n')
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': size, 'records': count, 'sha256': sha.hexdigest()}


def checked(binding, cache):
    require(isinstance(binding, dict) and {'path','sha256'} <= binding.keys(), 'invalid_baseline')
    path = project_path(binding['path'])
    if path not in cache:
        cache[path] = file_info(path)
    actual = cache[path]
    require(all(binding[k] == actual[k] for k in ('sha256','bytes','records') if k in binding), 'invalid_baseline')
    return path


def rows(path):
    with path.open('rb') as stream:
        for line in stream:
            yield decode(line)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(canonical(value)+b'\n')


def write_rows(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        for value in values:
            stream.write(canonical(value)+b'\n')


def grams(text):
    text = ' '.join(unicodedata.normalize('NFKC', text).casefold().split())
    return Counter(text[i:i+3] for i in range(len(text)-2)) if len(text)>=3 else Counter({text:1}) if text else Counter()


def text_vector(counts, idf):
    values = {g:(1+math.log(counts[g]))*idf[g] for g in sorted(counts) if g in idf}
    norm = math.sqrt(math.fsum(v*v for v in values.values()))
    return {g:v/norm for g,v in values.items()} if norm else {}


def directory_vectors(catalog):
    documents = {r['parent_asin']:grams(r['title']+' '+r['crop']) for r in catalog}
    df = Counter(g for doc in documents.values() for g in doc)
    idf = {g:math.log((len(catalog)+1)/(df[g]+1))+1 for g in sorted(df)}
    vocabulary_sha = digest(canonical([(g,df[g],idf[g]) for g in idf]))
    return idf, {p:text_vector(doc,idf) for p,doc in documents.items()}, vocabulary_sha


def score_history(task, products, idf, vectors):
    combined = defaultdict(float)
    for event in task['history']:
        product = products[event['parent_asin']]
        vector = text_vector(grams(' '.join((event['text'],product['title'],product['crop']))),idf)
        for g,v in vector.items():
            combined[g] += event['rating']/5*v
    norm = math.sqrt(math.fsum(combined[g]**2 for g in sorted(combined)))
    profile = {g:combined[g]/norm for g in sorted(combined)} if norm else {}
    candidates = task['candidate_parent_asins']
    raw = [round(math.fsum(v*profile.get(g,0) for g,v in vectors[p].items()),12) for p in candidates]
    low, high = min(raw,default=0), max(raw,default=0)
    scores = [round((v-low)/(high-low),12) if high!=low else .5 for v in raw]
    by_parent = dict(zip(candidates,scores))
    return {'root_task_id':task['task_id'],'C':candidates,'b_raw':raw,'b':scores,
            'score_version':'char3-tfidf-history-1.0.0','profile_zero':not profile,
            'base_scores_sha256':digest(canonical(list(zip(candidates,scores)))),
            'history_sha256':digest(canonical(task['history'])),
            'access_order':sorted(candidates,key=lambda p:(-by_parent[p],p.encode()))}


def validate_task(task, parents):
    require(task['schema_version']=='preference-model-input-1.0.0'
            and task['text_policy_version']=='finite-text-1.0.0'
            and task['metadata_time_basis']=='collection_snapshot')
    root = task['task_id']
    require(isinstance(root,str) and len(root)==64 and all(c in '0123456789abcdef' for c in root))
    time = task['history_cutoff_exclusive_ms']
    require(type(time) is int and isinstance(task['history'],list) and bool(task['history']))
    seen = task['seen_parent_asins']
    candidates = task['candidate_parent_asins']
    require(seen==sorted(set(seen),key=lambda p:p.encode()) and set(seen)<=set(parents))
    require(candidates==[p for p in parents if p not in set(seen)])
    for event in task['history']:
        require(set(event)=={'parent_asin','timestamp_ms','rating','text'}
                and event['parent_asin'] in seen and type(event['timestamp_ms']) is int
                and event['timestamp_ms']<time and type(event['rating']) in (float,int)
                and event['rating'] in (4,5) and isinstance(event['text'],str) and bool(event['text'].strip()))
    require([r['parent_asin'] for r in task['background_statistics']]==candidates)
    for stat in task['background_statistics']:
        require(set(stat)=={'parent_asin','interaction_count','account_count','positive_account_count'}
                and all(type(stat[k]) is int and stat[k]>=0 for k in ('interaction_count','account_count','positive_account_count'))
                and stat['positive_account_count']<=stat['account_count']<=stat['interaction_count'])


def validate_config(cfg):
    require(set(cfg)==set('schema_version package_version model_schema base_score_version catalog_version approval inputs views verify_at_ms principal_id page_size K budget serialization runtime'.split()), 'invalid_config')
    require(cfg['model_schema']=='joint-model-input-0.1.0' and cfg['base_score_version']=='char3-tfidf-history-1.0.0'
            and cfg['catalog_version']=='grain-A-1.1.15' and cfg['serialization']=='json-utf8-lf-sortkeys-finite-0.1.0', 'invalid_config')
    require(set(cfg['inputs'])==INPUTS and set(cfg['approval'])=={'contract','authorization','protocol','protocol_confirmation'},'invalid_config')
    require(cfg['runtime']=={'python':'3.13.16','environment':'Thesis'}
            and Path(sys.prefix).resolve()==ROOT/'.conda/envs/Thesis' and sys.version.split()[0]=='3.13.16', 'invalid_config')
    require(all(type(cfg[k]) is int for k in ('verify_at_ms','page_size','K'))
            and (cfg['verify_at_ms'],cfg['page_size'],cfg['K'],cfg['principal_id'])==(1791417600000,32,10,'SIM-VERIFIER'), 'invalid_config')
    candidate = {'logical_tools':2048,'physical_tools':256,'model_calls':12,'input_tokens':96000,
                 'output_tokens':12000,'retries':2,'candidates':64,'elapsed_ms':600000}
    require(cfg['budget']=={'validation':'pending','execution_budget':None,'execution_authorized':False,'candidate':candidate}
            and type(cfg['budget']['execution_authorized']) is bool
            and all(type(v) is int for v in cfg['budget']['candidate'].values()), 'invalid_config')
    require([v['label'] for v in cfg['views']]==['V00','V01','V03','V05','V06','V07','V09','V12','Q1','Q2'], 'invalid_config')
    for view in cfg['views']:
        require(set(view)=={'label','arm','material_version','view_id','snapshot','snapshot_id','request_profile_id'}
                and view['arm']==('quality' if view['label'].startswith('Q') else 'necessary')
                and view['material_version']==('sim-quality-fusion-0.1.0' if view['arm']=='quality' else 'sim-scenarios-1.0.0'), 'invalid_config')


def prepare_joint(config_path, output_root, access_probe=None):
    try:
        cache = {}
        config_path = project_path(config_path)
        cfg = decode(config_path.read_bytes())
        validate_config(cfg)
        require(cfg['schema_version'] == 'joint-config-0.1.0' and cfg['package_version'] == PACKAGE, 'invalid_config')
        require(cfg['approval']['contract']['sha256'] == CONTRACT, 'unapproved_protocol')
        for binding in cfg['approval'].values():
            checked(binding, cache)
        inputs = {key: checked(binding, cache) for key,binding in cfg['inputs'].items()}
        preference = decode(inputs['preference'].read_bytes())
        preference_acceptance = decode(inputs['preference_acceptance'].read_bytes())
        require(preference_acceptance['status']=='accepted_ticket08_preference_trial_api_only'
                and preference_acceptance['record_sha256']==cfg['inputs']['preference']['sha256'], 'invalid_baseline')
        for name in ('catalog','tasks','evaluation'):
            require(preference['components'][name]['sha256']==cfg['inputs']['preference_'+name]['sha256']
                    ==preference_acceptance['component_sha256'][name], 'invalid_baseline')
        for role in ('normal','scenarios','quality','cleaning','split'):
            require(decode(inputs[role+'_acceptance'].read_bytes())['status'].startswith('accepted'), 'invalid_baseline')
        source_components = {role:dict(cache[p]) for role,p in inputs.items()}
        for role in ('catalog','selected','cleaning','split'):
            source_record = decode(inputs[role].read_bytes())
            for key,value in source_record.items():
                digest_key = key[:-5]+'_sha256' if key.endswith('_path') else ''
                if digest_key in source_record and isinstance(value,str):
                    source_path = checked({'path':value,'sha256':source_record[digest_key]},cache)
                    source_components[role+':'+key] = dict(cache[source_path])
        selected = decode(inputs['selected'].read_bytes())
        cleaning = decode(inputs['cleaning'].read_bytes())
        raw_count = cache[inputs['raw_reviews']]['records']
        clean_count = cache[inputs['clean_reviews']]['records']
        require(selected['extract_path']==cfg['inputs']['raw_reviews']['path']
                and selected['extract_sha256']==cfg['inputs']['raw_reviews']['sha256']
                and selected['scan']['matched_rows']==raw_count
                and cleaning['source_extract_sha256']==cfg['inputs']['raw_reviews']['sha256']
                and cleaning['counts']['clean_reviews']==clean_count,'invalid_baseline')
        probes = list(rows(project_path(access_probe))) if access_probe else []
        require(all(set(p)=={'session_task_id','operation','arguments'} and isinstance(p['session_task_id'],str)
                    and isinstance(p['operation'],str) and isinstance(p['arguments'],dict) for p in probes), 'invalid_arguments')
        probe_by_session = defaultdict(list)
        for i,p in enumerate(probes):
            probe_by_session[p['session_task_id']].append((i,p))
        probe_results = [{'status':'access_denied'} for _ in probes]
        identity_key = inputs['identity_key'].read_bytes()
        require(len(identity_key)==32, 'invalid_baseline')
        records = {role:decode(inputs[role].read_bytes()) for role in ('normal','scenarios','quality')}
        for record in records.values():
            for binding in record['components'].values():
                checked(binding,cache)
        request_rows = list(rows(checked(records['scenarios']['components']['requests.jsonl'],cache)))
        request = next(r for r in request_rows if r['profile_id']==PROFILE)
        require(request['source']=='experiment_design')
        for view in cfg['views']:
            record = records['quality' if view['arm']=='quality' else 'scenarios']
            require(any(info['path']==view['snapshot']['path'] and info['sha256']==view['snapshot']['sha256']
                        for info in record['components'].values()),'invalid_baseline')
            snapshot = decode(checked(view['snapshot'],cache).read_bytes())
            require(snapshot['snapshot_id']==view['snapshot_id'] and snapshot['verify_at_ms']==cfg['verify_at_ms']
                    and snapshot['read_principal_id']==cfg['principal_id'] and view['request_profile_id']==PROFILE)
        catalog = list(rows(inputs['preference_catalog']))
        require(all(set(p)=={'parent_asin','title','crop'} and all(isinstance(v,str) and v for v in p.values()) for p in catalog))
        products = {p['parent_asin']:p for p in catalog}
        idf, vectors, vocabulary_sha = directory_vectors(catalog)
        normal = decode(inputs['normal'].read_bytes())
        batches = list(rows(checked(normal['components']['batches.jsonl'], cache)))
        parents = [r['parent_asin'] for r in catalog]
        require(parents==sorted(set(parents),key=lambda p:p.encode()))
        mapping = {r['parent_asin']:r['sim_batch_id'] for r in batches}
        require(len(mapping) == len(batches) == len(parents) and set(mapping) == set(parents))
        output = project_path(output_root)
        require(output==ROOT or (not any(output==p.parent or output in p.parents or p.parent in output.parents for p in cache)
                and not any(output==ROOT/name or ROOT/name in output.parents for name in ('research','manuscript'))), 'invalid_path')
        final = project_path(output/'data/joint-tasks'/cfg['catalog_version']/PACKAGE)
        record_path = project_path(output/'records/joint-tasks'/(cfg['catalog_version']+'-'+PACKAGE+'.json'))
        producer = {name:file_info(ROOT/name)['sha256'] for name in ('prepare_data.py','joint_tasks.py','joint_access.py')}
        fingerprint = digest(canonical({'config':file_info(config_path)['sha256'],'producer':producer,
            'probe':file_info(project_path(access_probe))['sha256'] if access_probe else None}))
        reuse = final.exists() or record_path.exists()
        if reuse:
            require(final.is_dir() and record_path.is_file(), 'output_conflict')
            old = decode(record_path.read_bytes())
            require(old.get('reuse_fingerprint_sha256')==fingerprint, 'output_conflict')
        with tempfile.TemporaryDirectory(dir=project_path(ROOT/'.tmp')) as temp:
            stage = Path(temp)/'bundle'
            stage.mkdir()
            write_rows(stage/'candidate-map.jsonl', [{'parent_asin':p,'sim_batch_id':mapping[p]} for p in parents])
            root_count = 0
            root_ids = set()
            (stage/'model').mkdir()
            (stage/'private').mkdir()
            write_rows(stage/'model/catalog.jsonl',catalog)
            def roots():
                nonlocal root_count
                for task in rows(inputs['preference_tasks']):
                    validate_task(task,parents)
                    require(task['task_id'] not in root_ids)
                    root_ids.add(task['task_id'])
                    root_count += 1
                    score = score_history(task,products,idf,vectors)
                    score_stream.write(canonical(score)+b'\n')
                    root_input_sha = digest(canonical({k:task[k] for k in task if k!='request'}))
                    model_root = {'schema_version':'joint-model-input-0.1.0','root_task_id':task['task_id'],
                        'history':task['history'],'seen_parent_asins':task['seen_parent_asins'],
                        'history_cutoff_exclusive_ms':task['history_cutoff_exclusive_ms'],
                        'metadata_time_basis':'collection_snapshot','text_policy_version':'finite-text-1.0.0',
                        'catalog_version':cfg['catalog_version'],'candidate_count':len(score['C']),
                        'C_sha256':digest(canonical(score['C'])),'H_sha256':score['history_sha256'],
                        'base_scores_sha256':score['base_scores_sha256'],'score_version':score['score_version']}
                    model_candidates = {'root_task_id':task['task_id'],'C':score['C'],'b':score['b'],
                        'batches':[mapping[p] for p in score['C']], 'background_statistics':task['background_statistics']}
                    model_root_stream.write(canonical(model_root)+b'\n')
                    model_candidate_stream.write(canonical(model_candidates)+b'\n')
                    for view in cfg['views']:
                        quality = view['arm']=='quality'
                        binding = {'root_task_id':task['task_id'],'root_input_sha256':root_input_sha,
                            'H_sha256':score['history_sha256'],'C_sha256':digest(canonical(score['C'])),
                            'base_scores_sha256':score['base_scores_sha256'],'score_version':score['score_version'],
                            'candidate_map_sha256':digest(canonical(mapping)),**view,'request':request,
                            'K':cfg['K'],'verify_at_ms':cfg['verify_at_ms'],'principal_id':cfg['principal_id'],
                            'alpha':.5 if quality else 1,'beta':[.25,.5,.25],
                            'preference':{'source':'experiment_design','dimensions':['retail_stock'] if quality else [],
                                          'weights':{'retail_stock':1} if quality else {}},
                            'stop_rule':'fixed_candidate_prefix' if quality else 'first_10_supported',
                            'planned_methods':['M'] if quality else ['R','S','M'],
                            'budget_candidate':cfg['budget']['candidate'],'execution_budget':None,
                            'execution_authorized':False,'tool_version':'pending','model_version':'pending',
                            'prompt_version':'pending'}
                        binding['common_binding_sha256']=digest(canonical(binding))
                        view_stream.write(canonical(binding)+b'\n')
                        handle = hmac.new(identity_key,b'Thesis:joint-session-0.1.0\0'+canonical([
                            task['task_id'],view['material_version'],view['snapshot_id'],view['request_profile_id']]),hashlib.sha256).hexdigest()
                        session_stream.write(canonical({'session_handle':handle,'root_task_id':task['task_id'],
                            'view_id':view['view_id'],'snapshot_id':view['snapshot_id']})+b'\n')
                        selected = list(probe_by_session.get(handle,[]))
                        if view is cfg['views'][0]:
                            selected += probe_by_session.get(task['task_id'],[])
                        if selected:
                            session = JointSession(model_root,model_candidates,catalog,binding,handle)
                            for i,probe in selected:
                                probe_results[i]=session.dispatch(probe['operation'],probe['arguments'])
                    yield {'root_task_id':task['task_id'],'history':task['history'],
                           'history_cutoff_exclusive_ms':task['history_cutoff_exclusive_ms'],
                           'seen_parent_asins':task['seen_parent_asins'],'C':task['candidate_parent_asins'],
                           'H_sha256':score['history_sha256'],'C_sha256':digest(canonical(score['C'])),
                           'base_scores_sha256':score['base_scores_sha256'],'root_input_sha256':root_input_sha}
            with (stage/'base-scores.jsonl').open('xb') as score_stream, (stage/'view-bindings.jsonl').open('xb') as view_stream, \
                    (stage/'model/roots.jsonl').open('xb') as model_root_stream, \
                    (stage/'model/candidates.jsonl').open('xb') as model_candidate_stream, \
                    (stage/'private/session-map.jsonl').open('xb') as session_stream:
                write_rows(stage/'roots.jsonl', roots())
            write_rows(stage/'private/access-probe.jsonl', [{'probe':p,'response':r} for p,r in zip(probes,probe_results)])
            write_json(stage/'model/manifest.json',{'schema_version':'joint-model-input-0.1.0',
                'components':{p.name:{'bytes':p.stat().st_size,'sha256':file_info(p)['sha256']}
                              for p in sorted((stage/'model').iterdir())}})
            write_json(stage/'package-manifest.json', {'schema_version':'joint-package-0.1.0',
                'package_version':PACKAGE,'sources':cfg['inputs'],'views':cfg['views'],
                'source_components':source_components,
                'upstream_components':{role:record['components'] for role,record in records.items()},
                'upstream_reused_semantics':True})
            components = {p.relative_to(stage).as_posix(): {**file_info(p),'path':(final/p.relative_to(stage)).relative_to(output).as_posix()}
                          for p in stage.rglob('*') if p.is_file()}
            if reuse:
                require(set(old['components'])==set(components), 'output_conflict')
                require({p.relative_to(final).as_posix() for p in final.rglob('*') if p.is_file()}==set(components), 'output_conflict')
                for name,info in components.items():
                    original = old['components'][name]
                    actual = file_info(project_path(final/name))
                    require(all(info[k]==original[k]==actual[k] for k in ('bytes','records','sha256'))
                            and info['path']==original['path'], 'output_conflict')
                print(canonical(old).decode())
                return 0
            final.parent.mkdir(parents=True, exist_ok=True)
            stage.rename(final)
        record = {'stage':'joint_tasks','schema_version':'joint-record-0.1.0','status':'joint_tasks_prepared',
                  'package_version':PACKAGE,'catalog_version':cfg['catalog_version'],
                  'counts':{'roots':root_count,'parents':len(parents),'business_batches':len(mapping),
                            'planned_view_bindings':root_count*len(cfg['views']),
                            'raw_comment_rows':raw_count,'clean_comment_rows':clean_count},
                  'components':components,'output_root':output.relative_to(ROOT).as_posix(),
                  'config':file_info(config_path),'independent_acceptance':'pending_separate_record',
                  'producer_sha256':producer,'reuse_fingerprint_sha256':fingerprint,
                  'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  'worktree_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),
                  'runtime':{'python_version':sys.version.split()[0],'conda_prefix':sys.prefix},
                  'score_contract':{'version':cfg['base_score_version'],'vocabulary_sha256':vocabulary_sha,
                                    'unicode_version':unicodedata.unidata_version},
                  'formal_package_status':'not_released','sample_sufficiency':'not_determined',
                  'runtime_adapter_status':'not_accepted','execution_budget_status':'unvalidated',
                  'model_execution_status':'not_run','ledger_deployment_status':'not_deployed',
                  'generated_at_utc':datetime.now(timezone.utc).isoformat()}
        write_json(record_path, record)
        print(canonical(record).decode())
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration, AttributeError):
        error = sys.exception()
        allowed = {'invalid_arguments','unapproved_protocol','invalid_config','invalid_path','invalid_baseline',
                   'binding_mismatch','unsafe_model_view','publication_incomplete','output_conflict'}
        code = str(error) if isinstance(error, ValueError) and str(error) in allowed else 'publication_incomplete'
        failure = {'stage':'joint_tasks','status':'joint_tasks_incomplete','error':{'code':code}}
        failure_path = project_path(ROOT/'data/joint-audit'/PACKAGE/'failures'/str(uuid.uuid4())/'failure.json')
        write_json(failure_path, {**failure,'exception_type':type(error).__name__})
        failure['failure_record']=failure_path.relative_to(ROOT).as_posix()
        print(canonical(failure).decode())
        return 2
