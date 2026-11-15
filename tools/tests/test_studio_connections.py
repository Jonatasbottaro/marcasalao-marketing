"""Testes da aba Conexoes: cadastro, cofre, selecao por projeto, diagnostico e historico.

Usa backend de cofre simulado (STUDIO_CREDENTIAL_BACKEND=simulated) e servidores
HTTP simulados para texto local e Gemini. Nenhuma credencial real e usada.
"""

import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
TOOLS = os.path.join(ROOT, 'tools')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import carousel_layout
import studio_connections
import video_studio


def _free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _png_bytes(width=64, height=64):
    rgb = bytearray(width * height * 3)
    for i in range(0, len(rgb), 3):
        rgb[i], rgb[i + 1], rgb[i + 2] = 40, 120, 200
    return carousel_layout.encode_png(width, height, rgb)


class _MockState:
    def __init__(self):
        self.models_status = 200
        self.chat_status = 200
        self.models = ['qwen3:8b', 'other:1b']
        self.expected_token = None
        self.expected_key = None
        self.chat_calls = []
        self.image_calls = []
        self.models_calls = 0


class _MockLLMHandler(BaseHTTPRequestHandler):
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

    def do_GET(self):
        st = self.state
        st.models_calls += 1
        if self.path == '/v1/models':
            if st.models_status != 200:
                self._send(st.models_status, {'error': 'simulado'})
                return
            self._send(200, {'data': [{'id': m} for m in st.models]})
            return
        self._send(404, {'error': 'not found'})

    def do_POST(self):
        st = self.state
        n = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(n) or b'{}')
        auth = self.headers.get('Authorization')
        st.chat_calls.append({'model': body.get('model'), 'auth': auth})
        if st.chat_status != 200:
            self._send(st.chat_status, {'error': 'simulado'})
            return
        if st.expected_token is not None and auth != f'Bearer {st.expected_token}':
            self._send(401, {'error': 'token invalido'})
            return
        suggestion = {
            'schemaVersion': 1, 'stage': 'briefing', 'product': 'Teste',
            'audience': 'Publico de teste', 'objective': 'Objetivo de teste',
            'coreMessage': 'Mensagem central de teste', 'supportEvidence': 'Evidencia de teste',
            'cta': 'CTA de teste', 'tone': 'Direto', 'recommendedProfiles': ['instagram-reels-video'],
            'gaps': [], 'questions': [], 'claims': [],
        }
        self._send(200, {
            'model': body.get('model'),
            'choices': [{'message': {'content': json.dumps(suggestion, ensure_ascii=False)}}],
            'usage': {'prompt_tokens': 11, 'completion_tokens': 7, 'total_tokens': 18},
        })


class _MockGeminiHandler(BaseHTTPRequestHandler):
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

    def do_GET(self):
        st = self.state
        st.models_calls += 1
        if self.path == '/v1beta/models':
            if st.models_status != 200:
                self._send(st.models_status, {'error': {'message': 'simulado'}})
                return
            self._send(200, {'models': [{'name': f'models/{m}'} for m in st.models]})
            return
        self._send(404, {'error': {'message': 'not found'}})

    def do_POST(self):
        st = self.state
        n = int(self.headers.get('Content-Length', 0))
        self.rfile.read(n)
        key = self.headers.get('x-goog-api-key')
        st.image_calls.append({'path': self.path, 'key': key})
        if st.chat_status != 200:
            self._send(st.chat_status, {'error': {'message': 'simulado'}})
            return
        if st.expected_key is not None and key != st.expected_key:
            self._send(403, {'error': {'message': 'API key invalida'}})
            return
        import base64
        self._send(200, {
            'modelVersion': 'gemini-3.1-flash-image',
            'candidates': [{'finishReason': 'STOP', 'content': {'parts': [
                {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(_png_bytes()).decode('ascii')}}
            ]}}],
            'usageMetadata': {'promptTokenCount': 5, 'candidatesTokenCount': 3, 'totalTokenCount': 8},
        })


class TestStudioConnections(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='t_conn_', dir=os.path.join(ROOT, '.workspace', 'tmp'))
        self.vault_path = os.path.join(self.tmp, 'vault.json')
        self._env_backup = {k: os.environ.get(k) for k in (
            'STUDIO_CREDENTIAL_BACKEND', 'STUDIO_CREDENTIAL_STORE_PATH',
            'STUDIO_LLM_ENABLED', 'STUDIO_LLM_ENDPOINT', 'STUDIO_LLM_MODEL',
            'GEMINI_API_KEY', 'STUDIO_GEMINI_IMAGE_ENDPOINT', 'TEST_GEMINI_KEY')}
        os.environ['STUDIO_CREDENTIAL_BACKEND'] = 'simulated'
        os.environ['STUDIO_CREDENTIAL_STORE_PATH'] = self.vault_path
        for k in ('STUDIO_LLM_ENABLED', 'STUDIO_LLM_ENDPOINT', 'STUDIO_LLM_MODEL',
                  'GEMINI_API_KEY', 'STUDIO_GEMINI_IMAGE_ENDPOINT', 'TEST_GEMINI_KEY'):
            os.environ.pop(k, None)
        self.studios = []
        self.work_ids = []
        self.project_files = []
        self.servers = []
        self.studio = self._make_studio()
        self.llm_state = _MockState()
        self.gem_state = _MockState()
        self.llm_port = self._serve(_MockLLMHandler, self.llm_state)
        self.gem_port = self._serve(_MockGeminiHandler, self.gem_state)
        self.llm_url = f'http://127.0.0.1:{self.llm_port}/v1/chat/completions'
        self.gem_url = f'http://127.0.0.1:{self.gem_port}'

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
            shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', wid), ignore_errors=True)
        for pf in self.project_files:
            if os.path.exists(pf):
                try:
                    os.remove(pf)
                except OSError:
                    pass
        conn_file = os.path.join(ROOT, '.workspace', 'studio', 'connections.json')
        if os.path.exists(conn_file):
            os.remove(conn_file)
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

    def _serve(self, handler, state):
        handler.state = state
        port = _free_port()
        srv = ThreadingHTTPServer(('127.0.0.1', port), handler)
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        self.servers.append((srv, thread))
        return port

    def _make_work(self, suffix):
        wid = f'tconn-{suffix}-{os.getpid()}'
        self.work_ids.append(wid)
        proj = self.studio.create_project({
            'schemaVersion': 1, 'id': f'tconn-proj-{suffix}-{os.getpid()}', 'name': f'Projeto {suffix}',
            'locale': 'pt-BR', 'timezone': 'America/Sao_Paulo', 'brandTheme': 'marca-salao',
            'assetRoot': f'.workspace/studio/works/{wid}/media',
            'contentPolicies': {'requireApprovedBriefing': True, 'requireApprovedScript': True,
                                'prohibitPersonalData': True, 'requireFunctionalEvidence': True},
            'outputProfiles': ['instagram-reels-video', 'instagram-feed-image-square'],
        })
        self.project_files.append(self.studio.confine(proj['path']))
        self.studio.create_work({'id': wid, 'name': f'Trabalho {suffix}', 'project': proj['path'], 'template': 'blank'})
        self.studio.save_planning({'workId': wid, 'ideaText': 'Ideia de teste conexoes', 'creative': {
            'hookOptions': [{'id': 'hook-1', 'text': 'Hook de teste', 'angle': 'dor'}],
            'selectedHookId': 'hook-1',
            'scriptSummary': 'Abertura e demonstracao de teste.',
            'videoScenes': [
                {'id': 'cena-1', 'objective': 'Abertura', 'narrativeFunction': 'hook', 'durationMs': 2000,
                 'titleOverlay': 'T1', 'caption': 'C1', 'narration': 'N1',
                 'requiredMediaDescriptor': 'Capa de teste', 'motionIntent': 'none'},
                {'id': 'cena-2', 'objective': 'Demonstracao', 'narrativeFunction': 'demonstration', 'durationMs': 2000,
                 'titleOverlay': 'T2', 'caption': 'C2', 'narration': 'N2',
                 'requiredMediaDescriptor': 'Tela de teste', 'motionIntent': 'none'},
            ],
            'carouselCards': [{'id': 'capa', 'role': 'cover', 'title': 'Capa', 'body': 'Corpo',
                               'requiredMediaDescriptor': ''}],
        }})
        return wid, proj['path']

    def _conn(self, cid, provider, endpoint, model, credential=None, value=None):
        body = {'id': cid, 'name': cid, 'provider': provider, 'endpoint': endpoint, 'model': model}
        if credential:
            body['credential'] = credential
        if value is not None:
            body['credentialValue'] = value
        return self.studio.save_connection(body)['connection']

    def _generate_text(self, wid):
        ov = self.studio.get_planning_overview(wid)
        return self.studio.generate_planning_suggestion({
            'workId': wid, 'stage': 'briefing',
            'expectedContextFingerprint': ov['fingerprints']['contextFingerprint'],
        })

    def _generate_image(self, wid, project_key):
        req = self.studio.create_image_request({
            'workId': wid, 'targetKind': 'video_scene', 'targetId': 'cena-1',
            'prompt': 'Imagem de teste conexoes',
        })['requestId']
        ov = self.studio.get_media_library(wid)
        return self.studio.generate_image_candidate({
            'workId': wid, 'requestId': req, 'provider': 'google-gemini', 'confirm': True,
            'expectedLibraryFingerprint': ov['libraryFingerprint'],
        })

    # ------------------------------------------------------------------
    def test_01_registry_credential_kinds_and_no_secret_in_metadata(self):
        secret = 'synthetic-vault-key-001'
        c_none = self._conn('local-sem-chave', 'local-llm', self.llm_url, 'qwen3:8b')
        c_vault = self._conn('gemini-cofre', 'google-gemini', self.gem_url, 'gemini-3.1-flash-image',
                             {'kind': 'vault'}, value=secret)
        os.environ['TEST_GEMINI_KEY'] = 'synthetic-env-key-002'
        c_env = self._conn('gemini-env', 'google-gemini', self.gem_url, 'gemini-3.1-flash-image',
                           {'kind': 'env', 'envVar': 'TEST_GEMINI_KEY'})
        self.assertEqual(c_none['credential']['kind'], 'none')
        self.assertTrue(c_none['credential']['configured'])
        self.assertTrue(c_vault['credential']['configured'])
        self.assertTrue(c_env['credential']['configured'])
        ov = self.studio.get_connections()
        blob = json.dumps(ov, ensure_ascii=False)
        self.assertNotIn(secret, blob)
        self.assertNotIn('synthetic-env-key-002', blob)
        with open(os.path.join(ROOT, '.workspace', 'studio', 'connections.json'), encoding='utf-8') as f:
            self.assertNotIn(secret, f.read())
        with open(self.vault_path, encoding='utf-8') as f:
            self.assertIn(secret, f.read())
        self.assertEqual(ov['storeBackend'], 'simulated')
        # combinacoes nao suportadas: capacidades derivam do provedor nesta versao
        odd = self.studio.save_connection({'id': 'x', 'name': 'x', 'provider': 'local-llm',
                                           'endpoint': self.llm_url, 'model': 'm',
                                           'credential': {'kind': 'env', 'envVar': 'TEST_GEMINI_KEY'},
                                           'capabilities': ['image']})['connection']
        self.assertEqual(odd['capabilities'], ['text'])

    def test_02_per_project_selection_text_and_image(self):
        w1, p1 = self._make_work('a')
        w2, p2 = self._make_work('b')
        self._conn('texto-a', 'local-llm', self.llm_url, 'qwen3:8b', {'kind': 'vault'}, value='tok-a')
        self._conn('texto-b', 'local-llm', self.llm_url, 'other:1b', {'kind': 'vault'}, value='tok-b')
        self.studio.select_connection({'project': p1, 'capability': 'text', 'connectionId': 'texto-a'})
        self.studio.select_connection({'project': p2, 'capability': 'text', 'connectionId': 'texto-b'})
        self.llm_state.expected_token = None  # aceita qualquer, registramos o recebido
        self._generate_text(w1)
        self._generate_text(w2)
        self.assertEqual(self.llm_state.chat_calls[-2]['model'], 'qwen3:8b')
        self.assertEqual(self.llm_state.chat_calls[-2]['auth'], 'Bearer tok-a')
        self.assertEqual(self.llm_state.chat_calls[-1]['model'], 'other:1b')
        self.assertEqual(self.llm_state.chat_calls[-1]['auth'], 'Bearer tok-b')

        self._conn('img-a', 'google-gemini', self.gem_url, 'gemini-3.1-flash-image', {'kind': 'vault'}, value='key-a')
        self._conn('img-b', 'google-gemini', self.gem_url, 'gemini-3.1-flash-image', {'kind': 'vault'}, value='key-b')
        self.studio.select_connection({'project': p1, 'capability': 'image', 'connectionId': 'img-a'})
        self.studio.select_connection({'project': p2, 'capability': 'image', 'connectionId': 'img-b'})
        self._generate_image(w1, 'key-a')
        self._generate_image(w2, 'key-b')
        self.assertEqual(self.gem_state.image_calls[-2]['key'], 'key-a')
        self.assertEqual(self.gem_state.image_calls[-1]['key'], 'key-b')

        ov = self.studio.get_connections()
        text_calls = [c for c in ov['calls'] if c['capability'] == 'text']
        img_calls = [c for c in ov['calls'] if c['capability'] == 'image']
        self.assertEqual(text_calls[0]['connectionId'], 'texto-b')
        self.assertEqual(text_calls[0]['usage'], {'promptTokens': 11, 'completionTokens': 7, 'totalTokens': 18})
        self.assertEqual(img_calls[0]['connectionId'], 'img-b')
        self.assertEqual(img_calls[0]['usage']['totalTokens'], 8)
        # overview do planejamento e da midia mostram a selecao sem segredo
        pov = self.studio.get_planning_overview(w1)
        self.assertEqual(pov['textConnection']['connectionId'], 'texto-a')
        self.assertNotIn('secret', pov['textConnection'])
        mov = self.studio.get_media_library(w1)
        self.assertEqual(mov['imageConnection']['connectionId'], 'img-a')
        gem = next(p for p in mov['providers'] if p['providerId'] == 'google-gemini')
        self.assertTrue(gem['configured'])
        self.assertEqual(gem['connectionId'], 'img-a')

    def test_03_replace_credential_and_restart_resolves_current_key(self):
        w1, p1 = self._make_work('c')
        self._conn('img-c', 'google-gemini', self.gem_url, 'gemini-3.1-flash-image', {'kind': 'vault'}, value='old-key')
        self.studio.select_connection({'project': p1, 'capability': 'image', 'connectionId': 'img-c'})
        self.gem_state.expected_key = 'old-key'
        self._generate_image(w1, 'old-key')
        res = self.studio.replace_connection_credential({'connectionId': 'img-c', 'value': 'new-key'})
        self.assertEqual(res['connection']['id'], 'img-c')
        self.assertTrue(res['connection']['credential']['configured'])
        # reinicio do Studio: mesma referencia resolve a chave atual
        self.studio.close()
        st2 = self._make_studio()
        resolved = studio_connections.resolve_for_project(st2, p1, 'image')
        self.assertEqual(resolved['secret'], 'new-key')
        self.assertEqual(resolved['connectionId'], 'img-c')
        self.gem_state.expected_key = 'new-key'
        req = st2.create_image_request({'workId': w1, 'targetKind': 'video_scene', 'targetId': 'cena-2',
                                        'prompt': 'Apos troca de chave'})['requestId']
        ov = st2.get_media_library(w1)
        st2.generate_image_candidate({'workId': w1, 'requestId': req, 'provider': 'google-gemini',
                                      'confirm': True,
                                      'expectedLibraryFingerprint': ov['libraryFingerprint']})
        self.assertEqual(self.gem_state.image_calls[-1]['key'], 'new-key')
        sel = st2.get_connections()['selections'][p1]['image']
        self.assertEqual(sel['connectionId'], 'img-c')

    def test_04_diagnostics_classify_and_never_generate(self):
        self._conn('diag', 'local-llm', self.llm_url, 'qwen3:8b', {'kind': 'vault'}, value='tok-diag')
        self.llm_state.expected_token = 'tok-diag'
        ok = self.studio.test_connection({'connectionId': 'diag'})['test']
        self.assertEqual(ok['status'], 'ok')
        self.llm_state.models_status = 401
        refused = self.studio.test_connection({'connectionId': 'diag'})['test']
        self.assertEqual(refused['code'], 'CREDENTIAL_REFUSED')
        self.llm_state.models_status = 429
        self.assertEqual(self.studio.test_connection({'connectionId': 'diag'})['test']['code'], 'RATE_LIMIT')
        self.llm_state.models_status = 200
        self.llm_state.models = ['outro-modelo:9b']
        self.assertEqual(self.studio.test_connection({'connectionId': 'diag'})['test']['code'], 'MODEL_INCOMPATIBLE')
        self.llm_state.models = ['qwen3:8b']
        # falha de rede: porta fechada
        dead_port = _free_port()
        self.studio.save_connection({'id': 'diag-rede', 'name': 'rede', 'provider': 'local-llm',
                                     'endpoint': f'http://127.0.0.1:{dead_port}/v1/chat/completions',
                                     'model': 'qwen3:8b'})
        net = self.studio.test_connection({'connectionId': 'diag-rede'})['test']
        self.assertEqual(net['code'], 'UNAVAILABLE')
        # gemini sem credencial
        self._conn('diag-sem-chave', 'google-gemini', self.gem_url, 'gemini-3.1-flash-image')
        missing = self.studio.test_connection({'connectionId': 'diag-sem-chave'})['test']
        self.assertEqual(missing['code'], 'CREDENTIAL_MISSING')
        self.assertEqual(self.llm_state.chat_calls, [])
        self.assertEqual(self.gem_state.image_calls, [])
        ov = self.studio.get_connections()
        diag_calls = [c for c in ov['calls'] if c['capability'] == 'diagnostic']
        self.assertGreaterEqual(len(diag_calls), 6)
        conn = next(c for c in ov['connections'] if c['id'] == 'diag')
        self.assertIsNotNone(conn['lastTest']['at'])

    def test_05_legacy_env_without_selection(self):
        w1, p1 = self._make_work('d')
        os.environ['STUDIO_LLM_ENABLED'] = '1'
        os.environ['STUDIO_LLM_ENDPOINT'] = self.llm_url
        os.environ['STUDIO_LLM_MODEL'] = 'qwen3:8b'
        os.environ['GEMINI_API_KEY'] = 'legacy-key'
        os.environ['STUDIO_GEMINI_IMAGE_ENDPOINT'] = self.gem_url
        self._generate_text(w1)
        self.assertEqual(self.llm_state.chat_calls[-1]['model'], 'qwen3:8b')
        self.assertIsNone(self.llm_state.chat_calls[-1]['auth'])
        self.gem_state.expected_key = 'legacy-key'
        self._generate_image(w1, 'legacy-key')
        self.assertEqual(self.gem_state.image_calls[-1]['key'], 'legacy-key')
        ov = self.studio.get_connections()
        self.assertIsNone(ov['calls'][0]['connectionId'])
        self.assertTrue(ov['legacy']['image']['configured'])
        self.assertTrue(ov['legacy']['text']['enabled'])

    def test_06_env_connection_resolves_at_call_time(self):
        w1, p1 = self._make_work('e')
        os.environ['TEST_GEMINI_KEY'] = 'env-v1'
        self._conn('img-env', 'google-gemini', self.gem_url, 'gemini-3.1-flash-image',
                   {'kind': 'env', 'envVar': 'TEST_GEMINI_KEY'})
        self.studio.select_connection({'project': p1, 'capability': 'image', 'connectionId': 'img-env'})
        self.gem_state.expected_key = 'env-v1'
        self._generate_image(w1, 'env-v1')
        os.environ['TEST_GEMINI_KEY'] = 'env-v2'
        self.gem_state.expected_key = 'env-v2'
        req = self.studio.create_image_request({'workId': w1, 'targetKind': 'video_scene', 'targetId': 'cena-2',
                                                'prompt': 'Segunda chamada'})['requestId']
        ov = self.studio.get_media_library(w1)
        self.studio.generate_image_candidate({'workId': w1, 'requestId': req, 'provider': 'google-gemini',
                                              'confirm': True,
                                              'expectedLibraryFingerprint': ov['libraryFingerprint']})
        self.assertEqual(self.gem_state.image_calls[-1]['key'], 'env-v2')

    def test_07_secrets_never_leak_to_state_logs_or_exports(self):
        w1, p1 = self._make_work('f')
        secret = 'synthetic-leak-check-999'
        self._conn('img-f', 'google-gemini', self.gem_url, 'gemini-3.1-flash-image', {'kind': 'vault'}, value=secret)
        self.studio.select_connection({'project': p1, 'capability': 'image', 'connectionId': 'img-f'})
        self.gem_state.expected_key = secret
        self._generate_image(w1, secret)
        self.studio.test_connection({'connectionId': 'img-f'})
        self.gem_state.models_status = 403
        self.studio.test_connection({'connectionId': 'img-f'})
        self.gem_state.models_status = 200
        work_dir = os.path.join(ROOT, '.workspace', 'studio', 'works', w1)
        checked = []
        for base, _dirs, files in os.walk(work_dir):
            for name in files:
                if name.endswith(('.json', '.txt', '.srt')):
                    path = os.path.join(base, name)
                    with open(path, encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    self.assertNotIn(secret, content, path)
                    checked.append(path)
        self.assertTrue(checked)
        for extra in ('connections.json', 'llm-config.json'):
            path = os.path.join(ROOT, '.workspace', 'studio', extra)
            if os.path.exists(path):
                with open(path, encoding='utf-8') as f:
                    self.assertNotIn(secret, f.read())
        ov_blob = json.dumps(self.studio.get_connections(), ensure_ascii=False)
        self.assertNotIn(secret, ov_blob)


if __name__ == '__main__':
    unittest.main()