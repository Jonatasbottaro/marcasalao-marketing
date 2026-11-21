"""Suíte de testes do motor de cards estaticos (Agente 1 - Etapa 5).

Requisitos cobertos:
  1. 3 lâminas de Stories 1080x1920 exatas no header PNG.
  2. 4 lâminas de Carrossel 1080x1350 exatas no header PNG.
  3. Aplicação distinta das paletas dos 4 tenants.
  4. Bloqueio preventivo (GUARDRAIL_VIOLACAO) com frase proibida.
  5. marca-salao bloqueia "Meu Salão"; meu-salao permite.
  6. Integridade SHA-256 e bytes das 7 lâminas vs static-manifest.json.
  7. Ausência de caminhos absolutos (D:/, C:/) e LF puro no manifesto.
  8. Determinismo: duas execuções geram SHA-256 idênticos.
  9. Validação consolidada das 8 entregas reais em 01-insta-stories/deliveries/.
 10. CLI --tenant + --campaign + --json encerra com código 0.
 11. CLI --all --json encerra com código 0.

Executa a geração real (--all) uma vez em setUpModule e valida os
artefatos produzidos em 01-insta-stories/deliveries/ da worktree.
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import static_cards
import tenant_validator
import render_local

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DELIVERIES = os.path.join(ROOT, "01-insta-stories", "deliveries")
SCRIPT = os.path.join(ROOT, "tools", "static_cards.py")
TENANTS = ["clinica-vital", "estudio-flow", "marca-salao", "meu-salao", "multitrack-hub"]
CAMPAIGNS_BY_TENANT = {
    "clinica-vital": ["camp-saas-demo-clinica-vital-001",
                      "camp-saas-demo-clinica-vital-002"],
    "estudio-flow": ["camp-saas-demo-estudio-flow-001",
                     "camp-saas-demo-estudio-flow-002"],
    "marca-salao": ["camp-saas-demo-marca-salao-001", "camp-saas-demo-ns001-agenda-001"],
    "meu-salao": ["camp-saas-demo-meu-salao-001", "camp-saas-demo-meu-salao-002"],
    "multitrack-hub": ["camp-shorts-completo-multitrack-001",
                       "camp-shorts-rateios-002",
                       "camp-shorts-stems-workflow-003"],
}


def _load_json(path):
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_bytes(path):
    with open(render_local.fs_path(path), "rb") as handle:
        return handle.read()


def _png_dimensions(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise AssertionError("PNG sem header IHDR valido")
    return struct.unpack(">II", data[16:24])


def _png_rgb_at(data, x, y):
    """Decodifica o pixel (x,y) de um PNG gerado pelo motor (filtro 0)."""
    pos = 8
    idat = b""
    w = h = None
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            w, h = struct.unpack(">II", chunk[:8])
        elif tag == b"IDAT":
            idat += chunk
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = w * 3 + 1
    row = raw[y * stride:(y + 1) * stride]
    assert row[0] == 0, "filtro de linha inesperado (esperado 0 = None)"
    i = 1 + x * 3
    return tuple(row[i:i + 3])


def _expected_gradient(top, bottom, y, h):
    ratio = y / (h - 1)
    return tuple(int(top[c] + (bottom[c] - top[c]) * ratio) for c in range(3))


def _all_deliveries():
    found = []
    for tid in TENANTS:
        for slug in CAMPAIGNS_BY_TENANT[tid]:
            found.append((tid, slug, os.path.join(DELIVERIES, tid, slug)))
    return found


def _generate_all():
    return static_cards.generate_all_static_cards(ROOT,
                                                  kinds=["stories", "carousel"])


def _cli_tmp_parent():
    parent = os.path.join(ROOT, ".workspace", "tmp")
    os.makedirs(render_local.fs_path(parent), exist_ok=True)
    return parent


def _run_cli(args, timeout=600):
    """Executa o CLI por caminho absoluto a partir de um cwd neutro.

    Regressao: com script relativo ("tools/static_cards.py") a chamada quebra
    quando o harness executa o unittest de um cwd diferente do checkout. O
    caminho absoluto + --root mantem saidas e manifesto presos a ROOT.
    """
    with tempfile.TemporaryDirectory(prefix="static-cli-cwd-", dir=_cli_tmp_parent()) as cwd:
        return subprocess.run(
            [sys.executable, SCRIPT, *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )


def tearDownModule():
    try:
        os.rmdir(render_local.fs_path(os.path.join(ROOT, ".workspace", "tmp")))
    except OSError:
        pass


class TestStaticCards(unittest.TestCase):

    @classmethod
    def setUpModule(cls):
        _generate_all()

    # --- Testes 1 e 2: dimensoes exatas das botoes -----------------------
    def test_stories_laminas_1080x1920(self):
        for tid, slug, _ in _all_deliveries():
            for name in static_cards.STORY_FILES:
                path = os.path.join(DELIVERIES, tid, slug, "stories", name)
                self.assertTrue(os.path.isfile(render_local.fs_path(path)), path)
                w, h = _png_dimensions(_read_bytes(path))
                self.assertEqual((w, h), (1080, 1920), f"{path}: {w}x{h}")

    def test_carousel_laminas_1080x1350(self):
        for tid, slug, _ in _all_deliveries():
            for name in static_cards.CAROUSEL_FILES:
                path = os.path.join(DELIVERIES, tid, slug, "carousel", name)
                self.assertTrue(os.path.isfile(render_local.fs_path(path)), path)
                w, h = _png_dimensions(_read_bytes(path))
                self.assertEqual((w, h), (1080, 1350), f"{path}: {w}x{h}")

    # --- Teste 3: paletas distintas dos 4 tenants -------------------------
    def test_paleta_distinta_por_tenant(self):
        amostras = {}
        for tid in TENANTS:
            slug = CAMPAIGNS_BY_TENANT[tid][0]
            data = _read_bytes(os.path.join(DELIVERIES, tid, slug,
                                            "stories", "story-01-hook.png"))
            brand = _load_json(os.path.join(ROOT, "tenants", tid, "brand-kit.json"))
            rgb = brand["palette"]["rgb"]
            # (900, 50): area do cabeçalho (fora do texto/titulo e da pílula de rota)
            hdr = _png_rgb_at(data, 900, 50)
            # (500, 166): faixa de acento de 6 px na base do cabeçalho
            acc = _png_rgb_at(data, 500, 166)
            # (500, 200): região de gradiente abaixo do cabeçalho
            grad = _png_rgb_at(data, 500, 200)
            self.assertEqual(hdr, tuple(rgb["headerBg"]),
                             f"{tid}: headerBg incorreto em (900,50): {hdr}")
            self.assertEqual(acc, tuple(rgb["primaryAccent"]),
                             f"{tid}: primaryAccent incorreto em (500,166): {acc}")
            self.assertEqual(grad, _expected_gradient(tuple(rgb["backgroundTop"]),
                                                      tuple(rgb["backgroundBottom"]), 200, 1920),
                             f"{tid}: gradiente incorreto em (500,200)")
            amostras[tid] = (hdr, acc, grad)
        chaves = list(amostras)
        for i in range(len(chaves)):
            for j in range(i + 1, len(chaves)):
                self.assertNotEqual(amostras[chaves[i]], amostras[chaves[j]],
                                    f"paletas iguais para {chaves[i]} e {chaves[j]}")

    # --- Teste 4: bloqueio preventivo com frase proibida ------------------
    def test_frase_proibida_bloqueia_render(self):
        cfg = {"id": "fake-bloqueio", "scenes": [{"headline": "CHECKOUT AGORA"}]}
        ctx = tenant_validator.load_and_validate_tenant("marca-salao", root=ROOT, strict=True)
        with self.assertRaises(static_cards.StaticCardsError) as ctx_exc:
            static_cards._generate_one(ROOT, "marca-salao", "fake-bloqueio", cfg,
                                       ctx["brandKit"], ctx["guardrails"], ctx["fixture"],
                                       ["stories", "carousel"])
        self.assertEqual(ctx_exc.exception.code, static_cards.GUARDRAIL_VIOLACAO)
        self.assertTrue(any("UI_FORBIDDEN" in v for v in ctx_exc.exception.errors),
                        f"esperava UI_FORBIDDEN, obteve: {ctx_exc.exception.errors}")

    def test_claim_proibido_bloqueia_render(self):
        cfg = {"id": "fake-bloqueio-2", "scenes": [{"headline": "REDUCAO DE FALTAS GARANTIDA"}]}
        ctx = tenant_validator.load_and_validate_tenant("marca-salao", root=ROOT, strict=True)
        with self.assertRaises(static_cards.StaticCardsError) as ctx_exc:
            static_cards._generate_one(ROOT, "marca-salao", "fake-bloqueio-2", cfg,
                                       ctx["brandKit"], ctx["guardrails"], ctx["fixture"],
                                       ["stories", "carousel"])
        self.assertEqual(ctx_exc.exception.code, static_cards.GUARDRAIL_VIOLACAO)
        self.assertTrue(any("CLAIM_FORBIDDEN" in v for v in ctx_exc.exception.errors),
                        f"esperava CLAIM_FORBIDDEN, obteve: {ctx_exc.exception.errors}")

    # --- Teste 5: marca-salao bloqueia "Meu Salão", meu-salao permite -----
    def test_meu_salao_regra_diferenciale_tenants(self):
        g_ms = _load_json(os.path.join(ROOT, "tenants", "marca-salao", "guardrails.json"))
        g_m2 = _load_json(os.path.join(ROOT, "tenants", "meu-salao", "guardrails.json"))
        texto = "MEU SALAO"
        viol_ms = tenant_validator.validate_text_against_guardrails(
            texto, g_ms, check_ui_elements=True)
        viol_m2 = tenant_validator.validate_text_against_guardrails(
            texto, g_m2, check_ui_elements=True)
        self.assertTrue(any("CLAIM_FORBIDDEN" in v for v in viol_ms),
                        f"marca-salao deveria bloquear 'MEU SALAO': {viol_ms}")
        self.assertEqual([], viol_m2,
                         f"meu-salao deveria permitir 'MEU SALAO': {viol_m2}")

    # --- Teste 6: integridade SHA-256 e bytes vs manifesto ----------------
    def test_manifest_integridade_sha256_e_bytes(self):
        for tid, slug, ddir in _all_deliveries():
            manifest_path = os.path.join(ddir, "static-manifest.json")
            self.assertTrue(os.path.isfile(render_local.fs_path(manifest_path)), manifest_path)
            manifest = _load_json(manifest_path)
            self.assertEqual(manifest["schemaVersion"], 1)
            self.assertEqual(manifest["tenantId"], tid)
            self.assertEqual(manifest["slug"], slug)
            self.assertTrue(manifest["guardrailsAudited"] is True)
            total_itens = 0
            for kit, espec in manifest["kits"].items():
                w, h = (1080, 1920) if kit == "stories" else (1080, 1350)
                for item in espec["items"]:
                    total_itens += 1
                    data = _read_bytes(os.path.join(ROOT, item["path"]))
                    self.assertEqual(len(data), item["bytes"],
                                     f"{item['name']}: bytes divergem do manifesto")
                    self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"],
                                     f"{item['name']}: SHA-256 diverge do manifesto")
                    pw, ph = _png_dimensions(data)
                    self.assertEqual((pw, ph), (w, h), f"{item['name']}: {pw}x{ph}")
            self.assertEqual(total_itens, 7, f"{tid}/{slug}: esperadas 7 laminas, achadas {total_itens}")

    # --- Teste 7: sem caminhos absolutos e LF puro ------------------------
    def test_manifest_sem_caminhos_absolutos_e_lf_puro(self):
        for tid, slug, ddir in _all_deliveries():
            manifest_path = os.path.join(ddir, "static-manifest.json")
            data = _read_bytes(manifest_path)
            self.assertNotIn(b"\r\n", data, f"{manifest_path}: quebra CRLF detectada")
            self.assertNotIn(b"D:/", data, f"{manifest_path}: caminho absoluto D:/")
            self.assertNotIn(b"C:/", data, f"{manifest_path}: caminho absoluto C:/")
            self.assertNotIn(b"\\sessions\\", data)
            _load_json(manifest_path)  # deve ser JSON valido UTF-8

    # --- Teste 8: determinismo -------------------------------------------
    def test_determinismo_hashes_identicos(self):
        tid, slug = "marca-salao", "camp-saas-demo-marca-salao-001"
        ddir = os.path.join(DELIVERIES, tid, slug)

        def fingerprints():
            fps = {}
            manifest_path = os.path.join(ddir, "static-manifest.json")
            fps["manifest"] = _read_bytes(manifest_path)
            for kit in ("stories", "carousel"):
                for name in os.listdir(render_local.fs_path(os.path.join(ddir, kit))):
                    if name.endswith(".png"):
                        fps[os.path.join(kit, name)] = _read_bytes(os.path.join(ddir, kit, name))
            return fps

        antes = fingerprints()
        static_cards.generate_campaign_static_cards(tid, slug, ROOT,
                                                    kinds=["stories", "carousel"])
        depois = fingerprints()
        self.assertEqual(antes, depois, "execucoes repetidas geraram bytes diferentes")

    # --- Teste 9: validacao consolidada das 8 entregas reais --------------
    def test_dez_entregas_reais_consolidadas(self):
        entregas = []
        for tid in TENANTS:
            tenant_dir = os.path.join(DELIVERIES, tid)
            self.assertTrue(os.path.isdir(render_local.fs_path(tenant_dir)), tenant_dir)
            for slug in CAMPAIGNS_BY_TENANT[tid]:
                ddir = os.path.join(tenant_dir, slug)
                self.assertTrue(os.path.isdir(render_local.fs_path(ddir)), ddir)
                manifest_path = os.path.join(ddir, "static-manifest.json")
                self.assertTrue(os.path.isfile(render_local.fs_path(manifest_path)), manifest_path)
                manifest = _load_json(manifest_path)
                self.assertTrue(manifest["guardrailsAudited"])
                nomes_stories = {i["name"] for i in manifest["kits"]["stories"]["items"]}
                nomes_carousel = {i["name"] for i in manifest["kits"]["carousel"]["items"]}
                self.assertEqual(set(static_cards.STORY_FILES), nomes_stories)
                self.assertEqual(set(static_cards.CAROUSEL_FILES), nomes_carousel)
                entregas.append((tid, slug))
        self.assertEqual(len(entregas), 11, f"esperadas 11 entregas, achadas {len(entregas)}")

    # --- Teste 12: caminhos OS-nativos e normalizacao de separadores ------
    def test_caminhos_os_nativos_e_normpath(self):
        """Regressao Errno 22: '/' em path longo quebra o prefixo estendido.

        Constantes de entrega usam separadores nativos; _fs normaliza com
        os.path.normpath antes de render_local.fs_path prefixar paths longos.
        """
        if os.name == "nt":
            self.assertNotIn("/", static_cards.DELIVERIES_REL)
            self.assertNotIn("/", static_cards.NARRATION_REL)
        misto_longo = "C:\\" + ("z" * 260) + "/arquivo.png"
        resolvido = static_cards._fs(misto_longo)
        self.assertIsInstance(resolvido, str)
        if os.name == "nt":
            self.assertTrue(resolvido.startswith("\\\\?\\"),
                            "path longo deveria receber prefixo estendido")
            self.assertNotIn("/", resolvido[4:],
                             "prefixo estendido exige separadores nativos")

    # --- Testes 10 e 11: CLI ---------------------------------------------
    def test_cli_tenant_campaign_json_exit_zero(self):
        res = _run_cli(["--tenant", "meu-salao", "--campaign", "camp-saas-demo-meu-salao-002",
                        "--root", ROOT, "--json"], timeout=300)
        self.assertEqual(res.returncode, 0, f"stderr: {res.stderr}")
        summary = json.loads(res.stdout)
        self.assertEqual(summary["tenantId"], "meu-salao")
        self.assertEqual(len(summary["campaigns"]), 1)
        self.assertEqual(summary["campaigns"][0]["slug"], "camp-saas-demo-meu-salao-002")

    def test_cli_all_json_exit_zero(self):
        res = _run_cli(["--all", "--root", ROOT, "--json"], timeout=600)
        self.assertEqual(res.returncode, 0, f"stderr: {res.stderr}")
        summary = json.loads(res.stdout)
        total = sum(len(t["campaigns"]) for t in summary["tenants"])
        self.assertEqual(total, 11, f"esperadas 11 campanhas no --all, achadas {total}")


if __name__ == "__main__":
    unittest.main()
