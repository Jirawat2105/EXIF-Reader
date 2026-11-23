"""Reviewed web references; exact model matching prevents cross-model guesses."""
import re
from metadata import value
CHECKED='2026-10-23'
ENTRIES=[]
def add(brand,models,cycles,url,publisher,kind='Manufacturer tested',note=''):
    for model in models:
        ENTRIES.append(dict(brand=brand,model=model,cycles=cycles,url=url,publisher=publisher,kind=kind,checked=CHECKED,note=note))
nikon='https://www.nikonimgsupport.com/eu/BV_article?articleNo=000044853&configured=1&lang=en_GB&setRedirect=true'
add('Nikon',['D850','D810A','D810','D800E','D800','D500'],200000,nikon,'Nikon Support')
add('Nikon',['D7500','D7200','D7100','D7000','D780','D750','D700','D610','D600','D300S','D300'],150000,nikon,'Nikon Support')
add('Nikon',['Z7II','Z7','Z6III','Z6II','Z6','Z5II','Z5','Zf'],200000,nikon,'Nikon Support')
add('Nikon',['D3S','D3X','D3'],300000,nikon,'Nikon Support')
add('Nikon',['D4'],400000,'https://assets.contentstack.io/v3/assets/blt0e5ec1de4817c440/bltbb338288b1a83bf8/65ba6e5fa0f40983cc700323/D4_Brochure2.pdf','Nikon brochure')
add('Nikon',['Z8'],None,'https://www.nikon.com/company/news/2023/0510_mirrorless_01/','Nikon','Electronic shutter only','No mechanical shutter-life comparison applies.')
add('Sony',['ILCE-6400'],200000,'https://www.sony.co.uk/store/product/ilce6400amb.cec/6400-E-mount-camera-with-APS-C-Sensor','Sony UK')
add('Sony',['ILCE-7RM5'],500000,'https://www.sony.co.uk/interchangeable-lens-cameras/products/ilce-7rm5/ILCE_7RM5_Introducing_Alpha_7R','Sony UK',note='Tested in excess of 500,000 cycles.')
add('Sony',['ILCE-7M4'],200000,'https://beta.shuttercount.net/camera/sony/a7iv','ShutterCount.net','Third-party estimate','Approximate web reference; not a verified Sony durability specification.')
add('Canon',['EOS R6'],300000,'https://www.canon.ca/en/product?category=&name=EOS_R6','Canon Canada')
add('Canon',['EOS R5'],500000,'https://downloads.canon.com/nw/camera/products/eos/product-1/pdfs/EOS-R5-improvements-part-1.pdf','Canon')
add('Fujifilm',['X-T4'],300000,'https://www.fujifilm-x.com/en-ca/wp-content/uploads/sites/12/2020/05/X-T4-Cheat-Sheet-Final.pdf','Fujifilm')
add('Fujifilm',['X-H2'],500000,'https://www.fujifilm-x.com/global/products/cameras/x-h2/','Fujifilm')
add('Pentax',['K-1 Mark II'],300000,'https://www.ricoh-imaging.co.jp/english/products/k-1-2/feature/03.html','Ricoh Imaging')
add('Pentax',['K-3 Mark III'],300000,'https://www.ricoh-imaging.co.jp/english/products/k-3-3/special/interview/reliability.html','Ricoh Imaging')
add('OM SYSTEM',['OM-1'],400000,'https://learnandsupport.getolympus.com/sites/default/files/media/files/2022/02/OM_SYSTEM_OM-1_Press_Release_US.pdf','OM SYSTEM')
add('OM SYSTEM',['OM-1MarkII'],400000,'https://my.omsystem.com/consumer/product_specs/SPECIFICATIONS_om-1-mark-ii_EN.pdf','OM SYSTEM')
add('Panasonic',['DC-GH5'],200000,'https://www.panasonic.com/content/dam/Panasonic/th/th/support/pdf/Catalog_Lumix_GH5_GH5S.pdf','Panasonic')

def camera_brand(make):
    upper=make.upper()
    for needles,brand in [(['NIKON'],'Nikon'),(['SONY'],'Sony'),(['CANON'],'Canon'),(['FUJI'],'Fujifilm'),(['PENTAX'],'Pentax'),(['OM DIGITAL','OLYMPUS','OM SYSTEM'],'OM SYSTEM'),(['PANASONIC','LUMIX'],'Panasonic'),(['RICOH'],'Ricoh'),(['LEICA'],'Leica'),(['HASSELBLAD'],'Hasselblad'),(['SIGMA'],'Sigma'),(['SAMSUNG'],'Samsung'),(['LEAF','PHASE ONE'],'Phase One')]:
        if any(n in upper for n in needles):return brand
    return make.strip() or 'CAMERA'

def normalize(model):
    s=model.upper().strip()
    s=re.sub(r'^(NIKON|SONY|CANON|FUJIFILM|PENTAX|OLYMPUS|OM SYSTEM|PANASONIC)\s+','',s)
    aliases={'Z 6_2':'Z6II','Z 7_2':'Z7II','Z 6_3':'Z6III','Z 5_2':'Z5II'}
    s=aliases.get(s,s)
    return re.sub(r'[^A-Z0-9]','',s)

def lookup_rating(data):
    brand=camera_brand(value(data,'Make',default=''))
    # Ricoh manufactures Pentax bodies, so use explicit model prefix where present.
    model=value(data,'Model',default='')
    if model.upper().startswith('PENTAX '):brand='Pentax'
    return next((dict(e) for e in ENTRIES if e['brand']==brand and normalize(e['model'])==normalize(model)),None)

def reference_for(data,rating):
    match=lookup_rating(data)
    if match and match['cycles']==rating:return match
    if match and match['cycles'] is None:return match
    return dict(cycles=rating or None,kind='Manual reference' if rating else 'Not available',publisher='User supplied' if rating else 'No reviewed reference',url='',checked=CHECKED,note='')
