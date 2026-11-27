"""Packaged native-Windows smoke test, deliberately using synthetic photo data."""
import json,time,tempfile,subprocess,sys
from pathlib import Path
from PIL import Image
from PySide6.QtCore import QEventLoop,QTimer
from metadata import exiftool_path,read_metadata
from brand_logos import SOURCES
from reports import create_report,verify_report

def run(app,result_path):
    # Import the entry module by its canonical name in frozen builds too.
    from main import Window
    output=Path(result_path).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    exe=exiftool_path()
    assert exe and Path(exe).is_file(),'Bundled ExifTool is missing'
    result=subprocess.run([exe,'-ver'],capture_output=True,text=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    assert result.returncode==0,result.stderr
    with tempfile.TemporaryDirectory(prefix='exif-reader-selftest-') as folder:
        source=Path(folder)/'synthetic-test.jpg'
        exif=Image.Exif();exif[271]='SONY';exif[272]='ILCE-7M4'
        Image.new('RGB',(480,320),'#ed8a45').save(source,exif=exif)
        window=Window();window.show();app.processEvents()
        for brand in SOURCES:
            window.brand_badge.set_brand(brand)
            assert window.brand_badge.logo_loaded,'Logo did not render: '+brand
        window.load(str(source))
        loop=QEventLoop();window.worker.finished.connect(loop.quit);QTimer.singleShot(45000,loop.quit);loop.exec();app.processEvents()
        assert window.worker is None,'Photo reader timed out'
        assert window.camera.text()=='ILCE-7M4'
        assert window.rating.value()==200000
        assert window.brand_badge.logo_loaded
        assert not window.photo_box.original.isNull()
        assert window.pdf.isEnabled()
        window.grab().save(str(output.with_suffix('.png')))
        pdf=Path(folder)/'test-certificate.pdf'
        create_report(source,window.data,window.engine,window.rating.value(),pdf,window.current_reference())
        assert pdf.read_bytes().startswith(b'%PDF-')
        assert all(verify_report(pdf.with_suffix('.certificate.json'),source,pdf).values())
        window.clear_photo();assert not window.data and not window.pdf.isEnabled()
        window.close();app.processEvents()
    output.write_text(json.dumps(dict(status='passed',frozen=bool(getattr(sys,'frozen',False)),logo_count=len(SOURCES),exiftool=result.stdout.strip(),photo_read=True,pdf_report=True,clear_photo=True),indent=2),encoding='utf-8')
