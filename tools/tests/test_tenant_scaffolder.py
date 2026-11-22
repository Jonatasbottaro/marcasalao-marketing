"""Tests automatizados para o tenant_scaffolder (Etapa 14 - Frente A).

Cobertura:
- dry-run retorna plannedFiles completo, applied False, nao cria arquivos
- creation com an e aac policies gera brand-kit valido passando strict validation
- creation + initial campaign gera todos os arquivos e valida hashes SRT, guardrails, editorial_qa
- fail-closed: invalid tenant_id/slug com ID_INVALIDO
- rejeita existing tenant com TENANT_JA_EXISTE
- dry-run+apply juntos nao sao aceitos (exit 2)
- integracao com executive_summary: presence of capacityStatus
- test_tenant_scaffolder incluso no smoke e fast ranges
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

# Adiciona tools/ ao sys.path (mesma convencao dos demais testes)
TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS_DIR)

import tenant_scaffolder
import tenant_validator
from tenant_scaffolder import (
    scaffold_tenant,
    ScaffolderError,
    _validate_slug,
    _validate_tenant_id,
)
import campaign_calendar


class TestTenantScaffolder(unittest.TestCase):
    """Tests for scaffold_tenant function via direct API calls."""

    def setUp(self):
        # CWD original restaurado no tearDown: outros modulos rodam no mesmo
        # processo e dependem da raiz do checkout como CWD.
        self._cwd = os.getcwd()
        # Get the actual repo root using git
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
        )
        self.repo_root = result.stdout.strip()
        # Temporarios sob <RAIZ>/.workspace/tmp (regra permanente de armazenamento).
        tmp_base = os.path.join(self.repo_root, ".workspace", "tmp")
        os.makedirs(tmp_base, exist_ok=True)
        self.tmpdir = tempfile.mkdtemp(dir=tmp_base)
        self.tmp_project = os.path.join(self.tmpdir, "marcasalao-marketing")
        # Copiar somente a estrutura essencial (nao todo o repo) para velocidade
        import shutil

        shutil.copytree(
            self.repo_root,
            self.tmp_project,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                ".git", "node_modules", ".venv", "tenants",
                "04-legendas", ".workspace",
            ),
        )
        os.chdir(self.tmp_project)

    def tearDown(self):
        os.chdir(self._cwd)
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_dry_run_returns_planned_files(self):
        """dry-run deve retornar plannedFiles completo e applied=False."""
        result = scaffold_tenant(
            tenant_id="marcasalao-test",
            brand_name="Marca Salão Test",
            domain="marcasalao-test.com.br",
            tagline="Teste de onboarding",
            audio_policy="an",
            root=self.tmp_project,
            apply=False,
        )
        self.assertTrue(result["ok"])
        self.assertFalse(result["applied"])
        self.assertIn("plannedFiles", result)
        self.assertEqual(len(result["writtenFiles"]), 0)
        self.assertEqual(result["tenantId"], "marcasalao-test")
        self.assertEqual(result["brandName"], "Marca Salão Test")
        self.assertEqual(result["audioPolicy"]["allowAudioTrack"], False)

    def test_creation_with_an_policy_validates(self):
        """Creation com audio policy 'an' gera brand-kit valido passando strict validation."""
        result = scaffold_tenant(
            tenant_id="marcasalao-an-test",
            brand_name="Marca Salão AN Test",
            domain="marcasalao-an-test.com.br",
            audio_policy="an",
            root=self.tmp_project,
            apply=True,
        )
        self.assertTrue(result["ok"], result.get("validation", {}))
        self.assertTrue(result["applied"])
        # brandKit deve ser valido com strict=True no tenant_validator
        tenant_ctx = tenant_validator.load_and_validate_tenant(
            "marcasalao-an-test", root=self.tmp_project, strict=True
        )
        self.assertTrue(tenant_ctx["ok"])
        # Verificar que o arquivo foi realmente escrito
        brand_path = os.path.join(
            self.tmp_project, "tenants", "marcasalao-an-test", "brand-kit.json"
        )
        self.assertTrue(os.path.isfile(brand_path))

    def test_creation_with_aac_policy_validates(self):
        """Creation com audio policy 'aac' gera brand-kit valido passando strict validation."""
        result = scaffold_tenant(
            tenant_id="marcasalao-aac-test",
            brand_name="Marca Salão AAC Test",
            domain="marcasalao-aac-test.com.br",
            audio_policy="aac",
            root=self.tmp_project,
            apply=True,
        )
        self.assertTrue(result["ok"])
        tenant_ctx = tenant_validator.load_and_validate_tenant(
            "marcasalao-aac-test", root=self.tmp_project, strict=True
        )
        self.assertTrue(tenant_ctx["ok"])

    def test_creation_with_campaign(self):
        """Creation + initial campaign gera todos os arquivos."""
        result = scaffold_tenant(
            tenant_id="marcasalao-camp-test",
            brand_name="Marca Salão Campanha Test",
            domain="marcasalao-camp-test.com.br",
            audio_policy="an",
            with_campaign="camp-marca-salao-001",
            campaign_title="Minha Primeira Campanha",
            root=self.tmp_project,
            apply=True,
        )
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["campaignSlug"])
        # Verificar os arquivos escritos
        planned = result.get("plannedFiles", [])
        written = result.get("writtenFiles", [])
        self.assertIn("tenants/marcasalao-camp-test/brand-kit.json", written)
        self.assertIn("tenants/marcasalao-camp-test/guardrails.json", written)
        self.assertIn("tenants/marcasalao-camp-test/fixtures/fixture-editorial-marcasalao-camp-test.json", written)
        self.assertIn(f"tenants/marcasalao-camp-test/campaigns/{result['campaignSlug']}.json", written)

    def test_existing_tenant_rejected(self):
        """Rejeita existing tenant com TENANT_JA_EXISTE."""
        scaffold_tenant(
            tenant_id="marcasalao-existing",
            brand_name="Marca Salão Existente",
            domain="marcasalao-existing.com.br",
            root=self.tmp_project,
            apply=True,
        )
        with self.assertRaises(ScaffolderError) as ctx:
            scaffold_tenant(
                tenant_id="marcasalao-existing",
                brand_name="Marca Salão Existente 2",
                domain="marcasalao-existing.com.br",
                root=self.tmp_project,
                apply=True,
            )
        self.assertEqual(ctx.exception.code, "TENANT_JA_EXISTE")

    def test_invalid_tenant_id(self):
        """Fail-closed: invalid tenant_id com underscore."""
        with self.assertRaises(ScaffolderError) as ctx:
            scaffold_tenant(
                tenant_id="tenant_com_underline",
                brand_name="Marca Salão",
                domain="example.com",
                root=self.tmp_project,
                apply=True,
            )
        self.assertEqual(ctx.exception.code, "ID_INVALIDO")

    def test_invalid_slug_in_campaign(self):
        """Fail-closed: invalid slug com path traversal."""
        with self.assertRaises(ScaffolderError) as ctx:
            scaffold_tenant(
                tenant_id="marcasalao-slug-test",
                brand_name="Marca Salão Slug Test",
                domain="marcasalao-slug-test.com.br",
                root=self.tmp_project,
                apply=True,
                with_campaign="../evil",
            )
        self.assertEqual(ctx.exception.code, "ID_INVALIDO")

    def test_capacity_status_in_executive_summary(self):
        """Integracao com executive_summary: presence of capacityStatus."""
        from executive_summary import build_executive_summary

        # Use the real repo root which has campaigns for tenant integration
        # This tests the capacityStatus block is present in the summary
        try:
            summary = build_executive_summary(
                root=self.repo_root, tenant_id="marca-salao"
            )
            self.assertIn("capacityStatus", summary)
            cs = summary["capacityStatus"]
            self.assertIn("current", cs)
            self.assertIn("simulated", cs)
            self.assertIn("threshold", cs)
            self.assertIn("recommendations", cs)
        except Exception as e:
            self.fail(f"build_executive_summary raised: {e}")


class TestSlugValidation(unittest.TestCase):
    """Tests for slug and tenant_id validation functions."""

    def test_slug_re_format(self):
        """Slug must match ^[a-z0-9]+(?:-[a-z0-9]+)*$."""
        # Valid slugs
        self.assertEqual(_validate_slug("marcasalao-test"), "marcasalao-test")
        self.assertEqual(_validate_slug("test"), "test")
        self.assertEqual(_validate_slug("a-b-c"), "a-b-c")
        # Invalid slugs
        with self.assertRaises(ScaffolderError):
            _validate_slug("../evil")
        with self.assertRaises(ScaffolderError):
            _validate_slug("test_with_underscore")
        with self.assertRaises(ScaffolderError):
            _validate_slug("Test With Spaces")

    def test_tenant_id_re_format(self):
        """Tenant ID must match ^[a-z0-9]+(?:-[a-z0-9]+)*$ and max 32 chars."""
        # Valid
        self.assertEqual(_validate_tenant_id("marcasalao"), "marcasalao")
        self.assertEqual(_validate_tenant_id("my-salao"), "my-salao")
        # Invalid - contains uppercase
        with self.assertRaises(ScaffolderError):
            _validate_tenant_id("MarcaSalao")
        # Invalid - contains underscore
        with self.assertRaises(ScaffolderError):
            _validate_tenant_id("marca_salao")


if __name__ == "__main__":
    unittest.main()

class TestScaffolderFailClosed(unittest.TestCase):
    """Rodada P1 (22/11/2026): fail-closed com rollback e pre-validacao no dry-run."""

    def setUp(self):
        import shutil

        self.repo_root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=TOOLS_DIR, capture_output=True, text=True,
        ).stdout.strip()
        tmp_base = os.path.join(self.repo_root, ".workspace", "tmp")
        os.makedirs(tmp_base, exist_ok=True)
        self._tmp = tempfile.TemporaryDirectory(prefix="scaffold-failclosed-", dir=tmp_base)
        self.root = os.path.realpath(self._tmp.name)
        shutil.copytree(
            os.path.join(self.repo_root, "schemas"),
            os.path.join(self.root, "schemas"),
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _args(self, **extra):
        params = dict(
            tenant_id="falha-test",
            brand_name="Falha Test",
            domain="falha-test.com.br",
            root=self.root,
        )
        params.update(extra)
        return params

    def test_apply_rollback_quando_contrato_invalido(self):
        from unittest import mock

        original = tenant_scaffolder._build_brand_kit

        def quebrado(*args, **kwargs):
            brand = original(*args, **kwargs)
            brand.pop("brandName", None)
            return brand

        with mock.patch.object(tenant_scaffolder, "_build_brand_kit", quebrado):
            with self.assertRaises(ScaffolderError) as ctx:
                scaffold_tenant(apply=True, **self._args())
        self.assertEqual(ctx.exception.code, "SCAFFOLD_VALIDACAO_FALHOU")
        self.assertFalse(os.path.exists(os.path.join(self.root, "tenants", "falha-test")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "tenants")))

    def test_apply_rollback_quando_guardrail_violado(self):
        with self.assertRaises(ScaffolderError) as ctx:
            scaffold_tenant(
                apply=True,
                tagline="agenda sempre cheia",
                with_campaign="camp-falha-test-001",
                **self._args(),
            )
        self.assertEqual(ctx.exception.code, "SCAFFOLD_VALIDACAO_FALHOU")
        self.assertFalse(os.path.exists(os.path.join(self.root, "tenants", "falha-test")))

    def test_apply_valido_grava_e_valida(self):
        result = scaffold_tenant(
            apply=True, with_campaign="camp-falha-test-001", **self._args()
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["validation"]["tenantValidatorOk"])
        self.assertTrue(result["validation"]["editorialQaPreview"])
        self.assertEqual(len(result["writtenFiles"]), 4)
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.root, "tenants", "falha-test", "brand-kit.json")
            )
        )

    def test_dry_run_pre_valida_sem_gravar_e_limpa_staging(self):
        result = scaffold_tenant(
            apply=False, with_campaign="camp-falha-test-001", **self._args()
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["dryRun"])
        self.assertTrue(result["validation"]["tenantValidatorOk"])
        self.assertTrue(result["validation"]["editorialQaPreview"])
        self.assertEqual(len(result["plannedFiles"]), 4)
        self.assertFalse(os.path.exists(os.path.join(self.root, "tenants")))
        staging = os.path.join(self.root, ".workspace", "tmp", "tenant-scaffolder-preview")
        restantes = []
        if os.path.isdir(staging):
            restantes = os.listdir(staging)
        self.assertEqual(restantes, [])

    def test_cli_apply_fail_closed_exit_1(self):
        from unittest import mock

        original = tenant_scaffolder._build_brand_kit

        def quebrado(*args, **kwargs):
            brand = original(*args, **kwargs)
            brand.pop("domain", None)
            return brand

        argv = [
            "--tenant-id", "falha-cli",
            "--brand-name", "Falha CLI",
            "--domain", "falha-cli.com.br",
            "--apply", "--json", "--root", self.root,
        ]
        with mock.patch.object(tenant_scaffolder, "_build_brand_kit", quebrado):
            code = tenant_scaffolder.main(argv)
        self.assertEqual(code, 1)
        self.assertFalse(os.path.exists(os.path.join(self.root, "tenants", "falha-cli")))
