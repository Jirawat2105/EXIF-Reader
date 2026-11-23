import hashlib,io,unittest,zipfile
from unittest.mock import patch
from scripts import install_exiftool as setup

class SetupTests(unittest.TestCase):
    def payload(self,name):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:archive.writestr(name,b'test')
        return stream.getvalue()
    def test_checksum_mismatch(self):
        with self.assertRaisesRegex(ValueError,'checksum mismatch'):setup.verified_archive(b'not the pinned archive')
    def test_path_escape_rejected_even_with_matching_digest(self):
        payload=self.payload(setup.PACKAGE+'/../../outside.txt')
        with patch.object(setup,'SHA256',hashlib.sha256(payload).hexdigest()):
            with self.assertRaisesRegex(ValueError,'Unexpected path'):setup.verified_archive(payload)
    def test_expected_root_is_accepted(self):
        payload=self.payload(setup.PACKAGE+'/README.txt')
        with patch.object(setup,'SHA256',hashlib.sha256(payload).hexdigest()):
            with setup.verified_archive(payload) as archive:self.assertEqual(len(archive.infolist()),1)

if __name__=='__main__':unittest.main()
