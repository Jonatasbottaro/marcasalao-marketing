"""Prova automatizada integrada do fluxo de campanha no Video Studio:

- Diagnostico de prontidao (--check --json com frontendBuild e 5 itens)
- Criacao/abertura generica via template="example:marca-salao-ns-001-p001"
- Recarga simulada (novo Studio sobre o mesmo workspace)
- Pre-voo HTTP (/api/queue/preflight) + CLI (tools/studio_preflight.py)
- Fila unica idempotente + conclusao -> Revisao & Entrega -> aprovacao tecnica
- Geracao de ZIP -> verificacao (/api/works/package/verify e delivery_verify.py) + download
- Edicao de rascunho -> draft_outdated -> reexportacao -> reexported_pending -> novo ZIP invalidando SHA anterior
- Backup e restauracao em segundo workspace isolado (ProjectManifest + sharedMedia antes/depois, preflight nos dois, fila preservada, review-state excluido, segunda restauracao recusada)
- Ensaio HTTP localhost de preservacao de query string UTM (/redirect-passa vs /redirect-descarta)
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from unittest.mock import patch

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKTREE_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)

import build_video
import campaign_proof
import delivery_verify
import render_local
import studio_work_backup as swb
import video_studio


def _main_root() -> str:
    real = os.path.realpath(WORKTREE_ROOT)
    marker = os.sep + ".workspace" + os.sep + "worktrees" + os.sep
    if marker in real:
        return real.split(marker, 1)[0]
    return real


def _http_json(url: str, method: str = "GET", body: dict | None = None, origin: str | None = None) -> tuple[int, dict]:
    headers = {}
    data = None
    if origin:
        headers["Origin"] = origin
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read().decode("utf-8"))


def _http_bytes(url: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.status, resp.read()


def _prepare_isolated_workspace(ws_dir: str, copy_project: bool = True) -> None:
    os.makedirs(render_local.fs_path(ws_dir, force=True), exist_ok=True)
    # Copiar tools/ (pulando studio/frontend/node_modules) e platform/
    shutil.copytree(
        render_local.fs_path(os.path.join(WORKTREE_ROOT, "tools"), force=True),
        render_local.fs_path(os.path.join(ws_dir, "tools"), force=True),
        ignore=shutil.ignore_patterns("node_modules", "__pycache__"),
        copy_function=lambda s, d: shutil.copy2(render_local.fs_path(s, force=True), render_local.fs_path(d, force=True)),
    )
    shutil.copytree(
        render_local.fs_path(os.path.join(WORKTREE_ROOT, "platform"), force=True),
        render_local.fs_path(os.path.join(ws_dir, "platform"), force=True),
        copy_function=lambda s, d: shutil.copy2(render_local.fs_path(s, force=True), render_local.fs_path(d, force=True)),
    )
    if not copy_project:
        pm = os.path.join(ws_dir, "platform", "examples", "projects", "marca-salao-social.project.json")
        if os.path.isfile(render_local.fs_path(pm, force=True)):
            os.remove(render_local.fs_path(pm, force=True))


class CampaignStudioEndToEndTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base_tmp = os.path.join(_main_root(), ".workspace", "tmp", "e2e-cs", uuid.uuid4().hex[:8])
        os.makedirs(render_local.fs_path(self.base_tmp, force=True), exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(render_local.fs_path(self.base_tmp, force=True), ignore_errors=True))

    def test_01_readiness_check_cli_json_and_utm_localhost_preservation(self) -> None:
        proc = subprocess.run(
            [sys.executable, os.path.join(WORKTREE_ROOT, "tools", "video_studio.py"), "--check", "--json", "--root", WORKTREE_ROOT],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual([i["id"] for i in data["items"]], ["python", "node", "platformBuild", "ffmpeg", "ffprobe"])
        self.assertIn("frontendBuild", data)
        self.assertIn("recommendedCommands", data)

        # Ensaio de preservacao de UTMs em redirecionamento HTTP localhost (GUIA-VALIDACAO-DESTINOS §5.1)
        seen_queries: dict[str, str] = {}

        class UtmHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlsplit(self.path)
                if parsed.path == "/redirect-passa":
                    loc = "/destino" + (("?" + parsed.query) if parsed.query else "")
                    self.send_response(302)
                    self.send_header("Location", loc)
                    self.end_headers()
                    return
                if parsed.path == "/redirect-descarta":
                    self.send_response(302)
                    self.send_header("Location", "/destino")
                    self.end_headers()
                    return
                if parsed.path == "/destino":
                    seen_queries["last"] = parsed.query
                    body = json.dumps({"query": parsed.query}).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_response(404)
                self.end_headers()

            def log_message(self, *args):
                pass

        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), UtmHandler)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            port = srv.server_port
            qs = "utm_source=instagram&utm_medium=reels&utm_campaign=ns-001&utm_content=ns-001-p001-reels-v1"
            st1, body1 = _http_json(f"http://127.0.0.1:{port}/redirect-passa?{qs}")
            self.assertEqual(st1, 200)
            self.assertEqual(body1["query"], qs)
            st2, body2 = _http_json(f"http://127.0.0.1:{port}/redirect-descarta?{qs}")
            self.assertEqual(st2, 200)
            self.assertEqual(body2["query"], "")
        finally:
            srv.shutdown()
            srv.server_close()

    def test_02_studio_campaign_flow_zip_invalidation_and_two_workspace_backup_restore(self) -> None:
        has_tools, msg = campaign_proof._ensure_video_tools_for_root(WORKTREE_ROOT)
        platform_ok = os.path.isfile(os.path.join(WORKTREE_ROOT, "platform", "dist", "src", "compile-video-request.js"))
        if not has_tools or not platform_ok:
            if os.environ.get("REQUIRE_RENDER") == "1":
                self.fail(f"REQUIRE_RENDER=1 mas pre-requisitos ausentes: {msg}")
            self.skipTest(msg or "pre-requisitos ausentes")

        ws1 = os.path.join(self.base_tmp, "ws1")
        ws2 = os.path.join(self.base_tmp, "ws2")
        zip_backup = os.path.join(ws1, ".workspace", "tmp", "backup-ns001.zip")
        zip_shared = os.path.join(ws1, ".workspace", "tmp", "backup-shared.zip")
        _prepare_isolated_workspace(ws1, copy_project=True)
        _prepare_isolated_workspace(ws2, copy_project=False)

        wid = "ns-001-e2e"
        httpd1, studio1 = video_studio.make_server(ws1, 0)
        th1 = threading.Thread(target=httpd1.serve_forever, daemon=True)
        th1.start()
        base1 = f"http://127.0.0.1:{httpd1.server_port}"

        try:
            # 1. Confirmar NS-001/NS-002 descobertos dinamicamente em /api/examples e criar via template generico
            st, ex_list = _http_json(f"{base1}/api/examples")
            self.assertEqual(st, 200)
            ex_ids = {e["request"].get("id") for e in ex_list["examples"] if e.get("kind") == "video"}
            self.assertIn("marca-salao-ns-001-p001", ex_ids)
            self.assertIn("marca-salao-ns-002-p001", ex_ids)

            st, created = _http_json(f"{base1}/api/works/create", method="POST", origin=base1, body={
                "id": wid,
                "name": "Piloto NS-001 E2E",
                "template": "example:marca-salao-ns-001-p001",
            })
            self.assertEqual(st, 200, created)
            self.assertEqual(len(created["videoRequest"]["scenes"]), 7)
            self.assertEqual(sum(s["durationMs"] for s in created["videoRequest"]["scenes"]), 30000)
        finally:
            studio1.close()
            httpd1.shutdown()
            httpd1.server_close()

        # 2. Recarga: novo Studio sobre ws1
        httpd1b, studio1b = video_studio.make_server(ws1, 0)
        th1b = threading.Thread(target=httpd1b.serve_forever, daemon=True)
        th1b.start()
        port1b = httpd1b.server_port
        base1b = f"http://127.0.0.1:{port1b}"
        try:
            st, opened = _http_json(f"{base1b}/api/works/open?id={wid}")
            self.assertEqual(st, 200, opened)
            self.assertEqual(len(opened["videoRequest"]["scenes"]), 7)
            self.assertEqual(
                opened["videoRequest"]["scenes"][0]["caption"],
                "Você consegue visualizar os agendamentos do seu salão com clareza?",
            )

            # 3. Pre-voo HTTP + CLI studio_preflight.py
            item_reels = {"workId": wid, "modality": "video", "profileId": "instagram-reels-video"}
            st, pre = _http_json(f"{base1b}/api/queue/preflight", method="POST", origin=base1b, body={"items": [item_reels]})
            self.assertEqual(st, 200, pre)
            self.assertTrue(pre["ready"], pre)

            cli_pre = subprocess.run(
                [sys.executable, os.path.join(ws1, "tools", "studio_preflight.py"),
                 "--port", str(port1b), "--work-id", wid, "--modality", "video",
                 "--profile", "instagram-reels-video", "--json"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            )
            self.assertEqual(cli_pre.returncode, 0, cli_pre.stderr)
            self.assertEqual(json.loads(cli_pre.stdout)["items"][0]["status"], "ready")

            # 4. Enfileirar (idempotencia) e aguardar estado terminal
            idem = f"idem-{uuid.uuid4().hex[:8]}"
            st, e1 = _http_json(f"{base1b}/api/queue/enqueue", method="POST", origin=base1b, body={"items": [item_reels], "idempotencyKey": idem})
            self.assertEqual(st, 200, e1)
            st, e2 = _http_json(f"{base1b}/api/queue/enqueue", method="POST", origin=base1b, body={"items": [item_reels], "idempotencyKey": idem})
            self.assertEqual(st, 200, e2)
            self.assertEqual(e1["batch"]["batchId"], e2["batch"]["batchId"])
            self.assertTrue(e2["batch"].get("deduplicated"))
            batch_id = e1["batch"]["batchId"]

            deadline = time.monotonic() + 240.0
            batch = None
            while time.monotonic() < deadline:
                _, b_res = _http_json(f"{base1b}/api/queue/batch?id={batch_id}")
                batch = b_res["batch"]
                if batch["counts"]["queued"] == 0 and batch["counts"]["running"] == 0:
                    break
                time.sleep(0.4)
            self.assertIsNotNone(batch)
            self.assertEqual(batch["counts"]["completed"], 1, batch)

            # 5. Revisao & Entrega: salvar ficha, aprovar fixture tecnica e gerar ZIP 1
            st, rev = _http_json(f"{base1b}/api/works/editorial/save", method="POST", origin=base1b, body={
                "workId": wid,
                "briefing": {
                    "objective": "Provar fluxo NS-001",
                    "audience": "Donos de salao",
                    "coreMessage": "Agenda clara",
                    "supportEvidence": "Fixture tecnica",
                    "hook": "NS-001-H15",
                    "scriptSummary": "7 cenas",
                    "cta": "Conheca a agenda do Marca Salao.",
                },
                "channels": {
                    "instagram-reels-video": {
                        "title": "",
                        "postText": "Conheça a agenda do Marca Salão.",
                        "cta": "Acesse o link na bio",
                        "destinationUrl": "https://marcasalao.com.br",
                        "hashtags": "#MarcaSalao",
                    }
                },
            })
            self.assertEqual(st, 200, rev)
            piece = next(p for p in rev["pieces"] if p["pieceKey"] == "video:instagram-reels-video")
            chan = next(c for c in rev["channels"] if c["profileId"] == "instagram-reels-video")

            st, rev = _http_json(f"{base1b}/api/works/review/decide", method="POST", origin=base1b, body={
                "workId": wid, "targetType": "piece", "modality": "video",
                "profileId": "instagram-reels-video",
                "expectedVersionId": piece["deliveryVersionId"],
                "expectedDraftFingerprint": piece["currentDraftFingerprint"],
                "decision": "approved_for_local_delivery", "note": "fixture tecnica aprovada",
            })
            self.assertEqual(st, 200, rev)
            st, rev = _http_json(f"{base1b}/api/works/review/decide", method="POST", origin=base1b, body={
                "workId": wid, "targetType": "channel", "profileId": "instagram-reels-video",
                "expectedCopySha256": chan["copySha256"],
                "decision": "approved_for_local_delivery", "note": "copia tecnica aprovada",
            })
            self.assertEqual(st, 200, rev)

            st, pkg1 = _http_json(f"{base1b}/api/works/package", method="POST", origin=base1b, body={
                "workId": wid,
                "pieces": [{"modality": "video", "profileId": "instagram-reels-video",
                            "expectedVersionId": piece["deliveryVersionId"],
                            "expectedDraftFingerprint": piece["currentDraftFingerprint"]}],
                "channels": [{"profileId": "instagram-reels-video", "expectedCopySha256": chan["copySha256"]}],
            })
            self.assertEqual(st, 200, pkg1)
            pd1 = pkg1["packageDelivery"]
            sha1 = pd1["lastValidDelivery"]["zipSha256"]

            # Verificar ZIP 1 via endpoint e via delivery_verify CLI e baixar ZIP
            st, ver1 = _http_json(f"{base1b}/api/works/package/verify?id={wid}")
            self.assertEqual(st, 200, ver1)
            self.assertTrue(ver1["verification"]["ok"], ver1)
            zip_sha_obj = ver1["verification"]["zipSha256"]
            actual_sha = zip_sha_obj["actual"] if isinstance(zip_sha_obj, dict) else zip_sha_obj
            self.assertEqual(actual_sha, sha1)

            st_dl, zip1_bytes = _http_bytes(f"{base1b}/api/works/package/download?id={wid}")
            self.assertEqual(st_dl, 200)
            self.assertEqual(hashlib.sha256(zip1_bytes).hexdigest(), sha1)
            with zipfile.ZipFile(io.BytesIO(zip1_bytes), "r") as zf:
                names = zf.namelist()
                self.assertIn("package-manifest.json", names)
                self.assertIn("video/instagram-reels-video/primary-output.mp4", names)

            zip1_abs = os.path.join(ws1, pd1["lastValidDelivery"]["zipPath"].replace("/", os.sep))
            cli_v1 = delivery_verify.verify_package_zip(zip1_abs, expected_zip_sha256=sha1)
            self.assertTrue(cli_v1["ok"], cli_v1)

            # 6. Editar rascunho -> draft_outdated -> reexportar -> reexported_pending -> ZIP 2 invalidando sha1
            _, cur_open = _http_json(f"{base1b}/api/works/open?id={wid}")
            edited_vreq = json.loads(json.dumps(cur_open["videoRequest"]))
            edited_vreq["scenes"][0]["caption"] = "Você consegue visualizar a agenda com clareza? (editado)"
            st, _ = _http_json(f"{base1b}/api/works/save", method="POST", origin=base1b, body={
                "workId": wid, "videoRequest": edited_vreq,
            })
            self.assertEqual(st, 200)
            _, rev_out = _http_json(f"{base1b}/api/works/review?id={wid}")
            p_out = next(p for p in rev_out["pieces"] if p["pieceKey"] == "video:instagram-reels-video")
            self.assertEqual(p_out["status"], "draft_outdated")

            st, e3 = _http_json(f"{base1b}/api/queue/enqueue", method="POST", origin=base1b, body={
                "items": [item_reels], "idempotencyKey": f"idem2-{uuid.uuid4().hex[:8]}",
            })
            self.assertEqual(st, 200, e3)
            b2 = e3["batch"]["batchId"]
            deadline2 = time.monotonic() + 240.0
            while time.monotonic() < deadline2:
                _, br2 = _http_json(f"{base1b}/api/queue/batch?id={b2}")
                if br2["batch"]["counts"]["queued"] == 0 and br2["batch"]["counts"]["running"] == 0:
                    break
                time.sleep(0.4)
            _, rev_re = _http_json(f"{base1b}/api/works/review?id={wid}")
            p_re = next(p for p in rev_re["pieces"] if p["pieceKey"] == "video:instagram-reels-video")
            self.assertEqual(p_re["status"], "reexported_pending")

            # Aprovar nova versao -> gerar ZIP 2 -> invalidacao do sha1 anterior
            st, _ = _http_json(f"{base1b}/api/works/review/decide", method="POST", origin=base1b, body={
                "workId": wid, "targetType": "piece", "modality": "video", "profileId": "instagram-reels-video",
                "expectedVersionId": p_re["deliveryVersionId"],
                "expectedDraftFingerprint": p_re["currentDraftFingerprint"],
                "decision": "approved_for_local_delivery",
            })
            self.assertEqual(st, 200)
            st, pkg2 = _http_json(f"{base1b}/api/works/package", method="POST", origin=base1b, body={
                "workId": wid,
                "pieces": [{"modality": "video", "profileId": "instagram-reels-video",
                            "expectedVersionId": p_re["deliveryVersionId"],
                            "expectedDraftFingerprint": p_re["currentDraftFingerprint"]}],
                "channels": [{"profileId": "instagram-reels-video", "expectedCopySha256": chan["copySha256"]}],
            })
            self.assertEqual(st, 200, pkg2)
            pd2 = pkg2["packageDelivery"]
            sha2 = pd2["lastValidDelivery"]["zipSha256"]
            self.assertNotEqual(sha2, sha1)
            zip2_abs = os.path.join(ws1, pd2["lastValidDelivery"]["zipPath"].replace("/", os.sep))
            cli_v2_old_sha = delivery_verify.verify_package_zip(zip2_abs, expected_zip_sha256=sha1)
            self.assertFalse(cli_v2_old_sha["ok"])

            # Snapshot pre-voo e midias em ws1 antes do backup
            opened1 = studio1b.open_work(wid)
            media_hashes1 = {
                m["name"]: swb.sha256_file(render_local.fs_path(os.path.join(ws1, m["path"].replace("/", os.sep)), force=True))
                for m in opened1["workMedia"]
            }
            pre1 = studio1b.queue.preflight([item_reels])
        finally:
            studio1b.close()
            httpd1b.shutdown()
            httpd1b.server_close()

        # 7. Backup em ws1 -> inspect antes/depois das dependencias em ws2 -> restore -> validar em ws2
        with patch("studio_work_backup._find_root", return_value=ws1):
            rc_bkp = swb.cmd_backup(argparse.Namespace(command="backup", work_id=wid, output=zip_backup))
            self.assertEqual(rc_bkp, 0)

        # Inspecionar ANTES de copiar ProjectManifest no ws2 -> deve detectar ausencia
        with patch("studio_work_backup._find_root", return_value=ws2):
            rc_before = swb.cmd_inspect(argparse.Namespace(command="inspect", archive=zip_backup, workspace=ws2))
            self.assertNotEqual(rc_before, 0)

        # Preparar ProjectManifest em ws2 e inspecionar novamente
        pm_rel = os.path.join("platform", "examples", "projects", "marca-salao-social.project.json")
        os.makedirs(render_local.fs_path(os.path.dirname(os.path.join(ws2, pm_rel)), force=True), exist_ok=True)
        shutil.copy2(render_local.fs_path(os.path.join(ws1, pm_rel), force=True), render_local.fs_path(os.path.join(ws2, pm_rel), force=True))

        with patch("studio_work_backup._find_root", return_value=ws2):
            rc_after = swb.cmd_inspect(argparse.Namespace(command="inspect", archive=zip_backup, workspace=ws2))
            self.assertEqual(rc_after, 0)
            rc_rest = swb.cmd_restore(argparse.Namespace(command="restore", archive=zip_backup, workspace=ws2))
            self.assertEqual(rc_rest, 0)
            # Segunda restauracao no mesmo destino existente deve recusar sem sobrescrever
            rc_rest_dup = swb.cmd_restore(argparse.Namespace(command="restore", archive=zip_backup, workspace=ws2))
            self.assertNotEqual(rc_rest_dup, 0)

        studio2 = video_studio.Studio(ws2, port=0, auto_start_queue=False)
        try:
            opened2 = studio2.open_work(wid)
            self.assertEqual(opened2["videoRequest"]["scenes"], opened1["videoRequest"]["scenes"])
            media_hashes2 = {
                m["name"]: swb.sha256_file(render_local.fs_path(os.path.join(ws2, m["path"].replace("/", os.sep)), force=True))
                for m in opened2["workMedia"]
            }
            self.assertEqual(media_hashes1, media_hashes2)
            self.assertFalse(os.path.exists(render_local.fs_path(studio2.confine_workspace(opened2["work"]["paths"]["reviewStateFile"]), force=True)))
            self.assertEqual(len(studio2.queue.list_queue()["items"]), 0)
            pre2 = studio2.queue.preflight([item_reels])
            self.assertEqual(pre1["ready"], pre2["ready"])
            self.assertEqual([b["code"] for b in pre1["items"][0]["blockers"]], [b["code"] for b in pre2["items"][0]["blockers"]])
        finally:
            studio2.close()

        # Fila no workspace de origem preservada
        studio1c = video_studio.Studio(ws1, port=0, auto_start_queue=False)
        try:
            self.assertGreaterEqual(len(studio1c.queue.list_queue()["items"]), 1)
        finally:
            studio1c.close()

        # 8. Validar tambem deteccao de sharedMedia externa antes/depois em ws2
        shared_wid = "shared-dep-test"
        s1 = video_studio.Studio(ws1, port=0, auto_start_queue=False)
        try:
            sh_created = s1.create_work({"id": shared_wid, "name": "Shared Dep", "template": "example:marca-salao-ns-001-p001"})
            ext_rel = ".workspace/shared/extra-frame.png"
            ext_abs_1 = os.path.join(ws1, ext_rel.replace("/", os.sep))
            campaign_proof.write_scene_png(ext_abs_1, shared_wid, "ext-frame", 1)
            vr = sh_created["videoRequest"]
            vr["media"][0]["path"] = ext_rel
            s1.save_work({"workId": shared_wid, "videoRequest": vr})
        finally:
            s1.close()

        with patch("studio_work_backup._find_root", return_value=ws1):
            self.assertEqual(swb.cmd_backup(argparse.Namespace(command="backup", work_id=shared_wid, output=zip_shared)), 0)
        with patch("studio_work_backup._find_root", return_value=ws2):
            self.assertNotEqual(swb.cmd_inspect(argparse.Namespace(command="inspect", archive=zip_shared, workspace=ws2)), 0)
            ext_abs_2 = os.path.join(ws2, ext_rel.replace("/", os.sep))
            os.makedirs(render_local.fs_path(os.path.dirname(ext_abs_2), force=True), exist_ok=True)
            shutil.copy2(render_local.fs_path(ext_abs_1, force=True), render_local.fs_path(ext_abs_2, force=True))
            self.assertEqual(swb.cmd_inspect(argparse.Namespace(command="inspect", archive=zip_shared, workspace=ws2)), 0)


if __name__ == "__main__":
    unittest.main()
