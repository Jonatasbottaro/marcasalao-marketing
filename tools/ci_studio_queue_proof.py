"""Prova HTTP de producao em lote com fila persistente no Video Studio (CI)."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
TOOLS = os.path.join(ROOT, 'tools')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import build_video
import render_local
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
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _create_color_video(path, color, duration_s=2.0, width=1280, height=720, fps=30):
    ffmpeg = build_video.get_ffmpeg()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cmd = [
        ffmpeg, '-y', '-f', 'lavfi',
        '-i', f'color=c={color}:s={width}x{height}:r={fps}:d={duration_s}',
        '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-an', path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if res.returncode != 0:
        raise RuntimeError(f'ffmpeg color video failed: {res.stderr}')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prova HTTP da fila de producao em lote')
    parser.add_argument('--port', type=int, default=8803)
    args = parser.parse_args(argv)

    w1 = 'ci-queue-ms-work'
    w2 = 'ci-queue-mh-work'
    pfiles = []
    for wid in (w1, w2):
        shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', wid), ignore_errors=True)

    httpd, studio = video_studio.make_server(ROOT, args.port)
    srv_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    srv_thread.start()
    base = f'http://127.0.0.1:{args.port}'
    post_json = lambda u, b: _http_json(u, 'POST', b, origin=base)

    try:
        for wid, theme, tpl, color in (
            (w1, 'marca-salao', 'marca-salao', 'blue'),
            (w2, 'multitrack-hub', 'multitrack-hub', 'green'),
        ):
            proj_res = post_json(f'{base}/api/projects/create', {
                'schemaVersion': 1,
                'id': f'ci-{wid}',
                'name': f'CI {wid}',
                'locale': 'pt-BR',
                'timezone': 'America/Sao_Paulo',
                'brandTheme': theme,
                'assetRoot': f'.workspace/studio/works/{wid}/media',
                'contentPolicies': {
                    'requireApprovedBriefing': True,
                    'requireApprovedScript': True,
                    'prohibitPersonalData': True,
                    'requireFunctionalEvidence': True,
                },
                'outputProfiles': [
                    'instagram-reels-video',
                    'youtube-video-horizontal',
                    'instagram-feed-image-square',
                    'instagram-feed-image-portrait',
                ],
            })
            proj = proj_res['path']
            pfiles.append(studio.confine(proj))
            created = post_json(f'{base}/api/works/create', {
                'id': wid, 'name': f'CI Queue {wid}', 'project': proj, 'template': tpl,
            })
            clip_rel = f".workspace/studio/works/{wid}/media/ci-clip.mp4"
            _create_color_video(studio.confine(clip_rel), color, duration_s=2.5)
            vreq = created['videoRequest']
            vreq['media'] = list(vreq.get('media') or []) + [
                {'id': 'clip-1', 'type': 'video', 'path': clip_rel, 'origin': 'synthetic-demo', 'license': 'owned-synthetic'}
            ]
            vreq['scenes'][0]['mediaId'] = 'clip-1'
            vreq['scenes'][0]['sourceStartMs'] = 250
            vreq['scenes'][0]['durationMs'] = 1200
            vreq['scenes'][0]['framingByProfile'] = {
                'instagram-reels-video': {'centerX': 0.7, 'centerY': 0.5, 'zoomPercent': 140},
                'youtube-video-horizontal': {'centerX': 0.5, 'centerY': 0.5, 'zoomPercent': 100},
            }
            vreq['profiles'] = ['instagram-reels-video', 'youtube-video-horizontal']
            creq = created['carouselRequest']
            creq['profile'] = 'instagram-feed-image-portrait'
            mplan = created['motionPlan']
            for eff in mplan.get('effects') or []:
                if eff.get('sceneId') == vreq['scenes'][0]['id']:
                    eff['startMs'] = 0
                    eff['endMs'] = min(int(eff.get('endMs') or 1000), 1000)
            post_json(f'{base}/api/works/save', {
                'workId': wid, 'videoRequest': vreq, 'carouselRequest': creq, 'motionPlan': mplan,
            })

        plan = post_json(f'{base}/api/queue/plan', {'workIds': [w1, w2]})
        assert len(plan['works']) == 2, 'plan should return 2 works'

        items = [
            {'workId': w1, 'modality': 'video', 'profileId': 'instagram-reels-video'},
            {'workId': w1, 'modality': 'video', 'profileId': 'youtube-video-horizontal'},
            {'workId': w1, 'modality': 'carousel', 'profileId': 'instagram-feed-image-portrait'},
            {'workId': w1, 'modality': 'motion', 'profileId': 'instagram-reels-video'},
            {'workId': w2, 'modality': 'video', 'profileId': 'instagram-reels-video'},
        ]
        preflight = post_json(f'{base}/api/queue/preflight', {
            'items': items + [{'workId': w1, 'modality': 'motion', 'profileId': 'youtube-video-horizontal'}],
        })
        assert preflight.get('schemaVersion') == 1 and preflight.get('ready') is False
        assert all(it['status'] == 'ready' for it in preflight['items'][:5]), f'expected ready items: {preflight["items"][:5]}'
        assert preflight['items'][5]['status'] == 'blocked', 'expected incompatible motion to be blocked'

        cli_ready = subprocess.run(
            [sys.executable, os.path.join(TOOLS, 'studio_preflight.py'),
             '--port', str(args.port), '--work-id', w1,
             '--modality', 'video', '--profile', 'instagram-reels-video', '--json'],
            capture_output=True, text=True, timeout=60,
        )
        assert cli_ready.returncode == 0, f'cli ready failed: {cli_ready.stderr}'
        assert json.loads(cli_ready.stdout)['items'][0]['status'] == 'ready'

        cli_blocked = subprocess.run(
            [sys.executable, os.path.join(TOOLS, 'studio_preflight.py'),
             '--port', str(args.port), '--work-id', w1,
             '--modality', 'motion', '--profile', 'youtube-video-horizontal'],
            capture_output=True, text=True, timeout=60,
        )
        assert cli_blocked.returncode == 1, f'cli blocked exit code unexpected: {cli_blocked.returncode}'
        assert 'BLOQUEADO:' in cli_blocked.stdout
        idem_key = f'ci-queue-idem-{int(time.time())}'
        e1 = post_json(f'{base}/api/queue/enqueue', {'items': items, 'idempotencyKey': idem_key, 'label': 'CI Lote'})
        e2 = post_json(f'{base}/api/queue/enqueue', {'items': items, 'idempotencyKey': idem_key, 'label': 'CI Lote'})
        assert e1['batch']['batchId'] == e2['batch']['batchId'], 'idempotency failed'
        assert e2['batch']['deduplicated'] is True, 'second enqueue should be deduplicated'
        batch_id = e1['batch']['batchId']

        deadline = time.monotonic() + 240.0
        batch = None
        while time.monotonic() < deadline:
            res = _http_json(f'{base}/api/queue/batch?id={batch_id}')
            batch = res['batch']
            c = batch['counts']
            if c['queued'] == 0 and c['running'] == 0:
                break
            time.sleep(0.4)
        assert batch is not None and batch['counts']['completed'] == 5, f'unexpected batch state: {batch}'

        summary = _http_json(f'{base}/api/queue/batch/summary?id={batch_id}')
        assert summary['batchId'] == batch_id

        # Aprovar peca e gerar ZIP via HTTP
        rev = _http_json(f'{base}/api/works/review?id={w1}')
        reels = next(p for p in rev['pieces'] if p['pieceKey'] == 'video:instagram-reels-video')
        post_json(f'{base}/api/works/review/decide', {
            'workId': w1,
            'targetType': 'piece',
            'modality': 'video',
            'profileId': 'instagram-reels-video',
            'decision': 'approved_for_local_delivery',
            'expectedVersionId': reels['deliveryVersionId'],
            'note': 'ci-bot',
        })
        pkg = post_json(f'{base}/api/works/package', {
            'workId': w1,
            'pieces': [{'modality': 'video', 'profileId': 'instagram-reels-video', 'expectedVersionId': reels['deliveryVersionId']}],
        })
        pkg_info = pkg.get('packageDelivery') or pkg
        assert pkg.get('ok') and pkg_info.get('available'), f'package build failed: {pkg}'

        print('studio-production-queue CI HTTP proof ok')
        print(json.dumps({
            'batchId': batch_id,
            'counts': batch['counts'],
            'zipSha256': (pkg_info.get('lastValidDelivery') or {}).get('zipSha256'),
        }, ensure_ascii=False))
        return 0
    finally:
        studio.close()
        httpd.shutdown()
        httpd.server_close()
        for wid in (w1, w2):
            shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', wid), ignore_errors=True)
        for pf in pfiles:
            if os.path.exists(pf):
                try:
                    os.remove(pf)
                except OSError:
                    pass


if __name__ == '__main__':
    raise SystemExit(main())
