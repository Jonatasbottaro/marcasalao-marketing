"""Consolidador automatico e idempotente de devlogs da Etapa 3.

Le arquivos `.workspace/devlogs/etapa3-agente-*.md` (e `etapa3-agente*.md`) em
ordem numerica de agente, verifica se cada sessao ja foi incorporada em
`contexto_projeto.md`, atualiza a data e o status da Secao 1 e anexa apenas as
novas entradas ao final da Secao 7 (Historico de sessoes), sem nunca apagar o
historico anterior.

Uso (a partir da raiz do checkout ou worktree):
    python tools/devlog_sync.py --devlogs-dir .workspace/devlogs --target contexto_projeto.md
    python tools/devlog_sync.py --devlogs-dir .workspace/devlogs --target contexto_projeto.md --json
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import render_local

DEVLOG_FILENAME_RE = re.compile(r"^etapa3-agente-?(\d+)\.md$", re.IGNORECASE)
SECTION_1_RE = re.compile(r"^(##\s+1\.\s+Estado atual)(.*)$", re.MULTILINE)
SECTION_7_RE = re.compile(r"^##\s+7\.\s+Hist[oó]rico de sess[oõ]es.*$", re.MULTILINE)
NEXT_SECTION_RE = re.compile(r"^##\s+\d+\.", re.MULTILINE)
HEADING_3_RE = re.compile(r"^###\s+(.+)$", re.MULTILINE)
HEADING_TOP_RE = re.compile(r"^#{1,2}\s+(.+)$", re.MULTILINE)


class DevlogSyncError(Exception):
    """Erro estruturado ao validar ou sincronizar devlogs."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def _resolve_contained(root_real: str, path_value: str, label: str) -> str:
    candidate = (
        os.path.realpath(path_value)
        if os.path.isabs(path_value)
        else os.path.realpath(os.path.join(root_real, path_value))
    )
    if not render_local.contained(root_real, candidate):
        raise DevlogSyncError("PATH_OUTSIDE_ROOT", f"{label} fora da raiz do projeto: {candidate}")
    return candidate


def discover_devlogs(devlogs_abs: str) -> list[tuple[int, str, str]]:
    """Descobre `etapa3-agente-*.md` / `etapa3-agente*.md` ordenados numericamente."""
    fs_dir = render_local.fs_path(devlogs_abs)
    if not os.path.isdir(fs_dir):
        return []
    found: list[tuple[int, str, str]] = []
    for name in os.listdir(fs_dir):
        match = DEVLOG_FILENAME_RE.match(name)
        if not match:
            continue
        full_path = os.path.join(devlogs_abs, name)
        if os.path.isfile(render_local.fs_path(full_path)):
            found.append((int(match.group(1)), name, full_path))
    found.sort(key=lambda item: (item[0], item[1].lower()))
    return found


def _parse_devlog_entry(devlog_abs: str, filename: str, agent_num: int) -> dict[str, Any]:
    with open(render_local.fs_path(devlog_abs), "r", encoding="utf-8") as handle:
        raw = handle.read().replace("\r\n", "\n").replace("\r", "\n").strip()

    if not raw:
        raise DevlogSyncError("DEVLOG_VAZIO", f"devlog '{filename}' esta vazio")

    m3 = HEADING_3_RE.search(raw)
    if m3:
        heading_line = m3.group(0).strip()
        body_tail = raw[m3.end():].strip()
    else:
        m_top = HEADING_TOP_RE.search(raw)
        if m_top:
            heading_line = f"### {m_top.group(1).strip()}"
            before = raw[:m_top.start()].strip()
            after = raw[m_top.end():].strip()
            body_tail = "\n\n".join(part for part in (before, after) if part)
        else:
            heading_line = f"### Sessão — Etapa 3 (Agente {agent_num})"
            body_tail = raw

    marker = f"<!-- devlog-sync:{filename} -->"
    # Remove eventual marcador antigo duplicado antes de reformatar.
    body_lines = [line for line in body_tail.splitlines() if line.strip() != marker]
    cleaned_body = "\n".join(body_lines).strip()

    if cleaned_body:
        rendered_block = f"{heading_line}\n{marker}\n\n{cleaned_body}"
    else:
        rendered_block = f"{heading_line}\n{marker}"

    return {
        "agent": agent_num,
        "filename": filename,
        "heading": heading_line,
        "marker": marker,
        "block": rendered_block,
    }


def _already_incorporated(target_text: str, entry: dict[str, Any]) -> bool:
    if entry["marker"] in target_text:
        return True
    heading = entry["heading"].strip()
    for line in target_text.splitlines():
        if line.strip() == heading:
            return True
    return False


def _update_section_1(text: str, date_str: str, all_agent_nums: list[int]) -> str:
    m1 = SECTION_1_RE.search(text)
    if not m1:
        raise DevlogSyncError("SECAO_1_AUSENTE", "Cabecalho `## 1. Estado atual` nao encontrado")

    # Localiza o limite final da Secao 1 (`---` ou proximo `## `)
    sec_start = m1.start()
    after_heading = text[m1.end():]
    sep_match = re.search(r"(?m)^(?:---|##\s+\d+\.)", after_heading)
    sec_end = m1.end() + (sep_match.start() if sep_match else len(after_heading))
    sec_block = text[sec_start:sec_end]

    lines = sec_block.splitlines()
    if lines:
        if re.search(r"\(atualizado em [^)]+\)", lines[0]):
            lines[0] = re.sub(
                r"\(atualizado em [^)]+\)",
                f"(atualizado em {date_str})",
                lines[0],
            )
        else:
            lines[0] = f"{lines[0].rstrip()} (atualizado em {date_str})"

    agents_label = ", ".join(str(n) for n in sorted(set(all_agent_nums)))
    count_agents = len(set(all_agent_nums))

    updated_lines: list[str] = []
    for line in lines:
        if line.startswith("| Fase atual |"):
            updated_lines.append(
                f"| Fase atual | Etapa 3 concluída — Plataforma Multi-Tenant + Sync Multi-Agente "
                f"({count_agents} agente(s): {agents_label}) |"
            )
        elif line.startswith("| Status das 5 tarefas |"):
            updated_lines.append(
                f"| Status das 5 tarefas | Fase 1, Etapa 1, Etapa 2 e Etapa 3 "
                f"(Agentes {agents_label}) concluídas — ver seções 2 e 7 |"
            )
        elif re.match(r"^\|\s*Status\s*\|", line):
            updated_lines.append(
                f"| Status | Fase 1, Etapa 1, Etapa 2 e Etapa 3 (Agentes {agents_label}) concluídas |"
            )
        else:
            updated_lines.append(line)

    new_sec_block = "\n".join(updated_lines)
    if sec_block.endswith("\n") and not new_sec_block.endswith("\n"):
        new_sec_block += "\n"
    return text[:sec_start] + new_sec_block + text[sec_end:]


def _append_to_section_7(text: str, blocks: list[str]) -> str:
    m7 = SECTION_7_RE.search(text)
    if not m7:
        raise DevlogSyncError("SECAO_7_AUSENTE", "Cabecalho `## 7. Histórico de sessões` nao encontrado")

    after_7 = text[m7.end():]
    next_sec = NEXT_SECTION_RE.search(after_7)
    joined = "\n\n".join(blocks)

    if next_sec:
        insert_at = m7.end() + next_sec.start()
        prefix = text[:insert_at].rstrip("\n")
        suffix = text[insert_at:].lstrip("\n")
        return f"{prefix}\n\n{joined}\n\n{suffix}"

    prefix = text.rstrip("\n")
    return f"{prefix}\n\n{joined}\n"


def sync_devlogs(
    devlogs_dir: str = ".workspace/devlogs",
    target_path: str = "contexto_projeto.md",
    root: str = ".",
    date_str: str | None = None,
) -> dict[str, Any]:
    """Consolida novos devlogs em `target_path` de forma idempotente."""
    root_real = os.path.realpath(root)
    devlogs_abs = _resolve_contained(root_real, devlogs_dir, "devlogs-dir")
    target_abs = _resolve_contained(root_real, target_path, "target")

    target_fs = render_local.fs_path(target_abs)
    if not os.path.isfile(target_fs):
        raise DevlogSyncError("TARGET_AUSENTE", f"arquivo alvo nao encontrado: {target_abs}")

    with open(target_fs, "r", encoding="utf-8") as handle:
        original_text = handle.read().replace("\r\n", "\n").replace("\r", "\n")

    discovered = discover_devlogs(devlogs_abs)
    parsed_entries = [
        _parse_devlog_entry(full_path, filename, agent_num)
        for agent_num, filename, full_path in discovered
    ]

    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for entry in parsed_entries:
        if _already_incorporated(original_text, entry):
            skipped.append({"agent": entry["agent"], "filename": entry["filename"], "heading": entry["heading"]})
        else:
            applied.append(entry)

    effective_date = date_str or datetime.date.today().isoformat()
    changed = False

    if applied:
        all_agents = [entry["agent"] for entry in parsed_entries]
        updated = _update_section_1(original_text, effective_date, all_agents)
        updated = _append_to_section_7(updated, [e["block"] for e in applied])
        if updated != original_text:
            with open(target_fs, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(updated)
            changed = True

    return {
        "schemaVersion": 1,
        "ok": True,
        "target": render_local.rel(root_real, target_abs),
        "devlogsDir": render_local.rel(root_real, devlogs_abs),
        "date": effective_date,
        "changed": changed,
        "discovered": [
            {"agent": e["agent"], "filename": e["filename"], "heading": e["heading"]}
            for e in parsed_entries
        ],
        "applied": [
            {"agent": e["agent"], "filename": e["filename"], "heading": e["heading"]}
            for e in applied
        ],
        "skipped": skipped,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Consolidador automatico de devlogs Etapa 3")
    parser.add_argument("--devlogs-dir", default=".workspace/devlogs", help="Diretorio com etapa3-agente-*.md")
    parser.add_argument("--target", default="contexto_projeto.md", help="Arquivo devlog consolidado alvo")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout/worktree")
    parser.add_argument("--date", default=None, help="Data YYYY-MM-DD para Secao 1 (opcional)")
    parser.add_argument("--json", action="store_true", help="Emite JSON no stdout")

    args = parser.parse_args(argv)
    try:
        res = sync_devlogs(
            devlogs_dir=args.devlogs_dir,
            target_path=args.target,
            root=args.root,
            date_str=args.date,
        )
    except DevlogSyncError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"Erro: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(
            f"devlog_sync: {len(res['discovered'])} descoberto(s), "
            f"{len(res['applied'])} aplicado(s), {len(res['skipped'])} ignorado(s) -> {res['target']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
