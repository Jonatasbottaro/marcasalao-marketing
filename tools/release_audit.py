"""Auditor final de prontidao de release da fabrica de video (7 dominios).

Verifica, em uma unica passada, o estado de prontidao de release do checkout,
organizado nos 7 dominios da Etapa 4:

  1. contratos_tenants       brand-kit, guardrails e fixture de >= 4 tenants,
                             validados por tenant_validator.
  2. entregas_video          manifest.json e artefatos versionados de cada
                             campanha (<slug>.srt, <slug>_narracao.txt,
                             preview-storyboard.png) com SHA-256/bytes conferidos
                             em disco, e politica de audio do manifesto
                             (guardrails.allowAudioTrack vs ffprobe.audioStreams).
  3. pacotes_sociais         textos por rede e checklist-publicacao.json com
                             autoPublish false, guardrailsAudited true e hashes
                             das midias conferidos.
  4. derivados_multiformato  derivatives.json com declaracoes completas
                             (cover, 1x1, 16x9); derivado presente em disco
                             tem SHA-256 conferido.
  5. calendario_utm          calendario-editorial.json/.md (estrutura, contagem
                             de slots, autoPublish false) e
                             matriz-utm-consolidada.csv.
  6. portal_revisao          05-review-portal/ completo e sem caminhos absolutos
                             de estacao vazados no JSON/HTML.
  7. higiene_git             nenhuma midia binaria rastreada ou nao-ignorada,
                             nenhum snapshot .zip versionado, .gitattributes com
                             eol=lf para .json/.srt/.md/.html e worktrees
                             historicas preservadas.

Os dominios 2, 4 e 7 tambem cruzam os manifestos versionados com os binarios
locais em ``.workspace/archives/`` (SHA-256, metadados ffprobe e midias orfas),
usando a mesma logica de ``tools/workspace_doctor.py``.

Severidades: `error` reprova sempre; `warning` nao reprova no modo padrao e
reprova com `--strict`. Midia local da estacao (`<slug>.mp4` de entrega e
derivados sob `.workspace/archives/`) ausente em disco NAO gera problema: o
manifesto e a declaracao preservam hash, ffprobe e comando reproduzivel, e o
`.gitignore` cobre `*.mp4`. Quando o arquivo esta presente, o hash e conferido.

CLI: python tools/release_audit.py [--strict] [--json] [--report-out <arquivo>]
Exit codes: 0 aprovado; 1 auditoria reprovada; 2 erro de uso ou execucao.
"""

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import render_local
import tenant_validator
import workspace_doctor

import publish_bundler

MIN_VALID_TENANTS = 4
HISTORICAL_WORKTREES = ("prova-campanha-conclusao", "studio-package-verify2")
EXPECTED_ARTIFACTS = (
    ("srt", "{slug}.srt"),
    ("narration", "{slug}_narracao.txt"),
    ("storyboard", "preview-storyboard.png"),
)
VIDEO_NAME_TEMPLATE = "{slug}.mp4"
DELIVERY_ROOT = ("02-reels-shorts", "deliveries")
PACKAGE_ROOT = ("04-legendas", "pacotes-publicacao")
PACKAGE_FILES = ("instagram-reels.md", "youtube-shorts.md", "facebook-reels.md")
DERIVATIVE_KEYS = ("cover", "1x1", "16x9")
CALENDAR_JSON = ("04-legendas", "calendario-editorial.json")
CALENDAR_MD = ("04-legendas", "calendario-editorial.md")
MATRIZ_UTM = ("04-legendas", "matriz-utm-consolidada.csv")
PORTAL_DIR = "05-review-portal"
PORTAL_FILES = ("index.html", "portal-data.json", "README.md")
PORTAL_SCANNED_FILES = ("index.html", "portal-data.json")
GITATTRIBUTES_EXTENSIONS = (".json", ".srt", ".md", ".html")
# Lookbehind evita falso positivo em URLs ("https://" termina em "s:/").
ABSOLUTE_PATH_PATTERN = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[/\\]|/users/", re.IGNORECASE)

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


class ReleaseAuditError(Exception):
    """Erro de execucao do auditor (raiz ausente, git indisponivel, caminho)."""


def _error(code: str, message: str) -> dict:
    return {"severity": "error", "code": code, "message": message}


def _warning(code: str, message: str) -> dict:
    return {"severity": "warning", "code": code, "message": message}


def _has_error(problems: list[dict]) -> bool:
    return any(problem["severity"] == "error" for problem in problems)


def _domain(domain_id: str, name: str, problems: list[dict]) -> dict:
    has_error = _has_error(problems)
    has_warning = any(problem["severity"] == "warning" for problem in problems)
    return {
        "id": domain_id,
        "name": name,
        "ok": not has_error,
        "status": "fail" if has_error else "warn" if has_warning else "ok",
        "problems": problems,
    }


def _run_git(root: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", root, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise ReleaseAuditError(f"git {' '.join(args)} falhou: {proc.stderr.strip()}")
    return proc.stdout


def _read_json(path: str) -> dict:
    with open(render_local.fs_path(path), "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("conteudo JSON nao e um objeto")
    return data


def _join_rel(root_real: str, rel_path: str) -> str:
    return os.path.join(root_real, *rel_path.replace("\\", "/").split("/"))


def discover_campaigns(root_real: str) -> list[dict]:
    """Lista campanhas como pares {tenant, slug} a partir de tenants/*/campaigns/*.json."""
    campaigns: list[dict] = []
    tenants_fs = render_local.fs_path(os.path.join(root_real, "tenants"))
    if not os.path.isdir(tenants_fs):
        return campaigns
    for tenant in sorted(os.listdir(tenants_fs)):
        campaigns_fs = render_local.fs_path(
            os.path.join(root_real, "tenants", tenant, "campaigns")
        )
        if not os.path.isdir(campaigns_fs):
            continue
        for name in sorted(os.listdir(campaigns_fs)):
            if name.endswith(".json"):
                campaigns.append({"tenant": tenant, "slug": name[: -len(".json")]})
    return campaigns


def _check_contratos(root_real: str) -> tuple[list[dict], dict]:
    problems: list[dict] = []
    valid: list[str] = []
    invalid: list[str] = []
    for tenant_id in tenant_validator.list_tenants(root_real):
        try:
            result = tenant_validator.load_and_validate_tenant(
                tenant_id, root=root_real, strict=False
            )
        except tenant_validator.TenantContractError as exc:
            invalid.append(tenant_id)
            problems.append(_error("TENANT_INVALIDO", f"{tenant_id}: {exc}"))
            continue
        if result["ok"]:
            valid.append(tenant_id)
        else:
            invalid.append(tenant_id)
            for message in result["errors"]:
                problems.append(_error("TENANT_INVALIDO", f"{tenant_id}: {message}"))
    if len(valid) < MIN_VALID_TENANTS:
        problems.append(
            _error(
                "TENANTS_INSUFICIENTES",
                f"{len(valid)} tenant(s) valido(s), minimo {MIN_VALID_TENANTS}",
            )
        )
    summary = {"total": len(valid) + len(invalid), "valid": len(valid), "invalid": len(invalid)}
    return problems, summary


def _check_manifest_artifacts(
    manifest: dict, delivery_dir: str, slug: str, label: str, problems: list[dict]
) -> None:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        problems.append(_error("ARTIFACTO_MANIFESTO_AUSENTE", f"{label}: secao artifacts"))
        return
    for key, template in EXPECTED_ARTIFACTS:
        filename = template.format(slug=slug)
        artifact = artifacts.get(key)
        if not isinstance(artifact, dict) or not artifact.get("sha256"):
            problems.append(_error("ARTIFACTO_MANIFESTO_AUSENTE", f"{label}: artifacts.{key}"))
            continue
        artifact_path = os.path.join(delivery_dir, filename)
        if not os.path.isfile(render_local.fs_path(artifact_path)):
            problems.append(_error("ARQUIVO_AUSENTE", f"{label}: {filename}"))
            continue
        if render_local.sha256_file(artifact_path) != artifact["sha256"]:
            problems.append(_error("HASH_DIVERGENTE", f"{label}: {filename}"))
            continue
        if "bytes" in artifact and os.path.getsize(
            render_local.fs_path(artifact_path)
        ) != artifact["bytes"]:
            problems.append(_error("TAMANHO_DIVERGENTE", f"{label}: {filename}"))


def _check_audio_policy(manifest: dict, label: str, problems: list[dict]) -> None:
    guardrails = manifest.get("guardrails")
    artifacts = manifest.get("artifacts")
    video = artifacts.get("video") if isinstance(artifacts, dict) else None
    ffprobe = video.get("ffprobe") if isinstance(video, dict) else None
    allow = guardrails.get("allowAudioTrack") if isinstance(guardrails, dict) else None
    streams = ffprobe.get("audioStreams") if isinstance(ffprobe, dict) else None
    if not isinstance(allow, bool) or not isinstance(streams, int):
        problems.append(
            _error(
                "FFPROBE_AUDIO_AUSENTE",
                f"{label}: manifesto sem guardrails.allowAudioTrack ou "
                "artifacts.video.ffprobe.audioStreams",
            )
        )
        return
    if allow and streams < 1:
        problems.append(
            _error(
                "POLITICA_AUDIO_DESCUMPRIDA",
                f"{label}: allowAudioTrack=true exige audioStreams >= 1 (trilha aac), "
                f"manifesto declara {streams}",
            )
        )
    elif not allow and streams != 0:
        problems.append(
            _error(
                "POLITICA_AUDIO_DESCUMPRIDA",
                f"{label}: allowAudioTrack=false exige audioStreams 0 (export -an), "
                f"manifesto declara {streams}",
            )
        )


def _check_video_file(manifest: dict, delivery_dir: str, slug: str, label: str, problems: list[dict]) -> None:
    artifacts = manifest.get("artifacts")
    video = artifacts.get("video") if isinstance(artifacts, dict) else None
    if not isinstance(video, dict) or not video.get("sha256"):
        return
    video_name = VIDEO_NAME_TEMPLATE.format(slug=slug)
    video_path = os.path.join(delivery_dir, video_name)
    if not os.path.isfile(render_local.fs_path(video_path)):
        return
    if render_local.sha256_file(video_path) != video["sha256"]:
        problems.append(_error("HASH_DIVERGENTE", f"{label}: {video_name}"))


def _check_entregas(root_real: str, campaigns: list[dict]) -> tuple[list[dict], int]:
    problems: list[dict] = []
    failed = 0
    for campaign in campaigns:
        tenant, slug = campaign["tenant"], campaign["slug"]
        label = f"{tenant}/{slug}"
        campaign_problems: list[dict] = []
        delivery_dir = os.path.join(root_real, *DELIVERY_ROOT, tenant, slug)
        if not os.path.isdir(render_local.fs_path(delivery_dir)):
            campaign_problems.append(
                _error(
                    "DELIVERY_DIR_AUSENTE",
                    f"{'/'.join(DELIVERY_ROOT)}/{tenant}/{slug}",
                )
            )
        else:
            manifest_path = os.path.join(delivery_dir, "manifest.json")
            manifest = None
            if not os.path.isfile(render_local.fs_path(manifest_path)):
                campaign_problems.append(_error("MANIFEST_AUSENTE", f"{label}: manifest.json"))
            else:
                try:
                    manifest = _read_json(manifest_path)
                except (OSError, ValueError) as exc:
                    campaign_problems.append(_error("MANIFEST_INVALIDO", f"{label}: {exc}"))
            if manifest is not None:
                _check_manifest_artifacts(manifest, delivery_dir, slug, label, campaign_problems)
                _check_audio_policy(manifest, label, campaign_problems)
                _check_video_file(manifest, delivery_dir, slug, label, campaign_problems)
        if _has_error(campaign_problems):
            failed += 1
        problems.extend(campaign_problems)
    return problems, failed


def _check_package_media(
    root_real: str, checklist: dict, label: str, problems: list[dict]
) -> None:
    media = checklist.get("media")
    if not isinstance(media, list):
        return
    for entry in media:
        if not isinstance(entry, dict):
            continue
        rel_path = entry.get("path")
        expected = entry.get("sha256")
        if not isinstance(rel_path, str) or not expected:
            continue
        target = _join_rel(root_real, rel_path)
        if not os.path.isfile(render_local.fs_path(target)):
            continue
        if render_local.sha256_file(target) != expected:
            problems.append(_error("HASH_DIVERGENTE", f"{label}: {rel_path}"))


def _check_pacotes(root_real: str, campaigns: list[dict]) -> tuple[list[dict], int]:
    problems: list[dict] = []
    failed = 0
    for campaign in campaigns:
        tenant, slug = campaign["tenant"], campaign["slug"]
        label = f"{tenant}/{slug}"
        campaign_problems: list[dict] = []
        package_dir = os.path.join(root_real, *PACKAGE_ROOT, tenant, slug)
        checklist_path = os.path.join(package_dir, "checklist-publicacao.json")
        if not os.path.isfile(render_local.fs_path(checklist_path)):
            campaign_problems.append(
                _error(
                    "PACOTE_AUSENTE",
                    f"{'/'.join(PACKAGE_ROOT)}/{tenant}/{slug}/checklist-publicacao.json",
                )
            )
        else:
            checklist = None
            try:
                checklist = _read_json(checklist_path)
            except (OSError, ValueError) as exc:
                campaign_problems.append(_error("CHECKLIST_INVALIDO", f"{label}: {exc}"))
            if checklist is not None:
                if checklist.get("autoPublish") is not False:
                    campaign_problems.append(
                        _error("AUTO_PUBLICACAO_ATIVO", f"{label}: autoPublish deve ser false")
                    )
                if checklist.get("guardrailsAudited") is not True:
                    campaign_problems.append(
                        _error("GUARDRAILS_NAO_AUDITADOS", f"{label}: guardrailsAudited deve ser true")
                    )
                for name in PACKAGE_FILES:
                    if not os.path.isfile(render_local.fs_path(os.path.join(package_dir, name))):
                        campaign_problems.append(
                            _error("ARQUIVO_PACOTE_AUSENTE", f"{label}: {name}")
                        )
                _check_package_media(root_real, checklist, label, campaign_problems)
        if _has_error(campaign_problems):
            failed += 1
        problems.extend(campaign_problems)
    return problems, failed


def _check_derivados(root_real: str, campaigns: list[dict]) -> tuple[list[dict], int]:
    problems: list[dict] = []
    failed = 0
    for campaign in campaigns:
        tenant, slug = campaign["tenant"], campaign["slug"]
        label = f"{tenant}/{slug}"
        campaign_problems: list[dict] = []
        derivatives_path = os.path.join(root_real, *DELIVERY_ROOT, tenant, slug, "derivatives.json")
        if not os.path.isfile(render_local.fs_path(derivatives_path)):
            campaign_problems.append(_warning("DERIVATIVES_AUSENTE", f"{label}: derivatives.json"))
        else:
            data = None
            try:
                data = _read_json(derivatives_path)
            except (OSError, ValueError) as exc:
                campaign_problems.append(_error("DERIVATIVES_INVALIDO", f"{label}: {exc}"))
            if data is not None:
                declarations = data.get("derivatives")
                if not isinstance(declarations, dict):
                    campaign_problems.append(
                        _error("DERIVATIVES_INVALIDO", f"{label}: secao derivatives")
                    )
                else:
                    for key in DERIVATIVE_KEYS:
                        entry = declarations.get(key)
                        if not isinstance(entry, dict):
                            campaign_problems.append(
                                _error("DERIVADO_DECLARACAO_AUSENTE", f"{label}: derivatives.{key}")
                            )
                            continue
                        expected = entry.get("sha256")
                        rel_path = entry.get("path")
                        if not expected or not isinstance(rel_path, str):
                            campaign_problems.append(
                                _error(
                                    "DERIVADO_SEM_HASH",
                                    f"{label}: derivatives.{key} sem sha256 ou path",
                                )
                            )
                            continue
                        target = _join_rel(root_real, rel_path)
                        if not os.path.isfile(render_local.fs_path(target)):
                            continue
                        if render_local.sha256_file(target) != expected:
                            campaign_problems.append(
                                _error("HASH_DIVERGENTE", f"{label}: derivatives.{key} ({rel_path})")
                            )
        if _has_error(campaign_problems):
            failed += 1
        problems.extend(campaign_problems)
    return problems, failed


def _check_calendario(root_real: str) -> list[dict]:
    problems: list[dict] = []
    json_path = os.path.join(root_real, *CALENDAR_JSON)
    md_path = os.path.join(root_real, *CALENDAR_MD)
    json_present = os.path.isfile(render_local.fs_path(json_path))
    if not json_present:
        problems.append(_warning("CALENDARIO_AUSENTE", "/".join(CALENDAR_JSON)))
    if not os.path.isfile(render_local.fs_path(md_path)):
        problems.append(_warning("CALENDARIO_AUSENTE", "/".join(CALENDAR_MD)))
    if json_present:
        data = None
        try:
            data = _read_json(json_path)
        except (OSError, ValueError) as exc:
            problems.append(_error("CALENDARIO_INVALIDO", f"calendario-editorial.json: {exc}"))
        if data is not None:
            if data.get("autoPublish") is not False:
                problems.append(
                    _error(
                        "AUTO_PUBLICACAO_ATIVO",
                        "calendario-editorial.json: autoPublish deve ser false",
                    )
                )
            slots = data.get("slots")
            if not isinstance(slots, list):
                problems.append(_error("SLOTS_AUSENTES", "calendario-editorial.json: secao slots"))
            else:
                total = data.get("totalSlots")
                if isinstance(total, int) and total != len(slots):
                    problems.append(
                        _error(
                            "SLOTS_CONTAGEM_DIVERGENTE",
                            f"calendario-editorial.json: totalSlots={total}, "
                            f"{len(slots)} slot(s) declarado(s)",
                        )
                    )
                offending = sum(
                    1
                    for slot in slots
                    if isinstance(slot, dict) and slot.get("autoPublish") is not False
                )
                if offending:
                    problems.append(
                        _error(
                            "AUTO_PUBLICACAO_ATIVO",
                            f"calendario-editorial.json: {offending} slot(s) com autoPublish "
                            "diferente de false",
                        )
                    )
    if not os.path.isfile(render_local.fs_path(os.path.join(root_real, *MATRIZ_UTM))):
        problems.append(_warning("MATRIZ_UTM_AUSENTE", "/".join(MATRIZ_UTM)))
    return problems


def _check_portal(root_real: str) -> list[dict]:
    problems: list[dict] = []
    portal_dir = os.path.join(root_real, PORTAL_DIR)
    for name in PORTAL_FILES:
        if not os.path.isfile(render_local.fs_path(os.path.join(portal_dir, name))):
            problems.append(_warning("PORTAL_ARQUIVO_AUSENTE", f"{PORTAL_DIR}/{name}"))
    for name in PORTAL_SCANNED_FILES:
        path = os.path.join(portal_dir, name)
        if not os.path.isfile(render_local.fs_path(path)):
            continue
        with open(render_local.fs_path(path), "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        match = ABSOLUTE_PATH_PATTERN.search(content)
        if match:
            problems.append(
                _error(
                    "CAMINHO_ABSOLUTO_VAZADO",
                    f"{PORTAL_DIR}/{name}: caminho local '{match.group(0)}'",
                )
            )
    return problems


def _check_gitattributes(root_real: str) -> list[dict]:
    path = os.path.join(root_real, ".gitattributes")
    if not os.path.isfile(render_local.fs_path(path)):
        return [_error("GITATTRIBUTES_AUSENTE", ".gitattributes")]
    with open(render_local.fs_path(path), "r", encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()
    rules = [line.strip() for line in lines if "eol=lf" in line]
    if not rules:
        return [_error("GITATTRIBUTES_SEM_EOL_LF", ".gitattributes sem nenhuma regra 'eol=lf'")]
    problems: list[dict] = []
    for ext in GITATTRIBUTES_EXTENSIONS:
        if not any(ext in rule for rule in rules):
            problems.append(
                _error("GITATTRIBUTES_EXT_SEM_EOL_LF", f".gitattributes sem regra 'eol=lf' para {ext}")
            )
    return problems


def _list_worktrees(root_real: str) -> dict[str, str]:
    output = _run_git(root_real, "worktree", "list", "--porcelain")
    registered: dict[str, str] = {}
    for line in output.splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):].strip()
            registered[os.path.basename(path.rstrip("/\\"))] = path
    return registered


def _check_worktrees(root_real: str) -> list[dict]:
    problems: list[dict] = []
    registered = _list_worktrees(root_real)
    for name in HISTORICAL_WORKTREES:
        if name in registered:
            path = registered[name]
            if not os.path.isdir(render_local.fs_path(path)):
                problems.append(
                    _error("WORKTREE_REGISTRADA_SEM_DIRETORIO", f"{name}: {path}")
                )
            continue
        orphan_dir = os.path.join(root_real, ".workspace", "worktrees", name)
        if os.path.isdir(render_local.fs_path(orphan_dir)):
            problems.append(
                _warning(
                    "WORKTREE_ORFA",
                    f"{name}: diretorio sem registro ({render_local.rel(root_real, orphan_dir)})",
                )
            )
    return problems


def _check_higiene(root_real: str) -> list[dict]:
    problems: list[dict] = []
    output = _run_git(root_real, "ls-files", "--", "*.mp4", "*.wav")
    tracked = [line.strip() for line in output.splitlines() if line.strip()]
    if tracked:
        problems.append(_error("MIDIA_RASTREADA", ", ".join(tracked)))

    others = _run_git(
        root_real, "ls-files", "--others", "--exclude-standard", "--", "*.mp4", "*.wav"
    )
    not_ignored = [line.strip() for line in others.splitlines() if line.strip()]
    if not_ignored:
        problems.append(
            _error("MIDIA_NAO_IGNORADA", "fora do Git Ignore: " + ", ".join(not_ignored))
        )

    indexed = [line.strip() for line in _run_git(root_real, "ls-files").splitlines() if line.strip()]
    snapshots = [path for path in indexed if _is_snapshot_path(path)]
    if snapshots:
        problems.append(_error("SNAPSHOT_RASTREADO", ", ".join(snapshots)))
    problems.extend(_check_gitattributes(root_real))
    problems.extend(_check_worktrees(root_real))
    return problems


# ---------------------------------------------------------------------------
# Integridade manifestos <-> binarios locais (dominios 2, 4 e 7)
# ---------------------------------------------------------------------------
def _is_snapshot_path(rel_path: str) -> bool:
    norm = str(rel_path).replace("\\", "/")
    lowered = norm.lower()
    if norm.startswith(".workspace/snapshots/"):
        return True
    base = lowered.rsplit("/", 1)[-1]
    if base == "snapshot-index.json" or base.startswith("workspace-snapshot-"):
        return True
    return lowered.endswith(".zip") and "snapshot" in lowered


def _split_integrity_problems(integrity: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Distribui os achados entre entregas_video, derivados_multiformato e higiene_git."""
    entregas: list[dict] = []
    derivados: list[dict] = []
    higiene: list[dict] = []
    for problem in integrity.get("problems", []):
        code = problem["code"]
        message = problem["message"]
        if code == "MIDIA_ORFA" or code.startswith(("PATH_OUTSIDE", "SNAPSHOT")):
            higiene.append(problem)
        elif "derivatives." in message or code.startswith("DERIVATIVES_"):
            derivados.append(problem)
        else:
            entregas.append(problem)
    return entregas, derivados, higiene


def _check_manifest_integrity(root_real: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Só cruza quando ha binarios locais; midia ausente na estacao e politica aceita."""
    main_root = os.path.realpath(workspace_doctor._resolve_main_root(root_real))
    archives = os.path.join(main_root, *workspace_doctor.WORKSPACE_REL, "archives")
    if not os.path.isdir(render_local.fs_path(archives)):
        return [], [], []
    try:
        integrity = workspace_doctor.audit_manifest_integrity(root_real, source_root=root_real)
    except workspace_doctor.WorkspaceDoctorError as exc:
        return [_error("INTEGRIDADE_LOCAL_INDISPONIVEL", str(exc))], [], []
    return _split_integrity_problems(integrity)


def _check_empacotamento(root_real: str) -> list[dict]:
    """Verifica se todos os bundles em .workspace/bundles/ sao validos (domínio 8).

    Retorna [] quando nao ha bundles (dominio informativo: so verifica o que
    existe). Com --strict, qualquer bundle invalido ou hash divergente reprova.
    """
    problems: list[dict] = []
    bundles_root = os.path.join(root_real, ".workspace", "bundles")
    if not os.path.isdir(render_local.fs_path(bundles_root)):
        return []

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
                    result = publish_bundler.verify_bundle(bundle_abs, root=root_real)
                except publish_bundler.PublishBundlerError as exc:
                    problems.append(
                        _error(
                            "BUNDLE_VERIFICACAO_FALHOU",
                            f"{tenant_id}/{slug}/{name}: {exc.code} - {exc.detail}",
                        )
                    )
                    continue
                if not result["ok"]:
                    for problem in result.get("problems", []):
                        problems.append(
                            {
                                "severity": problem["severity"],
                                "code": f"BUNDLE_{problem['code']}",
                                "message": f"{tenant_id}/{slug}/{name}: {problem['message']}",
                            }
                        )
    return problems


def run_release_audit(root: str = ".", strict: bool = False) -> dict:
    """Executa a auditoria dos 7 dominios e retorna o relatorio schemaVersion 2."""
    root_real = os.path.realpath(root)
    if not os.path.isdir(render_local.fs_path(root_real)):
        raise ReleaseAuditError(f"raiz ausente: {root_real}")

    campaigns = discover_campaigns(root_real)
    contrato_problems, tenants_summary = _check_contratos(root_real)
    entrega_problems, deliveries_failed = _check_entregas(root_real, campaigns)
    pacote_problems, packages_failed = _check_pacotes(root_real, campaigns)
    derivado_problems, derivatives_failed = _check_derivados(root_real, campaigns)
    calendario_problems = _check_calendario(root_real)
    portal_problems = _check_portal(root_real)
    higiene_problems = _check_higiene(root_real)
    empacotamento_problems = _check_empacotamento(root_real)

    # Integridade manifestos <-> binarios locais, distribuida entre os 7 dominios.
    extra_entregas, extra_derivados, extra_higiene = _check_manifest_integrity(root_real)
    entrega_problems = extra_entregas + entrega_problems
    derivado_problems = extra_derivados + derivado_problems
    higiene_problems = extra_higiene + higiene_problems

    results = (
        contrato_problems,
        entrega_problems,
        pacote_problems,
        derivado_problems,
        calendario_problems,
        portal_problems,
        higiene_problems,
        empacotamento_problems,
    )
    domains = [
        _domain(domain_id, name, problems)
        for (domain_id, name), problems in zip(DOMAIN_NAMES, results)
    ]
    all_problems = [problem for problems in results for problem in problems]
    errors = sum(1 for problem in all_problems if problem["severity"] == "error")
    warnings = sum(1 for problem in all_problems if problem["severity"] == "warning")

    return {
        "schemaVersion": 2,
        "ok": errors == 0 and not (strict and warnings > 0),
        "strict": strict,
        "root": root_real,
        "domains": domains,
        "summary": {
            "domains": {
                "ok": sum(1 for domain in domains if domain["status"] == "ok"),
                "warn": sum(1 for domain in domains if domain["status"] == "warn"),
                "fail": sum(1 for domain in domains if domain["status"] == "fail"),
            },
            "problems": {"errors": errors, "warnings": warnings},
            "tenants": tenants_summary,
            "campaigns": {
                "total": len(campaigns),
                "deliveriesFailed": deliveries_failed,
                "packagesFailed": packages_failed,
                "derivativesFailed": derivatives_failed,
            },
        },
    }


def _resolve_report_path(root_real: str, report_out: str | None) -> str | None:
    if not report_out:
        return None
    candidate = (
        report_out
        if os.path.isabs(report_out)
        else os.path.join(root_real, *report_out.replace("\\", "/").split("/"))
    )
    resolved = os.path.realpath(candidate)
    if not render_local.contained(root_real, resolved):
        raise ReleaseAuditError(
            f"PATH_OUTSIDE_ROOT: --report-out deve ficar sob a raiz ({root_real})"
        )
    return resolved


def _write_report(path: str, result: dict) -> None:
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(render_local.fs_path(parent), exist_ok=True)
        with open(render_local.fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except OSError as exc:
        raise ReleaseAuditError(f"REPORT_OUT_FALHOU: {exc}") from exc


def _stdout_utf8() -> None:
    """Garante UTF-8 na saida: no Windows o encoding padrao de pipe ou arquivo
    redirecionado e o da locale (cp1252), que corromperia os nomes acentuados
    dos dominios para qualquer consumidor UTF-8 (inclusive o CI)."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


def _print_human(result: dict) -> None:
    status_label = {"ok": "OK", "warn": "AVISO", "fail": "FALHA"}
    for domain in result["domains"]:
        print(f"[{status_label[domain['status']]}] {domain['id']} — {domain['name']}")
        for problem in domain["problems"]:
            print(f"    - [{problem['severity']}] {problem['code']}: {problem['message']}")
    summary = result["summary"]
    print()
    print(
        f"Tenants validos: {summary['tenants']['valid']}/{summary['tenants']['total']}"
        f" (minimo {MIN_VALID_TENANTS})"
    )
    print(
        f"Campanhas: {summary['campaigns']['total']} | "
        f"entregas reprovadas: {summary['campaigns']['deliveriesFailed']} | "
        f"pacotes reprovados: {summary['campaigns']['packagesFailed']} | "
        f"derivados reprovados: {summary['campaigns']['derivativesFailed']}"
    )
    print(
        f"Dominios: {summary['domains']['ok']} ok, {summary['domains']['warn']} aviso(s), "
        f"{summary['domains']['fail']} falha(s)"
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
        description="Auditor final de prontidao de release (7 dominios)"
    )
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument(
        "--strict", action="store_true", help="Avisos tambem reprovam o release"
    )
    parser.add_argument("--json", action="store_true", help="Emite JSON no stdout")
    parser.add_argument(
        "--report-out",
        default=None,
        help="Grava o relatorio JSON neste caminho, obrigatoriamente sob a raiz",
    )
    args = parser.parse_args(argv)

    try:
        root_real = os.path.realpath(args.root)
        if not os.path.isdir(render_local.fs_path(root_real)):
            raise ReleaseAuditError(f"raiz ausente: {root_real}")
        report_path = _resolve_report_path(root_real, args.report_out)
        result = run_release_audit(root=root_real, strict=args.strict)
        if report_path:
            _write_report(report_path, result)
    except ReleaseAuditError as exc:
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
