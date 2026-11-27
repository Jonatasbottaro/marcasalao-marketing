"""Prova HTTP da integracao HyperFrames na fila do Video Studio (HF-001 F7/F8).

Cobre: selecao explicita de renderer no trabalho, readiness do runtime, plano e
pre-voo da fila com a modalidade hyperframes, execucao real pelo adaptador
(VIDEO CLEAN: 0 faixas de audio), peca de revisao propria, pacote ZIP reutilizado,
caso negativo de guardrails (sem fallback silencioso para FFmpeg) e recuperacao
de item running apos reinicio (recover_on_startup + retry).
"""

import argparse
import json
import os
import shutil
import sys
import threading
import time
import urllib.request
import zipfile

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
TOOLS = os.path.join(ROOT, 'tools')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

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


def _wait_batch(base, batch_id, timeout_s=420.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        res = _http_json(f'{base}/api/queue/batch?id={batch_id}')
        batch = res['batch']
        c = batch['counts']
        if c['queued'] == 0 and c['running'] == 0:
            return batch
        time.sleep(0.5)
    raise AssertionError(f'lote {batch_id} nao convergiu no prazo')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prova HTTP da fila HyperFrames no Video Studio')
    parser.add_argument('--port', type=int, default=8813)
    args = parser.parse_args(argv)

    work_id = 'ci-hf-queue-work'
    work_dir = os.path.join(ROOT, '.workspace', 'studio', 'works', work_id)
    shutil.rmtree(work_dir, ignore_errors=True)
    project_file = None

    httpd, studio = video_studio.make_server(ROOT, args.port)
    srv_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    srv_thread.start()
    base = f'http://127.0.0.1:{args.port}'
    post_json = lambda u, b: _http_json(u, 'POST', b, origin=base)

    try:
        proj_res = post_json(f'{base}/api/projects/create', {
            'schemaVersion': 1,
            'id': f'ci-{work_id}',
            'name': f'CI {work_id}',
            'locale': 'pt-BR',
            'timezone': 'America/Sao_Paulo',
            'brandTheme': 'marca-salao',
            'assetRoot': f'.workspace/studio/works/{work_id}/media',
            'contentPolicies': {
                'requireApprovedBriefing': True,
                'requireApprovedScript': True,
                'prohibitPersonalData': True,
                'requireFunctionalEvidence': True,
            },
            'outputProfiles': ['instagram-reels-video'],
        })
        project_file = studio.confine(proj_res['path'])
        created = post_json(f'{base}/api/works/create', {
            'id': work_id, 'name': 'CI HF Queue', 'project': proj_res['path'], 'template': 'marca-salao',
        })
        vreq = created['videoRequest']
        vreq['profiles'] = ['instagram-reels-video']
        post_json(f'{base}/api/works/save', {'workId': work_id, 'videoRequest': vreq})

        # 1. Selecao explicita de renderer + readiness do runtime
        renderer_res = post_json(f'{base}/api/works/renderer/save', {
            'workId': work_id, 'renderer': {'adapter': 'hyperframes'},
        })
        assert renderer_res['work']['renderer']['adapter'] == 'hyperframes', renderer_res
        readiness = _http_json(f'{base}/api/hyperframes/readiness')
        assert readiness['ok'] is True and readiness['version'] == '0.9.103', readiness

        # 2. Plano da fila expoe a modalidade hyperframes
        plan = post_json(f'{base}/api/queue/plan', {'workIds': [work_id]})
        hf_options = [o for o in plan['works'][0]['options'] if o['modality'] == 'hyperframes']
        assert hf_options, 'plano sem opcoes hyperframes'
        reel_opt = next(o for o in hf_options if o['profileId'] == 'instagram-reels-video')
        assert reel_opt['available'] is True, reel_opt
        assert reel_opt['selectedByDefault'] is True, reel_opt
        assert reel_opt['outputDir'].endswith('/deliveries/hyperframes'), reel_opt

        # 3. Pre-voo pronto para o destino hyperframes
        preflight = post_json(f'{base}/api/queue/preflight', {
            'items': [{'workId': work_id, 'modality': 'hyperframes', 'profileId': 'instagram-reels-video'}],
        })
        assert preflight['ready'] is True, json.dumps(preflight, ensure_ascii=False, indent=2)

        # 4. Execucao real pela fila (adaptador HyperFrames, VIDEO CLEAN)
        item = {'workId': work_id, 'modality': 'hyperframes', 'profileId': 'instagram-reels-video'}
        enq = post_json(f'{base}/api/queue/enqueue', {'items': [item], 'label': 'CI HF positivo'})
        batch_id = enq['batch']['batchId']
        batch = _wait_batch(base, batch_id)
        assert batch['counts']['completed'] == 1, json.dumps(batch['counts'])

        # 5. Peca de revisao propria com entrega verificada (aguarda aprovacao humana)
        rev = _http_json(f'{base}/api/works/review?id={work_id}')
        piece = next(p for p in rev['pieces'] if p['pieceKey'] == 'hyperframes:instagram-reels-video')
        assert piece['status'] == 'pending_review', piece
        assert piece['deliveryVersionId'], piece
        assert piece['artifacts'].get('video') and piece['artifacts'].get('narration'), piece
        assert not piece['artifacts'].get('srt'), 'entrega HyperFrames nao deve ter SRT'
        assert piece['metrics'].get('audioStreams') == 0, piece['metrics']
        assert piece['readyForPackage'] is False, piece

        # 6. Aprovacao e pacote ZIP reutilizado (delivery_package.py)
        decided = post_json(f'{base}/api/works/review/decide', {
            'workId': work_id,
            'targetType': 'piece',
            'modality': 'hyperframes',
            'profileId': 'instagram-reels-video',
            'decision': 'approved_for_local_delivery',
            'expectedVersionId': piece['deliveryVersionId'],
            'note': 'ci-bot',
        })
        approved = next(
            p for p in decided['pieces'] if p['pieceKey'] == 'hyperframes:instagram-reels-video'
        )
        assert approved['status'] == 'approved' and approved['readyForPackage'] is True, approved
        pkg = post_json(f'{base}/api/works/package', {
            'workId': work_id,
            'pieces': [{'modality': 'hyperframes', 'profileId': 'instagram-reels-video',
                        'expectedVersionId': piece['deliveryVersionId']}],
        })
        pkg_info = pkg.get('packageDelivery') or pkg
        assert pkg.get('ok') and pkg_info.get('available'), f'package build failed: {pkg}'
        zip_abs = studio.confine(pkg_info['lastValidDelivery']['zipPath'])
        with zipfile.ZipFile(zip_abs) as zf:
            names = zf.namelist()
        assert 'hyperframes/instagram-reels-video/primary-output.mp4' in names, names
        assert 'hyperframes/instagram-reels-video/narration.txt' in names, names
        assert not any(n.endswith('.srt') for n in names), names

        # 7. Negativo: claim proibida aborta antes do render, sem fallback FFmpeg
        vreq['scenes'][0]['caption'] = 'Agenda sempre cheia, 24h sem faltas'
        post_json(f'{base}/api/works/save', {'workId': work_id, 'videoRequest': vreq})
        enq_neg = post_json(f'{base}/api/queue/enqueue', {'items': [item], 'label': 'CI HF guardrails'})
        batch_neg = _wait_batch(base, enq_neg['batch']['batchId'])
        assert batch_neg['counts']['failed'] == 1, batch_neg['counts']
        queue_state = _http_json(f'{base}/api/queue?workId={work_id}')
        failed_items = [it for it in queue_state['items'] if it['status'] == 'failed']
        assert failed_items and 'GUARDRAILS_VIOLATION' in (failed_items[-1].get('errorMessage') or ''), failed_items[-1]

        # 8. Recuperacao: item running com processo morto apos reinicio
        vreq['scenes'][0]['caption'] = 'Conheca o Marca Salao'
        post_json(f'{base}/api/works/save', {'workId': work_id, 'videoRequest': vreq})
        enq_rec = post_json(f'{base}/api/queue/enqueue', {'items': [item], 'label': 'CI HF recovery'})
        rec_batch_id = enq_rec['batch']['batchId']
        queue_state = _http_json(f'{base}/api/queue?workId={work_id}')
        rec_item = next(it for it in queue_state['items'] if it['batchId'] == rec_batch_id)
        with studio.queue._db_lock:
            conn = studio.queue._connect()
            try:
                conn.execute('BEGIN IMMEDIATE')
                conn.execute(
                    "UPDATE queue_items SET status='running', last_attempt_id=NULL WHERE item_id=?",
                    (rec_item['itemId'],),
                )
                conn.execute('COMMIT')
            finally:
                conn.close()
        studio.queue.recover_on_startup()
        queue_state = _http_json(f'{base}/api/queue?workId={work_id}')
        rec_item = next(it for it in queue_state['items'] if it['itemId'] == rec_item['itemId'])
        assert rec_item['status'] == 'interrupted', rec_item
        assert rec_item.get('errorCode') == 'INTERRUPTED_INCONCLUSIVE', rec_item
        retried = post_json(f'{base}/api/queue/retry', {'itemId': rec_item['itemId']})
        assert retried['item']['status'] == 'queued', retried
        batch_rec = _wait_batch(base, rec_batch_id)
        assert batch_rec['counts']['completed'] == 1, batch_rec['counts']

        print('hyperframes-queue CI HTTP proof ok')
        print(json.dumps({
            'positiveBatch': batch_id,
            'guardrailsBatch': enq_neg['batch']['batchId'],
            'recoveryBatch': rec_batch_id,
            'zipSha256': (pkg_info.get('lastValidDelivery') or {}).get('zipSha256'),
        }, ensure_ascii=False))
        return 0
    finally:
        studio.close()
        httpd.shutdown()
        httpd.server_close()
        shutil.rmtree(work_dir, ignore_errors=True)
        if project_file and os.path.exists(project_file):
            try:
                os.remove(project_file)
            except OSError:
                pass


if __name__ == '__main__':
    raise SystemExit(main())
