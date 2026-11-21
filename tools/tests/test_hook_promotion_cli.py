"""Testes da promocao assistida de hook (tools/approval_cli.py, subcomando promote-hook).

Cobre (6 casos):
  1. dry-run padrao: preview do diff, nada grava (applied=False).
  2. --apply grava promotionHistory (timestamp UTC ISO-8601, campaignId, tenantId,
     promotedVariant, zScore, pValue, classificationReason, fatigueStatus,
     sourceReport) de forma atomica.
  3. Isolamento multi-tenant: tenant_id da linha de comparacao diferente do
     solicitado -> PROMOTION_TENANT_DIVERGENTE.
  4. Gate de significancia estatistica: nao significativo -> PROMOTION_NAO_SIGNIFICATIVO.
  5. Alerta de fadiga: fatigueDetected=True aparece proeminente no preview.
  6. Gate editorial_qa --strict antes de --apply: quando a QA reprova, o apply
     aborta com PROMOTION_EDITORIAL_QA_REPROVADA e nada grava.

O fixture vive em <RAIZ>/.workspace/tmp/test_hook_promotion_cli (regra de
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
import render_local

FIXTURE_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "test_hook_promotion_cli")
MARCA = ("marca-salao", "camp-saas-demo-marca-salao-001")
MEU = ("meu-salao", "camp-saas-demo-meu-salao-001")

BASE_HASHES = {
    "video": "a" * 64,
    "srt": "b" * 64,
    "narracao": "c" * 64,
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
            "narration": {"sha256": BASE_HASHES["narracao"]},
            "storyboard": {"sha256": BASE_HASHES["storyboard"]},
        },
    }


def _utm_report(
    tenant_id: str,
    campaign: str,
    classification: str = "vencedor_A",
    z_score: float = 2.5,
    p_value: float = 0.01,
    fatigue_detected: bool = False,
    fatigue_status: str = "estavel",
    fatigue_reason: str = "sem fadiga",
) -> dict:
    """Construi um relatorio UTM minimo com hookComparison e tenantBenchmarks."""
    return {
        "schemaVersion": 1,
        "rankings": {
            "hookComparison": {
                "minSessions": 100,
                "minConversions": 5,
                "statistics": {
                    "method": "two_proportion_z",
                    "alpha": 0.05,
                    "zThreshold": 1.96,
                    "minSessions": 100,
                    "minConversions": 5,
                },
                "byCampaign": [
                    {
                        "tenantId": tenant_id,
                        "campaign": campaign,
                        "sessionsA": 120,
                        "sessionsB": 130,
                        "conversionsA": 10,
                        "conversionsB": 20,
                        "conversionRateA": 8.33,
                        "conversionRateB": 15.38,
                        "liftConversionPct": 84.6,
                        "slotsA": 2,
                        "slotsB": 2,
                        "classification": classification,
                        "classificationLabel": "Vencedor B" if classification == "vencedor_B" else "Vencedor A",
                        "classificationReason": f"Diferenca estatisticamente consistente: Hook {classification[-1]} ...",
                        "zScore": z_score,
                        "pValue": p_value,
                        "significant": True,
                    }
                ],
                "byTenant": [],
            },
            "tenantBenchmarks": {
                "minConversions": 5,
                "byTenant": [
                    {
                        "tenantId": tenant_id,
                        "campaigns": 1,
                        "sessions": 250,
                        "engagedSessions": 40,
                        "conversions": 30,
                        "conversionRatePct": 12.0,
                        "engagedRatePct": 16.0,
                        "slots": 2,
                        "abWinRatePct": 1.0,
                        "abCampaignsTotal": 1,
                        "abCampaignsWins": 1,
                        "hooksComFadiga": fatigue_detected,
                        "hooksComFadigaStatus": fatigue_status,
                        "hooksComFadigaZScore": None,
                        "hooksComFadigaPValue": None,
                        "hooksComFadigaReason": fatigue_reason,
                    }
                ],
            },
        },
    }


class HookPromotionCliTest(unittest.TestCase):
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
        os.makedirs(
            render_local.fs_path(os.path.join(cls.root, ".workspace", "tmp")), exist_ok=True
        )
        cls.report_rel = "tools/tests/fixtures/utm-report-promocao.json"
        _write_json(
            os.path.join(cls.root, cls.report_rel),
            _utm_report(MARCA[0], MARCA[1]),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(render_local.fs_path(cls.root), ignore_errors=True)

    def _store(self, name: str) -> str:
        return f".workspace/tmp/{name}.json"

    def _abs(self, rel: str) -> str:
        return os.path.join(self.root, *rel.split("/"))

    def _qa_ok(self) -> dict:
        return {"ok": True, "strict": True, "summary": {"problems": {"errors": 0, "warnings": 0}}}

    # 1 ---------------------------------------------------------------
    def test_01_dry_run_preview_diff_nada_grava(self) -> None:
        store = self._store("promo-dryrun")
        res = approval_cli.cmd_promote_hook(
            root=self.root,
            tenant_id=MARCA[0],
            campaign_slug=MARCA[1],
            utm_report=self.report_rel,
            reviewer="Titular",
            dry_run=True,
            apply_=False,
            approvals_file=store,
        )
        self.assertTrue(res["ok"])
        self.assertFalse(res["applied"])
        self.assertEqual(res["promotedVariant"], "A")
        preview = res["preview"]
        self.assertTrue(preview["dryRun"])
        self.assertIsInstance(preview["diff"], list)
        self.assertTrue(any("promotionHistory" in line for line in preview["diff"]))
        # nada gravado no store
        self.assertFalse(os.path.isfile(render_local.fs_path(self._abs(store))))

    # 2 ---------------------------------------------------------------
    def test_02_apply_grava_promotion_history_atomico(self) -> None:
        store = self._store("promo-apply")
        res = approval_cli.cmd_promote_hook(
            root=self.root,
            tenant_id=MARCA[0],
            campaign_slug=MARCA[1],
            utm_report=self.report_rel,
            reviewer="Titular",
            dry_run=False,
            apply_=True,
            approvals_file=store,
            run_qa=lambda *a, **k: self._qa_ok(),
        )
        self.assertTrue(res["ok"])
        self.assertTrue(res["applied"])
        self.assertEqual(res["promotedVariant"], "A")
        self.assertRegex(res["promotedAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

        doc = _read_json(self._abs(res["approvalsFile"]))
        item = next(
            it
            for it in doc["campanhas"]
            if it["tenantId"] == MARCA[0] and it["slug"] == MARCA[1]
        )
        history = item["promotionHistory"]
        self.assertEqual(len(history), 1)
        entry = history[0]
        self.assertEqual(entry["campaignId"], doc_campaign_id(self.root, MARCA))
        self.assertEqual(entry["tenantId"], MARCA[0])
        self.assertEqual(entry["promotedVariant"], "A")
        self.assertEqual(entry["zScore"], 2.5)
        self.assertEqual(entry["pValue"], 0.01)
        self.assertIn("classificationReason", entry)
        self.assertEqual(entry["fatigueStatus"], "estavel")
        self.assertFalse(entry["fatigueDetected"])
        self.assertEqual(entry["sourceReport"], self.report_rel)
        self.assertRegex(entry["promotedAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(entry["promotedBy"], "Titular")
        # escrita atomica: sem .tmp sobrando
        folder = os.path.dirname(self._abs(res["approvalsFile"]))
        leftovers = [
            n for n in os.listdir(render_local.fs_path(folder)) if n.endswith(".tmp")
        ]
        self.assertEqual(leftovers, [])

    # 3 ---------------------------------------------------------------
    def test_03_isolamento_tenant_divergente_rejeitado(self) -> None:
        # Relatorio cuja linha de comparacao pertence ao tenant 'meu-salao' para a
        # mesma campanha 'camp-saas-demo-marca-salao-001' (tenant diverge, campanha
        # igual) -> isolamento multi-tenant rejeita.
        _write_json(
            os.path.join(self.root, self.report_rel),
            _utm_report(MEU[0], MARCA[1]),
        )
        store = self._store("promo-divergente")
        with self.assertRaises(approval_cli.ApprovalError) as ctx:
            approval_cli.cmd_promote_hook(
                root=self.root,
                tenant_id=MARCA[0],
                campaign_slug=MARCA[1],
                utm_report=self.report_rel,
                reviewer="Titular",
                dry_run=False,
                apply_=True,
                approvals_file=store,
            )
        self.assertEqual(ctx.exception.code, "PROMOTION_TENANT_DIVERGENTE")
        # nada gravado
        self.assertFalse(os.path.isfile(render_local.fs_path(self._abs(store))))

    # 4 ---------------------------------------------------------------
    def test_04_gate_significancia_nao_significativo_rejeitado(self) -> None:
        _write_json(
            os.path.join(self.root, self.report_rel),
            _utm_report(
                MARCA[0],
                MARCA[1],
                classification="empate_tecnico",
                z_score=0.5,
                p_value=0.6,
                fatigue_detected=False,
            ),
        )
        store = self._store("promo-nao-sig")
        with self.assertRaises(approval_cli.ApprovalError) as ctx:
            approval_cli.cmd_promote_hook(
                root=self.root,
                tenant_id=MARCA[0],
                campaign_slug=MARCA[1],
                utm_report=self.report_rel,
                reviewer="Titular",
                dry_run=False,
                apply_=True,
                approvals_file=store,
            )
        self.assertEqual(ctx.exception.code, "PROMOTION_NAO_SIGNIFICATIVO")
        self.assertFalse(os.path.isfile(render_local.fs_path(self._abs(store))))

    # 5 ---------------------------------------------------------------
    def test_05_alerta_fadiga_no_preview(self) -> None:
        _write_json(
            os.path.join(self.root, self.report_rel),
            _utm_report(
                MARCA[0],
                MARCA[1],
                fatigue_detected=True,
                fatigue_status="fadiga_detectada",
                fatigue_reason="CVR caiu da janela inicial para a final",
            ),
        )
        store = self._store("promo-fadiga")
        res = approval_cli.cmd_promote_hook(
            root=self.root,
            tenant_id=MARCA[0],
            campaign_slug=MARCA[1],
            utm_report=self.report_rel,
            reviewer="Titular",
            dry_run=True,
            apply_=False,
            approvals_file=store,
        )
        self.assertTrue(res["ok"])
        preview = res["preview"]
        self.assertTrue(preview["fatigueDetected"])
        self.assertEqual(preview["fatigueStatus"], "fadiga_detectada")
        self.assertIn("CVR caiu", preview["fatigueReason"])

    # 6 ---------------------------------------------------------------
    def test_06_gate_editorial_qa_reprovado_aborta_apply(self) -> None:
        # Forca editorial_qa reprovar escrevendo um schema invalido no calendario
        # (lancaria erro na linte coerencia_hooks_calendario) - nao, mais simples:
        # injetamos um tenant com guardrails proibidos no SRT? O caminho mais
        # direto e usar um calendario-editorial.json invalido para provocar erro.
        # Aqui nao controlamos editorial_qa facilmente; usamos um relatorio sem
        # significancia para forcar PROMOTION_NAO_SIGNIFICATIVO antes do gate de
        # QA, e um segundo teste que force o gate de QA via calendario invalido.
        _write_json(
            os.path.join(self.root, self.report_rel),
            _utm_report(MARCA[0], MARCA[1]),
        )
        # calendario invalido para provocar erro de editorial_qa
        cal_rel = os.path.join("04-legendas", "calendario-editorial.json")
        _write_json(
            os.path.join(self.root, cal_rel),
            {
                "schemaVersion": 1,
                "slots": [
                    {
                        "tenantId": MARCA[0],
                        "slug": MARCA[1],
                        "hookVarianteA": "hook proibido X",
                        "hookVarianteB": "hook proibido X",
                    }
                ],
            },
        )
        store = self._store("promo-qa")
        with self.assertRaises(approval_cli.ApprovalError) as ctx:
            approval_cli.cmd_promote_hook(
                root=self.root,
                tenant_id=MARCA[0],
                campaign_slug=MARCA[1],
                utm_report=self.report_rel,
                reviewer="Titular",
                dry_run=False,
                apply_=True,
                approvals_file=store,
                run_qa=lambda *a, **k: {
                    "ok": False,
                    "strict": True,
                    "summary": {"problems": {"errors": 1, "warnings": 0}},
                },
            )
        self.assertEqual(ctx.exception.code, "PROMOTION_EDITORIAL_QA_REPROVADA")
        self.assertFalse(os.path.isfile(render_local.fs_path(self._abs(store))))


def doc_campaign_id(root: str, campaign: tuple[str, str]) -> str:
    cfg = _read_json(os.path.join(root, "tenants", campaign[0], "campaigns", campaign[1] + ".json"))
    return str(cfg.get("campaignId") or campaign[1])


if __name__ == "__main__":
    unittest.main()
