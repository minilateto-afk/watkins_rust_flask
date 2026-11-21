"""Third phase math & provenance checks. Can run without Flask or Docker."""
import json
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from findings_analysis import build_findings, select_low_audpc, check_complete_cases, PERCENTILES

class Phase3MathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.good = pd.read_csv(ROOT/'data/processed/audpc_njoro_apr_may.csv',dtype={'material_id':str,'accession':str})
        cls.results, cls.summary = build_findings(cls.good)

    def test_same_cohort_every_date(self):
        self.assertEqual(len(self.results),490)
        self.assertEqual([d['n'] for d in self.summary['dates_stats']], [490]*3)
        self.assertEqual([round(d['mean'],5) for d in self.summary['dates_stats']], [31.5, 38.73469, 44.82653])
        self.assertEqual([d['median'] for d in self.summary['dates_stats']], [30.0,40.0,50.0])

    def test_direction_all_materials_counted(self):
        self.assertEqual(self.summary['direction_counts'], {'增加':420,'不變':68,'下降':2})
        self.assertEqual(sum(self.summary['direction_counts'].values()),490)
        self.assertAlmostEqual(self.summary['delta_mean_pp'], 13.326530612244898)
        self.assertAlmostEqual(self.summary['delta_median_pp'],10)
        self.assertEqual(self.results['delta_16d_pct_points'].tolist(),
                         (self.good.may07_pct-self.good.apr21_pct).tolist())

    def test_real_source_pair_same_area_different_curve(self):
        byid=self.results.set_index('material_id')
        first=byid.loc['43']; second=byid.loc['436']
        self.assertEqual([first.I_raw,first.J_raw,first.K_raw],['0','10MR','10MR'])
        self.assertEqual([second.I_raw,second.J_raw,second.K_raw],['5MR','5MR','15MR'])
        self.assertEqual([first.apr21_pct,first.apr30_pct,first.may07_pct],[0,10,10])
        self.assertEqual([second.apr21_pct,second.apr30_pct,second.may07_pct],[5,5,15])
        self.assertEqual((first.audpc_pct_days,second.audpc_pct_days),(115,115))
        self.assertNotEqual(first.delta_first_interval_pp,second.delta_first_interval_pp)

    def test_5_10_20_25_percentiles_keep_ties(self):
        expected = {5:(0,30),10:(150,51),20:(320,99),25:(413.125,123)}
        for p in PERCENTILES:
            with self.subTest(p=p):
                got, meta=select_low_audpc(self.good,p)
                cutoff,count=expected[p]
                self.assertAlmostEqual(meta['cutoff'],cutoff)
                self.assertEqual(meta['selected'],count)
                self.assertEqual(len(got),count)
                self.assertTrue((got.audpc_pct_days<=cutoff).all())
                self.assertTrue(got.material_id.is_unique)

    def test_invalid_inputs_cannot_silently_pass(self):
        with self.assertRaises(ValueError):select_low_audpc(self.good, 50)
        wrong=self.good.copy()
        wrong.loc[0,'audpc_pct_days'] += 1
        with self.assertRaises(ValueError):check_complete_cases(wrong)
        dup=pd.concat([self.good,self.good.iloc[[0]]])
        with self.assertRaises(ValueError):build_findings(dup)

    def test_export_consistency(self):
        exported=pd.read_csv(ROOT/'data/processed/findings_matched_490.csv',dtype={'material_id':str})
        self.assertEqual(exported.shape[0],490)
        np.testing.assert_allclose(exported.delta_16d_pct_points,self.results.delta_16d_pct_points)
        summary=json.loads((ROOT/'data/processed/findings_summary.json').read_text(encoding='utf-8'))
        self.assertEqual(summary['direction_counts'],self.summary['direction_counts'])
        self.assertEqual(summary['low_10_percent']['selected'],51)
        low=pd.read_csv(ROOT/'data/processed/low_audpc_p10_exploratory.csv',dtype={'material_id':str})
        self.assertEqual(len(low),51)

if __name__ == '__main__':
    unittest.main()
