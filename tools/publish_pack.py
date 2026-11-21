"""Gerador de pacotes de publicacao (Agente 3 - Publicacao e UTM).

Le uma entrega ja renderizada em
    02-reels-shorts/deliveries/<tenantId>/<slug>/  (manifest.json, <slug>.srt,
    <slug>_narracao.txt)
o brand-kit.json (domain, utmDefaults) e o guardrails.json do respectivo
tenant e gera em
    04-legendas/pacotes-publicacao/<tenantId>/<slug>/
os arquivos:
    instagram-reels.md, youtube-shorts.md, facebook-reels.md e
    checklist-publicacao.json.

Todas as copias de legenda geradas sao auditadas com
tenant_validator.validate_text_against_guardrails(...) antes de gravar: se
qualquer palavra proibida de forbiddenClaims/forbiddenUiElements aparecer, o
script aborta com erro explicitamente e nao grava o pacote parcial.

Resolucao de ``.workspace/``: os MP4s nao sao versionados e vivem em
``<workspace>/archives/<slug>/`` no checkout principal. ``resolve_workspace_root``
usa ``git rev-parse --git-common-dir`` para alcancar esse ``.workspace/``
quando o script roda em qualquer worktree; o checklist registra
``sha256_disk_ok`` conferindo a midia arquivada, e nao um caminho inexistente
dentro da worktree.

Ponto unico de entrada para o tenant:
    ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=REPO_ROOT, strict=True)

Uso (a partir da raiz do checkout):
    python tools/publish_pack.py --all
    python tools/publish_pack.py --tenant marca-salao --slug camp-saas-demo-marca-salao-001

Retrocompativel: nao modifica entregas ja renderizadas nem arquivos de
outros agentes. Gera apenas novos pacotes em 04-legendas/pacotes-publicacao/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import render_local
import tenant_validator

DELIVERIES_ROOT = os.path.join("02-reels-shorts", "deliveries")
PUBLICACAO_ROOT = os.path.join("04-legendas", "pacotes-publicacao")

CHANNELS = ("instagram-reels", "youtube-shorts", "facebook-reels")
CHANNEL_FILES = {
    "instagram-reels": "instagram-reels.md",
    "youtube-shorts": "youtube-shorts.md",
    "facebook-reels": "facebook-reels.md",
}

UTM_BY_CHANNEL = {
    "instagram-reels": ("instagram", "reels"),
    "youtube-shorts": ("youtube", "shorts"),
    "facebook-reels": ("facebook", "reels"),
}

CHANNEL_CTA = {
    "instagram-reels": "Conheca o sistema — link na bio",
    "youtube-shorts": "Assista ate o fim e acesse o link na descricao",
    "facebook-reels": "Acesse pelo link da descricao",
}

CHANNEL_INTRO = {
    "instagram-reels": "",
    "youtube-shorts": "",
    "facebook-reels": "",
}


class PublishPackError(Exception):
    """Falha controlada do gerador de pacotes de publicacao."""


def _load_json(path: str) -> dict:
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(render_local.fs_path(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _main_checkout_root(root: str) -> str | None:
    """Raiz do checkout principal: pai do ``.git`` comum apontado pela worktree."""
    try:
        res = subprocess.run(
            ["git", "-C", root, "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if res.returncode != 0 or not res.stdout.strip():
        return None
    git_dir = os.path.normpath(os.path.join(os.path.realpath(root), res.stdout.strip()))
    main_root = os.path.dirname(git_dir)
    return main_root if os.path.isdir(render_local.fs_path(main_root)) else None


def resolve_workspace_root(root: str = ".") -> str:
    """Resolve o ``.workspace/`` aplicavel a raiz informada.

    Prefere ``<raiz>/.workspace`` quando ele tem ``archives/``; em worktree
    (sem ``.workspace/`` proprio) resolve o checkout principal via
    ``git rev-parse --git-common-dir`` e usa o ``.workspace/`` de la, onde
    vivem os MP4s preservados. Raizes que nao sao toplevel de checkout caem
    no proprio ``<raiz>/.workspace``.
    """
    root_real = os.path.realpath(root)
    candidate = os.path.join(root_real, ".workspace")
    if os.path.isdir(render_local.fs_path(os.path.join(candidate, "archives"))):
        return candidate
    main_root = _main_checkout_root(root_real)
    main_ws = os.path.join(main_root, ".workspace") if main_root else ""
    if main_ws and os.path.isdir(render_local.fs_path(os.path.join(main_ws, "archives"))):
        return main_ws
    if os.path.isdir(render_local.fs_path(candidate)):
        return candidate
    if main_ws and os.path.isdir(render_local.fs_path(main_ws)):
        return main_ws
    return candidate


def _resolve_artifact_path(
    root_real: str, workspace_root: str, entry: dict
) -> tuple[str | None, str]:
    """Caminho em disco de um artefato do manifesto e a origem resolvida.

    O video preservado declara ``archivePath`` (``.workspace/archives/...``);
    ele e resolvido contra o ``.workspace/`` do checkout principal. Os demais
    artefatos sao versionados e ficam sob a raiz do checkout.
    """
    archive_rel = str(entry.get("archivePath") or "")
    if archive_rel.startswith(".workspace/"):
        target = os.path.realpath(
            os.path.join(workspace_root, archive_rel[len(".workspace/"):].replace("/", os.sep))
        )
        if render_local.contained(workspace_root, target):
            return target, "archive"
        return None, "fora_da_raiz"
    rel_path = str(entry.get("path") or "")
    if not rel_path:
        return None, "sem_caminho"
    target = os.path.realpath(os.path.join(root_real, rel_path.replace("/", os.sep)))
    if render_local.contained(root_real, target):
        return target, "delivery"
    return None, "fora_da_raiz"


def _parse_srt_blocks(srt_text: str) -> list[dict]:
    """Devolve lista de blocos {index, start, end, text} de um SRT."""
    blocks: list[dict] = []
    raw_blocks = re.split(r"\n\s*\n", srt_text.strip("\n"))
    for block in raw_blocks:
        lines = block.split("\n")
        if len(lines) < 3:
            continue
        m = re.match(r"^(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})$", lines[1].strip())
        if not m:
            continue
        blocks.append(
            {
                "index": int(lines[0].strip()) if lines[0].strip().isdigit() else len(blocks) + 1,
                "start": m.group(1),
                "end": m.group(2),
                "text": "\n".join(lines[2:]).strip(),
            }
        )
    return blocks


def _audit(text: str, label: str, guardrails: dict) -> None:
    """Audita um texto contra os guardrails; levanta PublishPackError em caso de proibido."""
    violations = tenant_validator.validate_text_against_guardrails(
        text, guardrails, check_ui_elements=True, ignore_editorial_footer=True
    )
    if violations:
        raise PublishPackError(
            f"GUARDRAIL_VIOLACAO em {label}: " + "; ".join(violations)
        )


def _utm_url(domain: str, source: str, medium: str, campaign: str, content: str) -> str:
    """Constroi a URL rastreada com UTMs."""
    return (
        f"https://{domain}/?utm_source={source}&utm_medium={medium}"
        f"&utm_campaign={campaign}&utm_content={content}"
    )


def _build_instagram_reels(
    brand: dict, guardrails: dict, slug: str, srt_text: str, narration_text: str
) -> str:
    domain = brand.get("domain", "")
    url = _utm_url(domain, "instagram", "reels", slug, brand.get("tenantId", ""))
    brand_name = brand.get("brandName", "")
    tagline = brand.get("tagline", "")

    linhas = [
        f"Conheca o {brand_name}",
        "",
        tagline,
        "",
        "Agendamento online, agenda do salao e profissionais a poucos toques.",
        "",
        url,
        "",
        "Conheca o sistema — link na bio",
        "",
        "#MarcaSalao #AgendamentoOnline #AgendaDoSalao",
    ]
    texto = "\n".join(linhas)
    _audit(texto, "instagram-reels.md", guardrails)
    return texto


def _build_youtube_shorts(
    brand: dict, guardrails: dict, slug: str, srt_text: str, narration_text: str
) -> str:
    domain = brand.get("domain", "")
    url = _utm_url(domain, "youtube", "shorts", slug, brand.get("tenantId", ""))
    brand_name = brand.get("brandName", "")
    tagline = brand.get("tagline", "")

    blocks = _parse_srt_blocks(srt_text)
    capitulos = "\n".join(
        f"- {b['start']} — {b['text']}" for b in blocks[:5]
    ) if blocks else "- (sem capitulos extraídos do SRT)"

    linhas = [
        f"{brand_name} — {tagline}",
        "",
        "Descubra como organizar a agenda do seu salao em poucos minutos.",
        "",
        "Capitulos:",
        capitulos,
        "",
        url,
        "",
        "Assista ate o fim e acesse o link na descricao",
        "",
        "#MultitrackHub #Shorts #Stems #Rateios"
        if brand.get("tenantId") == "multitrack-hub"
        else "#MarcaSalao #AgendamentoOnline #Shorts",
    ]
    texto = "\n".join(linhas)
    _audit(texto, "youtube-shorts.md", guardrails)
    return texto


def _build_facebook_reels(
    brand: dict, guardrails: dict, slug: str, srt_text: str, narration_text: str
) -> str:
    domain = brand.get("domain", "")
    url = _utm_url(domain, "facebook", "reels", slug, brand.get("tenantId", ""))
    brand_name = brand.get("brandName", "")
    tagline = brand.get("tagline", "")

    linhas = [
        f"Conheca o {brand_name}",
        "",
        tagline,
        "",
        "Agende cortes, escovas, hidratacoes e muito mais direto pela agenda online.",
        "",
        url,
        "",
        "Acesse pelo link da descricao",
        "",
        "#MarcaSalao #AgendamentoOnline #Reels",
    ]
    texto = "\n".join(linhas)
    _audit(texto, "facebook-reels.md", guardrails)
    return texto


def _build_checklist(
    manifest: dict, brand: dict, guardrails: dict, slug: str, root_real: str, workspace_root: str
) -> dict:
    artifacts = manifest.get("artifacts", {})
    media_files = []
    for kind in ("video", "srt", "narration", "storyboard"):
        entry = artifacts.get(kind, {})
        rel_path = entry.get("path")
        if not rel_path:
            continue
        abs_path, source = _resolve_artifact_path(root_real, workspace_root, entry)
        exists = bool(abs_path) and os.path.isfile(render_local.fs_path(abs_path))
        media_files.append(
            {
                "kind": kind,
                "path": rel_path,
                "archivePath": entry.get("archivePath"),
                "resolvedFrom": source,
                "sha256": entry.get("sha256"),
                "bytes": entry.get("bytes"),
                "sha256_disk_ok": (
                    exists and _sha256_file(abs_path) == entry.get("sha256")
                ),
                "presentOnDisk": exists,
            }
        )

    # Auditoria de guardrails sobre os textos da entrega (referencia)
    def _audit_artifact(kind: str) -> tuple[str, list[str]]:
        entry = artifacts.get(kind, {})
        abs_path, _ = _resolve_artifact_path(root_real, workspace_root, entry)
        if not abs_path or not os.path.isfile(render_local.fs_path(abs_path)):
            return "arquivo_nao_encontrado", []
        try:
            with open(render_local.fs_path(abs_path), "r", encoding="utf-8") as handle:
                texto = handle.read()
        except OSError:
            return "arquivo_nao_encontrado", []
        violations = tenant_validator.validate_text_against_guardrails(
            texto, guardrails, check_ui_elements=True
        )
        return ("ok" if not violations else "violacao"), violations

    srt_status, srt_violations = _audit_artifact("srt")
    narration_status, narration_violations = _audit_artifact("narration")
    guardrail_status = {
        "srt": srt_status,
        "narration": narration_status,
        "srt_violations": srt_violations,
        "narration_violations": narration_violations,
    }

    return {
        "slug": slug,
        "tenantId": manifest.get("tenantId"),
        "preset": manifest.get("preset"),
        "allowAudioTrack": bool(guardrails.get("audioPolicy", {}).get("allowAudioTrack", False)),
        "requireSrt": bool(guardrails.get("audioPolicy", {}).get("requireSrt", False)),
        "guardrailsAudited": True,
        "guardrailStatus": guardrail_status,
        "media": media_files,
        "autoPublish": False,
        "generatedBy": "tools/publish_pack.py",
    }


def generate_pack(tenant_id: str, slug: str, root: str = ".") -> dict:
    """Gera o pacote de publicacao de uma entrega. Devolve o dicionario do pacote."""
    root_real = os.path.realpath(root)

    # Ponto unico de entrada do tenant (brandKit, guardrails, fixture).
    ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=root_real, strict=True)
    brand = ctx["brandKit"]
    guardrails = ctx["guardrails"]

    # Localiza a entrega renderizada.
    delivery_dir = os.path.realpath(os.path.join(root_real, DELIVERIES_ROOT, tenant_id, slug))
    if not render_local.contained(root_real, delivery_dir):
        raise PublishPackError(f"DELIVERY_FORA_DA_RAIZ: {tenant_id}/{slug}")
    if not os.path.isdir(render_local.fs_path(delivery_dir)):
        raise PublishPackError(f"DELIVERY_NAO_ENCONTRADA: {render_local.rel(root_real, delivery_dir)}")

    manifest_path = os.path.join(delivery_dir, "manifest.json")
    srt_path = os.path.join(delivery_dir, f"{slug}.srt")
    narration_path = os.path.join(delivery_dir, f"{slug}_narracao.txt")
    for label, path in (("manifest", manifest_path), ("srt", srt_path), ("narracao", narration_path)):
        if not os.path.isfile(render_local.fs_path(path)):
            raise PublishPackError(f"{label.upper()}_NAO_ENCONTRADO: {render_local.rel(root_real, path)}")

    manifest = _load_json(manifest_path)
    with open(render_local.fs_path(srt_path), "r", encoding="utf-8") as handle:
        srt_text = handle.read()
    with open(render_local.fs_path(narration_path), "r", encoding="utf-8") as handle:
        narration_text = handle.read()

    # Diretorio de saida do pacote.
    out_dir = os.path.realpath(os.path.join(root_real, PUBLICACAO_ROOT, tenant_id, slug))
    if not render_local.contained(root_real, out_dir):
        raise PublishPackError(f"SAIDA_FORA_DA_RAIZ: {tenant_id}/{slug}")
    os.makedirs(render_local.fs_path(out_dir), exist_ok=True)

    # Gera cada copia de legenda, auditando antes de gravar.
    conteudos: dict[str, str] = {}
    conteudos["instagram-reels.md"] = _build_instagram_reels(
        brand, guardrails, slug, srt_text, narration_text
    )
    conteudos["youtube-shorts.md"] = _build_youtube_shorts(
        brand, guardrails, slug, srt_text, narration_text
    )
    conteudos["facebook-reels.md"] = _build_facebook_reels(
        brand, guardrails, slug, srt_text, narration_text
    )

    written: dict[str, dict] = {}
    for filename, texto in conteudos.items():
        abs_path = os.path.join(out_dir, filename)
        with open(render_local.fs_path(abs_path), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(texto)
        written[filename] = {
            "path": render_local.rel(root_real, abs_path),
            "sha256": _sha256_file(abs_path),
            "bytes": os.path.getsize(render_local.fs_path(abs_path)),
            "guardrailsAudited": True,
        }

    # Checklist JSON.
    checklist = _build_checklist(
        manifest, brand, guardrails, slug, root_real, resolve_workspace_root(root_real)
    )
    checklist_path = os.path.join(out_dir, "checklist-publicacao.json")
    with open(render_local.fs_path(checklist_path), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(checklist, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    written["checklist-publicacao.json"] = {
        "path": render_local.rel(root_real, checklist_path),
        "sha256": _sha256_file(checklist_path),
        "bytes": os.path.getsize(render_local.fs_path(checklist_path)),
        "guardrailsAudited": True,
    }

    return {
        "tenantId": tenant_id,
        "slug": slug,
        "outputDir": render_local.rel(root_real, out_dir),
        "files": written,
        "checklist": checklist,
    }


def generate_all(root: str = ".") -> list[dict]:
    """Gera pacotes para todas as entregas existentes em 02-reels-shorts/deliveries/."""
    root_real = os.path.realpath(root)
    deliveries_root = os.path.realpath(os.path.join(root_real, DELIVERIES_ROOT))
    if not os.path.isdir(render_local.fs_path(deliveries_root)):
        return []

    results: list[dict] = []
    for tenant_id in sorted(
        name for name in os.listdir(render_local.fs_path(deliveries_root))
        if os.path.isdir(render_local.fs_path(os.path.join(deliveries_root, name)))
    ):
        tenant_dir = os.path.join(deliveries_root, tenant_id)
        for slug in sorted(
            name for name in os.listdir(render_local.fs_path(tenant_dir))
            if os.path.isdir(render_local.fs_path(os.path.join(tenant_dir, name)))
        ):
            results.append(generate_pack(tenant_id, slug, root=root_real))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gerador de pacotes de publicacao com UTMs e auditoria de guardrails"
    )
    parser.add_argument("--tenant", help="Slug do tenant (marca-salao, meu-salao, multitrack-hub)")
    parser.add_argument("--slug", help="Slug da entrega (ex.: camp-saas-demo-marca-salao-001)")
    parser.add_argument("--all", action="store_true", help="Gera pacotes para todas as entregas")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument("--json", action="store_true", help="Emite JSON no stdout")
    args = parser.parse_args(argv)

    try:
        if args.all:
            results = generate_all(root=args.root)
        elif args.tenant and args.slug:
            results = [generate_pack(args.tenant, args.slug, root=args.root)]
        else:
            print("Erro: informe --all ou --tenant <id> --slug <slug>", file=sys.stderr)
            return 2
    except PublishPackError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro: entrada invalida ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for res in results:
            print(f"Pacote gerado: {res['outputDir']} ({len(res['files'])} arquivos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
