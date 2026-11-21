"""Comando unico de verificacao de release da fabrica multi-tenant.

Orquestra, em sequencia e com as flags reais de cada ferramenta, os gates
oficiais do projeto. E 100% stdlib, cross-platform (Windows e Ubuntu) e
somente leitura: nao publica, nao agenda, nao gera audio e nao grava
artefatos versionados.

Gates orquestrados (nesta ordem):

  1. Higiene Git        - zero ``.mp4``/``.wav``/``.zip`` rastreados ou
                          nao-ignorados (inclui snapshots ``*.zip``) e o
                          invariante ``autoPublish: false`` em todos os JSONs
                          versionados (fora de ``node_modules/``/``.workspace/``).
  2. TypeScript         - ``npm run build`` e ``npm test`` em ``platform/``
                          (omitido quando ``--skip-ts``).
  3. Contratos          - ``python tools/tenant_validator.py --all --json``
                          (5 tenants).
  4. Editorial          - ``python tools/editorial_qa.py --all --strict --json``
                          (14 campanhas, 7 lentes, 0 erros e 0 avisos).
  5. Workspace doctor   - ``python tools/workspace_doctor.py --check --json``.
  6. Release audit      - ``python tools/release_audit.py --strict --json``
                          (8/8 dominios, incluindo empacotamento de distribuicao).
  7. Empacotamento      - ``python tools/publish_bundler.py verify`` sobre todos
                          os bundles em ``.workspace/bundles/`` (nao reprova se
                          nao houver bundles nesta estacao).
  8. E2E da fabrica     - ``python -m unittest discover -s tests/e2e -v``.

CLI:
    python tools/release_check.py [--json] [--skip-ts] [--root <raiz>]

Exit codes: 0 todos os gates aprovados; 1 algum gate reprovou; 2 erro de uso.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MEDIA_EXTENSIONS = ("*.mp4", "*.wav")
SNAPSHOT_EXTENSIONS = ("*.zip",)
EXCLUDED_DIRS = ("node_modules", ".workspace", ".git")
JSON_SUFFIX = ".json"


class GateError(Exception):
    """Falha de um gate individual, com codigo e detalhes."""

    def __init__(self, code: str, message: str, details: list[str] | None = None):
        self.code = code
        self.message = message
        self.details = details or []
        super().__init__(message)


def _run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _git(root: str, *args: str) -> str:
    proc = _run(["git", "-C", root, *args])
    if proc.returncode != 0:
        raise GateError("GIT_FALHOU", f"git {' '.join(args)} falhou: {proc.stderr.strip()}")
    return proc.stdout


def _resolve_root(root: str) -> str:
    proc = _run(["git", "-C", root, "rev-parse", "--show-toplevel"])
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    return os.path.realpath(os.path.abspath(root))


# ---------------------------------------------------------------------------
# Gate 1 - Higiene Git e invariante autoPublish
# ---------------------------------------------------------------------------
def gate_higiene_git(root: str) -> dict:
    tracked_media = []
    for pattern in MEDIA_EXTENSIONS:
        out = _git(root, "ls-files", "--", pattern)
        tracked_media.extend(line.strip() for line in out.splitlines() if line.strip())

    others_media = []
    for pattern in MEDIA_EXTENSIONS:
        out = _git(root, "ls-files", "--others", "--exclude-standard", "--", pattern)
        others_media.extend(line.strip() for line in out.splitlines() if line.strip())

    indexed = [line.strip() for line in _git(root, "ls-files").splitlines() if line.strip()]
    snapshots = [path for path in indexed if _is_snapshot_zip(path)]

    problems: list[dict] = []
    if tracked_media:
        problems.append({"code": "MIDIA_RASTREADA", "message": "midia rastreada: " + ", ".join(tracked_media)})
    if others_media:
        problems.append(
            {"code": "MIDIA_NAO_IGNORADA", "message": "fora do Git Ignore: " + ", ".join(others_media)}
        )
    if snapshots:
        problems.append({"code": "SNAPSHOT_RASTREADO", "message": "snapshot versionado: " + ", ".join(snapshots)})

    auto_publish_true = _find_auto_publish_true(root)
    if auto_publish_true:
        problems.append(
            {
                "code": "AUTO_PUBLISH_ATIVO",
                "message": "autoPublish:true em: " + ", ".join(auto_publish_true),
            }
        )

    return {
        "ok": not problems,
        "trackedMedia": tracked_media,
        "unignoredMedia": others_media,
        "trackedSnapshots": snapshots,
        "autoPublishTrue": auto_publish_true,
        "problems": problems,
    }


def _is_snapshot_zip(rel_path: str) -> bool:
    norm = rel_path.replace("\\", "/").lower()
    if norm.startswith(".workspace/snapshots/"):
        return True
    base = norm.rsplit("/", 1)[-1]
    if base == "snapshot-index.json" or base.startswith("workspace-snapshot-"):
        return True
    return norm.endswith(".zip") and "snapshot" in norm


def _find_auto_publish_true(root: str) -> list[str]:
    indexed = [line.strip() for line in _git(root, "ls-files", "--", "*.json").splitlines() if line.strip()]
    offenders: list[str] = []
    for rel in indexed:
        norm = rel.replace("\\", "/")
        parts = norm.split("/")
        if any(part in EXCLUDED_DIRS for part in parts):
            continue
        abs_path = os.path.join(root, rel)
        try:
            with open(abs_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        if _has_auto_publish_true(data):
            offenders.append(rel)
    return offenders


def _has_auto_publish_true(node: object) -> bool:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "autoPublish" and value is True:
                return True
            if _has_auto_publish_true(value):
                return True
    elif isinstance(node, list):
        return any(_has_auto_publish_true(item) for item in node)
    return False


# ---------------------------------------------------------------------------
# Gates 2 a 7 - execucao de ferramentas e suites
# ---------------------------------------------------------------------------
def _npm_command() -> str:
    """Resolve o executavel do npm de forma portavel (npm.cmd no Windows)."""
    if os.name == "nt":
        return "npm.cmd"
    return "npm"


def gate_typescript(root: str) -> dict:
    platform_dir = os.path.join(root, "platform")
    npm = _npm_command()
    build = _run([npm, "run", "build"], cwd=platform_dir)
    if build.returncode != 0:
        raise GateError(
            "TS_BUILD_FALHOU",
            "npm run build reprovou",
            (build.stdout + build.stderr).strip().splitlines()[-10:],
        )
    test = _run([npm, "test"], cwd=platform_dir)
    if test.returncode != 0:
        raise GateError(
            "TS_TEST_FALHOU",
            "npm test reprovou",
            (test.stdout + test.stderr).strip().splitlines()[-10:],
        )
    return {"ok": True, "build": "ok", "test": "ok"}


def gate_tenant_validator(root: str) -> dict:
    proc = _run([sys.executable, "tools/tenant_validator.py", "--all", "--json"], cwd=root)
    return _wrap_tool("TENANT_VALIDATOR", "tenant_validator", proc)


def gate_editorial_qa(root: str) -> dict:
    proc = _run(
        [sys.executable, "tools/editorial_qa.py", "--all", "--strict", "--json"], cwd=root
    )
    return _wrap_tool("EDITORIAL_QA", "editorial_qa", proc)


def gate_workspace_doctor(root: str) -> dict:
    proc = _run([sys.executable, "tools/workspace_doctor.py", "--check", "--json"], cwd=root)
    return _wrap_tool("WORKSPACE_DOCTOR", "workspace_doctor", proc)


def gate_release_audit(root: str) -> dict:
    proc = _run([sys.executable, "tools/release_audit.py", "--strict", "--json"], cwd=root)
    return _wrap_tool("RELEASE_AUDIT", "release_audit", proc)


def gate_bundling(root: str) -> dict:
    proc = _run(
        [sys.executable, "tools/publish_bundler.py", "verify", "--json"], cwd=root
    )
    return _wrap_tool("BUNDLING", "publish_bundler verify", proc)


def gate_e2e(root: str) -> dict:
    proc = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests/e2e", "-v"], cwd=root)
    ok = proc.returncode == 0
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-8:]
    result = {"ok": ok, "returncode": proc.returncode, "tail": tail}
    if not ok:
        raise GateError("E2E_FALHOU", "suite E2E reprovou", tail)
    return result


def _wrap_tool(error_code: str, name: str, proc: subprocess.CompletedProcess) -> dict:
    payload = None
    stdout = proc.stdout.strip()
    if stdout:
        try:
            payload = json.loads(stdout)
        except ValueError:
            payload = None
    ok = proc.returncode == 0 and (payload is None or payload.get("ok") is not False)
    result = {"ok": ok, "returncode": proc.returncode}
    if payload is not None:
        result["report"] = _summarize_report(payload)
    if not ok:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-8:]
        raise GateError(error_code, f"{name} reprovou", tail)
    return result


def _summarize_report(payload: dict) -> dict:
    summary = {}
    if "tenants" in payload and isinstance(payload["tenants"], list):
        summary["tenants"] = len(payload["tenants"])
    if "summary" in payload and isinstance(payload["summary"], dict):
        summary["checks"] = payload["summary"].get("checks") or payload["summary"].get("domains")
    return summary


# ---------------------------------------------------------------------------
# Orquestracao
# ---------------------------------------------------------------------------
GATES = (
    ("higiene_git", gate_higiene_git),
    ("typescript", gate_typescript),
    ("tenant_validator", gate_tenant_validator),
    ("editorial_qa", gate_editorial_qa),
    ("workspace_doctor", gate_workspace_doctor),
    ("release_audit", gate_release_audit),
    ("bundling", gate_bundling),
    ("e2e", gate_e2e),
)

GATE_LABELS = {
    "higiene_git": "Higiene Git e autoPublish",
    "typescript": "Build e testes TypeScript (platform)",
    "tenant_validator": "Contratos multi-tenant (5 tenants)",
    "editorial_qa": "Qualidade editorial (14 campanhas, 7 lentes)",
    "workspace_doctor": "Saude do workspace",
    "release_audit": "Auditoria de release (8 dominios)",
    "bundling": "Empacotamento de distribuicao (.workspace/bundles)",
    "e2e": "Suite E2E da fabrica",
}


def run_all(root: str, skip_ts: bool = False) -> dict:
    results: list[dict] = []
    overall_ok = True
    for gate_id, gate_fn in GATES:
        if gate_id == "typescript" and skip_ts:
            results.append({"id": gate_id, "name": GATE_LABELS[gate_id], "status": "skipped"})
            continue
        try:
            detail = gate_fn(root)
            results.append({"id": gate_id, "name": GATE_LABELS[gate_id], "status": "ok", "detail": detail})
        except GateError as exc:
            overall_ok = False
            results.append(
                {
                    "id": gate_id,
                    "name": GATE_LABELS[gate_id],
                    "status": "fail",
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            )
            break
        except Exception as exc:  # noqa: BLE001 - falha inesperada vira gate reprovado
            overall_ok = False
            results.append(
                {
                    "id": gate_id,
                    "name": GATE_LABELS[gate_id],
                    "status": "fail",
                    "code": "ERRO_INESPERADO",
                    "message": str(exc),
                }
            )
            break
    return {
        "schemaVersion": 1,
        "ok": overall_ok,
        "root": root,
        "skipTs": skip_ts,
        "gates": results,
        "totalGates": len(GATES),
        "passedGates": sum(1 for r in results if r["status"] in ("ok", "skipped")),
    }


def _print_human(report: dict) -> None:
    print("Verificacao de release da fabrica multi-tenant")
    print("=" * 48)
    for gate in report["gates"]:
        label = gate["name"]
        status = gate["status"]
        if status == "ok":
            print(f"[OK]      {label}")
        elif status == "skipped":
            print(f"[SKIP]    {label}")
        else:
            print(f"[FALHOU]  {label}: {gate.get('message', '')}")
            for line in gate.get("details", []):
                print(f"          {line}")
    print("-" * 48)
    verdict = "APROVADO" if report["ok"] else "REPROVADO"
    print(f"Resultado: {verdict} ({report['passedGates']}/{report['totalGates']} gates)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Comando unico de verificacao de release (7 gates, 100% stdlib)"
    )
    parser.add_argument("--json", action="store_true", help="emite o relatorio em JSON no stdout")
    parser.add_argument(
        "--skip-ts",
        action="store_true",
        help="pula build e testes TypeScript em platform/",
    )
    parser.add_argument("--root", default=os.getcwd(), help="raiz do checkout")
    args = parser.parse_args(argv)

    root = _resolve_root(args.root)
    report = run_all(root, skip_ts=args.skip_ts)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_human(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())