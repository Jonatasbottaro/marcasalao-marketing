"""Testes de edicao de gravacoes e cortes por cena no Video Studio.

Cobrem o contrato sourceStartMs (pedido legado, valores invalidos, corte em
imagem), a previa plan-only com janela da fonte distinta da posicao na
montagem, o render real com seek preciso entre keyframes (verificacao de
quadros por cor do trecho), fim exato e alem do arquivo, midia ausente,
troca de midia, reexportacao de um perfil com hashes previstos, registro dos
cortes no manifesto/relatorio, importacao de MP4 em blocos com FFprobe,
leitura em intervalos HTTP (seek), persistencia/reinicio e revisao/ZIP.
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import make_proof_assets
import make_request_media
import produce_video
import render_local
from test_multi_format import decode_png
from test_video_studio import (
    HAS_BRIDGE,
    HAS_FFMPEG,
    REQUIRE_RENDER,
    STUDIO_ROOT,
    StudioTestBase,
    read_json,
)

PROJECT_MS = 'platform/examples/projects/marca-salao-social.project.json'
TMP_BASE = os.path.join(STUDIO_ROOT, '.workspace', 'tmp', 't_rc')

# Trechos da gravacao fixture: A vermelho 0-4s, B verde 4-8s, C azul 8-12s.
# GOP de 90 quadros (3s): keyframes em 0/3/6/9s, nunca nas fronteiras 4/8s.
SEG_RED = (220, 40, 40)
SEG_GREEN = (40, 190, 60)
SEG_BLUE = (50, 80, 220)


def color_signature(px):
    r, g, b = px
    if r > 150 and g < 110 and b < 110:
        return 'A'
    if g > 130 and r < 120 and b < 120:
        return 'B'
    if b > 150 and r < 120 and g < 130:
        return 'C'
    return None


def extract_pixel(video_path, t_seconds, fx, fy, out_png):
    cmd = [build_video.get_ffmpeg(), '-y', '-ss', f'{t_seconds:.3f}', '-i', video_path,
           '-frames:v', '1', out_png]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if res.returncode != 0:
        raise AssertionError(f'extracao de quadro falhou em t={t_seconds}: {res.stderr[-200:]}')
    w, h, px = decode_png(out_png)
    x, y = int(w * fx), int(h * fy)
    return tuple(px[(y * w + x) * 3:(y * w + x) * 3 + 3])


def run_produce(argv):
    buf = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        code = produce_video.main(argv)
    out = buf.getvalue()
    try:
        payload = json.loads(out)
    except ValueError:
        payload = None
    return code, payload, err.getvalue()


def delivery_artifact(out_rel, profile_id, kind):
    """Caminho absoluto do artefato promovido, lido do manifesto (fonte de verdade)."""
    manifest = read_json(os.path.join(STUDIO_ROOT, out_rel, profile_id, 'delivery-manifest.json'))
    return os.path.join(STUDIO_ROOT, manifest['artifacts'][kind]['path'])


def base_request(work_dir_rel, media_rel, image_rel, profiles=None):
    return {
        'schemaVersion': 1,
        'id': 'pc',
        'project': PROJECT_MS,
        'title': 'Prova de cortes por cena',
        'profiles': profiles or ['instagram-reels-video', 'youtube-video-horizontal'],
        'media': [
            {'id': 'gravacao', 'path': media_rel, 'type': 'video', 'origin': 'synthetic-demo', 'license': 'owned-synthetic'},
            {'id': 'cartela', 'path': image_rel, 'type': 'image', 'origin': 'synthetic-demo', 'license': 'owned-synthetic'},
        ],
        'scenes': [
            {'id': 'cena-1', 'durationMs': 2400, 'sourceStartMs': 4200, 'mediaId': 'gravacao',
             'caption': 'Trecho B da gravacao', 'narration': 'Narracao do trecho B.', 'title': 'TITULO CORTE B'},
            {'id': 'cena-2', 'durationMs': 2000, 'mediaId': 'cartela',
             'caption': 'Cartela estatica', 'narration': 'Narracao da cartela.'},
            {'id': 'cena-3', 'durationMs': 1700, 'sourceStartMs': 8300, 'mediaId': 'gravacao',
             'caption': 'Trecho C da gravacao', 'narration': 'Narracao do trecho C.'},
            {'id': 'cena-4', 'durationMs': 1500, 'sourceStartMs': 4200, 'mediaId': 'gravacao',
             'caption': 'Trecho B reaproveitado', 'narration': 'Narracao do trecho B de novo.'},
        ],
    }


class RecordingCutsRenderTest(unittest.TestCase):
    """Render real com cortes, sem servidor HTTP (produce_video direto)."""

    @classmethod
    def setUpClass(cls):
        if not HAS_BRIDGE:
            raise unittest.SkipTest('ponte TypeScript indisponivel')
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError('REQUIRE_RENDER=1 sem FFmpeg disponivel')
            raise unittest.SkipTest('FFmpeg indisponivel')
        render_local.ensure_video_tools(STUDIO_ROOT)

    def setUp(self):
        self.dir = os.path.join(TMP_BASE, self._testMethodName[:12])
        shutil.rmtree(render_local.fs_path(self.dir, force=True), ignore_errors=True)
        os.makedirs(render_local.fs_path(self.dir), exist_ok=True)
        self.media_rel = f'.workspace/tmp/t_rc/{self._testMethodName[:12]}/gravacao.mp4'
        self.image_rel = f'.workspace/tmp/t_rc/{self._testMethodName[:12]}/cartela.png'
        self.out_rel = f'.workspace/tmp/t_rc/{self._testMethodName[:12]}/entrega'
        self.request_path = os.path.join(self.dir, 'pedido.video-request.json')

    def tearDown(self):
        shutil.rmtree(render_local.fs_path(self.dir, force=True), ignore_errors=True)

    def write_request(self, request):
        with open(self.request_path, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(request, handle, ensure_ascii=False, indent=2)
        return self.request_path

    def make_fixture(self, request, recording=True):
        make_request_media.generate_request_media(request, STUDIO_ROOT, recording=recording)

    def short_copy(self, video_abs):
        """Copia curta para o FFmpeg: caminhos longos do Windows nao cabem em MAX_PATH."""
        dst = os.path.join(self.dir, 'src.mp4')
        shutil.copyfile(render_local.fs_path(video_abs), render_local.fs_path(dst))
        return dst

    def produce(self, request, extra=None):
        self.write_request(request)
        argv = ['--input', self.request_path, '--root', STUDIO_ROOT, '--json']
        argv += extra or ['--output-dir', os.path.join(STUDIO_ROOT, self.out_rel)]
        return run_produce(argv)

    def test_plan_only_mostra_fonte_e_montagem_distintas(self):
        request = base_request(self.dir, self.media_rel, self.image_rel)
        code, payload, _ = self.produce(request, extra=['--plan-only'])
        self.assertEqual(code, 0)
        self.assertEqual(payload['status'], 'preview')
        for profile in payload['profiles']:
            beats = profile['beats']
            self.assertEqual([b['startMs'] for b in beats], [0, 2400, 4400, 6100])
            self.assertEqual([b['endMs'] for b in beats], [2400, 4400, 6100, 7600])
            self.assertEqual([b['sourceStartMs'] for b in beats], [4200, None, 8300, 4200])
            self.assertEqual([b['sourceEndMs'] for b in beats], [6600, None, 10000, 5700])
        # Sem FFmpeg obrigatorio: a previa nao le midia (arquivos nem existem).
        self.assertFalse(os.path.exists(os.path.join(STUDIO_ROOT, self.media_rel)))

    def test_pedido_legado_sem_corte_continua_renderizando(self):
        request = base_request(self.dir, self.media_rel, self.image_rel, profiles=['instagram-reels-video'])
        for scene in request['scenes']:
            scene.pop('sourceStartMs', None)
            scene['durationMs'] = 2000
        self.make_fixture(request, recording=False)
        code, payload, err = self.produce(request)
        self.assertEqual(code, 0, err)
        manifest = read_json(os.path.join(STUDIO_ROOT, self.out_rel, 'instagram-reels-video', 'delivery-manifest.json'))
        for cut in manifest['sourceCuts']:
            self.assertEqual(cut['sourceStartMs'], 0)
            self.assertEqual(cut['sourceEndMs'], cut['durationMs'])

    def test_inicio_negativo_ou_fracionario_reprovado_no_contrato(self):
        for bad in (-100, 1.5):
            request = base_request(self.dir, self.media_rel, self.image_rel)
            request['scenes'][0]['sourceStartMs'] = bad
            code, payload, err = self.produce(request, extra=['--plan-only'])
            self.assertEqual(code, 3, f'valor {bad}: {err}')

    def test_corte_em_imagem_reprovado_no_contrato(self):
        request = base_request(self.dir, self.media_rel, self.image_rel)
        request['scenes'][1]['sourceStartMs'] = 500
        code, _, err = self.produce(request, extra=['--plan-only'])
        self.assertEqual(code, 3, err)

    def test_render_real_cortes_precisos_entre_keyframes(self):
        request = base_request(self.dir, self.media_rel, self.image_rel)
        self.make_fixture(request)
        # Keyframes da fixture em 0/3/6/9s; cortes em 4.2s e 8.3s caem entre eles.
        probe = subprocess.run(
            [build_video.get_ffprobe(), '-v', 'error', '-select_streams', 'v',
             '-show_entries', 'packet=pts_time,flags', '-of', 'json',
             os.path.join(STUDIO_ROOT, self.media_rel)],
            capture_output=True, text=True, timeout=60)
        packets = json.loads(probe.stdout)['packets']
        keyframes = [float(p['pts_time']) for p in packets if 'K' in p['flags']]
        self.assertIn(3.0, keyframes)
        self.assertNotIn(4.0, keyframes)
        self.assertNotIn(8.0, keyframes)

        code, payload, err = self.produce(request)
        self.assertEqual(code, 0, err)
        frame_png = os.path.join(self.dir, 'frame.png')
        expected = {
            'instagram-reels-video': (1080, 1920, 0.10, 0.92),
            'youtube-video-horizontal': (1920, 1080, 0.50, 0.92),
        }
        for profile_id, (width, height, fx, fy) in expected.items():
            video = delivery_artifact(self.out_rel, profile_id, 'video')
            self.assertTrue(os.path.isfile(render_local.fs_path(video)), video)
            video = self.short_copy(video)
            inspection = payload['profiles'][0 if profile_id == 'instagram-reels-video' else 1]['inspection']
            self.assertEqual((inspection['width'], inspection['height']), (width, height))
            self.assertEqual(inspection['audioStreams'], 0)
            self.assertAlmostEqual(inspection['duration'], 7.6, delta=0.11)
            # Janela da montagem: B [0,2.4), cartela [2.4,4.4), C [4.4,6.1), B [6.1,7.6).
            self.assertEqual(color_signature(extract_pixel(video, 0.10, fx, fy, frame_png)), 'B',
                             'primeiro quadro deve ser o trecho B (nao o instante 0 nem o keyframe 3s)')
            self.assertEqual(color_signature(extract_pixel(video, 1.20, fx, fy, frame_png)), 'B')
            pixel_cartela = extract_pixel(video, 3.00, fx, fy, frame_png)
            pixel_b = extract_pixel(video, 1.20, fx, fy, frame_png)
            self.assertGreater(sum(abs(a - b) for a, b in zip(pixel_cartela, pixel_b)), 30,
                               'cena de imagem deve diferir do trecho B')
            self.assertEqual(color_signature(extract_pixel(video, 5.00, fx, fy, frame_png)), 'C',
                             'trecho C deve comecar em 8.3s da fonte (keyframe anterior e 6s, trecho B)')
            self.assertEqual(color_signature(extract_pixel(video, 6.80, fx, fy, frame_png)), 'B',
                             'trecho B reaproveitado em outra posicao da montagem')
            # SRT alinhado a montagem, nao a fonte.
            with open(render_local.fs_path(delivery_artifact(self.out_rel, profile_id, 'srt')), encoding='utf-8') as handle:
                srt = handle.read()
            self.assertIn('00:00:00,000 --> 00:00:02,400', srt)
            self.assertIn('00:00:02,400 --> 00:00:04,400', srt)
            self.assertIn('00:00:04,400 --> 00:00:06,100', srt)
            self.assertIn('00:00:06,100 --> 00:00:07,600', srt)
            # Manifesto e relatorio registram os trechos, a identidade e o hash da fonte.
            manifest = read_json(os.path.join(STUDIO_ROOT, self.out_rel, profile_id, 'delivery-manifest.json'))
            cuts = manifest['sourceCuts']
            self.assertEqual([c['sourceStartMs'] for c in cuts], [4200, 0, 8300, 4200])
            self.assertEqual([c['sourceEndMs'] for c in cuts], [6600, 2000, 10000, 5700])
            source_sha = render_local.sha256_file(os.path.join(STUDIO_ROOT, self.media_rel))
            for cut in cuts:
                if cut['beatId'] != 'cena-2':
                    self.assertEqual(cut['sha256'], source_sha)
                    self.assertEqual(cut['assetId'], cuts[0]['assetId'])

    def test_fim_exato_na_duracao_disponivel_e_aceito(self):
        request = base_request(self.dir, self.media_rel, self.image_rel, profiles=['instagram-reels-video'])
        request['scenes'] = [
            {'id': 'cena-fim', 'durationMs': 2000, 'sourceStartMs': 10000, 'mediaId': 'gravacao',
             'caption': 'Fim exato', 'narration': 'Narracao do fim exato.'},
        ]
        self.make_fixture(request)
        code, _, err = self.produce(request)
        self.assertEqual(code, 0, err)

    def test_corte_alem_do_arquivo_falha_e_preserva_entrega(self):
        request = base_request(self.dir, self.media_rel, self.image_rel, profiles=['instagram-reels-video'])
        self.make_fixture(request)
        code, _, err = self.produce(request)
        self.assertEqual(code, 0, err)
        video_abs = delivery_artifact(self.out_rel, 'instagram-reels-video', 'video')
        sha_before = render_local.sha256_file(video_abs)

        request['scenes'][2]['durationMs'] = 4000  # 8300 + 4000 = 12300 > 12000
        code, payload, err = self.produce(request)
        self.assertEqual(code, 1, err)
        self.assertIn('SOURCE_CUT_OUT_OF_RANGE', err + json.dumps(payload))
        self.assertEqual(render_local.sha256_file(video_abs), sha_before)
        index = read_json(os.path.join(STUDIO_ROOT, self.out_rel, 'index.json'))
        entry = index['profiles'][0]
        self.assertEqual(entry['status'], 'completed')
        self.assertTrue(entry['lastValidDelivery'])
        self.assertEqual(entry['lastAttempt']['status'], 'failed')

    def test_midia_ausente_falha_com_codigo_estavel(self):
        request = base_request(self.dir, self.media_rel, self.image_rel, profiles=['instagram-reels-video'])
        self.make_fixture(request)
        os.remove(os.path.join(STUDIO_ROOT, self.media_rel))
        code, payload, err = self.produce(request)
        self.assertEqual(code, 1, err)
        combined = err + json.dumps(payload)
        self.assertTrue('ASSET_MISSING' in combined or 'asset nao encontrado' in combined, combined)

    def test_troca_de_midia_mais_curta_falha_e_preserva(self):
        request = base_request(self.dir, self.media_rel, self.image_rel, profiles=['instagram-reels-video'])
        self.make_fixture(request)
        code, _, err = self.produce(request)
        self.assertEqual(code, 0, err)
        video_abs = delivery_artifact(self.out_rel, 'instagram-reels-video', 'video')
        sha_before = render_local.sha256_file(video_abs)
        # Substitui a fonte por um clipe de 3s (troca de midia sem ajustar o corte).
        make_proof_assets.write_scene_mp4(os.path.join(STUDIO_ROOT, self.media_rel),
                                          'pedido-cortes', 'gravacao', 1, duration_s=3.0)
        code, payload, err = self.produce(request)
        self.assertEqual(code, 1, err)
        self.assertIn('SOURCE_CUT_OUT_OF_RANGE', err + json.dumps(payload))
        self.assertEqual(render_local.sha256_file(video_abs), sha_before)

    def test_reexportacao_so_do_inicio_muda_mp4_e_preserva_textos(self):
        request = base_request(self.dir, self.media_rel, self.image_rel)
        self.make_fixture(request)
        code, _, err = self.produce(request)
        self.assertEqual(code, 0, err)
        base = os.path.join(STUDIO_ROOT, self.out_rel)

        def hashes(profile_id):
            return {
                kind: render_local.sha256_file(delivery_artifact(self.out_rel, profile_id, kind))
                for kind in ('video', 'srt', 'narration')
            }

        reels_before = hashes('instagram-reels-video')
        horiz_before = hashes('youtube-video-horizontal')
        source_sha = render_local.sha256_file(os.path.join(STUDIO_ROOT, self.media_rel))

        # Altera apenas o inicio de cena-1 (4200 -> 4600); duracao e textos iguais.
        request['scenes'][0]['sourceStartMs'] = 4600
        code, _, err = self.produce(request, extra=['--output-dir', base, '--profile', 'instagram-reels-video'])
        self.assertEqual(code, 0, err)
        reels_after = hashes('instagram-reels-video')
        self.assertNotEqual(reels_after['video'], reels_before['video'])
        self.assertEqual(reels_after['srt'], reels_before['srt'])
        self.assertEqual(reels_after['narration'], reels_before['narration'])
        self.assertEqual(render_local.sha256_file(os.path.join(STUDIO_ROOT, self.media_rel)), source_sha)
        # Perfil fora da reexportacao: arquivos intactos.
        self.assertEqual(hashes('youtube-video-horizontal'), horiz_before)
        # O quadro do perfil reexportado continua no trecho B (4.6s ainda e B).
        frame_png = os.path.join(self.dir, 'frame.png')
        video = self.short_copy(delivery_artifact(self.out_rel, 'instagram-reels-video', 'video'))
        self.assertEqual(color_signature(extract_pixel(video, 0.10, 0.10, 0.92, frame_png)), 'B')


class RecordingCutsStudioTest(StudioTestBase):
    """Importacao de MP4, seek HTTP, persistencia, revisao e ZIP via Studio."""

    @classmethod
    def setUpClass(cls):
        if not HAS_BRIDGE:
            raise unittest.SkipTest('ponte TypeScript indisponivel')
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError('REQUIRE_RENDER=1 sem FFmpeg disponivel')
            raise unittest.SkipTest('FFmpeg indisponivel')
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.work_id = f't-rc-{self._testMethodName[:24].replace("_", "-").strip("-")}'
        work_dir = os.path.join(STUDIO_ROOT, '.workspace', 'studio', 'works', self.work_id)
        shutil.rmtree(render_local.fs_path(work_dir, force=True), ignore_errors=True)
        status, data = self.request('POST', '/api/works/create', {
            'id': self.work_id, 'name': 'Trabalho de cortes', 'project': PROJECT_MS,
            'template': 'blank', 'overwrite': True,
        })
        self.assertEqual(status, 200, data)
        self.fixture = os.path.join(self.dir, 'gravacao-fixture.mp4')
        make_proof_assets.write_recording_mp4(self.fixture, duration_s=12.0)

    def import_recording(self, asset_id=None, origin='imported-manual'):
        with open(self.fixture, 'rb') as handle:
            data = handle.read()
        import base64
        status, start = self.request('POST', '/api/works/media/import-video/start', {
            'workId': self.work_id, 'fileName': 'gravacao.mp4', 'totalBytes': len(data),
            'origin': origin, 'license': 'owned-synthetic', 'assetId': asset_id,
        })
        self.assertEqual(status, 200, start)
        upload_id = start['uploadId']
        chunk_size = start['chunkBytes']
        offset = 0
        while offset < len(data):
            chunk = data[offset:offset + chunk_size]
            status, resp = self.request('POST', '/api/works/media/import-video/chunk', {
                'uploadId': upload_id, 'offset': offset,
                'dataBase64': base64.b64encode(chunk).decode('ascii'),
            })
            self.assertEqual(status, 200, resp)
            offset += len(chunk)
        status, finish = self.request('POST', '/api/works/media/import-video/finish', {
            'uploadId': upload_id, 'workId': self.work_id,
        })
        self.assertEqual(status, 200, finish)
        return finish

    def test_importacao_mp4_em_blocos_com_ffprobe_e_versoes(self):
        finish = self.import_recording()
        version = finish['version']
        self.assertEqual(version['kind'], 'video')
        self.assertEqual(version['format'], 'mp4')
        self.assertEqual(version['codec'], 'h264')
        self.assertEqual((version['width'], version['height']), (1080, 1920))
        self.assertAlmostEqual(version['durationSeconds'], 12.0, delta=0.1)
        self.assertEqual(version['sha256'], render_local.sha256_file(self.fixture))
        self.assertEqual(version['bytes'], os.path.getsize(self.fixture))
        # Segunda importacao cria nova versao no mesmo asset, preservando a anterior.
        again = self.import_recording(asset_id=finish['assetId'])
        self.assertEqual(again['assetId'], finish['assetId'])
        self.assertNotEqual(again['versionId'], finish['versionId'])
        status, lib = self.request('GET', f'/api/works/media-library?id={self.work_id}')
        asset = next(a for a in lib['mediaLibrary']['assets'] if a['id'] == finish['assetId'])
        self.assertEqual(len(asset['versions']), 2)

    def test_importacao_rejeita_conteudo_invalido_e_preserva_biblioteca(self):
        import base64
        status, lib_before = self.request('GET', f'/api/works/media-library?id={self.work_id}')
        fp_before = lib_before['libraryFingerprint']
        garbage = b'isto nao e um mp4' * 100
        status, start = self.request('POST', '/api/works/media/import-video/start', {
            'workId': self.work_id, 'fileName': 'lixo.mp4', 'totalBytes': len(garbage),
        })
        self.assertEqual(status, 200, start)
        status, _ = self.request('POST', '/api/works/media/import-video/chunk', {
            'uploadId': start['uploadId'], 'offset': 0,
            'dataBase64': base64.b64encode(garbage).decode('ascii'),
        })
        self.assertEqual(status, 200)
        status, finish = self.request('POST', '/api/works/media/import-video/finish', {
            'uploadId': start['uploadId'], 'workId': self.work_id,
        })
        self.assertEqual(status, 400, finish)
        status, lib_after = self.request('GET', f'/api/works/media-library?id={self.work_id}')
        self.assertEqual(lib_after['libraryFingerprint'], fp_before)

    def test_source_media_range_permite_avancar_e_voltar(self):
        finish = self.import_recording()
        version = finish['version']
        path = version['path']
        import http.client
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=60)
        conn.request('GET', f'/source-media?path={path}', headers={
            'Host': self.host, 'Range': 'bytes=0-1023'})
        res = conn.getresponse()
        body = res.read()
        self.assertEqual(res.status, 206)
        self.assertEqual(res.getheader('Content-Range'), f'bytes 0-1023/{version["bytes"]}')
        self.assertEqual(len(body), 1024)
        conn.close()
        # Seek para o meio e volta ao inicio: intervalos distintos do mesmo arquivo.
        mid = version['bytes'] // 2
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=60)
        conn.request('GET', f'/source-media?path={path}', headers={
            'Host': self.host, 'Range': f'bytes={mid}-{mid + 511}'})
        res = conn.getresponse()
        mid_body = res.read()
        self.assertEqual(res.status, 206)
        self.assertEqual(len(mid_body), 512)
        conn.close()
        with open(self.fixture, 'rb') as handle:
            handle.seek(mid)
            self.assertEqual(mid_body, handle.read(512))

    def test_edicao_persiste_salvamento_recarga_e_reinicio(self):
        finish = self.import_recording()
        version = finish['version']
        status, opened = self.request('GET', f'/api/works/open?id={self.work_id}')
        self.assertEqual(status, 200)
        vreq = opened['videoRequest']
        vreq['media'] = [{'id': 'gravacao', 'path': version['path'], 'type': 'video',
                          'origin': version['origin'], 'license': version['license']}]
        vreq['scenes'] = [
            {'id': 'cena-1', 'durationMs': 2400, 'sourceStartMs': 4200, 'mediaId': 'gravacao',
             'caption': 'Trecho B', 'narration': 'Narracao B.'},
            {'id': 'cena-2', 'durationMs': 1500, 'sourceStartMs': 8300, 'mediaId': 'gravacao',
             'caption': 'Trecho C', 'narration': 'Narracao C.'},
        ]
        status, saved = self.request('POST', '/api/works/save', {'workId': self.work_id, 'videoRequest': vreq})
        self.assertEqual(status, 200, saved)
        status, reloaded = self.request('GET', f'/api/works/open?id={self.work_id}')
        scenes = reloaded['videoRequest']['scenes']
        self.assertEqual([s['sourceStartMs'] for s in scenes], [4200, 8300])
        self.restart_server()
        status, after = self.request('GET', f'/api/works/open?id={self.work_id}')
        self.assertEqual([s['sourceStartMs'] for s in after['videoRequest']['scenes']], [4200, 8300])
        # Previa consome a edicao salva: janela da fonte e posicao na montagem.
        status, preview = self.request('POST', '/api/preview', {'request': after['videoRequest']})
        self.assertEqual(status, 200)
        beats = preview['result']['profiles'][0]['beats']
        self.assertEqual([b['sourceStartMs'] for b in beats], [4200, 8300])
        self.assertEqual([b['startMs'] for b in beats], [0, 2400])

    def test_revisao_draft_outdated_por_corte_e_zip_com_referencia(self):
        finish = self.import_recording()
        version = finish['version']
        status, opened = self.request('GET', f'/api/works/open?id={self.work_id}')
        vreq = opened['videoRequest']
        vreq['id'] = 'rc'
        vreq['profiles'] = ['instagram-reels-video']
        vreq['media'] = [{'id': 'gravacao', 'path': version['path'], 'type': 'video',
                          'origin': version['origin'], 'license': version['license']}]
        vreq['scenes'] = [
            {'id': 'cena-1', 'durationMs': 2400, 'sourceStartMs': 4200, 'mediaId': 'gravacao',
             'caption': 'Trecho B', 'narration': 'Narracao B.'},
            {'id': 'cena-2', 'durationMs': 1500, 'sourceStartMs': 8300, 'mediaId': 'gravacao',
             'caption': 'Trecho C', 'narration': 'Narracao C.'},
        ]
        status, _ = self.request('POST', '/api/works/save', {'workId': self.work_id, 'videoRequest': vreq})
        self.assertEqual(status, 200)
        status, job = self.request('POST', '/api/export', {
            'request': vreq, 'outputDir': f'.workspace/studio/works/{self.work_id}/deliveries/video',
            'workId': self.work_id, 'profile': 'instagram-reels-video',
        })
        self.assertEqual(status, 200, job)
        deadline = time.time() + 300
        while time.time() < deadline:
            status, st = self.request('GET', f'/api/export/status?job={job["jobId"]}')
            if st['status'] != 'running':
                break
            time.sleep(1)
        self.assertEqual(st['status'], 'completed', st)

        status, review = self.request('GET', f'/api/works/review?id={self.work_id}')
        piece = next(p for p in review['pieces'] if p['modality'] == 'video')
        self.assertEqual(piece['status'], 'pending_review')
        status, decided = self.request('POST', '/api/works/review/decide', {
            'workId': self.work_id, 'targetType': 'piece', 'modality': 'video',
            'profileId': 'instagram-reels-video', 'decision': 'approved_for_local_delivery',
            'expectedVersionId': piece['deliveryVersionId'],
        })
        self.assertEqual(status, 200, decided)

        # Altera apenas o inicio: video deve pedir reexportacao (draft_outdated).
        vreq['scenes'][0]['sourceStartMs'] = 4600
        status, _ = self.request('POST', '/api/works/save', {'workId': self.work_id, 'videoRequest': vreq})
        self.assertEqual(status, 200)
        status, review2 = self.request('GET', f'/api/works/review?id={self.work_id}')
        piece2 = next(p for p in review2['pieces'] if p['modality'] == 'video')
        self.assertEqual(piece2['status'], 'draft_outdated')

        # Inicio omitido vs zero: mesma versao efetiva (sem draft_outdated extra).
        vreq['scenes'][0]['sourceStartMs'] = 4200
        status, _ = self.request('POST', '/api/works/save', {'workId': self.work_id, 'videoRequest': vreq})
        status, review3 = self.request('GET', f'/api/works/review?id={self.work_id}')
        piece3 = next(p for p in review3['pieces'] if p['modality'] == 'video')
        self.assertEqual(piece3['status'], 'approved')
        vreq['scenes'][0]['sourceStartMs'] = 0
        status, _ = self.request('POST', '/api/works/save', {'workId': self.work_id, 'videoRequest': vreq})
        status, review4 = self.request('GET', f'/api/works/review?id={self.work_id}')
        piece4 = next(p for p in review4['pieces'] if p['modality'] == 'video')
        self.assertEqual(piece4['status'], 'draft_outdated')  # 0 != 4200: corte mudou
        del vreq['scenes'][0]['sourceStartMs']
        status, _ = self.request('POST', '/api/works/save', {'workId': self.work_id, 'videoRequest': vreq})
        status, review5 = self.request('GET', f'/api/works/review?id={self.work_id}')
        piece5 = next(p for p in review5['pieces'] if p['modality'] == 'video')
        self.assertEqual(piece5['currentDraftFingerprint'], piece4['currentDraftFingerprint'],
                         'inicio omitido e zero devem produzir a mesma versao efetiva')

        # Reexporta, aprova e empacota: ZIP referencia os cortes e a fonte.
        status, job2 = self.request('POST', '/api/export', {
            'request': vreq, 'outputDir': f'.workspace/studio/works/{self.work_id}/deliveries/video',
            'workId': self.work_id, 'profile': 'instagram-reels-video',
        })
        deadline = time.time() + 300
        while time.time() < deadline:
            status, st2 = self.request('GET', f'/api/export/status?job={job2["jobId"]}')
            if st2['status'] != 'running':
                break
            time.sleep(1)
        self.assertEqual(st2['status'], 'completed', st2)
        status, review6 = self.request('GET', f'/api/works/review?id={self.work_id}')
        piece6 = next(p for p in review6['pieces'] if p['modality'] == 'video')
        status, _ = self.request('POST', '/api/works/review/decide', {
            'workId': self.work_id, 'targetType': 'piece', 'modality': 'video',
            'profileId': 'instagram-reels-video', 'decision': 'approved_for_local_delivery',
            'expectedVersionId': piece6['deliveryVersionId'],
        })
        self.assertEqual(status, 200)
        status, pkg = self.request('POST', '/api/works/package', {
            'workId': self.work_id,
            'pieces': [{'modality': 'video', 'profileId': 'instagram-reels-video',
                        'expectedVersionId': piece6['deliveryVersionId']}],
            'channels': [],
        })
        self.assertEqual(status, 200, pkg)
        pkg_delivery = pkg['packageDelivery']
        manifest = pkg_delivery['manifest']
        video_piece = next(p for p in manifest['pieces'] if p['modality'] == 'video')
        self.assertIn('sourceCuts', video_piece)
        self.assertEqual([c['sourceStartMs'] for c in video_piece['sourceCuts']], [0, 8300])
        import zipfile
        zip_abs = os.path.join(STUDIO_ROOT, pkg_delivery['lastValidDelivery']['zipPath'])
        with zipfile.ZipFile(zip_abs) as zf:
            self.assertIsNone(zf.testzip())
            pkg_manifest = json.loads(zf.read('package-manifest.json'))
            video_entry = next(p for p in pkg_manifest['pieces'] if p['modality'] == 'video')
            self.assertEqual(video_entry['sourceCuts'], video_piece['sourceCuts'])
            for file_entry in video_entry['files']:
                import hashlib
                self.assertEqual(hashlib.sha256(zf.read(file_entry['archivePath'])).hexdigest(),
                                 file_entry['sha256'])


if __name__ == '__main__':
    unittest.main()