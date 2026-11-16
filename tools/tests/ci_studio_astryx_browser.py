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
            conn.execute('DELETE FROM queue_items WHERE batch_id = ?', (batch_id,))
            conn.execute('DELETE FROM queue_batches WHERE batch_id = ?', (batch_id,))
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

            page.on('pageerror', lambda err: page_errors.append(str(err)))

            def _on_console(msg):
                if msg.type == 'error':
                    text = msg.text
                    # Ignora 404 de favicon.ico que nao faz parte do app
                    if 'favicon.ico' not in text and '404 (Not Found)' not in text:
                        console_errors.append(text)

            page.on('console', _on_console)
            page.on('request', lambda req: (
                readiness_requests.append(req.url) if '/api/readiness' in req.url else None,
                create_requests.append(req.url) if '/api/works/create' in req.url else None,
            ))

            # 1. Inicializacao com lista (potencialmente) vazia
            page.goto(base_url, wait_until='networkidle')
            page.locator('[data-testid="astryx-home-pilot"]').wait_for(state='visible', timeout=20000)
            legacy_hidden = page.locator('#home-legacy-root').get_attribute('hidden')
            assert legacy_hidden is not None, '#home-legacy-root deve estar oculto quando React monta'
            assert not page_errors, f'Excecoes JS na abertura: {page_errors}'
            assert not console_errors, f'Erros de console na abertura: {console_errors}'

            # 2. Reverificar ambiente: exatamente 1 GET /api/readiness por clique
            before_readiness = len(readiness_requests)
            with page.expect_response(lambda r: '/api/readiness' in r.url and r.status == 200, timeout=20000):
                page.locator('#btn-refresh-readiness').click()
            page.locator('#astryx-readiness-feedback').wait_for(state='visible', timeout=20000)
            assert len(readiness_requests) - before_readiness == 1, (
                f'Esperado 1 GET /api/readiness por clique, obtidos {len(readiness_requests) - before_readiness}'
            )
            assert not page_errors, f'Excecoes JS apos Reverificar ambiente: {page_errors}'

            # 3. Criar e abrir trabalho: exatamente 1 POST /api/works/create
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

            # 5. Aba Fila de Producao em React/Astryx: montagem, atualizar fila, filtros e Abrir revisao
            page.locator('#mode-queue-btn').click()
            page.locator('[data-testid="astryx-queue-pilot"]').wait_for(state='visible', timeout=20000)
            queue_legacy_hidden = page.locator('#queue-legacy-root').get_attribute('hidden')
            assert queue_legacy_hidden is not None, '#queue-legacy-root deve estar oculto quando React monta'

            with page.expect_response(lambda r: '/api/queue' in r.url and r.status == 200, timeout=20000):
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

            with page.expect_response(lambda r: '/api/queue' in r.url and r.status == 200, timeout=20000):
                page.locator('#btn-q-refresh').click()

            page.locator('#q-batches-list').wait_for(state='visible', timeout=20000)
            assert 'Lote CI Astryx' in page.locator('#q-batches-list').inner_text()
            page.locator('#q-items-list').wait_for(state='visible', timeout=20000)
            assert work_id in page.locator('#q-items-list').inner_text()

            # Filtro por trabalho preserva selecao e responde 200
            page.locator(f'#q-filter-work option[value="{work_id}"]').wait_for(state='attached', timeout=20000)
            with page.expect_response(lambda r: f'workId={work_id}' in r.url and r.status == 200, timeout=20000):
                page.locator('#q-filter-work').select_option(work_id)
            assert page.locator('#q-filter-work').input_value() == work_id

            # Abrir revisao a partir da peca da fila ativa o trabalho em Revisao & Entrega
            page.locator('#q-items-list').get_by_role('button', name='Abrir revisão').first.click()
            page.locator('#active-work-bar').wait_for(state='visible', timeout=20000)
            assert work_id in page.locator('#active-work-title').inner_text()
            page.locator('#mode-review').wait_for(state='visible', timeout=20000)

            assert not page_errors, f'Excecoes JS acumuladas: {page_errors}'
            assert not console_errors, f'Erros de console acumulados: {console_errors}'

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
