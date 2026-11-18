"""Validador de contratos multi-tenant (brand-kit, guardrails e fixtures).

Implementado 100% com biblioteca padrao Python para execucao deterministica no
CI (Ubuntu/Windows) e reutilizacao direta pelo executor de presets do Agente 2
(`tools/preset_runner.py`).

Uso (a partir da raiz do checkout):
    python tools/tenant_validator.py --all --json
    python tools/tenant_validator.py --tenant marca-salao --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import render_local

TENANT_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

FORBIDDEN_FIXTURE_PLACEHOLDERS = (
    ("lorem_ipsum", re.compile(r"lorem\s+ipsum", re.IGNORECASE)),
    ("generic_user1", re.compile(r"\buser[-_\s]*1\b", re.IGNORECASE)),
    ("generic_test_user", re.compile(r"\btest[-_\s]*(user|client|cliente)\b", re.IGNORECASE)),
    ("e2e_namespace", re.compile(r"\be2e-[0-9]+\b", re.IGNORECASE)),
    ("e2e_salon", re.compile(r"\bmeu\s+sal[aã]o\s+e2e\b", re.IGNORECASE)),
    ("e2e_manager", re.compile(r"\bgestor\s+e2e\b", re.IGNORECASE)),
    ("inflated_e2e_price", re.compile(r"12\.000,00")),
)


class TenantContractError(Exception):
    """Erro de validacao de contrato de tenant com codigo estavel."""

    def __init__(self, code: str, errors: list[str] | None = None):
        self.code = code
        self.errors = errors or []
        summary = f"{code}: " + "; ".join(self.errors) if self.errors else code
        super().__init__(summary)


def _contained(root: str, target: str) -> bool:
    return render_local.contained(root, target)


def _load_json_contained(root: str, abs_path: str, label: str) -> dict:
    root_real = os.path.realpath(root)
    resolved = os.path.realpath(abs_path)
    if not _contained(root_real, resolved):
        raise TenantContractError("PATH_OUTSIDE_ROOT", [f"{label} fora da raiz do projeto"])
    fs = render_local.fs_path(resolved)
    if not os.path.isfile(fs):
        raise TenantContractError("FILE_MISSING", [f"{label} ausente: {render_local.rel(root_real, resolved)}"])
    try:
        with open(fs, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise TenantContractError("JSON_INVALID", [f"{label}: {exc}"]) from exc
    if not isinstance(data, dict):
        raise TenantContractError("JSON_ROOT_NOT_OBJECT", [f"{label} deve ter um objeto na raiz"])
    return data


def load_schema(schema_name: str, root: str = ".") -> dict:
    """Carrega um esquema JSON em `<root>/schemas/<schema_name>`."""
    schema_abs = os.path.join(os.path.realpath(root), "schemas", schema_name)
    return _load_json_contained(root, schema_abs, f"schema:{schema_name}")


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def validate_against_schema(data: Any, schema: dict, path: str = "$") -> list[str]:
    """Validador recursivo leve de JSON Schema em Python stdlib."""
    errors: list[str] = []

    expected_type = schema.get("type")
    if expected_type is not None and not _matches_type(data, expected_type):
        return [f"{path}: tipo esperado '{expected_type}', recebido '{type(data).__name__}'"]

    if "const" in schema and data != schema["const"]:
        errors.append(f"{path}: valor deve ser exatamente {schema['const']!r}")

    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: valor {data!r} fora do enum permitido {schema['enum']!r}")

    if isinstance(data, str):
        if "minLength" in schema and len(data) < int(schema["minLength"]):
            errors.append(f"{path}: comprimento {len(data)} < minimo {schema['minLength']}")
        if "maxLength" in schema and len(data) > int(schema["maxLength"]):
            errors.append(f"{path}: comprimento {len(data)} > maximo {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], data):
            errors.append(f"{path}: valor '{data}' nao corresponde ao padrao '{schema['pattern']}'")

    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{path}: valor {data} < minimo {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{path}: valor {data} > maximo {schema['maximum']}")

    if isinstance(data, list):
        if "minItems" in schema and len(data) < int(schema["minItems"]):
            errors.append(f"{path}: quantidade {len(data)} < minimo {schema['minItems']}")
        if "maxItems" in schema and len(data) > int(schema["maxItems"]):
            errors.append(f"{path}: quantidade {len(data)} > maximo {schema['maxItems']}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for idx, item in enumerate(data):
                errors.extend(validate_against_schema(item, item_schema, f"{path}[{idx}]"))

    if isinstance(data, dict):
        for req_key in schema.get("required", []):
            if req_key not in data:
                errors.append(f"{path}.{req_key}: campo obrigatorio ausente")
        props = schema.get("properties", {})
        addl = schema.get("additionalProperties", True)
        for key, val in data.items():
            if key in props:
                errors.extend(validate_against_schema(val, props[key], f"{path}.{key}"))
            elif addl is False:
                errors.append(f"{path}.{key}: propriedade adicional nao permitida")
            elif isinstance(addl, dict):
                errors.extend(validate_against_schema(val, addl, f"{path}.{key}"))

    return errors


def validate_brand_kit(brand_kit: dict, root: str = ".") -> list[str]:
    """Valida um dicionario `brand-kit.json` contra `schemas/brand-kit.schema.json`."""
    schema = load_schema("brand-kit.schema.json", root=root)
    return validate_against_schema(brand_kit, schema, path="brandKit")


def validate_guardrails_contract(guardrails: dict, root: str = ".") -> list[str]:
    """Valida um dicionario `guardrails.json` contra `schemas/guardrails.schema.json`."""
    schema = load_schema("guardrails.schema.json", root=root)
    return validate_against_schema(guardrails, schema, path="guardrails")


def _strip_editorial_footer(text: str) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        lowered = line.strip().lower()
        if lowered.startswith("observação editorial:") or lowered.startswith("observacao editorial:"):
            break
        kept.append(line)
    return "\n".join(kept)


def _match_forbidden_term(term: str, content: str) -> str | None:
    stripped = term.strip()
    if not stripped:
        return None
    if len(stripped) <= 4 and re.match(r"^[A-Za-z0-9]+$", stripped):
        pat = re.compile(rf"(?<!\w){re.escape(stripped)}(?!\w)", re.IGNORECASE)
    else:
        pat = re.compile(re.escape(stripped), re.IGNORECASE)
    match = pat.search(content)
    return match.group(0) if match else None


def validate_text_against_guardrails(
    text: str,
    guardrails: dict,
    check_ui_elements: bool = False,
    ignore_editorial_footer: bool = True,
) -> list[str]:
    """Verifica um texto (roteiro/SRT/narracao/UI) contra `forbiddenClaims` e UI proibida."""
    content = _strip_editorial_footer(text) if ignore_editorial_footer else text
    violations: list[str] = []

    for claim in guardrails.get("forbiddenClaims", []):
        matched = _match_forbidden_term(str(claim), content)
        if matched:
            violations.append(f"CLAIM_FORBIDDEN: termo vetado '{matched}' (regra '{claim}')")

    if check_ui_elements:
        for ui_el in guardrails.get("forbiddenUiElements", []):
            matched = _match_forbidden_term(str(ui_el), content)
            if matched:
                violations.append(f"UI_FORBIDDEN: elemento vetado '{matched}' (regra '{ui_el}')")

    return violations


def validate_fixture_data(fixture_data: dict, tenant_id: str | None = None) -> list[str]:
    """Confirma que a fixture editorial nao possui placeholders tecnicos/genericos."""
    errors: list[str] = []
    if not isinstance(fixture_data, dict) or not fixture_data:
        return ["FIXTURE_EMPTY: fixture deve ser um objeto JSON nao vazio"]

    # Verifica tenantId explicito quando declarado na fixture
    if tenant_id and fixture_data.get("tenantId") and fixture_data.get("tenantId") != tenant_id:
        errors.append(
            f"FIXTURE_TENANT_MISMATCH: tenantId '{fixture_data.get('tenantId')}' diverge de '{tenant_id}'"
        )

    serialized = json.dumps(fixture_data, ensure_ascii=False)
    for code, pattern in FORBIDDEN_FIXTURE_PLACEHOLDERS:
        m = pattern.search(serialized)
        if m:
            errors.append(f"FIXTURE_PLACEHOLDER_{code.upper()}: '{m.group(0)}' proibido em fixture editorial")
    return errors


def resolve_tenant_fixture_path(tenant_dir: str, tenant_id: str) -> str | None:
    """Localiza a fixture principal em `tenants/<tenantId>/fixtures/`."""
    fixtures_dir = os.path.join(tenant_dir, "fixtures")
    if not os.path.isdir(render_local.fs_path(fixtures_dir)):
        return None
    preferred = os.path.join(fixtures_dir, f"fixture-editorial-{tenant_id}.json")
    if os.path.isfile(render_local.fs_path(preferred)):
        return preferred
    candidates = sorted(
        f for f in os.listdir(render_local.fs_path(fixtures_dir))
        if f.endswith(".json")
    )
    if not candidates:
        return None
    return os.path.join(fixtures_dir, candidates[0])


def list_tenants(root: str = ".") -> list[str]:
    """Lista todos os slugs de tenant presentes sob `<root>/tenants/`."""
    tenants_dir = os.path.realpath(os.path.join(root, "tenants"))
    if not os.path.isdir(render_local.fs_path(tenants_dir)):
        return []
    return sorted(
        name for name in os.listdir(render_local.fs_path(tenants_dir))
        if os.path.isdir(render_local.fs_path(os.path.join(tenants_dir, name)))
    )


def load_and_validate_tenant(tenant_id: str, root: str = ".", strict: bool = True) -> dict:
    """Carrega e valida brand-kit, guardrails e fixture de um tenant.

    Ponto de entrada recomendado para o Agente 2 (`tools/preset_runner.py`).
    """
    root_real = os.path.realpath(root)
    if not TENANT_ID_RE.match(str(tenant_id)):
        raise TenantContractError("TENANT_ID_INVALID", [f"slug invalido: '{tenant_id}'"])

    tenant_dir = os.path.realpath(os.path.join(root_real, "tenants", tenant_id))
    if not _contained(root_real, tenant_dir):
        raise TenantContractError("PATH_OUTSIDE_ROOT", [f"tenant fora da raiz: {tenant_id}"])
    if not os.path.isdir(render_local.fs_path(tenant_dir)):
        raise TenantContractError("TENANT_NOT_FOUND", [f"diretorio ausente: tenants/{tenant_id}"])

    brand_kit_abs = os.path.join(tenant_dir, "brand-kit.json")
    guardrails_abs = os.path.join(tenant_dir, "guardrails.json")

    brand_kit = _load_json_contained(root_real, brand_kit_abs, f"tenants/{tenant_id}/brand-kit.json")
    guardrails = _load_json_contained(root_real, guardrails_abs, f"tenants/{tenant_id}/guardrails.json")

    errors: list[str] = []
    errors.extend(validate_brand_kit(brand_kit, root=root_real))
    errors.extend(validate_guardrails_contract(guardrails, root=root_real))

    if brand_kit.get("tenantId") != tenant_id:
        errors.append(f"brandKit.tenantId '{brand_kit.get('tenantId')}' diverge da pasta '{tenant_id}'")
    if guardrails.get("tenantId") != tenant_id:
        errors.append(f"guardrails.tenantId '{guardrails.get('tenantId')}' diverge da pasta '{tenant_id}'")

    fixture_abs = resolve_tenant_fixture_path(tenant_dir, tenant_id)
    fixture_data: dict = {}
    if not fixture_abs:
        errors.append(f"fixture ausente em tenants/{tenant_id}/fixtures/")
    else:
        fixture_data = _load_json_contained(
            root_real, fixture_abs, render_local.rel(root_real, fixture_abs)
        )
        errors.extend(validate_fixture_data(fixture_data, tenant_id=tenant_id))

    if errors and strict:
        raise TenantContractError("TENANT_VALIDATION_FAILED", errors)

    return {
        "ok": len(errors) == 0,
        "tenantId": tenant_id,
        "brandKit": brand_kit,
        "guardrails": guardrails,
        "fixture": fixture_data,
        "brandKitPath": render_local.rel(root_real, brand_kit_abs),
        "guardrailsPath": render_local.rel(root_real, guardrails_abs),
        "fixturePath": render_local.rel(root_real, fixture_abs) if fixture_abs else None,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validador de contratos multi-tenant")
    parser.add_argument("--tenant", help="Slug do tenant sob tenants/<tenantId>")
    parser.add_argument("--all", action="store_true", help="Valida todos os tenants registrados")
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument("--json", action="store_true", help="Emite JSON no stdout")
    args = parser.parse_args(argv)

    if not args.all and not args.tenant:
        print("Erro: informe --tenant <id> ou --all", file=sys.stderr)
        return 2

    targets = list_tenants(args.root) if args.all else [args.tenant]
    results = []
    has_failure = False
    for tid in targets:
        try:
            res = load_and_validate_tenant(tid, root=args.root, strict=False)
            results.append({
                "ok": res["ok"],
                "tenantId": tid,
                "brandKitPath": res["brandKitPath"],
                "guardrailsPath": res["guardrailsPath"],
                "fixturePath": res["fixturePath"],
                "errors": res["errors"],
            })
            if not res["ok"]:
                has_failure = True
        except TenantContractError as exc:
            has_failure = True
            results.append({"ok": False, "tenantId": tid, "code": exc.code, "errors": exc.errors})

    if args.json:
        print(json.dumps({"ok": not has_failure, "tenants": results}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            status = "OK" if r["ok"] else "FALHOU"
            print(f"[{status}] {r['tenantId']}: {len(r['errors'])} erro(s)")
            for err in r["errors"]:
                print(f"  - {err}")
    return 1 if has_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
