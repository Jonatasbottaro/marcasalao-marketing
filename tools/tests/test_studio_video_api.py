"""Testes da geracao de clipes por API (texto para video) no Video Studio.

Fornecedor simulado da Interactions API (POST /v1beta/interactions, GET
interactions/{id}, GET files/{id} e download), cofre simulado e credenciais
sinteticas. O simulador devolve MP4 H.264 COM audio (ffmpeg lavfi) para provar
a importacao silenciosa. Nenhuma credencial real e usada.
"""

import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
TOOLS = os.path.join(ROOT, 'tools')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import build_video
import render_local
import studio_connections
import studio_video_api
import video_studio

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


def _make_clip_with_audio(path, duration_s=2.0, width=320, height=240):
    ffmpeg = build_video.get_ffmpeg()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cmd = [
        ffmpeg, '-y',
        '-f', 'lavfi', '-i', f'color=c=0x28A03C:s={width}x{height}:r=15:d={duration_s}',
        '-f', 'lavfi', '-i', f'sine=frequency=440:duration={duration_s}',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if res.returncode != 0:
        raise RuntimeError(f'ffmpeg fixture failed: {res.stderr[-400:]}')


class _MockState:
    def __init__(self, video_bytes, port):
        self.video_bytes = video_bytes
        self.port = port
        self.mode = 'complete'
        self.expected_key = None
        self.posts = []
        self.gets = []
        self.file_gets = 0
        self.file_active_after = 1
        self.hold = False
        self.slow_s = 0.0
        self.interactions = {}
        self.files = {}
        self.counter = 0


class _MockInteractionsHandler(BaseHTTPRequestHandler):
    state = None

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, payload):
        data = json.dumps(payload).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_bytes(self, code, data, content_type):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _video_step(self, content):
        return {
            'id': None, 'status': 'completed', 'model': 'gemini-omni-1.2-flash',
            'object': 'interaction',
            'steps': [
                {'type': 'user_input', 'content': [{'type': 'text', 'text': 'prompt'}]},
                {'type': 'model_output', 'content': [content]},
            ],
            'usageMetadata': {'promptTokenCount': 12, 'candidatesTokenCount': 34, 'totalTokenCount': 46},
        }

    def do_GET(self):
        st = self.state
        parsed = urlparse(self.path)
        path = parsed.path
        st.gets.append({'path': self.path, 'key': self.headers.get('x-goog-api-key')})
        if path == '/v1beta/models':
            self._send(200, {'models': [
                {'name': 'models/gemini-omni-1.2-flash'},
                {'name': 'models/gemini-omni-1.1-flash'},
                {'name': 'models/gemini-3.1-flash-image'},
            ]})
            return
        if path.startswith('/v1beta/interactions/'):
            iid = path.rsplit('/', 1)[-1]
            final = st.interactions.get(iid)
            if final is None:
                self._send(404, {'error': {'message': 'interaction not found'}})
                return
            if st.hold:
                self._send(200, {'id': iid, 'status': 'in_progress', 'steps': []})
                return
            self._send(200, final)
            return
        if path.startswith('/v1beta/files/'):
            fid = path.rsplit('/', 1)[-1]
            if fid.endswith(':download'):
                fid = fid[:-len(':download')]
                self._send_bytes(200, st.video_bytes, 'video/mp4')
                return
            st.file_gets += 1
            state = 'ACTIVE' if st.file_gets >= st.file_active_after else 'PROCESSING'
            self._send(200, {'name': f'files/{fid}', 'state': state})
            return
        self._send(404, {'error': {'message': 'not found'}})

    def do_POST(self):
        st = self.state
        parsed = urlparse(self.path)
        n = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(n) or b'{}')
        key = self.headers.get('x-goog-api-key')
        st.posts.append({'path': parsed.path, 'key': key, 'body': body})
        if parsed.path != '/v1beta/interactions':
            self._send(404, {'error': {'message': 'not found'}})
            return
        if st.slow_s:
            time.sleep(st.slow_s)
        if st.expected_key is not None and key != st.expected_key:
            self._send(403, {'error': {'message': 'API key invalida'}})
            return
        if st.mode == 'refused':
            self._send(403, {'error': {'message': 'API key invalida'}})
            return
        if st.mode == 'limit':
            self._send(429, {'error': {'message': 'Resource exhausted'}})
            return
        if st.mode == 'uncertain':
            # envio aceito, resposta nunca chega: conexao encerrada sem resposta
            self.close_connection = True
            return
        st.counter += 1
        iid = f'v1_mock_{st.counter}'
        if st.mode == 'invalid':
            payload = self._video_step({'type': 'video', 'mime_type': 'video/mp4', 'data': '!!nao-e-base64!!'})
            payload['id'] = iid
            st.interactions[iid] = payload
            self._send(200, payload)
            return
        if st.mode == 'no_video':
            payload = {'id': iid, 'status': 'completed', 'steps': [
                {'type': 'model_output', 'content': [{'type': 'text', 'text': 'sem video'}]}]}
            st.interactions[iid] = payload
            self._send(200, payload)
            return
        if st.mode == 'uri':
            fid = f'file-{st.counter}'
            uri = f'http://127.0.0.1:{st.port}/v1beta/files/{fid}:download?alt=media'
            payload = self._video_step({'type': 'video', 'mime_type': 'video/mp4', 'uri': uri})
            payload['id'] = iid
            st.interactions[iid] = payload
            st.files[fid] = True
            self._send(200, payload)
            return
        if st.mode == 'inprogress':
            payload = self._video_step({'type': 'video', 'mime_type': 'video/mp4',
                                        'data': base64.b64encode(st.video_bytes).decode('ascii')})
            payload['id'] = iid
            st.interactions[iid] = payload
            self._send(200, {'id': iid, 'status': 'in_progress', 'steps': []})
            return
        payload = self._video_step({'type': 'video', 'mime_type': 'video/mp4',
                                    'data': base64.b64encode(st.video_bytes).decode('ascii')})
        payload['id'] = iid
        st.interactions[iid] = payload
        self._send(200, payload)


@unittest.skipUnless(REQUIRE_RENDER or _tools_available(), 'ffmpeg/ffprobe indisponiveis')
class TestStudioVideoApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_dir = tempfile.mkdtemp(prefix='t_vapi_fixture_', dir=os.path.join(ROOT, '.workspace', 'tmp'))
        cls.clip_path = os.path.join(cls.fixture_dir, 'clip-with-audio.mp4')
        _make_clip_with_audio(cls.clip_path)
        with open(cls.clip_path, 'rb') as handle:
            cls.clip_bytes = handle.read()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.fixture_dir, ignore_errors=True)

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='t_vapi_', dir=os.path.join(ROOT, '.workspace', 'tmp'))
        self.vault_path = os.path.join(self.tmp, 'vault.json')
        self._env_backup = {k: os.environ.get(k) for k in (
            'STUDIO_CREDENTIAL_BACKEND', 'STUDIO_CREDENTIAL_STORE_PATH', 'GEMINI_API_KEY', 'TEST_VIDEO_KEY')}
        os.environ['STUDIO_CREDENTIAL_BACKEND'] = 'simulated'
        os.environ['STUDIO_CREDENTIAL_STORE_PATH'] = self.vault_path
        os.environ.pop('GEMINI_API_KEY', None)
        os.environ.pop('TEST_VIDEO_KEY', None)
        self.studios = []
        self.work_ids = []
        self.project_files = []
        self.servers = []
        self.studio = self._make_studio()
        self.port = _free_port()
        self.state = _MockState(self.clip_bytes, self.port)
        self._serve(self.state)
        self.endpoint = f'http://127.0.0.1:{self.port}'

    def tearDown(self):
        for srv, thread in self.servers:
            srv.shutdown()
            srv.server_close()
        for st in self.studios:
            try:
                st.close()
            except Exception:
                pass
        for wid in self.work_ids:
            shutil.rmtree(render_local.fs_path(os.path.join(ROOT, '.workspace', 'studio', 'works', wid), force=True),
                          ignore_errors=True)
        for pf in self.project_files:
            if os.path.exists(pf):
                try:
                    os.remove(pf)
                except OSError:
                    pass
        conn_file = os.path.join(ROOT, '.workspace', 'studio', 'connections.json')
        if os.path.exists(conn_file):
            os.remove(conn_file)
        shutil.rmtree(os.path.join(ROOT, '.workspace', 'tmp', 'studio-video-api'), ignore_errors=True)
        for k, v in self._env_backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_studio(self):
        st = video_studio.Studio(ROOT, 0, auto_start_queue=False)
        self.studios.append(st)
        return st

    def _serve(self, state):
        handler = type('BoundMock', (_MockInteractionsHandler,), {'state': state})
        srv = ThreadingHTTPServer(('127.0.0.1', self.port), handler)
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        self.servers.append((srv, thread))

    def _make_work(self, suffix):
        wid = f'tvapi-{suffix}-{os.getpid()}'
        self.work_ids.append(wid)
        proj = self.studio.create_project({
            'schemaVersion': 1, 'id': f'tvapi-proj-{suffix}-{os.getpid()}', 'name': f'Projeto {suffix}',
            'locale': 'pt-BR', 'timezone': 'America/Sao_Paulo', 'brandTheme': 'marca-salao',
            'assetRoot': f'.workspace/studio/works/{wid}/media',
            'contentPolicies': {'requireApprovedBriefing': True, 'requireApprovedScript': True,
                                'prohibitPersonalData': True, 'requireFunctionalEvidence': True},
            'outputProfiles': ['instagram-reels-video', 'instagram-feed-image-square'],
        })
        self.project_files.append(self.studio.confine(proj['path']))
        self.studio.create_work({'id': wid, 'name': f'Trabalho {suffix}', 'project': proj['path'], 'template': 'blank'})
        return wid, proj['path']

    def _conn(self, cid, key=None, kind='vault'):
        body = {'id': cid, 'name': cid, 'provider': 'google-gemini', 'endpoint': self.endpoint,
                'model': 'gemini-3.1-flash-image', 'credential': {'kind': kind}}
        if kind == 'env':
            body['credential'] = {'kind': 'env', 'envVar': 'TEST_VIDEO_KEY'}
        if key is not None:
            body['credentialValue'] = key
        return self.studio.save_connection(body)['connection']

    def _select_video(self, project, conn_id, model=None):
        self.studio.select_connection({'project': project, 'capability': 'video',
                                       'connectionId': conn_id, 'model': model})

    def _create(self, wid, prompt='Clipe ficticio de teste para o Studio.', **params):
        body = {'workId': wid, 'prompt': prompt}
        body.update(params)
        return self.studio.create_video_request(body)

    def _submit(self, wid, rid, **extra):
        body = {'workId': wid, 'requestId': rid, 'confirm': True}
        body.update(extra)
        return self.studio.submit_video_request(body)

    def _wait_status(self, wid, rid, statuses, timeout=90.0, studio=None):
        st = studio or self.studio
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            data = st.get_video_requests(wid)
            entry = next(r for r in data['requests'] if r['id'] == rid)
            if entry['status'] in statuses:
                return entry
            time.sleep(0.25)
        raise TimeoutError(f'pedido {rid} nao alcancou {statuses}; estado atual: {entry["status"]}')

    def _import(self, wid, rid):
        return self.studio.import_video_request({'workId': wid, 'requestId': rid})

    # ------------------------------------------------------------------
    def test_01_two_projects_share_google_key_with_per_project_model(self):
        w1, p1 = self._make_work('a')
        w2, p2 = self._make_work('b')
        self._conn('google-unico', key='synthetic-shared-key-1')
        self._select_video(p1, 'google-unico')
        self._select_video(p2, 'google-unico', model='gemini-omni-1.1-flash')
        self.studio.select_connection({'project': p1, 'capability': 'image', 'connectionId': 'google-unico'})
        r1 = self._create(w1)['request']
        r2 = self._create(w2)['request']
        self.assertEqual(r1['model'], 'gemini-omni-1.2-flash')
        self.assertEqual(r2['model'], 'gemini-omni-1.1-flash')
        self._submit(w1, r1['id'])
        self._submit(w2, r2['id'])
        self._wait_status(w1, r1['id'], ('ready',))
        self._wait_status(w2, r2['id'], ('ready',))
        self.assertEqual(self.state.posts[-2]['body']['model'], 'gemini-omni-1.2-flash')
        self.assertEqual(self.state.posts[-1]['body']['model'], 'gemini-omni-1.1-flash')
        self.assertEqual(self.state.posts[-2]['key'], 'synthetic-shared-key-1')
        self.assertEqual(self.state.posts[-1]['key'], 'synthetic-shared-key-1')
        rf = self.state.posts[-1]['body']['response_format']
        self.assertEqual(rf['type'], 'video')
        self.assertEqual(rf['duration'], '10s')
        self.assertEqual(rf['aspect_ratio'], '16:9')
        self.assertEqual(rf['resolution'], '720p')
        # a mesma conexao atende imagem e video: mesma referencia de credencial,
        # modelos por capacidade (imagem heredado, video Omni Flash)
        resolved_img = studio_connections.resolve_for_project(self.studio, p1, 'image')
        resolved_vid = studio_connections.resolve_for_project(self.studio, p1, 'video')
        self.assertEqual(resolved_img['connectionId'], resolved_vid['connectionId'])
        self.assertEqual(resolved_img['secret'], resolved_vid['secret'])
        self.assertEqual(resolved_img['model'], 'gemini-3.1-flash-image')
        self.assertEqual(resolved_vid['model'], 'gemini-omni-1.2-flash')
        ov = self.studio.get_connections()
        video_calls = [c for c in ov['calls'] if c['capability'] == 'video']
        self.assertEqual(len(video_calls), 2)
        self.assertEqual(video_calls[0]['connectionId'], 'google-unico')
        self.assertEqual(video_calls[0]['usage']['totalTokens'], 46)
        self.assertNotIn('synthetic-shared-key-1', json.dumps(ov, ensure_ascii=False))

    def test_02_completion_import_silent_idempotent_and_provenance(self):
        w1, p1 = self._make_work('c')
        self._conn('google-c', key='synthetic-key-c')
        self._select_video(p1, 'google-c')
        created = self._create(w1, prompt='Uma cena continua de teste.', durationSeconds=5,
                               aspectRatio='9:16', resolution='1080p')
        rid = created['request']['id']
        conf = created['confirmation']
        self.assertEqual(conf['connectionId'], 'google-c')
        self.assertIn('55 dias', conf['notices']['retention'])
        self.assertIn('store=true', conf['notices']['retention'])
        self._submit(w1, rid)
        entry = self._wait_status(w1, rid, ('ready',))
        self.assertTrue(entry['remoteInteractionId'].startswith('v1_mock_'))
        self.assertEqual(entry['result']['bytes'], len(self.clip_bytes))
        imp = self._import(w1, rid)
        self.assertFalse(imp['deduplicated'])
        version = imp['version']
        self.assertEqual(version['kind'], 'video')
        self.assertEqual(version['origin'], 'generated-google-gemini-video')
        self.assertEqual(version['codec'], 'h264')
        prov = version['provenance']
        self.assertEqual(prov['provider'], 'google-gemini')
        self.assertEqual(prov['model'], 'gemini-omni-1.2-flash')
        self.assertEqual(prov['connectionId'], 'google-c')
        self.assertEqual(prov['params'], {'durationSeconds': 5, 'aspectRatio': '9:16', 'resolution': '1080p'})
        self.assertEqual(prov['videoRequestId'], rid)
        self.assertTrue(prov['audioRemoved'])
        self.assertEqual(prov['resultSha256'], version['sha256'])
        # produto final sem faixa de audio (FFprobe)
        abs_path = self.studio.confine(version['path'])
        info = render_local.probe_asset(os.path.dirname(abs_path), abs_path)
        self.assertFalse(any(s.get('codec_type') == 'audio' for s in info['streams']))
        self.assertTrue(any(s.get('codec_type') == 'video' and s.get('codec_name') == 'h264'
                            for s in info['streams']))
        # importacao repetida devolve a mesma versao, sem duplicar
        imp2 = self._import(w1, rid)
        self.assertTrue(imp2['deduplicated'])
        self.assertEqual(imp2['versionId'], imp['versionId'])
        lib = self.studio.get_media_library(w1)
        asset = next(a for a in lib['mediaLibrary']['assets'] if a['id'] == imp['assetId'])
        self.assertEqual(len(asset['versions']), 1)
        entry = self.studio.get_video_requests(w1)['requests'][0]
        self.assertEqual(entry['status'], 'imported')
        # arquivo de staging removido apos importacao
        self.assertFalse(os.path.exists(os.path.join(ROOT, '.workspace', 'tmp', 'studio-video-api', rid)))

    def test_03_failure_modes_and_explicit_resubmit(self):
        w1, p1 = self._make_work('d')
        self._conn('google-d', key='synthetic-key-d')
        self._select_video(p1, 'google-d')
        for mode, code in (('refused', 'CREDENTIAL_REFUSED'), ('limit', 'RATE_LIMIT'),
                           ('invalid', 'INVALID_RESULT'), ('no_video', 'INVALID_RESULT')):
            self.state.mode = mode
            rid = self._create(w1, prompt=f'falha {mode}')['request']['id']
            self._submit(w1, rid)
            entry = self._wait_status(w1, rid, ('failed',))
            attempt = entry['attempts'][-1]
            self.assertEqual(attempt['code'], code, mode)
            self.assertIsNotNone(attempt['error'])
            with self.assertRaises(studio_video_api.VideoApiError) as ctx:
                self._submit(w1, rid)
            self.assertEqual(ctx.exception.code, 'RESUBMIT_REQUIRED')
        self.state.mode = 'complete'
        rid = self._create(w1, prompt='recuperacao apos falha')['request']['id']
        self._submit(w1, rid)
        self._wait_status(w1, rid, ('ready',))
        ov = self.studio.get_connections()
        video_calls = [c for c in ov['calls'] if c['capability'] == 'video']
        codes = [c['code'] for c in video_calls]
        for expected in ('CREDENTIAL_REFUSED', 'RATE_LIMIT', 'INVALID_RESULT'):
            self.assertIn(expected, codes)
        self.assertIn(None, codes)  # completed

    def test_04_uncertain_after_send_and_duplicate_click(self):
        w1, p1 = self._make_work('e')
        self._conn('google-e', key='synthetic-key-e')
        self._select_video(p1, 'google-e')
        self.state.mode = 'uncertain'
        rid = self._create(w1)['request']['id']
        self._submit(w1, rid)
        entry = self._wait_status(w1, rid, ('uncertain',))
        self.assertEqual(entry['attempts'][-1]['code'], 'RESULT_UNCERTAIN')
        self.assertIsNone(entry['remoteInteractionId'])
        self.assertEqual(len(self.state.posts), 1)  # envio registrado uma vez
        with self.assertRaises(studio_video_api.VideoApiError) as ctx:
            self._submit(w1, rid)
        self.assertEqual(ctx.exception.code, 'RESUBMIT_REQUIRED')
        # clique duplicado durante processamento nao repete a submissao
        self.state.mode = 'complete'
        self.state.slow_s = 1.5
        rid2 = self._create(w1, prompt='clique duplicado')['request']['id']
        first = self._submit(w1, rid2)
        second = self._submit(w1, rid2)
        self.assertFalse(first['deduplicated'])
        self.assertTrue(second['deduplicated'])
        self._wait_status(w1, rid2, ('ready',))
        self.state.slow_s = 0.0
        self.assertEqual(len([p for p in self.state.posts if p['body'].get('input') == 'clique duplicado']), 1)
        # reenvio explicito do incerto preserva historico
        self.state.mode = 'complete'
        res = self._submit(w1, rid, resubmit=True)
        self.assertFalse(res['deduplicated'])
        entry = self._wait_status(w1, rid, ('ready',))
        self.assertEqual(len(entry['attempts']), 2)
        self.assertEqual(entry['attempts'][0]['code'], 'RESULT_UNCERTAIN')

    def test_05_restart_resumes_confirmed_remote_and_marks_interrupted(self):
        w1, p1 = self._make_work('f')
        self._conn('google-f', key='synthetic-key-f')
        self._select_video(p1, 'google-f')
        self.state.mode = 'inprogress'
        self.state.hold = True
        rid = self._create(w1)['request']['id']
        self._submit(w1, rid)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            entry = self.studio.get_video_requests(w1)['requests'][0]
            if entry['remoteInteractionId']:
                break
            time.sleep(0.2)
        self.assertTrue(entry['remoteInteractionId'])
        self.assertEqual(entry['status'], 'processing')
        # reinicio do Studio com geracao iniciada
        self.studio.close()
        time.sleep(2.5)  # thread antiga percebe o encerramento
        self.state.hold = False
        st2 = self._make_studio()
        self.assertGreaterEqual(st2.video_api_recovery['resumed'], 1)
        entry = self._wait_status(w1, rid, ('ready',), studio=st2)
        self.assertTrue(entry['remoteInteractionId'].startswith('v1_mock_'))
        imp = st2.import_video_request({'workId': w1, 'requestId': rid})
        self.assertEqual(imp['version']['kind'], 'video')
        # pedido processing sem ID remoto (queda antes da resposta) vira incerto no reinicio
        rid2 = self._create(w1, prompt='queda antes do id')['request']['id']
        path = st2.confine_workspace(st2.work_paths(w1)['videoRequestsFile'])
        with open(render_local.fs_path(path), encoding='utf-8') as handle:
            doc = json.load(handle)
        target = next(r for r in doc['requests'] if r['id'] == rid2)
        target['status'] = 'processing'
        target['attempts'] = [{'attemptId': 'att-crash', 'at': '2026-11-15T00:00:00Z',
                               'finishedAt': None, 'status': 'running', 'code': None,
                               'error': None, 'remoteInteractionId': None}]
        with open(render_local.fs_path(path), 'w', encoding='utf-8') as handle:
            json.dump(doc, handle)
        st2.close()
        st3 = self._make_studio()
        self.assertGreaterEqual(st3.video_api_recovery['uncertain'], 1)
        entry2 = next(r for r in st3.get_video_requests(w1)['requests'] if r['id'] == rid2)
        self.assertEqual(entry2['status'], 'uncertain')
        self.assertEqual(entry2['attempts'][-1]['code'], 'INTERRUPTED')
        # resultados ja recebidos sao preservados apos reinicio
        entry1 = next(r for r in st3.get_video_requests(w1)['requests'] if r['id'] == rid)
        self.assertEqual(entry1['status'], 'imported')

    def test_06_uri_delivery_polls_file_and_downloads(self):
        w1, p1 = self._make_work('g')
        self._conn('google-g', key='synthetic-key-g')
        self._select_video(p1, 'google-g')
        self.state.mode = 'uri'
        self.state.file_active_after = 2
        rid = self._create(w1)['request']['id']
        self._submit(w1, rid)
        entry = self._wait_status(w1, rid, ('ready',))
        self.assertTrue(entry['remoteFileId'])
        self.assertGreaterEqual(self.state.file_gets, 2)
        imp = self._import(w1, rid)
        self.assertEqual(imp['version']['kind'], 'video')
        abs_path = self.studio.confine(imp['version']['path'])
        info = render_local.probe_asset(os.path.dirname(abs_path), abs_path)
        self.assertFalse(any(s.get('codec_type') == 'audio' for s in info['streams']))

    def test_07_env_connection_and_missing_connection_errors(self):
        w1, p1 = self._make_work('h')
        with self.assertRaises(studio_video_api.VideoApiError) as ctx:
            self._create(w1)
        self.assertEqual(ctx.exception.code, 'VIDEO_CONNECTION_REQUIRED')
        os.environ['TEST_VIDEO_KEY'] = 'synthetic-env-video-key'
        self._conn('google-env', kind='env')
        self._select_video(p1, 'google-env')
        rid = self._create(w1)['request']['id']
        self._submit(w1, rid)
        self._wait_status(w1, rid, ('ready',))
        self.assertEqual(self.state.posts[-1]['key'], 'synthetic-env-video-key')
        os.environ['TEST_VIDEO_KEY'] = 'synthetic-env-video-key-2'
        rid2 = self._create(w1, prompt='segunda chamada env')['request']['id']
        self._submit(w1, rid2)
        self._wait_status(w1, rid2, ('ready',))
        self.assertEqual(self.state.posts[-1]['key'], 'synthetic-env-video-key-2')

    def test_08_secrets_never_leak_and_testar_reports_video_model(self):
        w1, p1 = self._make_work('i')
        secret = 'synthetic-leak-video-777'
        self._conn('google-i', key=secret)
        self._select_video(p1, 'google-i')
        self.state.expected_key = secret
        rid = self._create(w1)['request']['id']
        self._submit(w1, rid)
        self._wait_status(w1, rid, ('ready',))
        self._import(w1, rid)
        test = self.studio.test_connection({'connectionId': 'google-i'})['test']
        self.assertEqual(test['status'], 'ok')
        self.assertEqual(test['videoModel']['model'], 'gemini-omni-1.2-flash')
        self.assertTrue(test['videoModel']['listed'])
        work_dir = os.path.join(ROOT, '.workspace', 'studio', 'works', w1)
        checked = []
        for base, _dirs, files in os.walk(work_dir):
            for name in files:
                if name.endswith(('.json', '.txt', '.srt')):
                    path = os.path.join(base, name)
                    with open(render_local.fs_path(path), encoding='utf-8', errors='replace') as handle:
                        self.assertNotIn(secret, handle.read(), path)
                    checked.append(path)
        self.assertTrue(checked)
        with open(os.path.join(ROOT, '.workspace', 'studio', 'connections.json'), encoding='utf-8') as handle:
            self.assertNotIn(secret, handle.read())
        for blob in (json.dumps(self.studio.get_connections(), ensure_ascii=False),
                     json.dumps(self.studio.get_video_requests(w1), ensure_ascii=False),
                     json.dumps(self.studio.get_media_library(w1), ensure_ascii=False)):
            self.assertNotIn(secret, blob)
        with open(self.vault_path, encoding='utf-8') as handle:
            self.assertIn(secret, handle.read())
        # a chave aparece apenas nas chamadas autenticadas esperadas do simulador
        self.assertTrue(all(p['key'] == secret for p in self.state.posts))


if __name__ == '__main__':
    unittest.main()