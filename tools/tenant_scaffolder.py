"""Scaffolder automatico de novos tenants e campanha inicial (Etapa 14).

Implementa o onboarding automatizado da fabrica multi-tenant: a partir de
um ``--tenant-id`` novo, gera os contratos do tenant (brand-kit.json,
guardrails.json, fixture editorial) e, quando solicitado via
``--with-campaign``, o contrato da campanha inicial. SRT, narracao e copias
sociais sao derivados **somente em memoria** para a pre-validacao de
guardrails (``editorialQaPreview``); nada disso e' gravado em disco.

Comportamento fail-closed (rodada P1 de 22/11/2026): com ``apply=True``, os
arquivos sao gravados e em seguida validados (``tenant_validator`` strict +
pre-validacao de guardrails); qualquer falha executa rollback completo do que
foi gravado (sem tocar tenants preexistentes) e levanta
``ScaffolderError("SCAFFOLD_VALIDACAO_FALHOU")`` -> CLI exit 1 e ``ok: False``.
Com ``apply=False`` (dry-run), a mesma validacao e' executada em staging
descartavel sob ``<RAIZ>/.workspace/tmp/tenant-scaffolder-preview/`` e o
resultado e' reportado em ``validation`` antes de qualquer escrita.

Regras de engenharia respeitadas:

  * 100% biblioteca padrao Python (stdlib), sem dependencias externas.
  * Seguranca por padrao: ``--dry-run`` e ``--apply`` mutuamente exclusivos e
    um dos dois obrigatorio na CLI; API publica ``scaffold_tenant(..., apply=False)``.
  * Nenhuma publicacao: ``autoPublish: false`` em checklist e slots.
  * Politica de audio coerente com o tenant (``an``/``aac``) propagada para o
    manifesto, SRT, narracao e pacote social.
  * Confinamento de caminhos via ``render_local.contained``/``rel``/
    ``fs_path``/``write_text_lf``; ``tenant_id`` e slug validados com regex
    kebab-case estrito.
  * Zero mutacao em disco sem ``--apply`` explicito; rollback em falha.

Uso (a partir da raiz do checkout):
    python tools/tenant_scaffolder.py --tenant-id novo-tenant \\
        --brand-name "Novo Tenant" --domain novotenant.com.br \\
        --tagline "AGENDA SIMPLIFICADO" --audio-policy an \\
        --dry-run --json

    python tools/tenant_scaffolder.py --tenant-id novo-tenant \\
        --brand-name "Novo Tenant" --domain novotenant.com.br \\
        --with-campaign camp-novo-tenant-001 \\
        --campaign-title "COMO O FLUXO CONECTADO" \\
        --apply --json
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import os
import re
import shutil
import sys
import tempfile
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import editorial_qa  # noqa: E402
import render_local  # noqa: E402
import tenant_validator  # noqa: E402

TENANT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TENANT_ID_MAX_LEN = 40
SLUG_MAX_LEN = 80
DEFAULT_PRESETS = ("saas-demo", "shorts-completo")

SRT_MAX_LINE_CHARS = 48
SRT_SCENE_SECONDS = (4.0, 6.0, 7.0, 3.0, 6.0, 4.0)
SRT_SCENE_COUNT = 6
CAMPAIGN_DURATION = 30.0
CAMPAIGN_PREFIX_DEFAULT = "camp"
AUDIO_POLICIES = {
    "an": {
        "allowAudioTrack": False,
        "requireSrt": True,
        "requireExternalNarration": True,
        "ffmpegFlag": "-an",
    },
    "aac": {
        "allowAudioTrack": True,
        "requireSrt": True,
        "requireExternalNarration": False,
        "ffmpegFlag": "-c:a aac",
    },
}
SOCIAL_FILES = ("instagram-reels.md", "youtube-shorts.md", "facebook-reels.md")
CHECKLIST_FILE = "checklist-publicacao.json"


class ScaffolderError(Exception):
    """Falha controlada do scaffolder (codigo estavel no erro)."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _fs(path: str) -> str:
    return render_local.fs_path(path)


def _contained(root_real: str, target: str) -> bool:
    return render_local.contained(root_real, target)


def _write_json(path: str, data: dict) -> None:
    render_local.write_text_lf(_fs(path), json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _write_text(path: str, text: str) -> None:
    render_local.write_text_lf(_fs(path), text)


def _slugify(value: str, max_len: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    if len(slug) > max_len:
        slug = slug[:max_len]
    return slug.strip("-")


def _validate_tenant_id(tenant_id: str) -> str:
    if not isinstance(tenant_id, str) or not TENANT_ID_RE.match(tenant_id) or len(tenant_id) > TENANT_ID_MAX_LEN:
        raise ScaffolderError("ID_INVALIDO", f"tenant_id invalido: '{tenant_id}'")
    return tenant_id


def _validate_slug(slug: str) -> str:
    if not isinstance(slug, str) or not SLUG_RE.match(slug) or len(slug) > SLUG_MAX_LEN:
        raise ScaffolderError("ID_INVALIDO", f"slug invalido: '{slug}'")
    return slug


def _default_tagline(brand_name: str) -> str:
    return "AGENDA SIMPLIFICADO PARA SUA MARCA"


def _default_palette() -> dict:
    return {
        "primary": "#0EA5E9",
        "secondary": "#8B5CF6",
        "accent": "#22C55E",
        "background": "#090D16",
        "surface": "#161F30",
        "textPrimary": "#F1F5F9",
        "textMuted": "#94A3B8",
        "rgb": {
            "backgroundTop": [9, 13, 22],
            "backgroundBottom": [15, 23, 42],
            "headerBg": [6, 9, 17],
            "cardBg": [22, 31, 48],
            "cardHighlight": [30, 42, 66],
            "primaryAccent": [6, 182, 212],
            "secondaryAccent": [139, 92, 246],
            "statusConfirmed": [34, 197, 94],
            "statusWaiting": [234, 179, 8],
            "statusDone": [148, 163, 184],
            "textPrimary": [241, 245, 249],
            "textMuted": [148, 163, 184],
        },
    }


def _build_brand_kit(
    tenant_id: str,
    brand_name: str,
    domain: str,
    tagline: str,
    audio_policy: dict,
    palette: dict,
    monogram: str,
) -> dict:
    display_title = " ".join(
        part.upper() for part in re.split(r"[\s_-]+", brand_name.strip()) if part
    )
    slug_hint = _slugify(brand_name, 12)
    monogram_value = (monogram or slug_hint)[:4].upper()
    default_preset = "saas-demo" if audio_policy["allowAudioTrack"] is False else "shorts-completo"
    return {
        "schemaVersion": 1,
        "tenantId": tenant_id,
        "brandName": brand_name,
        "displayTitle": display_title,
        "monogram": monogram_value,
        "domain": domain,
        "url": f"https://{domain}",
        "tagline": tagline,
        "palette": palette,
        "typography": {
            "fontFamily": "Arial",
            "titleWeight": "bold",
            "bodyWeight": "bold" if audio_policy["allowAudioTrack"] is False else "regular",
        },
        "headerOverlay": {
            "enabled": True,
            "label": display_title,
            "badgeText": tagline.upper(),
            "bgColor": "#090D16",
            "textColor": "#F1F5F9",
            "height": 170,
        },
        "subtitleStyle": (
            "Fontname=Arial,Fontsize=12,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            "BackColour=&H80000000,Bold=1,Outline=2,Shadow=0,Alignment=2,MarginV=34"
        ),
        "defaultPreset": default_preset,
        "utmDefaults": {
            "utm_source": "instagram",
            "utm_medium": "reels",
            "utm_campaign_prefix": tenant_id.replace("-", ""),
        },
        "uiLabels": {
            "teamSectionTitle": "EQUIPE",
            "catalogSectionTitle": "SERVICOS",
            "publicRouteFallback": "/booking/[salonId]",
            "managerRouteFallback": "/gestor/agenda",
            "journeyBridgeCaption": "DO FLUXO ATUAL AO AGENDA DO SALAO",
            "itemUnitLabel": "servico",
            "customerLabel": "Cliente",
        },
    }


def _build_guardrails(tenant_id: str, audio_policy: dict) -> dict:
    return {
        "schemaVersion": 1,
        "tenantId": tenant_id,
        "forbiddenClaims": [
            "whatsapp",
            "sms",
            "lembrete",
            "24 horas",
            "24h",
            "automático",
            "automatico",
            "automatizado",
            "envio automático",
            "envio automatico",
            "redução de faltas",
            "reducao de faltas",
            "zero faltas",
            "faturamento garantido",
            "agenda sempre cheia",
        ],
        "forbiddenUiElements": [
            "pagamento",
            "cobrança",
            "cobranca",
            "a pagar",
            "checkout",
            "cartão de crédito",
            "cartao de credito",
        ],
        "routeRules": {
            "/booking/[salonId]": {
                "surface": "public-booking",
                "allowedResponsibilities": [
                    "identificacao-cliente-ficticia",
                    "escolha-servico",
                    "escolha-profissional",
                    "calculo-horarios-livres",
                    "confirmacao-agendamento",
                ],
                "forbiddenResponsibilities": [
                    "tela-pagamento",
                    "cobranca-simulada",
                    "envio-automatico-mensagem",
                ],
            },
            "/gestor/agenda": {
                "surface": "manager-agenda",
                "allowedResponsibilities": [
                    "visualizacao-agendamentos",
                    "filtro-profissional-status",
                    "alteracao-manual-status",
                ],
                "forbiddenResponsibilities": [
                    "calculo-horarios-livres",
                    "exibicao-slots-disponiveis",
                    "tela-pagamento",
                ],
            },
        },
        "audioPolicy": dict(audio_policy),
    }


def _build_fixture(tenant_id: str, brand_name: str, domain: str, tagline: str) -> dict:
    slug = tenant_id
    return {
        "schemaVersion": 1,
        "id": f"fixture-editorial-{slug}-v1",
        "descricao": (
            f"Fixture editorial dedicada para capturas de tela de {brand_name}. "
            "Dados integralmente ficticios. NAO usar em testes tecnicos automatizados (E2E, CI)."
        ),
        "data": datetime.date.today().isoformat(),
        "origem": "codex/fase1-conformidade-editorial",
        "guardrails": [
            "Sem promessas de automacao via WhatsApp/SMS/e-mail",
            "Sem fluxo de pagamento simulado (escopo NS-002)",
            "Separacao de rotas: /gestor/agenda = visualizacao/status manual; /booking/[salonId] = calculo de horarios livres",
            "Padrao de video: 1080x1920, 30fps, sem audio, com suporte a legendas queimadas e .srt",
        ],
        "estabelecimento": {
            "nome": brand_name,
            "nomeInterno": f"{slug}-modelo",
            "endereco": "Rua das Flores, 142 — Sao Paulo, SP",
            "telefone": "(11) 91234-5678",
            "site": f"https://{domain}",
            "horarioFuncionamento": "Terca a Sabado, 09h as 19h",
        },
        "profissionais": [
            {"id": "prof-001", "nome": "Profissional Um", "especialidade": "Servico Principal", "ativo": True},
            {"id": "prof-002", "nome": "Profissional Dois", "especialidade": "Servico Complementar", "ativo": True},
        ],
        "servicos": [
            {"id": "serv-001", "nome": "Servico Basico", "duracaoMin": 60, "precoBRL": 85.0, "categoria": "servico"},
            {"id": "serv-002", "nome": "Servico Premium", "duracaoMin": 50, "precoBRL": 110.0, "categoria": "servico"},
        ],
        "agenda": {
            "data": datetime.date.today().isoformat(),
            "diaDaSemana": "Terca-feira",
            "visaoRota": "/gestor/agenda",
            "nota": "Visualizacao e alteracao manual de status apenas. Horarios livres pertencem a rota /booking/[salonId].",
            "atendimentos": [
                {"id": "atend-001", "horario": "09:00", "duracaoMin": 60, "cliente": "Cliente Exemplo", "profissional": "prof-001", "servico": "serv-001", "status": "Confirmado"},
            ],
            "janelasSemAtendimento": [{"inicio": "12:00", "fim": "14:00", "nota": "intervalo"}],
        },
        "booking": {
            "nota": "Dados de horarios disponiveis para o cliente pertencem exclusivamente a rota /booking/[salonId].",
            "rota": f"/booking/{slug}-modelo",
            "servicosDisponiveis": ["serv-001", "serv-002"],
            "exemploFluxo": [
                "1. Cliente acessa /booking/[salonId]",
                "2. Escolhe o servico (ex.: Servico Basico — 60 min — R$ 85,00)",
                "3. Escolhe o profissional",
                "4. Visualiza horarios disponiveis no calendario",
                "5. Seleciona horario disponivel",
                "6. Confirma o agendamento — exibe mensagem 'Agendamento realizado'",
            ],
        },
    }


def _build_campaign(
    tenant_id: str,
    campaign_slug: str,
    campaign_title: str,
    brand_name: str,
    domain: str,
    tagline: str,
    audio_policy: dict,
) -> dict:
    brand_kit = _build_brand_kit(
        tenant_id, brand_name, domain, tagline, audio_policy, _default_palette(), "XX"
    )
    return {
        "schemaVersion": 1,
        "id": campaign_slug,
        "campaignId": campaign_slug.upper().replace("-", ""),
        "tenantId": tenant_id,
        "preset": brand_kit["defaultPreset"],
        "format": {
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "duration": CAMPAIGN_DURATION,
            "codec": "h264",
            "pixFmt": "yuv420p",
        },
        "subtitleStyle": brand_kit["subtitleStyle"],
        "artifacts": {
            "videoName": f"{campaign_slug}.mp4",
            "packageSrtName": f"{campaign_slug}.srt",
            "packageNarrationName": f"{campaign_slug}_narracao.txt",
            "manifestName": "manifest.json",
            "storyboardName": "preview-storyboard.png",
            "storyboardTimestamps": [2.0, 8.0, 16.0, 24.0],
        },
        "scenes": [
            {
                "id": "cena-01-hook",
                "kind": "hook-card",
                "start": 0.0,
                "duration": SRT_SCENE_SECONDS[0],
                "surface": "marca",
                "badge": tagline.upper(),
                "headline": campaign_title.upper(),
                "subline": campaign_title.upper(),
                "caption": campaign_title,
                "narrationText": campaign_title,
            },
            {
                "id": "cena-02-escolha",
                "kind": "booking-selection",
                "start": SRT_SCENE_SECONDS[0] + SRT_SCENE_SECONDS[1],
                "duration": SRT_SCENE_SECONDS[1],
                "surface": "public-booking",
                "route": f"/booking/{tenant_id}-modelo",
                "badge": "FLUXO PUBLICO /BOOKING",
                "headline": "ESCOLHA DO SERVICO E PROFISSIONAL",
                "caption": "A cliente escolhe o servico e o profissional.",
                "narrationText": f"Na rota publica /booking, a cliente escolhe o servico e o profissional.",
            },
            {
                "id": "cena-03-confirma",
                "kind": "booking-confirm",
                "start": SRT_SCENE_SECONDS[0] + SRT_SCENE_SECONDS[1] + SRT_SCENE_SECONDS[2],
                "duration": SRT_SCENE_SECONDS[2],
                "surface": "public-booking",
                "route": f"/booking/{tenant_id}-modelo",
                "badge": "HORARIOS LIVRES /BOOKING",
                "headline": "SELECIONA O HORARIO DISPONIVEL",
                "availableSlots": ["09:00", "11:00", "14:00", "16:30"],
                "selectedSlot": "09:00",
                "ctaLabel": "CONFIRMAR AGENDAMENTO",
                "caption": "Seleciona o horario disponivel e confirma.",
                "narrationText": f"Os horarios livres sao calculados em /booking/[salonId] e a cliente confirma o agendamento.",
            },
            {
                "id": "cena-04-ponte",
                "kind": "booking-success",
                "start": SRT_SCENE_SECONDS[0] + SRT_SCENE_SECONDS[1] + SRT_SCENE_SECONDS[2] + SRT_SCENE_SECONDS[3],
                "duration": SRT_SCENE_SECONDS[3],
                "surface": "public-booking",
                "route": f"/booking/{tenant_id}-modelo",
                "badge": "CONFIRMACAO",
                "headline": "AGENDAMENTO REALIZADO",
                "subline": "REGISTRO VISIVEL NA AGENDA DO SALAO",
                "caption": "Agendamento realizado.",
                "narrationText": "O agendamento e realizado e fica visivel na agenda do salao.",
            },
            {
                "id": "cena-05-salao-ve",
                "kind": "manager-agenda",
                "start": SRT_SCENE_SECONDS[0] + SRT_SCENE_SECONDS[1] + SRT_SCENE_SECONDS[2] + SRT_SCENE_SECONDS[3] + SRT_SCENE_SECONDS[4],
                "duration": SRT_SCENE_SECONDS[4],
                "surface": "manager-agenda",
                "route": "/gestor/agenda",
                "badge": "VISAO DO GESTOR /GESTOR/AGENDA",
                "headline": "AGENDA DO DIA - STATUS MANUAL",
                "highlightId": "atend-001",
                "caption": "O mesmo atendimento aparece na agenda do salao.",
                "narrationText": f"Na visao do gestor /gestor/agenda, o atendimento aparece com status manual.",
            },
            {
                "id": "cena-06-cta",
                "kind": "cta-card",
                "start": SRT_SCENE_SECONDS[0] + SRT_SCENE_SECONDS[1] + SRT_SCENE_SECONDS[2] + SRT_SCENE_SECONDS[3] + SRT_SCENE_SECONDS[4],
                "duration": SRT_SCENE_SECONDS[5],
                "surface": "marca",
                "route": domain,
                "badge": "MARCA",
                "headline": campaign_title.upper(),
                "subline": domain.upper(),
                "caption": campaign_title,
                "narrationText": campaign_title,
            },
        ],
    }


def _build_srt(campaign_slug: str) -> str:
    scenes = [
        ("cena-01-hook", 0.0, 4.0, "Conheca o fluxo conectado"),
        ("cena-02-escolha", 4.0, 6.0, "A cliente escolhe o servico"),
        ("cena-03-confirma", 10.0, 7.0, "Seleciona o horario disponivel"),
        ("cena-04-ponte", 17.0, 3.0, "Agendamento realizado"),
        ("cena-05-salao-ve", 20.0, 6.0, "Agendamento na agenda"),
        ("cena-06-cta", 26.0, 4.0, "Conheca o agendamento online"),
    ]
    lines: list[str] = []
    for index, (scene_id, start, duration, text) in enumerate(scenes, start=1):
        end = start + duration
        blocks = [
            str(index),
            f"00:00:{int(start):02d},{int(round((start % 1) * 1000)):03d} --> 00:00:{int(end):02d},{int(round((end % 1) * 1000)):03d}",
            text,
        ]
        lines.append("\n".join(blocks))
    return "\n\n".join(lines) + "\n"


def _build_narracao(campaign_slug: str, brand_name: str, domain: str) -> str:
    return (
        f"Roteiro de narracao - {campaign_slug}\n"
        "Video sem audio; texto para ferramenta externa, organizado por cena e tempos.\n"
        "\n"
        "[00:00:00,000 --> 00:00:04,000] cena-01-hook\n"
        f"Conheca o fluxo conectado do {brand_name}, do inicio ao agendamento.\n"
        "\n"
        "[00:00:04,000 --> 00:00:10,000] cena-02-escolha\n"
        "Na rota publica do cliente, a escolha do servico e do profissional acontece.\n"
        "\n"
        "[00:00:10,000 --> 00:00:17,000] cena-03-confirma\n"
        "Os horarios livres sao calculados e a cliente confirma o agendamento.\n"
        "\n"
        "[00:00:17,000 --> 00:00:20,000] cena-04-ponte\n"
        "O agendamento fica registrado na agenda do time.\n"
        "\n"
        "[00:00:20,000 --> 00:00:26,000] cena-05-salao-ve\n"
        "A equipe visualiza o atendimento com status manual.\n"
        "\n"
        "[00:00:26,000 --> 00:00:30,000] cena-06-cta\n"
        f"Conheca o agendamento online em {domain}.\n"
    )


def _social_copies(
    campaign_slug: str,
    brand_name: str,
    tagline: str,
    domain: str,
    audio_policy: dict,
    hook_a: str,
    hook_b: str,
) -> dict[str, str]:
    base = f"{brand_name} — {tagline}"
    return {
        "instagram-reels.md": (
            f"Conheca o {brand_name}\n\n"
            f"{tagline.upper()}\n\n"
            f"Agendamento online e agenda do time em poucos toques.\n\n"
            f"https://{domain}/?utm_source=instagram&utm_medium=reels&utm_campaign={campaign_slug}&utm_content={brand_name.lower().replace(' ', '-')}\n\n"
            "Conheca o sistema — link na bio\n\n"
            f"#{(brand_name.lower().replace(' ', '')).upper()} #AgendamentoOnline #AgendaDoSalao\n"
        ),
        "youtube-shorts.md": (
            f"{brand_name} — {tagline.upper()}\n\n"
            f"Descubra como organizar a agenda do time em poucos minutos.\n\n"
            f"https://{domain}/?utm_source=youtube&utm_medium=shorts&utm_campaign={campaign_slug}&utm_content={brand_name.lower().replace(' ', '-')}\n\n"
            "Assista ate o fim e acesse o link na descricao\n\n"
            f"#{(brand_name.lower().replace(' ', '')).upper()} #Shorts\n"
        ),
        "facebook-reels.md": (
            f"Conheca o {brand_name}\n\n"
            f"{tagline.upper()}\n\n"
            f"Agende servicos diretamente pela agenda online.\n\n"
            f"https://{domain}/?utm_source=facebook&utm_medium=reels&utm_campaign={campaign_slug}&utm_content={brand_name.lower().replace(' ', '-')}\n\n"
            "Acesse pelo link da descricao\n\n"
            f"#{(brand_name.lower().replace(' ', '')).upper()} #Reels\n"
        ),
    }


def _guardrails_preview(
    guardrails: dict,
    campaign: dict | None,
    campaign_slug: str | None,
    brand_name: str,
    domain: str,
    brand: dict,
    policy: dict,
) -> bool:
    """Pre-validacao editorial, em memoria, dos textos que a campanha geraria."""
    if campaign is None or campaign_slug is None:
        return True
    first = campaign["scenes"][0]
    social_texts = _social_copies(
        campaign_slug,
        brand_name,
        brand["tagline"],
        domain,
        policy,
        first["headline"],
        first["subline"],
    )
    texts = [
        ("srt", _build_srt(campaign_slug)),
        ("narracao", _build_narracao(campaign_slug, brand_name, domain)),
        *social_texts.items(),
    ]
    for _fonte, texto in texts:
        violacoes = tenant_validator.validate_text_against_guardrails(
            texto, guardrails, check_ui_elements=True
        )
        if violacoes:
            return False
    return True


def _tenant_validation(root_real: str, tenant_id: str) -> tuple[bool, list[str]]:
    """Valida o tenant gravado (ou staged) com fail-closed: qualquer excecao reprova."""
    try:
        tenant_validator.load_and_validate_tenant(tenant_id, root=root_real, strict=True)
        return True, []
    except tenant_validator.TenantContractError as exc:
        return False, [str(item) for item in (exc.errors or [exc.code])]
    except Exception as exc:  # validador indisponivel tambem e' falha fechada
        return False, [f"VALIDADOR_INDISPONIVEL: {type(exc).__name__}: {exc}"]


def _stage_preview(
    root_real: str,
    targets: list[tuple[str, dict]],
    tenant_id: str,
    guardrails: dict,
    campaign: dict | None,
    campaign_slug: str | None,
    brand_name: str,
    domain: str,
    brand: dict,
    policy: dict,
) -> dict:
    """Pre-valida os contratos em staging descartavel sob <RAIZ>/.workspace/tmp."""
    base = os.path.join(root_real, ".workspace", "tmp", "tenant-scaffolder-preview")
    os.makedirs(render_local.fs_path(base), exist_ok=True)
    staging = tempfile.mkdtemp(prefix="scaffold-", dir=render_local.fs_path(base))
    try:
        schemas_src = os.path.join(root_real, "schemas")
        if os.path.isdir(render_local.fs_path(schemas_src)):
            shutil.copytree(
                render_local.fs_path(schemas_src),
                render_local.fs_path(os.path.join(staging, "schemas")),
            )
        for rel, data in targets:
            abs_path = os.path.realpath(os.path.join(staging, rel))
            if not _contained(os.path.realpath(staging), abs_path):
                return {"tenantValidatorOk": False, "editorialQaPreview": False,
                        "errors": ["PATH_OUTSIDE_ROOT: " + rel]}
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            _write_json(abs_path, data)
        ok, errors = _tenant_validation(staging, tenant_id)
        preview: dict[str, Any] = {
            "tenantValidatorOk": ok,
            "editorialQaPreview": (
                _guardrails_preview(
                    guardrails, campaign, campaign_slug, brand_name, domain, brand, policy
                )
                if ok
                else False
            ),
        }
        if errors:
            preview["errors"] = errors
        return preview
    finally:
        shutil.rmtree(render_local.fs_path(staging), ignore_errors=True)


def _rollback(
    root_real: str,
    written: list[str],
    tenant_dir: str,
    tenant_dir_preexists: bool,
) -> None:
    """Remove somente o que esta rodada gravou; nunca toca tenants preexistentes."""
    for rel in written:
        try:
            os.remove(os.path.join(root_real, *rel.split("/")))
        except OSError:
            pass
    if not tenant_dir_preexists:
        shutil.rmtree(render_local.fs_path(tenant_dir), ignore_errors=True)
        tenants_dir = os.path.dirname(tenant_dir)
        try:
            os.rmdir(render_local.fs_path(tenants_dir))
        except OSError:
            pass


def scaffold_tenant(
    tenant_id: str,
    brand_name: str,
    domain: str,
    audio_policy: str = "an",
    tagline: str | None = None,
    palette: dict | None = None,
    with_campaign: str | None = None,
    campaign_title: str | None = None,
    root: str = ".",
    apply: bool = False,
) -> dict:
    """Gera contrato de tenant (e campanha inicial opcional) para um novo tenant.

    Operacao 100% read-only quando ``apply=False``; grava em disco somente
    com ``apply=True`` (validado explicitamente pela CLI).
    """
    root_real = os.path.realpath(root)
    tenant_id = _validate_tenant_id(tenant_id)
    slug = _validate_slug(tenant_id) if not with_campaign else _validate_slug(with_campaign)

    existing = tenant_validator.list_tenants(root_real)
    if tenant_id in existing:
        raise ScaffolderError("TENANT_JA_EXISTE", f"tenant '{tenant_id}' ja existe")

    policy = AUDIO_POLICIES.get(audio_policy)
    if policy is None:
        raise ScaffolderError("PRESET_INVALIDO", f"audio-policy desconhecido: '{audio_policy}'")
    preset = "shorts-completo" if policy["allowAudioTrack"] else "saas-demo"

    brand = _build_brand_kit(
        tenant_id,
        brand_name,
        domain,
        tagline or _default_tagline(brand_name),
        policy,
        palette or _default_palette(),
        "",
    )
    guardrails = _build_guardrails(tenant_id, policy)
    fixture = _build_fixture(tenant_id, brand_name, domain, brand["tagline"])
    campaign: dict | None = None

    if with_campaign:
        campaign_slug = _validate_slug(with_campaign)
        campaign = _build_campaign(
            tenant_id, campaign_slug, campaign_title or _default_tagline(brand_name),
            brand_name, domain, brand["tagline"], policy,
        )

    tenant_rel = f"tenants/{tenant_id}/brand-kit.json"
    guardrails_rel = f"tenants/{tenant_id}/guardrails.json"
    fixture_rel = f"tenants/{tenant_id}/fixtures/fixture-editorial-{tenant_id}.json"

    targets: list[tuple[str, dict]] = [
        (tenant_rel, brand),
        (guardrails_rel, guardrails),
        (fixture_rel, fixture),
    ]
    if with_campaign:
        targets.append(
            (f"tenants/{tenant_id}/campaigns/{_validate_slug(with_campaign)}.json", campaign)
        )

    for rel, _data in targets:
        abs_path = os.path.realpath(os.path.join(root_real, rel))
        if not _contained(root_real, abs_path):
            raise ScaffolderError("PATH_OUTSIDE_ROOT", rel)

    campaign_slug = _validate_slug(with_campaign) if with_campaign else None

    if not apply:
        validation = _stage_preview(
            root_real, targets, tenant_id, guardrails, campaign, campaign_slug,
            brand_name, domain, brand, policy,
        )
        return {
            "ok": True,
            "dryRun": True,
            "applied": False,
            "tenantId": tenant_id,
            "brandName": brand_name,
            "audioPolicy": policy,
            "campaignSlug": with_campaign,
            "plannedFiles": [
                {"path": rel, "sha256": "pending", "apply": False} for rel, _data in targets
            ],
            "writtenFiles": [],
            "validation": validation,
            "nextSteps": [
                "Revisar os contratos planejados; a validacao acima e previa, em staging descartavel.",
                "Gravar com --apply somente apos conferencia do titular.",
            ],
        }

    tenant_dir = os.path.join(root_real, "tenants", tenant_id)
    tenant_dir_preexists = os.path.isdir(render_local.fs_path(tenant_dir))
    written: list[str] = []
    try:
        for rel, data in targets:
            abs_path = os.path.realpath(os.path.join(root_real, rel))
            os.makedirs(render_local.fs_path(os.path.dirname(abs_path)), exist_ok=True)
            _write_json(abs_path, data)
            written.append(rel)
    except Exception:
        _rollback(root_real, written, tenant_dir, tenant_dir_preexists)
        raise

    validator_ok, tenant_errors = _tenant_validation(root_real, tenant_id)
    editorial_ok = (
        _guardrails_preview(
            guardrails, campaign, campaign_slug, brand_name, domain, brand, policy
        )
        if validator_ok
        else False
    )
    if not validator_ok or not editorial_ok:
        _rollback(root_real, written, tenant_dir, tenant_dir_preexists)
        motivo = (
            "contrato invalido: " + "; ".join(tenant_errors)
            if not validator_ok
            else "violacao de guardrails na pre-validacao editorial"
        )
        raise ScaffolderError("SCAFFOLD_VALIDACAO_FALHOU", motivo)

    return {
        "ok": True,
        "dryRun": False,
        "applied": True,
        "tenantId": tenant_id,
        "brandName": brand_name,
        "audioPolicy": policy,
        "campaignSlug": with_campaign,
        "plannedFiles": [rel for rel, _data in targets],
        "writtenFiles": written,
        "validation": {
            "tenantValidatorOk": True,
            "editorialQaPreview": editorial_ok,
        },
        "nextSteps": [
            "Renderizar a campanha com preset_runner apos conferencia do titular.",
            "Gerar pacote social com publish_pack apos o render.",
            "Simular capacidade editorial com campaign_calendar --simulate-capacity.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scaffolder automatico de tenant e campanha inicial (100% stdlib)"
    )
    parser.add_argument("--tenant-id", required=True, help="Slug kebab-case do novo tenant")
    parser.add_argument("--brand-name", required=True, help="Nome comercial da marca")
    parser.add_argument("--domain", required=True, help="Dominio do nicho (ex.: novotenant.com.br)")
    parser.add_argument("--tagline", default=None, help="Tagline opcional (neutra se ausente)")
    parser.add_argument("--audio-policy", choices=("an", "aac"), default="an", help="Politica de audio (padrao an)")
    parser.add_argument("--preset", default=None, help="Preset suportado (saas-demo|shorts-completo)")
    parser.add_argument("--palette", default=None, help="JSON de paleta acessivel (opcional)")
    parser.add_argument("--with-campaign", default=None, help="Slug da campanha inicial a gerar")
    parser.add_argument("--campaign-title", default=None, help="Titulo da campanha inicial")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Somente planeja (padrao)")
    mode.add_argument("--apply", action="store_true", help="Grava contratos e campanha no disco")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument("--json", action="store_true", help="Emite JSON no stdout")
    args = parser.parse_args(argv)

    if args.dry_run and args.apply:
        parser.error("--dry-run e --apply sao mutuamente exclusivos")

    if not args.dry_run and not args.apply:
        parser.error("informe --dry-run (padrao) ou --apply")

    try:
        result = scaffold_tenant(
            tenant_id=args.tenant_id,
            brand_name=args.brand_name,
            domain=args.domain,
            audio_policy=args.audio_policy,
            tagline=args.tagline,
            palette=json.loads(args.palette) if args.palette else None,
            with_campaign=args.with_campaign,
            campaign_title=args.campaign_title,
            root=args.root,
            apply=args.apply,
        )
    except ScaffolderError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc), "code": exc.code}, ensure_ascii=False))
        else:
            print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except tenant_validator.TenantContractError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc), "code": exc.code}, ensure_ascii=False))
        else:
            print(f"Erro de contrato: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "DRY-RUN" if result["dryRun"] else "APPLIED"
        print(f"Scaffold {status}: tenant {result['tenantId']} ({result['brandName']})")
        for path in result["writtenFiles"]:
            print(f"  - {path}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
