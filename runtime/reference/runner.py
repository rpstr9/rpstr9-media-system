"""Private, provider-neutral reference runner. No live adapter is bundled."""
from __future__ import annotations
import argparse, hashlib, json, os, signal, sqlite3, subprocess, sys, time, uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

KINDS={'article-production','article-publication','native-social','incoming-check','reply-processing','community-participation','conversation-follow-up','measurement','learning-review','health-check'}
FINAL={'completed','no-op','skipped','cancelled'}
def digest(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def stamp():return datetime.now(timezone.utc).isoformat()
class Hold(Exception):pass

def validate_plan(plan):
 if plan.get('schema_version')!='1.0':raise ValueError('Unsupported operating-plan schema')
 if not plan.get('publication_id') or not plan.get('library_release'):raise ValueError('Publication and library release are required')
 ids=set()
 for j in plan.get('jobs',[]):
  if j['id'] in ids:raise ValueError('Duplicate job ID')
  ids.add(j['id'])
  if j['kind'] not in KINDS:raise ValueError('Unknown job kind')
  if not isinstance(j.get('version'),int) or j['version']<1:raise ValueError('Positive job version required')
  if not j.get('enabled'):continue
  ZoneInfo(j['timezone'])
  t=j['trigger'];kind=t.get('kind')
  if kind=='interval':
   if t['seconds']<=0 or not isinstance(t['anchor'],(int,float)):raise ValueError('Interval and UTC anchor required')
  elif kind=='calendar':
   datetime.strptime(t['time'],'%H:%M')
   if not t.get('weekdays') or any(x not in range(7) for x in t['weekdays']):raise ValueError('Calendar weekdays required')
   if t.get('dst_fold') not in ('first','second','both') or t.get('dst_gap')!='skip':raise ValueError('Explicit DST policy required; skipped times support skip')
  else:raise ValueError('Only interval/calendar timers are supported')
  if j.get('mode') not in ('draft-only','review-before-send','bounded-auto'):raise ValueError('Execution mode required')
  if j.get('missed') not in ('coalesce-latest','skip','review'):raise ValueError('Missed-run policy required')
  if j.get('overlap') not in ('coalesce-latest','buffer-one'):raise ValueError('Overlap policy required')
  if j.get('freshness_seconds',0)<=0 or j.get('timeout_seconds',0)<=0:raise ValueError('Freshness and timeout required')
  if j.get('max_attempts',0)<1 or j.get('backoff_seconds',0)<0:raise ValueError('Bounded retry policy required')
  for key in ('actions','api_calls','tokens','spend'):
   if j.get('budget',{}).get(key,-1)<0:raise ValueError('Explicit nonnegative job budget required')
  executor=j.get('executor')
  if not (isinstance(executor,list) and executor and all(isinstance(x,str) for x in executor)) and not (isinstance(executor,dict) and executor.get('kind')=='host-computer-use'):raise ValueError('An authorized argv executor or host-computer-use route is required')
 return plan

def slots(job,after,now):
 """Resolve bounded timer slots. Calendar scans are capped; long gaps coalesce."""
 t=job['trigger'];start=max(after,job.get('start_at',after));end=min(now,job.get('end_at',now))
 if end<start:return []
 if t['kind']=='interval':
  a=t['anchor'];s=t['seconds'];first=max(0,int((start-a)//s)+1);last=int((end-a)//s)
  if last<first:return []
  # We never replay a backlog as a burst. Last slot is sufficient for all supported missed policies.
  return [a+last*s]
 tz=ZoneInfo(job['timezone']);day=datetime.fromtimestamp(max(start,end-370*86400),tz).date();lastday=datetime.fromtimestamp(end,tz).date();found=[]
 hh,mm=map(int,t['time'].split(':'))
 while day<=lastday:
  if day.weekday() in t['weekdays']:
   naive=datetime(day.year,day.month,day.day,hh,mm)
   candidates=[]
   for fold in (0,1):
    local=naive.replace(tzinfo=tz,fold=fold);utc=local.timestamp();back=datetime.fromtimestamp(utc,tz)
    if back.replace(tzinfo=None)==naive and utc not in candidates:candidates.append(utc)
   candidates.sort()
   if t['dst_fold']=='first':candidates=candidates[:1]
   elif t['dst_fold']=='second':candidates=candidates[-1:]
   found.extend(x for x in candidates if start<x<=end)
  day+=timedelta(days=1)
 return sorted(found)[-1:]

class Store:
 def __init__(self,root,publication=None):
  self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
  self.db=sqlite3.connect(self.root/'runtime.sqlite',timeout=30,isolation_level=None)
  self.db.row_factory=sqlite3.Row
  self.db.executescript('''PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,version INTEGER,config TEXT,last_tick REAL);
CREATE TABLE IF NOT EXISTS occurrences(id TEXT PRIMARY KEY,job TEXT,version INTEGER,slot REAL,state TEXT,attempts INTEGER DEFAULT 0,owner TEXT,lease REAL,token INTEGER DEFAULT 0,next_attempt REAL DEFAULT 0,result TEXT,release TEXT);
CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY,payload TEXT,state TEXT,receipt TEXT);
CREATE TABLE IF NOT EXISTS events(account TEXT,id TEXT,payload TEXT,PRIMARY KEY(account,id));
CREATE TABLE IF NOT EXISTS cursors(account TEXT PRIMARY KEY,cursor TEXT,gap TEXT);
CREATE TABLE IF NOT EXISTS pauses(scope TEXT PRIMARY KEY,reason TEXT);
CREATE TABLE IF NOT EXISTS usage(account TEXT,day TEXT,actions REAL DEFAULT 0,api_calls REAL DEFAULT 0,tokens REAL DEFAULT 0,spend REAL DEFAULT 0,PRIMARY KEY(account,day));
CREATE TABLE IF NOT EXISTS adaptations(id TEXT PRIMARY KEY,payload TEXT,status TEXT);
CREATE TABLE IF NOT EXISTS audit(n INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT,event TEXT,payload TEXT);
''')
  if publication:
   old=self.get('publication_id')
   if old and old!=publication:raise ValueError('Cross-publication workspace access refused')
   self.put('publication_id',publication)
  if not self.get('schema_version'):self.put('schema_version','1.0')
  if self.get('schema_version')!='1.0':raise ValueError('State migration required; no implicit conversion')
 def close(self):self.db.close()
 def get(self,k):
  r=self.db.execute('SELECT v FROM meta WHERE k=?',(k,)).fetchone();return json.loads(r[0]) if r else None
 def put(self,k,v):self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',(k,json.dumps(v)))
 def audit(self,event,data):self.db.execute('INSERT INTO audit(at,event,payload) VALUES(?,?,?)',(stamp(),event,json.dumps(data,ensure_ascii=False)))
 @contextmanager
 def transaction(self):
  self.db.execute('BEGIN IMMEDIATE')
  try:yield;self.db.execute('COMMIT')
  except BaseException:self.db.execute('ROLLBACK');raise
 def configure(self,plan,now=None):
  validate_plan(plan);now=time.time() if now is None else now
  if self.get('publication_id')!=plan['publication_id']:raise ValueError('Wrong publication plan')
  old=self.get('plan')
  if old and old['library_release']!=plan['library_release']:raise ValueError('Use staged release adoption before changing the lock')
  with self.transaction():
   for j in plan['jobs']:
    prev=self.db.execute('SELECT * FROM jobs WHERE id=?',(j['id'],)).fetchone()
    if prev and j['version']<prev['version']:raise ValueError('Schedule version cannot go backwards')
    if prev and json.loads(prev['config'])!=j and prev['version']==j['version']:raise ValueError('Changed schedule needs a new version')
    if prev and prev['version']!=j['version']:
     self.db.execute("UPDATE occurrences SET state='cancelled',result=? WHERE job=? AND state NOT IN ('completed','no-op','skipped','cancelled')",(json.dumps({'reason':'schedule superseded; external actions retained for reconciliation'}),j['id']))
    last=prev['last_tick'] if prev else now
    self.db.execute('INSERT OR REPLACE INTO jobs VALUES(?,?,?,?)',(j['id'],j['version'],json.dumps(j),last))
   active={j['id'] for j in plan['jobs']}
   for row in self.db.execute('SELECT id,config FROM jobs').fetchall():
    if row['id'] not in active:
     j=json.loads(row['config']);j['enabled']=False;self.db.execute('UPDATE jobs SET config=? WHERE id=?',(json.dumps(j),row['id']))
   self.put('plan',plan);self.audit('configured',{'plan_version':plan.get('version'),'jobs':len(plan['jobs'])})
 def enqueue(self,now):
  plan=self.get('plan')
  if not plan or not plan.get('enabled'):return
  with self.transaction():
   for r in self.db.execute('SELECT * FROM jobs').fetchall():
    j=json.loads(r['config'])
    if not j.get('enabled'):continue
    if now<r['last_tick']:
     self.audit('clock-backward',{'job':j['id']});continue
    for slot in slots(j,r['last_tick'],now):
     oid=digest([plan['publication_id'],j['id'],j['version'],slot]);age=now-slot
     state='queued'
     if age>j['freshness_seconds']:state='skipped' if j['missed']!='review' else 'blocked'
     if j['overlap']=='coalesce-latest':
      self.db.execute("UPDATE occurrences SET state='skipped',result=? WHERE job=? AND state IN ('queued','retry')",(json.dumps({'reason':'coalesced by current occurrence'}),j['id']))
     elif self.db.execute("SELECT 1 FROM occurrences WHERE job=? AND state IN ('queued','retry')",(j['id'],)).fetchone():continue
     self.db.execute('INSERT OR IGNORE INTO occurrences(id,job,version,slot,state,release) VALUES(?,?,?,?,?,?)',(oid,j['id'],j['version'],slot,state,plan['library_release']))
    self.db.execute('UPDATE jobs SET last_tick=? WHERE id=?',(now,j['id']))
   self.put('heartbeat',now);self.put('last_tick',now)
 def paused(self,j):
  scopes=['system','publication:'+self.get('publication_id'),'job:'+j['id'],'workflow:'+j['kind'],'account:'+j.get('account','')]
  return any(self.db.execute('SELECT 1 FROM pauses WHERE scope=?',(s,)).fetchone() for s in scopes)
 def claim(self,owner,now,executor_kind="subprocess"):
  with self.transaction():
   rows=self.db.execute("SELECT * FROM occurrences WHERE (state IN ('queued','retry') AND next_attempt<=?) OR (state='running' AND lease<=?) ORDER BY slot",(now,now)).fetchall()
   for r in rows:
    jr=self.db.execute('SELECT config FROM jobs WHERE id=?',(r['job'],)).fetchone();j=json.loads(jr[0])
    actual_kind='host-computer-use' if isinstance(j.get('executor'),dict) and j['executor'].get('kind')=='host-computer-use' else 'subprocess'
    if actual_kind!=executor_kind:continue
    if not j['enabled'] or self.paused(j):continue
    if now-r['slot']>j['freshness_seconds']:
     self.db.execute("UPDATE occurrences SET state='skipped',result=? WHERE id=?",(json.dumps({'reason':'stale before claim'}),r['id']));continue
    if r['attempts']>=j['max_attempts']:
     self.db.execute("UPDATE occurrences SET state='failed',result=? WHERE id=?",(json.dumps({'reason':'attempt budget exhausted'}),r['id']));continue
    other=self.db.execute("SELECT 1 FROM occurrences WHERE job=? AND state='running' AND lease>? AND id<>?",(r['job'],now,r['id'])).fetchone()
    if other:continue
    token=r['token']+1
    self.db.execute("UPDATE occurrences SET state='running',owner=?,lease=?,token=?,attempts=attempts+1 WHERE id=?",(owner,now+j['timeout_seconds']+5,token,r['id']))
    return dict(r)|{'owner':owner,'token':token,'attempts':r['attempts']+1,'job_config':j}
 def fence(self,occ,now):
  r=self.db.execute('SELECT * FROM occurrences WHERE id=?',(occ['id'],)).fetchone()
  if not r or r['state']!='running' or r['token']!=occ['token'] or r['owner']!=occ['owner'] or r['lease']<=now:raise Hold('Lost occurrence ownership')
  j=json.loads(self.db.execute('SELECT config FROM jobs WHERE id=?',(r['job'],)).fetchone()[0])
  if not j['enabled'] or self.paused(j):raise Hold('Operation paused or disabled')
  if j['version']!=occ['version']:raise Hold('Superseded schedule')
  if r['release']!=self.get('plan')['library_release']:raise Hold('Release changed; revalidate pending work')
  return j
 def finish(self,occ,state,result,now):
  with self.transaction():
   r=self.db.execute('SELECT * FROM occurrences WHERE id=?',(occ['id'],)).fetchone()
   if r['token']!=occ['token'] or r['owner']!=occ['owner'] or r['state']!='running':return False
   next_attempt=now+occ['job_config']['backoff_seconds']*2**(occ['attempts']-1) if state=='retry' else 0
   self.db.execute('UPDATE occurrences SET state=?,result=?,next_attempt=?,lease=0 WHERE id=?',(state,json.dumps(result),next_attempt,occ['id']))
   self.audit('occurrence-finished',{'id':occ['id'],'state':state,'result':result});return True
 def ingest(self,account,events,cursor,gap=None):
  with self.transaction():
   for e in events:
    if e['account']!=account:raise ValueError('Wrong account event')
    self.db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?)',(account,e['id'],json.dumps(e)))
   self.db.execute('INSERT OR REPLACE INTO cursors VALUES(?,?,?)',(account,json.dumps(cursor),gap))
 def pause(self,scope,reason):self.db.execute('INSERT OR REPLACE INTO pauses VALUES(?,?)',(scope,reason));self.audit('pause',{'scope':scope,'reason':reason})
 def resume(self,scope):self.db.execute('DELETE FROM pauses WHERE scope=?',(scope,));self.audit('resume',{'scope':scope})
 def status(self,now=None):
  now=time.time() if now is None else now;hb=self.get('heartbeat');plan=self.get('plan') or {}
  return {'publication_id':self.get('publication_id'),'library_release':plan.get('library_release'),'heartbeat':hb,'worker_state':'recent-heartbeat' if hb and now-hb<plan.get('health_timeout_seconds',30) else 'stale-or-not-running','occurrences':{r[0]:r[1] for r in self.db.execute('SELECT state,count(*) FROM occurrences GROUP BY state')},'unknown_actions':[r[0] for r in self.db.execute("SELECT id FROM actions WHERE state IN ('unknown','submitted')")],'pauses':[dict(r) for r in self.db.execute('SELECT * FROM pauses')],'listener_gaps':[dict(r) for r in self.db.execute('SELECT * FROM cursors WHERE gap IS NOT NULL')],'limitations':['Recent heartbeat is not proof of future availability. No offline independent monitor is bundled.']}

def gate(store,j,action,now):
 plan=store.get('plan');account=action['account'];op=action['operation']
 if store.paused(j):raise Hold('Paused')
 if action.get('publication_id')!=plan['publication_id']:raise Hold('Wrong publication')
 if j.get('account')!=account:raise Hold('Wrong account')
 if j['mode']=='draft-only':raise Hold('Draft-only job cannot send')
 if digest(action.get('content'))!=action.get('content_hash'):raise Hold('Content hash does not match actual content')
 cap=plan.get('capabilities',{}).get(account,{}).get(op,{})
 if cap.get('status')!='verified-available' or cap.get('policy')!='permitted':raise Hold('Action capability or platform policy unavailable')
 if cap.get('valid_until',0)<now:raise Hold('Capability verification expired')
 auth=plan.get('authorizations',{}).get(action.get('authorization_ref'),{})
 if auth.get('revoked') or not auth.get('starts_at',0)<=now<auth.get('expires_at',0):raise Hold('Authorization missing, revoked or expired')
 if account not in auth.get('accounts',[]) or op not in auth.get('operations',[]):raise Hold('Authorization scope mismatch')
 if action.get('target') not in auth.get('targets',[]) and '*' not in auth.get('targets',[]):raise Hold('Target outside authorization')
 if not auth.get('content_scope_delegated') and auth.get('content_hash')!=action['content_hash']:raise Hold('Approval content version mismatch')
 if j['mode']=='review-before-send' and auth.get('content_hash')!=action['content_hash']:raise Hold('Reviewed execution requires exact content approval')
 if action.get('opt_out') or action.get('human_answered') or action.get('target_deleted'):raise Hold('Opt-out, human response or deleted target')
 if action.get('context_hash')!=action.get('current_context_hash'):raise Hold('Conversation changed; revalidation required')
 if action.get('expected_before')!=action.get('current_before'):raise Hold('Account before-state changed')
 if action.get('requires_canonical') and not action.get('canonical_receipt',{}).get('confirmed'):raise Hold('Canonical publication unconfirmed')
 if not action.get('review_passed'):raise Hold('Content review incomplete')
 for slot in action.get('visuals',[]):
  if slot.get('required'):
   p=Path(slot.get('path',''))
   if not p.is_file() or slot.get('review')!='approved' or slot.get('rights')!='cleared':raise Hold('Required visual not ready')
   if hashlib.sha256(p.read_bytes()).hexdigest()!=slot.get('sha256'):raise Hold('Required visual changed')
 local=datetime.fromtimestamp(now,ZoneInfo(j['timezone']));minute=local.hour*60+local.minute
 windows=j.get('active_windows',[])
 if windows and not any((a<=minute<b if a<b else minute>=a or minute<b) for a,b in windows):raise Hold('Outside sending window')
 return cap,auth

def deliver(store,occ,action,adapter,now=None):
 """Adapter must refresh context, enforce remote idempotency, and return durable receipts."""
 clock=time.time if now is None else lambda:now
 current=clock()
 j=store.fence(occ,current)
 action=adapter.refresh(action)
 current=clock()
 cap,auth=gate(store,j,action,current)
 aid=digest([store.get('publication_id'),action['account'],action['operation'],action.get('target'),action.get('source_event'),action['content_hash']])
 with store.transaction():
  store.fence(occ,clock())
  old=store.db.execute('SELECT * FROM actions WHERE id=?',(aid,)).fetchone()
  if old and old['state']=='confirmed':return json.loads(old['receipt'])
  if old and old['state'] in ('unknown','submitted'):
   receipt=adapter.reconcile(aid)
   if receipt:
    store.db.execute("UPDATE actions SET state='confirmed',receipt=? WHERE id=?",(json.dumps(receipt),aid));return receipt
   raise Hold('Unknown remote result; reconcile before retry')
  day=datetime.fromtimestamp(current,timezone.utc).date().isoformat()
  usage=store.db.execute('SELECT * FROM usage WHERE account=? AND day=?',(action['account'],day)).fetchone()
  estimate=action.get('reserved_cost')
  if not estimate or any(k not in estimate or estimate[k]<0 for k in ('actions','api_calls','tokens','spend')):raise Hold('A bounded cost reservation is required')
  limits=store.get('plan').get('account_budgets',{}).get(action['account'],{})
  for k,v in estimate.items():
   if k not in ('actions','api_calls','tokens','spend'):raise Hold('Unknown cost dimension')
   limit=min(j['budget'].get(k,-1),limits.get(k,-1),auth.get('budget',{}).get(k,-1))
   if v+(usage[k] if usage else 0)>limit:raise Hold('Action/account authorization budget exhausted')
  store.db.execute('INSERT OR IGNORE INTO usage(account,day) VALUES(?,?)',(action['account'],day))
  store.db.execute('UPDATE usage SET actions=actions+?,api_calls=api_calls+?,tokens=tokens+?,spend=spend+? WHERE account=? AND day=?',(*[estimate[k] for k in ('actions','api_calls','tokens','spend')],action['account'],day))
  store.db.execute('INSERT OR REPLACE INTO actions VALUES(?,?,?,?)',(aid,json.dumps(action),'submitted',None))
 # Persisted submit state is intentionally outside the remote transaction. Lost responses reconcile.
 try:
  store.fence(occ,clock())
  gate(store,j,adapter.refresh(action),clock())
  if store.paused(j):raise Hold('Paused before submission')
  receipt=adapter.send(aid,action)
 except Exception as exc:
  store.db.execute("UPDATE actions SET state='unknown',receipt=? WHERE id=?",(json.dumps({'reason':str(exc)}),aid));raise
 if not receipt.get('confirmed') or not receipt.get('remote_id'):raise Hold('Adapter returned no confirmed receipt')
 store.db.execute("UPDATE actions SET state='confirmed',receipt=? WHERE id=?",(json.dumps(receipt),aid))
 store.audit('action-confirmed',{'id':aid,'receipt':receipt});return receipt

def run_one(store,occ,now=None):
 now=time.time() if now is None else now;j=occ['job_config']
 request={'schema_version':'1.0','publication_id':store.get('publication_id'),'library_release':occ['release'],'job':j,'occurrence':{k:v for k,v in occ.items() if k!='job_config'},'workspace':str(store.root),'protocol':'prepare-only: return artifacts, observations and action proposals; no external effects'}
 try:
  store.fence(occ,now)
  command=j['executor']
  if not isinstance(command,list) or not command:raise Hold('Executor must be an authorized argv list')
  p=subprocess.run(command,input=json.dumps(request),text=True,capture_output=True,timeout=j['timeout_seconds'],cwd=store.root)
  if p.returncode:raise RuntimeError(p.stderr[-1000:] or 'Executor failed')
  if len(p.stdout)>4_000_000:raise Hold('Executor result exceeds bounded protocol size')
  result=json.loads(p.stdout)
  if result.get('publication_id')!=store.get('publication_id'):raise Hold('Executor returned another publication')
  state=result.get('state')
  if state not in ('completed','no-op','blocked'):raise Hold('Invalid executor outcome')
  store.fence(occ,time.time())
  for batch in result.get('observations',[]):store.ingest(batch['account'],batch['events'],batch['cursor'],batch.get('gap'))
  actions=result.get('actions',[])
  if actions:
   # Only the explicit local simulation adapter ships. Real adapters require independent installation/review.
   if store.get('plan').get('adapter')!='synthetic':raise Hold('No verified live write adapter configured; proposals retained')
   from synthetic_adapter import SyntheticAdapter
   adapter=SyntheticAdapter(store.root)
   result['receipts']=[deliver(store,occ,a,adapter) for a in actions]
  store.finish(occ,state,result,time.time())
 except Hold as e:store.finish(occ,'blocked',{'reason':str(e),'prepared_result':locals().get('result')},time.time())
 except (subprocess.TimeoutExpired,RuntimeError,OSError,ValueError) as e:
  state='retry' if occ['attempts']<j['max_attempts'] else 'failed'
  store.finish(occ,state,{'reason':str(e)},time.time())

def export_workspace(store,destination):
 dest=Path(destination).resolve()
 if dest==store.root or store.root in dest.parents:raise ValueError('Export destination must be outside the workspace')
 if dest.exists() and any(dest.iterdir()):raise ValueError('Use an empty export destination')
 dest.mkdir(parents=True,exist_ok=True,mode=0o700)
 # Explicit approved files only; never recursively copy arbitrary workspace contents.
 approved=store.get('export_files') or [];inventory=[];omitted=[]
 for name in approved:
  p=(store.root/name).resolve()
  if store.root not in p.parents or p.is_symlink():raise ValueError('Unsafe export reference')
  if not p.is_file():omitted.append(name);continue
  data=p.read_bytes()
  if any(x in data for x in (b'-----BEGIN PRIVATE KEY',b'Authorization: Bearer',b'"access_token"',b'"password"')):raise ValueError('Potential secret requires private review before export')
  q=dest/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data);inventory.append({'path':name,'sha256':hashlib.sha256(data).hexdigest()})
 # State database contains private records, including action proposals. Require explicit authorization.
 if not store.get('export_state_authorized'):raise ValueError('State export requires explicit private export authorization')
 state_text='\n'.join(store.db.iterdump())
 if any(x in state_text for x in ('-----BEGIN PRIVATE KEY','Authorization: Bearer','"access_token"','"password"')):raise ValueError('Potential secret in state; review before export')
 database=sqlite3.connect(dest/'runtime.sqlite');store.db.backup(database);database.close()
 inventory.append({'path':'runtime.sqlite','sha256':hashlib.sha256((dest/'runtime.sqlite').read_bytes()).hexdigest()})
 manifest={'schema_version':'1.0','publication_id':store.get('publication_id'),'library_release':store.get('plan')['library_release'],'inventory':inventory,'omitted':omitted,'completeness':'approved-files-plus-state; inspect unresolved references','private':True}
 (dest/'export.json').write_text(json.dumps(manifest,indent=2));return manifest

def restore_workspace(source,destination,publication):
 source=Path(source).resolve();dest=Path(destination).resolve();m=json.loads((source/'export.json').read_text())
 if m['publication_id']!=publication:raise ValueError('Cross-publication restore refused')
 if dest.exists() and any(dest.iterdir()):raise ValueError('Restore only into an empty destination')
 verified=[]
 for f in m['inventory']:
  p=(source/f['path']).resolve();q=(dest/f['path']).resolve()
  if source not in p.parents or dest not in q.parents:raise ValueError('Unsafe export path')
  data=p.read_bytes()
  if hashlib.sha256(data).hexdigest()!=f['sha256']:raise ValueError('Export integrity mismatch')
  verified.append((q,data))
 dest.mkdir(parents=True,exist_ok=True,mode=0o700)
 for q,data in verified:q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
 return m

def main():
 p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);sub=p.add_subparsers(dest='cmd',required=True)
 c=sub.add_parser('configure');c.add_argument('plan')
 r=sub.add_parser('run');r.add_argument('--poll-seconds',type=float,default=1);r.add_argument('--max-seconds',type=float)
 sub.add_parser('status');sub.add_parser('tick');sub.add_parser('stop')
 for n in ('pause','resume'):
  q=sub.add_parser(n);q.add_argument('scope');q.add_argument('--reason',default='Owner request')
 a=p.parse_args();plan=json.loads(Path(a.plan).read_text()) if a.cmd=='configure' else None
 s=Store(a.workspace,plan['publication_id'] if plan else None)
 if a.cmd=='configure':s.configure(plan);print(json.dumps(s.status()));return
 if a.cmd=='status':print(json.dumps(s.status(),indent=2));return
 if a.cmd=='pause':s.pause(a.scope,a.reason);return
 if a.cmd=='resume':s.resume(a.scope);return
 if a.cmd=='stop':s.put('stop_requested',True);return
 owner=uuid.uuid4().hex;s.put('stop_requested',False);started=time.time();running=True
 def stop(signum,frame):
  nonlocal running
  running=False
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 try:
  while running and not s.get('stop_requested'):
   now=time.time();s.enqueue(now)
   occurrence=s.claim(owner,now)
   if occurrence:run_one(s,occurrence)
   if a.cmd=='tick' or (a.max_seconds and time.time()-started>=a.max_seconds):break
   time.sleep(max(.05,a.poll_seconds))
 finally:s.put('stopped_at',time.time());s.audit('worker-stopped',{'owner':owner});s.close()
if __name__=='__main__':main()
