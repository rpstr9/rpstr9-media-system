"""Local release integrity and opt-in adoption. Does not publish a repository."""
from pathlib import Path
import hashlib,json
def verify(root):
 root=Path(root).resolve();m=json.loads((root/'releases/manifest.json').read_text());errors=[]
 for entry in m['inventory']:
  p=(root/entry['path']).resolve()
  if root not in p.parents:errors.append('path outside release');continue
  if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:errors.append(entry['path'])
 if errors:raise ValueError('Release inventory mismatch: '+', '.join(errors))
 return m
def load_complete(root,paths,reader):
 verify(root);inventory=[];content=[]
 for path in paths:
  p=(Path(root)/path).resolve()
  if Path(root).resolve() not in p.parents:raise ValueError('Path outside release')
  data=reader(p)
  if not isinstance(data,bytes) or hashlib.sha256(data).digest()!=hashlib.sha256(p.read_bytes()).digest():raise ValueError('Missing or truncated method: '+path)
  inventory.append(path);content.append(data.decode())
 return '\n\n'.join(content),inventory
def stage_adoption(store,new_lock,compatible,authorized,new_library_root):
 if not authorized:raise ValueError('Owner update policy does not authorize adoption')
 if not compatible:raise ValueError('Migration/compatibility review required')
 manifest=verify(new_library_root)
 if manifest['release']!=new_lock:raise ValueError('New lock does not match verified release')
 prior=store.get('plan');store.put('prior_release_plan',prior)
 plan=dict(prior);plan['library_release']=new_lock;store.put('plan',plan)
 # Local rules remain stored; incompatible versions are never returned by applicable().
 store.audit('release-adopted',{'from':prior['library_release'],'to':new_lock})
def rollback_adoption(store):
 prior=store.get('prior_release_plan')
 if not prior:raise ValueError('No prior release retained')
 store.put('plan',prior);store.audit('release-rollback',{'to':prior['library_release'],'remote_effects':'unchanged'})
