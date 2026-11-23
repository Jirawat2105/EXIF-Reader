import unittest
from ratings import lookup_rating,reference_for

class ReferenceTests(unittest.TestCase):
    def test_exact_model_aliases(self):
        self.assertEqual(lookup_rating({'Make':'NIKON CORPORATION','Model':'NIKON D850'})['cycles'],200000)
        self.assertEqual(lookup_rating({'Make':'NIKON CORPORATION','Model':'NIKON Z 6 II'})['cycles'],200000)
        self.assertEqual(lookup_rating({'Make':'Canon','Model':'Canon EOS R5'})['cycles'],500000)
        self.assertIsNone(lookup_rating({'Make':'Canon','Model':'Canon EOS R5 Mark II'}))
        self.assertIsNone(lookup_rating({'Make':'SONY','Model':'ILCE-7M4A'}))
        self.assertEqual(lookup_rating({'Make':'RICOH IMAGING COMPANY, LTD.','Model':'PENTAX K-1 Mark II'})['cycles'],300000)
    def test_nikon_exif_aliases(self):
        self.assertEqual(lookup_rating({'Make':'NIKON CORPORATION','Model':'NIKON Z 6_2'})['model'],'Z6II')
        self.assertEqual(lookup_rating({'Make':'NIKON CORPORATION','Model':'NIKON Z 6_3'})['model'],'Z6III')

    def test_estimate_not_manufacturer(self):
        data={'Make':'SONY','Model':'ILCE-7M4'}
        ref=reference_for(data,200000)
        self.assertEqual(ref['kind'],'Third-party estimate')
        self.assertTrue(ref['url'].startswith('https://'))
        self.assertEqual(reference_for(data,150000)['kind'],'Manual reference')
    def test_electronic_only(self):
        ref=lookup_rating({'Make':'NIKON CORPORATION','Model':'NIKON Z 8'})
        self.assertIsNone(ref['cycles'])
        self.assertEqual(ref['kind'],'Electronic shutter only')

if __name__=='__main__':unittest.main()
