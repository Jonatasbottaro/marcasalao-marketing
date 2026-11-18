"""Construtor parametrizado do piloto ponta a ponta NS-002 (Agendamento online no Marca Salao).

Reutiliza os utilitarios do repositorio (build_video, carousel_layout, r002_pilot,
render_local, srt_validate) mantendo separacao limpa entre dados de marca/cenas
(ns002-piloto.config.json), dados editoriais (fixture-editorial-marca-salao.json)
e entrega transacional sem faixa de audio (-an).

Uso (a partir da raiz do checkout):
    python tools/ns002_pilot.py \
        --config 02-reels-shorts/ns002-piloto-01/ns002-piloto.config.json \
        --staging .workspace/tmp/ns002-piloto-01 \
        --archive .workspace/archives/ns002-piloto-01
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import carousel_layout
import r002_pilot
import render_local
import srt_validate

# Glifos complementares no mesmo padrao 5x7 de carousel_layout._FONT
_EXTRA_GLYPHS = {
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "[": (".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."),
    "]": (".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    "|": ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "%": ("##..#", "##.#.", "..#..", ".#...", "#..##", "#..##", "....."),
}

_EXTRA_TRANSLIT = str.maketrans({
    "—": "-",
    "–": "-",
    "•": "-",
    "ª": "a",
    "º": "o",
})

FORBIDDEN_EDITORIAL_PATTERNS = (
    ("automacao_whatsapp", re.compile(r"\bwhatsapp\b", re.IGNORECASE)),
    ("automacao_sms", re.compile(r"\bsms\b", re.IGNORECASE)),
    ("lembrete_24h", re.compile(r"lembrete|24\s*h|24\s*horas", re.IGNORECASE)),
    ("promessa_automatica", re.compile(r"autom[aá]tic[oa]|automatiz", re.IGNORECASE)),
    ("pagamento_ou_cobranca", re.compile(r"pagamento|cobran[cç]a|a pagar|checkout|cart[aã]o de cr[eé]dito", re.IGNORECASE)),
    ("promessa_faturamento", re.compile(r"faturamento|aumentar\s+receita|lucro\s+garantido", re.IGNORECASE)),
    ("promessa_faltas", re.compile(r"redu[cç][aã]o\s+de\s+faltas|zero\s+faltas|no-?show", re.IGNORECASE)),
    ("marca_legada", re.compile(r"meu\s+sal[aã]o", re.IGNORECASE)),
)


def _norm_text(text: str) -> str:
    return carousel_layout._norm(str(text).translate(_EXTRA_TRANSLIT))


def _text_width(text: str, scale: int) -> int:
    norm = _norm_text(text)
    if not norm:
        return 0
    return max(0, len(norm) * carousel_layout.char_width(scale) - scale)


def _draw_text(
    canvas: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    text: str,
    scale: int,
    color: tuple[int, int, int],
) -> None:
    norm = _norm_text(text)
    cx = int(x)
    cy = int(y)
    cw = carousel_layout.char_width(scale)
    for ch in norm:
        glyph = _EXTRA_GLYPHS.get(ch) or carousel_layout._FONT.get(ch, carousel_layout._FONT["?"])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] != "#":
                    continue
                for dy in range(scale):
                    py = cy + row * scale + dy
                    if py < 0 or py >= height:
                        continue
                    for dx in range(scale):
                        px = cx + col * scale + dx
                        if 0 <= px < width:
                            idx = (py * width + px) * 3
                            canvas[idx:idx + 3] = bytes(color)
        cx += cw


def _wrap_text(text: str, max_width: int, scale: int) -> list[str]:
    words = _norm_text(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if _text_width(candidate, scale) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        while _text_width(word, scale) > max_width:
            cut = max(1, max_width // carousel_layout.char_width(scale))
            lines.append(word[:cut])
            word = word[cut:]
        current = word
    if current:
        lines.append(current)
    return lines or [""]


def _fill_rect(
    canvas: bytearray,
    width: int,
    height: int,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int],
) -> None:
    x0c = max(0, min(width, int(x0)))
    x1c = max(x0c, min(width, int(x1)))
    y0c = max(0, min(height, int(y0)))
    y1c = max(y0c, min(height, int(y1)))
    if x1c <= x0c or y1c <= y0c:
        return
    row_bytes = bytes(color) * (x1c - x0c)
    for py in range(y0c, y1c):
        start = (py * width + x0c) * 3
        canvas[start:start + len(row_bytes)] = row_bytes


def _stroke_rect(
    canvas: bytearray,
    width: int,
    height: int,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    thickness: int,
    color: tuple[int, int, int],
) -> None:
    _fill_rect(canvas, width, height, x0, y0, x1, y0 + thickness, color)
    _fill_rect(canvas, width, height, x0, y1 - thickness, x1, y1, color)
    _fill_rect(canvas, width, height, x0, y0, x0 + thickness, y1, color)
    _fill_rect(canvas, width, height, x1 - thickness, y0, x1, y1, color)


def _draw_card(
    canvas: bytearray,
    width: int,
    height: int,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    bg_color: tuple[int, int, int],
    border_color: tuple[int, int, int] | None = None,
    border_thickness: int = 3,
    left_stripe_color: tuple[int, int, int] | None = None,
) -> None:
    _fill_rect(canvas, width, height, x0, y0, x1, y1, bg_color)
    if border_color is not None:
        _stroke_rect(canvas, width, height, x0, y0, x1, y1, border_thickness, border_color)
    if left_stripe_color is not None:
        _fill_rect(canvas, width, height, x0, y0, x0 + 12, y1, left_stripe_color)


def _draw_pill(
    canvas: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    text: str,
    scale: int,
    bg_color: tuple[int, int, int],
    text_color: tuple[int, int, int],
    pad_x: int = 20,
    pad_y: int = 12,
) -> tuple[int, int]:
    tw = _text_width(text, scale)
    th = carousel_layout.char_height(scale)
    pw = tw + 2 * pad_x
    ph = th + 2 * pad_y
    _fill_rect(canvas, width, height, x, y, x + pw, y + ph, bg_color)
    _draw_text(canvas, width, height, x + pad_x, y + pad_y, text, scale, text_color)
    return pw, ph


def _encode_png(width: int, height: int, rgb: bytearray) -> bytes:
    raw = b"".join(b"\x00" + bytes(rgb[y * width * 3:(y + 1) * width * 3]) for y in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + r002_pilot._png_chunk(b"IHDR", ihdr)
        + r002_pilot._png_chunk(b"IDAT", zlib.compress(raw, 6))
        + r002_pilot._png_chunk(b"IEND", b"")
    )


def _base_gradient(width: int, height: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> bytearray:
    canvas = bytearray(width * height * 3)
    for y in range(height):
        ratio = y / (height - 1) if height > 1 else 0.0
        color = tuple(int(top[c] + (bottom[c] - top[c]) * ratio) for c in range(3))
        canvas[y * width * 3:(y + 1) * width * 3] = bytes(color) * width
    return canvas


def _load_neutral_capture_backdrop(
    capture_path: str,
    bg_top: tuple[int, int, int],
    bg_bottom: tuple[int, int, int],
    width: int,
    height: int,
) -> bytearray:
    """Usa a area neutra da grade (y=725..885, x=350..1360) da captura base como textura sutil.

    Exclui integralmente sidebar ('Meu Salao'), titulo ('e2e-...'), 'Gestor E2E'
    e cartoes com 'A pagar'. Mistura em baixa opacidade sobre o gradiente escuro.
    """
    canvas = _base_gradient(width, height, bg_top, bg_bottom)
    if not capture_path or not os.path.isfile(render_local.fs_path(capture_path)):
        return canvas
    try:
        ffmpeg = build_video.get_ffmpeg()
        cmd = [
            ffmpeg,
            "-v", "error",
            "-i", render_local.fs_path(capture_path),
            "-vf", f"crop=1010:160:350:725,scale={width}:{height}:flags=bilinear",
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-",
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=20)
        expected = width * height * 3
        if res.returncode != 0 or len(res.stdout) != expected:
            return canvas
        raw = res.stdout
        # Mescla 12% da textura de grade no fundo sem comprometer o contraste
        for i in range(0, expected, 3):
            canvas[i] = (canvas[i] * 88 + raw[i] * 12) // 100
            canvas[i + 1] = (canvas[i + 1] * 88 + raw[i + 1] * 12) // 100
            canvas[i + 2] = (canvas[i + 2] * 88 + raw[i + 2] * 12) // 100
    except (OSError, subprocess.SubprocessError, build_video.DeliveryError):
        return canvas
    return canvas


def _pal(palette: dict, key: str) -> tuple[int, int, int]:
    vals = palette[key]
    return int(vals[0]), int(vals[1]), int(vals[2])


def _draw_brand_header(
    canvas: bytearray,
    width: int,
    height: int,
    brand: dict,
    route_label: str,
) -> int:
    palette = brand["palette"]
    overlay_cfg = brand.get("headerOverlay") or {}
    header_h = int(overlay_cfg.get("height", 170))
    header_bg = _pal(palette, "headerBg")
    accent = _pal(palette, "primaryAccent")
    secondary = _pal(palette, "secondaryAccent")
    text_pri = _pal(palette, "textPrimary")
    text_mut = _pal(palette, "textMuted")
    dark_ink = (14, 18, 28)

    _fill_rect(canvas, width, height, 0, 0, width, header_h, header_bg)
    _fill_rect(canvas, width, height, 0, header_h - 6, width, header_h, accent)

    # Monograma MS
    _fill_rect(canvas, width, height, 56, 44, 128, 116, accent)
    _draw_text(canvas, width, height, 69, 64, "MS", 4, dark_ink)

    _draw_text(canvas, width, height, 152, 42, brand["displayTitle"], 5, text_pri)
    _draw_text(canvas, width, height, 152, 92, brand.get("tagline", "AGENDAMENTO ONLINE"), 2, text_mut)

    # Indicador conciso da superficie no canto direito (sem truncamento)
    rw = _text_width(route_label, 2) + 28
    _fill_rect(canvas, width, height, width - 56 - rw, 56, width - 56, 102, secondary)
    _draw_text(canvas, width, height, width - 56 - rw + 14, 71, route_label, 2, text_pri)
    return header_h


def _draw_surface_banner(
    canvas: bytearray,
    width: int,
    height: int,
    y: int,
    badge: str,
    headline: str,
    palette: dict,
) -> int:
    secondary = _pal(palette, "secondaryAccent")
    accent = _pal(palette, "primaryAccent")
    text_pri = _pal(palette, "textPrimary")
    dark_ink = (14, 18, 28)

    _, ph = _draw_pill(canvas, width, height, 56, y, badge, 3, secondary, text_pri, pad_x=22, pad_y=12)
    hy = y + ph + 24
    lines = _wrap_text(headline, width - 112, 5)
    for line in lines:
        _draw_text(canvas, width, height, 56, hy, line, 5, accent)
        hy += carousel_layout.char_height(5) + 12
    _fill_rect(canvas, width, height, 56, hy + 4, 220, hy + 9, accent)
    return hy + 28


def _format_price_brl(value: float) -> str:
    reais = int(round(float(value) * 100))
    return f"R$ {reais // 100},{reais % 100:02d}"


def _render_scene_frame(
    scene: dict,
    config: dict,
    fixture: dict,
    root: str,
) -> bytearray:
    fmt = config["format"]
    width = int(fmt["width"])
    height = int(fmt["height"])
    brand = config["brand"]
    palette = brand["palette"]

    bg_top = _pal(palette, "backgroundTop")
    bg_bot = _pal(palette, "backgroundBottom")
    card_bg = _pal(palette, "cardBg")
    card_hi = _pal(palette, "cardHighlight")
    accent = _pal(palette, "primaryAccent")
    secondary = _pal(palette, "secondaryAccent")
    ok_col = _pal(palette, "statusConfirmed")
    wait_col = _pal(palette, "statusWaiting")
    done_col = _pal(palette, "statusDone")
    text_pri = _pal(palette, "textPrimary")
    text_mut = _pal(palette, "textMuted")
    dark_ink = (14, 18, 28)

    kind = scene["kind"]
    if kind == "manager-agenda":
        cap_abs = os.path.join(root, config["baseCaptureRef"].replace("/", os.sep))
        canvas = _load_neutral_capture_backdrop(cap_abs, bg_top, bg_bot, width, height)
    else:
        canvas = _base_gradient(width, height, bg_top, bg_bot)

    surface_labels = {
        "public-booking": "/BOOKING",
        "manager-agenda": "/GESTOR/AGENDA",
    }
    header_pill = surface_labels.get(scene.get("surface"), config.get("campaignId", "NS-002"))
    header_h = _draw_brand_header(canvas, width, height, brand, header_pill)

    booking_case = config["bookingCase"]
    services_by_id = {s["id"]: s for s in fixture["servicos"]}
    profs_by_id = {p["id"]: p for p in fixture["profissionais"]}
    selected_service = services_by_id[booking_case["servicoId"]]
    selected_prof = profs_by_id[booking_case["profissionalId"]]

    if kind == "hook-card":
        _draw_pill(canvas, width, height, 56, header_h + 70, scene["badge"], 3, secondary, text_pri, pad_x=24, pad_y=14)
        _draw_card(
            canvas, width, height, 56, header_h + 165, width - 56, header_h + 760,
            card_bg, border_color=secondary, border_thickness=3, left_stripe_color=accent,
        )
        lines = _wrap_text(scene["headline"], width - 190, 6)
        ly = header_h + 235
        for line in lines:
            _draw_text(canvas, width, height, 102, ly, line, 6, text_pri)
            ly += carousel_layout.char_height(6) + 22
        _fill_rect(canvas, width, height, 102, ly + 18, 360, ly + 26, accent)
        _draw_text(canvas, width, height, 102, ly + 56, scene.get("subline", ""), 3, accent)

        # Fluxo visual em 3 passos (sempre mantendo faixa inferior y>=1520 livre para legendas)
        steps = ("1. CLIENTE ESCOLHE", "2. CONFIRMA HORARIO", "3. APARECE NA AGENDA")
        step_w = (width - 112 - 32) // 3
        sy = header_h + 820
        for idx, label in enumerate(steps):
            sx = 56 + idx * (step_w + 16)
            _draw_card(canvas, width, height, sx, sy, sx + step_w, sy + 130, card_hi, border_color=accent if idx == 2 else None)
            wlines = _wrap_text(label, step_w - 28, 3)
            ty = sy + 28
            for wl in wlines:
                _draw_text(canvas, width, height, sx + 16, ty, wl, 3, text_pri if idx < 2 else accent)
                ty += carousel_layout.char_height(3) + 10

    elif kind == "booking-selection":
        cy = _draw_surface_banner(canvas, width, height, header_h + 36, scene["badge"], scene["headline"], palette)
        _draw_text(canvas, width, height, 56, cy, f"ROTA PUBLICA: {fixture['booking']['rota']}", 3, text_mut)
        cy += 52
        _draw_text(canvas, width, height, 56, cy, "SERVICOS DISPONIVEIS", 4, text_pri)
        cy += 44
        for srv in fixture["servicos"][:4]:
            is_sel = srv["id"] == selected_service["id"]
            _draw_card(
                canvas, width, height, 56, cy, width - 56, cy + 122,
                card_hi if is_sel else card_bg,
                border_color=accent if is_sel else None, border_thickness=4,
            )
            _draw_text(canvas, width, height, 84, cy + 24, srv["nome"], 4, accent if is_sel else text_pri)
            meta = f"{srv['duracaoMin']} MIN  -  {_format_price_brl(srv['precoBRL'])}"
            _draw_text(canvas, width, height, 84, cy + 70, meta, 3, text_mut)
            if is_sel:
                _draw_pill(canvas, width, height, width - 310, cy + 34, "SELECIONADO", 3, accent, dark_ink, pad_x=16, pad_y=10)
            cy += 136

        cy += 14
        _draw_text(canvas, width, height, 56, cy, "PROFISSIONAIS DO SALAO", 4, text_pri)
        cy += 44
        col_w = (width - 112 - 20) // 2
        for idx, prof in enumerate(fixture["profissionais"][:4]):
            col = idx % 2
            row = idx // 2
            px = 56 + col * (col_w + 20)
            py = cy + row * 124
            is_sel = prof["id"] == selected_prof["id"]
            _draw_card(
                canvas, width, height, px, py, px + col_w, py + 108,
                card_hi if is_sel else card_bg,
                border_color=accent if is_sel else None, border_thickness=4,
            )
            _draw_text(canvas, width, height, px + 20, py + 22, prof["nome"], 3, accent if is_sel else text_pri)
            _draw_text(canvas, width, height, px + 20, py + 62, prof["especialidade"][:34], 2, text_mut)

    elif kind == "booking-confirm":
        cy = _draw_surface_banner(canvas, width, height, header_h + 36, scene["badge"], scene["headline"], palette)
        _draw_text(canvas, width, height, 56, cy, "CALCULO DE HORARIOS LIVRES EM /BOOKING/[SALONID]", 2, text_mut)
        cy += 34

        # Cartao de selecao de dia e slots livres
        _draw_card(canvas, width, height, 56, cy, width - 56, cy + 335, card_bg, border_color=secondary, border_thickness=2)
        _draw_text(canvas, width, height, 84, cy + 26, "TERCA-FEIRA  18/11/2026", 4, text_pri)
        _draw_text(canvas, width, height, 84, cy + 72, f"{selected_prof['nome']}  |  {selected_service['nome']}", 3, text_mut)

        slots = scene.get("availableSlots", ["09:00", "11:00", "14:00", "16:30"])
        sel_slot = scene.get("selectedSlot", booking_case["horario"])
        slot_w = (width - 168 - 30) // 2
        for idx, slot in enumerate(slots[:4]):
            col = idx % 2
            row = idx // 2
            sx = 84 + col * (slot_w + 30)
            sy = cy + 126 + row * 94
            is_sel = slot == sel_slot
            label = f"{slot}  [ESCOLHIDO]" if is_sel else f"{slot}  LIVRE"
            _draw_card(
                canvas, width, height, sx, sy, sx + slot_w, sy + 76,
                accent if is_sel else card_hi,
                border_color=accent if is_sel else secondary, border_thickness=3,
            )
            _draw_text(canvas, width, height, sx + 22, sy + 24, label, 3, dark_ink if is_sel else text_pri)

        cy += 365
        # Resumo antes de confirmar (estritamente sem tela ou campos de cobranca)
        _draw_card(canvas, width, height, 56, cy, width - 56, cy + 350, card_bg, left_stripe_color=ok_col)
        _draw_text(canvas, width, height, 92, cy + 26, "RESUMO DO AGENDAMENTO", 4, accent)
        _draw_text(canvas, width, height, 92, cy + 84, f"CLIENTE: {booking_case['cliente']}", 3, text_pri)
        _draw_text(canvas, width, height, 92, cy + 132, f"SERVICO: {selected_service['nome']} ({selected_service['duracaoMin']} MIN)", 3, text_pri)
        _draw_text(canvas, width, height, 92, cy + 180, f"PROFISSIONAL: {selected_prof['nome']}", 3, text_pri)
        _draw_text(canvas, width, height, 92, cy + 228, f"HORARIO: 18/11/2026 AS {sel_slot}", 3, ok_col)
        _draw_text(canvas, width, height, 92, cy + 286, f"VALOR ESTIMADO: {_format_price_brl(selected_service['precoBRL'])}", 3, text_mut)

        cy += 380
        _draw_card(canvas, width, height, 56, cy, width - 56, cy + 104, ok_col)
        cta_txt = scene.get("ctaLabel", "CONFIRMAR AGENDAMENTO")
        tw = _text_width(cta_txt, 5)
        _draw_text(canvas, width, height, (width - tw) // 2, cy + 32, cta_txt, 5, dark_ink)

    elif kind == "booking-success":
        _draw_pill(canvas, width, height, 56, header_h + 60, scene["badge"], 3, ok_col, dark_ink, pad_x=24, pad_y=14)
        _draw_card(
            canvas, width, height, 56, header_h + 150, width - 56, header_h + 860,
            card_bg, border_color=ok_col, border_thickness=5, left_stripe_color=ok_col,
        )
        _draw_pill(canvas, width, height, 102, header_h + 210, "STATUS: CONFIRMADO", 3, ok_col, dark_ink, pad_x=20, pad_y=12)
        _draw_text(canvas, width, height, 102, header_h + 295, "AGENDAMENTO", 6, text_pri)
        _draw_text(canvas, width, height, 102, header_h + 360, "REALIZADO!", 6, ok_col)
        _fill_rect(canvas, width, height, 102, header_h + 435, width - 102, header_h + 440, secondary)

        _draw_text(canvas, width, height, 102, header_h + 475, f"CLIENTE: {booking_case['cliente']}", 4, text_pri)
        _draw_text(canvas, width, height, 102, header_h + 530, f"SERVICO: {selected_service['nome']}", 4, text_pri)
        _draw_text(canvas, width, height, 102, header_h + 585, f"PROFISSIONAL: {selected_prof['nome']}", 4, text_pri)
        _draw_text(canvas, width, height, 102, header_h + 640, f"DATA: 18/11 AS {booking_case['horario']}", 4, accent)

        _draw_pill(canvas, width, height, 102, header_h + 735, scene.get("subline", "VISIVEL NA AGENDA"), 3, secondary, text_pri, pad_x=22, pad_y=14)

    elif kind == "manager-agenda":
        cy = _draw_surface_banner(canvas, width, height, header_h + 28, scene["badge"], scene["headline"], palette)
        _draw_text(canvas, width, height, 56, cy, "TERCA 18/11/2026 - VISUALIZACAO E STATUS MANUAL", 3, text_mut)
        cy += 44

        highlight_id = scene.get("highlightId", "atend-001")
        for item in fixture["agenda"]["atendimentos"][:6]:
            is_hi = item["id"] == highlight_id
            srv = services_by_id[item["servico"]]
            prof = profs_by_id[item["profissional"]]
            status = item["status"]
            st_norm = _norm_text(status)
            if "CONCLUIDO" in st_norm:
                st_col = done_col
            elif "AGUARDANDO" in st_norm:
                st_col = wait_col
            else:
                st_col = ok_col

            _draw_card(
                canvas, width, height, 56, cy, width - 56, cy + 132,
                card_hi if is_hi else card_bg,
                border_color=accent if is_hi else secondary,
                border_thickness=6 if is_hi else 1,
                left_stripe_color=accent if is_hi else st_col,
            )
            pill_pad_x = 14
            pill_w = _text_width(status, 3) + 2 * pill_pad_x
            pill_x = width - 56 - 20 - pill_w
            _draw_pill(canvas, width, height, pill_x, cy + 36, status, 3, st_col, dark_ink, pad_x=pill_pad_x, pad_y=10)

            top_line = f"{item['horario']} ({item['duracaoMin']}M) {item['cliente']}"
            top_scale = 3 if _text_width(top_line, 3) <= (pill_x - 100) else 2
            _draw_text(canvas, width, height, 84, cy + 20, top_line, top_scale, accent if is_hi else text_pri)

            sub_line = f"{srv['nome']} - {prof['nome']}"
            sub_scale = 3 if _text_width(sub_line, 3) <= (pill_x - 100) else 2
            _draw_text(canvas, width, height, 84, cy + 70, sub_line, sub_scale, text_mut)
            cy += 148

    elif kind == "cta-card":
        _draw_pill(canvas, width, height, 56, header_h + 90, scene["badge"], 4, accent, dark_ink, pad_x=26, pad_y=16)
        _draw_card(
            canvas, width, height, 56, header_h + 200, width - 56, header_h + 900,
            card_bg, border_color=accent, border_thickness=4, left_stripe_color=secondary,
        )
        lines = _wrap_text(scene["headline"], width - 190, 6)
        ly = header_h + 275
        for line in lines:
            _draw_text(canvas, width, height, 102, ly, line, 6, text_pri)
            ly += carousel_layout.char_height(6) + 22
        _fill_rect(canvas, width, height, 102, ly + 22, 420, ly + 30, accent)

        # Dominio apenas como texto (nunca desenhar botao clicavel na arte final)
        domain_txt = scene.get("subline", brand["domain"])
        _draw_text(canvas, width, height, 102, ly + 72, domain_txt, 5, accent)
        _draw_text(canvas, width, height, 102, ly + 145, "DO AGENDAMENTO DA CLIENTE A AGENDA DO SALAO", 3, text_mut)
    else:
        raise build_video.DeliveryError(f"tipo de cena nao suportado: {kind}")

    return canvas


def validate_guardrails(config: dict, srt_text: str, narration_text: str) -> list[str]:
    """Valida adesao estrita aos guardrails da campanha NS-002."""
    errors: list[str] = []
    if config.get("brand", {}).get("brandName") != "Marca Salão":
        errors.append("BRAND_INVALID: brand.brandName deve ser 'Marca Salão'")
    if config.get("audioPolicy", {}).get("enabled", True) is not False:
        errors.append("AUDIO_POLICY_INVALID: audioPolicy.enabled deve ser false")
    if config.get("bookingCase", {}).get("paymentDisplayed", True) is not False:
        errors.append("PAYMENT_FORBIDDEN: bookingCase.paymentDisplayed deve ser false")

    # Ignora rodape explicativo de observacao na verificacao textual
    narr_body_lines = []
    for line in narration_text.splitlines():
        if line.strip().lower().startswith("observação editorial:") or line.strip().lower().startswith("observacao editorial:"):
            break
        narr_body_lines.append(line)
    narr_body = "\n".join(narr_body_lines)

    scene_texts = "\n".join(
        " ".join(str(scene.get(k, "")) for k in ("badge", "headline", "subline", "caption", "ctaLabel"))
        for scene in config.get("scenes", [])
    )

    for source_name, content in (("srt", srt_text), ("narracao", narr_body), ("scenes", scene_texts)):
        for rule_id, pattern in FORBIDDEN_EDITORIAL_PATTERNS:
            m = pattern.search(content)
            if m:
                errors.append(f"GUARDRAIL_{rule_id.upper()}: '{m.group(0)}' proibido em {source_name}")
    return errors


def _build_concat_command(
    scene_pngs: list[tuple[str, float]],
    srt_path: str,
    subtitle_style: str,
    video_path: str,
    width: int,
    height: int,
    fps: int,
    duration: float,
    preset: str,
) -> list[str]:
    ffmpeg = build_video.get_ffmpeg()
    cmd = [ffmpeg, "-y"]
    chains: list[str] = []
    labels: list[str] = []
    for idx, (png_path, dur) in enumerate(scene_pngs):
        cmd.extend(["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", png_path])
        chains.append(
            f"[{idx}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}[v{idx}]"
        )
        labels.append(f"[v{idx}]")
    chains.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[cat]")
    clean_srt = srt_path.replace("\\", "/").replace(":", "\\:")
    chains.append(f"[cat]subtitles='{clean_srt}':force_style='{subtitle_style}'[vfinal]")
    cmd.extend(["-filter_complex", ";".join(chains), "-map", "[vfinal]"])
    cmd.extend([
        "-an",
        "-c:v", "libx264",
        "-preset", preset,
        "-pix_fmt", "yuv420p",
        "-t", f"{duration:.3f}",
        video_path,
    ])
    return cmd


def _build_storyboard_grid(video_path: str, timestamps: list[float], output_png: str) -> None:
    if len(timestamps) != 4:
        raise build_video.DeliveryError("storyboard 2x2 exige exatamente 4 timestamps")
    ffmpeg = build_video.get_ffmpeg()
    cmd = [ffmpeg, "-y"]
    for ts in timestamps:
        cmd.extend(["-ss", f"{float(ts):.3f}", "-i", video_path])
    filter_complex = (
        "[0:v]scale=540:960[f0];"
        "[1:v]scale=540:960[f1];"
        "[2:v]scale=540:960[f2];"
        "[3:v]scale=540:960[f3];"
        "[f0][f1]hstack=inputs=2[top];"
        "[f2][f3]hstack=inputs=2[bot];"
        "[top][bot]vstack=inputs=2[grid]"
    )
    cmd.extend(["-filter_complex", filter_complex, "-map", "[grid]", "-frames:v", "1", output_png])
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    if res.returncode != 0 or not os.path.isfile(render_local.fs_path(output_png)):
        raise build_video.DeliveryError(f"falha ao gerar storyboard visual: {res.stderr[-240:]}")


def _load_json(path: str) -> dict:
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def run_pilot(
    config_path: str,
    root: str,
    staging_dir: str,
    archive_dir: str,
    project_root: str | None = None,
) -> dict:
    project_root = project_root or root
    render_local.ensure_video_tools(project_root)

    config_abs = os.path.realpath(os.path.join(root, config_path.replace("/", os.sep)) if not os.path.isabs(config_path) else config_path)
    staging_abs = os.path.realpath(staging_dir)
    archive_abs = os.path.realpath(archive_dir)
    for label, p in (("config", config_abs), ("staging", staging_abs), ("archive", archive_abs)):
        if not render_local.contained(project_root, p):
            raise build_video.DeliveryError(f"caminho de {label} fora da raiz do projeto")

    config = _load_json(config_abs)
    fixture_abs = os.path.realpath(os.path.join(root, config["fixtureRef"].replace("/", os.sep)))
    base_cap_abs = os.path.realpath(os.path.join(root, config["baseCaptureRef"].replace("/", os.sep)))
    art_cfg = config["artifacts"]
    srt_src = os.path.realpath(os.path.join(root, art_cfg["srt"].replace("/", os.sep)))
    narr_src = os.path.realpath(os.path.join(root, art_cfg["narration"].replace("/", os.sep)))
    out_dir = os.path.realpath(os.path.join(root, art_cfg["outputDir"].replace("/", os.sep)))

    for label, p in (
        ("fixture", fixture_abs),
        ("captura base", base_cap_abs),
        ("srt", srt_src),
        ("narracao", narr_src),
        ("saida", out_dir),
    ):
        if not render_local.contained(project_root, p):
            raise build_video.DeliveryError(f"caminho de {label} fora da raiz do projeto")
        if label != "saida" and not os.path.isfile(render_local.fs_path(p)):
            raise build_video.DeliveryError(f"{label} ausente: {render_local.rel(project_root, p)}")

    fixture = _load_json(fixture_abs)
    fmt = config["format"]
    duration = float(fmt["duration"])

    srt_errors = srt_validate.validate_srt_file(render_local.fs_path(srt_src), duration)
    if srt_errors:
        raise build_video.DeliveryError("SRT invalido: " + "; ".join(srt_errors))

    with open(render_local.fs_path(srt_src), "r", encoding="utf-8") as handle:
        srt_text = handle.read()
    with open(render_local.fs_path(narr_src), "r", encoding="utf-8") as handle:
        narr_text = handle.read()

    guardrail_errors = validate_guardrails(config, srt_text, narr_text)
    if guardrail_errors:
        raise build_video.DeliveryError("violacao de guardrail editorial: " + "; ".join(guardrail_errors))

    scenes = config["scenes"]
    sum_dur = round(sum(float(s["duration"]) for s in scenes), 3)
    if abs(sum_dur - duration) > 0.05:
        raise build_video.DeliveryError(f"soma das cenas ({sum_dur}s) diverge de format.duration ({duration}s)")

    video_dest = os.path.join(out_dir, art_cfg["videoName"])
    archive_video_dest = os.path.join(archive_abs, art_cfg["videoName"])
    srt_dest = os.path.join(out_dir, art_cfg["packageSrtName"])
    narr_dest = os.path.join(out_dir, art_cfg["packageNarrationName"])
    storyboard_dest = os.path.join(out_dir, art_cfg["storyboardName"])
    manifest_dest = os.path.join(out_dir, art_cfg["manifestName"])

    artifacts = {
        "video": {"staging": art_cfg["videoName"], "dest": video_dest},
        "archive_video": {"staging": "archive-" + art_cfg["videoName"], "dest": archive_video_dest},
        "srt": {"staging": art_cfg["packageSrtName"], "dest": srt_dest},
        "narration": {"staging": art_cfg["packageNarrationName"], "dest": narr_dest},
        "storyboard": {"staging": art_cfg["storyboardName"], "dest": storyboard_dest},
        "manifest": {"staging": art_cfg["manifestName"], "dest": manifest_dest},
    }

    def render(paths: dict[str, str]) -> None:
        scenes_dir = os.path.join(staging_abs, "scenes")
        os.makedirs(render_local.fs_path(scenes_dir), exist_ok=True)
        scene_pngs: list[tuple[str, float]] = []
        w, h = int(fmt["width"]), int(fmt["height"])
        for scene in scenes:
            canvas = _render_scene_frame(scene, config, fixture, root)
            png_path = os.path.join(scenes_dir, f"{scene['id']}.png")
            with open(render_local.fs_path(png_path), "wb") as handle:
                handle.write(_encode_png(w, h, canvas))
            scene_pngs.append((png_path, float(scene["duration"])))

        # Normaliza LF para entrega
        render_local.write_text(paths["srt"], srt_text.replace("\r\n", "\n").rstrip("\n") + "\n")
        render_local.write_text(paths["narration"], narr_text.replace("\r\n", "\n").rstrip("\n") + "\n")

        cmd = _build_concat_command(
            scene_pngs,
            paths["srt"],
            config.get("subtitleStyle", render_local.SUBTITLE_STYLE),
            paths["video"],
            w,
            h,
            int(fmt["fps"]),
            duration,
            fmt.get("preset", "veryfast"),
        )
        ok = build_video.run_cmd(cmd)
        if not ok:
            raise build_video.DeliveryError("renderizacao FFmpeg falhou")

        shutil.copyfile(render_local.fs_path(paths["video"]), render_local.fs_path(paths["archive_video"]))
        _build_storyboard_grid(paths["video"], art_cfg["storyboardTimestamps"], paths["storyboard"])

    def validators(paths: dict[str, str]) -> None:
        errs = srt_validate.validate_srt_file(render_local.fs_path(paths["srt"]), duration)
        if errs:
            raise build_video.DeliveryError("SRT no pacote invalido: " + "; ".join(errs))
        build_video.validate_mp4(paths["video"], int(fmt["width"]), int(fmt["height"]), int(fmt["fps"]), duration)
        probe_sb = build_video.probe_media(render_local.fs_path(paths["storyboard"]))
        sb_stream = probe_sb["streams"][0]
        if int(sb_stream["width"]) != 1080 or int(sb_stream["height"]) != 1920:
            raise build_video.DeliveryError("storyboard com dimensoes inesperadas")

    def render_all(paths: dict[str, str]) -> None:
        render(paths)
        inspection = build_video.validate_mp4(paths["video"], int(fmt["width"]), int(fmt["height"]), int(fmt["fps"]), duration)
        manifest = {
            "schemaVersion": 1,
            "id": config["id"],
            "campaignId": config["campaignId"],
            "preset": config["preset"],
            "brand": {
                "tenantId": config["brand"]["tenantId"],
                "brandName": config["brand"]["brandName"],
                "domain": config["brand"]["domain"],
            },
            "config": render_local.rel(project_root, config_abs),
            "fixture": {
                "path": render_local.rel(project_root, fixture_abs),
                "sha256": render_local.sha256_file(fixture_abs),
            },
            "command": (
                f"python tools/ns002_pilot.py --config {render_local.rel(project_root, config_abs)} "
                f"--staging {render_local.rel(project_root, staging_abs)} "
                f"--archive {render_local.rel(project_root, archive_abs)}"
            ),
            "tools": {
                "ffmpeg": render_local.tool_version(build_video.get_ffmpeg()),
                "ffprobe": render_local.tool_version(build_video.get_ffprobe()),
            },
            "artifacts": {
                "video": {
                    "path": render_local.rel(project_root, video_dest),
                    "archivePath": render_local.rel(project_root, archive_video_dest),
                    "sha256": render_local.sha256_file(paths["video"]),
                    "bytes": os.path.getsize(render_local.fs_path(paths["video"])),
                    "ffprobe": inspection,
                    "versioned": False,
                    "reasonNotVersioned": ".gitignore versionado ignora *.mp4; manifesto preserva hash, ffprobe e comando reproduzivel",
                },
                "srt": {
                    "path": render_local.rel(project_root, srt_dest),
                    "sourcePath": config["artifacts"]["srt"],
                    "sha256": render_local.sha256_file(paths["srt"]),
                    "bytes": os.path.getsize(render_local.fs_path(paths["srt"])),
                    "versioned": True,
                },
                "narration": {
                    "path": render_local.rel(project_root, narr_dest),
                    "sourcePath": config["artifacts"]["narration"],
                    "sha256": render_local.sha256_file(paths["narration"]),
                    "bytes": os.path.getsize(render_local.fs_path(paths["narration"])),
                    "versioned": True,
                },
                "storyboard": {
                    "path": render_local.rel(project_root, storyboard_dest),
                    "timestampsSeconds": art_cfg["storyboardTimestamps"],
                    "sha256": render_local.sha256_file(paths["storyboard"]),
                    "bytes": os.path.getsize(render_local.fs_path(paths["storyboard"])),
                    "width": 1080,
                    "height": 1920,
                    "versioned": True,
                },
            },
        }
        render_local.write_text(paths["manifest"], json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    build_video.transactional_export(staging_abs, artifacts, render_all, validators)
    return _load_json(manifest_dest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Piloto ponta a ponta NS-002 (Marca Salao)")
    parser.add_argument("--config", required=True, help="Caminho para ns002-piloto.config.json")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument("--project-root", default=None, help="Raiz principal do repositorio")
    parser.add_argument("--staging", required=True, help="Diretorio de staging em .workspace/tmp/")
    parser.add_argument("--archive", required=True, help="Diretorio de arquivo MP4 em .workspace/archives/")
    parser.add_argument("--json", action="store_true", help="Emite manifesto JSON no stdout")
    args = parser.parse_args(argv)
    try:
        manifest = run_pilot(
            args.config,
            args.root,
            args.staging,
            args.archive,
            project_root=args.project_root,
        )
    except build_video.DeliveryError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro: entrada invalida ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print("Piloto NS-002 renderizado e promovido com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
