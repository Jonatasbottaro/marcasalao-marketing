"""Testes automatizados (unittest) para tools/campaign_calendar.py (v2).

Cobre obrigatoriamente:
  1. Contagem exata de 44 slots (33 Onda 1 + 11 Onda 2), 5 tenants e 11 campanhas.
  2. Anti-colisao: nenhum dia com mais de uma publicacao do mesmo tenant.
  3. Espacamento >= 48h entre publicacoes de canais da mesma campanha na Onda 1.
  4. Validade sintatica das 44 URLs (urllib.parse.urlparse) + presenca de
     utm_source/utm_medium/utm_campaign/utm_content.
  5. Unicidade de slotId e da combinacao (slug, canal, onda).
  6. autoPublish false e statusEditorial em 100% dos slots.
  7. Guardrails: hooks A/B (e textos operacionais) de todos os slots sem
     violacoes nos 5 tenants.
  8. Paridade exata JSON <-> CSV (44 registros, 20 colunas).
  9. Bloqueio quando frase proibida e injetada em hookVarianteB.
 10. CLI --start-date + --json com codigo 0 (e data invalida com codigo 2).

Extras: cobertura de canais por campanha, dias uteis/semanas, alternancia e
formatos da Onda 2, saida markdown operacional e idempotencia da regeneracao.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlparse

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import campaign_calendar
import tenant_validator

START_DATE = "2026-11-23"
WEEKS = 5
CALENDAR_JSON = os.path.join(REPO_ROOT, "04-legendas", "calendario-editorial.json")
CALENDAR_MD = os.path.join(REPO_ROOT, "04-legendas", "calendario-editorial.md")
UTM_CSV = os.path.join(REPO_ROOT, "04-legendas", "matriz-utm-consolidada.csv")

EXPECTED_CAMPAIGNS = {
    ("clinica-vital", "camp-saas-demo-clinica-vital-001"),
    ("clinica-vital", "camp-saas-demo-clinica-vital-002"),
    ("estudio-flow", "camp-saas-demo-estudio-flow-001"),
    ("estudio-flow", "camp-saas-demo-estudio-flow-002"),
    ("marca-salao", "camp-saas-demo-marca-salao-001"),
    ("marca-salao", "camp-saas-demo-ns001-agenda-001"),
    ("meu-salao", "camp-saas-demo-meu-salao-001"),
    ("meu-salao", "camp-saas-demo-meu-salao-002"),
    ("multitrack-hub", "camp-shorts-completo-multitrack-001"),
    ("multitrack-hub", "camp-shorts-rateios-002"),
    ("multitrack-hub", "camp-shorts-stems-workflow-003"),
}

EXPECTED_DOMAINS = {
    "clinica-vital": "clinicavital.com.br",
    "estudio-flow": "estudioflow.com.br",
    "marca-salao": "marcasalao.com.br",
    "meu-salao": "meusalao.com.br",
    "multitrack-hub": "multitrackhub.com.br",
}

SLOT_FIELDS = (
    "slotId",
    "onda",
    "semana",
    "dataSugerida",
    "diaSemana",
    "janelaHorarioBrt",
    "tenantId",
    "brandName",
    "slug",
    "preset",
    "audioPolicy",
    "canal",
    "formatoVideo",
    "hookVarianteA",
    "hookVarianteB",
    "utmParams",
    "utmUrl",
    "checklistPrePublicacao",
    "statusEditorial",
    "autoPublish",
)


class CampaignCalendarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = campaign_calendar.generate_calendar(
            START_DATE, weeks=WEEKS, root=REPO_ROOT
        )
        with open(CALENDAR_JSON, "r", encoding="utf-8") as handle:
            cls.calendar = json.load(handle)
        with open(CALENDAR_MD, "r", encoding="utf-8") as handle:
            cls.md = handle.read()
        with open(UTM_CSV, "r", encoding="utf-8", newline="") as handle:
            cls.csv_text = handle.read()
        cls.slots = cls.calendar["slots"]

    def _slot_datetime(self, slot: dict) -> datetime.datetime:
        hour, minute = slot["janelaHorarioBrt"].split("-")[0].split(":")
        return datetime.datetime.fromisoformat(slot["dataSugerida"]).replace(
            hour=int(hour), minute=int(minute)
        )

    # ------------------------------------------------------------------
    # 1. Contagem exata de slots e cobertura das 11 campanhas nos 5 tenants
    # ------------------------------------------------------------------
    def test_01_slot_counts_and_campaign_coverage(self) -> None:
        slots = self.slots
        self.assertEqual(len(slots), 44)
        self.assertEqual(self.calendar["totalSlots"], 44)
        self.assertEqual(self.calendar["totalCampaigns"], 11)
        self.assertEqual(self.calendar["totalTenants"], 5)
        self.assertEqual(self.calendar["metrics"]["byOnda"], {"1": 33, "2": 11})
        campaigns = {(s["tenantId"], s["slug"]) for s in slots}
        self.assertEqual(campaigns, EXPECTED_CAMPAIGNS)
        for tenant_id, slug in EXPECTED_CAMPAIGNS:
            with self.subTest(campaign=f"{tenant_id}/{slug}"):
                o1_channels = {
                    s["canal"]
                    for s in slots
                    if s["slug"] == slug and s["onda"] == 1
                }
                self.assertEqual(o1_channels, {"instagram", "youtube", "facebook"})
                o2_slots = [s for s in slots if s["slug"] == slug and s["onda"] == 2]
                self.assertEqual(len(o2_slots), 1)
        for slot in slots:
            with self.subTest(slot=slot["slotId"]):
                for field in SLOT_FIELDS:
                    self.assertIn(field, slot)

    # ------------------------------------------------------------------
    # 2. Anti-colisao: nenhum dia com mais de uma publicacao do mesmo tenant
    # ------------------------------------------------------------------
    def test_02_no_same_tenant_same_day(self) -> None:
        by_day: dict[str, list[dict]] = {}
        for slot in self.slots:
            by_day.setdefault(slot["dataSugerida"], []).append(slot)
        for day, day_slots in sorted(by_day.items()):
            with self.subTest(day=day):
                tenants = [s["tenantId"] for s in day_slots]
                self.assertEqual(
                    len(tenants),
                    len(set(tenants)),
                    f"colisao de tenant no dia {day}: {tenants}",
                )
                onda1_count = sum(1 for s in day_slots if s["onda"] == 1)
                onda2_count = sum(1 for s in day_slots if s["onda"] == 2)
                self.assertLessEqual(onda1_count, 2)
                self.assertLessEqual(onda2_count, 1)

    # ------------------------------------------------------------------
    # 3. Espacamento >= 48h entre canais da mesma campanha na Onda 1
    # ------------------------------------------------------------------
    def test_03_channel_spacing_min_48h(self) -> None:
        for _, slug in sorted(EXPECTED_CAMPAIGNS):
            o1_slots = sorted(
                (s for s in self.slots if s["slug"] == slug and s["onda"] == 1),
                key=self._slot_datetime,
            )
            with self.subTest(campaign=slug):
                self.assertEqual(len(o1_slots), 3)
                self.assertEqual(
                    [s["canal"] for s in o1_slots],
                    ["youtube", "instagram", "facebook"],
                )
                for first, second in zip(o1_slots, o1_slots[1:]):
                    gap_hours = (
                        self._slot_datetime(second) - self._slot_datetime(first)
                    ).total_seconds() / 3600
                    self.assertGreaterEqual(
                        gap_hours,
                        campaign_calendar.CHANNEL_SPACING_HOURS,
                        f"{slug}: {first['canal']} -> {second['canal']} = {gap_hours}h",
                    )

    # ------------------------------------------------------------------
    # 4. Validade sintatica e integridade das 32 URLs UTM
    # ------------------------------------------------------------------
    def test_04_utm_url_validity(self) -> None:
        urls = set()
        for slot in self.slots:
            with self.subTest(slot=slot["slotId"]):
                parsed = urlparse(slot["utmUrl"])
                self.assertEqual(parsed.scheme, "https")
                self.assertEqual(parsed.netloc, EXPECTED_DOMAINS[slot["tenantId"]])
                query = parse_qs(parsed.query)
                for param in (
                    "utm_source",
                    "utm_medium",
                    "utm_campaign",
                    "utm_content",
                ):
                    self.assertIn(param, query)
                self.assertEqual(slot["utmParams"]["utm_source"], slot["canal"])
                self.assertEqual(
                    slot["utmParams"]["utm_medium"], query["utm_medium"][0]
                )
                self.assertEqual(
                    slot["utmParams"]["utm_campaign"], query["utm_campaign"][0]
                )
                self.assertEqual(
                    slot["utmParams"]["utm_content"], query["utm_content"][0]
                )
                self.assertEqual(slot["utmParams"]["utm_campaign"], slot["slug"])
                if slot["onda"] == 1:
                    self.assertEqual(slot["utmParams"]["utm_content"], slot["tenantId"])
                    self.assertEqual(
                        slot["utmParams"]["utm_medium"],
                        campaign_calendar.CHANNEL_UTM_MEDIUM_ONDA1[slot["canal"]],
                    )
                else:
                    self.assertIn(
                        slot["utmParams"]["utm_content"],
                        ("repurpose-1x1", "repurpose-16x9"),
                    )
                    self.assertEqual(
                        slot["utmParams"]["utm_medium"],
                        campaign_calendar.CHANNEL_UTM_MEDIUM_ONDA2[slot["canal"]],
                    )
                urls.add(slot["utmUrl"])
        self.assertEqual(len(urls), 44)

    # ------------------------------------------------------------------
    # 5. Unicidade de slotId e da combinacao (slug, canal, onda)
    # ------------------------------------------------------------------
    def test_05_uniqueness_slotid_and_combos(self) -> None:
        slot_ids = [s["slotId"] for s in self.slots]
        self.assertEqual(len(set(slot_ids)), 44)
        self.assertEqual(slot_ids, [f"slot-{i:03d}" for i in range(1, 45)])
        combos = [(s["slug"], s["canal"], s["onda"]) for s in self.slots]
        self.assertEqual(len(set(combos)), 44)

    # ------------------------------------------------------------------
    # 6. autoPublish false e statusEditorial em 100% dos slots
    # ------------------------------------------------------------------
    def test_06_auto_publish_false_and_status_editorial(self) -> None:
        for slot in self.slots:
            with self.subTest(slot=slot["slotId"]):
                self.assertIs(slot["autoPublish"], False)
                self.assertEqual(slot["statusEditorial"], "aguardando_aprovacao_titular")
                self.assertGreaterEqual(len(slot["checklistPrePublicacao"]), 5)
        self.assertIs(self.calendar["autoPublish"], False)
        self.assertEqual(self.calendar["statusEditorial"], "aguardando_aprovacao_titular")

    # ------------------------------------------------------------------
    # 7. Guardrails: hooks A/B e textos operacionais sem violacoes
    # ------------------------------------------------------------------
    def test_07_guardrails_hooks_zero_violations(self) -> None:
        self.assertTrue(self.calendar["guardrailsAudited"])
        self.assertEqual(self.calendar["guardrailViolations"], [])
        guardrails_by_tenant: dict[str, dict] = {}
        for slot in self.slots:
            tenant_id = slot["tenantId"]
            if tenant_id not in guardrails_by_tenant:
                ctx = tenant_validator.load_and_validate_tenant(
                    tenant_id, root=REPO_ROOT, strict=True
                )
                guardrails_by_tenant[tenant_id] = ctx["guardrails"]
            with self.subTest(slot=slot["slotId"]):
                text = "\n".join(
                    [
                        slot["hookVarianteA"],
                        slot["hookVarianteB"],
                        slot["utmUrl"],
                        *slot["checklistPrePublicacao"],
                    ]
                )
                violations = tenant_validator.validate_text_against_guardrails(
                    text, guardrails_by_tenant[tenant_id], check_ui_elements=True
                )
                self.assertEqual(violations, [], f"{slot['slotId']}: {violations}")

    # ------------------------------------------------------------------
    # 8. Paridade exata JSON <-> CSV (32 registros, 20 colunas)
    # ------------------------------------------------------------------
    def test_08_json_csv_parity(self) -> None:
        import csv
        import io as io_module

        reader = csv.reader(io_module.StringIO(self.csv_text, newline=""))
        rows = list(reader)
        self.assertEqual(tuple(rows[0]), campaign_calendar.CSV_COLUMNS)
        self.assertEqual(len(rows), 45)
        self.assertNotIn("\r", self.csv_text)
        slots_by_id = {slot["slotId"]: slot for slot in self.slots}
        for row in rows[1:]:
            record = dict(zip(campaign_calendar.CSV_COLUMNS, row))
            slot = slots_by_id[record["slot_id"]]
            with self.subTest(slot=record["slot_id"]):
                expected = {
                    "slot_id": slot["slotId"],
                    "onda": str(slot["onda"]),
                    "semana": str(slot["semana"]),
                    "data_sugerida": slot["dataSugerida"],
                    "dia_semana": slot["diaSemana"],
                    "janela_brt": slot["janelaHorarioBrt"],
                    "tenant_id": slot["tenantId"],
                    "brand_name": slot["brandName"],
                    "slug": slot["slug"],
                    "preset": slot["preset"] or "",
                    "audio_policy": (
                        "com_faixa_de_audio"
                        if slot["audioPolicy"].get("allowAudioTrack")
                        else "-an"
                    ),
                    "canal": slot["canal"],
                    "formato_video": slot["formatoVideo"],
                    "utm_source": slot["utmParams"]["utm_source"],
                    "utm_medium": slot["utmParams"]["utm_medium"],
                    "utm_campaign": slot["utmParams"]["utm_campaign"],
                    "utm_content": slot["utmParams"]["utm_content"],
                    "utm_url": slot["utmUrl"],
                    "status_editorial": slot["statusEditorial"],
                    "auto_publish": json.dumps(slot["autoPublish"]),
                }
                self.assertEqual(record, expected)

    # ------------------------------------------------------------------
    # 9. Bloqueio quando frase proibida e injetada em hookVarianteB
    # ------------------------------------------------------------------
    def test_09_forbidden_phrase_blocks_generation(self) -> None:
        slug = "camp-saas-demo-marca-salao-001"
        for forbidden in (
            "Promessa proibida: whatsapp automático",
            "O melhor do meu salão em um só lugar",
        ):
            with self.subTest(forbidden=forbidden):
                with mock.patch.dict(
                    campaign_calendar.HOOK_VARIANTE_B, {slug: forbidden}
                ):
                    with self.assertRaises(campaign_calendar.CampaignCalendarError) as ctx:
                        campaign_calendar.build_editorial_calendar(
                            START_DATE, weeks=WEEKS, root=REPO_ROOT
                        )
                self.assertIn("GUARDRAIL_VIOLACAO", str(ctx.exception))

    # ------------------------------------------------------------------
    # 10. CLI: --start-date + --json com codigo 0; data invalida com 2;
    #     semanas insuficientes com 1
    # ------------------------------------------------------------------
    def test_10_cli_exit_codes(self) -> None:
        rc = campaign_calendar.main(
            ["--start-date", START_DATE, "--weeks", "5", "--json", "--root", REPO_ROOT]
        )
        self.assertEqual(rc, 0)
        rc_invalid = campaign_calendar.main(
            ["--start-date", "2026-13-45", "--weeks", "4", "--json", "--root", REPO_ROOT]
        )
        self.assertEqual(rc_invalid, 2)
        rc_weeks = campaign_calendar.main(
            ["--start-date", START_DATE, "--weeks", "2", "--json", "--root", REPO_ROOT]
        )
        self.assertEqual(rc_weeks, 1)

    # ------------------------------------------------------------------
    # 11. Dias uteis (seg-sab, nunca domingo), semanas e janelas por canal
    # ------------------------------------------------------------------
    def test_11_publishable_days_and_weeks(self) -> None:
        start = datetime.date.fromisoformat(START_DATE)
        for slot in self.slots:
            with self.subTest(slot=slot["slotId"]):
                date = datetime.date.fromisoformat(slot["dataSugerida"])
                self.assertNotEqual(slot["diaSemana"], "domingo")
                self.assertLessEqual(date, start + datetime.timedelta(days=7 * WEEKS - 1))
                self.assertEqual(
                    slot["diaSemana"],
                    campaign_calendar.WEEKDAY_NAMES[date.weekday()],
                )
                self.assertEqual(
                    slot["janelaHorarioBrt"],
                    campaign_calendar.CHANNEL_WINDOWS[slot["canal"]],
                )
                self.assertIn(slot["semana"], (1, 2, 3, 4, 5))
        slots_per_week: dict[int, int] = {}
        for slot in self.slots:
            slots_per_week[slot["semana"]] = slots_per_week.get(slot["semana"], 0) + 1
        self.assertEqual(slots_per_week, {1: 12, 2: 12, 3: 9, 4: 6, 5: 5})
        self.assertEqual(self.calendar["onda1Weeks"], 3)
        self.assertEqual(self.calendar["weeks"], 5)

    # ------------------------------------------------------------------
    # 12. Onda 2: alternancia 1:1/16:9 pela ordem de slug, 1 slot/dia
    # ------------------------------------------------------------------
    def test_12_onda2_alternation_and_formats(self) -> None:
        o2_slots = sorted(
            (s for s in self.slots if s["onda"] == 2), key=lambda s: s["dataSugerida"]
        )
        self.assertEqual(len(o2_slots), 11)
        days = [s["dataSugerida"] for s in o2_slots]
        self.assertEqual(len(days), len(set(days)))
        ordered_slugs = sorted({s["slug"] for s in self.slots})
        for index, slot in enumerate(o2_slots):
            with self.subTest(slot=slot["slotId"]):
                expected_canal = "instagram" if index % 2 == 0 else "youtube"
                self.assertEqual(slot["canal"], expected_canal)
                formato, utm_content = campaign_calendar.ONDA2_FORMATS[expected_canal]
                self.assertEqual(slot["formatoVideo"], formato)
                self.assertEqual(slot["utmParams"]["utm_content"], utm_content)
                self.assertEqual(ordered_slugs.index(slot["slug"]), index)
        formats = [s["formatoVideo"] for s in self.slots]
        self.assertEqual(formats.count("9:16"), 33)
        self.assertEqual(formats.count("1:1"), 6)
        self.assertEqual(formats.count("16:9"), 5)
        self.assertEqual(
            self.calendar["metrics"]["byFormatoVideo"], {"9:16": 33, "1:1": 6, "16:9": 5}
        )

    # ------------------------------------------------------------------
    # 13. Saida markdown operacional
    # ------------------------------------------------------------------
    def test_13_markdown_operational_outputs(self) -> None:
        self.assertIn("## 1. Resumo executivo", self.md)
        self.assertIn("### 1.1 Por tenant", self.md)
        self.assertIn("### 1.2 Por canal", self.md)
        self.assertIn("## 2. Cronograma completo (5 semanas)", self.md)
        self.assertIn("### Semana 1 (2026-11-23 a 2026-11-28)", self.md)
        self.assertIn("### Semana 4 (2026-12-14 a 2026-12-19)", self.md)
        self.assertIn("### Semana 5 (2026-12-21 a 2026-12-25)", self.md)
        self.assertIn("## 3. Checklist de operação manual pré-publicação", self.md)
        self.assertIn("## 4. Referência rápida de URLs UTM (por campanha)", self.md)
        for tenant_id in (
            "clinica-vital",
            "estudio-flow",
            "marca-salao",
            "meu-salao",
            "multitrack-hub",
        ):
            self.assertIn(f"`{tenant_id}`", self.md)
        self.assertIn("Locução externa", self.md)
        self.assertIn("derivatives.json", self.md)
        self.assertIn("analytics", self.md)
        self.assertIn("aguardando_aprovacao_titular", self.md)
        self.assertIn("autoPublish: false", self.md)
        self.assertIn("Conheça o sistema — link na bio", self.md)
        for slot in self.slots:
            self.assertIn(slot["utmUrl"], self.md)
            self.assertIn(slot["slotId"], self.md)
            self.assertIn(slot["hookVarianteA"], self.md)
            self.assertIn(slot["hookVarianteB"], self.md)

    # ------------------------------------------------------------------
    # 14. Idempotencia: regeneracao produz bytes identicos
    # ------------------------------------------------------------------
    def test_14_idempotent_regeneration(self) -> None:
        before = {
            "json": open(CALENDAR_JSON, "r", encoding="utf-8", newline="").read(),
            "md": open(CALENDAR_MD, "r", encoding="utf-8", newline="").read(),
            "csv": open(UTM_CSV, "r", encoding="utf-8", newline="").read(),
        }
        result = campaign_calendar.generate_calendar(
            START_DATE, weeks=WEEKS, root=REPO_ROOT
        )
        after = {
            "json": open(CALENDAR_JSON, "r", encoding="utf-8", newline="").read(),
            "md": open(CALENDAR_MD, "r", encoding="utf-8", newline="").read(),
            "csv": open(UTM_CSV, "r", encoding="utf-8", newline="").read(),
        }
        self.assertEqual(before, after)
        for kind in ("json", "md", "csv"):
            self.assertEqual(
                result["outputs"][kind]["sha256"],
                self.result["outputs"][kind]["sha256"],
            )


if __name__ == "__main__":
    unittest.main()
