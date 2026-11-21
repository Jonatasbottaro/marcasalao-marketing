"""Infraestrutura determinística do E2E da fábrica.

Monta um checkout-miniatura em ``<RAIZ>/.workspace/tmp/factory-e2e/<cenario>/``
a partir de diretórios **versionados** do próprio repositório. Nenhum artefato
de mídia (``*.mp4`` / ``*.wav``) é copiado: o E2E prova o fluxo de metadados e
garante que nenhum vídeo/áudio seja gerado fora de ``.workspace/archives/``.

Todo caminho é montado com ``os.path.join`` e normalizado por
``render_local.fs_path`` para valer em Windows e Ubuntu. Arquivos de texto são
gravados em UTF-8 com LF explícito.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
sys.path.insert(0, TOOLS_DIR)

import render_local  # noqa: E402

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
SANDBOX_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "factory-e2e")

# Diretórios versionados necessários para o release_audit (7 domínios).
COPY_DIRS = (
    "schemas",
    "tenants",
    "02-reels-shorts",
    "01-insta-stories",
    "04-legendas",
    "05-review-portal",
)
COPY_FILES = (".gitattributes", ".gitignore")
IGNORED = shutil.ignore_patterns("*.mp4", "*.wav", "__pycache__", "*.pyc")

TENANT = "marca-salao"
SLUG = "camp-saas-demo-marca-salao-001"
APPROVALS_REL = ".workspace/tmp/aprovacoes-titular-e2e.json"
HANDOFF_REL = ".workspace/handoff-diario"


def _abs(root: str, rel: str) -> str:
    return os.path.join(root, *rel.replace("\\", "/").split("/"))


def force_rmtree(path: str) -> None:
    """Remove árvore mesmo com arquivos somente-leitura (Windows)."""
    if not os.path.isdir(render_local.fs_path(path)):
        return
    for dirpath, _dirnames, filenames in os.walk(render_local.fs_path(path)):
        for name in filenames:
            try:
                os.chmod(os.path.join(dirpath, name), stat.S_IWRITE)
            except OSError:
                pass
    shutil.rmtree(render_local.fs_path(path), ignore_errors=True)


def build_sandbox(scenario: str) -> str:
    """Copia o acervo versionado para um sandbox com repositório Git inicializado."""
    root = os.path.realpath(os.path.join(SANDBOX_ROOT, scenario))
    force_rmtree(root)
    os.makedirs(render_local.fs_path(root), exist_ok=True)
    for name in COPY_DIRS:
        shutil.copytree(
            render_local.fs_path(os.path.join(REPO_ROOT, name)),
            render_local.fs_path(_abs(root, name)),
            ignore=IGNORED,
        )
    for name in COPY_FILES:
        shutil.copy2(
            render_local.fs_path(os.path.join(REPO_ROOT, name)),
            render_local.fs_path(_abs(root, name)),
        )
    os.makedirs(render_local.fs_path(_abs(root, ".workspace/tmp")), exist_ok=True)
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(
        root,
        "-c", "user.name=factory-e2e",
        "-c", "user.email=factory-e2e@example.invalid",
        "commit", "-q", "-m", "fixture E2E",
    )
    return root


def git(root: str, *args: str) -> None:
    subprocess.run(
        ["git", "-C", root, *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def read_text(path: str) -> str:
    with open(render_local.fs_path(path), "r", encoding="utf-8", newline="") as handle:
        return handle.read()


def write_text(path: str, text: str) -> None:
    os.makedirs(render_local.fs_path(os.path.dirname(path)), exist_ok=True)
    with open(render_local.fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def read_json(path: str) -> dict:
    return json.loads(read_text(path))


def write_json(path: str, payload: dict) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def inject_long_srt(root: str, tenant: str = TENANT, slug: str = SLUG) -> str:
    """Introduz linhas acima de 48 caracteres numa entrega do sandbox."""
    srt_path = _abs(root, f"02-reels-shorts/deliveries/{tenant}/{slug}/{slug}.srt")
    write_text(srt_path, read_text(os.path.join(FIXTURES_DIR, "long_lines.srt")))
    return srt_path


def sync_checklist_srt(root: str, tenant: str = TENANT, slug: str = SLUG) -> None:
    """Sincroniza o hash do SRT no checklist após a formatação.

    Na fábrica real este papel é do `publish_pack`; o E2E reproduz apenas a
    atualização da entrada `srt` para não regravar o `sha256_disk_ok` das mídias
    ausentes nesta estação.
    """
    path = _abs(root, f"04-legendas/pacotes-publicacao/{tenant}/{slug}/checklist-publicacao.json")
    doc = read_json(path)
    srt_path = _abs(root, f"02-reels-shorts/deliveries/{tenant}/{slug}/{slug}.srt")
    with open(render_local.fs_path(srt_path), "rb") as handle:
        data = handle.read()
    for entry in doc.get("media", []):
        if entry.get("kind") == "srt":
            entry["sha256"] = hashlib.sha256(data).hexdigest()
            entry["bytes"] = len(data)
    write_json(path, doc)


def srt_max_line(path: str) -> int:
    """Maior comprimento de linha de texto (ignora índice e timecode)."""
    longest = 0
    for block in read_text(path).strip("\n").split("\n\n"):
        for line in block.split("\n")[2:]:
            longest = max(longest, len(line.strip()))
    return longest


def find_media(root: str) -> list[str]:
    """Arquivos .mp4/.wav encontrados no sandbox, como caminhos relativos com '/'."""
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(render_local.fs_path(root)):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        for name in filenames:
            if name.lower().endswith((".mp4", ".wav")):
                rel = os.path.relpath(os.path.join(dirpath, name), root)
                found.append(rel.replace(os.sep, "/"))
    return sorted(found)


def media_outside_workspace(root: str) -> list[str]:
    """Mídia na árvore versionada — nunca permitida (regra do CI e do release_audit)."""
    return [rel for rel in find_media(root) if not rel.startswith(".workspace/")]
