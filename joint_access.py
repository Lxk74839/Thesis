"""Pure joint data-session dispatch: no filesystem, network, index or model calls."""
import hashlib
import json


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


class JointSession:
    def __init__(self, root, candidates, catalog, view, handle):
        self.root = root
        self.candidates = candidates
        self.products = {p['parent_asin']:p for p in catalog}
        quality = view['arm']=='quality'
        payload = {**root, 'session_handle':handle, 'K':10, 'verify_at_ms':1791417600000,
            'request':{'source':'experiment_design','text':view['request']['design_text'],
                       'necessary_clauses':view['request']['necessary_clauses']},
            'source_disclosure':'SIM','alpha':.5 if quality else 1,'beta':[.25,.5,.25],
            'preference':{'source':'experiment_design','dimensions':['retail_stock'] if quality else [],
                          'weights':{'retail_stock':1} if quality else {}},
            'tool_version':'pending','model_version':'pending','prompt_version':'pending'}
        payload['input_fingerprint']=hashlib.sha256(encoded(payload)).hexdigest()
        self.request = {'messages':[{'role':'user','content':encoded(payload).decode()}],'tools':[]}
        by_parent = dict(zip(candidates['C'],candidates['b']))
        self.orders = {'parent':candidates['C'], 'base':sorted(candidates['C'],key=lambda p:(-by_parent[p],p.encode()))}
        self.cursors = {hashlib.sha256(encoded([handle,order,offset])).hexdigest():(order,offset)
                        for order in self.orders for offset in range(32,len(candidates['C']),32)}

    def dispatch(self, operation, arguments):
        denied = {'status':'access_denied'}
        if operation=='model_request' and arguments=={}:
            return {'status':'ok','request':self.request}
        if operation!='candidate_page' or set(arguments)!={'order','cursor'}:
            return denied
        order, cursor = arguments['order'], arguments['cursor']
        if not isinstance(order,str) or order not in self.orders:
            return denied
        if cursor is None:
            offset = 0
        elif not isinstance(cursor,str) or cursor not in self.cursors or self.cursors[cursor][0]!=order:
            return denied
        else:
            offset = self.cursors[cursor][1]
        parents = self.orders[order][offset:offset+32]
        positions = {p:i for i,p in enumerate(self.candidates['C'])}
        page = [{**self.products[p], 'sim_batch_id':self.candidates['batches'][positions[p]],
                 'base_score':self.candidates['b'][positions[p]],
                 'background_statistics':self.candidates['background_statistics'][positions[p]]} for p in parents]
        next_offset = offset+32
        next_cursor = next((token for token,pair in self.cursors.items() if pair==(order,next_offset)),None)
        return {'status':'ok','candidates':page,'total_candidates':len(self.candidates['C']), 'next_cursor':next_cursor}
