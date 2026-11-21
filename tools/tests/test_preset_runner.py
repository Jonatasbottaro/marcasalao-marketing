"""Testes automatizados (unittest) para o motor generico de presets tools/preset_runner.py.

Cobre obrigatoriamente:
  1. Renderizacao saas-demo (marca-salao): MP4 1080x1920 @ 30 fps, 0 streams de audio (-an).
  2. Renderizacao shorts-completo (multitrack-hub): MP4 1080x1920 @ 30 fps, 1 stream de audio AAC.
  3. Bloqueio de guardrails: falha ANTES de renderizar quando o roteiro/SRT contem
     frase proibida (ex.: "WhatsApp automático" no marca-salao) ou quando --audio e
     passado para um tenant com allowAudioTrack: false.
  4. Integridade do manifesto e storyboard: existencia e validade dos hashes SHA-256
     em manifest.json e geracao do preview-storyboard.png.

Os testes rendem video de verdade com FFmpeg/FFprobe (binarios em .workspace/tools/ffmpeg,
igual ao CI).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

# Garante ffmpeg/ffprobe no PATH do processo de teste (espelha o CI, que injeta o binario).
# Resolve a raiz PRINCIPAL via git-common-dir para achar .workspace/tools/ffmpeg
# compartilhado entre worktrees (o ffmpeg e instalado no checkout principal).
if shutil.which("ffmpeg") is None:
    _ffmpeg_candidates = []
    try:
        _common = subprocess.run(
            ["git", "-C", REPO_ROOT, "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout.strip()
        if _common:
            if not os.path.isabs(_common):
                _common = os.path.join(REPO_ROOT, _common)
            _main_root = os.path.dirname(os.path.abspath(os.path.normpath(_common)))
            _ffmpeg_candidates.append(os.path.join(_main_root, ".workspace", "tools", "ffmpeg"))
    except (OSError, subprocess.SubprocessError):
        pass
    _ffmpeg_candidates.append(os.path.join(REPO_ROOT, ".workspace", "tools", "ffmpeg"))
    for _ffmpeg_dir in _ffmpeg_candidates:
        if os.path.isdir(_ffmpeg_dir):
            os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
            break

import build_video  # noqa: E402
import preset_runner  # noqa: E402
import render_local  # noqa: E402
import srt_validate  # noqa: E402
import tenant_validator  # noqa: E402

TEST_TMP_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "test_preset_runner")

MS_TENANT = "marca-salao"
MS_CONFIG = "tenants/marca-salao/campaigns/camp-saas-demo-marca-salao-001.json"
MS_SLUG = "camp-saas-demo-marca-salao-001"

MTH_TENANT = "multitrack-hub"
MTH_CONFIG = "tenants/multitrack-hub/campaigns/camp-shorts-completo-multitrack-001.json"
MTH_SLUG = "camp-shorts-completo-multitrack-001"


def _clean_dir(path: str) -> str:
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)
    return path


def _generate_test_audio(path: str, duration_s: float = 30.0) -> str:
    """Gera um arquivo de audio WAV limpo (silencio) via FFmpeg lavfi para testes."""
    ffmpeg = build_video.get_ffmpeg()
    res = subprocess.run(
        [ffmpeg, "-y", "-f", "lavfi", "-i",
         "anullsrc=channel_layout=stereo:sample_rate=44100", "-t", f"{duration_s:.3f}",
         str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    if res.returncode != 0 or not os.path.isfile(path):
        raise build_video.DeliveryError(
            "falha ao gerar arquivo de audio de teste: " + res.stderr[-240:]
        )
    return str(path)


class PresetRunnerTest(unittest.TestCase):
    MS_MANIFEST: dict
    MTH_MANIFEST: dict
    MTH_AUDIO_MANIFEST: dict

    @classmethod
    def setUpClass(cls) -> None:
        _clean_dir(TEST_TMP_ROOT)

        cls.ms_output = _clean_dir(os.path.join(TEST_TMP_ROOT, "marca-salao-saas-demo"))
        cls.mth_output = _clean_dir(os.path.join(TEST_TMP_ROOT, "multitrack-hub-shorts"))
        cls.mth_audio_output = _clean_dir(os.path.join(TEST_TMP_ROOT, "multitrack-hub-audio"))
        cls.forbidden_output = _clean_dir(os.path.join(TEST_TMP_ROOT, "marca-salao-forbidden"))
        cls.audio_reject_output = _clean_dir(os.path.join(TEST_TMP_ROOT, "marca-salao-audio-reject"))

        # Audio externo para o teste de mixagem (multitrack-hub permite audio).
        cls.test_audio_path = _generate_test_audio(
            os.path.join(TEST_TMP_ROOT, "test-audio-externo.wav"), duration_s=30.0
        )

        # Render real: saas-demo (marca-salao) -> deve ficar sem audio (-an).
        cls.MS_MANIFEST = preset_runner.run_preset_pipeline(
            MS_TENANT, MS_CONFIG, cls.ms_output, audio_path=None, root=REPO_ROOT,
        )
        # Render real: shorts-completo (multitrack-hub) -> gera audio anullsrc (AAC).
        cls.MTH_MANIFEST = preset_runner.run_preset_pipeline(
            MTH_TENANT, MTH_CONFIG, cls.mth_output, audio_path=None, root=REPO_ROOT,
        )
        # Render real: shorts-completo com audio externo fornecido via --audio.
        cls.MTH_AUDIO_MANIFEST = preset_runner.run_preset_pipeline(
            MTH_TENANT, MTH_CONFIG, cls.mth_audio_output,
            audio_path=cls.test_audio_path, root=REPO_ROOT,
        )

    def _artifact_path(self, manifest: dict, kind: str) -> str:
        return os.path.join(REPO_ROOT, manifest["artifacts"][kind]["path"])

    # ------------------------------------------------------------------
    # 1. Renderizacao saas-demo (marca-salao): 1080x1920, 30 fps, 0 audio
    # ------------------------------------------------------------------
    def test_01_saas_demo_marca_salao_zero_audio(self) -> None:
        m = self.MS_MANIFEST
        self.assertEqual(m["tenantId"], MS_TENANT)
        self.assertEqual(m["preset"], "saas-demo")
        self.assertFalse(m["guardrails"]["allowAudioTrack"])

        video = m["artifacts"]["video"]
        fp = video["ffprobe"]
        self.assertEqual(fp["width"], 1080)
        self.assertEqual(fp["height"], 1920)
        self.assertEqual(fp["fps"], 30.0)
        self.assertEqual(fp["audioStreams"], 0)
        self.assertEqual(fp["codec"], "h264")
        self.assertEqual(fp["pixFmt"], "yuv420p")
        self.assertAlmostEqual(fp["duration"], 30.0, places=1)

        # Artefatos fisicos existem.
        for kind in ("video", "srt", "narration", "storyboard"):
            abs_p = self._artifact_path(m, kind)
            self.assertTrue(os.path.isfile(abs_p), f"artefato ausente: {kind} -> {abs_p}")

        # Copia do MP4 no arquivo (.workspace/archives/<slug>/).
        archive_video = os.path.join(REPO_ROOT, video["archivePath"])
        self.assertTrue(os.path.isfile(archive_video), f"arquivo de video ausente: {archive_video}")
        self.assertEqual(
            render_local.sha256_file(archive_video), render_local.sha256_file(self._artifact_path(m, "video"))
        )

        # SRT valido e sincronizado com a duracao.
        srt_abs = self._artifact_path(m, "srt")
        self.assertEqual(srt_validate.validate_srt_file(srt_abs, duration=30.0), [])

        # Storyboard 1080x1920 (grade 2x2).
        sb_abs = self._artifact_path(m, "storyboard")
        probe_sb = build_video.probe_media(sb_abs)
        sb_stream = probe_sb["streams"][0]
        self.assertEqual(int(sb_stream["width"]), 1080)
        self.assertEqual(int(sb_stream["height"]), 1920)

    # ------------------------------------------------------------------
    # 2. Renderizacao shorts-completo (multitrack-hub): 1080x1920, 30 fps, 1 audio AAC
    # ------------------------------------------------------------------
    def test_02_shorts_completo_multitrack_hub_one_audio_aac(self) -> None:
        m = self.MTH_MANIFEST
        self.assertEqual(m["tenantId"], MTH_TENANT)
        self.assertEqual(m["preset"], "shorts-completo")
        self.assertTrue(m["guardrails"]["allowAudioTrack"])
        self.assertEqual(m["audio"]["source"], "anullsrc")

        video = m["artifacts"]["video"]
        fp = video["ffprobe"]
        self.assertEqual(fp["width"], 1080)
        self.assertEqual(fp["height"], 1920)
        self.assertEqual(fp["fps"], 30.0)
        self.assertEqual(fp["audioStreams"], 1)
        self.assertEqual(fp["audioCodec"], "aac")
        self.assertEqual(fp["codec"], "h264")
        self.assertEqual(fp["pixFmt"], "yuv420p")
        self.assertAlmostEqual(fp["duration"], 30.0, places=1)

        for kind in ("video", "srt", "narration", "storyboard"):
            abs_p = self._artifact_path(m, kind)
            self.assertTrue(os.path.isfile(abs_p), f"artefato ausente: {kind} -> {abs_p}")

        self.assertEqual(srt_validate.validate_srt_file(self._artifact_path(m, "srt"), duration=30.0), [])

    # ------------------------------------------------------------------
    # 2b. Audio externo mixado e codificado em AAC (capacidade --audio)
    # ------------------------------------------------------------------
    def test_03_external_audio_mixed_aac(self) -> None:
        m = self.MTH_AUDIO_MANIFEST
        self.assertEqual(m["audio"]["source"], "external")
        fp = m["artifacts"]["video"]["ffprobe"]
        self.assertEqual(fp["audioStreams"], 1)
        self.assertEqual(fp["audioCodec"], "aac")
        self.assertAlmostEqual(fp["duration"], 30.0, places=1)

    # ------------------------------------------------------------------
    # 3. Bloqueio de guardrails (falha ANTES de renderizar)
    # ------------------------------------------------------------------
    def test_04_forbidden_claim_in_script_blocks_before_render(self) -> None:
        # Config do marca-salao com uma frase proibida ("WhatsApp automático")
        # injetada na legenda de uma cena.
        with open(os.path.join(REPO_ROOT, MS_CONFIG), "r", encoding="utf-8") as handle:
            forbidden_config = json.load(handle)
        forbidden_config["id"] = "camp-saas-demo-marca-salao-forbidden"
        forbidden_config["scenes"][0]["caption"] = (
            "Envio de WhatsApp automático para confirmar o agendamento"
        )
        forbidden_config_path = os.path.join(TEST_TMP_ROOT, "camp-forbidden-config.json")
        with open(forbidden_config_path, "w", encoding="utf-8") as handle:
            json.dump(forbidden_config, handle, ensure_ascii=False, indent=2)

        video_dest = os.path.join(self.forbidden_output, f"{forbidden_config['id']}.mp4")
        with self.assertRaises(preset_runner.PresetRunnerError) as ctx:
            preset_runner.run_preset_pipeline(
                MS_TENANT, forbidden_config_path, self.forbidden_output,
                audio_path=None, root=REPO_ROOT,
            )
        self.assertIn("GUARDRAIL_VIOLACAO", str(ctx.exception))
        # O motor deve falhar ANTES de renderizar: nenhum MP4 produzido.
        self.assertFalse(os.path.exists(video_dest), "MP4 nao deve ser gerado quando ha violação de guardrail")

    def test_05_audio_rejected_for_allow_audio_track_false(self) -> None:
        # --audio passado para um tenant com allowAudioTrack: false (marca-salao).
        with self.assertRaises(preset_runner.PresetRunnerError) as ctx:
            preset_runner.run_preset_pipeline(
                MS_TENANT, MS_CONFIG, self.audio_reject_output,
                audio_path=self.test_audio_path, root=REPO_ROOT,
            )
        self.assertIn("AUDIO_NAO_PERMITIDO", str(ctx.exception))
        video_dest = os.path.join(self.audio_reject_output, f"{MS_SLUG}.mp4")
        self.assertFalse(os.path.exists(video_dest), "MP4 nao deve ser gerado quando audio e recusado")

    # ------------------------------------------------------------------
    # 4. Integridade do manifesto e storyboard
    # ------------------------------------------------------------------
    def test_06_manifest_hashes_and_storyboard_integrity(self) -> None:
        for label, m in (("marca-salao saas-demo", self.MS_MANIFEST),
                         ("multitrack-hub shorts-completo", self.MTH_MANIFEST)):
            with self.subTest(tenant=label):
                self.assertEqual(m["schemaVersion"], 1)
                self.assertIn(m["tenantId"], (MS_TENANT, MTH_TENANT))
                self.assertIn(m["preset"], ("saas-demo", "shorts-completo"))

                # Comando reproduzível registrado.
                self.assertTrue(m["command"].startswith("python tools/preset_runner.py --tenant "))

                arts = m["artifacts"]
                for kind in ("video", "srt", "narration", "storyboard"):
                    entry = arts[kind]
                    abs_p = self._artifact_path(m, kind)
                    self.assertTrue(os.path.isfile(abs_p), f"{label}: {kind} ausente em {abs_p}")
                    self.assertEqual(
                        render_local.sha256_file(abs_p), entry["sha256"],
                        f"{label}: hash SHA-256 divergente em {kind}",
                    )
                    self.assertEqual(os.path.getsize(abs_p), entry["bytes"], f"{label}: bytes divergentes em {kind}")

                # Fixture referenciada tem hash valido.
                fix_abs = os.path.join(REPO_ROOT, m["fixture"]["path"])
                self.assertTrue(os.path.isfile(fix_abs))
                self.assertEqual(render_local.sha256_file(fix_abs), m["fixture"]["sha256"])

                # FFprobe do video bate com o manifesto.
                video_abs = self._artifact_path(m, "video")
                probe = json.loads(
                    subprocess.check_output(
                        [build_video.get_ffprobe(), "-v", "error", "-show_streams", "-show_format", "-of", "json",
                         str(video_abs)],
                        text=True,
                    )
                )
                streams = probe["streams"]
                video_streams = [s for s in streams if s.get("codec_type") == "video"]
                audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
                self.assertEqual(len(video_streams), 1)
                v = video_streams[0]
                self.assertEqual(int(v["width"]), 1080)
                self.assertEqual(int(v["height"]), 1920)
                rate = v.get("avg_frame_rate", "0/1")
                num, _, den = str(rate).partition("/")
                fps = float(num) / float(den or 1)
                self.assertAlmostEqual(fps, 30.0, places=1)

                # Storyboard: existe, tem hash valido e dimensoes 1080x1920.
                sb_entry = arts["storyboard"]
                self.assertEqual(sb_entry["timestampsSeconds"], [2.0, 8.0, 16.0, 24.0])
                self.assertEqual((sb_entry["width"], sb_entry["height"]), (1080, 1920))

    def test_07_all_tenants_still_loadable_after_engine_import(self) -> None:
        """Retrocompatibilidade: o validador de contratos continua funcionando
        para os tres tenants apos a importacao do motor de presets."""
        for tid in ("marca-salao", "meu-salao", "multitrack-hub"):
            ctx = tenant_validator.load_and_validate_tenant(tid, root=REPO_ROOT, strict=True)
            self.assertTrue(ctx["ok"], f"{tid}: {ctx['errors']}")

    # ------------------------------------------------------------------
    # 5. Regressao do CLI: main() encerra com codigo 0 apos o pipeline
    # ------------------------------------------------------------------
    def test_08_cli_exits_zero_after_pipeline(self) -> None:
        """Regressao do KeyError no resumo do CLI (preset_runner main).

        Executa o CLI como subprocesso e exige: returncode 0, ausencia de
        KeyError/Traceback em stderr e manifest.json integro e coerente.
        """
        out_dir = _clean_dir(os.path.join(TEST_TMP_ROOT, "cli-smoke"))
        cmd = [
            sys.executable,
            os.path.join(TOOLS_DIR, "preset_runner.py"),
            "--tenant", MTH_TENANT,
            "--config", MTH_CONFIG,
            "--output-dir", out_dir,
            "--root", REPO_ROOT,
        ]
        res = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=REPO_ROOT, timeout=240,
        )
        self.assertEqual(
            res.returncode, 0,
            f"CLI rc={res.returncode}\nstderr:\n{res.stderr[-600:]}",
        )
        self.assertNotIn("KeyError", res.stderr)
        self.assertNotIn("Traceback", res.stderr)

        manifest_path = os.path.join(out_dir, "manifest.json")
        self.assertTrue(os.path.isfile(manifest_path), "manifest.json nao gerado pelo CLI")
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["tenantId"], MTH_TENANT)
        self.assertEqual(manifest["format"]["width"], 1080)
        self.assertEqual(manifest["format"]["height"], 1920)
        self.assertEqual(manifest["format"]["fps"], 30)
        self.assertEqual(manifest["artifacts"]["video"]["ffprobe"]["audioStreams"], 1)


# ---------------------------------------------------------------------------
# Etapa 6: rotulos de UI parametrizaveis por nicho (brand-kit.uiLabels)
# ---------------------------------------------------------------------------
class UiLabelsTest(unittest.TestCase):
    """Parametrizacao de rotulos de UI: fallback de salao + nichos + guardrails + schema."""

    @staticmethod
    def _brand_kit(tid: str) -> dict:
        return tenant_validator.load_and_validate_tenant(tid, root=REPO_ROOT, strict=True)["brandKit"]

    def test_ui01_resolve_fallback_neutro_sem_uilabels(self) -> None:
        """Sem uiLabels => fallback neutro, sem vocabulario de nicho no codigo."""
        bk = self._brand_kit("marca-salao")
        bk_sem = {k: v for k, v in bk.items() if k != "uiLabels"}
        labels = preset_runner._resolve_ui_labels(bk_sem)
        self.assertEqual(labels, preset_runner.DEFAULT_UI_LABELS)
        self.assertEqual(labels["teamSectionTitle"], "EQUIPE")
        self.assertEqual(labels["publicRouteFallback"], "/")
        self.assertNotIn("SALAO", " ".join(preset_runner.DEFAULT_UI_LABELS.values()))
        # marca-salao com uiLabels resolve os termos da propria marca.
        self.assertEqual(preset_runner._resolve_ui_labels(bk)["teamSectionTitle"],
                         "PROFISSIONAIS DO SALAO")

    def test_ui02_resolve_nichos_clinica_e_estudio(self) -> None:
        cv = preset_runner._resolve_ui_labels(self._brand_kit("clinica-vital"))
        self.assertEqual(cv["publicRouteFallback"], "/avaliacao/[clinicId]")
        self.assertEqual(cv["managerRouteFallback"], "/gestor/consultas")
        self.assertEqual(cv["teamSectionTitle"], "ESPECIALISTAS DA CLINICA")
        self.assertEqual(cv["customerLabel"], "Paciente")
        ef = preset_runner._resolve_ui_labels(self._brand_kit("estudio-flow"))
        self.assertEqual(ef["publicRouteFallback"], "/aulas/[studioId]")
        self.assertEqual(ef["managerRouteFallback"], "/gestor/turmas")
        self.assertEqual(ef["customerLabel"], "Aluna")
        # Fallback parcial: chave omitida cai no padrao de salao.
        parcial = preset_runner._resolve_ui_labels({"uiLabels": {"customerLabel": "Aluna"}})
        self.assertEqual(parcial["customerLabel"], "Aluna")
        self.assertEqual(parcial["teamSectionTitle"], "EQUIPE")

    def test_ui03_guardrail_bloqueia_uilabel_proibido(self) -> None:
        ctx = tenant_validator.load_and_validate_tenant("marca-salao", root=REPO_ROOT, strict=True)
        guardrails = ctx["guardrails"]
        bk = dict(ctx["brandKit"])
        bk["uiLabels"] = dict(bk.get("uiLabels") or {})
        bk["uiLabels"]["customerLabel"] = "Meu Salão"  # forbiddenClaim do marca-salao
        labels = preset_runner._resolve_ui_labels(bk)
        texts = [(f"uiLabels.{k}", v) for k, v in labels.items()]
        violations = preset_runner._audit_texts(texts, guardrails)
        self.assertTrue(violations, "uiLabel proibido deveria gerar violacao de guardrail")
        joined = " ".join(violations).lower()
        self.assertTrue("meu salao" in joined or "claim_forbidden" in joined, joined)

    def test_ui04_schema_rejeita_chave_desconhecida_em_uilabels(self) -> None:
        import copy
        bk = copy.deepcopy(self._brand_kit("estudio-flow"))
        bk["uiLabels"]["chaveInventada"] = "X"
        errors = tenant_validator.validate_brand_kit(bk, root=REPO_ROOT)
        self.assertTrue(errors, "schema deveria rejeitar chave desconhecida em uiLabels")
        self.assertTrue(any("chaveInventada" in e for e in errors), errors)

    def test_ui05_frames_nichos_e_sem_regressao_marca(self) -> None:
        """Gera frames reais saas-demo dos nichos e confirma resolucao sem regressao."""
        import struct
        scene = {"id": "ui-frame", "kind": "booking-selection",
                 "badge": "DEMO", "headline": "TESTE DE ROTULOS", "surface": "public-booking"}
        for tid, esperado in (("clinica-vital", "ESPECIALISTAS DA CLINICA"),
                              ("estudio-flow", "INSTRUTORES DO ESTUDIO")):
            ctx = tenant_validator.load_and_validate_tenant(tid, root=REPO_ROOT, strict=True)
            labels = preset_runner._resolve_ui_labels(ctx["brandKit"])
            self.assertEqual(labels["teamSectionTitle"], esperado)
            canvas = preset_runner._render_saas_frame(
                dict(scene), ctx["brandKit"], ctx["fixture"], REPO_ROOT, None, {}, tid,
            )
            png = preset_runner._encode_png(preset_runner.OUTPUT_WIDTH,
                                            preset_runner.OUTPUT_HEIGHT, canvas)
            self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
            w, h = struct.unpack(">II", png[16:24])
            self.assertEqual((w, h), (preset_runner.OUTPUT_WIDTH, preset_runner.OUTPUT_HEIGHT))
        # Sem regressao: marca-salao continua com rotulos de salao.
        ms = preset_runner._resolve_ui_labels(self._brand_kit("marca-salao"))
        self.assertEqual(ms["teamSectionTitle"], "PROFISSIONAIS DO SALAO")
        self.assertEqual(ms["journeyBridgeCaption"], "DO AGENDAMENTO DA CLIENTE A AGENDA DO SALAO")


class VisualTokensTest(unittest.TestCase):
    """Tokens unificados: VisualStyle v1, framing por perfil e contrato de audio."""

    @staticmethod
    def _kit(tid: str = "marca-salao") -> dict:
        return tenant_validator.load_and_validate_tenant(tid, root=REPO_ROOT, strict=True)["brandKit"]

    def test_vt01_visual_style_derivado_da_paleta(self) -> None:
        kit = self._kit()
        style = preset_runner.resolve_visual_style(kit, "9:16")
        self.assertEqual(style["schemaVersion"], 1)
        self.assertRegex(style["id"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertEqual(style["title"]["textColor"], kit["palette"]["textPrimary"])
        self.assertEqual(style["title"]["outlineColor"], kit["palette"]["background"])
        self.assertEqual(style["title"]["fontSize"], 42)
        self.assertEqual(style["title"]["marginTop"], 160)
        self.assertEqual(style["title"]["marginHorizontal"], 56)

    def test_vt02_framing_por_perfil(self) -> None:
        kit = self._kit()
        expected = {
            "9:16": (1080, 1920, 160, 200),
            "4:5": (1080, 1350, 120, 160),
            "1:1": (1080, 1080, 96, 112),
            "16:9": (1920, 1080, 48, 64),
        }
        for profile, (width, height, top, bottom) in expected.items():
            framing = preset_runner.resolve_framing(kit, profile)
            self.assertEqual(
                (framing["width"], framing["height"], framing["topSafePx"], framing["bottomSafePx"]),
                (width, height, top, bottom),
                profile,
            )
            # Defaults de derivados preservam o quadro inteiro (insets 0).
            self.assertEqual(framing["derivativeTopInsetPx"], 0)
            self.assertEqual(framing["derivativeBottomInsetPx"], 0)

    def test_vt03_override_de_framing_e_clamp_de_fonte(self) -> None:
        kit = dict(self._kit())
        kit["framingByProfile"] = {
            "4:5": {"bottomSafePx": 210, "titleFontSize": 999},
            "16:9": {"derivativeTopInsetPx": 40, "derivativeBottomInsetPx": 24},
        }
        framing = preset_runner.resolve_framing(kit, "4:5")
        self.assertEqual(framing["bottomSafePx"], 210)
        self.assertEqual(framing["titleFontSize"], 160)  # clamp do limite v1
        style = preset_runner.resolve_visual_style(kit, "4:5")
        self.assertEqual(style["title"]["marginTop"], 120)  # safe-zone do perfil
        wide = preset_runner.resolve_framing(kit, "16:9")
        self.assertEqual(wide["derivativeTopInsetPx"], 40)
        self.assertEqual(wide["derivativeBottomInsetPx"], 24)

    def test_vt04_visual_style_declarado_tem_prioridade(self) -> None:
        kit = dict(self._kit())
        kit["visualStyle"] = {
            "schemaVersion": 1,
            "id": "ci-style",
            "title": {
                "textColor": "#FFD700",
                "outlineColor": "#000000",
                "fontSize": 46,
                "marginTop": 200,
                "marginHorizontal": 80,
            },
        }
        style = preset_runner.resolve_visual_style(kit, "9:16")
        self.assertEqual(style["id"], "ci-style")
        self.assertEqual(style["title"]["textColor"], "#FFD700")
        self.assertEqual(style["title"]["fontSize"], 46)
        self.assertEqual(style["title"]["marginHorizontal"], 80)

    def test_vt05_audio_contrato_apenas_multitrack_habilita_aac(self) -> None:
        tenants = ("clinica-vital", "estudio-flow", "marca-salao", "meu-salao", "multitrack-hub")
        for tenant_id in tenants:
            guardrails = tenant_validator.load_and_validate_tenant(
                tenant_id, root=REPO_ROOT, strict=True
            )["guardrails"]
            allow = bool((guardrails.get("audioPolicy") or {}).get("allowAudioTrack", False))
            self.assertEqual(allow, tenant_id == "multitrack-hub", tenant_id)
            if tenant_id != "multitrack-hub":
                self.assertEqual(
                    (guardrails.get("audioPolicy") or {}).get("ffmpegFlag"), "-an", tenant_id
                )


if __name__ == "__main__":
    unittest.main()
