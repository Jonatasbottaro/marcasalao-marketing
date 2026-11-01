import importlib.util
import json
from pathlib import Path
import threading
import tomllib
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock

MODULE = Path(__file__).resolve().parents[1] / "memory_sync.py"
spec = importlib.util.spec_from_file_location("memory_sync", MODULE)
memory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memory)


class MemoryTests(unittest.TestCase):
    def test_scope_and_campaign_isolation(self):
        for name in ("general",) + memory.BRANDS:
            pages = list(memory.pages(memory.ROOT, name))
            self.assertTrue(pages)
            self.assertEqual({p["project"] for p in pages},
                             {memory.scope(memory.ROOT, name)["project"]})
            campaigns = [p for p in pages if p["path"].startswith("campaigns/")]
            if name == "general":
                self.assertFalse(campaigns)
            else:
                expected = list((memory.ROOT / "marcas" / name / "posts").glob("*/README.md"))
                self.assertEqual(len(campaigns), len(expected))
                self.assertTrue(campaigns)
                for page in campaigns:
                    self.assertIn("/marcas/" + name + "/posts/", page["body"])
                    self.assertIn("historical", page["tags"])
            self.assertTrue(all(p["body"].startswith("# ") for p in pages))
            self.assertEqual(len(pages), len({p["path"] for p in pages}))

    def test_toml_and_retention(self):
        config = tomllib.loads((memory.ROOT / "memory/config/server.toml.example").read_text())
        self.assertEqual(config["embedding_provider"], "none")
        self.assertFalse(config["auto_improve"]["scheduler"]["enabled"])
        self.assertEqual(config["maintenance"]["forget_sweep_interval_secs"], 0)
        for name in ("general",) + memory.BRANDS:
            self.assertTrue(all(p["tier"] in ("semantic", "procedural")
                                for p in memory.pages(memory.ROOT, name)))

    def test_error_does_not_retry_or_read(self):
        client = Mock()
        client.call.side_effect = memory.RpcError({"code": -32603, "message": "denied"})
        with self.assertRaises(memory.RpcError):
            memory.import_page(client, {})
        self.assertEqual(client.call.call_count, 1)

    def test_remote_http_and_embedded_credentials_rejected(self):
        for url in ("http://remote.example", "https://user:password@example.com", "ftp://x"):
            with self.assertRaises(ValueError):
                memory.Client(url)

    def test_mcp_roundtrip_idempotency_and_conflict(self):
        state = {"pages": {}, "calls": []}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                self.assert_request()
                message = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                state["calls"].append(message)
                if message["method"] == "notifications/initialized":
                    self.send_response(202)
                    self.end_headers()
                    return
                response = {"jsonrpc": "2.0", "id": message["id"]}
                if message["method"] == "initialize":
                    response["result"] = {"protocolVersion": "2024-11-05",
                                          "capabilities": {}, "serverInfo": {
                                              "name": "fixture", "version": "1"}}
                else:
                    params = message["params"]
                    args = params["arguments"]
                    key = tuple(args[k] for k in ("workspace", "project", "path"))
                    if params["name"] == "memory_write_page":
                        if key in state["pages"]:
                            response["error"] = {"code": -32600, "message": "conflict",
                                                 "data": {"reason": "precondition_failed"}}
                        else:
                            assert args["create_only"] is True
                            state["pages"][key] = dict(args)
                            result = {"page_id": "fixture-id", "path": args["path"]}
                    else:
                        page = state["pages"][key]
                        result = {"body": page["body"], "truncated": False,
                                  "frontmatter": {k: page[k] for k in (
                                      "kind", "tier", "pinned", "tags")}}
                    if "error" not in response:
                        response["result"] = {"content": [
                            {"type": "text", "text": json.dumps(result)}]}
                # Exercise the Streamable HTTP SSE response path.
                raw = ("event: message\ndata: " + json.dumps(response) + "\n\n").encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def assert_request(self):
                assert self.path == "/mcp"
                assert self.headers["Authorization"] == "Bearer fixture-token"

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = memory.Client("http://127.0.0.1:" + str(server.server_port), "fixture-token")
            client.initialize()
            page = next(memory.pages(memory.ROOT, "marcasalao"))
            self.assertEqual(memory.import_page(client, page), "created")
            self.assertEqual(memory.import_page(client, page), "unchanged")
            changed = dict(page, body=page["body"] + "\nrevisão")
            self.assertEqual(memory.import_page(client, changed), "conflict")
            stored = next(iter(state["pages"].values()))
            self.assertEqual(stored["body"], page["body"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_json_and_tool_errors(self):
        client = memory.Client("http://localhost:49374")
        client.rpc = Mock(return_value={"isError": True, "content": []})
        with self.assertRaises(RuntimeError):
            client.call("memory_write_page", {})


if __name__ == "__main__":
    unittest.main()
