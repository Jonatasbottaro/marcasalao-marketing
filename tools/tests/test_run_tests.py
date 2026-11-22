"""Testes do runner particionado tools/run_tests.py e da blindagem de archives.

Cobre obrigatoriamente:
  1. Particao explicita fast vs render: todo modulo test_*.py classificado,
     sem sobreposicao e sem modulo orfao.
  2. Resolucao de grupos: --fast e o padrao; --render e --all selecionam o
     grupo pesado; flags combinadas equivalem a --all.
  3. Saida --json com contagem de testes, aprovados, falhas, duracao e modulos.
  4. Garantia de que a execucao nao altera os SHA-256 de .workspace/archives/,
     tanto pelo runner quanto por restauro automatico do ArchivesGuard.
  5. Regressao do vazamento real: os testes de render que chamam o pipeline
     canonico precisam passar archives_dir isolado.

O runner nunca e invocado sobre o grupo fast completo aqui: test_run_tests
pertence a esse grupo e a chamada seria recursiva. Os casos usam subconjuntos
explicitos de modulos baratos.
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import archives_guard  # noqa: E402
import factory_cli  # noqa: E402
import release_check  # noqa: E402
import run_tests  # noqa: E402

TEST_TMP_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "test_run_tests")
CHEAP_MODULE = "test_srt_validate"


def _fake_media(path: str, payload: bytes) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(payload)
    return path


class RunTestsPartitionTest(unittest.TestCase):
    def test_01_every_test_module_is_classified_exactly_once(self) -> None:
        partition = run_tests.partition_modules(REPO_ROOT)
        self.assertEqual(partition["unclassified"], [], "modulo novo sem classificacao")
        overlap = set(run_tests.FAST_MODULES) & set(run_tests.RENDER_MODULES)
        self.assertEqual(overlap, set(), "modulo em dois grupos ao mesmo tempo")

        directory = run_tests.tests_dir(REPO_ROOT)
        present = {
            name[:-3]
            for name in os.listdir(directory)
            if name.startswith("test_") and name.endswith(".py")
        }
        classified = set(partition["fast"]) | set(partition["render"])
        self.assertEqual(present, classified)

    def test_02_known_render_modules_are_in_render_group(self) -> None:
        partition = run_tests.partition_modules(REPO_ROOT)
        for name in (
            "test_preset_runner",
            "test_derivative_formats",
            "test_audio_tts",
            "test_factory_cli",
            "test_render_pipeline",
            "test_studio_media",
            "test_video_studio",
        ):
            self.assertIn(name, partition["render"], f"{name} deveria estar em render")
            self.assertNotIn(name, partition["fast"])

    def test_03_known_contract_modules_are_in_fast_group(self) -> None:
        partition = run_tests.partition_modules(REPO_ROOT)
        for name in (
            "test_utm_report_importer",
            "test_campaign_calendar",
            "test_review_dashboard",
            "test_approval_cli",
            "test_publish_bundler",
            "test_bundle_attribution",
            "test_release_audit",
            "test_editorial_qa",
            "test_workspace_doctor",
            "test_workspace_doctor_repair",
            "test_executive_summary",
            "test_run_tests",
        ):
            self.assertIn(name, run_tests.FAST_MODULES, f"{name} deveria estar em fast")
            self.assertNotIn(name, partition["render"])

    def test_04_group_resolution_defaults_to_fast(self) -> None:
        self.assertEqual(run_tests.resolve_groups({}), ("fast",))
        self.assertEqual(run_tests.resolve_groups({"fast": True}), ("fast",))
        self.assertEqual(run_tests.resolve_groups({"render": True}), ("render",))
        self.assertEqual(run_tests.resolve_groups({"all": True}), ("fast", "render"))
        self.assertEqual(
            run_tests.resolve_groups({"fast": True, "render": True}), ("fast", "render")
        )

    def test_05_unclassified_module_fails_closed(self) -> None:
        sandbox = tempfile.mkdtemp(prefix="partition-", dir=TEST_TMP_ROOT)
        try:
            tests = os.path.join(sandbox, "tools", "tests")
            os.makedirs(tests, exist_ok=True)
            _fake_media(os.path.join(tests, "test_novo_sem_grupo.py"), b"# vazio\n")
            partition = run_tests.partition_modules(sandbox)
            self.assertEqual(partition["unclassified"], ["test_novo_sem_grupo"])
            with self.assertRaises(run_tests.RunTestsError) as ctx:
                run_tests.run_tests(sandbox, ("fast",))
            self.assertIn("test_novo_sem_grupo", str(ctx.exception))
        finally:
            shutil.rmtree(sandbox, ignore_errors=True)

    def test_06_invalid_group_rejected(self) -> None:
        with self.assertRaises(run_tests.RunTestsError):
            run_tests.run_tests(REPO_ROOT, ("lento",))


class RunTestsJsonTest(unittest.TestCase):
    def _tiny_partition(self, *_args, **_kwargs) -> dict:
        return {"fast": [CHEAP_MODULE], "render": [], "unclassified": [], "absent": []}

    def test_07_json_report_has_counts_duration_and_modules(self) -> None:
        with mock.patch.object(run_tests, "partition_modules", self._tiny_partition):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = run_tests.main(["--fast", "--json", "--root", REPO_ROOT])
        self.assertEqual(rc, 0)
        report = json.loads(buf.getvalue())

        self.assertEqual(report["schemaVersion"], 1)
        self.assertEqual(report["generatedBy"], "tools/run_tests.py")
        self.assertTrue(report["ok"])
        self.assertEqual(report["mode"], "fast")
        self.assertEqual(report["modules"], [CHEAP_MODULE])
        self.assertGreater(report["total"], 0)
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["errors"], 0)
        self.assertEqual(
            report["passed"],
            report["total"] - report["failed"] - report["errors"] - report["skipped"],
        )
        self.assertIsInstance(report["durationSeconds"], float)
        self.assertGreaterEqual(report["durationSeconds"], 0.0)
        self.assertIn("fast", report["partition"])
        self.assertIn("render", report["partition"])

    def test_08_all_flag_selects_both_groups(self) -> None:
        with mock.patch.object(run_tests, "partition_modules", self._tiny_partition):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = run_tests.main(["--all", "--json", "--root", REPO_ROOT])
        self.assertEqual(rc, 0)
        report = json.loads(buf.getvalue())
        self.assertEqual(report["mode"], "all")

    def test_08b_json_expoe_o_contrato_de_chaves_pedido(self) -> None:
        with mock.patch.object(run_tests, "partition_modules", self._tiny_partition):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                run_tests.main(["--fast", "--json", "--root", REPO_ROOT])
        report = json.loads(buf.getvalue())
        for key in ("ok", "mode", "total", "passed", "failed", "errors", "durationSeconds", "modules"):
            self.assertIn(key, report, f"chave obrigatoria ausente: {key}")
        self.assertIsInstance(report["ok"], bool)
        self.assertIsInstance(report["mode"], str)
        self.assertIsInstance(report["total"], int)
        self.assertIsInstance(report["modules"], list)

    def test_08c_mode_render_quando_so_o_grupo_pesado(self) -> None:
        with mock.patch.object(
            run_tests, "partition_modules",
            lambda *_a, **_k: {"fast": [], "render": [CHEAP_MODULE], "unclassified": [], "absent": []},
        ):
            report = run_tests.run_tests(REPO_ROOT, ("render",))
        self.assertEqual(report["mode"], "render")
        self.assertEqual(report["modules"], [CHEAP_MODULE])

    def test_09_failing_module_reproves_runner(self) -> None:
        sandbox = tempfile.mkdtemp(prefix="failing-", dir=TEST_TMP_ROOT)
        try:
            tests = os.path.join(sandbox, "tools", "tests")
            os.makedirs(tests, exist_ok=True)
            _fake_media(
                os.path.join(tests, "test_sempre_falha.py"),
                b"import unittest\n"
                b"class FalhaTest(unittest.TestCase):\n"
                b"    def test_falha(self):\n"
                b"        self.assertTrue(False)\n",
            )
            with mock.patch.object(
                run_tests,
                "partition_modules",
                lambda *_a, **_k: {
                    "fast": ["test_sempre_falha"],
                    "render": [],
                    "unclassified": [],
                    "absent": [],
                },
            ):
                report = run_tests.run_tests(sandbox, ("fast",))
            self.assertFalse(report["ok"])
            self.assertEqual(report["total"], 1)
            self.assertEqual(report["failed"], 1)
            self.assertEqual(report["passed"], 0)
        finally:
            shutil.rmtree(sandbox, ignore_errors=True)


class ArchivesGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        os.makedirs(TEST_TMP_ROOT, exist_ok=True)
        self.sandbox = tempfile.mkdtemp(prefix="guard-", dir=TEST_TMP_ROOT)
        self.master = os.path.join(
            self.sandbox, ".workspace", "archives", "camp-fake", "camp-fake.mp4"
        )
        _fake_media(self.master, b"master-original" * 100)
        self.original = archives_guard.sha256_file(self.master)

    def tearDown(self) -> None:
        shutil.rmtree(self.sandbox, ignore_errors=True)

    def test_10_guard_restores_corrupted_master(self) -> None:
        with archives_guard.ArchivesGuard(self.sandbox) as guard:
            _fake_media(self.master, b"corrompido-pelo-teste")
            self.assertNotEqual(archives_guard.sha256_file(self.master), self.original)
        self.assertEqual(archives_guard.sha256_file(self.master), self.original)
        self.assertEqual(guard.report["restored"], ["camp-fake/camp-fake.mp4"])
        self.assertFalse(guard.report["ok"])

    def test_11_guard_restores_deleted_master(self) -> None:
        with archives_guard.ArchivesGuard(self.sandbox) as guard:
            os.remove(self.master)
        self.assertTrue(os.path.isfile(self.master))
        self.assertEqual(archives_guard.sha256_file(self.master), self.original)
        self.assertEqual(guard.report["restored"], ["camp-fake/camp-fake.mp4"])

    def test_12_guard_discards_media_created_during_run(self) -> None:
        extra = os.path.join(
            self.sandbox, ".workspace", "archives", "camp-fake", "intruso.png"
        )
        with archives_guard.ArchivesGuard(self.sandbox) as guard:
            _fake_media(extra, b"png-do-teste")
        self.assertFalse(os.path.exists(extra))
        self.assertEqual(guard.report["discarded"], ["camp-fake/intruso.png"])
        self.assertEqual(archives_guard.sha256_file(self.master), self.original)

    def test_13_guard_reports_ok_when_nothing_changed(self) -> None:
        with archives_guard.ArchivesGuard(self.sandbox) as guard:
            pass
        self.assertTrue(guard.report["ok"])
        self.assertEqual(guard.report["restored"], [])
        self.assertEqual(guard.report["discarded"], [])
        self.assertEqual(guard.report["filesBefore"], 1)

    def test_14_guard_restores_even_when_block_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            with archives_guard.ArchivesGuard(self.sandbox):
                _fake_media(self.master, b"corrompido-antes-do-erro")
                raise RuntimeError("falha no meio do run")
        self.assertEqual(archives_guard.sha256_file(self.master), self.original)

    def test_15_isolated_archives_stays_inside_root_tmp(self) -> None:
        with archives_guard.isolated_archives(self.sandbox) as archives:
            self.assertTrue(os.path.isdir(archives))
            expected = os.path.join(self.sandbox, ".workspace", "tmp")
            self.assertEqual(os.path.commonpath([expected, archives]), expected)
            leaked = archives
        self.assertFalse(os.path.exists(leaked), "diretorio isolado deve ser descartado")

    def test_16_backup_does_not_escape_root(self) -> None:
        with archives_guard.ArchivesGuard(self.sandbox) as guard:
            self.assertIsNotNone(guard._backup)
            expected = os.path.join(self.sandbox, ".workspace", "tmp")
            self.assertEqual(os.path.commonpath([expected, guard._backup]), expected)


class SharedArchivesIntegrityTest(unittest.TestCase):
    def test_17_runner_does_not_change_real_archive_hashes(self) -> None:
        before = archives_guard.snapshot(REPO_ROOT)
        self.assertTrue(before, "archives reais ausentes nesta estacao")
        with mock.patch.object(
            run_tests,
            "partition_modules",
            lambda *_a, **_k: {
                "fast": [CHEAP_MODULE],
                "render": [],
                "unclassified": [],
                "absent": [],
            },
        ):
            report = run_tests.run_tests(REPO_ROOT, ("fast",))
        self.assertTrue(report["ok"])
        self.assertTrue(report["archivesGuard"]["ok"], report["archivesGuard"])
        self.assertEqual(archives_guard.snapshot(REPO_ROOT), before)

    def test_18_render_tests_pass_isolated_archives_dir(self) -> None:
        """Regressao: estes dois renders ja sobrescreveram os masters reais."""
        for name in ("test_audio_tts.py", "test_factory_cli.py"):
            with open(os.path.join(TOOLS_DIR, "tests", name), "r", encoding="utf-8") as handle:
                source = handle.read()
            self.assertTrue(
                "archives_dir" in source or "--archives-dir" in source,
                f"{name} sem archives isolado",
            )
            self.assertIn("ArchivesGuard", source, f"{name} sem blindagem de modulo")

    def test_19_factory_cli_render_exposes_archives_dir(self) -> None:
        self.assertIn("archives_dir", inspect.signature(factory_cli.cmd_render).parameters)
        self.assertIn("archives_dir", inspect.signature(factory_cli.cmd_pipeline).parameters)


class ReleaseCheckGateTest(unittest.TestCase):
    """O gate 8 de release_check precisa usar --fast por padrao e --all com --full-tests."""

    def _fake_run(self, payload: dict, returncode: int = 0):
        calls: list[list[str]] = []

        def runner(cmd, cwd=None):
            calls.append(cmd)
            return subprocess.CompletedProcess(
                cmd, returncode, json.dumps(payload, ensure_ascii=False), ""
            )

        return runner, calls

    def test_20_gate_usa_fast_por_padrao(self) -> None:
        payload = {
            "ok": True, "total": 12, "passed": 12, "failed": 0, "errors": 0,
            "skipped": 0, "durationSeconds": 1.5, "modules": ["test_a", "test_b"],
            "archivesGuard": {"ok": True, "restored": [], "discarded": []},
        }
        runner, calls = self._fake_run(payload)
        with mock.patch.object(release_check, "_run", runner):
            detail = release_check.gate_unit_tests(REPO_ROOT)
        self.assertTrue(detail["ok"])
        self.assertEqual(detail["group"], "--fast")
        self.assertIn("--fast", calls[0])
        self.assertNotIn("--all", calls[0])
        self.assertEqual(detail["tests"]["total"], 12)
        self.assertEqual(detail["tests"]["passed"], 12)
        self.assertEqual(detail["totalModules"], 2)

    def test_21_gate_full_tests_usa_all(self) -> None:
        runner, calls = self._fake_run({"ok": True, "total": 1, "modules": []})
        with mock.patch.object(release_check, "_run", runner):
            detail = release_check.gate_unit_tests(REPO_ROOT, full=True)
        self.assertEqual(detail["group"], "--all")
        self.assertIn("--all", calls[0])

    def test_22_gate_reprova_quando_runner_falha(self) -> None:
        runner, _ = self._fake_run({"ok": False, "failed": 2}, returncode=1)
        with mock.patch.object(release_check, "_run", runner):
            with self.assertRaises(release_check.GateError) as ctx:
                release_check.gate_unit_tests(REPO_ROOT)
        self.assertEqual(ctx.exception.code, "TESTES_FALHARAM")

    def test_23_gate_registrado_na_orquestracao(self) -> None:
        ids = [gate_id for gate_id, _ in release_check.GATES]
        self.assertIn("unit_tests", ids)
        self.assertIn("unit_tests", release_check.GATE_LABELS)
        self.assertEqual(ids.index("unit_tests"), ids.index("e2e") - 1)


def setUpModule() -> None:
    os.makedirs(TEST_TMP_ROOT, exist_ok=True)


def tearDownModule() -> None:
    shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()