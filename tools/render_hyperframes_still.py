"""Still estatico pelo motor HyperFrames (HF-001, F10) a partir de CarouselRequest v1.

Estrategia especifica para imagens: post/card/carrossel NAO sao export de video.
Cada card vira uma composicao HyperFrames de cena unica (template nativo por
funcao narrativa: primeiro card hook, ultimos-meio demonstration, ultimo cta) e
o PNG sai da captura oficial de quadros (`hyperframes snapshot`) no instante com
entradas concluidas, com codec/geometria verificados por ffprobe. A geometria
vem do perfil de imagem resolvido pelo catalogo + allowlist do projeto (ponte
Node), respeitando 1:1 1080x1080, 4:5 1080x1350 e 9:16 1080x1920. A arte
estatica de feed gerada por IA (ComfyUI08 + guard de proveniencia) permanece
intocada; a exportacao legada de carrossel (produce_carousel.py) permanece
disponivel como fallback enquanto este caminho nao e validado.

Uso (a partir da raiz do checkout):
  python tools/render_hyperframes_still.py --input <pedido.carousel-request.json> --plan-only --json
  python tools/render_hyperframes_still.py --input <pedido.carousel-request.json> --output-dir <entrega> [--tenant <id>] [--json]

Entrega transacional no mesmo contrato do produce_carousel: PNGs numerados
(01-<id>.png, ...), stills.zip na mesma ordem, still-manifest.json (renderer
hyperframes, dimensoes, SHA-256) e index.json com lastAttempt/lastValidDelivery;
promocao sob lock com backup, falha preserva a ultima entrega valida.

Exit codes: 0 sucesso; 1 falha de render/promocao; 2 uso/caminho/JSON;
3 pedido/perfil invalido ou claim proibida pelo guardrails do tenant.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import produce_carousel
import render_hyperframes
import render_local

ADAPTER_TIMEOUT_SECONDS = 900
STILL_DURATION_MS = 2000
ADAPTER_ID = 'hyperframes'


def write_json(path, value):
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def rel(root, path):
    return render_local.rel(root, path)


def load_request(root, input_path):
    if not render_local.contained(root, input_path) or not os.path.isfile(input_path):
        raise render_local.InputFileError('pedido ausente ou fora da raiz do projeto')
    with open(input_path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def narrative_for(index, total):
    """Mesma convencao do compile-video-request: primeiro hook, ultimo cta."""
    if index == 0:
        return 'hook'
    if index == total - 1:
        return 'cta'
    return 'demonstration'


def build_card_profile(verdict, card, still_duration_ms=STILL_DURATION_MS):
    """Perfil compilado de cena unica para o card, no formato consumido pelo adaptador."""
    geometry = verdict['geometry']
    total = len(verdict['cards'])
    index = card['order'] - 1
    return {
        'profileId': verdict['profileId'],
        'caseId': f"{verdict['requestId']}-{card['id']}",
        'status': 'compiled',
        'composition': {'scenes': [{'id': card['id'], 'type': 'image'}]},
        'beatPlan': {'beats': [{'id': card['id'], 'narrativeFunction': narrative_for(index, total)}]},
        'plan': {
            'geometry': {'width': geometry['width'], 'height': geometry['height']},
            'fps': 30,
            'durationMs': still_duration_ms,
            'beats': [{
                'beatId': card['id'],
                'order': card['order'],
                'startMs': 0,
                'durationMs': still_duration_ms,
                'title': card['title'],
                'caption': card.get('body'),
                'narration': '',
                'mediaPath': card.get('mediaPath'),
                'motionIntent': 'none',
                'framing': {'centerX': 0.5, 'centerY': 0.5, 'zoomPercent': 100},
            }],
        },
    }


def run_adapter_still(root, profile_path, workdir, out_path, tenant):
    wrapper = os.path.join(root, 'renderers', 'hyperframes', 'scripts', 'hf-adapter.sh')
    if not os.path.isfile(wrapper):
        raise render_local.InputFileError('wrapper do adaptador ausente: renderers/hyperframes/scripts/hf-adapter.sh')
    cmd = [
        'bash', rel(root, wrapper),
        '--profile-json', profile_path,
        '--root', root,
        '--tenant', tenant,
        '--workdir', workdir,
        '--quality', 'draft',
        '--still',
        '--out', out_path,
    ]
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                               encoding='utf-8', errors='replace',
                               timeout=ADAPTER_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise build_video.DeliveryError('adaptador excedeu o tempo limite')


def adapter_verdict(res):
    """Ultima linha JSON do stdout do adaptador; None se ilegivel."""
    lines = [line for line in (res.stdout or '').strip().splitlines() if line.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except ValueError:
        return None


def verify_still_png(path, width, height):
    """Reverifica o PNG entregue pelo adaptador: codec png e geometria exata."""
    info = build_video.probe_media(path, timeout=render_local.PROBE_TIMEOUT_SECONDS)
    streams = [s for s in info.get('streams', []) if s.get('codec_type') == 'video']
    if len(streams) != 1 or streams[0].get('codec_name') != 'png':
        raise build_video.DeliveryError(f'STILL_INVALID: {os.path.basename(path)} nao e um PNG de quadro unico')
    if int(streams[0].get('width', 0)) != width or int(streams[0].get('height', 0)) != height:
        raise build_video.DeliveryError(
            f'STILL_GEOMETRY_MISMATCH: {os.path.basename(path)} '
            f"{streams[0].get('width')}x{streams[0].get('height')} (esperado {width}x{height})")


def run_export(root, input_path, output_dir, profile=None, tenant_override=None):
    root = os.path.realpath(root)
    request = load_request(root, input_path)
    verdict = produce_carousel.run_bridge_carousel(root, input_path, profile)
    if not verdict.get('ok'):
        raise render_local.RenderInputError(verdict.get('failureCode', 'CAROUSEL_REQUEST_INVALID'),
                                            verdict.get('subject'))
    geometry = verdict.get('geometry') or {}
    width = int(geometry.get('width', 0))
    height = int(geometry.get('height', 0))
    if width <= 0 or height <= 0:
        raise render_local.RenderInputError('CAROUSEL_PROFILE_NOT_IMAGE', verdict.get('profileId'))
    tenant = render_hyperframes.resolve_tenant(root, request, tenant_override)

    tmp_parent = os.path.join(root, '.workspace', 'tmp')
    os.makedirs(tmp_parent, exist_ok=True)
    workdir_base = os.path.join(tmp_parent, 'hf001-still', verdict['requestId'], verdict['profileId'])
    staging = tempfile.mkdtemp(prefix='hf-still-staging-', dir=tmp_parent)
    try:
        names = []
        card_entries = []
        for card in verdict['cards']:
            card_workdir = os.path.join(workdir_base, card['id'])
            os.makedirs(card_workdir, exist_ok=True)
            profile_path = os.path.join(card_workdir, 'profile.compiled.json')
            write_json(profile_path, build_card_profile(verdict, card))
            png_name = f"{card['order']:02d}-{card['id']}.png"
            png_staging = os.path.join(staging, png_name)
            res = run_adapter_still(root, profile_path, card_workdir, png_staging, tenant)
            verdict_json = adapter_verdict(res)
            if res.returncode != 0 or not verdict_json or not verdict_json.get('ok'):
                failure_code = (verdict_json or {}).get('failureCode', 'ADAPTER_FAILED')
                violations = (verdict_json or {}).get('violations') or []
                detail = f'; violacoes: {", ".join(str(v.get("term") or v) for v in violations if isinstance(v, dict))}' if violations else ''
                raise build_video.DeliveryError(
                    f'{failure_code}: still do card {card["id"]} falhou (codigo {res.returncode}){detail}')
            verify_still_png(png_staging, width, height)
            names.append(png_name)
            card_entries.append({
                'order': card['order'], 'id': card['id'], 'file': png_name,
                'path': rel(root, os.path.join(output_dir, png_name)),
                'bytes': os.path.getsize(png_staging),
                'sha256': render_local.sha256_file(png_staging),
            })

        zip_name = 'stills.zip'
        zip_path = os.path.join(staging, zip_name)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(os.path.join(staging, name), arcname=name)
        names.append(zip_name)

        manifest_name = 'still-manifest.json'
        manifest = {
            'schemaVersion': 1,
            'requestId': verdict['requestId'],
            'profileId': verdict['profileId'],
            'renderer': {'adapter': ADAPTER_ID, 'engine': 'hyperframes'},
            'geometry': {'width': width, 'height': height},
            'cards': card_entries,
            'zip': {'file': zip_name, 'path': rel(root, os.path.join(output_dir, zip_name)),
                    'bytes': os.path.getsize(zip_path), 'sha256': render_local.sha256_file(zip_path)},
        }
        write_json(os.path.join(staging, manifest_name), manifest)
        names.append(manifest_name)

        index_payload = {
            'schemaVersion': 1,
            'requestId': verdict['requestId'],
            'lastAttempt': {'status': 'completed', 'manifest': rel(root, os.path.join(output_dir, manifest_name))},
            'lastValidDelivery': {'status': 'completed', 'manifest': rel(root, os.path.join(output_dir, manifest_name)),
                                  'cardCount': len(card_entries)},
        }
        os.makedirs(output_dir, exist_ok=True)
        produce_carousel._promote_set(output_dir, staging, names, index_payload)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    return {
        'status': 'completed',
        'requestId': verdict['requestId'],
        'profileId': verdict['profileId'],
        'renderer': {'adapter': ADAPTER_ID},
        'outputDir': rel(root, output_dir),
        'manifest': rel(root, os.path.join(output_dir, manifest_name)),
        'index': rel(root, os.path.join(output_dir, 'index.json')),
        'cards': [e['file'] for e in card_entries],
        'zip': rel(root, os.path.join(output_dir, zip_name)),
    }


def main(argv=None):
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, 'reconfigure'):
            try:
                _stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
    parser = argparse.ArgumentParser(description='Still estatico pelo motor HyperFrames (CarouselRequest v1, HF-001 F10)')
    parser.add_argument('--input', required=True, help='Pedido de carrossel (*.carousel-request.json)')
    parser.add_argument('--plan-only', action='store_true', help='Apenas previa (ponte de carrossel), sem render')
    parser.add_argument('--output-dir', default=None, help='Diretorio final de entrega')
    parser.add_argument('--profile', default=None, help='Sobrescreve o perfil de imagem')
    parser.add_argument('--tenant', default=None, help='Tenant (padrao: id do ProjectManifest)')
    parser.add_argument('--root', default=os.getcwd(), help='Raiz do projeto')
    parser.add_argument('--json', action='store_true', help='Emite um unico resultado JSON no stdout')
    args = parser.parse_args(argv)

    root = os.path.realpath(args.root)
    input_path = os.path.realpath(args.input)
    try:
        if not render_local.contained(root, input_path) or not os.path.isfile(input_path):
            raise render_local.InputFileError('pedido ausente ou fora da raiz do projeto')
        if not args.plan_only and not args.output_dir:
            raise render_local.InputFileError('informe --output-dir para exportar, ou use --plan-only')

        if args.plan_only:
            verdict = produce_carousel.run_bridge_carousel(root, input_path, args.profile)
            if not verdict.get('ok'):
                raise render_local.RenderInputError(verdict.get('failureCode', 'CAROUSEL_REQUEST_INVALID'),
                                                    verdict.get('subject'))
            payload = produce_carousel.build_preview(verdict)
            payload['renderer'] = {'adapter': ADAPTER_ID}
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"Previa de stills {payload['requestId']} ({payload['profileId']}):")
                g = payload['geometry']
                print(f"  Geometria: {g['width']}x{g['height']}")
                for card in payload['cards']:
                    print(f"  {card['order']:02d} {card['id']}: {card['title']}")
            return 0 if not payload['overflowCards'] else 3

        output_dir = os.path.realpath(args.output_dir)
        if not render_local.contained(root, output_dir) or output_dir == root:
            raise render_local.InputFileError('destino fora da raiz ou igual a raiz')
        payload = run_export(root, input_path, output_dir, profile=args.profile,
                             tenant_override=args.tenant)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Stills exportados: {payload['outputDir']}")
            for name in payload['cards']:
                print(f"  - {name}")
            print(f"  ZIP: {payload['zip']}")
        return 0
    except render_local.RenderInputError as exc:
        subject = f': {exc.subject}' if exc.subject else ''
        print(f'Erro: entrada invalida ({exc.code}{subject})', file=sys.stderr)
        return 3
    except render_local.InputFileError as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 2
    except build_video.DeliveryError as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f'Erro: entrada invalida ({type(exc).__name__})', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
