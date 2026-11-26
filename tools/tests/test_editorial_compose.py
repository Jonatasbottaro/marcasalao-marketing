"""Testes de contrato do compositor editorial (tools/editorial_compose.py).

Cobertura dos testes A-J do prompt master v2.7 na faixa fast (sem render):
  A  proporcao/geometria (scale_dims, canvas par);
  B  proveniencia (hash de evidencia, valor verificado, regiao existente);
  C  isolamento de cliente (assetScopes);
  D  legendas sem duplicacao da CTA impressa na arte aprovada;
  E  mapeamento cena -> midia do pedido v2.7;
  F  areas seguras e faixa de legenda (captionBand);
  G  cenas 1 e 2 estruturalmente distintas;
  I  portabilidade (nenhum caminho absoluto de maquina nos arquivos versionados);
  J  estilo de legenda do renderizador canonico (referencia 1080x1920).

A prova de reutilizacao usa a fixture ficticia "Marca Exemplo"
(tools/tests/fixtures/editorial/), que nunca representa cliente real.
H (reprodutibilidade) e J (exportacao real) ficam em
test_editorial_compose_render.py, que renderiza de verdade.
"""

import copy
import json
import os
import sys
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
FIXTURE_DIR = os.path.join(TOOLS_DIR, "tests", "fixtures", "editorial")
V27_DIR = os.path.join(REPO_ROOT, "02-reels-shorts", "ns-001-reels-organizacao-agenda",
                       "editorial-v27")

sys.path.insert(0, TOOLS_DIR)

import editorial_compose  # noqa: E402
import render_local  # noqa: E402

ENDCARD_CTA_IMPRESSA = "Conheça o Marca Salão"


def load_fixture():
    with open(os.path.join(FIXTURE_DIR, "marca-exemplo.editorial.json"),
              encoding="utf-8") as handle:
        return json.load(handle)


def load_v27(name):
    with open(os.path.join(V27_DIR, name), encoding="utf-8") as handle:
        return json.load(handle)


class TestGeometria(unittest.TestCase):
    """A - proporcao preservada e canvas valido."""

    def test_scale_dims_preserva_proporcao(self):
        for sw, sh, tw in ((496, 93, 900), (549, 248, 900), (360, 80, 300)):
            w, h = editorial_compose.scale_dims(sw, sh, tw)
            self.assertEqual(w, tw)
            self.assertEqual(h % 2, 0)
            self.assertLess(abs(w / h - sw / sh) / (sw / sh), 0.02)

    def test_canvas_impar_reprovado(self):
        m = load_fixture()
        m["canvas"]["width"] = 361
        with self.assertRaises(editorial_compose.EditorialError) as ctx:
            editorial_compose.validate_manifest(m, REPO_ROOT)
        self.assertEqual(ctx.exception.code, "CANVAS_INVALID")


class TestProveniencia(unittest.TestCase):
    """B - todo valor editorial exige evidencia verificada."""

    def test_hash_divergente_reprovado(self):
        m = load_fixture()
        m["evidence"][0]["sha256"] = "0" * 64
        with self.assertRaises(editorial_compose.EditorialError) as ctx:
            editorial_compose.validate_manifest(m, REPO_ROOT)
        self.assertEqual(ctx.exception.code, "EVIDENCE_HASH_MISMATCH")

    def test_valor_nao_verificado_reprovado(self):
        m = load_fixture()
        m["scenes"][0]["highlights"][0]["value"] = "25:99"
        with self.assertRaises(editorial_compose.EditorialError) as ctx:
            editorial_compose.validate_manifest(m, REPO_ROOT)
        self.assertEqual(ctx.exception.code, "HIGHLIGHT_VALUE_UNVERIFIED")

    def test_regiao_inexistente_reprovada(self):
        m = load_fixture()
        m["scenes"][0]["proof"]["region"] = "regiao-fantasma"
        with self.assertRaises(editorial_compose.EditorialError) as ctx:
            editorial_compose.validate_manifest(m, REPO_ROOT)
        self.assertEqual(ctx.exception.code, "PROOF_EVIDENCE_MISSING")


class TestIsolamento(unittest.TestCase):
    """C -_midia fora dos escopos do cliente e recusada."""

    def test_evidencia_fora_do_escopo(self):
        m = load_fixture()
        m["evidence"][0]["path"] = "marcas/marcasalao/comfyui/custom_nodes/servidor02_gemini/assets/marcasalao-logo.png"
        with self.assertRaises(editorial_compose.EditorialError) as ctx:
            editorial_compose.validate_manifest(m, REPO_ROOT)
        self.assertEqual(ctx.exception.code, "ASSET_SCOPE_VIOLATION")


class TestLegendas(unittest.TestCase):
    """D - legendas queimadas nao duplicam a CTA impressa nem se repetem."""

    def setUp(self):
        self.req = load_v27("pedido-editorial-v27.video-request.json")
        self.manifest = load_v27("campanha-v27.editorial.json")

    def test_legendas_unicas(self):
        captions = [s["caption"] for s in self.req["scenes"]]
        self.assertEqual(len(captions), len(set(captions)))

    def test_legenda_endcard_nao_duplica_cta_impressa(self):
        cta = self.req["scenes"][-1]["caption"]
        self.assertNotEqual(cta, ENDCARD_CTA_IMPRESSA)
        self.assertNotIn(ENDCARD_CTA_IMPRESSA, cta)

    def test_legendas_nao_repetem_texto_editorial_queimado(self):
        baked = set()
        for scene in self.manifest["scenes"]:
            for part in scene.get("parts", [scene]):
                heading = part.get("heading")
                if heading:
                    baked.add(heading["text"])
                for hl in part.get("highlights", []):
                    baked.add(hl["value"])
        for scene in self.req["scenes"]:
            self.assertNotIn(scene["caption"], baked)


class TestMapeamento(unittest.TestCase):
    """E - cada cena referencia midia cadastrada, com tipo coerente."""

    def test_mapeamento_cena_midia(self):
        req = load_v27("pedido-editorial-v27.video-request.json")
        media = {m["id"]: m for m in req["media"]}
        self.assertEqual(len(media), len(req["media"]))
        for scene in req["scenes"]:
            self.assertIn(scene["mediaId"], media)
            self.assertGreater(scene["durationMs"], 0)
        self.assertEqual(media["ns001-c1-agenda"]["type"], "video")
        self.assertEqual(media["ns001-c2-status"]["type"], "video")
        self.assertEqual(media["ns001-c3-filtro"]["type"], "image")
        self.assertEqual(media["ns001-c4-cta"]["type"], "image")


class TestAreasSeguras(unittest.TestCase):
    """F - layout critico fora da area util reprova; captionBand validada."""

    def test_elemento_fora_da_area_util(self):
        m = load_fixture()
        reports = [{"sceneId": "fx", "layout": [
            {"kind": "text", "critical": True, "x": 0, "y": 0, "w": 100, "h": 40}]}]
        result = editorial_compose.check_safe_areas(m, reports)
        self.assertTrue(result[0]["violations"])

    def test_elemento_dentro_da_area_util(self):
        m = load_fixture()
        rect = editorial_compose.safe_area_rect(m, "instagram-reels-video")
        reports = [{"sceneId": "fx", "layout": [
            {"kind": "text", "critical": True, "x": rect["x"], "y": rect["y"],
             "w": 100, "h": 40}]}]
        result = editorial_compose.check_safe_areas(m, reports)
        self.assertFalse(result[0]["violations"])

    def test_caption_band_invalida(self):
        m = load_fixture()
        m["captionBand"]["height"] = 0
        with self.assertRaises(editorial_compose.EditorialError) as ctx:
            editorial_compose.validate_manifest(m, REPO_ROOT)
        self.assertEqual(ctx.exception.code, "CAPTION_BAND_INVALID")

    def test_caption_band_fora_do_canvas(self):
        m = load_fixture()
        m["captionBand"]["y"] = m["canvas"]["height"]
        with self.assertRaises(editorial_compose.EditorialError) as ctx:
            editorial_compose.validate_manifest(m, REPO_ROOT)
        self.assertEqual(ctx.exception.code, "CAPTION_BAND_INVALID")


class TestCenasDistintas(unittest.TestCase):
    """G - cenas 1 e 2 usam componentes e layouts diferentes."""

    def test_componentes_distintos(self):
        m = load_v27("campanha-v27.editorial.json")
        c1, c2 = m["scenes"][0], m["scenes"][1]
        self.assertEqual(c1["component"], "product-proof")
        self.assertEqual(c2["component"], "status-sequence")
        self.assertNotEqual(json.dumps(c1.get("parts"), sort_keys=True),
                            json.dumps(c2.get("states"), sort_keys=True))


class TestPortabilidade(unittest.TestCase):
    """I - nenhum caminho absoluto de maquina nos arquivos versionados v2.7."""

    def test_sem_caminhos_de_maquina(self):
        offenders = []
        for dirpath, _dirnames, filenames in os.walk(V27_DIR):
            for fname in filenames:
                if not fname.endswith((".json", ".md", ".txt")):
                    continue
                path = os.path.join(dirpath, fname)
                with open(path, encoding="utf-8") as handle:
                    text = handle.read()
                for token in ("C:/Users", "C:\\Users", "/c/Users", "\\Usuario\\"):
                    if token in text:
                        offenders.append((fname, token))
        self.assertFalse(offenders, offenders)


class TestEstiloLegenda(unittest.TestCase):
    """J - referencia do renderizador canonico em 1080x1920."""

    def test_estilo_referencia(self):
        style = render_local.build_subtitle_style(1080, 1920)
        self.assertIn("Fontsize=40", style)
        self.assertIn("MarginV=270", style)
        self.assertIn("PrimaryColour=&H00FFFFFF", style)


class TestReutilizacaoFixture(unittest.TestCase):
    """Prova de reutilizacao: mesma engine, apenas configuracao ficticia."""

    def test_fixture_valida_com_paleta_propria(self):
        m = load_fixture()
        refs = editorial_compose.validate_manifest(m, REPO_ROOT)
        self.assertIn("cap-exemplo", refs["evidence"])
        real = load_v27("campanha-v27.editorial.json")
        self.assertNotEqual(m["brand"]["primaryColor"], real["brand"]["primaryColor"])
        self.assertNotEqual(m["clientId"], real["clientId"])
        self.assertEqual(m["schemaVersion"], real["schemaVersion"])

    def test_fixture_nao_usa_escopo_de_cliente_real(self):
        m = load_fixture()
        for scope in m["assetScopes"]:
            self.assertNotIn("marcasalao", scope)
            self.assertNotIn(".workspace", scope)


if __name__ == "__main__":
    unittest.main()