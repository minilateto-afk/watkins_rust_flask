import unittest
from pathlib import Path
import sys
import pandas as pd
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from prepare_data import parse_score,build_from_rows
from measurements import MEASUREMENTS

class CleaningTest(unittest.TestCase):
    def test_explicit_percent(self):
        x=parse_score('50MR','adult')
        self.assertEqual((x['severity_pct'],x['reaction'],x['parse_status']), (50.0,'MR','adult_severity'))
    def test_zero_is_real_zero(self):
        x=parse_score(0,'adult')
        self.assertEqual(x['severity_pct'],0.0)
        self.assertEqual(x['parse_status'],'adult_severity')
    def test_trace_not_zero(self):
        x=parse_score('TMS','adult')
        self.assertIsNone(x['severity_pct'])
        self.assertEqual(x['parse_status'],'trace_not_quantified')
    def test_interval_not_midpoint(self):
        x=parse_score('0-20MSS','adult')
        self.assertIsNone(x['severity_pct'])
        self.assertEqual(x['parse_status'],'range_or_interval')
    def test_special_note(self):
        self.assertEqual(parse_score('DRY','adult')['parse_status'],'special_note')
        self.assertEqual(parse_score('SUSC','adult')['parse_status'],'special_note')
    def test_seedling_not_percent(self):
        x=parse_score(3,'seedling')
        self.assertIsNone(x['severity_pct'])
        self.assertEqual(x['seedling_score'],3)
    def test_unparsed_marker(self):
        self.assertEqual(parse_score('Sr26','seedling')['parse_status'],'unparsed')
    def test_missing(self):
        self.assertEqual(parse_score(';','adult')['parse_status'],'missing_marker')
        self.assertEqual(parse_score(None,'adult')['parse_status'],'blank')
    def test_measurement_id_unique(self):
        self.assertEqual(len(MEASUREMENTS),29)
        self.assertEqual(len({m.column for m in MEASUREMENTS}),29)

class ProcessedFilesTest(unittest.TestCase):
    def test_processed_integrity(self):
        path=ROOT/'data/processed'
        obs=pd.read_csv(path/'observations.csv')
        mats=pd.read_csv(path/'materials.csv')
        self.assertEqual(len(mats),650)
        self.assertEqual(len(obs),18850)
        self.assertEqual(obs['material_id'].nunique(),650)
        self.assertEqual((obs.parse_status=='adult_severity').sum(),8932)
        self.assertEqual((obs.parse_status=='seedling_score').sum(),1830)
        self.assertTrue(obs.loc[obs.parse_status!='adult_severity','severity_pct'].isna().all())
        self.assertTrue((obs.severity_pct.dropna().between(0,100)).all())

if __name__ == '__main__':unittest.main()

class HandCalculationTest(unittest.TestCase):
    def test_first_five_april_21(self):
        path=ROOT/'data/processed/observations.csv'
        obs=pd.read_csv(path)
        first=obs[obs.measurement_id=='I'].head(5)
        values=first.severity_pct.tolist()
        self.assertEqual(values,[50.,20.,20.,30.,30.])
        self.assertAlmostEqual(sum(values)/len(values),30.0)
        self.assertAlmostEqual(pd.Series(values).std(ddof=1)**2,150.0)
