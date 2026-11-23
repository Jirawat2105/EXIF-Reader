"""EMBER EXIF desktop inspector. Single-photo workflow; metadata remains local."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, Slot, QUrl, QSize
from PySide6.QtGui import QPixmap, QImageReader, QImage, QTransform, QFontDatabase, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QFrame, QFileDialog, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QSpinBox, QProgressBar, QAbstractItemView, QMessageBox,
    QScrollArea, QSizePolicy, QCheckBox, QGridLayout,
)
from metadata import read_metadata, value, shutter_count, condition, preview_bytes
from ratings import lookup_rating, reference_for, camera_brand, ENTRIES
from reports import create_report, verify_report

SUPPORTED = {'.jpg','.jpeg','.tif','.tiff','.png','.webp','.heic','.heif','.hif',
             '.nef','.nrw','.arw','.sr2','.srf','.crw','.cr2','.cr3','.dng',
             '.raf','.orf','.ori','.rw2','.rwl','.pef','.ptx','.srw','.3fr',
             '.fff','.iiq','.x3f','.raw','.mos','.mrw','.kdc','.dcr'}
STYLE = """
QWidget {background:#101216; color:#edf0f4; font-family:'Segoe UI'; font-size:13px;}
QLabel {background:transparent; border:0;}
QLabel#brand {font-size:21px; font-weight:800; letter-spacing:1px;}
QLabel#hero {font-size:28px; font-weight:700;}
QLabel#muted {color:#929aaa; font-size:12px;}
QLabel#eyebrow {color:#ff995c; font-size:10px; font-weight:700; letter-spacing:1.4px;}
QLabel#number {font-size:48px; font-weight:700;}
QLabel#model {font-size:20px; font-weight:700;}
QLabel#small {color:#919aaa; font-size:11px;}
QFrame#card {background:#191d24; border:1px solid #2b323d; border-radius:16px;}
QFrame#photoBox {background:#12161c; border:1px dashed #4b5665; border-radius:12px;}
QFrame#photoBox:hover, QFrame#photoBox:focus {border:1px solid #ff995c; background:#1e2229;}
QPushButton {background:#242b35; border:1px solid #37414f; border-radius:8px; padding:10px 16px; font-size:12px; font-weight:600;}
QPushButton:hover {background:#323b48; border-color:#596779;}
QPushButton:focus {border-color:#ff995c;}
QPushButton#primary {background:#ff8c45; color:#17120e; border:1px solid #ff8c45;}
QPushButton#primary:hover {background:#ffa66d;}
QPushButton#primary:disabled {background:#282f38;color:#667181;border-color:#343d48;}
QPushButton:disabled {background:#20252c; color:#616b79; border-color:#2e3540;}
QPushButton#link {background:transparent; border:0; color:#ffad79; padding:0; text-align:left; font-size:11px;}
QPushButton#link:disabled {color:#7c8797;}
QLineEdit, QSpinBox {background:#12171e; border:1px solid #343f4d; border-radius:8px; padding:9px; selection-background-color:#744425;}
QSpinBox:disabled {color:#7f8998;}
QCheckBox {background:transparent; color:#a8b1bf; font-size:11px; spacing:7px;}
QCheckBox::indicator {width:14px; height:14px; border:1px solid #566174; background:#12171e; border-radius:3px;}
QCheckBox::indicator:checked {background:#ff995c; border-color:#ff995c;}
QTableWidget {background:#191d24; alternate-background-color:#1e242d; border:0; gridline-color:#2b333e; selection-background-color:#533a2b;}
QHeaderView::section {background:#252d38; color:#a5b0c0; border:0; padding:9px; font-size:11px; font-weight:600;}
QProgressBar {border:0; background:#303947; border-radius:4px; min-height:8px; max-height:8px;}
QProgressBar::chunk {background:#ff995c; border-radius:4px;}
QScrollArea {border:0; background:transparent;}
QScrollBar:vertical {background:#151a21; width:9px; margin:0;}
QScrollBar::handle:vertical {background:#424e60; min-height:26px; border-radius:4px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent;}
"""

def label(text='', name=None):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    if name: widget.setObjectName(name)
    return widget

def card(title):
    frame = QFrame()
    frame.setObjectName('card')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22,20,22,20)
    layout.setSpacing(12)
    layout.addWidget(label(title,'eyebrow'))
    return frame,layout

class PhotoBox(QFrame):
    clicked = Signal()
    def __init__(self):
        super().__init__()
        self.setObjectName('photoBox')
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName('Choose a photo')
        self.setToolTip('Click to choose or replace a photo. You can also drop one image here.')
        self.original = QPixmap()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16,16,16,16)
        layout.setSpacing(10)
        self.image = label()
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Ignored)
        self.image.setMinimumHeight(140)
        self.hint = label('Click to choose a photo','small')
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for child in (self.image,self.hint): child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.image,1)
        layout.addWidget(self.hint)
        self.reset()
    def reset(self):
        self.original=QPixmap()
        self.image.clear()
        self.image.setText('+\n\nChoose a photo\n\nRAW / JPEG / HEIC / TIFF')
        self.hint.setText('Click here or drop one image')
    def set_image(self,image):
        self.original=QPixmap.fromImage(image) if not image.isNull() else QPixmap()
        self.image.clear()
        if self.original.isNull():self.image.setText('Preview unavailable\n\nMetadata is still available.')
        else:self.fit()
        self.hint.setText('Click to replace photo')
    def fit(self):
        if not self.original.isNull():
            self.image.setPixmap(self.original.scaled(self.image.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.fit()
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.clicked.emit();event.accept()
        else:super().mousePressEvent(event)
    def keyPressEvent(self,event):
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter,Qt.Key.Key_Space):self.clicked.emit();event.accept()
        else:super().keyPressEvent(event)

class BrandBadge(QLabel):
    """Local typographic manufacturer badge; no network image dependency."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(126,78)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_brand('CAMERA')
    def set_brand(self,brand):
        palettes={
            'Sony':('SONY','#0a0c10','#ffffff','Georgia',23),
            'Nikon':('Nikon','#f7d72c','#141414','Segoe UI',24),
            'Canon':('Canon','#fafafa','#c6252f','Georgia',24),
            'Fujifilm':('FUJIFILM','#0d1516','#f1f7f5','Segoe UI',16),
            'Pentax':('PENTAX','#15151b','#ee4e59','Segoe UI',21),
            'OM SYSTEM':('OM SYSTEM','#10171c','#eff2f6','Segoe UI',15),
            'Panasonic':('LUMIX','#10161f','#f2f6fa','Segoe UI',23),
            'Ricoh':('RICOH','#fafafa','#b91c37','Segoe UI',23),
            'Leica':('Leica','#bd1922','#ffffff','Georgia',24),
            'Hasselblad':('HASSELBLAD','#10151b','#e7eef4','Segoe UI',12),
        }
        text,bg,fg,font,size=palettes.get(brand,(brand.upper()[:18],'#202833','#aeb9c9','Segoe UI',14))
        self.setText(text)
        self.setToolTip(brand+' / camera manufacturer')
        self.setStyleSheet(f'background:{bg};color:{fg};font-family:"{font}";font-size:{size}px;font-weight:700;border:1px solid #3c4654;border-radius:10px;')

class Reader(QThread):
    done=Signal(object,str,bytes)
    failed=Signal(str)
    def __init__(self,path,token,parent=None):
        super().__init__(parent)
        self.path=path
        self.token=token
    def run(self):
        try:
            data,engine=read_metadata(self.path)
            try:preview=preview_bytes(self.path)
            except Exception:preview=b''
            self.done.emit(data,engine,preview)
        except Exception as error:self.failed.emit(str(error))

class ReportWriter(QThread):
    done=Signal(str)
    failed=Signal(str)
    def __init__(self,path,data,engine,rating,dest,reference,parent=None):
        super().__init__(parent)
        self.args=(path,dict(data),engine,rating,dest,dict(reference))
    def run(self):
        try:self.done.emit(create_report(*self.args))
        except Exception as error:self.failed.emit(str(error))

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data={}
        self.path=None
        self.engine=''
        self.worker=None
        self.report_job=None
        self.token=0
        self.queued=None
        self.reference=None
        self.setWindowTitle('EMBER EXIF / Camera Inspector')
        self.resize(1280,940)
        self.setMinimumSize(960,700)
        self.setAcceptDrops(True)
        root=QWidget()
        self.setCentralWidget(root)
        outer=QVBoxLayout(root)
        outer.setContentsMargins(28,22,28,18)
        outer.setSpacing(18)
        header=QHBoxLayout()
        header.addWidget(label('EMBER / EXIF','brand'))
        header.addStretch()
        header.addWidget(label('LOCAL INSPECTION  /  NO UPLOADS','small'))
        outer.addLayout(header)
        toolbar=QHBoxLayout()
        toolbar.setSpacing(10)
        titles=QVBoxLayout()
        titles.setSpacing(5)
        titles.addWidget(label('Camera Inspector','hero'))
        titles.addWidget(label('One photo. All the details.','muted'))
        toolbar.addLayout(titles)
        toolbar.addStretch()
        self.clear_button=QPushButton('Clear photo')
        self.clear_button.clicked.connect(self.clear_photo)
        toolbar.addWidget(self.clear_button)
        self.verify_button=QPushButton('Verify report')
        self.verify_button.clicked.connect(self.verify)
        toolbar.addWidget(self.verify_button)
        self.pdf=QPushButton('PDF Certificate')
        self.pdf.setObjectName('primary')
        self.pdf.clicked.connect(self.save_pdf)
        toolbar.addWidget(self.pdf)
        outer.addLayout(toolbar)
        scroll=QScrollArea()
        scroll.setWidgetResizable(True)
        body=QWidget()
        body.setMinimumHeight(670)
        grid=QGridLayout(body)
        grid.setContentsMargins(0,0,0,0)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(20)
        grid.setColumnStretch(0,4)
        grid.setColumnStretch(1,6)
        scroll.setWidget(body)
        outer.addWidget(scroll,1)
        left=QWidget()
        ll=QVBoxLayout(left)
        ll.setContentsMargins(0,0,0,0)
        ll.setSpacing(20)
        photo,pl=card('01 / SOURCE PHOTO')
        self.photo_box=PhotoBox()
        self.photo_box.clicked.connect(self.choose)
        pl.addWidget(self.photo_box,1)
        self.filename=label('No photo selected','muted')
        self.filename.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        pl.addWidget(self.filename)
        ll.addWidget(photo,1)
        info,il=card('CAMERA IDENTITY')
        identity=QHBoxLayout()
        identity.setSpacing(18)
        self.brand_badge=BrandBadge()
        identity.addWidget(self.brand_badge)
        names=QVBoxLayout()
        names.setSpacing(5)
        self.manufacturer=label('MANUFACTURER','small')
        self.camera=label('Your camera','model')
        names.addWidget(self.manufacturer)
        names.addWidget(self.camera)
        identity.addLayout(names,1)
        il.addLayout(identity)
        self.detail_labels={}
        details=QGridLayout()
        details.setHorizontalSpacing(16)
        details.setVerticalSpacing(9)
        for row,key in enumerate(('Lens','Exposure','Captured','Serial')):
            details.addWidget(label(key,'small'),row,0)
            field=label('—','muted')
            field.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            details.addWidget(field,row,1)
            self.detail_labels[key]=field
        details.setColumnStretch(1,1)
        il.addLayout(details)
        ll.addWidget(info)
        grid.addWidget(left,0,0)
        right=QWidget()
        rl=QVBoxLayout(right)
        rl.setContentsMargins(0,0,0,0)
        rl.setSpacing(20)
        health,hl=card('02 / SHUTTER CONDITION')
        headline=QHBoxLayout()
        self.count=label('—','number')
        headline.addWidget(self.count)
        headline.addStretch()
        self.badge=label('UNKNOWN')
        headline.addWidget(self.badge)
        hl.addLayout(headline)
        self.source=label('Open a photo to inspect its recorded counter.','small')
        hl.addWidget(self.source)
        self.bar=QProgressBar()
        self.bar.setRange(0,1000)
        self.bar.setTextVisible(False)
        hl.addWidget(self.bar)
        refrow=QHBoxLayout()
        refrow.setSpacing(12)
        refrow.addWidget(label('Shutter life reference','muted'))
        refrow.addStretch()
        self.rating=QSpinBox()
        self.rating.setRange(0,10000000)
        self.rating.setSingleStep(50000)
        self.rating.setGroupSeparatorShown(True)
        self.rating.setSpecialValueText('Not available')
        self.rating.setMinimumWidth(150)
        self.rating.setReadOnly(True)
        self.rating.lineEdit().setStyleSheet('border:0;padding:0;background:transparent;')
        self.rating.valueChanged.connect(self.update_condition)
        refrow.addWidget(self.rating)
        hl.addLayout(refrow)
        refmeta=QHBoxLayout()
        self.reference_kind=label('Automatic model lookup','small')
        refmeta.addWidget(self.reference_kind,1)
        self.custom=QCheckBox('Custom reference')
        self.custom.toggled.connect(self.custom_reference)
        refmeta.addWidget(self.custom)
        hl.addLayout(refmeta)
        self.reference_source=QPushButton('View reference source')
        self.reference_source.setObjectName('link')
        self.reference_source.clicked.connect(self.open_reference)
        hl.addWidget(self.reference_source)
        self.healthnote=label('A recorded counter and a model reference are needed.','muted')
        hl.addWidget(self.healthnote)
        legend=QHBoxLayout()
        for text,color in [('GOOD <50%','#51d99a'),('MODERATE 50–<80%','#f5c85c'),('HIGH ≥80%','#ff6b75')]:
            item=label(text,'small')
            item.setStyleSheet('color:'+color)
            legend.addWidget(item)
        hl.addLayout(legend)
        hl.addWidget(label('Usage guide only. Shutter life is a test reference, not a failure date.','small'))
        rl.addWidget(health)
        meta,ml=card('03 / METADATA EXPLORER')
        searchrow=QHBoxLayout()
        searchrow.setSpacing(12)
        self.search=QLineEdit()
        self.search.setPlaceholderText('Search tags or values: ISO, Lens, GPS…')
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter)
        searchrow.addWidget(self.search,1)
        self.export=QPushButton('Export JSON')
        self.export.clicked.connect(self.save)
        searchrow.addWidget(self.export)
        ml.addLayout(searchrow)
        self.table=QTableWidget(0,2)
        self.table.setHorizontalHeaderLabels(['TAG','VALUE'])
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(165)
        ml.addWidget(self.table,1)
        self.tag_count=label('No metadata loaded','small')
        ml.addWidget(self.tag_count)
        rl.addWidget(meta,1)
        grid.addWidget(right,0,1)
        self.status=label('Ready / Choose a photo in the photo box.','small')
        outer.addWidget(self.status)
        self.clear_photo()

    def choose(self):
        path,_=QFileDialog.getOpenFileName(self,'Choose a photo','','Image files ('+' '.join('*'+x for x in sorted(SUPPORTED))+');;All files (*)')
        if path:self.load(path)

    def dragEnterEvent(self,event):
        urls=event.mimeData().urls()
        if len(urls)==1 and urls[0].isLocalFile() and Path(urls[0].toLocalFile()).is_file():event.acceptProposedAction()

    def dropEvent(self,event):
        urls=event.mimeData().urls()
        if len(urls)==1 and urls[0].isLocalFile():
            path=urls[0].toLocalFile()
            if Path(path).is_file():self.load(path);event.acceptProposedAction()

    def load(self,path):
        self.token+=1
        self.queued=(str(path),self.token)
        self.clear_display()
        self.filename.setText(Path(path).name)
        self.photo_box.image.setText('Reading photo…')
        self.photo_box.hint.setText('Click to choose a different photo')
        self.clear_button.setEnabled(True)
        self.status.setText('Reading metadata and embedded preview…')
        if not self.worker:self.start_reader()

    def start_reader(self):
        if not self.queued:return
        path,token=self.queued
        self.queued=None
        job=Reader(path,token,self)
        self.worker=job
        job.done.connect(self.reader_result)
        job.failed.connect(self.reader_error)
        job.finished.connect(self.reader_finished)
        job.start()

    @Slot(object,str,bytes)
    def reader_result(self,data,engine,preview):
        job=self.sender()
        self.loaded(job.path,job.token,data,engine,preview)

    @Slot(str)
    def reader_error(self,error):
        self.failed(self.sender().token,error)

    @Slot()
    def reader_finished(self):
        old=self.sender()
        old.wait()
        self.worker=None
        old.deleteLater()
        if self.queued:self.start_reader()
        else:self.sync_actions()

    def clear_display(self):
        self.data={}
        self.path=None
        self.engine=''
        self.reference=None
        self.photo_box.reset()
        self.filename.setText('No photo selected')
        self.brand_badge.set_brand('CAMERA')
        self.manufacturer.setText('MANUFACTURER')
        self.camera.setText('Your camera')
        for field in self.detail_labels.values():field.setText('—')
        self.custom.blockSignals(True)
        self.custom.setChecked(False)
        self.custom.blockSignals(False)
        self.custom.setEnabled(False)
        self.rating.blockSignals(True)
        self.rating.setValue(0)
        self.rating.setReadOnly(True)
        self.rating.blockSignals(False)
        self.search.clear()
        self.table.setRowCount(0)
        self.tag_count.setText('No metadata loaded')
        self.update_condition()
        self.sync_actions()

    def clear_photo(self):
        self.token+=1
        self.queued=None
        self.clear_display()
        self.clear_button.setEnabled(False)
        self.status.setText('Ready / Choose a photo in the photo box.')

    def sync_actions(self):
        ready=bool(self.data) and not self.worker and not self.queued
        self.export.setEnabled(ready)
        self.pdf.setEnabled(ready and not (self.report_job and self.report_job.isRunning()))
        self.clear_button.setEnabled(bool(self.data) or bool(self.queued) or bool(self.worker and self.worker.token==self.token))

    def failed(self,token,error):
        if token!=self.token:return
        self.clear_display()
        self.status.setText('Unable to read photo: '+error)

    def loaded(self,path,token,data,engine,preview=b''):
        if token!=self.token:return
        self.data=data
        self.path=path
        self.engine=engine
        self.filename.setText(Path(path).name)
        brand=camera_brand(value(data,'Make',default=''))
        model=value(data,'Model',default='Unknown model')
        if model.upper().startswith('PENTAX '):brand='Pentax'
        self.brand_badge.set_brand(brand)
        self.manufacturer.setText(brand.upper())
        self.camera.setText(model)
        fields={
            'Lens':value(data,'LensModel','LensID','LensType'),
            'Exposure':f"ISO {value(data,'ISO','ISOSpeedRatings')} / f{value(data,'FNumber')} / {value(data,'ExposureTime')} s",
            'Captured':value(data,'DateTimeOriginal','CreateDate','DateTime'),
            'Serial':value(data,'SerialNumber','BodySerialNumber','InternalSerialNumber'),
        }
        for key,text in fields.items():self.detail_labels[key].setText(text)
        self.reference=lookup_rating(data)
        self.custom.setEnabled(not(self.reference and self.reference['kind']=='Electronic shutter only'))
        self.rating.blockSignals(True)
        self.rating.setValue((self.reference or {}).get('cycles') or 0)
        self.rating.blockSignals(False)
        reader=QImageReader(path)
        reader.setAutoTransform(True)
        size=reader.size()
        if size.isValid():reader.setScaledSize(size.scaled(QSize(1200,900),Qt.AspectRatioMode.KeepAspectRatio))
        image=reader.read()
        if image.isNull() and preview:
            image=QImage.fromData(preview)
            orientation=value(data,'Orientation',default='')
            if not image.isNull() and orientation in ('Rotate 90 CW','Rotate 270 CW','Rotate 180'):
                image=image.transformed(QTransform().rotate({'Rotate 90 CW':90,'Rotate 270 CW':270,'Rotate 180':180}[orientation]))
        self.photo_box.set_image(image)
        self.table.setRowCount(len(data))
        for row,(key,val) in enumerate(sorted(data.items())):
            self.table.setItem(row,0,QTableWidgetItem(key))
            self.table.setItem(row,1,QTableWidgetItem(str(val)))
        self.filter()
        self.update_condition()
        self.status.setText(f'{len(data):,} tags / {engine} / Processed locally')
        self.sync_actions()

    def current_reference(self):
        if self.custom.isChecked():
            return dict(cycles=self.rating.value() or None,kind='Manual reference',publisher='User supplied',url='',checked='',note='Custom reference entered by the operator.')
        return reference_for(self.data,self.rating.value())

    def custom_reference(self,checked):
        self.rating.setReadOnly(not checked)
        if not checked:self.rating.setValue((self.reference or {}).get('cycles') or 0)
        self.update_condition()

    def update_condition(self):
        ref=self.current_reference()
        count,tag=shutter_count(self.data)
        rating=0 if ref['kind']=='Electronic shutter only' else self.rating.value()
        text,color,pct=condition(count,rating)
        if ref['kind']=='Electronic shutter only':text='NOT APPLICABLE'
        self.count.setText(f'{count:,}' if count is not None else '—')
        self.badge.setText(text)
        self.badge.setStyleSheet(f'color:{color};font-size:12px;font-weight:700;')
        self.bar.setStyleSheet(f'QProgressBar::chunk {{background:{color};border-radius:4px;}}')
        self.bar.setValue(min(1000,int(pct*10)) if pct is not None else 0)
        self.source.setText('Recorded counter / '+tag if tag else 'No supported shutter counter found in this file.')
        if not self.data:self.source.setText('Open a photo to inspect its recorded counter.')
        self.reference_kind.setText(ref['kind']+(' / '+ref['publisher'] if ref['publisher'] else ''))
        self.reference_source.setEnabled(bool(ref.get('url')))
        self.reference_source.setText('View source / reviewed '+ref['checked'] if ref.get('url') else 'No reviewed web reference for this model')
        self.reference_source.setToolTip(ref.get('url',''))
        self.rating.setToolTip(ref.get('note','') or 'Reference cycles, not a guarantee of remaining life.')
        if ref['kind']=='Electronic shutter only':note='This model has no mechanical shutter-life comparison.'
        elif pct is not None:note=f'{pct:.1f}% of the reference cycle count used.'+(' Based on a third-party estimate.' if ref['kind']=='Third-party estimate' else '')
        elif count is None and self.data:note='The image does not contain a supported shutter counter.'
        elif self.data:note='No reviewed rating found. You may enter a custom reference.'
        else:note='A recorded counter and a model reference are needed.'
        self.healthnote.setText(note)

    def open_reference(self):
        url=self.current_reference().get('url')
        if url:QDesktopServices.openUrl(QUrl(url))

    def filter(self):
        query=self.search.text().casefold()
        visible=0
        for row in range(self.table.rowCount()):
            matches=any(query in self.table.item(row,col).text().casefold() for col in (0,1))
            self.table.setRowHidden(row,not matches)
            visible+=matches
        total=self.table.rowCount()
        self.tag_count.setText(f'{visible:,} of {total:,} tags' if total else 'No metadata loaded')

    def save(self):
        if not self.path:return
        path,_=QFileDialog.getSaveFileName(self,'Export metadata',str(Path.home()/'Documents'/(Path(self.path).stem+'.exif.json')),'JSON (*.json)')
        if path:
            try:
                Path(path).write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf-8')
                self.status.setText('Metadata saved / '+path)
            except OSError as error:self.status.setText('Export failed / '+str(error))

    def save_pdf(self):
        if not self.path or not self.data:return
        if self.report_job and self.report_job.isRunning():return
        dest,_=QFileDialog.getSaveFileName(self,'Save PDF Certificate',str(Path.home()/'Documents'/(Path(self.path).stem+'-certificate.pdf')),'PDF (*.pdf)')
        if not dest:return
        if not dest.lower().endswith('.pdf'):dest+='.pdf'
        job=ReportWriter(self.path,self.data,self.engine,self.rating.value(),dest,self.current_reference(),self)
        self.report_job=job
        self.pdf.setEnabled(False)
        self.status.setText('Creating PDF report and source checksum…')
        job.done.connect(self.report_done)
        job.failed.connect(self.report_failed)
        job.finished.connect(self.report_finished)
        job.start()

    @Slot(str)
    def report_done(self,report_id):
        self.status.setText('PDF + certificate JSON saved / Report '+report_id[:8])

    @Slot(str)
    def report_failed(self,error):
        self.status.setText('Report failed / '+error)

    @Slot()
    def report_finished(self):
        job=self.sender()
        job.wait()
        self.report_job=None
        job.deleteLater()
        self.sync_actions()

    def verify(self):
        manifest,_=QFileDialog.getOpenFileName(self,'Choose certificate JSON','','Certificate (*.certificate.json)')
        if not manifest:return
        source,_=QFileDialog.getOpenFileName(self,'Choose the original photo')
        if not source:return
        pdf,_=QFileDialog.getOpenFileName(self,'Choose the PDF report','','PDF (*.pdf)')
        if not pdf:return
        try:
            results=verify_report(manifest,source,pdf)
            message='\n'.join(k.replace('_',' ').title()+': '+('MATCH' if v else 'MISMATCH') for k,v in results.items())
            QMessageBox.information(self,'Local checksum verification',message+'\n\nChecksums are not digital signatures or manufacturer certification.')
        except Exception as error:QMessageBox.warning(self,'Verification failed',str(error))

    def closeEvent(self,event):
        if any(job and job.isRunning() for job in (self.worker,self.report_job)):
            self.status.setText('Processing is still running. Please wait before closing.')
            event.ignore()
        else:event.accept()

if __name__=='__main__':
    app=QApplication(sys.argv)
    for font in ('segoeui.ttf','segoeuib.ttf','georgia.ttf'):
        path=Path('C:/Windows/Fonts')/font
        if path.exists():QFontDatabase.addApplicationFont(str(path))
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    window=Window()
    window.show()
    sys.exit(app.exec())
