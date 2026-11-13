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

import build_video
import make_agenda_media
import make_proof_assets
import make_request_media
import produce_video
import render_local
import render_pipeline

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


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


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


def run_produce(args):
    cmd = [sys.executable, os.path.join(WORKTREE, "tools", "produce_video.py"), *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=MAIN_ROOT, timeout=600)


def generate_media(request, root):
    for index, media in enumerate(request["media"], start=1):
        target = os.path.join(root, media["path"].replace("/", os.sep))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        make_proof_assets.write_scene_png(target, "marca-salao", media["id"], index)


class ProduceTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAS_BRIDGE:
            raise unittest.SkipTest("ponte TypeScript indisponivel")

    def setUp(self):
        self.name = self._testMethodName
        self.dir = os.path.join(TMP_BASE, self.name)
        os.makedirs(self.dir, exist_ok=True)
        self.media_rel = f".workspace/tmp/t_produce/{self.name}/assets"
        self.request = demo_request(self.media_rel)
        self.request_path = os.path.join(self.dir, "pedido.json")
        write_json(self.request_path, self.request)
        generate_media(self.request, MAIN_ROOT)
        self.output_dir = os.path.join(self.dir, "entrega")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        assets = os.path.join(MAIN_ROOT, self.media_rel.replace("/", os.sep))
        shutil.rmtree(assets, ignore_errors=True)

    def rel(self, path):
        return os.path.relpath(path, MAIN_ROOT).replace(os.sep, "/")


class PreviewTest(ProduceTestBase):
    def test_previa_json_sem_ffmpeg_sem_gravacao(self):
        res = run_produce(["--input", self.rel(self.request_path), "--plan-only", "--json"])
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout)
        self.assertEqual(payload["status"], "preview")
        self.assertEqual(len(payload["profiles"]), 3)
        for profile in payload["profiles"]:
            self.assertEqual(profile["status"], "compiled")
            self.assertEqual(profile["durationMs"], 14000)
            self.assertEqual(len(profile["beats"]), 3)
        self.assertFalse(os.path.exists(self.output_dir))

    def test_previa_perfil_unico(self):
        res = run_produce(["--input", self.rel(self.request_path), "--plan-only", "--profile", "youtube-shorts", "--json"])
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout)
        self.assertEqual(len(payload["profiles"]), 1)
        self.assertEqual(payload["profiles"][0]["profileId"], "youtube-shorts")


class ExportRealTest(ProduceTestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError("REQUIRE_RENDER=1 mas FFmpeg/FFprobe ausentes")
            raise unittest.SkipTest("FFmpeg/FFprobe indisponiveis")

    def test_exporta_tres_destinos_de_um_pedido(self):
        res = run_produce(["--input", self.rel(self.request_path), "--output-dir", self.rel(self.output_dir), "--json"])
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout)
        self.assertEqual(payload["status"], "completed")
        completed = [p for p in payload["profiles"] if p["status"] == "completed"]
        self.assertEqual(len(completed), 3)
        index_path = os.path.join(self.output_dir, "index.json")
        self.assertTrue(os.path.isfile(index_path))
        for profile in completed:
            profile_dir = os.path.join(self.output_dir, profile["profileId"])
            mp4s = [f for f in os.listdir(profile_dir) if f.endswith("-primary-output.mp4")]
            self.assertEqual(len(mp4s), 1)
            info = build_video.probe_media(os.path.join(profile_dir, mp4s[0]))
            streams = info["streams"]
            self.assertEqual(sum(1 for s in streams if s.get("codec_type") == "video"), 1)
            self.assertEqual(sum(1 for s in streams if s.get("codec_type") == "audio"), 0)
            video = next(s for s in streams if s.get("codec_type") == "video")
            self.assertEqual(int(video["width"]), 1080)
            self.assertEqual(int(video["height"]), 1920)

    def test_reexporta_um_perfil_reutilizando_midia(self):
        first = run_produce(["--input", self.rel(self.request_path), "--output-dir", self.rel(self.output_dir), "--json"])
        self.assertEqual(first.returncode, 0, first.stderr)
        manifest_before = read_json(os.path.join(self.output_dir, "youtube-shorts", "delivery-manifest.json"))
        asset_hash_before = manifest_before["artifacts"]["assetManifest"]["sha256"]
        edited = json.loads(json.dumps(self.request))
        edited["scenes"][0]["title"] = "Titulo corrigido"
        write_json(self.request_path, edited)
        second = run_produce(["--input", self.rel(self.request_path), "--profile", "youtube-shorts", "--output-dir", self.rel(self.output_dir), "--json"])
        self.assertEqual(second.returncode, 0, second.stderr)
        payload = json.loads(second.stdout)
        self.assertEqual(len([p for p in payload["profiles"] if p["status"] == "completed"]), 1)
        manifest_after = read_json(os.path.join(self.output_dir, "youtube-shorts", "delivery-manifest.json"))
        self.assertEqual(manifest_after["artifacts"]["assetManifest"]["sha256"], asset_hash_before)
        self.assertTrue(os.path.isdir(os.path.join(self.output_dir, "instagram-reels-video")))


class FailureIsolationTest(ProduceTestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError("REQUIRE_RENDER=1 mas FFmpeg/FFprobe ausentes")
            raise unittest.SkipTest("FFmpeg/FFprobe indisponiveis")

    def test_perfil_fora_da_allowlist_falha_isolado(self):
        project = read_json(os.path.join(MAIN_ROOT, PROJECT_MS_REL))
        project["outputProfiles"] = ["instagram-reels-video", "youtube-shorts"]
        project_rel = f".workspace/tmp/t_produce/{self.name}/restricted.project.json"
        write_json(os.path.join(MAIN_ROOT, project_rel.replace("/", os.sep)), project)
        edited = json.loads(json.dumps(self.request))
        edited["project"] = project_rel
        write_json(self.request_path, edited)
        res = run_produce(["--input", self.rel(self.request_path), "--output-dir", self.rel(self.output_dir), "--json"])
        self.assertNotEqual(res.returncode, 0)
        payload = json.loads(res.stdout)
        by_id = {p["profileId"]: p for p in payload["profiles"]}
        self.assertEqual(by_id["facebook-reels-video"]["status"], "failed")
        self.assertEqual(by_id["instagram-reels-video"]["status"], "completed")
        self.assertEqual(by_id["youtube-shorts"]["status"], "completed")

    def test_midia_ausente_preserva_saida_anterior(self):
        first = run_produce(["--input", self.rel(self.request_path), "--output-dir", self.rel(self.output_dir), "--json"])
        self.assertEqual(first.returncode, 0, first.stderr)
        before = render_local.sha256_file(os.path.join(self.output_dir, "instagram-reels-video", "delivery-manifest.json"))
        os.remove(os.path.join(MAIN_ROOT, self.request["media"][0]["path"].replace("/", os.sep)))
        second = run_produce(["--input", self.rel(self.request_path), "--output-dir", self.rel(self.output_dir), "--json"])
        self.assertNotEqual(second.returncode, 0)
        after = render_local.sha256_file(os.path.join(self.output_dir, "instagram-reels-video", "delivery-manifest.json"))
        self.assertEqual(before, after)


class MakeRequestMediaTest(ProduceTestBase):
    def test_gera_png_por_material_cadastrado(self):
        written = make_request_media.generate_request_media(self.request, MAIN_ROOT)
        self.assertEqual(len(written), 2)
        for media in self.request["media"]:
            target = os.path.join(MAIN_ROOT, media["path"].replace("/", os.sep))
            self.assertTrue(os.path.isfile(target))
            with open(target, "rb") as handle:
                self.assertEqual(handle.read(8), b"\x89PNG\r\n\x1a\n")


class DemoExampleTest(ProduceTestBase):
    """O exemplo versionado de Multitrack Hub produz os tres destinos pelo mesmo comando."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError("REQUIRE_RENDER=1 mas FFmpeg/FFprobe ausentes")
            raise unittest.SkipTest("FFmpeg/FFprobe indisponiveis")

    def test_exemplo_multitrack_versionado(self):
        example_rel = "tools/produce/examples/multitrack-hub-social-reel.video-request.json"
        gen = subprocess.run([sys.executable, os.path.join(WORKTREE, "tools", "make_request_media.py"),
                              "--input", example_rel], capture_output=True, text=True, cwd=MAIN_ROOT, timeout=120)
        self.assertEqual(gen.returncode, 0, gen.stderr)
        res = run_produce(["--input", example_rel, "--output-dir", self.rel(self.output_dir), "--json"])
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(len([p for p in payload["profiles"] if p["status"] == "completed"]), 3)
        index = read_json(os.path.join(self.output_dir, "index.json"))
        self.assertEqual(index["completedCount"], 3)
        self.assertEqual(index["requestId"], "multitrack-hub-social-reel-demo")


class IndexRegressionTest(unittest.TestCase):
    """merge_index preserva a ultima entrega valida separada da tentativa mais recente."""

    def setUp(self):
        self.dir = os.path.join(TMP_BASE, f"index_{self._testMethodName}")
        os.makedirs(self.dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def completed(self, profile="youtube-shorts"):
        return {
            "profileId": profile, "caseId": f"pedido-teste-{profile}", "packageId": f"pkg-{profile}",
            "status": "completed", "outputDir": f".workspace/tmp/x/{profile}",
            "deliveryManifest": f".workspace/tmp/x/{profile}/delivery-manifest.json",
            "artifacts": {"video": f".workspace/tmp/x/{profile}/v.mp4"},
            "inspection": {"width": 1080, "height": 1920},
        }

    def failed(self, profile="youtube-shorts"):
        return {"profileId": profile, "caseId": f"pedido-teste-{profile}", "status": "failed",
                "failureCode": "ASSET_MISSING", "errors": [], "error": "asset nao encontrado"}

    def test_completed_then_failed_preserves_last_valid(self):
        produce_video.merge_index(self.dir, "pedido-teste", [self.completed()])
        index = produce_video.merge_index(self.dir, "pedido-teste", [self.failed()])
        entry = index["profiles"][0]
        self.assertEqual(entry["lastAttempt"]["status"], "failed")
        self.assertIsNotNone(entry["lastValidDelivery"])
        self.assertEqual(entry["lastValidDelivery"]["status"], "completed")
        self.assertEqual(entry["status"], "completed")
        self.assertEqual(index["completedCount"], 1)

    def test_reads_v1_index(self):
        v1 = {"schemaVersion": 1, "requestId": "pedido-teste", "profileCount": 1, "completedCount": 1,
              "overallStatus": "completed", "profiles": [self.completed()]}
        write_json(os.path.join(self.dir, "index.json"), v1)
        index = produce_video.merge_index(self.dir, "pedido-teste", [self.failed()])
        entry = index["profiles"][0]
        self.assertIsNotNone(entry["lastValidDelivery"])
        self.assertEqual(entry["lastValidDelivery"]["packageId"], "pkg-youtube-shorts")
        self.assertEqual(entry["lastAttempt"]["status"], "failed")

    def test_owner_conflict_raises(self):
        produce_video.merge_index(self.dir, "pedido-a", [self.completed()])
        with self.assertRaises(render_pipeline.DeliveryCollisionError):
            produce_video.merge_index(self.dir, "pedido-b", [self.completed()])

    def test_reconcile_from_promoted_manifests(self):
        profile_dir = os.path.join(self.dir, "youtube-shorts")
        os.makedirs(profile_dir, exist_ok=True)
        manifest = {"schemaVersion": 1, "caseId": "pedido-teste-youtube-shorts", "packageId": "pkg-youtube-shorts",
                    "projectId": "marca-salao", "outputDir": ".workspace/tmp/x/youtube-shorts",
                    "artifacts": {"video": {"path": ".workspace/tmp/x/youtube-shorts/v.mp4", "sha256": "a" * 64, "ffprobe": {"width": 1080}}}}
        write_json(os.path.join(profile_dir, "delivery-manifest.json"), manifest)
        index = produce_video.reconcile_index_from_manifests(self.dir, "pedido-teste")
        entry = next(p for p in index["profiles"] if p["profileId"] == "youtube-shorts")
        self.assertIsNotNone(entry["lastValidDelivery"])
        self.assertEqual(entry["lastValidDelivery"]["packageId"], "pkg-youtube-shorts")
        self.assertEqual(index["completedCount"], 1)


class MotionTest(unittest.TestCase):
    """MotionPlan v1: previa resolvida, exportacao com contorno e manifesto/relatorio."""

    @classmethod
    def setUpClass(cls):
        if not HAS_BRIDGE:
            raise unittest.SkipTest("ponte indisponivel")
        if not HAS_FFMPEG:
            if REQUIRE_RENDER:
                raise AssertionError("REQUIRE_RENDER=1 mas FFmpeg ausente")
            raise unittest.SkipTest("FFmpeg indisponivel")

    def setUp(self):
        self.dir = os.path.join(TMP_BASE, f"motion_{self._testMethodName}")
        os.makedirs(self.dir, exist_ok=True)
        self.request = read_json(os.path.join(MAIN_ROOT, "tools/produce/examples/marca-salao-motion.video-request.json"))
        self.plan = read_json(os.path.join(MAIN_ROOT, "tools/produce/examples/marca-salao-motion.motion-plan.json"))
        self.input_path = os.path.join(self.dir, "pedido.json")
        self.plan_path = os.path.join(self.dir, "plano.json")
        write_json(self.input_path, self.request)
        write_json(self.plan_path, self.plan)
        agenda_rel = self.request["media"][0]["path"]
        make_agenda_media.write_agenda_png(os.path.join(MAIN_ROOT, agenda_rel.replace("/", os.sep)))
        self.output = os.path.join(self.dir, "entrega")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def rel(self, p):
        return os.path.relpath(p, MAIN_ROOT).replace(os.sep, "/")

    def run_cli(self, extra):
        return subprocess.run([sys.executable, os.path.join(WORKTREE, "tools/produce_video.py"),
                               "--input", self.rel(self.input_path), "--motion-plan", self.rel(self.plan_path), *extra],
                              capture_output=True, text=True, cwd=MAIN_ROOT, timeout=300)

    def test_preview_motion_resolved(self):
        res = self.run_cli(["--plan-only", "--json"])
        self.assertEqual(res.returncode, 0, res.stderr)
        d = json.loads(res.stdout)
        motion = d["profiles"][0]["motion"]
        self.assertEqual(motion["effects"][0]["absoluteStartMs"], 500)
        self.assertEqual(motion["effects"][0]["absoluteEndMs"], 3000)

    def test_export_motion_manifest_and_report(self):
        res = self.run_cli(["--output-dir", self.rel(self.output), "--json"])
        self.assertEqual(res.returncode, 0, res.stderr)
        d = json.loads(res.stdout)
        profile_dir = os.path.join(self.output, "instagram-reels-video")
        manifest = read_json(os.path.join(profile_dir, "delivery-manifest.json"))
        self.assertIn("motionPlan", manifest["artifacts"])
        mp = manifest["artifacts"]["motionPlan"]
        self.assertEqual(render_local.sha256_file(os.path.join(MAIN_ROOT, mp["path"])), mp["sha256"])
        report_files = [f for f in os.listdir(profile_dir) if f.endswith("-execution-report.json")]
        report = read_json(os.path.join(profile_dir, report_files[0]))
        self.assertEqual(report["motion"]["effects"][0]["absoluteStartMs"], 500)
        self.assertEqual(report["motion"]["effects"][0]["region"]["x"], 0.06)

    def test_invalid_region_interval_reference_zoom(self):
        bad = json.loads(json.dumps(self.plan))
        bad["effects"][0]["region"] = {"x": 0.5, "y": 0.2, "w": 0.8, "h": 0.1}
        write_json(self.plan_path, bad)
        self.assertEqual(self.run_cli(["--plan-only", "--json"]).returncode, 3)
        bad = json.loads(json.dumps(self.plan))
        bad["effects"][0]["endMs"] = 9000
        write_json(self.plan_path, bad)
        self.assertEqual(self.run_cli(["--plan-only", "--json"]).returncode, 3)
        bad = json.loads(json.dumps(self.plan))
        bad["effects"][0]["sceneId"] = "inexistente"
        write_json(self.plan_path, bad)
        self.assertEqual(self.run_cli(["--plan-only", "--json"]).returncode, 3)
        zoom = json.loads(json.dumps(self.request))
        zoom["scenes"][0]["motionIntent"] = "slow-zoom"
        write_json(self.input_path, zoom)
        write_json(self.plan_path, self.plan)
        self.assertEqual(self.run_cli(["--plan-only", "--json"]).returncode, 3)


if __name__ == "__main__":
    unittest.main()