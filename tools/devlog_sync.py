"""Consolidador automatico e idempotente de devlogs por etapa (etapa3, etapa4, ...).

Le arquivos `.workspace/devlogs/` que casam com `--pattern` (padrao:
`etapa*-agente*.md`) em ordem numerica pela tupla `(etapa_num, agente_num)`,
verifica se cada sessao ja foi incorporada em `contexto_projeto.md`, atualiza
a data e o status da Secao 1 e anexa apenas as novas entradas ao final da
Secao 7 (Historico de sessoes), sem nunca apagar o historico anterior.

Marcadores `<!-- devlog-sync:<arquivo> -->` gravados por esta ferramenta
(inclusive os historicos `etapa3-agente*.md`) continuam sendo reconhecidos e
garantem idempotencia entre etapas.

Uso (a partir da raiz do checkout ou worktree):
    python tools/devlog_sync.py --devlogs-dir .workspace/devlogs --target contexto_projeto.md
    python tools/devlog_sync.py --devlogs-dir .workspace/devlogs --target contexto_projeto.md --json
    python tools/devlog_sync.py --pattern "etapa4-agente*.md" --json
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

DEFAULT_PATTERN = "etapa*-agente*.md"
ETAPA_NUM_RE = re.compile(r"etapa(-?\d+)", re.IGNORECASE)
AGENTE_NUM_RE = re.compile(r"agente(-?\d+)", re.IGNORECASE)
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


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Traduz um glob simples em regex ancorada; `*` casa apenas numeros."""
    parts: list[str] = []
    for char in pattern:
        if char == "*":
            parts.append(r"(-?\d+)")
        else:
            parts.append(re.escape(char))
    return re.compile("^" + "".join(parts) + "$", re.IGNORECASE)


def _extract_num(regex: re.Pattern[str], filename: str) -> int:
    match = regex.search(filename)
    if not match:
        return 0
    digits = re.sub(r"\D", "", match.group(1))
    return int(digits) if digits else 0


def discover_devlogs(
    devlogs_abs: str,
    pattern: str = DEFAULT_PATTERN,
) -> list[tuple[int, int, str, str]]:
    """Descobre devlogs que casam com `pattern`, ordenados por (etapa, agente)."""
    fs_dir = render_local.fs_path(devlogs_abs)
    if not os.path.isdir(fs_dir):
        return []
    name_re = _glob_to_regex(pattern)
    found: list[tuple[int, int, str, str]] = []
    for name in os.listdir(fs_dir):
        if not name_re.match(name):
            continue
        full_path = os.path.join(devlogs_abs, name)
        if os.path.isfile(render_local.fs_path(full_path)):
            etapa_num = _extract_num(ETAPA_NUM_RE, name)
            agent_num = _extract_num(AGENTE_NUM_RE, name)
            found.append((etapa_num, agent_num, name, full_path))
    found.sort(key=lambda item: (item[0], item[1], item[2].lower()))
    return found


def _parse_devlog_entry(
    devlog_abs: str,
    filename: str,
    etapa_num: int,
    agent_num: int,
) -> dict[str, Any]:
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
            heading_line = f"### Sessão — Etapa {etapa_num} (Agente {agent_num})"
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
        "etapa": etapa_num,
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


def _join_labels(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " e " + items[-1]


def _etapas_summary(parsed_entries: list[dict[str, Any]]) -> tuple[int, str, int]:
    """Resume (total de agentes, rotulo, maior etapa) das entradas descobertas.

    Com uma unica etapa o rotulo preserva o formato historico
    (`Agentes 1, 2, 4`); com multiplas etapas o rotulo passa a agrupar por
    etapa (`Etapa 3: Agentes 1, 2 + Etapa 4: Agentes 1, 2, 10`).
    """
    etapas: dict[int, set[int]] = {}
    for entry in parsed_entries:
        etapas.setdefault(entry["etapa"], set()).add(entry["agent"])
    etapas_sorted = sorted(etapas)
    if len(etapas_sorted) == 1:
        agents = sorted(etapas[etapas_sorted[0]])
        return len(agents), ", ".join(str(n) for n in agents), etapas_sorted[0]
    total = 0
    parts: list[str] = []
    for etapa in etapas_sorted:
        agents = sorted(etapas[etapa])
        total += len(agents)
        parts.append(f"Etapa {etapa}: Agentes " + ", ".join(str(n) for n in agents))
    return total, " + ".join(parts), etapas_sorted[-1]


def _update_section_1(text: str, date_str: str, parsed_entries: list[dict[str, Any]]) -> str:
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

    count_agents, agents_label, max_etapa = _etapas_summary(parsed_entries)
    etapas_sorted = sorted({entry["etapa"] for entry in parsed_entries})

    if len(etapas_sorted) == 1:
        fase_atual = (
            f"Etapa {max_etapa} concluída — Plataforma Multi-Tenant + Sync Multi-Agente "
            f"({count_agents} agente(s): {agents_label})"
        )
        status_agents = f"(Agentes {agents_label})"
    else:
        fase_atual = (
            f"Etapas {_join_labels([str(e) for e in etapas_sorted])} concluídas — Sync Multi-Agente "
            f"({count_agents} agente(s): {agents_label})"
        )
        status_agents = f"({agents_label})"

    fases_prefix = "Fase 1, " + _join_labels([f"Etapa {n}" for n in range(1, max_etapa + 1)])

    updated_lines: list[str] = []
    for line in lines:
        if line.startswith("| Fase atual |"):
            updated_lines.append(f"| Fase atual | {fase_atual} |")
        elif line.startswith("| Status das 5 tarefas |"):
            updated_lines.append(
                f"| Status das 5 tarefas | {fases_prefix} {status_agents} concluídas — ver seções 2 e 7 |"
            )
        elif re.match(r"^\|\s*Status\s*\|", line):
            updated_lines.append(f"| Status | {fases_prefix} {status_agents} concluídas |")
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
    pattern: str = DEFAULT_PATTERN,
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

    discovered = discover_devlogs(devlogs_abs, pattern=pattern)
    parsed_entries = [
        _parse_devlog_entry(full_path, filename, etapa_num, agent_num)
        for etapa_num, agent_num, filename, full_path in discovered
    ]

    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for entry in parsed_entries:
        if _already_incorporated(original_text, entry):
            skipped.append(
                {"etapa": entry["etapa"], "agent": entry["agent"], "filename": entry["filename"], "heading": entry["heading"]}
            )
        else:
            applied.append(entry)

    effective_date = date_str or datetime.date.today().isoformat()
    changed = False

    if applied:
        updated = _update_section_1(original_text, effective_date, parsed_entries)
        updated = _append_to_section_7(updated, [e["block"] for e in applied])
        if updated != original_text:
            with open(target_fs, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(updated)
            changed = True

    return {
        "schemaVersion": 1,
        "ok": True,
        "pattern": pattern,
        "target": render_local.rel(root_real, target_abs),
        "devlogsDir": render_local.rel(root_real, devlogs_abs),
        "date": effective_date,
        "changed": changed,
        "discovered": [
            {"etapa": e["etapa"], "agent": e["agent"], "filename": e["filename"], "heading": e["heading"]}
            for e in parsed_entries
        ],
        "applied": [
            {"etapa": e["etapa"], "agent": e["agent"], "filename": e["filename"], "heading": e["heading"]}
            for e in applied
        ],
        "skipped": skipped,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Consolidador automatico de devlogs por etapa")
    parser.add_argument("--devlogs-dir", default=".workspace/devlogs", help="Diretorio com os devlogs")
    parser.add_argument("--target", default="contexto_projeto.md", help="Arquivo devlog consolidado alvo")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout/worktree")
    parser.add_argument("--date", default=None, help="Data YYYY-MM-DD para Secao 1 (opcional)")
    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help=f"Glob dos devlogs (default: {DEFAULT_PATTERN}; ex.: 'etapa4-agente*.md')",
    )
    parser.add_argument("--json", action="store_true", help="Emite JSON no stdout")

    args = parser.parse_args(argv)
    try:
        res = sync_devlogs(
            devlogs_dir=args.devlogs_dir,
            target_path=args.target,
            root=args.root,
            date_str=args.date,
            pattern=args.pattern,
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
