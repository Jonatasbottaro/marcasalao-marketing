"""Auditor e simulador de funil UTM da fabrica multi-tenant (Etapa 5B - Agente 4).

Le `04-legendas/calendario-editorial.json` e audita 100% das URLs UTM dos slots
publicaveis. Para tenants/campanhas ainda nao agendados, deriva a URL padrao a
partir de `tenants/<tenantId>/brand-kit.json` (domain/utmDefaults) e do slug da
campanha, registrando a origem como `derived`.

Regras auditadas por URL:
  - esquema HTTPS e host igual ao `domain` do brand-kit do tenant;
  - `utm_source`, `utm_medium`, `utm_campaign` e `utm_content` presentes;
  - valores em minusculas e no alfabeto [a-z0-9._-], sem espacos/acentos;
  - `utm_campaign` igual ao slug da campanha;
  - ausencia de colisao de atribuicao entre tenants (mesma campanha ou mesmo
    par campanha+conteudo apontando para mais de um tenant).

Com `--simulate-traffic`, gera sessoes sinteticas deterministicas (seed fixa)
das duas ondas (Reels, Shorts, Feed 1:1 e Video 16:9), valida o catalogo de
eventos de conversao recomendado por nicho e grava `utm_sessions_sample.json`
e `utm_attribution_summary.md` em `--out-dir`. Nenhuma cobranca financeira e
simulada: todo campo monetario permanece nulo.

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import render_local

CALENDAR_REL = "04-legendas/calendario-editorial.json"
DEFAULT_OUT_DIR = ".workspace/tmp/utm-sim"
REQUIRED_PARAMS = ("utm_source", "utm_medium", "utm_campaign", "utm_content")
VALUE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
KNOWN_SOURCES = ("instagram", "youtube", "facebook", "tiktok", "linktree", "whatsapp", "email")
CHANNEL_MEDIA = {
    "instagram": ("reels", "feed", "stories", "bio"),
    "youtube": ("shorts", "video"),
    "facebook": ("reels", "feed", "stories"),
}
WAVE2_CONTENT = {"1:1": "repurpose-1x1", "16:9": "repurpose-16x9"}

# Catalogo de eventos de conversao recomendado por nicho. `clinica-vital` e um
# nicho planejado (novo tenant em onboarding) e por isso aparece no catalogo
# mesmo sem campanha agendada no calendario atual.
RECOMMENDED_EVENTS = {
    "marca-salao": (
        "schedule_view",
        "booking_link_click",
        "booking_started",
    ),
    "meu-salao": (
        "agenda_view",
        "attendance_checkin",
        "booking_completed",
    ),
    "estudio-flow": (
        "class_schedule_view",
        "trial_class_request",
    ),
    "multitrack-hub": (
        "rateio_view",
        "rateio_download",
        "stems_download",
    ),
    "clinica-vital": (
        "appointment_slot_view",
        "appointment_booked",
    ),
}
GENERIC_EVENTS = ("page_view", "cta_click")
NICHE_LABELS = {
    "marca-salao": "Salao de beleza (agenda online)",
    "meu-salao": "Salao de beleza (gestao de atendimentos)",
    "estudio-flow": "Estudio de pilates / bem-estar",
    "multitrack-hub": "Catalogo de multitracks e rateios",
    "clinica-vital": "Clinica de saude (agendamento)",
}


class UtmSimulatorError(Exception):
    """Erro controlado do auditor/simulador (raiz, calendario ou caminho)."""


def _contained(root_real: str, path: str) -> bool:
    return render_local.contained(root_real, os.path.realpath(path))


def _resolve(root_real: str, value: str, label: str) -> str:
    candidate = (
        os.path.realpath(value)
        if os.path.isabs(value)
        else os.path.realpath(os.path.join(root_real, *value.replace("\\", "/").split("/")))
    )
    if not _contained(root_real, candidate):
        raise UtmSimulatorError(f"PATH_OUTSIDE_ROOT: {label} fora da raiz ({value})")
    return candidate


def _load_json(path: str) -> dict:
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("conteudo JSON nao e um objeto")
    return data


def _problem(severity: str, code: str, message: str) -> dict:
    return {"severity": severity, "code": code, "message": message}


def _has_error(problems: list[dict]) -> bool:
    return any(problem["severity"] == "error" for problem in problems)


def load_tenant_kits(root_real: str) -> dict[str, dict]:
    """Le `tenants/*/brand-kit.json` diretamente (so o necessario para UTM)."""
    kits: dict[str, dict] = {}
    tenants_fs = render_local.fs_path(os.path.join(root_real, "tenants"))
    if not os.path.isdir(tenants_fs):
        return kits
    for tenant_id in sorted(os.listdir(tenants_fs)):
        kit_path = os.path.join(tenants_fs, tenant_id, "brand-kit.json")
        if not os.path.isfile(render_local.fs_path(kit_path)):
            continue
        try:
            kit = _load_json(kit_path)
        except (OSError, ValueError):
            continue
        kits[tenant_id] = kit
    return kits


def discover_tenant_campaigns(root_real: str, tenant_id: str) -> list[str]:
    campaigns_fs = render_local.fs_path(
        os.path.join(root_real, "tenants", tenant_id, "campaigns")
    )
    if not os.path.isdir(campaigns_fs):
        return []
    slugs: list[str] = []
    for name in sorted(os.listdir(campaigns_fs)):
        if not name.endswith(".json"):
            continue
        try:
            cfg = _load_json(os.path.join(campaigns_fs, name))
        except (OSError, ValueError):
            continue
        slugs.append(str(cfg.get("id") or name[: -len(".json")]))
    return slugs


def _expected_domain(kit: dict) -> str:
    domain = str(kit.get("domain") or "").strip().lower().rstrip(".")
    if not domain:
        return ""
    return domain


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
) -> dict:
    """Audita uma URL UTM isolada e devolve o resultado com problemas."""
    problems: list[dict] = []
    expected = _expected_domain(kit)
    params: dict[str, str] = {}

    if not expected:
        problems.append(
            _problem("error", "TENANT_SEM_DOMINIO", f"{tenant_id}: brand-kit sem domain")
        )

    if not isinstance(url, str) or not url.strip():
        problems.append(_problem("error", "UTM_URL_AUSENTE", f"{tenant_id}/{slug}: sem utmUrl"))
        return {
            "tenantId": tenant_id,
            "slug": slug,
            "origin": origin,
            "url": url or "",
            "domain": expected,
            "utmParams": params,
            "ok": False,
            "problems": problems,
        }

    split = urlsplit(url)
    host = (split.hostname or "").strip().lower().rstrip(".")
    host_no_www = host[4:] if host.startswith("www.") else host

    if split.scheme != "https":
        problems.append(
            _problem("error", "ESQUEMA_NAO_HTTPS", f"{tenant_id}/{slug}: esquema '{split.scheme}'")
        )
    if not host:
        problems.append(_problem("error", "URL_SEM_HOST", f"{tenant_id}/{slug}: URL sem host"))
    elif expected and host_no_www != expected:
        problems.append(
            _problem(
                "error",
                "DOMINIO_DIVERGENTE",
                f"{tenant_id}/{slug}: host '{host}' difere do domain '{expected}'",
            )
        )

    pairs = parse_qsl(split.query, keep_blank_values=True)
    seen: set[str] = set()
    for key, value in pairs:
        if key in seen:
            problems.append(
                _problem("error", "UTM_PARAM_DUPLICADO", f"{tenant_id}/{slug}: '{key}' repetido")
            )
        elif key in REQUIRED_PARAMS:
            seen.add(key)
        if key in REQUIRED_PARAMS:
            params[key] = value

    for name in REQUIRED_PARAMS:
        value = params.get(name)
        if value is None or value.strip() == "":
            problems.append(
                _problem("error", "UTM_PARAM_AUSENTE", f"{tenant_id}/{slug}: falta {name}")
            )
            continue
        if not VALUE_PATTERN.match(value):
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

    source = params.get("utm_source")
    medium = params.get("utm_medium")
    if source and source not in KNOWN_SOURCES:
        problems.append(
            _problem(
                "warning",
                "UTM_SOURCE_DESCONHECIDO",
                f"{tenant_id}/{slug}: utm_source '{source}' fora do vocabulario",
            )
        )
    if source in CHANNEL_MEDIA and medium and medium not in CHANNEL_MEDIA[source]:
        problems.append(
            _problem(
                "warning",
                "UTM_CANAL_DIVERGENTE",
                f"{tenant_id}/{slug}: {source}/{medium} nao e par canal/midia esperado",
            )
        )

    return {
        "tenantId": tenant_id,
        "slug": slug,
        "origin": origin,
        "url": url,
        "domain": expected,
        "utmParams": params,
        "ok": not _has_error(problems),
        "problems": problems,
    }


def _build_entries(
    root_real: str, calendar: dict | None, kits: dict[str, dict]
) -> tuple[list[dict], list[dict], list[dict]]:
    """Monta as entradas auditaveis (calendar + derivadas) e problemas globais."""
    entries: list[dict] = []
    calendar_slugs: set[str] = set()
    global_problems: list[dict] = []
    skipped: set[str] = set()

    if isinstance(calendar, dict):
        for slot in calendar.get("slots", []) or []:
            if not isinstance(slot, dict):
                continue
            tenant_id = str(slot.get("tenantId") or "")
            slug = str(slot.get("slug") or "")
            calendar_slugs.add(slug)
            kit = kits.get(tenant_id)
            if kit is None:
                skipped.add(tenant_id)
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
                )
            )

    for tenant_id, kit in kits.items():
        defaults = kit.get("utmDefaults") or {}
        for slug in discover_tenant_campaigns(root_real, tenant_id):
            if slug in calendar_slugs:
                continue
            params = {
                "utm_source": str(defaults.get("utm_source") or "instagram"),
                "utm_medium": str(defaults.get("utm_medium") or "reels"),
                "utm_campaign": slug,
                "utm_content": tenant_id,
            }
            url = (
                _canonical_url(_expected_domain(kit), params)
                if _expected_domain(kit)
                else ""
            )
            entries.append(audit_url(url, tenant_id, slug, kit, origin="derived"))

    return entries, global_problems, sorted(skipped)


def _detect_collisions(entries: list[dict]) -> list[dict]:
    by_campaign: dict[str, set[str]] = {}
    by_pair: dict[tuple[str, str], set[str]] = {}
    for entry in entries:
        params = entry.get("utmParams") or {}
        campaign = params.get("utm_campaign")
        content = params.get("utm_content")
        tenant_id = entry["tenantId"]
        if campaign:
            by_campaign.setdefault(campaign, set()).add(tenant_id)
        if campaign and content:
            by_pair.setdefault((campaign, content), set()).add(tenant_id)

    collisions: list[dict] = []
    for campaign, tenants in sorted(by_campaign.items()):
        if len(tenants) > 1:
            collisions.append(
                _problem(
                    "error",
                    "COLISAO_CAMPANHA_ENTRE_TENANTS",
                    f"utm_campaign '{campaign}' usado por {', '.join(sorted(tenants))}",
                )
            )
    for (campaign, content), tenants in sorted(by_pair.items()):
        if len(tenants) > 1:
            collisions.append(
                _problem(
                    "error",
                    "COLISAO_ATRIBUICAO",
                    f"par {campaign}+{content} usado por {', '.join(sorted(tenants))}",
                )
            )
    return collisions


def _simulate(entries: list[dict], seed: int) -> dict:
    """Gera sessoes sinteticas deterministicas para as duas ondas."""
    sessions: list[dict] = []
    per_channel_seed = {"reels": 18, "shorts": 14, "feed": 10, "video": 8, "bio": 5, "stories": 6}
    cvr = {
        ("instagram", "reels"): 0.12,
        ("youtube", "shorts"): 0.08,
        ("facebook", "reels"): 0.05,
        ("instagram", "feed"): 0.10,
        ("youtube", "video"): 0.06,
    }
    counter = 0
    for entry in entries:
        params = entry.get("utmParams") or {}
        if not params:
            continue
        source = params.get("utm_source", "")
        medium = params.get("utm_medium", "")
        tenant_id = entry["tenantId"]
        digest = hashlib.sha256(f"{seed}:{entry['slug']}:{source}:{medium}:{entry['url']}".encode("utf-8"))
        rng = random.Random(int.from_bytes(digest.digest()[:8], "big"))
        total = per_channel_seed.get(medium, 8)
        events = RECOMMENDED_EVENTS.get(tenant_id) or GENERIC_EVENTS
        rate = cvr.get((source, medium), 0.07)
        for _ in range(total):
            counter += 1
            converted = rng.random() < rate
            sessions.append(
                {
                    "sessionId": f"sess-{counter:05d}",
                    "wave": "onda-2" if params.get("utm_content", "").startswith("repurpose-") else "onda-1",
                    "slot": f"{entry['tenantId']}/{entry['slug']}",
                    "tenantId": tenant_id,
                    "origin": entry["origin"],
                    "utm_source": source,
                    "utm_medium": medium,
                    "utm_campaign": params.get("utm_campaign", ""),
                    "utm_content": params.get("utm_content", ""),
                    "landingUrl": entry["url"],
                    "device": "mobile" if rng.random() < 0.86 else "desktop",
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
            {"sessions": 0, "conversions": 0, "events": {}, "channels": {}},
        )
        niche["sessions"] += 1
        channel = f"{session['utm_source']}/{session['utm_medium']}"
        niche["channels"][channel] = niche["channels"].get(channel, 0) + 1
        if session["converted"]:
            niche["conversions"] += 1
            event = session["conversionEvent"]
            niche["events"][event] = niche["events"].get(event, 0) + 1

    for niche in by_niche.values():
        niche["cvr"] = round(niche["conversions"] / niche["sessions"], 4) if niche["sessions"] else 0.0

    tenants_seen = sorted(by_niche)
    recommended = {tid: list(events) for tid, events in RECOMMENDED_EVENTS.items()}
    validation_problems: list[dict] = []
    for tid in tenants_seen:
        if tid not in RECOMMENDED_EVENTS:
            validation_problems.append(
                _problem(
                    "warning",
                    "EVENTOS_RECOMENDADOS_AUSENTES",
                    f"{tid}: sem catalogo de eventos; usando fallback generico",
                )
            )
    for tid in tenants_seen:
        niche = by_niche[tid]
        used = set(niche["events"])
        allowed = set(RECOMMENDED_EVENTS.get(tid) or GENERIC_EVENTS)
        if used - allowed:
            validation_problems.append(
                _problem(
                    "error",
                    "EVENTO_FORA_DO_CATALOGO",
                    f"{tid}: eventos {sorted(used - allowed)} fora do catalogo",
                )
            )
    for tid in tenants_seen:
        by_niche[tid]["recommendedEvents"] = recommended.get(tid, list(GENERIC_EVENTS))

    return {
        "sessions": sessions,
        "byNiche": by_niche,
        "recommendedEvents": recommended,
        "problems": validation_problems,
        "totals": {
            "sessions": len(sessions),
            "conversions": sum(1 for s in sessions if s["converted"]),
            "tenants": len(by_niche),
            "waves": {
                "onda-1": sum(1 for s in sessions if s["wave"] == "onda-1"),
                "onda-2": sum(1 for s in sessions if s["wave"] == "onda-2"),
            },
            "footprints": sorted({f"{s['utm_source']}/{s['utm_medium']}" for s in sessions}),
        },
    }


def _render_summary_md(simulation: dict, seed: int) -> str:
    lines = [
        "# Resumo sintetico de atribuicao UTM",
        "",
        "Gerado por `tools/utm_simulator.py --simulate-traffic`.",
        "",
        f"- Seed deterministica: `{seed}`",
        "- Cobranca financeira simulada: **nao** (todos os `revenueBRL` sao nulos).",
        "- Dados sinteticos: nao representam trafego real e nao substituem analytics.",
        "",
        "## Totais",
        "",
        f"- Sessoes: {simulation['totals']['sessions']}",
        f"- Conversoes: {simulation['totals']['conversions']}",
        f"- Ondas: {simulation['totals']['waves']}",
        f"- Pegadas canal/midia: {', '.join(simulation['totals']['footprints'])}",
        "",
        "## Por nicho",
        "",
        "| Tenant | Nicho | Sessoes | Conversoes | CVR | Eventos observados |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for tenant_id in sorted(simulation["byNiche"]):
        niche = simulation["byNiche"][tenant_id]
        events = ", ".join(f"{k} ({v})" for k, v in sorted(niche["events"].items())) or "-"
        lines.append(
            f"| `{tenant_id}` | {NICHE_LABELS.get(tenant_id, 'nicho nao catalogado')} | "
            f"{niche['sessions']} | {niche['conversions']} | {niche['cvr']:.1%} | {events} |"
        )
    lines.extend(
        [
            "",
            "## Eventos recomendados por nicho",
            "",
            "| Tenant | Eventos |",
            "| --- | --- |",
        ]
    )
    for tenant_id, events in sorted(simulation["recommendedEvents"].items()):
        lines.append(f"| `{tenant_id}` | {', '.join(f'`{e}`' for e in events)} |")
    lines.extend(
        [
            "",
            "## Como ler",
            "",
            "1. Compare a CVR sintetica com a CVR real por canal no GA4/Plausible/Umami.",
            "2. O `utm_content=repurpose-*` identifica a Onda 2 (Feed 1:1 e Video 16:9).",
            "3. Nao use estes numeros em relatorios de resultado; sao apenas prova de fio.",
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
    session_seed: int = 20261120,
) -> dict:
    """Audita 100% das URLs UTM e, opcionalmente, simula trafego sintetico."""
    root_real = os.path.realpath(root)
    if not os.path.isdir(render_local.fs_path(root_real)):
        raise UtmSimulatorError(f"RAIZ_INVALIDA: {root}")

    explicit_calendar = calendar_path is not None
    calendar_abs = _resolve(root_real, calendar_path or CALENDAR_REL, "calendar")
    calendar: dict | None = None
    calendar_found = os.path.isfile(render_local.fs_path(calendar_abs))
    if explicit_calendar and not calendar_found:
        raise UtmSimulatorError(
            f"CALENDARIO_AUSENTE: {calendar_path} nao encontrado"
        )
    if calendar_found:
        try:
            calendar = _load_json(calendar_abs)
        except (OSError, ValueError) as exc:
            raise UtmSimulatorError(f"CALENDARIO_INVALIDO: {calendar_path or CALENDAR_REL}: {exc}") from exc

    kits = load_tenant_kits(root_real)
    entries, global_problems, skipped = _build_entries(root_real, calendar, kits)
    collisions = _detect_collisions(entries)

    all_problems = list(global_problems) + collisions
    for entry in entries:
        all_problems.extend(entry["problems"])

    errors = sum(1 for p in all_problems if p["severity"] == "error")
    warnings = sum(1 for p in all_problems if p["severity"] == "warning")
    urls_ok = sum(1 for entry in entries if entry["ok"])

    tenant_summary: dict[str, dict] = {}
    for entry in entries:
        slot = tenant_summary.setdefault(
            entry["tenantId"],
            {"domain": entry["domain"], "urls": 0, "ok": 0, "errors": 0},
        )
        slot["urls"] += 1
        slot["errors"] += sum(1 for p in entry["problems"] if p["severity"] == "error")
        if entry["ok"]:
            slot["ok"] += 1

    result: dict = {
        "schemaVersion": 1,
        "generatedBy": "tools/utm_simulator.py",
        "ok": errors == 0,
        "calendarPath": render_local.rel(root_real, calendar_abs) if calendar_found else None,
        "calendarFound": calendar_found,
        "totalUrls": len(entries),
        "urlsAudited": len(entries),
        "urlsOk": urls_ok,
        "derivedUrls": sum(1 for entry in entries if entry["origin"] == "derived"),
        "tenants": tenant_summary,
        "skippedTenants": skipped,
        "slots": entries,
        "problems": all_problems,
        "collisions": collisions,
        "summary": {
            "urls": len(entries),
            "ok": urls_ok,
            "errors": errors,
            "warnings": warnings,
        },
        "simulation": None,
    }

    if simulate_traffic:
        if not entries:
            raise UtmSimulatorError("SEM_URLS: nada para simular")
        simulation = _simulate(entries, session_seed)
        out_abs = _resolve(root_real, out_dir, "out-dir")
        os.makedirs(render_local.fs_path(out_abs), exist_ok=True)
        sessions_payload = {
            "schemaVersion": 1,
            "generatedBy": "tools/utm_simulator.py",
            "seed": session_seed,
            "financialSimulation": False,
            "note": "Dados sinteticos de fio; nao representam trafego real.",
            "totals": simulation["totals"],
            "sessions": simulation["sessions"],
        }
        sessions_path = os.path.join(out_abs, "utm_sessions_sample.json")
        summary_path = os.path.join(out_abs, "utm_attribution_summary.md")
        with open(render_local.fs_path(sessions_path), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(sessions_payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        with open(render_local.fs_path(summary_path), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_render_summary_md(simulation, session_seed))
        simulation_problems = simulation["problems"]
        for problem in simulation_problems:
            if problem["severity"] == "error":
                result["ok"] = False
                errors += 1
        result["problems"].extend(simulation_problems)
        result["summary"]["errors"] = errors
        result["summary"]["warnings"] = warnings + sum(
            1 for p in simulation_problems if p["severity"] == "warning"
        )
        result["simulation"] = {
            "enabled": True,
            "outDir": render_local.rel(root_real, out_abs),
            "sessionsFile": render_local.rel(root_real, sessions_path),
            "summaryFile": render_local.rel(root_real, summary_path),
            "seed": session_seed,
            "financialSimulation": False,
            "totalSessions": simulation["totals"]["sessions"],
            "totalConversions": simulation["totals"]["conversions"],
            "totals": simulation["totals"],
            "byNiche": simulation["byNiche"],
            "recommendedEvents": simulation["recommendedEvents"],
            "problems": simulation_problems,
        }

    return result


def _stdout_utf8() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


def _print_human(result: dict) -> None:
    print(
        f"URLs UTM auditadas: {result['urlsAudited']}, ok: {result['urlsOk']}, "
        f"derivadas: {result['derivedUrls']}"
    )
    for tenant_id, info in sorted(result["tenants"].items()):
        status = "OK" if info["errors"] == 0 else "ERRO"
        print(f"  [{status}] {tenant_id} ({info['domain']}): {info['ok']}/{info['urls']} URL(s)")
    for problem in result["problems"]:
        print(f"  - [{problem['severity']}] {problem['code']}: {problem['message']}")
    simulation = result.get("simulation")
    if simulation:
        print(
            f"Simulacao: {simulation['totalSessions']} sessoes, "
            f"{simulation['totalConversions']} conversoes -> {simulation['outDir']}"
        )
    summary = result["summary"]
    print(
        f"Resultado: {'APROVADO' if result['ok'] else 'REPROVADO'} "
        f"({summary['errors']} erro(s), {summary['warnings']} aviso(s))"
    )


def main(argv: list[str] | None = None) -> int:
    _stdout_utf8()
    parser = argparse.ArgumentParser(
        description="Auditor e simulador de funil UTM da fabrica multi-tenant"
    )
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument(
        "--calendar", default=None, help=f"Caminho do calendario (padrao: {CALENDAR_REL})"
    )
    parser.add_argument(
        "--simulate-traffic", action="store_true", help="Gera sessoes sinteticas das duas ondas"
    )
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Diretorio dos relatorios")
    parser.add_argument("--seed", type=int, default=20261120, help="Seed da simulacao")
    parser.add_argument("--json", action="store_true", help="Emite JSON no stdout")
    args = parser.parse_args(argv)

    try:
        result = audit_and_simulate_utm(
            root=args.root,
            calendar_path=args.calendar,
            simulate_traffic=bool(args.simulate_traffic),
            out_dir=args.out_dir,
            session_seed=args.seed,
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