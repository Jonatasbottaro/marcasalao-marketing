"""Doutor local de higiene do workspace (Etapa 6 - Agente 6).

Audita, em uma unica passada, o estado do ``.workspace/`` do checkout PRINCIPAL
(compartilhado por todas as worktrees):

  1. ffmpeg              presenca e versao de ``ffmpeg.exe``/``ffprobe.exe`` em
                         ``<MAIN_ROOT>/.workspace/tools/ffmpeg/``.
  2. archives            cruzamento dos MP4/PNG locais em ``.workspace/archives/``
                         com os SHA-256 declarados em ``manifest.json`` e
                         ``derivatives.json`` das entregas (9:16, 1:1, 16:9,
                         cover, thumb-16x9 e preview-formats). Também detecta metadados ffprobe divergentes e mídias órfãs.
  3. worktrees           registro/diretorio de worktrees e arquivos nao rastreados.
  4. tmp                 higiene de ``.workspace/tmp/``; no modo ``--clean-tmp``
                         remove somente subdiretorios descartaveis, preservando
                         ``aprovacoes-titular.json`` e os irmaos ``archives/``,
                         ``tools/`` e ``devlogs/``.

A raiz principal é resolvida por ``git rev-parse --git-common-dir``, exatamente
como em ``bootstrap_ffmpeg.py``, para que o diagnostico aponte para o mesmo
``.workspace/`` compartilhado mesmo quando executado dentro de uma worktree.
Sem git disponivel, cai para o diretorio informado (util em testes isolados).

CLI:
    python tools/workspace_doctor.py [--check | --clean-tmp] [--json] [--root DIR]
    python tools/workspace_doctor.py snapshot export [--out DIR/ARQUIVO.zip] [--json] [--root DIR]
    python tools/workspace_doctor.py snapshot verify [--archive ARQUIVO.zip] [--json] [--root DIR]

API:
    run_workspace_doctor(root=".", clean_tmp=False) -> dict
    audit_manifest_integrity(root=".", source_root=None) -> dict
    export_snapshot(root=".", out=None) -> dict
    verify_snapshot(root=".", archive=None) -> dict

O snapshot e gravado somente sob ``<MAIN_ROOT>/.workspace/snapshots/``, nunca
no indice do Git; o indice ``snapshot-index.json`` usa apenas caminhos relativos.

Exit codes: 0 sem erros; 1 com erros; 2 erro de uso/execucao.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

WORKSPACE_REL = (".workspace",)
ARCHIVES_REL = (".workspace", "archives")
TOOLS_FFMPEG_REL = (".workspace", "tools", "ffmpeg")
TMP_REL = (".workspace", "tmp")
DEVLOGS_REL = (".workspace", "devlogs")
WORKTREES_REL = (".workspace", "worktrees")
DELIVERIES_REL = ("02-reels-shorts", "deliveries")
SNAPSHOTS_REL = (".workspace", "snapshots")
SNAPSHOT_INDEX_NAME = "snapshot-index.json"
SNAPSHOT_PREFIX = "workspace-snapshot-"

APPROVALS_FILENAME = "aprovacoes-titular.json"
PROTECTED_TMP_NAMES = frozenset({APPROVALS_FILENAME})
PROTECTED_WORKSPACE_DIRS = ("archives", "tools", "devlogs")
MEDIA_EXTENSIONS = (".mp4", ".png")
# Campos escalares comparados entre o ffprobe declarado no manifesto e o arquivo local.
FFPROBE_FIELDS = (
    "videoStreams", "audioStreams", "codec", "width", "height",
    "fps", "pixFmt", "duration", "audioCodec", "audioSampleRate", "audioChannels",
)
FFPROBE_NUMERIC_FIELDS = frozenset({
    "videoStreams", "audioStreams", "width", "height", "fps", "duration",
    "audioSampleRate", "audioChannels",
})

DERIVATIVE_KINDS = ("1x1", "16x9", "cover", "thumb-16x9", "preview-formats")
VERSION_RE = re.compile(r"\b(ffmpeg|ffprobe)\s+version\s+(\S+)", re.IGNORECASE)

SECTION_NAMES = (
    ("ffmpeg", "FFmpeg/FFprobe portateis"),
    ("archives", "Integridade de midia em archives"),
    ("worktrees", "Higiene de worktrees e Git"),
    ("tmp", "Higiene de tmp"),
)


class WorkspaceDoctorError(Exception):
    """Erro controlado de execucao (raiz ausente, caminho fora da raiz)."""


# ---------------------------------------------------------------------------
# Helpers stdlib
# ---------------------------------------------------------------------------
def _fs_path(path: str) -> str:
    """Suporte a caminhos longos no Windows, sem dependencias externas."""
    value = str(path)
    if os.name != "nt" or value.startswith("\\\\?\\"):
        return value
    abs_path = os.path.abspath(value)
    if len(abs_path) < 248:
        return value
    if abs_path.startswith("\\\\"):
        return "\\\\?\\UNC\\" + abs_path.lstrip("\\")
    return "\\\\?\\" + abs_path


def _contained(root: str, path: str) -> bool:
    """True quando ``path`` (realpath) esta dentro de ``root`` (realpath)."""
    root_real = os.path.realpath(root)
    path_real = os.path.realpath(path)
    try:
        return os.path.commonpath([root_real, path_real]) == root_real
    except ValueError:  # volumes diferentes no Windows
        return False


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(_fs_path(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _join_rel(root: str, rel_path: str) -> str:
    return os.path.join(root, *str(rel_path).replace("\\", "/").split("/"))


def _run_git(root: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", root, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise WorkspaceDoctorError(
            f"git {' '.join(args)} falhou: {proc.stderr.strip()}"
        )
    return proc.stdout


def _resolve_main_root(root: str | os.PathLike = ".") -> str:
    """Raiz do checkout principal a partir de ``--git-common-dir``."""
    root_abs = os.path.abspath(str(root or "."))
    try:
        res = subprocess.run(
            ["git", "-C", root_abs, "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return root_abs
    if res.returncode != 0:
        return root_abs
    common = (res.stdout or "").strip()
    if not common:
        return root_abs
    if not os.path.isabs(common):
        common = os.path.join(root_abs, common)
    common = os.path.abspath(os.path.normpath(common))
    parent = os.path.dirname(common)
    return parent or root_abs


def _read_json(path: str) -> dict:
    with open(_fs_path(path), "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("conteudo JSON nao e um objeto")
    return data


def _error(code: str, message: str) -> dict:
    return {"severity": "error", "code": code, "message": message}


def _warning(code: str, message: str) -> dict:
    return {"severity": "warning", "code": code, "message": message}


def _status(problems: list[dict]) -> str:
    if any(p["severity"] == "error" for p in problems):
        return "fail"
    if any(p["severity"] == "warning" for p in problems):
        return "warn"
    return "ok"


def _section(section_id: str, problems: list[dict]) -> dict:
    return {
        "id": section_id,
        "name": dict(SECTION_NAMES)[section_id],
        "ok": not any(p["severity"] == "error" for p in problems),
        "status": _status(problems),
        "problems": problems,
    }


def _stdout_utf8() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. FFmpeg / FFprobe
# ---------------------------------------------------------------------------
def _exe_names() -> tuple[str, str]:
    """Nomes no Windows; tambem aceita os nomes sem extensao em outras plataformas."""
    return ("ffmpeg.exe", "ffprobe.exe") if os.name == "nt" else ("ffmpeg", "ffprobe")


def _probe_version(path: str) -> tuple[bool, str | None, str | None]:
    """Roda ``<path> -version``. Devolve (ok, primeira_linha, versao)."""
    if not path or not os.path.isfile(_fs_path(path)):
        return False, None, None
    try:
        res = subprocess.run(
            [_fs_path(path), "-version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False, None, None
    if res.returncode != 0:
        return False, None, None
    first = (res.stdout or res.stderr or "").strip().splitlines()
    line = first[0].strip() if first else ""
    match = VERSION_RE.search(line)
    return True, line, (match.group(2) if match else None)


def _check_ffmpeg(workspace_root: str) -> tuple[list[dict], dict]:
    problems: list[dict] = []
    tools_dir = os.path.join(workspace_root, "tools", "ffmpeg")
    ff_name, fp_name = _exe_names()
    summary: dict = {"toolsDir": os.path.relpath(tools_dir, os.path.dirname(workspace_root)).replace(os.sep, "/")}
    for label, filename in (("ffmpeg", ff_name), ("ffprobe", fp_name)):
        path = os.path.join(tools_dir, filename)
        entry: dict = {"path": os.path.relpath(path, os.path.dirname(workspace_root)).replace(os.sep, "/"),
                       "present": False, "version": None, "valid": False}
        if not os.path.isfile(_fs_path(path)):
            problems.append(_error(f"{label.upper()}_AUSENTE", f"{filename} ausente em .workspace/tools/ffmpeg/"))
            summary[label] = entry
            continue
        ok, first_line, version = _probe_version(path)
        entry.update({"present": True, "valid": ok, "version": version, "firstLine": first_line})
        if not ok:
            problems.append(_error(f"{label.upper()}_INVALIDO", f"{filename} nao respondeu a -version"))
        summary[label] = entry
    return problems, summary


# ---------------------------------------------------------------------------
# 1b. Metadados ffprobe (comparacao com o manifesto)
# ---------------------------------------------------------------------------
def _ffprobe_metadata(workspace_root: str, path: str) -> dict | None:
    """Le metadados do arquivo com o ffprobe portatil; None se indisponivel."""
    ffprobe = os.path.join(workspace_root, "tools", "ffmpeg", _exe_names()[1])
    if not os.path.isfile(_fs_path(ffprobe)):
        return None
    try:
        res = subprocess.run(
            [_fs_path(ffprobe), "-v", "error", "-show_streams", "-show_format",
             "-of", "json", _fs_path(path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if res.returncode != 0:
        return None
    try:
        payload = json.loads(res.stdout)
    except ValueError:
        return None
    streams = payload.get("streams") or []
    videos = [s for s in streams if str(s.get("codec_type", "")).lower() == "video"]
    audios = [s for s in streams if str(s.get("codec_type", "")).lower() == "audio"]
    video = videos[0] if videos else {}
    audio = audios[0] if audios else {}

    def rate(value: object) -> float | None:
        if value in (None, "", "0/0", "N/A"):
            return None
        text = str(value)
        if "/" in text:
            numerator, _, denominator = text.partition("/")
            try:
                den = float(denominator)
                return float(numerator) / den if den else None
            except ValueError:
                return None
        try:
            return float(text)
        except ValueError:
            return None

    def number(*values: object) -> float | None:
        for value in values:
            if value in (None, "", "N/A"):
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return None

    fmt = payload.get("format") or {}
    return {
        "videoStreams": len(videos),
        "audioStreams": len(audios),
        "codec": video.get("codec_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "pixFmt": video.get("pix_fmt"),
        "fps": rate(video.get("avg_frame_rate") or video.get("r_frame_rate")),
        "duration": number(fmt.get("duration"), video.get("duration")),
        "audioCodec": audio.get("codec_name"),
        "audioSampleRate": number(audio.get("sample_rate")),
        "audioChannels": number(audio.get("channels")),
    }


def _probe_field_equal(expected: object, actual: object) -> bool:
    if expected is None or actual is None:
        return expected == actual
    if isinstance(expected, bool) or isinstance(actual, bool):
        return expected == actual
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return abs(float(expected) - float(actual)) <= 1e-3
    if isinstance(expected, str) and isinstance(actual, str):
        return expected.strip().lower() == actual.strip().lower()
    return expected == actual


def _normalize_probe_value(field: str, value: object) -> object:
    """Normaliza strings como '30/1' ou 'H264' antes da comparacao."""
    if value is None:
        return None
    if field in FFPROBE_NUMERIC_FIELDS:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        text = str(value).strip()
        if "/" in text:
            numerator, _, denominator = text.partition("/")
            try:
                den = float(denominator)
                return float(numerator) / den if den else None
            except ValueError:
                return None
        try:
            return float(text)
        except ValueError:
            return None
    return str(value).strip().lower()


def _compare_ffprobe(declared: dict, actual: dict) -> list[str]:
    """Compara somente os campos efetivamente declarados no manifesto."""
    diffs: list[str] = []
    for field in FFPROBE_FIELDS:
        if field not in declared or declared[field] is None:
            continue
        raw_right = actual.get(field)
        if raw_right is None:
            # ffprobe nao informou o campo (ex.: duration de imagem): nao ha
            # base para afirmar divergencia.
            continue
        left = _normalize_probe_value(field, declared[field])
        right = _normalize_probe_value(field, raw_right)
        if not _probe_field_equal(left, right):
            diffs.append(f"{field}: manifesto={declared[field]!r}, arquivo={actual.get(field)!r}")
    return diffs


# ---------------------------------------------------------------------------
# 2. Archives x hashes declarados
# ---------------------------------------------------------------------------
def _classify_derivative(key: str, entry: dict) -> str:
    lowered = key.lower()
    if "thumb" in lowered:
        return "thumb-16x9"
    if "16x9" in lowered:
        return "16x9"
    if "1x1" in lowered:
        return "1x1"
    if "cover" in lowered:
        return "cover"
    if "preview" in lowered:
        return "preview-formats"
    kind = str(entry.get("kind", "")).lower()
    for candidate in DERIVATIVE_KINDS:
        if candidate in kind:
            return candidate
    return key


def _resolve_archive_target(resolution_root: str, archives_real: str, declared: str) -> str | None:
    """Resolve um caminho declarado, recusando qualquer saida de archives/.

    ``resolution_root`` e a raiz PRINCIPAL: as declaracoes ``.workspace/...``
    gravadas nos manifestos sao relativas a ela, mesmo quando o manifesto foi
    lido de uma worktree.
    """
    norm = str(declared).replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    if not norm:
        return None
    candidate = os.path.realpath(_join_rel(resolution_root, norm))
    return candidate if _contained(archives_real, candidate) else None


def _collect_declared_media(
    source_root: str, resolution_root: str, archives_real: str
) -> tuple[dict, list[dict]]:
    declared: dict[str, dict] = {}
    problems: list[dict] = []
    deliveries = os.path.join(source_root, *DELIVERIES_REL)
    fs_deliveries = _fs_path(deliveries)
    if not os.path.isdir(fs_deliveries):
        return declared, problems

    def register(declared_path: object, sha256: object, kind: str, label: str, ffprobe: object = None) -> None:
        if not isinstance(declared_path, str) or not isinstance(sha256, str) or not sha256:
            problems.append(_error("DECLARACAO_INCOMPLETA", f"{label}: path/sha256 ausente"))
            return
        target = _resolve_archive_target(resolution_root, archives_real, declared_path)
        if target is None:
            problems.append(
                _error("PATH_OUTSIDE_ARCHIVES", f"{label}: '{declared_path}' fora de .workspace/archives/")
            )
            return
        key = os.path.relpath(target, resolution_root).replace(os.sep, "/")
        record = {
            "sha256": sha256.lower(), "kind": kind, "label": label,
            "labels": [label],
            "ffprobe": ffprobe if isinstance(ffprobe, dict) else None,
        }
        previous = declared.get(key)
        if previous is not None and previous["sha256"] != record["sha256"]:
            problems.append(
                _error(
                    "DECLARACAO_CONFLITANTE",
                    f"{key}: hashes divergentes entre {previous['label']} e {label}",
                )
            )
            return
        if previous is not None and label not in previous["labels"]:
            previous["labels"].append(label)
            if previous.get("ffprobe") is None and record.get("ffprobe") is not None:
                previous["ffprobe"] = record["ffprobe"]
            return
        declared[key] = record

    for tenant in sorted(os.listdir(fs_deliveries)):
        tenant_dir = os.path.join(deliveries, tenant)
        if not os.path.isdir(_fs_path(tenant_dir)):
            continue
        for slug in sorted(os.listdir(_fs_path(tenant_dir))):
            delivery_dir = os.path.join(tenant_dir, slug)
            if not os.path.isdir(_fs_path(delivery_dir)):
                continue
            label_base = f"{tenant}/{slug}"
            manifest_path = os.path.join(delivery_dir, "manifest.json")
            if os.path.isfile(_fs_path(manifest_path)):
                try:
                    manifest = _read_json(manifest_path)
                except (OSError, ValueError) as exc:
                    problems.append(_error("MANIFEST_INVALIDO", f"{label_base}: {exc}"))
                else:
                    video = (manifest.get("artifacts") or {}).get("video") or {}
                    archive_path = video.get("archivePath") or video.get("path")
                    register(
                        archive_path, video.get("sha256"), "9:16",
                        f"{label_base}:manifest.video", video.get("ffprobe"),
                    )
            derivatives_path = os.path.join(delivery_dir, "derivatives.json")
            if os.path.isfile(_fs_path(derivatives_path)):
                try:
                    data = _read_json(derivatives_path)
                except (OSError, ValueError) as exc:
                    problems.append(_error("DERIVATIVES_INVALIDO", f"{label_base}: {exc}"))
                else:
                    source = data.get("source") or {}
                    register(
                        source.get("path"), source.get("sha256"), "9:16",
                        f"{label_base}:derivatives.source", source.get("ffprobe"),
                    )
                    for key, entry in (data.get("derivatives") or {}).items():
                        if isinstance(entry, dict):
                            register(
                                entry.get("path"),
                                entry.get("sha256"),
                                _classify_derivative(key, entry),
                                f"{label_base}:derivatives.{key}",
                                entry.get("ffprobe"),
                            )
    return declared, problems


def _audit_archives(
    resolution_root: str, workspace_root: str, source_root: str | None = None
) -> tuple[list[dict], dict]:
    problems: list[dict] = []
    archives_real = os.path.realpath(os.path.join(workspace_root, "archives"))
    declared, declaration_problems = _collect_declared_media(
        source_root or resolution_root, resolution_root, archives_real
    )
    problems.extend(declaration_problems)

    per_kind: dict[str, int] = {}
    verified = divergent = undeclared = 0
    probe_divergente = probe_indisponivel = 0
    seen: set[str] = set()
    fs_archives = _fs_path(archives_real)
    if os.path.isdir(fs_archives):
        for dirpath, dirnames, filenames in os.walk(fs_archives, followlinks=False):
            # Nunca desce em links/juncoes (podem apontar fora da raiz).
            dirnames[:] = [
                name for name in dirnames
                if not os.path.islink(os.path.join(dirpath, name))
                and _contained(archives_real, os.path.join(dirpath, name))
            ]
            for filename in filenames:
                if not filename.lower().endswith(MEDIA_EXTENSIONS):
                    continue
                full = os.path.join(dirpath, filename)
                if not _contained(archives_real, full):
                    problems.append(
                        _error("PATH_OUTSIDE_ARCHIVES", f"arquivo fora de archives/: {full}")
                    )
                    continue
                key = os.path.relpath(full, resolution_root).replace(os.sep, "/")
                seen.add(key)
                expected = declared.get(key)
                if expected is None:
                    undeclared += 1
                    problems.append(
                        _error("MIDIA_ORFA", f"midia em archives/ sem manifesto ativo que a referencie: {key}")
                    )
                    continue
                per_kind[expected["kind"]] = per_kind.get(expected["kind"], 0) + 1
                try:
                    actual = _sha256_file(full)
                except OSError as exc:
                    problems.append(_error("MIDIA_ILEGIVEL", f"{key}: {exc}"))
                    continue
                if actual.lower() != expected["sha256"]:
                    divergent += 1
                    problems.append(
                        _error(
                            "ARCHIVE_HASH_DIVERGENTE",
                            f"{key}: divergencia de SHA-256 ({' / '.join(expected['labels'])})",
                        )
                    )
                    continue
                verified += 1
                declared_probe = expected.get("ffprobe")
                if declared_probe:
                    actual_probe = _ffprobe_metadata(workspace_root, full)
                    if actual_probe is None:
                        probe_indisponivel += 1
                        problems.append(
                            _warning("FFPROBE_INDISPONIVEL", f"{key}: nao foi possivel ler metadados com ffprobe")
                        )
                    else:
                        diffs = _compare_ffprobe(declared_probe, actual_probe)
                        if diffs:
                            probe_divergente += 1
                            problems.append(
                                _error(
                                    "ARCHIVE_FFPROBE_DIVERGENTE",
                                    f"{key}: metadados divergentes ({' / '.join(expected['labels'])}): "
                                    + "; ".join(diffs),
                                )
                            )

    missing = 0
    for key in sorted(set(declared) - seen):
        missing += 1
        problems.append(
            _warning(
                "MIDIA_AUSENTE",
                f"declarada mas ausente em archives/ (midia nao versionada): {key} "
                f"({' / '.join(declared[key]['labels'])})",
            )
        )

    summary = {
        "declarados": len(declared),
        "presentes": len(seen),
        "verificados": verified,
        "divergentes": divergent,
        "ausentes": missing,
        "orfos": undeclared,
        "naoDeclarados": undeclared,  # alias retrocompativel
        "probeDivergente": probe_divergente,
        "probeIndisponivel": probe_indisponivel,
        "porFormato": {kind: per_kind.get(kind, 0) for kind in ("9:16", "1x1", "16x9")},
        "porTipo": dict(sorted(per_kind.items())),
    }
    return problems, summary


# ---------------------------------------------------------------------------
# 3. Worktrees e arquivos nao rastreados
# ---------------------------------------------------------------------------
def _audit_worktrees(root_real: str, workspace_root: str) -> tuple[list[dict], dict]:
    problems: list[dict] = []
    registered_paths: set[str] = set()
    registered_names: set[str] = set()
    untracked: list[str] = []
    git_available = True
    try:
        output = _run_git(root_real, "worktree", "list", "--porcelain")
        for line in output.splitlines():
            if line.startswith("worktree "):
                path = line[len("worktree "):].strip()
                registered_paths.add(os.path.realpath(path))
                registered_names.add(os.path.basename(path.rstrip("/\\")))
        status = _run_git(root_real, "status", "--porcelain", "--untracked-files=normal")
        untracked = [
            line[3:].strip() for line in status.splitlines()
            if line.startswith("?? ")
        ]
    except WorkspaceDoctorError as exc:
        git_available = False
        problems.append(_warning("GIT_INDISPONIVEL", f"higiene Git nao auditada: {exc}"))

    worktrees_dir = os.path.join(workspace_root, "worktrees")
    fs_worktrees = _fs_path(worktrees_dir)
    orphan_dirs: list[str] = []
    if os.path.isdir(fs_worktrees):
        for name in sorted(os.listdir(fs_worktrees)):
            path = os.path.join(worktrees_dir, name)
            if not os.path.isdir(_fs_path(path)) or os.path.islink(_fs_path(path)):
                continue
            if os.path.realpath(path) not in registered_paths:
                orphan_dirs.append(name)
                problems.append(
                    _warning("WORKTREE_ORFA", f".workspace/worktrees/{name} sem registro no Git")
                )

    if git_available:
        for path in sorted(registered_paths):
            rel = os.path.relpath(path, worktrees_dir).replace(os.sep, "/")
            if rel.startswith("..") or os.path.isabs(rel):
                continue  # checkout principal ou worktree fora de .workspace/worktrees/
            if not os.path.isdir(_fs_path(path)):
                problems.append(
                    _error("WORKTREE_REGISTRADA_SEM_DIRETORIO", f"{rel}: registro sem diretorio")
                )
        if untracked:
            sample = ", ".join(untracked[:10])
            more = "" if len(untracked) <= 10 else f" (+{len(untracked) - 10})"
            problems.append(
                _warning("ARQUIVOS_NAO_RASTREADOS", f"{len(untracked)} arquivo(s): {sample}{more}")
            )

    summary = {
        "gitDisponivel": git_available,
        "worktreesRegistradas": len(registered_names),
        "worktreesOrfas": orphan_dirs,
        "arquivosNaoRastreados": len(untracked),
    }
    return problems, summary


# ---------------------------------------------------------------------------
# 4. Higiene de tmp / --clean-tmp
# ---------------------------------------------------------------------------
def _clean_tmp_target(tmp_root: str, name: str) -> str | None:
    """Resolve um filho de tmp/, recusando nome protegido e saida da raiz."""
    if name in PROTECTED_TMP_NAMES:
        return None
    candidate = os.path.join(tmp_root, name)
    if not _contained(tmp_root, candidate):
        return None
    if os.path.islink(_fs_path(candidate)):
        return None
    is_junction = getattr(os.DirEntry, "is_junction", None)
    if is_junction is not None:
        try:
            with os.scandir(_fs_path(tmp_root)) as entries:
                for entry in entries:
                    if entry.name == name and entry.is_junction():
                        return None
        except OSError:
            return None
    return candidate


def _clean_tmp(workspace_root: str) -> tuple[list[str], list[dict]]:
    tmp_root = os.path.join(workspace_root, "tmp")
    removed: list[str] = []
    problems: list[dict] = []
    fs_tmp = _fs_path(tmp_root)
    if not os.path.isdir(fs_tmp):
        return removed, problems
    for name in sorted(os.listdir(fs_tmp)):
        candidate = _clean_tmp_target(tmp_root, name)
        if candidate is None:
            continue  # arquivos soltos, aprovacoes e links nunca sao removidos
        if not os.path.isdir(_fs_path(candidate)):
            continue
        try:
            shutil.rmtree(_fs_path(candidate))
        except OSError as exc:
            problems.append(_warning("CLEAN_TMP_FALHOU", f"{name}: {exc}"))
            continue
        removed.append(os.path.relpath(candidate, workspace_root).replace(os.sep, "/"))
    return removed, problems


def _audit_tmp(workspace_root: str, clean: bool) -> tuple[list[dict], dict, list[str]]:
    problems: list[dict] = []
    tmp_root = os.path.join(workspace_root, "tmp")
    fs_tmp = _fs_path(tmp_root)
    candidates: list[str] = []
    if os.path.isdir(fs_tmp):
        for name in sorted(os.listdir(fs_tmp)):
            candidate = _clean_tmp_target(tmp_root, name)
            if candidate is not None and os.path.isdir(_fs_path(candidate)):
                candidates.append(os.path.relpath(candidate, workspace_root).replace(os.sep, "/"))
    approvals = os.path.join(workspace_root, "tmp", APPROVALS_FILENAME)
    removed: list[str] = []
    if clean:
        removed, clean_problems = _clean_tmp(workspace_root)
        problems.extend(clean_problems)
    summary = {
        "tmpRoot": os.path.relpath(tmp_root, os.path.dirname(workspace_root)).replace(os.sep, "/"),
        "removiveis": candidates,
        "aprovacoesPresente": os.path.isfile(_fs_path(approvals)),
        "removidos": removed,
        "protegidos": list(PROTECTED_WORKSPACE_DIRS) + [APPROVALS_FILENAME],
    }
    return problems, summary, removed


# ---------------------------------------------------------------------------
# API principal
# ---------------------------------------------------------------------------
def run_workspace_doctor(root: str | os.PathLike = ".", clean_tmp: bool = False) -> dict:
    """Executa o diagnostico do .workspace/ principal e devolve o relatorio v1."""
    root_real = os.path.realpath(str(root or "."))
    if not os.path.isdir(_fs_path(root_real)):
        raise WorkspaceDoctorError(f"raiz ausente: {root_real}")
    main_root = os.path.realpath(_resolve_main_root(root_real))
    workspace_root = os.path.join(main_root, *WORKSPACE_REL)

    ffmpeg_problems, ffmpeg_summary = _check_ffmpeg(workspace_root)
    archive_problems, archive_summary = _audit_archives(main_root, workspace_root, root_real)
    worktree_problems, worktree_summary = _audit_worktrees(root_real, workspace_root)
    tmp_problems, tmp_summary, removed = _audit_tmp(workspace_root, clean_tmp)

    problem_lists = (ffmpeg_problems, archive_problems, worktree_problems, tmp_problems)
    sections = [
        _section(section_id, problems)
        for (section_id, _), problems in zip(SECTION_NAMES, problem_lists)
    ]
    all_problems = [p for problems in problem_lists for p in problems]
    errors = sum(1 for p in all_problems if p["severity"] == "error")
    warnings = sum(1 for p in all_problems if p["severity"] == "warning")

    result = {
        "schemaVersion": 1,
        "ok": errors == 0,
        "mode": "clean-tmp" if clean_tmp else "check",
        "mainRoot": main_root,
        "workspaceRoot": workspace_root,
        "sections": sections,
        "summary": {
            "errors": errors,
            "warnings": warnings,
            "ffmpeg": ffmpeg_summary,
            "archives": archive_summary,
            "worktrees": worktree_summary,
            "tmp": tmp_summary,
        },
        "cleaned": removed,
    }
    return result


# ---------------------------------------------------------------------------
# API publica de integridade de manifestos (consumida por release_audit)
# ---------------------------------------------------------------------------
def audit_manifest_integrity(
    root: str | os.PathLike = ".", source_root: str | os.PathLike | None = None
) -> dict:
    """Cruza manifestos versionados com as midias locais de ``.workspace/archives/``.

    ``root`` e o ponto de partida (worktree ou checkout principal) e
    ``source_root`` indica onde estao os manifestos. Caminhos declarados sao
    sempre resolvidos contra a raiz PRINCIPAL. Nao grava nem altera arquivos.
    """
    root_real = os.path.realpath(str(root or "."))
    if not os.path.isdir(_fs_path(root_real)):
        raise WorkspaceDoctorError(f"raiz ausente: {root_real}")
    main_root = os.path.realpath(_resolve_main_root(root_real))
    workspace_root = os.path.join(main_root, *WORKSPACE_REL)
    src = os.path.realpath(str(source_root)) if source_root else root_real
    problems, summary = _audit_archives(main_root, workspace_root, src)
    return {
        "schemaVersion": 1,
        "ok": not any(p["severity"] == "error" for p in problems),
        "mainRoot": main_root,
        "workspaceRoot": workspace_root,
        "problems": problems,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Snapshot local (export / verify) — nunca versionado no Git
# ---------------------------------------------------------------------------
def _safe_snapshot_rel(rel: object) -> bool:
    """Aceita somente caminhos relativos, sem '..', dentro de .workspace/archives/."""
    if not isinstance(rel, str):
        return False
    norm = rel.replace("\\", "/")
    if not norm or norm.startswith("/") or re.match(r"^[A-Za-z]:", norm):
        return False
    if any(part in ("", ".", "..") for part in norm.split("/")):
        return False
    return norm.startswith(".workspace/archives/")


def _iter_archive_files(workspace_root: str, resolution_root: str) -> list[dict]:
    """Lista mp4/png presentes em archives/ com caminho relativo a raiz principal."""
    archives_real = os.path.realpath(os.path.join(workspace_root, "archives"))
    found: list[dict] = []
    fs_archives = _fs_path(archives_real)
    if not os.path.isdir(fs_archives):
        return found
    for dirpath, dirnames, filenames in os.walk(fs_archives, followlinks=False):
        dirnames[:] = [
            name for name in dirnames
            if not os.path.islink(os.path.join(dirpath, name))
            and _contained(archives_real, os.path.join(dirpath, name))
        ]
        for filename in filenames:
            if not filename.lower().endswith(MEDIA_EXTENSIONS):
                continue
            full = os.path.join(dirpath, filename)
            if os.path.islink(_fs_path(full)) or not _contained(archives_real, full):
                continue
            found.append({
                "full": full,
                "path": os.path.relpath(full, resolution_root).replace(os.sep, "/"),
                "bytes": os.path.getsize(_fs_path(full)),
            })
    return found


def _resolve_snapshot_path(
    root_real: str, main_root: str, provided: str | os.PathLike | None, *, expect_exists: bool
) -> str:
    """Resolve o zip dentro de <MAIN_ROOT>/.workspace/snapshots/, recusando caminho rastreado."""
    snap_dir = os.path.join(main_root, *SNAPSHOTS_REL)
    if provided:
        raw = os.fspath(provided)
        candidate = raw if os.path.isabs(raw) else os.path.join(root_real, raw)
        candidate = os.path.realpath(candidate)
    elif expect_exists:
        fs_dir = _fs_path(snap_dir)
        if not os.path.isdir(fs_dir):
            raise WorkspaceDoctorError("SNAPSHOT_SEM_ARQUIVO: nenhum snapshot exportado nesta estacao")
        names = sorted(
            name for name in os.listdir(fs_dir)
            if name.startswith(SNAPSHOT_PREFIX) and name.endswith(".zip")
        )
        if not names:
            raise WorkspaceDoctorError("SNAPSHOT_SEM_ARQUIVO: nenhum snapshot exportado nesta estacao")
        candidate = os.path.join(snap_dir, names[-1])
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        candidate = os.path.join(snap_dir, f"{SNAPSHOT_PREFIX}{stamp}.zip")

    if not _contained(snap_dir, candidate):
        raise WorkspaceDoctorError(
            "SNAPSHOT_FORA_DO_WORKSPACE: o snapshot deve ficar sob .workspace/snapshots/"
        )
    rel = os.path.relpath(candidate, main_root).replace(os.sep, "/")
    try:
        _run_git(main_root, "ls-files", "--error-unmatch", "--", rel)
    except WorkspaceDoctorError:
        pass  # nao rastreado: caminho permitido
    else:
        raise WorkspaceDoctorError(f"SNAPSHOT_DESTINO_RASTREADO: {rel} esta no indice do Git")
    return candidate


def export_snapshot(root: str | os.PathLike = ".", out: str | os.PathLike | None = None) -> dict:
    """Empacota os binarios locais de archives/ com indice SHA-256 verificavel."""
    root_real = os.path.realpath(str(root or "."))
    if not os.path.isdir(_fs_path(root_real)):
        raise WorkspaceDoctorError(f"raiz ausente: {root_real}")
    main_root = os.path.realpath(_resolve_main_root(root_real))
    workspace_root = os.path.join(main_root, *WORKSPACE_REL)
    archives_real = os.path.realpath(os.path.join(workspace_root, "archives"))
    dest = _resolve_snapshot_path(root_real, main_root, out, expect_exists=False)

    declared, _ = _collect_declared_media(main_root, main_root, archives_real)
    files = _iter_archive_files(workspace_root, main_root)
    entries: list[dict] = []
    for item in sorted(files, key=lambda row: row["path"]):
        entries.append({
            "path": item["path"],
            "sha256": _sha256_file(item["full"]),
            "bytes": item["bytes"],
            "kind": declared.get(item["path"], {}).get("kind", "orfao"),
            "label": declared.get(item["path"], {}).get("label"),
        })

    index = {
        "schemaVersion": 1,
        "type": "workspace-archives-snapshot",
        "createdAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rootLabel": ".workspace/archives",
        "count": len(entries),
        "totalBytes": sum(entry["bytes"] for entry in entries),
        "entries": entries,
    }
    parent = os.path.dirname(dest)
    try:
        os.makedirs(_fs_path(parent), exist_ok=True)
        with zipfile.ZipFile(_fs_path(dest), "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                SNAPSHOT_INDEX_NAME,
                json.dumps(index, ensure_ascii=False, indent=2) + "\n",
            )
            for entry in entries:
                archive.write(
                    _fs_path(os.path.join(main_root, *entry["path"].split("/"))),
                    arcname=entry["path"],
                )
    except OSError as exc:
        raise WorkspaceDoctorError(f"SNAPSHOT_EXPORT_FALHOU: {exc}") from exc

    return {
        "ok": True,
        "action": "export",
        "snapshotPath": os.path.relpath(dest, main_root).replace(os.sep, "/"),
        "count": index["count"],
        "totalBytes": index["totalBytes"],
        "index": index,
    }


def verify_snapshot(root: str | os.PathLike = ".", archive: str | os.PathLike | None = None) -> dict:
    """Verifica o indice SHA-256 de um snapshot e, quando possivel, os arquivos locais."""
    root_real = os.path.realpath(str(root or "."))
    if not os.path.isdir(_fs_path(root_real)):
        raise WorkspaceDoctorError(f"raiz ausente: {root_real}")
    main_root = os.path.realpath(_resolve_main_root(root_real))
    path = _resolve_snapshot_path(root_real, main_root, archive, expect_exists=archive is None)
    if not os.path.isfile(_fs_path(path)):
        raise WorkspaceDoctorError("SNAPSHOT_AUSENTE: arquivo de snapshot nao encontrado")

    problems: list[dict] = []
    warnings: list[dict] = []
    verified = 0
    entries: list[dict] = []
    try:
        with zipfile.ZipFile(_fs_path(path)) as handle:
            names = set(handle.namelist())
            if SNAPSHOT_INDEX_NAME not in names:
                raise WorkspaceDoctorError("SNAPSHOT_SEM_INDICE: snapshot-index.json ausente")
            try:
                index = json.loads(handle.read(SNAPSHOT_INDEX_NAME).decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as exc:
                raise WorkspaceDoctorError(f"SNAPSHOT_INDICE_INVALIDO: {exc}") from exc
            if not isinstance(index, dict) or index.get("schemaVersion") != 1:
                raise WorkspaceDoctorError("SNAPSHOT_INDICE_INVALIDO: schemaVersion inesperado")
            if index.get("type") != "workspace-archives-snapshot":
                raise WorkspaceDoctorError("SNAPSHOT_INDICE_INVALIDO: tipo inesperado")
            raw_entries = index.get("entries")
            if not isinstance(raw_entries, list):
                raise WorkspaceDoctorError("SNAPSHOT_INDICE_INVALIDO: secao entries ausente")
            entries = raw_entries

            members: set[str] = set()
            for entry in entries:
                rel = entry.get("path") if isinstance(entry, dict) else None
                if not _safe_snapshot_rel(rel):
                    problems.append(_error("SNAPSHOT_CAMINHO_INVALIDO", f"entrada invalida: {rel!r}"))
                    continue
                members.add(rel)
                if rel not in names:
                    problems.append(_error("SNAPSHOT_MEMBRO_AUSENTE", f"{rel} ausente no zip"))
                    continue
                data = handle.read(rel)
                expected_sha = str(entry.get("sha256", "")).lower()
                if _sha256_bytes(data) != expected_sha:
                    problems.append(_error("SNAPSHOT_HASH_DIVERGENTE", f"{rel}: SHA-256 diverge do indice"))
                    continue
                expected_bytes = entry.get("bytes")
                if isinstance(expected_bytes, int) and len(data) != expected_bytes:
                    problems.append(_error("SNAPSHOT_TAMANHO_DIVERGENTE", f"{rel}: tamanho diverge do indice"))
                    continue
                verified += 1
                local = os.path.join(main_root, *rel.split("/"))
                if os.path.isfile(_fs_path(local)):
                    if _sha256_file(local).lower() != expected_sha:
                        problems.append(
                            _error("SNAPSHOT_DISCO_DIVERGENTE", f"{rel}: arquivo local diverge do snapshot")
                        )
                else:
                    warnings.append(
                        _warning("SNAPSHOT_ARQUIVO_AUSENTE_NO_DISCO", f"{rel}: nao presente nesta estacao")
                    )
            extras = sorted(names - members - {SNAPSHOT_INDEX_NAME})
            for rel in extras:
                problems.append(_error("SNAPSHOT_MEMBRO_EXTRA", f"{rel}: membro nao declarado no indice"))
    except (OSError, zipfile.BadZipFile) as exc:
        raise WorkspaceDoctorError(f"SNAPSHOT_LEITURA_FALHOU: {exc}") from exc

    return {
        "ok": not problems,
        "action": "verify",
        "snapshotPath": os.path.relpath(path, main_root).replace(os.sep, "/"),
        "count": len(entries),
        "verified": verified,
        "problems": problems,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _print_human(result: dict) -> None:
    label = {"ok": "OK", "warn": "AVISO", "fail": "FALHA"}
    for section in result["sections"]:
        print(f"[{label[section['status']]}] {section['id']} — {section['name']}")
        for problem in section["problems"]:
            print(f"    - [{problem['severity']}] {problem['code']}: {problem['message']}")
    summary = result["summary"]
    print()
    print(f"ffmpeg: {summary['ffmpeg']['ffmpeg']['version']} / {summary['ffmpeg']['ffprobe']['version']}")
    print(
        f"archives: {summary['archives']['verificados']} verificado(s), "
        f"{summary['archives']['divergentes']} divergente(s), "
        f"{summary['archives']['ausentes']} ausente(s), "
        f"{summary['archives']['orfos']} orfos(s), "
        f"{summary['archives']['probeDivergente']} ffprobe divergente(s)"
    )
    print(
        f"por formato: 9:16={summary['archives']['porFormato']['9:16']}, "
        f"1x1={summary['archives']['porFormato']['1x1']}, "
        f"16x9={summary['archives']['porFormato']['16x9']}"
    )
    if result["cleaned"]:
        print("removidos de tmp/: " + ", ".join(result["cleaned"]))
    print(f"Problemas: {summary['errors']} erro(s), {summary['warnings']} aviso(s)")
    print(f"Resultado ({result['mode']}): {'OK' if result['ok'] else 'REPROVADO'}")


def _print_snapshot_human(result: dict) -> None:
    print(f"ação: {result['action']}")
    print(f"snapshot: {result['snapshotPath']}")
    if result["action"] == "export":
        print(f"arquivos: {result['count']} ({result['totalBytes']} bytes)")
        print("indice: SHA-256 gerado; use 'snapshot verify' para conferir")
        return
    print(f"verificados: {result['verified']}/{result['count']}")
    for problem in result["problems"]:
        print(f"    - [error] {problem['code']}: {problem['message']}")
    for warning in result["warnings"]:
        print(f"    - [warning] {warning['code']}: {warning['message']}")
    print(f"Resultado: {'OK' if result['ok'] else 'REPROVADO'}")


def _add_common_args(parser: argparse.ArgumentParser, *, suppress: bool) -> None:
    """Adiciona --json/--root ao subcomando sem sobrescrever valores do topo."""
    json_default = argparse.SUPPRESS if suppress else False
    root_default = argparse.SUPPRESS if suppress else "."
    parser.add_argument("--json", action="store_true", default=json_default,
                        help="emite payload JSON no stdout")
    parser.add_argument("--root", default=root_default,
                        help="ponto de partida para resolver MAIN_ROOT")


def main(argv: list[str] | None = None) -> int:
    _stdout_utf8()
    parser = argparse.ArgumentParser(description="Doutor local do workspace (Etapa 6 - Agente 6)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="apenas diagnostica (padrao)")
    mode.add_argument("--clean-tmp", action="store_true", help="remove subdiretorios descartaveis de tmp/")
    _add_common_args(parser, suppress=False)

    commands = parser.add_subparsers(dest="command")
    snapshot = commands.add_parser("snapshot", help="backup local de .workspace/archives/")
    snapshot_actions = snapshot.add_subparsers(dest="snapshot_command")
    snapshot_actions.required = True
    export = snapshot_actions.add_parser("export", help="empacota binarios com indice SHA-256")
    export.add_argument("--out", default=None,
                        help="destino .zip relativo a raiz (padrao: .workspace/snapshots/)")
    _add_common_args(export, suppress=True)
    verify = snapshot_actions.add_parser("verify", help="verifica o indice SHA-256 de um snapshot")
    verify.add_argument("--archive", default=None,
                        help="snapshot .zip relativo a raiz (padrao: o mais recente)")
    _add_common_args(verify, suppress=True)

    args = parser.parse_args(argv)
    as_json = getattr(args, "json", False)
    root = getattr(args, "root", ".")

    try:
        if args.command == "snapshot":
            if args.snapshot_command == "export":
                result = export_snapshot(root=root, out=getattr(args, "out", None))
            else:
                result = verify_snapshot(root=root, archive=getattr(args, "archive", None))
        else:
            result = run_workspace_doctor(root=root, clean_tmp=args.clean_tmp)
    except WorkspaceDoctorError as exc:
        if as_json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Erro: {exc}", file=sys.stderr)
        return 2

    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "snapshot":
        _print_snapshot_human(result)
    else:
        _print_human(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
