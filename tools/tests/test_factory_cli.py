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

    def test_01_list_returns_three_valid_tenants_and_campaigns(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = factory_cli.main(["list", "--root", REPO_ROOT, "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["totalTenants"], 3)
        self.assertGreaterEqual(payload["totalCampaigns"], 3)

        by_id = {entry["tenantId"]: entry for entry in payload["tenants"]}
        self.assertEqual(by_id["marca-salao"]["defaultPreset"], "saas-demo")
        self.assertFalse(by_id["marca-salao"]["allowAudioTrack"])
        self.assertEqual(by_id["meu-salao"]["defaultPreset"], "saas-demo")
        self.assertFalse(by_id["meu-salao"]["allowAudioTrack"])
        self.assertEqual(by_id["multitrack-hub"]["defaultPreset"], "shorts-completo")
        self.assertTrue(by_id["multitrack-hub"]["allowAudioTrack"])

        for tid, expected_slug in (
            ("marca-salao", "camp-saas-demo-marca-salao-001"),
            ("meu-salao", "camp-saas-demo-meu-salao-001"),
            ("multitrack-hub", "camp-shorts-completo-multitrack-001"),
        ):
            slugs = [c["slug"] for c in by_id[tid]["campaigns"]]
            self.assertIn(expected_slug, slugs)

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
        self.assertEqual(report["totalTenants"], 3)
        self.assertEqual(report["totalCampaigns"], 3)

        by_tenant = {d["tenantId"]: d for d in report["deliveries"]}
        self.assertEqual(set(by_tenant.keys()), {"marca-salao", "meu-salao", "multitrack-hub"})

        # Confere politica de audio por tenant nas medicoes do relatorio
        self.assertEqual(by_tenant["marca-salao"]["ffprobe"]["audioStreams"], 0)
        self.assertEqual(by_tenant["meu-salao"]["ffprobe"]["audioStreams"], 0)
        self.assertEqual(by_tenant["multitrack-hub"]["ffprobe"]["audioStreams"], 1)
        self.assertEqual(by_tenant["multitrack-hub"]["ffprobe"]["audioCodec"], "aac")

        # Confere todos os artefatos versionados no Git (SRT, TXT, storyboard, manifest)
        for tid, d in by_tenant.items():
            manifest_abs = self._path(d["manifestPath"])
            self.assertTrue(os.path.isfile(manifest_abs), f"{tid}: manifest ausente")
            for kind in ("srt", "narration", "storyboard"):
                art = d["artifacts"][kind]
                art_abs = self._path(art["path"])
                self.assertTrue(os.path.isfile(art_abs), f"{tid}: {kind} ausente em {art_abs}")
                self.assertEqual(render_local.sha256_file(art_abs), art["sha256"], f"{tid}: sha256 {kind}")
                self.assertEqual(os.path.getsize(art_abs), art["bytes"], f"{tid}: bytes {kind}")

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


if __name__ == "__main__":
    unittest.main()
