"""Motor deterministico de quebra mobile de legendas SRT (Etapa 6 - Agente 2).

Reformata os textos dos cues para no maximo ``max_chars`` caracteres por
linha (padrao 48, teto de legibilidade mobile do ``editorial_qa``), em ate
``max_lines`` linhas (padrao 2), preservando integralmente:

  * indices dos blocos (1..N) e linhas de timestamp exatas;
  * pontuacao, acentos e texto UTF-8 (nenhuma palavra e reescrita);
  * fim de linha LF puro (``\\n``), sem CRLF.

O manifesto de cada entrega guarda ``sha256``/``bytes`` do ``<slug>.srt``;
quando o SRT muda, ``format_delivery_srts`` recalcula e sincroniza apenas a
entrada ``artifacts.srt`` (video, narracao e storyboard ficam intactos).

API:
    wrap_srt_cue_text(text, max_chars=48, max_lines=2) -> str
    format_srt_content(srt_text, max_chars=48, max_lines=2) -> (str, dict)
    format_delivery_srts(root=".", max_chars=48, update_manifests=True,
                         tenant=None, slug=None, dry_run=False) -> dict

CLI:
    python tools/srt_formatter.py [--all | --tenant <id> [--campaign <slug>]]
        [--max-chars 48] [--check-only] [--root <raiz>] [--json]

Exit codes: 0 conforme (ou formatter concluido); 1 check-only detectou linha
acima do teto ou o processamento teve falha; 2 uso/entrada invalida.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import render_local
import srt_validate

DEFAULT_MAX_CHARS = 48
DEFAULT_MAX_LINES = 2
DELIVERIES_REL = ("02-reels-shorts", "deliveries")

_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# Pontuacao que fecha uma unidade de sentido: o corte acontece logo depois.
_BREAK_PUNCT = (",", ".", ";", ":", "!", "?", "\u2014", "\u2013")
# Conjuncoes/ligacoes preferenciais: o corte acontece antes delas.
_CONJUNCTIONS = (
    " e ", " ou ", " mas ", " que ", " como ", " quando ",
    " para ", " com ", " porque ", " sem ",
)


class SrtFormatterError(Exception):
    """Falha controlada do formatador (codigo estavel + detalhe)."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fs(path: str) -> str:
    return render_local.fs_path(os.path.normpath(str(path)))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(_fs(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_text(text: str) -> str:
    return " ".join(str(text).split())


def _hard_cut(word: str, max_chars: int) -> list[str]:
    return [word[i:i + max_chars] for i in range(0, len(word), max_chars)]


def _greedy_lines(text: str, max_chars: int) -> list[str]:
    """Empacotamento guloso; palavras maiores que o teto sao cortadas sem loop."""
    lines: list[str] = []
    current = ""
    for word in text.split(" "):
        pieces = _hard_cut(word, max_chars) if len(word) > max_chars else [word]
        for piece in pieces:
            if not current:
                current = piece
            elif len(current) + 1 + len(piece) <= max_chars:
                current = f"{current} {piece}"
            else:
                lines.append(current)
                current = piece
    if current:
        lines.append(current)
    return lines


def _best_split(text: str, max_chars: int) -> tuple[str, str] | None:
    """Melhor corte em duas linhas dentro do teto.

    Prioridade: pontuacao (virgula/ponto/conjuncao textual), depois ponto medio
    em espaco. Entre candidatos validos, prefere o mais equilibrado.
    """
    candidates: list[tuple[int, str, str]] = []
    for index, char in enumerate(text):
        if char not in _BREAK_PUNCT:
            continue
        after = index + 1
        if after < len(text) and text[after] == " ":
            left = text[:after].rstrip()
            right = text[after + 1:].lstrip()
            if left and right:
                candidates.append((0, left, right))

    for conjunction in _CONJUNCTIONS:
        start = 0
        while True:
            found = text.find(conjunction, start)
            if found == -1:
                break
            left = text[:found].rstrip()
            # Mantem a conjuncao na segunda linha ("e ...").
            right = text[found + 1:].lstrip()
            if left and right:
                candidates.append((1, left, right))
            start = found + 1

    for index, char in enumerate(text):
        if char != " ":
            continue
        left = text[:index].rstrip()
        right = text[index + 1:].lstrip()
        if left and right:
            candidates.append((2, left, right))

    valid = [
        candidate for candidate in candidates
        if len(candidate[1]) <= max_chars and len(candidate[2]) <= max_chars
    ]
    if not valid:
        return None
    _, left, right = min(
        valid, key=lambda item: (item[0], abs(len(item[1]) - len(item[2])), item[1])
    )
    return left, right


def wrap_srt_cue_text(text: str, max_chars: int = DEFAULT_MAX_CHARS,
                      max_lines: int = DEFAULT_MAX_LINES) -> str:
    """Quebra o texto de um cue preservando palavras, acentos e pontuacao.

    Conteudo acima de ``max_lines * max_chars`` nao cabe no teto combinado:
    nesse caso o texto e preservado por completo e o empacotamento usa mais
    linhas, sempre com ``len(linha) <= max_chars`` (palavra isolada maior que
    o teto e cortada em pedacos seguros).
    """
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars <= 0:
        raise SrtFormatterError("MAX_CHARS_INVALIDO", f"max_chars={max_chars!r}")
    if isinstance(max_lines, bool) or not isinstance(max_lines, int) or max_lines <= 0:
        raise SrtFormatterError("MAX_LINES_INVALIDO", f"max_lines={max_lines!r}")

    normalized = _normalize_text(text)
    if not normalized:
        return ""
    if len(normalized) <= max_chars:
        return normalized

    if max_lines >= 2:
        split = _best_split(normalized, max_chars)
        if split is not None:
            return f"{split[0]}\n{split[1]}"

    return "\n".join(_greedy_lines(normalized, max_chars))


def _parse_blocks(srt_text: str) -> list[dict]:
    normalized = str(srt_text).replace("\r\n", "\n").replace("\r", "\n")
    blocks = []
    for raw in re.split(r"\n\s*\n", normalized.strip("\n")):
        if not raw.strip():
            continue
        lines = raw.split("\n")
        index = lines[0].strip()
        timestamp = lines[1].strip() if len(lines) > 1 else ""
        body_lines = [line.strip() for line in lines[2:] if line.strip()]
        if not index.isdigit():
            raise SrtFormatterError("SRT_INDICE_INVALIDO", f"indice {index!r}")
        if not srt_validate.TIMESTAMP_LINE_RE.match(timestamp):
            raise SrtFormatterError("SRT_TIMESTAMP_INVALIDO", f"tempo {timestamp!r}")
        blocks.append(
            {"index": index, "timestamp": timestamp, "body_lines": body_lines}
        )
    if not blocks:
        raise SrtFormatterError("SRT_VAZIO", "nenhum bloco de legenda")
    return blocks


def format_srt_content(srt_text: str, max_chars: int = DEFAULT_MAX_CHARS,
                       max_lines: int = DEFAULT_MAX_LINES) -> tuple[str, dict]:
    """Formata o SRT completo e devolve (novo_texto, estatisticas).

    Indices e timestamps sao copiados literalmente; o resultado e validado
    por ``srt_validate`` antes de ser devolvido.
    """
    blocks = _parse_blocks(srt_text)
    before_lengths: list[int] = []
    after_lengths: list[int] = []
    changed_cues = 0
    rebuilt: list[str] = []

    for block in blocks:
        original = block["body_lines"]
        before_lengths.extend(len(line) for line in original)
        wrapped = wrap_srt_cue_text(" ".join(original), max_chars, max_lines)
        wrapped_lines = wrapped.split("\n") if wrapped else []
        after_lengths.extend(len(line) for line in wrapped_lines)
        if tuple(wrapped_lines) != tuple(original):
            changed_cues += 1
        rebuilt.append(f"{block['index']}\n{block['timestamp']}\n{wrapped}")

    new_text = "\n\n".join(rebuilt) + "\n"
    errors = srt_validate.validate_srt_text(new_text)
    if errors:
        raise SrtFormatterError("SRT_INVALIDO", "; ".join(errors))

    stats = {
        "cues": len(blocks),
        "changedCues": changed_cues,
        "beforeMaxLineLength": max(before_lengths) if before_lengths else 0,
        "afterMaxLineLength": max(after_lengths) if after_lengths else 0,
        "beforeLongLines": sum(1 for n in before_lengths if n > max_chars),
        "afterLongLines": sum(1 for n in after_lengths if n > max_chars),
        "maxChars": max_chars,
        "maxLines": max_lines,
    }
    return new_text, stats


def _update_manifest_srt(manifest_path: str, slug: str, sha256: str, size: int) -> bool:
    """Sincroniza apenas a entrada SRT do manifesto; demais hashes intactos."""
    with open(_fs(manifest_path), "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    changed = False
    artifacts = manifest.get("artifacts")
    if isinstance(artifacts, dict):
        entry = artifacts.get("srt")
        if isinstance(entry, dict):
            if entry.get("sha256") != sha256:
                entry["sha256"] = sha256
                changed = True
            if entry.get("bytes") != size:
                entry["bytes"] = size
                changed = True
    files = manifest.get("files")
    if isinstance(files, dict):
        for key, entry in files.items():
            if not isinstance(entry, dict):
                continue
            label = str(entry.get("path") or key)
            if key == "srt" or label.endswith(f"{slug}.srt") or str(key).endswith(f"{slug}.srt"):
                if entry.get("sha256") != sha256:
                    entry["sha256"] = sha256
                    changed = True
                if "bytes" in entry and entry.get("bytes") != size:
                    entry["bytes"] = size
                    changed = True
    if changed:
        with open(_fs(manifest_path), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    return changed


def _discover(root_real: str, tenant: str | None, slug: str | None) -> list[tuple[str, str, str]]:
    deliveries = os.path.join(root_real, *DELIVERIES_REL)
    if not os.path.isdir(_fs(deliveries)):
        raise SrtFormatterError(
            "ENTREGAS_AUSENTES", "02-reels-shorts/deliveries/ nao encontrado"
        )
    jobs: list[tuple[str, str, str]] = []
    for tenant_id in sorted(os.listdir(_fs(deliveries))):
        tenant_dir = os.path.join(deliveries, tenant_id)
        if not os.path.isdir(_fs(tenant_dir)):
            continue
        if tenant is not None and tenant_id != tenant:
            continue
        if not _NAME_RE.match(tenant_id):
            continue
        for campaign in sorted(os.listdir(_fs(tenant_dir))):
            campaign_dir = os.path.join(tenant_dir, campaign)
            if not os.path.isdir(_fs(campaign_dir)):
                continue
            if slug is not None and campaign != slug:
                continue
            if not _NAME_RE.match(campaign):
                continue
            jobs.append((tenant_id, campaign, campaign_dir))
    if not jobs and (tenant is not None or slug is not None):
        alvo = f"{tenant or '*'}/{slug or '*'}"
        raise SrtFormatterError("CAMPANHA_NAO_ENCONTRADA", alvo)
    return jobs


def format_delivery_srts(root: str = ".", max_chars: int = DEFAULT_MAX_CHARS,
                         update_manifests: bool = True, tenant: str | None = None,
                         slug: str | None = None, dry_run: bool = False) -> dict:
    """Reformata os SRTs das entregas e sincroniza os manifestos.

    ``dry_run=True`` (usado pelo ``--check-only``) nao grava nada: apenas
    calcula o resultado e sinaliza linhas acima de ``max_chars``.
    """
    if tenant is not None and not _NAME_RE.match(str(tenant)):
        raise SrtFormatterError("TENANT_INVALIDO", str(tenant))
    if slug is not None and not _NAME_RE.match(str(slug)):
        raise SrtFormatterError("CAMPANHA_INVALIDA", str(slug))

    root_real = os.path.realpath(os.path.abspath(root))
    if not os.path.isdir(_fs(root_real)):
        raise SrtFormatterError("RAIZ_INVALIDA", str(root))

    rows: list[dict] = []
    errors: list[str] = []
    totals = {
        "campaigns": 0,
        "changed": 0,
        "manifestsUpdated": 0,
        "longLinesBefore": 0,
        "longLinesAfter": 0,
    }

    for tenant_id, campaign, campaign_dir in _discover(root_real, tenant, slug):
        if not render_local.contained(root_real, os.path.realpath(campaign_dir)):
            raise SrtFormatterError("CAMINHO_FORA_DA_RAIZ", f"{tenant_id}/{campaign}")
        srt_path = os.path.join(campaign_dir, f"{campaign}.srt")
        manifest_path = os.path.join(campaign_dir, "manifest.json")
        if not os.path.isfile(_fs(srt_path)):
            errors.append(f"SRT_AUSENTE: {tenant_id}/{campaign}")
            continue
        try:
            with open(_fs(srt_path), "rb") as handle:
                raw = handle.read()
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"SRT_ENCODING: {tenant_id}/{campaign} ({exc})")
            continue

        new_text, stats = format_srt_content(text, max_chars=max_chars)
        new_bytes = new_text.encode("utf-8")
        changed = new_bytes != raw
        written_bytes = new_bytes
        if changed and not dry_run:
            with open(_fs(srt_path), "wb") as handle:
                handle.write(new_bytes)
            written_bytes = new_bytes

        manifest_updated = False
        if update_manifests and not dry_run:
            if not os.path.isfile(_fs(manifest_path)):
                errors.append(f"MANIFESTO_AUSENTE: {tenant_id}/{campaign}")
            else:
                manifest_updated = _update_manifest_srt(
                    manifest_path, campaign,
                    _sha256_bytes(written_bytes), len(written_bytes),
                )

        totals["campaigns"] += 1
        totals["changed"] += int(changed)
        totals["manifestsUpdated"] += int(manifest_updated)
        totals["longLinesBefore"] += stats["beforeLongLines"]
        totals["longLinesAfter"] += stats["afterLongLines"]
        rows.append(
            {
                "tenant": tenant_id,
                "slug": campaign,
                "srtPath": render_local.rel(root_real, srt_path),
                "changed": changed,
                "dryRun": dry_run,
                "beforeMaxLineLength": stats["beforeMaxLineLength"],
                "afterMaxLineLength": stats["afterMaxLineLength"],
                "beforeLongLines": stats["beforeLongLines"],
                "afterLongLines": stats["afterLongLines"],
                "beforeSha256": _sha256_bytes(raw),
                "afterSha256": _sha256_bytes(written_bytes),
                "bytes": len(written_bytes),
                "manifestUpdated": manifest_updated,
            }
        )

    if dry_run:
        ok = not errors and totals["longLinesBefore"] == 0
    else:
        ok = not errors and totals["longLinesAfter"] == 0
    return {
        "schemaVersion": 1,
        "generatedBy": "tools/srt_formatter.py",
        "ok": ok,
        "maxChars": max_chars,
        "root": root_real,
        "tenantFilter": tenant,
        "campaignFilter": slug,
        "dryRun": dry_run,
        "totals": totals,
        "campaigns": rows,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Quebra mobile deterministica de legendas SRT (48 chars/linha, 2 linhas) "
            "com sincronizacao de hash/bytes no manifest.json"
        )
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--all", action="store_true", help="processa todas as entregas")
    selection.add_argument("--tenant", help="restrige a um tenant")
    parser.add_argument("--campaign", help="slug da campanha (exige --tenant)")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                        help=f"teto de caracteres por linha (padrao {DEFAULT_MAX_CHARS})")
    parser.add_argument("--check-only", action="store_true",
                        help="nao grava nada; exit 1 se houver linha acima do teto")
    parser.add_argument("--root", default=_repo_root(), help="raiz do checkout")
    parser.add_argument("--json", action="store_true", help="emite JSON no stdout")
    args = parser.parse_args(argv)

    if args.campaign and not args.tenant:
        print("Erro: --campaign exige --tenant", file=sys.stderr)
        return 2
    if args.all and args.tenant:
        print("Erro: use --all ou --tenant, nao ambos", file=sys.stderr)
        return 2
    if args.max_chars <= 0:
        print("Erro: --max-chars deve ser positivo", file=sys.stderr)
        return 2

    try:
        result = format_delivery_srts(
            root=args.root,
            max_chars=args.max_chars,
            update_manifests=not args.check_only,
            tenant=args.tenant,
            slug=args.campaign,
            dry_run=args.check_only,
        )
    except SrtFormatterError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro: entrada invalida ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        totals = result["totals"]
        print(
            f"SRTs: {totals['campaigns']} campanha(s), {totals['changed']} alterada(s), "
            f"{totals['manifestsUpdated']} manifesto(s) sincronizado(s); "
            f"linhas longas antes={totals['longLinesBefore']} depois={totals['longLinesAfter']}"
        )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())