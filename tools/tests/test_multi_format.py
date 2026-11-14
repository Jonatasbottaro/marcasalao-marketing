"""Testes da exportacao multiformato no Studio local (16:9 e 4:5).

Cobrem a matriz de compatibilidade por modulo (fonte compartilhada), o render
horizontal 1920x1080@30 H.264 sem audio com titulos/legendas encaixados, o
carrossel 4:5 1080x1350 com enquadramento preservado e overflow por card,
Motion restrito ao vertical, geometria do pedido de imagem por perfil,
revisao localizada por canal/perfil e o ZIP multiformato.
"""

import base64
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import unittest
import zipfile
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import image_adapters
import produce_carousel
import render_local
from test_video_studio import (
    HAS_BRIDGE,
    HAS_FFMPEG,
    REQUIRE_RENDER,
    STUDIO_ROOT,
    StudioTestBase,
    read_json,
)

PROJECT_REL = '.workspace/studio/projects/t-mf-proj.project.json'
ALLOWED = [
    'instagram-reels-video', 'youtube-shorts', 'youtube-video-horizontal',
    'instagram-feed-image-square', 'instagram-feed-image-portrait',
]

CREATIVE = {
    'hookOptions': [{'id': 'hook-1', 'text': 'Agenda organizada', 'angle': 'clareza'}],
    'selectedHookId': 'hook-1',
    'scriptSummary': 'Prova ficticia multiformato.',
    'videoScenes': [
        {'id': 'cena-abertura', 'objective': 'Abertura', 'narrativeFunction': 'hook',
         'durationMs': 4000, 'titleOverlay': 'TITULO HORIZONTAL DE PROVA', 'caption': 'Legenda de prova do quadro horizontal',
         'narration': 'Narracao 1', 'requiredMediaDescriptor': 'Ilustracao ficticia de abertura',
         'mediaId': 'abertura', 'motionIntent': 'none'},
        {'id': 'cena-prova', 'objective': 'Prova', 'narrativeFunction': 'demonstration',
         'durationMs': 4000, 'titleOverlay': 'Agenda do dia', 'caption': 'Segunda legenda de prova',
         'narration': 'Narracao 2', 'requiredMediaDescriptor': 'Captura ficticia da agenda',
         'mediaId': 'agenda', 'motionIntent': 'none'},
    ],
    'carouselCards': [
        {'id': 'capa', 'role': 'cover', 'title': 'Capa multiformato', 'body': 'Subtitulo direto', 'mediaId': 'abertura'},
        {'id': 'conteudo', 'role': 'content', 'title': 'Conteudo', 'body': 'Texto de apoio do card', 'mediaId': 'agenda'},
        {'id': 'fechamento', 'role': 'cta', 'title': 'Saiba mais', 'body': 'Confira na descricao'},
    ],
    'channelCopies': [],
}


def png_bytes(width, height, seed='mf'):
    return image_adapters.SimulatorImageAdapter().generate(seed, {'width': width, 'height': height})['bytes']


def decode_png(path):
    with open(path, 'rb') as handle:
        d = handle.read()
    pos = 8
    idat = b''
    w = h = None
    while pos < len(d):
        ln = struct.unpack('>I', d[pos:pos + 4])[0]
        tag = d[pos + 4:pos + 8]
        data = d[pos + 8:pos + 8 + ln]
        if tag == b'IHDR':
            w, h, _bd, _ct = struct.unpack('>IIBB', data[:10])
        if tag == b'IDAT':
            idat += data
        pos += 12 + ln
    raw = zlib.decompress(idat)
    stride = w * 3 + 1
    px = bytearray(w * h * 3)
    prev = bytearray(w * 3)
    for y in range(h):
        f = raw[y * stride]
        line = bytearray(raw[y * stride + 1:(y + 1) * stride])
        for x in range(len(line)):
            a = line[x - 3] if x >= 3 else 0
            b = prev[x]
            c = prev[x - 3] if x >= 3 else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        px[y * w * 3:(y + 1) * w * 3] = line
        prev = line
    return w, h, px


def text_bands(px, w, h, threshold=200):
    rows = [y for y in range(h) if any(px[(y * w + x) * 3] > threshold for x in range(0, w, 5))]
    if not rows:
        return []
    bands = []
    start = prev = rows[0]
    for y in rows[1:]:
        if y - prev > 10:
            bands.append((start, prev))
            start = y
        prev = y
    bands.append((start, prev))
    out = []
    for (y0, y1) in bands:
        xs = [x for x in range(w) for y in range(y0, y1 + 1, 2) if px[(y * w + x) * 3] > threshold]
        out.append({'y0': y0, 'y1': y1, 'x0': min(xs), 'x1': max(xs)})
    return out


class MultiFormatTestBase(StudioTestBase):
    @classmethod
    def setUpClass(cls):
        if not HAS_BRIDGE:
            raise unittest.SkipTest('ponte TypeScript indisponivel')
        super().setUpClass()

    def create_project(self, project_id='t-mf-proj', allowed=None, base='marca-salao-social'):
        manifest = {
            'schemaVersion': 1, 'id': project_id, 'name': 'Projeto ficticio multiformato',
            'locale': 'pt-BR', 'timezone': 'America/Sao_Paulo', 'brandTheme': project_id,
            'assetRoot': f'.workspace/studio/projects/{project_id}/assets',
            'contentPolicies': {
                'requireApprovedBriefing': True, 'requireApprovedScript': True,
                'prohibitPersonalData': True, 'requireFunctionalEvidence': True,
            },
            'outputProfiles': allowed if allowed is not None else ALLOWED,
        }
        status, data = self.request('POST', '/api/projects/create', {'project': manifest, 'overwrite': True})
        self.assertEqual(status, 200, data)
        return data['project']['path']

    def create_work(self, work_id, project_rel=None):
        work_dir = os.path.join(STUDIO_ROOT, '.workspace', 'studio', 'works', work_id)
        shutil.rmtree(render_local.fs_path(work_dir, force=True), ignore_errors=True)
        status, data = self.request('POST', '/api/works/create', {
            'id': work_id, 'name': 'Trabalho multiformato', 'project': project_rel or PROJECT_REL,
            'template': 'blank', 'overwrite': True,
        })
        self.assertEqual(status, 200, data)
        return data

    def save_creative(self, work_id, creative=None, carousel_profile='', recommended=None):
        payload = {'workId': work_id, 'creative': creative or CREATIVE, 'markCreativeChecked': True}
        if carousel_profile:
            payload['carouselProfileId'] = carousel_profile
        if recommended:
            payload['briefingExtended'] = {'recommendedProfiles': recommended}
        status, data = self.request('POST', '/api/works/planning/save', payload)
        self.assertEqual(status, 200, data)
        return data

    def wait_export(self, job_id, timeout=300):
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            status, data = self.request('GET', '/api/export/status?job=' + job_id)
            self.assertEqual(status, 200, data)
            if data['status'] in ('completed', 'failed'):
                return data
            time.sleep(1)
        self.fail('exportacao nao concluiu no tempo limite')

    def ffprobe(self, rel_path):
        out = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json',
             render_local.fs_path(os.path.join(STUDIO_ROOT, rel_path))],
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)


class CompatibilityMatrixTest(MultiFormatTestBase):
    def test_matrix_por_modulo_e_motivos(self):
        self.create_project()
        status, data = self.request('GET', '/api/profiles?project=' + PROJECT_REL)
        self.assertEqual(status, 200)
        profiles = {p['id']: p for p in data['listing']['profiles']}
        horiz = profiles['youtube-video-horizontal']
        self.assertTrue(horiz['localExportVideo'])
        self.assertFalse(horiz['localExportMotion'])
        self.assertEqual(horiz['localExport']['motion']['reason'], 'MOTION_VERTICAL_ONLY')
        portrait = profiles['instagram-feed-image-portrait']
        self.assertTrue(portrait['localExportCarousel'])
        self.assertFalse(portrait['localExportVideo'])
        square = profiles['instagram-feed-image-square']
        self.assertTrue(square['localExportCarousel'])
        stories_img = profiles['instagram-stories-image']
        self.assertFalse(stories_img['localExportCarousel'])
        self.assertEqual(stories_img['localExport']['carousel']['reason'], 'GEOMETRY_UNSUPPORTED')
        # Fora da allowlist: conhecido, com render, mas bloqueado para o projeto.
        status, data = self.request('GET', '/api/profiles?project=platform/examples/projects/multitrack-hub-social.project.json')
        mth = {p['id']: p for p in data['listing']['profiles']}
        self.assertEqual(mth['instagram-feed-image-portrait']['availability'], 'blocked')
        self.assertFalse(mth['instagram-feed-image-portrait']['localExportCarousel'])
        self.assertTrue(mth['instagram-feed-image-portrait']['localExport']['carousel']['supported'])

    def test_perfil_desconhecido_rejeitado(self):
        self.create_project()
        wid = 't-mf-unknown'
        self.create_work(wid)
        status, data = self.request('POST', '/api/preview', {
            'request': {**read_json(os.path.join(STUDIO_ROOT, 'tools/produce/examples/marca-salao-social-reel.video-request.json')),
                        'project': PROJECT_REL, 'profiles': ['perfil-fantasma']},
        })
        self.assertEqual(status, 200)
        profiles = data['result'].get('profiles') or []
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]['status'], 'failed')
        self.assertEqual(profiles[0]['failureCode'], 'OUTPUT_PROFILE_UNKNOWN')


class HorizontalVideoTest(MultiFormatTestBase):
    @classmethod
    def setUpClass(cls):
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError('REQUIRE_RENDER=1 mas FFmpeg/FFprobe ausentes')
            raise unittest.SkipTest('FFmpeg indisponivel')
        super().setUpClass()

    def test_horizontal_e_vertical_no_mesmo_pedido(self):
        self.create_project()
        wid = 't-mf-video'
        opened = self.create_work(wid)
        self.save_creative(wid, recommended=['instagram-reels-video', 'youtube-video-horizontal'])
        status, applied = self.request('POST', '/api/works/planning/apply', {
            'workId': wid, 'applyVideo': True,
        })
        self.assertEqual(status, 200, applied)
        vreq = applied['workData']['videoRequest']
        self.assertIn('youtube-video-horizontal', vreq['profiles'])
        self.assertIn('instagram-reels-video', vreq['profiles'])
        paths = applied['workData']['work']['paths']
        status, job = self.request('POST', '/api/export', {
            'workId': wid, 'kind': 'video', 'request': vreq, 'outputDir': paths['videoDeliveryDir'],
        })
        self.assertEqual(status, 200, job)
        result = self.wait_export(job['jobId'])
        self.assertEqual(result['status'], 'completed', result)
        done = {p['profileId']: p for p in result['result']['profiles'] if p['status'] == 'completed'}
        self.assertIn('youtube-video-horizontal', done)
        self.assertIn('instagram-reels-video', done)

        for pid, (w, h) in (('youtube-video-horizontal', (1920, 1080)), ('instagram-reels-video', (1080, 1920))):
            manifest = read_json(os.path.join(STUDIO_ROOT, paths['videoDeliveryDir'], pid, 'delivery-manifest.json'))
            probe = self.ffprobe(manifest['artifacts']['video']['path'])
            vstream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            self.assertEqual((vstream['width'], vstream['height']), (w, h))
            self.assertEqual(vstream['codec_name'], 'h264')
            self.assertEqual(vstream['r_frame_rate'], '30/1')
            self.assertEqual([s for s in probe['streams'] if s['codec_type'] == 'audio'], [])
            self.assertAlmostEqual(float(probe['format']['duration']), 8.0, delta=0.2)
            self.assertTrue(manifest['artifacts']['srt']['path'])
            self.assertTrue(manifest['artifacts']['narration']['path'])

        # Quadros com titulo e legenda: encaixe nas areas do 16:9.
        manifest = read_json(os.path.join(STUDIO_ROOT, paths['videoDeliveryDir'], 'youtube-video-horizontal', 'delivery-manifest.json'))
        frame = os.path.join(self.dir, 'horiz-frame.png')
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', '1.0', '-i',
                        render_local.fs_path(os.path.join(STUDIO_ROOT, manifest['artifacts']['video']['path'])),
                        '-frames:v', '1', render_local.fs_path(frame)], check=True, timeout=60)
        w, h, px = decode_png(frame)
        self.assertEqual((w, h), (1920, 1080))
        bands = text_bands(px, w, h)
        self.assertGreaterEqual(len(bands), 2, f'esperava titulo e legenda: {bands}')
        title, subtitle = bands[0], bands[-1]
        self.assertLess(title['y1'], h * 0.30, 'titulo deve ficar no topo')
        self.assertGreater(title['x0'], 60, 'titulo dentro da margem horizontal')
        self.assertLess(title['x1'], w - 60, 'titulo dentro da margem horizontal')
        self.assertGreater(subtitle['y0'], h * 0.60, 'legenda deve ficar na base')
        self.assertGreater(subtitle['x0'], 40)
        self.assertLess(subtitle['x1'], w - 40)
        self.assertLess(title['y1'], subtitle['y0'], 'titulo e legenda nao podem sobrepor')

    def test_falha_no_horizontal_preserva_vertical(self):
        self.create_project()
        wid = 't-mf-fail'
        self.create_work(wid)
        self.save_creative(wid, recommended=['instagram-reels-video', 'youtube-video-horizontal'])
        status, applied = self.request('POST', '/api/works/planning/apply', {'workId': wid, 'applyVideo': True})
        vreq = applied['workData']['videoRequest']
        paths = applied['workData']['work']['paths']
        status, job = self.request('POST', '/api/export', {
            'workId': wid, 'kind': 'video', 'request': vreq,
            'profile': 'instagram-reels-video', 'outputDir': paths['videoDeliveryDir'],
        })
        result = self.wait_export(job['jobId'])
        self.assertEqual(result['status'], 'completed', result)
        vertical_manifest = os.path.join(paths['videoDeliveryDir'], 'instagram-reels-video', 'delivery-manifest.json')
        sha_before = read_json(os.path.join(STUDIO_ROOT, vertical_manifest))['artifacts']['video']['sha256']

        # Corrompe a midia usada apenas pelo horizontal? Ambos compartilham midia;
        # em vez disso, força falha no horizontal com perfil inexistente no pedido
        # nao e possivel; usa-se asset adulterado apos o vertical (ambos falhariam).
        # Falha isolada real: exportar horizontal com motion (indisponivel) falha
        # somente naquele destino.
        motion_plan = {'schemaVersion': 1, 'requestId': vreq['id'], 'effects': [
            {'sceneId': 'cena-prova', 'region': {'x': 0.1, 'y': 0.2, 'w': 0.5, 'h': 0.2},
             'color': '#FFD700', 'thickness': 6, 'startMs': 400, 'endMs': 2000},
        ]}
        status, job = self.request('POST', '/api/export', {
            'workId': wid, 'kind': 'video', 'request': vreq,
            'profile': 'youtube-video-horizontal', 'motionPlan': motion_plan,
            'outputDir': paths['motionDeliveryDir'],
        })
        result = self.wait_export(job['jobId'])
        self.assertEqual(result['status'], 'failed', result)
        self.assertIn('MOTION_LOCAL_UNSUPPORTED_GEOMETRY', json.dumps(result))
        sha_after = read_json(os.path.join(STUDIO_ROOT, vertical_manifest))['artifacts']['video']['sha256']
        self.assertEqual(sha_before, sha_after)


class CarouselPortraitTest(MultiFormatTestBase):
    @classmethod
    def setUpClass(cls):
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError('REQUIRE_RENDER=1 mas FFmpeg/FFprobe ausentes')
            raise unittest.SkipTest('FFmpeg indisponivel')
        super().setUpClass()

    def test_quadrado_e_retrato_destinos_separados(self):
        self.create_project()
        wid = 't-mf-carousel'
        self.create_work(wid)
        self.save_creative(wid, carousel_profile='instagram-feed-image-portrait')
        status, applied = self.request('POST', '/api/works/planning/apply', {'workId': wid, 'applyCarousel': True})
        self.assertEqual(status, 200, applied)
        creq = applied['workData']['carouselRequest']
        self.assertEqual(creq['profile'], 'instagram-feed-image-portrait')
        paths = applied['workData']['work']['paths']
        status, job = self.request('POST', '/api/export', {
            'workId': wid, 'kind': 'carousel', 'request': creq, 'outputDir': paths['carouselDeliveryDir'],
        })
        result = self.wait_export(job['jobId'])
        self.assertEqual(result['status'], 'completed', result)
        manifest = read_json(os.path.join(STUDIO_ROOT, paths['carouselDeliveryDir'], 'carousel-manifest.json'))
        self.assertEqual(manifest['geometry'], {'width': 1080, 'height': 1350})
        self.assertEqual([c['file'] for c in manifest['cards']], ['01-capa.jpg', '02-conteudo.jpg', '03-fechamento.jpg'])
        for card in manifest['cards']:
            probe = self.ffprobe(card['path'])
            v = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            self.assertEqual((v['width'], v['height']), (1080, 1350))
            self.assertEqual(card['sha256'], hashlib.sha256(open(os.path.join(STUDIO_ROOT, card['path']), 'rb').read()).hexdigest())
        zip_path = os.path.join(STUDIO_ROOT, manifest['zip']['path'])
        with zipfile.ZipFile(zip_path) as zf:
            self.assertEqual(zf.namelist(), ['01-capa.jpg', '02-conteudo.jpg', '03-fechamento.jpg'])
            self.assertIsNone(zf.testzip())
            for card in manifest['cards']:
                self.assertEqual(hashlib.sha256(zf.read(card['file'])).hexdigest(), card['sha256'])

        # Mesmo pedido em 1:1, destino separado.
        square_dir = os.path.join(self.dir, 'square')
        creq_square = {**creq, 'profile': 'instagram-feed-image-square'}
        status, job = self.request('POST', '/api/export', {
            'workId': wid, 'kind': 'carousel', 'request': creq_square, 'outputDir': square_dir,
        })
        result = self.wait_export(job['jobId'])
        self.assertEqual(result['status'], 'completed', result)
        manifest_sq = read_json(os.path.join(STUDIO_ROOT, square_dir, 'carousel-manifest.json'))
        self.assertEqual(manifest_sq['geometry'], {'width': 1080, 'height': 1080})
        # O conjunto 4:5 permanece intacto no destino original.
        manifest_again = read_json(os.path.join(STUDIO_ROOT, paths['carouselDeliveryDir'], 'carousel-manifest.json'))
        self.assertEqual(manifest_again['geometry'], {'width': 1080, 'height': 1350})

    def test_overflow_indica_card_e_preserva_conjunto(self):
        self.create_project()
        wid = 't-mf-overflow'
        self.create_work(wid)
        long_body = 'palavraextremamentelonga ' * 40
        creative = json.loads(json.dumps(CREATIVE))
        creative['carouselCards'][1]['body'] = long_body
        self.save_creative(wid, creative=creative, carousel_profile='instagram-feed-image-portrait')
        status, applied = self.request('POST', '/api/works/planning/apply', {'workId': wid, 'applyCarousel': True})
        creq = applied['workData']['carouselRequest']
        paths = applied['workData']['work']['paths']
        status, prev = self.request('POST', '/api/preview', {'request': creq, 'kind': 'carousel'})
        self.assertEqual(status, 200)
        self.assertIn('conteudo', prev['result']['overflowCards'])
        # Exporta conjunto valido primeiro (sem o texto longo).
        good = json.loads(json.dumps(creq))
        good['cards'][1]['body'] = 'Texto de apoio do card'
        status, job = self.request('POST', '/api/export', {'workId': wid, 'kind': 'carousel', 'request': good, 'outputDir': paths['carouselDeliveryDir']})
        self.assertEqual(self.wait_export(job['jobId'])['status'], 'completed')
        manifest_before = read_json(os.path.join(STUDIO_ROOT, paths['carouselDeliveryDir'], 'carousel-manifest.json'))
        status, job = self.request('POST', '/api/export', {'workId': wid, 'kind': 'carousel', 'request': creq, 'outputDir': paths['carouselDeliveryDir']})
        result = self.wait_export(job['jobId'])
        self.assertEqual(result['status'], 'failed')
        self.assertIn('CAROUSEL_TEXT_OVERFLOW', json.dumps(result))
        manifest_after = read_json(os.path.join(STUDIO_ROOT, paths['carouselDeliveryDir'], 'carousel-manifest.json'))
        self.assertEqual(manifest_after['cards'], manifest_before['cards'])

    def test_midia_fora_de_proporcao_preservada_com_bandas(self):
        self.create_project()
        ffmpeg = shutil.which('ffmpeg')
        tall = os.path.join(self.dir, 'tall.png')
        with open(tall, 'wb') as handle:
            handle.write(png_bytes(1080, 1920, seed='tall'))
        staging = os.path.join(self.dir, 'staging')
        os.makedirs(staging, exist_ok=True)
        rgb = produce_carousel._media_rgb(ffmpeg, tall, 1080, 1350, staging, 'capa')
        self.assertEqual(len(rgb), 1080 * 1350 * 3)
        corner = tuple(rgb[0:3])
        center = tuple(rgb[(675 * 1080 + 540) * 3:(675 * 1080 + 540) * 3 + 3])
        self.assertEqual(corner, (16, 20, 26), 'banda de preenchimento esperada no topo')
        self.assertNotEqual(center, corner, 'midia central preservada')


class MotionVerticalOnlyTest(MultiFormatTestBase):
    def test_motion_horizontal_rejeitado_vertical_ok(self):
        self.create_project()
        wid = 't-mf-motion'
        self.create_work(wid)
        self.save_creative(wid, recommended=['instagram-reels-video', 'youtube-video-horizontal'])
        status, applied = self.request('POST', '/api/works/planning/apply', {'workId': wid, 'applyVideo': True})
        vreq = applied['workData']['videoRequest']
        motion_plan = {'schemaVersion': 1, 'requestId': vreq['id'], 'effects': [
            {'sceneId': 'cena-prova', 'region': {'x': 0.1, 'y': 0.2, 'w': 0.5, 'h': 0.2},
             'color': '#FFD700', 'thickness': 6, 'startMs': 400, 'endMs': 2000},
        ]}
        status, data = self.request('POST', '/api/preview', {'request': vreq, 'motionPlan': motion_plan})
        self.assertEqual(status, 200)
        profiles = {p['profileId']: p for p in data['result']['profiles']}
        self.assertEqual(profiles['youtube-video-horizontal']['status'], 'failed')
        self.assertEqual(profiles['youtube-video-horizontal']['failureCode'], 'MOTION_LOCAL_UNSUPPORTED_GEOMETRY')
        self.assertEqual(profiles['instagram-reels-video']['status'], 'compiled')
        self.assertTrue(profiles['instagram-reels-video'].get('motion'))


class ImageRequestGeometryTest(MultiFormatTestBase):
    def test_geometria_por_perfil_e_mudanca_de_destino(self):
        self.create_project()
        wid = 't-mf-imgreq'
        self.create_work(wid)
        self.save_creative(wid)
        status, imp = self.request('POST', '/api/works/media/import', {
            'workId': wid, 'dataBase64': base64.b64encode(png_bytes(1080, 1920)).decode(),
            'fileName': 'abertura.png', 'origin': 'imported-manual', 'assetId': 'abertura',
        })
        self.assertEqual(status, 200, imp)
        status, sel = self.request('POST', '/api/works/media/select', {
            'workId': wid, 'assetId': 'abertura', 'versionId': imp['versionId'],
            'targetKind': 'video_scene', 'targetId': 'cena-abertura',
        })
        self.assertEqual(status, 200, sel)
        status, req = self.request('POST', '/api/works/media/request/create', {
            'workId': wid, 'targetKind': 'video_scene', 'targetId': 'cena-abertura',
            'profileId': 'youtube-video-horizontal',
        })
        self.assertEqual(status, 200, req)
        entry = req['overview']['mediaLibrary']['requests'][-1]
        self.assertEqual(entry['request']['aspectRatio'], '16:9')
        self.assertEqual(entry['request']['geometry'], {'width': 1920, 'height': 1080})
        framing = entry['framing']
        self.assertEqual((framing['mediaWidth'], framing['mediaHeight']), (1080, 1920))
        self.assertEqual(framing['bands'], 'verticais (pillarbox)')
        status, gen = self.request('POST', '/api/works/media/generate', {
            'workId': wid, 'requestId': req['requestId'], 'provider': 'simulator', 'confirm': True,
        })
        self.assertEqual(status, 200, gen)
        status, upd = self.request('POST', '/api/works/media/request/update', {
            'workId': wid, 'requestId': req['requestId'], 'profileId': 'instagram-reels-video',
        })
        self.assertEqual(status, 200, upd)
        entry2 = next(r for r in upd['overview']['mediaLibrary']['requests'] if r['request']['id'] == req['requestId'])
        self.assertEqual(entry2['request']['geometry'], {'width': 1080, 'height': 1920})
        self.assertTrue(all(c['stale'] for c in entry2['candidates']))
        self.assertEqual(entry2['framing']['bands'], 'nenhuma (proporcao identica)')

    def test_carrossel_4_5_no_pedido(self):
        self.create_project()
        wid = 't-mf-imgreq-c'
        self.create_work(wid)
        self.save_creative(wid, carousel_profile='instagram-feed-image-portrait')
        status, req = self.request('POST', '/api/works/media/request/create', {
            'workId': wid, 'targetKind': 'carousel_card', 'targetId': 'capa',
        })
        self.assertEqual(status, 200, req)
        entry = req['overview']['mediaLibrary']['requests'][-1]
        self.assertEqual(entry['request']['profileId'], 'instagram-feed-image-portrait')
        self.assertEqual(entry['request']['aspectRatio'], '4:5')
        self.assertEqual(entry['request']['geometry'], {'width': 1080, 'height': 1350})


class ReviewAndZipMultiFormatTest(MultiFormatTestBase):
    @classmethod
    def setUpClass(cls):
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError('REQUIRE_RENDER=1 mas FFmpeg/FFprobe ausentes')
            raise unittest.SkipTest('FFmpeg indisponivel')
        super().setUpClass()

    def test_zip_multiformato_e_revisao_localizada_por_canal(self):
        self.create_project()
        wid = 't-mf-zip'
        self.create_work(wid)
        self.save_creative(wid, carousel_profile='instagram-feed-image-portrait',
                           recommended=['instagram-reels-video', 'youtube-video-horizontal', 'instagram-feed-image-portrait'])
        status, applied = self.request('POST', '/api/works/planning/apply', {
            'workId': wid, 'applyVideo': True, 'applyCarousel': True,
        })
        self.assertEqual(status, 200, applied)
        opened = applied['workData']
        paths = opened['work']['paths']
        status, job = self.request('POST', '/api/export', {
            'workId': wid, 'kind': 'video', 'request': opened['videoRequest'], 'outputDir': paths['videoDeliveryDir'],
        })
        self.assertEqual(self.wait_export(job['jobId'])['status'], 'completed')
        status, job = self.request('POST', '/api/export', {
            'workId': wid, 'kind': 'carousel', 'request': opened['carouselRequest'], 'outputDir': paths['carouselDeliveryDir'],
        })
        self.assertEqual(self.wait_export(job['jobId'])['status'], 'completed')

        channels = {}
        for pid in ('instagram-reels-video', 'youtube-video-horizontal', 'instagram-feed-image-portrait'):
            channels[pid] = {
                'profileId': pid, 'title': f'Titulo {pid}', 'postText': f'Texto de publicacao {pid}',
                'cta': 'Link na bio', 'destinationUrl': 'https://marcasalao.com.br', 'hashtags': '#teste',
            }
        status, ed = self.request('POST', '/api/works/editorial/save', {'workId': wid, 'channels': channels})
        self.assertEqual(status, 200, ed)
        for ch in ed['channels']:
            self.request('POST', '/api/works/review/decide', {
                'workId': wid, 'targetType': 'channel', 'profileId': ch['profileId'],
                'expectedCopySha256': ch['copySha256'], 'decision': 'approved_for_local_delivery',
            })
        status, rev = self.request('GET', '/api/works/review?id=' + wid)
        pieces = {p['pieceKey']: p for p in rev['pieces']}
        for key in ('video:instagram-reels-video', 'video:youtube-video-horizontal', 'carousel:instagram-feed-image-portrait'):
            self.assertEqual(pieces[key]['status'], 'pending_review', key)
            self.request('POST', '/api/works/review/decide', {
                'workId': wid, 'targetType': 'piece', 'modality': pieces[key]['modality'],
                'profileId': pieces[key]['profileId'], 'decision': 'approved_for_local_delivery',
                'expectedVersionId': pieces[key]['deliveryVersionId'],
            })
        horiz_sha = pieces['video:youtube-video-horizontal']['metrics']['videoSha256']
        vert_sha = pieces['video:instagram-reels-video']['metrics']['videoSha256']

        # Texto-only do horizontal: so aquele canal pede nova revisao.
        status, ed2 = self.request('POST', '/api/works/editorial/save', {
            'workId': wid, 'channels': {'youtube-video-horizontal': {
                **channels['youtube-video-horizontal'], 'postText': 'Texto revisado apenas do YouTube horizontal',
            }},
        })
        self.assertEqual(status, 200, ed2)
        status, rev2 = self.request('GET', '/api/works/review?id=' + wid)
        ch_map = {c['profileId']: c for c in rev2['channels']}
        self.assertEqual(ch_map['youtube-video-horizontal']['status'], 'copy_outdated')
        self.assertEqual(ch_map['instagram-reels-video']['status'], 'approved')
        pieces2 = {p['pieceKey']: p for p in rev2['pieces']}
        self.assertEqual(pieces2['video:youtube-video-horizontal']['metrics']['videoSha256'], horiz_sha)
        self.assertEqual(pieces2['video:instagram-reels-video']['metrics']['videoSha256'], vert_sha)
        self.assertEqual(pieces2['video:youtube-video-horizontal']['status'], 'approved')

        # Reaprova o canal alterado e gera o ZIP multiformato.
        ch_new = next(c for c in ed2['channels'] if c['profileId'] == 'youtube-video-horizontal')
        self.request('POST', '/api/works/review/decide', {
            'workId': wid, 'targetType': 'channel', 'profileId': 'youtube-video-horizontal',
            'expectedCopySha256': ch_new['copySha256'], 'decision': 'approved_for_local_delivery',
        })
        selection = [{'modality': p['modality'], 'profileId': p['profileId']} for p in rev2['pieces'] if p['status'] == 'approved']
        status, pkg = self.request('POST', '/api/works/package', {
            'workId': wid, 'pieces': selection,
            'channels': ['instagram-reels-video', 'youtube-video-horizontal', 'instagram-feed-image-portrait'],
        })
        self.assertEqual(status, 200, pkg)
        self.assertTrue(pkg['packageDelivery']['available'])
        zip_abs = os.path.join(STUDIO_ROOT, paths['packageDeliveryDir'], 'delivery-package.zip')
        with zipfile.ZipFile(zip_abs) as zf:
            names = zf.namelist()
            self.assertIsNone(zf.testzip())
            for expected in ('video/instagram-reels-video/primary-output.mp4',
                             'video/youtube-video-horizontal/primary-output.mp4',
                             'carousel/instagram-feed-image-portrait/01-capa.jpg',
                             'textos-por-canal/youtube-video-horizontal/publicacao.txt'):
                self.assertIn(expected, names)
            pkg_manifest = json.loads(zf.read('package-manifest.json'))
            # Confere hashes do manifesto contra os bytes do ZIP.
            for f in pkg_manifest.get('files') or []:
                arc = f.get('archivePath')
                if arc in names and f.get('sha256'):
                    self.assertEqual(hashlib.sha256(zf.read(arc)).hexdigest(), f['sha256'], arc)

        # Reinicio preserva destinos, revisoes e ZIP.
        self.restart_server()
        status, reopened = self.request('GET', '/api/works/open?id=' + wid)
        self.assertEqual(status, 200)
        self.assertTrue(reopened['packageDelivery']['available'])
        status, rev3 = self.request('GET', '/api/works/review?id=' + wid)
        keys = {p['pieceKey'] for p in rev3['pieces']}
        self.assertIn('video:youtube-video-horizontal', keys)
        self.assertIn('carousel:instagram-feed-image-portrait', keys)


class OtherBrandTest(MultiFormatTestBase):
    @classmethod
    def setUpClass(cls):
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError('REQUIRE_RENDER=1 mas FFmpeg/FFprobe ausentes')
            raise unittest.SkipTest('FFmpeg indisponivel')
        super().setUpClass()

    def test_allowlist_ausente_bloqueia_e_projeto_ficticio_habilita(self):
        status, data = self.request('GET', '/api/profiles?project=platform/examples/projects/multitrack-hub-social.project.json')
        mth = {p['id']: p for p in data['listing']['profiles']}
        self.assertEqual(mth['instagram-feed-image-portrait']['availability'], 'blocked')
        proj = self.create_project('t-mf-mth', allowed=[
            'instagram-reels-video', 'instagram-feed-image-square', 'instagram-feed-image-portrait',
        ], base='multitrack-hub-social')
        wid = 't-mf-mth-work'
        self.create_work(wid, project_rel=proj)
        self.save_creative(wid, carousel_profile='instagram-feed-image-portrait')
        status, applied = self.request('POST', '/api/works/planning/apply', {'workId': wid, 'applyCarousel': True})
        self.assertEqual(status, 200, applied)
        creq = applied['workData']['carouselRequest']
        self.assertEqual(creq['profile'], 'instagram-feed-image-portrait')
        out = os.path.join(self.dir, 'mth-carousel')
        status, job = self.request('POST', '/api/export', {'workId': wid, 'kind': 'carousel', 'request': creq, 'outputDir': out})
        result = self.wait_export(job['jobId'])
        self.assertEqual(result['status'], 'completed', result)
        manifest = read_json(os.path.join(STUDIO_ROOT, out, 'carousel-manifest.json'))
        self.assertEqual(manifest['geometry'], {'width': 1080, 'height': 1350})
        # Isolamento: nenhum arquivo do trabalho Marca Salao aparece aqui.
        self.assertNotIn('t-mf-zip', json.dumps(manifest))


if __name__ == '__main__':
    unittest.main()