"""Producao do reel vertical v3 (1080x1920) do PILOTO-OPERACIONAL-001-V3.

VIDEO CLEAN (MKT-VIDEO-002): o video sai SEM faixa de audio (`-an`), sem narracao
embutida. As legendas de tela sao curtas e sincronizadas (motor ASS/libass, mesma
tipografia comercial das pecas estaticas). A narracao falada e entregue SEPARADA
em `04-legendas/narracao-reel.txt`; a direcao de cenas vai em `direcao-de-cenas.md`
e as legendas cronometradas em `legendas.srt`.

Reaproveita FFmpeg portatil, brand-kit e capturas reais autorizadas; nao cria um
novo editor.

Uso:
  python tools/produce_v3_reel.py --outdir <entrega>/03-reel \
      --legendas-dir <entrega>/04-legendas --root <RAIZ>
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import carousel_layout
import commercial_text as ct
import produce_v3 as p3
import render_local

W, H = 1080, 1920
FPS = 30

# Cenas v3: (id, inicio_s, duracao_s, titulo_tela, legenda, narracao, captura, tw)
SCENES = [
    {
        "id": "01-hook", "start": 0.0, "dur": 4.0,
        "title": "Sua agenda, em um so lugar.",
        "sub": "Visualize os atendimentos e acompanhe o dia em uma so tela.",
        "caption": "Sua agenda, em um so lugar.",
        "narration": "Sua agenda em um so lugar, sem depender de anotacoes espalhadas.",
        "capture": None, "tw": 0,
    },
    {
        "id": "02-visoes", "start": 4.0, "dur": 6.0,
        "title": "Dia, semana e mes.",
        "sub": "O mesmo registro, visto por dia, semana ou mes.",
        "caption": "O mesmo registro, por dia, semana ou mes.",
        "narration": "Veja o dia, a semana e o mes na mesma tela.",
        "capture": p3.CAP_MOBILE_DAY, "tw": 560,
    },
    {
        "id": "03-filtros", "start": 10.0, "dur": 6.0,
        "title": "Filtre e acompanhe.",
        "sub": "Filtre por profissional ou status e atualize cada atendimento.",
        "caption": "Filtre por profissional ou status.",
        "narration": "Filtre por profissional ou status e acompanhe cada atendimento.",
        "capture": p3.CAP_STATUS, "tw": 840,
    },
    {
        "id": "04-cta", "start": 16.0, "dur": 4.0,
        "title": "Conheca o Marca Salao.",
        "sub": "marcasalao.com.br",
        "caption": "Conheca o Marca Salao.",
        "narration": "Conheca o Marca Salao em marcasalao ponto com ponto br.",
        "capture": None, "tw": 0,
    },
]


def _styles(brand: dict) -> list[dict]:
    p = brand["palette"]
    return [
        {"name": "Brand", "font": "Arial", "size": 34, "color": p["primary"],
         "bold": True, "alignment": ct.AN_TOP_CENTER, "marginL": 80, "marginR": 80,
         "marginV": 150, "spacing": 4},
        {"name": "Title", "font": "Arial", "size": 92, "color": p["textPrimary"],
         "bold": True, "alignment": ct.AN_MID_CENTER, "marginL": 90, "marginR": 90,
         "marginV": 0},
        {"name": "Sub", "font": "Arial", "size": 42, "color": p["textMuted"],
         "bold": False, "alignment": ct.AN_MID_CENTER, "marginL": 90, "marginR": 90,
         "marginV": 0},
        {"name": "Caption", "font": "Arial", "size": 46, "color": p["textPrimary"],
         "bold": True, "alignment": ct.AN_BOT_CENTER, "marginL": 80, "marginR": 80,
         "marginV": 96, "outline": 3, "outlineColor": "#0E121C"},
        {"name": "Url", "font": "Arial", "size": 40, "color": p["secondary"],
         "bold": True, "alignment": ct.AN_BOT_CENTER, "marginL": 80, "marginR": 80,
         "marginV": 96},
    ]


def _scene_image(root: str, scene: dict, brand: dict, out_png: str, staging: str, ffmpeg: str) -> None:
    bg = p3._brand_background(W, H, brand)
    bg_path = os.path.join(staging, f".{scene['id']}-bg.png")
    render_local.write_bytes(p3._fs(bg_path), carousel_layout.encode_png(W, H, bg))
    events = [{"style": "Brand", "text": "MARCA SALAO | AGENDAMENTO ONLINE"}]
    if scene["capture"]:
        events.append({"style": "Caption", "text": scene["caption"]})
    elif scene["id"] == "04-cta":
        events.append({"style": "Title", "text": scene["title"]})
        events.append({"style": "Url", "text": scene["sub"]})
    else:
        events.append({"style": "Title", "text": scene["title"]})
        events.append({"style": "Sub", "text": scene["sub"]})
    ass_path = os.path.join(staging, f".{scene['id']}.ass")
    render_local.write_text_lf(p3._fs(ass_path), ct.build_ass(W, H, _styles(brand), events))
    caps = []
    if scene["capture"]:
        caps.append({"cap": os.path.join(root, p3.CAPTURES_REL, scene["capture"]),
                     "target_w": scene["tw"], "pad": True, "y": "560"})
    p3._render(bg_path, caps, ass_path, out_png, ffmpeg, W, H)


def _encode_scene(png: str, dur: float, out_mp4: str, ffmpeg: str) -> None:
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
           "-loop", "1", "-t", f"{dur:.3f}", "-i", png,
           "-r", str(FPS), "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "medium",
           "-crf", "18", "-an", out_mp4]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=render_local.RENDER_TIMEOUT_SECONDS)
    if res.returncode != 0:
        raise build_video.DeliveryError(f"falha ao codificar cena: {res.stderr.strip()[:400]}")


def _srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt() -> str:
    blocks = []
    for i, sc in enumerate(SCENES, start=1):
        start = sc["start"]
        end = sc["start"] + sc["dur"]
        blocks.append(f"{i}\n{_srt_time(start)} --> {_srt_time(end)}\n{sc['caption']}\n")
    return "\n".join(blocks)


def build_narration() -> str:
    lines = ["Roteiro de narracao - PILOTO-OPERACIONAL-001-V3 (reel vertical).",
             "Video sem audio; texto para ferramenta externa, organizado por cena e tempos.",
             ""]
    for sc in SCENES:
        start = sc["start"]
        end = sc["start"] + sc["dur"]
        lines.append(f"[{_srt_time(start)} --> {_srt_time(end)}] {sc['id']}")
        lines.append(sc["narration"])
        lines.append("")
    return "\n".join(lines)


def build_direction() -> str:
    lines = ["# Direcao de cenas - PILOTO-OPERACIONAL-001-V3 (reel vertical 1080x1920)",
             "",
             "Documento de direcao (o que mostrar em cada cena). NAO e a narracao falada.",
             "A narracao esta em `04-legendas/narracao-reel.txt`.",
             ""]
    for sc in SCENES:
        lines.append(f"## {sc['id']} ({sc['dur']:.0f}s)")
        lines.append(f"- Tela: {sc['title']}")
        lines.append(f"- Legenda visivel: {sc['caption']}")
        src = "fundo de identidade da marca (sem tela de produto)" if not sc["capture"] \
            else f"captura real autorizada da agenda: {sc['capture']}"
        lines.append(f"- Midia: {src}")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Reel v3 Marca Salao (VIDEO CLEAN)")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--legendas-dir", required=True)
    ap.add_argument("--root", default=p3.repo_root())
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = os.path.realpath(args.root)
    outdir = os.path.realpath(args.outdir)
    legdir = os.path.realpath(args.legendas_dir)
    for d in (outdir, legdir):
        if not render_local.contained(root, d) or d == root:
            print("Erro: destino fora da raiz ou igual a raiz", file=sys.stderr)
            return 2
    brand = p3.load_brand(root)
    os.makedirs(p3._fs(outdir), exist_ok=True)
    os.makedirs(p3._fs(legdir), exist_ok=True)
    parent = os.path.join(root, ".workspace", "tmp")
    os.makedirs(p3._fs(parent), exist_ok=True)
    staging = tempfile.mkdtemp(prefix="reel-v3-", dir=parent)
    ffmpeg = p3._ffmpeg(root)
    try:
        scene_mp4s = []
        for sc in SCENES:
            png = os.path.join(staging, f"{sc['id']}.png")
            _scene_image(root, sc, brand, png, staging, ffmpeg)
            mp4 = os.path.join(staging, f"{sc['id']}.mp4")
            _encode_scene(png, sc["dur"], mp4, ffmpeg)
            scene_mp4s.append(mp4)
        listing = os.path.join(staging, "concat.txt")
        with open(p3._fs(listing), "w", encoding="utf-8", newline="\n") as fh:
            for m in scene_mp4s:
                fh.write(f"file '{m.replace(os.sep, '/')}'\n")
        reel = os.path.join(outdir, "reel-instagram-9x16.mp4")
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
               "-i", listing, "-c", "copy", "-an", reel]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=render_local.RENDER_TIMEOUT_SECONDS)
        if res.returncode != 0:
            raise build_video.DeliveryError(f"falha ao montar reel: {res.stderr.strip()[:400]}")

        render_local.write_text_lf(p3._fs(os.path.join(outdir, "direcao-de-cenas.md")), build_direction())
        render_local.write_text_lf(p3._fs(os.path.join(legdir, "narracao-reel.txt")), build_narration())
        render_local.write_text_lf(p3._fs(os.path.join(legdir, "legendas.srt")), build_srt())

        result = {
            "status": "completed",
            "reel": render_local.rel(root, reel),
            "bytes": os.path.getsize(p3._fs(reel)),
            "sha256": p3._sha256_file(reel),
            "duration": sum(sc["dur"] for sc in SCENES),
            "narration": render_local.rel(root, os.path.join(legdir, "narracao-reel.txt")),
            "srt": render_local.rel(root, os.path.join(legdir, "legendas.srt")),
            "direction": render_local.rel(root, os.path.join(outdir, "direcao-de-cenas.md")),
        }
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("reel v3 gerado:", result["reel"], f"({result['duration']:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
