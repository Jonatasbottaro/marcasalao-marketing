"""Adaptador opcional de modelo de texto local e ponto de extensao de imagem.

Mantem o adaptador de texto (POST /v1/chat/completions, ex.: qwen3:8b)
estritamente separado do ponto de extensao para futuros provedores de imagem.
Nesta etapa, midias visuais continuam baseadas exclusivamente em descritores de
necessidade e selecao de arquivos locais do trabalho.

Nao possui dependencias externas: usa apenas biblioteca padrao Python.
"""

import json
import os
import re
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

import studio_review

DEFAULT_LLM_CONFIG = {
    'schemaVersion': 1,
    'enabled': False,
    'endpoint': 'http://127.0.0.1:11434/v1/chat/completions',
    'model': 'qwen3:8b',
    'timeoutSec': 15.0,
    'temperature': 0.2,
}


class LLMAdapterError(RuntimeError):
    """Erro estruturado do adaptador de modelo local com diagnostico em portugues."""

    def __init__(self, code, message, detail=None):
        super().__init__(message)
        self.code = code
        self.detail = detail


class LLMUnavailableError(LLMAdapterError):
    def __init__(self, message, detail=None):
        super().__init__('LLM_UNAVAILABLE', message, detail=detail)


class LLMTimeoutError(LLMAdapterError):
    def __init__(self, message, detail=None):
        super().__init__('LLM_TIMEOUT', message, detail=detail)


class LLMEmptyResponseError(LLMAdapterError):
    def __init__(self, message, detail=None):
        super().__init__('LLM_EMPTY_RESPONSE', message, detail=detail)


class LLMInvalidJsonError(LLMAdapterError):
    def __init__(self, message, detail=None):
        super().__init__('LLM_INVALID_JSON', message, detail=detail)


def _env_override_defaults():
    cfg = dict(DEFAULT_LLM_CONFIG)
    raw_enabled = os.environ.get('STUDIO_LLM_ENABLED')
    if raw_enabled is not None:
        cfg['enabled'] = raw_enabled.strip().lower() in ('1', 'true', 'yes', 'on')
    raw_endpoint = os.environ.get('STUDIO_LLM_ENDPOINT')
    if raw_endpoint and raw_endpoint.strip():
        cfg['endpoint'] = raw_endpoint.strip()
    raw_model = os.environ.get('STUDIO_LLM_MODEL')
    if raw_model and raw_model.strip():
        cfg['model'] = raw_model.strip()
    raw_timeout = os.environ.get('STUDIO_LLM_TIMEOUT_SEC')
    if raw_timeout and raw_timeout.strip():
        try:
            cfg['timeoutSec'] = float(raw_timeout.strip())
        except ValueError:
            pass
    raw_temp = os.environ.get('STUDIO_LLM_TEMPERATURE')
    if raw_temp and raw_temp.strip():
        try:
            cfg['temperature'] = float(raw_temp.strip())
        except ValueError:
            pass
    return cfg


def validate_endpoint_url(url):
    if not isinstance(url, str) or not url.strip():
        raise ValueError('endpoint do modelo local nao pode ser vazio')
    cleaned = url.strip()
    if any(ch.isspace() for ch in cleaned):
        raise ValueError('endpoint do modelo local nao pode conter espacos')
    parsed = urlparse(cleaned)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('endpoint do modelo local deve usar http:// ou https:// com host valido (ex.: http://127.0.0.1:11434/v1/chat/completions)')
    return cleaned


def normalize_llm_config(raw, fallback=None):
    base = dict(fallback or _env_override_defaults())
    if not isinstance(raw, dict):
        return base
    enabled = bool(raw.get('enabled', base['enabled']))
    endpoint = validate_endpoint_url(raw.get('endpoint') if 'endpoint' in raw else base['endpoint'])
    model = str(raw.get('model') if 'model' in raw else base['model']).strip()
    if not model:
        raise ValueError('nome do modelo local nao pode ser vazio (ex.: qwen3:8b)')
    try:
        timeout_sec = float(raw.get('timeoutSec', base['timeoutSec']))
    except (TypeError, ValueError):
        raise ValueError('timeout (segundos) do modelo local deve ser numerico')
    if timeout_sec < 0.2 or timeout_sec > 300.0:
        raise ValueError('timeout do modelo local deve ficar entre 0.2 e 300 segundos')
    try:
        temperature = float(raw.get('temperature', base['temperature']))
    except (TypeError, ValueError):
        raise ValueError('temperature do modelo local deve ser numerica')
    if temperature < 0.0 or temperature > 1.5:
        raise ValueError('temperature do modelo local deve ficar entre 0.0 e 1.5')
    return {
        'schemaVersion': 1,
        'enabled': enabled,
        'endpoint': endpoint,
        'model': model,
        'timeoutSec': round(timeout_sec, 3),
        'temperature': round(temperature, 3),
    }


def llm_config_path(studio):
    return studio.confine_workspace('.workspace/studio/llm-config.json')


def load_llm_config(studio):
    defaults = _env_override_defaults()
    path = llm_config_path(studio)
    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                raw = json.load(handle)
            return normalize_llm_config(raw, fallback=defaults)
        except (OSError, ValueError):
            return defaults
    return defaults


def save_llm_config(studio, payload):
    current = load_llm_config(studio)
    normalized = normalize_llm_config(payload, fallback=current)
    target = llm_config_path(studio)
    studio_review.atomic_write_json(target, normalized)
    return normalized


def extract_json_object_from_text(raw_text):
    """Extrai objeto JSON de texto puro ou cercado em blocos markdown ```json ... ```."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise LLMEmptyResponseError('A resposta do modelo ou texto colado esta vazia.')
    stripped = raw_text.strip()

    fence = re.search(r'```(?:json)?\s*([\s\S]*?)```', stripped, re.IGNORECASE)
    candidate = fence.group(1).strip() if fence else stripped

    if not candidate.startswith('{'):
        first_brace = candidate.find('{')
        last_brace = candidate.rfind('}')
        if first_brace != -1 and last_brace > first_brace:
            candidate = candidate[first_brace:last_brace + 1]

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise LLMInvalidJsonError(
            f'JSON invalido na resposta (linha {exc.lineno}, coluna {exc.colno}): {exc.msg}. '
            'Corrija a sintaxe JSON mantendo apenas um objeto no formato da etapa.',
            detail={'lineno': exc.lineno, 'colno': exc.colno, 'msg': exc.msg},
        )
    if not isinstance(parsed, dict):
        raise LLMInvalidJsonError(
            'A resposta precisa ser um objeto JSON ({...}), e nao lista, numero ou texto solto.'
        )
    return parsed


class TextModelAdapter:
    """Adaptador de texto para servidores locais compativeis com POST /v1/chat/completions."""

    def __init__(self, config):
        self.config = normalize_llm_config(config)

    def request_stage_json(self, stage, system_prompt, user_prompt):
        if not self.config.get('enabled'):
            raise LLMAdapterError(
                'LLM_DISABLED',
                'Adaptador de modelo local esta desligado. Ative-o na aba Planejamento ou use o modo Manual / Copiar e importar.',
            )
        endpoint = validate_endpoint_url(self.config['endpoint'])
        timeout_sec = float(self.config['timeoutSec'])
        body = {
            'model': self.config['model'],
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': float(self.config['temperature']),
            'stream': False,
        }
        encoded = json.dumps(body, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(
            endpoint,
            data=encoded,
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                raw_bytes = resp.read()
        except urllib.error.HTTPError as exc:
            err_body = ''
            try:
                err_body = exc.read().decode('utf-8', errors='replace')[:300]
            except OSError:
                pass
            raise LLMUnavailableError(
                f'Servidor local retornou HTTP {exc.code} na etapa "{stage}": {err_body or exc.reason}. '
                'Verifique o endpoint e o nome do modelo configurado.',
                detail={'httpStatus': exc.code},
            )
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, (TimeoutError, socket.timeout)) or 'timed out' in str(reason).lower():
                raise LLMTimeoutError(
                    f'Tempo limite excedido ({timeout_sec}s) aguardando resposta do modelo "{self.config["model"]}" na etapa "{stage}". '
                    'Seu rascunho atual foi preservado.',
                )
            raise LLMUnavailableError(
                f'Modelo local indisponivel em {endpoint}: {reason}. '
                'Confira se o servidor local esta rodando ou use Copiar e importar / Manual.',
            )
        except (TimeoutError, socket.timeout):
            raise LLMTimeoutError(
                f'Tempo limite excedido ({timeout_sec}s) aguardando resposta do modelo "{self.config["model"]}" na etapa "{stage}". '
                'Seu rascunho atual foi preservado.',
            )

        if not raw_bytes or not raw_bytes.strip():
            raise LLMEmptyResponseError(
                f'Servidor local devolveu corpo vazio na etapa "{stage}". Rascunho preservado.'
            )
        try:
            payload = json.loads(raw_bytes.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LLMInvalidJsonError(
                f'Envelope HTTP do servidor local nao e JSON valido na etapa "{stage}": {exc}.'
            )

        choices = payload.get('choices') if isinstance(payload, dict) else None
        if not isinstance(choices, list) or not choices:
            raise LLMEmptyResponseError(
                f'Resposta do modelo local veio sem "choices" na etapa "{stage}". Rascunho preservado.'
            )
        first = choices[0] if isinstance(choices[0], dict) else {}
        message = first.get('message') if isinstance(first.get('message'), dict) else {}
        content = message.get('content')
        if content is None and isinstance(first.get('text'), str):
            content = first.get('text')
        if not isinstance(content, str) or not content.strip():
            raise LLMEmptyResponseError(
                f'Modelo local "{self.config["model"]}" retornou conteudo vazio na etapa "{stage}". Rascunho preservado.'
            )

        parsed = extract_json_object_from_text(content)
        return {
            'parsed': parsed,
            'rawText': content,
            'model': payload.get('model') or self.config['model'],
            'endpoint': endpoint,
        }


class ImageProviderExtensionPoint:
    """Ponto de extensao desacoplado para provedores visuais.

    A geracao de imagens acontece na biblioteca de midia por trabalho
    (studio_media.py + image_adapters.py), por acao confirmada do operador:
    importacao manual, simulador deterministico ou Google Gemini opcional.
    O adaptador de texto acima permanece independente e inalterado.
    """

    provider_id = 'media-library'
    supports_external_generation = True

    @staticmethod
    def status():
        return {
            'providerId': 'media-library',
            'supportsExternalGeneration': True,
            'message': 'Pedidos visuais na biblioteca de midia: importacao manual, simulador e Google Gemini opcional, sempre por acao confirmada.',
        }

    @staticmethod
    def summarize_media_requirements(video_scenes, carousel_cards, work_media_ids):
        available = set(work_media_ids or [])
        requirements = []
        for scene in video_scenes or []:
            mid = str(scene.get('mediaId') or '').strip()
            requirements.append({
                'targetKind': 'video_scene',
                'targetId': scene.get('id'),
                'descriptor': scene.get('requiredMediaDescriptor') or '',
                'mediaId': mid or None,
                'status': 'selected' if (mid and mid in available) else 'pending_local_file',
            })
        for card in carousel_cards or []:
            mid = str(card.get('mediaId') or '').strip()
            requirements.append({
                'targetKind': 'carousel_card',
                'targetId': card.get('id'),
                'descriptor': card.get('requiredMediaDescriptor') or '',
                'mediaId': mid or None,
                'status': 'selected' if (mid and mid in available) else ('optional_text_only' if not card.get('requiredMediaDescriptor') else 'pending_local_file'),
            })
        return requirements
