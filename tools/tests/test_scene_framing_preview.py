"""Testes de enquadramento por cena/destino e previa da montagem no Video Studio."""

import contextlib
import hashlib
import http.client
import io
import json
import os
import shutil
import subprocess
import sys
import time
import unittest
import urllib.parse
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import make_proof_assets
import produce_video
import render_local
import studio_review
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
TMP_BASE = os.path.join(STUDIO_ROOT, '.workspace', 'tmp', 't_sfp')


def run_produce(argv):
    buf = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        code = produce_video.main(argv)
    try:
        payload = json.loads(buf.getvalue())
    except ValueError:
        payload = None
    return code, payload, err.getvalue()


def ffprobe_json(path):
    res = subprocess.run(
        [build_video.get_ffprobe(), '-v', 'error', '-show_streams', '-show_format',
         '-of', 'json', render_local.fs_path(path)],
        capture_output=True, text=True, timeout=60,
    )
    if res.returncode != 0:
        raise AssertionError(f'ffprobe falhou em {path}: {res.stderr[-240:]}')
    return json.loads(res.stdout)


def extract_pixel(video_path, t_seconds, fx, fy, out_png):
    cmd = [
        build_video.get_ffmpeg(), '-y', '-ss', f'{t_seconds:.3f}',
        '-i', render_local.fs_path(video_path), '-frames:v', '1',
        render_local.fs_path(out_png),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if res.returncode != 0:
        raise AssertionError(f'extracao falhou em t={t_seconds}: {res.stderr[-240:]}')
    w, h, px = decode_png(out_png)
    x = min(w - 1, max(0, int(w * fx)))
    y = min(h - 1, max(0, int(h * fy)))
    return tuple(px[(y * w + x) * 3:(y * w + x) * 3 + 3])


def classify_rgb(rgb):
    r, g, b = rgb
    if r > 150 and g < 110 and b < 110:
        return 'RED'
    if b > 150 and r < 110 and g < 130:
        return 'BLUE'
    if g > 130 and r < 120 and b < 120:
        return 'GREEN'
    if r > 160 and g > 160 and b < 100:
        return 'YELLOW'
    return f'OTHER({r},{g},{b})'


def verify_split_framing_pixels(video_path, profile_id, tmp_png, expect_reels='BLUE'):
    """Detector automatizado: falha se o enquadramento for aplicado ao perfil errado."""
    p_left = classify_rgb(extract_pixel(video_path, 0.75, 0.18, 0.50, tmp_png))
    p_right = classify_rgb(extract_pixel(video_path, 0.75, 0.82, 0.50, tmp_png))
    if profile_id == 'instagram-reels-video':
        if p_left != expect_reels or p_right != expect_reels:
            raise AssertionError(
                f'enquadramento errado para {profile_id}: esquerda={p_left}, direita={p_right}, esperado={expect_reels}'
            )
    elif profile_id == 'youtube-video-horizontal':
        if p_left != 'RED' or p_right != 'BLUE':
            raise AssertionError(
                f'enquadramento errado para {profile_id}: esquerda={p_left} (esperado RED), direita={p_right} (esperado BLUE)'
            )
    else:
        raise AssertionError(f'perfil nao previsto no detector: {profile_id}')
    return {'left': p_left, 'right': p_right}


def write_split_horizontal_recording(path, duration_s=10.0, fps=30, sar=None, rotate=None):
    """Gera gravacao MP4 1920x1080 com inicio neutro (0-3.5s) e tela dividida (esquerda RED, direita BLUE) de 3.5s a 10s."""
    parent = os.path.dirname(path)
    os.makedirs(render_local.fs_path(parent), exist_ok=True)
    # t=[0, 3.5): fundo verde escuro (#28A03C); t=[3.5, duration_s]: metade esquerda RED (#DC2828), direita BLUE (#2850DC)
    vf = (
        "split=3[bg][lsrc][rsrc];"
        "[lsrc]crop=960:1080:0:0,drawbox=x=0:y=0:w=960:h=1080:color=0xDC2828:t=fill[left];"
        "[rsrc]crop=960:1080:960:0,drawbox=x=0:y=0:w=960:h=1080:color=0x2850DC:t=fill[right];"
        "[left][right]hstack=inputs=2[splitlr];"
        "[bg]drawbox=x=0:y=0:w=1920:h=1080:color=0x28A03C:t=fill[intro];"
        "[intro][splitlr]overlay=0:0:enable='gte(t,3.5)'"
    )
    if sar:
        vf += f",setsar={sar}"
    else:
        vf += ",setsar=1"
    cmd = [
        build_video.get_ffmpeg(), '-y',
        '-f', 'lavfi', '-i', f'color=c=0x28A03C:s=1920x1080:r={fps}:d={duration_s:.2f}',
        '-an', '-vf', vf,
        '-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p',
        '-g', '90', '-keyint_min', '90', '-sc_threshold', '0', '-r', str(fps),
    ]
    if rotate is None:
        cmd.append(render_local.fs_path(path))
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            raise AssertionError(f'falha ao gerar gravacao horizontal sintetica: {res.stderr[-300:]}')
    else:
        tmp_path = path + '.norot.mp4'
        cmd.append(render_local.fs_path(tmp_path))
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            raise AssertionError(f'falha ao gerar gravacao horizontal sintetica: {res.stderr[-300:]}')
        try:
            remux = subprocess.run(
                [build_video.get_ffmpeg(), '-y', '-display_rotation:v:0', str(rotate),
                 '-i', render_local.fs_path(tmp_path), '-c', 'copy', render_local.fs_path(path)],
                capture_output=True, text=True, timeout=60,
            )
            if remux.returncode != 0:
                raise AssertionError(f'falha ao aplicar metadata de rotacao: {remux.stderr[-300:]}')
        finally:
            if os.path.exists(render_local.fs_path(tmp_path)):
                os.remove(render_local.fs_path(tmp_path))


class FramingGeometryAndContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAS_BRIDGE:
            raise unittest.SkipTest('ponte TypeScript indisponivel')
        render_local.ensure_video_tools(STUDIO_ROOT)

    def setUp(self):
        self.dir = os.path.join(TMP_BASE, self._testMethodName[:14])
        shutil.rmtree(render_local.fs_path(self.dir, force=True), ignore_errors=True)
        os.makedirs(render_local.fs_path(self.dir), exist_ok=True)
        self.media_rel = f'.workspace/tmp/t_sfp/{self._testMethodName[:14]}/rec.mp4'
        self.image_rel = f'.workspace/tmp/t_sfp/{self._testMethodName[:14]}/img.png'
        self.req_path = os.path.join(self.dir, 'req.video-request.json')

    def tearDown(self):
        shutil.rmtree(render_local.fs_path(self.dir, force=True), ignore_errors=True)

    def _base_req(self, profiles=None):
        return {
            'schemaVersion': 1,
            'id': 'fr-contract',
            'project': PROJECT_MS,
            'title': 'Teste contrato enquadramento',
            'profiles': profiles or ['instagram-reels-video', 'youtube-video-horizontal'],
            'media': [
                {'id': 'rec', 'path': self.media_rel, 'type': 'video', 'origin': 'synthetic', 'license': 'owned'},
                {'id': 'img', 'path': self.image_rel, 'type': 'image', 'origin': 'synthetic', 'license': 'owned'},
            ],
            'scenes': [
                {'id': 's1', 'durationMs': 2500, 'sourceStartMs': 4000, 'mediaId': 'rec',
                 'caption': 'Cena gravacao', 'narration': 'Narracao 1.'},
                {'id': 's2', 'durationMs': 2000, 'mediaId': 'img',
                 'caption': 'Cena imagem', 'narration': 'Narracao 2.'},
            ],
        }

    def _plan(self, req):
        with open(self.req_path, 'w', encoding='utf-8', newline='\n') as h:
            json.dump(req, h, ensure_ascii=False, indent=2)
        return run_produce(['--input', self.req_path, '--root', STUDIO_ROOT, '--plan-only', '--json'])

    def test_contrato_legado_perfis_invalidos_valores_invalidos_e_restauracao(self):
        # 1. Pedido legado sem framingByProfile -> valido e compilation usa fit
        req = self._base_req()
        code, payload, err = self._plan(req)
        self.assertEqual(code, 0, err)
        for p in payload['profiles']:
            self.assertEqual(p['beats'][0]['framing'], {
                'mode': 'fit', 'centerX': 0.5, 'centerY': 0.5, 'zoomPercent': 100,
            })

        # 2. Perfil de imagem ou desconhecido -> erro de contrato (codigo 3)
        for bad_prof in ('instagram-feed-image-square', 'perfil-inexistente'):
            bad = self._base_req()
            bad['scenes'][0]['framingByProfile'] = {
                bad_prof: {'centerX': 0.5, 'centerY': 0.5, 'zoomPercent': 120},
            }
            code, _, err = self._plan(bad)
            self.assertEqual(code, 3, f'{bad_prof}: {err}')

        # 3. Valores invalidos (center fora [0,1], zoom fora [100,300] ou nao inteiro) -> codigo 3
        for bad_val in (
            {'centerX': -0.1, 'centerY': 0.5, 'zoomPercent': 100},
            {'centerX': 0.5, 'centerY': 1.05, 'zoomPercent': 100},
            {'centerX': 0.5, 'centerY': 0.5, 'zoomPercent': 99},
            {'centerX': 0.5, 'centerY': 0.5, 'zoomPercent': 301},
            {'centerX': 0.5, 'centerY': 0.5, 'zoomPercent': 150.5},
        ):
            bad = self._base_req()
            bad['scenes'][0]['framingByProfile'] = {'instagram-reels-video': bad_val}
            code, _, err = self._plan(bad)
            self.assertEqual(code, 3, f'{bad_val}: {err}')

        # 4. Perfil de video do catalogo pode sair de profiles[] mantendo framingByProfile e voltar depois
        req_unselected = self._base_req(profiles=['youtube-video-horizontal'])
        saved_framing = {'centerX': 0.82, 'centerY': 0.45, 'zoomPercent': 160}
        req_unselected['scenes'][0]['framingByProfile'] = {'instagram-reels-video': saved_framing}
        code, payload, err = self._plan(req_unselected)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(payload['profiles']), 1)
        self.assertEqual(payload['profiles'][0]['profileId'], 'youtube-video-horizontal')
        self.assertEqual(payload['profiles'][0]['beats'][0]['framing'], {
            'mode': 'fit', 'centerX': 0.5, 'centerY': 0.5, 'zoomPercent': 100,
        })

        # Ao restaurar instagram-reels-video em profiles[], o ajuste guardado volta ativo
        req_unselected['profiles'] = ['youtube-video-horizontal', 'instagram-reels-video']
        code2, payload2, err2 = self._plan(req_unselected)
        self.assertEqual(code2, 0, err2)
        reels_p = next(p for p in payload2['profiles'] if p['profileId'] == 'instagram-reels-video')
        self.assertEqual(reels_p['beats'][0]['framing'], {'mode': 'fill', **saved_framing})
        # Sem leitura de midia no --plan-only
        self.assertFalse(os.path.exists(os.path.join(STUDIO_ROOT, self.media_rel)))

    def test_bordas_do_quadro_e_metadados_incompativeis_com_fallback_fit(self):
        # Bordas nos cantos (0,0) e (1,1) em zoom 100% e 300% ficam integralmente dentro da fonte e pares
        src_meta = {'width': 1920, 'height': 1080, 'sar': '1:1', 'rotation': 0}
        for cx, cy in ((0.0, 0.0), (1.0, 1.0), (0.0, 1.0), (1.0, 0.0)):
            for zoom in (100, 180, 300):
                res = render_local.resolve_scene_framing(
                    src_meta, 1080, 1920,
                    framing={'centerX': cx, 'centerY': cy, 'zoomPercent': zoom},
                    beat_id='borda',
                )
                self.assertEqual(res['mode'], 'fill')
                self.assertGreaterEqual(res['cropX'], 0)
                self.assertGreaterEqual(res['cropY'], 0)
                self.assertLessEqual(res['cropX'] + res['cropWidth'], 1920)
                self.assertLessEqual(res['cropY'] + res['cropHeight'], 1080)
                self.assertEqual(res['cropWidth'] % 2, 0)
                self.assertEqual(res['cropHeight'] % 2, 0)

        # Rotacao != 0 e SAR != 1:1 bloqueiam 'fill' com FRAMING_MEDIA_METADATA_UNSUPPORTED, mas aceitam 'fit' (Ajustar)
        for bad_meta in (
            {'width': 1920, 'height': 1080, 'sar': '1:1', 'rotation': 90},
            {'width': 1920, 'height': 1080, 'sar': '4:3', 'rotation': 0},
        ):
            with self.assertRaises(build_video.DeliveryError) as ctx:
                render_local.resolve_scene_framing(
                    bad_meta, 1080, 1920,
                    framing={'centerX': 0.5, 'centerY': 0.5, 'zoomPercent': 120},
                    beat_id='meta-ruins',
                )
            self.assertIn('FRAMING_MEDIA_METADATA_UNSUPPORTED', str(ctx.exception))
            fit_res = render_local.resolve_scene_framing(bad_meta, 1080, 1920, framing=None, beat_id='meta-ruins')
            self.assertEqual(fit_res['mode'], 'fit')


class SceneFramingAndPreviewStudioTest(StudioTestBase):
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
        self.work_id = f'sfp-{self._testMethodName[:10].lower().replace("_", "-")}'
        self.proj_id = f'p-{self.work_id}'
        self._cleanup_work()
        super().setUp()

    def tearDown(self):
        self._cleanup_work()
        super().tearDown()

    def _cleanup_work(self):
        shutil.rmtree(render_local.fs_path(os.path.join(STUDIO_ROOT, '.workspace', 'studio', 'works', self.work_id), force=True), ignore_errors=True)
        shutil.rmtree(render_local.fs_path(os.path.join(STUDIO_ROOT, '.workspace', 'studio', 'projects', self.proj_id), force=True), ignore_errors=True)
        proj_file = os.path.join(STUDIO_ROOT, '.workspace', 'studio', 'projects', f'{self.proj_id}.project.json')
        if os.path.exists(proj_file):
            os.remove(proj_file)

    def _create_work_with_media(self):
        manifest = {
            'schemaVersion': 1, 'id': self.proj_id, 'name': 'Projeto Enquadramento',
            'locale': 'pt-BR', 'timezone': 'America/Sao_Paulo', 'brandTheme': self.proj_id,
            'assetRoot': f'.workspace/studio/projects/{self.proj_id}/assets',
            'contentPolicies': {
                'requireApprovedBriefing': True, 'requireApprovedScript': True,
                'prohibitPersonalData': True, 'requireFunctionalEvidence': True,
            },
            'outputProfiles': [
                'instagram-reels-video', 'youtube-video-horizontal',
                'youtube-shorts', 'instagram-feed-image-square',
            ],
        }
        st, p = self.request('POST', '/api/projects/create', {'project': manifest, 'overwrite': True})
        self.assertEqual(st, 200, p)
        proj_rel = p['project']['path']
        st, wk = self.request('POST', '/api/works/create', {
            'id': self.work_id, 'name': 'Trabalho Enquadramento', 'project': proj_rel,
            'template': 'blank', 'overwrite': True,
        })
        self.assertEqual(st, 200, wk)
        rec_rel = f'.workspace/studio/works/{self.work_id}/media/rec-split.mp4'
        img_rel = f'.workspace/studio/works/{self.work_id}/media/card-static.png'
        write_split_horizontal_recording(os.path.join(STUDIO_ROOT, rec_rel), duration_s=10.0)
        make_proof_assets.write_scene_png(os.path.join(STUDIO_ROOT, img_rel), self.proj_id, 'card-static', 2)
        return wk, rec_rel, img_rel

    def _wait_preview_job(self, job_id, work_id, profile_id):
        for _ in range(240):
            st, d = self.request('GET', '/api/video/preview-status?' + urllib.parse.urlencode({
                'job': job_id, 'work': work_id, 'profile': profile_id,
            }))
            self.assertEqual(st, 200, d)
            if d['job']['status'] != 'running':
                return d
            time.sleep(0.25)
        raise AssertionError('Timeout esperando previa da montagem')

    def _wait_export(self, payload, expect='completed'):
        st, started = self.request('POST', '/api/export', payload)
        self.assertEqual(st, 200, started)
        jid = started['jobId']
        for _ in range(360):
            st, d = self.request('GET', '/api/export/status?job=' + jid)
            self.assertEqual(st, 200, d)
            if d['status'] == expect:
                return d
            if d['status'] in ('failed', 'interrupted') and expect == 'completed':
                raise AssertionError(f'Export falhou: {d}')
            if d['status'] == 'completed' and expect == 'failed':
                raise AssertionError(f'Export deveria falhar: {d}')
            time.sleep(0.4)
        raise AssertionError('Timeout esperando exportacao')

    def test_frame_info_metadados_persistencia_cache_previa_e_edicao_concorrente(self):
        wk, rec_rel, img_rel = self._create_work_with_media()
        vreq = wk['videoRequest']
        vreq['id'] = 'work-fr'
        vreq['profiles'] = ['instagram-reels-video', 'youtube-video-horizontal']
        vreq['media'] = [
            {'id': 'rec', 'path': rec_rel, 'type': 'video', 'origin': 'synthetic', 'license': 'owned'},
            {'id': 'img', 'path': img_rel, 'type': 'image', 'origin': 'synthetic', 'license': 'owned'},
        ]
        vreq['scenes'] = [
            {'id': 'c1', 'durationMs': 2200, 'sourceStartMs': 3800, 'mediaId': 'rec',
             'caption': 'Lado direito no Reels', 'narration': 'Narracao 1.', 'title': 'FOCO DIREITA',
             'framingByProfile': {'instagram-reels-video': {'centerX': 0.82, 'centerY': 0.50, 'zoomPercent': 150}}},
            {'id': 'c2', 'durationMs': 1800, 'mediaId': 'img',
             'caption': 'Imagem fixa', 'narration': 'Narracao 2.'},
        ]
        st, _ = self.request('POST', '/api/works/save', {'workId': self.work_id, 'videoRequest': vreq})
        self.assertEqual(st, 200)

        # Persistencia ao reabrir apos reinicio + reordenacao mantendo corte e enquadramento
        self.restart_server()
        st, opened = self.request('GET', '/api/works/open?id=' + self.work_id)
        self.assertEqual(st, 200)
        self.assertEqual(opened['videoRequest']['scenes'][0]['framingByProfile']['instagram-reels-video'],
                         {'centerX': 0.82, 'centerY': 0.50, 'zoomPercent': 150})
        self.assertEqual(opened['videoRequest']['scenes'][0]['sourceStartMs'], 3800)

        # frame-info valida geometria e troca de midia com SAR/rotacao incompativel
        st, info = self.request('POST', '/api/video/frame-info', {
            'workId': self.work_id, 'profileId': 'instagram-reels-video',
            'mediaPath': rec_rel, 'beatId': 'c1',
            'framing': {'centerX': 0.82, 'centerY': 0.50, 'zoomPercent': 150},
        })
        self.assertEqual(st, 200, info)
        self.assertTrue(info['ok'])
        self.assertEqual(info['resolvedFraming']['cropWidth'] % 2, 0)
        self.assertGreater(info['resolvedFraming']['cropX'], 960)

        # Troca para gravacao com metadado de rotacao != 0 -> retorna motivo claro e aceita Ajustar
        rot_rel = f'.workspace/studio/works/{self.work_id}/media/rec-rot.mp4'
        write_split_horizontal_recording(os.path.join(STUDIO_ROOT, rot_rel), duration_s=5.0, rotate=90)
        st, bad_info = self.request('POST', '/api/video/frame-info', {
            'workId': self.work_id, 'profileId': 'instagram-reels-video',
            'mediaPath': rot_rel, 'beatId': 'c1',
            'framing': {'centerX': 0.5, 'centerY': 0.5, 'zoomPercent': 120},
        })
        self.assertEqual(st, 200)
        self.assertFalse(bad_info['ok'])
        self.assertEqual(bad_info['errorCode'], 'FRAMING_MEDIA_METADATA_UNSUPPORTED')
        self.assertEqual(bad_info['fallbackMode'], 'fit')

        # Edicao DURANTE geracao da previa marca previa concluida como desatualizada ("versao anterior")
        st, started1 = self.request('POST', '/api/video/preview-render', {
            'workId': self.work_id, 'profileId': 'instagram-reels-video', 'request': vreq,
        })
        self.assertEqual(st, 200, started1)
        edited_vreq = json.loads(json.dumps(vreq))
        edited_vreq['scenes'][0]['framingByProfile']['instagram-reels-video']['zoomPercent'] = 175
        self.request('POST', '/api/works/save', {'workId': self.work_id, 'videoRequest': edited_vreq})
        done1 = self._wait_preview_job(started1['jobId'], self.work_id, 'instagram-reels-video')
        self.assertEqual(done1['job']['status'], 'completed', done1)
        self.assertFalse(done1['lastReady']['matchesCurrentDraft'])
        self.assertEqual(done1['lastReady']['state'], 'outdated')

        # HTTP Range seeking no arquivo /preview-media
        url1 = done1['lastReady']['url']
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=60)
        conn.request('GET', url1, headers={'Host': self.host, 'Range': 'bytes=128-383'})
        r = conn.getresponse()
        part = r.read()
        conn.close()
        self.assertEqual(r.status, 206)
        self.assertEqual(len(part), 256)

        # Cache limitado: 5 geracoes adicionais mantem no maximo 4 MP4 sob .workspace/studio/works/<id>/previews/
        for z in (120, 140, 160, 190, 175):
            r_cur = json.loads(json.dumps(vreq))
            r_cur['scenes'][0]['framingByProfile']['instagram-reels-video']['zoomPercent'] = z
            self.request('POST', '/api/works/save', {'workId': self.work_id, 'videoRequest': r_cur})
            st, st_job = self.request('POST', '/api/video/preview-render', {
                'workId': self.work_id, 'profileId': 'instagram-reels-video', 'request': r_cur,
            })
            self.assertEqual(st, 200)
            res = self._wait_preview_job(st_job['jobId'], self.work_id, 'instagram-reels-video')
            self.assertEqual(res['job']['status'], 'completed')
            self.assertTrue(res['lastReady']['matchesCurrentDraft'])

        preview_dir = os.path.join(STUDIO_ROOT, '.workspace', 'studio', 'works', self.work_id, 'previews')
        mp4s = [n for n in os.listdir(preview_dir) if n.endswith('.mp4')]
        self.assertLessEqual(len(mp4s), 4)
        self.assertFalse(os.path.exists(os.path.join(STUDIO_ROOT, wk['work']['paths']['videoDeliveryDir'], 'index.json')))

    def test_fluxo_completo_revisao_localizada_reexport_falha_motion_carrossel_e_zip(self):
        wk, rec_rel, img_rel = self._create_work_with_media()
        paths = wk['work']['paths']
        vreq = wk['videoRequest']
        vreq['id'] = 'e2e-framing'
        vreq['profiles'] = ['instagram-reels-video', 'youtube-video-horizontal']
        vreq['media'] = [
            {'id': 'rec', 'path': rec_rel, 'type': 'video', 'origin': 'synthetic', 'license': 'owned'},
            {'id': 'img', 'path': img_rel, 'type': 'image', 'origin': 'synthetic', 'license': 'owned'},
        ]
        vreq['scenes'] = [
            {'id': 'c1', 'durationMs': 2200, 'sourceStartMs': 3800, 'mediaId': 'rec',
             'caption': 'Foco direita Reels', 'narration': 'Cena 1.', 'title': 'TITULO E2E',
             'framingByProfile': {'instagram-reels-video': {'centerX': 0.82, 'centerY': 0.50, 'zoomPercent': 150}}},
            {'id': 'c2', 'durationMs': 1800, 'mediaId': 'img',
             'caption': 'Cartela estatica', 'narration': 'Cena 2.'},
        ]
        mplan = {
            'schemaVersion': 1, 'requestId': 'e2e-framing',
            'effects': [{
                'sceneId': 'c2',
                'region': {'x': 0.15, 'y': 0.35, 'w': 0.70, 'h': 0.15},
                'color': '#FFD700', 'thickness': 6, 'startMs': 200, 'endMs': 1500,
            }],
        }
        creq = {
            'schemaVersion': 1, 'id': 'car-framing', 'project': wk['work']['project'],
            'profile': 'instagram-feed-image-square', 'title': 'Carrossel independente',
            'media': [{'id': 'cimg', 'path': img_rel, 'type': 'image', 'origin': 'synthetic', 'license': 'owned'}],
            'cards': [{'id': 'card1', 'mediaId': 'cimg', 'title': 'Card 1', 'body': 'Texto do card 1.'}],
        }
        self.request('POST', '/api/works/save', {
            'workId': self.work_id, 'videoRequest': vreq, 'carouselRequest': creq, 'motionPlan': mplan,
        })

        # Gera previa para Reels e YouTube antes da exportacao
        preview_files = {}
        for pid in ('instagram-reels-video', 'youtube-video-horizontal'):
            _, pjob = self.request('POST', '/api/video/preview-render', {
                'workId': self.work_id, 'profileId': pid, 'request': vreq,
                'motionPlan': mplan if pid == 'instagram-reels-video' else None,
            })
            pdone = self._wait_preview_job(pjob['jobId'], self.work_id, pid)
            self.assertEqual(pdone['job']['status'], 'completed', pdone)
            preview_files[pid] = os.path.join(
                STUDIO_ROOT, '.workspace', 'studio', 'works', self.work_id, 'previews', pdone['lastReady']['file']
            )

        # Exporta videos, motion 9:16 e carrossel
        self._wait_export({'workId': self.work_id, 'kind': 'video', 'request': vreq, 'outputDir': paths['videoDeliveryDir']})
        self._wait_export({'workId': self.work_id, 'kind': 'video', 'request': vreq, 'motionPlan': mplan,
                           'profile': 'instagram-reels-video', 'outputDir': paths['motionDeliveryDir']})
        self._wait_export({'workId': self.work_id, 'kind': 'carousel', 'request': creq,
                           'outputDir': paths['carouselDeliveryDir']})

        tmp_png = os.path.join(STUDIO_ROOT, '.workspace', 'tmp', 't_sfp', 'cmp.png')
        os.makedirs(os.path.dirname(tmp_png), exist_ok=True)
        final_files = {}
        for pid, (exp_w, exp_h) in (('instagram-reels-video', (1080, 1920)), ('youtube-video-horizontal', (1920, 1080))):
            dm = read_json(os.path.join(STUDIO_ROOT, paths['videoDeliveryDir'], pid, 'delivery-manifest.json'))
            mp4_abs = os.path.join(STUDIO_ROOT, dm['artifacts']['video']['path'])
            final_files[pid] = mp4_abs
            probe = ffprobe_json(mp4_abs)
            v = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            self.assertEqual((v['width'], v['height']), (exp_w, exp_h))
            self.assertEqual(v['r_frame_rate'], '30/1')
            self.assertEqual(len([s for s in probe['streams'] if s['codec_type'] == 'audio']), 0)
            # Compara pixels no mesmo instante entre previa e MP4 final
            verify_split_framing_pixels(preview_files[pid], pid, tmp_png, expect_reels='BLUE')
            verify_split_framing_pixels(mp4_abs, pid, tmp_png, expect_reels='BLUE')

        # Prova que o detector falha se tentar validar o arquivo do perfil errado
        with self.assertRaises(AssertionError):
            verify_split_framing_pixels(final_files['youtube-video-horizontal'], 'instagram-reels-video', tmp_png, expect_reels='BLUE')

        # Aprova todas as pecas e verifica paridade de ausente === Ajustar (fit)
        for mod, pid in (
            ('video', 'instagram-reels-video'),
            ('video', 'youtube-video-horizontal'),
            ('motion', 'instagram-reels-video'),
            ('carousel', 'instagram-feed-image-square'),
        ):
            st, dec = self.request('POST', '/api/works/review/decide', {
                'workId': self.work_id, 'targetType': 'piece', 'modality': mod,
                'profileId': pid, 'decision': 'approved_for_local_delivery', 'note': 'Aprovado inicial',
            })
            self.assertEqual(st, 200, dec)

        fp_absent, _ = studio_review.compute_draft_snapshot(
            self.studio, 'video', vreq, None, None, profile_id='youtube-video-horizontal'
        )
        vreq_explicit_empty = json.loads(json.dumps(vreq))
        vreq_explicit_empty['scenes'][0]['framingByProfile']['youtube-video-horizontal'] = None
        fp_fit, _ = studio_review.compute_draft_snapshot(
            self.studio, 'video', vreq_explicit_empty, None, None, profile_id='youtube-video-horizontal'
        )
        self.assertEqual(fp_absent, fp_fit)

        # Altera APENAS o enquadramento do Reels para a metade ESQUERDA (RED)
        def hashes_for(pid):
            dm = read_json(os.path.join(STUDIO_ROOT, paths['videoDeliveryDir'], pid, 'delivery-manifest.json'))
            return {k: dm['artifacts'][k]['sha256'] for k in ('video', 'srt', 'narration')}

        reels_before = hashes_for('instagram-reels-video')
        yt_before = hashes_for('youtube-video-horizontal')
        src_sha_before = render_local.sha256_file(os.path.join(STUDIO_ROOT, rec_rel))

        vreq['scenes'][0]['framingByProfile']['instagram-reels-video'] = {
            'centerX': 0.18, 'centerY': 0.50, 'zoomPercent': 150,
        }
        self.request('POST', '/api/works/save', {'workId': self.work_id, 'videoRequest': vreq})
        _, rev = self.request('GET', '/api/works/review?id=' + self.work_id)
        by_key = {p['pieceKey']: p for p in rev['pieces']}
        self.assertEqual(by_key['video:instagram-reels-video']['status'], 'draft_outdated')
        self.assertEqual(by_key['motion:instagram-reels-video']['status'], 'draft_outdated')
        self.assertEqual(by_key['video:youtube-video-horizontal']['status'], 'approved')
        self.assertEqual(by_key['carousel:instagram-feed-image-square']['status'], 'approved')

        # Reexporta APENAS o Reels e confirma mudança localizada de MP4 + preservacao dos demais hashes
        self._wait_export({
            'workId': self.work_id, 'kind': 'video', 'request': vreq,
            'profile': 'instagram-reels-video', 'outputDir': paths['videoDeliveryDir'],
        })
        reels_after = hashes_for('instagram-reels-video')
        self.assertNotEqual(reels_after['video'], reels_before['video'])
        self.assertEqual(reels_after['srt'], reels_before['srt'])
        self.assertEqual(reels_after['narration'], reels_before['narration'])
        self.assertEqual(hashes_for('youtube-video-horizontal'), yt_before)
        self.assertEqual(render_local.sha256_file(os.path.join(STUDIO_ROOT, rec_rel)), src_sha_before)
        # Pixels do Reels reexportado agora mostram metade esquerda RED!
        verify_split_framing_pixels(final_files['instagram-reels-video'], 'instagram-reels-video', tmp_png, expect_reels='RED')

        # Provoca falha controlada em nova tentativa de exportacao e prova preservacao da entrega anterior
        bad_req = json.loads(json.dumps(vreq))
        bad_req['scenes'][0]['durationMs'] = 9000  # 3800 + 9000 > 10000ms
        failed = self._wait_export({
            'workId': self.work_id, 'kind': 'video', 'request': bad_req,
            'profile': 'instagram-reels-video', 'outputDir': paths['videoDeliveryDir'],
        }, expect='failed')
        self.assertEqual(failed['status'], 'failed')
        self.assertEqual(hashes_for('instagram-reels-video'), reels_after)
        # Restaura rascunho valido no trabalho, reexporta motion 9:16 e aprova pecas atualizadas para ZIP
        self.request('POST', '/api/works/save', {'workId': self.work_id, 'videoRequest': vreq})
        self._wait_export({'workId': self.work_id, 'kind': 'video', 'request': vreq, 'motionPlan': mplan,
                           'profile': 'instagram-reels-video', 'outputDir': paths['motionDeliveryDir']})
        for mod in ('video', 'motion'):
            st_d, res_d = self.request('POST', '/api/works/review/decide', {
                'workId': self.work_id, 'targetType': 'piece', 'modality': mod,
                'profileId': 'instagram-reels-video', 'decision': 'approved_for_local_delivery',
            })
            self.assertEqual(st_d, 200, res_d)

        st_rev2, rev2 = self.request('GET', '/api/works/review?id=' + self.work_id)
        self.assertEqual(st_rev2, 200, rev2)
        selection = [
            {'modality': p['modality'], 'profileId': p['profileId'], 'expectedVersionId': p['deliveryVersionId']}
            for p in rev2['pieces'] if p['status'] == 'approved'
        ]
        self.assertEqual(len(selection), 4, rev2['pieces'])
        st, pkg_res = self.request('POST', '/api/works/package', {
            'workId': self.work_id, 'pieces': selection, 'channels': [],
        })
        self.assertEqual(st, 200, pkg_res)
        self.assertTrue(pkg_res['packageDelivery']['available'], pkg_res)
        zip_abs = os.path.join(STUDIO_ROOT, paths['packageDeliveryDir'], 'delivery-package.zip')
        with zipfile.ZipFile(render_local.fs_path(zip_abs), 'r') as zf:
            names = zf.namelist()
            self.assertFalse(any('previews/' in n for n in names))
            pkg_manifest = json.loads(zf.read('package-manifest.json').decode('utf-8'))
            reels_piece = next(p for p in pkg_manifest['pieces']
                               if p['modality'] == 'video' and p['profileId'] == 'instagram-reels-video')
            yt_piece = next(p for p in pkg_manifest['pieces']
                            if p['modality'] == 'video' and p['profileId'] == 'youtube-video-horizontal')
            self.assertEqual(reels_piece['framings'][0]['framing']['mode'], 'fill')
            self.assertAlmostEqual(reels_piece['framings'][0]['framing']['centerX'], 0.18, places=2)
            self.assertEqual(yt_piece['framings'][0]['framing']['mode'], 'fit')
            self.assertEqual(reels_piece['sourceCuts'][0]['sourceStartMs'], 3800)
            for piece in pkg_manifest['pieces']:
                for f in piece['files']:
                    digest = hashlib.sha256(zf.read(f['archivePath'])).hexdigest()
                    self.assertEqual(digest, f['sha256'], f['archivePath'])
