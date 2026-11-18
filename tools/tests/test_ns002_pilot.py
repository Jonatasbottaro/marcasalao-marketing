"""Testes automatizados (unittest) para o piloto ponta a ponta NS-002."""

from __future__ import annotations

import json
import os
import sys
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import build_video
import ns002_pilot
import render_local
import srt_validate


class Ns002PilotTest(unittest.TestCase):
    CONFIG_REL = "02-reels-shorts/ns002-piloto-01/ns002-piloto.config.json"
    MANIFEST_REL = "02-reels-shorts/ns002-piloto-01/manifest.json"
    SRT_REL = "04-legendas/ns002_roteiro_001.srt"
    NARR_REL = "04-legendas/ns002_roteiro_001_narracao.txt"

    def _path(self, rel_path: str) -> str:
        return os.path.join(REPO_ROOT, rel_path.replace("/", os.sep))

    def _load_json(self, rel_path: str) -> dict:
        with open(self._path(rel_path), "r", encoding="utf-8") as handle:
            return json.load(handle)

    def test_01_srt_valid_and_synced_with_package(self) -> None:
        srt_src = self._path(self.SRT_REL)
        self.assertTrue(os.path.isfile(srt_src))
        errors = srt_validate.validate_srt_file(srt_src, duration=30.0)
        self.assertEqual(errors, [])

        pkg_srt = self._path("02-reels-shorts/ns002-piloto-01/ns002_roteiro_001.srt")
        self.assertTrue(os.path.isfile(pkg_srt))
        self.assertEqual(render_local.sha256_file(srt_src), render_local.sha256_file(pkg_srt))

        narr_src = self._path(self.NARR_REL)
        pkg_narr = self._path("02-reels-shorts/ns002-piloto-01/ns002_roteiro_001_narracao.txt")
        self.assertTrue(os.path.isfile(narr_src))
        self.assertTrue(os.path.isfile(pkg_narr))
        self.assertEqual(render_local.sha256_file(narr_src), render_local.sha256_file(pkg_narr))

    def test_02_config_parametrized_for_brand_kit_and_guardrails(self) -> None:
        cfg = self._load_json(self.CONFIG_REL)
        self.assertEqual(cfg["campaignId"], "NS-002")
        self.assertEqual(cfg["preset"], "saas-demo")
        self.assertFalse(cfg["audioPolicy"]["enabled"])
        self.assertEqual(cfg["audioPolicy"]["ffmpegFlag"], "-an")
        self.assertEqual(cfg["brand"]["tenantId"], "marca-salao")
        self.assertEqual(cfg["brand"]["brandName"], "Marca Salão")
        self.assertTrue(cfg["brand"]["headerOverlay"]["enabled"])
        self.assertIn("primaryAccent", cfg["brand"]["palette"])
        self.assertFalse(cfg["bookingCase"]["paymentDisplayed"])
        self.assertEqual(round(sum(s["duration"] for s in cfg["scenes"]), 3), 30.0)

        # Verifica separacao de superficies
        surfaces = {s["id"]: s["surface"] for s in cfg["scenes"]}
        self.assertEqual(surfaces["cena-02-escolha"], "public-booking")
        self.assertEqual(surfaces["cena-03-confirma"], "public-booking")
        self.assertEqual(surfaces["cena-05-salao-ve"], "manager-agenda")

        with open(self._path(self.SRT_REL), "r", encoding="utf-8") as handle:
            srt_text = handle.read()
        with open(self._path(self.NARR_REL), "r", encoding="utf-8") as handle:
            narr_text = handle.read()
        self.assertEqual(ns002_pilot.validate_guardrails(cfg, srt_text, narr_text), [])

    def test_03_guardrails_reject_forbidden_promises_and_legacy_brand(self) -> None:
        cfg = self._load_json(self.CONFIG_REL)
        for forbidden_phrase in (
            "Confirmação automática via WhatsApp em 24 horas",
            "Tela de pagamento integrado",
            "Redução de faltas e aumento de faturamento",
            "Dashboard do Meu Salão",
        ):
            errs = ns002_pilot.validate_guardrails(cfg, forbidden_phrase, "texto limpo")
            self.assertTrue(errs, f"Deveria recusar: {forbidden_phrase}")

    def test_04_manifest_hashes_and_ffprobe_match_contract(self) -> None:
        manifest = self._load_json(self.MANIFEST_REL)
        self.assertEqual(manifest["id"], "ns002-piloto-01")
        self.assertEqual(manifest["brand"]["brandName"], "Marca Salão")

        arts = manifest["artifacts"]
        for key in ("srt", "narration", "storyboard"):
            entry = arts[key]
            abs_p = self._path(entry["path"])
            self.assertTrue(os.path.isfile(abs_p), abs_p)
            self.assertEqual(render_local.sha256_file(abs_p), entry["sha256"], key)
            self.assertEqual(os.path.getsize(abs_p), entry["bytes"], key)

        fix_abs = self._path(manifest["fixture"]["path"])
        self.assertEqual(render_local.sha256_file(fix_abs), manifest["fixture"]["sha256"])

        video_meta = arts["video"]
        ffp = video_meta["ffprobe"]
        self.assertEqual(ffp["videoStreams"], 1)
        self.assertEqual(ffp["audioStreams"], 0)
        self.assertEqual(ffp["codec"], "h264")
        self.assertEqual(ffp["width"], 1080)
        self.assertEqual(ffp["height"], 1920)
        self.assertEqual(ffp["fps"], 30.0)
        self.assertEqual(ffp["pixFmt"], "yuv420p")
        self.assertAlmostEqual(ffp["duration"], 30.0, places=1)

        sb = arts["storyboard"]
        self.assertEqual(sb["timestampsSeconds"], [2.0, 8.0, 16.0, 24.0])
        self.assertEqual((sb["width"], sb["height"]), (1080, 1920))

    def test_05_rejects_paths_outside_project_root(self) -> None:
        outside = os.path.abspath(os.path.join(REPO_ROOT, "..", "fora-da-raiz-ns002"))
        with self.assertRaises(build_video.DeliveryError):
            ns002_pilot.run_pilot(
                self.CONFIG_REL,
                REPO_ROOT,
                outside,
                os.path.join(REPO_ROOT, ".workspace", "archives", "ns002-piloto-01"),
                project_root=REPO_ROOT,
            )


if __name__ == "__main__":
    unittest.main()
