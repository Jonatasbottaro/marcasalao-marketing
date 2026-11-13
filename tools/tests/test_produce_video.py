"""Testes da producao de video por entrada unica (tools/produce_video.py).

Camadas:
- ponte --video-request: compila o pedido em documentos por perfil (puro, sem FFmpeg);
- cadastro de midia: AssetManifest por material com origem/licenca preservadas;
- previa (--plan-only): sem FFmpeg, sem assets e sem gravacao;
- exportacao real: tres destinos a partir de um pedido, inspecao FFprobe, SRT/TXT,
  hashes, reexportacao de um perfil e reutilizacao de midia;
- falha e recuperacao: perfil fora da allowlist, midia ausente/adulterada, falha
  isolada de perfil e preservacao da entrega anterior.
"""

import json
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import render_local

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
TMP_BASE = os.path.join(WORKTREE, ".workspace", "tmp", "t_produce")
FFMPEG_DIR = os.path.join(MAIN_ROOT, ".workspace", "tools", "ffmpeg")

HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe")) or all(
    os.path.isfile(os.path.join(FFMPEG_DIR, name))
    for name in (("ffmpeg.exe", "ffprobe.exe") if os.name == "nt" else ("ffmpeg", "ffprobe"))
)
HAS_BRIDGE = bool(shutil.which("node")) and os.path.isfile(
    os.path.join(WORKTREE, "platform", "dist", "src", "compile-video-request.js"))
REQUIRE_RENDER = os.environ.get("REQUIRE_RENDER") == "1"

PROJECT_MS_REL = "platform/examples/projects/marca-salao-social.project.json"


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def demo_request(media_dir_rel):
    return {
        "schemaVersion": 1,
        "id": "pedido-teste",
        "project": PROJECT_MS_REL,
        "title": "Video de teste",
        "profiles": ["instagram-reels-video", "facebook-reels-video", "youtube-shorts"],
        "visualStyle": {
            "schemaVersion": 1, "id": "estilo-teste",
            "title": {"textColor": "#FFFFFF", "outlineColor": "#000000", "fontSize": 42, "marginTop": 160, "marginHorizontal": 60},
        },
        "media": [
            {"id": "tela-01", "path": f"{media_dir_rel}/tela-01.png", "type": "image", "origin": "synthetic", "license": "owned-synthetic"},
            {"id": "tela-02", "path": f"{media_dir_rel}/tela-02.png", "type": "image", "origin": "synthetic"},
        ],
        "scenes": [
            {"id": "abertura", "durationMs": 4000, "mediaId": "tela-01", "caption": "Legenda abertura", "narration": "Narracao abertura", "title": "Titulo abertura", "narrativeFunction": "hook", "motionIntent": "none"},
            {"id": "meio", "durationMs": 6000, "mediaId": "tela-02", "caption": "Legenda meio", "narration": "Narracao meio", "motionIntent": "slow-zoom"},
            {"id": "fecho", "durationMs": 4000, "mediaId": "tela-01", "caption": "Legenda fecho", "narration": "Narracao fecho", "narrativeFunction": "cta"},
        ],
    }


def run_bridge_request(request_path, profile=None):
    cmd = [shutil.which("node"), os.path.join(WORKTREE, "tools", "render_bridge.mjs"),
           "--video-request", request_path, "--root", MAIN_ROOT]
    if profile:
        cmd.extend(["--profile", profile])
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return res


class BridgeVideoRequestTest(unittest.TestCase):
    """A ponte compila o pedido em documentos por perfil sem FFmpeg."""

    @classmethod
    def setUpClass(cls):
        if not HAS_BRIDGE:
            raise unittest.SkipTest("ponte TypeScript indisponivel")
        cls.dir = os.path.join(TMP_BASE, "bridge")
        os.makedirs(cls.dir, exist_ok=True)
        cls.request_path = os.path.join(cls.dir, "pedido.json")
        write_json(cls.request_path, demo_request(".workspace/tmp/t_produce/bridge/assets"))

    def test_compila_tres_perfis(self):
        res = run_bridge_request(self.request_path)
        self.assertEqual(res.returncode, 0, res.stderr)
        verdict = json.loads(res.stdout)
        self.assertTrue(verdict["ok"], verdict)
        self.assertEqual(verdict["requestId"], "pedido-teste")
        self.assertEqual(len(verdict["profiles"]), 3)
        for profile in verdict["profiles"]:
            self.assertEqual(profile["status"], "compiled", profile.get("failureCode"))
            self.assertEqual(profile["composition"]["format"]["width"], 1080)
            self.assertEqual(profile["composition"]["format"]["height"], 1920)
            self.assertEqual(profile["composition"]["format"]["fps"], 30)
            self.assertEqual(profile["package"]["output"]["durationMs"], 14000)
            self.assertTrue(profile["plan"]["supported"])

    def test_profile_filter(self):
        res = run_bridge_request(self.request_path, profile="youtube-shorts")
        self.assertEqual(res.returncode, 0, res.stderr)
        verdict = json.loads(res.stdout)
        self.assertEqual(len(verdict["profiles"]), 1)
        self.assertEqual(verdict["profiles"][0]["profileId"], "youtube-shorts")

    def test_pedido_invalido_saida_3(self):
        bad_path = os.path.join(self.dir, "invalido.json")
        write_json(bad_path, {**demo_request(".workspace/tmp/x"), "id": "PedidoInvalido"})
        res = run_bridge_request(bad_path)
        self.assertEqual(res.returncode, 3)
        verdict = json.loads(res.stdout)
        self.assertFalse(verdict["ok"])


if __name__ == "__main__":
    unittest.main()