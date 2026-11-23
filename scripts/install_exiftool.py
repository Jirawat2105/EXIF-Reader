"""Install the unmodified Windows ExifTool distribution after SHA-256 verification."""
from __future__ import annotations
import hashlib
import io
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

VERSION = '13.59'
PACKAGE = f'exiftool-{VERSION}_64'
SHA256 = '44b512b25af500724ba579d0a53c8fc5851628b692dd5e5d94ae4a15c2cba9ec'
URLS = (
    f'https://netix.dl.sourceforge.net/project/exiftool/{PACKAGE}.zip',
    f'https://downloads.sourceforge.net/project/exiftool/{PACKAGE}.zip',
)
ROOT = Path(__file__).resolve().parents[1]


def verified_archive(payload: bytes) -> zipfile.ZipFile:
    if hashlib.sha256(payload).hexdigest() != SHA256:
        raise ValueError('ExifTool download checksum mismatch. Nothing was installed.')
    archive = zipfile.ZipFile(io.BytesIO(payload))
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != PACKAGE or '\\' in info.filename:
            archive.close()
            raise ValueError('Unexpected path in ExifTool package.')
    return archive


def install() -> Path:
    if sys.platform != 'win32':
        raise RuntimeError('This setup installs Windows x64 ExifTool only.')
    tools = ROOT / 'tools'
    destination = tools / PACKAGE
    exe = destination / 'exiftool.exe'
    if exe.is_file():
        result = subprocess.run([str(exe), '-ver'], capture_output=True, text=True,
                                timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode == 0 and result.stdout.strip() == VERSION:
            print(f'ExifTool {VERSION} is ready.')
            return exe
    if destination.exists():
        raise RuntimeError(f'Incomplete ExifTool installation: {destination}. Move that folder aside, then run setup again.')
    errors = []
    for url in URLS:
        try:
            print(f'Downloading ExifTool {VERSION} for Windows x64…')
            with urllib.request.urlopen(url, timeout=45) as response:
                payload = response.read(32 * 1024 * 1024 + 1)
            with verified_archive(payload) as archive:
                tools.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(prefix='.exiftool-setup-', dir=tools) as stage:
                    archive.extractall(stage)
                    package = Path(stage) / PACKAGE
                    (package / 'exiftool(-k).exe').rename(package / 'exiftool.exe')
                    # Retain the entire upstream package, including all license notices.
                    (package / 'exiftool.exe').resolve(strict=True)
                    package.rename(destination)
            print(f'Installed ExifTool {VERSION}; upstream license files were retained.')
            return exe
        except Exception as error:
            errors.append(str(error))
    raise RuntimeError('ExifTool setup failed: ' + '; '.join(errors))


if __name__ == '__main__':
    try:
        install()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
