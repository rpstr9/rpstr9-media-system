import copy, hashlib, json, sqlite3, sys, tempfile, time, unittest
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'runtime/reference'),str(ROOT/'scripts')]
from runner import Store,Hold,digest,deliver,slots,validate_plan,export_workspace,restore_workspace
from synthetic_adapter import SyntheticAdapter
import private_learning as learning

def job(now,kind='article-publication',name='one'):
 return {'id':name,'version':1,'kind':kind,'enabled':True,'timezone':'UTC','trigger':{'kind':'interval','seconds':2,'anchor':now},'account':'synthetic-account','active_windows':[],'mode':'bounded-auto','missed':'coalesce-latest','overlap':'buffer-one','freshness_seconds':30,'timeout_seconds':10,'max_attempts':2,'backoff_seconds':1,'budget':dict(actions=20,api_calls=20,tokens=100,spend=0),'executor':[sys.executable,str(ROOT/'evaluations/public-fixtures/synthetic_executor.py')]}
def plan(now):
 budget=dict(actions=20,api_calls=20,tokens=100,spend=0)
 return {'schema_version':'1.0','version':1,'publication_id':'synthetic-a','library_release':'0.1.0','enabled':True,'adapter':'synthetic','jobs':[job(now)],'account_budgets':{'synthetic-account':budget},'authorizations':{'grant':{'starts_at':now-10,'expires_at':now+1000,'accounts':['synthetic-account'],'operations':['article','reply'],'targets':['*'],'content_scope_delegated':True,'budget':budget}},'capabilities':{'synthetic-account':{op:{'status':'verified-available','policy':'permitted','valid_until':now+1000} for op in ('article','reply')}},'health_timeout_seconds':10}
def action():
 text='Synthetic observation with a retained source.'
 return {'publication_id':'synthetic-a','account':'synthetic-account','operation':'article','target':'own','source_event':None,'content':text,'content_hash':digest(text),'authorization_ref':'grant','review_passed':True,'visuals':[],'context_hash':None,'current_context_hash':None,'reserved_cost':dict(actions=1,api_calls=1,tokens=0,spend=0)}
class RuntimeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.now=time.time();self.root=Path(self.temp.name)/'private-a';self.s=Store(self.root,'synthetic-a');self.p=plan(self.now);self.s.configure(self.p,self.now-.1);self.s.enqueue(self.now);self.occ=self.s.claim('worker',self.now);self.adapter=SyntheticAdapter(self.root)
 def tearDown(self):self.s.close();self.temp.cleanup()
 def test_occurrence_dedup(self):
  self.s.enqueue(self.now);self.assertEqual(self.s.db.execute('SELECT count(*) FROM occurrences').fetchone()[0],1)
 def test_publication_isolation(self):
  with self.assertRaises(ValueError):Store(self.root,'synthetic-b')
 def test_plan_change_requires_version(self):
  p=copy.deepcopy(self.p);p['jobs'][0]['trigger']['seconds']=3
  with self.assertRaises(ValueError):self.s.configure(p)
 def test_disabled_template_has_no_jobs(self):
  p=copy.deepcopy(self.p);p['enabled']=False;self.s.configure(p);self.s.enqueue(self.now+4);self.assertEqual(self.s.db.execute('SELECT count(*) FROM occurrences').fetchone()[0],1)
 def test_unknown_write_reconciles_once(self):
  self.adapter.lose_response=True
  with self.assertRaises(TimeoutError):deliver(self.s,self.occ,action(),self.adapter,self.now)
  self.s.close();self.s=Store(self.root,'synthetic-a');self.adapter.lose_response=False
  receipt=deliver(self.s,self.occ,action(),self.adapter,self.now+1)
  self.assertTrue(receipt['simulation']);self.assertEqual(self.adapter.db.execute('SELECT count(*) FROM effects').fetchone()[0],1)
 def test_unknown_without_receipt_is_held(self):
  a=action();aid=digest(['synthetic-a',a['account'],a['operation'],a['target'],None,a['content_hash']]);self.s.db.execute('INSERT INTO actions VALUES(?,?,?,?)',(aid,json.dumps(a),'unknown',None))
  with self.assertRaises(Hold):deliver(self.s,self.occ,a,self.adapter,self.now)
  self.assertEqual(self.adapter.db.execute('SELECT count(*) FROM effects').fetchone()[0],0)
 def test_pause_running_effect(self):
  self.s.pause('account:synthetic-account','test')
  with self.assertRaises(Hold):deliver(self.s,self.occ,action(),self.adapter,self.now)
 def test_stale_worker_fenced(self):
  self.s.db.execute('UPDATE occurrences SET token=token+1 WHERE id=?',(self.occ['id'],))
  with self.assertRaises(Hold):deliver(self.s,self.occ,action(),self.adapter,self.now)
 def test_release_changes_hold_inflight_work(self):
  p=self.s.get('plan');p['library_release']='0.2.0';self.s.put('plan',p)
  with self.assertRaises(Hold):deliver(self.s,self.occ,action(),self.adapter,self.now)
 def test_expired_lease_fenced(self):
  with self.assertRaises(Hold):deliver(self.s,self.occ,action(),self.adapter,self.now+100)
 def test_wrong_account(self):
  a=action();a['account']='other'
  with self.assertRaises(Hold):deliver(self.s,self.occ,a,self.adapter,self.now)
 def test_version_bound_approval(self):
  p=self.s.get('plan');p['authorizations']['grant']['content_scope_delegated']=False;p['authorizations']['grant']['content_hash']='old';self.s.put('plan',p)
  with self.assertRaises(Hold):deliver(self.s,self.occ,action(),self.adapter,self.now)
 def test_tampered_content_hash(self):
  a=action();a['content']='Changed body'
  with self.assertRaises(Hold):deliver(self.s,self.occ,a,self.adapter,self.now)
 def test_draft_only(self):
  j=self.occ['job_config'];j['mode']='draft-only';self.s.db.execute('UPDATE jobs SET config=?',(json.dumps(j),))
  with self.assertRaises(Hold):deliver(self.s,self.occ,action(),self.adapter,self.now)
 def test_platform_permission(self):
  p=self.s.get('plan');p['capabilities']['synthetic-account']['article']['policy']='blocked';self.s.put('plan',p)
  with self.assertRaises(Hold):deliver(self.s,self.occ,action(),self.adapter,self.now)
 def test_human_answered(self):
  self.adapter.context={'human_answered':True}
  with self.assertRaises(Hold):deliver(self.s,self.occ,action(),self.adapter,self.now)
 def test_opt_out(self):
  self.adapter.context={'opt_out':True}
  with self.assertRaises(Hold):deliver(self.s,self.occ,action(),self.adapter,self.now)
 def test_changed_context(self):
  self.adapter.context={'current_context_hash':'new'}
  with self.assertRaises(Hold):deliver(self.s,self.occ,action(),self.adapter,self.now)
 def test_before_state_conflict(self):
  a=action();a.update(expected_before='old',current_before='human-edit')
  with self.assertRaises(Hold):deliver(self.s,self.occ,a,self.adapter,self.now)
 def test_missing_visual(self):
  a=action();a['visuals']=[{'required':True,'path':str(self.root/'missing'),'review':'approved','rights':'cleared'}]
  with self.assertRaises(Hold):deliver(self.s,self.occ,a,self.adapter,self.now)
 def test_actual_visual_hash(self):
  f=self.root/'asset.svg';f.write_text('<svg/>');a=action();a['visuals']=[{'required':True,'path':str(f),'review':'approved','rights':'cleared','sha256':'wrong'}]
  with self.assertRaises(Hold):deliver(self.s,self.occ,a,self.adapter,self.now)
 def test_unconfirmed_canonical(self):
  a=action();a['requires_canonical']=True
  with self.assertRaises(Hold):deliver(self.s,self.occ,a,self.adapter,self.now)
 def test_budget(self):
  a=action();a['reserved_cost']['spend']=1
  with self.assertRaises(Hold):deliver(self.s,self.occ,a,self.adapter,self.now)
 def test_event_dedup_and_atomic_cursor(self):
  e={'account':'synthetic-account','id':'m1','text':'question'};self.s.ingest('synthetic-account',[e,e],2);self.assertEqual(self.s.db.execute('SELECT count(*) FROM events').fetchone()[0],1)
  with self.assertRaises(ValueError):self.s.ingest('synthetic-account',[dict(e,account='other')],99)
  self.assertEqual(json.loads(self.s.db.execute('SELECT cursor FROM cursors').fetchone()[0]),2)
 def test_listener_outage_not_empty(self):
  self.s.ingest('synthetic-account',[],None,'feed unavailable');self.assertTrue(self.s.status()['listener_gaps'])
 def test_health_staleness(self):self.assertEqual(self.s.status(self.now+100)['worker_state'],'stale-or-not-running')
 def test_missed_intervals_coalesce(self):self.assertEqual(len(slots(job(0),0,100000)),1)
 def test_dst_nonexistent_skipped(self):
  j=job(0);j['timezone']='America/New_York';j['trigger']={'kind':'calendar','time':'02:30','weekdays':[6],'dst_fold':'first','dst_gap':'skip'}
  lo=datetime(2026,3,8,tzinfo=timezone.utc).timestamp();self.assertEqual(slots(j,lo,lo+86400),[])
 def test_dst_fold_explicit(self):
  j=job(0);j['timezone']='America/New_York';j['trigger']={'kind':'calendar','time':'01:30','weekdays':[6],'dst_fold':'first','dst_gap':'skip'};lo=datetime(2026,11,1,tzinfo=timezone.utc).timestamp();a=slots(j,lo,lo+86400);j['trigger']['dst_fold']='second';b=slots(j,lo,lo+86400);self.assertEqual(b[0]-a[0],3600)
 def test_quiet_hours(self):
  j=self.occ['job_config'];m=datetime.fromtimestamp(self.now,timezone.utc).hour*60+datetime.fromtimestamp(self.now,timezone.utc).minute;j['active_windows']=[[(m+1)%1440,(m+2)%1440]];self.s.db.execute('UPDATE jobs SET config=?',(json.dumps(j),))
  with self.assertRaises(Hold):deliver(self.s,self.occ,action(),self.adapter,self.now)
 def test_export_restore(self):
  f=self.root/'article.md';f.write_text('Private synthetic text');self.s.put('export_files',['article.md']);self.s.put('export_state_authorized',True);dest=Path(self.temp.name)/'export';export_workspace(self.s,dest);restore=Path(self.temp.name)/'restored';restore_workspace(dest,restore,'synthetic-a');s2=Store(restore,'synthetic-a');self.assertEqual(s2.get('plan')['library_release'],'0.1.0');self.assertEqual((restore/'article.md').read_text(),f.read_text());s2.close()
 def test_export_secret_hold(self):
  self.s.put('bad',{'access_token':'synthetic-sensitive'});self.s.put('export_state_authorized',True)
  with self.assertRaises(ValueError):export_workspace(self.s,Path(self.temp.name)/'export')
 def test_learning_reject_and_rollback(self):
  r={'id':'adapt1','publication_id':'synthetic-a','surface':'editorial-format','baseline':'old','rollback':'old','skill':'media-editorial','release':'0.1.0','expires_at':self.now+100}
  learning.propose(self.s,r);self.assertEqual(learning.decide(self.s,'adapt1',{'protected_regressions':['citation lost'],'benefit_observed':True,'comparable':True},True),'rejected')
  r['id']='adapt2';learning.propose(self.s,r);self.assertEqual(learning.decide(self.s,'adapt2',{'protected_regressions':[],'benefit_observed':True,'comparable':True},True),'approved');self.assertEqual(len(learning.applicable(self.s,'media-editorial','0.1.0',self.now)),1);learning.rollback(self.s,'adapt2','synthetic later regression');self.assertEqual(learning.applicable(self.s,'media-editorial','0.1.0',self.now),[])
 def test_learning_cannot_expand_permissions(self):
  with self.assertRaises(ValueError):learning.propose(self.s,{'publication_id':'synthetic-a','surface':'permissions'})
 def test_insufficient_learning(self):
  learning.propose(self.s,{'id':'weak','publication_id':'synthetic-a','surface':'editorial-format','baseline':'old','rollback':'old'});self.assertEqual(learning.decide(self.s,'weak',{'comparable':False},True),'inconclusive')
if __name__=='__main__':unittest.main(verbosity=2)
