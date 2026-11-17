"""Testes do diagnostico de pre-voo (POST /api/queue/preflight e tools/studio_preflight.py)."""

import contextlib
import http.server
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
TOOLS = os.path.join(ROOT, 'tools')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import build_video
import render_local
import studio_preflight
import studio_queue
import video_studio


REQUIRE_RENDER = os.environ.get('REQUIRE_RENDER') == '1'


def _tools_available():
    try:
        build_video.get_ffmpeg()
        build_video.get_ffprobe()
        return True
    except build_video.DeliveryError:
        return False


def _create_color_video(path, color, duration_s=2.0, width=1280, height=720, fps=30):
    ffmpeg = build_video.get_ffmpeg()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cmd = [
        ffmpeg, '-y', '-f', 'lavfi',
        '-i', f'color=c={color}:s={width}x{height}:r={fps}:d={duration_s}',
        '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-an', path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if res.returncode != 0:
        raise RuntimeError(f'ffmpeg color video failed: {res.stderr}')


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class TestStudioPreflight(unittest.TestCase):
    def setUp(self):
        os.makedirs(os.path.join(ROOT, '.workspace', 'tmp'), exist_ok=True)
        self.tmp_root = tempfile.mkdtemp(prefix='t_studio_preflight_', dir=os.path.join(ROOT, '.workspace', 'tmp'))
        self.work_ids = []
        self.project_files = []
        self.servers = []

    def tearDown(self):
        for httpd, st in self.servers:
            try:
                httpd.shutdown()
                httpd.server_close()
            except Exception:
                pass
            try:
                st.close()
            except Exception:
                pass
        for wid in self.work_ids:
            shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', wid), ignore_errors=True)
        for pfile in self.project_files:
            if os.path.exists(pfile):
                try:
                    os.remove(pfile)
                except OSError:
                    pass
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def _start_server(self):
        port = _free_port()
        httpd, studio = video_studio.make_server(ROOT, port, auto_start_queue=False)
        studio.queue = studio_queue.StudioQueue(
            studio, auto_start=False, db_path=os.path.join(self.tmp_root, 'queue.sqlite')
        )
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        self.servers.append((httpd, studio))
        return port, studio

    def _seed_work(self, studio, work_id, template='marca-salao'):
        self.work_ids.append(work_id)
        shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', work_id), ignore_errors=True)
        proj_res = studio.create_project({
            'schemaVersion': 1,
            'id': f'tp-{work_id}',
            'name': f'Projeto {work_id}',
            'locale': 'pt-BR',
            'timezone': 'America/Sao_Paulo',
            'brandTheme': 'marca-salao' if template == 'marca-salao' else 'multitrack-hub',
            'assetRoot': f'.workspace/studio/works/{work_id}/media',
            'contentPolicies': {
                'requireApprovedBriefing': True,
                'requireApprovedScript': True,
                'prohibitPersonalData': True,
                'requireFunctionalEvidence': True,
            },
            'outputProfiles': [
                'instagram-reels-video',
                'youtube-video-horizontal',
                'instagram-feed-image-square',
                'instagram-feed-image-portrait',
            ],
        })
        project = proj_res['path']
        self.project_files.append(studio.confine(project))
        opened = studio.create_work({
            'id': work_id,
            'name': f'Trabalho {work_id}',
            'project': project,
            'template': template,
        })
        work = opened['work']
        clip_rel = f"{work['paths']['mediaDir']}/clip.mp4"
        clip_abs = studio.confine(clip_rel)
        if _tools_available():
            _create_color_video(clip_abs, 'blue', duration_s=2.5)
        else:
            os.makedirs(os.path.dirname(clip_abs), exist_ok=True)
            with open(clip_abs, 'wb') as f:
                f.write(b'fake-mp4-' + work_id.encode('utf-8'))

        vreq = json.loads(json.dumps(opened['videoRequest']))
        vreq['media'] = list(vreq.get('media') or []) + [
            {'id': 'clip-1', 'type': 'video', 'path': clip_rel, 'origin': 'synthetic-demo', 'license': 'owned-synthetic'}
        ]
        vreq['scenes'][0]['mediaId'] = 'clip-1'
        vreq['scenes'][0]['sourceStartMs'] = 300
        vreq['scenes'][0]['durationMs'] = 1200
        vreq['profiles'] = ['instagram-reels-video', 'youtube-video-horizontal']

        creq = json.loads(json.dumps(opened['carouselRequest']))
        creq['profile'] = 'instagram-feed-image-portrait'

        mplan = json.loads(json.dumps(opened['motionPlan']))
        for eff in mplan.get('effects') or []:
            if eff.get('sceneId') == vreq['scenes'][0]['id']:
                eff['startMs'] = 0
                eff['endMs'] = min(int(eff.get('endMs') or 1000), 1000)

        studio.save_work({
            'workId': work_id,
            'videoRequest': vreq,
            'carouselRequest': creq,
            'motionPlan': mplan,
        })
        return studio.open_work(work_id)

    def _run_cli(self, argv):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = studio_preflight.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_01_ready_video_carousel_and_cli_modes(self):
        if not REQUIRE_RENDER and not _tools_available():
            self.skipTest('FFmpeg/FFprobe indisponivel')
        port, studio = self._start_server()
        w1 = f'tp-ready-{os.getpid()}'
        self._seed_work(studio, w1)

        # CLI humano + JSON para video pronto
        code_h, out_h, err_h = self._run_cli([
            '--port', str(port), '--work-id', w1, '--modality', 'video', '--profile', 'instagram-reels-video',
        ])
        self.assertEqual(code_h, 0, err_h or out_h)
        self.assertIn('PRONTO:', out_h)

        code_j, out_j, err_j = self._run_cli([
            '--port', str(port), '--work-id', w1, '--modality', 'video', '--profile', 'instagram-reels-video', '--json',
        ])
        self.assertEqual(code_j, 0, err_j)
        parsed = json.loads(out_j)
        self.assertEqual(parsed['schemaVersion'], 1)
        self.assertTrue(parsed['ready'])
        self.assertEqual(parsed['items'][0]['status'], 'ready')

        # Carrossel com cards apenas textuais (sem mediaId obrigatorio) continua pronto
        opened = studio.open_work(w1)
        creq = json.loads(json.dumps(opened['carouselRequest']))
        for card in creq['cards']:
            card.pop('mediaId', None)
        studio.save_work({'workId': w1, 'carouselRequest': creq})
        code_c, out_c, err_c = self._run_cli([
            '--port', str(port), '--work-id', w1, '--modality', 'carousel', '--profile', 'instagram-feed-image-portrait', '--json',
        ])
        self.assertEqual(code_c, 0, err_c)
        self.assertEqual(json.loads(out_c)['items'][0]['status'], 'ready')

    def test_02_isolated_modalities_allowlist_and_motion_incompatibility(self):
        if not REQUIRE_RENDER and not _tools_available():
            self.skipTest('FFmpeg/FFprobe indisponivel')
        port, studio = self._start_server()
        w1 = f'tp-iso-{os.getpid()}'
        opened = self._seed_work(studio, w1)

        # Introduz overflow no carrossel mantendo video valido
        creq = json.loads(json.dumps(opened['carouselRequest']))
        creq['cards'][0]['body'] = ('Texto muito grande para provocar overflow no card. ' * 25).strip()
        studio.save_work({'workId': w1, 'carouselRequest': creq})

        res = studio.queue.preflight([
            {'workId': w1, 'modality': 'video', 'profileId': 'instagram-reels-video'},
            {'workId': w1, 'modality': 'carousel', 'profileId': 'instagram-feed-image-portrait'},
            {'workId': w1, 'modality': 'motion', 'profileId': 'youtube-video-horizontal'},
            {'workId': w1, 'modality': 'video', 'profileId': 'facebook-reels-video'},
        ])
        self.assertFalse(res['ready'])
        items = res['items']
        self.assertEqual(items[0]['status'], 'ready')
        self.assertEqual(items[1]['status'], 'blocked')
        self.assertEqual(items[1]['blockers'][0]['code'], 'CAROUSEL_TEXT_OVERFLOW')
        self.assertEqual(items[2]['status'], 'blocked')
        self.assertEqual(items[2]['blockers'][0]['code'], 'MOTION_LOCAL_UNSUPPORTED_GEOMETRY')
        self.assertEqual(items[3]['status'], 'blocked')
        self.assertEqual(items[3]['blockers'][0]['code'], 'PROFILE_NOT_ALLOWED')

        # CLI humano e JSON no item bloqueado saem com codigo 1
        code_b, out_b, _ = self._run_cli([
            '--port', str(port), '--work-id', w1, '--modality', 'motion', '--profile', 'youtube-video-horizontal',
        ])
        self.assertEqual(code_b, 1)
        self.assertIn('BLOQUEADO:', out_b)
        self.assertIn('MOTION_LOCAL_UNSUPPORTED_GEOMETRY', out_b)

    def test_03_missing_media_hash_mismatch_and_nonexistent_or_empty_work(self):
        if not REQUIRE_RENDER and not _tools_available():
            self.skipTest('FFmpeg/FFprobe indisponivel')
        port, studio = self._start_server()
        w1 = f'tp-media-{os.getpid()}'
        opened = self._seed_work(studio, w1)

        # 1) Divergencia de hash esperado
        vreq = json.loads(json.dumps(opened['videoRequest']))
        for m in vreq['media']:
            if m.get('id') == 'clip-1':
                m['sha256'] = '0' * 64
        studio.save_work({'workId': w1, 'videoRequest': vreq})
        res_hash = studio.queue.preflight([
            {'workId': w1, 'modality': 'video', 'profileId': 'instagram-reels-video'},
        ])
        self.assertEqual(res_hash['items'][0]['status'], 'blocked')
        self.assertTrue(any(b['code'] == 'MEDIA_HASH_MISMATCH' for b in res_hash['items'][0]['blockers']))

        # 2) Midia ausente em disco
        for m in vreq['media']:
            if m.get('id') == 'clip-1':
                m.pop('sha256', None)
                clip_abs = studio.confine(m['path'])
                if os.path.exists(clip_abs):
                    os.remove(clip_abs)
        studio.save_work({'workId': w1, 'videoRequest': vreq})
        res_miss = studio.queue.preflight([
            {'workId': w1, 'modality': 'video', 'profileId': 'instagram-reels-video'},
        ])
        self.assertEqual(res_miss['items'][0]['status'], 'blocked')
        self.assertTrue(any(b['code'] == 'MEDIA_FILE_MISSING' for b in res_miss['items'][0]['blockers']))

        # 3) Trabalho inexistente
        code_nf, out_nf, _ = self._run_cli([
            '--port', str(port), '--work-id', 'trabalho-inexistente-xyz', '--modality', 'video', '--profile', 'instagram-reels-video', '--json',
        ])
        self.assertEqual(code_nf, 1)
        self.assertEqual(json.loads(out_nf)['items'][0]['blockers'][0]['code'], 'WORK_NOT_FOUND')

        # 4) Rascunho vazio (sem cenas)
        vreq_empty = json.loads(json.dumps(vreq))
        vreq_empty['scenes'] = []
        studio.save_work({'workId': w1, 'videoRequest': vreq_empty})
        res_empty = studio.queue.preflight([
            {'workId': w1, 'modality': 'video', 'profileId': 'instagram-reels-video'},
        ])
        self.assertEqual(res_empty['items'][0]['blockers'][0]['code'], 'DRAFT_VIDEO_MISSING')

    def test_04_missing_prereqs_pending_checks_and_no_side_effects(self):
        port, studio = self._start_server()
        w1 = f'tp-nop-{os.getpid()}'
        opened = self._seed_work(studio, w1)
        work_before = json.loads(json.dumps(opened['work']))

        # Simula ambiente sem Node e sem FFprobe
        orig_readiness = studio.check_readiness
        studio.check_readiness = lambda: {
            'ready': False,
            'summary': 'Ambiente incompleto',
            'items': [
                {'id': 'python', 'label': 'Python', 'ok': True, 'detail': 'ok', 'instruction': None},
                {'id': 'node', 'label': 'Node.js', 'ok': False, 'detail': 'node ausente', 'instruction': 'Instale Node.js >= 22.'},
                {'id': 'platformBuild', 'label': 'Build', 'ok': True, 'detail': 'ok', 'instruction': None},
                {'id': 'ffmpeg', 'label': 'FFmpeg', 'ok': True, 'detail': 'ok', 'instruction': None},
                {'id': 'ffprobe', 'label': 'FFprobe', 'ok': False, 'detail': 'ffprobe ausente', 'instruction': 'Instale FFprobe.'},
            ],
        }
        try:
            res1 = studio.queue.preflight([
                {'workId': w1, 'modality': 'video', 'profileId': 'instagram-reels-video'},
            ])
            res2 = studio.queue.preflight([
                {'workId': w1, 'modality': 'video', 'profileId': 'instagram-reels-video'},
            ])
        finally:
            studio.check_readiness = orig_readiness

        item = res1['items'][0]
        self.assertEqual(item['status'], 'blocked')
        self.assertTrue(any(b['code'] == 'ENV_MISSING_NODE' for b in item['blockers']))
        self.assertTrue(any(p['code'] == 'PREVIEW_PENDING_PREREQUISITES' for p in item['pendingChecks']))
        self.assertTrue(any(p['code'] == 'MEDIA_PROBE_PENDING_FFPROBE' for p in item['pendingChecks']))
        self.assertEqual(res1, res2)

        # Trabalho, fila e revisao intactos
        opened_after = studio.open_work(w1)
        self.assertEqual(opened_after['work']['updatedAt'], work_before['updatedAt'])
        self.assertEqual(studio.queue.list_queue()['batches'], [])

    def test_05_infrastructure_errors_exit_2(self):
        # 1) Studio desligado
        dead_port = _free_port()
        code_dead, out_dead, err_dead = self._run_cli([
            '--port', str(dead_port), '--work-id', 'x', '--modality', 'video', '--profile', 'instagram-reels-video',
        ])
        self.assertEqual(code_dead, 2)
        self.assertEqual(out_dead, '')
        self.assertIn('video_studio.py', err_dead)

        # 2) Host nao loopback rejeitado
        code_host, _, err_host = self._run_cli([
            '--port', '8765', '--host', '192.168.1.10', '--work-id', 'x', '--modality', 'video', '--profile', 'instagram-reels-video',
        ])
        self.assertEqual(code_host, 2)
        self.assertIn('loopback', err_host)

        # 3) Resposta HTTP invalida (nao JSON)
        class BadHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'not-json')

            def log_message(self, *args):
                pass

        bad_port = _free_port()
        srv = http.server.HTTPServer(('127.0.0.1', bad_port), BadHandler)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            code_bad, out_bad, err_bad = self._run_cli([
                '--port', str(bad_port), '--work-id', 'x', '--modality', 'video', '--profile', 'instagram-reels-video', '--json',
            ])
            self.assertEqual(code_bad, 2)
            self.assertEqual(out_bad, '')
            self.assertIn('JSON ilegivel', err_bad)
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == '__main__':
    unittest.main()
