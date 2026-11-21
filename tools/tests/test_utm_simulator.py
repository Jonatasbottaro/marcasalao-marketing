"""Testes automatizados (unittest) para tools/utm_simulator.py — Etapa 5B, Agente 7."""

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

TEST_TMP_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "test_utm_simulator_ag7")


def _url(domain: str, source: str = "instagram", medium: str = "reels",
         campaign: str = "camp-x", content: str = "tenant-a") -> str:
    return (
        f"https://{domain}/?utm_source={source}&utm_medium={medium}"
        f"&utm_campaign={campaign}&utm_content={content}"
    )


class UtmSimulatorTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
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
        self._write_json(root, f"tenants/{tenant_id}/brand-kit.json", {
            "schemaVersion": 1,
            "tenantId": tenant_id,
            "brandName": tenant_id,
            "domain": domain,
            "url": f"https://{domain}",
            "defaultPreset": "saas-demo",
            "utmDefaults": {"utm_source": "instagram", "utm_medium": "reels"},
        })
        for slug in campaigns:
            self._write_json(root, f"tenants/{tenant_id}/campaigns/{slug}.json", {
                "id": slug, "tenantId": tenant_id,
            })

    def _calendar(self, root: str, slots: list[dict]) -> None:
        self._write_json(root, "04-legendas/calendario-editorial.json", {
            "schemaVersion": 2, "autoPublish": False, "slots": slots,
        })

    def _slot(self, slot_id: str, tenant_id: str, slug: str, url: str,
              onda: int = 1, canal: str = "instagram", formato: str = "9:16") -> dict:
        return {
            "slotId": slot_id,
            "onda": onda,
            "tenantId": tenant_id,
            "slug": slug,
            "canal": canal,
            "formatoVideo": formato,
            "utmUrl": url,
        }

    def _codes(self, result: dict) -> set[str]:
        codes = {problem["code"] for problem in result["problems"]}
        for slot in result["slots"]:
            codes.update(problem["code"] for problem in slot["problems"])
        return codes

    # 1) Auditoria real do calendario (100% das URLs).
    def test_01_real_calendar_audits_every_url(self) -> None:
        result = utm_simulator.audit_and_simulate_utm(root=REPO_ROOT)
        self.assertTrue(result["ok"], result["problems"])
        self.assertTrue(result["calendarFound"])
        self.assertGreaterEqual(result["totalUrls"], 40)
        self.assertEqual(result["urlsAudited"], result["totalUrls"])
        self.assertEqual(result["urlsOk"], result["totalUrls"])
        self.assertEqual(result["derivedUrls"], 0)
        self.assertEqual(result["unscheduledTenants"], [])
        self.assertTrue(all(slot["origin"] == "calendar" for slot in result["slots"]))
        for tenant_id, domain in {
            "marca-salao": "marcasalao.com.br",
            "meu-salao": "meusalao.com.br",
            "estudio-flow": "estudioflow.com.br",
            "multitrack-hub": "multitrackhub.com.br",
            "clinica-vital": "clinicavital.com.br",
        }.items():
            self.assertIn(tenant_id, result["tenants"])
            self.assertEqual(result["tenants"][tenant_id]["domain"], domain)

    # 2) Deteccao de dominio divergente ( HTTPS exato do brand-kit ).
    def test_02_domain_mismatch_is_detected(self) -> None:
        root = self._root("domain-mismatch")
        self._tenant(root, "alpha", "alpha.com.br")
        self._calendar(root, [
            self._slot("slot-1", "alpha", "camp-alpha", _url("beta.com.br", campaign="camp-alpha"))
        ])
        result = utm_simulator.audit_and_simulate_utm(root=root)
        self.assertFalse(result["ok"])
        self.assertIn("DOMINIO_DIVERGENTE", self._codes(result))
        self.assertEqual(result["urlsOk"], 0)

    # 3) Deteccao de colisao de atribuicao entre tenants (tupla de 4 UTMs).
    def test_03_cross_tenant_collision_is_detected(self) -> None:
        root = self._root("collision")
        self._tenant(root, "alpha", "alpha.com.br")
        self._tenant(root, "beta", "beta.com.br")
        self._calendar(root, [
            self._slot("slot-1", "alpha", "camp-shared",
                       _url("alpha.com.br", campaign="camp-shared", content="shared")),
            self._slot("slot-2", "beta", "camp-shared",
                       _url("beta.com.br", campaign="camp-shared", content="shared")),
        ])
        result = utm_simulator.audit_and_simulate_utm(root=root)
        self.assertFalse(result["ok"])
        codes = {problem["code"] for problem in result["collisions"]}
        self.assertIn("COLISAO_ATRIBUICAO", codes)
        self.assertIn("COLISAO_ATRIBUICAO", self._codes(result))

    # 4) Cobertura de tenant descoberto em tenants/* e ainda nao agendado.
    def test_04_unscheduled_tenant_is_covered(self) -> None:
        root = self._root("unscheduled")
        self._tenant(root, "alpha", "alpha.com.br")
        self._tenant(root, "beta", "beta.com.br", campaigns=("camp-beta-nova",))
        self._calendar(root, [
            self._slot("slot-1", "alpha", "camp-alpha", _url("alpha.com.br", campaign="camp-alpha"))
        ])
        result = utm_simulator.audit_and_simulate_utm(root=root)
        self.assertTrue(result["ok"], result["problems"])
        self.assertEqual(result["unscheduledTenants"], ["beta"])
        self.assertEqual(result["derivedUrls"], 1)
        derived = next(slot for slot in result["slots"] if slot["origin"] == "derived")
        self.assertEqual(derived["tenantId"], "beta")
        self.assertEqual(derived["utmParams"]["utm_campaign"], "camp-beta-nova")
        self.assertEqual(derived["utmParams"]["utm_content"], "beta")
        self.assertTrue(derived["url"].startswith("https://beta.com.br/?utm_source=instagram"))
        self.assertFalse(result["tenants"]["beta"]["onCalendar"])

    # 5) --simulate-traffic: arquivos, duas ondas, quatro formatos, sem receita.
    def test_05_simulate_traffic_writes_sessions_and_summary(self) -> None:
        out_dir = ".workspace/tmp/test_utm_simulator_ag7/sim-out"
        result = utm_simulator.audit_and_simulate_utm(
            root=REPO_ROOT, simulate_traffic=True, out_dir=out_dir, seed=7
        )
        self.assertTrue(result["ok"], result["problems"])
        simulation = result["simulation"]
        self.assertIsNotNone(simulation)
        self.assertFalse(simulation["financialSimulation"])
        self.assertGreaterEqual(simulation["totalSessions"], 40)

        sessions_path = os.path.join(REPO_ROOT, *out_dir.split("/"), "utm_sessions_sample.json")
        summary_path = os.path.join(REPO_ROOT, *out_dir.split("/"), "utm_attribution_summary.md")
        self.assertTrue(os.path.isfile(sessions_path))
        self.assertTrue(os.path.isfile(summary_path))

        with open(sessions_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertFalse(payload["financialSimulation"])
        self.assertTrue(all(session["revenueBRL"] is None for session in payload["sessions"]))
        self.assertEqual(
            {session["wave"] for session in payload["sessions"]}, {"onda-1", "onda-2"}
        )
        formats = {session["formatoVideo"] for session in payload["sessions"]}
        self.assertTrue({"9:16", "1:1", "16:9"}.issubset(formats))
        for expected in ("instagram/reels", "youtube/shorts", "instagram/feed", "youtube/video"):
            self.assertIn(expected, {s["canal"] for s in payload["sessions"]})
        for session in payload["sessions"]:
            if session["converted"]:
                allowed = utm_simulator.RECOMMENDED_EVENTS.get(session["tenantId"], ())
                self.assertIn(session["conversionEvent"], allowed)

        with open(summary_path, "r", encoding="utf-8") as handle:
            markdown = handle.read()
        self.assertIn("Transacoes financeiras simuladas: **nao**", markdown)
        self.assertIn("clinica-vital", markdown)
        self.assertIn("inspect_multitrack_split", markdown)

    # 6) Contencao de path (out-dir e calendar fora da raiz).
    def test_06_path_containment_is_enforced(self) -> None:
        root = self._root("containment")
        self._tenant(root, "alpha", "alpha.com.br", campaigns=("camp-cli",))
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = utm_simulator.main([
                "--root", root, "--simulate-traffic", "--out-dir", "../fora-da-raiz", "--json",
            ])
        self.assertEqual(rc, 2)
        self.assertIn("PATH_OUTSIDE_ROOT", json.loads(buf.getvalue())["error"])

        with contextlib.redirect_stdout(io.StringIO()) as buf2:
            rc2 = utm_simulator.main([
                "--root", root, "--calendar", "../../calendario-alheio.json", "--json",
            ])
        self.assertEqual(rc2, 2)
        self.assertIn("PATH_OUTSIDE_ROOT", json.loads(buf2.getvalue())["error"])

    # 7) CLI --json ( auditoria real ).
    def test_07_cli_json_output(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = utm_simulator.main(["--root", REPO_ROOT, "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["urlsAudited"], payload["totalUrls"])
        self.assertEqual(payload["collisions"], [])

    # 8) Parametro ausente e valor sujo.
    def test_08_missing_and_dirty_params_are_rejected(self) -> None:
        root = self._root("bad-params")
        self._tenant(root, "alpha", "alpha.com.br")
        missing = "https://alpha.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-alpha"
        self._calendar(root, [self._slot("slot-1", "alpha", "camp-alpha", missing)])
        first = utm_simulator.audit_and_simulate_utm(root=root)
        self.assertFalse(first["ok"])
        self.assertIn("UTM_PARAM_AUSENTE", self._codes(first))

        dirty = _url("alpha.com.br", source="Instagram", campaign="camp-alpha", content="Marca Salao")
        self._calendar(root, [self._slot("slot-1", "alpha", "camp-alpha", dirty)])
        second = utm_simulator.audit_and_simulate_utm(root=root)
        self.assertFalse(second["ok"])
        self.assertIn("UTM_VALOR_NAO_PADRONIZADO", self._codes(second))

    # 9) HTTPS e campanha igual ao slug.
    def test_09_https_and_campaign_slug_are_enforced(self) -> None:
        root = self._root("https-slug")
        self._tenant(root, "alpha", "alpha.com.br")
        http = "http://alpha.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-alpha&utm_content=alpha"
        self._calendar(root, [self._slot("slot-1", "alpha", "camp-alpha", http)])
        first = utm_simulator.audit_and_simulate_utm(root=root)
        self.assertIn("ESQUEMA_NAO_HTTPS", self._codes(first))

        other = _url("alpha.com.br", campaign="camp-outra")
        self._calendar(root, [self._slot("slot-1", "alpha", "camp-alpha", other)])
        second = utm_simulator.audit_and_simulate_utm(root=root)
        self.assertIn("UTM_CAMPANHA_DIVERGENTE", self._codes(second))

    # 10) Catalogo fechado de eventos recomendados por nicho.
    def test_10_recommended_events_catalog(self) -> None:
        self.assertEqual(
            set(utm_simulator.RECOMMENDED_EVENTS),
            {"marca-salao", "meu-salao", "estudio-flow", "clinica-vital", "multitrack-hub"},
        )
        self.assertEqual(utm_simulator.RECOMMENDED_EVENTS["marca-salao"], ("view_booking_page",))
        self.assertEqual(utm_simulator.RECOMMENDED_EVENTS["meu-salao"], ("view_booking_page",))
        self.assertEqual(utm_simulator.RECOMMENDED_EVENTS["estudio-flow"], ("select_service_or_class",))
        self.assertEqual(utm_simulator.RECOMMENDED_EVENTS["clinica-vital"], ("request_evaluation",))
        self.assertEqual(utm_simulator.RECOMMENDED_EVENTS["multitrack-hub"], ("inspect_multitrack_split",))
        all_events = {event for events in utm_simulator.RECOMMENDED_EVENTS.values() for event in events}
        self.assertEqual(all_events, {
            "view_booking_page", "select_service_or_class",
            "request_evaluation", "inspect_multitrack_split",
        })

    # 11) Determinismo da seed.
    def test_11_seed_is_deterministic(self) -> None:
        first = utm_simulator.audit_and_simulate_utm(
            root=REPO_ROOT, simulate_traffic=True,
            out_dir=".workspace/tmp/test_utm_simulator_ag7/det-1", seed=99,
        )
        second = utm_simulator.audit_and_simulate_utm(
            root=REPO_ROOT, simulate_traffic=True,
            out_dir=".workspace/tmp/test_utm_simulator_ag7/det-2", seed=99,
        )
        self.assertEqual(first["simulation"]["totals"], second["simulation"]["totals"])
        path_a = os.path.join(REPO_ROOT, ".workspace", "tmp", "test_utm_simulator_ag7", "det-1", "utm_sessions_sample.json")
        path_b = os.path.join(REPO_ROOT, ".workspace", "tmp", "test_utm_simulator_ag7", "det-2", "utm_sessions_sample.json")
        with open(path_a, "r", encoding="utf-8") as handle:
            payload_a = json.load(handle)
        with open(path_b, "r", encoding="utf-8") as handle:
            payload_b = json.load(handle)
        self.assertEqual(
            [s["sessionId"] for s in payload_a["sessions"]],
            [s["sessionId"] for s in payload_b["sessions"]],
        )

    # 12) CLI retorna 1 quando a auditoria reprova.
    def test_12_cli_returns_one_on_audit_failure(self) -> None:
        root = self._root("cli-failure")
        self._tenant(root, "alpha", "alpha.com.br")
        self._calendar(root, [
            self._slot("slot-1", "alpha", "camp-alpha", _url("errado.com.br", campaign="camp-alpha"))
        ])
        with contextlib.redirect_stdout(io.StringIO()):
            rc = utm_simulator.main(["--root", root, "--json"])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
