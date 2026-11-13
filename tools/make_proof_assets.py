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
import subprocess
import sys
import tempfile
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


def write_scene_mp4(path, project_id, beat_id, order, duration_s=6.0, fps=30):
    """Gera um clipe MP4 sintetico sem audio (H.264/yuv420p) a partir da cena."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, tmp_png = tempfile.mkstemp(prefix=".proof-frame-", suffix=".png", dir=parent)
    os.close(fd)
    try:
        write_scene_png(tmp_png, project_id, beat_id, order)
        cmd = [
            r002_pilot.build_video.get_ffmpeg(),
            "-y",
            "-loop",
            "1",
            "-framerate",
            str(fps),
            "-t",
            f"{duration_s:.3f}",
            "-i",
            tmp_png,
            "-an",
            "-vf",
            "scale=1080:1920:flags=bilinear,setsar=1",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps),
            path,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            raise r002_pilot.build_video.DeliveryError(
                f"falha ao gerar clipe mp4 sintetico para {beat_id}: {res.stderr[-240:]}"
            )
    finally:
        if os.path.exists(tmp_png):
            os.remove(tmp_png)


def generate_assets(package_path, output_dir, root, case_path=None):
    if not r002_pilot.contained(root, output_dir):
        raise r002_pilot.build_video.DeliveryError("diretorio de saida fora da raiz do projeto")
    if case_path:
        with open(case_path, "r", encoding="utf-8") as handle:
            case_data = json.load(handle)
        case_dir = os.path.dirname(case_path)
        proj_file = os.path.normpath(os.path.join(case_dir, case_data["project"]))
        beat_file = os.path.normpath(os.path.join(case_dir, case_data["beatPlan"]))
        with open(proj_file, "r", encoding="utf-8") as handle:
            project_data = json.load(handle)
        with open(beat_file, "r", encoding="utf-8") as handle:
            beat_data = json.load(handle)
        project_id = project_data["id"]
        beats = [{"beatId": b["id"], "order": b["order"]} for b in beat_data["beats"]]
    else:
        with open(package_path, "r", encoding="utf-8") as handle:
            package = json.load(handle)
        project_id = package["projectId"]
        beats = [{"beatId": step["beatId"], "order": step["order"]} for step in package["timeline"]]

    os.makedirs(output_dir, exist_ok=True)
    written = []
    for step in beats:
        target = os.path.join(output_dir, f"{step['beatId']}.png")
        write_scene_png(target, project_id, step["beatId"], step["order"])
        written.append(os.path.relpath(target, root).replace(os.sep, "/"))
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description="Assets ficticios para o render local de prova")
    parser.add_argument("--package", default=None)
    parser.add_argument("--case", default=None)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--root", default=os.getcwd())
    args = parser.parse_args(argv)
    if not args.package and not args.case:
        print("Erro: informe --case ou --package", file=sys.stderr)
        return 2
    try:
        written = generate_assets(args.package, args.output_dir, args.root, case_path=args.case)
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
