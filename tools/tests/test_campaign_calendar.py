"""Testes automatizados (unittest) para tools/campaign_calendar.py.

Cobre obrigatoriamente:
  1. Distribuicao intercalada sem colisao de tenant no mesmo dia.
  2. Contagem de slots: 8 campanhas x 3 canais = 24 entradas.
  3. autoPublish false e statusEditorial em todos os slots.
  4. Integridade das URLs UTM (dominio por tenant, parametros por canal,
     utm_campaign=slug, utm_content=tenantId, unicidade e coincidencia com
     os pacotes gerados por tools/publish_pack.py).
  5. Auditoria de guardrails com zero violacoes sobre as entradas.
  6. Saida markdown operacional (cronograma, checklist com locucao externa
     e matriz consolidada das 24 URLs).
  7. CLI com --start-date/--json (codigo 0) e data invalida (codigo 2).
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import campaign_calendar
import tenant_validator

START_DATE = "2026-11-23"
CALENDAR_JSON = os.path.join(REPO_ROOT, "04-legendas", "calendario-editorial.json")
CALENDAR_MD = os.path.join(REPO_ROOT, "04-legendas", "calendario-editorial.md")
PUBLICACAO_ROOT = os.path.join(REPO_ROOT, "04-legendas", "pacotes-publicacao")

EXPECTED_CAMPAIGNS = {
    ("estudio-flow", "camp-saas-demo-estudio-flow-001"),
    ("marca-salao", "camp-saas-demo-marca-salao-001"),
    ("marca-salao", "camp-saas-demo-ns001-agenda-001"),
    ("meu-salao", "camp-saas-demo-meu-salao-001"),
    ("meu-salao", "camp-saas-demo-meu-salao-002"),
    ("multitrack-hub", "camp-shorts-completo-multitrack-001"),
    ("multitrack-hub", "camp-shorts-rateios-002"),
    ("multitrack-hub", "camp-shorts-stems-workflow-003"),
}

EXPECTED_DOMAINS = {
    "estudio-flow": "estudioflow.com.br",
    "marca-salao": "marcasalao.com.br",
    "meu-salao": "meusalao.com.br",
    "multitrack-hub": "multitrackhub.com.br",
}

CHANNEL_FILES = {
    "instagram": "instagram-reels.md",
    "youtube": "youtube-shorts.md",
    "facebook": "facebook-reels.md",
}

SLOT_FIELDS = (
    "slotId",
    "dataSugerida",
    "janelaHorario",
    "tenantId",
    "brandName",
    "slug",
    "canal",
    "formato",
    "audioPolicy",
    "utmUrl",
    "statusEditorial",
    "autoPublish",
)


class CampaignCalendarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = campaign_calendar.generate_calendar(START_DATE, root=REPO_ROOT)
        with open(CALENDAR_JSON, "r", encoding="utf-8") as handle:
            cls.calendar = json.load(handle)
        with open(CALENDAR_MD, "r", encoding="utf-8") as handle:
            cls.md = handle.read()

    # ------------------------------------------------------------------
    # 1/2. Contagem de slots e cobertura das 8 campanhas nos 3 canais
    # ------------------------------------------------------------------
    def test_01_slot_count_and_campaign_coverage(self) -> None:
        slots = self.calendar["slots"]
        self.assertEqual(len(slots), 24)
        self.assertEqual(self.calendar["totalSlots"], 24)
        self.assertEqual(self.calendar["totalCampaigns"], 8)
        campaigns = {(s["tenantId"], s["slug"]) for s in slots}
        self.assertEqual(campaigns, EXPECTED_CAMPAIGNS)
        for tenant_id, slug in EXPECTED_CAMPAIGNS:
            with self.subTest(campaign=f"{tenant_id}/{slug}"):
                channels = {
                    s["canal"]
                    for s in slots
                    if s["tenantId"] == tenant_id and s["slug"] == slug
                }
                self.assertEqual(channels, {"instagram", "youtube", "facebook"})
        for slot in slots:
            with self.subTest(slot=slot["slotId"]):
                for field in SLOT_FIELDS:
                    self.assertIn(field, slot)

    def test_02_no_same_tenant_collision_same_day(self) -> None:
        by_day: dict[str, set] = {}
        for slot in self.calendar["slots"]:
            by_day.setdefault(slot["dataSugerida"], set()).add(
                (slot["tenantId"], slot["slug"])
            )
        self.assertEqual(len(by_day), 4)
        for day, campaigns in sorted(by_day.items()):
            with self.subTest(day=day):
                tenants = [tenant for tenant, _ in campaigns]
                self.assertEqual(
                    len(tenants),
                    len(set(tenants)),
                    f"colisao de tenant no mesmo dia: {sorted(campaigns)}",
                )
                self.assertEqual(len(campaigns), campaign_calendar.CAMPAIGNS_PER_DAY)

    # ------------------------------------------------------------------
    # 3. autoPublish false e statusEditorial em todos os slots
    # ------------------------------------------------------------------
    def test_03_auto_publish_false_and_status_editorial(self) -> None:
        for slot in self.calendar["slots"]:
            with self.subTest(slot=slot["slotId"]):
                self.assertIs(slot["autoPublish"], False)
                self.assertEqual(slot["statusEditorial"], "aguardando_aprovacao_titular")
        self.assertIs(self.calendar["autoPublish"], False)
        self.assertEqual(self.calendar["statusEditorial"], "aguardando_aprovacao_titular")

    # ------------------------------------------------------------------
    # 4. Integridade das URLs UTM
    # ------------------------------------------------------------------
    def test_04_utm_url_integrity(self) -> None:
        urls = set()
        for slot in self.calendar["slots"]:
            with self.subTest(slot=slot["slotId"]):
                source, medium = campaign_calendar.CHANNEL_META[slot["canal"]]["utm"]
                expected = (
                    f"https://{EXPECTED_DOMAINS[slot['tenantId']]}/"
                    f"?utm_source={source}&utm_medium={medium}"
                    f"&utm_campaign={slot['slug']}&utm_content={slot['tenantId']}"
                )
                self.assertEqual(slot["utmUrl"], expected)
                pack_md = os.path.join(
                    PUBLICACAO_ROOT,
                    slot["tenantId"],
                    slot["slug"],
                    CHANNEL_FILES[slot["canal"]],
                )
                with open(pack_md, "r", encoding="utf-8") as handle:
                    pack_text = handle.read()
                self.assertIn(
                    slot["utmUrl"],
                    pack_text,
                    f"URL ausente no pacote {CHANNEL_FILES[slot['canal']]} "
                    f"de {slot['tenantId']}/{slot['slug']}",
                )
                urls.add(slot["utmUrl"])
        self.assertEqual(len(urls), 24)


    # ------------------------------------------------------------------
    # 5. Datas, janelas horarias e ordem cronologica dos slots
    # ------------------------------------------------------------------
    def test_05_dates_windows_and_slot_order(self) -> None:
        slots = self.calendar["slots"]
        start = datetime.date.fromisoformat(START_DATE)
        dates = sorted({s["dataSugerida"] for s in slots})
        self.assertEqual(
            dates,
            [(start + datetime.timedelta(days=i)).isoformat() for i in range(4)],
        )
        self.assertEqual(self.calendar["startDate"], START_DATE)
        self.assertEqual(self.calendar["endDate"], dates[-1])
        self.assertEqual(
            [s["slotId"] for s in slots],
            [f"slot-{i:03d}" for i in range(1, 25)],
        )
        for slot in slots:
            with self.subTest(slot=slot["slotId"]):
                meta = campaign_calendar.CHANNEL_META[slot["canal"]]
                self.assertEqual(slot["janelaHorario"], meta["janela"])
                self.assertEqual(slot["formato"], meta["formato"])

    # ------------------------------------------------------------------
    # 6. Auditoria de guardrails com zero violacoes
    # ------------------------------------------------------------------
    def test_06_guardrails_audit_zero_violations(self) -> None:
        self.assertTrue(self.calendar["guardrailsAudited"])
        self.assertEqual(self.calendar["guardrailViolations"], [])
        self.assertTrue(self.result["guardrailsAudited"])
        self.assertEqual(self.result["guardrailViolations"], [])
        guardrails_by_tenant: dict[str, dict] = {}
        for slot in self.calendar["slots"]:
            tenant_id = slot["tenantId"]
            if tenant_id not in guardrails_by_tenant:
                ctx = tenant_validator.load_and_validate_tenant(
                    tenant_id, root=REPO_ROOT, strict=True
                )
                guardrails_by_tenant[tenant_id] = ctx["guardrails"]
            meta = campaign_calendar.CHANNEL_META[slot["canal"]]
            text = "\n".join([slot["brandName"], meta["cta"], slot["utmUrl"]])
            violations = tenant_validator.validate_text_against_guardrails(
                text, guardrails_by_tenant[tenant_id], check_ui_elements=True
            )
            self.assertEqual(
                violations, [], f"{slot['slotId']}: {violations}"
            )

    # ------------------------------------------------------------------
    # 7. Saida markdown operacional
    # ------------------------------------------------------------------
    def test_07_markdown_operational_outputs(self) -> None:
        self.assertGreater(len(self.md), 0)
        for slot in self.calendar["slots"]:
            self.assertIn(slot["utmUrl"], self.md)
        self.assertIn("Locução externa", self.md)
        for tenant_id in ("estudio-flow", "marca-salao", "meu-salao"):
            self.assertIn(f"`{tenant_id}`", self.md)
        self.assertIn("autoPublish", self.md)
        self.assertIn("aguardando_aprovacao_titular", self.md)
        self.assertIn("checklist-publicacao.json", self.md)
        self.assertIn("Matriz UTM consolidada", self.md)

    # ------------------------------------------------------------------
    # 8. CLI: saida JSON com codigo 0 e data invalida com codigo 2
    # ------------------------------------------------------------------
    def test_08_cli_exit_codes(self) -> None:
        rc = campaign_calendar.main(
            ["--start-date", START_DATE, "--json", "--root", REPO_ROOT]
        )
        self.assertEqual(rc, 0)
        rc_invalid = campaign_calendar.main(
            ["--start-date", "2026-13-45", "--json", "--root", REPO_ROOT]
        )
        self.assertEqual(rc_invalid, 2)


if __name__ == "__main__":
    unittest.main()
