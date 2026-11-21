"""Testes automatizados (unittest) para tools/publish_bundler.py (Etapa 11).

Cobre 6 casos:
  1. pack_bundle gera .zip + manifesto com autoPublish:false e itens indexados.
  2. verify_bundle aprova bundle valido (SHA-256, entradas ordenadas, manifesto).
  3. pack_bundle bloqueia campanha nao aprovada (falha fechada, sem ZIP).
  4. --allow-unapproved empacota previo com selo PREVIA_NAO_APROVADA.
  5. verify_bundle rejeita bundle adulterado (hash divergente / entrada ausente).
  6. Contencao de caminho: bundle fora da raiz e nomes invalidos reprovam.

Todos os testes rodam em uma raiz temporaria (.workspace/tmp/) com copia de
tenants/, schemas/ e entregas. Nenhum arquivo versionado e regravado.
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

import publish_bundler
import render_local
import tenant_validator

TENANTS = ("clinica-vital", "estudio-flow", "marca-salao", "meu-salao", "multitrack-hub")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_json(path: str, doc: dict) -> None:
    os.makedirs(render_local.fs_path(os.path.dirname(path)), exist_ok=True)
    with open(render_local.fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(doc, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _read_json(path: str) -> dict:
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _fake_video_bytes(seed: str) -> bytes:
    return b"\x00\x00\x00\x18ftypmp42" + seed.encode("utf-8") * 8


def _build_fixture(root: str) -> None:
    """Raiz temporaria com tenants, schemas, entregas e .workspace/archives."""
    shutil.copytree(
        render_local.fs_path(os.path.join(REPO_ROOT, "tenants")),
        render_local.fs_path(os.path.join(root, "tenants")),
    )
    shutil.copytree(
        render_local.fs_path(os.path.join(REPO_ROOT, "schemas")),
        render_local.fs_path(os.path.join(root, "schemas")),
    )

    for tenant_id in TENANTS:
        delivery_src = os.path.join(
            REPO_ROOT, "02-reels-shorts", "deliveries", tenant_id
        )
        if not os.path.isdir(render_local.fs_path(delivery_src)):
            continue
        for slug in sorted(os.listdir(render_local.fs_path(delivery_src))):
            src = os.path.join(delivery_src, slug)
            if not os.path.isdir(render_local.fs_path(src)):
                continue
            dst = os.path.join(root, "02-reels-shorts", "deliveries", tenant_id, slug)
            os.makedirs(render_local.fs_path(dst), exist_ok=True)

            # Copia os arquivos reais da entrega (manifest, srt, narracao,
            # storyboard) para que os hashes do manifesto conferam com o disco.
            for name in os.listdir(render_local.fs_path(src)):
                src_name = os.path.join(src, name)
                if not os.path.isfile(render_local.fs_path(src_name)):
                    continue
                shutil.copyfile(
                    render_local.fs_path(src_name),
                    render_local.fs_path(os.path.join(dst, name)),
                )

            manifest = _read_json(os.path.join(dst, "manifest.json"))

            archives = os.path.join(root, ".workspace", "archives", slug)
            os.makedirs(render_local.fs_path(archives), exist_ok=True)

            # MP4 simulado no .workspace/archives com hash coerente ao manifesto.
            video_rel = f".workspace/archives/{slug}/{slug}.mp4"
            video_abs = os.path.join(root, *video_rel.split("/"))
            payload = _fake_video_bytes(f"{slug}-9x16")
            with open(render_local.fs_path(video_abs), "wb") as handle:
                handle.write(payload)
            video = manifest.setdefault("artifacts", {}).setdefault("video", {})
            video["archivePath"] = video_rel
            video["sha256"] = _sha256_bytes(payload)
            video["bytes"] = len(payload)

            _write_json(os.path.join(dst, "manifest.json"), manifest)


def _write_approvals(root: str, entries: list[dict]) -> str:
    rel = ".workspace/tmp/aprovacoes-titular.json"
    _write_json(os.path.join(root, *rel.split("/")), {"schemaVersion": 2, "campanhas": entries})
    return rel


class PublishBundlerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        tmp_root = os.path.join(REPO_ROOT, ".workspace", "tmp")
        os.makedirs(tmp_root, exist_ok=True)
        cls._tmp = tempfile.TemporaryDirectory(prefix="publish-bundler-test-", dir=tmp_root)
        cls.root = os.path.realpath(cls._tmp.name)
        _build_fixture(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        # Cada teste começa sem aprovacoes nem bundles persistidos (isolamento de estado).
        aprova = os.path.join(self.root, ".workspace", "tmp", "aprovacoes-titular.json")
        if os.path.isfile(render_local.fs_path(aprova)):
            os.remove(render_local.fs_path(aprova))
        bundles_root = os.path.join(self.root, ".workspace", "bundles")
        if os.path.isdir(render_local.fs_path(bundles_root)):
            shutil.rmtree(render_local.fs_path(bundles_root))

    def _pack(self, tenant_id: str, slug: str, **kwargs) -> dict:
        return publish_bundler.pack_bundle(
            root=self.root, tenant_id=tenant_id, slug=slug, **kwargs
        )

    # ------------------------------------------------------------------
    # 1. pack_bundle gera .zip + manifesto com autoPublish:false
    # ------------------------------------------------------------------
    def test_01_pack_creates_zip_and_manifest(self) -> None:
        _write_approvals(
            self.root,
            [{"tenantId": "marca-salao", "slug": "camp-saas-demo-marca-salao-001", "decisao": "aprovado"}],
        )
        res = self._pack("marca-salao", "camp-saas-demo-marca-salao-001")
        self.assertTrue(res["ok"])
        self.assertIs(res["autoPublish"], False)
        self.assertEqual(res["tenantId"], "marca-salao")
        self.assertEqual(res["slug"], "camp-saas-demo-marca-salao-001")
        self.assertEqual(res["approvalStatus"], "APROVADO_PELO_TITULAR")
        self.assertGreater(res["itemCount"], 0)
        self.assertTrue(os.path.isfile(render_local.fs_path(os.path.join(self.root, res["bundlePath"]))))
        self.assertTrue(os.path.isfile(render_local.fs_path(os.path.join(self.root, res["manifestPath"]))))
        self.assertGreater(res["bundleBytes"], 0)
        self.assertEqual(len(res["bundleSha256"]), 64)

    # ------------------------------------------------------------------
    # 2. verify_bundle aprova bundle valido
    # ------------------------------------------------------------------
    def test_02_verify_bundle_valido(self) -> None:
        _write_approvals(
            self.root,
            [{"tenantId": "marca-salao", "slug": "camp-saas-demo-marca-salao-001", "decisao": "aprovado"}],
        )
        pack = self._pack("marca-salao", "camp-saas-demo-marca-salao-001")
        bundle_abs = os.path.join(self.root, pack["bundlePath"])
        result = publish_bundler.verify_bundle(bundle_abs, root=self.root)
        self.assertTrue(result["ok"])
        self.assertIs(result["autoPublish"], False)
        self.assertEqual(result["bundleSha256"], pack["bundleSha256"])
        self.assertGreaterEqual(result["zipEntryCount"], 1)

    # ------------------------------------------------------------------
    # 3. pack_bundle bloqueia campanha nao aprovada (falha fechada)
    # ------------------------------------------------------------------
    def test_03_nao_aprovado_sem_allow_unapproved(self) -> None:
        with self.assertRaises(publish_bundler.PublishBundlerError) as ctx:
            self._pack("marca-salao", "camp-saas-demo-marca-salao-001")
        self.assertEqual(ctx.exception.code, "CAMPANHA_NAO_APROVADA")
        # Nenhum ZIP gravado para campanha sem aprovacao.
        bundle_dir = os.path.join(
            self.root, ".workspace", "bundles", "marca-salao", "camp-saas-demo-marca-salao-001"
        )
        self.assertFalse(os.path.isdir(render_local.fs_path(bundle_dir)))

    def test_04_decisao_ajuste_nunca_entra(self) -> None:
        _write_approvals(
            self.root,
            [{"tenantId": "marca-salao", "slug": "camp-saas-demo-marca-salao-001", "decisao": "ajuste"}],
        )
        with self.assertRaises(publish_bundler.PublishBundlerError) as ctx:
            self._pack("marca-salao", "camp-saas-demo-marca-salao-001")
        self.assertEqual(ctx.exception.code, "SLOT_EM_AJUSTE")

    # ------------------------------------------------------------------
    # 4. --allow-unapproved empacota previo com PREVIA_NAO_APROVADA
    # ------------------------------------------------------------------
    def test_05_allow_unapproved_selo_previo(self) -> None:
        res = self._pack("marca-salao", "camp-saas-demo-marca-salao-001", allow_unapproved=True)
        self.assertTrue(res["ok"])
        self.assertEqual(res["approvalStatus"], "PREVIA_NAO_APROVADA")
        self.assertTrue(res["allowUnapproved"])
        bundle_abs = os.path.join(self.root, res["bundlePath"])
        result = publish_bundler.verify_bundle(bundle_abs, root=self.root)
        self.assertTrue(result["ok"])

    # ------------------------------------------------------------------
    # 5. verify_bundle rejeita bundle adulterado
    # ------------------------------------------------------------------
    def test_06_verify_rejeita_bundle_adulterado(self) -> None:
        _write_approvals(
            self.root,
            [{"tenantId": "marca-salao", "slug": "camp-saas-demo-marca-salao-001", "decisao": "aprovado"}],
        )
        pack = self._pack("marca-salao", "camp-saas-demo-marca-salao-001")
        bundle_abs = os.path.join(self.root, pack["bundlePath"])

        # Adiciona um byte ao final do ZIP (diverge do SHA-256 declarado).
        with open(render_local.fs_path(bundle_abs), "ab") as handle:
            handle.write(b"X")
        result = publish_bundler.verify_bundle(bundle_abs, root=self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(any(p["code"] == "HASH_DIVERGENTE" for p in result["problems"]))

    # ------------------------------------------------------------------
    # 6. Contencao de caminho e nomes invalidos
    # ------------------------------------------------------------------
    def test_07_nomes_invalidos_reprovados(self) -> None:
        with self.assertRaises(publish_bundler.PublishBundlerError) as ctx:
            self._pack("tenant com espacos", "slug")
        self.assertEqual(ctx.exception.code, "NOME_INVALIDO")

        with self.assertRaises(publish_bundler.PublishBundlerError) as ctx:
            self._pack("marca-salao", "../escape")
        self.assertEqual(ctx.exception.code, "NOME_INVALIDO")

    def test_08_bundle_fora_da_raiz(self) -> None:
        fora = os.path.join(self.root, "..", "fora", "bundle.zip")
        with self.assertRaises(publish_bundler.PublishBundlerError) as ctx:
            publish_bundler.verify_bundle(fora, root=self.root)
        self.assertEqual(ctx.exception.code, "BUNDLE_FORA_DA_RAIZ")

    # ------------------------------------------------------------------
    # CLI: pack + verify --json exit 0
    # ------------------------------------------------------------------
    def test_09_cli_pack_verify_json_exit_zero(self) -> None:
        _write_approvals(
            self.root,
            [{"tenantId": "marca-salao", "slug": "camp-saas-demo-marca-salao-001", "decisao": "aprovado"}],
        )
        proc_pack = subprocess.run(
            [
                sys.executable,
                os.path.abspath(publish_bundler.__file__),
                "pack",
                "--tenant", "marca-salao",
                "--slug", "camp-saas-demo-marca-salao-001",
                "--root", self.root,
                "--json",
            ],
            capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
        self.assertEqual(proc_pack.returncode, 0, proc_pack.stderr)
        doc_pack = json.loads(proc_pack.stdout)
        self.assertTrue(doc_pack["ok"])

        bundle_rel = doc_pack["bundlePath"]
        proc_verify = subprocess.run(
            [
                sys.executable,
                os.path.abspath(publish_bundler.__file__),
                "verify",
                "--bundle", bundle_rel,
                "--root", self.root,
                "--json",
            ],
            capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
        self.assertEqual(proc_verify.returncode, 0, proc_verify.stderr)
        doc_verify = json.loads(proc_verify.stdout)
        self.assertTrue(doc_verify["ok"])


if __name__ == "__main__":
    unittest.main()
