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
import time
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import make_agenda_media
import make_request_media
import render_local
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
STUDIO_ROOT = WORKTREE
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
        if HAS_FFMPEG and not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
            render_local.ensure_video_tools(MAIN_ROOT)
        cls._start_server()

    @classmethod
    def _start_server(cls):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        cls.port = sock.getsockname()[1]
        sock.close()
        cls.httpd, cls.studio = video_studio.make_server(STUDIO_ROOT, cls.port)
        cls.studio.port = cls.port
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = f"http://127.0.0.1:{cls.port}"
        cls.host = f"127.0.0.1:{cls.port}"

    @classmethod
    def restart_server(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls._start_server()

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
        shutil.rmtree(render_local.fs_path(self.dir, force=True), ignore_errors=True)
        os.makedirs(render_local.fs_path(self.dir), exist_ok=True)
        self.example = read_json(os.path.join(STUDIO_ROOT, EXAMPLE_MS))

    def tearDown(self):
        shutil.rmtree(render_local.fs_path(self.dir, force=True), ignore_errors=True)


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
        make_request_media.generate_request_media(self.example, STUDIO_ROOT)
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


class CarouselPanelTest(StudioTestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError("REQUIRE_RENDER=1 mas FFmpeg ausente")
            raise unittest.SkipTest("FFmpeg indisponivel")

    def setUp(self):
        super().setUp()
        self.carousel = read_json(os.path.join(STUDIO_ROOT, "tools/produce/examples/marca-salao-carousel.carousel-request.json"))
        make_request_media.generate_request_media(self.carousel, STUDIO_ROOT)

    def test_examples_include_carousel(self):
        status, data = self.request("GET", "/api/examples")
        self.assertEqual(status, 200)
        kinds = {e["kind"] for e in data["examples"]}
        self.assertIn("carousel", kinds)
        self.assertIn("video", kinds)

    def test_preview_carousel(self):
        status, data = self.request("POST", "/api/preview", {"request": self.carousel, "kind": "carousel"})
        self.assertEqual(status, 200, data)
        r = data["result"]
        self.assertEqual(r["status"], "preview")
        self.assertEqual(r["geometry"]["width"], 1080)
        self.assertEqual(len(r["cards"]), 3)

    def test_export_carousel_and_serve_images_zip(self):
        output_rel = f".workspace/tmp/t_studio/{self._testMethodName}/entrega"
        status, data = self.request("POST", "/api/export", {"request": self.carousel, "outputDir": output_rel, "kind": "carousel"})
        self.assertEqual(status, 200, data)
        job = data["jobId"]
        final = None
        for _ in range(120):
            status, d = self.request("GET", "/api/export/status?job=" + job)
            if d["status"] != "running":
                final = d
                break
            import time
            time.sleep(1.0)
        self.assertIsNotNone(final)
        self.assertEqual(final["status"], "completed", final)
        self.assertEqual(final["kind"], "carousel")

        status, delivery = self.request("GET", "/api/carousel-delivery?dir=" + output_rel)
        self.assertEqual(status, 200)
        self.assertEqual(len(delivery["manifest"]["cards"]), 3)
        self.assertIsNotNone(delivery["index"]["lastValidDelivery"])

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        conn.request("GET", f"/media?dir={output_rel}&kind=card&index=0", headers={"Host": self.host})
        res = conn.getresponse()
        blob = res.read()
        conn.close()
        self.assertEqual(res.status, 200)
        self.assertEqual(blob[:3], b"\xff\xd8\xff")

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        conn.request("GET", f"/media?dir={output_rel}&kind=zip", headers={"Host": self.host})
        res = conn.getresponse()
        zblob = res.read()
        conn.close()
        self.assertEqual(res.status, 200)
        self.assertEqual(zblob[:2], b"PK")

    def test_job_status_idempotent_two_queries(self):
        output_rel = f".workspace/tmp/t_studio/{self._testMethodName}/entrega"
        status, data = self.request("POST", "/api/export", {"request": self.carousel, "outputDir": output_rel, "kind": "carousel"})
        job = data["jobId"]
        final = None
        for _ in range(120):
            status, d = self.request("GET", "/api/export/status?job=" + job)
            if d["status"] != "running":
                final = d
                break
            import time
            time.sleep(1.0)
        self.assertIsNotNone(final)
        self.assertEqual(final["status"], "completed")
        status, second = self.request("GET", "/api/export/status?job=" + job)
        status, third = self.request("GET", "/api/export/status?job=" + job)
        self.assertEqual(second["status"], "completed")
        self.assertEqual(third["status"], "completed")
        self.assertEqual(second["result"], final["result"])
        self.assertEqual(third["result"], final["result"])


class MotionPanelTest(StudioTestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError("REQUIRE_RENDER=1 mas FFmpeg ausente")
            raise unittest.SkipTest("FFmpeg indisponivel")

    def setUp(self):
        super().setUp()
        self.mreq = read_json(os.path.join(STUDIO_ROOT, "tools/produce/examples/marca-salao-motion.video-request.json"))
        self.mplan = read_json(os.path.join(STUDIO_ROOT, "tools/produce/examples/marca-salao-motion.motion-plan.json"))
        make_agenda_media.write_agenda_png(os.path.join(STUDIO_ROOT, self.mreq["media"][0]["path"].replace("/", os.sep)))

    def test_source_media_served(self):
        status, _ = self.request("GET", "/source-media?path=" + self.mreq["media"][0]["path"])
        self.assertEqual(status, 200)

    def test_preview_motion_resolved(self):
        status, data = self.request("POST", "/api/preview", {"request": self.mreq, "motionPlan": self.mplan, "kind": "video"})
        self.assertEqual(status, 200, data)
        motion = data["result"]["profiles"][0]["motion"]
        self.assertEqual(motion["effects"][0]["absoluteStartMs"], 500)
        self.assertEqual(motion["effects"][0]["absoluteEndMs"], 3000)

    def test_export_motion_and_concurrent_status(self):
        output_rel = f".workspace/tmp/t_studio/{self._testMethodName}/entrega"
        status, data = self.request("POST", "/api/export", {"request": self.mreq, "outputDir": output_rel, "profile": "instagram-reels-video", "kind": "video", "motionPlan": self.mplan})
        self.assertEqual(status, 200, data)
        job = data["jobId"]
        final = None
        for _ in range(120):
            status, d = self.request("GET", "/api/export/status?job=" + job)
            if d["status"] != "running":
                final = d
                break
            time.sleep(1.0)
        self.assertIsNotNone(final)
        self.assertEqual(final["status"], "completed", final)
        # consultas simultaneas apos o fim: mesmo resultado, job finalizado uma vez
        results = []
        threads = [threading.Thread(target=lambda: results.append(self.request("GET", "/api/export/status?job=" + job))) for _ in range(4)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(len(results), 4)
        for _, r in results:
            self.assertEqual(r["status"], "completed")
            self.assertEqual(r["result"], final["result"])
        # video com motion servido
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        conn.request("GET", f"/media?dir={output_rel}&profile=instagram-reels-video&kind=video", headers={"Host": self.host})
        res = conn.getresponse()
        blob = res.read()
        conn.close()
        self.assertEqual(res.status, 200)
        self.assertGreater(len(blob), 1000)


class StudioWorkspaceLifecycleTest(StudioTestBase):
    def _cleanup_project(self, project_id):
        path = os.path.join(STUDIO_ROOT, ".workspace", "studio", "projects", f"{project_id}.project.json")
        if os.path.isfile(path):
            os.remove(path)

    def _cleanup_work(self, work_id):
        work_dir = os.path.join(STUDIO_ROOT, ".workspace", "studio", "works", work_id)
        shutil.rmtree(render_local.fs_path(work_dir, force=True), ignore_errors=True)
        for piece in ("video", "carousel", "motion"):
            st_path = self.studio._export_status_path(f".workspace/studio/works/{work_id}/deliveries/{piece}")
            if os.path.isfile(st_path):
                os.remove(st_path)

    def _poll_job(self, job_id, limit=180):
        for _ in range(limit):
            status, d = self.request("GET", "/api/export/status?job=" + job_id)
            self.assertEqual(status, 200, d)
            if d["status"] != "running":
                return d
            time.sleep(1.0)
        self.fail(f"job {job_id} excedeu tempo limite")

    def _fetch_raw(self, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        conn.request("GET", path, headers={"Host": self.host})
        res = conn.getresponse()
        blob = res.read()
        ctype = res.getheader("Content-Type")
        conn.close()
        return res.status, ctype, blob

    def test_readiness_endpoint_and_cli_check(self):
        status, data = self.request("GET", "/api/readiness")
        self.assertEqual(status, 200)
        r = data["readiness"]
        self.assertIn("summary", r)
        self.assertEqual([i["id"] for i in r["items"]], ["python", "node", "platformBuild", "ffmpeg", "ffprobe"])
        res = subprocess.run(
            [sys.executable, os.path.join(STUDIO_ROOT, "tools", "video_studio.py"),
             "--check", "--json", "--root", STUDIO_ROOT],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        parsed = json.loads(res.stdout)
        self.assertEqual(len(parsed["items"]), 5)
        self.assertEqual(res.returncode, 0 if parsed["ready"] else 1)

    def test_register_project_validation_and_module_filtering(self):
        pid = "t-proj-val"
        self.addCleanup(self._cleanup_project, pid)
        self._cleanup_project(pid)

        # Invalido (id maiusculo e profiles vazio): rejeitado pelo nucleo antes de gravar
        status, err = self.request("POST", "/api/projects/create", {
            "id": "Invalido", "name": "Ruim", "outputProfiles": [],
        })
        self.assertEqual(status, 400, err)
        self.assertFalse(os.path.exists(
            os.path.join(STUDIO_ROOT, ".workspace", "studio", "projects", "Invalido.project.json")))

        # Valido: salvo em .workspace/studio/projects/ e listado com origem 'registered'
        manifest = {
            "schemaVersion": 1,
            "id": pid,
            "name": "Projeto Prova Studio",
            "locale": "pt-BR",
            "timezone": "America/Sao_Paulo",
            "brandTheme": pid,
            "assetRoot": f".workspace/studio/projects/{pid}/assets",
            "contentPolicies": {
                "requireApprovedBriefing": True,
                "requireApprovedScript": True,
                "prohibitPersonalData": True,
                "requireFunctionalEvidence": True,
            },
            "outputProfiles": [
                "instagram-reels-video",
                "youtube-shorts",
                "instagram-feed-image-square",
                "youtube-video-horizontal",
            ],
        }
        status, data = self.request("POST", "/api/projects/create", manifest)
        self.assertEqual(status, 200, data)
        self.assertTrue(data["report"]["valid"])
        proj_rel = data["path"]

        status, listed = self.request("GET", "/api/projects")
        self.assertEqual(status, 200)
        by_id = {p["id"]: p for p in listed["projects"]}
        self.assertEqual(by_id[pid]["source"], "registered")
        self.assertEqual(by_id["marca-salao"]["source"], "example")

        # Filtragem por modulo
        status, v_prof = self.request("GET", f"/api/profiles?project={proj_rel}&module=video")
        self.assertEqual(status, 200)
        v_ids = [p["id"] for p in v_prof["listing"]["compatibleProfiles"]]
        self.assertEqual(set(v_ids), {"instagram-reels-video", "youtube-shorts"})

        status, c_prof = self.request("GET", f"/api/profiles?project={proj_rel}&module=carousel")
        self.assertEqual(status, 200)
        c_ids = [p["id"] for p in c_prof["listing"]["compatibleProfiles"]]
        self.assertEqual(c_ids, ["instagram-feed-image-square"])

    def test_work_lifecycle_conflict_resumption_and_multi_scene_motion(self):
        wid = "t-work-resume"
        self.addCleanup(self._cleanup_work, wid)
        self._cleanup_work(wid)

        status, created = self.request("POST", "/api/works/create", {
            "id": wid,
            "name": "Trabalho Retomada",
            "project": PROJECT_MS,
            "template": "blank",
        })
        self.assertEqual(status, 200, created)
        paths = created["work"]["paths"]
        self.assertTrue(paths["videoDraft"].startswith(f".workspace/studio/works/{wid}/"))
        self.assertTrue(paths["mediaDir"].startswith(f".workspace/studio/works/{wid}/media"))

        # Conflito de trabalho existente rejeitado sem sobrescrever
        status, dup = self.request("POST", "/api/works/create", {
            "id": wid, "name": "Outro Nome", "project": PROJECT_MS,
        })
        self.assertEqual(status, 400, dup)

        # Editar Video, Carrossel e Motion com efeitos em DUAS cenas diferentes
        vreq = created["videoRequest"]
        vreq["scenes"][0]["title"] = "Titulo Editado 1"
        creq = created["carouselRequest"]
        creq["cards"][0]["title"] = "Card Capa Editado"
        mplan = {
            "schemaVersion": 1,
            "requestId": vreq["id"],
            "effects": [
                {
                    "sceneId": "cena-1",
                    "region": {"x": 0.1, "y": 0.2, "w": 0.5, "h": 0.15},
                    "color": "#00FFAA",
                    "thickness": 5,
                    "startMs": 300,
                    "endMs": 2200,
                },
                {
                    "sceneId": "cena-2",
                    "region": {"x": 0.06, "y": 0.35, "w": 0.88, "h": 0.14},
                    "color": "#FFD700",
                    "thickness": 6,
                    "startMs": 500,
                    "endMs": 3000,
                },
            ],
        }
        status, saved = self.request("POST", "/api/works/save", {
            "workId": wid,
            "videoRequest": vreq,
            "carouselRequest": creq,
            "motionPlan": mplan,
        })
        self.assertEqual(status, 200, saved)

        # Reinicia o servidor HTTP e o objeto Studio
        self.restart_server()

        status, works = self.request("GET", "/api/works")
        self.assertEqual(status, 200)
        self.assertIn(wid, [w["id"] for w in works["works"]])

        status, reopened = self.request("GET", f"/api/works/open?id={wid}")
        self.assertEqual(status, 200, reopened)
        self.assertEqual(reopened["videoRequest"]["scenes"][0]["title"], "Titulo Editado 1")
        self.assertEqual(reopened["carouselRequest"]["cards"][0]["title"], "Card Capa Editado")
        self.assertEqual([e["sceneId"] for e in reopened["motionPlan"]["effects"]], ["cena-1", "cena-2"])
        self.assertEqual(reopened["motionPlan"]["effects"][0]["color"], "#00FFAA")
        self.assertEqual(len(reopened["workMedia"]), 2)

        # Traversal rejeitado
        status, _ = self.request("GET", "/api/works/open?id=../etc")
        self.assertEqual(status, 400)

    def test_guided_demo_creation_and_preview(self):
        wid = "t-demo-ms"
        self.addCleanup(self._cleanup_work, wid)
        self._cleanup_work(wid)

        status, data = self.request("POST", "/api/works/demo", {"brand": "marca-salao", "id": wid})
        self.assertEqual(status, 200, data)
        status, pv = self.request("POST", "/api/preview", {"request": data["videoRequest"]})
        self.assertEqual(status, 200, pv)
        self.assertEqual(pv["result"]["status"], "preview")
        status, pc = self.request("POST", "/api/preview", {"request": data["carouselRequest"], "kind": "carousel"})
        self.assertEqual(status, 200, pc)
        self.assertEqual(pc["result"]["status"], "preview")

    def test_interrupted_job_detected_after_restart(self):
        wid = "t-work-int"
        self.addCleanup(self._cleanup_work, wid)
        self._cleanup_work(wid)

        status, created = self.request("POST", "/api/works/create", {
            "id": wid, "name": "Interrupcao", "project": PROJECT_MS, "template": "blank",
        })
        self.assertEqual(status, 200, created)
        v_dir = created["work"]["paths"]["videoDeliveryDir"]
        self.studio._write_export_status(v_dir, {
            "jobId": "deadbeef1234",
            "kind": "video",
            "profile": "youtube-shorts",
            "outputDir": v_dir,
            "workId": wid,
            "status": "running",
            "startedAt": "2026-11-13T00:00:00Z",
        })
        self.restart_server()
        status, reopened = self.request("GET", f"/api/works/open?id={wid}")
        self.assertEqual(status, 200, reopened)
        st = reopened["deliveries"]["video"]["lastExportStatus"]
        self.assertIsNotNone(st)
        self.assertEqual(st["status"], "interrupted")

    def test_full_export_restart_reuse_and_failed_reexport(self):
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError("REQUIRE_RENDER=1 mas FFmpeg/FFprobe ausentes")
            raise unittest.SkipTest("FFmpeg/FFprobe indisponiveis")

        pid = "t-proj-e2e"
        wid = "t-work-e2e"
        self.addCleanup(self._cleanup_project, pid)
        self.addCleanup(self._cleanup_work, wid)
        self._cleanup_project(pid)
        self._cleanup_work(wid)

        status, p_res = self.request("POST", "/api/projects/create", {
            "schemaVersion": 1,
            "id": pid,
            "name": "Salao E2E",
            "locale": "pt-BR",
            "timezone": "America/Sao_Paulo",
            "brandTheme": pid,
            "assetRoot": f".workspace/studio/projects/{pid}/assets",
            "contentPolicies": {
                "requireApprovedBriefing": True,
                "requireApprovedScript": True,
                "prohibitPersonalData": True,
                "requireFunctionalEvidence": True,
            },
            "outputProfiles": [
                "instagram-reels-video",
                "facebook-reels-video",
                "youtube-shorts",
                "instagram-feed-image-square",
            ],
        })
        self.assertEqual(status, 200, p_res)

        status, created = self.request("POST", "/api/works/create", {
            "id": wid,
            "name": "Trabalho Completo",
            "project": p_res["path"],
            "template": "blank",
        })
        self.assertEqual(status, 200, created)
        paths = created["work"]["paths"]
        vreq = created["videoRequest"]
        creq = created["carouselRequest"]
        mplan = created["motionPlan"]
        media_hashes_before = {
            m["path"]: render_local.sha256_file(os.path.join(STUDIO_ROOT, m["path"].replace("/", os.sep)))
            for m in vreq["media"]
        }

        # Exporta Video, Carrossel e Motion
        _, jv = self.request("POST", "/api/export", {
            "request": vreq, "outputDir": paths["videoDeliveryDir"],
            "profile": "youtube-shorts", "kind": "video", "workId": wid,
        })
        _, jc = self.request("POST", "/api/export", {
            "request": creq, "outputDir": paths["carouselDeliveryDir"],
            "profile": "instagram-feed-image-square", "kind": "carousel", "workId": wid,
        })
        _, jm = self.request("POST", "/api/export", {
            "request": vreq, "outputDir": paths["motionDeliveryDir"],
            "profile": "instagram-reels-video", "kind": "video",
            "motionPlan": mplan, "workId": wid,
        })
        self.assertEqual(self._poll_job(jv["jobId"])["status"], "completed")
        self.assertEqual(self._poll_job(jc["jobId"])["status"], "completed")
        self.assertEqual(self._poll_job(jm["jobId"])["status"], "completed")

        # Reinicia servidor e verifica reconstrucao completa de rascunhos e entregas
        self.restart_server()
        status, reopened = self.request("GET", f"/api/works/open?id={wid}")
        self.assertEqual(status, 200, reopened)
        self.assertEqual(len(reopened["deliveries"]["video"]["profiles"]), 1)
        self.assertEqual(len(reopened["deliveries"]["motion"]["profiles"]), 1)
        self.assertIsNotNone(reopened["deliveries"]["carousel"]["manifest"])

        # Verifica stream 0 de audio e downloads reais
        st, _, mp4_blob = self._fetch_raw(f"/media?dir={paths['videoDeliveryDir']}&profile=youtube-shorts&kind=video")
        self.assertEqual(st, 200)
        self.assertGreater(len(mp4_blob), 1000)
        st, _, srt_blob = self._fetch_raw(f"/media?dir={paths['videoDeliveryDir']}&profile=youtube-shorts&kind=srt")
        self.assertEqual(st, 200)
        self.assertGreater(len(srt_blob), 5)
        st, _, txt_blob = self._fetch_raw(f"/media?dir={paths['videoDeliveryDir']}&profile=youtube-shorts&kind=narration")
        self.assertEqual(st, 200)
        self.assertGreater(len(txt_blob), 5)
        st, _, zip_blob = self._fetch_raw(f"/media?dir={paths['carouselDeliveryDir']}&kind=zip")
        self.assertEqual(st, 200)
        self.assertEqual(zip_blob[:2], b"PK")

        # Edita titulo/card, reexporta reutilizando exatamente a mesma midia de origem
        vreq["scenes"][0]["title"] = "Titulo Revisado"
        creq["cards"][0]["title"] = "Capa Revisada"
        _, jv2 = self.request("POST", "/api/export", {
            "request": vreq, "outputDir": paths["videoDeliveryDir"],
            "profile": "youtube-shorts", "kind": "video", "workId": wid,
        })
        _, jc2 = self.request("POST", "/api/export", {
            "request": creq, "outputDir": paths["carouselDeliveryDir"],
            "profile": "instagram-feed-image-square", "kind": "carousel", "workId": wid,
        })
        self.assertEqual(self._poll_job(jv2["jobId"])["status"], "completed")
        self.assertEqual(self._poll_job(jc2["jobId"])["status"], "completed")
        for mpath, digest in media_hashes_before.items():
            self.assertEqual(
                render_local.sha256_file(os.path.join(STUDIO_ROOT, mpath.replace("/", os.sep))),
                digest,
                "midia de origem deveria ser reutilizada sem alterar hash",
            )

        # Provoca falha de reexportacao (midia ausente) e reinicia o servidor
        broken_v = json.loads(json.dumps(vreq))
        broken_v["media"][0]["path"] = f".workspace/studio/works/{wid}/media/inexistente.png"
        broken_c = json.loads(json.dumps(creq))
        broken_c["media"][0]["path"] = f".workspace/studio/works/{wid}/media/inexistente.png"
        _, jv_fail = self.request("POST", "/api/export", {
            "request": broken_v, "outputDir": paths["videoDeliveryDir"],
            "profile": "youtube-shorts", "kind": "video",
        })
        _, jc_fail = self.request("POST", "/api/export", {
            "request": broken_c, "outputDir": paths["carouselDeliveryDir"],
            "profile": "instagram-feed-image-square", "kind": "carousel",
        })
        self.assertEqual(self._poll_job(jv_fail["jobId"])["status"], "failed")
        self.assertEqual(self._poll_job(jc_fail["jobId"])["status"], "failed")

        self.restart_server()
        status, after_fail = self.request("GET", f"/api/works/open?id={wid}")
        self.assertEqual(status, 200, after_fail)
        v_del = after_fail["deliveries"]["video"]
        c_del = after_fail["deliveries"]["carousel"]
        self.assertEqual(v_del["lastExportStatus"]["status"], "failed")
        self.assertEqual(c_del["lastExportStatus"]["status"], "failed")
        self.assertEqual(v_del["index"]["profiles"][0]["lastAttempt"]["status"], "failed")
        self.assertIsNotNone(v_del["index"]["profiles"][0]["lastValidDelivery"])
        self.assertEqual(c_del["index"]["lastAttempt"]["status"], "failed")
        self.assertIsNotNone(c_del["index"]["lastValidDelivery"])

        # Ultimas entregas validas seguem servindo normalmente apos reiniciar
        st, _, _ = self._fetch_raw(f"/media?dir={paths['videoDeliveryDir']}&profile=youtube-shorts&kind=video")
        self.assertEqual(st, 200)
        st, _, _ = self._fetch_raw(f"/media?dir={paths['carouselDeliveryDir']}&kind=zip")
        self.assertEqual(st, 200)


if __name__ == "__main__":
    unittest.main()
