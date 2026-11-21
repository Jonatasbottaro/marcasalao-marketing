"""Testes automatizados (unittest) para schemas, tenants e validador de contratos."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import sys
import unittest
from pathlib import Path

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

    def test_01_core_tenants_pass_contract_validation(self) -> None:
        discovered = tenant_validator.list_tenants(REPO_ROOT)
        # Portfolio consolidado: 5 tenants (incluindo clinica-vital).
        self.assertEqual(len(discovered), 5)
        for expected in ("clinica-vital", "estudio-flow", "marca-salao", "meu-salao", "multitrack-hub"):
            self.assertIn(expected, discovered)

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

        cv = tenant_validator.load_and_validate_tenant("clinica-vital", root=REPO_ROOT, strict=True)
        self.assertTrue(cv["ok"])
        self.assertEqual(cv["brandKit"]["monogram"], "CV")
        self.assertEqual(cv["brandKit"]["defaultPreset"], "saas-demo")
        self.assertFalse(cv["guardrails"]["audioPolicy"]["allowAudioTrack"])
        self.assertTrue(cv["guardrails"]["audioPolicy"]["requireSrt"])

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
        self.assertEqual(len(payload["tenants"]), 5)
        validated_ids = {entry["tenantId"] for entry in payload["tenants"]}
        self.assertTrue(
            {"clinica-vital", "estudio-flow", "marca-salao", "meu-salao", "multitrack-hub"}.issubset(validated_ids)
        )
        for entry in payload["tenants"]:
            self.assertTrue(entry["ok"], entry["tenantId"])

        with contextlib.redirect_stdout(io.StringIO()) as err_buf:
            rc_missing = tenant_validator.main(["--tenant", "inexistente", "--root", REPO_ROOT, "--json"])
        self.assertEqual(rc_missing, 1)
        err_payload = json.loads(err_buf.getvalue())
        self.assertFalse(err_payload["ok"])

    def _clinica_vital_brand_kit_in_memory(self) -> dict:
        """Copia literal do brand-kit clinico, sem depender da presença do diretorio do tenant."""
        return {
            "schemaVersion": 1,
            "tenantId": "clinica-vital",
            "brandName": "Clínica Vital",
            "displayTitle": "CLINICA VITAL",
            "monogram": "CV",
            "domain": "clinicavital.com.br",
            "url": "https://clinicavital.com.br",
            "tagline": "Organizacao de consultas e agenda clinica com clareza",
            "palette": {
                "primary": "#0EA5E9",
                "secondary": "#14B8A6",
                "accent": "#F59E0B",
                "background": "#0B1324",
                "surface": "#12203A",
                "textPrimary": "#F1F5F9",
                "textMuted": "#94A3B8",
                "rgb": {
                    "backgroundTop": [11, 19, 36],
                    "backgroundBottom": [18, 32, 58],
                    "headerBg": [7, 12, 24],
                    "cardBg": [18, 32, 58],
                    "cardHighlight": [28, 46, 78],
                    "primaryAccent": [14, 165, 233],
                    "secondaryAccent": [20, 184, 166],
                    "statusConfirmed": [20, 184, 166],
                    "statusWaiting": [245, 158, 11],
                    "statusDone": [148, 163, 184],
                    "textPrimary": [241, 245, 249],
                    "textMuted": [148, 163, 184],
                },
            },
            "typography": {"fontFamily": "Arial", "titleWeight": "bold", "bodyWeight": "regular"},
            "headerOverlay": {
                "enabled": True,
                "label": "CLINICA VITAL",
                "badgeText": "CONSULTAS & AGENDA",
                "bgColor": "#070C18",
                "textColor": "#F1F5F9",
                "height": 170,
            },
            "subtitleStyle": (
                "Fontname=Arial,Fontsize=12,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                "BackColour=&H80000000,Bold=1,Outline=2,Shadow=0,Alignment=2,MarginV=34"
            ),
            "defaultPreset": "saas-demo",
            "utmDefaults": {
                "utm_source": "instagram",
                "utm_medium": "reels",
                "utm_campaign_prefix": "cv",
            },
        }

    def _clinica_vital_guardrails_in_memory(self) -> dict:
        """Copia literal dos guardrails clinicos, sem depender da presença do diretorio do tenant."""
        return {
            "schemaVersion": 1,
            "tenantId": "clinica-vital",
            "forbiddenClaims": [
                "cura",
                "cura clínica",
                "cura clinica",
                "cura garantida",
                "promessa de cura",
                "tratamento garantido",
                "resultado garantido",
                "resultado estético garantido",
                "resultado estetico garantido",
                "resultado imediato",
                "tratamento sem dor garantido",
                "sem dor garantida",
                "diagnóstico online",
                "diagnostico online",
                "diagnóstico médico",
                "diagnostico medico",
                "diagnóstico odontológico",
                "diagnostico odontologico",
                "diagnóstico por mensagem",
                "diagnostico por mensagem",
                "antes e depois",
                "fotos antes e depois",
                "mensagem automática",
                "mensagem automatica",
                "mensagens automáticas",
                "mensagens automaticas",
                "mensagem automatizada",
                "mensagens automatizadas",
                "envio automático",
                "envio automatico",
                "confirmação automática",
                "confirmacao automatica",
                "whatsapp",
                "sms",
                "e-mail",
                "email",
                "lembrete automático",
                "lembrete automatico",
                "lembretes automáticos",
                "lembretes automaticos",
                "lembrete de 24 horas",
                "lembrete 24h",
                "24 horas",
                "24h",
                "redução de faltas",
                "reducao de faltas",
                "zero faltas",
                "zero absenteísmo",
                "zero absenteismo",
                "absenteísmo zero",
                "absenteismo zero",
                "aumento de faturamento",
                "aumento do faturamento",
                "faturamento garantido",
                "lucro garantido",
            ],
            "forbiddenUiElements": [
                "checkout",
                "pagamento",
                "cobrança",
                "cobranca",
                "a pagar",
                "cartão de crédito",
                "cartao de credito",
                "prontuário",
                "prontuario",
                "receita digital",
                "receita médica",
                "receita medica",
                "fotos antes e depois",
                "antes e depois",
                "meu salão",
                "meu salao",
                "e2e",
                "lorem ipsum",
            ],
            "routeRules": {
                "/avaliacao/[clinicId]": {
                    "surface": "public-booking",
                    "allowedResponsibilities": [
                        "identificacao-paciente-ficticia",
                        "escolha-procedimento",
                        "escolha-especialista",
                        "selecao-horario-avaliacao",
                        "confirmacao-avaliacao",
                    ],
                    "forbiddenResponsibilities": [
                        "tela-pagamento",
                        "cobranca-simulada",
                        "diagnostico-online",
                        "exposicao-prontuario",
                        "promessa-cura",
                        "envio-automatico-mensagem",
                    ],
                },
                "/gestor/consultas": {
                    "surface": "manager-agenda",
                    "allowedResponsibilities": [
                        "visualizacao-grade-consultas",
                        "filtro-especialista",
                        "filtro-status",
                        "busca-paciente",
                        "alteracao-manual-status",
                    ],
                    "forbiddenResponsibilities": [
                        "calculo-horarios-livres",
                        "exibicao-slots-disponiveis",
                        "tela-pagamento",
                        "prontuario-sensivel",
                        "namespace-e2e",
                    ],
                },
            },
            "audioPolicy": {
                "allowAudioTrack": False,
                "requireExternalNarration": True,
                "requireSrt": True,
                "ffmpegFlag": "-an",
            },
        }

    def test_08_clinica_vital_regulated_niche_contracts_in_memory(self) -> None:
        """Valida os contratos clinicos sem ler o diretorio do tenant (funciona com 4 tenants)."""
        brand_kit = self._clinica_vital_brand_kit_in_memory()
        gr = self._clinica_vital_guardrails_in_memory()

        self.assertEqual(tenant_validator.validate_brand_kit(brand_kit, REPO_ROOT), [])
        self.assertEqual(tenant_validator.validate_guardrails_contract(gr, REPO_ROOT), [])

        self.assertEqual(brand_kit["tenantId"], "clinica-vital")
        self.assertEqual(brand_kit["brandName"], "Clínica Vital")
        self.assertEqual(brand_kit["monogram"], "CV")
        self.assertEqual(brand_kit["defaultPreset"], "saas-demo")
        self.assertEqual(brand_kit["utmDefaults"]["utm_campaign_prefix"], "cv")

        # Termos vetados pela politica de nicho regulado (saude/estetica).
        for bad_text in (
            "antes e depois",
            "fotos antes e depois dos procedimentos",
            "cura garantida",
            "promessa de cura",
            "diagnostico online",
            "diagnóstico online em cinco minutos",
            "lembrete automatico",
            "lembrete automático de 24 horas",
            "mensagens automáticas por WhatsApp, SMS e e-mail",
            "resultado estético garantido",
            "aumento de faturamento comprovado",
        ):
            self.assertTrue(
                tenant_validator.validate_text_against_guardrails(bad_text, gr),
                f"clinica-vital deveria vetar: {bad_text}",
            )

        for bad_ui in (
            "checkout",
            "cobrança no aplicativo",
            "prontuário médico sensível",
            "receita digital",
            "fotos antes e depois",
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

        # Separacao auditavel entre a rota publica e a visao da recepcao.
        rules = gr["routeRules"]
        self.assertEqual(rules["/avaliacao/[clinicId]"]["surface"], "public-booking")
        self.assertEqual(rules["/gestor/consultas"]["surface"], "manager-agenda")
        self.assertIn("escolha-especialista", rules["/avaliacao/[clinicId]"]["allowedResponsibilities"])
        self.assertIn("diagnostico-online", rules["/avaliacao/[clinicId]"]["forbiddenResponsibilities"])
        self.assertIn("busca-paciente", rules["/gestor/consultas"]["allowedResponsibilities"])
        self.assertIn("alteracao-manual-status", rules["/gestor/consultas"]["allowedResponsibilities"])
        self.assertIn("calculo-horarios-livres", rules["/gestor/consultas"]["forbiddenResponsibilities"])

        # Politica de audio: nenhuma faixa sonora; SRT e narração externa obrigatorios.
        audio = gr["audioPolicy"]
        self.assertFalse(audio["allowAudioTrack"])
        self.assertTrue(audio["requireSrt"])
        self.assertTrue(audio["requireExternalNarration"])
        self.assertEqual(audio["ffmpegFlag"], "-an")

    def test_09_clinica_vital_contracts_and_campaigns_on_disk(self) -> None:
        """Valida o tenant e as campanhas no disco (clinica-vital integrado)."""
        if not (Path(REPO_ROOT) / "tenants" / "clinica-vital").exists():
            self.skipTest("tenant clinica-vital ainda nao integrado nesta worktree")

        loaded = tenant_validator.load_and_validate_tenant("clinica-vital", root=REPO_ROOT, strict=True)
        self.assertTrue(loaded["ok"])
        self.assertEqual(loaded["tenantId"], "clinica-vital")
        self.assertEqual(loaded["brandKit"]["brandName"], "Clínica Vital")
        self.assertEqual(loaded["brandKit"]["monogram"], "CV")
        self.assertEqual(loaded["brandKit"]["defaultPreset"], "saas-demo")
        self.assertFalse(loaded["guardrails"]["audioPolicy"]["allowAudioTrack"])
        self.assertTrue(loaded["guardrails"]["audioPolicy"]["requireSrt"])
        self.assertTrue(loaded["guardrails"]["audioPolicy"]["requireExternalNarration"])

        fixture = loaded["fixture"]
        self.assertEqual(fixture["tenantId"], "clinica-vital")
        self.assertEqual(len(fixture["profissionais"]), 4)
        self.assertEqual(len(fixture["servicos"]), 5)
        self.assertEqual(fixture["booking"]["rota"], "/avaliacao/clinica-vital-centro")
        self.assertEqual(fixture["agenda"]["visaoRota"], "/gestor/consultas")
        self.assertEqual(len(fixture["agenda"]["atendimentos"]), 6)
        statuses = {item["status"] for item in fixture["agenda"]["atendimentos"]}
        self.assertEqual(statuses, {"Confirmado", "Aguardando", "Concluído"})
        self.assertIn("Patricia Monteiro", {item["cliente"] for item in fixture["agenda"]["atendimentos"]})

        gr = loaded["guardrails"]
        campaigns = {}
        for name in (
            "camp-clinica-vital-002.json",
            "camp-saas-demo-clinica-vital-001.json",
            "camp-saas-demo-clinica-vital-002.json",
        ):
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

        # Campanha mista (public-booking + manager-agenda) do portfolio 14.
        mixed = campaigns["camp-clinica-vital-002"]
        mixed_surfaces = [scene["surface"] for scene in mixed["scenes"]]
        self.assertIn("public-booking", mixed_surfaces)
        self.assertIn("manager-agenda", mixed_surfaces)


if __name__ == "__main__":
    unittest.main()
