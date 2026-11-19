"""Gerador de derivados multiformato das entregas 9:16 (Agente 1 - Etapa 4).

Parte dos MP4s verticais 9:16 (1080x1920 @ 30 fps) arquivados em
``.workspace/archives/<slug>/<slug>.mp4`` e dos respectivos
``02-reels-shorts/deliveries/<tenantId>/<slug>/manifest.json`` e
``tenants/<tenantId>/brand-kit.json`` para produzir, por campanha, em
``.workspace/archives/<slug>/derivatives/``:

  * ``<slug>-cover.png``  : frame representativo (segundo 2.0, ou metade da
                            duracao em fontes muito curtas) em 1080x1920 com
                            moldura sutil na cor primaria do brand-kit.
  * ``<slug>-1x1.mp4``    : 1080x1080, 30 fps, h264, yuv420p; fundo desfocado
                            (boxblur) e escurecido derivado do proprio video,
                            com leve tinta da cor primaria, e o video 9:16
                            centralizado em altura total (608x1080, escala
                            proporcional limpa), preservando a legenda queimada.
  * ``<slug>-16x9.mp4``   : 1920x1080, 30 fps, h264, yuv420p; mesma composicao
                            widescreen com o video 9:16 centralizado (608x1080).

Politica de audio estrita (sempre, antes de qualquer render):
    ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=REPO_ROOT, strict=True)
    guardrails.audioPolicy.allowAudioTrack == false (marca-salao, meu-salao,
    estudio-flow) -> saida forcada com ``-an`` (0 streams de audio).
    == true (multitrack-hub) -> trilha AAC original recodificada em
    44100 Hz stereo; fonte sem stream de audio e recusada.

Manifesto versionado por campanha em
``02-reels-shorts/deliveries/<tenantId>/<slug>/derivatives.json`` com
dimensoes, codecs, contagem de streams de audio, bytes e SHA-256 de cada
derivado (os .mp4/.png em si nao sao versionados: ``*.mp4`` esta no
``.gitignore`` e ``.workspace/`` e local da estacao).

Uso (a partir da raiz do checkout):
    python tools/derivative_formats.py --all --json
    python tools/derivative_formats.py --tenant marca-salao --json
    python tools/derivative_formats.py --tenant marca-salao --campaign camp-saas-demo-marca-salao-001

Uso programatico:
    from tools import derivative_formats
    manifest = derivative_formats.generate_derivatives(
        "marca-salao", "camp-saas-demo-marca-salao-001", root=REPO_ROOT)
    campaigns = derivative_formats.discover_campaigns(REPO_ROOT)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
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

COVER_TIMESTAMP = 2.0
COVER_MIN_DURATION = 2.5
BORDER_THICKNESS = 8
BORDER_INSET = 12
BORDER_ALPHA = 0.85

BG_FILTERS = "boxblur=20:2,eq=brightness=-0.2:saturation=0.9"
TINT_OPACITY = 0.12

X264_PRESET = "veryfast"
X264_CRF = "20"

AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 2
AUDIO_BITRATE = "128k"


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
def _composition_filter(canvas_w: int, canvas_h: int) -> str:
    """Fundo desfocado/escurecido do proprio video + tinta da paleta + 9:16 centralizado."""
    return ";".join([
        "[0:v]split=2[bgsrc][fgsrc]",
        (
            f"[bgsrc]scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=increase,"
            f"crop={canvas_w}:{canvas_h},{BG_FILTERS},format=yuv420p[bg0]"
        ),
        "[1:v]format=yuv420p[tint]",
        f"[bg0][tint]blend=all_mode=normal:all_opacity={TINT_OPACITY}[bg]",
        f"[fgsrc]scale={FG_WIDTH}:{FG_HEIGHT},format=yuv420p[fg]",
        "[bg][fg]overlay=(W-w)/2:0[out]",
    ])


def _render_cover(ffmpeg: str, source: str, output: str, timestamp: float,
                  border_hex: str) -> None:
    alpha = f"{round(BORDER_ALPHA * 255):02X}"
    vf = (
        f"drawbox=x={BORDER_INSET}:y={BORDER_INSET}"
        f":w=iw-{2 * BORDER_INSET}:h=ih-{2 * BORDER_INSET}"
        f":color={border_hex}{alpha}:t={BORDER_THICKNESS}"
    )
    _run([
        ffmpeg, "-y", "-ss", f"{timestamp:.3f}", "-i", source,
        "-frames:v", "1", "-vf", vf, "-frames:v", "1", output,
    ])


def _render_composition(ffmpeg: str, source: str, output: str, canvas_w: int, canvas_h: int,
                        tint_hex: str, duration: float, allow_audio: bool) -> None:
    fc = _composition_filter(canvas_w, canvas_h)
    cmd = [
        ffmpeg, "-y", "-i", source,
        "-f", "lavfi", "-i",
        f"color=c={tint_hex}:s={canvas_w}x{canvas_h}:r={OUTPUT_FPS}:d={duration:.3f}",
        "-filter_complex", fc, "-map", "[out]",
    ]
    if allow_audio:
        cmd += [
            "-map", "0:a:0",
            "-c:a", "aac", "-ar", str(AUDIO_SAMPLE_RATE),
            "-ac", str(AUDIO_CHANNELS), "-b:a", AUDIO_BITRATE,
        ]
    else:
        cmd += ["-an"]
    cmd += [
        "-c:v", "libx264", "-preset", X264_PRESET, "-crf", X264_CRF,
        "-pix_fmt", "yuv420p", "-r", str(OUTPUT_FPS),
        "-movflags", "+faststart", output,
    ]
    _run(cmd)


# ---------------------------------------------------------------------------
# Auditoria pos-render
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
    if problems:
        raise DerivativeFormatsError("AUDITORIA_DERIVADO", f"{label}: " + "; ".join(problems))


def _artifact_entry(path: str, root_real: str, probe: dict, extra: dict) -> dict:
    entry = {
        "path": render_local.rel(root_real, path),
        "sha256": render_local.sha256_file(path),
        "bytes": os.path.getsize(render_local.fs_path(path)),
        "ffprobe": probe,
        "versioned": False,
    }
    entry.update(extra)
    return entry


# ---------------------------------------------------------------------------
# Ponto de entrada programatico
# ---------------------------------------------------------------------------
def generate_derivatives(tenant_id: str, slug: str, root: str = ".") -> dict:
    """Gera cover + 1x1 + 16x9 de uma campanha e devolve o manifesto dos derivados."""
    root_real = os.path.realpath(root)
    render_local.ensure_video_tools(root_real)
    ffmpeg = build_video.get_ffmpeg()

    # 1. Contratos do tenant: brand-kit (paleta) e guardrails (politica de audio).
    ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=root_real, strict=True)
    brand_kit = ctx["brandKit"]
    audio_policy = ctx["guardrails"].get("audioPolicy", {})
    allow_audio = bool(audio_policy.get("allowAudioTrack", False))
    primary_hex = str(brand_kit.get("palette", {}).get("primary") or "#000000")
    primary_ff = _hex_color(primary_hex)

    # 2. Manifesto da entrega vigente (versionado).
    delivery_dir = os.path.join(root_real, "02-reels-shorts", "deliveries", tenant_id, slug)
    delivery_manifest_path = os.path.join(delivery_dir, "manifest.json")
    if not os.path.isfile(render_local.fs_path(delivery_manifest_path)):
        raise DerivativeFormatsError(
            "ENTREGA_NAO_ENCONTRADA",
            f"manifesto de entrega ausente: {render_local.rel(root_real, delivery_manifest_path)}",
        )
    delivery = _load_json(delivery_manifest_path)

    # 3. MP4 fonte 9:16 arquivado + validacao de geometria/audio.
    source_path = os.path.join(root_real, ".workspace", "archives", slug, f"{slug}.mp4")
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
    cover_ts = COVER_TIMESTAMP if duration >= COVER_MIN_DURATION else round(duration / 2.0, 3)

    # 4. Destinos dos derivados (arquivo local da estacao, nao versionado).
    derivatives_dir = os.path.join(root_real, ".workspace", "archives", slug, "derivatives")
    os.makedirs(render_local.fs_path(derivatives_dir), exist_ok=True)
    cover_path = os.path.join(derivatives_dir, f"{slug}-cover.png")
    square_path = os.path.join(derivatives_dir, f"{slug}-1x1.mp4")
    wide_path = os.path.join(derivatives_dir, f"{slug}-16x9.mp4")

    # 5. Renders (cover; composicoes 1x1 e 16x9 com fundo do proprio video).
    _render_cover(ffmpeg, source_path, cover_path, cover_ts, primary_ff)
    _render_composition(ffmpeg, source_path, square_path, SQUARE_WIDTH, SQUARE_HEIGHT,
                        primary_ff, duration, allow_audio)
    _render_composition(ffmpeg, source_path, wide_path, WIDE_WIDTH, WIDE_HEIGHT,
                        primary_ff, duration, allow_audio)

    # 6. Auditoria real via ffprobe antes de gravar qualquer manifesto.
    cover_probe = _probe_summary(build_video.probe_media(render_local.fs_path(cover_path)))
    square_probe = _probe_summary(build_video.probe_media(render_local.fs_path(square_path)))
    wide_probe = _probe_summary(build_video.probe_media(render_local.fs_path(wide_path)))
    _audit_derivative("cover", cover_probe, SOURCE_WIDTH, SOURCE_HEIGHT, allow_audio, duration)
    _audit_derivative("1x1", square_probe, SQUARE_WIDTH, SQUARE_HEIGHT, allow_audio, duration)
    _audit_derivative("16x9", wide_probe, WIDE_WIDTH, WIDE_HEIGHT, allow_audio, duration)

    # 7. Manifesto versionado com dimensoes, codecs, streams de audio, bytes e SHA-256.
    manifest = {
        "schemaVersion": 1,
        "tenantId": tenant_id,
        "slug": slug,
        "preset": delivery.get("preset"),
        "brand": {
            "tenantId": brand_kit.get("tenantId"),
            "brandName": brand_kit.get("brandName"),
            "monogram": brand_kit.get("monogram"),
            "domain": brand_kit.get("domain"),
            "palettePrimary": primary_hex,
        },
        "guardrails": {
            "allowAudioTrack": allow_audio,
            "requireSrt": bool(audio_policy.get("requireSrt")),
            "requireExternalNarration": bool(audio_policy.get("requireExternalNarration")),
            "appliedAudioPolicy": "aac-44100-stereo" if allow_audio else "-an",
        },
        "source": {
            "path": render_local.rel(root_real, source_path),
            "sha256": render_local.sha256_file(source_path),
            "bytes": os.path.getsize(render_local.fs_path(source_path)),
            "deliveryManifest": render_local.rel(root_real, delivery_manifest_path),
            "deliveryRecordedSha256": delivery.get("artifacts", {}).get("video", {}).get("sha256"),
            "ffprobe": _probe_summary(source_info),
        },
        "derivatives": {
            "cover": _artifact_entry(cover_path, root_real, cover_probe, {
                "kind": "cover-png",
                "codec": "png",
                "width": SOURCE_WIDTH,
                "height": SOURCE_HEIGHT,
                "timestampSeconds": cover_ts,
                "border": {
                    "color": primary_hex,
                    "thickness": BORDER_THICKNESS,
                    "inset": BORDER_INSET,
                    "alpha": BORDER_ALPHA,
                },
                "reasonNotVersioned": (
                    "derivados vivem em .workspace/archives/ (local da estacao); "
                    "o manifesto versionado preserva hash, geometria e comando reproduzivel"
                ),
            }),
            "square": _artifact_entry(square_path, root_real, square_probe, {
                "kind": "1x1",
                "width": SQUARE_WIDTH,
                "height": SQUARE_HEIGHT,
                "fps": OUTPUT_FPS,
                "codec": "h264",
                "pixFmt": "yuv420p",
                "foreground": {
                    "width": FG_WIDTH,
                    "height": FG_HEIGHT,
                    "position": "center-full-height",
                },
                "background": {
                    "source": "self",
                    "filters": BG_FILTERS,
                    "tint": primary_hex,
                    "tintOpacity": TINT_OPACITY,
                },
                "audioStreams": square_probe["audioStreams"],
                "audioCodec": square_probe["audioCodec"],
                "reasonNotVersioned": (
                    ".gitignore versionado ignora *.mp4; o manifesto versionado "
                    "preserva hash, ffprobe e comando reproduzivel"
                ),
            }),
            "wide": _artifact_entry(wide_path, root_real, wide_probe, {
                "kind": "16x9",
                "width": WIDE_WIDTH,
                "height": WIDE_HEIGHT,
                "fps": OUTPUT_FPS,
                "codec": "h264",
                "pixFmt": "yuv420p",
                "foreground": {
                    "width": FG_WIDTH,
                    "height": FG_HEIGHT,
                    "position": "center-full-height",
                },
                "background": {
                    "source": "self",
                    "filters": BG_FILTERS,
                    "tint": primary_hex,
                    "tintOpacity": TINT_OPACITY,
                },
                "audioStreams": wide_probe["audioStreams"],
                "audioCodec": wide_probe["audioCodec"],
                "reasonNotVersioned": (
                    ".gitignore versionado ignora *.mp4; o manifesto versionado "
                    "preserva hash, ffprobe e comando reproduzivel"
                ),
            }),
        },
        "command": (
            f"python tools/derivative_formats.py --tenant {tenant_id} --campaign {slug}"
        ),
        "tools": {
            "ffmpeg": render_local.tool_version(build_video.get_ffmpeg()),
            "ffprobe": render_local.tool_version(build_video.get_ffprobe()),
        },
    }
    derivatives_manifest_path = os.path.join(delivery_dir, "derivatives.json")
    render_local.write_text(
        derivatives_manifest_path,
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )
    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gerador de derivados multiformato 1:1/16:9/cover (Agente 1 - Etapa 4)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Processa todas as campanhas entregues")
    group.add_argument("--tenant", default=None, help="Slug do tenant (ex.: marca-salao)")
    parser.add_argument("--campaign", default=None, help="Slug da campanha (exige --tenant)")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument("--json", action="store_true", help="Emite metadados JSON no stdout")
    args = parser.parse_args(argv)

    if args.campaign is not None and args.tenant is None:
        print("Erro: --campaign exige --tenant", file=sys.stderr)
        return 2

    root_real = os.path.realpath(args.root)
    pairs = discover_campaigns(root_real, tenant_id=args.tenant, campaign=args.campaign)
    if not pairs:
        print(
            "Erro: NENHUMA_CAMPANHA: nenhuma entrega vigente corresponde ao filtro "
            f"(tenant={args.tenant!r}, campaign={args.campaign!r})",
            file=sys.stderr,
        )
        return 2

    results: list[dict] = []
    errors: list[dict] = []
    for tenant_id, slug in pairs:
        try:
            manifest = generate_derivatives(tenant_id, slug, root=root_real)
            results.append(manifest)
        except tenant_validator.TenantContractError as exc:
            errors.append({"tenantId": tenant_id, "slug": slug, "error": str(exc)})
        except DerivativeFormatsError as exc:
            errors.append({"tenantId": tenant_id, "slug": slug, "error": str(exc)})
        except build_video.DeliveryError as exc:
            errors.append({"tenantId": tenant_id, "slug": slug, "error": str(exc)})

    if args.json:
        print(json.dumps({
            "ok": not errors,
            "total": len(pairs),
            "generated": len(results),
            "campaigns": results,
            "errors": errors,
        }, ensure_ascii=False, indent=2))
    else:
        for manifest in results:
            derivs = manifest["derivatives"]
            audio_flag = "-an" if not manifest["guardrails"]["allowAudioTrack"] else "aac"
            print(
                f"Derivados de {manifest['slug']} ({manifest['tenantId']}, audio {audio_flag}): "
                f"cover {derivs['cover']['bytes']} B | "
                f"1x1 {derivs['square']['width']}x{derivs['square']['height']} "
                f"{derivs['square']['bytes']} B | "
                f"16x9 {derivs['wide']['width']}x{derivs['wide']['height']} "
                f"{derivs['wide']['bytes']} B"
            )
        for err in errors:
            print(f"Erro em {err['slug']}: {err['error']}", file=sys.stderr)
        print(f"Total: {len(results)} campanha(s) com derivados, {len(errors)} erro(s).")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
