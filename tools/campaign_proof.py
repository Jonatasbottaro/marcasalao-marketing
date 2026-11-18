"""Ferramenta reutilizavel de prova de campanha para o Marca Salao.

Prepara, verifica, renderiza e gera pagina HTML portavel de revisao para
pedidos VideoRequest v1, reaproveitando os recursos existentes do Studio e do
pipeline de render (tools/produce_video.py, tools/render_pipeline.py,
tools/render_local.py, tools/carousel_layout.py, tools/make_proof_assets.py,
tools/build_video.py, tools/srt_validate.py).

Politica do projeto: video sem faixa de audio, sem rede, sem fornecedor e
sem TTS. Midias sinteticas sao marcadas visualmente ("PROVA FICTICIA") e
estruturalmente via metadado PNG (chunk tEXt), preservando sempre arquivos
fornecidos pelo operador.

Uso (a partir da raiz do checkout):
    python tools/campaign_proof.py run <pedido.json> --all-profiles --output-dir <dir>
    python tools/campaign_proof.py prepare <pedido.json> [--output-dir <dir>]
    python tools/campaign_proof.py verify <pedido.json>
    python tools/campaign_proof.py render <pedido.json> --profile <perfil> --output-dir <dir>
    python tools/campaign_proof.py review <pedido.json> [--delivery-dir <dir>] [--output <pagina.html>]

Com --json em qualquer subcomando, o resultado e emitido somente como JSON
no stdout. Codigos de saida: 0 sucesso; 1 pendencia/falha de entrega/render;
2 uso/caminho/JSON invalido; 3 contrato do pedido invalido.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import uuid
import zlib
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import carousel_layout
import make_proof_assets
import produce_video
import render_local
import srt_validate

VIDEO_REQUEST_SCHEMA_VERSION = 1
KEBAB_CASE_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
DEFAULT_LOCALE = "pt-BR"
DEFAULT_LICENSE = "pending"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SYNTHETIC_PROOF_MARKER = b"marcasalao-synthetic-proof"

_KEBAB_RE = re.compile(KEBAB_CASE_PATTERN)
_SAFE_SEGMENT_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


class ProofError(Exception):
    """Falha de prova com codigo estavel, assunto opcional e codigo de saida."""

    def __init__(self, code: str, subject: str | None = None, exit_code: int = 2):
        super().__init__(code)
        self.code = code
        self.subject = subject
        self.exit_code = exit_code


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_kebab(value: str | None) -> bool:
    return bool(isinstance(value, str) and _KEBAB_RE.match(value))


def total_duration_seconds(request: dict) -> float:
    """Retorna a duracao total em segundos com precisao de milissegundos."""
    total_ms = sum(
        int(s.get("durationMs", 0))
        for s in request.get("scenes", [])
        if isinstance(s, dict) and isinstance(s.get("durationMs"), (int, float))
    )
    return round(total_ms / 1000.0, 3)


def total_duration_s(request: dict) -> float:
    """Alias compativel retornando segundos com precisao decimal."""
    return total_duration_seconds(request)


def _resolve_contained(root: str, path_value: str, code: str = "CAMINHO_FORA_RAIZ") -> str:
    if not isinstance(path_value, str) or not path_value.strip():
        raise ProofError(code, str(path_value))
    norm = path_value.strip().replace("/", os.sep)
    candidate = norm if os.path.isabs(norm) else os.path.join(root, norm)
    resolved = os.path.realpath(candidate)
    if not render_local.contained(root, resolved):
        raise ProofError(code, path_value)
    return resolved


def _find_main_checkout_root(root: str) -> str:
    """Quando root aponta para worktree sob .workspace/worktrees/, localiza o checkout principal."""
    real = os.path.realpath(root)
    marker = os.sep + ".workspace" + os.sep + "worktrees" + os.sep
    if marker in real:
        candidate = real.split(marker, 1)[0]
        if os.path.isdir(candidate):
            return candidate
    return real


def _ensure_video_tools_for_root(root: str) -> tuple[bool, str | None]:
    """Verifica ffmpeg e ffprobe usando render_local.ensure_video_tools(root ou raiz principal)."""
    try:
        render_local.ensure_video_tools(root)
        return True, None
    except build_video.DeliveryError as exc:
        main_root = _find_main_checkout_root(root)
        if main_root != os.path.realpath(root):
            try:
                render_local.ensure_video_tools(main_root)
                return True, None
            except build_video.DeliveryError as inner_exc:
                return False, str(inner_exc)
        return False, str(exc)


def _is_synthetic_proof_file(abs_path: str) -> bool:
    """Detecta pela assinatura binaria do arquivo (sem confiar no JSON) se foi gerado pela prova."""
    fs = render_local.fs_path(abs_path)
    if not os.path.isfile(fs):
        return False
    try:
        with open(fs, "rb") as handle:
            head = handle.read(65536)
        return SYNTHETIC_PROOF_MARKER in head
    except OSError:
        return False


def _clean_label(text: str) -> str:
    return re.sub(r"[^A-Z0-9 .:/!?-]", "-", str(text).upper())


def _fill_rect(canvas: bytearray, width: int, height: int, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
    x0 = max(0, min(width, x0))
    x1 = max(x0, min(width, x1))
    y0 = max(0, min(height, y0))
    y1 = max(y0, min(height, y1))
    row_bytes = bytes(color) * (x1 - x0)
    for py in range(y0, y1):
        start = (py * width + x0) * 3
        canvas[start:start + len(row_bytes)] = row_bytes


def scene_palette(project_id: str, beat_id: str) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    digest = hashlib.sha256(f"{project_id}/{beat_id}".encode("utf-8")).digest()
    top = (36 + digest[0] % 130, 36 + digest[1] % 130, 48 + digest[2] % 130)
    bottom = (28 + digest[3] % 120, 32 + digest[4] % 120, 44 + digest[5] % 120)
    stripe = tuple(min(255, top[c] + 55) for c in range(3))
    return top, bottom, stripe


def write_scene_png(
    path: str,
    project_id: str,
    beat_id: str,
    order: int,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
) -> None:
    """Gera PNG sintetico rapido marcado visualmente e com chunk tEXt antes de IDAT."""
    top, bottom, stripe = scene_palette(project_id, beat_id)
    canvas = bytearray(width * height * 3)
    for y in range(height):
        ratio = y / (height - 1) if height > 1 else 0.0
        base = tuple(int(top[c] + (bottom[c] - top[c]) * ratio) for c in range(3))
        row_bytes = bytes(base) * width
        start = y * width * 3
        canvas[start:start + width * 3] = row_bytes

    bars = max(1, int(order))
    pitch = max(1, height // (bars + 1))
    for bar in range(1, bars + 1):
        cy = bar * pitch
        _fill_rect(canvas, width, height, 60, cy - 8, width - 60, cy + 8, stripe)

    # Faixa explicita identificando prova sintetica fora do titulo superior e das legendas inferiores
    pad_x = max(24, width // 18)
    badge_y0 = max(24, height // 4)
    badge_h = max(140, height // 9)
    _fill_rect(canvas, width, height, pad_x, badge_y0, width - pad_x, badge_y0 + badge_h, (18, 24, 34))
    _fill_rect(canvas, width, height, pad_x, badge_y0, width - pad_x, badge_y0 + 8, (245, 196, 0))

    scale_title = max(2, width // 180)
    scale_sub = max(2, width // 270)
    carousel_layout._draw_text(
        canvas, width, pad_x + 28, badge_y0 + 26,
        _clean_label("PROVA FICTICIA"), scale_title, (245, 196, 0), height=height,
    )
    carousel_layout._draw_text(
        canvas, width, pad_x + 28, badge_y0 + 26 + 11 * scale_title,
        _clean_label(f"{beat_id} / {project_id}"), scale_sub, (240, 244, 248), height=height,
    )

    raw = b"".join(
        b"\x00" + bytes(canvas[y * width * 3:(y + 1) * width * 3])
        for y in range(height)
    )
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    text_chunk = carousel_layout._png_chunk(b"tEXt", b"Software\x00" + SYNTHETIC_PROOF_MARKER)
    png = (
        PNG_SIGNATURE
        + carousel_layout._png_chunk(b"IHDR", ihdr)
        + text_chunk
        + carousel_layout._png_chunk(b"IDAT", zlib.compress(raw, 6))
        + carousel_layout._png_chunk(b"IEND", b"")
    )
    fs = render_local.fs_path(path)
    os.makedirs(os.path.dirname(fs), exist_ok=True)
    with open(fs, "wb") as handle:
        handle.write(png)


def _load_json(path: str, root: str, label: str) -> dict:
    abs_path = _resolve_contained(root, path, "ENTRADA_FORA_RAIZ")
    fs = render_local.fs_path(abs_path)
    if not os.path.isfile(fs):
        raise ProofError("ARQUIVO_AUSENTE", path)
    try:
        with open(fs, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProofError("JSON_INVALID", f"{label}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProofError("PEDIDO_INVALIDO", f"{label}: raiz nao e um objeto", exit_code=3)
    return data


def _collect_media(request: dict) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for entry in request.get("media", []):
        if isinstance(entry, dict) and isinstance(entry.get("id"), str) and entry["id"]:
            index[entry["id"]] = entry
    return index


def _basic_structural_checks(request: dict, root: str) -> list[ProofError]:
    """Checagem leve de integridade local e referencias basicas (sem duplicar todo schema TS)."""
    errors: list[ProofError] = []
    if request.get("schemaVersion") != VIDEO_REQUEST_SCHEMA_VERSION:
        errors.append(ProofError("SCHEMA_VERSION_UNSUPPORTED", str(request.get("schemaVersion")), exit_code=3))
    rid = request.get("id")
    if not _is_kebab(rid):
        errors.append(ProofError("ID_INVALID", str(rid), exit_code=3))
    proj = request.get("project")
    if not isinstance(proj, str) or not proj.strip():
        errors.append(ProofError("PROJECT_INVALID", str(proj), exit_code=3))
    else:
        norm = proj.strip().replace("/", os.sep)
        if os.path.isabs(norm) or not render_local.contained(root, os.path.realpath(os.path.join(root, norm))):
            errors.append(ProofError("PROJECT_OUTSIDE_ROOT", proj, exit_code=3))
    title = request.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append(ProofError("TITLE_INVALID", str(title), exit_code=3))

    profiles = request.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        errors.append(ProofError("PROFILES_EMPTY", None, exit_code=3))

    media_list = request.get("media")
    if not isinstance(media_list, list) or not media_list:
        errors.append(ProofError("MEDIA_EMPTY", None, exit_code=3))
        media_index: dict[str, dict] = {}
    else:
        media_index = {}
        for m in media_list:
            if not isinstance(m, dict) or not isinstance(m.get("id"), str) or not m["id"]:
                errors.append(ProofError("MEDIA_ITEM_INVALID", None, exit_code=3))
                continue
            if m["id"] in media_index:
                errors.append(ProofError("MEDIA_ID_DUPLICATE", m["id"], exit_code=3))
            media_index[m["id"]] = m
            mpath = m.get("path")
            if not isinstance(mpath, str) or not mpath.strip():
                errors.append(ProofError("MEDIA_PATH_INVALID", m["id"], exit_code=3))
            else:
                norm_m = mpath.strip().replace("/", os.sep)
                if os.path.isabs(norm_m) or not render_local.contained(root, os.path.realpath(os.path.join(root, norm_m))):
                    errors.append(ProofError("MEDIA_OUTSIDE_ROOT", m["id"], exit_code=3))

    scenes = request.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append(ProofError("SCENES_EMPTY", None, exit_code=3))
    else:
        for s in scenes:
            if not isinstance(s, dict) or not _is_kebab(s.get("id")):
                errors.append(ProofError("SCENE_ID_INVALID", str(s.get("id") if isinstance(s, dict) else None), exit_code=3))
                continue
            dur = s.get("durationMs")
            if isinstance(dur, bool) or not isinstance(dur, int) or dur <= 0:
                errors.append(ProofError("SCENE_DURATION_INVALID", s["id"], exit_code=3))
            mid = s.get("mediaId")
            if not isinstance(mid, str) or mid not in media_index:
                errors.append(ProofError("SCENE_MEDIA_REF_MISSING", f"{s.get('id')}:{mid}", exit_code=3))
    return errors


def _default_geometry_for_request(request: dict, compilation_profiles: list[dict] | None = None) -> tuple[int, int, int]:
    if compilation_profiles:
        for prof in compilation_profiles:
            plan = prof.get("outputPlan") or {}
            geom = plan.get("geometry") or {}
            if geom.get("width") and geom.get("height"):
                return int(geom["width"]), int(geom["height"]), int(plan.get("fps") or VIDEO_FPS)
    profiles = request.get("profiles") or []
    if profiles and "horizontal" in str(profiles[0]):
        return 1920, 1080, VIDEO_FPS
    return VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS


def cmd_prepare(
    request_path: str,
    output_dir: str | None = None,
    root: str = ".",
    force: bool = False,
) -> dict:
    """Prepara midia sintetica em media[].path preservando arquivos reais de operador."""
    root = os.path.realpath(root)
    request = _load_json(request_path, root, "pedido")
    errors = _basic_structural_checks(request, root)
    if errors:
        return {
            "ok": False,
            "operation": "prepare",
            "contractInvalid": True,
            "request": request_path,
            "errors": [{"code": e.code, "subject": e.subject} for e in errors],
        }

    abs_output = None
    if output_dir:
        abs_output = _resolve_contained(root, output_dir, "SAIDA_FORA_RAIZ")
        os.makedirs(render_local.fs_path(abs_output), exist_ok=True)

    duration_by_media: dict[str, int] = {}
    for scene in request.get("scenes", []):
        mid = scene.get("mediaId")
        duration_by_media[mid] = max(duration_by_media.get(mid, 0), int(scene.get("durationMs", 0)))

    tools_ready, tools_err = _ensure_video_tools_for_root(root)
    width, height, _fps = _default_geometry_for_request(request)
    project_id = request["id"]

    prepared: list[dict] = []
    preserved_operator: list[str] = []
    synthetic_files: list[str] = []
    prepare_errors: list[dict] = []

    for idx, media in enumerate(request.get("media", []), start=1):
        media_id = media["id"]
        declared_path = media["path"]
        target_abs = _resolve_contained(root, declared_path, "MEDIA_OUTSIDE_ROOT")
        rel_asset = render_local.rel(root, target_abs)
        exists = os.path.isfile(render_local.fs_path(target_abs))
        is_proof = _is_synthetic_proof_file(target_abs) if exists else False

        if exists and not is_proof and not force:
            status = "preserved_operator_media"
            synthetic = False
            preserved_operator.append(rel_asset)
        else:
            mtype = media.get("type", "image")
            if mtype == "image":
                write_scene_png(target_abs, project_id, media_id, idx, width=width, height=height)
                status = "regenerated_synthetic" if exists else "generated_synthetic"
                synthetic = True
                synthetic_files.append(rel_asset)
            elif mtype == "video":
                if not tools_ready:
                    prepare_errors.append({
                        "code": "FFMPEG_AUSENTE_PARA_VIDEO",
                        "subject": f"{media_id}: {tools_err}",
                    })
                    continue
                dur_s = max(2.0, duration_by_media.get(media_id, 2000) / 1000.0 + 0.5)
                os.makedirs(os.path.dirname(render_local.fs_path(target_abs)), exist_ok=True)
                make_proof_assets.write_scene_mp4(
                    render_local.fs_path(target_abs), project_id, media_id, idx, duration_s=dur_s,
                )
                status = "regenerated_synthetic" if exists else "generated_synthetic"
                synthetic = True
                synthetic_files.append(rel_asset)
            else:
                prepare_errors.append({"code": "TIPO_MEDIA_NAO_SUPORTADO", "subject": str(mtype)})
                continue

        prepared.append({
            "mediaId": media_id,
            "mediaPath": declared_path,
            "generatedAsset": rel_asset,
            "type": media.get("type", "image"),
            "origin": media.get("origin", "synthetic-demo"),
            "license": media.get("license", DEFAULT_LICENSE),
            "synthetic": synthetic,
            "status": status,
            "sha256": render_local.sha256_file(target_abs) if os.path.isfile(render_local.fs_path(target_abs)) else None,
        })

    if prepare_errors:
        return {
            "ok": False,
            "operation": "prepare",
            "request": request_path,
            "requestId": request["id"],
            "errors": prepare_errors,
            "mediaPrepared": prepared,
        }

    total_ms = sum(int(s.get("durationMs", 0)) for s in request.get("scenes", []))
    report = {
        "ok": True,
        "operation": "prepare",
        "request": request_path,
        "requestId": request["id"],
        "project": request["project"],
        "outputDir": output_dir,
        "mediaPrepared": prepared,
        "syntheticMedia": synthetic_files,
        "operatorMedia": preserved_operator,
        "sceneCount": len(request.get("scenes", [])),
        "totalDurationMs": total_ms,
        "totalDurationSeconds": total_duration_seconds(request),
        "preparedAt": _now_iso(),
    }
    if abs_output:
        report_path = os.path.join(abs_output, "prepare-report.json")
        with open(render_local.fs_path(report_path), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
    return report


def cmd_verify(request_path: str, root: str = ".") -> dict:
    """Valida arquivos fisicos e compila via ponte oficial da platform."""
    root = os.path.realpath(root)
    abs_request = _resolve_contained(root, request_path, "ENTRADA_FORA_RAIZ")
    request = _load_json(request_path, root, "pedido")

    structural_errors = _basic_structural_checks(request, root)
    structural_valid = len(structural_errors) == 0

    project_rel = request.get("project") if isinstance(request.get("project"), str) else ""
    project_exists = False
    if project_rel:
        try:
            proj_abs = _resolve_contained(root, project_rel, "PROJECT_OUTSIDE_ROOT")
            project_exists = os.path.isfile(render_local.fs_path(proj_abs))
        except ProofError as exc:
            structural_errors.append(exc)
            structural_valid = False

    blocking_errors = [{"code": e.code, "subject": e.subject} for e in structural_errors]
    if not project_exists and project_rel:
        blocking_errors.append({"code": "PROJECT_MANIFEST_AUSENTE", "subject": project_rel})

    scenes = request.get("scenes") if isinstance(request.get("scenes"), list) else []
    media_index = _collect_media(request) if isinstance(request.get("media"), list) else {}

    missing_media_refs = [
        s.get("mediaId") for s in scenes
        if isinstance(s, dict) and s.get("mediaId") not in media_index
    ]
    missing_media_files: list[str] = []
    synthetic_media: list[str] = []
    operator_media: list[str] = []

    for media_id, item in media_index.items():
        mpath = item.get("path", "")
        try:
            abs_media = _resolve_contained(root, mpath, "MEDIA_OUTSIDE_ROOT")
        except ProofError:
            missing_media_files.append(f"{media_id}:{mpath}")
            continue
        if not os.path.isfile(render_local.fs_path(abs_media)):
            missing_media_files.append(mpath)
        else:
            rel_media = render_local.rel(root, abs_media)
            is_synth_file = _is_synthetic_proof_file(abs_media) or (
                item.get("type") == "video" and str(item.get("origin", "")).startswith("synthetic-")
            )
            if is_synth_file:
                synthetic_media.append(rel_media)
            else:
                operator_media.append(rel_media)

    if missing_media_files:
        blocking_errors.append({
            "code": "MEDIA_FILES_MISSING",
            "subject": ", ".join(missing_media_files),
        })

    # Compilacao real via platform (render_bridge.mjs)
    compilation_executed = False
    compilation_valid = False
    compiled_profiles: list[dict] = []
    bridge_warnings: list[dict] = []

    if project_exists:
        try:
            verdict = produce_video.run_bridge_video_request(root, abs_request)
            compilation_executed = True
            if verdict.get("ok"):
                compiled_profiles = [
                    produce_video.preview_profile(p)
                    for p in verdict.get("profiles", [])
                ]
                all_compiled = all(p.get("status") == "compiled" for p in compiled_profiles) and bool(compiled_profiles)
                compilation_valid = all_compiled
                for p in compiled_profiles:
                    for w in p.get("warnings", []):
                        bridge_warnings.append(w)
                    if p.get("status") != "compiled":
                        blocking_errors.append({
                            "code": p.get("failureCode") or "PROFILE_COMPILE_FAILED",
                            "subject": p.get("profileId"),
                        })
            else:
                compilation_valid = False
                blocking_errors.append({
                    "code": verdict.get("failureCode") or "VIDEO_REQUEST_INVALID",
                    "subject": verdict.get("subject"),
                })
        except render_local.InputFileError as exc:
            msg = str(exc)
            if "node nao encontrado" in msg:
                code = "NODE_AUSENTE"
            elif "build da platform ausente" in msg:
                code = "PLATFORM_BUILD_AUSENTE"
            else:
                code = "PEDIDO_JSON_INVALIDO"
            blocking_errors.append({"code": code, "subject": msg})
        except build_video.DeliveryError as exc:
            blocking_errors.append({"code": "PONTE_COMPILACAO_FALHOU", "subject": str(exc)})

    tools_ready, tools_err = _ensure_video_tools_for_root(root)
    media_ready = not missing_media_refs and not missing_media_files and len(media_index) > 0
    preflight_ready = structural_valid and project_exists and media_ready and compilation_executed and compilation_valid
    total_ms = sum(
        int(s.get("durationMs", 0)) for s in scenes
        if isinstance(s, dict) and isinstance(s.get("durationMs"), (int, float))
    )
    width, height, fps = _default_geometry_for_request(request)
    if compiled_profiles and compiled_profiles[0].get("geometry"):
        geom = compiled_profiles[0]["geometry"]
        width = int(geom.get("width", width))
        height = int(geom.get("height", height))
        fps = int(compiled_profiles[0].get("fps") or fps)

    contract_invalid = (not structural_valid) or (compilation_executed and not compilation_valid)

    return {
        "ok": preflight_ready,
        "operation": "verify",
        "request": request_path,
        "requestId": request.get("id"),
        "project": project_rel,
        "title": request.get("title"),
        "locale": request.get("locale", DEFAULT_LOCALE),
        "profiles": request.get("profiles", []) if isinstance(request.get("profiles"), list) else [],
        "compiledProfiles": compiled_profiles,
        "geometry": f"{width}x{height}",
        "fps": fps,
        "sceneCount": len(scenes),
        "totalDurationMs": total_ms,
        "totalDurationSeconds": total_duration_seconds(request),
        "mediaCount": len(media_index),
        "missingMediaReferences": missing_media_refs,
        "missingMediaFiles": missing_media_files,
        "syntheticMedia": synthetic_media,
        "operatorMedia": operator_media,
        "structuralValid": structural_valid,
        "projectManifestValid": project_exists,
        "mediaReady": media_ready,
        "compilationExecuted": compilation_executed,
        "compilationValid": compilation_valid,
        "preflightReady": preflight_ready,
        "renderToolsReady": tools_ready,
        "renderToolsMessage": tools_err,
        "ready": preflight_ready,
        "contractInvalid": contract_invalid,
        "errors": blocking_errors,
        "warnings": bridge_warnings,
        "verifiedAt": _now_iso(),
    }


def _read_index_profile_state(abs_output: str, profile: str) -> tuple[dict | None, dict | None]:
    idx_path = render_local.fs_path(os.path.join(abs_output, "index.json"))
    if not os.path.isfile(idx_path):
        return None, None
    try:
        with open(idx_path, "r", encoding="utf-8") as handle:
            idx_data = json.load(handle)
    except (OSError, ValueError):
        return None, None
    for entry in idx_data.get("profiles", []):
        if isinstance(entry, dict) and entry.get("profileId") == profile:
            return entry.get("lastAttempt"), entry.get("lastValidDelivery")
    return None, None


def cmd_render(
    request_path: str,
    profile: str,
    output_dir: str,
    root: str = ".",
) -> dict:
    """Executa o render via tools/produce_video.py rastreando tentativa atual e preservando valida."""
    root = os.path.realpath(root)
    abs_request = _resolve_contained(root, request_path, "ENTRADA_FORA_RAIZ")
    abs_output = _resolve_contained(root, output_dir, "SAIDA_FORA_RAIZ")
    request = _load_json(request_path, root, "pedido")

    tools_ready, tools_err = _ensure_video_tools_for_root(root)
    _, prior_valid = _read_index_profile_state(abs_output, profile)

    result: dict = {
        "ok": False,
        "operation": "render",
        "request": request_path,
        "requestId": request.get("id"),
        "profile": profile,
        "outputDir": render_local.rel(root, abs_output),
        "ffmpegAvailable": tools_ready,
    }
    if prior_valid:
        result["preservedLastValidDelivery"] = prior_valid

    if not tools_ready:
        result["status"] = "pendente_ferramenta"
        result["error"] = tools_err or "ffmpeg/ffprobe nao encontrados; exponha no PATH ou em .workspace/tools/ffmpeg"
        result["comandoRetomada"] = (
            f"python tools/produce_video.py --input {request_path} "
            f"--profile {profile} --output-dir {output_dir} --json"
        )
        return result

    verify_out = cmd_verify(request_path, root)
    result["verify"] = verify_out
    if not verify_out.get("ready"):
        result["status"] = "reprovado_pre_voo"
        result["contractInvalid"] = verify_out.get("contractInvalid", False)
        result["errors"] = verify_out.get("errors", [])
        result["error"] = "pre-voo reprovado antes do render"
        return result

    attempt_id = f"proof-{profile}-{uuid.uuid4().hex[:12]}"
    result["attemptId"] = attempt_id
    cmd = [
        sys.executable,
        os.path.join(root, "tools", "produce_video.py"),
        "--input", abs_request,
        "--profile", profile,
        "--output-dir", abs_output,
        "--attempt-id", attempt_id,
        "--json",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=600, cwd=root,
        )
    except subprocess.TimeoutExpired:
        _, valid_after = _read_index_profile_state(abs_output, profile)
        if valid_after:
            result["preservedLastValidDelivery"] = valid_after
        result["status"] = "falha_tempo_limite"
        result["error"] = "render excedeu o tempo limite (600 s)"
        return result
    except FileNotFoundError as exc:
        result["status"] = "falha_ferramenta"
        result["error"] = f"interpretador Python indisponivel: {exc}"
        return result

    result["renderExitCode"] = proc.returncode
    render_out = None
    if proc.stdout and proc.stdout.strip():
        try:
            render_out = json.loads(proc.stdout)
        except ValueError:
            render_out = None

    _, valid_after = _read_index_profile_state(abs_output, profile)
    if render_out is None:
        result["status"] = "parcial_ou_falhou"
        result["error"] = (proc.stderr or proc.stdout or "produce_video falhou sem JSON").strip()[-1000:]
        result["stderr"] = (proc.stderr or "")[-1000:]
        if valid_after:
            result["preservedLastValidDelivery"] = valid_after
        return result

    result["rawRenderOutput"] = render_out
    profile_out = next(
        (p for p in render_out.get("profiles", []) if p.get("profileId") == profile),
        None,
    )
    if not profile_out or proc.returncode != 0 or profile_out.get("status") != "completed":
        result["status"] = "parcial_ou_falhou"
        result["profileStatus"] = profile_out.get("status") if profile_out else "ausente"
        result["profileFailureCode"] = profile_out.get("failureCode") if profile_out else None
        result["profileError"] = profile_out.get("error") if profile_out else result.get("error")
        if valid_after:
            result["preservedLastValidDelivery"] = valid_after
        return result

    manifest_rel = profile_out.get("deliveryManifest")
    if not manifest_rel:
        result["status"] = "parcial_ou_falhou"
        result["error"] = "deliveryManifest ausente no retorno do pipeline"
        return result

    manifest_abs = _resolve_contained(root, manifest_rel, "SAIDA_FORA_RAIZ")
    with open(render_local.fs_path(manifest_abs), "r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    if manifest.get("attemptId") != attempt_id:
        result["status"] = "tentativa_divergente"
        result["error"] = f"attemptId divergente no manifesto: esperado {attempt_id}, obtido {manifest.get('attemptId')}"
        if valid_after:
            result["preservedLastValidDelivery"] = valid_after
        return result

    artifacts = manifest.get("artifacts") or {}
    video_info = artifacts.get("video") or {}
    srt_info = artifacts.get("srt") or {}
    narr_info = artifacts.get("narration") or {}
    report_info = artifacts.get("report") or {}

    video_rel = video_info.get("path")
    srt_rel = srt_info.get("path")
    narr_rel = narr_info.get("path")
    report_rel = report_info.get("path")
    if not all([video_rel, srt_rel, narr_rel, report_rel]):
        result["status"] = "entrega_incompleta"
        result["error"] = "delivery-manifest.json nao listou todos os artefatos obrigatorios (video, srt, narration, report)"
        return result

    abs_mp4 = _resolve_contained(root, video_rel, "SAIDA_FORA_RAIZ")
    abs_srt = _resolve_contained(root, srt_rel, "SAIDA_FORA_RAIZ")
    abs_narr = _resolve_contained(root, narr_rel, "SAIDA_FORA_RAIZ")
    abs_rep = _resolve_contained(root, report_rel, "SAIDA_FORA_RAIZ")

    with open(render_local.fs_path(abs_rep), "r", encoding="utf-8") as handle:
        exec_report = json.load(handle)
    rep_output = exec_report.get("output") or {}
    exp_width = int(rep_output.get("width") or VIDEO_WIDTH)
    exp_height = int(rep_output.get("height") or VIDEO_HEIGHT)
    exp_fps = int(rep_output.get("fps") or VIDEO_FPS)
    exp_duration_s = round(int(rep_output.get("durationMs") or 0) / 1000.0, 3) or total_duration_seconds(request)

    try:
        inspection = build_video.validate_mp4(
            render_local.fs_path(abs_mp4), exp_width, exp_height, exp_fps,
            exp_duration_s, duration_tolerance=0.25, timeout=30,
        )
    except build_video.DeliveryError as exc:
        result["status"] = "inspecao_mp4_falhou"
        result["ffprobeError"] = str(exc)
        if valid_after:
            result["preservedLastValidDelivery"] = valid_after
        return result

    srt_errors = srt_validate.validate_srt_file(render_local.fs_path(abs_srt), duration=exp_duration_s)
    with open(render_local.fs_path(abs_narr), "r", encoding="utf-8") as handle:
        narration_text = handle.read().strip()

    audio_streams = inspection.get("audioStreams", 1)
    if audio_streams != 0 or srt_errors or not narration_text:
        result["status"] = "validacao_entrega_falhou"
        result["ffprobe"] = inspection
        result["srtErrors"] = srt_errors
        result["error"] = "MP4 contem faixa de audio, SRT invalido ou narracao vazia"
        return result

    result.update({
        "ok": True,
        "status": "concluido",
        "profileStatus": "completed",
        "deliveryManifest": render_local.rel(root, manifest_abs),
        "mp4Path": render_local.rel(root, abs_mp4),
        "srtPath": render_local.rel(root, abs_srt),
        "narrationPath": render_local.rel(root, abs_narr),
        "reportPath": render_local.rel(root, abs_rep),
        "expectedOutput": {"width": exp_width, "height": exp_height, "fps": exp_fps, "durationSeconds": exp_duration_s},
        "ffprobe": inspection,
        "srtValid": True,
        "narrationChars": len(narration_text),
    })
    return result


def _git_head_sha(root: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=5, cwd=root,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "indisponivel"


def _portable_asset_link(
    abs_src: str,
    html_dir: str,
    copy_subdir: str,
    root: str,
    copied_names: set[str],
    fallback_name: str | None = None,
) -> str:
    """Usa relpath se abs_src ja estiver dentro de html_dir; senao copia com seguranca."""
    if render_local.overlaps(html_dir, abs_src):
        return os.path.relpath(abs_src, html_dir).replace(os.sep, "/")
    base = fallback_name or os.path.basename(abs_src)
    if not _SAFE_SEGMENT_RE.match(base):
        base = re.sub(r"[^a-zA-Z0-9._-]", "_", base)
    stem, ext = os.path.splitext(base)
    candidate = base
    n = 2
    while os.path.join(copy_subdir, candidate) in copied_names:
        candidate = f"{stem}-{n}{ext}"
        n += 1
    copied_names.add(os.path.join(copy_subdir, candidate))
    dest_dir = os.path.join(html_dir, copy_subdir)
    dest_abs = os.path.realpath(os.path.join(dest_dir, candidate))
    if not render_local.contained(root, dest_abs):
        raise ProofError("SAIDA_FORA_RAIZ", copy_subdir)
    os.makedirs(render_local.fs_path(dest_dir), exist_ok=True)
    shutil.copy2(render_local.fs_path(abs_src), render_local.fs_path(dest_abs))
    return f"{copy_subdir}/{candidate}".replace("\\", "/")


def _collect_deliveries_for_review(
    root: str,
    abs_delivery_dir: str | None,
    render_results: list[dict] | dict | None,
) -> list[dict]:
    collected: dict[str, dict] = {}
    if isinstance(render_results, dict):
        render_list = [render_results]
    elif isinstance(render_results, list):
        render_list = list(render_results)
    else:
        render_list = []

    for r in render_list:
        prof = r.get("profile")
        if prof:
            collected[prof] = dict(r)

    if abs_delivery_dir and os.path.isfile(render_local.fs_path(os.path.join(abs_delivery_dir, "index.json"))):
        try:
            with open(render_local.fs_path(os.path.join(abs_delivery_dir, "index.json")), "r", encoding="utf-8") as h:
                idx_data = json.load(h)
            for entry in idx_data.get("profiles", []):
                prof = entry.get("profileId")
                if not prof or prof in collected:
                    continue
                valid = entry.get("lastValidDelivery") or {}
                last_att = entry.get("lastAttempt") or {}
                item: dict = {
                    "profile": prof,
                    "ok": last_att.get("status") == "completed",
                    "status": "concluido" if last_att.get("status") == "completed" else (last_att.get("status") or "desconhecido"),
                    "error": last_att.get("error"),
                }
                manifest_rel = valid.get("deliveryManifest")
                if manifest_rel:
                    m_abs = os.path.realpath(os.path.join(root, manifest_rel.replace("/", os.sep)))
                    if render_local.contained(root, m_abs) and os.path.isfile(render_local.fs_path(m_abs)):
                        with open(render_local.fs_path(m_abs), "r", encoding="utf-8") as mh:
                            man = json.load(mh)
                        arts = man.get("artifacts") or {}
                        item["deliveryManifest"] = manifest_rel
                        item["mp4Path"] = (arts.get("video") or {}).get("path")
                        item["srtPath"] = (arts.get("srt") or {}).get("path")
                        item["narrationPath"] = (arts.get("narration") or {}).get("path")
                        item["reportPath"] = (arts.get("report") or {}).get("path")
                        item["ffprobe"] = (arts.get("video") or {}).get("ffprobe")
                collected[prof] = item
        except (OSError, ValueError):
            pass
    return list(collected.values())


def cmd_review(
    request_path: str,
    output_html: str | None = None,
    root: str = ".",
    delivery_dir: str | None = None,
    verify_result: dict | None = None,
    render_results: list[dict] | dict | None = None,
) -> dict:
    """Gera pagina HTML portavel de revisao refletindo estado real de pre-voo, render e midias."""
    root = os.path.realpath(root)
    abs_request = _resolve_contained(root, request_path, "ENTRADA_FORA_RAIZ")
    request = _load_json(request_path, root, "pedido")
    req_id = str(request.get("id") or "campanha")
    verify_out = verify_result if verify_result is not None else cmd_verify(request_path, root)

    abs_delivery_dir = None
    if delivery_dir:
        abs_delivery_dir = _resolve_contained(root, delivery_dir, "SAIDA_FORA_RAIZ")
    elif output_html:
        abs_html_cand = _resolve_contained(root, output_html, "SAIDA_FORA_RAIZ")
        cand_dir = os.path.dirname(abs_html_cand)
        if os.path.isfile(render_local.fs_path(os.path.join(cand_dir, "index.json"))):
            abs_delivery_dir = cand_dir

    deliveries = _collect_deliveries_for_review(root, abs_delivery_dir, render_results)

    abs_html = None
    html_dir = None
    if output_html:
        abs_html = _resolve_contained(root, output_html, "SAIDA_FORA_RAIZ")
        html_dir = os.path.dirname(abs_html)
        os.makedirs(render_local.fs_path(html_dir), exist_ok=True)

    copied: set[str] = set()
    media_index = _collect_media(request) if isinstance(request.get("media"), list) else {}
    scenes = request.get("scenes") if isinstance(request.get("scenes"), list) else []

    scene_rows: list[str] = []
    synthetic_count = 0
    operator_count = 0
    for i, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            continue
        mid = str(scene.get("mediaId", ""))
        media = media_index.get(mid, {})
        mpath = str(media.get("path", ""))
        abs_media = None
        exists = False
        is_synth = False
        if mpath:
            try:
                abs_media = _resolve_contained(root, mpath, "MEDIA_OUTSIDE_ROOT")
                exists = os.path.isfile(render_local.fs_path(abs_media))
                if exists:
                    is_synth = _is_synthetic_proof_file(abs_media) or (
                        media.get("type") == "video" and str(media.get("origin", "")).startswith("synthetic-")
                    )
            except ProofError:
                exists = False
        if exists:
            if is_synth:
                synthetic_count += 1
            else:
                operator_count += 1

        thumb_html = "<span class=\"muted\">Sem miniatura</span>"
        if exists and abs_media and media.get("type", "image") == "image":
            if html_dir:
                rel_img = _portable_asset_link(abs_media, html_dir, "assets", root, copied)
            else:
                rel_img = mpath.replace("\\", "/")
            thumb_html = (
                f"<img class=\"thumb\" src=\"{html.escape(rel_img, quote=True)}\" "
                f"alt=\"{html.escape(str(scene.get('id', mid)), quote=True)}\">"
            )
        origin_badge = (
            "<span class=\"badge warn\">Prova ficticia</span>" if is_synth
            else ("<span class=\"badge ok\">Operador real</span>" if exists else "<span class=\"badge blocked\">Ausente</span>")
        )
        scene_rows.append(
            "<tr>"
            f"<td>{i}</td>"
            f"<td>{thumb_html}</td>"
            f"<td><code>{html.escape(str(scene.get('id', '')), quote=True)}</code></td>"
            f"<td>{html.escape(str(scene.get('durationMs', '')), quote=True)} ms</td>"
            f"<td>{html.escape(str(scene.get('narrativeFunction', '')), quote=True)}</td>"
            f"<td><code>{html.escape(mid, quote=True)}</code><br>{origin_badge}</td>"
            f"<td>{html.escape(str(scene.get('caption', '')), quote=True)}</td>"
            f"<td>{html.escape(str(scene.get('narration', '')), quote=True)}</td>"
            "</tr>"
        )

    deliveries_html_parts: list[str] = []
    if deliveries:
        for d in deliveries:
            prof = str(d.get("profile", "desconhecido"))
            d_ok = bool(d.get("ok"))
            status_lbl = str(d.get("status") or ("concluido" if d_ok else "pendente"))
            badge_cls = "ok" if d_ok else ("pending" if status_lbl == "pendente_ferramenta" else "blocked")
            safe_prof = re.sub(r"[^a-zA-Z0-9._-]", "_", prof) or "perfil"

            video_block = ""
            mp4_rel = d.get("mp4Path")
            if mp4_rel:
                abs_mp4 = _resolve_contained(root, mp4_rel, "SAIDA_FORA_RAIZ")
                if os.path.isfile(render_local.fs_path(abs_mp4)):
                    href_mp4 = _portable_asset_link(
                        abs_mp4, html_dir, f"deliveries/{safe_prof}", root, copied
                    ) if html_dir else mp4_rel.replace("\\", "/")
                    esc_mp4 = html.escape(href_mp4, quote=True)
                    video_block = (
                        f"<div class=\"mp4-wrap\"><video controls preload=\"metadata\" playsinline src=\"{esc_mp4}\"></video>"
                        f"<p><a href=\"{esc_mp4}\">Abrir MP4 ({html.escape(os.path.basename(abs_mp4), quote=True)})</a></p></div>"
                    )

            srt_block = ""
            if d.get("srtPath"):
                abs_srt = _resolve_contained(root, d["srtPath"], "SAIDA_FORA_RAIZ")
                if os.path.isfile(render_local.fs_path(abs_srt)):
                    with open(render_local.fs_path(abs_srt), "r", encoding="utf-8", errors="replace") as sh:
                        srt_txt = sh.read()
                    href_srt = _portable_asset_link(
                        abs_srt, html_dir, f"deliveries/{safe_prof}", root, copied
                    ) if html_dir else d["srtPath"]
                    srt_block = (
                        f"<details><summary>Legendas (.srt) — <a href=\"{html.escape(href_srt, quote=True)}\">baixar</a></summary>"
                        f"<pre>{html.escape(srt_txt, quote=True)}</pre></details>"
                    )

            narr_block = ""
            if d.get("narrationPath"):
                abs_n = _resolve_contained(root, d["narrationPath"], "SAIDA_FORA_RAIZ")
                if os.path.isfile(render_local.fs_path(abs_n)):
                    with open(render_local.fs_path(abs_n), "r", encoding="utf-8", errors="replace") as nh:
                        narr_txt = nh.read()
                    href_n = _portable_asset_link(
                        abs_n, html_dir, f"deliveries/{safe_prof}", root, copied
                    ) if html_dir else d["narrationPath"]
                    narr_block = (
                        f"<details><summary>Narracao separada (.txt) — <a href=\"{html.escape(href_n, quote=True)}\">baixar</a></summary>"
                        f"<pre>{html.escape(narr_txt, quote=True)}</pre></details>"
                    )

            ffp = d.get("ffprobe") or {}
            ffp_summary = ""
            if ffp:
                ffp_summary = (
                    f"<p><strong>FFprobe:</strong> {html.escape(str(ffp.get('width', '?')))}x{html.escape(str(ffp.get('height', '?')))} "
                    f"@ {html.escape(str(ffp.get('fps', '?')))} fps · duracao {html.escape(str(ffp.get('duration', '?')))} s · "
                    f"faixas de audio: {html.escape(str(ffp.get('audioStreams', '?')))}</p>"
                )
            err_block = f"<div class=\"error\">{html.escape(str(d.get('error')), quote=True)}</div>" if d.get("error") else ""
            deliveries_html_parts.append(
                "<div class=\"card delivery-card\">"
                f"<h3>{html.escape(prof, quote=True)} <span class=\"badge {badge_cls}\">{html.escape(status_lbl, quote=True)}</span></h3>"
                f"{ffp_summary}{err_block}{video_block}{srt_block}{narr_block}"
                "</div>"
            )
    else:
        tools_msg = verify_out.get("renderToolsMessage")
        note_text = (
            tools_msg
            if not verify_out.get("renderToolsReady")
            else "Nenhuma entrega renderizada foi informada ou localizada em delivery-dir para esta revisao."
        )
        deliveries_html_parts.append(f"<p class=\"note\">{html.escape(str(note_text), quote=True)}</p>")

    verify_errs = verify_out.get("errors", [])
    next_action = (
        "Nenhuma pendencia tecnica; aguardar substituicao de midias ficticias e aprovacao editorial do titular antes de publicar."
        if verify_out.get("ready") and deliveries and all(d.get("ok") for d in deliveries)
        else "Resolver bloqueios apontados acima e reexecutar o comando de prova."
    )
    repro_cmd = (
        f"python tools/campaign_proof.py run {request_path} "
        f"--all-profiles --output-dir .workspace/archives/prova-campanha-ns001-ns002/{req_id}"
    )

    page_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Revisao de Prova — {html.escape(req_id, quote=True)}</title>
<style>
  *{{box-sizing:border-box;}}
  html,body{{max-width:100%;overflow-x:hidden;}}
  body{{font-family:system-ui,-apple-system,sans-serif;background:#f4f6f9;color:#111827;margin:0;padding:16px;}}
  .container{{width:100%;max-width:1120px;margin:0 auto;background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 12px rgba(0,0,0,.08);}}
  h1{{font-size:22px;margin-top:0;color:#0b5ed7;overflow-wrap:anywhere;}}
  .badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px;color:#fff;font-weight:600;}}
  .badge.ok{{background:#2e7d32;}}.badge.blocked{{background:#c62828;}}.badge.pending,.badge.warn{{background:#f9a825;color:#111;}}
  .table-wrap{{overflow-x:auto;width:100%;max-width:100%;margin:12px 0;-webkit-overflow-scrolling:touch;}}
  table{{width:100%;border-collapse:collapse;min-width:640px;}}
  th,td{{border:1px solid #d1d5db;padding:8px;text-align:left;font-size:14px;vertical-align:top;}}
  th{{background:#eef4fb;}}
  img.thumb{{max-width:110px;max-height:180px;height:auto;border-radius:6px;border:1px solid #cbd5e1;display:block;}}
  video{{max-width:360px;width:100%;height:auto;border-radius:8px;background:#000;display:block;}}
  .section{{margin:24px 0;min-width:0;max-width:100%;}}
  .section h2{{font-size:17px;border-bottom:2px solid #0b5ed7;padding-bottom:6px;color:#0b5ed7;}}
  .note{{background:#fff8e1;border-left:4px solid #f9a825;padding:10px;margin:12px 0;overflow-wrap:anywhere;}}
  .error{{background:#ffebee;border-left:4px solid #c62828;padding:10px;margin:12px 0;overflow-wrap:anywhere;}}
  .ok-box{{background:#e8f5e9;border-left:4px solid #2e7d32;padding:10px;margin:12px 0;overflow-wrap:anywhere;}}
  p,a,li,summary{{overflow-wrap:anywhere;}}
  pre,code{{background:#f3f4f6;padding:4px 6px;border-radius:6px;overflow-x:auto;font-size:12px;overflow-wrap:anywhere;white-space:pre-wrap;max-width:100%;}}
  pre{{padding:10px;}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(220px,100%),1fr));gap:12px;width:100%;}}
  .card{{min-width:0;max-width:100%;border:1px solid #e5e7eb;border-radius:8px;padding:12px;background:#fafbfc;overflow-wrap:anywhere;}}
  .card h3{{margin:0 0 8px 0;font-size:15px;color:#0b5ed7;}}
  .delivery-card{{margin-bottom:14px;}}
  @media (max-width:640px){{
    body{{padding:8px;}}
    .container{{padding:12px;}}
    h1{{font-size:18px;}}
  }}
</style>
</head>
<body>
<div class="container">
  <h1>Revisao de Prova de Campanha — {html.escape(req_id, quote=True)}</h1>

  <div class="section">
    <h2>Identificacao e Rastreabilidade</h2>
    <div class="grid">
      <div class="card"><h3>Pedido / Campanha</h3><p><strong>{html.escape(req_id, quote=True)}</strong><br>{html.escape(str(request.get('title', '')), quote=True)}</p></div>
      <div class="card"><h3>Projeto e Perfis</h3><p>{html.escape(str(request.get('project', '')), quote=True)}<br><code>{html.escape(', '.join(verify_out.get('profiles', [])), quote=True)}</code></p></div>
      <div class="card"><h3>Estado Editorial</h3><p><span class="badge warn">Rascunho / Prova tecnica</span><br>Midias ficticias: {synthetic_count} · Operador: {operator_count}</p></div>
      <div class="card"><h3>Revisao do Codigo</h3><p>Git: <code>{html.escape(_git_head_sha(root), quote=True)}</code><br>SHA-256 pedido: <code>{html.escape(render_local.sha256_file(abs_request)[:16], quote=True)}</code></p></div>
    </div>
  </div>

  <div class="section">
    <h2>Pre-voo e Compilacao (platform)</h2>
    <div class="{'ok-box' if verify_out.get('ready') else 'error'}">
      <p><strong>Pronto para render:</strong> {'SIM' if verify_out.get('ready') else 'NAO'} · <strong>Geometria:</strong> {html.escape(str(verify_out.get('geometry')), quote=True)} @ {html.escape(str(verify_out.get('fps')), quote=True)} fps · <strong>Duracao:</strong> {html.escape(str(verify_out.get('totalDurationSeconds')), quote=True)} s ({verify_out.get('totalDurationMs', 0)} ms) · <strong>Audio:</strong> 0 faixas (-an)</p>
      {''.join(f"<p>- [{html.escape(str(e.get('code', '')), quote=True)}] {html.escape(str(e.get('subject') or ''), quote=True)}</p>" for e in verify_errs) if verify_errs else "<p>Sem bloqueios no pre-voo.</p>"}
    </div>
    <p class="note"><strong>Proxima acao:</strong> {html.escape(next_action, quote=True)}</p>
  </div>

  <div class="section">
    <h2>Entregas Renderizadas e Inspecao</h2>
    {''.join(deliveries_html_parts)}
  </div>

  <div class="section">
    <h2>Sequencia de Cenas ({len(scenes)})</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>#</th><th>Miniatura</th><th>Cena</th><th>Duracao</th><th>Funcao</th><th>Midia / Origem</th><th>Legenda</th><th>Narracao separada</th></tr></thead>
        <tbody>{''.join(scene_rows)}</tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <h2>Comando para Reproduzir a Prova</h2>
    <pre>{html.escape(repro_cmd, quote=True)}</pre>
  </div>
</div>
</body>
</html>
"""

    if abs_html:
        with open(render_local.fs_path(abs_html), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(page_html)

    return {
        "ok": True,
        "operation": "review",
        "request": request_path,
        "requestId": req_id,
        "verifyReady": bool(verify_out.get("ready")),
        "deliveryCount": len(deliveries),
        "htmlPath": render_local.rel(root, abs_html) if abs_html else None,
        "sceneCount": len(scenes),
        "totalDurationMs": verify_out.get("totalDurationMs", 0),
        "totalDurationSeconds": verify_out.get("totalDurationSeconds", 0.0),
    }


def _order_profiles(declared: list[str], profile: str | None, all_profiles: bool) -> list[str]:
    if not declared:
        return [profile] if profile else []
    if all_profiles:
        ordered = []
        if "instagram-reels-video" in declared:
            ordered.append("instagram-reels-video")
        for p in declared:
            if p not in ordered:
                ordered.append(p)
        return ordered
    if profile:
        return [profile]
    return ["instagram-reels-video" if "instagram-reels-video" in declared else declared[0]]


def cmd_run(
    request_path: str,
    output_dir: str,
    root: str = ".",
    profile: str | None = None,
    all_profiles: bool = False,
    output_html: str | None = None,
    force: bool = False,
) -> dict:
    """Encadeia prepare -> verify -> render -> review em uma unica operacao."""
    root = os.path.realpath(root)
    abs_output = _resolve_contained(root, output_dir, "SAIDA_FORA_RAIZ")
    os.makedirs(render_local.fs_path(abs_output), exist_ok=True)
    request = _load_json(request_path, root, "pedido")
    req_id = str(request.get("id") or "campanha")

    prep = cmd_prepare(request_path, output_dir=output_dir, root=root, force=force)
    ver = cmd_verify(request_path, root=root)

    declared = ver.get("profiles") or []
    targets = _order_profiles(declared, profile, all_profiles)
    render_results: list[dict] = []
    if prep.get("ok") and ver.get("ready"):
        for prof in targets:
            render_results.append(cmd_render(request_path, prof, output_dir, root=root))

    html_target = output_html or os.path.join(output_dir, f"revisao-{req_id}.html")
    rev = cmd_review(
        request_path,
        output_html=html_target,
        root=root,
        delivery_dir=output_dir,
        verify_result=ver,
        render_results=render_results,
    )

    all_ok = bool(
        prep.get("ok")
        and ver.get("ready")
        and render_results
        and all(r.get("ok") for r in render_results)
        and rev.get("ok")
    )
    summary = {
        "ok": all_ok,
        "operation": "run",
        "request": request_path,
        "requestId": req_id,
        "outputDir": render_local.rel(root, abs_output),
        "profilesRun": targets,
        "prepare": prep,
        "verify": ver,
        "renders": render_results,
        "review": rev,
        "contractInvalid": bool(ver.get("contractInvalid")),
        "completedAt": _now_iso(),
    }
    summary_abs = os.path.join(abs_output, "proof-summary.json")
    with open(render_local.fs_path(summary_abs), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ferramenta de prova de campanha para o Marca Salao"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="Prepara midia sintetica em media[].path preservando operador")
    p_prepare.add_argument("request", help="Caminho do pedido VideoRequest v1")
    p_prepare.add_argument("--output-dir", default=None, help="Diretorio opcional de relatorio")
    p_prepare.add_argument("--force", action="store_true", help="Regenera arquivos mesmo se existentes")
    p_prepare.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_prepare.add_argument("--json", action="store_true", help="Saida somente JSON")

    p_verify = sub.add_parser("verify", help="Valida pedido via arquivos e ponte da platform")
    p_verify.add_argument("request", help="Caminho do pedido VideoRequest v1")
    p_verify.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_verify.add_argument("--json", action="store_true", help="Saida somente JSON")

    p_render = sub.add_parser("render", help="Renderiza um perfil via pipeline e inspeciona MP4/SRT")
    p_render.add_argument("request", help="Caminho do pedido VideoRequest v1")
    p_render.add_argument("--profile", required=True, help="Perfil de saida (ex: instagram-reels-video)")
    p_render.add_argument("--output-dir", required=True, help="Diretorio de entrega")
    p_render.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_render.add_argument("--json", action="store_true", help="Saida somente JSON")

    p_review = sub.add_parser("review", help="Gera pagina HTML portavel de revisao")
    p_review.add_argument("request", help="Caminho do pedido VideoRequest v1")
    p_review.add_argument("--delivery-dir", default=None, help="Diretorio com index.json e entregas")
    p_review.add_argument("--output", default=None, help="Caminho do HTML de saida")
    p_review.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_review.add_argument("--json", action="store_true", help="Saida somente JSON")

    p_run = sub.add_parser("run", help="Encadeia prepare -> verify -> render -> review")
    p_run.add_argument("request", help="Caminho do pedido VideoRequest v1")
    p_run.add_argument("--profile", default=None, help="Perfil especifico a renderizar")
    p_run.add_argument("--all-profiles", action="store_true", help="Renderiza todos os perfis (Instagram primeiro)")
    p_run.add_argument("--output-dir", required=True, help="Diretorio de entrega e HTML de revisao")
    p_run.add_argument("--output-html", default=None, help="Caminho alternativo do HTML de revisao")
    p_run.add_argument("--force", action="store_true", help="Regenera midias existentes")
    p_run.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_run.add_argument("--json", action="store_true", help="Saida somente JSON")

    return parser


def main(argv=None) -> int:
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "prepare":
            result = cmd_prepare(args.request, args.output_dir, args.root, force=args.force)
        elif args.command == "verify":
            result = cmd_verify(args.request, args.root)
        elif args.command == "render":
            result = cmd_render(args.request, args.profile, args.output_dir, args.root)
        elif args.command == "review":
            result = cmd_review(args.request, args.output, args.root, delivery_dir=args.delivery_dir)
        elif args.command == "run":
            result = cmd_run(
                args.request,
                args.output_dir,
                args.root,
                profile=args.profile,
                all_profiles=args.all_profiles,
                output_html=args.output_html,
                force=args.force,
            )
        else:
            print("Comando desconhecido", file=sys.stderr)
            return 2
    except ProofError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": exc.code, "subject": exc.subject}, ensure_ascii=False))
        else:
            print(f"Erro: [{exc.code}] {exc.subject or ''}", file=sys.stderr)
        return exc.exit_code
    except (OSError, ValueError, KeyError) as exc:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": "ENTRADA_INVALIDA", "message": str(exc)}, ensure_ascii=False))
        else:
            print(f"Erro: entrada invalida ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("ok"):
        return 0
    if result.get("contractInvalid"):
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
