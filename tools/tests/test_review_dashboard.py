"""Testes automatizados (unittest) para tools/review_dashboard.py (Etapa 4 - Agente 2).

Cobre obrigatoriamente (brief expandido da Etapa 4):
  1. Build estatico gerando index.html, portal-data.json e README.md com
     4 tenants e 8 campanhas; CLI --build --json encerra com codigo 0.
  2. Sanitizacao de paths: zero ocorrencias de caminhos absolutos do host
     (D:/, C:/) em portal-data.json e no bloco embutido do index.html.
  3. Escape seguro de HTML/JSON: strings hostis (</script>, aspas, tags)
     nao quebram o script embutido e fazem roundtrip identico.
  4. Resolucao de .workspace/ em worktrees via git rev-parse
     --git-common-dir (raiz principal) e fallback para raizes sem git.
  5. Servidor HTTP efemero (port=0): /, /api/health, /api/data,
     /media/storyboard|cover|formats/<tenant>/<slug>,
     /media/video/<tenant>/<slug>/<variante> com Range (200/206/416),
     travessia de caminho bloqueada (404) e metodos de escrita recusados
     (exceto POST /api/approvals).
  6. Roundtrip POST + GET /api/approvals persistindo em
     .workspace/tmp/aprovacoes-titular.json com validacao estrita de
     schema e limpeza apos o teste.
  7. autoPublish: false e URLs UTM nos 3 canais para as 8 campanhas;
     guardrails por tenant (rotas autorizadas e claims bloqueados).
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import shutil
import subprocess
import sys
import threading
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import render_local
import review_dashboard

PORTAL_DIR = os.path.join(REPO_ROOT, "05-review-portal")
TMP_DIR = os.path.join(REPO_ROOT, ".workspace", "tmp", "etapa4-agente2")

EXPECTED_TENANTS = ("estudio-flow", "marca-salao", "meu-salao", "multitrack-hub")
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

MP4_BYTES = bytes(range(64))
MP4_DERIV_BYTES = bytes(range(64, 128))


def _sha256_abs(path: str) -> str:
    digest = hashlib.sha256()
    with open(render_local.fs_path(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rmtree(path: str) -> None:
    forced = render_local.fs_path(path, force=True)
    if os.path.isdir(forced):
        shutil.rmtree(forced)


def _walk_strings(obj, key=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk_strings(v, k)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_strings(item, key)
    elif isinstance(obj, str):
        yield key, obj


def _http_get(port: int, path: str, headers: dict | None = None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request("GET", path, headers=headers or {})
        resp = conn.getresponse()
        body = resp.read()
        hdrs = {k.lower(): v for k, v in resp.getheaders()}
        return resp.status, body, hdrs
    finally:
        conn.close()


def _http_method(port: int, method: str, path: str):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request(method, path, body=b"x" if method in ("POST", "PUT") else None)
        resp = conn.getresponse()
        body = resp.read()
        return resp.status, body
    finally:
        conn.close()


def _http_post(port: int, path: str, body: bytes):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request(
            "POST",
            path,
            body=body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(body))},
        )
        resp = conn.getresponse()
        return resp.status, resp.read()
    finally:
        conn.close()


def _git(root: str, *args: str) -> str:
    saida = subprocess.run(
        ["git", "-C", root, *args], capture_output=True, text=True, timeout=15
    )
    if saida.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} falhou: {saida.stderr.strip()}")
    return saida.stdout.strip()


def _fake_portal_data() -> dict:
    return {
        "schemaVersion": 1,
        "generatedBy": "tools/review_dashboard.py",
        "deliveriesRoot": "02-reels-shorts/deliveries",
        "pacotesRoot": "04-legendas/pacotes-publicacao",
        "archivesRoot": ".workspace/archives",
        "totals": {"tenants": 1, "campaigns": 1},
        "tenants": [
            {
                "tenantId": "t-tenant",
                "brandName": "Tenant Teste",
                "displayTitle": "TENANT TESTE",
                "monogram": "TT",
                "domain": "t.example",
                "tagline": "TAGLINE",
                "palette": {
                    "primary": "#10B981",
                    "secondary": "#4F8CFF",
                    "accent": "#F5C107",
                    "background": "#121620",
                    "surface": "#222C40",
                    "textPrimary": "#F5F7FA",
                    "textMuted": "#B4C0D2",
                },
                "audioPolicy": {
                    "allowAudioTrack": False,
                    "ffmpegFlag": "-an",
                    "requireSrt": True,
                    "requireExternalNarration": True,
                },
                "routeRules": {},
                "forbiddenClaims": [],
                "forbiddenUiElements": [],
            }
        ],
        "campaigns": [
            {
                "tenantId": "t-tenant",
                "slug": "t-slug",
                "campaignId": "t-slug",
                "titulo": "Tenant Teste",
                "preset": "saas-demo",
                "politicaAudio": "-an",
                "audioStreams": 0,
                "format": {"width": 1080, "height": 1920, "fps": 30, "duration": 30.0},
                "scenes": 4,
                "video": {
                    "archiveRelPath": ".workspace/archives/t-slug/t-slug.mp4",
                    "sha256": "a" * 64,
                    "bytes": 64,
                    "audioStreams": 0,
                    "audioCodec": None,
                    "variants": ["9x16", "1x1"],
                },
                "srt": {
                    "relPath": "02-reels-shorts/deliveries/t-tenant/t-slug/t-slug.srt",
                    "sha256": "b" * 64,
                    "bytes": 10,
                    "text": "1\n00:00:00,000 --> 00:00:02,000\nOi",
                },
                "narracao": {
                    "relPath": "02-reels-shorts/deliveries/t-tenant/t-slug/t-slug_narracao.txt",
                    "sha256": "c" * 64,
                    "bytes": 8,
                    "text": "Narração de teste",
                },
                "storyboard": {
                    "relPath": "02-reels-shorts/deliveries/t-tenant/t-slug/preview-storyboard.png",
                    "sha256": "d" * 64,
                    "bytes": 9,
                    "timestampsSeconds": [2.0, 8.0, 16.0, 24.0],
                },
                "copies": {
                    "instagram": {
                        "relPath": "04-legendas/pacotes-publicacao/t-tenant/t-slug/instagram-reels.md",
                        "text": "Tenant Teste\n\nhttps://t.example/?utm_source=instagram",
                        "utmUrl": "https://t.example/?utm_source=instagram",
                    },
                    "youtube": {
                        "relPath": "04-legendas/pacotes-publicacao/t-tenant/t-slug/youtube-shorts.md",
                        "text": "Tenant Teste\n\nhttps://t.example/?utm_source=youtube",
                        "utmUrl": "https://t.example/?utm_source=youtube",
                    },
                    "facebook": {
                        "relPath": "04-legendas/pacotes-publicacao/t-tenant/t-slug/facebook-reels.md",
                        "text": "Tenant Teste\n\nhttps://t.example/?utm_source=facebook",
                        "utmUrl": "https://t.example/?utm_source=facebook",
                    },
                },
                "pacote": {
                    "checklistRelPath": "04-legendas/pacotes-publicacao/t-tenant/t-slug/checklist-publicacao.json",
                    "guardrailsAudited": True,
                    "guardrailStatus": {"srt": "ok", "narration": "ok"},
                    "autoPublish": False,
                },
            }
        ],
    }


def _doc_aprovacoes() -> dict:
    return {
        "schemaVersion": 2,
        "arquivo": "aprovacoes-titular.json",
        "origem": "05-review-portal",
        "exportadoEm": "2026-11-18T12:00:00Z",
        "revisor": "Titular Teste",
        "resumo": {"totalCampanhas": 1, "aprovadas": 1, "ajustes": 0, "pendentes": 0},
        "campanhas": [
            {
                "tenantId": "t-tenant",
                "slug": "t-slug",
                "campaignId": "t-slug",
                "preset": "saas-demo",
                "politicaAudio": "-an",
                "decisao": "aprovado",
                "locucaoExternaConferida": True,
                "observacoes": "Aprovado no teste",
                "hashes": {
                    "video": "a" * 64,
                    "srt": "b" * 64,
                    "narracao": "c" * 64,
                    "storyboard": "d" * 64,
                },
            }
        ],
    }


class HelpersTest(unittest.TestCase):
    """Unidades internas: hash, UTM e resolucao de .workspace/."""

    def test_01_verify_sha256_ok_and_mismatch(self) -> None:
        os.makedirs(render_local.fs_path(TMP_DIR), exist_ok=True)
        path = os.path.join(TMP_DIR, "hash-probe.txt")
        with open(render_local.fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
            handle.write("conteudo de teste\n")
        good = _sha256_abs(path)
        review_dashboard._verify_sha256(path, good, "probe")
        with self.assertRaises(review_dashboard.ReviewPortalError) as ctx:
            review_dashboard._verify_sha256(path, "0" * 64, "probe")
        self.assertIn("HASH_DIVERGENTE", str(ctx.exception))
        with self.assertRaises(review_dashboard.ReviewPortalError) as ctx:
            review_dashboard._verify_sha256(os.path.join(TMP_DIR, "inexistente.txt"), good, "probe")
        self.assertIn("ARQUIVO_NAO_ENCONTRADO", str(ctx.exception))

    def test_02_extract_utm_url(self) -> None:
        texto = (
            "Conheca o Marca Salao\n\n"
            "https://marcasalao.com.br/?utm_source=instagram&utm_medium=reels"
            "&utm_campaign=camp-x&utm_content=marca-salao\n\n"
            "#MarcaSalao"
        )
        url = review_dashboard._extract_utm_url(texto)
        self.assertIsNotNone(url)
        self.assertTrue(url.startswith("https://"))
        self.assertIn("utm_campaign=camp-x", url)
        self.assertIsNone(review_dashboard._extract_utm_url("sem url aqui"))

    def test_03_resolve_workspace_dir(self) -> None:
        # Worktree (git-dir != git-common-dir): resolve para o .workspace/
        # da raiz principal, mesmo que a worktree tenha .workspace/ proprio.
        common = _git(REPO_ROOT, "rev-parse", "--git-common-dir")
        raiz_principal = os.path.dirname(os.path.abspath(os.path.join(REPO_ROOT, common)))
        esperado = os.path.normpath(os.path.join(raiz_principal, ".workspace"))
        obtido = os.path.normpath(review_dashboard.resolve_workspace_dir(REPO_ROOT))
        self.assertEqual(obtido, esperado)
        self.assertTrue(os.path.isdir(render_local.fs_path(esperado)))

        # Raiz que nao e toplevel de checkout (raiz falsa dentro da worktree):
        # cai no proprio .workspace/.
        fake = os.path.join(TMP_DIR, "resolver-probe")
        _rmtree(fake)
        os.makedirs(render_local.fs_path(os.path.join(fake, ".workspace", "archives")))
        self.assertEqual(
            os.path.normpath(review_dashboard.resolve_workspace_dir(fake)),
            os.path.normpath(os.path.join(fake, ".workspace")),
        )
        _rmtree(fake)

        # Caminho do arquivo de aprovacoes fica dentro do workspace resolvido.
        store = review_dashboard.approvals_store_path(REPO_ROOT)
        self.assertEqual(
            os.path.normpath(store),
            os.path.normpath(os.path.join(esperado, "tmp", "aprovacoes-titular.json")),
        )


class BuildPortalTest(unittest.TestCase):
    """Build consolidado sobre a raiz real da worktree."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = review_dashboard.build_portal(root=REPO_ROOT)
        with open(
            render_local.fs_path(os.path.join(PORTAL_DIR, "portal-data.json")),
            "r",
            encoding="utf-8",
        ) as handle:
            cls.data = json.load(handle)

    def test_04_generates_portal_files(self) -> None:
        for filename in ("index.html", "portal-data.json", "README.md"):
            abs_path = os.path.join(PORTAL_DIR, filename)
            self.assertTrue(os.path.isfile(render_local.fs_path(abs_path)), filename)
            info = self.summary["files"][filename]
            self.assertEqual(info["sha256"], _sha256_abs(abs_path))
            self.assertEqual(info["bytes"], os.path.getsize(render_local.fs_path(abs_path)))
        self.assertTrue(self.summary["ok"])
        self.assertEqual(self.summary["outputDir"], "05-review-portal")

    def test_05_totals_four_tenants_eight_campaigns(self) -> None:
        self.assertEqual(self.summary["totalTenants"], 4)
        self.assertEqual(self.summary["totalCampaigns"], 8)
        self.assertEqual(self.data["totals"], {"tenants": 4, "campaigns": 8})
        self.assertEqual(
            sorted(t["tenantId"] for t in self.data["tenants"]), list(EXPECTED_TENANTS)
        )
        self.assertEqual(
            {(c["tenantId"], c["slug"]) for c in self.data["campaigns"]},
            EXPECTED_CAMPAIGNS,
        )

    def test_06_campaign_fields(self) -> None:
        for c in self.data["campaigns"]:
            with self.subTest(slug=c["slug"]):
                self.assertIn(c["politicaAudio"], ("-an", "AAC"))
                self.assertTrue(c["titulo"])
                self.assertIsInstance(c["titulo"], str)
                fmt = c["format"]
                self.assertEqual(fmt["duration"], 30.0)
                self.assertEqual(fmt["fps"], 30)
                self.assertEqual(fmt["width"], 1080)
                self.assertEqual(fmt["height"], 1920)
                # variante primaria derivada da geometria (1080x1920 -> 9x16)
                self.assertEqual(c["video"]["variants"][0], "9x16")
                self.assertIn("9x16", c["video"]["variants"])
                # opcionais presentes apos a consolidacao da Etapa 4 (agente 1)
                self.assertTrue(c.get("cover"))
                self.assertTrue(c.get("formats"))
                derivs = c.get("derivatives")
                self.assertTrue(derivs)
                self.assertEqual({d["variant"] for d in derivs}, {"1x1", "16x9"})
                self.assertIn("1x1", c["video"]["variants"])
                self.assertIn("16x9", c["video"]["variants"])
                self.assertTrue(c["copies"])
                self.assertTrue(c["pacote"])

    def test_07_hash_integrity_against_disk_and_manifest(self) -> None:
        for c in self.data["campaigns"]:
            with self.subTest(slug=c["slug"]):
                delivery = os.path.join(
                    REPO_ROOT, "02-reels-shorts", "deliveries", c["tenantId"], c["slug"]
                )
                with open(
                    render_local.fs_path(os.path.join(delivery, "manifest.json")),
                    "r",
                    encoding="utf-8",
                ) as handle:
                    manifest = json.load(handle)
                artifacts = manifest["artifacts"]
                self.assertEqual(c["srt"]["sha256"], artifacts["srt"]["sha256"])
                self.assertEqual(
                    c["narracao"]["sha256"], artifacts["narration"]["sha256"]
                )
                self.assertEqual(
                    c["storyboard"]["sha256"], artifacts["storyboard"]["sha256"]
                )
                self.assertEqual(c["video"]["sha256"], artifacts["video"]["sha256"])
                self.assertEqual(
                    c["srt"]["sha256"],
                    _sha256_abs(os.path.join(delivery, c["slug"] + ".srt")),
                )
                self.assertEqual(
                    c["narracao"]["sha256"],
                    _sha256_abs(os.path.join(delivery, c["slug"] + "_narracao.txt")),
                )
                self.assertEqual(
                    c["storyboard"]["sha256"],
                    _sha256_abs(os.path.join(delivery, "preview-storyboard.png")),
                )

    def test_08_no_path_leakage_outside_root(self) -> None:
        with open(
            render_local.fs_path(os.path.join(PORTAL_DIR, "portal-data.json")),
            "r",
            encoding="utf-8",
        ) as handle:
            bruto = handle.read()
        with open(
            render_local.fs_path(os.path.join(PORTAL_DIR, "index.html")),
            "r",
            encoding="utf-8",
        ) as handle:
            html = handle.read()
        for texto in (bruto, html):
            self.assertNotIn("D:/", texto)
            self.assertNotIn("C:/", texto)
            self.assertNotIn("C:\\", texto)
        for key, valor in _walk_strings(self.data):
            if key.endswith(("Path", "Root")):
                self.assertFalse(valor.startswith(("/", "\\")), f"{key}={valor}")
                self.assertNotIn("..", valor)
                self.assertRegex(valor, r"^[A-Za-z0-9_.\-/]")

    def test_09_build_is_deterministic(self) -> None:
        antes = {
            filename: self.summary["files"][filename]["sha256"]
            for filename in ("index.html", "portal-data.json", "README.md")
        }
        resumo2 = review_dashboard.build_portal(root=REPO_ROOT)
        for filename, sha in antes.items():
            self.assertEqual(resumo2["files"][filename]["sha256"], sha, filename)

    def test_10_index_html_ui_markers(self) -> None:
        with open(
            render_local.fs_path(os.path.join(PORTAL_DIR, "index.html")),
            "r",
            encoding="utf-8",
        ) as handle:
            html = handle.read()
        marcadores = (
            'id="painel-metricas"',
            'id="busca"',
            'id="lightbox"',
            'id="filtro-preset"',
            'id="filtro-audio"',
            'id="filtro-status"',
            'id="btn-exportar-aprovacoes"',
            'id="btn-importar-aprovacoes"',
            'id="input-revisor"',
            "Guardrails & Hashes",
            "Aprovado para Publicação Manual",
            "Solicitar Ajuste",
            "Locução externa conferida",
            "reviewPortal.aprovacoes.v2",
            "/media/storyboard/",
            "/media/video/",
            "/api/approvals",
            "/api/health",
        )
        for marcador in marcadores:
            self.assertIn(marcador, html)

    def test_11_auto_publish_false_and_utm_all_channels(self) -> None:
        self.assertEqual(len(self.data["campaigns"]), 8)
        for c in self.data["campaigns"]:
            with self.subTest(slug=c["slug"]):
                self.assertIsNotNone(c["pacote"])
                self.assertIsNot(c["pacote"]["autoPublish"], True)
                self.assertFalse(c["pacote"]["autoPublish"])
                for canal in ("instagram", "youtube", "facebook"):
                    copy = c["copies"][canal]
                    self.assertIn("utm_", copy["utmUrl"], canal)
                    self.assertIn("utm_campaign=", copy["utmUrl"], canal)

    def test_12_tenant_guardrails_fields(self) -> None:
        tenants = {t["tenantId"]: t for t in self.data["tenants"]}
        marca = tenants["marca-salao"]
        self.assertIn("/booking/[salonId]", marca["routeRules"])
        rota = marca["routeRules"]["/booking/[salonId]"]
        self.assertIn("identificacao-cliente-ficticia", rota["allowedResponsibilities"])
        self.assertIn("whatsapp", marca["forbiddenClaims"])
        self.assertTrue(marca["forbiddenClaims"])
        for tenant_id in EXPECTED_TENANTS:
            self.assertIn("routeRules", tenants[tenant_id])
            self.assertIn("forbiddenClaims", tenants[tenant_id])

    def test_13_readme_documents_usage(self) -> None:
        with open(
            render_local.fs_path(os.path.join(PORTAL_DIR, "README.md")),
            "r",
            encoding="utf-8",
        ) as handle:
            readme = handle.read()
        for trecho in (
            "--build",
            "--serve",
            "--export-aprovacoes",
            "/media/video/",
            "/api/health",
            "/api/approvals",
            "aprovacoes-titular.json",
        ):
            self.assertIn(trecho, readme)


class EscapeTest(unittest.TestCase):
    """Escape do bloco JSON embutido no index.html."""

    def test_14_embeds_hostile_json_safely(self) -> None:
        hostil = {
            "schemaVersion": 1,
            "totals": {"tenants": 0, "campaigns": 1},
            "tenants": [],
            "campaigns": [
                {
                    "tenantId": "</script><img src=x onerror=alert(1)>",
                    "slug": 'aspas " contra\\barra',
                    "srt": {"text": "</script>\nlinha"},
                }
            ],
        }
        html = review_dashboard.render_index_html(hostil)
        abertura = '<script id="portal-data" type="application/json">'
        inicio = html.index(abertura) + len(abertura)
        fim = html.index("</script>", inicio)
        embutido = html[inicio:fim]
        self.assertEqual(json.loads(embutido), hostil)
        self.assertNotIn("</script><img", embutido)
        self.assertIn("<\\/script>", embutido)


class ServeFakeRootTest(unittest.TestCase):
    """Servidor HTTP sobre uma raiz falsa minima, em porta efemera (port=0)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.fake_root = os.path.join(TMP_DIR, "serve-fake-root")
        _rmtree(cls.fake_root)
        portal = os.path.join(cls.fake_root, "05-review-portal")
        os.makedirs(render_local.fs_path(portal))
        with open(
            render_local.fs_path(os.path.join(portal, "index.html")),
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write("<!DOCTYPE html><html><body>portal-teste</body></html>")
        with open(
            render_local.fs_path(os.path.join(portal, "portal-data.json")),
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(json.dumps(_fake_portal_data(), ensure_ascii=False, indent=2))
        archives = os.path.join(cls.fake_root, ".workspace", "archives", "t-slug")
        os.makedirs(render_local.fs_path(archives))
        with open(render_local.fs_path(os.path.join(archives, "t-slug.mp4")), "wb") as handle:
            handle.write(MP4_BYTES)
        deriv = os.path.join(archives, "derivatives")
        os.makedirs(render_local.fs_path(deriv))
        with open(
            render_local.fs_path(os.path.join(deriv, "t-slug-1x1.mp4")), "wb"
        ) as handle:
            handle.write(MP4_DERIV_BYTES)
        deliveries = os.path.join(
            cls.fake_root, "02-reels-shorts", "deliveries", "t-tenant", "t-slug"
        )
        os.makedirs(render_local.fs_path(deliveries))
        with open(
            render_local.fs_path(os.path.join(deliveries, "preview-storyboard.png")), "wb"
        ) as handle:
            handle.write(b"\x89PNG-fake")

        cls.server = review_dashboard.make_server(root=cls.fake_root, port=0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        _rmtree(cls.fake_root)

    def test_15_serves_index_data_api(self) -> None:
        status, body, _ = _http_get(self.port, "/")
        self.assertEqual(status, 200)
        self.assertIn(b"portal-teste", body)
        status, _, _ = _http_get(self.port, "/index.html")
        self.assertEqual(status, 200)
        status, body, hdrs = _http_get(self.port, "/portal-data.json")
        self.assertEqual(status, 200)
        self.assertEqual(hdrs["content-type"], "application/json; charset=utf-8")
        self.assertEqual(json.loads(body)["totals"]["campaigns"], 1)
        status, body, hdrs = _http_get(self.port, "/api/data")
        self.assertEqual(status, 200)
        self.assertEqual(hdrs["content-type"], "application/json; charset=utf-8")
        self.assertEqual(json.loads(body)["totals"]["campaigns"], 1)
        status, body, _ = _http_get(self.port, "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(
            json.loads(body), {"ok": True, "tenants": 1, "campaigns": 1}
        )

    def test_16_media_storyboard_cover_formats(self) -> None:
        status, body, hdrs = _http_get(self.port, "/media/storyboard/t-tenant/t-slug")
        self.assertEqual(status, 200)
        self.assertEqual(hdrs["content-type"], "image/png")
        self.assertEqual(body, b"\x89PNG-fake")
        status, _, _ = _http_get(self.port, "/media/cover/t-tenant/t-slug")
        self.assertEqual(status, 404)
        status, _, _ = _http_get(self.port, "/media/formats/t-tenant/t-slug")
        self.assertEqual(status, 404)
        status, _, _ = _http_get(self.port, "/media/storyboard/t-tenant/nao-existe")
        self.assertEqual(status, 404)
        status, _, _ = _http_get(
            self.port, "/deliveries/t-tenant/t-slug/preview-storyboard.png"
        )
        self.assertEqual(status, 200)

    def test_17_video_variant_streaming_with_range(self) -> None:
        url = "/media/video/t-tenant/t-slug/9x16"
        status, body, hdrs = _http_get(self.port, url)
        self.assertEqual(status, 200)
        self.assertEqual(body, MP4_BYTES)
        self.assertEqual(hdrs["content-type"], "video/mp4")
        self.assertEqual(hdrs["accept-ranges"], "bytes")
        self.assertEqual(hdrs["content-length"], str(len(MP4_BYTES)))

        status, body, hdrs = _http_get(self.port, url, {"Range": "bytes=4-7"})
        self.assertEqual(status, 206)
        self.assertEqual(body, MP4_BYTES[4:8])
        self.assertEqual(hdrs["content-range"], f"bytes 4-7/{len(MP4_BYTES)}")
        self.assertEqual(hdrs["content-length"], "4")

        status, body, hdrs = _http_get(self.port, url, {"Range": "bytes=60-"})
        self.assertEqual(status, 206)
        self.assertEqual(body, MP4_BYTES[60:])
        self.assertEqual(hdrs["content-range"], f"bytes 60-63/{len(MP4_BYTES)}")

        status, _, hdrs = _http_get(self.port, url, {"Range": "bytes=999-"})
        self.assertEqual(status, 416)
        self.assertEqual(hdrs["content-range"], f"bytes */{len(MP4_BYTES)}")

        status, body, _ = _http_get(self.port, "/media/video/t-tenant/t-slug/1x1")
        self.assertEqual(status, 200)
        self.assertEqual(body, MP4_DERIV_BYTES)

        status, _, _ = _http_get(self.port, "/media/video/t-tenant/t-slug/16x9")
        self.assertEqual(status, 404)

        status, body, _ = _http_get(self.port, "/archives/t-slug/t-slug.mp4")
        self.assertEqual(status, 200)
        self.assertEqual(body, MP4_BYTES)

    def test_18_traversal_and_restrictions_blocked(self) -> None:
        cases = (
            "/media/video/../../secret",
            "/media/video/t-tenant/t-slug/9x16/extra",
            "/media/storyboard/../t-tenant/t-slug",
            "/media/%2e%2e/video/t-tenant/t-slug/9x16",
            "/api/health/extra",
            "/archives/../05-review-portal/index.html",
            "/archives/%2e%2e/05-review-portal/portal-data.json",
            "/archives/..%5c..%5cindex.html",
            "/deliveries/../../../../tools/review_dashboard.py",
            "/deliveries/t-tenant/../../../../tools/review_dashboard.py",
            "/qualquer/coisa",
        )
        for path in cases:
            with self.subTest(path=path):
                status, _, _ = _http_get(self.port, path)
                self.assertEqual(status, 404, path)

    def test_19_write_methods_refused(self) -> None:
        for method in ("POST", "PUT", "DELETE"):
            with self.subTest(method=method):
                status, _ = _http_method(self.port, method, "/")
                self.assertIn(status, (405, 501))
        status, _ = _http_method(self.port, "POST", "/api/data")
        self.assertIn(status, (405, 501))

    def test_20_head_supported(self) -> None:
        status, body = _http_method(self.port, "HEAD", "/")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")

    def test_21_approvals_roundtrip_persists_and_cleans(self) -> None:
        store = os.path.join(
            self.fake_root, ".workspace", "tmp", "aprovacoes-titular.json"
        )
        self.assertTrue(
            render_local.contained(self.fake_root, os.path.realpath(store))
        )
        status, body, _ = _http_get(self.port, "/api/approvals")
        self.assertEqual(status, 200)
        doc = json.loads(body)
        self.assertTrue(doc["ok"])
        self.assertFalse(doc["existe"])
        self.assertIsNone(doc["aprovacoes"])
        self.assertFalse(os.path.exists(render_local.fs_path(store)))

        doc1 = _doc_aprovacoes()
        status, body = _http_post(
            self.port, "/api/approvals", json.dumps(doc1, ensure_ascii=False).encode("utf-8")
        )
        self.assertEqual(status, 200)
        resp = json.loads(body)
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["campanhas"], 1)
        self.assertEqual(resp["salvoEm"], ".workspace/tmp/aprovacoes-titular.json")
        self.assertTrue(os.path.isfile(render_local.fs_path(store)))
        with open(render_local.fs_path(store), "r", encoding="utf-8") as handle:
            gravado = json.load(handle)
        self.assertEqual(gravado, doc1)

        status, body, _ = _http_get(self.port, "/api/approvals")
        self.assertEqual(status, 200)
        doc = json.loads(body)
        self.assertTrue(doc["existe"])
        self.assertEqual(doc["aprovacoes"], doc1)

        doc2 = _doc_aprovacoes()
        doc2["campanhas"][0]["decisao"] = "ajuste"
        doc2["campanhas"][0]["observacoes"] = "Ajustar antes de publicar"
        status, body = _http_post(
            self.port, "/api/approvals", json.dumps(doc2, ensure_ascii=False).encode("utf-8")
        )
        self.assertEqual(status, 200)
        status, body, _ = _http_get(self.port, "/api/approvals")
        self.assertEqual(json.loads(body)["aprovacoes"], doc2)

        # limpeza apos o teste: remove o arquivo persistido
        os.remove(render_local.fs_path(store))
        self.assertFalse(os.path.exists(render_local.fs_path(store)))

    def test_22_approvals_invalid_schema_rejected(self) -> None:
        casos = [
            (b"isto nao e json", "JSON_INVALIDO"),
            (
                json.dumps({"schemaVersion": 1, "campanhas": []}).encode("utf-8"),
                "SCHEMA_INVALIDO",
            ),
            (
                json.dumps({"schemaVersion": 2, "campanhas": [], "hack": 1}).encode("utf-8"),
                "CHAVE_DESCONHECIDA",
            ),
            (
                json.dumps(
                    {
                        "schemaVersion": 2,
                        "campanhas": [
                            {"tenantId": "t-tenant", "slug": "x", "decisao": "aprovado"}
                        ],
                    }
                ).encode("utf-8"),
                "CAMPANHA_DESCONHECIDA",
            ),
            (
                json.dumps(
                    {
                        "schemaVersion": 2,
                        "campanhas": [
                            {
                                "tenantId": "t-tenant",
                                "slug": "t-slug",
                                "decisao": "publicar",
                            }
                        ],
                    }
                ).encode("utf-8"),
                "DECISAO_INVALIDA",
            ),
            (
                json.dumps(
                    {
                        "schemaVersion": 2,
                        "campanhas": [
                            {
                                "tenantId": "t-tenant",
                                "slug": "t-slug",
                                "decisao": "aprovado",
                                "locucaoExternaConferida": "sim",
                            }
                        ],
                    }
                ).encode("utf-8"),
                "TIPO_INVALIDO",
            ),
        ]
        for corpo, erro in casos:
            with self.subTest(erro=erro):
                status, body = _http_post(self.port, "/api/approvals", corpo)
                self.assertEqual(status, 400)
                resp = json.loads(body)
                self.assertFalse(resp["ok"])
                self.assertEqual(resp["erro"], erro)


class ServeRealRootTest(unittest.TestCase):
    """Servidor HTTP sobre a raiz real da worktree, em porta efemera."""

    @classmethod
    def setUpClass(cls) -> None:
        review_dashboard.build_portal(root=REPO_ROOT)
        cls.server = review_dashboard.make_server(root=REPO_ROOT, port=0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_23_serves_real_portal(self) -> None:
        status, body, _ = _http_get(self.port, "/")
        self.assertEqual(status, 200)
        self.assertIn(b"<!DOCTYPE html>", body)
        status, body, _ = _http_get(self.port, "/portal-data.json")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["totals"]["campaigns"], 8)
        status, body, _ = _http_get(self.port, "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"ok": True, "tenants": 4, "campaigns": 8})
        status, body, hdrs = _http_get(
            self.port, "/media/storyboard/marca-salao/camp-saas-demo-marca-salao-001"
        )
        self.assertEqual(status, 200)
        self.assertEqual(hdrs["content-type"], "image/png")
        disk = os.path.join(
            REPO_ROOT,
            "02-reels-shorts",
            "deliveries",
            "marca-salao",
            "camp-saas-demo-marca-salao-001",
            "preview-storyboard.png",
        )
        self.assertEqual(
            hashlib.sha256(body).hexdigest(), _sha256_abs(disk)
        )


class CliTest(unittest.TestCase):
    """CLI: --build --json, validacao de modos e --export-aprovacoes."""

    @staticmethod
    def _run_cli(*args: str):
        return subprocess.run(
            [sys.executable, os.path.join(TOOLS_DIR, "review_dashboard.py"), *args],
            capture_output=True,
            text=True,
            timeout=180,
        )

    def test_24_build_json_exit_zero(self) -> None:
        saida = self._run_cli("--build", "--json", "--root", REPO_ROOT)
        self.assertEqual(saida.returncode, 0, saida.stderr)
        resumo = json.loads(saida.stdout)
        self.assertTrue(resumo["ok"])
        self.assertEqual(resumo["totalTenants"], 4)
        self.assertEqual(resumo["totalCampaigns"], 8)
        self.assertEqual(len(resumo["files"]), 3)

    def test_25_requires_exactly_one_mode(self) -> None:
        saida = self._run_cli("--root", REPO_ROOT)
        self.assertEqual(saida.returncode, 2)
        saida = self._run_cli("--build", "--serve", "--root", REPO_ROOT)
        self.assertEqual(saida.returncode, 2)

    def test_26_export_aprovacoes(self) -> None:
        fake = os.path.join(TMP_DIR, "cli-aprovacoes")
        _rmtree(fake)
        store = os.path.join(fake, ".workspace", "tmp", "aprovacoes-titular.json")
        os.makedirs(render_local.fs_path(os.path.dirname(store)))
        doc = _doc_aprovacoes()
        with open(render_local.fs_path(store), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")

        saida = self._run_cli("--export-aprovacoes", "--root", fake)
        self.assertEqual(saida.returncode, 0, saida.stderr)
        self.assertEqual(json.loads(saida.stdout), doc)

        os.remove(render_local.fs_path(store))
        saida = self._run_cli("--export-aprovacoes", "--root", fake)
        self.assertEqual(saida.returncode, 1)
        self.assertIn("APROVACOES_AUSENTES", saida.stderr)
        _rmtree(fake)


if __name__ == "__main__":
    unittest.main(verbosity=2)


