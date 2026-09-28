"""Exposed development checks; no live provider or protected benchmark claims."""
import copy,hashlib,importlib.util,json,re,sys,tempfile,unittest
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'runtime/reference')]
from validate_records import validate
from release_control import verify,load_complete,stage_adoption,rollback_adoption
from runner import Store
import yaml

def record(kind,scope='synthetic-a'):
 schema=json.loads((ROOT/f'contracts/{kind}.schema.json').read_text());p={}
 for key,s in schema['properties']['payload']['properties'].items():
  typ=s.get('type',[]);types=[typ] if isinstance(typ,str) else typ
  p[key]=s['enum'][0] if 'enum' in s else None if 'null' in types else [] if 'array' in types else {} if 'object' in types else False if 'boolean' in types else 'fixture'
 return {'record_type':kind,'record_id':'synthetic-'+kind,'schema_version':'1.0','created_at':'2026-09-28T00:00:00Z','publication_id_or_system_scope':scope,'provenance_refs':[],'data_classification':'public-synthetic','payload':p}
class PackageTests(unittest.TestCase):
 def test_every_schema_valid(self):
  for f in (ROOT/'contracts').glob('*.schema.json'):Draft202012Validator.check_schema(json.loads(f.read_text()))
 def test_skill_frontmatter_and_paths(self):
  for f in (ROOT/'skills').glob('*/SKILL.md'):
   h=yaml.safe_load(f.read_text().split('---',2)[1]);self.assertEqual(h['name'],f.parent.name);self.assertTrue(h['description']);self.assertNotIn('model',h)
   for t in re.findall(r'\]\(([^)]+)\)',f.read_text()):
    if '://' not in t:self.assertTrue((f.parent/t.split('#')[0]).exists(),t)
 def test_manifest_integrity(self):self.assertEqual(verify(ROOT)['release'],'0.1.7')
 def test_workflow_inventory_exact(self):
  inv=json.loads((ROOT/'dist/source-inventories.json').read_text())
  for w in json.loads((ROOT/'registry/workflows.json').read_text())['workflows']:
   paths={x['path'] for x in inv[w['id']]};bundle=(ROOT/w['bundle']).read_text()
   for skill in w['required_skills']:self.assertIn('skills/'+skill+'/SKILL.md',paths)
   for entry in inv[w['id']]:
    self.assertEqual(entry['sha256'],hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest());self.assertIn('Source: `'+entry['path']+'`',bundle)
 def test_full_read_and_truncation(self):
  paths=['skills/media-growth/SKILL.md','contracts/HANDOFF.md'];text,loaded=load_complete(ROOT,paths,lambda p:p.read_bytes());self.assertEqual(loaded,paths);self.assertIn('Growth',text)
  with self.assertRaises(ValueError):load_complete(ROOT,paths,lambda p:p.read_bytes()[:80])
 def test_manifest_tamper_and_escape(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'releases').mkdir();(root/'method.md').write_text('complete');m={'inventory':[{'path':'method.md','sha256':hashlib.sha256(b'complete').hexdigest(),'bytes':8}]};(root/'releases/manifest.json').write_text(json.dumps(m));verify(root);(root/'method.md').write_text('changed')
   with self.assertRaises(ValueError):verify(root)
   m['inventory'][0]['path']='../outside';(root/'releases/manifest.json').write_text(json.dumps(m))
   with self.assertRaises(ValueError):verify(root)
 def test_missing_observation_not_zero(self):
  r=record('OutcomeRecord');r['payload'].update(observation_type='unavailable',value=None);self.assertEqual(validate([r]),[]);r['payload']['value']=0;self.assertTrue(validate([r]))
 def test_simulation_cannot_be_live_receipt(self):
  r=record('PublicationReceipt');r['payload'].update(result_status='confirmed',remote_id='simulation:test',evidence_ref='fixture',confirmation_source='simulation');self.assertTrue(validate([r]))
 def test_required_visual_gate(self):
  r=record('ContentPackage');r['payload'].update(status='ready',visual_readiness='missing');self.assertTrue(validate([r]));r['payload']['visual_readiness']='not-applicable';self.assertEqual(validate([r]),[])
 def test_publication_record_reference_isolation(self):
  a=record('EditorialProgram');b=record('PublicationBlueprint','synthetic-b');a['payload']['blueprint_ref']='record:'+b['record_id'];self.assertIn('Cross-publication record reference',validate([a,b]))
 def test_launch_state_requires_evidence(self):
  r=record('LaunchPackage');r['payload']['published']=True;self.assertTrue(validate([r]));r['payload']['state_evidence']['published']=['record:remote-receipt'];r['payload']['simulation']=True;self.assertTrue(validate([r]))
 def test_release_adoption_and_rollback(self):
  with tempfile.TemporaryDirectory() as d:
   s=Store(d,'synthetic-a');s.put('plan',{'library_release':'prior'});s.put('private_note','retained')
   with self.assertRaises(ValueError):stage_adoption(s,'0.1.7',True,False,ROOT)
   with self.assertRaises(ValueError):stage_adoption(s,'0.1.7',False,True,ROOT)
   stage_adoption(s,'0.1.7',True,True,ROOT);self.assertEqual(s.get('plan')['library_release'],'0.1.7');rollback_adoption(s);self.assertEqual(s.get('plan')['library_release'],'prior');self.assertEqual(s.get('private_note'),'retained');s.close()
if __name__=='__main__':unittest.main(verbosity=2)
