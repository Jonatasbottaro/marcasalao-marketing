"""Piloto tecnico local R002: agenda ficticia de tres cenas com contorno editavel.

Gera a camada de contorno como PNG RGBA separado (stdlib), reutiliza a captura
sanitizada ja versionada, exporta MP4 vertical sem audio pela via transacional
de tools/build_video.py e registra manifesto com hashes e inspecao FFprobe.
Nenhum audio, nenhum fornecedor, nenhuma rede, nenhuma publicacao.
"""

import argparse
import hashlib
import json
import math
import os
import shutil
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import srt_validate


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contained(root, path):
    root_real = os.path.realpath(root)
    target = os.path.realpath(path)
    return target == root_real or target.startswith(root_real + os.sep)


def map_rect(rect, capture_w, capture_h, frame_w, frame_h):
    """Mesma matematica scale/pad do exportador: coordenadas nativas -> frame."""
    scale = min(frame_w / capture_w, frame_h / capture_h)
    scaled_w = capture_w * scale
    scaled_h = capture_h * scale
    off_x = math.floor((frame_w - scaled_w) / 2)
    off_y = math.floor((frame_h - scaled_h) / 2)
    return (
        off_x + rect["x"] * scale,
        off_y + rect["y"] * scale,
        rect["w"] * scale,
        rect["h"] * scale,
    )


def _png_chunk(tag, payload):
    return (struct.pack(">I", len(payload)) + tag + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))


def write_outline_png(path, rect, thickness, color, radius, frame_w, frame_h):
    """Anel de retangulo arredondado com alpha antialiasado; resto transparente."""
    x, y, w, h = rect
    r = min(radius, w / 2, h / 2)
    half_t = thickness / 2.0
    cx, cy = x + w / 2.0, y + h / 2.0
    hx, hy = w / 2.0 - r, h / 2.0 - r
    x0 = max(0, int(math.floor(x - thickness)))
    y0 = max(0, int(math.floor(y - thickness)))
    x1 = min(frame_w, int(math.ceil(x + w + thickness)))
    y1 = min(frame_h, int(math.ceil(y + h + thickness)))

    rows = []
    transparent = b"\x00" * (frame_w * 4)
    for py in range(frame_h):
        if py < y0 or py >= y1:
            rows.append(b"\x00" + transparent)
            continue
        row = bytearray(frame_w * 4)
        for px in range(x0, x1):
            qx = abs(px + 0.5 - cx) - hx
            qy = abs(py + 0.5 - cy) - hy
            distance = math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - r
            coverage = max(0.0, min(1.0, half_t - abs(distance) + 0.5))
            if coverage <= 0.0:
                continue
            alpha = int(round(coverage * color[3]))
            offset = px * 4
            row[offset] = color[0]
            row[offset + 1] = color[1]
            row[offset + 2] = color[2]
            row[offset + 3] = alpha
        rows.append(b"\x00" + bytes(row))

    raw = b"".join(rows)
    ihdr = struct.pack(">IIBBBBB", frame_w, frame_h, 8, 6, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr)
           + _png_chunk(b"IDAT", zlib.compress(raw, 9)) + _png_chunk(b"IEND", b""))
    with open(path, "wb") as handle:
        handle.write(png)


def load_config(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def run_pilot(config_path, root, staging_dir, archive_dir, manifest_path, tag,
              project_root=None):
    project_root = project_root or root
    for label, path in (("config", config_path), ("staging", staging_dir),
                        ("archive", archive_dir), ("manifest", manifest_path)):
        if not contained(project_root, path):
            raise build_video.DeliveryError(f"caminho de {label} fora da raiz do projeto")
    config = load_config(config_path)
    capture = os.path.join(root, config["capture"])
    srt_src = os.path.join(root, config["srt"])
    narration_src = os.path.join(root, config["narration"])
    for label, path in (("captura", capture), ("srt", srt_src), ("narracao", narration_src)):
        if not contained(project_root, path) or not os.path.exists(path):
            raise build_video.DeliveryError(f"{label} ausente ou fora da raiz do projeto")

    fmt = config["format"]
    duration = float(config["duration"])
    outline = config["outline"]
    probe = build_video.probe_media(capture)
    cap_stream = probe["streams"][0]
    capture_w, capture_h = int(cap_stream["width"]), int(cap_stream["height"])
    rect = map_rect(outline, capture_w, capture_h, fmt["width"], fmt["height"])

    hashes_before = {}
    for name, path in (("capture", capture), ("srt", srt_src), ("narration", narration_src)):
        hashes_before[name] = sha256_file(path) if os.path.exists(path) else None

    video_name = config["videoName"]
    artifacts = {
        "video": {"staging": video_name, "dest": os.path.join(archive_dir, video_name)},
        "srt": {"staging": os.path.basename(srt_src), "dest": srt_src},
        "narration": {"staging": os.path.basename(narration_src), "dest": narration_src},
        "manifest": {"staging": "manifest.json", "dest": manifest_path},
    }

    def render(paths):
        outline_png = os.path.join(os.path.dirname(paths["video"]), "outline.png")
        write_outline_png(outline_png, rect, outline["thickness"], outline["color"],
                          outline["radius"], fmt["width"], fmt["height"])
        shutil.copyfile(srt_src, paths["srt"])
        shutil.copyfile(narration_src, paths["narration"])
        ok = build_video.build_video(
            capture, None, outline_png, paths["srt"], paths["video"],
            duration=duration, resolution=f"{fmt['width']}x{fmt['height']}", fps=fmt["fps"],
            preset=config.get("preset", "veryfast"),
            overlay_start=outline["start"], overlay_end=outline["end"],
            overlay_fade_in=outline["fadeIn"], overlay_fade_out=outline["fadeOut"],
            subtitle_style=config.get("subtitleStyle"),
        )
        if not ok:
            raise build_video.DeliveryError("renderizacao FFmpeg falhou; entrega anterior preservada")

    def validators(paths):
        errors = srt_validate.validate_srt_file(paths["srt"], duration)
        if errors:
            raise build_video.DeliveryError("SRT invalido: " + "; ".join(errors))
        with open(paths["narration"], "rb") as handle:
            narration = handle.read()
        if not narration.decode("utf-8").strip():
            raise build_video.DeliveryError("narracao vazia ou nao UTF-8")
        build_video.validate_mp4(paths["video"], fmt["width"], fmt["height"], fmt["fps"], duration)

    def write_manifest(paths):
        inspection = build_video.validate_mp4(
            paths["video"], fmt["width"], fmt["height"], fmt["fps"], duration)
        manifest = {"schemaVersion": 1, "runs": {}}
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as handle:
                manifest = json.load(handle)
        hashes_after = {name: sha256_file(paths[name]) for name in ("srt", "narration")}
        hashes_after["capture"] = hashes_before["capture"]
        manifest["runs"][tag] = {
            "config": os.path.relpath(config_path, root).replace(os.sep, "/"),
            "command": (
                "python tools/r002_pilot.py --config "
                + os.path.relpath(config_path, root).replace(os.sep, "/")
                + " --staging " + os.path.relpath(staging_dir, project_root).replace(os.sep, "/")
                + " --archive " + os.path.relpath(archive_dir, project_root).replace(os.sep, "/")
                + " --manifest " + os.path.relpath(manifest_path, root).replace(os.sep, "/")
                + " --tag " + tag
            ),
            "artifacts": {
                "video": {
                    "path": os.path.relpath(artifacts["video"]["dest"], project_root).replace(os.sep, "/"),
                    "sha256": sha256_file(paths["video"]),
                    "bytes": os.path.getsize(paths["video"]),
                    "ffprobe": inspection,
                    "versioned": False,
                    "reasonNotVersioned": ".gitignore versionado ignora *.mp4; manifesto preserva hash e comando reproduzivel",
                },
                "srt": {
                    "path": config["srt"],
                    "sha256": hashes_after["srt"],
                    "bytes": os.path.getsize(paths["srt"]),
                    "versioned": True,
                },
                "narration": {
                    "path": config["narration"],
                    "sha256": hashes_after["narration"],
                    "bytes": os.path.getsize(paths["narration"]),
                    "versioned": True,
                },
                "capture": {
                    "path": config["capture"],
                    "sha256": hashes_after["capture"],
                    "bytes": os.path.getsize(capture),
                    "width": capture_w,
                    "height": capture_h,
                    "versioned": True,
                },
            },
            "unchanged": {
                name: (hashes_before[name] is not None and hashes_before[name] == hashes_after[name])
                for name in ("capture", "srt", "narration")
            },
        }
        with open(paths["manifest"], "w", encoding="utf-8", newline="\n") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    def render_all(paths):
        render(paths)
        write_manifest(paths)

    build_video.transactional_export(staging_dir, artifacts, render_all, validators)
    return artifacts


def main(argv=None):
    parser = argparse.ArgumentParser(description="Piloto local R002 (video sem audio)")
    parser.add_argument("--config", required=True)
    parser.add_argument("--root", default=os.getcwd())
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--staging", required=True)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args(argv)
    try:
        run_pilot(args.config, args.root, args.staging, args.archive, args.manifest, args.tag,
                  project_root=args.project_root)
    except build_video.DeliveryError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro: entrada invalida ({type(exc).__name__})", file=sys.stderr)
        return 2
    print(f"Entrega {args.tag} promovida com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())