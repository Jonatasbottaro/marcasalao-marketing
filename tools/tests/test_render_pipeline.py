"""Testes da CLI do pipeline local de renderizacao (tools/render_pipeline.py).

Camadas:
- previa (--plan-only): calcula plano, caseId, packageId, perfil, geometria,
  FPS, duracao, beatIds e compatibilidade com o recorte sem FFmpeg ou assets;
- ponte: validacao de caso, geracao do pacote canonico, verificacao de associacao
  e recorte via tools/render_bridge.mjs;
- render real: execucao completa de Marca Salao e Multitrack Hub com FFmpeg/FFprobe,
  inspecao dos MP4 (1 stream video, 0 audio), SRT, narracao, relatorio e manifesto;
- manifesto e rastreabilidade: abertura e recalculacao de hash de cada arquivo publicado;
- falha e transacao: colisao de caso, caso invalido, associacao incompativel,
  recorte nao suportado, asset ausente, falha de promocao, falha de restauracao,
  disputa de lock e sobreposicao de staging preservam a entrega anterior por SHA-256.
"""

import hashlib
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
import prepare_asset_manifest
import render_local
import render_pipeline
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
TMP_BASE = os.path.join(WORKTREE, ".workspace", "tmp", "t_pipe")
FFMPEG_DIR = os.path.join(MAIN_ROOT, ".workspace", "tools", "ffmpeg")

CASE_MS_REL = "platform/examples/pipelines/marca-salao-pipeline-pilot.pipeline.json"
CASE_MH_REL = "platform/examples/pipelines/multitrack-hub-pipeline-pilot.pipeline.json"
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
    return {
        name: render_local.sha256_file(os.path.join(output_dir, name))
        for name in sorted(os.listdir(output_dir))
        if os.path.isfile(os.path.join(output_dir, name))
        and name != render_local.PROMOTION_LOCK_NAME
    }


class PlanOnlyTest(unittest.TestCase):
    """Previa do plano (--plan-only) sem FFmpeg, sem assets e sem saida em disco."""

    @classmethod
    def setUpClass(cls):
        if not HAS_BRIDGE:
            if REQUIRE_RENDER:
                raise RuntimeError("build da platform ausente e REQUIRE_RENDER=1")
            raise unittest.SkipTest("build da platform ausente")

    def test_plan_only_marca_salao(self):
        plan = render_pipeline.run_plan_only(
            os.path.join(WORKTREE, CASE_MS_REL), WORKTREE)
        self.assertEqual(plan["caseId"], "marca-salao-pipeline-pilot")
        self.assertEqual(plan["packageId"],
                         "execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan")
        self.assertEqual(plan["perfil"], "instagram-reels-video")
        self.assertEqual(plan["fps"], 30)
        self.assertEqual(plan["duracao"], "14.0s")
        self.assertEqual(plan["durationMs"], 14000)
        self.assertEqual(plan["beats"], ["opening-hook", "demonstration-body", "closing-cta"])
        self.assertTrue(plan["supported"])
        self.assertTrue(plan["cabeNoRecorte"])
        self.assertIsNone(plan["unsupportedReason"])

    def test_plan_only_multitrack_hub(self):
        plan = render_pipeline.run_plan_only(
            os.path.join(WORKTREE, CASE_MH_REL), WORKTREE)
        self.assertEqual(plan["caseId"], "multitrack-hub-pipeline-pilot")
        self.assertEqual(plan["packageId"],
                         "execution-multitrack-hub-multitrack-social-reel-example-instagram-reels-video-multitrack-social-reel-beat-plan")
        self.assertEqual(plan["perfil"], "instagram-reels-video")
        self.assertEqual(plan["fps"], 30)
        self.assertEqual(plan["duracao"], "15.0s")
        self.assertEqual(plan["durationMs"], 15000)
        self.assertEqual(plan["beats"], ["opening-hook", "demonstration-body", "explanation-body", "closing-cta"])
        self.assertTrue(plan["supported"])

    def test_plan_only_cli_json_and_text(self):
        res_json = subprocess.run(
            [sys.executable, os.path.join(WORKTREE, "tools", "render_pipeline.py"),
             "--case", os.path.join(WORKTREE, CASE_MS_REL), "--plan-only", "--json"],
            capture_output=True, text=True, cwd=WORKTREE)
        self.assertEqual(res_json.returncode, 0)
        data = json.loads(res_json.stdout)
        self.assertEqual(data["caseId"], "marca-salao-pipeline-pilot")

        res_text = subprocess.run(
            [sys.executable, os.path.join(WORKTREE, "tools", "render_pipeline.py"),
             "--case", os.path.join(WORKTREE, CASE_MS_REL), "--plan-only"],
            capture_output=True, text=True, cwd=WORKTREE)
        self.assertEqual(res_text.returncode, 0)
        self.assertIn("Plano de renderizacao:", res_text.stdout)
        self.assertIn("Cabe no recorte do adaptador: Sim", res_text.stdout)

    def test_plan_only_missing_file_rejected(self):
        res = subprocess.run(
            [sys.executable, os.path.join(WORKTREE, "tools", "render_pipeline.py"),
             "--case", "nao-existe.pipeline.json", "--plan-only", "--json"],
            capture_output=True, text=True, cwd=WORKTREE)
        self.assertEqual(res.returncode, 2)
        self.assertIn("arquivo de case ausente", res.stderr)
        self.assertEqual(res.stdout, "")

    def test_plan_only_with_text_overlays(self):
        overlays_data = {
            "schemaVersion": 1,
            "caseId": "marca-salao-pipeline-pilot",
            "overlays": [
                {
                    "beatId": "demonstration-body",
                    "text": "Titulo de teste no plan-only"
                }
            ]
        }
        overlay_file = os.path.join(TMP_BASE, "plan_only_overlays.json")
        os.makedirs(TMP_BASE, exist_ok=True)
        write_json(overlay_file, overlays_data)
        try:
            plan = render_pipeline.run_plan_only(
                os.path.join(WORKTREE, CASE_MS_REL), WORKTREE, text_overlays_path=overlay_file)
            self.assertIn("textOverlays", plan)
            self.assertEqual(len(plan["textOverlays"]), 1)
            item = plan["textOverlays"][0]
            self.assertEqual(item["beatId"], "demonstration-body")
            self.assertEqual(item["text"], "Titulo de teste no plan-only")
            self.assertEqual(item["startMs"], 4000)
            self.assertEqual(item["endMs"], 10000)
            self.assertEqual(item["durationMs"], 6000)
        finally:
            if os.path.exists(overlay_file):
                os.remove(overlay_file)

    def test_plan_only_cli_text_overlays_json_and_text(self):
        overlays_data = {
            "schemaVersion": 1,
            "caseId": "marca-salao-pipeline-pilot",
            "overlays": [
                {
                    "beatId": "demonstration-body",
                    "text": "Chamada principal com acentuacao: facil e rapido!"
                }
            ]
        }
        overlay_file = os.path.join(TMP_BASE, "plan_cli_overlays.json")
        os.makedirs(TMP_BASE, exist_ok=True)
        write_json(overlay_file, overlays_data)
        try:
            res_json = subprocess.run(
                [sys.executable, os.path.join(WORKTREE, "tools", "render_pipeline.py"),
                 "--case", os.path.join(WORKTREE, CASE_MS_REL),
                 "--text-overlays", overlay_file,
                 "--plan-only", "--json"],
                capture_output=True, text=True, cwd=WORKTREE)
            self.assertEqual(res_json.returncode, 0)
            data = json.loads(res_json.stdout)
            self.assertEqual(data["caseId"], "marca-salao-pipeline-pilot")
            self.assertEqual(len(data["textOverlays"]), 1)
            self.assertEqual(data["textOverlays"][0]["text"], "Chamada principal com acentuacao: facil e rapido!")

            res_text = subprocess.run(
                [sys.executable, os.path.join(WORKTREE, "tools", "render_pipeline.py"),
                 "--case", os.path.join(WORKTREE, CASE_MS_REL),
                 "--text-overlays", overlay_file,
                 "--plan-only"],
                capture_output=True, text=True, cwd=WORKTREE)
            self.assertEqual(res_text.returncode, 0)
            self.assertIn("Titulos sobrepostos:", res_text.stdout)
            self.assertIn("demonstration-body (4000ms -> 10000ms)", res_text.stdout)
        finally:
            if os.path.exists(overlay_file):
                os.remove(overlay_file)

    def test_plan_only_invalid_text_overlays_rejected(self):
        bad_overlays = {
            "schemaVersion": 1,
            "caseId": "marca-salao-pipeline-pilot",
            "overlays": [
                {
                    "beatId": "beat-inexistente",
                    "text": "Texto"
                }
            ]
        }
        overlay_file = os.path.join(TMP_BASE, "bad_overlays.json")
        os.makedirs(TMP_BASE, exist_ok=True)
        write_json(overlay_file, bad_overlays)
        try:
            res = subprocess.run(
                [sys.executable, os.path.join(WORKTREE, "tools", "render_pipeline.py"),
                 "--case", os.path.join(WORKTREE, CASE_MS_REL),
                 "--text-overlays", overlay_file,
                 "--plan-only", "--json"],
                capture_output=True, text=True, cwd=WORKTREE)
            self.assertEqual(res.returncode, 3)
            self.assertIn("UNKNOWN_BEAT_REFERENCE", res.stderr)
        finally:
            if os.path.exists(overlay_file):
                os.remove(overlay_file)

    def test_plan_only_with_visual_style(self):
        style = {
            "schemaVersion": 1,
            "id": "style-gold",
            "title": {
                "textColor": "#FFD700",
                "outlineColor": "#000000",
                "fontSize": 48,
                "marginTop": 180,
                "marginHorizontal": 80
            }
        }
        overlays = {
            "schemaVersion": 1,
            "caseId": "marca-salao-pipeline-pilot",
            "overlays": [{"beatId": "demonstration-body", "text": "TITULO DE PROVA"}]
        }
        style_file = os.path.join(TMP_BASE, "style_gold.json")
        overlay_file = os.path.join(TMP_BASE, "overlays_sample.json")
        os.makedirs(TMP_BASE, exist_ok=True)
        write_json(style_file, style)
        write_json(overlay_file, overlays)
        try:
            # Com overlays: hasTitlesToApply deve ser True
            res = subprocess.run(
                [sys.executable, os.path.join(WORKTREE, "tools", "render_pipeline.py"),
                 "--case", os.path.join(WORKTREE, CASE_MS_REL),
                 "--text-overlays", overlay_file,
                 "--visual-style", style_file,
                 "--plan-only", "--json"],
                capture_output=True, text=True, cwd=WORKTREE)
            self.assertEqual(res.returncode, 0, f"stderr: {res.stderr}")
            data = json.loads(res.stdout)
            self.assertIn("visualStyle", data)
            self.assertEqual(data["visualStyle"]["id"], "style-gold")
            self.assertEqual(data["visualStyle"]["title"]["textColor"], "#FFD700")
            self.assertTrue(data.get("hasTitlesToApply"))

            # Sem overlays: hasTitlesToApply deve ser False
            res_no_overlays = subprocess.run(
                [sys.executable, os.path.join(WORKTREE, "tools", "render_pipeline.py"),
                 "--case", os.path.join(WORKTREE, CASE_MS_REL),
                 "--visual-style", style_file,
                 "--plan-only", "--json"],
                capture_output=True, text=True, cwd=WORKTREE)
            self.assertEqual(res_no_overlays.returncode, 0)
            data_no = json.loads(res_no_overlays.stdout)
            self.assertIn("visualStyle", data_no)
            self.assertFalse(data_no.get("hasTitlesToApply"))

            # Saida legivel de terminal
            res_txt = subprocess.run(
                [sys.executable, os.path.join(WORKTREE, "tools", "render_pipeline.py"),
                 "--case", os.path.join(WORKTREE, CASE_MS_REL),
                 "--text-overlays", overlay_file,
                 "--visual-style", style_file,
                 "--plan-only"],
                capture_output=True, text=True, cwd=WORKTREE)
            self.assertEqual(res_txt.returncode, 0)
            self.assertIn("Estilo visual: style-gold", res_txt.stdout)
            self.assertIn("Cor do texto: #FFD700", res_txt.stdout)
            self.assertIn("Tamanho da fonte: 48px", res_txt.stdout)
            self.assertIn("Margem superior: 180px", res_txt.stdout)
            self.assertIn("Margem lateral: 80px", res_txt.stdout)
            self.assertIn("Aplicavel a titulos: Sim", res_txt.stdout)
        finally:
            for f in (style_file, overlay_file):
                if os.path.exists(f):
                    os.remove(f)

    def test_plan_only_invalid_visual_style_rejected(self):
        bad_style = {
            "schemaVersion": 1,
            "id": "bad-style",
            "title": {
                "textColor": "amarelo-invalido",
                "outlineColor": "#000000",
                "fontSize": 48,
                "marginTop": 180,
                "marginHorizontal": 80
            }
        }
        style_file = os.path.join(TMP_BASE, "bad_style.json")
        os.makedirs(TMP_BASE, exist_ok=True)
        write_json(style_file, bad_style)
        try:
            res = subprocess.run(
                [sys.executable, os.path.join(WORKTREE, "tools", "render_pipeline.py"),
                 "--case", os.path.join(WORKTREE, CASE_MS_REL),
                 "--visual-style", style_file,
                 "--plan-only", "--json"],
                capture_output=True, text=True, cwd=WORKTREE)
            self.assertEqual(res.returncode, 3)
            self.assertIn("STYLE_COLOR_INVALID", res.stderr)
        finally:
            if os.path.exists(style_file):
                os.remove(style_file)

class PipelineBridgeTest(unittest.TestCase):
    """Ponte Node de carregamento de caso e validacao integrada."""

    @classmethod
    def setUpClass(cls):
        if not HAS_BRIDGE:
            if REQUIRE_RENDER:
                raise RuntimeError("build da platform ausente e REQUIRE_RENDER=1")
            raise unittest.SkipTest("build da platform ausente")

    def setUp(self):
        self.tmp = os.path.join(TMP_BASE, "b_" + hashlib.md5(self._testMethodName.encode()).hexdigest()[:6])
        os.makedirs(self.tmp, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_bridge_valid_case_and_assets(self):
        verdict = render_pipeline.run_bridge_case(
            WORKTREE, os.path.join(WORKTREE, CASE_MS_REL),
            assets_path=os.path.join(WORKTREE, ASSOC_MS_REL), plan_only=False)
        self.assertTrue(verdict["ok"])
        self.assertEqual(verdict["caseId"], "marca-salao-pipeline-pilot")
        self.assertIn("package", verdict)
        self.assertIn("canonicalJson", verdict)
        self.assertIn("association", verdict)

    def test_bridge_incompatible_association(self):
        assoc = read_json(os.path.join(WORKTREE, ASSOC_MS_REL))
        assoc["packageId"] = "outro-package-id"
        bad_assoc = os.path.join(self.tmp, "bad.assets.json")
        write_json(bad_assoc, assoc)
        verdict = render_pipeline.run_bridge_case(
            WORKTREE, os.path.join(WORKTREE, CASE_MS_REL),
            assets_path=bad_assoc, plan_only=False)
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["failureCode"], "PACKAGE_ID_MISMATCH")

    def test_bridge_unsupported_configuration(self):
        case_dir = os.path.join(self.tmp, "case-unsupported")
        os.makedirs(case_dir, exist_ok=True)
        orig_case = read_json(os.path.join(WORKTREE, CASE_MS_REL))
        orig_case_dir = os.path.dirname(os.path.join(WORKTREE, CASE_MS_REL))

        proj = read_json(os.path.normpath(os.path.join(orig_case_dir, orig_case["project"])))
        comp = read_json(os.path.normpath(os.path.join(orig_case_dir, orig_case["composition"])))
        out_plan = read_json(os.path.normpath(os.path.join(orig_case_dir, orig_case["outputPlan"])))
        beat_plan = read_json(os.path.normpath(os.path.join(orig_case_dir, orig_case["beatPlan"])))

        # Altera beat para motionIntent 'parallax-depth' (valido no contrato geral, mas fora do recorte do adaptador)
        beat_plan["beats"][1]["motionIntent"] = "parallax-depth"

        write_json(os.path.join(case_dir, "project.json"), proj)
        write_json(os.path.join(case_dir, "composition.json"), comp)
        write_json(os.path.join(case_dir, "output-plan.json"), out_plan)
        write_json(os.path.join(case_dir, "beat-plan.json"), beat_plan)

        bad_case = {
            "schemaVersion": 1,
            "id": "unsupported-case",
            "project": "./project.json",
            "composition": "./composition.json",
            "outputPlan": "./output-plan.json",
            "beatPlan": "./beat-plan.json",
        }
        case_file = os.path.join(case_dir, "test.pipeline.json")
        write_json(case_file, bad_case)

        plan = render_pipeline.run_plan_only(case_file, WORKTREE)
        self.assertFalse(plan["supported"])
        self.assertFalse(plan["cabeNoRecorte"])
        self.assertEqual(plan["unsupportedReason"], "demonstration-body.motionIntent")


class PipelineRenderEndToEndTest(unittest.TestCase):
    """Execucao real de renderizacao, inspecao, promocao e transacao."""

    @classmethod
    def setUpClass(cls):
        if not HAS_FFMPEG or not HAS_BRIDGE:
            if REQUIRE_RENDER:
                raise RuntimeError("ferramentas obrigatorias ausentes e REQUIRE_RENDER=1")
            raise unittest.SkipTest("ffmpeg ou platform ausente")

        cls.assets_dir_ms = os.path.join(TMP_BASE, "assets", "marca-salao")
        cls.assets_dir_mh = os.path.join(TMP_BASE, "assets", "multitrack-hub")
        os.makedirs(cls.assets_dir_ms, exist_ok=True)
        os.makedirs(cls.assets_dir_mh, exist_ok=True)
        make_proof_assets.generate_assets(
            None, cls.assets_dir_ms, WORKTREE,
            case_path=os.path.join(WORKTREE, CASE_MS_REL))
        make_proof_assets.generate_assets(
            None, cls.assets_dir_mh, WORKTREE,
            case_path=os.path.join(WORKTREE, CASE_MH_REL))

    def setUp(self):
        self.tmp = os.path.join(TMP_BASE, "r_" + hashlib.md5(self._testMethodName.encode()).hexdigest()[:6])
        os.makedirs(self.tmp, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _prepare_assoc(self, base_assoc_rel, assets_dir):
        base = read_json(os.path.join(WORKTREE, base_assoc_rel))
        for binding in base["assets"]:
            binding["path"] = render_local.rel(
                WORKTREE, os.path.join(assets_dir, f"{binding['beatId']}.png"))
        target = os.path.join(self.tmp, os.path.basename(base_assoc_rel))
        write_json(target, base)
        return target

    def test_01_marca_salao_render_e2e_and_manifest_hashes(self):
        assoc = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        output_dir = os.path.join(self.tmp, "ms-delivery")

        summary = render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc, output_dir, WORKTREE, None)
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["caseId"], "marca-salao-pipeline-pilot")

        # Inspeciona MP4
        video_path = os.path.join(WORKTREE, summary["artifacts"]["video"])
        inspection = build_video.validate_mp4(video_path, 1080, 1920, 30, 14.0)
        self.assertEqual(inspection["videoStreams"], 1)
        self.assertEqual(inspection["audioStreams"], 0)
        self.assertEqual(inspection["duration"], 14.0)
        self.assertEqual(inspection["pixFmt"], "yuv420p")

        # Inspeciona SRT
        srt_path = os.path.join(WORKTREE, summary["artifacts"]["srt"])
        self.assertEqual(srt_validate.validate_srt_file(srt_path, 14.0), [])

        # Abre cada arquivo listado no manifesto e recalcula hash
        manifest_path = os.path.join(WORKTREE, summary["manifest"])
        manifest = read_json(manifest_path)
        self.assertEqual(manifest["schemaVersion"], 1)
        self.assertEqual(manifest["caseId"], "marca-salao-pipeline-pilot")

        for key, entry in manifest["artifacts"].items():
            file_path = os.path.join(WORKTREE, entry["path"])
            self.assertTrue(os.path.isfile(file_path), f"arquivo do manifesto ausente: {entry['path']}")
            with open(file_path, "rb") as handle:
                content = handle.read()
            self.assertEqual(len(content), entry["bytes"])
            self.assertEqual(render_local.sha256_file(file_path), entry["sha256"])

        # O pacote promovido deve ser identico em bytes a fixture oficial
        pkg_path = os.path.join(WORKTREE, summary["artifacts"]["package"])
        official_pkg_path = os.path.join(
            WORKTREE,
            "platform/examples/execution-packages/execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan.execution-package.json")
        with open(pkg_path, "rb") as h1, open(official_pkg_path, "rb") as h2:
            self.assertEqual(h1.read(), h2.read())

    def test_02_multitrack_hub_render_e2e_and_manifest_hashes(self):
        assoc = self._prepare_assoc(ASSOC_MH_REL, self.assets_dir_mh)
        output_dir = os.path.join(self.tmp, "mh-delivery")

        summary = render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MH_REL), assoc, output_dir, WORKTREE, None)
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["caseId"], "multitrack-hub-pipeline-pilot")

        video_path = os.path.join(WORKTREE, summary["artifacts"]["video"])
        inspection = build_video.validate_mp4(video_path, 1080, 1920, 30, 15.0)
        self.assertEqual(inspection["videoStreams"], 1)
        self.assertEqual(inspection["audioStreams"], 0)
        self.assertEqual(inspection["duration"], 15.0)

        srt_path = os.path.join(WORKTREE, summary["artifacts"]["srt"])
        self.assertEqual(srt_validate.validate_srt_file(srt_path, 15.0), [])

        manifest_path = os.path.join(WORKTREE, summary["manifest"])
        manifest = read_json(manifest_path)
        for key, entry in manifest["artifacts"].items():
            file_path = os.path.join(WORKTREE, entry["path"])
            self.assertTrue(os.path.isfile(file_path))
            self.assertEqual(render_local.sha256_file(file_path), entry["sha256"])

    def test_03_repeat_same_case_idempotent(self):
        assoc = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        output_dir = os.path.join(self.tmp, "repeat-delivery")

        # Primeira execucao
        render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc, output_dir, WORKTREE, None)
        first_hashes = delivery_hashes(output_dir)

        # Repete o mesmo caso
        render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc, output_dir, WORKTREE, None)
        second_hashes = delivery_hashes(output_dir)

        # Arquivos deterministicos permanecem iguais
        self.assertEqual(first_hashes["delivery-manifest.json"], second_hashes["delivery-manifest.json"])

    def test_04_destination_collision_with_different_case_rejected(self):
        assoc_ms = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        assoc_mh = self._prepare_assoc(ASSOC_MH_REL, self.assets_dir_mh)
        output_dir = os.path.join(self.tmp, "collision-delivery")

        # Renderiza Marca Salao
        render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc_ms, output_dir, WORKTREE, None)
        hashes_before = delivery_hashes(output_dir)

        # Tenta renderizar Multitrack Hub no mesmo destino -> colisao
        with self.assertRaises(render_pipeline.DeliveryCollisionError) as ctx:
            render_pipeline.run_render_pipeline(
                os.path.join(WORKTREE, CASE_MH_REL), assoc_mh, output_dir, WORKTREE, None)
        self.assertIn("colisao de entrega", str(ctx.exception))

        # Entrega de Marca Salao permanece 100% intacta
        hashes_after = delivery_hashes(output_dir)
        self.assertEqual(hashes_before, hashes_after)

    def test_05_incompatible_association_preserves_previous_delivery(self):
        assoc_ms = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        output_dir = os.path.join(self.tmp, "preserve-incompatible-assoc")

        render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc_ms, output_dir, WORKTREE, None)
        hashes_before = delivery_hashes(output_dir)

        # Associacao com beat faltando
        bad_assoc_data = read_json(assoc_ms)
        bad_assoc_data["assets"] = bad_assoc_data["assets"][:1]
        bad_assoc_file = os.path.join(self.tmp, "bad-assoc.json")
        write_json(bad_assoc_file, bad_assoc_data)

        with self.assertRaises(render_local.RenderInputError):
            render_pipeline.run_render_pipeline(
                os.path.join(WORKTREE, CASE_MS_REL), bad_assoc_file, output_dir, WORKTREE, None)

        self.assertEqual(hashes_before, delivery_hashes(output_dir))

    def test_06_unsupported_configuration_preserves_previous_delivery(self):
        assoc_ms = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        output_dir = os.path.join(self.tmp, "preserve-unsupported-config")

        render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc_ms, output_dir, WORKTREE, None)
        hashes_before = delivery_hashes(output_dir)

        # Cria caso com configuracao fora do recorte (motionIntent 'parallax-depth')
        case_dir = os.path.join(self.tmp, "case-unsupported-config")
        os.makedirs(case_dir, exist_ok=True)
        orig_case = read_json(os.path.join(WORKTREE, CASE_MS_REL))
        orig_case_dir = os.path.dirname(os.path.join(WORKTREE, CASE_MS_REL))

        proj = read_json(os.path.normpath(os.path.join(orig_case_dir, orig_case["project"])))
        comp = read_json(os.path.normpath(os.path.join(orig_case_dir, orig_case["composition"])))
        out_plan = read_json(os.path.normpath(os.path.join(orig_case_dir, orig_case["outputPlan"])))
        beat_plan = read_json(os.path.normpath(os.path.join(orig_case_dir, orig_case["beatPlan"])))
        beat_plan["beats"][1]["motionIntent"] = "parallax-depth"

        write_json(os.path.join(case_dir, "project.json"), proj)
        write_json(os.path.join(case_dir, "composition.json"), comp)
        write_json(os.path.join(case_dir, "output-plan.json"), out_plan)
        write_json(os.path.join(case_dir, "beat-plan.json"), beat_plan)

        bad_case = {
            "schemaVersion": 1,
            "id": "marca-salao-pipeline-pilot",  # Mesmo id para nao falhar por colisao
            "project": "./project.json",
            "composition": "./composition.json",
            "outputPlan": "./output-plan.json",
            "beatPlan": "./beat-plan.json",
        }
        case_file = os.path.join(case_dir, "test.pipeline.json")
        write_json(case_file, bad_case)

        with self.assertRaises(render_local.RenderInputError):
            render_pipeline.run_render_pipeline(
                case_file, assoc_ms, output_dir, WORKTREE, None)

        self.assertEqual(hashes_before, delivery_hashes(output_dir))

    def test_07_missing_asset_preserves_previous_delivery(self):
        assoc_ms = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        output_dir = os.path.join(self.tmp, "preserve-missing-asset")

        render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc_ms, output_dir, WORKTREE, None)
        hashes_before = delivery_hashes(output_dir)

        bad_assoc = read_json(assoc_ms)
        bad_assoc["assets"][0]["path"] = ".workspace/tmp/nao-existe.png"
        bad_assoc_file = os.path.join(self.tmp, "missing-asset.json")
        write_json(bad_assoc_file, bad_assoc)

        with self.assertRaises(build_video.DeliveryError):
            render_pipeline.run_render_pipeline(
                os.path.join(WORKTREE, CASE_MS_REL), bad_assoc_file, output_dir, WORKTREE, None)

        self.assertEqual(hashes_before, delivery_hashes(output_dir))

    def test_08_promotion_failure_preserves_previous_delivery(self):
        assoc_ms = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        output_dir = os.path.join(self.tmp, "preserve-promotion-failure")

        render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc_ms, output_dir, WORKTREE, None)
        hashes_before = delivery_hashes(output_dir)

        real_replace = os.replace
        calls = {"count": 0}

        def fail_on_third_replace(src, dst):
            calls["count"] += 1
            if calls["count"] == 3:
                raise OSError("falha forcada de I/O na promocao")
            return real_replace(src, dst)

        with mock.patch("os.replace", side_effect=fail_on_third_replace):
            with self.assertRaises(build_video.DeliveryError):
                render_pipeline.run_render_pipeline(
                    os.path.join(WORKTREE, CASE_MS_REL), assoc_ms, output_dir, WORKTREE, None)

        self.assertEqual(hashes_before, delivery_hashes(output_dir))

    def test_09_restore_failure_preserves_backup_for_diagnosis(self):
        assoc_ms = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        output_dir = os.path.join(self.tmp, "preserve-restore-failure")

        render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc_ms, output_dir, WORKTREE, None)

        real_replace = os.replace
        calls = {"count": 0}

        def fail_always(src, dst):
            calls["count"] += 1
            if calls["count"] >= 3:
                raise OSError("falha forcada na promocao e na restauracao")
            return real_replace(src, dst)

        with mock.patch("os.replace", side_effect=fail_always):
            with self.assertRaises(build_video.DeliveryError) as ctx:
                render_pipeline.run_render_pipeline(
                    os.path.join(WORKTREE, CASE_MS_REL), assoc_ms, output_dir, WORKTREE, None)
            self.assertIn("backup preservado para diagnostico", str(ctx.exception))

    def test_10_promotion_lock_dispute_has_clear_diagnostic(self):
        assoc_ms = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        output_dir = os.path.join(self.tmp, "lock-dispute")
        os.makedirs(output_dir, exist_ok=True)
        lock_file = os.path.join(output_dir, render_local.PROMOTION_LOCK_NAME)
        with open(lock_file, "w") as handle:
            handle.write("lock-concorrente\n")

        with self.assertRaises(build_video.DeliveryError) as ctx:
            render_pipeline.run_render_pipeline(
                os.path.join(WORKTREE, CASE_MS_REL), assoc_ms, output_dir, WORKTREE, None)
        self.assertIn("promocao concorrente", str(ctx.exception))

    def test_11_staging_overlap_rejected_before_any_write(self):
        assoc_ms = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        output_dir = os.path.join(self.tmp, "staging-overlap")

        # Staging e raiz
        with self.assertRaises(render_local.InputFileError):
            render_pipeline.run_render_pipeline(
                os.path.join(WORKTREE, CASE_MS_REL), assoc_ms, output_dir, WORKTREE, WORKTREE)

        # Staging sobrepoe output
        with self.assertRaises(render_local.InputFileError):
            render_pipeline.run_render_pipeline(
                os.path.join(WORKTREE, CASE_MS_REL), assoc_ms, output_dir, WORKTREE, output_dir)

    def test_12_text_overlay_revision_reuses_visual_and_differs_in_title_region(self):
        assoc = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        output_v1 = os.path.join(self.tmp, "delivery-v1")
        output_v2 = os.path.join(self.tmp, "delivery-v2")

        plan_v1_file = os.path.join(self.tmp, "title_v1.json")
        plan_v2_file = os.path.join(self.tmp, "title_v2.json")

        write_json(plan_v1_file, {
            "schemaVersion": 1,
            "caseId": "marca-salao-pipeline-pilot",
            "overlays": [
                {
                    "beatId": "demonstration-body",
                    "text": "TITULO ORIGINAL DE PROVA"
                }
            ]
        })

        write_json(plan_v2_file, {
            "schemaVersion": 1,
            "caseId": "marca-salao-pipeline-pilot",
            "overlays": [
                {
                    "beatId": "demonstration-body",
                    "text": "TITULO REVISADO COM NOVA CHAMADA"
                }
            ]
        })

        # Render V1
        res_v1 = render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc, output_v1, WORKTREE, None,
            text_overlays_path=plan_v1_file)
        self.assertEqual(res_v1["status"], "completed")

        # Render V2 (mesmo caso e mesmos assets, alterando apenas o titulo)
        res_v2 = render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc, output_v2, WORKTREE, None,
            text_overlays_path=plan_v2_file)
        self.assertEqual(res_v2["status"], "completed")

        manifest_v1 = read_json(os.path.join(WORKTREE, res_v1["manifest"]))
        manifest_v2 = read_json(os.path.join(WORKTREE, res_v2["manifest"]))

        # 1. Hashes identicos: pacote, SRT, narracao
        self.assertEqual(
            manifest_v1["artifacts"]["package"]["sha256"],
            manifest_v2["artifacts"]["package"]["sha256"]
        )
        self.assertEqual(
            manifest_v1["artifacts"]["srt"]["sha256"],
            manifest_v2["artifacts"]["srt"]["sha256"]
        )
        self.assertEqual(
            manifest_v1["artifacts"]["narration"]["sha256"],
            manifest_v2["artifacts"]["narration"]["sha256"]
        )

        # 2. Hashes que devem diferir: o video e o plano de sobreposicao textual
        self.assertNotEqual(
            manifest_v1["artifacts"]["video"]["sha256"],
            manifest_v2["artifacts"]["video"]["sha256"]
        )
        self.assertNotEqual(
            manifest_v1["artifacts"]["textOverlayPlan"]["sha256"],
            manifest_v2["artifacts"]["textOverlayPlan"]["sha256"]
        )

        # 3. Inspecao dos dois MP4 com FFprobe
        video_v1 = os.path.join(WORKTREE, res_v1["artifacts"]["video"])
        video_v2 = os.path.join(WORKTREE, res_v2["artifacts"]["video"])
        for path in (video_v1, video_v2):
            insp = build_video.validate_mp4(path, 1080, 1920, 30, 14.0)
            self.assertEqual(insp["videoStreams"], 1)
            self.assertEqual(insp["audioStreams"], 0)
            self.assertEqual(insp["duration"], 14.0)
            self.assertEqual(insp["pixFmt"], "yuv420p")

        # 4. Inspecao visual dos quadros: antes (t=2.0s), durante (t=7.0s) e depois (t=12.0s)
        frame_v1_pre = extract_raw_frame(video_v1, 2.0)
        frame_v2_pre = extract_raw_frame(video_v2, 2.0)
        mae_pre = calculate_mae(frame_v1_pre, frame_v2_pre, y_start=0, y_end=1920)
        self.assertLess(mae_pre, 0.5, f"Quadro antes do intervalo deveria ser visualmente igual, MAE={mae_pre}")

        frame_v1_post = extract_raw_frame(video_v1, 12.0)
        frame_v2_post = extract_raw_frame(video_v2, 12.0)
        mae_post = calculate_mae(frame_v1_post, frame_v2_post, y_start=0, y_end=1920)
        self.assertLess(mae_post, 0.5, f"Quadro depois do intervalo deveria ser visualmente igual, MAE={mae_post}")

        frame_v1_mid = extract_raw_frame(video_v1, 7.0)
        frame_v2_mid = extract_raw_frame(video_v2, 7.0)
        # Regiao superior (titulo): a diferenca entre os textos aparece aqui
        mae_title_region = calculate_mae(frame_v1_mid, frame_v2_mid, y_start=0, y_end=400)
        self.assertGreater(mae_title_region, 2.0, f"Regiao do titulo deveria diferir entre as versoes, MAE={mae_title_region}")
        # Regiao inferior (legenda e imagem de fundo): tolerante a compressao do codec (< 1.0)
        mae_bottom_region = calculate_mae(frame_v1_mid, frame_v2_mid, y_start=1200, y_end=1920)
        self.assertLess(mae_bottom_region, 1.0, f"Regiao inferior da legenda deveria ser igual, MAE={mae_bottom_region}")

        # 5. Reabertura e recalculacao de hashes de todos os arquivos publicados em ambos os manifestos
        for m in (manifest_v1, manifest_v2):
            self.assertIn("textOverlayPlan", m["artifacts"])
            for key, entry in m["artifacts"].items():
                file_path = os.path.join(WORKTREE, entry["path"])
                self.assertTrue(os.path.isfile(file_path))
                self.assertEqual(os.path.getsize(file_path), entry["bytes"])
                self.assertEqual(render_local.sha256_file(file_path), entry["sha256"])

    def test_13_text_overlay_reexecution_updates_same_destination(self):
        assoc = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        output_dir = os.path.join(self.tmp, "reexec-delivery")
        plan_v1_file = os.path.join(self.tmp, "plan_reexec_v1.json")
        plan_v2_file = os.path.join(self.tmp, "plan_reexec_v2.json")

        write_json(plan_v1_file, {
            "schemaVersion": 1,
            "caseId": "marca-salao-pipeline-pilot",
            "overlays": [{"beatId": "demonstration-body", "text": "TITULO VERSAO UM"}]
        })
        write_json(plan_v2_file, {
            "schemaVersion": 1,
            "caseId": "marca-salao-pipeline-pilot",
            "overlays": [{"beatId": "demonstration-body", "text": "TITULO VERSAO DOIS REVISADO"}]
        })

        # Primeira execucao
        render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc, output_dir, WORKTREE, None,
            text_overlays_path=plan_v1_file)
        hashes_v1 = delivery_hashes(output_dir)

        # Reexecucao com titulo revisado no mesmo destino
        render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc, output_dir, WORKTREE, None,
            text_overlays_path=plan_v2_file)
        hashes_v2 = delivery_hashes(output_dir)

        # Pacote, SRT e narracao permanecem identicos
        package_name = [k for k in hashes_v1 if k.endswith(".execution-package.json")][0]
        srt_name = [k for k in hashes_v1 if k.endswith("-captions.srt")][0]
        narration_name = [k for k in hashes_v1 if k.endswith("-narration-script.txt")][0]
        self.assertEqual(hashes_v1[package_name], hashes_v2[package_name])
        self.assertEqual(hashes_v1[srt_name], hashes_v2[srt_name])
        self.assertEqual(hashes_v1[narration_name], hashes_v2[narration_name])

        # Video e plano de titulos mudaram
        overlay_plan_name = [k for k in hashes_v1 if k.endswith("-text-overlay-plan.json")][0]
        video_name = [k for k in hashes_v1 if k.endswith("-primary-output.mp4")][0]
        self.assertNotEqual(hashes_v1[overlay_plan_name], hashes_v2[overlay_plan_name])
        self.assertNotEqual(hashes_v1[video_name], hashes_v2[video_name])

    def test_14_invalid_text_overlay_preserves_previous_delivery(self):
        assoc = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        output_dir = os.path.join(self.tmp, "preserve-invalid-overlay")
        valid_plan_file = os.path.join(self.tmp, "plan_valid.json")
        bad_plan_file = os.path.join(self.tmp, "plan_bad.json")

        write_json(valid_plan_file, {
            "schemaVersion": 1,
            "caseId": "marca-salao-pipeline-pilot",
            "overlays": [{"beatId": "demonstration-body", "text": "TITULO VALIDO"}]
        })
        write_json(bad_plan_file, {
            "schemaVersion": 1,
            "caseId": "marca-salao-pipeline-pilot",
            "overlays": [{"beatId": "beat-inexistente", "text": "TITULO INVALIDO"}]
        })

        render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc, output_dir, WORKTREE, None,
            text_overlays_path=valid_plan_file)
        hashes_before = delivery_hashes(output_dir)

        # Tentativa de renderizar com plano invalido
        with self.assertRaises(render_local.RenderInputError):
            render_pipeline.run_render_pipeline(
                os.path.join(WORKTREE, CASE_MS_REL), assoc, output_dir, WORKTREE, None,
                text_overlays_path=bad_plan_file)

        # Destino intacto
        self.assertEqual(hashes_before, delivery_hashes(output_dir))

    def test_15_concurrent_empty_destination_collision_revalidated_under_lock(self):
        assoc_ms = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        assoc_mh = self._prepare_assoc(ASSOC_MH_REL, self.assets_dir_mh)
        output_dir = os.path.join(self.tmp, "concurrent-collision")

        original_acquire = render_local.acquire_promotion_lock

        def simulate_concurrent_promotion(target_dir):
            lock = original_acquire(target_dir)
            # Simula que outro caso promoveu no mesmo destino enquanto o segundo renderizava:
            manifest_sim = {
                "schemaVersion": 1,
                "caseId": "marca-salao-pipeline-pilot",
                "packageId": "pkg-concorrente"
            }
            write_json(os.path.join(target_dir, "delivery-manifest.json"), manifest_sim)
            return lock

        with mock.patch("render_local.acquire_promotion_lock", side_effect=simulate_concurrent_promotion):
            with self.assertRaises(render_pipeline.DeliveryCollisionError) as ctx:
                render_pipeline.run_render_pipeline(
                    os.path.join(WORKTREE, CASE_MH_REL), assoc_mh, output_dir, WORKTREE, None)
            self.assertIn("colisao de entrega", str(ctx.exception))

    def test_16_visual_style_dual_render_reuses_visual_and_differs_in_title_region(self):
        assoc = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        out_a = os.path.join(self.tmp, "ms-style-a")
        out_b = os.path.join(self.tmp, "ms-style-b")

        overlays_data = {
            "schemaVersion": 1,
            "caseId": "marca-salao-pipeline-pilot",
            "overlays": [
                {"beatId": "demonstration-body", "text": "TITULO DE PROVA VISUAL"}
            ]
        }
        style_a_data = {
            "schemaVersion": 1,
            "id": "style-gold",
            "title": {
                "textColor": "#FFD700",
                "outlineColor": "#000000",
                "fontSize": 48,
                "marginTop": 180,
                "marginHorizontal": 80
            }
        }
        style_b_data = {
            "schemaVersion": 1,
            "id": "style-cyan",
            "title": {
                "textColor": "#00FFFF",
                "outlineColor": "#1A1A1A",
                "fontSize": 36,
                "marginTop": 240,
                "marginHorizontal": 100
            }
        }

        overlays_file = os.path.join(self.tmp, "overlays.json")
        style_a_file = os.path.join(self.tmp, "style_a.json")
        style_b_file = os.path.join(self.tmp, "style_b.json")
        write_json(overlays_file, overlays_data)
        write_json(style_a_file, style_a_data)
        write_json(style_b_file, style_b_data)

        res_a = render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc, out_a, WORKTREE, None,
            text_overlays_path=overlays_file, visual_style_path=style_a_file)
        self.assertEqual(res_a["status"], "completed")

        res_b = render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc, out_b, WORKTREE, None,
            text_overlays_path=overlays_file, visual_style_path=style_b_file)
        self.assertEqual(res_b["status"], "completed")

        with open(res_a["manifest"], "r", encoding="utf-8") as f:
            man_a = json.load(f)
        with open(res_b["manifest"], "r", encoding="utf-8") as f:
            man_b = json.load(f)

        # 1. Hashes identicos entre as duas versoes: pacote, srt, narracao, plano de titulos
        self.assertEqual(man_a["artifacts"]["package"]["sha256"], man_b["artifacts"]["package"]["sha256"])
        self.assertEqual(man_a["artifacts"]["srt"]["sha256"], man_b["artifacts"]["srt"]["sha256"])
        self.assertEqual(man_a["artifacts"]["narration"]["sha256"], man_b["artifacts"]["narration"]["sha256"])
        self.assertEqual(man_a["artifacts"]["textOverlayPlan"]["sha256"], man_b["artifacts"]["textOverlayPlan"]["sha256"])

        # 2. Hashes que diferem: video e estilo visual
        self.assertNotEqual(man_a["artifacts"]["video"]["sha256"], man_b["artifacts"]["video"]["sha256"])
        self.assertIn("visualStyle", man_a["artifacts"])
        self.assertIn("visualStyle", man_b["artifacts"])
        self.assertEqual(man_a["artifacts"]["visualStyle"]["styleId"], "style-gold")
        self.assertEqual(man_b["artifacts"]["visualStyle"]["styleId"], "style-cyan")
        self.assertNotEqual(man_a["artifacts"]["visualStyle"]["sha256"], man_b["artifacts"]["visualStyle"]["sha256"])

        # 3. Recalculo de todos os arquivos publicados em ambos os manifestos
        for man, out_dir in ((man_a, out_a), (man_b, out_b)):
            for key, artifact in man["artifacts"].items():
                target_path = os.path.join(WORKTREE, artifact["path"])
                self.assertTrue(os.path.isfile(target_path), f"Arquivo do manifesto ausente: {target_path}")
                self.assertEqual(render_local.sha256_file(target_path), artifact["sha256"], f"SHA divergente: {key}")
                self.assertEqual(os.path.getsize(target_path), artifact["bytes"], f"Tamanho divergente: {key}")

        # 4. Inspecao FFprobe
        for vid in (os.path.join(WORKTREE, man_a["artifacts"]["video"]["path"]),
                    os.path.join(WORKTREE, man_b["artifacts"]["video"]["path"])):
            insp = build_video.validate_mp4(vid, 1080, 1920, 30, 14.0)
            self.assertEqual(insp["videoStreams"], 1)
            self.assertEqual(insp["audioStreams"], 0)
            self.assertEqual(insp["duration"], 14.0)
            self.assertEqual(insp["pixFmt"], "yuv420p")

        # 5. Comparacao visual de quadros
        vid_a = os.path.join(WORKTREE, man_a["artifacts"]["video"]["path"])
        vid_b = os.path.join(WORKTREE, man_b["artifacts"]["video"]["path"])

        # Em t=2.0s (antes do beat demonstration-body que comeca em 4s): visualmente identicos (< 1.0)
        frame_a_pre = extract_raw_frame(vid_a, 2.0)
        frame_b_pre = extract_raw_frame(vid_b, 2.0)
        mae_pre = calculate_mae(frame_a_pre, frame_b_pre, width=1080, y_start=0, y_end=1920)
        self.assertLess(mae_pre, 1.0, f"Quadros antes do beat deveriam ser identicos, MAE={mae_pre}")

        # Em t=12.0s (apos o beat que termina em 10s): visualmente identicos (< 1.0)
        frame_a_post = extract_raw_frame(vid_a, 12.0)
        frame_b_post = extract_raw_frame(vid_b, 12.0)
        mae_post = calculate_mae(frame_a_post, frame_b_post, width=1080, y_start=0, y_end=1920)
        self.assertLess(mae_post, 1.0, f"Quadros apos o beat deveriam ser identicos, MAE={mae_post}")

        # Em t=7.0s (durante o beat demonstration-body):
        frame_a_mid = extract_raw_frame(vid_a, 7.0)
        frame_b_mid = extract_raw_frame(vid_b, 7.0)

        # Regiao superior do titulo (y=150 a y=320): diferenca visual significativa entre os estilos
        mae_title = calculate_mae(frame_a_mid, frame_b_mid, width=1080, y_start=150, y_end=320)
        self.assertGreater(mae_title, 2.0, f"Regiao do titulo deveria diferir entre estilos, MAE={mae_title}")

        # Regiao inferior (y=1200 a y=1800): diferenca insignificante (apenas ruido de compressao H.264)
        mae_bottom = calculate_mae(frame_a_mid, frame_b_mid, width=1080, y_start=1200, y_end=1800)
        self.assertLess(mae_bottom, 2.0, f"Regiao inferior nao deveria ter diferenca visual relevante, MAE={mae_bottom}")
        self.assertGreater(mae_title, mae_bottom, f"Diferenca no titulo ({mae_title}) deve superar ruido inferior ({mae_bottom})")

    def test_17_visual_style_shared_with_multitrack_hub(self):
        assoc = self._prepare_assoc(ASSOC_MH_REL, self.assets_dir_mh)
        out_mh = os.path.join(self.tmp, "mh-style-shared")

        overlays_data = {
            "schemaVersion": 1,
            "caseId": "multitrack-hub-pipeline-pilot",
            "overlays": [
                {"beatId": "opening-hook", "text": "RATEIOS MULTITRACK HUB"}
            ]
        }
        # Reutiliza o mesmo estilo gold definido para Marca Salao
        style_shared = {
            "schemaVersion": 1,
            "id": "style-gold",
            "title": {
                "textColor": "#FFD700",
                "outlineColor": "#000000",
                "fontSize": 48,
                "marginTop": 180,
                "marginHorizontal": 80
            }
        }
        overlays_file = os.path.join(self.tmp, "mh_overlays.json")
        style_file = os.path.join(self.tmp, "shared_style.json")
        write_json(overlays_file, overlays_data)
        write_json(style_file, style_shared)

        res = render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MH_REL), assoc, out_mh, WORKTREE, None,
            text_overlays_path=overlays_file, visual_style_path=style_file)
        self.assertEqual(res["status"], "completed")

        with open(res["manifest"], "r", encoding="utf-8") as f:
            man = json.load(f)

        self.assertIn("visualStyle", man["artifacts"])
        self.assertEqual(man["artifacts"]["visualStyle"]["styleId"], "style-gold")
        self.assertEqual(man.get("visualStyleId"), "style-gold")

        # Recalculo de todos os arquivos
        for key, artifact in man["artifacts"].items():
            target_path = os.path.join(WORKTREE, artifact["path"])
            self.assertTrue(os.path.isfile(target_path))
            self.assertEqual(render_local.sha256_file(target_path), artifact["sha256"])

        # FFprobe Multitrack Hub: 1080x1920@30, 15.0s, 0 audio
        vid = os.path.join(WORKTREE, man["artifacts"]["video"]["path"])
        insp = build_video.validate_mp4(vid, 1080, 1920, 30, 15.0)
        self.assertEqual(insp["videoStreams"], 1)
        self.assertEqual(insp["audioStreams"], 0)
        self.assertEqual(insp["duration"], 15.0)
        self.assertEqual(insp["pixFmt"], "yuv420p")

    def test_18_empty_text_overlay_plan_tracked_and_renders_without_title_filter(self):
        assoc = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        out_dir = os.path.join(self.tmp, "ms-empty-overlays")

        empty_overlays = {
            "schemaVersion": 1,
            "caseId": "marca-salao-pipeline-pilot",
            "overlays": []
        }
        overlays_file = os.path.join(self.tmp, "empty_overlays.json")
        write_json(overlays_file, empty_overlays)

        res = render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc, out_dir, WORKTREE, None,
            text_overlays_path=overlays_file)
        self.assertEqual(res["status"], "completed")

        with open(res["manifest"], "r", encoding="utf-8") as f:
            man = json.load(f)

        # O plano com overlays: [] deve ser gravado e rastreado no manifesto
        self.assertIn("textOverlayPlan", man["artifacts"])
        plan_path = os.path.join(WORKTREE, man["artifacts"]["textOverlayPlan"]["path"])
        self.assertTrue(os.path.isfile(plan_path))
        with open(plan_path, "r", encoding="utf-8") as f:
            saved_plan = json.load(f)
        self.assertEqual(saved_plan["overlays"], [])

        # O video e gerado perfeitamente sem falhas
        vid = os.path.join(WORKTREE, man["artifacts"]["video"]["path"])
        insp = build_video.validate_mp4(vid, 1080, 1920, 30, 14.0)
        self.assertEqual(insp["videoStreams"], 1)
        self.assertEqual(insp["audioStreams"], 0)
        self.assertEqual(insp["duration"], 14.0)

    def test_19_invalid_visual_style_preserves_previous_delivery(self):
        assoc = self._prepare_assoc(ASSOC_MS_REL, self.assets_dir_ms)
        output_dir = os.path.join(self.tmp, "preserve-invalid-style")

        valid_style = {
            "schemaVersion": 1,
            "id": "valid-style",
            "title": {
                "textColor": "#FFFFFF",
                "outlineColor": "#000000",
                "fontSize": 42,
                "marginTop": 160,
                "marginHorizontal": 60
            }
        }
        bad_style = {
            "schemaVersion": 1,
            "id": "bad-style",
            "title": {
                "textColor": "#FFFFFF",
                "outlineColor": "#000000",
                "fontSize": 999,  # Acima de 160
                "marginTop": 160,
                "marginHorizontal": 60
            }
        }
        valid_file = os.path.join(self.tmp, "valid_style.json")
        bad_file = os.path.join(self.tmp, "bad_style.json")
        write_json(valid_file, valid_style)
        write_json(bad_file, bad_style)

        render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), assoc, output_dir, WORKTREE, None,
            visual_style_path=valid_file)
        hashes_before = delivery_hashes(output_dir)

        # Tentativa de renderizar com visual-style invalido
        with self.assertRaises(render_local.RenderInputError):
            render_pipeline.run_render_pipeline(
                os.path.join(WORKTREE, CASE_MS_REL), assoc, output_dir, WORKTREE, None,
                visual_style_path=bad_file)

        # Destino intacto
        self.assertEqual(hashes_before, delivery_hashes(output_dir))


class AssetManifestPipelineTests(unittest.TestCase):
    """Testes de ponta a ponta do inventario de midia (AssetManifest v1)."""

    @classmethod
    def setUpClass(cls):
        if not HAS_BRIDGE:
            if REQUIRE_RENDER:
                raise RuntimeError("build da platform ausente e REQUIRE_RENDER=1")
            raise unittest.SkipTest("build da platform ausente")
        if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
            if REQUIRE_RENDER:
                raise RuntimeError("ffmpeg/ffprobe ausentes e REQUIRE_RENDER=1")
            raise unittest.SkipTest("ffmpeg/ffprobe ausentes")

    def setUp(self):
        os.makedirs(TMP_BASE, exist_ok=True)
        short_tag = hashlib.sha1(self._testMethodName.encode("utf-8")).hexdigest()[:8]
        self.tmp = os.path.join(TMP_BASE, f"am-{short_tag}")
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.makedirs(self.tmp, exist_ok=True)
        self.media_dir = os.path.join(self.tmp, "media")
        os.makedirs(self.media_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _build_mixed_media_ms(self):
        shared_img = os.path.join(self.media_dir, "shared-card.png")
        clip_mp4 = os.path.join(self.media_dir, "demo-clip.mp4")
        make_proof_assets.write_scene_png(shared_img, "marca-salao", "opening-hook", 1)
        make_proof_assets.write_scene_mp4(clip_mp4, "marca-salao", "demonstration-body", 2, duration_s=6.0)

        base_assoc = read_json(os.path.join(WORKTREE, ASSOC_MS_REL))
        assoc_path = os.path.join(self.tmp, "ms-mixed.assets.json")
        rel_img = render_local.rel(WORKTREE, shared_img)
        rel_vid = render_local.rel(WORKTREE, clip_mp4)
        assoc_data = {
            "schemaVersion": 1,
            "packageId": base_assoc["packageId"],
            "assets": [
                {"beatId": "opening-hook", "path": rel_img},
                {"beatId": "demonstration-body", "path": rel_vid},
                {"beatId": "closing-cta", "path": rel_img},
            ],
        }
        write_json(assoc_path, assoc_data)
        return shared_img, clip_mp4, assoc_path

    def test_01_prepare_manifest_deduplication_license_and_source_preservation(self):
        shared_img, clip_mp4, assoc_path = self._build_mixed_media_ms()
        img_hash_before = render_local.sha256_file(shared_img)
        vid_hash_before = render_local.sha256_file(clip_mp4)
        assoc_hash_before = render_local.sha256_file(assoc_path)

        out_pending = os.path.join(self.tmp, "ms-pending.asset-manifest.json")
        res = subprocess.run(
            [sys.executable, os.path.join(WORKTREE, "tools", "prepare_asset_manifest.py"),
             "--case", os.path.join(WORKTREE, CASE_MS_REL),
             "--assets", assoc_path,
             "--origin", "synthetic-proof-unit",
             "--output", out_pending,
             "--root", WORKTREE, "--json"],
            capture_output=True, text=True, cwd=WORKTREE)
        self.assertEqual(res.returncode, 0, res.stderr)
        summary = json.loads(res.stdout)
        self.assertEqual(summary["assetCount"], 2)
        self.assertEqual(summary["bindingCount"], 3)
        self.assertEqual(summary["deduplicatedCount"], 1)

        manifest = read_json(out_pending)
        self.assertEqual(len(manifest["assets"]), 2)
        self.assertEqual(len(manifest["bindings"]), 3)
        for entry in manifest["assets"]:
            self.assertEqual(entry["origin"], "synthetic-proof-unit")
            self.assertEqual(entry["license"], "pending")
        self.assertEqual(manifest["bindings"][0]["assetId"], manifest["bindings"][2]["assetId"])

        out_declared = os.path.join(self.tmp, "ms-declared.asset-manifest.json")
        summary2 = prepare_asset_manifest.prepare_manifest(
            os.path.join(WORKTREE, CASE_MS_REL), assoc_path, "local-studio",
            out_declared, WORKTREE, license_value="owned-synthetic"
        )
        self.assertEqual(summary2["manifest"]["assets"][0]["license"], "owned-synthetic")
        self.assertEqual(render_local.sha256_file(shared_img), img_hash_before)
        self.assertEqual(render_local.sha256_file(clip_mp4), vid_hash_before)
        self.assertEqual(render_local.sha256_file(assoc_path), assoc_hash_before)

    def test_02_plan_only_with_asset_manifest_skips_media_io_and_ffmpeg(self):
        base_assoc = read_json(os.path.join(WORKTREE, ASSOC_MS_REL))
        ghost_manifest = {
            "schemaVersion": 1,
            "caseId": "marca-salao-pipeline-pilot",
            "packageId": base_assoc["packageId"],
            "assets": [
                {
                    "id": "asset-ghost-img",
                    "type": "image",
                    "path": ".workspace/tmp/inexistent-ghost-dir/missing-a.png",
                    "bytes": 1234,
                    "sha256": "a" * 64,
                    "origin": "synthetic-proof",
                    "license": "pending",
                }
            ],
            "bindings": [
                {"beatId": "opening-hook", "assetId": "asset-ghost-img"},
                {"beatId": "demonstration-body", "assetId": "asset-ghost-img"},
                {"beatId": "closing-cta", "assetId": "asset-ghost-img"},
            ],
        }
        manifest_path = os.path.join(self.tmp, "ghost.asset-manifest.json")
        write_json(manifest_path, ghost_manifest)

        with mock.patch("build_video.get_ffmpeg", side_effect=AssertionError("nao deveria chamar ffmpeg")), \
             mock.patch("build_video.get_ffprobe", side_effect=AssertionError("nao deveria chamar ffprobe")):
            plan = render_pipeline.run_plan_only(
                os.path.join(WORKTREE, CASE_MS_REL), WORKTREE, asset_manifest_path=manifest_path)

        self.assertEqual(plan["assetManifest"]["assetCount"], 1)
        self.assertEqual(len(plan["assetManifest"]["resolvedBindings"]), 3)

        bad_manifest = json.loads(json.dumps(ghost_manifest))
        bad_manifest["bindings"][1]["assetId"] = "asset-inexistente"
        bad_path = os.path.join(self.tmp, "bad-ref.asset-manifest.json")
        write_json(bad_path, bad_manifest)
        res = subprocess.run(
            [sys.executable, os.path.join(WORKTREE, "tools", "render_pipeline.py"),
             "--case", os.path.join(WORKTREE, CASE_MS_REL),
             "--asset-manifest", bad_path,
             "--plan-only", "--json"],
            capture_output=True, text=True, cwd=WORKTREE)
        self.assertEqual(res.returncode, 3)
        self.assertIn("UNKNOWN_ASSET_REFERENCE", res.stderr)

    def test_03_check_assets_inspects_reused_asset_once_without_output_dir(self):
        _, _, assoc_path = self._build_mixed_media_ms()
        manifest_path = os.path.join(self.tmp, "ms.asset-manifest.json")
        prepare_asset_manifest.prepare_manifest(
            os.path.join(WORKTREE, CASE_MS_REL), assoc_path, "synthetic-proof", manifest_path, WORKTREE
        )

        with mock.patch("render_local.probe_asset", wraps=render_local.probe_asset) as spy_probe:
            report = render_pipeline.run_check_assets(
                os.path.join(WORKTREE, CASE_MS_REL), manifest_path, WORKTREE
            )
        self.assertEqual(report["status"], "assets-verified")
        self.assertEqual(report["assetCount"], 2)
        self.assertEqual(report["bindingCount"], 3)
        self.assertEqual(spy_probe.call_count, 2)

        cli = subprocess.run(
            [sys.executable, os.path.join(WORKTREE, "tools", "render_pipeline.py"),
             "--case", os.path.join(WORKTREE, CASE_MS_REL),
             "--asset-manifest", manifest_path,
             "--check-assets", "--json"],
            capture_output=True, text=True, cwd=WORKTREE)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        cli_json = json.loads(cli.stdout)
        self.assertEqual(cli_json["status"], "assets-verified")
        self.assertEqual(len(cli_json["resolvedBindings"]), 3)

    def test_04_e2e_render_marca_salao_combined_asset_manifest_overlays_and_style(self):
        _, _, assoc_path = self._build_mixed_media_ms()
        manifest_path = os.path.join(self.tmp, "ms.asset-manifest.json")
        prepare_asset_manifest.prepare_manifest(
            os.path.join(WORKTREE, CASE_MS_REL), assoc_path, "synthetic-proof", manifest_path, WORKTREE,
            license_value="owned-synthetic"
        )
        overlays_path = os.path.join(self.tmp, "ms-overlays.json")
        style_path = os.path.join(self.tmp, "ms-style.json")
        write_json(overlays_path, {
            "schemaVersion": 1,
            "caseId": "marca-salao-pipeline-pilot",
            "overlays": [{"beatId": "demonstration-body", "text": "TITULO DE INVENTARIO"}],
        })
        write_json(style_path, {
            "schemaVersion": 1,
            "id": "style-gold",
            "title": {
                "textColor": "#FFD700",
                "outlineColor": "#000000",
                "fontSize": 48,
                "marginTop": 180,
                "marginHorizontal": 80,
            },
        })

        out_dir = os.path.join(self.tmp, "delivery-ms-combined")
        res = render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), None, out_dir, WORKTREE, None,
            text_overlays_path=overlays_path, visual_style_path=style_path,
            asset_manifest_path=manifest_path,
        )
        self.assertEqual(res["status"], "completed")
        self.assertEqual(res.get("visualStyleId"), "style-gold")
        self.assertIn("assetManifest", res["artifacts"])

        delivery = read_json(os.path.join(WORKTREE, res["manifest"]))
        self.assertIn("assetManifest", delivery["artifacts"])
        self.assertEqual(delivery["assetManifestSummary"]["caseId"], "marca-salao-pipeline-pilot")
        self.assertEqual(delivery["assetManifestSummary"]["assetCount"], 2)
        for key, artifact in delivery["artifacts"].items():
            full_path = os.path.join(WORKTREE, artifact["path"])
            self.assertTrue(os.path.isfile(full_path), f"artefato ausente: {key}")
            self.assertEqual(os.path.getsize(full_path), artifact["bytes"])
            self.assertEqual(render_local.sha256_file(full_path), artifact["sha256"])

        report = read_json(os.path.join(WORKTREE, delivery["artifacts"]["report"]["path"]))
        self.assertEqual(len(report["assets"]), 3)
        self.assertEqual(report["assets"][0]["assetId"], report["assets"][2]["assetId"])
        self.assertEqual(report["assets"][1]["type"], "video")
        self.assertGreaterEqual(report["assets"][1]["durationSeconds"], 6.0)

        vid_path = os.path.join(WORKTREE, delivery["artifacts"]["video"]["path"])
        insp = build_video.validate_mp4(vid_path, 1080, 1920, 30, 14.0)
        self.assertEqual(insp["videoStreams"], 1)
        self.assertEqual(insp["audioStreams"], 0)
        self.assertEqual(insp["duration"], 14.0)
        self.assertEqual(insp["pixFmt"], "yuv420p")

        srt_path = os.path.join(WORKTREE, delivery["artifacts"]["srt"]["path"])
        self.assertEqual(srt_validate.validate_srt_file(srt_path, 14.0), [])
        narration_path = os.path.join(WORKTREE, delivery["artifacts"]["narration"]["path"])
        with open(narration_path, "r", encoding="utf-8") as handle:
            self.assertTrue(handle.read().strip())

    def test_05_e2e_render_multitrack_hub_from_asset_manifest(self):
        shared_img = os.path.join(self.media_dir, "mh-shared.png")
        clip_mp4 = os.path.join(self.media_dir, "mh-demo.mp4")
        make_proof_assets.write_scene_png(shared_img, "multitrack-hub", "opening-hook", 1)
        make_proof_assets.write_scene_mp4(clip_mp4, "multitrack-hub", "demonstration-body", 2, duration_s=5.0)

        base_assoc = read_json(os.path.join(WORKTREE, ASSOC_MH_REL))
        assoc_path = os.path.join(self.tmp, "mh.assets.json")
        rel_img = render_local.rel(WORKTREE, shared_img)
        rel_vid = render_local.rel(WORKTREE, clip_mp4)
        write_json(assoc_path, {
            "schemaVersion": 1,
            "packageId": base_assoc["packageId"],
            "assets": [
                {"beatId": "opening-hook", "path": rel_img},
                {"beatId": "demonstration-body", "path": rel_vid},
                {"beatId": "explanation-body", "path": rel_img},
                {"beatId": "closing-cta", "path": rel_img},
            ],
        })
        manifest_path = os.path.join(self.tmp, "mh.asset-manifest.json")
        prepare_asset_manifest.prepare_manifest(
            os.path.join(WORKTREE, CASE_MH_REL), assoc_path, "synthetic-proof-mh", manifest_path, WORKTREE
        )

        out_dir = os.path.join(self.tmp, "delivery-mh")
        res = render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MH_REL), None, out_dir, WORKTREE, None,
            asset_manifest_path=manifest_path,
        )
        self.assertEqual(res["status"], "completed")
        delivery = read_json(os.path.join(WORKTREE, res["manifest"]))
        self.assertEqual(delivery["assetManifestSummary"]["assetCount"], 2)
        for artifact in delivery["artifacts"].values():
            full_path = os.path.join(WORKTREE, artifact["path"])
            self.assertEqual(render_local.sha256_file(full_path), artifact["sha256"])

        vid_path = os.path.join(WORKTREE, delivery["artifacts"]["video"]["path"])
        insp = build_video.validate_mp4(vid_path, 1080, 1920, 30, 15.0)
        self.assertEqual(insp["videoStreams"], 1)
        self.assertEqual(insp["audioStreams"], 0)
        self.assertEqual(insp["duration"], 15.0)

    def test_06_tampered_asset_aborts_before_ffmpeg_and_preserves_delivery(self):
        shared_img, _, assoc_path = self._build_mixed_media_ms()
        manifest_path = os.path.join(self.tmp, "ms-tamper.asset-manifest.json")
        prepare_asset_manifest.prepare_manifest(
            os.path.join(WORKTREE, CASE_MS_REL), assoc_path, "synthetic-proof", manifest_path, WORKTREE
        )

        out_dir = os.path.join(self.tmp, "delivery-tamper")
        render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), None, out_dir, WORKTREE, None,
            asset_manifest_path=manifest_path,
        )
        hashes_before = delivery_hashes(out_dir)

        # Adultera 1 byte sem alterar o tamanho do arquivo -> dispara ASSET_HASH_MISMATCH
        with open(shared_img, "r+b") as handle:
            original_byte = handle.read(1)
            handle.seek(0)
            handle.write(bytes([original_byte[0] ^ 0xFF]))

        with mock.patch("render_local.build_render_command",
                        side_effect=AssertionError("nao deveria montar comando ffmpeg")):
            with self.assertRaises(build_video.DeliveryError) as ctx:
                render_pipeline.run_render_pipeline(
                    os.path.join(WORKTREE, CASE_MS_REL), None, out_dir, WORKTREE, None,
                    asset_manifest_path=manifest_path,
                )
        self.assertIn("ASSET_HASH_MISMATCH", str(ctx.exception))
        self.assertEqual(hashes_before, delivery_hashes(out_dir))

    def test_07_asset_manifest_failure_diagnostics_and_rollback(self):
        shared_img, clip_mp4, assoc_path = self._build_mixed_media_ms()
        manifest_path = os.path.join(self.tmp, "ms-fail.asset-manifest.json")
        prepare_asset_manifest.prepare_manifest(
            os.path.join(WORKTREE, CASE_MS_REL), assoc_path, "synthetic-proof", manifest_path, WORKTREE
        )

        # 1. Video mais curto que a duracao do beat (1.0s < 6.0s)
        short_clip = os.path.join(self.media_dir, "short-demo.mp4")
        make_proof_assets.write_scene_mp4(short_clip, "marca-salao", "demonstration-body", 2, duration_s=1.0)
        short_assoc = os.path.join(self.tmp, "short.assets.json")
        base_assoc = read_json(os.path.join(WORKTREE, ASSOC_MS_REL))
        rel_img = render_local.rel(WORKTREE, shared_img)
        rel_short = render_local.rel(WORKTREE, short_clip)
        write_json(short_assoc, {
            "schemaVersion": 1,
            "packageId": base_assoc["packageId"],
            "assets": [
                {"beatId": "opening-hook", "path": rel_img},
                {"beatId": "demonstration-body", "path": rel_short},
                {"beatId": "closing-cta", "path": rel_img},
            ],
        })
        short_manifest = os.path.join(self.tmp, "short.asset-manifest.json")
        prepare_asset_manifest.prepare_manifest(
            os.path.join(WORKTREE, CASE_MS_REL), short_assoc, "synthetic-proof", short_manifest, WORKTREE
        )
        with self.assertRaises(build_video.DeliveryError) as short_ctx:
            render_pipeline.run_check_assets(os.path.join(WORKTREE, CASE_MS_REL), short_manifest, WORKTREE)
        self.assertIn("ASSET_VIDEO_TOO_SHORT", str(short_ctx.exception))

        # 2. Asset corrompido (junk com mesmo nome e extensao .png)
        corrupt_img = os.path.join(self.media_dir, "corrupt.png")
        with open(corrupt_img, "wb") as handle:
            handle.write(b"nao-e-um-png-valido-1234567890")
        corrupt_assoc = os.path.join(self.tmp, "corrupt.assets.json")
        write_json(corrupt_assoc, {
            "schemaVersion": 1,
            "packageId": base_assoc["packageId"],
            "assets": [
                {"beatId": step["beatId"], "path": render_local.rel(WORKTREE, corrupt_img)}
                for step in base_assoc["assets"]
            ],
        })
        corrupt_manifest = os.path.join(self.tmp, "corrupt.asset-manifest.json")
        prepare_asset_manifest.prepare_manifest(
            os.path.join(WORKTREE, CASE_MS_REL), corrupt_assoc, "synthetic-proof", corrupt_manifest, WORKTREE
        )
        with self.assertRaises(build_video.DeliveryError) as corrupt_ctx:
            render_pipeline.run_check_assets(os.path.join(WORKTREE, CASE_MS_REL), corrupt_manifest, WORKTREE)
        self.assertIn("ASSET_CORRUPTED", str(corrupt_ctx.exception))

        # 3. Falha na promocao preserva entrega anterior
        out_dir = os.path.join(self.tmp, "delivery-rollback")
        render_pipeline.run_render_pipeline(
            os.path.join(WORKTREE, CASE_MS_REL), None, out_dir, WORKTREE, None,
            asset_manifest_path=manifest_path,
        )
        hashes_before = delivery_hashes(out_dir)
        with mock.patch("render_local.promote_with_backup",
                        side_effect=build_video.DeliveryError("falha simulada na promocao")):
            with self.assertRaises(build_video.DeliveryError):
                render_pipeline.run_render_pipeline(
                    os.path.join(WORKTREE, CASE_MS_REL), None, out_dir, WORKTREE, None,
                    asset_manifest_path=manifest_path,
                )
        self.assertEqual(hashes_before, delivery_hashes(out_dir))

        # 4. Asset ausente apos montagem do inventario
        os.remove(clip_mp4)
        with self.assertRaises(build_video.DeliveryError) as miss_ctx:
            render_pipeline.run_check_assets(os.path.join(WORKTREE, CASE_MS_REL), manifest_path, WORKTREE)
        self.assertIn("ASSET_MISSING", str(miss_ctx.exception))

        # 5. Flags conflitantes na CLI devolvem codigo 2
        conflict_1 = subprocess.run(
            [sys.executable, os.path.join(WORKTREE, "tools", "render_pipeline.py"),
             "--case", os.path.join(WORKTREE, CASE_MS_REL),
             "--assets", assoc_path,
             "--asset-manifest", manifest_path,
             "--output-dir", out_dir],
            capture_output=True, text=True, cwd=WORKTREE)
        self.assertEqual(conflict_1.returncode, 2)

        conflict_2 = subprocess.run(
            [sys.executable, os.path.join(WORKTREE, "tools", "render_pipeline.py"),
             "--case", os.path.join(WORKTREE, CASE_MS_REL),
             "--asset-manifest", manifest_path,
             "--check-assets",
             "--output-dir", out_dir],
            capture_output=True, text=True, cwd=WORKTREE)
        self.assertEqual(conflict_2.returncode, 2)


def extract_raw_frame(video_path, timestamp_s, width=1080, height=1920):
    cmd = [
        build_video.get_ffmpeg(),
        "-ss", f"{timestamp_s:.3f}",
        "-i", video_path,
        "-vframes", "1",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-"
    ]
    res = subprocess.run(cmd, capture_output=True, timeout=render_local.PROBE_TIMEOUT_SECONDS)
    if res.returncode != 0:
        raise RuntimeError(f"Falha ao extrair quadro em t={timestamp_s}")
    expected_size = width * height * 3
    if len(res.stdout) < expected_size:
        raise RuntimeError(f"Tamanho de quadro insuficiente: {len(res.stdout)} < {expected_size}")
    return res.stdout[:expected_size]


def calculate_mae(frame_a, frame_b, width=1080, y_start=0, y_end=1920):
    bytes_per_row = width * 3
    start_offset = y_start * bytes_per_row
    end_offset = y_end * bytes_per_row
    slice_a = frame_a[start_offset:end_offset]
    slice_b = frame_b[start_offset:end_offset]
    diff = sum(abs(a - b) for a, b in zip(slice_a, slice_b))
    return diff / float(len(slice_a))


if __name__ == "__main__":
    unittest.main()
