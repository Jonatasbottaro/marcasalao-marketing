"""Testes automatizados (unittest) para o gerador de derivados tools/derivative_formats.py.

Cobre obrigatoriamente:
  1. Composicao 1:1 (1080x1080, 30 fps, h264, yuv420p) com -an forcado para
     tenant allowAudioTrack=false (marca-salao), mesmo quando a fonte TEM audio.
  2. Composicao 16:9 (1920x1080, 30 fps, h264, yuv420p) com o mesmo bloqueio.
  3. Cover PNG 1080x1920 com moldura na cor primaria do brand-kit do tenant.
  4. Preservacao AAC (44100 Hz stereo) em tenant allowAudioTrack=true
     (multitrack-hub) e erro FONTE_SEM_AUDIO quando a fonte nao tem trilha.
  5. Integridade SHA-256/bytes dos derivados contra o derivatives.json em disco.
  6. Erros contratuais FONTE_AUSENTE / ENTREGA_NAO_ENCONTRADA.
  7. Descoberta de campanhas e CLI --json (exit 0, payload ok/generated).

As fontes sao sinteticas (1080x1920, 3 s, 30 fps, com e sem trilha AAC) em
slugs de teste: a suite nao depende dos MP4s reais arquivados, porque o
.workspace/ e local por desenho e nao existe no CI. Os manifestos de entrega
sinteticos ficam em deliveries/<tenant>/<slug-de-teste> e sao removidos no
cleanup da classe.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
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

import build_video  # noqa: E402
import derivative_formats  # noqa: E402
import render_local  # noqa: E402

TEST_TMP_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "test_derivative_formats")

MS_TENANT = "marca-salao"
MTH_TENANT = "multitrack-hub"
MS_SLUG = "test-deriv-ms"
MTH_SLUG = "test-deriv-mth"
MTH_NOAUDIO_SLUG = "test-deriv-mth-noaudio"
MISSING_SLUG = "test-deriv-missing"
FAKE_SLUGS = (MS_SLUG, MTH_SLUG, MTH_NOAUDIO_SLUG, MISSING_SLUG)


def _clean_dir(path: str) -> str:
    if os.path.isdir(path):
        shutil.rmtree(render_local.fs_path(path, force=True), ignore_errors=True)
    os.makedirs(path, exist_ok=True)
    return path


def _archive_source(slug: str) -> str:
    return os.path.join(REPO_ROOT, ".workspace", "archives", slug, f"{slug}.mp4")


def _make_source(path: str, with_audio: bool) -> None:
    """Fonte sintetica 1080x1920, 3 s, 30 fps, com ou sem trilha AAC 44100 stereo."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cmd = [
        build_video.get_ffmpeg(), "-y",
        "-f", "lavfi", "-i", "testsrc2=s=1080x1920:d=3:r=30",
    ]
    if with_audio:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=3"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", "30"]
    cmd += ["-c:a", "aac", "-ar", "44100", "-ac", "2"] if with_audio else ["-an"]
    cmd += [path]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise AssertionError(f"falha ao gerar fonte sintetica: {res.stderr[-300:]}")


def _write_delivery_manifest(tenant: str, slug: str) -> str:
    delivery_dir = os.path.join(REPO_ROOT, "02-reels-shorts", "deliveries", tenant, slug)
    os.makedirs(render_local.fs_path(delivery_dir), exist_ok=True)
    path = os.path.join(delivery_dir, "manifest.json")
    render_local.write_text(path, json.dumps({
        "schemaVersion": 1,
        "tenantId": tenant,
        "preset": "synthetic-test",
        "artifacts": {"video": {"sha256": "fonte-sintetica-de-teste"}},
    }, ensure_ascii=False, indent=2) + "\n")
    return delivery_dir


class DerivativeFormatsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _clean_dir(TEST_TMP_ROOT)

        # marca-salao recebe fonte COM audio para provar que o -an e forcado
        # pela politica do tenant; multitrack-hub recebe com e sem audio.
        _make_source(_archive_source(MS_SLUG), with_audio=True)
        _make_source(_archive_source(MTH_SLUG), with_audio=True)
        _make_source(_archive_source(MTH_NOAUDIO_SLUG), with_audio=False)

        cls._fake_delivery_dirs = [
            _write_delivery_manifest(MS_TENANT, MS_SLUG),
            _write_delivery_manifest(MTH_TENANT, MTH_SLUG),
            _write_delivery_manifest(MTH_TENANT, MTH_NOAUDIO_SLUG),
            _write_delivery_manifest(MS_TENANT, MISSING_SLUG),
        ]
        cls.addClassCleanup(cls._remove_fixtures)

        cls.ms_result = derivative_formats.generate_derivatives(
            MS_TENANT, MS_SLUG, root=REPO_ROOT,
        )
        cls.mth_result = derivative_formats.generate_derivatives(
            MTH_TENANT, MTH_SLUG, root=REPO_ROOT,
        )

    @classmethod
    def _remove_fixtures(cls) -> None:
        for delivery_dir in cls._fake_delivery_dirs:
            shutil.rmtree(render_local.fs_path(delivery_dir, force=True), ignore_errors=True)
        for slug in FAKE_SLUGS:
            shutil.rmtree(
                render_local.fs_path(
                    os.path.join(REPO_ROOT, ".workspace", "archives", slug), force=True,
                ),
                ignore_errors=True,
            )

    # ------------------------------------------------------------------
    # 1. Composicao 1:1 com -an forcado (tenant allowAudioTrack=false)
    # ------------------------------------------------------------------
    def test_01_square_1x1_geometry_forced_an(self) -> None:
        m = self.ms_result
        self.assertEqual(m["tenantId"], MS_TENANT)
        self.assertFalse(m["guardrails"]["allowAudioTrack"])
        self.assertEqual(m["guardrails"]["appliedAudioPolicy"], "-an")

        sq = m["derivatives"]["square"]
        self.assertEqual(sq["kind"], "1x1")
        self.assertEqual(sq["width"], 1080)
        self.assertEqual(sq["height"], 1080)
        self.assertEqual(sq["fps"], 30)
        self.assertEqual(sq["codec"], "h264")
        self.assertEqual(sq["pixFmt"], "yuv420p")
        self.assertEqual(sq["audioStreams"], 0)
        self.assertIsNone(sq["audioCodec"])

        # Sonda independente no arquivo: o -an derruba ate o audio da fonte.
        probe = build_video.probe_media(render_local.fs_path(os.path.join(REPO_ROOT, sq["path"])))
        audio = [s for s in probe["streams"] if s.get("codec_type") == "audio"]
        video = [s for s in probe["streams"] if s.get("codec_type") == "video"]
        self.assertEqual(len(audio), 0)
        self.assertEqual(len(video), 1)
        self.assertEqual(int(video[0]["width"]), 1080)
        self.assertEqual(int(video[0]["height"]), 1080)

    # ------------------------------------------------------------------
    # 2. Composicao 16:9 (1920x1080) com o mesmo bloqueio -an
    # ------------------------------------------------------------------
    def test_02_wide_16x9_geometry_forced_an(self) -> None:
        wd = self.ms_result["derivatives"]["wide"]
        self.assertEqual(wd["kind"], "16x9")
        self.assertEqual(wd["width"], 1920)
        self.assertEqual(wd["height"], 1080)
        self.assertEqual(wd["fps"], 30)
        self.assertEqual(wd["codec"], "h264")
        self.assertEqual(wd["pixFmt"], "yuv420p")
        self.assertEqual(wd["audioStreams"], 0)
        self.assertEqual(wd["foreground"]["width"], 608)
        self.assertEqual(wd["foreground"]["height"], 1080)

        probe = build_video.probe_media(render_local.fs_path(os.path.join(REPO_ROOT, wd["path"])))
        audio = [s for s in probe["streams"] if s.get("codec_type") == "audio"]
        self.assertEqual(len(audio), 0)

    # ------------------------------------------------------------------
    # 3. Cover PNG 1080x1920 com moldura na cor primaria do brand-kit
    # ------------------------------------------------------------------
    def test_03_cover_png_primary_border(self) -> None:
        m = self.ms_result
        cv = m["derivatives"]["cover"]
        self.assertEqual(cv["kind"], "cover-png")
        self.assertEqual(cv["codec"], "png")
        self.assertEqual(cv["width"], 1080)
        self.assertEqual(cv["height"], 1920)
        self.assertEqual(cv["timestampSeconds"], 2.0)
        self.assertEqual(cv["border"]["color"], m["brand"]["palettePrimary"])
        self.assertEqual(cv["border"]["color"], "#F5C107")
        self.assertTrue(os.path.isfile(render_local.fs_path(os.path.join(REPO_ROOT, cv["path"]))))

    # ------------------------------------------------------------------
    # 4. Preservacao AAC em multitrack-hub + erro FONTE_SEM_AUDIO
    # ------------------------------------------------------------------
    def test_04_aac_preservation_multitrack(self) -> None:
        m = self.mth_result
        self.assertTrue(m["guardrails"]["allowAudioTrack"])
        self.assertEqual(m["guardrails"]["appliedAudioPolicy"], "aac-44100-stereo")
        for kind in ("square", "wide"):
            d = m["derivatives"][kind]
            self.assertEqual(d["audioStreams"], 1, kind)
            self.assertEqual(d["audioCodec"], "aac", kind)
            probe = build_video.probe_media(render_local.fs_path(os.path.join(REPO_ROOT, d["path"])))
            audio = [s for s in probe["streams"] if s.get("codec_type") == "audio"]
            self.assertEqual(len(audio), 1, kind)
            self.assertEqual(audio[0]["codec_name"], "aac", kind)
            self.assertEqual(int(audio[0]["sample_rate"]), 44100, kind)
            self.assertEqual(int(audio[0]["channels"]), 2, kind)

    def test_05_fonte_sem_audio_rejected(self) -> None:
        deriv_dir = os.path.join(REPO_ROOT, ".workspace", "archives", MTH_NOAUDIO_SLUG, "derivatives")
        with self.assertRaises(derivative_formats.DerivativeFormatsError) as ctx:
            derivative_formats.generate_derivatives(MTH_TENANT, MTH_NOAUDIO_SLUG, root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "FONTE_SEM_AUDIO")
        self.assertFalse(os.path.exists(deriv_dir), "nenhum derivado deve ser gerado")

    # ------------------------------------------------------------------
    # 5. Integridade SHA-256/bytes contra o derivatives.json em disco
    # ------------------------------------------------------------------
    def test_06_sha256_integrity_and_versioned_manifest(self) -> None:
        for result in (self.ms_result, self.mth_result):
            for kind in ("cover", "square", "wide"):
                entry = result["derivatives"][kind]
                abs_path = render_local.fs_path(os.path.join(REPO_ROOT, entry["path"]))
                self.assertTrue(os.path.isfile(abs_path), kind)
                self.assertEqual(render_local.sha256_file(abs_path), entry["sha256"], kind)
                self.assertEqual(os.path.getsize(abs_path), entry["bytes"], kind)
                self.assertFalse(entry["versioned"], kind)

            disk_path = os.path.join(
                REPO_ROOT, "02-reels-shorts", "deliveries",
                result["tenantId"], result["slug"], "derivatives.json",
            )
            with open(render_local.fs_path(disk_path), "rb") as fh:
                raw = fh.read()
            self.assertNotIn(b"\r", raw, "manifesto deve usar LF")
            disk = json.loads(raw.decode("utf-8"))
            self.assertEqual(
                disk["derivatives"]["square"]["sha256"],
                result["derivatives"]["square"]["sha256"],
            )
            self.assertEqual(
                disk["guardrails"]["appliedAudioPolicy"],
                result["guardrails"]["appliedAudioPolicy"],
            )

    # ------------------------------------------------------------------
    # 6. Erros contratuais FONTE_AUSENTE / ENTREGA_NAO_ENCONTRADA
    # ------------------------------------------------------------------
    def test_07_fonte_ausente_rejected(self) -> None:
        with self.assertRaises(derivative_formats.DerivativeFormatsError) as ctx:
            derivative_formats.generate_derivatives(MS_TENANT, MISSING_SLUG, root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "FONTE_AUSENTE")

    def test_08_entrega_nao_encontrada_rejected(self) -> None:
        with self.assertRaises(derivative_formats.DerivativeFormatsError) as ctx:
            derivative_formats.generate_derivatives(MS_TENANT, "slug-que-nao-existe", root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "ENTREGA_NAO_ENCONTRADA")

    # ------------------------------------------------------------------
    # 7. Descoberta de campanhas e CLI --json
    # ------------------------------------------------------------------
    def test_09_discover_campaigns(self) -> None:
        pairs = derivative_formats.discover_campaigns(REPO_ROOT)
        tenants = {t for t, _ in pairs}
        self.assertIn(MS_TENANT, tenants)
        self.assertIn(MTH_TENANT, tenants)
        self.assertTrue(len(pairs) >= 8, f"esperadas >= 8 entregas reais; observado {len(pairs)}")

        ms_pairs = derivative_formats.discover_campaigns(REPO_ROOT, tenant_id=MS_TENANT)
        self.assertTrue(all(t == MS_TENANT for t, _ in ms_pairs))
        self.assertIn((MS_TENANT, MS_SLUG), ms_pairs)

        only = derivative_formats.discover_campaigns(
            REPO_ROOT, tenant_id=MS_TENANT, campaign=MS_SLUG,
        )
        self.assertEqual(only, [(MS_TENANT, MS_SLUG)])

    def test_10_cli_json_exit_zero(self) -> None:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        res = subprocess.run(
            [sys.executable, os.path.join(TOOLS_DIR, "derivative_formats.py"),
             "--tenant", MS_TENANT, "--campaign", MS_SLUG, "--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=REPO_ROOT, env=env, timeout=300,
        )
        self.assertEqual(res.returncode, 0, res.stderr[-500:])
        payload = json.loads(res.stdout)
        self.assertTrue(payload["ok"], payload["errors"])
        self.assertEqual(payload["generated"], 1)
        self.assertEqual(payload["campaigns"][0]["slug"], MS_SLUG)
        self.assertEqual(payload["campaigns"][0]["guardrails"]["appliedAudioPolicy"], "-an")


if __name__ == "__main__":
    unittest.main()
