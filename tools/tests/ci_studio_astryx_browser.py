"""Regressao focada de navegador (Chromium/Playwright) para o piloto Astryx do Video Studio.

Executa contra o servidor real `tools/video_studio.py` com o bundle compilado em
`tools/studio/frontend/dist/`, falhando em qualquer excecao JavaScript ou console.error
da aplicacao. Limpa trabalhos/modelos criados em `.workspace/studio/` e encerra o
servidor no bloco finally.

Uso local:
  pip install playwright
  python -m playwright install chromium
  python tools/tests/ci_studio_astryx_browser.py
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Estados finais possiveis de um item da fila (tools/studio_queue.py VALID_STATUSES).
TERMINAL_STATUSES = ('completed', 'failed', 'cancelled', 'interrupted')
# Teto de espera por um estado terminal antes de simular SNAPSHOT_LEGACY.
TERMINAL_WAIT_SECONDS = 300.0


def _free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _wait_ready(base_url, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f'{base_url}/api/readiness', timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError(f'Studio nao respondeu em {base_url} dentro de {timeout}s')


def _cleanup_test_artifacts(work_id, template_id, batch_id=None):
    work_dir = os.path.join(ROOT, '.workspace', 'studio', 'works', work_id)
    if os.path.isdir(work_dir):
        shutil.rmtree(work_dir, ignore_errors=True)
    tpl_dir = os.path.join(ROOT, '.workspace', 'studio', 'templates', template_id)
    if os.path.isdir(tpl_dir):
        shutil.rmtree(tpl_dir, ignore_errors=True)
    db_path = os.path.join(ROOT, '.workspace', 'studio', 'production-queue.sqlite')
    if batch_id and os.path.isfile(db_path):
        import sqlite3
        try:
            conn = sqlite3.connect(db_path)
            conn.execute('DELETE FROM queue_items WHERE work_id = ?', (work_id,))
            if batch_id:
                conn.execute('DELETE FROM queue_items WHERE batch_id = ?', (batch_id,))
                conn.execute('DELETE FROM queue_batches WHERE batch_id = ?', (batch_id,))
            conn.execute('DELETE FROM queue_batches WHERE label IN (?, ?)', ('Lote CI Astryx', 'Lote Preflight UI'))
            conn.commit()
            conn.close()
        except Exception:
            pass


def run_browser_regression():
    dist_dir = os.path.join(ROOT, 'tools', 'studio', 'frontend', 'dist')
    manifest_path = os.path.join(dist_dir, '.vite', 'manifest.json')
    if not os.path.isfile(manifest_path):
        raise RuntimeError('Bundle ausente: execute npm run build em tools/studio/frontend antes da prova.')

    port = _free_port()
    base_url = f'http://127.0.0.1:{port}'
    work_id = 'ci-astryx-piloto-01'
    template_id = 'ci-modelo-astryx'
    _cleanup_test_artifacts(work_id, template_id)

    proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, 'tools', 'video_studio.py'), '--port', str(port)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_ready(base_url)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1280, 'height': 840})
            page = context.new_page()

            page_errors = []
            console_errors = []
            readiness_requests = []
            create_requests = []
            retry_requests = []
            preflight_requests = []
            enqueue_requests = []
            allow_expected_409 = [False]
            allow_expected_preflight_abort = [False]

            page.on('pageerror', lambda err: page_errors.append(str(err)))

            def _on_console(msg):
                if msg.type == 'error':
                    text = msg.text
                    # Ignora 404 de favicon.ico que nao faz parte do app
                    if 'favicon.ico' not in text and '404 (Not Found)' not in text:
                        if allow_expected_409[0] and '409 (Conflict)' in text:
                            return
                        if allow_expected_preflight_abort[0] and ('Failed to fetch' in text or 'ERR_FAILED' in text or 'NetworkError' in text):
                            return
                        console_errors.append(text)

            page.on('console', _on_console)

            # Registra metodo, rota e status de toda resposta HTTP de erro (>= 400) para
            # identificar a origem de falhas silenciosas em chamadas feitas via page.evaluate.
            http_error_responses = []

            def _on_response(resp):
                try:
                    status = resp.status
                except Exception:
                    return
                if status < 400:
                    return
                route = resp.url.split('?')[0]
                # Ignora 404 de favicon.ico que nao faz parte do app
                if route.endswith('/favicon.ico'):
                    return
                # 409 e esperado no retry com snapshot legado (SNAPSHOT_LEGACY)
                if allow_expected_409[0] and status == 409:
                    return
                method = resp.request.method
                http_error_responses.append((method, route, status))
                print(
                    f'[ci_studio_astryx_browser][http-error] {method} {route} -> {status}',
                    flush=True,
                )

            page.on('response', _on_response)
            page.on('request', lambda req: (
                readiness_requests.append(req.url) if '/api/readiness' in req.url else None,
                create_requests.append(req.url) if '/api/works/create' in req.url else None,
                retry_requests.append((req.url, req.post_data)) if '/api/queue/retry' in req.url else None,
                preflight_requests.append((req.url, req.post_data)) if '/api/queue/preflight' in req.url else None,
                enqueue_requests.append((req.url, req.post_data)) if '/api/queue/enqueue' in req.url else None,
            ))

            # 1. Inicializacao com lista (potencialmente) vazia
            print('[ci_studio_astryx_browser] Etapa 1: abertura inicial...', flush=True)
            page.goto(base_url, wait_until='networkidle')
            page.locator('[data-testid="astryx-home-pilot"]').wait_for(state='visible', timeout=20000)
            legacy_hidden = page.locator('#home-legacy-root').get_attribute('hidden')
            assert legacy_hidden is not None, '#home-legacy-root deve estar oculto quando React monta'
            assert not page_errors, f'Excecoes JS na abertura: {page_errors}'
            assert not console_errors, f'Erros de console na abertura: {console_errors}'

            # 2. Reverificar ambiente: exatamente 1 GET /api/readiness por clique
            print('[ci_studio_astryx_browser] Etapa 2: reverificar ambiente...', flush=True)
            before_readiness = len(readiness_requests)
            with page.expect_response(lambda r: '/api/readiness' in r.url and r.status == 200, timeout=20000):
                page.locator('#btn-refresh-readiness').click()
            page.locator('#astryx-readiness-feedback').wait_for(state='visible', timeout=20000)
            assert len(readiness_requests) - before_readiness == 1, (
                f'Esperado 1 GET /api/readiness por clique, obtidos {len(readiness_requests) - before_readiness}'
            )
            assert not page_errors, f'Excecoes JS apos Reverificar ambiente: {page_errors}'

            # 3. Criar e abrir trabalho: exatamente 1 POST /api/works/create
            print('[ci_studio_astryx_browser] Etapa 3: criar e abrir trabalho...', flush=True)
            page.locator('#work-name').fill('CI Astryx Piloto 01')
            page.locator('#work-id').fill(work_id)
            page.locator('#work-project').select_option('platform/examples/projects/marca-salao-social.project.json')
            before_create = len(create_requests)
            with page.expect_response(lambda r: '/api/works/create' in r.url and r.status == 200, timeout=20000):
                page.locator('#btn-create-work').click()
            page.locator('#active-work-bar').wait_for(state='visible', timeout=20000)
            assert work_id in page.locator('#active-work-title').inner_text()
            assert len(create_requests) - before_create == 1, (
                f'Esperado 1 POST /api/works/create por clique, obtidos {len(create_requests) - before_create}'
            )
            assert not page_errors, f'Excecoes JS apos criar trabalho: {page_errors}'

            # 4. Inicializacao com trabalhos existentes e acionamento unico de Criar a partir de modelo
            print('[ci_studio_astryx_browser] Etapa 4: modelos e dialogo...', flush=True)
            page.reload(wait_until='networkidle')
            page.locator('[data-testid="astryx-home-pilot"]').wait_for(state='visible', timeout=20000)
            page.locator('#works-table').wait_for(state='visible', timeout=20000)
            assert work_id in page.locator('#works-table').inner_text()

            # Salva como modelo
            row_btn = page.locator('#works-table tr', has_text=work_id).get_by_role('button', name='Salvar como modelo')
            row_btn.click()
            page.locator('#tpl-save-name').fill('CI Modelo Astryx')
            with page.expect_response(lambda r: '/api/templates/save' in r.url and r.status == 200, timeout=20000):
                page.locator('#btn-tpl-save-confirm').click()
            page.locator('#tpl-save-name').wait_for(state='hidden', timeout=20000)

            # Clique unico em Criar a partir de modelo: 1 dialogo, 1 #tpl-create-revision
            trigger = page.locator('#btn-open-template-create')
            trigger.click()
            page.locator('#tpl-create-revision').wait_for(state='visible', timeout=20000)
            rev_count = page.locator('#tpl-create-revision').count()
            assert rev_count == 1, f'Esperado 1 #tpl-create-revision no DOM, obtidos {rev_count}'
            dialog_count = page.locator('dialog[open]').count()
            assert dialog_count == 1, f'Esperado 1 dialog aberto, obtidos {dialog_count}'

            # Escape fecha dialogo e devolve foco ao disparador
            page.keyboard.press('Escape')
            page.locator('#tpl-create-revision').wait_for(state='hidden', timeout=20000)
            assert page.locator('dialog[open]').count() == 0, 'Nenhum dialog deve permanecer aberto apos Escape'

            # 4b. Pre-voo no dialogo Exportar em lote (backend real + bloqueio corrigivel + simulacoes)
            print('[ci_studio_astryx_browser] Etapa 4b: pre-voo no dialogo Exportar em lote...', flush=True)
            work_row = page.locator('#works-table tr', has_text=work_id)
            work_row.locator('input[type="checkbox"]').check()
            batch_btn = page.get_by_role('button', name='Exportar em lote')
            with page.expect_response(lambda r: '/api/queue/plan' in r.url and r.status == 200, timeout=20000):
                batch_btn.click()
            page.locator('#batch-export-dialog').wait_for(state='visible', timeout=20000)
            assert page.locator('#batch-export-dialog').count() == 1

            # Verificar selecao (leitura): 1 preflight, 0 enqueue
            before_pf = len(preflight_requests)
            before_enq = len(enqueue_requests)
            with page.expect_response(lambda r: '/api/queue/preflight' in r.url and r.status == 200, timeout=30000):
                page.locator('#btn-batch-verify').click()
            page.locator('#batch-preflight-summary').get_by_text('pronto(s)').wait_for(state='visible', timeout=20000)
            assert len(preflight_requests) - before_pf == 1, 'Esperado 1 POST /api/queue/preflight ao verificar'
            assert len(enqueue_requests) - before_enq == 0, 'Verificar selecao nao deve enviar enqueue'
            page.keyboard.press('Escape')
            page.locator('#batch-export-dialog').wait_for(state='hidden', timeout=20000)

            # Remove obrigatoriamente um arquivo de midia apos o plano para provocar bloqueio real no pre-voo
            media_file = os.path.join(ROOT, '.workspace', 'studio', 'works', work_id, 'media', 'tela-abertura.png')
            media_bak = media_file + '.bak'
            with page.expect_response(lambda r: '/api/queue/plan' in r.url and r.status == 200, timeout=20000):
                batch_btn.click()
            page.locator('#batch-export-dialog').wait_for(state='visible', timeout=20000)
            page.locator('#batch-label-input').fill('Lote Preflight UI')
            shutil.move(media_file, media_bak)
            try:
                with page.expect_response(lambda r: '/api/queue/preflight' in r.url and r.status == 200, timeout=30000):
                    page.locator('#btn-batch-confirm').click()
                page.locator('#batch-confirm-feedback').get_by_text('Enfileiramento bloqueado').wait_for(state='visible', timeout=20000)
                page.locator('#batch-export-dialog').get_by_text('MEDIA_FILE_MISSING').first.wait_for(state='visible', timeout=20000)
                assert len(enqueue_requests) == before_enq, 'Confirmacao bloqueada nao deve enviar enqueue'
            finally:
                if os.path.exists(media_bak) and not os.path.exists(media_file):
                    shutil.move(media_bak, media_file)

            # Apos restaurar a midia, confirma novamente -> 1 preflight + 1 enqueue
            with page.expect_response(lambda r: '/api/queue/preflight' in r.url and r.status == 200, timeout=30000):
                with page.expect_response(lambda r: '/api/queue/enqueue' in r.url and r.status == 200, timeout=30000):
                    page.locator('#btn-batch-confirm').click()
            page.locator('#batch-export-dialog').wait_for(state='hidden', timeout=20000)
            assert len(enqueue_requests) - before_enq == 1, 'Esperado exatamente 1 POST /api/queue/enqueue apos correcao'
            page.locator('#q-batches-list').get_by_text('Lote Preflight UI').wait_for(state='visible', timeout=20000)

            # Volta para Trabalhos & Projetos para testar resposta atrasada, duplo clique, erro e 390px
            page.locator('#mode-home-btn').click()
            page.locator('[data-testid="astryx-home-pilot"]').wait_for(state='visible', timeout=20000)
            with page.expect_response(lambda r: '/api/queue/plan' in r.url and r.status == 200, timeout=20000):
                batch_btn.click()
            page.locator('#batch-export-dialog').wait_for(state='visible', timeout=20000)

            # Duplo clique + fechar durante pre-voo atrasado
            def _delay_route(route):
                time.sleep(0.35)
                route.continue_()

            page.route('**/api/queue/preflight', _delay_route)
            before_pf_delay = len(preflight_requests)
            page.evaluate("() => { const b = document.getElementById('btn-batch-verify'); b.click(); b.click(); }")
            page.locator('#btn-batch-close').click()
            page.locator('#batch-export-dialog').wait_for(state='hidden', timeout=20000)
            time.sleep(0.45)
            assert len(preflight_requests) - before_pf_delay == 1, 'Duplo clique nao deve disparar dois preflights'
            page.unroute('**/api/queue/preflight', _delay_route)

            # Erro de transporte e resposta incompleta
            with page.expect_response(lambda r: '/api/queue/plan' in r.url and r.status == 200, timeout=20000):
                batch_btn.click()
            page.locator('#batch-export-dialog').wait_for(state='visible', timeout=20000)
            allow_expected_preflight_abort[0] = True
            page.route('**/api/queue/preflight', lambda route: route.abort())
            page.locator('#btn-batch-verify').click()
            page.locator('#batch-preflight-summary').get_by_text('Falha ao consultar').wait_for(state='visible', timeout=20000)
            page.unroute('**/api/queue/preflight')
            allow_expected_preflight_abort[0] = False

            page.route('**/api/queue/preflight', lambda route: route.fulfill(
                status=200, content_type='application/json',
                body=json.dumps({'ok': True, 'schemaVersion': 1, 'ready': True, 'items': []}),
            ))
            before_enq_inc = len(enqueue_requests)
            page.locator('#btn-batch-confirm').click()
            page.locator('#batch-confirm-feedback').get_by_text('incompleta').wait_for(state='visible', timeout=20000)
            assert len(enqueue_requests) == before_enq_inc
            page.unroute('**/api/queue/preflight')
            page.keyboard.press('Escape')
            page.locator('#batch-export-dialog').wait_for(state='hidden', timeout=20000)

            # Alteracoes nao salvas no trabalho ativo
            with page.expect_response(lambda r: '/api/works/open' in r.url and r.status == 200, timeout=20000):
                work_row.get_by_role('button', name='Reabrir').click()
            page.locator('#mode-video-btn').click()
            page.locator('#v-title').wait_for(state='visible', timeout=20000)
            page.locator('#v-title').fill('Titulo alterado sem salvar')
            page.locator('#mode-home-btn').click()
            with page.expect_response(lambda r: '/api/queue/plan' in r.url and r.status == 200, timeout=20000):
                batch_btn.click()
            page.locator('#btn-batch-save-active').wait_for(state='visible', timeout=20000)
            with page.expect_response(lambda r: '/api/works/save' in r.url and r.status == 200, timeout=20000):
                page.locator('#btn-batch-save-active').click()
            page.locator('#batch-export-dialog').wait_for(state='visible', timeout=20000)
            assert page.locator('#btn-batch-save-active').count() == 0
            page.keyboard.press('Escape')
            page.locator('#batch-export-dialog').wait_for(state='hidden', timeout=20000)

            # Largura de 390px e teclado
            page.set_viewport_size({'width': 390, 'height': 844})
            with page.expect_response(lambda r: '/api/queue/plan' in r.url and r.status == 200, timeout=20000):
                batch_btn.click()
            page.locator('#batch-export-dialog').wait_for(state='visible', timeout=20000)
            overflow_390 = page.evaluate("""() => {
                const dlg = document.getElementById('batch-export-dialog');
                return {
                    docOverflow: document.documentElement.scrollWidth > 392,
                    dlgOverflow: dlg ? dlg.scrollWidth > dlg.clientWidth + 2 : true,
                };
            }""")
            assert not overflow_390['docOverflow'] and not overflow_390['dlgOverflow'], f'Overflow em 390px: {overflow_390}'
            page.keyboard.press('Escape')
            page.locator('#batch-export-dialog').wait_for(state='hidden', timeout=20000)
            page.set_viewport_size({'width': 1280, 'height': 840})

            # 5. Aba Fila de Producao em React/Astryx: montagem, atualizar fila, filtros e Abrir revisao
            print('[ci_studio_astryx_browser] Etapa 5: aba Fila de Producao...', flush=True)
            page.locator('#mode-queue-btn').click()
            page.locator('[data-testid="astryx-queue-pilot"]').wait_for(state='visible', timeout=20000)
            queue_legacy_hidden = page.locator('#queue-legacy-root').get_attribute('hidden')
            assert queue_legacy_hidden is not None, '#queue-legacy-root deve estar oculto quando React monta'

            with page.expect_response(lambda r: r.url.split('?')[0].endswith('/api/queue') and r.status == 200, timeout=20000):
                page.locator('#btn-q-refresh').click()

            # Enfileira 1 lote de teste via API oficial e valida na UI da fila
            enqueue_res = page.evaluate(f"""async () => {{
                const plan = await fetch('/api/queue/plan', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ workIds: ['{work_id}'] }})
                }}).then(r => r.json());
                const firstOpt = plan.works[0].options.find(o => o.available);
                const res = await fetch('/api/queue/enqueue', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        label: 'Lote CI Astryx',
                        items: [{{ workId: '{work_id}', modality: firstOpt.modality, profileId: firstOpt.profileId }}]
                    }})
                }}).then(r => r.json());
                return res;
            }}""")
            assert enqueue_res.get('ok'), f'Falha ao enfileirar lote de teste: {enqueue_res}'

            with page.expect_response(lambda r: r.url.split('?')[0].endswith('/api/queue') and r.status == 200, timeout=20000):
                page.locator('#btn-q-refresh').click()

            page.locator('#q-batches-list').get_by_text('Lote CI Astryx').wait_for(state='visible', timeout=20000)
            page.locator('#q-items-list').get_by_text(work_id).first.wait_for(state='visible', timeout=20000)

            # Filtro por trabalho preserva selecao e responde 200
            page.locator(f'#q-filter-work option[value="{work_id}"]').wait_for(state='attached', timeout=20000)
            with page.expect_response(lambda r: f'workId={work_id}' in r.url and r.status == 200, timeout=20000):
                page.locator('#q-filter-work').select_option(work_id)
            assert page.locator('#q-filter-work').input_value() == work_id

            # Retry com snapshot indisponivel/legado mantem aviso e unico botao Enfileirar versao atual
            import sqlite3
            db_path = os.path.join(ROOT, '.workspace', 'studio', 'production-queue.sqlite')
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                'SELECT item_id, snapshot_json FROM queue_items WHERE work_id = ? ORDER BY created_at DESC LIMIT 1',
                (work_id,),
            ).fetchone()
            assert row is not None, f'Nenhum item na fila encontrado para {work_id}'
            item_id, snap_raw = row
            conn.close()

            # Espera a peca alcancar um estado terminal antes de simular SNAPSHOT_LEGACY.
            # Nao chamamos POST /api/queue/cancel: a rota so aceita itens `queued` e responde
            # HTTP 400 quando a peca ja esta `running`, que e o caso durante a preparacao.
            deadline = time.time() + TERMINAL_WAIT_SECONDS
            last_status = None
            final_status = None
            while time.time() < deadline:
                conn = sqlite3.connect(db_path)
                st_row = conn.execute('SELECT status FROM queue_items WHERE item_id = ?', (item_id,)).fetchone()
                conn.close()
                current_status = st_row[0] if st_row else None
                if current_status != last_status:
                    print(
                        f'[ci_studio_astryx_browser] item {item_id}: status={current_status}',
                        flush=True,
                    )
                    last_status = current_status
                if current_status in TERMINAL_STATUSES:
                    final_status = current_status
                    break
                time.sleep(0.5)
            assert final_status is not None, (
                f'Peca {item_id} nao alcancou estado terminal em {TERMINAL_WAIT_SECONDS:.0f}s '
                f'(ultimo status: {last_status})'
            )

            conn = sqlite3.connect(db_path)
            snap_obj = json.loads(snap_raw)
            snap_obj['schemaVersion'] = 1
            snap_obj.pop('projectManifestSha256', None)
            conn.execute(
                'UPDATE queue_items SET status = ?, error_code = ?, error_message = ?, snapshot_json = ? WHERE item_id = ?',
                ('failed', 'SNAPSHOT_LEGACY', 'Snapshot legado para prova de retry.', json.dumps(snap_obj), item_id),
            )
            conn.commit()
            conn.close()

            with page.expect_response(lambda r: r.url.split('?')[0].endswith('/api/queue') and r.status == 200, timeout=20000):
                page.locator('#btn-q-refresh').click()

            item_card = page.locator(f'[data-queue-item-id="{item_id}"]')
            item_card.get_by_text('Snapshot legado para prova de retry.').wait_for(state='visible', timeout=20000)
            assert item_card.get_by_role('button', name='Enfileirar versão atual').count() == 1

            allow_expected_409[0] = True
            with page.expect_response(lambda r: '/api/queue/retry' in r.url and r.status == 409, timeout=20000):
                item_card.get_by_role('button', name='Tentar novamente').click()
            item_card.get_by_text('Snapshot anterior indisponível').wait_for(state='visible', timeout=20000)
            allow_expected_409[0] = False

            current_btns = item_card.get_by_role('button', name='Enfileirar versão atual')
            assert current_btns.count() == 1, f'Esperado exatamente 1 botao Enfileirar versao atual, obtidos {current_btns.count()}'

            before_retry = len(retry_requests)
            with page.expect_response(lambda r: '/api/queue/retry' in r.url and r.status == 200, timeout=20000):
                current_btns.first.click()
            new_retries = retry_requests[before_retry:]
            assert len(new_retries) == 1, f'Esperado exatamente 1 POST /api/queue/retry, obtidos {len(new_retries)}'
            retry_payload = json.loads(new_retries[0][1] or '{}')
            assert retry_payload.get('itemId') == item_id and retry_payload.get('useCurrent') is True, (
                f'Payload inesperado em POST /api/queue/retry: {retry_payload}'
            )

            # Abrir revisao a partir da peca da fila ativa o trabalho em Revisao & Entrega
            page.locator('#q-items-list').get_by_role('button', name='Abrir revisão').first.click()
            page.locator('#mode-review').wait_for(state='visible', timeout=20000)
            page.locator('#active-work-bar').wait_for(state='visible', timeout=20000)
            assert work_id in page.locator('#active-work-title').inner_text()

            assert not page_errors, f'Excecoes JS acumuladas: {page_errors}'
            assert not console_errors, f'Erros de console acumulados: {console_errors}'
            assert not http_error_responses, (
                'Respostas HTTP de erro inesperadas (metodo, rota, status): '
                f'{http_error_responses}'
            )

            # 6. Fallback sem bundle em instancia isolada (sem modificar frontend/dist)
            print('[ci_studio_astryx_browser] Etapa 6: fallback sem bundle...', flush=True)
            import tempfile
            import threading
            sys.path.insert(0, os.path.join(ROOT, 'tools'))
            import video_studio as vs_mod

            fb_tmp = tempfile.mkdtemp(prefix='ci-astryx-fallback-', dir=os.path.join(ROOT, '.workspace', 'tmp'))
            fb_studio_dir = os.path.join(fb_tmp, 'studio')
            os.makedirs(fb_studio_dir, exist_ok=True)
            for fname in ('index.html', 'app.js', 'style.css', 'planning.js', 'media.js'):
                shutil.copy2(os.path.join(ROOT, 'tools', 'studio', fname), os.path.join(fb_studio_dir, fname))
            fb_server, fb_studio = vs_mod.make_server(ROOT, 0, auto_start_queue=False)
            fb_studio.studio_dir = fb_studio_dir
            fb_port = fb_server.server_address[1]
            fb_studio.port = fb_port
            fb_thread = threading.Thread(target=fb_server.serve_forever, daemon=True)
            fb_thread.start()
            try:
                fb_page = context.new_page()
                fb_errors = []
                fb_page.on('pageerror', lambda err: fb_errors.append(str(err)))
                fb_page.goto(f'http://127.0.0.1:{fb_port}', wait_until='networkidle')
                fb_page.locator('#home-legacy-root').wait_for(state='visible', timeout=20000)
                fb_row = fb_page.locator('#works-table tr', has_text=work_id)
                fb_row.locator('input[type="checkbox"]').check()
                with fb_page.expect_response(lambda r: '/api/queue/plan' in r.url and r.status == 200, timeout=20000):
                    fb_page.locator('#btn-open-batch-export').click()
                fb_page.locator('#batch-export-dialog').wait_for(state='visible', timeout=20000)
                with fb_page.expect_response(lambda r: '/api/queue/preflight' in r.url and r.status == 200, timeout=30000):
                    fb_page.locator('#btn-batch-verify').click()
                fb_page.locator('#batch-preflight-summary').get_by_text('pronto(s)').wait_for(state='visible', timeout=20000)
                assert fb_page.locator('#btn-batch-confirm').is_visible()
                assert not fb_errors, f'Excecoes JS no fallback: {fb_errors}'
                fb_page.close()
            finally:
                fb_server.shutdown()
                fb_server.server_close()
                shutil.rmtree(fb_tmp, ignore_errors=True)

            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        _cleanup_test_artifacts(work_id, template_id, enqueue_res.get('batch', {}).get('batchId') if 'enqueue_res' in locals() else None)

    print('Regressao de navegador Astryx concluida com sucesso (0 excecoes JS).')


if __name__ == '__main__':
    run_browser_regression()
