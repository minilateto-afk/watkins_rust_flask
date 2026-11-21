"""Check full 650-material inclusion and that missing observations are never fabricated."""
from pathlib import Path
import unittest
import pandas as pd
from coverage_analysis import build_coverage

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'data'/'processed'

class CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.obs=pd.read_csv(DATA/'observations.csv',dtype={'material_id':str})
        cls.mats=pd.read_csv(DATA/'materials.csv',dtype={'material_id':str})
        cls.audpc=pd.read_csv(DATA/'audpc_njoro_apr_may.csv',dtype={'material_id':str})
        cls.table,cls.info=build_coverage(cls.obs,cls.mats,cls.audpc)

    def test_all_materials_present(self):
        self.assertEqual(len(self.table),650)
        self.assertEqual(len(set(self.table.material_id)),650)
        self.assertEqual(self.info['all_29_measurement_cells'],18850)

    def test_counts_sum_without_imputation(self):
        self.assertEqual(self.info['complete_ijk'],490)
        self.assertEqual(self.info['other_numeric'],111)
        self.assertEqual(self.info['no_numeric'],49)
        self.assertEqual(self.info['any_numeric'],601)
        self.assertEqual(self.info['ijk_valid_distribution'],{'0':154,'1':6,'3':490})

    def test_disease_coverages_not_summed(self):
        self.assertEqual(self.info['any_yellow_adult'],588)
        self.assertEqual(self.info['any_stem_adult'],583)
        self.assertEqual(self.info['any_leaf_adult'],582)
        self.assertEqual(self.info['adult_numeric_entries'],8932)
        self.assertEqual(self.info['seedling_numeric_entries'],1830)

    def test_zero_scores_not_confused_with_missing(self):
        # 0 percent is a *measured* numeric score; it counts towards coverage.
        row=self.table.loc[self.table.material_id=='43'].iloc[0]
        self.assertGreater(row['numeric_count'],0)
        self.assertEqual(row['coverage_group'],'complete_ijk')
        # Every material with no numeric value is still explicitly included.
        empty=self.table.loc[self.table.coverage_group=='no_numeric']
        self.assertTrue((empty.numeric_count==0).all())
        self.assertEqual(len(empty),49)

    def test_no_aggregated_disease_index(self):
        forbidden={'resistance_score','pooled_mean_severity','combined_disease_index'}
        self.assertFalse(forbidden.intersection(self.table.columns))

if __name__=='__main__': unittest.main()
