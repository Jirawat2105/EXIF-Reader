"""Download original camera-brand SVGs and record their Wikimedia provenance."""
import hashlib,json,re,urllib.parse,urllib.request
from pathlib import Path
from datetime import date
ROOT=Path(__file__).resolve().parents[1]
FILES={
'Sony':('sony.svg','Sony logo.svg'), 'Nikon':('nikon.svg','Nikon Logo.svg'),
'Canon':('canon.svg','Canon logo.svg'), 'Fujifilm':('fujifilm.svg','Fujifilm logo.svg'),
'Pentax':('pentax.svg','Pentax Logo.svg'), 'Panasonic':('panasonic.svg','Panasonic logo (Blue).svg'),
'Ricoh':('ricoh.svg','Ricoh logo.svg'), 'Leica':('leica.svg','Leica Camera logo.svg'),
'Hasselblad':('hasselblad.svg','Hasselblad logo.svg'), 'OM SYSTEM':('om-system.svg','OM-System-Logo.svg'),
'Olympus':('olympus.svg','Olympus Corporation logo.svg'), 'Sigma':('sigma.svg','Sigma Logo.svg'),
'Samsung':('samsung.svg','Samsung wordmark.svg'), 'Phase One':('phase-one.svg','Phase One logo.svg'),
}
HEADERS={'User-Agent':'EXIFReader/1.0 (https://github.com/Jirawat2105/EXIF-Reader)'}
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=45) as response:return response.read()
def clean(text):return re.sub('<[^>]+>','',text)
def main():
    query=urllib.parse.urlencode(dict(action='query',format='json',prop='imageinfo',iiprop='url|extmetadata',titles='|'.join('File:'+x[1] for x in FILES.values())))
    pages=json.loads(fetch('https://commons.wikimedia.org/w/api.php?'+query))['query']['pages'].values()
    info={p['title']:p['imageinfo'][0] for p in pages if 'imageinfo' in p}
    target=ROOT/'assets'/'logos';target.mkdir(parents=True,exist_ok=True)
    manifest={}
    for brand,(filename,title) in FILES.items():
        entry=info.get('File:'+title)
        if not entry:raise RuntimeError('Missing Commons logo: '+title)
        url=entry['url'].split('?')[0]
        payload=fetch(url)
        if b'<svg' not in payload or len(payload)>1000000:raise ValueError('Unexpected SVG data for '+brand)
        (target/filename).write_bytes(payload)
        meta=entry.get('extmetadata',{})
        get=lambda key:clean(meta.get(key,{}).get('value',''))
        manifest[brand]=dict(file=filename,url=url,source_page=entry['descriptionurl'],downloaded=date.today().isoformat(),sha256=hashlib.sha256(payload).hexdigest(),license=get('LicenseShortName'),license_url=get('LicenseUrl'),artist=get('Artist'),credit=get('Credit'),restrictions=get('Restrictions'))
        print(brand,filename,len(payload),get('LicenseShortName'))
    (target/'SOURCES.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
