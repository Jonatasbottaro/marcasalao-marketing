"""Prova HTTP de modelos reutilizaveis e variacoes em serie no Video Studio (CI).

Cobre: salvar modelo + nova revisao, variacoes a partir de revisao anterior,
duplicacao direta, independencia, colisao de ID, midia ausente, mudanca de
allowlist, modelo de outro projeto, envio a Fila de Produção (Reels, YouTube
horizontal, carrossel 4:5 e Motion vertical), reexportacao isolada, FFprobe sem
audio, aprovacao na Revisao, ZIP conferido e recuperacao apos reinicio.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile

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
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _create_color_video(path, color, duration_s=2.5, width=1280, height=720, fps=30):
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


def _sha256(path):
    return render_local.sha256_file(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prova HTTP de modelos e variacoes em serie')
    parser.add_argument('--port', type=int, default=8804)
    args = parser.parse_args(argv)

    src = 'ci-tpl-src-work'
    mth = 'ci-tpl-mth-work'
    variations = [f'ci-tpl-var-{i}' for i in (1, 2, 3)]
    dup = 'ci-tpl-dup-work'
    all_works = [src, mth, dup] + variations
    pfiles = []
    tpl_ids = []
    creation_keys = []
    for wid in all_works:
        shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', wid), ignore_errors=True)

    httpd, studio = video_studio.make_server(ROOT, args.port)
    srv_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    srv_thread.start()
    base = f'http://127.0.0.1:{args.port}'
    post_json = lambda u, b: _http_json(u, 'POST', b, origin=base)

    def make_project(wid, theme):
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
        pfiles.append(studio.confine(proj_res['path']))
        return proj_res['path']

    def seed_work(wid, theme, tpl, color):
        proj = make_project(wid, theme)
        created = post_json(f'{base}/api/works/create', {
            'id': wid, 'name': f'CI Templates {wid}', 'project': proj, 'template': tpl,
        })
        clip_rel = f'.workspace/studio/works/{wid}/media/ci-clip.mp4'
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
        post_json(f'{base}/api/works/editorial/save', {
            'workId': wid, 'briefing': {'hook': f'Gancho {wid}', 'cta': 'Conheca o sistema'},
        })
        return proj

    try:
        proj_ms = seed_work(src, 'marca-salao', 'marca-salao', 'blue')
        seed_work(mth, 'multitrack-hub', 'multitrack-hub', 'green')

        # 1. Salvar modelo (rev-1), editar origem, salvar rev-2
        s1 = post_json(f'{base}/api/templates/save', {'workId': src, 'name': 'Modelo agenda CI'})
        tpl = s1['template']['id']
        tpl_ids.append(tpl)
        assert s1['revisionId'] == 'rev-1'
        opened = _http_json(f'{base}/api/works/open?id={src}')
        vreq = opened['videoRequest']
        original_title = vreq['title']
        vreq['title'] = 'Titulo da revisao 2'
        post_json(f'{base}/api/works/save', {'workId': src, 'videoRequest': vreq})
        s2 = post_json(f'{base}/api/templates/save', {'workId': src, 'templateId': tpl, 'label': 'Rev 2'})
        assert s2['revisionId'] == 'rev-2'

        # 2. Plano + criacao de 3 variacoes a partir da revisao ANTERIOR
        rows = [
            {'id': variations[0], 'name': 'Agenda semana 42', 'title': 'Agenda semana 42', 'hook': 'Sua agenda cheia'},
            {'id': variations[1], 'name': 'Agenda semana 43', 'title': 'Agenda semana 43'},
            {'id': variations[2], 'name': 'Agenda semana 44'},
        ]
        plan = post_json(f'{base}/api/templates/plan', {'templateId': tpl, 'revisionId': 'rev-1', 'rows': rows})
        assert all(p['ok'] for p in plan['plans']), plan
        for wid in variations:
            assert not os.path.exists(os.path.join(ROOT, '.workspace', 'studio', 'works', wid))
        key = f'ci-tpl-key-{int(time.time())}'
        creation_keys.append(key)
        created = post_json(f'{base}/api/templates/create', {
            'templateId': tpl, 'revisionId': 'rev-1', 'rows': rows, 'idempotencyKey': key,
        })
        assert all(c['status'] == 'created' for c in created['creations']), created
        again = post_json(f'{base}/api/templates/create', {
            'templateId': tpl, 'revisionId': 'rev-1', 'rows': rows, 'idempotencyKey': key,
        })
        assert again['deduplicated'] is True

        # Variacoes herdam a rev-1 (titulo original), nao a rev-2
        v1 = _http_json(f'{base}/api/works/open?id={variations[0]}')
        assert v1['videoRequest']['title'] == 'Agenda semana 42'
        v3 = _http_json(f'{base}/api/works/open?id={variations[2]}')
        assert v3['videoRequest']['title'] == original_title, (v3['videoRequest']['title'], original_title)
        assert v1['videoRequest']['scenes'][0].get('sourceStartMs') == 250
        assert v1['videoRequest']['scenes'][0]['framingByProfile']['instagram-reels-video']['zoomPercent'] == 140
        assert v1['review']['editorial']['briefing']['hook'] == 'Sua agenda cheia'
        assert v3['review']['editorial']['briefing']['hook'] == f'Gancho {src}'

        # 3. Duplicacao direta da Multitrack Hub
        d = post_json(f'{base}/api/works/duplicate', {'workId': mth, 'newId': dup, 'name': 'Copia MTH'})
        assert d['work']['origin']['kind'] == 'duplicate'

        # 4. Independencia: editar texto de uma variacao nao afeta modelo/outras/origem
        v2 = _http_json(f'{base}/api/works/open?id={variations[1]}')
        v2req = v2['videoRequest']
        v2req['title'] = 'Editado so na variacao 2'
        post_json(f'{base}/api/works/save', {'workId': variations[1], 'videoRequest': v2req})
        assert _http_json(f'{base}/api/works/open?id={variations[0]}')['videoRequest']['title'] == 'Agenda semana 42'
        assert _http_json(f'{base}/api/works/open?id={src}')['videoRequest']['title'] == 'Titulo da revisao 2'
        snap_check = _http_json(f'{base}/api/templates/get?id={tpl}')
        assert len(snap_check['template']['revisions']) == 2

        # 5. Casos negativos
        col_key = f'ci-tpl-col-{int(time.time())}'
        creation_keys.append(col_key)
        col = post_json(f'{base}/api/templates/create', {
            'templateId': tpl, 'revisionId': 'rev-1',
            'rows': [{'id': src, 'name': 'Colisao'}], 'idempotencyKey': col_key,
        })
        assert col['creations'][0]['error']['code'] == 'WORK_ID_COLLISION'

        tpl_dir = os.path.join(ROOT, '.workspace', 'studio', 'templates', tpl, 'revisions', 'rev-1')
        with open(os.path.join(tpl_dir, 'snapshot.json'), 'r', encoding='utf-8') as f:
            snap = json.load(f)
        victim = os.path.join(tpl_dir, 'media', snap['media'][0]['file'])
        os.replace(victim, victim + '.bak')
        try:
            miss_plan = post_json(f'{base}/api/templates/plan', {
                'templateId': tpl, 'revisionId': 'rev-1', 'rows': [{'id': 'ci-tpl-missing'}],
            })
            assert any(c['code'] == 'TEMPLATE_MEDIA_MISSING' for c in miss_plan['plans'][0]['conditions'])
        finally:
            os.replace(victim + '.bak', victim)

        proj_abs = studio.confine(proj_ms)
        with open(proj_abs, 'r', encoding='utf-8') as f:
            pdoc = json.load(f)
        keep = list(pdoc['outputProfiles'])
        pdoc['outputProfiles'] = ['instagram-feed-image-square']
        with open(proj_abs, 'w', encoding='utf-8') as f:
            json.dump(pdoc, f, ensure_ascii=False, indent=2)
        try:
            allow_plan = post_json(f'{base}/api/templates/plan', {
                'templateId': tpl, 'revisionId': 'rev-1', 'rows': [{'id': 'ci-tpl-allow'}],
            })
            assert allow_plan['profileAdjustments'], allow_plan
        finally:
            pdoc['outputProfiles'] = keep
            with open(proj_abs, 'w', encoding='utf-8') as f:
                json.dump(pdoc, f, ensure_ascii=False, indent=2)

        try:
            post_json(f'{base}/api/templates/save', {'workId': mth, 'templateId': tpl})
            raise AssertionError('modelo de outro projeto aceito')
        except urllib.error.HTTPError as exc:
            assert exc.code == 409, exc.code

        # 6. Enviar variacoes a Fila de Produção (lote misto)
        items = [
            {'workId': variations[0], 'modality': 'video', 'profileId': 'instagram-reels-video'},
            {'workId': variations[0], 'modality': 'video', 'profileId': 'youtube-video-horizontal'},
            {'workId': variations[0], 'modality': 'motion', 'profileId': 'instagram-reels-video'},
            {'workId': variations[1], 'modality': 'carousel', 'profileId': 'instagram-feed-image-portrait'},
        ]
        qkey = f'ci-tpl-queue-{int(time.time())}'
        e1 = post_json(f'{base}/api/queue/enqueue', {'items': items, 'idempotencyKey': qkey, 'label': 'CI Modelos'})
        batch_id = e1['batch']['batchId']
        deadline = time.monotonic() + 300.0
        batch = None
        while time.monotonic() < deadline:
            batch = _http_json(f'{base}/api/queue/batch?id={batch_id}')['batch']
            c = batch['counts']
            if c['queued'] == 0 and c['running'] == 0:
                break
            time.sleep(0.4)
        assert batch and batch['counts']['completed'] == 4, batch

        # 7. FFprobe: geometria, 30 fps, zero audio; carrossel 1080x1350
        ffprobe = build_video.get_ffprobe()
        promoted = {}
        for it in batch['items']:
            man_abs = studio.confine_workspace(it['deliveryManifestPath'])
            with open(man_abs, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            if it['modality'] == 'carousel':
                assert manifest['geometry'] == {'width': 1080, 'height': 1350}
                for card in manifest['cards']:
                    cabs = studio.confine_workspace(card['path'])
                    assert _sha256(cabs) == card['sha256']
                    probe = subprocess.run([ffprobe, '-v', 'error', '-show_streams', '-of', 'json', cabs],
                                           capture_output=True, text=True, check=True)
                    st = json.loads(probe.stdout)['streams'][0]
                    assert (st['width'], st['height']) == (1080, 1350)
            else:
                v_art = manifest['artifacts']['video']
                v_abs = studio.confine_workspace(v_art['path'])
                assert _sha256(v_abs) == v_art['sha256']
                probe = subprocess.run([ffprobe, '-v', 'error', '-show_streams', '-of', 'json', v_abs],
                                       capture_output=True, text=True, check=True)
                streams = json.loads(probe.stdout)['streams']
                assert len([s for s in streams if s.get('codec_type') == 'audio']) == 0
                vs = next(s for s in streams if s.get('codec_type') == 'video')
                assert vs['r_frame_rate'] == '30/1'
                expected = (1920, 1080) if it['profileId'] == 'youtube-video-horizontal' else (1080, 1920)
                assert (vs['width'], vs['height']) == expected
                promoted[(it['modality'], it['profileId'])] = v_art['sha256']
                if it['modality'] == 'video' and it['profileId'] == 'instagram-reels-video':
                    # Quadro medio do trecho recortado: a fonte ficticia e azul
                    ffmpeg = build_video.get_ffmpeg()
                    raw = subprocess.run(
                        [ffmpeg, '-v', 'error', '-i', v_abs, '-vf', 'select=eq(n\\,15),scale=1:1',
                         '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                        capture_output=True, check=True, timeout=60,
                    ).stdout
                    r, g, b = raw[0], raw[1], raw[2]
                    assert b > r and b > g, f'quadro do trecho nao e azul: {(r, g, b)}'

        # 8. Reexportacao isolada do horizontal preserva os demais perfis
        v1_open = _http_json(f'{base}/api/works/open?id={variations[0]}')
        export = post_json(f'{base}/api/export', {
            'request': v1_open['videoRequest'],
            'outputDir': v1_open['work']['paths']['videoDeliveryDir'],
            'profile': 'youtube-video-horizontal',
            'kind': 'video',
            'workId': variations[0],
        })
        job_id = export['jobId']
        deadline = time.monotonic() + 180.0
        status = None
        while time.monotonic() < deadline:
            status = _http_json(f'{base}/api/export/status?job={job_id}')
            if status.get('status') in ('completed', 'failed'):
                break
            time.sleep(0.4)
        assert status and status['status'] == 'completed', status
        after = _http_json(f"{base}/api/delivery?dir={v1_open['work']['paths']['videoDeliveryDir']}")
        for entry in after['index']['profiles']:
            if entry['profileId'] == 'instagram-reels-video':
                man_rel = entry['lastValidDelivery']['deliveryManifest']
                with open(studio.confine_workspace(man_rel), 'r', encoding='utf-8') as f:
                    reels_man = json.load(f)
                assert reels_man['artifacts']['video']['sha256'] == promoted[('video', 'instagram-reels-video')]

        # 9. Aprovacao na Revisao + ZIP conferido (manifesto, hashes, versao de origem)
        rev = _http_json(f'{base}/api/works/review?id={variations[0]}')
        reels = next(p for p in rev['pieces'] if p['pieceKey'] == 'video:instagram-reels-video')
        post_json(f'{base}/api/works/review/decide', {
            'workId': variations[0], 'targetType': 'piece', 'modality': 'video',
            'profileId': 'instagram-reels-video', 'decision': 'approved_for_local_delivery',
            'expectedVersionId': reels['deliveryVersionId'], 'note': 'ci-tpl',
        })
        pkg = post_json(f'{base}/api/works/package', {
            'workId': variations[0],
            'pieces': [{'modality': 'video', 'profileId': 'instagram-reels-video',
                         'expectedVersionId': reels['deliveryVersionId']}],
        })
        pkg_info = pkg.get('packageDelivery') or pkg
        assert pkg_info.get('available'), pkg
        zip_rel = pkg_info['lastValidDelivery']['zipPath']
        zip_abs = studio.confine_workspace(zip_rel)
        assert _sha256(zip_abs) == pkg_info['lastValidDelivery']['zipSha256']
        pkg_dir = os.path.dirname(zip_abs)
        with open(os.path.join(pkg_dir, 'package-manifest.json'), 'r', encoding='utf-8') as f:
            pkg_manifest = json.load(f)
        with zipfile.ZipFile(zip_abs, 'r') as zf:
            for entry in pkg_manifest['files']:
                data = zf.read(entry['archivePath'])
                assert hashlib.sha256(data).hexdigest() == entry['sha256'], entry['archivePath']
        piece_meta = next(p for p in pkg_manifest['pieces'] if p.get('profileId') == 'instagram-reels-video' and p.get('modality') == 'video')
        assert piece_meta.get('deliveryVersionId') == reels['deliveryVersionId']

        # 10. Recuperacao apos reinicio do servidor
        studio.close()
        httpd.shutdown()
        httpd.server_close()
        httpd2, studio2 = video_studio.make_server(ROOT, args.port)
        t2 = threading.Thread(target=httpd2.serve_forever, daemon=True)
        t2.start()
        try:
            templates = _http_json(f'{base}/api/templates')['templates']
            assert tpl in [t['id'] for t in templates]
            reopened = _http_json(f'{base}/api/works/open?id={variations[0]}')
            assert reopened['videoRequest']['title'] == 'Agenda semana 42'
            assert reopened['review']['pieces']
            queue_after = _http_json(f'{base}/api/queue/batch?id={batch_id}')['batch']
            assert queue_after['counts']['completed'] == 4
        finally:
            studio2.close()
            httpd2.shutdown()
            httpd2.server_close()

        print('studio-work-templates CI HTTP proof ok')
        print(json.dumps({
            'templateId': tpl,
            'revisions': ['rev-1', 'rev-2'],
            'variations': variations,
            'duplicate': dup,
            'batchId': batch_id,
            'counts': batch['counts'],
            'zipSha256': pkg_info['lastValidDelivery']['zipSha256'],
        }, ensure_ascii=False))
        return 0
    finally:
        try:
            studio.close()
        except Exception:
            pass
        for wid in all_works:
            shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', wid), ignore_errors=True)
        for tid in tpl_ids:
            shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'templates', tid), ignore_errors=True)
        for key in creation_keys:
            p = os.path.join(ROOT, '.workspace', 'studio', 'template-creations', f'{key}.json')
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        for pf in pfiles:
            if os.path.exists(pf):
                try:
                    os.remove(pf)
                except OSError:
                    pass


if __name__ == '__main__':
    raise SystemExit(main())