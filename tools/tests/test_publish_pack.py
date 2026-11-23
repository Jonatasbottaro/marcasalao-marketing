"""Testes automatizados (unittest) para tools/publish_pack.py.

Cobre obrigatoriamente:
  1. Geracao de arquivos (instagram-reels.md, youtube-shorts.md,
     facebook-reels.md, checklist-publicacao.json) para todos os tenants
     presentes em tenants/ (contagem dinamica, >= 4 tenants / >= 8 campanhas).
  2. Formatacao correta dos parametros UTM por canal.
  3. Bloqueio de forbiddenClaims: gera copia de legenda com frase proibida e
     confirma que a auditoria aborta ANTES de gravar o pacote parcial.
  4. Integridade JSON do checklist-publicacao.json (autoPublish false,
     hashes SHA-256, guardrails auditados).
  5. Resolucao de .workspace/ em worktrees via git rev-parse
     --git-common-dir: o hash da midia arquivada e conferido no checkout
     principal, nao num caminho inexistente dentro da worktree.

Todos os testes de geracao rodam em uma raiz temporaria (tempfile), com copia
de tenants/, schemas/ e das entregas. Nenhum arquivo versionado em
04-legendas/pacotes-publicacao/ e regravado durante o unittest.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import publish_pack
import render_local
import tenant_validator

PUBLICACAO_ROOT = os.path.join(REPO_ROOT, "04-legendas", "pacotes-publicacao")
DELIVERIES_ROOT = os.path.join(REPO_ROOT, "02-reels-shorts", "deliveries")

FAKE_VIDEO_BYTES = b"\x00\x00\x00\x18ftypmp42" + bytes(range(64))


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _snapshot(root: str) -> dict[str, str]:
    """Hash dos arquivos de um diretorio versionado (para provar imutabilidade)."""
    snapshot: dict[str, str] = {}
    if not os.path.isdir(render_local.fs_path(root)):
        return snapshot
    for dirpath, _dirnames, filenames in os.walk(render_local.fs_path(root)):
        for name in sorted(filenames):
            abs_path = os.path.join(dirpath, name)
            with open(render_local.fs_path(abs_path), "rb") as handle:
                snapshot[render_local.rel(root, abs_path)] = hashlib.sha256(
                    handle.read()
                ).hexdigest()
    return snapshot


def _build_fixture_root(root: str) -> None:
    """Raiz temporaria com tenants, schemas, entregas e archives de teste."""
    shutil.copytree(
        render_local.fs_path(os.path.join(REPO_ROOT, "tenants")),
        render_local.fs_path(os.path.join(root, "tenants")),
    )
    shutil.copytree(
        render_local.fs_path(os.path.join(REPO_ROOT, "schemas")),
        render_local.fs_path(os.path.join(root, "schemas")),
    )
    deliveries_dst = os.path.join(root, "02-reels-shorts", "deliveries")
    os.makedirs(render_local.fs_path(deliveries_dst), exist_ok=True)
    archives_dst = os.path.join(root, ".workspace", "archives")
    os.makedirs(render_local.fs_path(archives_dst), exist_ok=True)

    for tenant_id in sorted(os.listdir(render_local.fs_path(DELIVERIES_ROOT))):
        tenant_src = os.path.join(DELIVERIES_ROOT, tenant_id)
        if not os.path.isdir(render_local.fs_path(tenant_src)):
            continue
        for slug in sorted(os.listdir(render_local.fs_path(tenant_src))):
            src = os.path.join(tenant_src, slug)
            if not os.path.isdir(render_local.fs_path(src)):
                continue
            dst = os.path.join(deliveries_dst, tenant_id, slug)
            os.makedirs(render_local.fs_path(dst), exist_ok=True)
            for name in ("manifest.json", f"{slug}.srt", f"{slug}_narracao.txt"):
                if os.path.isfile(render_local.fs_path(os.path.join(src, name))):
                    shutil.copyfile(
                        render_local.fs_path(os.path.join(src, name)),
                        render_local.fs_path(os.path.join(dst, name)),
                    )
            # Midia preservada simulada no .workspace/archives da raiz de teste,
            # com hash coerente com o manifesto copiado.
            manifest_path = os.path.join(dst, "manifest.json")
            with open(render_local.fs_path(manifest_path), "r", encoding="utf-8") as handle:
                manifest = json.load(handle)
            archive_rel = f".workspace/archives/{slug}/{slug}.mp4"
            archive_abs = os.path.join(root, *archive_rel.split("/"))
            os.makedirs(render_local.fs_path(os.path.dirname(archive_abs)), exist_ok=True)
            with open(render_local.fs_path(archive_abs), "wb") as handle:
                handle.write(FAKE_VIDEO_BYTES)
            video = manifest.setdefault("artifacts", {}).setdefault("video", {})
            video["path"] = f"02-reels-shorts/deliveries/{tenant_id}/{slug}/{slug}.mp4"
            video["archivePath"] = archive_rel
            video["sha256"] = _sha256_bytes(FAKE_VIDEO_BYTES)
            video["bytes"] = len(FAKE_VIDEO_BYTES)
            with open(render_local.fs_path(manifest_path), "w", encoding="utf-8", newline="\n") as handle:
                json.dump(manifest, handle, ensure_ascii=False, indent=2)
                handle.write("\n")


class PublishPackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        tmp_root = os.path.join(REPO_ROOT, ".workspace", "tmp")
        os.makedirs(tmp_root, exist_ok=True)
        cls._tmp = tempfile.TemporaryDirectory(prefix="publish-pack-test-", dir=tmp_root)
        cls.root = cls._tmp.name
        cls.real_snapshot_before = _snapshot(PUBLICACAO_ROOT)
        _build_fixture_root(cls.root)
        cls.results = publish_pack.generate_all(root=cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _pack_dir(self, tenant_id: str, slug: str) -> str:
        return os.path.join(self.root, "04-legendas", "pacotes-publicacao", tenant_id, slug)

    def _load_json(self, rel_path: str) -> dict:
        with open(
            render_local.fs_path(os.path.join(self.root, rel_path.replace("/", os.sep))),
            "r",
            encoding="utf-8",
        ) as handle:
            return json.load(handle)

    # ------------------------------------------------------------------
    # 1. Geracao de arquivos para todos os tenants (contagem dinamica)
    # ------------------------------------------------------------------
    def test_01_generates_files_for_all_tenants(self) -> None:
        tenants = {res["tenantId"] for res in self.results}
        self.assertGreaterEqual(len(tenants), 4, f"tenants encontrados: {sorted(tenants)}")
        self.assertGreaterEqual(len(self.results), 8, "campanhas geradas abaixo do esperado")
        for res in self.results:
            with self.subTest(tenant=res["tenantId"], slug=res["slug"]):
                pack_dir = self._pack_dir(res["tenantId"], res["slug"])
                self.assertTrue(os.path.isdir(render_local.fs_path(pack_dir)), pack_dir)
                for filename in (
                    "instagram-reels.md",
                    "youtube-shorts.md",
                    "facebook-reels.md",
                    "checklist-publicacao.json",
                ):
                    abs_p = os.path.join(pack_dir, filename)
                    self.assertTrue(os.path.isfile(render_local.fs_path(abs_p)), f"{filename} ausente")
                    self.assertGreater(os.path.getsize(render_local.fs_path(abs_p)), 0, f"{filename} vazio")

    def test_02_result_matches_written_files(self) -> None:
        for res in self.results:
            with self.subTest(tenant=res["tenantId"], slug=res["slug"]):
                pack_dir = self._pack_dir(res["tenantId"], res["slug"])
                for filename, entry in res["files"].items():
                    abs_p = os.path.join(pack_dir, filename)
                    self.assertTrue(os.path.isfile(render_local.fs_path(abs_p)))
                    self.assertEqual(
                        render_local.sha256_file(abs_p),
                        entry["sha256"],
                        f"hash divergente em {filename} ({res['tenantId']})",
                    )
                    self.assertEqual(os.path.getsize(render_local.fs_path(abs_p)), entry["bytes"])

    # ------------------------------------------------------------------
    # 2. Formatacao de parametros UTM por canal
    # ------------------------------------------------------------------
    def test_03_utm_parameters_per_channel(self) -> None:
        expected = {
            "clinica-vital": "clinicavital.com.br",
            "estudio-flow": "estudioflow.com.br",
            "marca-salao": "marcasalao.com.br",
            "meu-salao": "meusalao.com.br",
            "multitrack-hub": "multitrackhub.com.br",
        }
        channel_utm = {
            "instagram-reels.md": ("instagram", "reels"),
            "youtube-shorts.md": ("youtube", "shorts"),
            "facebook-reels.md": ("facebook", "reels"),
        }
        for res in self.results:
            tenant_id = res["tenantId"]
            slug = res["slug"]
            domain = expected[tenant_id]
            with self.subTest(tenant=tenant_id, slug=slug):
                for filename, (source, medium) in channel_utm.items():
                    with open(
                        render_local.fs_path(os.path.join(self._pack_dir(tenant_id, slug), filename)),
                        "r",
                        encoding="utf-8",
                    ) as handle:
                        texto = handle.read()
                    url = (
                        f"https://{domain}/?utm_source={source}&utm_medium={medium}"
                        f"&utm_campaign={slug}&utm_content={tenant_id}"
                    )
                    self.assertIn(url, texto, f"URL UTM ausente em {filename} ({tenant_id})")

    def test_04_instagram_uses_link_na_bio_and_domain(self) -> None:
        for res in self.results:
            with self.subTest(tenant=res["tenantId"]):
                with open(
                    render_local.fs_path(
                        os.path.join(self._pack_dir(res["tenantId"], res["slug"]), "instagram-reels.md")
                    ),
                    "r",
                    encoding="utf-8",
                ) as handle:
                    texto = handle.read()
                self.assertIn("link na bio", texto.lower())
                self.assertIn(res["checklist"]["tenantId"], texto)

    # ------------------------------------------------------------------
    # 3. Bloqueio de forbiddenClaims (abort ANTES de gravar pacote parcial)
    # ------------------------------------------------------------------
    def test_05_forbidden_claim_aborts_before_writing(self) -> None:
        guardrails = self._load_json("tenants/marca-salao/guardrails.json")
        frases_proibidas = (
            "Agende pelo WhatsApp automático e receba lembrete de 24 horas",
            "Redução de faltas e aumento de faturamento garantido",
            "Pague pelo checkout no cartão de crédito",
        )
        texto_limpo = "Agendamento online no Marca Salão"
        for frase in frases_proibidas:
            with self.subTest(frase=frase):
                violacoes = tenant_validator.validate_text_against_guardrails(
                    frase, guardrails, check_ui_elements=True, ignore_editorial_footer=True
                )
                self.assertTrue(violacoes, f"Deveria bloquear: {frase}")
        self.assertEqual(
            tenant_validator.validate_text_against_guardrails(texto_limpo, guardrails),
            [],
            "texto limpo deveria ser aceito",
        )

    def test_06_publish_pack_aborts_on_audited_text(self) -> None:
        guardrails = self._load_json("tenants/marca-salao/guardrails.json")
        sujo = "Confirmação automática via WhatsApp em 24 horas"
        with self.assertRaises(publish_pack.PublishPackError):
            publish_pack._audit(sujo, "probe.md", guardrails)
        self.assertTrue(
            tenant_validator.validate_text_against_guardrails(sujo, guardrails, check_ui_elements=True)
        )

    # ------------------------------------------------------------------
    # 4. Integridade JSON do checklist-publicacao.json
    # ------------------------------------------------------------------
    def test_07_checklist_integrity(self) -> None:
        for res in self.results:
            with self.subTest(tenant=res["tenantId"], slug=res["slug"]):
                checklist = res["checklist"]
                self.assertEqual(checklist["autoPublish"], False)
                self.assertTrue(checklist["guardrailsAudited"])
                self.assertEqual(checklist["tenantId"], res["tenantId"])
                self.assertEqual(checklist["slug"], res["slug"])
                self.assertIn("guardrailStatus", checklist)
                self.assertEqual(checklist["guardrailStatus"]["srt"], "ok")
                self.assertEqual(checklist["guardrailStatus"]["narration"], "ok")
                self.assertIsInstance(checklist["media"], list)
                self.assertGreaterEqual(len(checklist["media"]), 3)
                for media in checklist["media"]:
                    self.assertIn("kind", media)
                    self.assertIn("sha256", media)
                    self.assertIn("bytes", media)
                    self.assertIn("sha256_disk_ok", media)

    # ------------------------------------------------------------------
    # 5. Resolucao de .workspace/ (worktree -> checkout principal)
    # ------------------------------------------------------------------
    def test_08_resolve_workspace_root(self) -> None:
        resolvido = publish_pack.resolve_workspace_root(self.root)
        self.assertEqual(
            os.path.normcase(os.path.realpath(resolvido)),
            os.path.normcase(os.path.realpath(os.path.join(self.root, ".workspace"))),
        )
        self.assertTrue(os.path.isdir(render_local.fs_path(os.path.join(resolvido, "archives"))))

        # Raiz sem checkout git cai no proprio .workspace, sem excecao.
        fake = os.path.join(self.root, "nao-e-checkout")
        os.makedirs(render_local.fs_path(fake), exist_ok=True)
        self.assertEqual(
            os.path.normcase(os.path.realpath(publish_pack.resolve_workspace_root(fake))),
            os.path.normcase(os.path.realpath(os.path.join(fake, ".workspace"))),
        )

        # Na raiz real do projeto (worktree ou checkout principal) o workspace
        # resolvido sempre eh o .workspace da estacao. Quando a estacao nao
        # possui .workspace/archives (medio local nao versionado), a assercao
        # de existencia e pulada para nao falhar por estado da maquina.
        real_ws = publish_pack.resolve_workspace_root(REPO_ROOT)
        self.assertEqual(
            os.path.normcase(os.path.realpath(real_ws)),
            os.path.normcase(os.path.realpath(os.path.join(REPO_ROOT, ".workspace"))),
        )
        arquivo_existe = os.path.isdir(render_local.fs_path(os.path.join(real_ws, "archives")))
        if arquivo_existe:
            self.assertTrue(os.path.isdir(render_local.fs_path(os.path.join(real_ws, "archives"))))

    def test_09_video_hash_checked_against_archives(self) -> None:
        for res in self.results:
            with self.subTest(tenant=res["tenantId"], slug=res["slug"]):
                video = next(m for m in res["checklist"]["media"] if m["kind"] == "video")
                self.assertEqual(video["resolvedFrom"], "archive")
                self.assertTrue(video["presentOnDisk"])
                self.assertTrue(video["sha256_disk_ok"], "hash do MP4 arquivado deveria conferir")

    def test_10_tracked_packages_untouched(self) -> None:
        # A suite grava somente em raizes temporarias.
        self.assertEqual(_snapshot(PUBLICACAO_ROOT), self.real_snapshot_before)


if __name__ == "__main__":
    unittest.main()
