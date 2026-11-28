"""Prova complementar de concorrencia da fila HyperFrames (HF-003.6).

Diferente de tools/ci_hyperframes_concurrency_proof.py (que prova deduplicacao por
idempotencyKey e lease serial), esta prova exercita o caminho oposto:
- dois trabalhos independentes, com chaves de idempotencia DIFERENTES;
- submissao simultanea real (barreira entre threads);
- dois itens realmente aceitos (dois lotes distintos, sem deduplicacao);
- execucao conforme o limite de concorrencia configurado (executor serial);
- ausencia de mistura de outputDir entre os trabalhos;
- manifests com workId/tenant corretos e sem fallback silencioso;
- falha e cancelamento isolados (um item do trabalho A nao afeta o B).

Nao substitui a prova anterior; usa banco de fila proprio e destinos de CI.
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


def _get_json(url):
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _wait_batch(base, batch_id, timeout_s=480.0):
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        last = _get_json(f'{base}/api/queue/batch?id={batch_id}')['batch']
        c = last['counts']
        if c['queued'] == 0 and c['running'] == 0:
            return last
        time.sleep(0.4)
    raise AssertionError(f'lote {batch_id} nao convergiu: {last}')


def _make_work(base, work_id, theme='marca-salao'):
    proj = _post_json(f'{base}/api/projects/create', {
        'schemaVersion': 1,
        'id': f'ci-conc2-{work_id}',
        'name': f'CI Concurrency2 {work_id}',
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
        'id': work_id, 'name': f'CI Concurrency2 {work_id}',
        'project': proj['path'], 'template': 'marca-salao',
    }, base)
    vreq = created['videoRequest']
    vreq['profiles'] = ['instagram-reels-video']
    _post_json(f'{base}/api/works/save', {'workId': work_id, 'videoRequest': vreq}, base)
    return created


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prova complementar de concorrencia HyperFrames')
    parser.add_argument('--port', type=int, default=8816)
    args = parser.parse_args(argv)

    suffix = time.strftime('%H%M%S')
    work_a = f'ci-conc2-alpha-{suffix}'
    work_b = f'ci-conc2-beta-{suffix}'
    work_c = f'ci-conc2-gamma-{suffix}'
    for wid in (work_a, work_b, work_c):
        shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', wid), ignore_errors=True)
    project_files = []

    queue_db = os.path.join(ROOT, '.workspace', 'tmp', 'hf0036-concurrency',
                            f'queue-{os.getpid()}.sqlite')
    os.makedirs(os.path.dirname(queue_db), exist_ok=True)
    os.environ['STUDIO_QUEUE_DB_PATH'] = queue_db

    httpd, studio = video_studio.make_server(ROOT, args.port)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{args.port}'

    try:
        created_a = _make_work(base, work_a)
        created_b = _make_work(base, work_b)
        for wid in (work_a, work_b):
            res = _post_json(f'{base}/api/queue/plan', {'workIds': [wid]}, base)
            for opt in res['works'][0]['options']:
                if opt['modality'] == 'hyperframes':
                    project_files.append(opt.get('projectManifest'))

        # Motor explicito nos dois trabalhos (tenant marca-salao esta preparado).
        for wid in (work_a, work_b):
            r = _post_json(f'{base}/api/works/renderer/save',
                           {'workId': wid, 'renderer': {'adapter': 'hyperframes'}}, base)
            assert r['work']['renderer']['adapter'] == 'hyperframes', r

        item_a = {'workId': work_a, 'modality': 'hyperframes', 'profileId': 'instagram-reels-video'}
        item_b = {'workId': work_b, 'modality': 'hyperframes', 'profileId': 'instagram-reels-video'}

        # Chaves de idempotencia DIFERENTES: dois lotes independentes aceitos.
        idem_a = f'ci-conc2-a-{int(time.time())}-{os.getpid()}'
        idem_b = f'ci-conc2-b-{int(time.time())}-{os.getpid()}'
        results = {}
        barrier = threading.Barrier(3)

        def _submit(key, item, idem):
            payload = {'items': [item], 'label': f'CI conc2 {key}', 'idempotencyKey': idem}
            barrier.wait()
            results[key] = _post_json(f'{base}/api/queue/enqueue', payload, base)

        threads = [
            threading.Thread(target=_submit, args=('a', item_a, idem_a)),
            threading.Thread(target=_submit, args=('b', item_b, idem_b)),
        ]
        for t in threads:
            t.start()
        barrier.wait()
        for t in threads:
            t.join()

        batch_ids = {r['batch']['batchId'] for r in results.values()}
        assert len(batch_ids) == 2, f'esperados 2 lotes independentes: {batch_ids}'
        assert not any(r['batch'].get('deduplicated') for r in results.values()), results
        batch_a = next(r['batch']['batchId'] for k, r in results.items() if k == 'a')
        batch_b = next(r['batch']['batchId'] for k, r in results.items() if k == 'b')

        done_a = _wait_batch(base, batch_a)
        done_b = _wait_batch(base, batch_b)
        assert done_a['counts']['completed'] == 1, done_a['counts']
        assert done_b['counts']['completed'] == 1, done_b['counts']

        # Limite de concorrencia: executor unico serial por workspace.
        assert studio.queue.acquire_executor_lease() is True, 'fila do processo deveria deter o lease'
        rival = studio_queue.StudioQueue(studio)
        assert rival.acquire_executor_lease() is False, 'lease concedida a um segundo executor'

        # Integridade: 1 tentativa por item nos dois trabalhos.
        total_attempts = 0
        for wid in (work_a, work_b):
            state = _get_json(f'{base}/api/queue?workId={wid}')
            for it in state['items']:
                if it['batchId'] in (batch_a, batch_b):
                    total_attempts += len(it.get('attempts') or [])
        assert total_attempts == 2, f'tentativas inesperadas: {total_attempts}'

        # Isolamento: cada trabalho entrega no proprio diretorio, sem mistura.
        dirs = {}
        for wid, bid in ((work_a, batch_a), (work_b, batch_b)):
            state = _get_json(f'{base}/api/queue?workId={wid}')
            own = [it for it in state['items'] if it['batchId'] == bid and it['status'] == 'completed']
            assert len(own) == 1, (wid, own)
            dirs[wid] = own[0]['outputDir']
        assert dirs[work_a] != dirs[work_b], dirs
        assert work_a in dirs[work_a] and work_b in dirs[work_b], dirs

        # Manifestos: adapter hyperframes, tenant correto, captions clean, sem SRT.
        for wid, bid in ((work_a, batch_a), (work_b, batch_b)):
            mpath = os.path.join(studio.confine_workspace(dirs[wid]),
                                 'instagram-reels-video', 'delivery-manifest.json')
            with open(mpath, 'r', encoding='utf-8') as handle:
                m = json.load(handle)
            assert m.get('adapter') == 'hyperframes', (wid, m.get('adapter'))
            assert (m.get('renderer') or {}).get('adapter') == 'hyperframes', m.get('renderer')
            assert m.get('captionsMode') == 'clean', m.get('captionsMode')
            assert not (m.get('artifacts') or {}).get('srt'), m.get('artifacts')
            assert wid in str(m.get('outputDir') or ''), (wid, m.get('outputDir'))

        # Snapshots congelados: tenant correto por trabalho, sem fallback.
        with studio.queue._db_lock:
            conn = studio.queue._connect()
            try:
                rows = conn.execute(
                    'SELECT snapshot_json FROM queue_items WHERE batch_id IN (?,?)',
                    (batch_a, batch_b)).fetchall()
            finally:
                conn.close()
        assert len(rows) == 2, len(rows)
        for row in rows:
            snap = json.loads(row['snapshot_json'])
            assert (snap.get('renderer') or {}).get('adapter') == 'hyperframes', snap.get('renderer')
            assert snap.get('tenantId') == 'marca-salao', snap.get('tenantId')
            assert snap.get('captionsMode') == 'clean', snap.get('captionsMode')

        # Falha isolada: banner de check do tenant A nao pode derrubar o trabalho B.
        # Cria-se um trabalho sob tenant sem frame.md (clinica-vital) e verifica-se
        # que a falha fica no item dele, com a entrega de B intacta.
        work_c = f'ci-conc2-gamma-{suffix}'
        proj_c = _post_json(f'{base}/api/projects/create', {
            'schemaVersion': 1,
            'id': f'ci-conc2-{work_c}',
            'name': f'CI Concurrency2 {work_c}',
            'locale': 'pt-BR',
            'timezone': 'America/Sao_Paulo',
            'brandTheme': 'clinica-vital',
            'assetRoot': f'.workspace/studio/works/{work_c}/media',
            'contentPolicies': {
                'requireApprovedBriefing': True,
                'requireApprovedScript': True,
                'prohibitPersonalData': True,
                'requireFunctionalEvidence': True,
            },
            'outputProfiles': ['instagram-reels-video'],
        }, base)
        created_c = _post_json(f'{base}/api/works/create', {
            'id': work_c, 'name': f'CI Concurrency2 {work_c}',
            'project': proj_c['path'], 'template': 'blank',
        }, base)
        vreq_c = created_c['videoRequest']
        vreq_c['profiles'] = ['instagram-reels-video']
        _post_json(f'{base}/api/works/save',
                   {'workId': work_c, 'videoRequest': vreq_c}, base)
        _post_json(f'{base}/api/works/renderer/save',
                   {'workId': work_c, 'renderer': {'adapter': 'ffmpeg'}}, base)
        # Forca a selecao HyperFrames no snapshot sem passar pela validacao de
        # prontidao do tenant (cenario legitimo de trabalho antigo reaproveitado).
        work_c_file = studio.confine_workspace(studio.work_paths(work_c)['workFile'])
        with open(work_c_file, 'r', encoding='utf-8') as handle:
            doc_c = json.load(handle)
        doc_c['renderer'] = {'adapter': 'hyperframes'}
        with open(work_c_file, 'w', encoding='utf-8') as handle:
            json.dump(doc_c, handle, ensure_ascii=False, indent=2)
        bad = _post_json(f'{base}/api/queue/enqueue', {
            'items': [{'workId': work_c, 'modality': 'hyperframes',
                       'profileId': 'instagram-reels-video'}],
            'label': 'CI conc2 falha isolada',
        }, base)
        bad_id = bad['batch']['batchId']
        bad_done = _wait_batch(base, bad_id)
        assert bad_done['counts']['failed'] == 1, bad_done['counts']
        state_b = _get_json(f'{base}/api/queue?workId={work_b}')
        assert all(it['status'] == 'completed' for it in state_b['items']
                   if it['batchId'] == batch_b), state_b['items']

        # Cancelamento isolado: item pendente do trabalho A cancelado; B intacto.
        studio.queue._stop_event.set()
        cancel_batch = _post_json(f'{base}/api/queue/enqueue', {
            'items': [item_a], 'label': 'CI conc2 cancel',
        }, base)
        cancel_id = cancel_batch['batch']['batchId']
        state_a = _get_json(f'{base}/api/queue?workId={work_a}')
        pending = [it for it in state_a['items']
                   if it['batchId'] == cancel_id and it['status'] == 'queued']
        assert pending, state_a['items']
        cancelled = _post_json(f'{base}/api/queue/cancel',
                               {'itemId': pending[0]['itemId']}, base)['item']
        assert cancelled['status'] == 'cancelled', cancelled
        assert cancelled.get('errorCode') == 'CANCELLED_BY_USER', cancelled
        cancel_done = _wait_batch(base, cancel_id)
        assert cancel_done['counts']['cancelled'] == 1, cancel_done['counts']
        studio.queue._stop_event.clear()
        studio.queue.start_executor()

        # Preservacao: as duas entregas continuam no disco ao final da prova.
        for wid in (work_a, work_b):
            mpath = os.path.join(studio.confine_workspace(dirs[wid]),
                                 'instagram-reels-video', 'delivery-manifest.json')
            assert os.path.isfile(mpath), f'entrega de {wid} desapareceu'

        print('hyperframes-concurrency2 CI HTTP proof ok')
        print(json.dumps({
            'workA': work_a,
            'workB': work_b,
            'batchA': batch_a,
            'batchB': batch_b,
            'countsA': done_a['counts'],
            'countsB': done_b['counts'],
            'deliveryDirs': [dirs[work_a], dirs[work_b]],
            'failedBatch': bad_id,
            'cancelBatchId': cancel_id,
            'attempts': total_attempts,
        }, ensure_ascii=False))
        return 0
    finally:
        studio.close()
        httpd.shutdown()
        httpd.server_close()
        os.environ.pop('STUDIO_QUEUE_DB_PATH', None)
        for sfx in ('', '-wal', '-shm'):
            try:
                os.remove(queue_db + sfx)
            except OSError:
                pass
        for wid in (work_a, work_b, work_c):
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