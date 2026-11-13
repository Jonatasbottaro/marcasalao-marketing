"""Producao local de carrossel de imagens (R003) a partir de CarouselRequest v1.

Uso (a partir da raiz do checkout):
  python tools/produce_carousel.py --input <pedido.carousel-request.json> --plan-only --json
  python tools/produce_carousel.py --input <pedido.carousel-request.json> --output-dir <entrega> --json

Responsabilidades:
- Previa (--plan-only): resolve o perfil de imagem pelo catalogo + allowlist do
  projeto (ponte Node), informa ordem, geometria e erros/overflow por card, sem
  FFmpeg e sem gravacao.
- Exportacao: renderiza JPEGs 1080x1080 (layout reutilizavel com margens,
  contraste e quebra de linha; FFmpeg decodifica/escala a midia e converte
  PNG->JPEG), com nomes numerados (01-capa.jpg, ...), ZIP na mesma ordem e
  manifesto (id do pedido, dimensoes, caminhos relativos, tamanhos, SHA-256).
- Entrega transacional: promove o conjunto sob lock com backup; falha preserva a
  ultima entrega valida; remover card e reexportar reflete a nova ordem no
  conjunto ativo e no ZIP. Indice separa lastAttempt de lastValidDelivery.

Exit codes: 0 sucesso; 1 falha de render/asset/promocao; 2 uso/caminho/JSON;
3 pedido/perfil invalido ou texto excedendo a area (card indicado).
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
import carousel_layout
import render_local


def write_json(path, value):
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def rel(root, path):
    return render_local.rel(root, path)


def run_bridge_carousel(root, input_path, profile=None):
    node = shutil.which('node')
    if not node:
        raise render_local.InputFileError('node nao encontrado no PATH')
    dist = os.path.join(root, 'platform', 'dist', 'src', 'validate-carousel-request.js')
    if not os.path.isfile(dist):
        raise render_local.InputFileError('build da platform ausente; execute npm run build em platform/')
    cmd = [node, os.path.join(root, 'tools', 'render_bridge.mjs'),
           '--carousel-request', input_path, '--root', root]
    if profile:
        cmd.extend(['--profile', profile])
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=render_local.BRIDGE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise build_video.DeliveryError('ponte de carrossel excedeu o tempo limite')
    if res.returncode == 2:
        raise render_local.InputFileError('pedido de carrossel ilegivel ou JSON invalido')
    if res.returncode not in (0, 3):
        raise build_video.DeliveryError('ponte de carrossel falhou de forma inesperada')
    try:
        return json.loads(res.stdout)
    except ValueError:
        raise build_video.DeliveryError('veredito da ponte de carrossel ilegivel')


def build_preview(verdict):
    cards = []
    overflow_cards = []
    for card in verdict['cards']:
        measured = carousel_layout.measure_card(card)
        entry = dict(card)
        entry['overflow'] = measured['overflow']
        entry['totalHeight'] = measured['totalHeight']
        entry['availableHeight'] = measured['availableHeight']
        cards.append(entry)
        if measured['overflow']:
            overflow_cards.append(card['id'])
    return {
        'status': 'preview',
        'requestId': verdict['requestId'],
        'profileId': verdict['profileId'],
        'geometry': verdict['geometry'],
        'cards': cards,
        'overflowCards': overflow_cards,
        'warnings': verdict.get('warnings', []),
    }


def _media_rgb(ffmpeg, media_abs, width, height, staging, card_id):
    raw_path = os.path.join(staging, f'.media-{card_id}.raw')
    cmd = [ffmpeg, '-y', '-i', media_abs, '-vf', f'scale={width}:{height}',
           '-f', 'rawvideo', '-pix_fmt', 'rgb24', raw_path]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=render_local.RENDER_TIMEOUT_SECONDS)
    if res.returncode != 0:
        raise build_video.DeliveryError(f'ASSET_CORRUPTED: {card_id} (falha ao decodificar midia)')
    with open(raw_path, 'rb') as handle:
        data = handle.read()
    os.remove(raw_path)
    if len(data) != width * height * 3:
        raise build_video.DeliveryError(f'ASSET_CORRUPTED: {card_id} (bytes inesperados)')
    return data


def _promote_set(output_dir, staging, names, index_payload):
    """Promove o conjunto completo sob lock; falha restaura a entrega anterior."""
    lock = render_local.acquire_promotion_lock(output_dir)
    backup_dir = os.path.join(staging, '.backup')
    os.makedirs(backup_dir, exist_ok=True)
    existing = [n for n in os.listdir(output_dir)
                if os.path.isfile(os.path.join(output_dir, n)) and n != render_local.PROMOTION_LOCK_NAME]
    try:
        for name in existing:
            shutil.copyfile(os.path.join(output_dir, name), os.path.join(backup_dir, name))
        for name in existing:
            os.remove(os.path.join(output_dir, name))
        for name in names:
            shutil.copyfile(os.path.join(staging, name), os.path.join(output_dir, name))
        fd, tmp = tempfile.mkstemp(prefix='.index-', suffix='.tmp', dir=output_dir)
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(index_payload, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(tmp, os.path.join(output_dir, 'index.json'))
    except OSError:
        for name in existing:
            src = os.path.join(backup_dir, name)
            if os.path.isfile(src):
                shutil.copyfile(src, os.path.join(output_dir, name))
        raise
    finally:
        if os.path.exists(lock):
            os.remove(lock)
    shutil.rmtree(backup_dir, ignore_errors=True)


def run_export(root, input_path, output_dir, profile=None):
    root = os.path.realpath(root)
    verdict = run_bridge_carousel(root, input_path, profile)
    if not verdict.get('ok'):
        raise render_local.RenderInputError(verdict.get('failureCode', 'CAROUSEL_REQUEST_INVALID'),
                                            verdict.get('subject'))
    preview = build_preview(verdict)
    if preview['overflowCards']:
        raise render_local.RenderInputError('CAROUSEL_TEXT_OVERFLOW', ','.join(preview['overflowCards']))

    width = verdict['geometry']['width']
    height = verdict['geometry']['height']
    render_local.ensure_video_tools(root)
    ffmpeg = build_video.get_ffmpeg()

    parent = os.path.join(root, '.workspace', 'tmp')
    os.makedirs(parent, exist_ok=True)
    staging = tempfile.mkdtemp(prefix='carousel-staging-', dir=parent)
    try:
        names = []
        card_entries = []
        for card in verdict['cards']:
            media_rgb = None
            if card['mediaPath']:
                media_abs = os.path.realpath(os.path.join(root, card['mediaPath']))
                if not render_local.contained(root, media_abs) or not os.path.isfile(media_abs):
                    raise build_video.DeliveryError(f"ASSET_MISSING: {card['id']} ({card['mediaPath']})")
                media_rgb = _media_rgb(ffmpeg, media_abs, width, height, staging, card['id'])
            rgb, overflow = carousel_layout.render_card(card, media_rgb, width, height)
            if overflow:
                raise render_local.RenderInputError('CAROUSEL_TEXT_OVERFLOW', card['id'])
            name = f"{card['order']:02d}-{card['id']}.jpg"
            png_path = os.path.join(staging, f'.{card["id"]}.png')
            with open(png_path, 'wb') as handle:
                handle.write(carousel_layout.encode_png(width, height, rgb))
            jpg_path = os.path.join(staging, name)
            res = subprocess.run([ffmpeg, '-y', '-i', png_path, '-q:v', '2', jpg_path],
                                 capture_output=True, text=True, timeout=render_local.RENDER_TIMEOUT_SECONDS)
            os.remove(png_path)
            if res.returncode != 0:
                raise build_video.DeliveryError(f'falha ao codificar JPEG do card {card["id"]}')
            names.append(name)
            card_entries.append({
                'order': card['order'], 'id': card['id'], 'file': name,
                'path': rel(root, os.path.join(output_dir, name)),
                'bytes': os.path.getsize(jpg_path),
                'sha256': render_local.sha256_file(jpg_path),
            })

        zip_name = 'carousel.zip'
        zip_path = os.path.join(staging, zip_name)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(os.path.join(staging, name), arcname=name)
        names.append(zip_name)

        manifest_name = 'carousel-manifest.json'
        manifest = {
            'schemaVersion': 1,
            'requestId': verdict['requestId'],
            'profileId': verdict['profileId'],
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
        _promote_set(output_dir, staging, names, index_payload)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    return {
        'status': 'completed',
        'requestId': verdict['requestId'],
        'profileId': verdict['profileId'],
        'outputDir': rel(root, output_dir),
        'manifest': rel(root, os.path.join(output_dir, manifest_name)),
        'index': rel(root, os.path.join(output_dir, 'index.json')),
        'cards': [e['file'] for e in card_entries],
        'zip': rel(root, os.path.join(output_dir, zip_name)),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='Producao local de carrossel (CarouselRequest v1)')
    parser.add_argument('--input', required=True, help='Pedido de carrossel (*.carousel-request.json)')
    parser.add_argument('--plan-only', action='store_true', help='Apenas previa, sem FFmpeg nem gravacao')
    parser.add_argument('--output-dir', default=None, help='Diretorio final de entrega')
    parser.add_argument('--profile', default=None, help='Sobrescreve o perfil de imagem')
    parser.add_argument('--root', default=os.getcwd(), help='Raiz do projeto')
    parser.add_argument('--json', action='store_true', help='Emite um unico resultado JSON no stdout')
    args = parser.parse_args(argv)

    root = os.path.realpath(args.root)
    input_path = os.path.realpath(args.input)
    if not render_local.contained(root, input_path) or not os.path.isfile(input_path):
        print('Erro: pedido ausente ou fora da raiz do projeto', file=sys.stderr)
        return 2
    if not args.plan_only and not args.output_dir:
        print('Erro: informe --output-dir para exportar, ou use --plan-only', file=sys.stderr)
        return 2

    try:
        if args.plan_only:
            verdict = run_bridge_carousel(root, input_path, args.profile)
            if not verdict.get('ok'):
                raise render_local.RenderInputError(verdict.get('failureCode', 'CAROUSEL_REQUEST_INVALID'),
                                                    verdict.get('subject'))
            payload = build_preview(verdict)
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"Previa do carrossel {payload['requestId']} ({payload['profileId']}):")
                g = payload['geometry']
                print(f"  Geometria: {g['width']}x{g['height']}")
                for card in payload['cards']:
                    flag = ' [EXCEDE AREA]' if card['overflow'] else ''
                    print(f"  {card['order']:02d} {card['id']}: {card['title']}{flag}")
                if payload['overflowCards']:
                    print('  Cards que precisam de ajuste: ' + ', '.join(payload['overflowCards']))
            return 0 if not payload['overflowCards'] else 3

        output_dir = os.path.realpath(args.output_dir)
        if not render_local.contained(root, output_dir) or output_dir == root:
            raise render_local.InputFileError('destino fora da raiz ou igual a raiz')
        payload = run_export(root, input_path, output_dir, args.profile)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Carrossel exportado: {payload['outputDir']}")
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