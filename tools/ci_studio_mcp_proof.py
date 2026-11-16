"""Prova de uso do servidor MCP de Planejamento do Video Studio (CI).

Sobe um Studio real em loopback com um trabalho ficticio e exercita o servidor
MCP como subprocesso stdio com um cliente MCP de teste, em dois papeis (Codex e
Claude Code) sobre o MESMO trabalho. Cobre o handshake initialize/tools/list/
tools/call, as rotas HTTP reais e a persistencia do historico; duas propostas
creative validas (roteiro e carrossel) com dois IDs; o caminho completo
(incorporar + aplicar) mudando os editores somente apos acao do operador;
rejeicoes (trabalho inexistente, payload invalido, fingerprint vencido, edicao
concorrente no momento da gravacao) preservando o estado; dois envios validos
concorrentes; Studio indisponivel; e varredura de segredos/caminhos nas respostas.

Uso: python tools/ci_studio_mcp_proof.py --port 8810
"""

import argparse
import json
import os
import shutil
import socket
import sys
import threading
import time

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
TOOLS = os.path.join(ROOT, 'tools')
for p in (ROOT, TOOLS):
    if p not in sys.path:
        sys.path.insert(0, p)

import render_local
import studio_planning
import studio_review
import video_studio
from tools.tests.test_studio_mcp import McpStdioClient, creative_suggestion, briefing_suggestion

PROJECT_MS = 'platform/examples/projects/marca-salao-social.project.json'
WORK_ID = 'ci-mcp-planejamento'


def _free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _rmtree(path):
    target = render_local.fs_path(path, force=True)
    if os.path.exists(target):
        shutil.rmtree(target, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prova de uso MCP do Planejamento (Studio)')
    parser.add_argument('--port', type=int, default=8810)
    args = parser.parse_args(argv)

    import http.client as http_client

    def http(method, path, body=None):
        conn = http_client.HTTPConnection('127.0.0.1', args.port, timeout=120)
        headers = {'Host': f'127.0.0.1:{args.port}'}
        if method == 'POST':
            headers['Origin'] = f'http://127.0.0.1:{args.port}'
            headers['Content-Type'] = 'application/json'
        conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res.status, json.loads(data)

    _rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', WORK_ID))
    httpd, studio = video_studio.make_server(ROOT, args.port)
    studio.port = args.port
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base_ready = False
    for _ in range(60):
        try:
            http('GET', '/api/readiness')
            base_ready = True
            break
        except OSError:
            time.sleep(0.25)
    assert base_ready, 'Studio nao ficou pronto'

    clients = []

    def new_client(label, port=None, env=None, version='2025-06-18'):
        c = McpStdioClient(port if port is not None else args.port, label=label, env=env)
        clients.append(c)
        init = c.initialize(version=version)
        assert init['result']['serverInfo']['name'] == 'video-studio-planejamento'
        return c

    def overview():
        st, ov = http('GET', f'/api/works/planning?id={WORK_ID}')
        assert st == 200, ov
        return ov

    def history_ids():
        return [r['suggestionId'] for r in overview()['planning']['suggestionHistory']]

    def consult(c):
        res = c.call_tool('consultar_planejamento', {'workId': WORK_ID})
        assert not res['result'].get('isError'), res
        return res['result']['structuredContent']

    def enviar(c, fp, suggestion):
        return c.call_tool('enviar_proposta', {
            'workId': WORK_ID, 'expectedContextFingerprint': fp, 'suggestion': suggestion})

    summary = {'clients': 0, 'proposals': 0, 'rejections': {}, 'leaks': 0}
    try:
        st, created = http('POST', '/api/works/create', {
            'id': WORK_ID, 'name': 'CI MCP Planejamento', 'project': PROJECT_MS, 'template': 'blank'})
        assert st == 200, created
        st, _ = http('POST', '/api/works/planning/save', {
            'workId': WORK_ID, 'ideaText': 'Video curto sobre a agenda do salao',
            'briefing': {'objective': 'Organizar horarios', 'audience': 'Donos de salao',
                         'coreMessage': 'Agenda visual sem caderno'}})
        assert st == 200

        codex = new_client('codex')
        claude = new_client('claude-code')
        summary['clients'] = 2
        listing = codex.request('tools/list')
        names = {t['name'] for t in listing['result']['tools']}
        assert names == {'consultar_planejamento', 'enviar_proposta'}, names

        ctx_a = consult(codex)
        ctx_b = consult(claude)
        assert ctx_a['contextFingerprint'] == ctx_b['contextFingerprint']
        assert 'PlanningSuggestion v1' in ctx_a['instructions']['systemPrompt']
        profiles = ctx_a['allowedProfiles']
        fp = ctx_a['contextFingerprint']

        # Duas propostas validas sobre o mesmo contexto, clientes distintos.
        before = history_ids()
        res_a = enviar(codex, fp, creative_suggestion(profiles, 'video'))
        res_b = enviar(claude, fp, creative_suggestion(profiles, 'carousel'))
        assert not res_a['result'].get('isError'), res_a
        assert not res_b['result'].get('isError'), res_b
        id_a = res_a['result']['structuredContent']['suggestionId']
        id_b = res_b['result']['structuredContent']['suggestionId']
        assert id_a != id_b
        after = history_ids()
        assert id_a in after and id_b in after
        assert len(after) == len(before) + 2
        summary['proposals'] = 2
        summary['suggestionIds'] = [id_a, id_b]
        summary['historyCount'] = len(after)

        # Caminho completo com a proposta de roteiro: editores so mudam apos
        # incorporar + aplicar pelo operador (via rotas HTTP reais do Studio).
        st, opened = http('GET', f'/api/works/open?id={WORK_ID}')
        video_before = opened['videoRequest']
        sug_video = creative_suggestion(profiles, 'video')
        media_ids = [m['id'] for m in video_before.get('media', [])]
        for i, scene in enumerate(sug_video['videoScenes']):
            scene['mediaId'] = media_ids[i % len(media_ids)]
        res_full = enviar(codex, fp, sug_video)
        assert not res_full['result'].get('isError'), res_full
        sid_full = res_full['result']['structuredContent']['suggestionId']
        st, opened_mid = http('GET', f'/api/works/open?id={WORK_ID}')
        assert opened_mid['videoRequest'] == video_before, 'registro nao pode alterar o editor'
        fp_mid = overview()['fingerprints']['contextFingerprint']
        st_acc, acc = http('POST', '/api/works/planning/accept-suggestion', {
            'workId': WORK_ID, 'suggestionId': sid_full, 'expectedContextFingerprint': fp_mid})
        assert st_acc == 200, acc
        st, opened_acc = http('GET', f'/api/works/open?id={WORK_ID}')
        assert opened_acc['videoRequest'] == video_before, 'incorporar nao altera o editor de video'
        fps = acc['fingerprints']
        st_app, app = http('POST', '/api/works/planning/apply', {
            'workId': WORK_ID, 'expectedContextFingerprint': fps['contextFingerprint'],
            'expectedEditorialBriefingSha256': fps['editorialBriefingSha256'],
            'expectedDraftsSha256': fps['draftsSha256'],
            'applyBriefing': False, 'applyVideo': True, 'applyCarousel': False,
            'applyMotionSync': False, 'channelsToApply': [],
            'preserveSceneIds': [], 'preserveCardIds': [], 'preserveChannelIds': []})
        assert st_app == 200, app
        assert app['applied']['video']['status'] == 'applied', app
        st, opened_after = http('GET', f'/api/works/open?id={WORK_ID}')
        assert opened_after['videoRequest'] != video_before, 'aplicar deve alterar o editor de video'
        summary['editorChangedOnlyAfterApply'] = True

        # Rejeicao: trabalho inexistente.
        r = codex.call_tool('consultar_planejamento', {'workId': 'ci-mcp-nao-existe'})
        assert r['result']['isError'] and 'nao encontrado' in r['result']['content'][0]['text']
        summary['rejections']['nonexistentWork'] = True

        # Rejeicao: payload invalido (hook selecionado desconhecido), estado preservado.
        hist_before = history_ids()
        bad = creative_suggestion(profiles, 'video')
        bad['selectedHookId'] = 'hook-inexistente'
        r = enviar(codex, overview()['fingerprints']['contextFingerprint'], bad)
        assert r['result']['isError']
        assert r['result']['structuredContent']['code'] == 'PLANNING_SELECTED_HOOK_UNKNOWN'
        assert history_ids() == hist_before
        summary['rejections']['invalidPayload'] = True

        # Rejeicao: fingerprint vencido apos edicao do operador.
        old_fp = overview()['fingerprints']['contextFingerprint']
        hist_before = history_ids()
        st, _ = http('POST', '/api/works/planning/save', {'workId': WORK_ID, 'ideaText': 'Ideia editada'})
        assert st == 200
        new_fp = overview()['fingerprints']['contextFingerprint']
        assert old_fp != new_fp
        r = enviar(claude, old_fp, creative_suggestion(profiles, 'carousel'))
        assert r['result']['isError']
        assert r['result']['structuredContent']['code'] == 'CONTEXT_CONFLICT'
        assert history_ids() == hist_before
        summary['rejections']['staleFingerprint'] = True

        # Rejeicao: edicao concorrente no momento da gravacao (reconferencia sob lock).
        cur_fp = overview()['fingerprints']['contextFingerprint']
        hist_before = history_ids()
        original = studio_planning.build_planning_overview
        calls = {'n': 0}

        def patched(studio, work_id):
            ov = original(studio, work_id)
            calls['n'] += 1
            if calls['n'] == 1:
                studio_planning.save_planning(studio, work_id, {'ideaText': 'edicao concorrente no envio'})
            return ov

        studio_planning.build_planning_overview = patched
        try:
            try:
                studio_planning.validate_and_stage_suggestion(studio, WORK_ID, {
                    'expectedContextFingerprint': cur_fp,
                    'suggestion': creative_suggestion(profiles, 'video')}, mode='import')
                raise AssertionError('edicao concorrente deveria conflitar sob o lock')
            except studio_review.ReviewVersionConflictError:
                pass
        finally:
            studio_planning.build_planning_overview = original
        assert history_ids() == hist_before
        assert overview()['planning']['ideaText'] == 'edicao concorrente no envio'
        summary['rejections']['concurrentEditAtWrite'] = True

        # Dois envios validos concorrentes sobre o mesmo contexto: ambos registrados.
        cur_fp = overview()['fingerprints']['contextFingerprint']
        hist_before = history_ids()
        results = {}

        def submit(key, client, focus):
            results[key] = enviar(client, cur_fp, creative_suggestion(profiles, focus))

        t1 = threading.Thread(target=submit, args=('a', codex, 'video'))
        t2 = threading.Thread(target=submit, args=('b', claude, 'carousel'))
        t1.start(); t2.start(); t1.join(); t2.join()
        assert not results['a']['result'].get('isError'), results['a']
        assert not results['b']['result'].get('isError'), results['b']
        id_ca = results['a']['result']['structuredContent']['suggestionId']
        id_cb = results['b']['result']['structuredContent']['suggestionId']
        after = history_ids()
        assert id_ca in after and id_cb in after
        assert len(after) == len(hist_before) + 2
        summary['concurrentValidSubmits'] = 2

        # Studio indisponivel: instrucao de como iniciar a instancia local.
        dead_port = _free_port()
        dead_client = new_client('codex', port=dead_port)
        r = dead_client.call_tool('consultar_planejamento', {'workId': WORK_ID})
        assert r['result']['isError']
        assert r['result']['structuredContent']['code'] == 'STUDIO_UNAVAILABLE'
        assert 'video_studio.py --port' in r['result']['content'][0]['text']
        summary['rejections']['studioUnavailable'] = True

        # UTF-8 sob PYTHONIOENCODING=cp1252: texto recebido e gravado com acentos.
        accented = 'Ação e narração — coração da agenda'
        st, _ = http('POST', '/api/works/planning/save', {'workId': WORK_ID, 'briefing': {'coreMessage': accented}})
        assert st == 200
        cp_client = new_client('codex-cp1252', env={'PYTHONIOENCODING': 'cp1252'})
        ctx_cp = cp_client.call_tool('consultar_planejamento', {'workId': WORK_ID})['result']['structuredContent']
        assert ctx_cp['briefing']['coreMessage'] == accented, ctx_cp['briefing']
        sug_cp = creative_suggestion(profiles, 'video')
        sug_cp['videoScenes'][0]['caption'] = accented
        r_cp = enviar(cp_client, overview()['fingerprints']['contextFingerprint'], sug_cp)
        assert not r_cp['result'].get('isError'), r_cp
        sid_cp = r_cp['result']['structuredContent']['suggestionId']
        rec_cp = next(r for r in overview()['planning']['suggestionHistory'] if r['suggestionId'] == sid_cp)
        assert rec_cp['suggestion']['videoScenes'][0]['caption'] == accented
        summary['utf8UnderCp1252'] = True

        # Etapa: briefing valido enviado pelo MCP e rejeitado (stage creative); Studio segue importando briefing.
        hist_before = history_ids()
        r_b = enviar(codex, overview()['fingerprints']['contextFingerprint'], briefing_suggestion(profiles))
        assert r_b['result']['isError']
        assert r_b['result']['structuredContent']['code'] == 'PLANNING_STAGE_MISMATCH'
        assert history_ids() == hist_before
        st_b, imp_b = http('POST', '/api/works/planning/import', {
            'workId': WORK_ID, 'stage': 'briefing', 'suggestion': briefing_suggestion(profiles)})
        assert st_b == 200, imp_b
        summary['rejections']['mcpBriefingStage'] = True
        summary['studioBriefingImportOk'] = True

        # Negociacao de versao: anunciadas ecoam; fora da lista -> 2025-06-18; lote -> Invalid Request.
        v_old = new_client('ver-2024-11-05', version='2024-11-05')
        assert v_old.request('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {},
                                            'clientInfo': {'name': 'v', 'version': '1'}})['result']['protocolVersion'] == '2024-11-05'
        v_out = new_client('ver-out', version='2025-03-26')
        assert v_out.request('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {},
                                            'clientInfo': {'name': 'v', 'version': '1'}})['result']['protocolVersion'] == '2025-06-18'
        batch_resp = codex.send_raw([{'jsonrpc': '2.0', 'id': 900, 'method': 'ping'},
                                     {'jsonrpc': '2.0', 'id': 901, 'method': 'ping'}])
        assert batch_resp['error']['code'] == -32600, batch_resp
        summary['versionNegotiation'] = True
        summary['batchRejected'] = True

        # Varredura de segredos/caminhos internos em todas as respostas MCP.
        forbidden = ('"secret"', '"apiKey"', '"credentialValue"', '"connectionId"',
                     '"endpoint"', '"llmConfig"', '"textConnection"', '.workspace',
                     ROOT.replace('\\', '/'))
        leaks = []
        for c in clients:
            blob = '\n'.join(c.raw_responses)
            for f in forbidden:
                if f in blob:
                    leaks.append(f)
        assert not leaks, f'vazamento nas respostas MCP: {leaks}'
        summary['leaks'] = 0

        print(json.dumps(summary, ensure_ascii=False))
        return 0
    finally:
        for c in clients:
            c.close()
        studio.close()
        httpd.shutdown()
        httpd.server_close()
        _rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', WORK_ID))


if __name__ == '__main__':
    raise SystemExit(main())