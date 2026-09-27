"""Scoped local adaptation records. No network or shared-library writes."""
from datetime import datetime,timezone
PROTECTED={'permissions','authorization','platform_policy','objectives','identity','grader','source_evidence','shared_library','budget_limit'}
def propose(store,record):
 if record['publication_id']!=store.get('publication_id'):raise ValueError('Wrong publication')
 if record['surface'] in PROTECTED:raise ValueError('Protected surface requires separate owner policy path')
 if not record.get('baseline') or not record.get('rollback'):raise ValueError('Baseline and rollback required')
 import json
 store.db.execute('INSERT INTO adaptations VALUES(?,?,?)',(record['id'],json.dumps(record),'experiment'))
 store.audit('adaptation-proposed',{'id':record['id']})
def decide(store,aid,evidence,authorized):
 import json
 row=store.db.execute('SELECT payload FROM adaptations WHERE id=?',(aid,)).fetchone()
 if not row:raise ValueError('Missing adaptation')
 record=json.loads(row[0])
 if evidence.get('protected_regressions'):status='rejected'
 elif not evidence.get('comparable') or not evidence.get('benefit_observed'):status='inconclusive'
 elif not authorized:status='awaiting-approval'
 else:status='approved'
 record['evaluation']=evidence
 store.db.execute('UPDATE adaptations SET status=?,payload=? WHERE id=?',(status,json.dumps(record),aid));store.audit('adaptation-decision',{'id':aid,'status':status});return status
def applicable(store,skill,release,now):
 import json
 selected=[]
 for row in store.db.execute("SELECT * FROM adaptations WHERE status='approved'"):
  r=json.loads(row['payload'])
  if r['publication_id']==store.get('publication_id') and r['skill']==skill and r['release']==release and r['expires_at']>now:selected.append(r)
 return selected
def rollback(store,aid,reason):
 store.db.execute("UPDATE adaptations SET status='rolled-back' WHERE id=?",(aid,));store.audit('adaptation-rollback',{'id':aid,'reason':reason})
