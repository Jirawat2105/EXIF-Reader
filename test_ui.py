import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,time,unittest,gc
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from PySide6.QtCore import Qt,QCoreApplication,QEvent
from PySide6.QtTest import QTest
from main import QApplication,Window,STYLE,QFileDialog,QFontDatabase,QPushButton

app=QApplication.instance() or QApplication([])
for font in ('segoeui.ttf','segoeuib.ttf','georgia.ttf'):
    p=Path('C:/Windows/Fonts')/font
    if p.exists():QFontDatabase.addApplicationFont(str(p))
app.setStyle('Fusion');app.setStyleSheet(STYLE)

def wait_for_reader(window):
    deadline=time.monotonic()+15
    while window.worker or window.queued:
        if time.monotonic()>deadline:raise AssertionError('Reader did not finish')
        QTest.qWait(10)
    app.processEvents()

class SinglePhotoTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.path=Path(self.folder.name)/'photo.jpg'
        exif=Image.Exif();exif[271]='SONY';exif[272]='ILCE-7M4'
        Image.new('RGB',(120,80),'#ee8833').save(self.path,exif=exif)
        self.window=Window();self.window.show();app.processEvents()
    def tearDown(self):
        wait_for_reader(self.window)
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        app.processEvents()
        self.folder.cleanup()
        # Destroy prior windows on the GUI thread before a later test starts a worker.
        gc.collect()
    def test_click_box_load_and_clear(self):
        w=self.window
        self.assertFalse(w.pdf.isEnabled())
        with patch.object(QFileDialog,'getOpenFileName',return_value=(str(self.path),'Image files')) as dialog:
            QTest.mouseClick(w.photo_box,Qt.MouseButton.LeftButton)
        dialog.assert_called_once();wait_for_reader(w)
        self.assertEqual(w.rating.value(),200000)
        self.assertGreater(w.rating.lineEdit().width(),60)
        self.assertTrue(w.brand_badge.logo_loaded)
        self.assertFalse(w.brand_badge.pixmap().isNull())
        self.assertEqual(w.brand_badge.accessibleName(),'Sony logo')
        self.assertFalse(w.photo_box.original.isNull())
        self.assertTrue(w.pdf.isEnabled())
        QTest.mouseClick(w.clear_button,Qt.MouseButton.LeftButton)
        self.assertIsNone(w.path);self.assertFalse(w.data);self.assertEqual(w.table.rowCount(),0)
        self.assertTrue(w.photo_box.original.isNull());self.assertEqual(w.rating.value(),0)
        self.assertFalse(w.pdf.isEnabled());self.assertFalse(w.export.isEnabled())
    def test_clear_during_read_ignores_late_result(self):
        w=self.window;w.load(str(self.path));w.clear_photo();wait_for_reader(w)
        self.assertIsNone(w.path);self.assertEqual(w.table.rowCount(),0)
        self.assertFalse(w.clear_button.isEnabled());self.assertFalse(w.pdf.isEnabled())
    def test_replacement_queues_latest_photo(self):
        second=Path(self.folder.name)/'second.jpg';Image.new('RGB',(40,40)).save(second)
        w=self.window;w.load(str(self.path));w.load(str(second));wait_for_reader(w)
        self.assertEqual(w.path,str(second));self.assertEqual(w.rating.value(),0)
        self.assertEqual(w.reference_kind.text(),'Not available / No reviewed reference')
        self.assertFalse(any('Batch' in b.text() for b in w.findChildren(QPushButton)))
    def test_cancel_preserves_photo(self):
        w=self.window;w.load(str(self.path));wait_for_reader(w)
        with patch.object(QFileDialog,'getOpenFileName',return_value=('','')):w.choose()
        self.assertEqual(w.path,str(self.path))
    def test_pdf_uses_automatic_provenance(self):
        w=self.window;w.load(str(self.path));wait_for_reader(w)
        destination=Path(self.folder.name)/'certificate.pdf'
        with patch.object(QFileDialog,'getSaveFileName',return_value=(str(destination),'PDF (*.pdf)')):w.save_pdf()
        deadline=time.monotonic()+15
        while w.report_job:
            if time.monotonic()>deadline:raise AssertionError('Report writer did not finish')
            QTest.qWait(10)
        import json
        manifest=json.loads(destination.with_suffix('.certificate.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['record']['reference']['kind'],'Third-party estimate')
        self.assertEqual(manifest['record']['reference_rating'],200000)
        self.assertTrue(w.pdf.isEnabled())

    def test_manual_reference_and_restore(self):
        w=self.window;w.load(str(self.path));wait_for_reader(w)
        w.custom.setChecked(True);w.rating.setValue(150000)
        self.assertEqual(w.current_reference()['kind'],'Manual reference')
        w.custom.setChecked(False);self.assertEqual(w.rating.value(),200000)
        self.assertEqual(w.current_reference()['kind'],'Third-party estimate')

if __name__=='__main__':unittest.main()
