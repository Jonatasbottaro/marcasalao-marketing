"""Auditor final de prontidao de release da fabrica de video.

Verifica, em uma unica passada, o estado de prontidao de release do checkout:

  1. Tenants: pelo menos 4 tenants validos via tenant_validator (brand-kit,
     guardrails e fixture validados por schema e guardrails de texto).
  2. Entregas: toda campanha em `tenants/*/campaigns/*.json` possui pacote de
     entrega em `02-reels-shorts/deliveries/<tenant>/<slug>/` com manifest.json,
     `<slug>.srt`, `<slug>_narracao.txt` e `preview-storyboard.png`, com hashes
     SHA-256 e tamanhos conferidos em disco. O video `<slug>.mp4` nao e
     versionado (`.gitignore` cobre `*.mp4`): quando presente em disco o hash
     e conferido; quando ausente gera aviso, pois o manifesto preserva hash,
     ffprobe e comando reproduzivel.
  3. Pacotes sociais: `04-legendas/pacotes-publicacao/<tenant>/<slug>/` com
     checklist-publicacao.json e `autoPublish: false`.
  4. Higiene Git: nenhum `.mp4`/`.wav` rastreado, regras `eol=lf` em
     `.gitattributes` e worktrees historicas preservadas
     (prova-campanha-conclusao e studio-package-verify2).

O modo padrao reprova somente falhas. `--strict` tambem reprova avisos (video
nao versionado ausente no disco, worktree historica ausente na estacao e
worktree orfa), cobrindo o gate de release na estacao que possui os videos.

Exit codes: 0 aprovado; 1 auditoria reprovada; 2 erro de uso ou execucao.
"""

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import render_local
import tenant_validator

MIN_VALID_TENANTS = 4
HISTORICAL_WORKTREES = ("prova-campanha-conclusao", "studio-package-verify2")
EXPECTED_ARTIFACTS = (
    ("srt", "{slug}.srt"),
    ("narration", "{slug}_narracao.txt"),
    ("storyboard", "preview-storyboard.png"),
)
VIDEO_NAME_TEMPLATE = "{slug}.mp4"


class ReleaseAuditError(Exception):
    """Erro de execucao do auditor (raiz ausente, git indisponivel)."""


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


def _check_tenants(root_real: str) -> dict:
    check: dict = {"id": "tenants", "status": "ok", "problems": [], "valid": [], "invalid": []}
    for tenant_id in tenant_validator.list_tenants(root_real):
        try:
            result = tenant_validator.load_and_validate_tenant(
                tenant_id, root=root_real, strict=False
            )
        except tenant_validator.TenantContractError as exc:
            check["invalid"].append(tenant_id)
            check["problems"].append(f"TENANT_INVALIDO: {tenant_id}: {exc}")
            continue
        if result["ok"]:
            check["valid"].append(tenant_id)
        else:
            check["invalid"].append(tenant_id)
            for error in result["errors"]:
                check["problems"].append(f"TENANT_INVALIDO: {tenant_id}: {error}")
    if len(check["valid"]) < MIN_VALID_TENANTS:
        check["problems"].append(
            f"TENANTS_INSUFICIENTES: {len(check['valid'])} validos, minimo {MIN_VALID_TENANTS}"
        )
    if check["invalid"] or len(check["valid"]) < MIN_VALID_TENANTS:
        check["status"] = "fail"
    return check


def _check_delivery(root_real: str, tenant: str, slug: str) -> dict:
    check: dict = {"id": f"delivery:{tenant}/{slug}", "status": "ok", "problems": []}
    delivery_dir = os.path.join(root_real, "02-reels-shorts", "deliveries", tenant, slug)
    if not os.path.isdir(render_local.fs_path(delivery_dir)):
        check["status"] = "fail"
        check["problems"].append(
            f"DELIVERY_DIR_AUSENTE: 02-reels-shorts/deliveries/{tenant}/{slug}"
        )
        return check
    manifest_path = os.path.join(delivery_dir, "manifest.json")
    if not os.path.isfile(render_local.fs_path(manifest_path)):
        check["status"] = "fail"
        check["problems"].append("MANIFEST_AUSENTE: manifest.json")
        return check
    try:
        manifest = _read_json(manifest_path)
    except (OSError, ValueError) as exc:
        check["status"] = "fail"
        check["problems"].append(f"MANIFEST_INVALIDO: {exc}")
        return check
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        check["status"] = "fail"
        check["problems"].append("ARTIFACTO_MANIFESTO_AUSENTE: secao artifacts")
        return check
    for key, template in EXPECTED_ARTIFACTS:
        filename = template.format(slug=slug)
        artifact = artifacts.get(key)
        if not isinstance(artifact, dict) or not artifact.get("sha256"):
            check["status"] = "fail"
            check["problems"].append(f"ARTIFACTO_MANIFESTO_AUSENTE: artifacts.{key}")
            continue
        artifact_path = os.path.join(delivery_dir, filename)
        if not os.path.isfile(render_local.fs_path(artifact_path)):
            check["status"] = "fail"
            check["problems"].append(f"ARQUIVO_AUSENTE: {filename}")
            continue
        if render_local.sha256_file(artifact_path) != artifact["sha256"]:
            check["status"] = "fail"
            check["problems"].append(f"HASH_DIVERGENTE: {filename}")
            continue
        if "bytes" in artifact and os.path.getsize(
            render_local.fs_path(artifact_path)
        ) != artifact["bytes"]:
            check["status"] = "fail"
            check["problems"].append(f"TAMANHO_DIVERGENTE: {filename}")
    video = artifacts.get("video")
    video_name = VIDEO_NAME_TEMPLATE.format(slug=slug)
    video_path = os.path.join(delivery_dir, video_name)
    if isinstance(video, dict) and video.get("sha256"):
        if os.path.isfile(render_local.fs_path(video_path)):
            if render_local.sha256_file(video_path) != video["sha256"]:
                check["status"] = "fail"
                check["problems"].append(f"HASH_DIVERGENTE: {video_name}")
        else:
            if check["status"] != "fail":
                check["status"] = "warn"
            check["problems"].append(f"VIDEO_NAO_VERSIONADO_AUSENTE_NO_DISCO: {video_name}")
    return check


def _check_package(root_real: str, tenant: str, slug: str) -> dict:
    check: dict = {"id": f"package:{tenant}/{slug}", "status": "ok", "problems": []}
    package_rel = f"04-legendas/pacotes-publicacao/{tenant}/{slug}"
    checklist_path = os.path.join(
        root_real, "04-legendas", "pacotes-publicacao", tenant, slug, "checklist-publicacao.json"
    )
    if not os.path.isfile(render_local.fs_path(checklist_path)):
        check["status"] = "fail"
        check["problems"].append(f"PACOTE_AUSENTE: {package_rel}/checklist-publicacao.json")
        return check
    try:
        checklist = _read_json(checklist_path)
    except (OSError, ValueError) as exc:
        check["status"] = "fail"
        check["problems"].append(f"CHECKLIST_INVALIDO: {exc}")
        return check
    if checklist.get("autoPublish") is not False:
        check["status"] = "fail"
        check["problems"].append("AUTO_PUBLICACAO_ATIVO: autoPublish deve ser false")
    return check


def _check_no_binary_media(root_real: str) -> dict:
    check: dict = {
        "id": "git_hygiene:no_binary_media_tracked",
        "status": "ok",
        "problems": [],
    }
    output = _run_git(root_real, "ls-files", "--", "*.mp4", "*.wav")
    tracked = [line.strip() for line in output.splitlines() if line.strip()]
    if tracked:
        check["status"] = "fail"
        check["problems"].append("MIDIA_RASTREADA: " + ", ".join(tracked))
    return check


def _check_gitattributes_eol(root_real: str) -> dict:
    check: dict = {"id": "git_hygiene:gitattributes_eol_lf", "status": "ok", "problems": []}
    gitattributes_path = os.path.join(root_real, ".gitattributes")
    if not os.path.isfile(render_local.fs_path(gitattributes_path)):
        check["status"] = "fail"
        check["problems"].append("GITATTRIBUTES_AUSENTE: .gitattributes")
        return check
    with open(
        render_local.fs_path(gitattributes_path), "r", encoding="utf-8", errors="replace"
    ) as handle:
        content = handle.read()
    rules = [line.strip() for line in content.splitlines() if "eol=lf" in line]
    if not rules:
        check["status"] = "fail"
        check["problems"].append("GITATTRIBUTES_SEM_EOL_LF: nenhuma regra 'text eol=lf'")
    else:
        check["rules"] = len(rules)
    return check


def _list_worktrees(root_real: str) -> dict[str, str]:
    output = _run_git(root_real, "worktree", "list", "--porcelain")
    registered: dict[str, str] = {}
    for line in output.splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):].strip()
            registered[os.path.basename(path.rstrip("/\\"))] = path
    return registered


def _check_historical_worktree(root_real: str, name: str, registered: dict[str, str]) -> dict:
    check: dict = {"id": f"git_hygiene:worktree:{name}", "status": "ok", "problems": []}
    if name in registered:
        path = registered[name]
        if os.path.isdir(render_local.fs_path(path)):
            check["path"] = path
        else:
            check["status"] = "fail"
            check["problems"].append(f"WORKTREE_REGISTRADA_SEM_DIRETORIO: {path}")
        return check
    orphan_dir = os.path.join(root_real, ".workspace", "worktrees", name)
    if os.path.isdir(render_local.fs_path(orphan_dir)):
        check["status"] = "warn"
        check["problems"].append(
            f"WORKTREE_ORFA: diretorio sem registro ({render_local.rel(root_real, orphan_dir)})"
        )
    else:
        check["status"] = "warn"
        check["problems"].append(
            "WORKTREE_AUSENTE_NA_ESTACAO: nem registro nem diretorio nesta estacao"
        )
    return check


def run_audit(root: str = ".", strict: bool = False) -> dict:
    """Executa a auditoria completa e retorna o relatorio com todos os checks."""
    root_real = os.path.realpath(root)
    if not os.path.isdir(render_local.fs_path(root_real)):
        raise ReleaseAuditError(f"raiz ausente: {root_real}")

    checks: list[dict] = []
    tenants_check = _check_tenants(root_real)
    checks.append(tenants_check)

    campaigns = discover_campaigns(root_real)
    for campaign in campaigns:
        checks.append(_check_delivery(root_real, campaign["tenant"], campaign["slug"]))
        checks.append(_check_package(root_real, campaign["tenant"], campaign["slug"]))

    checks.append(_check_no_binary_media(root_real))
    checks.append(_check_gitattributes_eol(root_real))
    registered = _list_worktrees(root_real)
    for name in HISTORICAL_WORKTREES:
        checks.append(_check_historical_worktree(root_real, name, registered))

    failed = [check for check in checks if check["status"] == "fail"]
    warned = [check for check in checks if check["status"] == "warn"]
    ok = not failed and not (strict and warned)

    return {
        "schemaVersion": 1,
        "ok": ok,
        "strict": strict,
        "root": root_real,
        "summary": {
            "tenants": {
                "total": len(tenants_check["valid"]) + len(tenants_check["invalid"]),
                "valid": len(tenants_check["valid"]),
                "invalid": len(tenants_check["invalid"]),
            },
            "campaigns": {
                "total": len(campaigns),
                "deliveryFailed": sum(
                    1 for check in checks
                    if check["id"].startswith("delivery:") and check["status"] == "fail"
                ),
                "packageFailed": sum(
                    1 for check in checks
                    if check["id"].startswith("package:") and check["status"] == "fail"
                ),
            },
            "checks": {
                "ok": sum(1 for check in checks if check["status"] == "ok"),
                "warn": len(warned),
                "fail": len(failed),
            },
        },
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditor final de prontidao de release")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument(
        "--strict", action="store_true", help="Avisos tambem reprovam o release"
    )
    parser.add_argument("--json", action="store_true", help="Emite JSON no stdout")
    args = parser.parse_args(argv)

    try:
        result = run_audit(root=args.root, strict=args.strict)
    except ReleaseAuditError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Erro: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1

    status_label = {"ok": "OK", "warn": "AVISO", "fail": "FALHA"}
    for check in result["checks"]:
        print(f"[{status_label[check['status']]}] {check['id']}")
        for problem in check["problems"]:
            print(f"    - {problem}")
    summary = result["summary"]
    print()
    print(
        f"Tenants validos: {summary['tenants']['valid']}/{summary['tenants']['total']}"
        f" (minimo {MIN_VALID_TENANTS})"
    )
    print(
        f"Campanhas: {summary['campaigns']['total']} | "
        f"entregas reprovadas: {summary['campaigns']['deliveryFailed']} | "
        f"pacotes reprovados: {summary['campaigns']['packageFailed']}"
    )
    print(
        f"Checks: {summary['checks']['ok']} ok, {summary['checks']['warn']} aviso(s), "
        f"{summary['checks']['fail']} falha(s)"
    )
    mode = " (strict)" if result["strict"] else ""
    print(f"Resultado{mode}: {'APROVADO' if result['ok'] else 'REPROVADO'}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
