"""Geracao de clipes por API (texto para video) no Video Studio.

Primeiro fornecedor: Google Gemini Omni Flash (gemini-omni-1.2-flash) pela
Interactions API oficial (POST /v1beta/interactions). O video volta nos passos
da interacao (steps[].model_output.content[] com type "video", base64 inline
ou URI de arquivo). A execucao e sincrona no fornecedor e roda em segundo
plano no Studio; background=true nao e documentado para o Omni Flash e nao e
usado. A retencao padrao do provedor (store=true) e informada ao operador
antes da confirmacao.

Cada pedido tem ID local registrado ANTES da chamada, estados persistidos em
`.workspace/studio/works/<id>/video-requests.json` (gravacao atomica) e
historico na aba Conexoes. Clique duplicado/recarregamento recuperam o mesmo
pedido; envio com resultado incerto preserva a evidencia e exige acao
explicita para nova submissao. Apos reinicio, pedidos com ID remoto confirmado
retomam a consulta (GET /v1beta/interactions/{id}); sem ID remoto, o pedido
fica incerto. A importacao usa os mecanismos da Biblioteca (FFprobe,
normalizacao MP4 H.264, exportacao silenciosa, promocao conjunta) e e
idempotente por pedido.

O valor da credencial e resolvido no momento da chamada pelo backend de
Conexoes e nunca entra em estado, respostas, logs ou exportacoes.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from urllib.parse import urlparse

import build_video
import image_adapters
import render_local
import studio_connections
import studio_media
import studio_review

VIDEO_REQUESTS_SCHEMA_VERSION = 1
DEFAULT_VIDEO_MODEL = studio_connections.GEMINI_VIDEO_DEFAULT_MODEL
DURATION_MIN_S = 3
DURATION_MAX_S = 15
DURATION_DEFAULT_S = 10
ASPECT_RATIOS = ('16:9', '9:16')
RESOLUTIONS = ('360p', '720p', '1080p', '4k')
RESOLUTION_DEFAULT = '720p'
MAX_VIDEO_BYTES = studio_media.MAX_VIDEO_IMPORT_BYTES
STAGING_DIR_REL = '.workspace/tmp/studio-video-api'
POLL_INTERVAL_S = 2.0
POLL_BUDGET_S = 600.0
STATUSES = ('awaiting', 'processing', 'ready', 'imported', 'failed', 'uncertain')
STATUS_LABELS = {
    'awaiting': 'Aguardando confirmacao',
    'processing': 'Em processamento',
    'ready': 'Pronto para importar',
    'imported': 'Importado na Biblioteca',
    'failed': 'Falha confirmada',
    'uncertain': 'Resultado incerto',
}
RETENTION_NOTICE = (
    'A Interactions API do Google armazena a interacao por padrao (store=true): '
    '55 dias no plano pago e 1 dia no plano gratuito. O texto enviado e o video '
    'gerado ficam registrados no provedor nesse periodo; a exclusao antecipada e '
    'possivel pela API/AI Studio. Este Studio nao envia store=false porque a '
    'retomada apos reinicio depende do ID remoto armazenado.'
)
BILLING_NOTICE = (
    'Cobranca por video gerado conforme o preco do modelo na conta Google '
    '(Gemini Omni Flash). O Studio nao estima custo: uso, cota e saldo so '
    'aparecem no historico quando o fornecedor devolver esses dados.'
)
AUDIO_NOTICE = (
    'O modelo gera video com audio nativo. Pela politica do projeto, o Studio '
    'importa o clipe SEM faixa de audio (exportacao silenciosa verificada por '
    'FFprobe); legendas SRT e narracao TXT continuam separadas.'
)

_ACTIVE_LOCK = threading.Lock()
_ACTIVE = {}


class VideoApiError(ValueError):
    """Erro estruturado da geracao por API com codigo estavel."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def _now():
    return studio_review.now_iso()


def _requests_path(studio, wpaths):
    return studio.confine_workspace(wpaths.get('videoRequestsFile')
                                    or f"{wpaths['workDir']}/video-requests.json")


def _load_doc(studio, wpaths):
    path = _requests_path(studio, wpaths)
    if os.path.isfile(render_local.fs_path(path)):
        try:
            with open(render_local.fs_path(path), 'r', encoding='utf-8') as handle:
                doc = json.load(handle)
            if isinstance(doc, dict) and doc.get('schemaVersion') == VIDEO_REQUESTS_SCHEMA_VERSION:
                doc.setdefault('requests', [])
                return doc
        except (OSError, ValueError):
            pass
    return {'schemaVersion': VIDEO_REQUESTS_SCHEMA_VERSION, 'requests': []}


def _save_doc(studio, wpaths, doc):
    studio_review.atomic_write_json(_requests_path(studio, wpaths), doc)


def _find_request(doc, request_id):
    entry = next((r for r in doc['requests'] if r.get('id') == request_id), None)
    if entry is None:
        raise VideoApiError('REQUEST_NOT_FOUND', f'pedido de clipe nao encontrado: {request_id}')
    return entry


def _public_request(entry):
    return json.loads(json.dumps(entry, ensure_ascii=False))


def _video_connection_public(studio, project):
    resolved = studio_connections.resolve_for_project(studio, project, 'video')
    if not resolved:
        return None
    return {k: v for k, v in resolved.items() if k != 'secret'}


def options_payload():
    return {
        'model': DEFAULT_VIDEO_MODEL,
        'durations': list(range(DURATION_MIN_S, DURATION_MAX_S + 1)),
        'durationDefault': DURATION_DEFAULT_S,
        'aspectRatios': list(ASPECT_RATIOS),
        'aspectDefault': '16:9',
        'resolutions': list(RESOLUTIONS),
        'resolutionDefault': RESOLUTION_DEFAULT,
        'maxBytes': MAX_VIDEO_BYTES,
        'statusLabels': dict(STATUS_LABELS),
        'notices': {'retention': RETENTION_NOTICE, 'billing': BILLING_NOTICE, 'audio': AUDIO_NOTICE},
    }


def _validate_params(body):
    prompt = str(body.get('prompt') or '').strip()
    if not prompt:
        raise VideoApiError('BAD_PROMPT', 'descreva o clipe antes de gerar (texto para video)')
    if len(prompt) > 4000 or any(ord(ch) < 32 and ch not in '\n\t' for ch in prompt):
        raise VideoApiError('BAD_PROMPT', 'texto do clipe invalido (ate 4000 caracteres, sem caracteres de controle)')
    try:
        duration = int(body.get('durationSeconds') or DURATION_DEFAULT_S)
    except (TypeError, ValueError):
        raise VideoApiError('BAD_DURATION', 'duracao deve ser um numero inteiro de segundos')
    if not DURATION_MIN_S <= duration <= DURATION_MAX_S:
        raise VideoApiError('BAD_DURATION',
                            f'duracao fora das opcoes oficiais do modelo ({DURATION_MIN_S}s a {DURATION_MAX_S}s)')
    aspect = str(body.get('aspectRatio') or '16:9').strip()
    if aspect not in ASPECT_RATIOS:
        raise VideoApiError('BAD_ASPECT', f'proporcao nao suportada pelo modelo: {aspect} (use {", ".join(ASPECT_RATIOS)})')
    resolution = str(body.get('resolution') or RESOLUTION_DEFAULT).strip()
    if resolution not in RESOLUTIONS:
        raise VideoApiError('BAD_RESOLUTION', f'resolucao nao suportada: {resolution} (use {", ".join(RESOLUTIONS)})')
    return prompt, {'durationSeconds': duration, 'aspectRatio': aspect, 'resolution': resolution}


def _resolve_video_connection(studio, project):
    resolved = studio_connections.resolve_for_project(studio, project, 'video')
    if not resolved:
        raise VideoApiError(
            'VIDEO_CONNECTION_REQUIRED',
            'Nenhuma conexao de video selecionada para este projeto. Cadastre uma conexao Google Gemini '
            'e selecione a capacidade video na aba Conexoes (a mesma conexao pode atender imagem e video).',
        )
    if resolved['provider'] != 'google-gemini':
        raise VideoApiError('VIDEO_PROVIDER_UNSUPPORTED',
                            'nesta versao a geracao de clipes usa apenas o Google Gemini (Omni Flash)')
    if not resolved.get('secret'):
        raise VideoApiError(
            'CREDENTIAL_MISSING',
            f'Conexao "{resolved["connectionName"]}" ({resolved["connectionId"]}) sem credencial resolvida. '
            'Grave a chave no cofre ou selecione uma variavel de ambiente configurada na aba Conexoes.',
        )
    return resolved


def create_request(studio, work_id, body):
    """Registra o pedido com ID local ANTES de qualquer chamada ao fornecedor."""
    if not isinstance(body, dict):
        raise ValueError('payload de pedido de clipe invalido')
    prompt, params = _validate_params(body)
    with studio_review._STATE_LOCK:
        work_doc, wpaths, _, _, _, _ = studio_review._read_work_core(studio, work_id)
        project = work_doc.get('project')
        resolved = _resolve_video_connection(studio, project)
        model = str(body.get('model') or '').strip() or resolved['model']
        if not image_adapters.GEMINI_MODEL_RE.match(model):
            raise VideoApiError('BAD_MODEL', f'identificador de modelo Gemini invalido: {model}')
        doc = _load_doc(studio, wpaths)
        request_id = f'vreq-{uuid.uuid4().hex[:10]}'
        entry = {
            'id': request_id,
            'workId': work_id,
            'project': project,
            'provider': 'google-gemini',
            'connectionId': resolved['connectionId'],
            'connectionName': resolved['connectionName'],
            'model': model,
            'prompt': prompt,
            'params': params,
            'status': 'awaiting',
            'createdAt': _now(),
            'updatedAt': _now(),
            'remoteInteractionId': None,
            'remoteFileId': None,
            'attempts': [],
            'result': None,
            'imported': None,
        }
        doc['requests'].append(entry)
        _save_doc(studio, wpaths, doc)
        return {
            'request': _public_request(entry),
            'confirmation': {
                'connectionId': resolved['connectionId'],
                'connectionName': resolved['connectionName'],
                'model': model,
                'prompt': prompt,
                'params': params,
                'notices': {'retention': RETENTION_NOTICE, 'billing': BILLING_NOTICE, 'audio': AUDIO_NOTICE},
            },
            'options': options_payload(),
        }


def _attempt_start(entry):
    attempt = {
        'attemptId': f'att-{uuid.uuid4().hex[:10]}',
        'at': _now(),
        'finishedAt': None,
        'status': 'running',
        'code': None,
        'error': None,
        'remoteInteractionId': None,
    }
    entry.setdefault('attempts', []).append(attempt)
    entry['status'] = 'processing'
    entry['updatedAt'] = _now()
    return attempt


def _attempt_finish(entry, attempt, status, code=None, error=None):
    attempt.update({'status': status, 'code': code, 'error': error, 'finishedAt': _now()})
    entry['status'] = {'completed': 'ready', 'failed': 'failed', 'uncertain': 'uncertain'}[status]
    entry['updatedAt'] = _now()


def submit_request(studio, work_id, body):
    """Confirmacao explicita do operador; clique duplicado recupera o mesmo pedido."""
    if not isinstance(body, dict) or body.get('confirm') is not True:
        raise VideoApiError('CONFIRM_REQUIRED',
                            'o envio ao fornecedor exige confirmacao explicita (confirm: true) apos revisar conexao, modelo, texto e condicoes')
    request_id = str(body.get('requestId') or '').strip()
    with studio_review._STATE_LOCK:
        work_doc, wpaths, _, _, _, _ = studio_review._read_work_core(studio, work_id)
        doc = _load_doc(studio, wpaths)
        entry = _find_request(doc, request_id)
        if entry['status'] in ('processing', 'ready', 'imported'):
            return {'request': _public_request(entry), 'deduplicated': True}
        if entry['status'] in ('failed', 'uncertain') and body.get('resubmit') is not True:
            raise VideoApiError(
                'RESUBMIT_REQUIRED',
                'o pedido anterior falhou ou ficou incerto; uma nova submissao exige acao explicita do operador (resubmit: true)',
            )
        resolved = _resolve_video_connection(studio, work_doc.get('project'))
        entry['connectionId'] = resolved['connectionId']
        entry['connectionName'] = resolved['connectionName']
        attempt = _attempt_start(entry)
        _save_doc(studio, wpaths, doc)
        key = (studio, work_id, request_id)
        with _ACTIVE_LOCK:
            if key in _ACTIVE:
                return {'request': _public_request(entry), 'deduplicated': True}
            worker = threading.Thread(
                target=_run_generation,
                args=(studio, work_id, request_id, attempt['attemptId']),
                daemon=True,
            )
            _ACTIVE[key] = worker
        worker.start()
        return {'request': _public_request(entry), 'deduplicated': False}


def _headers(secret):
    return {'Accept': 'application/json', 'x-goog-api-key': secret}


def _post_json(url, payload, headers, timeout):
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST',
                                 headers={**headers, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _get_json(url, headers, timeout):
    req = urllib.request.Request(url, headers=headers, method='GET')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _get_bytes(url, headers, timeout):
    req = urllib.request.Request(url, headers=headers, method='GET')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _extract_video_content(payload):
    for step in reversed(payload.get('steps') or []):
        if not isinstance(step, dict) or step.get('type') != 'model_output':
            continue
        for content in step.get('content') or []:
            if isinstance(content, dict) and content.get('type') == 'video':
                return content
    return None


def _interaction_body(entry):
    params = entry['params']
    return {
        'model': entry['model'],
        'input': entry['prompt'],
        'response_format': {
            'type': 'video',
            'aspect_ratio': params['aspectRatio'],
            'resolution': params['resolution'],
            'duration': f"{params['durationSeconds']}s",
        },
    }


def _timeout_for(resolved):
    try:
        timeout = float(resolved.get('timeoutSec') or 300.0)
    except (TypeError, ValueError):
        timeout = 300.0
    return max(30.0, min(600.0, timeout))


def _staging_dir(studio, request_id):
    return studio.confine_workspace(os.path.join(STAGING_DIR_REL, request_id))


def _record(studio, entry, status, code=None, usage=None, provider_info=None):
    studio_connections.record_call(
        studio, entry.get('project'), entry.get('connectionId'), 'video',
        entry.get('model'), status, code, usage=usage, provider_info=provider_info,
    )


def _usage_from_payload(payload):
    raw = payload.get('usage') if isinstance(payload.get('usage'), dict) else payload.get('usageMetadata')
    usage = studio_connections._normalize_usage(raw)
    if isinstance(raw, dict):
        for src in ('videoCount', 'video_count'):
            if isinstance(raw.get(src), (int, float)):
                usage = usage or {}
                usage['videoCount'] = raw[src]
    return usage


def _provider_info_from_payload(payload):
    return studio_connections._normalize_provider_info(payload)


def _run_generation(studio, work_id, request_id, attempt_id):
    key = (studio, work_id, request_id)
    try:
        with studio_review._STATE_LOCK:
            work_doc, wpaths, _, _, _, _ = studio_review._read_work_core(studio, work_id)
            doc = _load_doc(studio, wpaths)
            entry = _find_request(doc, request_id)
            attempt = next(a for a in entry['attempts'] if a['attemptId'] == attempt_id)
            resolved = studio_connections.resolve_for_project(studio, work_doc.get('project'), 'video')
        if not resolved or not resolved.get('secret'):
            with studio_review._STATE_LOCK:
                doc = _load_doc(studio, wpaths)
                entry = _find_request(doc, request_id)
                attempt = next(a for a in entry['attempts'] if a['attemptId'] == attempt_id)
                _attempt_finish(entry, attempt, 'failed', 'CREDENTIAL_MISSING',
                                'credencial nao resolvida no momento da chamada; confira a conexao na aba Conexoes')
                _save_doc(studio, wpaths, doc)
            _record(studio, entry, 'failed', 'CREDENTIAL_MISSING')
            return
        secret = resolved['secret']
        endpoint = resolved['endpoint'].rstrip('/')
        timeout = _timeout_for(resolved)
        try:
            payload = _post_json(f'{endpoint}/v1beta/interactions', _interaction_body(entry),
                                 _headers(secret), timeout)
        except urllib.error.HTTPError as exc:
            code, message = studio_connections._classify_http(exc, secret)
            with studio_review._STATE_LOCK:
                doc = _load_doc(studio, wpaths)
                entry = _find_request(doc, request_id)
                attempt = next(a for a in entry['attempts'] if a['attemptId'] == attempt_id)
                _attempt_finish(entry, attempt, 'failed', code, message)
                _save_doc(studio, wpaths, doc)
            _record(studio, entry, 'failed', code)
            return
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as exc:
            reason = getattr(exc, 'reason', exc)
            message = studio_connections._redact(
                f'Envio pode ter sido aceito, mas a resposta nao chegou: {reason}. '
                'O estado ficou incerto; consulte o provedor ou reenvie explicitamente.', str(secret))
            with studio_review._STATE_LOCK:
                doc = _load_doc(studio, wpaths)
                entry = _find_request(doc, request_id)
                attempt = next(a for a in entry['attempts'] if a['attemptId'] == attempt_id)
                _attempt_finish(entry, attempt, 'uncertain', 'RESULT_UNCERTAIN', message)
                _save_doc(studio, wpaths, doc)
            _record(studio, entry, 'uncertain', 'RESULT_UNCERTAIN')
            return
        except ValueError as exc:
            with studio_review._STATE_LOCK:
                doc = _load_doc(studio, wpaths)
                entry = _find_request(doc, request_id)
                attempt = next(a for a in entry['attempts'] if a['attemptId'] == attempt_id)
                _attempt_finish(entry, attempt, 'uncertain', 'RESULT_UNCERTAIN',
                                studio_connections._redact(f'Resposta ilegivel apos envio: {exc}', secret))
                _save_doc(studio, wpaths, doc)
            _record(studio, entry, 'uncertain', 'RESULT_UNCERTAIN')
            return
        with studio_review._STATE_LOCK:
            doc = _load_doc(studio, wpaths)
            entry = _find_request(doc, request_id)
            attempt = next(a for a in entry['attempts'] if a['attemptId'] == attempt_id)
            remote_id = payload.get('id') if isinstance(payload, dict) else None
            if remote_id:
                entry['remoteInteractionId'] = str(remote_id)
                attempt['remoteInteractionId'] = str(remote_id)
            _save_doc(studio, wpaths, doc)
        _consume_interaction(studio, work_id, request_id, attempt_id, resolved, payload)
    finally:
        with _ACTIVE_LOCK:
            _ACTIVE.pop(key, None)


def _consume_interaction(studio, work_id, request_id, attempt_id, resolved, payload):
    """Processa a resposta (inline ou URI) e persiste o resultado verificado."""
    secret = resolved['secret']
    endpoint = resolved['endpoint'].rstrip('/')
    timeout = _timeout_for(resolved)
    deadline = time.monotonic() + POLL_BUDGET_S
    while True:
        if getattr(studio, 'video_api_stopped', False):
            return
        status = str(payload.get('status') or '').lower()
        if status in ('queued', 'in_progress', 'requires_action'):
            remote_id = payload.get('id')
            if not remote_id or time.monotonic() >= deadline:
                _finish_failed(studio, work_id, request_id, attempt_id, 'UNAVAILABLE',
                               'o fornecedor nao concluiu a interacao dentro do tempo de acompanhamento')
                return
            time.sleep(POLL_INTERVAL_S)
            try:
                payload = _get_json(f'{endpoint}/v1beta/interactions/{remote_id}', _headers(secret),
                                    min(timeout, 60.0))
            except urllib.error.HTTPError as exc:
                code, message = studio_connections._classify_http(exc, secret)
                _finish_failed(studio, work_id, request_id, attempt_id, code, message)
                return
            except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError, ValueError) as exc:
                _note_poll_error(studio, work_id, request_id, attempt_id,
                                 studio_connections._redact(str(getattr(exc, 'reason', exc)), secret))
                return
            continue
        if status in ('failed', 'cancelled'):
            detail = payload.get('error') if isinstance(payload.get('error'), dict) else {}
            message = studio_connections._redact(str(detail.get('message') or f'interacao terminou com estado {status}'), secret)
            code = 'RATE_LIMIT' if 'rate' in message.lower() or 'quota' in message.lower() else 'PROVIDER_FAILED'
            _finish_failed(studio, work_id, request_id, attempt_id, code, message)
            return
        if status != 'completed':
            _finish_failed(studio, work_id, request_id, attempt_id, 'INVALID_RESULT',
                           f'estado de interacao nao reconhecido: {status or "ausente"}')
            return
        break

    content = _extract_video_content(payload)
    if not content:
        _finish_failed(studio, work_id, request_id, attempt_id, 'INVALID_RESULT',
                       'resposta concluida sem conteudo de video nos passos da interacao (steps/model_output)')
        return
    try:
        if content.get('data'):
            video_bytes = base64.b64decode(content['data'], validate=True)
        elif content.get('uri'):
            video_bytes = _download_uri(endpoint, content['uri'], secret, timeout, deadline,
                                        studio, work_id, request_id, attempt_id)
            if video_bytes is None:
                return
        else:
            raise ValueError('conteudo de video sem data nem uri')
    except (ValueError, TypeError) as exc:
        _finish_failed(studio, work_id, request_id, attempt_id, 'INVALID_RESULT',
                       f'video devolvido pelo fornecedor e invalido: {exc}')
        return
    if not video_bytes or len(video_bytes) > MAX_VIDEO_BYTES:
        _finish_failed(studio, work_id, request_id, attempt_id, 'INVALID_RESULT',
                       f'tamanho do video fora dos limites do Studio (1 byte a {MAX_VIDEO_BYTES // (1024 * 1024)} MiB)')
        return
    with studio_review._STATE_LOCK:
        work_doc, wpaths, _, _, _, _ = studio_review._read_work_core(studio, work_id)
        doc = _load_doc(studio, wpaths)
        entry = _find_request(doc, request_id)
        attempt = next(a for a in entry['attempts'] if a['attemptId'] == attempt_id)
        staging = _staging_dir(studio, request_id)
        os.makedirs(render_local.fs_path(staging), exist_ok=True)
        staged_abs = os.path.join(staging, 'provider.mp4')
        with open(render_local.fs_path(staged_abs), 'wb') as handle:
            handle.write(video_bytes)
        entry['result'] = {
            'stagedPath': studio.rel(staged_abs),
            'sha256': render_local.sha256_file(staged_abs),
            'bytes': len(video_bytes),
            'mimeType': content.get('mime_type') or 'video/mp4',
            'receivedAt': _now(),
        }
        _attempt_finish(entry, attempt, 'completed')
        _save_doc(studio, wpaths, doc)
    _record(studio, entry, 'completed', None,
            usage=_usage_from_payload(payload), provider_info=_provider_info_from_payload(payload))


def _download_uri(endpoint, uri, secret, timeout, deadline, studio, work_id, request_id, attempt_id):
    """Entrega delivery=uri: consulta o arquivo ate ACTIVE e baixa os bytes."""
    parsed = urlparse(uri)
    match = re.search(r'/files/([A-Za-z0-9_\-]+)', parsed.path or uri)
    file_id = match.group(1) if match else None
    if not file_id:
        raise ValueError(f'URI de video sem identificador de arquivo: {uri}')
    with studio_review._STATE_LOCK:
        _, wpaths, _, _, _, _ = studio_review._read_work_core(studio, work_id)
        doc = _load_doc(studio, wpaths)
        entry = _find_request(doc, request_id)
        entry['remoteFileId'] = file_id
        _save_doc(studio, wpaths, doc)
    while True:
        if getattr(studio, 'video_api_stopped', False):
            return None
        if time.monotonic() >= deadline:
            _finish_failed(studio, work_id, request_id, attempt_id, 'UNAVAILABLE',
                           'arquivo do fornecedor nao ficou ACTIVE dentro do tempo de acompanhamento')
            return None
        try:
            info = _get_json(f'{endpoint}/v1beta/files/{file_id}', _headers(secret), min(timeout, 60.0))
        except urllib.error.HTTPError as exc:
            code, message = studio_connections._classify_http(exc, secret)
            _finish_failed(studio, work_id, request_id, attempt_id, code, message)
            return None
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError, ValueError) as exc:
            _note_poll_error(studio, work_id, request_id, attempt_id,
                             studio_connections._redact(str(getattr(exc, 'reason', exc)), secret))
            return None
        state = str(info.get('state') or '').upper()
        if state == 'ACTIVE':
            break
        if state == 'FAILED':
            _finish_failed(studio, work_id, request_id, attempt_id, 'PROVIDER_FAILED',
                           'o fornecedor marcou o arquivo de video como FAILED')
            return None
        time.sleep(POLL_INTERVAL_S)
    download_url = uri if uri.startswith('http') else f'{endpoint}/v1beta/files/{file_id}:download?alt=media'
    try:
        return _get_bytes(download_url, _headers(secret), timeout)
    except urllib.error.HTTPError as exc:
        code, message = studio_connections._classify_http(exc, secret)
        _finish_failed(studio, work_id, request_id, attempt_id, code, message)
        return None
    except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as exc:
        _note_poll_error(studio, work_id, request_id, attempt_id,
                         studio_connections._redact(str(getattr(exc, 'reason', exc)), secret))
        return None


def _finish_failed(studio, work_id, request_id, attempt_id, code, message):
    with studio_review._STATE_LOCK:
        _, wpaths, _, _, _, _ = studio_review._read_work_core(studio, work_id)
        doc = _load_doc(studio, wpaths)
        entry = _find_request(doc, request_id)
        attempt = next(a for a in entry['attempts'] if a['attemptId'] == attempt_id)
        _attempt_finish(entry, attempt, 'failed', code, message)
        _save_doc(studio, wpaths, doc)
    _record(studio, entry, 'failed', code)


def _note_poll_error(studio, work_id, request_id, attempt_id, message):
    """Falha de rede durante consulta com ID remoto confirmado: mantem processing."""
    with studio_review._STATE_LOCK:
        _, wpaths, _, _, _, _ = studio_review._read_work_core(studio, work_id)
        doc = _load_doc(studio, wpaths)
        entry = _find_request(doc, request_id)
        attempt = next(a for a in entry['attempts'] if a['attemptId'] == attempt_id)
        attempt['error'] = f'Consulta interrompida: {message}'
        entry['updatedAt'] = _now()
        _save_doc(studio, wpaths, doc)


def check_request(studio, work_id, body):
    """Acompanhar: consulta unica ao provedor quando ha ID remoto confirmado."""
    request_id = str((body or {}).get('requestId') or '').strip()
    with studio_review._STATE_LOCK:
        work_doc, wpaths, _, _, _, _ = studio_review._read_work_core(studio, work_id)
        doc = _load_doc(studio, wpaths)
        entry = _find_request(doc, request_id)
        snapshot = _public_request(entry)
        remote_id = entry.get('remoteInteractionId')
        attempt_id = entry['attempts'][-1]['attemptId'] if entry.get('attempts') else None
    if not remote_id or entry_status_terminal(snapshot['status']):
        return {'request': snapshot, 'checked': False}
    with _ACTIVE_LOCK:
        if (studio, work_id, request_id) in _ACTIVE:
            return {'request': snapshot, 'checked': False,
                    'message': 'geracao em andamento neste servidor; o acompanhamento automatico ja esta consultando o provedor'}
    resolved = studio_connections.resolve_for_project(studio, work_doc.get('project'), 'video')
    if not resolved or not resolved.get('secret'):
        return {'request': snapshot, 'checked': False,
                'message': 'credencial nao resolvida; confira a conexao na aba Conexoes'}
    try:
        payload = _get_json(f'{resolved["endpoint"].rstrip("/")}/v1beta/interactions/{remote_id}',
                            _headers(resolved['secret']), min(_timeout_for(resolved), 60.0))
    except urllib.error.HTTPError as exc:
        code, message = studio_connections._classify_http(exc, resolved['secret'])
        if attempt_id:
            _finish_failed(studio, work_id, request_id, attempt_id, code, message)
        return {'request': get_request(studio, work_id, request_id), 'checked': True}
    except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError, ValueError) as exc:
        if attempt_id:
            _note_poll_error(studio, work_id, request_id, attempt_id,
                             studio_connections._redact(str(getattr(exc, 'reason', exc)), resolved['secret']))
        return {'request': get_request(studio, work_id, request_id), 'checked': True}
    if attempt_id:
        _consume_interaction(studio, work_id, request_id, attempt_id, resolved, payload)
    return {'request': get_request(studio, work_id, request_id), 'checked': True}


def entry_status_terminal(status):
    return status in ('ready', 'imported', 'failed', 'awaiting')


def get_request(studio, work_id, request_id):
    with studio_review._STATE_LOCK:
        _, wpaths, _, _, _, _ = studio_review._read_work_core(studio, work_id)
        doc = _load_doc(studio, wpaths)
        return _public_request(_find_request(doc, request_id))


def get_requests(studio, work_id):
    with studio_review._STATE_LOCK:
        work_doc, wpaths, _, _, _, _ = studio_review._read_work_core(studio, work_id)
        doc = _load_doc(studio, wpaths)
        return {
            'workId': work_id,
            'requests': [_public_request(r) for r in reversed(doc['requests'])],
            'videoConnection': _video_connection_public(studio, work_doc.get('project')),
            'options': options_payload(),
        }


def recover_on_startup(studio):
    """Retoma consultas comprovadamente possiveis; sem ID remoto, marca incerto."""
    resumed, uncertain = 0, 0
    works_dir = studio.works_dir
    if not os.path.isdir(works_dir):
        return {'resumed': 0, 'uncertain': 0}
    for work_id in sorted(os.listdir(works_dir)):
        wpaths = studio.work_paths(work_id) if re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', work_id) else None
        if not wpaths:
            continue
        path = studio.confine_workspace(wpaths['videoRequestsFile'])
        if not os.path.isfile(render_local.fs_path(path)):
            continue
        with studio_review._STATE_LOCK:
            doc = _load_doc(studio, wpaths)
            changed = False
            for entry in doc['requests']:
                if entry.get('status') != 'processing':
                    continue
                attempt = entry['attempts'][-1] if entry.get('attempts') else None
                if entry.get('remoteInteractionId'):
                    key = (studio, work_id, entry['id'])
                    with _ACTIVE_LOCK:
                        if key in _ACTIVE:
                            continue
                        worker = threading.Thread(
                            target=_resume_poll,
                            args=(studio, work_id, entry['id'],
                                  attempt['attemptId'] if attempt else None),
                            daemon=True,
                        )
                        _ACTIVE[key] = worker
                    worker.start()
                    resumed += 1
                else:
                    if attempt:
                        attempt.update({'status': 'uncertain', 'code': 'INTERRUPTED',
                                        'error': 'Studio reiniciado antes de confirmar o ID remoto; '
                                                 'o envio pode ter sido aceito. Nova submissao exige acao explicita.',
                                        'finishedAt': _now()})
                    entry['status'] = 'uncertain'
                    entry['updatedAt'] = _now()
                    uncertain += 1
                    changed = True
            if changed:
                _save_doc(studio, wpaths, doc)
    return {'resumed': resumed, 'uncertain': uncertain}


def _resume_poll(studio, work_id, request_id, attempt_id):
    key = (studio, work_id, request_id)
    try:
        with studio_review._STATE_LOCK:
            work_doc, wpaths, _, _, _, _ = studio_review._read_work_core(studio, work_id)
            doc = _load_doc(studio, wpaths)
            entry = _find_request(doc, request_id)
            remote_id = entry.get('remoteInteractionId')
            if entry['status'] != 'processing' or not remote_id:
                return
            if attempt_id is None:
                attempt = _attempt_start(entry)
                attempt_id = attempt['attemptId']
                _save_doc(studio, wpaths, doc)
        resolved = studio_connections.resolve_for_project(studio, work_doc.get('project'), 'video')
        if not resolved or not resolved.get('secret'):
            _note_poll_error(studio, work_id, request_id, attempt_id,
                             'credencial nao resolvida na retomada; confira a conexao na aba Conexoes')
            return
        try:
            payload = _get_json(f'{resolved["endpoint"].rstrip("/")}/v1beta/interactions/{remote_id}',
                                _headers(resolved['secret']), min(_timeout_for(resolved), 60.0))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, socket.timeout,
                ConnectionError, OSError, ValueError) as exc:
            message = studio_connections._redact(str(getattr(exc, 'reason', exc)), resolved['secret'])
            _note_poll_error(studio, work_id, request_id, attempt_id, f'retomada: {message}')
            return
        _consume_interaction(studio, work_id, request_id, attempt_id, resolved, payload)
    finally:
        with _ACTIVE_LOCK:
            _ACTIVE.pop(key, None)


# ---------------------------------------------------------------------------
# Importacao na Biblioteca (FFprobe + normalizacao silenciosa + promocao)
# ---------------------------------------------------------------------------

def _probe_raw(studio, abs_path):
    try:
        render_local.ensure_video_tools(studio.root)
    except build_video.DeliveryError:
        pass
    return render_local.probe_asset(os.path.dirname(abs_path), abs_path)


def _normalize_silent(studio, staged_abs):
    """Garante MP4 H.264 sem audio; devolve (arquivo_final, info, audio_removido, reencoded)."""
    info = _probe_raw(studio, staged_abs)
    streams = info.get('streams', [])
    video = next((s for s in streams if s.get('codec_type') == 'video'), None)
    if not video:
        raise VideoApiError('INVALID_RESULT', 'o fornecedor devolveu um arquivo sem faixa de video')
    has_audio = any(s.get('codec_type') == 'audio' for s in streams)
    format_name = (info.get('format', {}).get('format_name') or '')
    width, height = int(video.get('width') or 0), int(video.get('height') or 0)
    codec = video.get('codec_name')
    is_mp4 = 'mp4' in format_name
    even = width > 0 and height > 0 and width % 2 == 0 and height % 2 == 0
    if codec == 'h264' and is_mp4 and even and not has_audio:
        final_abs = staged_abs
    else:
        ffmpeg = build_video.get_ffmpeg()
        out_abs = os.path.join(os.path.dirname(staged_abs), 'normalized.mp4')
        cmd = [ffmpeg, '-y', '-i', staged_abs, '-map', '0:v:0', '-an']
        if codec == 'h264' and even:
            cmd += ['-c:v', 'copy']
        else:
            vf = 'scale=trunc(iw/2)*2:trunc(ih/2)*2' if not even else None
            cmd += ['-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p']
            if vf:
                cmd += ['-vf', vf]
        cmd += ['-movflags', '+faststart', out_abs]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if res.returncode != 0:
            raise VideoApiError('NORMALIZE_FAILED',
                                f'falha ao normalizar o clipe para MP4 H.264 sem audio: {res.stderr[-300:]}')
        final_abs = out_abs
    final_info = studio_media.inspect_video_file(final_abs, root=studio.root)
    return final_abs, final_info, has_audio, final_abs != staged_abs


def import_request(studio, work_id, body):
    """Importa o clipe pronto; importacao repetida devolve a mesma versao."""
    request_id = str((body or {}).get('requestId') or '').strip()
    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, _, _ = studio_review._read_work_core(studio, work_id)
        doc = _load_doc(studio, wpaths)
        entry = _find_request(doc, request_id)
        library, _ = studio_media.load_library(studio, work_id, work_doc, wpaths, video_req, carousel_req)
        if entry['status'] == 'imported' and entry.get('imported'):
            asset = studio_media._find_asset(library, entry['imported']['assetId'])
            version = studio_media._find_version(asset, entry['imported']['versionId']) if asset else None
            if version and not version.get('missing'):
                overview = studio_media._overview_payload(studio, work_id, wpaths, library, True,
                                                          video_req, carousel_req)
                return {'request': _public_request(entry), 'assetId': asset['id'],
                        'versionId': version['versionId'], 'deduplicated': True, 'overview': overview}
            raise VideoApiError('IMPORT_MISSING', 'a versao importada anteriormente nao esta mais na biblioteca; '
                                'reimporte o arquivo manualmente antes de repetir')
        if entry['status'] != 'ready' or not entry.get('result'):
            raise VideoApiError('NOT_READY', f'o pedido nao esta pronto para importar (estado: {entry["status"]})')
        staged_abs = studio.confine(entry['result']['stagedPath'])
        if not os.path.isfile(render_local.fs_path(staged_abs)):
            raise VideoApiError('RESULT_MISSING', 'arquivo do resultado ausente; gere o clipe novamente')
        if render_local.sha256_file(staged_abs) != entry['result']['sha256']:
            raise VideoApiError('RESULT_HASH_MISMATCH', 'checksum do resultado divergente; importacao cancelada')
        final_abs, info, audio_removed, reencoded = _normalize_silent(studio, staged_abs)
        sha = render_local.sha256_file(final_abs)
        size = os.path.getsize(render_local.fs_path(final_abs))
        asset_id = studio_media._unique_asset_id(library, studio_media._slug(f'clipe-api-{request_id}'))
        asset = {
            'id': asset_id,
            'name': f'Clipe API — {entry["model"]}',
            'category': 'other',
            'createdAt': _now(),
            'versions': [],
            'selectedVersionId': None,
        }
        library['assets'].append(asset)
        version_id = studio_media._new_version_id()
        rel = f"{wpaths['mediaDir']}/library/{asset_id}/{version_id}.mp4"
        target = studio.confine_workspace(rel)
        fs = render_local.fs_path
        os.makedirs(fs(os.path.dirname(target)), exist_ok=True)
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
            'origin': 'generated-google-gemini-video',
            'license': 'pending',
            'simulated': False,
            'createdAt': _now(),
            'requestId': request_id,
            'candidateId': None,
            'provenance': {
                'provider': 'google-gemini',
                'model': entry['model'],
                'prompt': entry['prompt'],
                'params': dict(entry['params']),
                'connectionId': entry['connectionId'],
                'connectionName': entry['connectionName'],
                'remoteInteractionId': entry.get('remoteInteractionId'),
                'videoRequestId': request_id,
                'sourceSha256': entry['result']['sha256'],
                'audioRemoved': bool(audio_removed),
                'reencoded': bool(reencoded),
                'anchor': None,
                'resultSha256': sha,
            },
            'missing': False,
        }
        asset['versions'].append(version)
        asset['selectedVersionId'] = version_id
        os.replace(fs(final_abs), fs(target))
        try:
            studio_media.save_library(studio, wpaths, library)
        except OSError:
            if os.path.exists(fs(target)):
                os.remove(fs(target))
            raise
        entry['status'] = 'imported'
        entry['imported'] = {'assetId': asset_id, 'versionId': version_id, 'at': _now()}
        entry['updatedAt'] = _now()
        _save_doc(studio, wpaths, doc)
        staging = _staging_dir(studio, request_id)
        shutil.rmtree(render_local.fs_path(staging), ignore_errors=True)
        overview = studio_media._overview_payload(studio, work_id, wpaths, library, True,
                                                  video_req, carousel_req)
        return {'request': _public_request(entry), 'assetId': asset_id, 'versionId': version_id,
                'deduplicated': False, 'version': version, 'overview': overview}