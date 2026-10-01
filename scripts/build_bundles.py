from pathlib import Path
import hashlib,json,re,os
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def make(name,paths):
 paths=list(dict.fromkeys(paths));out=ROOT/name;out.parent.mkdir(parents=True,exist_ok=True)
 anchors={p:'source-'+re.sub('[^a-z0-9]+','-',p.lower()) for p in paths}
 chunks=['# Complete reading bundle\n\nGenerated from canonical sources. Read the required workflow completely; external methods remain external and must be loaded in full when invoked.\n']
 inventory=[]
 for path in paths:
  src=ROOT/path;text=src.read_text();inventory.append({'path':path,'bytes':src.stat().st_size,'sha256':sha(src)})
  def link(m):
   label,target=m.groups()
   if '://' in target or target.startswith('#'):return m[0]
   resolved=(src.parent/target.split('#')[0]).resolve()
   try:rel=str(resolved.relative_to(ROOT))
   except ValueError:raise ValueError('Reference escapes public source tree: '+target)
   if not resolved.exists():raise ValueError('Missing source link '+rel)
   return f'[{label}](#{anchors[rel]})' if rel in anchors else f'[{label}]({os.path.relpath(resolved,out.parent)})'
  text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',link,text)
  if src.suffix=='.json':text='```json\n'+text+'\n```'
  chunks.append(f'\n<a id="{anchors[path]}"></a>\n\n---\n\nSource: `{path}`\n\n'+text)
 chunks.append('\n## Source inventory\n\n```json\n'+json.dumps(inventory,indent=2)+'\n```\n')
 out.write_text(''.join(chunks));return inventory
def main():
 reg=json.loads((ROOT/'registry/workflows.json').read_text())
 common=['policies/CONSTITUTION.md','contracts/HANDOFF.md','registry/method-dependencies.json']
 inventories={}
 for w in reg['workflows']:
  paths=common+w.get('references',[])+[f'skills/{s}/SKILL.md' for s in w['required_skills']]
  if 'media-master' in w['required_skills'] or 'media-publishing' in w['required_skills']:paths+=['runtime/reference/BROWSER_HOST.md']
  if 'media-publishing' in w['required_skills']:paths+=['adapters/platforms.md','adapters/contracts/EXECUTOR.md']
  if w['id'] in ('configure-recurring-operations','operations-review','create-and-launch-publication'):paths+=['runtime/reference/README.md']
  inventories[w['id']]=make(w['bundle'],paths)
 inventories['master']=make('dist/MASTER.md',common+['contracts/EDITORIAL_FOUNDATION.md','skills/media-master/SKILL.md','skills/concept-review/SKILL.md','START_HERE.md','registry/workflows.json','runtime/reference/README.md','runtime/reference/BROWSER_HOST.md'])
 (ROOT/'dist/source-inventories.json').write_text(json.dumps(inventories,indent=2))
 files=[]
 allow=json.loads((ROOT/'releases/public-allowlist.json').read_text())['paths']
 for p in sorted(ROOT.rglob('*')):
  rel=str(p.relative_to(ROOT))
  if p.is_file() and '__pycache__' not in rel and '.git' not in p.relative_to(ROOT).parts and rel not in ('releases/manifest.json','releases/latest.json'):
   if rel not in allow:raise ValueError('Unreviewed file outside public allowlist: '+rel)
   files.append({'path':rel,'sha256':sha(p),'bytes':p.stat().st_size})
 (ROOT/'releases/manifest.json').write_text(json.dumps({'schema_version':'1.0','release':'0.1.8','inventory':files,'excludes':['releases/manifest.json','releases/latest.json']},indent=2))
 print(json.dumps({'workflows':len(reg['workflows']),'files':len(files),'inventory_digest':sha(ROOT/'releases/manifest.json')}))
if __name__=='__main__':main()
