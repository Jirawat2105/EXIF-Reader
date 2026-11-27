"""Original downloaded brand artwork; resources work from source and frozen builds."""
import json
from pathlib import Path
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QPixmap,QPainter,QColor
from PySide6.QtSvg import QSvgRenderer

RESOURCE_ROOT=Path(__file__).resolve().parent
LOGOS=RESOURCE_ROOT/'assets'/'logos'
SOURCES=json.loads((LOGOS/'SOURCES.json').read_text(encoding='utf-8'))

def logo_pixmap(brand,width=104,height=58):
    entry=SOURCES.get(brand)
    if not entry:return QPixmap()
    renderer=QSvgRenderer(str(LOGOS/entry['file']))
    if not renderer.isValid():return QPixmap()
    size=renderer.defaultSize().scaled(width,height,Qt.AspectRatioMode.KeepAspectRatio)
    pixmap=QPixmap(width*2,height*2)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(QColor('white'))
    painter=QPainter(pixmap)
    renderer.render(painter,QRectF((width-size.width())/2,(height-size.height())/2,size.width(),size.height()))
    painter.end()
    return pixmap
