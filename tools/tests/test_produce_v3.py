"""Regressao da producao v3 (PILOTO-OPERACIONAL-001-V3).

Cobre o contrato das tres pecas v3 geradas pelo motor comercial:
  - Post 4:5 em 1080x1350 e carrossel de 4 cards 1080x1080.
  - Reel vertical 1080x1920, VIDEO CLEAN (0 faixas de audio, `-an`).
  - Narracao separada, SRT cronometrado e direcao de cenas distintos.
  - Tipografia nao e bitmap: o texto e renderizado e ocupa area real (variancia).
  - Auditoria de claims limpa contra o guardrails do tenant Marca Salao.

Sem capturas autorizadas ou sem FFmpeg, o teste e pulado (SkipTest).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import assemble_v3_delivery
import build_video
import produce_v3
import render_local


def _region_stats(ffmpeg, path, w, x, y, rw, rh):
    p = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", path,
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       capture_output=True)
    data = p.stdout
    total = n = s2 = 0
    for yy in range(y, y + rh):
        row = yy * w
        for xx in range(x, x + rw):
            v = data[row + xx]
            total += v
            n += 1
            s2 += v * v
    mean = total / n
    return mean, (s2 / n - mean * mean) ** 0.5


class ProduceV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        render_local.ensure_video_tools(REPO_ROOT)
        cls.ffmpeg = build_video.get_ffmpeg()
        cls.ffprobe = build_video.get_ffprobe()
        if not cls.ffmpeg or not cls.ffprobe:
            raise unittest.SkipTest("FFmpeg/ffprobe indisponiveis")
        cap = os.path.join(REPO_ROOT, produce_v3.CAPTURES_REL, produce_v3.CAP_MOBILE_DAY)
        if not os.path.isfile(render_local.fs_path(cap)):
            raise unittest.SkipTest("capturas autorizadas ausentes")
        parent = os.path.join(REPO_ROOT, ".workspace", "tmp")
        os.makedirs(render_local.fs_path(parent), exist_ok=True)
        cls.tmp = tempfile.mkdtemp(prefix="v3-test-", dir=parent)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(render_local.fs_path(cls.tmp), ignore_errors=True)

    def _run(self, script, *extra):
        cmd = [sys.executable, os.path.join(TOOLS_DIR, script), "--root", REPO_ROOT, "--json", *extra]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        self.assertEqual(res.returncode, 0, res.stderr[-500:])
        return res.stdout

    def _probe(self, path):
        res = subprocess.run([self.ffprobe, "-v", "error", "-show_entries",
                              "stream=codec_type,width,height", "-of", "json", path],
                             capture_output=True, text=True, timeout=60)
        import json
        return json.loads(res.stdout).get("streams", [])

    def test_post_and_carousel_geometry_and_text(self):
        out = os.path.join(self.tmp, "delivery")
        self._run("produce_v3.py", "--piece", "all", "--outdir", out)
        post = os.path.join(out, "post-45", "01-capa.jpg")
        self.assertTrue(os.path.isfile(render_local.fs_path(post)))
        st = self._probe(post)[0]
        self.assertEqual((st["width"], st["height"]), (1080, 1350))
        # texto no topo deve ter variancia (texto renderizado, nao fundo liso)
        _, std = _region_stats(self.ffmpeg, post, 1080, 0, 70, 1080, 240)
        self.assertGreater(std, 25.0, "post sem texto visivel no topo")
        for name in ("01-capa.jpg", "02-horarios.jpg", "03-atendimentos.jpg", "04-cta.jpg"):
            p = os.path.join(out, "carousel", name)
            self.assertTrue(os.path.isfile(render_local.fs_path(p)), name)
            st = self._probe(p)[0]
            self.assertEqual((st["width"], st["height"]), (1080, 1080), name)
            _, std = _region_stats(self.ffmpeg, p, 1080, 0, 70, 1080, 240)
            self.assertGreater(std, 20.0, f"{name} sem texto visivel")

    def test_reel_clean_and_narration_assets(self):
        out = os.path.join(self.tmp, "reel-out")
        leg = os.path.join(self.tmp, "leg")
        self._run("produce_v3_reel.py", "--outdir", out, "--legendas-dir", leg)
        reel = os.path.join(out, "reel-instagram-9x16.mp4")
        streams = self._probe(reel)
        video = [s for s in streams if s["codec_type"] == "video"]
        audio = [s for s in streams if s["codec_type"] == "audio"]
        self.assertEqual(len(video), 1)
        self.assertEqual((video[0]["width"], video[0]["height"]), (1080, 1920))
        self.assertEqual(audio, [], "reel deve ser VIDEO CLEAN (sem audio)")
        for rel in ("narracao-reel.txt", "legendas.srt"):
            self.assertTrue(os.path.isfile(render_local.fs_path(os.path.join(leg, rel))), rel)
        self.assertTrue(os.path.isfile(render_local.fs_path(os.path.join(out, "direcao-de-cenas.md"))))
        # narracao e direcao sao arquivos distintos e sem verbos de direcao na narracao
        with open(render_local.fs_path(os.path.join(leg, "narracao-reel.txt")), encoding="utf-8") as fh:
            nar = fh.read().lower()
        for verbe in ("mostre", "apresente", "destaque", "exiba"):
            self.assertNotIn(verbe, nar, f"narracao contem verbo de direcao: {verbe}")

    def test_claims_clean_against_guardrails(self):
        out = os.path.join(self.tmp, "reel-out2")
        leg = os.path.join(self.tmp, "leg2")
        self._run("produce_v3_reel.py", "--outdir", out, "--legendas-dir", leg)
        texts = [("on-image", t) for t in assemble_v3_delivery.ON_IMAGE_TEXTS]
        for p in (os.path.join(leg, "narracao-reel.txt"), os.path.join(leg, "legendas.srt")):
            with open(render_local.fs_path(p), encoding="utf-8") as fh:
                texts.append((os.path.basename(p), fh.read()))
        audit = assemble_v3_delivery.audit_claims(REPO_ROOT, texts)
        self.assertTrue(audit["ok"], f"claims proibidos: {audit['hits']}")


if __name__ == "__main__":
    unittest.main()
