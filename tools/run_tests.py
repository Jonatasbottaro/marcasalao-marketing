"""Runner deterministico da suite de testes da fabrica, particionada por custo.

Os modulos de ``tools/tests/`` sao classificados explicitamente em dois grupos:

  ``fast``    testes unitarios e de contrato puros. Nao invocam FFmpeg/FFprobe
              para renderizar midia; sao o gate padrao de ``release_check.py``.
  ``render``  testes que renderizam video/audio de verdade via FFmpeg/FFprobe.
              Sao lentos e exigem as ferramentas portateis instaladas.

Dentro de ``fast`` ha uma faixa mais estreita para o loop de desenvolvimento:

  ``smoke``   ``fast`` menos ``HEAVY_CONTRACT_MODULES`` — os modulos que criam
              sandboxes Git completos, inicializam ponte Node/MCP ou sobem
              servidores HTTP locais. Nao renderizam midia, mas dominam o tempo
              do gate completo; ficam fora do ``smoke`` e dentro do ``fast``.

A partição é fechada: um modulo ``test_*.py`` novo e nao classificado reprova o
runner com erro de uso, em vez de cair silenciosamente em um grupo padrao.
``smoke`` e derivado de ``fast``, portanto nunca diverge da classificacao.

Blindagem de ``.workspace/archives/``: toda execucao — em qualquer faixa — roda
dentro de ``archives_guard.ArchivesGuard``, que fotografa os SHA-256 dos masters
antes do run e restaura qualquer arquivo alterado ao final. Assim, mesmo um
teste que esqueca ``archives_dir`` isolado nao corrompe a midia real.

CLI (as quatro faixas sao mutuamente exclusivas):
    python tools/run_tests.py [--smoke | --fast | --render | --all] [--json] [--root DIR]

Sem flag de grupo, o padrao e ``--fast``. ``--all`` equivale a ``fast + render``.
O payload JSON traz ``ok``, ``mode`` (smoke/fast/render/all), ``total``,
``passed``, ``failed``, ``errors``, ``skipped``, ``durationSeconds`` e ``modules``.

API:
    partition_modules(root=".") -> dict   # smoke/fast/render/unclassified/absent
    resolve_groups(flags) -> tuple
    run_tests(root=".", groups=("fast",)) -> dict

Exit codes: 0 todos os testes aprovados; 1 falha/erro de teste; 2 erro de uso.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import archives_guard  # noqa: E402

SCHEMA_VERSION = 1
GENERATED_BY = "tools/run_tests.py"
TESTS_REL = ("tools", "tests")
GROUPS = ("fast", "render")
DEFAULT_GROUPS = ("fast",)
WORKER_FLAG = "--_worker"

FAST_MODULES = (
    "test_approval_cli",
    "test_bootstrap_ffmpeg",
    "test_build_video",
    "test_bundle_attribution",
    "test_campaign_calendar",
    "test_delivery_verify",
    "test_tenant_scaffolder",
    "test_devlog_sync",
    "test_editorial_qa",
    "test_executive_summary",
    "test_handoff_bundler",
    "test_hook_promotion_cli",
    "test_ns002_pilot",
    "test_publish_bundler",
    "test_publish_pack",
    "test_release_audit",
    "test_review_dashboard",
    "test_run_tests",
    "test_srt_formatter",
    "test_srt_validate",
    "test_static_cards",
    "test_studio_astryx_frontend",
    "test_studio_connections",
    "test_studio_mcp",
    "test_tenant_contracts",
    "test_utm_report_importer",
    "test_utm_simulator",
    "test_workspace_doctor",
    "test_workspace_doctor_repair",
)

RENDER_MODULES = (
    "test_audio_tts",
    "test_campaign_proof",
    "test_campaign_studio_e2e",
    "test_derivative_formats",
    "test_factory_cli",
    "test_multi_format",
    "test_preset_runner",
    "test_produce_carousel",
    "test_produce_video",
    "test_queue_process_restart",
    "test_r002_pilot",
    "test_recording_cuts",
    "test_render_local",
    "test_render_pipeline",
    "test_scene_framing_preview",
    "test_studio_media",
    "test_studio_preflight",
    "test_studio_queue",
    "test_studio_templates",
    "test_studio_video_api",
    "test_studio_work_backup",
    "test_video_studio",
)


class RunTestsError(Exception):
    """Erro de uso do runner (particao incompleta, grupo invalido)."""


# Modulos de contrato que, apesar de nao renderizarem midia, sao caros: criam
# sandboxes Git completos, inicializam ponte Node/MCP ou sobem servidores HTTP
# locais. Ficam em ``fast`` (gate oficial) mas fora de ``smoke`` (loop de dev).
HEAVY_CONTRACT_MODULES = (
    "test_release_audit",
    "test_studio_mcp",
    "test_studio_connections",
    "test_editorial_qa",
)

# Derivada de FAST_MODULES para nunca divergir quando a classificacao mudar.
SMOKE_MODULES = tuple(m for m in FAST_MODULES if m not in HEAVY_CONTRACT_MODULES)

SELECTABLE = ("smoke",) + GROUPS


def tests_dir(root: str = ".") -> str:
    return os.path.join(os.path.realpath(root), *TESTS_REL)


def partition_modules(root: str = ".") -> dict:
    """Classifica os modulos presentes em disco e aponta os nao classificados."""
    directory = tests_dir(root)
    present = sorted(
        name[:-3]
        for name in os.listdir(archives_guard.fs_path(directory))
        if name.startswith("test_") and name.endswith(".py")
    )
    known = set(FAST_MODULES) | set(RENDER_MODULES)
    return {
        "smoke": [m for m in present if m in SMOKE_MODULES],
        "fast": [m for m in present if m in FAST_MODULES],
        "render": [m for m in present if m in RENDER_MODULES],
        "unclassified": [m for m in present if m not in known],
        "absent": sorted(known - set(present)),
    }


def resolve_groups(flags: dict) -> tuple[str, ...]:
    if flags.get("all"):
        return GROUPS
    if flags.get("smoke"):
        return ("smoke",)
    selected = tuple(g for g in GROUPS if flags.get(g))
    return selected or DEFAULT_GROUPS


def _worker(names: list[str], directory: str) -> int:
    """Executa os modulos em processo filho e emite o resultado em JSON."""
    import unittest

    sys.path.insert(0, directory)
    started = time.perf_counter()
    suite = unittest.TestLoader().loadTestsFromNames(names)
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2).run(suite)
    payload = {
        "total": result.testsRun,
        "failed": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "expectedFailures": len(result.expectedFailures),
        "unexpectedSuccesses": len(result.unexpectedSuccesses),
        "durationSeconds": round(time.perf_counter() - started, 3),
        "ok": result.wasSuccessful(),
        "failureNames": [str(case) for case, _ in result.failures + result.errors],
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return 0 if result.wasSuccessful() else 1


def _run_group(group: str, names: list[str], root: str) -> dict:
    directory = tests_dir(root)
    proc = subprocess.run(
        [sys.executable, os.path.abspath(__file__), WORKER_FLAG, *names],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    payload: dict = {}
    for line in reversed((proc.stdout or "").splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                payload = json.loads(line)
            except ValueError:
                payload = {}
            break
    if not payload:
        payload = {
            "total": 0,
            "failed": 0,
            "errors": 1,
            "skipped": 0,
            "durationSeconds": 0.0,
            "ok": False,
            "failureNames": [f"{group}: worker sem resultado (rc={proc.returncode})"],
        }
    tail = (proc.stderr or "").strip().splitlines()[-12:]
    return {
        "group": group,
        "modules": list(names),
        "totalModules": len(names),
        "returncode": proc.returncode,
        "tail": tail,
        **payload,
    }


def run_tests(root: str = ".", groups: tuple[str, ...] = DEFAULT_GROUPS) -> dict:
    """Executa os grupos escolhidos sob blindagem de ``.workspace/archives/``."""
    root_real = os.path.realpath(root)
    unknown = [g for g in groups if g not in SELECTABLE]
    if unknown:
        raise RunTestsError(f"grupo invalido: {', '.join(unknown)}")
    partition = partition_modules(root_real)
    if partition["unclassified"]:
        raise RunTestsError(
            "modulos sem classificacao em FAST_MODULES/RENDER_MODULES: "
            + ", ".join(partition["unclassified"])
        )

    started = time.perf_counter()
    results: list[dict] = []
    with archives_guard.ArchivesGuard(root_real, name="run-tests") as guard:
        for group in SELECTABLE:
            if group not in groups:
                continue
            names = partition[group]
            if not names:
                continue
            results.append(_run_group(group, names, root_real))

    totals = {
        key: sum(r.get(key, 0) for r in results)
        for key in ("total", "failed", "errors", "skipped")
    }
    passed = totals["total"] - totals["failed"] - totals["errors"] - totals["skipped"]
    selected = [g for g in SELECTABLE if g in groups]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedBy": GENERATED_BY,
        "ok": all(r.get("ok") for r in results) and guard.report["ok"],
        "root": root_real,
        "mode": "all" if set(selected) == set(GROUPS) else "+".join(selected),
        "total": totals["total"],
        "passed": passed,
        "failed": totals["failed"],
        "errors": totals["errors"],
        "skipped": totals["skipped"],
        "durationSeconds": round(time.perf_counter() - started, 3),
        "modules": [m for r in results for m in r["modules"]],
        "results": results,
        "archivesGuard": guard.report,
        "partition": {g: partition[g] for g in SELECTABLE},
    }


def _print_human(report: dict) -> None:
    print("Suite de testes da fabrica multi-tenant")
    print("=" * 48)
    for result in report["results"]:
        verdict = "OK" if result.get("ok") else "FALHOU"
        print(
            f"[{verdict:6}] {result['group']:6} "
            f"{result.get('total', 0)} testes, "
            f"{result.get('failed', 0)} falhas, "
            f"{result.get('errors', 0)} erros, "
            f"{result.get('skipped', 0)} pulados "
            f"({result.get('durationSeconds', 0)}s, {result['totalModules']} modulos)"
        )
        if not result.get("ok"):
            for name in result.get("failureNames", []):
                print(f"          - {name}")
    guard = report["archivesGuard"]
    print("-" * 48)
    print(
        f"archives: {guard['filesBefore']} masters fotografados, "
        f"{len(guard['restored'])} restaurados, {len(guard['discarded'])} descartados"
    )
    for rel in guard["restored"]:
        print(f"          restaurado: {rel}")
    verdict = "APROVADO" if report["ok"] else "REPROVADO"
    print(
        f"Resultado: {verdict} — {report['passed']}/{report['total']} aprovados "
        f"em {report['durationSeconds']}s"
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == WORKER_FLAG:
        return _worker(argv[1:], os.path.join(os.getcwd(), *TESTS_REL))

    parser = argparse.ArgumentParser(
        description="Runner deterministico da suite (smoke/fast/render/all), 100% stdlib"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--smoke", action="store_true",
                      help="loop de dev: fast sem os 4 modulos de contrato pesados")
    mode.add_argument("--fast", action="store_true", help="testes unitarios e de contrato (padrao)")
    mode.add_argument("--render", action="store_true", help="testes que renderizam via FFmpeg")
    mode.add_argument("--all", action="store_true", help="fast + render")
    parser.add_argument("--json", action="store_true", help="emite o relatorio em JSON no stdout")
    parser.add_argument("--root", default=os.getcwd(), help="raiz do checkout")
    args = parser.parse_args(argv)

    groups = resolve_groups({
        "smoke": args.smoke, "fast": args.fast, "render": args.render, "all": args.all,
    })
    try:
        report = run_tests(args.root, groups)
    except RunTestsError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_human(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())