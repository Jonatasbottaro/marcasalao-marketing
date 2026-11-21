"""Testes da CLI de aprovacoes do titular (tools/approval_cli.py).

Cobre (>= 10 casos):
  1. status inicial sem arquivo (10 campanhas, tudo aguardando).
  2. decide aprovado gravando documento v2 com updatedAt e resumo.
  3. hashes SHA-256 vindos do manifest.json da entrega.
  4. ajuste exige --notes e nao grava nada quando ausente.
  5. ajuste com notes persiste observacoes.
  6. decide aguardando.
  7. tenant/campanha inexistente.
  8. staleApproval quando o hash do manifesto muda apos a decisao.
  9. validate reprova schemaVersion antigo e campanha desconhecida.
 10. roundtrip com handoff_bundler.load_approvals.
 11. contencao de path do --approvals-file.
 12. CLI --json (decide + status) com exit 0.
 13. escrita atomica sem sobra .tmp.
 14. migracao de item legado v1 (aprovada: true).

O fixture vive em <RAIZ>/.workspace/tmp/test_approval_cli (regra de
armazenamento do projeto; nada em %TEMP%).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import approval_cli
import handoff_bundler
import render_local

FIXTURE_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "test_approval_cli")
MARCA = ("marca-salao", "camp-saas-demo-marca-salao-001")
MEU = ("meu-salao", "camp-saas-demo-meu-salao-001")
BASE_HASHES = {
    "video": "a" * 64,
    "srt": "b" * 64,
    "narration": "c" * 64,
    "storyboard": "d" * 64,
}


def _write_json(path: str, doc: dict) -> None:
    os.makedirs(render_local.fs_path(os.path.dirname(path)), exist_ok=True)
    with open(render_local.fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(doc, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _read_json(path: str) -> dict:
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _manifest_doc(video_sha: str = BASE_HASHES["video"]) -> dict:
    return {
        "schemaVersion": 1,
        "artifacts": {
            "video": {"sha256": video_sha},
            "srt": {"sha256": BASE_HASHES["srt"]},
            "narration": {"sha256": BASE_HASHES["narration"]},
            "storyboard": {"sha256": BASE_HASHES["storyboard"]},
        },
    }


class ApprovalCliTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if os.path.isdir(render_local.fs_path(FIXTURE_ROOT)):
            shutil.rmtree(render_local.fs_path(FIXTURE_ROOT))
        os.makedirs(render_local.fs_path(FIXTURE_ROOT), exist_ok=True)
        cls.root = os.path.realpath(FIXTURE_ROOT)
        shutil.copytree(
            render_local.fs_path(os.path.join(REPO_ROOT, "tenants")),
            render_local.fs_path(os.path.join(cls.root, "tenants")),
        )
        cls.manifest_rel = os.path.join(
            "02-reels-shorts", "deliveries", MARCA[0], MARCA[1], "manifest.json"
        )
        _write_json(os.path.join(cls.root, cls.manifest_rel), _manifest_doc())
        os.makedirs(render_local.fs_path(os.path.join(cls.root, ".workspace", "tmp")), exist_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(render_local.fs_path(cls.root), ignore_errors=True)

    def _store(self, name: str) -> str:
        return f".workspace/tmp/{name}.json"

    def _abs(self, rel: str) -> str:
        return os.path.join(self.root, *rel.split("/"))

    def _decide(self, name: str, campaign: tuple[str, str] = MEU, **kwargs) -> dict:
        defaults = {
            "root": self.root,
            "tenant_id": campaign[0],
            "campaign_slug": campaign[1],
            "decision": "aprovado",
            "reviewer": "Titular",
            "notes": None,
            "external_audio_checked": False,
            "approvals_file": self._store(name),
        }
        defaults.update(kwargs)
        return approval_cli.cmd_decide(**defaults)

    # 1 ---------------------------------------------------------------
    def test_01_status_without_store(self) -> None:
        res = approval_cli.cmd_status(
            root=self.root, approvals_file=self._store("inexistente-status")
        )
        self.assertTrue(res["ok"])
        self.assertFalse(res["exists"])
        self.assertEqual(res["summary"], {"total": 14, "aprovadas": 0, "aguardando": 14, "ajuste": 0})
        self.assertEqual({row["decision"] for row in res["campaigns"]}, {"aguardando"})
        self.assertIn("marca-salao", res["externalAudioTenants"])
        self.assertNotIn("multitrack-hub", res["externalAudioTenants"])

    # 2 ---------------------------------------------------------------
    def test_02_decide_aprovado_writes_v2_document(self) -> None:
        res = self._decide("aprov-aprovado")
        self.assertTrue(res["ok"])
        self.assertIs(res["autoPublish"], False)
        self.assertRegex(res["updatedAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

        doc = _read_json(self._abs(res["approvalsFile"]))
        self.assertEqual(doc["schemaVersion"], 2)
        self.assertEqual(doc["arquivo"], "aprovacoes-titular.json")
        self.assertEqual(doc["origem"], "tools/approval_cli.py")
        self.assertEqual(doc["revisor"], "Titular")
        self.assertEqual(doc["resumo"], {"totalCampanhas": 1, "aprovadas": 1, "ajustes": 0, "pendentes": 0})
        item = doc["campanhas"][0]
        self.assertEqual((item["tenantId"], item["slug"], item["decisao"]), (MEU[0], MEU[1], "aprovado"))
        self.assertEqual(item["updatedAt"], res["updatedAt"])

    # 3 ---------------------------------------------------------------
    def test_03_decide_records_current_manifest_hashes(self) -> None:
        res = self._decide("aprov-hashes", campaign=MARCA)
        item = _read_json(self._abs(res["approvalsFile"]))["campanhas"][0]
        self.assertEqual(
            item["hashes"],
            {
                "video": BASE_HASHES["video"],
                "srt": BASE_HASHES["srt"],
                "narracao": BASE_HASHES["narration"],
                "storyboard": BASE_HASHES["storyboard"],
            },
        )

    # 4 ---------------------------------------------------------------
    def test_04_ajuste_without_notes_is_rejected(self) -> None:
        with self.assertRaises(approval_cli.ApprovalError) as ctx:
            self._decide("aprov-ajuste-vazio", decision="ajuste", notes="   ")
        self.assertEqual(ctx.exception.code, "NOTES_OBRIGATORIAS")
        self.assertFalse(os.path.isfile(render_local.fs_path(self._abs(self._store("aprov-ajuste-vazio")))))

    # 5 ---------------------------------------------------------------
    def test_05_ajuste_with_notes_persists_observacoes(self) -> None:
        res = self._decide(
            "aprov-ajuste", decision="ajuste", notes="Ajustar chamada do CTA."
        )
        item = _read_json(self._abs(res["approvalsFile"]))["campanhas"][0]
        self.assertEqual(item["decisao"], "ajuste")
        self.assertEqual(item["observacoes"], "Ajustar chamada do CTA.")

    # 6 ---------------------------------------------------------------
    def test_06_decide_aguardando(self) -> None:
        res = self._decide("aprov-aguardando", decision="aguardando")
        self.assertEqual(res["decision"], "aguardando")
        doc = _read_json(self._abs(res["approvalsFile"]))
        self.assertEqual(doc["resumo"]["pendentes"], 1)

    # 7 ---------------------------------------------------------------
    def test_07_unknown_tenant_and_campaign(self) -> None:
        with self.assertRaises(approval_cli.ApprovalError) as ctx:
            self._decide("aprov-erro", campaign=("tenant-fantasma", "camp-x"))
        self.assertEqual(ctx.exception.code, "TENANT_DESCONHECIDO")
        with self.assertRaises(approval_cli.ApprovalError) as ctx:
            self._decide("aprov-erro", campaign=(MEU[0], "campanha-fantasma"))
        self.assertEqual(ctx.exception.code, "CAMPANHA_DESCONHECIDA")

    # 8 ---------------------------------------------------------------
    def test_08_validate_flags_stale_approval_when_manifest_changes(self) -> None:
        rel = self._store("aprov-stale")
        self._decide("aprov-stale", campaign=MARCA)
        clean = approval_cli.cmd_validate(root=self.root, approvals_file=rel)
        self.assertTrue(clean["ok"], clean["errors"])
        self.assertEqual(clean["staleApprovals"], [])

        manifest_abs = self._abs(self.manifest_rel)
        try:
            _write_json(manifest_abs, _manifest_doc(video_sha="e" * 64))
            stale = approval_cli.cmd_validate(root=self.root, approvals_file=rel)
        finally:
            _write_json(manifest_abs, _manifest_doc())

        self.assertFalse(stale["ok"])
        self.assertEqual(len(stale["staleApprovals"]), 1)
        self.assertEqual(stale["staleApprovals"][0]["changedHashes"], ["video"])
        self.assertTrue(stale["campaigns"][0]["staleApproval"])

    # 9 ---------------------------------------------------------------
    def test_09_validate_rejects_schema_and_unknown_campaign(self) -> None:
        bad_schema = self._store("aprov-schema")
        _write_json(
            self._abs(bad_schema),
            {"schemaVersion": 1, "campanhas": []},
        )
        res = approval_cli.cmd_validate(root=self.root, approvals_file=bad_schema)
        self.assertFalse(res["ok"])
        self.assertEqual([e["code"] for e in res["errors"]], ["SCHEMA_VERSION"])

        bad_campaign = self._store("aprov-desconhecida")
        _write_json(
            self._abs(bad_campaign),
            {
                "schemaVersion": 2,
                "campanhas": [
                    {"tenantId": MEU[0], "slug": "campanha-fantasma", "decisao": "aprovado"}
                ],
            },
        )
        res2 = approval_cli.cmd_validate(root=self.root, approvals_file=bad_campaign)
        self.assertFalse(res2["ok"])
        self.assertIn("CAMPANHA_DESCONHECIDA", [e["code"] for e in res2["errors"]])

    # 10 --------------------------------------------------------------
    def test_10_roundtrip_with_handoff_bundler(self) -> None:
        res = self._decide("aprov-roundtrip")
        index = handoff_bundler.load_approvals(self._abs(res["approvalsFile"]))
        self.assertEqual(index[(MEU[0], MEU[1])]["status"], "aprovado")

    # 11 --------------------------------------------------------------
    def test_11_approvals_path_containment(self) -> None:
        with self.assertRaises(approval_cli.ApprovalError) as ctx:
            self._decide("ignorado", approvals_file="../../fora-do-projeto.json")
        self.assertEqual(ctx.exception.code, "APPROVALS_FORA_DA_RAIZ")
        with self.assertRaises(approval_cli.ApprovalError) as ctx_status:
            approval_cli.cmd_status(root=self.root, approvals_file="../../fora.json")
        self.assertEqual(ctx_status.exception.code, "APPROVALS_FORA_DA_RAIZ")

    # 12 --------------------------------------------------------------
    def test_12_cli_json_decide_and_status(self) -> None:
        rel = self._store("aprov-cli")
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = approval_cli.main([
                "decide", "--root", self.root,
                "--tenant", MEU[0], "--campaign", MEU[1],
                "--decision", "aprovado", "--reviewer", "Titular",
                "--external-audio-checked", "--approvals-file", rel, "--json",
            ])
        self.assertEqual(rc, 0)
        decide_doc = json.loads(buf.getvalue())
        self.assertTrue(decide_doc["ok"])
        self.assertTrue(decide_doc["campaign"]["locucaoExternaConferida"])

        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = approval_cli.main([
                "status", "--root", self.root, "--approvals-file", rel, "--json",
            ])
        self.assertEqual(rc, 0)
        status_doc = json.loads(buf.getvalue())
        self.assertEqual(status_doc["summary"]["aprovadas"], 1)

    # 13 --------------------------------------------------------------
    def test_13_atomic_write_leaves_no_tmp_file(self) -> None:
        res = self._decide("aprov-atomic")
        folder = os.path.dirname(self._abs(res["approvalsFile"]))
        leftovers = [name for name in os.listdir(render_local.fs_path(folder)) if name.endswith(".tmp")]
        self.assertEqual(leftovers, [])
        self.assertTrue(os.path.isfile(render_local.fs_path(self._abs(res["approvalsFile"]))))

    # 14 --------------------------------------------------------------
    def test_14_legacy_v1_item_is_migrated_on_next_decide(self) -> None:
        rel = self._store("aprov-legado")
        _write_json(
            self._abs(rel),
            {
                "schemaVersion": 2,
                "campanhas": [
                    {"tenantId": MARCA[0], "slug": MARCA[1], "aprovada": True}
                ],
            },
        )
        res = self._decide("aprov-legado", campaign=MEU)
        doc = _read_json(self._abs(res["approvalsFile"]))
        by_slug = {item["slug"]: item for item in doc["campanhas"]}
        self.assertEqual(by_slug[MARCA[1]]["decisao"], "aprovado")
        self.assertNotIn("aprovada", by_slug[MARCA[1]])
        self.assertEqual(by_slug[MEU[1]]["decisao"], "aprovado")
        self.assertEqual(doc["resumo"]["aprovadas"], 2)


if __name__ == "__main__":
    unittest.main()