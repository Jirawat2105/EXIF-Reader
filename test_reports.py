import unittest,tempfile,json
from pathlib import Path
from PIL import Image
from metadata import read_metadata,shutter_count
from reports import create_report,verify_report
from pypdf import PdfReader

class ReportTests(unittest.TestCase):
    def test_pdf_and_tampering(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'photo.jpg';Image.new('RGB',(20,30)).save(source)
            data,engine=read_metadata(source);data['Nikon:ShutterCount']=90000
            pdf=root/'report.pdf';create_report(source,data,engine,100000,pdf)
            manifest=pdf.with_suffix('.certificate.json')
            self.assertTrue(all(verify_report(manifest,source,pdf).values()))
            text=''.join(page.extract_text() for page in PdfReader(pdf).pages)
            self.assertIn('90,000',text);self.assertIn('HIGH USAGE',text);self.assertIn('METADATA APPENDIX',text)
            pdf.write_bytes(pdf.read_bytes()+b'changed');self.assertFalse(verify_report(manifest,source,pdf)['pdf_matches'])
            source.write_bytes(source.read_bytes()+b'changed');self.assertFalse(verify_report(manifest,source,pdf)['source_matches'])
            record=json.loads(manifest.read_text());record['record']['counter_value']=1;manifest.write_text(json.dumps(record));self.assertFalse(verify_report(manifest,source,pdf)['record_matches'])
    def test_refuse_stale_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'photo.jpg';Image.new('RGB',(20,30)).save(source);d,e=read_metadata(source)
            source.write_bytes(source.read_bytes()+b'change')
            with self.assertRaisesRegex(ValueError,'Source changed'):create_report(source,d,e,0,Path(folder)/'r.pdf')
    def test_counter_priority(self):
        self.assertEqual(shutter_count({'Sony:ShutterCount':100,'Sony:MechanicalShutterCount':80}),(80,'MechanicalShutterCount'))
        self.assertEqual(shutter_count({'FileNumber':99,'SequenceNumber':200,'ImageCount':300}),(None,None))

if __name__=='__main__':unittest.main()
