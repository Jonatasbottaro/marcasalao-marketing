"""Testes do painel local Video Studio (tools/video_studio.py).

Cobrem o fluxo HTTP (projetos, perfis, rascunho, previa, exportacao), a
seguranca (Host/Origin, contencao a raiz, midia por referencia verificada no
manifesto) e a exportacao real com FFmpeg (REQUIRE_RENDER).
"""

import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import make_request_media
import video_studio

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
TMP_BASE = os.path.join(WORKTREE, ".workspace", "tmp", "t_studio")
FFMPEG_DIR = os.path.join(MAIN_ROOT, ".workspace", "tools", "ffmpeg")
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe")) or all(
    os.path.isfile(os.path.join(FFMPEG_DIR, name))
    for name in (("ffmpeg.exe", "ffprobe.exe") if os.name == "nt" else ("ffmpeg", "ffprobe"))
)
HAS_BRIDGE = bool(shutil.which("node")) and os.path.isfile(
    os.path.join(WORKTREE, "platform", "dist", "src", "compile-video-request.js"))
REQUIRE_RENDER = os.environ.get("REQUIRE_RENDER") == "1"
PROJECT_MS = "platform/examples/projects/marca-salao-social.project.json"
EXAMPLE_MS = "tools/produce/examples/marca-salao-social-reel.video-request.json"


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


class StudioTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAS_BRIDGE:
            raise unittest.SkipTest("ponte TypeScript indisponivel")
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        cls.port = sock.getsockname()[1]
        sock.close()
        cls.httpd, cls.studio = video_studio.make_server(MAIN_ROOT, cls.port)
        cls.studio.port = cls.port
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = f"http://127.0.0.1:{cls.port}"
        cls.host = f"127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def request(self, method, path, body=None, origin=None, host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        headers = {"Host": host or self.host}
        if method == "POST":
            headers["Origin"] = origin if origin is not None else self.origin
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        try:
            payload = json.loads(data)
        except ValueError:
            payload = data
        return res.status, payload

    def setUp(self):
        self.dir = os.path.join(TMP_BASE, self._testMethodName)
        os.makedirs(self.dir, exist_ok=True)
        self.example = read_json(os.path.join(MAIN_ROOT, EXAMPLE_MS))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class StudioHttpTest(StudioTestBase):
    def test_index_html(self):
        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Video Studio", body)

    def test_projects(self):
        status, data = self.request("GET", "/api/projects")
        self.assertEqual(status, 200)
        ids = [p["id"] for p in data["projects"]]
        self.assertIn("marca-salao", ids)
        self.assertIn("multitrack-hub", ids)

    def test_profiles_local_export(self):
        status, data = self.request("GET", "/api/profiles?project=" + PROJECT_MS)
        self.assertEqual(status, 200)
        profiles = {p["id"]: p for p in data["listing"]["profiles"]}
        for pid in ("instagram-reels-video", "facebook-reels-video", "youtube-shorts"):
            self.assertTrue(profiles[pid]["localExport"], pid)
            self.assertEqual(profiles[pid]["availability"], "allowed")

    def test_draft_save_load_roundtrip(self):
        rel = f".workspace/tmp/t_studio/{self._testMethodName}/draft.json"
        status, data = self.request("POST", "/api/draft/save", {"path": rel, "request": self.example})
        self.assertEqual(status, 200, data)
        status, data = self.request("GET", "/api/draft/load?path=" + rel)
        self.assertEqual(status, 200)
        self.assertEqual(data["request"]["id"], self.example["id"])

    def test_preview_sem_ffmpeg(self):
        status, data = self.request("POST", "/api/preview", {"request": self.example})
        self.assertEqual(status, 200, data)
        self.assertEqual(data["result"]["status"], "preview")
        self.assertEqual(len(data["result"]["profiles"]), 3)
        for p in data["result"]["profiles"]:
            self.assertEqual(p["status"], "compiled")
            self.assertEqual(p["durationMs"], 14000)

    def test_examples_listed(self):
        status, data = self.request("GET", "/api/examples")
        self.assertEqual(status, 200)
        names = [e["name"] for e in data["examples"]]
        self.assertIn("marca-salao-social-reel.video-request.json", names)
        self.assertIn("multitrack-hub-social-reel.video-request.json", names)


class StudioSecurityTest(StudioTestBase):
    def test_post_bad_origin_rejected(self):
        status, data = self.request("POST", "/api/draft/save",
                                    {"path": ".workspace/tmp/x.json", "request": self.example},
                                    origin="http://evil.example")
        self.assertEqual(status, 403)

    def test_post_missing_origin_rejected(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        conn.request("POST", "/api/draft/save", body=json.dumps({"path": ".workspace/tmp/x.json", "request": self.example}),
                     headers={"Host": self.host, "Content-Type": "application/json"})
        res = conn.getresponse()
        res.read()
        conn.close()
        self.assertEqual(res.status, 403)

    def test_bad_host_rejected(self):
        status, _ = self.request("GET", "/api/projects", host="evil.example")
        self.assertEqual(status, 403)

    def test_draft_load_traversal_rejected(self):
        status, _ = self.request("GET", "/api/draft/load?path=../../etc/passwd")
        self.assertEqual(status, 400)

    def test_draft_save_outside_workspace_rejected(self):
        status, _ = self.request("POST", "/api/draft/save",
                                 {"path": "tools/produce/examples/hack.json", "request": self.example})
        self.assertEqual(status, 400)

    def test_media_traversal_rejected(self):
        status, _ = self.request("GET", "/media?dir=.workspace/tmp/x&profile=..&kind=video")
        self.assertEqual(status, 404)


class StudioExportTest(StudioTestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError("REQUIRE_RENDER=1 mas FFmpeg/FFprobe ausentes")
            raise unittest.SkipTest("FFmpeg/FFprobe indisponiveis")

    def test_export_and_serve_verified_media(self):
        make_request_media.generate_request_media(self.example, MAIN_ROOT)
        output_rel = f".workspace/tmp/t_studio/{self._testMethodName}/entrega"
        status, data = self.request("POST", "/api/export", {"request": self.example, "outputDir": output_rel})
        self.assertEqual(status, 200, data)
        job = data["jobId"]
        final = None
        for _ in range(200):
            status, data = self.request("GET", "/api/export/status?job=" + job)
            self.assertEqual(status, 200)
            if data["status"] != "running":
                final = data
                break
            import time
            time.sleep(1.5)
        self.assertIsNotNone(final, "exportacao nao concluiu")
        self.assertEqual(final["status"], "completed", final)
        self.assertEqual(len([p for p in final["result"]["profiles"] if p["status"] == "completed"]), 3)

        status, delivery = self.request("GET", "/api/delivery?dir=" + output_rel)
        self.assertEqual(status, 200)
        self.assertEqual(delivery["index"]["completedCount"], 3)

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        conn.request("GET", f"/media?dir={output_rel}&profile=youtube-shorts&kind=video", headers={"Host": self.host})
        res = conn.getresponse()
        blob = res.read()
        conn.close()
        self.assertEqual(res.status, 200)
        self.assertEqual(res.getheader("Content-Type"), "video/mp4")
        self.assertGreater(len(blob), 1000)

        status, _ = self.request("GET", f"/media?dir={output_rel}&profile=youtube-shorts&kind=srt")
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()