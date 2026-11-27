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

Multi-tenant e preflight (Etapa 6): a interface servida injeta um seletor de
tenant alimentado por ``tenants/*/brand-kit.json`` (paleta, tipografia,
uiLabels e VisualStyle v1). Antes de preview, exportacao, criacao e download do
pacote ZIP, o Studio executa ``preflight``: guardrails do tenant + termos
globais do Studio, mistura de rotas publica/gestor, SRT de 48 colunas via
``srt_formatter`` e as 7 lentes do ``editorial_qa``. Falhas viram bloqueio 422
(409 no download) com payload estruturado que a UI exibe. ``autoPublish`` e
sempre false; nenhum binario novo e gerado pelo preflight.
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
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import campaign_proof
import editorial_qa
import make_agenda_media
import make_proof_assets
import make_request_media
import produce_video
import render_local
import srt_formatter
import studio_queue
import delivery_package
import delivery_verify
import image_adapters
import llm_adapter
import studio_media
import studio_planning
import studio_review
import studio_connections
import studio_templates
import studio_video_api
import tenant_validator

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp')
VIDEO_EXTENSIONS = ('.mp4', '.mov')
KEBAB_CASE_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
PREVIEW_FILE_RE = re.compile(r'^[a-z0-9][a-z0-9._-]*\.mp4$')
PREVIEW_CACHE_MAX_FILES = 4
CONTENT_TYPES = {
    '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8', '.mjs': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8', '.map': 'application/json; charset=utf-8',
    '.svg': 'image/svg+xml', '.woff2': 'font/woff2',
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
    'validate-planning-suggestion.js',
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

TENANTS_DIR = 'tenants'
DEFAULT_TENANT_ID = 'marca-salao'
STUDIO_SRT_MAX_CHARS = 48
STUDIO_ROUTE_PUBLIC = '/booking/'
STUDIO_ROUTE_MANAGER = '/gestor/'
STUDIO_TENANT_UI = r'''<!-- STUDIO_TENANT_UI -->
<style>
#studio-tenant-bar{position:fixed;right:12px;bottom:12px;z-index:9999;background:#0d1117;color:#e6edf3;border:1px solid #30363d;border-radius:10px;padding:10px 12px;font:12px/1.45 Arial,sans-serif;max-width:360px;box-shadow:0 6px 24px rgba(0,0,0,.45)}
#studio-tenant-bar label{display:block;margin:4px 0}
#studio-tenant-bar select{width:100%;background:#0b0f14;color:#e6edf3;border:1px solid #30363d;border-radius:6px;padding:4px}
#studio-tenant-bar .studio-muted{color:#8b949e}
#studio-tenant-bar .studio-swatch{display:inline-block;width:10px;height:10px;border-radius:3px;margin-left:4px;border:1px solid #30363d}
#studio-tenant-bar button{margin-top:6px;background:#1f6feb;color:#fff;border:0;border-radius:6px;padding:4px 8px;cursor:pointer}
#studio-tenant-alert{position:fixed;left:50%;top:12px;transform:translateX(-50%);z-index:10000;display:none;max-width:78vw;background:#3d1214;border:1px solid #f85149;color:#ffdcdc;border-radius:8px;padding:10px 14px;font:12px/1.4 Consolas,monospace;white-space:pre-wrap;box-shadow:0 6px 24px rgba(0,0,0,.5)}
</style>
<div id="studio-tenant-bar">
  <strong>Tenant (brand-kit)</strong>
  <label>Conta <select id="studio-tenant-select"></select></label>
  <div id="studio-tenant-brand" class="studio-muted">carregando…</div>
  <div id="studio-tenant-labels" class="studio-muted"></div>
  <button id="studio-tenant-recheck" type="button">Verificar pré-requisitos</button>
  <span id="studio-tenant-status" class="studio-muted"></span>
</div>
<div id="studio-tenant-alert" role="alert"></div>
<script>
(function(){
  "use strict";
  var select=document.getElementById("studio-tenant-select");
  var brandEl=document.getElementById("studio-tenant-brand");
  var labelsEl=document.getElementById("studio-tenant-labels");
  var statusEl=document.getElementById("studio-tenant-status");
  var alertEl=document.getElementById("studio-tenant-alert");
  var bar=document.getElementById("studio-tenant-bar");
  var KEY="studio.tenantId";
  function esc(v){return String(v==null?"":v).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];});}
  function color(v){return /^#[0-9a-fA-F]{6}$/.test(String(v||""))?String(v):"#000000";}
  function showAlerts(pf){
    if(!pf||pf.ok){alertEl.style.display="none";alertEl.textContent="";return;}
    var lines=["PREFLIGHT BLOQUEADO — "+String(pf.tenantId||"")];
    (pf.alerts||[]).forEach(function(a){lines.push("["+a.code+"] "+(a.field?("("+a.field+") "):"")+a.message);});
    alertEl.textContent=lines.join("\n");alertEl.style.display="block";
  }
  function applyBrand(t){
    if(!t){return;}
    var p=t.palette||{};
    document.documentElement.style.setProperty("--studio-brand-primary",color(p.primary));
    document.documentElement.style.setProperty("--studio-brand-text",color(p.textPrimary));
    var font=String((t.typography||{}).fontFamily||"Arial").replace(/[^A-Za-z0-9 ,-]/g,"")||"Arial";
    document.body.style.fontFamily=font;
    bar.style.borderColor=color(p.primary);
    var labels=t.uiLabels||{};
    brandEl.innerHTML=esc(t.brandName||t.tenantId)+" · "+esc(t.domain||"")+
      '<span class="studio-swatch" style="background:'+color(p.primary)+'"></span>'+
      '<span class="studio-swatch" style="background:'+color(p.secondary)+'"></span>'+
      '<span class="studio-swatch" style="background:'+color(p.accent)+'"></span>';
    labelsEl.textContent="Fonte: "+font+" · "+String(labels.customerLabel||"")+" · "+String(labels.itemUnitLabel||"");
    statusEl.textContent="";
  }
  function selectTenant(id){
    var body={tenant_id:id};
    return fetch("/api/tenants/select",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})
      .then(function(r){return r.json();})
      .then(function(d){ if(d&&d.tenant){localStorage.setItem(KEY,id);applyBrand(d.tenant);} return d; })
      .catch(function(){statusEl.textContent="tenant indisponível";});
  }
  fetch("/api/tenants").then(function(r){return r.json();}).then(function(d){
    var tenants=(d&&d.tenants)||[];
    select.innerHTML="";
    tenants.forEach(function(t){var o=document.createElement("option");o.value=t.tenantId;o.textContent=t.brandName||t.tenantId;select.appendChild(o);});
    var saved=localStorage.getItem(KEY)||"";
    var pick=tenants.some(function(t){return t.tenantId===saved;})?saved:(tenants[0]&&tenants[0].tenantId);
    if(pick){select.value=pick;selectTenant(pick);}
  }).catch(function(){brandEl.textContent="tenants indisponíveis";});
  select.addEventListener("change",function(){selectTenant(select.value);});
  document.getElementById("studio-tenant-recheck").addEventListener("click",function(){
    statusEl.textContent="verificando…";
    fetch("/api/works/preflight",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({tenant_id:select.value})})
      .then(function(r){return r.json();})
      .then(function(d){showAlerts(d&&d.preflight?d.preflight:d);statusEl.textContent=(d&&d.preflight&&d.preflight.ok)?"pré-requisitos OK":"bloqueado";})
      .catch(function(){statusEl.textContent="falha na verificação";});
  });
  var originalFetch=window.fetch.bind(window);
  window.fetch=function(input,init){
    var url=typeof input==="string"?input:((input&&input.url)||"");
    try{
      var tid=localStorage.getItem(KEY);
      if(tid&&init&&init.body&&typeof init.body==="string"&&
         (url.indexOf("/api/projects/create")>=0||url.indexOf("/api/works/create")>=0||url.indexOf("/api/mcp/")>=0)){
        var payload=JSON.parse(init.body);
        if(payload&&!payload.tenant_id&&!payload.tenantId){
          payload.tenant_id=tid;
          init=Object.assign({},init,{body:JSON.stringify(payload)});
        }
      }
    }catch(e){}
    return originalFetch(input,init).then(function(res){
      if(/\/api\/(preview|video\/preview-render|export|works\/package)/.test(url)){
        res.clone().json().then(function(d){if(d&&d.preflight){showAlerts(d.preflight);}}).catch(function(){});
      }
      return res;
    });
  };
})();
</script>
<!-- /STUDIO_TENANT_UI -->'''
# Termos exigidos pelo preflight do Studio, alem dos claims do guardrails.json.
STUDIO_EXTRA_FORBIDDEN_TERMS = (
    'whatsapp', 'sms', 'lembrete automatico', 'lembretes automaticos',
    'mensagem automatica', 'mensagens automaticas', 'confirmacao automatica',
    'confirmacoes automaticas', 'checkout', 'pagamento', 'pagamentos',
    'cartao de credito', 'faturamento garantido', 'garantia de faturamento',
    'resultado garantido', 'aumento de faturamento garantido',
)


class PreflightBlocked(ValueError):
    """Preflight editorial/guardrails reprovou a operacao antes do render/download."""

    def __init__(self, report):
        self.report = report
        alerts = report.get('alerts') or []
        codes = ', '.join(sorted({a.get('code') for a in alerts if a.get('code')})) or 'PREFLIGHT'
        self.code = (alerts[0].get('code') if alerts else 'PREFLIGHT')
        super().__init__(f'Preflight bloqueou a operacao ({codes})')


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _srt_timestamp(ms):
    ms = max(0, int(ms))
    seconds, millis = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}'


def atomic_write_json(target, value):
    """Grava JSON de forma atomica com UTF-8, LF e flush+fsync antes de os.replace.

    No Windows o destino recem-criado pode ficar brevemente bloqueado por
    antivirus/indexador; o replace e repetido com espera curta (mesmo arquivo
    temporario) em vez de falhar a operacao inteira.
    """
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
        last_error = None
        for attempt in range(6):
            try:
                os.replace(tmp, fs(target))
                last_error = None
                break
            except PermissionError as exc:
                last_error = exc
                time.sleep(0.05 * (attempt + 1))
        if last_error is not None:
            raise last_error
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
    fe_manifest = 'tools/studio/frontend/dist/.vite/manifest.json'
    fe_ok = os.path.isfile(os.path.join(root, fe_manifest.replace('/', os.sep)))
    return {
        'ready': ready,
        'summary': summary,
        'items': items,
        'frontendBuild': {
            'ok': fe_ok,
            'manifestPath': fe_manifest,
        },
        'recommendedCommands': {
            'check': 'python tools/video_studio.py --check --json',
            'prepare': 'python tools/video_studio.py --prepare --check',
            'start': 'python tools/video_studio.py --prepare --port 8765',
        },
    }


def _run_npm_build_if_needed(sub_dir, required_files, root, env):
    missing = [p for p in required_files if not os.path.isfile(render_local.fs_path(p))]
    if not missing:
        return {'ok': True, 'action': 'already_built', 'missing': []}
    npm_bin = shutil.which('npm')
    if not npm_bin:
        return {'ok': False, 'action': 'missing_npm', 'error': 'Comando "npm" nao encontrado no PATH.', 'missing': missing}
    has_modules = os.path.isdir(render_local.fs_path(os.path.join(sub_dir, 'node_modules')))
    cmds = ([['run', 'build']] if has_modules else [['ci', '--offline'], ['run', 'build']])
    for args in cmds:
        proc = subprocess.run(
            [npm_bin, *args],
            cwd=sub_dir,
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=300,
        )
        if proc.stdout:
            print(proc.stdout, file=sys.stderr)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        if proc.returncode != 0:
            err_hint = 'falha ao executar npm (em estacoes offline, garanta node_modules local)' if not has_modules else 'npm run build falhou'
            return {'ok': False, 'action': 'build_failed', 'error': err_hint, 'command': f'npm {" ".join(args)}'}
    still_missing = [p for p in required_files if not os.path.isfile(render_local.fs_path(p))]
    return {'ok': not still_missing, 'action': 'built', 'missing': still_missing}


def prepare_environment(root, build_frontend=True):
    """Prepara builds locais e midias sinteticas dos exemplos mantendo temporarios sob .workspace/."""
    prep_tmp = os.path.join(root, '.workspace', 'tmp', 'studio-prepare')
    os.makedirs(render_local.fs_path(prep_tmp), exist_ok=True)
    env = os.environ.copy()
    env['TEMP'] = prep_tmp
    env['TMP'] = prep_tmp
    env['npm_config_cache'] = os.path.join(prep_tmp, 'npm-cache')
    os.makedirs(render_local.fs_path(env['npm_config_cache']), exist_ok=True)

    platform_files = [os.path.join(root, 'platform', 'dist', 'src', m) for m in REQUIRED_PLATFORM_MODULES]
    plat_res = _run_npm_build_if_needed(os.path.join(root, 'platform'), platform_files, root, env)

    fe_files = [os.path.join(root, 'tools', 'studio', 'frontend', 'dist', '.vite', 'manifest.json')]
    fe_res = (
        _run_npm_build_if_needed(os.path.join(root, 'tools', 'studio', 'frontend'), fe_files, root, env)
        if build_frontend else {'ok': True, 'action': 'skipped'}
    )

    tools_ok, tools_err = campaign_proof._ensure_video_tools_for_root(root)

    examples_dir = os.path.join(root, 'tools', 'produce', 'examples')
    examples_res = []
    if os.path.isdir(examples_dir):
        for fname in sorted(os.listdir(examples_dir)):
            if not fname.endswith('.video-request.json'):
                continue
            rel_req = f'tools/produce/examples/{fname}'
            try:
                prep = campaign_proof.cmd_prepare(rel_req, root=root)
                examples_res.append({'request': rel_req, 'ok': bool(prep.get('ok')), 'errors': prep.get('errors', [])})
            except Exception as exc:
                examples_res.append({'request': rel_req, 'ok': False, 'errors': [{'code': 'PREPARE_FAILED', 'subject': str(exc)}]})

    ok = bool(plat_res.get('ok') and fe_res.get('ok') and all(e['ok'] for e in examples_res))
    return {
        'ok': ok,
        'platformBuild': plat_res,
        'frontendBuild': fe_res,
        'renderToolsReady': tools_ok,
        'renderToolsMessage': tools_err,
        'examplesPrepared': examples_res,
    }


def _default_output_profiles_from_listing(listing):
    profiles = listing.get('profiles', [])
    video = [p['id'] for p in profiles if p.get('localExportVideo')]
    carousel = [p['id'] for p in profiles if p.get('localExportCarousel')]
    motion = [p['id'] for p in profiles if p.get('localExportMotion')]
    return video, carousel, motion


# Modos de legenda por trabalho. 'burned' (legado) mantem legenda queimada + SRT;
# 'clean' e o VIDEO CLEAN (MKT-VIDEO-002): MP4 sem legenda queimada e sem SRT,
# roteiro de narracao TXT preservado. Aplica-se a video/motion, nunca a carrossel.
VALID_CAPTIONS_MODES = ('burned', 'clean')


def _normalize_captions_mode(value, default='burned'):
    normalized = str(value or '').strip().lower()
    return normalized if normalized in VALID_CAPTIONS_MODES else default


# Selecao explicita de motor de render por trabalho (MKT-VIDEO-003):
# 'ffmpeg' e o legado (produce_video); 'hyperframes' aciona o adaptador HF-001
# na fila. Sem escolha registrada, o legado permanece; nunca ha fallback silencioso.
VALID_RENDERER_ADAPTERS = ('ffmpeg', 'hyperframes')


def _normalize_renderer(value, default='ffmpeg'):
    if isinstance(value, str):
        adapter = value.strip().lower()
    elif isinstance(value, dict):
        adapter = str(value.get('adapter') or '').strip().lower()
    else:
        adapter = ''
    return adapter if adapter in VALID_RENDERER_ADAPTERS else default


class Studio:
    """Estado e operacoes do painel, confinadas a raiz do projeto."""

    def __init__(self, root, port, auto_start_queue=True):
        self.root = os.path.realpath(root)
        self.port = port
        self.tools = os.path.join(self.root, 'tools')
        self.studio_dir = os.path.join(self.tools, 'studio')
        self.studio_workspace = os.path.join(self.root, '.workspace', 'studio')
        self.projects_dir = os.path.join(self.studio_workspace, 'projects')
        self.works_dir = os.path.join(self.studio_workspace, 'works')
        self.status_dir = os.path.join(self.studio_workspace, 'export-status')
        self.drafts_dir = os.path.join(self.root, '.workspace', 'tmp', 'video-studio', 'drafts')
        self.standalone_previews_dir = os.path.join(self.root, '.workspace', 'tmp', 'video-studio', 'previews')
        self.jobs = {}
        self.jobs_lock = threading.Lock()
        self.preview_jobs = {}
        self.preview_jobs_by_key = {}
        self.preview_jobs_lock = threading.Lock()
        self.active_tenant_id = None
        self._editorial_cache = {}
        self._editorial_cache_lock = threading.Lock()
        for folder in (self.projects_dir, self.works_dir, self.status_dir, self.drafts_dir, self.standalone_previews_dir):
            os.makedirs(folder, exist_ok=True)
        self.queue = studio_queue.StudioQueue(self, auto_start=auto_start_queue)
        self.video_api_stopped = False
        self.video_api_recovery = studio_video_api.recover_on_startup(self)

    def close(self):
        self.video_api_stopped = True
        if getattr(self, 'queue', None) is not None:
            self.queue.stop_executor()

    def is_single_export_active(self, output_dir_rel, profile=None):
        try:
            norm = self._normalize_rel(output_dir_rel)
        except ValueError:
            return False
        with self.jobs_lock:
            for job in self.jobs.values():
                if job.get('status') == 'running' and self._normalize_rel(job['outputDir']) == norm:
                    if profile is not None and job.get('profile') != profile:
                        continue
                    return True
        return False

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

    # ---- tenants (brand-kit + guardrails) ----
    def tenant_ids(self):
        base = os.path.join(self.root, TENANTS_DIR)
        if not os.path.isdir(render_local.fs_path(base)):
            return []
        ids = []
        for name in sorted(os.listdir(render_local.fs_path(base))):
            if not KEBAB_CASE_RE.match(name):
                continue
            if os.path.isfile(render_local.fs_path(os.path.join(base, name, 'brand-kit.json'))):
                ids.append(name)
        return ids

    def _tenant_dir(self, tenant_id):
        tid = str(tenant_id or '').strip()
        if not KEBAB_CASE_RE.match(tid):
            raise ValueError(f'tenant_id invalido: {tenant_id!r}')
        base = os.path.realpath(os.path.join(self.root, TENANTS_DIR))
        target = os.path.realpath(os.path.join(base, tid))
        if os.path.commonpath([base, target]) != base or not os.path.isdir(render_local.fs_path(target)):
            raise ValueError(f'tenant_id inexistente: {tid}')
        return target

    def list_tenants(self):
        rows = []
        for tenant_id in self.tenant_ids():
            kit_path = os.path.join(self.root, TENANTS_DIR, tenant_id, 'brand-kit.json')
            try:
                with open(render_local.fs_path(kit_path), 'r', encoding='utf-8') as handle:
                    kit = json.load(handle)
            except (OSError, ValueError):
                continue
            rows.append({
                'tenantId': tenant_id,
                'brandName': kit.get('brandName') or tenant_id,
                'displayTitle': kit.get('displayTitle') or kit.get('brandName') or tenant_id,
                'monogram': kit.get('monogram') or '',
                'domain': kit.get('domain') or '',
                'defaultPreset': kit.get('defaultPreset'),
                'fontFamily': (kit.get('typography') or {}).get('fontFamily'),
            })
        return rows

    def _tenant_visual_style(self, tenant_id, style_id=None):
        """VisualStyle v1 (contrato do nucleo) derivado da paleta do brand-kit."""
        kit_path = os.path.join(self.root, TENANTS_DIR, tenant_id, 'brand-kit.json')
        with open(render_local.fs_path(kit_path), 'r', encoding='utf-8') as handle:
            kit = json.load(handle)
        palette = kit.get('palette') or {}

        def _hex(value, fallback):
            return value if isinstance(value, str) and re.match(r'^#[0-9a-fA-F]{6}$', value) else fallback

        candidate_id = str(style_id or f'{tenant_id}-brand')
        if not KEBAB_CASE_RE.match(candidate_id):
            candidate_id = f'{tenant_id}-brand'
        return {
            'schemaVersion': 1,
            'id': candidate_id,
            'title': {
                'textColor': _hex(palette.get('textPrimary'), '#FFFFFF'),
                'outlineColor': _hex(palette.get('background'), '#000000'),
                'fontSize': 44,
                'marginTop': 170,
                'marginHorizontal': 70,
            },
        }

    def get_tenant_brand(self, tenant_id):
        self._tenant_dir(tenant_id)
        try:
            ctx = tenant_validator.load_and_validate_tenant(
                tenant_id, root=self.root, strict=True)
        except tenant_validator.TenantContractError as exc:
            raise ValueError(str(exc))
        kit = ctx['brandKit']
        guardrails = ctx['guardrails']
        palette = kit.get('palette') or {}
        return {
            'tenantId': tenant_id,
            'brandName': kit.get('brandName') or tenant_id,
            'displayTitle': kit.get('displayTitle') or kit.get('brandName') or tenant_id,
            'monogram': kit.get('monogram') or '',
            'domain': kit.get('domain') or '',
            'url': kit.get('url') or '',
            'tagline': kit.get('tagline') or '',
            'palette': {
                key: palette.get(key)
                for key in (
                    'primary', 'secondary', 'accent', 'background', 'surface',
                    'textPrimary', 'textMuted',
                )
            },
            'typography': kit.get('typography') or {},
            'uiLabels': kit.get('uiLabels') or {},
            'visualStyle': self._tenant_visual_style(tenant_id),
            'guardrails': {
                'forbiddenClaims': list(guardrails.get('forbiddenClaims') or []),
                'forbiddenUiElements': list(guardrails.get('forbiddenUiElements') or []),
                'routeRules': guardrails.get('routeRules') or {},
            },
            'audioPolicy': guardrails.get('audioPolicy') or {},
            'brandKitPath': ctx['brandKitPath'],
            'guardrailsPath': ctx['guardrailsPath'],
            'autoPublish': False,
        }

    def select_tenant(self, body):
        if not isinstance(body, dict):
            raise ValueError('payload de tenant invalido')
        tenant_id = (body.get('tenant_id') or body.get('tenantId') or '').strip()
        brand = self.get_tenant_brand(tenant_id)
        self.active_tenant_id = tenant_id
        return {'activeTenantId': tenant_id, 'tenant': brand}

    def _tenant_from_project(self, project_rel):
        if not project_rel:
            return None
        try:
            doc = self._load_json(project_rel)
        except (ValueError, OSError):
            return None
        candidate = str(doc.get('brandTheme') or '').strip()
        return candidate if candidate in self.tenant_ids() else None

    def _resolve_tenant_id(self, body=None, work_id=None, project_rel=None):
        explicit = None
        if isinstance(body, dict):
            explicit = body.get('tenant_id') or body.get('tenantId')
        if explicit:
            self._tenant_dir(explicit)
            return str(explicit)
        if work_id and KEBAB_CASE_RE.match(str(work_id)):
            work_abs = self.confine_workspace(self.work_paths(work_id)['workFile'])
            if os.path.isfile(render_local.fs_path(work_abs)):
                try:
                    with open(render_local.fs_path(work_abs), 'r', encoding='utf-8') as handle:
                        candidate = str(json.load(handle).get('tenantId') or '').strip()
                except (OSError, ValueError):
                    candidate = ''
                if candidate:
                    self._tenant_dir(candidate)
                    return candidate
        from_project = self._tenant_from_project(project_rel)
        if from_project:
            return from_project
        if self.active_tenant_id:
            self._tenant_dir(self.active_tenant_id)
            return self.active_tenant_id
        if DEFAULT_TENANT_ID in self.tenant_ids():
            return DEFAULT_TENANT_ID
        return None

    def _request_texts(self, request, overlay_plan=None):
        """Rotulos e textos auditaveis do roteiro/cards/TextOverlayPlan v1."""
        texts = []
        if isinstance(request, dict):
            if str(request.get('title') or '').strip():
                texts.append(('request.title', str(request['title'])))
            for index, scene in enumerate(request.get('scenes') or []):
                if not isinstance(scene, dict):
                    continue
                for key in ('caption', 'title', 'narration'):
                    value = str(scene.get(key) or '').strip()
                    if value:
                        texts.append((f'scenes[{index}].{key}', value))
            for index, card in enumerate(request.get('cards') or []):
                if not isinstance(card, dict):
                    continue
                for key in ('title', 'body'):
                    value = str(card.get(key) or '').strip()
                    if value:
                        texts.append((f'cards[{index}].{key}', value))
            if overlay_plan is None:
                overlay_plan = request.get('textOverlayPlan') or request.get('overlayPlan')
        if overlay_plan is not None:
            if not isinstance(overlay_plan, dict):
                raise ValueError('TextOverlayPlan v1 deve ser um objeto')
            if overlay_plan.get('schemaVersion') != 1:
                raise ValueError('TextOverlayPlan exige schemaVersion 1')
            overlays = overlay_plan.get('overlays')
            if not isinstance(overlays, list):
                raise ValueError('TextOverlayPlan.overlays deve ser lista')
            for index, overlay in enumerate(overlays):
                if not isinstance(overlay, dict):
                    raise ValueError(f'TextOverlayPlan.overlays[{index}] invalido')
                text = str(overlay.get('text') or '').strip()
                if not text:
                    raise ValueError(f'TextOverlayPlan.overlays[{index}].text vazio')
                texts.append((f'textOverlayPlan.overlays[{index}].text', text))
        return texts

    def _synthesize_srt(self, request):
        scenes = request.get('scenes') if isinstance(request, dict) else None
        cues = []
        cursor = 0
        for scene in scenes or []:
            if not isinstance(scene, dict):
                continue
            text = str(scene.get('caption') or scene.get('title') or '').strip()
            if not text:
                continue
            duration = int(scene.get('durationMs') or 0)
            if duration <= 0:
                duration = 1000
            end = cursor + duration
            cues.append(
                f'{len(cues) + 1}\n{_srt_timestamp(cursor)} --> {_srt_timestamp(end)}\n{text}'
            )
            cursor = end
        return '\n\n'.join(cues) + '\n' if cues else ''

    def _editorial_audit(self, tenant_id, strict):
        key = (tenant_id, bool(strict))
        with self._editorial_cache_lock:
            cached = self._editorial_cache.get(key)
        if cached is not None:
            return cached
        try:
            report = editorial_qa.run_editorial_qa(
                root=self.root, strict=strict, tenant=tenant_id)
        except (OSError, ValueError, editorial_qa.EditorialQAError) as exc:
            report = {
                'schemaVersion': 1,
                'ok': False,
                'error': str(exc),
                'checks': [],
                'summary': {'problems': {'errors': 1, 'warnings': 0}},
            }
        with self._editorial_cache_lock:
            if report.get('ok'):
                self._editorial_cache[key] = report
        return report

    def preflight(self, tenant_id=None, request=None, overlay_plan=None, srt_text=None,
                  work_id=None, project_rel=None, strict_editorial=False,
                  include_editorial=True):
        """Guardrails + rotas + SRT 48 col + 7 lentes antes de render/entrega."""
        resolved = self._resolve_tenant_id(
            {'tenant_id': tenant_id} if tenant_id else None,
            work_id=work_id,
            project_rel=project_rel,
        )
        if not resolved:
            raise ValueError('nenhum tenant disponivel para o preflight')
        brand = self.get_tenant_brand(resolved)
        guardrails = brand['guardrails']
        alerts = []

        try:
            texts = self._request_texts(request, overlay_plan)
        except ValueError as exc:
            texts = []
            alerts.append({
                'code': 'TEXT_OVERLAY_PLAN_INVALIDO',
                'severity': 'error',
                'field': 'textOverlayPlan',
                'message': str(exc),
            })

        merged_claims = list(dict.fromkeys(
            [str(c) for c in guardrails.get('forbiddenClaims') or []] +
            [str(c) for c in STUDIO_EXTRA_FORBIDDEN_TERMS]
        ))
        merged_guardrails = {
            'forbiddenClaims': merged_claims,
            'forbiddenUiElements': list(guardrails.get('forbiddenUiElements') or []),
        }
        guardrail_hits = 0
        for label, text in texts:
            for violation in tenant_validator.validate_text_against_guardrails(
                text, merged_guardrails, check_ui_elements=True
            ):
                guardrail_hits += 1
                alerts.append({
                    'code': 'GUARDRAIL_VIOLACAO',
                    'severity': 'error',
                    'field': label,
                    'message': violation,
                })

        joined = '\n'.join(text for _, text in texts)
        route_ok = not (
            STUDIO_ROUTE_PUBLIC in joined and STUDIO_ROUTE_MANAGER in joined
        )
        if not route_ok:
            alerts.append({
                'code': 'ROTAS_MISTURADAS',
                'severity': 'error',
                'field': 'request',
                'message': (
                    f'mistura de rotas {STUDIO_ROUTE_PUBLIC}... e {STUDIO_ROUTE_MANAGER}... '
                    'na mesma peca; separe fluxo publico e gestor'
                ),
            })

        srt_check = {
            'ok': True,
            'maxLineChars': STUDIO_SRT_MAX_CHARS,
            'cues': 0,
            'maxLineLength': 0,
        }
        source = srt_text if isinstance(srt_text, str) and srt_text.strip() else self._synthesize_srt(request)
        if source:
            try:
                formatted, stats = srt_formatter.format_srt_content(
                    source, max_chars=STUDIO_SRT_MAX_CHARS)
            except srt_formatter.SrtFormatterError as exc:
                srt_check = {
                    'ok': False,
                    'maxLineChars': STUDIO_SRT_MAX_CHARS,
                    'error': str(exc),
                }
                alerts.append({
                    'code': 'SRT_INVALIDO',
                    'severity': 'error',
                    'field': 'srt',
                    'message': str(exc),
                })
            else:
                srt_ok = stats['afterLongLines'] == 0
                srt_check = {
                    'ok': srt_ok,
                    'maxLineChars': STUDIO_SRT_MAX_CHARS,
                    'cues': stats['cues'],
                    'beforeMaxLineLength': stats['beforeMaxLineLength'],
                    'maxLineLength': stats['afterMaxLineLength'],
                }
                if not srt_ok:
                    alerts.append({
                        'code': 'SRT_LINHA_LONGA',
                        'severity': 'error',
                        'field': 'srt',
                        'message': (
                            f"{stats['afterLongLines']} linha(s) acima de "
                            f'{STUDIO_SRT_MAX_CHARS} caracteres'
                        ),
                    })
                srt_check['formatted'] = formatted

        editorial = {'enabled': bool(include_editorial), 'ok': True, 'strict': bool(strict_editorial)}
        if include_editorial:
            report = self._editorial_audit(resolved, strict_editorial)
            editorial = {
                'enabled': True,
                'ok': bool(report.get('ok')),
                'strict': bool(strict_editorial),
                'lenses': [
                    {
                        'id': check.get('id'),
                        'ok': bool(check.get('ok')),
                        'status': check.get('status'),
                        'problems': len(check.get('problems') or []),
                    }
                    for check in report.get('checks') or []
                ],
                'errors': ((report.get('summary') or {}).get('problems') or {}).get('errors', 0),
                'warnings': ((report.get('summary') or {}).get('problems') or {}).get('warnings', 0),
            }
            if report.get('error'):
                editorial['error'] = report['error']
            if not editorial['ok']:
                codes = sorted({
                    problem.get('code')
                    for check in report.get('checks') or []
                    for problem in (check.get('problems') or [])
                    if problem.get('severity') == 'error' and problem.get('code')
                })
                alerts.append({
                    'code': 'EDITORIAL_QA_REPROVADO',
                    'severity': 'error',
                    'field': 'editorial_qa',
                    'message': (
                        'editorial_qa reprovou: ' + (', '.join(codes) if codes else
                        (report.get('error') or 'consulte o relatorio'))
                    ),
                })

        ok = not any(alert['severity'] == 'error' for alert in alerts)
        return {
            'schemaVersion': 1,
            'ok': ok,
            'tenantId': resolved,
            'autoPublish': False,
            'maxLineChars': STUDIO_SRT_MAX_CHARS,
            'alerts': alerts,
            'checks': {
                'guardrails': {
                    'ok': guardrail_hits == 0,
                    'textFields': len(texts),
                    'violations': guardrail_hits,
                },
                'rotas': {'ok': route_ok},
                'srt': srt_check,
                'editorialQa': editorial,
            },
            'brand': {
                'brandName': brand['brandName'],
                'palette': brand['palette'],
                'typography': brand['typography'],
                'uiLabels': brand['uiLabels'],
                'visualStyle': brand['visualStyle'],
            },
        }

    def preflight_for_work(self, work_id, strict_editorial=True, request=None,
                           overlay_plan=None, tenant_id=None):
        if not KEBAB_CASE_RE.match(str(work_id or '')):
            raise ValueError('workId invalido para preflight')
        work, disk_request, _ = self._load_work_draft_bundle(work_id)
        return self.preflight(
            tenant_id=tenant_id or work.get('tenantId'),
            request=request or disk_request,
            overlay_plan=overlay_plan,
            work_id=work_id,
            project_rel=work.get('project'),
            strict_editorial=strict_editorial,
        )

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

        tenant_hint = body.get('tenant_id') or body.get('tenantId') or manifest_in.get('tenantId')
        tenant_id = None
        brand = None
        if tenant_hint:
            tenant_id = self._resolve_tenant_id({'tenantId': tenant_hint})
            brand = self.get_tenant_brand(tenant_id)

        brand_theme = (manifest_in.get('brandTheme') or '').strip()
        if not brand_theme:
            brand_theme = tenant_id or project_id
        name = (manifest_in.get('name') or '').strip()
        if not name and brand:
            name = brand['brandName']

        manifest = {
            'schemaVersion': manifest_in.get('schemaVersion', 1),
            'id': project_id,
            'name': name,
            'locale': (manifest_in.get('locale') or 'pt-BR').strip(),
            'timezone': (manifest_in.get('timezone') or 'America/Sao_Paulo').strip(),
            'brandTheme': brand_theme,
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
            'tenantId': tenant_id,
            'brand': brand,
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
            # Fonte compartilhada: a exportabilidade local por modulo vem do
            # catalogo + adaptador (platform/output-profiles/local-export.ts),
            # nunca de um segundo dicionario de formatos aqui.
            local = profile.get('localExport') or {}
            video_ok = allowed and bool((local.get('video') or {}).get('supported'))
            carousel_ok = allowed and bool((local.get('carousel') or {}).get('supported'))
            motion_ok = allowed and bool((local.get('motion') or {}).get('supported'))
            modules = []
            if video_ok:
                modules.append('video')
            if carousel_ok:
                modules.append('carousel')
            if motion_ok:
                modules.append('motion')
            profile['localExport'] = local
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
            'planningFile': f'{base}/planning.json',
            'mediaLibraryFile': f'{base}/media-library.json',
            'videoRequestsFile': f'{base}/video-requests.json',
            'videoDeliveryDir': f'{base}/deliveries/video',
            'carouselDeliveryDir': f'{base}/deliveries/carousel',
            'motionDeliveryDir': f'{base}/deliveries/motion',
            'hyperframesDeliveryDir': f'{base}/deliveries/hyperframes',
            'packageDeliveryDir': f'{base}/deliveries/package',
        }

    def _delivery_badge_summary(self, video_dir, carousel_dir, motion_dir, work_id=None, hyperframes_dir=None):
        v = self.read_delivery(video_dir)
        c = self.read_carousel_delivery(carousel_dir)
        m = self.read_delivery(motion_dir)
        h = self.read_delivery(hyperframes_dir) if hyperframes_dir else {'profiles': [], 'index': {}}
        v_valid = sum(
            1 for p in (v.get('index') or {}).get('profiles', [])
            if p.get('lastValidDelivery')
        ) or len(v.get('profiles', []))
        c_valid = bool(c.get('manifest') and (c.get('index') or {}).get('lastValidDelivery', True))
        m_valid = sum(
            1 for p in (m.get('index') or {}).get('profiles', [])
            if p.get('lastValidDelivery')
        ) or len(m.get('profiles', []))
        h_valid = sum(
            1 for p in (h.get('index') or {}).get('profiles', [])
            if p.get('lastValidDelivery')
        ) or len(h.get('profiles', []))
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
            'hyperframesValidCount': h_valid,
            'packageValid': pkg_valid,
            'videoLastStatus': (v.get('lastExportStatus') or {}).get('status'),
            'carouselLastStatus': (c.get('lastExportStatus') or {}).get('status'),
            'motionLastStatus': (m.get('lastExportStatus') or {}).get('status'),
            'hyperframesLastStatus': (h.get('lastExportStatus') or {}).get('status'),
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
                hyperframes_dir=paths.get('hyperframesDeliveryDir', f'.workspace/studio/works/{entry}/deliveries/hyperframes'),
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

        video_req_path = (body.get('videoRequestPath') or '').strip()
        example_match = None
        if video_req_path:
            ex_abs = self.confine(video_req_path)
            if not os.path.isfile(render_local.fs_path(ex_abs)):
                raise ValueError(f'VideoRequest nao encontrado: {video_req_path}')
            example_match = {'path': self.rel(ex_abs), 'request': self._load_json(self.rel(ex_abs))}
        else:
            tmpl_raw = (body.get('template') or '').strip()
            if tmpl_raw and tmpl_raw not in BRAND_EXAMPLES and tmpl_raw != 'blank':
                target_id = tmpl_raw[len('example:'):] if tmpl_raw.startswith('example:') else tmpl_raw
                for ex in self.list_examples():
                    if ex.get('kind') != 'video':
                        continue
                    ex_id = (ex.get('request') or {}).get('id')
                    if target_id in (ex_id, ex.get('name'), ex.get('path')):
                        example_match = ex
                        break
                if example_match is None and tmpl_raw.startswith('example:'):
                    raise ValueError(f'exemplo de video nao encontrado: {target_id}')

        project_rel = (body.get('project') or '').strip()
        if not project_rel and example_match is not None:
            project_rel = str((example_match.get('request') or {}).get('project') or '').strip()
        if not project_rel:
            raise ValueError('selecione um projeto para criar o trabalho')
        project_abs = self.confine(project_rel)
        if not os.path.isfile(project_abs):
            raise ValueError('ProjectManifest selecionado nao encontrado')
        with open(project_abs, 'r', encoding='utf-8') as handle:
            project_doc = json.load(handle)
        self._validate_project_with_core(project_doc)

        tenant_id = self._resolve_tenant_id(body, project_rel=project_rel)
        brand = self.get_tenant_brand(tenant_id) if tenant_id else None
        visual_style = (
            self._tenant_visual_style(tenant_id, f'{work_id}-estilo')
            if tenant_id else {
                'schemaVersion': 1,
                'id': f'{work_id}-estilo',
                'title': {
                    'textColor': '#FFFFFF', 'outlineColor': '#000000',
                    'fontSize': 44, 'marginTop': 170, 'marginHorizontal': 70,
                },
            }
        )

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

        if example_match is not None:
            ex_video = json.loads(json.dumps(example_match['request']))
            if not video_profiles:
                raise ValueError('projeto selecionado nao permite destinos de video locais compativeis')
            ex_profiles = ex_video.get('profiles') or []
            filtered_profiles = [p for p in ex_profiles if p in video_profiles]
            if ex_profiles and not filtered_profiles:
                raise ValueError('nenhum perfil do exemplo e compativel com o projeto selecionado')

            used_names = set()
            copied_media = []
            dur_by_media = {}
            for sc in ex_video.get('scenes', []):
                dur_by_media[sc.get('mediaId')] = max(dur_by_media.get(sc.get('mediaId'), 0), int(sc.get('durationMs', 0)))

            for idx, item in enumerate(ex_video.get('media', []), start=1):
                base_name = os.path.basename(str(item.get('path') or f"{item['id']}.png"))
                dest_name = base_name if base_name not in used_names else f'{idx:02d}-{base_name}'
                used_names.add(dest_name)
                dest_rel = f'{media_dir_rel}/{dest_name}'
                dest_abs = self.confine_workspace(dest_rel)
                src_copied = False
                src_rel = str(item.get('path') or '').strip()
                if src_rel:
                    try:
                        src_abs = self.confine(src_rel)
                        if os.path.isfile(render_local.fs_path(src_abs)) and not campaign_proof._is_synthetic_proof_file(src_abs):
                            shutil.copy2(render_local.fs_path(src_abs), render_local.fs_path(dest_abs))
                            src_copied = True
                    except ValueError:
                        src_copied = False
                if not src_copied:
                    mtype = item.get('type', 'image')
                    if mtype == 'image':
                        campaign_proof.write_scene_png(dest_abs, f'{work_id}-video', item['id'], idx)
                    elif mtype == 'video':
                        dur_s = max(2.0, dur_by_media.get(item['id'], 2000) / 1000.0 + 0.5)
                        make_proof_assets.write_scene_mp4(render_local.fs_path(dest_abs), f'{work_id}-video', item['id'], idx, duration_s=dur_s)
                    else:
                        raise ValueError(f'tipo de midia nao suportado no exemplo: {mtype}')
                copied_media.append({
                    'id': item['id'],
                    'path': dest_rel,
                    'type': item.get('type', 'image'),
                    'origin': item.get('origin', 'synthetic-demo'),
                    'license': item.get('license', 'owned-synthetic'),
                })

            video_req = {
                'schemaVersion': 1,
                'id': f'{work_id}-video',
                'project': project_rel,
                'title': ex_video.get('title', name),
                'locale': ex_video.get('locale', project_doc.get('locale', 'pt-BR')),
                'profiles': filtered_profiles or video_profiles,
                'visualStyle': visual_style if tenant_id else ex_video.get('visualStyle', visual_style),
                'media': copied_media,
                'scenes': json.loads(json.dumps(ex_video.get('scenes', []))),
            }
            carousel_req = {
                'schemaVersion': 1,
                'id': f'{work_id}-carrossel',
                'project': project_rel,
                'profile': carousel_profiles[0] if carousel_profiles else 'instagram-feed-image-square',
                'title': f'{video_req["title"]} — Carrossel',
                'media': [],
                'cards': [{'id': 'capa', 'title': video_req['title'], 'body': name}],
            }
            motion_plan = {
                'schemaVersion': 1,
                'requestId': video_req['id'],
                'effects': [],
            }
        elif template in BRAND_EXAMPLES:
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
                'visualStyle': visual_style if tenant_id else ex_video.get('visualStyle', visual_style),
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
                'visualStyle': visual_style,
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
            'tenantId': tenant_id,
            'autoPublish': False,
            'captionsMode': _normalize_captions_mode(body.get('captionsMode')),
            'renderer': {'adapter': _normalize_renderer(body.get('renderer'))},
            'brand': {
                'brandName': brand['brandName'],
                'monogram': brand['monogram'],
                'palette': brand['palette'],
                'typography': brand['typography'],
                'uiLabels': brand['uiLabels'],
                'visualStyle': brand['visualStyle'],
            } if brand else None,
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
            'hyperframes': self.read_delivery(wpaths['hyperframesDeliveryDir']),
        }
        listing = self.list_profiles(work['project'])
        review = studio_review.build_review_overview(self, work_id)
        planning = studio_planning.build_planning_overview(self, work_id)
        package_delivery = delivery_package.read_package_delivery(self, work_id)
        media_library = studio_media.build_media_overview(self, work_id)
        return {
            'work': work_view,
            'videoRequest': video_req,
            'carouselRequest': carousel_req,
            'motionPlan': motion_plan,
            'workMedia': work_media,
            'deliveries': deliveries,
            'listing': listing,
            'review': review,
            'planning': planning,
            'packageDelivery': package_delivery,
            'mediaLibrary': media_library,
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

        if 'captionsMode' in body:
            work['captionsMode'] = _normalize_captions_mode(
                body.get('captionsMode'), work.get('captionsMode') or 'burned')

        if 'renderer' in body:
            current = (work.get('renderer') or {}).get('adapter') if isinstance(work.get('renderer'), dict) else None
            work['renderer'] = {'adapter': _normalize_renderer(body.get('renderer'), current or 'ffmpeg')}

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

    # ---- motor HyperFrames (MKT-VIDEO-003 / HF-001 F7) ----
    def save_work_renderer(self, body):
        """Selecao explicita de motor de render do trabalho (sem fallback silencioso)."""
        if not isinstance(body, dict):
            raise ValueError('payload de renderer invalido')
        work_id = (body.get('workId') or body.get('id') or '').strip()
        if not work_id:
            raise ValueError('informe workId')
        adapter = _normalize_renderer(body.get('renderer'))
        if adapter == 'hyperframes':
            ok, reason = studio_queue.hyperframes_runtime_ready(self.root)
            if not ok:
                raise ValueError(reason)
        return self.save_work({'workId': work_id, 'renderer': {'adapter': adapter}})

    def hyperframes_readiness(self):
        ok, reason = studio_queue.hyperframes_runtime_ready(self.root)
        version = None
        pkg_path = os.path.join(self.root, 'renderers', 'hyperframes', 'node_modules', 'hyperframes', 'package.json')
        if os.path.isfile(render_local.fs_path(pkg_path)):
            try:
                with open(render_local.fs_path(pkg_path), 'r', encoding='utf-8') as handle:
                    version = json.load(handle).get('version')
            except (OSError, ValueError):
                version = None
        return {
            'ok': ok,
            'reason': reason,
            'version': version,
            'adapter': 'hyperframes',
        }

    def hyperframes_preview(self, body):
        """Compoe a composicao HyperFrames do rascunho e roda o check (sem render)."""
        if not isinstance(body, dict):
            raise ValueError('payload de previa HyperFrames invalido')
        work_id = (body.get('workId') or '').strip()
        profile_id = (body.get('profileId') or '').strip() or None
        if not work_id:
            raise ValueError('informe workId')
        opened = self.open_work(work_id)
        vreq = opened.get('videoRequest')
        if not isinstance(vreq, dict) or not vreq.get('scenes'):
            raise ValueError(f'trabalho {work_id} sem rascunho de video salvo com cenas')
        tmp = self._write_temp_request(vreq)
        run_dir = tempfile.mkdtemp(prefix='hf-preview-', dir=self.standalone_previews_dir)
        cmd = [
            sys.executable,
            os.path.join(self.tools, 'render_hyperframes.py'),
            '--input', tmp,
            '--root', self.root,
            '--workdir', run_dir,
            '--skip-render',
        ]
        if profile_id:
            cmd.extend(['--profile', profile_id])
        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=240)
        except subprocess.TimeoutExpired:
            raise RuntimeError('previa HyperFrames excedeu o tempo limite (240s)')
        lines = [line for line in (res.stdout or '').strip().splitlines() if line.strip()]
        verdict = None
        if lines:
            try:
                verdict = json.loads(lines[-1])
            except ValueError:
                verdict = None
        return {
            'returncode': res.returncode,
            'verdict': verdict,
            'stderr': (res.stderr or '').strip()[-4000:],
        }

    # ---- conexoes de texto e imagem ----
    def get_connections(self):
        return studio_connections.build_connections_overview(self)

    def save_connection(self, body):
        return studio_connections.save_connection(self, body)

    def replace_connection_credential(self, body):
        return studio_connections.replace_credential(self, body)

    def delete_connection(self, body):
        return studio_connections.delete_connection(self, body)

    def select_connection(self, body):
        return studio_connections.select_for_project(self, body)

    def test_connection(self, body):
        return studio_connections.test_connection(self, body)

    # ---- modelos reutilizaveis e variacoes ----
    def get_templates(self, project=None):
        return {'templates': studio_templates.list_templates(self, project)}

    def get_template(self, template_id):
        return {'template': studio_templates.get_template(self, template_id)}

    def save_template(self, body):
        return studio_templates.save_as_template(self, body)

    def duplicate_work(self, body):
        return studio_templates.duplicate_work(self, body)

    def plan_template_variations(self, body):
        return studio_templates.plan_variations(self, body)

    def create_template_variations(self, body):
        return studio_templates.create_variations(self, body)

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

    def preview(self, request, profile=None, kind='video', motion_plan=None,
                tenant_id=None, overlay_plan=None, enforce_preflight=True):
        preflight = None
        if enforce_preflight:
            project_rel = request.get('project') if isinstance(request, dict) else None
            preflight = self.preflight(
                tenant_id=tenant_id, request=request, overlay_plan=overlay_plan,
                project_rel=project_rel, strict_editorial=False)
            if not preflight['ok']:
                raise PreflightBlocked(preflight)
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
        return {'returncode': res.returncode, 'result': payload, 'preflight': preflight}

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

    def start_export(self, request, output_dir_rel, profile=None, kind='video', motion_plan=None,
                     work_id=None, tenant_id=None, overlay_plan=None, captions_mode=None):
        if self.is_single_export_active(output_dir_rel, profile=profile) or self.queue.is_destination_active(output_dir_rel):
            raise ValueError('Destino em uso por uma exportacao ou item da fila em andamento. Aguarde a conclusao.')
        if work_id:
            preflight = self.preflight_for_work(
                work_id, strict_editorial=False, request=request,
                overlay_plan=overlay_plan, tenant_id=tenant_id)
        else:
            preflight = self.preflight(
                tenant_id=tenant_id, request=request, overlay_plan=overlay_plan,
                project_rel=request.get('project') if isinstance(request, dict) else None,
                strict_editorial=False)
        if not preflight['ok']:
            raise PreflightBlocked(preflight)
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
        effective_captions_mode = _normalize_captions_mode(captions_mode) if captions_mode else None
        if effective_captions_mode is None and work_id:
            effective_captions_mode = _normalize_captions_mode(saved_work.get('captionsMode') or 'burned')
        if effective_captions_mode == 'clean' and kind != 'carousel':
            cmd.append('--clean')
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

    # ---- enquadramento e previa da montagem ----
    def _resolve_video_profile_meta(self, project_rel, profile_id):
        if not isinstance(profile_id, str) or not profile_id.strip():
            raise ValueError('profileId obrigatorio')
        pid = profile_id.strip()
        listing = self.list_profiles(project_rel or None)
        for item in listing.get('profiles') or []:
            if item.get('id') == pid:
                if item.get('mediaKind') != 'video':
                    raise ValueError(f'perfil {pid} nao e um perfil de video')
                return item, listing
        raise ValueError(f'perfil de video desconhecido: {pid}')

    def _preview_dir(self, work_id=None):
        if work_id:
            paths = self.work_paths(work_id)
            return self.confine_workspace(f"{paths['workDir']}/previews")
        return self.confine_workspace(self.standalone_previews_dir)

    def _preview_state_path(self, preview_dir, profile_id):
        if not isinstance(profile_id, str) or not KEBAB_CASE_RE.match(profile_id):
            raise ValueError('perfil invalido para previa')
        return self.confine_workspace(os.path.join(preview_dir, f'{profile_id}.preview.json'))

    def _read_preview_state(self, preview_dir, profile_id):
        fs = render_local.fs_path
        state_path = self._preview_state_path(preview_dir, profile_id)
        if not os.path.isfile(fs(state_path)):
            return None
        try:
            with open(fs(state_path), 'r', encoding='utf-8') as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def _prune_preview_cache(self, preview_dir, protected_files=None, max_files=PREVIEW_CACHE_MAX_FILES):
        fs = render_local.fs_path
        if not os.path.isdir(fs(preview_dir)):
            return
        protected = set(protected_files or ())
        # Tambem preserva o ultimo arquivo pronto de outros perfis ativos quando cabe no limite
        for entry in os.listdir(fs(preview_dir)):
            if not entry.endswith('.preview.json'):
                continue
            try:
                with open(fs(os.path.join(preview_dir, entry)), 'r', encoding='utf-8') as handle:
                    doc = json.load(handle)
                fname = doc.get('file') if isinstance(doc, dict) else None
                if isinstance(fname, str) and fname:
                    protected.add(fname)
            except (OSError, ValueError):
                pass
        mp4s = []
        for entry in os.listdir(fs(preview_dir)):
            if not PREVIEW_FILE_RE.match(entry):
                continue
            full = os.path.join(preview_dir, entry)
            if not os.path.isfile(fs(full)):
                continue
            try:
                mtime = os.path.getmtime(fs(full))
            except OSError:
                mtime = 0
            mp4s.append((0 if entry in protected else 1, -mtime, entry, full))
        mp4s.sort()
        for _, _, _, victim in mp4s[max(1, int(max_files)):]:
            try:
                os.remove(fs(victim))
            except OSError:
                pass

    def _motion_applies_to_profile(self, profile_meta, motion_plan):
        if not isinstance(motion_plan, dict) or not (motion_plan.get('effects') or []):
            return False
        dims = (profile_meta or {}).get('dimensions') or profile_meta or {}
        if int(dims.get('width') or 0) == 1080 and int(dims.get('height') or 0) == 1920:
            return True
        return bool((profile_meta or {}).get('localExportMotion'))

    def _applicable_motion_plan(self, request, profile_meta, motion_plan):
        if not self._motion_applies_to_profile(profile_meta, motion_plan):
            return None
        scenes = request.get('scenes') if isinstance(request, dict) else None
        scene_ids = {s.get('id') for s in (scenes or []) if isinstance(s, dict) and s.get('id')}
        effects = [
            e for e in (motion_plan.get('effects') or [])
            if isinstance(e, dict) and e.get('sceneId') in scene_ids
        ]
        if not effects:
            return None
        plan_copy = json.loads(json.dumps(motion_plan))
        plan_copy['effects'] = effects
        if isinstance(request, dict) and request.get('id'):
            plan_copy['requestId'] = request['id']
        return plan_copy

    def _compute_preview_fingerprint(self, request, profile_id, motion_plan=None, profile_meta=None):
        req_copy = json.loads(json.dumps(request if isinstance(request, dict) else {}))
        plan_copy = self._applicable_motion_plan(req_copy, profile_meta, motion_plan)
        if plan_copy is not None:
            fp, _ = studio_review.compute_draft_snapshot(
                self, 'motion', req_copy, None, plan_copy, profile_id=profile_id
            )
            return fp, 'motion'
        fp, _ = studio_review.compute_draft_snapshot(
            self, 'video', req_copy, None, None, profile_id=profile_id
        )
        return fp, 'video'

    def _load_work_draft_bundle(self, work_id):
        fs = render_local.fs_path
        paths = self.work_paths(work_id)
        work_abs = self.confine_workspace(paths['workFile'])
        if not os.path.isfile(fs(work_abs)):
            raise ValueError(f'trabalho nao encontrado: {work_id}')
        with open(fs(work_abs), 'r', encoding='utf-8') as handle:
            work = json.load(handle)
        wpaths = studio_review.merged_work_paths(self, work_id, work)
        vreq = self._load_json(wpaths['videoDraft']) or {}
        mplan = self._load_json(wpaths['motionPlan']) or None
        if isinstance(vreq, dict) and not vreq.get('project'):
            vreq['project'] = work['project']
        return work, vreq, mplan

    def video_frame_info(self, body):
        if not isinstance(body, dict):
            raise ValueError('payload de quadro invalido')
        work_id = (body.get('workId') or '').strip() or None
        project_rel = (body.get('project') or '').strip() or None
        if work_id and not project_rel:
            work, _, _ = self._load_work_draft_bundle(work_id)
            project_rel = work.get('project')
        profile_id = (body.get('profileId') or body.get('profile') or '').strip()
        profile_meta, _ = self._resolve_video_profile_meta(project_rel, profile_id)
        dims = profile_meta.get('dimensions') or profile_meta
        out_w, out_h = int(dims['width']), int(dims['height'])
        media_path = (body.get('mediaPath') or body.get('path') or '').strip()
        if not media_path:
            raise ValueError('mediaPath obrigatorio')
        media_abs = self.source_media_path(media_path)
        probe_info = render_local.probe_asset(self.root, media_abs)
        source_meta = render_local.extract_stream_geometry_meta(probe_info)
        framing = body.get('framing') if 'framing' in body else None
        beat_id = body.get('beatId')
        try:
            resolved = render_local.resolve_scene_framing(
                source_meta, out_w, out_h, framing=framing, beat_id=beat_id
            )
            return {
                'ok': True,
                'profileId': profile_id,
                'sourceMeta': source_meta,
                'outputDimensions': {'width': out_w, 'height': out_h},
                'resolvedFraming': resolved,
            }
        except build_video.DeliveryError as exc:
            msg = str(exc)
            if 'FRAMING_MEDIA_METADATA_UNSUPPORTED' not in msg:
                raise ValueError(msg)
            fit_resolved = render_local.resolve_scene_framing(
                source_meta, out_w, out_h, framing=None, beat_id=beat_id
            )
            return {
                'ok': False,
                'errorCode': 'FRAMING_MEDIA_METADATA_UNSUPPORTED',
                'message': msg,
                'fallbackMode': 'fit',
                'profileId': profile_id,
                'sourceMeta': source_meta,
                'outputDimensions': {'width': out_w, 'height': out_h},
                'resolvedFraming': fit_resolved,
            }

    def _run_preview_job(self, job):
        fs = render_local.fs_path
        preview_dir = job['previewDir']
        os.makedirs(fs(preview_dir), exist_ok=True)
        tmp_mp4 = self.confine_workspace(os.path.join(preview_dir, f".tmp-{job['jobId']}.mp4"))
        try:
            res = produce_video.render_assembly_preview(
                self.root,
                job['request'],
                job['profileId'],
                tmp_mp4,
                preset='veryfast',
                scale_factor=0.5,
                motion_plan=job.get('motionPlan'),
            )
            final_name = f"{job['profileId']}-{job['previewFingerprint'][:12]}.mp4"
            final_mp4 = self.confine_workspace(os.path.join(preview_dir, final_name))
            os.replace(fs(tmp_mp4), fs(final_mp4))
            finished_at = now_iso()
            work_q = quote(job['workId']) if job.get('workId') else ''
            state_doc = {
                'profileId': job['profileId'],
                'previewFingerprint': job['previewFingerprint'],
                'modality': job['modality'],
                'file': final_name,
                'url': f"/preview-media?work={work_q}&file={quote(final_name)}",
                'width': res['width'],
                'height': res['height'],
                'sourceOutputWidth': res.get('sourceOutputWidth'),
                'sourceOutputHeight': res.get('sourceOutputHeight'),
                'fps': res.get('fps'),
                'durationMs': res.get('durationMs'),
                'bytes': res.get('bytes'),
                'sha256': res.get('sha256'),
                'framings': res.get('framings') or [],
                'updatedAt': finished_at,
                'jobId': job['jobId'],
            }
            state_path = self._preview_state_path(preview_dir, job['profileId'])
            atomic_write_json(state_path, state_doc)
            self._prune_preview_cache(preview_dir, protected_files={final_name})
            with job['lock']:
                job['status'] = 'completed'
                job['finishedAt'] = finished_at
                job['result'] = state_doc
                job['error'] = None
        except Exception as exc:
            with job['lock']:
                job['status'] = 'failed'
                job['finishedAt'] = now_iso()
                job['error'] = str(exc)
                job['result'] = None
        finally:
            if os.path.exists(fs(tmp_mp4)):
                try:
                    os.remove(fs(tmp_mp4))
                except OSError:
                    pass

    def start_video_preview_render(self, body):
        if not isinstance(body, dict):
            raise ValueError('payload de previa invalido')
        work_id = (body.get('workId') or '').strip() or None
        profile_id = (body.get('profileId') or body.get('profile') or '').strip()
        req = body.get('request')
        mplan = body.get('motionPlan') if 'motionPlan' in body else None
        if work_id:
            work, disk_req, disk_mplan = self._load_work_draft_bundle(work_id)
            if not isinstance(req, dict):
                req = disk_req
            elif not req.get('project'):
                req = dict(req)
                req['project'] = work['project']
            if 'motionPlan' not in body:
                mplan = disk_mplan
        if not isinstance(req, dict) or not req:
            raise ValueError('VideoRequest ausente para gerar previa')
        project_rel = req.get('project')
        if work_id:
            preflight = self.preflight_for_work(
                work_id, strict_editorial=False, request=req,
                overlay_plan=body.get('textOverlayPlan') or body.get('overlayPlan'),
                tenant_id=body.get('tenant_id') or body.get('tenantId'))
        else:
            preflight = self.preflight(
                tenant_id=body.get('tenant_id') or body.get('tenantId'),
                request=req,
                overlay_plan=body.get('textOverlayPlan') or body.get('overlayPlan'),
                project_rel=project_rel,
                strict_editorial=False)
        if not preflight['ok']:
            raise PreflightBlocked(preflight)
        profile_meta, _ = self._resolve_video_profile_meta(project_rel, profile_id)
        mplan = self._applicable_motion_plan(req, profile_meta, mplan)
        preview_dir = self._preview_dir(work_id)
        fp, modality = self._compute_preview_fingerprint(req, profile_id, mplan, profile_meta)
        job_id = f'prev-{uuid.uuid4().hex[:12]}'
        job = {
            'jobId': job_id,
            'workId': work_id,
            'profileId': profile_id,
            'modality': modality,
            'previewFingerprint': fp,
            'previewDir': preview_dir,
            'request': json.loads(json.dumps(req)),
            'motionPlan': mplan if modality == 'motion' else None,
            'status': 'running',
            'error': None,
            'result': None,
            'startedAt': now_iso(),
            'finishedAt': None,
            'lock': threading.Lock(),
        }
        with self.preview_jobs_lock:
            self.preview_jobs[job_id] = job
            self.preview_jobs_by_key[(work_id or '_standalone', profile_id)] = job_id
        worker = threading.Thread(target=self._run_preview_job, args=(job,), daemon=True)
        worker.start()
        return {
            'jobId': job_id,
            'status': 'running',
            'workId': work_id,
            'profileId': profile_id,
            'previewFingerprint': fp,
            'preflight': preflight,
        }

    def video_preview_status(self, work_id=None, profile_id=None, job_id=None, request=None, motion_plan=None):
        fs = render_local.fs_path
        work_id = (work_id or '').strip() or None
        profile_id = (profile_id or '').strip() or None
        job_id = (job_id or '').strip() or None
        job = None
        if job_id:
            with self.preview_jobs_lock:
                job = self.preview_jobs.get(job_id)
            if job is None:
                raise ValueError('job de previa desconhecido')
            work_id = work_id or job.get('workId')
            profile_id = profile_id or job.get('profileId')
        elif profile_id:
            with self.preview_jobs_lock:
                latest_id = self.preview_jobs_by_key.get((work_id or '_standalone', profile_id))
                job = self.preview_jobs.get(latest_id) if latest_id else None
        if not profile_id:
            raise ValueError('profile obrigatorio')

        current_req = request if isinstance(request, dict) else None
        current_mplan = motion_plan if isinstance(motion_plan, dict) else None
        project_rel = current_req.get('project') if current_req else None
        if work_id:
            work, disk_req, disk_mplan = self._load_work_draft_bundle(work_id)
            if current_req is None:
                current_req = disk_req
            elif not current_req.get('project'):
                current_req = dict(current_req)
                current_req['project'] = work['project']
            project_rel = project_rel or work.get('project')
            if current_mplan is None and motion_plan is None:
                current_mplan = disk_mplan

        profile_meta, _ = self._resolve_video_profile_meta(project_rel, profile_id)
        current_fp = None
        if isinstance(current_req, dict) and current_req:
            current_fp, _ = self._compute_preview_fingerprint(
                current_req, profile_id, current_mplan, profile_meta
            )

        preview_dir = self._preview_dir(work_id)
        last_ready = self._read_preview_state(preview_dir, profile_id)
        if last_ready:
            mp4_name = last_ready.get('file') or ''
            if not PREVIEW_FILE_RE.match(mp4_name):
                last_ready = None
            else:
                mp4_abs = self.confine_workspace(os.path.join(preview_dir, mp4_name))
                if not os.path.isfile(fs(mp4_abs)):
                    last_ready = None
                else:
                    ref_fp = current_fp or (job.get('previewFingerprint') if job else None)
                    matches = (last_ready.get('previewFingerprint') == ref_fp) if ref_fp else True
                    last_ready = {
                        **last_ready,
                        'matchesCurrentDraft': matches,
                        'state': 'current' if matches else 'outdated',
                    }

        job_view = None
        if job is not None:
            with job['lock']:
                ref_fp = current_fp or job.get('previewFingerprint')
                job_view = {
                    'jobId': job['jobId'],
                    'status': job['status'],
                    'profileId': job['profileId'],
                    'previewFingerprint': job['previewFingerprint'],
                    'matchesCurrentDraft': job['previewFingerprint'] == ref_fp,
                    'error': job.get('error'),
                    'startedAt': job.get('startedAt'),
                    'finishedAt': job.get('finishedAt'),
                }

        return {
            'workId': work_id,
            'profileId': profile_id,
            'currentFingerprint': current_fp,
            'job': job_view,
            'lastReady': last_ready,
        }

    def preview_media_path(self, work_id=None, filename=''):
        fs = render_local.fs_path
        work_id = (work_id or '').strip() or None
        fname = os.path.basename((filename or '').strip())
        if not PREVIEW_FILE_RE.match(fname) or fname != (filename or '').strip():
            raise ValueError('arquivo de previa invalido')
        preview_dir = self._preview_dir(work_id)
        target = self.confine_workspace(os.path.join(preview_dir, fname))
        if os.path.dirname(target) != preview_dir or not os.path.isfile(fs(target)):
            raise ValueError('arquivo de previa ausente')
        return target

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
        preflight = self.preflight_for_work(
            work_id, strict_editorial=False,
            overlay_plan=(body.get('textOverlayPlan') or body.get('overlayPlan')) if isinstance(body, dict) else None,
            tenant_id=(body.get('tenant_id') or body.get('tenantId')) if isinstance(body, dict) else None,
        )
        if not preflight['ok']:
            raise PreflightBlocked(preflight)
        pkg = delivery_package.build_and_promote_package(self, work_id, body)
        overview = studio_review.build_review_overview(self, work_id)
        return {**overview, 'packageDelivery': pkg, 'preflight': preflight}

    def read_package_delivery(self, work_id):
        return delivery_package.read_package_delivery(self, work_id)

    def verified_package_download(self, work_id):
        preflight = self.preflight_for_work(work_id, strict_editorial=False)
        if not preflight['ok']:
            raise PreflightBlocked(preflight)
        return delivery_package.verified_package_zip_path(self, work_id)

    def verify_package_delivery(self, work_id):
        """Verifica o pacote ZIP salvo do trabalho ativo (somente leitura)."""
        info = delivery_package.read_package_delivery(self, work_id)
        last_valid = info.get('lastValidDelivery')
        if not last_valid or not last_valid.get('zipPath'):
            return {
                'ok': False,
                'available': False,
                'workId': work_id,
                'packageId': None,
                'summary': info.get('zipError') or 'Nenhum pacote ZIP de entrega gerado para este trabalho.',
                'errors': [{'message': info.get('zipError') or 'Nenhum pacote ZIP de entrega gerado para este trabalho.'}],
                'checks': [],
                'limitations': [],
                'files': [],
                'pieces': [],
                'channels': [],
                'zipSha256': {
                    'actual': None,
                    'expected': (last_valid or {}).get('zipSha256'),
                    'compared': False,
                    'match': None,
                },
            }
        zip_abs = self.confine(last_valid['zipPath'])
        result = delivery_verify.verify_package_zip(
            zip_abs,
            expected_zip_sha256=last_valid.get('zipSha256'),
        )
        result['available'] = bool(info.get('available'))
        result['indexZipSha256'] = last_valid.get('zipSha256')
        result['zipPath'] = last_valid.get('zipPath')
        return result

    # ---- planejamento por etapas e adaptador local de modelo ----
    def get_planning_overview(self, work_id):
        return studio_planning.build_planning_overview(self, work_id)

    def save_planning(self, body):
        work_id = (body.get('workId') or body.get('id') or '').strip() if isinstance(body, dict) else ''
        return studio_planning.save_planning(self, work_id, body)

    def build_planning_prompt(self, body):
        work_id = (body.get('workId') or body.get('id') or '').strip() if isinstance(body, dict) else ''
        stage = (body.get('stage') or 'briefing').strip() if isinstance(body, dict) else 'briefing'
        return studio_planning.build_stage_prompt(self, work_id, stage)

    def import_planning_suggestion(self, body):
        work_id = (body.get('workId') or body.get('id') or '').strip() if isinstance(body, dict) else ''
        return studio_planning.validate_and_stage_suggestion(self, work_id, body, mode='import')

    def generate_planning_suggestion(self, body):
        work_id = (body.get('workId') or body.get('id') or '').strip() if isinstance(body, dict) else ''
        return studio_planning.generate_with_local_model(self, work_id, body)

    def accept_planning_suggestion(self, body):
        work_id = (body.get('workId') or body.get('id') or '').strip() if isinstance(body, dict) else ''
        return studio_planning.accept_suggestion(self, work_id, body)

    def preview_planning_diff(self, body):
        work_id = (body.get('workId') or body.get('id') or '').strip() if isinstance(body, dict) else ''
        return studio_planning.preview_editors_diff(self, work_id, body)

    def apply_planning_to_editors(self, body):
        work_id = (body.get('workId') or body.get('id') or '').strip() if isinstance(body, dict) else ''
        return studio_planning.apply_planning_to_editors(self, work_id, body)

    def get_llm_config(self):
        return {
            'llmConfig': llm_adapter.load_llm_config(self),
            'imageExtensionPoint': llm_adapter.ImageProviderExtensionPoint.status(),
        }

    def save_llm_config(self, body):
        cfg = llm_adapter.save_llm_config(self, body)
        return {
            'llmConfig': cfg,
            'imageExtensionPoint': llm_adapter.ImageProviderExtensionPoint.status(),
        }

    def source_media_path(self, path_rel):
        """Caminho de midia de origem (imagem ou gravacao) confinado a raiz, para o editor."""
        target = self.confine(path_rel)
        if os.path.splitext(target)[1].lower() not in IMAGE_EXTENSIONS + VIDEO_EXTENSIONS:
            raise ValueError('midia de origem deve ser imagem ou video')
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

    # ---- biblioteca de midia por trabalho (pedidos visuais e versoes) ----
    def get_media_library(self, work_id):
        return studio_media.build_media_overview(self, work_id)

    def import_work_media(self, body):
        work_id = (body.get('workId') or '').strip() if isinstance(body, dict) else ''
        return studio_media.import_media(self, work_id, body)

    def register_work_media(self, body):
        work_id = (body.get('workId') or '').strip() if isinstance(body, dict) else ''
        return studio_media.register_existing_media(self, work_id, body)

    def save_visual_anchor(self, body):
        work_id = (body.get('workId') or '').strip() if isinstance(body, dict) else ''
        return studio_media.save_anchor(self, work_id, body)

    def create_image_request(self, body):
        work_id = (body.get('workId') or '').strip() if isinstance(body, dict) else ''
        return studio_media.create_image_request(self, work_id, body)

    def update_image_request(self, body):
        work_id = (body.get('workId') or '').strip() if isinstance(body, dict) else ''
        return studio_media.update_image_request(self, work_id, body)

    def generate_image_candidate(self, body):
        work_id = (body.get('workId') or '').strip() if isinstance(body, dict) else ''
        return studio_media.generate_candidate(self, work_id, body)

    def select_work_media(self, body):
        work_id = (body.get('workId') or '').strip() if isinstance(body, dict) else ''
        return studio_media.select_media(self, work_id, body)

    def get_image_providers(self):
        return {'providers': image_adapters.provider_status()}

    def library_media_file(self, work_id, asset_id, version_id):
        return studio_media.library_media_path(self, work_id, asset_id, version_id)

    # ---- importacao de gravacoes MP4 (blocos, FFprobe, promocao conjunta) ----
    def start_video_import(self, body):
        work_id = (body.get('workId') or '').strip() if isinstance(body, dict) else ''
        return studio_media.start_video_import(self, work_id, body)

    def chunk_video_import(self, body):
        return studio_media.chunk_video_import(self, body)

    def finish_video_import(self, body):
        work_id = (body.get('workId') or '').strip() if isinstance(body, dict) else ''
        return studio_media.finish_video_import(self, work_id, body)

    def cancel_video_import(self, body):
        return studio_media.cancel_video_import(self, body)

    # ---- geracao de clipes por API (texto para video) ----
    def get_video_requests(self, work_id):
        return studio_video_api.get_requests(self, work_id)

    def create_video_request(self, body):
        work_id = (body.get('workId') or '').strip() if isinstance(body, dict) else ''
        return studio_video_api.create_request(self, work_id, body)

    def submit_video_request(self, body):
        work_id = (body.get('workId') or '').strip() if isinstance(body, dict) else ''
        return studio_video_api.submit_request(self, work_id, body)

    def check_video_request(self, body):
        work_id = (body.get('workId') or '').strip() if isinstance(body, dict) else ''
        return studio_video_api.check_request(self, work_id, body)

    def import_video_request(self, body):
        work_id = (body.get('workId') or '').strip() if isinstance(body, dict) else ''
        return studio_video_api.import_request(self, work_id, body)


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

    def send_error_json(self, code, message, extra=None):
        payload = {'ok': False, 'error': message}
        if isinstance(extra, dict) and extra:
            payload.update(extra)
        self.send_json(code, payload)

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

    def _astryx_frontend_tags(self):
        dist_dir = os.path.realpath(os.path.join(self.studio.studio_dir, 'frontend', 'dist'))
        manifest_path = os.path.join(dist_dir, '.vite', 'manifest.json')
        if not os.path.isfile(manifest_path):
            return ''
        try:
            with open(manifest_path, 'r', encoding='utf-8') as handle:
                manifest = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return ''
        entry = manifest.get('src/main.jsx')
        if not isinstance(entry, dict) or not entry.get('file'):
            return ''
        entry_rel = str(entry['file']).lstrip('/')
        entry_fs = os.path.realpath(os.path.join(dist_dir, *entry_rel.split('/')))
        if os.path.commonpath([dist_dir, entry_fs]) != dist_dir or not os.path.isfile(entry_fs):
            return ''
        tags = []
        for css_rel in entry.get('css', []) or []:
            css_clean = str(css_rel).lstrip('/')
            css_fs = os.path.realpath(os.path.join(dist_dir, *css_clean.split('/')))
            if os.path.commonpath([dist_dir, css_fs]) == dist_dir and os.path.isfile(css_fs):
                tags.append(f'<link rel="stylesheet" href="/static/frontend/{css_clean}">')
        tags.append(f'<script type="module" src="/static/frontend/{entry_rel}"></script>')
        return '\n  '.join(tags)

    def serve_index(self):
        path = os.path.join(self.studio.studio_dir, 'index.html')
        if not os.path.isfile(path):
            self.send_error_json(404, 'arquivo ausente')
            return
        with open(path, 'r', encoding='utf-8') as handle:
            html = handle.read()
        tags = self._astryx_frontend_tags()
        html = html.replace('<!-- ASTRYX_FRONTEND_ASSETS -->', tags)
        if '</body>' in html:
            html = html.replace('</body>', STUDIO_TENANT_UI + '\n</body>')
        body = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def serve_static(self, name):
        if not name or '\\' in name or name in ('.', '..'):
            self.send_error_json(404, 'arquivo invalido')
            return
        if name.startswith('frontend/'):
            rel = name[len('frontend/'):]
            parts = [p for p in rel.split('/') if p]
            if not parts or any(p in ('.', '..') for p in parts):
                self.send_error_json(404, 'arquivo invalido')
                return
            dist_dir = os.path.realpath(os.path.join(self.studio.studio_dir, 'frontend', 'dist'))
            path = os.path.realpath(os.path.join(dist_dir, *parts))
            if os.path.commonpath([dist_dir, path]) != dist_dir:
                self.send_error_json(404, 'arquivo invalido')
                return
        else:
            if '/' in name:
                self.send_error_json(404, 'arquivo invalido')
                return
            path = os.path.join(self.studio.studio_dir, name)
        if not os.path.isfile(path):
            self.send_error_json(404, 'arquivo ausente')
            return
        ext = os.path.splitext(path)[1].lower()
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
    def serve_file_ranges(self, target):
        """Serve arquivo com suporte a Range (206) para o player avancar/voltar."""
        fs = render_local.fs_path
        size = os.path.getsize(fs(target))
        ext = os.path.splitext(target)[1].lower()
        content_type = CONTENT_TYPES.get(ext, 'application/octet-stream')
        range_header = self.headers.get('Range')
        start, end = 0, size - 1
        partial = False
        if range_header:
            match = re.match(r'^bytes=(\d*)-(\d*)$', range_header.strip())
            if not match or (not match.group(1) and not match.group(2)):
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.end_headers()
                return
            if match.group(1):
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else size - 1
            else:
                suffix = int(match.group(2))
                start = max(0, size - suffix)
            if start >= size or end < start:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.end_headers()
                return
            end = min(end, size - 1)
            partial = True
        length = end - start + 1
        self.send_response(206 if partial else 200)
        self.send_header('Content-Type', content_type)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(length))
        if partial:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        with open(fs(target), 'rb') as handle:
            handle.seek(start)
            remaining = length
            while remaining > 0:
                chunk = handle.read(min(65536, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

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
                self.serve_index()
            elif path.startswith('/static/'):
                self.serve_static(path[len('/static/'):])
            elif path == '/api/readiness':
                self.send_json(200, {'ok': True, 'readiness': studio.check_readiness()})
            elif path == '/api/tenants':
                self.send_json(200, {
                    'ok': True,
                    'tenants': studio.list_tenants(),
                    'activeTenantId': studio.active_tenant_id,
                })
            elif path == '/api/tenants/get':
                self.send_json(200, {
                    'ok': True,
                    'tenant': studio.get_tenant_brand(query.get('id', [''])[0]),
                })
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
            elif path == '/api/templates':
                self.send_json(200, {'ok': True, **studio.get_templates(query.get('project', [None])[0])})
            elif path == '/api/connections':
                self.send_json(200, {'ok': True, **studio.get_connections()})
            elif path == '/api/templates/get':
                self.send_json(200, {'ok': True, **studio.get_template(query.get('id', [''])[0])})
            elif path == '/api/queue':
                self.send_json(200, {'ok': True, **studio.queue.list_queue(
                    status=query.get('status', [None])[0],
                    work_id=query.get('workId', [None])[0],
                    batch_id=query.get('batchId', [None])[0],
                )})
            elif path == '/api/hyperframes/readiness':
                self.send_json(200, {'ok': True, **studio.hyperframes_readiness()})
            elif path == '/api/queue/batch':
                self.send_json(200, {'ok': True, 'batch': studio.queue.get_batch(query.get('id', [''])[0])})
            elif path == '/api/queue/batch/summary':
                summary = studio.queue.export_batch_summary(query.get('id', [''])[0])
                payload = (json.dumps(summary, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
                bid = re.sub(r'[^a-zA-Z0-9._-]', '_', summary['batchId'])
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Disposition', f'attachment; filename="{bid}-summary.json"')
                self.send_header('Content-Length', str(len(payload)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(payload)
            elif path == '/api/works/open':
                self.send_json(200, {'ok': True, **studio.open_work(query.get('id', [''])[0])})
            elif path == '/api/works/planning':
                self.send_json(200, {'ok': True, **studio.get_planning_overview(query.get('id', [''])[0])})
            elif path == '/api/works/media-library':
                self.send_json(200, {'ok': True, **studio.get_media_library(query.get('id', [''])[0])})
            elif path == '/api/works/video-requests':
                self.send_json(200, {'ok': True, **studio.get_video_requests(query.get('id', [''])[0])})
            elif path == '/api/image/config':
                self.send_json(200, {'ok': True, **studio.get_image_providers()})
            elif path == '/library-media':
                try:
                    target, mime = studio.library_media_file(
                        query.get('work', [''])[0], query.get('asset', [''])[0], query.get('version', [''])[0])
                except (ValueError, OSError) as exc:
                    self.send_error_json(404, str(exc))
                    return
                with open(render_local.fs_path(target), 'rb') as handle:
                    body = handle.read()
                self.send_response(200)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(body)
            elif path == '/api/llm/config':
                self.send_json(200, {'ok': True, **studio.get_llm_config()})
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
            elif path == '/api/works/package/verify':
                self.send_json(200, {'ok': True, 'verification': studio.verify_package_delivery(query.get('id', [''])[0])})
            elif path == '/api/works/package/download':
                try:
                    target, download_name = studio.verified_package_download(query.get('id', [''])[0])
                except PreflightBlocked as exc:
                    self.send_error_json(409, str(exc), {
                        'preflight': exc.report,
                        'code': exc.code,
                    })
                    return
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
            elif path == '/api/video/preview-status':
                self.send_json(200, {'ok': True, **studio.video_preview_status(
                    work_id=query.get('work', [''])[0],
                    profile_id=query.get('profile', [''])[0],
                    job_id=query.get('job', [''])[0],
                )})
            elif path == '/api/delivery':
                self.send_json(200, {'ok': True, **studio.read_delivery(query.get('dir', [''])[0])})
            elif path == '/api/carousel-delivery':
                self.send_json(200, {'ok': True, **studio.read_carousel_delivery(query.get('dir', [''])[0])})
            elif path == '/media':
                self.serve_artifact(query)
            elif path == '/preview-media':
                try:
                    target = studio.preview_media_path(
                        work_id=query.get('work', [''])[0],
                        filename=query.get('file', [''])[0],
                    )
                except (ValueError, OSError) as exc:
                    self.send_error_json(404, str(exc))
                    return
                self.serve_file_ranges(target)
            elif path == '/source-media':
                try:
                    target = studio.source_media_path(query.get('path', [''])[0])
                except (ValueError, OSError) as exc:
                    self.send_error_json(404, str(exc))
                    return
                self.serve_file_ranges(target)
            else:
                self.send_error_json(404, 'rota desconhecida')
        except studio_video_api.VideoApiError as exc:
            self.send_error_json(400, exc.message, {'code': exc.code})
        except studio_connections.ConnectionError_ as exc:
            self.send_error_json(400, exc.message, {'code': exc.code})
        except studio_templates.TemplateConflictError as exc:
            self.send_error_json(409, exc.message, {'code': exc.code})
        except studio_queue.QueueConflictError as exc:
            self.send_error_json(409, exc.message, {'code': exc.code, 'canUseCurrent': exc.can_use_current})
        except PreflightBlocked as exc:
            self.send_error_json(422, str(exc), {
                'preflight': exc.report,
                'code': exc.code,
            })
        except studio_review.ReviewVersionConflictError as exc:
            self.send_error_json(409, str(exc), {'conflict': True})
        except studio_planning.PlanningValidationError as exc:
            self.send_error_json(400, str(exc), {
                'failureCode': exc.failure_code,
                'subject': exc.subject,
                'stage': exc.stage,
            })
        except llm_adapter.LLMTimeoutError as exc:
            self.send_error_json(504, str(exc), {'code': exc.code})
        except llm_adapter.LLMUnavailableError as exc:
            self.send_error_json(503, str(exc), {'code': exc.code})
        except llm_adapter.LLMAdapterError as exc:
            self.send_error_json(400, str(exc), {'code': exc.code})
        except image_adapters.ImageProviderTimeoutError as exc:
            self.send_error_json(504, str(exc), {'code': exc.code})
        except image_adapters.ImageProviderUnavailableError as exc:
            self.send_error_json(503, str(exc), {'code': exc.code})
        except image_adapters.ImageAdapterError as exc:
            self.send_error_json(400, str(exc), {'code': exc.code})
        except (ValueError, OSError, build_video.DeliveryError) as exc:
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
            elif path == '/api/mcp/projects/create':
                self.send_json(200, {'ok': True, 'mcp': True, **studio.create_project(body)})
            elif path == '/api/mcp/works/create':
                self.send_json(200, {'ok': True, 'mcp': True, **studio.create_work(body)})
            elif path == '/api/tenants/select':
                self.send_json(200, {'ok': True, **studio.select_tenant(body)})
            elif path == '/api/works/preflight':
                work_id = (body.get('workId') or body.get('id') or '').strip()
                overlay = body.get('textOverlayPlan') or body.get('overlayPlan')
                if work_id:
                    report = studio.preflight_for_work(
                        work_id,
                        strict_editorial=bool(body.get('strict', False)),
                        request=body.get('request'),
                        overlay_plan=overlay,
                        tenant_id=body.get('tenant_id') or body.get('tenantId'),
                    )
                else:
                    report = studio.preflight(
                        tenant_id=body.get('tenant_id') or body.get('tenantId'),
                        request=body.get('request'),
                        overlay_plan=overlay,
                        strict_editorial=bool(body.get('strict', False)),
                    )
                self.send_json(200, {'ok': True, 'preflight': report})
            elif path == '/api/works/create':
                self.send_json(200, {'ok': True, **studio.create_work(body)})
            elif path == '/api/works/demo':
                self.send_json(200, {'ok': True, **studio.create_demo_work(body)})
            elif path == '/api/works/save':
                self.send_json(200, {'ok': True, **studio.save_work(body)})
            elif path == '/api/works/renderer/save':
                self.send_json(200, {'ok': True, **studio.save_work_renderer(body)})
            elif path == '/api/works/hyperframes/preview':
                self.send_json(200, {'ok': True, **studio.hyperframes_preview(body)})
            elif path == '/api/templates/save':
                self.send_json(200, {'ok': True, **studio.save_template(body)})
            elif path == '/api/connections/save':
                self.send_json(200, {'ok': True, **studio.save_connection(body)})
            elif path == '/api/connections/credential':
                self.send_json(200, {'ok': True, **studio.replace_connection_credential(body)})
            elif path == '/api/connections/delete':
                self.send_json(200, {'ok': True, **studio.delete_connection(body)})
            elif path == '/api/connections/select':
                self.send_json(200, {'ok': True, **studio.select_connection(body)})
            elif path == '/api/connections/test':
                self.send_json(200, {'ok': True, **studio.test_connection(body)})
            elif path == '/api/works/duplicate':
                self.send_json(200, {'ok': True, **studio.duplicate_work(body)})
            elif path == '/api/templates/plan':
                self.send_json(200, {'ok': True, **studio.plan_template_variations(body)})
            elif path == '/api/templates/create':
                self.send_json(200, {'ok': True, **studio.create_template_variations(body)})
            elif path == '/api/works/editorial/save':
                self.send_json(200, {'ok': True, **studio.save_editorial(body)})
            elif path == '/api/works/planning/save':
                self.send_json(200, {'ok': True, **studio.save_planning(body)})
            elif path == '/api/works/planning/prompt':
                if isinstance(body, dict):
                    tenant_hint = body.pop('tenant_id', None) or body.pop('tenantId', None)
                    if tenant_hint:
                        studio.get_tenant_brand(tenant_hint)
                self.send_json(200, {'ok': True, **studio.build_planning_prompt(body)})
            elif path == '/api/works/planning/import':
                if isinstance(body, dict):
                    tenant_hint = body.pop('tenant_id', None) or body.pop('tenantId', None)
                    if tenant_hint:
                        studio.get_tenant_brand(tenant_hint)
                self.send_json(200, {'ok': True, **studio.import_planning_suggestion(body)})
            elif path == '/api/works/planning/generate':
                self.send_json(200, {'ok': True, **studio.generate_planning_suggestion(body)})
            elif path == '/api/works/planning/accept-suggestion':
                self.send_json(200, {'ok': True, **studio.accept_planning_suggestion(body)})
            elif path == '/api/works/planning/diff':
                self.send_json(200, {'ok': True, **studio.preview_planning_diff(body)})
            elif path == '/api/works/planning/apply':
                self.send_json(200, {'ok': True, **studio.apply_planning_to_editors(body)})
            elif path == '/api/works/media/import':
                self.send_json(200, {'ok': True, **studio.import_work_media(body)})
            elif path == '/api/works/media/import-video/start':
                self.send_json(200, {'ok': True, **studio.start_video_import(body)})
            elif path == '/api/works/media/import-video/chunk':
                self.send_json(200, {'ok': True, **studio.chunk_video_import(body)})
            elif path == '/api/works/media/import-video/finish':
                self.send_json(200, {'ok': True, **studio.finish_video_import(body)})
            elif path == '/api/works/media/import-video/cancel':
                self.send_json(200, {'ok': True, **studio.cancel_video_import(body)})
            elif path == '/api/works/video-requests/create':
                self.send_json(200, {'ok': True, **studio.create_video_request(body)})
            elif path == '/api/works/video-requests/submit':
                self.send_json(200, {'ok': True, **studio.submit_video_request(body)})
            elif path == '/api/works/video-requests/check':
                self.send_json(200, {'ok': True, **studio.check_video_request(body)})
            elif path == '/api/works/video-requests/import':
                self.send_json(200, {'ok': True, **studio.import_video_request(body)})
            elif path == '/api/works/media/register':
                self.send_json(200, {'ok': True, **studio.register_work_media(body)})
            elif path == '/api/works/media/anchor':
                self.send_json(200, {'ok': True, **studio.save_visual_anchor(body)})
            elif path == '/api/works/media/request/create':
                self.send_json(200, {'ok': True, **studio.create_image_request(body)})
            elif path == '/api/works/media/request/update':
                self.send_json(200, {'ok': True, **studio.update_image_request(body)})
            elif path == '/api/works/media/generate':
                self.send_json(200, {'ok': True, **studio.generate_image_candidate(body)})
            elif path == '/api/works/media/select':
                self.send_json(200, {'ok': True, **studio.select_work_media(body)})
            elif path == '/api/llm/config':
                self.send_json(200, {'ok': True, **studio.save_llm_config(body)})
            elif path == '/api/works/review/decide':
                self.send_json(200, {'ok': True, **studio.decide_review(body)})
            elif path == '/api/works/package':
                self.send_json(200, {'ok': True, **studio.create_package(body)})
            elif path == '/api/draft/save':
                rel = studio.save_draft(body.get('path', ''), body.get('request'))
                self.send_json(200, {'ok': True, 'path': rel})
            elif path == '/api/preview':
                self.send_json(200, {'ok': True, **studio.preview(
                    body.get('request'), body.get('profile'), body.get('kind', 'video'),
                    body.get('motionPlan'),
                    tenant_id=body.get('tenant_id') or body.get('tenantId'),
                    overlay_plan=body.get('textOverlayPlan') or body.get('overlayPlan'))})
            elif path == '/api/video/frame-info':
                self.send_json(200, studio.video_frame_info(body))
            elif path == '/api/video/preview-render':
                self.send_json(200, {'ok': True, **studio.start_video_preview_render(body)})
            elif path == '/api/video/preview-status':
                self.send_json(200, {'ok': True, **studio.video_preview_status(
                    work_id=body.get('workId'),
                    profile_id=body.get('profileId') or body.get('profile'),
                    job_id=body.get('jobId'),
                    request=body.get('request'),
                    motion_plan=body.get('motionPlan'),
                )})
            elif path == '/api/export':
                job_id = studio.start_export(
                    body.get('request'),
                    body.get('outputDir', ''),
                    body.get('profile'),
                    body.get('kind', 'video'),
                    body.get('motionPlan'),
                    work_id=body.get('workId'),
                    tenant_id=body.get('tenant_id') or body.get('tenantId'),
                    overlay_plan=body.get('textOverlayPlan') or body.get('overlayPlan'),
                    captions_mode=body.get('captionsMode'),
                )
                self.send_json(200, {'ok': True, 'jobId': job_id})
            elif path == '/api/queue/plan':
                self.send_json(200, {'ok': True, **studio.queue.plan_batch(body.get('workIds') or [])})
            elif path == '/api/queue/preflight':
                items = body.get('items')
                if items is None and isinstance(body, dict) and (
                    'workId' in body or 'modality' in body or 'profileId' in body
                ):
                    items = [{
                        'workId': body.get('workId'),
                        'modality': body.get('modality'),
                        'profileId': body.get('profileId'),
                    }]
                self.send_json(200, {'ok': True, **studio.queue.preflight(items)})
            elif path == '/api/queue/enqueue':
                batch = studio.queue.enqueue_batch(
                    body.get('items') or [],
                    idempotency_key=body.get('idempotencyKey'),
                    label=body.get('label'),
                )
                self.send_json(200, {'ok': True, 'batch': batch})
            elif path == '/api/queue/cancel':
                item = studio.queue.cancel_item(body.get('itemId'))
                self.send_json(200, {'ok': True, 'item': item})
            elif path == '/api/queue/retry':
                item = studio.queue.retry_item(body.get('itemId'), use_current=bool(body.get('useCurrent')))
                self.send_json(200, {'ok': True, 'item': item})
            elif path == '/api/media/scan':
                self.send_json(200, {'ok': True, 'media': studio.scan_media(body.get('folder', ''))})
            elif path == '/api/media/generate':
                self.send_json(200, {'ok': True, 'written': studio.generate_media(body.get('request'))})
            else:
                self.send_error_json(404, 'rota desconhecida')
        except studio_video_api.VideoApiError as exc:
            self.send_error_json(400, exc.message, {'code': exc.code})
        except studio_connections.ConnectionError_ as exc:
            self.send_error_json(400, exc.message, {'code': exc.code})
        except studio_templates.TemplateConflictError as exc:
            self.send_error_json(409, exc.message, {'code': exc.code})
        except studio_queue.QueueConflictError as exc:
            self.send_error_json(409, exc.message, {'code': exc.code, 'canUseCurrent': exc.can_use_current})
        except PreflightBlocked as exc:
            self.send_error_json(422, str(exc), {
                'preflight': exc.report,
                'code': exc.code,
            })
        except studio_review.ReviewVersionConflictError as exc:
            self.send_error_json(409, str(exc), {'conflict': True})
        except studio_planning.PlanningValidationError as exc:
            self.send_error_json(400, str(exc), {
                'failureCode': exc.failure_code,
                'subject': exc.subject,
                'stage': exc.stage,
            })
        except llm_adapter.LLMTimeoutError as exc:
            self.send_error_json(504, str(exc), {'code': exc.code})
        except llm_adapter.LLMUnavailableError as exc:
            self.send_error_json(503, str(exc), {'code': exc.code})
        except llm_adapter.LLMAdapterError as exc:
            self.send_error_json(400, str(exc), {'code': exc.code})
        except image_adapters.ImageProviderTimeoutError as exc:
            self.send_error_json(504, str(exc), {'code': exc.code})
        except image_adapters.ImageProviderUnavailableError as exc:
            self.send_error_json(503, str(exc), {'code': exc.code})
        except image_adapters.ImageAdapterError as exc:
            self.send_error_json(400, str(exc), {'code': exc.code})
        except (ValueError, OSError, build_video.DeliveryError) as exc:
            self.send_error_json(400, str(exc))
        except RuntimeError as exc:
            self.send_error_json(500, str(exc))


def make_server(root, port, auto_start_queue=True):
    studio = Studio(root, port, auto_start_queue=auto_start_queue)
    handler = type('BoundStudioHandler', (StudioHandler,), {'studio': studio})
    httpd = ThreadingHTTPServer(('127.0.0.1', port), handler)
    studio.port = httpd.server_port
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
    parser.add_argument('--prepare', action='store_true', help='Prepara builds e midias sinteticas dos exemplos antes de iniciar')
    parser.add_argument('--json', action='store_true', help='Emite o resultado de --check/--prepare em JSON')
    args = parser.parse_args(argv)
    root = discover_root(args.root)
    prep = None
    if args.prepare:
        prep = prepare_environment(root)
    readiness = check_readiness(root)
    if args.check or (args.prepare and args.json):
        payload = {**readiness, 'prepare': prep} if prep is not None else readiness
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print_readiness_text(readiness)
            if prep is not None:
                print(f"Preparacao do ambiente: {'OK' if prep['ok'] else 'FALHOU'}")
        ok = readiness['ready'] and (True if prep is None else prep['ok'])
        return 0 if ok else 1
    if prep is not None and not prep['ok']:
        print(json.dumps(prep, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    print_readiness_text(readiness)
    httpd, studio = make_server(root, args.port)
    print(f"Video Studio em http://127.0.0.1:{args.port} (raiz: {root})")
    print("Ctrl+C para encerrar.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        studio.close()
        httpd.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
