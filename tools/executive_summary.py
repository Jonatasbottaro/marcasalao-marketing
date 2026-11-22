"""Relatorio executivo semanal por tenant da fabrica multi-tenant (Etapa 13).

Consolida, para UM tenant por vez, o estado editorial, a inteligencia A/B, a
fadiga criativa, as entregas empacotadas e a atribuicao pos-publicacao, e
devolve um plano de acao recomendatorio para o titular.

Princípios:

  * **Somente leitura.** Nenhuma aprovacao, data de calendario, canal, UTM ou
    midia e alterada. O selo ``autoPublish: false`` aparece no JSON e no
    Markdown. Nada e publicado nem agendado.
  * **Isolamento estrito por tenant.** Cada relatorio usa apenas campanhas,
    slots, benchmarks, bundles e historico do proprio ``tenant_id``.
  * **Sem formulas duplicadas.** Os numeros vem das ferramentas canonicas:
    ``editorial_qa`` (lentes), ``approval_cli`` (decisoes e promotionHistory),
    ``campaign_calendar`` (registro de campanhas e calendario),
    ``utm_report_importer`` (teste z, fadiga, tenantBenchmarks, atribuicao) e
    ``publish_bundler`` (gate SHA-256 dos pacotes).
  * **Ausencia de dados e explicita.** Sem relatorio UTM ou sem bundles nesta
    estacao, as secoes declaram ``sem dados`` com o motivo, em vez de inventar
    metricas ou recalcular estatistica por conta propria.

Artefatos gerados em ``.workspace/reports/<tenant_id>/`` (nunca versionados):
    relatorio-executivo-<tenant_id>.json
    relatorio-executivo-<tenant_id>.md

CLI:
    python tools/executive_summary.py (--tenant <id> | --all) [--week 1..7]
        [--output-dir DIR] [--utm-report CAMINHO] [--bundle-attribution CAMINHO]
        [--json] [--root DIR]

API:
    build_tenant_summary(root, tenant_id, week=None, ...) -> dict
    render_markdown(summary) -> str
    generate_reports(root=".", tenant=None, all_tenants=False, week=None, ...) -> dict

Exit codes: 0 relatorios gerados; 1 falha controlada; 2 erro de uso.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import approval_cli  # noqa: E402
import campaign_calendar  # noqa: E402
import editorial_qa  # noqa: E402
import publish_bundler  # noqa: E402
import render_local  # noqa: E402
import review_dashboard  # noqa: E402
import utm_report_importer as utm  # noqa: E402

SCHEMA_VERSION = 1
GENERATED_BY = "tools/executive_summary.py"
DEFAULT_OUTPUT_DIR = os.path.join(".workspace", "reports")
REPORT_PREFIX = "relatorio-executivo-"
AUTO_PUBLISH = False
WEEK_MIN = 1
WEEK_MAX = 7
DECISIONS = ("aprovado", "aguardando", "ajuste")
AB_CLASSES = ("vencedor_A", "vencedor_B", "empate_tecnico", "amostra_insuficiente")
FATIGUE_DETECTED = "fadiga_detectada"
NO_DATA = "sem dados"


class ExecutiveSummaryError(Exception):
    """Erro controlado de uso ou de entrada (tenant inexistente, semana invalida)."""


def _load_json(path: str) -> dict | None:
    try:
        with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _workspace(root_real: str) -> str:
    return review_dashboard.resolve_workspace_dir(root_real)


def _resolve_input(root_real: str, provided: str | None, default_rel: str) -> tuple[dict | None, str | None]:
    """Le um artefato de entrada existente; nao gera nada quando ausente."""
    rel = provided or default_rel
    path = rel if os.path.isabs(rel) else os.path.join(root_real, rel)
    if not render_local.contained(root_real, path):
        raise ExecutiveSummaryError(f"ENTRADA_FORA_DA_RAIZ: {rel}")
    data = _load_json(path)
    return data, (render_local.rel(root_real, path) if data is not None else None)


def collect_inputs(
    root: str = ".",
    utm_report_path: str | None = None,
    bundle_attribution_path: str | None = None,
) -> dict:
    """Carrega uma unica vez as fontes compartilhadas entre os tenants."""
    root_real = os.path.realpath(root)
    workspace = _workspace(root_real)

    utm_default = os.path.join(utm.DEFAULT_OUT_DIR, "utm-performance-report.json")
    utm_report, utm_rel = _resolve_input(root_real, utm_report_path, utm_default)
    attr_default = os.path.join(utm.DEFAULT_OUT_DIR, "bundle-attribution.json")
    attribution, attr_rel = _resolve_input(root_real, bundle_attribution_path, attr_default)

    calendar = _load_json(os.path.join(root_real, campaign_calendar.CALENDAR_JSON_REL))
    qa = editorial_qa.run_editorial_qa(root_real, strict=True)
    approvals = approval_cli.cmd_status(root_real)

    promotions: dict[tuple[str, str], list] = {}
    store_path = approval_cli.approvals_store_path(root_real)
    store = _load_json(store_path)
    if store:
        for item in store.get("campanhas") or []:
            if isinstance(item, dict) and item.get("tenantId") and item.get("slug"):
                history = item.get("promotionHistory")
                if isinstance(history, list) and history:
                    promotions[(item["tenantId"], item["slug"])] = history

    registry = campaign_calendar.discover_campaigns(root_real)
    return {
        "root": root_real,
        "workspace": workspace,
        "utmReport": utm_report,
        "utmReportPath": utm_rel,
        "attribution": attribution,
        "attributionPath": attr_rel,
        "calendar": calendar,
        "qa": qa,
        "approvals": approvals,
        "promotions": promotions,
        "registry": registry,
    }


def _tenant_campaigns(inputs: dict, tenant_id: str) -> list[dict]:
    return [c for c in inputs["registry"] if c["tenantId"] == tenant_id]


def _editorial_section(inputs: dict, tenant_id: str, campaigns: list[dict]) -> dict:
    rows = [r for r in inputs["approvals"]["campaigns"] if r["tenantId"] == tenant_id]
    by_status = {decision: 0 for decision in DECISIONS}
    for row in rows:
        if row["decision"] in by_status:
            by_status[row["decision"]] += 1

    prefix = f"{tenant_id}/"
    problems = [
        problem
        for check in inputs["qa"]["checks"]
        for problem in check["problems"]
        if problem["message"].startswith(prefix)
    ]
    errors = sum(1 for p in problems if p["severity"] == "error")
    warnings = sum(1 for p in problems if p["severity"] == "warning")
    qa_rows = [c for c in inputs["qa"]["campaigns"] if c["tenant"] == tenant_id]
    pending = [
        {"slug": r["slug"], "decision": r["decision"]}
        for r in rows
        if r["decision"] != "aprovado"
    ]
    return {
        "totalCampaigns": len(campaigns),
        "byStatus": by_status,
        "pendingApprovals": pending,
        "locucaoExternaPendente": [
            item["slug"]
            for item in inputs["approvals"]["locucaoExternaPendente"]
            if item["tenantId"] == tenant_id
        ],
        "qa": {
            "ok": errors == 0 and warnings == 0,
            "errors": errors,
            "warnings": warnings,
            "campaignsAudited": len(qa_rows),
            "campaignsWithProblems": sum(1 for c in qa_rows if not c["ok"]),
            "lenses": len(inputs["qa"]["checks"]),
            "problems": problems,
        },
    }


def _ab_section(inputs: dict, tenant_id: str, campaigns: list[dict], slots: list[dict]) -> dict:
    report = inputs["utmReport"]
    slugs = {c["slug"] for c in campaigns}
    comparison = ((report or {}).get("rankings") or {}).get("hookComparison") or {}
    rows = [
        row for row in (comparison.get("byCampaign") or [])
        if row.get("tenantId") == tenant_id and row.get("campaign") in slugs
    ]
    counts = {name: 0 for name in AB_CLASSES}
    for row in rows:
        if row.get("classification") in counts:
            counts[row["classification"]] += 1
    decided = counts["vencedor_A"] + counts["vencedor_B"] + counts["empate_tecnico"]
    wins = counts["vencedor_A"] + counts["vencedor_B"]

    benchmarks_all = ((report or {}).get("rankings") or {}).get("tenantBenchmarks") or {}
    benchmark = next(
        (b for b in (benchmarks_all.get("byTenant") or []) if b.get("tenantId") == tenant_id),
        None,
    )

    alerts: list[dict] = []
    for slot in slots:
        if slot.get("fatigueStatus") == FATIGUE_DETECTED or slot.get("fatigueDetected"):
            alerts.append({
                "slug": slot["slug"],
                "slotId": slot.get("slotId"),
                "canal": slot.get("canal"),
                "formatoVideo": slot.get("formatoVideo"),
                "semana": slot.get("semana"),
                "fatigueStatus": slot.get("fatigueStatus"),
                "zScore": slot.get("fatigueZScore"),
                "pValue": slot.get("fatiguePValue"),
                "reason": slot.get("fatigueReason"),
            })

    promotions: list[dict] = []
    for campaign in campaigns:
        history = inputs["promotions"].get((tenant_id, campaign["slug"])) or []
        for entry in history:
            promotions.append({"slug": campaign["slug"], **entry})
    promotions.sort(key=lambda e: (e.get("promotedAt") or e.get("updatedAt") or "", e["slug"]))

    by_channel: dict[str, int] = {}
    by_format: dict[str, int] = {}
    for slot in slots:
        by_channel[slot["canal"]] = by_channel.get(slot["canal"], 0) + 1
        by_format[slot["formatoVideo"]] = by_format.get(slot["formatoVideo"], 0) + 1

    return {
        "dataSource": inputs["utmReportPath"],
        "hasData": bool(rows) or benchmark is not None,
        "hookTests": {
            "total": len(rows),
            "byClassification": counts,
            "decided": decided,
            "wins": wins,
            "winRatePct": round(wins / decided * 100, 2) if decided else None,
            "byCampaign": rows,
        },
        "fatigueAlerts": alerts,
        "tenantBenchmarks": benchmark,
        "channelRanking": sorted(by_channel.items(), key=lambda kv: (-kv[1], kv[0])),
        "formatRanking": sorted(by_format.items(), key=lambda kv: (-kv[1], kv[0])),
        "promotionHistory": promotions,
    }


def _delivery_section(inputs: dict, tenant_id: str, campaigns: list[dict], slots: list[dict]) -> dict:
    root_real = inputs["root"]
    bundles_dir = os.path.join(inputs["workspace"], "bundles", tenant_id)
    packages: list[dict] = []
    if os.path.isdir(render_local.fs_path(bundles_dir)):
        for slug in sorted(os.listdir(render_local.fs_path(bundles_dir))):
            slug_dir = os.path.join(bundles_dir, slug)
            if not os.path.isdir(render_local.fs_path(slug_dir)):
                continue
            for name in sorted(os.listdir(render_local.fs_path(slug_dir))):
                if not name.endswith(".zip"):
                    continue
                path = os.path.join(slug_dir, name)
                entry = {
                    "slug": slug,
                    "bundlePath": render_local.rel(root_real, path),
                    "bundleSha256": None,
                    "verified": False,
                    "itemCount": None,
                    "problems": [],
                }
                try:
                    result = publish_bundler.verify_bundle(path, root=root_real)
                except publish_bundler.PublishBundlerError as exc:
                    entry["problems"] = [{"code": exc.code, "message": str(exc)}]
                else:
                    entry["bundleSha256"] = result.get("bundleSha256")
                    entry["verified"] = bool(result.get("ok"))
                    entry["itemCount"] = result.get("itemCount")
                    entry["problems"] = result.get("problems") or []
                packages.append(entry)

    attribution = inputs["attribution"]
    slugs = {c["slug"] for c in campaigns}
    entries = [
        item for item in ((attribution or {}).get("bundles") or [])
        if item.get("tenantId") == tenant_id and item.get("slug") in slugs
    ]
    statuses = {
        utm.ATTR_STATUS_RECONCILIADO: 0,
        utm.ATTR_STATUS_AGUARDANDO_METRICAS: 0,
        utm.ATTR_STATUS_DIVERGENCIA_TENANT: 0,
        utm.ATTR_STATUS_NAO_ELEGIVEL_PREVIA: 0,
    }
    metrics: list[dict] = []
    for item in entries:
        status = item.get("attributionStatus")
        if status in statuses:
            statuses[status] += 1
        observed = item.get("metrics") or {}
        metrics.append({
            "slug": item.get("slug"),
            "attributionStatus": status,
            "approvalStatus": item.get("approvalStatus"),
            "bundleSha256": item.get("bundleSha256"),
            "ctr": observed.get("ctr"),
            "conversionRate": observed.get("conversionRate"),
            "observedUpliftPct": observed.get("observedUpliftPct"),
            "winnerSustained": observed.get("winnerSustained", item.get("winnerSustained")),
            "reason": item.get("attributionReason"),
        })

    slot_attribution = [
        {
            "slotId": slot.get("slotId"),
            "slug": slot["slug"],
            "attributionStatus": (slot.get("bundleAttribution") or {}).get("attributionStatus"),
        }
        for slot in slots
        if isinstance(slot.get("bundleAttribution"), dict)
    ]

    return {
        "dataSource": inputs["attributionPath"],
        "hasData": bool(entries) or bool(packages),
        "bundles": packages,
        "bundlesTotal": len(packages),
        "bundlesVerified": sum(1 for p in packages if p["verified"]),
        "attribution": {
            "total": len(entries),
            "byStatus": statuses,
            "campaigns": metrics,
            "slots": slot_attribution,
        },
    }


def _action_plan(editorial: dict, ab: dict, delivery: dict) -> list[dict]:
    """Recomendacoes priorizadas; nenhuma delas e executada automaticamente."""
    actions: list[dict] = []
    if editorial["qa"]["errors"]:
        actions.append({
            "priority": 1,
            "category": "qualidade-editorial",
            "action": f"Corrigir {editorial['qa']['errors']} erro(s) do QA editorial antes de aprovar.",
            "reason": "O gate editorial strict reprova com qualquer erro.",
        })
    if editorial["pendingApprovals"]:
        slugs = ", ".join(item["slug"] for item in editorial["pendingApprovals"])
        actions.append({
            "priority": 2,
            "category": "aprovacoes",
            "action": f"Decidir {len(editorial['pendingApprovals'])} campanha(s) pendente(s): {slugs}.",
            "reason": "Sem decisao do titular o slot nao pode ser empacotado como aprovado.",
        })
    if editorial["locucaoExternaPendente"]:
        actions.append({
            "priority": 2,
            "category": "locucao-externa",
            "action": "Conferir a locucao externa de: " + ", ".join(editorial["locucaoExternaPendente"]) + ".",
            "reason": "Tenant com audio permitido exige conferencia antes da distribuicao.",
        })
    if ab["fatigueAlerts"]:
        slugs = sorted({alert["slug"] for alert in ab["fatigueAlerts"]})
        actions.append({
            "priority": 1,
            "category": "fadiga-criativa",
            "action": "Renovar o hook das campanhas com fadiga detectada: " + ", ".join(slugs) + ".",
            "reason": "Queda estatisticamente significativa entre ondas (z >= 1.96 e p < 0.05).",
        })
    if delivery["bundlesTotal"] and delivery["bundlesVerified"] < delivery["bundlesTotal"]:
        actions.append({
            "priority": 1,
            "category": "integridade-de-pacote",
            "action": "Reempacotar os bundles que reprovaram no gate SHA-256.",
            "reason": "Pacote divergente nao deve ser distribuido.",
        })
    ready = [
        item["slug"] for item in delivery["attribution"]["campaigns"]
        if item["attributionStatus"] == utm.ATTR_STATUS_RECONCILIADO
    ]
    if ready:
        actions.append({
            "priority": 3,
            "category": "distribuicao",
            "action": "Pacotes reconciliados prontos para distribuicao manual: " + ", ".join(sorted(set(ready))) + ".",
            "reason": "Atribuicao closed-loop concluida; publicacao continua manual.",
        })
    awaiting = delivery["attribution"]["byStatus"][utm.ATTR_STATUS_AGUARDANDO_METRICAS]
    if awaiting:
        actions.append({
            "priority": 3,
            "category": "metricas",
            "action": f"Importar metricas UTM de {awaiting} pacote(s) aguardando reconciliacao.",
            "reason": "Sem sessoes/conversoes o uplift observado nao pode ser calculado.",
        })
    if not ab["hasData"]:
        actions.append({
            "priority": 4,
            "category": "inteligencia-ab",
            "action": "Gerar o relatorio UTM (utm_report_importer) para habilitar teste z, fadiga e benchmarks.",
            "reason": "Sem relatorio UTM nesta estacao as secoes A/B ficam sem dados.",
        })
    if not actions:
        actions.append({
            "priority": 5,
            "category": "manutencao",
            "action": "Nenhuma acao pendente para este tenant na janela analisada.",
            "reason": "QA limpo, aprovacoes em dia e sem alerta de fadiga.",
        })
    actions.sort(key=lambda a: (a["priority"], a["category"]))
    return actions


def build_tenant_summary(
    root: str = ".",
    tenant_id: str = "",
    week: int | None = None,
    inputs: dict | None = None,
) -> dict:
    """Monta o relatorio executivo de UM tenant, sem misturar dados de outros."""
    if not tenant_id:
        raise ExecutiveSummaryError("TENANT_OBRIGATORIO: informe --tenant <id> ou --all")
    if week is not None and not (WEEK_MIN <= week <= WEEK_MAX):
        raise ExecutiveSummaryError(f"SEMANA_INVALIDA: use {WEEK_MIN}..{WEEK_MAX}")
    data = inputs if inputs is not None else collect_inputs(root)
    campaigns = _tenant_campaigns(data, tenant_id)
    if not campaigns:
        raise ExecutiveSummaryError(f"TENANT_DESCONHECIDO: {tenant_id}")

    calendar = data["calendar"] or {}
    all_slots = [s for s in (calendar.get("slots") or []) if s.get("tenantId") == tenant_id]
    slots = [s for s in all_slots if week is None or s.get("semana") == week]
    weeks = sorted({s["semana"] for s in all_slots if isinstance(s.get("semana"), int)})
    dates = sorted(s["dataSugerida"] for s in slots if s.get("dataSugerida"))

    editorial = _editorial_section(data, tenant_id, campaigns)
    ab = _ab_section(data, tenant_id, campaigns, slots)
    delivery = _delivery_section(data, tenant_id, campaigns, slots)

    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedBy": GENERATED_BY,
        "ok": True,
        "governance": {
            "tenantId": tenant_id,
            "brandName": campaigns[0]["brandName"],
            "domain": campaigns[0].get("domain"),
            "generatedAtUtc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "autoPublish": AUTO_PUBLISH,
            "statusEditorial": campaign_calendar.STATUS_EDITORIAL,
            "janela": {
                "week": week,
                "weeksAvailable": weeks,
                "startDate": dates[0] if dates else None,
                "endDate": dates[-1] if dates else None,
                "slots": len(slots),
                "slotsTotalTenant": len(all_slots),
                "calendarWeeks": calendar.get("weeks"),
            },
            "readOnly": True,
        },
        "editorial": editorial,
        "abIntelligence": ab,
        "delivery": delivery,
        "actionPlan": _action_plan(editorial, ab, delivery),
        "sources": {
            "calendar": (
                campaign_calendar.CALENDAR_JSON_REL.replace(os.sep, "/")
                if data["calendar"] else None
            ),
            "utmReport": data["utmReportPath"],
            "bundleAttribution": data["attributionPath"],
            "approvals": data["approvals"]["approvalsFile"],
        },
    }


def _fmt(value: object, suffix: str = "") -> str:
    if value is None:
        return NO_DATA
    return f"{value}{suffix}"


def render_markdown(summary: dict) -> str:
    """Markdown limpo para leitura executiva do titular."""
    gov = summary["governance"]
    ed = summary["editorial"]
    ab = summary["abIntelligence"]
    dl = summary["delivery"]
    janela = gov["janela"]
    lines: list[str] = []
    add = lines.append

    add(f"# Relatorio executivo — {gov['brandName']} (`{gov['tenantId']}`)")
    add("")
    add(f"- Gerado em (UTC): {gov['generatedAtUtc']}")
    add(f"- Dominio: {_fmt(gov.get('domain'))}")
    add(f"- **autoPublish: false** — publicacao exclusivamente manual")
    add(f"- Status editorial: `{gov['statusEditorial']}`")
    add(f"- Somente leitura: nenhuma aprovacao, data, canal ou UTM foi alterada")
    add("")
    add("## 1. Janela analisada")
    add("")
    add("| Campo | Valor |")
    add("| --- | --- |")
    week_label = str(janela["week"]) if janela["week"] is not None else "todas"
    add(f"| Semana | {week_label} |")
    add(f"| Semanas disponiveis | {', '.join(str(w) for w in janela['weeksAvailable']) or NO_DATA} |")
    add(f"| Periodo | {_fmt(janela['startDate'])} a {_fmt(janela['endDate'])} |")
    add(f"| Slots na janela | {janela['slots']} de {janela['slotsTotalTenant']} do tenant |")
    add("")
    add("## 2. Saude editorial e aprovacoes")
    add("")
    add(f"Campanhas do tenant: **{ed['totalCampaigns']}**")
    add("")
    add("| Status | Campanhas |")
    add("| --- | --- |")
    for decision in DECISIONS:
        add(f"| {decision} | {ed['byStatus'][decision]} |")
    add("")
    qa = ed["qa"]
    add(
        f"QA editorial: {'APROVADO' if qa['ok'] else 'REPROVADO'} "
        f"({qa['errors']} erros, {qa['warnings']} avisos, "
        f"{qa['campaignsAudited']} campanhas em {qa['lenses']} lentes)"
    )
    if qa["problems"]:
        add("")
        for problem in qa["problems"]:
            add(f"- `{problem['severity']}` {problem['code']}: {problem['message']}")
    if ed["pendingApprovals"]:
        add("")
        add("Aprovacoes pendentes:")
        for item in ed["pendingApprovals"]:
            add(f"- {item['slug']} — `{item['decision']}`")
    if ed["locucaoExternaPendente"]:
        add("")
        add("Locucao externa a conferir: " + ", ".join(ed["locucaoExternaPendente"]))
    add("")
    add("## 3. Inteligencia A/B e fadiga criativa")
    add("")
    if not ab["hasData"]:
        add(f"{NO_DATA}: relatorio UTM ausente nesta estacao.")
        add("")
    hooks = ab["hookTests"]
    add(f"Testes Hook A/B avaliados: **{hooks['total']}**")
    add("")
    add("| Classificacao | Campanhas |")
    add("| --- | --- |")
    for name in AB_CLASSES:
        add(f"| {name} | {hooks['byClassification'][name]} |")
    add("")
    add(f"Taxa de vitoria (A ou B sobre decididos): {_fmt(hooks['winRatePct'], '%')}")
    if hooks["byCampaign"]:
        add("")
        add("| Campanha | Classificacao | zScore | pValue |")
        add("| --- | --- | --- | --- |")
        for row in hooks["byCampaign"]:
            add(
                f"| {row['campaign']} | {row['classification']} | "
                f"{_fmt(row.get('zScore'))} | {_fmt(row.get('pValue'))} |"
            )
    add("")
    if ab["fatigueAlerts"]:
        add(f"**Alertas de fadiga ativos: {len(ab['fatigueAlerts'])}**")
        add("")
        add("| Campanha | Slot | zScore | pValue | Status |")
        add("| --- | --- | --- | --- | --- |")
        for alert in ab["fatigueAlerts"]:
            add(
                f"| {alert['slug']} | {_fmt(alert['slotId'])} | {_fmt(alert['zScore'])} | "
                f"{_fmt(alert['pValue'])} | {alert['fatigueStatus']} |"
            )
    else:
        add("Alertas de fadiga ativos: 0")
    add("")
    bench = ab["tenantBenchmarks"]
    if bench:
        add("Benchmarks do tenant (`tenantBenchmarks`):")
        add("")
        add("| Indicador | Valor |")
        add("| --- | --- |")
        for key in ("sessions", "conversions", "conversionRatePct", "engagedRatePct", "abWinRatePct", "slots"):
            if key in bench:
                add(f"| {key} | {_fmt(bench[key])} |")
        add("")
    if ab["channelRanking"]:
        add("Ranking interno de canais: " + ", ".join(f"{c} ({n})" for c, n in ab["channelRanking"]))
    if ab["formatRanking"]:
        add("Ranking interno de formatos: " + ", ".join(f"{f} ({n})" for f, n in ab["formatRanking"]))
    add("")
    if ab["promotionHistory"]:
        add(f"Promocoes auditadas (`promotionHistory`): {len(ab['promotionHistory'])}")
        add("")
        add("| Campanha | Variante | Quando | Por | zScore | pValue |")
        add("| --- | --- | --- | --- | --- | --- |")
        for entry in ab["promotionHistory"]:
            add(
                f"| {entry['slug']} | {_fmt(entry.get('promotedVariant') or entry.get('decisao'))} | "
                f"{_fmt(entry.get('promotedAt') or entry.get('updatedAt'))} | "
                f"{_fmt(entry.get('promotedBy') or entry.get('reviewer'))} | "
                f"{_fmt(entry.get('zScore'))} | {_fmt(entry.get('pValue'))} |"
            )
    else:
        add("Promocoes auditadas (`promotionHistory`): 0")
    add("")
    add("## 4. Entregas e atribuicao pos-publicacao (closed-loop)")
    add("")
    add(f"Pacotes gerados: **{dl['bundlesTotal']}** | verificados por SHA-256: **{dl['bundlesVerified']}**")
    if dl["bundles"]:
        add("")
        add("| Campanha | SHA-256 | Gate | Itens |")
        add("| --- | --- | --- | --- |")
        for package in dl["bundles"]:
            digest = (package["bundleSha256"] or NO_DATA)
            short = digest[:16] if package["bundleSha256"] else digest
            add(
                f"| {package['slug']} | `{short}` | "
                f"{'OK' if package['verified'] else 'FALHOU'} | {_fmt(package['itemCount'])} |"
            )
    add("")
    attr = dl["attribution"]
    add(f"Slots reconciliados: **{attr['total']}**")
    add("")
    add("| Status de atribuicao | Pacotes |")
    add("| --- | --- |")
    for status, count in attr["byStatus"].items():
        add(f"| {status} | {count} |")
    if attr["campaigns"]:
        add("")
        add("| Campanha | Status | CTR | Conversao | Uplift obs. | Vencedor sustentado |")
        add("| --- | --- | --- | --- | --- | --- |")
        for item in attr["campaigns"]:
            add(
                f"| {item['slug']} | {item['attributionStatus']} | {_fmt(item['ctr'], '%')} | "
                f"{_fmt(item['conversionRate'], '%')} | {_fmt(item['observedUpliftPct'], '%')} | "
                f"{_fmt(item['winnerSustained'])} |"
            )
    if not dl["hasData"]:
        add("")
        add(f"{NO_DATA}: nenhum bundle ou relatorio de atribuicao nesta estacao.")
    add("")
    add("## 5. Plano de acao priorizado (recomendatorio)")
    add("")
    add("Nenhuma acao abaixo e executada automaticamente. Todas exigem decisao do titular.")
    add("")
    for index, action in enumerate(summary["actionPlan"], start=1):
        add(f"{index}. **[P{action['priority']}] {action['category']}** — {action['action']}")
        add(f"   - Motivo: {action['reason']}")
    add("")
    add("## 6. Fontes")
    add("")
    for label, path in summary["sources"].items():
        add(f"- {label}: `{path or NO_DATA}`")
    add("")
    return "\n".join(lines)


def generate_reports(
    root: str = ".",
    tenant: str | None = None,
    all_tenants: bool = False,
    week: int | None = None,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    utm_report_path: str | None = None,
    bundle_attribution_path: str | None = None,
) -> dict:
    """Gera JSON + Markdown por tenant em ``.workspace/reports/<tenant_id>/``."""
    if bool(tenant) == bool(all_tenants):
        raise ExecutiveSummaryError("USO_INVALIDO: informe exatamente um de --tenant ou --all")
    root_real = os.path.realpath(root)
    inputs = collect_inputs(root_real, utm_report_path, bundle_attribution_path)

    available = sorted({c["tenantId"] for c in inputs["registry"]})
    targets = available if all_tenants else [tenant]
    for tid in targets:
        if tid not in available:
            raise ExecutiveSummaryError(f"TENANT_DESCONHECIDO: {tid}")

    workspace = inputs["workspace"]
    out_rel = output_dir or DEFAULT_OUTPUT_DIR
    if os.path.isabs(out_rel):
        out_abs = os.path.realpath(out_rel)
    else:
        norm = out_rel.replace("\\", "/")
        if not norm.startswith(".workspace/"):
            raise ExecutiveSummaryError(
                f"SAIDA_FORA_DO_WORKSPACE: {out_rel} precisa começar com .workspace/ (nunca versionado)"
            )
        out_abs = os.path.realpath(os.path.join(os.path.dirname(workspace), norm))
    if not render_local.contained(workspace, out_abs):
        raise ExecutiveSummaryError(
            f"SAIDA_FORA_DO_WORKSPACE: {out_rel} precisa ficar sob .workspace/ (nunca versionado)"
        )

    reports: list[dict] = []
    for tid in targets:
        summary = build_tenant_summary(root_real, tid, week=week, inputs=inputs)
        tenant_dir = os.path.join(out_abs, tid)
        os.makedirs(render_local.fs_path(tenant_dir), exist_ok=True)
        base = f"{REPORT_PREFIX}{tid}"
        json_path = os.path.join(tenant_dir, f"{base}.json")
        md_path = os.path.join(tenant_dir, f"{base}.md")
        render_local.write_text_lf(
            json_path, json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
        )
        render_local.write_text_lf(md_path, render_markdown(summary))
        reports.append({
            "tenantId": tid,
            "brandName": summary["governance"]["brandName"],
            "autoPublish": AUTO_PUBLISH,
            "campaigns": summary["editorial"]["totalCampaigns"],
            "qaOk": summary["editorial"]["qa"]["ok"],
            "fatigueAlerts": len(summary["abIntelligence"]["fatigueAlerts"]),
            "bundlesVerified": summary["delivery"]["bundlesVerified"],
            "actions": len(summary["actionPlan"]),
            "files": {
                "json": render_local.rel(root_real, json_path),
                "markdown": render_local.rel(root_real, md_path),
            },
            "summary": summary,
        })

    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedBy": GENERATED_BY,
        "ok": True,
        "autoPublish": AUTO_PUBLISH,
        "root": root_real,
        "outputDir": render_local.rel(root_real, out_abs),
        "week": week,
        "totalTenants": len(reports),
        "tenants": [r["tenantId"] for r in reports],
        "reports": reports,
    }


def _print_human(result: dict) -> None:
    print("Relatorio executivo semanal por tenant")
    print("=" * 48)
    print(f"Saida: {result['outputDir']} | semana: {_fmt(result['week'])} | autoPublish: false")
    for report in result["reports"]:
        print(
            f"  [{report['tenantId']}] {report['brandName']}: "
            f"{report['campaigns']} campanhas, QA {'OK' if report['qaOk'] else 'FALHOU'}, "
            f"{report['fatigueAlerts']} alertas de fadiga, "
            f"{report['bundlesVerified']} pacotes verificados, "
            f"{report['actions']} acoes"
        )
        print(f"      {report['files']['markdown']}")
    print("-" * 48)
    print(f"Resultado: {result['totalTenants']} relatorio(s) gerado(s), nenhuma mutacao de governanca")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Relatorio executivo semanal por tenant (100% stdlib, somente leitura)"
    )
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--tenant", default=None, help="tenant especifico")
    scope.add_argument("--all", action="store_true", help="todos os tenants ativos")
    parser.add_argument("--week", type=int, default=None, help=f"semana do calendario ({WEEK_MIN}..{WEEK_MAX})")
    parser.add_argument(
        "--output-dir", default=DEFAULT_OUTPUT_DIR,
        help="diretorio de saida; precisa começar com .workspace/ (nunca versionado)",
    )
    parser.add_argument("--utm-report", default=None, help="relatorio UTM ja gerado (JSON)")
    parser.add_argument("--bundle-attribution", default=None, help="atribuicao de bundles ja gerada (JSON)")
    parser.add_argument("--json", action="store_true", help="emite o relatorio em JSON no stdout")
    parser.add_argument("--root", default=os.getcwd(), help="raiz do checkout")
    args = parser.parse_args(argv)

    try:
        result = generate_reports(
            root=args.root,
            tenant=args.tenant,
            all_tenants=bool(args.all),
            week=args.week,
            output_dir=args.output_dir,
            utm_report_path=args.utm_report,
            bundle_attribution_path=args.bundle_attribution,
        )
    except ExecutiveSummaryError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    except (campaign_calendar.CampaignCalendarError, editorial_qa.EditorialQAError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro: entrada invalida ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())