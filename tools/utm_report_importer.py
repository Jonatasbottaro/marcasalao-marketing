"""Importador e analisador de performance UTM da fabrica multi-tenant.

Etapa 6 - Agente 4 (Growth Analytics & Data Pipeline). Implementacao 100% stdlib
(`csv`, `json`, `pathlib`, `argparse`, `collections`).

Fecha o ciclo de growth: ingere um CSV exportado do GA4, Plausible ou Umami,
normaliza os cabecalhos de cada provedor, cruza cada linha com a tupla de
atribuicao `(utm_source, utm_medium, utm_campaign, utm_content)` do calendario
editorial (ou da matriz consolidada como fallback) e produz um relatorio
executivo por tenant, canal, onda e variante de hook (A/B).

A variante de hook pode vir da coluna `hook_variant_used` do CSV ou de um log
manual opcional (`--hook-log`), aceito como:

    {"hooks": [{"slot_id": "slot-001", "variant": "A"}]}
    {"hooks": [{"utm_campaign": "camp-x", "utm_content": "marca-salao", "hook_variant": "B"}]}
    {"slot-001": "A", "slot-002": "B"}

Linhas de trafego nao atribuido sao reportadas em `unmatchedRows` sem reprovar a
execucao. Nenhuma receita financeira e simulada ou inferida.

CLI:
    python tools/utm_report_importer.py --metrics-csv <arquivo.csv>
        [--provider auto|ga4|plausible|umami] [--hook-log <json>]
        [--calendar 04-legendas/calendario-editorial.json]
        [--out-dir .workspace/tmp/utm-report] [--json]
    python tools/utm_report_importer.py --generate-template <saida.csv> [--json]

Exit codes: 0 relatorio gerado; 2 uso, entrada invalida ou caminho fora da raiz.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

CALENDAR_REL = "04-legendas/calendario-editorial.json"
MATRIZ_REL = "04-legendas/matriz-utm-consolidada.csv"
DEFAULT_OUT_DIR = ".workspace/tmp/utm-report"
REPORT_JSON = "utm-performance-report.json"
REPORT_MD = "utm-performance-report.md"
PROVIDERS = ("auto", "ga4", "plausible", "umami")
TEMPLATE_EXTRA_COLUMNS = ("sessions", "engaged_sessions", "conversions", "hook_variant_used")
WAVE_LABELS = {1: "Onda 1 9:16", 2: "Onda 2 1:1/16:9"}
EMPTY_MARKERS = {"", "-", "n/a", "na", "null", "none", "(not set)", "(none)", "(not provided)"}

ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    "ga4": {
        "source": ("session source",),
        "medium": ("session medium",),
        "campaign": ("session campaign",),
        "content": ("session manual ad content", "session manual content", "session content"),
        "sessions": ("sessions",),
        "engaged": ("engaged sessions",),
        "conversions": ("conversions", "key events"),
    },
    "plausible": {
        "source": ("utm_source", "source"),
        "medium": ("utm_medium", "medium"),
        "campaign": ("utm_campaign", "campaign"),
        "content": ("utm_content", "content"),
        "sessions": ("visitors", "visits", "sessions"),
        "engaged": ("engaged visitors", "engaged_sessions"),
        "conversions": ("conversions", "custom events"),
    },
    "umami": {
        "source": ("source", "utm_source"),
        "medium": ("medium", "utm_medium"),
        "campaign": ("campaign", "utm_campaign"),
        "content": ("content", "utm_content"),
        "sessions": ("views", "visits", "sessions"),
        "engaged": ("engaged_sessions", "engaged views"),
        "conversions": ("events", "conversions"),
    },
}

DETECTION_MARKERS: dict[str, dict[str, int]] = {
    "ga4": {
        "session source": 3,
        "session medium": 3,
        "session campaign": 3,
        "session manual ad content": 3,
        "sessions": 2,
        "engaged sessions": 1,
    },
    "plausible": {
        "visitors": 4,
        "utm_source": 2,
        "utm_medium": 2,
        "utm_campaign": 2,
        "utm_content": 2,
        "conversions": 1,
    },
    "umami": {
        "views": 4,
        "events": 4,
        "source": 1,
        "medium": 1,
        "campaign": 1,
        "content": 1,
    },
}

HOOK_COLUMNS = ("hook_variant_used", "hook variant used", "hook_variant", "hook")

HOOK_COMPARISON_LABELS = {
    "vencedor_A": "vencedor A",
    "vencedor_B": "vencedor B",
    "empate_tecnico": "empate tecnico",
    "amostra_insuficiente": "amostra insuficiente",
}
DEFAULT_MIN_SESSIONS = 100
DEFAULT_MIN_CONVERSIONS = 5
DEFAULT_Z_THRESHOLD = 1.96
SIGNIFICANCE_ALPHA = 0.05

# ---------------------------------------------------------------------------
# Reconciliacao bundle -> UTM (Etapa 12)
# ---------------------------------------------------------------------------

BUNDLES_REL = os.path.join(".workspace", "bundles")
MANIFEST_SUFFIX = "-manifest.json"
UTM_REPORT_DEFAULT_NAME = "utm-performance-report.json"

ATTR_STATUS_RECONCILIADO = "reconciliado"
ATTR_STATUS_AGUARDANDO_METRICAS = "aguardando_metricas"
ATTR_STATUS_DIVERGENCIA_TENANT = "divergencia_tenant"
ATTR_STATUS_NAO_ELEGIVEL_PREVIA = "nao_elegivel_para_PREVIA_NAO_APROVADA"


class UtmReportError(Exception):
    """Erro controlado do importador (entrada, provedor, calendario ou caminho)."""


def _root_real(root: str) -> Path:
    path = Path(root).resolve()
    if not path.is_dir():
        raise UtmReportError(f"RAIZ_INVALIDA: {root}")
    return path


def _resolve_contained(root_real: Path, value: str, label: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root_real / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root_real):
        raise UtmReportError(f"PATH_OUTSIDE_ROOT: {label} fora da raiz ({value})")
    return resolved


def _rel(root_real: Path, path: Path) -> str:
    return path.resolve().relative_to(root_real).as_posix()


def _read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        raise UtmReportError(f"JSON_INVALIDO: {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise UtmReportError(f"JSON_INVALIDO: {path.name}: esperado objeto")
    return data


def _norm_header(value: str) -> str:
    return " ".join(str(value or "").replace("\ufeff", "").strip().strip('"').lower().split())


def _norm_value(value: object) -> str:
    text = str(value if value is not None else "").strip()
    return "" if text.lower() in EMPTY_MARKERS else text


def _to_number(value: object) -> float:
    text = _norm_value(value).replace("%", "").replace(" ", "")
    if not text:
        return 0.0
    if "," in text:
        parts = text.split(",")
        if len(parts) > 1 and all(len(part) == 3 for part in parts[1:]):
            text = text.replace(",", "")
        else:
            text = text.replace(",", ".")
    return float(text)


def _to_int(value: float) -> int | float:
    return int(value) if float(value).is_integer() else round(value, 4)


def _normalize_variant(value: object) -> str:
    text = _norm_value(value).lower()
    if text in {"a", "hook a", "variant a", "hook_a", "hook-a"}:
        return "A"
    if text in {"b", "hook b", "variant b", "hook_b", "hook-b"}:
        return "B"
    return ""


def _rate(conversions: float, sessions: float) -> float:
    return round(conversions / sessions * 100, 2) if sessions else 0.0


# ---------------------------------------------------------------------------
# Ingestao de metricas
# ---------------------------------------------------------------------------
def detect_provider(headers: list[str]) -> str:
    normalized = {_norm_header(header) for header in headers}
    scores = {
        provider: sum(weight for marker, weight in markers.items() if marker in normalized)
        for provider, markers in DETECTION_MARKERS.items()
    }
    best = max(scores.values())
    if best == 0:
        raise UtmReportError(
            "PROVEDOR_NAO_DETECTADO: cabecalhos nao correspondem a GA4, Plausible ou Umami"
        )
    leaders = [provider for provider, score in scores.items() if score == best]
    if len(leaders) > 1:
        raise UtmReportError(
            f"PROVEDOR_AMBIGUO: {', '.join(sorted(leaders))} ({scores}); informe --provider"
        )
    return leaders[0]


def _column_map(headers: list[str], provider: str) -> dict[str, str]:
    normalized = {_norm_header(header): header for header in headers if header}
    mapping: dict[str, str] = {}
    for field, aliases in ALIASES[provider].items():
        for alias in aliases:
            if alias in normalized:
                mapping[field] = normalized[alias]
                break
    missing = [field for field in ("source", "medium", "campaign", "content", "sessions", "conversions")
               if field not in mapping]
    if missing:
        raise UtmReportError(
            f"COLUNAS_OBRIGATORIAS_AUSENTES: {', '.join(missing)} para provedor '{provider}'"
        )
    return mapping


def load_metrics(root_real: Path, metrics_csv: str, provider: str = "auto") -> dict:
    path = _resolve_contained(root_real, metrics_csv, "metrics-csv")
    if not path.is_file():
        raise UtmReportError(f"METRICS_AUSENTE: {metrics_csv}")
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise UtmReportError(f"METRICS_ILEGIVEL: {exc}") from exc
    with handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        if not headers:
            raise UtmReportError("METRICS_VAZIO: CSV sem cabecalho")
        effective = detect_provider(headers) if provider == "auto" else provider
        if effective not in ALIASES:
            raise UtmReportError(f"PROVEDOR_INVALIDO: {provider}")
        columns = _column_map(headers, effective)
        hook_column = next((h for h in headers if _norm_header(h) in HOOK_COLUMNS), None)

        rows: list[dict] = []
        invalid_rows: list[dict] = []
        for index, raw in enumerate(reader, start=2):
            try:
                row = {
                    "source": _norm_value(raw.get(columns["source"])),
                    "medium": _norm_value(raw.get(columns["medium"])),
                    "campaign": _norm_value(raw.get(columns["campaign"])),
                    "content": _norm_value(raw.get(columns["content"])),
                    "sessions": _to_number(raw.get(columns["sessions"])),
                    "engagedSessions": _to_number(raw.get(columns["engaged"]))
                    if "engaged" in columns
                    else 0.0,
                    "conversions": _to_number(raw.get(columns["conversions"])),
                    "hookVariant": _normalize_variant(raw.get(hook_column)) if hook_column else "",
                }
            except (TypeError, ValueError) as exc:
                invalid_rows.append({"line": index, "error": str(exc)})
                continue
            rows.append(row)

    return {
        "path": path,
        "provider": effective,
        "headers": headers,
        "rows": rows,
        "invalidRows": invalid_rows,
        "hookColumn": hook_column,
    }


# ---------------------------------------------------------------------------
# Calendario / matriz
# ---------------------------------------------------------------------------
def _slot_key(slot: dict) -> tuple[str, str, str, str]:
    params = slot.get("utmParams") or {}
    return (
        str(params.get("utm_source") or slot.get("utm_source") or ""),
        str(params.get("utm_medium") or slot.get("utm_medium") or ""),
        str(params.get("utm_campaign") or slot.get("utm_campaign") or ""),
        str(params.get("utm_content") or slot.get("utm_content") or ""),
    )


def _slot_from_json(slot: dict) -> dict:
    return {
        "slotId": str(slot.get("slotId") or ""),
        "tenantId": str(slot.get("tenantId") or ""),
        "brandName": slot.get("brandName"),
        "slug": str(slot.get("slug") or ""),
        "canal": str(slot.get("canal") or ""),
        "onda": int(slot.get("onda") or 0),
        "formatoVideo": slot.get("formatoVideo"),
        "semana": slot.get("semana"),
        "dataSugerida": slot.get("dataSugerida"),
        "hookVarianteA": slot.get("hookVarianteA"),
        "hookVarianteB": slot.get("hookVarianteB"),
        "utmParams": slot.get("utmParams") or {},
    }


def _slot_from_matrix(row: dict) -> dict:
    return {
        "slotId": str(row.get("slot_id") or ""),
        "tenantId": str(row.get("tenant_id") or ""),
        "brandName": row.get("brand_name"),
        "slug": str(row.get("slug") or ""),
        "canal": str(row.get("canal") or ""),
        "onda": int(row.get("onda") or 0),
        "formatoVideo": row.get("formato_video"),
        "semana": row.get("semana"),
        "dataSugerida": row.get("data_sugerida"),
        "hookVarianteA": None,
        "hookVarianteB": None,
        "utmParams": {
            "utm_source": row.get("utm_source"),
            "utm_medium": row.get("utm_medium"),
            "utm_campaign": row.get("utm_campaign"),
            "utm_content": row.get("utm_content"),
        },
    }


def load_calendar(root_real: Path, calendar: str | None = None) -> dict:
    explicit = calendar is not None
    calendar_path = _resolve_contained(root_real, calendar or CALENDAR_REL, "calendar")
    source_kind = "calendar"
    slots: list[dict] = []
    if calendar_path.is_file():
        data = _read_json(calendar_path)
        raw_slots = data.get("slots")
        if not isinstance(raw_slots, list):
            raise UtmReportError(f"CALENDARIO_INVALIDO: {calendar_path.name} sem secao slots")
        slots = [_slot_from_json(slot) for slot in raw_slots if isinstance(slot, dict)]
    else:
        if explicit:
            raise UtmReportError(f"CALENDARIO_AUSENTE: {calendar}")
        matrix_path = _resolve_contained(root_real, MATRIZ_REL, "matriz")
        if not matrix_path.is_file():
            raise UtmReportError(
                f"CALENDARIO_AUSENTE: {calendar or CALENDAR_REL} e matriz consolidada ausentes"
            )
        with matrix_path.open("r", encoding="utf-8-sig", newline="") as handle:
            slots = [_slot_from_matrix(row) for row in csv.DictReader(handle)]
        source_kind = "matriz"
        calendar_path = matrix_path

    index: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for slot in slots:
        index[_slot_key(slot)].append(slot)
    duplicates = [
        {"key": list(key), "slotIds": [slot["slotId"] for slot in entries]}
        for key, entries in index.items()
        if len(entries) > 1
    ]
    return {
        "path": calendar_path,
        "sourceKind": source_kind,
        "slots": slots,
        "index": dict(index),
        "duplicates": duplicates,
    }


# ---------------------------------------------------------------------------
# Hook log
# ---------------------------------------------------------------------------
def load_hook_log(root_real: Path, hook_log: str | None) -> dict:
    if not hook_log:
        return {"path": None, "bySlot": {}, "byKey": {}, "ignored": 0}
    path = _resolve_contained(root_real, hook_log, "hook-log")
    if not path.is_file():
        raise UtmReportError(f"HOOK_LOG_AUSENTE: {hook_log}")
    data = _read_json(path)
    by_slot: dict[str, str] = {}
    by_key: dict[tuple[str, str], str] = {}
    ignored = 0

    def register(item: dict) -> None:
        nonlocal ignored
        variant = ""
        for name in ("hook_variant", "hook_variant_used", "variant", "hook", "hookVariant"):
            variant = _normalize_variant(item.get(name))
            if variant:
                break
        if not variant:
            ignored += 1
            return
        slot_id = item.get("slot_id") or item.get("slotId")
        if slot_id:
            by_slot[str(slot_id)] = variant
            return
        campaign = item.get("utm_campaign") or item.get("campaign")
        content = item.get("utm_content") or item.get("content")
        if campaign and content:
            by_key[(str(campaign), str(content))] = variant
        else:
            ignored += 1

    if isinstance(data.get("hooks"), list):
        for item in data["hooks"]:
            if isinstance(item, dict):
                register(item)
    elif isinstance(data.get("slots"), list):
        for item in data["slots"]:
            if isinstance(item, dict):
                register(item)
    else:
        for key, value in data.items():
            variant = _normalize_variant(value)
            if not variant:
                if isinstance(value, dict):
                    register(value)
                else:
                    ignored += 1
                continue
            if "|" in str(key):
                campaign, content = str(key).split("|", 1)
                by_key[(campaign, content)] = variant
            else:
                by_slot[str(key)] = variant

    return {"path": path, "bySlot": by_slot, "byKey": by_key, "ignored": ignored}


# ---------------------------------------------------------------------------
# Analise
# ---------------------------------------------------------------------------
def _empty_group(label_key: str, label_value: str) -> dict:
    return {
        label_key: label_value,
        "sessions": 0.0,
        "engagedSessions": 0.0,
        "conversions": 0.0,
        "conversionRatePct": 0.0,
        "engagedRatePct": 0.0,
        "slots": 0,
    }


def _finalize_group(group: dict) -> dict:
    group["sessions"] = _to_int(group["sessions"])
    group["engagedSessions"] = _to_int(group["engagedSessions"])
    group["conversions"] = _to_int(group["conversions"])
    group["conversionRatePct"] = _rate(group["conversions"], group["sessions"])
    group["engagedRatePct"] = _rate(group["engagedSessions"], group["sessions"])
    return group


def _rank(groups: list[dict]) -> list[dict]:
    def label(item: dict) -> str:
        return str(item.get("tenantId") or item.get("channel") or item.get("label") or item.get("hook") or "")

    return sorted(
        groups,
        key=lambda item: (-float(item["conversions"]), -float(item["sessions"]), label(item)),
    )


def _two_proportion_z(
    conversions_a: float,
    sessions_a: float,
    conversions_b: float,
    sessions_b: float,
) -> tuple[float | None, float | None]:
    """Teste z de duas proporcoes com `math.erfc` — 100% stdlib, sem scipy/rede.

    A proporcao testada e `conversoes/sessoes` (CTR de conversao do link
    rastreado). `math.erfc` fornece o p-valor bilateral da normal, o que torna
    o resultado reproduzivel em qualquer estacao.
    """
    if sessions_a <= 0 or sessions_b <= 0:
        return None, None
    p_a = conversions_a / sessions_a
    p_b = conversions_b / sessions_b
    pooled = (conversions_a + conversions_b) / (sessions_a + sessions_b)
    variance = pooled * (1.0 - pooled) * (1.0 / sessions_a + 1.0 / sessions_b)
    if variance <= 0:
        return 0.0, 1.0
    z = (p_a - p_b) / math.sqrt(variance)
    p_value = math.erfc(abs(z) / math.sqrt(2.0))
    return round(z, 4), round(p_value, 6)


def _detect_hook_fatigue(
    conversions_w1: float,
    sessions_w1: float,
    conversions_w2: float,
    sessions_w2: float,
    min_conversions: int = DEFAULT_MIN_CONVERSIONS,
    z_threshold: float = DEFAULT_Z_THRESHOLD,
) -> dict:
    """Detecta fadiga temporal de hook comparando duas janelas.

    Compara a taxa de conversao (CVR) da janela inicial (w1) com a janela
    final (w2) para o mesmo hook/tenant/campanha. Se a CVR caiu
    estatisticamente (z <= -z_threshold e p < alpha), classifica como
    `fadiga_detectada`. Sem amostra minima em qualquer janela =>
    `amostra_insuficiente`. Caso contrario => `estavel`.

    Devolve dict com `fatigueStatus`, `fatigueZScore`, `fatiguePValue`,
    `fatigueDetected` (bool) e `fatigueReason`.
    """
    if sessions_w1 <= 0 or sessions_w2 <= 0:
        return {
            "fatigueStatus": "amostra_insuficiente",
            "fatigueZScore": None,
            "fatiguePValue": None,
            "fatigueDetected": False,
            "fatigueReason": (
                "Amostra insuficiente para detecao de fadiga: "
                f"necessario pelo menos 1 sessao em cada janela "
                f"(w1={_to_int(sessions_w1)}, w2={_to_int(sessions_w2)})."
            ),
        }
    if conversions_w1 < min_conversions or conversions_w2 < min_conversions:
        return {
            "fatigueStatus": "amostra_insuficiente",
            "fatigueZScore": None,
            "fatiguePValue": None,
            "fatigueDetected": False,
            "fatigueReason": (
                "Amostra insuficiente para detecao de fadiga: "
                f"minimo de {min_conversions} conversoes por janela "
                f"(w1={_to_int(conversions_w1)}, w2={_to_int(conversions_w2)})."
            ),
        }
    z, p_value = _two_proportion_z(conversions_w1, sessions_w1, conversions_w2, sessions_w2)
    if z is None or p_value is None:
        return {
            "fatigueStatus": "amostra_insuficiente",
            "fatigueZScore": None,
            "fatiguePValue": None,
            "fatigueDetected": False,
            "fatigueReason": "Nao foi possivel calcular o teste z de duas proporcoes.",
        }
    if z >= z_threshold and p_value < SIGNIFICANCE_ALPHA:
        return {
            "fatigueStatus": "fadiga_detectada",
            "fatigueZScore": z,
            "fatiguePValue": p_value,
            "fatigueDetected": True,
            "fatigueReason": (
                "Fadiga de hook detectada: CVR caiu da janela inicial para a final "
                f"(z={z}, p={p_value}, 95% de confianca)."
            ),
        }
    return {
        "fatigueStatus": "estavel",
        "fatigueZScore": z,
        "fatiguePValue": p_value,
        "fatigueDetected": False,
        "fatigueReason": (
            f"Hook estavel entre janelas (z={z}, p={p_value}); "
            "sem queda estatisticamente consistente."
        ),
    }


def _classify_hook(
    rate_a: float,
    rate_b: float,
    sessions_a: float,
    sessions_b: float,
    conversions_a: float,
    conversions_b: float,
    min_sessions: int = DEFAULT_MIN_SESSIONS,
    min_conversions: int = DEFAULT_MIN_CONVERSIONS,
    z_threshold: float = DEFAULT_Z_THRESHOLD,
) -> dict:
    """Classifica Hook A x Hook B exigindo significancia estatistica.

    Sem amostra minima (sessoes e conversoes por variante) nao ha vencedor; com
    amostra suficiente, so ha vencedor quando o teste z de duas proporcoes
    atinge o limiar (`z_threshold`, 95% de confianca). Fora disso, empate
    tecnico com recomendacao de manter o teste.
    """
    z, p_value = _two_proportion_z(conversions_a, sessions_a, conversions_b, sessions_b)
    if sessions_a + sessions_b < min_sessions or conversions_a < min_conversions or conversions_b < min_conversions:
        return {
            "classification": "amostra_insuficiente",
            "classificationLabel": HOOK_COMPARISON_LABELS["amostra_insuficiente"],
            "classificationReason": (
                f"Amostra insuficiente: minimo de {min_sessions} sessoes e "
                f"{min_conversions} conversoes por variante "
                f"(A={_to_int(sessions_a)}/{_to_int(conversions_a)}, "
                f"B={_to_int(sessions_b)}/{_to_int(conversions_b)})."
            ),
            "zScore": z,
            "pValue": p_value,
            "significant": False,
        }
    if rate_a == rate_b:
        return {
            "classification": "empate_tecnico",
            "classificationLabel": HOOK_COMPARISON_LABELS["empate_tecnico"],
            "classificationReason": f"Taxas identicas ({rate_a:.2f}%) entre Hook A e Hook B.",
            "zScore": z,
            "pValue": p_value,
            "significant": False,
        }
    significant = (
        z is not None
        and p_value is not None
        and abs(z) >= z_threshold
        and p_value < SIGNIFICANCE_ALPHA
    )
    winner = "B" if rate_b > rate_a else "A"
    if significant:
        classification = f"vencedor_{winner}"
        reason = (
            f"Diferenca estatisticamente consistente: Hook {winner} "
            f"{max(rate_a, rate_b):.2f}% vs {min(rate_a, rate_b):.2f}% "
            f"(z={z}, p={p_value}, 95% de confianca)."
        )
    else:
        classification = "empate_tecnico"
        reason = (
            f"Diferenca observada (A {rate_a:.2f}% vs B {rate_b:.2f}%) nao atinge 95% de "
            f"confianca (z={z}, p={p_value}); manter o teste A/B."
        )
    return {
        "classification": classification,
        "classificationLabel": HOOK_COMPARISON_LABELS[classification],
        "classificationReason": reason,
        "zScore": z,
        "pValue": p_value,
        "significant": bool(significant),
    }


def _compare_hooks(
    slots: list[dict],
    by_tenant: dict[str, dict],
    by_channel: dict[str, dict],
    min_sessions: int = DEFAULT_MIN_SESSIONS,
    min_conversions: int = DEFAULT_MIN_CONVERSIONS,
    z_threshold: float = DEFAULT_Z_THRESHOLD,
) -> dict:
    """Compara Hook A x Hook B por tenant e por campanha, com lift, teste z e classificacao."""

    def empty() -> dict:
        return {"A": _empty_group("hook", "A"), "B": _empty_group("hook", "B")}

    groups: dict[tuple[str, str], dict] = {}

    def ensure(tenant: str, campaign: str) -> dict:
        key = (tenant, campaign)
        entry = groups.get(key)
        if entry is None:
            entry = {"tenantId": tenant, "campaign": campaign, "A": _empty_group("hook", "A"), "B": _empty_group("hook", "B")}
            groups[key] = entry
        return entry

    for slot in slots:
        entry = ensure(slot["tenantId"], slot["slug"])
        variant = slot.get("hookVariant") or ""
        if variant in ("A", "B"):
            side = entry[variant]
            side["sessions"] += float(slot["sessions"])
            side["engagedSessions"] += float(slot["engagedSessions"])
            side["conversions"] += float(slot["conversions"])
            side["slots"] += 1

    for entry in groups.values():
        for side in ("A", "B"):
            group = entry[side]
            group["label"] = f"Hook {side}"
            _finalize_group(group)

    # Campanhas sem nenhuma sessao atribuida a A ou B nao entram no comparativo:
    # sem variante medida nao ha o que classificar.
    active = [entry for entry in groups.values() if entry["A"]["sessions"] or entry["B"]["sessions"]]

    def finalize(entry: dict) -> dict:
        sessions_a = entry["A"]["sessions"]
        sessions_b = entry["B"]["sessions"]
        sessions_total = sessions_a + sessions_b
        conversions_a = entry["A"]["conversions"]
        conversions_b = entry["B"]["conversions"]
        rate_a = entry["A"]["conversionRatePct"]
        rate_b = entry["B"]["conversionRatePct"]
        engaged_a = entry["A"]["engagedRatePct"]
        engaged_b = entry["B"]["engagedRatePct"]
        lift_conversion = _rate(rate_b - rate_a, rate_a) if rate_a else None
        lift_engagement = _rate(engaged_b - engaged_a, engaged_a) if engaged_a else None

        stats = _classify_hook(
            rate_a,
            rate_b,
            sessions_a,
            sessions_b,
            conversions_a,
            conversions_b,
            min_sessions,
            min_conversions,
            z_threshold,
        )

        return {
            "tenantId": entry["tenantId"],
            "campaign": entry["campaign"],
            "sessionsA": sessions_a,
            "sessionsB": sessions_b,
            "sessionsTotal": sessions_total,
            "conversionsA": conversions_a,
            "conversionsB": conversions_b,
            "conversionRateA": rate_a,
            "conversionRateB": rate_b,
            "engagedRateA": engaged_a,
            "engagedRateB": engaged_b,
            "liftConversionPct": lift_conversion,
            "liftEngagementPct": lift_engagement,
            "slotsA": entry["A"]["slots"],
            "slotsB": entry["B"]["slots"],
            "classification": stats["classification"],
            "classificationLabel": stats["classificationLabel"],
            "classificationReason": stats["classificationReason"],
            "zScore": stats["zScore"],
            "pValue": stats["pValue"],
            "significant": stats["significant"],
        }

    rows = sorted((finalize(entry) for entry in active), key=lambda row: (row["tenantId"], row["campaign"]))

    tenants = sorted({row["tenantId"] for row in rows})
    tenant_rows: list[dict] = []
    for tenant in tenants:
        group_a = _empty_group("tenantId", tenant)
        group_b = _empty_group("tenantId", tenant)
        count = 0
        for row in rows:
            if row["tenantId"] != tenant:
                continue
            count += 1
            for side, acc in (("A", group_a), ("B", group_b)):
                source = row[f"conversionRate{side}"]
                sessions = row[f"sessions{side}"]
                if sessions:
                    acc["conversions"] += row[f"conversions{side}"]
                    acc["sessions"] += sessions
                    acc["engagedSessions"] += row[f"engagedRate{side}"] / 100 * sessions
        if count:
            _finalize_group(group_a)
            _finalize_group(group_b)
            total = group_a["sessions"] + group_b["sessions"]
            tenant_stats = _classify_hook(
                group_a["conversionRatePct"],
                group_b["conversionRatePct"],
                group_a["sessions"],
                group_b["sessions"],
                group_a["conversions"],
                group_b["conversions"],
                min_sessions,
                min_conversions,
                z_threshold,
            )
            tenant_rows.append(
                {
                    "tenantId": tenant,
                    "campaigns": count,
                    "sessionsA": group_a["sessions"],
                    "sessionsB": group_b["sessions"],
                    "sessionsTotal": total,
                    "conversionRateA": group_a["conversionRatePct"],
                    "conversionRateB": group_b["conversionRatePct"],
                    "engagedRateA": group_a["engagedRatePct"],
                    "engagedRateB": group_b["engagedRatePct"],
                    "liftConversionPct": _rate(
                        group_b["conversionRatePct"] - group_a["conversionRatePct"],
                        group_a["conversionRatePct"],
                    )
                    if group_a["conversionRatePct"]
                    else None,
                    "classification": tenant_stats["classification"],
                    "classificationLabel": tenant_stats["classificationLabel"],
                    "classificationReason": tenant_stats["classificationReason"],
                    "zScore": tenant_stats["zScore"],
                    "pValue": tenant_stats["pValue"],
                    "significant": tenant_stats["significant"],
                }
            )

    return {
        "minSessions": min_sessions,
        "minConversions": min_conversions,
        "statistics": {
            "method": "two_proportion_z",
            "alpha": SIGNIFICANCE_ALPHA,
            "zThreshold": z_threshold,
            "minSessions": min_sessions,
            "minConversions": min_conversions,
        },
        "byCampaign": rows,
        "byTenant": tenant_rows,
    }


def _tenant_benchmarks(
    by_tenant: dict[str, dict],
    hook_comparison: dict,
    by_wave: dict[int, dict],
    min_conversions: int,
) -> dict:
    """Consolida benchmarks isolados por tenant_id.

    Para cada tenant: total de campanhas, sessoes/engajadas/conversoes,
    taxa de vitoria A/B (vencedor_A ou vencedor_B sobre total de campanhas
    comparadas), hooks com fadiga detectada (comparando Onda 1 vs Onda 2)
    e ranking de canais/formatos por CVR dentro do tenant.

    Nao ha vazamento de metrica entre tenants: cada tenant e agregado
    somente a partir de seus proprios slots.
    """
    # Taxa de vitoria A/B por tenant a partir do comparativo por campanha.
    ab_by_tenant: dict[str, dict] = {}
    for row in hook_comparison.get("byCampaign", []):
        tid = row.get("tenantId")
        if tid is None:
            continue
        entry = ab_by_tenant.setdefault(tid, {"total": 0, "wins": 0})
        entry["total"] += 1
        if row.get("classification") in ("vencedor_A", "vencedor_B"):
            entry["wins"] += 1

    # Fadiga temporal: compara Onda 1 (w1) vs Onda 2 (w2) por tenant.
    wave1 = by_wave.get(1, _empty_group("onda", "Onda 1"))
    wave2 = by_wave.get(2, _empty_group("onda", "Onda 2"))

    benchmarks: dict[str, dict] = {}
    for tenant_id, group in by_tenant.items():
        ab = ab_by_tenant.get(tenant_id, {"total": 0, "wins": 0})
        ab_rate = round(ab["wins"] / ab["total"], 4) if ab["total"] else None

        fadiga = _detect_hook_fatigue(
            wave1["conversions"],
            wave1["sessions"],
            wave2["conversions"],
            wave2["sessions"],
            min_conversions=min_conversions,
        )

        benchmarks[tenant_id] = {
            "tenantId": tenant_id,
            "campaigns": group.get("campaigns", 0),
            "sessions": group["sessions"],
            "engagedSessions": group["engagedSessions"],
            "conversions": group["conversions"],
            "conversionRatePct": group["conversionRatePct"],
            "engagedRatePct": group["engagedRatePct"],
            "slots": group["slots"],
            "abWinRatePct": ab_rate,
            "abCampaignsTotal": ab["total"],
            "abCampaignsWins": ab["wins"],
            "hooksComFadiga": fadiga["fatigueDetected"],
            "hooksComFadigaStatus": fadiga["fatigueStatus"],
            "hooksComFadigaZScore": fadiga["fatigueZScore"],
            "hooksComFadigaPValue": fadiga["fatiguePValue"],
            "hooksComFadigaReason": fadiga["fatigueReason"],
        }

    return {
        "minConversions": min_conversions,
        "byTenant": [benchmarks[tid] for tid in sorted(benchmarks)],
    }


def analyze_performance(
    root: str = ".",
    metrics_csv: str | None = None,
    provider: str = "auto",
    hook_log: str | None = None,
    calendar: str | None = None,
    out_dir: str = DEFAULT_OUT_DIR,
    min_sessions: int = DEFAULT_MIN_SESSIONS,
    min_conversions: int = DEFAULT_MIN_CONVERSIONS,
) -> dict:
    """Ingere o CSV, cruza com o calendario e grava o relatorio executivo."""
    if not metrics_csv:
        raise UtmReportError("USO_INVALIDO: informe --metrics-csv ou --generate-template")
    if min_sessions < 0:
        raise UtmReportError(f"LIMIAR_INVALIDO: --min-hook-sessions nao pode ser negativo ({min_sessions})")
    if min_conversions < 0:
        raise UtmReportError(
            f"LIMIAR_INVALIDO: --min-hook-conversions nao pode ser negativo ({min_conversions})"
        )
    root_real = _root_real(root)
    calendar_data = load_calendar(root_real, calendar)
    hooks = load_hook_log(root_real, hook_log)
    metrics = load_metrics(root_real, metrics_csv, provider)

    slot_totals: dict[str, dict] = {}
    unmatched: list[dict] = []
    matched_rows = 0
    variant_rows = 0

    for row in metrics["rows"]:
        key = (row["source"], row["medium"], row["campaign"], row["content"])
        candidates = calendar_data["index"].get(key) or []
        if not candidates:
            unmatched.append({**row, "reason": "UTM_NOT_IN_CALENDAR"})
            continue
        slot = candidates[0]
        matched_rows += 1
        entry = slot_totals.setdefault(
            slot["slotId"],
            {
                **slot,
                "sessions": 0.0,
                "engagedSessions": 0.0,
                "conversions": 0.0,
                "metricsRows": 0,
                "hookVariant": "",
            },
        )
        entry["sessions"] += row["sessions"]
        entry["engagedSessions"] += row["engagedSessions"]
        entry["conversions"] += row["conversions"]
        entry["metricsRows"] += 1

        variant = (
            hooks["bySlot"].get(slot["slotId"])
            or hooks["byKey"].get((row["campaign"], row["content"]))
            or row["hookVariant"]
        )
        if variant:
            entry["hookVariant"] = variant
            variant_rows += 1

    slot_results = []
    for entry in slot_totals.values():
        entry["sessions"] = _to_int(entry["sessions"])
        entry["engagedSessions"] = _to_int(entry["engagedSessions"])
        entry["conversions"] = _to_int(entry["conversions"])
        entry["conversionRatePct"] = _rate(entry["conversions"], entry["sessions"])
        entry["engagedRatePct"] = _rate(entry["engagedSessions"], entry["sessions"])
        slot_results.append(entry)
    slot_results.sort(key=lambda item: item["slotId"])

    total_sessions = sum(float(item["sessions"]) for item in slot_results)
    total_engaged = sum(float(item["engagedSessions"]) for item in slot_results)
    total_conversions = sum(float(item["conversions"]) for item in slot_results)

    by_tenant: dict[str, dict] = {}
    by_channel: dict[str, dict] = {}
    by_wave: dict[int, dict] = {}
    tenant_campaigns: dict[str, set[str]] = {}
    for slot in calendar_data["slots"]:
        by_tenant.setdefault(
            slot["tenantId"], _empty_group("tenantId", slot["tenantId"])
        )
        tenant_campaigns.setdefault(slot["tenantId"], set()).add(slot["slug"])
        by_channel.setdefault(slot["canal"], _empty_group("channel", slot["canal"]))
        by_wave.setdefault(slot["onda"], _empty_group("onda", WAVE_LABELS.get(slot["onda"], f"Onda {slot['onda']}")))
        by_wave[slot["onda"]]["label"] = WAVE_LABELS.get(slot["onda"], f"Onda {slot['onda']}")

    by_hook: dict[str, dict] = {}

    def add(group: dict, slot: dict) -> None:
        group["sessions"] += float(slot["sessions"])
        group["engagedSessions"] += float(slot["engagedSessions"])
        group["conversions"] += float(slot["conversions"])
        group["slots"] += 1

    for slot in slot_results:
        add(by_tenant[slot["tenantId"]], slot)
        add(by_channel[slot["canal"]], slot)
        add(by_wave[slot["onda"]], slot)
        if slot["hookVariant"]:
            group = by_hook.setdefault(
                slot["hookVariant"],
                _empty_group("hook", slot["hookVariant"]),
            )
            group["label"] = f"Hook {slot['hookVariant']}"
            add(group, slot)

    for group in by_tenant.values():
        group["campaigns"] = len(tenant_campaigns.get(group["tenantId"], set()))
        _finalize_group(group)
    for group in by_channel.values():
        _finalize_group(group)
    for group in by_wave.values():
        _finalize_group(group)
    for group in by_hook.values():
        _finalize_group(group)

    hook_rows = [by_hook[key] for key in sorted(by_hook)]
    hook_comparison = _compare_hooks(
        slot_results, by_tenant, by_channel,
        min_sessions=min_sessions, min_conversions=min_conversions,
    )
    tenant_benchmarks = _tenant_benchmarks(
        by_tenant, hook_comparison, by_wave, min_conversions
    )
    data_quality = {
        "invalidRows": metrics["invalidRows"],
        "duplicateCalendarKeys": calendar_data["duplicates"],
        "hookLogIgnored": hooks["ignored"],
        "hookLogEntries": len(hooks["bySlot"]) + len(hooks["byKey"]),
        "rowsWithoutHookVariant": matched_rows - variant_rows,
    }

    report = {
        "schemaVersion": 1,
        "generatedBy": "tools/utm_report_importer.py",
        "ok": True,
        "provider": metrics["provider"],
        "metricsCsv": _rel(root_real, metrics["path"]),
        "calendarPath": _rel(root_real, calendar_data["path"]),
        "calendarSource": calendar_data["sourceKind"],
        "hookLogPath": _rel(root_real, hooks["path"]) if hooks["path"] else None,
        "totals": {
            "rows": len(metrics["rows"]),
            "matchedRows": matched_rows,
            "unmatchedRows": len(unmatched),
            "coveragePct": round(matched_rows / len(metrics["rows"]) * 100, 2) if metrics["rows"] else 0.0,
            "sessions": _to_int(total_sessions),
            "engagedSessions": _to_int(total_engaged),
            "conversions": _to_int(total_conversions),
            "conversionRatePct": _rate(total_conversions, total_sessions),
            "engagedRatePct": _rate(total_engaged, total_sessions),
            "slotsMatched": len(slot_results),
            "slotsInCalendar": len(calendar_data["slots"]),
        },
        "rankings": {
            "byTenant": _rank(list(by_tenant.values())),
            "byChannel": _rank(list(by_channel.values())),
            "byWave": _rank(list(by_wave.values())),
            "byHook": hook_rows,
            "hookComparison": hook_comparison,
            "tenantBenchmarks": tenant_benchmarks,
        },
        "slots": slot_results,
        "unmatchedRows": unmatched,
        "dataQuality": data_quality,
        "financialSimulation": False,
    }

    out_abs = _resolve_contained(root_real, out_dir, "out-dir")
    out_abs.mkdir(parents=True, exist_ok=True)
    json_path = out_abs / REPORT_JSON
    md_path = out_abs / REPORT_MD
    report["reports"] = {"json": _rel(root_real, json_path), "markdown": _rel(root_real, md_path)}
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    md_path.write_text(render_markdown(report), encoding="utf-8", newline="\n")
    return report


# ---------------------------------------------------------------------------
# Reconciliacao bundle -> UTM (Etapa 12: Closed-Loop Attribution)
# ---------------------------------------------------------------------------

def _bundles_root(root_real: Path) -> Path:
    return root_real / BUNDLES_REL


def _iter_bundle_manifests(root_real: Path, bundles_abs: Path | None = None) -> list[tuple[Path, dict]]:
    """Percorre .workspace/bundles/<tenantId>/<slug>/ e carrega cada manifesto.

    Devolve lista de (caminho_absoluto_do_manifesto, dict_carregado). Silenciosamente
    ignora diretorios/arquivos ausentes e manifestos JSON invalidos (fail-soft
    para nao quebrar o relatorio quando um bundle esta incompleto).
    """
    found: list[tuple[Path, dict]] = []
    bundles_root = bundles_abs or _bundles_root(root_real)
    if not bundles_root.is_dir():
        return found
    for tenant_dir in sorted(p for p in bundles_root.iterdir() if p.is_dir()):
        tenant_id = tenant_dir.name
        for slug_dir in sorted(p for p in tenant_dir.iterdir() if p.is_dir()):
            slug = slug_dir.name
            for manifest_path in sorted(slug_dir.glob("*" + MANIFEST_SUFFIX)):
                try:
                    data = _read_json(manifest_path)
                except UtmReportError:
                    continue
                if not isinstance(data, dict):
                    continue
                data["_manifestAbsPath"] = str(manifest_path)
                found.append((manifest_path, data))
    return found


def _match_slot_to_manifest(slot: dict, manifest: dict) -> bool:
    """Verifica se o slot (campanha/tenant) corresponde ao manifesto do bundle."""
    return (
        str(slot.get("tenantId") or "") == str(manifest.get("tenantId") or "")
        and str(slot.get("slug") or "") == str(manifest.get("slug") or "")
    )


def _promotion_history_has_winner(history: list[dict] | None) -> bool:
    """True quando o historico de promocoes contem um vencedor (A ou B) persistido."""
    if not isinstance(history, list):
        return False
    for entry in history:
        if not isinstance(entry, dict):
            continue
        variant = entry.get("promotedVariant") or entry.get("decisao")
        if variant in ("A", "B"):
            return True
    return False


def reconcile_bundles(
    root: str = ".",
    utm_report: dict | None = None,
    bundles_dir: str | None = None,
) -> dict:
    """Reconcilia pacotes entregues (.zip + manifesto) com o relatorio de performance UTM.

    Para cada bundle encontrado em ``.workspace/bundles/<tenantId>/<slug>/`` (ou
    ``bundles_dir`` quando informado) cruza o manifesto com o(s) slot(s) do
    calendário correspondente no relatorio UTM, produzindo ``bundleAttribution``:

    - ``reconciliado``: manifesto existe e UTM report contem metrica para o
      (tenantId, slug) correspondente. Anexa impressoes, cliques, conversoes,
      CTR, conversoes totais, conversionRate, observedUpliftPct e
      winnerSustained (quando promotionHistory presente).
    - ``aguardando_metricas``: bundle aprovado mas ainda sem dados de UTM
      (relatorio ausente ou slot nao encontrado).
    - ``divergencia_tenant``: tenantId do manifesto nao bate com o do slot UTM.
    - ``nao_elegivel_para_PREVIA_NAO_APROVADA``: bundle com selo PREVIA_NAO_APROVADA
      nao pode ser reconciliado ate ser aprovado pelo titular.

    Parametros:
        root: raiz do checkout (contencao de caminho).
        utm_report: relatorio UTM ja carregado (dict de analyze_performance).
        bundles_dir: diretorio de bundles (padrao: <root>/.workspace/bundles).

    Devolve dict com ``bundles[]``, ``summary`` (contadores por status) e
    ``attributionPath`` (caminho relativo gravado). Nunca modifica .zip nem
    manifesto (somente leitura).
    """
    root_real = _root_real(root)
    if bundles_dir:
        bundles_abs = _resolve_contained(root_real, bundles_dir, "bundles-dir")
    else:
        bundles_abs = _bundles_root(root_real)

    manifests = _iter_bundle_manifests(root_real, bundles_abs)

    slots_by_key: dict[tuple[str, str], list[dict]] = {}
    if utm_report:
        for slot in utm_report.get("slots", []):
            if not isinstance(slot, dict):
                continue
            key = (str(slot.get("tenantId") or ""), str(slot.get("slug") or ""))
            slots_by_key.setdefault(key, []).append(slot)

    bundle_attributions: list[dict] = []
    summary = {
        "total": 0,
        "reconciliado": 0,
        "aguardando_metricas": 0,
        "divergencia_tenant": 0,
        "nao_elegivel_para_PREVIA_NAO_APROVADA": 0,
    }

    for manifest_path, manifest in manifests:
        summary["total"] += 1
        tenant_id = str(manifest.get("tenantId") or "")
        slug = str(manifest.get("slug") or "")
        approval_status = str(manifest.get("approvalStatus") or "")
        bundle_sha256 = manifest.get("bundleSha256") or ""
        promotion_history = manifest.get("promotionHistory") or []
        items = manifest.get("items") or []

        # 1. Nao elegivel: previo sem aprovacao nunca entra na atribuicao.
        if approval_status == "PREVIA_NAO_APROVADA":
            bundle_attributions.append(
                {
                    "tenantId": tenant_id,
                    "slug": slug,
                    "bundlePath": manifest.get("bundlePath"),
                    "bundleSha256": bundle_sha256,
                    "approvalStatus": approval_status,
                    "attributionStatus": ATTR_STATUS_NAO_ELEGIVEL_PREVIA,
                    "attributionReason": (
                        "Bundle com selo PREVIA_NAO_APROVADA: so e elegivel para "
                        "atribuicao apos aprovacao expressa do titular."
                    ),
                    "metrics": None,
                    "promotionHistory": promotion_history,
                }
            )
            summary[ATTR_STATUS_NAO_ELEGIVEL_PREVIA] += 1
            continue

        # 2. Multi-tenant isolation: tenantId do manifesto deve bater com o slot.
        matching_slots = slots_by_key.get((tenant_id, slug), [])
        if not matching_slots:
            # Nenhum slot UTM para este tenant/slug.
            if utm_report is None:
                # Sem relatorio UTM: nao podemos afirmar divergencia, apenas
                # aguardar metricas.
                status = ATTR_STATUS_AGUARDANDO_METRICAS
                reason = (
                    "Relatorio UTM nao informado: aguardando metricas para este "
                    "(tenantId, slug)."
                )
            else:
                tenant_appears = any(
                    str(s.get("tenantId") or "") == tenant_id
                    for s in utm_report.get("slots", [])
                )
                if tenant_appears:
                    status = ATTR_STATUS_AGUARDANDO_METRICAS
                    reason = (
                        "Bundle aprovado, mas ainda sem dados de UTM para este "
                        "(tenantId, slug)."
                    )
                else:
                    status = ATTR_STATUS_DIVERGENCIA_TENANT
                    reason = (
                        "TenantId do manifesto nao corresponde a nenhum tenant no "
                        "relatorio UTM."
                    )
            bundle_attributions.append(
                {
                    "tenantId": tenant_id,
                    "slug": slug,
                    "bundlePath": manifest.get("bundlePath"),
                    "bundleSha256": bundle_sha256,
                    "approvalStatus": approval_status,
                    "attributionStatus": status,
                    "attributionReason": reason,
                    "metrics": None,
                    "winnerSustained": None,
                    "promotionHistory": promotion_history,
                }
            )
            summary[status] += 1
            continue

        # 3. Reconciliado: cruza metrica do(s) slot(s) correspondente(s).
        # Agrega sessoes/conversoes de todos os slots da campanha (podem haver
        # varios canais para o mesmo slug).
        sessions = sum(float(s.get("sessions") or 0) for s in matching_slots)
        conversions = sum(float(s.get("conversions") or 0) for s in matching_slots)
        impressions = sum(float(s.get("sessions") or 0) for s in matching_slots)
        clicks = sum(float(s.get("engagedSessions") or 0) for s in matching_slots)
        ctr = _rate(clicks, impressions) if impressions else 0.0
        conversion_rate = _rate(conversions, sessions) if sessions else 0.0

        # observedUpliftPct: lift da conversao observada vs taxa de referencia
        # (uso a media do tenant como referencia quando disponivel).
        tenant_ref_rate = None
        if utm_report:
            benchmarks = (
                utm_report.get("rankings", {}).get("tenantBenchmarks", {}) or {}
            )
            by_tenant = benchmarks.get("byTenant", []) if isinstance(benchmarks, dict) else []
            for b in by_tenant:
                if str(b.get("tenantId") or "") == tenant_id:
                    tenant_ref_rate = b.get("conversionRatePct")
                    break

        observed_uplift_pct = None
        if tenant_ref_rate is not None and tenant_ref_rate:
            observed_uplift_pct = _rate(conversion_rate - tenant_ref_rate, tenant_ref_rate)

        winner_sustained = None
        if promotion_history:
            winner_sustained = _promotion_history_has_winner(promotion_history)

        bundle_attributions.append(
            {
                "tenantId": tenant_id,
                "slug": slug,
                "bundlePath": manifest.get("bundlePath"),
                "bundleSha256": bundle_sha256,
                "approvalStatus": approval_status,
                "attributionStatus": ATTR_STATUS_RECONCILIADO,
                "attributionReason": (
                    "Bundle reconciliado com relatorio UTM: metricas entregues e "
                    "atribuidas ao pacote distribuido."
                ),
                "metrics": {
                    "impressions": _to_int(impressions),
                    "clicks": _to_int(clicks),
                    "ctr": ctr,
                    "conversions": _to_int(conversions),
                    "conversionRate": conversion_rate,
                    "observedUpliftPct": observed_uplift_pct,
                    "winnerSustained": winner_sustained,
                },
                "promotionHistory": promotion_history,
                "itemsCount": len(items),
            }
        )
        summary[ATTR_STATUS_RECONCILIADO] += 1

    # Ordena por tenantId/slug para determinismo.
    bundle_attributions.sort(key=lambda b: (b["tenantId"], b["slug"]))

    out_dir = _resolve_contained(root_real, DEFAULT_OUT_DIR, "out-dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "bundle-attribution.json"
    payload = {
        "schemaVersion": 1,
        "generatedBy": "tools/utm_report_importer.py",
        "root": str(root_real),
        "bundlesDir": str(bundles_abs),
        "summary": summary,
        "bundles": bundle_attributions,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    return {
        "ok": True,
        "attributionPath": _rel(root_real, out_path),
        "bundles": bundle_attributions,
        "summary": summary,
    }


def _table(headers: list[str], rows: list[list[object]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return lines


def render_markdown(report: dict) -> str:
    totals = report["totals"]
    lines = [
        "# Relatorio executivo de performance UTM",
        "",
        f"- Fonte: `{report['metricsCsv']}` (provedor **{report['provider']}**)",
        f"- Calendario: `{report['calendarPath']}` ({report['calendarSource']})",
        f"- Hook log: {'`' + report['hookLogPath'] + '`' if report['hookLogPath'] else 'nao informado'}",
        f"- Cobertura de atribuicao: {totals['matchedRows']}/{totals['rows']} linhas "
        f"({totals['coveragePct']}%), {totals['unmatchedRows']} nao atribuida(s)",
        "- Receita financeira: **nao simulada** (nenhum campo monetario e inferido)",
        "",
        "## Totais",
        "",
        f"- Sessoes: {totals['sessions']}",
        f"- Sessoes engajadas: {totals['engagedSessions']} ({totals['engagedRatePct']}%)",
        f"- Conversoes: {totals['conversions']} (CVR {totals['conversionRatePct']}%)",
        f"- Slots casados: {totals['slotsMatched']}/{totals['slotsInCalendar']}",
        "",
        "## Ranking por canal",
        "",
    ]
    lines.extend(_table(
        ["Canal", "Sessoes", "Conversoes", "CVR", "Slots"],
        [[g["channel"], g["sessions"], g["conversions"], f"{g['conversionRatePct']}%", g["slots"]]
         for g in report["rankings"]["byChannel"]],
    ))
    lines.extend(["", "## Ranking por onda", ""])
    lines.extend(_table(
        ["Onda", "Sessoes", "Conversoes", "CVR", "Slots"],
        [[g["label"], g["sessions"], g["conversions"], f"{g['conversionRatePct']}%", g["slots"]]
         for g in report["rankings"]["byWave"]],
    ))
    lines.extend(["", "## Ranking por tenant", ""])
    lines.extend(_table(
        ["Tenant", "Sessoes", "Conversoes", "CVR", "Slots"],
        [[f"`{g['tenantId']}`", g["sessions"], g["conversions"], f"{g['conversionRatePct']}%", g["slots"]]
         for g in report["rankings"]["byTenant"]],
    ))
    lines.extend(["", "## Hook A vs Hook B", ""])
    if report["rankings"]["byHook"]:
        lines.extend(_table(
            ["Variante", "Sessoes", "Conversoes", "CVR", "Slots"],
            [[g["label"], g["sessions"], g["conversions"], f"{g['conversionRatePct']}%", g["slots"]]
             for g in report["rankings"]["byHook"]],
        ))
    else:
        lines.append("Sem `hook_variant_used` no CSV nem `--hook-log`; comparativo indisponivel.")
    lines.extend(["", "## Comparativo de hooks A x B", ""])
    comparison = report["rankings"]["hookComparison"]
    lines.append(
        f"- Limiar de amostra: {comparison['minSessions']} sessoes por comparativo "
        "(abaixo disso => `amostra_insuficiente`)"
    )
    if comparison["byCampaign"]:
        lines.extend(_table(
            ["Tenant", "Campanha", "Sessoes A", "Sessoes B", "CVR A", "CVR B",
             "Lift conversao", "Lift engajamento", "Classificacao"],
            [[f"`{row['tenantId']}`", f"`{row['campaign']}`", row["sessionsA"], row["sessionsB"],
              f"{row['conversionRateA']}%", f"{row['conversionRateB']}%",
              ("n/d" if row["liftConversionPct"] is None else f"{row['liftConversionPct']}%"),
              ("n/d" if row["liftEngagementPct"] is None else f"{row['liftEngagementPct']}%"),
              f"`{row['classification']}`"]
             for row in comparison["byCampaign"]],
        ))
    else:
        lines.append("Sem sessoes com variante de hook; comparativo A/B indisponivel.")
    if comparison["byTenant"]:
        lines.extend(["", "### Comparativo por tenant", ""])
        lines.extend(_table(
            ["Tenant", "Campanhas", "Sessoes A", "Sessoes B", "CVR A", "CVR B", "Lift", "Classificacao"],
            [[f"`{row['tenantId']}`", row["campaigns"], row["sessionsA"], row["sessionsB"],
              f"{row['conversionRateA']}%", f"{row['conversionRateB']}%",
              ("n/d" if row["liftConversionPct"] is None else f"{row['liftConversionPct']}%"),
              f"`{row['classification']}`"]
             for row in comparison["byTenant"]],
        ))
    lines.extend(["", "## Trafego nao atribuido", ""])
    if report["unmatchedRows"]:
        lines.extend(_table(
            ["source", "medium", "campaign", "content", "sessoes", "conversoes"],
            [[row["source"] or "(vazio)", row["medium"] or "(vazio)", row["campaign"] or "(vazio)",
              row["content"] or "(vazio)", _to_int(row["sessions"]), _to_int(row["conversions"])]
             for row in report["unmatchedRows"][:20]],
        ))
        if len(report["unmatchedRows"]) > 20:
            lines.append(f"\n_… e mais {len(report['unmatchedRows']) - 20} linha(s)._")
    else:
        lines.append("Nenhuma linha nao atribuida.")
    lines.extend(["", "## Qualidade de dados", ""])
    quality = report["dataQuality"]
    lines.append(f"- Linhas invalidas ignoradas: {len(quality['invalidRows'])}")
    lines.append(f"- Linhas casadas sem variante de hook: {quality['rowsWithoutHookVariant']}")
    lines.append(f"- Chaves duplicadas no calendario: {len(quality['duplicateCalendarKeys'])}")
    lines.append("")
    lines.append("Consulte `docs/analytics-utm-playbook.md` para a rotina semanal.")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------
def generate_template(root: str = ".", output: str = "utm-metrics-template.csv") -> dict:
    root_real = _root_real(root)
    matrix_path = _resolve_contained(root_real, MATRIZ_REL, "matriz")
    if not matrix_path.is_file():
        raise UtmReportError(f"MATRIZ_AUSENTE: {MATRIZ_REL}")
    out_abs = _resolve_contained(root_real, output, "template-saida")
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    with matrix_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if not fieldnames:
        raise UtmReportError("MATRIZ_INVALIDA: CSV sem cabecalho")
    for column in TEMPLATE_EXTRA_COLUMNS:
        if column not in fieldnames:
            fieldnames.append(column)
    with out_abs.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            for column in TEMPLATE_EXTRA_COLUMNS:
                row.setdefault(column, "")
            writer.writerow(row)
    return {
        "ok": True,
        "templatePath": _rel(root_real, out_abs),
        "rows": len(rows),
        "columns": fieldnames,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _stdout_utf8() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


def _print_human(report: dict) -> None:
    totals = report["totals"]
    print(
        f"Relatorio UTM ({report['provider']}): {totals['matchedRows']}/{totals['rows']} linhas casadas, "
        f"{totals['sessions']} sessoes, {totals['conversions']} conversoes "
        f"(CVR {totals['conversionRatePct']}%)"
    )
    for group in report["rankings"]["byChannel"]:
        print(
            f"  - {group['channel']}: {group['sessions']} sessoes, {group['conversions']} conversoes "
            f"(CVR {group['conversionRatePct']}%)"
        )
    print(f"  Nao atribuidas: {totals['unmatchedRows']} linha(s)")
    print(f"Relatorios: {report['reports']['json']} | {report['reports']['markdown']}")


def main(argv: list[str] | None = None) -> int:
    _stdout_utf8()
    parser = argparse.ArgumentParser(
        description="Importador e analisador de performance UTM (GA4, Plausible, Umami)"
    )
    parser.add_argument("--root", default=".", help="Raiz do checkout")
    parser.add_argument("--metrics-csv", default=None, help="CSV exportado do provedor")
    parser.add_argument(
        "--provider", choices=PROVIDERS, default="auto", help="Formato de entrada (padrao: auto)"
    )
    parser.add_argument("--hook-log", default=None, help="JSON com a variante de hook publicada")
    parser.add_argument(
        "--calendar", default=None, help=f"Calendario editorial (padrao: {CALENDAR_REL})"
    )
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Diretorio dos relatorios")
    parser.add_argument(
        "--min-hook-sessions",
        type=int,
        default=DEFAULT_MIN_SESSIONS,
        help=f"Limiar de sessoes do comparativo A/B (padrao {DEFAULT_MIN_SESSIONS})",
    )
    parser.add_argument(
        "--min-hook-conversions",
        type=int,
        default=DEFAULT_MIN_CONVERSIONS,
        help=f"Limiar de conversoes por variante no comparativo A/B (padrao {DEFAULT_MIN_CONVERSIONS})",
    )
    parser.add_argument(
        "--generate-template", default=None, help="Gera CSV modelo preenchivel neste caminho"
    )
    parser.add_argument(
        "--reconcile-bundles",
        action="store_true",
        default=False,
        help="Executa a reconciliacao bundle -> UTM (atribuicao de pacotes entregues)",
    )
    parser.add_argument(
        "--bundles-dir",
        default=None,
        help=f"Diretorio de bundles (padrao: <root>/{BUNDLES_REL})",
    )
    parser.add_argument(
        "--utm-report",
        default=None,
        help="Caminho do relatorio UTM JSON (padrao: <root>/.workspace/tmp/utm-report/utm-performance-report.json)",
    )
    parser.add_argument("--json", action="store_true", help="Emite JSON no stdout")
    args = parser.parse_args(argv)

    try:
        if args.generate_template:
            result = generate_template(args.root, args.generate_template)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"Template gerado: {result['templatePath']} ({result['rows']} linha(s))")
            return 0

        if args.reconcile_bundles:
            utm_report = None
            utm_path = args.utm_report
            if utm_path is None:
                # Descobre o relatorio UTM: primeiro o default, depois busca
                # recursiva em .workspace/tmp/ para relatorios gerados por
                # --generate-template ou analyze_performance.
                default_path = _resolve_contained(
                    _root_real(args.root), DEFAULT_OUT_DIR, "out-dir"
                ) / REPORT_JSON
                if os.path.isfile(default_path):
                    utm_path = str(default_path)
                else:
                    tmp_root = _root_real(args.root) / ".workspace" / "tmp"
                    found = None
                    if tmp_root.is_dir():
                        for cand in tmp_root.rglob("*.json"):
                            name = cand.name.lower()
                            if "utm" in name and cand.is_file():
                                found = str(cand)
                                break
                    utm_path = found
            if utm_path and os.path.isfile(utm_path):
                utm_report = _read_json(Path(utm_path))
            result = reconcile_bundles(
                root=args.root,
                utm_report=utm_report,
                bundles_dir=args.bundles_dir,
            )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                summary = result["summary"]
                print(
                    f"Reconciliacao bundle->UTM: {summary['total']} bundle(s), "
                    f"{summary['reconciliado']} reconciliado(s), "
                    f"{summary['aguardando_metricas']} aguardando metricas, "
                    f"{summary['divergencia_tenant']} divergencia(s) de tenant, "
                    f"{summary['nao_elegivel_para_PREVIA_NAO_APROVADA']} nao elegivel(is) para PREVIA."
                )
                print(f"Saida: {result['attributionPath']}")
            return 0

        if not args.metrics_csv:
            raise UtmReportError("USO_INVALIDO: informe --metrics-csv ou --generate-template")
        report = analyze_performance(
            root=args.root,
            metrics_csv=args.metrics_csv,
            provider=args.provider,
            hook_log=args.hook_log,
            calendar=args.calendar,
            out_dir=args.out_dir,
            min_sessions=args.min_hook_sessions,
            min_conversions=args.min_hook_conversions,
        )
    except (UtmReportError, OSError, ValueError) as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Erro: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_human(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())