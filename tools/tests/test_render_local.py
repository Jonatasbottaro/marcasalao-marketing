"""Testes do adaptador de render local de prova (tools/render_local.py).

Camadas:
- pura: SRT, narracao, nomes de artefatos e grafo de filtros derivam do pacote;
- ponte: vereditos do nucleo (pacote/associacao/recorte) via render_bridge.mjs;
- real: render dos dois pacotes versionados com FFmpeg/FFprobe, inspecao e hashes;
- falha: pacote invalido, asset ausente/fora da raiz, falha da ferramenta de
  video e falha de promocao preservam a entrega anterior por SHA-256.

Testes reais sao ignorados quando FFmpeg ou o build da platform nao existem;
a matriz de CI da platform cobre o nucleo, e o render real e registrado como
evidencia local separada.
"""

import json
import os
import shutil
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build_video
import make_proof_assets
import render_local
import srt_validate

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
TMP_BASE = os.path.join(WORKTREE, ".workspace", "tmp", "local-render-adapter-v1-tests")
FFMPEG_DIR = os.path.join(MAIN_ROOT, ".workspace", "tools", "ffmpeg")

PKG_MS_REL = ("platform/examples/execution-packages/execution-marca-salao-social-reel-example-"
              "instagram-reels-video-social-reel-beat-plan.execution-package.json")
PKG_MH_REL = ("platform/examples/execution-packages/execution-multitrack-hub-multitrack-social-reel-"
              "example-instagram-reels-video-multitrack-social-reel-beat-plan.execution-package.json")
ASSOC_MS_REL = "tools/render/marca-salao.assets.json"
ASSOC_MH_REL = "tools/render/multitrack-hub.assets.json"

HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe")) or all(
    os.path.isfile(os.path.join(FFMPEG_DIR, name))
    for name in (("ffmpeg.exe", "ffprobe.exe") if os.name == "nt" else ("ffmpeg", "ffprobe"))
)
HAS_BRIDGE = bool(shutil.which("node")) and os.path.isfile(
    os.path.join(WORKTREE, "platform", "dist", "src", "validate-local-render-input.js"))


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, value):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def delivery_hashes(output_dir):
    return {
        name: render_local.sha256_file(os.path.join(output_dir, name))
        for name in sorted(os.listdir(output_dir))
        if os.path.isfile(os.path.join(output_dir, name))
    }


class BuildersTest(unittest.TestCase):
    """Derivacoes puras a partir do pacote versionado."""

    @classmethod
    def setUpClass(cls):
        cls.package = read_json(os.path.join(WORKTREE, PKG_MS_REL))

    def test_srt_timestamp_format(self):
        self.assertEqual(render_local.srt_timestamp(0), "00:00:00,000")
        self.assertEqual(render_local.srt_timestamp(4000), "00:00:04,000")
        self.assertEqual(render_local.srt_timestamp(74500), "00:01:14,500")

    def test_srt_derives_from_package_and_validates(self):
        text = render_local.build_srt(self.package)
        self.assertEqual(srt_validate.validate_srt_text(text, 14.0), [])
        self.assertTrue(text.endswith("\n"))
        self.assertFalse(text.endswith("\n\n"))
        self.assertNotIn("\r", text)
        self.assertEqual(text.count("-->"), 3)
        self.assertIn("Contrato de saida em tres cenas.", text)
        self.assertIn("00:00:04,000 --> 00:00:10,000", text)

    def test_narration_derives_from_package(self):
        text = render_local.build_narration(self.package)
        self.assertIn(self.package["packageId"], text)
        for step in self.package["timeline"]:
            self.assertIn(step["beatId"], text)
            self.assertIn(step["narrationText"], text)
        self.assertTrue(text.endswith("\n"))
        self.assertFalse(text.endswith("\n\n"))

    def test_artifact_names_come_from_expected_artifacts(self):
        names = render_local.artifact_names(self.package)
        self.assertEqual(set(names), {"video", "srt", "narration", "report"})
        self.assertTrue(names["video"].endswith(".mp4"))
        self.assertTrue(names["srt"].endswith(".srt"))
        self.assertTrue(names["narration"].endswith(".txt"))
        self.assertTrue(names["report"].endswith(".json"))

    def test_filter_graph_respects_motion_transitions_and_audio_policy(self):
        graph = render_local.build_filter_graph(self.package, "staging/captions.srt")
        self.assertIn("concat=n=3:v=1:a=0", graph)
        self.assertIn("zoompan=", graph)
        self.assertIn("fade=t=out:st=13.500:d=0.500", graph)
        self.assertTrue(graph.endswith("[vfinal]"))
        self.assertIn("subtitles=", graph)
        cmd = render_local.build_render_command(
            self.package, ["a.png", "b.png", "c.png"], "staging/captions.srt",
            "staging/video.mp4", "veryfast")
        self.assertIn("-an", cmd)
        self.assertNotIn("-c:a", cmd)


@unittest.skipUnless(HAS_BRIDGE, "node ou build da platform ausente")
class BridgeTest(unittest.TestCase):
    """Vereditos do nucleo puro atraves da ponte interna."""

    @classmethod
    def setUpClass(cls):
        os.makedirs(TMP_BASE, exist_ok=True)
        import tempfile
        cls.base = tempfile.mkdtemp(dir=TMP_BASE)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base, ignore_errors=True)

    def verdict(self, package, association):
        package_path = os.path.join(self.base, "package.json")
        association_path = os.path.join(self.base, "assets.json")
        write_json(package_path, package)
        write_json(association_path, association)
        return render_local.run_bridge(WORKTREE, package_path, association_path)

    def test_valid_entry(self):
        package = read_json(os.path.join(WORKTREE, PKG_MS_REL))
        association = read_json(os.path.join(WORKTREE, ASSOC_MS_REL))
        verdict = self.verdict(package, association)
        self.assertTrue(verdict["ok"])
        self.assertEqual(verdict["package"]["packageId"], package["packageId"])

    def test_invalid_package(self):
        package = read_json(os.path.join(WORKTREE, PKG_MS_REL))
        package["timeline"][0]["endMs"] += 1
        association = read_json(os.path.join(WORKTREE, ASSOC_MS_REL))
        verdict = self.verdict(package, association)
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["failureCode"], "PACKAGE_INVALID")

    def test_missing_beat_asset(self):
        package = read_json(os.path.join(WORKTREE, PKG_MS_REL))
        association = read_json(os.path.join(WORKTREE, ASSOC_MS_REL))
        association["assets"] = association["assets"][1:]
        verdict = self.verdict(package, association)
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["failureCode"], "BEAT_ASSET_MISSING")

    def test_absolute_asset_path(self):
        package = read_json(os.path.join(WORKTREE, PKG_MS_REL))
        association = read_json(os.path.join(WORKTREE, ASSOC_MS_REL))
        association["assets"][0]["path"] = os.path.abspath("fora.png")
        verdict = self.verdict(package, association)
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["failureCode"], "ASSET_PATH_INVALID")

    def test_traversal_asset_path(self):
        package = read_json(os.path.join(WORKTREE, PKG_MS_REL))
        association = read_json(os.path.join(WORKTREE, ASSOC_MS_REL))
        association["assets"][0]["path"] = "../fora.png"
        verdict = self.verdict(package, association)
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["failureCode"], "ASSET_PATH_INVALID")

    def test_unsupported_extension(self):
        package = read_json(os.path.join(WORKTREE, PKG_MS_REL))
        association = read_json(os.path.join(WORKTREE, ASSOC_MS_REL))
        association["assets"][0]["path"] = ".workspace/tmp/a.gif"
        verdict = self.verdict(package, association)
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["failureCode"], "ASSET_EXTENSION_UNSUPPORTED")

    def test_unsupported_configuration(self):
        package = read_json(os.path.join(WORKTREE, PKG_MS_REL))
        package["output"]["fps"] = 25
        association = read_json(os.path.join(WORKTREE, ASSOC_MS_REL))
        verdict = self.verdict(package, association)
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["failureCode"], "RENDER_CONFIGURATION_UNSUPPORTED")
        self.assertEqual(verdict["subject"], "output.fps")


@unittest.skipUnless(HAS_FFMPEG and HAS_BRIDGE, "FFmpeg ou build da platform ausente")
class RenderEndToEndTest(unittest.TestCase):
    """Render real, inspecao FFprobe e preservacao transacional da entrega."""

    @classmethod
    def setUpClass(cls):
        if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
            os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")
        os.makedirs(TMP_BASE, exist_ok=True)
        import tempfile
        cls.base = tempfile.mkdtemp(dir=TMP_BASE)
        for package_rel, project in ((PKG_MS_REL, "marca-salao"), (PKG_MH_REL, "multitrack-hub")):
            make_proof_assets.generate_assets(
                os.path.join(WORKTREE, package_rel),
                os.path.join(WORKTREE, ".workspace", "tmp", "local-render-adapter-v1",
                             "assets", project),
                WORKTREE)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base, ignore_errors=True)

    def run_cli(self, package_rel, assoc_rel, output_dir, extra=()):
        return render_local.main([
            "--package", os.path.join(WORKTREE, package_rel),
            "--assets", os.path.join(WORKTREE, assoc_rel),
            "--output-dir", output_dir,
            "--root", WORKTREE,
            *extra,
        ])

    def test_01_marca_salao_14s_no_audio(self):
        output_dir = os.path.join(self.base, "ms")
        code = self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir)
        self.assertEqual(code, 0)
        names = render_local.artifact_names(read_json(os.path.join(WORKTREE, PKG_MS_REL)))
        inspection = build_video.validate_mp4(
            os.path.join(output_dir, names["video"]), 1080, 1920, 30, 14.0)
        self.assertEqual(inspection["videoStreams"], 1)
        self.assertEqual(inspection["audioStreams"], 0)
        self.assertEqual(inspection["codec"], "h264")
        self.assertEqual(inspection["pixFmt"], "yuv420p")
        self.assertEqual(srt_validate.validate_srt_file(
            os.path.join(output_dir, names["srt"]), 14.0), [])
        report = read_json(os.path.join(output_dir, names["report"]))
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["inspection"]["duration"], 14.0)
        for artifact in report["artifacts"]:
            promoted = os.path.join(output_dir, os.path.basename(artifact["path"]))
            self.assertEqual(render_local.sha256_file(promoted), artifact["sha256"])

    def test_02_multitrack_hub_15s_no_audio(self):
        output_dir = os.path.join(self.base, "mh")
        code = self.run_cli(PKG_MH_REL, ASSOC_MH_REL, output_dir)
        self.assertEqual(code, 0)
        names = render_local.artifact_names(read_json(os.path.join(WORKTREE, PKG_MH_REL)))
        inspection = build_video.validate_mp4(
            os.path.join(output_dir, names["video"]), 1080, 1920, 30, 15.0)
        self.assertEqual(inspection["audioStreams"], 0)
        self.assertEqual(inspection["duration"], 15.0)
        self.assertEqual(srt_validate.validate_srt_file(
            os.path.join(output_dir, names["srt"]), 15.0), [])

    def test_03_text_artifacts_deterministic(self):
        first = os.path.join(self.base, "det-a")
        second = os.path.join(self.base, "det-b")
        self.assertEqual(self.run_cli(PKG_MS_REL, ASSOC_MS_REL, first), 0)
        self.assertEqual(self.run_cli(PKG_MS_REL, ASSOC_MS_REL, second), 0)
        names = render_local.artifact_names(read_json(os.path.join(WORKTREE, PKG_MS_REL)))
        for key in ("srt", "narration"):
            with open(os.path.join(first, names[key]), "rb") as handle:
                data_a = handle.read()
            with open(os.path.join(second, names[key]), "rb") as handle:
                data_b = handle.read()
            self.assertEqual(data_a, data_b)

    def test_04_invalid_package_preserves_previous_delivery(self):
        output_dir = os.path.join(self.base, "preserve-invalid")
        self.assertEqual(self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir), 0)
        before = delivery_hashes(output_dir)
        tampered = read_json(os.path.join(WORKTREE, PKG_MS_REL))
        tampered["timeline"][0]["endMs"] += 1
        tampered_path = os.path.join(self.base, "tampered-package.json")
        write_json(tampered_path, tampered)
        code = render_local.main([
            "--package", tampered_path,
            "--assets", os.path.join(WORKTREE, ASSOC_MS_REL),
            "--output-dir", output_dir,
            "--root", WORKTREE,
        ])
        self.assertEqual(code, 3)
        self.assertEqual(delivery_hashes(output_dir), before)

    def test_05_missing_asset_preserves_previous_delivery(self):
        output_dir = os.path.join(self.base, "preserve-missing")
        self.assertEqual(self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir), 0)
        before = delivery_hashes(output_dir)
        association = read_json(os.path.join(WORKTREE, ASSOC_MS_REL))
        association["assets"][0]["path"] = ".workspace/tmp/local-render-adapter-v1/assets/marca-salao/nao-existe.png"
        association_path = os.path.join(self.base, "missing-assets.json")
        write_json(association_path, association)
        code = render_local.main([
            "--package", os.path.join(WORKTREE, PKG_MS_REL),
            "--assets", association_path,
            "--output-dir", output_dir,
            "--root", WORKTREE,
        ])
        self.assertEqual(code, 1)
        self.assertEqual(delivery_hashes(output_dir), before)

    def test_06_asset_outside_root_preserves_previous_delivery(self):
        output_dir = os.path.join(self.base, "preserve-outside")
        self.assertEqual(self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir), 0)
        before = delivery_hashes(output_dir)
        association = read_json(os.path.join(WORKTREE, ASSOC_MS_REL))
        association["assets"][0]["path"] = "../fora-da-raiz.png"
        association_path = os.path.join(self.base, "outside-assets.json")
        write_json(association_path, association)
        code = render_local.main([
            "--package", os.path.join(WORKTREE, PKG_MS_REL),
            "--assets", association_path,
            "--output-dir", output_dir,
            "--root", WORKTREE,
        ])
        self.assertEqual(code, 3)
        self.assertEqual(delivery_hashes(output_dir), before)

    def test_07_unreadable_asset_preserves_previous_delivery(self):
        output_dir = os.path.join(self.base, "preserve-render")
        self.assertEqual(self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir), 0)
        before = delivery_hashes(output_dir)
        asset = os.path.join(WORKTREE, ".workspace", "tmp", "local-render-adapter-v1",
                             "assets", "marca-salao", "opening-hook.png")
        with open(asset, "rb") as handle:
            original = handle.read()
        try:
            with open(asset, "wb") as handle:
                handle.write(b"isto nao e um png")
            code = self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir)
            self.assertEqual(code, 1)
            self.assertEqual(delivery_hashes(output_dir), before)
        finally:
            with open(asset, "wb") as handle:
                handle.write(original)

    def test_07b_video_tool_failure_preserves_previous_delivery(self):
        output_dir = os.path.join(self.base, "preserve-ffmpeg")
        self.assertEqual(self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir), 0)
        before = delivery_hashes(output_dir)
        code = self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir,
                            extra=("--preset", "preset-que-nao-existe"))
        self.assertEqual(code, 1)
        self.assertEqual(delivery_hashes(output_dir), before)

    def test_08_promotion_failure_preserves_previous_delivery(self):
        output_dir = os.path.join(self.base, "preserve-promote")
        self.assertEqual(self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir), 0)
        before = delivery_hashes(output_dir)
        staging = output_dir + ".staging"
        real_replace = os.replace
        promotion_calls = {"count": 0}

        def flaky_replace(src, dst):
            src_text = str(src)
            if src_text.startswith(staging) and ".backup" not in src_text:
                promotion_calls["count"] += 1
                if promotion_calls["count"] == 2:
                    raise OSError("falha simulada de promocao")
            return real_replace(src, dst)

        with mock.patch.object(render_local.os, "replace", side_effect=flaky_replace):
            code = self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir)
        self.assertEqual(code, 1)
        self.assertEqual(delivery_hashes(output_dir), before)
        self.assertTrue(os.path.isdir(staging))

    def test_09_unsupported_configuration_preserves_previous_delivery(self):
        output_dir = os.path.join(self.base, "preserve-config")
        self.assertEqual(self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir), 0)
        before = delivery_hashes(output_dir)
        tampered = read_json(os.path.join(WORKTREE, PKG_MS_REL))
        tampered["output"]["fps"] = 25
        tampered_path = os.path.join(self.base, "fps25-package.json")
        write_json(tampered_path, tampered)
        code = render_local.main([
            "--package", tampered_path,
            "--assets", os.path.join(WORKTREE, ASSOC_MS_REL),
            "--output-dir", output_dir,
            "--root", WORKTREE,
        ])
        self.assertEqual(code, 3)
        self.assertEqual(delivery_hashes(output_dir), before)


if __name__ == "__main__":
    unittest.main()
