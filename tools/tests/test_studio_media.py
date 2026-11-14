"""Testes da biblioteca de midia por trabalho (studio_media + image_adapters).

Cobrem contratos visuais via ponte, importacao validada pelo conteudo,
versoes e selecao, pedidos visuais, simulador deterministico, adaptador
Google Gemini simulado (sem rede), falhas, concorrencia, reinicio,
isolamento entre marcas e materializacao no AssetManifest do render.
"""

import base64
import hashlib
import io
import json
import os
import shutil
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import image_adapters
import render_local
import studio_media
import video_studio
from test_video_studio import (
    HAS_BRIDGE,
    HAS_FFMPEG,
    REQUIRE_RENDER,
    STUDIO_ROOT,
    StudioTestBase,
    read_json,
)

PROJECT_MS = "platform/examples/projects/marca-salao-social.project.json"
PROJECT_MTH = "platform/examples/projects/multitrack-hub-social.project.json"


def make_png(width=64, height=64, seed="fixture"):
    return image_adapters.SimulatorImageAdapter().generate(
        str(seed), {"width": width, "height": height}
    )["bytes"]


def b64(data):
    return base64.b64encode(data).decode("ascii")


CREATIVE = {
    "hookOptions": [{"id": "hook-1", "text": "Agenda organizada", "angle": "clareza"}],
    "selectedHookId": "hook-1",
    "scriptSummary": "Demonstracao ficticia para testes.",
    "videoScenes": [
        {
            "id": "cena-abertura", "objective": "Abertura", "narrativeFunction": "hook",
            "durationMs": 4000, "titleOverlay": "Abertura", "caption": "Legenda 1",
            "narration": "Narracao 1", "requiredMediaDescriptor": "Ilustracao de abertura com agenda",
            "motionIntent": "none",
        },
        {
            "id": "cena-prova", "objective": "Prova", "narrativeFunction": "demonstration",
            "durationMs": 4000, "titleOverlay": "Prova", "caption": "Legenda 2",
            "narration": "Narracao 2", "requiredMediaDescriptor": "Captura da agenda",
            "mediaId": "agenda", "motionIntent": "none",
        },
    ],
    "carouselCards": [
        {"id": "capa", "role": "cover", "title": "Capa", "body": "Subtitulo", "requiredMediaDescriptor": "Imagem de capa"},
        {"id": "conteudo", "role": "content", "title": "Conteudo", "body": "Texto", "mediaId": "agenda"},
        {"id": "fechamento", "role": "cta", "title": "Saiba mais", "body": "Confira"},
    ],
    "channelCopies": [],
}


class MediaTestBase(StudioTestBase):
    def create_demo(self, brand="marca-salao", work_id=None):
        body = {"brand": brand}
        if work_id:
            body["id"] = work_id
        status, data = self.request("POST", "/api/works/demo", body)
        self.assertEqual(status, 200, data)
        return data["work"]["id"]

    def save_creative(self, work_id, creative=None):
        status, data = self.request("POST", "/api/works/planning/save", {
            "workId": work_id, "creative": creative or CREATIVE, "markCreativeChecked": True,
        })
        self.assertEqual(status, 200, data)
        return data

    def get_library(self, work_id):
        status, data = self.request("GET", "/api/works/media-library?id=" + work_id)
        self.assertEqual(status, 200, data)
        return data

    def import_png(self, work_id, data=None, **extra):
        payload = {
            "workId": work_id,
            "dataBase64": b64(data if data is not None else make_png()),
            "fileName": extra.pop("fileName", "teste.png"),
            "origin": extra.pop("origin", "imported-manual"),
            "license": extra.pop("license", "pending"),
        }
        payload.update(extra)
        return self.request("POST", "/api/works/media/import", payload)

    def create_request(self, work_id, target_kind="video_scene", target_id="cena-abertura", **extra):
        payload = {"workId": work_id, "targetKind": target_kind, "targetId": target_id}
        payload.update(extra)
        return self.request("POST", "/api/works/media/request/create", payload)

    def generate(self, work_id, request_id, provider="simulator", confirm=True, fingerprint=None):
        payload = {"workId": work_id, "requestId": request_id, "provider": provider, "confirm": confirm}
        if fingerprint is not None:
            payload["expectedLibraryFingerprint"] = fingerprint
        return self.request("POST", "/api/works/media/generate", payload)


class ImageInspectionTest(unittest.TestCase):
    def test_png_valido(self):
        info = image_adapters.inspect_image_bytes(make_png(48, 96))
        self.assertEqual(info["format"], "png")
        self.assertEqual((info["width"], info["height"]), (48, 96))

    def test_formato_invalido(self):
        with self.assertRaises(ValueError):
            image_adapters.inspect_image_bytes(b"isto nao e uma imagem de verdade")

    def test_arquivo_pequeno(self):
        with self.assertRaises(ValueError):
            image_adapters.inspect_image_bytes(b"\x89PNG\r\n\x1a\n")

    def test_limite_de_tamanho(self):
        with self.assertRaises(ValueError):
            image_adapters.inspect_image_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * (image_adapters.MAX_IMAGE_BYTES + 1))

    def test_jpeg_minimo_sof(self):
        # JPEG com marcador SOF0 sintetico para o leitor de dimensoes.
        data = b"\xff\xd8\xff\xe0\x00\x04\x00\x00" + b"\xff\xc0\x00\x0b\x08\x00\x40\x00\x30\x01\x01\x11\x00" + b"\xff\xd9"
        info = image_adapters.inspect_image_bytes(data)
        self.assertEqual(info["format"], "jpeg")
        self.assertEqual((info["width"], info["height"]), (48, 64))

    def test_webp_vp8l(self):
        width, height = 100, 60
        bits = (width - 1) | ((height - 1) << 14)
        payload = b"\x2f" + bits.to_bytes(4, "little")
        chunk = b"VP8L" + len(payload).to_bytes(4, "little") + payload
        data = b"RIFF" + (4 + len(chunk)).to_bytes(4, "little") + b"WEBP" + chunk
        info = image_adapters.inspect_image_bytes(data)
        self.assertEqual(info["format"], "webp")
        self.assertEqual((info["width"], info["height"]), (100, 60))

    def test_simulador_deterministico(self):
        a = image_adapters.SimulatorImageAdapter().generate("mesmo prompt", {"width": 64, "height": 64})
        b = image_adapters.SimulatorImageAdapter().generate("mesmo prompt", {"width": 64, "height": 64})
        self.assertEqual(a["bytes"], b["bytes"])
        self.assertTrue(a["simulated"])
        c = image_adapters.SimulatorImageAdapter().generate("outro prompt", {"width": 64, "height": 64})
        self.assertNotEqual(a["bytes"], c["bytes"])


class GeminiAdapterTest(unittest.TestCase):
    ENV_WITH_KEY = {"GEMINI_API_KEY": "chave-ficticia-de-teste"}

    def _response(self, payload):
        return io.BytesIO(json.dumps(payload).encode("utf-8"))

    def test_sem_credencial(self):
        adapter = image_adapters.GeminiImageAdapter(env={})
        with self.assertRaises(image_adapters.ImageProviderUnavailableError) as ctx:
            adapter.generate("prompt", {"width": 64, "height": 64}, "1:1")
        self.assertEqual(ctx.exception.code, "IMAGE_PROVIDER_NO_CREDENTIAL")

    def test_modelo_invalido(self):
        adapter = image_adapters.GeminiImageAdapter(env={**self.ENV_WITH_KEY, "STUDIO_GEMINI_IMAGE_MODEL": "Modelo Invalido!"})
        with self.assertRaises(image_adapters.ImageAdapterError) as ctx:
            adapter.generate("prompt", {"width": 64, "height": 64}, "1:1")
        self.assertEqual(ctx.exception.code, "IMAGE_PROVIDER_BAD_MODEL")

    def test_endpoint_invalido(self):
        adapter = image_adapters.GeminiImageAdapter(env={**self.ENV_WITH_KEY, "STUDIO_GEMINI_IMAGE_ENDPOINT": "ftp://x"})
        with self.assertRaises(image_adapters.ImageAdapterError) as ctx:
            adapter.generate("prompt", {"width": 64, "height": 64}, "1:1")
        self.assertEqual(ctx.exception.code, "IMAGE_PROVIDER_BAD_ENDPOINT")

    def test_sucesso_com_imagem(self):
        png = make_png(32, 32)
        payload = {
            "candidates": [{"finishReason": "STOP", "content": {"parts": [
                {"text": "aqui esta"},
                {"inlineData": {"mimeType": "image/png", "data": b64(png)}},
            ]}}],
            "modelVersion": "gemini-test",
        }
        adapter = image_adapters.GeminiImageAdapter(env=self.ENV_WITH_KEY)
        with mock.patch.object(image_adapters.urllib.request, "urlopen", return_value=self._response(payload)) as opened:
            result = adapter.generate("prompt", {"width": 32, "height": 32}, "1:1", anchor_bytes=png, anchor_mime="image/png")
        self.assertEqual(result["bytes"], png)
        self.assertFalse(result["simulated"])
        self.assertEqual(result["provider"], "google-gemini")
        req = opened.call_args[0][0]
        self.assertIn("x-goog-api-key", {k.lower() for k in req.headers})
        self.assertIn(":generateContent", req.full_url)
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["generationConfig"]["responseModalities"], ["TEXT", "IMAGE"])
        self.assertEqual(body["generationConfig"]["imageConfig"]["aspectRatio"], "1:1")
        self.assertEqual(len(body["contents"][0]["parts"]), 2)

    def test_cota_429(self):
        adapter = image_adapters.GeminiImageAdapter(env=self.ENV_WITH_KEY)
        err = image_adapters.urllib.error.HTTPError("http://x", 429, "quota", {}, io.BytesIO(b"{}"))
        with mock.patch.object(image_adapters.urllib.request, "urlopen", side_effect=err):
            with self.assertRaises(image_adapters.ImageProviderUnavailableError) as ctx:
                adapter.generate("prompt", {"width": 32, "height": 32}, "1:1")
        self.assertEqual(ctx.exception.code, "IMAGE_PROVIDER_QUOTA")

    def test_timeout(self):
        adapter = image_adapters.GeminiImageAdapter(env=self.ENV_WITH_KEY)
        with mock.patch.object(image_adapters.urllib.request, "urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaises(image_adapters.ImageProviderTimeoutError):
                adapter.generate("prompt", {"width": 32, "height": 32}, "1:1")

    def test_recusa_do_provedor(self):
        adapter = image_adapters.GeminiImageAdapter(env=self.ENV_WITH_KEY)
        payload = {"promptFeedback": {"blockReason": "SAFETY"}}
        with mock.patch.object(image_adapters.urllib.request, "urlopen", return_value=self._response(payload)):
            with self.assertRaises(image_adapters.ImageAdapterError) as ctx:
                adapter.generate("prompt", {"width": 32, "height": 32}, "1:1")
        self.assertEqual(ctx.exception.code, "IMAGE_PROVIDER_REFUSED")

    def test_resposta_sem_imagem(self):
        adapter = image_adapters.GeminiImageAdapter(env=self.ENV_WITH_KEY)
        payload = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "so texto"}]}}]}
        with mock.patch.object(image_adapters.urllib.request, "urlopen", return_value=self._response(payload)):
            with self.assertRaises(image_adapters.ImageAdapterError) as ctx:
                adapter.generate("prompt", {"width": 32, "height": 32}, "1:1")
        self.assertEqual(ctx.exception.code, "IMAGE_PROVIDER_NO_IMAGE")

    def test_arquivo_invalido_do_provedor(self):
        adapter = image_adapters.GeminiImageAdapter(env=self.ENV_WITH_KEY)
        payload = {"candidates": [{"content": {"parts": [
            {"inlineData": {"mimeType": "image/png", "data": b64(b"nao e imagem")}},
        ]}}]}
        with mock.patch.object(image_adapters.urllib.request, "urlopen", return_value=self._response(payload)):
            with self.assertRaises(image_adapters.ImageAdapterError) as ctx:
                adapter.generate("prompt", {"width": 32, "height": 32}, "1:1")
        self.assertEqual(ctx.exception.code, "IMAGE_PROVIDER_INVALID_FILE")

    def test_status_nao_expoe_chave(self):
        providers = image_adapters.provider_status(env=self.ENV_WITH_KEY)
        gemini = next(p for p in providers if p["providerId"] == "google-gemini")
        self.assertTrue(gemini["configured"])
        self.assertNotIn("chave-ficticia", json.dumps(providers))


class MediaLibraryHttpTest(MediaTestBase):
    def test_legado_inicializa_biblioteca(self):
        wid = self.create_demo()
        lib = self.get_library(wid)
        self.assertFalse(lib["initializedOnDisk"])
        ids = [a["id"] for a in lib["mediaLibrary"]["assets"]]
        self.assertIn("agenda", ids)
        for asset in lib["mediaLibrary"]["assets"]:
            self.assertTrue(asset["selectedVersionId"])
            self.assertEqual(len(asset["versions"]), 1)

    def test_import_manual_cria_versao(self):
        wid = self.create_demo()
        png = make_png(80, 60)
        status, data = self.import_png(wid, png, fileName="externa.png", origin="external-tool",
                                       originDetail={"tool": "Google Flow (ficticio)"})
        self.assertEqual(status, 200, data)
        lib = self.get_library(wid)
        asset = next(a for a in lib["mediaLibrary"]["assets"] if a["id"] == data["assetId"])
        version = asset["versions"][-1]
        self.assertEqual(version["sha256"], hashlib.sha256(png).hexdigest())
        self.assertEqual((version["width"], version["height"]), (80, 60))
        self.assertEqual(version["origin"], "external-tool")
        self.assertEqual(version["provenance"]["params"]["originDetail"]["tool"], "Google Flow (ficticio)")
        self.assertTrue(lib["initializedOnDisk"])

    def test_import_conteudo_invalido(self):
        wid = self.create_demo()
        status, data = self.import_png(wid, b"conteudo que nao e imagem")
        self.assertEqual(status, 400)
        self.assertIn("imagem", data["error"].lower())

    def test_import_source_path_contencao(self):
        wid = self.create_demo()
        status, _ = self.request("POST", "/api/works/media/import", {
            "workId": wid, "sourcePath": "../../fora.png", "origin": "imported-manual",
        })
        self.assertEqual(status, 400)

    def test_import_source_path_valido(self):
        wid = self.create_demo()
        rel = f".workspace/studio/works/{wid}/media/agenda.png"
        status, data = self.request("POST", "/api/works/media/import", {
            "workId": wid, "sourcePath": rel, "origin": "imported-manual",
        })
        self.assertEqual(status, 200, data)

    def test_register_existing(self):
        wid = self.create_demo()
        lib = self.get_library(wid)
        pending = lib["unregisteredFiles"]
        # agenda.png ja referenciada; gera arquivo novo na pasta de midia
        extra_rel = f".workspace/studio/works/{wid}/media/extra.png"
        with open(render_local.fs_path(os.path.join(STUDIO_ROOT, extra_rel)), "wb") as handle:
            handle.write(make_png(40, 40))
        status, data = self.request("POST", "/api/works/media/register", {
            "workId": wid, "path": extra_rel, "origin": "studio-work",
        })
        self.assertEqual(status, 200, data)
        status, data = self.request("POST", "/api/works/media/register", {
            "workId": wid, "path": extra_rel,
        })
        self.assertEqual(status, 400)

    def test_register_fora_da_pasta_rejeitado(self):
        wid = self.create_demo()
        status, _ = self.request("POST", "/api/works/media/register", {
            "workId": wid, "path": "platform/examples/projects/marca-salao-social.project.json",
        })
        self.assertEqual(status, 400)

    def test_pedido_visual_geometria_do_perfil(self):
        wid = self.create_demo()
        self.save_creative(wid)
        status, data = self.create_request(wid)
        self.assertEqual(status, 200, data)
        entry = data["overview"]["mediaLibrary"]["requests"][-1]
        req = entry["request"]
        self.assertEqual(req["profileId"], "instagram-reels-video")
        self.assertEqual(req["aspectRatio"], "9:16")
        self.assertEqual(req["geometry"], {"width": 1080, "height": 1920})
        self.assertEqual(req["context"]["descriptor"], "Ilustracao de abertura com agenda")
        self.assertIn("Ilustracao de abertura", entry["providerTextPreview"])
        status, data = self.create_request(wid, "carousel_card", "capa")
        self.assertEqual(status, 200, data)
        req = data["overview"]["mediaLibrary"]["requests"][-1]["request"]
        self.assertEqual(req["aspectRatio"], "1:1")
        self.assertEqual(req["geometry"], {"width": 1080, "height": 1080})

    def test_pedido_alvo_inexistente(self):
        wid = self.create_demo()
        self.save_creative(wid)
        status, _ = self.create_request(wid, "video_scene", "cena-fantasma")
        self.assertEqual(status, 400)

    def test_ancora_e_pedido_com_referencia(self):
        wid = self.create_demo()
        self.save_creative(wid)
        status, imp = self.import_png(wid)
        self.assertEqual(status, 200, imp)
        status, anchor = self.request("POST", "/api/works/media/anchor", {
            "workId": wid, "title": "Referencia de teste",
            "assetId": imp["assetId"], "versionId": imp["versionId"],
            "direction": "Fundo neutro com agenda em destaque",
            "mustInclude": ["agenda"], "mustAvoid": ["dados pessoais"],
        })
        self.assertEqual(status, 200, anchor)
        status, data = self.create_request(wid, anchorId=anchor["anchorId"], sendAnchorToProvider=True)
        self.assertEqual(status, 200, data)
        entry = data["overview"]["mediaLibrary"]["requests"][-1]
        self.assertEqual(entry["request"]["anchor"]["anchorId"], anchor["anchorId"])
        self.assertIn("Direcao visual de referencia", entry["providerTextPreview"])
        self.assertIn("Elementos a evitar: dados pessoais", entry["providerTextPreview"])

    def test_ancora_invalida_rejeitada(self):
        wid = self.create_demo()
        status, imp = self.import_png(wid)
        status, data = self.request("POST", "/api/works/media/anchor", {
            "workId": wid, "title": "X", "assetId": imp["assetId"], "versionId": imp["versionId"],
            "direction": "",
        })
        self.assertEqual(status, 400)

    def test_simulador_exige_confirmacao(self):
        wid = self.create_demo()
        self.save_creative(wid)
        status, data = self.create_request(wid)
        rid = data["requestId"]
        status, err = self.generate(wid, rid, confirm=False)
        self.assertEqual(status, 400)
        self.assertIn("confirmacao", err["error"])

    def test_simulador_gera_candidato_simulado(self):
        wid = self.create_demo()
        self.save_creative(wid)
        status, data = self.create_request(wid)
        rid = data["requestId"]
        status, gen = self.generate(wid, rid)
        self.assertEqual(status, 200, gen)
        lib = self.get_library(wid)
        entry = next(r for r in lib["mediaLibrary"]["requests"] if r["request"]["id"] == rid)
        cand = entry["candidates"][-1]
        self.assertEqual(cand["provider"], "simulator")
        self.assertFalse(cand["stale"])
        asset = next(a for a in lib["mediaLibrary"]["assets"] if a["id"] == gen["assetId"])
        version = next(v for v in asset["versions"] if v["versionId"] == gen["versionId"])
        self.assertTrue(version["simulated"])
        self.assertEqual(version["origin"], "generated-simulator")
        self.assertEqual(version["category"] if "category" in version else asset["category"], "illustration")
        self.assertEqual(version["provenance"]["provider"], "simulator")
        self.assertEqual(version["provenance"]["resultSha256"], version["sha256"])
        self.assertEqual(entry["attempts"][-1]["status"], "completed")

    def test_provedor_manual_orienta_importacao(self):
        wid = self.create_demo()
        self.save_creative(wid)
        status, data = self.create_request(wid)
        status, err = self.generate(wid, data["requestId"], provider="manual")
        self.assertEqual(status, 400)
        self.assertIn("Importar", err["error"])

    def test_gemini_sem_chave_http_503(self):
        wid = self.create_demo()
        self.save_creative(wid)
        status, data = self.create_request(wid)
        env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
        with mock.patch.dict(os.environ, env, clear=True):
            status, err = self.generate(wid, data["requestId"], provider="google-gemini")
        self.assertEqual(status, 503)
        self.assertEqual(err["code"], "IMAGE_PROVIDER_NO_CREDENTIAL")
        lib = self.get_library(wid)
        entry = next(r for r in lib["mediaLibrary"]["requests"] if r["request"]["id"] == data["requestId"])
        self.assertEqual(entry["status"], "failed")
        self.assertEqual(entry["attempts"][-1]["code"], "IMAGE_PROVIDER_NO_CREDENTIAL")
        self.assertEqual(entry["candidates"], [])

    def test_gemini_simulado_no_servidor(self):
        wid = self.create_demo()
        self.save_creative(wid)
        status, data = self.create_request(wid)
        rid = data["requestId"]
        png = make_png(1080, 1920, seed="gemini-ficticio")
        payload = {"candidates": [{"finishReason": "STOP", "content": {"parts": [
            {"inlineData": {"mimeType": "image/png", "data": b64(png)}},
        ]}}]}
        env = {**os.environ, "GEMINI_API_KEY": "chave-ficticia"}
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(image_adapters.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            status, gen = self.generate(wid, rid, provider="google-gemini")
        self.assertEqual(status, 200, gen)
        lib = self.get_library(wid)
        asset = next(a for a in lib["mediaLibrary"]["assets"] if a["id"] == gen["assetId"])
        version = next(v for v in asset["versions"] if v["versionId"] == gen["versionId"])
        self.assertEqual(version["origin"], "generated-google-gemini")
        self.assertFalse(version["simulated"])
        self.assertEqual(version["sha256"], hashlib.sha256(png).hexdigest())

    def test_prompt_atualizado_marca_candidatos(self):
        wid = self.create_demo()
        self.save_creative(wid)
        status, data = self.create_request(wid)
        rid = data["requestId"]
        status, gen = self.generate(wid, rid)
        self.assertEqual(status, 200)
        status, upd = self.request("POST", "/api/works/media/request/update", {
            "workId": wid, "requestId": rid, "prompt": "Prompt revisado pelo operador",
        })
        self.assertEqual(status, 200, upd)
        entry = next(r for r in upd["overview"]["mediaLibrary"]["requests"] if r["request"]["id"] == rid)
        self.assertTrue(all(c["stale"] for c in entry["candidates"]))
        self.assertTrue(entry["contextOutdated"])

    def test_referencia_atualizada_marca_candidatos(self):
        wid = self.create_demo()
        self.save_creative(wid)
        status, imp = self.import_png(wid)
        status, anchor = self.request("POST", "/api/works/media/anchor", {
            "workId": wid, "title": "Ref", "assetId": imp["assetId"], "versionId": imp["versionId"],
            "direction": "Direcao inicial",
        })
        aid = anchor["anchorId"]
        status, data = self.create_request(wid, anchorId=aid, sendAnchorToProvider=True)
        rid = data["requestId"]
        status, gen = self.generate(wid, rid)
        self.assertEqual(status, 200)
        status, imp2 = self.import_png(wid, make_png(64, 64, seed="nova-versao"))
        status, anchor2 = self.request("POST", "/api/works/media/anchor", {
            "workId": wid, "anchorId": aid, "title": "Ref",
            "assetId": imp2["assetId"], "versionId": imp2["versionId"],
            "direction": "Direcao revisada",
        })
        self.assertEqual(status, 200, anchor2)
        lib = self.get_library(wid)
        entry = next(r for r in lib["mediaLibrary"]["requests"] if r["request"]["id"] == rid)
        self.assertTrue(all(c["stale"] for c in entry["candidates"]))

    def test_conflito_de_fingerprint(self):
        wid = self.create_demo()
        status, data = self.import_png(wid, expectedLibraryFingerprint="0" * 64)
        self.assertEqual(status, 409)
        self.assertTrue(data.get("conflict"))

    def test_selecao_aplica_via_planejamento(self):
        wid = self.create_demo()
        self.save_creative(wid)
        status, data = self.create_request(wid)
        rid = data["requestId"]
        status, gen = self.generate(wid, rid)
        self.assertEqual(status, 200)
        status, sel = self.request("POST", "/api/works/media/select", {
            "workId": wid, "assetId": gen["assetId"], "versionId": gen["versionId"],
            "requestId": rid, "candidateId": gen["candidateId"],
        })
        self.assertEqual(status, 200, sel)
        self.assertTrue(sel["targets"][0]["viaPlanning"])
        status, diff = self.request("POST", "/api/works/planning/diff", {"workId": wid})
        self.assertEqual(status, 200)
        self.assertTrue(diff["editorsDiff"]["video"]["readyToApply"])
        status, applied = self.request("POST", "/api/works/planning/apply", {
            "workId": wid, "applyVideo": True,
            "preserveCardIds": ["capa", "conteudo", "fechamento"],
        })
        self.assertEqual(status, 200, applied)
        self.assertEqual(applied["applied"]["video"]["status"], "applied")
        vreq = applied["workData"]["videoRequest"]
        media = next(m for m in vreq["media"] if m["id"] == gen["assetId"])
        self.assertEqual(media["origin"], "generated-simulator")
        self.assertEqual(media["license"], "owned-synthetic")
        scene = next(s for s in vreq["scenes"] if s["id"] == "cena-abertura")
        self.assertEqual(scene["mediaId"], gen["assetId"])

    def test_checksum_divergente_preserva_selecao(self):
        wid = self.create_demo()
        self.save_creative(wid)
        status, data = self.create_request(wid)
        rid = data["requestId"]
        status, gen = self.generate(wid, rid)
        lib = self.get_library(wid)
        asset = next(a for a in lib["mediaLibrary"]["assets"] if a["id"] == gen["assetId"])
        version = next(v for v in asset["versions"] if v["versionId"] == gen["versionId"])
        abs_path = os.path.join(STUDIO_ROOT, version["path"])
        with open(render_local.fs_path(abs_path), "ab") as handle:
            handle.write(b"adulteracao")
        before = self.get_library(wid)
        asset_before = next(a for a in before["mediaLibrary"]["assets"] if a["id"] == gen["assetId"])
        selections_before = before["mediaLibrary"]["selections"]
        status, err = self.request("POST", "/api/works/media/select", {
            "workId": wid, "assetId": gen["assetId"], "versionId": gen["versionId"],
            "requestId": rid, "candidateId": gen["candidateId"],
        })
        self.assertEqual(status, 400)
        self.assertIn("checksum", err["error"].lower())
        lib2 = self.get_library(wid)
        asset2 = next(a for a in lib2["mediaLibrary"]["assets"] if a["id"] == gen["assetId"])
        self.assertEqual(asset2["selectedVersionId"], asset_before["selectedVersionId"])
        self.assertEqual(lib2["mediaLibrary"]["selections"], selections_before)

    def test_miniaturas_por_referencia_valida(self):
        wid = self.create_demo()
        status, imp = self.import_png(wid)
        url = f"/library-media?work={wid}&asset={imp['assetId']}&version={imp['versionId']}"
        status, body = self.request("GET", url)
        self.assertEqual(status, 200)
        self.assertTrue(isinstance(body, bytes) and body[:8] == b"\x89PNG\r\n\x1a\n")
        status, _ = self.request("GET", f"/library-media?work={wid}&asset={imp['assetId']}&version=v-inexistente")
        self.assertEqual(status, 404)
        status, _ = self.request("GET", f"/library-media?work=trabalho-fantasma&asset={imp['assetId']}&version={imp['versionId']}")
        self.assertEqual(status, 404)

    def test_reinicio_restaura_estado(self):
        wid = self.create_demo()
        self.save_creative(wid)
        status, imp = self.import_png(wid)
        status, anchor = self.request("POST", "/api/works/media/anchor", {
            "workId": wid, "title": "Ref", "assetId": imp["assetId"], "versionId": imp["versionId"],
            "direction": "Direcao de teste",
        })
        status, data = self.create_request(wid, anchorId=anchor["anchorId"])
        rid = data["requestId"]
        status, gen = self.generate(wid, rid)
        status, sel = self.request("POST", "/api/works/media/select", {
            "workId": wid, "assetId": gen["assetId"], "versionId": gen["versionId"],
            "requestId": rid, "candidateId": gen["candidateId"],
        })
        self.assertEqual(status, 200)
        self.restart_server()
        lib = self.get_library(wid)
        self.assertTrue(lib["initializedOnDisk"])
        entry = next(r for r in lib["mediaLibrary"]["requests"] if r["request"]["id"] == rid)
        self.assertEqual(entry["selectedCandidateId"], gen["candidateId"])
        self.assertEqual(len(entry["candidates"]), 1)
        self.assertEqual(len(lib["mediaLibrary"]["anchors"]), 1)
        self.assertTrue(any(s["assetId"] == gen["assetId"] for s in lib["mediaLibrary"]["selections"]))
        status, opened = self.request("GET", "/api/works/open?id=" + wid)
        self.assertEqual(status, 200)
        self.assertIn("mediaLibrary", opened)

    def test_isolamento_entre_marcas(self):
        wid_ms = self.create_demo("marca-salao")
        wid_mth = self.create_demo("multitrack-hub")
        self.save_creative(wid_ms)
        status, data = self.create_request(wid_ms)
        rid = data["requestId"]
        status, gen = self.generate(wid_ms, rid)
        self.assertEqual(status, 200)
        lib_mth = self.get_library(wid_mth)
        ids = [a["id"] for a in lib_mth["mediaLibrary"]["assets"]]
        self.assertNotIn(gen["assetId"], ids)
        self.assertEqual(lib_mth["mediaLibrary"]["requests"], [])
        self.assertEqual(lib_mth["mediaLibrary"]["anchors"], [])
        dumped = json.dumps(lib_mth)
        self.assertNotIn(rid, dumped)
        self.assertNotIn("Ilustracao de abertura com agenda", dumped)

    def test_midia_compartilhada_atualiza_todos_os_vinculos(self):
        wid = self.create_demo()
        self.save_creative(wid)
        # Aplica o roteiro: 'agenda' passa a ser consumida por cena e card
        status, applied = self.request("POST", "/api/works/planning/apply", {
            "workId": wid, "applyVideo": True, "applyCarousel": True,
        })
        self.assertEqual(status, 200, applied)
        lib = self.get_library(wid)
        asset = next(a for a in lib["mediaLibrary"]["assets"] if a["id"] == "agenda")
        consumers = asset["consumers"]
        modalities = {c["modality"] for c in consumers}
        self.assertIn("video", modalities)
        self.assertIn("carousel", modalities)
        status, imp = self.import_png(wid, make_png(540, 960, seed="nova-agenda"), assetId="agenda", origin="imported-manual")
        self.assertEqual(status, 200, imp)
        status, sel = self.request("POST", "/api/works/media/select", {
            "workId": wid, "assetId": "agenda", "versionId": imp["versionId"],
            "updateLinkedTargets": True,
        })
        self.assertEqual(status, 200, sel)
        self.assertGreaterEqual(len(sel["targets"]), 2)
        status, opened = self.request("GET", "/api/works/open?id=" + wid)
        vmedia = next(m for m in opened["videoRequest"]["media"] if m["id"] == "agenda")
        cmedia = next(m for m in opened["carouselRequest"]["media"] if m["id"] == "agenda")
        self.assertEqual(vmedia["path"], cmedia["path"])
        self.assertIn(imp["versionId"], vmedia["path"])

    def test_host_origin_invalidos(self):
        wid = self.create_demo()
        status, _ = self.request("POST", "/api/works/media/import", {
            "workId": wid, "dataBase64": b64(make_png()), "origin": "imported-manual",
        }, origin="http://evil.example")
        self.assertEqual(status, 403)


class MediaLibraryRenderTest(MediaTestBase):
    @classmethod
    def setUpClass(cls):
        if not HAS_BRIDGE:
            raise unittest.SkipTest("ponte TypeScript indisponivel")
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError("REQUIRE_RENDER=1 mas FFmpeg/FFprobe ausentes")
            raise unittest.SkipTest("FFmpeg indisponivel")
        super().setUpClass()

    def _wait_export(self, job_id, timeout=240):
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            status, data = self.request("GET", "/api/export/status?job=" + job_id)
            self.assertEqual(status, 200, data)
            if data["status"] in ("completed", "failed"):
                return data
            time.sleep(1)
        self.fail("exportacao nao concluiu no tempo limite")

    def test_render_materializa_asset_manifest_e_revisao_localizada(self):
        wid = self.create_demo()
        self.save_creative(wid)
        status, data = self.create_request(wid)
        rid = data["requestId"]
        status, gen = self.generate(wid, rid)
        self.assertEqual(status, 200)
        status, sel = self.request("POST", "/api/works/media/select", {
            "workId": wid, "assetId": gen["assetId"], "versionId": gen["versionId"],
            "requestId": rid, "candidateId": gen["candidateId"],
        })
        self.assertEqual(status, 200)
        status, applied = self.request("POST", "/api/works/planning/apply", {
            "workId": wid, "applyVideo": True, "applyCarousel": True,
        })
        self.assertEqual(status, 200, applied)
        self.assertEqual(applied["applied"]["video"]["status"], "applied")
        self.assertEqual(applied["applied"]["carousel"]["status"], "applied")
        opened = applied["workData"]
        p = opened["work"]["paths"]

        # Exporta video (primeiro perfil) e carrossel
        status, job = self.request("POST", "/api/export", {
            "request": opened["videoRequest"], "outputDir": p["videoDeliveryDir"],
            "profile": opened["videoRequest"]["profiles"][0], "kind": "video", "workId": wid,
        })
        self.assertEqual(status, 200, job)
        result = self._wait_export(job["jobId"])
        self.assertEqual(result["status"], "completed", result)
        status, job = self.request("POST", "/api/export", {
            "request": opened["carouselRequest"], "outputDir": p["carouselDeliveryDir"],
            "kind": "carousel", "workId": wid,
        })
        self.assertEqual(status, 200, job)
        result = self._wait_export(job["jobId"])
        self.assertEqual(result["status"], "completed", result)

        # AssetManifest do render materializa origem/licenca/hash da versao
        profile_id = opened["videoRequest"]["profiles"][0]
        manifest = read_json(os.path.join(STUDIO_ROOT, p["videoDeliveryDir"], profile_id, "delivery-manifest.json"))
        am_artifact = (manifest.get("artifacts") or {}).get("assetManifest")
        self.assertTrue(am_artifact and am_artifact.get("path"), f"assetManifest ausente no manifesto: {list((manifest.get('artifacts') or {}).keys())}")
        asset_manifest = read_json(os.path.join(STUDIO_ROOT, am_artifact["path"]))
        assets = asset_manifest.get("assets") or []
        self.assertTrue(assets, "inventario sem assets")
        gen_assets = [a for a in assets if a.get("origin") == "generated-simulator"]
        self.assertTrue(gen_assets, f"asset gerado ausente no manifesto: {assets}")
        lib = self.get_library(wid)
        asset = next(a for a in lib["mediaLibrary"]["assets"] if a["id"] == gen["assetId"])
        version = next(v for v in asset["versions"] if v["versionId"] == gen["versionId"])
        self.assertEqual(gen_assets[0]["sha256"], version["sha256"])
        self.assertEqual(gen_assets[0]["license"], "owned-synthetic")

        # FFprobe: zero faixas de audio
        video_rel = manifest["artifacts"]["video"]["path"]
        video_abs = os.path.join(STUDIO_ROOT, video_rel)
        probe = render_local.ffprobe_json(video_abs) if hasattr(render_local, "ffprobe_json") else None
        if probe is None:
            import subprocess
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-show_streams", "-of", "json", render_local.fs_path(video_abs)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            )
            probe = json.loads(out.stdout)
        audio = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
        self.assertEqual(audio, [])

        # Revisao localizada: troca a imagem do card e prova que so o carrossel pede nova revisao
        status, review_before = self.request("GET", "/api/works/review?id=" + wid)
        self.assertEqual(status, 200)
        pieces_before = {pc["pieceKey"]: pc["status"] for pc in review_before["pieces"]}
        video_key = f"video:{profile_id}"
        carousel_key = "carousel:" + opened["carouselRequest"]["profile"]
        self.assertEqual(pieces_before.get(video_key), "pending_review")
        self.assertEqual(pieces_before.get(carousel_key), "pending_review")

        status, imp = self.import_png(wid, make_png(1080, 1080, seed="nova-capa"), origin="imported-manual")
        self.assertEqual(status, 200)
        status, sel = self.request("POST", "/api/works/media/select", {
            "workId": wid, "assetId": imp["assetId"], "versionId": imp["versionId"],
            "targetKind": "carousel_card", "targetId": "capa",
        })
        self.assertEqual(status, 200, sel)
        status, applied = self.request("POST", "/api/works/planning/apply", {
            "workId": wid, "applyCarousel": True,
            "preserveSceneIds": ["cena-abertura", "cena-prova"],
        })
        self.assertEqual(status, 200, applied)
        self.assertEqual(applied["applied"]["carousel"]["status"], "applied")
        status, review_after = self.request("GET", "/api/works/review?id=" + wid)
        pieces_after = {pc["pieceKey"]: pc["status"] for pc in review_after["pieces"]}
        self.assertEqual(pieces_after.get(carousel_key), "draft_outdated")
        self.assertEqual(pieces_after.get(video_key), "pending_review")


if __name__ == "__main__":
    unittest.main()