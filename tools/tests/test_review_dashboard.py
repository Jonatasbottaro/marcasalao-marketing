"""Testes automatizados (unittest) para tools/review_dashboard.py (Etapa 4 - Agente 2).

Cobre obrigatoriamente:
  1. Geracao do portal consolidado (05-review-portal/index.html,
     portal-data.json e README.md) para 4 tenants / 8 campanhas.
  2. Integridade dos hashes SHA-256 (srt, narracao, storyboard) declarados no
     portal-data.json contra os arquivos reais em disco e contra o manifest.json
     de cada entrega.
  3. Zero vazamento de caminhos fora da raiz: somente caminhos relativos
     contidos no checkout (sem caminho absoluto, sem UNC, sem "..").
  4. Determinismo do build (duas geracoes produzem bytes identicos).
  5. Marcadores da interface (filtros, abas, checklist, exportacao).
  6. Servidor HTTP local (--serve) em porta efemera (port=0): index, dados e
     storyboard 200; MP4 com suporte a Range (206/416); travessia de caminho
     e extensao nao permitida bloqueadas (404); metodo de escrita recusado.
  7. CLI --build --json com codigo de saida 0 e resumo JSON consistente.
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
PATH_KEYS_SUFFIX = ("Path", "Root")

MP4_BYTES = bytes(range(64))


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


class HelpersTest(unittest.TestCase):
    """Unidades internas: verificacao de hash e extracao de URL UTM."""

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


class BuildPortalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = review_dashboard.build_portal(root=REPO_ROOT)
        with open(render_local.fs_path(os.path.join(PORTAL_DIR, "portal-data.json")), "r", encoding="utf-8") as handle:
            cls.data = json.load(handle)

    def test_03_generates_portal_files(self) -> None:
        self.assertTrue(self.summary.get("ok"))
        for filename in ("index.html", "portal-data.json", "README.md"):
            abs_path = os.path.join(PORTAL_DIR, filename)
            self.assertTrue(os.path.isfile(render_local.fs_path(abs_path)), filename)
            self.assertGreater(os.path.getsize(render_local.fs_path(abs_path)), 0, filename)
            entry = self.summary["files"][filename]
            self.assertEqual(entry["sha256"], _sha256_abs(abs_path))
            self.assertEqual(entry["bytes"], os.path.getsize(render_local.fs_path(abs_path)))

    def test_04_totals_four_tenants_eight_campaigns(self) -> None:
        self.assertEqual(self.summary["totalTenants"], 4)
        self.assertEqual(self.summary["totalCampaigns"], 8)
        self.assertEqual(tuple(sorted(self.summary["tenants"])), EXPECTED_TENANTS)
        self.assertEqual(self.data["totals"]["tenants"], 4)
        self.assertEqual(self.data["totals"]["campaigns"], 8)
        tenants_data = {t["tenantId"]: t for t in self.data["tenants"]}
        self.assertEqual(tuple(sorted(tenants_data)), EXPECTED_TENANTS)
        campaigns = self.data["campaigns"]
        self.assertEqual(len(campaigns), 8)
        self.assertEqual({(c["tenantId"], c["slug"]) for c in campaigns}, EXPECTED_CAMPAIGNS)
        for tenant_id, tenant in tenants_data.items():
            with self.subTest(tenant=tenant_id):
                for key in ("brandName", "monogram", "domain", "palette", "audioPolicy"):
                    self.assertIn(key, tenant)
                for key in ("primary", "secondary", "accent", "background"):
                    self.assertIn(key, tenant["palette"])
                self.assertIn(tenant["audioPolicy"]["ffmpegFlag"], ("-an", "aac"))

    def test_05_campaign_fields(self) -> None:
        for campaign in self.data["campaigns"]:
            slug = campaign["slug"]
            with self.subTest(slug=slug):
                self.assertIn(campaign["preset"], ("saas-demo", "shorts-completo"))
                self.assertIn(campaign["politicaAudio"], ("-an", "AAC"))
                self.assertTrue(campaign["campaignId"])
                self.assertGreater(campaign["format"]["duration"], 0)
                self.assertGreater(campaign["scenes"], 0)
                self.assertIn("-->", campaign["srt"]["text"])
                self.assertGreater(len(campaign["narracao"]["text"].strip()), 0)
                self.assertTrue(campaign["storyboard"]["relPath"].endswith("preview-storyboard.png"))
                self.assertTrue(campaign["video"]["archiveRelPath"].endswith(".mp4"))
                for channel in ("instagram", "youtube", "facebook"):
                    copy = campaign["copies"][channel]
                    self.assertGreater(len(copy["text"].strip()), 0)
                    self.assertIsNotNone(copy["utmUrl"], channel)
                    self.assertIn(f"utm_campaign={slug}", copy["utmUrl"])
                pacote = campaign["pacote"]
                self.assertTrue(pacote["checklistRelPath"].endswith("checklist-publicacao.json"))
                self.assertFalse(pacote["autoPublish"])
                self.assertTrue(pacote["guardrailsAudited"])
                if campaign["preset"] == "saas-demo":
                    self.assertEqual(campaign["politicaAudio"], "-an")
                    self.assertEqual(campaign["audioStreams"], 0)
                else:
                    self.assertEqual(campaign["politicaAudio"], "AAC")
                    self.assertEqual(campaign["audioStreams"], 1)

    def test_06_hash_integrity_against_disk_and_manifest(self) -> None:
        for campaign in self.data["campaigns"]:
            slug = campaign["slug"]
            with self.subTest(slug=slug):
                for section in ("srt", "narracao", "storyboard"):
                    rel = campaign[section]["relPath"]
                    abs_path = os.path.join(REPO_ROOT, rel.replace("/", os.sep))
                    self.assertEqual(
                        campaign[section]["sha256"],
                        _sha256_abs(abs_path),
                        f"{section} divergiu do arquivo em disco",
                    )
                delivery_dir = os.path.dirname(
                    os.path.join(REPO_ROOT, campaign["srt"]["relPath"].replace("/", os.sep))
                )
                with open(render_local.fs_path(os.path.join(delivery_dir, "manifest.json")), "r", encoding="utf-8") as handle:
                    manifest = json.load(handle)
                artifacts = manifest["artifacts"]
                self.assertEqual(campaign["srt"]["sha256"], artifacts["srt"]["sha256"])
                self.assertEqual(campaign["narracao"]["sha256"], artifacts["narration"]["sha256"])
                self.assertEqual(campaign["storyboard"]["sha256"], artifacts["storyboard"]["sha256"])
                self.assertEqual(campaign["video"]["sha256"], artifacts["video"]["sha256"])
                self.assertEqual(campaign["video"]["bytes"], artifacts["video"]["bytes"])

    def test_07_no_path_leakage_outside_root(self) -> None:
        root_real = os.path.realpath(REPO_ROOT)
        variants = {root_real, root_real.replace(os.sep, "/")}
        for key, value in _walk_strings(self.data):
            with self.subTest(key=key, value=value[:60]):
                for variant in variants:
                    self.assertNotIn(variant, value)
                self.assertNotRegex(value, r"^[A-Za-z]:[\\/]")
                self.assertFalse(value.startswith("\\\\"))
                if key.endswith(PATH_KEYS_SUFFIX):
                    self.assertFalse(value.startswith("/"), value)
                    self.assertNotIn("..", value)
                    resolved = os.path.realpath(os.path.join(REPO_ROOT, value.replace("/", os.sep)))
                    self.assertTrue(
                        render_local.contained(REPO_ROOT, resolved),
                        f"caminho fora da raiz: {value}",
                    )

    def test_08_build_is_deterministic(self) -> None:
        out_dir = os.path.join(TMP_DIR, "portal-deterministico")
        _rmtree(out_dir)
        review_dashboard.build_portal(root=REPO_ROOT, output_dir=out_dir)
        for filename in ("index.html", "portal-data.json", "README.md"):
            with self.subTest(file=filename):
                self.assertEqual(
                    _sha256_abs(os.path.join(out_dir, filename)),
                    _sha256_abs(os.path.join(PORTAL_DIR, filename)),
                )
        _rmtree(out_dir)

    def test_09_index_html_ui_markers(self) -> None:
        with open(render_local.fs_path(os.path.join(PORTAL_DIR, "index.html")), "r", encoding="utf-8") as handle:
            html = handle.read()
        for marker in (
            'id="filtro-tenant"',
            'id="filtro-preset"',
            'id="filtro-audio"',
            'id="btn-exportar-aprovacoes"',
            'id="portal-data"',
            "aprovacoes-titular.json",
            "localStorage",
            "<video",
            "Copy Instagram",
            "Copy YouTube",
            "Copy Facebook",
            "Legenda .srt",
        ):
            self.assertIn(marker, html, marker)
        for slug in {slug for _, slug in EXPECTED_CAMPAIGNS}:
            self.assertIn(slug, html)

    def test_10_readme_documents_usage(self) -> None:
        with open(render_local.fs_path(os.path.join(PORTAL_DIR, "README.md")), "r", encoding="utf-8") as handle:
            readme = handle.read()
        self.assertIn("--build", readme)
        self.assertIn("--serve", readme)
        self.assertIn("review_dashboard.py", readme)


class ServeFakeRootTest(unittest.TestCase):
    """Servidor HTTP sobre uma raiz falsa minima, em porta efemera (port=0)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.fake_root = os.path.join(TMP_DIR, "serve-fake-root")
        _rmtree(cls.fake_root)
        portal = os.path.join(cls.fake_root, "05-review-portal")
        os.makedirs(render_local.fs_path(portal))
        with open(render_local.fs_path(os.path.join(portal, "index.html")), "w", encoding="utf-8", newline="\n") as handle:
            handle.write("<!DOCTYPE html><html><body>portal-teste</body></html>")
        with open(render_local.fs_path(os.path.join(portal, "portal-data.json")), "w", encoding="utf-8", newline="\n") as handle:
            handle.write('{"schemaVersion": 1, "totals": {"tenants": 1, "campaigns": 1}}')
        archives = os.path.join(cls.fake_root, ".workspace", "archives", "test-slug")
        os.makedirs(render_local.fs_path(archives))
        with open(render_local.fs_path(os.path.join(archives, "test.mp4")), "wb") as handle:
            handle.write(MP4_BYTES)
        deliveries = os.path.join(cls.fake_root, "02-reels-shorts", "deliveries", "t-tenant", "t-slug")
        os.makedirs(render_local.fs_path(deliveries))
        with open(render_local.fs_path(os.path.join(deliveries, "preview-storyboard.png")), "wb") as handle:
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

    def test_11_serves_index_data_and_storyboard(self) -> None:
        status, body, _ = _http_get(self.port, "/")
        self.assertEqual(status, 200)
        self.assertIn(b"portal-teste", body)
        status, body, hdrs = _http_get(self.port, "/portal-data.json")
        self.assertEqual(status, 200)
        self.assertEqual(hdrs["content-type"], "application/json; charset=utf-8")
        self.assertEqual(json.loads(body)["totals"]["campaigns"], 1)
        status, body, _ = _http_get(self.port, "/deliveries/t-tenant/t-slug/preview-storyboard.png")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"\x89PNG-fake")
        status, _, _ = _http_get(self.port, "/index.html")
        self.assertEqual(status, 200)

    def test_12_video_streaming_with_range(self) -> None:
        url = "/archives/test-slug/test.mp4"
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

    def test_13_traversal_and_restrictions_blocked(self) -> None:
        cases = (
            "/archives/../05-review-portal/index.html",
            "/archives/%2e%2e/05-review-portal/portal-data.json",
            "/archives/..%5c..%5cindex.html",
            "/deliveries/../../../../tools/review_dashboard.py",
            "/deliveries/t-tenant/../../../../tools/review_dashboard.py",
            "/archives/test-slug/notes.txt",
            "/archives/test-slug/",
            "/qualquer/coisa",
        )
        for path in cases:
            with self.subTest(path=path):
                status, _, _ = _http_get(self.port, path)
                self.assertEqual(status, 404, path)

    def test_14_write_methods_refused(self) -> None:
        for method in ("POST", "PUT", "DELETE"):
            with self.subTest(method=method):
                status, _ = _http_method(self.port, method, "/")
                self.assertIn(status, (405, 501))

    def test_15_head_supported(self) -> None:
        status, body = _http_method(self.port, "HEAD", "/")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")


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

    def test_16_serves_real_portal(self) -> None:
        status, body, _ = _http_get(self.port, "/")
        self.assertEqual(status, 200)
        self.assertIn(b"<!DOCTYPE html>", body)
        status, body, _ = _http_get(self.port, "/portal-data.json")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["totals"]["campaigns"], 8)
        status, body, _ = _http_get(
            self.port,
            "/deliveries/marca-salao/camp-saas-demo-marca-salao-001/preview-storyboard.png",
        )
        self.assertEqual(status, 200)
        disk = os.path.join(
            REPO_ROOT,
            "02-reels-shorts", "deliveries", "marca-salao",
            "camp-saas-demo-marca-salao-001", "preview-storyboard.png",
        )
        with open(render_local.fs_path(disk), "rb") as handle:
            self.assertEqual(body, handle.read())


class CliTest(unittest.TestCase):
    def test_17_build_json_exit_zero(self) -> None:
        proc = subprocess.run(
            [sys.executable, "tools/review_dashboard.py", "--build", "--json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["totalTenants"], 4)
        self.assertEqual(payload["totalCampaigns"], 8)
        self.assertEqual(
            tuple(sorted(payload["tenants"])),
            EXPECTED_TENANTS,
        )
        for filename in ("index.html", "portal-data.json", "README.md"):
            self.assertIn(filename, payload["files"])

    def test_18_requires_build_or_serve(self) -> None:
        proc = subprocess.run(
            [sys.executable, "tools/review_dashboard.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--build", proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
