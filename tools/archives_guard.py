"""Blindagem dos masters compartilhados em ``.workspace/archives/``.

Testes de render que chamam o pipeline canonico sem ``archives_dir`` isolado
sobrescrevem os MP4/PNG reais do checkout principal, produzindo divergencia de
SHA-256 contra ``manifest.json``/``derivatives.json``. Este modulo oferece duas
defesas complementares, 100% stdlib e portaveis (Windows e Linux):

  1. ``ArchivesGuard``: contexto que fotografa os hashes e guarda copia integral
     das midias antes da execucao e, ao sair, restaura qualquer arquivo alterado
     ou removido e descarta midia nova criada durante o run.
  2. ``isolated_archives``: diretorio temporario descartavel para passar como
     ``archives_dir`` ao pipeline, evitando a escrita na raiz compartilhada.

Todos os temporarios ficam sob ``<RAIZ>/.workspace/tmp/``, nunca em ``%TEMP%``
ou ``/tmp``: o projeto exige que nenhum artefato seja criado fora do checkout.

Uso em teste executado diretamente por ``unittest``::

    import archives_guard

    def setUpModule():
        global _GUARD
        _GUARD = archives_guard.ArchivesGuard(REPO_ROOT).__enter__()

    def tearDownModule():
        _GUARD.__exit__(None, None, None)

Uso como diretorio isolado::

    with archives_guard.isolated_archives(REPO_ROOT) as archives:
        preset_runner.run_preset_pipeline(..., archives_dir=archives)
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import shutil
import tempfile

MEDIA_EXTENSIONS = (".mp4", ".png")
ARCHIVES_REL = (".workspace", "archives")
TMP_REL = (".workspace", "tmp")


def fs_path(path: str) -> str:
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


def task_tmp_root(root: str = ".", name: str = "archives-guard") -> str:
    """Diretorio de temporarios da tarefa, sempre dentro de ``<RAIZ>``."""
    path = os.path.join(os.path.realpath(root), *TMP_REL, name)
    os.makedirs(fs_path(path), exist_ok=True)
    return path


def archives_root(root: str = ".") -> str:
    return os.path.join(os.path.realpath(root), *ARCHIVES_REL)


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(fs_path(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(root: str = ".") -> dict[str, str]:
    """Mapa ``caminho relativo a archives/ -> sha256`` das midias presentes."""
    base = archives_root(root)
    result: dict[str, str] = {}
    if not os.path.isdir(fs_path(base)):
        return result
    for dirpath, dirnames, filenames in os.walk(fs_path(base), followlinks=False):
        dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]
        for filename in filenames:
            if not filename.lower().endswith(MEDIA_EXTENSIONS):
                continue
            full = os.path.join(dirpath, filename)
            rel = os.path.relpath(full, base).replace(os.sep, "/")
            result[rel] = sha256_file(full)
    return result


@contextlib.contextmanager
def isolated_archives(root: str = ".", name: str = "archives-guard"):
    """Diretorio de archives descartavel, confinado a ``<RAIZ>/.workspace/tmp/``."""
    parent = task_tmp_root(root, name)
    path = tempfile.mkdtemp(prefix="archives-", dir=parent)
    try:
        yield path
    finally:
        shutil.rmtree(fs_path(path), ignore_errors=True)


class ArchivesGuard:
    """Fotografa e restaura os masters compartilhados ao redor de um bloco.

    ``report`` fica disponivel apos a saida do contexto e distingue arquivos
    restaurados (conteudo alterado ou removido) de midia nova descartada.
    """

    def __init__(self, root: str = ".", name: str = "archives-guard") -> None:
        self.root = os.path.realpath(root)
        self.base = archives_root(self.root)
        self._name = name
        self._backup: str | None = None
        self._before: dict[str, str] = {}
        self.report: dict = {
            "archivesRoot": self.base,
            "filesBefore": 0,
            "restored": [],
            "discarded": [],
            "ok": True,
        }

    def __enter__(self) -> "ArchivesGuard":
        self._before = snapshot(self.root)
        self.report["filesBefore"] = len(self._before)
        parent = task_tmp_root(self.root, self._name)
        self._backup = tempfile.mkdtemp(prefix="backup-", dir=parent)
        for rel in self._before:
            src = os.path.join(self.base, *rel.split("/"))
            dst = os.path.join(self._backup, *rel.split("/"))
            os.makedirs(fs_path(os.path.dirname(dst)), exist_ok=True)
            shutil.copyfile(fs_path(src), fs_path(dst))
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            self._restore()
        finally:
            if self._backup is not None:
                shutil.rmtree(fs_path(self._backup), ignore_errors=True)
                self._backup = None
        return False

    def _restore(self) -> None:
        after = snapshot(self.root)
        restored: list[str] = []
        for rel, expected in self._before.items():
            if after.get(rel) == expected:
                continue
            src = os.path.join(self._backup or "", *rel.split("/"))
            dst = os.path.join(self.base, *rel.split("/"))
            os.makedirs(fs_path(os.path.dirname(dst)), exist_ok=True)
            shutil.copyfile(fs_path(src), fs_path(dst))
            restored.append(rel)
        discarded: list[str] = []
        for rel in sorted(set(after) - set(self._before)):
            os.remove(fs_path(os.path.join(self.base, *rel.split("/"))))
            discarded.append(rel)
        self.report["restored"] = sorted(restored)
        self.report["discarded"] = discarded
        self.report["ok"] = not restored and not discarded