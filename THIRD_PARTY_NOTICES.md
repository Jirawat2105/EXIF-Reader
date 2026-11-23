# Third-party notices

The MIT License in `LICENSE` covers EXIF Reader's original project code and documentation. It does not relicense third-party software, manufacturer names or trademarks.

The following projects are installed separately:

| Dependency | Role | Upstream license / notices |
| --- | --- | --- |
| [Python](https://www.python.org/) | Runtime | [Python license](https://docs.python.org/3/license.html) |
| [PySide6 Essentials / Qt for Python](https://doc.qt.io/qtforpython-6/) | Desktop interface | [Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html); available under LGPLv3/GPLv3 or commercial terms, depending on components and use |
| [Pillow](https://python-pillow.github.io/) | Standard image metadata | [HPND-style license](https://github.com/python-pillow/Pillow/blob/main/LICENSE) |
| [ReportLab](https://www.reportlab.com/) | PDF generation | [BSD-style license](https://hg.reportlab.com/hg-public/reportlab/file/tip/LICENSE) |
| [ExifTool](https://exiftool.org/) | RAW metadata and embedded previews | [Same terms as Perl (Artistic License / GPL)](https://exiftool.org/#license) |
| [ExifTool Windows distribution](https://oliverbetz.de/pages/Artikel/ExifTool-for-Windows) | Windows launcher and Perl runtime | Launcher: CC0. Perl and included libraries retain their individual upstream licenses; see the complete downloaded package and its license archive |
| [pypdf](https://pypdf.readthedocs.io/) | Development tests only | [BSD-3-Clause](https://github.com/py-pdf/pypdf/blob/main/LICENSE) |

`tools/`, installed Python packages and compiled applications are not committed to this source repository. The ExifTool setup helper downloads a pinned, SHA-256-verified upstream archive and retains its complete license files, including notices for its Perl runtime. ExifTool runs as a separate process.

Camera references in `ratings.py` contain source links and provenance. Manufacturer badges are local typographic labels used for identification. No manufacturer endorsement is claimed.
