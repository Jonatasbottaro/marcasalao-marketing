import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build_video

CAPTURE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "00-briefings", "campanhas", "NS-001", "capturas", "2026-11-05", "01-agenda-visao-dia.png",
)


class BuildVideoCommandTest(unittest.TestCase):
    def setUp(self):
        self.commands = []
        self.original = build_video.run_cmd
        build_video.run_cmd = self.capture_cmd

    def tearDown(self):
        build_video.run_cmd = self.original

    def capture_cmd(self, cmd):
        self.commands.append(cmd)
        return True

    def test_no_audio_injection(self):
        ok = build_video.build_video(CAPTURE, None, None, None, "out.mp4", duration=4.0)
        self.assertTrue(ok)
        cmd = self.commands[0]
        joined = " ".join(cmd)
        self.assertNotIn("anullsrc", joined)
        self.assertNotIn("aac", joined)
        self.assertIn("-an", cmd)
        self.assertNotIn("-c:a", cmd)

    def test_audio_input_rejected(self):
        with self.assertRaises(build_video.DeliveryError):
            build_video.build_video(CAPTURE, "voz.mp3", None, None, "out.mp4")
        self.assertEqual(self.commands, [])

    def test_overlay_fade_window(self):
        build_video.build_video(CAPTURE, None, CAPTURE, None, "out.mp4", duration=12.0,
                                overlay_start=4.0, overlay_end=9.0,
                                overlay_fade_in=0.5, overlay_fade_out=0.5)
        joined = " ".join(self.commands[0])
        self.assertIn("fade=t=in:st=4.0:d=0.5:alpha=1", joined)
        self.assertIn("fade=t=out:st=8.5:d=0.5:alpha=1", joined)
        self.assertIn("between(t,4.0,9.0)", joined)


class ValidateMp4Test(unittest.TestCase):
    def test_non_media_rejected(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake.mp4")
        with open(path, "wb") as handle:
            handle.write(b"isto nao e um mp4")
        try:
            with self.assertRaises(build_video.DeliveryError):
                build_video.validate_mp4(path, 1080, 1920, 30, 12.0)
        finally:
            os.remove(path)


class TransactionalExportTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        worktree = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # sobe ate o checkout principal: em worktree o .git e arquivo, nao diretorio
        main_root = worktree
        while not os.path.isdir(os.path.join(main_root, ".git")):
            parent = os.path.dirname(main_root)
            if parent == main_root:
                break
            main_root = parent
        tmp_base = os.path.join(main_root, ".workspace", "tmp", "r002-video-local")
        os.makedirs(tmp_base, exist_ok=True)
        self.base = tempfile.mkdtemp(dir=tmp_base)
        self.dest = os.path.join(self.base, "dest.txt")
        self.staging = os.path.join(self.base, "staging")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.base, ignore_errors=True)

    def test_failure_preserves_destination(self):
        with open(self.dest, "w", encoding="utf-8") as handle:
            handle.write("entrega anterior")
        before = open(self.dest, "rb").read()

        def render(paths):
            with open(paths["a"], "w", encoding="utf-8") as handle:
                handle.write("novo parcial")

        def validators(paths):
            raise build_video.DeliveryError("SRT invalido: teste")

        with self.assertRaises(build_video.DeliveryError):
            build_video.transactional_export(
                self.staging, {"a": {"staging": "a.txt", "dest": self.dest}}, render, validators)
        self.assertEqual(open(self.dest, "rb").read(), before)
        self.assertTrue(os.path.exists(os.path.join(self.staging, "a.txt")))

    def test_success_promotes_atomically(self):
        def render(paths):
            with open(paths["a"], "w", encoding="utf-8") as handle:
                handle.write("novo aprovado")

        build_video.transactional_export(
            self.staging, {"a": {"staging": "a.txt", "dest": self.dest}}, render, lambda paths: None)
        self.assertEqual(open(self.dest, encoding="utf-8").read(), "novo aprovado")


if __name__ == "__main__":
    unittest.main()