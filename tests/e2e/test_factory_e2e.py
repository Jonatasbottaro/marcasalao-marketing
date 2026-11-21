"""E2E determinístico da fábrica — seis etapas, um único checkout-sandbox.

Cadeia validada (na ordem em que a operação real acontece):

    1. validação de tenant (``tenant_validator``)
    2. formatação SRT para <= 48 caracteres (``srt_formatter``)
    3. QA editorial com 7 lentes (``editorial_qa``)
    4. aprovação via CLI (``approval_cli decide``)
    5. geração do pacote de postagem manual (``factory_cli handoff``)
    6. auditoria de release strict (``release_audit``)

Invariantes verificados ao longo da cadeia: `autoPublish: false` em todos os
pacotes, nenhum `.mp4`/`.wav` gerado fora de `.workspace/archives/`, UTF-8 e
separadores portáteis. A suíte roda idêntica em Windows e Ubuntu com
``python -m unittest discover -s tests/e2e -v``.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _support as support  # noqa: E402

TOOLS_DIR = support.TOOLS_DIR
sys.path.insert(0, TOOLS_DIR)

import approval_cli  # noqa: E402
import editorial_qa  # noqa: E402
import factory_cli  # noqa: E402
import release_audit  # noqa: E402
import review_dashboard  # noqa: E402
import srt_formatter  # noqa: E402
import tenant_validator  # noqa: E402


class FactoryEndToEndTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        method = self.id().rsplit(".", 1)[-1]
        self.root = support.build_sandbox(method.replace("test_", "") or "cenario")
        self.approvals_rel = support.APPROVALS_REL

    def tearDown(self) -> None:
        support.force_rmtree(self.root)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _run_cli(self, argv: list[str]) -> tuple[int, str]:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = approval_cli.main(argv + ["--root", self.root, "--json"])
        return code, stdout.getvalue()

    def _approve(self, *, tenant: str = support.TENANT, slug: str = support.SLUG) -> dict:
        code, output = self._run_cli([
            "decide",
            "--tenant", tenant,
            "--campaign", slug,
            "--decision", "aprovado",
            "--reviewer", "Titular E2E",
            "--external-audio-checked",
            "--approvals-file", self.approvals_rel,
        ])
        self.assertEqual(code, 0, output)
        return json.loads(output)

    def _qa_codes(self, result: dict, check_id: str) -> list[str]:
        for check in result["checks"]:
            if check["id"] == check_id:
                return [problem["code"] for problem in check["problems"]]
        self.fail(f"lente ausente: {check_id}")

    # ------------------------------------------------------------------
    # 1. Fluxo completo
    # ------------------------------------------------------------------
    def test_01_fluxo_completo_seis_etapas(self) -> None:
        root = self.root
        steps: list[str] = []

        # Etapa 1 — validação de tenant -------------------------------------
        tenants = tenant_validator.list_tenants(root)
        self.assertGreaterEqual(len(tenants), 4)
        for tenant_id in tenants:
            ctx = tenant_validator.load_and_validate_tenant(
                tenant_id, root=root, strict=True
            )
            self.assertTrue(ctx["ok"])
        steps.append(f"tenant_validator:{len(tenants)}/ok")

        # Etapa 2 — formatação SRT ------------------------------------------
        srt_path = support.inject_long_srt(root)
        self.assertGreater(support.srt_max_line(srt_path), srt_formatter.DEFAULT_MAX_CHARS)
        before = editorial_qa.run_editorial_qa(root=root, tenant=support.TENANT)
        self.assertIn("SRT_LINHA_LONGA", self._qa_codes(before, "legibilidade_mobile"))

        formatted = srt_formatter.format_delivery_srts(
            root, tenant=support.TENANT, slug=support.SLUG
        )
        self.assertEqual(formatted["totals"]["changed"], 1, formatted)
        self.assertGreater(formatted["totals"]["longLinesBefore"], 0)
        self.assertEqual(formatted["totals"]["longLinesAfter"], 0)
        self.assertEqual(
            support.srt_max_line(srt_path), srt_formatter.DEFAULT_MAX_CHARS
        )
        self.assertEqual(
            srt_formatter.format_delivery_srts(
                root, tenant=support.TENANT, slug=support.SLUG, dry_run=True
            )["totals"]["changed"],
            0,
            "a formatação deve ser idempotente",
        )
        support.sync_checklist_srt(root)
        review_dashboard.build_portal(root=root)
        steps.append("srt_formatter:48chars/manifesto/checklist/portal")

        # Etapa 3 — QA editorial (7 lentes) ---------------------------------
        qa = editorial_qa.run_editorial_qa(root=root, strict=True)
        self.assertEqual([c["id"] for c in qa["checks"]], list(editorial_qa.CHECK_IDS))
        self.assertEqual(len(qa["checks"]), 7)
        self.assertEqual(qa["summary"]["problems"], {"errors": 0, "warnings": 0})
        self.assertTrue(qa["ok"], qa["summary"])
        steps.append("editorial_qa:7/7")

        # Etapa 4 — aprovação via CLI ---------------------------------------
        decision = self._approve()
        self.assertEqual(decision["decision"], "aprovado")
        self.assertFalse(decision["autoPublish"])
        self.assertTrue(decision["campaign"]["locucaoExternaConferida"])
        code, output = self._run_cli([
            "status", "--approvals-file", self.approvals_rel,
        ])
        self.assertEqual(code, 0, output)
        status = json.loads(output)
        self.assertEqual(status["summary"]["aprovadas"], 1)
        self.assertEqual(status["summary"]["total"], len(qa["campaigns"]))
        steps.append("approval_cli:1 aprovada")

        # Etapa 5 — pacote de postagem manual -------------------------------
        handoff = factory_cli.cmd_handoff(
            root=root,
            all_approved=True,
            approvals_file=self.approvals_rel,
            output_dir=support.HANDOFF_REL,
        )
        self.assertTrue(handoff["ok"], handoff)
        self.assertIs(handoff["autoPublish"], False)
        bundle = handoff["handoff"]
        self.assertGreater(bundle.get("bundledSlots", 0), 0)
        self.assertIs(bundle.get("autoPublish"), False)
        folders = [
            support._abs(root, item["directory"])
            for item in bundle.get("slots", [])
            if isinstance(item, dict) and item.get("directory")
        ]
        self.assertEqual(len(folders), bundle["bundledSlots"])
        self.assertTrue(folders, "o handoff deve produzir diretórios de slot")
        for folder in folders:
            for name in ("POSTAGEM-MANUAL.md", "copy-pronta.txt", "handoff-manifest.json"):
                self.assertTrue(
                    os.path.isfile(support.render_local.fs_path(os.path.join(folder, name))),
                    f"{name} ausente em {folder}",
                )
            manifest = support.read_json(os.path.join(folder, "handoff-manifest.json"))
            self.assertIs(manifest.get("autoPublish"), False)
        steps.append(f"handoff:{bundle.get('bundledSlots')} slots/autoPublish=false")

        # Etapa 6 — auditoria de release ------------------------------------
        audit = release_audit.run_release_audit(root=root, strict=True)
        self.assertTrue(audit["ok"], audit["summary"])
        self.assertEqual(audit["summary"]["domains"], {"ok": 7, "warn": 0, "fail": 0})
        self.assertEqual(audit["summary"]["problems"], {"errors": 0, "warnings": 0})
        steps.append("release_audit:7/7 strict")

        # Invariante final de mídia -----------------------------------------
        self.assertEqual(support.find_media(root), [])

        print("E2E " + " -> ".join(steps))

    # ------------------------------------------------------------------
    # 2. Fail-closed do handoff sem aprovação
    # ------------------------------------------------------------------
    def test_02_handoff_sem_aprovacao_nao_empacota(self) -> None:
        handoff = factory_cli.cmd_handoff(
            root=self.root,
            all_approved=True,
            approvals_file=self.approvals_rel,
            output_dir=support.HANDOFF_REL,
        )
        self.assertTrue(handoff["ok"], handoff)
        self.assertEqual(handoff["handoff"].get("bundledSlots"), 0)
        self.assertIn(
            "NENHUMA_CAMPANHA_APROVADA_PELO_TITULAR",
            str(handoff["handoff"].get("reason")),
        )
        self.assertIs(handoff["autoPublish"], False)
        self.assertEqual(support.find_media(self.root), [])

    # ------------------------------------------------------------------
    # 3. Guard de mídia: só .workspace/archives/ é permitido
    # ------------------------------------------------------------------
    def test_03_guard_midia_fora_do_arquivo(self) -> None:
        # Nenhuma mídia no checkout inicial.
        self.assertEqual(support.find_media(self.root), [])
        self.assertEqual(support.media_outside_workspace(self.root), [])

        allowed = support._abs(self.root, ".workspace/archives/e2e/prova.mp4")
        support.write_text(allowed, "mp4 sintetico")
        self.assertEqual(support.find_media(self.root), [".workspace/archives/e2e/prova.mp4"])
        self.assertEqual(support.media_outside_workspace(self.root), [])

        staging = support._abs(self.root, ".workspace/tmp/prova.wav")
        support.write_text(staging, "wav sintetico")
        self.assertIn(".workspace/tmp/prova.wav", support.find_media(self.root))
        self.assertEqual(support.media_outside_workspace(self.root), [])

        forbidden = support._abs(self.root, "02-reels-shorts/deliveries/prova.wav")
        support.write_text(forbidden, "wav indevido")
        self.assertEqual(
            support.media_outside_workspace(self.root),
            ["02-reels-shorts/deliveries/prova.wav"],
        )

    # ------------------------------------------------------------------
    # 4. Determinismo da cadeia completa
    # ------------------------------------------------------------------
    def test_04_cadeia_deterministica(self) -> None:
        first = editorial_qa.run_editorial_qa(root=self.root, strict=True)
        second = editorial_qa.run_editorial_qa(root=self.root, strict=True)
        self.assertEqual(first, second)

        before = support.find_media(self.root)
        self._approve()
        after = support.find_media(self.root)
        self.assertEqual(before, after)
        self.assertEqual(before, [])
