"""Motor programatico de cards estaticos para Instagram Stories e Carrossel
(Agente 1 - Etapa 5).

Gera, para cada campanha em tenants/*/campaigns/*.json, dois kits visuais
versionados em 01-insta-stories/deliveries/<tenantId>/<slug>/:

  stories/      - 3 banners verticais 1080x1920
                  (story-01-hook.png, story-02-fluxo.png, story-03-cta.png)
  carousel/     - 4 slides retrato 1080x1350 (proporcao 4:5)
                  (slide-01-capa.png, slide-02-problema.png,
                   slide-03-pratica.png, slide-04-resumo-cta.png)
  static-manifest.json - schemaVersion 1, guardrailsAudited, dimensoes,
                         bytes e SHA-256 de cada uma das 7 laminas PNG.

100% biblioteca padrao Python (zlib, struct, json, hashlib, argparse).
Reutiliza as primitivas de canvas PNG e fonte bitmap 5x7 de
tools/ns002_pilot.py (as mesmas reutilizadas por tools/preset_runner.py).
Nao exige Pillow/PIL. So produz imagens estaticas: nao ha faixa de audio.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import zlib
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import carousel_layout
import ns002_pilot
import render_local
import tenant_validator

# ---------------------------------------------------------------------------
# Primitivas de desenho reutilizadas (bitmap 5x7, stdlib, sem fontes do sistema)
# ---------------------------------------------------------------------------
_draw_text = ns002_pilot._draw_text
_wrap_text = ns002_pilot._wrap_text
_fill_rect = ns002_pilot._fill_rect
_stroke_rect = ns002_pilot._stroke_rect
_draw_card = ns002_pilot._draw_card
_draw_pill = ns002_pilot._draw_pill
_encode_png = ns002_pilot._encode_png
_base_gradient = ns002_pilot._base_gradient
_pal = ns002_pilot._pal
_format_price_brl = ns002_pilot._format_price_brl
_norm_text = ns002_pilot._norm_text
_text_width = ns002_pilot._text_width

STORY_W = 1080
STORY_H = 1920
CAROUSEL_W = 1080
CAROUSEL_H = 1350

HEADER_H = 170
DARK_INK = (14, 18, 28)

KIT_STORIES = "stories"
KIT_CAROUSEL = "carousel"
KIT_SIZES = {
    KIT_STORIES: (STORY_W, STORY_H),
    KIT_CAROUSEL: (CAROUSEL_W, CAROUSEL_H),
}

STORY_FILES = ("story-01-hook.png", "story-02-fluxo.png", "story-03-cta.png")
CAROUSEL_FILES = (
    "slide-01-capa.png",
    "slide-02-problema.png",
    "slide-03-pratica.png",
    "slide-04-resumo-cta.png",
)

DELIVERIES_REL = "01-insta-stories/deliveries"
NARRATION_REL = "02-reels-shorts/deliveries"


class StaticCardsError(Exception):
    """Falha controlada do motor de cards estaticos (mensagem sanitizada)."""

    def __init__(self, code: str, errors: list[str] | None = None):
        self.code = code
        self.errors = errors or []
        summary = f"{code}: " + "; ".join(self.errors) if self.errors else code
        super().__init__(summary)


GUARDRAIL_VIOLACAO = "GUARDRAIL_VIOLACAO"


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_json(path: str) -> dict:
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _png_dimensions(png_data: bytes) -> tuple[int, int]:
    """Largura e altura lidas do header IHDR do PNG (sem dependencias externas)."""
    if len(png_data) < 24 or png_data[:8] != b"\x89PNG\r\n\x1a\n":
        raise StaticCardsError("PNG_INVALID", ["assinatura PNG ausente"])
    if png_data[12:16] != b"IHDR":
        raise StaticCardsError("PNG_INVALID", ["chunk IHDR ausente"])
    return struct.unpack(">II", png_data[16:24])


def _emit_png_file(path: str, width: int, height: int, canvas: bytearray) -> bytes:
    data = _encode_png(width, height, canvas)
    with open(render_local.fs_path(path), "wb") as handle:
        handle.write(data)
    return data


def _write_text_lf(path: str, text: str) -> None:
    with open(render_local.fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


# ---------------------------------------------------------------------------
# Helpers de marca
# ---------------------------------------------------------------------------
def _brand_palette(brand_kit: dict) -> dict:
    return brand_kit.get("palette", {}).get("rgb", {})


def _overlay_cfg(brand_kit: dict) -> dict:
    return brand_kit.get("headerOverlay") or {}


def _utm_source(brand_kit: dict) -> str:
    return str(((brand_kit.get("utmDefaults") or {})).get("utm_source", "instagram"))


def _cta_call(brand_kit: dict) -> str:
    """CTA explícito sem desenhar botão/sticker clicável falso."""
    return "LINK NA BIO" if _utm_source(brand_kit) == "instagram" else "LINK NA DESCRICAO"


def _first_narration_line(narration_text: str) -> str:
    """Extrai o texto do primeiro bloco de narracao da entrega (.txt)."""
    if not narration_text:
        return ""
    blocks = [b for b in narration_text.split("\n\n") if b.strip()]
    if not blocks:
        return ""
    lines = blocks[0].splitlines()
    return lines[1].strip() if len(lines) > 1 else blocks[0].strip()


def _draw_brand_header(canvas, width, height, brand_kit, route_label=None, header_h=HEADER_H):
    """Cabecalho de marca: monogram da brandKit, displayTitle, tagline."""
    palette = _brand_palette(brand_kit)
    overlay = _overlay_cfg(brand_kit)
    header_h = int(overlay.get("height", header_h))
    header_bg = _pal(palette, "headerBg")
    accent = _pal(palette, "primaryAccent")
    secondary = _pal(palette, "secondaryAccent")
    text_pri = _pal(palette, "textPrimary")
    text_mut = _pal(palette, "textMuted")

    _fill_rect(canvas, width, height, 0, 0, width, header_h, header_bg)
    _fill_rect(canvas, width, height, 0, header_h - 6, width, header_h, accent)

    mono = str(brand_kit.get("monogram", "??"))
    _fill_rect(canvas, width, height, 56, 44, 128, 116, accent)
    _draw_text(canvas, width, height, 69, 64, mono, 4, DARK_INK)

    _draw_text(canvas, width, height, 152, 42, str(brand_kit.get("displayTitle", "MARCA")), 5, text_pri)
    _draw_text(canvas, width, height, 152, 92, str(brand_kit.get("tagline", "")), 2, text_mut)

    if route_label:
        rw = _text_width(route_label, 2) + 28
        x0 = width - 56 - rw
        _fill_rect(canvas, width, height, x0, 56, width - 56, 102, secondary)
        _draw_text(canvas, width, height, x0 + 14, 71, route_label, 2, text_pri)
    return header_h


def _draw_sequence_chip(canvas, width, height, y, label, palette):
    accent = _pal(palette, "primaryAccent")
    text_pri = _pal(palette, "textPrimary")
    _draw_pill(canvas, width, height, width - 122, y, label, 3, accent, text_pri)


# ---------------------------------------------------------------------------
# Auditoria de guardrails (antes de qualquer pixel)
# ---------------------------------------------------------------------------
def _audit_texts(texts: list[tuple[str, str]], guardrails: dict) -> list[str]:
    violations: list[str] = []
    for label, text in texts:
        if not text:
            continue
        found = tenant_validator.validate_text_against_guardrails(
            text, guardrails, check_ui_elements=True
        )
        for v in found:
            violations.append(f"{label}: {v}")
    return violations


# ---------------------------------------------------------------------------
# Montagem de copias (todos os textos que serao renderizados)
# ---------------------------------------------------------------------------
def _problema_lines(brand_kit: dict) -> list[str]:
    brand_name = str(brand_kit.get("brandName", ""))
    if brand_name == "Estúdio Flow":
        return [
            "Reserva por troca de mensagens com a instrutora",
            "Modalidade e instrutora sem confirmacao na hora",
            "Grade de turmas sem visualizacao unificada",
            "Status da aula atualizado fora do sistema",
        ]
    if str(brand_kit.get("tenantId")) == "multitrack-hub":
        return [
            "Stems espalhados por pastas diferentes",
            "BPM e tom sem um catalogo unificado",
            "Rateio de faixas sem controle de vagas",
            "Download de projetos dificil de organizar",
        ]
    return [
        "Horario anotado em papel ou planilha avulsa",
        "Horario escolhido pelo cliente nao chega a agenda do salão",
        "Profissional confere o status manualmente",
        "Risco de horarios sobrepostos e dupla marcacao",
    ]


def _campaign_routes(guardrails: dict, fixture: dict) -> list[str]:
    """Linhas de rota extraídas de routeRules (sep. de superfícies, sem simulação)."""
    route_lines: list[str] = []
    route_rules = guardrails.get("routeRules") or {}
    for route, rule in list(route_rules.items())[:2]:
        surface = str(rule.get("surface", route))
        route_lines.append(f"ROTA {surface.upper()}: {route}")
    if not route_lines:
        rota = str((fixture.get("booking") or {}).get("rota", "/"))
        route_lines.append(f"ROTA PUBLICA: {rota}")
    return route_lines


def _build_copy(config: dict, brand_kit: dict, guardrails: dict, fixture: dict, narration_text: str) -> dict:
    scenes = list(config.get("scenes", []))
    first = scenes[0] if scenes else {}
    hook = str(first.get("headline") or "")
    subline = str(first.get("subline") or brand_kit.get("tagline") or "")
    badge = str(first.get("badge") or "")
    domain = str(brand_kit.get("domain", ""))
    cta = _cta_call(brand_kit)
    narration_first = _first_narration_line(narration_text)

    is_multitrack = bool(fixture.get("projetos") or fixture.get("rateios"))
    services = fixture.get("servicos", [])
    profs = fixture.get("profissionais", [])
    projects = fixture.get("projetos", [])
    rateios = fixture.get("rateios", [])

    if is_multitrack:
        flux_badge = "DADOS REAIS DO CATALOGO"
        flux_headline = "PROJETO, STEMS E RATEIO"
        rows: list[str] = []
        if projects:
            p = projects[0]
            stems = p.get("stems", [])
            rows.append(f"PROJETO: {p.get('titulo', '-')}")
            rows.append(f"REFERENCIA: {p.get('artistaReferencia', '-')}")
            rows.append(f"BPM {p.get('bpm', '-')} | TOM {p.get('tom', '-')} | {p.get('compasso', '-')}")
            rows.append(f"STEMS: {len(stems)} | {p.get('formato', '-')}")
        if rateios:
            r = rateios[0]
            rows.append(f"RATEIO: {r.get('titulo', '-')}")
            rows.append(f"COTA: {_format_price_brl(r.get('cotaBRL', 0))} | VAGAS: {r.get('vagasRestantes', 0)}")
        value_lines = [
            "Catalogo, stems e rateios organizados por projeto",
            "BPM, tom e stems separados por instrumento",
            "Rateios com cota e vagas restantes claras",
        ]
        pratica_items = [f"{p.get('titulo', '-')} - {len(p.get('stems', []))} stems" for p in projects[:3]]
        cta_headline = "POR QUE ORGANIZAR O CATALOGO"
    else:
        flux_badge = "DADOS REAIS DA FIXTURE EDITORIAL"
        flux_headline = "SERVICO, PROFISSIONAL E PRECO BRL"
        rows = []
        if services:
            s = services[0]
            rows.append(f"SERVICO: {s.get('nome', '-')} - {s.get('duracaoMin', 0)} MIN")
            rows.append(f"PRECO: {_format_price_brl(s.get('precoBRL', 0))}")
        if profs:
            pr = profs[0]
            rows.append(f"PROFISSIONAL: {pr.get('nome', '-')}")
            especialidade = str(pr.get("especialidade", "-"))
            rows.append(f"ESPECIALIDADE: {especialidade[:40]}")
        agenda = fixture.get("agenda", {})
        atendimentos = agenda.get("atendimentos", [])
        if atendimentos:
            rows.append(f"AGENDA {agenda.get('data', '')}: {len(atendimentos)} atendimentos")
        value_lines = [
            "Horario escolhido pela cliente chega direto a agenda do salão",
            "Agenda do dia com status em uma unica tela",
            "Confirmacao de agendamento concluida no fluxo publico",
        ]
        pratica_items = [
            f"{s.get('nome', '-')} - {s.get('duracaoMin', 0)} MIN - {_format_price_brl(s.get('precoBRL', 0))}"
            for s in services[:3]
        ]
        cta_headline = "RESUMO DE VALOR OPERACIONAL"

    return {
        "hook": hook,
        "subline": subline,
        "badge": badge,
        "domain": domain,
        "cta": cta,
        "narration_first": narration_first,
        "flux_badge": flux_badge,
        "flux_headline": flux_headline,
        "flux_rows": rows,
        "route_lines": _campaign_routes(guardrails, fixture),
        "value_lines": value_lines,
        "pratica_items": pratica_items,
        "cta_headline": cta_headline,
        "is_multitrack": is_multitrack,
    }


# ---------------------------------------------------------------------------
# Especificacoes de laminas (textos para auditoria + render)
# ---------------------------------------------------------------------------
def _story_01_spec(brand_kit: dict, copy: dict, route_label: str | None) -> dict:
    palette = _brand_palette(brand_kit)
    texts = [
        ("story-01 header", str(brand_kit.get("headerOverlay", {}).get("label", ""))),
        ("story-01 badge", copy["badge"]),
        ("story-01 hook", copy["hook"]),
        ("story-01 subline", copy["subline"]),
        ("story-01 narracao", copy["narration_first"]),
        ("story-01 dominio", copy["domain"]),
        ("story-01 sequencia", "1/3"),
        ("story-01 rodape", "CONTEUDO ESTATICO - VERTICAL 9:16 - SEM AUDIO"),
    ]
    if route_label:
        texts.append(("story-01 rota", route_label))

    def render(canvas, width, height):
        header_h = _draw_brand_header(canvas, width, height, brand_kit, route_label=route_label)
        _draw_sequence_chip(canvas, width, height, header_h + 40, "1/3", palette)
        secondary = _pal(palette, "secondaryAccent")
        text_pri = _pal(palette, "textPrimary")
        text_mut = _pal(palette, "textMuted")
        accent = _pal(palette, "primaryAccent")
        _, ph = _draw_pill(canvas, width, height, 56, header_h + 70, copy["badge"], 3, secondary, text_pri)
        ly = header_h + 70 + ph + 34
        for line in _wrap_text(copy["hook"], width - 190, 6):
            _draw_text(canvas, width, height, 102, ly, line, 6, text_pri)
            ly += carousel_layout.char_height(6) + 26
        _draw_text(canvas, width, height, 102, ly + 24, copy["subline"], 4, accent)
        ly += 24
        if copy["narration_first"]:
            ly += 40
            for line in _wrap_text(copy["narration_first"], width - 190, 3):
                _draw_text(canvas, width, height, 102, ly, line, 3, text_mut)
                ly += carousel_layout.char_height(3) + 10
        _draw_text(canvas, width, height, 102, height - 200, copy["domain"], 5, accent)
        _draw_text(canvas, width, height, 102, height - 140, "CONTEUDO ESTATICO - VERTICAL 9:16 - SEM AUDIO", 2, text_mut)

    return {"kit": "stories", "name": "story-01-hook.png", "texts": texts, "render": render}


def _story_02_spec(brand_kit: dict, copy: dict) -> dict:
    palette = _brand_palette(brand_kit)
    texts = [
        ("story-02 badge", copy["flux_badge"]),
        ("story-02 headline", copy["flux_headline"]),
    ]
    for row in copy["flux_rows"]:
        texts.append((f"story-02 row: {row[:20]}", row))
    for line in copy["route_lines"]:
        texts.append((f"story-02 rota: {line[:20]}", line))

    def render(canvas, width, height):
        header_h = _draw_brand_header(
            canvas, width, height, brand_kit,
            route_label=copy["route_lines"][0] if copy["route_lines"] else None,
        )
        _draw_sequence_chip(canvas, width, height, header_h + 40, "2/3", palette)
        secondary = _pal(palette, "secondaryAccent")
        text_pri = _pal(palette, "textPrimary")
        text_mut = _pal(palette, "textMuted")
        accent = _pal(palette, "primaryAccent")
        card_bg = _pal(palette, "cardBg")

        _, ph = _draw_pill(canvas, width, height, 56, header_h + 70, copy["flux_badge"], 3, secondary, text_pri)
        ly = header_h + 70 + ph + 34
        for line in _wrap_text(copy["flux_headline"], width - 190, 5):
            _draw_text(canvas, width, height, 102, ly, line, 5, accent)
            ly += carousel_layout.char_height(5) + 16
        cy = ly + 30
        _draw_card(canvas, width, height, 56, cy, width - 56, cy + 330, card_bg,
                   border_color=secondary, border_thickness=3)
        ty = cy + 26
        for row in copy["flux_rows"]:
            _draw_text(canvas, width, height, 84, ty, row, 3, text_pri)
            ty += carousel_layout.char_height(3) + 18
        ry = cy + 330 + 30
        for line in copy["route_lines"]:
            _draw_text(canvas, width, height, 84, ry, line, 3, text_mut)
            ry += carousel_layout.char_height(3) + 14
        _fill_rect(canvas, width, height, 102, height - 120, 300, height - 112, accent)
        _draw_text(canvas, width, height, 102, height - 100, "AGENDAMENTO NO FLUXO PUBLICO", 3, text_pri)

    return {"kit": "stories", "name": "story-02-fluxo.png", "texts": texts, "render": render}


def _story_03_spec(brand_kit: dict, copy: dict) -> dict:
    palette = _brand_palette(brand_kit)
    texts = [
        ("story-03 badge", "CHAMADA PARA A ACAO"),
        ("story-03 headline", copy["cta_headline"]),
    ]
    for line in copy["value_lines"]:
        texts.append((f"story-03 valor: {line[:20]}", line))
    texts.append(("story-03 cta", copy["cta"]))
    texts.append(("story-03 dominio", copy["domain"]))
    texts.append(("story-03 sequencia", "3/3"))

    def render(canvas, width, height):
        header_h = _draw_brand_header(canvas, width, height, brand_kit)
        _draw_sequence_chip(canvas, width, height, header_h + 40, "3/3", palette)
        secondary = _pal(palette, "secondaryAccent")
        text_pri = _pal(palette, "textPrimary")
        text_mut = _pal(palette, "textMuted")
        accent = _pal(palette, "primaryAccent")

        _, ph = _draw_pill(canvas, width, height, 56, header_h + 80, "CHAMADA PARA A ACAO", 3, secondary, text_pri)
        ly = header_h + 80 + ph + 34
        _draw_text(canvas, width, height, 102, ly, copy["cta_headline"], 5, text_pri)
        ly += carousel_layout.char_height(5) + 40
        for line in copy["value_lines"]:
            _draw_text(canvas, width, height, 102, ly, line, 3, text_pri)
            ly += carousel_layout.char_height(3) + 16
        cy = height // 2 - 60
        tw = _text_width(copy["cta"], 7)
        _draw_text(canvas, width, height, (width - tw) // 2, cy, copy["cta"], 7, accent)
        _draw_text(canvas, width, height, 102, cy + 70, copy["domain"], 5, accent)
        _fill_rect(canvas, width, height, 56, height - 130, width - 56, height - 122, secondary)

    return {"kit": "stories", "name": "story-03-cta.png", "texts": texts, "render": render}


def _carousel_01_spec(brand_kit: dict, copy: dict) -> dict:
    palette = _brand_palette(brand_kit)
    title = copy["hook"] or f"GUIA PRATICO {str(brand_kit.get('brandName', ''))}"
    texts = [
        ("carousel-01 badge", "GUIA PRATICO | 1/4"),
        ("carousel-01 titulo", title),
        ("carousel-01 subline", str(brand_kit.get("tagline", ""))),
        ("carousel-01 dominio", copy["domain"]),
        ("carousel-01 rodape", "CARROSSEL RETRATO - 1080x1350 - 4:5"),
    ]

    def render(canvas, width, height):
        header_h = _draw_brand_header(canvas, width, height, brand_kit)
        secondary = _pal(palette, "secondaryAccent")
        text_pri = _pal(palette, "textPrimary")
        text_mut = _pal(palette, "textMuted")
        accent = _pal(palette, "primaryAccent")

        _, ph = _draw_pill(canvas, width, height, 56, header_h + 60, "GUIA PRATICO | 1/4", 4, secondary, text_pri)
        ly = header_h + 60 + ph + 34
        for line in _wrap_text(title, width - 190, 7):
            _draw_text(canvas, width, height, 56, ly, line, 7, text_pri)
            ly += carousel_layout.char_height(7) + 24
        _draw_text(canvas, width, height, 56, ly + 20, str(brand_kit.get("tagline", "")), 3, text_mut)
        _draw_text(canvas, width, height, 56, height - 110, f"ACESSE: {copy['domain']}", 5, accent)
        _draw_text(canvas, width, height, 56, height - 60, "CARROSSEL RETRATO - 1080x1350 - 4:5", 2, text_mut)

    return {"kit": "carousel", "name": "slide-01-capa.png", "texts": texts, "render": render}


def _carousel_02_spec(brand_kit: dict, copy: dict) -> dict:
    palette = _brand_palette(brand_kit)
    problemas = _problema_lines(brand_kit)
    texts = [
        ("carousel-02 badge", "DIAGNOSTICO | 2/4"),
        ("carousel-02 titulo", "DIAGNOSTICO DA ROTINA OPERACIONAL"),
    ]
    for line in problemas:
        texts.append((f"carousel-02 problema: {line[:20]}", line))

    def render(canvas, width, height):
        header_h = _draw_brand_header(canvas, width, height, brand_kit)
        secondary = _pal(palette, "secondaryAccent")
        text_pri = _pal(palette, "textPrimary")
        accent = _pal(palette, "primaryAccent")

        _, ph = _draw_pill(canvas, width, height, 56, header_h + 50, "DIAGNOSTICO | 2/4", 4, secondary, text_pri)
        ly = header_h + 50 + ph + 34
        _draw_text(canvas, width, height, 56, ly, "DIAGNOSTICO DA ROTINA OPERACIONAL", 6, accent)
        ly += carousel_layout.char_height(6) + 34
        for line in problemas:
            _draw_text(canvas, width, height, 56, ly, "- " + line, 3, text_pri)
            ly += carousel_layout.char_height(3) + 16

    return {"kit": "carousel", "name": "slide-02-problema.png", "texts": texts, "render": render}


def _carousel_03_spec(brand_kit: dict, copy: dict) -> dict:
    palette = _brand_palette(brand_kit)
    texts = [
        ("carousel-03 badge", "PRATICA | 3/4"),
        ("carousel-03 titulo", "3 ITENS DA PRATICA"),
    ]
    for item in copy["pratica_items"]:
        texts.append((f"carousel-03 item: {item[:20]}", item))

    def render(canvas, width, height):
        header_h = _draw_brand_header(canvas, width, height, brand_kit)
        secondary = _pal(palette, "secondaryAccent")
        text_pri = _pal(palette, "textPrimary")
        accent = _pal(palette, "primaryAccent")

        _, ph = _draw_pill(canvas, width, height, 56, header_h + 50, "PRATICA | 3/4", 4, secondary, text_pri)
        ly = header_h + 50 + ph + 34
        _draw_text(canvas, width, height, 56, ly, "3 ITENS DA PRATICA", 6, accent)
        ly += carousel_layout.char_height(6) + 34
        for item in copy["pratica_items"]:
            _draw_text(canvas, width, height, 56, ly, "- " + item, 4, text_pri)
            ly += carousel_layout.char_height(4) + 18

    return {"kit": "carousel", "name": "slide-03-pratica.png", "texts": texts, "render": render}


def _carousel_04_spec(brand_kit: dict, copy: dict) -> dict:
    palette = _brand_palette(brand_kit)
    checklist = [
        "ESCOLHA O SERVICO OU PROJETO",
        "CONFIRME O HORARIO OU A COTA",
        "ACOMPANHE NA AGENDA OU NA GRADE",
    ]
    texts = [
        ("carousel-04 badge", "RESUMO | 4/4"),
        ("carousel-04 titulo", "RESUMO E PROXIMO PASSO"),
    ]
    for item in checklist:
        texts.append((f"carousel-04 checklist: {item[:20]}", item))
    texts.append(("carousel-04 cta", copy["cta"]))
    texts.append(("carousel-04 dominio", copy["domain"]))
    texts.append(("carousel-04 rodape", "CARROSSEL RETRATO 4:5 - SEM AUDIO"))

    def render(canvas, width, height):
        header_h = _draw_brand_header(canvas, width, height, brand_kit)
        secondary = _pal(palette, "secondaryAccent")
        text_pri = _pal(palette, "textPrimary")
        text_mut = _pal(palette, "textMuted")
        accent = _pal(palette, "primaryAccent")

        _, ph = _draw_pill(canvas, width, height, 56, header_h + 50, "RESUMO | 4/4", 4, secondary, text_pri)
        ly = header_h + 50 + ph + 34
        _draw_text(canvas, width, height, 56, ly, "RESUMO E PROXIMO PASSO", 6, accent)
        ly += carousel_layout.char_height(6) + 34
        for item in checklist:
            _stroke_rect(canvas, width, height, 84, ly, 116, ly + 26, 2, accent)
            _draw_text(canvas, width, height, 132, ly + 4, item, 3, text_pri)
            ly += 52
        cy = height - 210
        tw = _text_width(copy["cta"], 6)
        _draw_text(canvas, width, height, (width - tw) // 2, cy, copy["cta"], 6, accent)
        _draw_text(canvas, width, height, 84, cy + 52, copy["domain"], 5, accent)
        _draw_text(canvas, width, height, 84, cy + 92, "CARROSSEL RETRATO 4:5 - SEM AUDIO", 2, text_mut)

    return {"kit": "carousel", "name": "slide-04-resumo-cta.png", "texts": texts, "render": render}


def _blade_specs(brand_kit: dict, copy: dict, kinds: list[str]) -> list[dict]:
    specs: list[dict] = []
    route_label = copy["route_lines"][0] if copy["route_lines"] else None
    if KIT_STORIES in kinds:
        specs.append(_story_01_spec(brand_kit, copy, route_label))
        specs.append(_story_02_spec(brand_kit, copy))
        specs.append(_story_03_spec(brand_kit, copy))
    if KIT_CAROUSEL in kinds:
        specs.append(_carousel_01_spec(brand_kit, copy))
        specs.append(_carousel_02_spec(brand_kit, copy))
        specs.append(_carousel_03_spec(brand_kit, copy))
        specs.append(_carousel_04_spec(brand_kit, copy))
    return specs


# ---------------------------------------------------------------------------
# Geração de uma campanha
# ---------------------------------------------------------------------------
def _generate_one(root: str, tenant_id: str, slug: str, config: dict,
                  brand_kit: dict, guardrails: dict, fixture: dict,
                  kinds: list[str]) -> dict:
    delivery_dir = os.path.join(root, DELIVERIES_REL, tenant_id, slug)
    narr_path = os.path.join(root, NARRATION_REL, tenant_id, slug, f"{slug}_narracao.txt")
    narration_text = ""
    if os.path.isfile(render_local.fs_path(narr_path)):
        with open(render_local.fs_path(narr_path), "r", encoding="utf-8") as handle:
            narration_text = handle.read()

    copy = _build_copy(config, brand_kit, guardrails, fixture, narration_text)
    specs = _blade_specs(brand_kit, copy, kinds)

    # Auditoria obrigatoria de guardrails ANTES de renderizar qualquer pixel.
    audit_texts: list[tuple[str, str]] = []
    for spec in specs:
        audit_texts.extend(spec["texts"])
    violations = _audit_texts(audit_texts, guardrails)
    if violations:
        raise StaticCardsError(GUARDRAIL_VIOLACAO, violations)

    palette = _brand_palette(brand_kit)
    bg_top = _pal(palette, "backgroundTop")
    bg_bot = _pal(palette, "backgroundBottom")

    rendered: dict[str, list[dict[str, Any]]] = {KIT_STORIES: [], KIT_CAROUSEL: []}
    for spec in specs:
        width, height = KIT_SIZES[spec["kit"]]
        canvas = _base_gradient(width, height, bg_top, bg_bot)
        spec["render"](canvas, width, height)

        abs_dir = os.path.join(delivery_dir, spec["kit"])
        os.makedirs(render_local.fs_path(abs_dir), exist_ok=True)
        abs_path = os.path.join(abs_dir, spec["name"])
        data = _emit_png_file(abs_path, width, height, canvas)

        dw, dh = _png_dimensions(data)
        if (dw, dh) != (width, height):
            raise StaticCardsError("PNG_DIMENSAO",
                                   [f"{spec['name']} gerado com {dw}x{dh}, esperado {width}x{height}"])

        rendered[spec["kit"]].append({
            "name": spec["name"],
            "path": render_local.rel(root, abs_path),
            "width": width,
            "height": height,
            "bytes": len(data),
            "sha256": _sha256_bytes(data),
        })

    manifest = {
        "schemaVersion": 1,
        "tenantId": tenant_id,
        "slug": slug,
        "guardrailsAudited": True,
        "kits": {
            KIT_STORIES: {
                "size": f"{STORY_W}x{STORY_H}",
                "count": len(rendered[KIT_STORIES]),
                "items": rendered[KIT_STORIES],
            },
            KIT_CAROUSEL: {
                "size": f"{CAROUSEL_W}x{CAROUSEL_H}",
                "count": len(rendered[KIT_CAROUSEL]),
                "items": rendered[KIT_CAROUSEL],
            },
        },
    }
    manifest_path = os.path.join(delivery_dir, "static-manifest.json")
    _write_text_lf(manifest_path,
                   json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    return {
        "slug": slug,
        "manifest": render_local.rel(root, manifest_path),
        "kits": {
            KIT_STORIES: {"size": f"{STORY_W}x{STORY_H}", "count": len(rendered[KIT_STORIES])},
            KIT_CAROUSEL: {"size": f"{CAROUSEL_W}x{CAROUSEL_H}", "count": len(rendered[KIT_CAROUSEL])},
        },
    }


def generate_campaign_static_cards(tenant_id: str, slug: str | None = None,
                                   root: str | None = None,
                                   kinds: list[str] | None = None) -> dict:
    """Gera os kits estaticos de uma (ou todas as) campanha(s) de um tenant."""
    root_real = os.path.realpath(root or _repo_root())
    kinds = kinds or [KIT_STORIES, KIT_CAROUSEL]
    ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=root_real, strict=True)
    brand_kit = ctx["brandKit"]
    guardrails = ctx["guardrails"]
    fixture = ctx["fixture"]

    campaigns_dir = os.path.join(root_real, "tenants", tenant_id, "campaigns")
    targets: list[tuple[str, dict]] = []
    for fname in sorted(os.listdir(render_local.fs_path(campaigns_dir))):
        if not fname.endswith(".json"):
            continue
        cfg = _load_json(os.path.join(campaigns_dir, fname))
        cfg_slug = str(cfg.get("id") or fname[:-5])
        if slug is not None and cfg_slug != slug:
            continue
        targets.append((cfg_slug, cfg))
    if not targets:
        alvo = f"campanha '{slug}'" if slug else "nenhuma campanha"
        raise StaticCardsError("CAMPAIGN_NOT_FOUND",
                               [f"tenant '{tenant_id}': {alvo} nao encontrado em tenants/{tenant_id}/campaigns/"])

    results = []
    for cfg_slug, cfg in targets:
        results.append(_generate_one(root_real, tenant_id, cfg_slug, cfg,
                                     brand_kit, guardrails, fixture, kinds))
    return {"tenantId": tenant_id, "slug": slug, "campaigns": results}


def generate_all_static_cards(root: str | None = None,
                              kinds: list[str] | None = None) -> dict:
    """Gera todos os kits estaticos de todos os tenants (8 campanhas x 7 laminas)."""
    root_real = os.path.realpath(root or _repo_root())
    tenants = tenant_validator.list_tenants(root_real)
    out: dict[str, Any] = {"tenants": []}
    for tid in tenants:
        out["tenants"].append(generate_campaign_static_cards(tid, None, root_real, kinds))
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Motor programatico de cards estaticos (stories 1080x1920 e carrossel 1080x1350) - Agente 1 Etapa 5"
    )
    parser.add_argument("--all", action="store_true", help="processa todas as campanhas de todos os tenants")
    parser.add_argument("--tenant", help="slug do tenant (marca-salao, meu-salao, estudio-flow, multitrack-hub)")
    parser.add_argument("--campaign", help="slug/id da campanha (ignorado sem --tenant)")
    parser.add_argument("--types", default="stories,carousel",
                        help="tipos de kit a gerar (stories,carousel)")
    parser.add_argument("--root", default=_repo_root(), help="raiz do checkout")
    parser.add_argument("--json", action="store_true", help="emite resumo em JSON no stdout")
    args = parser.parse_args(argv)

    kinds = [t.strip() for t in str(args.types).split(",") if t.strip()]
    for k in kinds:
        if k not in KIT_SIZES:
            print(f"Erro: tipo de kit invalido '{k}' (validos: {list(KIT_SIZES)})", file=sys.stderr)
            return 2

    root_real = os.path.realpath(args.root)
    try:
        if args.all:
            summary = generate_all_static_cards(root_real, kinds)
        elif args.tenant:
            summary = {"tenantId": args.tenant,
                       "campaigns": [generate_campaign_static_cards(args.tenant, args.campaign, root_real, kinds)]}
        else:
            print("Erro: informe --all ou --tenant <id> [--campaign <slug>]", file=sys.stderr)
            return 2
    except StaticCardsError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except tenant_validator.TenantContractError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"Erro: entrada invalida ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        total = sum(len(t.get("campaigns", [])) for t in summary.get("tenants", []))
        print(f"Cards estaticos gerados: {total} campanha(s), kits {','.join(kinds)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
