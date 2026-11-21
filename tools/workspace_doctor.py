"""Doutor local de higiene do workspace (Etapa 6 - Agente 6).

Audita, em uma unica passada, o estado do ``.workspace/`` do checkout PRINCIPAL
(compartilhado por todas as worktrees):

  1. ffmpeg              presenca e versao de ``ffmpeg.exe``/``ffprobe.exe`` em
                         ``<MAIN_ROOT>/.workspace/tools/ffmpeg/``.
  2. archives            cruzamento dos MP4/PNG locais em ``.workspace/archives/``
                         com os SHA-256 declarados em ``manifest.json`` e
                         ``derivatives.json`` das entregas (9:16, 1:1, 16:9,
                         cover, thumb-16x9 e preview-formats).
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

API:
    run_workspace_doctor(root=".", clean_tmp=False) -> dict

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

WORKSPACE_REL = (".workspace",)
ARCHIVES_REL = (".workspace", "archives")
TOOLS_FFMPEG_REL = (".workspace", "tools", "ffmpeg")
TMP_REL = (".workspace", "tmp")
DEVLOGS_REL = (".workspace", "devlogs")
WORKTREES_REL = (".workspace", "worktrees")
DELIVERIES_REL = ("02-reels-shorts", "deliveries")

APPROVALS_FILENAME = "aprovacoes-titular.json"
PROTECTED_TMP_NAMES = frozenset({APPROVALS_FILENAME})
PROTECTED_WORKSPACE_DIRS = ("archives", "tools", "devlogs")
MEDIA_EXTENSIONS = (".mp4", ".png")

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

    def register(declared_path: object, sha256: object, kind: str, label: str) -> None:
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
        record = {"sha256": sha256.lower(), "kind": kind, "label": label}
        previous = declared.get(key)
        if previous is not None and previous["sha256"] != record["sha256"]:
            problems.append(
                _error(
                    "DECLARACAO_CONFLITANTE",
                    f"{key}: hashes divergentes entre {previous['label']} e {label}",
                )
            )
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
                    register(archive_path, video.get("sha256"), "9:16", f"{label_base}:manifest.video")
            derivatives_path = os.path.join(delivery_dir, "derivatives.json")
            if os.path.isfile(_fs_path(derivatives_path)):
                try:
                    data = _read_json(derivatives_path)
                except (OSError, ValueError) as exc:
                    problems.append(_error("DERIVATIVES_INVALIDO", f"{label_base}: {exc}"))
                else:
                    source = data.get("source") or {}
                    register(
                        source.get("path"), source.get("sha256"), "9:16", f"{label_base}:derivatives.source"
                    )
                    for key, entry in (data.get("derivatives") or {}).items():
                        if isinstance(entry, dict):
                            register(
                                entry.get("path"),
                                entry.get("sha256"),
                                _classify_derivative(key, entry),
                                f"{label_base}:derivatives.{key}",
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
                        _warning("MIDIA_NAO_DECLARADA", f"sem hash registrado: {key}")
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
                        _error("ARCHIVE_HASH_DIVERGENTE", f"{key}: divergencia de SHA-256 ({expected['label']})")
                    )
                else:
                    verified += 1

    missing = 0
    for key in sorted(set(declared) - seen):
        missing += 1
        problems.append(
            _warning(
                "MIDIA_AUSENTE",
                f"declarada mas ausente em archives/ (midia nao versionada): {key}",
            )
        )

    summary = {
        "declarados": len(declared),
        "presentes": len(seen),
        "verificados": verified,
        "divergentes": divergent,
        "ausentes": missing,
        "naoDeclarados": undeclared,
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
        f"{summary['archives']['naoDeclarados']} nao declarado(s)"
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


def main(argv: list[str] | None = None) -> int:
    _stdout_utf8()
    parser = argparse.ArgumentParser(description="Doutor local do workspace (Etapa 6 - Agente 6)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="apenas diagnostica (padrao)")
    mode.add_argument("--clean-tmp", action="store_true", help="remove subdiretorios descartaveis de tmp/")
    parser.add_argument("--json", action="store_true", help="emite relatorio JSON no stdout")
    parser.add_argument("--root", default=".", help="ponto de partida para resolver MAIN_ROOT")
    args = parser.parse_args(argv)

    try:
        result = run_workspace_doctor(root=args.root, clean_tmp=args.clean_tmp)
    except WorkspaceDoctorError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Erro: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
