"""Prova HTTP curta da exportacao multiformato no Studio local (CI e local).

Sobe o Studio em 127.0.0.1, registra um projeto ficticio com YouTube horizontal
e carrossel 4:5 na allowlist, exporta video vertical + horizontal e carrossel
4:5, confere geometrias/codec/fps/zero audio via FFprobe, dimensoes dos JPEGs,
aprovacao, ZIP multiformato e recuperacao apos reinicio. Dados ficticios.

Uso: python tools/ci_multi_format_proof.py [--port 8796] [--keep]
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import render_local  # noqa: E402

WORK_ID = 'ci-multi-format-work'
PROJECT_ID = 'ci-multi-format-proj'
ALLOWED = [
    'instagram-reels-video', 'youtube-shorts', 'youtube-video-horizontal',
    'instagram-feed-image-square', 'instagram-feed-image-portrait',
]
CREATIVE = {
    'hookOptions': [{'id': 'hook-1', 'text': 'Agenda organizada', 'angle': 'clareza'}],
    'selectedHookId': 'hook-1',
    'scriptSummary': 'Prova CI ficticia multiformato.',
    'videoScenes': [
        {'id': 'cena-abertura', 'objective': 'Abertura', 'narrativeFunction': 'hook',
         'durationMs': 4000, 'titleOverlay': 'TITULO HORIZONTAL CI', 'caption': 'Legenda CI do quadro horizontal',
         'narration': 'Narracao 1', 'requiredMediaDescriptor': 'Ilustracao ficticia de abertura',
         'mediaId': 'abertura', 'motionIntent': 'none'},
        {'id': 'cena-prova', 'objective': 'Prova', 'narrativeFunction': 'demonstration',
         'durationMs': 4000, 'titleOverlay': 'Agenda do dia', 'caption': 'Segunda legenda CI',
         'narration': 'Narracao 2', 'requiredMediaDescriptor': 'Captura ficticia da agenda',
         'mediaId': 'agenda', 'motionIntent': 'none'},
    ],
    'carouselCards': [
        {'id': 'capa', 'role': 'cover', 'title': 'Capa CI', 'body': 'Subtitulo direto', 'mediaId': 'abertura'},
        {'id': 'conteudo', 'role': 'content', 'title': 'Conteudo', 'body': 'Texto de apoio', 'mediaId': 'agenda'},
        {'id': 'fechamento', 'role': 'cta', 'title': 'Saiba mais', 'body': 'Confira'},
    ],
    'channelCopies': [],
}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prova HTTP multiformato do Studio')
    parser.add_argument('--port', type=int, default=8796)
    parser.add_argument('--keep', action='store_true')
    args = parser.parse_args(argv)

    base = f'http://127.0.0.1:{args.port}'
    hdrs = {'Content-Type': 'application/json', 'Origin': base}
    proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, 'tools', 'video_studio.py'), '--port', str(args.port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    def call(path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(base + path, data=data, headers=hdrs if data is not None else {})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='replace')[:400]
            raise RuntimeError(f'HTTP {exc.code} em {path}: {detail}') from exc

    def wait_ready():
        for _ in range(60):
            try:
                if call('/api/readiness')['readiness']['ready']:
                    return
            except Exception:
                time.sleep(0.25)
        raise RuntimeError('Studio nao ficou pronto na porta ' + str(args.port))

    def wait_export(payload):
        res = call('/api/export', payload)
        jid = res['jobId']
        for _ in range(360):
            st = call('/api/export/status?' + urllib.parse.urlencode({'job': jid}))
            if st['status'] == 'completed':
                return st
            if st['status'] in ('failed', 'interrupted'):
                raise RuntimeError(f'Export falhou na prova: {st}')
            time.sleep(0.5)
        raise RuntimeError('Timeout esperando exportacao na prova')

    def ffprobe(rel_path):
        out = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_streams', '-of', 'json',
             render_local.fs_path(os.path.join(ROOT, rel_path))],
            capture_output=True, text=True, timeout=60,
        )
        if out.returncode != 0:
            raise RuntimeError(f'ffprobe falhou: {out.stderr}')
        return json.loads(out.stdout)

    try:
        wait_ready()
        manifest = {
            'schemaVersion': 1, 'id': PROJECT_ID, 'name': 'CI multiformato',
            'locale': 'pt-BR', 'timezone': 'America/Sao_Paulo', 'brandTheme': PROJECT_ID,
            'assetRoot': f'.workspace/studio/projects/{PROJECT_ID}/assets',
            'contentPolicies': {
                'requireApprovedBriefing': True, 'requireApprovedScript': True,
                'prohibitPersonalData': True, 'requireFunctionalEvidence': True,
            },
            'outputProfiles': ALLOWED,
        }
        proj = call('/api/projects/create', {'project': manifest, 'overwrite': True})
        project_rel = proj['project']['path']
        wk = call('/api/works/create', {
            'id': WORK_ID, 'name': 'CI multiformato', 'project': project_rel,
            'template': 'blank', 'overwrite': True,
        })
        paths = wk['work']['paths']
        call('/api/works/planning/save', {
            'workId': WORK_ID, 'creative': CREATIVE, 'markCreativeChecked': True,
            'carouselProfileId': 'instagram-feed-image-portrait',
            'briefingExtended': {'recommendedProfiles': [
                'instagram-reels-video', 'youtube-video-horizontal', 'instagram-feed-image-portrait',
            ]},
        })
        applied = call('/api/works/planning/apply', {'workId': WORK_ID, 'applyVideo': True, 'applyCarousel': True})
        assert applied['applied']['video']['status'] == 'applied', applied
        assert applied['applied']['carousel']['status'] == 'applied', applied
        opened = applied['workData']
        assert 'youtube-video-horizontal' in opened['videoRequest']['profiles']
        assert opened['carouselRequest']['profile'] == 'instagram-feed-image-portrait'

        wait_export({'workId': WORK_ID, 'kind': 'video', 'request': opened['videoRequest'],
                     'outputDir': paths['videoDeliveryDir']})
        wait_export({'workId': WORK_ID, 'kind': 'carousel', 'request': opened['carouselRequest'],
                     'outputDir': paths['carouselDeliveryDir']})

        measures = {}
        for pid, (w, h) in (('instagram-reels-video', (1080, 1920)), ('youtube-video-horizontal', (1920, 1080))):
            dm = json.load(open(os.path.join(ROOT, paths['videoDeliveryDir'], pid, 'delivery-manifest.json'), encoding='utf-8'))
            probe = ffprobe(dm['artifacts']['video']['path'])
            v = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            assert (v['width'], v['height']) == (w, h), (pid, v)
            assert v['codec_name'] == 'h264', v
            assert v['r_frame_rate'] == '30/1', v
            assert not [s for s in probe['streams'] if s['codec_type'] == 'audio'], probe
            measures[pid] = {'width': v['width'], 'height': v['height'], 'fps': v['r_frame_rate'],
                             'codec': v['codec_name'], 'audioStreams': 0,
                             'sha256': dm['artifacts']['video']['sha256']}
        cm = json.load(open(os.path.join(ROOT, paths['carouselDeliveryDir'], 'carousel-manifest.json'), encoding='utf-8'))
        assert cm['geometry'] == {'width': 1080, 'height': 1350}, cm
        for card in cm['cards']:
            probe = ffprobe(card['path'])
            v = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            assert (v['width'], v['height']) == (1080, 1350), card
            assert card['sha256'] == hashlib.sha256(open(os.path.join(ROOT, card['path']), 'rb').read()).hexdigest()
        measures['carousel'] = {'geometry': cm['geometry'], 'cards': [c['file'] for c in cm['cards']]}

        # Motion restrito ao vertical: preview com motion no horizontal falha so naquele perfil.
        motion_plan = {'schemaVersion': 1, 'requestId': opened['videoRequest']['id'], 'effects': [
            {'sceneId': 'cena-prova', 'region': {'x': 0.1, 'y': 0.2, 'w': 0.5, 'h': 0.2},
             'color': '#FFD700', 'thickness': 6, 'startMs': 400, 'endMs': 2000},
        ]}
        prev = call('/api/preview', {'request': opened['videoRequest'], 'motionPlan': motion_plan})
        pmap = {p['profileId']: p for p in prev['result']['profiles']}
        assert pmap['youtube-video-horizontal']['failureCode'] == 'MOTION_LOCAL_UNSUPPORTED_GEOMETRY'
        assert pmap['instagram-reels-video']['status'] == 'compiled'

        channels = {}
        for pid in ('instagram-reels-video', 'youtube-video-horizontal', 'instagram-feed-image-portrait'):
            channels[pid] = {'profileId': pid, 'title': f'Titulo {pid}', 'postText': f'Texto {pid}',
                             'cta': 'Link na bio', 'destinationUrl': 'https://marcasalao.com.br', 'hashtags': '#ci'}
        ed = call('/api/works/editorial/save', {'workId': WORK_ID, 'channels': channels})
        for ch in ed['channels']:
            call('/api/works/review/decide', {'workId': WORK_ID, 'targetType': 'channel', 'profileId': ch['profileId'],
                                              'expectedCopySha256': ch['copySha256'], 'decision': 'approved_for_local_delivery'})
        rev = call('/api/works/review?id=' + WORK_ID)
        selection = []
        for piece in rev['pieces']:
            assert piece['status'] == 'pending_review', piece
            call('/api/works/review/decide', {'workId': WORK_ID, 'targetType': 'piece', 'modality': piece['modality'],
                                              'profileId': piece['profileId'], 'decision': 'approved_for_local_delivery',
                                              'expectedVersionId': piece['deliveryVersionId']})
            selection.append({'modality': piece['modality'], 'profileId': piece['profileId']})
        pkg = call('/api/works/package', {'workId': WORK_ID, 'pieces': selection, 'channels': list(channels)})
        assert pkg['packageDelivery']['available'], pkg
        zip_abs = os.path.join(ROOT, paths['packageDeliveryDir'], 'delivery-package.zip')
        zdata = open(zip_abs, 'rb').read()
        zsha = hashlib.sha256(zdata).hexdigest()
        with zipfile.ZipFile(zip_abs) as zf:
            names = zf.namelist()
            assert zf.testzip() is None
            for expected in ('video/instagram-reels-video/primary-output.mp4',
                             'video/youtube-video-horizontal/primary-output.mp4',
                             'carousel/instagram-feed-image-portrait/01-capa.jpg'):
                assert expected in names, names
            pm = json.loads(zf.read('package-manifest.json'))
            for f in pm.get('files') or []:
                if f.get('archivePath') in names and f.get('sha256'):
                    assert hashlib.sha256(zf.read(f['archivePath'])).hexdigest() == f['sha256']

        proc.terminate()
        proc.wait(timeout=30)
        proc = subprocess.Popen(
            [sys.executable, os.path.join(ROOT, 'tools', 'video_studio.py'), '--port', str(args.port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        wait_ready()
        reopened = call('/api/works/open?id=' + WORK_ID)
        assert reopened['packageDelivery']['available']
        rev2 = call('/api/works/review?id=' + WORK_ID)
        keys = {p['pieceKey'] for p in rev2['pieces']}
        assert 'video:youtube-video-horizontal' in keys
        assert 'carousel:instagram-feed-image-portrait' in keys
        assert hashlib.sha256(open(zip_abs, 'rb').read()).hexdigest() == zsha

        print('multi-format CI HTTP proof ok: horizontal+vertical video, 4:5 carousel, motion vertical-only, zip, restart')
        print(json.dumps({'workId': WORK_ID, 'zipSha256': zsha, 'zipBytes': len(zdata), 'measures': measures}, ensure_ascii=False))
        return 0
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=30)
        except Exception:
            proc.kill()
        if not args.keep:
            shutil.rmtree(render_local.fs_path(os.path.join(ROOT, '.workspace', 'studio', 'works', WORK_ID), force=True), ignore_errors=True)
            shutil.rmtree(render_local.fs_path(os.path.join(ROOT, '.workspace', 'studio', 'projects', f'{PROJECT_ID}.project.json'), force=True), ignore_errors=True)


if __name__ == '__main__':
    raise SystemExit(main())