"""CLI auditavel de gestao das aprovacoes do titular (Etapa 6 - Agente 3).

Consulta o status editorial, registra decisoes (aprovado/aguardando/ajuste) e
audita a integridade do arquivo ``aprovacoes-titular.json`` sem depender do
navegador. E 100% biblioteca padrao e compartilha o mesmo contrato v2 do
``tools/review_dashboard.py``:

    {
      "schemaVersion": 2,
      "arquivo": "aprovacoes-titular.json",
      "origem": "tools/approval_cli.py",
      "exportadoEm": "<ISO-8601 UTC>",
      "revisor": "<nome>",
      "resumo": {"totalCampanhas": N, "aprovadas": A, "ajustes": J, "pendentes": P},
      "campanhas": [
        {"tenantId", "slug", "campaignId", "preset", "politicaAudio",
         "decisao", "locucaoExternaConferida", "observacoes", "hashes", "updatedAt"}
      ]
    }

``updatedAt`` (ISO-8601 UTC) e um campo aditivo por campanha exigido por esta
CLI. O portal le o arquivo sem validacao estrita (GET), portanto exibe o
documento normalmente; o POST estrito do portal ainda nao lista ``updatedAt`` e
uma reexportacao pelo navegador o descarta, sem corromper os demais campos.

O store vive em ``<workspace>/tmp/aprovacoes-titular.json``, resolvido via
``git rev-parse --git-common-dir`` (mesmo padrao de ``review_dashboard.py`` e
``handoff_bundler.py``). Nenhuma operacao publica ou agenda: ``autoPublish`` e
sempre ``false``.

Uso (a partir da raiz do checkout):
    python tools/approval_cli.py status [--json]
    python tools/approval_cli.py decide --tenant <id> --campaign <slug> \
        --decision aprovado --reviewer "Titular" [--external-audio-checked] [--json]
    python tools/approval_cli.py validate [--json]
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
import review_dashboard

APPROVALS_FILENAME = "aprovacoes-titular.json"
SCHEMA_VERSION = 2
DECISIONS = ("aprovado", "aguardando", "ajuste")
TENANTS_ROOT = "tenants"
DELIVERIES_REL = os.path.join("02-reels-shorts", "deliveries")
DOC_ORIGIN = "tools/approval_cli.py"

HASH_ARTIFACTS = {
    "video": "video",
    "srt": "srt",
    "narracao": "narration",
    "storyboard": "storyboard",
}

_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_SAFE_SLUG_RE = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")

_USAGE_ERROR_CODES = {
    "DECISAO_INVALIDA",
    "REVISOR_OBRIGATORIO",
    "NOTES_OBRIGATORIAS",
    "TENANT_DESCONHECIDO",
    "CAMPANHA_DESCONHECIDA",
    "APPROVALS_FORA_DA_RAIZ",
}


class ApprovalError(Exception):
    """Falha controlada da CLI de aprovacoes."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# ---------------------------------------------------------------------------
# Helpers de arquivo e workspace
# ---------------------------------------------------------------------------

def resolve_workspace_dir(root: str = ".") -> str:
    """Workspace aplicavel (git-common-dir), identico ao review_dashboard."""
    return review_dashboard.resolve_workspace_dir(os.path.realpath(root))


def approvals_store_path(root: str = ".") -> str:
    return review_dashboard.approvals_store_path(os.path.realpath(root))


def _load_json(abs_path: str) -> Any:
    with open(render_local.fs_path(abs_path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _atomic_write_json(abs_path: str, payload: dict) -> None:
    """Grava em arquivo temporario na mesma pasta e troca com os.replace."""
    parent = os.path.dirname(abs_path)
    os.makedirs(render_local.fs_path(parent), exist_ok=True)
    tmp_path = os.path.join(parent, f".{os.path.basename(abs_path)}.tmp")
    try:
        with open(render_local.fs_path(tmp_path), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(render_local.fs_path(tmp_path), render_local.fs_path(abs_path))
    finally:
        if os.path.isfile(render_local.fs_path(tmp_path)):
            os.remove(render_local.fs_path(tmp_path))


def _now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_approvals_path(root_real: str, approvals_file: str | None) -> str:
    workspace_root = resolve_workspace_dir(root_real)
    if approvals_file:
        candidate = os.path.realpath(
            approvals_file
            if os.path.isabs(approvals_file)
            else os.path.join(root_real, approvals_file.replace("/", os.sep))
        )
        if not (
            render_local.contained(root_real, candidate)
            or render_local.contained(workspace_root, candidate)
        ):
            raise ApprovalError(
                "APPROVALS_FORA_DA_RAIZ", "arquivo de aprovacoes fora do projeto"
            )
        return candidate
    return os.path.join(workspace_root, "tmp", APPROVALS_FILENAME)


def _rel(root_real: str, abs_path: str) -> str:
    try:
        return render_local.rel(root_real, abs_path)
    except ValueError:
        return abs_path


# ---------------------------------------------------------------------------
# Descoberta de campanhas e leitura do store
# ---------------------------------------------------------------------------

def _campaign_dirs(root_real: str) -> list[str]:
    tenants_dir = os.path.join(root_real, TENANTS_ROOT)
    if not os.path.isdir(render_local.fs_path(tenants_dir)):
        return []
    return sorted(
        name
        for name in os.listdir(render_local.fs_path(tenants_dir))
        if os.path.isdir(render_local.fs_path(os.path.join(tenants_dir, name)))
    )


def discover_campaigns(root: str = ".") -> dict[tuple[str, str], dict]:
    """Indexa todas as campanhas de ``tenants/<tenant>/campaigns/*.json``."""
    root_real = os.path.realpath(root)
    found: dict[tuple[str, str], dict] = {}
    for tenant_id in _campaign_dirs(root_real):
        campaigns_dir = os.path.join(root_real, TENANTS_ROOT, tenant_id, "campaigns")
        if not os.path.isdir(render_local.fs_path(campaigns_dir)):
            continue
        for name in sorted(os.listdir(render_local.fs_path(campaigns_dir))):
            if not name.endswith(".json"):
                continue
            abs_cfg = os.path.join(campaigns_dir, name)
            if not os.path.isfile(render_local.fs_path(abs_cfg)):
                continue
            cfg = _load_json(abs_cfg)
            cfg_tenant = cfg.get("tenantId")
            if cfg_tenant and cfg_tenant != tenant_id:
                raise ApprovalError(
                    "CAMPAIGN_TENANT_MISMATCH",
                    f"{render_local.rel(root_real, abs_cfg)} declara '{cfg_tenant}'",
                )
            slug = str(cfg.get("id") or os.path.splitext(name)[0])
            found[(tenant_id, slug)] = {
                "tenantId": tenant_id,
                "slug": slug,
                "campaignId": str(cfg.get("campaignId") or slug),
                "preset": str(cfg.get("preset") or ""),
                "configPath": render_local.rel(root_real, abs_cfg),
            }
    return found


def tenant_audio_policy(root: str, tenant_id: str) -> dict:
    """Politica de audio do tenant; vazio quando o guardrails nao existe."""
    path = os.path.join(os.path.realpath(root), TENANTS_ROOT, tenant_id, "guardrails.json")
    if not os.path.isfile(render_local.fs_path(path)):
        return {}
    doc = _load_json(path)
    policy = doc.get("audioPolicy")
    return policy if isinstance(policy, dict) else {}


def _external_audio(policy: dict) -> bool:
    return policy.get("allowAudioTrack") is False or policy.get("ffmpegFlag") == "-an"


def _politica_audio_label(policy: dict) -> str:
    flag = policy.get("ffmpegFlag")
    if flag:
        return str(flag)
    return "audio" if policy.get("allowAudioTrack") else ""


def current_hashes(root: str, tenant_id: str, slug: str) -> dict[str, str]:
    """SHA-256 declarados no manifest.json atual da entrega."""
    root_real = os.path.realpath(root)
    manifest = os.path.join(root_real, DELIVERIES_REL, tenant_id, slug, "manifest.json")
    if not os.path.isfile(render_local.fs_path(manifest)):
        return {}
    arts = (_load_json(manifest).get("artifacts") or {})
    hashes: dict[str, str] = {}
    for out_key, art_key in HASH_ARTIFACTS.items():
        art = arts.get(art_key)
        if isinstance(art, dict) and isinstance(art.get("sha256"), str):
            hashes[out_key] = art["sha256"]
    return hashes


def _normalize_decision(item: dict) -> str:
    if "decisao" in item:
        return str(item.get("decisao"))
    if "aprovada" in item:
        return "aprovado" if item.get("aprovada") is True else "aguardando"
    return "aguardando"


def load_document(abs_path: str) -> dict:
    doc = _load_json(abs_path)
    if not isinstance(doc, dict) or not isinstance(doc.get("campanhas"), list):
        raise ApprovalError("APROVACOES_INVALIDAS", "documento sem a lista 'campanhas'")
    return doc


def _index_document(doc: dict) -> dict[tuple[str, str], dict]:
    index: dict[tuple[str, str], dict] = {}
    for item in doc.get("campanhas", []):
        if not isinstance(item, dict):
            continue
        tenant_id = item.get("tenantId")
        slug = item.get("slug")
        if isinstance(tenant_id, str) and isinstance(slug, str):
            index[(tenant_id, slug)] = item
    return index


def _summary(items: list[dict]) -> dict:
    resumo = {"totalCampanhas": len(items), "aprovadas": 0, "ajustes": 0, "pendentes": 0}
    for item in items:
        decision = _normalize_decision(item)
        if decision == "aprovado":
            resumo["aprovadas"] += 1
        elif decision == "ajuste":
            resumo["ajustes"] += 1
        else:
            resumo["pendentes"] += 1
    return resumo


# ---------------------------------------------------------------------------
# Subcomando: status
# ---------------------------------------------------------------------------

def cmd_status(root: str = ".", approvals_file: str | None = None) -> dict:
    """Lista campanhas descobertas cruzadas com as aprovacoes do titular."""
    root_real = os.path.realpath(root)
    campaigns = discover_campaigns(root_real)
    approvals_path = _resolve_approvals_path(root_real, approvals_file)
    exists = os.path.isfile(render_local.fs_path(approvals_path))
    index = _index_document(load_document(approvals_path)) if exists else {}

    rows: list[dict] = []
    for key in sorted(campaigns):
        campaign = campaigns[key]
        item = index.get(key) or {}
        policy = tenant_audio_policy(root_real, key[0])
        decision = _normalize_decision(item)
        rows.append(
            {
                "tenantId": key[0],
                "slug": key[1],
                "campaignId": campaign["campaignId"],
                "preset": campaign["preset"],
                "decision": decision,
                "locucaoExternaConferida": bool(item.get("locucaoExternaConferida", False)),
                "externalAudio": _external_audio(policy),
                "politicaAudio": _politica_audio_label(policy),
                "updatedAt": item.get("updatedAt"),
            }
        )

    policy_by_tenant = {
        row["tenantId"]: {"externalAudio": row["externalAudio"]} for row in rows
    }
    summary = {
        "total": len(rows),
        "aprovadas": sum(1 for r in rows if r["decision"] == "aprovado"),
        "aguardando": sum(1 for r in rows if r["decision"] == "aguardando"),
        "ajuste": sum(1 for r in rows if r["decision"] == "ajuste"),
    }
    pendentes_locucao = [
        {"tenantId": r["tenantId"], "slug": r["slug"]}
        for r in rows
        if r["externalAudio"] and r["decision"] == "aprovado" and not r["locucaoExternaConferida"]
    ]
    return {
        "ok": True,
        "autoPublish": False,
        "exists": exists,
        "approvalsFile": _rel(root_real, approvals_path),
        "summary": summary,
        "externalAudioTenants": sorted(
            tenant for tenant, ctx in policy_by_tenant.items() if ctx["externalAudio"]
        ),
        "locucaoExternaPendente": pendentes_locucao,
        "campaigns": rows,
    }


# ---------------------------------------------------------------------------
# Subcomando: decide
# ---------------------------------------------------------------------------

def cmd_decide(
    root: str = ".",
    tenant_id: str | None = None,
    campaign_slug: str | None = None,
    decision: str | None = None,
    reviewer: str | None = None,
    notes: str | None = None,
    external_audio_checked: bool = False,
    approvals_file: str | None = None,
) -> dict:
    """Registra uma decisao editorial e persiste o store de forma atomica."""
    root_real = os.path.realpath(root)
    decision = str(decision or "")
    if decision not in DECISIONS:
        raise ApprovalError("DECISAO_INVALIDA", f"use um de {DECISIONS}")
    reviewer = str(reviewer or "").strip()
    if not reviewer:
        raise ApprovalError("REVISOR_OBRIGATORIO", "informe --reviewer")
    notes = str(notes or "").strip()
    if decision == "ajuste" and not notes:
        raise ApprovalError("NOTES_OBRIGATORIAS", "decisao 'ajuste' exige --notes")

    tenant_id = str(tenant_id or "")
    campaign_slug = str(campaign_slug or "")
    campaigns = discover_campaigns(root_real)
    key = (tenant_id, campaign_slug)
    if tenant_id not in {t for t, _ in campaigns}:
        raise ApprovalError("TENANT_DESCONHECIDO", tenant_id)
    if key not in campaigns:
        raise ApprovalError("CAMPANHA_DESCONHECIDA", f"{tenant_id}/{campaign_slug}")

    approvals_path = _resolve_approvals_path(root_real, approvals_file)
    doc = load_document(approvals_path) if os.path.isfile(render_local.fs_path(approvals_path)) else {}
    index = _index_document(doc)
    existing = index.get(key) or {}

    policy = tenant_audio_policy(root_real, tenant_id)
    campaign = campaigns[key]
    updated_at = _now_utc()
    item = {
        "tenantId": tenant_id,
        "slug": campaign_slug,
        "campaignId": campaign["campaignId"],
        "preset": campaign["preset"],
        "politicaAudio": _politica_audio_label(policy),
        "decisao": decision,
        "locucaoExternaConferida": bool(
            external_audio_checked or existing.get("locucaoExternaConferida", False)
        ),
        "observacoes": notes,
        "hashes": current_hashes(root_real, tenant_id, campaign_slug),
        "updatedAt": updated_at,
    }

    merged: dict[tuple[str, str], dict] = {}
    for other_key, other_item in index.items():
        normalized = dict(other_item)
        normalized["decisao"] = _normalize_decision(other_item)
        normalized.pop("aprovada", None)
        merged[other_key] = normalized
    merged[key] = item
    campanhas = [merged[k] for k in sorted(merged)]

    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "arquivo": APPROVALS_FILENAME,
        "origem": DOC_ORIGIN,
        "exportadoEm": updated_at,
        "revisor": reviewer,
        "resumo": _summary(campanhas),
        "campanhas": campanhas,
    }
    _atomic_write_json(approvals_path, payload)

    return {
        "ok": True,
        "autoPublish": False,
        "approvalsFile": _rel(root_real, approvals_path),
        "tenantId": tenant_id,
        "slug": campaign_slug,
        "decision": decision,
        "reviewer": reviewer,
        "updatedAt": updated_at,
        "campaign": item,
        "summary": payload["resumo"],
    }


# ---------------------------------------------------------------------------
# Subcomando: validate
# ---------------------------------------------------------------------------

def _validate_item(
    item: Any,
    campaigns: dict[tuple[str, str], dict],
    root_real: str,
    errors: list[dict],
    warnings: list[dict],
) -> dict | None:
    if not isinstance(item, dict):
        errors.append({"code": "TIPO_INVALIDO", "detail": "item de campanha nao e objeto"})
        return None
    tenant_id = item.get("tenantId")
    slug = item.get("slug")
    for field in ("tenantId", "slug", "decisao"):
        if field not in item:
            errors.append({"code": "CAMPO_AUSENTE", "detail": f"campanha sem '{field}'"})
            return None
    if not isinstance(tenant_id, str) or not isinstance(slug, str):
        errors.append({"code": "TIPO_INVALIDO", "detail": "tenantId/slug devem ser texto"})
        return None
    key = (tenant_id, slug)
    decision = _normalize_decision(item)
    if decision not in DECISIONS:
        errors.append(
            {"code": "DECISAO_INVALIDA", "detail": f"{tenant_id}/{slug}: {decision!r}"}
        )
    if key not in campaigns:
        errors.append(
            {"code": "CAMPANHA_DESCONHECIDA", "detail": f"{tenant_id}/{slug}"}
        )
    updated_at = item.get("updatedAt")
    if updated_at is not None and (
        not isinstance(updated_at, str) or not _ISO_RE.match(updated_at)
    ):
        errors.append(
            {"code": "UPDATEDAT_INVALIDO", "detail": f"{tenant_id}/{slug}: {updated_at!r}"}
        )
    hashes = item.get("hashes")
    if hashes is not None and not (
        isinstance(hashes, dict)
        and all(isinstance(k, str) and isinstance(v, str) for k, v in hashes.items())
    ):
        errors.append(
            {"code": "HASHES_INVALIDOS", "detail": f"{tenant_id}/{slug}: hashes malformados"}
        )
        hashes = {}

    policy = tenant_audio_policy(root_real, tenant_id)
    external = _external_audio(policy)
    checked = bool(item.get("locucaoExternaConferida", False))
    if external and decision == "aprovado" and not checked:
        warnings.append(
            {
                "code": "LOCUCAO_EXTERNA_NAO_CONFERIDA",
                "detail": f"{tenant_id}/{slug}: aprovado sem conferencia de locucao externa",
            }
        )

    stored = hashes if isinstance(hashes, dict) else {}
    current = current_hashes(root_real, tenant_id, slug)
    changed: list[str] = []
    if stored:
        for hash_key, stored_value in stored.items():
            if current.get(hash_key) != stored_value:
                changed.append(hash_key)
    stale = bool(changed)

    return {
        "tenantId": tenant_id,
        "slug": slug,
        "decision": decision,
        "locucaoExternaConferida": checked,
        "externalAudio": external,
        "updatedAt": updated_at,
        "staleApproval": stale,
        "changedHashes": changed,
        "hashCheck": "ok" if stored and not changed else ("stale" if stale else "sem_hashes"),
    }


def cmd_validate(root: str = ".", approvals_file: str | None = None) -> dict:
    """Audita schema v2, campanhas conhecidas e hashes pos-aprovacao."""
    root_real = os.path.realpath(root)
    campaigns = discover_campaigns(root_real)
    approvals_path = _resolve_approvals_path(root_real, approvals_file)
    exists = os.path.isfile(render_local.fs_path(approvals_path))
    base = {
        "autoPublish": False,
        "exists": exists,
        "approvalsFile": _rel(root_real, approvals_path),
        "total": 0,
        "summary": {"total": 0, "aprovadas": 0, "aguardando": 0, "ajuste": 0},
        "errors": [],
        "warnings": [],
        "staleApprovals": [],
        "campaigns": [],
    }
    if not exists:
        return {"ok": True, **base}

    errors: list[dict] = []
    warnings: list[dict] = []
    try:
        doc = load_document(approvals_path)
    except (ApprovalError, ValueError, OSError) as exc:
        detail = getattr(exc, "detail", "") or str(exc)
        return {
            "ok": False,
            **base,
            "errors": [{"code": "DOCUMENTO_ILEGIVEL", "detail": detail}],
        }

    schema_version = doc.get("schemaVersion")
    if schema_version != SCHEMA_VERSION:
        errors.append(
            {
                "code": "SCHEMA_VERSION",
                "detail": f"esperado {SCHEMA_VERSION}, recebido {schema_version!r}",
            }
        )
    if "arquivo" in doc and doc.get("arquivo") != APPROVALS_FILENAME:
        errors.append(
            {"code": "ARQUIVO_INVALIDO", "detail": f"arquivo deve ser {APPROVALS_FILENAME}"}
        )
    exportado = doc.get("exportadoEm")
    if exportado is not None and (
        not isinstance(exportado, str) or not _ISO_RE.match(exportado)
    ):
        errors.append({"code": "EXPORTADO_EM_INVALIDO", "detail": str(exportado)})
    if "resumo" in doc and not isinstance(doc.get("resumo"), dict):
        errors.append({"code": "RESUMO_INVALIDO", "detail": "resumo deve ser objeto"})

    items: list[dict] = []
    checked: list[dict] = []
    for raw in doc.get("campanhas", []):
        record = _validate_item(raw, campaigns, root_real, errors, warnings)
        if record is None:
            continue
        checked.append(record)
        items.append(raw)

    stale = [r for r in checked if r["staleApproval"]]
    summary = {
        "total": len(checked),
        "aprovadas": sum(1 for r in checked if r["decision"] == "aprovado"),
        "aguardando": sum(1 for r in checked if r["decision"] == "aguardando"),
        "ajuste": sum(1 for r in checked if r["decision"] == "ajuste"),
    }
    return {
        "ok": not errors and not stale,
        **base,
        "total": len(checked),
        "summary": summary,
        "errors": errors,
        "warnings": warnings,
        "staleApprovals": [
            {
                "tenantId": r["tenantId"],
                "slug": r["slug"],
                "changedHashes": r["changedHashes"],
            }
            for r in stale
        ],
        "campaigns": checked,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_status(result: dict) -> None:
    s = result["summary"]
    print(
        f"Aprovacoes: {s['total']} campanha(s) | aprovadas={s['aprovadas']} "
        f"aguardando={s['aguardando']} ajuste={s['ajuste']} (autoPublish: false)"
    )
    if not result["exists"]:
        print(f"Store ainda nao existe: {result['approvalsFile']}")
    for row in result["campaigns"]:
        audio = " -an" if row["externalAudio"] else ""
        locucao = " locucao=ok" if row["locucaoExternaConferida"] else ""
        print(
            f"  [{row['decision']}] {row['tenantId']}/{row['slug']}"
            f"{audio}{locucao}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gestao auditavel das aprovacoes do titular (autoPublish sempre false)"
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    p_status = subparsers.add_parser("status", help="Lista campanhas e status de aprovacao")
    p_status.add_argument("--approvals-file", default=None, help="JSON de aprovacoes")
    p_status.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_status.add_argument("--json", action="store_true", help="Emite JSON no stdout")

    p_decide = subparsers.add_parser("decide", help="Registra decisao editorial")
    p_decide.add_argument("--tenant", required=True, help="Slug do tenant")
    p_decide.add_argument("--campaign", required=True, help="Slug da campanha")
    p_decide.add_argument("--decision", required=True, choices=DECISIONS)
    p_decide.add_argument("--reviewer", required=True, help="Nome do revisor")
    p_decide.add_argument("--notes", default=None, help="Observacoes (obrigatorias em 'ajuste')")
    p_decide.add_argument(
        "--external-audio-checked",
        action="store_true",
        help="Marca a conferencia de locucao externa (tenants -an)",
    )
    p_decide.add_argument("--approvals-file", default=None, help="JSON de aprovacoes")
    p_decide.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_decide.add_argument("--json", action="store_true", help="Emite JSON no stdout")

    p_validate = subparsers.add_parser("validate", help="Audita integridade das aprovacoes")
    p_validate.add_argument("--approvals-file", default=None, help="JSON de aprovacoes")
    p_validate.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_validate.add_argument("--json", action="store_true", help="Emite JSON no stdout")

    args = parser.parse_args(argv)

    try:
        if args.subcommand == "status":
            result = cmd_status(root=args.root, approvals_file=args.approvals_file)
        elif args.subcommand == "decide":
            result = cmd_decide(
                root=args.root,
                tenant_id=args.tenant,
                campaign_slug=args.campaign,
                decision=args.decision,
                reviewer=args.reviewer,
                notes=args.notes,
                external_audio_checked=args.external_audio_checked,
                approvals_file=args.approvals_file,
            )
        else:
            result = cmd_validate(root=args.root, approvals_file=args.approvals_file)
    except ApprovalError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2 if exc.code in _USAGE_ERROR_CODES else 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro: entrada invalida ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.subcommand == "status":
        _print_status(result)
    elif args.subcommand == "decide":
        print(
            f"Decisao registrada: {result['tenantId']}/{result['slug']} -> "
            f"{result['decision']} ({result['updatedAt']}); autoPublish: false"
        )
    else:
        status = "OK" if result["ok"] else "REPROVADO"
        print(
            f"Validacao {status}: {result['total']} campanha(s), "
            f"{len(result['staleApprovals'])} stale, {len(result['errors'])} erro(s)"
        )
        for err in result["errors"]:
            print(f"  - {err['code']}: {err['detail']}")
        for stale_item in result["staleApprovals"]:
            print(
                f"  - stale: {stale_item['tenantId']}/{stale_item['slug']} "
                f"({', '.join(stale_item['changedHashes'])})"
            )
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())