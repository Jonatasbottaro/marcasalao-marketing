"""Gerador e servidor local do Portal de Revisao (Etapa 4 - Agente 2).

Consolida em um portal estatico de revisao humana (05-review-portal/):
  - tenants: tenants/*/brand-kit.json + guardrails.json
  - entregas: 02-reels-shorts/deliveries/<tenant>/<slug>/
    (manifest.json, <slug>.srt, <slug>_narracao.txt, preview-storyboard.png
    e, opcionalmente, cover.png, preview-formats.png e derivatives.json)
  - pacotes sociais: 04-legendas/pacotes-publicacao/<tenant>/<slug>/
    (checklist-publicacao.json, instagram-reels.md, youtube-shorts.md,
    facebook-reels.md)

Gera 05-review-portal/index.html (dados embutidos, funciona via file://),
05-review-portal/portal-data.json e 05-review-portal/README.md. O build e
deterministico: nao grava timestamps e produz bytes identicos para os mesmos
insumos, para que o portal versionado seja o mesmo em qualquer estacao.

Resolucao de .workspace/ em worktrees: .workspace/ nao e versionado e nao
existe dentro de worktrees; quando a raiz informada e uma worktree, a raiz
principal e localizada via git rev-parse --git-common-dir para alcancar
.workspace/archives/ (videos locais) e .workspace/tmp/aprovacoes-titular.json
(aprovacoes do titular). Raizes que nao sao toplevel de checkout usam o
proprio <raiz>/.workspace.

O modo --serve reconstrói o portal na inicializacao e sobe um servidor HTTP
local (apenas stdlib, somente leitura, vinculado a 127.0.0.1) que serve o
portal, os storyboards/covers/formats das entregas, faz streaming dos MP4s
preservados em .workspace/archives/ com suporte a Range e expoe:
  - GET /api/health            -> {"ok": true, "tenants": N, "campaigns": M}
  - GET /api/data              -> portal-data.json atualizado
  - GET /media/storyboard/<tenant>/<slug>  -> preview-storyboard.png
  - GET /media/cover/<tenant>/<slug>       -> cover.png (quando existir)
  - GET /media/formats/<tenant>/<slug>      -> preview-formats.png (idem)
  - GET /media/video/<tenant>/<slug>/<variante> -> MP4 com Range (206/416)
  - GET/POST /api/approvals    -> le/persiste as aprovacoes humanas em
    .workspace/tmp/aprovacoes-titular.json (schema estrito, decisao em
    aguardando/aprovado/ajuste, locucao externa conferida e observacoes)
Todo caminho solicitado e confinado as raizes permitidas (sem "..", sem
caminho absoluto, sem UNC); apenas GET/HEAD sao atendidos, exceto POST em
/api/approvals.

Uso (a partir da raiz do checkout):
    python tools/review_dashboard.py --build [--output-dir 05-review-portal] [--json]
    python tools/review_dashboard.py --serve [--port 8765] [--host 127.0.0.1]
    python tools/review_dashboard.py --export-aprovacoes
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
import re
import subprocess
import sys
import urllib.parse
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import render_local
import tenant_validator

PORTAL_DIR_NAME = "05-review-portal"
DELIVERIES_ROOT = os.path.join("02-reels-shorts", "deliveries")
PACOTES_ROOT = os.path.join("04-legendas", "pacotes-publicacao")
ARCHIVES_ROOT = os.path.join(".workspace", "archives")
ARCHIVES_PREFIX = ARCHIVES_ROOT.replace(os.sep, "/") + "/"
TENANTS_ROOT = "tenants"

APPROVALS_FILENAME = "aprovacoes-titular.json"
APPROVALS_SCHEMA_VERSION = 2
APPROVALS_STORE_REL = ".workspace/tmp/" + APPROVALS_FILENAME
APPROVALS_DECISOES = ("aguardando", "aprovado", "ajuste")
_APPROVALS_DOC_KEYS = {
    "schemaVersion",
    "arquivo",
    "origem",
    "exportadoEm",
    "revisor",
    "resumo",
    "campanhas",
}
_APPROVALS_ITEM_KEYS = {
    "tenantId",
    "slug",
    "campaignId",
    "preset",
    "politicaAudio",
    "decisao",
    "locucaoExternaConferida",
    "observacoes",
    "hashes",
}
_APPROVALS_RESUMO_KEYS = {"totalCampanhas", "aprovadas", "ajustes", "pendentes"}
_MAX_CORPO_POST = 1_000_000

_VARIANTE_RE = re.compile(r"^\d+x\d+$")
_EXPORTADO_EM_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")

COPY_FILES = {
    "instagram": "instagram-reels.md",
    "youtube": "youtube-shorts.md",
    "facebook": "facebook-reels.md",
}

_UTM_RE = re.compile(r"https://[^\s]+utm_[^\s]+")

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".srt": "text/plain; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
}
_DELIVERIES_ALLOWED_EXT = {".png", ".srt", ".txt", ".json", ".md"}


class ReviewPortalError(Exception):
    """Falha controlada do portal de revisao."""


class _AprovacoesInvalidas(Exception):
    """Documento de aprovacoes reprovado na validacao estrita de schema."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(abs_path: str) -> dict:
    with open(render_local.fs_path(abs_path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(abs_path: str) -> str:
    with open(render_local.fs_path(abs_path), "r", encoding="utf-8") as handle:
        return handle.read()


def _sha256_file(abs_path: str) -> str:
    digest = hashlib.sha256()
    with open(render_local.fs_path(abs_path), "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_sha256(abs_path: str, expected: str, label: str) -> None:
    """Confere o SHA-256 de um artefato contra o manifesto; falha fechada."""
    if not os.path.isfile(render_local.fs_path(abs_path)):
        raise ReviewPortalError(f"ARQUIVO_NAO_ENCONTRADO: {label}")
    actual = _sha256_file(abs_path)
    if actual != expected:
        raise ReviewPortalError(
            f"HASH_DIVERGENTE: {label} (esperado {expected}, obtido {actual})"
        )


def _extract_utm_url(text: str) -> str | None:
    """Extrai a primeira URL com parametros UTM de um texto de copy."""
    match = _UTM_RE.search(text)
    if not match:
        return None
    return match.group(0).rstrip(".,;)")


def _rel(root: str, abs_path: str) -> str:
    return render_local.rel(root, abs_path)


def _list_dirs(abs_dir: str) -> list[str]:
    if not os.path.isdir(render_local.fs_path(abs_dir)):
        return []
    return sorted(
        name
        for name in os.listdir(render_local.fs_path(abs_dir))
        if os.path.isdir(render_local.fs_path(os.path.join(abs_dir, name)))
    )


def resolve_workspace_dir(root: str) -> str:
    """Resolve o diretorio .workspace/ aplicavel a raiz de checkout informada.

    .workspace/ nao e versionado: worktrees nao o possuem. Quando a raiz e o
    toplevel de uma worktree (git-dir != git-common-dir), a raiz principal e
    localizada via git rev-parse --git-common-dir e o .workspace/ dela e
    usado (archives de video e aprovacoes do titular). Raizes que nao sao
    toplevel de checkout (raizes falsas de teste, subpastas) usam o proprio
    <raiz>/.workspace.
    """
    proprio = os.path.realpath(os.path.join(root, ".workspace"))
    try:
        saida = subprocess.run(
            ["git", "-C", root, "rev-parse", "--show-toplevel", "--git-common-dir", "--git-dir"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return proprio
    if saida.returncode != 0:
        return proprio
    linhas = [linha.strip() for linha in saida.stdout.strip().splitlines()]
    if len(linhas) < 3 or not all(linhas[:3]):
        return proprio
    toplevel, common, gitdir = linhas[0], linhas[1], linhas[2]
    root_abs = os.path.abspath(root)
    if os.path.normcase(os.path.abspath(toplevel)) != os.path.normcase(root_abs):
        return proprio
    common_abs = os.path.abspath(os.path.join(root_abs, common))
    gitdir_abs = os.path.abspath(os.path.join(root_abs, gitdir))
    if os.path.normcase(common_abs) != os.path.normcase(gitdir_abs):
        principal = os.path.dirname(common_abs)
        candidato = os.path.join(principal, ".workspace")
        if os.path.isdir(render_local.fs_path(candidato)):
            return os.path.realpath(candidato)
    return proprio


def approvals_store_path(root: str) -> str:
    """Caminho do arquivo de aprovacoes dentro do workspace resolvido."""
    return os.path.join(resolve_workspace_dir(root), "tmp", APPROVALS_FILENAME)


def _archives_dir(root: str) -> str:
    return os.path.join(resolve_workspace_dir(root), "archives")


def _variante_primaria(width: int, height: int) -> str:
    """Variante principal derivada da geometria do video."""
    if height > width:
        return "9x16"
    if width > height:
        return "16x9"
    return "1x1"


# ---------------------------------------------------------------------------
# Coleta de dados
# ---------------------------------------------------------------------------

def _collect_tenant(root: str, tenant_id: str) -> dict:
    ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=root, strict=True)
    brand = ctx["brandKit"]
    guardrails = ctx["guardrails"]
    audio_policy = guardrails.get("audioPolicy", {})
    palette = brand.get("palette", {})
    return {
        "tenantId": tenant_id,
        "brandName": brand.get("brandName", tenant_id),
        "displayTitle": brand.get("displayTitle", brand.get("brandName", tenant_id)),
        "monogram": brand.get("monogram", ""),
        "domain": brand.get("domain", ""),
        "tagline": brand.get("tagline", ""),
        "palette": {
            key: palette.get(key, "#121620")
            for key in (
                "primary",
                "secondary",
                "accent",
                "background",
                "surface",
                "textPrimary",
                "textMuted",
            )
        },
        "audioPolicy": {
            "allowAudioTrack": bool(audio_policy.get("allowAudioTrack", False)),
            "ffmpegFlag": audio_policy.get("ffmpegFlag", "-an"),
            "requireSrt": bool(audio_policy.get("requireSrt", True)),
            "requireExternalNarration": bool(
                audio_policy.get("requireExternalNarration", True)
            ),
        },
        "routeRules": guardrails.get("routeRules", {}),
        "forbiddenClaims": list(guardrails.get("forbiddenClaims", [])),
        "forbiddenUiElements": list(guardrails.get("forbiddenUiElements", [])),
    }


def _collect_campaign(root: str, tenant_id: str, slug: str, tenant_ctx_audio: bool) -> dict:
    delivery_dir = os.path.realpath(
        os.path.join(root, DELIVERIES_ROOT, tenant_id, slug)
    )
    if not render_local.contained(root, delivery_dir):
        raise ReviewPortalError(f"DELIVERY_FORA_DA_RAIZ: {tenant_id}/{slug}")
    if not os.path.isdir(render_local.fs_path(delivery_dir)):
        raise ReviewPortalError(f"DELIVERY_NAO_ENCONTRADA: {tenant_id}/{slug}")

    manifest = _load_json(os.path.join(delivery_dir, "manifest.json"))
    artifacts = manifest.get("artifacts", {})

    srt_abs = os.path.join(delivery_dir, f"{slug}.srt")
    narr_abs = os.path.join(delivery_dir, f"{slug}_narracao.txt")
    storyboard_abs = os.path.join(delivery_dir, "preview-storyboard.png")
    _verify_sha256(srt_abs, artifacts["srt"]["sha256"], f"{tenant_id}/{slug} srt")
    _verify_sha256(narr_abs, artifacts["narration"]["sha256"], f"{tenant_id}/{slug} narracao")
    _verify_sha256(
        storyboard_abs, artifacts["storyboard"]["sha256"], f"{tenant_id}/{slug} storyboard"
    )

    campaign_id = slug
    scenes = 0
    config_rel = manifest.get("config")
    if config_rel:
        config_abs = os.path.realpath(os.path.join(root, config_rel.replace("/", os.sep)))
        if render_local.contained(root, config_abs) and os.path.isfile(
            render_local.fs_path(config_abs)
        ):
            config = _load_json(config_abs)
            campaign_id = str(config.get("campaignId", slug))
            scenes = len(config.get("scenes", []))

    video_artifact = artifacts.get("video", {})
    ffprobe = video_artifact.get("ffprobe", {})
    archive_rel = video_artifact.get("archivePath") or _rel(
        root, os.path.join(root, ARCHIVES_ROOT, slug, f"{slug}.mp4")
    )

    copies: dict[str, dict] | None = None
    pacote: dict | None = None
    pacote_dir = os.path.realpath(os.path.join(root, PACOTES_ROOT, tenant_id, slug))
    if os.path.isdir(render_local.fs_path(pacote_dir)):
        copies = {}
        for channel, filename in COPY_FILES.items():
            copy_abs = os.path.join(pacote_dir, filename)
            text = _read_text(copy_abs) if os.path.isfile(render_local.fs_path(copy_abs)) else ""
            copies[channel] = {
                "relPath": _rel(root, copy_abs),
                "text": text,
                "utmUrl": _extract_utm_url(text),
            }
        checklist_abs = os.path.join(pacote_dir, "checklist-publicacao.json")
        checklist = (
            _load_json(checklist_abs)
            if os.path.isfile(render_local.fs_path(checklist_abs))
            else {}
        )
        pacote = {
            "checklistRelPath": _rel(root, checklist_abs),
            "guardrailsAudited": bool(checklist.get("guardrailsAudited", False)),
            "guardrailStatus": checklist.get("guardrailStatus", {}),
            "autoPublish": bool(checklist.get("autoPublish", False)),
        }

    derivatives = _coletar_derivatives(delivery_dir, tenant_id, slug)
    cover = _coletar_png_opcional(root, delivery_dir, "cover.png")
    formats = _coletar_png_opcional(root, delivery_dir, "preview-formats.png")

    fmt = manifest.get("format", {})
    primaria = _variante_primaria(int(fmt.get("width", 0)), int(fmt.get("height", 0)))
    variants = [primaria]
    for deriv in derivatives or []:
        if deriv["variant"] not in variants:
            variants.append(deriv["variant"])

    titulo = campaign_id
    if copies and copies.get("instagram", {}).get("text"):
        for linha in copies["instagram"]["text"].splitlines():
            if linha.strip():
                titulo = linha.strip()
                break

    return {
        "tenantId": tenant_id,
        "slug": slug,
        "campaignId": campaign_id,
        "titulo": titulo,
        "preset": manifest.get("preset", ""),
        "politicaAudio": "AAC" if tenant_ctx_audio else "-an",
        "audioStreams": int(ffprobe.get("audioStreams", 0)),
        "format": {
            "width": fmt.get("width", 0),
            "height": fmt.get("height", 0),
            "fps": fmt.get("fps", 0),
            "duration": fmt.get("duration", 0.0),
        },
        "scenes": scenes,
        "video": {
            "archiveRelPath": archive_rel,
            "sha256": video_artifact.get("sha256", ""),
            "bytes": int(video_artifact.get("bytes", 0)),
            "audioStreams": int(ffprobe.get("audioStreams", 0)),
            "audioCodec": ffprobe.get("audioCodec"),
            "variants": variants,
        },
        "srt": {
            "relPath": _rel(root, srt_abs),
            "sha256": artifacts["srt"]["sha256"],
            "bytes": os.path.getsize(render_local.fs_path(srt_abs)),
            "text": _read_text(srt_abs),
        },
        "narracao": {
            "relPath": _rel(root, narr_abs),
            "sha256": artifacts["narration"]["sha256"],
            "bytes": os.path.getsize(render_local.fs_path(narr_abs)),
            "text": _read_text(narr_abs),
        },
        "storyboard": {
            "relPath": _rel(root, storyboard_abs),
            "sha256": artifacts["storyboard"]["sha256"],
            "bytes": os.path.getsize(render_local.fs_path(storyboard_abs)),
            "timestampsSeconds": artifacts["storyboard"].get("timestampsSeconds", []),
        },
        "cover": cover,
        "formats": formats,
        "derivatives": derivatives,
        "copies": copies,
        "pacote": pacote,
    }


def _coletar_derivatives(delivery_dir: str, tenant_id: str, slug: str) -> list[dict] | None:
    """Le derivatives.json opcional da entrega (variantes 1x1/16x9 etc.).

    Formato esperado: {"schemaVersion": 1, "derivatives": [{"variant": "1x1",
    "path": "<slug>-1x1.mp4", "sha256": "...", "bytes": N}]} com path
    relativo ao diretorio do slug em .workspace/archives/. Malformado aborta
    o build (fail-closed).
    """
    caminho = os.path.join(delivery_dir, "derivatives.json")
    if not os.path.isfile(render_local.fs_path(caminho)):
        return None
    doc = _load_json(caminho)
    itens = doc.get("derivatives") if isinstance(doc, dict) else None
    if not isinstance(itens, list):
        raise ReviewPortalError(
            f"DERIVATIVOS_INVALIDOS: {tenant_id}/{slug} (lista 'derivatives' ausente)"
        )
    sane: list[dict] = []
    for item in itens:
        if not isinstance(item, dict):
            raise ReviewPortalError(
                f"DERIVATIVOS_INVALIDOS: {tenant_id}/{slug} (item nao objeto)"
            )
        variante = str(item.get("variant", ""))
        path = str(item.get("path", ""))
        if (
            not _VARIANTE_RE.match(variante)
            or not path
            or ".." in path
            or "\\" in path
            or path.startswith("/")
        ):
            raise ReviewPortalError(
                f"DERIVATIVOS_INVALIDOS: {tenant_id}/{slug} (variant/path)"
            )
        sane.append(
            {
                "variant": variante,
                "path": path,
                "sha256": str(item.get("sha256", "")),
                "bytes": int(item.get("bytes", 0)),
            }
        )
    return sane


def _coletar_png_opcional(root: str, delivery_dir: str, filename: str) -> dict | None:
    """Hasheia um PNG opcional da entrega (cover.png, preview-formats.png)."""
    caminho = os.path.join(delivery_dir, filename)
    if not os.path.isfile(render_local.fs_path(caminho)):
        return None
    return {
        "relPath": _rel(root, caminho),
        "sha256": _sha256_file(caminho),
        "bytes": os.path.getsize(render_local.fs_path(caminho)),
    }


def _collect_data(root: str) -> tuple[dict, dict]:
    tenants: list[dict] = []
    campaigns: list[dict] = []
    videos_found = 0
    videos_missing = 0

    for tenant_id in _list_dirs(os.path.join(root, TENANTS_ROOT)):
        brand_kit = os.path.join(root, TENANTS_ROOT, tenant_id, "brand-kit.json")
        if not os.path.isfile(render_local.fs_path(brand_kit)):
            continue
        tenant = _collect_tenant(root, tenant_id)
        tenants.append(tenant)
        for slug in _list_dirs(os.path.join(root, DELIVERIES_ROOT, tenant_id)):
            manifest_probe = os.path.join(
                root, DELIVERIES_ROOT, tenant_id, slug, "manifest.json"
            )
            if not os.path.isfile(render_local.fs_path(manifest_probe)):
                continue
            campaign = _collect_campaign(
                root, tenant_id, slug, tenant["audioPolicy"]["allowAudioTrack"]
            )
            campaigns.append(campaign)
            video_abs = os.path.realpath(
                os.path.join(root, campaign["video"]["archiveRelPath"].replace("/", os.sep))
            )
            if render_local.contained(root, video_abs) and os.path.isfile(
                render_local.fs_path(video_abs)
            ):
                videos_found += 1
            else:
                videos_missing += 1

    data = {
        "schemaVersion": 1,
        "generatedBy": "tools/review_dashboard.py",
        "deliveriesRoot": DELIVERIES_ROOT.replace(os.sep, "/"),
        "pacotesRoot": PACOTES_ROOT.replace(os.sep, "/"),
        "archivesRoot": ARCHIVES_ROOT.replace(os.sep, "/"),
        "totals": {"tenants": len(tenants), "campaigns": len(campaigns)},
        "tenants": tenants,
        "campaigns": campaigns,
    }
    stats = {"encontrados": videos_found, "ausentes": videos_missing}
    return data, stats


# ---------------------------------------------------------------------------
# Geracao do portal
# ---------------------------------------------------------------------------

def build_portal(root: str = ".", output_dir: str | None = None) -> dict:
    """Gera index.html, portal-data.json e README.md. Devolve o resumo."""
    root_real = os.path.realpath(root)
    if not os.path.isdir(render_local.fs_path(root_real)):
        raise ReviewPortalError(f"RAIZ_INVALIDA: {root}")
    out_rel = output_dir or PORTAL_DIR_NAME
    out_abs = os.path.realpath(os.path.join(root_real, out_rel))
    if not render_local.contained(root_real, out_abs):
        raise ReviewPortalError(f"SAIDA_FORA_DA_RAIZ: {out_rel}")
    os.makedirs(render_local.fs_path(out_abs), exist_ok=True)

    data, stats = _collect_data(root_real)

    payload_json = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    html = render_index_html(data)
    readme = _render_readme(data)

    conteudos = {
        "portal-data.json": payload_json,
        "index.html": html,
        "README.md": readme,
    }
    files: dict[str, dict] = {}
    for filename, conteudo in conteudos.items():
        abs_path = os.path.join(out_abs, filename)
        with open(render_local.fs_path(abs_path), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(conteudo)
        files[filename] = {
            "path": _rel(root_real, abs_path),
            "sha256": _sha256_file(abs_path),
            "bytes": os.path.getsize(render_local.fs_path(abs_path)),
        }

    return {
        "ok": True,
        "outputDir": _rel(root_real, out_abs),
        "totalTenants": data["totals"]["tenants"],
        "totalCampaigns": data["totals"]["campaigns"],
        "tenants": [t["tenantId"] for t in data["tenants"]],
        "campaigns": [
            {
                "tenantId": c["tenantId"],
                "slug": c["slug"],
                "preset": c["preset"],
                "politicaAudio": c["politicaAudio"],
            }
            for c in data["campaigns"]
        ],
        "videosLocais": stats,
        "files": files,
    }


def _render_readme(data: dict) -> str:
    tenants_lista = ", ".join(t["tenantId"] for t in data["tenants"])
    return f"""# Portal de Revisão — Content Factory Multi-Tenant

Portal estático de revisão humana das campanhas renderizadas pela fábrica
multi-tenant. Consolidado por `tools/review_dashboard.py` a partir de:

- `tenants/*/brand-kit.json` e `tenants/*/guardrails.json`
- `02-reels-shorts/deliveries/<tenant>/<slug>/` (`manifest.json`, `<slug>.srt`,
  `<slug>_narracao.txt`, `preview-storyboard.png` e, quando existirem,
  `cover.png`, `preview-formats.png` e `derivatives.json`)
- `04-legendas/pacotes-publicacao/<tenant>/<slug>/`
  (`checklist-publicacao.json` e copies por rede)

Estado consolidado nesta geração: **{data['totals']['tenants']} tenants**
({tenants_lista}) e **{data['totals']['campaigns']} campanhas**.

## Gerar

```
python tools/review_dashboard.py --build [--json]
```

Gera `index.html`, `portal-data.json` e este `README.md`. O build é
**determinístico**: não grava timestamps e produz bytes idênticos para os
mesmos insumos, em qualquer estação. Hashes SHA-256 de SRT, narração e
storyboard são verificados contra o `manifest.json` de cada entrega; qualquer
divergência aborta o build com `HASH_DIVERGENTE`. `portal-data.json` contém
apenas caminhos relativos contidos na raiz (nenhum caminho absoluto de
estação), mantendo o portal portátil.

## Servir (recomendado)

```
python tools/review_dashboard.py --serve [--port 8765] [--host 127.0.0.1]
```

Reconstrói o portal na inicialização e sobe um servidor HTTP local em
`http://127.0.0.1:8765/` (somente leitura, vinculado a 127.0.0.1, sem
dependências externas). Endpoints:

- `GET /` e `GET /portal-data.json` — o portal e seus dados.
- `GET /api/health` — `{{"ok": true, "tenants": N, "campaigns": M}}`.
- `GET /api/data` — `portal-data.json` atualizado.
- `GET /media/storyboard/<tenant>/<slug>` — `preview-storyboard.png`.
- `GET /media/cover/<tenant>/<slug>` e `GET /media/formats/<tenant>/<slug>`
  — `cover.png` e `preview-formats.png`, quando existirem na entrega.
- `GET /media/video/<tenant>/<slug>/<variante>` — streaming do MP4 preservado
  em `.workspace/archives/<slug>/` (variante primária derivada da geometria;
  derivadas `1x1`/`16x9` via `derivatives.json` ou convenção de nomes), com
  suporte a `Range` (206/416).
- `GET/POST /api/approvals` — lê e persiste as decisões do titular em
  `.workspace/tmp/aprovacoes-titular.json` (schema estrito v2: decisão em
  `aguardando`/`aprovado`/`ajuste`, locução externa conferida, observações e
  hashes SHA-256).

## Exportar aprovações

```
python tools/review_dashboard.py --export-aprovacoes
```

Emite no stdout o conteúdo atual de `aprovacoes-titular.json` (schema v2)
para redirecionar a um arquivo ou anexar ao handoff. Sem arquivo persistido,
encerra com `APROVACOES_AUSENTES`.

## Interface

- **Painel de métricas:** nichos, campanhas, vídeos `-an` × `AAC`,
  conformidade de guardrails e contadores dinâmicos de aprovados, pendentes
  e ajustes.
- **Filtros e busca:** tenant (com monograma e cor), preset, política de
  áudio, status de aprovação e busca textual por slug, título, legenda,
  roteiro ou rota.
- **Cartões por campanha:** paleta do tenant, storyboard 2×2 (com lightbox),
  player por variante quando servido, abas **Legenda .srt** (blocos numerados
  com timecodes), **Narração**, **Instagram/YouTube/Facebook** (copy completa,
  contador de caracteres, URL UTM destacada e botões Copiar) e
  **Guardrails & Hashes** (rotas autorizadas, claims bloqueados,
  `autoPublish: false` e hashes SHA-256).
- **Controle editorial:** decisão por campanha (Aguardando Revisão, Aprovado
  para Publicação Manual, Solicitar Ajuste), conferência de locução externa
  para tenants `-an` e observações do titular — salvos no `localStorage`
  (chave `reviewPortal.aprovacoes.v2`) e sincronizados via
  `POST /api/approvals` quando o portal é servido.
- **Exportar/Importar:** botões que baixam `aprovacoes-titular.json` e
  reimportam um JSON de aprovações.

## Segurança do servidor

- Somente `GET`/`HEAD`; métodos de escrita são recusados, exceto
  `POST /api/approvals` (validação estrita de schema, corpo limitado a 1 MB).
- Rotas restritas: portal, `/api/*`, `/media/*`, `/deliveries/<caminho>`
  (PNG/SRT/TXT/JSON/MD das entregas) e `/archives/<slug>/<arquivo>.mp4`
  (legado, com `Range`).
- Todo caminho é decodificado e confinado à raiz permitida: `..`, `\\`,
  caminhos absolutos e UNC recebem 404; extensões fora da lista permitida
  também são recusadas.
- Os MP4s **não são versionados** (`.workspace/archives/` é local por
  estação): quando a raiz é uma worktree, o servidor localiza a raiz
  principal via `git rev-parse --git-common-dir` para alcançar os vídeos;
  se o arquivo não existir na estação, o player cai no storyboard com aviso.
"""


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Portal de Revisão — Content Factory Multi-Tenant</title>
<style>
:root{--bg:#0d1117;--surface:#161b22;--border:#30363d;--text:#e6edf3;--muted:#8b949e;--ok:#2ea043;--warn:#d29922;--info:#1f6feb;--danger:#f85149}
*{box-sizing:border-box}
body{margin:0;font-family:"Segoe UI",Arial,sans-serif;background:var(--bg);color:var(--text)}
header{padding:16px 22px;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg);z-index:20}
h1{margin:0 0 2px;font-size:19px}
.sub{margin:0 0 10px;color:var(--muted);font-size:13px}
.metricas{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.metrica{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:6px 12px;min-width:104px}
.metrica-valor{display:block;font-size:17px;font-weight:700}
.metrica-rotulo{display:block;font-size:11px;color:var(--muted)}
.filtros{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.filtros label{font-size:12px;color:var(--muted);display:flex;gap:6px;align-items:center}
select,button,input,textarea{background:#0b0f14;color:var(--text);border:1px solid var(--border);border-radius:6px;padding:6px 10px;font-size:13px;font-family:inherit}
button{cursor:pointer}
button:hover{border-color:#58a6ff}
button.desabilitado{opacity:.45;cursor:not-allowed}
#busca{min-width:240px}
.swatch{width:16px;height:16px;border-radius:4px;border:1px solid var(--border);display:inline-block;flex:none}
#btn-exportar-aprovacoes{background:var(--info);border-color:var(--info);font-weight:600;color:#fff}
#btn-importar-aprovacoes{background:var(--ok);border-color:var(--ok);font-weight:600;color:#fff}
main{padding:18px 22px;display:grid;grid-template-columns:repeat(auto-fill,minmax(460px,1fr));gap:16px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden;display:flex;flex-direction:column}
.card-head{padding:10px 14px;border-bottom:1px solid var(--border);border-left:4px solid var(--c-primary);display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.monogram{width:30px;height:30px;border-radius:8px;background:var(--c-primary);color:#0b0f14;font-weight:700;display:flex;align-items:center;justify-content:center;font-size:13px;flex:none}
.card-titulo{display:flex;flex-direction:column;margin-right:auto;min-width:180px}
.card-titulo strong{font-size:14px}
.card-titulo span{font-size:11px;color:var(--muted)}
.chip{font-size:11px;padding:2px 8px;border-radius:10px;border:1px solid var(--border);color:var(--muted)}
.chip.audio-an{background:rgba(31,111,235,.12);color:#58a6ff;border-color:#1f6feb}
.chip.audio-aac{background:rgba(46,160,67,.15);color:#3fb950;border-color:#2ea043}
.chip.status.aguardando{background:rgba(210,153,34,.15);color:#d29922;border-color:#9e6a03}
.chip.status.aprovado{background:rgba(46,160,67,.2);color:#3fb950;border-color:#2ea043}
.chip.status.ajuste{background:rgba(248,81,73,.15);color:#f85149;border-color:#da3633}
.card-media{padding:10px 14px 0;display:flex;flex-direction:column;gap:6px}
.viewer img,.viewer video{width:100%;max-height:430px;object-fit:contain;background:#000;border-radius:8px;display:block}
.viewer img{cursor:zoom-in}
.modo-botoes{display:flex;gap:6px;flex-wrap:wrap}
.nota{font-size:11px;color:var(--muted)}
.abas{display:flex;gap:4px;padding:10px 14px 0;flex-wrap:wrap}
.aba{padding:5px 10px;font-size:12px;border-radius:6px 6px 0 0;color:var(--muted)}
.aba.ativa{color:var(--text);background:#0b0f14}
.aba-conteudo{margin:0 14px;border:1px solid var(--border);border-radius:0 8px 8px 8px;padding:10px;background:#0b0f14;max-height:340px;overflow:auto}
.aba-conteudo pre{margin:0 0 8px;white-space:pre-wrap;font-size:12px;font-family:Consolas,monospace}
.srt-bloco{border-bottom:1px dashed var(--border);padding:4px 0}
.srt-tempo{font-size:11px;color:#58a6ff;font-family:Consolas,monospace}
.srt-texto{font-size:12px;white-space:pre-wrap}
.linha-acoes{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.linha-acoes a{color:#58a6ff;font-size:12px;text-decoration:none;word-break:break-all}
.contador{font-size:11px;color:var(--muted)}
.utm-box{border:1px solid var(--border);border-left:3px solid var(--ok);border-radius:6px;padding:6px 8px;margin:0 0 8px;font-size:12px;word-break:break-all}
.guardrails-lista{margin:4px 0 10px;padding-left:18px;font-size:12px}
.hash-linha{font-family:Consolas,monospace;font-size:11px;word-break:break-all;color:var(--muted);margin:2px 0}
.aprovacao{padding:12px 14px;border-top:1px solid var(--border);display:flex;flex-direction:column;gap:8px}
.aprovacao .linha{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
.aprovacao label{font-size:12px;color:var(--muted);display:flex;gap:6px;align-items:center}
.aprovacao textarea{width:100%}
footer{padding:14px 22px;color:var(--muted);font-size:12px}
#vazio{text-align:center;color:var(--muted);padding:30px}
#lightbox{position:fixed;inset:0;background:rgba(0,0,0,.88);display:flex;align-items:center;justify-content:center;z-index:50}
#lightbox[hidden]{display:none}
#lightbox img{max-width:96vw;max-height:92vh;object-fit:contain;border-radius:8px}
#lightbox button{position:fixed;top:14px;right:14px}
</style>
</head>
<body>
<header>
  <h1>Portal de Revisão — Content Factory Multi-Tenant</h1>
  <p class="sub"><span id="sub-titulo"></span> · <span id="contagem"></span> · <span id="badge-servidor"></span></p>
  <div id="painel-metricas" class="metricas">
    <div class="metrica"><span class="metrica-valor" id="metrica-nichos">—</span><span class="metrica-rotulo">Nichos</span></div>
    <div class="metrica"><span class="metrica-valor" id="metrica-campanhas">—</span><span class="metrica-rotulo">Campanhas</span></div>
    <div class="metrica"><span class="metrica-valor" id="metrica-videos-an">—</span><span class="metrica-rotulo">Vídeos -an</span></div>
    <div class="metrica"><span class="metrica-valor" id="metrica-videos-aac">—</span><span class="metrica-rotulo">Vídeos AAC</span></div>
    <div class="metrica"><span class="metrica-valor" id="metrica-guardrails">—</span><span class="metrica-rotulo">Guardrails</span></div>
    <div class="metrica"><span class="metrica-valor" id="metrica-aprovados">—</span><span class="metrica-rotulo">Aprovados</span></div>
    <div class="metrica"><span class="metrica-valor" id="metrica-pendentes">—</span><span class="metrica-rotulo">Pendentes</span></div>
    <div class="metrica"><span class="metrica-valor" id="metrica-ajustes">—</span><span class="metrica-rotulo">Ajustes</span></div>
  </div>
  <div class="filtros">
    <label>Tenant <select id="filtro-tenant"><option value="">Todos</option></select></label>
    <span id="swatch-tenant" class="swatch" title="Cor do tenant selecionado"></span>
    <label>Preset <select id="filtro-preset"><option value="">Todos</option><option value="saas-demo">saas-demo</option><option value="shorts-completo">shorts-completo</option></select></label>
    <label>Áudio <select id="filtro-audio"><option value="">Todos</option><option value="-an">-an (sem áudio)</option><option value="AAC">AAC (com áudio)</option></select></label>
    <label>Status <select id="filtro-status"><option value="">Todos</option><option value="aguardando">Aguardando Revisão</option><option value="aprovado">Aprovado para Publicação Manual</option><option value="ajuste">Solicitar Ajuste</option></select></label>
    <input id="busca" type="search" placeholder="Buscar slug, título, legenda, roteiro ou rota">
    <label>Revisor <input id="input-revisor" type="text" placeholder="Revisor"></label>
    <button id="btn-exportar-aprovacoes" type="button">Exportar aprovacoes-titular.json</button>
    <button id="btn-importar-aprovacoes" type="button">Importar JSON</button>
    <input id="input-importar" type="file" accept=".json,application/json" hidden>
  </div>
</header>
<main id="grid"></main>
<p id="vazio" hidden>Nenhuma campanha corresponde aos filtros.</p>
<div id="lightbox" hidden>
  <button id="lightbox-fechar" type="button">Fechar</button>
  <img id="lightbox-img" alt="Prévia ampliada">
</div>
<footer>Portal de Revisão gerado por <code>tools/review_dashboard.py</code> · Decisões persistem no <code>localStorage</code> (reviewPortal.aprovacoes.v2) e sincronizam via <code>/api/approvals</code> quando servido · Vídeos são servidos de <code>.workspace/archives/</code> (local por estação).</footer>
<script id="portal-data" type="application/json">__PORTAL_DATA__</script>
<script>
"use strict";
const DATA = JSON.parse(document.getElementById("portal-data").textContent);
const SERVIDO = location.protocol === "http:" || location.protocol === "https:";
const LS_KEY = "reviewPortal.aprovacoes.v2";
const DECISOES = {
  aguardando: "Aguardando Revisão",
  aprovado: "Aprovado para Publicação Manual",
  ajuste: "Solicitar Ajuste"
};
const ABAS = [
  ["srt", "Legenda .srt"],
  ["narracao", "Narração"],
  ["instagram", "Instagram"],
  ["youtube", "YouTube"],
  ["facebook", "Facebook"],
  ["guardrails", "Guardrails & Hashes"]
];

function normalizar(texto) {
  return String(texto || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function el(tag, attrs, children) {
  const node = document.createElement(tag);
  if (attrs) {
    Object.keys(attrs).forEach(function (k) {
      if (k === "class") { node.className = attrs[k]; }
      else if (k === "text") { node.textContent = attrs[k]; }
      else if (k.indexOf("on") === 0) { node.addEventListener(k.slice(2), attrs[k]); }
      else { node.setAttribute(k, attrs[k]); }
    });
  }
  (children || []).forEach(function (ch) { node.appendChild(ch); });
  return node;
}

function carregarEstado() {
  try {
    const st = JSON.parse(localStorage.getItem(LS_KEY) || "{}");
    if (st && typeof st === "object") { return st; }
  } catch (e) { /* estado corrompido: recomeca vazio */ }
  return {};
}
function salvarEstado(estado) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(estado)); }
  catch (e) { /* localStorage indisponivel: segue sem persistencia */ }
}
function chaveCampanha(c) { return c.tenantId + "/" + c.slug; }
function estadoCampanha(c) {
  const item = (carregarEstado().campanhas || {})[chaveCampanha(c)];
  return {
    decisao: item && DECISOES[item.decisao] ? item.decisao : "aguardando",
    locucaoExternaConferida: !!(item && item.locucaoExternaConferida),
    observacoes: item && item.observacoes ? item.observacoes : ""
  };
}
function registrar(c, campo, valor) {
  const estado = carregarEstado();
  estado.campanhas = estado.campanhas || {};
  const chave = chaveCampanha(c);
  const item = estado.campanhas[chave] || { decisao: "aguardando", locucaoExternaConferida: false, observacoes: "" };
  item[campo] = valor;
  estado.campanhas[chave] = item;
  salvarEstado(estado);
  agendarSync();
  atualizarPainel();
}
function registrarRevisor(nome) {
  const estado = carregarEstado();
  estado.revisor = nome;
  salvarEstado(estado);
  agendarSync();
}

function docAprovacoes() {
  const estado = carregarEstado();
  const campanhas = DATA.campaigns.map(function (c) {
    const e = estadoCampanha(c);
    return {
      tenantId: c.tenantId,
      slug: c.slug,
      campaignId: c.campaignId,
      preset: c.preset,
      politicaAudio: c.politicaAudio,
      decisao: e.decisao,
      locucaoExternaConferida: e.locucaoExternaConferida,
      observacoes: e.observacoes,
      hashes: {
        video: c.video.sha256,
        srt: c.srt.sha256,
        narracao: c.narracao.sha256,
        storyboard: c.storyboard.sha256
      }
    };
  });
  const resumo = { totalCampanhas: campanhas.length, aprovadas: 0, ajustes: 0, pendentes: 0 };
  campanhas.forEach(function (k) {
    if (k.decisao === "aprovado") { resumo.aprovadas += 1; }
    else if (k.decisao === "ajuste") { resumo.ajustes += 1; }
    else { resumo.pendentes += 1; }
  });
  return {
    schemaVersion: 2,
    arquivo: "aprovacoes-titular.json",
    origem: "05-review-portal",
    exportadoEm: new Date().toISOString(),
    revisor: typeof estado.revisor === "string" ? estado.revisor : "",
    resumo: resumo,
    campanhas: campanhas
  };
}

let syncTimer = null;
function agendarSync() {
  if (!SERVIDO) { return; }
  if (syncTimer) { clearTimeout(syncTimer); }
  syncTimer = setTimeout(sincronizar, 800);
}
function sincronizar() {
  if (!SERVIDO) { return; }
  fetch("/api/approvals", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(docAprovacoes())
  }).catch(function () { /* servidor fora do ar: localStorage segue como fonte */ });
}

function exportarAprovacoes() {
  const blob = new Blob([JSON.stringify(docAprovacoes(), null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "aprovacoes-titular.json";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}
function importarAprovacoes(arquivo) {
  const leitor = new FileReader();
  leitor.onload = function () {
    let doc = null;
    try { doc = JSON.parse(String(leitor.result)); }
    catch (e) { window.alert("Arquivo nao e um JSON valido."); return; }
    if (!doc || typeof doc !== "object" || !Array.isArray(doc.campanhas)) {
      window.alert("Documento sem a lista de campanhas.");
      return;
    }
    const estado = carregarEstado();
    estado.campanhas = estado.campanhas || {};
    if (typeof doc.revisor === "string") {
      estado.revisor = doc.revisor;
      document.getElementById("input-revisor").value = doc.revisor;
    }
    doc.campanhas.forEach(function (item) {
      if (!item || typeof item !== "object") { return; }
      const alvo = DATA.campaigns.filter(function (c) {
        return c.tenantId === item.tenantId && c.slug === item.slug;
      })[0];
      if (!alvo) { return; }
      estado.campanhas[chaveCampanha(alvo)] = {
        decisao: DECISOES[item.decisao] ? item.decisao : "aguardando",
        locucaoExternaConferida: !!item.locucaoExternaConferida,
        observacoes: typeof item.observacoes === "string" ? item.observacoes : ""
      };
    });
    salvarEstado(estado);
    agendarSync();
    render();
  };
  leitor.readAsText(arquivo);
}

function urlStoryboard(c) {
  return SERVIDO ? "/media/storyboard/" + c.tenantId + "/" + c.slug : "../" + c.storyboard.relPath;
}
function urlCover(c) {
  return SERVIDO ? "/media/cover/" + c.tenantId + "/" + c.slug : "../" + c.cover.relPath;
}
function urlFormats(c) {
  return SERVIDO ? "/media/formats/" + c.tenantId + "/" + c.slug : "../" + c.formats.relPath;
}
function urlVideo(c, variante) {
  return "/media/video/" + c.tenantId + "/" + c.slug + "/" + variante;
}

function copiar(texto, botao) {
  function concluido() {
    const antigo = botao.textContent;
    botao.textContent = "Copiado!";
    setTimeout(function () { botao.textContent = antigo; }, 1500);
  }
  function alternativa() {
    const ta = document.createElement("textarea");
    ta.value = texto;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); concluido(); }
    catch (e) { window.prompt("Copie manualmente:", texto); }
    document.body.removeChild(ta);
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(texto).then(concluido).catch(alternativa);
  } else { alternativa(); }
}
function blocosSrt(texto) {
  const blocos = [];
  String(texto || "").replace(/\r\n/g, "\n").split(/\n\s*\n/).forEach(function (bruto) {
    const linhas = bruto.split("\n").filter(function (l) { return l.trim() !== ""; });
    if (linhas.length >= 2) {
      blocos.push({ numero: linhas[0], tempo: linhas[1], texto: linhas.slice(2).join("\n") });
    }
  });
  return blocos;
}

function painelGuardrails(c) {
  const tenant = DATA.tenants.filter(function (t) { return t.tenantId === c.tenantId; })[0] || {};
  const painel = el("div", { class: "aba-conteudo" });
  painel.appendChild(el("strong", { text: "Rotas autorizadas" }));
  const rotas = el("ul", { class: "guardrails-lista" });
  Object.keys(tenant.routeRules || {}).forEach(function (rota) {
    rotas.appendChild(el("li", { text: rota }));
  });
  painel.appendChild(rotas);
  painel.appendChild(el("strong", { text: "Claims bloqueados" }));
  const claims = el("ul", { class: "guardrails-lista" });
  (tenant.forbiddenClaims || []).forEach(function (claim) {
    claims.appendChild(el("li", { text: claim }));
  });
  painel.appendChild(claims);
  painel.appendChild(el("p", {
    class: "nota",
    text: "autoPublish: " + (c.pacote && c.pacote.autoPublish ? "true" : "false")
      + " · guardrailsAudited: " + (c.pacote && c.pacote.guardrailsAudited ? "true" : "false")
  }));
  painel.appendChild(el("strong", { text: "Hashes SHA-256" }));
  [["video", c.video.sha256], ["srt", c.srt.sha256], ["narracao", c.narracao.sha256], ["storyboard", c.storyboard.sha256]].forEach(function (par) {
    painel.appendChild(el("div", { class: "hash-linha", text: par[0] + ": " + par[1] }));
  });
  return painel;
}

function painelAba(c, aba) {
  if (aba === "guardrails") { return painelGuardrails(c); }
  const painel = el("div", { class: "aba-conteudo" });
  if (aba === "srt") {
    blocosSrt(c.srt.text).forEach(function (b) {
      const bloco = el("div", { class: "srt-bloco" });
      bloco.appendChild(el("div", { class: "srt-tempo", text: "#" + b.numero + " · " + b.tempo }));
      bloco.appendChild(el("div", { class: "srt-texto", text: b.texto }));
      painel.appendChild(bloco);
    });
    const botaoSrt = el("button", { type: "button", text: "Copiar Texto" });
    botaoSrt.addEventListener("click", function () { copiar(c.srt.text, botaoSrt); });
    painel.appendChild(el("div", { class: "linha-acoes" }, [botaoSrt]));
    return painel;
  }
  if (aba === "narracao") {
    const botaoNarr = el("button", { type: "button", text: "Copiar Texto" });
    botaoNarr.addEventListener("click", function () { copiar(c.narracao.text, botaoNarr); });
    painel.appendChild(el("pre", { text: c.narracao.text }));
    painel.appendChild(el("div", { class: "linha-acoes" }, [botaoNarr]));
    return painel;
  }
  const copy = c.copies ? c.copies[aba] : null;
  if (!copy || !copy.text) {
    painel.appendChild(el("p", { class: "nota", text: "Pacote de publicação não gerado para esta campanha." }));
    return painel;
  }
  if (copy.utmUrl) {
    painel.appendChild(el("div", { class: "utm-box", text: "URL UTM: " + copy.utmUrl }));
  }
  painel.appendChild(el("pre", { text: copy.text }));
  const botaoCopy = el("button", { type: "button", text: "Copiar Copy" });
  botaoCopy.addEventListener("click", function () { copiar(copy.text, botaoCopy); });
  const acoes = el("div", { class: "linha-acoes" }, [
    el("span", { class: "contador", text: copy.text.length + " caracteres" }),
    botaoCopy
  ]);
  if (copy.utmUrl) {
    const botaoUrl = el("button", { type: "button", text: "Copiar URL UTM" });
    botaoUrl.addEventListener("click", function () { copiar(copy.utmUrl, botaoUrl); });
    acoes.appendChild(botaoUrl);
    acoes.appendChild(el("a", { href: copy.utmUrl, target: "_blank", rel: "noopener", text: copy.utmUrl }));
  }
  painel.appendChild(acoes);
  return painel;
}

function abrirLightbox(src) {
  document.getElementById("lightbox-img").src = src;
  document.getElementById("lightbox").hidden = false;
}
function fecharLightbox() {
  document.getElementById("lightbox").hidden = true;
  document.getElementById("lightbox-img").src = "";
}

function card(c) {
  const tenant = DATA.tenants.filter(function (t) { return t.tenantId === c.tenantId; })[0] || { palette: {} };
  const cardEl = el("article", { class: "card" });
  cardEl.style.setProperty("--c-primary", (tenant.palette && tenant.palette.primary) || "#1f6feb");

  const chipStatus = el("span", { class: "chip status aguardando" });
  function atualizarChip() {
    const e = estadoCampanha(c);
    chipStatus.textContent = DECISOES[e.decisao];
    chipStatus.className = "chip status " + e.decisao;
  }

  const cabecalho = el("div", { class: "card-head" }, [
    el("div", { class: "monogram", text: tenant.monogram || "" }),
    el("div", { class: "card-titulo" }, [
      el("strong", { text: c.titulo }),
      el("span", { text: c.slug + " · " + (tenant.domain || "") })
    ]),
    el("span", { class: "chip", text: c.preset }),
    el("span", { class: "chip", text: c.format.width + "x" + c.format.height + " @ " + c.format.fps + "fps · " + c.format.duration + "s · " + c.scenes + " cenas" }),
    el("span", {
      class: "chip " + (c.politicaAudio === "AAC" ? "audio-aac" : "audio-an"),
      text: c.politicaAudio === "AAC" ? "ÁUDIO AAC" : "SEM ÁUDIO (-an)"
    }),
    chipStatus
  ]);
  atualizarChip();
  cardEl.appendChild(cabecalho);

  const media = el("div", { class: "card-media" });
  const modos = el("div", { class: "modo-botoes" });
  const viewer = el("div", { class: "viewer" });
  function imgStoryboard() {
    const img = el("img", { src: urlStoryboard(c), alt: "Storyboard 2x2 da campanha " + c.slug });
    img.addEventListener("click", function () { abrirLightbox(img.src); });
    return img;
  }
  function mostrarStoryboard() { viewer.replaceChildren(imgStoryboard()); }
  function mostrarPlayer(variante) {
    if (!SERVIDO) { return; }
    const video = el("video", { controls: "", preload: "metadata" });
    video.poster = urlStoryboard(c);
    video.addEventListener("error", function () {
      viewer.replaceChildren(
        imgStoryboard(),
        el("p", { class: "nota", text: "MP4 não disponível nesta estação (.workspace/archives é local por estação)." })
      );
    });
    video.src = urlVideo(c, variante);
    viewer.replaceChildren(video);
  }
  const botaoStoryboard = el("button", { type: "button", text: "Storyboard 2x2" });
  botaoStoryboard.addEventListener("click", mostrarStoryboard);
  modos.appendChild(botaoStoryboard);
  (c.video.variants || []).forEach(function (variante) {
    const botao = el("button", { type: "button", text: "Player " + variante.replace("x", ":") });
    if (!SERVIDO) {
      botao.className = "desabilitado";
      botao.title = "Disponível apenas com --serve";
    }
    botao.addEventListener("click", function () { mostrarPlayer(variante); });
    modos.appendChild(botao);
  });
  if (c.cover) {
    const botaoCover = el("button", { type: "button", text: "Capa (cover.png)" });
    botaoCover.addEventListener("click", function () {
      const img = el("img", { src: urlCover(c), alt: "Capa da campanha " + c.slug });
      img.addEventListener("click", function () { abrirLightbox(img.src); });
      viewer.replaceChildren(img);
    });
    modos.appendChild(botaoCover);
  }
  if (c.formats) {
    const botaoFormats = el("button", { type: "button", text: "Formatos (preview-formats.png)" });
    botaoFormats.addEventListener("click", function () {
      const img = el("img", { src: urlFormats(c), alt: "Prévia de formatos da campanha " + c.slug });
      img.addEventListener("click", function () { abrirLightbox(img.src); });
      viewer.replaceChildren(img);
    });
    modos.appendChild(botaoFormats);
  }
  mostrarStoryboard();
  media.appendChild(modos);
  media.appendChild(viewer);
  if (!SERVIDO) {
    media.appendChild(el("p", { class: "nota", text: "Aberto via arquivo: player e sincronização de aprovações exigem python tools/review_dashboard.py --serve." }));
  }
  cardEl.appendChild(media);

  const abas = el("div", { class: "abas" });
  const area = el("div");
  function ativar(aba, botao) {
    Array.prototype.forEach.call(abas.children, function (b) { b.classList.remove("ativa"); });
    botao.classList.add("ativa");
    area.replaceChildren(painelAba(c, aba));
  }
  ABAS.forEach(function (par, i) {
    const botao = el("button", { class: "aba" + (i === 0 ? " ativa" : ""), type: "button", text: par[1] });
    botao.addEventListener("click", function () { ativar(par[0], botao); });
    abas.appendChild(botao);
  });
  area.appendChild(painelAba(c, ABAS[0][0]));
  cardEl.appendChild(abas);
  cardEl.appendChild(area);

  const aprovacao = el("div", { class: "aprovacao" });
  const e0 = estadoCampanha(c);
  const selDecisao = el("select");
  Object.keys(DECISOES).forEach(function (chave) {
    const opt = el("option", { value: chave, text: DECISOES[chave] });
    if (chave === e0.decisao) { opt.selected = true; }
    selDecisao.appendChild(opt);
  });
  selDecisao.addEventListener("change", function () {
    registrar(c, "decisao", selDecisao.value);
    atualizarChip();
  });
  const linhaDecisao = el("div", { class: "linha" }, [
    el("label", {}, [document.createTextNode("Decisão "), selDecisao])
  ]);
  if (c.politicaAudio === "-an") {
    const cbLocucao = el("input", { type: "checkbox" });
    cbLocucao.checked = e0.locucaoExternaConferida;
    cbLocucao.addEventListener("change", function () {
      registrar(c, "locucaoExternaConferida", cbLocucao.checked);
    });
    linhaDecisao.appendChild(el("label", {}, [
      cbLocucao,
      document.createTextNode(" Locução externa conferida")
    ]));
  }
  aprovacao.appendChild(linhaDecisao);
  const obs = el("textarea", { placeholder: "Observações do titular", rows: "2" });
  obs.value = e0.observacoes;
  obs.addEventListener("input", function () { registrar(c, "observacoes", obs.value); });
  aprovacao.appendChild(obs);
  cardEl.appendChild(aprovacao);
  return cardEl;
}

function correspondeBusca(c, termo) {
  if (!termo) { return true; }
  const alvo = [c.slug, c.campaignId, c.titulo, c.srt.text, c.narracao.text];
  Object.keys(c.routeRules || {}).forEach(function (rota) { alvo.push(rota); });
  Object.keys(c.copies || {}).forEach(function (canal) {
    const copy = c.copies[canal];
    if (copy) {
      if (copy.text) { alvo.push(copy.text); }
      if (copy.utmUrl) { alvo.push(copy.utmUrl); }
    }
  });
  return normalizar(alvo.join(" ")).indexOf(termo) >= 0;
}

function atualizarPainel() {
  const total = DATA.campaigns.length;
  const an = DATA.campaigns.filter(function (c) { return c.politicaAudio === "-an"; }).length;
  const conformes = DATA.campaigns.filter(function (c) {
    return c.pacote && c.pacote.guardrailsAudited && !c.pacote.autoPublish;
  }).length;
  const contagens = { aprovado: 0, ajuste: 0, aguardando: 0 };
  DATA.campaigns.forEach(function (c) {
    contagens[estadoCampanha(c).decisao] += 1;
  });
  document.getElementById("metrica-nichos").textContent = DATA.totals.tenants;
  document.getElementById("metrica-campanhas").textContent = DATA.totals.campaigns;
  document.getElementById("metrica-videos-an").textContent = an;
  document.getElementById("metrica-videos-aac").textContent = total - an;
  document.getElementById("metrica-guardrails").textContent =
    total ? Math.round((conformes / total) * 100) + "% conformes" : "0%";
  document.getElementById("metrica-aprovados").textContent = contagens.aprovado;
  document.getElementById("metrica-ajustes").textContent = contagens.ajuste;
  document.getElementById("metrica-pendentes").textContent = contagens.aguardando;
}

function render() {
  const grid = document.getElementById("grid");
  grid.replaceChildren();
  const fTenant = document.getElementById("filtro-tenant").value;
  const fPreset = document.getElementById("filtro-preset").value;
  const fAudio = document.getElementById("filtro-audio").value;
  const fStatus = document.getElementById("filtro-status").value;
  const termo = normalizar(document.getElementById("busca").value.trim());
  const visiveis = DATA.campaigns.filter(function (c) {
    return (!fTenant || c.tenantId === fTenant)
      && (!fPreset || c.preset === fPreset)
      && (!fAudio || c.politicaAudio === fAudio)
      && (!fStatus || estadoCampanha(c).decisao === fStatus)
      && correspondeBusca(c, termo);
  });
  visiveis.forEach(function (c) { grid.appendChild(card(c)); });
  document.getElementById("vazio").hidden = visiveis.length > 0;
  document.getElementById("contagem").textContent =
    visiveis.length + " de " + DATA.campaigns.length + " campanhas exibidas";
}

function atualizarSwatch() {
  const tenant = DATA.tenants.filter(function (t) {
    return t.tenantId === document.getElementById("filtro-tenant").value;
  })[0];
  document.getElementById("swatch-tenant").style.background =
    tenant && tenant.palette && tenant.palette.primary ? tenant.palette.primary : "#1f6feb";
}

(function init() {
  const selTenant = document.getElementById("filtro-tenant");
  DATA.tenants.forEach(function (t) {
    const opt = document.createElement("option");
    opt.value = t.tenantId;
    opt.textContent = t.monogram + " · " + t.brandName;
    selTenant.appendChild(opt);
  });
  selTenant.addEventListener("change", function () { atualizarSwatch(); render(); });
  ["filtro-preset", "filtro-audio", "filtro-status"].forEach(function (id) {
    document.getElementById(id).addEventListener("change", render);
  });
  document.getElementById("busca").addEventListener("input", render);
  const inputRevisor = document.getElementById("input-revisor");
  inputRevisor.value = carregarEstado().revisor || "";
  inputRevisor.addEventListener("input", function () { registrarRevisor(inputRevisor.value); });
  document.getElementById("btn-exportar-aprovacoes").addEventListener("click", exportarAprovacoes);
  document.getElementById("btn-importar-aprovacoes").addEventListener("click", function () {
    document.getElementById("input-importar").click();
  });
  document.getElementById("input-importar").addEventListener("change", function (ev) {
    if (ev.target.files && ev.target.files[0]) { importarAprovacoes(ev.target.files[0]); }
  });
  document.getElementById("lightbox").addEventListener("click", function (ev) {
    if (ev.target.id === "lightbox") { fecharLightbox(); }
  });
  document.getElementById("lightbox-fechar").addEventListener("click", fecharLightbox);
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") { fecharLightbox(); }
  });
  document.getElementById("sub-titulo").textContent =
    DATA.totals.tenants + " tenants · " + DATA.totals.campaigns + " campanhas";
  if (SERVIDO) {
    fetch("/api/health").then(function (r) { return r.json(); }).then(function (s) {
      document.getElementById("badge-servidor").textContent =
        "Servidor ativo · " + s.tenants + " tenants · " + s.campaigns + " campanhas";
    }).catch(function () { /* servidor fora do ar: segue sem badge */ });
  }
  atualizarSwatch();
  render();
  atualizarPainel();
})();
</script>
</body>
</html>"""


def render_index_html(data: dict) -> str:
    """Renderiza index.html embutindo o JSON do portal com escape de "</".

    A sequencia "</" vira "<\\/" (escape valido de barra em strings JSON):
    impede o fechamento prematuro do bloco <script> por valores hostis e
    preserva o documento identico apos json.loads.
    """
    embutido = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return _HTML_TEMPLATE.replace("__PORTAL_DATA__", embutido)


def _validar_aprovacoes(doc: Any, conhecidas: dict) -> None:
    """Valida estritamente o documento de aprovacoes do titular (schema v2).

    Falha fechada: chave desconhecida, tipo errado, campanha fora do portal
    ou decisao fora do vocabulario aborta o POST com codigo proprio, sem
    gravar nada em disco.
    """
    if not isinstance(doc, dict):
        raise _AprovacoesInvalidas("JSON_INVALIDO", "documento nao e um objeto JSON")
    desconhecidas = sorted(set(doc) - _APPROVALS_DOC_KEYS)
    if desconhecidas:
        raise _AprovacoesInvalidas(
            "CHAVE_DESCONHECIDA", "chave(s) desconhecida(s): " + ", ".join(desconhecidas)
        )
    for chave in ("schemaVersion", "campanhas"):
        if chave not in doc:
            raise _AprovacoesInvalidas(
                "SCHEMA_INVALIDO", f"chave obrigatoria ausente: {chave}"
            )
    versao = doc["schemaVersion"]
    if (
        isinstance(versao, bool)
        or not isinstance(versao, int)
        or versao != APPROVALS_SCHEMA_VERSION
    ):
        raise _AprovacoesInvalidas(
            "SCHEMA_INVALIDO", f"schemaVersion deve ser {APPROVALS_SCHEMA_VERSION}"
        )
    for chave in ("arquivo", "origem", "exportadoEm", "revisor"):
        if chave in doc and not isinstance(doc[chave], str):
            raise _AprovacoesInvalidas("TIPO_INVALIDO", f"{chave} deve ser texto")
    if "arquivo" in doc and doc["arquivo"] != APPROVALS_FILENAME:
        raise _AprovacoesInvalidas(
            "SCHEMA_INVALIDO", f"arquivo deve ser {APPROVALS_FILENAME}"
        )
    if "exportadoEm" in doc and not _EXPORTADO_EM_RE.match(doc["exportadoEm"]):
        raise _AprovacoesInvalidas("SCHEMA_INVALIDO", "exportadoEm deve ser timestamp ISO")
    if "resumo" in doc:
        _validar_resumo(doc["resumo"])
    campanhas = doc["campanhas"]
    if not isinstance(campanhas, list):
        raise _AprovacoesInvalidas("TIPO_INVALIDO", "campanhas deve ser lista")
    for item in campanhas:
        _validar_item_aprovacoes(item, conhecidas)


def _validar_resumo(resumo: Any) -> None:
    if not isinstance(resumo, dict):
        raise _AprovacoesInvalidas("TIPO_INVALIDO", "resumo deve ser objeto")
    extras = sorted(set(resumo) - _APPROVALS_RESUMO_KEYS)
    if extras:
        raise _AprovacoesInvalidas(
            "CHAVE_DESCONHECIDA", "resumo com chave(s) desconhecida(s): " + ", ".join(extras)
        )
    for chave, valor in resumo.items():
        if isinstance(valor, bool) or not isinstance(valor, int):
            raise _AprovacoesInvalidas("TIPO_INVALIDO", f"resumo.{chave} deve ser inteiro")


def _validar_item_aprovacoes(item: Any, conhecidas: dict) -> None:
    if not isinstance(item, dict):
        raise _AprovacoesInvalidas("TIPO_INVALIDO", "item de campanha nao e objeto")
    extras = sorted(set(item) - _APPROVALS_ITEM_KEYS)
    if extras:
        raise _AprovacoesInvalidas(
            "CHAVE_DESCONHECIDA", "item com chave(s) desconhecida(s): " + ", ".join(extras)
        )
    for chave in ("tenantId", "slug", "decisao"):
        if chave not in item:
            raise _AprovacoesInvalidas(
                "SCHEMA_INVALIDO", f"chave obrigatoria ausente no item: {chave}"
            )
    for chave in ("tenantId", "slug", "decisao"):
        if not isinstance(item[chave], str):
            raise _AprovacoesInvalidas("TIPO_INVALIDO", f"{chave} deve ser texto")
    if (item["tenantId"], item["slug"]) not in conhecidas:
        raise _AprovacoesInvalidas(
            "CAMPANHA_DESCONHECIDA",
            f"campanha desconhecida: {item['tenantId']}/{item['slug']}",
        )
    if item["decisao"] not in APPROVALS_DECISOES:
        raise _AprovacoesInvalidas(
            "DECISAO_INVALIDA", f"decisao invalida: {item['decisao']}"
        )
    for chave in ("campaignId", "preset", "politicaAudio", "observacoes"):
        if chave in item and not isinstance(item[chave], str):
            raise _AprovacoesInvalidas("TIPO_INVALIDO", f"{chave} deve ser texto")
    if "locucaoExternaConferida" in item and not isinstance(
        item["locucaoExternaConferida"], bool
    ):
        raise _AprovacoesInvalidas(
            "TIPO_INVALIDO", "locucaoExternaConferida deve ser booleano"
        )
    if "hashes" in item:
        hashes = item["hashes"]
        if not isinstance(hashes, dict):
            raise _AprovacoesInvalidas("TIPO_INVALIDO", "hashes deve ser objeto")
        for chave, valor in hashes.items():
            if not isinstance(chave, str) or not isinstance(valor, str):
                raise _AprovacoesInvalidas(
                    "TIPO_INVALIDO", "hashes deve mapear texto para texto"
                )


# ---------------------------------------------------------------------------
# Servidor HTTP local (somente leitura, confinado a raiz)
# ---------------------------------------------------------------------------

class _PortalServer(http.server.ThreadingHTTPServer):
    """Servidor multithread confinado a raiz do checkout e ao workspace resolvido."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address,
        handler,
        portal_root: str,
        archives_dir: str,
        portal_data: dict,
        approvals_store: str,
    ) -> None:
        super().__init__(address, handler)
        self.portal_root = portal_root
        self.archives_dir = archives_dir
        self.portal_data = portal_data
        self.approvals_store = approvals_store
        self.campanhas: dict[tuple[str, str], dict] = {}
        for campanha in portal_data.get("campaigns", []):
            if isinstance(campanha, dict):
                chave = (campanha.get("tenantId"), campanha.get("slug"))
                self.campanhas[chave] = campanha


_MEDIA_PNG = ("storyboard", "cover", "formats")


class _PortalHandler(http.server.BaseHTTPRequestHandler):
    """Handler: GET/HEAD de leitura; POST apenas em /api/approvals."""

    server_version = "ReviewPortal/2.0"
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802 (nome exigido pela stdlib)
        self._atender(head_only=False)

    def do_HEAD(self) -> None:  # noqa: N802
        self._atender(head_only=True)

    def do_POST(self) -> None:  # noqa: N802
        segments = self._segmentos()
        if segments is None:
            return
        if segments == ["api", "approvals"]:
            self._post_aprovacoes()
            return
        self.send_error(405, "Method Not Allowed")

    def do_PUT(self) -> None:  # noqa: N802
        self.send_error(405, "Method Not Allowed")

    def do_DELETE(self) -> None:  # noqa: N802
        self.send_error(405, "Method Not Allowed")

    def _negar(self) -> None:
        self.send_error(404, "Not Found")

    def _segmentos(self) -> list[str] | None:
        raw = self.path.split("?", 1)[0].split("#", 1)[0]
        try:
            path = urllib.parse.unquote(raw)
        except (UnicodeDecodeError, ValueError):
            self._negar()
            return None
        if "\\" in path or "\x00" in path:
            self._negar()
            return None
        segments = [s for s in path.split("/") if s != ""]
        if any(s == ".." for s in segments):
            self._negar()
            return None
        return segments

    def _atender(self, head_only: bool) -> None:
        segments = self._segmentos()
        if segments is None:
            return
        root = self.server.portal_root
        if not segments or segments == ["index.html"]:
            self._servir_arquivo(
                os.path.join(root, PORTAL_DIR_NAME, "index.html"),
                "text/html; charset=utf-8",
                head_only,
            )
            return
        if segments == ["portal-data.json"] or segments == ["api", "data"]:
            self._servir_arquivo(
                os.path.join(root, PORTAL_DIR_NAME, "portal-data.json"),
                "application/json; charset=utf-8",
                head_only,
            )
            return
        if segments == ["api", "health"]:
            totals = self.server.portal_data.get("totals") or {}
            self._responder_json(
                200,
                {
                    "ok": True,
                    "tenants": totals.get("tenants", 0),
                    "campaigns": totals.get("campaigns", 0),
                },
                head_only,
            )
            return
        if segments == ["api", "approvals"]:
            self._get_aprovacoes(head_only)
            return
        if len(segments) == 4 and segments[0] == "media" and segments[1] in _MEDIA_PNG:
            self._atender_media_png(segments, head_only)
            return
        if len(segments) == 5 and segments[0] == "media" and segments[1] == "video":
            self._atender_media_video(segments, head_only)
            return
        if segments[0] == "deliveries" and len(segments) > 1:
            ext = os.path.splitext(segments[-1])[1].lower()
            if ext not in _DELIVERIES_ALLOWED_EXT:
                self._negar()
                return
            alvo = os.path.join(root, DELIVERIES_ROOT, *segments[1:])
            self._servir_arquivo(alvo, _CONTENT_TYPES.get(ext, "application/octet-stream"), head_only)
            return
        if segments[0] == "archives" and len(segments) > 1:
            if os.path.splitext(segments[-1])[1].lower() != ".mp4":
                self._negar()
                return
            alvo = os.path.join(self.server.archives_dir, *segments[1:])
            self._servir_video(alvo, head_only)
            return
        self._negar()

    def _atender_media_png(self, segments: list[str], head_only: bool) -> None:
        _, tipo, tenant_id, slug = segments
        campanha = self.server.campanhas.get((tenant_id, slug))
        ativo = (campanha or {}).get(tipo)
        if not isinstance(ativo, dict) or not ativo.get("relPath"):
            self._negar()
            return
        alvo = os.path.join(
            self.server.portal_root, str(ativo["relPath"]).replace("/", os.sep)
        )
        self._servir_arquivo(alvo, "image/png", head_only)

    def _atender_media_video(self, segments: list[str], head_only: bool) -> None:
        _, _, tenant_id, slug, variante = segments
        campanha = self.server.campanhas.get((tenant_id, slug))
        if not campanha:
            self._negar()
            return
        if not _VARIANTE_RE.match(variante):
            self._negar()
            return
        video = campanha.get("video") or {}
        variantes = video.get("variants") or []
        if variante not in variantes:
            self._negar()
            return
        for candidato in self._candidatos_video(video, variante, variantes):
            real = self._resolver(candidato, self.server.archives_dir)
            if real is not None:
                self._servir_video(real, head_only)
                return
        self._negar()

    def _candidatos_video(self, video: dict, variante: str, variantes: list) -> list[str]:
        """Caminhos candidatos da variante sob o workspace resolvido.

        A variante primaria e o MP4 arquivado; derivadas usam o caminho
        declarado em derivatives.json ou a convencao de nomes do slug.
        """
        archive_rel = str(video.get("archiveRelPath") or "")
        if not archive_rel.startswith(ARCHIVES_PREFIX):
            return []
        primario = os.path.join(
            self.server.archives_dir,
            archive_rel[len(ARCHIVES_PREFIX):].replace("/", os.sep),
        )
        if variante == variantes[0]:
            return [primario]
        pasta_slug = os.path.dirname(primario)
        stem = os.path.splitext(os.path.basename(primario))[0]
        candidatos: list[str] = []
        for deriv in video.get("derivatives") or []:
            if isinstance(deriv, dict) and deriv.get("variant") == variante:
                caminho = str(deriv.get("path") or "")
                if caminho:
                    candidatos.append(os.path.join(pasta_slug, caminho.replace("/", os.sep)))
        candidatos.append(os.path.join(pasta_slug, "derivatives", stem + "-" + variante + ".mp4"))
        candidatos.append(os.path.join(pasta_slug, stem + "-" + variante + ".mp4"))
        return candidatos

    def _resolver(self, alvo: str, base: str) -> str | None:
        real = os.path.realpath(alvo)
        if not render_local.contained(base, real):
            return None
        if not os.path.isfile(render_local.fs_path(real)):
            return None
        return real

    def _responder_json(self, status: int, payload: dict, head_only: bool = False) -> None:
        corpo = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(corpo)

    def _get_aprovacoes(self, head_only: bool) -> None:
        store = self.server.approvals_store
        existe = os.path.isfile(render_local.fs_path(store))
        doc = None
        if existe:
            try:
                doc = _load_json(store)
            except ValueError:
                self.send_error(500, "Store de aprovacoes ilegivel")
                return
        self._responder_json(
            200, {"ok": True, "existe": existe, "aprovacoes": doc}, head_only
        )

    def _post_aprovacoes(self) -> None:
        tamanho_bruto = self.headers.get("Content-Length")
        if tamanho_bruto is None:
            self.send_error(411, "Length Required")
            return
        try:
            tamanho = int(tamanho_bruto)
        except ValueError:
            self.send_error(400, "Bad Request")
            return
        if tamanho < 0 or tamanho > _MAX_CORPO_POST:
            self.send_error(413, "Payload Too Large")
            return
        corpo = self.rfile.read(tamanho)
        if len(corpo) != tamanho:
            self.send_error(400, "Bad Request")
            return
        try:
            doc = json.loads(corpo.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            self._responder_json(
                400,
                {"ok": False, "erro": "JSON_INVALIDO", "detalhe": "corpo nao e JSON valido"},
            )
            return
        try:
            _validar_aprovacoes(doc, self.server.campanhas)
        except _AprovacoesInvalidas as exc:
            self._responder_json(400, {"ok": False, "erro": exc.code, "detalhe": str(exc)})
            return
        store = self.server.approvals_store
        os.makedirs(render_local.fs_path(os.path.dirname(store)), exist_ok=True)
        with open(render_local.fs_path(store), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(doc, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        self._responder_json(
            200,
            {
                "ok": True,
                "campanhas": len(doc["campanhas"]),
                "salvoEm": APPROVALS_STORE_REL,
            },
        )

    def _servir_arquivo(self, alvo: str, ctype: str, head_only: bool) -> None:
        real = self._resolver(alvo, self.server.portal_root)
        if real is None:
            self._negar()
            return
        try:
            with open(render_local.fs_path(real), "rb") as handle:
                corpo = handle.read()
        except OSError:
            self._negar()
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(corpo)

    def _servir_video(self, alvo: str, head_only: bool) -> None:
        real = self._resolver(alvo, self.server.archives_dir)
        if real is None:
            self._negar()
            return
        size = os.path.getsize(render_local.fs_path(real))
        inicio, fim = 0, size - 1
        status = 200
        range_header = self.headers.get("Range")
        if range_header:
            m = re.match(r"^bytes=(\d+)-(\d*)$", range_header.strip())
            if m:
                inicio = int(m.group(1))
                fim = int(m.group(2)) if m.group(2) else size - 1
                fim = min(fim, size - 1)
                if inicio >= size or inicio > fim:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                status = 206
        tamanho = fim - inicio + 1
        self.send_response(status)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(tamanho))
        if status == 206:
            self.send_header("Content-Range", f"bytes {inicio}-{fim}/{size}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if head_only:
            return
        try:
            with open(render_local.fs_path(real), "rb") as handle:
                handle.seek(inicio)
                restante = tamanho
                while restante > 0:
                    chunk = handle.read(min(65536, restante))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    restante -= len(chunk)
        except OSError:
            pass

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[portal] %s - %s\n" % (self.address_string(), fmt % args))


def make_server(root: str = ".", port: int = 8765, host: str = "127.0.0.1") -> _PortalServer:
    """Cria (sem bloquear) o servidor HTTP local do portal."""
    root_real = os.path.realpath(root)
    if not os.path.isdir(render_local.fs_path(root_real)):
        raise ReviewPortalError(f"RAIZ_INVALIDA: {root}")
    indice = os.path.join(root_real, PORTAL_DIR_NAME, "index.html")
    dados = os.path.join(root_real, PORTAL_DIR_NAME, "portal-data.json")
    if not os.path.isfile(render_local.fs_path(indice)) or not os.path.isfile(
        render_local.fs_path(dados)
    ):
        raise ReviewPortalError(
            "PORTAL_NAO_GERADO: execute --build antes de --serve"
        )
    try:
        portal_data = _load_json(dados)
    except ValueError as exc:
        raise ReviewPortalError(f"PORTAL_DADOS_INVALIDOS: {exc}") from exc
    if not isinstance(portal_data, dict):
        raise ReviewPortalError("PORTAL_DADOS_INVALIDOS: portal-data.json nao e um objeto")
    archives = _archives_dir(root_real)
    store = approvals_store_path(root_real)
    try:
        return _PortalServer(
            (host, port), _PortalHandler, root_real, archives, portal_data, store
        )
    except OSError as exc:
        raise ReviewPortalError(f"PORTA_INDISPONIVEL: {host}:{port} ({exc})") from exc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Gerador e servidor local do Portal de Revisao "
            "(05-review-portal). Modos: --build, --serve, --export-aprovacoes."
        )
    )
    parser.add_argument("--build", action="store_true", help="Gera o portal consolidado")
    parser.add_argument("--serve", action="store_true", help="Serve o portal via HTTP local")
    parser.add_argument(
        "--export-aprovacoes",
        action="store_true",
        help="Imprime no stdout o documento de aprovacoes persistido",
    )
    parser.add_argument("--output-dir", default=None, help="Diretorio de saida do --build (padrao: 05-review-portal)")
    parser.add_argument("--port", type=int, default=8765, help="Porta do --serve (padrao: 8765)")
    parser.add_argument("--host", default="127.0.0.1", help="Host do --serve (padrao: 127.0.0.1)")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument("--json", action="store_true", help="Emite JSON no stdout (apenas --build)")
    args = parser.parse_args(argv)

    modos = [args.build, args.serve, args.export_aprovacoes]
    if sum(1 for modo in modos if modo) != 1:
        print(
            "Erro: informe exatamente um modo (--build, --serve ou --export-aprovacoes)",
            file=sys.stderr,
        )
        return 2

    try:
        if args.build:
            resumo = build_portal(root=args.root, output_dir=args.output_dir)
            if args.json:
                print(json.dumps(resumo, ensure_ascii=False, indent=2))
            else:
                print(
                    f"Portal gerado em {resumo['outputDir']} "
                    f"({resumo['totalTenants']} tenants / {resumo['totalCampaigns']} campanhas)"
                )
            return 0

        if args.export_aprovacoes:
            store = approvals_store_path(os.path.realpath(args.root))
            if not os.path.isfile(render_local.fs_path(store)):
                print(
                    f"Erro: APROVACOES_AUSENTES: nada persistido em {APPROVALS_STORE_REL}",
                    file=sys.stderr,
                )
                return 1
            try:
                doc = _load_json(store)
            except ValueError as exc:
                print(f"Erro: APROVACOES_INVALIDAS: {exc}", file=sys.stderr)
                return 1
            print(json.dumps(doc, ensure_ascii=False, indent=2))
            return 0

        build_portal(root=args.root, output_dir=args.output_dir)
        servidor = make_server(root=args.root, port=args.port, host=args.host)
        porta_real = servidor.server_address[1]
        print(f"Portal de revisao servindo em http://{args.host}:{porta_real}/")
        print("Ctrl+C para encerrar.")
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            servidor.server_close()
        return 0
    except ReviewPortalError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro: entrada invalida ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
