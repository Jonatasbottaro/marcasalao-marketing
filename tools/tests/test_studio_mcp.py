"""Regressao do servidor MCP de Planejamento (tools/studio_mcp_server.py).

Sobe um Studio real em loopback (thread in-process) e exercita o servidor MCP
como subprocesso stdio, com um cliente MCP de teste. Cobre: handshake
initialize/tools/list/tools/call; dois clientes (Codex e Claude Code) no mesmo
trabalho ficticio com duas propostas creative validas (roteiro e carrossel);
persistencia do historico; editores inalterados ate incorporar+aplicar;
rejeicoes (trabalho inexistente, payload invalido, fingerprint vencido, edicao
concorrente no momento da gravacao) preservando o estado; dois envios validos
concorrentes; Studio indisponivel; e varredura de segredos/caminhos nas respostas.
"""

import http.client
import json
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import render_local
import studio_planning
import studio_review
import video_studio

WORKTREE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_MS = "platform/examples/projects/marca-salao-social.project.json"
MCP_SERVER = os.path.join(WORKTREE, "tools", "studio_mcp_server.py")
HAS_BRIDGE = bool(shutil.which("node")) and os.path.isfile(
    os.path.join(WORKTREE, "platform", "dist", "src", "compile-video-request.js"))


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def creative_suggestion(profiles, focus="video"):
    """PlanningSuggestion v1 (creative) valida; varia a secao conforme o foco."""
    pid = profiles[0]
    pid2 = profiles[1] if len(profiles) > 1 else profiles[0]
    hooks = [
        {"id": "hook-1", "text": "Cansado de conferir horarios no caderno?", "angle": "dor-pratica"},
        {"id": "hook-2", "text": "Veja a agenda do salao em uma tela.", "angle": "clareza"},
    ]
    if focus == "video":
        scenes = [
            {"id": "cena-gancho", "objective": "Apresentar a dor", "narrativeFunction": "hook",
             "durationMs": 4000, "titleOverlay": "Agenda no caderno?", "caption": "Legenda da cena de gancho.",
             "narration": "Narracao externa da cena de gancho.", "requiredMediaDescriptor": "Tela de abertura",
             "motionIntent": "none"},
            {"id": "cena-demo", "objective": "Mostrar a agenda", "narrativeFunction": "demonstration",
             "durationMs": 5000, "titleOverlay": "Agenda visual", "caption": "Legenda da demonstracao.",
             "narration": "Narracao externa da demonstracao.", "requiredMediaDescriptor": "Captura da agenda",
             "motionIntent": "none"},
            {"id": "cena-cta", "objective": "Convidar a conhecer", "narrativeFunction": "cta",
             "durationMs": 3000, "titleOverlay": "Conheca o Marca Salao", "caption": "Legenda de fechamento.",
             "narration": "Narracao externa de fechamento.", "requiredMediaDescriptor": "Tela de encerramento",
             "motionIntent": "none"},
        ]
        cards = [
            {"id": "capa", "role": "cover", "title": "Agenda visual", "body": "Subtitulo",
             "requiredMediaDescriptor": "Capa limpa"},
            {"id": "fechamento", "role": "cta", "title": "Conheca agora", "body": "Chamada do canal"},
        ]
        copies = [{"profileId": pid, "title": "Agenda do salao", "postText": "Texto de publicacao do roteiro.",
                   "cta": "Conheca o Marca Salao", "destinationUrl": "https://marcasalao.com.br",
                   "hashtags": "#marcasalao", "flags": ["Confirmar URL e CTA antes de aprovar"]}]
        summary = "Roteiro em tres passos: dor, demonstracao da agenda e convite."
    else:
        scenes = [
            {"id": "cena-unica", "objective": "Abertura", "narrativeFunction": "hook",
             "durationMs": 4000, "titleOverlay": "Agenda visual", "caption": "Legenda unica.",
             "narration": "Narracao externa unica.", "requiredMediaDescriptor": "Tela de abertura",
             "motionIntent": "none"},
        ]
        cards = [
            {"id": "capa", "role": "cover", "title": "5 sinais de agenda desorganizada", "body": "Capa",
             "requiredMediaDescriptor": "Capa limpa"},
            {"id": "passo-1", "role": "content", "title": "Horarios duplicados", "body": "Explicacao breve"},
            {"id": "passo-2", "role": "content", "title": "Faltas sem aviso", "body": "Explicacao breve"},
            {"id": "fechamento", "role": "cta", "title": "Organize a agenda", "body": "Chamada do canal"},
        ]
        copies = [{"profileId": pid2, "title": "Carrossel agenda", "postText": "Texto de publicacao do carrossel.",
                   "cta": "Conheca o Marca Salao", "destinationUrl": "https://marcasalao.com.br",
                   "hashtags": "#marcasalao", "flags": ["Confirmar URL e CTA antes de aprovar"]}]
        summary = "Carrossel em quatro cards: capa, dois sinais e fechamento."
    return {
        "schemaVersion": 1, "stage": "creative", "hookOptions": hooks, "selectedHookId": "hook-1",
        "scriptSummary": summary, "videoScenes": scenes, "carouselCards": cards, "channelCopies": copies,
    }


class McpStdioClient:
    """Cliente MCP de teste sobre stdio (JSON-RPC delimitado por newline)."""

    def __init__(self, port, label="test", timeout=120, env=None):
        self.port = port
        self.label = label
        self.timeout = timeout
        proc_env = dict(os.environ)
        if env:
            proc_env.update(env)
        self.proc = subprocess.Popen(
            [sys.executable, MCP_SERVER, "--port", str(port)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1, cwd=WORKTREE, env=proc_env,
        )
        self._id = 0
        self._lines = queue.Queue()
        self._reader = threading.Thread(target=self._pump, daemon=True)
        self._reader.start()
        self.raw_responses = []

    def _pump(self):
        for line in self.proc.stdout:
            self._lines.put(line)
        self._lines.put(None)

    def _write(self, obj):
        self.proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def request(self, method, params=None):
        self._id += 1
        mid = self._id
        msg = {"jsonrpc": "2.0", "id": mid, "method": method}
        if params is not None:
            msg["params"] = params
        self._write(msg)
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"sem resposta MCP para {method}")
            try:
                line = self._lines.get(timeout=remaining)
            except queue.Empty:
                raise TimeoutError(f"sem resposta MCP para {method}")
            if line is None:
                raise RuntimeError(f"stdout do servidor MCP encerrou durante {method}")
            line = line.strip()
            if not line:
                continue
            parsed = json.loads(line)  # stdout deve conter apenas JSON MCP
            self.raw_responses.append(line)
            if parsed.get("id") == mid:
                return parsed

    def notify(self, method, params=None):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        self._write(msg)

    def initialize(self, version="2025-06-18"):
        res = self.request("initialize", {
            "protocolVersion": version, "capabilities": {},
            "clientInfo": {"name": self.label, "version": "1.0.0"},
        })
        self.notify("notifications/initialized")
        return res

    def call_tool(self, name, arguments):
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def send_raw(self, obj):
        """Envia uma linha JSON-RPC crua (ex.: lote) e devolve a proxima resposta."""
        self.proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()
        line = self._lines.get(timeout=self.timeout)
        if line is None:
            raise RuntimeError("stdout do servidor MCP encerrou")
        return json.loads(line.strip())

    def close(self):
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)
        self.stderr = self.proc.stderr.read()
        self.proc.stderr.close()
        self.proc.stdout.close()


class StudioMcpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HAS_BRIDGE:
            raise unittest.SkipTest("ponte TypeScript indisponivel")
        cls.port = _free_port()
        cls.httpd, cls.studio = video_studio.make_server(WORKTREE, cls.port)
        cls.studio.port = cls.port
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = f"http://127.0.0.1:{cls.port}"
        cls.host = f"127.0.0.1:{cls.port}"
        for _ in range(60):
            try:
                cls.http("GET", "/api/readiness")
                break
            except OSError:
                time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.studio.close()

    @classmethod
    def http(cls, method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=120)
        headers = {"Host": cls.host}
        if method == "POST":
            headers["Origin"] = cls.origin
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res.status, json.loads(data)

    def setUp(self):
        self.wid = f"t-mcp-{self._testMethodName.replace('_', '-')}"[:60]
        self._cleanup_work(self.wid)
        self.addCleanup(self._cleanup_work, self.wid)
        st, created = self.http("POST", "/api/works/create", {
            "id": self.wid, "name": f"MCP {self.wid}", "project": PROJECT_MS, "template": "blank"})
        self.assertEqual(st, 200, created)
        st, _ = self.http("POST", "/api/works/planning/save", {
            "workId": self.wid, "ideaText": "Video curto sobre a agenda do salao",
            "briefing": {"objective": "Organizar horarios", "audience": "Donos de salao",
                         "coreMessage": "Agenda visual sem caderno"},
        })
        self.assertEqual(st, 200)
        self.clients = []

    def tearDown(self):
        for c in self.clients:
            c.close()

    def _cleanup_work(self, wid):
        work_dir = os.path.join(WORKTREE, ".workspace", "studio", "works", wid)
        shutil.rmtree(render_local.fs_path(work_dir, force=True), ignore_errors=True)

    def _client(self, label="test", port=None, env=None, version="2025-06-18"):
        c = McpStdioClient(port if port is not None else self.port, label=label, env=env)
        self.clients.append(c)
        c.initialize(version=version)
        return c

    def _overview(self):
        st, ov = self.http("GET", f"/api/works/planning?id={self.wid}")
        self.assertEqual(st, 200, ov)
        return ov

    def _history_ids(self):
        return [r["suggestionId"] for r in self._overview()["planning"]["suggestionHistory"]]

    def _consult(self, client):
        res = client.call_tool("consultar_planejamento", {"workId": self.wid})
        self.assertFalse(res["result"].get("isError"), res)
        return res["result"]["structuredContent"]

    def _enviar(self, client, fp, suggestion):
        return client.call_tool("enviar_proposta", {
            "workId": self.wid, "expectedContextFingerprint": fp, "suggestion": suggestion})

    # ---- testes ----

    def test_01_handshake_tools_list_and_consult(self):
        c = self._client("codex")
        init = c.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                        "clientInfo": {"name": "codex", "version": "1"}})
        self.assertEqual(init["result"]["serverInfo"]["name"], "video-studio-planejamento")
        self.assertIn(init["result"]["protocolVersion"], ("2025-06-18", "2025-03-26", "2024-11-05"))
        listing = c.request("tools/list")
        names = {t["name"] for t in listing["result"]["tools"]}
        self.assertEqual(names, {"consultar_planejamento", "enviar_proposta"})
        ctx = self._consult(c)
        self.assertEqual(ctx["stage"], "creative")
        self.assertTrue(ctx["contextFingerprint"])
        self.assertTrue(ctx["allowedProfiles"])
        self.assertIn("PlanningSuggestion v1", ctx["instructions"]["systemPrompt"])
        self.assertIn("videoScenes", ctx["instructions"]["userPrompt"])
        self.assertIn("carouselCards", ctx["instructions"]["userPrompt"])

    def test_02_two_clients_two_proposals_persist_in_history(self):
        codex = self._client("codex")
        claude = self._client("claude-code")
        ctx_a = self._consult(codex)
        ctx_b = self._consult(claude)
        self.assertEqual(ctx_a["contextFingerprint"], ctx_b["contextFingerprint"])
        profiles = ctx_a["allowedProfiles"]
        before = self._history_ids()
        res_a = self._enviar(codex, ctx_a["contextFingerprint"], creative_suggestion(profiles, "video"))
        res_b = self._enviar(claude, ctx_b["contextFingerprint"], creative_suggestion(profiles, "carousel"))
        self.assertFalse(res_a["result"].get("isError"), res_a)
        self.assertFalse(res_b["result"].get("isError"), res_b)
        id_a = res_a["result"]["structuredContent"]["suggestionId"]
        id_b = res_b["result"]["structuredContent"]["suggestionId"]
        self.assertNotEqual(id_a, id_b)
        after = self._history_ids()
        self.assertIn(id_a, after)
        self.assertIn(id_b, after)
        self.assertEqual(len(after), len(before) + 2)
        self.assertTrue(res_a["result"]["structuredContent"]["diffPreview"]["videoScenesAdded"])
        self.assertTrue(res_b["result"]["structuredContent"]["diffPreview"]["carouselCardsAdded"])

    def test_03_editors_change_only_after_accept_and_apply(self):
        c = self._client("codex")
        ctx = self._consult(c)
        profiles = ctx["allowedProfiles"]
        st, opened = self.http("GET", f"/api/works/open?id={self.wid}")
        self.assertEqual(st, 200)
        video_before = opened["videoRequest"]
        scenes_before = self._overview()["planning"]["creative"]["videoScenes"]
        suggestion = creative_suggestion(profiles, "video")
        # Vincula as cenas a midia local existente para o apply resolver o VideoRequest.
        media_ids = [m["id"] for m in video_before.get("media", [])]
        self.assertTrue(media_ids)
        for i, scene in enumerate(suggestion["videoScenes"]):
            scene["mediaId"] = media_ids[i % len(media_ids)]
        res = self._enviar(c, ctx["contextFingerprint"], suggestion)
        sid = res["result"]["structuredContent"]["suggestionId"]
        # Registrar a proposta NAO altera o rascunho de planejamento nem os editores.
        st, opened_mid = self.http("GET", f"/api/works/open?id={self.wid}")
        self.assertEqual(opened_mid["videoRequest"], video_before)
        self.assertEqual(self._overview()["planning"]["creative"]["videoScenes"], scenes_before)
        # Operador incorpora (accept) -> rascunho de planejamento passa a ter as cenas propostas.
        fp_mid = self._overview()["fingerprints"]["contextFingerprint"]
        st_acc, acc = self.http("POST", "/api/works/planning/accept-suggestion", {
            "workId": self.wid, "suggestionId": sid, "expectedContextFingerprint": fp_mid})
        self.assertEqual(st_acc, 200, acc)
        accepted_ids = {s["id"] for s in acc["planning"]["creative"]["videoScenes"]}
        self.assertIn("cena-demo", accepted_ids)
        # Editores ainda nao mudaram so com incorporar.
        st, opened_acc = self.http("GET", f"/api/works/open?id={self.wid}")
        self.assertEqual(opened_acc["videoRequest"], video_before)
        # Operador aplica aos editores -> o rascunho de video muda.
        fps = acc["fingerprints"]
        st_app, app = self.http("POST", "/api/works/planning/apply", {
            "workId": self.wid, "expectedContextFingerprint": fps["contextFingerprint"],
            "expectedEditorialBriefingSha256": fps["editorialBriefingSha256"],
            "expectedDraftsSha256": fps["draftsSha256"],
            "applyBriefing": False, "applyVideo": True, "applyCarousel": False,
            "applyMotionSync": False, "channelsToApply": [],
            "preserveSceneIds": [], "preserveCardIds": [], "preserveChannelIds": []})
        self.assertEqual(st_app, 200, app)
        self.assertEqual(app["applied"]["video"]["status"], "applied", app)
        st, opened_after = self.http("GET", f"/api/works/open?id={self.wid}")
        self.assertNotEqual(opened_after["videoRequest"], video_before)
        after_ids = {s["id"] for s in opened_after["videoRequest"]["scenes"]}
        self.assertIn("cena-demo", after_ids)

    def test_04_nonexistent_work_rejected_state_preserved(self):
        c = self._client("codex")
        res = c.call_tool("consultar_planejamento", {"workId": "t-mcp-nao-existe-xyz"})
        self.assertTrue(res["result"]["isError"])
        self.assertIn("nao encontrado", res["result"]["content"][0]["text"])
        res2 = c.call_tool("enviar_proposta", {
            "workId": "t-mcp-nao-existe-xyz", "expectedContextFingerprint": "x",
            "suggestion": creative_suggestion(["instagram-reels-video"], "video")})
        self.assertTrue(res2["result"]["isError"])

    def test_05_invalid_payload_returns_validator_error(self):
        c = self._client("codex")
        ctx = self._consult(c)
        before = self._history_ids()
        bad = creative_suggestion(ctx["allowedProfiles"], "video")
        bad["selectedHookId"] = "hook-inexistente"
        res = self._enviar(c, ctx["contextFingerprint"], bad)
        self.assertTrue(res["result"]["isError"])
        self.assertEqual(res["result"]["structuredContent"]["code"], "PLANNING_SELECTED_HOOK_UNKNOWN")
        # carouselCards vazio tambem e rejeitado pelo contrato creative.
        bad2 = creative_suggestion(ctx["allowedProfiles"], "video")
        bad2["carouselCards"] = []
        res2 = self._enviar(c, ctx["contextFingerprint"], bad2)
        self.assertTrue(res2["result"]["isError"])
        self.assertEqual(self._history_ids(), before)

    def test_06_stale_fingerprint_after_edit_conflicts(self):
        c = self._client("codex")
        ctx = self._consult(c)
        old_fp = ctx["contextFingerprint"]
        before = self._history_ids()
        # Operador edita o planejamento -> fingerprint muda.
        st, _ = self.http("POST", "/api/works/planning/save", {
            "workId": self.wid, "ideaText": "Ideia editada pelo operador"})
        self.assertEqual(st, 200)
        new_fp = self._overview()["fingerprints"]["contextFingerprint"]
        self.assertNotEqual(old_fp, new_fp)
        res = self._enviar(c, old_fp, creative_suggestion(ctx["allowedProfiles"], "video"))
        self.assertTrue(res["result"]["isError"])
        self.assertEqual(res["result"]["structuredContent"]["code"], "CONTEXT_CONFLICT")
        self.assertIn("consultar_planejamento", res["result"]["content"][0]["text"])
        self.assertEqual(self._history_ids(), before)
        # Com o fingerprint atualizado, a mesma proposta e aceita.
        ok = self._enviar(c, new_fp, creative_suggestion(ctx["allowedProfiles"], "video"))
        self.assertFalse(ok["result"].get("isError"), ok)

    def test_07_concurrent_edit_at_write_moment_is_rechecked_under_lock(self):
        # Prova deterministica da reconferencia sob o lock: uma edicao concorrente
        # entre a validacao (fora do lock) e a gravacao nao pode passar.
        c = self._client("codex")
        ctx = self._consult(c)
        original_fp = ctx["contextFingerprint"]
        before = self._history_ids()
        original = studio_planning.build_planning_overview
        calls = {"n": 0}

        def patched(studio, work_id):
            ov = original(studio, work_id)
            calls["n"] += 1
            if calls["n"] == 1:
                studio_planning.save_planning(studio, work_id, {"ideaText": "edicao concorrente no envio"})
            return ov

        studio_planning.build_planning_overview = patched
        try:
            with self.assertRaises(studio_review.ReviewVersionConflictError):
                studio_planning.validate_and_stage_suggestion(self.studio, self.wid, {
                    "expectedContextFingerprint": original_fp,
                    "suggestion": creative_suggestion(ctx["allowedProfiles"], "video"),
                }, mode="import")
        finally:
            studio_planning.build_planning_overview = original
        self.assertEqual(self._history_ids(), before)
        self.assertEqual(self._overview()["planning"]["ideaText"], "edicao concorrente no envio")

    def test_08_two_valid_concurrent_submits_both_recorded(self):
        c1 = self._client("codex")
        c2 = self._client("claude-code")
        ctx = self._consult(c1)
        fp = ctx["contextFingerprint"]
        profiles = ctx["allowedProfiles"]
        before = self._history_ids()
        results = {}

        def submit(key, client, focus):
            results[key] = self._enviar(client, fp, creative_suggestion(profiles, focus))

        t1 = threading.Thread(target=submit, args=("a", c1, "video"))
        t2 = threading.Thread(target=submit, args=("b", c2, "carousel"))
        t1.start(); t2.start(); t1.join(); t2.join()
        self.assertFalse(results["a"]["result"].get("isError"), results["a"])
        self.assertFalse(results["b"]["result"].get("isError"), results["b"])
        id_a = results["a"]["result"]["structuredContent"]["suggestionId"]
        id_b = results["b"]["result"]["structuredContent"]["suggestionId"]
        after = self._history_ids()
        self.assertIn(id_a, after)
        self.assertIn(id_b, after)
        self.assertEqual(len(after), len(before) + 2)

    def test_09_studio_unavailable_reports_start_instruction(self):
        dead_port = _free_port()
        c = self._client("codex", port=dead_port)
        res = c.call_tool("consultar_planejamento", {"workId": self.wid})
        self.assertTrue(res["result"]["isError"])
        self.assertEqual(res["result"]["structuredContent"]["code"], "STUDIO_UNAVAILABLE")
        text = res["result"]["content"][0]["text"]
        self.assertIn("video_studio.py --port", text)
        self.assertIn(str(dead_port), text)

    def test_10_responses_leak_no_secrets_or_internal_paths(self):
        c = self._client("codex")
        ctx = self._consult(c)
        res = self._enviar(c, ctx["contextFingerprint"], creative_suggestion(ctx["allowedProfiles"], "video"))
        self.assertFalse(res["result"].get("isError"), res)
        blob = "\n".join(c.raw_responses)
        # Chaves sensiveis (entre aspas, para nao casar com o eco do ID do trabalho)
        # e caminhos internos nao podem aparecer nas respostas MCP.
        for forbidden in ('"secret"', '"apiKey"', '"credentialValue"', '"connectionId"',
                          '"endpoint"', '"llmConfig"', '"textConnection"',
                          ".workspace", WORKTREE.replace("\\", "/")):
            self.assertNotIn(forbidden, blob, f"vazamento de {forbidden} na resposta MCP")

    def test_11_import_without_fingerprint_stable_binds_preview(self):
        before = self._history_ids()
        fp_now = self._overview()["fingerprints"]["contextFingerprint"]
        st, imp = self.http("POST", "/api/works/planning/import", {
            "workId": self.wid, "suggestion": creative_suggestion(self._profiles(), "video")})
        self.assertEqual(st, 200, imp)
        rec = imp["suggestionRecord"]
        self.assertEqual(rec["baseContextFingerprint"], fp_now)
        self.assertTrue(rec["diffPreview"]["videoScenesAdded"])
        self.assertEqual(len(self._history_ids()), len(before) + 1)

    def test_12_import_without_fingerprint_concurrent_edit_conflicts(self):
        before = self._history_ids()
        profiles = self._profiles()
        original = studio_planning.build_planning_overview
        calls = {"n": 0}

        def patched(studio, work_id):
            ov = original(studio, work_id)
            calls["n"] += 1
            if calls["n"] == 1:
                studio_planning.save_planning(studio, work_id, {"ideaText": "edicao concorrente sem fingerprint"})
            return ov

        studio_planning.build_planning_overview = patched
        try:
            st, d = self.http("POST", "/api/works/planning/import", {
                "workId": self.wid, "suggestion": creative_suggestion(profiles, "video")})
        finally:
            studio_planning.build_planning_overview = original
        self.assertEqual(st, 409, d)
        self.assertTrue(d.get("conflict"))
        self.assertEqual(self._history_ids(), before)
        self.assertEqual(self._overview()["planning"]["ideaText"], "edicao concorrente sem fingerprint")

    def test_13_two_concurrent_imports_without_fingerprint_both_recorded(self):
        before = self._history_ids()
        results = {}

        def submit(key, focus):
            results[key] = self.http("POST", "/api/works/planning/import", {
                "workId": self.wid, "suggestion": creative_suggestion(self._profiles(), focus)})

        t1 = threading.Thread(target=submit, args=("a", "video"))
        t2 = threading.Thread(target=submit, args=("b", "carousel"))
        t1.start(); t2.start(); t1.join(); t2.join()
        self.assertEqual(results["a"][0], 200, results["a"])
        self.assertEqual(results["b"][0], 200, results["b"])
        after = self._history_ids()
        self.assertIn(results["a"][1]["suggestionRecord"]["suggestionId"], after)
        self.assertIn(results["b"][1]["suggestionRecord"]["suggestionId"], after)
        self.assertEqual(len(after), len(before) + 2)

    def test_14_mcp_rejects_briefing_stage_but_studio_import_ok(self):
        c = self._client("codex")
        ctx = self._consult(c)
        before = self._history_ids()
        res = self._enviar(c, ctx["contextFingerprint"], briefing_suggestion(ctx["allowedProfiles"]))
        self.assertTrue(res["result"]["isError"])
        self.assertEqual(res["result"]["structuredContent"]["code"], "PLANNING_STAGE_MISMATCH")
        self.assertEqual(self._history_ids(), before)
        # O fluxo normal de importacao de briefing pelo Studio continua disponivel.
        st, imp = self.http("POST", "/api/works/planning/import", {
            "workId": self.wid, "stage": "briefing",
            "suggestion": briefing_suggestion(ctx["allowedProfiles"])})
        self.assertEqual(st, 200, imp)
        self.assertEqual(imp["suggestionRecord"]["stage"], "briefing")
        self.assertEqual(len(self._history_ids()), len(before) + 1)

    def test_15_handshake_versions_and_batch_rejected(self):
        for ver in ("2025-06-18", "2024-11-05"):
            c = McpStdioClient(self.port, label=f"ver-{ver}")
            self.clients.append(c)
            init = c.initialize(version=ver)
            self.assertEqual(init["result"]["protocolVersion"], ver)
        for ver in ("2025-03-26", "1999-01-01"):
            c = McpStdioClient(self.port, label=f"out-{ver}")
            self.clients.append(c)
            init = c.initialize(version=ver)
            self.assertEqual(init["result"]["protocolVersion"], "2025-06-18")
        # Lote JSON-RPC: as versoes oferecidas nao suportam lotes -> Invalid Request.
        c = self._client("codex")
        batch = [{"jsonrpc": "2.0", "id": 900, "method": "ping"},
                 {"jsonrpc": "2.0", "id": 901, "method": "ping"}]
        resp = c.send_raw(batch)
        self.assertEqual(resp["error"]["code"], -32600)

    def test_16_utf8_transport_under_cp1252(self):
        accented = "Ação e narração — coração da agenda"
        st, _ = self.http("POST", "/api/works/planning/save", {
            "workId": self.wid, "briefing": {"coreMessage": accented}})
        self.assertEqual(st, 200)
        c = self._client("codex", env={"PYTHONIOENCODING": "cp1252"})
        ctx = self._consult(c)
        # Texto recebido pelo cliente (sentido servidor->cliente) em UTF-8 correto.
        self.assertEqual(ctx["briefing"]["coreMessage"], accented)
        sug = creative_suggestion(ctx["allowedProfiles"], "video")
        sug["videoScenes"][0]["caption"] = accented
        sug["videoScenes"][0]["narration"] = accented
        res = self._enviar(c, ctx["contextFingerprint"], sug)
        self.assertFalse(res["result"].get("isError"), res)
        sid = res["result"]["structuredContent"]["suggestionId"]
        rec = next(r for r in self._overview()["planning"]["suggestionHistory"] if r["suggestionId"] == sid)
        # Conteudo gravado no historico (sentido cliente->servidor) preservado.
        self.assertEqual(rec["suggestion"]["videoScenes"][0]["caption"], accented)
        self.assertEqual(rec["suggestion"]["videoScenes"][0]["narration"], accented)

    def _profiles(self):
        st, ov = self.http("GET", f"/api/works/planning?id={self.wid}")
        self.assertEqual(st, 200)
        return [p["id"] for p in ov["allowedProfiles"]]


def briefing_suggestion(profiles):
    return {
        "schemaVersion": 1, "stage": "briefing",
        "product": "Marca Salao", "objective": "Organizar horarios",
        "audience": "Donos de salao", "coreMessage": "Agenda visual sem caderno",
        "supportEvidence": "Captura da tela de agenda", "cta": "Conheca o Marca Salao",
        "tone": "Direto", "recommendedProfiles": [profiles[0]],
        "gaps": [], "questions": [], "claims": [],
    }


if __name__ == "__main__":
    unittest.main()