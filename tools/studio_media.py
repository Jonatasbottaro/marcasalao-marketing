"""Biblioteca de midia por trabalho conectada ao Planejamento do Studio local.

Cada trabalho tem uma biblioteca (``media-library.json``) com:
  - assets: midias logicas reutilizaveis, cada uma com versoes imutaveis
    (ID proprio, SHA-256, dimensoes, origem, licenca e proveniencia);
  - anchors: referencias visuais VisualAnchor v1 vinculadas a uma versao;
  - requests: pedidos visuais ImageRequest v1 derivados do descritor de uma
    cena ou card, com candidatos, tentativas e historico;
  - selections: vinculo alvo (cena/card) -> asset -> versao escolhida.

A selecao alimenta o catalogo de midia do Planejamento e o fluxo de previa de
diferencas existente; o vinculo chega ao rascunho pelos campos atuais
(``mediaId`` + ``media[]``). O AssetManifest do render materializa caminho,
origem, licenca e hash da versao selecionada.

Escrita atomica, concorrencia otimista por fingerprint e contencao a raiz.
Trabalhos legados abrem com a biblioteca inicializada a partir das midias ja
referenciadas nos rascunhos. Nenhuma chamada externa acontece aqui sem acao
confirmada do operador (ver image_adapters.py).
"""

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid

import image_adapters
import render_local
import studio_connections
import studio_review

LIBRARY_SCHEMA_VERSION = 1
CATEGORIES = ('illustration', 'screenshot', 'photo', 'logo', 'other')
# Importacao de gravacoes MP4 H.264: limite documentado de 256 MiB por arquivo,
# escrita em blocos de ate 4 MiB na area temporaria da tarefa antes da promocao.
MAX_VIDEO_IMPORT_BYTES = 256 * 1024 * 1024
VIDEO_IMPORT_CHUNK_BYTES = 4 * 1024 * 1024
VIDEO_IMPORT_DIR_REL = '.workspace/tmp/studio-video-imports'
_VIDEO_IMPORT_SESSIONS = {}
ASPECT_GEOMETRY = {
    '9:16': (1080, 1920),
    '1:1': (1080, 1080),
    '16:9': (1920, 1080),
    '4:5': (1080, 1350),
}
ORIGIN_LABELS = {
    'imported-manual': 'Importacao manual',
    'imported-recording': 'Gravacao importada',
    'external-tool': 'Ferramenta externa (importada)',
    'generated-simulator': 'Ilustracao gerada (simulador)',
    'generated-google-gemini': 'Ilustracao gerada (Google Gemini)',
    'synthetic-demo': 'Ficticia de demonstracao',
    'studio-work': 'Arquivo do trabalho',
    'screenshot': 'Captura / evidencia funcional',
}
KEBAB_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


def _now():
    return studio_review.now_iso()


def _sha(value):
    return studio_review.canonical_sha256(value)


def _slug(text, fallback='midia'):
    import unicodedata
    norm = unicodedata.normalize('NFKD', str(text or ''))
    cleaned = ''.join(ch for ch in norm if not unicodedata.combining(ch)).lower()
    cleaned = re.sub(r'[^a-z0-9]+', '-', cleaned).strip('-')
    return cleaned or fallback


def library_file_rel(wpaths):
    return wpaths.get('mediaLibraryFile') or f"{wpaths['workDir']}/media-library.json"


def _new_version_id():
    return f'v-{uuid.uuid4().hex[:10]}'


def _clean_text(value, field, max_len=120, allow_empty=False):
    text = str(value or '').strip()
    if len(text) > max_len or any(ord(ch) < 32 for ch in text):
        raise ValueError(f'{field} invalido (ate {max_len} caracteres, sem caracteres de controle)')
    if not text and not allow_empty:
        raise ValueError(f'{field} nao pode ser vazio')
    return text


def _category_for(origin, requested=None):
    if requested in CATEGORIES:
        return requested
    if str(origin).startswith('generated-'):
        return 'illustration'
    if origin == 'screenshot':
        return 'screenshot'
    return 'other'


# ---------------------------------------------------------------------------
# Carga, inicializacao legada e persistencia
# ---------------------------------------------------------------------------

def _legacy_version_id(rel_path):
    return 'v-' + hashlib.sha1(rel_path.encode('utf-8')).hexdigest()[:10]


def _legacy_created_at(studio, rel_path):
    try:
        abs_path = studio.confine(rel_path)
        mtime = os.path.getmtime(render_local.fs_path(abs_path))
        from datetime import datetime, timezone
        return datetime.fromtimestamp(mtime, timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    except (ValueError, OSError):
        return '1970-01-01T00:00:00Z'


def _version_from_existing_file(studio, rel_path, origin, license_value, category, media_type='image'):
    version = {
        'versionId': _legacy_version_id(rel_path),
        'path': rel_path,
        'origin': origin,
        'license': license_value,
        'simulated': origin == 'generated-simulator',
        'createdAt': _legacy_created_at(studio, rel_path),
        'requestId': None,
        'candidateId': None,
        'provenance': None,
        'missing': True,
        'kind': media_type,
    }
    try:
        abs_path = studio.confine(rel_path)
        fs = render_local.fs_path(abs_path)
        if os.path.isfile(fs):
            if media_type == 'video':
                info = inspect_video_file(abs_path, root=studio.root)
                version.update({
                    'sha256': render_local.sha256_file(abs_path),
                    'bytes': os.path.getsize(fs),
                    'width': info['width'],
                    'height': info['height'],
                    'format': 'mp4',
                    'codec': info['codec'],
                    'durationSeconds': info['durationSeconds'],
                    'missing': False,
                })
            else:
                with open(fs, 'rb') as handle:
                    data = handle.read()
                info = image_adapters.inspect_image_bytes(data)
                version.update({
                    'sha256': render_local.sha256_file(abs_path),
                    'bytes': info['bytes'],
                    'width': info['width'],
                    'height': info['height'],
                    'format': info['format'],
                    'missing': False,
                })
    except (ValueError, OSError, RuntimeError):
        pass
    return version


def _initialize_legacy_library(studio, work_id, wpaths, video_req, carousel_req):
    assets = []
    seen_ids = set()
    seen_paths = set()
    for req in (video_req or {}, carousel_req or {}):
        for item in req.get('media') or []:
            if not isinstance(item, dict) or not item.get('path'):
                continue
            mid = item.get('id') or _slug(os.path.splitext(os.path.basename(item['path']))[0])
            if mid in seen_ids or item['path'] in seen_paths:
                continue
            seen_ids.add(mid)
            seen_paths.add(item['path'])
            origin = item.get('origin') or 'studio-work'
            license_value = item.get('license') or 'pending'
            media_type = item.get('type') if item.get('type') in ('image', 'video') else 'image'
            version = _version_from_existing_file(studio, item['path'], origin, license_value,
                                                  _category_for(origin), media_type=media_type)
            assets.append({
                'id': mid,
                'name': os.path.basename(item['path']),
                'category': _category_for(origin),
                'createdAt': version['createdAt'],
                'versions': [version],
                'selectedVersionId': version['versionId'],
            })
    return {
        'schemaVersion': LIBRARY_SCHEMA_VERSION,
        'workId': work_id,
        'updatedAt': max([a['createdAt'] for a in assets], default='1970-01-01T00:00:00Z'),
        'assets': assets,
        'anchors': [],
        'requests': [],
        'selections': [],
    }


def load_library(studio, work_id, work_doc, wpaths, video_req, carousel_req):
    path = studio.confine_workspace(library_file_rel(wpaths))
    raw = studio_review._read_json_safe(path)
    if isinstance(raw, dict) and raw.get('schemaVersion') == LIBRARY_SCHEMA_VERSION:
        raw.setdefault('assets', [])
        raw.setdefault('anchors', [])
        raw.setdefault('requests', [])
        raw.setdefault('selections', [])
        return raw, True
    return _initialize_legacy_library(studio, work_id, wpaths, video_req, carousel_req), False


def save_library(studio, wpaths, library):
    library['updatedAt'] = _now()
    studio_review.atomic_write_json(studio.confine_workspace(library_file_rel(wpaths)), library)
    return library


def library_fingerprint(library):
    return _sha(library)


def _check_expected(library, body):
    expected = body.get('expectedLibraryFingerprint')
    if expected is not None and expected != library_fingerprint(library):
        raise studio_review.ReviewVersionConflictError(
            'A biblioteca de midia mudou enquanto voce editava (outro pedido, importacao ou selecao). '
            'Atualize a tela de Midias e confira antes de repetir a acao.'
        )


def _find_asset(library, asset_id):
    return next((a for a in library['assets'] if a['id'] == asset_id), None)


def _find_version(asset, version_id):
    return next((v for v in asset['versions'] if v['versionId'] == version_id), None)


def _find_request(library, request_id):
    return next((r for r in library['requests'] if r['request']['id'] == request_id), None)


def _find_anchor(library, anchor_id):
    return next((a for a in library['anchors'] if a['anchor']['id'] == anchor_id), None)


def _unique_asset_id(library, base_id):
    used = {a['id'] for a in library['assets']}
    mid = base_id
    idx = 2
    while mid in used:
        mid = f'{base_id}-{idx}'
        idx += 1
    return mid


# ---------------------------------------------------------------------------
# Contexto do pedido e marcacao de candidatos desatualizados
# ---------------------------------------------------------------------------

def request_context_sha(fields, anchor_link):
    return _sha({
        'target': fields['target'],
        'descriptor': fields['descriptor'],
        'prompt': fields['prompt'],
        'purpose': fields['purpose'],
        'framing': fields['framing'],
        'aspectRatio': fields['aspectRatio'],
        'geometry': fields['geometry'],
        'anchor': anchor_link,
    })


def _anchor_link_for(library, anchor_id, send_to_provider):
    if not anchor_id:
        return None
    record = _find_anchor(library, anchor_id)
    if not record:
        raise ValueError(f'referencia visual "{anchor_id}" nao encontrada neste trabalho')
    ref = record['anchor']['reference']
    return {
        'anchorId': anchor_id,
        'versionId': ref['versionId'],
        'sha256': ref['sha256'],
        'sendToProvider': bool(send_to_provider),
    }


def effective_context_sha(library, req_entry):
    """Contexto vigente do pedido: muda se o texto ou a referencia mudaram."""
    req = req_entry['request']
    link = req.get('anchor')
    current_link = None
    if link:
        record = _find_anchor(library, link['anchorId'])
        if record:
            ref = record['anchor']['reference']
            current_link = {
                'anchorId': link['anchorId'],
                'versionId': ref['versionId'],
                'sha256': ref['sha256'],
                'sendToProvider': link['sendToProvider'],
            }
        else:
            current_link = link
    return request_context_sha({
        'target': req['target'],
        'descriptor': req['context']['descriptor'],
        'prompt': req['prompt'],
        'purpose': req['purpose'],
        'framing': req['framing'],
        'aspectRatio': req['aspectRatio'],
        'geometry': req['geometry'],
    }, current_link)


def _anchor_doc_for_request(library, req):
    link = req.get('anchor')
    if not link:
        return None
    record = _find_anchor(library, link['anchorId'])
    return record['anchor'] if record else None


# ---------------------------------------------------------------------------
# Validacao dos contratos pelo nucleo (ponte Node)
# ---------------------------------------------------------------------------

def _validate_with_bridge(studio, flag, doc, label):
    import shutil
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Node.js nao encontrado no PATH para validar o contrato visual.')
    bridge = os.path.join(studio.root, 'tools', 'render_bridge.mjs')
    os.makedirs(studio.drafts_dir, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='media-contract-', suffix='.json', dir=studio.drafts_dir)
    os.close(fd)
    try:
        studio_review.atomic_write_json(tmp, doc)
        res = subprocess.run(
            [node, bridge, flag, tmp, '--root', studio.root],
            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60,
        )
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    try:
        payload = json.loads((res.stdout or '').strip() or '{}')
    except ValueError:
        payload = {}
    if res.returncode != 0 or not payload.get('ok'):
        code = payload.get('failureCode') or 'MEDIA_CONTRACT_INVALID'
        subject = payload.get('subject') or ''
        raise ValueError(
            f'{label} fora do contrato v1 ({code} {subject}). '
            'Corrija os campos antes de confirmar.'
        )
    return payload


# ---------------------------------------------------------------------------
# Escrita de versoes (atomica, com validacao pelo conteudo)
# ---------------------------------------------------------------------------

def _write_version_file(studio, wpaths, asset_id, version_id, data, fmt):
    ext = image_adapters.extension_for_format(fmt)
    rel = f"{wpaths['mediaDir']}/library/{asset_id}/{version_id}{ext}"
    target = studio.confine_workspace(rel)
    fs = render_local.fs_path
    parent = os.path.dirname(target)
    os.makedirs(fs(parent), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.tmp-media-', suffix=ext, dir=fs(parent))
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
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
    return studio.rel(target)


def _create_version(studio, wpaths, asset_id, data, origin, license_value,
                    request_id=None, candidate_id=None, provenance=None, simulated=False):
    info = image_adapters.inspect_image_bytes(data)
    version_id = _new_version_id()
    rel = _write_version_file(studio, wpaths, asset_id, version_id, data, info['format'])
    abs_path = studio.confine(rel)
    return {
        'versionId': version_id,
        'path': rel,
        'sha256': render_local.sha256_file(abs_path),
        'bytes': info['bytes'],
        'width': info['width'],
        'height': info['height'],
        'format': info['format'],
        'kind': 'image',
        'origin': origin,
        'license': license_value,
        'simulated': bool(simulated),
        'createdAt': _now(),
        'requestId': request_id,
        'candidateId': candidate_id,
        'provenance': provenance,
        'missing': False,
    }


def _read_import_bytes(studio, body):
    if body.get('dataBase64'):
        try:
            data = base64.b64decode(body['dataBase64'], validate=True)
        except (ValueError, TypeError):
            raise ValueError('conteudo base64 da imagem invalido; reenvie o arquivo')
        return data, str(body.get('fileName') or 'imagem.png')
    source = str(body.get('sourcePath') or '').strip()
    if not source:
        raise ValueError('informe o arquivo (dataBase64) ou um caminho de origem confinado a raiz (sourcePath)')
    abs_path = studio.confine(source)
    if not os.path.isfile(render_local.fs_path(abs_path)):
        raise ValueError('arquivo de origem ausente')
    if os.path.getsize(render_local.fs_path(abs_path)) > image_adapters.MAX_IMAGE_BYTES:
        raise ValueError(f'imagem acima do limite de {image_adapters.MAX_IMAGE_BYTES // (1024 * 1024)} MB')
    with open(render_local.fs_path(abs_path), 'rb') as handle:
        return handle.read(), os.path.basename(abs_path)


# ---------------------------------------------------------------------------
# Importacao de gravacoes MP4 H.264 (blocos + FFprobe + promocao conjunta)
# ---------------------------------------------------------------------------

def inspect_video_file(abs_path, root=None):
    """Valida o conteudo com FFprobe: MP4 H.264, dimensoes pares, duracao > 0."""
    import build_video
    try:
        render_local.ensure_video_tools(root or os.getcwd())
    except build_video.DeliveryError:
        pass
    try:
        info = render_local.probe_asset(os.path.dirname(abs_path), abs_path)
    except build_video.DeliveryError as exc:
        raise ValueError(f'gravacao ilegivel pelo FFprobe: {exc}')
    streams = info.get('streams', [])
    video = next((s for s in streams if s.get('codec_type') == 'video'), None)
    if not video:
        raise ValueError('gravacao sem faixa de video')
    if video.get('codec_name') != 'h264':
        raise ValueError(f'codec de video nao suportado: {video.get("codec_name")} (use MP4 H.264)')
    format_name = (info.get('format', {}).get('format_name') or '')
    if 'mp4' not in format_name:
        raise ValueError(f'conteiner nao suportado: {format_name} (use MP4)')
    width, height = int(video.get('width') or 0), int(video.get('height') or 0)
    if width <= 0 or height <= 0 or width % 2 or height % 2:
        raise ValueError(f'dimensoes invalidas: {width}x{height}')
    raw_dur = video.get('duration') or info.get('format', {}).get('duration')
    try:
        duration_s = float(raw_dur)
    except (TypeError, ValueError):
        raise ValueError('duracao da gravacao indisponivel')
    if duration_s <= 0:
        raise ValueError('duracao da gravacao invalida')
    return {'width': width, 'height': height, 'codec': 'h264', 'durationSeconds': round(duration_s, 3)}


def _video_import_session_dir(studio, upload_id):
    return studio.confine(os.path.join(VIDEO_IMPORT_DIR_REL, upload_id))


def start_video_import(studio, work_id, body):
    if not isinstance(body, dict):
        raise ValueError('payload de importacao de gravacao invalido')
    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, _, _ = studio_review._read_work_core(studio, work_id)
        library, _ = load_library(studio, work_id, work_doc, wpaths, video_req, carousel_req)
        _check_expected(library, body)
        file_name = _clean_text(body.get('fileName') or 'gravacao.mp4', 'fileName')
        if not file_name.lower().endswith('.mp4'):
            raise ValueError('a gravacao deve ser um arquivo .mp4 (H.264)')
        total = body.get('totalBytes')
        if not isinstance(total, int) or total < 1 or total > MAX_VIDEO_IMPORT_BYTES:
            raise ValueError(f'tamanho invalido: a gravacao deve ter entre 1 byte e '
                             f'{MAX_VIDEO_IMPORT_BYTES // (1024 * 1024)} MiB')
        asset_id = str(body.get('assetId') or '').strip() or None
        if asset_id:
            if not KEBAB_RE.match(asset_id):
                raise ValueError('assetId deve usar kebab-case')
            if not _find_asset(library, asset_id):
                raise ValueError(f'midia "{asset_id}" nao encontrada na biblioteca deste trabalho')
        upload_id = f'up-{uuid.uuid4().hex[:12]}'
        session_dir = _video_import_session_dir(studio, upload_id)
        os.makedirs(render_local.fs_path(session_dir), exist_ok=True)
        _VIDEO_IMPORT_SESSIONS[upload_id] = {
            'workId': work_id,
            'fileName': file_name,
            'totalBytes': total,
            'received': 0,
            'origin': _clean_text(body.get('origin') or 'imported-manual', 'origin'),
            'license': _clean_text(body.get('license') or 'pending', 'license'),
            'assetId': asset_id,
            'partPath': os.path.join(session_dir, 'payload.part'),
        }
        return {'uploadId': upload_id, 'chunkBytes': VIDEO_IMPORT_CHUNK_BYTES,
                'maxBytes': MAX_VIDEO_IMPORT_BYTES}


def chunk_video_import(studio, body):
    if not isinstance(body, dict):
        raise ValueError('payload de bloco invalido')
    upload_id = str(body.get('uploadId') or '')
    with studio_review._STATE_LOCK:
        session = _VIDEO_IMPORT_SESSIONS.get(upload_id)
        if not session:
            raise ValueError('upload desconhecido ou expirado; reinicie a importacao')
        offset = body.get('offset')
        if not isinstance(offset, int) or offset != session['received']:
            raise ValueError(f'bloco fora de ordem: esperado offset {session["received"]}')
        try:
            data = base64.b64decode(body.get('dataBase64') or '', validate=True)
        except (ValueError, TypeError):
            raise ValueError('bloco base64 invalido')
        if not data or len(data) > VIDEO_IMPORT_CHUNK_BYTES:
            raise ValueError(f'bloco deve ter entre 1 byte e {VIDEO_IMPORT_CHUNK_BYTES // (1024 * 1024)} MiB')
        if session['received'] + len(data) > session['totalBytes']:
            raise ValueError('blocos excedem o tamanho declarado da gravacao')
        with open(render_local.fs_path(session['partPath']), 'ab') as handle:
            handle.write(data)
        session['received'] += len(data)
        return {'received': session['received'], 'totalBytes': session['totalBytes']}


def cancel_video_import(studio, body):
    upload_id = str((body or {}).get('uploadId') or '')
    with studio_review._STATE_LOCK:
        session = _VIDEO_IMPORT_SESSIONS.pop(upload_id, None)
        if session:
            shutil.rmtree(render_local.fs_path(os.path.dirname(session['partPath']), force=True),
                          ignore_errors=True)
        return {'cancelled': bool(session)}


def finish_video_import(studio, work_id, body):
    """Promove o arquivo e o registro da biblioteca juntos, ou recupera o estado anterior."""
    import shutil as _shutil
    upload_id = str((body or {}).get('uploadId') or '')
    with studio_review._STATE_LOCK:
        session = _VIDEO_IMPORT_SESSIONS.get(upload_id)
        if not session or session['workId'] != work_id:
            raise ValueError('upload desconhecido para este trabalho; reinicie a importacao')
        if session['received'] != session['totalBytes']:
            raise ValueError(f'upload incompleto: {session["received"]} de {session["totalBytes"]} bytes')
        part_path = session['partPath']
        try:
            info = inspect_video_file(part_path, root=studio.root)
        except ValueError:
            _VIDEO_IMPORT_SESSIONS.pop(upload_id, None)
            _shutil.rmtree(render_local.fs_path(os.path.dirname(part_path), force=True), ignore_errors=True)
            raise
        work_doc, wpaths, video_req, carousel_req, _, _ = studio_review._read_work_core(studio, work_id)
        library, _ = load_library(studio, work_id, work_doc, wpaths, video_req, carousel_req)
        asset_id = session['assetId']
        if asset_id:
            asset = _find_asset(library, asset_id)
        else:
            asset_id = _unique_asset_id(library, _slug(os.path.splitext(session['fileName'])[0]))
            asset = {
                'id': asset_id,
                'name': session['fileName'],
                'category': 'other',
                'createdAt': _now(),
                'versions': [],
                'selectedVersionId': None,
            }
            library['assets'].append(asset)
        version_id = _new_version_id()
        rel = f"{wpaths['mediaDir']}/library/{asset_id}/{version_id}.mp4"
        target = studio.confine_workspace(rel)
        fs = render_local.fs_path
        os.makedirs(fs(os.path.dirname(target)), exist_ok=True)
        sha = render_local.sha256_file(part_path)
        size = os.path.getsize(fs(part_path))
        version = {
            'versionId': version_id,
            'path': rel,
            'sha256': sha,
            'bytes': size,
            'width': info['width'],
            'height': info['height'],
            'format': 'mp4',
            'kind': 'video',
            'codec': info['codec'],
            'durationSeconds': info['durationSeconds'],
            'origin': session['origin'],
            'license': session['license'],
            'simulated': False,
            'createdAt': _now(),
            'requestId': None,
            'candidateId': None,
            'provenance': {'provider': 'import-video', 'model': None, 'prompt': None,
                           'params': {'fileName': session['fileName']}, 'anchor': None,
                           'resultSha256': sha},
            'missing': False,
        }
        asset['versions'].append(version)
        if not asset.get('selectedVersionId'):
            asset['selectedVersionId'] = version_id
        # Promocao conjunta: move o arquivo verificado e grava a biblioteca; se a
        # gravacao do registro falhar, o arquivo promovido e removido e o estado
        # anterior da biblioteca permanece intacto.
        os.replace(fs(part_path), fs(target))
        try:
            save_library(studio, wpaths, library)
        except OSError:
            if os.path.exists(fs(target)):
                os.remove(fs(target))
            raise
        _VIDEO_IMPORT_SESSIONS.pop(upload_id, None)
        _shutil.rmtree(render_local.fs_path(os.path.dirname(part_path), force=True), ignore_errors=True)
        overview = _overview_payload(studio, work_id, wpaths, library, True, video_req, carousel_req)
        return {'assetId': asset_id, 'versionId': version_id, 'version': version, 'overview': overview}


# ---------------------------------------------------------------------------
# Visao geral
# ---------------------------------------------------------------------------

def consumers_of_asset(video_req, carousel_req, asset_id):
    consumers = []
    for scene in (video_req or {}).get('scenes') or []:
        if isinstance(scene, dict) and scene.get('mediaId') == asset_id:
            consumers.append({'modality': 'video', 'targetKind': 'video_scene', 'targetId': scene.get('id')})
            consumers.append({'modality': 'motion', 'targetKind': 'video_scene', 'targetId': scene.get('id')})
    for card in (carousel_req or {}).get('cards') or []:
        if isinstance(card, dict) and card.get('mediaId') == asset_id:
            consumers.append({'modality': 'carousel', 'targetKind': 'carousel_card', 'targetId': card.get('id')})
    return consumers


def build_media_overview(studio, work_id):
    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, _, _ = studio_review._read_work_core(studio, work_id)
        library, on_disk = load_library(studio, work_id, work_doc, wpaths, video_req, carousel_req)
        return _overview_payload(studio, work_id, wpaths, library, on_disk, video_req, carousel_req)


def _request_framing(studio, library, req, video_req, carousel_req, wpaths=None):
    """Como a midia atual do alvo sera enquadrada no quadro do pedido.

    Regra do adaptador: scale com force_original_aspect_ratio=decrease + pad
    centralizado + setsar=1 (bandas de preenchimento, sem distorcao).
    """
    target = req['target']
    asset_id = None
    selection = next((s for s in library.get('selections') or []
                      if s['targetKind'] == target['kind'] and s['targetId'] == target['id']), None)
    if selection:
        asset_id = selection['assetId']
    else:
        if target['kind'] == 'video_scene':
            scene = next((s for s in (video_req or {}).get('scenes') or [] if s.get('id') == target['id']), None)
            asset_id = (scene or {}).get('mediaId')
        else:
            card = next((c for c in (carousel_req or {}).get('cards') or [] if c.get('id') == target['id']), None)
            asset_id = (card or {}).get('mediaId')
    if not asset_id and wpaths:
        # Alvo ainda nao aplicado aos editores: usa o roteiro do Planejamento.
        raw = studio_review._read_json_safe(studio.confine_workspace(wpaths['planningFile'])) or {}
        creative = raw.get('creative') or {}
        if target['kind'] == 'video_scene':
            scene = next((s for s in creative.get('videoScenes') or [] if s.get('id') == target['id']), None)
            asset_id = (scene or {}).get('mediaId')
        else:
            card = next((c for c in creative.get('carouselCards') or [] if c.get('id') == target['id']), None)
            asset_id = (card or {}).get('mediaId')
    asset = _find_asset(library, asset_id) if asset_id else None
    version = _find_version(asset, asset.get('selectedVersionId')) if asset else None
    geometry = req.get('geometry') or {}
    out = {
        'rule': 'fit-center-pad',
        'targetWidth': geometry.get('width'),
        'targetHeight': geometry.get('height'),
        'mediaWidth': None,
        'mediaHeight': None,
        'bands': None,
    }
    if not version or version.get('missing'):
        return out
    mw, mh = version.get('width'), version.get('height')
    out['mediaWidth'], out['mediaHeight'] = mw, mh
    tw, th = geometry.get('width'), geometry.get('height')
    if not mw or not mh or not tw or not th:
        return out
    fit = min(tw / mw, th / mh)
    dw, dh = mw * fit, mh * fit
    if dw < tw - 1:
        out['bands'] = 'verticais (pillarbox)'
    elif dh < th - 1:
        out['bands'] = 'horizontais (letterbox)'
    else:
        out['bands'] = 'nenhuma (proporcao identica)'
    return out


def _overview_payload(studio, work_id, wpaths, library, on_disk, video_req, carousel_req):
    requests_view = []
    for entry in library['requests']:
        req = entry['request']
        current_sha = effective_context_sha(library, entry)
        candidates = []
        for cand in entry.get('candidates') or []:
            candidates.append({
                **cand,
                'stale': cand.get('contextSha256') != current_sha,
            })
        anchor_doc = _anchor_doc_for_request(library, req)
        requests_view.append({
            **entry,
            'candidates': candidates,
            'currentContextSha256': current_sha,
            'contextOutdated': any(c['stale'] for c in candidates),
            'providerTextPreview': image_adapters.build_provider_text(req, anchor_doc),
            'framing': _request_framing(studio, library, req, video_req, carousel_req, wpaths),
        })
    assets_view = []
    for asset in library['assets']:
        selected = _find_version(asset, asset.get('selectedVersionId'))
        assets_view.append({
            **asset,
            'selectedVersion': selected,
            'consumers': consumers_of_asset(video_req, carousel_req, asset['id']),
        })
    unregistered = []
    media_dir_abs = studio.confine_workspace(wpaths['mediaDir'])
    known_paths = {v['path'] for a in library['assets'] for v in a['versions']}
    if os.path.isdir(render_local.fs_path(media_dir_abs)):
        for entry in studio.scan_media(wpaths['mediaDir']):
            if entry['type'] == 'image' and entry['path'] not in known_paths:
                unregistered.append(entry)
    providers = image_adapters.provider_status()
    work_doc = studio_review._read_json_safe(
        studio.confine_workspace(studio.work_paths(work_id)['workFile'])) or {}
    image_conn = studio_connections.resolve_for_project(studio, work_doc.get('project'), 'image')
    if image_conn:
        for prov in providers:
            if prov['providerId'] == 'google-gemini':
                prov['available'] = bool(image_conn['secret'])
                prov['configured'] = bool(image_conn['secret'])
                prov['model'] = image_conn['model']
                prov['connectionId'] = image_conn['connectionId']
                prov['connectionName'] = image_conn['connectionName']
                prov['message'] = (
                    f'Conexao "{image_conn["connectionName"]}" selecionada para este projeto; '
                    'geracao habilitada por acao confirmada.'
                    if image_conn['secret'] else
                    f'Conexao "{image_conn["connectionName"]}" selecionada, mas a credencial nao resolveu. '
                    'Confira o cofre/variavel na aba Conexoes.'
                )
    return {
        'workId': work_id,
        'mediaLibrary': {**library, 'assets': assets_view, 'requests': requests_view},
        'libraryFingerprint': library_fingerprint(library),
        'initializedOnDisk': on_disk,
        'unregisteredFiles': unregistered,
        'providers': providers,
        'imageConnection': {k: v for k, v in image_conn.items() if k != 'secret'} if image_conn else None,
        'originLabels': ORIGIN_LABELS,
        'categories': list(CATEGORIES),
    }


# ---------------------------------------------------------------------------
# Importacao manual e associacao de arquivos existentes
# ---------------------------------------------------------------------------

def import_media(studio, work_id, body):
    if not isinstance(body, dict):
        raise ValueError('payload de importacao invalido')
    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, _, _ = studio_review._read_work_core(studio, work_id)
        library, _ = load_library(studio, work_id, work_doc, wpaths, video_req, carousel_req)
        _check_expected(library, body)

        data, file_name = _read_import_bytes(studio, body)
        info = image_adapters.inspect_image_bytes(data)
        origin = _clean_text(body.get('origin') or 'imported-manual', 'origin')
        license_value = _clean_text(body.get('license') or 'pending', 'license')
        origin_detail = body.get('originDetail') if isinstance(body.get('originDetail'), dict) else None
        if origin_detail:
            origin_detail = {
                'tool': _clean_text(origin_detail.get('tool'), 'originDetail.tool', allow_empty=True),
                'note': _clean_text(origin_detail.get('note'), 'originDetail.note', max_len=500, allow_empty=True),
            }

        asset_id = str(body.get('assetId') or '').strip()
        if asset_id:
            if not KEBAB_RE.match(asset_id):
                raise ValueError('assetId deve usar kebab-case')
            asset = _find_asset(library, asset_id)
            if not asset:
                raise ValueError(f'midia "{asset_id}" nao encontrada na biblioteca deste trabalho')
        else:
            base_id = _slug(os.path.splitext(file_name)[0])
            asset_id = _unique_asset_id(library, base_id)
            asset = {
                'id': asset_id,
                'name': file_name,
                'category': _category_for(origin, body.get('category')),
                'createdAt': _now(),
                'versions': [],
                'selectedVersionId': None,
            }
            library['assets'].append(asset)

        request_id = str(body.get('requestId') or '').strip() or None
        req_entry = _find_request(library, request_id) if request_id else None
        if request_id and not req_entry:
            raise ValueError(f'pedido visual "{request_id}" nao encontrado neste trabalho')
        candidate_id = f'cand-{uuid.uuid4().hex[:10]}' if req_entry else None
        provenance = {
            'provider': 'manual',
            'model': None,
            'prompt': req_entry['request']['prompt'] if req_entry else None,
            'params': {'fileName': file_name, 'originDetail': origin_detail},
            'anchor': req_entry['request'].get('anchor') if req_entry else None,
            'resultSha256': None,
        }
        version = _create_version(
            studio, wpaths, asset_id, data, origin, license_value,
            request_id=request_id, candidate_id=candidate_id,
            provenance=provenance, simulated=False,
        )
        provenance['resultSha256'] = version['sha256']
        asset['versions'].append(version)
        if not asset.get('selectedVersionId'):
            asset['selectedVersionId'] = version['versionId']

        if req_entry:
            req_entry.setdefault('candidates', []).append({
                'candidateId': candidate_id,
                'assetId': asset_id,
                'versionId': version['versionId'],
                'provider': str(body.get('provider') or 'manual'),
                'model': None,
                'createdAt': _now(),
                'contextSha256': effective_context_sha(library, req_entry),
                'provenance': provenance,
            })
            req_entry['status'] = 'completed'
            req_entry['updatedAt'] = _now()

        save_library(studio, wpaths, library)
        overview = _overview_payload(studio, work_id, wpaths, library, True, video_req, carousel_req)
        return {'assetId': asset_id, 'versionId': version['versionId'], 'candidateId': candidate_id, 'overview': overview}


def register_existing_media(studio, work_id, body):
    """Cadastra um arquivo que ja existe na pasta de midia do trabalho (sem copia)."""
    if not isinstance(body, dict):
        raise ValueError('payload de cadastro invalido')
    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, _, _ = studio_review._read_work_core(studio, work_id)
        library, _ = load_library(studio, work_id, work_doc, wpaths, video_req, carousel_req)
        _check_expected(library, body)
        rel = str(body.get('path') or '').strip()
        abs_path = studio.confine_workspace(rel)
        media_dir = studio.confine_workspace(wpaths['mediaDir'])
        if not (abs_path == media_dir or abs_path.startswith(media_dir + os.sep)):
            raise ValueError('o arquivo precisa estar dentro da pasta de midia do trabalho')
        if not os.path.isfile(render_local.fs_path(abs_path)):
            raise ValueError('arquivo ausente na pasta de midia do trabalho')
        rel_norm = studio.rel(abs_path)
        for asset in library['assets']:
            if any(v['path'] == rel_norm for v in asset['versions']):
                raise ValueError('este arquivo ja esta cadastrado na biblioteca')
        with open(render_local.fs_path(abs_path), 'rb') as handle:
            data = handle.read()
        info = image_adapters.inspect_image_bytes(data)
        origin = _clean_text(body.get('origin') or 'studio-work', 'origin')
        license_value = _clean_text(body.get('license') or 'pending', 'license')
        asset_id = _unique_asset_id(library, _slug(os.path.splitext(os.path.basename(abs_path))[0]))
        version = {
            'versionId': _new_version_id(),
            'path': rel_norm,
            'sha256': render_local.sha256_file(abs_path),
            'bytes': info['bytes'],
            'width': info['width'],
            'height': info['height'],
            'format': info['format'],
            'origin': origin,
            'license': license_value,
            'simulated': False,
            'createdAt': _now(),
            'requestId': None,
            'candidateId': None,
            'provenance': {'provider': 'register-existing', 'model': None, 'prompt': None,
                           'params': None, 'anchor': None, 'resultSha256': render_local.sha256_file(abs_path)},
            'missing': False,
        }
        library['assets'].append({
            'id': asset_id,
            'name': os.path.basename(abs_path),
            'category': _category_for(origin, body.get('category')),
            'createdAt': _now(),
            'versions': [version],
            'selectedVersionId': version['versionId'],
        })
        save_library(studio, wpaths, library)
        overview = _overview_payload(studio, work_id, wpaths, library, True, video_req, carousel_req)
        return {'assetId': asset_id, 'versionId': version['versionId'], 'overview': overview}


# ---------------------------------------------------------------------------
# Referencias visuais (VisualAnchor v1)
# ---------------------------------------------------------------------------

def save_anchor(studio, work_id, body):
    if not isinstance(body, dict):
        raise ValueError('payload de referencia visual invalido')
    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, _, _ = studio_review._read_work_core(studio, work_id)
        library, _ = load_library(studio, work_id, work_doc, wpaths, video_req, carousel_req)
        _check_expected(library, body)

        asset_id = str(body.get('assetId') or '').strip()
        version_id = str(body.get('versionId') or '').strip()
        asset = _find_asset(library, asset_id)
        if not asset:
            raise ValueError(f'midia "{asset_id}" nao encontrada na biblioteca deste trabalho')
        version = _find_version(asset, version_id) if version_id else _find_version(asset, asset.get('selectedVersionId'))
        if not version:
            raise ValueError('versao da midia de referencia nao encontrada')
        if version.get('missing'):
            raise ValueError('arquivo da versao de referencia ausente; reimporte antes de usar como ancora')
        abs_path = studio.confine(version['path'])
        actual_sha = render_local.sha256_file(abs_path)
        if actual_sha != version.get('sha256'):
            raise ValueError('checksum divergente na midia de referencia; a versao valida anterior foi preservada')

        anchor_id = str(body.get('anchorId') or '').strip()
        if anchor_id and not KEBAB_RE.match(anchor_id):
            raise ValueError('anchorId deve usar kebab-case')
        if not anchor_id:
            anchor_id = _unique_asset_id({'assets': [{'id': a['anchor']['id']} for a in library['anchors']]},
                                         _slug(body.get('title') or 'referencia-visual'))
        existing = _find_anchor(library, anchor_id)
        anchor_doc = {
            'schemaVersion': 1,
            'id': anchor_id,
            'title': _clean_text(body.get('title'), 'title', max_len=120),
            'reference': {'mediaId': asset_id, 'versionId': version['versionId'], 'sha256': version['sha256']},
            'direction': _clean_text(body.get('direction'), 'direction', max_len=2000),
            'mustInclude': [_clean_text(t, 'mustInclude', max_len=200) for t in (body.get('mustInclude') or [])],
            'mustAvoid': [_clean_text(t, 'mustAvoid', max_len=200) for t in (body.get('mustAvoid') or [])],
            'origin': _clean_text(body.get('origin') or version['origin'], 'origin'),
            'license': _clean_text(body.get('license') or version['license'], 'license'),
        }
        _validate_with_bridge(studio, '--visual-anchor', anchor_doc, 'Referencia visual')
        if existing:
            existing['anchor'] = anchor_doc
            existing['updatedAt'] = _now()
        else:
            library['anchors'].append({'anchor': anchor_doc, 'createdAt': _now(), 'updatedAt': _now()})
        save_library(studio, wpaths, library)
        overview = _overview_payload(studio, work_id, wpaths, library, True, video_req, carousel_req)
        return {'anchorId': anchor_id, 'overview': overview}


# ---------------------------------------------------------------------------
# Pedidos visuais (ImageRequest v1)
# ---------------------------------------------------------------------------

def _planning_context(studio, work_id, work_doc, wpaths, listing):
    import studio_planning
    editorial = studio_review._load_editorial_doc(studio, work_id, wpaths)
    work_media = studio_planning._build_work_media_catalog(studio, wpaths, {}, {}, use_library=False)
    planning_doc, allowed_profiles, _ = studio_planning._load_planning_doc(
        studio, work_id, work_doc, wpaths, editorial, listing, work_media
    )
    return planning_doc, allowed_profiles


def _profile_for_target(studio, body, target_kind, planning_doc, allowed_profiles):
    requested = str(body.get('profileId') or '').strip()
    if target_kind == 'video_scene':
        candidates = [p for p in allowed_profiles if p.get('localExportVideo')]
    else:
        candidates = [p for p in allowed_profiles if p.get('localExportCarousel')]
        chosen = planning_doc.get('carouselProfileId') or ''
        if not requested and chosen:
            requested = chosen
    if requested:
        match = next((p for p in candidates if p['id'] == requested), None)
        if not match:
            raise ValueError(f'perfil "{requested}" nao e compativel com o alvo ou nao e permitido pelo projeto')
        return match
    rec = planning_doc['briefingExtended'].get('recommendedProfiles') or []
    for pid in rec:
        match = next((p for p in candidates if p['id'] == pid), None)
        if match:
            return match
    if not candidates:
        raise ValueError('projeto nao possui perfil local compativel com este alvo')
    return candidates[0]


def _target_descriptor(planning_doc, target_kind, target_id):
    if target_kind == 'video_scene':
        scene = next((s for s in planning_doc['creative']['videoScenes'] if s['id'] == target_id), None)
        if not scene:
            raise ValueError(f'cena "{target_id}" nao encontrada no roteiro do Planejamento')
        return scene.get('requiredMediaDescriptor') or '', scene.get('objective') or '', scene.get('narrativeFunction') or ''
    card = next((c for c in planning_doc['creative']['carouselCards'] if c['id'] == target_id), None)
    if not card:
        raise ValueError(f'card "{target_id}" nao encontrado no Planejamento')
    return card.get('requiredMediaDescriptor') or '', card.get('title') or '', card.get('role') or ''


def create_image_request(studio, work_id, body):
    if not isinstance(body, dict):
        raise ValueError('payload de pedido visual invalido')
    target_kind = str(body.get('targetKind') or '').strip()
    target_id = str(body.get('targetId') or '').strip()
    if target_kind not in ('video_scene', 'carousel_card') or not KEBAB_RE.match(target_id or ''):
        raise ValueError('alvo invalido: informe targetKind (video_scene|carousel_card) e targetId em kebab-case')
    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, _, listing = studio_review._read_work_core(studio, work_id)
        library, _ = load_library(studio, work_id, work_doc, wpaths, video_req, carousel_req)
        _check_expected(library, body)
        planning_doc, allowed_profiles = _planning_context(studio, work_id, work_doc, wpaths, listing)
        descriptor, objective, role = _target_descriptor(planning_doc, target_kind, target_id)
        profile = _profile_for_target(studio, body, target_kind, planning_doc, allowed_profiles)
        aspect = profile.get('aspectRatio')
        if aspect not in ASPECT_GEOMETRY:
            raise ValueError(f'proporcao do perfil "{profile["id"]}" ({aspect}) nao suportada para pedido de imagem')
        width, height = ASPECT_GEOMETRY[aspect]
        prompt = _clean_text(body.get('prompt') or descriptor or objective, 'prompt', max_len=4000)
        purpose = _clean_text(body.get('purpose') or objective or f'Imagem para {target_id}', 'purpose', max_len=300)
        framing = _clean_text(body.get('framing') or 'Plano medio, elemento centralizado', 'framing', max_len=300)
        anchor_link = _anchor_link_for(library, str(body.get('anchorId') or '').strip(), body.get('sendAnchorToProvider'))
        context_sha = request_context_sha({
            'target': {'kind': target_kind, 'id': target_id},
            'descriptor': descriptor,
            'prompt': prompt,
            'purpose': purpose,
            'framing': framing,
            'aspectRatio': aspect,
            'geometry': {'width': width, 'height': height},
        }, anchor_link)
        request_doc = {
            'schemaVersion': 1,
            'id': f'img-{uuid.uuid4().hex[:10]}',
            'target': {'kind': target_kind, 'id': target_id},
            'profileId': profile['id'],
            'prompt': prompt,
            'purpose': purpose,
            'framing': framing,
            'aspectRatio': aspect,
            'geometry': {'width': width, 'height': height},
            'anchor': anchor_link,
            'context': {'descriptor': descriptor, 'contextSha256': context_sha},
        }
        _validate_with_bridge(studio, '--image-request', request_doc, 'Pedido de imagem')
        entry = {
            'request': request_doc,
            'status': 'ready',
            'createdAt': _now(),
            'updatedAt': _now(),
            'candidates': [],
            'selectedCandidateId': None,
            'attempts': [],
        }
        library['requests'].append(entry)
        save_library(studio, wpaths, library)
        overview = _overview_payload(studio, work_id, wpaths, library, True, video_req, carousel_req)
        return {'requestId': request_doc['id'], 'overview': overview}


def update_image_request(studio, work_id, body):
    if not isinstance(body, dict):
        raise ValueError('payload de atualizacao invalido')
    request_id = str(body.get('requestId') or '').strip()
    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, _, listing = studio_review._read_work_core(studio, work_id)
        library, _ = load_library(studio, work_id, work_doc, wpaths, video_req, carousel_req)
        _check_expected(library, body)
        entry = _find_request(library, request_id)
        if not entry:
            raise ValueError(f'pedido visual "{request_id}" nao encontrado neste trabalho')
        req = entry['request']
        if 'prompt' in body:
            req['prompt'] = _clean_text(body.get('prompt'), 'prompt', max_len=4000)
        if 'purpose' in body:
            req['purpose'] = _clean_text(body.get('purpose'), 'purpose', max_len=300)
        if 'framing' in body:
            req['framing'] = _clean_text(body.get('framing'), 'framing', max_len=300)
        if 'profileId' in body and str(body.get('profileId') or '').strip() != req['profileId']:
            planning_doc, allowed_profiles = _planning_context(studio, work_id, work_doc, wpaths, listing)
            profile = _profile_for_target(studio, body, req['target']['kind'], planning_doc, allowed_profiles)
            aspect = profile.get('aspectRatio')
            if aspect not in ASPECT_GEOMETRY:
                raise ValueError(f'proporcao do perfil "{profile["id"]}" ({aspect}) nao suportada para pedido de imagem')
            width, height = ASPECT_GEOMETRY[aspect]
            req['profileId'] = profile['id']
            req['aspectRatio'] = aspect
            req['geometry'] = {'width': width, 'height': height}
        if 'anchorId' in body or 'sendAnchorToProvider' in body:
            anchor_id = str(body.get('anchorId') if 'anchorId' in body else (req.get('anchor') or {}).get('anchorId') or '').strip()
            send = body.get('sendAnchorToProvider')
            if send is None:
                send = (req.get('anchor') or {}).get('sendToProvider', False)
            req['anchor'] = _anchor_link_for(library, anchor_id, send)
        context_sha = request_context_sha({
            'target': req['target'],
            'descriptor': req['context']['descriptor'],
            'prompt': req['prompt'],
            'purpose': req['purpose'],
            'framing': req['framing'],
            'aspectRatio': req['aspectRatio'],
            'geometry': req['geometry'],
        }, req.get('anchor'))
        req['context']['contextSha256'] = context_sha
        _validate_with_bridge(studio, '--image-request', req, 'Pedido de imagem')
        entry['status'] = 'ready' if not entry.get('candidates') else entry['status']
        entry['updatedAt'] = _now()
        save_library(studio, wpaths, library)
        overview = _overview_payload(studio, work_id, wpaths, library, True, video_req, carousel_req)
        return {'requestId': request_id, 'overview': overview}


# ---------------------------------------------------------------------------
# Geracao de candidatos (uma chamada por acao confirmada)
# ---------------------------------------------------------------------------

def generate_candidate(studio, work_id, body):
    if not isinstance(body, dict):
        raise ValueError('payload de geracao invalido')
    request_id = str(body.get('requestId') or '').strip()
    provider = str(body.get('provider') or '').strip()
    if body.get('confirm') is not True:
        raise ValueError('geracao exige confirmacao explicita do operador (confirm: true) apos revisar o material enviado')
    if provider == 'manual':
        raise ValueError('o caminho manual usa Importar arquivo: copie o pedido visual, gere na ferramenta autorizada e importe o resultado')
    if provider not in ('simulator', 'google-gemini'):
        raise ValueError(f'provedor de imagem desconhecido: "{provider}" (use simulator, google-gemini ou importacao manual)')
    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, _, _ = studio_review._read_work_core(studio, work_id)
        library, _ = load_library(studio, work_id, work_doc, wpaths, video_req, carousel_req)
        _check_expected(library, body)
        entry = _find_request(library, request_id)
        if not entry:
            raise ValueError(f'pedido visual "{request_id}" nao encontrado neste trabalho')
        req = entry['request']
        anchor_doc = _anchor_doc_for_request(library, req)
        provider_text = image_adapters.build_provider_text(req, anchor_doc)
        anchor_bytes, anchor_mime = None, None
        link = req.get('anchor')
        if link and link.get('sendToProvider'):
            record = _find_anchor(library, link['anchorId'])
            if not record:
                raise ValueError('referencia visual do pedido nao encontrada; atualize o pedido antes de gerar')
            ref = record['anchor']['reference']
            asset = _find_asset(library, ref['mediaId'])
            version = _find_version(asset, ref['versionId']) if asset else None
            if not version or version.get('missing'):
                raise ValueError('arquivo da referencia visual ausente; reimporte antes de gerar')
            abs_path = studio.confine(version['path'])
            if render_local.sha256_file(abs_path) != ref['sha256']:
                raise ValueError('checksum divergente na referencia visual; geracao cancelada para preservar a proveniencia')
            with open(render_local.fs_path(abs_path), 'rb') as handle:
                anchor_bytes = handle.read()
            anchor_mime = image_adapters.mime_for_format(version.get('format') or 'png')

        attempt = {'at': _now(), 'provider': provider, 'status': 'running', 'code': None, 'error': None}
        entry.setdefault('attempts', []).append(attempt)
        entry['status'] = 'generating'
        save_library(studio, wpaths, library)

        try:
            if provider == 'simulator':
                result = image_adapters.SimulatorImageAdapter().generate(
                    provider_text, req['geometry'],
                    anchor_sha256=link['sha256'] if link and link.get('sendToProvider') else None,
                )
                studio_connections.record_call(
                    studio, work_doc.get('project'), None, 'image', 'simulator-v1', 'completed', None,
                    usage={'imageCount': 1},
                )
            else:
                resolved = studio_connections.resolve_for_project(studio, work_doc.get('project'), 'image')
                if resolved:
                    adapter = image_adapters.GeminiImageAdapter(config={
                        'apiKey': resolved['secret'],
                        'model': resolved['model'],
                        'endpoint': resolved['endpoint'],
                        'timeoutSec': resolved['timeoutSec'],
                    })
                else:
                    adapter = image_adapters.GeminiImageAdapter()
                try:
                    result = adapter.generate(
                        provider_text, req['geometry'], req['aspectRatio'],
                        anchor_bytes=anchor_bytes, anchor_mime=anchor_mime,
                    )
                except image_adapters.ImageAdapterError as exc:
                    studio_connections.record_call(
                        studio, work_doc.get('project'),
                        resolved['connectionId'] if resolved else None, 'image',
                        adapter.model, 'failed', exc.code,
                    )
                    if resolved:
                        raise exc.__class__(
                            exc.code,
                            f'Conexao "{resolved["connectionName"]}" ({resolved["connectionId"]}): {exc} '
                            'Confira a conexao na aba Conexoes (teste, credencial e modelo) ou troque a selecao do projeto.',
                            detail=exc.detail,
                        )
                    raise
                studio_connections.record_call(
                    studio, work_doc.get('project'),
                    resolved['connectionId'] if resolved else None, 'image',
                    result.get('model'), 'completed', None,
                    usage=studio_connections._normalize_usage(result.get('usage')),
                    provider_info=studio_connections._normalize_provider_info(result.get('providerInfo')),
                )
        except image_adapters.ImageAdapterError as exc:
            attempt.update({'status': 'failed', 'code': exc.code, 'error': str(exc)})
            entry['status'] = 'failed'
            entry['updatedAt'] = _now()
            save_library(studio, wpaths, library)
            raise
        except (ValueError, OSError) as exc:
            attempt.update({'status': 'failed', 'code': 'IMAGE_GENERATION_FAILED', 'error': str(exc)})
            entry['status'] = 'failed'
            entry['updatedAt'] = _now()
            save_library(studio, wpaths, library)
            raise

        target = req['target']
        existing_asset_id = next((c['assetId'] for c in entry.get('candidates') or []), None)
        if existing_asset_id and _find_asset(library, existing_asset_id):
            asset_id = existing_asset_id
            asset = _find_asset(library, asset_id)
        else:
            asset_id = _unique_asset_id(library, _slug(f"{target['id']}-imagem"))
            asset = {
                'id': asset_id,
                'name': f"{target['id']} (gerada)",
                'category': 'illustration',
                'createdAt': _now(),
                'versions': [],
                'selectedVersionId': None,
            }
            library['assets'].append(asset)
        origin = f'generated-{provider}'
        candidate_id = f'cand-{uuid.uuid4().hex[:10]}'
        provenance = {
            'provider': provider,
            'model': result['model'],
            'prompt': provider_text,
            'params': {'aspectRatio': req['aspectRatio'], 'geometry': req['geometry']},
            'anchor': link if link and link.get('sendToProvider') else None,
            'resultSha256': None,
        }
        version = _create_version(
            studio, wpaths, asset_id, result['bytes'], origin,
            'owned-synthetic' if provider == 'simulator' else 'pending',
            request_id=request_id, candidate_id=candidate_id,
            provenance=provenance, simulated=result['simulated'],
        )
        provenance['resultSha256'] = version['sha256']
        asset['versions'].append(version)
        if not asset.get('selectedVersionId'):
            asset['selectedVersionId'] = version['versionId']
        entry.setdefault('candidates', []).append({
            'candidateId': candidate_id,
            'assetId': asset_id,
            'versionId': version['versionId'],
            'provider': provider,
            'model': result['model'],
            'createdAt': _now(),
            'contextSha256': effective_context_sha(library, entry),
            'provenance': provenance,
        })
        attempt.update({'status': 'completed', 'code': None, 'error': None})
        entry['status'] = 'completed'
        entry['updatedAt'] = _now()
        save_library(studio, wpaths, library)
        overview = _overview_payload(studio, work_id, wpaths, library, True, video_req, carousel_req)
        return {
            'requestId': request_id,
            'candidateId': candidate_id,
            'assetId': asset_id,
            'versionId': version['versionId'],
            'overview': overview,
        }


# ---------------------------------------------------------------------------
# Selecao de versao e vinculo com cena/card
# ---------------------------------------------------------------------------

def _set_draft_media_link(req, asset_id, version):
    media_type = version.get('kind') or 'image'
    media = req.setdefault('media', [])
    entry = next((m for m in media if m.get('id') == asset_id), None)
    if entry:
        entry['path'] = version['path']
        entry['type'] = media_type
        entry['origin'] = version['origin']
        entry['license'] = version['license']
    else:
        media.append({
            'id': asset_id,
            'path': version['path'],
            'type': media_type,
            'origin': version['origin'],
            'license': version['license'],
        })


def select_media(studio, work_id, body):
    if not isinstance(body, dict):
        raise ValueError('payload de selecao invalido')
    asset_id = str(body.get('assetId') or '').strip()
    version_id = str(body.get('versionId') or '').strip()
    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, _, _ = studio_review._read_work_core(studio, work_id)
        library, _ = load_library(studio, work_id, work_doc, wpaths, video_req, carousel_req)
        _check_expected(library, body)
        asset = _find_asset(library, asset_id)
        if not asset:
            raise ValueError(f'midia "{asset_id}" nao encontrada na biblioteca deste trabalho')
        version = _find_version(asset, version_id)
        if not version:
            raise ValueError(f'versao "{version_id}" nao encontrada para a midia "{asset_id}"')
        if version.get('missing'):
            raise ValueError('arquivo da versao ausente; a selecao anterior foi preservada')
        abs_path = studio.confine(version['path'])
        if not os.path.isfile(render_local.fs_path(abs_path)):
            raise ValueError('arquivo da versao ausente; a selecao anterior foi preservada')
        if render_local.sha256_file(abs_path) != version.get('sha256'):
            raise ValueError('checksum divergente na versao selecionada; a selecao anterior e os vinculos foram preservados')

        request_id = str(body.get('requestId') or '').strip() or None
        candidate_id = str(body.get('candidateId') or '').strip() or None
        req_entry = _find_request(library, request_id) if request_id else None
        if request_id and not req_entry:
            raise ValueError(f'pedido visual "{request_id}" nao encontrado neste trabalho')

        targets = []
        if body.get('targetKind') and body.get('targetId'):
            targets.append({'targetKind': body['targetKind'], 'targetId': body['targetId']})
        elif req_entry:
            targets.append({'targetKind': req_entry['request']['target']['kind'], 'targetId': req_entry['request']['target']['id']})
        if body.get('updateLinkedTargets'):
            for consumer in consumers_of_asset(video_req, carousel_req, asset_id):
                pair = {'targetKind': consumer['targetKind'], 'targetId': consumer['targetId']}
                if pair not in targets:
                    targets.append(pair)
        if not targets:
            raise ValueError('informe o alvo (targetKind/targetId) ou um pedido visual para vincular a versao')

        import studio_planning
        editorial = studio_review._load_editorial_doc(studio, work_id, wpaths)
        work_media = studio_planning._build_work_media_catalog(studio, wpaths, video_req, carousel_req, use_library=False)
        planning_doc, _, _ = studio_planning._load_planning_doc(
            studio, work_id, work_doc, wpaths, editorial,
            studio.list_profiles(work_doc['project']), work_media,
        )
        planning_changed = False
        draft_video_changed = False
        draft_carousel_changed = False
        applied_targets = []
        for pair in targets:
            kind, tid = pair['targetKind'], pair['targetId']
            if kind not in ('video_scene', 'carousel_card'):
                raise ValueError(f'tipo de alvo invalido: {kind}')
            library['selections'] = [s for s in library['selections']
                                     if not (s['targetKind'] == kind and s['targetId'] == tid)]
            library['selections'].append({
                'targetKind': kind, 'targetId': tid,
                'assetId': asset_id, 'versionId': version_id,
                'requestId': request_id, 'candidateId': candidate_id,
                'selectedAt': _now(),
            })
            in_planning = False
            if kind == 'video_scene':
                scene = next((s for s in planning_doc['creative']['videoScenes'] if s['id'] == tid), None)
                if scene:
                    scene['mediaId'] = asset_id
                    planning_changed = True
                    in_planning = True
                draft_scene = next((s for s in video_req.get('scenes') or [] if s.get('id') == tid), None)
                if draft_scene is not None and (not in_planning or body.get('updateLinkedTargets')):
                    draft_scene['mediaId'] = asset_id
                    _set_draft_media_link(video_req, asset_id, version)
                    draft_video_changed = True
            else:
                card = next((c for c in planning_doc['creative']['carouselCards'] if c['id'] == tid), None)
                if card:
                    card['mediaId'] = asset_id
                    planning_changed = True
                    in_planning = True
                draft_card = next((c for c in carousel_req.get('cards') or [] if c.get('id') == tid), None)
                if draft_card is not None and (not in_planning or body.get('updateLinkedTargets')):
                    draft_card['mediaId'] = asset_id
                    _set_draft_media_link(carousel_req, asset_id, version)
                    draft_carousel_changed = True
            applied_targets.append({**pair, 'viaPlanning': in_planning and not body.get('updateLinkedTargets')})

        asset['selectedVersionId'] = version_id
        if req_entry and candidate_id:
            if not any(c['candidateId'] == candidate_id for c in req_entry.get('candidates') or []):
                raise ValueError(f'candidato "{candidate_id}" nao pertence ao pedido "{request_id}"')
            req_entry['selectedCandidateId'] = candidate_id
            req_entry['updatedAt'] = _now()

        if draft_video_changed:
            studio_review.atomic_write_json(studio.confine_workspace(wpaths['videoDraft']), video_req)
        if draft_carousel_changed:
            studio_review.atomic_write_json(studio.confine_workspace(wpaths['carouselDraft']), carousel_req)
        if planning_changed:
            studio_planning._save_planning_doc(studio, wpaths, planning_doc)
        save_library(studio, wpaths, library)
        overview = _overview_payload(studio, work_id, wpaths, library, True, video_req, carousel_req)
        return {
            'assetId': asset_id,
            'versionId': version_id,
            'targets': applied_targets,
            'consumers': consumers_of_asset(video_req, carousel_req, asset_id),
            'overview': overview,
        }


# ---------------------------------------------------------------------------
# Catalogo de midia do Planejamento e miniaturas verificadas
# ---------------------------------------------------------------------------

def apply_library_to_catalog(studio, wpaths, catalog):
    """Sobrepoe o catalogo com as versoes selecionadas na biblioteca do trabalho."""
    library_rel = library_file_rel(wpaths)
    raw = studio_review._read_json_safe(studio.confine_workspace(library_rel))
    if not isinstance(raw, dict) or raw.get('schemaVersion') != LIBRARY_SCHEMA_VERSION:
        return catalog
    by_id = {entry['id']: entry for entry in catalog if entry.get('id')}
    for asset in raw.get('assets') or []:
        selected = next((v for v in asset.get('versions') or []
                         if v['versionId'] == asset.get('selectedVersionId')), None)
        if not selected or selected.get('missing'):
            continue
        entry = by_id.get(asset['id'])
        if entry:
            entry['path'] = selected['path']
            entry['origin'] = selected['origin']
            entry['license'] = selected['license']
            entry['bytes'] = selected.get('bytes') or entry.get('bytes')
            entry['versionId'] = selected['versionId']
            entry['simulated'] = bool(selected.get('simulated'))
        else:
            catalog.append({
                'id': asset['id'],
                'name': asset.get('name') or asset['id'],
                'path': selected['path'],
                'type': selected.get('kind') or 'image',
                'bytes': selected.get('bytes') or 0,
                'origin': selected['origin'],
                'license': selected['license'],
                'versionId': selected['versionId'],
                'simulated': bool(selected.get('simulated')),
            })
            by_id[asset['id']] = catalog[-1]
    return catalog


def library_media_path(studio, work_id, asset_id, version_id):
    """Miniatura por referencia valida da biblioteca (com conferencia de hash)."""
    work_doc, wpaths, video_req, carousel_req, _, _ = studio_review._read_work_core(studio, work_id)
    library, _ = load_library(studio, work_id, work_doc, wpaths, video_req, carousel_req)
    asset = _find_asset(library, asset_id)
    if not asset:
        raise ValueError('midia nao encontrada na biblioteca deste trabalho')
    version = _find_version(asset, version_id)
    if not version:
        raise ValueError('versao nao encontrada na biblioteca deste trabalho')
    if version.get('missing'):
        raise ValueError('arquivo da versao ausente')
    abs_path = studio.confine(version['path'])
    if not os.path.isfile(render_local.fs_path(abs_path)):
        raise ValueError('arquivo da versao ausente')
    if render_local.sha256_file(abs_path) != version.get('sha256'):
        raise ValueError('checksum divergente; miniatura bloqueada para esta versao')
    if version.get('kind') == 'video':
        return abs_path, 'video/mp4'
    mime = image_adapters.mime_for_format(version.get('format') or 'png')
    return abs_path, mime