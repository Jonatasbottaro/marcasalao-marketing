"""Testes do relatorio executivo semanal por tenant (tools/executive_summary.py).

Cobre obrigatoriamente:
  1. Geracao de JSON + Markdown por tenant, com as seis secoes exigidas.
  2. Isolamento estrito entre os 5 tenants reais: nenhum identificador, slug ou
     marca de um tenant aparece no relatorio de outro.
  3. Selo ``autoPublish: false`` no JSON e no Markdown, e natureza somente leitura.
  4. Incorporacao de ``bundleAttribution``, ``promotionHistory`` e fadiga
     (``fatigueDetected`` / ``fadiga_detectada``) com zScore e pValue.
  5. Integracao com ``review_dashboard``: o portal expoe o digest por tenant e
     o caminho/status do relatorio, sem quebrar ``portal-data.json``.
  6. Contencao de saida: relatorios nunca podem cair fora de ``.workspace/``.

Saidas de teste vao para ``<RAIZ>/.workspace/tmp/``; o store de aprovacoes real
nunca e escrito (as fixtures substituem o resolvedor em memoria).
"""

from __future__ import annotations

import contextlib
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

import approval_cli  # noqa: E402
import campaign_calendar  # noqa: E402
import executive_summary as es  # noqa: E402
import review_dashboard  # noqa: E402
import utm_report_importer as utm  # noqa: E402

TMP_PARENT = REPO_ROOT / ".workspace" / "tmp" / "test_executive_summary"
EXPECTED_TENANTS = ("clinica-vital", "estudio-flow", "marca-salao", "meu-salao", "multitrack-hub")
SECTIONS = (
    "## 1. Janela analisada",
    "## 2. Saude editorial e aprovacoes",
    "## 3. Inteligencia A/B e fadiga criativa",
    "## 4. Entregas e atribuicao pos-publicacao (closed-loop)",
    "## 5. Plano de acao priorizado (recomendatorio)",
    "## 6. Fontes",
)


def _registry_by_tenant() -> dict[str, list[dict]]:
    registry = campaign_calendar.discover_campaigns(str(REPO_ROOT))
    grouped: dict[str, list[dict]] = {}
    for row in registry:
        grouped.setdefault(row["tenantId"], []).append(row)
    return grouped


class ExecutiveSummaryBase(unittest.TestCase):
    def setUp(self) -> None:
        TMP_PARENT.mkdir(parents=True, exist_ok=True)
        self._tmp = tempfile.TemporaryDirectory(prefix="exec-", dir=str(TMP_PARENT))
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.out_rel = ".workspace/tmp/test_executive_summary/" + self.tmp.name + "/reports"

    def _generate_all(self, **kwargs) -> dict:
        return es.generate_reports(
            root=str(REPO_ROOT), all_tenants=True, output_dir=self.out_rel, **kwargs
        )

    def _read(self, tenant: str, ext: str) -> str:
        path = REPO_ROOT / self.out_rel / tenant / f"relatorio-executivo-{tenant}.{ext}"
        return path.read_text(encoding="utf-8")


class ExecutiveSummaryGenerationTest(ExecutiveSummaryBase):
    def test_01_all_gera_json_e_markdown_para_os_cinco_tenants(self) -> None:
        result = self._generate_all()
        self.assertTrue(result["ok"])
        self.assertIs(result["autoPublish"], False)
        self.assertEqual(result["totalTenants"], 5)
        self.assertEqual(tuple(result["tenants"]), EXPECTED_TENANTS)
        for report in result["reports"]:
            tid = report["tenantId"]
            self.assertTrue((REPO_ROOT / report["files"]["json"]).is_file(), tid)
            self.assertTrue((REPO_ROOT / report["files"]["markdown"]).is_file(), tid)
            self.assertIn(f".workspace/", report["files"]["json"])

    def test_02_cabecalho_de_governanca_completo(self) -> None:
        self._generate_all()
        grouped = _registry_by_tenant()
        for tid in EXPECTED_TENANTS:
            doc = json.loads(self._read(tid, "json"))
            gov = doc["governance"]
            self.assertEqual(gov["tenantId"], tid)
            self.assertEqual(gov["brandName"], grouped[tid][0]["brandName"])
            self.assertIs(gov["autoPublish"], False)
            self.assertIs(gov["readOnly"], True)
            self.assertRegex(gov["generatedAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertEqual(gov["statusEditorial"], campaign_calendar.STATUS_EDITORIAL)
            self.assertIn("janela", gov)
            self.assertEqual(gov["janela"]["calendarWeeks"], 7)
            self.assertGreater(gov["janela"]["slotsTotalTenant"], 0)

    def test_03_markdown_tem_seis_secoes_e_selo_auto_publish(self) -> None:
        self._generate_all()
        for tid in EXPECTED_TENANTS:
            text = self._read(tid, "md")
            for section in SECTIONS:
                self.assertIn(section, text, f"{tid}: secao ausente {section}")
            self.assertIn("autoPublish: false", text)
            self.assertIn(tid, text)
            self.assertIn("Nenhuma acao abaixo e executada automaticamente", text)

    def test_04_contagem_de_campanhas_por_tenant(self) -> None:
        result = self._generate_all()
        grouped = _registry_by_tenant()
        for report in result["reports"]:
            tid = report["tenantId"]
            self.assertEqual(report["campaigns"], len(grouped[tid]), tid)
            doc = json.loads(self._read(tid, "json"))
            self.assertEqual(doc["editorial"]["totalCampaigns"], len(grouped[tid]))
            self.assertEqual(
                sum(doc["editorial"]["byStatus"].values()), len(grouped[tid]),
                "distribuicao por status deve fechar com o total do tenant",
            )

    def test_05_qa_editorial_limpo_em_todos_os_tenants(self) -> None:
        self._generate_all()
        for tid in EXPECTED_TENANTS:
            qa = json.loads(self._read(tid, "json"))["editorial"]["qa"]
            self.assertEqual(qa["errors"], 0, tid)
            self.assertEqual(qa["warnings"], 0, tid)
            self.assertTrue(qa["ok"], tid)
            self.assertEqual(qa["lenses"], 7)

    def test_06_filtro_de_semana_restringe_a_janela(self) -> None:
        full = es.generate_reports(
            root=str(REPO_ROOT), tenant="marca-salao", output_dir=self.out_rel
        )
        total = full["reports"][0]["summary"]["governance"]["janela"]["slots"]
        week1 = es.generate_reports(
            root=str(REPO_ROOT), tenant="marca-salao", week=1, output_dir=self.out_rel
        )
        janela = week1["reports"][0]["summary"]["governance"]["janela"]
        self.assertEqual(janela["week"], 1)
        self.assertLessEqual(janela["slots"], total)
        self.assertEqual(janela["slotsTotalTenant"], total)
        self.assertIn("| Semana | 1 |", self._read("marca-salao", "md"))

    def test_07_semana_invalida_rejeitada(self) -> None:
        for week in (0, 8, -1):
            with self.assertRaises(es.ExecutiveSummaryError) as ctx:
                es.generate_reports(
                    root=str(REPO_ROOT), tenant="marca-salao", week=week, output_dir=self.out_rel
                )
            self.assertIn("SEMANA_INVALIDA", str(ctx.exception))

    def test_08_tenant_desconhecido_rejeitado(self) -> None:
        with self.assertRaises(es.ExecutiveSummaryError) as ctx:
            es.generate_reports(
                root=str(REPO_ROOT), tenant="tenant-inexistente", output_dir=self.out_rel
            )
        self.assertIn("TENANT_DESCONHECIDO", str(ctx.exception))

    def test_09_escopo_exige_tenant_ou_all(self) -> None:
        with self.assertRaises(es.ExecutiveSummaryError):
            es.generate_reports(root=str(REPO_ROOT), output_dir=self.out_rel)
        with self.assertRaises(es.ExecutiveSummaryError):
            es.generate_reports(
                root=str(REPO_ROOT), tenant="marca-salao", all_tenants=True, output_dir=self.out_rel
            )

    def test_10_saida_fora_do_workspace_rejeitada(self) -> None:
        with self.assertRaises(es.ExecutiveSummaryError) as ctx:
            es.generate_reports(
                root=str(REPO_ROOT), tenant="marca-salao", output_dir="04-legendas/relatorios"
            )
        self.assertIn("SAIDA_FORA_DO_WORKSPACE", str(ctx.exception))
        self.assertFalse((REPO_ROOT / "04-legendas" / "relatorios").exists())

    def test_11_cli_all_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = es.main(["--all", "--json", "--root", str(REPO_ROOT), "--output-dir", self.out_rel])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["totalTenants"], 5)
        self.assertIs(payload["autoPublish"], False)

    def test_12_cli_week_invalida_retorna_dois(self) -> None:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = es.main(["--tenant", "marca-salao", "--week", "9", "--root", str(REPO_ROOT)])
        self.assertEqual(rc, 2)
        self.assertIn("SEMANA_INVALIDA", err.getvalue())


class ExecutiveSummaryIsolationTest(ExecutiveSummaryBase):
    def test_13_nenhum_dado_de_outro_tenant_vaza(self) -> None:
        self._generate_all()
        grouped = _registry_by_tenant()
        for tid in EXPECTED_TENANTS:
            json_text = self._read(tid, "json")
            md_text = self._read(tid, "md")
            doc = json.loads(json_text)
            for other in EXPECTED_TENANTS:
                if other == tid:
                    continue
                self.assertNotIn(other, json_text, f"{tid}: id de {other} no JSON")
                self.assertNotIn(other, md_text, f"{tid}: id de {other} no Markdown")
                for row in grouped[other]:
                    self.assertNotIn(row["slug"], json_text, f"{tid}: slug de {other}")
                    self.assertNotIn(row["slug"], md_text, f"{tid}: slug de {other}")
                    self.assertNotIn(row["brandName"], json_text, f"{tid}: marca de {other}")
            self.assertEqual(doc["governance"]["tenantId"], tid)

    def test_14_slots_e_campanhas_ab_sao_do_proprio_tenant(self) -> None:
        self._generate_all()
        grouped = _registry_by_tenant()
        for tid in EXPECTED_TENANTS:
            doc = json.loads(self._read(tid, "json"))
            own = {row["slug"] for row in grouped[tid]}
            for row in doc["abIntelligence"]["hookTests"]["byCampaign"]:
                self.assertEqual(row["tenantId"], tid)
                self.assertIn(row["campaign"], own)
            for alert in doc["abIntelligence"]["fatigueAlerts"]:
                self.assertIn(alert["slug"], own)
            for entry in doc["abIntelligence"]["promotionHistory"]:
                self.assertIn(entry["slug"], own)
            for item in doc["delivery"]["attribution"]["campaigns"]:
                self.assertIn(item["slug"], own)
            for package in doc["delivery"]["bundles"]:
                self.assertIn(package["slug"], own)
            bench = doc["abIntelligence"]["tenantBenchmarks"]
            if bench:
                self.assertEqual(bench["tenantId"], tid)


class ExecutiveSummaryFixtureTest(ExecutiveSummaryBase):
    """Injeta UTM, atribuicao, fadiga e promotionHistory sem tocar no estado real."""

    def setUp(self) -> None:
        super().setUp()
        self.grouped = _registry_by_tenant()
        self.tid = "multitrack-hub"
        self.other = "marca-salao"
        self.slug = self.grouped[self.tid][0]["slug"]
        self.other_slug = self.grouped[self.other][0]["slug"]

        self.utm_report = {
            "schemaVersion": 1,
            "rankings": {
                "hookComparison": {
                    "byCampaign": [
                        {
                            "tenantId": self.tid, "campaign": self.slug,
                            "classification": "vencedor_A", "zScore": 2.41, "pValue": 0.0159,
                            "sessionsA": 400, "sessionsB": 380,
                        },
                        {
                            "tenantId": self.other, "campaign": self.other_slug,
                            "classification": "vencedor_B", "zScore": -2.9, "pValue": 0.0037,
                        },
                    ]
                },
                "tenantBenchmarks": {
                    "byTenant": [
                        {"tenantId": self.tid, "sessions": 780, "conversions": 39,
                         "conversionRatePct": 5.0, "abWinRatePct": 0.5, "hooksComFadiga": True},
                        {"tenantId": self.other, "sessions": 999, "conversions": 99,
                         "conversionRatePct": 9.91},
                    ]
                },
            },
        }
        self.attribution = {
            "schemaVersion": 1,
            "bundles": [
                {
                    "tenantId": self.tid, "slug": self.slug,
                    "attributionStatus": utm.ATTR_STATUS_RECONCILIADO,
                    "approvalStatus": "APROVADO_PELO_TITULAR",
                    "bundleSha256": "a" * 64,
                    "metrics": {"ctr": 4.2, "conversionRate": 5.0,
                                "observedUpliftPct": 12.5, "winnerSustained": True},
                },
                {
                    "tenantId": self.tid, "slug": self.grouped[self.tid][1]["slug"],
                    "attributionStatus": utm.ATTR_STATUS_AGUARDANDO_METRICAS,
                    "metrics": None, "winnerSustained": None,
                },
                {
                    "tenantId": self.other, "slug": self.other_slug,
                    "attributionStatus": utm.ATTR_STATUS_RECONCILIADO,
                    "metrics": {"ctr": 9.9, "conversionRate": 9.91,
                                "observedUpliftPct": 88.0, "winnerSustained": True},
                },
            ],
        }
        self.store = {
            "schemaVersion": 2,
            "campanhas": [
                {
                    "tenantId": self.tid, "slug": self.slug, "decisao": "aprovado",
                    "locucaoExternaConferida": True,
                    "promotionHistory": [{
                        "schemaVersion": 1, "tenantId": self.tid, "campaignId": "X",
                        "promotedVariant": "A", "zScore": 2.41, "pValue": 0.0159,
                        "fatigueStatus": "fadiga_detectada", "fatigueDetected": True,
                        "promotedAt": "2026-11-20T12:00:00Z", "promotedBy": "titular",
                    }],
                },
                {
                    "tenantId": self.other, "slug": self.other_slug, "decisao": "aprovado",
                    "promotionHistory": [{
                        "promotedVariant": "B", "promotedAt": "2026-11-21T12:00:00Z",
                        "promotedBy": "outro-titular",
                    }],
                },
            ],
        }
        self.store_path = self.tmp / "aprovacoes-titular.json"
        self.store_path.write_text(json.dumps(self.store, ensure_ascii=False), encoding="utf-8")
        self.utm_path = self.tmp / "utm-performance-report.json"
        self.utm_path.write_text(json.dumps(self.utm_report, ensure_ascii=False), encoding="utf-8")
        self.attr_path = self.tmp / "bundle-attribution.json"
        self.attr_path.write_text(json.dumps(self.attribution, ensure_ascii=False), encoding="utf-8")

    def _inputs(self, with_fatigue: bool = True) -> dict:
        real_status = approval_cli.cmd_status
        with mock.patch.object(
            approval_cli, "cmd_status",
            lambda root=".": real_status(root, approvals_file=str(self.store_path)),
        ), mock.patch.object(
            review_dashboard, "approvals_store_path", lambda root: str(self.store_path)
        ):
            inputs = es.collect_inputs(
                str(REPO_ROOT),
                utm_report_path=str(self.utm_path),
                bundle_attribution_path=str(self.attr_path),
            )
        if with_fatigue:
            calendar = json.loads(json.dumps(inputs["calendar"]))
            for slot in calendar["slots"]:
                if slot["tenantId"] == self.tid and slot["slug"] == self.slug:
                    slot["fatigueStatus"] = "fadiga_detectada"
                    slot["fatigueDetected"] = True
                    slot["fatigueZScore"] = 2.13
                    slot["fatiguePValue"] = 0.0331
                    slot["fatigueReason"] = "queda significativa entre ondas"
            inputs["calendar"] = calendar
        return inputs

    def test_15_hook_ab_incorpora_classificacao_z_e_p(self) -> None:
        summary = es.build_executive_summary(str(REPO_ROOT), self.tid, inputs=self._inputs())
        hooks = summary["abIntelligence"]["hookTests"]
        self.assertTrue(summary["abIntelligence"]["hasData"])
        self.assertEqual(hooks["total"], 1)
        self.assertEqual(hooks["byClassification"]["vencedor_A"], 1)
        self.assertEqual(hooks["byClassification"]["vencedor_B"], 0)
        self.assertEqual(hooks["winRatePct"], 100.0)
        row = hooks["byCampaign"][0]
        self.assertEqual(row["zScore"], 2.41)
        self.assertEqual(row["pValue"], 0.0159)

    def test_16_fadiga_detectada_com_zscore_e_pvalue(self) -> None:
        summary = es.build_executive_summary(str(REPO_ROOT), self.tid, inputs=self._inputs())
        alerts = summary["abIntelligence"]["fatigueAlerts"]
        self.assertTrue(alerts)
        for alert in alerts:
            self.assertEqual(alert["slug"], self.slug)
            self.assertEqual(alert["fatigueStatus"], "fadiga_detectada")
            self.assertEqual(alert["zScore"], 2.13)
            self.assertEqual(alert["pValue"], 0.0331)
        categories = {a["category"] for a in summary["actionPlan"]}
        self.assertIn("fadiga-criativa", categories)
        text = es.render_markdown(summary)
        self.assertIn("Alertas de fadiga ativos", text)
        self.assertIn("2.13", text)
        self.assertIn("0.0331", text)

    def test_17_tenant_benchmarks_isolado(self) -> None:
        summary = es.build_executive_summary(str(REPO_ROOT), self.tid, inputs=self._inputs())
        bench = summary["abIntelligence"]["tenantBenchmarks"]
        self.assertEqual(bench["tenantId"], self.tid)
        self.assertEqual(bench["sessions"], 780)
        self.assertEqual(bench["conversionRatePct"], 5.0)

    def test_17b_ab_win_rate_tratado_como_fracao(self) -> None:
        summary = es.build_executive_summary(str(REPO_ROOT), self.tid, inputs=self._inputs())
        win = summary["abIntelligence"]["benchmarkAbWinRate"]
        self.assertEqual(win["fraction"], 0.5)
        self.assertEqual(win["percent"], 50.0)
        text = es.render_markdown(summary)
        self.assertIn("fracao 0..1", text)
        self.assertIn("50.0%", text)

    def test_17c_fadiga_do_benchmark_lida_de_hooks_com_fadiga(self) -> None:
        summary = es.build_executive_summary(str(REPO_ROOT), self.tid, inputs=self._inputs())
        fatigue = summary["abIntelligence"]["benchmarkFatigue"]
        self.assertIs(fatigue["detected"], True)
        self.assertIn("hooksComFadiga", es.render_markdown(summary))

    def test_17d_governanca_expoe_generated_at_e_week_filter(self) -> None:
        summary = es.build_executive_summary(str(REPO_ROOT), self.tid, week=2, inputs=self._inputs())
        gov = summary["governance"]
        self.assertEqual(gov["weekFilter"], 2)
        self.assertRegex(gov["generatedAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertIs(gov["autoPublish"], False)
        self.assertEqual(gov["tenantId"], self.tid)

    def test_17e_qa_rodado_por_tenant_com_filtro_nativo(self) -> None:
        inputs = self._inputs()
        self.assertEqual(set(inputs["qaByTenant"]), set(EXPECTED_TENANTS))
        for tid, qa in inputs["qaByTenant"].items():
            self.assertEqual(qa["tenantFilter"], tid)
            for row in qa["campaigns"]:
                self.assertEqual(row["tenant"], tid)

    def test_18_promotion_history_incorporado(self) -> None:
        summary = es.build_executive_summary(str(REPO_ROOT), self.tid, inputs=self._inputs())
        history = summary["abIntelligence"]["promotionHistory"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["promotedVariant"], "A")
        self.assertEqual(history[0]["promotedBy"], "titular")
        self.assertIs(history[0]["fatigueDetected"], True)
        text = es.render_markdown(summary)
        self.assertIn("Promocoes auditadas", text)
        self.assertIn("titular", text)
        self.assertNotIn("outro-titular", text)

    def test_19_bundle_attribution_closed_loop(self) -> None:
        summary = es.build_executive_summary(str(REPO_ROOT), self.tid, inputs=self._inputs())
        attr = summary["delivery"]["attribution"]
        self.assertEqual(attr["total"], 2)
        self.assertEqual(attr["byStatus"][utm.ATTR_STATUS_RECONCILIADO], 1)
        self.assertEqual(attr["byStatus"][utm.ATTR_STATUS_AGUARDANDO_METRICAS], 1)
        reconciled = next(
            c for c in attr["campaigns"]
            if c["attributionStatus"] == utm.ATTR_STATUS_RECONCILIADO
        )
        self.assertEqual(reconciled["ctr"], 4.2)
        self.assertEqual(reconciled["conversionRate"], 5.0)
        self.assertEqual(reconciled["observedUpliftPct"], 12.5)
        self.assertIs(reconciled["winnerSustained"], True)
        self.assertEqual(reconciled["bundleSha256"], "a" * 64)
        text = es.render_markdown(summary)
        self.assertIn("reconciliado", text)
        self.assertIn("aguardando_metricas", text)
        self.assertIn("12.5%", text)

    def test_20_fixture_de_outro_tenant_nao_vaza(self) -> None:
        inputs = self._inputs()
        summary = es.build_executive_summary(str(REPO_ROOT), self.tid, inputs=inputs)
        text = json.dumps(summary, ensure_ascii=False) + es.render_markdown(summary)
        self.assertNotIn(self.other, text)
        self.assertNotIn(self.other_slug, text)
        self.assertNotIn("outro-titular", text)
        self.assertNotIn("88.0", text)

    def test_21_generate_reports_com_utm_e_attribution_por_flag(self) -> None:
        real_status = approval_cli.cmd_status
        with mock.patch.object(
            approval_cli, "cmd_status",
            lambda root=".": real_status(root, approvals_file=str(self.store_path)),
        ), mock.patch.object(
            review_dashboard, "approvals_store_path", lambda root: str(self.store_path)
        ):
            result = es.generate_reports(
                root=str(REPO_ROOT), tenant=self.tid, output_dir=self.out_rel,
                utm_report_path=str(self.utm_path),
                bundle_attribution_path=str(self.attr_path),
            )
        self.assertTrue(result["ok"])
        doc = json.loads(self._read(self.tid, "json"))
        self.assertEqual(doc["abIntelligence"]["hookTests"]["total"], 1)
        self.assertEqual(doc["delivery"]["attribution"]["total"], 2)
        self.assertEqual(len(doc["abIntelligence"]["promotionHistory"]), 1)
        self.assertIsNotNone(doc["sources"]["utmReport"])
        self.assertIsNotNone(doc["sources"]["bundleAttribution"])

    def test_22_sem_relatorio_utm_declara_sem_dados(self) -> None:
        summary = es.build_executive_summary(str(REPO_ROOT), self.tid)
        ab = summary["abIntelligence"]
        self.assertFalse(ab["hasData"])
        self.assertEqual(ab["hookTests"]["total"], 0)
        self.assertIsNone(ab["hookTests"]["winRatePct"])
        self.assertIn("sem dados", es.render_markdown(summary))
        self.assertIn("inteligencia-ab", {a["category"] for a in summary["actionPlan"]})


class ExecutiveSummaryPortalTest(ExecutiveSummaryBase):
    def test_23_portal_expoe_digest_por_tenant(self) -> None:
        self._generate_all()
        portal_out = ".workspace/tmp/test_executive_summary/" + self.tmp.name + "/portal"
        result = review_dashboard.build_portal(root=str(REPO_ROOT), output_dir=portal_out)
        self.assertTrue(result["ok"])
        data = json.loads((REPO_ROOT / portal_out / "portal-data.json").read_text(encoding="utf-8"))
        self.assertEqual(data["totals"], {"tenants": 5, "campaigns": 14})
        self.assertIs(data["autoPublish"], False)
        digest = data["executiveSummary"]
        self.assertIs(digest["autoPublish"], False)
        self.assertEqual(digest["generatedBy"], "tools/executive_summary.py")
        self.assertEqual(len(digest["byTenant"]), 5)
        for row in digest["byTenant"]:
            self.assertEqual(row["status"], "gerado", row["tenantId"])
            self.assertTrue(row["markdownPath"].endswith(f"relatorio-executivo-{row['tenantId']}.md"))
            self.assertIsNotNone(row["generatedAt"])
            self.assertTrue(row["qaOk"])
            self.assertGreaterEqual(row["actions"], 1)

    def test_24_portal_marca_ausente_quando_relatorio_nao_existe(self) -> None:
        fake_ws = self.tmp / "workspace"
        (fake_ws / "tmp").mkdir(parents=True)
        portal_out = ".workspace/tmp/test_executive_summary/" + self.tmp.name + "/portal2"
        with mock.patch.object(review_dashboard, "resolve_workspace_dir", lambda root: str(fake_ws)):
            review_dashboard.build_portal(root=str(REPO_ROOT), output_dir=portal_out)
        data = json.loads((REPO_ROOT / portal_out / "portal-data.json").read_text(encoding="utf-8"))
        digest = data["executiveSummary"]
        self.assertEqual(len(digest["byTenant"]), 5)
        for row in digest["byTenant"]:
            self.assertEqual(row["status"], "ausente", row["tenantId"])
            self.assertIsNone(row["generatedAt"])
            self.assertIsNone(row["qaOk"])
            self.assertGreaterEqual(row["campaigns"], 1)

    def test_25_index_html_contem_painel_executivo(self) -> None:
        self._generate_all()
        portal_out = ".workspace/tmp/test_executive_summary/" + self.tmp.name + "/portal3"
        review_dashboard.build_portal(root=str(REPO_ROOT), output_dir=portal_out)
        html = (REPO_ROOT / portal_out / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="resumo-executivo"', html)
        self.assertIn('id="tabela-executiva"', html)
        self.assertIn("renderResumoExecutivo", html)
        self.assertIn("executiveSummary", html)
        self.assertNotIn("__PORTAL_DATA__", html, "placeholder deve ser substituido pelo JSON")

    def test_26_portal_digest_nao_mistura_tenants(self) -> None:
        self._generate_all()
        portal_out = ".workspace/tmp/test_executive_summary/" + self.tmp.name + "/portal4"
        review_dashboard.build_portal(root=str(REPO_ROOT), output_dir=portal_out)
        data = json.loads((REPO_ROOT / portal_out / "portal-data.json").read_text(encoding="utf-8"))
        grouped = _registry_by_tenant()
        for row in data["executiveSummary"]["byTenant"]:
            tid = row["tenantId"]
            self.assertEqual(row["campaigns"], len(grouped[tid]))
            self.assertIn(f"/{tid}/", row["markdownPath"])
            for other in EXPECTED_TENANTS:
                if other != tid:
                    self.assertNotIn(other, row["markdownPath"])


_QA_PATCH = None


def setUpModule() -> None:
    """Memoiza o QA editorial do acervo real, que e somente leitura e invariante.

    ``collect_inputs`` roda ``run_editorial_qa`` uma vez por tenant; sem cache,
    cada teste que gera relatorios repete as mesmas 5 auditorias identicas. O
    cache guarda o resultado REAL (nao um stub), portanto as assercoes sobre
    lentes, ``tenantFilter`` e contagens continuam verificando o acervo verdadeiro.
    """
    global _QA_PATCH
    import editorial_qa

    real = editorial_qa.run_editorial_qa
    cache: dict = {}

    def cached(root=".", strict=False, tenant=None):
        key = (os.path.realpath(str(root)), bool(strict), tenant)
        if key not in cache:
            cache[key] = real(root, strict=strict, tenant=tenant)
        return cache[key]

    _QA_PATCH = mock.patch.object(editorial_qa, "run_editorial_qa", cached)
    _QA_PATCH.start()


def tearDownModule() -> None:
    if _QA_PATCH is not None:
        _QA_PATCH.stop()
    shutil.rmtree(TMP_PARENT, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()