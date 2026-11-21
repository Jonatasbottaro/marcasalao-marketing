"""Bootstrap portatil e idempotente de ffmpeg/ffprobe (Agente 1 - Etapa 5B).

Instala o pacote essencial do Windows (gyan.dev) em
``<MAIN_ROOT>/.workspace/tools/ffmpeg/`` e valida ambos os binarios com
``-version``. Resolve ``MAIN_ROOT`` via ``git rev-parse --git-common-dir`` para
que a instalacao fique no checkout principal e seja compartilhada por todas as
worktrees.

100% biblioteca padrao (urllib.request, zipfile, shutil, subprocess, hashlib,
pathlib, platform). Nunca versiona ``.exe``/``.zip``: tudo fica sob
``.workspace/`` (ignorado localmente no Git).

CLI:
    python tools/bootstrap_ffmpeg.py [--check-only] [--force] [--json] [--root DIR]

API:
    ensure_ffmpeg_tools(root=".", force=False) -> dict
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
_WINDOWS = os.name == "nt" or platform.system() == "Windows"

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


class BootstrapError(Exception):
    """Falha controlada do bootstrap; mensagem sanitizada, sem stack trace."""


# ---------------------------------------------------------------------------
# Resolucao de raizes e nomes de binarios
# ---------------------------------------------------------------------------
def _resolve_main_root(root: str | os.PathLike = ".") -> str:
    """Raiz do checkout PRINCIPAL a partir de ``git rev-parse --git-common-dir``.

    Em worktrees, o git-common-dir aponta para ``<MAIN_ROOT>/.git``; o diretorio
    pai desse caminho e a raiz principal, onde ``.workspace/tools/ffmpeg`` deve
    morar para ser compartilhado. Sem git disponivel, cai para ``abspath(root)``.
    """
    root_abs = os.path.abspath(str(root or "."))
    try:
        res = subprocess.run(
            ["git", "-C", root_abs, "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
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
    # common == <MAIN_ROOT>/.git ; main == pai
    parent = os.path.dirname(common)
    return parent or root_abs


def _tools_dir(main_root: str) -> str:
    return os.path.join(main_root, ".workspace", "tools", "ffmpeg")


def _exe_names() -> tuple[str, str]:
    if _WINDOWS:
        return f"{FFMPEG}.exe", f"{FFPROBE}.exe"
    return FFMPEG, FFPROBE


# ---------------------------------------------------------------------------
# Deteccao / validacao
# ---------------------------------------------------------------------------
def _probe(path: str | None) -> tuple[bool, str | None]:
    """Roda ``<path> -version``. Devolve (ok, primeira_linha) sem lancar."""
    if not path or not os.path.isfile(path):
        return False, None
    try:
        res = subprocess.run(
            [path, "-version"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False, None
    if res.returncode != 0:
        return False, None
    lines = (res.stdout or res.stderr or "").strip().splitlines()
    return True, (lines[0].strip() if lines else "")


def _find_existing(main_root: str) -> dict | None:
    """Procura ffmpeg/ffprobe em ``<tools_dir>`` e no PATH, validando ``-version``.

    Ordem: instalacao do workspace (preferida) e depois PATH. So devolve quando
    AMBOS os binarios respondem a ``-version`` com sucesso.
    """
    ff_name, fp_name = _exe_names()
    tools = _tools_dir(main_root)
    candidates: list[tuple[str, str, str]] = [
        (os.path.join(tools, ff_name), os.path.join(tools, fp_name), "workspace"),
    ]
    which_ff = shutil.which(FFMPEG)
    which_fp = shutil.which(FFPROBE)
    if which_ff and which_fp:
        candidates.append((which_ff, which_fp, "path"))
    for ff, fp, origin in candidates:
        ok_ff, ver_ff = _probe(ff)
        ok_fp, _ = _probe(fp)
        if ok_ff and ok_fp:
            return {
                "ffmpegPath": ff,
                "ffprobePath": fp,
                "version": ver_ff,
                "origin": origin,
            }
    return None


def _is_gitignored(main_root: str, path: str) -> bool:
    """True se ``git check-ignore`` confirma que o caminho esta ignorado."""
    try:
        rel = os.path.relpath(path, main_root)
        res = subprocess.run(
            ["git", "-C", main_root, "check-ignore", "-q", rel],
            capture_output=True,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return res.returncode == 0


# ---------------------------------------------------------------------------
# Download / extracao / promocao atomica
# ---------------------------------------------------------------------------
def _download(url: str, dest_zip: str) -> str:
    """Baixa ``url`` para ``dest_zip`` e devolve o SHA-256 dos bytes."""
    os.makedirs(os.path.dirname(dest_zip), exist_ok=True)
    sha = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=120) as resp, open(dest_zip, "wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            sha.update(chunk)
            out.write(chunk)
    return sha.hexdigest()


def _extract_binaries(zip_path: str, staging_dir: str) -> tuple[str, str]:
    """Extrai ``ffmpeg``/``ffprobe`` do pacote para ``staging_dir`` (por basename).

    Aceita a estrutura ``ffmpeg-<ver>-essentials_build/bin/<exe>``. Escreve
    sempre ``staging_dir/<basename>`` (nunca o caminho interno do zip), o que
    contem qualquer tentativa de path traversal.
    """
    ff_name, fp_name = _exe_names()
    wanted = {ff_name: "", fp_name: ""}
    os.makedirs(staging_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            norm = member.replace("\\", "/")
            base = norm.rsplit("/", 1)[-1]
            if base in wanted and not wanted[base] and "/bin/" in ("/" + norm):
                dest = os.path.join(staging_dir, base)
                with zf.open(member) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)
                wanted[base] = dest
    missing = [name for name, got in wanted.items() if not got]
    if missing:
        raise BootstrapError(
            "binarios ausentes no pacote zip: " + ", ".join(missing)
        )
    return wanted[ff_name], wanted[fp_name]


def _promote(ff_src: str, fp_src: str, tools_dir: str) -> tuple[str, str]:
    """Move os binarios extraidos para ``tools_dir`` com substituicao atomica."""
    os.makedirs(tools_dir, exist_ok=True)
    ff_name, fp_name = _exe_names()
    ff_dest = os.path.join(tools_dir, ff_name)
    fp_dest = os.path.join(tools_dir, fp_name)
    # os.replace e atomico quando origem/destino estao no mesmo volume, o que vale
    # aqui porque o staging vive em <MAIN_ROOT>/.workspace/tmp (mesmo drive).
    os.replace(ff_src, ff_dest)
    os.replace(fp_src, fp_dest)
    return ff_dest, fp_dest


def _cleanup(tmp_root: str, staging: str, zip_path: str) -> None:
    shutil.rmtree(staging, ignore_errors=True)
    try:
        if os.path.isfile(zip_path):
            os.remove(zip_path)
    except OSError:
        pass
    try:
        if os.path.isdir(tmp_root) and not os.listdir(tmp_root):
            os.rmdir(tmp_root)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# API principal
# ---------------------------------------------------------------------------
def ensure_ffmpeg_tools(root: str | os.PathLike = ".", force: bool = False) -> dict:
    """Garante ffmpeg/ffprobe operacionais em ``<MAIN_ROOT>/.workspace/tools/ffmpeg``.

    Retorna um dict com ``ok``, ``status`` e caminhos. Status possiveis:
    ``already_available`` (nada a fazer), ``installed`` (baixou/promoveu) ou
    ``unsupported_platform``/``error`` (``ok`` False).
    """
    main_root = _resolve_main_root(root)
    tools_dir = _tools_dir(main_root)

    existing = _find_existing(main_root)
    if existing is not None and not force:
        return {
            "ok": True,
            "status": "already_available",
            "mainRoot": main_root,
            "toolsDir": tools_dir,
            "ffmpegPath": existing["ffmpegPath"],
            "ffprobePath": existing["ffprobePath"],
            "version": existing["version"],
            "origin": existing["origin"],
            "gitignored": _is_gitignored(main_root, tools_dir),
        }

    if not _WINDOWS:
        return {
            "ok": False,
            "status": "unsupported_platform",
            "mainRoot": main_root,
            "toolsDir": tools_dir,
            "message": (
                "download automatico suporta apenas Windows; "
                "instale ffmpeg/ffprobe no PATH nesta plataforma"
            ),
        }

    tmp_root = os.path.join(main_root, ".workspace", "tmp", "ffmpeg-bootstrap")
    os.makedirs(tmp_root, exist_ok=True)
    staging = tempfile.mkdtemp(prefix="staging-", dir=tmp_root)
    zip_path = os.path.join(tmp_root, "ffmpeg-essentials.zip")
    try:
        sha = _download(DOWNLOAD_URL, zip_path)
        ff_src, fp_src = _extract_binaries(zip_path, staging)
        ff_dest, fp_dest = _promote(ff_src, fp_src, tools_dir)
        ok_ff, ver_ff = _probe(ff_dest)
        ok_fp, _ = _probe(fp_dest)
        if not (ok_ff and ok_fp):
            raise BootstrapError(
                "binarios instalados mas '-version' falhou na validacao"
            )
        return {
            "ok": True,
            "status": "installed",
            "mainRoot": main_root,
            "toolsDir": tools_dir,
            "ffmpegPath": ff_dest,
            "ffprobePath": fp_dest,
            "version": ver_ff,
            "sha256": sha,
            "downloadUrl": DOWNLOAD_URL,
            "gitignored": _is_gitignored(main_root, tools_dir),
        }
    finally:
        _cleanup(tmp_root, staging, zip_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    status = payload.get("status")
    detail = payload.get("ffmpegPath") or payload.get("message") or ""
    print(f"{status}: {detail}".rstrip(": "))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap portatil de ffmpeg/ffprobe (Etapa 5B - Agente 1)"
    )
    parser.add_argument("--check-only", action="store_true",
                        help="apenas verifica disponibilidade; nunca baixa")
    parser.add_argument("--force", action="store_true",
                        help="reinstala mesmo se ja houver ffmpeg disponivel")
    parser.add_argument("--json", action="store_true", help="emite payload JSON no stdout")
    parser.add_argument("--root", default=".",
                        help="ponto de partida para resolver MAIN_ROOT (default: .)")
    args = parser.parse_args(argv)

    if args.check_only:
        main_root = _resolve_main_root(args.root)
        existing = _find_existing(main_root)
        payload = {
            "ok": existing is not None,
            "status": "available" if existing is not None else "missing",
            "mainRoot": main_root,
            "toolsDir": _tools_dir(main_root),
            "ffmpegPath": existing["ffmpegPath"] if existing else None,
            "ffprobePath": existing["ffprobePath"] if existing else None,
            "version": existing["version"] if existing else None,
        }
        _emit(payload, args.json)
        return 0 if existing is not None else 1

    try:
        result = ensure_ffmpeg_tools(args.root, force=args.force)
    except BootstrapError as exc:
        payload = {"ok": False, "status": "error", "message": str(exc)}
        _emit(payload, args.json)
        return 1
    except (OSError, urllib.error.URLError) as exc:
        payload = {
            "ok": False,
            "status": "error",
            "message": f"{type(exc).__name__}: {exc}",
        }
        _emit(payload, args.json)
        return 1

    _emit(result, args.json)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())