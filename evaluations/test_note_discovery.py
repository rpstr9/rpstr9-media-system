"""Synthetic offline metric decisions; no live observation or attribution proof."""
import importlib.util
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('metrics', ROOT / 'scripts/note_discovery_metrics.py')
metrics = importlib.util.module_from_spec(spec); spec.loader.exec_module(metrics)


def observation(kind, value, population='all-arrivals'):
    return dict(kind=kind, value=value, account='synthetic-account', item='synthetic-item', start='2026-10-01', end='2026-10-02', population=population, definition_ref='synthetic-definition', evidence_ref='synthetic-observation', aggregated_at='2026-10-03T00:00Z')


class MetricBehavior(unittest.TestCase):
    def test_external_pv_is_a_proxy_above_one_without_clamping(self):
        out = metrics.metric_pair(observation('page_views', 160), observation('impressions', 100, 'note-exposures'))
        self.assertEqual(out['value'], 1.6); self.assertEqual(out['status'], 'diagnostic')
        self.assertFalse(out['population_matched']); self.assertNotEqual(out['metric'], 'CTR')

    def test_note_source_pv_still_does_not_become_clicks(self):
        n = observation('page_views', 40, 'note-exposures'); d = observation('impressions', 100, 'note-exposures')
        self.assertEqual(metrics.metric_pair(n, d)['metric'], 'PV/impression diagnostic proxy')
        self.assertEqual(metrics.metric_pair(n, d, 'ctr')['status'], 'unavailable')

    def test_zero_exposure_does_not_report_zero_performance(self):
        out = metrics.metric_pair(observation('page_views', 8), observation('impressions', 0))
        self.assertIsNone(out['value']); self.assertIn('zero denominator', out['reasons'])

    def test_missing_and_invalid_counts_are_not_zero(self):
        for value in [None, -1, True, float('inf'), float('nan'), '30']:
            with self.subTest(value=value):
                self.assertIsNone(metrics.metric_pair(observation('page_views', value), observation('impressions', 100))['value'])

    def test_different_account_item_and_window_cannot_be_combined(self):
        for field in ('account', 'item', 'start', 'end'):
            n = observation('page_views', 30); d = observation('impressions', 100); d[field] = 'other'
            out = metrics.metric_pair(n, d)
            self.assertIsNone(out['value']); self.assertIn('incompatible ' + field, out['reasons'])

    def test_missing_definition_and_evidence_hold_calculation(self):
        for field in ('definition_ref', 'evidence_ref', 'aggregated_at', 'population'):
            n = observation('page_views', 30); d = observation('impressions', 100); n.pop(field)
            self.assertIsNone(metrics.metric_pair(n, d)['value'])

    def test_actual_matching_clicks_and_exposure_can_be_calculated(self):
        n = observation('clicks', 12, 'eligible-native-exposures'); d = observation('impressions', 100, 'eligible-native-exposures')
        for obs in (n, d):obs.update(exposure_set='native-matched-set-1', attribution_definition='unique clicked eligible exposures')
        out = metrics.metric_pair(n, d, 'ctr')
        self.assertEqual(out['value'], .12); self.assertEqual(out['metric'], 'CTR')
        self.assertEqual(out['status'], 'calculated-from-supplied-evidence'); self.assertFalse(out['attribution_verified_by_helper'])

    def test_clicks_from_different_population_are_held(self):
        n = observation('clicks', 12); d = observation('impressions', 100, 'native-only')
        for obs in (n, d):obs.update(exposure_set='set-1', attribution_definition='unique-exposure-click')
        self.assertIsNone(metrics.metric_pair(n, d, 'ctr')['value'])

    def test_unmatched_or_undocumented_click_attribution_is_held(self):
        for field in ('exposure_set', 'attribution_definition'):
            n = observation('clicks', 12); d = observation('impressions', 100)
            for obs in (n, d):obs.update(exposure_set='set-1', attribution_definition='unique-exposure-click')
            d[field] = 'other'
            self.assertIsNone(metrics.metric_pair(n, d, 'ctr')['value'])

    def test_unavailable_kind_is_not_relabelled(self):
        self.assertIsNone(metrics.metric_pair(observation('old_mobile_combined_views', 30), observation('impressions', 100))['value'])


if __name__ == '__main__':unittest.main(verbosity=2)
