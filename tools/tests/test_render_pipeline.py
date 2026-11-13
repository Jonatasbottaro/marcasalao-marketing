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


if __name__ == "__main__":
    unittest.main()
