"""Testes do auditor de prontidao de release (tools/release_audit.py).

Cobertura:
  - Aprovacao completa no repositorio atual (modo normal, sem --strict).
  - Sandbox fiel do repositorio aprova no modo normal e reprova no --strict
    (video nao versionado ausente e worktrees historicas ausentes viram aviso).
  - Falhas simuladas: hash corrompido, arquivo ausente, diretorio de entrega
    ausente, autoPublish true, pacote ausente, midia rastreada, .gitattributes
    sem eol=lf, worktree registrada sem diretorio e worktree orfa.
"""

import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
# Caminho curto: o worktree ja e profundo e o Windows falha com WinError 3
# acima de ~248 caracteres (limiar de render_local.fs_path).
TEST_TMP_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "rel-audit")

sys.path.insert(0, TOOLS_DIR)

import release_audit  # noqa: E402


def _force_rmtree(path: str) -> None:
    if not os.path.isdir(path):
        return
    for dirpath, _dirnames, filenames in os.walk(path):
        for fname in filenames:
            target = os.path.join(dirpath, fname)
            try:
                os.chmod(target, stat.S_IWRITE)
            except OSError:
                pass
    shutil.rmtree(path, ignore_errors=True)


def _count_campaign_files(root: str) -> int:
    tenants_dir = os.path.join(root, "tenants")
    total = 0
    for tenant in sorted(os.listdir(tenants_dir)):
        campaigns_dir = os.path.join(tenants_dir, tenant, "campaigns")
        if os.path.isdir(campaigns_dir):
            total += sum(1 for name in os.listdir(campaigns_dir) if name.endswith(".json"))
    return total


def _git(cwd: str, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class ReleaseAuditTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def tearDownClass(cls):
        _force_rmtree(TEST_TMP_ROOT)

    def _build_sandbox(self) -> str:
        method = self.id().rsplit(".", 1)[-1]
        sandbox = os.path.join(TEST_TMP_ROOT, "sb-" + method.split("_")[1])
        _force_rmtree(sandbox)
        os.makedirs(sandbox)
        shutil.copytree(os.path.join(REPO_ROOT, "schemas"), os.path.join(sandbox, "schemas"))
        shutil.copytree(os.path.join(REPO_ROOT, "tenants"), os.path.join(sandbox, "tenants"))
        shutil.copytree(
            os.path.join(REPO_ROOT, "02-reels-shorts", "deliveries"),
            os.path.join(sandbox, "02-reels-shorts", "deliveries"),
        )
        shutil.copytree(
            os.path.join(REPO_ROOT, "04-legendas", "pacotes-publicacao"),
            os.path.join(sandbox, "04-legendas", "pacotes-publicacao"),
        )
        shutil.copy2(
            os.path.join(REPO_ROOT, ".gitattributes"),
            os.path.join(sandbox, ".gitattributes"),
        )
        _git(sandbox, "init", "-q")
        _git(sandbox, "add", "-A")
        _git(
            sandbox,
            "-c", "user.name=release-audit-test",
            "-c", "user.email=release-audit-test@example.invalid",
            "commit", "-q", "-m", "sandbox",
        )
        return sandbox

    def _find_check(self, result: dict, check_id: str) -> dict:
        for check in result["checks"]:
            if check["id"] == check_id:
                return check
        self.fail(f"check ausente no resultado: {check_id}")

    def _run_cli(self, *args: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = release_audit.main(list(args))
        return code, stdout.getvalue()

    def test_01_full_approval_on_current_repo(self):
        result = release_audit.run_audit(root=REPO_ROOT)
        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["checks"]["fail"], 0)
        self.assertGreaterEqual(result["summary"]["tenants"]["valid"], 4)
        self.assertEqual(result["summary"]["tenants"]["invalid"], 0)
        self.assertEqual(result["summary"]["campaigns"]["total"], _count_campaign_files(REPO_ROOT))
        self.assertEqual(result["summary"]["campaigns"]["deliveryFailed"], 0)
        self.assertEqual(result["summary"]["campaigns"]["packageFailed"], 0)
        self.assertEqual(
            self._find_check(result, "git_hygiene:no_binary_media_tracked")["status"], "ok"
        )
        self.assertEqual(
            self._find_check(result, "git_hygiene:gitattributes_eol_lf")["status"], "ok"
        )
        code, stdout = self._run_cli("--root", REPO_ROOT, "--json")
        self.assertEqual(code, 0)
        payload = json.loads(stdout)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["strict"])

    def test_02_sandbox_baseline_approves_normal_and_fails_strict(self):
        sandbox = self._build_sandbox()
        result = release_audit.run_audit(root=sandbox)
        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["checks"]["fail"], 0)
        self.assertGreater(result["summary"]["checks"]["warn"], 0)
        self.assertEqual(result["summary"]["campaigns"]["total"], _count_campaign_files(sandbox))
        code, _ = self._run_cli("--root", sandbox, "--json")
        self.assertEqual(code, 0)
        code, stdout = self._run_cli("--root", sandbox, "--strict", "--json")
        self.assertEqual(code, 1)
        payload = json.loads(stdout)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["strict"])
        self.assertEqual(payload["summary"]["checks"]["fail"], 0)

    def test_03_corrupted_srt_hash_fails(self):
        sandbox = self._build_sandbox()
        srt_path = os.path.join(
            sandbox, "02-reels-shorts", "deliveries", "marca-salao",
            "camp-saas-demo-marca-salao-001", "camp-saas-demo-marca-salao-001.srt",
        )
        with open(srt_path, "a", encoding="utf-8") as handle:
            handle.write("x")
        result = release_audit.run_audit(root=sandbox)
        self.assertFalse(result["ok"])
        check = self._find_check(result, "delivery:marca-salao/camp-saas-demo-marca-salao-001")
        self.assertEqual(check["status"], "fail")
        self.assertTrue(any("HASH_DIVERGENTE" in problem for problem in check["problems"]))
        code, _ = self._run_cli("--root", sandbox, "--json")
        self.assertEqual(code, 1)

    def test_04_missing_storyboard_fails(self):
        sandbox = self._build_sandbox()
        storyboard = os.path.join(
            sandbox, "02-reels-shorts", "deliveries", "meu-salao",
            "camp-saas-demo-meu-salao-001", "preview-storyboard.png",
        )
        os.remove(storyboard)
        result = release_audit.run_audit(root=sandbox)
        self.assertFalse(result["ok"])
        check = self._find_check(result, "delivery:meu-salao/camp-saas-demo-meu-salao-001")
        self.assertEqual(check["status"], "fail")
        self.assertTrue(any("ARQUIVO_AUSENTE" in problem for problem in check["problems"]))
        code, _ = self._run_cli("--root", sandbox, "--json")
        self.assertEqual(code, 1)

    def test_05_missing_delivery_dir_fails(self):
        sandbox = self._build_sandbox()
        delivery_dir = os.path.join(
            sandbox, "02-reels-shorts", "deliveries", "estudio-flow",
            "camp-saas-demo-estudio-flow-001",
        )
        _force_rmtree(delivery_dir)
        result = release_audit.run_audit(root=sandbox)
        self.assertFalse(result["ok"])
        check = self._find_check(result, "delivery:estudio-flow/camp-saas-demo-estudio-flow-001")
        self.assertEqual(check["status"], "fail")
        self.assertTrue(any("DELIVERY_DIR_AUSENTE" in problem for problem in check["problems"]))
        code, _ = self._run_cli("--root", sandbox, "--json")
        self.assertEqual(code, 1)

    def test_06_auto_publish_true_fails(self):
        sandbox = self._build_sandbox()
        checklist_path = os.path.join(
            sandbox, "04-legendas", "pacotes-publicacao", "multitrack-hub",
            "camp-shorts-rateios-002", "checklist-publicacao.json",
        )
        with open(checklist_path, "r", encoding="utf-8") as handle:
            checklist = json.load(handle)
        checklist["autoPublish"] = True
        with open(checklist_path, "w", encoding="utf-8") as handle:
            json.dump(checklist, handle, indent=2, ensure_ascii=False)
        result = release_audit.run_audit(root=sandbox)
        self.assertFalse(result["ok"])
        check = self._find_check(result, "package:multitrack-hub/camp-shorts-rateios-002")
        self.assertEqual(check["status"], "fail")
        self.assertTrue(any("AUTO_PUBLICACAO_ATIVO" in problem for problem in check["problems"]))
        code, _ = self._run_cli("--root", sandbox, "--json")
        self.assertEqual(code, 1)

    def test_07_missing_package_dir_fails(self):
        sandbox = self._build_sandbox()
        package_dir = os.path.join(
            sandbox, "04-legendas", "pacotes-publicacao", "multitrack-hub",
            "camp-shorts-stems-workflow-003",
        )
        _force_rmtree(package_dir)
        result = release_audit.run_audit(root=sandbox)
        self.assertFalse(result["ok"])
        check = self._find_check(result, "package:multitrack-hub/camp-shorts-stems-workflow-003")
        self.assertEqual(check["status"], "fail")
        self.assertTrue(any("PACOTE_AUSENTE" in problem for problem in check["problems"]))
        code, _ = self._run_cli("--root", sandbox, "--json")
        self.assertEqual(code, 1)

    def test_08_tracked_media_fails(self):
        sandbox = self._build_sandbox()
        with open(os.path.join(sandbox, "fake.mp4"), "wb") as handle:
            handle.write(b"fake-video")
        with open(os.path.join(sandbox, "fake.wav"), "wb") as handle:
            handle.write(b"fake-audio")
        _git(sandbox, "add", "fake.mp4", "fake.wav")
        result = release_audit.run_audit(root=sandbox)
        self.assertFalse(result["ok"])
        check = self._find_check(result, "git_hygiene:no_binary_media_tracked")
        self.assertEqual(check["status"], "fail")
        self.assertTrue(any("MIDIA_RASTREADA" in problem for problem in check["problems"]))
        self.assertTrue(any("fake.mp4" in problem for problem in check["problems"]))
        self.assertTrue(any("fake.wav" in problem for problem in check["problems"]))
        code, _ = self._run_cli("--root", sandbox, "--json")
        self.assertEqual(code, 1)

    def test_09_gitattributes_without_eol_lf_fails(self):
        sandbox = self._build_sandbox()
        with open(os.path.join(sandbox, ".gitattributes"), "w", encoding="utf-8") as handle:
            handle.write("*.png binary\n")
        result = release_audit.run_audit(root=sandbox)
        self.assertFalse(result["ok"])
        check = self._find_check(result, "git_hygiene:gitattributes_eol_lf")
        self.assertEqual(check["status"], "fail")
        self.assertTrue(any("GITATTRIBUTES_SEM_EOL_LF" in problem for problem in check["problems"]))
        code, _ = self._run_cli("--root", sandbox, "--json")
        self.assertEqual(code, 1)

    def test_10_orphan_worktree_dir_warns(self):
        sandbox = self._build_sandbox()
        orphan_dir = os.path.join(
            sandbox, ".workspace", "worktrees", "prova-campanha-conclusao"
        )
        os.makedirs(orphan_dir)
        result = release_audit.run_audit(root=sandbox)
        self.assertTrue(result["ok"])
        check = self._find_check(result, "git_hygiene:worktree:prova-campanha-conclusao")
        self.assertEqual(check["status"], "warn")
        self.assertTrue(any("WORKTREE_ORFA" in problem for problem in check["problems"]))
        code, _ = self._run_cli("--root", sandbox, "--strict", "--json")
        self.assertEqual(code, 1)

    def test_11_registered_worktree_without_dir_fails(self):
        sandbox = self._build_sandbox()
        worktree_path = os.path.join(
            sandbox, ".workspace", "worktrees", "studio-package-verify2"
        )
        os.makedirs(os.path.dirname(worktree_path), exist_ok=True)
        # --no-checkout: o checkout do worktree excederia MAX_PATH no Windows
        # (caminho do sandbox + arquivo mais profundo da entrega); o check do
        # auditor depende apenas do registro e do diretorio ausente.
        _git(sandbox, "worktree", "add", "--detach", "--no-checkout", worktree_path)
        _force_rmtree(worktree_path)
        result = release_audit.run_audit(root=sandbox)
        self.assertFalse(result["ok"])
        check = self._find_check(result, "git_hygiene:worktree:studio-package-verify2")
        self.assertEqual(check["status"], "fail")
        self.assertTrue(
            any(
                "WORKTREE_REGISTRADA_SEM_DIRETORIO" in problem
                for problem in check["problems"]
            )
        )
        code, _ = self._run_cli("--root", sandbox, "--json")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
