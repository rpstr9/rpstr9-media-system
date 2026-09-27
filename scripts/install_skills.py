"""Install this complete library plus new skill links without overwriting skills."""
from pathlib import Path
import argparse,json,shutil,sys
from release_control import verify
ROOT=Path(__file__).resolve().parents[1]
def install(library_dest,skill_root):
 m=verify(ROOT);dest=Path(library_dest).expanduser().absolute();skills=Path(skill_root).expanduser().absolute()
 if dest==ROOT or ROOT in dest.parents:raise ValueError('Choose an installed library location outside the source tree')
 names=[p.name for p in (ROOT/'skills').iterdir() if (p/'SKILL.md').is_file()]
 for name in names:
  link=skills/name;target=dest/'skills'/name
  if (link.exists() or link.is_symlink()) and (not link.is_symlink() or link.resolve()!=target.resolve()):raise ValueError('Existing skill retained; conflicting name: '+name)
 if dest.exists():
  verify(dest)
  if (dest/'releases/manifest.json').read_bytes()!=(ROOT/'releases/manifest.json').read_bytes():raise ValueError('Installed library differs; choose a new version location')
 else:
  dest.mkdir(parents=True)
  for rel in [e['path'] for e in m['inventory']]+['releases/manifest.json']:
   out=dest/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,out)
  pointer=ROOT/'releases/latest.json'
  if pointer.is_file():shutil.copy2(pointer,dest/'releases/latest.json')
  verify(dest)
 skills.mkdir(parents=True,exist_ok=True)
 for name in names:
  link=skills/name
  if not link.is_symlink():link.symlink_to(dest/'skills'/name,target_is_directory=True)
 return {'installed_count':len(names),'library':str(dest),'skills':sorted(names),'existing_skills_overwritten':False,'services_started':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--library-dest',required=True);p.add_argument('--skill-root',required=True);a=p.parse_args();print(json.dumps(install(a.library_dest,a.skill_root),indent=2))
