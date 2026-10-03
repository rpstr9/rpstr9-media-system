"""Offline calculation from supplied observations; never authenticates them."""
import argparse
import json
import math
from pathlib import Path

FIELDS = ('account', 'item', 'start', 'end', 'population', 'definition_ref', 'evidence_ref', 'aggregated_at')


def metric_pair(numerator, denominator, mode='pv-impression-proxy'):
    if mode not in ('pv-impression-proxy', 'ctr'):
        raise ValueError('Unsupported metric mode')
    label = 'PV/impression diagnostic proxy' if mode == 'pv-impression-proxy' else 'CTR'
    out = {'metric': label, 'status': 'unavailable', 'value': None,
           'numerator': numerator.get('value'), 'denominator': denominator.get('value'),
           'population_matched': False, 'attribution_verified_by_helper': False, 'reasons': []}
    for obs in (numerator, denominator):
        if any(not isinstance(obs.get(f), str) or not obs[f].strip() for f in FIELDS):
            out['reasons'].append('missing observation scope, definition, time or evidence')
        v = obs.get('value')
        if isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or v < 0:
            out['reasons'].append('unavailable or invalid count')
    for f in ('account', 'item', 'start', 'end'):
        if numerator.get(f) != denominator.get(f):
            out['reasons'].append('incompatible ' + f)
    names = ('page_views', 'impressions') if mode == 'pv-impression-proxy' else ('clicks', 'impressions')
    if (numerator.get('kind'), denominator.get('kind')) != names:
        out['reasons'].append('incompatible metric definitions')
    if denominator.get('value') == 0:
        out['reasons'].append('zero denominator')
    population_matched = numerator.get('population') == denominator.get('population')
    out['population_matched'] = population_matched
    if mode == 'ctr':
        for f in ('population', 'exposure_set', 'attribution_definition'):
            if not numerator.get(f) or numerator.get(f) != denominator.get(f):
                out['reasons'].append('unmatched ' + f)
        if not out['reasons'] and numerator['value'] > denominator['value']:
            out['reasons'].append('click count exceeds the declared eligible exposures')
    if out['reasons']:
        out['reasons'] = list(dict.fromkeys(out['reasons']))
        return out
    out.update(status='diagnostic' if mode == 'pv-impression-proxy' else 'calculated-from-supplied-evidence',
               value=numerator['value'] / denominator['value'])
    if mode == 'pv-impression-proxy':
        out['reasons'].append('PV may include external/direct traffic; ratio is not opening probability or CTR')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    print(json.dumps(metric_pair(data['numerator'], data['denominator'], data.get('mode', 'pv-impression-proxy')), ensure_ascii=False, indent=2))
