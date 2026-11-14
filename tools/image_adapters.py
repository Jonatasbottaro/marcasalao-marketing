"""Adaptadores de imagem substituiveis do Studio local.

Tres caminhos independentes, escolhidos pelo operador por acao confirmada:
  1. Importacao manual (sem rede, sem chave): tratada em studio_media.py.
  2. Simulador deterministico para fixtures, testes e demonstracao guiada.
  3. Google Gemini opcional (API oficial generateContent), com GEMINI_API_KEY
     apenas no ambiente do processo; o painel exibe somente o estado da
     configuracao, nunca a credencial.

Diagnosticos em portugues, uma chamada por acao confirmada, sem retry
automatico. Validacao de formato pelo conteudo (magic bytes), sem dependencias
externas: apenas biblioteca padrao Python.
"""

import base64
import hashlib
import json
import os
import re
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

import carousel_layout

MAX_IMAGE_BYTES = 20 * 1024 * 1024
IMAGE_FORMAT_EXTENSIONS = {'png': '.png', 'jpeg': '.jpg', 'webp': '.webp'}
IMAGE_FORMAT_MIMES = {'png': 'image/png', 'jpeg': 'image/jpeg', 'webp': 'image/webp'}
GEMINI_MODEL_RE = re.compile(r'^[a-z0-9][a-z0-9.\-]*$')
DEFAULT_GEMINI_MODEL = 'gemini-3.1-flash-image'
DEFAULT_GEMINI_ENDPOINT = 'https://generativelanguage.googleapis.com'


class ImageAdapterError(RuntimeError):
    """Erro estruturado de adaptador de imagem com diagnostico em portugues."""

    def __init__(self, code, message, detail=None):
        super().__init__(message)
        self.code = code
        self.detail = detail


class ImageProviderUnavailableError(ImageAdapterError):
    def __init__(self, code, message, detail=None):
        super().__init__(code, message, detail=detail)


class ImageProviderTimeoutError(ImageAdapterError):
    def __init__(self, message, detail=None):
        super().__init__('IMAGE_PROVIDER_TIMEOUT', message, detail=detail)


def inspect_image_bytes(data):
    """Valida o formato pelo conteudo e extrai dimensoes (PNG, JPEG, WebP)."""
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError('conteudo de imagem invalido (esperado bytes)')
    if len(data) < 12:
        raise ValueError('arquivo de imagem muito pequeno ou corrompido; importe um PNG, JPEG ou WebP valido')
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f'imagem acima do limite de {MAX_IMAGE_BYTES // (1024 * 1024)} MB; reduza o arquivo antes de importar')
    data = bytes(data)
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        if data[12:16] != b'IHDR':
            raise ValueError('PNG sem cabecalho IHDR; arquivo corrompido')
        width = int.from_bytes(data[16:20], 'big')
        height = int.from_bytes(data[20:24], 'big')
        fmt = 'png'
    elif data[:2] == b'\xff\xd8':
        width, height = _jpeg_dimensions(data)
        fmt = 'jpeg'
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        width, height = _webp_dimensions(data)
        fmt = 'webp'
    else:
        raise ValueError('formato de imagem nao reconhecido pelo conteudo; use PNG, JPEG ou WebP')
    if width <= 0 or height <= 0 or width > 16384 or height > 16384:
        raise ValueError('dimensoes de imagem invalidas ou acima do suportado (ate 16384 px por lado)')
    return {'format': fmt, 'width': width, 'height': height, 'bytes': len(data)}


def _jpeg_dimensions(data):
    pos = 2
    sof_markers = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while pos + 4 < len(data):
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker == 0xFF:
            pos += 1
            continue
        if marker == 0xD8 or marker == 0x01 or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        if marker == 0xDA:
            break
        length = int.from_bytes(data[pos + 2:pos + 4], 'big')
        if marker in sof_markers:
            if pos + 9 > len(data):
                break
            height = int.from_bytes(data[pos + 5:pos + 7], 'big')
            width = int.from_bytes(data[pos + 7:pos + 9], 'big')
            return width, height
        pos += 2 + length
    raise ValueError('JPEG sem quadro SOF legivel; arquivo corrompido ou formato nao suportado')


def _webp_dimensions(data):
    pos = 12
    while pos + 8 <= len(data):
        tag = data[pos:pos + 4]
        size = int.from_bytes(data[pos + 4:pos + 8], 'little')
        payload = pos + 8
        if tag == b'VP8X' and payload + 10 <= len(data):
            width = 1 + int.from_bytes(data[payload + 4:payload + 7], 'little')
            height = 1 + int.from_bytes(data[payload + 7:payload + 10], 'little')
            return width, height
        if tag == b'VP8L' and payload + 5 <= len(data):
            bits = int.from_bytes(data[payload + 1:payload + 5], 'little')
            width = 1 + (bits & 0x3FFF)
            height = 1 + ((bits >> 14) & 0x3FFF)
            return width, height
        if tag == b'VP8 ' and payload + 10 <= len(data):
            if data[payload + 3:payload + 6] == b'\x9d\x01\x2a':
                width = int.from_bytes(data[payload + 6:payload + 8], 'little') & 0x3FFF
                height = int.from_bytes(data[payload + 8:payload + 10], 'little') & 0x3FFF
                return width, height
        pos = payload + size + (size % 2)
    raise ValueError('WebP sem quadro de dimensoes legivel; arquivo corrompido')


def extension_for_format(fmt):
    ext = IMAGE_FORMAT_EXTENSIONS.get(fmt)
    if not ext:
        raise ValueError(f'formato de imagem nao suportado: {fmt}')
    return ext


def mime_for_format(fmt):
    mime = IMAGE_FORMAT_MIMES.get(fmt)
    if not mime:
        raise ValueError(f'formato de imagem nao suportado: {fmt}')
    return mime


class SimulatorImageAdapter:
    """Gerador deterministico de PNG para fixtures e demonstracao guiada.

    A mesma entrada (prompt + geometria + hash da referencia) produz sempre os
    mesmos bytes. Todo material e identificado como simulado na biblioteca e
    nos registros de proveniencia.
    """

    provider_id = 'simulator'
    model = 'simulator-v1'

    def generate(self, prompt, geometry, anchor_sha256=None):
        width = int(geometry['width'])
        height = int(geometry['height'])
        seed_text = f'{prompt}|{width}x{height}|{anchor_sha256 or ""}'
        seed = hashlib.sha256(seed_text.encode('utf-8')).digest()
        top = (seed[0], seed[1], seed[2])
        bottom = (seed[3], seed[4], seed[5])
        accent = (seed[6], seed[7], seed[8])
        rgb = bytearray(width * height * 3)
        for y in range(height):
            ratio = y / max(1, height - 1)
            row = bytes(tuple(int(top[c] + (bottom[c] - top[c]) * ratio) for c in range(3)))
            rgb[y * width * 3:(y + 1) * width * 3] = row * width
        # Faixa central de destaque, derivada do seed (deterministica).
        band_y = int(height * (0.30 + (seed[9] % 20) / 100.0))
        band_h = max(24, height // 8)
        for yy in range(band_y, min(height, band_y + band_h)):
            for xx in range(int(width * 0.08), int(width * 0.92)):
                idx = (yy * width + xx) * 3
                rgb[idx] = accent[0]
                rgb[idx + 1] = accent[1]
                rgb[idx + 2] = accent[2]
        scale = max(2, min(6, width // 220))
        carousel_layout._draw_text(rgb, width, 40, 40, 'IMAGEM SIMULADA', scale, (255, 255, 255))
        label = hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:12].upper()
        carousel_layout._draw_text(rgb, width, 40, 40 + scale * 12, f'PROMPT {label}', max(2, scale - 1), (255, 255, 255))
        carousel_layout._draw_text(rgb, width, 40, height - 40 - scale * 8, f'{width}X{height}', max(2, scale - 1), (255, 255, 255))
        data = carousel_layout.encode_png(width, height, rgb)
        return {
            'bytes': data,
            'format': 'png',
            'width': width,
            'height': height,
            'provider': self.provider_id,
            'model': self.model,
            'simulated': True,
        }


def gemini_config_from_env(env=None):
    env = os.environ if env is None else env
    try:
        timeout = float(env.get('STUDIO_GEMINI_TIMEOUT_SEC', '120'))
    except (TypeError, ValueError):
        timeout = 120.0
    timeout = max(5.0, min(600.0, timeout))
    return {
        'apiKey': (env.get('GEMINI_API_KEY') or '').strip(),
        'model': (env.get('STUDIO_GEMINI_IMAGE_MODEL') or DEFAULT_GEMINI_MODEL).strip(),
        'endpoint': (env.get('STUDIO_GEMINI_IMAGE_ENDPOINT') or DEFAULT_GEMINI_ENDPOINT).strip().rstrip('/'),
        'timeoutSec': timeout,
    }


def provider_status(env=None):
    """Estado publico dos provedores; nunca expoe a credencial."""
    cfg = gemini_config_from_env(env)
    return [
        {
            'providerId': 'manual',
            'label': 'Importacao manual',
            'available': True,
            'requiresCredential': False,
            'message': 'Copie o pedido visual, gere em qualquer ferramenta autorizada e importe o arquivo resultante. Funciona sem rede e sem chave.',
        },
        {
            'providerId': 'simulator',
            'label': 'Simulador (fixtures)',
            'available': True,
            'requiresCredential': False,
            'message': 'Gera imagens determinísticas marcadas como simuladas, para testes e demonstracao guiada.',
        },
        {
            'providerId': 'google-gemini',
            'label': 'Google Gemini',
            'available': bool(cfg['apiKey']),
            'requiresCredential': True,
            'configured': bool(cfg['apiKey']),
            'model': cfg['model'],
            'message': (
                'GEMINI_API_KEY configurada no ambiente do processo; geracao habilitada por acao confirmada.'
                if cfg['apiKey']
                else 'GEMINI_API_KEY ausente no ambiente do processo. Defina a chave autorizada e reinicie o Studio, ou use a importacao manual.'
            ),
        },
    ]


class GeminiImageAdapter:
    """Adaptador opcional para a API oficial de geracao de imagens do Gemini.

    Usa POST {endpoint}/v1/models/{model}:generateContent com header
    x-goog-api-key, responseModalities TEXT+IMAGE e imageConfig.aspectRatio.
    A referencia visual (VisualAnchor) e enviada como inline_data somente quando
    o operador marcar o envio no pedido.
    """

    provider_id = 'google-gemini'

    def __init__(self, env=None):
        cfg = gemini_config_from_env(env)
        self.api_key = cfg['apiKey']
        self.model = cfg['model']
        self.endpoint = cfg['endpoint']
        self.timeout_sec = cfg['timeoutSec']

    def _validate_config(self):
        if not self.api_key:
            raise ImageProviderUnavailableError(
                'IMAGE_PROVIDER_NO_CREDENTIAL',
                'GEMINI_API_KEY nao esta configurada no ambiente do processo. '
                'Defina a chave autorizada e reinicie o Studio, ou use a importacao manual / simulador.',
            )
        if not GEMINI_MODEL_RE.match(self.model or ''):
            raise ImageAdapterError(
                'IMAGE_PROVIDER_BAD_MODEL',
                f'Identificador de modelo Gemini invalido: "{self.model}". '
                'Use um identificador como gemini-3.1-flash-image (STUDIO_GEMINI_IMAGE_MODEL).',
            )
        parsed = urlparse(self.endpoint)
        local_http = parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost')
        if parsed.scheme != 'https' and not local_http:
            raise ImageAdapterError(
                'IMAGE_PROVIDER_BAD_ENDPOINT',
                f'Endpoint Gemini invalido: "{self.endpoint}". Use https://generativelanguage.googleapis.com '
                '(http apenas para servidor local de teste).',
            )
        if not parsed.hostname:
            raise ImageAdapterError(
                'IMAGE_PROVIDER_BAD_ENDPOINT',
                f'Endpoint Gemini sem host valido: "{self.endpoint}".',
            )

    def generate(self, prompt, geometry, aspect_ratio, anchor_bytes=None, anchor_mime=None):
        self._validate_config()
        parts = [{'text': prompt}]
        if anchor_bytes:
            parts.append({'inline_data': {'mime_type': anchor_mime or 'image/png', 'data': base64.b64encode(anchor_bytes).decode('ascii')}})
        body = {
            'contents': [{'role': 'user', 'parts': parts}],
            'generationConfig': {
                'responseModalities': ['TEXT', 'IMAGE'],
                'imageConfig': {'aspectRatio': aspect_ratio},
            },
        }
        url = f'{self.endpoint}/v1/models/{self.model}:generateContent'
        req = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': self.api_key,
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            detail = ''
            try:
                detail = exc.read().decode('utf-8', errors='replace')[:300]
            except OSError:
                pass
            raise self._http_error(exc.code, detail)
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, (TimeoutError, socket.timeout)) or 'timed out' in str(reason).lower():
                raise ImageProviderTimeoutError(
                    f'Tempo limite excedido ({self.timeout_sec}s) aguardando o Gemini. '
                    'Nenhuma imagem foi registrada; decida se quer tentar novamente ou importar manualmente.',
                )
            raise ImageProviderUnavailableError(
                'IMAGE_PROVIDER_UNAVAILABLE',
                f'Falha de comunicacao com o Gemini em {self.endpoint}: {reason}. '
                'Confira a rede ou use a importacao manual; nenhuma tentativa automatica sera feita.',
            )
        except (TimeoutError, socket.timeout):
            raise ImageProviderTimeoutError(
                f'Tempo limite excedido ({self.timeout_sec}s) aguardando o Gemini. '
                'Nenhuma imagem foi registrada; decida se quer tentar novamente ou importar manualmente.',
            )
        return self._parse_response(raw)

    def _http_error(self, status, detail):
        suffix = f' Detalhe: {detail}' if detail else ''
        if status in (401, 403):
            return ImageProviderUnavailableError(
                'IMAGE_PROVIDER_AUTH',
                f'Google recusou a credencial (HTTP {status}). Confira se GEMINI_API_KEY e a chave autorizada para este teste.{suffix}',
                {'httpStatus': status},
            )
        if status == 404:
            return ImageAdapterError(
                'IMAGE_PROVIDER_BAD_MODEL',
                f'Modelo "{self.model}" nao encontrado no endpoint (HTTP 404). '
                f'Confira o identificador em STUDIO_GEMINI_IMAGE_MODEL.{suffix}',
                {'httpStatus': status},
            )
        if status == 429:
            return ImageProviderUnavailableError(
                'IMAGE_PROVIDER_QUOTA',
                f'Cota ou limite de requisicoes do Google atingido (HTTP 429). '
                f'Aguarde a janela de cota ou use a importacao manual; sem retry automatico.{suffix}',
                {'httpStatus': status},
            )
        if status == 400:
            return ImageAdapterError(
                'IMAGE_PROVIDER_BAD_REQUEST',
                f'O Google rejeitou a solicitacao (HTTP 400). Confira modelo, endpoint e formato do pedido.{suffix}',
                {'httpStatus': status},
            )
        return ImageProviderUnavailableError(
            'IMAGE_PROVIDER_UNAVAILABLE',
            f'Google Gemini retornou HTTP {status}. Nenhuma imagem foi registrada; tente novamente quando o servico estabilizar ou importe manualmente.{suffix}',
            {'httpStatus': status},
        )

    def _parse_response(self, raw):
        try:
            payload = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ImageAdapterError(
                'IMAGE_PROVIDER_INVALID_RESPONSE',
                'Resposta do Gemini nao e JSON valido. Nenhuma imagem foi registrada.',
            )
        if not isinstance(payload, dict):
            raise ImageAdapterError(
                'IMAGE_PROVIDER_INVALID_RESPONSE',
                'Resposta do Gemini fora do formato esperado (objeto JSON). Nenhuma imagem foi registrada.',
            )
        feedback = payload.get('promptFeedback') or {}
        if isinstance(feedback, dict) and feedback.get('blockReason'):
            raise ImageAdapterError(
                'IMAGE_PROVIDER_REFUSED',
                f'O Google recusou o prompt (bloqueio: {feedback["blockReason"]}). '
                'Revise o texto do pedido e a referencia visual antes de tentar novamente.',
            )
        candidates = payload.get('candidates') or []
        if not isinstance(candidates, list) or not candidates:
            raise ImageAdapterError(
                'IMAGE_PROVIDER_NO_IMAGE',
                'O Gemini respondeu sem candidatos. Nenhuma imagem foi registrada; revise o pedido ou importe manualmente.',
            )
        first = candidates[0] if isinstance(candidates[0], dict) else {}
        finish = str(first.get('finishReason') or '')
        if finish and finish not in ('STOP', 'MAX_TOKENS', 'FINISH_REASON_UNSPECIFIED'):
            raise ImageAdapterError(
                'IMAGE_PROVIDER_REFUSED',
                f'O Google interrompeu a geracao (finishReason: {finish}). '
                'Revise o prompt e a referencia; nenhuma imagem foi registrada.',
            )
        content = first.get('content') or {}
        parts = content.get('parts') or [] if isinstance(content, dict) else []
        for part in parts:
            if not isinstance(part, dict):
                continue
            inline = part.get('inlineData') or part.get('inline_data')
            if not isinstance(inline, dict):
                continue
            data_b64 = inline.get('data')
            if not isinstance(data_b64, str) or not data_b64:
                continue
            try:
                data = base64.b64decode(data_b64, validate=True)
            except (ValueError, TypeError):
                raise ImageAdapterError(
                    'IMAGE_PROVIDER_INVALID_FILE',
                    'O Gemini retornou dados de imagem em base64 invalido. Nenhuma imagem foi registrada.',
                )
            try:
                info = inspect_image_bytes(data)
            except ValueError as exc:
                raise ImageAdapterError(
                    'IMAGE_PROVIDER_INVALID_FILE',
                    f'O Gemini retornou um arquivo de imagem invalido: {exc}. Nenhuma imagem foi registrada.',
                )
            return {
                'bytes': data,
                'format': info['format'],
                'width': info['width'],
                'height': info['height'],
                'provider': self.provider_id,
                'model': payload.get('modelVersion') or self.model,
                'simulated': False,
            }
        raise ImageAdapterError(
            'IMAGE_PROVIDER_NO_IMAGE',
            'O Gemini respondeu sem imagem (apenas texto ou partes vazias). '
            'Confira se o modelo configurado suporta geracao de imagens; nenhuma imagem foi registrada.',
        )


def build_provider_text(request_doc, anchor_doc=None):
    """Texto exatamente enviado ao provedor, mostrado antes da confirmacao."""
    lines = [str(request_doc.get('prompt') or '').strip()]
    framing = str(request_doc.get('framing') or '').strip()
    if framing:
        lines.append(f'Enquadramento: {framing}')
    geometry = request_doc.get('geometry') or {}
    lines.append(f'Proporcao: {request_doc.get("aspectRatio")} ({geometry.get("width")}x{geometry.get("height")})')
    link = request_doc.get('anchor')
    if link and link.get('sendToProvider') and isinstance(anchor_doc, dict):
        lines.append(f'Direcao visual de referencia: {anchor_doc.get("direction")}')
        must_include = anchor_doc.get('mustInclude') or []
        if must_include:
            lines.append('Elementos que precisam aparecer: ' + '; '.join(must_include))
        must_avoid = anchor_doc.get('mustAvoid') or []
        if must_avoid:
            lines.append('Elementos a evitar: ' + '; '.join(must_avoid))
    return '\n'.join(line for line in lines if line)