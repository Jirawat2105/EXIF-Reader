from __future__ import annotations
import json, shutil, subprocess
from pathlib import Path
from PIL import Image, ExifTags

COUNTERS = ('MechanicalShutterCount', 'ShutterCount', 'ShutterCount2')

def exiftool_path():
    base = Path(__file__).parent
    return next((str(p) for p in [base/'tools'/'exiftool.exe', *sorted((base/'tools').glob('*/exiftool.exe')), base/'exiftool.exe'] if p.is_file()), None) or shutil.which('exiftool')

def preview_bytes(filename):
    exe = exiftool_path()
    if not exe: return b''
    for tag in ('PreviewImage', 'JpgFromRaw', 'ThumbnailImage'):
        r = subprocess.run([exe, '-b', '-'+tag, str(Path(filename).resolve())], capture_output=True, timeout=60, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if r.returncode == 0 and r.stdout: return r.stdout
    return b''

def condition(count, rating):
    if count is None or rating <= 0: return ('UNKNOWN', '#8d95a5', None)
    ratio = count / rating * 100
    if ratio < 50: return ('GOOD', '#51d99a', ratio)
    if ratio < 80: return ('MODERATE', '#f5c85c', ratio)
    return ('HIGH USAGE', '#ff6b75', ratio)

def read_metadata(filename):
    path = Path(filename).resolve()
    if not path.is_file(): raise ValueError('The selected file does not exist.')
    initial_stat = path.stat()
    exe = exiftool_path()
    if exe:
        result = subprocess.run([exe, '-j', '-G1', '-s', '-api', 'LargeFileSupport=1', str(path)], capture_output=True, encoding='utf-8', errors='replace', timeout=90, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode: raise ValueError(result.stderr.strip() or 'Unable to read this file.')
        data = json.loads(result.stdout)[0]
        if 'ExifTool:Error' in data: raise ValueError(data['ExifTool:Error'])
        engine = 'ExifTool · Full metadata'
    else:
        if path.suffix.lower() in {'.arw','.nef','.nrw','.cr2','.cr3','.raf','.rw2','.orf','.pef','.dng','.srw','.3fr','.fff','.iiq','.rwl','.x3f','.raw'}:
            raise ValueError('ExifTool is missing. Restore the bundled tools folder to read RAW files.')
        with Image.open(path) as im:
            exif = im.getexif()
            data = {ExifTags.TAGS.get(k, str(k)): str(v) for k,v in exif.items() if k != 37500}
            for ifd in (34665, 34853):
                try:
                    data.update({ExifTags.TAGS.get(k, str(k)): str(v) for k,v in exif.get_ifd(ifd).items() if k != 37500})
                except (KeyError, TypeError, ValueError): pass
            data.update({'ImageWidth': im.width, 'ImageHeight': im.height, 'Format': im.format})
        engine = 'Pillow / Standard EXIF only'
    final_stat = path.stat()
    if (initial_stat.st_size, initial_stat.st_mtime_ns) != (final_stat.st_size, final_stat.st_mtime_ns):
        raise ValueError('The source changed while reading. Please open it again.')
    data['Ember:SourceMTimeNS'] = str(final_stat.st_mtime_ns)
    data['File:FileName'] = path.name
    data['File:FileSizeBytes'] = path.stat().st_size
    return data, engine

def value(data, *names, default='—'):
    for name in names:
        for key, val in data.items():
            if key.split(':')[-1] == name and val is not None and str(val).strip(): return str(val)
    return default

def shutter_count(data):
    for name in COUNTERS:
        raw = value(data, name, default='')
        try:
            n = int(raw)
            if n >= 0: return n, name
        except (ValueError, TypeError): pass
    return None, None
