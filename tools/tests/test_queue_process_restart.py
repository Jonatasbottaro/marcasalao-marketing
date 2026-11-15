"""Prova de processo da fila: encerra e reinicia um Studio real com itens em andamento.

Cobre retomada de pendentes, protecao contra promocao atrasada (cerca revogada)
e reconciliacao apos promocao com o mesmo attemptId, criando uma unica versao
na Revisao. Usa sincronizacao deterministica por polling do SQLite/manifestos e
dados ficticios gerados sob a raiz.
"""

import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import uuid

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
TOOLS = os.path.join(ROOT, 'tools')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import build_video
import render_local

REQUIRE_RENDER = os.environ.get('REQUIRE_RENDER') == '1'


def _tools_available():
    try:
        build_video.get_ffmpeg()
        build_video.get_ffprobe()
        return True
    except build_video.DeliveryError:
        return False


def _free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _http_json(url, method='GET', body=None, origin=None):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json'
        if origin:
            headers['Origin'] = origin
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _create_color_video(path, color, duration_s=2.5, width=1280, height=720, fps=30):
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


def _pid_alive(pid):
    if not pid:
        return False
    if os.name == 'nt':
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return bool(ok) and code.value == 259
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def _kill_tree(pid):
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'],
                       capture_output=True, text=True, timeout=30)
    else:
        import signal
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except OSError:
            pass


class TestQueueProcessRestart(unittest.TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp(prefix='t_queue_restart_', dir=os.path.join(ROOT, '.workspace', 'tmp'))
        self.db_path = os.path.join(self.tmp_root, 'queue.sqlite')
        self.work_id = f'tqr-{os.getpid()}-{uuid.uuid4().hex[:6]}'
        self.project_abs = None
        self.server = None
        self.port = None

    def tearDown(self):
        self._stop_server(kill_tree=True)
        shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', self.work_id), ignore_errors=True)
        if self.project_abs and os.path.exists(self.project_abs):
            try:
                os.remove(self.project_abs)
            except OSError:
                pass
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    # ---- infraestrutura ----
    def _start_server(self):
        self.port = _free_port()
        env = dict(os.environ)
        env['STUDIO_QUEUE_DB_PATH'] = self.db_path
        kwargs = {}
        if os.name != 'nt':
            kwargs['start_new_session'] = True
        self.server = subprocess.Popen(
            [sys.executable, os.path.join(TOOLS, 'video_studio.py'), '--port', str(self.port)],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs,
        )
        self.base = f'http://127.0.0.1:{self.port}'
        deadline = time.monotonic() + 60.0
        while time.monotonic() < deadline:
            try:
                _http_json(f'{self.base}/api/readiness')
                return
            except OSError:
                if self.server.poll() is not None:
                    raise RuntimeError('servidor morreu no startup')
                time.sleep(0.2)
        raise TimeoutError('servidor nao ficou pronto')

    def _stop_server(self, kill_tree=False):
        if self.server is None:
            return
        if self.server.poll() is None:
            if kill_tree:
                _kill_tree(self.server.pid)
            else:
                self.server.kill()
            try:
                self.server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                pass
        self.server = None

    def _post(self, path, body):
        return _http_json(f'{self.base}{path}', 'POST', body, origin=self.base)

    def _db(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _wait_item_status(self, item_id, statuses, timeout=240.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            conn = self._db()
            try:
                row = conn.execute('SELECT status, error_code, error_message, last_attempt_id FROM queue_items WHERE item_id=?',
                                   (item_id,)).fetchone()
            finally:
                conn.close()
            if row and row['status'] in statuses:
                return dict(row)
            time.sleep(0.25)
        raise TimeoutError(f'item {item_id} nao alcancou {statuses}')

    def _wait_attempt_pid(self, item_id, timeout=60.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            conn = self._db()
            try:
                row = conn.execute('''
                    SELECT a.attempt_id, a.pid, a.staging_dir, a.fence_path
                    FROM queue_attempts a JOIN queue_items i ON i.last_attempt_id = a.attempt_id
                    WHERE i.item_id=? AND i.status='running'
                ''', (item_id,)).fetchone()
            finally:
                conn.close()
            if row and row['pid'] and _pid_alive(row['pid']):
                return dict(row)
            time.sleep(0.1)
        raise TimeoutError(f'tentativa do item {item_id} nao iniciou processo')

    def _seed_work(self):
        proj_res = self._post('/api/projects/create', {
            'schemaVersion': 1,
            'id': f'proj-{self.work_id}',
            'name': 'Projeto restart',
            'locale': 'pt-BR',
            'timezone': 'America/Sao_Paulo',
            'brandTheme': 'marca-salao',
            'assetRoot': f'.workspace/studio/works/{self.work_id}/media',
            'contentPolicies': {
                'requireApprovedBriefing': True,
                'requireApprovedScript': True,
                'prohibitPersonalData': True,
                'requireFunctionalEvidence': True,
            },
            'outputProfiles': [
                'instagram-reels-video',
                'instagram-feed-image-portrait',
            ],
        })
        self.project_abs = os.path.join(ROOT, proj_res['path'].replace('/', os.sep))
        created = self._post('/api/works/create', {
            'id': self.work_id, 'name': 'Restart prova', 'project': proj_res['path'], 'template': 'marca-salao',
        })
        clip_rel = f".workspace/studio/works/{self.work_id}/media/clip.mp4"
        _create_color_video(os.path.join(ROOT, clip_rel.replace('/', os.sep)), 'blue', duration_s=2.5)
        vreq = created['videoRequest']
        vreq['media'] = list(vreq.get('media') or []) + [
            {'id': 'clip-1', 'type': 'video', 'path': clip_rel, 'origin': 'synthetic-demo', 'license': 'owned-synthetic'}
        ]
        vreq['scenes'][0]['mediaId'] = 'clip-1'
        vreq['scenes'][0]['sourceStartMs'] = 200
        vreq['scenes'][0]['durationMs'] = 1200
        vreq['profiles'] = ['instagram-reels-video']
        creq = created['carouselRequest']
        creq['profile'] = 'instagram-feed-image-portrait'
        self._post('/api/works/save', {'workId': self.work_id, 'videoRequest': vreq, 'carouselRequest': creq})

    # ---- cenarios ----
    def test_01_kill_midrender_preserves_delivery_and_resumes_pending(self):
        if not REQUIRE_RENDER and not _tools_available():
            self.skipTest('FFmpeg/FFprobe indisponivel')
        self._start_server()
        self._seed_work()

        # Entrega valida de referencia (baseline)
        b0 = self._post('/api/queue/enqueue', {'items': [
            {'workId': self.work_id, 'modality': 'video', 'profileId': 'instagram-reels-video'},
        ]})
        it0 = b0['batch']['items'][0]['itemId']
        self._wait_item_status(it0, ('completed',))
        baseline = _http_json(f"{self.base}/api/delivery?dir=.workspace/studio/works/{self.work_id}/deliveries/video")
        baseline_entry = next(p for p in baseline['index']['profiles'] if p['profileId'] == 'instagram-reels-video')
        baseline_manifest = baseline_entry['lastValidDelivery']['deliveryManifest']

        # Novo lote: video em andamento + carrossel pendente; derruba a arvore durante o render
        b1 = self._post('/api/queue/enqueue', {'items': [
            {'workId': self.work_id, 'modality': 'video', 'profileId': 'instagram-reels-video'},
            {'workId': self.work_id, 'modality': 'carousel', 'profileId': 'instagram-feed-image-portrait'},
        ]})
        vid_id = b1['batch']['items'][0]['itemId']
        car_id = b1['batch']['items'][1]['itemId']
        self._wait_attempt_pid(vid_id)
        self._stop_server(kill_tree=True)

        # Reinicio: video interrompido (sem promocao comprovada), carrossel retoma e conclui
        self._start_server()
        vid_row = self._wait_item_status(vid_id, ('interrupted', 'failed'))
        self.assertEqual(vid_row['status'], 'interrupted')
        self._wait_item_status(car_id, ('completed',))

        after = _http_json(f"{self.base}/api/delivery?dir=.workspace/studio/works/{self.work_id}/deliveries/video")
        after_entry = next(p for p in after['index']['profiles'] if p['profileId'] == 'instagram-reels-video')
        self.assertEqual(after_entry['lastValidDelivery']['deliveryManifest'], baseline_manifest,
                         'entrega valida anterior nao foi preservada')

    def test_02_orphan_promotion_reconciles_single_review_version(self):
        if not REQUIRE_RENDER and not _tools_available():
            self.skipTest('FFmpeg/FFprobe indisponivel')
        self._start_server()
        self._seed_work()
        b = self._post('/api/queue/enqueue', {'items': [
            {'workId': self.work_id, 'modality': 'video', 'profileId': 'instagram-reels-video'},
        ]})
        item_id = b['batch']['items'][0]['itemId']
        attempt = self._wait_attempt_pid(item_id)
        attempt_id = attempt['attempt_id']
        producer_pid = int(attempt['pid'])

        # Mata apenas o servidor; o produtor orfao continua e promove com a cerca ainda valida
        self._stop_server(kill_tree=False)

        manifest_abs = os.path.join(
            ROOT, '.workspace', 'studio', 'works', self.work_id,
            'deliveries', 'video', 'instagram-reels-video', 'delivery-manifest.json',
        )
        deadline = time.monotonic() + 240.0
        promoted = False
        while time.monotonic() < deadline:
            if os.path.isfile(render_local.fs_path(manifest_abs)):
                try:
                    with open(render_local.fs_path(manifest_abs), 'r', encoding='utf-8') as f:
                        man = json.load(f)
                    if man.get('attemptId') == attempt_id:
                        promoted = True
                        break
                except (OSError, ValueError):
                    pass
            time.sleep(0.25)
        self.assertTrue(promoted, 'produtor orfao nao promoveu a tempo')
        deadline = time.monotonic() + 60.0
        while time.monotonic() < deadline and _pid_alive(producer_pid):
            time.sleep(0.2)
        self.assertFalse(_pid_alive(producer_pid), 'produtor orfao nao encerrou')

        # Reinicio: reconciliacao pelo attemptId prova a promocao e conclui o item
        self._start_server()
        row = self._wait_item_status(item_id, ('completed',))
        self.assertEqual(row['last_attempt_id'], attempt_id)

        rev = _http_json(f'{self.base}/api/works/review?id={self.work_id}')
        piece = next(p for p in rev['pieces'] if p['pieceKey'] == 'video:instagram-reels-video')
        self.assertEqual(piece['versionsCount'], 1)

        # Reconciliar de novo a mesma tentativa nao cria outra versao
        conn = self._db()
        try:
            item_row = conn.execute('SELECT * FROM queue_items WHERE item_id=?', (item_id,)).fetchone()
        finally:
            conn.close()
        import studio_queue
        import video_studio
        st = video_studio.Studio(ROOT, 0, auto_start_queue=False)
        try:
            q = studio_queue.StudioQueue(st, auto_start=False, db_path=self.db_path)
            q._record_review_for_item(item_row, attempt_id, {
                'status': 'completed',
                'profiles': [{'profileId': 'instagram-reels-video', 'status': 'completed'}],
            })
        finally:
            st.close()
        rev2 = _http_json(f'{self.base}/api/works/review?id={self.work_id}')
        piece2 = next(p for p in rev2['pieces'] if p['pieceKey'] == 'video:instagram-reels-video')
        self.assertEqual(piece2['versionsCount'], 1)


if __name__ == '__main__':
    unittest.main()