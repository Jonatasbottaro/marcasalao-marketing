"""Testes do verificador compartilhado de pacote ZIP (tools/delivery_verify.py)."""

import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
TOOLS = os.path.join(ROOT, 'tools')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import delivery_verify


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def build_manifest(files, pieces=None, channels=None, schema_version=1):
    return {
        'schemaVersion': schema_version,
        'packageId': 'trabalho-pkg-123',
        'workId': 'trabalho-1',
        'workName': 'Trabalho fictício',
        'project': 'marca-salao',
        'createdAt': '2026-11-17T00:00:00Z',
        'modalities': ['video'],
        'profiles': ['instagram-reels-video'],
        'pieces': pieces if pieces is not None else [],
        'channels': channels or [],
        'files': files,
    }


class DeliveryVerifyTest(unittest.TestCase):
    def setUp(self):
        tmp_dir = os.path.join(ROOT, '.workspace', 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        self.base = tempfile.mkdtemp(prefix='delivery-verify-', dir=tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def _write_zip(self, name, files, manifest=None, manifest_name='package-manifest.json'):
        zip_path = os.path.join(self.base, name)
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for arc, data in files.items():
                zf.writestr(arc, data)
            if manifest is not None:
                zf.writestr(manifest_name, json.dumps(manifest, ensure_ascii=False))
        return zip_path

    def _valid_files(self):
        video = b'mp4-prova-sem-audio'
        srt = b'1\n00:00:00,000 --> 00:00:04,000\nLegenda\n'
        return {
            'video/instagram-reels-video/primary-output.mp4': video,
            'video/instagram-reels-video/subtitles.srt': srt,
        }

    def _valid_manifest(self, files, with_hashes=True):
        entries = []
        nested = []
        for arc, data in files.items():
            item = {
                'archivePath': arc,
                'kind': 'video' if arc.endswith('.mp4') else 'srt',
                'sourcePath': arc,
                'bytes': len(data),
            }
            if with_hashes:
                item['sha256'] = sha256_bytes(data)
            entries.append(item)
            nested.append({k: item[k] for k in ('archivePath', 'bytes', 'sha256') if k in item})
        pieces = [{
            'modality': 'video',
            'profileId': 'instagram-reels-video',
            'deliveryVersionId': 'video-instagram-reels-video-v1-abc',
            'draftFingerprint': 'abc',
            'reviewedDecision': {'decision': 'approved_for_local_delivery'},
            'files': nested,
        }]
        return build_manifest(entries, pieces=pieces)

    def test_valid_package(self):
        files = self._valid_files()
        manifest = self._valid_manifest(files)
        zip_path = self._write_zip('ok.zip', files, manifest)
        result = delivery_verify.verify_package_zip(zip_path)
        self.assertTrue(result['ok'], result['errors'])
        self.assertEqual(result['packageId'], 'trabalho-pkg-123')
        self.assertEqual(len(result['files']), 2)
        self.assertEqual(len(result['pieces']), 1)
        self.assertIn('íntegro', result['summary'])

    def test_string_decision_supported(self):
        files = self._valid_files()
        manifest = self._valid_manifest(files)
        manifest['pieces'][0]['reviewedDecision'] = 'approved_for_local_delivery'
        zip_path = self._write_zip('string-decision.zip', files, manifest)
        result = delivery_verify.verify_package_zip(zip_path)
        self.assertTrue(result['ok'], result['errors'])

    def test_missing_declared_file(self):
        files = self._valid_files()
        manifest = self._valid_manifest(files)
        del files['video/instagram-reels-video/subtitles.srt']
        zip_path = self._write_zip('missing.zip', files, manifest)
        result = delivery_verify.verify_package_zip(zip_path)
        self.assertFalse(result['ok'])
        self.assertTrue(any(e.get('file', '').endswith('subtitles.srt') for e in result['errors']))

    def test_divergent_content(self):
        files = self._valid_files()
        manifest = self._valid_manifest(files)
        files['video/instagram-reels-video/primary-output.mp4'] = b'conteudo-divergente'
        zip_path = self._write_zip('divergent.zip', files, manifest)
        result = delivery_verify.verify_package_zip(zip_path)
        self.assertFalse(result['ok'])
        self.assertTrue(any('sha256' in (e.get('field') or '') for e in result['errors']))

    def test_external_sha_mismatch(self):
        files = self._valid_files()
        manifest = self._valid_manifest(files)
        zip_path = self._write_zip('sha.zip', files, manifest)
        result = delivery_verify.verify_package_zip(zip_path, expected_zip_sha256='0' * 64)
        self.assertFalse(result['ok'])
        self.assertFalse(result['zipSha256']['match'])

    def test_legacy_without_hashes_reports_limitation(self):
        files = self._valid_files()
        manifest = self._valid_manifest(files, with_hashes=False)
        zip_path = self._write_zip('legacy.zip', files, manifest)
        result = delivery_verify.verify_package_zip(zip_path)
        self.assertTrue(result['ok'], result['errors'])
        self.assertTrue(result['limitations'])

    def test_cli_exit_codes(self):
        files = self._valid_files()
        manifest = self._valid_manifest(files)
        zip_path = self._write_zip('cli.zip', files, manifest)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = delivery_verify.main([zip_path, '--json'])
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertTrue(payload['ok'])

        out_fail = io.StringIO()
        with contextlib.redirect_stdout(out_fail):
            code_fail = delivery_verify.main([zip_path, '--json', '--expected-sha256', 'f' * 64])
        self.assertEqual(code_fail, 1)

    def test_unknown_schema_version_fails(self):
        files = self._valid_files()
        manifest = self._valid_manifest(files)
        manifest['schemaVersion'] = 999
        zip_path = self._write_zip('schema-999.zip', files, manifest)
        result = delivery_verify.verify_package_zip(zip_path)
        self.assertFalse(result['ok'])
        self.assertTrue(any(e.get('field') == 'schemaVersion' for e in result['errors']))
        self.assertNotIn('íntegro', result['summary'])

    def test_missing_schema_is_legacy(self):
        files = self._valid_files()
        manifest = self._valid_manifest(files)
        del manifest['schemaVersion']
        zip_path = self._write_zip('schema-missing.zip', files, manifest)
        result = delivery_verify.verify_package_zip(zip_path)
        self.assertTrue(result['ok'], result['errors'])
        self.assertTrue(any('schemaVersion ausente' in item for item in result['limitations']))

    def test_pieces_not_list(self):
        files = self._valid_files()
        manifest = self._valid_manifest(files)
        manifest['pieces'] = 7
        zip_path = self._write_zip('pieces-7.zip', files, manifest)
        result = delivery_verify.verify_package_zip(zip_path)
        self.assertFalse(result['ok'])
        self.assertTrue(any(e.get('field') == 'pieces' for e in result['errors']))

    def test_files_not_list(self):
        files = self._valid_files()
        manifest = self._valid_manifest(files)
        manifest['files'] = {'x': 1}
        zip_path = self._write_zip('files-dict.zip', files, manifest)
        result = delivery_verify.verify_package_zip(zip_path)
        self.assertFalse(result['ok'])
        self.assertTrue(any(e.get('field') == 'files' for e in result['errors']))

    def test_channels_not_list(self):
        files = self._valid_files()
        manifest = self._valid_manifest(files)
        manifest['channels'] = 'x'
        zip_path = self._write_zip('channels-str.zip', files, manifest)
        result = delivery_verify.verify_package_zip(zip_path)
        self.assertFalse(result['ok'])
        self.assertTrue(any(e.get('field') == 'channels' for e in result['errors']))

    def test_piece_files_not_list(self):
        files = self._valid_files()
        manifest = self._valid_manifest(files)
        manifest['pieces'][0]['files'] = 7
        zip_path = self._write_zip('piece-files-7.zip', files, manifest)
        result = delivery_verify.verify_package_zip(zip_path)
        self.assertFalse(result['ok'])
        self.assertTrue(any((e.get('field') or '').startswith('pieces.files') for e in result['errors']))

    def test_channel_files_not_list(self):
        files = self._valid_files()
        manifest = self._valid_manifest(files)
        manifest['channels'] = [{
            'profileId': 'instagram-feed-carousel',
            'files': 7,
            'reviewedDecision': {'decision': 'approved_for_local_delivery'},
        }]
        zip_path = self._write_zip('channel-files-7.zip', files, manifest)
        result = delivery_verify.verify_package_zip(zip_path)
        self.assertFalse(result['ok'])
        self.assertTrue(any((e.get('field') or '').startswith('channels.files') for e in result['errors']))

    def test_cli_pieces_not_list_valid_json(self):
        files = self._valid_files()
        manifest = self._valid_manifest(files)
        manifest['pieces'] = 7
        zip_path = self._write_zip('cli-pieces-7.zip', files, manifest)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = delivery_verify.main([zip_path, '--json'])
        self.assertNotEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertFalse(payload['ok'])

    def test_cli_malformed_manifest_valid_json(self):
        files = self._valid_files()
        zip_path = self._write_zip('bad-manifest.zip', files, None)
        with zipfile.ZipFile(zip_path, 'a') as zf:
            zf.writestr('package-manifest.json', '{nao-json')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = delivery_verify.main([zip_path, '--json'])
        self.assertNotEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertFalse(payload['ok'])


if __name__ == '__main__':
    unittest.main()