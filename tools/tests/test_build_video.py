import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# get_ffmpeg()/get_ffprobe() resolvem o caminho do binario mesmo quando run_cmd e
# simulado; sem isto o modulo falha isolado numa estacao sem ffmpeg no PATH global.
if shutil.which("ffmpeg") is None:
    _ffmpeg_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        ".workspace", "tools", "ffmpeg",
    )
    if os.path.isdir(_ffmpeg_dir):
        os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

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


class CleanModeContractTest(unittest.TestCase):
    """VIDEO CLEAN (26/11/2026): sem legendas queimadas/SRT, retrocompativel.

    O contrato VideoRequest v1 e o pacote de execucao nao mudam; o modo clean
    e uma opcao de renderizacao Python. Sem a opcao, o comportamento legado
    (legenda queimada + SRT validado) permanece identico.
    """

    @classmethod
    def setUpClass(cls):
        import render_local
        import render_pipeline
        import produce_video
        cls.render_local = render_local
        cls.render_pipeline = render_pipeline
        cls.produce_video = produce_video
        cls.package = {
            "output": {"width": 1080, "height": 1920, "fps": 30, "durationMs": 4000},
            "timeline": [
                {"beatId": "b1", "durationMs": 2000, "motionIntent": "none",
                 "transitionOut": "cut", "onScreenText": "Primeira cena"},
                {"beatId": "b2", "durationMs": 2000, "motionIntent": "none",
                 "transitionOut": "fade", "onScreenText": "Segunda cena"},
            ],
        }

    def test_grafo_clean_sem_filtro_subtitles(self):
        graph = self.render_local.build_filter_graph(self.package, None, burn_captions=False)
        self.assertNotIn("subtitles=", graph)
        self.assertTrue(graph.endswith("scale=out_range=limited,format=yuv420p[vfinal]"))

    def test_grafo_legado_padrao_mantem_legenda(self):
        graph = self.render_local.build_filter_graph(self.package, "C:/x/a.srt")
        self.assertIn("subtitles=", graph)
        self.assertIn("format=yuv420p[vfinal]", graph)

    def test_comando_clean_sem_audio_e_sem_legenda(self):
        cmd = self.render_local.build_render_command(
            self.package, ["a.png", "b.png"], None, "out.mp4", "veryfast", burn_captions=False)
        joined = " ".join(cmd)
        self.assertIn("-an", cmd)
        self.assertNotIn("subtitles=", joined)
        self.assertNotIn("-c:a", cmd)

    def test_assinaturas_clean_retrocompativeis(self):
        import inspect
        for fn in (self.render_local.run_render,
                   self.render_pipeline.run_render_pipeline,
                   self.produce_video.export_profile):
            params = inspect.signature(fn).parameters
            self.assertIn("clean", params)
            self.assertIs(params["clean"].default, False)

    def test_cli_produce_video_aceita_clean(self):
        parser_actions = None
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try:
                self.produce_video.main(["--help"])
            except SystemExit:
                pass
        self.assertIn("--clean", buf.getvalue())

    def test_delivery_fields_preserva_marcador_clean(self):
        self.assertIn("captionsMode", self.produce_video.DELIVERY_FIELDS)


if __name__ == "__main__":
    unittest.main()