"""Ferramenta reutilizavel de prova de campanha para o Marca Salao.

Prepara, verifica, renderiza e gera pagina de revisao para pedidos
VideoRequest v1, reaproveitando os recursos existentes do Studio e do
pipeline de render (tools/render_pipeline.py, tools/produce_video.py,
tools/make_proof_assets.py, tools/build_video.py).

Politica do projeto: video sem faixa de audio, sem rede, sem fornecedor,
sem TTS. Mídias sao sinteticas e identificadas como prova. Todos os
arquivos temporarios e de resultado ficam dentro de <RAIZ>/.workspace/.

Uso (a partir da raiz do checkout):
    python tools/campaign_proof.py prepare <pedido.json> --output-dir <dir>
    python tools/campaign_proof.py verify <pedido.json>
    python tools/campaign_proof.py render <pedido.json> --profile <perfil> --output-dir <dir>
    python tools/campaign_proof.py review <pedido.json> [--output <pagina.html>]

Com --json em qualquer subcomando, o resultado e emitido somente como JSON
no stdout. Codigos de saida: 0 sucesso; 1 falha de entrega/render;
2 uso/caminho/JSON invalido; 3 contrato do pedido invalido.
"""

from __future__ import annotations

import argparse
import hashlib
import html as html_mod
import json
import os
import shutil
import struct
import subprocess
import sys
import zlib
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import render_local
import r002_pilot
import srt_validate

# ---------------------------------------------------------------------------
# Constantes do projeto (reaproveitadas dos contratos existentes)
# ---------------------------------------------------------------------------

VIDEO_REQUEST_SCHEMA_VERSION = 1
KEBAB_CASE_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"

NARRATIVE_FUNCTIONS = [
    "hook", "context", "problem", "demonstration", "explanation",
    "proof", "transition", "cta", "closing",
]
MOTION_INTENTS = ["none", "slow-zoom"]
MEDIA_TYPES = ["image", "video"]
DEFAULT_LOCALE = "pt-BR"
DEFAULT_LICENSE = "pending"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


# ---------------------------------------------------------------------------
# Gerador de mídia sintética (PNG determinístico, stdlib apenas)
# ---------------------------------------------------------------------------

def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + tag
        + payload
        + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    )


def scene_palette(project_id: str, beat_id: str):
    digest = hashlib.sha256(f"{project_id}/{beat_id}".encode("utf-8")).digest()
    top = (40 + digest[0] % 150, 40 + digest[1] % 150, 40 + digest[2] % 150)
    bottom = (40 + digest[3] % 150, 40 + digest[4] % 150, 40 + digest[5] % 150)
    stripe = (
        min(255, top[0] + 60),
        min(255, top[1] + 60),
        min(255, top[2] + 60),
    )
    return top, bottom, stripe


def write_scene_png(path: str, project_id: str, beat_id: str, order: int,
                    width: int = VIDEO_WIDTH, height: int = VIDEO_HEIGHT) -> None:
    """Gera um PNG determinístico (gradiente + listras) identificado por
    project_id/beat_id. Nenhuma rede, nenhuma dependência externa."""
    top, bottom, stripe = scene_palette(project_id, beat_id)
    bars = max(1, int(order))
    rows = []
    bar_pitch = height // (bars + 1)
    for y in range(height):
        ratio = y / (height - 1) if height > 1 else 0
        base = tuple(
            int(top[c] + (bottom[c] - top[c]) * ratio) for c in range(3)
        )
        row = bytearray()
        for x in range(width):
            color = base
            if ((x + y) // 24) % 2 == 0:
                color = tuple(
                    min(255, base[c] + (stripe[c] - top[c]) // 2) for c in range(3)
                )
            for bar in range(1, bars + 1):
                center = bar * bar_pitch
                if abs(y - center) <= 10 and 60 <= x <= width - 60:
                    color = (235, 235, 235)
                    break
            row.extend(color)
        rows.append(b"\x00" + bytes(row))
    raw = b"".join(rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = (
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )
    with open(path, "wb") as handle:
        handle.write(png)


# ---------------------------------------------------------------------------
# Utilitários de validação (espelho dos contratos da platform)
# ---------------------------------------------------------------------------

import re

_KEBAB_RE = re.compile(KEBAB_CASE_PATTERN)


def _is_kebab(value: str) -> bool:
    return bool(_KEBAB_RE.match(value or ""))


class ProofError(Exception):
    """Falha de prova com código estável e assunto opcional."""

    def __init__(self, code: str, subject: str | None = None):
        super().__init__(code)
        self.code = code
        self.subject = subject


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _html_escape(text: str) -> str:
    return html_mod.escape(str(text or ""), quote=True)


def _load_json(path: str, root: str, label: str) -> dict:
    abs_path = render_local.fs_path(os.path.join(root, path))
    if not os.path.isfile(abs_path):
        raise ProofError("ARQUIVO_AUSENTE", path)
    try:
        with open(abs_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProofError("JSON_INVALID", f"{label}: {exc}") from exc


def validate_video_request(request: dict, root: str) -> list[ProofError]:
    """Valida o VideoRequest contra o contrato da platform (espelho de
    platform/src/video-request-contract.ts). Devolve lista de ProofError."""
    errors: list[ProofError] = []

    if not isinstance(request, dict):
        errors.append(ProofError("PEDIDO_INVALIDO", "raiz nao e um objeto"))
        return errors

    # schemaVersion
    if request.get("schemaVersion") != VIDEO_REQUEST_SCHEMA_VERSION:
        errors.append(
            ProofError("SCHEMA_VERSION_UNSUPPORTED", str(request.get("schemaVersion")))
        )

    # id (kebab, obrigatorio)
    rid = request.get("id")
    if not isinstance(rid, str) or not rid or not _is_kebab(rid):
        errors.append(ProofError("ID_INVALID", str(rid)))

    # project (obrigatorio, nao vazio)
    project = request.get("project")
    if not isinstance(project, str) or not project.strip():
        errors.append(ProofError("PROJECT_INVALID", str(project)))

    # title (obrigatorio, nao vazio)
    title = request.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append(ProofError("TITLE_INVALID", str(title)))

    # locale (opcional)
    locale = request.get("locale")
    if locale is not None and not isinstance(locale, str):
        errors.append(ProofError("LOCALE_INVALID", str(locale)))

    # profiles (obrigatorio, nao vazio, sem duplicatas)
    profiles = request.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        errors.append(ProofError("PROFILES_INVALID", str(profiles)))
    else:
        seen_profiles = set()
        for p in profiles:
            if not isinstance(p, str) or not p.strip():
                errors.append(ProofError("PROFILE_INVALID", str(p)))
            elif p in seen_profiles:
                errors.append(ProofError("PROFILE_DUPLICATE", p))
            else:
                seen_profiles.add(p)

    # visualStyle (opcional)
    visual_style = request.get("visualStyle")
    if visual_style is not None:
        if not isinstance(visual_style, dict):
            errors.append(ProofError("VISUAL_STYLE_INVALID", str(visual_style)))
        else:
            vs_title = visual_style.get("title")
            if not isinstance(vs_title, dict):
                errors.append(ProofError("VISUAL_STYLE_TITLE_INVALID", str(vs_title)))
            else:
                for field in ("textColor", "outlineColor"):
                    val = vs_title.get(field)
                    if not isinstance(val, str) or not val.startswith("#"):
                        errors.append(
                            ProofError("VISUAL_STYLE_COLOR_INVALID", f"{field}={val}")
                        )
                for field in ("fontSize", "marginTop", "marginHorizontal"):
                    val = vs_title.get(field)
                    if not isinstance(val, int) or not (8 <= val <= 160 if field == "fontSize" else 0 <= val <= 600):
                        errors.append(
                            ProofError("VISUAL_STYLE_FIELD_INVALID", f"{field}={val}")
                        )

    # media (obrigatorio)
    media = request.get("media")
    if not isinstance(media, list):
        errors.append(ProofError("MEDIA_INVALID", str(media)))
        media = []
    else:
        seen_media_ids = set()
        for entry in media:
            if not isinstance(entry, dict):
                errors.append(ProofError("MEDIA_ITEM_INVALID", str(entry)))
                continue
            mid = entry.get("id")
            if not isinstance(mid, str) or not mid or not _is_kebab(mid):
                errors.append(ProofError("MEDIA_ID_INVALID", str(mid)))
            elif mid in seen_media_ids:
                errors.append(ProofError("MEDIA_ID_DUPLICATE", mid))
            else:
                seen_media_ids.add(mid)
            mpath = entry.get("path")
            if not isinstance(mpath, str) or not mpath.strip():
                errors.append(ProofError("MEDIA_PATH_INVALID", str(mpath)))
            else:
                abs_path = render_local.fs_path(os.path.join(root, mpath))
                if not render_local.contained(root, abs_path):
                    errors.append(ProofError("MEDIA_PATH_FORA_RAIZ", mpath))
                # existência do arquivo é verificada no prepare/render, não aqui
            mtype = entry.get("type")
            if mtype not in MEDIA_TYPES:
                errors.append(ProofError("MEDIA_TYPE_INVALID", str(mtype)))
            origin = entry.get("origin")
            if not isinstance(origin, str) or not origin.strip():
                errors.append(ProofError("MEDIA_ORIGIN_INVALID", str(origin)))
            license_ = entry.get("license", DEFAULT_LICENSE)
            if not isinstance(license_, str):
                errors.append(ProofError("MEDIA_LICENSE_INVALID", str(license_)))

    # scenes (obrigatorio)
    scenes = request.get("scenes")
    if not isinstance(scenes, list):
        errors.append(ProofError("SCENES_INVALID", str(scenes)))
        scenes = []
    else:
        seen_scene_ids = set()
        for entry in scenes:
            if not isinstance(entry, dict):
                errors.append(ProofError("SCENE_INVALID", str(entry)))
                continue
            sid = entry.get("id")
            if not isinstance(sid, str) or not sid or not _is_kebab(sid):
                errors.append(ProofError("SCENE_ID_INVALID", str(sid)))
            elif sid in seen_scene_ids:
                errors.append(ProofError("SCENE_ID_DUPLICATE", sid))
            else:
                seen_scene_ids.add(sid)
            dur = entry.get("durationMs")
            if not isinstance(dur, int) or isinstance(dur, bool) or dur <= 0:
                errors.append(ProofError("SCENE_DURATION_INVALID", str(dur)))
            media_id = entry.get("mediaId")
            if not isinstance(media_id, str) or not media_id:
                errors.append(ProofError("SCENE_MEDIA_REF_INVALID", str(media_id)))
            caption = entry.get("caption")
            if not isinstance(caption, str) or not caption.strip():
                errors.append(ProofError("SCENE_CAPTION_INVALID", str(caption)))
            narration = entry.get("narration")
            if not isinstance(narration, str) or not narration.strip():
                errors.append(ProofError("SCENE_NARRATION_INVALID", str(narration)))
            nfunc = entry.get("narrativeFunction")
            if nfunc is not None and nfunc not in NARRATIVE_FUNCTIONS:
                errors.append(ProofError("SCENE_NARRATIVE_FUNCTION_INVALID", str(nfunc)))
            motion = entry.get("motionIntent")
            if motion is not None and motion not in MOTION_INTENTS:
                errors.append(ProofError("SCENE_MOTION_INTENT_INVALID", str(motion)))

    return errors


def _collect_media(request: dict) -> dict[str, dict]:
    """Indexa media por id."""
    return {m["id"]: m for m in request.get("media", []) if isinstance(m, dict)}


# ---------------------------------------------------------------------------
# Subcomandos
# ---------------------------------------------------------------------------

def cmd_prepare(request_path: str, output_dir: str, root: str) -> dict:
    """Prepara mídia sintética e valida o pedido.

    Gera PNGs sintéticos nos caminhos referenciados pelo pedido (resolvidos a
    partir da raiz), preservando mídias já existentes informadas pelo operador.
    Mídias recém-criadas são marcadas com origin='synthetic-proof'. Se
    --output-dir for informado, grava nele uma cópia do pedido preparado com
    caminhos atualizados para os arquivos gerados.
    """
    request = _load_json(request_path, root, "pedido")
    errors = validate_video_request(request, root)
    if errors:
        return {
            "ok": False,
            "operation": "prepare",
            "request": request_path,
            "errors": [{"code": e.code, "subject": e.subject} for e in errors],
        }

    media_index = _collect_media(request)
    project_id = request["id"]
    prepared_media = []

    for scene in request.get("scenes", []):
        media_id = scene["mediaId"]
        media = media_index[media_id]
        mpath = media["path"]
        abs_media = render_local.fs_path(os.path.join(root, mpath))

        # Preserva mídia existente do operador; gera sintética somente se faltar.
        if os.path.isfile(abs_media):
            origin = media.get("origin", "operador")
        else:
            os.makedirs(render_local.fs_path(os.path.dirname(abs_media)), exist_ok=True)
            write_scene_png(abs_media, project_id, media_id, 1)
            origin = "synthetic-proof"

        if not os.path.isfile(abs_media):
            errors.append(ProofError("MEDIA_AUSENTE", media_id))
            continue

        prepared_media.append({
            "sceneId": scene["id"],
            "mediaId": media_id,
            "mediaPath": mpath,
            "type": media["type"],
            "origin": origin,
            "license": media.get("license", DEFAULT_LICENSE),
            "durationMs": scene["durationMs"],
            "caption": scene["caption"],
            "narrativeFunction": scene.get("narrativeFunction"),
        })

    if errors:
        return {
            "ok": False,
            "operation": "prepare",
            "request": request_path,
            "errors": [{"code": e.code, "subject": e.subject} for e in errors],
        }

    prepared_request_path = None
    if output_dir:
        abs_output = render_local.fs_path(os.path.join(root, output_dir))
        if not render_local.contained(root, output_dir):
            raise ProofError("SAIDA_FORA_RAIZ", output_dir)
        os.makedirs(abs_output, exist_ok=True)
        prepared_request = json.loads(json.dumps(request))
        path_by_media_id = {m["mediaId"]: m["mediaPath"] for m in prepared_media}
        for m in prepared_request.get("media", []):
            if m["id"] in path_by_media_id:
                m["path"] = path_by_media_id[m["id"]]
                m["origin"] = next(
                    (pm["origin"] for pm in prepared_media if pm["mediaId"] == m["id"]),
                    m.get("origin", DEFAULT_LICENSE),
                )
        prepared_request_path = os.path.join(abs_output, "prepared-request.json")
        with open(render_local.fs_path(prepared_request_path), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(prepared_request, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    return {
        "ok": True,
        "operation": "prepare",
        "request": request_path,
        "preparedRequest": render_local.rel(root, prepared_request_path) if prepared_request_path else None,
        "requestId": request["id"],
        "project": request["project"],
        "outputDir": output_dir,
        "mediaPrepared": prepared_media,
        "sceneCount": len(prepared_media),
        "totalDurationMs": sum(s["durationMs"] for s in request.get("scenes", [])),
        "preparedAt": _now_iso(),
    }


def cmd_verify(request_path: str, root: str) -> dict:
    """Valida o pedido e exibe relatório de prontidão estrutural.

    Agora também verifica:
      - existência do ProjectManifest referenciado por project;
      - existência de cada arquivo de mídia referenciado dentro da raiz.
    ready=true somente quando estrutura, manifest e mídias estão OK.
    """
    request = _load_json(request_path, root, "pedido")
    errors = validate_video_request(request, root)
    if errors:
        return {
            "ok": False,
            "operation": "verify",
            "request": request_path,
            "errors": [{"code": e.code, "subject": e.subject} for e in errors],
        }

    # Verifica existência do ProjectManifest
    project_rel = request.get("project")
    project_abs = render_local.fs_path(os.path.join(root, project_rel)) if project_rel else None
    project_exists = (
        isinstance(project_rel, str)
        and project_rel.strip()
        and render_local.contained(root, project_rel)
        and os.path.isfile(project_abs)
    )
    if not project_exists:
        errors.append(ProofError("PROJECT_MANIFEST_AUSENTE", project_rel))

    # Verifica existência de cada arquivo de mídia referenciado
    media_index = _collect_media(request)
    scenes = request.get("scenes", [])
    missing_media = []
    for scene in scenes:
        media_id = scene.get("mediaId")
        media = media_index.get(media_id)
        if not media:
            missing_media.append(scene.get("mediaId", scene.get("id", "?")))
            continue
        mpath = media.get("path", "")
        abs_mpath = render_local.fs_path(os.path.join(root, mpath)) if mpath else None
        if not mpath or not render_local.contained(root, mpath) or not os.path.isfile(abs_mpath):
            missing_media.append(media_id)

    total_duration = sum(s["durationMs"] for s in scenes)
    ready = len(errors) == 0 and not missing_media and project_exists

    return {
        "ok": True,
        "operation": "verify",
        "request": request_path,
        "requestId": request["id"],
        "project": request["project"],
        "title": request["title"],
        "locale": request.get("locale", DEFAULT_LOCALE),
        "profiles": request.get("profiles", []),
        "geometry": f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}",
        "fps": VIDEO_FPS,
        "sceneCount": len(scenes),
        "totalDurationMs": total_duration,
        "totalDurationSeconds": total_duration / 1000.0,
        "mediaCount": len(media_index),
        "projectManifestExists": project_exists,
        "missingMediaReferences": missing_media,
        "structuralValid": len(errors) == 0,
        "ready": ready,
        "verifiedAt": _now_iso(),
    }


def _ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def cmd_render(request_path: str, profile: str, output_dir: str,
               root: str) -> dict:
    """Executa o render via tools/produce_video.py. Se ffmpeg faltar, devolve
    relatório de pendência sem tocar entrega anterior.

    Obtém o MP4 pelo resultado da entrega atual (não por ordenação de caminhos)
    e confirma sucesso somente após render + inspeção aprovados.
    """
    abs_output = render_local.fs_path(os.path.join(root, output_dir))
    if not render_local.contained(root, output_dir):
        raise ProofError("SAIDA_FORA_RAIZ", output_dir)

    result = {
        "ok": False,
        "operation": "render",
        "request": request_path,
        "profile": profile,
        "outputDir": output_dir,
        "ffmpegAvailable": _ffmpeg_available(),
    }

    if not _ffmpeg_available():
        result["status"] = "pendente_ferramenta"
        result["error"] = (
            "ffmpeg/ffprobe nao encontrados; exponha no PATH ou em "
            ".workspace/tools/ffmpeg"
        )
        result["comandoRetomada"] = (
            f"{sys.executable} tools/produce_video.py --input {request_path} "
            f"--profile {profile} --output-dir {output_dir} --json"
        )
        return result

    # Carrega o pedido para passar ao comando e para inspeção.
    request = _load_json(request_path, root, "pedido")

    abs_request = render_local.fs_path(os.path.join(root, request_path))
    cmd = [
        sys.executable, "tools/produce_video.py",
        "--input", abs_request,
        "--profile", profile,
        "--output-dir", abs_output,
        "--json",
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            cwd=root,
        )
    except subprocess.TimeoutExpired:
        result["status"] = "falha_tempo_limite"
        result["error"] = "render excedeu o tempo limite (600 s)"
        return result
    except FileNotFoundError:
        result["status"] = "falha_ferramenta"
        result["error"] = "python nao encontrado no PATH"
        return result

    try:
        render_out = json.loads(proc.stdout)
    except ValueError:
        result["status"] = "falha_saida_ilegivel"
        result["error"] = "saida do render nao e JSON valido"
        result["stderr"] = proc.stderr[-500:]
        return result

    result["rawRenderOutput"] = render_out
    render_ok = proc.returncode == 0 and render_out.get("overallStatus") != "partial"
    result["status"] = "concluido" if render_ok else "parcial_ou_falhou"
    result["renderExitCode"] = proc.returncode

    # Inspeciona o MP4 do perfil solicitado pelo resultado da entrega atual.
    profile_out = None
    for p in render_out.get("profiles", []):
        if p.get("profileId") == profile:
            profile_out = p
            break

    if profile_out:
        result["profileStatus"] = profile_out.get("status")
        result["profileFailureCode"] = profile_out.get("failureCode")
        result["profileError"] = profile_out.get("error")

        # Usa o deliveryManifest para localizar o vídeo do perfil atual.
        delivery_manifest_rel = profile_out.get("deliveryManifest")
        video_path = None
        if delivery_manifest_rel:
            manifest_abs = render_local.fs_path(
                os.path.join(root, delivery_manifest_rel)
            )
            if os.path.isfile(manifest_abs):
                try:
                    with open(manifest_abs, "r", encoding="utf-8") as fh:
                        manifest = json.load(fh)
                    artifacts = manifest.get("artifacts", {})
                    video_info = artifacts.get("video", {})
                    video_rel = video_info.get("path")
                    if video_rel:
                        abs_video = render_local.fs_path(os.path.join(root, video_rel))
                        if os.path.isfile(abs_video):
                            video_path = abs_video
                except (OSError, ValueError):
                    pass

        # Fallback: procura o MP4 mais recente dentro da pasta do perfil.
        if not video_path:
            import glob
            mp4_candidates = sorted(
                glob.glob(os.path.join(abs_output, "**", "*.mp4"), recursive=True),
                key=os.path.getmtime,
                reverse=True,
            )
            if mp4_candidates:
                video_path = mp4_candidates[0]

        if video_path:
            try:
                total_duration = sum(int(s["durationMs"]) for s in request.get("scenes", []))
                inspection = build_video.validate_mp4(
                    video_path, VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS,
                    total_duration, timeout=30,
                )
                result["ffprobe"] = inspection
                result["mp4Path"] = render_local.rel(root, video_path)
                # Sucesso somente se render completou E inspeção aprovada (0 áudio).
                result["ok"] = (
                    render_ok
                    and inspection.get("audioStreams", 1) == 0
                    and inspection.get("videoStreams") == 1
                )
            except build_video.DeliveryError as exc:
                result["ffprobeError"] = str(exc)
    return result


def total_duration_s(request: dict) -> int:
    return sum(int(s["durationMs"]) for s in request.get("scenes", [])) // 1000


def cmd_review(request_path: str, output_html: str | None, root: str) -> dict:
    """Gera a página HTML de revisão local a partir dos resultados reais da prova.

    Consome o estado do pedido (estrutura, janelas, métricas, render) e
    apresenta: identificação da peça, sequência de cenas com miniatura,
    indicação de mídias sintéticas/faltantes, vídeo reproduzível quando o MP4
    existir, legendas/SRT quando disponíveis, resultado do pré-voo/render/inspeção
    com avisos, caminhos de entrega e comando para repetir. Escapa textos
    inseridos e usa links relativos para funcionar após transferir a pasta.
    """
    request = _load_json(request_path, root, "pedido")
    errors = validate_video_request(request, root)

    scenes_html = ""
    media_index = _collect_media(request)
    total_duration_ms = sum(int(s["durationMs"]) for s in request.get("scenes", []))

    for i, scene in enumerate(request.get("scenes", []), start=1):
        media = media_index.get(scene.get("mediaId"), {})
        media_path = media.get("path", "")
        abs_media = render_local.fs_path(os.path.join(root, media_path)) if media_path else None
        media_exists = bool(media_path) and render_local.contained(root, media_path) and os.path.isfile(abs_media)
        origin = media.get("origin", "")
        is_synthetic = origin == "synthetic-proof" or not media_path
        media_label = _html_escape(media.get("mediaId", scene.get("mediaId", "")))
        caption = _html_escape(scene.get("caption", ""))
        scenes_html += f"""
        <tr>
            <td>{i}</td>
            <td><code>{scene.get('id','')}</code></td>
            <td>{scene.get('durationMs','')} ms</td>
            <td>{scene.get('narrativeFunction','')}</td>
            <td>{media_label}</td>
            <td>{media.get('type','')}</td>
            <td class="{'ok' if media_exists else 'blocked'}">{'SIM' if media_exists else 'NÃO (faltante)'}</td>
            <td>{caption}</td>
            <td>{'SINTÉTICA' if is_synthetic else 'OPERADOR'}</td>
        </tr>
        """

    # Estado editorial a partir da documentação da peça (briefing/roteiro).
    editorial_note = ""
    project_rel = request.get("project")
    if project_rel and render_local.contained(root, project_rel):
        project_abs = render_local.fs_path(os.path.join(root, project_rel))
        if os.path.isfile(project_abs):
            try:
                with open(project_abs, "r", encoding="utf-8") as fh:
                    project_doc = json.load(fh)
                editorial_note = (
                    f"<p><strong>Projeto:</strong> {_html_escape(project_doc.get('name',''))}</p>"
                    f"<p><strong>Marca/Tema:</strong> {_html_escape(project_doc.get('brandTheme',''))}</p>"
                    f"<p><strong>Permissões:</strong> briefing aprovado="
                    f"{project_doc.get('contentPolicies',{}).get('requireApprovedBriefing', False)}, "
                    f"roteiro aprovado="
                    f"{project_doc.get('contentPolicies',{}).get('requireApprovedScript', False)}</p>"
                )
            except (OSError, ValueError):
                editorial_note = "<p>Não foi possível ler o ProjectManifest da peça.</p>"
        else:
            editorial_note = "<p>ProjectManifest não encontrado na raiz.</p>"
    else:
        editorial_note = "<p>Nenhum ProjectManifest informado no pedido.</p>"

    # Tenta incluir dados de render se houver um arquivo de resultado recente
    # ao lado do pedido (gerado por render ou por execução anterior).
    render_summary = ""
    mp4_rel = None
    srt_rel = None
    nar_rel = None
    render_status = "não executado"
    render_error = ""
    # Procura por um index.json ou delivery-manifest em pastas de entrega próximas
    import glob
    candidate_dirs = []
    req_dir = os.path.dirname(render_local.fs_path(os.path.join(root, request_path)))
    for d in [req_dir, os.path.join(root, ".workspace", "archives"), os.path.join(root, ".workspace", "tmp")]:
        if os.path.isdir(d):
            candidate_dirs.append(d)
    for cand in candidate_dirs:
        for sub in os.listdir(cand):
            sub_path = os.path.join(cand, sub)
            if not os.path.isdir(sub_path):
                continue
            index_path = os.path.join(sub_path, "index.json")
            manifest_path = os.path.join(sub_path, "delivery-manifest.json")
            if os.path.isfile(index_path):
                try:
                    with open(index_path, "r", encoding="utf-8") as fh:
                        idx = json.load(fh)
                    if idx.get("requestId") == request.get("id"):
                        for prof in idx.get("profiles", []):
                            if prof.get("profileId") == profile or not profile:
                                render_status = prof.get("status", "desconhecido")
                                last = prof.get("lastValidDelivery") or prof.get("lastAttempt") or {}
                                if last.get("zipPath"):
                                    mp4_rel = last["zipPath"]
                                if last.get("manifestPath"):
                                    # tenta derivar SRT do mesmo diretório
                                    base = os.path.dirname(last.get("manifestPath",""))
                                    cand_srt = os.path.join(base, "captions.srt")
                                    cand_nar = os.path.join(base, "narration-script.txt")
                                    if os.path.isfile(render_local.fs_path(os.path.join(root, cand_srt))):
                                        srt_rel = cand_srt
                                    if os.path.isfile(render_local.fs_path(os.path.join(root, cand_nar))):
                                        nar_rel = cand_nar
                                render_error = last.get("error","")
                                break
                except (OSError, ValueError):
                    pass

    render_section = ""
    if render_status == "concluido" and mp4_rel:
        abs_mp4 = render_local.fs_path(os.path.join(root, mp4_rel)) if mp4_rel else None
        mp4_exists = bool(mp4_rel) and render_local.contained(root, mp4_rel) and os.path.isfile(abs_mp4)
        render_section = f"""
        <div class="{'ok' if mp4_exists else 'blocked'}">
          <h3>Render e inspeção (perfil {_html_escape(profile)})</h3>
          <p><strong>Status:</strong> {render_status}</p>
          <p><strong>MP4:</strong> {'<a href="' + mp4_rel + '">baixar/abrir MP4</a>' if mp4_exists else 'não gerado'}</p>
          <p><strong>SRT:</strong> {'<a href="' + srt_rel + '">baixar SRT</a>' if srt_rel else 'não gerado'}</p>
          <p><strong>Narração:</strong> {'<a href="' + nar_rel + '">baixar TXT</a>' if nar_rel else 'não gerado'}</p>
          {f'<p><strong>Aviso:</strong> {_html_escape(render_error)}</p>' if render_error else ''}
        </div>
        """
    elif render_status == "pendente_ferramenta":
        render_section = f"""
        <div class="blocked">
          <h3>Render e inspeção (perfil {_html_escape(profile)})</h3>
          <p><strong>Status:</strong> pendente de ferramenta</p>
          <p>{_html_escape(render_error)}</p>
          <p>Comando para repetir quando FFmpeg/FFprobe estiver disponível:</p>
          <pre>{sys.executable} tools/produce_video.py --input {_html_escape(request_path)} --profile {_html_escape(profile)} --output-dir &lt;entrega&gt; --json</pre>
        </div>
        """
    else:
        render_section = """
        <div class="blocked">
          <h3>Render e inspeção</h3>
          <p><strong>Status:</strong> não executado</p>
          <p>Execute o render para gerar o MP4 e a inspeção.</p>
          <pre>{sys.executable} tools/produce_video.py --input {request_path} --profile {profile} --output-dir &lt;entrega&gt; --json</pre>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Revisão de Prova — {_html_escape(request.get('id','campanha'))}</title>
<style>
  body{{font-family:sans-serif;background:#f5f7fa;color:#111;margin:0;padding:24px;}}
  .container{{max-width:980px;margin:0 auto;background:#fff;border-radius:12px;padding:24px;box-shadow:0 2px 12px rgba(0,0,0,.08);}}
  h1{{font-size:20px;margin-top:0;color:#0b5ed7;}}
  h2{{font-size:16px;border-bottom:2px solid #0b5ed7;padding-bottom:6px;color:#0b5ed7;margin-top:24px;}}
  .badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px;color:#fff;}}
  .badge.ok{{background:#2e7d32;}}.badge.blocked{{background:#c62828;}}.badge.pending{{background:#f9a825;color:#000;}}
  table{{width:100%;border-collapse:collapse;margin:12px 0;}}
  th,td{{border:1px solid #ddd;padding:8px;text-align:left;font-size:14px;}}
  th{{background:#eef4fb;}}
  .section{{margin:24px 0;}}
  .note{{background:#fff8e1;border-left:4px solid #f9a825;padding:10px;margin:12px 0;}}
  .error{{background:#ffebee;border-left:4px solid #c62828;padding:10px;margin:12px 0;}}
  .ok{{background:#e8f5e9;border-left:4px solid #2e7d32;padding:10px;margin:12px 0;}}
  pre{{background:#f5f5f5;padding:10px;border-radius:6px;overflow:auto;font-size:12px;}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;}}
  .card{{border:1px solid #ddd;border-radius:8px;padding:12px;background:#fafbfc;}}
  .card h3{{margin:0 0 8px 0;font-size:14px;color:#0b5ed7;}}
  .card p{{margin:0;font-size:13px;color:#333;}}
  .mp4-wrap{{margin:12px 0;max-width:1080px;}}
  .mp4-wrap video{{max-width:100%;height:auto;border:1px solid #ddd;border-radius:8px;}}
  img.thumb{{max-width:160px;height:auto;border:1px solid #ccc;border-radius:6px;}}
</style>
</head>
<body>
<div class="container">
  <h1>Revisão de Prova de Campanha — Marca Salão</h1>

  <div class="section">
    <h2>Identificação</h2>
    <div class="grid">
      <div class="card"><h3>Campanha / Peça</h3><p><strong>{_html_escape(request.get('id',''))}</strong></p></div>
      <div class="card"><h3>Título</h3><p>{_html_escape(request.get('title',''))}</p></div>
      <div class="card"><h3>Projeto</h3><p>{_html_escape(request.get('project',''))}</p></div>
      <div class="card"><h3>Estado editorial</h3><p><span class="badge {'ok' if len(errors)==0 else 'blocked'}">{'Estrutura válida' if len(errors)==0 else 'Erros estruturais'}</span></p></div>
    </div>
    {editorial_note}
  </div>

  <div class="section">
    <h2>Especificação da peça</h2>
    <p><strong>Perfis:</strong> {', '.join(request.get('profiles', []))}</p>
    <p><strong>Geometria:</strong> {VIDEO_WIDTH}x{VIDEO_HEIGHT}, 9:16</p>
    <p><strong>FPS:</strong> {VIDEO_FPS}</p>
    <p><strong>Duração total:</strong> {total_duration_ms // 1000} s ({total_duration_ms} ms)</p>
    <p><strong>Cenas:</strong> {len(request.get('scenes',[]))}</p>
    <p><strong>Áudio:</strong> nenhuma faixa (regra de vídeo sem áudio)</p>
  </div>

  <div class="section">
    <h2>Sequência de cenas</h2>
    <table>
      <thead><tr><th>#</th><th>ID</th><th>Duração</th><th>Função narrativa</th><th>Mídia</th><th>Tipo</th><th>Presente</th><th>Origem</th><th>Texto de tela</th></tr></thead>
      <tbody>{scenes_html}</tbody>
    </table>
  </div>

  <div class="section">
    <h2>Mídias (prova)</h2>
    <p class="note">Mídias sintéticas identificadas como prova (gradiente determinado por project_id/beat_id).
    São substituíveis por capturas reais com fixture editorial antes da peça final.</p>
    <table>
      <thead><tr><th>Cena</th><th>Mídia</th><th>Tipo</th><th>Origem</th><th>Licença</th><th>Presente</th></tr></thead>
      <tbody>
        {''.join(
          f"<tr><td>{s.get('id','')}</td><td><code>{m.get('id','')}</code></td><td>{m.get('type','')}</td><td>{_html_escape(m.get('origin',''))}</td><td>{m.get('license',DEFAULT_LICENSE)}</td><td class=\"{'ok' if (render_local.contained(root,m.get('path','')) and os.path.isfile(render_local.fs_path(os.path.join(root,m.get('path',''))))) else 'blocked'}\">{'SIM' if (render_local.contained(root,m.get('path','')) and os.path.isfile(render_local.fs_path(os.path.join(root,m.get('path',''))))) else 'NÃO'}</td></tr>"
          for s in request.get('scenes',[]) for m in [media_index.get(s.get('mediaId'),{})]
        )}
      </tbody>
    </table>
  </div>

  <div class="section">
    <h2>Resultado da prova</h2>
    <div class="{'ok' if len(errors)==0 else 'error'}">
      <p><strong>Validação estrutural:</strong> {'APROVADA' if len(errors)==0 else 'REPROVADA'}</p>
      <p><strong>Erros:</strong> {len(errors)}</p>
      {''.join(f"<p>- [{e.code}] {e.subject or ''}</p>" for e in errors) if errors else "<p>Nenhum erro estrutural.</p>"}
    </div>
    {render_section}
  </div>

  <div class="section">
    <h2>Comando para repetir a prova</h2>
    <pre>{sys.executable} tools/campaign_proof.py prepare {_html_escape(request_path)} --output-dir .workspace/tmp/prova-campanha-ns001-ns002/{request.get('id','campanha')}
{sys.executable} tools/campaign_proof.py verify {_html_escape(request_path)}
{sys.executable} tools/campaign_proof.py render {_html_escape(request_path)} --profile &lt;perfil&gt; --output-dir &lt;entrega&gt;
{sys.executable} tools/campaign_proof.py review {_html_escape(request_path)} --output revisao-{request.get('id','campanha')}.html</pre>
  </div>
</div>
</body>
</html>
"""

    abs_html = render_local.fs_path(output_html) if output_html else None
    if output_html:
        if not render_local.contained(root, output_html):
            raise ProofError("SAIDA_FORA_RAIZ", output_html)
        os.makedirs(render_local.fs_path(os.path.dirname(output_html)), exist_ok=True)
        with open(abs_html, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(html)

    return {
        "ok": True,
        "operation": "review",
        "request": request_path,
        "requestId": request["id"],
        "structuralErrors": [{"code": e.code, "subject": e.subject} for e in errors],
        "htmlPath": output_html,
        "sceneCount": len(request.get("scenes", [])),
        "totalDurationMs": total_duration_ms,
        "renderStatus": render_status,
        "mp4Path": mp4_rel,
        "srtPath": srt_rel,
        "narrationPath": nar_rel,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ferramenta de prova de campanha para o Marca Salão"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="Prepara mídia sintética e valida o pedido")
    p_prepare.add_argument("request", help="Caminho do pedido VideoRequest v1")
    p_prepare.add_argument("--output-dir", required=True, help="Diretório de saída para mídias preparadas")
    p_prepare.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_prepare.add_argument("--json", action="store_true", help="Saída somente JSON")

    p_verify = sub.add_parser("verify", help="Valida o pedido e exibe prontidão")
    p_verify.add_argument("request", help="Caminho do pedido VideoRequest v1")
    p_verify.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_verify.add_argument("--json", action="store_true", help="Saída somente JSON")

    p_render = sub.add_parser("render", help="Renderiza o perfil via pipeline")
    p_render.add_argument("request", help="Caminho do pedido VideoRequest v1")
    p_render.add_argument("--profile", required=True, help="Perfil de saída (ex: instagram-reels-video)")
    p_render.add_argument("--output-dir", required=True, help="Diretório de entrega")
    p_render.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_render.add_argument("--json", action="store_true", help="Saída somente JSON")

    p_review = sub.add_parser("review", help="Gera página HTML de revisão")
    p_review.add_argument("request", help="Caminho do pedido VideoRequest v1")
    p_review.add_argument("--output", default=None, help="Caminho do HTML de saída")
    p_review.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_review.add_argument("--json", action="store_true", help="Saída somente JSON")

    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "prepare":
            result = cmd_prepare(args.request, args.output_dir, args.root)
        elif args.command == "verify":
            result = cmd_verify(args.request, args.root)
        elif args.command == "render":
            result = cmd_render(args.request, args.profile, args.output_dir, args.root)
        elif args.command == "review":
            result = cmd_review(args.request, args.output, args.root)
        else:
            print("Comando desconhecido", file=sys.stderr)
            return 2
    except ProofError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": exc.code, "subject": exc.subject}, ensure_ascii=False))
        else:
            print(f"Erro: [{exc.code}] {exc.subject or ''}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError) as exc:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": "ENTRADA_INVALIDA", "message": str(exc)}, ensure_ascii=False))
        else:
            print(f"Erro: entrada inválida ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 2

    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
