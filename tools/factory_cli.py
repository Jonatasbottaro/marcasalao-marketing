"""Orquestrador unificado da fabrica multi-tenant de conteudo (Etapa 5B).

Descobre tenants validos em `tenants/`, lista campanhas configuradas, aciona
o motor generico (`tools/preset_runner.py`) respeitando contratos e politicas de
audio por tenant, grava pacotes de entrega padronizados em
`02-reels-shorts/deliveries/<tenantId>/<slug>/` (com copia dos .mp4 em
`.workspace/archives/<slug>/`) e gera o relatorio consolidado
`02-reels-shorts/deliveries/factory-report.json`.

O subcomando `pipeline` e o mestre end-to-end: encadeia contratos, render 9:16,
derivados multiformato, cards estaticos, pacotes sociais, calendario editorial,
portal de revisao, auditoria UTM, QA editorial e Release Gate. Modulos paralelos
(Etapas 5/5B) sao importados de forma opcional: se um deles ainda nao existir, o
estagio e marcado como `skipped` e o restante continua. Com `--skip-render`, os
estagios de producao passam a verificar os artefatos versionados existentes.

Uso (a partir da raiz do checkout):
    python tools/factory_cli.py list [--tenant <tenantId>] [--json]
    python tools/factory_cli.py render --tenant <tenantId> [--campaign <slug>] [--json]
    python tools/factory_cli.py render --all [--json]
    python tools/factory_cli.py pipeline --all [--skip-render] [--start-date YYYY-MM-DD]
        [--weeks 5] [--strict-audit] [--json]
    python tools/factory_cli.py pipeline --tenant <tenantId> [--campaign <slug>]
        [--skip-render] [--json]
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import json
import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import preset_runner
import render_local
import tenant_validator

DEFAULT_DELIVERIES_DIR = "02-reels-shorts/deliveries"
DEFAULT_REPORT_REL = "02-reels-shorts/deliveries/factory-report.json"
STATIC_CARDS_DIR = "01-insta-stories/deliveries"
PACKAGES_DIR = "04-legendas/pacotes-publicacao"
CALENDAR_REL = "04-legendas/calendario-editorial.json"
PORTAL_DIR = "05-review-portal"
PORTAL_FILES = ("index.html", "portal-data.json", "README.md")
PACKAGE_FILES = ("instagram-reels.md", "youtube-shorts.md", "facebook-reels.md")
DERIVATIVE_KEYS = ("cover", "1x1", "16x9")
DEFAULT_UTM_OUT_DIR = ".workspace/tmp/utm-sim"


class FactoryError(Exception):
    """Erro controlado do orquestrador da fabrica."""


class StageFailure(FactoryError):
    """Falha de estagio com detalhes estruturados preservados no relatorio."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


def _resolve_contained(root_real: str, path_value: str, label: str) -> str:
    candidate = (
        os.path.realpath(path_value)
        if os.path.isabs(path_value)
        else os.path.realpath(os.path.join(root_real, path_value.replace("/", os.sep)))
    )
    if not render_local.contained(root_real, candidate):
        raise FactoryError(f"PATH_OUTSIDE_ROOT: {label} fora da raiz do projeto ({path_value})")
    return candidate


def _load_json(path: str) -> dict:
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def discover_tenant_campaigns(tenant_id: str, root: str = ".") -> list[dict[str, Any]]:
    """Lista e lê os arquivos `*.json` em `tenants/<tenantId>/campaigns/`."""
    root_real = os.path.realpath(root)
    campaigns_dir = _resolve_contained(
        root_real, os.path.join("tenants", tenant_id, "campaigns"), f"campaigns:{tenant_id}"
    )
    if not os.path.isdir(render_local.fs_path(campaigns_dir)):
        return []

    found: list[dict[str, Any]] = []
    for name in sorted(os.listdir(render_local.fs_path(campaigns_dir))):
        if not name.endswith(".json"):
            continue
        abs_cfg = os.path.join(campaigns_dir, name)
        if not os.path.isfile(render_local.fs_path(abs_cfg)):
            continue
        cfg = _load_json(abs_cfg)
        cfg_tenant = cfg.get("tenantId")
        if cfg_tenant and cfg_tenant != tenant_id:
            raise FactoryError(
                f"CAMPAIGN_TENANT_MISMATCH: {render_local.rel(root_real, abs_cfg)} declara tenantId '{cfg_tenant}'"
            )
        slug = str(cfg.get("id") or os.path.splitext(name)[0])
        found.append({
            "slug": slug,
            "campaignId": str(cfg.get("campaignId") or slug),
            "preset": str(cfg.get("preset") or ""),
            "configPath": render_local.rel(root_real, abs_cfg),
            "scenesCount": len(cfg.get("scenes", [])),
            "durationSeconds": float(cfg.get("format", {}).get("duration", 0.0)),
        })
    return found


def cmd_list(root: str = ".", tenant_filter: str | None = None) -> dict[str, Any]:
    """Retorna todos os tenants descobertos, seus presets e campanhas cadastradas."""
    root_real = os.path.realpath(root)
    tenants = [tenant_filter] if tenant_filter else tenant_validator.list_tenants(root_real)

    entries: list[dict[str, Any]] = []
    all_ok = True
    total_campaigns = 0
    for tid in tenants:
        try:
            ctx = tenant_validator.load_and_validate_tenant(tid, root=root_real, strict=False)
            campaigns = discover_tenant_campaigns(tid, root=root_real)
            kit = ctx["brandKit"]
            gr = ctx["guardrails"]
            entry = {
                "tenantId": tid,
                "ok": ctx["ok"],
                "brandName": kit.get("brandName"),
                "monogram": kit.get("monogram"),
                "domain": kit.get("domain"),
                "defaultPreset": kit.get("defaultPreset"),
                "allowAudioTrack": bool(gr.get("audioPolicy", {}).get("allowAudioTrack", False)),
                "campaignsCount": len(campaigns),
                "campaigns": campaigns,
                "errors": ctx["errors"],
            }
            if not ctx["ok"]:
                all_ok = False
            total_campaigns += len(campaigns)
        except (tenant_validator.TenantContractError, FactoryError, OSError, ValueError) as exc:
            all_ok = False
            entry = {
                "tenantId": tid,
                "ok": False,
                "campaignsCount": 0,
                "campaigns": [],
                "errors": [str(exc)],
            }
        entries.append(entry)

    return {
        "schemaVersion": 1,
        "ok": all_ok,
        "totalTenants": len(entries),
        "totalCampaigns": total_campaigns,
        "tenants": entries,
    }


def _atomic_write_json(path: str, payload: dict[str, Any]) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(render_local.fs_path(parent), exist_ok=True)
    tmp_path = os.path.join(parent, f".{os.path.basename(path)}.tmp")
    with open(render_local.fs_path(tmp_path), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(render_local.fs_path(tmp_path), render_local.fs_path(path))


def cmd_render(
    root: str = ".",
    tenant_id: str | None = None,
    campaign_slug: str | None = None,
    render_all: bool = False,
    deliveries_dir: str = DEFAULT_DELIVERIES_DIR,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Valida e renderiza campanhas em lote e grava `factory-report.json`."""
    if not render_all and not tenant_id:
        raise FactoryError("USO_INVALIDO: informe --all ou --tenant <tenantId>")
    if render_all and tenant_id:
        raise FactoryError("USO_INVALIDO: nao combine --all com --tenant")
    if campaign_slug and not tenant_id:
        raise FactoryError("USO_INVALIDO: --campaign requer --tenant <tenantId>")

    root_real = os.path.realpath(root)
    render_local.ensure_video_tools(root_real)

    deliveries_abs = _resolve_contained(root_real, deliveries_dir, "deliveries-dir")
    effective_report = report_path or os.path.join(deliveries_abs, "factory-report.json")
    report_abs = _resolve_contained(root_real, effective_report, "report-path")

    target_tenants = tenant_validator.list_tenants(root_real) if render_all else [str(tenant_id)]
    if not target_tenants:
        raise FactoryError("NENHUM_TENANT: nenhum diretorio encontrado em tenants/")

    deliveries: list[dict[str, Any]] = []
    processed_tenants: list[str] = []

    for tid in target_tenants:
        ctx = tenant_validator.load_and_validate_tenant(tid, root=root_real, strict=True)
        campaigns = discover_tenant_campaigns(tid, root=root_real)
        if campaign_slug:
            campaigns = [c for c in campaigns if c["slug"] == campaign_slug]
            if not campaigns:
                raise FactoryError(f"CAMPANHA_NAO_ENCONTRADA: '{campaign_slug}' em tenants/{tid}/campaigns/")
        if not campaigns:
            raise FactoryError(f"SEM_CAMPANHAS: nenhuma campanha JSON em tenants/{tid}/campaigns/")

        processed_tenants.append(tid)
        for camp in campaigns:
            slug = camp["slug"]
            out_dir = _resolve_contained(
                root_real, os.path.join(deliveries_abs, tid, slug), f"delivery:{tid}/{slug}"
            )
            with contextlib.redirect_stdout(sys.stderr):
                manifest = preset_runner.run_preset_pipeline(
                    tid, camp["configPath"], out_dir, audio_path=None, root=root_real
                )
            arts = manifest["artifacts"]
            video_art = arts["video"]
            deliveries.append({
                "tenantId": tid,
                "brandName": ctx["brandKit"]["brandName"],
                "monogram": ctx["brandKit"]["monogram"],
                "campaignSlug": slug,
                "campaignId": camp["campaignId"],
                "preset": manifest["preset"],
                "configPath": camp["configPath"],
                "deliveryDir": render_local.rel(root_real, out_dir),
                "manifestPath": render_local.rel(root_real, os.path.join(out_dir, "manifest.json")),
                "allowAudioTrack": manifest["guardrails"]["allowAudioTrack"],
                "ffprobe": video_art["ffprobe"],
                "artifacts": {
                    "video": {
                        "path": video_art["path"],
                        "archivePath": video_art["archivePath"],
                        "sha256": video_art["sha256"],
                        "bytes": video_art["bytes"],
                    },
                    "srt": {
                        "path": arts["srt"]["path"],
                        "sha256": arts["srt"]["sha256"],
                        "bytes": arts["srt"]["bytes"],
                    },
                    "narration": {
                        "path": arts["narration"]["path"],
                        "sha256": arts["narration"]["sha256"],
                        "bytes": arts["narration"]["bytes"],
                    },
                    "storyboard": {
                        "path": arts["storyboard"]["path"],
                        "sha256": arts["storyboard"]["sha256"],
                        "bytes": arts["storyboard"]["bytes"],
                    },
                },
            })

    report = {
        "schemaVersion": 1,
        "ok": True,
        "mode": "all" if render_all else "filtered",
        "deliveriesRoot": render_local.rel(root_real, deliveries_abs),
        "totalTenants": len(processed_tenants),
        "totalCampaigns": len(deliveries),
        "tenants": processed_tenants,
        "deliveries": deliveries,
    }
    _atomic_write_json(report_abs, report)
    return report


def _optional_module(name: str):
    """Importa um modulo de etapa paralela sem quebrar o pipeline se ele faltar."""
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def _run_stage(stage_id: str, title: str, runner) -> dict[str, Any]:
    started = time.perf_counter()
    details: dict[str, Any] = {}
    error: str | None = None
    status = "ok"
    try:
        details = runner() or {}
    except StageFailure as exc:
        status = "failed"
        error = str(exc)
        details = exc.details
    except Exception as exc:  # noqa: BLE001 - o lote precisa registrar a falha e seguir
        status = "failed"
        error = f"{type(exc).__name__}: {exc}"
    return {
        "id": stage_id,
        "title": title,
        "status": status,
        "durationMs": int(round((time.perf_counter() - started) * 1000)),
        "details": details,
        "error": error,
    }


def _skipped_stage(stage_id: str, title: str, reason: str) -> dict[str, Any]:
    return {
        "id": stage_id,
        "title": title,
        "status": "skipped",
        "durationMs": 0,
        "details": {"reason": reason},
        "error": None,
    }


def _declared_hash_ok(
    root_real: str,
    rel_path: Any,
    expected: Any,
    label: str,
    failures: list[str],
) -> int:
    """Confere hash quando o arquivo declarado existe no disco local."""
    if not isinstance(rel_path, str) or not rel_path or not expected:
        failures.append(f"{label}: declaracao sem path/sha256")
        return 0
    target = _resolve_contained(root_real, rel_path, label)
    if not os.path.isfile(render_local.fs_path(target)):
        return 0
    if render_local.sha256_file(target) != expected:
        failures.append(f"{label}: sha256 divergente ({rel_path})")
    return 1


def _pipeline_targets(
    root_real: str, run_all: bool, tenant_id: str | None, campaign_slug: str | None
) -> tuple[list[str], list[dict[str, Any]]]:
    if not run_all and not tenant_id:
        raise FactoryError("USO_INVALIDO: informe --all ou --tenant <tenantId>")
    if run_all and tenant_id:
        raise FactoryError("USO_INVALIDO: nao combine --all com --tenant")
    if campaign_slug and not tenant_id:
        raise FactoryError("USO_INVALIDO: --campaign requer --tenant <tenantId>")

    tenants = tenant_validator.list_tenants(root_real) if run_all else [str(tenant_id)]
    if not tenants:
        raise FactoryError("NENHUM_TENANT: nenhum diretorio encontrado em tenants/")

    targets: list[dict[str, Any]] = []
    for tid in tenants:
        campaigns = discover_tenant_campaigns(tid, root=root_real)
        if campaign_slug:
            campaigns = [c for c in campaigns if c["slug"] == campaign_slug]
            if not campaigns:
                raise FactoryError(
                    f"CAMPANHA_NAO_ENCONTRADA: '{campaign_slug}' em tenants/{tid}/campaigns/"
                )
        if not campaigns:
            raise FactoryError(f"SEM_CAMPANHAS: nenhuma campanha JSON em tenants/{tid}/campaigns/")
        for camp in campaigns:
            targets.append({"tenantId": tid, **camp})
    return tenants, targets


def cmd_pipeline(
    root: str = ".",
    tenant_id: str | None = None,
    campaign_slug: str | None = None,
    run_all: bool = False,
    skip_render: bool = False,
    start_date: str | None = None,
    weeks: int | None = None,
    strict_audit: bool = False,
    simulate_traffic: bool = False,
    utm_out_dir: str = DEFAULT_UTM_OUT_DIR,
) -> dict[str, Any]:
    """Executa o pipeline mestre e devolve o relatorio com status por estagio."""
    pipeline_started = time.perf_counter()
    root_real = os.path.realpath(root)
    tenants, targets = _pipeline_targets(root_real, run_all, tenant_id, campaign_slug)

    delivery_root = _resolve_contained(root_real, DEFAULT_DELIVERIES_DIR, "deliveries-root")
    static_root = _resolve_contained(root_real, STATIC_CARDS_DIR, "static-cards-root")
    packages_root = _resolve_contained(root_real, PACKAGES_DIR, "packages-root")

    def delivery_dir(target: dict[str, Any]) -> str:
        return os.path.join(delivery_root, target["tenantId"], target["slug"])

    # ------------------------------------------------------------------
    # 1. Contratos dos tenants
    # ------------------------------------------------------------------
    def stage_contracts() -> dict[str, Any]:
        entries = []
        for tid in tenants:
            ctx = tenant_validator.load_and_validate_tenant(tid, root=root_real, strict=True)
            kit = ctx["brandKit"]
            entries.append(
                {
                    "tenantId": tid,
                    "brandName": kit.get("brandName"),
                    "domain": kit.get("domain"),
                    "defaultPreset": kit.get("defaultPreset"),
                }
            )
        return {"tenants": entries, "count": len(entries)}

    # ------------------------------------------------------------------
    # 2. Render master 9:16 (ou verificacao dos manifestos existentes)
    # ------------------------------------------------------------------
    def stage_render() -> dict[str, Any]:
        deliveries: list[dict[str, Any]] = []
        failures: list[str] = []
        for target in targets:
            tid, slug = target["tenantId"], target["slug"]
            out_dir = delivery_dir(target)
            manifest_path = os.path.join(out_dir, "manifest.json")
            if skip_render:
                if not os.path.isfile(render_local.fs_path(manifest_path)):
                    failures.append(
                        f"{tid}/{slug}: manifest ausente ({render_local.rel(root_real, manifest_path)})"
                    )
                    continue
                manifest = _load_json(manifest_path)
                video = ((manifest.get("artifacts") or {}).get("video") or {})
                deliveries.append(
                    {
                        "tenantId": tid,
                        "slug": slug,
                        "mode": "verified",
                        "manifestPath": render_local.rel(root_real, manifest_path),
                        "preset": manifest.get("preset"),
                        "audioStreams": (video.get("ffprobe") or {}).get("audioStreams"),
                    }
                )
                continue
            os.makedirs(render_local.fs_path(out_dir), exist_ok=True)
            with contextlib.redirect_stdout(sys.stderr):
                manifest = preset_runner.run_preset_pipeline(
                    tid, target["configPath"], out_dir, audio_path=None, root=root_real
                )
            video = manifest["artifacts"]["video"]
            deliveries.append(
                {
                    "tenantId": tid,
                    "slug": slug,
                    "mode": "rendered",
                    "manifestPath": render_local.rel(root_real, os.path.join(out_dir, "manifest.json")),
                    "preset": manifest["preset"],
                    "audioStreams": video["ffprobe"].get("audioStreams"),
                }
            )
        if failures:
            raise StageFailure("RENDER_REPROVADO: " + "; ".join(failures), {"failures": failures})
        return {"deliveries": deliveries, "mode": "verified" if skip_render else "rendered"}

    # ------------------------------------------------------------------
    # 3. Derivados multiformato
    # ------------------------------------------------------------------
    derivatives_mod = _optional_module("derivative_formats")

    def stage_derivatives() -> dict[str, Any]:
        campaigns: list[dict[str, Any]] = []
        failures: list[str] = []
        hashes_checked = 0
        for target in targets:
            tid, slug = target["tenantId"], target["slug"]
            if not skip_render:
                derivatives_mod.generate_campaign_derivatives(tid, slug, root=root_real)
            derivatives_path = os.path.join(delivery_dir(target), "derivatives.json")
            if not os.path.isfile(render_local.fs_path(derivatives_path)):
                failures.append(f"{tid}/{slug}: derivatives.json ausente")
                continue
            data = _load_json(derivatives_path)
            declared = data.get("derivatives") or {}
            for key in DERIVATIVE_KEYS:
                entry = declared.get(key)
                if not isinstance(entry, dict):
                    failures.append(f"{tid}/{slug}: derivatives.{key} ausente")
                    continue
                hashes_checked += _declared_hash_ok(
                    root_real,
                    entry.get("path"),
                    entry.get("sha256"),
                    f"{tid}/{slug}: derivatives.{key}",
                    failures,
                )
            campaigns.append({"tenantId": tid, "slug": slug, "declared": len(declared)})
        if failures:
            raise StageFailure("DERIVADOS_REPROVADOS: " + "; ".join(failures), {"failures": failures})
        return {"campaigns": campaigns, "count": len(campaigns), "hashesChecked": hashes_checked}

    # ------------------------------------------------------------------
    # 4. Cards estaticos Stories/Carrossel
    # ------------------------------------------------------------------
    static_cards_mod = _optional_module("static_cards")

    def stage_static_cards() -> dict[str, Any]:
        campaigns: list[dict[str, Any]] = []
        failures: list[str] = []
        total_cards = 0
        hashes_checked = 0
        for target in targets:
            tid, slug = target["tenantId"], target["slug"]
            if not skip_render:
                static_cards_mod.generate_campaign_static_cards(tid, slug, root_real)
            manifest_path = os.path.join(static_root, tid, slug, "static-manifest.json")
            if not os.path.isfile(render_local.fs_path(manifest_path)):
                failures.append(f"{tid}/{slug}: static-manifest.json ausente")
                continue
            data = _load_json(manifest_path)
            if data.get("guardrailsAudited") is not True:
                failures.append(f"{tid}/{slug}: guardrailsAudited deve ser true")
            kits = data.get("kits") or {}
            stories = kits.get("stories") or {}
            carousel = kits.get("carousel") or {}
            count = int(stories.get("count") or 0) + int(carousel.get("count") or 0)
            if int(stories.get("count") or 0) < 1 or int(carousel.get("count") or 0) < 1:
                failures.append(f"{tid}/{slug}: kits stories/carousel vazios")
            for kit_name, kit in (("stories", stories), ("carousel", carousel)):
                for item in kit.get("items") or []:
                    if not isinstance(item, dict):
                        continue
                    hashes_checked += _declared_hash_ok(
                        root_real,
                        item.get("path"),
                        item.get("sha256"),
                        f"{tid}/{slug}: {kit_name}/{item.get('name')}",
                        failures,
                    )
            total_cards += count
            campaigns.append(
                {
                    "tenantId": tid,
                    "slug": slug,
                    "stories": int(stories.get("count") or 0),
                    "carousel": int(carousel.get("count") or 0),
                }
            )
        if failures:
            raise StageFailure("CARDS_REPROVADOS: " + "; ".join(failures), {"failures": failures})
        return {
            "campaigns": campaigns,
            "count": len(campaigns),
            "totalCards": total_cards,
            "hashesChecked": hashes_checked,
        }

    # ------------------------------------------------------------------
    # 5. Pacotes sociais e UTMs
    # ------------------------------------------------------------------
    publish_pack_mod = _optional_module("publish_pack")

    def stage_packages() -> dict[str, Any]:
        packages: list[dict[str, Any]] = []
        failures: list[str] = []
        for target in targets:
            tid, slug = target["tenantId"], target["slug"]
            if not skip_render:
                publish_pack_mod.generate_pack(tid, slug, root=root_real)
            package_dir = os.path.join(packages_root, tid, slug)
            checklist_path = os.path.join(package_dir, "checklist-publicacao.json")
            if not os.path.isfile(render_local.fs_path(checklist_path)):
                failures.append(f"{tid}/{slug}: checklist-publicacao.json ausente")
                continue
            checklist = _load_json(checklist_path)
            if checklist.get("autoPublish") is not False:
                failures.append(f"{tid}/{slug}: autoPublish deve ser false")
            if checklist.get("guardrailsAudited") is not True:
                failures.append(f"{tid}/{slug}: guardrailsAudited deve ser true")
            for name in PACKAGE_FILES:
                if not os.path.isfile(render_local.fs_path(os.path.join(package_dir, name))):
                    failures.append(f"{tid}/{slug}: {name} ausente")
            packages.append(
                {
                    "tenantId": tid,
                    "slug": slug,
                    "checklist": render_local.rel(root_real, checklist_path),
                }
            )
        if failures:
            raise StageFailure("PACOTES_REPROVADOS: " + "; ".join(failures), {"failures": failures})
        return {"packages": packages, "count": len(packages)}

    # ------------------------------------------------------------------
    # 6. Calendario editorial (somente --all)
    # ------------------------------------------------------------------
    calendar_mod = _optional_module("campaign_calendar") if run_all else None

    def stage_calendar() -> dict[str, Any]:
        effective_start = start_date
        effective_weeks = weeks
        calendar_path = os.path.join(root_real, *CALENDAR_REL.split("/"))
        if (not effective_start or not effective_weeks) and os.path.isfile(
            render_local.fs_path(calendar_path)
        ):
            existing = _load_json(calendar_path)
            effective_start = effective_start or existing.get("startDate")
            effective_weeks = effective_weeks or int(existing.get("weeks") or 0) or None
        if not effective_start:
            raise StageFailure("DATA_INICIAL_AUSENTE: informe --start-date YYYY-MM-DD")
        effective_weeks = int(effective_weeks or 4)
        calendar = calendar_mod.build_editorial_calendar(
            str(effective_start), effective_weeks, root=root_real
        )
        slots = calendar.get("slots") or []
        if calendar.get("autoPublish") is not False:
            raise StageFailure("AUTO_PUBLICACAO_ATIVO: calendario deve manter autoPublish false")
        return {
            "startDate": str(effective_start),
            "weeks": effective_weeks,
            "totalSlots": len(slots),
            "totalCampaigns": calendar.get("totalCampaigns"),
            "autoPublish": False,
        }

    # ------------------------------------------------------------------
    # 7. Portal de revisao (somente --all)
    # ------------------------------------------------------------------
    portal_mod = _optional_module("review_dashboard") if run_all else None

    def stage_portal() -> dict[str, Any]:
        if skip_render:
            portal_dir = os.path.join(root_real, PORTAL_DIR)
            missing = [
                name
                for name in PORTAL_FILES
                if not os.path.isfile(render_local.fs_path(os.path.join(portal_dir, name)))
            ]
            if missing:
                raise StageFailure("PORTAL_INCOMPLETO: " + ", ".join(missing), {"missing": missing})
            data = _load_json(os.path.join(portal_dir, "portal-data.json"))
            totals = data.get("totals") or {}
            return {
                "mode": "verified",
                "outputDir": PORTAL_DIR,
                "totalTenants": totals.get("tenants"),
                "totalCampaigns": totals.get("campaigns"),
            }
        result = portal_mod.build_portal(root=root_real)
        return {
            "mode": "rebuilt",
            "outputDir": result.get("outputDir"),
            "totalTenants": result.get("totalTenants"),
            "totalCampaigns": result.get("totalCampaigns"),
        }

    # ------------------------------------------------------------------
    # 8. Auditoria/simulacao UTM
    # ------------------------------------------------------------------
    utm_mod = _optional_module("utm_simulator")

    def stage_utm() -> dict[str, Any]:
        result = utm_mod.audit_and_simulate_utm(
            root=root_real,
            simulate_traffic=simulate_traffic,
            out_dir=utm_out_dir,
        )
        details = {
            "totalUrls": result["totalUrls"],
            "urlsOk": result["urlsOk"],
            "derivedUrls": result["derivedUrls"],
            "collisions": len(result["collisions"]),
            "simulation": (result.get("simulation") or {}).get("outDir"),
        }
        if not result["ok"]:
            errors = [p for p in result["problems"] if p["severity"] == "error"]
            raise StageFailure(
                "UTM_REPROVADO: "
                + "; ".join(f"{p['code']}: {p['message']}" for p in errors[:5]),
                details,
            )
        return details

    # ------------------------------------------------------------------
    # 9. QA editorial (modulo paralelo opcional)
    # ------------------------------------------------------------------
    editorial_qa_mod = _optional_module("editorial_qa")

    def stage_editorial_qa() -> dict[str, Any]:
        runner = None
        for name in ("run_editorial_qa", "audit_editorial_qa", "run_qa", "audit"):
            candidate = getattr(editorial_qa_mod, name, None)
            if callable(candidate):
                runner = candidate
                break
        if runner is None:
            raise StageFailure(
                "API_EDITORIAL_QA_AUSENTE: esperado run_editorial_qa(root=...) em tools/editorial_qa.py",
                {"reason": "api_unavailable"},
            )
        result = runner(root=root_real)
        if not isinstance(result, dict):
            result = {"ok": True, "result": result}
        details = {
            "ok": result.get("ok", True),
            "totalChecked": result.get("totalChecked"),
            "findings": result.get("findings"),
            "warnings": result.get("warnings"),
            "reportPath": result.get("reportPath"),
        }
        if result.get("ok") is False:
            problems = result.get("problems") or result.get("findings") or []
            summary = "; ".join(str(p) for p in list(problems)[:5]) if isinstance(problems, list) else str(problems)
            raise StageFailure("EDITORIAL_QA_REPROVADO: " + summary, details)
        return details

    # ------------------------------------------------------------------
    # 10. Release Gate final
    # ------------------------------------------------------------------
    release_mod = _optional_module("release_audit")

    def stage_release() -> dict[str, Any]:
        if release_mod is None:
            raise StageFailure("MODULO_INDISPONIVEL: release_audit", {"reason": "module_unavailable"})
        result = release_mod.run_release_audit(root=root_real, strict=strict_audit)
        details = {
            "strict": strict_audit,
            "domains": {d["id"]: d["status"] for d in result["domains"]},
            "summary": result["summary"],
        }
        if not result["ok"]:
            failed = [d["id"] for d in result["domains"] if d["status"] == "fail"]
            raise StageFailure("RELEASE_REPROVADO: " + ", ".join(failed), details)
        return details

    # ------------------------------------------------------------------
    # Montagem deterministica dos estagios
    # ------------------------------------------------------------------
    stages: list[dict[str, Any]] = [_run_stage("contratos", "Contratos dos tenants", stage_contracts)]
    stages.append(_run_stage("render", "Render master 9:16", stage_render))
    if derivatives_mod is None:
        stages.append(
            _skipped_stage("derivados", "Derivados multiformato", "modulo derivative_formats indisponivel")
        )
    else:
        stages.append(_run_stage("derivados", "Derivados multiformato", stage_derivatives))
    if static_cards_mod is None:
        stages.append(
            _skipped_stage("cards-estaticos", "Cards estaticos Stories/Carrossel", "modulo static_cards indisponivel")
        )
    else:
        stages.append(
            _run_stage("cards-estaticos", "Cards estaticos Stories/Carrossel", stage_static_cards)
        )
    if publish_pack_mod is None:
        stages.append(
            _skipped_stage("pacotes", "Pacotes sociais e UTMs", "modulo publish_pack indisponivel")
        )
    else:
        stages.append(_run_stage("pacotes", "Pacotes sociais e UTMs", stage_packages))
    if run_all:
        if calendar_mod is None:
            stages.append(
                _skipped_stage("calendario", "Calendario editorial", "modulo campaign_calendar indisponivel")
            )
        else:
            stages.append(_run_stage("calendario", "Calendario editorial", stage_calendar))
        if portal_mod is None:
            stages.append(
                _skipped_stage("portal", "Portal de revisao", "modulo review_dashboard indisponivel")
            )
        else:
            stages.append(_run_stage("portal", "Portal de revisao", stage_portal))
    else:
        stages.append(_skipped_stage("calendario", "Calendario editorial", "escopo --tenant"))
        stages.append(_skipped_stage("portal", "Portal de revisao", "escopo --tenant"))
    if utm_mod is None:
        stages.append(_skipped_stage("utm", "Auditoria UTM", "modulo utm_simulator indisponivel"))
    else:
        stages.append(_run_stage("utm", "Auditoria UTM", stage_utm))
    if editorial_qa_mod is None:
        stages.append(
            _skipped_stage("editorial-qa", "QA editorial", "modulo editorial_qa indisponivel")
        )
    else:
        stages.append(_run_stage("editorial-qa", "QA editorial", stage_editorial_qa))
    stages.append(_run_stage("release-gate", "Release Gate final", stage_release))

    by_id = {stage["id"]: stage for stage in stages}
    render_details = by_id["render"]["details"]
    counts = {
        "tenants": len(tenants),
        "campaigns": len(targets),
        "deliveries": len(render_details.get("deliveries") or []),
        "derivatives": (by_id["derivados"]["details"] or {}).get("count", 0),
        "staticCampaigns": (by_id["cards-estaticos"]["details"] or {}).get("count", 0),
        "staticCards": (by_id["cards-estaticos"]["details"] or {}).get("totalCards", 0),
        "publishPacks": (by_id["pacotes"]["details"] or {}).get("count", 0),
        "calendarSlots": (by_id["calendario"]["details"] or {}).get("totalSlots"),
        "portalCampaigns": (by_id["portal"]["details"] or {}).get("totalCampaigns"),
        "utmUrls": (by_id["utm"]["details"] or {}).get("totalUrls"),
        "utmSimulation": (by_id["utm"]["details"] or {}).get("simulation"),
        "editorialQa": (by_id["editorial-qa"]["details"] or {}).get("totalChecked"),
        "releaseDomains": (by_id["release-gate"]["details"] or {}).get("domains"),
    }

    return {
        "schemaVersion": 1,
        "ok": all(stage["status"] != "failed" for stage in stages),
        "mode": "all" if run_all else "filtered",
        "skipRender": skip_render,
        "root": root_real,
        "durationMs": int(round((time.perf_counter() - pipeline_started) * 1000)),
        "targets": {
            "tenants": tenants,
            "campaigns": [
                {"tenantId": t["tenantId"], "slug": t["slug"], "campaignId": t["campaignId"]}
                for t in targets
            ],
        },
        "stages": stages,
        "counts": counts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Orquestrador unificado da fabrica multi-tenant")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    p_list = subparsers.add_parser("list", help="Lista tenants validos, presets e campanhas")
    p_list.add_argument("--tenant", default=None, help="Filtra um tenant especifico")
    p_list.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_list.add_argument("--json", action="store_true", help="Emite JSON no stdout")

    p_render = subparsers.add_parser("render", help="Renderiza campanhas multi-tenant em lote")
    p_render.add_argument("--all", action="store_true", help="Renderiza todos os tenants ativos")
    p_render.add_argument("--tenant", default=None, help="Slug do tenant especifico")
    p_render.add_argument("--campaign", default=None, help="Slug da campanha dentro do tenant")
    p_render.add_argument("--deliveries-dir", default=DEFAULT_DELIVERIES_DIR, help="Diretorio raiz das entregas")
    p_render.add_argument("--report", default=None, help="Caminho para factory-report.json")
    p_render.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_render.add_argument("--json", action="store_true", help="Emite JSON no stdout")

    p_pipeline = subparsers.add_parser(
        "pipeline", help="Pipeline mestre end-to-end (contratos -> release gate)"
    )
    p_pipeline.add_argument("--all", action="store_true", help="Processa todos os tenants ativos")
    p_pipeline.add_argument("--tenant", default=None, help="Slug do tenant especifico")
    p_pipeline.add_argument("--campaign", default=None, help="Slug da campanha dentro do tenant")
    p_pipeline.add_argument(
        "--skip-render",
        action="store_true",
        help="Nao renderiza; verifica os manifestos e artefatos versionados",
    )
    p_pipeline.add_argument("--start-date", default=None, help="Data inicial do calendario (YYYY-MM-DD)")
    p_pipeline.add_argument("--weeks", type=int, default=None, help="Semanas do calendario editorial")
    p_pipeline.add_argument(
        "--strict-audit", action="store_true", help="Avisos do Release Gate tambem reprovam"
    )
    p_pipeline.add_argument(
        "--simulate-traffic", action="store_true", help="Gera sessoes UTM sinteticas no estagio UTM"
    )
    p_pipeline.add_argument(
        "--utm-out-dir", default=DEFAULT_UTM_OUT_DIR, help="Diretorio da simulacao UTM"
    )
    p_pipeline.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_pipeline.add_argument("--json", action="store_true", help="Emite JSON no stdout")

    args = parser.parse_args(argv)

    try:
        if args.subcommand == "list":
            res = cmd_list(root=args.root, tenant_filter=args.tenant)
            if args.json:
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                for t in res["tenants"]:
                    status = "OK" if t["ok"] else "ERRO"
                    print(
                        f"[{status}] {t['tenantId']} ({t.get('brandName', '?')}) "
                        f"preset={t.get('defaultPreset', '?')} audio={t.get('allowAudioTrack')} "
                        f"campanhas={t.get('campaignsCount', 0)}"
                    )
                    for c in t.get("campaigns", []):
                        print(f"    - {c['slug']} ({c['preset'] or t.get('defaultPreset')}) <- {c['configPath']}")
            return 0 if res["ok"] else 1

        if args.subcommand == "pipeline":
            pipeline_report = cmd_pipeline(
                root=args.root,
                tenant_id=args.tenant,
                campaign_slug=args.campaign,
                run_all=bool(args.all),
                skip_render=bool(args.skip_render),
                start_date=args.start_date,
                weeks=args.weeks,
                strict_audit=bool(args.strict_audit),
                simulate_traffic=bool(args.simulate_traffic),
                utm_out_dir=args.utm_out_dir,
            )
            if args.json:
                print(json.dumps(pipeline_report, ensure_ascii=False, indent=2))
            else:
                print(
                    f"Pipeline {'--all' if pipeline_report['mode'] == 'all' else 'filtrado'}"
                    f"{' (skip-render)' if pipeline_report['skipRender'] else ''}: "
                    f"{pipeline_report['durationMs']} ms"
                )
                for stage in pipeline_report["stages"]:
                    suffix = f" — {stage['error']}" if stage["error"] else ""
                    print(
                        f"  [{stage['status'].upper()}] {stage['id']} "
                        f"({stage['title']}, {stage['durationMs']} ms){suffix}"
                    )
                counts = pipeline_report["counts"]
                print(
                    f"Tenants: {counts['tenants']} | campanhas: {counts['campaigns']} | "
                    f"entregas: {counts['deliveries']} | derivados: {counts['derivatives']} | "
                    f"cards: {counts['staticCards']} | pacotes: {counts['publishPacks']} | "
                    f"UTM: {counts['utmUrls']} | QA editorial: {counts['editorialQa']}"
                )
                print(f"Resultado: {'APROVADO' if pipeline_report['ok'] else 'REPROVADO'}")
            return 0 if pipeline_report["ok"] else 1

        report = cmd_render(
            root=args.root,
            tenant_id=args.tenant,
            campaign_slug=args.campaign,
            render_all=bool(args.all),
            deliveries_dir=args.deliveries_dir,
            report_path=args.report,
        )
    except (
        FactoryError,
        tenant_validator.TenantContractError,
        preset_runner.PresetRunnerError,
        build_video.DeliveryError,
    ) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro: entrada invalida ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"Fabrica concluida: {report['totalTenants']} tenant(s), "
            f"{report['totalCampaigns']} campanha(s) em '{report['deliveriesRoot']}'."
        )
        for d in report["deliveries"]:
            fp = d["ffprobe"]
            print(
                f"  - {d['tenantId']}/{d['campaignSlug']}: "
                f"{fp['width']}x{fp['height']}@{fp['fps']}fps, "
                f"audioStreams={fp['audioStreams']}"
                + (f" ({fp.get('audioCodec')})" if fp.get("audioCodec") else " (-an)")
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
