"""Local simulation only. Never contacts a platform or returns a live URL."""
import json, sqlite3
from pathlib import Path

class SyntheticAdapter:
 def __init__(self,root):
  self.db=sqlite3.connect(Path(root)/'synthetic-remote.sqlite',isolation_level=None)
  self.db.execute('CREATE TABLE IF NOT EXISTS effects(id TEXT PRIMARY KEY,action TEXT,receipt TEXT)')
  self.context={};self.lose_response=False
 def refresh(self,action):return action|self.context
 def reconcile(self,aid):
  row=self.db.execute('SELECT receipt FROM effects WHERE id=?',(aid,)).fetchone()
  return json.loads(row[0]) if row else None
 def send(self,aid,action):
  existing=self.reconcile(aid)
  if existing:return existing
  receipt={'confirmed':True,'remote_id':'simulation:'+aid,'confirmation_source':'local-simulation','simulation':True,'remote_url':None,'content_hash':action['content_hash'],'account':action['account'],'parent':action.get('target'),'media':[{'sha256':v['sha256'],'anchor':v.get('anchor')} for v in action.get('visuals',[])]}
  self.db.execute('INSERT OR IGNORE INTO effects VALUES(?,?,?)',(aid,json.dumps(action),json.dumps(receipt)))
  if self.lose_response:raise TimeoutError('Synthetic response lost after committed effect')
  return receipt
