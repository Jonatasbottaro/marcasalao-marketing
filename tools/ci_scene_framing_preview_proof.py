"""Prova HTTP curta de enquadramento por cena/destino e previa da montagem (CI e local).

Sobe o Studio em 127.0.0.1, importa gravacao horizontal ficticia em tela dividida
(esquerda RED / direita BLUE apos 3.5s) e gera cartela estatica, testa
/api/video/frame-info e fallback Fit para metadado de rotacao != 0, configura
Preencher no lado direito para Reels (9:16) e Ajustar no YouTube (16:9), gera as
duas previas da montagem (com Range 206, cache limitado <= 4 MP4s e invalidacao por
edicao concorrente), exporta Reels, YouTube, Motion 9:16 e Carrossel 1:1, confere
geometria/fps/zero-audio via FFprobe, compara pixels entre previa e MP4 final
(incluindo detector que falha se aplicar ao perfil errado), invalida apenas
Reels+Motion ao mudar o quadro de Reels, reexporta mantendo hashes de SRT/TXT/YouTube/fonte,
provoca falha controlada com preservacao da entrega valida anterior e valida o
ZIP com package-manifest.json (sourceCuts, framings e SHA-256 dos bytes).

Uso: python tools/ci_scene_framing_preview_proof.py [--port 8799] [--keep]
"""

import argparse
import base64
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

import build_video  # noqa: E402
import ci_recording_cuts_proof  # noqa: E402
import make_proof_assets  # noqa: E402
import render_local  # noqa: E402

WORK_ID = 'ci-scene-framing-preview-work'
PROJECT_ID = 'ci-scene-framing-preview-proj'
ALLOWED = [
    'instagram-reels-video',
    'youtube-shorts',
    'youtube-video-horizontal',
    'instagram-feed-image-square',
]
TMP_REL = '.workspace/tmp/ci-scene-framing-preview'


def classify_rgb(rgb):
    r, g, b = rgb
    if r > 150 and g < 110 and b < 110:
        return 'RED'
    if b > 150 and r < 110 and g < 130:
        return 'BLUE'
    if g > 130 and r < 120 and b < 120:
        return 'GREEN'
    return f'OTHER({r},{g},{b})'


def write_split_horizontal_recording(path, duration_s=10.0, fps=30, rotate=None):
    """Gera MP4 H.264 1920x1080 mudo com verde (0-3.5s) e tela dividida RED/BLUE (3.5-duration_s)."""
    os.makedirs(render_local.fs_path(os.path.dirname(path)), exist_ok=True)
    vf = (
        "split=3[bg][lsrc][rsrc];"
        "[lsrc]crop=960:1080:0:0,drawbox=x=0:y=0:w=960:h=1080:color=0xDC2828:t=fill[left];"
        "[rsrc]crop=960:1080:960:0,drawbox=x=0:y=0:w=960:h=1080:color=0x2850DC:t=fill[right];"
        "[left][right]hstack=inputs=2[splitlr];"
        "[bg]drawbox=x=0:y=0:w=1920:h=1080:color=0x28A03C:t=fill[intro];"
        "[intro][splitlr]overlay=0:0:enable='gte(t,3.5)',setsar=1"
    )
    cmd = [
        build_video.get_ffmpeg(), '-y',
        '-f', 'lavfi', '-i', f'color=c=0x28A03C:s=1920x1080:r={fps}:d={duration_s:.2f}',
        '-an', '-vf', vf,
        '-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p',
        '-g', '90', '-keyint_min', '90', '-sc_threshold', '0', '-r', str(fps),
    ]
    target = path if rotate is None else f'{path}.norot.mp4'
    cmd.append(render_local.fs_path(target))
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if res.returncode != 0:
        raise RuntimeError(f'falha ao gerar gravacao sintetica: {res.stderr[-300:]}')
    if rotate is not None:
        try:
            remux = subprocess.run(
                [build_video.get_ffmpeg(), '-y', '-display_rotation:v:0', str(rotate),
                 '-i', render_local.fs_path(target), '-c', 'copy', render_local.fs_path(path)],
                capture_output=True, text=True, timeout=60,
            )
            if remux.returncode != 0:
                raise RuntimeError(f'falha ao aplicar rotacao sintetica: {remux.stderr[-300:]}')
        finally:
            if os.path.exists(render_local.fs_path(target)):
                os.remove(render_local.fs_path(target))


def frame_pixel_abs(video_abs, t_seconds, fx, fy, out_png_abs):
    res = subprocess.run(
        [build_video.get_ffmpeg(), '-y', '-ss', f'{t_seconds:.3f}',
         '-i', render_local.fs_path(video_abs), '-frames:v', '1',
         render_local.fs_path(out_png_abs)],
        capture_output=True, text=True, timeout=120,
    )
    if res.returncode != 0:
        raise RuntimeError(f'extracao de quadro falhou em t={t_seconds}: {res.stderr[-240:]}')
    w, h, px = ci_recording_cuts_proof.decode_png(out_png_abs)
    x = min(w - 1, max(0, int(w * fx)))
    y = min(h - 1, max(0, int(h * fy)))
    return tuple(px[(y * w + x) * 3:(y * w + x) * 3 + 3])


def verify_split_framing_pixels(video_abs, profile_id, tmp_png_abs, expect_reels='BLUE'):
    """Detector automatizado: falha se o enquadramento esperado for aplicado ao perfil errado."""
    left = classify_rgb(frame_pixel_abs(video_abs, 0.75, 0.18, 0.50, tmp_png_abs))
    right = classify_rgb(frame_pixel_abs(video_abs, 0.75, 0.82, 0.50, tmp_png_abs))
    if profile_id == 'instagram-reels-video':
        if left != expect_reels or right != expect_reels:
            raise AssertionError(
                f'enquadramento errado para {profile_id}: esquerda={left}, direita={right}, esperado={expect_reels}'
            )
    elif profile_id == 'youtube-video-horizontal':
        if left != 'RED' or right != 'BLUE':
            raise AssertionError(
                f'enquadramento errado para {profile_id}: esquerda={left} (esperado RED), direita={right} (esperado BLUE)'
            )
    else:
        raise AssertionError(f'perfil nao previsto: {profile_id}')
    return {'left': left, 'right': right}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prova HTTP de enquadramento e previa da montagem')
    parser.add_argument('--port', type=int, default=8799)
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

    def wait_preview(payload):
        t0 = time.monotonic()
        res = call('/api/video/preview-render', payload)
        jid = res['jobId']
        pid = payload['profileId']
        for _ in range(240):
            st = call('/api/video/preview-status?' + urllib.parse.urlencode({
                'job': jid, 'work': WORK_ID, 'profile': pid,
            }))
            if st['job']['status'] == 'completed':
                return st, round(time.monotonic() - t0, 3)
            if st['job']['status'] in ('failed', 'interrupted'):
                raise RuntimeError(f'Previa falhou na prova: {st}')
            time.sleep(0.25)
        raise RuntimeError('Timeout esperando previa da montagem na prova')

    def wait_export(payload, expect='completed'):
        t0 = time.monotonic()
        res = call('/api/export', payload)
        jid = res['jobId']
        for _ in range(360):
            st = call('/api/export/status?' + urllib.parse.urlencode({'job': jid}))
            if st['status'] == expect:
                return st, round(time.monotonic() - t0, 3)
            if st['status'] in ('failed', 'interrupted') and expect == 'completed':
                raise RuntimeError(f'Export falhou na prova: {st}')
            if st['status'] == 'completed' and expect == 'failed':
                raise RuntimeError(f'Export deveria falhar na prova: {st}')
            time.sleep(0.4)
        raise RuntimeError('Timeout esperando exportacao na prova')

    def ffprobe(rel_path):
        out = subprocess.run(
            [build_video.get_ffprobe(), '-v', 'error', '-show_streams', '-show_format', '-of', 'json',
             render_local.fs_path(os.path.join(ROOT, rel_path))],
            capture_output=True, text=True, timeout=60,
        )
        if out.returncode != 0:
            raise RuntimeError(f'ffprobe falhou: {out.stderr}')
        return json.loads(out.stdout)

    try:
        wait_ready()
        os.makedirs(render_local.fs_path(os.path.join(ROOT, TMP_REL)), exist_ok=True)
        rec_src = os.path.join(ROOT, TMP_REL, 'split-recording.mp4')
        rot_src = os.path.join(ROOT, TMP_REL, 'split-rotated.mp4')
        img_rel = f'{TMP_REL}/cartela-estatica.png'
        write_split_horizontal_recording(rec_src, duration_s=10.0)
        write_split_horizontal_recording(rot_src, duration_s=5.0, rotate=90)
        make_proof_assets.write_scene_png(os.path.join(ROOT, img_rel), PROJECT_ID, 'cartela', 2)

        manifest = {
            'schemaVersion': 1, 'id': PROJECT_ID, 'name': 'CI enquadramento e previa',
            'locale': 'pt-BR', 'timezone': 'America/Sao_Paulo', 'brandTheme': PROJECT_ID,
            'assetRoot': f'.workspace/studio/projects/{PROJECT_ID}/assets',
            'contentPolicies': {
                'requireApprovedBriefing': True, 'requireApprovedScript': True,
                'prohibitPersonalData': True, 'requireFunctionalEvidence': True,
            },
            'outputProfiles': ALLOWED,
        }
        proj = call('/api/projects/create', {'project': manifest, 'overwrite': True})
        wk = call('/api/works/create', {
            'id': WORK_ID, 'name': 'CI enquadramento e previa',
            'project': proj['project']['path'], 'template': 'blank', 'overwrite': True,
        })
        paths = wk['work']['paths']

        # Importa ambas as gravacoes em blocos pelo fluxo do Studio.
        uploaded = {}
        for key, local_abs, fname in (('split', rec_src, 'split-recording.mp4'), ('rot', rot_src, 'split-rotated.mp4')):
            with open(render_local.fs_path(local_abs), 'rb') as handle:
                data = handle.read()
            start = call('/api/works/media/import-video/start', {
                'workId': WORK_ID, 'fileName': fname, 'totalBytes': len(data),
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
            uploaded[key] = call('/api/works/media/import-video/finish', {
                'uploadId': start['uploadId'], 'workId': WORK_ID,
            })['version']

        rec_rel = uploaded['split']['path']
        rot_rel = uploaded['rot']['path']
        source_sha = uploaded['split']['sha256']

        # Frame-info valido (Preencher direita) e bloqueado por rotacao != 0 com fallback Fit.
        finfo_ok = call('/api/video/frame-info', {
            'workId': WORK_ID, 'profileId': 'instagram-reels-video',
            'mediaPath': rec_rel, 'beatId': 'cena-1',
            'framing': {'centerX': 0.82, 'centerY': 0.50, 'zoomPercent': 150},
        })
        assert finfo_ok['ok'] and finfo_ok['resolvedFraming']['cropWidth'] % 2 == 0, finfo_ok
        assert finfo_ok['resolvedFraming']['cropX'] > 960, finfo_ok

        finfo_rot = call('/api/video/frame-info', {
            'workId': WORK_ID, 'profileId': 'instagram-reels-video',
            'mediaPath': rot_rel, 'beatId': 'cena-1',
            'framing': {'centerX': 0.50, 'centerY': 0.50, 'zoomPercent': 120},
        })
        assert (not finfo_rot['ok']
                and finfo_rot['errorCode'] == 'FRAMING_MEDIA_METADATA_UNSUPPORTED'
                and finfo_rot['fallbackMode'] == 'fit'), finfo_rot

        opened = call('/api/works/open?id=' + WORK_ID)
        vreq = opened['videoRequest']
        vreq['id'] = 'ci-framing-preview'
        vreq['profiles'] = ['instagram-reels-video', 'youtube-video-horizontal']
        vreq['media'] = [
            {'id': 'gravacao', 'path': rec_rel, 'type': 'video', 'origin': 'imported-manual', 'license': 'owned-synthetic'},
            {'id': 'cartela', 'path': img_rel, 'type': 'image', 'origin': 'synthetic-demo', 'license': 'owned-synthetic'},
        ]
        vreq['scenes'] = [
            {'id': 'cena-1', 'durationMs': 2200, 'sourceStartMs': 3800, 'mediaId': 'gravacao',
             'caption': 'Detalhe direita no Reels', 'narration': 'Narracao cena 1.', 'title': 'TITULO ENQUADRAMENTO',
             'framingByProfile': {'instagram-reels-video': {'centerX': 0.82, 'centerY': 0.50, 'zoomPercent': 150}}},
            {'id': 'cena-2', 'durationMs': 1800, 'mediaId': 'cartela',
             'caption': 'Cartela estatica', 'narration': 'Narracao cena 2.'},
        ]
        mplan = {
            'schemaVersion': 1, 'requestId': 'ci-framing-preview',
            'effects': [{
                'sceneId': 'cena-2',
                'region': {'x': 0.15, 'y': 0.35, 'w': 0.70, 'h': 0.15},
                'color': '#FFD700', 'thickness': 6, 'startMs': 200, 'endMs': 1500,
            }],
        }
        creq = {
            'schemaVersion': 1, 'id': 'ci-car-framing', 'project': wk['work']['project'],
            'profile': 'instagram-feed-image-square', 'title': 'Carrossel independente',
            'media': [{'id': 'cimg', 'path': img_rel, 'type': 'image', 'origin': 'synthetic-demo', 'license': 'owned-synthetic'}],
            'cards': [{'id': 'card1', 'mediaId': 'cimg', 'title': 'Card independente', 'body': 'Copia fixa.'}],
        }
        call('/api/works/save', {'workId': WORK_ID, 'videoRequest': vreq, 'carouselRequest': creq, 'motionPlan': mplan})

        # Previa concorrente -> edicao durante geracao marca versao anterior e respeita cache <= 4 MP4s.
        conc_job = call('/api/video/preview-render', {
            'workId': WORK_ID, 'profileId': 'instagram-reels-video', 'request': vreq,
        })
        edited = json.loads(json.dumps(vreq))
        edited['scenes'][0]['framingByProfile']['instagram-reels-video']['zoomPercent'] = 175
        call('/api/works/save', {'workId': WORK_ID, 'videoRequest': edited})
        for _ in range(240):
            st_conc = call('/api/video/preview-status?' + urllib.parse.urlencode({
                'job': conc_job['jobId'], 'work': WORK_ID, 'profile': 'instagram-reels-video',
            }))
            if st_conc['job']['status'] != 'running':
                break
            time.sleep(0.25)
        assert st_conc['job']['status'] == 'completed', st_conc
        assert not st_conc['lastReady']['matchesCurrentDraft'] and st_conc['lastReady']['state'] == 'outdated', st_conc

        for z in (120, 140, 160, 190):
            rz = json.loads(json.dumps(vreq))
            rz['scenes'][0]['framingByProfile']['instagram-reels-video']['zoomPercent'] = z
            call('/api/works/save', {'workId': WORK_ID, 'videoRequest': rz})
            wait_preview({'workId': WORK_ID, 'profileId': 'instagram-reels-video', 'request': rz})
        preview_dir = os.path.join(ROOT, '.workspace', 'studio', 'works', WORK_ID, 'previews')
        assert len([n for n in os.listdir(preview_dir) if n.endswith('.mp4')]) <= 4

        # Restaura rascunho base, gera previas finais Reels + YouTube e testa Range 206.
        call('/api/works/save', {'workId': WORK_ID, 'videoRequest': vreq})
        timings = {}
        preview_abs = {}
        for pid in ('instagram-reels-video', 'youtube-video-horizontal'):
            pst, p_secs = wait_preview({
                'workId': WORK_ID, 'profileId': pid, 'request': vreq,
                'motionPlan': mplan if pid == 'instagram-reels-video' else None,
            })
            timings[f'preview_{pid}_s'] = p_secs
            assert pst['lastReady']['matchesCurrentDraft'], pst
            preview_abs[pid] = os.path.join(preview_dir, pst['lastReady']['file'])
            rreq = urllib.request.Request(base + pst['lastReady']['url'], headers={'Range': 'bytes=128-383'})
            with urllib.request.urlopen(rreq, timeout=60) as resp:
                assert resp.status == 206 and len(resp.read()) == 256

        # Exporta videos (Reels+YouTube), Motion 9:16 e Carrossel.
        _, timings['export_video_both_s'] = wait_export({
            'workId': WORK_ID, 'kind': 'video', 'request': vreq, 'outputDir': paths['videoDeliveryDir'],
        })
        _, timings['export_motion_s'] = wait_export({
            'workId': WORK_ID, 'kind': 'video', 'request': vreq, 'motionPlan': mplan,
            'profile': 'instagram-reels-video', 'outputDir': paths['motionDeliveryDir'],
        })
        _, timings['export_carousel_s'] = wait_export({
            'workId': WORK_ID, 'kind': 'carousel', 'request': creq, 'outputDir': paths['carouselDeliveryDir'],
        })

        cmp_png = os.path.join(ROOT, TMP_REL, 'cmp-frame.png')
        measures = {}
        final_abs = {}
        for pid, (exp_w, exp_h) in (('instagram-reels-video', (1080, 1920)), ('youtube-video-horizontal', (1920, 1080))):
            dm = json.load(open(os.path.join(ROOT, paths['videoDeliveryDir'], pid, 'delivery-manifest.json'), encoding='utf-8'))
            mp4_rel = dm['artifacts']['video']['path']
            final_abs[pid] = os.path.join(ROOT, mp4_rel)
            probe = ffprobe(mp4_rel)
            v = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            assert (v['width'], v['height']) == (exp_w, exp_h), (pid, v)
            assert v['r_frame_rate'] == '30/1', v
            assert not [s for s in probe['streams'] if s['codec_type'] == 'audio'], probe
            prev_colors = verify_split_framing_pixels(preview_abs[pid], pid, cmp_png, expect_reels='BLUE')
            mp4_colors = verify_split_framing_pixels(final_abs[pid], pid, cmp_png, expect_reels='BLUE')
            assert prev_colors == mp4_colors
            measures[pid] = {
                'width': exp_w, 'height': exp_h, 'fps': v['r_frame_rate'],
                'audioStreams': 0, 'previewColors': prev_colors, 'mp4Colors': mp4_colors,
            }

        # Detector automatizado deve falhar ao validar arquivo do perfil errado.
        wrong_detector_failed = False
        try:
            verify_split_framing_pixels(final_abs['youtube-video-horizontal'], 'instagram-reels-video', cmp_png, expect_reels='BLUE')
        except AssertionError:
            wrong_detector_failed = True
        assert wrong_detector_failed

        # Aprova todas as 4 pecas e altera APENAS o enquadramento do Reels para esquerda (RED).
        rev0 = call('/api/works/review?id=' + WORK_ID)
        for p in rev0['pieces']:
            call('/api/works/review/decide', {
                'workId': WORK_ID, 'targetType': 'piece', 'modality': p['modality'],
                'profileId': p['profileId'], 'decision': 'approved_for_local_delivery',
                'expectedVersionId': p['deliveryVersionId'],
            })

        def video_hashes(pid):
            dm = json.load(open(os.path.join(ROOT, paths['videoDeliveryDir'], pid, 'delivery-manifest.json'), encoding='utf-8'))
            return {k: dm['artifacts'][k]['sha256'] for k in ('video', 'srt', 'narration')}

        reels_before = video_hashes('instagram-reels-video')
        yt_before = video_hashes('youtube-video-horizontal')

        vreq['scenes'][0]['framingByProfile']['instagram-reels-video'] = {
            'centerX': 0.18, 'centerY': 0.50, 'zoomPercent': 150,
        }
        call('/api/works/save', {'workId': WORK_ID, 'videoRequest': vreq})
        rev1 = call('/api/works/review?id=' + WORK_ID)
        by_key = {p['pieceKey']: p for p in rev1['pieces']}
        assert by_key['video:instagram-reels-video']['status'] == 'draft_outdated', by_key
        assert by_key['motion:instagram-reels-video']['status'] == 'draft_outdated', by_key
        assert by_key['video:youtube-video-horizontal']['status'] == 'approved', by_key
        assert by_key['carousel:instagram-feed-image-square']['status'] == 'approved', by_key

        # Reexporta APENAS o Reels.
        _, timings['reexport_reels_s'] = wait_export({
            'workId': WORK_ID, 'kind': 'video', 'request': vreq,
            'profile': 'instagram-reels-video', 'outputDir': paths['videoDeliveryDir'],
        })
        reels_after = video_hashes('instagram-reels-video')
        assert reels_after['video'] != reels_before['video']
        assert reels_after['srt'] == reels_before['srt']
        assert reels_after['narration'] == reels_before['narration']
        assert video_hashes('youtube-video-horizontal') == yt_before
        assert hashlib.sha256(open(render_local.fs_path(os.path.join(ROOT, rec_rel)), 'rb').read()).hexdigest() == source_sha
        verify_split_framing_pixels(final_abs['instagram-reels-video'], 'instagram-reels-video', cmp_png, expect_reels='RED')

        # Falha controlada preserva entrega anterior.
        bad_req = json.loads(json.dumps(vreq))
        bad_req['scenes'][0]['durationMs'] = 9000
        wait_export({
            'workId': WORK_ID, 'kind': 'video', 'request': bad_req,
            'profile': 'instagram-reels-video', 'outputDir': paths['videoDeliveryDir'],
        }, expect='failed')
        assert video_hashes('instagram-reels-video') == reels_after

        # Reexporta Motion atualizado, aprova pecas e gera ZIP verificado.
        call('/api/works/save', {'workId': WORK_ID, 'videoRequest': vreq})
        wait_export({
            'workId': WORK_ID, 'kind': 'video', 'request': vreq, 'motionPlan': mplan,
            'profile': 'instagram-reels-video', 'outputDir': paths['motionDeliveryDir'],
        })
        rev2 = call('/api/works/review?id=' + WORK_ID)
        selection = []
        for p in rev2['pieces']:
            if p['status'] != 'approved':
                call('/api/works/review/decide', {
                    'workId': WORK_ID, 'targetType': 'piece', 'modality': p['modality'],
                    'profileId': p['profileId'], 'decision': 'approved_for_local_delivery',
                    'expectedVersionId': p['deliveryVersionId'],
                })
            selection.append({
                'modality': p['modality'], 'profileId': p['profileId'],
                'expectedVersionId': p['deliveryVersionId'],
            })
        pkg = call('/api/works/package', {'workId': WORK_ID, 'pieces': selection, 'channels': []})
        assert pkg['packageDelivery']['available'], pkg
        zip_abs = os.path.join(ROOT, paths['packageDeliveryDir'], 'delivery-package.zip')
        zbytes = open(render_local.fs_path(zip_abs), 'rb').read()
        zsha = hashlib.sha256(zbytes).hexdigest()
        with zipfile.ZipFile(render_local.fs_path(zip_abs), 'r') as zf:
            assert zf.testzip() is None
            assert not any('previews/' in n for n in zf.namelist())
            pm = json.loads(zf.read('package-manifest.json').decode('utf-8'))
            reels_piece = next(p for p in pm['pieces'] if p['modality'] == 'video' and p['profileId'] == 'instagram-reels-video')
            yt_piece = next(p for p in pm['pieces'] if p['modality'] == 'video' and p['profileId'] == 'youtube-video-horizontal')
            assert reels_piece['framings'][0]['framing']['mode'] == 'fill'
            assert abs(reels_piece['framings'][0]['framing']['centerX'] - 0.18) < 0.02
            assert yt_piece['framings'][0]['framing']['mode'] == 'fit'
            assert reels_piece['sourceCuts'][0]['sourceStartMs'] == 3800
            for piece in pm['pieces']:
                for f in piece['files']:
                    assert hashlib.sha256(zf.read(f['archivePath'])).hexdigest() == f['sha256'], f['archivePath']

        print('scene-framing-preview CI HTTP proof ok')
        print(json.dumps({
            'workId': WORK_ID, 'zipSha256': zsha, 'zipBytes': len(zbytes),
            'sourceSha256': source_sha, 'reelsBeforeSha': reels_before['video'],
            'reelsAfterSha': reels_after['video'], 'ytShaPreserved': yt_before['video'],
            'measures': measures, 'timings': timings,
        }, ensure_ascii=False))
        return 0
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=30)
        except Exception:
            proc.kill()
        if not args.keep:
            shutil.rmtree(render_local.fs_path(os.path.join(ROOT, '.workspace', 'studio', 'works', WORK_ID)), ignore_errors=True)
            proj_file = os.path.join(ROOT, '.workspace', 'studio', 'projects', f'{PROJECT_ID}.project.json')
            if os.path.exists(proj_file):
                os.remove(proj_file)
            shutil.rmtree(render_local.fs_path(os.path.join(ROOT, TMP_REL)), ignore_errors=True)


if __name__ == '__main__':
    raise SystemExit(main())
