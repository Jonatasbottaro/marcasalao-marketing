"""Gemini REST direto; credencial apenas no ambiente do processo."""
import base64
import json
import os
import re
import urllib.error
import urllib.request


def generate(prompt: str, kind: str, system: str, reference=None, aspect_ratio=None, image_size=None):
    key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not key:
        raise RuntimeError('Cadastre GEMINI_API_KEY nas variáveis privadas do Coolify e reinicie este recurso.')
    if kind not in ('texto', 'imagem'):
        raise RuntimeError('Tipo de geração inválido.')
    model = os.environ.get('GEMINI_TEXT_MODEL', 'gemini-3.8-flash') if kind == 'texto' else os.environ.get('GEMINI_IMAGE_MODEL', 'gemini-3.1-flash-image')
    if not re.fullmatch(r'[a-zA-Z0-9._-]{1,100}', model):
        raise RuntimeError('Nome de modelo inválido nas variáveis do Coolify.')
    if not prompt.strip() or len(prompt) > 24000 or len(system) > 24000:
        raise RuntimeError('Preencha o pedido; limite de 24000 caracteres por campo.')
    config = {'maxOutputTokens': 4096}
    if kind == 'imagem':
        config['responseModalities'] = ['TEXT', 'IMAGE']
    if aspect_ratio is not None or image_size is not None:
        if kind != 'imagem' or aspect_ratio not in ('1:1','4:5','9:16') or image_size not in ('1K','2K'):
            raise RuntimeError('Proporção/resolução de imagem inválida.')
        config['imageConfig'] = {'aspectRatio':aspect_ratio,'imageSize':image_size}
    body = {'contents': [{'role': 'user', 'parts': [{'text': prompt}]}], 'generationConfig': config}
    if reference is not None:
        if kind != 'imagem' or not isinstance(reference, bytes) or not 0 < len(reference) <= 8 * 1024 * 1024:
            raise RuntimeError('Referência deve ser uma imagem PNG de até 8 MiB.')
        body['contents'][0]['parts'].append({'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(reference).decode()}})
    if system.strip():
        body['systemInstruction'] = {'parts': [{'text': system}]}
    request = urllib.request.Request(
        f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
        data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', 'x-goog-api-key': key},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = response.read(32 * 1024 * 1024 + 1)
        if len(raw) > 32 * 1024 * 1024:
            raise RuntimeError('Resposta Gemini maior que o limite de 32 MiB.')
        result = json.loads(raw)
    except urllib.error.HTTPError as exc:
        messages = {400: 'Revise modelo e parâmetros.', 401: 'Confira a chave.', 403: 'Confira chave e permissões do projeto.', 404: 'Confira o modelo configurado.', 429: 'Cota ou limite atingido; confira créditos e limites no Google.'}
        raise RuntimeError(f'Gemini HTTP {exc.code}. {messages.get(exc.code, "Provedor indisponível; tente novamente depois.")} Nenhuma repetição automática executada.') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError('Falha de conexão ou timeout no Gemini. Confira o estado da solicitação antes de repetir.') from None
    except (ValueError, TypeError):
        raise RuntimeError('Resposta Gemini inválida.') from None
    candidates = result.get('candidates') or []
    if not candidates:
        raise RuntimeError('Gemini não retornou conteúdo; revise o pedido e as políticas do provedor.')
    parts = candidates[0].get('content', {}).get('parts', [])
    text = '\n'.join(part['text'] for part in parts if isinstance(part.get('text'), str) and not part.get('thought'))
    image = None
    for part in parts:
        inline = part.get('inlineData', {})
        if str(inline.get('mimeType', '')).startswith('image/'):
            try:
                image = base64.b64decode(inline['data'], validate=True)
            except (KeyError, ValueError, TypeError):
                raise RuntimeError('Imagem Gemini inválida.') from None
            break
    if kind == 'imagem' and image is None:
        raise RuntimeError('Gemini não retornou imagem; confira modelo de imagem e pedido.')
    if kind == 'texto' and not text.strip():
        raise RuntimeError('Gemini não retornou conteúdo textual utilizável.')
    return text, image
