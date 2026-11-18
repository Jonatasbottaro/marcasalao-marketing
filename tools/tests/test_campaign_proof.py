"""Testes automatizados (unittest) para tools/campaign_proof.py."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import struct
import subprocess
import sys
import unittest
import uuid
import zlib
from unittest.mock import patch

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import campaign_proof
import carousel_layout
import render_local


def _test_dir(prefix: str) -> str:
    base = os.path.join(REPO_ROOT, ".workspace", "tmp", "tcp", f"{prefix[:4]}-{uuid.uuid4().hex[:6]}")
    os.makedirs(render_local.fs_path(base), exist_ok=True)
    return base


def _write_plain_png(path: str, width: int = 8, height: int = 8, color: tuple[int, int, int] = (20, 120, 60)) -> None:
    """Escreve PNG valido SEM marcador sintetico da ferramenta (simula captura do operador)."""
    raw = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = (
        campaign_proof.PNG_SIGNATURE
        + carousel_layout._png_chunk(b"IHDR", ihdr)
        + carousel_layout._png_chunk(b"IDAT", zlib.compress(raw, 6))
        + carousel_layout._png_chunk(b"IEND", b"")
    )
    os.makedirs(os.path.dirname(render_local.fs_path(path)), exist_ok=True)
    with open(render_local.fs_path(path), "wb") as handle:
        handle.write(png)


def _write_request(
    root: str,
    rel_dir: str,
    scenes: list[dict],
    request_id: str = "req-teste",
    project_rel: str = "platform/examples/projects/marca-salao-social.project.json",
    title: str = "Pedido de teste",
) -> str:
    media = []
    req_scenes = []
    seen_media: set[str] = set()
    for i, s in enumerate(scenes):
        mid = s.get("mediaId", f"m-{i}")
        if mid not in seen_media:
            seen_media.add(mid)
            media.append({
                "id": mid,
                "path": f"{rel_dir}/assets/{mid}.png",
                "type": "image",
                "origin": "synthetic-demo",
                "license": "owned-synthetic",
            })
        req_scenes.append({
            "id": s.get("id", f"cena-{i}"),
            "durationMs": s["durationMs"],
            "mediaId": mid,
            "caption": s.get("caption", f"Legenda cena {i}"),
            "narration": s.get("narration", f"Narracao cena {i} com texto util."),
            "title": s.get("title", f"Titulo cena {i}"),
            "narrativeFunction": s.get("narrativeFunction", "demonstration"),
            "motionIntent": s.get("motionIntent", "none"),
        })
    request = {
        "schemaVersion": 1,
        "id": request_id,
        "project": project_rel,
        "title": title,
        "locale": "pt-BR",
        "profiles": ["instagram-reels-video"],
        "visualStyle": {
            "schemaVersion": 1,
            "id": "marca-salao-editorial",
            "title": {
                "textColor": "#FFFFFF",
                "outlineColor": "#000000",
                "fontSize": 44,
                "marginTop": 170,
                "marginHorizontal": 70,
            },
        },
        "media": media,
        "scenes": req_scenes,
    }
    req_rel = f"{rel_dir}/{request_id}.video-request.json"
    req_abs = os.path.join(root, req_rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(render_local.fs_path(req_abs)), exist_ok=True)
    with open(render_local.fs_path(req_abs), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(request, handle, ensure_ascii=False, indent=2)
    return req_rel


def _copy_project_manifest(dest_root: str) -> str:
    src = os.path.join(REPO_ROOT, "platform", "examples", "projects", "marca-salao-social.project.json")
    rel = "platform/examples/projects/marca-salao-social.project.json"
    dst = os.path.join(dest_root, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(render_local.fs_path(dst)), exist_ok=True)
    shutil.copy2(render_local.fs_path(src), render_local.fs_path(dst))
    return rel


class CampaignProofTest(unittest.TestCase):
    def setUp(self) -> None:
        self.work_dirs: list[str] = []

    def tearDown(self) -> None:
        for d in self.work_dirs:
            shutil.rmtree(render_local.fs_path(d), ignore_errors=True)

    def _new_dir(self, prefix: str) -> str:
        d = _test_dir(prefix)
        self.work_dirs.append(d)
        return d

    def test_prepare_generates_at_contract_paths_and_preserves_operator_media(self) -> None:
        """Prepare gera PNG marcado em media[].path e preserva captura real mesmo com origin synthetic-demo."""
        ws = self._new_dir("prep")
        rel_ws = render_local.rel(REPO_ROOT, ws)
        req_rel = _write_request(
            REPO_ROOT,
            rel_ws,
            [
                {"durationMs": 4000, "narrativeFunction": "hook", "mediaId": "m-operador"},
                {"durationMs": 4000, "narrativeFunction": "cta", "mediaId": "m-sintetico"},
            ],
            request_id="req-prep-op",
        )
        op_abs = os.path.join(ws, "assets", "m-operador.png")
        _write_plain_png(op_abs, width=16, height=16, color=(12, 34, 56))
        op_sha_before = render_local.sha256_file(op_abs)

        res = campaign_proof.cmd_prepare(req_rel, output_dir=f"{rel_ws}/prep-out", root=REPO_ROOT)
        self.assertTrue(res["ok"], res)
        self.assertEqual(len(res["mediaPrepared"]), 2)
        self.assertEqual(render_local.sha256_file(op_abs), op_sha_before)
        self.assertIn(f"{rel_ws}/assets/m-operador.png", res["operatorMedia"])
        self.assertIn(f"{rel_ws}/assets/m-sintetico.png", res["syntheticMedia"])
        synth_abs = os.path.join(ws, "assets", "m-sintetico.png")
        self.assertTrue(campaign_proof._is_synthetic_proof_file(synth_abs))
        self.assertFalse(campaign_proof._is_synthetic_proof_file(op_abs))

    def test_verify_not_ready_when_project_or_media_missing_and_fractional_duration(self) -> None:
        """Verify nunca retorna ready=True sem ProjectManifest ou sem arquivo fisico; duracao mantem decimais."""
        iso = self._new_dir("verify-iso")
        req_rel = _write_request(
            iso,
            "ped",
            [
                {"durationMs": 4500, "narrativeFunction": "hook"},
                {"durationMs": 3250, "narrativeFunction": "cta"},
            ],
            request_id="req-frac",
        )
        res_missing = campaign_proof.cmd_verify(req_rel, root=iso)
        self.assertFalse(res_missing["ok"])
        self.assertFalse(res_missing["ready"])
        self.assertFalse(res_missing["projectManifestValid"])
        self.assertFalse(res_missing["mediaReady"])
        self.assertEqual(res_missing["totalDurationMs"], 7750)
        self.assertEqual(res_missing["totalDurationSeconds"], 7.75)

        # Agora com ProjectManifest no subdiretorio isolado, mas sem media preparada e sem platform/dist
        _copy_project_manifest(iso)
        res_no_media = campaign_proof.cmd_verify(req_rel, root=iso)
        self.assertFalse(res_no_media["ok"])
        self.assertFalse(res_no_media["ready"])
        self.assertTrue(res_no_media["projectManifestValid"])
        self.assertFalse(res_no_media["mediaReady"])

    def test_verify_rejects_invalid_schema_version_with_exit_3(self) -> None:
        """Pedido invalido retorna contractInvalid=True e CLI sai com codigo 3."""
        iso = self._new_dir("bad")
        bad_path = os.path.join(iso, "ruim.video-request.json")
        with open(bad_path, "w", encoding="utf-8") as handle:
            json.dump({"schemaVersion": 99, "id": "x", "project": "p", "title": "t", "profiles": [], "media": [], "scenes": []}, handle)
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            exit_code = campaign_proof.main(["verify", "ruim.video-request.json", "--root", iso, "--json"])
        self.assertEqual(exit_code, 3)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["contractInvalid"])

    def test_render_missing_ffmpeg_mocked_returns_pending(self) -> None:
        """Render com ffmpeg ausente (mockado em render_local) retorna pendente_ferramenta."""
        ws = self._new_dir("noff")
        rel_ws = render_local.rel(REPO_ROOT, ws)
        req_rel = _write_request(REPO_ROOT, rel_ws, [{"durationMs": 4000, "narrativeFunction": "hook"}], request_id="req-noff")
        with patch("render_local.shutil.which", return_value=None), patch.object(
            campaign_proof, "_ensure_video_tools_for_root", return_value=(False, "ffmpeg/ffprobe ausentes (simulado)")
        ):
            res = campaign_proof.cmd_render(req_rel, "instagram-reels-video", f"{rel_ws}/out", root=REPO_ROOT)
        self.assertFalse(res["ok"])
        self.assertFalse(res["ffmpegAvailable"])
        self.assertEqual(res["status"], "pendente_ferramenta")
        self.assertIn("comandoRetomada", res)

    def test_render_and_failure_preserves_last_valid_delivery_and_portable_review_html(self) -> None:
        """Render real gera MP4/SRT/TXT, tentativa falha preserva entrega anterior e HTML escapado funciona movido."""
        has_tools, msg = campaign_proof._ensure_video_tools_for_root(REPO_ROOT)
        platform_ok = os.path.isfile(os.path.join(REPO_ROOT, "platform", "dist", "src", "compile-video-request.js"))
        if not has_tools or not platform_ok:
            reason = msg or "platform/dist ausente"
            if os.environ.get("REQUIRE_RENDER") == "1":
                self.fail(f"REQUIRE_RENDER=1 ativo, mas ambiente incompleto: {reason}")
            self.skipTest(f"Pre-requisitos de render ausentes: {reason}")

        ws = self._new_dir("real-render")
        rel_ws = render_local.rel(REPO_ROOT, ws)
        req_rel = _write_request(
            REPO_ROOT,
            rel_ws,
            [
                {"durationMs": 4000, "narrativeFunction": "hook", "caption": 'Gancho <script>alert("xss")</script>'},
                {"durationMs": 4000, "narrativeFunction": "cta", "caption": "Final seguro"},
            ],
            request_id="req-real-e2e",
            title='Titulo "Especial" & <Teste>',
        )
        out_rel = f"{rel_ws}/entrega"

        prep = campaign_proof.cmd_prepare(req_rel, output_dir=out_rel, root=REPO_ROOT)
        self.assertTrue(prep["ok"], prep)
        ver = campaign_proof.cmd_verify(req_rel, root=REPO_ROOT)
        self.assertTrue(ver["ready"], ver)

        ren1 = campaign_proof.cmd_render(req_rel, "instagram-reels-video", out_rel, root=REPO_ROOT)
        self.assertTrue(ren1["ok"], ren1)
        self.assertEqual(ren1["ffprobe"]["audioStreams"], 0)
        mp4_abs = render_local.fs_path(os.path.join(REPO_ROOT, ren1["mp4Path"]))
        srt_abs = render_local.fs_path(os.path.join(REPO_ROOT, ren1["srtPath"]))
        narr_abs = render_local.fs_path(os.path.join(REPO_ROOT, ren1["narrationPath"]))
        self.assertTrue(os.path.isfile(mp4_abs), mp4_abs)
        self.assertTrue(os.path.isfile(srt_abs), srt_abs)
        self.assertTrue(os.path.isfile(narr_abs), narr_abs)
        mp4_sha_1 = render_local.sha256_file(mp4_abs)

        # Simular falha na segunda tentativa (produce_video sai com erro em stderr e stdout vazio)
        real_run = subprocess.run
        fake_fail = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Erro simulado de falha no pipeline")

        def fail_only_produce(cmd, *args, **kwargs):
            if any("produce_video.py" in str(part) for part in cmd):
                return fake_fail
            return real_run(cmd, *args, **kwargs)

        with patch("campaign_proof.subprocess.run", side_effect=fail_only_produce):
            ren2 = campaign_proof.cmd_render(req_rel, "instagram-reels-video", out_rel, root=REPO_ROOT)
        self.assertFalse(ren2["ok"])
        self.assertEqual(ren2["status"], "parcial_ou_falhou")
        self.assertIn("preservedLastValidDelivery", ren2)
        self.assertTrue(os.path.isfile(mp4_abs))
        self.assertEqual(render_local.sha256_file(mp4_abs), mp4_sha_1)

        # Revisao HTML escapada + links relativos portaveis ao mover pasta
        rev_rel = f"{out_rel}/revisao.html"
        rev = campaign_proof.cmd_review(req_rel, output_html=rev_rel, root=REPO_ROOT, delivery_dir=out_rel)
        self.assertTrue(rev["ok"], rev)
        rev_abs = render_local.fs_path(os.path.join(REPO_ROOT, rev["htmlPath"]))
        with open(rev_abs, "r", encoding="utf-8") as handle:
            html_content = handle.read()
        self.assertNotIn('<script>alert("xss")</script>', html_content)
        self.assertIn("&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;", html_content)
        self.assertIn("concluido", html_content)
        self.assertIn("<video controls", html_content)

        moved_dir = os.path.join(ws, "movida")
        shutil.copytree(
            render_local.fs_path(os.path.join(ws, "entrega"), force=True),
            render_local.fs_path(moved_dir, force=True),
            copy_function=lambda s, d: shutil.copy2(render_local.fs_path(s, force=True), render_local.fs_path(d, force=True)),
        )
        self.assertTrue(os.path.isfile(render_local.fs_path(os.path.join(moved_dir, "revisao.html"))))
        self.assertTrue(os.path.isdir(render_local.fs_path(os.path.join(moved_dir, "assets"))))
        for asset_name in os.listdir(render_local.fs_path(os.path.join(moved_dir, "assets"))):
            self.assertIn(f"assets/{asset_name}", html_content)

        # CLI end-to-end subcomando `run`
        run_out_rel = f"{rel_ws}/run-cli"
        with contextlib.redirect_stdout(io.StringIO()) as run_buf:
            cli_rc = campaign_proof.main(["run", req_rel, "--output-dir", run_out_rel, "--root", REPO_ROOT, "--json"])
        self.assertEqual(cli_rc, 0)
        run_payload = json.loads(run_buf.getvalue())
        self.assertTrue(run_payload["ok"])
        self.assertTrue(os.path.isfile(render_local.fs_path(os.path.join(ws, "run-cli", "revisao-req-real-e2e.html"))))
        self.assertTrue(os.path.isfile(render_local.fs_path(os.path.join(ws, "run-cli", "proof-summary.json"))))


if __name__ == "__main__":
    unittest.main()
