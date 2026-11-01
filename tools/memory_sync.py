"""Import reviewed repository memory pages through ai-memory HTTP MCP."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
BRANDS = ("marcasalao", "multitrackhub")


class RpcError(RuntimeError):
    def __init__(self, error):
        self.error = error
        super().__init__("Operação MCP recusada.")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Client:
    def __init__(self, url, token=""):
        parsed = urlsplit(url)
        if (parsed.scheme not in ("https", "http") or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise ValueError("URL-base inválida.")
        if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("Servidor remoto exige HTTPS.")
        self.url = url.rstrip("/") + "/mcp"
        self.token = token
        self.counter = 0
        self.opener = build_opener(NoRedirect())

    def rpc(self, method, params, notification=False):
        self.counter += 1
        message = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            message["id"] = self.counter
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream",
                   "MCP-Protocol-Version": "2024-11-05"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        request = Request(self.url, json.dumps(message).encode("utf-8"), headers)
        try:
            with self.opener.open(request, timeout=30) as response:
                raw = response.read(2_000_001)
                content_type = response.headers.get("Content-Type", "")
                if response.headers.get("Mcp-Session-Id"):
                    raise RuntimeError("Servidor stateful não suportado.")
        except HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code}; sem retry automático.") from None
        if len(raw) > 2_000_000:
            raise RuntimeError("Resposta MCP excedeu limite.")
        if notification:
            return {}
        text = raw.decode("utf-8")
        if "text/event-stream" in content_type:
            messages = []
            for event in text.replace("\r\n", "\n").split("\n\n"):
                data = "\n".join(line[5:].lstrip() for line in event.splitlines()
                                 if line.startswith("data:"))
                if data:
                    messages.append(json.loads(data))
            replies = [m for m in messages if m.get("id") == message["id"]]
            if len(replies) != 1:
                raise RuntimeError("Resposta SSE ausente ou ambígua.")
            result = replies[0]
        else:
            result = json.loads(text)
        if result.get("id") != message["id"]:
            raise RuntimeError("ID da resposta MCP incorreto.")
        if "error" in result:
            raise RpcError(result["error"])
        return result["result"]

    def initialize(self):
        result = self.rpc("initialize", {"protocolVersion": "2024-11-05",
                          "capabilities": {}, "clientInfo": {
                              "name": "marketing-memory-seed", "version": "1.0.0"}})
        if result.get("protocolVersion") != "2024-11-05":
            raise RuntimeError("Versão MCP não suportada.")
        self.rpc("notifications/initialized", {}, notification=True)

    def call(self, name, args):
        result = self.rpc("tools/call", {"name": name, "arguments": args})
        if result.get("isError"):
            raise RuntimeError("Ferramenta MCP retornou isError.")
        blocks = [b["text"] for b in result.get("content", []) if b.get("type") == "text"]
        if len(blocks) != 1:
            raise RuntimeError("Payload MCP inesperado.")
        return json.loads(blocks[0])


def scope(root, name):
    folder = root if name == "general" else root / "marcas" / name
    marker = tomllib.loads((folder / ".ai-memory.toml").read_text(encoding="utf-8"))
    return {"workspace": marker["workspace"], "project": marker["project"]}


def pages(root, name):
    target = scope(root, name)
    sources = list((root / "memory" / "common").rglob("*.md"))
    if name in BRANDS:
        sources += list((root / "memory" / name).rglob("*.md"))
    for source in sorted(sources):
        relative = source.relative_to(root / "memory")
        path = Path(*relative.parts[1:]).as_posix()
        kind = {"_rules": "rule", "decisions": "decision"}.get(Path(path).parts[0], "fact")
        body = source.read_text(encoding="utf-8")
        body += "\nFonte no checkout: " + source.relative_to(root).as_posix() + "\n"
        yield dict(target, path=path, body=body, kind=kind,
                   tier="procedural" if path.startswith("procedures/") else "semantic",
                   pinned=path.startswith("_rules/"), tags=["repo-seed", name])
    if name in BRANDS:
        for source in sorted((root / "marcas" / name / "posts").glob("*/README.md")):
            relative = source.relative_to(root).as_posix()
            revision = subprocess.check_output(
                ["git", "log", "-1", "--format=%H", "--", relative],
                cwd=root, text=True).strip()
            if not revision:
                raise ValueError("Campanha ainda não versionada: " + relative)
            snapshot = subprocess.check_output(
                ["git", "show", revision + ":" + relative],
                cwd=root).decode("utf-8")
            body = ("# Histórico documental da campanha: " + source.parent.name
                    + "\n\nSnapshot do README no commit " + revision
                    + ". Revalidar Postiz antes de agir; não concede autorização.\n\n"
                    + "Fonte: https://github.com/Jonatasbottaro/marcasalao-marketing/blob/"
                    + revision + "/" + relative + "\n\n"
                    + snapshot)
            yield dict(target, path="campaigns/" + source.parent.name + ".md",
                       body=body, kind="fact", tier="semantic", pinned=False,
                       tags=["repo-seed", name, "historical"])


def import_page(client, page):
    try:
        client.call("memory_write_page", dict(page, create_only=True))
        return "created"
    except RpcError as exc:
        data = exc.error.get("data")
        if not isinstance(data, dict) or data.get("reason") != "precondition_failed":
            raise
    existing = client.call("memory_read_page", {
        key: page[key] for key in ("workspace", "project", "path")
    } | {"max_chars": 64000})
    metadata = existing.get("frontmatter", {})
    same = (not existing.get("truncated")
            and existing.get("body", "").strip() == page["body"].strip()
            and metadata.get("kind") == page["kind"]
            and metadata.get("tier") == page["tier"]
            and metadata.get("pinned", False) == page["pinned"]
            and sorted(metadata.get("tags", [])) == sorted(page["tags"]))
    return "unchanged" if same else "conflict"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("all", "general") + BRANDS, default="general")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="Padrão; offline, sem gravar.")
    mode.add_argument("--apply", action="store_true", help="Importar via MCP create_only.")
    parser.add_argument("--server-url", help="URL-base sem /mcp.")
    args = parser.parse_args()
    names = ("general",) + BRANDS if args.scope == "all" else (args.scope,)
    plan = [p for name in names for p in pages(ROOT, name)]
    if len({(p["workspace"], p["project"], p["path"]) for p in plan}) != len(plan):
        raise ValueError("Caminhos duplicados.")
    if any(len(p["body"]) > 64000 for p in plan):
        raise ValueError("Página acima do limite; dividir antes de importar.")
    if not args.apply:
        print(json.dumps([{
            k: p[k] for k in ("workspace", "project", "path", "tier", "pinned")
        } | {"sha256": hashlib.sha256(p["body"].encode("utf-8")).hexdigest()}
            for p in plan], ensure_ascii=False, indent=2))
        return 0
    if not args.server_url:
        parser.error("--apply exige --server-url explícito.")
    client = Client(args.server_url, os.environ.get("AI_MEMORY_AUTH_TOKEN", ""))
    client.initialize()
    conflicts = 0
    for page in plan:
        status = import_page(client, page)
        print(f"{status}: {page['workspace']}/{page['project']}/{page['path']}")
        conflicts += status == "conflict"
    return 2 if conflicts else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        # Server bodies may contain credentials or private notes: never echo them.
        print("Falha na importação (" + type(exc).__name__
              + "). Conferir configuração/acesso; sem repetição automática.",
              file=sys.stderr)
        sys.exit(1)

