"""Testes automatizados (unittest) para o gerador de derivados tools/derivative_formats.py (v2).

Cobre obrigatoriamente os cinco formatos, a resolucao de .workspace/ em worktree,
a politica de audio por tenant e o manifesto versionado v2:

  1. Composicao 1:1 (1080x1080, 30 fps, h264, yuv420p) com -an forcado para
     tenant allowAudioTrack=false (marca-salao), mesmo quando a fonte TEM audio.
  2. Composicao 16:9 (1920x1080, 30 fps, h264, yuv420p) com o mesmo bloqueio.
  3. Cover PNG 1080x1920 com tarjas na paleta do tenant e copia versionada.
  4. Thumb 16:9 e prancha comparativa (preview-grid) 1920x1080 com copias versionadas.
  5. Preservacao AAC (44100 Hz stereo) em tenant allowAudioTrack=true
     (multitrack-hub) e erro FONTE_SEM_AUDIO quando a fonte nao tem trilha.
  6. Integridade SHA-256/bytes dos derivados contra o derivatives.json v2 em disco,
     sem caminhos absolutos de estacao no manifesto.
  7. Erros contratuais FONTE_AUSENTE / ENTREGA_NAO_ENCONTRADA / FORMATO_INVALIDO.
  8. Resolucao de .workspace/ (worktree -> checkout principal) e probe normalizado.
  9. Descoberta de campanhas, pulo por integridade (skip) e regeneracao com --force.
 10. CLI --tenant + --campaign + --formats + --json (exit 0, payload ok/generated).
 11. Validacao consolidada das 8 campanhas reais renderizadas no repositorio
     (manifestos v2 versionados, dimensoes, politica de audio e previews PNG).

As fontes sao sinteticas (1080x1920, 3 s, 30 fps, com e sem trilha AAC) em
slugs de teste: a suite nao depende dos MP4s reais arquivados, porque o
.workspace/ e local por desenho e nao existe no CI. Os manifestos de entrega
sinteticos ficam em deliveries/<tenant>/<slug-de-teste> e sao removidos no
cleanup da classe, junto com os arquivos sinteticos em .workspace/.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import PureWindowsPath

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

MS_PRIMARY = "#F5C107"
MS_BACKGROUND = "#121620"


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


def _delivery_dir(tenant: str, slug: str) -> str:
    return os.path.join(REPO_ROOT, "02-reels-shorts", "deliveries", tenant, slug)


def _manifest_path(tenant: str, slug: str) -> str:
    return os.path.join(_delivery_dir(tenant, slug), "derivatives.json")


def _read_manifest_raw(tenant: str, slug: str) -> bytes:
    with open(render_local.fs_path(_manifest_path(tenant, slug)), "rb") as fh:
        return fh.read()


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

        cls.ms_result = derivative_formats.generate_campaign_derivatives(
            MS_TENANT, MS_SLUG, root=REPO_ROOT,
        )
        cls.mth_result = derivative_formats.generate_campaign_derivatives(
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
        self.assertEqual(m["status"], "generated")
        self.assertFalse(m["allowAudioTrack"])
        self.assertEqual(m["appliedAudioPolicy"], "-an")

        sq = m["derivatives"]["1x1"]
        self.assertEqual(sq["kind"], "1x1")
        self.assertEqual(sq["width"], 1080)
        self.assertEqual(sq["height"], 1080)
        self.assertEqual(sq["fps"], 30)
        self.assertEqual(sq["codec"], "h264")
        self.assertEqual(sq["pixFmt"], "yuv420p")
        self.assertEqual(sq["audioStreams"], 0)
        self.assertIsNone(sq["audioCodec"])
        self.assertEqual(sq["foreground"]["width"], 608)
        self.assertEqual(sq["foreground"]["height"], 1080)
        self.assertEqual(sq["foreground"]["padWidth"], 616)
        self.assertEqual(sq["foreground"]["padEdge"], 4)
        self.assertEqual(sq["foreground"]["padColor"], MS_PRIMARY)
        self.assertEqual(sq["visualStyle"]["schemaVersion"], 1)
        self.assertEqual(sq["framing"]["profile"], "1:1")
        self.assertEqual(
            (sq["framing"]["width"], sq["framing"]["height"]), (1080, 1080)
        )
        self.assertTrue(sq["framingPreservedFullFrame"])

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
        wd = self.ms_result["derivatives"]["16x9"]
        self.assertEqual(wd["kind"], "16x9")
        self.assertEqual(wd["width"], 1920)
        self.assertEqual(wd["height"], 1080)
        self.assertEqual(wd["fps"], 30)
        self.assertEqual(wd["codec"], "h264")
        self.assertEqual(wd["pixFmt"], "yuv420p")
        self.assertEqual(wd["audioStreams"], 0)
        self.assertEqual(wd["foreground"]["width"], 608)
        self.assertEqual(wd["foreground"]["height"], 1080)
        self.assertEqual(wd["framing"]["profile"], "16:9")
        self.assertEqual((wd["framing"]["width"], wd["framing"]["height"]), (1920, 1080))
        self.assertTrue(wd["framingPreservedFullFrame"])

        probe = build_video.probe_media(render_local.fs_path(os.path.join(REPO_ROOT, wd["path"])))
        audio = [s for s in probe["streams"] if s.get("codec_type") == "audio"]
        self.assertEqual(len(audio), 0)

    # ------------------------------------------------------------------
    # 3. Cover PNG 1080x1920 com tarjas na paleta e copia versionada
    # ------------------------------------------------------------------
    def test_03_cover_png_bars_and_versioned_copy(self) -> None:
        m = self.ms_result
        cv = m["derivatives"]["cover"]
        self.assertEqual(cv["kind"], "cover-png")
        self.assertEqual(cv["codec"], "png")
        self.assertEqual(cv["width"], 1080)
        self.assertEqual(cv["height"], 1920)
        self.assertEqual(cv["timestampSeconds"], 2.5)
        self.assertEqual(cv["bars"]["top"]["color"], MS_BACKGROUND)
        self.assertEqual(cv["bars"]["bottom"]["color"], MS_BACKGROUND)
        self.assertEqual(cv["bars"]["accent"]["color"], MS_PRIMARY)
        self.assertEqual(cv["bars"]["accent"]["thickness"], 8)

        versioned_abs = os.path.join(REPO_ROOT, cv["versionedCopy"])
        self.assertTrue(os.path.isfile(render_local.fs_path(versioned_abs)))
        self.assertEqual(render_local.sha256_file(versioned_abs), cv["sha256"])

    # ------------------------------------------------------------------
    # 4. Thumb 16:9 e prancha comparativa com copias versionadas
    # ------------------------------------------------------------------
    def test_04_thumb_and_grid_geometry(self) -> None:
        m = self.ms_result
        th = m["derivatives"]["thumb-16x9"]
        self.assertEqual(th["kind"], "thumb-16x9-png")
        self.assertEqual(th["codec"], "png")
        self.assertEqual(th["width"], 1920)
        self.assertEqual(th["height"], 1080)
        self.assertEqual(th["timestampSeconds"], 2.5)

        gr = m["derivatives"]["preview-formats"]
        self.assertEqual(gr["kind"], "preview-grid-png")
        self.assertEqual(gr["codec"], "png")
        self.assertEqual(gr["width"], 1920)
        self.assertEqual(gr["height"], 1080)
        self.assertEqual(gr["panels"]["order"], ["9:16", "1:1", "16:9"])
        self.assertEqual(gr["panels"]["height"], 540)
        self.assertEqual(gr["panels"]["background"], MS_BACKGROUND)

        for key, name in (("thumb-16x9", "thumb-16x9.png"),
                          ("preview-formats", "preview-formats.png")):
            entry = m["derivatives"][key]
            versioned_abs = os.path.join(REPO_ROOT, entry["versionedCopy"])
            self.assertTrue(os.path.isfile(render_local.fs_path(versioned_abs)), name)
            self.assertEqual(render_local.sha256_file(versioned_abs), entry["sha256"], name)

    # ------------------------------------------------------------------
    # 5. Preservacao AAC em multitrack-hub + erro FONTE_SEM_AUDIO
    # ------------------------------------------------------------------
    def test_05_aac_preservation_multitrack(self) -> None:
        m = self.mth_result
        self.assertTrue(m["allowAudioTrack"])
        self.assertEqual(m["appliedAudioPolicy"], "aac-44100-stereo")
        for kind in ("1x1", "16x9"):
            d = m["derivatives"][kind]
            self.assertEqual(d["audioStreams"], 1, kind)
            self.assertEqual(d["audioCodec"], "aac", kind)
            probe = build_video.probe_media(render_local.fs_path(os.path.join(REPO_ROOT, d["path"])))
            audio = [s for s in probe["streams"] if s.get("codec_type") == "audio"]
            self.assertEqual(len(audio), 1, kind)
            self.assertEqual(audio[0]["codec_name"], "aac", kind)
            self.assertEqual(int(audio[0]["sample_rate"]), 44100, kind)
            self.assertEqual(int(audio[0]["channels"]), 2, kind)

    def test_06_fonte_sem_audio_rejected(self) -> None:
        deriv_dir = os.path.join(REPO_ROOT, ".workspace", "archives", MTH_NOAUDIO_SLUG, "derivatives")
        with self.assertRaises(derivative_formats.DerivativeFormatsError) as ctx:
            derivative_formats.generate_campaign_derivatives(
                MTH_TENANT, MTH_NOAUDIO_SLUG, root=REPO_ROOT,
            )
        self.assertEqual(ctx.exception.code, "FONTE_SEM_AUDIO")
        self.assertFalse(os.path.exists(deriv_dir), "nenhum derivado deve ser gerado")

    # ------------------------------------------------------------------
    # 6. Integridade SHA-256/bytes contra o derivatives.json v2 em disco
    # ------------------------------------------------------------------
    def test_07_sha256_integrity_and_manifest_v2(self) -> None:
        for result in (self.ms_result, self.mth_result):
            for kind in derivative_formats.ALL_FORMATS:
                entry = result["derivatives"][kind]
                abs_path = render_local.fs_path(os.path.join(REPO_ROOT, entry["path"]))
                self.assertTrue(os.path.isfile(abs_path), kind)
                self.assertEqual(render_local.sha256_file(abs_path), entry["sha256"], kind)
                self.assertEqual(os.path.getsize(abs_path), entry["bytes"], kind)

            raw = _read_manifest_raw(result["tenantId"], result["slug"])
            self.assertNotIn(b"\r", raw, "manifesto deve usar LF")
            self.assertNotIn(os.path.realpath(REPO_ROOT).encode(), raw)
            disk = json.loads(raw.decode("utf-8"))
            paths = [disk["source"]["path"], disk["source"]["deliveryManifest"]]
            for entry in disk["derivatives"].values():
                paths.append(entry["path"])
                if "versionedCopy" in entry:
                    paths.append(entry["versionedCopy"])
            for path in paths:
                parsed = PureWindowsPath(path)
                self.assertFalse(parsed.anchor, path)
                self.assertNotIn("..", parsed.parts, path)
            self.assertEqual(disk["schemaVersion"], 2)
            self.assertEqual(disk["allowAudioTrack"], result["allowAudioTrack"])
            self.assertEqual(disk["appliedAudioPolicy"], result["appliedAudioPolicy"])
            self.assertEqual(disk["slug"], result["slug"])
            self.assertEqual(disk["tenantId"], result["tenantId"])
            self.assertEqual(
                disk["derivatives"]["1x1"]["sha256"],
                result["derivatives"]["1x1"]["sha256"],
            )
            source_abs = render_local.fs_path(_archive_source(result["slug"]))
            self.assertEqual(disk["sourceVideoSha256"], render_local.sha256_file(source_abs))
            for kind in ("1x1", "16x9"):
                self.assertNotIn("versionedCopy", disk["derivatives"][kind],
                                 "MP4 derivado nunca e versionado")

    # ------------------------------------------------------------------
    # 7. Erros contratuais FONTE_AUSENTE / ENTREGA_NAO_ENCONTRADA / FORMATO_INVALIDO
    # ------------------------------------------------------------------
    def test_08_contract_errors(self) -> None:
        with self.assertRaises(derivative_formats.DerivativeFormatsError) as ctx:
            derivative_formats.generate_campaign_derivatives(MS_TENANT, MISSING_SLUG, root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "FONTE_AUSENTE")

        with self.assertRaises(derivative_formats.DerivativeFormatsError) as ctx:
            derivative_formats.generate_campaign_derivatives(
                MS_TENANT, "slug-que-nao-existe", root=REPO_ROOT,
            )
        self.assertEqual(ctx.exception.code, "ENTREGA_NAO_ENCONTRADA")

        with self.assertRaises(derivative_formats.DerivativeFormatsError) as ctx:
            derivative_formats.generate_campaign_derivatives(
                MS_TENANT, MS_SLUG, root=REPO_ROOT, formats="1x1,foo",
            )
        self.assertEqual(ctx.exception.code, "FORMATO_INVALIDO")

    # ------------------------------------------------------------------
    # 8. Resolucao de .workspace/ (worktree -> checkout principal) e probe
    # ------------------------------------------------------------------
    def test_09_workspace_resolution_and_probe(self) -> None:
        ws = derivative_formats.resolve_workspace_root(REPO_ROOT)
        self.assertTrue(os.path.isdir(render_local.fs_path(ws)))
        self.assertTrue(os.path.basename(ws) == ".workspace")
        self.assertTrue(os.path.isdir(render_local.fs_path(os.path.join(ws, "archives"))))

        main_root = derivative_formats._main_checkout_root(REPO_ROOT)
        self.assertIsNotNone(main_root)
        self.assertTrue(os.path.isdir(render_local.fs_path(main_root)))

        summary = derivative_formats.probe_media(_archive_source(MS_SLUG))
        self.assertEqual(summary["width"], 1080)
        self.assertEqual(summary["height"], 1920)
        self.assertEqual(summary["codec"], "h264")
        self.assertEqual(summary["audioStreams"], 1)
        self.assertEqual(summary["audioCodec"], "aac")

    # ------------------------------------------------------------------
    # 9. Descoberta de campanhas, pulo por integridade e regeneracao --force
    # ------------------------------------------------------------------
    def test_10_discover_and_idempotent_skip(self) -> None:
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

        # Sem --force e com derivados integros em disco: pula (skip).
        again = derivative_formats.generate_campaign_derivatives(MS_TENANT, MS_SLUG, root=REPO_ROOT)
        self.assertEqual(again["status"], "skipped")
        # Com --force: regenera de fato.
        forced = derivative_formats.generate_campaign_derivatives(
            MS_TENANT, MS_SLUG, root=REPO_ROOT, force=True,
        )
        self.assertEqual(forced["status"], "generated")

    # ------------------------------------------------------------------
    # 10. CLI --tenant + --campaign + --formats + --json (exit 0)
    # ------------------------------------------------------------------
    def test_11_cli_json_exit_zero(self) -> None:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        res = subprocess.run(
            [sys.executable, os.path.join(TOOLS_DIR, "derivative_formats.py"),
             "--tenant", MS_TENANT, "--campaign", MS_SLUG,
             "--formats", "cover", "--force", "--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=REPO_ROOT, env=env, timeout=300,
        )
        self.assertEqual(res.returncode, 0, res.stderr[-500:])
        payload = json.loads(res.stdout)
        self.assertTrue(payload["ok"], payload["errors"])
        self.assertEqual(payload["generated"], 1)
        self.assertEqual(payload["campaigns"][0]["slug"], MS_SLUG)
        self.assertEqual(payload["campaigns"][0]["formats"], ["cover"])
        self.assertEqual(payload["campaigns"][0]["appliedAudioPolicy"], "-an")

        # O manifesto preserva as entradas dos formatos nao re-gerados.
        disk = json.loads(_read_manifest_raw(MS_TENANT, MS_SLUG).decode("utf-8"))
        for kind in derivative_formats.ALL_FORMATS:
            self.assertIn(kind, disk["derivatives"])

    # ------------------------------------------------------------------
    # 11. Validacao consolidada das 8 campanhas reais do repositorio
    # ------------------------------------------------------------------
    def test_12_consolidated_eight_campaigns(self) -> None:
        real_pairs = [
            (t, s) for t, s in derivative_formats.discover_campaigns(REPO_ROOT)
            if s not in FAKE_SLUGS
        ]
        self.assertTrue(len(real_pairs) >= 8,
                        f"esperadas >= 8 campanhas reais; observado {len(real_pairs)}")

        main_root = derivative_formats._main_checkout_root(REPO_ROOT)
        for tenant, slug in real_pairs:
            with self.subTest(tenant=tenant, slug=slug):
                raw = _read_manifest_raw(tenant, slug)
                disk = json.loads(raw.decode("utf-8"))
                self.assertEqual(disk["schemaVersion"], 2)
                self.assertEqual(disk["tenantId"], tenant)
                self.assertEqual(disk["slug"], slug)
                self.assertTrue(disk["sourceVideoSha256"])

                allow_audio = disk["allowAudioTrack"]
                self.assertEqual(
                    disk["appliedAudioPolicy"],
                    "aac-44100-stereo" if allow_audio else "-an",
                )
                expected_audio = 1 if allow_audio else 0
                dims = {"1x1": (1080, 1080), "16x9": (1920, 1080),
                        "cover": (1080, 1920), "thumb-16x9": (1920, 1080),
                        "preview-formats": (1920, 1080)}
                for kind, (w, h) in dims.items():
                    entry = disk["derivatives"][kind]
                    self.assertEqual((entry["width"], entry["height"]), (w, h), kind)
                    self.assertTrue(entry["sha256"], kind)
                    self.assertGreater(entry["bytes"], 0, kind)
                    if kind in ("1x1", "16x9"):
                        self.assertEqual(entry["codec"], "h264", kind)
                        self.assertEqual(entry["audioStreams"], expected_audio, kind)
                        self.assertEqual(entry["fps"], 30, kind)
                    else:
                        self.assertEqual(entry["codec"], "png", kind)
                        versioned_abs = os.path.join(REPO_ROOT, entry["versionedCopy"])
                        self.assertTrue(
                            os.path.isfile(render_local.fs_path(versioned_abs)), kind,
                        )
                        self.assertEqual(
                            render_local.sha256_file(versioned_abs), entry["sha256"], kind,
                        )
                    # MP4s derivados vivem no .workspace/ local: conferidos
                    # quando presentes (estacao com archives), pulados no CI.
                    if main_root:
                        deriv_abs = os.path.join(
                            main_root, entry["path"].replace("/", os.sep),
                        )
                        if os.path.isfile(render_local.fs_path(deriv_abs)):
                            self.assertEqual(
                                render_local.sha256_file(deriv_abs), entry["sha256"], kind,
                            )


if __name__ == "__main__":
    unittest.main()
