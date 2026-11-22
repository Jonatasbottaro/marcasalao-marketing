"""Testes do reparo cirurgico de midia local (workspace_doctor --repair).

Cobre obrigatoriamente:
  1. Dry-run por padrao: plano de reparo sem NENHUMA mutacao em disco.
  2. Deteccao de arquivo corrompido/ausente em fixture temporaria isolada.
  3. Reparo com --apply restaurando a conformidade SHA-256 declarada.
  4. Fail-closed quando os insumos de origem estao ausentes ou nao reproduzem
     o hash declarado (nada e promovido para archives).
  5. Regeneracao somente dos derivados afetados, e somente com master integro.
  6. Isolamento por tenant/slug e recusa de path traversal.

Toda fixture vive sob ``<RAIZ>/.workspace/tmp/`` e o resolvedor de raiz principal
e simulado, para que nenhum teste toque nos masters reais do checkout.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

import derivative_formats  # noqa: E402
import preset_runner  # noqa: E402
import render_local  # noqa: E402
import workspace_doctor as wd  # noqa: E402

TMP_PARENT = REPO_ROOT / ".workspace" / "tmp" / "test_workspace_doctor_repair"
SLOTS = (("tenant-alfa", "camp-alfa-001"), ("tenant-beta", "camp-beta-001"))
DERIV_FORMATS = ("1x1", "cover")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RepairFixture(unittest.TestCase):
    def setUp(self) -> None:
        TMP_PARENT.mkdir(parents=True, exist_ok=True)
        self._tmp = tempfile.TemporaryDirectory(prefix="repair-", dir=str(TMP_PARENT))
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

        self.workspace = self.root / ".workspace"
        (self.workspace / "archives").mkdir(parents=True)
        (self.workspace / "tmp").mkdir()

        # slot -> {"master": (archive_path, bytes, versioned_path), "derivs": {...}}
        self.slots: dict[str, dict] = {}
        for tenant, slug in SLOTS:
            self._build_slot(tenant, slug)

        self._root_patch = mock.patch.object(
            wd, "_resolve_main_root", return_value=str(self.root)
        )
        self._root_patch.start()
        self.addCleanup(self._root_patch.stop)

    def _build_slot(self, tenant: str, slug: str) -> None:
        delivery = self.root / "02-reels-shorts" / "deliveries" / tenant / slug
        delivery.mkdir(parents=True)
        archive = self.workspace / "archives" / slug
        (archive / "derivatives").mkdir(parents=True)

        master_bytes = f"master-{slug}".encode() * 64
        master_archive = archive / f"{slug}.mp4"
        master_versioned = delivery / f"{slug}.mp4"
        master_archive.write_bytes(master_bytes)
        master_versioned.write_bytes(master_bytes)

        derivs: dict[str, dict] = {}
        declared: dict[str, dict] = {}
        for fmt in DERIV_FORMATS:
            ext = "png" if fmt == "cover" else "mp4"
            name = f"{slug}-{fmt}.{ext}"
            data = f"deriv-{slug}-{fmt}".encode() * 32
            arc = archive / "derivatives" / name
            arc.write_bytes(data)
            versioned = delivery / name
            versioned.write_bytes(data)
            derivs[fmt] = {"archive": arc, "data": data, "versioned": versioned}
            declared[fmt] = {
                "path": self._rel(arc),
                "sha256": _sha(data),
                "kind": fmt,
                "versionedCopy": self._rel(versioned),
            }

        manifest = {
            "schemaVersion": 1,
            "tenantId": tenant,
            "config": f"tenants/{tenant}/campaigns/{slug}.json",
            "artifacts": {
                "video": {
                    "path": self._rel(master_versioned),
                    "archivePath": self._rel(master_archive),
                    "sha256": _sha(master_bytes),
                }
            },
        }
        (delivery / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
        )
        (delivery / "derivatives.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 2,
                    "tenantId": tenant,
                    "slug": slug,
                    "source": {
                        "path": self._rel(master_archive),
                        "sha256": _sha(master_bytes),
                    },
                    "derivatives": declared,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        config = self.root / "tenants" / tenant / "campaigns"
        config.mkdir(parents=True, exist_ok=True)
        (config / f"{slug}.json").write_text('{"id": "%s"}' % slug, encoding="utf-8")

        self.slots[slug] = {
            "tenant": tenant,
            "delivery": delivery,
            "master": master_archive,
            "masterData": master_bytes,
            "masterVersioned": master_versioned,
            "derivs": derivs,
        }

    def _rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def _corrupt(self, path: Path) -> None:
        path.write_bytes(b"CONTEUDO-CORROMPIDO-PELO-TESTE")

    def _hash(self, path: Path) -> str:
        return _sha(path.read_bytes())


class RepairDryRunTest(RepairFixture):
    def test_01_slot_integro_nao_gera_plano(self) -> None:
        result = wd.repair_media(self.root)
        self.assertTrue(result["ok"], result["remainingErrors"])
        self.assertTrue(result["dryRun"])
        self.assertFalse(result["applied"])
        self.assertIs(result["autoPublish"], False)
        self.assertEqual(result["plannedItems"], [])
        self.assertEqual(result["repairedItems"], [])
        self.assertEqual(result["summary"]["slotsInspecionados"], 2)

    def test_02_dry_run_detecta_corrupcao_sem_mutar(self) -> None:
        slot = self.slots["camp-alfa-001"]
        self._corrupt(slot["master"])
        corrupted = self._hash(slot["master"])

        result = wd.repair_media(self.root)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["plannedItems"]), 1)
        item = result["plannedItems"][0]
        self.assertEqual(item["slug"], "camp-alfa-001")
        self.assertEqual(item["kind"], "master")
        self.assertEqual(item["state"], "divergente")
        self.assertEqual(item["strategy"], "restore-from-delivery")
        self.assertEqual(item["actualSha256"], corrupted)
        self.assertEqual(result["repairedItems"], [])
        self.assertEqual(self._hash(slot["master"]), corrupted, "dry-run nao pode gravar")

    def test_03_dry_run_detecta_master_ausente(self) -> None:
        slot = self.slots["camp-beta-001"]
        slot["master"].unlink()
        result = wd.repair_media(self.root)
        self.assertEqual(len(result["plannedItems"]), 1)
        self.assertEqual(result["plannedItems"][0]["state"], "ausente")
        self.assertIsNone(result["plannedItems"][0]["actualSha256"])
        self.assertFalse(slot["master"].exists(), "dry-run nao pode recriar arquivo")


class RepairApplyTest(RepairFixture):
    def test_04_apply_restaura_sha256_do_master(self) -> None:
        slot = self.slots["camp-alfa-001"]
        expected = _sha(slot["masterData"])
        self._corrupt(slot["master"])
        self.assertNotEqual(self._hash(slot["master"]), expected)

        result = wd.repair_media(self.root, apply=True)
        self.assertTrue(result["ok"], result["remainingErrors"])
        self.assertTrue(result["applied"])
        self.assertEqual(len(result["repairedItems"]), 1)
        self.assertEqual(result["repairedItems"][0]["strategy"], "restore-from-delivery")
        self.assertEqual(self._hash(slot["master"]), expected)
        self.assertEqual(result["remainingErrors"], [])

        audit = wd.run_workspace_doctor(self.root)
        self.assertEqual(audit["summary"]["archives"]["divergentes"], 0)

    def test_05_apply_recria_master_ausente(self) -> None:
        slot = self.slots["camp-beta-001"]
        slot["master"].unlink()
        result = wd.repair_media(self.root, apply=True)
        self.assertTrue(result["ok"], result["remainingErrors"])
        self.assertTrue(slot["master"].is_file())
        self.assertEqual(self._hash(slot["master"]), _sha(slot["masterData"]))

    def test_06_apply_repara_os_dois_tenants_sem_misturar(self) -> None:
        for slot in self.slots.values():
            self._corrupt(slot["master"])
        result = wd.repair_media(self.root, apply=True)
        self.assertTrue(result["ok"], result["remainingErrors"])
        self.assertEqual(len(result["repairedItems"]), 2)
        self.assertEqual(
            {item["tenantId"] for item in result["repairedItems"]},
            {"tenant-alfa", "tenant-beta"},
        )
        for slot in self.slots.values():
            self.assertEqual(self._hash(slot["master"]), _sha(slot["masterData"]))

    def test_07_filtro_slug_restringe_o_reparo(self) -> None:
        for slot in self.slots.values():
            self._corrupt(slot["master"])
        untouched = self._hash(self.slots["camp-beta-001"]["master"])
        result = wd.repair_media(self.root, apply=True, slug="camp-alfa-001")
        self.assertTrue(result["ok"], result["remainingErrors"])
        self.assertEqual(result["summary"]["slotsInspecionados"], 1)
        self.assertEqual(len(result["repairedItems"]), 1)
        self.assertEqual(result["repairedItems"][0]["slug"], "camp-alfa-001")
        self.assertEqual(
            self._hash(self.slots["camp-beta-001"]["master"]), untouched,
            "reparo filtrado nao pode tocar em outro slot",
        )

    def test_08_filtro_tenant_restringe_o_reparo(self) -> None:
        for slot in self.slots.values():
            self._corrupt(slot["master"])
        result = wd.repair_media(self.root, apply=True, tenant="tenant-beta")
        self.assertTrue(result["ok"], result["remainingErrors"])
        self.assertEqual(result["summary"]["slotsInspecionados"], 1)
        self.assertEqual(result["repairedItems"][0]["tenantId"], "tenant-beta")

    def test_09_filtro_sem_correspondencia_falha(self) -> None:
        with self.assertRaises(wd.WorkspaceDoctorError) as ctx:
            wd.repair_media(self.root, slug="campanha-inexistente")
        self.assertIn("FILTRO_SEM_CORRESPONDENCIA", str(ctx.exception))


class RepairFailClosedTest(RepairFixture):
    def test_10_sem_copia_integra_nem_config_pula_e_reporta(self) -> None:
        slot = self.slots["camp-alfa-001"]
        self._corrupt(slot["master"])
        self._corrupt(slot["masterVersioned"])
        config = self.root / "tenants" / slot["tenant"] / "campaigns" / "camp-alfa-001.json"
        config.unlink()
        corrupted = self._hash(slot["master"])

        result = wd.repair_media(self.root, apply=True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["repairedItems"], [])
        self.assertEqual(len(result["skippedItems"]), 1)
        self.assertEqual(result["skippedItems"][0]["reason"], "INSUMO_AUSENTE")
        self.assertTrue(result["remainingErrors"])
        self.assertEqual(self._hash(slot["master"]), corrupted, "nada deve ser promovido")

    def test_11_rerender_com_hash_diferente_nao_promove(self) -> None:
        slot = self.slots["camp-alfa-001"]
        self._corrupt(slot["master"])
        self._corrupt(slot["masterVersioned"])
        corrupted = self._hash(slot["master"])

        def fake_pipeline(tenant, config, out_dir, audio_path=None, root=".", archives_dir=None):
            target = Path(archives_dir) / "camp-alfa-001"
            target.mkdir(parents=True, exist_ok=True)
            wrong = b"render-de-outra-versao-do-pipeline"
            (target / "camp-alfa-001.mp4").write_bytes(wrong)
            return {"artifacts": {"video": {"sha256": _sha(wrong)}}}

        with mock.patch.object(render_local, "ensure_video_tools", lambda *_a, **_k: None), \
             mock.patch.object(preset_runner, "run_preset_pipeline", side_effect=fake_pipeline):
            result = wd.repair_media(self.root, apply=True, slug="camp-alfa-001")

        self.assertFalse(result["ok"])
        self.assertEqual(result["repairedItems"], [])
        self.assertEqual(result["skippedItems"][0]["reason"], "MASTER_NAO_REPRODUTIVEL")
        self.assertEqual(self._hash(slot["master"]), corrupted)

    def test_12_rerender_promove_quando_sha_confere(self) -> None:
        slot = self.slots["camp-alfa-001"]
        expected = _sha(slot["masterData"])
        self._corrupt(slot["master"])
        self._corrupt(slot["masterVersioned"])

        def fake_pipeline(tenant, config, out_dir, audio_path=None, root=".", archives_dir=None):
            target = Path(archives_dir) / "camp-alfa-001"
            target.mkdir(parents=True, exist_ok=True)
            (target / "camp-alfa-001.mp4").write_bytes(slot["masterData"])
            return {"artifacts": {"video": {"sha256": expected}}}

        with mock.patch.object(render_local, "ensure_video_tools", lambda *_a, **_k: None), \
             mock.patch.object(preset_runner, "run_preset_pipeline", side_effect=fake_pipeline):
            result = wd.repair_media(self.root, apply=True, slug="camp-alfa-001")

        self.assertTrue(result["ok"], result["remainingErrors"])
        self.assertEqual(result["repairedItems"][0]["strategy"], "rerender")
        self.assertEqual(self._hash(slot["master"]), expected)

    def test_13_pipeline_que_explode_e_fail_closed(self) -> None:
        slot = self.slots["camp-alfa-001"]
        self._corrupt(slot["master"])
        self._corrupt(slot["masterVersioned"])
        corrupted = self._hash(slot["master"])

        with mock.patch.object(render_local, "ensure_video_tools", lambda *_a, **_k: None), \
             mock.patch.object(
                 preset_runner, "run_preset_pipeline",
                 side_effect=preset_runner.PresetRunnerError("ffmpeg ausente"),
             ):
            result = wd.repair_media(self.root, apply=True, slug="camp-alfa-001")

        self.assertFalse(result["ok"])
        self.assertEqual(result["skippedItems"][0]["reason"], "RENDER_FALHOU")
        self.assertEqual(self._hash(slot["master"]), corrupted)

    def test_14_ffprobe_divergente_pos_reparo_bloqueia(self) -> None:
        slot = self.slots["camp-alfa-001"]
        manifest_path = slot["delivery"] / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["artifacts"]["video"]["ffprobe"] = {"width": 1080, "height": 1920}
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        self._corrupt(slot["master"])

        with mock.patch.object(wd, "_ffprobe_metadata", return_value={"width": 720, "height": 1280}):
            result = wd.repair_media(self.root, apply=True, slug="camp-alfa-001")

        self.assertFalse(result["ok"])
        self.assertEqual(result["repairedItems"], [])
        self.assertIn("FFPROBE_DIVERGENTE_POS_REPARO", result["skippedItems"][0]["reason"])


class RepairDerivativesTest(RepairFixture):
    def test_15_regenera_apenas_o_formato_afetado(self) -> None:
        slot = self.slots["camp-alfa-001"]
        target = slot["derivs"]["1x1"]
        self._corrupt(target["archive"])
        seen: dict = {}

        def fake_generate(tenant, slug, root=".", formats=None, **kwargs):
            seen["tenant"], seen["slug"], seen["formats"] = tenant, slug, list(formats)
            target["archive"].write_bytes(target["data"])
            return {"status": "generated"}

        with mock.patch.object(
            derivative_formats, "generate_campaign_derivatives", side_effect=fake_generate
        ):
            result = wd.repair_media(self.root, apply=True, slug="camp-alfa-001")

        self.assertTrue(result["ok"], result["remainingErrors"])
        self.assertEqual(seen["formats"], ["1x1"], "so o formato divergente deve ser pedido")
        self.assertEqual(seen["tenant"], "tenant-alfa")
        self.assertEqual(len(result["repairedItems"]), 1)
        self.assertEqual(result["repairedItems"][0]["kind"], "derivado")
        self.assertEqual(result["repairedItems"][0]["format"], "1x1")
        self.assertEqual(self._hash(target["archive"]), _sha(target["data"]))

    def test_16_derivado_pulado_quando_master_nao_integro(self) -> None:
        slot = self.slots["camp-alfa-001"]
        self._corrupt(slot["master"])
        self._corrupt(slot["masterVersioned"])
        (self.root / "tenants" / slot["tenant"] / "campaigns" / "camp-alfa-001.json").unlink()
        self._corrupt(slot["derivs"]["cover"]["archive"])

        result = wd.repair_media(self.root, apply=True, slug="camp-alfa-001")
        self.assertFalse(result["ok"])
        reasons = {item["reason"] for item in result["skippedItems"]}
        self.assertIn("MASTER_NAO_INTEGRO", reasons)
        self.assertIn("INSUMO_AUSENTE", reasons)
        self.assertEqual(result["repairedItems"], [])

    def test_17_derivado_nao_reprodutivel_e_reportado(self) -> None:
        slot = self.slots["camp-alfa-001"]
        target = slot["derivs"]["cover"]
        self._corrupt(target["archive"])

        with mock.patch.object(
            derivative_formats, "generate_campaign_derivatives",
            return_value={"status": "generated"},
        ):
            result = wd.repair_media(self.root, apply=True, slug="camp-alfa-001")

        self.assertFalse(result["ok"])
        self.assertEqual(result["repairedItems"], [])
        self.assertEqual(result["skippedItems"][0]["reason"], "DERIVADO_NAO_REPRODUTIVEL")

    def test_18_dry_run_planeja_derivado_sem_chamar_pipeline(self) -> None:
        slot = self.slots["camp-beta-001"]
        self._corrupt(slot["derivs"]["cover"]["archive"])
        with mock.patch.object(
            derivative_formats, "generate_campaign_derivatives",
            side_effect=AssertionError("dry-run nao pode regenerar"),
        ):
            result = wd.repair_media(self.root)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["plannedItems"]), 1)
        self.assertEqual(result["plannedItems"][0]["strategy"], "derivative-formats")


class RepairContainmentTest(RepairFixture):
    def test_19_declaracao_fora_de_archives_e_recusada(self) -> None:
        slot = self.slots["camp-alfa-001"]
        outside = self.root / "fora.mp4"
        outside.write_bytes(b"nao-deve-ser-tocado")
        before = self._hash(outside)
        manifest_path = slot["delivery"] / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["artifacts"]["video"]["archivePath"] = "../fora.mp4"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        result = wd.repair_media(self.root, apply=True)
        self.assertFalse(result["ok"])
        codes = {p["code"] for p in result["remainingErrors"]}
        self.assertIn("PATH_OUTSIDE_ARCHIVES", codes)
        self.assertEqual(self._hash(outside), before)

    def test_20_staging_de_reparo_fica_dentro_do_workspace_tmp(self) -> None:
        slot = self.slots["camp-alfa-001"]
        self._corrupt(slot["master"])
        self._corrupt(slot["masterVersioned"])
        seen: dict = {}

        def fake_pipeline(tenant, config, out_dir, audio_path=None, root=".", archives_dir=None):
            seen["archives_dir"] = archives_dir
            seen["out_dir"] = out_dir
            raise preset_runner.PresetRunnerError("interrompido de proposito")

        expected_tmp = str(self.workspace / "tmp")
        with mock.patch.object(render_local, "ensure_video_tools", lambda *_a, **_k: None), \
             mock.patch.object(preset_runner, "run_preset_pipeline", side_effect=fake_pipeline):
            wd.repair_media(self.root, apply=True, slug="camp-alfa-001")

        for key in ("archives_dir", "out_dir"):
            self.assertEqual(
                os.path.commonpath([expected_tmp, seen[key]]), expected_tmp,
                f"{key} precisa ficar sob .workspace/tmp/",
            )
        self.assertFalse(os.path.exists(seen["archives_dir"]), "staging deve ser descartado")


class RepairCliTest(RepairFixture):
    def test_21_cli_repair_json_dry_run(self) -> None:
        slot = self.slots["camp-alfa-001"]
        self._corrupt(slot["master"])
        corrupted = self._hash(slot["master"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = wd.main(["--repair", "--json", "--root", str(self.root)])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["mode"], "repair")
        self.assertTrue(payload["dryRun"])
        self.assertIs(payload["autoPublish"], False)
        self.assertEqual(len(payload["plannedItems"]), 1)
        for key in ("repairedItems", "skippedItems", "remainingErrors"):
            self.assertIn(key, payload)
        self.assertEqual(self._hash(slot["master"]), corrupted)

    def test_22_cli_repair_apply_restaura(self) -> None:
        slot = self.slots["camp-alfa-001"]
        self._corrupt(slot["master"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = wd.main(["--repair", "--apply", "--json", "--root", str(self.root)])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["applied"])
        self.assertEqual(len(payload["repairedItems"]), 1)
        self.assertEqual(self._hash(slot["master"]), _sha(slot["masterData"]))

    def test_23_cli_repair_humano_sem_json(self) -> None:
        slot = self.slots["camp-alfa-001"]
        self._corrupt(slot["master"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = wd.main(["--repair", "--root", str(self.root)])
        self.assertEqual(rc, 0)
        text = buf.getvalue()
        self.assertIn("DRY-RUN", text)
        self.assertIn("--apply", text)

    def test_24_cli_dry_run_explicito_nao_muta(self) -> None:
        slot = self.slots["camp-alfa-001"]
        self._corrupt(slot["master"])
        corrupted = self._hash(slot["master"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = wd.main(["--repair", "--dry-run", "--json", "--root", str(self.root)])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["dryRun"])
        self.assertFalse(payload["applied"])
        self.assertEqual(len(payload["plannedItems"]), 1)
        self.assertEqual(payload["repairedItems"], [])
        self.assertEqual(self._hash(slot["master"]), corrupted)

    def test_25_apply_e_dry_run_sao_exclusivos(self) -> None:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = wd.main(["--repair", "--apply", "--dry-run", "--root", str(self.root)])
        self.assertEqual(rc, 2)
        self.assertIn("mutuamente exclusivos", err.getvalue())


def tearDownModule() -> None:
    shutil.rmtree(TMP_PARENT, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()