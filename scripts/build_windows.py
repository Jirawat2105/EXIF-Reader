"""Build a standalone Windows EXE and verify it outside the source checkout."""
import hashlib,os,shutil,subprocess,sys,zipfile,urllib.request
from pathlib import Path
from importlib.metadata import distribution
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from version import __version__

def main():
    if sys.platform!='win32':raise RuntimeError('Build the Windows executable on Windows.')
    subprocess.run([sys.executable,str(ROOT/'scripts/install_exiftool.py')],check=True)
    work=ROOT/'build'/'windows';work.mkdir(parents=True,exist_ok=True)
    licenses=work/'third-party-licenses';licenses.mkdir(exist_ok=True)
    for name in ('PySide6-Essentials','shiboken6','Pillow','reportlab','charset-normalizer'):
        d=distribution(name)
        for f in d.files or []:
            if 'license' in str(f).lower() and d.locate_file(f).is_file():
                dest=licenses/name/str(f);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(d.locate_file(f),dest)
    # Some Qt wheels list the open-source terms in metadata but omit their text.
    # Include the complete unmodified upstream LGPL and GPL texts with the bundle.
    for filename,url in [('LGPL-3.0.txt','https://raw.githubusercontent.com/spdx/license-list-data/main/text/LGPL-3.0-only.txt'),('GPL-3.0.txt','https://raw.githubusercontent.com/spdx/license-list-data/main/text/GPL-3.0-only.txt'),('GPL-2.0.txt','https://raw.githubusercontent.com/spdx/license-list-data/main/text/GPL-2.0-only.txt')]:
        dest=licenses/'Qt'/filename;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():dest.write_bytes(urllib.request.urlopen(url,timeout=45).read())
    shutil.copy2(Path(sys.base_prefix)/'LICENSE.txt',licenses/'Python-LICENSE.txt')
    from PIL import Image,ImageDraw
    icon=Image.new('RGBA',(256,256),(0,0,0,0));draw=ImageDraw.Draw(icon)
    draw.rounded_rectangle((4,4,252,252),radius=54,fill='#171d26')
    draw.rounded_rectangle((40,72,216,190),radius=22,outline='#ff934e',width=15)
    draw.rounded_rectangle((70,50,133,83),radius=8,fill='#ff934e')
    draw.ellipse((91,100,165,174),outline='#ff934e',width=13)
    iconpath=work/'EXIFReader.ico';icon.save(iconpath,sizes=[(s,s) for s in (16,24,32,48,64,128,256)])
    env=os.environ.copy();windows=Path(env.get('WINDIR','C:/Windows'))
    env['PATH']=os.pathsep.join(map(str,[Path(sys.executable).parent,Path(sys.base_prefix),Path(sys.base_prefix)/'DLLs',windows/'System32',windows]))
    env.pop('PYTHONPATH',None)
    args=[sys.executable,'-m','PyInstaller','--clean','--noconfirm','--onefile','--windowed','--name','EXIFReader','--icon',str(iconpath),'--hidden-import','PySide6.QtSvg','--collect-data','reportlab']
    for source,dest in [(ROOT/'assets','assets'),(ROOT/'tools','tools'),(licenses,'third-party-licenses'),(ROOT/'LICENSE','.'),(ROOT/'README.md','.'),(ROOT/'THIRD_PARTY_NOTICES.md','.')]:
        args+=['--add-data',str(source)+os.pathsep+dest]
    args+=[str(ROOT/'main.py')]
    subprocess.run(args,cwd=ROOT,env=env,check=True)
    exe=ROOT/'dist'/'EXIFReader.exe'
    # Native Windows backend; dependencies and logos must resolve without the checkout.
    smoke_env=env.copy();smoke_env.pop('QT_QPA_PLATFORM',None)
    report=work/'packaged-self-test.json'
    subprocess.run([str(exe),'--self-test',str(report)],cwd=env.get('TEMP',str(work)),env=smoke_env,check=True,timeout=120)
    import json
    result=json.loads(report.read_text(encoding='utf-8'))
    assert result['status']=='passed' and result['frozen'],result
    release=exe.with_name(f'EXIFReader-{__version__}-Windows-x64.exe');shutil.copy2(exe,release)
    notices=ROOT/'dist'/f'EXIFReader-{__version__}-ThirdPartyNotices.zip'
    with zipfile.ZipFile(notices,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in licenses.rglob('*'):
            if path.is_file():archive.write(path,'third-party-licenses/'+path.relative_to(licenses).as_posix())
        for path in (ROOT/'tools').rglob('*'):
            if path.is_file() and ('license' in path.name.lower() or path.name in ('README.txt','readme_windows.txt')):archive.write(path,path.relative_to(ROOT).as_posix())
        for path in (ROOT/'LICENSE',ROOT/'THIRD_PARTY_NOTICES.md',ROOT/'assets/logos/SOURCES.json'):archive.write(path,path.relative_to(ROOT).as_posix())
    (ROOT/'dist'/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name+'\n' for path in (release,notices)),encoding='utf-8')
    print('Packaged app passed its native self-test:',release)
    print(json.dumps(result))
if __name__=='__main__':main()
