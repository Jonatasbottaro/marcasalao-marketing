"""Gerador deterministico de midia ficticia para um pedido VideoRequest v1.

Le o cadastro de midia do pedido e produz um arquivo por material no caminho
declarado (relativo a raiz): PNG para imagem, MP4 sintetico sem audio para
video. A duracao do clipe cobre a maior cena que reutiliza o material. Nenhum
dado real, nenhuma rede; stdlib + FFmpeg apenas para clipes de video. Os
arquivos sao insumos de demonstracao e devem permanecer em .workspace/.

Uso (a partir da raiz do checkout):
    python tools/make_request_media.py --input <pedido.json> [--root <raiz>]
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import make_proof_assets
import render_local


def generate_request_media(request, root, recording=False):
    if not isinstance(request, dict) or not isinstance(request.get('media'), list):
        raise render_local.InputFileError('pedido invalido: cadastro de midia ausente')
    duration_by_media = {}
    source_end_by_media = {}
    for scene in request.get('scenes', []):
        media_id = scene.get('mediaId')
        duration_ms = scene.get('durationMs', 0)
        duration_by_media[media_id] = max(duration_by_media.get(media_id, 0), duration_ms)
        source_end_ms = (scene.get('sourceStartMs') or 0) + duration_ms
        source_end_by_media[media_id] = max(source_end_by_media.get(media_id, 0), source_end_ms)

    written = []
    for index, media in enumerate(request['media'], start=1):
        declared = media['path']
        target = os.path.realpath(os.path.join(root, declared.replace('/', os.sep)))
        if not render_local.contained(root, target):
            raise render_local.InputFileError(f'caminho de midia fora da raiz: {declared}')
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if media['type'] == 'image':
            make_proof_assets.write_scene_png(target, request['id'], media['id'], index)
        elif media['type'] == 'video':
            if recording:
                required_s = source_end_by_media.get(media['id'], 0) / 1000.0
                make_proof_assets.write_recording_mp4(target, duration_s=max(12.0, required_s + 1.0))
            else:
                duration_s = max(2.0, duration_by_media.get(media['id'], 2000) / 1000.0 + 0.5)
                make_proof_assets.write_scene_mp4(target, request['id'], media['id'], index, duration_s=duration_s)
        else:
            raise render_local.InputFileError(f'tipo de midia nao suportado: {media["type"]}')
        written.append(render_local.rel(root, target))
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description='Midia ficticia para um pedido VideoRequest v1')
    parser.add_argument('--input', required=True, help='Pedido de video (*.video-request.json)')
    parser.add_argument('--root', default=os.getcwd(), help='Raiz do projeto')
    parser.add_argument('--recording', action='store_true',
                        help='Gera videos como gravacoes ficticias de tres trechos identificaveis (A/B/C), longas o bastante para os cortes pedidos')
    args = parser.parse_args(argv)
    root = os.path.realpath(args.root)
    input_path = os.path.realpath(args.input)
    if not render_local.contained(root, input_path) or not os.path.isfile(input_path):
        print('Erro: pedido ausente ou fora da raiz do projeto', file=sys.stderr)
        return 2
    try:
        with open(input_path, 'r', encoding='utf-8') as handle:
            request = json.load(handle)
        written = generate_request_media(request, root, recording=args.recording)
    except render_local.InputFileError as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 2
    except build_video.DeliveryError as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f'Erro: entrada invalida ({type(exc).__name__})', file=sys.stderr)
        return 2
    for relative in written:
        print(relative)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())