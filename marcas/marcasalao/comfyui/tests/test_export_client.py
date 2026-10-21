import copy
import hashlib
import io
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import marcasalao_export as export


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.media = {}
        self.manifest = {'schema_version': 1, 'brand': 'marcasalao', 'bundle': 'marcasalao/teste/run',
                         'status': 'prepared', 'review_required': True, 'publication_authorized': False,
                         'postiz': {'mode': 'draft_only', 'media_uploaded': False, 'drafts_created': False,
                                    'integrations': {'facebook': 'cmvbegwql0001msbhvdpjy0in', 'instagram': 'cmvbeq3100003msbhihu2dm4z'}},
                         'images': [], 'captions': {}}
        for network in ('facebook', 'instagram'):
            for fmt, size in [('quadrado', (1080, 1080)), ('vertical', (1080, 1350)), ('stories', (1080, 1920))]:
                data = io.BytesIO()
                Image.new('RGB', size).save(data, 'PNG')
                name = f'{network}-{fmt}.png'
                self.media[name] = data.getvalue()
                self.manifest['images'].append({'file': name, 'width': size[0], 'height': size[1],
                                               'network': network, 'format': fmt,
                                               'sha256': hashlib.sha256(data.getvalue()).hexdigest()})
            self.manifest['captions'][network] = {'file': f'legenda-{network}.txt', 'text': 'Olá',
                                                 'sha256': hashlib.sha256('Olá\n'.encode()).hexdigest()}

    def test_downloads_complete_package_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            package = export.download_bundle(self.manifest, Path(temp), lambda item: self.media[item['file']])
            self.assertEqual((package / 'facebook-quadrado.png').read_bytes(), self.media['facebook-quadrado.png'])
            self.assertEqual((package / 'legenda-facebook.txt').read_text(), 'Olá\n')
            self.assertTrue((package / 'manifest.json').is_file())
            with self.assertRaises(FileExistsError):
                export.download_bundle(self.manifest, Path(temp), lambda item: self.media[item['file']])

    def test_rejects_incomplete_or_wrong_contract_before_fetch(self):
        for changes in [{'images': []}, {'captions': {}}, {'publication_authorized': True},
                        {'images': self.manifest['images'][:1]}, {'review_required': False}]:
            manifest = self.manifest | changes
            with tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):
                export.download_bundle(manifest, Path(temp), lambda item: self.fail('Não deveria baixar mídia de contrato inválido'))

    def test_rejects_png_truncated_after_header_even_with_matching_hash(self):
        bad = b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\rIHDR' + struct.pack('>II', 1080, 1080)
        manifest = copy.deepcopy(self.manifest)
        manifest['images'][0]['sha256'] = hashlib.sha256(bad).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                export.download_bundle(manifest, Path(temp), lambda item: bad if item['file'] == 'facebook-quadrado.png' else self.media[item['file']])
            self.assertFalse((Path(temp) / 'marcasalao/teste/run').exists())

    def test_rejects_traversal_and_hash_mismatch_without_final_package(self):
        for field, value in [('bundle', 'marcasalao/../escape'), ('file', '../escape'), ('sha256', 'bad')]:
            manifest = copy.deepcopy(self.manifest)
            if field == 'bundle': manifest[field] = value
            else: manifest['images'][0][field] = value
            with tempfile.TemporaryDirectory() as temp:
                with self.assertRaises(ValueError):
                    export.download_bundle(manifest, Path(temp), lambda item: self.media.get(item['file'], b'corrupt'))
                self.assertFalse((Path(temp) / 'marcasalao/teste/run').exists())


if __name__ == '__main__':
    unittest.main()
