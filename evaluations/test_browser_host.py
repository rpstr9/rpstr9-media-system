"""Queue-protocol tests only; no real Chrome or X effects."""
import json,sys,time,tempfile,unittest,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'runtime/reference'),str(ROOT/'evaluations')]
from runner import Store,Hold
from browser_host import claim,begin,record_receipt,finish
from test_runtime import plan,action
class BrowserHostTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.now=time.time();self.s=Store(self.temp.name,'synthetic-a');p=plan(self.now);p['adapter']='host-computer-use';p['jobs'][0]['executor']={'kind':'host-computer-use'};p['browser_routes']={'synthetic-account':{'browser':'Chrome','profile':'synthetic-profile','context_max_age_seconds':30}};self.s.configure(p,self.now-.1)
 def tearDown(self):self.s.close();self.temp.cleanup()
 def observe(self):return {'browser':'Chrome','profile':'synthetic-profile','account':'synthetic-account','observed_at':self.now,'available':True,'evidence_ref':'synthetic-observation','target':'own','human_answered':False,'opt_out':False,'target_deleted':False,'current_context_hash':None,'current_before':None}
 def receipt(self,a):return {'account':a['account'],'content_hash':a['content_hash'],'target':a['target'],'confirmed':True,'simulation':False,'confirmation_source':'browser-ui','remote_id':'fixture-only','remote_url':'https://example.invalid/fixture','evidence_ref':'fixture-only','observed_at':self.now}
 def test_host_claim_and_subprocess_separation(self):
  self.s.enqueue(self.now);self.assertIsNone(self.s.claim('subprocess',self.now));t=claim(self.s,'host',self.now);self.assertEqual(t['state'],'claimed');self.assertEqual(claim(self.s,'other-host',self.now)['state'],'no-op')
 def test_durable_begin_unknown_cannot_reclick(self):
  t=claim(self.s,'host',self.now);r=begin(self.s,t,action(),self.observe(),self.now);self.assertEqual(r['state'],'submit-once');self.s.close();self.s=Store(self.temp.name,'synthetic-a')
  with self.assertRaises(Hold):begin(self.s,t,action(),self.observe(),self.now)
  self.assertEqual(self.s.db.execute('SELECT actions FROM usage').fetchone()[0],1)
 def test_observed_identity_and_stale_context(self):
  t=claim(self.s,'host',self.now)
  for key,value in [('profile','other'),('account','other'),('browser','other'),('target','other'),('observed_at',self.now-60),('available',False),('human_answered',None)]:
   o=self.observe();o[key]=value
   with self.assertRaises(Hold,msg=key):begin(self.s,t,action(),o,self.now)
  self.assertEqual(self.s.db.execute('SELECT count(*) FROM actions').fetchone()[0],0)
 def test_pause_before_browser_effect(self):
  t=claim(self.s,'host',self.now);self.s.pause('system','test')
  with self.assertRaises(Hold):begin(self.s,t,action(),self.observe(),self.now)
 def test_human_answer_and_changed_context(self):
  t=claim(self.s,'host',self.now)
  for key,value in [('human_answered',True),('opt_out',True),('current_context_hash','changed')]:
   o=self.observe();o[key]=value
   with self.assertRaises(Hold):begin(self.s,t,action(),o,self.now)
 def test_receipt_requires_matching_observed_result(self):
  t=claim(self.s,'host',self.now);a=action();aid=begin(self.s,t,a,self.observe(),self.now)['action_id'];r=self.receipt(a)
  for key,value in [('content_hash','wrong'),('account','wrong'),('evidence_ref',None),('simulation',True),('confirmed',False)]:
   bad=dict(r);bad[key]=value
   with self.assertRaises(Hold):record_receipt(self.s,aid,bad)
 def test_reconcile_after_lease_expiry_and_duplicate(self):
  t=claim(self.s,'host',self.now);a=action();aid=begin(self.s,t,a,self.observe(),self.now)['action_id'];self.s.db.execute('UPDATE occurrences SET lease=0');record_receipt(self.s,aid,self.receipt(a));self.assertEqual(self.s.db.execute('SELECT state FROM actions').fetchone()[0],'confirmed');self.assertEqual(record_receipt(self.s,aid,self.receipt(a))['remote_id'],'fixture-only')
 def test_unresolved_effect_cannot_finish_success(self):
  t=claim(self.s,'host',self.now);a=action();aid=begin(self.s,t,a,self.observe(),self.now)['action_id'];r={'state':'completed','publication_id':'synthetic-a'}
  with self.assertRaises(Hold):finish(self.s,t,r,self.now)
  record_receipt(self.s,aid,self.receipt(a));self.assertTrue(finish(self.s,t,r,self.now))
if __name__=='__main__':unittest.main(verbosity=2)
