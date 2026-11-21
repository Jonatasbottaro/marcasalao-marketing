"""Gerador de derivados multiformato das entregas 9:16 (Agente 1 - Etapa 4, rodada 2).

Parte dos MP4s verticais 9:16 (1080x1920 @ 30 fps) arquivados em
``.workspace/archives/<slug>/<slug>.mp4`` e dos respectivos contratos
``02-reels-shorts/deliveries/<tenantId>/<slug>/manifest.json``,
``tenants/<tenantId>/brand-kit.json`` e ``tenants/<tenantId>/guardrails.json``
para produzir, por campanha:

Em ``.workspace/archives/<slug>/derivatives/`` (local da estacao, nao versionado):

  * ``<slug>-1x1.mp4``          : 1080x1080, 30 fps, h264, yuv420p, crf 20; fundo
                                  desfocado e escurecido do proprio video
                                  (boxblur=24:4, eq=brightness=-0.18:saturation=0.85)
                                  e video 9:16 centralizado em altura total
                                  (608x1080, lanczos) com moldura lateral de 4 px
                                  na cor primaria do brand-kit (pad 616x1080),
                                  preservando a legenda queimada.
  * ``<slug>-16x9.mp4``         : 1920x1080, 30 fps, h264, yuv420p, crf 20; fundo
                                  widescreen (boxblur=28:5,
                                  eq=brightness=-0.22:saturation=0.80) com o mesmo
                                  primeiro plano 608x1080 e bordas de 4 px.
  * ``<slug>-cover.png``        : 1080x1920, frame hero em t=2.5 s com tarjas
                                  superior e inferior translucidas na paleta do
                                  tenant (fundo do brand-kit + linha de acento
                                  na cor primaria).
  * ``<slug>-thumb-16x9.png``   : 1920x1080, frame em t=2.5 s composto em 16:9
                                  (mesma composicao do derivado largo).
  * ``<slug>-preview-grid.png`` : 1920x1080, prancha comparativa 9:16 | 1:1 | 16:9
                                  extraida em t=2.5 s, altura uniforme de 540 px
                                  sobre fundo escuro da marca.

Na pasta versionada da entrega (``02-reels-shorts/deliveries/<tenantId>/<slug>/``):

  * ``cover.png``, ``thumb-16x9.png`` e ``preview-formats.png`` (previews leves);
  * ``derivatives.json`` (manifesto) com ``sourceVideoSha256``,
    ``allowAudioTrack`` e, por derivado (``1x1``, ``16x9``, ``cover``,
    ``thumb-16x9``, ``preview-formats``): caminho relativo, dimensoes, fps,
    codec, audioStreams, audioCodec, bytes e SHA-256. Nenhum caminho absoluto
    da estacao entra no manifesto; ``*.mp4`` segue ignorado pelo ``.gitignore``
    versionado.

Politica de audio estrita (sempre, antes de qualquer render):
    guardrails.audioPolicy.allowAudioTrack == false (marca-salao, meu-salao,
    estudio-flow) -> saida forcada com ``-an`` (0 streams de audio), mesmo que
    a fonte tenha trilha.
    == true (multitrack-hub) -> trilha AAC recodificada em 44100 Hz stereo
    (``-c:a aac -b:a 128k -ar 44100 -ac 2``); fonte sem stream de audio e
    recusada (FONTE_SEM_AUDIO).

Resolucao de ``.workspace/``: ``resolve_workspace_root(repo_root)`` tenta
``repo_root/.workspace`` e, em worktree sem ``.workspace/`` proprio, resolve o
checkout principal via ``git rev-parse --git-common-dir`` (pai do ``.git``
compartilhado) — os masters e os derivados vivem no ``.workspace/archives/``
do checkout principal. Ferramentas: ``build_video.get_ffmpeg()`` /
``build_video.get_ffprobe()`` com fallback para
``<MAIN_ROOT>/.workspace/tools/ffmpeg``.

Uso (a partir da raiz do checkout):
    python tools/derivative_formats.py --all [--formats 1x1,16x9,cover,thumb,grid] [--force] [--json]
    python tools/derivative_formats.py --tenant marca-salao [--campaign <slug>] [--json]
    python tools/derivative_formats.py --tenant marca-salao --campaign <slug> --archives-dir <dir>

``--archives-dir`` redireciona toda leitura/gravacao de MP4 arquivado para um
diretorio alternativo confinado a raiz (os testes usam um diretorio temporario
para nao alterar os masters compartilhados de ``.workspace/archives/``).

Uso programatico:
    from tools import derivative_formats
    result = derivative_formats.generate_campaign_derivatives(
        "marca-salao", "camp-saas-demo-marca-salao-001", root=REPO_ROOT)
    report = derivative_formats.generate_all_derivatives(root=REPO_ROOT)
    probe = derivative_formats.probe_media("video.mp4")
    campaigns = derivative_formats.discover_campaigns(REPO_ROOT)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import preset_runner
import render_local
import tenant_validator

OUTPUT_FPS = 30
SOURCE_WIDTH = 1080
SOURCE_HEIGHT = 1920

SQUARE_WIDTH = 1080
SQUARE_HEIGHT = 1080
WIDE_WIDTH = 1920
WIDE_HEIGHT = 1080

FG_WIDTH = 608
FG_HEIGHT = 1080
FG_PAD_WIDTH = 616
FG_PAD_EDGE = 4

FRAME_TIMESTAMP = 2.5
FRAME_MIN_DURATION = 2.75

COVER_TOP_BAR = 200
COVER_BOTTOM_BAR = 280
COVER_ACCENT = 8
BAR_ALPHA = 0.55
ACCENT_ALPHA = 0.95

GRID_PANEL_HEIGHT = 540
GRID_RAW_PANEL_WIDTH = 304
GRID_SQUARE_PANEL_WIDTH = 540
GRID_WIDE_PANEL_WIDTH = 960

X264_PRESET = "veryfast"
X264_CRF = "20"

AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 2
AUDIO_BITRATE = "128k"

SQUARE_BG_FILTERS = "boxblur=24:4,eq=brightness=-0.18:saturation=0.85"
WIDE_BG_FILTERS = "boxblur=28:5,eq=brightness=-0.22:saturation=0.80"

# Tokens aceitos em --formats -> chave canonica do manifesto.
CLI_FORMAT_TOKENS = {
    "1x1": "1x1",
    "16x9": "16x9",
    "cover": "cover",
    "thumb": "thumb-16x9",
    "grid": "preview-formats",
}
ALL_FORMATS = ("1x1", "16x9", "cover", "thumb-16x9", "preview-formats")

# Nome do derivado em .workspace/archives/<slug>/derivatives/ por formato.
ARCHIVE_NAMES = {
    "1x1": "{slug}-1x1.mp4",
    "16x9": "{slug}-16x9.mp4",
    "cover": "{slug}-cover.png",
    "thumb-16x9": "{slug}-thumb-16x9.png",
    "preview-formats": "{slug}-preview-grid.png",
}

# Nome da copia leve publicada na pasta versionada da entrega (imagens apenas).
VERSIONED_NAMES = {
    "cover": "cover.png",
    "thumb-16x9": "thumb-16x9.png",
    "preview-formats": "preview-formats.png",
}


class DerivativeFormatsError(Exception):
    """Falha controlada do gerador de derivados (codigo estavel + mensagem sanitizada)."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


# ---------------------------------------------------------------------------
# Infraestrutura de execucao
# ---------------------------------------------------------------------------
def _run(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    try:
        res = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise DerivativeFormatsError("FFMPEG_TIMEOUT", "comando de derivado excedeu o tempo limite") from exc
    except OSError as exc:
        raise DerivativeFormatsError("FFMPEG_NAO_EXECUTAVEL", str(exc)) from exc
    if res.returncode != 0:
        tail = (res.stderr or "").strip()[-400:]
        raise DerivativeFormatsError("FFMPEG_FALHOU", tail or f"codigo {res.returncode}")
    return res


def _load_json(path: str) -> dict:
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _hex_color(value: str) -> str:
    """Normaliza '#RRGGBB' do brand-kit para '0xRRGGBB' do FFmpeg."""
    return "0x" + str(value).strip().lstrip("#")


def _hex_alpha(hex_ff: str, alpha: float) -> str:
    """Anexa o byte de alpha a cor FFmpeg: '0xRRGGBB' + alpha -> '0xRRGGBBAA'."""
    return f"{hex_ff}{round(alpha * 255):02X}"


def _video_stream(info: dict) -> dict:
    return next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})


def _audio_stream(info: dict) -> dict | None:
    return next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)


def _fps(value: Any) -> float:
    raw = str(value or "0")
    if "/" in raw:
        num, _, den = raw.partition("/")
        den_f = float(den or 1)
        return float(num) / den_f if den_f else 0.0
    return float(raw)


def _probe_summary(info: dict) -> dict:
    v = _video_stream(info)
    a = _audio_stream(info)
    return {
        "videoStreams": sum(1 for s in info.get("streams", []) if s.get("codec_type") == "video"),
        "audioStreams": sum(1 for s in info.get("streams", []) if s.get("codec_type") == "audio"),
        "codec": v.get("codec_name"),
        "width": int(v.get("width", 0)),
        "height": int(v.get("height", 0)),
        "fps": round(_fps(v.get("avg_frame_rate")), 3),
        "pixFmt": v.get("pix_fmt"),
        "duration": round(float(info.get("format", {}).get("duration", 0.0)), 3),
        "audioCodec": a.get("codec_name") if a else None,
        "audioSampleRate": int(a.get("sample_rate", 0)) if a else None,
        "audioChannels": int(a.get("channels", 0)) if a else None,
    }


# ---------------------------------------------------------------------------
# Resolucao de .workspace/ e ferramentas (worktree -> checkout principal)
# ---------------------------------------------------------------------------
def _main_checkout_root(repo_root: str) -> str | None:
    """Raiz do checkout principal: pai do ``.git`` comum apontado pela worktree."""
    try:
        res = subprocess.run(
            ["git", "-C", repo_root, "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if res.returncode != 0:
        return None
    git_dir = os.path.normpath(os.path.join(repo_root, res.stdout.strip()))
    main_root = os.path.dirname(git_dir)
    return main_root if os.path.isdir(render_local.fs_path(main_root)) else None


def resolve_workspace_root(repo_root: str = ".") -> str:
    """Resolve o ``.workspace/`` aplicavel ao checkout desta tarefa.

    Tenta ``repo_root/.workspace`` (com ``archives/``) e, quando a tarefa roda em
    worktree sem ``.workspace/`` proprio, resolve o checkout principal via
    ``git rev-parse --git-common-dir`` (pai do ``.git`` compartilhado) e usa o
    ``.workspace/`` dele — e la que vivem os masters ``archives/<slug>/`` e os
    derivados quando o ``.workspace/`` gitignored nao foi checkado.
    """
    root_real = os.path.realpath(repo_root)
    candidate = os.path.join(root_real, ".workspace")
    if os.path.isdir(render_local.fs_path(os.path.join(candidate, "archives"))):
        return candidate

    main_root = _main_checkout_root(root_real)
    main_ws = os.path.join(main_root, ".workspace") if main_root else None
    if main_ws and os.path.isdir(render_local.fs_path(os.path.join(main_ws, "archives"))):
        return main_ws

    # Nenhum ``archives/`` em nenhum dos dois: devolve o que existir para que o
    # erro contratual seja FONTE_AUSENTE (e nao um crash de resolucao).
    if os.path.isdir(render_local.fs_path(candidate)):
        return candidate
    if main_ws and os.path.isdir(render_local.fs_path(main_ws)):
        return main_ws
    raise DerivativeFormatsError(
        "WORKSPACE_NAO_ENCONTRADO",
        "nem <raiz>/.workspace nem o .workspace do checkout principal existem",
    )


def resolve_archives_dir(repo_root: str, archives_dir: Path | str | None = None) -> str:
    """Raiz de archives da execucao (contem ``<slug>/<slug>.mp4``).

    ``None`` usa o ``.workspace/archives`` historico (worktree-aware). Um valor
    explicito e confinado a raiz do projeto; toda leitura/gravacao de MP4
    arquivado passa a ocorrer somente dentro dele.
    """
    root_real = os.path.realpath(repo_root)
    if archives_dir is None:
        return os.path.realpath(os.path.join(resolve_workspace_root(root_real), "archives"))
    raw = str(archives_dir)
    candidate = raw if os.path.isabs(raw) else os.path.join(root_real, raw.replace("/", os.sep))
    resolved = os.path.realpath(candidate)
    if not render_local.contained(root_real, resolved):
        raise DerivativeFormatsError(
            "ARCHIVES_FORA_DA_RAIZ",
            "archives-dir deve ficar sob a raiz do projeto",
        )
    if os.path.exists(render_local.fs_path(resolved)) and not os.path.isdir(render_local.fs_path(resolved)):
        raise DerivativeFormatsError("ARCHIVES_INVALIDO", "archives-dir nao e um diretorio")
    return resolved


def _ensure_tools(root_real: str) -> tuple[str, str]:
    """ffmpeg/ffprobe pelo PATH (build_video) com fallback em .workspace/tools/ffmpeg."""
    try:
        render_local.ensure_video_tools(root_real)
        return build_video.get_ffmpeg(), build_video.get_ffprobe()
    except build_video.DeliveryError:
        pass
    # Worktree sem .workspace/ proprio: ferramentas portateis do checkout principal.
    try:
        tools_dir = os.path.join(resolve_workspace_root(root_real), "tools", "ffmpeg")
    except DerivativeFormatsError:
        tools_dir = None
    if tools_dir:
        names = ("ffmpeg.exe", "ffprobe.exe") if os.name == "nt" else ("ffmpeg", "ffprobe")
        if all(os.path.isfile(render_local.fs_path(os.path.join(tools_dir, n))) for n in names):
            os.environ["PATH"] = tools_dir + os.pathsep + os.environ.get("PATH", "")
            return build_video.get_ffmpeg(), build_video.get_ffprobe()
    raise DerivativeFormatsError(
        "FFMPEG_NAO_EXECUTAVEL",
        "ffmpeg/ffprobe nao encontrados no PATH nem em .workspace/tools/ffmpeg",
    )


def probe_media(path: str, timeout: int | None = None) -> dict:
    """Sonda um media via ffprobe e devolve o resumo normalizado (geometria/codecs/audio)."""
    info = build_video.probe_media(render_local.fs_path(path), timeout=timeout)
    return _probe_summary(info)


# ---------------------------------------------------------------------------
# Descoberta de campanhas (entregas vigentes versionadas)
# ---------------------------------------------------------------------------
def discover_campaigns(root: str = ".", tenant_id: str | None = None,
                       campaign: str | None = None) -> list[tuple[str, str]]:
    """Lista ``(tenantId, slug)`` a partir dos manifestos de entrega versionados."""
    root_real = os.path.realpath(root)
    pattern = os.path.join(root_real, "02-reels-shorts", "deliveries", "*", "*", "manifest.json")
    pairs: list[tuple[str, str]] = []
    for manifest_path in sorted(glob.glob(pattern)):
        rel_parts = os.path.relpath(manifest_path, root_real).replace(os.sep, "/").split("/")
        tenant, slug = rel_parts[2], rel_parts[3]
        if tenant_id is not None and tenant != tenant_id:
            continue
        if campaign is not None and slug != campaign:
            continue
        pairs.append((tenant, slug))
    return pairs


# ---------------------------------------------------------------------------
# Comandos FFmpeg dos derivados
# ---------------------------------------------------------------------------
def _composition_filter(canvas_w: int, canvas_h: int, bg_filters: str, primary_ff: str,
                        in_label: str = "0:v", out_label: str = "out",
                        framing: dict | None = None) -> str:
    """Fundo desfocado + 9:16 centralizado, respeitando os insets do perfil.

    Os defaults de `framingByProfile` tem insets 0, preservando a geometria
    historica (608x1080, moldura de 4 px) e enquadrando o quadro inteiro.
    """
    top_inset = max(0, int((framing or {}).get("derivativeTopInsetPx", 0)))
    bottom_inset = max(0, int((framing or {}).get("derivativeBottomInsetPx", 0)))
    fg_height = max(1, canvas_h - top_inset - bottom_inset)
    fg_width = max(1, round(FG_WIDTH * fg_height / FG_HEIGHT))
    pad_width = fg_width + 2 * FG_PAD_EDGE
    return ";".join([
        f"[{in_label}]split=2[bgsrc][fgsrc]",
        (
            f"[bgsrc]scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=increase,"
            f"crop={canvas_w}:{canvas_h},{bg_filters},format=yuv420p[bg]"
        ),
        (
            f"[fgsrc]scale={fg_width}:{fg_height}:flags=lanczos,"
            f"pad={pad_width}:{fg_height}:{FG_PAD_EDGE}:0:{primary_ff},format=yuv420p[fg]"
        ),
        f"[bg][fg]overlay=(W-w)/2:{top_inset},format=yuv420p[{out_label}]",
    ])


def _audio_args(allow_audio: bool) -> list[str]:
    if allow_audio:
        return [
            "-map", "0:a:0", "-c:a", "aac", "-b:a", AUDIO_BITRATE,
            "-ar", str(AUDIO_SAMPLE_RATE), "-ac", str(AUDIO_CHANNELS),
        ]
    return ["-an"]


def _render_video(ffmpeg: str, source: str, output: str, canvas_w: int, canvas_h: int,
                  bg_filters: str, primary_ff: str, duration: float,
                  allow_audio: bool, framing: dict | None = None) -> None:
    cmd = [
        ffmpeg, "-y", "-i", source,
        "-filter_complex", _composition_filter(canvas_w, canvas_h, bg_filters, primary_ff,
                                               framing=framing),
        "-map", "[out]",
    ]
    cmd += _audio_args(allow_audio)
    cmd += [
        "-c:v", "libx264", "-preset", X264_PRESET, "-crf", X264_CRF,
        "-pix_fmt", "yuv420p", "-r", str(OUTPUT_FPS),
        "-movflags", "+faststart", output,
    ]
    _run(cmd, timeout=1800)


def _render_cover(ffmpeg: str, source: str, output: str, timestamp: float,
                  background_ff: str, primary_ff: str) -> None:
    """Frame hero com tarjas translucidas (fundo do tenant) e linhas de acento (primaria)."""
    bars = ",".join([
        f"drawbox=x=0:y=0:w=iw:h={COVER_TOP_BAR}:color={_hex_alpha(background_ff, BAR_ALPHA)}:t=fill",
        f"drawbox=x=0:y={COVER_TOP_BAR}:w=iw:h={COVER_ACCENT}:color={_hex_alpha(primary_ff, ACCENT_ALPHA)}:t=fill",
        f"drawbox=x=0:y=ih-{COVER_BOTTOM_BAR}:w=iw:h={COVER_BOTTOM_BAR}:color={_hex_alpha(background_ff, BAR_ALPHA)}:t=fill",
        f"drawbox=x=0:y=ih-{COVER_BOTTOM_BAR + COVER_ACCENT}:w=iw:h={COVER_ACCENT}:color={_hex_alpha(primary_ff, ACCENT_ALPHA)}:t=fill",
    ])
    _run([
        ffmpeg, "-y", "-ss", f"{timestamp:.3f}", "-i", source,
        "-vf", bars, "-frames:v", "1", output,
    ])


def _render_thumb(ffmpeg: str, source: str, output: str, timestamp: float,
                  primary_ff: str, framing: dict | None = None) -> None:
    """Frame em 16:9 composto (mesma composicao do derivado largo)."""
    _run([
        ffmpeg, "-y", "-ss", f"{timestamp:.3f}", "-i", source,
        "-filter_complex", _composition_filter(WIDE_WIDTH, WIDE_HEIGHT, WIDE_BG_FILTERS, primary_ff,
                                               framing=framing),
        "-map", "[out]", "-frames:v", "1", output,
    ])


def _render_grid(ffmpeg: str, source: str, output: str, timestamp: float,
                 background_ff: str, primary_ff: str, framing: dict | None = None) -> None:
    """Prancha comparativa 9:16 | 1:1 | 16:9 em altura uniforme sobre fundo da marca."""
    height = GRID_PANEL_HEIGHT
    panels = ";".join([
        "[0:v]split=3[raw][sqsrc][wdsrc]",
        (
            f"[raw]scale={GRID_RAW_PANEL_WIDTH}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={GRID_RAW_PANEL_WIDTH}:{height}:(ow-iw)/2:(oh-ih)/2:black,format=rgb24[p1]"
        ),
        _composition_filter(SQUARE_WIDTH, SQUARE_HEIGHT, SQUARE_BG_FILTERS, primary_ff,
                             in_label="sqsrc", out_label="sqcomp"),
        f"[sqcomp]scale={GRID_SQUARE_PANEL_WIDTH}:{height},format=rgb24[p2]",
        _composition_filter(WIDE_WIDTH, WIDE_HEIGHT, WIDE_BG_FILTERS, primary_ff,
                            in_label="wdsrc", out_label="wdcomp", framing=framing),
        f"[wdcomp]scale={GRID_WIDE_PANEL_WIDTH}:{height},format=rgb24[p3]",
        (
            f"[p1][p2][p3]hstack=inputs=3,"
            f"pad={WIDE_WIDTH}:{WIDE_HEIGHT}:(ow-iw)/2:(oh-ih)/2:{background_ff}[out]"
        ),
    ])
    _run([
        ffmpeg, "-y", "-ss", f"{timestamp:.3f}", "-i", source,
        "-filter_complex", panels, "-map", "[out]", "-frames:v", "1", output,
    ])


# ---------------------------------------------------------------------------
# Auditoria pos-render (ffprobe) antes de gravar qualquer manifesto
# ---------------------------------------------------------------------------
def _audit_derivative(label: str, probe: dict, width: int, height: int,
                      allow_audio: bool, duration: float) -> None:
    problems: list[str] = []
    if probe["width"] != width or probe["height"] != height:
        problems.append(f"geometria {probe['width']}x{probe['height']} (esperado {width}x{height})")
    if label in ("1x1", "16x9"):
        expect_audio = 1 if allow_audio else 0
        if probe["codec"] != "h264":
            problems.append(f"codec {probe['codec']} (esperado h264)")
        if probe["pixFmt"] != "yuv420p":
            problems.append(f"pix_fmt {probe['pixFmt']} (esperado yuv420p)")
        if abs(probe["fps"] - OUTPUT_FPS) > 0.01:
            problems.append(f"fps {probe['fps']} (esperado {OUTPUT_FPS})")
        if probe["audioStreams"] != expect_audio:
            problems.append(f"streams de audio {probe['audioStreams']} (esperado {expect_audio})")
        if allow_audio:
            if probe["audioCodec"] != "aac":
                problems.append(f"codec de audio {probe['audioCodec']} (esperado aac)")
            if probe["audioSampleRate"] != AUDIO_SAMPLE_RATE:
                problems.append(f"sample rate {probe['audioSampleRate']} (esperado {AUDIO_SAMPLE_RATE})")
            if probe["audioChannels"] != AUDIO_CHANNELS:
                problems.append(f"canais {probe['audioChannels']} (esperado {AUDIO_CHANNELS})")
        if abs(probe["duration"] - duration) > 0.5:
            problems.append(f"duracao {probe['duration']}s (fonte {duration}s)")
    else:
        if probe["codec"] != "png":
            problems.append(f"codec {probe['codec']} (esperado png)")
        if probe["audioStreams"] != 0:
            problems.append(f"streams de audio {probe['audioStreams']} (esperado 0)")
    if problems:
        raise DerivativeFormatsError("AUDITORIA_DERIVADO", f"{label}: " + "; ".join(problems))


# ---------------------------------------------------------------------------
# Manifesto versionado
# ---------------------------------------------------------------------------
def _format_entry(rel_path: str, abs_path: str, probe: dict, extra: dict) -> dict:
    is_video = probe["codec"] != "png"
    entry = {
        "path": rel_path,
        "width": probe["width"],
        "height": probe["height"],
        "fps": probe["fps"] if is_video else None,
        "codec": probe["codec"],
        "audioStreams": probe["audioStreams"],
        "audioCodec": probe["audioCodec"],
        "bytes": os.path.getsize(render_local.fs_path(abs_path)),
        "sha256": render_local.sha256_file(abs_path),
        "ffprobe": probe,
    }
    entry.update(extra)
    return entry


def _normalize_formats(formats: Any) -> tuple[str, ...]:
    if formats is None:
        return ALL_FORMATS
    if isinstance(formats, str):
        tokens = [t.strip() for t in formats.split(",") if t.strip()]
    else:
        tokens = [str(t).strip() for t in formats if str(t).strip()]
    keys: list[str] = []
    for token in tokens:
        key = CLI_FORMAT_TOKENS.get(token.lower())
        if key is None and token in ALL_FORMATS:
            key = token  # chave canonica repassada pela API programatica
        if key is None:
            raise DerivativeFormatsError(
                "FORMATO_INVALIDO",
                f"formato '{token}' nao reconhecido; use: {', '.join(CLI_FORMAT_TOKENS)}",
            )
        if key not in keys:
            keys.append(key)
    if not keys:
        raise DerivativeFormatsError("FORMATO_INVALIDO", "nenhum formato solicitado")
    return tuple(keys)


def _campaign_complete(manifest_path: str, derivatives_dir: str, delivery_dir: str,
                       requested: tuple[str, ...]) -> bool:
    """True quando o manifesto v2 em disco ja cobre os formatos pedidos com arquivos integros."""
    if not os.path.isfile(render_local.fs_path(manifest_path)):
        return False
    try:
        with open(render_local.fs_path(manifest_path), "r", encoding="utf-8") as handle:
            disk = json.load(handle)
    except (OSError, ValueError):
        return False
    if disk.get("schemaVersion") != 2:
        return False
    entries = disk.get("derivatives") or {}
    for key in requested:
        entry = entries.get(key)
        if not entry or not entry.get("path") or not entry.get("sha256"):
            return False
        abs_path = os.path.join(derivatives_dir, os.path.basename(entry["path"].replace("/", os.sep)))
        if not os.path.isfile(render_local.fs_path(abs_path)):
            return False
        if render_local.sha256_file(abs_path) != entry["sha256"]:
            return False
        if os.path.getsize(abs_path) != entry.get("bytes"):
            return False
        versioned_name = VERSIONED_NAMES.get(key)
        if versioned_name:
            versioned_abs = os.path.join(delivery_dir, versioned_name)
            if not os.path.isfile(render_local.fs_path(versioned_abs)):
                return False
            if render_local.sha256_file(versioned_abs) != entry["sha256"]:
                return False
    return True


# ---------------------------------------------------------------------------
# Geracao por campanha
# ---------------------------------------------------------------------------
def generate_campaign_derivatives(tenant_id: str, slug: str, root: str = ".",
                                  formats: Any = None, force: bool = False,
                                  archives_dir: Path | str | None = None) -> dict:
    """Gera os derivados de uma campanha e devolve o resultado com o manifesto gravado."""
    root_real = os.path.realpath(root)
    ffmpeg, _ffprobe_bin = _ensure_tools(root_real)

    # 1. Contratos do tenant: brand-kit (paleta) e guardrails (politica de audio).
    ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=root_real, strict=True)
    brand_kit = ctx["brandKit"]
    tokens_1x1 = preset_runner.resolve_visual_tokens(brand_kit, "1:1")
    tokens_16x9 = preset_runner.resolve_visual_tokens(brand_kit, "16:9")
    audio_policy = ctx["guardrails"].get("audioPolicy", {})
    allow_audio = bool(audio_policy.get("allowAudioTrack", False))
    palette = brand_kit.get("palette", {})
    primary_hex = str(palette.get("primary") or "#000000")
    background_hex = str(palette.get("background") or "#000000")
    primary_ff = _hex_color(primary_hex)
    background_ff = _hex_color(background_hex)
    applied_policy = "aac-44100-stereo" if allow_audio else "-an"

    # 2. Manifesto da entrega vigente (versionado).
    delivery_dir = os.path.join(root_real, "02-reels-shorts", "deliveries", tenant_id, slug)
    delivery_manifest_path = os.path.join(delivery_dir, "manifest.json")
    if not os.path.isfile(render_local.fs_path(delivery_manifest_path)):
        raise DerivativeFormatsError(
            "ENTREGA_NAO_ENCONTRADA",
            f"manifesto de entrega ausente: {render_local.rel(root_real, delivery_manifest_path)}",
        )
    delivery = _load_json(delivery_manifest_path)

    # 3. MP4 fonte 9:16 arquivado + validacao de geometria/audio/duracao.
    archives_root = resolve_archives_dir(root_real, archives_dir)
    source_path = os.path.join(archives_root, slug, f"{slug}.mp4")
    if not os.path.isfile(render_local.fs_path(source_path)):
        raise DerivativeFormatsError(
            "FONTE_AUSENTE",
            f"MP4 fonte ausente: {render_local.rel(root_real, source_path)}; "
            "regenere a entrega com a fabrica (tools/preset_runner.py / tools/factory_cli.py)",
        )
    source_info = build_video.probe_media(render_local.fs_path(source_path))
    source_v = _video_stream(source_info)
    if (int(source_v.get("width", 0)) != SOURCE_WIDTH
            or int(source_v.get("height", 0)) != SOURCE_HEIGHT):
        raise DerivativeFormatsError(
            "FONTE_GEOMETRIA_INVALIDA",
            f"esperado {SOURCE_WIDTH}x{SOURCE_HEIGHT} 9:16; observado "
            f"{source_v.get('width')}x{source_v.get('height')}",
        )
    source_a = _audio_stream(source_info)
    if allow_audio and source_a is None:
        raise DerivativeFormatsError(
            "FONTE_SEM_AUDIO",
            "allowAudioTrack=true exige trilha AAC na fonte, mas o MP4 nao tem stream de audio",
        )
    duration = float(source_info.get("format", {}).get("duration", 0.0))
    if duration <= 0:
        raise DerivativeFormatsError("FONTE_DURACAO_INVALIDA", f"duracao observada: {duration}s")
    frame_ts = FRAME_TIMESTAMP if duration >= FRAME_MIN_DURATION else round(duration / 2.0, 3)

    # 4. Formatos pedidos e destinos (derivados no diretorio de archives da execucao).
    requested = _normalize_formats(formats)
    derivatives_dir = os.path.join(archives_root, slug, "derivatives")
    manifest_path = os.path.join(delivery_dir, "derivatives.json")

    # Caminhos do manifesto permanecem canonicos (``.workspace/archives/...``)
    # no modo padrao, mesmo quando o checkout principal e resolvido de uma
    # worktree; com archives-dir explicito, usa-se o caminho relativo a raiz.
    archive_prefix = (
        ".workspace/archives" if archives_dir is None
        else render_local.rel(root_real, archives_root)
    )

    def _archive_rel(abs_path: str) -> str:
        inner = os.path.relpath(abs_path, archives_root).replace(os.sep, "/")
        return f"{archive_prefix}/{inner}"

    if not force and _campaign_complete(manifest_path, derivatives_dir, delivery_dir, requested):
        return {
            "tenantId": tenant_id,
            "slug": slug,
            "status": "skipped",
            "formats": list(requested),
            "allowAudioTrack": allow_audio,
            "appliedAudioPolicy": applied_policy,
            "manifestPath": render_local.rel(root_real, manifest_path),
        }

    os.makedirs(render_local.fs_path(derivatives_dir), exist_ok=True)

    # 5. Renders por formato + auditoria ffprobe antes de gravar qualquer manifesto.
    entries: dict[str, dict] = {}
    fg_meta = {
        "width": FG_WIDTH,
        "height": FG_HEIGHT,
        "padWidth": FG_PAD_WIDTH,
        "padEdge": FG_PAD_EDGE,
        "padColor": primary_hex,
        "position": "center-full-height",
        "scaler": "lanczos",
    }
    not_versioned_reason = (
        ".gitignore versionado ignora *.mp4; o manifesto versionado "
        "preserva hash, ffprobe e comando reproduzivel"
    )
    for key in requested:
        filename = ARCHIVE_NAMES[key].format(slug=slug)
        out_path = os.path.join(derivatives_dir, filename)
        rel_path = _archive_rel(out_path)
        if key == "1x1":
            _render_video(ffmpeg, source_path, out_path, SQUARE_WIDTH, SQUARE_HEIGHT,
                          SQUARE_BG_FILTERS, primary_ff, duration, allow_audio,
                          framing=tokens_1x1["framing"])
            probe = probe_media(out_path)
            _audit_derivative("1x1", probe, SQUARE_WIDTH, SQUARE_HEIGHT, allow_audio, duration)
            entries[key] = _format_entry(rel_path, out_path, probe, {
                "kind": "1x1",
                "pixFmt": "yuv420p",
                "foreground": dict(fg_meta),
                "background": {"source": "self", "filters": SQUARE_BG_FILTERS},
                "visualStyle": tokens_1x1["visualStyle"],
                "uiLabels": tokens_1x1["uiLabels"],
                "typography": tokens_1x1["typography"],
                "framing": tokens_1x1["framing"],
                "framingPreservedFullFrame": (
                    int(tokens_1x1["framing"]["derivativeTopInsetPx"]) == 0
                    and int(tokens_1x1["framing"]["derivativeBottomInsetPx"]) == 0
                ),
                "reasonNotVersioned": not_versioned_reason,
            })
        elif key == "16x9":
            _render_video(ffmpeg, source_path, out_path, WIDE_WIDTH, WIDE_HEIGHT,
                          WIDE_BG_FILTERS, primary_ff, duration, allow_audio,
                          framing=tokens_16x9["framing"])
            probe = probe_media(out_path)
            _audit_derivative("16x9", probe, WIDE_WIDTH, WIDE_HEIGHT, allow_audio, duration)
            entries[key] = _format_entry(rel_path, out_path, probe, {
                "kind": "16x9",
                "pixFmt": "yuv420p",
                "foreground": dict(fg_meta),
                "background": {"source": "self", "filters": WIDE_BG_FILTERS},
                "visualStyle": tokens_16x9["visualStyle"],
                "uiLabels": tokens_16x9["uiLabels"],
                "typography": tokens_16x9["typography"],
                "framing": tokens_16x9["framing"],
                "framingPreservedFullFrame": (
                    int(tokens_16x9["framing"]["derivativeTopInsetPx"]) == 0
                    and int(tokens_16x9["framing"]["derivativeBottomInsetPx"]) == 0
                ),
                "reasonNotVersioned": not_versioned_reason,
            })
        elif key == "cover":
            _render_cover(ffmpeg, source_path, out_path, frame_ts, background_ff, primary_ff)
            probe = probe_media(out_path)
            _audit_derivative("cover", probe, SOURCE_WIDTH, SOURCE_HEIGHT, allow_audio, duration)
            entries[key] = _format_entry(rel_path, out_path, probe, {
                "kind": "cover-png",
                "timestampSeconds": frame_ts,
                "bars": {
                    "top": {"height": COVER_TOP_BAR, "color": background_hex, "alpha": BAR_ALPHA},
                    "bottom": {"height": COVER_BOTTOM_BAR, "color": background_hex, "alpha": BAR_ALPHA},
                    "accent": {"thickness": COVER_ACCENT, "color": primary_hex, "alpha": ACCENT_ALPHA},
                },
            })
        elif key == "thumb-16x9":
            _render_thumb(ffmpeg, source_path, out_path, frame_ts, primary_ff,
                          framing=tokens_16x9["framing"])
            probe = probe_media(out_path)
            _audit_derivative("thumb-16x9", probe, WIDE_WIDTH, WIDE_HEIGHT, allow_audio, duration)
            entries[key] = _format_entry(rel_path, out_path, probe, {
                "kind": "thumb-16x9-png",
                "timestampSeconds": frame_ts,
            })
        else:  # preview-formats
            _render_grid(ffmpeg, source_path, out_path, frame_ts, background_ff, primary_ff,
                         framing=tokens_16x9["framing"])
            probe = probe_media(out_path)
            _audit_derivative("preview-formats", probe, WIDE_WIDTH, WIDE_HEIGHT,
                               allow_audio, duration)
            entries[key] = _format_entry(rel_path, out_path, probe, {
                "kind": "preview-grid-png",
                "timestampSeconds": frame_ts,
                "panels": {
                    "height": GRID_PANEL_HEIGHT,
                    "order": ["9:16", "1:1", "16:9"],
                    "background": background_hex,
                },
            })

    # 6. Previews leves versionados na pasta da entrega (imagens; .mp4 nunca).
    for key in requested:
        versioned_name = VERSIONED_NAMES.get(key)
        if not versioned_name:
            continue
        src_abs = os.path.join(derivatives_dir, ARCHIVE_NAMES[key].format(slug=slug))
        dst_abs = os.path.join(delivery_dir, versioned_name)
        shutil.copyfile(render_local.fs_path(src_abs), render_local.fs_path(dst_abs))
        if render_local.sha256_file(dst_abs) != entries[key]["sha256"]:
            raise DerivativeFormatsError(
                "PREVIEW_COPIA_DIVERGENTE",
                f"{key}: copia versionada diverge do derivado arquivado",
            )
        entries[key]["versionedCopy"] = render_local.rel(root_real, dst_abs)

    # 7. Manifesto versionado (v2; preserva entradas de formatos nao re-gerados).
    source_sha = render_local.sha256_file(source_path)
    existing: dict = {}
    if os.path.isfile(render_local.fs_path(manifest_path)):
        try:
            with open(render_local.fs_path(manifest_path), "r", encoding="utf-8") as handle:
                existing = json.load(handle)
        except (OSError, ValueError):
            existing = {}
    merged_entries = dict(existing.get("derivatives") or {}) \
        if existing.get("schemaVersion") == 2 else {}
    merged_entries.update(entries)

    manifest = {
        "schemaVersion": 2,
        "tenantId": tenant_id,
        "slug": slug,
        "preset": delivery.get("preset"),
        "sourceVideoSha256": source_sha,
        "allowAudioTrack": allow_audio,
        "appliedAudioPolicy": applied_policy,
        "source": {
            "path": _archive_rel(source_path),
            "sha256": source_sha,
            "bytes": os.path.getsize(render_local.fs_path(source_path)),
            "deliveryManifest": render_local.rel(root_real, delivery_manifest_path),
            "deliveryRecordedSha256": delivery.get("artifacts", {}).get("video", {}).get("sha256"),
            "ffprobe": _probe_summary(source_info),
        },
        "derivatives": merged_entries,
        "visualTokens": {
            "schemaVersion": 1,
            "visualStyle": tokens_1x1["visualStyle"],
            "uiLabels": tokens_1x1["uiLabels"],
            "typography": tokens_1x1["typography"],
            "framing": {"1:1": tokens_1x1["framing"], "16:9": tokens_16x9["framing"]},
            "framingPreservedFullFrame": True,
        },
        "command": (
            f"python tools/derivative_formats.py --tenant {tenant_id} --campaign {slug}"
            + (f" --archives-dir {render_local.rel(root_real, archives_root)}"
               if archives_dir is not None else "")
        ),
        "tools": {
            "ffmpeg": render_local.tool_version(build_video.get_ffmpeg()),
            "ffprobe": render_local.tool_version(build_video.get_ffprobe()),
        },
    }
    delivery_motion = delivery.get("motionPlan")
    if isinstance(delivery_motion, dict) and delivery_motion.get("schemaVersion") == 1:
        manifest["motionPlan"] = delivery_motion
    render_local.write_text(
        manifest_path,
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )
    return {
        "tenantId": tenant_id,
        "slug": slug,
        "status": "generated",
        "formats": list(requested),
        "allowAudioTrack": allow_audio,
        "appliedAudioPolicy": applied_policy,
        "sourceVideoSha256": source_sha,
        "derivatives": entries,
        "manifestPath": render_local.rel(root_real, manifest_path),
    }


# ---------------------------------------------------------------------------
# Geracao em lote (--all)
# ---------------------------------------------------------------------------
def generate_all_derivatives(root: str = ".", formats: Any = None,
                             force: bool = False,
                             archives_dir: Path | str | None = None) -> dict:
    """Gera os derivados de todas as campanhas vigentes; erros por campanha nao abortam o lote."""
    root_real = os.path.realpath(root)
    requested = _normalize_formats(formats)
    campaigns: list[dict] = []
    errors: list[dict] = []
    for tenant_id, slug in discover_campaigns(root_real):
        try:
            result = generate_campaign_derivatives(
                tenant_id, slug, root=root_real, formats=requested, force=force,
                archives_dir=archives_dir,
            )
            campaigns.append(result)
        except DerivativeFormatsError as exc:
            errors.append({"tenantId": tenant_id, "slug": slug, "error": str(exc), "code": exc.code})
        except tenant_validator.TenantContractError as exc:
            errors.append({"tenantId": tenant_id, "slug": slug, "error": str(exc), "code": "CONTRATO_TENANT"})
    generated = sum(1 for c in campaigns if c["status"] == "generated")
    skipped = sum(1 for c in campaigns if c["status"] == "skipped")
    return {
        "ok": not errors,
        "total": len(campaigns) + len(errors),
        "generated": generated,
        "skipped": skipped,
        "formats": list(requested),
        "campaigns": campaigns,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="derivative_formats.py",
        description="Gera derivados multiformato (1x1, 16x9, cover, thumb, grid) das entregas 9:16.",
    )
    parser.add_argument("--all", action="store_true",
                        help="processa todas as campanhas vigentes")
    parser.add_argument("--tenant", help="tenantId (ex.: marca-salao, multitrack-hub)")
    parser.add_argument("--campaign", help="slug da campanha (exige --tenant)")
    parser.add_argument("--formats", default=None,
                        help="lista separada por virgulas: 1x1,16x9,cover,thumb,grid")
    parser.add_argument("--force", action="store_true",
                        help="regenera mesmo com derivados integros em disco")
    parser.add_argument("--archives-dir", default=None,
                        help="raiz de archives alternativa (confinada ao projeto)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="saida JSON com relatorio completo")
    args = parser.parse_args(argv)

    root = os.getcwd()
    try:
        formats = _normalize_formats(args.formats)
    except DerivativeFormatsError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.all:
        report = generate_all_derivatives(
            root=root, formats=formats, force=args.force, archives_dir=args.archives_dir)
    elif args.tenant:
        pairs = discover_campaigns(root, tenant_id=args.tenant, campaign=args.campaign)
        if not pairs:
            print(
                f"nenhuma entrega vigente para tenant={args.tenant}"
                + (f" campaign={args.campaign}" if args.campaign else ""),
                file=sys.stderr,
            )
            return 2
        campaigns: list[dict] = []
        errors: list[dict] = []
        for tenant_id, slug in pairs:
            try:
                campaigns.append(generate_campaign_derivatives(
                    tenant_id, slug, root=root, formats=formats, force=args.force,
                    archives_dir=args.archives_dir,
                ))
            except DerivativeFormatsError as exc:
                errors.append({"tenantId": tenant_id, "slug": slug,
                               "error": str(exc), "code": exc.code})
            except tenant_validator.TenantContractError as exc:
                errors.append({"tenantId": tenant_id, "slug": slug,
                               "error": str(exc), "code": "CONTRATO_TENANT"})
        report = {
            "ok": not errors,
            "total": len(campaigns) + len(errors),
            "generated": sum(1 for c in campaigns if c["status"] == "generated"),
            "skipped": sum(1 for c in campaigns if c["status"] == "skipped"),
            "formats": list(formats),
            "campaigns": campaigns,
            "errors": errors,
        }
    else:
        parser.print_help()
        return 2

    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for result in report["campaigns"]:
            policy = result.get("appliedAudioPolicy", "?")
            if result["status"] == "skipped":
                print(
                    f"{result['slug']} ({result['tenantId']}, audio {policy}): "
                    "derivados ja integros; use --force para regerar"
                )
                continue
            derivs = result.get("derivatives") or {}
            summary = " | ".join(
                f"{key} {entry['width']}x{entry['height']} {entry['bytes']} B"
                for key, entry in derivs.items()
            )
            print(f"Derivados de {result['slug']} ({result['tenantId']}, audio {policy}): {summary}")
        for err in report["errors"]:
            print(f"Erro em {err['slug']}: {err['error']}", file=sys.stderr)
        print(
            f"Total: {report['generated']} campanha(s) gerada(s), "
            f"{report['skipped']} dispensada(s) por integridade, {len(report['errors'])} erro(s)."
        )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
