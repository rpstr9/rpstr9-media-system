"""Durable queue bridge for a scheduled host with supported computer-use tools.
This module never drives UI; the authorized Codex turn does so through its tools.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,time,uuid
from runner import Store,Hold,gate,digest

def claim(store,owner,now=None):
 now=time.time() if now is None else now;store.enqueue(now)
 occ=store.claim(owner,now,executor_kind='host-computer-use')
 if not occ:return {'state':'no-op','publication_id':store.get('publication_id')}
 return {'state':'claimed','publication_id':store.get('publication_id'),'occurrence':occ,'browser_routes':store.get('plan').get('browser_routes',{}),'protocol':'Read the full locked workflow. Use supported host computer controls. Persist intent immediately before each external effect and record its actual UI receipt. Resume unknown writes by observation, not by clicking again.'}

def current(store,ticket,now):
 if ticket.get('publication_id')!=store.get('publication_id'):raise Hold('Wrong publication ticket')
 occ=ticket['occurrence'];j=store.fence(occ,now)
 if not isinstance(j.get('executor'),dict) or j['executor'].get('kind')!='host-computer-use':raise Hold('Not a host computer-use occurrence')
 return occ,j

def begin(store,ticket,action,observation,now=None):
 now=time.time() if now is None else now;occ,j=current(store,ticket,now)
 route=store.get('plan').get('browser_routes',{}).get(action.get('account'),{})
 if not route or not route.get('profile'):raise Hold('Private browser/account route not configured')
 if not 0<=now-observation.get('observed_at',0)<=route.get('context_max_age_seconds',0):raise Hold('Fresh browser observation required')
 for key in ('browser','profile'):
  if observation.get(key)!=route.get(key):raise Hold('Wrong browser or profile')
 if observation.get('account')!=action.get('account'):raise Hold('Wrong observed account')
 if observation.get('available') is not True or not observation.get('evidence_ref'):raise Hold('Browser unavailable or observation evidence missing')
 if observation.get('target')!=action.get('target'):raise Hold('Wrong browser target')
 if any(not isinstance(observation.get(k),bool) for k in ('human_answered','opt_out','target_deleted')):raise Hold('Unobserved conversation or target state')
 a=dict(action);a.update({k:observation.get(k) for k in ('human_answered','opt_out','target_deleted','current_context_hash','current_before')});a['host_occurrence_id']=occ['id']
 _,auth=gate(store,j,a,now)
 aid=digest([store.get('publication_id'),a['account'],a['operation'],a.get('target'),a.get('source_event'),a['content_hash']])
 with store.transaction():
  store.fence(occ,now)
  old=store.db.execute('SELECT * FROM actions WHERE id=?',(aid,)).fetchone()
  if old:
   if old['state']=='confirmed':return {'state':'already-confirmed','action_id':aid,'receipt':json.loads(old['receipt'])}
   raise Hold('Possible prior browser effect; inspect remote state before retry')
  cost=a.get('reserved_cost');dimensions=('actions','api_calls','tokens','spend')
  if not cost or set(cost)!=set(dimensions) or any(not isinstance(cost[k],(int,float)) or cost[k]<0 for k in dimensions):raise Hold('Bounded action cost required')
  day=datetime.fromtimestamp(now,timezone.utc).date().isoformat();u=store.db.execute('SELECT * FROM usage WHERE account=? AND day=?',(a['account'],day)).fetchone();limits=store.get('plan').get('account_budgets',{}).get(a['account'],{})
  for k in dimensions:
   if cost[k]+(u[k] if u else 0)>min(j['budget'].get(k,-1),limits.get(k,-1),auth.get('budget',{}).get(k,-1)):raise Hold('Browser action budget exhausted')
  store.db.execute('INSERT OR IGNORE INTO usage(account,day) VALUES(?,?)',(a['account'],day))
  store.db.execute('UPDATE usage SET actions=actions+?,api_calls=api_calls+?,tokens=tokens+?,spend=spend+? WHERE account=? AND day=?',(*[cost[k] for k in dimensions],a['account'],day))
  store.db.execute('INSERT INTO actions VALUES(?,?,?,?)',(aid,json.dumps(a),'submitted',None));store.audit('browser-intent-persisted',{'action_id':aid,'occurrence':occ['id'],'observation':observation})
 return {'state':'submit-once','action_id':aid,'content_hash':a['content_hash'],'instruction':'Recheck unchanged UI, authority and pause before the immediate final click; afterwards persist actual evidence. An interruption or timeout requires observation and reconciliation before another click.'}

def record_receipt(store,aid,receipt):
 row=store.db.execute('SELECT * FROM actions WHERE id=?',(aid,)).fetchone()
 if not row:raise Hold('No persisted action intent')
 a=json.loads(row['payload'])
 if a['publication_id']!=store.get('publication_id'):raise Hold('Wrong publication action')
 for k in ('account','content_hash','target'):
  if receipt.get(k)!=a.get(k):raise Hold('Receipt does not match intended '+k)
 if receipt.get('confirmed') is not True or receipt.get('simulation') is not False or receipt.get('confirmation_source')!='browser-ui':raise Hold('Actual browser confirmation required')
 if not all(receipt.get(k) for k in ('remote_id','remote_url','evidence_ref','observed_at')):raise Hold('Remote identity and observed UI evidence required')
 if row['state']=='confirmed':
  old=json.loads(row['receipt'])
  if old.get('remote_id')!=receipt['remote_id']:raise Hold('Receipt conflicts with confirmed remote effect')
  return old
 # Recording an already-observed effect is allowed after a lease expires; it creates no new remote action.
 store.db.execute("UPDATE actions SET state='confirmed',receipt=? WHERE id=?",(json.dumps(receipt),aid));store.audit('browser-action-confirmed',{'action_id':aid,'receipt':receipt});return receipt

def finish(store,ticket,result,now=None):
 now=time.time() if now is None else now;occ,j=current(store,ticket,now)
 if result.get('publication_id')!=store.get('publication_id') or result.get('state') not in ('completed','blocked','no-op'):raise Hold('Invalid host outcome')
 pending=[]
 for row in store.db.execute("SELECT * FROM actions WHERE state!='confirmed'"):
  if json.loads(row['payload']).get('host_occurrence_id')==occ['id']:pending.append(row['id'])
 if pending and result['state']!='blocked':raise Hold('Unresolved browser effects must remain blocked')
 for b in result.get('observations',[]):store.ingest(b['account'],b['events'],b['cursor'],b.get('gap'))
 return store.finish(occ,result['state'],dict(result,unresolved_actions=pending),now)

def main():
 p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);sub=p.add_subparsers(dest='command',required=True)
 c=sub.add_parser('claim');c.add_argument('--owner',required=True)
 b=sub.add_parser('begin');b.add_argument('ticket');b.add_argument('action');b.add_argument('observation')
 r=sub.add_parser('receipt');r.add_argument('action_id');r.add_argument('receipt')
 f=sub.add_parser('finish');f.add_argument('ticket');f.add_argument('result')
 args=p.parse_args();s=Store(args.workspace)
 def read(path):return json.loads(Path(path).read_text())
 try:
  if args.command=='claim':out=claim(s,args.owner)
  elif args.command=='begin':out=begin(s,read(args.ticket),read(args.action),read(args.observation))
  elif args.command=='receipt':out=record_receipt(s,args.action_id,read(args.receipt))
  else:out={'completed':finish(s,read(args.ticket),read(args.result))}
  print(json.dumps(out,ensure_ascii=False,indent=2))
 except Hold as exc:print(json.dumps({'state':'blocked','reason':str(exc)}));raise SystemExit(2)
 finally:s.close()
if __name__=='__main__':main()
