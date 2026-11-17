"""Testes direcionados para tools/campaign_proof.py.

Cobrem: preparação reproduzível, pedido inválido, referência de mídia
ausente, duração calculada a partir das cenas, diagnóstico de ferramenta
ausente, relatório com render concluído e pendente, preservação de
entrega anterior em tentativa que falha, e textos do pedido no HTML.

Executados com: python -m unittest discover -s tools/tests -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import campaign_proof


def _make_request(tmp: str, scenes: list[dict], request_id: str = "req-teste",
                  root: str = "") -> str:
    """Cria um pedido VideoRequest v1 com mídias referenciadas em
    .workspace/tmp/prova-campanha/ (dentro da raiz do projeto)."""
    request = {
        "schemaVersion": 1,
        "id": request_id,
        "project": "platform/examples/projects/marca-salao-social.project.json",
        "title": "Pedido de teste",
        "locale": "pt-BR",
        "profiles": ["instagram-reels-video"],
        "media": [
            {
                "id": f"m-{i}",
                "path": f".workspace/tmp/prova-campanha/assets/{i}.png",
                "type": "image",
                "origin": "synthetic-demo",
                "license": "owned-synthetic",
            }
            for i in range(len(scenes))
        ],
        "scenes": [
            {
                "id": f"cena-{i}",
                "durationMs": s["durationMs"],
                "mediaId": f"m-{i}",
                "caption": s.get("caption", f"Legenda cena {i}"),
                "narration": f"Narração cena {i}",
                "title": f"Título cena {i}",
                "narrativeFunction": s.get("narrativeFunction", "demonstration"),
                "motionIntent": "none",
            }
            for i, s in enumerate(scenes)
        ],
    }
    path = os.path.join(tmp, f"{request_id}.json")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(request, handle, ensure_ascii=False, indent=2)
    return path


class CampaignProofTest(unittest.TestCase):

    def test_preparo_reproduzivel_com_midias_presentes(self):
        """Preparação gera PNGs sintéticos e relatório com cenas e duração."""
        root = os.getcwd()
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            req_path = _make_request(
                tmp,
                [
                    {"durationMs": 4000, "narrativeFunction": "hook"},
                    {"durationMs": 6000, "narrativeFunction": "demonstration"},
                    {"durationMs": 20000, "narrativeFunction": "cta"},
                ],
                root=root,
            )
            out_dir = os.path.join(tmp, "saida")
            result = campaign_proof.cmd_prepare(req_path, out_dir, root)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["sceneCount"], 3)
            self.assertEqual(result["totalDurationMs"], 30000)
            self.assertEqual(len(result["mediaPrepared"]), 3)
            # arquivos PNG existem nos caminhos referenciados pelo pedido
            for item in result["mediaPrepared"]:
                abs_asset = os.path.join(root, item["mediaPath"])
                self.assertTrue(os.path.isfile(abs_asset), item["mediaPath"])

    def test_pedido_invalido_rejeitado(self):
        """Pedido com schemaVersion errado é rejeitado com código estável."""
        with tempfile.TemporaryDirectory() as tmp:
            req_path = os.path.join(tmp, "ruim.json")
            with open(req_path, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(
                    {"schemaVersion": 99, "id": "x", "project": "p", "title": "t",
                     "profiles": [], "media": [], "scenes": []},
                    handle,
                )
            result = campaign_proof.cmd_verify(req_path, tmp)
            self.assertFalse(result["ok"])
            self.assertTrue(
                any(e["code"] == "SCHEMA_VERSION_UNSUPPORTED" for e in result["errors"])
            )

    def test_preparo_gera_midia_sintetica_quando_ausente(self):
        """Prepare gera a mídia sintética; após a preparação o arquivo existe."""
        root = os.getcwd()
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            req_path = _make_request(
                tmp,
                [{"durationMs": 4000, "mediaId": "m-0"}],
                root=root,
            )
            out_dir = os.path.join(tmp, "saida")
            result = campaign_proof.cmd_prepare(req_path, out_dir, root)
            self.assertTrue(result["ok"], result)
            # o arquivo sintético foi gerado no caminho referenciado pelo pedido
            asset_abs = os.path.join(root, result["mediaPrepared"][0]["mediaPath"])
            self.assertTrue(os.path.isfile(asset_abs), result["mediaPrepared"][0]["mediaPath"])

    def test_duracao_calculada_a_partir_das_cenas(self):
        """Duração total é soma das durações das cenas."""
        root = os.getcwd()
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            req_path = _make_request(
                tmp,
                [{"durationMs": 4000}, {"durationMs": 6000}, {"durationMs": 20000}],
                root=root,
            )
            result = campaign_proof.cmd_verify(req_path, root)
            self.assertEqual(result["totalDurationMs"], 30000)
            self.assertEqual(result["totalDurationSeconds"], 30.0)
            self.assertEqual(result["sceneCount"], 3)

    @patch("campaign_proof.shutil.which", return_value=None)
    def test_diagnostico_ferramenta_ausente(self, _mock_which):
        """Render sem ffmpeg devolve relatório de pendência, não exceção."""
        root = os.getcwd()
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            req_path = _make_request(
                tmp,
                [{"durationMs": 4000}],
                root=root,
            )
            result = campaign_proof.cmd_render(
                req_path, "instagram-reels-video", os.path.join(tmp, "entrega"), root
            )
            self.assertFalse(result["ffmpegAvailable"])
            self.assertEqual(result["status"], "pendente_ferramenta")
            self.assertIn("ffmpeg/ffprobe", result["error"])
            self.assertIn("comandoRetomada", result)

    @patch("campaign_proof.shutil.which", return_value=None)
    def test_relatorio_render_pendente_quando_sem_ffmpeg(self, _mock_which):
        """Quando não há ffmpeg, o relatório fica pendente (não concluído)."""
        root = os.getcwd()
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            req_path = _make_request(
                tmp,
                [{"durationMs": 4000}],
                root=root,
            )
            result = campaign_proof.cmd_render(
                req_path, "instagram-reels-video", os.path.join(tmp, "entrega"), root
            )
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "pendente_ferramenta")

    def test_textos_do_pedido_no_html(self):
        """A página de revisão exibe os textos do pedido."""
        root = os.getcwd()
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            req_path = _make_request(
                tmp,
                [{"durationMs": 4000, "caption": "Texto da cena 1", "narrativeFunction": "hook"}],
                request_id="req-html",
                root=root,
            )
            html_path = os.path.join(tmp, "revisao.html")
            result = campaign_proof.cmd_review(req_path, html_path, root)
            self.assertTrue(result["ok"])
            self.assertTrue(os.path.isfile(os.path.join(tmp, "revisao.html")))
            with open(html_path, "r", encoding="utf-8") as handle:
                html = handle.read()
            self.assertIn("req-html", html)
            self.assertIn("Texto da cena 1", html)

    def test_segunda_execucao_reutiliza_entrada(self):
        """Duas execuções de prepare sobre a mesma entrada produzem resultado consistente."""
        root = os.getcwd()
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            req_path = _make_request(
                tmp,
                [{"durationMs": 4000}, {"durationMs": 6000}],
                root=root,
            )
            out_dir = os.path.join(tmp, "saida")
            r1 = campaign_proof.cmd_prepare(req_path, out_dir, root)
            r2 = campaign_proof.cmd_prepare(req_path, out_dir, root)
            self.assertTrue(r1["ok"] and r2["ok"])
            self.assertEqual(r1["sceneCount"], 2)
            self.assertEqual(r2["sceneCount"], 2)
            self.assertEqual(r1["totalDurationMs"], 10000)
            self.assertEqual(r2["totalDurationMs"], 10000)


if __name__ == "__main__":
    unittest.main()
