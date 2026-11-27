import hashlib,unittest
from PySide6.QtWidgets import QApplication
from brand_logos import SOURCES,LOGOS,logo_pixmap
class LogoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_downloaded_artwork_and_all_renderers(self):
        self.assertEqual(len(SOURCES),14)
        for brand,source in SOURCES.items():
            with self.subTest(brand=brand):
                self.assertTrue(source['url'].startswith('https://upload.wikimedia.org/'))
                self.assertEqual(hashlib.sha256((LOGOS/source['file']).read_bytes()).hexdigest(),source['sha256'])
                self.assertFalse(logo_pixmap(brand).isNull())
    def test_unknown_brand_no_fabricated_artwork(self):self.assertTrue(logo_pixmap('Imaginary Camera').isNull())
if __name__=='__main__':unittest.main()
