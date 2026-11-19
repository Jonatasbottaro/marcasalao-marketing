"""Gerador e servidor local do Portal de Revisao (Etapa 4 - Agente 2).

Consolida em um portal estatico de revisao humana (05-review-portal/):
  - tenants: tenants/*/brand-kit.json + guardrails.json
  - entregas: 02-reels-shorts/deliveries/<tenant>/<slug>/
    (manifest.json, <slug>.srt, <slug>_narracao.txt, preview-storyboard.png)
  - pacotes sociais: 04-legendas/pacotes-publicacao/<tenant>/<slug>/
    (checklist-publicacao.json, instagram-reels.md, youtube-shorts.md,
    facebook-reels.md)

Gera 05-review-portal/index.html (dados embutidos, funciona via file://),
05-review-portal/portal-data.json e 05-review-portal/README.md. O build e
deterministico: nao grava timestamps e produz bytes identicos para os mesmos
insumos, para que o portal versionado seja o mesmo em qualquer estacao.

O modo --serve sobe um servidor HTTP local (apenas stdlib, somente leitura,
vinculado a 127.0.0.1) que serve o portal, os storyboards das entregas e faz
streaming dos MP4s preservados em .workspace/archives/ com suporte a Range.
Todo caminho solicitado e confinado a raiz do checkout (sem "..", sem
caminho absoluto, sem UNC); apenas GET/HEAD sao atendidos.

Uso (a partir da raiz do checkout):
    python tools/review_dashboard.py --build [--output-dir 05-review-portal] [--json]
    python tools/review_dashboard.py --serve [--port 8765]
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
import re
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
TENANTS_ROOT = "tenants"

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

    return {
        "tenantId": tenant_id,
        "slug": slug,
        "campaignId": campaign_id,
        "preset": manifest.get("preset", ""),
        "politicaAudio": "AAC" if tenant_ctx_audio else "-an",
        "audioStreams": int(ffprobe.get("audioStreams", 0)),
        "format": {
            "width": manifest.get("format", {}).get("width", 0),
            "height": manifest.get("format", {}).get("height", 0),
            "fps": manifest.get("format", {}).get("fps", 0),
            "duration": manifest.get("format", {}).get("duration", 0.0),
        },
        "scenes": scenes,
        "video": {
            "archiveRelPath": archive_rel,
            "sha256": video_artifact.get("sha256", ""),
            "bytes": int(video_artifact.get("bytes", 0)),
            "audioStreams": int(ffprobe.get("audioStreams", 0)),
            "audioCodec": ffprobe.get("audioCodec"),
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
        "copies": copies,
        "pacote": pacote,
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
    embedded = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = _HTML_TEMPLATE.replace("__PORTAL_DATA__", embedded)
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
  `<slug>_narracao.txt`, `preview-storyboard.png`)
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
divergência aborta o build com `HASH_DIVERGENTE`.

## Servir (recomendado)

```
python tools/review_dashboard.py --serve [--port 8765]
```

Sobe um servidor HTTP local em `http://127.0.0.1:8765/` (somente leitura,
vinculado a 127.0.0.1, sem dependências externas). Quando servido, cada
cartão exibe o player `<video>` com o MP4 preservado em
`.workspace/archives/<slug>/` (com suporte a Range/seek). Aberto direto do
disco (`file://`), o portal funciona com o storyboard 2×2 como prévia.

Os MP4s **não são versionados** (`.workspace/archives/` é local por estação):
se o arquivo não existir na estação, o player cai no storyboard com aviso.

## Interface

- **Filtros:** tenant, preset (`saas-demo` × `shorts-completo`) e política de
  áudio (`-an` sem áudio × `AAC` com áudio).
- **Cartões por campanha:** paleta do tenant, storyboard 2×2 (e player quando
  servido), abas **Legenda .srt**, **Roteiro de Narração**, **Copy
  Instagram/YouTube/Facebook** com botões "Copiar" e links UTM rastreados.
- **Checklist de aprovação humana:** itens por campanha, revisor e observações,
  persistidos no `localStorage` do navegador (chave
  `reviewPortal.aprovacoes.v1`).
- **Exportar JSON de Aprovações:** botão no cabeçalho que baixa
  `aprovacoes-titular.json` com todas as campanhas, estado de cada item do
  checklist, `aprovada` (true quando todos os itens marcados), revisor,
  observações e hashes SHA-256 para rastreabilidade — compatível com o fluxo
  manual de aprovação do titular.

## Segurança do servidor

- Somente `GET`/`HEAD`; métodos de escrita são recusados.
- Rotas restritas: `/` e `/portal-data.json` (portal),
  `/deliveries/<caminho>` (storyboards e textos das entregas) e
  `/archives/<slug>/<arquivo>.mp4` (vídeos, com `Range`).
- Todo caminho é decodificado e confinado à raiz do checkout: `..`, `\\`,
  caminhos absolutos e UNC recebem 404; extensões fora da lista permitida
  também são recusadas.
- `portal-data.json` contém apenas caminhos relativos contidos na raiz
  (nenhum caminho absoluto de estação), mantendo o portal portátil.
"""


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Portal de Revisão — Content Factory Multi-Tenant</title>
<style>
:root{--bg:#0d1117;--surface:#161b22;--border:#30363d;--text:#e6edf3;--muted:#8b949e;--ok:#2ea043;--warn:#d29922;--info:#1f6feb}
*{box-sizing:border-box}
body{margin:0;font-family:"Segoe UI",Arial,sans-serif;background:var(--bg);color:var(--text)}
header{padding:18px 22px;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg);z-index:20}
h1{margin:0 0 2px;font-size:19px}
.sub{margin:0 0 12px;color:var(--muted);font-size:13px}
.filtros{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.filtros label{font-size:12px;color:var(--muted);display:flex;gap:6px;align-items:center}
select,button,input,textarea{background:#0b0f14;color:var(--text);border:1px solid var(--border);border-radius:6px;padding:6px 10px;font-size:13px;font-family:inherit}
button{cursor:pointer}
button:hover{border-color:#58a6ff}
#btn-exportar-aprovacoes{margin-left:auto;background:var(--info);border-color:var(--info);font-weight:600;color:#fff}
main{padding:18px 22px;display:grid;grid-template-columns:repeat(auto-fill,minmax(440px,1fr));gap:16px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden;display:flex;flex-direction:column}
.card-head{padding:10px 14px;border-bottom:1px solid var(--border);border-left:4px solid var(--c-primary);display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.monogram{width:30px;height:30px;border-radius:8px;background:var(--c-primary);color:#0b0f14;font-weight:700;display:flex;align-items:center;justify-content:center;font-size:13px;flex:none}
.card-titulo{display:flex;flex-direction:column;margin-right:auto}
.card-titulo strong{font-size:14px}
.card-titulo span{font-size:11px;color:var(--muted)}
.chip{font-size:11px;padding:2px 8px;border-radius:10px;border:1px solid var(--border);color:var(--muted)}
.chip.aprovada{background:rgba(46,160,67,.2);color:#3fb950;border-color:#2ea043}
.chip.revisao{background:rgba(210,153,34,.15);color:#d29922;border-color:#9e6a03}
.card-media{padding:10px 14px 0;display:flex;flex-direction:column;gap:6px}
.card-media img,.card-media video{width:100%;max-height:430px;object-fit:contain;background:#000;border-radius:8px}
.nota{font-size:11px;color:var(--muted)}
.abas{display:flex;gap:4px;padding:10px 14px 0;flex-wrap:wrap}
.aba{padding:5px 10px;font-size:12px;border-radius:6px 6px 0 0;color:var(--muted)}
.aba.ativa{color:var(--text);background:#0b0f14}
.aba-conteudo{margin:0 14px;border:1px solid var(--border);border-radius:0 8px 8px 8px;padding:10px;background:#0b0f14}
.aba-conteudo pre{margin:0 0 8px;white-space:pre-wrap;font-size:12px;max-height:220px;overflow:auto;font-family:Consolas,monospace}
.linha-acoes{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.linha-acoes a{color:#58a6ff;font-size:12px;text-decoration:none;word-break:break-all}
.checklist{padding:12px 14px;border-top:1px solid var(--border);display:flex;flex-direction:column;gap:6px}
.checklist label.item{display:flex;gap:8px;align-items:center;font-size:12px}
.checklist .campos{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:4px}
footer{padding:14px 22px;color:var(--muted);font-size:12px}
#vazio{text-align:center;color:var(--muted);padding:30px}
</style>
</head>
<body>
<header>
  <h1>Portal de Revisão — Content Factory Multi-Tenant</h1>
  <p class="sub"><span id="sub-titulo"></span> · <span id="contagem"></span></p>
  <div class="filtros">
    <label>Tenant <select id="filtro-tenant"><option value="">Todos</option></select></label>
    <label>Preset <select id="filtro-preset"><option value="">Todos</option><option value="saas-demo">saas-demo</option><option value="shorts-completo">shorts-completo</option></select></label>
    <label>Áudio <select id="filtro-audio"><option value="">Todos</option><option value="-an">-an (sem áudio)</option><option value="AAC">AAC (com áudio)</option></select></label>
    <button id="btn-exportar-aprovacoes" type="button">Exportar JSON de Aprovações</button>
  </div>
</header>
<main id="grid"></main>
<p id="vazio" hidden>Nenhuma campanha corresponde aos filtros.</p>
<footer>Portal de Revisão gerado por <code>tools/review_dashboard.py</code> · Aprovações persistem no <code>localStorage</code> do navegador · A exportação gera <code>aprovacoes-titular.json</code> · Vídeos são servidos de <code>.workspace/archives/</code> (local por estação).</footer>
<script id="portal-data" type="application/json">__PORTAL_DATA__</script>
<script>
"use strict";
const DATA = JSON.parse(document.getElementById("portal-data").textContent);
const SERVIDO = location.protocol === "http:" || location.protocol === "https:";
const LS_KEY = "reviewPortal.aprovacoes.v1";
const ITENS = [
  ["storyboard", "Storyboard 2×2 revisado"],
  ["legendas", "Legendas SRT conferidas (sincronização e legibilidade)"],
  ["narracao", "Roteiro de narração revisado"],
  ["copies", "Copies Instagram/YouTube/Facebook revisadas"],
  ["utm", "Links UTM conferidos"],
  ["audio", "Política de áudio confirmada"],
  ["guardrails", "Guardrails sem violações (checklist de publicação)"]
];
const ABAS = [
  ["srt", "Legenda .srt"],
  ["narracao", "Roteiro de Narração"],
  ["instagram", "Copy Instagram"],
  ["youtube", "Copy YouTube"],
  ["facebook", "Copy Facebook"]
];

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
  try { return JSON.parse(localStorage.getItem(LS_KEY) || "{}"); }
  catch (e) { return {}; }
}
function salvarEstado(estado) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(estado)); }
  catch (e) { /* localStorage indisponivel: segue sem persistencia */ }
}
function chaveCampanha(c) { return c.tenantId + "/" + c.slug; }
function estadoCampanha(c) {
  const st = carregarEstado()[chaveCampanha(c)];
  return st || { itens: {}, revisor: "", observacoes: "" };
}
function registrar(c, campo, valor) {
  const estado = carregarEstado();
  const st = estado[chaveCampanha(c)] || { itens: {} };
  if (campo === "itens") {
    st.itens = valor;
  } else {
    st[campo] = valor;
  }
  estado[chaveCampanha(c)] = st;
  salvarEstado(estado);
}

function urlStoryboard(c) {
  const rest = c.storyboard.relPath.slice(DATA.deliveriesRoot.length + 1);
  return SERVIDO ? "/deliveries/" + rest : "../" + c.storyboard.relPath;
}
function urlVideo(c) {
  return "/archives/" + c.video.archiveRelPath.slice(DATA.archivesRoot.length + 1);
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
function textoAudio(c) {
  return c.politicaAudio === "AAC"
    ? "AAC · " + c.audioStreams + " faixa(s)"
    : "-an · " + c.audioStreams + " faixa(s)";
}

function painelAba(c, aba) {
  const painel = el("div", { class: "aba-conteudo" });
  if (aba === "srt" || aba === "narracao") {
    const texto = aba === "srt" ? c.srt.text : c.narracao.text;
    const botao = el("button", { type: "button", text: "Copiar" });
    botao.addEventListener("click", function () { copiar(texto, botao); });
    painel.appendChild(el("pre", { text: texto }));
    painel.appendChild(el("div", { class: "linha-acoes" }, [botao]));
    return painel;
  }
  const copy = c.copies ? c.copies[aba] : null;
  if (!copy || !copy.text) {
    painel.appendChild(el("p", { class: "nota", text: "Pacote de publicação não gerado para esta campanha." }));
    return painel;
  }
  const botaoCopy = el("button", { type: "button", text: "Copiar" });
  botaoCopy.addEventListener("click", function () { copiar(copy.text, botaoCopy); });
  const acoes = el("div", { class: "linha-acoes" }, [botaoCopy]);
  if (copy.utmUrl) {
    acoes.appendChild(el("a", { href: copy.utmUrl, target: "_blank", rel: "noopener", text: copy.utmUrl }));
    const botaoUrl = el("button", { type: "button", text: "Copiar link UTM" });
    botaoUrl.addEventListener("click", function () { copiar(copy.utmUrl, botaoUrl); });
    acoes.appendChild(botaoUrl);
  }
  painel.appendChild(el("pre", { text: copy.text }));
  painel.appendChild(acoes);
  return painel;
}

function card(c) {
  const tenant = DATA.tenants.filter(function (t) { return t.tenantId === c.tenantId; })[0] || { palette: {} };
  const cardEl = el("article", { class: "card" });
  cardEl.style.setProperty("--c-primary", tenant.palette.primary || "#1f6feb");

  const chip = el("span", { class: "chip", text: "Não iniciada" });
  function atualizarChip() {
    const st = estadoCampanha(c);
    const marcados = ITENS.filter(function (par) { return (st.itens || {})[par[0]]; }).length;
    if (marcados === ITENS.length) {
      chip.textContent = "Aprovada";
      chip.className = "chip aprovada";
    } else if (marcados > 0) {
      chip.textContent = "Em revisão " + marcados + "/" + ITENS.length;
      chip.className = "chip revisao";
    } else {
      chip.textContent = "Não iniciada";
      chip.className = "chip";
    }
  }

  const cabecalho = el("div", { class: "card-head" }, [
    el("div", { class: "monogram", text: tenant.monogram || "" }),
    el("div", { class: "card-titulo" }, [
      el("strong", { text: tenant.brandName + " — " + c.campaignId }),
      el("span", { text: c.slug + " · " + c.format.width + "×" + c.format.height + " @ " + c.format.fps + "fps · " + c.format.duration + "s · " + c.scenes + " cenas" })
    ]),
    el("span", { class: "chip", text: c.preset }),
    el("span", { class: "chip", text: textoAudio(c) }),
    chip
  ]);
  atualizarChip();
  cardEl.appendChild(cabecalho);

  const media = el("div", { class: "card-media" });
  const img = el("img", { src: urlStoryboard(c), alt: "Storyboard 2×2 da campanha " + c.slug });
  if (SERVIDO) {
    const wrap = document.createElement("div");
    wrap.innerHTML = '<video class="player" controls preload="metadata"></video>';
    const video = wrap.firstChild;
    video.poster = urlStoryboard(c);
    video.addEventListener("error", function () {
      media.replaceChildren(img, el("p", { class: "nota", text: "MP4 não disponível nesta estação (.workspace/archives é local por estação)." }));
    });
    video.src = urlVideo(c);
    media.appendChild(video);
  } else {
    media.appendChild(img);
    media.appendChild(el("p", { class: "nota", text: "Aberto via arquivo. Execute python tools/review_dashboard.py --serve para assistir ao vídeo." }));
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

  const checklist = el("div", { class: "checklist" });
  checklist.appendChild(el("strong", { text: "Checklist de aprovação" }));
  const st = estadoCampanha(c);
  ITENS.forEach(function (par) {
    const cb = el("input", { type: "checkbox" });
    cb.checked = Boolean((st.itens || {})[par[0]]);
    cb.addEventListener("change", function () {
      const itens = estadoCampanha(c).itens || {};
      itens[par[0]] = cb.checked;
      registrar(c, "itens", itens);
      atualizarChip();
    });
    checklist.appendChild(el("label", { class: "item" }, [cb, el("span", { text: par[1] })]));
  });
  const revisor = el("input", { type: "text", placeholder: "Revisor (opcional)" });
  revisor.value = st.revisor || "";
  revisor.addEventListener("input", function () { registrar(c, "revisor", revisor.value); });
  const obs = el("textarea", { placeholder: "Observações (opcional)", rows: "2" });
  obs.value = st.observacoes || "";
  obs.addEventListener("input", function () { registrar(c, "observacoes", obs.value); });
  checklist.appendChild(el("div", { class: "campos" }, [revisor, obs]));
  cardEl.appendChild(checklist);
  return cardEl;
}

function render() {
  const grid = document.getElementById("grid");
  grid.replaceChildren();
  const fTenant = document.getElementById("filtro-tenant").value;
  const fPreset = document.getElementById("filtro-preset").value;
  const fAudio = document.getElementById("filtro-audio").value;
  const visiveis = DATA.campaigns.filter(function (c) {
    return (!fTenant || c.tenantId === fTenant)
      && (!fPreset || c.preset === fPreset)
      && (!fAudio || c.politicaAudio === fAudio);
  });
  visiveis.forEach(function (c) { grid.appendChild(card(c)); });
  document.getElementById("vazio").hidden = visiveis.length > 0;
  document.getElementById("contagem").textContent =
    visiveis.length + " de " + DATA.campaigns.length + " campanhas exibidas";
}

function exportarAprovacoes() {
  const estado = carregarEstado();
  const campanhas = DATA.campaigns.map(function (c) {
    const st = estadoCampanha(c);
    const itens = {};
    ITENS.forEach(function (par) { itens[par[0]] = Boolean((st.itens || {})[par[0]]); });
    const aprovada = ITENS.every(function (par) { return itens[par[0]]; });
    return {
      tenantId: c.tenantId,
      slug: c.slug,
      campaignId: c.campaignId,
      preset: c.preset,
      politicaAudio: c.politicaAudio,
      aprovada: aprovada,
      revisor: st.revisor || "",
      observacoes: st.observacoes || "",
      itens: itens,
      hashes: {
        video: c.video.sha256,
        srt: c.srt.sha256,
        narracao: c.narracao.sha256,
        storyboard: c.storyboard.sha256
      }
    };
  });
  const aprovadas = campanhas.filter(function (c) { return c.aprovada; }).length;
  const payload = {
    schemaVersion: 1,
    arquivo: "aprovacoes-titular.json",
    origem: "05-review-portal",
    exportadoEm: new Date().toISOString(),
    resumo: {
      totalCampanhas: campanhas.length,
      aprovadas: aprovadas,
      pendentes: campanhas.length - aprovadas
    },
    campanhas: campanhas
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "aprovacoes-titular.json";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

(function init() {
  const selTenant = document.getElementById("filtro-tenant");
  DATA.tenants.forEach(function (t) {
    const opt = document.createElement("option");
    opt.value = t.tenantId;
    opt.textContent = t.brandName + " (" + t.tenantId + ")";
    selTenant.appendChild(opt);
  });
  ["filtro-tenant", "filtro-preset", "filtro-audio"].forEach(function (id) {
    document.getElementById(id).addEventListener("change", render);
  });
  document.getElementById("btn-exportar-aprovacoes").addEventListener("click", exportarAprovacoes);
  document.getElementById("sub-titulo").textContent =
    DATA.totals.tenants + " tenants · " + DATA.totals.campaigns + " campanhas";
  render();
})();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Servidor HTTP local (somente leitura, confinado a raiz)
# ---------------------------------------------------------------------------

class _PortalServer(http.server.ThreadingHTTPServer):
    """Servidor multithread que carrega a raiz do checkout."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, portal_root: str) -> None:
        super().__init__(address, handler)
        self.portal_root = portal_root


class _PortalHandler(http.server.BaseHTTPRequestHandler):
    """Handler somente leitura: GET/HEAD, rotas restritas, Range para MP4."""

    server_version = "ReviewPortal/1.0"
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802 (nome exigido pela stdlib)
        self._atender(head_only=False)

    def do_HEAD(self) -> None:  # noqa: N802
        self._atender(head_only=True)

    def _negar(self) -> None:
        self.send_error(404, "Not Found")

    def _atender(self, head_only: bool) -> None:
        root = self.server.portal_root
        raw = self.path.split("?", 1)[0].split("#", 1)[0]
        try:
            path = urllib.parse.unquote(raw)
        except (UnicodeDecodeError, ValueError):
            self._negar()
            return
        if "\\" in path or "\x00" in path:
            self._negar()
            return
        segments = [s for s in path.split("/") if s != ""]
        if any(s == ".." for s in segments):
            self._negar()
            return

        if not segments or segments == ["index.html"]:
            self._servir_arquivo(
                os.path.join(root, PORTAL_DIR_NAME, "index.html"),
                "text/html; charset=utf-8",
                head_only,
            )
            return
        if segments == ["portal-data.json"]:
            self._servir_arquivo(
                os.path.join(root, PORTAL_DIR_NAME, "portal-data.json"),
                "application/json; charset=utf-8",
                head_only,
            )
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
            alvo = os.path.join(root, ARCHIVES_ROOT, *segments[1:])
            self._servir_video(alvo, head_only)
            return
        self._negar()

    def _resolver(self, alvo: str) -> str | None:
        root = self.server.portal_root
        real = os.path.realpath(alvo)
        if not render_local.contained(root, real):
            return None
        if not os.path.isfile(render_local.fs_path(real)):
            return None
        return real

    def _servir_arquivo(self, alvo: str, ctype: str, head_only: bool) -> None:
        real = self._resolver(alvo)
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
        real = self._resolver(alvo)
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
    if not os.path.isfile(render_local.fs_path(indice)):
        raise ReviewPortalError(
            "PORTAL_NAO_GERADO: execute --build antes de --serve"
        )
    try:
        return _PortalServer((host, port), _PortalHandler, root_real)
    except OSError as exc:
        raise ReviewPortalError(f"PORTA_INDISPONIVEL: {host}:{port} ({exc})") from exc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Gerador e servidor local do Portal de Revisao "
            "(05-review-portal). Use --build para gerar e --serve para revisar."
        )
    )
    parser.add_argument("--build", action="store_true", help="Gera o portal consolidado")
    parser.add_argument("--serve", action="store_true", help="Serve o portal via HTTP local")
    parser.add_argument("--output-dir", default=None, help="Diretorio de saida do --build (padrao: 05-review-portal)")
    parser.add_argument("--port", type=int, default=8765, help="Porta do --serve (padrao: 8765)")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument("--json", action="store_true", help="Emite JSON no stdout (apenas --build)")
    args = parser.parse_args(argv)

    if args.build and args.serve:
        print("Erro: informe apenas um modo (--build ou --serve)", file=sys.stderr)
        return 2
    if not args.build and not args.serve:
        print("Erro: informe --build ou --serve", file=sys.stderr)
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

        servidor = make_server(root=args.root, port=args.port)
        porta_real = servidor.server_address[1]
        print(f"Portal de revisao servindo em http://127.0.0.1:{porta_real}/")
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
