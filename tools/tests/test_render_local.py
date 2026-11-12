"""Testes do adaptador de render local de prova (tools/render_local.py).

Camadas:
- pura: SRT, narracao, nomes de artefatos e grafo de filtros derivam do pacote;
- ponte: vereditos do nucleo (pacote/associacao/recorte) via render_bridge.mjs;
- real: render dos dois pacotes versionados com FFmpeg/FFprobe, inspecao e hashes;
- falha: pacote invalido, asset ausente/fora da raiz, falha da ferramenta de
  video e falha de promocao preservam a entrega anterior por SHA-256.

Testes reais sao ignorados quando FFmpeg ou o build da platform nao existem;
a matriz de CI da platform cobre o nucleo, e o workflow dedicado de render
exige REQUIRE_RENDER=1: nesse modo, ferramenta ou ponte ausente viram erro,
nunca skip, e os testes obrigatorios de render nao podem ser pulados.
"""

import json
import os
import shutil
import subprocess
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
REQUIRE_RENDER = os.environ.get("REQUIRE_RENDER") == "1"


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, value):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def delivery_hashes(output_dir):
    # O lock de promocao e arquivo de controle, nao artefato da entrega.
    return {
        name: render_local.sha256_file(os.path.join(output_dir, name))
        for name in sorted(os.listdir(output_dir))
        if os.path.isfile(os.path.join(output_dir, name))
        and name != render_local.PROMOTION_LOCK_NAME
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
        self.assertIn("scale=w='1080*(1+0.10*t/6.000)'", graph)
        self.assertIn("eval=frame", graph)
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
        if REQUIRE_RENDER and not HAS_BRIDGE:
            raise RuntimeError("REQUIRE_RENDER: ponte indisponivel; teste obrigatorio nao pode ser pulado")
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
        if REQUIRE_RENDER and not (HAS_FFMPEG and HAS_BRIDGE):
            raise RuntimeError("REQUIRE_RENDER: FFmpeg ou ponte ausente; teste obrigatorio nao pode ser pulado")
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

    def run_cli(self, package_rel, assoc_rel, output_dir, extra=(), staging=None):
        argv = [
            "--package", os.path.join(WORKTREE, package_rel),
            "--assets", os.path.join(WORKTREE, assoc_rel),
            "--output-dir", output_dir,
            "--root", WORKTREE,
            *extra,
        ]
        if staging is not None:
            argv += ["--staging", staging]
        return render_local.main(argv)

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

    def test_01b_report_points_to_final_promoted_files(self):
        output_dir = os.path.join(self.base, "report-final")
        self.assertEqual(self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir), 0)
        names = render_local.artifact_names(read_json(os.path.join(WORKTREE, PKG_MS_REL)))
        report = read_json(os.path.join(output_dir, names["report"]))
        self.assertEqual(len(report["artifacts"]), 3)
        for artifact in report["artifacts"]:
            expected_rel = os.path.relpath(
                os.path.join(output_dir, os.path.basename(artifact["path"])),
                WORKTREE).replace(os.sep, "/")
            self.assertEqual(artifact["path"], expected_rel)
            self.assertNotIn(".staging", artifact["path"])
            self.assertNotIn("local-render-staging-", artifact["path"])
            pointed = os.path.join(WORKTREE, artifact["path"])
            self.assertTrue(os.path.isfile(pointed))
            with open(pointed, "rb") as handle:
                data = handle.read()
            self.assertEqual(len(data), artifact["bytes"])
            import hashlib
            self.assertEqual(hashlib.sha256(data).hexdigest(), artifact["sha256"])

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
        # Copia por teste: o asset compartilhado nunca e mutado, para que uma
        # rodada interrompida nao contamine as demais.
        corrupt_dir = os.path.join(self.base, "corrupt-asset")
        os.makedirs(corrupt_dir, exist_ok=True)
        source = os.path.join(WORKTREE, ".workspace", "tmp", "local-render-adapter-v1",
                              "assets", "marca-salao", "opening-hook.png")
        corrupt = os.path.join(corrupt_dir, "opening-hook.png")
        shutil.copyfile(source, corrupt)
        with open(corrupt, "wb") as handle:
            handle.write(b"isto nao e um png")
        association = read_json(os.path.join(WORKTREE, ASSOC_MS_REL))
        association["assets"][0]["path"] = os.path.relpath(corrupt, WORKTREE).replace(os.sep, "/")
        association_path = os.path.join(self.base, "corrupt-assets.json")
        write_json(association_path, association)
        code = render_local.main([
            "--package", os.path.join(WORKTREE, PKG_MS_REL),
            "--assets", association_path,
            "--output-dir", output_dir,
            "--root", WORKTREE,
        ])
        self.assertEqual(code, 1)
        self.assertEqual(delivery_hashes(output_dir), before)

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
        staging = os.path.join(self.base, "staging-08")
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
            code = self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir, staging=staging)
        self.assertEqual(code, 1)
        self.assertEqual(delivery_hashes(output_dir), before)
        self.assertTrue(os.path.isdir(staging))
        self.assertFalse(os.path.exists(
            os.path.join(output_dir, render_local.PROMOTION_LOCK_NAME)))

    def test_08b_restore_failure_preserves_backup_for_diagnosis(self):
        output_dir = os.path.join(self.base, "preserve-restore")
        self.assertEqual(self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir), 0)
        staging = os.path.join(self.base, "staging-08b")
        real_replace = os.replace
        promotion_calls = {"count": 0}

        def broken_replace(src, dst):
            src_text = str(src)
            if ".backup" in src_text:
                raise OSError("falha simulada de restauracao")
            if src_text.startswith(staging):
                promotion_calls["count"] += 1
                if promotion_calls["count"] == 2:
                    raise OSError("falha simulada de promocao")
            return real_replace(src, dst)

        import io
        import contextlib
        stderr = io.StringIO()
        with mock.patch.object(render_local.os, "replace", side_effect=broken_replace):
            with contextlib.redirect_stderr(stderr):
                code = self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir, staging=staging)
        self.assertEqual(code, 1)
        self.assertIn("backup preservado para diagnostico", stderr.getvalue())
        backup_dir = os.path.join(staging, ".backup")
        self.assertTrue(os.path.isdir(backup_dir))
        self.assertTrue(os.listdir(backup_dir))
        self.assertFalse(os.path.exists(
            os.path.join(output_dir, render_local.PROMOTION_LOCK_NAME)))

    def test_08c_promotion_lock_dispute_has_clear_diagnostic(self):
        output_dir = os.path.join(self.base, "lock-dispute")
        self.assertEqual(self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir), 0)
        before = delivery_hashes(output_dir)
        lock = os.path.join(output_dir, render_local.PROMOTION_LOCK_NAME)
        with open(lock, "w", encoding="utf-8") as handle:
            handle.write("ocupado por outra execucao\n")
        import io
        import contextlib
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir)
        self.assertEqual(code, 1)
        self.assertIn("promocao concorrente", stderr.getvalue())
        self.assertEqual(delivery_hashes(output_dir), before)
        self.assertTrue(os.path.exists(lock))
        os.remove(lock)
        self.assertEqual(self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir), 0)
        self.assertFalse(os.path.exists(lock))

    def test_08d_staging_overlap_rejected_before_any_write(self):
        package_path = os.path.join(WORKTREE, PKG_MS_REL)
        assets_path = os.path.join(WORKTREE, ASSOC_MS_REL)
        output_dir = os.path.join(self.base, "staging-reject-out")
        candidates = [
            WORKTREE,
            os.path.join(output_dir, "inner"),
            self.base,
            package_path,
            os.path.dirname(package_path),
        ]
        for staging in candidates:
            code = render_local.main([
                "--package", package_path,
                "--assets", assets_path,
                "--output-dir", output_dir,
                "--root", WORKTREE,
                "--staging", staging,
            ])
            self.assertEqual(code, 2, f"staging deveria ser rejeitado: {staging}")
        self.assertFalse(os.path.exists(output_dir))
        occupied = os.path.join(self.base, "staging-occupied")
        os.makedirs(occupied, exist_ok=True)
        with open(os.path.join(occupied, "sentinel.txt"), "w", encoding="utf-8") as handle:
            handle.write("nao tocar\n")
        code = render_local.main([
            "--package", package_path,
            "--assets", assets_path,
            "--output-dir", output_dir,
            "--root", WORKTREE,
            "--staging", occupied,
        ])
        self.assertEqual(code, 2)
        self.assertTrue(os.path.isfile(os.path.join(occupied, "sentinel.txt")))
        self.assertFalse(os.path.exists(output_dir))

    def test_08e_provided_empty_staging_survives_recursive_cleanup(self):
        output_dir = os.path.join(self.base, "staging-kept-out")
        staging = os.path.join(self.base, "staging-kept")
        os.makedirs(staging, exist_ok=True)
        self.assertEqual(
            self.run_cli(PKG_MS_REL, ASSOC_MS_REL, output_dir, staging=staging), 0)
        self.assertTrue(os.path.isdir(staging))
        self.assertFalse(os.path.exists(os.path.join(staging, ".backup")))
        self.assertEqual(os.listdir(staging), [])
        self.assertFalse(os.path.exists(
            os.path.join(output_dir, render_local.PROMOTION_LOCK_NAME)))

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


class TimeoutAndInspectionTest(unittest.TestCase):
    """Timeouts e erro de inspecao simulados: nenhum teste espera o limite real."""

    def test_bridge_timeout_short_diagnostic(self):
        def raise_timeout(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=render_local.BRIDGE_TIMEOUT_SECONDS)

        with mock.patch.object(render_local.shutil, "which", return_value="node"), \
                mock.patch.object(render_local.os.path, "isfile", return_value=True), \
                mock.patch.object(render_local.subprocess, "run", side_effect=raise_timeout):
            with self.assertRaises(build_video.DeliveryError) as ctx:
                render_local.run_bridge(WORKTREE, "p.json", "a.json")
        self.assertIn("ponte de validacao excedeu o tempo limite", str(ctx.exception))

    def test_probe_timeout_short_diagnostic(self):
        def raise_timeout(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=render_local.PROBE_TIMEOUT_SECONDS)

        with mock.patch.object(render_local.build_video, "get_ffprobe", return_value="ffprobe"), \
                mock.patch.object(render_local.subprocess, "run", side_effect=raise_timeout):
            with self.assertRaises(build_video.DeliveryError) as ctx:
                render_local.probe_asset(WORKTREE, os.path.join(WORKTREE, "asset.png"))
        self.assertIn("inspecao previa excedeu o tempo limite", str(ctx.exception))

    def test_probe_empty_streams_rejected(self):
        class Result:
            returncode = 0
            stdout = '{"streams": [], "format": {}}'

        with mock.patch.object(render_local.build_video, "get_ffprobe", return_value="ffprobe"), \
                mock.patch.object(render_local.subprocess, "run", return_value=Result()):
            with self.assertRaises(build_video.DeliveryError) as ctx:
                render_local.probe_asset(WORKTREE, os.path.join(WORKTREE, "asset.png"))
        self.assertIn("asset ilegivel pela inspecao previa", str(ctx.exception))

    def test_probe_nonzero_exit_rejected(self):
        class Result:
            returncode = 1
            stdout = ""

        with mock.patch.object(render_local.build_video, "get_ffprobe", return_value="ffprobe"), \
                mock.patch.object(render_local.subprocess, "run", return_value=Result()):
            with self.assertRaises(build_video.DeliveryError):
                render_local.probe_asset(WORKTREE, os.path.join(WORKTREE, "asset.png"))

    def test_version_timeout_returns_unknown(self):
        def raise_timeout(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=render_local.VERSION_TIMEOUT_SECONDS)

        with mock.patch.object(render_local.subprocess, "run", side_effect=raise_timeout):
            self.assertEqual(render_local.tool_version("ffmpeg"), "desconhecida")

    def test_render_timeout_preserves_delivery(self):
        output_dir = os.path.join(self.base, "preserve-render-timeout")
        os.makedirs(output_dir, exist_ok=True)
        sentinel = os.path.join(output_dir, "sentinel.txt")
        with open(sentinel, "w", encoding="utf-8") as handle:
            handle.write("entrega anterior\n")
        before = render_local.sha256_file(sentinel)

        def raise_timeout(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=render_local.RENDER_TIMEOUT_SECONDS)

        with mock.patch.object(render_local.subprocess, "run", side_effect=raise_timeout):
            code = render_local.main([
                "--package", os.path.join(WORKTREE, PKG_MS_REL),
                "--assets", os.path.join(WORKTREE, ASSOC_MS_REL),
                "--output-dir", output_dir,
                "--root", WORKTREE,
            ])
        self.assertEqual(code, 1)
        self.assertEqual(render_local.sha256_file(sentinel), before)

    @classmethod
    def setUpClass(cls):
        os.makedirs(TMP_BASE, exist_ok=True)
        import tempfile
        cls.base = tempfile.mkdtemp(dir=TMP_BASE)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
