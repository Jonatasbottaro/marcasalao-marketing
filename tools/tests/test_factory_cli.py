"""Testes automatizados (unittest) para o orquestrador em lote tools/factory_cli.py."""

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

if shutil.which("ffmpeg") is None:
    _ffmpeg_dir = os.path.join(REPO_ROOT, ".workspace", "tools", "ffmpeg")
    if os.path.isdir(_ffmpeg_dir):
        os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

import factory_cli  # noqa: E402
import render_local  # noqa: E402
import srt_validate  # noqa: E402

TEST_TMP_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "test_factory_cli")


class FactoryCliTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        if os.path.isdir(TEST_TMP_ROOT):
            shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)

    def _path(self, rel_path: str) -> str:
        return os.path.join(REPO_ROOT, rel_path.replace("/", os.sep))

    def test_01_list_returns_valid_tenants_and_campaigns(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = factory_cli.main(["list", "--root", REPO_ROOT, "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["ok"])
        self.assertGreaterEqual(payload["totalTenants"], 4)
        self.assertGreaterEqual(payload["totalCampaigns"], 8)

        by_id = {entry["tenantId"]: entry for entry in payload["tenants"]}
        self.assertEqual(by_id["estudio-flow"]["defaultPreset"], "saas-demo")
        self.assertFalse(by_id["estudio-flow"]["allowAudioTrack"])
        self.assertEqual(by_id["marca-salao"]["defaultPreset"], "saas-demo")
        self.assertFalse(by_id["marca-salao"]["allowAudioTrack"])
        self.assertEqual(by_id["meu-salao"]["defaultPreset"], "saas-demo")
        self.assertFalse(by_id["meu-salao"]["allowAudioTrack"])
        self.assertEqual(by_id["multitrack-hub"]["defaultPreset"], "shorts-completo")
        self.assertTrue(by_id["multitrack-hub"]["allowAudioTrack"])

        for tid, expected_slug in (
            ("estudio-flow", "camp-saas-demo-estudio-flow-001"),
            ("marca-salao", "camp-saas-demo-marca-salao-001"),
            ("marca-salao", "camp-saas-demo-ns001-agenda-001"),
            ("meu-salao", "camp-saas-demo-meu-salao-001"),
            ("meu-salao", "camp-saas-demo-meu-salao-002"),
            ("multitrack-hub", "camp-shorts-completo-multitrack-001"),
            ("multitrack-hub", "camp-shorts-rateios-002"),
            ("multitrack-hub", "camp-shorts-stems-workflow-003"),
        ):
            slugs = [c["slug"] for c in by_id[tid]["campaigns"]]
            self.assertIn(expected_slug, slugs)

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "ffmpeg/ffprobe indisponiveis nesta estacao; render binario nao executavel",
    )
    def test_02_render_filtered_by_tenant_and_campaign_writes_report(self) -> None:
        out_deliveries = ".workspace/tmp/test_factory_cli/deliveries"
        report_rel = ".workspace/tmp/test_factory_cli/factory-report.json"
        if os.path.isdir(os.path.join(REPO_ROOT, ".workspace", "tmp", "test_factory_cli")):
            shutil.rmtree(os.path.join(REPO_ROOT, ".workspace", "tmp", "test_factory_cli"), ignore_errors=True)

        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = factory_cli.main([
                "render",
                "--tenant", "meu-salao",
                "--campaign", "camp-saas-demo-meu-salao-001",
                "--deliveries-dir", out_deliveries,
                "--report", report_rel,
                "--root", REPO_ROOT,
                "--json",
            ])
        self.assertEqual(rc, 0)
        report = json.loads(buf.getvalue())
        self.assertTrue(report["ok"])
        self.assertEqual(report["mode"], "filtered")
        self.assertEqual(report["totalTenants"], 1)
        self.assertEqual(report["totalCampaigns"], 1)
        self.assertTrue(os.path.isfile(self._path(report_rel)))

        delivery = report["deliveries"][0]
        self.assertEqual(delivery["tenantId"], "meu-salao")
        self.assertEqual(delivery["preset"], "saas-demo")
        self.assertFalse(delivery["allowAudioTrack"])
        fp = delivery["ffprobe"]
        self.assertEqual((fp["width"], fp["height"], fp["fps"], fp["audioStreams"]), (1080, 1920, 30.0, 0))

        for kind in ("video", "srt", "narration", "storyboard"):
            art_path = self._path(delivery["artifacts"][kind]["path"])
            self.assertTrue(os.path.isfile(art_path), f"artefato ausente: {kind} -> {art_path}")
            self.assertEqual(render_local.sha256_file(art_path), delivery["artifacts"][kind]["sha256"])

        self.assertEqual(
            srt_validate.validate_srt_file(self._path(delivery["artifacts"]["srt"]["path"]), duration=30.0),
            [],
        )

    def test_03_committed_deliveries_and_factory_report_integrity(self) -> None:
        report_abs = self._path("02-reels-shorts/deliveries/factory-report.json")
        self.assertTrue(os.path.isfile(report_abs), "factory-report.json ausente")
        with open(report_abs, "r", encoding="utf-8") as handle:
            report = json.load(handle)

        self.assertTrue(report["ok"])
        self.assertGreaterEqual(report["totalTenants"], 4)
        self.assertGreaterEqual(report["totalCampaigns"], 8)
        self.assertEqual(len(report["deliveries"]), report["totalCampaigns"])

        self.assertTrue(
            {"estudio-flow", "marca-salao", "meu-salao", "multitrack-hub"}.issubset(set(report["tenants"]))
        )

        # Confere politica de audio por tenant e integridade dos artefatos versionados
        for d in report["deliveries"]:
            tid = d["tenantId"]
            slug = d["campaignSlug"]
            label = f"{tid}/{slug}"
            if d["allowAudioTrack"]:
                self.assertEqual(d["ffprobe"]["audioStreams"], 1, label)
                self.assertEqual(d["ffprobe"]["audioCodec"], "aac", label)
            else:
                self.assertEqual(d["ffprobe"]["audioStreams"], 0, label)

            manifest_abs = self._path(d["manifestPath"])
            self.assertTrue(os.path.isfile(manifest_abs), f"{label}: manifest ausente")
            for kind in ("srt", "narration", "storyboard"):
                art = d["artifacts"][kind]
                art_abs = self._path(art["path"])
                self.assertTrue(os.path.isfile(art_abs), f"{label}: {kind} ausente em {art_abs}")
                self.assertEqual(render_local.sha256_file(art_abs), art["sha256"], f"{label}: sha256 {kind}")
                self.assertEqual(os.path.getsize(art_abs), art["bytes"], f"{label}: bytes {kind}")

    def test_04_invalid_tenant_or_campaign_returns_error(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            rc_bad_tenant = factory_cli.main([
                "render", "--tenant", "tenant-inexistente",
                "--deliveries-dir", ".workspace/tmp/test_factory_cli/err",
                "--root", REPO_ROOT,
            ])
        self.assertNotEqual(rc_bad_tenant, 0)

        with contextlib.redirect_stderr(io.StringIO()):
            rc_bad_camp = factory_cli.main([
                "render", "--tenant", "meu-salao", "--campaign", "campanha-inexistente",
                "--deliveries-dir", ".workspace/tmp/test_factory_cli/err",
                "--root", REPO_ROOT,
            ])
        self.assertNotEqual(rc_bad_camp, 0)

        with contextlib.redirect_stderr(io.StringIO()):
            rc_pipeline_sem_escopo = factory_cli.main(["pipeline", "--root", REPO_ROOT])
        self.assertNotEqual(rc_pipeline_sem_escopo, 0)

    def _run_pipeline(self, extra_args: list[str]) -> tuple[int, dict]:
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = factory_cli.main(
                ["pipeline", *extra_args, "--skip-render", "--root", REPO_ROOT, "--json"]
            )
        return rc, json.loads(buf.getvalue())

    def test_05_pipeline_filtered_skip_render_reports_each_stage(self) -> None:
        rc, report = self._run_pipeline([
            "--tenant", "marca-salao",
            "--campaign", "camp-saas-demo-marca-salao-001",
            "--utm-out-dir", ".workspace/tmp/test_factory_cli/utm-filtered",
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(report["ok"])
        self.assertEqual(report["mode"], "filtered")
        self.assertTrue(report["skipRender"])
        self.assertEqual(
            [stage["id"] for stage in report["stages"]],
            ["contratos", "render", "derivados", "cards-estaticos", "pacotes",
             "calendario", "portal", "utm", "editorial-qa", "release-gate"],
        )
        by_id = {stage["id"]: stage for stage in report["stages"]}
        for stage_id in ("contratos", "render", "derivados", "cards-estaticos", "pacotes",
                         "utm", "release-gate"):
            self.assertEqual(by_id[stage_id]["status"], "ok", stage_id)
            self.assertIsInstance(by_id[stage_id]["durationMs"], int, stage_id)
            self.assertGreaterEqual(by_id[stage_id]["durationMs"], 0, stage_id)
        self.assertIn(by_id["editorial-qa"]["status"], ("ok", "skipped"))
        self.assertEqual(by_id["calendario"]["status"], "skipped")
        self.assertEqual(by_id["portal"]["status"], "skipped")

        counts = report["counts"]
        self.assertEqual(counts["tenants"], 1)
        self.assertEqual(counts["campaigns"], 1)
        self.assertEqual(counts["deliveries"], 1)
        self.assertGreaterEqual(counts["staticCards"], 7)
        self.assertGreaterEqual(counts["utmUrls"], 1)
        self.assertEqual(counts["releaseDomains"]["contratos_tenants"], "ok")

    def test_06_pipeline_all_skip_render_consolidates_factory(self) -> None:
        rc, report = self._run_pipeline([
            "--all",
            "--utm-out-dir", ".workspace/tmp/test_factory_cli/utm-all",
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(report["ok"])
        self.assertEqual(report["mode"], "all")
        statuses = {stage["id"]: stage["status"] for stage in report["stages"]}
        self.assertEqual(list(statuses), [
            "contratos", "render", "derivados", "cards-estaticos", "pacotes",
            "calendario", "portal", "utm", "editorial-qa", "release-gate",
        ])
        for stage_id, status in statuses.items():
            if stage_id == "editorial-qa":
                # Modulo paralelo: pode ainda nao estar presente na branch integrada.
                self.assertIn(status, ("ok", "skipped"), stage_id)
            else:
                self.assertEqual(status, "ok", stage_id)

        counts = report["counts"]
        self.assertGreaterEqual(counts["tenants"], 4)
        self.assertGreaterEqual(counts["campaigns"], 8)
        self.assertEqual(counts["deliveries"], counts["campaigns"])
        self.assertEqual(counts["derivatives"], counts["campaigns"])
        self.assertEqual(counts["staticCards"], 7 * counts["campaigns"])
        self.assertEqual(counts["publishPacks"], counts["campaigns"])
        self.assertGreaterEqual(counts["calendarSlots"], counts["campaigns"])
        self.assertEqual(counts["portalCampaigns"], counts["campaigns"])
        self.assertGreaterEqual(counts["utmUrls"], counts["calendarSlots"])
        self.assertEqual(set(counts["releaseDomains"].values()), {"ok"})

    def _write_json(self, rel_path: str, doc: dict) -> None:
        abs_path = self._path(rel_path)
        os.makedirs(render_local.fs_path(os.path.dirname(abs_path)), exist_ok=True)
        with open(render_local.fs_path(abs_path), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(doc, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    def _run_handoff(self, extra_args: list[str]) -> tuple[int, dict]:
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = factory_cli.main(
                ["handoff", *extra_args, "--root", REPO_ROOT, "--json"]
            )
        return rc, json.loads(buf.getvalue())

    def test_07_handoff_json_zero_approved(self) -> None:
        approvals_rel = ".workspace/tmp/test_factory_cli/handoff-vazio.json"
        self._write_json(approvals_rel, {"schemaVersion": 2, "campanhas": []})
        rc, payload = self._run_handoff([
            "--all-approved",
            "--approvals-file", approvals_rel,
            "--output-dir", ".workspace/tmp/test_factory_cli/handoff-zero",
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(payload["ok"])
        self.assertIs(payload["autoPublish"], False)
        self.assertEqual(payload["approvalAudit"]["summary"]["aprovadas"], 0)
        handoff = payload["handoff"]
        self.assertEqual(handoff["bundledSlots"], 0)
        self.assertEqual(handoff["reason"], "NENHUMA_CAMPANHA_APROVADA_PELO_TITULAR")
        self.assertIs(handoff["autoPublish"], False)

    def test_08_handoff_json_with_approved_campaign(self) -> None:
        approvals_rel = ".workspace/tmp/test_factory_cli/handoff-aprovado.json"
        self._write_json(
            approvals_rel,
            {
                "schemaVersion": 2,
                "campanhas": [
                    {
                        "tenantId": "marca-salao",
                        "slug": "camp-saas-demo-ns001-agenda-001",
                        "campaignId": "SAAS-DEMO-NS001-AGENDA-001",
                        "preset": "saas-demo",
                        "decisao": "aprovado",
                        "locucaoExternaConferida": True,
                        "observacoes": "",
                        "hashes": {},
                        "updatedAt": "2026-11-20T12:00:00Z",
                    }
                ],
            },
        )
        with open(
            self._path("04-legendas/calendario-editorial.json"), "r", encoding="utf-8"
        ) as handle:
            calendar = json.load(handle)
        slot_date = next(
            slot["dataSugerida"]
            for slot in calendar["slots"]
            if slot["slug"] == "camp-saas-demo-ns001-agenda-001" and slot["onda"] == 1
        )
        rc, payload = self._run_handoff([
            "--date", slot_date,
            "--approvals-file", approvals_rel,
            "--output-dir", ".workspace/tmp/test_factory_cli/handoff-ok",
        ])
        self.assertEqual(rc, 0, payload)
        self.assertTrue(payload["ok"])
        self.assertIs(payload["autoPublish"], False)
        self.assertEqual(payload["approvalAudit"]["summary"]["aprovadas"], 1)
        handoff = payload["handoff"]
        self.assertGreaterEqual(handoff["bundledSlots"], 1)
        self.assertEqual(handoff["dates"], [slot_date])
        self.assertEqual(handoff["slots"][0]["tenantId"], "marca-salao")
        self.assertTrue(
            os.path.isdir(
                self._path(f".workspace/tmp/test_factory_cli/handoff-ok/{slot_date}")
            )
        )


if __name__ == "__main__":
    unittest.main()
