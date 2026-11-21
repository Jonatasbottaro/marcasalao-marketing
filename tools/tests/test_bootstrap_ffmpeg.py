"""Suite do bootstrap_ffmpeg (Agente 1 - Etapa 5B).

Testes hermeticos: nao dependem de internet (download mockado), usam zip
simulado com a estrutura real ``ffmpeg-<ver>-essentials_build/bin/<exe>`` e
binarios falsos em ``TemporaryDirectory`` (dentro de ``.workspace/tmp`` para
respeitar a regra de armazenamento da raiz). Ha ainda um teste de deteccao
real do ambiente, que passa (skip) antes da instalacao e valida depois dela.

Cobertura obrigatoria:
  1. already_available quando os binarios ja existem (sem baixar).
  2. Extracao + promocao atomica de um .zip simulado.
  3. --check-only retorna 1 quando ausente e 0 quando presente.
  4. Contencao de caminho: nada e escrito fora do staging (basename sempre).
  5. Limpeza automatica dos temporarios apos instalar.
  6. CLI --json devolve payload estruturado valido.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import bootstrap_ffmpeg

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKSPACE_TMP = os.path.join(REPO_ROOT, ".workspace", "tmp")
os.makedirs(WORKSPACE_TMP, exist_ok=True)


def _fake_probe(path):
    """Simula binario operacional apenas quando o arquivo existe em disco."""
    if path and os.path.isfile(path):
        return True, "ffmpeg version fake-test"
    return False, None


def _write_zip(path, entries):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries:
            zf.writestr(name, data)


def _essentials_entries():
    ff, fp = bootstrap_ffmpeg._exe_names()
    return [
        (f"ffmpeg-7.0-essentials_build/bin/{ff}", b"FAKE-FFMPEG-BYTES"),
        (f"ffmpeg-7.0-essentials_build/bin/{fp}", b"FAKE-FFPROBE-BYTES"),
    ]


class TestBootstrapFfmpeg(unittest.TestCase):

    def setUp(self):
        # Mantem os temporarios sob <RAIZ>/.workspace/tmp (regra AGENTS.md).
        self._tmpdir = tempfile.TemporaryDirectory(dir=WORKSPACE_TMP)
        self.tmp = os.path.abspath(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    @property
    def tools_dir(self):
        return os.path.join(self.tmp, ".workspace", "tools", "ffmpeg")

    def _make_local_binaries(self):
        os.makedirs(self.tools_dir, exist_ok=True)
        ff, fp = bootstrap_ffmpeg._exe_names()
        paths = {}
        for name in (ff, fp):
            p = os.path.join(self.tools_dir, name)
            with open(p, "wb") as handle:
                handle.write(b"STUB")
            paths[name] = p
        return paths

    # --- 1. already_available ------------------------------------------------
    def test_01_already_available_quando_binarios_existem(self):
        paths = self._make_local_binaries()

        def _no_download(*a, **k):
            raise AssertionError("nao deveria baixar quando ja existem binarios")

        with mock.patch.object(bootstrap_ffmpeg, "_resolve_main_root",
                               lambda r=".": self.tmp), \
             mock.patch.object(bootstrap_ffmpeg, "_probe", _fake_probe), \
             mock.patch.object(bootstrap_ffmpeg, "_is_gitignored", lambda *a: True), \
             mock.patch.object(bootstrap_ffmpeg, "_download", _no_download), \
             mock.patch.object(bootstrap_ffmpeg.shutil, "which", lambda name: None):
            result = bootstrap_ffmpeg.ensure_ffmpeg_tools(self.tmp, force=False)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "already_available")
        ff, fp = bootstrap_ffmpeg._exe_names()
        self.assertEqual(os.path.abspath(result["ffmpegPath"]), os.path.abspath(paths[ff]))
        self.assertEqual(os.path.abspath(result["ffprobePath"]), os.path.abspath(paths[fp]))

    # --- 2. extracao + promocao atomica --------------------------------------
    def test_02_extracao_atomica_de_zip_simulado(self):
        zip_path = os.path.join(self.tmp, "pkg.zip")
        _write_zip(zip_path, _essentials_entries())
        staging = os.path.join(self.tmp, "staging")

        ff_src, fp_src = bootstrap_ffmpeg._extract_binaries(zip_path, staging)
        ff, fp = bootstrap_ffmpeg._exe_names()
        self.assertTrue(os.path.isfile(os.path.join(staging, ff)))
        self.assertTrue(os.path.isfile(os.path.join(staging, fp)))

        ff_dest, fp_dest = bootstrap_ffmpeg._promote(ff_src, fp_src, self.tools_dir)
        self.assertTrue(os.path.isfile(ff_dest))
        self.assertTrue(os.path.isfile(fp_dest))
        with open(ff_dest, "rb") as handle:
            self.assertEqual(handle.read(), b"FAKE-FFMPEG-BYTES")
        # staging esvaziado apos a promocao (movido, nao copiado)
        self.assertFalse(os.path.exists(os.path.join(staging, ff)))

    # --- 3. --check-only exit codes ------------------------------------------
    def test_03_check_only_ausente_retorna_1(self):
        with mock.patch.object(bootstrap_ffmpeg, "_resolve_main_root",
                               lambda r=".": self.tmp), \
             mock.patch.object(bootstrap_ffmpeg.shutil, "which", lambda name: None):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = bootstrap_ffmpeg.main(["--check-only", "--json", "--root", self.tmp])
        self.assertEqual(rc, 1)
        payload = json.loads(buf.getvalue())
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["status"], "missing")

    def test_04_check_only_presente_retorna_0(self):
        self._make_local_binaries()
        with mock.patch.object(bootstrap_ffmpeg, "_resolve_main_root",
                               lambda r=".": self.tmp), \
             mock.patch.object(bootstrap_ffmpeg, "_probe", _fake_probe), \
             mock.patch.object(bootstrap_ffmpeg.shutil, "which", lambda name: None):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = bootstrap_ffmpeg.main(["--check-only", "--json", "--root", self.tmp])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "available")

    # --- 4. contencao de caminho ---------------------------------------------
    def test_05_contencao_de_caminho_zip(self):
        ff, fp = bootstrap_ffmpeg._exe_names()
        zip_path = os.path.join(self.tmp, "malicioso.zip")
        _write_zip(zip_path, [
            (f"../../evil/bin/{ff}", b"X"),
            (f"../../../etc/bin/{fp}", b"Y"),
        ])
        staging = os.path.join(self.tmp, "staging")
        bootstrap_ffmpeg._extract_binaries(zip_path, staging)

        # Sempre grava pelo basename, dentro do staging.
        self.assertTrue(os.path.isfile(os.path.join(staging, ff)))
        self.assertTrue(os.path.isfile(os.path.join(staging, fp)))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "evil")))
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.tmp), "evil")))

    # --- 5. limpeza de temporarios -------------------------------------------
    def test_06_limpeza_de_temporarios_apos_instalar(self):
        def fake_download(url, dest_zip):
            _write_zip(dest_zip, _essentials_entries())
            return "deadbeefcafe"

        with mock.patch.object(bootstrap_ffmpeg, "_resolve_main_root",
                               lambda r=".": self.tmp), \
             mock.patch.object(bootstrap_ffmpeg, "_probe", _fake_probe), \
             mock.patch.object(bootstrap_ffmpeg, "_is_gitignored", lambda *a: True), \
             mock.patch.object(bootstrap_ffmpeg, "_download", fake_download), \
             mock.patch.object(bootstrap_ffmpeg, "_WINDOWS", True), \
             mock.patch.object(bootstrap_ffmpeg.shutil, "which", lambda name: None):
            result = bootstrap_ffmpeg.ensure_ffmpeg_tools(self.tmp, force=True)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "installed")
        self.assertTrue(os.path.isfile(result["ffmpegPath"]))
        self.assertTrue(os.path.isfile(result["ffprobePath"]))
        tmp_root = os.path.join(self.tmp, ".workspace", "tmp", "ffmpeg-bootstrap")
        self.assertFalse(os.path.exists(tmp_root),
                         "o diretorio temporario do bootstrap deveria ser removido")

    # --- 6. payload JSON estruturado -----------------------------------------
    def test_07_cli_json_payload_estruturado(self):
        with mock.patch.object(bootstrap_ffmpeg, "_resolve_main_root",
                               lambda r=".": self.tmp), \
             mock.patch.object(bootstrap_ffmpeg.shutil, "which", lambda name: None):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                bootstrap_ffmpeg.main(["--check-only", "--json", "--root", self.tmp])
        payload = json.loads(buf.getvalue())
        for chave in ("ok", "status", "mainRoot", "toolsDir",
                      "ffmpegPath", "ffprobePath", "version"):
            self.assertIn(chave, payload)

    # --- Deteccao real no ambiente (skip antes, valida depois da instalacao) --
    def test_08_deteccao_real_no_ambiente(self):
        main_root = bootstrap_ffmpeg._resolve_main_root(REPO_ROOT)
        self.assertTrue(os.path.isdir(main_root), main_root)
        existing = bootstrap_ffmpeg._find_existing(main_root)
        if existing is None:
            self.skipTest("ffmpeg real ausente; instale via bootstrap_ffmpeg.py para exercitar")
        self.assertIn("version", existing)
        self.assertTrue(os.path.isfile(existing["ffmpegPath"]))


if __name__ == "__main__":
    unittest.main()