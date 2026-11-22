"""Gerador de Calendario Editorial 4 Semanas & Matriz UTM (Etapa 4 - Agente 3, v2).

Le os tenants registrados em `tenants/*/` (brand-kit, guardrails e fixture via
`tenant_validator.load_and_validate_tenant`) e os pacotes de publicacao
gerados por `tools/publish_pack.py` em
`04-legendas/pacotes-publicacao/<tenantId>/<slug>/` (checklist-publicacao.json
e as legendas .md de cada canal) e distribui as campanhas em um cronograma
editorial de duas ondas ao longo de `--weeks` semanas:

  Onda 1 (semanas 1..onda1Weeks) - lancamentos 9:16:
    - 8 campanhas x 3 canais (YouTube Shorts, Instagram Reels, Facebook
      Reels) = 24 slots, ate 2 campanhas por dia util;
    - nunca duas publicacoes do mesmo tenant no mesmo dia;
    - os 3 canais da mesma campanha ficam espacados em dias uteis distintos
      com no minimo 48 horas de distancia entre publicacoes (ordem
      youtube -> instagram -> facebook nos deslocamentos +0/+2/+4: com as
      janelas fixas 12:00 / 18:30 / 20:00 BRT essa e a unica ordem que
      respeita o piso de 48h — youtube 12:00 D, instagram 18:30 D+2 = 54,5h,
      facebook 20:00 D+4 = 49,5h);
    - dias uteis de segunda a sabado (domingo nunca e dia de publicacao),
      equilibrando os 6 dias publicaveis de cada semana.

  Onda 2 (semanas seguintes) - reaproveitamento multiformato:
    - 1 slot por campanha, 1 campanha por dia, alternando Instagram Feed
      (1:1, utm_content=repurpose-1x1) e YouTube Video (16:9,
      utm_content=repurpose-16x9) pela ordem de slug;
    - zero colisao de tenant no mesmo dia por construcao.

Hooks A/B por slot:
  - hookVarianteA: abertura original extraida da primeira linha da legenda
    do canal no pacote (instagram-reels.md / youtube-shorts.md /
    facebook-reels.md);
  - hookVarianteB: abertura alternativa de clareza operacional por nicho
    (salao/agenda, link de agendamento, aulas/turmas em estudio,
    stems/rateios multitrack).

AUDITORIA OBRIGATORIA: todo texto gerado (hooks A e B, notas operacionais,
checklist pre-publicacao e URLs UTM de cada slot) e auditado contra os
guardrails do PROPRIO tenant com
`tenant_validator.validate_text_against_guardrails(...,
check_ui_elements=True)` antes de qualquer gravacao; qualquer termo proibido
de `forbiddenClaims`/`forbiddenUiElements` aborta a geracao sem gravar saida
parcial. O texto de um tenant nunca e auditado contra guardrails de outro
("meu salao" e forbiddenClaim de marca-salao).

Saidas versionadas (UTF-8, LF, deterministicas — sem timestamps):
  - `04-legendas/calendario-editorial.json` (32 slots estruturados, regras
    aplicadas e metricas por tenant/canal);
  - `04-legendas/calendario-editorial.md` (resumo executivo por tenant e por
    canal, cronograma cronologico completo das 4 semanas, checklist de
    operacao manual pre-publicacao e referencia rapida das URLs UTM);
  - `04-legendas/matriz-utm-consolidada.csv` (32 linhas, 20 colunas
    padronizadas, pronto para Google Sheets/Excel/Looker Studio).

Nenhuma publicacao automatica: `autoPublish: false` e
`statusEditorial: "aguardando_aprovacao_titular"` em todos os slots.

Uso (a partir da raiz do checkout):
    python tools/campaign_calendar.py --start-date 2026-11-23 --weeks 4 --json

Uso programatico:
    calendar = campaign_calendar.build_editorial_calendar(
        "2026-11-23", weeks=4, root=REPO_ROOT)
"""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import render_local
import tenant_validator

CALENDAR_JSON_REL = os.path.join("04-legendas", "calendario-editorial.json")
CALENDAR_MD_REL = os.path.join("04-legendas", "calendario-editorial.md")
UTM_CSV_REL = os.path.join("04-legendas", "matriz-utm-consolidada.csv")
PUBLICACAO_ROOT = os.path.join("04-legendas", "pacotes-publicacao")
BUNDLE_ATTRIBUTION_DEFAULT = os.path.join(".workspace", "tmp", "utm-report", "bundle-attribution.json")

# Comparativo de hooks A/B (configurado em utm_report_importer.py).
HOOK_COMPARISON_KEY = "hookComparison"
HOOK_RECOMENDADO_FIELD = "hookRecomendado"
HOOK_JUSTIFICATIVA_FIELD = "hookRecomendadoJustificativa"
HOOK_SEM_DADOS = "testar_ab"
HOOK_CLASSIFICACOES = (
    "vencedor_A",
    "vencedor_B",
    "empate_tecnico",
    "amostra_insuficiente",
)

WEEKS_DEFAULT = 4
CAMPAIGNS_PER_LANE = 2
CHANNEL_SPACING_HOURS = 48
PUBLISHABLE_DAYS_PER_WEEK = 6

WEEKDAY_NAMES = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}
PUBLISHABLE_WEEKDAYS = frozenset({0, 1, 2, 3, 4, 5})

CHANNEL_WINDOWS = {
    "instagram": "18:30-19:30",
    "youtube": "12:00-13:00",
    "facebook": "20:00-21:00",
}
CHANNEL_LABELS_ONDA1 = {
    "instagram": "Instagram Reels",
    "youtube": "YouTube Shorts",
    "facebook": "Facebook Reels",
}
CHANNEL_LABELS_ONDA2 = {
    "instagram": "Instagram Feed",
    "youtube": "YouTube Vídeo",
}
CHANNEL_UTM_MEDIUM_ONDA1 = {
    "instagram": "reels",
    "youtube": "shorts",
    "facebook": "reels",
}
CHANNEL_UTM_MEDIUM_ONDA2 = {
    "instagram": "feed",
    "youtube": "video",
}
CHANNEL_CAPTION_FILE = {
    "instagram": "instagram-reels.md",
    "youtube": "youtube-shorts.md",
    "facebook": "facebook-reels.md",
}

# Unica ordem de canais que, com as janelas fixas (12:00 / 18:30 / 20:00) e os
# deslocamentos +0/+2/+4, mantem >= 48h entre publicacoes da mesma campanha:
# youtube 12:00 D -> instagram 18:30 D+2 = 54,5h -> facebook 20:00 D+4 = 49,5h.
ONDA1_CHANNEL_ORDER = ("youtube", "instagram", "facebook")
ONDA1_DAY_OFFSETS = (0, 2, 4)
FORMATO_VIDEO_ONDA1 = "9:16"
ONDA2_FORMATS = {
    "instagram": ("1:1", "repurpose-1x1"),
    "youtube": ("16:9", "repurpose-16x9"),
}

STATUS_EDITORIAL = "aguardando_aprovacao_titular"
AUTO_PUBLISH = False

CSV_COLUMNS = (
    "slot_id",
    "onda",
    "semana",
    "data_sugerida",
    "dia_semana",
    "janela_brt",
    "tenant_id",
    "brand_name",
    "slug",
    "preset",
    "audio_policy",
    "canal",
    "formato_video",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_url",
    "status_editorial",
    "auto_publish",
)

# Aberturas alternativas de clareza operacional por nicho/campanha, auditadas
# contra os guardrails do respectivo tenant antes de qualquer gravacao.
HOOK_VARIANTE_B = {
    "camp-saas-demo-estudio-flow-001": (
        "Veja o passo a passo para reservar uma aula experimental e conferir "
        "a grade de turmas do estúdio."
    ),
    "camp-saas-demo-estudio-flow-002": (
        "Veja a grade de turmas por horário e acompanhe as matrículas "
        "confirmadas em uma tela só."
    ),
    "camp-saas-demo-marca-salao-001": (
        "Acompanhe o caminho do horário escolhido pela cliente até a agenda "
        "do salão, passo a passo."
    ),
    "camp-saas-demo-ns001-agenda-001": (
        "Visualize os agendamentos do salão por profissional e por status, "
        "em uma tela só."
    ),
    "camp-saas-demo-meu-salao-001": (
        "Mostre o link de agendamento para a cliente e veja o horário "
        "reservado chegar na agenda da equipe."
    ),
    "camp-saas-demo-meu-salao-002": (
        "A equipe acompanha os atendimentos do dia em uma lista só, com o "
        "status de cada cliente."
    ),
    "camp-shorts-completo-multitrack-001": (
        "Encontre multitracks por tom e BPM, veja os stems separados e "
        "escolha o rateio certo para o seu projeto."
    ),
    "camp-shorts-rateios-002": (
        "Compare os rateios por faixas, cotas e vagas antes de escolher o seu."
    ),
    "camp-shorts-stems-workflow-003": (
        "Trabalhe com os stems Click, Guide e banda separados por "
        "instrumento, na ordem certa do seu workflow."
    ),
    "camp-saas-demo-clinica-vital-001": (
        "Acompanhe o caminho da avaliação marcada pela paciente até a agenda "
        "da recepção, passo a passo."
    ),
    "camp-saas-demo-clinica-vital-002": (
        "Veja a agenda de consultas do dia organizada por especialista e por "
        "status, em uma tela só."
    ),
    "camp-clinica-vital-002": (
        "Acompanhe o retorno de pacientes na agenda da clínica e veja o status "
        "atualizado pela recepção."
    ),
    "camp-multitrack-hub-002": (
        "Organize sessões por projeto, confira os stems separados e acompanhe "
        "cada entrega técnica."
    ),
    "camp-meu-salao-002": (
        "Compare a vitrine pública de horários com a rotina interna da equipe "
        "na agenda do salão."
    ),
}


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


def _audio_policy_label(audio_policy: dict) -> str:
    if audio_policy.get("allowAudioTrack"):
        return "com_faixa_de_audio"
    return "-an"


def _caption_opening(path: str) -> str:
    """Extrai a primeira linha nao vazia da legenda do canal (abertura original)."""
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                return stripped
    raise CampaignCalendarError(f"LEGENDA_VAZIA: {path}")


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
            openings: dict[str, str] = {}
            for canal, filename in CHANNEL_CAPTION_FILE.items():
                md_path = os.path.join(pkg_tenant_dir, slug, filename)
                if not os.path.isfile(render_local.fs_path(md_path)):
                    raise CampaignCalendarError(
                        f"PACOTE_MD_AUSENTE: {tenant_id}/{slug}/{filename}"
                    )
                openings[canal] = _caption_opening(md_path)
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
                    "captionOpenings": openings,
                }
            )

    if not campaigns:
        raise CampaignCalendarError(
            "NENHUMA_CAMPANHA: nenhum checklist-publicacao.json encontrado"
        )
    return campaigns


def _publishable_dates(start: datetime.date, count: int) -> list[datetime.date]:
    """Dias de publicacao (segunda a sabado) a partir da data inicial."""
    days: list[datetime.date] = []
    current = start
    while len(days) < count:
        if current.weekday() in PUBLISHABLE_WEEKDAYS:
            days.append(current)
        current += datetime.timedelta(days=1)
    return days


def _plan_onda1(campaigns: list[dict], o1_weeks: int) -> list[tuple[dict, int]]:
    """Distribui as campanhas da Onda 1 em pistas de dias uteis.

    Cada campanha ocupa a pista no dia util de ancora e repete nos
    deslocamentos +2 e +4 (sempre dias uteis). Pistas vizinhas (ancoras
    consecutivas) cobrem dias alternados, entao campanhas de tenants
    distintos dividem o dia sem colisao de tenant. A selecao e gulosa:
    tenants com mais campanhas escolhem primeiro e cada campanha ocupa a
    pista com mais capacidade livre que ainda nao tenha o seu tenant.
    """
    lane_anchors = [6 * (k // 2) + (k % 2) for k in range(2 * o1_weeks)]
    if len(campaigns) > CAMPAIGNS_PER_LANE * len(lane_anchors):
        raise CampaignCalendarError(
            f"CAPACIDADE_INSUFICIENTE_ONDA1: {len(campaigns)} campanhas para "
            f"{len(lane_anchors)} pistas de {CAMPAIGNS_PER_LANE} campanhas"
        )
    queues: dict[str, list[dict]] = {}
    for campaign in sorted(campaigns, key=lambda c: c["slug"]):
        queues.setdefault(campaign["tenantId"], []).append(campaign)
    order = sorted(
        campaigns,
        key=lambda c: (-len(queues[c["tenantId"]]), c["tenantId"], c["slug"]),
    )
    lanes: list[list[dict]] = [[] for _ in lane_anchors]
    for campaign in order:
        candidates = [
            k
            for k, lane in enumerate(lanes)
            if len(lane) < CAMPAIGNS_PER_LANE
            and all(other["tenantId"] != campaign["tenantId"] for other in lane)
        ]
        if not candidates:
            raise CampaignCalendarError(
                f"CAPACIDADE_INSUFICIENTE_ONDA1: sem pista livre para "
                f"{campaign['tenantId']}/{campaign['slug']} sem colisao de tenant"
            )
        chosen = min(
            candidates,
            key=lambda k: (-(CAMPAIGNS_PER_LANE - len(lanes[k])), k),
        )
        lanes[chosen].append(campaign)
    assignments: list[tuple[dict, int]] = []
    for k, lane in enumerate(lanes):
        for campaign in sorted(lane, key=lambda c: c["slug"]):
            assignments.append((campaign, lane_anchors[k]))
    return assignments


def _slot_checklist(campaign: dict, canal: str, onda: int, formato_video: str) -> list[str]:
    slug = campaign["slug"]
    items = [
        "Aprovação expressa do titular antes de publicar (status editorial: "
        "aguardando_aprovacao_titular).",
        "Publicação manual: nenhuma ferramenta publica ou agenda sozinha "
        "(autoPublish: false).",
        "Conferir os hashes SHA-256 no checklist-publicacao.json do pacote "
        "antes de anexar a mídia.",
        "Usar a legenda do canal no pacote ("
        + CHANNEL_CAPTION_FILE[canal]
        + "), incluindo a URL UTM exatamente como gerada.",
    ]
    if onda == 1:
        items.append("Anexar o vídeo 9:16 da entrega (conferir o hash no manifesto).")
    else:
        derivative = f"{slug}-1x1.mp4" if formato_video == "1:1" else f"{slug}-16x9.mp4"
        items.append(
            f"Anexar o derivado {formato_video} {derivative} da entrega "
            "(ver derivatives.json)."
        )
    if campaign["audioPolicy"].get("allowAudioTrack"):
        items.append("Vídeo já sai com a faixa de áudio permitida pelo guardrail do tenant.")
    else:
        items.append(
            f"Locução externa opcional: gravar fora do editor a partir de "
            f"{slug}_narracao.txt; não é requisito para publicar o vídeo legendado."
        )
    items.append(
        "Enquanto a ferramenta de analytics estiver PENDENTE "
        "(docs/rastreio-utm.md, seção 5), não declarar o link UTM como ativo "
        "em registros de campanha."
    )
    return items


def _build_slot(
    campaign: dict,
    onda: int,
    day_index: int,
    dates: list[datetime.date],
    canal: str,
    medium: str,
    formato_video: str,
    utm_content: str,
    violations: list[str],
) -> dict:
    date = dates[day_index]
    utm_params = {
        "utm_source": canal,
        "utm_medium": medium,
        "utm_campaign": campaign["slug"],
        "utm_content": utm_content,
    }
    utm_url = _utm_url(campaign["domain"], canal, medium, campaign["slug"], utm_content)
    hook_a = campaign["captionOpenings"][canal]
    if campaign["slug"] not in HOOK_VARIANTE_B:
        raise CampaignCalendarError(
            f"HOOK_VARIANTE_B_AUSENTE: {campaign['tenantId']}/{campaign['slug']}"
        )
    hook_b = HOOK_VARIANTE_B[campaign["slug"]]
    checklist = _slot_checklist(campaign, canal, onda, formato_video)
    audit_text = "\n".join([hook_a, hook_b, _audio_note(campaign["audioPolicy"]), utm_url, *checklist])
    found = tenant_validator.validate_text_against_guardrails(
        audit_text, campaign["guardrails"], check_ui_elements=True
    )
    for violation in found:
        violations.append(f"{campaign['tenantId']}/{campaign['slug']}/{canal}: {violation}")
    return {
        "slotId": None,
        "onda": onda,
        "semana": day_index // PUBLISHABLE_DAYS_PER_WEEK + 1,
        "dataSugerida": date.isoformat(),
        "diaSemana": WEEKDAY_NAMES[date.weekday()],
        "janelaHorarioBrt": CHANNEL_WINDOWS[canal],
        "tenantId": campaign["tenantId"],
        "brandName": campaign["brandName"],
        "slug": campaign["slug"],
        "preset": campaign["preset"],
        "audioPolicy": campaign["audioPolicy"],
        "canal": canal,
        "formatoVideo": formato_video,
        "hookVarianteA": hook_a,
        "hookVarianteB": hook_b,
        "utmParams": utm_params,
        "utmUrl": utm_url,
        "checklistPrePublicacao": checklist,
        "statusEditorial": STATUS_EDITORIAL,
        "autoPublish": AUTO_PUBLISH,
    }


def _build_metrics(campaigns: list[dict], slots: list[dict]) -> dict:
    by_tenant: dict[str, dict] = {}
    for campaign in campaigns:
        entry = by_tenant.setdefault(
            campaign["tenantId"],
            {"campaigns": 0, "slots": 0, "onda1": 0, "onda2": 0, "byChannel": {}},
        )
        entry["campaigns"] += 1
    for slot in slots:
        entry = by_tenant[slot["tenantId"]]
        entry["slots"] += 1
        entry[f"onda{slot['onda']}"] += 1
        entry["byChannel"][slot["canal"]] = entry["byChannel"].get(slot["canal"], 0) + 1

    by_channel = {
        canal: {"onda1": 0, "onda2": 0, "total": 0} for canal in CHANNEL_WINDOWS
    }
    by_onda = {1: 0, 2: 0}
    by_formato: dict[str, int] = {}
    for slot in slots:
        by_channel[slot["canal"]][f"onda{slot['onda']}"] += 1
        by_channel[slot["canal"]]["total"] += 1
        by_onda[slot["onda"]] += 1
        by_formato[slot["formatoVideo"]] = by_formato.get(slot["formatoVideo"], 0) + 1

    return {
        "byTenant": by_tenant,
        "byChannel": by_channel,
        "byOnda": by_onda,
        "byFormatoVideo": by_formato,
    }


# ---------------------------------------------------------------------------
# Planejador de capacidade editorial (Etapa 14) - simulacao sem mutacao
# ---------------------------------------------------------------------------

def simulate_calendar_capacity(
    root: str = ".",
    extra_campaigns: int = 0,
    extra_tenants: int = 0,
    start_date: str | None = None,
) -> dict:
    """Simula o impacto de novos tenants/campanhas no calendario sem gravar nada.

    Operacao 100% read-only: nunca escreve `04-legendas/`. Descobre o estado
    atual via `discover_campaigns` e compara com o cenario simulado
    (`current_campaigns + extra_campaigns`).

    Deve ser chamada com dados reais do checkout (os tenants existentes com
    pacotes de publicacao validos). Para 14 campanhas o minimo e 7 semanas
    (headroom = 2 ate 16); com +3 campanhas (17 total) sobe para 8 semanas.
    """
    root_real = os.path.realpath(root)
    campaigns = discover_campaigns(root_real)
    current_total = len(campaigns)
    current_tenants = len({c["tenantId"] for c in campaigns})

    o1_weeks_current = max(1, -(-current_total // 4))
    o2_weeks_current = max(1, -(-current_total // 6))
    min_weeks_current = o1_weeks_current + o2_weeks_current

    simulated_total = current_total + extra_campaigns
    simulated_tenants = current_tenants + extra_tenants

    o1_weeks_sim = max(1, -(-simulated_total // 4))
    o2_weeks_sim = max(1, -(-simulated_total // 6))
    min_weeks_sim = o1_weeks_sim + o2_weeks_sim

    week_delta = min_weeks_sim - min_weeks_current

    slots_per_week_avg = round(simulated_total * 4 / max(min_weeks_sim, 1), 2)
    total_slots_estimate = simulated_total * 4

    headroom_current = max(0, 16 - current_total)

    thresholds = [
        {"campanhas": 16, "semanasMinimas": 7, "nota": "ate 16 campanhas = 7 semanas"},
        {"campanhas": 18, "semanasMinimas": 8, "nota": "17-18 campanhas = 8 semanas"},
        {"campanhas": 20, "semanasMinimas": 9, "nota": "19-20 campanhas = 9 semanas"},
    ]

    recommendations: list[str] = []
    if week_delta > 0:
        recommendations.append(
            f"Apos onboarding de {extra_campaigns} campanha(oes), o minimo de semanas "
            f"sube de {min_weeks_current} para {min_weeks_sim} (delta +{week_delta})."
        )
        recommendations.append(
            "Rode campaign_calendar.py com --weeks igual ao novo minimo para evitar "
            "SEMANAS_INSUFICIENTES."
        )
    else:
        recommendations.append(
            f"Cenario cabe no horizonte atual de {min_weeks_current} semanas "
            f"(headroom: {headroom_current} campanha(oes) ate o proximo degrau de 16)."
        )

    if extra_tenants > 0:
        recommendations.append(
            f"Novo(s) tenant(s): {extra_tenants}; confirme --tenant-id unico e "
            f"validate com tenant_validator --all antes de render."
        )

    return {
        "root": root_real,
        "startDate": start_date or "semana de referencia atual",
        "current": {
            "tenants": current_tenants,
            "campaigns": current_total,
            "onda1Weeks": o1_weeks_current,
            "onda2Weeks": o2_weeks_current,
            "minRequiredWeeks": min_weeks_current,
            "totalSlotsEstimate": total_slots_estimate,
            "slotsPerWeekAvg": slots_per_week_avg,
        },
        "simulated": {
            "tenants": simulated_tenants,
            "campaigns": simulated_total,
            "onda1Weeks": o1_weeks_sim,
            "onda2Weeks": o2_weeks_sim,
            "minRequiredWeeks": min_weeks_sim,
            "totalSlotsEstimate": round(simulated_total * 4 / max(min_weeks_sim, 1) * min_weeks_sim),
            "slotsPerWeekAvg": slots_per_week_avg,
            "weekDelta": week_delta,
        },
        "capacityThresholds": thresholds,
        "recommendations": recommendations,
    }


def load_utm_report(root_real: str, utm_report: str | None) -> dict | None:
    """Carrega um relatorio UTM (`utm-performance-report.json`) confinado a raiz.

    Devolve o indice de comparativos por tenant/campanha ou None quando nenhum
    caminho e informado. O relatorio precisa ser saida de
    `tools/utm_report_importer.py`, com `rankings.hookComparison`.
    """
    if not utm_report:
        return None
    report_path = os.path.realpath(os.path.join(root_real, utm_report))
    if not render_local.contained(root_real, report_path):
        raise CampaignCalendarError(
            f"UTM_REPORT_FORA_DA_RAIZ: {utm_report} (fora de {root_real})"
        )
    if not os.path.isfile(render_local.fs_path(report_path)):
        raise CampaignCalendarError(f"UTM_REPORT_AUSENTE: {utm_report}")
    try:
        with open(render_local.fs_path(report_path), "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        raise CampaignCalendarError(f"UTM_REPORT_INVALIDO: {utm_report}: {exc}") from exc

    rankings = data.get("rankings") if isinstance(data, dict) else None
    comparison = rankings.get(HOOK_COMPARISON_KEY) if isinstance(rankings, dict) else None
    if not isinstance(comparison, dict):
        raise CampaignCalendarError(
            f"UTM_REPORT_SEM_COMPARATIVO: {utm_report} nao possui rankings.{HOOK_COMPARISON_KEY}"
        )
    by_campaign = comparison.get("byCampaign")
    if not isinstance(by_campaign, list):
        raise CampaignCalendarError(
            f"UTM_REPORT_SEM_COMPARATIVO: {utm_report} sem rankings.{HOOK_COMPARISON_KEY}.byCampaign"
        )

    index: dict[tuple[str, str], dict] = {}
    for row in by_campaign:
        if not isinstance(row, dict):
            continue
        tenant = row.get("tenantId")
        campaign = row.get("campaign")
        classification = row.get("classification")
        if tenant is None or campaign is None:
            continue
        index[(str(tenant), str(campaign))] = {
            "classification": classification,
            "sessionsA": row.get("sessionsA"),
            "sessionsB": row.get("sessionsB"),
            "conversionRateA": row.get("conversionRateA"),
            "conversionRateB": row.get("conversionRateB"),
            "liftConversionPct": row.get("liftConversionPct"),
            "minSessions": comparison.get("minSessions"),
            "zScore": row.get("zScore"),
            "pValue": row.get("pValue"),
            "significant": row.get("significant"),
            "classificationReason": row.get("classificationReason"),
        }

    tenant_benchmarks: dict[str, dict] = {}
    benchmarks = rankings.get("tenantBenchmarks") if isinstance(rankings, dict) else None
    if isinstance(benchmarks, dict):
        for row in benchmarks.get("byTenant", []):
            if not isinstance(row, dict):
                continue
            tid = row.get("tenantId")
            if tid is None:
                continue
            tenant_benchmarks[str(tid)] = row

    return {
        "path": render_local.rel(root_real, report_path),
        "minSessions": comparison.get("minSessions"),
        "byCampaign": index,
        "byTenant": tenant_benchmarks,
    }


def _recommendation(comparison: dict | None) -> tuple[str, str]:
    """Traduz um comparativo A/B em (hookRecomendado, justificativa objetiva)."""
    if not comparison or comparison.get("classification") not in HOOK_CLASSIFICACOES:
        return (
            HOOK_SEM_DADOS,
            "Sem comparativo A/B consolidado para este tenant/campanha no relatorio UTM; "
            "manter teste A/B.",
        )

    classification = comparison["classification"]
    rate_a = comparison.get("conversionRateA")
    rate_b = comparison.get("conversionRateB")
    sessions_a = comparison.get("sessionsA")
    sessions_b = comparison.get("sessionsB")
    lift = comparison.get("liftConversionPct")
    min_sessions = comparison.get("minSessions")
    total = None
    if isinstance(sessions_a, (int, float)) and isinstance(sessions_b, (int, float)):
        total = sessions_a + sessions_b
    lift_text = "n/d" if lift is None else f"{lift}%"
    total_text = "n/d" if total is None else f"{total}"
    z = comparison.get("zScore")
    p_value = comparison.get("pValue")
    stats_text = "" if z is None or p_value is None else f", z={z}, p={p_value}"

    if classification == "vencedor_A":
        return (
            "A",
            f"Hook A venceu no relatorio UTM: CVR {rate_a}% vs {rate_b}% "
            f"(lift de B {lift_text}, {total_text} sessoes comparadas{stats_text}).",
        )
    if classification == "vencedor_B":
        return (
            "B",
            f"Hook B venceu no relatorio UTM: CVR {rate_b}% vs {rate_a}% "
            f"(lift de B {lift_text}, {total_text} sessoes comparadas{stats_text}).",
        )
    if classification == "empate_tecnico":
        return (
            HOOK_SEM_DADOS,
            f"Empate tecnico no relatorio UTM: CVR {rate_a}% vs {rate_b}% "
            f"(lift {lift_text}, {total_text} sessoes comparadas{stats_text}); "
            "sem significancia estatistica, manter o teste A/B.",
        )
    return (
        HOOK_SEM_DADOS,
        f"Amostra insuficiente no relatorio UTM: {total_text} sessoes comparadas "
        f"(minimo {min_sessions}); manter teste A/B.",
    )


def _apply_utm_recommendations(calendar: dict, utm_report: dict | None) -> dict:
    """Ancora `hookRecomendado` e justificativa nos slots do calendario."""
    benchmarks = utm_report.get("byTenant", {}) if utm_report else {}
    for slot in calendar["slots"]:
        comparison = None
        fatigue = None
        if utm_report is not None:
            key = (slot["tenantId"], slot["slug"])
            comparison = utm_report["byCampaign"].get(key)
            bench = benchmarks.get(slot["tenantId"])
            if bench and bench.get("hooksComFadigaStatus") == "fadiga_detectada":
                fatigue = bench
        recommended, justification = _recommendation(comparison)
        slot[HOOK_RECOMENDADO_FIELD] = recommended
        slot[HOOK_JUSTIFICATIVA_FIELD] = justification
        slot["fatigueStatus"] = (
            fatigue["hooksComFadigaStatus"] if fatigue else "sem_dados"
        )
        slot["fatigueZScore"] = fatigue["hooksComFadigaZScore"] if fatigue else None
        slot["fatiguePValue"] = fatigue["hooksComFadigaPValue"] if fatigue else None
        slot["fatigueDetected"] = bool(fatigue) if fatigue else False
        if fatigue:
            slot["fatigueReason"] = fatigue["hooksComFadigaReason"]
            justification = (
                f"{justification} ALERTA DE FADIGA: {fatigue['hooksComFadigaReason']}"
            )
            slot[HOOK_JUSTIFICATIVA_FIELD] = justification
    calendar["utmReport"] = (
        {
            "path": utm_report["path"],
            "minSessions": utm_report["minSessions"],
            "aplicado": True,
        }
        if utm_report is not None
        else None
    )
    return calendar


def load_bundle_attribution(root_real: str, bundle_attribution: str | None) -> dict | None:
    """Carrega o arquivo de atribuicao de bundle (Etapa 12).

    Confina o caminho a raiz e valida que o JSON possua a chave ``bundles``.
    Indexa os atribuicoes por (tenantId, slug) para consulta rapida.
    """
    if not bundle_attribution:
        return None
    report_path = os.path.realpath(os.path.join(root_real, bundle_attribution))
    if not render_local.contained(root_real, report_path):
        raise CampaignCalendarError(
            f"BUNDLE_ATTRIBUTION_FORA_DA_RAIZ: {bundle_attribution} (fora de {root_real})"
        )
    if not os.path.isfile(render_local.fs_path(report_path)):
        raise CampaignCalendarError(f"BUNDLE_ATTRIBUTION_AUSENTE: {bundle_attribution}")
    try:
        with open(render_local.fs_path(report_path), "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        raise CampaignCalendarError(f"BUNDLE_ATTRIBUTION_INVALIDO: {bundle_attribution}: {exc}") from exc

    bundles = data.get("bundles")
    if not isinstance(bundles, list):
        raise CampaignCalendarError(
            f"BUNDLE_ATTRIBUTION_SEM_LISTA: {bundle_attribution} sem 'bundles'"
        )

    index: dict[tuple[str, str], dict] = {}
    for entry in bundles:
        if not isinstance(entry, dict):
            continue
        tid = entry.get("tenantId")
        slug = entry.get("slug")
        if tid is None or slug is None:
            continue
        index[(str(tid), str(slug))] = entry

    return {
        "path": render_local.rel(root_real, report_path),
        "byKey": index,
    }


def _apply_bundle_attribution(calendar: dict, bundle_attribution: dict | None) -> dict:
    """Anexa `bundleAttribution` aos slots do calendario (Etapa 12).

    Para cada slot, cruza (tenantId, slug) com o índice de atribuicoes e
    anexa status de atribuicao, metricas entregues (impressoes, cliques, CTR,
    conversoes, conversionRate, observedUpliftPct, winnerSustained) e
    promotionHistory. Quando ha atribuicao, a justificativa do
    `hookRecomendadoJustificativa` incorpora a taxa de conversão pós-entrega
    e a sustentação do vencedor, sem mutar datas, canais, UTMs ou cópia.
    """
    if not bundle_attribution:
        return calendar
    index = bundle_attribution.get("byKey", {})
    for slot in calendar["slots"]:
        key = (slot["tenantId"], slot["slug"])
        attr = index.get(key)
        if not attr:
            continue
        slot["bundleAttribution"] = {
            "attributionStatus": attr.get("attributionStatus"),
            "approvalStatus": attr.get("approvalStatus"),
            "bundleSha256": attr.get("bundleSha256"),
            "bundlePath": attr.get("bundlePath"),
            "metrics": attr.get("metrics"),
            "promotionHistory": attr.get("promotionHistory", []),
            "attributionReason": attr.get("attributionReason"),
        }
        metrics = attr.get("metrics") or {}
        conversion_rate = metrics.get("conversionRate")
        uplift = metrics.get("observedUpliftPct")
        winner_sustained = metrics.get("winnerSustained")
        justification = slot.get(HOOK_JUSTIFICATIVA_FIELD, "")
        parts = [justification]
        if conversion_rate is not None:
            parts.append(f"CVR pós-entrega: {conversion_rate}%.")
        if uplift is not None:
            parts.append(f"Uplift observado: {uplift}%.")
        if winner_sustained is not None:
            parts.append(
                f"Vencedor sustentado: {'sim' if winner_sustained else 'não'}."
            )
        slot[HOOK_JUSTIFICATIVA_FIELD] = " ".join(parts)
    return calendar


def build_editorial_calendar(
    start_date: str,
    weeks: int = WEEKS_DEFAULT,
    root: str = ".",
    utm_report: str | None = None,
    bundle_attribution: str | None = None,
) -> dict:
    """Constrói o calendário editorial completo (sem gravar em disco).

    Quando `utm_report` é informado (caminho relativo a raiz de um
    `utm-performance-report.json`), cada slot recebe `hookRecomendado`
    (`A`, `B` ou `testar_ab`) e uma justificativa objetiva baseada no
    comparativo A/B. Sem `utm_report` a saída é deterministicamente
    `testar_ab` para todos os slots.

    Quando `bundle_attribution` é informado (caminho relativo a raiz de um
    `bundle-attribution.json` produzido pela reconciliação Etapa 12), os slots
    recebem `bundleAttribution` (status de atribuição, métricas entregues,
    observedUpliftPct e winnerSustained), e a justificativa do `hookRecomendado`
    incorpora a taxa de conversão pós-entrega e a sustentação do vencedor quando
    disponível.
    """
    root_real = os.path.realpath(root)
    try:
        start = datetime.date.fromisoformat(start_date)
    except ValueError as exc:
        raise CampaignCalendarError(
            f"DATA_INVALIDA: {start_date} (esperado YYYY-MM-DD)"
        ) from exc
    if weeks < 1:
        raise CampaignCalendarError(f"SEMANAS_INVALIDAS: {weeks}")

    campaigns = discover_campaigns(root_real)
    total = len(campaigns)
    o1_weeks = max(1, -(-total // 4))
    o2_weeks_needed = max(1, -(-total // 6))
    if weeks < o1_weeks + o2_weeks_needed:
        raise CampaignCalendarError(
            f"SEMANAS_INSUFICIENTES: {weeks} semanas para {total} campanhas "
            f"(mínimo {o1_weeks + o2_weeks_needed}: {o1_weeks} da Onda 1 + "
            f"{o2_weeks_needed} da Onda 2)"
        )

    dates = _publishable_dates(start, PUBLISHABLE_DAYS_PER_WEEK * weeks)
    assignments1 = _plan_onda1(campaigns, o1_weeks)
    o2_start = PUBLISHABLE_DAYS_PER_WEEK * o1_weeks
    o2_capacity = PUBLISHABLE_DAYS_PER_WEEK * (weeks - o1_weeks)
    ordered2 = sorted(campaigns, key=lambda c: c["slug"])
    if len(ordered2) > o2_capacity:
        raise CampaignCalendarError(
            f"CAPACIDADE_INSUFICIENTE_ONDA2: {len(ordered2)} campanhas para "
            f"{o2_capacity} dias úteis de reaproveitamento"
        )

    slots: list[dict] = []
    violations: list[str] = []
    for campaign, anchor in assignments1:
        for canal, offset in zip(ONDA1_CHANNEL_ORDER, ONDA1_DAY_OFFSETS):
            slots.append(
                _build_slot(
                    campaign,
                    onda=1,
                    day_index=anchor + offset,
                    dates=dates,
                    canal=canal,
                    medium=CHANNEL_UTM_MEDIUM_ONDA1[canal],
                    formato_video=FORMATO_VIDEO_ONDA1,
                    utm_content=campaign["tenantId"],
                    violations=violations,
                )
            )
    for i, campaign in enumerate(ordered2):
        canal = "instagram" if i % 2 == 0 else "youtube"
        formato_video, utm_content = ONDA2_FORMATS[canal]
        slots.append(
            _build_slot(
                campaign,
                onda=2,
                day_index=o2_start + i,
                dates=dates,
                canal=canal,
                medium=CHANNEL_UTM_MEDIUM_ONDA2[canal],
                formato_video=formato_video,
                utm_content=utm_content,
                violations=violations,
            )
        )

    if violations:
        raise CampaignCalendarError("GUARDRAIL_VIOLACAO: " + "; ".join(violations))

    slots.sort(
        key=lambda s: (
            s["dataSugerida"],
            s["janelaHorarioBrt"].split("-")[0],
            s["tenantId"],
            s["slug"],
            s["canal"],
        )
    )
    for index, slot in enumerate(slots, start=1):
        slot["slotId"] = f"slot-{index:03d}"

    tenants_used = sorted({campaign["tenantId"] for campaign in campaigns})
    calendar = {
        "schemaVersion": 2,
        "generatedBy": "tools/campaign_calendar.py",
        "startDate": start.isoformat(),
        "endDate": max(slot["dataSugerida"] for slot in slots),
        "weeks": weeks,
        "onda1Weeks": o1_weeks,
        "campaignsPerDay": CAMPAIGNS_PER_LANE,
        "channels": list(CHANNEL_WINDOWS),
        "tenants": tenants_used,
        "totalTenants": len(tenants_used),
        "totalCampaigns": total,
        "totalSlots": len(slots),
        "statusEditorial": STATUS_EDITORIAL,
        "autoPublish": AUTO_PUBLISH,
        "rules": {
            "publishableDays": [WEEKDAY_NAMES[d] for d in sorted(PUBLISHABLE_WEEKDAYS)],
            "campaignsPerDayOnda1": CAMPAIGNS_PER_LANE,
            "sameTenantSameDay": "proibido",
            "minSpacingHoursBetweenChannels": CHANNEL_SPACING_HOURS,
            "onda1ChannelOrder": list(ONDA1_CHANNEL_ORDER),
            "onda1DayOffsets": list(ONDA1_DAY_OFFSETS),
            "windowsBrt": dict(CHANNEL_WINDOWS),
            "onda2SlotsPerDay": 1,
            "onda2Alternation": {
                "instagram": "Feed 1:1 (utm_content=repurpose-1x1)",
                "youtube": "Vídeo 16:9 (utm_content=repurpose-16x9)",
            },
        },
        "guardrailsAudited": True,
        "guardrailViolations": [],
        "metrics": _build_metrics(campaigns, slots),
        "slots": slots,
    }

    utm_report_data = load_utm_report(root_real, utm_report)
    bundle_attribution_data = load_bundle_attribution(root_real, bundle_attribution)
    calendar = _apply_utm_recommendations(calendar, utm_report_data)
    calendar = _apply_bundle_attribution(calendar, bundle_attribution_data)
    calendar["bundleAttribution"] = (
        {
            "path": bundle_attribution_data["path"],
            "aplicado": bool(bundle_attribution_data),
        }
        if bundle_attribution_data
        else None
    )
    return calendar


def _channel_label(slot: dict) -> str:
    if slot["onda"] == 1:
        return CHANNEL_LABELS_ONDA1[slot["canal"]]
    return CHANNEL_LABELS_ONDA2[slot["canal"]]


def _render_md(calendar: dict) -> str:
    slots = calendar["slots"]
    metrics = calendar["metrics"]

    brand_by_tenant: dict[str, str] = {}
    audio_by_tenant: dict[str, bool] = {}
    for slot in slots:
        brand_by_tenant.setdefault(slot["tenantId"], slot["brandName"])
        audio_by_tenant.setdefault(
            slot["tenantId"], slot["audioPolicy"].get("allowAudioTrack", False)
        )
    an_tenants = sorted(t for t, allow in audio_by_tenant.items() if not allow)
    audio_tenants = sorted(t for t, allow in audio_by_tenant.items() if allow)

    lines: list[str] = []
    lines.append(
        f"# Calendário Editorial — Content Factory Multi-Tenant ({calendar['weeks']} semanas)"
    )
    lines.append("")
    lines.append(
        f"> Gerado por `tools/campaign_calendar.py --start-date {calendar['startDate']} "
        f"--weeks {calendar['weeks']}`."
    )
    lines.append(
        f"> Período: **{calendar['startDate']}** a **{calendar['endDate']}** — "
        f"{calendar['totalCampaigns']} campanhas de {calendar['totalTenants']} tenants, "
        f"{calendar['totalSlots']} slots: {metrics['byOnda'][1]} da Onda 1 "
        f"(lançamentos 9:16, semanas 1-{calendar['onda1Weeks']}) + "
        f"{metrics['byOnda'][2]} da Onda 2 (reaproveitamento 1:1/16:9, semanas "
        f"{calendar['onda1Weeks'] + 1}-{calendar['weeks']})."
    )
    lines.append("> Publicação 100% manual: `autoPublish: false` em todos os slots.")
    lines.append(
        "> Status editorial: `aguardando_aprovacao_titular` — nenhuma publicação sem "
        "aprovação expressa do titular."
    )
    if calendar.get("utmReport"):
        lines.append(
            f"> Hook recomendado ancorado no relatorio UTM `{calendar['utmReport']['path']}` "
            f"(limiar de {calendar['utmReport']['minSessions']} sessoes)."
        )
    lines.append("")

    lines.append("## 1. Resumo executivo")
    lines.append("")
    lines.append("### 1.1 Por tenant")
    lines.append("")
    lines.append(
        "| Tenant | Marca | Campanhas | Slots Onda 1 | Slots Onda 2 | Total | Áudio |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for tenant_id in calendar["tenants"]:
        entry = metrics["byTenant"][tenant_id]
        audio = (
            "com faixa de áudio"
            if audio_by_tenant.get(tenant_id)
            else "`-an` (locução externa)"
        )
        lines.append(
            f"| `{tenant_id}` | {brand_by_tenant[tenant_id]} | {entry['campaigns']} "
            f"| {entry['onda1']} | {entry['onda2']} | {entry['slots']} | {audio} |"
        )
    lines.append("")

    lines.append("### 1.2 Por canal")
    lines.append("")
    lines.append("| Canal | Janela (BRT) | Onda 1 | Onda 2 | Total |")
    lines.append("|---|---|---|---|---|")
    canal_display = {
        "instagram": "Instagram (Reels + Feed 1:1)",
        "youtube": "YouTube (Shorts + Vídeo 16:9)",
        "facebook": "Facebook (Reels)",
    }
    for canal in calendar["channels"]:
        entry = metrics["byChannel"][canal]
        lines.append(
            f"| {canal_display[canal]} | {CHANNEL_WINDOWS[canal]} "
            f"| {entry['onda1']} | {entry['onda2']} | {entry['total']} |"
        )
    lines.append("")

    lines.append(f"## 2. Cronograma completo ({calendar['weeks']} semanas)")
    lines.append("")
    for week in range(1, calendar["weeks"] + 1):
        week_slots = [slot for slot in slots if slot["semana"] == week]
        if not week_slots:
            continue
        week_start = week_slots[0]["dataSugerida"]
        week_end = week_slots[-1]["dataSugerida"]
        lines.append(f"### Semana {week} ({week_start} a {week_end})")
        lines.append("")
        lines.append(
            "| Slot | Data | Dia | Janela (BRT) | Tenant | Campanha | Canal "
            "| Formato | Áudio | Hook A | Hook B |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for slot in week_slots:
            audio = (
                "com áudio"
                if slot["audioPolicy"].get("allowAudioTrack", False)
                else "`-an`"
            )
            lines.append(
                f"| {slot['slotId']} | {slot['dataSugerida']} | {slot['diaSemana']} "
                f"| {slot['janelaHorarioBrt']} | `{slot['tenantId']}` "
                f"| `{slot['slug']}` | {_channel_label(slot)} | {slot['formatoVideo']} "
                f"| {audio} | {slot['hookVarianteA']} | {slot['hookVarianteB']} |"
            )
        lines.append("")

    lines.append("## 3. Checklist de operação manual pré-publicação")
    lines.append("")
    lines.append(
        "1. **Aprovação do titular:** o slot só entra em produção após aprovação "
        "expressa; o status editorial é `aguardando_aprovacao_titular`."
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
        "9. **Onda 2 (derivados):** anexar `<slug>-1x1.mp4` (Instagram Feed 1:1) ou "
        "`<slug>-16x9.mp4` (YouTube Vídeo 16:9) conforme o slot; conferir o "
        "`derivatives.json` da entrega."
    )
    lines.append(
        "10. **UTM:** não alterar os parâmetros UTM de posts já publicados; qualquer "
        "mudança invalida o histórico de dados."
    )
    lines.append(
        "11. **Analytics:** confirmar a ferramenta de analytics ativa "
        "(`docs/rastreio-utm.md`, seção 5) antes de declarar qualquer link UTM como "
        "ativo em registros de campanha."
    )
    lines.append("")

    lines.append("## 4. Referência rápida de URLs UTM (por campanha)")
    lines.append("")
    lines.append("| Tenant | Campanha | Onda | Canal | Formato | URL rastreada |")
    lines.append("|---|---|---|---|---|---|")
    matrix_slots = sorted(
        slots, key=lambda s: (s["tenantId"], s["slug"], s["onda"], s["canal"])
    )
    for slot in matrix_slots:
        lines.append(
            f"| `{slot['tenantId']}` | `{slot['slug']}` | {slot['onda']} "
            f"| {_channel_label(slot)} | {slot['formatoVideo']} | {slot['utmUrl']} |"
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


def _render_csv(calendar: dict) -> str:
    """Renderiza a matriz UTM consolidada (CSV UTF-8/LF, 20 colunas)."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for slot in calendar["slots"]:
        params = slot["utmParams"]
        writer.writerow(
            [
                slot["slotId"],
                slot["onda"],
                slot["semana"],
                slot["dataSugerida"],
                slot["diaSemana"],
                slot["janelaHorarioBrt"],
                slot["tenantId"],
                slot["brandName"],
                slot["slug"],
                slot["preset"] or "",
                _audio_policy_label(slot["audioPolicy"]),
                slot["canal"],
                slot["formatoVideo"],
                params["utm_source"],
                params["utm_medium"],
                params["utm_campaign"],
                params["utm_content"],
                slot["utmUrl"],
                slot["statusEditorial"],
                json.dumps(slot["autoPublish"]),
            ]
        )
    return buffer.getvalue()


def write_calendar(calendar: dict, root: str = ".") -> dict:
    """Grava o calendário editorial em JSON, Markdown e CSV (UTF-8, LF)."""
    root_real = os.path.realpath(root)
    targets = (
        (
            "json",
            CALENDAR_JSON_REL,
            json.dumps(calendar, ensure_ascii=False, indent=2) + "\n",
        ),
        ("md", CALENDAR_MD_REL, _render_md(calendar)),
        ("csv", UTM_CSV_REL, _render_csv(calendar)),
    )
    outputs: dict[str, dict] = {}
    for kind, rel_path, content in targets:
        abs_path = os.path.realpath(os.path.join(root_real, rel_path))
        if not render_local.contained(root_real, abs_path):
            raise CampaignCalendarError(f"SAIDA_FORA_DA_RAIZ: {rel_path}")
        os.makedirs(render_local.fs_path(os.path.dirname(abs_path)), exist_ok=True)
        render_local.write_text_lf(abs_path, content)
        outputs[kind] = {
            "path": render_local.rel(root_real, abs_path),
            "sha256": _sha256_file(abs_path),
            "bytes": os.path.getsize(render_local.fs_path(abs_path)),
        }
    return outputs


def generate_calendar(
    start_date: str,
    weeks: int = WEEKS_DEFAULT,
    root: str = ".",
    utm_report: str | None = None,
) -> dict:
    """Constrói, audita e grava o calendário editorial. Devolve o resumo."""
    calendar = build_editorial_calendar(
        start_date, weeks=weeks, root=root, utm_report=utm_report
    )
    outputs = write_calendar(calendar, root=root)
    return {
        "ok": True,
        "startDate": calendar["startDate"],
        "endDate": calendar["endDate"],
        "weeks": calendar["weeks"],
        "onda1Weeks": calendar["onda1Weeks"],
        "totalTenants": calendar["totalTenants"],
        "totalCampaigns": calendar["totalCampaigns"],
        "totalSlots": calendar["totalSlots"],
        "guardrailsAudited": calendar["guardrailsAudited"],
        "guardrailViolations": calendar["guardrailViolations"],
        "utmReport": calendar["utmReport"],
        "outputs": outputs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gerador de calendario editorial 4 semanas e matriz UTM multi-tenant"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--start-date", help="Data inicial do cronograma (YYYY-MM-DD)"
    )
    mode.add_argument(
        "--simulate-capacity", action="store_true",
        help="Simula impacto de novos tenants/campanhas (read-only, nao grava)"
    )
    parser.add_argument(
        "--weeks", type=int, default=WEEKS_DEFAULT, help="Semanas do cronograma (padrao 4)"
    )
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument(
        "--extra-campaigns", type=int, default=0,
        help="Campanhas extras para simulacao de capacidade"
    )
    parser.add_argument(
        "--extra-tenants", type=int, default=0,
        help="Tenants extras para simulacao de capacidade"
    )
    parser.add_argument(
        "--utm-report",
        default=None,
        help="Caminho (relativo a raiz) de um utm-performance-report.json com hookComparison",
    )
    parser.add_argument("--json", action="store_true", help="Emite JSON no stdout")
    args = parser.parse_args(argv)

    if args.simulate_capacity:
        try:
            if args.start_date:
                start_date = args.start_date
            else:
                start_date = datetime.date.today().isoformat()
            datetime.date.fromisoformat(start_date)
        except ValueError:
            print(
                f"Erro: --start-date invalida: {start_date} (esperado YYYY-MM-DD)",
                file=sys.stderr,
            )
            return 2
        try:
            result = simulate_calendar_capacity(
                root=args.root,
                extra_campaigns=args.extra_campaigns,
                extra_tenants=args.extra_tenants,
                start_date=start_date,
            )
        except CampaignCalendarError as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1
        except (OSError, ValueError, KeyError) as exc:
            print(f"Erro: entrada invalida ({type(exc).__name__}: {exc})", file=sys.stderr)
            return 2

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            current = result["current"]
            simulated = result["simulated"]
            print(
                f"Capacidade simulada: {current['campaigns']} -> {simulated['campaigns']} campanhas, "
                f"{current['minRequiredWeeks']} -> {simulated['minRequiredWeeks']} semanas "
                f"(delta {simulated['weekDelta']:+d})"
            )
            for rec in result["recommendations"]:
                print(f"  - {rec}")
        return 0

    try:
        datetime.date.fromisoformat(args.start_date)
    except ValueError:
        print(
            f"Erro: --start-date invalida: {args.start_date} (esperado YYYY-MM-DD)",
            file=sys.stderr,
        )
        return 2

    try:
        result = generate_calendar(
            args.start_date, weeks=args.weeks, root=args.root, utm_report=args.utm_report
        )
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
            f"de {result['startDate']} a {result['endDate']} "
            f"({result['weeks']} semanas)"
        )
        for kind in ("json", "md", "csv"):
            entry = result["outputs"][kind]
            print(f"  - {entry['path']} ({entry['bytes']} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
