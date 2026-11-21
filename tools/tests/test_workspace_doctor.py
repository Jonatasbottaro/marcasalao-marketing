"""Testes do doutor local de higiene do workspace (Etapa 6 - Agente 6).

Todos os diretorios temporarios ficam sob ``<RAIZ>/.workspace/tmp/`` para
respeitar a regra de armazenamento do projeto, mesmo usando ``TemporaryDirectory``.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

import workspace_doctor as wd

TENANT = "marca-salao"
SLUG = "camp-saas-demo-marca-salao-001"
TMP_PARENT = REPO_ROOT / ".workspace" / "tmp" / "etapa6-agente6-doctor-tests"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class WorkspaceDoctorTest(unittest.TestCase):
    def setUp(self) -> None:
        TMP_PARENT.mkdir(parents=True, exist_ok=True)
        self._tmp = tempfile.TemporaryDirectory(prefix="doctor-", dir=str(TMP_PARENT))
        self.root = Path(self._tmp.name)

        def cleanup() -> None:
            self._tmp.cleanup()
            shutil.rmtree(TMP_PARENT, ignore_errors=True)

        self.addCleanup(cleanup)

        self.workspace = self.root / ".workspace"
        self.archives = self.workspace / "archives" / SLUG
        self.derivatives = self.archives / "derivatives"
        self.derivatives.mkdir(parents=True)
        self.tools = self.workspace / "tools" / "ffmpeg"
        self.tools.mkdir(parents=True)
        self.tmp = self.workspace / "tmp"
        self.tmp.mkdir()
        (self.workspace / "devlogs").mkdir()
        (self.workspace / "devlogs" / "etapa6-agente6.md").write_text("devlog", encoding="utf-8")
        (self.workspace / "worktrees").mkdir()

        self.media: dict[str, tuple[Path, bytes]] = {}
        self._write_media(self.archives / f"{SLUG}.mp4", b"video-9x16", "9:16")
        self._write_media(self.derivatives / f"{SLUG}-1x1.mp4", b"video-1x1", "1x1")
        self._write_media(self.derivatives / f"{SLUG}-16x9.mp4", b"video-16x9", "16x9")
        self._write_media(self.derivatives / f"{SLUG}-cover.png", b"png-cover", "cover")
        self._write_media(self.derivatives / f"{SLUG}-thumb-16x9.png", b"png-thumb", "thumb-16x9")
        self._write_media(self.derivatives / f"{SLUG}-preview-grid.png", b"png-grid", "preview-formats")

        self.delivery = self.root / "02-reels-shorts" / "deliveries" / TENANT / SLUG
        self.delivery.mkdir(parents=True)
        self.manifest_path = self.delivery / "manifest.json"
        self.derivatives_path = self.delivery / "derivatives.json"
        self._write_manifest()
        self._write_derivatives()

        for exe in ("ffmpeg.exe", "ffprobe.exe"):
            (self.tools / exe).write_bytes(b"fake-binary")

        self.approvals = self.tmp / "aprovacoes-titular.json"
        self.approvals.write_text('{"versao": 2, "aprovacoes": []}', encoding="utf-8")
        self.disposable_a = self.tmp / "ffmpeg-bootstrap"
        self.disposable_a.mkdir()
        (self.disposable_a / "staging.tmp").write_bytes(b"x" * 32)
        self.disposable_b = self.tmp / "egm"
        self.disposable_b.mkdir()
        (self.disposable_b / "rascunho.md").write_text("rascunho", encoding="utf-8")

        def fake_probe(path: str):
            name = os.path.basename(path).lower()
            if "ffprobe" in name:
                return True, "ffprobe version 9.1-essentials_build", "9.1-essentials_build"
            return True, "ffmpeg version 9.1-essentials_build", "9.1-essentials_build"

        # O diretorio temporario vive DENTRO do checkout; sem este patch o
        # _resolve_main_root (via --git-common-dir) apontaria para o .workspace/
        # principal real. Cada teste deve operar apenas na sua propria fixture.
        self._root_patch = mock.patch.object(
            wd, "_resolve_main_root", return_value=str(self.root)
        )
        self._root_patch.start()
        self.addCleanup(self._root_patch.stop)

        self._probe_patch = mock.patch.object(wd, "_probe_version", side_effect=fake_probe)
        self._probe_patch.start()
        self.addCleanup(self._probe_patch.stop)

    def _write_media(self, path: Path, data: bytes, kind: str) -> None:
        path.write_bytes(data)
        self.media[kind] = (path, data)

    def _rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def _write_manifest(self) -> None:
        path, data = self.media["9:16"]
        payload = {
            "schemaVersion": 1,
            "tenantId": TENANT,
            "artifacts": {
                "video": {
                    "path": f"02-reels-shorts/deliveries/{TENANT}/{SLUG}/{SLUG}.mp4",
                    "archivePath": self._rel(path),
                    "sha256": _sha(data),
                    "versioned": False,
                }
            },
        }
        self.manifest_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _write_derivatives(self, override_1x1: str | None = None) -> None:
        source_path, source_data = self.media["9:16"]
        derivatives: dict = {}
        for kind in ("1x1", "16x9", "cover", "thumb-16x9", "preview-formats"):
            path, data = self.media[kind]
            entry: dict = {"path": self._rel(path), "sha256": _sha(data), "kind": kind}
            if kind == "1x1" and override_1x1 is not None:
                entry["path"] = override_1x1
            derivatives[kind] = entry
        payload = {
            "schemaVersion": 2,
            "tenantId": TENANT,
            "slug": SLUG,
            "source": {"path": self._rel(source_path), "sha256": _sha(source_data)},
            "derivatives": derivatives,
        }
        self.derivatives_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _problems(self, result: dict, code: str) -> list[dict]:
        return [
            problem
            for section in result["sections"]
            for problem in section["problems"]
            if problem["code"] == code
        ]

    def test_01_auditoria_integra_e_formatos(self) -> None:
        result = wd.run_workspace_doctor(self.root)
        self.assertTrue(result["ok"], result["sections"])
        self.assertEqual(result["summary"]["errors"], 0)
        self.assertEqual(len(result["sections"]), 4)
        archives = result["summary"]["archives"]
        self.assertEqual(archives["divergentes"], 0)
        self.assertEqual(archives["ausentes"], 0)
        self.assertEqual(archives["naoDeclarados"], 0)
        self.assertEqual(archives["verificados"], 6)
        self.assertEqual(archives["porFormato"], {"9:16": 1, "1x1": 1, "16x9": 1})
        self.assertEqual(archives["porTipo"]["cover"], 1)
        self.assertEqual(archives["porTipo"]["thumb-16x9"], 1)
        self.assertEqual(result["summary"]["ffmpeg"]["ffmpeg"]["version"], "9.1-essentials_build")
        self.assertEqual(result["summary"]["ffmpeg"]["ffprobe"]["version"], "9.1-essentials_build")

    def test_02_detecta_hash_corrompido_em_archive(self) -> None:
        path, _ = self.media["1x1"]
        with open(path, "ab") as handle:
            handle.write(b"CORROMPIDO")
        result = wd.run_workspace_doctor(self.root)
        self.assertFalse(result["ok"])
        self.assertEqual(len(self._problems(result, "ARCHIVE_HASH_DIVERGENTE")), 1)
        self.assertEqual(result["summary"]["archives"]["divergentes"], 1)
        self.assertEqual(result["summary"]["archives"]["verificados"], 5)

    def test_03_clean_tmp_preserva_protegidos(self) -> None:
        before = self.approvals.read_text(encoding="utf-8")
        result = wd.run_workspace_doctor(self.root, clean_tmp=True)
        self.assertFalse(self.disposable_a.exists())
        self.assertFalse(self.disposable_b.exists())
        self.assertEqual(self.approvals.read_text(encoding="utf-8"), before)
        self.assertTrue((self.archives / f"{SLUG}.mp4").exists())
        self.assertTrue((self.tools / "ffmpeg.exe").exists())
        self.assertTrue((self.workspace / "devlogs" / "etapa6-agente6.md").exists())
        self.assertIn("tmp/ffmpeg-bootstrap", result["cleaned"])
        self.assertIn("tmp/egm", result["cleaned"])

    def test_04_clean_tmp_preserva_arquivos_soltos(self) -> None:
        loose = self.tmp / "rascunho-local.txt"
        loose.write_text("nao apagar", encoding="utf-8")
        wd.run_workspace_doctor(self.root, clean_tmp=True)
        self.assertTrue(loose.exists())
        self.assertTrue(self.approvals.exists())
        self.assertFalse(self.disposable_a.exists())
        self.assertNotIn("tmp/rascunho-local.txt", wd.run_workspace_doctor(self.root)["cleaned"])

    def test_05_declaracao_fora_de_archives_e_recusada(self) -> None:
        self._write_derivatives(override_1x1="../../fora-da-raiz.mp4")
        result = wd.run_workspace_doctor(self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(self._problems(result, "PATH_OUTSIDE_ARCHIVES"))
        self.assertEqual(result["summary"]["archives"]["ausentes"], 0)
        self.assertEqual(result["summary"]["archives"]["naoDeclarados"], 1)

    def test_06_contenção_de_alvos_do_clean_tmp(self) -> None:
        tmp_root = self.tmp
        self.assertIsNone(wd._clean_tmp_target(str(tmp_root), "aprovacoes-titular.json"))
        self.assertIsNone(wd._clean_tmp_target(str(tmp_root), "../archives"))
        self.assertIsNone(wd._clean_tmp_target(str(tmp_root), "sub/../../archives"))
        self.assertIsNotNone(wd._clean_tmp_target(str(tmp_root), "ffmpeg-bootstrap"))
        self.assertTrue((self.archives / f"{SLUG}.mp4").exists())

    def test_07_cli_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = wd.main(["--root", str(self.root), "--json"])
        payload = json.loads(buf.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["mode"], "check")
        self.assertEqual(payload["mainRoot"], str(self.root.resolve()))
        self.assertEqual(len(payload["sections"]), 4)

    def test_08_cli_clean_tmp_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = wd.main(["--root", str(self.root), "--clean-tmp", "--json"])
        payload = json.loads(buf.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(payload["mode"], "clean-tmp")
        self.assertIn("tmp/ffmpeg-bootstrap", payload["cleaned"])
        self.assertTrue(self.approvals.exists())

    def test_09_ffmpeg_ausente(self) -> None:
        (self.tools / "ffmpeg.exe").unlink()
        result = wd.run_workspace_doctor(self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(self._problems(result, "FFMPEG_AUSENTE"))
        self.assertFalse(result["summary"]["ffmpeg"]["ffmpeg"]["present"])
        self.assertTrue(result["summary"]["ffmpeg"]["ffprobe"]["valid"])

    def test_10_worktrees_e_nao_rastreados(self) -> None:
        (self.workspace / "worktrees" / "etapa6-agente6").mkdir()
        (self.workspace / "worktrees" / "orfa-local").mkdir()

        def fake_git(root: str, *args: str) -> str:
            if args[0] == "worktree":
                return (
                    f"worktree {root}\nbranch refs/heads/main\n\n"
                    f"worktree {root}/.workspace/worktrees/etapa6-agente6\n"
                    "branch refs/heads/codex/etapa6-agente6\n\n"
                    f"worktree {root}/.workspace/worktrees/etapa6-fantasma\n"
                    "branch refs/heads/codex/fantasma\n"
                )
            if args[0] == "status":
                return "?? 02-reels-shorts/deliveries/novo/\n?? tools/__pycache__/\n"
            return ""

        with mock.patch.object(wd, "_run_git", side_effect=fake_git):
            result = wd.run_workspace_doctor(self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(self._problems(result, "WORKTREE_REGISTRADA_SEM_DIRETORIO"))
        self.assertTrue(self._problems(result, "WORKTREE_ORFA"))
        self.assertTrue(self._problems(result, "ARQUIVOS_NAO_RASTREADOS"))
        self.assertEqual(result["summary"]["worktrees"]["arquivosNaoRastreados"], 2)
        self.assertFalse(self._problems(result, "GIT_INDISPONIVEL"))

    def test_11_midia_nao_declarada_e_midia_ausente_sao_avisos(self) -> None:
        extra = self.derivatives / "extra-nao-declarado.png"
        extra.write_bytes(b"extra")
        source_path, _ = self.media["9:16"]
        source_path.unlink()
        result = wd.run_workspace_doctor(self.root)
        self.assertTrue(result["ok"])
        self.assertTrue(self._problems(result, "MIDIA_NAO_DECLARADA"))
        self.assertTrue(self._problems(result, "MIDIA_AUSENTE"))
        self.assertEqual(result["summary"]["archives"]["ausentes"], 1)
        self.assertEqual(result["summary"]["archives"]["naoDeclarados"], 1)


if __name__ == "__main__":
    unittest.main()
