"""Real Flask endpoint tests (also executed by the Docker image build)."""
import unittest

try:
    from app import app
except ModuleNotFoundError as exc:
    if exc.name in {'flask','werkzeug'}:
        app=None
    else:
        raise

@unittest.skipUnless(app is not None, 'Flask is unavailable in the current environment; Docker image installs it.')
class FlaskQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=app.test_client()

    def _check(self,path,expected):
        response=self.client.get(path)
        self.assertEqual(response.status_code,200, (path,response.data[:300]))
        body=response.get_data(as_text=True)
        for text in expected:
            self.assertIn(text,body,path)

    def test_material_by_excel_serial(self):
        self._check('/materials?q=43',['材料查詢','43','觀測明細'])

    def test_material_by_accession(self):
        self._check('/materials?q=1190202',['1190202','Manitoba velloso','觀測明細'])

    def test_material_details_with_audpc(self):
        self._check('/materials/2',['435','1190202','觀測欄位明細'])

    def test_material_not_complete_still_has_detail(self):
        self._check('/materials/650',['觀測明細','650'])

    def test_screening_lookup_and_comparison(self):
        self._check('/screening?q=1190202&percentile=10',['1190202','435','未達門檻'])
        self._check('/screening?compare=43,436',['/materials/43','/materials/436','1190048','1190527'])

    def test_screening_accession_comparison(self):
        # Check the actual mapped materials, independent of presentation wording.
        self._check('/screening?compare=1190048,1190527',
                    ['/materials/43', '/materials/436', '1190048', '1190527'])

    def test_invalid_accession_in_comparison(self):
        self._check('/screening?compare=43,9999999',
                    ['/materials/43', '9999999', '無法辨識'])

    def test_unknown_query_handling(self):
        self._check('/materials?q=no_such_cultivar_90812',['查無符合'])
        self._check('/screening?q=no_such_cultivar_90812',['沒有符合'])

    def test_audpc_unknown_material_not_replaced_by_default(self):
        self._check('/audpc?id=9999999',['9999999','不具備本系列完整 AUDPC'])

if __name__=='__main__':unittest.main()
