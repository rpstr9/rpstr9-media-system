"""Validate record shape and material cross-record relationships."""
from pathlib import Path
import argparse,json
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
def validate(records):
 from jsonschema import Draft202012Validator,FormatChecker
 errors=[];index={}
 for r in records:
  kind=r.get('record_type');schema=ROOT/'contracts'/f'{kind}.schema.json'
  if not schema.is_file():errors.append('Unknown record type');continue
  for e in Draft202012Validator(json.loads(schema.read_text()),format_checker=FormatChecker()).iter_errors(r):errors.append(f'{r.get("record_id")}: {list(e.path)} {e.message}')
  if r.get('record_id') in index:errors.append('Duplicate record ID')
  index[r.get('record_id')]=r
 for r in records:
  p=r.get('payload',{});scope=r.get('publication_id_or_system_scope');kind=r.get('record_type')
  for k,v in p.items():
   refs=[v] if k.endswith('_ref') and isinstance(v,str) else v if k.endswith('_refs') and isinstance(v,list) else []
   for ref in refs:
    if not isinstance(ref,str) or not ref.startswith('record:'):continue
    target=index.get(ref[7:])
    if not target:errors.append(f'Missing record reference {ref}')
    elif target['publication_id_or_system_scope'] not in (scope,'system'):errors.append('Cross-publication record reference')
  if p.get('publication_id') and p['publication_id']!=scope:errors.append('Payload/envelope publication mismatch')
  if kind=='LaunchPackage':
   for state in ('prepared','connected','approved','published','recurring_running'):
    if p.get(state) and not p.get('state_evidence',{}).get(state):errors.append('Launch state lacks evidence: '+state)
   if p.get('simulation') and (p.get('published') or p.get('recurring_running')):errors.append('Simulation cannot assert a live launch')
  if kind=='OutcomeRecord':
   if p.get('observation_type')=='unavailable' and p.get('value') is not None:errors.append('Missing observation is not a value')
   if p.get('observation_type')=='simulated' and not p.get('simulation'):errors.append('Simulation label missing')
  if kind=='PublicationReceipt' and p.get('result_status')=='confirmed':
   if not p.get('remote_id') or not p.get('evidence_ref'):errors.append('Confirmed receipt lacks remote evidence')
   if p.get('confirmation_source')=='simulation':errors.append('Use simulation status for simulated publication')
  if kind=='ContentPackage' and p.get('status')=='ready' and p.get('visual_readiness') not in ('ready','not-applicable'):errors.append('Required visual readiness missing')
  if kind=='RecurringJob' and p.get('enabled'):
   if not p.get('timezone') or not p.get('trigger') or not p.get('library_lock_ref'):errors.append('Enabled job lacks timezone, trigger or release')
  if kind=='HandoffEnvelope' and p.get('method_load_status') not in ('complete','blocked','partial'):errors.append('Explicit method load status required')
 return errors
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('records');args=a.parse_args();d=json.loads(Path(args.records).read_text());e=validate(d if isinstance(d,list) else [d]);print(json.dumps({'valid':not e,'errors':e},indent=2));raise SystemExit(bool(e))
