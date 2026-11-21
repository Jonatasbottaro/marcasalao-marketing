"""Motor de empacotamento diario pos-aprovacao (Etapa 5B - Agente 2).

Cruza tres fontes para produzir o handoff que a operacao humana usa no dia:

  * aprovacoes do titular (``aprovacoes-titular.json``), nos schemas v1
    (``campanhas[].aprovada: true``) e v2 (``campanhas[].decisao:
    "aprovado"``) do ``tools/review_dashboard.py``;
  * o calendario editorial (``04-legendas/calendario-editorial.json``);
  * os pacotes sociais (``04-legendas/pacotes-publicacao/<tenant>/<slug>/``)
    e os derivados (``derivatives.json`` da entrega).

Para cada slot selecionado gera, em
``.workspace/handoff-diario/<dataSugerida>/<slotId>-<tenantId>-<canal>/``:

  * ``POSTAGEM-MANUAL.md``  — ficha de operacao manual (horario BRT, marca,
    conta, formato, alerta de locucao externa para tenants ``-an``, copy,
    URL UTM completa e checklist de 5 passos);
  * ``copy-pronta.txt``     — texto UTF-8 limpo, pronto para colar;
  * ``handoff-manifest.json`` — metadados, hashes SHA-256 esperados, status
    da midia local (``mediaCopied``) e ``autoPublish: false``;
  * a midia correspondente (``<slug>.mp4`` na Onda 1; ``<slug>-1x1.mp4`` ou
    ``<slug>-16x9.mp4`` na Onda 2; ``cover.png``) quando existir em
    ``<workspace>/archives/``.

Gera tambem o indice consolidado ``.workspace/handoff-diario/
INDICE-OPERACIONAL.md`` e ``indice-operacional.json``.

Travas de seguranca (fail-closed):
  * sem ``--include-pending`` empacota SOMENTE campanhas explicitamente
    aprovadas; nenhuma aprovada devolve
    ``{"ok": true, "bundledSlots": 0, "reason":
    "NENHUMA_CAMPANHA_APROVADA_PELO_TITULAR"}``;
  * ``autoPublish`` e sempre ``false`` (nenhuma ferramenta publica);
  * slots com decisao ``ajuste`` nunca entram, nem com ``--include-pending``;
  * todo caminho e validado contra a raiz do projeto / workspace resolvido;
  * a copy e reauditada contra os guardrails do tenant antes de gravar.

Resolucao de ``.workspace/`` em worktrees: ``publish_pack.resolve_workspace_root``
usa ``git rev-parse --git-common-dir`` para alcancar o ``.workspace/`` do
checkout principal, onde vivem os MP4s preservados e as aprovacoes do titular.
O diretorio de SAIDA e relativo a raiz informada (``--root``), de modo que uma
worktree grava o handoff dentro dela.

Uso (a partir da raiz do checkout):
    python tools/handoff_bundler.py --all-approved [--json]
    python tools/handoff_bundler.py --date 2026-11-23 [--include-pending] [--json]
    python tools/handoff_bundler.py --approvals-file .workspace/tmp/aprovacoes-titular.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import publish_pack
import render_local
import tenant_validator

CALENDAR_REL = os.path.join("04-legendas", "calendario-editorial.json")
PACOTES_ROOT_REL = os.path.join("04-legendas", "pacotes-publicacao")
DELIVERIES_ROOT_REL = os.path.join("02-reels-shorts", "deliveries")
ARCHIVES_REL = ".workspace/archives"
APPROVALS_STORE_REL = os.path.join(".workspace", "tmp", "aprovacoes-titular.json")
DEFAULT_OUTPUT_REL = os.path.join(".workspace", "handoff-diario")

REASON_NONE_APPROVED = "NENHUMA_CAMPANHA_APROVADA_PELO_TITULAR"
REASON_NONE_FOR_DATE = "NENHUM_SLOT_APROVADO_NA_DATA"
STAMP_APPROVED = "APROVADO_PELO_TITULAR"
STAMP_PENDING = "PREVIA_NAO_APROVADA"
INDEX_MD = "INDICE-OPERACIONAL.md"
INDEX_JSON = "indice-operacional.json"

CHANNEL_COPY_FILES = {
    "instagram": "instagram-reels.md",
    "youtube": "youtube-shorts.md",
    "facebook": "facebook-reels.md",
}
CHANNEL_LABELS = {
    "instagram": "Instagram",
    "youtube": "YouTube",
    "facebook": "Facebook",
}
FORMAT_MEDIA = {
    "9:16": ("9x16", "{slug}.mp4"),
    "1:1": ("1x1", "{slug}-1x1.mp4"),
    "16:9": ("16x9", "{slug}-16x9.mp4"),
}

_SAFE_NAME_RE = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_UTM_URL_RE = re.compile(r"https://[^\s]+utm_[^\s]+")


class HandoffBundlerError(Exception):
    """Falha controlada do empacotamento de handoff."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(abs_path: str) -> dict:
    with open(render_local.fs_path(abs_path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(abs_path: str) -> str:
    with open(render_local.fs_path(abs_path), "r", encoding="utf-8") as handle:
        return handle.read()


def _write_text(abs_path: str, text: str) -> None:
    os.makedirs(render_local.fs_path(os.path.dirname(abs_path)), exist_ok=True)
    with open(render_local.fs_path(abs_path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _sha256_file(abs_path: str) -> str:
    digest = hashlib.sha256()
    with open(render_local.fs_path(abs_path), "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_name(value: Any, label: str) -> str:
    text = str(value or "")
    if not _SAFE_NAME_RE.match(text):
        raise HandoffBundlerError(
            "NOME_INVALIDO", f"{label} invalido: {text!r}"
        )
    return text


def _workspace_root(root_real: str) -> str:
    return publish_pack.resolve_workspace_root(root_real)


def _contained_in(root: str, target: str) -> bool:
    return render_local.contained(root, target)


def _assert_inside(root: str, target: str, label: str) -> str:
    resolved = os.path.realpath(target)
    if not _contained_in(root, resolved):
        raise HandoffBundlerError(
            "HANDOFF_FORA_DA_RAIZ", f"{label} fora da raiz: {render_local.rel(root, resolved)}"
        )
    return resolved


def _decision(item: dict) -> str:
    """Normaliza a decisao nos schemas v1 (aprovada) e v2 (decisao)."""
    if "aprovada" in item:
        return "aprovado" if item.get("aprovada") is True else "pendente"
    decisao = item.get("decisao")
    if decisao == "aprovado":
        return "aprovado"
    if decisao == "ajuste":
        return "ajuste"
    return "pendente"


def load_approvals(abs_path: str) -> dict[tuple[str, str], dict]:
    """Indexa as aprovacoes do titular por (tenantId, slug).

    Aceita o schema v1 (``aprovada: true``) e o schema v2 (``decisao``).
    Ausencia do arquivo e tratada pelo chamador como "nenhuma aprovacao".
    """
    doc = _load_json(abs_path)
    if not isinstance(doc, dict) or not isinstance(doc.get("campanhas"), list):
        raise HandoffBundlerError(
            "APROVACOES_INVALIDAS", "documento sem a lista 'campanhas'"
        )
    index: dict[tuple[str, str], dict] = {}
    for item in doc["campanhas"]:
        if not isinstance(item, dict):
            continue
        tenant_id = item.get("tenantId")
        slug = item.get("slug")
        if not isinstance(tenant_id, str) or not isinstance(slug, str):
            continue
        index[(tenant_id, slug)] = {
            "status": _decision(item),
            "locucaoExternaConferida": bool(item.get("locucaoExternaConferida", False)),
            "observacoes": item.get("observacoes")
            if isinstance(item.get("observacoes"), str)
            else "",
            "schemaVersion": doc.get("schemaVersion"),
        }
    return index


def _replace_utm(text: str, utm_url: str) -> str:
    """Troca a primeira URL UTM pela URL do slot (Onda 2 tem utm_content proprio)."""
    if not utm_url:
        return text
    novo, count = _UTM_URL_RE.subn(utm_url, text, count=1)
    return novo if count else text


def _utm_from_params(slot: dict, brand: dict) -> str:
    params = slot.get("utmParams") or {}
    if not isinstance(params, dict) or not params:
        return ""
    domain = brand.get("domain", "")
    if not domain:
        return ""
    query = "&".join(f"{key}={value}" for key, value in params.items())
    return f"https://{domain}/?{query}"


def _external_narration(policy: dict) -> bool:
    if policy.get("requireExternalNarration") is True:
        return True
    if policy.get("ffmpegFlag") == "-an":
        return True
    return policy.get("allowAudioTrack") is False


def _resolve_media(
    workspace_root: str,
    delivery_dir: str,
    slug: str,
    formato: str,
    onda: int,
) -> dict:
    """Descreve a midia esperada do slot (Onda 1 = 9:16; Onda 2 = derivado)."""
    variant, template = FORMAT_MEDIA.get(formato, FORMAT_MEDIA["9:16"])
    expected_name = template.format(slug=slug)
    manifest_path = os.path.join(delivery_dir, "manifest.json")
    manifest = _load_json(manifest_path) if os.path.isfile(render_local.fs_path(manifest_path)) else {}
    artifacts = manifest.get("artifacts") or {}
    workspace_rel = f".workspace/archives/{slug}"

    source_rel: str | None = None
    sha_expected: str | None = None
    if onda == 1 or variant == "9x16":
        video = artifacts.get("video") or {}
        source_rel = str(video.get("archivePath") or f"{workspace_rel}/{expected_name}")
        sha_expected = video.get("sha256") or None
    else:
        derivatives_path = os.path.join(delivery_dir, "derivatives.json")
        derivatives = _load_json(derivatives_path) if os.path.isfile(render_local.fs_path(derivatives_path)) else {}
        items = derivatives.get("derivatives") if isinstance(derivatives, dict) else {}
        item = items.get(variant) if isinstance(items, dict) else None
        if isinstance(item, dict) and item.get("path"):
            source_rel = str(item["path"])
            sha_expected = item.get("sha256") or None
        else:
            source_rel = f"{workspace_rel}/derivatives/{expected_name}"

    def _abs_under_workspace(rel_path: str) -> str | None:
        clean = rel_path.replace("\\", "/")
        if clean.startswith(".workspace/"):
            clean = clean[len(".workspace/"):]
        if ".." in clean.split("/") or clean.startswith("/") or ":" in clean:
            return None
        target = os.path.realpath(os.path.join(workspace_root, *clean.split("/")))
        if not _contained_in(workspace_root, target):
            return None
        return target

    candidates: list[str] = []
    if source_rel:
        first = _abs_under_workspace(source_rel)
        if first:
            candidates.append(first)
    candidates.append(os.path.join(workspace_root, "archives", slug, expected_name))
    candidates.append(os.path.join(workspace_root, "archives", slug, "derivatives", expected_name))

    source_abs = next(
        (c for c in candidates if os.path.isfile(render_local.fs_path(c))), None
    )
    return {
        "variant": variant,
        "expectedFile": expected_name,
        "sourceRelPath": render_local.rel(workspace_root, source_abs)
        if source_abs
        else (source_rel or ""),
        "sourceAbsPath": source_abs,
        "sha256Expected": sha_expected,
    }


def _resolve_cover(workspace_root: str, delivery_dir: str, slug: str) -> dict:
    derivatives_path = os.path.join(delivery_dir, "derivatives.json")
    derivatives = _load_json(derivatives_path) if os.path.isfile(render_local.fs_path(derivatives_path)) else {}
    items = derivatives.get("derivatives") if isinstance(derivatives, dict) else {}
    cover = items.get("cover") if isinstance(items, dict) else None
    expected_name = f"{slug}-cover.png"
    candidates: list[str] = []
    if isinstance(cover, dict) and cover.get("path"):
        clean = str(cover["path"]).replace("\\", "/")
        if clean.startswith(".workspace/"):
            clean = clean[len(".workspace/"):]
        if ".." not in clean.split("/"):
            target = os.path.realpath(os.path.join(workspace_root, *clean.split("/")))
            if _contained_in(workspace_root, target):
                candidates.append(target)
    candidates.append(os.path.join(workspace_root, "archives", slug, "derivatives", expected_name))
    source_abs = next(
        (c for c in candidates if os.path.isfile(render_local.fs_path(c))), None
    )
    return {
        "expectedFile": "cover.png",
        "sourceAbsPath": source_abs,
        "sha256Expected": (cover or {}).get("sha256") if isinstance(cover, dict) else None,
    }


def _copy_media(source_abs: str | None, dest_abs: str, expected_sha: str | None) -> dict:
    """Copia a midia e confere o hash; nunca entrega arquivo divergente."""
    if not source_abs:
        return {
            "copiedFile": None,
            "mediaCopied": False,
            "sha256Copied": None,
            "hashVerified": None,
            "error": "MIDIA_AUSENTE_NESTA_ESTACAO",
        }
    shutil.copyfile(render_local.fs_path(source_abs), render_local.fs_path(dest_abs))
    actual = _sha256_file(dest_abs)
    if expected_sha and actual != expected_sha:
        os.remove(render_local.fs_path(dest_abs))
        return {
            "copiedFile": None,
            "mediaCopied": False,
            "sha256Copied": actual,
            "hashVerified": False,
            "error": "HASH_DIVERGENTE",
        }
    return {
        "copiedFile": os.path.basename(dest_abs),
        "mediaCopied": True,
        "sha256Copied": actual,
        "hashVerified": bool(expected_sha),
        "error": None,
    }


# ---------------------------------------------------------------------------
# Geracao dos artefatos por slot
# ---------------------------------------------------------------------------

def _render_postagem_manual(slot: dict, info: dict) -> str:
    policy = info["audioPolicy"]
    status_line = (
        f"Aprovado pelo titular — publicacao manual autorizada."
        if info["approved"]
        else f"{STAMP_PENDING} — NAO PUBLICAR sem aprovacao expressa do titular."
    )
    media_line = (
        f"Copia local: `{info['media']['copiedFile']}`"
        if info["media"]["mediaCopied"]
        else "Midia AUSENTE nesta estacao (copiar de outra estacao onde `.workspace/archives/` existe)."
    )
    linhas = [
        f"# Postagem manual — {info['slotId']}",
        "",
        f"**Status:** {status_line}",
        "",
        f"- **Data sugerida:** {info['dataSugerida']} ({info['diaSemana']})",
        f"- **Horario (BRT):** {info['janelaHorarioBrt']}",
        f"- **Conta/marca:** {info['brandName']} (`{info['tenantId']}`)",
        f"- **Canal:** {info['channelLabel']} (`{info['canal']}`)",
        f"- **Formato:** {info['formatoVideo']}",
        f"- **Campanha:** `{info['slug']}`",
        f"- **Midia esperada:** `{info['media']['expectedFile']}` — {media_line}",
        f"- **autoPublish:** false (nenhuma ferramenta publica ou agenda sozinha)",
        "",
    ]
    if policy.get("ffmpegFlag"):
        linhas.append(f"- **Politica de audio:** `{policy.get('ffmpegFlag')}`")
    linhas.append("")
    if info["externalNarration"]:
        linhas.extend(
            [
                "## Alerta: locucao externa",
                "",
                "> Este tenant e `-an`: o video sai sem audio. Grave a locucao fora do",
                "> editor a partir do arquivo de narracao da entrega. A locucao NAO e",
                "> requisito para publicar o video legendado — entregue o video mudo com",
                "> legendas queimadas e o `.srt` correspondente.",
                "",
            ]
        )
    linhas.extend(
        [
            "## Copy pronta (colar)",
            "",
            "```text",
            info["copyText"].rstrip("\n"),
            "```",
            "",
            "## URL UTM completa",
            "",
            info["utmUrl"],
            "",
            "## Checklist de publicacao (5 passos)",
            "",
            "1. Confirmar a aprovacao expressa do titular e o status deste slot.",
            f"2. Conferir o SHA-256 da midia contra o `handoff-manifest.json`"
            + (f" (esperado: `{info['media']['sha256Expected']}`)." if info["media"]["sha256Expected"] else "."),
            f"3. Anexar `{info['media']['expectedFile']}`"
            + (" ja copiado nesta pasta." if info["media"]["mediaCopied"] else " (indisponivel nesta estacao)."),
            "4. Colar a copy de `copy-pronta.txt`, mantendo a URL UTM exatamente como esta.",
            f"5. Publicar manualmente na janela {info['janelaHorarioBrt']} (BRT) e registrar o link publicado.",
            "",
        ]
    )
    return "\n".join(linhas)


def _bundle_slot(
    root_real: str,
    workspace_root: str,
    output_root: str,
    slot: dict,
    approval: dict | None,
) -> dict:
    slot_id = _safe_name(slot.get("slotId"), "slotId")
    tenant_id = _safe_name(slot.get("tenantId"), "tenantId")
    canal = _safe_name(slot.get("canal"), "canal")
    slug = _safe_name(slot.get("slug"), "slug")
    if canal not in CHANNEL_COPY_FILES:
        raise HandoffBundlerError("CANAL_INVALIDO", f"{slot_id}: canal {canal!r}")

    status = approval["status"] if approval else "pendente"
    if status == "ajuste":
        raise HandoffBundlerError("SLOT_EM_AJUSTE", f"{tenant_id}/{slug} pediu ajuste")
    approved = status == "aprovado"

    tenant_ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=root_real, strict=True)
    brand = tenant_ctx["brandKit"]
    guardrails = tenant_ctx["guardrails"]

    pacotes_root = os.path.realpath(os.path.join(root_real, PACOTES_ROOT_REL))
    package_dir = _assert_inside(
        pacotes_root,
        os.path.join(pacotes_root, tenant_id, slug),
        f"pacote {tenant_id}/{slug}",
    )
    copy_file = CHANNEL_COPY_FILES[canal]
    copy_abs = os.path.join(package_dir, copy_file)
    if not os.path.isfile(render_local.fs_path(copy_abs)):
        raise HandoffBundlerError(
            "PACOTE_AUSENTE", f"{tenant_id}/{slug}: {copy_file} nao encontrado"
        )
    raw_copy = _read_text(copy_abs).strip("\n")

    utm_url = str(slot.get("utmUrl") or "") or _utm_from_params(slot, brand)
    copy_text = _replace_utm(raw_copy, utm_url)
    violations = tenant_validator.validate_text_against_guardrails(
        copy_text, guardrails, check_ui_elements=True
    )
    if violations:
        raise HandoffBundlerError(
            "GUARDRAIL_VIOLACAO", f"{tenant_id}/{slug}/{canal}: " + "; ".join(violations)
        )

    delivery_dir = _assert_inside(
        os.path.realpath(os.path.join(root_real, DELIVERIES_ROOT_REL)),
        os.path.join(root_real, DELIVERIES_ROOT_REL, tenant_id, slug),
        f"entrega {tenant_id}/{slug}",
    )

    formato = str(slot.get("formatoVideo") or "9:16")
    onda = int(slot.get("onda") or 1)
    media = _resolve_media(workspace_root, delivery_dir, slug, formato, onda)
    cover = _resolve_cover(workspace_root, delivery_dir, slug)

    dest_dir = _assert_inside(
        output_root,
        os.path.join(output_root, str(slot.get("dataSugerida")), f"{slot_id}-{tenant_id}-{canal}"),
        f"pasta do slot {slot_id}",
    )
    os.makedirs(render_local.fs_path(dest_dir), exist_ok=True)

    media_copy = _copy_media(
        media["sourceAbsPath"],
        os.path.join(dest_dir, media["expectedFile"]),
        media["sha256Expected"],
    )
    cover_copy = _copy_media(
        cover["sourceAbsPath"],
        os.path.join(dest_dir, "cover.png"),
        cover["sha256Expected"],
    )

    policy = slot.get("audioPolicy")
    if not isinstance(policy, dict) or not policy:
        policy = guardrails.get("audioPolicy") or {}
    audit_policy = {
        "allowAudioTrack": bool(policy.get("allowAudioTrack", False)),
        "ffmpegFlag": policy.get("ffmpegFlag"),
        "requireSrt": bool(policy.get("requireSrt", True)),
        "requireExternalNarration": bool(policy.get("requireExternalNarration", False)),
    }
    external_narration = _external_narration(audit_policy)

    info = {
        "slotId": slot_id,
        "tenantId": tenant_id,
        "brandName": str(slot.get("brandName") or brand.get("brandName") or tenant_id),
        "slug": slug,
        "canal": canal,
        "channelLabel": CHANNEL_LABELS[canal],
        "dataSugerida": str(slot.get("dataSugerida") or ""),
        "diaSemana": str(slot.get("diaSemana") or ""),
        "janelaHorarioBrt": str(slot.get("janelaHorarioBrt") or ""),
        "formatoVideo": formato,
        "onda": onda,
        "approved": approved,
        "externalNarration": external_narration,
        "audioPolicy": audit_policy,
        "copyText": copy_text,
        "utmUrl": utm_url,
        "media": media_copy | {"expectedFile": media["expectedFile"], "sha256Expected": media["sha256Expected"]},
    }

    _write_text(os.path.join(dest_dir, "copy-pronta.txt"), copy_text + "\n")
    _write_text(os.path.join(dest_dir, "POSTAGEM-MANUAL.md"), _render_postagem_manual(slot, info))

    manifest = {
        "schemaVersion": 1,
        "generatedBy": "tools/handoff_bundler.py",
        "slotId": slot_id,
        "tenantId": tenant_id,
        "brandName": info["brandName"],
        "slug": slug,
        "campaignId": slug,
        "canal": canal,
        "channelLabel": info["channelLabel"],
        "onda": onda,
        "formatoVideo": formato,
        "dataSugerida": info["dataSugerida"],
        "diaSemana": info["diaSemana"],
        "janelaHorarioBrt": info["janelaHorarioBrt"],
        "approvalStatus": STAMP_APPROVED if approved else STAMP_PENDING,
        "approved": approved,
        "locucaoExternaConferida": bool(
            approval.get("locucaoExternaConferida") if approval else False
        ),
        "externalNarrationAlert": external_narration,
        "audioPolicy": audit_policy,
        "copyFile": "copy-pronta.txt",
        "copySourcePackage": render_local.rel(root_real, copy_abs),
        "utmUrl": utm_url,
        "utmParams": slot.get("utmParams") or {},
        "media": {
            "expectedFile": media["expectedFile"],
            "sourceRelPath": media["sourceRelPath"],
            "copiedFile": media_copy["copiedFile"],
            "mediaCopied": media_copy["mediaCopied"],
            "sha256Expected": media["sha256Expected"],
            "sha256Copied": media_copy["sha256Copied"],
            "hashVerified": media_copy["hashVerified"],
            "error": media_copy["error"],
        },
        "cover": {
            "expectedFile": "cover.png",
            "copiedFile": cover_copy["copiedFile"],
            "copyCopied": cover_copy["mediaCopied"],
            "sha256Expected": cover["sha256Expected"],
            "sha256Copied": cover_copy["sha256Copied"],
            "error": cover_copy["error"],
        },
        "guardrailsAudited": True,
        "guardrailViolations": [],
        "autoPublish": False,
        "manualOnly": True,
    }
    _write_text(
        os.path.join(dest_dir, "handoff-manifest.json"),
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )
    manifest["_dirRel"] = render_local.rel(root_real, dest_dir)
    return manifest


# ---------------------------------------------------------------------------
# Indice consolidado
# ---------------------------------------------------------------------------

def _render_index_md(manifests: list[dict]) -> str:
    linhas = [
        "# Indice operacional — handoff diario",
        "",
        "Gerado por `tools/handoff_bundler.py`. `autoPublish: false` — toda",
        "publicacao e manual e exige aprovacao expressa do titular.",
        "",
        f"**Slots empacotados nesta execucao:** {len(manifests)}",
        "",
        "| Data | Slot | Marca | Canal | Formato | Status | Midia local | Pasta |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in sorted(
        manifests,
        key=lambda m: (m["dataSugerida"], m["slotId"], m["tenantId"], m["canal"]),
    ):
        midia = "sim" if item["media"]["mediaCopied"] else "ausente nesta estacao"
        linhas.append(
            "| {data} | {slot} | {brand} (`{tenant}`) | {canal} | {fmt} | {status} | {midia} | `{pasta}` |".format(
                data=item["dataSugerida"],
                slot=item["slotId"],
                brand=item["brandName"].replace("|", "/"),
                tenant=item["tenantId"],
                canal=item["channelLabel"],
                fmt=item["formatoVideo"],
                status=item["approvalStatus"],
                midia=midia,
                pasta=item["_dirRel"],
            )
        )
    linhas.append("")
    return "\n".join(linhas)


def _write_index(root_real: str, output_root: str, manifests: list[dict]) -> dict:
    summary = {
        "schemaVersion": 1,
        "generatedBy": "tools/handoff_bundler.py",
        "autoPublish": False,
        "bundledSlots": len(manifests),
        "dates": sorted({m["dataSugerida"] for m in manifests}),
        "slots": [
            {
                "slotId": m["slotId"],
                "tenantId": m["tenantId"],
                "slug": m["slug"],
                "canal": m["canal"],
                "dataSugerida": m["dataSugerida"],
                "formatoVideo": m["formatoVideo"],
                "approvalStatus": m["approvalStatus"],
                "mediaCopied": m["media"]["mediaCopied"],
                "directory": m["_dirRel"],
            }
            for m in sorted(
                manifests,
                key=lambda m: (m["dataSugerida"], m["slotId"], m["tenantId"], m["canal"]),
            )
        ],
    }
    _write_text(os.path.join(output_root, INDEX_MD), _render_index_md(manifests))
    _write_text(
        os.path.join(output_root, INDEX_JSON),
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
    )
    return summary


# ---------------------------------------------------------------------------
# API programatica
# ---------------------------------------------------------------------------

def _calendar_slots(root_real: str) -> list[dict]:
    calendar_path = os.path.join(root_real, CALENDAR_REL)
    if not os.path.isfile(render_local.fs_path(calendar_path)):
        raise HandoffBundlerError(
            "CALENDARIO_AUSENTE", f"nao encontrado: {CALENDAR_REL}"
        )
    doc = _load_json(calendar_path)
    slots = doc.get("slots")
    if not isinstance(slots, list):
        raise HandoffBundlerError("CALENDARIO_INVALIDO", "campo 'slots' ausente")
    return [slot for slot in slots if isinstance(slot, dict)]


def _resolve_approvals_path(
    root_real: str, workspace_root: str, approvals_file: str | None
) -> str:
    if approvals_file:
        candidate = os.path.realpath(
            approvals_file
            if os.path.isabs(approvals_file)
            else os.path.join(root_real, approvals_file)
        )
        if not (
            _contained_in(root_real, candidate) or _contained_in(workspace_root, candidate)
        ):
            raise HandoffBundlerError(
                "APROVACOES_FORA_DA_RAIZ", "arquivo de aprovacoes fora do projeto"
            )
        return candidate
    return os.path.join(workspace_root, "tmp", "aprovacoes-titular.json")


def build_handoff_bundle(
    root: str = ".",
    approvals_file: str | None = None,
    date: str | None = None,
    all_approved: bool = False,
    include_pending: bool = False,
    output_dir: str | None = None,
) -> dict:
    """Empacota o handoff diario a partir das aprovacoes do titular.

    Sem ``include_pending``, SOMENTE campanhas explicitamente aprovadas sao
    empacotadas; sem nenhuma aprovada devolve o JSON limpo com
    ``bundledSlots: 0`` e ``reason: NENHUMA_CAMPANHA_APROVADA_PELO_TITULAR``.
    ``autoPublish`` e sempre ``false``.
    """
    if date and all_approved:
        raise ValueError("use --date ou --all-approved, nao ambos")
    if date is not None and not _DATE_RE.match(str(date)):
        raise ValueError("data deve estar no formato YYYY-MM-DD")

    root_real = os.path.realpath(root)
    if not os.path.isdir(render_local.fs_path(root_real)):
        raise HandoffBundlerError("RAIZ_INVALIDA", str(root))

    slots_calendar = _calendar_slots(root_real)
    workspace_root = _workspace_root(root_real)
    approvals_path = _resolve_approvals_path(root_real, workspace_root, approvals_file)
    approvals = (
        load_approvals(approvals_path)
        if os.path.isfile(render_local.fs_path(approvals_path))
        else {}
    )

    selected: list[tuple[dict, dict | None]] = []
    skipped: list[dict] = []
    for slot in slots_calendar:
        if date and str(slot.get("dataSugerida")) != date:
            continue
        key = (str(slot.get("tenantId")), str(slot.get("slug")))
        approval = approvals.get(key)
        status = approval["status"] if approval else "pendente"
        if status == "aprovado":
            selected.append((slot, approval))
        elif status == "ajuste":
            skipped.append(
                {"slotId": slot.get("slotId"), "reason": "AJUSTE_SOLICITADO"}
            )
        elif include_pending:
            selected.append((slot, approval))
        else:
            skipped.append(
                {"slotId": slot.get("slotId"), "reason": "NAO_APROVADA"}
            )

    selected.sort(key=lambda pair: (str(pair[0].get("dataSugerida")), str(pair[0].get("slotId"))))

    if not selected:
        if not approvals or not any(item["status"] == "aprovado" for item in approvals.values()):
            return {"ok": True, "bundledSlots": 0, "reason": REASON_NONE_APPROVED}
        return {
            "ok": True,
            "bundledSlots": 0,
            "reason": REASON_NONE_FOR_DATE if date else REASON_NONE_APPROVED,
        }

    output_root = _assert_inside(
        root_real,
        os.path.join(root_real, output_dir or DEFAULT_OUTPUT_REL),
        "diretorio de saida",
    )
    os.makedirs(render_local.fs_path(output_root), exist_ok=True)

    manifests: list[dict] = []
    for slot, approval in selected:
        try:
            manifests.append(
                _bundle_slot(root_real, workspace_root, output_root, slot, approval)
            )
        except HandoffBundlerError as exc:
            # Pacote social ausente nao derruba os demais slots aprovados.
            if exc.code != "PACOTE_AUSENTE":
                raise
            skipped.append(
                {
                    "slotId": slot.get("slotId"),
                    "reason": "PACOTE_AUSENTE",
                    "detail": exc.detail,
                }
            )

    index = _write_index(root_real, output_root, manifests)
    return {
        "ok": True,
        "autoPublish": False,
        "bundledSlots": len(manifests),
        "outputDir": render_local.rel(root_real, output_root),
        "indexMarkdown": render_local.rel(root_real, os.path.join(output_root, INDEX_MD)),
        "indexJson": render_local.rel(root_real, os.path.join(output_root, INDEX_JSON)),
        "dates": index["dates"],
        "slots": index["slots"],
        "skipped": skipped,
        "reason": None,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Empacotamento diario pos-aprovacao: gera handoff manual por slot "
            "(autoPublish sempre false)."
        )
    )
    parser.add_argument(
        "--approvals-file",
        default=None,
        help="JSON de aprovacoes do titular (padrao: <workspace>/tmp/aprovacoes-titular.json)",
    )
    parser.add_argument("--date", default=None, help="Filtra slots por dataSugerida (YYYY-MM-DD)")
    parser.add_argument(
        "--all-approved",
        action="store_true",
        help="Empacota todas as campanhas aprovadas do calendario",
    )
    parser.add_argument(
        "--include-pending",
        action="store_true",
        help="Inclui slots nao aprovados com o selo PREVIA_NAO_APROVADA",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=f"Diretorio de saida (padrao: {DEFAULT_OUTPUT_REL.replace(os.sep, '/')})",
    )
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument("--json", action="store_true", help="Emite JSON no stdout")
    args = parser.parse_args(argv)

    try:
        result = build_handoff_bundle(
            root=args.root,
            approvals_file=args.approvals_file,
            date=args.date,
            all_approved=args.all_approved,
            include_pending=args.include_pending,
            output_dir=args.output_dir,
        )
    except HandoffBundlerError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro: entrada invalida ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("bundledSlots"):
        print(
            f"Handoff gerado em {result['outputDir']} "
            f"({result['bundledSlots']} slot(s); autoPublish: false)"
        )
    else:
        print(f"Nenhum slot empacotado: {result.get('reason')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())