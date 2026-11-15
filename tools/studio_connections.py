"""Conexoes de texto e imagem do Video Studio: cadastro, credenciais e historico.

Armazena metadados, escolhas por projeto e referencias de credencial em
`.workspace/studio/connections.json` (formato versionado, gravacao atomica).
O valor da credencial nunca entra nesse arquivo: fica no cofre da estacao
(Windows Credential Manager) ou em backend simulado nos testes, ou e resolvido
de variavel de ambiente no momento da chamada. Respostas, erros, logs e
historico carregam apenas referencias e metadados.
"""

from __future__ import annotations

import ctypes
import json
import os
import re
import socket
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import image_adapters
import llm_adapter
import studio_review

CONNECTIONS_SCHEMA_VERSION = 1
CALL_HISTORY_LIMIT = 200
PROVIDERS = {
    'local-llm': {'capabilities': ['text'], 'label': 'Modelo local de texto (OpenAI-compativel)'},
    'google-gemini': {'capabilities': ['image'], 'label': 'Google Gemini (imagem)'},
}
KEBAB_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
ENV_VAR_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


class ConnectionError_(ValueError):
    """Erro estruturado de conexoes com codigo estavel e mensagem normalizada."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def _now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _redact(text, secret):
    if not secret or not isinstance(text, str):
        return text
    return text.replace(secret, '[credencial ocultada]')


# ---------------------------------------------------------------------------
# Cofre de credenciais: interface + backends
# ---------------------------------------------------------------------------

class CredentialStore:
    backend = 'abstract'

    def write(self, ref, secret):
        raise NotImplementedError

    def read(self, ref):
        raise NotImplementedError

    def has(self, ref):
        raise NotImplementedError

    def delete(self, ref):
        raise NotImplementedError


class UnavailableCredentialStore(CredentialStore):
    backend = 'unavailable'

    def _fail(self):
        raise ConnectionError_(
            'CREDENTIAL_STORE_UNAVAILABLE',
            'Cofre de credenciais indisponivel nesta estacao. Use uma conexao com variavel de ambiente '
            '(ex.: GEMINI_API_KEY) ou configure STUDIO_CREDENTIAL_BACKEND=simulated apenas para testes.',
        )

    def write(self, ref, secret):
        self._fail()

    def read(self, ref):
        self._fail()

    def has(self, ref):
        return False

    def delete(self, ref):
        self._fail()


class SimulatedCredentialStore(CredentialStore):
    """Backend de testes: memoria ou arquivo JSON explicito (nunca o cofre real)."""

    backend = 'simulated'

    def __init__(self, path=None):
        self.path = path
        self._mem = {}
        if path and os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as handle:
                    self._mem = json.load(handle)
            except (OSError, ValueError):
                self._mem = {}

    def _flush(self):
        if self.path:
            studio_review.atomic_write_json(self.path, self._mem)

    def write(self, ref, secret):
        self._mem[ref] = secret
        self._flush()

    def read(self, ref):
        return self._mem.get(ref)

    def has(self, ref):
        return ref in self._mem

    def delete(self, ref):
        self._mem.pop(ref, None)
        self._flush()


class WindowsCredentialStore(CredentialStore):
    """Cofre da estacao Windows via CredWriteW/CredReadW/CredDeleteW (advapi32)."""

    backend = 'windows-credential-manager'
    TARGET_PREFIX = 'MarcaSalaoStudio/'

    class _CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ('Flags', ctypes.c_ulong),
            ('Type', ctypes.c_ulong),
            ('TargetName', ctypes.c_wchar_p),
            ('Comment', ctypes.c_wchar_p),
            ('LastWritten', ctypes.c_ulonglong),
            ('CredentialBlobSize', ctypes.c_ulong),
            ('CredentialBlob', ctypes.c_void_p),
            ('Persist', ctypes.c_ulong),
            ('AttributeCount', ctypes.c_ulong),
            ('Attributes', ctypes.c_void_p),
            ('TargetAlias', ctypes.c_wchar_p),
            ('UserName', ctypes.c_wchar_p),
        ]

    def __init__(self):
        self._adv = ctypes.windll.advapi32
        self._adv.CredWriteW.argtypes = [ctypes.POINTER(self._CREDENTIALW), ctypes.c_ulong]
        self._adv.CredWriteW.restype = ctypes.c_bool
        self._adv.CredReadW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong,
                                       ctypes.POINTER(ctypes.POINTER(self._CREDENTIALW))]
        self._adv.CredReadW.restype = ctypes.c_bool
        self._adv.CredDeleteW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong]
        self._adv.CredDeleteW.restype = ctypes.c_bool
        self._adv.CredFree.argtypes = [ctypes.c_void_p]

    def _target(self, ref):
        return self.TARGET_PREFIX + ref

    def write(self, ref, secret):
        blob = secret.encode('utf-8')
        buf = ctypes.create_string_buffer(blob)
        cred = self._CREDENTIALW()
        cred.Flags = 0
        cred.Type = 1  # CRED_TYPE_GENERIC
        cred.TargetName = self._target(ref)
        cred.CredentialBlobSize = len(blob)
        cred.CredentialBlob = ctypes.cast(buf, ctypes.c_void_p)
        cred.Persist = 2  # CRED_PERSIST_LOCAL_MACHINE
        cred.UserName = 'MarcaSalaoStudio'
        if not self._adv.CredWriteW(ctypes.byref(cred), 0):
            raise ConnectionError_('CREDENTIAL_STORE_WRITE_FAILED',
                                   f'Falha ao gravar a credencial no cofre do Windows (erro {ctypes.GetLastError()}).')

    def read(self, ref):
        ptr = ctypes.POINTER(self._CREDENTIALW)()
        if not self._adv.CredReadW(self._target(ref), 1, 0, ctypes.byref(ptr)):
            return None
        try:
            cred = ptr.contents
            size = int(cred.CredentialBlobSize)
            if not size or not cred.CredentialBlob:
                return None
            return ctypes.string_at(cred.CredentialBlob, size).decode('utf-8', errors='replace')
        finally:
            self._adv.CredFree(ptr)

    def has(self, ref):
        return self.read(ref) is not None

    def delete(self, ref):
        self._adv.CredDeleteW(self._target(ref), 1, 0)


def get_credential_store():
    backend = (os.environ.get('STUDIO_CREDENTIAL_BACKEND') or 'auto').strip().lower()
    if backend == 'simulated':
        return SimulatedCredentialStore(os.environ.get('STUDIO_CREDENTIAL_STORE_PATH') or None)
    if backend == 'windows':
        if os.name != 'nt':
            return UnavailableCredentialStore()
        return WindowsCredentialStore()
    if os.name == 'nt':
        return WindowsCredentialStore()
    return UnavailableCredentialStore()


# ---------------------------------------------------------------------------
# Armazenamento versionado de metadados / escolhas / historico
# ---------------------------------------------------------------------------

def connections_path(studio):
    return studio.confine_workspace('.workspace/studio/connections.json')


def _load_doc(studio):
    path = connections_path(studio)
    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                doc = json.load(handle)
            if isinstance(doc, dict) and doc.get('schemaVersion') == CONNECTIONS_SCHEMA_VERSION:
                doc.setdefault('connections', [])
                doc.setdefault('selections', {})
                doc.setdefault('calls', [])
                return doc
        except (OSError, ValueError):
            pass
    return {'schemaVersion': CONNECTIONS_SCHEMA_VERSION, 'connections': [], 'selections': {}, 'calls': []}


def _save_doc(studio, doc):
    studio_review.atomic_write_json(connections_path(studio), doc)


def _find(doc, connection_id):
    conn = next((c for c in doc['connections'] if c.get('id') == connection_id), None)
    if conn is None:
        raise ConnectionError_('CONNECTION_NOT_FOUND', f'conexao nao encontrada: {connection_id}')
    return conn


def _public_connection(conn, store):
    cred = conn.get('credential') or {}
    kind = cred.get('kind') or 'none'
    if kind == 'vault':
        configured = bool(cred.get('vaultRef')) and store.has(cred['vaultRef'])
    elif kind == 'env':
        configured = bool(os.environ.get(cred.get('envVar') or ''))
    else:
        configured = True
    return {
        'id': conn['id'],
        'name': conn.get('name'),
        'provider': conn.get('provider'),
        'providerLabel': PROVIDERS.get(conn.get('provider'), {}).get('label'),
        'capabilities': list(conn.get('capabilities') or []),
        'endpoint': conn.get('endpoint'),
        'model': conn.get('model'),
        'timeoutSec': conn.get('timeoutSec'),
        'credential': {
            'kind': kind,
            'envVar': cred.get('envVar'),
            'vaultRef': cred.get('vaultRef'),
            'configured': configured,
        },
        'lastTest': conn.get('lastTest'),
        'createdAt': conn.get('createdAt'),
        'updatedAt': conn.get('updatedAt'),
    }


def resolve_secret(conn, store):
    """Resolve o valor no momento da chamada; nunca registra o valor."""
    cred = conn.get('credential') or {}
    kind = cred.get('kind') or 'none'
    if kind == 'vault':
        ref = cred.get('vaultRef')
        if not ref:
            return None
        return store.read(ref)
    if kind == 'env':
        var = cred.get('envVar') or ''
        return (os.environ.get(var) or '').strip() or None
    return None


def _validate_endpoint(provider, endpoint):
    if provider == 'local-llm':
        return llm_adapter.validate_endpoint_url(endpoint)
    cleaned = (endpoint or '').strip().rstrip('/')
    parsed = urlparse(cleaned)
    local_http = parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost')
    if parsed.scheme != 'https' and not local_http:
        raise ConnectionError_('BAD_ENDPOINT',
                               'Endpoint Gemini deve usar https://generativelanguage.googleapis.com '
                               '(http apenas para servidor local de teste).')
    if not parsed.hostname:
        raise ConnectionError_('BAD_ENDPOINT', 'Endpoint Gemini sem host valido.')
    return cleaned


def save_connection(studio, body):
    if not isinstance(body, dict):
        raise ValueError('payload de conexao invalido')
    store = get_credential_store()
    doc = _load_doc(studio)
    conn_id = (body.get('id') or '').strip()
    name = (body.get('name') or '').strip()
    provider = (body.get('provider') or '').strip()
    if provider not in PROVIDERS:
        raise ConnectionError_('BAD_PROVIDER', f'provedor nao suportado nesta versao: {provider} '
                               f'(use {", ".join(PROVIDERS)})')
    if not name:
        raise ValueError('nome da conexao nao pode ser vazio')
    endpoint = _validate_endpoint(provider, body.get('endpoint') or (
        llm_adapter.DEFAULT_LLM_CONFIG['endpoint'] if provider == 'local-llm'
        else image_adapters.DEFAULT_GEMINI_ENDPOINT))
    model = (body.get('model') or '').strip() or (
        llm_adapter.DEFAULT_LLM_CONFIG['model'] if provider == 'local-llm'
        else image_adapters.DEFAULT_GEMINI_MODEL)
    if provider == 'google-gemini' and not image_adapters.GEMINI_MODEL_RE.match(model):
        raise ConnectionError_('BAD_MODEL', f'identificador de modelo Gemini invalido: {model}')
    try:
        timeout_sec = float(body.get('timeoutSec') or (15.0 if provider == 'local-llm' else 120.0))
    except (TypeError, ValueError):
        raise ValueError('timeout deve ser numerico')
    timeout_sec = max(0.2, min(600.0, timeout_sec))

    cred_in = body.get('credential') or {}
    kind = (cred_in.get('kind') or 'none').strip()
    if kind not in ('none', 'vault', 'env'):
        raise ConnectionError_('BAD_CREDENTIAL_KIND', f'tipo de credencial invalido: {kind}')
    if provider == 'local-llm' and kind == 'vault' and not isinstance(store, (WindowsCredentialStore, SimulatedCredentialStore)):
        raise ConnectionError_('CREDENTIAL_STORE_UNAVAILABLE',
                               'Cofre indisponivel; use variavel de ambiente para esta conexao.')
    credential = {'kind': kind, 'envVar': None, 'vaultRef': None}
    if kind == 'env':
        var = (cred_in.get('envVar') or '').strip()
        if not ENV_VAR_RE.match(var):
            raise ConnectionError_('BAD_ENV_VAR', f'nome de variavel de ambiente invalido: {var}')
        credential['envVar'] = var
    elif kind == 'vault':
        credential['vaultRef'] = (cred_in.get('vaultRef') or '').strip() or f'cred-{uuid.uuid4().hex[:10]}'

    existing = next((c for c in doc['connections'] if c.get('id') == conn_id), None) if conn_id else None
    if conn_id and not KEBAB_RE.match(conn_id):
        raise ConnectionError_('BAD_ID', 'id da conexao deve usar kebab-case')
    if existing is None:
        if not conn_id:
            conn_id = f'conn-{uuid.uuid4().hex[:8]}'
            while any(c.get('id') == conn_id for c in doc['connections']):
                conn_id = f'conn-{uuid.uuid4().hex[:8]}'
        conn = {
            'id': conn_id, 'createdAt': _now(), 'lastTest': None,
        }
        doc['connections'].append(conn)
    else:
        conn = existing
        if conn.get('provider') != provider:
            raise ConnectionError_('PROVIDER_IMMUTABLE',
                                   'o provedor de uma conexao existente nao pode ser trocado; crie outra conexao')
        credential['vaultRef'] = credential['vaultRef'] or (conn.get('credential') or {}).get('vaultRef')
    conn.update({
        'name': name,
        'provider': provider,
        'capabilities': list(PROVIDERS[provider]['capabilities']),
        'endpoint': endpoint,
        'model': model,
        'timeoutSec': round(timeout_sec, 3),
        'credential': credential,
        'updatedAt': _now(),
    })

    secret = body.get('credentialValue')
    if secret is not None and str(secret).strip():
        if kind != 'vault':
            raise ConnectionError_('CREDENTIAL_KIND_MISMATCH',
                                   'valor de credencial so pode ser gravado em conexoes do tipo cofre (vault)')
        store.write(credential['vaultRef'], str(secret))
    _save_doc(studio, doc)
    return {'connection': _public_connection(conn, store)}


def replace_credential(studio, body):
    conn_id = (body.get('connectionId') or '').strip()
    value = body.get('value')
    if not isinstance(value, str) or not value.strip():
        raise ValueError('informe o novo valor da credencial')
    store = get_credential_store()
    doc = _load_doc(studio)
    conn = _find(doc, conn_id)
    cred = conn.get('credential') or {}
    if cred.get('kind') != 'vault' or not cred.get('vaultRef'):
        raise ConnectionError_('CREDENTIAL_KIND_MISMATCH',
                               'esta conexao nao usa cofre; troque a variavel de ambiente ou recrie a conexao como cofre')
    store.write(cred['vaultRef'], value)
    conn['updatedAt'] = _now()
    _save_doc(studio, doc)
    return {'connection': _public_connection(conn, store)}


def delete_connection(studio, body):
    conn_id = (body.get('connectionId') or '').strip()
    store = get_credential_store()
    doc = _load_doc(studio)
    conn = _find(doc, conn_id)
    cred = conn.get('credential') or {}
    if cred.get('kind') == 'vault' and cred.get('vaultRef'):
        try:
            store.delete(cred['vaultRef'])
        except ConnectionError_:
            pass
    doc['connections'] = [c for c in doc['connections'] if c.get('id') != conn_id]
    for project, sel in list(doc['selections'].items()):
        for cap in ('text', 'image'):
            if (sel.get(cap) or {}).get('connectionId') == conn_id:
                sel[cap] = None
    _save_doc(studio, doc)
    return {'deleted': conn_id}


def select_for_project(studio, body):
    project = (body.get('project') or '').strip()
    capability = (body.get('capability') or '').strip()
    conn_id = (body.get('connectionId') or '').strip() or None
    model = (body.get('model') or '').strip() or None
    if not project:
        raise ValueError('informe o projeto (caminho do ProjectManifest)')
    if capability not in ('text', 'image'):
        raise ConnectionError_('BAD_CAPABILITY', f'capacidade invalida: {capability} (use text ou image)')
    store = get_credential_store()
    doc = _load_doc(studio)
    if conn_id:
        conn = _find(doc, conn_id)
        if capability not in (conn.get('capabilities') or []):
            raise ConnectionError_('CAPABILITY_MISMATCH',
                                   f'a conexao {conn_id} nao implementa a capacidade {capability}')
        if model and conn['provider'] == 'google-gemini' and not image_adapters.GEMINI_MODEL_RE.match(model):
            raise ConnectionError_('BAD_MODEL', f'identificador de modelo Gemini invalido: {model}')
    sel = doc['selections'].setdefault(project, {'text': None, 'image': None})
    sel[capability] = {'connectionId': conn_id, 'model': model} if conn_id else None
    _save_doc(studio, doc)
    return {'project': project, 'selection': sel}


def resolve_for_project(studio, project, capability):
    """Selecao efetiva do projeto com credencial resolvida; None = legado."""
    if not project:
        return None
    doc = _load_doc(studio)
    sel = (doc['selections'].get(project) or {}).get(capability)
    if not sel or not sel.get('connectionId'):
        return None
    conn = next((c for c in doc['connections'] if c.get('id') == sel['connectionId']), None)
    if conn is None:
        return None
    store = get_credential_store()
    return {
        'connectionId': conn['id'],
        'connectionName': conn.get('name'),
        'provider': conn['provider'],
        'endpoint': conn['endpoint'],
        'model': sel.get('model') or conn.get('model'),
        'timeoutSec': conn.get('timeoutSec'),
        'credentialKind': (conn.get('credential') or {}).get('kind') or 'none',
        'secret': resolve_secret(conn, store),
    }


# ---------------------------------------------------------------------------
# Historico de chamadas
# ---------------------------------------------------------------------------

def record_call(studio, project, connection_id, capability, model, status, code=None,
                usage=None, provider_info=None):
    doc = _load_doc(studio)
    entry = {
        'at': _now(),
        'project': project,
        'connectionId': connection_id,
        'capability': capability,
        'model': model,
        'status': status,
        'code': code,
    }
    if isinstance(usage, dict) and usage:
        entry['usage'] = {k: usage[k] for k in ('promptTokens', 'completionTokens', 'totalTokens', 'imageCount')
                          if k in usage}
    if isinstance(provider_info, dict) and provider_info:
        entry['providerInfo'] = {k: provider_info[k] for k in ('cost', 'quota', 'balance', 'currency')
                                 if k in provider_info}
    doc['calls'].append(entry)
    doc['calls'] = doc['calls'][-CALL_HISTORY_LIMIT:]
    _save_doc(studio, doc)
    return entry


def _normalize_usage(raw):
    if not isinstance(raw, dict):
        return None
    out = {}
    for src, dst in (('prompt_tokens', 'promptTokens'), ('promptTokenCount', 'promptTokens'),
                     ('completion_tokens', 'completionTokens'), ('candidatesTokenCount', 'completionTokens'),
                     ('total_tokens', 'totalTokens'), ('totalTokenCount', 'totalTokens')):
        if src in raw and isinstance(raw[src], (int, float)):
            out[dst] = raw[src]
    return out or None


def _normalize_provider_info(raw):
    if not isinstance(raw, dict):
        return None
    out = {k: raw[k] for k in ('cost', 'quota', 'balance', 'currency') if k in raw}
    return out or None


# ---------------------------------------------------------------------------
# Diagnostico (Testar) — nunca gera conteudo
# ---------------------------------------------------------------------------

def _http_get_json(url, headers, timeout):
    req = urllib.request.Request(url, headers=headers, method='GET')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _classify_http(exc, secret):
    detail = ''
    try:
        detail = exc.read().decode('utf-8', errors='replace')[:300]
    except OSError:
        pass
    finally:
        try:
            exc.close()
        except OSError:
            pass
    detail = _redact(detail, secret)
    if exc.code in (401, 403):
        return 'CREDENTIAL_REFUSED', f'Credencial recusada pelo provedor (HTTP {exc.code}). Troque a chave da conexao ou confira a autorizacao.'
    if exc.code == 429:
        return 'RATE_LIMIT', f'Limite ou cota de requisicoes atingido (HTTP 429). Aguarde a janela antes de novo teste.'
    if exc.code == 404:
        return 'MODEL_INCOMPATIBLE', f'Endpoint ou modelo nao encontrado (HTTP 404). Confira o identificador do modelo.'
    return 'UNAVAILABLE', f'Provedor retornou HTTP {exc.code}. {detail}'.strip()


def test_connection(studio, body):
    conn_id = (body.get('connectionId') or '').strip()
    store = get_credential_store()
    doc = _load_doc(studio)
    conn = _find(doc, conn_id)
    provider = conn['provider']
    secret = resolve_secret(conn, store)
    timeout = float(conn.get('timeoutSec') or 15.0)
    headers = {'Accept': 'application/json'}
    if provider == 'local-llm':
        parsed = urlparse(conn['endpoint'])
        url = f'{parsed.scheme}://{parsed.netloc}/v1/models'
        if secret:
            headers['Authorization'] = f'Bearer {secret}'
    else:
        url = f'{conn["endpoint"]}/v1beta/models'
        if secret:
            headers['x-goog-api-key'] = secret
    status, code, message = 'ok', 'OK', 'Diagnostico concluido com sucesso.'
    try:
        if provider == 'google-gemini' and not secret:
            raise ConnectionError_('CREDENTIAL_MISSING',
                                   'Conexao Gemini sem credencial resolvida. Grave a chave no cofre, selecione uma '
                                   'variavel de ambiente configurada ou use o legado GEMINI_API_KEY.')
        payload = _http_get_json(url, headers, min(timeout, 30.0))
        models = payload.get('models') if provider == 'google-gemini' else payload.get('data')
        names = []
        if isinstance(models, list):
            for m in models:
                if isinstance(m, dict):
                    names.append(str(m.get('name') or m.get('id') or ''))
        wanted = conn.get('model') or ''
        if names and wanted:
            short = wanted.split('/')[-1]
            if not any(n == wanted or n.split('/')[-1] == short for n in names):
                status, code = 'error', 'MODEL_INCOMPATIBLE'
                message = f'Modelo "{wanted}" nao aparece na lista de modelos do servidor. Escolha um modelo listado.'
        if status == 'ok':
            message = f'Servidor respondeu com {len(names)} modelo(s); conexao utilizavel.' if names \
                else 'Servidor respondeu ao diagnostico de disponibilidade.'
    except ConnectionError_ as exc:
        status, code, message = 'error', exc.code, exc.message
    except urllib.error.HTTPError as exc:
        status, code, message = 'error', *_classify_http(exc, secret)
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, (TimeoutError, socket.timeout)) or 'timed out' in str(reason).lower():
            status, code, message = 'error', 'TIMEOUT', f'Tempo limite excedido no diagnostico de {conn["endpoint"]}.'
        else:
            status, code, message = 'error', 'UNAVAILABLE', \
                f'Servidor indisponivel em {conn["endpoint"]}: {_redact(str(reason), secret)}. Confira se o servico esta rodando.'
    except (TimeoutError, socket.timeout):
        status, code, message = 'error', 'TIMEOUT', f'Tempo limite excedido no diagnostico de {conn["endpoint"]}.'
    except (ValueError, OSError) as exc:
        status, code, message = 'error', 'UNAVAILABLE', f'Falha no diagnostico: {_redact(str(exc), secret)}'

    conn['lastTest'] = {'at': _now(), 'status': status, 'code': code, 'message': message}
    conn['updatedAt'] = _now()
    _save_doc(studio, doc)
    record_call(studio, None, conn_id, 'diagnostic', conn.get('model'), status, code)
    return {'connection': _public_connection(conn, store), 'test': conn['lastTest']}


# ---------------------------------------------------------------------------
# Visao publica
# ---------------------------------------------------------------------------

def build_connections_overview(studio):
    store = get_credential_store()
    doc = _load_doc(studio)
    llm_cfg = llm_adapter.load_llm_config(studio)
    gemini_cfg = image_adapters.gemini_config_from_env()
    return {
        'schemaVersion': CONNECTIONS_SCHEMA_VERSION,
        'storeBackend': store.backend,
        'connections': [_public_connection(c, store) for c in doc['connections']],
        'selections': doc['selections'],
        'calls': list(reversed(doc['calls'])),
        'providers': [
            {'provider': pid, 'label': meta['label'], 'capabilities': meta['capabilities']}
            for pid, meta in PROVIDERS.items()
        ],
        'legacy': {
            'text': {
                'enabled': llm_cfg['enabled'],
                'endpoint': llm_cfg['endpoint'],
                'model': llm_cfg['model'],
                'source': 'STUDIO_LLM_* / llm-config.json',
            },
            'image': {
                'configured': bool(gemini_cfg['apiKey']),
                'model': gemini_cfg['model'],
                'source': 'GEMINI_API_KEY / STUDIO_GEMINI_*',
            },
        },
    }