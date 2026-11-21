"""Testes automatizados (unittest) para tools/utm_report_importer.py."""

from __future__ import annotations

import contextlib
import csv
import io
import json
import os
import shutil
import sys
import unittest
from pathlib import Path

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import utm_report_importer  # noqa: E402

TEST_TMP_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "test_utm_report_importer")

CALENDAR_SLOTS = [
    {
        "slotId": "slot-001",
        "onda": 1,
        "semana": 1,
        "dataSugerida": "2026-11-23",
        "tenantId": "marca-salao",
        "brandName": "Marca Salão",
        "slug": "camp-marca",
        "canal": "youtube",
        "formatoVideo": "9:16",
        "hookVarianteA": "Hook A Marca Salão",
        "hookVarianteB": "Hook B Marca Salão",
        "utmParams": {
            "utm_source": "youtube",
            "utm_medium": "shorts",
            "utm_campaign": "camp-marca",
            "utm_content": "marca-salao",
        },
    },
    {
        "slotId": "slot-002",
        "onda": 1,
        "semana": 1,
        "dataSugerida": "2026-11-24",
        "tenantId": "marca-salao",
        "brandName": "Marca Salão",
        "slug": "camp-marca",
        "canal": "instagram",
        "formatoVideo": "9:16",
        "hookVarianteA": "Hook A Marca Salão",
        "hookVarianteB": "Hook B Marca Salão",
        "utmParams": {
            "utm_source": "instagram",
            "utm_medium": "reels",
            "utm_campaign": "camp-marca",
            "utm_content": "marca-salao",
        },
    },
    {
        "slotId": "slot-003",
        "onda": 2,
        "semana": 3,
        "dataSugerida": "2026-12-07",
        "tenantId": "marca-salao",
        "brandName": "Marca Salão",
        "slug": "camp-marca",
        "canal": "instagram",
        "formatoVideo": "1:1",
        "hookVarianteA": "Hook A Marca Salão",
        "hookVarianteB": "Hook B Marca Salão",
        "utmParams": {
            "utm_source": "instagram",
            "utm_medium": "feed",
            "utm_campaign": "camp-marca",
            "utm_content": "repurpose-1x1",
        },
    },
    {
        "slotId": "slot-004",
        "onda": 2,
        "semana": 3,
        "dataSugerida": "2026-12-08",
        "tenantId": "multitrack-hub",
        "brandName": "Multitrack Hub",
        "slug": "camp-multi",
        "canal": "youtube",
        "formatoVideo": "16:9",
        "hookVarianteA": "Hook A Multitrack",
        "hookVarianteB": "Hook B Multitrack",
        "utmParams": {
            "utm_source": "youtube",
            "utm_medium": "video",
            "utm_campaign": "camp-multi",
            "utm_content": "repurpose-16x9",
        },
    },
]

GA4_HEADER = [
    "Session source",
    "Session medium",
    "Session campaign",
    "Session manual ad content",
    "Sessions",
    "Engaged sessions",
    "Conversions",
]
GA4_ROWS = [
    ["youtube", "shorts", "camp-marca", "marca-salao", "1000", "600", "50"],
    ["instagram", "reels", "camp-marca", "marca-salao", "400", "200", "20"],
    ["instagram", "feed", "camp-marca", "repurpose-1x1", "200", "120", "30"],
    ["youtube", "video", "camp-multi", "repurpose-16x9", "300", "150", "40"],
    ["tiktok", "bio", "camp-fantasma", "ghost", "10", "2", "0"],
]


class UtmReportImporterTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        if os.path.isdir(TEST_TMP_ROOT):
            shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)

    # ------------------------------------------------------------------
    # fixtures
    # ------------------------------------------------------------------
    def _root(self, name: str) -> Path:
        root = Path(TEST_TMP_ROOT) / name
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _write_json(self, root: Path, rel_path: str, payload: dict) -> Path:
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target

    def _write_csv(self, root: Path, rel_path: str, header: list[str], rows: list[list[str]]) -> Path:
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)
        return target

    def _project(self, name: str) -> Path:
        root = self._root(name)
        self._write_json(
            root,
            "04-legendas/calendario-editorial.json",
            {"schemaVersion": 2, "autoPublish": False, "slots": CALENDAR_SLOTS},
        )
        return root

    def _ga4_project(self, name: str, header: list[str] | None = None,
                     rows: list[list[str]] | None = None) -> Path:
        root = self._project(name)
        self._write_csv(root, "metrics.csv", header or GA4_HEADER, rows or GA4_ROWS)
        return root

    def _run_main(self, args: list[str]) -> tuple[int, str]:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = utm_report_importer.main(args)
        return rc, buffer.getvalue()

    # ------------------------------------------------------------------
    # ingestao por provedor
    # ------------------------------------------------------------------
    def test_01_ga4_ingestion_matches_calendar_and_writes_reports(self) -> None:
        root = self._ga4_project("ga4")
        report = utm_report_importer.analyze_performance(
            root=str(root), metrics_csv="metrics.csv", out_dir="out"
        )
        self.assertEqual(report["provider"], "ga4")
        totals = report["totals"]
        self.assertEqual(totals["rows"], 5)
        self.assertEqual(totals["matchedRows"], 4)
        self.assertEqual(totals["unmatchedRows"], 1)
        self.assertEqual(totals["coveragePct"], 80.0)
        self.assertEqual(totals["sessions"], 1900)
        self.assertEqual(totals["conversions"], 140)
        self.assertEqual(totals["slotsMatched"], 4)
        self.assertEqual(totals["slotsInCalendar"], 4)
        for key in ("json", "markdown"):
            self.assertTrue((root / report["reports"][key]).is_file(), key)

    def test_02_plausible_ingestion(self) -> None:
        root = self._project("plausible")
        self._write_csv(
            root,
            "plausible.csv",
            ["utm_source", "utm_medium", "utm_campaign", "utm_content", "visitors", "conversions"],
            [
                ["youtube", "shorts", "camp-marca", "marca-salao", "500", "25"],
                ["instagram", "reels", "camp-marca", "marca-salao", "300", "15"],
            ],
        )
        report = utm_report_importer.analyze_performance(
            root=str(root), metrics_csv="plausible.csv", out_dir="out"
        )
        self.assertEqual(report["provider"], "plausible")
        self.assertEqual(report["totals"]["sessions"], 800)
        self.assertEqual(report["totals"]["conversions"], 40)
        self.assertEqual(report["totals"]["conversionRatePct"], 5.0)

    def test_03_umami_ingestion(self) -> None:
        root = self._project("umami")
        self._write_csv(
            root,
            "umami.csv",
            ["source", "medium", "campaign", "content", "views", "events"],
            [
                ["instagram", "feed", "camp-marca", "repurpose-1x1", "210", "21"],
                ["youtube", "video", "camp-multi", "repurpose-16x9", "90", "9"],
            ],
        )
        report = utm_report_importer.analyze_performance(
            root=str(root), metrics_csv="umami.csv", out_dir="out"
        )
        self.assertEqual(report["provider"], "umami")
        self.assertEqual(report["totals"]["sessions"], 300)
        self.assertEqual(report["totals"]["conversions"], 30)
        self.assertEqual(report["totals"]["matchedRows"], 2)

    def test_04_auto_detection_identifies_each_provider(self) -> None:
        self.assertEqual(
            utm_report_importer.detect_provider(GA4_HEADER),
            "ga4",
        )
        self.assertEqual(
            utm_report_importer.detect_provider(
                ["utm_source", "utm_medium", "utm_campaign", "utm_content", "visitors", "conversions"]
            ),
            "plausible",
        )
        self.assertEqual(
            utm_report_importer.detect_provider(
                ["source", "medium", "campaign", "content", "views", "events"]
            ),
            "umami",
        )
        with self.assertRaises(utm_report_importer.UtmReportError):
            utm_report_importer.detect_provider(["foo", "bar"])

    def test_05_explicit_provider_mismatch_is_rejected(self) -> None:
        root = self._ga4_project("mismatch")
        rc, out = self._run_main([
            "--root", str(root), "--metrics-csv", "metrics.csv",
            "--provider", "plausible", "--out-dir", "out", "--json",
        ])
        self.assertEqual(rc, 2)
        payload = json.loads(out)
        self.assertFalse(payload["ok"])
        self.assertIn("COLUNAS_OBRIGATORIAS_AUSENTES", payload["error"])

    # ------------------------------------------------------------------
    # rankings
    # ------------------------------------------------------------------
    def test_06_ranking_by_channel_and_wave(self) -> None:
        root = self._ga4_project("ranking")
        report = utm_report_importer.analyze_performance(
            root=str(root), metrics_csv="metrics.csv", out_dir="out"
        )
        channels = report["rankings"]["byChannel"]
        self.assertEqual([group["channel"] for group in channels], ["youtube", "instagram"])
        self.assertEqual(channels[0]["sessions"], 1300)
        self.assertEqual(channels[0]["conversions"], 90)
        self.assertEqual(channels[0]["conversionRatePct"], 6.92)

        waves = report["rankings"]["byWave"]
        self.assertEqual(
            [group["label"] for group in waves],
            ["Onda 1 9:16", "Onda 2 1:1/16:9"],
        )
        by_label = {group["label"]: group for group in waves}
        self.assertEqual(by_label["Onda 1 9:16"]["sessions"], 1400)
        self.assertEqual(by_label["Onda 2 1:1/16:9"]["conversions"], 70)
        self.assertEqual(by_label["Onda 2 1:1/16:9"]["conversionRatePct"], 14.0)

    def test_07_ranking_by_tenant(self) -> None:
        root = self._ga4_project("tenant-ranking")
        report = utm_report_importer.analyze_performance(
            root=str(root), metrics_csv="metrics.csv", out_dir="out"
        )
        by_tenant = {group["tenantId"]: group for group in report["rankings"]["byTenant"]}
        self.assertEqual(by_tenant["marca-salao"]["sessions"], 1600)
        self.assertEqual(by_tenant["multitrack-hub"]["sessions"], 300)
        self.assertEqual(report["rankings"]["byTenant"][0]["tenantId"], "marca-salao")

    # ------------------------------------------------------------------
    # hooks
    # ------------------------------------------------------------------
    def test_08_hook_a_vs_b_from_csv_column(self) -> None:
        root = self._project("hooks-csv")
        header = GA4_HEADER + ["hook_variant_used"]
        rows = [
            ["youtube", "shorts", "camp-marca", "marca-salao", "1000", "600", "50", "A"],
            ["instagram", "reels", "camp-marca", "marca-salao", "400", "200", "20", "B"],
            ["instagram", "feed", "camp-marca", "repurpose-1x1", "200", "120", "30", "B"],
            ["youtube", "video", "camp-multi", "repurpose-16x9", "300", "150", "40", "A"],
        ]
        self._write_csv(root, "metrics.csv", header, rows)
        report = utm_report_importer.analyze_performance(
            root=str(root), metrics_csv="metrics.csv", out_dir="out"
        )
        hooks = {group["hook"]: group for group in report["rankings"]["byHook"]}
        self.assertEqual(set(hooks), {"A", "B"})
        self.assertEqual(hooks["A"]["sessions"], 1300)
        self.assertEqual(hooks["A"]["conversions"], 90)
        self.assertEqual(hooks["B"]["sessions"], 600)
        self.assertEqual(hooks["A"]["label"], "Hook A")

    def test_09_hook_log_overrides_csv_and_supports_campaign_content_key(self) -> None:
        root = self._project("hooks-log")
        header = GA4_HEADER + ["hook_variant_used"]
        rows = [
            ["youtube", "shorts", "camp-marca", "marca-salao", "1000", "600", "50", "A"],
            ["instagram", "feed", "camp-marca", "repurpose-1x1", "200", "120", "30", "A"],
        ]
        self._write_csv(root, "metrics.csv", header, rows)
        self._write_json(
            root,
            "hooks.json",
            {"hooks": [
                {"utm_campaign": "camp-marca", "utm_content": "repurpose-1x1", "hook_variant": "B"},
            ]},
        )
        report = utm_report_importer.analyze_performance(
            root=str(root), metrics_csv="metrics.csv", hook_log="hooks.json", out_dir="out"
        )
        hooks = {group["hook"]: group for group in report["rankings"]["byHook"]}
        self.assertEqual(hooks["A"]["sessions"], 1000)
        self.assertEqual(hooks["B"]["sessions"], 200)
        self.assertEqual(report["hookLogPath"], "hooks.json")

    def test_10_hook_log_by_slot_id(self) -> None:
        root = self._project("hooks-slot")
        self._write_csv(root, "metrics.csv", GA4_HEADER, GA4_ROWS[:2])
        self._write_json(root, "hooks.json", {"slot-002": "B"})
        report = utm_report_importer.analyze_performance(
            root=str(root), metrics_csv="metrics.csv", hook_log="hooks.json", out_dir="out"
        )
        slots = {slot["slotId"]: slot for slot in report["slots"]}
        self.assertEqual(slots["slot-002"]["hookVariant"], "B")
        self.assertEqual(slots["slot-001"]["hookVariant"], "")

    # ------------------------------------------------------------------
    # nao atribuido / fallback / template / CLI
    # ------------------------------------------------------------------
    def test_11_unmatched_rows_are_reported_without_failing(self) -> None:
        root = self._ga4_project("unmatched")
        rc, out = self._run_main([
            "--root", str(root), "--metrics-csv", "metrics.csv", "--out-dir", "out", "--json",
        ])
        self.assertEqual(rc, 0)
        report = json.loads(out)
        self.assertTrue(report["ok"])
        self.assertEqual(report["totals"]["unmatchedRows"], 1)
        self.assertEqual(report["unmatchedRows"][0]["campaign"], "camp-fantasma")
        self.assertEqual(report["unmatchedRows"][0]["reason"], "UTM_NOT_IN_CALENDAR")

    def test_12_matrix_fallback_when_calendar_is_absent(self) -> None:
        root = self._root("matrix-fallback")
        self._write_csv(
            root,
            "04-legendas/matriz-utm-consolidada.csv",
            ["slot_id", "onda", "semana", "data_sugerida", "tenant_id", "brand_name", "slug",
             "canal", "formato_video", "utm_source", "utm_medium", "utm_campaign", "utm_content"],
            [["slot-001", "1", "1", "2026-11-23", "marca-salao", "Marca Salão", "camp-marca",
              "youtube", "9:16", "youtube", "shorts", "camp-marca", "marca-salao"]],
        )
        self._write_csv(
            root,
            "metrics.csv",
            ["utm_source", "utm_medium", "utm_campaign", "utm_content", "visitors", "conversions"],
            [["youtube", "shorts", "camp-marca", "marca-salao", "100", "10"]],
        )
        report = utm_report_importer.analyze_performance(
            root=str(root), metrics_csv="metrics.csv", out_dir="out"
        )
        self.assertEqual(report["calendarSource"], "matriz")
        self.assertEqual(report["totals"]["matchedRows"], 1)
        self.assertEqual(report["totals"]["sessions"], 100)

    def test_13_generate_template_exports_fillable_matrix(self) -> None:
        out_rel = ".workspace/tmp/test_utm_report_importer/template/metrics-template.csv"
        rc, out = self._run_main([
            "--root", REPO_ROOT, "--generate-template", out_rel, "--json",
        ])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["templatePath"], out_rel)
        for column in ("sessions", "engaged_sessions", "conversions", "hook_variant_used"):
            self.assertIn(column, payload["columns"])

        template = Path(REPO_ROOT) / out_rel
        with template.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        matrix = Path(REPO_ROOT) / "04-legendas/matriz-utm-consolidada.csv"
        with matrix.open("r", encoding="utf-8", newline="") as handle:
            matrix_rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), len(matrix_rows))
        self.assertGreaterEqual(len(rows), 40)
        self.assertEqual(rows[0]["slot_id"], "slot-001")
        self.assertEqual(rows[0]["sessions"], "")

    def test_14_out_dir_outside_root_is_rejected(self) -> None:
        root = self._ga4_project("containment")
        rc, out = self._run_main([
            "--root", str(root), "--metrics-csv", "metrics.csv",
            "--out-dir", "../fora-da-raiz", "--json",
        ])
        self.assertEqual(rc, 2)
        self.assertIn("PATH_OUTSIDE_ROOT", json.loads(out)["error"])

    def test_15_cli_json_outputs_report_and_files(self) -> None:
        root = self._ga4_project("cli")
        rc, out = self._run_main([
            "--root", str(root), "--metrics-csv", "metrics.csv",
            "--provider", "auto", "--out-dir", "reports", "--json",
        ])
        self.assertEqual(rc, 0)
        report = json.loads(out)
        self.assertEqual(report["schemaVersion"], 1)
        self.assertTrue(report["ok"])
        self.assertFalse(report["financialSimulation"])
        self.assertEqual(report["reports"]["json"], "reports/utm-performance-report.json")
        self.assertTrue((root / report["reports"]["json"]).is_file())
        self.assertTrue((root / report["reports"]["markdown"]).is_file())
        markdown = (root / report["reports"]["markdown"]).read_text(encoding="utf-8")
        self.assertIn("Relatorio executivo de performance UTM", markdown)
        self.assertIn("nao simulada", markdown)

    def test_16_cli_human_output_and_missing_metrics_error(self) -> None:
        root = self._ga4_project("cli-human")
        rc, out = self._run_main([
            "--root", str(root), "--metrics-csv", "metrics.csv", "--out-dir", "out",
        ])
        self.assertEqual(rc, 0)
        self.assertIn("Relatorio UTM (ga4)", out)

        rc_missing, out_missing = self._run_main(["--root", str(root), "--json"])
        self.assertEqual(rc_missing, 2)
        self.assertIn("USO_INVALIDO", json.loads(out_missing)["error"])

    # ------------------------------------------------------------------
    # comparativo A/B: classificacao, limiar, empate e integracao
    # ------------------------------------------------------------------
    def _hook_project(self, name: str, rows: list[list[str]], header: list[str] | None = None) -> Path:
        root = self._project(name)
        full_header = header or (GA4_HEADER + ["hook_variant_used"])
        self._write_csv(root, "metrics.csv", full_header, rows)
        return root

    def test_17_hook_comparison_classifies_winner(self) -> None:
        root = self._hook_project("cmp-winner", [
            ["youtube", "shorts", "camp-marca", "marca-salao", "1000", "600", "50", "A"],
            ["instagram", "reels", "camp-marca", "marca-salao", "500", "250", "40", "B"],
        ])
        report = utm_report_importer.analyze_performance(
            root=str(root), metrics_csv="metrics.csv", out_dir="out"
        )
        comparison = report["rankings"]["hookComparison"]
        self.assertEqual(comparison["minSessions"], 100)
        by_campaign = comparison["byCampaign"]
        self.assertEqual(len(by_campaign), 1)
        row = by_campaign[0]
        self.assertEqual(row["tenantId"], "marca-salao")
        self.assertEqual(row["campaign"], "camp-marca")
        self.assertEqual(row["sessionsA"], 1000)
        self.assertEqual(row["sessionsB"], 500)
        self.assertEqual(row["sessionsTotal"], 1500)
        self.assertEqual(row["conversionRateA"], 5.0)
        self.assertEqual(row["conversionRateB"], 8.0)
        self.assertEqual(row["classification"], "vencedor_B")
        self.assertEqual(row["liftConversionPct"], 60.0)
        self.assertEqual(row["classificationLabel"], "vencedor B")
        # agregado por tenant acompanha a classificacao
        tenant_row = next(
            g for g in comparison["byTenant"] if g["tenantId"] == "marca-salao"
        )
        self.assertEqual(tenant_row["classification"], "vencedor_B")

    def test_18_hook_comparison_insufficient_sample(self) -> None:
        root = self._hook_project("cmp-insuf", [
            ["youtube", "shorts", "camp-marca", "marca-salao", "40", "20", "3", "A"],
            ["instagram", "reels", "camp-marca", "marca-salao", "30", "15", "4", "B"],
        ])
        report = utm_report_importer.analyze_performance(
            root=str(root), metrics_csv="metrics.csv", out_dir="out"
        )
        row = report["rankings"]["hookComparison"]["byCampaign"][0]
        self.assertEqual(row["sessionsTotal"], 70)
        self.assertEqual(row["classification"], "amostra_insuficiente")
        self.assertEqual(row["classificationLabel"], "amostra insuficiente")

    def test_19_hook_comparison_min_sessions_threshold_configurable(self) -> None:
        root = self._hook_project("cmp-threshold", [
            ["youtube", "shorts", "camp-marca", "marca-salao", "60", "30", "3", "A"],
            ["instagram", "reels", "camp-marca", "marca-salao", "60", "30", "6", "B"],
        ])
        report = utm_report_importer.analyze_performance(
            root=str(root), metrics_csv="metrics.csv", out_dir="out", min_sessions=50
        )
        row = report["rankings"]["hookComparison"]["byCampaign"][0]
        self.assertEqual(report["rankings"]["hookComparison"]["minSessions"], 50)
        self.assertEqual(row["sessionsTotal"], 120)
        self.assertEqual(row["classification"], "vencedor_B")

        rc, out = self._run_main([
            "--root", str(root), "--metrics-csv", "metrics.csv",
            "--out-dir", "out", "--min-hook-sessions", "200", "--json",
        ])
        self.assertEqual(rc, 0)
        row_cli = json.loads(out)["rankings"]["hookComparison"]["byCampaign"][0]
        self.assertEqual(row_cli["classification"], "amostra_insuficiente")

    def test_20_hook_comparison_technical_tie(self) -> None:
        root = self._hook_project("cmp-empate", [
            ["youtube", "shorts", "camp-marca", "marca-salao", "500", "300", "25", "A"],
            ["instagram", "reels", "camp-marca", "marca-salao", "500", "300", "25", "B"],
        ])
        report = utm_report_importer.analyze_performance(
            root=str(root), metrics_csv="metrics.csv", out_dir="out"
        )
        row = report["rankings"]["hookComparison"]["byCampaign"][0]
        self.assertEqual(row["sessionsTotal"], 1000)
        self.assertEqual(row["conversionRateA"], 5.0)
        self.assertEqual(row["conversionRateB"], 5.0)
        self.assertEqual(row["classification"], "empate_tecnico")
        self.assertEqual(row["liftConversionPct"], 0.0)

    def test_21_hook_comparison_absent_without_variant(self) -> None:
        root = self._ga4_project("cmp-absent")
        report = utm_report_importer.analyze_performance(
            root=str(root), metrics_csv="metrics.csv", out_dir="out"
        )
        comparison = report["rankings"]["hookComparison"]
        self.assertEqual(comparison["byCampaign"], [])
        self.assertEqual(comparison["byTenant"], [])
        markdown = (root / report["reports"]["markdown"]).read_text(encoding="utf-8")
        self.assertIn("Comparativo de hooks A x B", markdown)

    def test_22_utm_report_feeds_campaign_calendar_recommendations(self) -> None:
        import campaign_calendar

        root = self._hook_project("cmp-calendar", [
            ["youtube", "shorts", "camp-marca", "marca-salao", "1000", "600", "50", "A"],
            ["instagram", "reels", "camp-marca", "marca-salao", "500", "250", "40", "B"],
        ])
        report = utm_report_importer.analyze_performance(
            root=str(root), metrics_csv="metrics.csv", out_dir="out"
        )
        report_rel = report["reports"]["json"]

        calendar = campaign_calendar.build_editorial_calendar(
            "2026-11-23", weeks=7, root=REPO_ROOT, utm_report=None
        )
        self.assertTrue(all(s["hookRecomendado"] == "testar_ab" for s in calendar["slots"]))
        self.assertIsNone(calendar["utmReport"])

        # copia o relatorio para dentro da raiz real do calendario
        target_rel = ".workspace/tmp/test_utm_report_importer/utm-report.json"
        target = Path(REPO_ROOT) / target_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            (root / report_rel).read_text(encoding="utf-8"), encoding="utf-8"
        )
        calendar = campaign_calendar.build_editorial_calendar(
            "2026-11-23", weeks=7, root=REPO_ROOT, utm_report=target_rel
        )
        self.assertIsNotNone(calendar["utmReport"])
        recommended = {s["hookRecomendado"] for s in calendar["slots"]}
        self.assertTrue(recommended.issubset({"A", "B", "testar_ab"}))
        for slot in calendar["slots"]:
            self.assertIn(
                slot["hookRecomendado"], ("A", "B", "testar_ab")
            )
            self.assertTrue(slot["hookRecomendadoJustificativa"])

    def test_23_campaign_calendar_rejects_utm_report_outside_root(self) -> None:
        import campaign_calendar

        with self.assertRaises(campaign_calendar.CampaignCalendarError) as ctx:
            campaign_calendar.build_editorial_calendar(
                "2026-11-23", weeks=7, root=REPO_ROOT, utm_report="../fora.json"
            )
        self.assertIn("UTM_REPORT_FORA_DA_RAIZ", str(ctx.exception))

    def test_24_campaign_calendar_rejects_malformed_utm_report(self) -> None:
        import campaign_calendar

        target_rel = ".workspace/tmp/test_utm_report_importer/malformed.json"
        target = Path(REPO_ROOT) / target_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"rankings": {}}), encoding="utf-8")
        with self.assertRaises(campaign_calendar.CampaignCalendarError) as ctx:
            campaign_calendar.build_editorial_calendar(
                "2026-11-23", weeks=7, root=REPO_ROOT, utm_report=target_rel
            )
        self.assertIn("UTM_REPORT_SEM_COMPARATIVO", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()