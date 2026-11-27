"""Producao v3 (Qualidade Criativa) do PILOTO-OPERACIONAL-001-V3.

Gera post 4:5, carrossel (4 cards) e reel vertical VIDEO CLEAN com aparencia
comercial: tipografia profissional (libass/ASS, fonte do brand-kit), identidade
visual do Marca Salao e capturas REAIS autorizadas da agenda.

Nao cria um novo editor: reaproveita o FFmpeg portatil, o brand-kit e o catalogo
de midias do projeto. A composicao usa primitivas de canvas ja existentes
(`ns002_pilot`) e o motor de texto comercial (`commercial_text`).

Uso:
  python tools/produce_v3.py --piece all --outdir .workspace/archives/operacao-resultado-26/delivery-v3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import carousel_layout
import commercial_text as ct
import ns002_pilot
import render_local

CAPTURES_REL = os.path.join("00-briefings", "campanhas", "NS-001", "capturas", "2026-11-05")
CAP_DAY = "01-agenda-visao-dia.png"
CAP_WEEK = "04-agenda-visao-semana.png"
CAP_STATUS = "03-agenda-status-confirmado.png"
CAP_MODAL = "02-agenda-modal-detalhes.png"
CAP_MOBILE_DAY = "10-agenda-mobile-dia.png"
CAP_MOBILE_WEEK = "11-agenda-mobile-semana.png"
CAP_MOBILE_GRID = "12-agenda-mobile-semana-grade.png"


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fs(path: str) -> str:
    return render_local.fs_path(os.path.normpath(str(path)))


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(_fs(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _ffmpeg(root: str) -> str:
    render_local.ensure_video_tools(root)
    return build_video.get_ffmpeg()


def _rgb(hex_value: str, fallback=(255, 255, 255)) -> tuple[int, int, int]:
    t = str(hex_value or "").strip().lstrip("#")
    if len(t) == 6:
        try:
            return (int(t[0:2], 16), int(t[2:4], 16), int(t[4:6], 16))
        except ValueError:
            pass
    return fallback


def load_brand(root: str) -> dict:
    with open(_fs(os.path.join(root, "tenants", "marca-salao", "brand-kit.json")), "r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Canvas RGB e PNG RGBA (rounded)
# ---------------------------------------------------------------------------
def _fill(canvas: bytearray, w: int, h: int, x0: int, y0: int, x1: int, y1: int, rgb) -> None:
    x0 = max(0, x0); y0 = max(0, y0); x1 = min(w, x1); y1 = min(h, y1)
    color = bytes(rgb)
    for y in range(y0, y1):
        start = (y * w + x0) * 3
        canvas[start:start + (x1 - x0) * 3] = color * (x1 - x0)


def _brand_background(w: int, h: int, brand: dict) -> bytearray:
    palette = brand.get("palette", {}).get("rgb", {})
    top = tuple(palette.get("backgroundTop", [18, 22, 32]))
    bottom = tuple(palette.get("backgroundBottom", [28, 36, 52]))
    canvas = ns002_pilot._base_gradient(w, h, top, bottom)
    accent = tuple(palette.get("primaryAccent", [245, 193, 7]))
    _fill(canvas, w, h, 0, 0, w, 10, accent)  # barra de acento no topo
    return canvas


def _encode_png_rgba(w: int, h: int, rgba: bytearray) -> bytes:
    raw = b"".join(b"\x00" + bytes(rgba[y * w * 4:(y + 1) * w * 4]) for y in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def _rounded_panel_png(w: int, h: int, radius: int, fill_rgb, border_rgb=None, border_w: int = 0) -> bytes:
    rgba = bytearray(w * h * 4)
    f = tuple(fill_rgb)
    b = tuple(border_rgb) if border_rgb else None
    r2 = radius * radius
    for y in range(h):
        for x in range(w):
            # distancia aos cantos arredondados
            inside = True
            cx = x; cy = y
            if x < radius and y < radius:
                inside = (radius - x) ** 2 + (radius - y) ** 2 <= r2
            elif x >= w - radius and y < radius:
                inside = (x - (w - radius - 1)) ** 2 + (radius - y) ** 2 <= r2
            elif x < radius and y >= h - radius:
                inside = (radius - x) ** 2 + (y - (h - radius - 1)) ** 2 <= r2
            elif x >= w - radius and y >= h - radius:
                inside = (x - (w - radius - 1)) ** 2 + (y - (h - radius - 1)) ** 2 <= r2
            if not inside:
                continue
            color = f
            if b is not None and border_w > 0:
                edge = (x < border_w or y < border_w or x >= w - border_w or y >= h - border_w)
                # mantem os cantos arredondados tambem na borda
                if edge:
                    color = b
            i = (y * w + x) * 4
            rgba[i:i + 4] = bytes((color[0], color[1], color[2], 255))
    return _encode_png_rgba(w, h, rgba)


# ---------------------------------------------------------------------------
# Composicao com FFmpeg: fundo + captura em moldura + texto ASS
# ---------------------------------------------------------------------------
def _render(base_png: str, caps: list[dict], ass_path: str,
            out_path: str, ffmpeg: str, w: int, h: int) -> None:
    """caps: lista de {cap, target_w, pad(bool), x(expr), y(expr)}."""
    inputs = ["-i", base_png]
    filters = []
    prev = "[0:v]"
    for idx, c in enumerate(caps, start=1):
        inputs += ["-i", c["cap"]]
        chain = f"[{idx}:v]scale={int(c['target_w'])}:-1"
        if c.get("pad"):
            chain += ",pad=iw+16:ih+16:8:8:color=0x4F8CFF"
        chain += f"[c{idx}]"
        filters.append(chain)
        x = c.get("x") or "(W-w)/2"
        y = c.get("y") or "(H-h)/2"
        filters.append(f"{prev}[c{idx}]overlay={x}:{y}[o{idx}]")
        prev = f"[o{idx}]"
    filters.append(f"{prev}ass={ct._ass_filter_arg(ass_path)}[vout]")
    graph = ";".join(filters)
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", *inputs,
           "-filter_complex", graph, "-map", "[vout]", "-frames:v", "1", "-q:v", "2", out_path]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=render_local.RENDER_TIMEOUT_SECONDS)
    if res.returncode != 0:
        raise build_video.DeliveryError(f"falha ao compor imagem: {res.stderr.strip()[:400]}")


# ---------------------------------------------------------------------------
# Pecas
# ---------------------------------------------------------------------------
def _post_styles(brand: dict) -> list[dict]:
    p = brand["palette"]
    return [
        {"name": "Brand", "font": "Arial", "size": 30, "color": p["primary"],
         "bold": True, "alignment": ct.AN_TOP_LEFT, "marginL": 72, "marginR": 72, "marginV": 60, "spacing": 3},
        {"name": "Title", "font": "Arial", "size": 88, "color": p["textPrimary"],
         "bold": True, "alignment": ct.AN_TOP_LEFT, "marginL": 72, "marginR": 72, "marginV": 132},
        {"name": "Sub", "font": "Arial", "size": 42, "color": p["textMuted"],
         "bold": False, "alignment": ct.AN_TOP_LEFT, "marginL": 72, "marginR": 72, "marginV": 244},
        {"name": "Cta", "font": "Arial", "size": 50, "color": p["accent"],
         "bold": True, "alignment": ct.AN_BOT_CENTER, "marginL": 72, "marginR": 72, "marginV": 70},
    ]


def compose_post(root: str, brand: dict, out_path: str, staging: str) -> None:
    ffmpeg = _ffmpeg(root)
    w, h = 1080, 1350
    bg = _brand_background(w, h, brand)
    bg_path = os.path.join(staging, ".post-bg.png")
    render_local.write_bytes(_fs(bg_path), carousel_layout.encode_png(w, h, bg))

    ass = ct.build_ass(w, h, _post_styles(brand), [
        {"style": "Brand", "text": "MARCA SALAO | AGENDAMENTO ONLINE"},
        {"style": "Title", "text": "Sua agenda, mais organizada."},
        {"style": "Sub", "text": "Visualize horarios e acompanhe os atendimentos em um so lugar."},
        {"style": "Cta", "text": "Conheca o Marca Salao"},
    ])
    ass_path = os.path.join(staging, ".post.ass")
    render_local.write_text_lf(_fs(ass_path), ass)

    cap = os.path.join(root, CAPTURES_REL, CAP_MOBILE_DAY)
    _render(bg_path, [{"cap": cap, "target_w": 430, "pad": True, "y": "344"}],
            ass_path, out_path, ffmpeg, w, h)


def _carousel_styles(brand: dict) -> list[dict]:
    p = brand["palette"]
    return [
        {"name": "Badge", "font": "Arial", "size": 30, "color": p["secondary"],
         "bold": True, "alignment": ct.AN_TOP_LEFT, "marginL": 76, "marginR": 76, "marginV": 56, "spacing": 2},
        {"name": "Title", "font": "Arial", "size": 72, "color": p["textPrimary"],
         "bold": True, "alignment": ct.AN_TOP_LEFT, "marginL": 76, "marginR": 76, "marginV": 118},
        {"name": "Body", "font": "Arial", "size": 40, "color": p["textMuted"],
         "bold": False, "alignment": ct.AN_TOP_LEFT, "marginL": 76, "marginR": 76, "marginV": 296},
        {"name": "Cta", "font": "Arial", "size": 54, "color": p["accent"],
         "bold": True, "alignment": ct.AN_BOT_CENTER, "marginL": 76, "marginR": 76, "marginV": 76},
        {"name": "Foot", "font": "Arial", "size": 26, "color": p["textMuted"],
         "bold": False, "alignment": ct.AN_BOT_LEFT, "marginL": 76, "marginR": 76, "marginV": 28},
    ]


def compose_carousel(root: str, brand: dict, out_dir: str, staging: str) -> list[str]:
    ffmpeg = _ffmpeg(root)
    w, h = 1080, 1080
    styles = _carousel_styles(brand)
    capdir = os.path.join(root, CAPTURES_REL)
    cards = [
        ("01-capa", "SUA ROTINA | 1/4", "Sua rotina comeca com uma agenda organizada.",
         "Gestao de salao, do agendamento ao atendimento.", CAP_MOBILE_DAY, 300, True, None, "360"),
        ("02-horarios", "HORARIOS | 2/4", "Veja os horarios do dia com mais clareza.",
         "Visao do dia e da semana em uma so tela.", CAP_MOBILE_WEEK, 300, True, None, "360"),
        ("03-atendimentos", "ATENDIMENTOS | 3/4", "Acompanhe cada atendimento.",
         "Visualize e atualize os status do dia.", CAP_STATUS, 760, True, None, "430"),
        ("04-cta", "CONHECA | 4/4", "Conheca o Marca Salao.",
         "Explore uma maneira mais pratica de organizar a agenda.", None, 0, False, None, None),
    ]
    names = []
    for cid, badge, title, caption, cap, tw, pad, x, y in cards:
        bg = _brand_background(w, h, brand)
        bg_path = os.path.join(staging, f".car-{cid}-bg.png")
        render_local.write_bytes(_fs(bg_path), carousel_layout.encode_png(w, h, bg))
        events = [
            {"style": "Badge", "text": badge},
            {"style": "Title", "text": title},
            {"style": "Body", "text": caption},
            {"style": "Foot", "text": "MARCA SALAO - marcasalao.com.br"},
        ]
        if cid == "04-cta":
            events.append({"style": "Cta", "text": "Conheca o Marca Salao"})
        ass_path = os.path.join(staging, f".car-{cid}.ass")
        render_local.write_text_lf(_fs(ass_path), ct.build_ass(w, h, styles, events))
        caps = []
        if cap:
            caps.append({"cap": os.path.join(capdir, cap), "target_w": tw, "pad": pad, "x": x, "y": y})
        out_path = os.path.join(out_dir, f"{cid}.jpg")
        _render(bg_path, caps, ass_path, out_path, ffmpeg, w, h)
        names.append(f"{cid}.jpg")
    return names


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Producao v3 Marca Salao")
    parser.add_argument("--piece", default="all", choices=["post", "carousel", "all"])
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--root", default=repo_root())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = os.path.realpath(args.root)
    outdir = os.path.realpath(args.outdir)
    if not render_local.contained(root, outdir) or outdir == root:
        print("Erro: destino fora da raiz ou igual a raiz", file=sys.stderr)
        return 2
    brand = load_brand(root)
    os.makedirs(_fs(outdir), exist_ok=True)
    parent = os.path.join(root, ".workspace", "tmp")
    os.makedirs(_fs(parent), exist_ok=True)
    staging = tempfile.mkdtemp(prefix="v3-staging-", dir=parent)
    result = {"status": "completed", "post": None, "carousel": []}
    try:
        if args.piece in ("post", "all"):
            post_dir = os.path.join(outdir, "post-45")
            os.makedirs(_fs(post_dir), exist_ok=True)
            post_path = os.path.join(post_dir, "01-capa.jpg")
            compose_post(root, brand, post_path, staging)
            result["post"] = {"path": render_local.rel(root, post_path),
                              "bytes": os.path.getsize(_fs(post_path)),
                              "sha256": _sha256_file(post_path)}
        if args.piece in ("carousel", "all"):
            car_dir = os.path.join(outdir, "carousel")
            os.makedirs(_fs(car_dir), exist_ok=True)
            names = compose_carousel(root, brand, car_dir, staging)
            result["carousel"] = [{"file": n, "path": render_local.rel(root, os.path.join(car_dir, n)),
                                   "sha256": _sha256_file(os.path.join(car_dir, n))} for n in names]
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("v3 gerado em", render_local.rel(root, outdir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
