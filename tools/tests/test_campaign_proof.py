"""Testes direcionados para tools/campaign_proof.py.

Cobrem: preparação reproduzível, pedido inválido, referência de mídia
ausente, duração calculada a partir das cenas, diagnóstico de ferramenta
ausente, relatório com render concluído e pendente, preservação de
entrega anterior em tentativa que falha, e textos do pedido no HTML.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import campaign_proof


def _make_request(tmp: str, scenes: list[dict], request_id: str = "req-teste") -> str:
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
                "path": f"assets/{i}.png",
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


def test_preparo_reproduzivel_com_midias_presentes():
    """Preparação gera PNGs sintéticos e relatório com cenas e duração."""
    with tempfile.TemporaryDirectory() as tmp:
        req_path = _make_request(
            tmp,
            [
                {"durationMs": 4000, "narrativeFunction": "hook"},
                {"durationMs": 6000, "narrativeFunction": "demonstration"},
                {"durationMs": 20000, "narrativeFunction": "cta"},
            ],
        )
        out_dir = os.path.join(tmp, "saida")
        result = campaign_proof.cmd_prepare(req_path, out_dir, tmp)
        assert result["ok"] is True, result
        assert result["sceneCount"] == 3
        assert result["totalDurationMs"] == 30000
        assert len(result["mediaPrepared"]) == 3
        # arquivos PNG existem no disco
        for item in result["mediaPrepared"]:
            assert os.path.isfile(os.path.join(tmp, item["generatedAsset"]))


def test_pedido_invalido_rejeitado():
    """Pedido com schemaVersion errado é rejeitado com código estável."""
    with tempfile.TemporaryDirectory() as tmp:
        req_path = os.path.join(tmp, "ruim.json")
        with open(req_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump({"schemaVersion": 99, "id": "x", "project": "p", "title": "t", "profiles": [], "media": [], "scenes": []}, handle)
        result = campaign_proof.cmd_verify(req_path, tmp)
        assert result["ok"] is False
        assert any(e["code"] == "SCHEMA_VERSION_UNSUPPORTED" for e in result["errors"])


def test_referencia_de_media_ausente():
    """Prepare gera a mídia sintética; após a preparação o arquivo existe."""
    with tempfile.TemporaryDirectory() as tmp:
        req_path = _make_request(
            tmp,
            [{"durationMs": 4000, "mediaId": "m-0"}],
        )
        out_dir = os.path.join(tmp, "saida")
        result = campaign_proof.cmd_prepare(req_path, out_dir, tmp)
        assert result["ok"] is True, result
        # o arquivo sintético foi gerado no disco
        assert os.path.isfile(os.path.join(tmp, result["mediaPrepared"][0]["generatedAsset"]))


def test_duracao_calculada_a_partir_das_cenas():
    """Duração total é soma das durações das cenas."""
    with tempfile.TemporaryDirectory() as tmp:
        req_path = _make_request(
            tmp,
            [{"durationMs": 4000}, {"durationMs": 6000}, {"durationMs": 20000}],
        )
        result = campaign_proof.cmd_verify(req_path, tmp)
        assert result["totalDurationMs"] == 30000
        assert result["totalDurationSeconds"] == 30.0
        assert result["sceneCount"] == 3


def test_diagnostico_ferramenta_ausente():
    """Render sem ffmpeg devolve relatório de pendência, não exceção."""
    # ffmpeg não está instalado nesta estação; o comando render deve
    # reportar pendência de ferramenta em vez de travar.
    with tempfile.TemporaryDirectory() as tmp:
        req_path = _make_request(
            tmp,
            [{"durationMs": 4000}],
        )
        result = campaign_proof.cmd_render(req_path, "instagram-reels-video", os.path.join(tmp, "entrega"), tmp)
        assert result["ffmpegAvailable"] is False
        assert result["status"] == "pendente_ferramenta"
        assert "ffmpeg/ffprobe" in result["error"]
        assert "comandoRetomada" in result


def test_relatorio_render_concluido_e_pendente():
    """Quando não há ffmpeg, o relatório fica pendente (não concluído)."""
    with tempfile.TemporaryDirectory() as tmp:
        req_path = _make_request(
            tmp,
            [{"durationMs": 4000}],
        )
        result = campaign_proof.cmd_render(req_path, "instagram-reels-video", os.path.join(tmp, "entrega"), tmp)
        assert result["ok"] is False
        assert result["status"] == "pendente_ferramenta"


def test_textos_do_pedido_no_html():
    """A página de revisão exibe os textos do pedido."""
    with tempfile.TemporaryDirectory() as tmp:
        req_path = _make_request(
            tmp,
            [{"durationMs": 4000, "caption": "Texto da cena 1", "narrativeFunction": "hook"}],
            request_id="req-html",
        )
        html_path = os.path.join(tmp, "revisao.html")
        result = campaign_proof.cmd_review(req_path, html_path, tmp)
        assert result["ok"] is True
        assert os.path.isfile(os.path.join(tmp, "revisao.html"))
        with open(html_path, "r", encoding="utf-8") as handle:
            html = handle.read()
        assert "req-html" in html
        assert "Texto da cena 1" in html
        assert "Texto da cena 1" in html


def test_segunda_execucao_reutiliza_entrada():
    """Duas execuções de prepare sobre a mesma entrada produzem resultado consistente."""
    with tempfile.TemporaryDirectory() as tmp:
        req_path = _make_request(
            tmp,
            [{"durationMs": 4000}, {"durationMs": 6000}],
        )
        out_dir = os.path.join(tmp, "saida")
        r1 = campaign_proof.cmd_prepare(req_path, out_dir, tmp)
        r2 = campaign_proof.cmd_prepare(req_path, out_dir, tmp)
        assert r1["ok"] is True and r2["ok"] is True
        assert r1["sceneCount"] == r2["sceneCount"] == 2
        assert r1["totalDurationMs"] == r2["totalDurationMs"] == 10000


if __name__ == "__main__":
    import traceback

    tests = [
        test_preparo_reproduzivel_com_midias_presentes,
        test_pedido_invalido_rejeitado,
        test_referencia_de_media_ausente,
        test_duracao_calculada_a_partir_das_cenas,
        test_diagnostico_ferramenta_ausente,
        test_relatorio_render_concluido_e_pendente,
        test_textos_do_pedido_no_html,
        test_segunda_execucao_reutiliza_entrada,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"OK   {test.__name__}")
            passed += 1
        except Exception as exc:
            print(f"FALHA {test.__name__}: {exc}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} aprovados, {failed} falhos de {len(tests)}")
    sys.exit(1 if failed else 0)
