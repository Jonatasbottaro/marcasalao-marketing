#!/usr/bin/env python3
"""Offline integrity verification for the repository-local EGM installation.

Checks that the canonical Elephant-Goldfish Model bundle under
`.agents/plugins/egm/` is complete, has valid manifests, contains no symlinks,
resolves internal relative links, and is wired into `AGENTS.md`, `CLAUDE.md`,
and `docs/designs/`.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

EXPECTED_SKILLS = (
    "egm-bootstrap",
    "egm-brainstorm",
    "egm-draft",
    "egm-drift-report",
    "egm-lite",
    "egm-resolve",
    "egm-review",
    "egm-review-loop",
)

EXPECTED_AGENTS = (
    "bootstrap_orchestrator",
    "codebase_details",
    "comprehension",
    "design_critic",
    "implementation_readiness",
    "inventive_catalyst",
    "structural",
    "style",
    "synthesizer",
    "zoom_out",
)

EXPECTED_STANDARDS = (
    "feature-spec-standard.md",
    "heilmeier-standard.md",
    "implementation-readiness-standard.md",
    "re-implementation-standard.md",
    "zoom-out-standard.md",
)

EXPECTED_DOCS = (
    "index.md",
    "getting_started.md",
    "harnesses.md",
    "claude.md",
    "codex.md",
    "opencode.md",
    "cursor.md",
    "copilot.md",
    "muse.md",
    "faq.md",
    "privacy.md",
    "releases.md",
)

REQUIRED_REFERENCES = (
    "skills/egm-bootstrap/references/worker-return.schema.json",
    "skills/egm-bootstrap/references/templates.md",
    "skills/egm-draft/references/design_doc.md",
)

ARTIFACT_DIRECTIVE = "EGM artifact directory: .workspace/tmp/egm"
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def check_installation(repo_root: pathlib.Path) -> list[str]:
    errors: list[str] = []
    bundle = repo_root / ".agents" / "plugins" / "egm"

    if not bundle.is_dir():
        return [f"Missing EGM bundle directory: {bundle}"]

    # 1. No symlinks inside bundle
    for path in bundle.rglob("*"):
        if path.is_symlink():
            errors.append(f"Symlink found inside EGM bundle: {path.relative_to(repo_root)}")

    # 2. Core root files
    for rel in (
        "plugin.json",
        "LICENSE",
        "README.md",
        "TESTING.md",
        "assets/icon.svg",
        "resources/README.md",
        "resources/execution_instructions.md",
        "adapters/opencode/install.py",
    ):
        if not (bundle / rel).is_file():
            errors.append(f"Missing required bundle file: .agents/plugins/egm/{rel}")

    # 3. Skills and references
    for skill in EXPECTED_SKILLS:
        for rel in ("SKILL.md", "agents/openai.yaml", "assets/icon.svg"):
            target = bundle / "skills" / skill / rel
            if not target.is_file():
                errors.append(f"Missing skill file: {target.relative_to(repo_root)}")

    for rel in REQUIRED_REFERENCES:
        if not (bundle / rel).is_file():
            errors.append(f"Missing skill reference: .agents/plugins/egm/{rel}")

    # 4. Agents and frontmatter names
    for agent in EXPECTED_AGENTS:
        target = bundle / "agents" / f"{agent}.md"
        if not target.is_file():
            errors.append(f"Missing agent persona: {target.relative_to(repo_root)}")
        else:
            text = target.read_text(encoding="utf-8")
            parts = text.split("---", 2)
            if len(parts) < 3 or not re.search(r"^name:\s*egm-[a-z-]+$", parts[1], re.MULTILINE):
                errors.append(f"Invalid frontmatter name in agent persona: {target.relative_to(repo_root)}")

    # 5. Document standards & docs
    for std in EXPECTED_STANDARDS:
        if not (bundle / "resources" / "document_standards" / std).is_file():
            errors.append(f"Missing document standard: .agents/plugins/egm/resources/document_standards/{std}")

    for doc in EXPECTED_DOCS:
        if not (bundle / "docs" / doc).is_file():
            errors.append(f"Missing harness/guide doc: .agents/plugins/egm/docs/{doc}")

    # 6. Manifests JSON & consistency
    canonical_path = bundle / "plugin.json"
    canonical: dict[str, object] = {}
    try:
        canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
        if canonical.get("name") != "egm":
            errors.append(f"Unexpected plugin.json name: {canonical.get('name')!r}")
    except Exception as exc:
        errors.append(f"Invalid JSON in plugin.json: {exc}")

    for manifest_rel in (
        ".codex-plugin/plugin.json",
        ".claude-plugin/plugin.json",
        ".cursor-plugin/plugin.json",
    ):
        mpath = bundle / manifest_rel
        if not mpath.is_file():
            errors.append(f"Missing compatibility manifest: .agents/plugins/egm/{manifest_rel}")
            continue
        try:
            data = json.loads(mpath.read_text(encoding="utf-8"))
            if canonical and data.get("name") != canonical.get("name"):
                errors.append(f"Manifest name mismatch in {manifest_rel}")
            if canonical and data.get("version") != canonical.get("version"):
                errors.append(f"Manifest version mismatch in {manifest_rel}")
        except Exception as exc:
            errors.append(f"Invalid JSON in {manifest_rel}: {exc}")

    marketplace_path = repo_root / ".agents" / "plugins" / "marketplace.json"
    if not marketplace_path.is_file():
        errors.append("Missing workspace marketplace catalog: .agents/plugins/marketplace.json")
    else:
        try:
            mp = json.loads(marketplace_path.read_text(encoding="utf-8"))
            plugins = mp.get("plugins", [])
            egm_entries = [p for p in plugins if isinstance(p, dict) and p.get("name") == "egm"]
            if not egm_entries:
                errors.append("marketplace.json has no 'egm' plugin entry")
            else:
                src_rel = egm_entries[0].get("source")
                resolved = (marketplace_path.parent / str(src_rel)).resolve()
                if resolved != bundle.resolve():
                    errors.append(
                        f"marketplace.json source {src_rel!r} resolves to {resolved}, expected {bundle.resolve()}"
                    )
        except Exception as exc:
            errors.append(f"Invalid JSON in marketplace.json: {exc}")

    # 7. Relative links inside skills/*/SKILL.md resolve inside bundle
    for skill in EXPECTED_SKILLS:
        skill_md = bundle / "skills" / skill / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")
        # Ignore fenced code blocks and inline code spans (which contain syntax examples)
        cleaned = re.sub(r"```[\s\S]*?```", "", text)
        cleaned = re.sub(r"`[^`]+`", "", cleaned)
        for match in LINK_RE.finditer(cleaned):
            raw_target = match.group(1).strip()
            if (
                not raw_target
                or raw_target.startswith(("http://", "https://", "#", "${", "/"))
                or any(tok in raw_target for tok in ("<", ">", "${", "[", "]"))
            ):
                continue
            target_no_anchor = raw_target.split("#", 1)[0]
            if not target_no_anchor:
                continue
            resolved = (skill_md.parent / target_no_anchor).resolve()
            if not resolved.is_relative_to(bundle.resolve()) or not resolved.exists():
                errors.append(
                    f"Broken relative link in {skill_md.relative_to(repo_root)}: {raw_target!r}"
                )

    # 8. Workspace wiring (AGENTS.md, CLAUDE.md, docs/designs/)
    for doc_rel in ("AGENTS.md", "CLAUDE.md"):
        doc_path = repo_root / doc_rel
        if not doc_path.is_file():
            errors.append(f"Missing instruction file: {doc_rel}")
            continue
        content = doc_path.read_text(encoding="utf-8")
        if ARTIFACT_DIRECTIVE not in content:
            errors.append(f"{doc_rel} missing directive: {ARTIFACT_DIRECTIVE!r}")
        if ".agents/plugins/egm" not in content:
            errors.append(f"{doc_rel} missing reference to '.agents/plugins/egm'")

    for design_rel in ("docs/designs/README.md", "docs/designs/SITEMAP.md", "docs/designs/GUIA-EGM.md"):
        if not (repo_root / design_rel).is_file():
            errors.append(f"Missing design directory file: {design_rel}")

    return errors


def main() -> int:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    errors = check_installation(repo_root)
    if errors:
        print("EGM verification FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(
        f"EGM verification OK: {len(EXPECTED_SKILLS)} skills, "
        f"{len(EXPECTED_AGENTS)} agents, {len(EXPECTED_STANDARDS)} standards, "
        f"manifests and workspace wiring verified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
