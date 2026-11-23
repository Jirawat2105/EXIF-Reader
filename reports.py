"""Local certificate reports. No remote upload or claim of third-party authentication."""
import hashlib,json,uuid,os,tempfile
from datetime import datetime,timezone,timedelta
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.colors import HexColor,white
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from metadata import value,shutter_count,condition
from ratings import reference_for

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def canonical(data):return json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')

def create_report(source,data,engine,rating,destination,reference=None):
    source=Path(source);dest=Path(destination)
    if dest.resolve()==source.resolve():raise ValueError('Report must not overwrite the source image')
    stat=source.stat()
    if 'Ember:SourceMTimeNS' in data and (str(stat.st_mtime_ns)!=data['Ember:SourceMTimeNS'] or stat.st_size!=data['File:FileSizeBytes']):
        raise ValueError('Source changed since inspection. Reopen the image before issuing a report.')
    reference=dict(reference or reference_for(data,rating))
    if reference['kind']=='Electronic shutter only':rating=0
    count,tag=shutter_count(data);grade,color,pct=condition(count,rating)
    if reference['kind']=='Electronic shutter only':grade='NOT APPLICABLE'
    record={'schema':'ember-certificate-v2','report_id':str(uuid.uuid4()),'issued_at':datetime.now(timezone(timedelta(hours=7))).isoformat(timespec='seconds'),'source_name':source.name,'source_sha256':sha256(source),'source_size':source.stat().st_size,'engine':engine,'reference_rating':rating,'reference':reference,'counter_tag':tag,'counter_value':count,'usage_percent':pct,'metadata':data}
    if (source.stat().st_size,source.stat().st_mtime_ns)!=(stat.st_size,stat.st_mtime_ns):raise ValueError('Source changed while hashing')
    record_hash=hashlib.sha256(canonical(record)).hexdigest()
    font=Path('C:/Windows/Fonts/segoeui.ttf')
    if font.exists() and 'Ember' not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont('Ember',str(font)))
    face='Ember' if font.exists() else 'Helvetica'
    styles=getSampleStyleSheet()
    for name in ('Normal','BodyText','Title','Heading1','Heading2'):styles[name].fontName=face
    styles.add(ParagraphStyle(name='SmallEmber',fontName=face,fontSize=8,leading=12,textColor=HexColor('#596170'),wordWrap='CJK'))
    styles.add(ParagraphStyle(name='BigEmber',fontName=face,fontSize=42,leading=52,textColor=HexColor(color)))
    styles['BodyText'].fontSize=10;styles['BodyText'].leading=16
    def p(t,style='BodyText'):return Paragraph(escape(str(t)),styles[style])
    story=[p('EMBER / EXIF','Heading1'),p('CAMERA METADATA CERTIFICATE','Title'),p('Local file inspection report - no image upload'),Spacer(1,12),p(value(data,'Make')+'  /  '+value(data,'Model'),'Heading1'),p(f'{count:,}' if count is not None else 'UNAVAILABLE','BigEmber'),p('Recorded counter: '+(tag or 'No supported counter found')),
           p('Usage grade: '+grade.split(' · ')[0]),p(f'Usage: {pct:.2f}% of reference ({rating:,} cycles)' if pct is not None else ('No mechanical shutter-life comparison applies.' if grade=='NOT APPLICABLE' else 'Usage grade unavailable: counter and reference rating are both required.')),p(reference['kind']+' / '+reference['publisher']+' / Reviewed '+(reference.get('checked') or 'operator supplied'),'SmallEmber'),p(reference.get('url') or 'No reviewed web source; reference is unavailable or entered manually.','SmallEmber'),Spacer(1,12)]
    rows=[('Report ID',record['report_id']),('Issued (UTC+07:00)',record['issued_at']),('Source file',source.name),('Camera serial',value(data,'SerialNumber','BodySerialNumber','InternalSerialNumber')),('Lens',value(data,'LensModel','LensID','LensType')),('Capture time',value(data,'DateTimeOriginal','CreateDate')),('Exposure',f"ISO {value(data,'ISO')} / f{value(data,'FNumber')} / {value(data,'ExposureTime')} s"),('Reader',engine)]
    table=Table([[p(a,'SmallEmber'),p(b)] for a,b in rows],colWidths=[125,382]);table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,-1),HexColor('#f1f3f6')),('BOTTOMPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6)]));story.extend([table,Spacer(1,16),p('SOURCE SHA-256','Heading2'),p(record['source_sha256'],'SmallEmber'),p('RECORD SHA-256','Heading2'),p(record_hash,'SmallEmber'),Spacer(1,12),p('Scope & interpretation','Heading2'),p('This report records metadata present in the selected file. Metadata can be edited. Counter meaning varies by camera and shutter mode. This is not a physical inspection, manufacturer certification, digital signature or public verification service.','SmallEmber'),p('App thresholds: GOOD <50%; MODERATE 50% to <80%; HIGH USAGE >=80%. Reference provenance is listed above. Third-party and custom references are not manufacturer specifications. A rating does not predict remaining shutter life.','SmallEmber'),PageBreak(),p('METADATA APPENDIX','Title'),p('Report ID: '+record['report_id'],'SmallEmber'),Spacer(1,14)])
    entries=[[p('TAG','SmallEmber'),p('VALUE','SmallEmber')]]
    for k,v in sorted(data.items()):
        # Bound each cell so huge maker-note text cannot exceed a page.
        text=str(v)
        for offset in range(0,max(1,len(text)),900):entries.append([p(k if offset==0 else k+' (continued)','SmallEmber'),p(text[offset:offset+900],'SmallEmber')])
    table=Table(entries,colWidths=[190,317],repeatRows=1);table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,HexColor('#f2f4f7')]),('BACKGROUND',(0,0),(-1,0),HexColor('#ffe4d2')),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.append(table)
    def footer(c,doc):
        c.setFillColor(HexColor('#ef843e'));c.rect(0,825,595,17,fill=1,stroke=0);c.setFillColor(HexColor('#687080'));c.setFont(face,8);c.drawString(44,24,'EMBER EXIF / '+record['report_id'][:8]);c.drawRightString(551,24,f'Page {doc.page}')
    # Build before replacing any existing destination.
    handle,tmp=tempfile.mkstemp(suffix='.pdf',dir=dest.parent);os.close(handle)
    try:
        SimpleDocTemplate(tmp,pagesize=(595.28,841.89),rightMargin=44,leftMargin=44,topMargin=42,bottomMargin=44,title='EMBER Camera Metadata Certificate',author='EMBER EXIF').build(story,onFirstPage=footer,onLaterPages=footer)
        pdf_hash=sha256(tmp);os.replace(tmp,dest)
    finally:
        if Path(tmp).exists():Path(tmp).unlink()
    manifest={'record':record,'record_sha256':record_hash,'pdf_sha256':pdf_hash,'verification_note':'Checksums are not a digital signature or proof of original camera data.'}
    dest.with_suffix('.certificate.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return record['report_id']

def verify_report(manifest_path,source_path,pdf_path):
    m=json.loads(Path(manifest_path).read_text(encoding='utf-8'));r=m['record']
    return {'record_matches':hashlib.sha256(canonical(r)).hexdigest()==m['record_sha256'],'source_matches':sha256(source_path)==r['source_sha256'],'pdf_matches':sha256(pdf_path)==m['pdf_sha256']}
