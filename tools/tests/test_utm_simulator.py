"""Testes automatizados (unittest) para tools/utm_simulator.py."""

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

import utm_simulator  # noqa: E402

TEST_TMP_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "test_utm_simulator")


def _url(domain: str, source: str = "instagram", medium: str = "reels",
         campaign: str = "camp-x", content: str = "tenant-a") -> str:
    return (
        f"https://{domain}/?utm_source={source}&utm_medium={medium}"
        f"&utm_campaign={campaign}&utm_content={content}"
    )


class UtmSimulatorTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        if os.path.isdir(TEST_TMP_ROOT):
            shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)

    def _root(self, name: str) -> str:
        path = os.path.join(TEST_TMP_ROOT, name)
        shutil.rmtree(path, ignore_errors=True)
        os.makedirs(path, exist_ok=True)
        return path

    def _write_json(self, root: str, rel_path: str, payload: dict) -> str:
        target = os.path.join(root, *rel_path.split("/"))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        return target

    def _tenant(self, root: str, tenant_id: str, domain: str, campaigns: tuple[str, ...] = ()) -> None:
        self._write_json(
            root,
            f"tenants/{tenant_id}/brand-kit.json",
            {
                "schemaVersion": 1,
                "tenantId": tenant_id,
                "brandName": tenant_id,
                "domain": domain,
                "url": f"https://{domain}",
                "utmDefaults": {"utm_source": "instagram", "utm_medium": "reels"},
            },
        )
        for slug in campaigns:
            self._write_json(
                root,
                f"tenants/{tenant_id}/campaigns/{slug}.json",
                {"id": slug, "tenantId": tenant_id},
            )

    def _calendar(self, root: str, slots: list[dict]) -> None:
        self._write_json(
            root,
            "04-legendas/calendario-editorial.json",
            {"schemaVersion": 2, "autoPublish": False, "slots": slots},
        )

    def _slot(self, slot_id: str, tenant_id: str, slug: str, url: str,
              onda: int = 1, canal: str = "instagram") -> dict:
        return {
            "slotId": slot_id,
            "onda": onda,
            "tenantId": tenant_id,
            "slug": slug,
            "canal": canal,
            "utmUrl": url,
        }

    def _codes(self, result: dict) -> set[str]:
        codes = {problem["code"] for problem in result["problems"]}
        for slot in result["slots"]:
            codes.update(problem["code"] for problem in slot["problems"])
        return codes

    def test_01_real_calendar_audits_every_url(self) -> None:
        result = utm_simulator.audit_and_simulate_utm(root=REPO_ROOT)
        self.assertTrue(result["ok"], result["problems"])
        self.assertTrue(result["calendarFound"])
        self.assertGreaterEqual(result["totalUrls"], 32)
        self.assertEqual(result["urlsAudited"], result["totalUrls"])
        self.assertEqual(result["urlsOk"], result["totalUrls"])
        self.assertEqual(result["derivedUrls"], 0)
        self.assertTrue(all(slot["origin"] == "calendar" for slot in result["slots"]))
        self.assertGreaterEqual(len(result["tenants"]), 4)
        self.assertEqual(result["tenants"]["marca-salao"]["domain"], "marcasalao.com.br")
        self.assertEqual(result["tenants"]["multitrack-hub"]["domain"], "multitrackhub.com.br")

    def test_02_domain_mismatch_is_rejected(self) -> None:
        root = self._root("domain-mismatch")
        self._tenant(root, "alpha", "alpha.com.br")
        self._calendar(root, [
            self._slot("slot-1", "alpha", "camp-alpha", _url("beta.com.br", campaign="camp-alpha"))
        ])
        result = utm_simulator.audit_and_simulate_utm(root=root)
        self.assertFalse(result["ok"])
        self.assertIn("DOMINIO_DIVERGENTE", self._codes(result))
        self.assertEqual(result["urlsOk"], 0)

    def test_03_missing_utm_param_is_rejected(self) -> None:
        root = self._root("missing-param")
        self._tenant(root, "alpha", "alpha.com.br")
        url = "https://alpha.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-alpha"
        self._calendar(root, [self._slot("slot-1", "alpha", "camp-alpha", url)])
        result = utm_simulator.audit_and_simulate_utm(root=root)
        self.assertFalse(result["ok"])
        self.assertIn("UTM_PARAM_AUSENTE", self._codes(result))

    def test_04_non_normalized_values_are_rejected(self) -> None:
        root = self._root("non-normalized")
        self._tenant(root, "alpha", "alpha.com.br")
        url = _url("alpha.com.br", source="Instagram", campaign="camp-alpha", content="Marca Salao")
        self._calendar(root, [self._slot("slot-1", "alpha", "camp-alpha", url)])
        result = utm_simulator.audit_and_simulate_utm(root=root)
        self.assertFalse(result["ok"])
        self.assertIn("UTM_VALOR_NAO_PADRONIZADO", self._codes(result))

    def test_05_cross_tenant_collision_is_rejected(self) -> None:
        root = self._root("collision")
        self._tenant(root, "alpha", "alpha.com.br")
        self._tenant(root, "beta", "beta.com.br")
        self._calendar(root, [
            self._slot("slot-1", "alpha", "camp-shared", _url("alpha.com.br", campaign="camp-shared", content="shared")),
            self._slot("slot-2", "beta", "camp-shared", _url("beta.com.br", campaign="camp-shared", content="shared")),
        ])
        result = utm_simulator.audit_and_simulate_utm(root=root)
        self.assertFalse(result["ok"])
        codes = {problem["code"] for problem in result["collisions"]}
        self.assertIn("COLISAO_CAMPANHA_ENTRE_TENANTS", codes)
        self.assertIn("COLISAO_ATRIBUICAO", codes)
        self.assertGreaterEqual(len(result["collisions"]), 2)

    def test_06_derives_urls_for_uncalendared_campaigns(self) -> None:
        root = self._root("derived")
        self._tenant(root, "alpha", "alpha.com.br", campaigns=("camp-nova",))
        self._calendar(root, [])
        result = utm_simulator.audit_and_simulate_utm(root=root)
        self.assertTrue(result["ok"], result["problems"])
        self.assertEqual(result["totalUrls"], 1)
        self.assertEqual(result["derivedUrls"], 1)
        derived = result["slots"][0]
        self.assertEqual(derived["origin"], "derived")
        self.assertEqual(derived["utmParams"]["utm_campaign"], "camp-nova")
        self.assertEqual(derived["utmParams"]["utm_content"], "alpha")
        self.assertTrue(derived["url"].startswith("https://alpha.com.br/?utm_source=instagram"))

    def test_07_calendar_tenant_without_brand_kit_is_rejected(self) -> None:
        root = self._root("unknown-tenant")
        self._tenant(root, "alpha", "alpha.com.br")
        self._calendar(root, [
            self._slot("slot-1", "alpha", "camp-alpha", _url("alpha.com.br", campaign="camp-alpha")),
            self._slot("slot-2", "fantasma", "camp-ghost", _url("alpha.com.br", campaign="camp-ghost")),
        ])
        result = utm_simulator.audit_and_simulate_utm(root=root)
        self.assertFalse(result["ok"])
        self.assertIn("TENANT_DESCONHECIDO", self._codes(result))
        self.assertIn("fantasma", result["skippedTenants"])

    def test_08_simulate_traffic_writes_sessions_and_summary(self) -> None:
        out_dir = ".workspace/tmp/test_utm_simulator/sim-out"
        result = utm_simulator.audit_and_simulate_utm(
            root=REPO_ROOT, simulate_traffic=True, out_dir=out_dir, session_seed=7
        )
        self.assertTrue(result["ok"], result["problems"])
        simulation = result["simulation"]
        self.assertIsNotNone(simulation)
        self.assertFalse(simulation["financialSimulation"])
        self.assertGreaterEqual(simulation["totalSessions"], 32)
        sessions_path = os.path.join(REPO_ROOT, *out_dir.split("/"), "utm_sessions_sample.json")
        summary_path = os.path.join(REPO_ROOT, *out_dir.split("/"), "utm_attribution_summary.md")
        self.assertTrue(os.path.isfile(sessions_path))
        self.assertTrue(os.path.isfile(summary_path))

        with open(sessions_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertFalse(payload["financialSimulation"])
        self.assertTrue(all(session["revenueBRL"] is None for session in payload["sessions"]))
        waves = {session["wave"] for session in payload["sessions"]}
        self.assertEqual(waves, {"onda-1", "onda-2"})
        footprints = {f"{s['utm_source']}/{s['utm_medium']}" for s in payload["sessions"]}
        for expected in ("instagram/reels", "youtube/shorts", "instagram/feed", "youtube/video"):
            self.assertIn(expected, footprints)

        with open(summary_path, "r", encoding="utf-8") as handle:
            markdown = handle.read()
        self.assertIn("Cobranca financeira simulada: **nao**", markdown)
        self.assertIn("marca-salao", markdown)
        self.assertIn("clinica-vital", markdown)

        # Mesma seed -> mesmas sessoes (determinismo).
        again = utm_simulator.audit_and_simulate_utm(
            root=REPO_ROOT, simulate_traffic=True,
            out_dir=".workspace/tmp/test_utm_simulator/sim-out-2", session_seed=7,
        )
        self.assertTrue(again["simulation"]["enabled"])
        with open(
            os.path.join(REPO_ROOT, ".workspace", "tmp", "test_utm_simulator",
                         "sim-out-2", "utm_sessions_sample.json"),
            "r",
            encoding="utf-8",
        ) as handle:
            payload_again = json.load(handle)
        self.assertEqual(
            [s["sessionId"] for s in payload["sessions"]],
            [s["sessionId"] for s in payload_again["sessions"]],
        )

    def test_09_simulation_validates_recommended_events_per_niche(self) -> None:
        result = utm_simulator.audit_and_simulate_utm(
            root=REPO_ROOT, simulate_traffic=True,
            out_dir=".workspace/tmp/test_utm_simulator/sim-events", session_seed=11,
        )
        simulation = result["simulation"]
        self.assertEqual(
            set(simulation["recommendedEvents"]),
            {"marca-salao", "meu-salao", "estudio-flow", "multitrack-hub", "clinica-vital"},
        )
        for tenant_id, niche in simulation["byNiche"].items():
            self.assertTrue(niche["recommendedEvents"], tenant_id)
            observed = set(niche["events"])
            self.assertTrue(observed.issubset(set(niche["recommendedEvents"])), (tenant_id, observed))
        observable = utm_simulator.RECOMMENDED_EVENTS["marca-salao"]
        self.assertIn("booking_started", observable)
        self.assertEqual(
            [p for p in simulation["problems"] if p["severity"] == "error"], []
        )

    def test_10_cli_json_and_human_outputs(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = utm_simulator.main(["--root", REPO_ROOT, "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertTrue(payload["ok"])

        with contextlib.redirect_stdout(io.StringIO()) as human:
            rc_human = utm_simulator.main(["--root", REPO_ROOT])
        self.assertEqual(rc_human, 0)
        self.assertIn("APROVADO", human.getvalue())

    def test_11_cli_errors_and_path_containment(self) -> None:
        root = self._root("cli-errors")
        self._tenant(root, "alpha", "alpha.com.br", campaigns=("camp-cli",))

        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = utm_simulator.main([
                "--root", root, "--calendar", "04-legendas/nao-existe.json", "--json",
            ])
        self.assertEqual(rc, 2)
        payload = json.loads(buf.getvalue())
        self.assertFalse(payload["ok"])
        self.assertIn("CALENDARIO_AUSENTE", payload["error"])

        with contextlib.redirect_stdout(io.StringIO()) as buf2:
            rc_outside = utm_simulator.main([
                "--root", root, "--simulate-traffic", "--out-dir", "../fora-da-raiz", "--json",
            ])
        self.assertEqual(rc_outside, 2)
        self.assertIn("PATH_OUTSIDE_ROOT", json.loads(buf2.getvalue())["error"])


if __name__ == "__main__":
    unittest.main()