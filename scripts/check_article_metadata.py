"""Check an article's private native metadata handoff; performs no remote action."""
import argparse,json

def _tags(value):
    if not isinstance(value,list):raise ValueError('Tag list is missing')
    out=[]
    for t in value:
        if not isinstance(t,str) or not t.strip() or t.strip().startswith('#'):
            raise ValueError('Use native tag names without body hashtag markers')
        out.append(t.strip())
    if len(out)!=len(set(out)):raise ValueError('Duplicate native tags')
    return set(out)

def check(metadata,stage='prepared'):
    if not isinstance(metadata,dict):raise ValueError('Native article metadata is missing')
    if not metadata.get('platform') or not metadata.get('content_hash'):
        raise ValueError('Metadata must bind platform and exact content hash')
    if metadata['platform']!='note' and metadata.get('tag_policy')=='not-applicable':
        if not metadata.get('reason'):raise ValueError('Explain non-applicable tag metadata')
        return {'stage':stage,'status':'not-applicable'}
    if metadata.get('native_field')!='hashtags':
        raise ValueError('Native hashtag field is missing; body tags are insufficient')
    proposed=metadata.get('planned_tags')
    if not isinstance(proposed,list) or not proposed:raise ValueError('Planned native tags are missing')
    if any(not isinstance(x,dict) or not x.get('reason') for x in proposed):
        raise ValueError('Each planned tag needs a task-specific relevance reason')
    tags=_tags([x.get('tag') for x in proposed]);prior=_tags(metadata.get('prior_valid_tags',[]))
    if not prior<=tags:raise ValueError('A valid existing tag was lost from the plan')
    checkpoints=[] if stage=='prepared' else (['saved'] if stage=='saved' else ['saved','public'])
    for checkpoint in checkpoints:
        observation=metadata.get(checkpoint)
        if not isinstance(observation,dict):raise ValueError(checkpoint+' native tag observation is missing')
        expected='native_hashtag_field' if checkpoint=='saved' else 'public_hashtag_metadata'
        if observation.get('location')!=expected:raise ValueError('Body text is not native/public hashtag metadata')
        if observation.get('observation_mode')!='actual' or not observation.get('evidence_ref'):
            raise ValueError('Retain actual tag observation evidence; preparation/simulation is insufficient')
        if observation.get('content_hash')!=metadata['content_hash']:raise ValueError('Tag observation is for another content version')
        observed=_tags(observation.get('tags'))
        if not tags<=observed:raise ValueError('Planned native tags are missing from '+checkpoint+' metadata')
    return {'stage':stage,'status':'complete-record','remote_evidence_verified_by_script':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('metadata');p.add_argument('--stage',choices=['prepared','saved','public'],default='prepared');a=p.parse_args()
    try:print(json.dumps(check(json.load(open(a.metadata)),a.stage)))
    except ValueError as e:p.exit(2,str(e)+'\n')
