"""Prova HTTP da aba Conexoes do Video Studio (CI).

Cofre simulado (STUDIO_CREDENTIAL_BACKEND=simulated) e servidores HTTP simulados
de texto local e Gemini. Cobre selecao por projeto, diagnostico, troca de chave
com reinicio, legado por ambiente e ausencia de segredos em metadados.
"""

import argparse
import base64
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
TOOLS = os.path.join(ROOT, 'tools')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import carousel_layout
import video_studio


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
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8'))


class _State:
    def __init__(self):
        self.models_status = 200
        self.chat_status = 200
        self.models = ['qwen3:8b', 'other:1b']
        self.chat_calls = []
        self.image_calls = []


class _LLMHandler(BaseHTTPRequestHandler):
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
        if self.path == '/v1/models':
            if self.state.models_status != 200:
                self._send(self.state.models_status, {'error': 'simulado'})
                return
            self._send(200, {'data': [{'id': m} for m in self.state.models]})
            return
        self._send(404, {'error': 'not found'})

    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(n) or b'{}')
        self.state.chat_calls.append({'model': body.get('model'), 'auth': self.headers.get('Authorization')})
        if self.state.chat_status != 200:
            self._send(self.state.chat_status, {'error': 'simulado'})
            return
        suggestion = {
            'schemaVersion': 1, 'stage': 'briefing', 'product': 'Prova CI',
            'audience': 'Publico CI', 'objective': 'Objetivo CI', 'coreMessage': 'Mensagem CI',
            'supportEvidence': 'Evidencia CI', 'cta': 'CTA CI', 'tone': 'Direto',
            'recommendedProfiles': ['instagram-reels-video'], 'gaps': [], 'questions': [], 'claims': [],
        }
        self._send(200, {
            'model': body.get('model'),
            'choices': [{'message': {'content': json.dumps(suggestion, ensure_ascii=False)}}],
            'usage': {'prompt_tokens': 9, 'completion_tokens': 4, 'total_tokens': 13},
        })


class _GeminiHandler(BaseHTTPRequestHandler):
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
        if self.path == '/v1beta/models':
            if self.state.models_status != 200:
                self._send(self.state.models_status, {'error': {'message': 'simulado'}})
                return
            self._send(200, {'models': [{'name': f'models/{m}'} for m in self.state.models]})
            return
        self._send(404, {'error': {'message': 'not found'}})

    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        self.rfile.read(n)
        self.state.image_calls.append({'key': self.headers.get('x-goog-api-key')})
        if self.state.chat_status != 200:
            self._send(self.state.chat_status, {'error': {'message': 'simulado'}})
            return
        rgb = bytearray(64 * 64 * 3)
        for i in range(0, len(rgb), 3):
            rgb[i], rgb[i + 1], rgb[i + 2] = 30, 140, 90
        png = carousel_layout.encode_png(64, 64, rgb)
        self._send(200, {
            'modelVersion': 'gemini-3.1-flash-image',
            'candidates': [{'finishReason': 'STOP', 'content': {'parts': [
                {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(png).decode('ascii')}}
            ]}}],
            'usageMetadata': {'promptTokenCount': 4, 'candidatesTokenCount': 2, 'totalTokenCount': 6},
        })


def _serve(handler, state):
    handler.state = state
    port = _free_port()
    srv = ThreadingHTTPServer(('127.0.0.1', port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prova HTTP da aba Conexoes')
    parser.add_argument('--port', type=int, default=8807)
    args = parser.parse_args(argv)

    tmp = tempfile.mkdtemp(prefix='ci-conn-', dir=os.path.join(ROOT, '.workspace', 'tmp'))
    vault_path = os.path.join(tmp, 'vault.json')
    env_backup = {k: os.environ.get(k) for k in (
        'STUDIO_CREDENTIAL_BACKEND', 'STUDIO_CREDENTIAL_STORE_PATH', 'STUDIO_LLM_ENABLED',
        'STUDIO_LLM_ENDPOINT', 'STUDIO_LLM_MODEL', 'GEMINI_API_KEY',
        'STUDIO_GEMINI_IMAGE_ENDPOINT', 'CI_GEMINI_KEY')}
    os.environ['STUDIO_CREDENTIAL_BACKEND'] = 'simulated'
    os.environ['STUDIO_CREDENTIAL_STORE_PATH'] = vault_path
    for k in ('STUDIO_LLM_ENABLED', 'STUDIO_LLM_ENDPOINT', 'STUDIO_LLM_MODEL', 'GEMINI_API_KEY',
              'STUDIO_GEMINI_IMAGE_ENDPOINT', 'CI_GEMINI_KEY'):
        os.environ.pop(k, None)

    llm_state, gem_state = _State(), _State()
    llm_srv, llm_port = _serve(_LLMHandler, llm_state)
    gem_srv, gem_port = _serve(_GeminiHandler, gem_state)
    llm_url = f'http://127.0.0.1:{llm_port}/v1/chat/completions'
    gem_url = f'http://127.0.0.1:{gem_port}'
    works = ['ci-conn-a', 'ci-conn-b', 'ci-conn-legacy']
    pfiles = []
    httpd = studio = None
    base = f'http://127.0.0.1:{args.port}'
    post = lambda u, b: _http_json(u, 'POST', b, origin=base)

    def start_server():
        nonlocal httpd, studio
        httpd, studio = video_studio.make_server(ROOT, args.port)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        for _ in range(60):
            try:
                _http_json(f'{base}/api/readiness')
                return
            except OSError:
                time.sleep(0.25)
        raise RuntimeError('Studio nao ficou pronto')

    def stop_server():
        nonlocal httpd, studio
        if studio:
            studio.close()
        if httpd:
            httpd.shutdown()
            httpd.server_close()
        httpd = studio = None

    try:
        start_server()
        projects = {}
        for wid in works:
            shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', wid), ignore_errors=True)
            proj = post(f'{base}/api/projects/create', {
                'schemaVersion': 1, 'id': f'ci-{wid}', 'name': f'CI {wid}',
                'locale': 'pt-BR', 'timezone': 'America/Sao_Paulo', 'brandTheme': 'marca-salao',
                'assetRoot': f'.workspace/studio/works/{wid}/media',
                'contentPolicies': {'requireApprovedBriefing': True, 'requireApprovedScript': True,
                                    'prohibitPersonalData': True, 'requireFunctionalEvidence': True},
                'outputProfiles': ['instagram-reels-video', 'instagram-feed-image-square'],
            })['path']
            pfiles.append(studio.confine(proj))
            projects[wid] = proj
            post(f'{base}/api/works/create', {'id': wid, 'name': f'CI {wid}', 'project': proj, 'template': 'blank'})
            post(f'{base}/api/works/planning/save', {'workId': wid, 'ideaText': 'Ideia CI conexoes', 'creative': {
                'hookOptions': [{'id': 'hook-1', 'text': 'Hook CI', 'angle': 'dor'}],
                'selectedHookId': 'hook-1', 'scriptSummary': 'Resumo CI.',
                'videoScenes': [
                    {'id': 'cena-1', 'objective': 'Abertura', 'narrativeFunction': 'hook', 'durationMs': 2000,
                     'titleOverlay': 'T1', 'caption': 'C1', 'narration': 'N1',
                     'requiredMediaDescriptor': 'Capa CI', 'motionIntent': 'none'},
                    {'id': 'cena-2', 'objective': 'Demo', 'narrativeFunction': 'demonstration', 'durationMs': 2000,
                     'titleOverlay': 'T2', 'caption': 'C2', 'narration': 'N2',
                     'requiredMediaDescriptor': 'Tela CI', 'motionIntent': 'none'},
                ],
                'carouselCards': [{'id': 'capa', 'role': 'cover', 'title': 'Capa', 'body': 'Corpo',
                                   'requiredMediaDescriptor': ''}],
            }})

        # Conexoes: sem chave, cofre e variavel de ambiente
        post(f'{base}/api/connections/save', {'id': 'ci-texto-a', 'name': 'Texto A', 'provider': 'local-llm',
                                              'endpoint': llm_url, 'model': 'qwen3:8b'})
        post(f'{base}/api/connections/save', {'id': 'ci-texto-b', 'name': 'Texto B', 'provider': 'local-llm',
                                              'endpoint': llm_url, 'model': 'other:1b',
                                              'credential': {'kind': 'vault'}, 'credentialValue': 'ci-tok-b'})
        post(f'{base}/api/connections/save', {'id': 'ci-img-vault', 'name': 'Gemini cofre', 'provider': 'google-gemini',
                                              'endpoint': gem_url, 'model': 'gemini-3.1-flash-image',
                                              'credential': {'kind': 'vault'}, 'credentialValue': 'ci-key-vault'})
        os.environ['CI_GEMINI_KEY'] = 'ci-key-env'
        post(f'{base}/api/connections/save', {'id': 'ci-img-env', 'name': 'Gemini env', 'provider': 'google-gemini',
                                              'endpoint': gem_url, 'model': 'gemini-3.1-flash-image',
                                              'credential': {'kind': 'env', 'envVar': 'CI_GEMINI_KEY'}})
        post(f'{base}/api/connections/select', {'project': projects['ci-conn-a'], 'capability': 'text', 'connectionId': 'ci-texto-a'})
        post(f'{base}/api/connections/select', {'project': projects['ci-conn-b'], 'capability': 'text', 'connectionId': 'ci-texto-b'})
        post(f'{base}/api/connections/select', {'project': projects['ci-conn-a'], 'capability': 'image', 'connectionId': 'ci-img-vault'})
        post(f'{base}/api/connections/select', {'project': projects['ci-conn-b'], 'capability': 'image', 'connectionId': 'ci-img-env'})

        # Chamadas de texto e imagem por projeto
        for wid in ('ci-conn-a', 'ci-conn-b'):
            ov = _http_json(f'{base}/api/works/planning?id={wid}')
            post(f'{base}/api/works/planning/generate', {'workId': wid, 'stage': 'briefing',
                                                         'expectedContextFingerprint': ov['fingerprints']['contextFingerprint']})
        assert llm_state.chat_calls[-2]['model'] == 'qwen3:8b' and llm_state.chat_calls[-2]['auth'] is None
        assert llm_state.chat_calls[-1]['model'] == 'other:1b' and llm_state.chat_calls[-1]['auth'] == 'Bearer ci-tok-b'
        for wid in ('ci-conn-a', 'ci-conn-b'):
            req = post(f'{base}/api/works/media/request/create', {
                'workId': wid, 'targetKind': 'video_scene', 'targetId': 'cena-1', 'prompt': 'Imagem CI conexoes',
            })['requestId']
            mov = _http_json(f'{base}/api/works/media-library?id={wid}')
            post(f'{base}/api/works/media/generate', {'workId': wid, 'requestId': req, 'provider': 'google-gemini',
                                                      'confirm': True, 'expectedLibraryFingerprint': mov['libraryFingerprint']})
        assert gem_state.image_calls[-2]['key'] == 'ci-key-vault'
        assert gem_state.image_calls[-1]['key'] == 'ci-key-env'

        # Diagnosticos
        t = post(f'{base}/api/connections/test', {'connectionId': 'ci-texto-a'})['test']
        assert t['status'] == 'ok', t
        llm_state.models_status = 401
        assert post(f'{base}/api/connections/test', {'connectionId': 'ci-texto-b'})['test']['code'] == 'CREDENTIAL_REFUSED'
        llm_state.models_status = 429
        assert post(f'{base}/api/connections/test', {'connectionId': 'ci-texto-b'})['test']['code'] == 'RATE_LIMIT'
        llm_state.models_status = 200
        llm_state.models = ['so-outro:9b']
        assert post(f'{base}/api/connections/test', {'connectionId': 'ci-texto-b'})['test']['code'] == 'MODEL_INCOMPATIBLE'
        llm_state.models = ['qwen3:8b', 'other:1b']
        dead = _free_port()
        post(f'{base}/api/connections/save', {'id': 'ci-rede', 'name': 'Rede', 'provider': 'local-llm',
                                              'endpoint': f'http://127.0.0.1:{dead}/v1/chat/completions', 'model': 'qwen3:8b'})
        assert post(f'{base}/api/connections/test', {'connectionId': 'ci-rede'})['test']['code'] == 'UNAVAILABLE'
        post(f'{base}/api/connections/save', {'id': 'ci-sem-chave', 'name': 'Sem chave', 'provider': 'google-gemini',
                                              'endpoint': gem_url, 'model': 'gemini-3.1-flash-image'})
        assert post(f'{base}/api/connections/test', {'connectionId': 'ci-sem-chave'})['test']['code'] == 'CREDENTIAL_MISSING'
        chat_count = len(llm_state.chat_calls)
        post(f'{base}/api/connections/test', {'connectionId': 'ci-texto-a'})
        assert len(llm_state.chat_calls) == chat_count

        # Troca de chave + reinicio: mesma referencia resolve a chave atual
        post(f'{base}/api/connections/credential', {'connectionId': 'ci-img-vault', 'value': 'ci-key-vault-2'})
        stop_server()
        start_server()
        wid = 'ci-conn-a'
        req = post(f'{base}/api/works/media/request/create', {
            'workId': wid, 'targetKind': 'video_scene', 'targetId': 'cena-2', 'prompt': 'Apos reinicio',
        })['requestId']
        mov = _http_json(f'{base}/api/works/media-library?id={wid}')
        post(f'{base}/api/works/media/generate', {'workId': wid, 'requestId': req, 'provider': 'google-gemini',
                                                  'confirm': True, 'expectedLibraryFingerprint': mov['libraryFingerprint']})
        assert gem_state.image_calls[-1]['key'] == 'ci-key-vault-2'
        ov = _http_json(f'{base}/api/connections')
        assert ov['selections'][projects['ci-conn-a']]['image']['connectionId'] == 'ci-img-vault'

        # Legado sem selecao
        os.environ['STUDIO_LLM_ENABLED'] = '1'
        os.environ['STUDIO_LLM_ENDPOINT'] = llm_url
        os.environ['STUDIO_LLM_MODEL'] = 'qwen3:8b'
        os.environ['GEMINI_API_KEY'] = 'ci-legacy-key'
        os.environ['STUDIO_GEMINI_IMAGE_ENDPOINT'] = gem_url
        wid = 'ci-conn-legacy'
        ov = _http_json(f'{base}/api/works/planning?id={wid}')
        post(f'{base}/api/works/planning/generate', {'workId': wid, 'stage': 'briefing',
                                                     'expectedContextFingerprint': ov['fingerprints']['contextFingerprint']})
        req = post(f'{base}/api/works/media/request/create', {
            'workId': wid, 'targetKind': 'video_scene', 'targetId': 'cena-1', 'prompt': 'Legado CI',
        })['requestId']
        mov = _http_json(f'{base}/api/works/media-library?id={wid}')
        post(f'{base}/api/works/media/generate', {'workId': wid, 'requestId': req, 'provider': 'google-gemini',
                                                  'confirm': True, 'expectedLibraryFingerprint': mov['libraryFingerprint']})
        assert gem_state.image_calls[-1]['key'] == 'ci-legacy-key'
        ov = _http_json(f'{base}/api/connections')
        assert ov['calls'][0]['connectionId'] is None
        assert ov['legacy']['image']['configured'] and ov['legacy']['text']['enabled']

        # Segredos nunca aparecem em metadados, estado ou historico
        secrets = ['ci-tok-b', 'ci-key-vault', 'ci-key-vault-2', 'ci-key-env', 'ci-legacy-key']
        blob = json.dumps(ov, ensure_ascii=False)
        for s in secrets:
            assert s not in blob
        with open(os.path.join(ROOT, '.workspace', 'studio', 'connections.json'), encoding='utf-8') as f:
            content = f.read()
        for s in secrets:
            assert s not in content
        for wid in works:
            for base_dir, _dirs, files in os.walk(os.path.join(ROOT, '.workspace', 'studio', 'works', wid)):
                for name in files:
                    if name.endswith(('.json', '.txt', '.srt')):
                        with open(os.path.join(base_dir, name), encoding='utf-8', errors='replace') as f:
                            content = f.read()
                        for s in secrets:
                            assert s not in content, (wid, name)

        print('studio-connections CI HTTP proof ok')
        print(json.dumps({
            'storeBackend': ov['storeBackend'],
            'connections': [c['id'] for c in ov['connections']],
            'calls': len(ov['calls']),
            'textCalls': len(llm_state.chat_calls),
            'imageCalls': len(gem_state.image_calls),
        }, ensure_ascii=False))
        return 0
    finally:
        stop_server()
        llm_srv.shutdown()
        llm_srv.server_close()
        gem_srv.shutdown()
        gem_srv.server_close()
        for wid in works:
            shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', wid), ignore_errors=True)
        for pf in pfiles:
            if os.path.exists(pf):
                try:
                    os.remove(pf)
                except OSError:
                    pass
        conn_file = os.path.join(ROOT, '.workspace', 'studio', 'connections.json')
        if os.path.exists(conn_file):
            os.remove(conn_file)
        for k, v in env_backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    raise SystemExit(main())