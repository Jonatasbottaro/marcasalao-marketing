"""Testes automatizados (unittest) para a reconciliacao bundle -> UTM (Etapa 12).

Cobre 6 casos:
  1. Bundle aprovado com metrica UTM para o mesmo (tenantId, slug) -> reconciliado,
     com metricas (impressions, clicks, ctr, conversions, conversionRate,
     observedUpliftPct, winnerSustained) anexadas.
  2. Bundle aprovado sem metrica UTM para o (tenantId, slug) -> aguardando_metricas.
  3. Bundle aprovado com tenantId divergente (nenhum slot UTM para aquele tenant)
     -> divergencia_tenant.
  4. Bundle com selo PREVIA_NAO_APROVADA -> nao_elegivel_para_PREVIA_NAO_APROVADA.
  5. Sem bundles no diretorio -> total 0, listas vazias.
  6. CLI --reconcile-bundles --json -> codigo 0 e saida JSON com summary e bundles.

Todos os testes rodam em uma raiz temporaria (.workspace/tmp/) sem gravar em
arquivos versionados. O tenant_id e slug sao validos (apenas [a-z0-9_-]).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import utm_report_importer  # noqa: E402

TEST_TMP_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "test_bundle_attribution")


def _write_json(path: str, doc: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(doc, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _make_bundle_manifest(root: str, tenant_id: str, slug: str,
                          approval_status: str = "APROVADO_PELO_TITULAR",
                          bundle_sha: str = "abc123",
                          promotion_history: list | None = None,
                          items: list | None = None) -> str:
    """Grava um manifesto de bundle em .workspace/bundles/<tenant>/<slug>/ e
    devolve o caminho relativo do arquivo -manifest.json."""
    bundle_dir = os.path.join(root, ".workspace", "bundles", tenant_id, slug)
    os.makedirs(bundle_dir, exist_ok=True)
    manifest_name = f"{slug}-v1-manifest.json"
    manifest_path = os.path.join(bundle_dir, manifest_name)
    manifest = {
        "schemaVersion": 1,
        "generatedBy": "tools/publish_bundler.py",
        "tenantId": tenant_id,
        "slug": slug,
        "autoPublish": False,
        "approvalStatus": approval_status,
        "bundlePath": f".workspace/bundles/{tenant_id}/{slug}/{slug}-v1.zip",
        "bundleSha256": bundle_sha,
        "bundleBytes": 1024,
        "promotionHistory": promotion_history or [],
        "items": items or [],
        "bundleSummary": {"itemCount": len(items or []), "totalBytes": 1024},
    }
    _write_json(manifest_path, manifest)
    return manifest_path


class BundleAttributionTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        if os.path.isdir(TEST_TMP_ROOT):
            shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)

    # ------------------------------------------------------------------
    # fixtures
    # ------------------------------------------------------------------
    def _root(self, name: str) -> str:
        root = os.path.join(TEST_TMP_ROOT, name)
        shutil.rmtree(root, ignore_errors=True)
        os.makedirs(root, exist_ok=True)
        return root

    def _utm_report(self, root: str, slots: list[dict]) -> str:
        report = {
            "schemaVersion": 1,
            "generatedBy": "tools/utm_report_importer.py",
            "ok": True,
            "provider": "ga4",
            "slots": slots,
            "rankings": {
                "tenantBenchmarks": {
                    "byTenant": [
                        {
                            "tenantId": "marca-salao",
                            "conversionRatePct": 4.0,
                            "sessions": 1000,
                            "conversions": 40,
                        },
                    ],
                },
            },
        }
        rel = ".workspace/tmp/test_bundle_attribution/utm-report.json"
        _write_json(os.path.join(root, *rel.split("/")), report)
        return rel

    # ------------------------------------------------------------------
    # 1. Bundle aprovado + UTM -> reconciliado com metricas
    # ------------------------------------------------------------------
    def test_01_bundle_aprovado_com_utm_reconciliado(self) -> None:
        root = self._root("reconciliado")
        _make_bundle_manifest(
            root, "marca-salao", "camp-saas-demo-marca-salao-001",
            approval_status="APROVADO_PELO_TITULAR",
            bundle_sha="aaaa1111",
            promotion_history=[
                {"promotedVariant": "B", "promotedBy": "revisor", "promotedAt": "2026-11-20T10:00:00Z"},
            ],
        )
        utm_rel = self._utm_report(root, [
            {
                "slotId": "slot-001",
                "tenantId": "marca-salao",
                "slug": "camp-saas-demo-marca-salao-001",
                "canal": "youtube",
                "sessions": 1000,
                "engagedSessions": 600,
                "conversions": 50,
                "conversionRatePct": 5.0,
            },
        ])
        result = utm_report_importer.reconcile_bundles(
            root=root, utm_report=_read_json(os.path.join(root, utm_rel)),
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["total"], 1)
        self.assertEqual(result["summary"]["reconciliado"], 1)
        entry = result["bundles"][0]
        self.assertEqual(entry["tenantId"], "marca-salao")
        self.assertEqual(entry["slug"], "camp-saas-demo-marca-salao-001")
        self.assertEqual(entry["attributionStatus"], "reconciliado")
        self.assertEqual(entry["approvalStatus"], "APROVADO_PELO_TITULAR")
        metrics = entry["metrics"]
        self.assertEqual(metrics["impressions"], 1000)
        self.assertEqual(metrics["clicks"], 600)
        self.assertEqual(metrics["ctr"], 60.0)
        self.assertEqual(metrics["conversions"], 50)
        self.assertEqual(metrics["conversionRate"], 5.0)
        # observedUpliftPct = (5.0 - 4.0) / 4.0 * 100 = 25.0
        self.assertEqual(metrics["observedUpliftPct"], 25.0)
        self.assertIs(metrics["winnerSustained"], True)
        # Arquivo gravado
        attr_path = os.path.join(root, result["attributionPath"])
        self.assertTrue(os.path.isfile(attr_path))

    # ------------------------------------------------------------------
    # 2. Bundle aprovado sem UTM -> aguardando_metricas
    # ------------------------------------------------------------------
    def test_02_bundle_aprovado_sem_utm_aguardando_metricas(self) -> None:
        root = self._root("aguardando")
        _make_bundle_manifest(
            root, "marca-salao", "camp-saas-demo-ns001-agenda-001",
            approval_status="APROVADO_PELO_TITULAR",
        )
        result = utm_report_importer.reconcile_bundles(root=root, utm_report=None)
        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["total"], 1)
        self.assertEqual(result["summary"]["aguardando_metricas"], 1)
        entry = result["bundles"][0]
        self.assertEqual(entry["attributionStatus"], "aguardando_metricas")
        self.assertIsNone(entry["metrics"])
        self.assertIsNone(entry["winnerSustained"])

    # ------------------------------------------------------------------
    # 3. Bundle aprovado com tenant divergente -> divergencia_tenant
    # ------------------------------------------------------------------
    def test_03_bundle_tenant_divergente(self) -> None:
        root = self._root("divergente")
        _make_bundle_manifest(
            root, "marca-salao", "camp-x",
            approval_status="APROVADO_PELO_TITULAR",
        )
        # UTM so tem slots de multitrack-hub (outro tenant)
        utm_rel = self._utm_report(root, [
            {
                "slotId": "slot-001",
                "tenantId": "multitrack-hub",
                "slug": "camp-multi",
                "canal": "youtube",
                "sessions": 1000,
                "engagedSessions": 600,
                "conversions": 50,
                "conversionRatePct": 5.0,
            },
        ])
        result = utm_report_importer.reconcile_bundles(
            root=root, utm_report=_read_json(os.path.join(root, utm_rel)),
        )
        entry = result["bundles"][0]
        self.assertEqual(entry["attributionStatus"], "divergencia_tenant")
        self.assertEqual(result["summary"]["divergencia_tenant"], 1)

    # ------------------------------------------------------------------
    # 4. Bundle PREVIA_NAO_APROVADA -> nao_elegivel
    # ------------------------------------------------------------------
    def test_04_bundle_previo_nao_aprovado_nao_elegivel(self) -> None:
        root = self._root("previo")
        _make_bundle_manifest(
            root, "marca-salao", "camp-x",
            approval_status="PREVIA_NAO_APROVADA",
        )
        result = utm_report_importer.reconcile_bundles(root=root, utm_report=None)
        entry = result["bundles"][0]
        self.assertEqual(entry["attributionStatus"], "nao_elegivel_para_PREVIA_NAO_APROVADA")
        self.assertEqual(result["summary"]["nao_elegivel_para_PREVIA_NAO_APROVADA"], 1)

    # ------------------------------------------------------------------
    # 5. Sem bundles -> total 0
    # ------------------------------------------------------------------
    def test_05_sem_bundles(self) -> None:
        root = self._root("vazio")
        result = utm_report_importer.reconcile_bundles(root=root, utm_report=None)
        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["total"], 0)
        self.assertEqual(result["bundles"], [])
        self.assertEqual(result["summary"]["reconciliado"], 0)

    # ------------------------------------------------------------------
    # 6. CLI --reconcile-bundles --json -> codigo 0
    # ------------------------------------------------------------------
    def test_06_cli_reconcile_bundles_json_exit_zero(self) -> None:
        root = self._root("cli")
        _make_bundle_manifest(
            root, "marca-salao", "camp-saas-demo-marca-salao-001",
            approval_status="APROVADO_PELO_TITULAR",
        )
        utm_rel = self._utm_report(root, [
            {
                "slotId": "slot-001",
                "tenantId": "marca-salao",
                "slug": "camp-saas-demo-marca-salao-001",
                "canal": "youtube",
                "sessions": 1000,
                "engagedSessions": 600,
                "conversions": 50,
                "conversionRatePct": 5.0,
            },
        ])
        proc = subprocess.run(
            [
                sys.executable,
                os.path.abspath(utm_report_importer.__file__),
                "--root", root,
                "--reconcile-bundles",
                "--json",
            ],
            capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        doc = json.loads(proc.stdout)
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["summary"]["total"], 1)
        self.assertEqual(doc["summary"]["reconciliado"], 1)
        self.assertEqual(doc["bundles"][0]["attributionStatus"], "reconciliado")


if __name__ == "__main__":
    unittest.main()
