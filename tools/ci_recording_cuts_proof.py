"""Prova HTTP curta da edicao de gravacoes e cortes por cena (CI e local).

Sobe o Studio em 127.0.0.1, importa uma gravacao ficticia MP4 H.264 em blocos
(com FFprobe), recorta trechos que comecam depois de zero em cenas diferentes,
reaproveita um trecho em outra posicao, exporta Reels 1080x1920 e YouTube
1920x1080 do mesmo pedido, confere os quadros por cor do trecho (detecta
inicio no instante zero ou no keyframe errado), reexporta um perfil alterando
so o inicio (hash do MP4 muda; SRT/TXT/fonte preservados), provoca corte fora
do intervalo (ultima entrega valida preservada), aprova, empacota ZIP com
referencia aos cortes e recupera apos reinicio. Dados ficticios.

Uso: python tools/ci_recording_cuts_proof.py [--port 8797] [--keep]
"""

import argparse
import base64
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import zlib

ROOT = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import make_proof_assets  # noqa: E402
import render_local  # noqa: E402

WORK_ID = 'ci-recording-cuts-work'
PROJECT_ID = 'ci-recording-cuts-proj'
ALLOWED = ['instagram-reels-video', 'youtube-shorts', 'youtube-video-horizontal']
TMP_REL = '.workspace/tmp/ci-recording-cuts'


def decode_png(path):
    with open(path, 'rb') as handle:
        d = handle.read()
    pos = 8
    idat = b''
    w = h = None
    while pos < len(d):
        ln = struct.unpack('>I', d[pos:pos + 4])[0]
        tag = d[pos + 4:pos + 8]
        data = d[pos + 8:pos + 8 + ln]
        if tag == b'IHDR':
            w, h, _bd, _ct = struct.unpack('>IIBB', data[:10])
        if tag == b'IDAT':
            idat += data
        pos += 12 + ln
    raw = zlib.decompress(idat)
    stride = w * 3 + 1
    px = bytearray(w * h * 3)
    prev = bytearray(w * 3)
    for y in range(h):
        f = raw[y * stride]
        line = bytearray(raw[y * stride + 1:(y + 1) * stride])
        for x in range(len(line)):
            a = line[x - 3] if x >= 3 else 0
            b = prev[x]
            c = prev[x - 3] if x >= 3 else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        px[y * w * 3:(y + 1) * w * 3] = line
        prev = line
    return w, h, px


def color_signature(px):
    r, g, b = px
    if r > 150 and g < 110 and b < 110:
        return 'A'
    if g > 130 and r < 120 and b < 120:
        return 'B'
    if b > 150 and r < 120 and g < 130:
        return 'C'
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prova HTTP de cortes por cena do Studio')
    parser.add_argument('--port', type=int, default=8797)
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

    def wait_export(payload, expect='completed'):
        res = call('/api/export', payload)
        jid = res['jobId']
        for _ in range(360):
            st = call('/api/export/status?' + urllib.parse.urlencode({'job': jid}))
            if st['status'] == expect:
                return st
            if st['status'] in ('failed', 'interrupted') and expect == 'completed':
                raise RuntimeError(f'Export falhou na prova: {st}')
            if st['status'] == 'completed' and expect == 'failed':
                raise RuntimeError(f'Export deveria falhar na prova: {st}')
            time.sleep(0.5)
        raise RuntimeError('Timeout esperando exportacao na prova')

    def ffprobe(rel_path):
        out = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json',
             render_local.fs_path(os.path.join(ROOT, rel_path))],
            capture_output=True, text=True, timeout=60,
        )
        if out.returncode != 0:
            raise RuntimeError(f'ffprobe falhou: {out.stderr}')
        return json.loads(out.stdout)

    def frame_pixel(video_rel, t, fx, fy):
        out_png = os.path.join(ROOT, TMP_REL, 'frame.png')
        res = subprocess.run(
            ['ffmpeg', '-y', '-ss', f'{t:.3f}', '-i', render_local.fs_path(os.path.join(ROOT, video_rel)),
             '-frames:v', '1', render_local.fs_path(out_png)],
            capture_output=True, text=True, timeout=120,
        )
        if res.returncode != 0:
            raise RuntimeError(f'extracao de quadro falhou: {res.stderr[-200:]}')
        w, h, px = decode_png(out_png)
        x, y = int(w * fx), int(h * fy)
        return tuple(px[(y * w + x) * 3:(y * w + x) * 3 + 3])

    try:
        wait_ready()
        os.makedirs(render_local.fs_path(os.path.join(ROOT, TMP_REL)), exist_ok=True)
        fixture_rel = f'{TMP_REL}/gravacao.mp4'
        make_proof_assets.write_recording_mp4(os.path.join(ROOT, fixture_rel), duration_s=12.0)
        image_rel = f'{TMP_REL}/cartela.png'
        make_proof_assets.write_scene_png(os.path.join(ROOT, image_rel), PROJECT_ID, 'cartela', 1)

        manifest = {
            'schemaVersion': 1, 'id': PROJECT_ID, 'name': 'CI cortes por cena',
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
            'id': WORK_ID, 'name': 'CI cortes por cena', 'project': project_rel,
            'template': 'blank', 'overwrite': True,
        })
        paths = wk['work']['paths']

        # Importacao em blocos com validacao FFprobe.
        with open(os.path.join(ROOT, fixture_rel), 'rb') as handle:
            data = handle.read()
        start = call('/api/works/media/import-video/start', {
            'workId': WORK_ID, 'fileName': 'gravacao.mp4', 'totalBytes': len(data),
            'origin': 'imported-manual', 'license': 'owned-synthetic',
        })
        offset = 0
        while offset < len(data):
            chunk = data[offset:offset + start['chunkBytes']]
            call('/api/works/media/import-video/chunk', {
                'uploadId': start['uploadId'], 'offset': offset,
                'dataBase64': base64.b64encode(chunk).decode('ascii'),
            })
            offset += len(chunk)
        finish = call('/api/works/media/import-video/finish', {'uploadId': start['uploadId'], 'workId': WORK_ID})
        version = finish['version']
        assert version['codec'] == 'h264' and version['kind'] == 'video', version
        assert abs(version['durationSeconds'] - 12.0) < 0.1, version
        source_sha = hashlib.sha256(data).hexdigest()
        assert version['sha256'] == source_sha

        # Seek HTTP: intervalos distintos do arquivo registrado.
        req = urllib.request.Request(
            base + '/source-media?path=' + urllib.parse.quote(version['path']),
            headers={'Range': 'bytes=1000-1999'})
        with urllib.request.urlopen(req, timeout=60) as r:
            assert r.status == 206
            assert r.read() == data[1000:2000]

        opened = call('/api/works/open?id=' + WORK_ID)
        vreq = opened['videoRequest']
        vreq['id'] = 'ci-cuts'
        vreq['profiles'] = ['instagram-reels-video', 'youtube-video-horizontal']
        vreq['media'] = [
            {'id': 'gravacao', 'path': version['path'], 'type': 'video',
             'origin': version['origin'], 'license': version['license']},
            {'id': 'cartela', 'path': image_rel, 'type': 'image',
             'origin': 'synthetic-demo', 'license': 'owned-synthetic'},
        ]
        vreq['scenes'] = [
            {'id': 'cena-1', 'durationMs': 2400, 'sourceStartMs': 4200, 'mediaId': 'gravacao',
             'caption': 'Trecho B', 'narration': 'Narracao B.', 'title': 'TITULO CORTE B'},
            {'id': 'cena-2', 'durationMs': 2000, 'mediaId': 'cartela',
             'caption': 'Cartela', 'narration': 'Narracao cartela.'},
            {'id': 'cena-3', 'durationMs': 1700, 'sourceStartMs': 8300, 'mediaId': 'gravacao',
             'caption': 'Trecho C', 'narration': 'Narracao C.'},
            {'id': 'cena-4', 'durationMs': 1500, 'sourceStartMs': 4200, 'mediaId': 'gravacao',
             'caption': 'Trecho B de novo', 'narration': 'Narracao B2.'},
        ]
        call('/api/works/save', {'workId': WORK_ID, 'videoRequest': vreq})

        prev = call('/api/preview', {'request': vreq})
        beats = prev['result']['profiles'][0]['beats']
        assert [b['sourceStartMs'] for b in beats] == [4200, None, 8300, 4200], beats
        assert [b['startMs'] for b in beats] == [0, 2400, 4400, 6100], beats

        st = wait_export({'workId': WORK_ID, 'kind': 'video', 'request': vreq,
                          'outputDir': paths['videoDeliveryDir']})
        measures = {}
        for pid, (w, h), fx, fy in (
            ('instagram-reels-video', (1080, 1920), 0.10, 0.92),
            ('youtube-video-horizontal', (1920, 1080), 0.50, 0.92),
        ):
            dm = json.load(open(os.path.join(ROOT, paths['videoDeliveryDir'], pid, 'delivery-manifest.json'), encoding='utf-8'))
            video_rel = dm['artifacts']['video']['path']
            probe = ffprobe(video_rel)
            v = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            assert (v['width'], v['height']) == (w, h), (pid, v)
            assert v['codec_name'] == 'h264' and v['r_frame_rate'] == '30/1', v
            assert not [s for s in probe['streams'] if s['codec_type'] == 'audio'], probe
            assert abs(float(probe['format']['duration']) - 7.6) < 0.11, probe['format']
            assert color_signature(frame_pixel(video_rel, 0.10, fx, fy)) == 'B', pid
            assert color_signature(frame_pixel(video_rel, 5.00, fx, fy)) == 'C', pid
            assert color_signature(frame_pixel(video_rel, 6.80, fx, fy)) == 'B', pid
            assert [c['sourceStartMs'] for c in dm['sourceCuts']] == [4200, 0, 8300, 4200]
            for cut in dm['sourceCuts']:
                if cut['beatId'] != 'cena-2':
                    assert cut['sha256'] == source_sha
            measures[pid] = {'width': w, 'height': h, 'fps': v['r_frame_rate'], 'codec': 'h264',
                             'audioStreams': 0, 'sha256': dm['artifacts']['video']['sha256']}

        def artifact_hashes(pid):
            dm = json.load(open(os.path.join(ROOT, paths['videoDeliveryDir'], pid, 'delivery-manifest.json'), encoding='utf-8'))
            return {k: dm['artifacts'][k]['sha256'] for k in ('video', 'srt', 'narration')}

        reels_before = artifact_hashes('instagram-reels-video')
        horiz_before = artifact_hashes('youtube-video-horizontal')

        # Reexportacao de um perfil: so o inicio muda; MP4 muda, SRT/TXT/fonte ficam.
        vreq['scenes'][0]['sourceStartMs'] = 4600
        call('/api/works/save', {'workId': WORK_ID, 'videoRequest': vreq})
        wait_export({'workId': WORK_ID, 'kind': 'video', 'request': vreq,
                     'outputDir': paths['videoDeliveryDir'], 'profile': 'instagram-reels-video'})
        reels_after = artifact_hashes('instagram-reels-video')
        assert reels_after['video'] != reels_before['video']
        assert reels_after['srt'] == reels_before['srt']
        assert reels_after['narration'] == reels_before['narration']
        assert artifact_hashes('youtube-video-horizontal') == horiz_before
        assert hashlib.sha256(open(os.path.join(ROOT, version['path']), 'rb').read()).hexdigest() == source_sha

        # Corte fora do intervalo: falha controlada preserva a ultima entrega valida.
        vreq['scenes'][2]['durationMs'] = 4000  # 8300 + 4000 > 12000
        call('/api/works/save', {'workId': WORK_ID, 'videoRequest': vreq})
        failed = wait_export({'workId': WORK_ID, 'kind': 'video', 'request': vreq,
                              'outputDir': paths['videoDeliveryDir'], 'profile': 'instagram-reels-video'},
                             expect='failed')
        assert 'SOURCE_CUT_OUT_OF_RANGE' in json.dumps(failed), failed
        assert artifact_hashes('instagram-reels-video') == reels_after
        index = json.load(open(os.path.join(ROOT, paths['videoDeliveryDir'], 'index.json'), encoding='utf-8'))
        entry = next(p for p in index['profiles'] if p['profileId'] == 'instagram-reels-video')
        assert entry['lastValidDelivery'] and entry['lastAttempt']['status'] == 'failed'

        # Restaura o corte valido, aprova e empacota com referencia aos cortes.
        vreq['scenes'][2]['durationMs'] = 1700
        call('/api/works/save', {'workId': WORK_ID, 'videoRequest': vreq})
        wait_export({'workId': WORK_ID, 'kind': 'video', 'request': vreq,
                     'outputDir': paths['videoDeliveryDir'], 'profile': 'instagram-reels-video'})
        rev = call('/api/works/review?id=' + WORK_ID)
        selection = []
        for piece in rev['pieces']:
            # O horizontal ficou com rascunho anterior (inicio 4200) e pede
            # reexportacao; empacota apenas o perfil reexportado e aprovado.
            if piece['modality'] != 'video' or piece['profileId'] != 'instagram-reels-video':
                if piece['profileId'] == 'youtube-video-horizontal':
                    assert piece['status'] == 'draft_outdated', piece
                continue
            assert piece['status'] in ('pending_review', 'reexported_pending'), piece
            call('/api/works/review/decide', {'workId': WORK_ID, 'targetType': 'piece', 'modality': 'video',
                                              'profileId': piece['profileId'], 'decision': 'approved_for_local_delivery',
                                              'expectedVersionId': piece['deliveryVersionId']})
            selection.append({'modality': 'video', 'profileId': piece['profileId'],
                              'expectedVersionId': piece['deliveryVersionId']})
        pkg = call('/api/works/package', {'workId': WORK_ID, 'pieces': selection, 'channels': []})
        pkg_delivery = pkg['packageDelivery']
        assert pkg_delivery['available'], pkg_delivery
        zip_abs = os.path.join(ROOT, paths['packageDeliveryDir'], 'delivery-package.zip')
        zdata = open(zip_abs, 'rb').read()
        zsha = hashlib.sha256(zdata).hexdigest()
        with zipfile.ZipFile(zip_abs) as zf:
            assert zf.testzip() is None
            pm = json.loads(zf.read('package-manifest.json'))
            for piece in pm['pieces']:
                assert piece.get('sourceCuts'), piece
                assert [c['sourceStartMs'] for c in piece['sourceCuts']] == [4600, 0, 8300, 4200]
                for f in piece['files']:
                    assert hashlib.sha256(zf.read(f['archivePath'])).hexdigest() == f['sha256']

        # Reinicio: escolhas de corte e pacote recuperados.
        proc.terminate()
        proc.wait(timeout=30)
        proc = subprocess.Popen(
            [sys.executable, os.path.join(ROOT, 'tools', 'video_studio.py'), '--port', str(args.port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        wait_ready()
        reopened = call('/api/works/open?id=' + WORK_ID)
        scenes = reopened['videoRequest']['scenes']
        assert [s.get('sourceStartMs') for s in scenes] == [4600, None, 8300, 4200], scenes
        assert reopened['packageDelivery']['available']
        assert hashlib.sha256(open(zip_abs, 'rb').read()).hexdigest() == zsha

        print('recording-cuts CI HTTP proof ok: import MP4, cuts between keyframes, reels+horizontal, single-profile reexport, controlled failure, zip, restart')
        print(json.dumps({'workId': WORK_ID, 'zipSha256': zsha, 'zipBytes': len(zdata),
                          'sourceSha256': source_sha, 'measures': measures}, ensure_ascii=False))
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
            shutil.rmtree(render_local.fs_path(os.path.join(ROOT, TMP_REL), force=True), ignore_errors=True)


if __name__ == '__main__':
    raise SystemExit(main())