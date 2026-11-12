import json
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build_video
import r002_pilot

WORKTREE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(WORKTREE)))
TMP_BASE = os.path.join(MAIN_ROOT, ".workspace", "tmp", "r002-video-local")
CAPTURE_REL = "00-briefings/campanhas/NS-001/capturas/2026-11-05/01-agenda-visao-dia.png"
SRT_REL = "04-legendas/roteiro_r002_agenda_ficticia.srt"
NARRATION_REL = "04-legendas/roteiro_r002_agenda_ficticia_narracao.txt"


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


class OutlineTest(unittest.TestCase):
    def test_map_rect_matches_scale_pad(self):
        rect = {"x": 425, "y": 608, "w": 910, "h": 82}
        x, y, w, h = r002_pilot.map_rect(rect, 1440, 900, 1080, 1920)
        self.assertAlmostEqual(w, 910 * 0.75)
        self.assertAlmostEqual(h, 82 * 0.75)
        self.assertAlmostEqual(x, 425 * 0.75)
        self.assertAlmostEqual(y, 622 + 608 * 0.75)

    def test_png_valid_and_config_driven(self):
        import tempfile
        os.makedirs(TMP_BASE, exist_ok=True)
        base = tempfile.mkdtemp(dir=TMP_BASE)
        try:
            rect = (318.75, 1078.0, 682.5, 61.5)
            a = os.path.join(base, "a.png")
            b = os.path.join(base, "b.png")
            r002_pilot.write_outline_png(a, rect, 6, [255, 193, 7, 255], 10, 1080, 1920)
            r002_pilot.write_outline_png(b, rect, 10, [233, 30, 99, 255], 10, 1080, 1920)
            data = read_bytes(a)
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertNotEqual(data, read_bytes(b))
            info = build_video.probe_media(a)
            self.assertEqual(info["streams"][0]["width"], 1080)
            self.assertEqual(info["streams"][0]["height"], 1920)
        finally:
            shutil.rmtree(base, ignore_errors=True)


class PilotEndToEndTest(unittest.TestCase):
    """Render real, inspecao FFprobe real, revisao localizada e falha transacional."""

    @classmethod
    def setUpClass(cls):
        os.makedirs(TMP_BASE, exist_ok=True)
        import tempfile
        cls.base = tempfile.mkdtemp(dir=TMP_BASE)
        cls.archive = os.path.join(cls.base, "archive")
        cls.manifest = os.path.join(cls.base, "manifest.json")
        cls.srt_copy = os.path.join(cls.base, "copia.srt")
        cls.narration_copy = os.path.join(cls.base, "copia.txt")
        shutil.copyfile(os.path.join(WORKTREE, SRT_REL), cls.srt_copy)
        shutil.copyfile(os.path.join(WORKTREE, NARRATION_REL), cls.narration_copy)
        cls.config = os.path.join(cls.base, "pilot.json")
        with open(os.path.join(WORKTREE, "tools", "r002", "agenda-ficticia.pilot.json"),
                  encoding="utf-8") as handle:
            cfg = json.load(handle)
        cfg["srt"] = os.path.relpath(cls.srt_copy, WORKTREE).replace(os.sep, "/")
        cfg["narration"] = os.path.relpath(cls.narration_copy, WORKTREE).replace(os.sep, "/")
        cfg["videoName"] = "teste-v1.mp4"
        with open(cls.config, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(cfg, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        cls.config_rel = os.path.relpath(cls.config, WORKTREE).replace(os.sep, "/")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base, ignore_errors=True)

    def run_tag(self, config, tag):
        return r002_pilot.run_pilot(
            config, WORKTREE, os.path.join(self.base, "staging-" + tag),
            self.archive, self.manifest, tag, project_root=MAIN_ROOT)

    def test_01_pilot_three_scenes_no_audio(self):
        self.run_tag(self.config_rel, "t-v1")
        video = os.path.join(self.archive, "teste-v1.mp4")
        report = build_video.validate_mp4(video, 1080, 1920, 30, 12.0)
        self.assertEqual(report["videoStreams"], 1)
        self.assertEqual(report["audioStreams"], 0)
        self.assertEqual(report["codec"], "h264")
        self.assertEqual(report["pixFmt"], "yuv420p")
        with open(self.manifest, encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertIn("t-v1", manifest["runs"])
        self.assertEqual(manifest["runs"]["t-v1"]["artifacts"]["capture"]["sha256"],
                         r002_pilot.sha256_file(os.path.join(WORKTREE, CAPTURE_REL)))

    def test_02_revision_reuses_capture(self):
        self.run_tag(self.config_rel, "t-v1")
        with open(self.config, encoding="utf-8") as handle:
            cfg = json.load(handle)
        before_video = r002_pilot.sha256_file(os.path.join(self.archive, "teste-v1.mp4"))
        before_srt = r002_pilot.sha256_file(self.srt_copy)
        cfg["outline"]["color"] = [233, 30, 99, 255]
        cfg["outline"]["thickness"] = 10
        cfg["videoName"] = "teste-revisao.mp4"
        rev = os.path.join(self.base, "revisao.json")
        with open(rev, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(cfg, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        self.run_tag(os.path.relpath(rev, WORKTREE).replace(os.sep, "/"), "t-rev")
        after_video = r002_pilot.sha256_file(os.path.join(self.archive, "teste-revisao.mp4"))
        self.assertNotEqual(before_video, after_video)
        self.assertEqual(before_srt, r002_pilot.sha256_file(self.srt_copy))
        with open(self.manifest, encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertTrue(manifest["runs"]["t-rev"]["unchanged"]["capture"])
        self.assertTrue(manifest["runs"]["t-rev"]["unchanged"]["srt"])
        self.assertTrue(manifest["runs"]["t-rev"]["unchanged"]["narration"])

    def test_03_invalid_srt_preserves_previous_delivery(self):
        self.run_tag(self.config_rel, "t-v1")
        video = os.path.join(self.archive, "teste-v1.mp4")
        hashes_before = {
            "video": r002_pilot.sha256_file(video),
            "srt": r002_pilot.sha256_file(self.srt_copy),
            "narration": r002_pilot.sha256_file(self.narration_copy),
        }
        bad_srt = os.path.join(self.base, "invalido.srt")
        with open(bad_srt, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("1\n00:00:99,000 --> 00:00:04,000\nTexto.\n")
        with open(self.config, encoding="utf-8") as handle:
            cfg = json.load(handle)
        cfg["srt"] = os.path.relpath(bad_srt, WORKTREE).replace(os.sep, "/")
        bad_config = os.path.join(self.base, "invalido.json")
        with open(bad_config, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(cfg, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        with self.assertRaises(build_video.DeliveryError):
            self.run_tag(os.path.relpath(bad_config, WORKTREE).replace(os.sep, "/"), "t-bad")
        self.assertEqual(hashes_before["video"], r002_pilot.sha256_file(video))
        self.assertEqual(hashes_before["srt"], r002_pilot.sha256_file(self.srt_copy))
        self.assertEqual(hashes_before["narration"], r002_pilot.sha256_file(self.narration_copy))


if __name__ == "__main__":
    unittest.main()