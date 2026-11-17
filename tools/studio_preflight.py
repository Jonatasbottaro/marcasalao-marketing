"""CLI local de diagnostico de pre-voo de producao no Video Studio.

Consulta a instancia em execucao do Video Studio em loopback (`POST /api/queue/preflight`)
sem alterar rascunhos, fila, revisoes ou entregas.

Codigos de saida:
  0  Checagem concluida e destino pronto (ready)
  1  Checagem concluida e destino bloqueado (blocked)
  2  Erro de uso, transporte (Studio desligado/timeout) ou resposta invalida
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


LOOPBACK_HOSTS = {'127.0.0.1', 'localhost', '::1'}


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description='Diagnostico de pre-voo de producao por trabalho, modalidade e perfil'
    )
    parser.add_argument('--port', type=int, required=True, help='Porta do Video Studio local em execucao')
    parser.add_argument('--host', default='127.0.0.1', help='Endereco loopback do Studio (padrao: 127.0.0.1)')
    parser.add_argument('--work-id', required=True, help='Identificador do trabalho salvo')
    parser.add_argument(
        '--modality',
        required=True,
        choices=('video', 'carousel', 'motion'),
        help='Modalidade de producao (video, carousel ou motion)',
    )
    parser.add_argument('--profile', required=True, help='Identificador do perfil de saida')
    parser.add_argument('--timeout', type=float, default=60.0, help='Timeout HTTP em segundos (padrao: 60)')
    parser.add_argument('--json', action='store_true', help='Emite somente o relatorio JSON no stdout')
    return parser.parse_args(argv)


def _format_human(item):
    status = item.get('status')
    work_id = item.get('workId')
    modality = item.get('modality')
    profile_id = item.get('profileId')
    lines = []
    if status == 'ready':
        lines.append(f"PRONTO: {work_id} [{modality} / {profile_id}] - {item.get('summary') or 'Destino pronto.'}")
    else:
        lines.append(f"BLOQUEADO: {work_id} [{modality} / {profile_id}] - {item.get('summary') or 'Destino bloqueado.'}")

    blockers = item.get('blockers') or []
    if blockers:
        lines.append('Impedimentos:')
        for b in blockers:
            subj = f" ({b['subject']})" if b.get('subject') else ''
            lines.append(f"  - [{b.get('code', 'BLOCKED')}]{subj}: {b.get('message')}")

    warnings = item.get('warnings') or []
    if warnings:
        lines.append('Avisos:')
        for w in warnings:
            subj = f" ({w['subject']})" if w.get('subject') else ''
            lines.append(f"  - [{w.get('code', 'WARNING')}]{subj}: {w.get('message')}")

    pending = item.get('pendingChecks') or []
    if pending:
        lines.append('Checagens pendentes:')
        for p in pending:
            lines.append(f"  - [{p.get('code', 'PENDING')}]: {p.get('message')}")

    actions = item.get('suggestedActions') or []
    if actions:
        lines.append('Proximos passos:')
        for act in actions:
            lines.append(f"  - {act}")
    return '\n'.join(lines)


def main(argv=None):
    try:
        args = _parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code != 0 else 0

    if args.port < 1 or args.port > 65535:
        print('Erro: --port deve estar entre 1 e 65535.', file=sys.stderr)
        return 2
    host = (args.host or '127.0.0.1').strip()
    if host not in LOOPBACK_HOSTS:
        print('Erro: apenas enderecos loopback (127.0.0.1, localhost, ::1) sao permitidos.', file=sys.stderr)
        return 2
    if args.timeout <= 0:
        print('Erro: --timeout deve ser maior que zero.', file=sys.stderr)
        return 2

    url_host = f'[{host}]' if ':' in host else host
    base = f'http://{url_host}:{args.port}'
    url = f'{base}/api/queue/preflight'
    payload = json.dumps({
        'items': [{
            'workId': args.work_id,
            'modality': args.modality,
            'profileId': args.profile,
        }]
    }).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Origin': base,
        'Host': f'{url_host}:{args.port}',
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            raw = resp.read().decode('utf-8')
    except urllib.error.HTTPError as exc:
        body = ''
        try:
            body = exc.read().decode('utf-8', errors='replace').strip()
        except Exception:
            pass
        print(f'Erro HTTP {exc.code} ao consultar {url}: {body or exc.reason}', file=sys.stderr)
        return 2
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(
            f'Erro de conexao com o Video Studio em {base} ({exc}). '
            'Verifique se o servidor esta ativo com `python tools/video_studio.py --port '
            f'{args.port}`.',
            file=sys.stderr,
        )
        return 2

    try:
        data = json.loads(raw)
    except ValueError:
        print('Erro: resposta invalida do Video Studio (JSON ilegivel).', file=sys.stderr)
        return 2

    if not isinstance(data, dict) or not data.get('ok') or not isinstance(data.get('items'), list) or not data['items']:
        print('Erro: resposta inesperada do Video Studio para /api/queue/preflight.', file=sys.stderr)
        return 2

    item = data['items'][0]
    if not isinstance(item, dict) or item.get('status') not in ('ready', 'blocked'):
        print('Erro: item de diagnostico invalido na resposta do Studio.', file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(_format_human(item))

    return 0 if item['status'] == 'ready' else 1


if __name__ == '__main__':
    raise SystemExit(main())
