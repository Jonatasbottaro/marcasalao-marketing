"""Auditoria transversal de qualidade editorial da fabrica multi-tenant.

Criada na Etapa 5B (Agente 8) e estendida na Etapa 6 (Agente 7) com duas lentes
de coerencia editorial. Varre TODAS as campanhas descobertas em
``tenants/*/campaigns/*.json`` e cruza sete lentes de qualidade, independentes
da renderizacao e 100% stdlib:

  1. ``duracao_srt_manifest``  - o ultimo cue do SRT termina na duracao final
     declarada no ``manifest.json`` (padrao 30.0s, tolerancia de 1 ms), e o SRT
     e estruturalmente valido (reutiliza ``srt_validate``).
  2. ``legibilidade_mobile``   - nenhuma linha de texto de um cue excede 48
     caracteres e nenhum bloco esta vazio. Linha longa e AVISO de legibilidade
     (reprova com ``--strict``); bloco vazio e erro.
  3. ``paridade_entregas``     - presenca e identidade (tenantId/slug) cruzadas
     entre video (``02-reels-shorts/deliveries/``), cards estaticos
     (``01-insta-stories/deliveries/<tenant>/<slug>/static-manifest.json``,
     quando presente) e pacote social (``04-legendas/pacotes-publicacao/``).
  4. ``guardrails_cruzados``   - re-auditoria de ``forbiddenClaims`` /
     ``forbiddenUiElements`` via ``tenant_validator`` sobre SRT, narracao e as
     tres legendas sociais.
  5. ``integridade_utf8``      - nenhum arquivo UTF-8 auditado contem U+FFFD ou
     sequencias tipicas de mojibake (dupla decodificacao Latin-1/CP1252).
   6. ``coerencia_hooks_calendario`` - quando ``04-legendas/calendario-editorial.json``
      existe, cada campanha agendada tem ``hookVarianteA`` e ``hookVarianteB``
      nao vazios, distintos e livres de violacoes de guardrails do tenant.
      Variantes identicas sao AVISO; ausencia/violacao e erro.
   7. ``aderencia_ui_labels``   - quando ``brand-kit.json`` define ``uiLabels``,
      todos os valores sao strings nao vazias e passam em
      ``validate_text_against_guardrails`` com UI elements habilitados.

Severidades: ``error`` reprova sempre; ``warning`` so reprova com ``--strict``.
A ferramenta e somente leitura: nao grava, nao publica e nao agenda nada.

CLI:
    python tools/editorial_qa.py [--all | --tenant <id>] [--strict] [--json]
    python tools/editorial_qa.py --tenant marca-salao --strict --json

API:
    run_editorial_qa(root=".", strict=False, tenant=None) -> dict

Exit codes: 0 aprovado; 1 auditoria reprovada; 2 erro de uso/execucao.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import render_local
import srt_validate
import tenant_validator

# ---------------------------------------------------------------------------
# Constantes e contrato do relatorio
# ---------------------------------------------------------------------------
REPORT_SCHEMA_VERSION = 1
EXPECTED_DURATION = 30.0
DURATION_TOLERANCE = 0.001
MAX_LINE_CHARS = 48
LONG_LINE_SEVERITY = "warning"
CALENDAR_REL = ("04-legendas", "calendario-editorial.json")

DELIVERY_ROOT = ("02-reels-shorts", "deliveries")
STATIC_ROOT = ("01-insta-stories", "deliveries")
PACKAGE_ROOT = ("04-legendas", "pacotes-publicacao")
PACKAGE_FILES = ("instagram-reels.md", "youtube-shorts.md", "facebook-reels.md")
CHECKLIST_FILE = "checklist-publicacao.json"
STATIC_FILE = "static-manifest.json"

CHECK_IDS = (
    "duracao_srt_manifest",
    "legibilidade_mobile",
    "paridade_entregas",
    "guardrails_cruzados",
    "integridade_utf8",
    "coerencia_hooks_calendario",
    "aderencia_ui_labels",
)
CHECK_NAMES = {
    "duracao_srt_manifest": "Sincronismo SRT x Manifesto",
    "legibilidade_mobile": "Legibilidade Mobile do SRT",
    "paridade_entregas": "Paridade Video / Cards / Pacotes",
    "guardrails_cruzados": "Re-auditoria Cruzada de Guardrails",
    "integridade_utf8": "Integridade UTF-8 e Mojibake",
    "coerencia_hooks_calendario": "Coerencia dos Hooks A/B no Calendario",
    "aderencia_ui_labels": "Aderencia de uiLabels por Nicho",
}

# U+FFFD e o sinal primario. As demais sequencias sao o resultado classico de
# decodificar bytes UTF-8 como CP1252/Latin-1 (ex.: "Ã§" = "ç", "â€" = travessao).
# Evita-se o marcador isolado "Ã" porque ele e legitimo em textos ALL-CAPS como
# "AÇÃO"; apenas pares inequivocos entram na varredura.
MOJIBAKE_PATTERNS = (
    "\ufffd",
    "Ã¡", "Ã©", "Ãª", "Ã­", "Ã³", "Ãµ", "Ãº", "Ã§", "Ã£", "Ã±",
    "Ã\u00a0", "Â ", "Â©", "Â®", "Âº", "Âª",
    "â€", "â€™", "â€œ", "â€\u009d", "â‚¬",
)


class EditorialQAError(Exception):
    """Erro de execucao do auditor (raiz ausente, caminho fora da raiz)."""


# ---------------------------------------------------------------------------
# Helpers de baixo nivel
# ---------------------------------------------------------------------------
def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _rel(root_real: str, rel_path: str) -> str:
    return os.path.join(root_real, *str(rel_path).replace("\\", "/").split("/"))


def _problem(code: str, message: str, label: str, severity: str = "error") -> dict:
    return {
        "severity": severity,
        "code": code,
        "message": f"{label}: {message}",
    }


def _read_text(path: str) -> tuple[str | None, str | None]:
    """Le UTF-8 estrito. Devolve (texto, mensagem_de_erro)."""
    try:
        with open(render_local.fs_path(path), "r", encoding="utf-8", newline="") as handle:
            return handle.read(), None
    except UnicodeDecodeError as exc:
        return None, f"UTF-8 invalido ({exc})"
    except OSError as exc:
        return None, f"leitura falhou ({exc})"


def _read_json(path: str) -> tuple[dict | None, str | None]:
    text, error = _read_text(path)
    if error:
        return None, error
    try:
        data = json.loads(text)
    except ValueError as exc:
        return None, f"JSON invalido ({exc})"
    if not isinstance(data, dict):
        return None, "JSON nao e um objeto"
    return data, None


def _srt_cues(text: str) -> tuple[list[dict], list[str]]:
    """Extrai cues {index, body_lines, empty} e os fins de cada bloco."""
    cues: list[dict] = []
    ends: list[float] = []
    for block in re.split(r"\n\s*\n", text.strip("\n")):
        lines = block.split("\n")
        body_lines = [line.strip() for line in lines[2:] if line.strip()]
        cues.append(
            {
                "index": lines[0].strip() if lines else "",
                "body_lines": body_lines,
                "empty": not body_lines,
            }
        )
        if len(lines) >= 2:
            match = srt_validate.TIMESTAMP_LINE_RE.match(lines[1].strip())
            if match:
                end = srt_validate.parse_timestamp(match.group(2))
                if end is not None:
                    ends.append(end)
    return cues, ends


# ---------------------------------------------------------------------------
# Coleta unica por campanha (evita releituras entre as cinco lentes)
# ---------------------------------------------------------------------------
def _collect_campaign(root_real: str, tenant: str, slug: str) -> dict:
    delivery_dir = _rel(root_real, "/".join(DELIVERY_ROOT + (tenant, slug)))
    static_dir = _rel(root_real, "/".join(STATIC_ROOT + (tenant, slug)))
    package_dir = _rel(root_real, "/".join(PACKAGE_ROOT + (tenant, slug)))

    ctx: dict = {
        "tenant": tenant,
        "slug": slug,
        "label": f"{tenant}/{slug}",
        "delivery_dir": delivery_dir,
        "static_dir": static_dir,
        "package_dir": package_dir,
        "manifest_path": os.path.join(delivery_dir, "manifest.json"),
        "srt_path": os.path.join(delivery_dir, f"{slug}.srt"),
        "narration_path": os.path.join(delivery_dir, f"{slug}_narracao.txt"),
        "static_path": os.path.join(static_dir, STATIC_FILE),
        "checklist_path": os.path.join(package_dir, CHECKLIST_FILE),
        "manifest": None,
        "srt_text": None,
        "narration_text": None,
        "static": None,
        "checklist": None,
        "social_texts": {},
        "audited_files": [],
        "guardrails": None,
        "problems": {check_id: [] for check_id in CHECK_IDS},
    }

    # Arquivos que entram na varredura de integridade UTF-8.
    candidates = [
        ctx["manifest_path"],
        ctx["srt_path"],
        ctx["narration_path"],
        ctx["static_path"],
        ctx["checklist_path"],
        os.path.join(root_real, "tenants", tenant, "brand-kit.json"),
        os.path.join(root_real, "tenants", tenant, "guardrails.json"),
        os.path.join(root_real, "tenants", tenant, "campaigns", f"{slug}.json"),
    ]
    candidates.extend(
        os.path.join(package_dir, name)
        for name in PACKAGE_FILES
    )
    for path in candidates:
        if os.path.isfile(render_local.fs_path(path)):
            ctx["audited_files"].append((render_local.rel(root_real, path), path))

    # JSONs estruturais
    for key, path in (
        ("manifest", ctx["manifest_path"]),
        ("static", ctx["static_path"]),
        ("checklist", ctx["checklist_path"]),
    ):
        data, error = _read_json(path)
        if error:
            ctx["problems"]["paridade_entregas"].append(
                _problem("ARQUIVO_ILEGIVEL", f"{os.path.basename(path)}: {error}", ctx["label"])
            )
        else:
            ctx[key] = data

    # Textos
    for key, path in (
        ("srt_text", ctx["srt_path"]),
        ("narration_text", ctx["narration_path"]),
    ):
        text, error = _read_text(path)
        if error:
            ctx["problems"]["integridade_utf8"].append(
                _problem("UTF8_INVALIDO", f"{os.path.basename(path)}: {error}", ctx["label"])
            )
        else:
            ctx[key] = text

    for name in PACKAGE_FILES:
        text, error = _read_text(os.path.join(package_dir, name))
        if error:
            ctx["problems"]["integridade_utf8"].append(
                _problem("UTF8_INVALIDO", f"{name}: {error}", ctx["label"])
            )
        else:
            ctx["social_texts"][name] = text

    # Guardrails do tenant (strict=False para continuarelatorio mesmo com erro)
    try:
        ctx["guardrails"] = tenant_validator.load_and_validate_tenant(
            tenant, root=root_real, strict=False
        )["guardrails"]
    except tenant_validator.TenantContractError as exc:
        ctx["problems"]["guardrails_cruzados"].append(
            _problem("TENANT_INVALIDO", f"{exc}", ctx["label"])
        )

    return ctx


# ---------------------------------------------------------------------------
# Lente 1 - duracao final do SRT x manifesto
# ---------------------------------------------------------------------------
def _check_duration(ctx: dict) -> None:
    label = ctx["label"]
    problems = ctx["problems"]["duracao_srt_manifest"]
    manifest = ctx["manifest"]

    if manifest is None:
        problems.append(_problem("MANIFEST_AUSENTE", "manifest.json nao legivel", label))
    else:
        duration = (manifest.get("format") or {}).get("duration")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool):
            problems.append(
                _problem("MANIFEST_DURACAO_AUSENTE", "format.duration ausente ou invalido", label)
            )

    if ctx["srt_text"] is None:
        problems.append(_problem("SRT_AUSENTE", "SRT nao legivel", label))
        return

    text = ctx["srt_text"]
    # Erros estruturais de SRT (SRT_TEXT_EMPTY e tratado pela lente de legibilidade).
    for message in srt_validate.validate_srt_text(text):
        if message.startswith("SRT_TEXT_EMPTY"):
            continue
        code = message.split(":", 1)[0]
        problems.append(_problem(code, message, label))

    _cues, ends = _srt_cues(text)
    if not ends:
        problems.append(_problem("SRT_SEM_CUES", "nenhum cue com intervalo valido", label))
        return

    expected = duration if isinstance(duration, (int, float)) and not isinstance(duration, bool) else EXPECTED_DURATION
    final_end = max(ends)
    if abs(final_end - float(expected)) > DURATION_TOLERANCE:
        problems.append(
            _problem(
                "SRT_DURACAO_DIVERGENTE",
                f"ultimo cue termina em {final_end:.3f}s, manifesto declara {float(expected):.3f}s",
                label,
            )
        )


# ---------------------------------------------------------------------------
# Lente 2 - legibilidade mobile
# ---------------------------------------------------------------------------
def _check_legibility(ctx: dict) -> None:
    if ctx["srt_text"] is None:
        return
    label = ctx["label"]
    problems = ctx["problems"]["legibilidade_mobile"]
    cues, _ends = _srt_cues(ctx["srt_text"])

    for cue in cues:
        if cue["empty"]:
            problems.append(
                _problem("SRT_BLOCO_VAZIO", f"bloco {cue['index']} sem texto", label)
            )
        for line in cue["body_lines"]:
            if len(line) > MAX_LINE_CHARS:
                problems.append(
                    _problem(
                        "SRT_LINHA_LONGA",
                        f"bloco {cue['index']}: linha com {len(line)} caracteres "
                        f"(limite {MAX_LINE_CHARS})",
                        label,
                        severity=LONG_LINE_SEVERITY,
                    )
                )


# ---------------------------------------------------------------------------
# Lente 3 - paridade entre as tres superficies de entrega
# ---------------------------------------------------------------------------
def _check_identity(data: dict | None, label: str, surface: str, tenant: str, slug: str,
                    problems: list, file_name: str) -> None:
    if data is None:
        return
    found_tenant = data.get("tenantId")
    found_slug = data.get("slug")
    if found_tenant and found_tenant != tenant:
        problems.append(
            _problem("PARIDADE_TENANT_DIVERGENTE",
                     f"{surface}: tenantId '{found_tenant}' != '{tenant}'", label)
        )
    if found_slug and found_slug != slug:
        problems.append(
            _problem("PARIDADE_SLUG_DIVERGENTE",
                     f"{surface}: slug '{found_slug}' != '{slug}'", label)
        )


def _check_parity(ctx: dict) -> None:
    label = ctx["label"]
    problems = ctx["problems"]["paridade_entregas"]
    tenant, slug = ctx["tenant"], ctx["slug"]

    # Video: presenca do diretorio e dos tres artefatos versionados.
    if not os.path.isdir(render_local.fs_path(ctx["delivery_dir"])):
        problems.append(_problem("ENTREGA_AUSENTE", "diretorio de entrega ausente", label))
    for name, path, code in (
        ("SRT", ctx["srt_path"], "ENTREGA_SRT_AUSENTE"),
        ("narracao", ctx["narration_path"], "ENTREGA_NARRACAO_AUSENTE"),
    ):
        if not os.path.isfile(render_local.fs_path(path)):
            problems.append(_problem(code, f"{name} ausente na entrega de video", label))
    _check_identity(ctx["manifest"], label, "manifesto", tenant, slug, problems, "manifest.json")

    # Cards estaticos: "quando presente" - ausencia e aviso, nao erro.
    if not os.path.isfile(render_local.fs_path(ctx["static_path"])):
        problems.append(
            _problem("CARDS_ESTATICOS_AUSENTE", "static-manifest.json nao encontrado",
                     label, severity="warning")
        )
    else:
        _check_identity(ctx["static"], label, "cards estaticos", tenant, slug, problems, STATIC_FILE)
        if ctx["static"] is not None and ctx["static"].get("guardrailsAudited") is not True:
            problems.append(
                _problem("CARDS_SEM_AUDITORIA", "static-manifest.json sem guardrailsAudited=true", label)
            )

    # Pacote social: checklist + tres textos por rede.
    checklist_path = ctx["checklist_path"]
    if not os.path.isfile(render_local.fs_path(checklist_path)):
        problems.append(
            _problem("PACOTE_SOCIAL_AUSENTE", f"{CHECKLIST_FILE} nao encontrado", label)
        )
    else:
        _check_identity(ctx["checklist"], label, "pacote social", tenant, slug, problems, CHECKLIST_FILE)
        if ctx["checklist"] is not None:
            if ctx["checklist"].get("autoPublish") is not False:
                problems.append(
                    _problem("PARIDADE_AUTO_PUBLICACAO", "checklist autoPublish deve ser false", label)
                )
            if ctx["checklist"].get("guardrailsAudited") is not True:
                problems.append(
                    _problem("PARIDADE_GUARDRAILS_NAO_AUDITADOS",
                             "checklist guardrailsAudited deve ser true", label)
                )
    for name in PACKAGE_FILES:
        if name not in ctx["social_texts"]:
            problems.append(
                _problem("PACOTE_ARQUIVO_AUSENTE", f"{name} ausente no pacote social", label)
            )


# ---------------------------------------------------------------------------
# Lente 4 - re-auditoria cruzada de guardrails
# ---------------------------------------------------------------------------
def _check_guardrails(ctx: dict) -> None:
    guardrails = ctx["guardrails"]
    if guardrails is None:
        return
    problems = ctx["problems"]["guardrails_cruzados"]
    label = ctx["label"]
    sources = [("srt", ctx["srt_text"]), ("narracao", ctx["narration_text"])]
    sources.extend(ctx["social_texts"].items())
    for source, text in sources:
        if not text:
            continue
        for violation in tenant_validator.validate_text_against_guardrails(
            text, guardrails, check_ui_elements=True
        ):
            problems.append(
                _problem("GUARDRAIL_VIOLACAO", f"{source}: {violation}", label)
            )


# ---------------------------------------------------------------------------
# Lente 5 - integridade UTF-8 / mojibake
# ---------------------------------------------------------------------------
def _check_utf8(ctx: dict) -> None:
    problems = ctx["problems"]["integridade_utf8"]
    label = ctx["label"]
    for rel_path, path in ctx["audited_files"]:
        text, error = _read_text(path)
        if error:
            problems.append(_problem("UTF8_INVALIDO", f"{rel_path}: {error}", label))
            continue
        for pattern in MOJIBAKE_PATTERNS:
            if pattern in text:
                problems.append(
                    _problem("MOJIBAKE_DETECTADO", f"{rel_path}: sequencia {pattern!r}", label)
                )


# ---------------------------------------------------------------------------
# Lente 6 - coerencia dos hooks A/B no calendario editorial
# ---------------------------------------------------------------------------
def _tenant_guardrails(root_real: str, tenant: str, cache: dict) -> tuple[dict | None, str | None]:
    """Guardrails de um tenant, com cache por execucao de auditoria."""
    if tenant not in cache:
        try:
            guardrails = tenant_validator.load_and_validate_tenant(
                tenant, root=root_real, strict=False
            )["guardrails"]
            cache[tenant] = (guardrails, None)
        except tenant_validator.TenantContractError as exc:
            cache[tenant] = (None, str(exc))
    return cache[tenant]


def _check_calendar_hooks(root_real: str, tenant_filter: str | None, cache: dict) -> list[dict]:
    """Compara hookVarianteA/B de cada campanha agendada com os guardrails do tenant."""
    problems: list[dict] = []
    calendar_path = _rel(root_real, "/".join(CALENDAR_REL))
    if not os.path.isfile(render_local.fs_path(calendar_path)):
        return problems
    calendar, error = _read_json(calendar_path)
    if error or calendar is None:
        problems.append(
            _problem(
                "CALENDARIO_ILEGIVEL",
                f"{'/'.join(CALENDAR_REL)}: {error or 'JSON invalido'}",
                "calendario-editorial",
            )
        )
        return problems

    seen: set[tuple[str, str, str]] = set()
    for slot in calendar.get("slots", []) or []:
        if not isinstance(slot, dict):
            continue
        tenant = str(slot.get("tenantId") or "")
        slug = str(slot.get("slug") or "")
        if not tenant or not slug:
            continue
        if tenant_filter is not None and tenant != tenant_filter:
            continue
        label = f"{tenant}/{slug}"

        def add(code: str, message: str, severity: str = "error") -> None:
            key = (label, code, message)
            if key not in seen:
                seen.add(key)
                problems.append(_problem(code, message, label, severity=severity))

        guardrails, tenant_error = _tenant_guardrails(root_real, tenant, cache)
        if tenant_error:
            add("TENANT_INVALIDO", tenant_error)
            continue

        variants: dict[str, str] = {}
        for field_name in ("hookVarianteA", "hookVarianteB"):
            value = slot.get(field_name)
            text = value.strip() if isinstance(value, str) else ""
            variants[field_name] = text
            if not text:
                add("HOOK_VARIANTE_AUSENTE", f"{field_name} ausente ou vazio")
                continue
            for violation in tenant_validator.validate_text_against_guardrails(
                text, guardrails, check_ui_elements=True
            ):
                add("HOOK_GUARDRAIL_VIOLACAO", f"{field_name}: {violation}")

        hook_a = variants.get("hookVarianteA", "")
        hook_b = variants.get("hookVarianteB", "")
        if hook_a and hook_b and hook_a.casefold() == hook_b.casefold():
            add(
                "HOOK_VARIANTES_IDENTICAS",
                "hookVarianteA e hookVarianteB sao identicos",
                severity="warning",
            )
    return problems


# ---------------------------------------------------------------------------
# Lente 7 - aderencia de uiLabels por nicho
# ---------------------------------------------------------------------------
def _check_ui_labels(root_real: str, tenant_filter: str | None, cache: dict) -> list[dict]:
    """Valora os rotulos de UI declarados no brand-kit, quando existirem."""
    problems: list[dict] = []
    tenants_fs = render_local.fs_path(os.path.join(root_real, "tenants"))
    if not os.path.isdir(tenants_fs):
        return problems

    for tenant in sorted(os.listdir(tenants_fs)):
        if tenant_filter is not None and tenant != tenant_filter:
            continue
        kit_path = os.path.join(tenants_fs, tenant, "brand-kit.json")
        if not os.path.isfile(render_local.fs_path(kit_path)):
            continue
        kit, error = _read_json(kit_path)
        if error or kit is None or "uiLabels" not in kit:
            continue

        label = f"{tenant}/brand-kit.json"
        ui_labels = kit["uiLabels"]
        if not isinstance(ui_labels, dict):
            problems.append(
                _problem("UI_LABELS_TIPO_INVALIDO", "uiLabels deve ser um objeto", label)
            )
            continue
        guardrails, tenant_error = _tenant_guardrails(root_real, tenant, cache)
        if tenant_error:
            problems.append(_problem("TENANT_INVALIDO", tenant_error, label))
            continue

        def walk(node: object, path: str) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    walk(value, f"{path}.{key}" if path else str(key))
                return
            if isinstance(node, (list, tuple)):
                for index, value in enumerate(node):
                    walk(value, f"{path}[{index}]")
                return
            if not isinstance(node, str):
                problems.append(
                    _problem("UI_LABEL_TIPO_INVALIDO", f"{path}: valor nao e string", label)
                )
                return
            text = node.strip()
            if not text:
                problems.append(_problem("UI_LABEL_VAZIA", f"{path}: valor vazio", label))
                return
            for violation in tenant_validator.validate_text_against_guardrails(
                text, guardrails, check_ui_elements=True
            ):
                problems.append(
                    _problem("UI_LABEL_GUARDRAIL_VIOLACAO", f"{path}: {violation}", label)
                )

        walk(ui_labels, "uiLabels")
    return problems


# ---------------------------------------------------------------------------
# Orquestracao e relatorio
# ---------------------------------------------------------------------------
def discover_campaigns(root_real: str, tenant: str | None = None) -> list[dict]:
    """Descobre campanhas em tenants/*/campaigns/*.json, opcionalmente filtradas."""
    campaigns: list[dict] = []
    tenants_fs = render_local.fs_path(os.path.join(root_real, "tenants"))
    if not os.path.isdir(tenants_fs):
        return campaigns
    for tenant_id in sorted(os.listdir(tenants_fs)):
        if tenant is not None and tenant_id != tenant:
            continue
        campaigns_fs = render_local.fs_path(
            os.path.join(root_real, "tenants", tenant_id, "campaigns")
        )
        if not os.path.isdir(campaigns_fs):
            continue
        for name in sorted(os.listdir(campaigns_fs)):
            if name.endswith(".json"):
                campaigns.append({"tenant": tenant_id, "slug": name[: -len(".json")]})
    return campaigns


def _status(problems: list[dict], strict: bool) -> tuple[bool, str]:
    has_error = any(p["severity"] == "error" for p in problems)
    has_warning = any(p["severity"] == "warning" for p in problems)
    ok = not has_error and not (strict and has_warning)
    status = "fail" if has_error else "warn" if has_warning else "ok"
    return ok, status


def run_editorial_qa(root: str = ".", strict: bool = False,
                     tenant: str | None = None) -> dict:
    """Executa as sete lentes editoriais e devolve o relatorio schemaVersion 1."""
    root_real = os.path.realpath(root)
    if not os.path.isdir(render_local.fs_path(root_real)):
        raise EditorialQAError(f"raiz ausente: {root_real}")

    campaigns = discover_campaigns(root_real, tenant=tenant)
    per_check: dict[str, list[dict]] = {check_id: [] for check_id in CHECK_IDS}
    campaign_rows: list[dict] = []

    for campaign in campaigns:
        ctx = _collect_campaign(root_real, campaign["tenant"], campaign["slug"])
        _check_duration(ctx)
        _check_legibility(ctx)
        _check_parity(ctx)
        _check_guardrails(ctx)
        _check_utf8(ctx)

        for check_id in CHECK_IDS:
            per_check[check_id].extend(ctx["problems"][check_id])
        count = sum(len(problems) for problems in ctx["problems"].values())
        campaign_rows.append(
            {
                "tenant": campaign["tenant"],
                "slug": campaign["slug"],
                "problems": count,
                "ok": count == 0,
            }
        )

    # Lentes 6 e 7: escopo de calendario e de brand-kit (nao por campanha).
    guardrails_cache: dict[str, tuple[dict | None, str | None]] = {}
    per_check["coerencia_hooks_calendario"].extend(
        _check_calendar_hooks(root_real, tenant, guardrails_cache)
    )
    per_check["aderencia_ui_labels"].extend(
        _check_ui_labels(root_real, tenant, guardrails_cache)
    )

    check_rows = []
    for check_id in CHECK_IDS:
        problems = per_check[check_id]
        ok, status = _status(problems, strict)
        check_rows.append(
            {
                "id": check_id,
                "name": CHECK_NAMES[check_id],
                "ok": ok,
                "status": status,
                "problems": problems,
            }
        )

    all_problems = [p for problems in per_check.values() for p in problems]
    errors = sum(1 for p in all_problems if p["severity"] == "error")
    warnings = sum(1 for p in all_problems if p["severity"] == "warning")
    ok = errors == 0 and not (strict and warnings > 0)

    return {
        "schemaVersion": REPORT_SCHEMA_VERSION,
        "ok": ok,
        "strict": strict,
        "root": root_real,
        "tenantFilter": tenant,
        "campaigns": campaign_rows,
        "checks": check_rows,
        "summary": {
            "campaigns": {
                "total": len(campaign_rows),
                "withProblems": sum(1 for row in campaign_rows if not row["ok"]),
            },
            "checks": {
                "ok": sum(1 for row in check_rows if row["status"] == "ok"),
                "warn": sum(1 for row in check_rows if row["status"] == "warn"),
                "fail": sum(1 for row in check_rows if row["status"] == "fail"),
            },
            "problems": {"errors": errors, "warnings": warnings},
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _stdout_utf8() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


def _print_human(result: dict) -> None:
    labels = {"ok": "OK", "warn": "AVISO", "fail": "FALHA"}
    for check in result["checks"]:
        print(f"[{labels[check['status']]}] {check['id']} - {check['name']}")
        for problem in check["problems"]:
            print(f"    - [{problem['severity']}] {problem['code']}: {problem['message']}")
    summary = result["summary"]
    print()
    print(
        f"Campanhas: {summary['campaigns']['total']} "
        f"({summary['campaigns']['withProblems']} com observacoes)"
    )
    print(
        f"Verificacoes: {summary['checks']['ok']} ok, {summary['checks']['warn']} aviso(s), "
        f"{summary['checks']['fail']} falha(s)"
    )
    print(
        f"Problemas: {summary['problems']['errors']} erro(s), "
        f"{summary['problems']['warnings']} aviso(s)"
    )
    mode = " (strict)" if result["strict"] else ""
    print(f"Resultado{mode}: {'APROVADO' if result['ok'] else 'REPROVADO'}")


def main(argv: list[str] | None = None) -> int:
    _stdout_utf8()
    parser = argparse.ArgumentParser(
        description="Auditoria transversal de qualidade editorial (7 lentes, 100% stdlib)"
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--all", action="store_true", help="audita todas as campanhas (padrao)")
    selection.add_argument("--tenant", help="restrige a auditoria a um tenant")
    parser.add_argument(
        "--strict", action="store_true", help="avisos (ex.: linha de SRT longa) tambem reprovam"
    )
    parser.add_argument("--json", action="store_true", help="emite o relatorio em JSON no stdout")
    parser.add_argument("--root", default=_repo_root(), help="raiz do checkout")
    args = parser.parse_args(argv)

    try:
        result = run_editorial_qa(
            root=os.path.realpath(os.path.abspath(args.root)),
            strict=args.strict,
            tenant=args.tenant,
        )
    except EditorialQAError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Erro: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
