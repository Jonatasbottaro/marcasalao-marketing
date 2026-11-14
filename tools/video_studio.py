"""Painel local de video (Video Studio) sobre o pipeline existente.

Servidor HTTP local (stdlib) que serve uma interface HTML/CSS/JS em tools/studio/
e uma API JSON para cadastrar projetos, gerenciar trabalhos persistentes,
revisar, exportar e retomar videos, carrosseis e motion pelo navegador.

Uso (a partir da raiz do checkout):
    python tools/video_studio.py --port 8765
    python tools/video_studio.py --check [--json]

Seguranca:
- Escuta apenas em 127.0.0.1; valida Host e Origin nas operacoes de escrita.
- Confina entradas e saidas a raiz do projeto (realpath); projetos cadastrados,
  trabalhos, rascunhos, midias geradas e entregas ficam em .workspace/.
- Disponibiliza arquivos de entrega apenas por referencias verificadas nos
  manifestos promovidos (delivery-manifest.json / carousel-manifest.json).
- Processos invocados com argumentos estruturados (sem shell).

O painel produz arquivos locais para revisao; nenhuma aprovacao editorial nem
publicacao. Videos sem faixa de audio.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import make_agenda_media
import make_proof_assets
import make_request_media
import render_local
import delivery_package
import studio_review

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp')
VIDEO_EXTENSIONS = ('.mp4', '.mov')
KEBAB_CASE_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
CONTENT_TYPES = {
    '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8',
    '.mp4': 'video/mp4', '.mov': 'video/quicktime', '.srt': 'text/plain; charset=utf-8',
    '.txt': 'text/plain; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.zip': 'application/zip',
}
ARTIFACT_KINDS = {'video': 'video', 'srt': 'srt', 'narration': 'narration'}
REQUIRED_PLATFORM_MODULES = (
    'validate-project-cli.js',
    'output-profiles-cli.js',
    'compile-video-request.js',
    'validate-carousel-request.js',
    'validate-motion-plan.js',
)
BRAND_EXAMPLES = {
    'marca-salao': {
        'project': 'platform/examples/projects/marca-salao-social.project.json',
        'video': 'tools/produce/examples/marca-salao-social-reel.video-request.json',
        'carousel': 'tools/produce/examples/marca-salao-carousel.carousel-request.json',
        'motionVideo': 'tools/produce/examples/marca-salao-motion.video-request.json',
        'motionPlan': 'tools/produce/examples/marca-salao-motion.motion-plan.json',
    },
    'multitrack-hub': {
        'project': 'platform/examples/projects/multitrack-hub-social.project.json',
        'video': 'tools/produce/examples/multitrack-hub-social-reel.video-request.json',
        'carousel': 'tools/produce/examples/multitrack-hub-carousel.carousel-request.json',
        'motionVideo': 'tools/produce/examples/multitrack-hub-motion.video-request.json',
        'motionPlan': 'tools/produce/examples/multitrack-hub-motion.motion-plan.json',
    },
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def atomic_write_json(target, value):
    """Grava JSON de forma atomica com UTF-8, LF e flush+fsync antes de os.replace."""
    fs = render_local.fs_path
    parent = os.path.dirname(os.path.abspath(target))
    os.makedirs(fs(parent), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.tmp-', suffix='.json', dir=fs(parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(tmp, fs(target))
    except OSError:
        if os.path.exists(fs(tmp)):
            os.remove(fs(tmp))
        raise


def discover_root(explicit=None):
    if explicit:
        return os.path.realpath(explicit)
    try:
        out = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            text=True,
            encoding='utf-8',
            errors='replace',
        ).strip()
        if out:
            return os.path.realpath(out)
    except (OSError, subprocess.CalledProcessError):
        pass
    return os.path.realpath(os.getcwd())


def _tool_version_safe(binary):
    try:
        res = subprocess.run(
            [binary, '-version' if 'ff' in os.path.basename(binary).lower() else '--version'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=10,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.splitlines()[0].strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return 'disponivel'


def check_readiness(root):
    """Verifica Python, Node, build da platform, FFmpeg e FFprobe em portugues."""
    items = []

    py_ver = sys.version.split()[0]
    items.append({
        'id': 'python',
        'label': 'Python',
        'ok': True,
        'detail': f'Python {py_ver} ativo.',
        'instruction': None,
    })

    node = shutil.which('node')
    if node:
        items.append({
            'id': 'node',
            'label': 'Node.js',
            'ok': True,
            'detail': f'{_tool_version_safe(node)} ({node})',
            'instruction': None,
        })
    else:
        items.append({
            'id': 'node',
            'label': 'Node.js',
            'ok': False,
            'detail': 'Comando "node" nao encontrado no PATH.',
            'instruction': 'Instale Node.js >= 22 e garanta o comando "node" no PATH antes de abrir o Studio.',
        })

    dist_src = os.path.join(root, 'platform', 'dist', 'src')
    missing_modules = [
        name for name in REQUIRED_PLATFORM_MODULES
        if not os.path.isfile(os.path.join(dist_src, name))
    ]
    if not missing_modules:
        items.append({
            'id': 'platformBuild',
            'label': 'Build da platform (TypeScript)',
            'ok': True,
            'detail': 'Modulos compilados disponiveis em platform/dist/src/.',
            'instruction': None,
        })
    else:
        items.append({
            'id': 'platformBuild',
            'label': 'Build da platform (TypeScript)',
            'ok': False,
            'detail': 'Arquivos ausentes em platform/dist/src/: ' + ', '.join(missing_modules),
            'instruction': 'Execute "cd platform && npm ci && npm run build && cd .." na raiz do checkout.',
        })

    try:
        render_local.ensure_video_tools(root)
    except Exception:
        pass

    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg:
        items.append({
            'id': 'ffmpeg',
            'label': 'FFmpeg',
            'ok': True,
            'detail': f'{_tool_version_safe(ffmpeg)} ({ffmpeg})',
            'instruction': None,
        })
    else:
        items.append({
            'id': 'ffmpeg',
            'label': 'FFmpeg',
            'ok': False,
            'detail': 'FFmpeg nao encontrado no PATH nem em .workspace/tools/ffmpeg/.',
            'instruction': 'Instale FFmpeg no PATH ou coloque os binarios portateis em .workspace/tools/ffmpeg/.',
        })

    ffprobe = shutil.which('ffprobe')
    if ffprobe:
        items.append({
            'id': 'ffprobe',
            'label': 'FFprobe',
            'ok': True,
            'detail': f'{_tool_version_safe(ffprobe)} ({ffprobe})',
            'instruction': None,
        })
    else:
        items.append({
            'id': 'ffprobe',
            'label': 'FFprobe',
            'ok': False,
            'detail': 'FFprobe nao encontrado no PATH nem em .workspace/tools/ffmpeg/.',
            'instruction': 'Instale FFprobe no PATH ou coloque os binarios portateis em .workspace/tools/ffmpeg/.',
        })

    ready = all(item['ok'] for item in items)
    missing_labels = [item['label'] for item in items if not item['ok']]
    summary = (
        'Ambiente pronto para cadastrar projetos e produzir videos, carrosseis e motion.'
        if ready
        else 'Ambiente incompleto: faltam ' + ', '.join(missing_labels) + '.'
    )
    return {'ready': ready, 'summary': summary, 'items': items}


def _default_output_profiles_from_listing(listing):
    profiles = listing.get('profiles', [])
    video = [p['id'] for p in profiles if p.get('localExportVideo')]
    carousel = [p['id'] for p in profiles if p.get('localExportCarousel')]
    motion = [p['id'] for p in profiles if p.get('localExportMotion')]
    return video, carousel, motion


class Studio:
    """Estado e operacoes do painel, confinadas a raiz do projeto."""

    def __init__(self, root, port):
        self.root = os.path.realpath(root)
        self.port = port
        self.tools = os.path.join(self.root, 'tools')
        self.studio_dir = os.path.join(self.tools, 'studio')
        self.studio_workspace = os.path.join(self.root, '.workspace', 'studio')
        self.projects_dir = os.path.join(self.studio_workspace, 'projects')
        self.works_dir = os.path.join(self.studio_workspace, 'works')
        self.status_dir = os.path.join(self.studio_workspace, 'export-status')
        self.drafts_dir = os.path.join(self.root, '.workspace', 'tmp', 'video-studio', 'drafts')
        self.jobs = {}
        self.jobs_lock = threading.Lock()
        for folder in (self.projects_dir, self.works_dir, self.status_dir, self.drafts_dir):
            os.makedirs(folder, exist_ok=True)

    # ---- prontidao ----
    def check_readiness(self):
        return check_readiness(self.root)

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
    def _scan_project_dir(self, folder, source, source_label):
        items = []
        if not os.path.isdir(folder):
            return items
        for name in sorted(os.listdir(folder)):
            if not name.endswith('.project.json'):
                continue
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, 'r', encoding='utf-8') as handle:
                    data = json.load(handle)
            except (OSError, ValueError):
                continue
            items.append({
                'id': data.get('id'),
                'name': data.get('name'),
                'path': self.rel(path),
                'source': source,
                'sourceLabel': source_label,
                'locale': data.get('locale'),
                'timezone': data.get('timezone'),
                'brandTheme': data.get('brandTheme'),
                'assetRoot': data.get('assetRoot'),
                'contentPolicies': data.get('contentPolicies', {}),
                'outputProfiles': data.get('outputProfiles', []),
            })
        return items

    def list_projects(self):
        registered = self._scan_project_dir(self.projects_dir, 'registered', 'cadastrado')
        examples = self._scan_project_dir(
            os.path.join(self.root, 'platform', 'examples', 'projects'),
            'example',
            'exemplo',
        )
        return registered + examples

    def _validate_project_with_core(self, manifest):
        node = shutil.which('node')
        if not node:
            raise RuntimeError('node nao encontrado no PATH')
        cli = os.path.join(self.root, 'platform', 'dist', 'src', 'validate-project-cli.js')
        if not os.path.isfile(cli):
            raise RuntimeError('build da platform ausente; execute npm run build em platform/')
        fd, tmp = tempfile.mkstemp(prefix='proj-check-', suffix='.project.json', dir=self.drafts_dir)
        os.close(fd)
        try:
            atomic_write_json(tmp, manifest)
            res = subprocess.run(
                [node, cli, '--project', tmp, '--json'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60,
            )
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        try:
            report = json.loads(res.stdout)
        except ValueError:
            raise ValueError(res.stderr.strip() or 'validador de projeto retornou resposta ilegivel')
        if res.returncode != 0 or not report.get('valid'):
            errs = report.get('errors') or []
            details = '; '.join(f"{e.get('path') or e.get('code')}: {e.get('message')}" for e in errs)
            raise ValueError(details or report.get('summary') or 'ProjectManifest invalido')
        return report

    def create_project(self, body):
        if not isinstance(body, dict):
            raise ValueError('dados do projeto invalidos')
        manifest_in = body.get('project') if isinstance(body.get('project'), dict) else body
        project_id = (manifest_in.get('id') or '').strip()
        if not project_id or not KEBAB_CASE_RE.match(project_id):
            raise ValueError('id do projeto deve usar kebab-case (letras minusculas, numeros e hifens)')

        policies_in = manifest_in.get('contentPolicies')
        if not isinstance(policies_in, dict):
            policies_in = {
                'requireApprovedBriefing': True,
                'requireApprovedScript': True,
                'prohibitPersonalData': True,
                'requireFunctionalEvidence': True,
            }
        else:
            policies_in = {
                'requireApprovedBriefing': bool(policies_in.get('requireApprovedBriefing', True)),
                'requireApprovedScript': bool(policies_in.get('requireApprovedScript', True)),
                'prohibitPersonalData': bool(policies_in.get('prohibitPersonalData', True)),
                'requireFunctionalEvidence': bool(policies_in.get('requireFunctionalEvidence', True)),
            }

        profiles = manifest_in.get('outputProfiles')
        if not isinstance(profiles, list):
            profiles = []

        manifest = {
            'schemaVersion': manifest_in.get('schemaVersion', 1),
            'id': project_id,
            'name': (manifest_in.get('name') or '').strip(),
            'locale': (manifest_in.get('locale') or 'pt-BR').strip(),
            'timezone': (manifest_in.get('timezone') or 'America/Sao_Paulo').strip(),
            'brandTheme': (manifest_in.get('brandTheme') or project_id).strip(),
            'assetRoot': (manifest_in.get('assetRoot') or f'.workspace/studio/projects/{project_id}/assets').strip(),
            'contentPolicies': policies_in,
            'outputProfiles': [str(p).strip() for p in profiles if str(p).strip()],
        }

        target = self.confine_workspace(os.path.join('.workspace', 'studio', 'projects', f'{project_id}.project.json'))
        if os.path.exists(target) and not body.get('overwrite'):
            raise ValueError(f'ja existe um projeto cadastrado com id "{project_id}"')
        existing_examples = {p['id'] for p in self._scan_project_dir(
            os.path.join(self.root, 'platform', 'examples', 'projects'), 'example', 'exemplo')}
        if project_id in existing_examples and not body.get('overwrite'):
            raise ValueError(f'id "{project_id}" pertence a um projeto de exemplo versionado; escolha outro id')

        report = self._validate_project_with_core(manifest)
        atomic_write_json(target, manifest)
        return {
            'path': self.rel(target),
            'project': {
                **manifest,
                'path': self.rel(target),
                'source': 'registered',
                'sourceLabel': 'cadastrado',
            },
            'report': report,
        }

    def list_profiles(self, project_rel=None, module=None):
        if module and module not in ('video', 'carousel', 'motion'):
            raise ValueError('modulo invalido')
        node = shutil.which('node')
        if not node:
            raise RuntimeError('node nao encontrado no PATH')
        cli = os.path.join(self.root, 'platform', 'dist', 'src', 'output-profiles-cli.js')
        if not os.path.isfile(cli):
            raise RuntimeError('build da platform ausente; execute npm run build em platform/')
        cmd = [node, cli, '--json']
        if project_rel:
            project_abs = self.confine(project_rel)
            cmd.extend(['--project', project_abs])
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        if not res.stdout.strip():
            raise ValueError(res.stderr.strip() or 'falha ao listar perfis')
        listing = json.loads(res.stdout)
        if res.returncode != 0:
            errs = listing.get('diagnostics') or []
            msg = '; '.join(f"{e.get('code')}: {e.get('message')}" for e in errs) or listing.get('summary')
            raise ValueError(msg or 'projeto rejeitado ao consultar perfis')
        for profile in listing.get('profiles', []):
            allowed = profile.get('availability') == 'allowed'
            video_ok = (
                allowed
                and profile.get('mediaKind') == 'video'
                and profile.get('aspectRatio') == '9:16'
                and profile.get('fps') == 30
            )
            carousel_ok = (
                allowed
                and profile.get('mediaKind') == 'image'
                and profile.get('aspectRatio') == '1:1'
            )
            motion_ok = video_ok
            modules = []
            if video_ok:
                modules.append('video')
            if carousel_ok:
                modules.append('carousel')
            if motion_ok:
                modules.append('motion')
            profile['localExport'] = video_ok
            profile['localExportVideo'] = video_ok
            profile['localExportCarousel'] = carousel_ok
            profile['localExportMotion'] = motion_ok
            profile['compatibleModules'] = modules
        if module:
            listing['compatibleProfiles'] = [
                p for p in listing.get('profiles', [])
                if module in p.get('compatibleModules', [])
            ]
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

    # ---- persistencia de status de exportacao ----
    def _normalize_rel(self, dir_rel):
        target = self.confine(dir_rel)
        return self.rel(target)

    def _export_status_path(self, dir_rel):
        norm = self._normalize_rel(dir_rel)
        digest = hashlib.sha1(norm.encode('utf-8')).hexdigest()[:16]
        return os.path.join(self.status_dir, f'{digest}.json')

    def _write_export_status(self, dir_rel, payload):
        path = self._export_status_path(dir_rel)
        atomic_write_json(path, payload)
        return path

    def _read_export_status(self, dir_rel):
        try:
            path = self._export_status_path(dir_rel)
        except ValueError:
            return None
        if not os.path.isfile(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return None
        if data.get('status') == 'running':
            job_id = data.get('jobId')
            with self.jobs_lock:
                job = self.jobs.get(job_id)
                still_running = job is not None and job.get('status') == 'running' and job['proc'].poll() is None
            if not still_running:
                data['status'] = 'interrupted'
                data['error'] = 'A exportacao em andamento foi interrompida quando o painel foi fechado. Tente novamente.'
                data['interruptedAt'] = now_iso()
                atomic_write_json(path, data)
        return data

    # ---- trabalhos persistentes ----
    def work_paths(self, work_id):
        if not isinstance(work_id, str) or not KEBAB_CASE_RE.match(work_id):
            raise ValueError('id do trabalho deve usar kebab-case (letras minusculas, numeros e hifens)')
        base = f'.workspace/studio/works/{work_id}'
        return {
            'workDir': base,
            'workFile': f'{base}/work.json',
            'mediaDir': f'{base}/media',
            'videoDraft': f'{base}/drafts/video.request.json',
            'carouselDraft': f'{base}/drafts/carousel.request.json',
            'motionPlan': f'{base}/drafts/motion.plan.json',
            'editorialFile': f'{base}/editorial.json',
            'reviewStateFile': f'{base}/review-state.json',
            'videoDeliveryDir': f'{base}/deliveries/video',
            'carouselDeliveryDir': f'{base}/deliveries/carousel',
            'motionDeliveryDir': f'{base}/deliveries/motion',
            'packageDeliveryDir': f'{base}/deliveries/package',
        }

    def _delivery_badge_summary(self, video_dir, carousel_dir, motion_dir, work_id=None):
        v = self.read_delivery(video_dir)
        c = self.read_carousel_delivery(carousel_dir)
        m = self.read_delivery(motion_dir)
        v_valid = sum(
            1 for p in (v.get('index') or {}).get('profiles', [])
            if p.get('lastValidDelivery')
        ) or len(v.get('profiles', []))
        c_valid = bool(c.get('manifest') and (c.get('index') or {}).get('lastValidDelivery', True))
        m_valid = sum(
            1 for p in (m.get('index') or {}).get('profiles', [])
            if p.get('lastValidDelivery')
        ) or len(m.get('profiles', []))
        pkg_valid = False
        if work_id:
            try:
                pkg_valid = bool(delivery_package.read_package_delivery(self, work_id).get('available'))
            except (ValueError, OSError):
                pkg_valid = False
        return {
            'videoValidCount': v_valid,
            'carouselValid': c_valid,
            'motionValidCount': m_valid,
            'packageValid': pkg_valid,
            'videoLastStatus': (v.get('lastExportStatus') or {}).get('status'),
            'carouselLastStatus': (c.get('lastExportStatus') or {}).get('status'),
            'motionLastStatus': (m.get('lastExportStatus') or {}).get('status'),
        }

    def list_works(self):
        works = []
        if not os.path.isdir(self.works_dir):
            return works
        for entry in sorted(os.listdir(self.works_dir)):
            work_file = os.path.join(self.works_dir, entry, 'work.json')
            if not os.path.isfile(render_local.fs_path(work_file)):
                continue
            try:
                with open(render_local.fs_path(work_file), 'r', encoding='utf-8') as handle:
                    work = json.load(handle)
            except (OSError, ValueError):
                continue
            paths = work.get('paths', {})
            work_id = work.get('id') or entry
            work['summary'] = self._delivery_badge_summary(
                paths.get('videoDeliveryDir', f'.workspace/studio/works/{entry}/deliveries/video'),
                paths.get('carouselDeliveryDir', f'.workspace/studio/works/{entry}/deliveries/carousel'),
                paths.get('motionDeliveryDir', f'.workspace/studio/works/{entry}/deliveries/motion'),
                work_id=work_id if KEBAB_CASE_RE.match(str(work_id)) else None,
            )
            works.append(work)
        works.sort(key=lambda w: w.get('updatedAt', ''), reverse=True)
        return works

    def _load_json(self, rel_path):
        target = self.confine(rel_path)
        with open(render_local.fs_path(target), 'r', encoding='utf-8') as handle:
            return json.load(handle)

    def create_work(self, body):
        if not isinstance(body, dict):
            raise ValueError('dados do trabalho invalidos')
        work_id = (body.get('id') or '').strip()
        paths = self.work_paths(work_id)
        work_abs = self.confine_workspace(paths['workFile'])
        if os.path.exists(work_abs) and not body.get('overwrite'):
            raise ValueError(f'ja existe um trabalho com o id "{work_id}"; escolha outro id ou reabra o existente')

        project_rel = (body.get('project') or '').strip()
        if not project_rel:
            raise ValueError('selecione um projeto para criar o trabalho')
        project_abs = self.confine(project_rel)
        if not os.path.isfile(project_abs):
            raise ValueError('ProjectManifest selecionado nao encontrado')
        with open(project_abs, 'r', encoding='utf-8') as handle:
            project_doc = json.load(handle)
        self._validate_project_with_core(project_doc)

        listing = self.list_profiles(project_rel)
        video_profiles, carousel_profiles, _ = _default_output_profiles_from_listing(listing)
        if not video_profiles and not carousel_profiles:
            raise ValueError('projeto nao permite nenhum destino local compativel (video 9:16@30 ou imagem 1:1)')

        name = (body.get('name') or work_id).strip()
        template = (body.get('template') or 'blank').strip()
        media_dir_rel = paths['mediaDir']
        media_dir_abs = self.confine_workspace(media_dir_rel)
        for p_key in ('mediaDir', 'videoDeliveryDir', 'carouselDeliveryDir', 'motionDeliveryDir'):
            os.makedirs(self.confine_workspace(paths[p_key]), exist_ok=True)

        if template in BRAND_EXAMPLES:
            seed = BRAND_EXAMPLES[template]
            ex_video = self._load_json(seed['video'])
            ex_carousel = self._load_json(seed['carousel'])
            ex_motion_plan = self._load_json(seed['motionPlan'])

            # Gera midias ficticias compartilhadas dentro da pasta media/ do trabalho.
            agenda_rel = f'{media_dir_rel}/agenda.png'
            make_agenda_media.write_agenda_png(self.confine_workspace(agenda_rel))

            shared_media = []
            for item in ex_video.get('media', []):
                filename = os.path.basename(item['path'])
                shared_media.append({
                    'id': item['id'],
                    'path': f'{media_dir_rel}/{filename}',
                    'type': 'image',
                    'origin': item.get('origin', 'synthetic-demo'),
                    'license': item.get('license', 'owned-synthetic'),
                })
            shared_media.append({
                'id': 'agenda',
                'path': agenda_rel,
                'type': 'image',
                'origin': 'synthetic-demo',
                'license': 'owned-synthetic',
            })

            scenes = json.loads(json.dumps(ex_video.get('scenes', [])))
            if scenes:
                # Vincula a primeira cena sem zoom a agenda para possibilitar contorno animado direto,
                # preservando tambem as demais cenas para demonstracao multi-cena e zoom.
                first_no_zoom = next((s for s in scenes if s.get('motionIntent', 'none') == 'none'), None)
                if first_no_zoom is not None and not any(s.get('mediaId') == 'agenda' for s in scenes):
                    first_no_zoom['mediaId'] = 'agenda'

            video_req = {
                'schemaVersion': 1,
                'id': f'{work_id}-video',
                'project': project_rel,
                'title': ex_video.get('title', name),
                'locale': ex_video.get('locale', project_doc.get('locale', 'pt-BR')),
                'profiles': video_profiles or ex_video.get('profiles', []),
                'visualStyle': ex_video.get('visualStyle', {
                    'schemaVersion': 1,
                    'id': f'{work_id}-estilo',
                    'title': {
                        'textColor': '#FFFFFF', 'outlineColor': '#000000',
                        'fontSize': 44, 'marginTop': 170, 'marginHorizontal': 70,
                    },
                }),
                'media': [m for m in shared_media if m['id'] != 'agenda' or any(s['mediaId'] == 'agenda' for s in scenes)],
                'scenes': scenes,
            }
            make_request_media.generate_request_media(
                {**video_req, 'media': [m for m in video_req['media'] if m['id'] != 'agenda']},
                self.root,
            )

            carousel_media = []
            for item in ex_carousel.get('media', []):
                filename = os.path.basename(item['path'])
                carousel_media.append({
                    'id': item['id'],
                    'path': f'{media_dir_rel}/{filename}',
                    'type': 'image',
                    'origin': item.get('origin', 'synthetic-demo'),
                    'license': item.get('license', 'owned-synthetic'),
                })
            # Inclui a midia da abertura do video para reutilizacao entre pecas.
            if not any(m['id'] == 'agenda' for m in carousel_media):
                carousel_media.append({
                    'id': 'agenda',
                    'path': agenda_rel,
                    'type': 'image',
                    'origin': 'synthetic-demo',
                    'license': 'owned-synthetic',
                })

            carousel_req = {
                'schemaVersion': 1,
                'id': f'{work_id}-carrossel',
                'project': project_rel,
                'profile': carousel_profiles[0] if carousel_profiles else ex_carousel.get('profile', 'instagram-feed-image-square'),
                'title': ex_carousel.get('title', name),
                'media': carousel_media,
                'cards': ex_carousel.get('cards', []),
            }
            make_request_media.generate_request_media(
                {**carousel_req, 'media': [m for m in carousel_req['media'] if m['id'] != 'agenda']},
                self.root,
            )

            target_scene = next(
                (s['id'] for s in video_req['scenes'] if s.get('motionIntent', 'none') == 'none'),
                video_req['scenes'][0]['id'],
            )
            base_effect = dict((ex_motion_plan.get('effects') or [{}])[0])
            base_effect['sceneId'] = target_scene
            base_effect.setdefault('region', make_agenda_media.slot_region(1))
            base_effect.setdefault('color', '#FFD700')
            base_effect.setdefault('thickness', 6)
            base_effect['startMs'] = 400
            target_duration = next((s['durationMs'] for s in video_req['scenes'] if s['id'] == target_scene), 4000)
            base_effect['endMs'] = min(3000, max(1000, target_duration - 200))
            motion_plan = {
                'schemaVersion': 1,
                'requestId': video_req['id'],
                'effects': [base_effect],
            }
        else:
            abertura_rel = f'{media_dir_rel}/abertura.png'
            agenda_rel = f'{media_dir_rel}/agenda.png'
            make_proof_assets.write_scene_png(self.confine_workspace(abertura_rel), work_id, 'abertura', 1)
            make_agenda_media.write_agenda_png(self.confine_workspace(agenda_rel))

            shared = [
                {'id': 'abertura', 'path': abertura_rel, 'type': 'image', 'origin': 'studio-work', 'license': 'pending'},
                {'id': 'agenda', 'path': agenda_rel, 'type': 'image', 'origin': 'studio-work', 'license': 'pending'},
            ]
            video_req = {
                'schemaVersion': 1,
                'id': f'{work_id}-video',
                'project': project_rel,
                'title': name,
                'locale': project_doc.get('locale', 'pt-BR'),
                'profiles': video_profiles or ['instagram-reels-video'],
                'visualStyle': {
                    'schemaVersion': 1,
                    'id': f'{work_id}-estilo',
                    'title': {
                        'textColor': '#FFFFFF', 'outlineColor': '#000000',
                        'fontSize': 44, 'marginTop': 170, 'marginHorizontal': 70,
                    },
                },
                'media': json.loads(json.dumps(shared)),
                'scenes': [
                    {
                        'id': 'cena-1',
                        'durationMs': 4000,
                        'mediaId': 'abertura',
                        'caption': f'Conheca {name}',
                        'narration': f'Abertura do trabalho {name}.',
                        'title': name,
                        'narrativeFunction': 'hook',
                        'motionIntent': 'none',
                    },
                    {
                        'id': 'cena-2',
                        'durationMs': 4000,
                        'mediaId': 'agenda',
                        'caption': 'Confira os detalhes',
                        'narration': 'Segunda cena com destaque visual.',
                        'title': 'Detalhes',
                        'narrativeFunction': 'demonstration',
                        'motionIntent': 'none',
                    },
                ],
            }
            carousel_req = {
                'schemaVersion': 1,
                'id': f'{work_id}-carrossel',
                'project': project_rel,
                'profile': carousel_profiles[0] if carousel_profiles else 'instagram-feed-image-square',
                'title': f'{name} — Carrossel',
                'media': json.loads(json.dumps(shared)),
                'cards': [
                    {'id': 'capa', 'title': name, 'body': 'Apresentacao inicial', 'mediaId': 'abertura'},
                    {'id': 'conteudo', 'title': 'Destaques', 'body': 'Organizacao e clareza', 'mediaId': 'agenda'},
                    {'id': 'fechamento', 'title': 'Saiba mais', 'body': 'Confira na descricao'},
                ],
            }
            motion_plan = {
                'schemaVersion': 1,
                'requestId': video_req['id'],
                'effects': [
                    {
                        'sceneId': 'cena-2',
                        'region': make_agenda_media.slot_region(1),
                        'color': '#FFD700',
                        'thickness': 6,
                        'startMs': 500,
                        'endMs': 3000,
                        'fadeInMs': 200,
                        'fadeOutMs': 200,
                    },
                ],
            }

        ts = now_iso()
        work_doc = {
            'schemaVersion': 1,
            'id': work_id,
            'name': name,
            'project': project_rel,
            'projectId': project_doc.get('id'),
            'createdAt': ts,
            'updatedAt': ts,
            'paths': paths,
        }
        atomic_write_json(self.confine_workspace(paths['videoDraft']), video_req)
        atomic_write_json(self.confine_workspace(paths['carouselDraft']), carousel_req)
        atomic_write_json(self.confine_workspace(paths['motionPlan']), motion_plan)
        atomic_write_json(work_abs, work_doc)
        return self.open_work(work_id)

    def create_demo_work(self, body=None):
        body = body or {}
        brand = body.get('brand', 'marca-salao')
        if brand not in BRAND_EXAMPLES:
            brand = 'marca-salao'
        project_rel = body.get('project') or BRAND_EXAMPLES[brand]['project']
        base_id = (body.get('id') or f'demo-{brand}').strip()
        if not KEBAB_CASE_RE.match(base_id):
            base_id = f'demo-{brand}'
        candidate = base_id
        suffix = 2
        while os.path.exists(self.confine_workspace(f'.workspace/studio/works/{candidate}/work.json')):
            candidate = f'{base_id}-{suffix}'
            suffix += 1
        return self.create_work({
            'id': candidate,
            'name': body.get('name') or f'Demonstracao guiada ({brand})',
            'project': project_rel,
            'template': brand,
        })

    def open_work(self, work_id):
        fs = render_local.fs_path
        paths = self.work_paths(work_id)
        work_abs = self.confine_workspace(paths['workFile'])
        if not os.path.isfile(fs(work_abs)):
            raise ValueError(f'trabalho nao encontrado: {work_id}')
        with open(fs(work_abs), 'r', encoding='utf-8') as handle:
            work = json.load(handle)
        wpaths = studio_review.merged_work_paths(self, work_id, work)
        work_view = {**work, 'paths': wpaths}
        video_req = self._load_json(wpaths['videoDraft'])
        carousel_req = self._load_json(wpaths['carouselDraft'])
        motion_plan = self._load_json(wpaths['motionPlan'])
        work_media = []
        media_dir_abs = self.confine_workspace(wpaths['mediaDir'])
        if os.path.isdir(fs(media_dir_abs)):
            work_media = self.scan_media(wpaths['mediaDir'])
        deliveries = {
            'video': self.read_delivery(wpaths['videoDeliveryDir']),
            'carousel': self.read_carousel_delivery(wpaths['carouselDeliveryDir']),
            'motion': self.read_delivery(wpaths['motionDeliveryDir']),
        }
        listing = self.list_profiles(work['project'])
        review = studio_review.build_review_overview(self, work_id)
        package_delivery = delivery_package.read_package_delivery(self, work_id)
        return {
            'work': work_view,
            'videoRequest': video_req,
            'carouselRequest': carousel_req,
            'motionPlan': motion_plan,
            'workMedia': work_media,
            'deliveries': deliveries,
            'listing': listing,
            'review': review,
            'packageDelivery': package_delivery,
        }

    def save_work(self, body):
        if not isinstance(body, dict):
            raise ValueError('payload de trabalho invalido')
        fs = render_local.fs_path
        work_id = (body.get('workId') or body.get('id') or '').strip()
        paths = self.work_paths(work_id)
        work_abs = self.confine_workspace(paths['workFile'])
        if not os.path.isfile(fs(work_abs)):
            raise ValueError(f'trabalho nao encontrado: {work_id}')
        with open(fs(work_abs), 'r', encoding='utf-8') as handle:
            work = json.load(handle)
        wpaths = studio_review.merged_work_paths(self, work_id, work)
        work['paths'] = wpaths

        if isinstance(body.get('name'), str) and body['name'].strip():
            work['name'] = body['name'].strip()
        if isinstance(body.get('project'), str) and body['project'].strip():
            proj_abs = self.confine(body['project'].strip())
            if not os.path.isfile(proj_abs):
                raise ValueError('ProjectManifest ausente')
            with open(proj_abs, 'r', encoding='utf-8') as handle:
                pdoc = json.load(handle)
            work['project'] = self.rel(proj_abs)
            work['projectId'] = pdoc.get('id')

        if isinstance(body.get('videoRequest'), dict):
            vreq = dict(body['videoRequest'])
            vreq['project'] = work['project']
            atomic_write_json(self.confine_workspace(wpaths['videoDraft']), vreq)
        if isinstance(body.get('carouselRequest'), dict):
            creq = dict(body['carouselRequest'])
            creq['project'] = work['project']
            atomic_write_json(self.confine_workspace(wpaths['carouselDraft']), creq)
        if isinstance(body.get('motionPlan'), dict):
            mplan = dict(body['motionPlan'])
            if isinstance(body.get('videoRequest'), dict) and body['videoRequest'].get('id'):
                mplan['requestId'] = body['videoRequest']['id']
            atomic_write_json(self.confine_workspace(wpaths['motionPlan']), mplan)

        work['updatedAt'] = now_iso()
        atomic_write_json(work_abs, work)
        return {'work': work}

    # ---- rascunhos avulsos (compatibilidade) ----
    def save_draft(self, path_rel, request):
        target = self.confine_workspace(path_rel)
        atomic_write_json(target, request)
        return self.rel(target)

    def load_draft(self, path_rel):
        target = self.confine(path_rel)
        with open(target, 'r', encoding='utf-8') as handle:
            return json.load(handle)

    def _write_temp_request(self, request):
        fd, tmp = tempfile.mkstemp(prefix='studio-request-', suffix='.json', dir=self.drafts_dir)
        os.close(fd)
        atomic_write_json(tmp, request)
        return tmp

    # ---- previa e exportacao ----
    def _tool_for(self, kind):
        return 'produce_carousel.py' if kind == 'carousel' else 'produce_video.py'

    def preview(self, request, profile=None, kind='video', motion_plan=None):
        tmp = self._write_temp_request(request)
        plan_tmp = None
        cmd = [sys.executable, os.path.join(self.tools, self._tool_for(kind)),
               '--input', tmp, '--root', self.root, '--plan-only', '--json']
        if profile:
            cmd.extend(['--profile', profile])
        if motion_plan is not None and kind == 'video':
            plan_tmp = self._write_temp_request(motion_plan)
            cmd.extend(['--motion-plan', plan_tmp])
        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
        finally:
            for p in (tmp, plan_tmp):
                if p and os.path.exists(p):
                    os.remove(p)
        try:
            payload = json.loads(res.stdout)
        except ValueError:
            payload = {'status': 'error', 'error': res.stderr.strip() or 'previa ilegivel'}
        return {'returncode': res.returncode, 'result': payload}

    def _finalize_job(self, job):
        with job['lock']:
            if job['status'] != 'running':
                return {
                    'status': job['status'],
                    'returncode': job['returncode'],
                    'outputDir': job['outputDir'],
                    'profile': job['profile'],
                    'kind': job.get('kind', 'video'),
                    'result': job['result'],
                }
            code = job['proc'].poll()
            if code is None:
                return None
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
            for key in ('tmp', 'plan_tmp', 'out', 'err'):
                path = job.get(key)
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            status = 'completed' if code == 0 else 'failed'
            error_summary = None
            if status != 'completed':
                error_summary = (
                    result.get('error')
                    or next(
                        (
                            p.get('failureCode') or p.get('error')
                            for p in (result.get('profiles') or [])
                            if p.get('status') != 'completed'
                        ),
                        None,
                    )
                    or f'exportacao falhou (codigo {code})'
                )
            elif job.get('workId') and job.get('exportLineage'):
                lineage_job = dict(job)
                lineage_job['status'] = status
                lineage_job['result'] = result
                studio_review.record_export_lineage(self, lineage_job)

            job['status'] = status
            job['result'] = result
            job['returncode'] = code
            self._write_export_status(job['outputDir'], {
                'jobId': job['jobId'],
                'kind': job.get('kind', 'video'),
                'profile': job.get('profile'),
                'outputDir': job['outputDir'],
                'workId': job.get('workId'),
                'status': status,
                'returncode': code,
                'error': error_summary,
                'result': result,
                'startedAt': job.get('startedAt'),
                'finishedAt': now_iso(),
            })
            return {
                'status': status,
                'returncode': code,
                'outputDir': job['outputDir'],
                'profile': job['profile'],
                'kind': job.get('kind', 'video'),
                'result': result,
            }

    def _watch_job(self, job):
        try:
            job['proc'].wait()
        finally:
            self._finalize_job(job)

    def start_export(self, request, output_dir_rel, profile=None, kind='video', motion_plan=None, work_id=None):
        export_lineage = None
        if work_id:
            save_payload = {'workId': work_id}
            if kind == 'carousel':
                save_payload['carouselRequest'] = request
            else:
                save_payload['videoRequest'] = request
                if motion_plan is not None:
                    save_payload['motionPlan'] = motion_plan
            saved_work = self.save_work(save_payload)['work']
            req_snapshot = json.loads(json.dumps(request))
            if isinstance(req_snapshot, dict):
                req_snapshot['project'] = saved_work['project']
            plan_snapshot = json.loads(json.dumps(motion_plan)) if motion_plan is not None else None
            if isinstance(plan_snapshot, dict) and isinstance(req_snapshot, dict) and req_snapshot.get('id'):
                plan_snapshot['requestId'] = req_snapshot['id']
            export_lineage = {
                'modality': 'carousel' if kind == 'carousel' else ('motion' if motion_plan is not None else 'video'),
                'request': req_snapshot,
                'motionPlan': plan_snapshot,
                'mediaOrigins': studio_review._hash_media_list(self, (req_snapshot or {}).get('media', [])),
            }

        output_abs = self.confine_workspace(output_dir_rel)
        out_rel = self.rel(output_abs)
        tmp = self._write_temp_request(request)
        plan_tmp = None
        cmd = [sys.executable, os.path.join(self.tools, self._tool_for(kind)),
               '--input', tmp, '--root', self.root, '--output-dir', output_abs, '--json']
        if profile:
            cmd.extend(['--profile', profile])
        if motion_plan is not None and kind == 'video':
            plan_tmp = self._write_temp_request(motion_plan)
            cmd.extend(['--motion-plan', plan_tmp])
        job_id = uuid.uuid4().hex[:12]
        out_path = os.path.join(self.drafts_dir, f'job-{job_id}.out.json')
        err_path = os.path.join(self.drafts_dir, f'job-{job_id}.err.log')
        out_handle = open(out_path, 'w', encoding='utf-8')
        err_handle = open(err_path, 'w', encoding='utf-8')
        proc = subprocess.Popen(
            cmd, stdout=out_handle, stderr=err_handle, stdin=subprocess.DEVNULL, text=True,
            encoding='utf-8', errors='replace',
        )
        started_at = now_iso()
        job = {
            'jobId': job_id, 'proc': proc, 'tmp': tmp, 'plan_tmp': plan_tmp,
            'outputDir': out_rel, 'profile': profile, 'kind': kind, 'workId': work_id,
            'exportLineage': export_lineage,
            'status': 'running', 'result': None, 'returncode': None,
            'out': out_path, 'err': err_path, 'out_handle': out_handle, 'err_handle': err_handle,
            'startedAt': started_at, 'lock': threading.Lock(),
        }
        self._write_export_status(out_rel, {
            'jobId': job_id,
            'kind': kind,
            'profile': profile,
            'outputDir': out_rel,
            'workId': work_id,
            'status': 'running',
            'pid': proc.pid,
            'startedAt': started_at,
        })
        with self.jobs_lock:
            self.jobs[job_id] = job
        watcher = threading.Thread(target=self._watch_job, args=(job,), daemon=True)
        watcher.start()
        return job_id

    def export_status(self, job_id):
        with self.jobs_lock:
            job = self.jobs.get(job_id)
        if job is None:
            raise ValueError('job desconhecido')
        finalized = self._finalize_job(job)
        if finalized is None:
            return {'status': 'running', 'outputDir': job['outputDir'],
                    'profile': job['profile'], 'kind': job.get('kind', 'video')}
        return finalized

    # ---- entrega e midia verificada ----
    def read_delivery(self, dir_rel):
        fs = render_local.fs_path
        delivery_abs = self.confine(dir_rel)
        rel_dir = self.rel(delivery_abs)
        index_path = os.path.join(delivery_abs, 'index.json')
        index = None
        if os.path.isfile(fs(index_path)):
            with open(fs(index_path), 'r', encoding='utf-8') as handle:
                index = json.load(handle)
        profiles = []
        if os.path.isdir(fs(delivery_abs)):
            for name in sorted(os.listdir(fs(delivery_abs))):
                manifest_path = os.path.join(delivery_abs, name, 'delivery-manifest.json')
                if not os.path.isfile(fs(manifest_path)):
                    continue
                with open(fs(manifest_path), 'r', encoding='utf-8') as handle:
                    manifest = json.load(handle)
                profiles.append({'profileId': name, 'manifest': manifest})
        last_export = self._read_export_status(rel_dir)
        return {'dir': rel_dir, 'index': index, 'profiles': profiles, 'lastExportStatus': last_export}

    def verified_artifact_path(self, dir_rel, profile_id, kind):
        if kind not in ARTIFACT_KINDS:
            raise ValueError('tipo de artefato invalido')
        if not isinstance(profile_id, str) or '/' in profile_id or '\\' in profile_id or profile_id in ('.', '..'):
            raise ValueError('perfil invalido')
        fs = render_local.fs_path
        delivery_abs = self.confine(dir_rel)
        manifest_path = os.path.join(delivery_abs, profile_id, 'delivery-manifest.json')
        with open(fs(manifest_path), 'r', encoding='utf-8') as handle:
            manifest = json.load(handle)
        artifact = manifest.get('artifacts', {}).get(ARTIFACT_KINDS[kind])
        if not artifact or not artifact.get('path'):
            raise ValueError('artefato ausente no manifesto')
        target = self.confine(artifact['path'])
        if not os.path.isfile(fs(target)):
            raise ValueError('arquivo de artefato ausente')
        return target

    def read_carousel_delivery(self, dir_rel):
        fs = render_local.fs_path
        delivery_abs = self.confine(dir_rel)
        rel_dir = self.rel(delivery_abs)
        index = None
        index_path = os.path.join(delivery_abs, 'index.json')
        if os.path.isfile(fs(index_path)):
            with open(fs(index_path), 'r', encoding='utf-8') as handle:
                index = json.load(handle)
        manifest = None
        manifest_path = os.path.join(delivery_abs, 'carousel-manifest.json')
        if os.path.isfile(fs(manifest_path)):
            with open(fs(manifest_path), 'r', encoding='utf-8') as handle:
                manifest = json.load(handle)
        last_export = self._read_export_status(rel_dir)
        if last_export and last_export.get('status') in ('failed', 'interrupted') and isinstance(index, dict):
            index = dict(index)
            index['lastAttempt'] = {
                'status': last_export.get('status'),
                'error': last_export.get('error'),
                'finishedAt': last_export.get('finishedAt') or last_export.get('interruptedAt'),
            }
        return {'dir': rel_dir, 'index': index, 'manifest': manifest, 'lastExportStatus': last_export}

    def verified_carousel_path(self, dir_rel, kind, index=None):
        fs = render_local.fs_path
        delivery_abs = self.confine(dir_rel)
        manifest_path = os.path.join(delivery_abs, 'carousel-manifest.json')
        with open(fs(manifest_path), 'r', encoding='utf-8') as handle:
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
        if not os.path.isfile(fs(target)):
            raise ValueError('arquivo de artefato ausente')
        return target

    # ---- revisao editorial e pacote ZIP ----
    def get_review_overview(self, work_id):
        overview = studio_review.build_review_overview(self, work_id)
        pkg = delivery_package.read_package_delivery(self, work_id)
        return {**overview, 'packageDelivery': pkg}

    def save_editorial(self, body):
        work_id = (body.get('workId') or body.get('id') or '').strip() if isinstance(body, dict) else ''
        overview = studio_review.save_editorial(self, work_id, body)
        pkg = delivery_package.read_package_delivery(self, work_id)
        return {**overview, 'packageDelivery': pkg}

    def decide_review(self, body):
        work_id = (body.get('workId') or body.get('id') or '').strip() if isinstance(body, dict) else ''
        overview = studio_review.record_review_decision(self, work_id, body)
        pkg = delivery_package.read_package_delivery(self, work_id)
        return {**overview, 'packageDelivery': pkg}

    def read_artifact_text(self, work_id, modality, profile_id, kind):
        return studio_review.read_verified_artifact_text(self, work_id, modality, profile_id, kind)

    def create_package(self, body):
        work_id = (body.get('workId') or body.get('id') or '').strip() if isinstance(body, dict) else ''
        pkg = delivery_package.build_and_promote_package(self, work_id, body)
        overview = studio_review.build_review_overview(self, work_id)
        return {**overview, 'packageDelivery': pkg}

    def read_package_delivery(self, work_id):
        return delivery_package.read_package_delivery(self, work_id)

    def verified_package_download(self, work_id):
        return delivery_package.verified_package_zip_path(self, work_id)

    def source_media_path(self, path_rel):
        """Caminho de midia de origem (imagem) confinado a raiz, para o editor."""
        target = self.confine(path_rel)
        if os.path.splitext(target)[1].lower() not in IMAGE_EXTENSIONS:
            raise ValueError('midia de origem deve ser imagem')
        if not os.path.isfile(target):
            raise ValueError('midia de origem ausente')
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
            found.append({
                'path': self.rel(path),
                'name': name,
                'type': media_type,
                'bytes': os.path.getsize(path),
            })
        return found

    def generate_media(self, request):
        tmp = self._write_temp_request(request)
        cmd = [sys.executable, os.path.join(self.tools, 'make_request_media.py'),
               '--input', tmp, '--root', self.root]
        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
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
        fs_target = render_local.fs_path(target)
        content_type = CONTENT_TYPES.get(ext, 'application/octet-stream')
        size = os.path.getsize(fs_target)
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
        with open(fs_target, 'rb') as handle:
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
            elif path == '/api/readiness':
                self.send_json(200, {'ok': True, 'readiness': studio.check_readiness()})
            elif path == '/api/projects':
                self.send_json(200, {'ok': True, 'projects': studio.list_projects()})
            elif path == '/api/profiles':
                proj = query.get('project', [''])[0]
                mod = query.get('module', [None])[0]
                self.send_json(200, {'ok': True, 'listing': studio.list_profiles(proj, mod)})
            elif path == '/api/examples':
                self.send_json(200, {'ok': True, 'examples': studio.list_examples()})
            elif path == '/api/works':
                self.send_json(200, {'ok': True, 'works': studio.list_works()})
            elif path == '/api/works/open':
                self.send_json(200, {'ok': True, **studio.open_work(query.get('id', [''])[0])})
            elif path == '/api/works/review':
                self.send_json(200, {'ok': True, **studio.get_review_overview(query.get('id', [''])[0])})
            elif path == '/api/works/artifact-text':
                self.send_json(200, {'ok': True, **studio.read_artifact_text(
                    query.get('id', [''])[0],
                    query.get('modality', [''])[0],
                    query.get('profile', [''])[0],
                    query.get('kind', [''])[0],
                )})
            elif path == '/api/works/package':
                self.send_json(200, {'ok': True, **studio.read_package_delivery(query.get('id', [''])[0])})
            elif path == '/api/works/package/download':
                try:
                    target, download_name = studio.verified_package_download(query.get('id', [''])[0])
                except (ValueError, OSError) as exc:
                    self.send_error_json(404, str(exc))
                    return
                fs_target = render_local.fs_path(target)
                size = os.path.getsize(fs_target)
                self.send_response(200)
                self.send_header('Content-Type', 'application/zip')
                self.send_header('Content-Disposition', f'attachment; filename="{download_name}"')
                self.send_header('Content-Length', str(size))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                with open(fs_target, 'rb') as handle:
                    while True:
                        chunk = handle.read(65536)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
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
            elif path == '/source-media':
                try:
                    target = studio.source_media_path(query.get('path', [''])[0])
                except (ValueError, OSError) as exc:
                    self.send_error_json(404, str(exc))
                    return
                ext = os.path.splitext(target)[1].lower()
                with open(render_local.fs_path(target), 'rb') as handle:
                    body = handle.read()
                self.send_response(200)
                self.send_header('Content-Type', CONTENT_TYPES.get(ext, 'application/octet-stream'))
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_error_json(404, 'rota desconhecida')
        except studio_review.ReviewVersionConflictError as exc:
            self.send_json(409, {'ok': False, 'error': str(exc), 'conflict': True})
        except (ValueError, OSError) as exc:
            self.send_error_json(400, str(exc))
        except RuntimeError as exc:
            self.send_error_json(500, str(exc))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        studio = self.studio
        try:
            body = self.read_body()
            if not self.check_write():
                return
            if path == '/api/projects/create':
                self.send_json(200, {'ok': True, **studio.create_project(body)})
            elif path == '/api/works/create':
                self.send_json(200, {'ok': True, **studio.create_work(body)})
            elif path == '/api/works/demo':
                self.send_json(200, {'ok': True, **studio.create_demo_work(body)})
            elif path == '/api/works/save':
                self.send_json(200, {'ok': True, **studio.save_work(body)})
            elif path == '/api/works/editorial/save':
                self.send_json(200, {'ok': True, **studio.save_editorial(body)})
            elif path == '/api/works/review/decide':
                self.send_json(200, {'ok': True, **studio.decide_review(body)})
            elif path == '/api/works/package':
                self.send_json(200, {'ok': True, **studio.create_package(body)})
            elif path == '/api/draft/save':
                rel = studio.save_draft(body.get('path', ''), body.get('request'))
                self.send_json(200, {'ok': True, 'path': rel})
            elif path == '/api/preview':
                self.send_json(200, {'ok': True, **studio.preview(
                    body.get('request'), body.get('profile'), body.get('kind', 'video'), body.get('motionPlan'))})
            elif path == '/api/export':
                job_id = studio.start_export(
                    body.get('request'),
                    body.get('outputDir', ''),
                    body.get('profile'),
                    body.get('kind', 'video'),
                    body.get('motionPlan'),
                    work_id=body.get('workId'),
                )
                self.send_json(200, {'ok': True, 'jobId': job_id})
            elif path == '/api/media/scan':
                self.send_json(200, {'ok': True, 'media': studio.scan_media(body.get('folder', ''))})
            elif path == '/api/media/generate':
                self.send_json(200, {'ok': True, 'written': studio.generate_media(body.get('request'))})
            else:
                self.send_error_json(404, 'rota desconhecida')
        except studio_review.ReviewVersionConflictError as exc:
            self.send_json(409, {'ok': False, 'error': str(exc), 'conflict': True})
        except (ValueError, OSError) as exc:
            self.send_error_json(400, str(exc))
        except RuntimeError as exc:
            self.send_error_json(500, str(exc))


def make_server(root, port):
    studio = Studio(root, port)
    handler = type('BoundStudioHandler', (StudioHandler,), {'studio': studio})
    httpd = ThreadingHTTPServer(('127.0.0.1', port), handler)
    return httpd, studio


def print_readiness_text(readiness):
    print(readiness['summary'])
    for item in readiness['items']:
        mark = 'OK' if item['ok'] else 'FALTA'
        print(f"  [{mark}] {item['label']}: {item['detail']}")
        if item.get('instruction'):
            print(f"         -> {item['instruction']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description='Painel local de video (Video Studio)')
    parser.add_argument('--port', type=int, default=8765, help='Porta local (127.0.0.1)')
    parser.add_argument('--root', default=None, help='Raiz do projeto (padrao: git rev-parse --show-toplevel)')
    parser.add_argument('--check', action='store_true', help='Verifica pre-requisitos locais e sai sem abrir servidor')
    parser.add_argument('--json', action='store_true', help='Emite o resultado de --check em JSON')
    args = parser.parse_args(argv)
    root = discover_root(args.root)
    readiness = check_readiness(root)
    if args.check:
        if args.json:
            print(json.dumps(readiness, ensure_ascii=False, indent=2))
        else:
            print_readiness_text(readiness)
        return 0 if readiness['ready'] else 1

    print_readiness_text(readiness)
    httpd, _ = make_server(root, args.port)
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
