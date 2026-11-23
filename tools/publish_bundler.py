"""Empacotamento deterministico de distribuicao (Etapa 11).

Consolida artefatos aprovados de uma campanha em pacotes .zip portateis e
auditaveis por SHA-256, sem violar politicas de versionamento nem publicacao
manual. Cada pacote pertence a um unico tenant_id e grava em
``.workspace/bundles/<tenantId>/<slug>/`` (nao rastreado pelo Git).

O ZIP e bit-deterministico: entradas ordenadas lexicograficamente, data/hora
fixa no ZipInfo, permissoes normalizadas, JSON em UTF-8 com LF (\n).
O campo ``autoPublish`` e sempre ``false``.

CLI (a partir da raiz do checkout):
    python tools/publish_bundler.py pack --tenant <id> --slug <slug>
        [--allow-unapproved] [--json] [--root <raiz>]
    python tools/publish_bundler.py verify --bundle <caminho.zip> [--json]
        [--root <raiz>]

API:
    pack_bundle(root, tenant_id, slug, allow_unapproved=False) -> dict
    verify_bundle(bundle_path, root=".") -> dict
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import zipfile
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import render_local
import tenant_validator

BUNDLES_REL = os.path.join(".workspace", "bundles")
DELIVERIES_ROOT_REL = os.path.join("02-reels-shorts", "deliveries")
ARCHIVES_REL = os.path.join(".workspace", "archives")
APPROVALS_STORE_REL = os.path.join(".workspace", "tmp", "aprovacoes-titular.json")

SCHEMA_VERSION = 1
FIXED_ZIP_DATE = (1980, 1, 1, 0, 0, 0)  # data/hora fixa para determinismo
ZIP_PERMS = 0o600  # permissoes normalizadas (rw------- para owner)

_SAFE_SLUG_RE = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_SAFE_TENANT_RE = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")

UNSTAMPED_DOMAINS = (" aguardando", "ajuste")

DOMAIN_NAMES = (
    ("contratos_tenants", "Contratos & Tenants"),
    ("entregas_video", "Entregas de Vídeo & Manifestos"),
    ("pacotes_sociais", "Pacotes Sociais & Guardrails"),
    ("derivados_multiformato", "Derivados Multiformato"),
    ("calendario_utm", "Calendário Editorial & Matriz UTM"),
    ("portal_revisao", "Portal Visual de Revisão"),
    ("higiene_git", "Higiene Git, EOL e Worktrees"),
    ("empacotamento_distribuicao", "Empacotamento de Distribuição"),
)


class PublishBundlerError(Exception):
    """Falha controlada do empacotamento deterministico."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def _now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(abs_path: str) -> str:
    digest = hashlib.sha256()
    with open(render_local.fs_path(abs_path), "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_json(abs_path: str, payload: dict) -> None:
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


def _safe_name(value: Any, label: str, pattern: re.Pattern) -> str:
    text = str(value or "")
    if not pattern.match(text):
        raise PublishBundlerError("NOME_INVALIDO", f"{label} invalido: {text!r}")
    return text


def _contained(root: str, target: str) -> bool:
    root_real = os.path.realpath(root)
    target_real = os.path.realpath(target)
    try:
        return os.path.commonpath([root_real, target_real]) == root_real
    except ValueError:
        return False


def _assert_inside(root: str, target: str, label: str) -> str:
    resolved = os.path.realpath(target)
    if not _contained(root, resolved):
        raise PublishBundlerError(
            "BUNDLE_FORA_DA_RAIZ", f"{label} fora da raiz: {render_local.rel(root, resolved)}"
        )
    return resolved


def _bundles_dir(root_real: str) -> str:
    return os.path.join(root_real, BUNDLES_REL)


def _approvals_store_path(root_real: str) -> str:
    return os.path.join(root_real, APPROVALS_STORE_REL)


def _load_approvals(root_real: str) -> dict[tuple[str, str], dict]:
    path = _approvals_store_path(root_real)
    if not os.path.isfile(render_local.fs_path(path)):
        return {}
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        doc = json.load(handle)
    index: dict[tuple[str, str], dict] = {}
    for item in doc.get("campanhas", []):
        if not isinstance(item, dict):
            continue
        tenant_id = item.get("tenantId")
        slug = item.get("slug")
        if isinstance(tenant_id, str) and isinstance(slug, str):
            index[(tenant_id, slug)] = item
    return index


def _decision(item: dict | None) -> str:
    if not item:
        return "pendente"
    if item.get("decisao") == "aprovado":
        return "aprovado"
    if item.get("decisao") == "ajuste":
        return "ajuste"
    if item.get("aprovada") is True:
        return "aprovado"
    return "pendente"


def _delivery_dir(root_real: str, tenant_id: str, slug: str) -> str:
    return os.path.join(root_real, DELIVERIES_ROOT_REL, tenant_id, slug)


def _archive_dir(root_real: str, slug: str) -> str:
    return os.path.join(root_real, ARCHIVES_REL, slug)


def _checksums_for_files(files: list[str]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for abs_path in files:
        if not os.path.isfile(render_local.fs_path(abs_path)):
            continue
        rel_path = os.path.relpath(abs_path).replace(os.sep, "/")
        result[rel_path] = {
            "sha256": _sha256_file(abs_path),
            "bytes": os.path.getsize(render_local.fs_path(abs_path)),
        }
    return result


def _zip_deterministic(zip_path: str, entries: list[tuple[str, str]]) -> None:
    """Gera um ZIP bit-deterministico.

    ``entries`` e uma lista de (caminho_no_zip, caminho_em_disco), ja ordenada
    lexicograficamente pelo caminho no ZIP.
    """
    os.makedirs(render_local.fs_path(os.path.dirname(zip_path)), exist_ok=True)
    with zipfile.ZipFile(
        render_local.fs_path(zip_path), "w", compression=zipfile.ZIP_DEFLATED
    ) as zf:
        for arcname, disk_path in entries:
            info = zipfile.ZipInfo(
                filename=arcname.replace(os.sep, "/"),
                date_time=FIXED_ZIP_DATE,
            )
            info.external_attr = (ZIP_PERMS << 16) | 0o0
            info.create_system = 0
            info.create_version = 20
            info.extract_version = 20
            info.flag_bits = 0x0008  # data descriptors (UTF-8 names)
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(render_local.fs_path(disk_path), "rb") as handle:
                zf.writestr(info, handle.read())


def _build_bundle_manifest(
    root_real: str,
    tenant_id: str,
    slug: str,
    bundle_path: str,
    items: list[dict],
    approval_status: str,
    brand: dict,
    guardrails: dict,
) -> dict:
    bundle_sha = _sha256_file(bundle_path)
    bundle_bytes = os.path.getsize(render_local.fs_path(bundle_path))
    audio_policy = guardrails.get("audioPolicy", {})
    promotion_history = []
    approvals = _load_approvals(root_real)
    item = approvals.get((tenant_id, slug))
    if item:
        promotion_history.append(
            {
                "decisao": _decision(item),
                "updatedAt": item.get("updatedAt"),
                "reviewer": item.get("revisor", ""),
                "locucaoExternaConferida": bool(item.get("locucaoExternaConferida", False)),
            }
        )

    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedBy": "tools/publish_bundler.py",
        "generatedAt": _now_utc(),
        "tenantId": tenant_id,
        "brandName": brand.get("brandName", tenant_id),
        "domain": brand.get("domain", ""),
        "slug": slug,
        "autoPublish": False,
        "approvalStatus": approval_status,
        "audioPolicy": {
            "allowAudioTrack": bool(audio_policy.get("allowAudioTrack", False)),
            "ffmpegFlag": audio_policy.get("ffmpegFlag"),
            "requireSrt": bool(audio_policy.get("requireSrt", True)),
            "requireExternalNarration": bool(audio_policy.get("requireExternalNarration", False)),
        },
        "bundlePath": os.path.relpath(bundle_path, root_real).replace(os.sep, "/"),
        "bundleSha256": bundle_sha,
        "bundleBytes": bundle_bytes,
        "promotionHistory": promotion_history,
        "items": items,
        "bundleSummary": {
            "itemCount": len(items),
            "totalBytes": sum(it.get("bytes", 0) for it in items),
        },
    }


def pack_bundle(
    root: str = ".",
    tenant_id: str | None = None,
    slug: str | None = None,
    allow_unapproved: bool = False,
) -> dict:
    """Empacota artefatos aprovados de uma campanha em um ZIP deterministico.

    Falha fechada: exige aprovacao expressa (``aprovado``) a menos que
    ``--allow-unapproved`` (selo ``PREVIA_NAO_APROVADA``). Decisoes
    ``ajuste`` nunca entram.
    """
    root_real = os.path.realpath(root)
    if not os.path.isdir(render_local.fs_path(root_real)):
        raise PublishBundlerError("RAIZ_INVALIDA", str(root))

    tenant_id = _safe_name(tenant_id, "tenantId", _SAFE_TENANT_RE)
    slug = _safe_name(slug, "slug", _SAFE_SLUG_RE)

    ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=root_real, strict=True)
    brand = ctx["brandKit"]
    guardrails = ctx["guardrails"]

    delivery_dir = _delivery_dir(root_real, tenant_id, slug)
    if not os.path.isdir(render_local.fs_path(delivery_dir)):
        raise PublishBundlerError("DELIVERY_NAO_ENCONTRADA", f"{tenant_id}/{slug}")

    manifest_path = os.path.join(delivery_dir, "manifest.json")
    if not os.path.isfile(render_local.fs_path(manifest_path)):
        raise PublishBundlerError("MANIFESTO_AUSENTE", f"{tenant_id}/{slug}")
    with open(render_local.fs_path(manifest_path), "r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    artifacts = manifest.get("artifacts") or {}

    # Verifica aprovacao.
    approvals = _load_approvals(root_real)
    approval = approvals.get((tenant_id, slug))
    decision = _decision(approval)
    if decision == "ajuste":
        raise PublishBundlerError(
            "SLOT_EM_AJUSTE", f"{tenant_id}/{slug}: decisao ajuste nao entra no bundle"
        )
    if decision != "aprovado":
        if not allow_unapproved:
            raise PublishBundlerError(
                "CAMPANHA_NAO_APROVADA",
                f"{tenant_id}/{slug}: decisao={decision}; use --allow-unapproved para previao",
            )
        approval_status = "PREVIA_NAO_APROVADA"
    else:
        approval_status = "APROVADO_PELO_TITULAR"

    # Coleta artefatos para empacotar: video, srt, narracao, storyboard, cover,
    # e derivados declarados em derivatives.json (quando presentes no archives).
    files_to_pack: list[str] = []
    items: list[dict] = []

    def _add_file(abs_path: str, kind: str, entry_sha: str | None = None) -> None:
        if not abs_path or not os.path.isfile(render_local.fs_path(abs_path)):
            return
        rel_path = os.path.relpath(abs_path, root_real).replace(os.sep, "/")
        sha = entry_sha or _sha256_file(abs_path)
        files_to_pack.append(abs_path)
        items.append(
            {
                "kind": kind,
                "path": rel_path,
                "sha256": sha,
                "bytes": os.path.getsize(render_local.fs_path(abs_path)),
            }
        )

    # 1. Video (arquivo MP4 da entrega, se existir em disco).
    video = artifacts.get("video") if isinstance(artifacts, dict) else None
    video_path = None
    if isinstance(video, dict):
        archive_rel = str(video.get("archivePath") or "")
        if archive_rel.startswith(".workspace/"):
            candidate = os.path.realpath(
                os.path.join(root_real, archive_rel.replace("/", os.sep))
            )
            if _contained(root_real, candidate) and os.path.isfile(
                render_local.fs_path(candidate)
            ):
                video_path = candidate
    if not video_path:
        video_name = f"{slug}.mp4"
        candidate = os.path.join(delivery_dir, video_name)
        if os.path.isfile(render_local.fs_path(candidate)):
            video_path = candidate
    if video_path:
        _add_file(video_path, "video", video.get("sha256") if isinstance(video, dict) else None)

    # 2. SRT, narracao, storyboard (versao versionada da entrega).
    for key, template in (
        ("srt", f"{slug}.srt"),
        ("narracao", f"{slug}_narracao.txt"),
        ("storyboard", "preview-storyboard.png"),
    ):
        art = artifacts.get(key) if isinstance(artifacts, dict) else None
        sha_hint = art.get("sha256") if isinstance(art, dict) else None
        _add_file(os.path.join(delivery_dir, template), key, sha_hint)

    # 3. Derivados declarados em derivatives.json (arquivos em .workspace/archives).
    derivatives_path = os.path.join(delivery_dir, "derivatives.json")
    if os.path.isfile(render_local.fs_path(derivatives_path)):
        with open(render_local.fs_path(derivatives_path), "r", encoding="utf-8") as handle:
            derivatives = json.load(handle)
        decls = derivatives.get("derivatives") if isinstance(derivatives, dict) else {}
        if isinstance(decls, dict):
            for variant in ("cover", "1x1", "16x9", "thumb-16x9", "preview-formats"):
                entry = decls.get(variant)
                if not isinstance(entry, dict) or not entry.get("path"):
                    continue
                rel = str(entry["path"]).replace("\\", "/")
                if rel.startswith(".workspace/"):
                    clean = rel[len(".workspace/"):]
                else:
                    clean = rel
                abs_candidate = os.path.realpath(
                    os.path.join(root_real, *clean.split("/"))
                )
                if _contained(root_real, abs_candidate) and os.path.isfile(
                    render_local.fs_path(abs_candidate)
                ):
                    _add_file(abs_candidate, variant, entry.get("sha256"))

    # Ordena itens lexicograficamente por caminho para determinismo.
    items.sort(key=lambda it: it["path"])
    files_to_pack = [os.path.join(root_real, it["path"]) for it in items]

    # Falha fechada: SHA-256 de masters/derivados em .workspace/archives conferido
    # contra manifest.json e derivatives.json antes de empacotar.
    archive_dir = _archive_dir(root_real, slug)
    if os.path.isdir(render_local.fs_path(archive_dir)):
        for name in os.listdir(render_local.fs_path(archive_dir)):
            abs_path = os.path.join(archive_dir, name)
            if not os.path.isfile(render_local.fs_path(abs_path)):
                continue
            # Se o arquivo tem declaração no manifesto, confere o hash.
            for it in items:
                if it["path"].endswith(name) or name in it["path"]:
                    declared = it.get("sha256")
                    if declared and declared != _sha256_file(abs_path):
                        raise PublishBundlerError(
                            "HASH_DIVERGENTE_ARCHIVE",
                            f"{name}: hash declarado diverge do arquivo em disco",
                        )

    # Monta o pacote .zip sob .workspace/bundles/<tenant>/<slug>/.
    bundle_dir = _assert_inside(
        root_real,
        os.path.join(root_real, BUNDLES_REL, tenant_id, slug),
        "diretorio do bundle",
    )
    os.makedirs(render_local.fs_path(bundle_dir), exist_ok=True)
    bundle_name = f"{slug}-v{SCHEMA_VERSION}.zip"
    bundle_path = os.path.join(bundle_dir, bundle_name)

    entries = [
        (os.path.relpath(abs_path, root_real).replace(os.sep, "/"), abs_path)
        for abs_path in files_to_pack
    ]
    entries.sort(key=lambda e: e[0])
    _zip_deterministic(bundle_path, entries)

    # Grava bundle-manifest.json ao lado do ZIP.
    bundle_manifest = _build_bundle_manifest(
        root_real,
        tenant_id,
        slug,
        bundle_path,
        items,
        approval_status,
        brand,
        guardrails,
    )
    manifest_path_out = os.path.join(bundle_dir, f"{slug}-v{SCHEMA_VERSION}-manifest.json")
    _atomic_write_json(manifest_path_out, bundle_manifest)

    return {
        "ok": True,
        "autoPublish": False,
        "tenantId": tenant_id,
        "slug": slug,
        "bundlePath": render_local.rel(root_real, bundle_path),
        "manifestPath": render_local.rel(root_real, manifest_path_out),
        "bundleSha256": bundle_manifest["bundleSha256"],
        "bundleBytes": bundle_manifest["bundleBytes"],
        "itemCount": len(items),
        "approvalStatus": approval_status,
        "allowUnapproved": allow_unapproved,
        "items": items,
    }


def verify_bundle(bundle_path: str, root: str = ".") -> dict:
    """Verifica a integridade de um bundle .zip: SHA-256, entradas, manifesto.

    Falha fechada: qualquer divergencia de hash, entrada ausente ou manifesto
    invalido reprova a verificacao.
    """
    root_real = os.path.realpath(root)
    bundle_abs = (
        bundle_path
        if os.path.isabs(bundle_path)
        else os.path.join(root_real, bundle_path.replace("/", os.sep))
    )
    bundle_abs = os.path.realpath(bundle_abs)
    if not _contained(root_real, bundle_abs):
        raise PublishBundlerError("BUNDLE_FORA_DA_RAIZ", f"bundle fora da raiz: {bundle_path}")
    if not os.path.isfile(render_local.fs_path(bundle_abs)):
        raise PublishBundlerError("BUNDLE_NAO_ENCONTRADO", bundle_path)

    bundle_dir = os.path.dirname(bundle_abs)
    base = os.path.splitext(os.path.basename(bundle_abs))[0]
    # O nome eh <slug>-v<schema>.zip; o manifesto correspondente eh
    # <slug>-v<schema>-manifest.json.
    m = re.match(r"^(.+)-v\d+$", base)
    manifest_name = f"{m.group(1)}-v{SCHEMA_VERSION}-manifest.json" if m else f"{base}-manifest.json"
    manifest_abs = os.path.join(bundle_dir, manifest_name)

    problems: list[dict] = []

    if not os.path.isfile(render_local.fs_path(manifest_abs)):
        problems.append(
            {"severity": "error", "code": "MANIFESTO_BUNDLE_AUSENTE", "message": manifest_name}
        )
        return {
            "ok": False,
            "autoPublish": False,
            "bundlePath": render_local.rel(root_real, bundle_abs),
            "bundleSha256": _sha256_file(bundle_abs),
            "problems": problems,
        }

    with open(render_local.fs_path(manifest_abs), "r", encoding="utf-8") as handle:
        bundle_manifest = json.load(handle)

    if bundle_manifest.get("autoPublish") is not False:
        problems.append(
            {"severity": "error", "code": "AUTO_PUBLISH_ATIVO", "message": "autoPublish deve ser false"}
        )

    # Recalcula SHA-256 do ZIP.
    actual_bundle_sha = _sha256_file(bundle_abs)
    declared_bundle_sha = bundle_manifest.get("bundleSha256")
    if declared_bundle_sha and actual_bundle_sha != declared_bundle_sha:
        problems.append(
            {
                "severity": "error",
                "code": "HASH_DIVERGENTE",
                "message": f"bundle SHA-256 diverge (declarado {declared_bundle_sha}, obtido {actual_bundle_sha})",
            }
        )

    # Verifica cada item declarado no manifesto: existe no ZIP e confere hash.
    declared_items = bundle_manifest.get("items") or []
    if not isinstance(declared_items, list):
        problems.append(
            {"severity": "error", "code": "ITENS_INVALIDOS", "message": "items nao e uma lista"}
        )
        declared_items = []

    with zipfile.ZipFile(render_local.fs_path(bundle_abs), "r") as zf:
        zip_names = set(zf.namelist())
        for it in declared_items:
            if not isinstance(it, dict):
                continue
            arcname = it.get("path")
            expected_sha = it.get("sha256")
            if not arcname or not expected_sha:
                problems.append(
                    {
                        "severity": "error",
                        "code": "ITEM_MALFORMADO",
                        "message": f"item sem path/sha256: {it!r}",
                    }
                )
                continue
            if arcname not in zip_names:
                problems.append(
                    {
                        "severity": "error",
                        "code": "ENTRADA_AUSENTE_ZIP",
                        "message": f"{arcname} nao esta no ZIP",
                    }
                )
                continue
            # Extrai para memoria e confere hash.
            data = zf.read(arcname)
            actual_sha = hashlib.sha256(data).hexdigest()
            if actual_sha != expected_sha:
                problems.append(
                    {
                        "severity": "error",
                        "code": "HASH_DIVERGENTE",
                        "message": f"{arcname}: SHA-256 diverge (declarado {expected_sha}, obtido {actual_sha})",
                    }
                )

    # Verifica ordem deterministica: entradas do ZIP devem estar ordenadas.
    with zipfile.ZipFile(render_local.fs_path(bundle_abs), "r") as zf:
        names = zf.namelist()
        if names != sorted(names):
            problems.append(
                {
                    "severity": "error",
                    "code": "ENTRADAS_NAO_ORDENADAS",
                    "message": "entradas do ZIP nao estao ordenadas lexicograficamente",
                }
            )

    errors = sum(1 for p in problems if p["severity"] == "error")
    return {
        "ok": errors == 0,
        "autoPublish": False,
        "bundlePath": render_local.rel(root_real, bundle_abs),
        "manifestPath": render_local.rel(root_real, manifest_abs),
        "bundleSha256": actual_bundle_sha,
        "declaredSha256": declared_bundle_sha,
        "itemCount": len(declared_items),
        "zipEntryCount": len(zip_names),
        "problems": problems,
    }


def verify_all_bundles(root: str = ".") -> dict:
    """Verifica todos os bundles ``*.zip`` de ``.workspace/bundles/`` da estacao.

    Estacao sem bundles e' considerada ``ok`` (o dominio e' informativo: so' verifica
    o que existe). Reprova somente se algum bundle presente falhar.
    """
    root_real = os.path.realpath(root)
    bundles_root = _bundles_dir(root_real)
    bundles: list[dict] = []
    problems: list[dict] = []
    if os.path.isdir(render_local.fs_path(bundles_root)):
        for tenant_id in sorted(os.listdir(render_local.fs_path(bundles_root))):
            tenant_dir = os.path.join(bundles_root, tenant_id)
            if not os.path.isdir(render_local.fs_path(tenant_dir)):
                continue
            for slug in sorted(os.listdir(render_local.fs_path(tenant_dir))):
                slug_dir = os.path.join(tenant_dir, slug)
                if not os.path.isdir(render_local.fs_path(slug_dir)):
                    continue
                for name in sorted(os.listdir(render_local.fs_path(slug_dir))):
                    if not name.endswith(".zip"):
                        continue
                    bundle_abs = os.path.join(slug_dir, name)
                    try:
                        result = verify_bundle(bundle_abs, root=root_real)
                    except PublishBundlerError as exc:
                        result = {
                            "ok": False,
                            "autoPublish": False,
                            "bundlePath": render_local.rel(root_real, bundle_abs),
                            "problems": [
                                {
                                    "severity": "error",
                                    "code": exc.code,
                                    "message": exc.detail,
                                }
                            ],
                        }
                    bundles.append(result)
                    problems.extend(result.get("problems", []))
    return {
        "ok": all(bundle.get("ok", False) for bundle in bundles),
        "autoPublish": False,
        "checkedCount": len(bundles),
        "bundles": bundles,
        "problems": problems,
    }


def cmd_pack(
    root: str = ".",
    tenant_id: str | None = None,
    slug: str | None = None,
    allow_unapproved: bool = False,
) -> dict:
    return pack_bundle(
        root=root, tenant_id=tenant_id, slug=slug, allow_unapproved=allow_unapproved
    )


def cmd_verify(bundle_path: str, root: str = ".") -> dict:
    return verify_bundle(bundle_path=bundle_path, root=root)


def cmd_verify_all(root: str = ".") -> dict:
    return verify_all_bundles(root=root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Empacotamento deterministico de distribuicao (autoPublish sempre false)"
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    p_pack = subparsers.add_parser("pack", help="Empacota artefatos aprovados de uma campanha")
    p_pack.add_argument("--tenant", required=True, help="Slug do tenant")
    p_pack.add_argument("--slug", required=True, help="Slug da campanha")
    p_pack.add_argument(
        "--allow-unapproved",
        action="store_true",
        default=False,
        help="Empacota previo sem aprovacao expressa (selo PREVIA_NAO_APROVADA)",
    )
    p_pack.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_pack.add_argument("--json", action="store_true", help="Emite JSON no stdout")

    p_verify = subparsers.add_parser("verify", help="Verifica integridade de bundles .zip")
    verify_mode = p_verify.add_mutually_exclusive_group(required=False)
    verify_mode.add_argument("--bundle", help="Caminho de um bundle .zip especifico")
    verify_mode.add_argument(
        "--all",
        action="store_true",
        help="Verifica todos os bundles de .workspace/bundles/ (padrao quando nenhum dos dois)",
    )
    p_verify.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    p_verify.add_argument("--json", action="store_true", help="Emite JSON no stdout")

    args = parser.parse_args(argv)

    try:
        if args.subcommand == "pack":
            result = cmd_pack(
                root=args.root,
                tenant_id=args.tenant,
                slug=args.slug,
                allow_unapproved=args.allow_unapproved,
            )
        elif args.bundle:
            result = cmd_verify(bundle_path=args.bundle, root=args.root)
        else:
            result = cmd_verify_all(root=args.root)
    except PublishBundlerError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro: entrada invalida ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.subcommand == "verify" and not args.bundle:
        status = "OK" if result.get("ok") else "REPROVADO"
        print(f"{status}: {result.get('checkedCount', 0)} bundle(s) verificado(s)")
        for bundle in result.get("bundles", []):
            bundle_status = "OK" if bundle.get("ok") else "REPROVADO"
            print(f"  - {bundle.get('bundlePath', '')}: {bundle_status}")
        print(f"  autoPublish: {result.get('autoPublish', False)}")
    else:
        status = "OK" if result.get("ok") else "REPROVADO"
        print(f"{status}: {result.get('tenantId', '')}/{result.get('slug', '')}")
        print(f"  bundle: {result.get('bundlePath', '')}")
        print(f"  sha256: {result.get('bundleSha256', '')}")
        print(f"  itens: {result.get('itemCount', 0)}")
        print(f"  autoPublish: {result.get('autoPublish', False)}")
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
