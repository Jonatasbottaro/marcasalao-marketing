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
            self.assertTrue(profiles[pid]["localExportVideo"], pid)
            self.assertTrue(profiles[pid]["localExport"]["video"]["supported"], pid)
            self.assertEqual(profiles[pid]["availability"], "allowed")
        # Horizontal habilitado no allowlist deste projeto e suportado pelo adaptador.
        horiz = profiles["youtube-video-horizontal"]
        self.assertEqual(horiz["availability"], "allowed")
        self.assertTrue(horiz["localExportVideo"])
        self.assertEqual((horiz["width"], horiz["height"]), (1920, 1080))
        # Motion permanece apenas no vertical nesta rodada.
        self.assertFalse(horiz["localExportMotion"])
        self.assertEqual(horiz["localExport"]["motion"]["reason"], "MOTION_VERTICAL_ONLY")
        self.assertTrue(profiles["instagram-reels-video"]["localExportMotion"])
        # Retrato 4:5 (1080x1350) habilitado no allowlist deste projeto e suportado pelo adaptador
        # (Operacao Resultado 24: geracao estatica 4:5 nativa, sem resize manual por FFmpeg).
        portrait = profiles["instagram-feed-image-portrait"]
        self.assertEqual(portrait["availability"], "allowed")
        self.assertTrue(portrait["localExportCarousel"])
        self.assertTrue(portrait["localExport"]["carousel"]["supported"])
        self.assertEqual((portrait["width"], portrait["height"]), (1080, 1350))
        # Imagem 9:16 de stories: conhecida, porem sem render local de carrossel.
        stories_img = profiles["instagram-stories-image"]
        self.assertFalse(stories_img["localExport"]["carousel"]["supported"])
        self.assertEqual(stories_img["localExport"]["carousel"]["reason"], "GEOMETRY_UNSUPPORTED")

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

        # Filtragem por modulo (horizontal agora e exportavel em Video; Motion segue 9:16)
        status, v_prof = self.request("GET", f"/api/profiles?project={proj_rel}&module=video")
        self.assertEqual(status, 200)
        v_ids = [p["id"] for p in v_prof["listing"]["compatibleProfiles"]]
        self.assertEqual(set(v_ids), {"instagram-reels-video", "youtube-shorts", "youtube-video-horizontal"})

        status, m_prof = self.request("GET", f"/api/profiles?project={proj_rel}&module=motion")
        self.assertEqual(status, 200)
        m_ids = [p["id"] for p in m_prof["listing"]["compatibleProfiles"]]
        self.assertEqual(set(m_ids), {"instagram-reels-video", "youtube-shorts"})

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


class StudioReviewAndDeliveryPackageTest(StudioTestBase):
    def _cleanup_work(self, wid):
        base = os.path.join(STUDIO_ROOT, ".workspace", "studio", "works", wid)
        if os.path.isdir(render_local.fs_path(base)):
            shutil.rmtree(render_local.fs_path(base, force=True), ignore_errors=True)
        exports_dir = os.path.join(STUDIO_ROOT, ".workspace", "tmp", "video-studio", "exports")
        if os.path.isdir(exports_dir):
            norm_prefix = f".workspace/studio/works/{wid}/deliveries/"
            for name in os.listdir(exports_dir):
                fpath = os.path.join(exports_dir, name)
                if not name.endswith(".json"):
                    continue
                try:
                    data = read_json(fpath)
                except (OSError, ValueError):
                    continue
                if str(data.get("outputDir", "")).startswith(norm_prefix) or data.get("workId") == wid:
                    os.remove(fpath)

    def _poll_job(self, job_id, timeout=180):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            _, data = self.request("GET", f"/api/export/status?job={job_id}")
            if data["status"] != "running":
                return data
            time.sleep(0.5)
        raise AssertionError(f"job {job_id} excedeu timeout")

    def _fetch_raw(self, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        conn.request("GET", path, headers={"Host": self.host})
        res = conn.getresponse()
        blob = res.read()
        ctype = res.getheader("Content-Type")
        conn.close()
        return res.status, ctype, blob

    def test_legacy_work_opens_cleanly_and_flags_unlinked(self):
        wid = "t-rev-legacy"
        self.addCleanup(self._cleanup_work, wid)
        self._cleanup_work(wid)

        st, created = self.request("POST", "/api/works/create", {
            "id": wid,
            "name": "Trabalho Legado Sem Ficha",
            "project": PROJECT_MS,
            "template": "blank",
        })
        self.assertEqual(st, 200, created)

        # Simula work.json legado (sem editorialFile, reviewStateFile, packageDeliveryDir)
        work_file = os.path.join(STUDIO_ROOT, ".workspace", "studio", "works", wid, "work.json")
        wdoc = read_json(work_file)
        for k in ("editorialFile", "reviewStateFile", "packageDeliveryDir"):
            wdoc["paths"].pop(k, None)
        with open(render_local.fs_path(work_file), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(wdoc, handle, ensure_ascii=False, indent=2)

        # Promove uma entrega de carrossel diretamente via CLI fora do Studio (sem review-state.json)
        creq_path = os.path.join(STUDIO_ROOT, created["work"]["paths"]["carouselDraft"].replace("/", os.sep))
        c_out = os.path.join(STUDIO_ROOT, created["work"]["paths"]["carouselDeliveryDir"].replace("/", os.sep))
        proc = subprocess.run(
            [sys.executable, os.path.join(STUDIO_ROOT, "tools", "produce_carousel.py"),
             "--input", creq_path, "--root", STUDIO_ROOT, "--output-dir", c_out, "--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + "\n" + proc.stderr)

        st, reopened = self.request("GET", f"/api/works/open?id={wid}")
        self.assertEqual(st, 200, reopened)
        rev = reopened["review"]
        self.assertTrue(rev["legacyWork"])
        self.assertFalse(rev["editorial"]["existsOnDisk"])
        self.assertEqual(rev["editorial"]["briefing"]["objective"], "")
        c_piece = next(p for p in rev["pieces"] if p["modality"] == "carousel")
        self.assertEqual(c_piece["status"], "unlinked")
        self.assertFalse(c_piece["readyForPackage"])
        self.assertIn("vinculo", c_piece["unlinkedReason"].lower())

        # Aprovar peca nao vinculada exige reexportacao; solicitar ajuste funciona
        st, blk = self.request("POST", "/api/works/review/decide", {
            "workId": wid,
            "targetType": "piece",
            "modality": "carousel",
            "profileId": c_piece["profileId"],
            "decision": "approved_for_local_delivery",
            "note": "tentativa",
        })
        self.assertEqual(st, 400, blk)

        st, adj = self.request("POST", "/api/works/review/decide", {
            "workId": wid,
            "targetType": "piece",
            "modality": "carousel",
            "profileId": c_piece["profileId"],
            "decision": "changes_requested",
            "note": "Reexportar pelo Studio para vincular.",
        })
        self.assertEqual(st, 200, adj)

        st, pkg_err = self.request("POST", "/api/works/package", {
            "workId": wid,
            "pieces": [{"modality": "carousel", "profileId": c_piece["profileId"]}],
            "channels": [],
        })
        self.assertEqual(st, 400, pkg_err)

    def test_review_workflow_localized_changes_history_failures_and_zip(self):
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError("REQUIRE_RENDER=1 mas FFmpeg/FFprobe ausentes")
            raise unittest.SkipTest("FFmpeg/FFprobe indisponiveis")

        import delivery_package
        import studio_review

        wid = "t-rev-full"
        self.addCleanup(self._cleanup_work, wid)
        self._cleanup_work(wid)

        st, created = self.request("POST", "/api/works/create", {
            "id": wid,
            "name": "Campanha Revisao Completa",
            "project": PROJECT_MS,
            "template": "blank",
        })
        self.assertEqual(st, 200, created)
        paths = created["work"]["paths"]
        vreq = created["videoRequest"]
        vreq["profiles"] = ["youtube-shorts", "instagram-reels-video"]
        creq = created["carouselRequest"]
        mplan = created["motionPlan"]

        # Exporta Video em 2 perfis (incluindo instagram-reels-video) + Motion em instagram-reels-video + Carrossel
        _, jv_yt = self.request("POST", "/api/export", {
            "request": vreq, "outputDir": paths["videoDeliveryDir"],
            "profile": "youtube-shorts", "kind": "video", "workId": wid,
        })
        _, jv_ig = self.request("POST", "/api/export", {
            "request": vreq, "outputDir": paths["videoDeliveryDir"],
            "profile": "instagram-reels-video", "kind": "video", "workId": wid,
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
        self.assertEqual(self._poll_job(jv_yt["jobId"])["status"], "completed")
        self.assertEqual(self._poll_job(jv_ig["jobId"])["status"], "completed")
        self.assertEqual(self._poll_job(jc["jobId"])["status"], "completed")
        self.assertEqual(self._poll_job(jm["jobId"])["status"], "completed")

        # Bloqueio de Origin nas rotas novas de escrita
        st_ori, _ = self.request("POST", "/api/works/editorial/save", {
            "workId": wid, "briefing": {"objective": "bloqueado"},
        }, origin="http://evil.example")
        self.assertEqual(st_ori, 403)

        # Inspecao de SRT e narracao separados
        st, srt_doc = self.request(
            "GET",
            f"/api/works/artifact-text?id={wid}&modality=video&profile=youtube-shorts&kind=srt",
        )
        self.assertEqual(st, 200, srt_doc)
        self.assertIn("-->", srt_doc["content"])
        st, nar_doc = self.request(
            "GET",
            f"/api/works/artifact-text?id={wid}&modality=motion&profile=instagram-reels-video&kind=narration",
        )
        self.assertEqual(st, 200, nar_doc)
        self.assertIn("narracao", nar_doc["content"].lower())

        # Estado inicial pos-render: todas as pecas pendentes (render tecnico != aprovacao editorial)
        st, rev = self.request("GET", f"/api/works/review?id={wid}")
        self.assertEqual(st, 200, rev)
        self.assertEqual(len(rev["pieces"]), 4)
        for p in rev["pieces"]:
            self.assertEqual(p["status"], "pending_review")
            self.assertFalse(p["readyForPackage"])
            self.assertTrue(p["linked"])

        # Tentar empacotar antes de aprovar falha com bloqueio claro
        st, blk_pkg = self.request("POST", "/api/works/package", {
            "workId": wid,
            "pieces": [{"modality": "video", "profileId": "youtube-shorts"}],
            "channels": [],
        })
        self.assertEqual(st, 400, blk_pkg)

        # Salva ficha editorial e textos por canal para os 3 perfis selecionados
        channels_payload = {
            "youtube-shorts": {
                "title": "Agenda sem furos no salao",
                "postText": "Confira o sistema no link da descricao: https://marcasalao.com.br",
                "cta": "Acesse o link da descricao",
                "destinationUrl": "https://marcasalao.com.br",
                "hashtags": "#MarcaSalao #Shorts",
            },
            "instagram-reels-video": {
                "title": "",
                "postText": "Organize atendimentos e horarios em um so lugar.",
                "cta": "Acesse o link na bio",
                "destinationUrl": "https://marcasalao.com.br",
                "hashtags": "#MarcaSalao #Reels",
            },
            "instagram-feed-image-square": {
                "title": "",
                "postText": "Carrossel completo com destaques do Marca Salao.",
                "cta": "Acesse o link na bio",
                "destinationUrl": "https://marcasalao.com.br",
                "hashtags": "#MarcaSalao #Feed",
            },
        }
        st, rev = self.request("POST", "/api/works/editorial/save", {
            "workId": wid,
            "briefing": {
                "objective": "Apresentar agenda organizada para saloes",
                "audience": "Donos de saloes de beleza",
                "coreMessage": "Agenda clara reduz faltas",
                "supportEvidence": "Demonstracao visual com horarios organizados",
                "hook": "Chega de horario perdido no caderno",
                "scriptSummary": "Cena 1 apresenta o sistema; Cena 2 destaca a agenda.",
                "cta": "Conheca o Marca Salao",
            },
            "channels": channels_payload,
        })
        self.assertEqual(st, 200, rev)

        yt_piece = next(p for p in rev["pieces"] if p["pieceKey"] == "video:youtube-shorts")
        yt_mp4_sha_v1 = yt_piece["metrics"]["videoSha256"]
        yt_ch = next(c for c in rev["channels"] if c["profileId"] == "youtube-shorts")

        # Teste de concorrencia otimista (HTTP 409)
        st_409, d409 = self.request("POST", "/api/works/review/decide", {
            "workId": wid,
            "targetType": "piece",
            "modality": "video",
            "profileId": "youtube-shorts",
            "expectedVersionId": "versao-obsoleta",
            "decision": "approved_for_local_delivery",
        })
        self.assertEqual(st_409, 409, d409)
        self.assertTrue(d409.get("conflict"))

        st_c409, dc409 = self.request("POST", "/api/works/review/decide", {
            "workId": wid,
            "targetType": "channel",
            "profileId": "youtube-shorts",
            "expectedCopySha256": "deadbeef",
            "decision": "approved_for_local_delivery",
        })
        self.assertEqual(st_c409, 409, dc409)

        # Aprova todas as pecas e todos os textos de canal
        for p in rev["pieces"]:
            st, rev = self.request("POST", "/api/works/review/decide", {
                "workId": wid,
                "targetType": "piece",
                "modality": p["modality"],
                "profileId": p["profileId"],
                "expectedVersionId": p["deliveryVersionId"],
                "expectedDraftFingerprint": p["currentDraftFingerprint"],
                "decision": "approved_for_local_delivery",
                "note": f"Aprovado {p['pieceKey']}",
            })
            self.assertEqual(st, 200, rev)

        for c in rev["channels"]:
            st, rev = self.request("POST", "/api/works/review/decide", {
                "workId": wid,
                "targetType": "channel",
                "profileId": c["profileId"],
                "expectedCopySha256": c["copySha256"],
                "decision": "approved_for_local_delivery",
                "note": f"Texto ok {c['profileId']}",
            })
            self.assertEqual(st, 200, rev)

        # Monta pacote ZIP v1 com Video + Motion (mesmo destino instagram-reels-video!), Carrossel e textos
        sel_pieces = [
            {
                "modality": p["modality"],
                "profileId": p["profileId"],
                "expectedVersionId": p["deliveryVersionId"],
                "expectedDraftFingerprint": p["currentDraftFingerprint"],
            }
            for p in rev["pieces"]
        ]
        sel_channels = [
            {"profileId": c["profileId"], "expectedCopySha256": c["copySha256"]}
            for c in rev["channels"]
        ]
        st, pkg_res = self.request("POST", "/api/works/package", {
            "workId": wid, "pieces": sel_pieces, "channels": sel_channels,
        })
        self.assertEqual(st, 200, pkg_res)
        pkg = pkg_res["packageDelivery"]
        self.assertTrue(pkg["available"])
        zip_v1_sha = pkg["lastValidDelivery"]["zipSha256"]

        # Download autentico do ZIP + auditoria completa do arquivo
        st_dl, ctype, zip_bytes = self._fetch_raw(f"/api/works/package/download?id={wid}")
        self.assertEqual(st_dl, 200)
        self.assertEqual(ctype, "application/zip")
        self.assertEqual(delivery_package._sha256_bytes(zip_bytes), zip_v1_sha)

        zip_disk = os.path.join(STUDIO_ROOT, pkg["lastValidDelivery"]["zipPath"].replace("/", os.sep))
        with zipfile.ZipFile(render_local.fs_path(zip_disk), "r") as zf:
            names = zf.namelist()
            self.assertIn("package-manifest.json", names)
            self.assertIn("briefing/ficha-editorial.json", names)
            self.assertIn("briefing/ficha-editorial.txt", names)
            for pid in ("youtube-shorts", "instagram-reels-video", "instagram-feed-image-square"):
                self.assertIn(f"textos-por-canal/{pid}/publicacao.json", names)
                self.assertIn(f"textos-por-canal/{pid}/publicacao.txt", names)
            # Video e Motion para instagram-reels-video em pastas separadas sem colisao
            self.assertTrue(any(n.startswith("video/instagram-reels-video/") and n.endswith(".mp4") for n in names))
            self.assertTrue(any(n.startswith("motion/instagram-reels-video/") and n.endswith(".mp4") for n in names))
            self.assertTrue(any(n.startswith("video/youtube-shorts/") and n.endswith(".srt") for n in names))
            p_man = json.loads(zf.read("package-manifest.json").decode("utf-8"))
            self.assertEqual(set(p_man["modalities"]), {"video", "carousel", "motion"})
            car_entry = next(x for x in p_man["pieces"] if x["modality"] == "carousel")
            car_zip_names = [n for n in names if n.startswith("carousel/instagram-feed-image-square/")]
            self.assertEqual(
                car_zip_names,
                [f"carousel/instagram-feed-image-square/{fn}" for fn in car_entry["cardOrder"]],
            )

            # FFprobe confirma 0 stream de audio nos MP4s empacotados
            extract_dir = os.path.join(STUDIO_ROOT, ".workspace", "tmp", "t_pkg_ffprobe")
            shutil.rmtree(extract_dir, ignore_errors=True)
            os.makedirs(extract_dir, exist_ok=True)
            self.addCleanup(shutil.rmtree, extract_dir, True)
            for idx, mp4_name in enumerate([n for n in names if n.endswith(".mp4")]):
                out_mp4 = os.path.join(extract_dir, f"probe-{idx}.mp4")
                with open(out_mp4, "wb") as handle:
                    handle.write(zf.read(mp4_name))
                probe = json.loads(subprocess.check_output(
                    ["ffprobe", "-v", "error", "-show_streams", "-of", "json", out_mp4],
                    text=True, encoding="utf-8", errors="replace",
                ))
                self.assertEqual(
                    sum(1 for s in probe["streams"] if s.get("codec_type") == "audio"), 0, mp4_name
                )

        # Alteracao SOMENTE do texto de publicacao de youtube-shorts
        st, rev_after_copy = self.request("POST", "/api/works/editorial/save", {
            "workId": wid,
            "channels": {
                "youtube-shorts": {
                    **channels_payload["youtube-shorts"],
                    "postText": "Novo texto somente no canal YouTube Shorts: https://marcasalao.com.br",
                }
            },
        })
        self.assertEqual(st, 200, rev_after_copy)
        ch_map = {c["profileId"]: c for c in rev_after_copy["channels"]}
        p_map = {p["pieceKey"]: p for p in rev_after_copy["pieces"]}
        self.assertEqual(ch_map["youtube-shorts"]["status"], "copy_outdated")
        self.assertEqual(ch_map["instagram-reels-video"]["status"], "approved")
        self.assertEqual(ch_map["instagram-feed-image-square"]["status"], "approved")
        self.assertEqual(p_map["video:youtube-shorts"]["status"], "approved")
        self.assertEqual(p_map["video:youtube-shorts"]["metrics"]["videoSha256"], yt_mp4_sha_v1)

        # Pacote rejeitado com canal desatualizado (preserva ZIP anterior) e liberado apos reaprovar apenas esse canal
        st_blk, _ = self.request("POST", "/api/works/package", {
            "workId": wid,
            "pieces": [{"modality": "video", "profileId": "youtube-shorts"}],
            "channels": [{"profileId": "youtube-shorts"}],
        })
        self.assertEqual(st_blk, 400)
        st, rev_reapproved_ch = self.request("POST", "/api/works/review/decide", {
            "workId": wid,
            "targetType": "channel",
            "profileId": "youtube-shorts",
            "expectedCopySha256": ch_map["youtube-shorts"]["copySha256"],
            "decision": "approved_for_local_delivery",
            "note": "Copy revisado",
        })
        self.assertEqual(st, 200, rev_reapproved_ch)

        # Alteracao em MotionPlan invalida APENAS Motion; alteracao no VideoRequest invalida Video + Motion (nao Carrossel)
        mplan_edited = json.loads(json.dumps(mplan))
        mplan_edited["effects"][0]["color"] = "#00FF88"
        st, _ = self.request("POST", "/api/works/save", {"workId": wid, "motionPlan": mplan_edited})
        self.assertEqual(st, 200)
        _, rev_m = self.request("GET", f"/api/works/review?id={wid}")
        pm = {p["pieceKey"]: p for p in rev_m["pieces"]}
        self.assertEqual(pm["motion:instagram-reels-video"]["status"], "draft_outdated")
        self.assertEqual(pm["video:youtube-shorts"]["status"], "approved")
        self.assertEqual(pm["carousel:instagram-feed-image-square"]["status"], "approved")

        # Reexporta Motion e confirma decisao antiga vinculada a v1 no historico + v2 pendente de revisao
        old_motion_ver = pm["motion:instagram-reels-video"]["deliveryVersionId"]
        _, jm2 = self.request("POST", "/api/export", {
            "request": vreq, "outputDir": paths["motionDeliveryDir"],
            "profile": "instagram-reels-video", "kind": "video",
            "motionPlan": mplan_edited, "workId": wid,
        })
        self.assertEqual(self._poll_job(jm2["jobId"])["status"], "completed")
        _, rev_m2 = self.request("GET", f"/api/works/review?id={wid}")
        pm2 = {p["pieceKey"]: p for p in rev_m2["pieces"]}
        motion_p2 = pm2["motion:instagram-reels-video"]
        self.assertEqual(motion_p2["status"], "reexported_pending")
        self.assertNotEqual(motion_p2["deliveryVersionId"], old_motion_ver)
        self.assertEqual(motion_p2["decisionHistory"][-1]["deliveryVersionId"], old_motion_ver)
        self.assertEqual(motion_p2["decisionHistory"][-1]["decision"], "approved_for_local_delivery")

        # Simula falha na promocao (os.replace) do novo ZIP e verifica ZIP anterior intacto
        orig_promote = render_local.promote_with_backup
        def fail_promote(staging_paths, dests, backup_dir):
            raise OSError("falha simulada na promocao do ZIP")
        render_local.promote_with_backup = fail_promote
        try:
            st_fail_pkg, _ = self.request("POST", "/api/works/package", {
                "workId": wid,
                "pieces": [{"modality": "carousel", "profileId": "instagram-feed-image-square"}],
                "channels": [],
            })
            self.assertEqual(st_fail_pkg, 400)
        finally:
            render_local.promote_with_backup = orig_promote

        # Falha de reexportacao de video + reinicio do servidor preserva aviso, decisao v1, lastValidDelivery e ZIP v1
        broken_v = json.loads(json.dumps(vreq))
        broken_v["media"][0]["path"] = f".workspace/studio/works/{wid}/media/ausente.png"
        _, jv_fail = self.request("POST", "/api/export", {
            "request": broken_v, "outputDir": paths["videoDeliveryDir"],
            "profile": "youtube-shorts", "kind": "video",
        })
        self.assertEqual(self._poll_job(jv_fail["jobId"])["status"], "failed")

        self.restart_server()
        st_open, after_restart = self.request("GET", f"/api/works/open?id={wid}")
        self.assertEqual(st_open, 200, after_restart)
        after_map = {p["pieceKey"]: p for p in after_restart["review"]["pieces"]}
        self.assertEqual(after_map["video:youtube-shorts"]["lastAttempt"]["status"], "failed")
        self.assertIsNotNone(after_map["video:youtube-shorts"]["lastValidDelivery"])
        self.assertEqual(after_map["video:youtube-shorts"]["decisionHistory"][-1]["decision"], "approved_for_local_delivery")
        self.assertTrue(after_restart["packageDelivery"]["available"])
        self.assertEqual(after_restart["packageDelivery"]["lastValidDelivery"]["zipSha256"], zip_v1_sha)
        st_dl2, _, zip_bytes2 = self._fetch_raw(f"/api/works/package/download?id={wid}")
        self.assertEqual(st_dl2, 200)
        self.assertEqual(delivery_package._sha256_bytes(zip_bytes2), zip_v1_sha)

        # Corromper card do carrossel torna indisponivel e bloqueia novo ZIP sem destruir ZIP anterior
        c_manifest_abs = os.path.join(STUDIO_ROOT, paths["carouselDeliveryDir"].replace("/", os.sep), "carousel-manifest.json")
        c_man = read_json(c_manifest_abs)
        card0_abs = os.path.join(STUDIO_ROOT, c_man["cards"][0]["path"].replace("/", os.sep))
        with open(render_local.fs_path(card0_abs), "ab") as handle:
            handle.write(b"CORRUPT")
        _, rev_corrupt = self.request("GET", f"/api/works/review?id={wid}")
        corrupt_car = next(p for p in rev_corrupt["pieces"] if p["modality"] == "carousel")
        self.assertEqual(corrupt_car["status"], "unavailable")
        self.assertTrue(corrupt_car["integrityErrors"])
        st_cor_pkg, _ = self.request("POST", "/api/works/package", {
            "workId": wid,
            "pieces": [{"modality": "carousel", "profileId": "instagram-feed-image-square"}],
            "channels": [],
        })
        self.assertEqual(st_cor_pkg, 400)
        st_dl3, _, _ = self._fetch_raw(f"/api/works/package/download?id={wid}")
        self.assertEqual(st_dl3, 200)

    def test_second_project_multitrack_hub_review_and_package(self):
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError("REQUIRE_RENDER=1 mas FFmpeg/FFprobe ausentes")
            raise unittest.SkipTest("FFmpeg/FFprobe indisponiveis")

        wid = "t-rev-mth"
        self.addCleanup(self._cleanup_work, wid)
        self._cleanup_work(wid)

        st, created = self.request("POST", "/api/works/create", {
            "id": wid,
            "name": "Multitrack Hub Revisao",
            "project": "platform/examples/projects/multitrack-hub-social.project.json",
            "template": "multitrack-hub",
        })
        self.assertEqual(st, 200, created)
        paths = created["work"]["paths"]
        creq = created["carouselRequest"]

        _, jc = self.request("POST", "/api/export", {
            "request": creq, "outputDir": paths["carouselDeliveryDir"],
            "profile": creq["profile"], "kind": "carousel", "workId": wid,
        })
        self.assertEqual(self._poll_job(jc["jobId"])["status"], "completed")

        st, rev = self.request("POST", "/api/works/editorial/save", {
            "workId": wid,
            "briefing": {
                "objective": "Divulgar catalogo organizado do Multitrack Hub",
                "audience": "Ministerios e equipes tecnicas de audio",
                "coreMessage": "Busque, compare e encontre multitracks sem perda de tempo",
                "cta": "Acesse multitrackhub.com.br",
            },
            "channels": {
                creq["profile"]: {
                    "postText": "Catalogo completo em https://multitrackhub.com.br",
                    "cta": "Acesse pelo link da bio",
                    "destinationUrl": "https://multitrackhub.com.br",
                }
            },
        })
        self.assertEqual(st, 200, rev)
        car = next(p for p in rev["pieces"] if p["modality"] == "carousel")
        ch = next(c for c in rev["channels"] if c["profileId"] == creq["profile"])
        st, rev = self.request("POST", "/api/works/review/decide", {
            "workId": wid, "targetType": "piece", "modality": "carousel",
            "profileId": car["profileId"], "expectedVersionId": car["deliveryVersionId"],
            "expectedDraftFingerprint": car["currentDraftFingerprint"],
            "decision": "approved_for_local_delivery", "note": "MTH ok",
        })
        self.assertEqual(st, 200, rev)
        st, rev = self.request("POST", "/api/works/review/decide", {
            "workId": wid, "targetType": "channel", "profileId": ch["profileId"],
            "expectedCopySha256": ch["copySha256"],
            "decision": "approved_for_local_delivery", "note": "Copy MTH ok",
        })
        self.assertEqual(st, 200, rev)

        st, pkg_res = self.request("POST", "/api/works/package", {
            "workId": wid,
            "pieces": [{"modality": "carousel", "profileId": car["profileId"]}],
            "channels": [{"profileId": ch["profileId"]}],
        })
        self.assertEqual(st, 200, pkg_res)
        self.assertEqual(pkg_res["packageDelivery"]["manifest"]["projectId"], "multitrack-hub")
        self.assertTrue(pkg_res["packageDelivery"]["available"])


class _MockLLMServer:
    """Servidor HTTP local /v1/chat/completions em processo para testes deterministas."""

    def __init__(self, handler_fn):
        self.requests = []
        outer = self

        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length) if length else b"{}"
                payload = json.loads(raw.decode("utf-8"))
                outer.requests.append({"path": self.path, "payload": payload})
                code, resp_obj = handler_fn(self.path, payload, len(outer.requests))
                if isinstance(resp_obj, bytes):
                    body = resp_obj
                else:
                    body = json.dumps(resp_obj, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.endpoint = f"http://127.0.0.1:{self.port}/v1/chat/completions"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class StudioPlanningAndLLMAdapterTest(StudioReviewAndDeliveryPackageTest):
    PROJECT_MTH = "platform/examples/projects/multitrack-hub-social.project.json"

    def _backup_llm_config(self):
        cfg_path = os.path.join(STUDIO_ROOT, ".workspace", "studio", "llm-config.json")
        existed = os.path.isfile(cfg_path)
        prev = None
        if existed:
            with open(cfg_path, "rb") as handle:
                prev = handle.read()

        def restore():
            if existed:
                with open(cfg_path, "wb") as handle:
                    handle.write(prev)
            elif os.path.isfile(cfg_path):
                os.remove(cfg_path)

        self.addCleanup(restore)

    def _cleanup_project(self, pid):
        pfile = os.path.join(STUDIO_ROOT, ".workspace", "studio", "projects", f"{pid}.project.json")
        pdir = os.path.join(STUDIO_ROOT, ".workspace", "studio", "projects", pid)
        if os.path.isfile(pfile):
            os.remove(pfile)
        if os.path.isdir(pdir):
            shutil.rmtree(render_local.fs_path(pdir, force=True), ignore_errors=True)

    def _create_work_with_media(self, wid, project=PROJECT_MS, template="blank"):
        self.addCleanup(self._cleanup_work, wid)
        self._cleanup_work(wid)
        st, created = self.request("POST", "/api/works/create", {
            "id": wid,
            "name": f"Trabalho {wid}",
            "project": project,
            "template": template,
        })
        self.assertEqual(st, 200, created)
        media_dir = created["work"]["paths"]["mediaDir"]
        st_m, gen = self.request("POST", "/api/media/generate", {
            "request": {
                "schemaVersion": 1,
                "id": f"{wid}-media-gen",
                "project": project,
                "title": "Media base",
                "locale": "pt-BR",
                "profiles": [created["listing"]["profiles"][0]["id"]],
                "media": [
                    {"id": "img-capa", "path": f"{media_dir}/img-capa.png", "type": "image", "origin": "studio-test", "license": "proprietary"},
                    {"id": "img-prova", "path": f"{media_dir}/img-prova.png", "type": "image", "origin": "studio-test", "license": "proprietary"},
                ],
                "scenes": [
                    {"id": "s1", "durationMs": 2000, "mediaId": "img-capa", "caption": "S1", "narration": "S1", "narrativeFunction": "hook", "motionIntent": "none"},
                    {"id": "s2", "durationMs": 2000, "mediaId": "img-prova", "caption": "S2", "narration": "S2", "narrativeFunction": "proof", "motionIntent": "none"},
                ],
            }
        })
        self.assertEqual(st_m, 200, gen)
        _, reopened = self.request("GET", f"/api/works/open?id={wid}")
        return reopened

    def test_manual_planning_multi_brand_isolation_and_legacy_work(self):
        self._backup_llm_config()
        st_cfg, cfg_res = self.request("GET", "/api/llm/config")
        self.assertEqual(st_cfg, 200, cfg_res)
        self.assertFalse(cfg_res["llmConfig"]["enabled"])
        self.assertEqual(cfg_res["llmConfig"]["model"], "qwen3:8b")
        # Geracao de imagem agora existe na biblioteca de midia, por acao confirmada;
        # o adaptador de texto local continua desligado por padrao.
        self.assertTrue(cfg_res["imageExtensionPoint"]["supportsExternalGeneration"])
        self.assertEqual(cfg_res["imageExtensionPoint"]["providerId"], "media-library")

        # Legado sem planningFile ou planning.json abre limpo sem migrar forcadamente
        wid_legacy = "t-plan-legacy"
        self.addCleanup(self._cleanup_work, wid_legacy)
        self._cleanup_work(wid_legacy)
        st, _ = self.request("POST", "/api/works/create", {
            "id": wid_legacy, "name": "Legado Planejamento", "project": PROJECT_MS, "template": "blank",
        })
        self.assertEqual(st, 200)
        wfile = os.path.join(STUDIO_ROOT, ".workspace", "studio", "works", wid_legacy, "work.json")
        wdoc = read_json(wfile)
        wdoc["paths"].pop("planningFile", None)
        with open(render_local.fs_path(wfile), "w", encoding="utf-8", newline="\n") as h:
            json.dump(wdoc, h, ensure_ascii=False, indent=2)
        st_open, leg_open = self.request("GET", f"/api/works/open?id={wid_legacy}")
        self.assertEqual(st_open, 200, leg_open)
        self.assertEqual(len(leg_open["planning"]["planning"]["questions"]), 8)

        # Dois trabalhos de marcas distintas + projeto restrito para isolar allowlist
        w_ms = self._create_work_with_media("t-plan-ms", PROJECT_MS)
        w_mth = self._create_work_with_media("t-plan-mth", self.PROJECT_MTH)
        ms_profiles = {p["id"] for p in w_ms["planning"]["allowedProfiles"]}
        mth_profiles = {p["id"] for p in w_mth["planning"]["allowedProfiles"]}
        ms_expected = {
            p["id"] for p in w_ms["listing"]["profiles"]
            if p.get("availability") == "allowed" and (p.get("localExportVideo") or p.get("localExportCarousel") or p.get("localExportMotion"))
        }
        mth_expected = {
            p["id"] for p in w_mth["listing"]["profiles"]
            if p.get("availability") == "allowed" and (p.get("localExportVideo") or p.get("localExportCarousel") or p.get("localExportMotion"))
        }
        self.assertEqual(ms_profiles, ms_expected)
        self.assertEqual(mth_profiles, mth_expected)
        self.assertIn("youtube-shorts", ms_profiles)

        restricted_proj_rel = ".workspace/studio/projects/t-plan-restricted.project.json"
        self.addCleanup(self._cleanup_project, "t-plan-restricted")
        self._cleanup_project("t-plan-restricted")
        st_rp, rp_res = self.request("POST", "/api/projects/create", {
            "schemaVersion": 1,
            "id": "t-plan-restricted",
            "name": "Projeto Somente Quadrado",
            "locale": "pt-BR",
            "timezone": "America/Sao_Paulo",
            "brandTheme": "t-plan-restricted",
            "assetRoot": ".workspace/studio/projects/t-plan-restricted/assets",
            "contentPolicies": {
                "requireApprovedBriefing": True,
                "requireApprovedScript": True,
                "prohibitPersonalData": True,
                "requireFunctionalEvidence": True,
            },
            "outputProfiles": ["instagram-feed-image-square"],
        })
        self.assertEqual(st_rp, 200, rp_res)
        w_res = self._create_work_with_media("t-plan-rest", restricted_proj_rel)
        rest_profiles = {p["id"] for p in w_res["planning"]["allowedProfiles"]}
        self.assertEqual(rest_profiles, {"instagram-feed-image-square"})
        self.assertNotIn("youtube-shorts", rest_profiles)

        # Marca Salao: texto com afirmacao nao comprovada e proibida gera alerta claro
        st_ms, ov_ms = self.request("POST", "/api/works/planning/save", {
            "workId": "t-plan-ms",
            "ideaText": "Mostrar agenda confirmada sem depender de mensagem automatica ou lembrete no WhatsApp.",
            "briefing": {
                "objective": "Ensinar a conferir horarios no Marca Salao",
                "audience": "Donos de salao",
                "coreMessage": "Agenda visual evita conflitos de horario",
                "supportEvidence": "Tela real de agenda do salao",
                "cta": "Conheca o Marca Salao",
            },
            "briefingExtended": {"product": "Marca Salao", "tone": "Direto"},
            "claims": [
                {"id": "c-1", "statement": "Envio automatico de lembrete reduz falta em 100%", "status": "hypothesis", "evidenceMediaId": "img-prova"},
            ],
        })
        self.assertEqual(st_ms, 200, ov_ms)
        joined_warn = " ".join(ov_ms["analysis"]["warnings"]).lower()
        self.assertIn("marca salao", joined_warn)
        self.assertTrue(ov_ms["planning"]["claims"][0]["requiresConfirmation"])

        # Multitrack Hub nao sofre contaminacao com dados do Marca Salao
        st_mth, ov_mth = self.request("POST", "/api/works/planning/save", {
            "workId": "t-plan-mth",
            "ideaText": "Catalogo organizado por tom e BPM para bandas.",
            "briefing": {
                "objective": "Levar bandas ao catalogo Multitrack Hub",
                "audience": "Equipes de louvor e audio",
                "coreMessage": "Encontre multitracks organizadas em segundos",
                "supportEvidence": "Busca do catalogo multitrackhub.com.br",
                "cta": "Acesse multitrackhub.com.br",
            },
            "briefingExtended": {"product": "Multitrack Hub", "tone": "Pratico"},
        })
        self.assertEqual(st_mth, 200, ov_mth)
        self.assertNotEqual(ov_mth["work"]["id"], ov_ms["work"]["id"])
        self.assertNotIn("Marca Salao", json.dumps(ov_mth["planning"], ensure_ascii=False))

    def test_copy_import_prompts_validation_diff_and_error_diagnostics(self):
        self._backup_llm_config()
        wid = "t-plan-import"
        self._create_work_with_media(wid, PROJECT_MS)

        # Prompt Etapa 1 tem apenas contexto de briefing/lacunas
        st_p1, p1 = self.request("POST", "/api/works/planning/prompt", {"workId": wid, "stage": "briefing"})
        self.assertEqual(st_p1, 200, p1)
        self.assertEqual(p1["stage"], "briefing")
        self.assertIn("PlanningSuggestion v1", p1["promptText"])
        self.assertNotIn("carouselCards", p1["promptText"])

        # Salva resposta do operador para preservar no aceite
        st_sv, ov_sv = self.request("POST", "/api/works/planning/save", {
            "workId": wid,
            "ideaText": "Video curto sobre horarios do salao",
            "questions": [{"dimension": "audience", "question": "Quem assiste?", "answer": "Donos e recepcao de salao"}],
        })
        self.assertEqual(st_sv, 200, ov_sv)

        # Rejeicoes com diagnostico em portugues
        bad_payloads = [
            ({"workId": wid, "stage": "briefing", "rawText": "nao eh json"}, 400, None),
            ({"workId": wid, "stage": "briefing", "rawText": json.dumps({"schemaVersion": 1, "stage": "creative", "hookOptions": [{"id": "h1", "text": "t", "angle": "a"}], "selectedHookId": "h1", "scriptSummary": "s", "videoScenes": [], "carouselCards": [], "channelCopies": []})}, 400, "PLANNING_STAGE_MISMATCH"),
            ({"workId": wid, "stage": "briefing", "rawText": json.dumps({"schemaVersion": 1, "stage": "briefing", "product": "P", "audience": "A", "objective": "O", "coreMessage": "M", "supportEvidence": "E", "cta": "C", "tone": "T", "recommendedProfiles": ["tiktok-proibido"], "gaps": [], "questions": [], "claims": []})}, 400, "PLANNING_PROFILE_NOT_ALLOWED"),
            ({"workId": wid, "stage": "briefing", "rawText": json.dumps({"schemaVersion": 1, "stage": "briefing", "product": "P", "audience": "A", "objective": "O", "coreMessage": "M", "supportEvidence": "E", "cta": "C", "tone": "T", "recommendedProfiles": ["youtube-shorts"], "gaps": [], "questions": [], "claims": [], "extraProibido": 1})}, 400, None),
            ({"workId": wid, "stage": "creative", "rawText": json.dumps({"schemaVersion": 1, "stage": "creative", "hookOptions": [{"id": "h1", "text": "Hook 1", "angle": "dor"}], "selectedHookId": "hook-inexistente", "scriptSummary": "Resumo", "videoScenes": [], "carouselCards": [], "channelCopies": []})}, 400, "PLANNING_SELECTED_HOOK_UNKNOWN"),
        ]
        for payload, expected_st, expected_fc in bad_payloads:
            st_bad, d_bad = self.request("POST", "/api/works/planning/import", payload)
            self.assertEqual(st_bad, expected_st, d_bad)
            if expected_fc:
                self.assertEqual(d_bad.get("failureCode"), expected_fc, d_bad)

        # Importacao valida com markdown ```json``` e diferenca previa
        sug_b = {
            "schemaVersion": 1,
            "stage": "briefing",
            "product": "Marca Salao",
            "audience": "Profissionais de beleza",
            "objective": "Simplificar consulta de horarios",
            "coreMessage": "Visualize horarios sem caderno",
            "supportEvidence": "Captura real da tela de agenda",
            "cta": "Conheca o Marca Salao",
            "tone": "Direto",
            "recommendedProfiles": ["youtube-shorts", "instagram-feed-image-square"],
            "gaps": [],
            "questions": [
                {"id": "q-audience", "dimension": "audience", "question": "Quem?", "suggestedAnswer": "Profissionais"},
                {"id": "q-objective", "dimension": "objective", "question": "Objetivo?", "suggestedAnswer": "Simplificar"},
            ],
            "claims": [],
        }
        st_imp, imp = self.request("POST", "/api/works/planning/import", {
            "workId": wid,
            "stage": "briefing",
            "rawText": f"Aqui esta:\n```json\n{json.dumps(sug_b, ensure_ascii=False)}\n```",
            "expectedContextFingerprint": ov_sv["fingerprints"]["contextFingerprint"],
        })
        self.assertEqual(st_imp, 200, imp)
        self.assertTrue(imp["diffPreview"]["changedFields"])
        # Antes do aceite, objetivo continua vazio no rascunho
        self.assertEqual(imp["overview"]["planning"]["briefing"]["objective"], "")

        # Aceita preservando a resposta do operador em audience
        st_acc, acc = self.request("POST", "/api/works/planning/accept-suggestion", {
            "workId": wid,
            "suggestionId": imp["suggestionRecord"]["suggestionId"],
            "expectedContextFingerprint": imp["overview"]["fingerprints"]["contextFingerprint"],
            "preserveQuestions": True,
        })
        self.assertEqual(st_acc, 200, acc)
        self.assertEqual(acc["planning"]["briefing"]["objective"], "Simplificar consulta de horarios")
        aud_q = next(q for q in acc["planning"]["questions"] if q["dimension"] == "audience")
        self.assertEqual(aud_q["answer"], "Donos e recepcao de salao")

    def test_local_llm_adapter_success_errors_and_preserving_valid_deliveries(self):
        self._backup_llm_config()
        wid = "t-plan-llm"
        opened = self._create_work_with_media(wid, PROJECT_MS, template="marca-salao")
        paths = opened["work"]["paths"]

        # Gera ZIP previo valido se ffmpeg estiver disponivel para provar preservacao em falha do LLM
        prior_zip_sha = None
        if HAS_FFMPEG:
            creq = opened["carouselRequest"]
            _, jc = self.request("POST", "/api/export", {
                "request": creq, "outputDir": paths["carouselDeliveryDir"],
                "profile": creq["profile"], "kind": "carousel", "workId": wid,
            })
            self.assertEqual(self._poll_job(jc["jobId"])["status"], "completed")
            _, rev = self.request("POST", "/api/works/editorial/save", {
                "workId": wid,
                "briefing": {"objective": "Base previa", "cta": "Conheca o Marca Salao"},
                "channels": {creq["profile"]: {"postText": "Texto valido anterior", "cta": "Acesse pelo link na bio", "destinationUrl": "https://marcasalao.com.br"}},
            })
            car = next(p for p in rev["pieces"] if p["modality"] == "carousel")
            ch = next(c for c in rev["channels"] if c["profileId"] == creq["profile"])
            self.request("POST", "/api/works/review/decide", {
                "workId": wid, "targetType": "piece", "modality": "carousel", "profileId": car["profileId"],
                "expectedVersionId": car["deliveryVersionId"], "expectedDraftFingerprint": car["currentDraftFingerprint"],
                "decision": "approved_for_local_delivery", "note": "ok",
            })
            self.request("POST", "/api/works/review/decide", {
                "workId": wid, "targetType": "channel", "profileId": ch["profileId"],
                "expectedCopySha256": ch["copySha256"], "decision": "approved_for_local_delivery", "note": "ok",
            })
            _, pkg = self.request("POST", "/api/works/package", {
                "workId": wid, "pieces": [{"modality": "carousel", "profileId": car["profileId"]}],
                "channels": [{"profileId": ch["profileId"]}],
            })
            prior_zip_sha = pkg["packageDelivery"]["lastValidDelivery"]["zipSha256"]

        # Salva ideia manual antes de testar LLM
        self.request("POST", "/api/works/planning/save", {"workId": wid, "ideaText": "Ideia do operador que nao pode se perder."})

        # LLM desabilitado por padrao bloqueia chamada
        st_off, d_off = self.request("POST", "/api/works/planning/generate", {"workId": wid, "stage": "briefing"})
        self.assertEqual(st_off, 400, d_off)
        self.assertEqual(d_off.get("code"), "LLM_DISABLED")

        # Mock /v1/chat/completions para sucesso e modos de falha
        mode_box = {"mode": "ok-briefing"}

        def mock_handler(path, payload, count):
            self.assertEqual(path, "/v1/chat/completions")
            m = mode_box["mode"]
            if m == "timeout":
                time.sleep(1.1)
                return 504, {"error": "mock timeout"}
            if m == "empty":
                return 200, {"model": payload.get("model"), "choices": [{"message": {"content": ""}}]}
            if m == "bad-json":
                return 200, {"model": payload.get("model"), "choices": [{"message": {"content": "Desculpe, nao consegui gerar JSON."}}]}
            if m == "bad-contract":
                return 200, {"model": payload.get("model"), "choices": [{"message": {"content": json.dumps({"schemaVersion": 1, "stage": "briefing", "recommendedProfiles": ["perfil-proibido"]})}}]}
            if m == "ok-briefing":
                content = {
                    "schemaVersion": 1,
                    "stage": "briefing",
                    "product": "Marca Salao",
                    "audience": "Donos de salao",
                    "objective": "Mostrar agenda diaria sem caderno",
                    "coreMessage": "Horarios organizados em uma tela",
                    "supportEvidence": "Captura real do painel de horarios",
                    "cta": "Conheca o Marca Salao",
                    "tone": "Pratico",
                    "recommendedProfiles": ["youtube-shorts", "instagram-feed-image-square"],
                    "gaps": ["Definir tela principal da cena 2"],
                    "questions": [{"id": "q-objective", "dimension": "objective", "question": "Foco principal?", "suggestedAnswer": "Agilidade"}],
                    "claims": [],
                }
                return 200, {"model": payload.get("model"), "choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}]}
            raise AssertionError(m)

        mock = _MockLLMServer(mock_handler)
        self.addCleanup(mock.close)

        # Configura endpoint e qwen3:8b
        st_sc, cfg_saved = self.request("POST", "/api/llm/config", {
            "enabled": True, "endpoint": mock.endpoint, "model": "qwen3:8b", "timeoutSec": 5.0,
        })
        self.assertEqual(st_sc, 200, cfg_saved)

        # 1) Sucesso na Etapa 1
        st_ok, gen_ok = self.request("POST", "/api/works/planning/generate", {"workId": wid, "stage": "briefing"})
        self.assertEqual(st_ok, 200, gen_ok)
        self.assertEqual(gen_ok["llmResponseMeta"]["model"], "qwen3:8b")
        self.assertEqual(mock.requests[0]["payload"]["model"], "qwen3:8b")

        # 2) Timeout -> 504 + LLM_TIMEOUT
        mode_box["mode"] = "timeout"
        st_to, d_to = self.request("POST", "/api/works/planning/generate", {
            "workId": wid, "stage": "briefing", "llmConfig": {"enabled": True, "endpoint": mock.endpoint, "model": "qwen3:8b", "timeoutSec": 0.3},
        })
        self.assertEqual(st_to, 504, d_to)
        self.assertEqual(d_to.get("code"), "LLM_TIMEOUT")

        # 3) Resposta vazia -> 400 + LLM_EMPTY_RESPONSE
        mode_box["mode"] = "empty"
        st_em, d_em = self.request("POST", "/api/works/planning/generate", {"workId": wid, "stage": "briefing"})
        self.assertEqual(st_em, 400, d_em)
        self.assertEqual(d_em.get("code"), "LLM_EMPTY_RESPONSE")

        # 4) JSON invalido -> 400 + LLM_INVALID_JSON
        mode_box["mode"] = "bad-json"
        st_bj, d_bj = self.request("POST", "/api/works/planning/generate", {"workId": wid, "stage": "briefing"})
        self.assertEqual(st_bj, 400, d_bj)
        self.assertEqual(d_bj.get("code"), "LLM_INVALID_JSON")

        # 5) Fora do contrato PlanningSuggestion -> 400
        mode_box["mode"] = "bad-contract"
        st_bc, d_bc = self.request("POST", "/api/works/planning/generate", {"workId": wid, "stage": "briefing"})
        self.assertEqual(st_bc, 400, d_bc)

        # 6) Porta fechada -> 503 + LLM_UNAVAILABLE
        s_dead = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s_dead.bind(("127.0.0.1", 0))
        dead_port = s_dead.getsockname()[1]
        s_dead.close()
        st_un, d_un = self.request("POST", "/api/works/planning/generate", {
            "workId": wid, "stage": "briefing",
            "llmConfig": {"enabled": True, "endpoint": f"http://127.0.0.1:{dead_port}/v1/chat/completions", "model": "qwen3:8b", "timeoutSec": 8.0},
        })
        self.assertEqual(st_un, 503, d_un)
        self.assertEqual(d_un.get("code"), "LLM_UNAVAILABLE")

        # Todas as falhas preservaram o rascunho de planejamento e o ZIP previo
        _, after_err = self.request("GET", f"/api/works/planning?id={wid}")
        self.assertEqual(after_err["planning"]["ideaText"], "Ideia do operador que nao pode se perder.")
        if prior_zip_sha:
            _, pkg_after = self.request("GET", f"/api/works/package?id={wid}")
            self.assertEqual(pkg_after["lastValidDelivery"]["zipSha256"], prior_zip_sha)

    def test_pending_media_preserve_recheck_and_409_conflicts(self):
        self._backup_llm_config()
        wid = "t-plan-state"
        opened = self._create_work_with_media(wid, PROJECT_MS)

        # Salva Stage 1 e Stage 2 com cena 2 sem midia selecionada
        self.request("POST", "/api/works/planning/save", {
            "workId": wid,
            "currentStage": "creative",
            "ideaText": "Agenda simples",
            "briefing": {"objective": "Obj 1", "audience": "Saloes", "coreMessage": "Msg 1", "supportEvidence": "Tela", "hook": "Hook A", "scriptSummary": "Roteiro", "cta": "Conheca o Marca Salao"},
            "briefingExtended": {"product": "Marca Salao", "tone": "Direto", "recommendedProfiles": ["youtube-shorts", "instagram-feed-image-square"]},
            "creative": {
                "hookOptions": [{"id": "h-a", "text": "Hook A", "angle": "dor"}],
                "selectedHookId": "h-a",
                "scriptSummary": "Roteiro",
                "videoScenes": [
                    {"id": "cena-1", "durationMs": 3000, "titleOverlay": "Cena 1", "caption": "Cap 1", "narration": "Nar 1", "requiredMediaDescriptor": "Tela 1", "mediaId": "img-capa", "motionIntent": "none"},
                    {"id": "cena-2", "durationMs": 3000, "titleOverlay": "Cena 2", "caption": "Cap 2", "narration": "Nar 2", "requiredMediaDescriptor": "Tela 2 obrigatoria", "mediaId": "", "motionIntent": "none"},
                ],
                "carouselCards": [
                    {"id": "card-1", "role": "cover", "title": "Capa", "body": "Subtitulo", "requiredMediaDescriptor": "", "mediaId": ""},
                    {"id": "card-2", "role": "cta", "title": "Fechamento", "body": "Conheca o Marca Salao", "requiredMediaDescriptor": "", "mediaId": ""},
                ],
                "channelCopies": {
                    "youtube-shorts": {"postText": "Veja https://marcasalao.com.br", "cta": "Link na descricao", "destinationUrl": "https://marcasalao.com.br"},
                },
            },
            "markCreativeChecked": True,
        })

        # Aplicar sem midia em cena-2 deixa Video pending_media e nao escreve video.request invalido
        _, ov_now = self.request("GET", f"/api/works/planning?id={wid}")
        self.assertFalse(ov_now["analysis"]["creativeNeedsRecheck"])
        st_ap, ap_res = self.request("POST", "/api/works/planning/apply", {
            "workId": wid,
            "expectedContextFingerprint": ov_now["fingerprints"]["contextFingerprint"],
            "applyBriefing": True, "applyVideo": True, "applyCarousel": True, "applyMotionSync": False,
            "channelsToApply": ["youtube-shorts"],
        })
        self.assertEqual(st_ap, 200, ap_res)
        self.assertEqual(ap_res["applied"]["video"]["status"], "pending_media")
        self.assertEqual(ap_res["applied"]["video"]["pendingScenes"], ["cena-2"])
        self.assertEqual(ap_res["applied"]["carousel"]["status"], "applied")

        # Alterar briefing marca creativeNeedsRecheck = True ate reconferencia
        _, ov_chg = self.request("POST", "/api/works/planning/save", {
            "workId": wid,
            "briefing": {"objective": "Obj 2 alterado"},
        })
        self.assertTrue(ov_chg["analysis"]["creativeNeedsRecheck"])
        _, ov_chk = self.request("POST", "/api/works/planning/save", {
            "workId": wid,
            "creative": ov_chg["planning"]["creative"],
            "markCreativeChecked": True,
        })
        self.assertFalse(ov_chk["analysis"]["creativeNeedsRecheck"])

        # Edicao concorrente nos editores dispara HTTP 409 ao tentar aplicar com fingerprint antigo
        stale_fp = ov_chk["fingerprints"]["contextFingerprint"]
        stale_drafts_fp = ov_chk["fingerprints"]["draftsSha256"]
        mod_vreq = dict(opened["videoRequest"])
        mod_vreq["title"] = "Edicao concorrente no editor Video"
        self.request("POST", "/api/works/save", {"workId": wid, "videoRequest": mod_vreq})
        st_409, d409 = self.request("POST", "/api/works/planning/apply", {
            "workId": wid,
            "expectedContextFingerprint": stale_fp,
            "expectedDraftsSha256": stale_drafts_fp,
            "applyBriefing": True, "applyVideo": False, "applyCarousel": False, "applyMotionSync": False,
            "channelsToApply": [],
        })
        self.assertEqual(st_409, 409, d409)
        self.assertTrue(d409.get("conflict"))

    def test_end_to_end_planning_motion_export_localized_copy_and_zip(self):
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError("REQUIRE_RENDER=1 mas FFmpeg/FFprobe ausentes")
            raise unittest.SkipTest("FFmpeg/FFprobe indisponiveis")

        import delivery_package

        self._backup_llm_config()
        wid = "t-plan-e2e"
        opened = self._create_work_with_media(wid, PROJECT_MS)
        paths = opened["work"]["paths"]

        def mock_creative_handler(path, payload, count):
            if count == 1:
                sug = {
                    "schemaVersion": 1, "stage": "briefing",
                    "product": "Marca Salao", "audience": "Gestores de salao", "objective": "Apresentar agenda clara",
                    "coreMessage": "Controle seus horarios em segundos", "supportEvidence": "Tela real do trabalho",
                    "cta": "Conheca o Marca Salao", "tone": "Objetivo",
                    "recommendedProfiles": ["youtube-shorts", "instagram-feed-image-square"],
                    "gaps": [], "questions": [], "claims": [],
                }
            else:
                sug = {
                    "schemaVersion": 1, "stage": "creative",
                    "hookOptions": [
                        {"id": "hook-1", "text": "Ainda usa caderno?", "angle": "dor"},
                        {"id": "hook-2", "text": "Veja seus horarios do dia em 1 tela", "angle": "demonstracao"},
                    ],
                    "selectedHookId": "hook-2",
                    "scriptSummary": "Cena 1 abre com a visao do dia e Cena 2 detalha o horario.",
                    "videoScenes": [
                        {"id": "cena-abertura", "objective": "Gancho", "narrativeFunction": "hook", "durationMs": 2000, "titleOverlay": "Agenda em 1 tela", "caption": "Horarios do dia claros", "narration": "Veja seus horarios do dia sem complicacao.", "requiredMediaDescriptor": "Capa agenda", "motionIntent": "none"},
                        {"id": "cena-detalhe", "objective": "Prova", "narrativeFunction": "demonstration", "durationMs": 2500, "titleOverlay": "Tudo organizado", "caption": "Confirmados na tela", "narration": "Acompanhe cada atendimento facilmente.", "requiredMediaDescriptor": "Tela de horarios", "motionIntent": "none"},
                    ],
                    "carouselCards": [
                        {"id": "c-capa", "role": "cover", "title": "Agenda em 1 tela", "body": "Sem complicacao", "requiredMediaDescriptor": ""},
                        {"id": "c-passo", "role": "content", "title": "Tudo no horario", "body": "Organizacao diaria", "requiredMediaDescriptor": ""},
                    ],
                    "channelCopies": [
                        {"profileId": "youtube-shorts", "title": "Agenda no Marca Salao", "postText": "Confira em https://marcasalao.com.br", "cta": "Acesse pelo link da descricao", "destinationUrl": "https://marcasalao.com.br", "hashtags": "#MarcaSalao"},
                        {"profileId": "instagram-feed-image-square", "title": "", "postText": "Organize sua rotina no Marca Salao.", "cta": "Acesse pelo link na bio", "destinationUrl": "https://marcasalao.com.br", "hashtags": "#Salao"},
                    ],
                    "motionSuggestions": [
                        {"sceneId": "cena-detalhe", "targetElement": "Bloco horario confirmado", "suggestedColor": "#FFD700", "suggestedStartMs": 300, "suggestedEndMs": 2000, "note": "Marcar no canvas"},
                    ],
                }
            return 200, {"model": payload.get("model"), "choices": [{"message": {"content": json.dumps(sug, ensure_ascii=False)}}]}

        mock = _MockLLMServer(mock_creative_handler)
        self.addCleanup(mock.close)
        self.request("POST", "/api/llm/config", {"enabled": True, "endpoint": mock.endpoint, "model": "qwen3:8b", "timeoutSec": 10.0})

        # Etapa 1 e 2 via modelo local + vinculacao local das midias pelo operador
        self.request("POST", "/api/works/planning/save", {"workId": wid, "ideaText": "Demonstrar organizacao de horarios."})
        _, g1 = self.request("POST", "/api/works/planning/generate", {"workId": wid, "stage": "briefing"})
        _, ov1 = self.request("POST", "/api/works/planning/accept-suggestion", {
            "workId": wid, "suggestionId": g1["suggestionRecord"]["suggestionId"],
        })
        _, g2 = self.request("POST", "/api/works/planning/generate", {"workId": wid, "stage": "creative"})
        _, ov2 = self.request("POST", "/api/works/planning/accept-suggestion", {
            "workId": wid, "suggestionId": g2["suggestionRecord"]["suggestionId"],
        })

        # Seleciona midias locais para cena-abertura e cena-detalhe + reordena card
        cr = ov2["planning"]["creative"]
        cr["videoScenes"][0]["mediaId"] = "img-capa"
        cr["videoScenes"][1]["mediaId"] = "img-prova"
        cr["carouselCards"] = [cr["carouselCards"][1], cr["carouselCards"][0]]
        _, ov3 = self.request("POST", "/api/works/planning/save", {"workId": wid, "creative": cr, "markCreativeChecked": True})

        # Aplica tudo nos editores
        st_ap, ap = self.request("POST", "/api/works/planning/apply", {
            "workId": wid,
            "expectedContextFingerprint": ov3["fingerprints"]["contextFingerprint"],
            "applyBriefing": True, "applyVideo": True, "applyCarousel": True, "applyMotionSync": True,
            "channelsToApply": ["youtube-shorts", "instagram-feed-image-square"],
        })
        self.assertEqual(st_ap, 200, ap)
        self.assertEqual(ap["applied"]["video"]["status"], "applied")
        self.assertEqual(ap["applied"]["carousel"]["status"], "applied")
        self.assertEqual(ap["applied"]["motion"]["sceneIds"], ["cena-abertura", "cena-detalhe"])
        # Sugestao Motion nao cria retangulo automatico no MotionPlan
        self.assertEqual(ap["workData"]["motionPlan"]["effects"], [])

        # Operador marca região no Motion na cena-detalhe e exporta Video, Carrossel e Motion
        mplan = {
            "schemaVersion": 1,
            "requestId": ap["workData"]["videoRequest"]["id"],
            "effects": [{"sceneId": "cena-detalhe", "region": {"x": 0.15, "y": 0.25, "w": 0.5, "h": 0.3}, "color": "#FFD700", "thickness": 6, "startMs": 300, "endMs": 2000}],
        }
        self.request("POST", "/api/works/save", {"workId": wid, "motionPlan": mplan})

        _, jv = self.request("POST", "/api/export", {
            "request": ap["workData"]["videoRequest"], "outputDir": paths["videoDeliveryDir"],
            "profile": "youtube-shorts", "kind": "video", "workId": wid,
        })
        _, jc = self.request("POST", "/api/export", {
            "request": ap["workData"]["carouselRequest"], "outputDir": paths["carouselDeliveryDir"],
            "profile": "instagram-feed-image-square", "kind": "carousel", "workId": wid,
        })
        _, jm = self.request("POST", "/api/export", {
            "request": ap["workData"]["videoRequest"], "outputDir": paths["motionDeliveryDir"],
            "profile": "youtube-shorts", "kind": "video", "motionPlan": mplan, "workId": wid,
        })
        self.assertEqual(self._poll_job(jv["jobId"])["status"], "completed")
        self.assertEqual(self._poll_job(jc["jobId"])["status"], "completed")
        self.assertEqual(self._poll_job(jm["jobId"])["status"], "completed")

        # Aprova pecas e canais -> gera ZIP v1
        _, rev = self.request("GET", f"/api/works/review?id={wid}")
        v_p = next(p for p in rev["pieces"] if p["pieceKey"] == "video:youtube-shorts")
        c_p = next(p for p in rev["pieces"] if p["pieceKey"] == "carousel:instagram-feed-image-square")
        m_p = next(p for p in rev["pieces"] if p["pieceKey"] == "motion:youtube-shorts")
        mp4_sha_v1 = v_p["metrics"]["videoSha256"]
        self.assertEqual(v_p["metrics"]["audioStreams"], 0)
        for p in (v_p, c_p, m_p):
            st_d, rev = self.request("POST", "/api/works/review/decide", {
                "workId": wid, "targetType": "piece", "modality": p["modality"], "profileId": p["profileId"],
                "expectedVersionId": p["deliveryVersionId"], "expectedDraftFingerprint": p["currentDraftFingerprint"],
                "decision": "approved_for_local_delivery", "note": "Aprovado e2e",
            })
            self.assertEqual(st_d, 200, rev)
        for ch in rev["channels"]:
            st_dc, rev = self.request("POST", "/api/works/review/decide", {
                "workId": wid, "targetType": "channel", "profileId": ch["profileId"],
                "expectedCopySha256": ch["copySha256"], "decision": "approved_for_local_delivery", "note": "Copy aprovada",
            })
            self.assertEqual(st_dc, 200, rev)
        st_pkg1, pkg1 = self.request("POST", "/api/works/package", {
            "workId": wid,
            "pieces": [
                {"modality": "video", "profileId": "youtube-shorts"},
                {"modality": "carousel", "profileId": "instagram-feed-image-square"},
                {"modality": "motion", "profileId": "youtube-shorts"},
            ],
            "channels": [{"profileId": "youtube-shorts"}, {"profileId": "instagram-feed-image-square"}],
        })
        self.assertEqual(st_pkg1, 200, pkg1)
        self.assertTrue(pkg1["packageDelivery"]["available"])

        # Ajustar somente texto do canal youtube-shorts via Planejamento gera apenas copy_outdated sem re-render MP4
        _, ov_pre = self.request("GET", f"/api/works/planning?id={wid}")
        cr2 = ov_pre["planning"]["creative"]
        cr2["channelCopies"]["youtube-shorts"]["postText"] = "Texto revisado para YouTube Shorts: https://marcasalao.com.br"
        _, ov_post = self.request("POST", "/api/works/planning/save", {"workId": wid, "creative": cr2})
        _, ap_ch = self.request("POST", "/api/works/planning/apply", {
            "workId": wid,
            "expectedContextFingerprint": ov_post["fingerprints"]["contextFingerprint"],
            "applyBriefing": False, "applyVideo": False, "applyCarousel": False, "applyMotionSync": False,
            "channelsToApply": ["youtube-shorts"],
        })
        self.assertEqual(ap_ch["applied"]["video"]["status"], "skipped")
        rev_after = ap_ch["workData"]["review"]
        yt_ch = next(c for c in rev_after["channels"] if c["profileId"] == "youtube-shorts")
        ig_ch = next(c for c in rev_after["channels"] if c["profileId"] == "instagram-feed-image-square")
        self.assertEqual(yt_ch["status"], "copy_outdated")
        self.assertEqual(ig_ch["status"], "approved")
        v_p2 = next(p for p in rev_after["pieces"] if p["pieceKey"] == "video:youtube-shorts")
        self.assertEqual(v_p2["status"], "approved")
        self.assertEqual(v_p2["metrics"]["videoSha256"], mp4_sha_v1)

        # Reaprova apenas o canal atualizado e baixa ZIP v2 valido
        self.request("POST", "/api/works/review/decide", {
            "workId": wid, "targetType": "channel", "profileId": "youtube-shorts",
            "expectedCopySha256": yt_ch["copySha256"], "decision": "approved_for_local_delivery", "note": "Reaprovado",
        })
        st_pkg2, pkg2 = self.request("POST", "/api/works/package", {
            "workId": wid,
            "pieces": [
                {"modality": "video", "profileId": "youtube-shorts"},
                {"modality": "carousel", "profileId": "instagram-feed-image-square"},
            ],
            "channels": [{"profileId": "youtube-shorts"}, {"profileId": "instagram-feed-image-square"}],
        })
        self.assertEqual(st_pkg2, 200, pkg2)
        st_dl, ctype, zip_bytes = self._fetch_raw(f"/api/works/package/download?id={wid}")
        self.assertEqual(st_dl, 200)
        self.assertEqual(ctype, "application/zip")
        self.assertEqual(delivery_package._sha256_bytes(zip_bytes), pkg2["packageDelivery"]["lastValidDelivery"]["zipSha256"])


class StudioTenantEditorialIntegrationTest(StudioTestBase):
    """Tenant selector, brand-kit, preflight editorial/guardrails e MCP local."""

    def _cleanup_project(self, project_id):
        path = os.path.join(
            STUDIO_ROOT, ".workspace", "studio", "projects", f"{project_id}.project.json")
        if os.path.isfile(render_local.fs_path(path)):
            os.remove(render_local.fs_path(path))

    def _cleanup_work(self, work_id):
        work_dir = os.path.join(STUDIO_ROOT, ".workspace", "studio", "works", work_id)
        shutil.rmtree(render_local.fs_path(work_dir, force=True), ignore_errors=True)
        for piece in ("video", "carousel", "motion"):
            st_path = self.studio._export_status_path(
                f".workspace/studio/works/{work_id}/deliveries/{piece}")
            if os.path.isfile(render_local.fs_path(st_path)):
                os.remove(render_local.fs_path(st_path))

    def _request_copy(self):
        return json.loads(json.dumps(self.example))

    @staticmethod
    def _codes(preflight):
        return {alert.get("code") for alert in preflight.get("alerts") or []}

    def test_01_tenants_listing_brand_payload_and_selection(self):
        status, data = self.request("GET", "/api/tenants")
        self.assertEqual(status, 200, data)
        ids = {row["tenantId"] for row in data["tenants"]}
        self.assertEqual(ids, {"clinica-vital", "estudio-flow", "marca-salao", "meu-salao", "multitrack-hub"})

        status, data = self.request("GET", "/api/tenants/get?id=clinica-vital")
        self.assertEqual(status, 200, data)
        brand = data["tenant"]
        self.assertEqual(brand["brandName"], "Clínica Vital")
        self.assertTrue(brand["palette"]["primary"].startswith("#"))
        self.assertTrue(brand["typography"]["fontFamily"])
        self.assertTrue(brand["uiLabels"]["customerLabel"])
        self.assertEqual(brand["visualStyle"]["schemaVersion"], 1)
        self.assertRegex(brand["visualStyle"]["title"]["textColor"], r"^#[0-9a-fA-F]{6}$")
        self.assertIs(brand["autoPublish"], False)

        status, selected = self.request("POST", "/api/tenants/select", {"tenant_id": "multitrack-hub"})
        self.assertEqual(status, 200, selected)
        self.assertEqual(selected["activeTenantId"], "multitrack-hub")
        status, data = self.request("GET", "/api/tenants")
        self.assertEqual(data["activeTenantId"], "multitrack-hub")
        self.request("POST", "/api/tenants/select", {"tenant_id": "marca-salao"})

    def test_02_create_project_accepts_tenant_id(self):
        pid = "t-tenant-proj"
        pid_mcp = "t-tenant-proj-mcp"
        for item in (pid, pid_mcp):
            self._cleanup_project(item)
            self.addCleanup(self._cleanup_project, item)

        status, data = self.request("POST", "/api/projects/create", {
            "schemaVersion": 1,
            "id": pid,
            "name": "Projeto Clinica",
            "tenant_id": "clinica-vital",
            "outputProfiles": ["instagram-reels-video"],
        })
        self.assertEqual(status, 200, data)
        self.assertEqual(data["tenantId"], "clinica-vital")
        self.assertEqual(data["brand"]["brandName"], "Clínica Vital")
        manifest_path = os.path.join(
            STUDIO_ROOT, ".workspace", "studio", "projects", f"{pid}.project.json")
        manifest = read_json(render_local.fs_path(manifest_path))
        self.assertEqual(manifest["brandTheme"], "clinica-vital")
        self.assertTrue(data["report"]["valid"])

        status, mcp = self.request("POST", "/api/mcp/projects/create", {
            "schemaVersion": 1,
            "id": pid_mcp,
            "name": "Projeto via MCP",
            "tenant_id": "meu-salao",
            "outputProfiles": ["instagram-reels-video"],
        })
        self.assertEqual(status, 200, mcp)
        self.assertTrue(mcp["mcp"])
        self.assertEqual(mcp["tenantId"], "meu-salao")
        self.assertEqual(mcp["brand"]["brandName"], "Meu Salão")

    def test_03_create_work_applies_brand_visual_style(self):
        wid = "t-tenant-work"
        wid_mcp = "t-tenant-work-mcp"
        for item in (wid, wid_mcp):
            self._cleanup_work(item)
            self.addCleanup(self._cleanup_work, item)

        status, created = self.request("POST", "/api/works/create", {
            "id": wid,
            "name": "Trabalho Clinica",
            "project": PROJECT_MS,
            "template": "blank",
            "tenant_id": "clinica-vital",
        })
        self.assertEqual(status, 200, created)
        self.assertEqual(created["work"]["tenantId"], "clinica-vital")
        self.assertIs(created["work"]["autoPublish"], False)
        style = created["videoRequest"]["visualStyle"]
        brand = self.studio.get_tenant_brand("clinica-vital")
        self.assertEqual(style["schemaVersion"], 1)
        self.assertEqual(style["title"]["textColor"], brand["palette"]["textPrimary"])
        self.assertEqual(style["title"]["outlineColor"], brand["palette"]["background"])

        # Payloads MCP de planejamento aceitam tenant_id no corpo.
        status, prompt = self.request("POST", "/api/works/planning/prompt", {
            "workId": wid, "stage": "creative", "tenant_id": "clinica-vital",
        })
        self.assertEqual(status, 200, prompt)

        status, mcp = self.request("POST", "/api/mcp/works/create", {
            "id": wid_mcp,
            "name": "Trabalho MCP",
            "project": PROJECT_MS,
            "template": "blank",
            "tenant_id": "multitrack-hub",
        })
        self.assertEqual(status, 200, mcp)
        self.assertTrue(mcp["mcp"])
        self.assertEqual(mcp["work"]["tenantId"], "multitrack-hub")
        self.assertEqual(
            mcp["videoRequest"]["visualStyle"]["title"]["textColor"],
            self.studio.get_tenant_brand("multitrack-hub")["palette"]["textPrimary"],
        )

    def test_04_preflight_blocks_guardrails_routes_and_overlay(self):
        request = self._request_copy()
        request["scenes"][0]["caption"] = "Envie WhatsApp e receba lembrete automatico"
        request["scenes"][1]["caption"] = "Pague no checkout com cartao de credito"
        status, data = self.request("POST", "/api/works/preflight", {
            "tenant_id": "marca-salao",
            "request": request,
        })
        self.assertEqual(status, 200, data)
        preflight = data["preflight"]
        self.assertFalse(preflight["ok"])
        self.assertIn("GUARDRAIL_VIOLACAO", self._codes(preflight))
        self.assertEqual(
            preflight["checks"]["guardrails"]["violations"] > 0, True)
        self.assertIs(preflight["autoPublish"], False)

        routes = self._request_copy()
        routes["scenes"][0]["caption"] = "Agende em /booking/salao-1"
        routes["scenes"][1]["caption"] = "A equipe ve tudo em /gestor/agenda"
        status, data = self.request("POST", "/api/works/preflight", {
            "tenant_id": "marca-salao",
            "request": routes,
        })
        self.assertEqual(status, 200, data)
        self.assertIn("ROTAS_MISTURADAS", self._codes(data["preflight"]))

        status, data = self.request("POST", "/api/works/preflight", {
            "tenant_id": "marca-salao",
            "request": self._request_copy(),
            "textOverlayPlan": {"schemaVersion": 2, "caseId": "case-a", "overlays": []},
        })
        self.assertEqual(status, 200, data)
        self.assertIn("TEXT_OVERLAY_PLAN_INVALIDO", self._codes(data["preflight"]))

        status, data = self.request("POST", "/api/works/preflight", {
            "tenant_id": "marca-salao",
            "request": self._request_copy(),
            "textOverlayPlan": {
                "schemaVersion": 1,
                "caseId": "case-a",
                "overlays": [{"beatId": "beat-a", "text": "Pague no checkout"}],
            },
        })
        self.assertEqual(status, 200, data)
        self.assertIn("GUARDRAIL_VIOLACAO", self._codes(data["preflight"]))

    def test_05_preview_endpoint_enforces_preflight(self):
        status, clean = self.request("POST", "/api/preview", {"request": self._request_copy()})
        self.assertEqual(status, 200, clean)
        self.assertTrue(clean["preflight"]["ok"])
        self.assertEqual(len(clean["preflight"]["checks"]["editorialQa"]["lenses"]), 7)
        self.assertEqual(clean["result"]["status"], "preview")

        bad = self._request_copy()
        bad["scenes"][0]["caption"] = "Envie WhatsApp para confirmar o horario"
        status, blocked = self.request("POST", "/api/preview", {"request": bad})
        self.assertEqual(status, 422, blocked)
        self.assertIn("GUARDRAIL_VIOLACAO", self._codes(blocked["preflight"]))
        self.assertFalse(blocked["preflight"]["ok"])

    def test_06_srt_formatter_keeps_48_columns(self):
        request = self._request_copy()
        long_caption = (
            "A cliente escolhe o servico, o profissional e o horario disponivel "
            "na agenda do salao sem precisar de mensagens."
        )
        self.assertGreater(len(long_caption), 48)
        request["scenes"][0]["caption"] = long_caption
        status, data = self.request("POST", "/api/works/preflight", {
            "tenant_id": "marca-salao",
            "request": request,
        })
        self.assertEqual(status, 200, data)
        srt = data["preflight"]["checks"]["srt"]
        self.assertTrue(srt["ok"], srt)
        self.assertGreater(srt["beforeMaxLineLength"], 48)
        self.assertLessEqual(srt["maxLineLength"], 48)
        for line in srt["formatted"].splitlines():
            if "-->" not in line and not line.strip().isdigit():
                self.assertLessEqual(len(line), 48, line)

    def test_07_ui_tenant_selector_and_alert_banner_injected(self):
        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        text = body.decode("utf-8") if isinstance(body, bytes) else str(body)
        self.assertIn('id="studio-tenant-select"', text)
        self.assertIn("/api/tenants/select", text)
        self.assertIn("PREFLIGHT BLOQUEADO", text)

    def test_08_package_preflight_blocks_before_review(self):
        wid = "t-tenant-pkg-block"
        self._cleanup_work(wid)
        self.addCleanup(self._cleanup_work, wid)

        status, created = self.request("POST", "/api/works/create", {
            "id": wid,
            "name": "Pacote bloqueado",
            "project": PROJECT_MS,
            "template": "blank",
            "tenant_id": "marca-salao",
        })
        self.assertEqual(status, 200, created)
        vreq = created["videoRequest"]
        vreq["scenes"][0]["caption"] = "Pague no checkout para liberar o acesso"
        status, saved = self.request("POST", "/api/works/save", {
            "workId": wid, "videoRequest": vreq,
        })
        self.assertEqual(status, 200, saved)

        status, blocked = self.request("POST", "/api/works/package", {
            "workId": wid, "pieces": [], "channels": [],
        })
        self.assertEqual(status, 422, blocked)
        self.assertIn("GUARDRAIL_VIOLACAO", self._codes(blocked["preflight"]))

        # Exportacao e download do ZIP tambem passam pelo mesmo preflight.
        status, blocked_export = self.request("POST", "/api/export", {
            "workId": wid,
            "request": vreq,
            "outputDir": created["work"]["paths"]["videoDeliveryDir"],
            "profile": "instagram-reels-video",
        })
        self.assertEqual(status, 422, blocked_export)
        self.assertIn("GUARDRAIL_VIOLACAO", self._codes(blocked_export["preflight"]))
        with self.assertRaises(video_studio.PreflightBlocked) as ctx_download:
            self.studio.verified_package_download(wid)
        self.assertIn("GUARDRAIL_VIOLACAO", self._codes(ctx_download.exception.report))

        vreq["scenes"][0]["caption"] = "Agenda organizada no sistema"
        self.request("POST", "/api/works/save", {"workId": wid, "videoRequest": vreq})
        status, review_block = self.request("POST", "/api/works/package", {
            "workId": wid, "pieces": [], "channels": [],
        })
        self.assertEqual(status, 400, review_block)

    def test_09_preflight_is_read_only(self):
        def snapshot():
            files = set()
            for base in (
                os.path.join(STUDIO_ROOT, ".workspace", "studio"),
                os.path.join(STUDIO_ROOT, "02-reels-shorts", "deliveries"),
            ):
                for dirpath, _dirs, names in os.walk(render_local.fs_path(base)):
                    for name in names:
                        # Artefatos transientes do SQLite (WAL/SHM) nao sao conteudo
                        # do workspace: aparecem/desaparecem por checkpoint e tornariam
                        # a comparacao flaky sem indicar mutacao real.
                        if name.endswith(('-wal', '-shm')):
                            continue
                        files.add(os.path.relpath(os.path.join(dirpath, name), STUDIO_ROOT))
            return files

        before = snapshot()
        status, data = self.request("POST", "/api/works/preflight", {
            "tenant_id": "marca-salao",
            "request": self._request_copy(),
        })
        self.assertEqual(status, 200, data)
        self.assertTrue(data["preflight"]["ok"])
        self.assertEqual(snapshot(), before)

    def test_10_mcp_alias_projects_requires_known_tenant(self):
        pid = "t-tenant-proj-bad"
        self._cleanup_project(pid)
        self.addCleanup(self._cleanup_project, pid)
        status, err = self.request("POST", "/api/mcp/projects/create", {
            "schemaVersion": 1,
            "id": pid,
            "name": "Projeto tenant invalido",
            "tenant_id": "tenant-inexistente",
            "outputProfiles": ["instagram-reels-video"],
        })
        self.assertEqual(status, 400, err)
        self.assertIn("tenant_id", str(err.get("error", "")))


if __name__ == "__main__":
    unittest.main()
