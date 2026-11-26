"""Motor de composicao editorial reutilizavel: prova real + destaque editorial.

Gera as midias de cena (PNG estatico ou MP4 sem audio) consumidas por um
VideoRequest v1 a partir de um manifesto editorial por campanha
(``*.editorial.json``). Identidade visual, evidencias, regioes de recorte e
valores verificados vem TODOS do manifesto; nenhum texto, cor ou caminho de
uma marca especifica fica hardcoded aqui.

Componentes (funcoes de layout sobre o mesmo grafo FFmpeg):
  product-context   contexto real do produto (recorte autenticado + titulo)
  product-proof     recorte real em destaque + destaques editoriais verificados
  status-sequence   2-3 estados reais em sequencia com transicoes suaves
  brand-endcard     identidade + CTA (arte aprovada registrada ou logo+texto)
  static-art        arte aprovada registrada, ajustada ao canvas sem deformar

Principios:
  - Evidencia do produto: recorte proporcional da captura real, sem esticar.
  - Destaque editorial: tipografia grande da marca, estilo grafico distinto
    da interface; cada valor aponta para evidencia registrada (arquivo,
    SHA-256, regiao, valor verificado, cena).
  - Movimento embutido na midia de cena (revelacao suave, troca de foco,
    deriva controlada, fade de borda); o renderizador canonico concatena as
    cenas sem alteracao. Nenhum audio em nenhuma saida.
  - Areas seguras por perfil, configuraveis; a previsualizacao com sobreposicao
    e artefato temporario de QC e nunca entra no MP4 final.

CLI (a partir da raiz do checkout):
  python tools/editorial_compose.py --manifest <campanha.editorial.json> \
      --root . --output-dir <dir> [--scene ID] [--safe-area-preview] \
      [--preview-frames-dir <dir>] [--json]

Exit codes: 0 sucesso; 1 falha de render; 2 uso/caminho; 3 manifesto invalido.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import render_local

SCHEMA_VERSION = 1
COMPONENTS = ('product-context', 'product-proof', 'status-sequence',
              'brand-endcard', 'static-art')
HEX_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')
KEBAB_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
FF_TIMEOUT = 300
PROBE_TIMEOUT = 30
EDGE_FADE_S = 0.25
ELEMENT_FADE_S = 0.35
TEXT_WIDTH_FACTOR = 0.62  # estimativa conservadora Arial bold para areas seguras


class EditorialError(Exception):
    """Manifesto ou configuracao invalida; codigo estavel."""

    def __init__(self, code, subject=None):
        super().__init__(f'{code}: {subject}' if subject else code)
        self.code = code
        self.subject = subject


def sha256_file(path):
    with open(render_local.fs_path(path), 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, '/')


def hex_ff(color):
    return '0x' + color.lstrip('#').upper()


def resolve_font(role):
    """Resolve arquivo de fonte em tempo de execucao (nunca caminho fixo no manifesto)."""
    bold = role == 'bold'
    candidates = []
    windir = os.environ.get('WINDIR') or os.environ.get('SYSTEMROOT')
    if windir:
        candidates.append(os.path.join(windir, 'Fonts', 'arialbd.ttf' if bold else 'arial.ttf'))
    for dejavu_dir in ('/usr/share/fonts/truetype/dejavu', '/usr/share/fonts/dejavu'):
        candidates.append(os.path.join(dejavu_dir, 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'))
    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    raise EditorialError('FONT_UNAVAILABLE', role)


def font_ff(role):
    path = resolve_font(role).replace(os.sep, '/')
    return path.replace(':', '\\:')


def esc_text(text):
    out = str(text).replace('\n', ' ')
    for ch in ('\\', "'", ':', ',', '%', ';'):
        out = out.replace(ch, '\\' + ch)
    return out


def probe_dims(path):
    res = subprocess.run([build_video.get_ffprobe(), '-v', 'error', '-select_streams', 'v:0',
                          '-show_entries', 'stream=width,height', '-of', 'json',
                          str(path)], capture_output=True, text=True, timeout=PROBE_TIMEOUT)
    if res.returncode != 0:
        raise EditorialError('ASSET_UNREADABLE', str(path))
    stream = json.loads(res.stdout)['streams'][0]
    return int(stream['width']), int(stream['height'])


def run_ffmpeg(args):
    res = subprocess.run([build_video.get_ffmpeg()] + args, capture_output=True, text=True,
                         encoding='utf-8', errors='replace', timeout=FF_TIMEOUT)
    if res.returncode != 0:
        raise RuntimeError(f'FFmpeg falhou: {(res.stderr or "")[-400:]}')
    return res


def scale_dims(src_w, src_h, target_w):
    """Escala proporcional com altura par; desvio de proporcao registrado."""
    target_h = max(2, int(round(src_h * target_w / src_w / 2.0)) * 2)
    return target_w, target_h


# ---------------------------------------------------------------------------
# Validacao do manifesto (proveniencia, isolamento, portabilidade)
# ---------------------------------------------------------------------------

def _check_rel_path(path, scopes, label):
    if not isinstance(path, str) or not path:
        raise EditorialError('MANIFEST_PATH_INVALID', label)
    norm = path.replace('\\', '/')
    if norm.startswith('/') or ':' in norm or norm != os.path.normpath(norm).replace('\\', '/'):
        raise EditorialError('MANIFEST_PATH_NOT_PORTABLE', f'{label}: {path}')
    if '..' in norm.split('/'):
        raise EditorialError('MANIFEST_PATH_NOT_PORTABLE', f'{label}: {path}')
    if not any(norm.startswith(scope) for scope in scopes):
        raise EditorialError('ASSET_SCOPE_VIOLATION', f'{label}: {path}')
    return norm


def validate_manifest(manifest, root, check_hashes=True):
    if not isinstance(manifest, dict) or manifest.get('schemaVersion') != SCHEMA_VERSION:
        raise EditorialError('MANIFEST_SCHEMA_UNSUPPORTED')
    for key in ('clientId', 'campaignId'):
        if not KEBAB_RE.match(str(manifest.get(key, ''))):
            raise EditorialError('MANIFEST_ID_INVALID', key)
    brand = manifest.get('brand') or {}
    for key in ('primaryColor', 'backgroundColor', 'textColor'):
        if not HEX_RE.match(str(brand.get(key, ''))):
            raise EditorialError('BRAND_COLOR_INVALID', key)
    canvas = manifest.get('canvas') or {}
    for key in ('width', 'height', 'fps'):
        if not isinstance(canvas.get(key), int) or canvas[key] <= 0:
            raise EditorialError('CANVAS_INVALID', key)
    if canvas['width'] % 2 or canvas['height'] % 2:
        raise EditorialError('CANVAS_INVALID', 'dimensoes impares')
    band = manifest.get('captionBand')
    if band is not None:
        if not isinstance(band, dict) or not isinstance(band.get('color'), str):
            raise EditorialError('CAPTION_BAND_INVALID', 'color')
        for key in ('y', 'height'):
            if not isinstance(band.get(key), int) or band[key] < 0 or band[key] % 2:
                raise EditorialError('CAPTION_BAND_INVALID', key)
        if band['height'] == 0 or band['y'] + band['height'] > canvas['height']:
            raise EditorialError('CAPTION_BAND_INVALID', 'geometria')
    scopes = manifest.get('assetScopes') or []
    if not scopes or not all(isinstance(s, str) and s.endswith('/') for s in scopes):
        raise EditorialError('ASSET_SCOPES_INVALID')
    for scope in scopes:
        _check_rel_path(scope + 'x', [scope], 'assetScopes')

    evidence = {}
    for item in manifest.get('evidence', []):
        eid = item.get('id')
        if not eid or eid in evidence:
            raise EditorialError('EVIDENCE_ID_INVALID', str(eid))
        path = _check_rel_path(item.get('path'), scopes, f'evidence {eid}')
        abs_path = os.path.join(root, path)
        if not os.path.isfile(render_local.fs_path(abs_path)):
            raise EditorialError('EVIDENCE_MISSING', path)
        if check_hashes and sha256_file(abs_path) != item.get('sha256'):
            raise EditorialError('EVIDENCE_HASH_MISMATCH', path)
        regions = item.get('regions') or {}
        if not regions:
            raise EditorialError('EVIDENCE_REGIONS_MISSING', eid)
        for name, reg in regions.items():
            if not all(isinstance(reg.get(k), int) and reg[k] >= 0 for k in ('x', 'y', 'w', 'h')) \
                    or reg['w'] < 4 or reg['h'] < 4:
                raise EditorialError('EVIDENCE_REGION_INVALID', f'{eid}/{name}')
        values = item.get('values') or []
        if not values or not all(isinstance(v, str) and v for v in values):
            raise EditorialError('EVIDENCE_VALUES_MISSING', eid)
        evidence[eid] = {**item, 'path': path}

    assets = {}
    for item in manifest.get('assets', []):
        aid = item.get('id')
        if not aid or aid in assets:
            raise EditorialError('ASSET_ID_INVALID', str(aid))
        path = _check_rel_path(item.get('path'), scopes, f'asset {aid}')
        abs_path = os.path.join(root, path)
        if not os.path.isfile(render_local.fs_path(abs_path)):
            raise EditorialError('ASSET_MISSING', path)
        if check_hashes and sha256_file(abs_path) != item.get('sha256'):
            raise EditorialError('ASSET_HASH_MISMATCH', path)
        assets[aid] = {**item, 'path': path}
    if brand.get('logo'):
        path = _check_rel_path(brand['logo'].get('path'), scopes, 'brand.logo')
        if check_hashes and sha256_file(os.path.join(root, path)) != brand['logo'].get('sha256'):
            raise EditorialError('ASSET_HASH_MISMATCH', path)

    safe = manifest.get('safeAreas') or {}
    if not safe:
        raise EditorialError('SAFE_AREAS_MISSING')
    for profile, area in safe.items():
        for key in ('top', 'bottom', 'left', 'right'):
            v = area.get(key)
            if not isinstance(v, (int, float)) or not (0 <= v < 0.5):
                raise EditorialError('SAFE_AREA_INVALID', f'{profile}/{key}')

    scenes = manifest.get('scenes') or []
    if not scenes:
        raise EditorialError('SCENES_MISSING')
    seen = set()
    for scene in scenes:
        sid = scene.get('id')
        if not KEBAB_RE.match(str(sid or '')) or sid in seen:
            raise EditorialError('SCENE_ID_INVALID', str(sid))
        seen.add(sid)
        comp = scene.get('component')
        if comp not in COMPONENTS:
            raise EditorialError('SCENE_COMPONENT_INVALID', f'{sid}: {comp}')
        if not isinstance(scene.get('durationMs'), int) or scene['durationMs'] < 500:
            raise EditorialError('SCENE_DURATION_INVALID', sid)
        _validate_scene_refs(scene, evidence, assets)
    return {'evidence': evidence, 'assets': assets}


def _validate_highlight(hl, evidence, where):
    eid = hl.get('evidenceId')
    ev = evidence.get(eid)
    if not ev:
        raise EditorialError('HIGHLIGHT_EVIDENCE_MISSING', where)
    region = hl.get('region')
    if region not in (ev.get('regions') or {}):
        raise EditorialError('HIGHLIGHT_REGION_MISSING', f'{where}: {region}')
    value = hl.get('value')
    if not value or value not in ev.get('values', []):
        raise EditorialError('HIGHLIGHT_VALUE_UNVERIFIED', f'{where}: {value}')


def _validate_scene_refs(scene, evidence, assets):
    sid = scene['id']
    comp = scene['component']
    if comp in ('static-art', 'brand-endcard'):
        if scene.get('mode') == 'approved-art':
            if scene.get('assetId') not in assets:
                raise EditorialError('SCENE_ASSET_MISSING', sid)
        elif comp == 'static-art':
            raise EditorialError('SCENE_MODE_INVALID', sid)
        elif not (scene.get('ctaText') and scene.get('brandName')):
            raise EditorialError('ENDCARD_TEXT_MISSING', sid)
    if comp == 'status-sequence':
        states = scene.get('states') or []
        if not 2 <= len(states) <= 3:
            raise EditorialError('STATUS_SEQUENCE_LENGTH', sid)
        for st in states:
            for role in ('status', 'time', 'service'):
                _validate_highlight({'evidenceId': st.get('evidenceId'),
                                     'region': st.get('region'), 'value': st.get(role)},
                                    evidence, f'{sid}/{role}')
    parts = scene.get('parts')
    if parts is None and comp in ('product-context', 'product-proof'):
        parts = [scene]
    for part in parts or []:
        pcomp = part.get('component')
        if pcomp not in ('product-context', 'product-proof'):
            raise EditorialError('PART_COMPONENT_INVALID', f'{sid}: {pcomp}')
        proof = part.get('proof') or {}
        ev = evidence.get(proof.get('evidenceId'))
        if not ev or proof.get('region') not in (ev.get('regions') or {}):
            raise EditorialError('PROOF_EVIDENCE_MISSING', sid)
        for hl in part.get('highlights', []):
            _validate_highlight(hl, evidence, sid)


# ---------------------------------------------------------------------------
# Grafo FFmpeg: camadas, revelacao suave, deriva controlada, fade de borda
# ---------------------------------------------------------------------------

class SceneGraph:
    def __init__(self, manifest, root):
        self.manifest = manifest
        self.root = root
        self.canvas = manifest['canvas']
        self.W = self.canvas['width']
        self.H = self.canvas['height']
        self.fps = self.canvas['fps']
        self.bg = hex_ff(manifest['brand']['backgroundColor'])
        self.inputs = []
        self.chains = []
        self.layout = []
        self.geometry = []
        self._last = 'bg'
        self._n = 0

    def begin(self, duration_s, with_bg=True, band=None):
        self.duration = duration_s
        if with_bg:
            self.chains.append(f'color=c={self.bg}:s={self.W}x{self.H}:r={self.fps}:d={duration_s:.3f}[bg]')
            if band:
                nxt = self._next()
                color = hex_ff(self.color_of(band['color']))
                self.chains.append(
                    f"[bg]drawbox=x=0:y={band['y']}:w={self.W}:h={band['height']}:"
                    f"color={color}:t=fill[{nxt}]")
                self._last = nxt
        else:
            self._last = None

    def _input(self, abs_path, duration_s):
        idx = len(self.inputs)
        self.inputs.append(['-loop', '1', '-framerate', str(self.fps),
                            '-t', f'{duration_s:.3f}', '-i', str(abs_path)])
        return idx

    def _next(self):
        self._n += 1
        return f'l{self._n}'

    def color_of(self, token):
        brand = self.manifest['brand']
        if token == 'primary':
            return brand['primaryColor']
        if token == 'text':
            return brand['textColor']
        if token == 'muted':
            return brand.get('mutedColor', '#5A6B72')
        if isinstance(token, str) and token.startswith('func:'):
            return brand['functionalColors'][token[5:]]['text']
        if isinstance(token, str) and token.startswith('funcSurface:'):
            return brand['functionalColors'][token[12:]]['surface']
        if HEX_RE.match(str(token)):
            return token
        raise EditorialError('COLOR_TOKEN_INVALID', str(token))

    def proof(self, evidence, region_name, width, y, t0, t1, drift=6, critical=True):
        reg = evidence['regions'][region_name]
        src_w, src_h = probe_dims(os.path.join(self.root, evidence['path']))
        if reg['x'] + reg['w'] > src_w or reg['y'] + reg['h'] > src_h:
            raise EditorialError('REGION_OUT_OF_BOUNDS', f"{evidence['id']}/{region_name}")
        sw, sh = scale_dims(reg['w'], reg['h'], width)
        x = (self.W - sw) // 2
        idx = self._input(os.path.join(self.root, evidence['path']), max(t1, 1.0))
        lbl = f'p{self._n}'
        fade = ''
        animated = t1 > t0
        if animated:
            fade = (f',format=rgba,fade=t=in:st={t0:.3f}:d={ELEMENT_FADE_S}:alpha=1,'
                    f'fade=t=out:st={max(t0, t1 - ELEMENT_FADE_S):.3f}:d={ELEMENT_FADE_S}:alpha=1')
        self.chains.append(
            f"[{idx}:v]crop={reg['w']}:{reg['h']}:{reg['x']}:{reg['y']},"
            f"scale={sw}:{sh}:flags=lanczos,setsar=1{fade}[{lbl}]")
        if animated and drift:
            yexpr = f"{y}-{drift}*(t-{t0:.3f})/{max(0.001, t1 - t0):.3f}"
            ol = f"overlay={x}:y='{yexpr}':enable='between(t,{t0:.3f},{t1:.3f})'"
        else:
            ol = f'overlay={x}:{y}'
        nxt = self._next()
        self.chains.append(f'[{self._last}][{lbl}]{ol}[{nxt}]')
        self._last = nxt
        ratio_src = reg['w'] / reg['h']
        self.geometry.append({
            'kind': 'proof', 'evidenceId': evidence['id'], 'region': region_name,
            'source': {'x': reg['x'], 'y': reg['y'], 'w': reg['w'], 'h': reg['h']},
            'scaled': {'w': sw, 'h': sh},
            'aspectDeviation': abs(sw / sh - ratio_src) / ratio_src,
        })
        self.layout.append({'kind': 'proof', 'x': x, 'y': y - drift, 'w': sw, 'h': sh + drift,
                            'critical': critical, 'window': [t0, t1]})
        return sw, sh

    def text(self, content, size, color_token, y, t0, t1, role='bold', critical=True, label='text'):
        color = hex_ff(self.color_of(color_token))
        est_w = int(size * TEXT_WIDTH_FACTOR * len(content))
        x = (self.W - est_w) // 2
        alpha = ''
        if t1 > t0:
            a_in = f'min(1,(t-{t0:.3f})/{ELEMENT_FADE_S})'
            a_out = f'max(0,({t1:.3f}-t)/{ELEMENT_FADE_S})'
            alpha = (f":alpha='if(lt(t,{t0:.3f}),0,"
                     f"if(gt(t,{t1 - ELEMENT_FADE_S:.3f}),{a_out},{a_in}))'")
        nxt = self._next()
        self.chains.append(
            f"[{self._last}]drawtext=fontfile='{font_ff(role)}':text='{esc_text(content)}':"
            f"fontsize={size}:fontcolor={color}:x=(w-text_w)/2:y={y}{alpha}[{nxt}]")
        self._last = nxt
        self.layout.append({'kind': label, 'x': x, 'y': y, 'w': est_w, 'h': int(size * 1.2),
                            'critical': critical, 'window': [t0, t1], 'text': content})
        return est_w

    def chip(self, content, size, color_token, surface_token, y, t0, t1, pad_x=48, pad_y=22):
        color = hex_ff(self.color_of(color_token))
        surface = hex_ff(self.color_of(surface_token))
        est_w = int(size * TEXT_WIDTH_FACTOR * len(content))
        box_w = est_w + 2 * pad_x
        box_h = int(size * 1.2) + 2 * pad_y
        box_x = (self.W - box_w) // 2
        cbg, ctxt, clayer = f'cb{self._n}', f'ct{self._n}', f'cl{self._n}'
        self.chains.append(
            f'color=c={surface}:s={box_w}x{box_h}:r={self.fps}:d={self.duration:.3f},'
            f'format=rgba[{cbg}]')
        self.chains.append(
            f"[{cbg}]drawtext=fontfile='{font_ff('bold')}':text='{esc_text(content)}':"
            f"fontsize={size}:fontcolor={color}:x=(w-text_w)/2:y={pad_y}[{ctxt}]")
        fade = ''
        ol_enable = ''
        if t1 > t0:
            fade = (f',fade=t=in:st={t0:.3f}:d={ELEMENT_FADE_S}:alpha=1,'
                    f'fade=t=out:st={max(t0, t1 - ELEMENT_FADE_S):.3f}:d={ELEMENT_FADE_S}:alpha=1')
            ol_enable = f":enable='between(t,{t0:.3f},{t1:.3f})'"
        self.chains.append(f'[{ctxt}]{fade.lstrip(",")}[{clayer}]' if fade
                           else f'[{ctxt}]null[{clayer}]')
        nxt = self._next()
        self.chains.append(f'[{self._last}][{clayer}]overlay={box_x}:{y}{ol_enable}[{nxt}]')
        self._last = nxt
        self.layout.append({'kind': 'status-chip', 'x': box_x, 'y': y, 'w': box_w, 'h': box_h,
                            'critical': True, 'window': [t0, t1], 'text': content})

    def logo(self, logo_path, width, y, t0, t1):
        src_w, src_h = probe_dims(os.path.join(self.root, logo_path))
        sw, sh = scale_dims(src_w, src_h, width)
        x = (self.W - sw) // 2
        idx = self._input(os.path.join(self.root, logo_path), max(t1, 1.0))
        lbl = f'lg{self._n}'
        fade = ''
        if t1 > t0:
            fade = (f',format=rgba,fade=t=in:st={t0:.3f}:d={ELEMENT_FADE_S}:alpha=1,'
                    f'fade=t=out:st={max(t0, t1 - ELEMENT_FADE_S):.3f}:d={ELEMENT_FADE_S}:alpha=1')
        self.chains.append(f'[{idx}:v]scale={sw}:{sh}:flags=lanczos,setsar=1{fade}[{lbl}]')
        nxt = self._next()
        self.chains.append(f'[{self._last}][{lbl}]overlay={x}:{y}[{nxt}]')
        self._last = nxt
        self.layout.append({'kind': 'logo', 'x': x, 'y': y, 'w': sw, 'h': sh,
                            'critical': True, 'window': [t0, t1]})

    def fit_art(self, asset_path):
        idx = self._input(os.path.join(self.root, asset_path), 1.0)
        nxt = self._next()
        self.chains.append(
            f'[{idx}:v]scale={self.W}:{self.H}:force_original_aspect_ratio=decrease:flags=lanczos,'
            f'pad={self.W}:{self.H}:(ow-iw)/2:(oh-ih)/2:color={self.bg},setsar=1[{nxt}]')
        self._last = nxt
        self.layout.append({'kind': 'approved-art', 'x': 0, 'y': 0, 'w': self.W, 'h': self.H,
                            'critical': False, 'window': [0, 0]})

    def finish_video(self, duration_s):
        self.chains.append(
            f'[{self._last}]fade=t=in:st=0:d={EDGE_FADE_S}:color={self.bg},'
            f'fade=t=out:st={duration_s - EDGE_FADE_S:.3f}:d={EDGE_FADE_S}:color={self.bg},'
            f'format=yuv420p[v]')

    def finish_static(self):
        self.chains.append(f'[{self._last}]format=rgb24[v]')

    def render(self, out_path, duration_s, video):
        args = ['-y', '-v', 'error']
        for inp in self.inputs:
            args += inp
        args += ['-filter_complex', ';'.join(self.chains), '-map', '[v]']
        if video:
            args += ['-an', '-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p',
                     '-r', str(self.fps), '-t', f'{duration_s:.3f}',
                     '-movflags', '+faststart', str(out_path)]
        else:
            args += ['-frames:v', '1', str(out_path)]
        run_ffmpeg(args)


# ---------------------------------------------------------------------------
# Componentes
# ---------------------------------------------------------------------------

def _part_window(part, scene_duration_s):
    t0 = part.get('startMs', 0) / 1000.0
    t1 = part.get('endMs', int(scene_duration_s * 1000)) / 1000.0
    return t0, t1


def compose_product_part(graph, part, evidence, t0, t1):
    layout = part.get('layout') or {}
    proof = part['proof']
    ev = evidence[proof['evidenceId']]
    heading = part.get('heading')
    if heading:
        graph.text(heading['text'], heading['size'], heading.get('color', 'primary'),
                   heading['y'], t0, t1, label='heading')
    graph.proof(ev, proof['region'], proof.get('width', 900), proof['y'], t0, t1,
                drift=proof.get('drift', 6))
    for hl in part.get('highlights', []):
        if hl.get('chip'):
            graph.chip(hl['value'], hl['size'], hl.get('color', 'text'),
                       hl.get('surface', 'primary'), hl['y'], t0, t1)
        else:
            graph.text(hl['value'], hl['size'], hl.get('color', 'primary'), hl['y'], t0, t1,
                       label=f"highlight-{hl.get('role', 'value')}")
    micro = part.get('microcopy')
    if micro:
        graph.text(micro['text'], micro['size'], micro.get('color', 'muted'), micro['y'],
                   t0, t1, role='regular', critical=False, label='microcopy')


def compose_scene(manifest, refs, root, scene, out_dir):
    duration_s = scene['durationMs'] / 1000.0
    comp = scene['component']
    graph = SceneGraph(manifest, root)
    video = comp in ('product-context', 'product-proof', 'status-sequence') or \
        (comp == 'brand-endcard' and scene.get('mode') != 'approved-art')
    needs_bg = comp not in ('static-art',) and not (
        comp == 'brand-endcard' and scene.get('mode') == 'approved-art')
    band = manifest.get('captionBand') if comp in (
        'product-context', 'product-proof', 'status-sequence') else None
    graph.begin(duration_s if video else 1.0, with_bg=needs_bg, band=band)
    provenance = []

    if comp in ('product-context', 'product-proof'):
        parts = scene.get('parts') or [{**scene, 'component': comp}]
        for part in parts:
            t0, t1 = _part_window(part, duration_s)
            compose_product_part(graph, part, refs['evidence'], t0, t1)
            provenance.append({'part': part.get('component'), 'window': [t0, t1],
                               'evidenceId': part['proof']['evidenceId'],
                               'region': part['proof']['region'],
                               'highlights': [{'value': h['value'], 'role': h.get('role'),
                                               'evidenceId': h['evidenceId'], 'region': h['region']}
                                              for h in part.get('highlights', [])]})
    elif comp == 'status-sequence':
        states = scene['states']
        layout = scene.get('layout') or {}
        step = duration_s / len(states)
        for i, st in enumerate(states):
            t0, t1 = i * step, (i + 1) * step
            ev = refs['evidence'][st['evidenceId']]
            graph.proof(ev, st['region'], layout.get('proofWidth', 900),
                        layout.get('proofY', 360), t0, t1, drift=4)
            graph.text(st['status'], layout.get('statusSize', 130),
                       f"func:{st['status']}", layout.get('statusY', 680), t0, t1,
                       label='highlight-status')
            line = f"{st['time']} · {st['service']}"
            graph.text(line, layout.get('lineSize', 46), 'text', layout.get('lineY', 880),
                       t0, t1, label='highlight-line')
            micro = layout.get('microcopy')
            if micro:
                graph.text(micro['text'], micro['size'], micro.get('color', 'muted'),
                           micro['y'], t0, t1, role='regular', critical=False, label='microcopy')
            provenance.append({'state': st['status'], 'window': [t0, t1],
                               'evidenceId': st['evidenceId'], 'region': st['region'],
                               'values': {'status': st['status'], 'time': st['time'],
                                          'service': st['service']}})
    elif comp == 'brand-endcard' and scene.get('mode') == 'approved-art':
        graph.fit_art(refs['assets'][scene['assetId']]['path'])
        provenance.append({'assetId': scene['assetId'], 'mode': 'approved-art'})
        video = False
    elif comp == 'brand-endcard':
        brand = manifest['brand']
        if brand.get('logo'):
            graph.logo(brand['logo']['path'], scene.get('logoWidth', 360),
                       scene.get('logoY', 560), 0, duration_s)
        graph.text(scene['brandName'], scene.get('nameSize', 80), 'primary',
                   scene.get('nameY', 1000), 0, duration_s, label='brand-name')
        graph.text(scene['ctaText'], scene.get('ctaSize', 56), 'text',
                   scene.get('ctaY', 1140), 0, duration_s, label='cta')
        provenance.append({'mode': 'generated', 'logo': (brand.get('logo') or {}).get('path')})
    elif comp == 'static-art':
        graph.fit_art(refs['assets'][scene['assetId']]['path'])
        provenance.append({'assetId': scene['assetId'], 'mode': 'approved-art'})
        video = False

    ext = '.mp4' if video else '.png'
    out_path = os.path.join(out_dir, scene['id'] + ext)
    if video:
        graph.finish_video(duration_s)
    else:
        graph.finish_static()
    graph.render(out_path, duration_s, video)
    return {
        'sceneId': scene['id'], 'component': comp, 'media': out_path,
        'mediaType': 'video' if video else 'image', 'durationMs': scene['durationMs'],
        'sha256': sha256_file(out_path), 'bytes': os.path.getsize(render_local.fs_path(out_path)),
        'layout': graph.layout, 'geometry': graph.geometry, 'provenance': provenance,
    }


# ---------------------------------------------------------------------------
# Areas seguras
# ---------------------------------------------------------------------------

def safe_area_rect(manifest, profile):
    area = manifest['safeAreas'][profile]
    W, H = manifest['canvas']['width'], manifest['canvas']['height']
    return {
        'x': int(area['left'] * W), 'y': int(area['top'] * H),
        'w': int((1 - area['left'] - area['right']) * W),
        'h': int((1 - area['top'] - area['bottom']) * H),
    }


def check_safe_areas(manifest, scene_reports):
    results = []
    for profile in manifest['safeAreas']:
        rect = safe_area_rect(manifest, profile)
        violations = []
        for report in scene_reports:
            for el in report['layout']:
                if not el.get('critical'):
                    continue
                if el['x'] < rect['x'] or el['y'] < rect['y'] or \
                        el['x'] + el['w'] > rect['x'] + rect['w'] or \
                        el['y'] + el['h'] > rect['y'] + rect['h']:
                    violations.append({'sceneId': report['sceneId'], 'element': el['kind'],
                                       'text': el.get('text'), 'rect': el})
        results.append({'profile': profile, 'usefulRect': rect, 'violations': violations})
    return results


def safe_area_overlay(manifest, profile, out_path):
    """PNG de sobreposicao das zonas potencialmente cobertas (somente QC)."""
    W, H = manifest['canvas']['width'], manifest['canvas']['height']
    area = manifest['safeAreas'][profile]
    top = int(area['top'] * H)
    bottom = int(area['bottom'] * H)
    left = int(area['left'] * W)
    right = int(area['right'] * W)
    red = '0xFF3B30@0.38'
    chains = [
        f'color=c=black@0:s={W}x{H}:d=1,format=rgba[base]',
        f'[base]drawbox=x=0:y=0:w={W}:h={top}:color={red}:t=fill[a]',
        f'[a]drawbox=x=0:y={H - bottom}:w={W}:h={bottom}:color={red}:t=fill[b]',
        f'[b]drawbox=x=0:y={top}:w={left}:h={H - top - bottom}:color={red}:t=fill[c]',
        f'[c]drawbox=x={W - right}:y={top}:w={right}:h={H - top - bottom}:color={red}:t=fill[d]',
        f"[d]drawtext=fontfile='{font_ff('bold')}':text='{esc_text(profile)}':"
        f'fontsize=34:fontcolor=white:x=(w-text_w)/2:y={top + 12}[e]',
    ]
    run_ffmpeg(['-y', '-v', 'error', '-filter_complex', ';'.join(chains),
                '-map', '[e]', '-frames:v', '1', str(out_path)])


def safe_area_previews(manifest, frames_dir, out_dir):
    """Compoe a sobreposicao de areas seguras sobre frames existentes (QC)."""
    os.makedirs(render_local.fs_path(out_dir), exist_ok=True)
    frames = sorted(f for f in os.listdir(render_local.fs_path(frames_dir))
                    if f.lower().endswith('.png'))
    outputs = []
    for profile in manifest['safeAreas']:
        overlay = os.path.join(out_dir, f'overlay-{profile}.png')
        safe_area_overlay(manifest, profile, overlay)
        for frame in frames:
            dst = os.path.join(out_dir, f'{profile}--{frame}')
            run_ffmpeg(['-y', '-v', 'error',
                        '-i', os.path.join(frames_dir, frame), '-i', overlay,
                        '-filter_complex', '[0:v][1:v]overlay=0:0[v]',
                        '-map', '[v]', '-frames:v', '1', str(dst)])
            outputs.append(dst)
    return outputs


# ---------------------------------------------------------------------------
# Orquestracao da campanha
# ---------------------------------------------------------------------------

def compose_campaign(manifest_path, root, output_dir, scene_ids=None):
    root = os.path.realpath(root)
    with open(render_local.fs_path(manifest_path), 'r', encoding='utf-8') as handle:
        manifest = json.load(handle)
    refs = validate_manifest(manifest, root)
    os.makedirs(render_local.fs_path(output_dir), exist_ok=True)
    reports = []
    for scene in manifest['scenes']:
        if scene_ids and scene['id'] not in scene_ids:
            continue
        reports.append(compose_scene(manifest, refs, root, scene, output_dir))
    safe = check_safe_areas(manifest, reports)
    violations = [v for entry in safe for v in entry['violations']]
    if violations:
        raise EditorialError('SAFE_AREA_VIOLATION', json.dumps(violations[:4], ensure_ascii=False))
    report = {
        'schemaVersion': 1,
        'clientId': manifest['clientId'],
        'campaignId': manifest['campaignId'],
        'canvas': manifest['canvas'],
        'captionBand': manifest.get('captionBand'),
        'fonts': {'bold': resolve_font('bold'), 'regular': resolve_font('regular')},
        'ffmpeg': build_video.get_ffmpeg(),
        'scenes': reports,
        'safeAreas': safe,
        'evidence': [
            {'id': eid, 'path': ev['path'], 'sha256': ev['sha256'],
             'regions': ev['regions'], 'values': ev['values']}
            for eid, ev in refs['evidence'].items()
        ],
    }
    report_path = os.path.join(output_dir, 'composition-report.json')
    with open(render_local.fs_path(report_path), 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='Composicao editorial reutilizavel (prova real + destaque)')
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--root', default=os.getcwd())
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--scene', action='append', default=None)
    parser.add_argument('--safe-area-preview', action='store_true')
    parser.add_argument('--preview-frames-dir', default=None)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    root = os.path.realpath(args.root)
    try:
        render_local.ensure_video_tools(root)
        report = compose_campaign(args.manifest, root, args.output_dir, args.scene)
        previews = []
        if args.safe_area_preview:
            if not args.preview_frames_dir:
                print('Erro: --safe-area-preview exige --preview-frames-dir', file=sys.stderr)
                return 2
            with open(render_local.fs_path(args.manifest), 'r', encoding='utf-8') as handle:
                manifest = json.load(handle)
            previews = safe_area_previews(manifest, args.preview_frames_dir,
                                          os.path.join(args.output_dir, 'safe-area-previews'))
    except EditorialError as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 3
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({'status': 'completed', 'scenes': [r['sceneId'] for r in report['scenes']],
                          'report': rel(root, os.path.join(args.output_dir, 'composition-report.json')),
                          'safeAreaPreviews': [rel(root, p) for p in previews]}, ensure_ascii=False, indent=2))
    else:
        print(f"Composicao concluida: {len(report['scenes'])} cenas em {args.output_dir}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())