import unittest
from metadata import condition, shutter_count, read_metadata
from PIL import Image
import tempfile
from pathlib import Path
class MetadataTests(unittest.TestCase):
    def test_thresholds(self):
        for n,prefix in [(0,'GOOD'),(49999,'GOOD'),(50000,'MODERATE'),(79999,'MODERATE'),(80000,'HIGH'),(150000,'HIGH')]:
            self.assertTrue(condition(n,100000)[0].startswith(prefix))
        self.assertIsNone(condition(None,100000)[2])
        self.assertIsNone(condition(100,0)[2])
    def test_counter(self):
        self.assertEqual(shutter_count({'Nikon:ShutterCount':1234}),(1234,'ShutterCount'))
        self.assertEqual(shutter_count({'FileNumber':1234}),(None,None))
        self.assertEqual(shutter_count({'ShutterCount':-1}),(None,None))
    def test_file(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.jpg';im=Image.new('RGB',(100,60));exif=Image.Exif();exif[271]='Test Camera';im.save(path,exif=exif)
            data,_=read_metadata(path)
            self.assertTrue(any(str(v)=='Test Camera' for v in data.values()))
if __name__=='__main__':unittest.main()
