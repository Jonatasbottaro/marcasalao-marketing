"""Testes automatizados (unittest) para tools/handoff_bundler.py (Etapa 5B - Agente 2).

Cobre (>= 10 casos):
  1. Trava de aprovacao humana: sem aprovacoes devolve o JSON limpo
     {"ok": true, "bundledSlots": 0, "reason": "NENHUMA_CAMPANHA_APROVADA_PELO_TITULAR"}.
  2. Compatibilidade dos schemas v1 (aprovada: true) e v2 (decisao: "aprovado").
  3. Filtragem seletiva: SOMENTE campanhas explicitamente aprovadas entram.
  4. Roteamento de midia: Onda 1 (9:16, <slug>.mp4) e Onda 2 (1:1 / 16:9,
     <slug>-1x1.mp4 / <slug>-16x9.mp4) com cover.png e hash conferido.
  5. --include-pending inclui slots nao aprovados com selo PREVIA_NAO_APROVADA.
  6. Filtro --date.
  7. POSTAGEM-MANUAL.md + copy-pronta.txt + handoff-manifest.json com
     autoPublish: false e checklist de 5 passos.
  8. Alerta de locucao externa em tenants -an vs multitrack-hub (AAC).
  9. Contencao de path (slot malicioso, output fora da raiz, aprovacoes fora).
 10. CLI --json termina com codigo 0 e JSON valido.
 11. Indice consolidado INDICE-OPERACIONAL.md + indice-operacional.json.

Tudo roda em uma raiz temporaria (tempfile) construida no setUpClass.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import handoff_bundler
import publish_pack
import render_local

CAMPAIGNS = {
    "estudio-flow": "camp-saas-demo-estudio-flow-001",
    "marca-salao": "camp-saas-demo-marca-salao-001",
    "meu-salao": "camp-saas-demo-meu-salao-001",
    "multitrack-hub": "camp-shorts-completo-multitrack-001",
}
AN_TENANTS = ("estudio-flow", "marca-salao", "meu-salao")
AUDIO_POLICY = {
    tenant: {
        "allowAudioTrack": False,
        "requireExternalNarration": True,
        "requireSrt": True,
        "ffmpegFlag": "-an",
    }
    for tenant in AN_TENANTS
}
AUDIO_POLICY["multitrack-hub"] = {
    "allowAudioTrack": True,
    "requireExternalNarration": False,
    "requireSrt": True,
}
DOMAINS = {
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


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fake_bytes(seed: str) -> bytes:
    return b"\x00\x00\x00\x18ftypmp42" + seed.encode("utf-8") * 4


def _utm(slot: dict) -> str:
    tenant = slot["tenantId"]
    domain = DOMAINS[tenant]
    canal = slot["canal"]
    formato = slot["formatoVideo"]
    if formato == "1:1":
        source, medium, content = "instagram", "feed", "repurpose-1x1"
    elif formato == "16:9":
        source, medium, content = "youtube", "video", "repurpose-16x9"
    elif canal == "youtube":
        source, medium, content = "youtube", "shorts", tenant
    elif canal == "instagram":
        source, medium, content = "instagram", "reels", tenant
    else:
        source, medium, content = "facebook", "reels", tenant
    return (
        f"https://{domain}/?utm_source={source}&utm_medium={medium}"
        f"&utm_campaign={slot['slug']}&utm_content={content}"
    )


def _slot(
    slot_id: str,
    tenant: str,
    canal: str,
    data: str,
    formato: str = "9:16",
    onda: int = 1,
) -> dict:
    slot = {
        "slotId": slot_id,
        "onda": onda,
        "semana": 1,
        "dataSugerida": data,
        "diaSemana": "segunda-feira",
        "janelaHorarioBrt": {
            "youtube": "12:00-13:00",
            "instagram": "18:30-19:30",
            "facebook": "20:00-21:00",
        }[canal],
        "tenantId": tenant,
        "brandName": tenant.replace("-", " ").title(),
        "slug": CAMPAIGNS[tenant],
        "preset": "saas-demo" if tenant != "multitrack-hub" else "shorts-completo",
        "audioPolicy": dict(AUDIO_POLICY[tenant]),
        "canal": canal,
        "formatoVideo": formato,
        "utmParams": {},
        "statusEditorial": "aguardando_aprovacao_titular",
        "autoPublish": False,
    }
    url = _utm(slot)
    slot["utmUrl"] = url
    slot["utmParams"] = dict(
        part.split("=", 1) for part in url.split("?", 1)[1].split("&")
    )
    return slot


def _write_json(path: str, doc: dict) -> None:
    os.makedirs(render_local.fs_path(os.path.dirname(path)), exist_ok=True)
    with open(render_local.fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(doc, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _read_text(path: str) -> str:
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        return handle.read()


def _read_json(path: str) -> dict:
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _build_fixture(root: str) -> None:
    for name in ("tenants", "schemas"):
        shutil.copytree(
            render_local.fs_path(os.path.join(REPO_ROOT, name)),
            render_local.fs_path(os.path.join(root, name)),
        )

    calendar = {
        "schemaVersion": 2,
        "generatedBy": "tools/tests/test_handoff_bundler.py",
        "statusEditorial": "aguardando_aprovacao_titular",
        "autoPublish": False,
        "slots": [
            _slot("slot-101", "marca-salao", "youtube", "2026-11-23"),
            _slot("slot-102", "marca-salao", "instagram", "2026-11-25"),
            _slot("slot-103", "meu-salao", "youtube", "2026-11-24"),
            _slot("slot-104", "multitrack-hub", "youtube", "2026-11-24"),
            _slot("slot-105", "estudio-flow", "instagram", "2026-12-07", "1:1", 2),
            _slot("slot-106", "marca-salao", "youtube", "2026-12-08", "16:9", 2),
        ],
    }
    _write_json(os.path.join(root, "04-legendas", "calendario-editorial.json"), calendar)

    for tenant, slug in CAMPAIGNS.items():
        # Pacote social versionado (copy real, auditada pelo publish_pack).
        pkg_dst = os.path.join(root, "04-legendas", "pacotes-publicacao", tenant, slug)
        os.makedirs(render_local.fs_path(pkg_dst), exist_ok=True)
        for filename in CHANNEL_FILES.values():
            src = os.path.join(REPO_ROOT, "04-legendas", "pacotes-publicacao", tenant, slug, filename)
            shutil.copyfile(render_local.fs_path(src), render_local.fs_path(os.path.join(pkg_dst, filename)))

        # Entrega: manifesto e derivados reais, com hashes reescritos para a
        # midia simulada em .workspace/archives.
        src_dir = os.path.join(REPO_ROOT, "02-reels-shorts", "deliveries", tenant, slug)
        dst_dir = os.path.join(root, "02-reels-shorts", "deliveries", tenant, slug)
        os.makedirs(render_local.fs_path(dst_dir), exist_ok=True)
        manifest = _read_json(os.path.join(src_dir, "manifest.json"))
        derivatives = _read_json(os.path.join(src_dir, "derivatives.json"))

        archives = os.path.join(root, ".workspace", "archives", slug)
        primary_rel = f".workspace/archives/{slug}/{slug}.mp4"
        primary_abs = os.path.join(root, *primary_rel.split("/"))
        os.makedirs(render_local.fs_path(os.path.dirname(primary_abs)), exist_ok=True)
        primary_bytes = _fake_bytes(f"{slug}-9x16")
        with open(render_local.fs_path(primary_abs), "wb") as handle:
            handle.write(primary_bytes)
        video = manifest.setdefault("artifacts", {}).setdefault("video", {})
        video["archivePath"] = primary_rel
        video["sha256"] = _sha256(primary_bytes)
        video["bytes"] = len(primary_bytes)

        for variant in ("1x1", "16x9", "cover"):
            item = derivatives.get("derivatives", {}).get(variant)
            if not isinstance(item, dict):
                continue
            rel = str(item["path"])
            abs_path = os.path.join(root, *rel.split("/"))
            os.makedirs(render_local.fs_path(os.path.dirname(abs_path)), exist_ok=True)
            payload = _fake_bytes(f"{slug}-{variant}")
            with open(render_local.fs_path(abs_path), "wb") as handle:
                handle.write(payload)
            item["sha256"] = _sha256(payload)
            item["bytes"] = len(payload)

        _write_json(os.path.join(dst_dir, "manifest.json"), manifest)
        _write_json(os.path.join(dst_dir, "derivatives.json"), derivatives)

    os.makedirs(render_local.fs_path(os.path.join(root, ".workspace", "tmp")), exist_ok=True)


def _write_approvals(root: str, name: str, entries: list[dict]) -> str:
    rel = f".workspace/tmp/{name}.json"
    _write_json(os.path.join(root, *rel.split("/")), {"schemaVersion": 2, "campanhas": entries})
    return rel


class HandoffBundlerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="handoff-bundler-test-")
        cls.root = os.path.realpath(cls._tmp.name)
        _build_fixture(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _build(self, **kwargs) -> dict:
        kwargs.setdefault("root", self.root)
        return handoff_bundler.build_handoff_bundle(**kwargs)

    def _slot_dir(self, output: str, data: str, slot_id: str, tenant: str, canal: str) -> str:
        return os.path.join(self.root, output, data, f"{slot_id}-{tenant}-{canal}")

    # ------------------------------------------------------------------
    # 1. Trava de aprovacao humana
    # ------------------------------------------------------------------
    def test_01_no_approvals_returns_clean_json(self) -> None:
        res = self._build(
            approvals_file=".workspace/tmp/nao-existe.json",
            all_approved=True,
            output_dir=".workspace/handoff-t01",
        )
        self.assertEqual(
            res,
            {
                "ok": True,
                "bundledSlots": 0,
                "reason": "NENHUMA_CAMPANHA_APROVADA_PELO_TITULAR",
            },
        )
        self.assertFalse(os.path.isdir(render_local.fs_path(os.path.join(self.root, ".workspace", "handoff-t01"))))

        vazio = _write_approvals(self.root, "aprov-vazio", [])
        self.assertEqual(
            self._build(approvals_file=vazio, all_approved=True)["reason"],
            "NENHUMA_CAMPANHA_APROVADA_PELO_TITULAR",
        )

    # ------------------------------------------------------------------
    # 2. Compatibilidade de schema v1 e v2
    # ------------------------------------------------------------------
    def test_02_schema_v1_aprovada_true(self) -> None:
        rel = ".workspace/tmp/aprov-v1.json"
        _write_json(
            os.path.join(self.root, *rel.split("/")),
            {
                "schemaVersion": 1,
                "campanhas": [
                    {"tenantId": "marca-salao", "slug": CAMPAIGNS["marca-salao"], "aprovada": True}
                ],
            },
        )
        res = self._build(approvals_file=rel, all_approved=True, output_dir=".workspace/handoff-v1")
        self.assertEqual(res["bundledSlots"], 3)
        self.assertTrue(all(s["approvalStatus"] == "APROVADO_PELO_TITULAR" for s in res["slots"]))

    def test_03_schema_v2_decisao_aprovado(self) -> None:
        rel = _write_approvals(
            self.root,
            "aprov-v2",
            [
                {
                    "tenantId": "multitrack-hub",
                    "slug": CAMPAIGNS["multitrack-hub"],
                    "decisao": "aprovado",
                    "locucaoExternaConferida": False,
                }
            ],
        )
        res = self._build(approvals_file=rel, all_approved=True, output_dir=".workspace/handoff-v2")
        self.assertEqual(res["bundledSlots"], 1)
        self.assertEqual(res["slots"][0]["slotId"], "slot-104")
        manifest = _read_json(
            os.path.join(
                self._slot_dir(".workspace/handoff-v2", "2026-11-24", "slot-104", "multitrack-hub", "youtube"),
                "handoff-manifest.json",
            )
        )
        self.assertEqual(manifest["approvalStatus"], "APROVADO_PELO_TITULAR")

    # ------------------------------------------------------------------
    # 3. Filtragem seletiva
    # ------------------------------------------------------------------
    def test_04_only_approved_campaigns_are_bundled(self) -> None:
        rel = _write_approvals(
            self.root,
            "aprov-marca",
            [
                {"tenantId": "marca-salao", "slug": CAMPAIGNS["marca-salao"], "decisao": "aprovado"},
                {"tenantId": "meu-salao", "slug": CAMPAIGNS["meu-salao"], "decisao": "aguardando"},
            ],
        )
        res = self._build(approvals_file=rel, all_approved=True, output_dir=".workspace/handoff-t04")
        self.assertEqual(res["bundledSlots"], 3)
        self.assertEqual({s["tenantId"] for s in res["slots"]}, {"marca-salao"})
        self.assertEqual({s["slotId"] for s in res["slots"]}, {"slot-101", "slot-102", "slot-106"})
        self.assertFalse(
            os.path.isdir(
                render_local.fs_path(
                    os.path.join(self.root, ".workspace", "handoff-t04", "2026-11-24")
                )
            )
        )

    # ------------------------------------------------------------------
    # 4. Roteamento de midia Onda 1 vs Onda 2
    # ------------------------------------------------------------------
    def test_05_media_routing_onda1_and_onda2(self) -> None:
        rel = _write_approvals(
            self.root,
            "aprov-todas",
            [
                {"tenantId": tenant, "slug": slug, "decisao": "aprovado"}
                for tenant, slug in CAMPAIGNS.items()
            ],
        )
        out = ".workspace/handoff-t05"
        res = self._build(approvals_file=rel, all_approved=True, output_dir=out)
        self.assertEqual(res["bundledSlots"], 6)

        casos = [
            ("2026-11-23", "slot-101", "marca-salao", "youtube", "9:16"),
            ("2026-11-25", "slot-102", "marca-salao", "instagram", "9:16"),
            ("2026-12-07", "slot-105", "estudio-flow", "instagram", "1:1"),
            ("2026-12-08", "slot-106", "marca-salao", "youtube", "16:9"),
        ]
        for data, slot_id, tenant, canal, formato in casos:
            with self.subTest(slot=slot_id):
                slug = CAMPAIGNS[tenant]
                suffix = {"9:16": "", "1:1": "-1x1", "16:9": "-16x9"}[formato]
                expected_media = f"{slug}{suffix}.mp4"
                slot_dir = self._slot_dir(out, data, slot_id, tenant, canal)
                manifest = _read_json(os.path.join(slot_dir, "handoff-manifest.json"))
                self.assertEqual(manifest["formatoVideo"], formato)
                self.assertEqual(manifest["media"]["expectedFile"], expected_media)
                self.assertTrue(manifest["media"]["mediaCopied"], manifest["media"])
                self.assertTrue(manifest["media"]["hashVerified"], manifest["media"])
                self.assertEqual(manifest["media"]["copiedFile"], expected_media)
                self.assertTrue(os.path.isfile(render_local.fs_path(os.path.join(slot_dir, expected_media))))
                self.assertTrue(os.path.isfile(render_local.fs_path(os.path.join(slot_dir, "cover.png"))))

    # ------------------------------------------------------------------
    # 5. --include-pending e exclusao de ajuste
    # ------------------------------------------------------------------
    def test_06_include_pending_stamp_and_adjustment_excluded(self) -> None:
        rel = _write_approvals(
            self.root,
            "aprov-t06",
            [
                {"tenantId": "marca-salao", "slug": CAMPAIGNS["marca-salao"], "decisao": "aprovado"},
                {"tenantId": "meu-salao", "slug": CAMPAIGNS["meu-salao"], "decisao": "ajuste"},
            ],
        )
        out = ".workspace/handoff-t06"
        res = self._build(
            approvals_file=rel, all_approved=True, include_pending=True, output_dir=out
        )
        # 6 slots no calendario; meu-salao esta em ajuste e nao entra.
        self.assertEqual(res["bundledSlots"], 5)
        self.assertIn(
            {"slotId": "slot-103", "reason": "AJUSTE_SOLICITADO"},
            [{"slotId": s["slotId"], "reason": s["reason"]} for s in res["skipped"]],
        )

        aprovado = _read_json(
            os.path.join(
                self._slot_dir(out, "2026-11-23", "slot-101", "marca-salao", "youtube"),
                "handoff-manifest.json",
            )
        )
        pendente = _read_json(
            os.path.join(
                self._slot_dir(out, "2026-11-24", "slot-104", "multitrack-hub", "youtube"),
                "handoff-manifest.json",
            )
        )
        self.assertEqual(aprovado["approvalStatus"], "APROVADO_PELO_TITULAR")
        self.assertEqual(pendente["approvalStatus"], "PREVIA_NAO_APROVADA")
        pending_doc = _read_text(
            os.path.join(
                self._slot_dir(out, "2026-11-24", "slot-104", "multitrack-hub", "youtube"),
                "POSTAGEM-MANUAL.md",
            )
        )
        self.assertIn("PREVIA_NAO_APROVADA", pending_doc)

    # ------------------------------------------------------------------
    # 6. Filtro --date
    # ------------------------------------------------------------------
    def test_07_date_filter(self) -> None:
        rel = _write_approvals(
            self.root,
            "aprov-t07",
            [{"tenantId": "marca-salao", "slug": CAMPAIGNS["marca-salao"], "decisao": "aprovado"}],
        )
        res = self._build(
            approvals_file=rel, date="2026-11-23", output_dir=".workspace/handoff-t07"
        )
        self.assertEqual(res["bundledSlots"], 1)
        self.assertEqual(res["dates"], ["2026-11-23"])
        self.assertEqual(res["slots"][0]["slotId"], "slot-101")

        vazio = self._build(
            approvals_file=rel, date="2026-11-24", output_dir=".workspace/handoff-t07b"
        )
        self.assertEqual(vazio["bundledSlots"], 0)
        self.assertEqual(vazio["reason"], "NENHUM_SLOT_APROVADO_NA_DATA")

    # ------------------------------------------------------------------
    # 7. Documentos do slot e autoPublish
    # ------------------------------------------------------------------
    def test_08_documents_manifest_and_checklist(self) -> None:
        rel = _write_approvals(
            self.root,
            "aprov-t08",
            [{"tenantId": "marca-salao", "slug": CAMPAIGNS["marca-salao"], "decisao": "aprovado"}],
        )
        out = ".workspace/handoff-t08"
        self._build(approvals_file=rel, all_approved=True, output_dir=out)
        slot_dir = self._slot_dir(out, "2026-12-08", "slot-106", "marca-salao", "youtube")

        for filename in ("POSTAGEM-MANUAL.md", "copy-pronta.txt", "handoff-manifest.json"):
            self.assertTrue(
                os.path.isfile(render_local.fs_path(os.path.join(slot_dir, filename))),
                filename,
            )

        doc = _read_text(os.path.join(slot_dir, "POSTAGEM-MANUAL.md"))
        self.assertIn("12:00-13:00", doc)
        self.assertIn("Marca Salão", doc)
        self.assertIn("16:9", doc)
        self.assertIn("Checklist de publicacao (5 passos)", doc)
        for passo in range(1, 6):
            self.assertIn(f"\n{passo}. ", doc)
        self.assertNotIn("\n6. ", doc)

        copy_pronta = _read_text(os.path.join(slot_dir, "copy-pronta.txt"))
        self.assertIn("utm_content=repurpose-16x9", copy_pronta)
        self.assertNotIn("utm_content=marca-salao", copy_pronta)

        manifest = _read_json(os.path.join(slot_dir, "handoff-manifest.json"))
        self.assertIs(manifest["autoPublish"], False)
        self.assertIs(manifest["manualOnly"], True)
        self.assertTrue(manifest["guardrailsAudited"])
        self.assertEqual(manifest["guardrailViolations"], [])
        self.assertEqual(manifest["utmUrl"], "https://marcasalao.com.br/?utm_source=youtube&utm_medium=video&utm_campaign=camp-saas-demo-marca-salao-001&utm_content=repurpose-16x9")
        self.assertIn("sha256Expected", manifest["media"])

    # ------------------------------------------------------------------
    # 8. Alerta de locucao externa: -an vs multitrack-hub
    # ------------------------------------------------------------------
    def test_09_external_narration_alert_only_for_an_tenants(self) -> None:
        rel = _write_approvals(
            self.root,
            "aprov-t09",
            [
                {"tenantId": "marca-salao", "slug": CAMPAIGNS["marca-salao"], "decisao": "aprovado"},
                {"tenantId": "multitrack-hub", "slug": CAMPAIGNS["multitrack-hub"], "decisao": "aprovado"},
            ],
        )
        out = ".workspace/handoff-t09"
        self._build(approvals_file=rel, all_approved=True, output_dir=out)

        an_dir = self._slot_dir(out, "2026-11-23", "slot-101", "marca-salao", "youtube")
        aac_dir = self._slot_dir(out, "2026-11-24", "slot-104", "multitrack-hub", "youtube")
        an_doc = _read_text(os.path.join(an_dir, "POSTAGEM-MANUAL.md"))
        aac_doc = _read_text(os.path.join(aac_dir, "POSTAGEM-MANUAL.md"))
        self.assertIn("locucao externa", an_doc.lower())
        self.assertNotIn("locucao externa", aac_doc.lower())

        an_manifest = _read_json(os.path.join(an_dir, "handoff-manifest.json"))
        aac_manifest = _read_json(os.path.join(aac_dir, "handoff-manifest.json"))
        self.assertTrue(an_manifest["externalNarrationAlert"])
        self.assertFalse(aac_manifest["externalNarrationAlert"])
        self.assertEqual(an_manifest["audioPolicy"]["ffmpegFlag"], "-an")

    # ------------------------------------------------------------------
    # 9. Contencao de path
    # ------------------------------------------------------------------
    def test_10_path_containment(self) -> None:
        rel = _write_approvals(
            self.root,
            "aprov-t10",
            [{"tenantId": "marca-salao", "slug": CAMPAIGNS["marca-salao"], "decisao": "aprovado"}],
        )
        with self.assertRaises(handoff_bundler.HandoffBundlerError) as ctx:
            self._build(approvals_file=rel, all_approved=True, output_dir="../fora-do-projeto")
        self.assertEqual(ctx.exception.code, "HANDOFF_FORA_DA_RAIZ")

        with self.assertRaises(handoff_bundler.HandoffBundlerError) as ctx:
            self._build(approvals_file="../../fora.json", all_approved=True, output_dir=".workspace/handoff-t10")
        self.assertEqual(ctx.exception.code, "APROVACOES_FORA_DA_RAIZ")

        slot = _slot("slot-999", "marca-salao", "youtube", "2026-11-23")
        slot["slotId"] = "../escape"
        workspace_root = publish_pack.resolve_workspace_root(self.root)
        with self.assertRaises(handoff_bundler.HandoffBundlerError) as ctx:
            handoff_bundler._bundle_slot(
                self.root,
                workspace_root,
                os.path.join(self.root, ".workspace", "handoff-t10"),
                slot,
                {"status": "aprovado"},
            )
        self.assertEqual(ctx.exception.code, "NOME_INVALIDO")

    # ------------------------------------------------------------------
    # 10. CLI --json exit 0
    # ------------------------------------------------------------------
    def test_11_cli_json_exit_zero(self) -> None:
        rel = _write_approvals(
            self.root,
            "aprov-cli",
            [{"tenantId": "marca-salao", "slug": CAMPAIGNS["marca-salao"], "decisao": "aprovado"}],
        )
        proc = subprocess.run(
            [
                sys.executable,
                os.path.abspath(handoff_bundler.__file__),
                "--root",
                self.root,
                "--approvals-file",
                rel,
                "--all-approved",
                "--output-dir",
                ".workspace/handoff-cli",
                "--json",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        doc = json.loads(proc.stdout)
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["bundledSlots"], 3)
        self.assertIs(doc["autoPublish"], False)

    # ------------------------------------------------------------------
    # 11. Indice consolidado
    # ------------------------------------------------------------------
    def test_12_index_files_generated(self) -> None:
        rel = _write_approvals(
            self.root,
            "aprov-t12",
            [{"tenantId": "marca-salao", "slug": CAMPAIGNS["marca-salao"], "decisao": "aprovado"}],
        )
        out = ".workspace/handoff-t12"
        res = self._build(approvals_file=rel, all_approved=True, output_dir=out)
        md_path = os.path.join(self.root, *out.split("/"), "INDICE-OPERACIONAL.md")
        json_path = os.path.join(self.root, *out.split("/"), "indice-operacional.json")
        self.assertTrue(os.path.isfile(render_local.fs_path(md_path)))
        self.assertTrue(os.path.isfile(render_local.fs_path(json_path)))
        self.assertEqual(res["indexMarkdown"], f"{out}/INDICE-OPERACIONAL.md")
        index = _read_json(json_path)
        self.assertIs(index["autoPublish"], False)
        self.assertEqual(index["bundledSlots"], 3)
        self.assertEqual(sorted(index["dates"]), ["2026-11-23", "2026-11-25", "2026-12-08"])
        doc = _read_text(md_path)
        self.assertIn("| Data | Slot | Marca | Canal | Formato | Status |", doc)


if __name__ == "__main__":
    unittest.main()