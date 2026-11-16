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

import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import zipfile

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
    second_work = 'ci-astryx-piloto-02'
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
            package_requests = []
            allow_expected_409 = [False]

            page.on('pageerror', lambda err: page_errors.append(str(err)))

            def _on_console(msg):
                if msg.type == 'error':
                    text = msg.text
                    # Ignora 404 de favicon.ico que nao faz parte do app
                    if 'favicon.ico' not in text and '404 (Not Found)' not in text:
                        if allow_expected_409[0] and '409 (Conflict)' in text:
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
                package_requests.append((req.url, req.post_data)) if '/api/works/package' in req.url and req.method == 'POST' else None,
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

            # 5. Aba Fila de Producao em React/Astryx: montagem, atualizar fila, filtros e Abrir revisao
            print('[ci_studio_astryx_browser] Etapa 5: aba Fila de Producao...', flush=True)
            page.locator('#mode-queue-btn').click()
            page.locator('[data-testid="astryx-queue-pilot"]').wait_for(state='visible', timeout=20000)
            queue_legacy_hidden = page.locator('#queue-legacy-root').get_attribute('hidden')
            assert queue_legacy_hidden is not None, '#queue-legacy-root deve estar oculto quando React monta'

            with page.expect_response(lambda r: r.url.split('?')[0].endswith('/api/queue') and r.status == 200, timeout=20000):
                page.locator('#btn-q-refresh').click()

            # Enfileira 1 lote de teste via API oficial e valida na UI da fila
            batch_label = f'Lote CI Astryx {int(time.time())}'
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
                        label: '{batch_label}',
                        items: [{{ workId: '{work_id}', modality: firstOpt.modality, profileId: firstOpt.profileId }}]
                    }})
                }}).then(r => r.json());
                return res;
            }}""")
            assert enqueue_res.get('ok'), f'Falha ao enfileirar lote de teste: {enqueue_res}'

            with page.expect_response(lambda r: r.url.split('?')[0].endswith('/api/queue') and r.status == 200, timeout=20000):
                page.locator('#btn-q-refresh').click()

            page.locator('#q-batches-list').get_by_text(batch_label).first.wait_for(state='visible', timeout=20000)
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

            # 6. Painel de pacote ZIP em React/Astryx na aba Revisao & Entrega
            print('[ci_studio_astryx_browser] Etapa 6: painel ZIP em Revisao & Entrega...', flush=True)
            page.locator('[data-testid="astryx-review-package-pilot"]').wait_for(state='visible', timeout=20000)
            pkg_legacy_hidden = page.locator('#review-package-legacy-root').get_attribute('hidden')
            assert pkg_legacy_hidden is not None, '#review-package-legacy-root deve estar oculto quando React monta'
            page.locator('#r-package-checklist').wait_for(state='visible', timeout=20000)
            page.locator('#btn-r-build-package').wait_for(state='visible', timeout=20000)

            # Aprova a peça renderizada para entrega local (o item da fila nasce pending_review).
            profile_id = page.evaluate(
                """() => {
                    const el = [...document.querySelectorAll('#r-package-checklist input[data-pkg-type="piece"]')]
                        .find(i => i.dataset.expectedVersion);
                    return el ? el.dataset.profile : null;
                }"""
            )
            assert profile_id, 'Nenhuma peça renderizada disponível para aprovar'
            approve_res = page.evaluate(
                """async ({workId, profileId}) => {
                    const review = await fetch('/api/works/review?id=' + encodeURIComponent(workId)).then(r => r.json());
                    const piece = review.pieces.find(p => p.modality === 'video' && p.profileId === profileId);
                    if (!piece) return {status: 0, versionId: null, body: {error: 'piece not found'}};
                    const res = await fetch('/api/works/review/decide', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            workId,
                            targetType: 'piece',
                            modality: 'video',
                            profileId,
                            decision: 'approved_for_local_delivery',
                            expectedVersionId: piece.deliveryVersionId,
                            expectedDraftFingerprint: piece.currentDraftFingerprint,
                        }),
                    });
                    return {status: res.status, versionId: piece.deliveryVersionId, body: await res.json()};
                }""",
                {'workId': work_id, 'profileId': profile_id},
            )
            assert approve_res['status'] == 200, f'Falha ao aprovar peça: {approve_res}'
            approved_version_id = approve_res['versionId']
            assert approved_version_id, f'Aprovação sem deliveryVersionId: {approve_res}'

            with page.expect_response(lambda r: r.url.split('?')[0].endswith('/api/works/review') and r.status == 200, timeout=20000):
                page.locator('#btn-r-refresh').click()
            page.wait_for_function(
                "sel => { const el = document.querySelector(sel); return el && el.checked; }",
                arg=f'#r-package-checklist input[data-pkg-type="piece"][data-profile="{profile_id}"]',
                timeout=20000,
            )

            # Um clique gera exatamente um POST /api/works/package.
            before_pkg = len(package_requests)
            with page.expect_response(lambda r: r.url.split('?')[0].endswith('/api/works/package') and r.status == 200, timeout=30000):
                page.locator('#btn-r-build-package').click()
            new_pkg = package_requests[before_pkg:]
            assert len(new_pkg) == 1, f'Esperado exatamente 1 POST /api/works/package, obtidos {len(new_pkg)}'
            pkg_payload = json.loads(new_pkg[0][1] or '{}')
            assert any(
                p.get('profileId') == profile_id and p.get('expectedVersionId') == approved_version_id
                for p in pkg_payload.get('pieces', [])
            ), f'Payload inesperado em POST /api/works/package: {pkg_payload}'

            # Baixa o ZIP e confere o SHA-256 informado pelo Studio.
            page.locator('#r-package-result').get_by_text('Pacote ZIP promovido').wait_for(state='visible', timeout=20000)
            result_text = page.locator('#r-package-result').inner_text()
            pkg_match = re.search(r'Pacote ZIP promovido: (\S+)', result_text)
            assert pkg_match, f'Resultado sem packageId: {result_text}'
            package_id = pkg_match.group(1)
            sha_match = re.search(r'SHA-256 ([0-9a-f]{64})', result_text)
            assert sha_match, f'Resultado sem SHA-256: {result_text}'
            studio_sha = sha_match.group(1)
            with page.expect_download(timeout=30000) as dl_info:
                page.locator('#btn-r-download-zip').click()
            zip_path = dl_info.value.path()
            with open(zip_path, 'rb') as fh:
                actual_sha = hashlib.sha256(fh.read()).hexdigest()
            assert actual_sha == studio_sha, (
                f'SHA-256 do ZIP baixado ({actual_sha}) difere do Studio ({studio_sha})'
            )

            # Manifesto: arquivos íntegros e peça amarrada à versão aprovada.
            with zipfile.ZipFile(zip_path, 'r') as zf:
                manifest = json.loads(zf.read('package-manifest.json').decode('utf-8'))
                for item in manifest['files']:
                    data = zf.read(item['archivePath'])
                    assert hashlib.sha256(data).hexdigest() == item['sha256'], (
                        f"Arquivo {item['archivePath']} não confere com o manifesto"
                    )
                pkg_piece = next(
                    (p for p in manifest['pieces'] if p['profileId'] == profile_id),
                    None,
                )
                assert pkg_piece is not None, f'Peça {profile_id} ausente no manifesto'
                assert pkg_piece['deliveryVersionId'] == approved_version_id, (
                    f"Versão empacotada {pkg_piece['deliveryVersionId']} difere da aprovada {approved_version_id}"
                )

            # Troca de trabalho: a resposta/estado antigo não pode derrubar o painel Astryx.
            page.evaluate(
                """async ({workId}) => {
                    await fetch('/api/works/create', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            id: workId,
                            name: 'CI Astryx Piloto 02',
                            project: 'platform/examples/projects/marca-salao-social.project.json',
                            template: 'blank',
                            overwrite: true,
                        }),
                    });
                }""",
                {'workId': second_work},
            )
            page.locator('#mode-home-btn').click()
            row_b = page.locator('tr', has_text=second_work).get_by_role('button', name='Reabrir')
            row_b.wait_for(state='visible', timeout=20000)
            row_b.click()
            page.locator('#mode-review-btn').click()
            page.locator('[data-testid="astryx-review-package-pilot"]').wait_for(state='visible', timeout=20000)
            page.locator('#mode-home-btn').click()
            row_a = page.locator('tr', has_text=work_id).get_by_role('button', name='Reabrir')
            row_a.wait_for(state='visible', timeout=20000)
            row_a.click()
            page.locator('#mode-review-btn').click()
            page.locator('[data-testid="astryx-review-package-pilot"]').wait_for(state='visible', timeout=20000)
            page.locator('#r-package-result').get_by_text(package_id).first.wait_for(state='visible', timeout=20000)

            assert not page_errors, f'Excecoes JS acumuladas: {page_errors}'
            assert not console_errors, f'Erros de console acumulados: {console_errors}'
            assert not http_error_responses, (
                'Respostas HTTP de erro inesperadas (metodo, rota, status): '
                f'{http_error_responses}'
            )

            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        _cleanup_test_artifacts(work_id, template_id, enqueue_res.get('batch', {}).get('batchId') if 'enqueue_res' in locals() else None)
        _cleanup_test_artifacts(second_work, template_id)

    print('Regressao de navegador Astryx concluida com sucesso (0 excecoes JS).')


if __name__ == '__main__':
    run_browser_regression()
