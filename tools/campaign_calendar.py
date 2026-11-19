"""Gerador de Calendario Editorial & Matriz UTM (Etapa 4 - Agente 3).

Le os tenants registrados em `tenants/*/` (brand-kit, guardrails e fixture via
`tenant_validator.load_and_validate_tenant`) e os pacotes de publicacao
gerados por `tools/publish_pack.py` em
`04-legendas/pacotes-publicacao/<tenantId>/<slug>/checklist-publicacao.json`
e distribui as campanhas em um cronograma editorial intercalado:

  - ate 2 campanhas por dia, nunca duas campanhas do mesmo tenant no mesmo
    dia (selecao gulosa pelos tenants com mais campanhas restantes);
  - cada campanha cobre os 3 canais configurados (instagram Reels,
    youtube Shorts e facebook Reels), cada canal em sua janela horaria;
  - nenhuma publicacao automatica: `autoPublish: false` e
    `statusEditorial: "aguardando_aprovacao_titular"` em todos os slots.

Saidas versionadas:
  - `04-legendas/calendario-editorial.json` (estrutura completa dos slots)
  - `04-legendas/calendario-editorial.md` (cronograma cronologico, checklist
    pre-publicacao com lembrete de locucao externa para tenants `-an` e
    matriz consolidada das URLs UTM)

Todas as entradas geradas sao auditadas com
`tenant_validator.validate_text_against_guardrails(...,
check_ui_elements=True)` antes de gravar: qualquer termo proibido de
`forbiddenClaims`/`forbiddenUiElements` aborta a geracao sem gravar saida
parcial.

Uso (a partir da raiz do checkout):
    python tools/campaign_calendar.py --start-date 2026-11-23 --json
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import render_local
import tenant_validator

CALENDAR_JSON_REL = os.path.join("04-legendas", "calendario-editorial.json")
CALENDAR_MD_REL = os.path.join("04-legendas", "calendario-editorial.md")
PUBLICACAO_ROOT = os.path.join("04-legendas", "pacotes-publicacao")

CAMPAIGNS_PER_DAY = 2

CHANNELS = ("instagram", "youtube", "facebook")
CHANNEL_META = {
    "instagram": {
        "label": "Instagram Reels",
        "formato": "reels",
        "utm": ("instagram", "reels"),
        "janela": "12:00-13:00",
        "cta": "Conheça o sistema — link na bio",
    },
    "youtube": {
        "label": "YouTube Shorts",
        "formato": "shorts",
        "utm": ("youtube", "shorts"),
        "janela": "18:00-19:00",
        "cta": "Assista até o fim e acesse o link na descrição",
    },
    "facebook": {
        "label": "Facebook Reels",
        "formato": "reels",
        "utm": ("facebook", "reels"),
        "janela": "19:00-20:00",
        "cta": "Acesse pelo link da descrição",
    },
}

STATUS_EDITORIAL = "aguardando_aprovacao_titular"
AUTO_PUBLISH = False


class CampaignCalendarError(Exception):
    """Falha controlada do gerador de calendario editorial."""


def _load_json(path: str) -> dict:
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(render_local.fs_path(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utm_url(domain: str, source: str, medium: str, campaign: str, content: str) -> str:
    """Constroi a URL rastreada no mesmo padrao de tools/publish_pack.py."""
    return (
        f"https://{domain}/?utm_source={source}&utm_medium={medium}"
        f"&utm_campaign={campaign}&utm_content={content}"
    )


def _audio_note(audio_policy: dict) -> str:
    if audio_policy.get("allowAudioTrack"):
        return "Vídeo com faixa de áudio própria (permitida pelo guardrail do tenant)."
    return (
        "Vídeo sem faixa de áudio (`-an`). Locução externa opcional, gravada fora do "
        "editor a partir do arquivo `_narracao.txt`; não é requisito para publicar o "
        "vídeo legendado."
    )


def discover_campaigns(root_real: str) -> list[dict]:
    """Descobre as campanhas com pacote de publicacao valido por tenant."""
    campaigns: list[dict] = []
    for tenant_id in tenant_validator.list_tenants(root_real):
        ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=root_real, strict=True)
        brand = ctx["brandKit"]
        guardrails = ctx["guardrails"]

        pkg_tenant_dir = os.path.realpath(os.path.join(root_real, PUBLICACAO_ROOT, tenant_id))
        if not render_local.contained(root_real, pkg_tenant_dir):
            raise CampaignCalendarError(f"PACOTE_FORA_DA_RAIZ: {tenant_id}")
        if not os.path.isdir(render_local.fs_path(pkg_tenant_dir)):
            continue

        for slug in sorted(
            name for name in os.listdir(render_local.fs_path(pkg_tenant_dir))
            if os.path.isdir(render_local.fs_path(os.path.join(pkg_tenant_dir, name)))
        ):
            checklist_path = os.path.join(pkg_tenant_dir, slug, "checklist-publicacao.json")
            if not os.path.isfile(render_local.fs_path(checklist_path)):
                continue
            checklist = _load_json(checklist_path)
            if checklist.get("tenantId") != tenant_id:
                raise CampaignCalendarError(
                    f"TENANT_DIVERGENTE: checklist de {tenant_id}/{slug} declara "
                    f"'{checklist.get('tenantId')}'"
                )
            if checklist.get("autoPublish") is not False:
                raise CampaignCalendarError(
                    f"AUTO_PUBLICACAO_INVALIDO: {tenant_id}/{slug} declara autoPublish != false"
                )
            campaigns.append(
                {
                    "tenantId": tenant_id,
                    "brandName": brand.get("brandName", ""),
                    "domain": brand.get("domain", ""),
                    "tagline": brand.get("tagline", ""),
                    "slug": slug,
                    "preset": checklist.get("preset"),
                    "audioPolicy": dict(guardrails.get("audioPolicy", {})),
                    "guardrails": guardrails,
                }
            )

    if not campaigns:
        raise CampaignCalendarError(
            "NENHUMA_CAMPANHA: nenhum checklist-publicacao.json encontrado"
        )
    return campaigns


def distribute_campaigns(
    campaigns: list[dict], per_day: int = CAMPAIGNS_PER_DAY
) -> list[list[dict]]:
    """Distribui campanhas em dias intercalados, sem repetir tenant no mesmo dia."""
    queues: dict[str, list[dict]] = {}
    for campaign in sorted(campaigns, key=lambda c: (c["tenantId"], c["slug"])):
        queues.setdefault(campaign["tenantId"], []).append(campaign)

    days: list[list[dict]] = []
    while any(queues.values()):
        order = sorted(
            (tenant_id for tenant_id in queues if queues[tenant_id]),
            key=lambda tenant_id: (-len(queues[tenant_id]), tenant_id),
        )
        day: list[dict] = []
        for tenant_id in order:
            if len(day) >= per_day:
                break
            day.append(queues[tenant_id].pop(0))
        days.append(day)
    return days


def build_calendar(start_date: str, root: str = ".") -> dict:
    """Constrói o calendário editorial completo (sem gravar em disco)."""
    root_real = os.path.realpath(root)
    try:
        start = datetime.date.fromisoformat(start_date)
    except ValueError as exc:
        raise CampaignCalendarError(
            f"DATA_INVALIDA: {start_date} (esperado YYYY-MM-DD)"
        ) from exc

    campaigns = discover_campaigns(root_real)
    days = distribute_campaigns(campaigns)

    slots: list[dict] = []
    violations: list[str] = []
    index = 0
    for day_offset, day_campaigns in enumerate(days):
        date_str = (start + datetime.timedelta(days=day_offset)).isoformat()
        for channel in CHANNELS:
            meta = CHANNEL_META[channel]
            for campaign in day_campaigns:
                index += 1
                utm_url = _utm_url(
                    campaign["domain"],
                    meta["utm"][0],
                    meta["utm"][1],
                    campaign["slug"],
                    campaign["tenantId"],
                )
                audio_note = _audio_note(campaign["audioPolicy"])
                audit_text = "\n".join(
                    [
                        campaign["brandName"],
                        campaign["tagline"],
                        meta["cta"],
                        utm_url,
                        audio_note,
                    ]
                )
                found = tenant_validator.validate_text_against_guardrails(
                    audit_text, campaign["guardrails"], check_ui_elements=True
                )
                for violation in found:
                    violations.append(
                        f"{campaign['tenantId']}/{campaign['slug']}/{channel}: {violation}"
                    )
                slots.append(
                    {
                        "slotId": f"slot-{index:03d}",
                        "dataSugerida": date_str,
                        "janelaHorario": meta["janela"],
                        "tenantId": campaign["tenantId"],
                        "brandName": campaign["brandName"],
                        "slug": campaign["slug"],
                        "canal": channel,
                        "formato": meta["formato"],
                        "audioPolicy": campaign["audioPolicy"],
                        "utmUrl": utm_url,
                        "statusEditorial": STATUS_EDITORIAL,
                        "autoPublish": AUTO_PUBLISH,
                    }
                )

    if violations:
        raise CampaignCalendarError("GUARDRAIL_VIOLACAO: " + "; ".join(violations))

    tenants_used = sorted({campaign["tenantId"] for campaign in campaigns})
    return {
        "schemaVersion": 1,
        "generatedBy": "tools/campaign_calendar.py",
        "startDate": start.isoformat(),
        "endDate": (start + datetime.timedelta(days=len(days) - 1)).isoformat(),
        "campaignsPerDay": CAMPAIGNS_PER_DAY,
        "channels": list(CHANNELS),
        "tenants": tenants_used,
        "totalTenants": len(tenants_used),
        "totalCampaigns": len(campaigns),
        "totalSlots": len(slots),
        "statusEditorial": STATUS_EDITORIAL,
        "autoPublish": AUTO_PUBLISH,
        "guardrailsAudited": True,
        "guardrailViolations": [],
        "slots": slots,
    }


def _render_md(calendar: dict) -> str:
    slots = calendar["slots"]
    an_tenants = sorted(
        {s["tenantId"] for s in slots if not s["audioPolicy"].get("allowAudioTrack", False)}
    )
    audio_tenants = sorted(
        {s["tenantId"] for s in slots if s["audioPolicy"].get("allowAudioTrack", False)}
    )

    lines: list[str] = []
    lines.append("# Calendário Editorial — Content Factory Multi-Tenant")
    lines.append("")
    lines.append(f"> Gerado por `tools/campaign_calendar.py --start-date {calendar['startDate']}`.")
    lines.append(
        f"> Período sugerido: **{calendar['startDate']}** a **{calendar['endDate']}** — "
        f"{calendar['totalCampaigns']} campanhas de {calendar['totalTenants']} tenants, "
        f"{calendar['totalSlots']} slots ({calendar['totalCampaigns']} campanhas × 3 canais), "
        f"até {calendar['campaignsPerDay']} campanhas por dia."
    )
    lines.append("> Publicação 100% manual: `autoPublish: false` em todos os slots.")
    lines.append(
        "> Status editorial: `aguardando_aprovacao_titular` — nenhuma publicação sem "
        "aprovação expressa do titular."
    )
    lines.append("")

    lines.append("## 1. Cronograma editorial (ordem cronológica)")
    lines.append("")
    lines.append(
        "| Slot | Data sugerida | Janela | Tenant | Marca | Campanha | Canal | Formato | Áudio |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for slot in slots:
        audio = (
            "com áudio"
            if slot["audioPolicy"].get("allowAudioTrack", False)
            else "`-an` (sem áudio)"
        )
        lines.append(
            f"| {slot['slotId']} | {slot['dataSugerida']} | {slot['janelaHorario']} "
            f"| {slot['tenantId']} | {slot['brandName']} | `{slot['slug']}` "
            f"| {CHANNEL_META[slot['canal']]['label']} | {slot['formato']} | {audio} |"
        )
    lines.append("")

    lines.append("## 2. Checklist pré-publicação (por slot)")
    lines.append("")
    lines.append(
        "1. **Aprovação do titular:** o slot só entra em produção após aprovação expressa; "
        "o status editorial é `aguardando_aprovacao_titular`."
    )
    lines.append(
        "2. **Publicação manual:** nenhuma ferramenta publica ou agenda sozinha "
        "(`autoPublish: false`); publicar direto na rede ou via Postiz, conforme "
        "autorização do titular."
    )
    lines.append(
        "3. **Mídia e integridade:** conferir no pacote "
        "`04-legendas/pacotes-publicacao/<tenant>/<slug>/checklist-publicacao.json` os "
        "hashes SHA-256 (`sha256_disk_ok: true`) antes de anexar o vídeo."
    )
    lines.append(
        "4. **Legenda por canal:** usar o arquivo do canal no pacote "
        "(`instagram-reels.md`, `youtube-shorts.md`, `facebook-reels.md`), incluindo a "
        "URL UTM do slot exatamente como gerada."
    )
    lines.append(
        "5. **Instagram:** CTA \"Conheça o sistema — link na bio\"; conferir o link "
        "externo real cadastrado no perfil antes de prometer o acesso."
    )
    lines.append(
        "6. **Facebook e YouTube:** URL completa na descrição com \"Acesse pelo link da "
        "descrição\"; não simular botão clicável na imagem."
    )
    lines.append(
        f"7. **Locução externa (tenants `-an`: "
        f"{', '.join(f'`{t}`' for t in an_tenants)}):** o vídeo é entregue sem faixa de "
        "áudio; a narração de `<slug>_narracao.txt` é gravada fora do editor, pelo "
        "titular, quando desejado — não é requisito para publicar o vídeo legendado."
    )
    if audio_tenants:
        lines.append(
            f"8. **Tenants com áudio próprio ({', '.join(f'`{t}`' for t in audio_tenants)}):** "
            "o vídeo já sai com a faixa de áudio permitida pelo guardrail do tenant."
        )
    lines.append(
        "9. **UTM:** não alterar os parâmetros UTM de posts já publicados; qualquer "
        "mudança invalida o histórico de dados."
    )
    lines.append(
        "10. **Analytics:** enquanto a ferramenta de analytics estiver PENDENTE "
        "(`docs/rastreio-utm.md`, seção 5), não declarar links UTM como ativos em "
        "registros de campanha."
    )
    lines.append("")


    lines.append(
        f"## 3. Matriz UTM consolidada ({calendar['totalCampaigns']} campanhas × "
        f"{len(calendar['channels'])} canais = {calendar['totalSlots']} URLs)"
    )
    lines.append("")
    lines.append("| Tenant | Campanha | Canal | URL rastreada |")
    lines.append("|---|---|---|---|")
    matrix_slots = sorted(
        slots,
        key=lambda s: (s["tenantId"], s["slug"], CHANNELS.index(s["canal"])),
    )
    for slot in matrix_slots:
        lines.append(
            f"| {slot['tenantId']} | `{slot['slug']}` "
            f"| {CHANNEL_META[slot['canal']]['label']} | {slot['utmUrl']} |"
        )
    lines.append("")
    lines.append("> [!IMPORTANT]")
    lines.append(
        "> Enquanto a ferramenta de analytics (seção 5 de `docs/rastreio-utm.md`) "
        "estiver como PENDENTE,"
    )
    lines.append(
        "> nenhum link UTM acima deve ser declarado como ativo em registros de campanha."
    )
    lines.append("")
    return "\n".join(lines)


def write_calendar(calendar: dict, root: str = ".") -> dict:
    """Grava o calendario editorial em JSON e Markdown (UTF-8, LF)."""
    root_real = os.path.realpath(root)
    targets = (
        ("json", CALENDAR_JSON_REL, json.dumps(calendar, ensure_ascii=False, indent=2) + "\n"),
        ("md", CALENDAR_MD_REL, _render_md(calendar)),
    )
    outputs: dict[str, dict] = {}
    for kind, rel_path, content in targets:
        abs_path = os.path.realpath(os.path.join(root_real, rel_path))
        if not render_local.contained(root_real, abs_path):
            raise CampaignCalendarError(f"SAIDA_FORA_DA_RAIZ: {rel_path}")
        os.makedirs(render_local.fs_path(os.path.dirname(abs_path)), exist_ok=True)
        with open(render_local.fs_path(abs_path), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        outputs[kind] = {
            "path": render_local.rel(root_real, abs_path),
            "sha256": _sha256_file(abs_path),
            "bytes": os.path.getsize(render_local.fs_path(abs_path)),
        }
    return outputs


def generate_calendar(start_date: str, root: str = ".") -> dict:
    """Constrói, audita e grava o calendário editorial. Devolve o resumo."""
    calendar = build_calendar(start_date, root=root)
    outputs = write_calendar(calendar, root=root)
    return {
        "ok": True,
        "startDate": calendar["startDate"],
        "endDate": calendar["endDate"],
        "campaignsPerDay": calendar["campaignsPerDay"],
        "totalTenants": calendar["totalTenants"],
        "totalCampaigns": calendar["totalCampaigns"],
        "totalSlots": calendar["totalSlots"],
        "guardrailsAudited": calendar["guardrailsAudited"],
        "guardrailViolations": calendar["guardrailViolations"],
        "outputs": outputs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gerador de calendario editorial e matriz UTM multi-tenant"
    )
    parser.add_argument("--start-date", required=True, help="Data inicial do cronograma (YYYY-MM-DD)")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument("--json", action="store_true", help="Emite JSON no stdout")
    args = parser.parse_args(argv)

    try:
        datetime.date.fromisoformat(args.start_date)
    except ValueError:
        print(
            f"Erro: --start-date invalida: {args.start_date} (esperado YYYY-MM-DD)",
            file=sys.stderr,
        )
        return 2

    try:
        result = generate_calendar(args.start_date, root=args.root)
    except CampaignCalendarError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro: entrada invalida ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"Calendario gerado: {result['totalSlots']} slots "
            f"({result['totalCampaigns']} campanhas, {result['totalTenants']} tenants) "
            f"de {result['startDate']} a {result['endDate']}"
        )
        for kind in ("json", "md"):
            entry = result["outputs"][kind]
            print(f"  - {entry['path']} ({entry['bytes']} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
