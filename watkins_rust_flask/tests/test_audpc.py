"""Phase 2 regression checks, including independently auditable source examples."""
import json
import math
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from audpc_analysis import (observation_days,trapezoid_audpc,
                           calculate_njoro_audpc, REQUIRED_COLUMNS)

class FormulaTests(unittest.TestCase):
    def test_source_dates_and_time_intervals(self):
        self.assertEqual(REQUIRED_COLUMNS,('I','J','K'))
        self.assertEqual(observation_days(),(0,9,16))

    def test_hand_calculation_material_two(self):
        total,areas=trapezoid_audpc([20,30,30],[0,9,16])
        self.assertEqual(areas,[225.0,210.0])
        self.assertEqual(total,435.0)
        self.assertEqual(total/16,27.1875)

    def test_unequal_intervals_and_zero(self):
        self.assertEqual(trapezoid_audpc([0,0,0],[0,9,16])[0],0)
        self.assertEqual(trapezoid_audpc([50,50,50],[0,9,16])[0],800)
        self.assertEqual(trapezoid_audpc([0,20,60],[0,9,16])[0],370)

    def test_independent_numpy_verification(self):
        for scores in ([20,30,30],[5,15,15],[70,80,90],[0,0,0]):
            actual=trapezoid_audpc(scores,[0,9,16])[0]
            self.assertAlmostEqual(actual,float((np.trapezoid if hasattr(np, "trapezoid") else np.trapz)(scores,[0,9,16])))

    def test_reject_bad_input(self):
        for ys,ts in [([10,20],[0,0]),([10,20],[5,0]),
                      ([10,math.nan],[0,9]),([-1,20],[0,9]),
                      ([10,101],[0,9]),([10,20],[0]),([10],[0])]:
            with self.subTest(ys=ys,ts=ts):
                with self.assertRaises(ValueError):trapezoid_audpc(ys,ts)

class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.obs=pd.read_csv(ROOT/'data/processed/observations.csv',
                            dtype={'material_id':str,'measurement_id':str},keep_default_na=False)
        cls.mats=pd.read_csv(ROOT/'data/processed/materials.csv',dtype={'material_id':str},keep_default_na=False)

    def test_complete_cases_and_range(self):
        good,bad,s=calculate_njoro_audpc(self.obs,self.mats)
        self.assertEqual((len(good),len(bad)),(490,160))
        self.assertEqual(s['per_date_valid'],{'I':496,'J':490,'K':490})
        self.assertAlmostEqual(s['median_audpc'],630)
        self.assertAlmostEqual(s['mean_audpc'],608.5204081632653)
        self.assertTrue(good['audpc_pct_days'].between(0,1600).all())
        self.assertTrue(good['time_weighted_mean_pct'].between(0,100).all())
        self.assertEqual(set(good.material_id)&set(bad.material_id),set())
        self.assertEqual(set(good.material_id)|set(bad.material_id),set(self.mats.material_id))

    def test_material_two_exact_real_source(self):
        good,bad,_=calculate_njoro_audpc(self.obs,self.mats)
        row=good.set_index('material_id').loc['2']
        self.assertEqual([row['I_raw'],row['J_raw'],row['K_raw']],['20MR','30MR','30MR'])
        self.assertEqual([row['apr21_pct'],row['apr30_pct'],row['may07_pct']],[20,30,30])
        self.assertEqual((row['area_apr21_apr30'],row['area_apr30_may07']),(225,210))
        self.assertEqual(row['audpc_pct_days'],435)

    def test_strict_exclusion_for_trace_range_missing(self):
        sample=self.obs[self.obs.material_id=='2'].copy()
        mats=self.mats[self.mats.material_id=='2'].copy()
        for status in ['trace_not_quantified','range_or_interval','missing_marker']:
            mutated=sample.copy()
            selector=mutated.measurement_id=='J'
            mutated.loc[selector,'parse_status']=status
            mutated.loc[selector,'severity_pct']=float('nan')
            good,bad,_=calculate_njoro_audpc(mutated,mats)
            self.assertEqual((len(good),len(bad)),(0,1))
            self.assertIn(status,bad.iloc[0]['reason'])

    def test_no_wrong_site_or_duplicate(self):
        subset=self.obs[self.obs.material_id=='2'].copy()
        mats=self.mats[self.mats.material_id=='2'].copy()
        subset.loc[subset.measurement_id=='I','site']='Meraro'
        with self.assertRaises(ValueError):calculate_njoro_audpc(subset,mats)
        src=self.obs[self.obs.material_id=='2'].copy()
        row=src[src.measurement_id=='I'].copy()
        with self.assertRaises(ValueError):calculate_njoro_audpc(pd.concat([src,row]),mats)

    def test_export_matches_computation(self):
        good,_,s=calculate_njoro_audpc(self.obs,self.mats)
        exported=pd.read_csv(ROOT/'data/processed/audpc_njoro_apr_may.csv',dtype={'material_id':str})
        self.assertEqual(len(exported),len(good))
        np.testing.assert_allclose(exported['audpc_pct_days'].values,good['audpc_pct_days'].values)
        json_summary=json.loads((ROOT/'data/processed/audpc_summary.json').read_text(encoding='utf-8'))
        self.assertEqual(s['complete_materials'],json_summary['complete_materials'])

if __name__=='__main__':unittest.main()
