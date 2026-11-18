"""Orquestrador em lote da fabrica multi-tenant de videos (Agente 3 - Etapa 2).

Descobre tenants validos em `tenants/`, lista campanhas configuradas, aciona
o motor generico (`tools/preset_runner.py`) respeitando contratos e politicas de
audio por tenant, grava pacotes de entrega padronizados em
`02-reels-shorts/deliveries/<tenantId>/<slug>/` (com copia dos .mp4 em
`.workspace/archives/<slug>/`) e gera o relatorio consolidado
`02-reels-shorts/deliveries/factory-report.json`.

Uso (a partir da raiz do checkout):
    python tools/factory_cli.py list [--tenant <tenantId>] [--json]
    python tools/factory_cli.py render --tenant <tenantId> [--campaign <slug>] [--json]
    python tools/factory_cli.py render --all [--json]
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import preset_runner
import render_local
import tenant_validator

DEFAULT_DELIVERIES_DIR = "02-reels-shorts/deliveries"
DEFAULT_REPORT_REL = "02-reels-shorts/deliveries/factory-report.json"


class FactoryError(Exception):
    """Erro controlado do orquestrador da fabrica."""


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Orquestrador em lote da fabrica multi-tenant")
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
