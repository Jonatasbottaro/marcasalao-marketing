"""Testes automatizados (unittest) para schemas, tenants e validador de contratos."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import sys
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import render_local
import tenant_validator


class TenantContractsTest(unittest.TestCase):
    def _path(self, rel_path: str) -> str:
        return os.path.join(REPO_ROOT, rel_path.replace("/", os.sep))

    def _load_json(self, rel_path: str) -> dict:
        with open(self._path(rel_path), "r", encoding="utf-8") as handle:
            return json.load(handle)

    def test_01_all_three_tenants_pass_contract_validation(self) -> None:
        discovered = tenant_validator.list_tenants(REPO_ROOT)
        for expected in ("clinica-vital", "estudio-flow", "marca-salao", "meu-salao", "multitrack-hub"):
            self.assertIn(expected, discovered)

        cv = tenant_validator.load_and_validate_tenant("clinica-vital", root=REPO_ROOT, strict=True)
        self.assertTrue(cv["ok"])
        self.assertEqual(cv["brandKit"]["brandName"], "Clínica Vital")
        self.assertEqual(cv["brandKit"]["monogram"], "CV")
        self.assertEqual(cv["brandKit"]["defaultPreset"], "saas-demo")
        self.assertFalse(cv["guardrails"]["audioPolicy"]["allowAudioTrack"])
        self.assertTrue(cv["guardrails"]["audioPolicy"]["requireSrt"])
        self.assertTrue(cv["guardrails"]["audioPolicy"]["requireExternalNarration"])

        ef = tenant_validator.load_and_validate_tenant("estudio-flow", root=REPO_ROOT, strict=True)
        self.assertTrue(ef["ok"])
        self.assertEqual(ef["brandKit"]["monogram"], "EF")
        self.assertEqual(ef["brandKit"]["defaultPreset"], "saas-demo")
        self.assertFalse(ef["guardrails"]["audioPolicy"]["allowAudioTrack"])

        ms = tenant_validator.load_and_validate_tenant("marca-salao", root=REPO_ROOT, strict=True)
        self.assertTrue(ms["ok"])
        self.assertEqual(ms["brandKit"]["defaultPreset"], "saas-demo")
        self.assertFalse(ms["guardrails"]["audioPolicy"]["allowAudioTrack"])
        self.assertIn("/booking/[salonId]", ms["guardrails"]["routeRules"])
        self.assertIn("/gestor/agenda", ms["guardrails"]["routeRules"])

        wl = tenant_validator.load_and_validate_tenant("meu-salao", root=REPO_ROOT, strict=True)
        self.assertTrue(wl["ok"])
        self.assertEqual(wl["brandKit"]["brandName"], "Meu Salão")
        self.assertEqual(wl["brandKit"]["defaultPreset"], "saas-demo")
        self.assertFalse(wl["guardrails"]["audioPolicy"]["allowAudioTrack"])

        mth = tenant_validator.load_and_validate_tenant("multitrack-hub", root=REPO_ROOT, strict=True)
        self.assertTrue(mth["ok"])
        self.assertEqual(mth["brandKit"]["monogram"], "MH")
        self.assertEqual(mth["brandKit"]["defaultPreset"], "shorts-completo")
        self.assertTrue(mth["guardrails"]["audioPolicy"]["allowAudioTrack"])
        self.assertTrue(mth["guardrails"]["audioPolicy"]["requireSrt"])

    def test_02_marca_salao_brand_kit_and_fixture_sync_with_pilot(self) -> None:
        kit = self._load_json("tenants/marca-salao/brand-kit.json")
        pilot_cfg = self._load_json("02-reels-shorts/ns002-piloto-01/ns002-piloto.config.json")

        self.assertEqual(kit["tenantId"], pilot_cfg["brand"]["tenantId"])
        self.assertEqual(kit["brandName"], pilot_cfg["brand"]["brandName"])
        self.assertEqual(kit["displayTitle"], pilot_cfg["brand"]["displayTitle"])
        self.assertEqual(kit["domain"], pilot_cfg["brand"]["domain"])
        self.assertEqual(kit["url"], pilot_cfg["brand"]["url"])
        self.assertEqual(kit["tagline"], pilot_cfg["brand"]["tagline"])
        self.assertEqual(kit["palette"]["rgb"], pilot_cfg["brand"]["palette"])
        self.assertEqual(kit["subtitleStyle"], pilot_cfg["subtitleStyle"])
        self.assertEqual(kit["headerOverlay"]["height"], pilot_cfg["brand"]["headerOverlay"]["height"])
        self.assertEqual(
            kit["headerOverlay"]["replaceLegacyLabel"],
            pilot_cfg["brand"]["headerOverlay"]["replaceLegacyLabel"],
        )
        self.assertEqual(kit["defaultPreset"], pilot_cfg["preset"])

        self.assertEqual(
            render_local.sha256_file(self._path("tenants/marca-salao/fixtures/fixture-editorial-marca-salao.json")),
            render_local.sha256_file(self._path("docs/fixtures/fixture-editorial-marca-salao.json")),
        )

    def test_03_ns002_artifacts_pass_marca_salao_guardrails(self) -> None:
        guardrails = self._load_json("tenants/marca-salao/guardrails.json")
        for rel_file in ("04-legendas/ns002_roteiro_001.srt", "04-legendas/ns002_roteiro_001_narracao.txt"):
            with open(self._path(rel_file), "r", encoding="utf-8") as handle:
                content = handle.read()
            violations = tenant_validator.validate_text_against_guardrails(
                content, guardrails, check_ui_elements=True, ignore_editorial_footer=True
            )
            self.assertEqual(violations, [], f"{rel_file}: {violations}")

    def test_04_invalid_brand_kit_rejected_by_schema(self) -> None:
        base_kit = self._load_json("tenants/marca-salao/brand-kit.json")

        bad_id = copy.deepcopy(base_kit)
        bad_id["tenantId"] = "Marca_Salao"
        self.assertTrue(tenant_validator.validate_brand_kit(bad_id, REPO_ROOT))

        bad_hex = copy.deepcopy(base_kit)
        bad_hex["palette"]["primary"] = "amarelo"
        self.assertTrue(tenant_validator.validate_brand_kit(bad_hex, REPO_ROOT))

        bad_preset = copy.deepcopy(base_kit)
        bad_preset["defaultPreset"] = "podcast-audio"
        self.assertTrue(tenant_validator.validate_brand_kit(bad_preset, REPO_ROOT))

        missing_field = copy.deepcopy(base_kit)
        del missing_field["utmDefaults"]
        self.assertTrue(tenant_validator.validate_brand_kit(missing_field, REPO_ROOT))

        extra_field = copy.deepcopy(base_kit)
        extra_field["campoDesconhecido"] = True
        self.assertTrue(tenant_validator.validate_brand_kit(extra_field, REPO_ROOT))

        bad_rgb = copy.deepcopy(base_kit)
        bad_rgb["palette"]["rgb"]["primaryAccent"] = [255, 193]
        self.assertTrue(tenant_validator.validate_brand_kit(bad_rgb, REPO_ROOT))

    def test_05_forbidden_claims_and_ui_elements_blocked_per_tenant(self) -> None:
        ms_gr = self._load_json("tenants/marca-salao/guardrails.json")
        for bad_text in (
            "Envio automático via WhatsApp e lembrete de 24 horas",
            "Redução de faltas garantida e aumento de faturamento",
            "Conheça o painel do Meu Salão",
        ):
            self.assertTrue(
                tenant_validator.validate_text_against_guardrails(bad_text, ms_gr),
                f"marca-salao deveria vetar: {bad_text}",
            )
        self.assertTrue(
            tenant_validator.validate_text_against_guardrails("Tela A pagar", ms_gr, check_ui_elements=True)
        )

        wl_gr = self._load_json("tenants/meu-salao/guardrails.json")
        # White-label Meu Salão permite o proprio nome de marca, mas bloqueia promessas falsas
        self.assertEqual(
            tenant_validator.validate_text_against_guardrails("Agendamento online no Meu Salão", wl_gr),
            [],
        )
        self.assertTrue(
            tenant_validator.validate_text_against_guardrails("Lembrete automatico por SMS", wl_gr)
        )

        mth_gr = self._load_json("tenants/multitrack-hub/guardrails.json")
        self.assertEqual(
            tenant_validator.validate_text_against_guardrails(
                "Catálogo organizado com Click, Guide e stems em multitrackhub.com.br", mth_gr
            ),
            [],
        )
        self.assertTrue(
            tenant_validator.validate_text_against_guardrails(
                "Chame no WhatsApp comercial e tenha lucro garantido", mth_gr, check_ui_elements=True
            )
        )

    def test_06_fixture_rejects_generic_or_e2e_placeholders(self) -> None:
        for bad_payload in (
            {"tenantId": "marca-salao", "cliente": "Lorem ipsum dolor"},
            {"tenantId": "marca-salao", "cliente": "user1"},
            {"tenantId": "marca-salao", "namespace": "e2e-1793884270981"},
            {"tenantId": "marca-salao", "salao": "Meu Salão E2E"},
            {"tenantId": "marca-salao", "preco": "R$ 12.000,00"},
        ):
            self.assertTrue(
                tenant_validator.validate_fixture_data(bad_payload, tenant_id="marca-salao"),
                f"Deveria recusar placeholder: {bad_payload}",
            )

        bad_tenant = {"tenantId": "outro-tenant", "nome": "Exemplo"}
        self.assertTrue(tenant_validator.validate_fixture_data(bad_tenant, tenant_id="marca-salao"))

    def test_07_cli_exit_codes(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = tenant_validator.main(["--all", "--root", REPO_ROOT, "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["ok"])
        self.assertGreaterEqual(len(payload["tenants"]), 5)
        validated_ids = {entry["tenantId"] for entry in payload["tenants"]}
        self.assertIn("clinica-vital", validated_ids)

        with contextlib.redirect_stdout(io.StringIO()) as err_buf:
            rc_missing = tenant_validator.main(["--tenant", "inexistente", "--root", REPO_ROOT, "--json"])
        self.assertEqual(rc_missing, 1)
        err_payload = json.loads(err_buf.getvalue())
        self.assertFalse(err_payload["ok"])

    def test_08_clinica_vital_regulated_niche_guardrails(self) -> None:
        gr = self._load_json("tenants/clinica-vital/guardrails.json")

        for bad_text in (
            "Prometemos cura garantida em poucas sessões",
            "Resultado estético garantido após a primeira avaliação",
            "Tratamento sem dor garantido para todos os pacientes",
            "Diagnóstico online em cinco minutos",
            "Mensagens automáticas por WhatsApp, SMS e e-mail",
            "Lembrete automático 24 horas antes da consulta",
            "Redução de faltas garantida e zero absenteísmo",
            "Aumento de faturamento comprovado para a clínica",
        ):
            self.assertTrue(
                tenant_validator.validate_text_against_guardrails(bad_text, gr),
                f"clinica-vital deveria vetar promessa clínica: {bad_text}",
            )

        for bad_ui in (
            "Tela de checkout simulada",
            "Pagamento e cobrança no aplicativo",
            "Prontuário médico sensível exposto na tela",
            "Receita digital liberada na consulta",
            "Fotos antes e depois dos procedimentos",
            "Painel do Meu Salão E2E",
            "Lorem ipsum dolor sit amet",
        ):
            self.assertTrue(
                tenant_validator.validate_text_against_guardrails(bad_ui, gr, check_ui_elements=True),
                f"clinica-vital deveria vetar elemento de UI: {bad_ui}",
            )

        self.assertEqual(
            tenant_validator.validate_text_against_guardrails(
                "A recepção organiza a agenda de consultas em /gestor/consultas.", gr
            ),
            [],
        )

        rules = gr["routeRules"]
        self.assertEqual(rules["/avaliacao/[clinicId]"]["surface"], "public-booking")
        self.assertEqual(rules["/gestor/consultas"]["surface"], "manager-agenda")
        self.assertIn("busca-paciente", rules["/gestor/consultas"]["allowedResponsibilities"])
        self.assertIn("alteracao-manual-status", rules["/gestor/consultas"]["allowedResponsibilities"])
        self.assertIn("diagnostico-online", rules["/avaliacao/[clinicId]"]["forbiddenResponsibilities"])

    def test_09_clinica_vital_fixture_and_campaigns_match_contracts(self) -> None:
        fixture = self._load_json("tenants/clinica-vital/fixtures/fixture-editorial-clinica-vital.json")
        self.assertEqual(fixture["tenantId"], "clinica-vital")
        self.assertEqual(len(fixture["profissionais"]), 4)
        self.assertEqual(len(fixture["servicos"]), 5)
        self.assertEqual(fixture["booking"]["rota"], "/avaliacao/clinica-vital-centro")
        self.assertEqual(fixture["agenda"]["visaoRota"], "/gestor/consultas")
        self.assertEqual(len(fixture["agenda"]["atendimentos"]), 6)
        statuses = {item["status"] for item in fixture["agenda"]["atendimentos"]}
        self.assertEqual(statuses, {"Confirmado", "Aguardando", "Concluído"})
        self.assertIn("Patricia Monteiro", {item["cliente"] for item in fixture["agenda"]["atendimentos"]})

        gr = self._load_json("tenants/clinica-vital/guardrails.json")
        campaigns = {}
        for name in ("camp-saas-demo-clinica-vital-001.json", "camp-saas-demo-clinica-vital-002.json"):
            cfg = self._load_json(f"tenants/clinica-vital/campaigns/{name}")
            campaigns[cfg["id"]] = cfg
            self.assertEqual(cfg["tenantId"], "clinica-vital")
            self.assertEqual(cfg["preset"], "saas-demo")
            self.assertEqual(len(cfg["scenes"]), 6)
            self.assertAlmostEqual(
                sum(float(scene["duration"]) for scene in cfg["scenes"]),
                float(cfg["format"]["duration"]),
                places=3,
            )
            for scene in cfg["scenes"]:
                for key in ("badge", "headline", "subline", "caption", "ctaLabel", "narrationText", "route"):
                    text = scene.get(key)
                    if not text:
                        continue
                    self.assertEqual(
                        tenant_validator.validate_text_against_guardrails(
                            str(text), gr, check_ui_elements=True
                        ),
                        [],
                        f"{cfg['id']} {scene['id']}.{key}: texto viola guardrails",
                    )

        journey = campaigns["camp-saas-demo-clinica-vital-001"]
        routes = {scene.get("route") for scene in journey["scenes"] if scene.get("route")}
        self.assertIn("/avaliacao/clinica-vital-centro", routes)
        self.assertIn("/gestor/consultas", routes)
        self.assertEqual(journey["bookingCase"]["cliente"], "Patricia Monteiro")
        self.assertEqual(journey["bookingCase"]["servicoId"], "srv-cv-001")

        reception = campaigns["camp-saas-demo-clinica-vital-002"]
        for scene in reception["scenes"]:
            self.assertFalse(str(scene.get("route", "")).startswith("/avaliacao"))
        reception_surfaces = [scene["surface"] for scene in reception["scenes"]]
        self.assertEqual(reception_surfaces.count("manager-agenda"), 4)
        self.assertEqual(reception_surfaces.count("public-booking"), 0)


if __name__ == "__main__":
    unittest.main()
