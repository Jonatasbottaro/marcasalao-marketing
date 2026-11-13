"""Painel local de video (Video Studio) sobre o pipeline existente.

Servidor HTTP local (stdlib) que serve uma interface HTML/CSS/JS em tools/studio/
e uma API JSON para criar, revisar e exportar um video pelo navegador, usando
VideoRequest v1 como formato de rascunho e execucao. Toda a validacao, render e
promoacao permanecem no pipeline existente (produce_video.py / render_pipeline.py).

Uso (a partir da raiz do checkout):
    python tools/video_studio.py --port 8765

Seguranca:
- Escuta apenas em 127.0.0.1; valida Host e Origin nas operacoes de escrita.
- Confina entradas e saidas a raiz do projeto (realpath); rascunhos e entregas
  ficam em .workspace/.
- Disponibiliza arquivos de entrega apenas por referencias verificadas nos
  manifestos promovidos (delivery-manifest.json), nunca por caminho arbitrario.
- Processos invocados com argumentos estruturados (sem shell).

O painel produz arquivos locais para revisao; nenhuma aprovacao editorial nem
publicacao. Videos sem faixa de audio.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import render_local

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp')
VIDEO_EXTENSIONS = ('.mp4', '.mov')
CONTENT_TYPES = {
    '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8',
    '.mp4': 'video/mp4', '.mov': 'video/quicktime', '.srt': 'text/plain; charset=utf-8',
    '.txt': 'text/plain; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg', '.webp': 'image/webp',
}
ARTIFACT_KINDS = {'video': 'video', 'srt': 'srt', 'narration': 'narration'}


def discover_root(explicit=None):
    if explicit:
        return os.path.realpath(explicit)
    try:
        out = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
        if out:
            return os.path.realpath(out)
    except (OSError, subprocess.CalledProcessError):
        pass
    return os.path.realpath(os.getcwd())


class Studio:
    """Estado e operacoes do painel, confinadas a raiz do projeto."""

    def __init__(self, root, port):
        self.root = root
        self.port = port
        self.tools = os.path.join(root, 'tools')
        self.studio_dir = os.path.join(self.tools, 'studio')
        self.drafts_dir = os.path.join(root, '.workspace', 'tmp', 'video-studio', 'drafts')
        self.jobs = {}
        self.jobs_lock = threading.Lock()
        os.makedirs(self.drafts_dir, exist_ok=True)

    # ---- contencao e seguranca ----
    def confine(self, rel_or_abs):
        if not isinstance(rel_or_abs, str) or not rel_or_abs:
            raise ValueError('caminho vazio')
        candidate = rel_or_abs if os.path.isabs(rel_or_abs) else os.path.join(self.root, rel_or_abs)
        real = os.path.realpath(candidate)
        if not render_local.contained(self.root, real):
            raise ValueError('caminho fora da raiz do projeto')
        return real

    def confine_workspace(self, rel_or_abs):
        real = self.confine(rel_or_abs)
        workspace = os.path.realpath(os.path.join(self.root, '.workspace'))
        if not (real == workspace or real.startswith(workspace + os.sep)):
            raise ValueError('destino precisa estar em .workspace/')
        return real

    def rel(self, path):
        return os.path.relpath(path, self.root).replace(os.sep, '/')

    def host_ok(self, host_header):
        if not host_header:
            return False
        host = host_header.split(':')[0].lower()
        return host in ('127.0.0.1', 'localhost')

    def origin_ok(self, origin):
        if not origin:
            return False
        parsed = urlparse(origin)
        return parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost') and parsed.port == self.port

    # ---- projetos e perfis ----
    def list_projects(self):
        projects_dir = os.path.join(self.root, 'platform', 'examples', 'projects')
        projects = []
        if os.path.isdir(projects_dir):
            for name in sorted(os.listdir(projects_dir)):
                if not name.endswith('.project.json'):
                    continue
                path = os.path.join(projects_dir, name)
                try:
                    with open(path, 'r', encoding='utf-8') as handle:
                        data = json.load(handle)
                except (OSError, ValueError):
                    continue
                projects.append({
                    'id': data.get('id'), 'name': data.get('name'),
                    'path': self.rel(path), 'outputProfiles': data.get('outputProfiles', []),
                })
        return projects

    def list_profiles(self, project_rel):
        project_abs = self.confine(project_rel)
        node = shutil.which('node')
        if not node:
            raise RuntimeError('node nao encontrado no PATH')
        cli = os.path.join(self.root, 'platform', 'dist', 'src', 'output-profiles-cli.js')
        if not os.path.isfile(cli):
            raise RuntimeError('build da platform ausente; execute npm run build em platform/')
        res = subprocess.run([node, cli, '--project', project_abs, '--json'],
                             capture_output=True, text=True, timeout=60)
        listing = json.loads(res.stdout)
        for profile in listing.get('profiles', []):
            profile['localExport'] = (
                profile.get('mediaKind') == 'video'
                and profile.get('aspectRatio') == '9:16'
                and profile.get('fps') == 30
                and profile.get('availability') == 'allowed'
            )
        return listing

    def list_examples(self):
        examples_dir = os.path.join(self.tools, 'produce', 'examples')
        examples = []
        if os.path.isdir(examples_dir):
            for name in sorted(os.listdir(examples_dir)):
                if name.endswith('.video-request.json'):
                    kind = 'video'
                elif name.endswith('.carousel-request.json'):
                    kind = 'carousel'
                else:
                    continue
                path = os.path.join(examples_dir, name)
                try:
                    with open(path, 'r', encoding='utf-8') as handle:
                        request = json.load(handle)
                except (OSError, ValueError):
                    continue
                examples.append({'name': name, 'path': self.rel(path), 'kind': kind, 'request': request})
        return examples

    # ---- rascunhos ----
    def save_draft(self, path_rel, request):
        target = self.confine_workspace(path_rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        fd, tmp = __import__('tempfile').mkstemp(prefix='.draft-', suffix='.tmp', dir=os.path.dirname(target))
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
                json.dump(request, handle, ensure_ascii=False, indent=2)
                handle.write('\n')
            os.replace(tmp, target)
        except OSError:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise
        return self.rel(target)

    def load_draft(self, path_rel):
        target = self.confine(path_rel)
        with open(target, 'r', encoding='utf-8') as handle:
            return json.load(handle)

    def _write_temp_request(self, request):
        fd, tmp = __import__('tempfile').mkstemp(prefix='studio-request-', suffix='.json', dir=self.drafts_dir)
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(request, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        return tmp

    # ---- previa e exportacao ----
    def _tool_for(self, kind):
        return 'produce_carousel.py' if kind == 'carousel' else 'produce_video.py'

    def preview(self, request, profile=None, kind='video'):
        tmp = self._write_temp_request(request)
        cmd = [sys.executable, os.path.join(self.tools, self._tool_for(kind)),
               '--input', tmp, '--root', self.root, '--plan-only', '--json']
        if profile:
            cmd.extend(['--profile', profile])
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        try:
            payload = json.loads(res.stdout)
        except ValueError:
            payload = {'status': 'error', 'error': res.stderr.strip() or 'previa ilegivel'}
        return {'returncode': res.returncode, 'result': payload}

    def start_export(self, request, output_dir_rel, profile=None, kind='video'):
        output_abs = self.confine_workspace(output_dir_rel)
        tmp = self._write_temp_request(request)
        cmd = [sys.executable, os.path.join(self.tools, self._tool_for(kind)),
               '--input', tmp, '--root', self.root, '--output-dir', output_abs, '--json']
        if profile:
            cmd.extend(['--profile', profile])
        job_id = uuid.uuid4().hex[:12]
        out_path = os.path.join(self.drafts_dir, f'job-{job_id}.out.json')
        err_path = os.path.join(self.drafts_dir, f'job-{job_id}.err.log')
        out_handle = open(out_path, 'w', encoding='utf-8')
        err_handle = open(err_path, 'w', encoding='utf-8')
        proc = subprocess.Popen(cmd, stdout=out_handle, stderr=err_handle,
                                stdin=subprocess.DEVNULL, text=True)
        with self.jobs_lock:
            self.jobs[job_id] = {'proc': proc, 'tmp': tmp, 'outputDir': self.rel(output_abs),
                                 'profile': profile, 'kind': kind, 'status': 'running', 'result': None,
                                 'returncode': None, 'out': out_path, 'err': err_path,
                                 'out_handle': out_handle, 'err_handle': err_handle}
        return job_id

    def export_status(self, job_id):
        with self.jobs_lock:
            job = self.jobs.get(job_id)
        if job is None:
            raise ValueError('job desconhecido')
        # Job ja finalizado: devolve o resultado em cache, sem reler temporarios.
        if job['status'] != 'running':
            return {'status': job['status'], 'returncode': job['returncode'],
                    'outputDir': job['outputDir'], 'profile': job['profile'],
                    'kind': job.get('kind', 'video'), 'result': job['result']}
        proc = job['proc']
        code = proc.poll()
        if code is None:
            return {'status': 'running', 'outputDir': job['outputDir'],
                    'profile': job['profile'], 'kind': job.get('kind', 'video')}
        job['out_handle'].close()
        job['err_handle'].close()
        try:
            with open(job['out'], 'r', encoding='utf-8') as handle:
                result = json.load(handle)
        except (OSError, ValueError):
            try:
                with open(job['err'], 'r', encoding='utf-8') as handle:
                    err = handle.read().strip()
            except OSError:
                err = ''
            result = {'status': 'error', 'error': err or 'exportacao ilegivel'}
        for key in ('tmp', 'out', 'err'):
            path = job.get(key)
            if path and os.path.exists(path):
                os.remove(path)
        status = 'completed' if code == 0 else 'failed'
        with self.jobs_lock:
            job['status'] = status
            job['result'] = result
            job['returncode'] = code
        return {'status': status, 'returncode': code, 'outputDir': job['outputDir'],
                'profile': job['profile'], 'kind': job.get('kind', 'video'), 'result': result}

    # ---- entrega e midia verificada ----
    def read_delivery(self, dir_rel):
        delivery_abs = self.confine(dir_rel)
        index_path = os.path.join(delivery_abs, 'index.json')
        index = None
        if os.path.isfile(index_path):
            with open(index_path, 'r', encoding='utf-8') as handle:
                index = json.load(handle)
        profiles = []
        if os.path.isdir(delivery_abs):
            for name in sorted(os.listdir(delivery_abs)):
                manifest_path = os.path.join(delivery_abs, name, 'delivery-manifest.json')
                if not os.path.isfile(manifest_path):
                    continue
                with open(manifest_path, 'r', encoding='utf-8') as handle:
                    manifest = json.load(handle)
                profiles.append({'profileId': name, 'manifest': manifest})
        return {'dir': self.rel(delivery_abs), 'index': index, 'profiles': profiles}

    def verified_artifact_path(self, dir_rel, profile_id, kind):
        if kind not in ARTIFACT_KINDS:
            raise ValueError('tipo de artefato invalido')
        if not isinstance(profile_id, str) or '/' in profile_id or '\\' in profile_id or profile_id in ('.', '..'):
            raise ValueError('perfil invalido')
        delivery_abs = self.confine(dir_rel)
        manifest_path = os.path.join(delivery_abs, profile_id, 'delivery-manifest.json')
        with open(manifest_path, 'r', encoding='utf-8') as handle:
            manifest = json.load(handle)
        artifact = manifest.get('artifacts', {}).get(ARTIFACT_KINDS[kind])
        if not artifact or not artifact.get('path'):
            raise ValueError('artefato ausente no manifesto')
        target = self.confine(artifact['path'])
        if not os.path.isfile(target):
            raise ValueError('arquivo de artefato ausente')
        return target

    def read_carousel_delivery(self, dir_rel):
        delivery_abs = self.confine(dir_rel)
        index = None
        index_path = os.path.join(delivery_abs, 'index.json')
        if os.path.isfile(index_path):
            with open(index_path, 'r', encoding='utf-8') as handle:
                index = json.load(handle)
        manifest = None
        manifest_path = os.path.join(delivery_abs, 'carousel-manifest.json')
        if os.path.isfile(manifest_path):
            with open(manifest_path, 'r', encoding='utf-8') as handle:
                manifest = json.load(handle)
        return {'dir': self.rel(delivery_abs), 'index': index, 'manifest': manifest}

    def verified_carousel_path(self, dir_rel, kind, index=None):
        delivery_abs = self.confine(dir_rel)
        manifest_path = os.path.join(delivery_abs, 'carousel-manifest.json')
        with open(manifest_path, 'r', encoding='utf-8') as handle:
            manifest = json.load(handle)
        if kind == 'zip':
            path = manifest.get('zip', {}).get('path')
        elif kind == 'card':
            cards = manifest.get('cards', [])
            if index is None or not (0 <= index < len(cards)):
                raise ValueError('indice de card invalido')
            path = cards[index].get('path')
        else:
            raise ValueError('tipo de artefato de carrossel invalido')
        if not path:
            raise ValueError('artefato ausente no manifesto')
        target = self.confine(path)
        if not os.path.isfile(target):
            raise ValueError('arquivo de artefato ausente')
        return target

    def scan_media(self, folder_rel):
        folder = self.confine(folder_rel)
        if not os.path.isdir(folder):
            raise ValueError('pasta de midia ausente')
        found = []
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            lower = name.lower()
            if lower.endswith(IMAGE_EXTENSIONS):
                media_type = 'image'
            elif lower.endswith(VIDEO_EXTENSIONS):
                media_type = 'video'
            else:
                continue
            found.append({'path': self.rel(path), 'name': name, 'type': media_type,
                          'bytes': os.path.getsize(path)})
        return found

    def generate_media(self, request):
        tmp = self._write_temp_request(request)
        cmd = [sys.executable, os.path.join(self.tools, 'make_request_media.py'),
               '--input', tmp, '--root', self.root]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        if res.returncode != 0:
            raise RuntimeError(res.stderr.strip() or 'falha ao gerar midia ficticia')
        return [line for line in res.stdout.splitlines() if line.strip()]


class StudioHandler(BaseHTTPRequestHandler):
    server_version = 'VideoStudio/1.0'
    studio: Studio = None  # injetado pelo servidor

    def log_message(self, fmt, *args):
        sys.stderr.write("[studio] %s - %s\n" % (self.address_string(), fmt % args))

    # ---- helpers de resposta ----
    def send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, code, message):
        self.send_json(code, {'ok': False, 'error': message})

    def read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length) if length else b''
        return json.loads(raw.decode('utf-8')) if raw else {}

    def check_write(self):
        if not self.studio.host_ok(self.headers.get('Host')):
            self.send_error_json(403, 'Host invalido')
            return False
        if not self.studio.origin_ok(self.headers.get('Origin')):
            self.send_error_json(403, 'Origin invalida')
            return False
        return True

    def serve_static(self, name):
        if not name or '/' in name or '\\' in name or name in ('.', '..'):
            self.send_error_json(404, 'arquivo invalido')
            return
        path = os.path.join(self.studio.studio_dir, name)
        if not os.path.isfile(path):
            self.send_error_json(404, 'arquivo ausente')
            return
        ext = os.path.splitext(name)[1].lower()
        with open(path, 'rb') as handle:
            body = handle.read()
        self.send_response(200)
        self.send_header('Content-Type', CONTENT_TYPES.get(ext, 'application/octet-stream'))
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_artifact(self, query):
        kind = query.get('kind', [''])[0]
        try:
            if kind in ('zip', 'card'):
                index = query.get('index', [None])[0]
                index = int(index) if index is not None else None
                target = self.studio.verified_carousel_path(query.get('dir', [''])[0], kind, index)
            else:
                target = self.studio.verified_artifact_path(
                    query.get('dir', [''])[0], query.get('profile', [''])[0], kind)
        except (ValueError, OSError) as exc:
            self.send_error_json(404, str(exc))
            return
        ext = os.path.splitext(target)[1].lower()
        content_type = CONTENT_TYPES.get(ext, 'application/octet-stream')
        size = os.path.getsize(target)
        range_header = self.headers.get('Range')
        start, end = 0, size - 1
        partial = False
        if range_header and range_header.startswith('bytes='):
            try:
                spec = range_header[6:].split('-')
                start = int(spec[0]) if spec[0] else 0
                end = int(spec[1]) if len(spec) > 1 and spec[1] else size - 1
                end = min(end, size - 1)
                partial = True
            except ValueError:
                start, end, partial = 0, size - 1, False
        length = end - start + 1
        self.send_response(206 if partial else 200)
        self.send_header('Content-Type', content_type)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(length))
        if partial:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        with open(target, 'rb') as handle:
            handle.seek(start)
            remaining = length
            while remaining > 0:
                chunk = handle.read(min(65536, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    # ---- rotas ----
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        studio = self.studio
        if not studio.host_ok(self.headers.get('Host')):
            self.send_error_json(403, 'Host invalido')
            return
        try:
            if path == '/' or path == '/index.html':
                self.serve_static('index.html')
            elif path.startswith('/static/'):
                self.serve_static(path[len('/static/'):])
            elif path == '/api/projects':
                self.send_json(200, {'ok': True, 'projects': studio.list_projects()})
            elif path == '/api/profiles':
                self.send_json(200, {'ok': True, 'listing': studio.list_profiles(query.get('project', [''])[0])})
            elif path == '/api/examples':
                self.send_json(200, {'ok': True, 'examples': studio.list_examples()})
            elif path == '/api/draft/load':
                self.send_json(200, {'ok': True, 'request': studio.load_draft(query.get('path', [''])[0])})
            elif path == '/api/export/status':
                self.send_json(200, {'ok': True, **studio.export_status(query.get('job', [''])[0])})
            elif path == '/api/delivery':
                self.send_json(200, {'ok': True, **studio.read_delivery(query.get('dir', [''])[0])})
            elif path == '/api/carousel-delivery':
                self.send_json(200, {'ok': True, **studio.read_carousel_delivery(query.get('dir', [''])[0])})
            elif path == '/media':
                self.serve_artifact(query)
            else:
                self.send_error_json(404, 'rota desconhecida')
        except (ValueError, OSError) as exc:
            self.send_error_json(400, str(exc))
        except RuntimeError as exc:
            self.send_error_json(500, str(exc))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        studio = self.studio
        if not self.check_write():
            return
        try:
            body = self.read_body()
            if path == '/api/draft/save':
                rel = studio.save_draft(body.get('path', ''), body.get('request'))
                self.send_json(200, {'ok': True, 'path': rel})
            elif path == '/api/preview':
                self.send_json(200, {'ok': True, **studio.preview(body.get('request'), body.get('profile'), body.get('kind', 'video'))})
            elif path == '/api/export':
                job_id = studio.start_export(body.get('request'), body.get('outputDir', ''), body.get('profile'), body.get('kind', 'video'))
                self.send_json(200, {'ok': True, 'jobId': job_id})
            elif path == '/api/media/scan':
                self.send_json(200, {'ok': True, 'media': studio.scan_media(body.get('folder', ''))})
            elif path == '/api/media/generate':
                self.send_json(200, {'ok': True, 'written': studio.generate_media(body.get('request'))})
            else:
                self.send_error_json(404, 'rota desconhecida')
        except (ValueError, OSError) as exc:
            self.send_error_json(400, str(exc))
        except RuntimeError as exc:
            self.send_error_json(500, str(exc))


def make_server(root, port):
    studio = Studio(root, port)
    handler = type('BoundStudioHandler', (StudioHandler,), {'studio': studio})
    httpd = ThreadingHTTPServer(('127.0.0.1', port), handler)
    return httpd, studio


def main(argv=None):
    parser = argparse.ArgumentParser(description='Painel local de video (Video Studio)')
    parser.add_argument('--port', type=int, default=8765, help='Porta local (127.0.0.1)')
    parser.add_argument('--root', default=None, help='Raiz do projeto (padrao: git rev-parse --show-toplevel)')
    args = parser.parse_args(argv)
    root = discover_root(args.root)
    httpd, studio = make_server(root, args.port)
    print(f"Video Studio em http://127.0.0.1:{args.port} (raiz: {root})")
    print("Ctrl+C para encerrar.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())