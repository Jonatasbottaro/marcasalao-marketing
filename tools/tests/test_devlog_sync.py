"""Testes automatizados (unittest) para o consolidador tools/devlog_sync.py."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import unittest

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import devlog_sync  # noqa: E402

TEST_TMP_ROOT = os.path.join(REPO_ROOT, ".workspace", "tmp", "test_devlog_sync")

SAMPLE_CONTEXTO = """# contexto_projeto.md — Devlog acumulativo

---

## 1. Estado atual (atualizado em 2026-11-17)

| Item | Valor |
|------|-------|
| Raiz oficial | `D:/MEGA/Marketing/marcasalao-marketing` |
| HEAD main | `ccea432` |
| Fase atual | Merge Local Concluído na main |
| Status das 5 tarefas | Fase 1, Etapa 1 e Etapa 2 concluídas |

---

## 2. Fase 1 — Resumo

Texto histórico preservado integralmente.

---

## 7. Histórico de sessões

### Sessão 2026-11-17 — Entrada Anterior

- Registro pré-existente que nunca pode ser removido.
"""


class DevlogSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        if os.path.isdir(TEST_TMP_ROOT):
            shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)
        os.makedirs(TEST_TMP_ROOT, exist_ok=True)
        self.devlogs_dir = os.path.join(TEST_TMP_ROOT, "devlogs")
        os.makedirs(self.devlogs_dir, exist_ok=True)
        self.target = os.path.join(TEST_TMP_ROOT, "contexto_projeto.md")
        with open(self.target, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(SAMPLE_CONTEXTO)

    @classmethod
    def tearDownClass(cls) -> None:
        if os.path.isdir(TEST_TMP_ROOT):
            shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)

    def _write_devlog(self, filename: str, content: str) -> None:
        with open(os.path.join(self.devlogs_dir, filename), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def test_01_orders_agent_logs_numerically_and_appends_to_section_7(self) -> None:
        self._write_devlog(
            "etapa3-agente-2.md",
            "### Sessão 2026-11-18 — Etapa 3 (Agente 2): Áudio Multitrack\n\n- Detalhe agente 2.\n",
        )
        self._write_devlog(
            "etapa3-agente1.md",
            "## Sessão 2026-11-18 — Etapa 3 (Agente 1): Motor Base\n\n- Detalhe agente 1.\n",
        )
        self._write_devlog(
            "etapa3-agente-10.md",
            "### Sessão 2026-11-18 — Etapa 3 (Agente 10): Pós-etapa\n\n- Detalhe agente 10.\n",
        )
        self._write_devlog(
            "etapa3-agente4.md",
            "### Sessão 2026-11-18 — Etapa 3 (Agente 4): Estúdio Flow\n\n- Detalhe agente 4.\n",
        )
        # Arquivo fora do padrão deve ser ignorado.
        self._write_devlog("notas-soltas.md", "Não deve ser mesclado.")

        res = devlog_sync.sync_devlogs(
            devlogs_dir=self.devlogs_dir,
            target_path=self.target,
            root=REPO_ROOT,
            date_str="2026-11-19",
        )
        self.assertTrue(res["ok"])
        self.assertTrue(res["changed"])
        self.assertEqual([item["agent"] for item in res["applied"]], [1, 2, 4, 10])
        self.assertEqual(res["skipped"], [])

        with open(self.target, "rb") as handle:
            raw_bytes = handle.read()
        self.assertNotIn(b"\r\n", raw_bytes)
        content = raw_bytes.decode("utf-8")

        # Preserva conteúdo histórico
        self.assertIn("Texto histórico preservado integralmente.", content)
        self.assertIn("### Sessão 2026-11-17 — Entrada Anterior", content)
        self.assertIn("Registro pré-existente que nunca pode ser removido.", content)

        # Seção 1 atualizada
        self.assertIn("## 1. Estado atual (atualizado em 2026-11-19)", content)
        self.assertIn("Agentes 1, 2, 4, 10", content)

        # Ordem numérica estrita após a entrada anterior (1 -> 2 -> 4 -> 10)
        pos_old = content.index("### Sessão 2026-11-17 — Entrada Anterior")
        pos_1 = content.index("### Sessão 2026-11-18 — Etapa 3 (Agente 1)")
        pos_2 = content.index("### Sessão 2026-11-18 — Etapa 3 (Agente 2)")
        pos_4 = content.index("### Sessão 2026-11-18 — Etapa 3 (Agente 4)")
        pos_10 = content.index("### Sessão 2026-11-18 — Etapa 3 (Agente 10)")
        self.assertLess(pos_old, pos_1)
        self.assertLess(pos_1, pos_2)
        self.assertLess(pos_2, pos_4)
        self.assertLess(pos_4, pos_10)
        self.assertNotIn("Não deve ser mesclado.", content)

    def test_02_idempotent_second_run_does_not_duplicate(self) -> None:
        self._write_devlog(
            "etapa3-agente4.md",
            "### Sessão 2026-11-18 — Etapa 3 (Agente 4): Estúdio Flow\n\n- Item A.\n",
        )
        first = devlog_sync.sync_devlogs(
            devlogs_dir=self.devlogs_dir,
            target_path=self.target,
            root=REPO_ROOT,
            date_str="2026-11-18",
        )
        self.assertTrue(first["changed"])
        with open(self.target, "rb") as handle:
            bytes_after_first = handle.read()

        second = devlog_sync.sync_devlogs(
            devlogs_dir=self.devlogs_dir,
            target_path=self.target,
            root=REPO_ROOT,
            date_str="2026-11-20",
        )
        self.assertTrue(second["ok"])
        self.assertFalse(second["changed"])
        self.assertEqual(second["applied"], [])
        self.assertEqual(len(second["skipped"]), 1)

        with open(self.target, "rb") as handle:
            bytes_after_second = handle.read()
        self.assertEqual(bytes_after_first, bytes_after_second)

    def test_03_partial_new_log_appends_only_missing_agent(self) -> None:
        self._write_devlog(
            "etapa3-agente2.md",
            "### Sessão 2026-11-18 — Etapa 3 (Agente 2): Áudio\n\n- Ok 2.\n",
        )
        devlog_sync.sync_devlogs(
            devlogs_dir=self.devlogs_dir, target_path=self.target, root=REPO_ROOT, date_str="2026-11-18"
        )

        self._write_devlog(
            "etapa3-agente3.md",
            "### Sessão 2026-11-18 — Etapa 3 (Agente 3): Publish UTM\n\n- Ok 3.\n",
        )
        res = devlog_sync.sync_devlogs(
            devlogs_dir=self.devlogs_dir, target_path=self.target, root=REPO_ROOT, date_str="2026-11-18"
        )
        self.assertTrue(res["changed"])
        self.assertEqual([e["agent"] for e in res["applied"]], [3])
        self.assertEqual([e["agent"] for e in res["skipped"]], [2])

        with open(self.target, "r", encoding="utf-8") as handle:
            final_text = handle.read()
        self.assertEqual(final_text.count("### Sessão 2026-11-18 — Etapa 3 (Agente 2): Áudio"), 1)
        self.assertEqual(final_text.count("### Sessão 2026-11-18 — Etapa 3 (Agente 3): Publish UTM"), 1)

    def test_04_multi_etapa_orders_by_etapa_then_agent(self) -> None:
        self._write_devlog(
            "etapa4-agente2.md",
            "### Sessão 2026-11-19 — Etapa 4 (Agente 2): Review Portal\n\n- Detalhe etapa4 agente2.\n",
        )
        self._write_devlog(
            "etapa3-agente2.md",
            "### Sessão 2026-11-19 — Etapa 3 (Agente 2): Base\n\n- Detalhe etapa3 agente2.\n",
        )
        self._write_devlog(
            "etapa4-agente-10.md",
            "### Sessão 2026-11-19 — Etapa 4 (Agente 10): Pós\n\n- Detalhe etapa4 agente10.\n",
        )
        self._write_devlog(
            "etapa3-agente1.md",
            "### Sessão 2026-11-19 — Etapa 3 (Agente 1): Motor\n\n- Detalhe etapa3 agente1.\n",
        )
        self._write_devlog(
            "etapa4-agente1.md",
            "### Sessão 2026-11-19 — Etapa 4 (Agente 1): Formatos\n\n- Detalhe etapa4 agente1.\n",
        )

        res = devlog_sync.sync_devlogs(
            devlogs_dir=self.devlogs_dir,
            target_path=self.target,
            root=REPO_ROOT,
            date_str="2026-11-19",
        )
        self.assertTrue(res["ok"])
        self.assertTrue(res["changed"])
        self.assertEqual(
            [(e["etapa"], e["agent"]) for e in res["applied"]],
            [(3, 1), (3, 2), (4, 1), (4, 2), (4, 10)],
        )

        with open(self.target, "r", encoding="utf-8") as handle:
            content = handle.read()

        pos_old = content.index("### Sessão 2026-11-17 — Entrada Anterior")
        pos_31 = content.index("Etapa 3 (Agente 1)")
        pos_32 = content.index("Etapa 3 (Agente 2)")
        pos_41 = content.index("Etapa 4 (Agente 1)")
        pos_42 = content.index("Etapa 4 (Agente 2)")
        pos_410 = content.index("Etapa 4 (Agente 10)")
        self.assertLess(pos_old, pos_31)
        self.assertLess(pos_31, pos_32)
        self.assertLess(pos_32, pos_41)
        self.assertLess(pos_41, pos_42)
        self.assertLess(pos_42, pos_410)

        self.assertIn(
            "| Fase atual | Etapas 3 e 4 concluídas — Sync Multi-Agente "
            "(5 agente(s): Etapa 3: Agentes 1, 2 + Etapa 4: Agentes 1, 2, 10) |",
            content,
        )
        self.assertIn(
            "| Status das 5 tarefas | Fase 1, Etapa 1, Etapa 2, Etapa 3 e Etapa 4 "
            "(Etapa 3: Agentes 1, 2 + Etapa 4: Agentes 1, 2, 10) concluídas — ver seções 2 e 7 |",
            content,
        )

    def test_05_multi_etapa_idempotent_second_run(self) -> None:
        self._write_devlog(
            "etapa3-agente1.md",
            "### Sessão 2026-11-19 — Etapa 3 (Agente 1): Antiga\n\n- Item antigo.\n",
        )
        self._write_devlog(
            "etapa4-agente1.md",
            "### Sessão 2026-11-19 — Etapa 4 (Agente 1): Nova\n\n- Item novo.\n",
        )
        first = devlog_sync.sync_devlogs(
            devlogs_dir=self.devlogs_dir, target_path=self.target, root=REPO_ROOT, date_str="2026-11-19"
        )
        self.assertTrue(first["changed"])
        with open(self.target, "rb") as handle:
            bytes_after_first = handle.read()

        second = devlog_sync.sync_devlogs(
            devlogs_dir=self.devlogs_dir, target_path=self.target, root=REPO_ROOT, date_str="2026-11-20"
        )
        self.assertTrue(second["ok"])
        self.assertFalse(second["changed"])
        self.assertEqual(second["applied"], [])
        self.assertEqual(len(second["skipped"]), 2)

        with open(self.target, "rb") as handle:
            bytes_after_second = handle.read()
        self.assertEqual(bytes_after_first, bytes_after_second)

    def test_06_custom_pattern_restricts_discovery(self) -> None:
        self._write_devlog(
            "etapa3-agente1.md",
            "### Sessão 2026-11-19 — Etapa 3 (Agente 1): Antiga\n\n- Antiga.\n",
        )
        self._write_devlog(
            "etapa4-agente1.md",
            "### Sessão 2026-11-19 — Etapa 4 (Agente 1): Nova\n\n- Nova 1.\n",
        )
        self._write_devlog(
            "etapa4-agente-2.md",
            "### Sessão 2026-11-19 — Etapa 4 (Agente 2): Nova\n\n- Nova 2.\n",
        )

        res = devlog_sync.sync_devlogs(
            devlogs_dir=self.devlogs_dir,
            target_path=self.target,
            root=REPO_ROOT,
            date_str="2026-11-19",
            pattern="etapa4-agente*.md",
        )
        self.assertEqual(res["pattern"], "etapa4-agente*.md")
        self.assertEqual(
            [(e["etapa"], e["agent"]) for e in res["discovered"]],
            [(4, 1), (4, 2)],
        )
        self.assertEqual(
            [e["filename"] for e in res["applied"]],
            ["etapa4-agente1.md", "etapa4-agente-2.md"],
        )
        with open(self.target, "r", encoding="utf-8") as handle:
            content = handle.read()
        self.assertNotIn("Antiga.", content)
        self.assertIn("Nova 1.", content)
        self.assertIn("Nova 2.", content)

        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = devlog_sync.main([
                "--devlogs-dir", ".workspace/tmp/test_devlog_sync/devlogs",
                "--target", ".workspace/tmp/test_devlog_sync/contexto_projeto.md",
                "--root", REPO_ROOT,
                "--date", "2026-11-19",
                "--pattern", "etapa3-agente*.md",
                "--json",
            ])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["pattern"], "etapa3-agente*.md")
        self.assertEqual([e["filename"] for e in payload["applied"]], ["etapa3-agente1.md"])
        with open(self.target, "r", encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("Antiga.", content)

    def test_07_cli_json_and_path_containment(self) -> None:
        self._write_devlog(
            "etapa3-agente4.md",
            "### Sessão 2026-11-18 — Etapa 3 (Agente 4): Teste CLI\n\n- Conteúdo CLI.\n",
        )
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = devlog_sync.main([
                "--devlogs-dir", ".workspace/tmp/test_devlog_sync/devlogs",
                "--target", ".workspace/tmp/test_devlog_sync/contexto_projeto.md",
                "--root", REPO_ROOT,
                "--date", "2026-11-18",
                "--json",
            ])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(len(payload["applied"]), 1)

        with contextlib.redirect_stdout(io.StringIO()) as err_buf:
            rc_err = devlog_sync.main([
                "--devlogs-dir", "../fora-da-raiz",
                "--target", ".workspace/tmp/test_devlog_sync/contexto_projeto.md",
                "--root", REPO_ROOT,
                "--json",
            ])
        self.assertEqual(rc_err, 1)
        err_payload = json.loads(err_buf.getvalue())
        self.assertFalse(err_payload["ok"])
        self.assertIn("PATH_OUTSIDE_ROOT", err_payload["error"])


if __name__ == "__main__":
    unittest.main()
