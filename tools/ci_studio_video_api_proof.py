"""Prova HTTP da geracao de clipes por API no Video Studio (CI).

Fornecedor simulado da Interactions API (Gemini Omni Flash), cofre simulado e
credenciais sinteticas. Cobre: dois projetos com a mesma conexao Google para
imagem e video, modelo por capacidade, confirmacao com avisos de retencao e
cobranca, falhas (credencial recusada, limite, resultado invalido, resposta
incerta), reenvio explicito, clique duplicado, reinicio com retomada,
importacao silenciosa idempotente, selecao em cena e saida pela Fila de
Producao sem audio + SRT + TXT. Varre segredos em estado, respostas e arquivos.
"""

import argparse
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
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
TOOLS = os.path.join(ROOT, 'tools')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import build_video
import carousel_layout
import render_local
import video_studio


def _free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _rmtree(path):
    # caminhos longos no Windows: sem o prefixo \\?\ a remocao falha silenciosamente
    target = render_local.fs_path(path, force=True)
    if os.path.exists(target):
        shutil.rmtree(target, ignore_errors=True)


def _http_json(url, method='GET', body=None, origin=None):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json'
        if origin:
            headers['Origin'] = origin
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _http_error(url, body, origin):
    try:
        _http_json(url, 'POST', body, origin=origin)
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read().decode('utf-8'))
        return exc.code, payload
    raise AssertionError('esperava erro HTTP')


def _make_clip_with_audio(path, width=320, height=240, duration_s=2.0, fps=15):
    ffmpeg = build_video.get_ffmpeg()
    cmd = [
        ffmpeg, '-y',
        '-f', 'lavfi', '-i', f'color=c=0x28A03C:s={width}x{height}:r={fps}:d={duration_s}',
        '-f', 'lavfi', '-i', f'sine=frequency=440:duration={duration_s}',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if res.returncode != 0:
        raise RuntimeError(f'ffmpeg fixture failed: {res.stderr[-400:]}')


def _probe(path):
    return render_local.probe_asset(os.path.dirname(path), path)


def _video_stream(info):
    return next(s for s in info['streams'] if s.get('codec_type') == 'video')


def _fps_of(stream):
    for key in ('avg_frame_rate', 'r_frame_rate'):
        raw = stream.get(key) or ''
        if '/' in raw:
            num, den = raw.split('/', 1)
            try:
                if float(den) > 0 and float(num) > 0:
                    return float(num) / float(den)
            except ValueError:
                continue
    return 30.0


class _State:
    def __init__(self, video_bytes, port, geometry_bytes=None):
        self.video_bytes = video_bytes
        self.geometry_bytes = geometry_bytes or video_bytes
        self.port = port
        self.mode = 'complete'
        self.expected_key = None
        self.posts = []
        self.image_calls = []
        self.gets = []
        self.file_gets = 0
        self.hold = False
        self.interactions = {}
        self.counter = 0


class _Handler(BaseHTTPRequestHandler):
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
            'status': 'completed', 'model': 'gemini-omni-1.2-flash', 'object': 'interaction',
            'steps': [
                {'type': 'user_input', 'content': [{'type': 'text', 'text': 'prompt'}]},
                {'type': 'model_output', 'content': [content]},
            ],
            'usageMetadata': {'promptTokenCount': 12, 'candidatesTokenCount': 34, 'totalTokenCount': 46},
        }

    def do_GET(self):
        st = self.state
        path = urlparse(self.path).path
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
                self._send_bytes(200, st.video_bytes, 'video/mp4')
                return
            st.file_gets += 1
            self._send(200, {'name': f'files/{fid}',
                             'state': 'ACTIVE' if st.file_gets >= 2 else 'PROCESSING'})
            return
        self._send(404, {'error': {'message': 'not found'}})

    def do_POST(self):
        st = self.state
        path = urlparse(self.path).path
        n = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(n) or b'{}')
        key = self.headers.get('x-goog-api-key')
        if path.endswith(':generateContent'):
            st.image_calls.append({'key': key, 'path': path})
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
            return
        st.posts.append({'path': path, 'key': key, 'body': body})
        if path != '/v1beta/interactions':
            self._send(404, {'error': {'message': 'not found'}})
            return
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
            self.close_connection = True
            return
        st.counter += 1
        iid = f'v1_ci_{st.counter}'
        rf = body.get('response_format') or {}
        geometry_case = (rf.get('duration') == '4s' and rf.get('aspect_ratio') == '9:16'
                         and rf.get('resolution') == '720p')
        clip = st.geometry_bytes if geometry_case else st.video_bytes
        st.posts[-1]['fixture'] = '720x1280-4s' if geometry_case else '320x240-2s'
        if st.mode == 'invalid':
            payload = self._video_step({'type': 'video', 'mime_type': 'video/mp4', 'data': '!!invalido!!'})
        elif st.mode == 'uri':
            fid = f'file-{st.counter}'
            payload = self._video_step({'type': 'video', 'mime_type': 'video/mp4',
                                        'uri': f'http://127.0.0.1:{st.port}/v1beta/files/{fid}:download?alt=media'})
        elif st.mode == 'inprogress':
            payload = self._video_step({'type': 'video', 'mime_type': 'video/mp4',
                                        'data': base64.b64encode(clip).decode('ascii')})
            payload['id'] = iid
            st.interactions[iid] = payload
            self._send(200, {'id': iid, 'status': 'in_progress', 'steps': []})
            return
        else:
            payload = self._video_step({'type': 'video', 'mime_type': 'video/mp4',
                                        'data': base64.b64encode(clip).decode('ascii')})
        payload['id'] = iid
        st.interactions[iid] = payload
        self._send(200, payload)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prova HTTP de clipes por API (Studio)')
    parser.add_argument('--port', type=int, default=8808)
    args = parser.parse_args(argv)

    tmp = tempfile.mkdtemp(prefix='ci-vapi-', dir=os.path.join(ROOT, '.workspace', 'tmp'))
    vault_path = os.path.join(tmp, 'vault.json')
    clip_path = os.path.join(tmp, 'clip-with-audio.mp4')
    _make_clip_with_audio(clip_path)
    with open(clip_path, 'rb') as handle:
        clip_bytes = handle.read()
    # Caso de geometria: o pedido 4s/9:16/720p recebe um MP4 H.264 720x1280 de 4 s
    # com audio sintetico, para conferir a preservacao na importacao da Biblioteca.
    geometry_path = os.path.join(tmp, 'clip-720x1280-4s-with-audio.mp4')
    _make_clip_with_audio(geometry_path, width=720, height=1280, duration_s=4.0, fps=30)
    with open(geometry_path, 'rb') as handle:
        geometry_bytes = handle.read()
    geometry_input_info = _probe(geometry_path)
    geometry_input_audio = [s for s in geometry_input_info['streams'] if s.get('codec_type') == 'audio']
    assert geometry_input_audio, 'fixture de geometria sem faixa de audio'
    # Medidas do insumo observadas por FFprobe; a tolerancia de duracao e
    # 1 quadro do FPS da fixture (nao o FPS do arquivo importado).
    geometry_input_vstream = _video_stream(geometry_input_info)
    geometry_input_fps = _fps_of(geometry_input_vstream)
    geometry_input_duration = float(geometry_input_vstream.get('duration')
                                    or geometry_input_info.get('format', {}).get('duration'))
    geometry_input_width = int(geometry_input_vstream['width'])
    geometry_input_height = int(geometry_input_vstream['height'])
    geometry_frame_tol = 1.0 / geometry_input_fps
    assert (geometry_input_width, geometry_input_height) == (720, 1280), geometry_input_vstream
    assert abs(geometry_input_duration - 4.0) <= geometry_frame_tol, geometry_input_duration
    env_backup = {k: os.environ.get(k) for k in (
        'STUDIO_CREDENTIAL_BACKEND', 'STUDIO_CREDENTIAL_STORE_PATH', 'GEMINI_API_KEY')}
    os.environ['STUDIO_CREDENTIAL_BACKEND'] = 'simulated'
    os.environ['STUDIO_CREDENTIAL_STORE_PATH'] = vault_path
    os.environ.pop('GEMINI_API_KEY', None)

    mock_port = _free_port()
    state = _State(clip_bytes, mock_port, geometry_bytes=geometry_bytes)
    handler = type('BoundCIHandler', (_Handler,), {'state': state})
    mock_srv = ThreadingHTTPServer(('127.0.0.1', mock_port), handler)
    threading.Thread(target=mock_srv.serve_forever, daemon=True).start()
    gem_url = f'http://127.0.0.1:{mock_port}'

    works = ['ci-vapi-a', 'ci-vapi-b']
    pfiles = []
    httpd = studio = None
    base = f'http://127.0.0.1:{args.port}'
    post = lambda u, b: _http_json(u, 'POST', b, origin=base)
    secret = 'ci-vapi-key-1'

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

    def wait_request(wid, rid, statuses, timeout=120.0):
        deadline = time.monotonic() + timeout
        entry = None
        while time.monotonic() < deadline:
            data = _http_json(f'{base}/api/works/video-requests?id={wid}')
            entry = next(r for r in data['requests'] if r['id'] == rid)
            if entry['status'] in statuses:
                return entry
            time.sleep(0.3)
        raise TimeoutError(f'pedido {rid} nao alcancou {statuses}; estado: {entry and entry["status"]}')

    def create_submit(wid, prompt, **params):
        body = {'workId': wid, 'prompt': prompt}
        body.update(params)
        created = post(f'{base}/api/works/video-requests/create', body)
        rid = created['request']['id']
        post(f'{base}/api/works/video-requests/submit', {'workId': wid, 'requestId': rid, 'confirm': True})
        return rid, created

    try:
        start_server()
        projects = {}
        for wid, template in (('ci-vapi-a', 'marca-salao'), ('ci-vapi-b', 'blank')):
            _rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', wid))
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
            post(f'{base}/api/works/create', {'id': wid, 'name': f'CI {wid}', 'project': proj, 'template': template})
            post(f'{base}/api/works/planning/save', {'workId': wid, 'ideaText': 'Ideia CI clipes', 'creative': {
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

        # Uma conexao Google para imagem e video; modelo de video por projeto
        post(f'{base}/api/connections/save', {'id': 'ci-vapi-google', 'name': 'Google CI', 'provider': 'google-gemini',
                                              'endpoint': gem_url, 'model': 'gemini-3.1-flash-image',
                                              'credential': {'kind': 'vault'}, 'credentialValue': secret})
        post(f'{base}/api/connections/select', {'project': projects['ci-vapi-a'], 'capability': 'video', 'connectionId': 'ci-vapi-google'})
        post(f'{base}/api/connections/select', {'project': projects['ci-vapi-b'], 'capability': 'video',
                                                'connectionId': 'ci-vapi-google', 'model': 'gemini-omni-1.1-flash'})
        post(f'{base}/api/connections/select', {'project': projects['ci-vapi-a'], 'capability': 'image', 'connectionId': 'ci-vapi-google'})
        t = post(f'{base}/api/connections/test', {'connectionId': 'ci-vapi-google'})['test']
        assert t['status'] == 'ok' and t['videoModel']['listed'] is True, t

        # Projeto A: confirmacao com avisos, geracao, importacao silenciosa idempotente
        rid_a, created = create_submit('ci-vapi-a', 'Clipe CI A: cena continua de demonstracao.',
                                       durationSeconds=4, aspectRatio='9:16', resolution='720p')
        conf = created['confirmation']
        assert conf['connectionId'] == 'ci-vapi-google'
        assert '55 dias' in conf['notices']['retention'] and 'store=true' in conf['notices']['retention']
        assert 'cobranca' in conf['notices']['billing'].lower() or 'Cobranca' in conf['notices']['billing']
        entry = wait_request('ci-vapi-a', rid_a, ('ready',))
        assert entry['remoteInteractionId'].startswith('v1_ci_')
        imp = post(f'{base}/api/works/video-requests/import', {'workId': 'ci-vapi-a', 'requestId': rid_a})
        assert imp['deduplicated'] is False
        version = imp['version']
        assert version['kind'] == 'video' and version['codec'] == 'h264'
        assert version['provenance']['audioRemoved'] is True
        assert version['provenance']['connectionId'] == 'ci-vapi-google'
        assert version['provenance']['model'] == 'gemini-omni-1.2-flash'
        clip_abs = studio.confine(version['path'])
        # FFprobe no arquivo da Biblioteca, antes de qualquer recorte ou montagem:
        # geometria/duracao/codec preservados e zero faixas de audio.
        info = _probe(clip_abs)
        vstream = _video_stream(info)
        assert not any(s.get('codec_type') == 'audio' for s in info['streams']), 'clipe importado com audio'
        assert int(vstream['width']) == 720 and int(vstream['height']) == 1280, \
            f"geometria divergente na Biblioteca: {vstream['width']}x{vstream['height']}"
        assert vstream.get('codec_name') == 'h264', vstream.get('codec_name')
        fps = _fps_of(vstream)
        duration = float(vstream.get('duration') or info.get('format', {}).get('duration'))
        assert abs(duration - 4.0) <= geometry_frame_tol, \
            f'duracao divergente na Biblioteca: {duration}s (tolerancia {geometry_frame_tol:.4f}s = 1 quadro da fixture)'
        assert geometry_input_audio, 'insumo do simulador sem audio'
        geometry_measures = {
            'input': {'width': geometry_input_width, 'height': geometry_input_height,
                      'durationSeconds': round(geometry_input_duration, 6), 'fps': geometry_input_fps,
                      'audioStreams': len(geometry_input_audio),
                      'audioCodec': geometry_input_audio[0].get('codec_name')},
            'library': {'width': int(vstream['width']), 'height': int(vstream['height']),
                        'durationSeconds': round(duration, 6), 'fps': fps,
                        'frameToleranceSeconds': round(geometry_frame_tol, 6),
                        'codec': vstream.get('codec_name'), 'audioStreams': 0,
                        'sha256': version['sha256']},
        }
        imp2 = post(f'{base}/api/works/video-requests/import', {'workId': 'ci-vapi-a', 'requestId': rid_a})
        assert imp2['deduplicated'] is True and imp2['versionId'] == imp['versionId']
        sent = state.posts[-1]
        assert sent['body']['model'] == 'gemini-omni-1.2-flash'
        assert sent['fixture'] == '720x1280-4s', sent['fixture']
        assert sent['body']['response_format'] == {'type': 'video', 'aspect_ratio': '9:16',
                                                   'resolution': '720p', 'duration': '4s'}, sent['body']
        assert state.posts[-1]['key'] == secret

        # Imagem pela mesma conexao/chave
        req = post(f'{base}/api/works/media/request/create', {
            'workId': 'ci-vapi-a', 'targetKind': 'video_scene', 'targetId': 'cena-1', 'prompt': 'Imagem CI',
        })['requestId']
        mov = _http_json(f'{base}/api/works/media-library?id=ci-vapi-a')
        post(f'{base}/api/works/media/generate', {'workId': 'ci-vapi-a', 'requestId': req, 'provider': 'google-gemini',
                                                  'confirm': True, 'expectedLibraryFingerprint': mov['libraryFingerprint']})
        assert state.image_calls[-1]['key'] == secret

        # Projeto B: modelo por capacidade
        rid_b, _ = create_submit('ci-vapi-b', 'Clipe CI B com modelo proprio.')
        wait_request('ci-vapi-b', rid_b, ('ready',))
        assert state.posts[-1]['body']['model'] == 'gemini-omni-1.1-flash'
        assert state.posts[-1]['key'] == secret

        # Falhas e reenvio explicito
        for mode, code in (('refused', 'CREDENTIAL_REFUSED'), ('limit', 'RATE_LIMIT'), ('invalid', 'INVALID_RESULT')):
            state.mode = mode
            rid_f, _ = create_submit('ci-vapi-a', f'falha {mode}')
            entry = wait_request('ci-vapi-a', rid_f, ('failed',))
            assert entry['attempts'][-1]['code'] == code, (mode, entry)
        state.mode = 'uncertain'
        rid_u, _ = create_submit('ci-vapi-a', 'resposta incerta CI')
        entry = wait_request('ci-vapi-a', rid_u, ('uncertain',))
        assert entry['attempts'][-1]['code'] == 'RESULT_UNCERTAIN'
        status_code, payload = _http_error(f'{base}/api/works/video-requests/submit',
                                           {'workId': 'ci-vapi-a', 'requestId': rid_u, 'confirm': True}, base)
        assert status_code == 400 and payload.get('code') == 'RESUBMIT_REQUIRED', payload
        state.mode = 'complete'
        post(f'{base}/api/works/video-requests/submit',
             {'workId': 'ci-vapi-a', 'requestId': rid_u, 'confirm': True, 'resubmit': True})
        wait_request('ci-vapi-a', rid_u, ('ready',))

        # Reinicio com geracao iniciada: retomada pelo ID remoto confirmado
        state.mode = 'inprogress'
        state.hold = True
        rid_r, _ = create_submit('ci-vapi-a', 'geracao iniciada antes do reinicio')
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            data = _http_json(f'{base}/api/works/video-requests?id=ci-vapi-a')
            entry = next(r for r in data['requests'] if r['id'] == rid_r)
            if entry['remoteInteractionId']:
                break
            time.sleep(0.2)
        assert entry['remoteInteractionId'] and entry['status'] == 'processing'
        stop_server()
        time.sleep(2.5)
        state.hold = False
        start_server()
        assert studio.video_api_recovery['resumed'] >= 1
        wait_request('ci-vapi-a', rid_r, ('ready',))
        post(f'{base}/api/works/video-requests/import', {'workId': 'ci-vapi-a', 'requestId': rid_r})

        # Cena + Fila de Producao: composicao montada com o clipe importado
        opened = _http_json(f'{base}/api/works/open?id=ci-vapi-a')
        vreq = opened['videoRequest']
        scene_id = vreq['scenes'][0]['id']
        mov = _http_json(f'{base}/api/works/media-library?id=ci-vapi-a')
        post(f'{base}/api/works/media/select', {
            'workId': 'ci-vapi-a', 'targetKind': 'video_scene', 'targetId': scene_id,
            'assetId': imp['assetId'], 'versionId': imp['versionId'],
            'expectedLibraryFingerprint': mov['libraryFingerprint'],
        })
        opened = _http_json(f'{base}/api/works/open?id=ci-vapi-a')
        vreq = opened['videoRequest']
        vreq['scenes'] = [vreq['scenes'][0]]
        vreq['scenes'][0]['durationMs'] = 1500
        vreq['scenes'][0]['sourceStartMs'] = 0
        vreq['profiles'] = ['instagram-reels-video']
        post(f'{base}/api/works/save', {'workId': 'ci-vapi-a', 'videoRequest': vreq})
        batch = post(f'{base}/api/queue/enqueue', {
            'items': [{'workId': 'ci-vapi-a', 'modality': 'video', 'profileId': 'instagram-reels-video'}],
            'idempotencyKey': f'ci-vapi-{os.getpid()}', 'label': 'CI clipes por API',
        })['batch']
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            b = _http_json(f'{base}/api/queue/batch?id={batch["batchId"]}')['batch']
            if b['counts']['queued'] == 0 and b['counts']['running'] == 0:
                break
            time.sleep(0.5)
        assert b['counts']['completed'] == 1 and b['counts']['failed'] == 0, json.dumps(b, ensure_ascii=False)[:2000]
        delivery = _http_json(f'{base}/api/delivery?dir={studio.work_paths("ci-vapi-a")["videoDeliveryDir"]}')
        entry = next(p for p in delivery['index']['profiles'] if p['profileId'] == 'instagram-reels-video')
        artifacts = entry['lastValidDelivery']['artifacts']

        def _art_path(value):
            return value['path'] if isinstance(value, dict) else value

        video_abs = studio.confine(_art_path(artifacts['video']))
        info = render_local.probe_asset(os.path.dirname(video_abs), video_abs)
        assert not any(s.get('codec_type') == 'audio' for s in info['streams']), 'entrega final com audio'
        assert any(s.get('codec_type') == 'video' for s in info['streams'])
        for kind in ('srt', 'narration'):
            art_abs = studio.confine(_art_path(artifacts[kind]))
            assert os.path.getsize(render_local.fs_path(art_abs)) > 0, kind

        # Segredos nunca aparecem em estado, respostas ou arquivos
        ov = _http_json(f'{base}/api/connections')
        blobs = [json.dumps(ov, ensure_ascii=False),
                 json.dumps(_http_json(f'{base}/api/works/video-requests?id=ci-vapi-a'), ensure_ascii=False),
                 json.dumps(_http_json(f'{base}/api/works/media-library?id=ci-vapi-a'), ensure_ascii=False)]
        with open(os.path.join(ROOT, '.workspace', 'studio', 'connections.json'), encoding='utf-8') as handle:
            blobs.append(handle.read())
        for wid in works:
            for base_dir, _dirs, files in os.walk(os.path.join(ROOT, '.workspace', 'studio', 'works', wid)):
                for name in files:
                    if name.endswith(('.json', '.txt', '.srt')):
                        with open(render_local.fs_path(os.path.join(base_dir, name)),
                                  encoding='utf-8', errors='replace') as handle:
                            blobs.append(handle.read())
        for blob in blobs:
            assert secret not in blob
        assert all(p['key'] == secret for p in state.posts)
        video_calls = [c for c in ov['calls'] if c['capability'] == 'video']
        assert any(c['status'] == 'completed' and c['usage']['totalTokens'] == 46 for c in video_calls)

        print('studio-video-api CI HTTP proof ok')
        print(json.dumps({
            'videoPosts': len(state.posts),
            'imageCalls': len(state.image_calls),
            'videoCalls': len(video_calls),
            'queueCompleted': b['counts']['completed'],
            'deliveryAudioStreams': 0,
            'resumedAfterRestart': studio.video_api_recovery['resumed'],
            'geometryCase': geometry_measures,
        }, ensure_ascii=False))
        return 0
    finally:
        stop_server()
        mock_srv.shutdown()
        mock_srv.server_close()
        for wid in works:
            _rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', wid))
        for pf in pfiles:
            if os.path.exists(pf):
                try:
                    os.remove(pf)
                except OSError:
                    pass
        conn_file = os.path.join(ROOT, '.workspace', 'studio', 'connections.json')
        if os.path.exists(conn_file):
            os.remove(conn_file)
        _rmtree(os.path.join(ROOT, '.workspace', 'tmp', 'studio-video-api'))
        for k, v in env_backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    raise SystemExit(main())