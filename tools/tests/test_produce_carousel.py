"""Testes do exportador de carrossel (tools/produce_carousel.py).

Previa sem FFmpeg; exportacao real de JPEGs 1080x1080 + ZIP + manifesto;
ordem numerada; remocao de card reflete no conjunto e no ZIP; falha preserva a
ultima entrega valida; overflow de texto indica o card.
"""

import json
import os
import shutil
import subprocess
import sys
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build_video
import carousel_layout
import make_request_media
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
TMP_BASE = os.path.join(WORKTREE, ".workspace", "tmp", "t_carousel")
FFMPEG_DIR = os.path.join(MAIN_ROOT, ".workspace", "tools", "ffmpeg")
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe")) or all(
    os.path.isfile(os.path.join(FFMPEG_DIR, n)) for n in (("ffmpeg.exe", "ffprobe.exe") if os.name == "nt" else ("ffmpeg", "ffprobe")))
HAS_BRIDGE = bool(shutil.which("node")) and os.path.isfile(
    os.path.join(WORKTREE, "platform", "dist", "src", "validate-carousel-request.js"))
REQUIRE_RENDER = os.environ.get("REQUIRE_RENDER") == "1"
EXAMPLE = "tools/produce/examples/marca-salao-carousel.carousel-request.json"


def read_json(p):
    with open(p, encoding="utf-8") as h:
        return json.load(h)


def run_carousel(args):
    return subprocess.run([sys.executable, os.path.join(WORKTREE, "tools", "produce_carousel.py"), *args],
                          capture_output=True, text=True, cwd=MAIN_ROOT, timeout=300)


class CarouselTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAS_BRIDGE:
            raise unittest.SkipTest("ponte indisponivel")

    def setUp(self):
        self.dir = os.path.join(TMP_BASE, self._testMethodName)
        os.makedirs(self.dir, exist_ok=True)
        self.example = read_json(os.path.join(MAIN_ROOT, EXAMPLE))
        self.input_path = os.path.join(self.dir, "pedido.json")
        with open(self.input_path, "w", encoding="utf-8") as h:
            json.dump(self.example, h)
        self.output = os.path.join(self.dir, "entrega")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def rel(self, p):
        return os.path.relpath(p, MAIN_ROOT).replace(os.sep, "/")


class PreviewTest(CarouselTestBase):
    def test_previa_ordem_geometria_sem_ffmpeg(self):
        res = run_carousel(["--input", self.rel(self.input_path), "--plan-only", "--json"])
        self.assertEqual(res.returncode, 0, res.stderr)
        d = json.loads(res.stdout)
        self.assertEqual(d["status"], "preview")
        self.assertEqual(d["geometry"]["width"], 1080)
        self.assertEqual(d["geometry"]["height"], 1080)
        self.assertEqual([c["id"] for c in d["cards"]], ["capa", "conteudo", "fechamento"])
        self.assertEqual(d["overflowCards"], [])
        self.assertFalse(os.path.exists(self.output))

    def test_pedido_invalido_saida_3(self):
        bad = dict(self.example, id="Invalido")
        with open(self.input_path, "w", encoding="utf-8") as h:
            json.dump(bad, h)
        res = run_carousel(["--input", self.rel(self.input_path), "--plan-only", "--json"])
        self.assertEqual(res.returncode, 3)

    def test_overflow_indica_card(self):
        long = dict(self.example)
        long["cards"] = [{"id": "capa", "title": "Titulo", "body": "palavra " * 400}]
        with open(self.input_path, "w", encoding="utf-8") as h:
            json.dump(long, h)
        res = run_carousel(["--input", self.rel(self.input_path), "--plan-only", "--json"])
        self.assertEqual(res.returncode, 3)
        d = json.loads(res.stdout)
        self.assertIn("capa", d["overflowCards"])


class LayoutTest(unittest.TestCase):
    def test_wrap_e_overflow(self):
        m = carousel_layout.measure_card({"id": "c", "title": "Titulo curto", "body": "corpo"})
        self.assertFalse(m["overflow"])
        m2 = carousel_layout.measure_card({"id": "c", "title": "T", "body": "palavra " * 400})
        self.assertTrue(m2["overflow"])
        lines = carousel_layout.wrap_text("uma duas tres quatro cinco seis sete oito nove dez", 300, 5)
        self.assertTrue(all(carousel_layout.text_width(l, 5) <= 300 for l in lines))


class ExportTest(CarouselTestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError("REQUIRE_RENDER=1 mas FFmpeg ausente")
            raise unittest.SkipTest("FFmpeg indisponivel")

    def test_exporta_jpegs_zip_manifesto_ordem(self):
        make_request_media.generate_request_media(self.example, MAIN_ROOT)
        res = run_carousel(["--input", self.rel(self.input_path), "--output-dir", self.rel(self.output), "--json"])
        self.assertEqual(res.returncode, 0, res.stderr)
        d = json.loads(res.stdout)
        self.assertEqual(d["cards"], ["01-capa.jpg", "02-conteudo.jpg", "03-fechamento.jpg"])
        manifest = read_json(os.path.join(self.output, "carousel-manifest.json"))
        self.assertEqual(manifest["requestId"], self.example["id"])
        self.assertEqual([c["file"] for c in manifest["cards"]], d["cards"])
        for c in manifest["cards"]:
            path = os.path.join(MAIN_ROOT, c["path"])
            self.assertTrue(os.path.isfile(path))
            with open(path, "rb") as h:
                self.assertEqual(h.read(3), b"\xff\xd8\xff")  # JPEG magic
            self.assertEqual(os.path.getsize(path), c["bytes"])
            self.assertEqual(render_local.sha256_file(path), c["sha256"])
        with zipfile.ZipFile(os.path.join(self.output, "carousel.zip")) as zf:
            self.assertEqual(zf.namelist(), d["cards"])
        idx = read_json(os.path.join(self.output, "index.json"))
        self.assertEqual(idx["lastValidDelivery"]["status"], "completed")

    def test_remocao_de_card_reflete_ordem_e_zip(self):
        make_request_media.generate_request_media(self.example, MAIN_ROOT)
        run_carousel(["--input", self.rel(self.input_path), "--output-dir", self.rel(self.output), "--json"])
        reduced = dict(self.example)
        reduced["cards"] = [c for c in self.example["cards"] if c["id"] != "conteudo"]
        with open(self.input_path, "w", encoding="utf-8") as h:
            json.dump(reduced, h)
        res = run_carousel(["--input", self.rel(self.input_path), "--output-dir", self.rel(self.output), "--json"])
        self.assertEqual(res.returncode, 0, res.stderr)
        d = json.loads(res.stdout)
        self.assertEqual(d["cards"], ["01-capa.jpg", "02-fechamento.jpg"])
        self.assertFalse(os.path.exists(os.path.join(self.output, "02-conteudo.jpg")))
        self.assertFalse(os.path.exists(os.path.join(self.output, "03-fechamento.jpg")))
        with zipfile.ZipFile(os.path.join(self.output, "carousel.zip")) as zf:
            self.assertEqual(zf.namelist(), d["cards"])

    def test_falha_preserva_entrega_anterior(self):
        make_request_media.generate_request_media(self.example, MAIN_ROOT)
        run_carousel(["--input", self.rel(self.input_path), "--output-dir", self.rel(self.output), "--json"])
        before = render_local.sha256_file(os.path.join(self.output, "01-capa.jpg"))
        os.remove(os.path.join(MAIN_ROOT, self.example["media"][0]["path"]))
        res = run_carousel(["--input", self.rel(self.input_path), "--output-dir", self.rel(self.output), "--json"])
        self.assertNotEqual(res.returncode, 0)
        after = render_local.sha256_file(os.path.join(self.output, "01-capa.jpg"))
        self.assertEqual(before, after)
        self.assertTrue(os.path.isfile(os.path.join(self.output, "carousel.zip")))


if __name__ == "__main__":
    unittest.main()