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

O comparativo A/B (`compare_hook_variants`) agrupa as linhas casadas por
`(tenantId, utm_campaign, utm_content)` e por `(tenantId, utm_campaign)`,
calculando CTR (conversoes/sessoes), sessoes qualificadas (engajadas) e taxa de
engajamento por variante. Um vencedor so e declarado quando ha amostra minima
por variante e teste z bilateral de duas proporcoes a 95% com `math.erfc`;
empates e amostras insuficientes sao sinalizados explicitamente. As
recomendacoes em `abTests.recommendations` sao insumo de revisao humana:
`autoPublish` permanece `false` e nada e alterado em producao. Operacao
integralmente offline, somente a partir de arquivos locais exportados.

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

# Comparativo A/B — limites deterministicos e sem dependencia externa.
# O teste e de duas proporcoes (conversoes/sessoes) com aproximacao normal.
MIN_SESSIONS_PER_VARIANT = 100
MIN_CONVERSIONS_PER_VARIANT = 10
Z_THRESHOLD_95 = 1.959963984540054  # z bilateral de 95% (math.erfc)
AB_SCOPES = ("campaign-content", "campaign")
AB_OUTCOMES = (
    "winner_a",
    "winner_b",
    "tie",
    "insufficient_sample",
    "single_variant",
    "no_data",
)


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
# Comparativo determinístico de hooks A/B
# ---------------------------------------------------------------------------
def _two_proportion_z(
    conversions_a: float,
    sessions_a: float,
    conversions_b: float,
    sessions_b: float,
) -> tuple[float | None, float | None]:
    """Teste z de duas proporções com `math.erfc` — sem scipy, sem rede.

    A proporção testada é `conversoes/sessoes` (CTR de conversão do link
    rastreado). A biblioteca padrão `math.erfc` fornece o p-valor bilateral
    da normal, tornando o resultado reproduzível em qualquer estação.
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


def _empty_variant_bucket() -> dict:
    return {"sessions": 0.0, "qualifiedSessions": 0.0, "conversions": 0.0, "observations": 0}


def _variant_metrics(bucket: dict | None) -> dict | None:
    if bucket is None:
        return None
    sessions = float(bucket["sessions"])
    return {
        "sessions": _to_int(bucket["sessions"]),
        "qualifiedSessions": _to_int(bucket["qualifiedSessions"]),
        "conversions": _to_int(bucket["conversions"]),
        "ctrPct": _rate(bucket["conversions"], sessions),
        "engagementRatePct": _rate(bucket["qualifiedSessions"], sessions),
        "observations": int(bucket["observations"]),
    }


def _ab_outcome(
    metrics_a: dict | None,
    metrics_b: dict | None,
    min_sessions: int,
    min_conversions: int,
    z_threshold: float,
) -> tuple[str, str, str | None, float | None, float | None]:
    """Devolve (desfecho, motivo, vencedor, z, p-valor)."""
    if not metrics_a and not metrics_b:
        return "no_data", "Nenhuma observação com variante A ou B identificada.", None, None, None
    if not metrics_a or not metrics_b:
        present = "A" if metrics_a else "B"
        return (
            "single_variant",
            f"Apenas a variante {present} foi observada neste escopo; compare somente quando A e B existirem.",
            None,
            None,
            None,
        )
    too_small = (
        float(metrics_a["sessions"]) < min_sessions
        or float(metrics_b["sessions"]) < min_sessions
        or float(metrics_a["conversions"]) < min_conversions
        or float(metrics_b["conversions"]) < min_conversions
    )
    if too_small:
        return (
            "insufficient_sample",
            f"Amostra insuficiente: mínimo de {min_sessions} sessões e {min_conversions} "
            f"conversões por variante (A={metrics_a['sessions']}/{metrics_a['conversions']}, "
            f"B={metrics_b['sessions']}/{metrics_b['conversions']}).",
            None,
            None,
            None,
        )
    z, p_value = _two_proportion_z(
        float(metrics_a["conversions"]),
        float(metrics_a["sessions"]),
        float(metrics_b["conversions"]),
        float(metrics_b["sessions"]),
    )
    ctr_a = float(metrics_a["ctrPct"])
    ctr_b = float(metrics_b["ctrPct"])
    if z is None or p_value is None:
        return "insufficient_sample", "Sem sessões suficientes para o teste z.", None, None, None
    if ctr_a == ctr_b:
        return "tie", f"CTR idêntico ({ctr_a:.2f}%) entre A e B; não há vencedor.", None, z, p_value
    if abs(z) >= z_threshold and p_value < 0.05:
        winner = "A" if ctr_a > ctr_b else "B"
        higher, lower = (ctr_a, ctr_b) if winner == "A" else (ctr_b, ctr_a)
        reason = (
            f"Diferença estatisticamente consistente: CTR {higher:.2f}% vs {lower:.2f}% "
            f"(z={z}, p={p_value}, 95% de confiança)."
        )
        return f"winner_{winner.lower()}", reason, winner, z, p_value
    return (
        "tie",
        f"Diferença observada (A {ctr_a:.2f}% vs B {ctr_b:.2f}%) não atinge 95% de confiança "
        f"(z={z}, p={p_value}); manter o teste.",
        None,
        z,
        p_value,
    )


def _ab_recommendation(comparison: dict) -> dict:
    """Recomendação acionável, sempre sujeita a revisão humana."""
    winner = comparison["winner"]
    outcome = comparison["outcome"]
    scope = comparison["scope"]
    if outcome == "winner_a" or outcome == "winner_b":
        action = f"priorizar_hook_{winner}"
        text = (
            f"Priorizar o Hook {winner} nos próximos slots de "
            f"`{comparison['utmCampaign']}` / `{comparison['utmContent']}` "
            f"(tenant `{comparison['tenantId']}`). {comparison['reason']}"
        )
    elif outcome == "tie":
        action = "manter_teste_ab"
        text = f"Manter o teste A/B em `{comparison['utmCampaign']}`; {comparison['reason']}"
    elif outcome == "insufficient_sample":
        action = "acumular_amostra"
        text = f"Não declarar vencedor em `{comparison['utmCampaign']}`. {comparison['reason']}"
    elif outcome == "single_variant":
        action = "universalizar_variante_observada"
        text = f"Sem comparação válida em `{comparison['utmCampaign']}`. {comparison['reason']}"
    else:
        action = "sem_dados"
        text = f"Sem dados de hook em `{comparison['utmCampaign']}`. {comparison['reason']}"
    return {
        "scope": scope,
        "tenantId": comparison["tenantId"],
        "utmCampaign": comparison["utmCampaign"],
        "utmContent": comparison["utmContent"],
        "outcome": outcome,
        "winner": winner,
        "action": action,
        "text": text,
        "requiresHumanReview": True,
        "autoPublish": False,
    }


def compare_hook_variants(
    observations: list[dict],
    min_sessions: int = MIN_SESSIONS_PER_VARIANT,
    min_conversions: int = MIN_CONVERSIONS_PER_VARIANT,
    z_threshold: float = Z_THRESHOLD_95,
) -> dict:
    """Compara hooks A/B por `utm_content` e por `utm_campaign`, de forma pura.

    `observations` é uma lista de ditos com `tenantId`, `utmCampaign`,
    `utmContent`, `variant` (``A``/``B``), `sessions`, `engagedSessions` e
    `conversions`. Nenhuma chamada de rede, nenhum efeito colateral e nenhuma
    inferência financeira.
    """
    grouped: dict[tuple[str, tuple[str, str, str], str], dict] = defaultdict(dict)
    for obs in observations:
        variant = obs.get("variant")
        if variant not in ("A", "B"):
            continue
        tenant = str(obs.get("tenantId") or "")
        campaign = str(obs.get("utmCampaign") or "")
        content = str(obs.get("utmContent") or "")
        sessions = float(obs.get("sessions") or 0.0)
        engaged = float(obs.get("engagedSessions") or 0.0)
        conversions = float(obs.get("conversions") or 0.0)
        keys = (
            ("campaign-content", (tenant, campaign, content)),
            ("campaign", (tenant, campaign, "*")),
        )
        for scope, key in keys:
            bucket = grouped[(scope, key)].setdefault(variant, _empty_variant_bucket())
            bucket["sessions"] += sessions
            bucket["qualifiedSessions"] += engaged
            bucket["conversions"] += conversions
            bucket["observations"] += 1

    comparisons: list[dict] = []
    for (scope, key), buckets in sorted(
        grouped.items(), key=lambda item: (item[0][0], item[0][1])
    ):
        tenant, campaign, content = key
        metrics_a = _variant_metrics(buckets.get("A"))
        metrics_b = _variant_metrics(buckets.get("B"))
        outcome, reason, winner, z, p_value = _ab_outcome(
            metrics_a, metrics_b, min_sessions, min_conversions, z_threshold
        )
        ctr_a = float(metrics_a["ctrPct"]) if metrics_a else 0.0
        ctr_b = float(metrics_b["ctrPct"]) if metrics_b else 0.0
        comparison = {
            "scope": scope,
            "tenantId": tenant,
            "utmCampaign": campaign,
            "utmContent": content,
            "variantA": metrics_a,
            "variantB": metrics_b,
            "outcome": outcome,
            "winner": winner,
            "reason": reason,
            "absoluteDiffPct": round(ctr_b - ctr_a, 2),
            "relativeDiffPct": round((ctr_b - ctr_a) / ctr_a * 100, 2) if ctr_a else None,
            "zScore": z,
            "pValue": p_value,
            "confidencePct": 95.0 if p_value is not None else None,
            "requiresHumanReview": True,
            "autoPublish": False,
        }
        comparisons.append(comparison)

    summary = {outcome: 0 for outcome in AB_OUTCOMES}
    for comparison in comparisons:
        summary[comparison["outcome"]] += 1
    return {
        "method": "two_proportion_z_test_normal_approximation",
        "metricsDefinitions": {
            "ctrPct": "conversions / sessions * 100 (taxa de clique-through para o evento de conversão; exports não trazem impressões)",
            "qualifiedSessions": "sessões engajadas (engagedSessions), usadas como sessões qualificadas",
            "engagementRatePct": "qualifiedSessions / sessions * 100",
        },
        "thresholds": {
            "minSessionsPerVariant": min_sessions,
            "minConversionsPerVariant": min_conversions,
            "zThreshold95": z_threshold,
            "alpha": 0.05,
        },
        "scopes": list(AB_SCOPES),
        "comparisons": comparisons,
        "recommendations": [_ab_recommendation(item) for item in comparisons],
        "summary": summary,
        "networkCalls": 0,
        "financialSimulation": False,
    }


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


def analyze_performance(
    root: str = ".",
    metrics_csv: str | None = None,
    provider: str = "auto",
    hook_log: str | None = None,
    calendar: str | None = None,
    out_dir: str = DEFAULT_OUT_DIR,
) -> dict:
    """Ingere o CSV, cruza com o calendario e grava o relatorio executivo."""
    if not metrics_csv:
        raise UtmReportError("USO_INVALIDO: informe --metrics-csv ou --generate-template")
    root_real = _root_real(root)
    calendar_data = load_calendar(root_real, calendar)
    hooks = load_hook_log(root_real, hook_log)
    metrics = load_metrics(root_real, metrics_csv, provider)

    slot_totals: dict[str, dict] = {}
    unmatched: list[dict] = []
    observations: list[dict] = []
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
        if variant in ("A", "B"):
            observations.append({
                "tenantId": slot["tenantId"],
                "utmCampaign": row["campaign"],
                "utmContent": row["content"],
                "variant": variant,
                "sessions": row["sessions"],
                "engagedSessions": row["engagedSessions"],
                "conversions": row["conversions"],
            })

    ab_tests = compare_hook_variants(observations)
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
    for slot in calendar_data["slots"]:
        by_tenant.setdefault(
            slot["tenantId"], _empty_group("tenantId", slot["tenantId"])
        )
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
        _finalize_group(group)
    for group in by_channel.values():
        _finalize_group(group)
    for group in by_wave.values():
        _finalize_group(group)
    for group in by_hook.values():
        _finalize_group(group)

    hook_rows = [by_hook[key] for key in sorted(by_hook)]
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
        },
        "abTests": ab_tests,
        "recommendations": ab_tests["recommendations"],
        "slots": slot_results,
        "unmatchedRows": unmatched,
        "dataQuality": data_quality,
        "offlineOnly": True,
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

    ab_tests = report.get("abTests") or {}
    comparisons = ab_tests.get("comparisons") or []
    lines.extend(["", "## Comparativo A/B e recomendacoes (revisao humana)", ""])
    if comparisons:
        lines.append(
            "> CTR = conversoes/sessoes (nao ha impressoes nos exports); "
            "sessoes qualificadas = sessoes engajadas; vencedor exige minimo de "
            f"{ab_tests.get('thresholds', {}).get('minSessionsPerVariant', MIN_SESSIONS_PER_VARIANT)} "
            "sessoes e "
            f"{ab_tests.get('thresholds', {}).get('minConversionsPerVariant', MIN_CONVERSIONS_PER_VARIANT)} "
            "conversoes por variante e teste z bilateral a 95%."
        )
        lines.append("")
        lines.extend(_table(
            ["Escopo", "Tenant", "Campaign / content", "CTR A", "CTR B", "Qualif. A", "Qualif. B", "Desfecho", "Vencedor", "p-valor"],
            [[
                item["scope"],
                f"`{item['tenantId']}`",
                f"`{item['utmCampaign']}` / `{item['utmContent']}`",
                f"{(item['variantA'] or {}).get('ctrPct', '-')}%",
                f"{(item['variantB'] or {}).get('ctrPct', '-')}%",
                (item["variantA"] or {}).get("qualifiedSessions", "-"),
                (item["variantB"] or {}).get("qualifiedSessions", "-"),
                item["outcome"],
                item["winner"] or "-",
                item["pValue"] if item["pValue"] is not None else "-",
            ] for item in comparisons],
        ))
        lines.extend(["", "### Acões sugeridas (nao aplicadas automaticamente)", ""])
        for rec in ab_tests.get("recommendations", []):
            lines.append(f"- **{rec['action']}** — {rec['text']}")
    else:
        lines.append(
            "Sem observacoes A/B apos o cruzamento UTM; nenhuma recomendacao de hook gerada."
        )
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
    ab_summary = (report.get("abTests") or {}).get("summary") or {}
    if ab_summary:
        print(
            "  A/B: "
            f"{ab_summary.get('winner_a', 0)} vitoria(s) A, "
            f"{ab_summary.get('winner_b', 0)} vitoria(s) B, "
            f"{ab_summary.get('tie', 0)} empate(s), "
            f"{ab_summary.get('insufficient_sample', 0)} amostra(s) insuficiente(s)"
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
        "--generate-template", default=None, help="Gera CSV modelo preenchivel neste caminho"
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

        if not args.metrics_csv:
            raise UtmReportError("USO_INVALIDO: informe --metrics-csv ou --generate-template")
        report = analyze_performance(
            root=args.root,
            metrics_csv=args.metrics_csv,
            provider=args.provider,
            hook_log=args.hook_log,
            calendar=args.calendar,
            out_dir=args.out_dir,
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