"""Testes da auditoria editorial transversal (tools/editorial_qa.py).

Cobertura (Etapa 5B, Agente 8):
  - auditoria completa do acervo real (10 campanhas, 5 lentes, 4 lentes estaveis
    aprovadas e nenhum erro);
  - deteccao de linha de SRT longa demais (aviso de legibilidade, --strict
    reprova);
  - deteccao de mojibake/U+FFFD e de violacao de guardrail (erros);
  - filtro --tenant, modo --strict, CLI --json e saida humana;
  - divergencia de duracao SRT x manifesto, pacote social ausente e bloco de
    SRT vazio;
  - determinismo e ausencia de efeito colateral da API.

Todos os testes de defeito usam um sandbox somente-leitura copiado para
<RAIZ>/.workspace/tmp/editorial-qa/ (dentro do checkout, fora do Git).
"""

import contextlib
import io
import json
import os
import shutil
import stat
import sys
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
TEST_TMP_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "editorial-qa")

sys.path.insert(0, TOOLS_DIR)

import editorial_qa  # noqa: E402

CHECK_IDS = list(editorial_qa.CHECK_IDS)
STABLE_CHECKS = (
    "duracao_srt_manifest",
    "paridade_entregas",
    "guardrails_cruzados",
    "integridade_utf8",
)


def _force_rmtree(path: str) -> None:
    if not os.path.isdir(path):
        return
    for dirpath, _dirnames, filenames in os.walk(path):
        for fname in filenames:
            target = os.path.join(dirpath, fname)
            try:
                os.chmod(target, stat.S_IWRITE)
            except OSError:
                pass
    shutil.rmtree(path, ignore_errors=True)


class EditorialQATests(unittest.TestCase):
    maxDiff = None

    def tearDown(self) -> None:
        sandbox = getattr(self, "_sandbox", None)
        if sandbox:
            _force_rmtree(sandbox)

    @classmethod
    def tearDownClass(cls):
        _force_rmtree(TEST_TMP_ROOT)

    # ------------------------------------------------------------------
    # Infraestrutura de sandbox
    # ------------------------------------------------------------------
    def _build_sandbox(self, tag: str) -> str:
        sandbox = os.path.join(TEST_TMP_ROOT, tag)
        _force_rmtree(sandbox)
        os.makedirs(sandbox)
        for folder in ("schemas", "tenants"):
            shutil.copytree(
                os.path.join(REPO_ROOT, folder),
                os.path.join(sandbox, folder),
            )
        for campaign in editorial_qa.discover_campaigns(REPO_ROOT):
            tenant, slug = campaign["tenant"], campaign["slug"]
            src_delivery = os.path.join(
                REPO_ROOT, *editorial_qa.DELIVERY_ROOT, tenant, slug
            )
            dst_delivery = os.path.join(sandbox, *editorial_qa.DELIVERY_ROOT, tenant, slug)
            os.makedirs(dst_delivery, exist_ok=True)
            for name in ("manifest.json", f"{slug}.srt", f"{slug}_narracao.txt"):
                shutil.copy2(os.path.join(src_delivery, name), os.path.join(dst_delivery, name))

            src_static = os.path.join(REPO_ROOT, *editorial_qa.STATIC_ROOT, tenant, slug)
            dst_static = os.path.join(sandbox, *editorial_qa.STATIC_ROOT, tenant, slug)
            os.makedirs(dst_static, exist_ok=True)
            shutil.copy2(
                os.path.join(src_static, editorial_qa.STATIC_FILE),
                os.path.join(dst_static, editorial_qa.STATIC_FILE),
            )

            src_pkg = os.path.join(REPO_ROOT, *editorial_qa.PACKAGE_ROOT, tenant, slug)
            dst_pkg = os.path.join(sandbox, *editorial_qa.PACKAGE_ROOT, tenant, slug)
            os.makedirs(dst_pkg, exist_ok=True)
            for name in editorial_qa.PACKAGE_FILES + (editorial_qa.CHECKLIST_FILE,):
                shutil.copy2(os.path.join(src_pkg, name), os.path.join(dst_pkg, name))
        self._sandbox = sandbox
        return sandbox

    @staticmethod
    def _srt_path(root: str, tenant: str, slug: str) -> str:
        return os.path.join(root, *editorial_qa.DELIVERY_ROOT, tenant, slug, f"{slug}.srt")

    @staticmethod
    def _replace_in_file(path: str, old: str, new: str) -> None:
        with open(path, "r", encoding="utf-8", newline="") as handle:
            text = handle.read()
        if old not in text:
            raise AssertionError(f"trecho nao encontrado em {path}: {old!r}")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text.replace(old, new))

    @staticmethod
    def _set_cue_body(path: str, cue_index: int, body: str) -> None:
        """Substitui o corpo de um cue preservando indice e timestamp."""
        with open(path, "r", encoding="utf-8", newline="") as handle:
            text = handle.read()
        blocks = text.strip("\n").split("\n\n")
        lines = blocks[cue_index].split("\n")
        rebuilt = [lines[0], lines[1]]
        if body:
            rebuilt.append(body)
        blocks[cue_index] = "\n".join(rebuilt)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n\n".join(blocks) + "\n")

    @staticmethod
    def _wrap_all_srt_lines(root: str) -> None:
        """Reduz todas as linhas de corpo dos SRTs a <= 48 caracteres no sandbox.

        O acervo real tem linhas longas (avisos conhecidos); para isolar o teste
        do modo --strict é preciso um ponto de partida sem nenhum aviso.
        """
        limit = editorial_qa.MAX_LINE_CHARS
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                if not name.endswith(".srt"):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, "r", encoding="utf-8", newline="") as handle:
                    text = handle.read()
                blocks = []
                for block in text.strip("\n").split("\n\n"):
                    lines = block.split("\n")
                    if len(lines) < 3:
                        blocks.append(block)
                        continue
                    body: list[str] = []
                    for line in lines[2:]:
                        while len(line) > limit:
                            body.append(line[:limit])
                            line = line[limit:]
                        if line:
                            body.append(line)
                    blocks.append("\n".join(lines[:2] + body))
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write("\n\n".join(blocks) + "\n")

    @staticmethod
    def _check(result: dict, check_id: str) -> dict:
        for row in result["checks"]:
            if row["id"] == check_id:
                return row
        raise AssertionError(f"lente ausente: {check_id}")

    @staticmethod
    def _codes(row: dict) -> list[str]:
        return [problem["code"] for problem in row["problems"]]

    # ------------------------------------------------------------------
    # 1. Auditoria completa do acervo
    # ------------------------------------------------------------------
    def test_01_auditoria_completa_do_acervo(self) -> None:
        result = editorial_qa.run_editorial_qa(root=REPO_ROOT)
        self.assertEqual(result["schemaVersion"], 1)
        self.assertFalse(result["strict"])
        self.assertEqual(
            result["summary"]["campaigns"]["total"],
            len(editorial_qa.discover_campaigns(REPO_ROOT)),
        )
        self.assertEqual(result["summary"]["campaigns"]["total"], 10)
        self.assertEqual([row["id"] for row in result["checks"]], CHECK_IDS)
        self.assertEqual(result["summary"]["problems"]["errors"], 0)
        for check_id in STABLE_CHECKS:
            self.assertEqual(self._check(result, check_id)["status"], "ok")
        # Apos o saneamento da Etapa 6 (tools/srt_formatter.py) o acervo nao
        # tem nenhuma linha acima de 48 caracteres: a lente fica ok tambem no
        # modo --strict.
        self.assertEqual(self._check(result, "legibilidade_mobile")["status"], "ok")
        self.assertEqual(result["summary"]["problems"]["warnings"], 0)
        self.assertTrue(result["ok"])

    # ------------------------------------------------------------------
    # 2. Linha de SRT longa demais
    # ------------------------------------------------------------------
    def test_02_deteccao_linha_srt_longa(self) -> None:
        sandbox = self._build_sandbox("longa")
        path = self._srt_path(
            sandbox, "marca-salao", "camp-saas-demo-marca-salao-001"
        )
        self._set_cue_body(path, 0, "L" * 60)
        result = editorial_qa.run_editorial_qa(root=sandbox)
        row = self._check(result, "legibilidade_mobile")
        self.assertIn("SRT_LINHA_LONGA", self._codes(row))
        self.assertTrue(
            any("60 caracteres" in p["message"] for p in row["problems"])
        )
        self.assertTrue(
            all(p["severity"] == "warning" for p in row["problems"])
        )
        self.assertEqual(row["status"], "warn")
        self.assertTrue(result["ok"])

    # ------------------------------------------------------------------
    # 3. Mojibake
    # ------------------------------------------------------------------
    def test_03_deteccao_mojibake(self) -> None:
        sandbox = self._build_sandbox("mojibake")
        path = self._srt_path(sandbox, "meu-salao", "camp-saas-demo-meu-salao-001")
        self._replace_in_file(path, "\n\n2\n", " \u00c3\u00a7\n\n2\n")
        result = editorial_qa.run_editorial_qa(root=sandbox)
        row = self._check(result, "integridade_utf8")
        self.assertIn("MOJIBAKE_DETECTADO", self._codes(row))
        self.assertEqual(row["status"], "fail")
        self.assertFalse(result["ok"])

    def test_03b_deteccao_ufffd(self) -> None:
        sandbox = self._build_sandbox("ufffd")
        path = self._srt_path(sandbox, "meu-salao", "camp-saas-demo-meu-salao-002")
        self._replace_in_file(path, "\n\n2\n", " \ufffd\n\n2\n")
        result = editorial_qa.run_editorial_qa(root=sandbox)
        self.assertIn("MOJIBAKE_DETECTADO", self._codes(self._check(result, "integridade_utf8")))
        self.assertFalse(result["ok"])

    # ------------------------------------------------------------------
    # 4. Guardrail cruzado
    # ------------------------------------------------------------------
    def test_04_deteccao_violacao_guardrail(self) -> None:
        sandbox = self._build_sandbox("guardrail")
        caption = os.path.join(
            sandbox, *editorial_qa.PACKAGE_ROOT, "marca-salao",
            "camp-saas-demo-marca-salao-001", "instagram-reels.md",
        )
        self._replace_in_file(caption, "#MarcaSalao", "whatsapp #MarcaSalao")
        result = editorial_qa.run_editorial_qa(root=sandbox)
        row = self._check(result, "guardrails_cruzados")
        self.assertIn("GUARDRAIL_VIOLACAO", self._codes(row))
        self.assertTrue(any("instagram-reels.md" in p["message"] for p in row["problems"]))
        self.assertFalse(result["ok"])

    # ------------------------------------------------------------------
    # 5. Filtro --tenant
    # ------------------------------------------------------------------
    def test_05_filtro_tenant(self) -> None:
        sandbox = self._build_sandbox("tenant")
        result = editorial_qa.run_editorial_qa(root=sandbox, tenant="meu-salao")
        self.assertEqual(result["tenantFilter"], "meu-salao")
        self.assertEqual(result["summary"]["campaigns"]["total"], 2)
        self.assertTrue(all(row["tenant"] == "meu-salao" for row in result["campaigns"]))
        for problem in (p for c in result["checks"] for p in c["problems"]):
            self.assertTrue(problem["message"].startswith("meu-salao/"))
        empty = editorial_qa.run_editorial_qa(root=sandbox, tenant="tenant-inexistente")
        self.assertEqual(empty["summary"]["campaigns"]["total"], 0)
        self.assertTrue(empty["ok"])

    # ------------------------------------------------------------------
    # 6. Modo --strict
    # ------------------------------------------------------------------
    def test_06_modo_strict(self) -> None:
        sandbox = self._build_sandbox("strict")
        self._wrap_all_srt_lines(sandbox)
        clean = editorial_qa.run_editorial_qa(root=sandbox, strict=True)
        self.assertTrue(clean["ok"])
        path = self._srt_path(
            sandbox, "estudio-flow", "camp-saas-demo-estudio-flow-001"
        )
        self._replace_in_file(path, "\n\n2\n", " " + "Y" * 55 + "\n\n2\n")
        normal = editorial_qa.run_editorial_qa(root=sandbox, strict=False)
        strict = editorial_qa.run_editorial_qa(root=sandbox, strict=True)
        self.assertTrue(normal["ok"])
        self.assertFalse(strict["ok"])
        self.assertEqual(self._check(strict, "legibilidade_mobile")["status"], "warn")
        self.assertFalse(self._check(strict, "legibilidade_mobile")["ok"])

    # ------------------------------------------------------------------
    # 7. CLI --json
    # ------------------------------------------------------------------
    def test_07_cli_json(self) -> None:
        sandbox = self._build_sandbox("cli-json")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = editorial_qa.main(["--all", "--json", "--root", sandbox])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertEqual(payload["summary"]["campaigns"]["total"], 10)
        self.assertEqual([c["id"] for c in payload["checks"]], CHECK_IDS)

        path = self._srt_path(sandbox, "meu-salao", "camp-saas-demo-meu-salao-001")
        self._replace_in_file(path, "\n\n2\n", " \ufffd\n\n2\n")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = editorial_qa.main(["--strict", "--json", "--root", sandbox])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(stdout.getvalue())["ok"])

    def test_07b_cli_humano_e_filtro(self) -> None:
        sandbox = self._build_sandbox("cli-human")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = editorial_qa.main(["--tenant", "estudio-flow", "--root", sandbox])
        self.assertEqual(code, 0)
        text = stdout.getvalue()
        self.assertIn("Campanhas: 1", text)
        self.assertIn("APROVADO", text)
        self.assertIn("paridade_entregas", text)

    # ------------------------------------------------------------------
    # 8. Divergencia de duracao SRT x manifesto
    # ------------------------------------------------------------------
    def test_08_divergencia_duracao(self) -> None:
        sandbox = self._build_sandbox("duracao")
        path = self._srt_path(sandbox, "clinica-vital", "camp-saas-demo-clinica-vital-001")
        self._replace_in_file(path, "00:00:30,000", "00:00:29,000")
        result = editorial_qa.run_editorial_qa(root=sandbox)
        row = self._check(result, "duracao_srt_manifest")
        self.assertIn("SRT_DURACAO_DIVERGENTE", self._codes(row))
        self.assertTrue(any("29.000s" in p["message"] for p in row["problems"]))
        self.assertFalse(result["ok"])

    # ------------------------------------------------------------------
    # 9. Paridade: pacote social ausente
    # ------------------------------------------------------------------
    def test_09_paridade_pacote_social_ausente(self) -> None:
        sandbox = self._build_sandbox("paridade")
        package = os.path.join(
            sandbox, *editorial_qa.PACKAGE_ROOT, "estudio-flow",
            "camp-saas-demo-estudio-flow-001",
        )
        _force_rmtree(package)
        result = editorial_qa.run_editorial_qa(root=sandbox)
        row = self._check(result, "paridade_entregas")
        self.assertIn("PACOTE_SOCIAL_AUSENTE", self._codes(row))
        self.assertFalse(result["ok"])

    # ------------------------------------------------------------------
    # 10. Bloco de SRT vazio
    # ------------------------------------------------------------------
    def test_10_bloco_srt_vazio(self) -> None:
        sandbox = self._build_sandbox("vazio")
        path = self._srt_path(
            sandbox, "marca-salao", "camp-saas-demo-ns001-agenda-001"
        )
        self._set_cue_body(path, 0, "")
        result = editorial_qa.run_editorial_qa(root=sandbox)
        row = self._check(result, "legibilidade_mobile")
        self.assertIn("SRT_BLOCO_VAZIO", self._codes(row))
        self.assertFalse(result["ok"])

    # ------------------------------------------------------------------
    # 11. Determinismo e sem efeito colateral
    # ------------------------------------------------------------------
    def test_11_determinismo_sem_efeito_colateral(self) -> None:
        sandbox = self._build_sandbox("determinismo")
        before = {
            os.path.relpath(os.path.join(dirpath, name), sandbox)
            for dirpath, _dirs, files in os.walk(sandbox)
            for name in files
        }
        first = editorial_qa.run_editorial_qa(root=sandbox)
        second = editorial_qa.run_editorial_qa(root=sandbox)
        self.assertEqual(first, second)
        after = {
            os.path.relpath(os.path.join(dirpath, name), sandbox)
            for dirpath, _dirs, files in os.walk(sandbox)
            for name in files
        }
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
