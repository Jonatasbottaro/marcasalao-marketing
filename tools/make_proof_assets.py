"""Gerador deterministico de assets ficticios para o render local de prova.

Produz um PNG por beat da timeline do CreativeExecutionPackage, com padrao
visual derivado apenas de projectId + beatId (gradiente, listras diagonais e
faixas horizontais). Nenhum dado real, nenhuma rede, nenhuma dependencia
externa: stdlib apenas. Os assets sao insumos de teste e devem permanecer em
.workspace/ (nao sao versionados).

Uso (a partir da raiz do checkout):
    python tools/make_proof_assets.py \
        --package platform/examples/execution-packages/<pacote>.json \
        --output-dir .workspace/tmp/local-render-adapter-v1/assets/<projeto>
"""

import argparse
import hashlib
import json
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import r002_pilot

WIDTH = 540
HEIGHT = 960


def scene_palette(project_id, beat_id):
    digest = hashlib.sha256(f"{project_id}/{beat_id}".encode("utf-8")).digest()
    top = (40 + digest[0] % 150, 40 + digest[1] % 150, 40 + digest[2] % 150)
    bottom = (40 + digest[3] % 150, 40 + digest[4] % 150, 40 + digest[5] % 150)
    stripe = (min(255, top[0] + 60), min(255, top[1] + 60), min(255, top[2] + 60))
    return top, bottom, stripe


def write_scene_png(path, project_id, beat_id, order):
    top, bottom, stripe = scene_palette(project_id, beat_id)
    bars = max(1, int(order))
    rows = []
    for y in range(HEIGHT):
        ratio = y / (HEIGHT - 1)
        base = tuple(int(top[c] + (bottom[c] - top[c]) * ratio) for c in range(3))
        row = bytearray()
        bar_pitch = HEIGHT // (bars + 1)
        for x in range(WIDTH):
            color = base
            if ((x + y) // 24) % 2 == 0:
                color = tuple(min(255, base[c] + (stripe[c] - top[c]) // 2) for c in range(3))
            for bar in range(1, bars + 1):
                center = bar * bar_pitch
                if abs(y - center) <= 10 and 60 <= x <= WIDTH - 60:
                    color = (235, 235, 235)
                    break
            row.extend(color)
        rows.append(b"\x00" + bytes(row))
    raw = b"".join(rows)
    ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + r002_pilot._png_chunk(b"IHDR", ihdr)
           + r002_pilot._png_chunk(b"IDAT", zlib.compress(raw, 9))
           + r002_pilot._png_chunk(b"IEND", b""))
    with open(path, "wb") as handle:
        handle.write(png)


def generate_assets(package_path, output_dir, root):
    if not r002_pilot.contained(root, output_dir):
        raise r002_pilot.build_video.DeliveryError("diretorio de saida fora da raiz do projeto")
    with open(package_path, "r", encoding="utf-8") as handle:
        package = json.load(handle)
    project_id = package["projectId"]
    os.makedirs(output_dir, exist_ok=True)
    written = []
    for step in package["timeline"]:
        target = os.path.join(output_dir, f"{step['beatId']}.png")
        write_scene_png(target, project_id, step["beatId"], step["order"])
        written.append(os.path.relpath(target, root).replace(os.sep, "/"))
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description="Assets ficticios para o render local de prova")
    parser.add_argument("--package", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--root", default=os.getcwd())
    args = parser.parse_args(argv)
    try:
        written = generate_assets(args.package, args.output_dir, args.root)
    except r002_pilot.build_video.DeliveryError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro: entrada invalida ({type(exc).__name__})", file=sys.stderr)
        return 2
    for relative in written:
        print(relative)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
