"""Tipografia comercial reutilizavel para pecas do Marca Salao (Modo Comercial).

Motor de texto profissional baseado em ASS/libass (o mesmo provedor de legendas
ja usado pelo projeto), sem dependencia de Pillow nem fonte bitmap.

Por que ASS/libass:
- Resolve a fonte do brand-kit (Arial) pelo provedor do sistema (DirectWrite no
  Windows; fontconfig no Linux), com antialiasing, acentos e caracteres especiais.
- Suporta pesos (bold), tamanho, cor, contorno, alinhamento, margens e quebra de
  linha automatica por largura (WrapStyle), sem medir texto manualmente.
- Reaproveita o FFmpeg portatil do projeto; nenhum renderizador novo.

O Modo Comercial coexiste com o renderizador bitmap legado
(`carousel_layout`), que continua valido para testes e entregas historicas.
"""

from __future__ import annotations

import os
import subprocess

# Alinhamento ASS (numpad): 1..9 (ver libass). 7..9 = topo; 4..6 = meio; 1..3 = base.
AN_TOP_LEFT, AN_TOP_CENTER, AN_TOP_RIGHT = 7, 8, 9
AN_MID_LEFT, AN_MID_CENTER, AN_MID_RIGHT = 4, 5, 6
AN_BOT_LEFT, AN_BOT_CENTER, AN_BOT_RIGHT = 1, 2, 3


def ass_color(hex_value: str, alpha: int = 0) -> str:
    """#RRGGBB -> &HAABBGGRR (ASS usa ordem BGR; alpha 00 opaco, FF transparente)."""
    text = str(hex_value or "").strip().lstrip("#")
    if len(text) != 6:
        text = "FFFFFF"
    try:
        r = int(text[0:2], 16)
        g = int(text[2:4], 16)
        b = int(text[4:6], 16)
    except ValueError:
        r = g = b = 255
    return f"&H{alpha & 0xFF:02X}{b:02X}{g:02X}{r:02X}"


def ass_escape(text: str) -> str:
    """Escapa texto para um Dialogue ASS, preservando acentos e quebrando linhas."""
    out = str(text or "")
    out = out.replace("\\", "\\\\").replace("{", "(").replace("}", ")")
    out = out.replace("\r\n", "\n").replace("\r", "\n")
    out = out.replace("\n", "\\N")
    return out


def build_ass(width: int, height: int, styles: list[dict], events: list[dict]) -> str:
    """Monta um documento ASS v4.00+ com os estilos e eventos informados.

    style dict: name, font, size, color(hex), bold, italic, alignment, marginL,
                marginR, marginV, outline, shadow, outlineColor(hex), spacing.
    event dict: style, text, start, end, layer, override (str prefix, ex. "{\\an8\\pos(..)}").
    """
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {int(width)}",
        f"PlayResY: {int(height)}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding",
    ]
    for s in styles:
        lines.append(
            "Style: {name},{font},{size},{pri},{sec},{outc},{backc},{bold},{italic},0,0,"
            "100,100,{spacing},0,1,{outline},{shadow},{align},{ml},{mr},{mv},1".format(
                name=s["name"],
                font=s.get("font", "Arial"),
                size=int(s.get("size", 48)),
                pri=ass_color(s.get("color", "#F5F7FA")),
                sec=ass_color(s.get("secondary", "#0000FF")),
                outc=ass_color(s.get("outlineColor", "#101010"), alpha=int(s.get("outlineAlpha", 0))),
                backc=ass_color(s.get("backColor", "#000000"), alpha=0x80),
                bold=1 if s.get("bold") else 0,
                italic=1 if s.get("italic") else 0,
                spacing=int(s.get("spacing", 0)),
                outline=int(s.get("outline", 0)),
                shadow=int(s.get("shadow", 0)),
                align=int(s.get("alignment", AN_TOP_LEFT)),
                ml=int(s.get("marginL", 0)),
                mr=int(s.get("marginR", 0)),
                mv=int(s.get("marginV", 0)),
            )
        )
    lines += ["", "[Events]",
              "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for e in events:
        override = e.get("override", "") or ""
        text = override + ass_escape(e.get("text", ""))
        lines.append(
            "Dialogue: {layer},{start},{end},{style},,{ml},{mr},{mv},,{text}".format(
                layer=int(e.get("layer", 0)),
                start=e.get("start", "0:00:00.00"),
                end=e.get("end", "0:00:10.00"),
                style=e["style"],
                ml=int(e.get("marginL", 0)),
                mr=int(e.get("marginR", 0)),
                mv=int(e.get("marginV", 0)),
                text=text,
            )
        )
    return "\n".join(lines) + "\n"


def _ass_filter_arg(ass_path: str) -> str:
    """Argumento do filtro `ass=` no mesmo padrao do projeto (subtitles='...'): 
    barras invertidas viram '/', ':' e escapado e o valor fica entre aspas simples."""
    clean = ass_path.replace("\\", "/").replace(":", "\\:")
    return f"'{clean}'"


def render_text_on_image(ffmpeg: str, base_path: str, ass_path: str, out_path: str,
                         width: int, height: int, extra_filters: str | None = None,
                         timeout: int = 120) -> None:
    """Renderiza um ASS sobre uma imagem base e grava o resultado final (PNG/JPG)."""
    vf = f"ass={_ass_filter_arg(ass_path)}"
    if extra_filters:
        vf = extra_filters + "," + vf
    tmp_out = out_path
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:d=1",
           "-frames:v", "1", "-f", "image2", "-"]
    # O base_path e composto como filtro de entrada quando existir.
    if base_path:
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
               "-i", base_path, "-vf", vf, "-frames:v", "1", tmp_out]
    else:
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
               "-f", "lavfi", "-i", f"color=c=0x121620:s={width}x{height}:d=1",
               "-vf", vf, "-frames:v", "1", tmp_out]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"falha ao renderizar texto ASS: {res.stderr.strip()[:400]}")
