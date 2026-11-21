"""Regression tests for material lookup and comparison, independently of Flask."""
import unittest
import pandas as pd
from pathlib import Path
from search_utils import search_materials, resolve_material_ids, normalize_query
from findings_analysis import select_low_audpc

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'data'/'processed'

class MaterialLookupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mats=pd.read_csv(DATA/'materials.csv',dtype={'material_id':str,'accession':str},keep_default_na=False)
        cls.good=pd.read_csv(DATA/'findings_matched_490.csv',dtype={'material_id':str,'accession':str},keep_default_na=False)

    def test_all_materials_are_accessible(self):
        self.assertEqual(len(search_materials(self.mats,'')),650)

    def test_excel_serial_lookup(self):
        self.assertEqual(search_materials(self.mats,'43').iloc[0].material_id,'43')
        self.assertEqual(search_materials(self.mats,'650').iloc[0].material_id,'650')

    def test_accession_lookup_and_fullwidth_digits(self):
        self.assertEqual(search_materials(self.mats,'1190202').iloc[0].material_id,'2')
        self.assertEqual(search_materials(self.mats,'１１９０２０２').iloc[0].material_id,'2')

    def test_cultivar_country_and_missing(self):
        self.assertEqual(search_materials(self.mats,'Galberie').iloc[0].material_id,'1')
        self.assertGreater(len(search_materials(self.mats,'Spain')),0)
        self.assertEqual(len(search_materials(self.mats,'no_such_cultivar_90812')),0)

    def test_curve_comparison_with_excel_and_accession_ids(self):
        ids,unknown=resolve_material_ids(self.good,'43,436')
        self.assertEqual(ids,['43','436']);self.assertEqual(unknown,[])
        ids,unknown=resolve_material_ids(self.good,'1190201, 1190202')
        self.assertEqual(ids,['1','2']);self.assertEqual(unknown,[])
        ids,unknown=resolve_material_ids(self.good,'43,9999999')
        self.assertEqual(ids,['43']);self.assertEqual(unknown,['9999999'])

    def test_comparison_percentile_and_query(self):
        cohort,bounds=select_low_audpc(self.good,10)
        self.assertEqual(len(cohort),51)
        self.assertEqual(bounds['cutoff'],150.0)
        self.assertEqual(len(search_materials(self.good,'1190202')),1)
        self.assertEqual(len(search_materials(cohort,'1190202')),0)

if __name__=='__main__': unittest.main()
