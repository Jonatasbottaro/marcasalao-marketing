"""Testes do motor de quebra mobile de SRT (Etapa 6 - Agente 2).

Cobre (>= 10 casos):
  1. quebra equilibrada de linha unica longa em 2 linhas <= 48;
  2. preservacao de indices, timestamps, pontuacao e acentos UTF-8;
  3. idempotencia (segunda execucao gera bytes identicos);
  4. --check-only detecta linha > 48 (exit 1) sem tocar no disco;
  5. sincronizacao de sha256/bytes no manifest.json (artifacts.srt e files.srt),
     sem alterar video/narracao/storyboard;
  6. LF puro (sem CRLF) e exatamente uma newline final;
  7. as 10 campanhas reais tem maxLineLength <= 48 e hashes de SRT integros;
  8. filtros --tenant / --campaign;
  9. contencao de path (tenant/slug/root invalidos);
 10. CLI --json com payload estruturado;
 11. palavra unica maior que o teto e cortada sem loop nem perda de texto.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import render_local
import srt_formatter
import srt_validate

SCRIPT = os.path.join(ROOT, "tools", "srt_formatter.py")
REAL_DELIVERIES = os.path.join(ROOT, "02-reels-shorts", "deliveries")
REAL_CAMPAIGNS = (
    ("clinica-vital", "camp-saas-demo-clinica-vital-001"),
    ("clinica-vital", "camp-saas-demo-clinica-vital-002"),
    ("estudio-flow", "camp-saas-demo-estudio-flow-001"),
    ("marca-salao", "camp-saas-demo-marca-salao-001"),
    ("marca-salao", "camp-saas-demo-ns001-agenda-001"),
    ("meu-salao", "camp-saas-demo-meu-salao-001"),
    ("meu-salao", "camp-saas-demo-meu-salao-002"),
    ("multitrack-hub", "camp-shorts-completo-multitrack-001"),
    ("multitrack-hub", "camp-shorts-rateios-002"),
    ("multitrack-hub", "camp-shorts-stems-workflow-003"),
)

LONG_LINE = (
    "Como organizar as avaliações da clínica sem depender de troca de mensagens?"
)

SRT_ONE = f"""1
00:00:00,000 --> 00:00:04,000
{LONG_LINE}

2
00:00:04,000 --> 00:00:10,000
A paciente escolhe o procedimento e a especialista disponível.
"""

SRT_TWO = """1
00:00:00,000 --> 00:00:05,000
A equipe acompanha os atendimentos do dia.

2
00:00:05,000 --> 00:00:10,000
Status atualizado manualmente na agenda.
"""

SRT_THREE = """1
00:00:00,000 --> 00:00:06,000
O filtro por especialista mostra apenas as consultas da Dra. Camila Ferraz.

2
00:00:06,000 --> 00:00:12,000
Conheça a rotina da Clínica Vital — clinicavital.com.br
"""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: str, text: str) -> None:
    os.makedirs(render_local.fs_path(os.path.dirname(path)), exist_ok=True)
    with open(render_local.fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _manifest(tid: str, slug: str, srt_text: str) -> dict:
    data = srt_text.encode("utf-8")
    rel = f"02-reels-shorts/deliveries/{tid}/{slug}/{slug}.srt"
    return {
        "schemaVersion": 1,
        "tenantId": tid,
        "slug": slug,
        "format": {"duration": 10.0},
        "artifacts": {
            "video": {"sha256": "1" * 64, "bytes": 111},
            "srt": {"path": rel, "sha256": _sha256(data), "bytes": len(data)},
            "narration": {"sha256": "2" * 64, "bytes": 222},
            "storyboard": {"sha256": "3" * 64, "bytes": 333},
        },
        "files": {"srt": {"path": rel, "sha256": _sha256(data), "bytes": len(data)}},
    }


def _build_sandbox(root: str) -> None:
    cases = (
        ("tenant-a", "camp-one", SRT_ONE),
        ("tenant-a", "camp-two", SRT_TWO),
        ("tenant-b", "camp-three", SRT_THREE),
    )
    for tid, slug, srt in cases:
        base = os.path.join(root, "02-reels-shorts", "deliveries", tid, slug)
        _write(os.path.join(base, f"{slug}.srt"), srt)
        with open(
            render_local.fs_path(os.path.join(base, "manifest.json")),
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            json.dump(_manifest(tid, slug, srt), handle, ensure_ascii=False, indent=2)
            handle.write("\n")


def _body_lines(srt_text: str) -> list[str]:
    lines: list[str] = []
    for block in re.split(r"\n\s*\n", srt_text.strip("\n")):
        parts = block.split("\n")
        lines.extend(line for line in parts[2:] if line.strip())
    return lines


class SrtFormatterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        parent = os.path.join(ROOT, ".workspace", "tmp")
        os.makedirs(render_local.fs_path(parent), exist_ok=True)
        cls._base = tempfile.TemporaryDirectory(prefix="srt-formatter-tests-", dir=parent)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._base.cleanup()
        try:
            os.rmdir(render_local.fs_path(os.path.join(ROOT, ".workspace", "tmp")))
        except OSError:
            pass

    def _sandbox(self) -> str:
        tmp = tempfile.TemporaryDirectory(prefix="case-", dir=self._base.name)
        self.addCleanup(tmp.cleanup)
        _build_sandbox(tmp.name)
        return tmp.name

    def _run_cli(self, root: str, *extra: str, timeout: int = 120):
        return subprocess.run(
            [sys.executable, SCRIPT, "--root", root, *extra],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # 1. Quebra equilibrada
    # ------------------------------------------------------------------
    def test_01_wrap_balanced_long_line(self) -> None:
        self.assertGreater(len(LONG_LINE), 48)
        wrapped = srt_formatter.wrap_srt_cue_text(LONG_LINE)
        lines = wrapped.split("\n")
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertLessEqual(len(line), 48, line)
        self.assertEqual(" ".join(lines), LONG_LINE)
        self.assertEqual(len(set(LONG_LINE.split()) - set(wrapped.split())), 0)
        self.assertLessEqual(abs(len(lines[0]) - len(lines[1])), 10)

    # ------------------------------------------------------------------
    # 2. Indices, timestamps, pontuacao e acentos
    # ------------------------------------------------------------------
    def test_02_preserves_structure_and_utf8(self) -> None:
        new_text, stats = srt_formatter.format_srt_content(SRT_ONE)
        self.assertEqual(stats["cues"], 2)
        self.assertEqual(srt_validate.validate_srt_text(new_text), [])

        def headers(text: str) -> list[tuple[str, str]]:
            out = []
            for block in re.split(r"\n\s*\n", text.strip("\n")):
                parts = block.split("\n")
                out.append((parts[0], parts[1]))
            return out

        self.assertEqual(headers(new_text), headers(SRT_ONE))
        self.assertIn("avaliações", new_text)
        self.assertIn("disponível", new_text)
        self.assertIn("A paciente escolhe o procedimento e a especialista disponível.", new_text.replace("\n", " "))

    # ------------------------------------------------------------------
    # 3. Idempotencia
    # ------------------------------------------------------------------
    def test_03_idempotent(self) -> None:
        first, _ = srt_formatter.format_srt_content(SRT_ONE)
        second, stats = srt_formatter.format_srt_content(first)
        self.assertEqual(first, second)
        self.assertEqual(stats["changedCues"], 0)

        root = self._sandbox()
        result = srt_formatter.format_delivery_srts(root=root, tenant="tenant-a")
        self.assertTrue(result["ok"])
        path = os.path.join(root, "02-reels-shorts", "deliveries", "tenant-a", "camp-one", "camp-one.srt")
        with open(render_local.fs_path(path), "rb") as handle:
            before = handle.read()
        again = srt_formatter.format_delivery_srts(root=root, tenant="tenant-a")
        with open(render_local.fs_path(path), "rb") as handle:
            after = handle.read()
        self.assertEqual(before, after)
        self.assertEqual(again["totals"]["changed"], 0)

    # ------------------------------------------------------------------
    # 4. --check-only: exit 1 sem tocar no disco
    # ------------------------------------------------------------------
    def test_04_check_only_detects_and_does_not_write(self) -> None:
        root = self._sandbox()
        path = os.path.join(root, "02-reels-shorts", "deliveries", "tenant-a", "camp-one", "camp-one.srt")
        with open(render_local.fs_path(path), "rb") as handle:
            before = handle.read()

        res = self._run_cli(root, "--all", "--check-only", "--json")
        self.assertEqual(res.returncode, 1, res.stderr)
        payload = json.loads(res.stdout)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["dryRun"])
        self.assertGreater(payload["totals"]["longLinesBefore"], 0)

        with open(render_local.fs_path(path), "rb") as handle:
            self.assertEqual(handle.read(), before)

        # Depois de formatar, check-only fica verde.
        srt_formatter.format_delivery_srts(root=root)
        clean = self._run_cli(root, "--all", "--check-only", "--json")
        self.assertEqual(clean.returncode, 0, clean.stderr)
        self.assertTrue(json.loads(clean.stdout)["ok"])

    # ------------------------------------------------------------------
    # 5. Sincronizacao do manifesto
    # ------------------------------------------------------------------
    def test_05_manifest_hash_and_bytes_synced(self) -> None:
        root = self._sandbox()
        manifest_path = os.path.join(
            root, "02-reels-shorts", "deliveries", "tenant-a", "camp-one", "manifest.json"
        )
        with open(render_local.fs_path(manifest_path), "r", encoding="utf-8") as handle:
            before = json.load(handle)

        result = srt_formatter.format_delivery_srts(root=root, tenant="tenant-a", slug="camp-one")
        self.assertTrue(result["ok"])
        row = result["campaigns"][0]
        self.assertTrue(row["changed"])
        self.assertTrue(row["manifestUpdated"])

        srt_path = os.path.join(
            root, "02-reels-shorts", "deliveries", "tenant-a", "camp-one", "camp-one.srt"
        )
        with open(render_local.fs_path(srt_path), "rb") as handle:
            raw = handle.read()
        with open(render_local.fs_path(manifest_path), "r", encoding="utf-8") as handle:
            after = json.load(handle)

        self.assertEqual(after["artifacts"]["srt"]["sha256"], _sha256(raw))
        self.assertEqual(after["artifacts"]["srt"]["bytes"], len(raw))
        self.assertEqual(after["files"]["srt"]["sha256"], _sha256(raw))
        self.assertEqual(after["files"]["srt"]["bytes"], len(raw))
        for key in ("video", "narration", "storyboard"):
            self.assertEqual(after["artifacts"][key], before["artifacts"][key])

    # ------------------------------------------------------------------
    # 6. LF puro
    # ------------------------------------------------------------------
    def test_06_lf_only_and_single_trailing_newline(self) -> None:
        root = self._sandbox()
        srt_formatter.format_delivery_srts(root=root)
        for tid in ("tenant-a", "tenant-b"):
            tenant_dir = os.path.join(root, "02-reels-shorts", "deliveries", tid)
            for slug in sorted(os.listdir(render_local.fs_path(tenant_dir))):
                path = os.path.join(tenant_dir, slug, f"{slug}.srt")
                with open(render_local.fs_path(path), "rb") as handle:
                    data = handle.read()
                self.assertNotIn(b"\r", data, path)
                self.assertTrue(data.endswith(b"\n"))
                self.assertFalse(data.endswith(b"\n\n"))

    # ------------------------------------------------------------------
    # 7. Campanhas reais
    # ------------------------------------------------------------------
    def test_07_real_campaigns_mobile_and_hash_integrity(self) -> None:
        for tid, slug in REAL_CAMPAIGNS:
            with self.subTest(campaign=f"{tid}/{slug}"):
                base = os.path.join(REAL_DELIVERIES, tid, slug)
                srt_path = os.path.join(base, f"{slug}.srt")
                manifest_path = os.path.join(base, "manifest.json")
                self.assertTrue(os.path.isfile(render_local.fs_path(srt_path)), srt_path)
                with open(render_local.fs_path(srt_path), "rb") as handle:
                    raw = handle.read()
                text = raw.decode("utf-8")
                self.assertNotIn("\r", text)
                self.assertEqual(srt_validate.validate_srt_text(text), [])
                for line in _body_lines(text):
                    self.assertLessEqual(len(line), 48, f"{tid}/{slug}: {line!r}")
                with open(render_local.fs_path(manifest_path), "r", encoding="utf-8") as handle:
                    manifest = json.load(handle)
                srt_entry = manifest["artifacts"]["srt"]
                self.assertEqual(srt_entry["sha256"], _sha256(raw))
                self.assertEqual(srt_entry["bytes"], len(raw))
        dirs = [
            (tid, slug)
            for tid in sorted(os.listdir(render_local.fs_path(REAL_DELIVERIES)))
            if os.path.isdir(render_local.fs_path(os.path.join(REAL_DELIVERIES, tid)))
            for slug in sorted(os.listdir(render_local.fs_path(os.path.join(REAL_DELIVERIES, tid))))
            if os.path.isdir(render_local.fs_path(os.path.join(REAL_DELIVERIES, tid, slug)))
        ]
        for campaign in REAL_CAMPAIGNS:
            self.assertIn(campaign, dirs)

    # ------------------------------------------------------------------
    # 8. Filtros --tenant / --campaign
    # ------------------------------------------------------------------
    def test_08_tenant_and_campaign_filters(self) -> None:
        root = self._sandbox()
        by_tenant = srt_formatter.format_delivery_srts(root=root, tenant="tenant-a", dry_run=True)
        self.assertEqual(by_tenant["totals"]["campaigns"], 2)
        self.assertEqual({row["tenant"] for row in by_tenant["campaigns"]}, {"tenant-a"})

        by_campaign = srt_formatter.format_delivery_srts(
            root=root, tenant="tenant-a", slug="camp-two", dry_run=True
        )
        self.assertEqual(by_campaign["totals"]["campaigns"], 1)
        self.assertEqual(by_campaign["campaigns"][0]["slug"], "camp-two")

        with self.assertRaises(srt_formatter.SrtFormatterError) as ctx:
            srt_formatter.format_delivery_srts(root=root, tenant="tenant-a", slug="nao-existe")
        self.assertEqual(ctx.exception.code, "CAMPANHA_NAO_ENCONTRADA")

    # ------------------------------------------------------------------
    # 9. Contencao de path
    # ------------------------------------------------------------------
    def test_09_path_containment(self) -> None:
        root = self._sandbox()
        with self.assertRaises(srt_formatter.SrtFormatterError) as ctx:
            srt_formatter.format_delivery_srts(root=root, tenant="../escape")
        self.assertEqual(ctx.exception.code, "TENANT_INVALIDO")

        with self.assertRaises(srt_formatter.SrtFormatterError) as ctx:
            srt_formatter.format_delivery_srts(root=root, tenant="tenant-a", slug="../x")
        self.assertEqual(ctx.exception.code, "CAMPANHA_INVALIDA")

        with self.assertRaises(srt_formatter.SrtFormatterError) as ctx:
            srt_formatter.format_delivery_srts(root=os.path.join(root, "nao-existe"))
        self.assertEqual(ctx.exception.code, "RAIZ_INVALIDA")

        res = self._run_cli(os.path.join(root, "nao-existe"), "--all", "--json")
        self.assertEqual(res.returncode, 1)
        self.assertFalse(json.loads(res.stdout)["ok"])

    # ------------------------------------------------------------------
    # 10. CLI --json estruturado
    # ------------------------------------------------------------------
    def test_10_cli_json_payload(self) -> None:
        root = self._sandbox()
        res = self._run_cli(root, "--all", "--max-chars", "48", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout)
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["dryRun"])
        self.assertEqual(payload["maxChars"], 48)
        self.assertEqual(payload["totals"]["campaigns"], 3)
        self.assertEqual(payload["totals"]["changed"], 2)
        self.assertEqual(payload["totals"]["manifestsUpdated"], 2)
        self.assertEqual(payload["totals"]["longLinesAfter"], 0)
        for row in payload["campaigns"]:
            self.assertIn("beforeMaxLineLength", row)
            self.assertIn("afterSha256", row)
            self.assertIn("srtPath", row)

    # ------------------------------------------------------------------
    # 11. Palavra unica acima do teto
    # ------------------------------------------------------------------
    def test_11_overlong_single_word_safe_cut(self) -> None:
        word = "supercalifragilisticexpialidocious" * 2
        self.assertGreater(len(word), 48)
        wrapped = srt_formatter.wrap_srt_cue_text(word)
        self.assertLessEqual(len(wrapped.split("\n")), 2)
        self.assertEqual("".join(wrapped.split("\n")), word)
        for line in wrapped.split("\n"):
            self.assertLessEqual(len(line), 48)


if __name__ == "__main__":
    unittest.main()