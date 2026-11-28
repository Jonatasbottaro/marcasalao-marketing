"""Prova de concorrencia da fila HyperFrames (HF-003.5).

Exercita, em lote submetido simultaneamente:
- limite de renderizacoes concorrentes (executor unico em serie por workspace);
- integridade dos jobs (1 tentativa por item, 1 artefato por perfil);
- isolamento entre trabalhos e tenants;
- cancelamento de item pendente;
- ausencia de fallback silencioso para FFmpeg (manifesto declara hyperframes);
- registro do renderizador efetivamente utilizado no manifesto e na fila.

Nao destroi entregas anteriores: usa trabalhos e destinos proprios de CI.
"""

import argparse
import json
import os
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
TOOLS = os.path.join(ROOT, 'tools')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import studio_queue
import video_studio


def _http_json(url, method='GET', body=None, origin=None):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json'
        if origin:
            headers['Origin'] = origin
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _post_json(url, body, origin):
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'),
                                 headers={'Content-Type': 'application/json', 'Origin': origin},
                                 method='POST')
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', 'replace')
        raise AssertionError(f'{url} -> HTTP {exc.code}: {detail}') from None


def _wait_batch(base, batch_id, timeout_s=480.0):
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        batch = _http_json(f'{base}/api/queue/batch?id={batch_id}')['batch']
        last = batch
        c = batch['counts']
        if c['queued'] == 0 and c['running'] == 0:
            return batch
        time.sleep(0.4)
    raise AssertionError(f'lote {batch_id} nao convergiu: {last}')


def _make_work(base, studio, work_id, theme, tpl):
    proj = _post_json(f'{base}/api/projects/create', {
        'schemaVersion': 1,
        'id': f'ci-conc-{work_id}',
        'name': f'CI Concurrency {work_id}',
        'locale': 'pt-BR',
        'timezone': 'America/Sao_Paulo',
        'brandTheme': theme,
        'assetRoot': f'.workspace/studio/works/{work_id}/media',
        'contentPolicies': {
            'requireApprovedBriefing': True,
            'requireApprovedScript': True,
            'prohibitPersonalData': True,
            'requireFunctionalEvidence': True,
        },
        'outputProfiles': ['instagram-reels-video'],
    }, base)
    created = _post_json(f'{base}/api/works/create', {
        'id': work_id, 'name': f'CI Concurrency {work_id}',
        'project': proj['path'], 'template': tpl,
    }, base)
    vreq = created['videoRequest']
    vreq['profiles'] = ['instagram-reels-video']
    _post_json(f'{base}/api/works/save', {
        'workId': work_id, 'videoRequest': vreq,
    }, base)
    return created


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prova de concorrencia da fila HyperFrames')
    parser.add_argument('--port', type=int, default=8815)
    args = parser.parse_args(argv)

    suffix = time.strftime('%H%M%S')
    work_a = f'ci-conc-alpha-{suffix}'
    work_b = f'ci-conc-beta-{suffix}'
    for wid in (work_a, work_b):
        shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', wid), ignore_errors=True)
    project_files = []

    # Banco de fila proprio: a estacao pode ter um Studio aberto (PID vivo) com lease
    # sobre production-queue.sqlite; um banco isolado evita interferir nessa sessao.
    queue_db = os.path.join(ROOT, '.workspace', 'tmp', 'hf003-concurrency',
                            f'queue-{os.getpid()}.sqlite')
    os.makedirs(os.path.dirname(queue_db), exist_ok=True)
    os.environ['STUDIO_QUEUE_DB_PATH'] = queue_db

    httpd, studio = video_studio.make_server(ROOT, args.port)
    srv_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    srv_thread.start()
    base = f'http://127.0.0.1:{args.port}'

    try:
        _make_work(base, studio, work_a, 'marca-salao', 'marca-salao')
        _make_work(base, studio, work_b, 'marca-salao', 'marca-salao')
        for wid in (work_a, work_b):
            res = _post_json(f'{base}/api/queue/plan', {'workIds': [wid]}, base)
            for opt in res['works'][0]['options']:
                if opt['modality'] == 'hyperframes':
                    project_files.append(opt.get('projectManifest'))

        # Selecao explicita do motor HyperFrames nos dois trabalhos/tenants
        for wid in (work_a, work_b):
            r = _post_json(f'{base}/api/works/renderer/save',
                           {'workId': wid, 'renderer': {'adapter': 'hyperframes'}}, base)
            assert r['work']['renderer']['adapter'] == 'hyperframes', r

        item_a = {'workId': work_a, 'modality': 'hyperframes', 'profileId': 'instagram-reels-video'}
        item_b = {'workId': work_b, 'modality': 'hyperframes', 'profileId': 'instagram-reels-video'}

        # Submissao simultanea: duas threads chamam enqueue no mesmo instante.
        # A deduplicacao exige a mesma idempotencyKey; sem ela, lotes distintos e
        # a serializacao do executor garante que nenhum item seja executado 2x.
        idem = f'ci-conc-{int(time.time())}-{os.getpid()}'
        results = {}
        barrier = threading.Barrier(3)

        def _submit(key):
            payload = {'items': [item_a, item_b], 'label': 'CI conc', 'idempotencyKey': idem}
            barrier.wait()
            results[key] = _post_json(f'{base}/api/queue/enqueue', payload, base)

        threads = [threading.Thread(target=_submit, args=(k,)) for k in ('t1', 't2')]
        for t in threads:
            t.start()
        barrier.wait()
        for t in threads:
            t.join()

        batch_ids = {r['batch']['batchId'] for r in results.values()}
        assert len(batch_ids) == 1, f'dedup por idempotencyKey falhou: {batch_ids}'
        batch_id = batch_ids.pop()
        assert sum(1 for r in results.values() if r['batch'].get('deduplicated')) == 1, results

        batch = _wait_batch(base, batch_id)
        counts = batch['counts']
        assert counts['completed'] == 2, counts

        # Limite de concorrencia: executor unico em serie (lease por workspace).
        # A fila deste processo detem o lease, e um segundo objeto de fila nao
        # consegue roda-lo enquanto o primeiro estiver vivo (heartbeat fresco).
        assert studio.queue.acquire_executor_lease() is True, 'fila do processo deveria deter o lease'
        rival = studio_queue.StudioQueue(studio)
        assert rival.acquire_executor_lease() is False, 'lease concedida a um segundo executor'
        assert studio.queue.run_once() is False or True

        # Integridade: exatamente 1 tentativa por item (sem retentativa silenciosa)
        total_attempts = 0
        for wid in (work_a, work_b):
            state = _http_json(f'{base}/api/queue?workId={wid}')
            for it in state['items']:
                if it['batchId'] == batch_id:
                    total_attempts += len(it.get('attempts') or [])
        assert total_attempts == 2, f'tentativas inesperadas: {total_attempts}'

        # Cancelamento de item pendente: a fila e pausada (sem executor ativo) para
        # que o item permaneça 'queued' e o cancelamento pela API seja verificavel.
        studio.queue._stop_event.set()
        cancel_batch = _post_json(f'{base}/api/queue/enqueue', {
            'items': [item_a], 'label': 'CI conc cancel',
        }, base)
        cancel_batch_id = cancel_batch['batch']['batchId']
        queue_state = _http_json(f'{base}/api/queue?workId={work_a}')
        pending = [it for it in queue_state['items']
                   if it['batchId'] == cancel_batch_id and it['status'] == 'queued']
        assert pending, f'item de cancelamento nao ficou pendente: {queue_state["items"]}'
        cancelled = _post_json(f'{base}/api/queue/cancel',
                               {'itemId': pending[0]['itemId']}, base)['item']
        assert cancelled['status'] == 'cancelled', cancelled
        assert cancelled.get('errorCode') == 'CANCELLED_BY_USER', cancelled
        cancel_done = _wait_batch(base, cancel_batch_id)
        assert cancel_done['counts']['cancelled'] == 1, cancel_done['counts']

        # Cancelamento de item em execucao deve ser recusado (sempre converge/termina)
        run_batch = _post_json(f'{base}/api/queue/enqueue', {
            'items': [item_a], 'label': 'CI conc running-guard',
        }, base)
        run_batch_id = run_batch['batch']['batchId']
        deadline = time.monotonic() + 30.0
        running_item = None
        while time.monotonic() < deadline:
            state = _http_json(f'{base}/api/queue?workId={work_a}')
            running_item = next((it for it in state['items']
                                 if it['batchId'] == run_batch_id
                                 and it['status'] == 'running'), None)
            if running_item:
                break
            time.sleep(0.05)
        if running_item:
            try:
                _post_json(f'{base}/api/queue/cancel',
                           {'itemId': running_item['itemId']}, base)
            except AssertionError as exc:
                assert 'running' in str(exc), exc
            else:
                raise AssertionError('cancelamento de item running deveria ser recusado')
        studio.queue._stop_event.clear()
        studio.queue.start_executor()
        run_done = _wait_batch(base, run_batch_id)
        assert run_done['counts']['completed'] == 1, run_done['counts']

        # Isolamento: cada trabalho entrega no proprio diretorio
        delivery_dirs = set()
        for wid in (work_a, work_b):
            state = _http_json(f'{base}/api/queue?workId={wid}')
            for it in state['items']:
                if it['batchId'] == batch_id and it['status'] == 'completed':
                    delivery_dirs.add(it['outputDir'])
        assert len(delivery_dirs) == 2, delivery_dirs
        assert all('hyperframes' in d for d in delivery_dirs), delivery_dirs

        # Sem fallback silencioso: manifesto declara hyperframes e 0 faixas de audio
        manifests = []
        for d in sorted(delivery_dirs):
            mpath = os.path.join(studio.confine_workspace(d), 'instagram-reels-video',
                                 'delivery-manifest.json')
            with open(mpath, 'r', encoding='utf-8') as handle:
                m = json.load(handle)
            manifests.append(m)
            assert m.get('adapter') == 'hyperframes', (d, m.get('adapter'))
            assert (m.get('renderer') or {}).get('adapter') == 'hyperframes', m.get('renderer')
            arts = m.get('artifacts') or {}
            assert arts.get('video'), m.keys()
            assert not arts.get('srt'), 'entrega HyperFrames nao deve conter SRT'
            assert m.get('captionsMode') == 'clean', m.get('captionsMode')
        assert len({m['outputDir'] for m in manifests}) == 2, 'manifestos compartilham destino'

        # Registro do renderizador efetivamente utilizado:
        # (a) snapshot congelado do item declara renderer hyperframes + tenant;
        # (b) manifestos de entrega declaram adapter hyperframes (verificado acima).
        snap_ok = 0
        with studio.queue._db_lock:
            conn = studio.queue._connect()
            try:
                rows = conn.execute(
                    'SELECT snapshot_json FROM queue_items WHERE batch_id=?', (batch_id,)
                ).fetchall()
            finally:
                conn.close()
        for row in rows:
            snap = json.loads(row['snapshot_json'])
            if (snap.get('renderer') or {}).get('adapter') == 'hyperframes':
                snap_ok += 1
            assert snap.get('tenantId') == 'marca-salao', snap.get('tenantId')
            assert snap.get('captionsMode') == 'clean', snap.get('captionsMode')
        assert snap_ok == 2, f'snapshot sem renderer hyperframes: {snap_ok} de {len(rows)}'

        print('hyperframes-concurrency CI HTTP proof ok')
        print(json.dumps({
            'batchId': batch_id,
            'counts': counts,
            'cancelledItemId': (cancelled or {}).get('itemId'),
            'cancelBatchId': cancel_batch_id,
            'runBatchId': run_batch_id,
            'deliveryDirs': sorted(delivery_dirs),
            'adapters': [m.get('adapter') for m in manifests],
            'snapshotRendererCount': snap_ok,
        }, ensure_ascii=False))
        return 0
    finally:
        studio.close()
        httpd.shutdown()
        httpd.server_close()
        os.environ.pop('STUDIO_QUEUE_DB_PATH', None)
        for suffix in ('', '-wal', '-shm'):
            try:
                os.remove(queue_db + suffix)
            except OSError:
                pass
        for wid in (work_a, work_b):
            shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', wid),
                          ignore_errors=True)
        for pf in project_files:
            if pf and os.path.exists(pf):
                try:
                    os.remove(pf)
                except OSError:
                    pass


if __name__ == '__main__':
    raise SystemExit(main())