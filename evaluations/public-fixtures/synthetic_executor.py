"""Transparent fixture for timer/protocol tests, not a real editorial agent.

All topical inputs come from the private test workspace. No live platform calls.
"""
import hashlib,json,sys,sqlite3
from pathlib import Path
from xml.sax.saxutils import escape
r=json.load(sys.stdin);root=Path(r['workspace']);j=r['job'];publication=r['publication_id'];kind=j['kind']
def load(n,default=None):
 p=root/n;return json.loads(p.read_text()) if p.exists() else default
def save(n,d):(root/n).write_text(json.dumps(d,ensure_ascii=False,indent=2))
def digest(d):return hashlib.sha256(json.dumps(d,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
result={'publication_id':publication,'state':'completed','simulation':True,'method_evidence':'deterministic supplied-source protocol fixture; not model-generated editorial evidence'}
if kind=='article-production':
 brief=load('fixture-brief.json');sources=load('fixture-sources.json',[])
 if not brief or not sources:result.update(state='blocked',reason='No supplied brief/evidence')
 else:
  selected=[s for s in sources if s['topic'] in brief['topics'] and s.get('verified')]
  if not selected:result.update(state='no-op',reason='No supported relevant candidate')
  else:
   # Assemble a new source-attributed digest at each occurrence from supplied source records.
   title=brief['title'];body=title+'\n\n'+'\n\n'.join(s['finding']+' [Source: '+s['id']+']' for s in selected)
   text=root/'synthetic-article.md';text.write_text(body)
   svg=root/'synthetic-header.svg';svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"><rect width="1200" height="630" fill="'+brief['background']+'"/><text x="80" y="300" fill="'+brief['foreground']+'" font-size="48">'+escape(title)+'</text><text x="80" y="550" fill="'+brief['foreground']+'" font-size="24">SYNTHETIC PROTOCOL TEST</text></svg>')
   package={'title':title,'body':body,'evidence_ids':[s['id'] for s in selected],'review_passed':all(s['verified'] for s in selected),'visuals':[{'path':str(svg),'sha256':hashlib.sha256(svg.read_bytes()).hexdigest(),'required':True,'rights':'cleared','review':'approved','anchor':'header','representation':'synthetic original typesetting'}],'content_hash':digest(body),'simulation':True}
   save('fixture-package.json',package);result.update(artifacts=[str(text),str(svg)],stages=['supplied-source-selection','claim-linked-digest-writing','file-render-preparation','deterministic-review','package'])
elif kind in ('article-publication','native-social'):
 package=load('fixture-package.json')
 if not package:result.update(state='blocked',reason='No ready package')
 else:
  if kind=='native-social':
   text=package['title']+' — '+package['body'].split('\n\n')[1];operation='social';visuals=[]
  else:text=package['body'];operation='article';visuals=package['visuals']
  result['actions']=[{'publication_id':publication,'account':j['account'],'operation':operation,'target':'own','source_event':None,'content':text,'content_hash':digest(text),'authorization_ref':'fixture-authority','review_passed':package['review_passed'],'visuals':visuals,'context_hash':None,'current_context_hash':None,'reserved_cost':{'actions':1,'api_calls':1,'tokens':0,'spend':0}}]
  if kind=='native-social':
   db=sqlite3.connect(root/'runtime.sqlite');canonical=None
   for payload,receipt in db.execute("SELECT payload,receipt FROM actions WHERE state='confirmed'"):
    a=json.loads(payload)
    if a['operation']=='article' and a['content_hash']==package['content_hash']:canonical=json.loads(receipt)
   db.close();result['actions'][0].update(requires_canonical=True,canonical_receipt=canonical or {})
elif kind=='incoming-check':
 events=load('fixture-incoming.json',[]);result.update(observations=[{'account':j['account'],'events':events,'cursor':len(events)}],state='completed' if events else 'no-op')
elif kind in ('reply-processing','conversation-follow-up','community-participation'):
 context=load('fixture-conversations.json',[]);actions=[];decisions=[]
 for c in context:
  if c.get('workflow')!=kind:continue
  if c.get('opt_out') or c.get('human_answered') or not c.get('root_text') or not c.get('draft'):
   decisions.append({'event':c['id'],'decision':'no-response','reason':'opt-out, human response or incomplete context'});continue
  actions.append({'publication_id':publication,'account':j['account'],'operation':'reply','target':c['id'],'source_event':c['id'],'content':c['draft'],'content_hash':digest(c['draft']),'authorization_ref':'fixture-authority','review_passed':True,'visuals':[],'context_hash':digest(c['root_text']),'current_context_hash':digest(c['root_text']),'reserved_cost':{'actions':1,'api_calls':1,'tokens':0,'spend':0}})
 result.update(actions=actions,decisions=decisions,state='completed' if actions else 'no-op')
elif kind=='measurement':result.update(observations_available=False,value=None,reason='No real audience data in this fixture')
elif kind=='learning-review':result.update(state='no-op',decision='inconclusive',reason='Runtime conformance alone cannot prove editorial improvement')
elif kind=='health-check':result.update(state='completed',reason='Timer invoked health workflow; store supplies observed runtime status')
print(json.dumps(result,ensure_ascii=False))
