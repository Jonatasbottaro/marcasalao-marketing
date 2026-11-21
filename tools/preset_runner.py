"""Motor generico multi-tenant de presets de video e audio (Agente 2 - Etapa 2).

Constrói pacotes de entrega verticais 1080x1920 @ 30 fps para os presets
"saas-demo" (SaaS B2B / Apps: marca-salao, meu-salao) e "shorts-completo"
(Shorts / Produtos Tech: multitrack-hub), respeitando os guardrails de cada
tenant carregados por tenant_validator.load_and_validate_tenant(...).

Saida padronizada e transacional (tudo produzido em staging, promovido
atomicamente; qualquer falha preserva a entrega anterior):
    <slug>.mp4, <slug>.srt, <slug>_narracao.txt,
    preview-storyboard.png (grade 2x2 com 4 frames) e manifest.json
    (tenantId, preset, hashes SHA-256 de todos os artefatos e saida ffprobe).
Copia do .mp4 em .workspace/archives/<slug>/ (*.mp4 e .workspace/ estao no
.gitignore; o manifesto preserva hash, ffprobe e comando reproduzivel).

Ponto unico de entrada para brandKit, guardrails e fixture:
    ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=REPO_ROOT, strict=True)

Antes de qualquer frame ser renderizado ou o FFmpeg invocado:
  1. O tenant e validado (brandKit + guardrails + fixture).
  2. Todos os textos de cenas, legendas (.srt) e roteiro de narracao sao
     auditados por tenant_validator.validate_text_against_guardrails(...).
  3. Se guardrails["audioPolicy"]["allowAudioTrack"] for false, o motor força
     -an (zero streams de audio) e recusa com erro explícito qualquer tentativa
     de injetar trilha sonora (--audio).

Reutiliza as primitivas de desenho PNG (bitmap 5x7, stdlib) e montagem de
tools/ns002_pilot.py e os validadores/FFmpeg de tools/build_video.py,
tools/render_local.py e tools/srt_validate.py.
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
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import carousel_layout
import ns002_pilot
import render_local
import srt_validate
import tenant_validator

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
OUTPUT_FPS = 30
STORYBOARD_SCALE = 540  # metade de 1080 na grade 2x2 (540x960 por frame)

PRESET_SAAS_DEMO = "saas-demo"
PRESET_SHORTS_COMPLETO = "shorts-completo"
SUPPORTED_PRESETS = (PRESET_SAAS_DEMO, PRESET_SHORTS_COMPLETO)


class PresetRunnerError(Exception):
    """Falha controlada do motor de presets (mensagem sanitizada, sem stack)."""


def _load_json(path: str) -> dict:
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _slug_from_config(config: dict, tenant_id: str) -> str:
    return str(config.get("id") or f"{tenant_id}-{config.get('preset', 'preset')}")


# ---------------------------------------------------------------------------
# Primitivas de desenho reaproveitadas de tools/ns002_pilot.py (bitmap 5x7,
# stdlib, sem dependencia de fonte do sistema).
# ---------------------------------------------------------------------------
_draw_text = ns002_pilot._draw_text
_wrap_text = ns002_pilot._wrap_text
_fill_rect = ns002_pilot._fill_rect
_stroke_rect = ns002_pilot._stroke_rect
_draw_card = ns002_pilot._draw_card
_draw_pill = ns002_pilot._draw_pill
_encode_png = ns002_pilot._encode_png
_base_gradient = ns002_pilot._base_gradient
_pal = ns002_pilot._pal
_format_price_brl = ns002_pilot._format_price_brl
_norm_text = ns002_pilot._norm_text
_text_width = ns002_pilot._text_width


def _brand_palette(brand_kit: dict) -> dict:
    """Devolve a paleta RGB (chaves usadas pelos desenhistas de ns002_pilot)."""
    return brand_kit.get("palette", {}).get("rgb", {})


# Rotulos de UI padrao: neutros e sem vocabulario de nicho. Cada tenant deve
# declarar `uiLabels` no brand-kit para os termos da propria marca; chaves
# ausentes usam estes fallbacks genericos. Os 7 primeiros sao o contrato
# versionado de uiLabels; os demais cobrem a chrome compartilhada de videos e
# cards (badges, rodapes, passos e resumos).
DEFAULT_UI_LABELS = {
    # Contrato versionado (schemas/brand-kit.schema.json)
    "teamSectionTitle": "EQUIPE",
    "catalogSectionTitle": "CATALOGO",
    "publicRouteFallback": "/",
    "managerRouteFallback": "/gestor",
    "journeyBridgeCaption": "DA ESCOLHA A CONFIRMACAO",
    "itemUnitLabel": "item",
    "customerLabel": "Cliente",
    # Chrome compartilhada de video
    "teamMemberLabel": "RESPONSAVEL",
    "managerSectionLabel": "PAINEL DO GESTOR",
    "selectedLabel": "SELECIONADO",
    "availableLabel": "DISPONIVEL",
    "selectedSlotLabel": "ESCOLHIDO",
    "availableSlotLabel": "LIVRE",
    "summaryTitle": "RESUMO DA CONFIRMACAO",
    "statusLabel": "STATUS",
    "confirmedLabel": "CONFIRMADO",
    "successTitle": "REGISTRO",
    "successHighlight": "REALIZADO!",
    "visibleInPanelLabel": "VISIVEL NO PAINEL",
    "dateLabel": "DATA",
    "atLabel": "AS",
    "availabilityCaption": "HORARIOS DISPONIVEIS EM",
    "estimatedValueLabel": "VALOR ESTIMADO POR",
    "ctaConfirmLabel": "CONFIRMAR",
    "stepChooseTemplate": "{customer} ESCOLHE",
    "stepConfirmLabel": "CONFIRMA OS DADOS",
    "stepAppearLabel": "ACOMPANHE O STATUS",
    "managerCaption": "VISAO E STATUS",
    "linkCtaLabel": "ACESSE O LINK DA BIO OU DA DESCRICAO",
    # Chrome compartilhada de catalogo/metricas
    "liveDataBadge": "DADOS REAIS",
    "projectsLabel": "PROJETOS",
    "stemsLabel": "STEMS",
    "sharesLabel": "COTAS",
    "tracksLabel": "FAIXAS",
    "shareUnitLabel": "COTA",
    "remainingSlotsLabel": "VAGAS RESTANTES",
    "routeLabel": "ROTA",
    "referenceLabel": "REFERENCIA",
    "priceLabel": "PRECO",
    "specialtyLabel": "ESPECIALIDADE",
    "bpmLabel": "BPM",
    "keyLabel": "TOM",
    "scheduleLabel": "AGENDA",
    "agendaSummaryLabel": "REGISTROS",
    "stemsCaption": "FAIXAS SEPARADAS POR INSTRUMENTO",
    "sharesFromLabel": "COTAS A PARTIR DE",
    "processingCaption": "PROCESSAMENTO EM NUVEM",
    # Chrome compartilhada de cards estaticos
    "guideBadge": "GUIA PRATICO",
    "diagnosticBadge": "DIAGNOSTICO",
    "practiceBadge": "PRATICA",
    "summaryBadge": "RESUMO",
    "ctaBadge": "CHAMADA PARA A ACAO",
    "diagnosticTitle": "DIAGNOSTICO DA OPERACAO",
    "practiceTitle": "ITENS DA PRATICA",
    "summaryCardTitle": "RESUMO E PROXIMO PASSO",
    "valueTitle": "RESUMO DE VALOR",
    "chooseItemLabel": "ESCOLHA O ITEM",
    "confirmStepLabel": "CONFIRME OS DADOS",
    "followStepLabel": "ACOMPANHE O STATUS",
    "accessLabel": "ACESSE",
    "publicFlowCaption": "NO FLUXO PUBLICO",
    "staticFooter": "CONTEUDO ESTATICO - SEM AUDIO",
    "carouselFooter": "CARROSSEL - SEM AUDIO",
    "publicRouteWord": "PUBLICA",
    "ctaLinkBio": "LINK NA BIO",
    "ctaLinkDescription": "LINK NA DESCRICAO",
}


def _resolve_ui_labels(brand_kit: dict) -> dict:
    """Resolve rotulos de UI do brand-kit sobre defaults neutros.

    ``brand_kit["uiLabels"]`` e opcional. Qualquer chave string nao vazia e
    aceita (o schema versionado restringe o contrato publico, mas tenants
    legados ou extensoes internas nao quebram o render); chaves ausentes caem
    no fallback neutro acima.
    """
    provided = brand_kit.get("uiLabels")
    labels = dict(DEFAULT_UI_LABELS)
    if isinstance(provided, dict):
        for key, value in provided.items():
            if isinstance(value, str) and value.strip():
                labels[str(key)] = value
    return labels


# ---------------------------------------------------------------------------
# VisualStyle v1 + enquadramento por perfil (fonte unica de tokens visuais)
# ---------------------------------------------------------------------------
VISUAL_STYLE_SCHEMA_VERSION = 1
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
VISUAL_STYLE_LIMITS = {
    "fontSize": (16, 160),
    "marginTop": (0, 600),
    "marginHorizontal": (0, 400),
}
FRAMING_PROFILES = {
    "9:16": {
        "width": 1080, "height": 1920,
        "topSafePx": 160, "bottomSafePx": 200, "sideSafePx": 56,
        "titleFontSize": 42,
        "derivativeTopInsetPx": 0, "derivativeBottomInsetPx": 0,
    },
    "4:5": {
        "width": 1080, "height": 1350,
        "topSafePx": 120, "bottomSafePx": 160, "sideSafePx": 56,
        "titleFontSize": 36,
        "derivativeTopInsetPx": 0, "derivativeBottomInsetPx": 0,
    },
    "1:1": {
        "width": 1080, "height": 1080,
        "topSafePx": 96, "bottomSafePx": 112, "sideSafePx": 56,
        "titleFontSize": 32,
        "derivativeTopInsetPx": 0, "derivativeBottomInsetPx": 0,
    },
    "16:9": {
        "width": 1920, "height": 1080,
        "topSafePx": 48, "bottomSafePx": 64, "sideSafePx": 64,
        "titleFontSize": 24,
        "derivativeTopInsetPx": 0, "derivativeBottomInsetPx": 0,
    },
}
FRAMING_FIELDS = (
    "width", "height", "topSafePx", "bottomSafePx", "sideSafePx",
    "titleFontSize", "derivativeTopInsetPx", "derivativeBottomInsetPx",
)


def resolve_framing(brand_kit: dict, profile: str = "9:16") -> dict:
    """Safe-zones do perfil, com override opcional em ``brand-kit.framingByProfile``."""
    key = profile if profile in FRAMING_PROFILES else "9:16"
    framing = dict(FRAMING_PROFILES[key])
    framing["profile"] = key
    overrides = brand_kit.get("framingByProfile")
    if isinstance(overrides, dict) and isinstance(overrides.get(key), dict):
        for field in FRAMING_FIELDS:
            value = overrides[key].get(field)
            if isinstance(value, int) and value >= 0:
                framing[field] = value
    framing["titleFontSize"] = max(16, min(160, int(framing["titleFontSize"])))
    return framing


def _style_number(value: Any, field: str, fallback: int) -> int:
    minimum, maximum = VISUAL_STYLE_LIMITS[field]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(minimum, min(maximum, int(round(value))))
    return fallback


def resolve_visual_style(brand_kit: dict, profile: str = "9:16") -> dict:
    """VisualStyle v1 canonico: brand-kit.visualStyle valido ou derivado da paleta."""
    framing = resolve_framing(brand_kit, profile)
    palette = brand_kit.get("palette") or {}
    provided = brand_kit.get("visualStyle")
    provided = provided if isinstance(provided, dict) else {}
    provided_title = provided.get("title")
    provided_title = provided_title if isinstance(provided_title, dict) else {}

    def color(value: Any, fallback: str) -> str:
        return value if isinstance(value, str) and HEX_COLOR_RE.match(value) else fallback

    title = {
        "textColor": color(provided_title.get("textColor"), str(palette.get("textPrimary") or "#FFFFFF")),
        "outlineColor": color(provided_title.get("outlineColor"), str(palette.get("background") or "#000000")),
        "fontSize": _style_number(provided_title.get("fontSize"), "fontSize", framing["titleFontSize"]),
        "marginTop": _style_number(provided_title.get("marginTop"), "marginTop", framing["topSafePx"]),
        "marginHorizontal": _style_number(
            provided_title.get("marginHorizontal"), "marginHorizontal", framing["sideSafePx"]
        ),
    }
    tenant = str(brand_kit.get("tenantId") or "tenant")
    style_id = str(provided.get("id") or f"{tenant}-{framing['profile'].replace(':', 'x')}")
    return {"schemaVersion": VISUAL_STYLE_SCHEMA_VERSION, "id": style_id, "title": title}


def resolve_visual_tokens(brand_kit: dict, profile: str = "9:16") -> dict:
    """Fonte unica de tokens visuais para video, derivados e cards estaticos."""
    framing = resolve_framing(brand_kit, profile)
    return {
        "profile": framing["profile"],
        "uiLabels": _resolve_ui_labels(brand_kit),
        "visualStyle": resolve_visual_style(brand_kit, profile),
        "framing": framing,
        "palette": brand_kit.get("palette") or {},
        "typography": brand_kit.get("typography") or {},
    }


def _draw_brand_header_generic(canvas, width, height, brand_kit, route_label):
    """Cabecalho de marca dinamico: monogram, displayTitle, tagline,
    headerOverlay.height e cores da brandKit."""
    palette = _brand_palette(brand_kit)
    overlay_cfg = brand_kit.get("headerOverlay") or {}
    header_h = int(overlay_cfg.get("height", 170))
    header_bg = _pal(palette, "headerBg")
    accent = _pal(palette, "primaryAccent")
    secondary = _pal(palette, "secondaryAccent")
    text_pri = _pal(palette, "textPrimary")
    text_mut = _pal(palette, "textMuted")
    dark_ink = (14, 18, 28)

    _fill_rect(canvas, width, height, 0, 0, width, header_h, header_bg)
    _fill_rect(canvas, width, height, 0, header_h - 6, width, header_h, accent)

    # Monograma (letra(s) da brandKit, nao hardcoded)
    mono = str(brand_kit.get("monogram", "??"))
    _fill_rect(canvas, width, height, 56, 44, 128, 116, accent)
    _draw_text(canvas, width, height, 69, 64, mono, 4, dark_ink)

    _draw_text(canvas, width, height, 152, 42, str(brand_kit.get("displayTitle", "MARCA")), 5, text_pri)
    _draw_text(canvas, width, height, 152, 92, str(brand_kit.get("tagline", "")), 2, text_mut)

    # Indicador conciso da superficie no canto direito (sem truncamento)
    rw = _text_width(route_label, 2) + 28
    _fill_rect(canvas, width, height, width - 56 - rw, 56, width - 56, 102, secondary)
    _draw_text(canvas, width, height, width - 56 - rw + 14, 71, route_label, 2, text_pri)
    return header_h


def _draw_surface_banner_generic(canvas, width, height, y, badge, headline, palette):
    """Banner de superfície: pílula de badge + título em destaque."""
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


# ===========================================================================
# Montagem de SRT e roteiro de narracao (textos puros, auditaveis)
# ===========================================================================
def _srt_timestamp(ms: float) -> str:
    seconds, millis = divmod(int(round(ms)), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _scene_text(scene: dict, key: str) -> str:
    return str(scene.get(key) or "")


def build_srt_text(scenes: list[dict]) -> str:
    """Constrói o conteúdo .srt a partir das legendas (caption) das cenas."""
    blocks = []
    index = 0
    for scene in scenes:
        text = _scene_text(scene, "caption") or _scene_text(scene, "onScreenText")
        if not text:
            continue
        index += 1
        blocks.append(
            f"{index}\n"
            f"{_srt_timestamp(scene['start'] * 1000.0)} --> "
            f"{_srt_timestamp(scene['end'] * 1000.0)}\n"
            f"{text}"
        )
    if not blocks:
        raise PresetRunnerError("SRT_VAZIO: nenhuma cena possui texto de legenda (caption)")
    return "\n\n".join(blocks) + "\n"


def build_narration_text(scenes: list[dict], package_id: str) -> str:
    """Constrói o roteiro de narracao externo (.txt), organizado por cena."""
    lines = [
        f"Roteiro de narracao - {package_id}",
        "Video com suporte a legendas; texto para ferramenta externa, organizado por cena e tempos.",
        "",
    ]
    found = False
    for scene in scenes:
        text = _scene_text(scene, "narrationText") or _scene_text(scene, "caption")
        if not text:
            continue
        found = True
        lines.append(f"[{_srt_timestamp(scene['start'] * 1000.0)} --> {_srt_timestamp(scene['end'] * 1000.0)}] {scene.get('id', '?')}")
        lines.append(text)
        lines.append("")
    if not found:
        raise PresetRunnerError("NARracao_VAZIA: nenhuma cena possui texto de narracao")
    return "\n".join(lines).rstrip("\n") + "\n"


# ===========================================================================
# FFmpeg: filtros de montagem + comando de render (com e sem audio)
# ===========================================================================
def _build_concat_filter(num_inputs: int, srt_path: str, subtitle_style: str,
                         width: int, height: int, fps: int) -> tuple[list[str], str]:
    """Gera a cadeia de filtros: escala/pad de cada entrada -> concat -> legendas."""
    chains: list[str] = []
    labels: list[str] = []
    for idx in range(num_inputs):
        chains.append(
            f"[{idx}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}[v{idx}]"
        )
        labels.append(f"[v{idx}]")
    chains.append("".join(labels) + f"concat=n={num_inputs}:v=1:a=0[cat]")
    clean_srt = srt_path.replace("\\", "/").replace(":", "\\:")
    chains.append(f"[cat]subtitles='{clean_srt}':force_style='{subtitle_style}'[vfinal]")
    return chains, "[vfinal]"


def _audio_filter_chain(audio_path: str | None, total_s: float, input_index: int) -> tuple[list[str], str]:
    """Devolve (argumentos de entrada extra, cadeia de filtro de audio, label de mapeamento).

    - Arquivo externo: trima para a duracao exata e padoca se for menor.
    - Sem arquivo (preset com audio permitido): anullsrc (silencio limpo) trimmado.
    """
    extra_inputs: list[str] = []
    if audio_path is not None:
        extra_inputs = ["-i", str(audio_path)]
    else:
        extra_inputs = ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    audio_label = f"[{input_index}:a]"
    atrim = f"{audio_label}atrim=0:{total_s:.3f},apad=pad_dur={total_s:.3f}[audio]"
    return extra_inputs, atrim


def _build_render_command(scenes: list[tuple[str, float]], srt_path: str, subtitle_style: str,
                          width: int, height: int, fps: int, total_s: float,
                          x264_preset: str, include_audio: bool, audio_path: str | None,
                          video_path: str) -> list[str]:
    """Constrói o comando FFmpeg completo (video + opcional audio AAC).

    Quando include_audio e falso (allowAudioTrack=false), força -an e nao
    injeta nenhuma faixa de audio, independentemente de audio_path.
    """
    ffmpeg = build_video.get_ffmpeg()
    num_inputs = len(scenes)
    cmd: list[str] = [ffmpeg, "-y"]
    for png_path, dur in scenes:
        cmd += ["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", str(png_path)]

    audio_chain = ""
    if include_audio:
        if audio_path is not None:
            # Som externo fornecido pelo usuario.
            extra_inputs, audio_chain = _audio_filter_chain(audio_path, total_s, num_inputs)
            cmd += extra_inputs
        else:
            # Trilha limpa gerada pelo proprio FFmpeg (anullsrc) quando nenhum
            # arquivo externo e passado, garantindo 1 stream de audio AAC valido.
            extra_inputs, audio_chain = _audio_filter_chain(None, total_s, num_inputs)
            cmd += extra_inputs

    filter_chains, final_label = _build_concat_filter(num_inputs, srt_path, subtitle_style, width, height, fps)
    if audio_chain:
        filter_chains.append(audio_chain)
    cmd += ["-filter_complex", ";".join(filter_chains), "-map", final_label]
    if audio_chain:
        cmd += ["-map", "[audio]"]
        cmd += [
            "-c:v", "libx264", "-preset", x264_preset, "-pix_fmt", "yuv420p",
            "-r", str(fps), "-t", f"{total_s:.3f}",
            "-c:a", "aac", "-b:a", "128k",
            str(video_path),
        ]
    else:
        cmd += [
            "-an",
            "-c:v", "libx264", "-preset", x264_preset, "-pix_fmt", "yuv420p",
            "-r", str(fps), "-t", f"{total_s:.3f}",
            str(video_path),
        ]
    return cmd


def _build_storyboard_grid(video_path: str, timestamps: list[float], output_png: str) -> None:
    """Gera a grade visual 2x2 com 4 frames extraídos nos segundos informados."""
    if len(timestamps) != 4:
        raise PresetRunnerError("STORYBOARD_INVALID: sao necessarios exatamente 4 timestamps")
    ffmpeg = build_video.get_ffmpeg()
    cmd = [ffmpeg, "-y"]
    for ts in timestamps:
        cmd.extend(["-ss", f"{float(ts):.3f}", "-i", str(video_path)])
    filter_complex = (
        "[0:v]scale=540:960[f0];"
        "[1:v]scale=540:960[f1];"
        "[2:v]scale=540:960[f2];"
        "[3:v]scale=540:960[f3];"
        "[f0][f1]hstack=inputs=2[top];"
        "[f2][f3]hstack=inputs=2[bot];"
        "[top][bot]vstack=inputs=2[grid]"
    )
    cmd.extend(["-filter_complex", filter_complex, "-map", "[grid]", "-frames:v", "1", str(output_png)])
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    if res.returncode != 0 or not os.path.isfile(render_local.fs_path(output_png)):
        raise build_video.DeliveryError(f"falha ao gerar storyboard visual: {res.stderr[-240:]}")


# ===========================================================================
# Inspecao FFprobe e validacao do MP4 (geometria/fps/duracao/contagem de audio)
# ===========================================================================
def _probe_summary(path: str, width: int, height: int, fps: int, duration: float,
                   expect_audio: int) -> dict:
    info = build_video.probe_media(path)
    streams = info.get("streams", [])
    video = [s for s in streams if s.get("codec_type") == "video"]
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    problems: list[str] = []
    if len(video) != 1:
        problems.append(f"streams de video: {len(video)} (esperado 1)")
    if len(audio) != expect_audio:
        problems.append(f"streams de audio: {len(audio)} (esperado {expect_audio})")
    v = video[0] if video else {}
    if v.get("codec_name") != "h264":
        problems.append(f"codec de video: {v.get('codec_name')} (esperado h264)")
    if int(v.get("width", 0)) != width or int(v.get("height", 0)) != height:
        problems.append(f"dimensoes: {v.get('width')}x{v.get('height')} (esperado {width}x{height})")
    if v.get("pix_fmt") != "yuv420p":
        problems.append(f"pix_fmt: {v.get('pix_fmt')} (esperado yuv420p)")
    rate = v.get("avg_frame_rate", "0/1")
    num, _, den = str(rate).partition("/")
    measured_fps = float(num) / float(den or 1)
    if abs(measured_fps - fps) > 0.01:
        problems.append(f"fps: {measured_fps} (esperado {fps})")
    measured_duration = float(info.get("format", {}).get("duration", 0))
    if abs(measured_duration - duration) > 0.2:
        problems.append(f"duracao: {measured_duration:.3f}s (esperado {duration:.3f}s)")
    if problems:
        raise build_video.DeliveryError("MP4 reprovado na inspecao: " + "; ".join(problems))
    return {
        "videoStreams": len(video),
        "audioStreams": len(audio),
        "codec": v.get("codec_name"),
        "width": int(v.get("width", 0)) if v else None,
        "height": int(v.get("height", 0)) if v else None,
        "fps": measured_fps,
        "pixFmt": v.get("pix_fmt"),
        "duration": measured_duration,
        "audioCodec": audio[0].get("codec_name") if audio else None,
    }


# ===========================================================================
# Renderizacao de frames (desenho bitmap puro) - preset saas-demo
# ===========================================================================
def _hex_to_rgb(value: Any, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    """Converte #RRGGBB do VisualStyle em tupla RGB; fallback se invalido."""
    text = str(value or "").strip().lstrip("#")
    if len(text) == 6:
        try:
            return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
        except ValueError:
            pass
    return fallback


def _display_date(value: Any) -> str:
    """Converte YYYY-MM-DD em DD/MM/YYYY para exibicao; mantem outros formatos."""
    text = str(value or "-")
    parts = text.split("-")
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return text


def _render_saas_frame(scene: dict, brand_kit: dict, fixture: dict, root: str,
                       base_capture_ref: str | None, booking_case: dict,
                       campaign_id: str) -> Any:
    """Reaproveita o layout multi-superficie do piloto NS-002, alimentado por
    ctx['brandKit'] (palette.rgb, monogram, headerOverlay, displayTitle...)
    e ctx['fixture'], sem exibir elementos proibidos."""
    palette = _brand_palette(brand_kit)
    width, height = OUTPUT_WIDTH, OUTPUT_HEIGHT
    tokens = resolve_visual_tokens(brand_kit, "9:16")
    framing = tokens["framing"]
    top_safe = int(framing["topSafePx"])
    bottom_safe = int(framing["bottomSafePx"])

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
    title_color = _hex_to_rgb(tokens["visualStyle"]["title"]["textColor"], text_pri)

    labels = tokens["uiLabels"]
    customer = _norm_text(labels["customerLabel"])
    public_route = _norm_text(labels["publicRouteFallback"])
    manager_route = _norm_text(labels["managerRouteFallback"])
    catalog_title = _norm_text(labels["catalogSectionTitle"])
    team_title = _norm_text(labels["teamSectionTitle"])
    team_member = _norm_text(labels["teamMemberLabel"])
    unit_label = _norm_text(labels["itemUnitLabel"])
    bridge_caption = _norm_text(labels["journeyBridgeCaption"])
    agenda_date = _display_date((fixture.get("agenda") or {}).get("data"))
    booking_date = _display_date(booking_case.get("data") or agenda_date)

    kind = scene["kind"]
    if kind == "manager-agenda":
        cap_abs = os.path.join(root, base_capture_ref.replace("/", os.sep)) if base_capture_ref else None
        canvas = ns002_pilot._load_neutral_capture_backdrop(cap_abs, bg_top, bg_bot, width, height)
    else:
        canvas = _base_gradient(width, height, bg_top, bg_bot)

    surface_labels = {
        "public-booking": public_route,
        "manager-agenda": manager_route,
    }
    header_pill = surface_labels.get(scene.get("surface"), campaign_id)
    header_h = max(_draw_brand_header_generic(canvas, width, height, brand_kit, header_pill), top_safe)

    services_by_id = {s["id"]: s for s in fixture.get("servicos", [])}
    profs_by_id = {p["id"]: p for p in fixture.get("profissionais", [])}
    selected_service = None
    selected_prof = None
    if booking_case:
        selected_service = services_by_id.get(booking_case.get("servicoId"))
        selected_prof = profs_by_id.get(booking_case.get("profissionalId"))

    if kind == "hook-card":
        _draw_pill(canvas, width, height, 56, header_h + 70, _scene_text(scene, "badge"), 3,
                   secondary, text_pri, pad_x=24, pad_y=14)
        _draw_card(canvas, width, height, 56, header_h + 165, width - 56, header_h + 760,
                   card_bg, border_color=secondary, border_thickness=3, left_stripe_color=accent)
        lines = _wrap_text(_scene_text(scene, "headline"), width - 190, 6)
        ly = header_h + 235
        for line in lines:
            _draw_text(canvas, width, height, 102, ly, line, 6, title_color)
            ly += carousel_layout.char_height(6) + 22
        _fill_rect(canvas, width, height, 102, ly + 18, 360, ly + 26, accent)
        _draw_text(canvas, width, height, 102, ly + 56, _scene_text(scene, "subline"), 3, accent)
        steps = (
            _norm_text(labels["stepChooseTemplate"].replace("{customer}", customer)),
            _norm_text(labels["stepConfirmLabel"]),
            _norm_text(labels["stepAppearLabel"]),
        )
        step_w = (width - 112 - 32) // 3
        sy = header_h + 820
        for idx, label in enumerate(steps):
            sx = 56 + idx * (step_w + 16)
            _draw_card(canvas, width, height, sx, sy, sx + step_w, sy + 130, card_hi,
                       border_color=accent if idx == 2 else None)
            wlines = _wrap_text(label, step_w - 28, 3)
            ty = sy + 28
            for wl in wlines:
                _draw_text(canvas, width, height, sx + 16, ty, wl, 3, text_pri if idx < 2 else accent)
                ty += carousel_layout.char_height(3) + 10

    elif kind == "booking-selection":
        cy = _draw_surface_banner_generic(canvas, width, height, header_h + 36,
                                          _scene_text(scene, "badge"), _scene_text(scene, "headline"), palette)
        rota = fixture.get("booking", {}).get("rota", public_route)
        _draw_text(canvas, width, height, 56, cy, f"ROTA PUBLICA: {rota}", 3, text_mut)
        cy += 52
        _draw_text(canvas, width, height, 56, cy, catalog_title, 4, text_pri)
        cy += 44
        for srv in fixture.get("servicos", [])[:4]:
            is_sel = selected_service and srv["id"] == selected_service["id"]
            _draw_card(canvas, width, height, 56, cy, width - 56, cy + 122,
                       card_hi if is_sel else card_bg,
                       border_color=accent if is_sel else None, border_thickness=4)
            _draw_text(canvas, width, height, 84, cy + 24, srv["nome"], 4, accent if is_sel else text_pri)
            meta = f"{srv['duracaoMin']} MIN  -  {_format_price_brl(srv['precoBRL'])}"
            _draw_text(canvas, width, height, 84, cy + 70, meta, 3, text_mut)
            if is_sel:
                _draw_pill(canvas, width, height, width - 310, cy + 34, _norm_text(labels["selectedLabel"]), 3, accent, dark_ink,
                           pad_x=16, pad_y=10)
            cy += 136
        cy += 14
        _draw_text(canvas, width, height, 56, cy, team_title, 4, text_pri)
        cy += 44
        col_w = (width - 112 - 20) // 2
        for idx, prof in enumerate(fixture.get("profissionais", [])[:4]):
            col = idx % 2
            row = idx // 2
            px = 56 + col * (col_w + 20)
            py = cy + row * 124
            is_sel = selected_prof and prof["id"] == selected_prof["id"]
            _draw_card(canvas, width, height, px, py, px + col_w, py + 108,
                       card_hi if is_sel else card_bg,
                       border_color=accent if is_sel else None, border_thickness=4)
            _draw_text(canvas, width, height, px + 20, py + 22, prof["nome"], 3, accent if is_sel else text_pri)
            _draw_text(canvas, width, height, px + 20, py + 62, prof["especialidade"][:34], 2, text_mut)

    elif kind == "booking-confirm":
        cy = _draw_surface_banner_generic(canvas, width, height, header_h + 36,
                                          _scene_text(scene, "badge"), _scene_text(scene, "headline"), palette)
        _draw_text(canvas, width, height, 56, cy,
                   f"{_norm_text(labels['availabilityCaption'])} {public_route}", 2, text_mut)
        cy += 34
        _draw_card(canvas, width, height, 56, cy, width - 56, cy + 335, card_bg, border_color=secondary, border_thickness=2)
        _draw_text(canvas, width, height, 84, cy + 26, booking_date, 4, text_pri)
        if selected_prof and selected_service:
            _draw_text(canvas, width, height, 84, cy + 72, f"{selected_prof['nome']}  |  {selected_service['nome']}", 3, text_mut)
        slots = list(scene.get("availableSlots", ["09:00", "11:00", "14:00", "16:30"]))
        sel_slot = scene.get("selectedSlot", booking_case.get("horario") if booking_case else "09:00")
        slot_w = (width - 168 - 30) // 2
        for idx, slot in enumerate(slots[:4]):
            col = idx % 2
            row = idx // 2
            sx = 84 + col * (slot_w + 30)
            sy = cy + 126 + row * 94
            is_sel = slot == sel_slot
            slot_state = _norm_text(labels["selectedSlotLabel"] if is_sel else labels["availableSlotLabel"])
            label = f"{slot}  [{slot_state}]" if is_sel else f"{slot}  {slot_state}"
            _draw_card(canvas, width, height, sx, sy, sx + slot_w, sy + 76,
                       accent if is_sel else card_hi,
                       border_color=accent if is_sel else secondary, border_thickness=3)
            _draw_text(canvas, width, height, sx + 22, sy + 24, label, 3, dark_ink if is_sel else text_pri)
        cy += 365
        _draw_card(canvas, width, height, 56, cy, width - 56, cy + 350, card_bg, left_stripe_color=ok_col)
        _draw_text(canvas, width, height, 92, cy + 26, _norm_text(labels["summaryTitle"]), 4, accent)
        if booking_case:
            _draw_text(canvas, width, height, 92, cy + 84, f"{customer}: {booking_case.get('cliente', '-')}", 3, text_pri)
        if selected_service:
            _draw_text(canvas, width, height, 92, cy + 132,
                       f"{unit_label.upper()}: {selected_service['nome']} ({selected_service['duracaoMin']} MIN)",
                       3, text_pri)
        if selected_prof:
            _draw_text(canvas, width, height, 92, cy + 180, f"{team_member}: {selected_prof['nome']}", 3, text_pri)
        _draw_text(canvas, width, height, 92, cy + 228,
                   f"{_norm_text(labels['dateLabel'])}: {booking_date} "
                   f"{_norm_text(labels['atLabel'])} {sel_slot}", 3, ok_col)
        if selected_service:
            _draw_text(canvas, width, height, 92, cy + 286,
                       f"{_norm_text(labels['estimatedValueLabel'])} {unit_label}: "
                       f"{_format_price_brl(selected_service['precoBRL'])}", 3, text_mut)
        cy += 380
        _draw_card(canvas, width, height, 56, cy, width - 56, cy + 104, ok_col)
        cta_txt = _scene_text(scene, "ctaLabel") or _norm_text(labels["ctaConfirmLabel"])
        tw = _text_width(cta_txt, 5)
        _draw_text(canvas, width, height, (width - tw) // 2, cy + 32, cta_txt, 5, dark_ink)

    elif kind == "booking-success":
        _draw_pill(canvas, width, height, 56, header_h + 60, _scene_text(scene, "badge"), 3, ok_col, dark_ink,
                   pad_x=24, pad_y=14)
        _draw_card(canvas, width, height, 56, header_h + 150, width - 56, header_h + 860,
                   card_bg, border_color=ok_col, border_thickness=5, left_stripe_color=ok_col)
        _draw_pill(canvas, width, height, 102, header_h + 210,
                   f"{_norm_text(labels['statusLabel'])}: {_norm_text(labels['confirmedLabel'])}",
                   3, ok_col, dark_ink,
                   pad_x=20, pad_y=12)
        _draw_text(canvas, width, height, 102, header_h + 295, _norm_text(labels["successTitle"]), 6, text_pri)
        _draw_text(canvas, width, height, 102, header_h + 360, _norm_text(labels["successHighlight"]), 6, ok_col)
        _fill_rect(canvas, width, height, 102, header_h + 435, width - 102, header_h + 440, secondary)
        if booking_case:
            _draw_text(canvas, width, height, 102, header_h + 475, f"{customer}: {booking_case.get('cliente', '-')}", 4, text_pri)
        if selected_service:
            _draw_text(canvas, width, height, 102, header_h + 530,
                       f"{unit_label.upper()}: {selected_service['nome']}", 4, text_pri)
        if selected_prof:
            _draw_text(canvas, width, height, 102, header_h + 585,
                       f"{team_member}: {selected_prof['nome']}", 4, text_pri)
        _draw_text(canvas, width, height, 102, header_h + 640,
                   f"{_norm_text(labels['dateLabel'])}: {booking_date} "
                   f"{_norm_text(labels['atLabel'])} {booking_case.get('horario', '--:--')}", 4, accent)
        _draw_pill(canvas, width, height, 102, header_h + 735,
                   _scene_text(scene, "subline") or _norm_text(labels["visibleInPanelLabel"]), 3,
                   secondary, text_pri, pad_x=22, pad_y=14)

    elif kind == "manager-agenda":
        cy = _draw_surface_banner_generic(canvas, width, height, header_h + 28,
                                          _scene_text(scene, "badge"), _scene_text(scene, "headline"), palette)
        _draw_text(canvas, width, height, 56, cy,
                   f"{agenda_date} - {_norm_text(labels['managerCaption'])}", 3, text_mut)
        cy += 44
        highlight_id = scene.get("highlightId", "atend-001")
        for item in fixture.get("agenda", {}).get("atendimentos", [])[:6]:
            if cy + 132 > height - bottom_safe:
                break
            is_hi = item["id"] == highlight_id
            srv = services_by_id.get(item.get("servico"), {})
            prof = profs_by_id.get(item.get("profissional"), {})
            status = item.get("status", "")
            st_norm = _norm_text(status)
            if "CONCLUIDO" in st_norm:
                st_col = done_col
            elif "AGUARDANDO" in st_norm:
                st_col = wait_col
            else:
                st_col = ok_col
            _draw_card(canvas, width, height, 56, cy, width - 56, cy + 132,
                       card_hi if is_hi else card_bg,
                       border_color=accent if is_hi else secondary,
                       border_thickness=6 if is_hi else 1,
                       left_stripe_color=accent if is_hi else st_col)
            pill_pad_x = 14
            pill_w = _text_width(status, 3) + 2 * pill_pad_x
            pill_x = width - 56 - 20 - pill_w
            _draw_pill(canvas, width, height, pill_x, cy + 36, status, 3, st_col, dark_ink, pad_x=pill_pad_x, pad_y=10)
            top_line = f"{item.get('horario', '--:--')} ({item.get('duracaoMin', 0)}M) {item.get('cliente', '-')}"
            top_scale = 3 if _text_width(top_line, 3) <= (pill_x - 100) else 2
            _draw_text(canvas, width, height, 84, cy + 20, top_line, top_scale, accent if is_hi else text_pri)
            sub_line = f"{srv.get('nome', '-')} - {prof.get('nome', '-')}"
            sub_scale = 3 if _text_width(sub_line, 3) <= (pill_x - 100) else 2
            _draw_text(canvas, width, height, 84, cy + 70, sub_line, sub_scale, text_mut)
            cy += 148

    elif kind == "cta-card":
        _draw_pill(canvas, width, height, 56, header_h + 90, _scene_text(scene, "badge"), 4, accent, dark_ink,
                   pad_x=26, pad_y=16)
        _draw_card(canvas, width, height, 56, header_h + 200, width - 56, header_h + 900,
                   card_bg, border_color=accent, border_thickness=4, left_stripe_color=secondary)
        lines = _wrap_text(_scene_text(scene, "headline"), width - 190, 6)
        ly = header_h + 275
        for line in lines:
            _draw_text(canvas, width, height, 102, ly, line, 6, title_color)
            ly += carousel_layout.char_height(6) + 22
        _fill_rect(canvas, width, height, 102, ly + 22, 420, ly + 30, accent)
        domain_txt = _scene_text(scene, "subline") or brand_kit.get("domain", "")
        _draw_text(canvas, width, height, 102, ly + 72, domain_txt, 5, accent)
        _draw_text(canvas, width, height, 102, ly + 145, bridge_caption, 3, text_mut)
    else:
        raise build_video.DeliveryError(f"tipo de cena nao suportado (saas-demo): {kind}")

    return canvas


# ===========================================================================
# Renderizacao de frames - preset shorts-completo
# ===========================================================================
def _render_shorts_frame(scene: dict, brand_kit: dict, fixture: dict, root: str) -> Any:
    """Layout dinamico orientado a ritmo rapido de Shorts: cards de destaque,
    metricas/stems/projetos extraídos da fixture, barra de progresso e
    headerOverlay configuravel."""
    del root  # nao usamos captura externa no shorts-completo (graficos puros)
    palette = _brand_palette(brand_kit)
    width, height = OUTPUT_WIDTH, OUTPUT_HEIGHT
    tokens = resolve_visual_tokens(brand_kit, "9:16")
    framing = tokens["framing"]
    labels = tokens["uiLabels"]
    top_safe = int(framing["topSafePx"])
    bottom_safe = int(framing["bottomSafePx"])

    bg_top = _pal(palette, "backgroundTop")
    bg_bot = _pal(palette, "backgroundBottom")
    card_bg = _pal(palette, "cardBg")
    card_hi = _pal(palette, "cardHighlight")
    accent = _pal(palette, "primaryAccent")
    secondary = _pal(palette, "secondaryAccent")
    ok_col = _pal(palette, "statusConfirmed")
    text_pri = _pal(palette, "textPrimary")
    text_mut = _pal(palette, "textMuted")
    dark_ink = (14, 18, 28)
    title_color = _hex_to_rgb(tokens["visualStyle"]["title"]["textColor"], text_pri)

    canvas = _base_gradient(width, height, bg_top, bg_bot)
    header_h = max(_draw_brand_header_generic(canvas, width, height, brand_kit,
                                              scene.get("route", "/")), top_safe)
    kind = scene["kind"]

    if kind == "shorts-hook":
        _draw_pill(canvas, width, height, 56, header_h + 60, _scene_text(scene, "badge"), 3,
                   secondary, text_pri, pad_x=24, pad_y=14)
        lines = _wrap_text(_scene_text(scene, "headline"), width - 112, 6)
        ly = header_h + 130
        for line in lines:
            _draw_text(canvas, width, height, 56, ly, line, 6, title_color)
            ly += carousel_layout.char_height(6) + 18
        _draw_text(canvas, width, height, 56, ly + 26, _scene_text(scene, "subline") or brand_kit.get("domain", ""),
                   4, accent)
        _draw_text(canvas, width, height, 56, ly + 90, _scene_text(scene, "caption"), 3, text_mut)

    elif kind == "shorts-catalogo":
        cy = _draw_surface_banner_generic(canvas, width, height, header_h + 36,
                                          _scene_text(scene, "badge"), _scene_text(scene, "headline"), palette)
        projetos = list(fixture.get("projetos", []))[:3]
        card_h = 250
        gap = 20
        for proj in projetos:
            if cy + card_h > height - bottom_safe:
                break
            _draw_card(canvas, width, height, 56, cy, width - 56, cy + card_h, card_bg, border_color=secondary, border_thickness=2)
            _draw_text(canvas, width, height, 84, cy + 22,
                       proj.get("titulo", labels["itemUnitLabel"].capitalize()), 4, accent)
            meta = f"BPM {proj.get('bpm', '-')}  •  Tom {proj.get('tom', '-')}  •  {proj.get('compasso', '-')}  •  {proj.get('duracao', '-')}"
            _draw_text(canvas, width, height, 84, cy + 66, meta, 3, text_mut)
            _draw_text(canvas, width, height, 84, cy + 102,
                       f"{labels['referenceLabel']}: {proj.get('artistaReferencia', '-')}", 3, text_mut)
            stems = proj.get("stems", [])
            stem_txt = f"{labels['stemsLabel']}: " + ", ".join(stems)
            sy = cy + 138
            for line in _wrap_text(stem_txt, width - 168, 2):
                _draw_text(canvas, width, height, 84, sy, line, 2, text_mut)
                sy += carousel_layout.char_height(2) + 6
            _draw_text(canvas, width, height, 84, cy + card_h - 40, proj.get("formato", "WAV 48kHz / 24-bit"), 2, text_mut)
            _draw_pill(canvas, width, height, width - 260, cy + 24, proj.get("status", ""), 2, ok_col, dark_ink,
                       pad_x=10, pad_y=6)
            cy += card_h + gap

    elif kind == "shorts-metricas":
        cy = _draw_surface_banner_generic(canvas, width, height, header_h + 36,
                                          _scene_text(scene, "badge"), _scene_text(scene, "headline"), palette)
        projetos = list(fixture.get("projetos", []))
        rateios = list(fixture.get("rateios", []))
        total_stems = sum(len(p.get("stems", [])) for p in projetos)
        min_cota = min((float(r.get("cotaBRL") or 0) for r in rateios), default=0.0)
        metrics = [
            (f"{len(projetos)} {labels['projectsLabel']}", str(brand_kit.get("brandName", ""))),
            (f"{total_stems} {labels['stemsLabel']}", labels["stemsCaption"]),
            (f"{len(rateios)} {labels['sharesLabel']}",
             f"{labels['sharesFromLabel']} {_format_price_brl(min_cota)}"),
        ]
        col_w = (width - 112 - 40) // 3
        for idx, (big, small) in enumerate(metrics):
            sx = 56 + idx * (col_w + 20)
            _draw_card(canvas, width, height, sx, cy, sx + col_w, cy + 210, card_hi, border_color=accent, border_thickness=3)
            _draw_text(canvas, width, height, sx + 24, cy + 30, big, 5, dark_ink)
            _draw_text(canvas, width, height, sx + 24, cy + 100, small, 3, text_mut)
            _fill_rect(canvas, width, height, sx + 24, cy + 150, sx + col_w - 48, cy + 156, accent)
        # Barra de progresso inferior
        by = cy + 240
        _fill_rect(canvas, width, height, 56, by, width - 56, by + 16, (40, 50, 70))
        _fill_rect(canvas, width, height, 56, by, int((width - 112) * 0.72) + 56, by + 16, accent)
        _draw_text(canvas, width, height, 56, by + 30,
                   f"{labels['processingCaption']} - 72%", 3, text_mut)

    elif kind == "shorts-rateios":
        cy = _draw_surface_banner_generic(canvas, width, height, header_h + 36,
                                          _scene_text(scene, "badge"), _scene_text(scene, "headline"), palette)
        for rateio in list(fixture.get("rateios", []))[:4]:
            if cy + 150 > height - bottom_safe:
                break
            _draw_card(canvas, width, height, 56, cy, width - 56, cy + 150, card_bg, border_color=secondary, border_thickness=2)
            _draw_text(canvas, width, height, 84, cy + 18,
                       rateio.get("titulo", labels["shareUnitLabel"].capitalize()), 4, accent)
            _draw_text(canvas, width, height, 84, cy + 60,
                       f"{rateio.get('faixasInclusas', 0)} {labels['tracksLabel'].lower()}  •  "
                       f"{labels['shareUnitLabel'].lower()} {_format_price_brl(rateio.get('cotaBRL', 0))}",
                       3, text_pri)
            status = rateio.get("status", "")
            st_col = ok_col if status == "Aberto" else secondary
            _draw_pill(canvas, width, height, width - 250, cy + 20, status, 2, st_col, dark_ink, pad_x=10, pad_y=6)
            _draw_text(canvas, width, height, 84, cy + 100,
                       f"{labels['remainingSlotsLabel']}: {rateio.get('vagasRestantes', 0)}",
                       3, text_mut)
            _draw_text(canvas, width, height, 84, cy + 130,
                       f"{labels['routeLabel']}: {rateio.get('rota', labels['managerRouteFallback'])}",
                       2, text_mut)
            cy += 160

    elif kind == "shorts-cta":
        _draw_pill(canvas, width, height, 56, header_h + 80, _scene_text(scene, "badge"), 4, accent, dark_ink,
                   pad_x=26, pad_y=16)
        lines = _wrap_text(_scene_text(scene, "headline"), width - 190, 6)
        ly = header_h + 160
        for line in lines:
            _draw_text(canvas, width, height, 102, ly, line, 6, title_color)
            ly += carousel_layout.char_height(6) + 22
        domain_txt = _scene_text(scene, "subline") or brand_kit.get("domain", "")
        _draw_text(canvas, width, height, 102, ly + 40, domain_txt, 5, accent)
        _draw_text(canvas, width, height, 102, ly + 110, labels["linkCtaLabel"], 3, text_mut)
    else:
        raise build_video.DeliveryError(f"tipo de cena nao suportado (shorts-completo): {kind}")

    return canvas


# ===========================================================================
# Auditoria de guardrails (antes de qualquer render)
# ===========================================================================
def _audit_texts(texts: list[tuple[str, str]], guardrails: dict) -> list[str]:
    violations: list[str] = []
    for label, text in texts:
        if not text:
            continue
        found = tenant_validator.validate_text_against_guardrails(
            text, guardrails, check_ui_elements=True, ignore_editorial_footer=True
        )
        for v in found:
            violations.append(f"{label}: {v}")
    return violations


# ===========================================================================
# Pipeline principal
# ===========================================================================
def run_preset_pipeline(tenant_id: str, config_path: str, output_dir: str,
                        audio_path: str | None = None, root: str = ".") -> dict:
    """Executa o pipeline completo de um preset e devolve o manifesto."""
    root_real = os.path.realpath(root)
    render_local.ensure_video_tools(root_real)

    # 1. Ponto unico de entrada: carrega e valida o tenant (brandKit, guardrails, fixture).
    ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=root_real, strict=True)
    brand_kit = ctx["brandKit"]
    guardrails = ctx["guardrails"]
    fixture = ctx["fixture"]
    visual_tokens = resolve_visual_tokens(brand_kit, "9:16")
    ui_labels = visual_tokens["uiLabels"]

    # 2. Carrega o config da campanha.
    config_abs = (os.path.realpath(config_path) if os.path.isabs(config_path)
                  else os.path.realpath(os.path.join(root_real, config_path.replace("/", os.sep))))
    if not render_local.contained(root_real, config_abs):
        raise PresetRunnerError("CONFIG_FORA_DA_RAIZ: caminho do config esta fora da raiz do projeto")
    if not os.path.isfile(render_local.fs_path(config_abs)):
        raise PresetRunnerError(f"CONFIG_NAO_ENCONTRADO: {render_local.rel(root_real, config_abs)}")
    config = _load_json(config_abs)

    preset = config.get("preset") or brand_kit.get("defaultPreset") or PRESET_SAAS_DEMO
    if preset not in SUPPORTED_PRESETS:
        raise PresetRunnerError(f"PRESET_NAO_SUPORTADO: '{preset}' (suportados: {SUPPORTED_PRESETS})")

    fmt = config.get("format", {})
    width = int(fmt.get("width", OUTPUT_WIDTH))
    height = int(fmt.get("height", OUTPUT_HEIGHT))
    fps = int(fmt.get("fps", OUTPUT_FPS))
    duration = float(fmt.get("duration", 30.0))
    x264_preset = fmt.get("preset", "veryfast")
    subtitle_style = config.get("subtitleStyle") or brand_kit.get("subtitleStyle") or render_local.SUBTITLE_STYLE

    # 3. Guardrail de audio ANTES de qualquer render ou invocacao do FFmpeg.
    audio_policy = guardrails.get("audioPolicy", {})
    allow_audio = bool(audio_policy.get("allowAudioTrack", False))
    if audio_path is not None and not allow_audio:
        raise PresetRunnerError(
            "AUDIO_NAO_PERMITIDO: "
            f"tenant '{tenant_id}' tem allowAudioTrack=false; nao e possivel injetar trilha sonora. "
            "Use narracao externa (.txt) + .str e saida com -an."
        )
    expect_audio = 1 if allow_audio else 0

    # 4. Normaliza cenas e valida soma de duracoes.
    scenes = list(config.get("scenes", []))
    if not scenes:
        raise PresetRunnerError("CENAS_VAZIAS: o config da campanha deve definir pelo menos uma cena")
    cursor = 0.0
    for scene in scenes:
        if "start" in scene:
            cursor = float(scene["start"])
        else:
            scene["start"] = cursor
        scene["duration"] = float(scene.get("duration", 0.0))
        scene["end"] = scene["start"] + scene["duration"]
        cursor = scene["end"]
    sum_dur = round(sum(float(s["duration"]) for s in scenes), 3)
    if abs(sum_dur - duration) > 0.05:
        raise PresetRunnerError(f"SOMA_CENAS_DIVERGE: {sum_dur}s diverge de format.duration {duration}s")

    # 5. Auditoria de todos os textos (cenas + .srt + narracao) ANTES do render.
    base_capture_ref = config.get("baseCaptureRef")
    booking_case = config.get("bookingCase", {})
    campaign_id = config.get("campaignId", tenant_id)
    slug = _slug_from_config(config, tenant_id)

    scene_texts: list[tuple[str, str]] = []
    for scene in scenes:
        for key in ("badge", "headline", "subline", "caption", "ctaLabel", "narrationText", "route"):
            v = scene.get(key)
            if v:
                scene_texts.append((f"scene:{scene.get('id')}:{key}", str(v)))

    srt_text = build_srt_text(scenes)
    narration_text = build_narration_text(scenes, slug)

    ui_label_texts = [(f"uiLabels.{key}", val) for key, val in ui_labels.items()]
    texts_to_audit = scene_texts + ui_label_texts + [("srt", srt_text), ("narracao", narration_text)]
    violations = _audit_texts(texts_to_audit, guardrails)
    if violations:
        raise PresetRunnerError("GUARDRAIL_VIOLACAO: " + "; ".join(violations))

    # 6. Caminhos de saida (slug padronizado).
    output_abs = (os.path.realpath(output_dir) if os.path.isabs(output_dir)
                  else os.path.realpath(os.path.join(root_real, output_dir.replace("/", os.sep))))
    if not render_local.contained(root_real, output_abs):
        raise PresetRunnerError("OUTPUT_FORA_DA_RAIZ: output-dir esta fora da raiz do projeto")

    artifacts_cfg = config.get("artifacts", {})
    video_name = artifacts_cfg.get("videoName") or f"{slug}.mp4"
    srt_name = artifacts_cfg.get("packageSrtName") or f"{slug}.srt"
    narration_name = artifacts_cfg.get("packageNarrationName") or f"{slug}_narracao.txt"
    manifest_name = artifacts_cfg.get("manifestName") or "manifest.json"
    storyboard_name = artifacts_cfg.get("storyboardName") or "preview-storyboard.png"
    storyboard_timestamps = list(artifacts_cfg.get("storyboardTimestamps") or [2.0, 8.0, 16.0, 24.0])

    video_dest = os.path.join(output_abs, video_name)
    srt_dest = os.path.join(output_abs, srt_name)
    narration_dest = os.path.join(output_abs, narration_name)
    storyboard_dest = os.path.join(output_abs, storyboard_name)
    manifest_dest = os.path.join(output_abs, manifest_name)

    archive_dir = os.path.join(root_real, ".workspace", "archives", slug)
    archive_video_dest = os.path.join(archive_dir, video_name)

    staging_dir = os.path.join(root_real, ".workspace", "tmp", f"preset-runner-{slug}")
    if os.path.isdir(staging_dir):
        shutil.rmtree(staging_dir)
    os.makedirs(staging_dir, exist_ok=True)

    artifacts = {
        "video": {"staging": video_name, "dest": video_dest},
        "srt": {"staging": srt_name, "dest": srt_dest},
        "narration": {"staging": narration_name, "dest": narration_dest},
        "storyboard": {"staging": storyboard_name, "dest": storyboard_dest},
        "manifest": {"staging": manifest_name, "dest": manifest_dest},
    }
    staging_paths = {name: os.path.join(staging_dir, spec["staging"])
                     for name, spec in artifacts.items()}

    # ------------------------------------------------------------------
    # Render em staging
    # ------------------------------------------------------------------
    def render(paths: dict[str, str]) -> None:
        scenes_dir = os.path.join(staging_dir, "scenes")
        os.makedirs(render_local.fs_path(scenes_dir), exist_ok=True)
        scene_pngs: list[tuple[str, float]] = []
        for scene in scenes:
            if preset == PRESET_SAAS_DEMO:
                canvas = _render_saas_frame(scene, brand_kit, fixture, root_real,
                                            base_capture_ref, booking_case, campaign_id)
            else:
                canvas = _render_shorts_frame(scene, brand_kit, fixture, root_real)
            png_path = os.path.join(scenes_dir, f"{scene['id']}.png")
            with open(render_local.fs_path(png_path), "wb") as handle:
                handle.write(_encode_png(width, height, canvas))
            scene_pngs.append((png_path, float(scene["duration"])))

        render_local.write_text(paths["srt"], srt_text.replace("\r\n", "\n").rstrip("\n") + "\n")
        render_local.write_text(paths["narration"], narration_text.replace("\r\n", "\n").rstrip("\n") + "\n")

        cmd = _build_render_command(scene_pngs, paths["srt"], subtitle_style,
                                    width, height, fps, duration, x264_preset,
                                    allow_audio, audio_path, paths["video"])
        ok = build_video.run_cmd(cmd)
        if not ok:
            raise build_video.DeliveryError("renderizacao FFmpeg falhou")

        _build_storyboard_grid(paths["video"], storyboard_timestamps, paths["storyboard"])

        inspection = _probe_summary(paths["video"], width, height, fps, duration, expect_audio)
        manifest = {
            "schemaVersion": 1,
            "tenantId": tenant_id,
            "preset": preset,
            "brand": {
                "tenantId": brand_kit.get("tenantId"),
                "brandName": brand_kit.get("brandName"),
                "monogram": brand_kit.get("monogram"),
                "domain": brand_kit.get("domain"),
            },
            "uiLabels": {key: _norm_text(val) for key, val in ui_labels.items()},
            "visualStyle": visual_tokens["visualStyle"],
            "framing": visual_tokens["framing"],
            "guardrails": {
                "allowAudioTrack": allow_audio,
                "requireSrt": bool(audio_policy.get("requireSrt")),
                "requireExternalNarration": bool(audio_policy.get("requireExternalNarration")),
            },
            "config": render_local.rel(root_real, config_abs),
            "fixture": {
                "path": ctx["fixturePath"],
                "sha256": render_local.sha256_file(ctx["fixturePath"]),
            },
            "format": {
                "width": width, "height": height, "fps": fps, "duration": duration,
                "codec": "h264", "pixFmt": "yuv420p",
            },
            "audio": {
                "allowAudioTrack": allow_audio,
                "audioStream": expect_audio,
                "source": "external" if audio_path else ("anullsrc" if allow_audio else "none"),
            },
            "command": (
                f"python tools/preset_runner.py --tenant {tenant_id} "
                f"--config {render_local.rel(root_real, config_abs)} "
                f"--output-dir {render_local.rel(root_real, output_abs)}"
                + (f" --audio {render_local.rel(root_real, os.path.realpath(audio_path))}" if audio_path else "")
            ),
            "tools": {
                "ffmpeg": render_local.tool_version(build_video.get_ffmpeg()),
                "ffprobe": render_local.tool_version(build_video.get_ffprobe()),
            },
            "artifacts": {
                "video": {
                    "path": render_local.rel(root_real, video_dest),
                    "archivePath": render_local.rel(root_real, archive_video_dest),
                    "sha256": render_local.sha256_file(paths["video"]),
                    "bytes": os.path.getsize(render_local.fs_path(paths["video"])),
                    "ffprobe": inspection,
                    "versioned": False,
                    "reasonNotVersioned": ".gitignore versionado ignora *.mp4; manifesto preserva hash, ffprobe e comando reproduzivel",
                },
                "srt": {
                    "path": render_local.rel(root_real, srt_dest),
                    "sourcePath": config.get("artifacts", {}).get("srt"),
                    "sha256": render_local.sha256_file(paths["srt"]),
                    "bytes": os.path.getsize(render_local.fs_path(paths["srt"])),
                    "versioned": True,
                },
                "narration": {
                    "path": render_local.rel(root_real, narration_dest),
                    "sha256": render_local.sha256_file(paths["narration"]),
                    "bytes": os.path.getsize(render_local.fs_path(paths["narration"])),
                    "versioned": True,
                },
                "storyboard": {
                    "path": render_local.rel(root_real, storyboard_dest),
                    "timestampsSeconds": storyboard_timestamps,
                    "sha256": render_local.sha256_file(paths["storyboard"]),
                    "bytes": os.path.getsize(render_local.fs_path(paths["storyboard"])),
                    "width": width,
                    "height": height,
                    "versioned": True,
                },
            },
        }
        render_local.write_text(paths["manifest"], json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    # ------------------------------------------------------------------
    # Validacao dos artefatos em staging (antes de promover)
    # ------------------------------------------------------------------
    def validators(paths: dict[str, str]) -> None:
        errs = srt_validate.validate_srt_file(render_local.fs_path(paths["srt"]), duration)
        if errs:
            raise build_video.DeliveryError("SRT no pacote invalido: " + "; ".join(errs))
        with open(render_local.fs_path(paths["narration"]), "rb") as handle:
            if not handle.read().decode("utf-8").strip():
                raise build_video.DeliveryError("narracao vazia ou nao UTF-8")
        _probe_summary(paths["video"], width, height, fps, duration, expect_audio)
        probe_sb = build_video.probe_media(render_local.fs_path(paths["storyboard"]))
        sb_stream = probe_sb["streams"][0]
        if int(sb_stream.get("width", 0)) != width or int(sb_stream.get("height", 0)) != height:
            raise build_video.DeliveryError("storyboard com dimensoes inesperadas")

    build_video.transactional_export(staging_dir, artifacts, render, validators)

    # ------------------------------------------------------------------
    # Promocao ja feita pelo transactional_export; copia do MP4 para o arquivo.
    # ------------------------------------------------------------------
    os.makedirs(archive_dir, exist_ok=True)
    shutil.copyfile(render_local.fs_path(video_dest), render_local.fs_path(archive_video_dest))

    return _load_json(manifest_dest)


# ===========================================================================
# CLI
# ===========================================================================
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Motor generico multi-tenant de presets de video e audio (Agente 2 - Etapa 2)"
    )
    parser.add_argument("--tenant", required=True, help="Slug do tenant (marca-salao, meu-salao, multitrack-hub)")
    parser.add_argument("--config", required=True, help="Caminho para o JSON de configuracao da campanha")
    parser.add_argument("--output-dir", required=True, help="Diretorio de destino dos artefatos")
    parser.add_argument("--audio", default=None, help="Caminho para trilha de audio externa (somente se allowAudioTrack=true)")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument("--json", action="store_true", help="Emite o manifesto JSON no stdout")
    args = parser.parse_args(argv)

    try:
        manifest = run_preset_pipeline(
            args.tenant, args.config, args.output_dir,
            audio_path=args.audio, root=args.root,
        )
    except PresetRunnerError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except build_video.DeliveryError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro: entrada invalida ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        fmt = manifest.get("format", {})
        audio_streams = (
            manifest.get("artifacts", {}).get("video", {}).get("ffprobe", {}).get("audioStreams")
        )
        if audio_streams is None:
            audio_streams = manifest.get("audio", {}).get("audioStream", 0)
        print(f"Preset '{manifest['preset']}' renderizado para o tenant '{manifest['tenantId']}' "
              f"({fmt.get('width')}x{fmt.get('height')} "
              f"@{fmt.get('fps')}fps, "
              f"{audio_streams} stream(s) de audio).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
