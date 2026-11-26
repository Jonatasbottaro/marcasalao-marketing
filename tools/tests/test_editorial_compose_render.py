"""Testes reais do compositor editorial (tools/editorial_compose.py).

Faixa render: usa FFmpeg/FFprobe de verdade sobre a fixture ficticia
"Marca Exemplo" (tools/tests/fixtures/editorial/), nunca sobre midia de cliente.

  H  reprodutibilidade: a mesma cena composta duas vezes gera bytes identicos;
  J  exportacao: h264, yuv420p, sem audio, geometria e duracao corretos;
  G  cenas distintas produzem midias com hashes diferentes;
  prova de reutilizacao: campanha ficticia completa compila e compoe apenas
  por configuracao, com areas seguras respeitadas.

Ignorados quando FFmpeg/FFprobe nao existem (mesma convencao de
test_render_local.py). Sandbox em <RAIZ>/.workspace/tmp/, fora do Git.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import editorial_compose  # noqa: E402
import render_local  # noqa: E402

WORKTREE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _main_root(start):
    root = start
    while not os.path.isdir(os.path.join(root, ".git")):
        parent = os.path.dirname(root)
        if parent == root:
            return start
        root = parent
    return root


MAIN_ROOT = _main_root(WORKTREE)
FFMPEG_DIR = os.path.join(MAIN_ROOT, ".workspace", "tools", "ffmpeg")
FIXTURE = os.path.join(WORKTREE, "tools", "tests", "fixtures", "editorial",
                       "marca-exemplo.editorial.json")
SANDBOX = os.path.join(WORKTREE, ".workspace", "tmp", "editorial-compose-render")

HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe")) or all(
    os.path.isfile(os.path.join(FFMPEG_DIR, name))
    for name in (("ffmpeg.exe", "ffprobe.exe") if os.name == "nt" else ("ffmpeg", "ffprobe"))
)


def sha(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


@unittest.skipUnless(HAS_FFMPEG, "FFmpeg/FFprobe ausentes")
class TestEditorialComposeRender(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
            os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")
        os.makedirs(SANDBOX, exist_ok=True)

    def test_reprodutibilidade_bytes_identicos(self):
        out_a = os.path.join(SANDBOX, "rep-a")
        out_b = os.path.join(SANDBOX, "rep-b")
        editorial_compose.compose_campaign(FIXTURE, WORKTREE, out_a, ["fx-c1-prova"])
        editorial_compose.compose_campaign(FIXTURE, WORKTREE, out_b, ["fx-c1-prova"])
        self.assertEqual(sha(os.path.join(out_a, "fx-c1-prova.mp4")),
                         sha(os.path.join(out_b, "fx-c1-prova.mp4")))

    def test_exportacao_video_sem_audio(self):
        out = os.path.join(SANDBOX, "export")
        editorial_compose.compose_campaign(FIXTURE, WORKTREE, out, ["fx-c1-prova"])
        path = os.path.join(out, "fx-c1-prova.mp4")
        probe = subprocess.run(
            [shutil.which("ffprobe"), "-v", "error", "-show_streams", "-show_format",
             "-of", "json", path], capture_output=True, text=True, check=True)
        data = json.loads(probe.stdout)
        video = [s for s in data["streams"] if s["codec_type"] == "video"]
        audio = [s for s in data["streams"] if s["codec_type"] == "audio"]
        self.assertEqual(len(video), 1)
        self.assertFalse(audio)
        self.assertEqual(video[0]["codec_name"], "h264")
        self.assertEqual(video[0]["pix_fmt"], "yuv420p")
        self.assertEqual((video[0]["width"], video[0]["height"]), (360, 640))
        self.assertAlmostEqual(float(data["format"]["duration"]), 2.0, delta=0.05)

    def test_campanha_ficticia_completa(self):
        out = os.path.join(SANDBOX, "campanha")
        report = editorial_compose.compose_campaign(FIXTURE, WORKTREE, out)
        self.assertEqual(len(report["scenes"]), 3)
        for entry in report["safeAreas"]:
            self.assertFalse(entry["violations"])
        hashes = {r["sceneId"]: r["sha256"] for r in report["scenes"]}
        self.assertNotEqual(hashes["fx-c1-prova"], hashes["fx-c2-status"])
        self.assertTrue(os.path.isfile(os.path.join(out, "fx-c3-endcard.mp4")))
        self.assertEqual(report["captionBand"]["color"], "primary")
        with open(os.path.join(out, "composition-report.json"), encoding="utf-8") as handle:
            persisted = json.load(handle)
        self.assertEqual(persisted["clientId"], "marca-exemplo")


if __name__ == "__main__":
    unittest.main()