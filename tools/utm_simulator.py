"""Auditor e simulador de atribuicao UTM da fabrica multi-tenant.

Etapa 5B - Agente 7 (Growth & Analytics). Implementacao 100% stdlib.

Le `04-legendas/calendario-editorial.json`, descobre os tenants em
`tenants/*/brand-kit.json` e audita 100% das URLs UTM (incluindo URLs derivadas
de campanhas de tenants ainda nao agendados). Opcionalmente gera uma simulacao
sintetica e deterministica de sessoes das duas ondas, sem qualquer transacao
financeira.

Regras auditadas:
  - esquema HTTPS e host EXATAMENTE igual ao `domain` do brand-kit do tenant;
  - presenca de `utm_source`, `utm_medium`, `utm_campaign` e `utm_content`;
  - formato limpo: minusculas, [a-z0-9._-], sem espacos e sem duplicatas;
  - `utm_campaign` igual ao slug da entrega;
  - zero colisoes da tupla de atribuicao
    (utm_source, utm_medium, utm_campaign, utm_content) entre tenants distintos.

CLI:
    python tools/utm_simulator.py [--root <raiz>] [--calendar <arquivo>]
        [--simulate-traffic] [--out-dir .workspace/tmp/utm-sim]
        [--seed <int>] [--json]

Exit codes: 0 aprovado; 1 auditoria reprovada; 2 erro de uso/caminho/execucao.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
from urllib.parse import parse_qsl, urlsplit

CALENDAR_REL = "04-legendas/calendario-editorial.json"
DEFAULT_OUT_DIR = ".workspace/tmp/utm-sim"
REQUIRED_PARAMS = ("utm_source", "utm_medium", "utm_campaign", "utm_content")
VALUE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
DEFAULT_SEED = 20261120

# Eventos recomendados por nicho (vocabulario fechado da simulacao).
RECOMMENDED_EVENTS = {
    "marca-salao": ("view_booking_page",),
    "meu-salao": ("view_booking_page",),
    "estudio-flow": ("select_service_or_class",),
    "clinica-vital": ("request_evaluation",),
    "multitrack-hub": ("inspect_multitrack_split",),
}
GENERIC_EVENTS = ("page_view",)
NICHE_LABELS = {
    "marca-salao": "SaaS de agenda para saloes",
    "meu-salao": "SaaS de agendamento e atendimentos",
    "estudio-flow": "Aulas e turmas em estudio (pilates/bem-estar)",
    "clinica-vital": "Nicho regulado de saude (consultas e avaliacoes)",
    "multitrack-hub": "Catalogo de multitracks, stems e rateios",
}
FORMAT_BY_MEDIUM = {
    "reels": "9:16",
    "shorts": "9:16",
    "stories": "9:16",
    "bio": "9:16",
    "feed": "1:1",
    "video": "16:9",
}


class UtmSimulatorError(Exception):
    """Erro controlado (raiz, calendario, caminho ou simulacao)."""


def _problem(severity: str, code: str, message: str) -> dict:
    return {"severity": severity, "code": code, "message": message}


def _has_error(problems: list[dict]) -> bool:
    return any(item["severity"] == "error" for item in problems)


def _root_real(root: str) -> str:
    path = os.path.realpath(root)
    if not os.path.isdir(path):
        raise UtmSimulatorError(f"RAIZ_INVALIDA: {root}")
    return path


def _contained(root_real: str, path: str) -> bool:
    try:
        return os.path.commonpath([root_real, os.path.realpath(path)]) == root_real
    except ValueError:
        return False


def _resolve(root_real: str, value: str, label: str) -> str:
    candidate = os.path.realpath(value if os.path.isabs(value) else os.path.join(root_real, value))
    if not _contained(root_real, candidate):
        raise UtmSimulatorError(f"PATH_OUTSIDE_ROOT: {label} fora da raiz ({value})")
    return candidate


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("conteudo JSON nao e um objeto")
    return payload


def _rel(root_real: str, path: str) -> str:
    return os.path.relpath(path, root_real).replace(os.sep, "/")


def discover_tenants(root_real: str) -> dict[str, dict]:
    """Descobre tenants diretamente em `tenants/*/brand-kit.json`."""
    kits: dict[str, dict] = {}
    tenants_dir = os.path.join(root_real, "tenants")
    if not os.path.isdir(tenants_dir):
        return kits
    for tenant_id in sorted(os.listdir(tenants_dir)):
        kit_path = os.path.join(tenants_dir, tenant_id, "brand-kit.json")
        if not os.path.isfile(kit_path):
            continue
        try:
            kits[tenant_id] = _read_json(kit_path)
        except (OSError, ValueError):
            continue
    return kits


def discover_campaign_slugs(root_real: str, tenant_id: str) -> list[str]:
    """Slugs das campanhas locais de um tenant (para cobertura de nao agendados)."""
    campaigns_dir = os.path.join(root_real, "tenants", tenant_id, "campaigns")
    if not os.path.isdir(campaigns_dir):
        return []
    slugs: list[str] = []
    for name in sorted(os.listdir(campaigns_dir)):
        if not name.endswith(".json"):
            continue
        try:
            payload = _read_json(os.path.join(campaigns_dir, name))
        except (OSError, ValueError):
            continue
        slugs.append(str(payload.get("id") or name[: -len(".json")]))
    return slugs


def _expected_domain(kit: dict) -> str:
    return str(kit.get("domain") or "").strip().lower().rstrip(".")


def _canonical_url(domain: str, params: dict[str, str]) -> str:
    return (
        f"https://{domain}/?utm_source={params['utm_source']}"
        f"&utm_medium={params['utm_medium']}"
        f"&utm_campaign={params['utm_campaign']}"
        f"&utm_content={params['utm_content']}"
    )


def audit_url(
    url: str,
    tenant_id: str,
    slug: str,
    kit: dict,
    origin: str = "calendar",
    slot_id: str = "",
    formato_video: str = "",
    canal: str = "",
) -> dict:
    """Audita uma URL UTM isolada e devolve o resultado estruturado."""
    problems: list[dict] = []
    expected = _expected_domain(kit)
    params: dict[str, str] = {}

    if not expected:
        problems.append(_problem("error", "TENANT_SEM_DOMINIO", f"{tenant_id}: brand-kit sem domain"))

    if not isinstance(url, str) or not url.strip():
        problems.append(_problem("error", "UTM_URL_AUSENTE", f"{tenant_id}/{slug}: sem utmUrl"))
        return {
            "slotId": slot_id,
            "tenantId": tenant_id,
            "slug": slug,
            "origin": origin,
            "canal": canal,
            "formatoVideo": formato_video,
            "url": url or "",
            "domain": expected,
            "utmParams": params,
            "ok": False,
            "problems": problems,
        }

    split = urlsplit(url)
    host = (split.hostname or "").strip().lower().rstrip(".")

    if split.scheme != "https":
        problems.append(
            _problem("error", "ESQUEMA_NAO_HTTPS", f"{tenant_id}/{slug}: esquema '{split.scheme}'")
        )
    if not host:
        problems.append(_problem("error", "URL_SEM_HOST", f"{tenant_id}/{slug}: URL sem host"))
    elif expected and host != expected:
        problems.append(
            _problem(
                "error",
                "DOMINIO_DIVERGENTE",
                f"{tenant_id}/{slug}: host '{host}' difere do domain exato '{expected}'",
            )
        )

    seen: set[str] = set()
    for key, value in parse_qsl(split.query, keep_blank_values=True):
        if key in REQUIRED_PARAMS:
            if key in seen:
                problems.append(
                    _problem("error", "UTM_PARAM_DUPLICADO", f"{tenant_id}/{slug}: '{key}' repetido")
                )
            seen.add(key)
            params[key] = value

    for name in REQUIRED_PARAMS:
        value = params.get(name)
        if value is None or value.strip() == "":
            problems.append(_problem("error", "UTM_PARAM_AUSENTE", f"{tenant_id}/{slug}: falta {name}"))
        elif not VALUE_PATTERN.match(value):
            problems.append(
                _problem(
                    "error",
                    "UTM_VALOR_NAO_PADRONIZADO",
                    f"{tenant_id}/{slug}: {name}='{value}' fora de [a-z0-9._-]",
                )
            )

    campaign = params.get("utm_campaign")
    if campaign and campaign != slug:
        problems.append(
            _problem(
                "error",
                "UTM_CAMPANHA_DIVERGENTE",
                f"{tenant_id}/{slug}: utm_campaign '{campaign}' difere do slug",
            )
        )

    return {
        "slotId": slot_id,
        "tenantId": tenant_id,
        "slug": slug,
        "origin": origin,
        "canal": canal,
        "formatoVideo": formato_video,
        "url": url,
        "domain": expected,
        "utmParams": params,
        "ok": not _has_error(problems),
        "problems": problems,
    }


def _build_entries(root_real: str, calendar: dict | None, kits: dict[str, dict]) -> tuple[list[dict], list[dict], list[str]]:
    """Monta entradas do calendario + derivadas e problemas globais."""
    entries: list[dict] = []
    global_problems: list[dict] = []
    scheduled_slugs: set[str] = set()
    scheduled_tenants: set[str] = set()

    for slot in (calendar or {}).get("slots", []) or []:
        if not isinstance(slot, dict):
            continue
        tenant_id = str(slot.get("tenantId") or "")
        slug = str(slot.get("slug") or "")
        scheduled_slugs.add(slug)
        scheduled_tenants.add(tenant_id)
        kit = kits.get(tenant_id)
        if kit is None:
            global_problems.append(
                _problem(
                    "error",
                    "TENANT_DESCONHECIDO",
                    f"{slot.get('slotId', '?')}: tenant '{tenant_id}' sem brand-kit",
                )
            )
            continue
        entries.append(
            audit_url(
                str(slot.get("utmUrl") or ""),
                tenant_id,
                slug,
                kit,
                origin="calendar",
                slot_id=str(slot.get("slotId") or ""),
                formato_video=str(slot.get("formatoVideo") or ""),
                canal=str(slot.get("canal") or ""),
            )
        )

    # Cobertura de tenants/campanhas descobertos em tenants/* e ainda nao agendados.
    for tenant_id, kit in kits.items():
        defaults = kit.get("utmDefaults") or {}
        for slug in discover_campaign_slugs(root_real, tenant_id):
            if slug in scheduled_slugs:
                continue
            params = {
                "utm_source": str(defaults.get("utm_source") or "instagram"),
                "utm_medium": str(defaults.get("utm_medium") or "reels"),
                "utm_campaign": slug,
                "utm_content": tenant_id,
            }
            domain = _expected_domain(kit)
            entries.append(
                audit_url(
                    _canonical_url(domain, params) if domain else "",
                    tenant_id,
                    slug,
                    kit,
                    origin="derived",
                )
            )

    unscheduled = sorted(set(kits) - scheduled_tenants)
    return entries, global_problems, unscheduled


def detect_collisions(entries: list[dict]) -> list[dict]:
    """Colisao de atribuicao: mesma tupla de 4 UTMs em tenants distintos."""
    owners: dict[tuple[str, ...], set[str]] = {}
    for entry in entries:
        params = entry.get("utmParams") or {}
        if not all(name in params for name in REQUIRED_PARAMS):
            continue
        key = tuple(params[name] for name in REQUIRED_PARAMS)
        owners.setdefault(key, set()).add(entry["tenantId"])

    collisions: list[dict] = []
    for key, tenants in sorted(owners.items()):
        if len(tenants) > 1:
            collisions.append(
                _problem(
                    "error",
                    "COLISAO_ATRIBUICAO",
                    "tupla " + "/".join(key) + " usada por " + ", ".join(sorted(tenants)),
                )
            )
    return collisions


def _simulate(entries: list[dict], seed: int) -> dict:
    """Sessoes sinteticas deterministicas das duas ondas, sem receita/transacao."""
    sessions: list[dict] = []
    sessions_per_entry = {"reels": 6, "shorts": 5, "feed": 4, "video": 4}
    conversion_rate = {
        ("instagram", "reels"): 0.12,
        ("youtube", "shorts"): 0.09,
        ("facebook", "reels"): 0.06,
        ("instagram", "feed"): 0.10,
        ("youtube", "video"): 0.07,
    }

    for entry in entries:
        params = entry.get("utmParams") or {}
        if not all(name in params for name in REQUIRED_PARAMS):
            continue
        source = params["utm_source"]
        medium = params["utm_medium"]
        tenant_id = entry["tenantId"]
        slug = entry["slug"]
        fingerprint = "|".join(
            [str(seed), str(entry.get("slotId", "")), tenant_id, slug, source, medium,
             params["utm_campaign"], params["utm_content"], entry.get("url", "")]
        )
        digest = hashlib.sha256(fingerprint.encode("utf-8")).digest()
        rng = random.Random(int.from_bytes(digest[:8], "big"))
        wave = "onda-2" if params["utm_content"].startswith("repurpose-") else "onda-1"
        formato = entry.get("formatoVideo") or FORMAT_BY_MEDIUM.get(medium, "9:16")
        total = sessions_per_entry.get(medium, 4)
        events = RECOMMENDED_EVENTS.get(tenant_id) or GENERIC_EVENTS
        rate = conversion_rate.get((source, medium), 0.08)

        for _ in range(total):
            converted = rng.random() < rate
            sessions.append(
                {
                    "sessionId": f"sess-{len(sessions) + 1:05d}",
                    "wave": wave,
                    "slotId": entry.get("slotId", ""),
                    "tenantId": tenant_id,
                    "origin": entry.get("origin", ""),
                    "canal": f"{source}/{medium}",
                    "formatoVideo": formato,
                    "utm_source": source,
                    "utm_medium": medium,
                    "utm_campaign": params["utm_campaign"],
                    "utm_content": params["utm_content"],
                    "landingUrl": entry.get("url", ""),
                    "device": "mobile" if rng.random() < 0.85 else "desktop",
                    "country": "BR",
                    "pageViews": rng.randint(1, 4),
                    "converted": converted,
                    "conversionEvent": rng.choice(events) if converted else None,
                    "revenueBRL": None,
                }
            )

    by_niche: dict[str, dict] = {}
    for session in sessions:
        niche = by_niche.setdefault(
            session["tenantId"],
            {
                "tenantId": session["tenantId"],
                "niche": NICHE_LABELS.get(session["tenantId"], "nicho nao catalogado"),
                "sessions": 0,
                "conversions": 0,
                "events": {},
                "waves": {},
                "formats": {},
                "recommendedEvents": list(
                    RECOMMENDED_EVENTS.get(session["tenantId"]) or GENERIC_EVENTS
                ),
            },
        )
        niche["sessions"] += 1
        niche["waves"][session["wave"]] = niche["waves"].get(session["wave"], 0) + 1
        niche["formats"][session["formatoVideo"]] = niche["formats"].get(session["formatoVideo"], 0) + 1
        if session["converted"]:
            niche["conversions"] += 1
            event = session["conversionEvent"]
            niche["events"][event] = niche["events"].get(event, 0) + 1

    for niche in by_niche.values():
        niche["cvr"] = (
            round(niche["conversions"] / niche["sessions"], 4) if niche["sessions"] else 0.0
        )

    problems: list[dict] = []
    for tenant_id, niche in by_niche.items():
        allowed = set(niche["recommendedEvents"])
        unexpected = set(niche["events"]) - allowed
        if unexpected:
            problems.append(
                _problem(
                    "error",
                    "EVENTO_FORA_DO_CATALOGO",
                    f"{tenant_id}: {sorted(unexpected)} fora do catalogo",
                )
            )
    if not any(s["revenueBRL"] is None for s in sessions) and sessions:
        problems.append(
            _problem("error", "TRANSACAO_FINANCEIRA_SIMULADA", "campo revenueBRL preenchido")
        )

    formats = sorted({s["formatoVideo"] for s in sessions})
    waves = {wave: sum(1 for s in sessions if s["wave"] == wave) for wave in ("onda-1", "onda-2")}
    return {
        "sessions": sessions,
        "byNiche": by_niche,
        "recommendedEvents": {k: list(v) for k, v in RECOMMENDED_EVENTS.items()},
        "problems": problems,
        "totals": {
            "sessions": len(sessions),
            "conversions": sum(1 for s in sessions if s["converted"]),
            "tenants": len(by_niche),
            "waves": waves,
            "formats": formats,
            "financialSimulation": False,
        },
    }


def _render_summary(simulation: dict, seed: int, out_dir_rel: str) -> str:
    totals = simulation["totals"]
    lines = [
        "# Resumo sintetico de atribuicao UTM",
        "",
        "Gerado por `tools/utm_simulator.py --simulate-traffic` (Etapa 5B, Agente 7).",
        "",
        f"- Seed deterministica: `{seed}`",
        f"- Diretorio de saida: `{out_dir_rel}`",
        "- Transacoes financeiras simuladas: **nao** (todo `revenueBRL` e nulo).",
        "- Dados sinteticos: nao representam trafego real nem substituem analytics.",
        "",
        "## Totais",
        "",
        f"- Sessoes: {totals['sessions']}",
        f"- Conversoes: {totals['conversions']}",
        f"- Ondas: onda-1 = {totals['waves']['onda-1']}, onda-2 = {totals['waves']['onda-2']}",
        f"- Formatos: {', '.join(totals['formats'])} (Reels, Shorts, Feed 1:1, Video 16:9)",
        "",
        "## Por nicho",
        "",
        "| Tenant | Nicho | Sessoes | Conversoes | CVR | Eventos observados |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for tenant_id in sorted(simulation["byNiche"]):
        niche = simulation["byNiche"][tenant_id]
        events = ", ".join(f"`{k}` ({v})" for k, v in sorted(niche["events"].items())) or "-"
        lines.append(
            f"| `{tenant_id}` | {niche['niche']} | {niche['sessions']} | "
            f"{niche['conversions']} | {niche['cvr']:.1%} | {events} |"
        )
    lines.extend(
        [
            "",
            "## Eventos recomendados por nicho",
            "",
            "| Tenant | Evento recomendado |",
            "| --- | --- |",
        ]
    )
    for tenant_id, events in sorted(simulation["recommendedEvents"].items()):
        lines.append(f"| `{tenant_id}` | {', '.join(f'`{event}`' for event in events)} |")
    lines.extend(
        [
            "",
            "## Como ler",
            "",
            "1. Compare a CVR sintetica com a CVR real por canal no GA4, Plausible ou Umami.",
            "2. `utm_content=repurpose-1x1` e `repurpose-16x9` identificam a Onda 2.",
            "3. Nao use estes numeros em relatorio de resultado: sao apenas prova de fio.",
            "4. Consulte `docs/analytics-utm-playbook.md` para configurar os eventos reais.",
            "",
        ]
    )
    return "\n".join(lines)


def audit_and_simulate_utm(
    root: str = ".",
    calendar_path: str | None = None,
    simulate_traffic: bool = False,
    out_dir: str = DEFAULT_OUT_DIR,
    seed: int = DEFAULT_SEED,
) -> dict:
    """Audita 100% das URLs UTM e, opcionalmente, simula trafego sintetico."""
    root_real = _root_real(root)

    explicit = calendar_path is not None
    calendar_abs = _resolve(root_real, calendar_path or CALENDAR_REL, "calendar")
    calendar: dict | None = None
    found = os.path.isfile(calendar_abs)
    if explicit and not found:
        raise UtmSimulatorError(f"CALENDARIO_AUSENTE: {calendar_path} nao encontrado")
    if found:
        try:
            calendar = _read_json(calendar_abs)
        except (OSError, ValueError) as exc:
            raise UtmSimulatorError(f"CALENDARIO_INVALIDO: {calendar_path or CALENDAR_REL}: {exc}") from exc

    kits = discover_tenants(root_real)
    entries, global_problems, unscheduled = _build_entries(root_real, calendar, kits)
    collisions = detect_collisions(entries)

    all_problems = list(global_problems) + list(collisions)
    for entry in entries:
        all_problems.extend(entry["problems"])

    errors = sum(1 for item in all_problems if item["severity"] == "error")
    warnings = sum(1 for item in all_problems if item["severity"] == "warning")
    urls_ok = sum(1 for entry in entries if entry["ok"])

    tenant_summary: dict[str, dict] = {}
    for entry in entries:
        info = tenant_summary.setdefault(
            entry["tenantId"],
            {
                "domain": entry["domain"],
                "brandName": str((kits.get(entry["tenantId"]) or {}).get("brandName") or ""),
                "urls": 0,
                "ok": 0,
                "errors": 0,
                "onCalendar": False,
            },
        )
        info["urls"] += 1
        info["errors"] += sum(1 for p in entry["problems"] if p["severity"] == "error")
        info["onCalendar"] = info["onCalendar"] or entry["origin"] == "calendar"
        if entry["ok"]:
            info["ok"] += 1
    for tenant_id in kits:
        tenant_summary.setdefault(
            tenant_id,
            {
                "domain": _expected_domain(kits[tenant_id]),
                "brandName": str(kits[tenant_id].get("brandName") or ""),
                "urls": 0,
                "ok": 0,
                "errors": 0,
                "onCalendar": False,
            },
        )

    result: dict = {
        "schemaVersion": 1,
        "generatedBy": "tools/utm_simulator.py (Etapa 5B - Agente 7)",
        "ok": errors == 0,
        "root": root_real,
        "calendarFound": found,
        "calendarPath": _rel(root_real, calendar_abs) if found else None,
        "totalUrls": len(entries),
        "urlsAudited": len(entries),
        "urlsOk": urls_ok,
        "derivedUrls": sum(1 for entry in entries if entry["origin"] == "derived"),
        "tenants": tenant_summary,
        "unscheduledTenants": unscheduled,
        "slots": entries,
        "collisions": collisions,
        "problems": all_problems,
        "summary": {"urls": len(entries), "ok": urls_ok, "errors": errors, "warnings": warnings},
        "simulation": None,
    }

    if simulate_traffic:
        if not entries:
            raise UtmSimulatorError("SEM_URLS: nada para simular")
        simulation = _simulate(entries, seed)
        out_abs = _resolve(root_real, out_dir, "out-dir")
        os.makedirs(out_abs, exist_ok=True)
        out_rel = _rel(root_real, out_abs)
        sessions_payload = {
            "schemaVersion": 1,
            "generatedBy": "tools/utm_simulator.py (Etapa 5B - Agente 7)",
            "seed": seed,
            "financialSimulation": False,
            "note": "Dados sinteticos de prova de fio; nao representam trafego real.",
            "totals": simulation["totals"],
            "sessions": simulation["sessions"],
        }
        sessions_path = os.path.join(out_abs, "utm_sessions_sample.json")
        summary_path = os.path.join(out_abs, "utm_attribution_summary.md")
        with open(sessions_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(sessions_payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        with open(summary_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_render_summary(simulation, seed, out_rel))

        for problem in simulation["problems"]:
            if problem["severity"] == "error":
                result["ok"] = False
                errors += 1
        result["problems"].extend(simulation["problems"])
        result["summary"]["errors"] = errors
        result["summary"]["warnings"] = warnings + sum(
            1 for p in simulation["problems"] if p["severity"] == "warning"
        )
        result["simulation"] = {
            "enabled": True,
            "outDir": out_rel,
            "sessionsFile": _rel(root_real, sessions_path),
            "summaryFile": _rel(root_real, summary_path),
            "seed": seed,
            "financialSimulation": False,
            "totalSessions": simulation["totals"]["sessions"],
            "totalConversions": simulation["totals"]["conversions"],
            "totals": simulation["totals"],
            "byNiche": simulation["byNiche"],
            "recommendedEvents": simulation["recommendedEvents"],
            "problems": simulation["problems"],
        }

    return result


def _stdout_utf8() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


def _print_human(result: dict) -> None:
    print(
        f"URLs UTM auditadas: {result['urlsAudited']} | ok: {result['urlsOk']} | "
        f"derivadas: {result['derivedUrls']} | colisoes: {len(result['collisions'])}"
    )
    for tenant_id, info in sorted(result["tenants"].items()):
        status = "OK" if info["errors"] == 0 else "ERRO"
        agenda = "agendado" if info["onCalendar"] else "nao agendado"
        print(
            f"  [{status}] {tenant_id} ({info['domain']}, {agenda}): "
            f"{info['ok']}/{info['urls']} URL(s)"
        )
    if result["unscheduledTenants"]:
        print("  Tenants descobertos sem slots no calendario: " + ", ".join(result["unscheduledTenants"]))
    for problem in result["problems"]:
        print(f"  - [{problem['severity']}] {problem['code']}: {problem['message']}")
    simulation = result.get("simulation")
    if simulation:
        print(
            f"Simulacao: {simulation['totalSessions']} sessoes, "
            f"{simulation['totalConversions']} conversoes, seed {simulation['seed']} "
            f"-> {simulation['outDir']}"
        )
    summary = result["summary"]
    print(
        f"Resultado: {'APROVADO' if result['ok'] else 'REPROVADO'} "
        f"({summary['errors']} erro(s), {summary['warnings']} aviso(s))"
    )


def main(argv: list[str] | None = None) -> int:
    _stdout_utf8()
    parser = argparse.ArgumentParser(
        description="Auditor e simulador de atribuicao UTM (Etapa 5B - Agente 7)"
    )
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument("--calendar", default=None, help=f"Calendario (padrao: {CALENDAR_REL})")
    parser.add_argument("--simulate-traffic", action="store_true", help="Gerar sessoes sinteticas")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Diretorio dos relatorios")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Seed deterministica")
    parser.add_argument("--json", action="store_true", help="Emitir JSON no stdout")
    args = parser.parse_args(argv)

    try:
        result = audit_and_simulate_utm(
            root=args.root,
            calendar_path=args.calendar,
            simulate_traffic=bool(args.simulate_traffic),
            out_dir=args.out_dir,
            seed=args.seed,
        )
    except (UtmSimulatorError, OSError, ValueError) as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Erro: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
