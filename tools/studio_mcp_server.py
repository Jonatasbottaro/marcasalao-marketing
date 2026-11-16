"""Servidor MCP (stdio) para o Planejamento do Video Studio.

Expoe duas ferramentas a clientes MCP (Codex, Claude Code, cliente de teste):

- ``consultar_planejamento``: briefing, perfis permitidos, ``contextFingerprint``
  e instrucoes canonicas da etapa ``creative`` (reusa ``build_stage_prompt``).
- ``enviar_proposta``: registra uma ``PlanningSuggestion`` no historico do
  trabalho (reusa o importador validado do Studio), devolvendo ``suggestionId``,
  diferencas e avisos.

O servidor NAO le nem grava o trabalho diretamente: conversa por HTTP de
loopback com a instancia do Studio JA em execucao, que continua responsavel
pela leitura, validacao (contrato do nucleo) e gravacao. O stdout transporta
apenas mensagens MCP (JSON-RPC 2.0 delimitado por newline); diagnosticos vao
para o stderr. Sem SDK de terceiros: somente biblioteca padrao do Python.

Uso (o cliente inicia o subprocesso via stdio):

    python tools/studio_mcp_server.py --port 8765

Requer o Studio rodando em http://127.0.0.1:<porta> (``python tools/video_studio.py --port 8765``).
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

PROTOCOL_VERSION = '2025-06-18'
SUPPORTED_PROTOCOL_VERSIONS = ('2025-06-18', '2025-03-26', '2024-11-05')
SERVER_INFO = {'name': 'video-studio-planejamento', 'version': '1.0.0'}
LOOPBACK_HOST = '127.0.0.1'
DEFAULT_PORT = 8765
DEFAULT_TIMEOUT_S = 120.0


def _log(message):
    sys.stderr.write(f'[studio-mcp] {message}\n')
    sys.stderr.flush()


class StudioUnavailableError(Exception):
    """Studio local nao acessivel em loopback (conexao recusada/timeout)."""


class StudioHttpError(Exception):
    """Resposta nao-2xx do Studio, com status e payload de erro."""

    def __init__(self, status, payload):
        self.status = status
        self.payload = payload if isinstance(payload, dict) else {'error': str(payload)}
        super().__init__(self.payload.get('error') or f'HTTP {status}')


class StudioHttpClient:
    """Adaptador HTTP isolado: destino fixo em loopback, Host/Origin preservados."""

    def __init__(self, port, timeout=DEFAULT_TIMEOUT_S):
        self.port = int(port)
        self.timeout = float(timeout)
        self.base = f'http://{LOOPBACK_HOST}:{self.port}'
        self.origin = self.base

    def _request(self, method, path, body=None):
        url = f'{self.base}{path}'
        data = json.dumps(body).encode('utf-8') if body is not None else None
        headers = {'Host': f'{LOOPBACK_HOST}:{self.port}', 'Accept': 'application/json'}
        if data is not None:
            headers['Content-Type'] = 'application/json'
            headers['Origin'] = self.origin
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode('utf-8', errors='replace')
            try:
                payload = json.loads(raw)
            except ValueError:
                payload = {'error': raw or f'HTTP {exc.code}'}
            raise StudioHttpError(exc.code, payload) from None
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise StudioUnavailableError(str(getattr(exc, 'reason', exc))) from None

    def build_creative_prompt(self, work_id):
        return self._request('POST', '/api/works/planning/prompt',
                             {'workId': work_id, 'stage': 'creative'})

    def import_suggestion(self, work_id, expected_fingerprint, suggestion):
        return self._request('POST', '/api/works/planning/import', {
            'workId': work_id,
            'expectedContextFingerprint': expected_fingerprint,
            'suggestion': suggestion,
        })


def _start_instruction(port):
    return (
        f'Studio local indisponivel em http://{LOOPBACK_HOST}:{port}. '
        f'Inicie a instancia na raiz do projeto com: python tools/video_studio.py --port {port} '
        f'(abra http://{LOOPBACK_HOST}:{port}). Quando o Studio estiver pronto, repita a chamada.'
    )


def _tool_consultar(client, args):
    work_id = args.get('workId')
    if not isinstance(work_id, str) or not work_id.strip():
        raise ValueError('Informe "workId" (string nao vazia) do trabalho do Studio.')
    prompt = client.build_creative_prompt(work_id.strip())
    ctx = prompt.get('contextObject') or {}
    result = {
        'workId': prompt.get('workId', work_id.strip()),
        'stage': 'creative',
        'contract': 'PlanningSuggestion v1 (etapa creative; exige videoScenes e carouselCards)',
        'contextFingerprint': prompt.get('contextFingerprint'),
        'briefingSha256': prompt.get('briefingSha256'),
        'projectId': ctx.get('projectId'),
        'allowedProfiles': prompt.get('allowedProfiles') or [],
        'briefing': ctx.get('briefing') or {},
        'briefingExtended': ctx.get('briefingExtended') or {},
        'claims': ctx.get('claims') or [],
        'availableWorkMedia': ctx.get('availableWorkMedia') or [],
        'instructions': {
            'systemPrompt': prompt.get('systemPrompt'),
            'userPrompt': prompt.get('userPrompt'),
        },
    }
    return result


def _tool_enviar(client, args):
    work_id = args.get('workId')
    if not isinstance(work_id, str) or not work_id.strip():
        raise ValueError('Informe "workId" (string nao vazia) do trabalho do Studio.')
    expected = args.get('expectedContextFingerprint')
    if not isinstance(expected, str) or not expected.strip():
        raise ValueError(
            'Informe "expectedContextFingerprint" obtido em consultar_planejamento; '
            'a proposta fica vinculada ao contexto consultado.'
        )
    suggestion = args.get('suggestion')
    if not isinstance(suggestion, dict):
        raise ValueError('Informe "suggestion" como objeto PlanningSuggestion v1 (etapa creative).')
    res = client.import_suggestion(work_id.strip(), expected.strip(), suggestion)
    record = res.get('suggestionRecord') or {}
    return {
        'workId': work_id.strip(),
        'suggestionId': record.get('suggestionId'),
        'stage': record.get('stage'),
        'createdAt': record.get('createdAt'),
        'baseContextFingerprint': record.get('baseContextFingerprint'),
        'diffPreview': res.get('diffPreview') or {},
        'warnings': res.get('warnings') or [],
        'nextStep': 'Operador revisa no Studio (aba Planejamento > historico > Visualizar / Incorporar > Aplicar).',
    }


TOOLS = [
    {
        'name': 'consultar_planejamento',
        'description': (
            'Consulta o briefing de um trabalho do Video Studio e devolve os perfis permitidos, '
            'o contextFingerprint e as instrucoes canonicas da etapa creative (PlanningSuggestion v1). '
            'Use o contextFingerprint retornado ao enviar uma proposta.'
        ),
        'inputSchema': {
            'type': 'object',
            'additionalProperties': False,
            'required': ['workId'],
            'properties': {
                'workId': {'type': 'string', 'minLength': 1, 'description': 'ID do trabalho no Studio.'},
            },
        },
        'outputSchema': {
            'type': 'object',
            'required': ['workId', 'stage', 'contextFingerprint', 'allowedProfiles', 'instructions'],
            'properties': {
                'workId': {'type': 'string'},
                'stage': {'type': 'string', 'const': 'creative'},
                'contract': {'type': 'string'},
                'contextFingerprint': {'type': 'string'},
                'briefingSha256': {'type': 'string'},
                'projectId': {'type': ['string', 'null']},
                'allowedProfiles': {'type': 'array', 'items': {'type': 'string'}},
                'briefing': {'type': 'object'},
                'briefingExtended': {'type': 'object'},
                'claims': {'type': 'array'},
                'availableWorkMedia': {'type': 'array'},
                'instructions': {'type': 'object'},
            },
        },
    },
    {
        'name': 'enviar_proposta',
        'description': (
            'Registra uma PlanningSuggestion v1 (etapa creative) no historico do trabalho indicado, '
            'vinculada ao expectedContextFingerprint consultado. O Studio valida o contrato e reconfere '
            'o fingerprint sob lock antes de gravar. Devolve suggestionId, diferencas e avisos. '
            'A incorporacao e a aplicacao aos editores continuam sendo acoes do operador no Studio.'
        ),
        'inputSchema': {
            'type': 'object',
            'additionalProperties': False,
            'required': ['workId', 'expectedContextFingerprint', 'suggestion'],
            'properties': {
                'workId': {'type': 'string', 'minLength': 1},
                'expectedContextFingerprint': {'type': 'string', 'minLength': 1},
                'suggestion': {'type': 'object', 'description': 'Objeto PlanningSuggestion v1 (stage creative).'},
            },
        },
        'outputSchema': {
            'type': 'object',
            'required': ['suggestionId', 'diffPreview', 'warnings'],
            'properties': {
                'workId': {'type': 'string'},
                'suggestionId': {'type': 'string'},
                'stage': {'type': 'string'},
                'createdAt': {'type': 'string'},
                'baseContextFingerprint': {'type': 'string'},
                'diffPreview': {'type': 'object'},
                'warnings': {'type': 'array'},
                'nextStep': {'type': 'string'},
            },
        },
    },
]

_TOOL_HANDLERS = {
    'consultar_planejamento': _tool_consultar,
    'enviar_proposta': _tool_enviar,
}


def _tool_error(message, structured=None):
    result = {'content': [{'type': 'text', 'text': message}], 'isError': True}
    if isinstance(structured, dict):
        result['structuredContent'] = structured
    return result


def _tool_success(payload):
    return {
        'content': [{'type': 'text', 'text': json.dumps(payload, ensure_ascii=False)}],
        'structuredContent': payload,
        'isError': False,
    }


def _handle_tool_call(client, params):
    name = (params or {}).get('name')
    args = (params or {}).get('arguments') or {}
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        return _tool_error(f'Ferramenta desconhecida: {name}. Disponiveis: {", ".join(_TOOL_HANDLERS)}.')
    if not isinstance(args, dict):
        return _tool_error('Os argumentos da ferramenta devem ser um objeto JSON.')
    try:
        return _tool_success(handler(client, args))
    except ValueError as exc:
        return _tool_error(str(exc), {'code': 'INVALID_ARGUMENTS'})
    except StudioUnavailableError:
        return _tool_error(_start_instruction(client.port), {'code': 'STUDIO_UNAVAILABLE'})
    except StudioHttpError as exc:
        payload = exc.payload
        if exc.status == 409 or payload.get('conflict'):
            msg = (
                f'{payload.get("error") or "Conflito de contexto."} '
                'Recarregue o contexto com consultar_planejamento para obter o contextFingerprint '
                'atual antes de reenviar a proposta.'
            )
            return _tool_error(msg, {'code': 'CONTEXT_CONFLICT', 'conflict': True})
        code = payload.get('failureCode') or payload.get('code')
        structured = {'code': code or 'STUDIO_ERROR', 'httpStatus': exc.status}
        if payload.get('subject'):
            structured['subject'] = payload['subject']
        if payload.get('stage'):
            structured['stage'] = payload['stage']
        return _tool_error(payload.get('error') or f'HTTP {exc.status}', structured)


def _handle_message(client, msg):
    """Devolve o objeto de resposta JSON-RPC, ou None para notificacoes."""
    if not isinstance(msg, dict):
        return {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32600, 'message': 'Invalid Request'}}
    method = msg.get('method')
    msg_id = msg.get('id')
    is_notification = 'id' not in msg

    if method == 'initialize':
        params = msg.get('params') or {}
        requested = params.get('protocolVersion')
        version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else PROTOCOL_VERSION
        result = {
            'protocolVersion': version,
            'capabilities': {'tools': {'listChanged': False}},
            'serverInfo': SERVER_INFO,
            'instructions': (
                'Ferramentas de Planejamento do Video Studio local. Consulte o briefing com '
                'consultar_planejamento e registre propostas com enviar_proposta usando o '
                'contextFingerprint consultado. A revisao, incorporacao e aplicacao sao do operador no Studio.'
            ),
        }
        return None if is_notification else {'jsonrpc': '2.0', 'id': msg_id, 'result': result}

    if method in ('notifications/initialized', 'notifications/cancelled'):
        return None

    if method == 'ping':
        return None if is_notification else {'jsonrpc': '2.0', 'id': msg_id, 'result': {}}

    if method == 'tools/list':
        result = {'tools': TOOLS}
        return None if is_notification else {'jsonrpc': '2.0', 'id': msg_id, 'result': result}

    if method == 'tools/call':
        result = _handle_tool_call(client, msg.get('params'))
        return None if is_notification else {'jsonrpc': '2.0', 'id': msg_id, 'result': result}

    if is_notification:
        return None
    return {'jsonrpc': '2.0', 'id': msg_id, 'error': {'code': -32601, 'message': f'Method not found: {method}'}}


def serve(client, stdin=None, stdout=None):
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout
    _log(f'pronto; Studio alvo {client.base} (timeout {client.timeout}s)')
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            resp = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Parse error'}}
            stdout.write(json.dumps(resp, ensure_ascii=False) + '\n')
            stdout.flush()
            continue
        try:
            resp = _handle_message(client, msg)
        except Exception as exc:  # falha inesperada nao derruba o transporte
            _log(f'erro interno: {exc}')
            resp = None if 'id' not in msg else {
                'jsonrpc': '2.0', 'id': msg.get('id'),
                'error': {'code': -32603, 'message': f'Internal error: {exc}'},
            }
        if resp is not None:
            stdout.write(json.dumps(resp, ensure_ascii=False) + '\n')
            stdout.flush()
    _log('stdin encerrado; saindo')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Servidor MCP (stdio) do Planejamento do Video Studio')
    parser.add_argument('--port', type=int, default=int(os.environ.get('STUDIO_MCP_PORT', DEFAULT_PORT)),
                        help=f'Porta do Studio em 127.0.0.1 (padrao {DEFAULT_PORT} ou STUDIO_MCP_PORT)')
    parser.add_argument('--timeout', type=float, default=DEFAULT_TIMEOUT_S,
                        help='Tempo limite por chamada HTTP ao Studio (segundos)')
    args = parser.parse_args(argv)
    client = StudioHttpClient(args.port, timeout=args.timeout)
    serve(client)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())