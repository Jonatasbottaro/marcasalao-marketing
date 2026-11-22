"""Testes automatizados (unittest) para o gerador de audio tools/audio_tts.py.

Cobre obrigatoriamente:
  1. Geracao de WAV ambient-bed: 30.0 s, 44100 Hz, stereo, pcm_s16le, exato.
  2. Geracao narration-bed: saida de audio valida (motor TTS local ou fallback
     seguro para ambient-bed) com duracao exata.
  3. Bloqueio contra tenants com allowAudioTrack=false (marca-salao e meu-salao):
     AudioTtsError AUDIO_NAO_PERMITIDO e nenhum arquivo gerado.
  4. Duracao parametrizada respeitada (ex.: 12.5 s).
  5. Rejeicao de caminho de saida fora da raiz e de modo invalido.
  6. Integracao: o WAV gerado alimenta preset_runner.run_preset_pipeline via
     audio_path e produz 1 stream de audio AAC no MP4.

Os testes geram audio real com FFmpeg/FFprobe (binarios em .workspace/tools/ffmpeg,
igual ao CI).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

# Garante ffmpeg/ffprobe no PATH do processo de teste (espelha o CI).
if shutil.which("ffmpeg") is None:
    _ffmpeg_dir = os.path.join(REPO_ROOT, ".workspace", "tools", "ffmpeg")
    if os.path.isdir(_ffmpeg_dir):
        os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

import audio_tts  # noqa: E402
import build_video  # noqa: E402
import preset_runner  # noqa: E402
import render_local  # noqa: E402
import tenant_validator  # noqa: E402
import archives_guard  # noqa: E402

TEST_TMP_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "test_audio_tts")

# Rede de seguranca para execucao direta via unittest: o render de integracao
# nunca pode deixar o master compartilhado com o bed de audio externo do teste.
_GUARD = None


def setUpModule() -> None:
    global _GUARD
    _GUARD = archives_guard.ArchivesGuard(REPO_ROOT, name="test_audio_tts").__enter__()


def tearDownModule() -> None:
    if _GUARD is not None:
        _GUARD.__exit__(None, None, None)

MTH_TENANT = "multitrack-hub"
MS_TENANT = "marca-salao"
MS2_TENANT = "meu-salao"

MS_CONFIG = "tenants/multitrack-hub/campaigns/camp-shorts-completo-multitrack-001.json"


def _clean_dir(path: str) -> str:
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)
    return path


def _probe_audio(path: str) -> dict:
    info = build_video.probe_media(path)
    streams = info.get("streams", [])
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    if not audio:
        raise build_video.DeliveryError("arquivo sem stream de audio")
    a = audio[0]
    return {
        "codec": a.get("codec_name"),
        "sampleRate": int(a.get("sample_rate", 0)),
        "channels": int(a.get("channels", 0)),
        "duration": float(info.get("format", {}).get("duration", 0.0)),
    }


class AudioTtsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _clean_dir(TEST_TMP_ROOT)
        cls.ambient_path = os.path.join(TEST_TMP_ROOT, "bed-30s.wav")
        cls.narration_path = os.path.join(TEST_TMP_ROOT, "narracao-30s.wav")
        cls.short_path = os.path.join(TEST_TMP_ROOT, "bed-12_5s.wav")
        cls.integration_path = os.path.join(TEST_TMP_ROOT, "integration-30s.wav")

        cls.ambient = audio_tts.generate_audio(
            MTH_TENANT, cls.ambient_path, duration=30.0,
            mode=audio_tts.AMBIENT_BED, root=REPO_ROOT,
        )
        cls.narration = audio_tts.generate_audio(
            MTH_TENANT, cls.narration_path, duration=30.0,
            mode=audio_tts.NARRATION_BED, root=REPO_ROOT,
            text="Conheca o catalogo de projetos, stems e rateios do Multitrack Hub.",
        )
        cls.short = audio_tts.generate_audio(
            MTH_TENANT, cls.short_path, duration=12.5,
            mode=audio_tts.AMBIENT_BED, root=REPO_ROOT,
        )
        cls.integration = audio_tts.generate_audio(
            MTH_TENANT, cls.integration_path, duration=30.0,
            mode=audio_tts.AMBIENT_BED, root=REPO_ROOT,
        )

    # ------------------------------------------------------------------
    # 1. ambient-bed: WAV 30.0 s, 44100 Hz, stereo, pcm_s16le
    # ------------------------------------------------------------------
    def test_01_ambient_bed_exact_wav(self) -> None:
        m = self.ambient
        self.assertEqual(m["tenantId"], MTH_TENANT)
        self.assertEqual(m["mode"], audio_tts.AMBIENT_BED)
        self.assertEqual(m["requestedMode"], audio_tts.AMBIENT_BED)
        self.assertTrue(m["allowAudioTrack"])

        abs_path = os.path.join(REPO_ROOT, m["path"])
        self.assertTrue(os.path.isfile(abs_path), f"WAV ausente: {abs_path}")

        probe = _probe_audio(abs_path)
        self.assertEqual(probe["codec"], "pcm_s16le")
        self.assertEqual(probe["sampleRate"], 44100)
        self.assertEqual(probe["channels"], 2)
        self.assertAlmostEqual(probe["duration"], 30.0, places=2)

        # Metadados coerentes com a inspecao real e com o arquivo em disco.
        self.assertEqual(m["sampleRate"], 44100)
        self.assertEqual(m["channels"], 2)
        self.assertEqual(m["codec"], "pcm_s16le")
        self.assertEqual(m["sha256"], render_local.sha256_file(abs_path))
        self.assertEqual(m["bytes"], os.path.getsize(abs_path))

    # ------------------------------------------------------------------
    # 2. narration-bed: saida de audio valida (motor TTS ou fallback seguro)
    # ------------------------------------------------------------------
    def test_02_narration_bed_valid_output(self) -> None:
        m = self.narration
        self.assertEqual(m["requestedMode"], audio_tts.NARRATION_BED)
        self.assertIn(m["mode"], (audio_tts.NARRATION_BED, audio_tts.AMBIENT_BED))
        if m["mode"] == audio_tts.AMBIENT_BED:
            # Fallback seguro obrigatorio quando nenhum motor TTS existe.
            self.assertEqual(m["ttsEngine"], "fallback-ambient-bed")
        else:
            self.assertIsNotNone(m["ttsEngine"])

        abs_path = os.path.join(REPO_ROOT, m["path"])
        probe = _probe_audio(abs_path)
        self.assertEqual(probe["codec"], "pcm_s16le")
        self.assertEqual(probe["sampleRate"], 44100)
        self.assertEqual(probe["channels"], 2)
        self.assertAlmostEqual(probe["duration"], 30.0, places=2)

    # ------------------------------------------------------------------
    # 3. Bloqueio contra tenants com allowAudioTrack=false
    # ------------------------------------------------------------------
    def test_03_blocks_marca_salao(self) -> None:
        out = os.path.join(TEST_TMP_ROOT, "marca-salao-blocked.wav")
        with self.assertRaises(audio_tts.AudioTtsError) as ctx:
            audio_tts.generate_audio(
                MS_TENANT, out, duration=30.0, mode=audio_tts.AMBIENT_BED, root=REPO_ROOT,
            )
        self.assertEqual(ctx.exception.code, "AUDIO_NAO_PERMITIDO")
        self.assertFalse(os.path.exists(out), "WAV nao deve ser gerado para tenant -an")

    def test_04_blocks_meu_salao(self) -> None:
        out = os.path.join(TEST_TMP_ROOT, "meu-salao-blocked.wav")
        with self.assertRaises(audio_tts.AudioTtsError) as ctx:
            audio_tts.generate_audio(
                MS2_TENANT, out, duration=30.0, mode=audio_tts.AMBIENT_BED, root=REPO_ROOT,
            )
        self.assertEqual(ctx.exception.code, "AUDIO_NAO_PERMITIDO")
        self.assertFalse(os.path.exists(out), "WAV nao deve ser gerado para tenant -an")

    # ------------------------------------------------------------------
    # 4. Duracao parametrizada respeitada
    # ------------------------------------------------------------------
    def test_05_duration_param_respected(self) -> None:
        m = self.short
        abs_path = os.path.join(REPO_ROOT, m["path"])
        probe = _probe_audio(abs_path)
        self.assertAlmostEqual(probe["duration"], 12.5, places=2)
        self.assertEqual(probe["sampleRate"], 44100)
        self.assertEqual(probe["channels"], 2)

    # ------------------------------------------------------------------
    # 5. Rejeicao de caminho fora da raiz e de modo invalido
    # ------------------------------------------------------------------
    def test_06_output_outside_root_rejected(self) -> None:
        outside = os.path.join(REPO_ROOT, "..", "escape-audio.wav")
        with self.assertRaises(audio_tts.AudioTtsError) as ctx:
            audio_tts.generate_audio(
                MTH_TENANT, outside, duration=5.0,
                mode=audio_tts.AMBIENT_BED, root=REPO_ROOT,
            )
        self.assertEqual(ctx.exception.code, "OUTPUT_FORA_DA_RAIZ")
        self.assertFalse(os.path.exists(outside), "nao deve criar arquivo fora da raiz")

    def test_07_invalid_mode_rejected(self) -> None:
        out = os.path.join(TEST_TMP_ROOT, "invalid-mode.wav")
        with self.assertRaises(audio_tts.AudioTtsError) as ctx:
            audio_tts.generate_audio(
                MTH_TENANT, out, duration=5.0, mode="guaca", root=REPO_ROOT,
            )
        self.assertEqual(ctx.exception.code, "MODO_INVALIDO")
        self.assertFalse(os.path.exists(out))

    # ------------------------------------------------------------------
    # 6. Integracao: WAV gerado alimenta preset_runner (--audio) e vira AAC
    # ------------------------------------------------------------------
    def test_08_wav_feeds_preset_runner_audio_track(self) -> None:
        out_dir = _clean_dir(os.path.join(TEST_TMP_ROOT, "integration-render"))
        archives_dir = _clean_dir(os.path.join(TEST_TMP_ROOT, "integration-archives"))
        wav_abs = os.path.join(REPO_ROOT, self.integration["path"])
        manifest = preset_runner.run_preset_pipeline(
            MTH_TENANT, MS_CONFIG, out_dir, audio_path=wav_abs, root=REPO_ROOT,
            archives_dir=archives_dir,
        )
        self.assertEqual(manifest["audio"]["source"], "external")
        self.assertTrue(
            manifest["artifacts"]["video"]["archivePath"].startswith(
                ".workspace/tmp/test_audio_tts/integration-archives"
            ),
            "render de teste precisa gravar em archives isolado, nunca nos masters compartilhados",
        )
        fp = manifest["artifacts"]["video"]["ffprobe"]
        self.assertEqual(fp["width"], 1080)
        self.assertEqual(fp["height"], 1920)
        self.assertEqual(fp["fps"], 30.0)
        self.assertEqual(fp["audioStreams"], 1)
        self.assertEqual(fp["audioCodec"], "aac")

        # Confirma tambem por sonda direta no MP4 (44100 Hz, 2 canais).
        video_abs = os.path.join(REPO_ROOT, manifest["artifacts"]["video"]["path"])
        info = build_video.probe_media(video_abs)
        audio = [s for s in info["streams"] if s.get("codec_type") == "audio"][0]
        self.assertEqual(int(audio["sample_rate"]), 44100)
        self.assertEqual(int(audio["channels"]), 2)

    # ------------------------------------------------------------------
    # 7. Todos os tenants continuam carregaveis apos importar audio_tts
    # ------------------------------------------------------------------
    def test_09_all_tenants_still_loadable(self) -> None:
        for tid in ("marca-salao", "meu-salao", "multitrack-hub"):
            ctx = tenant_validator.load_and_validate_tenant(tid, root=REPO_ROOT, strict=True)
            self.assertTrue(ctx["ok"], f"{tid}: {ctx['errors']}")


if __name__ == "__main__":
    unittest.main()