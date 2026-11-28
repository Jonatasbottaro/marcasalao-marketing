"""Prova HTTP da biblioteca de midia por trabalho no Studio local (CI e local).

Sobe o Studio em 127.0.0.1, executa o fluxo completo com dados ficticios e
provedor simulado (importar -> referencia -> pedido -> gerar -> comparar ->
selecionar -> aplicar -> exportar video/carrossel -> revisar -> ZIP), confere
AssetManifest, FFprobe sem audio, revisao localizada, midia compartilhada,
falhas e recuperacao apos reinicio do servidor. Ao final remove o trabalho de
prova e encerra o processo.

Uso: python tools/ci_media_library_proof.py [--port 8797] [--keep]
Requer a ponte TypeScript compilada (platform/dist) e FFmpeg/FFprobe.
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
import image_adapters  # noqa: E402
import render_local  # noqa: E402

WORK_ID = 'ci-media-library-work'


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prova HTTP da biblioteca de midia do Studio')
    parser.add_argument('--port', type=int, default=8797)
    parser.add_argument('--keep', action='store_true', help='Nao remove o trabalho de prova ao final')
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

    def png(prompt, w, h):
        return image_adapters.SimulatorImageAdapter().generate(prompt, {'width': w, 'height': h})['bytes']

    try:
        wait_ready()
        wk = call('/api/works/create', {
            'id': WORK_ID, 'name': 'CI Biblioteca de Midia',
            'project': 'platform/examples/projects/marca-salao-social.project.json',
            'template': 'marca-salao',
        })
        assert wk['ok']
        paths = wk['work']['paths']

        creative = {
            'hookOptions': [{'id': 'hook-1', 'text': 'Agenda organizada', 'angle': 'clareza'}],
            'selectedHookId': 'hook-1',
            'scriptSummary': 'Prova CI ficticia da biblioteca de midia.',
            'videoScenes': [
                {'id': 'cena-abertura', 'objective': 'Abertura', 'narrativeFunction': 'hook',
                 'durationMs': 4000, 'titleOverlay': 'Abertura', 'caption': 'Legenda 1',
                 'narration': 'Narracao 1', 'requiredMediaDescriptor': 'Ilustracao ficticia de abertura com agenda',
                 'motionIntent': 'none'},
                {'id': 'cena-prova', 'objective': 'Prova', 'narrativeFunction': 'demonstration',
                 'durationMs': 4000, 'titleOverlay': 'Prova', 'caption': 'Legenda 2',
                 'narration': 'Narracao 2', 'requiredMediaDescriptor': 'Captura ficticia da agenda',
                 'mediaId': 'agenda', 'motionIntent': 'none'},
            ],
            'carouselCards': [
                {'id': 'capa', 'role': 'cover', 'title': 'Capa', 'body': 'Sub', 'requiredMediaDescriptor': 'Imagem ficticia de capa'},
                {'id': 'conteudo', 'role': 'content', 'title': 'Conteudo', 'body': 'Texto', 'mediaId': 'agenda'},
                {'id': 'fechamento', 'role': 'cta', 'title': 'Saiba mais', 'body': 'Confira'},
            ],
            'channelCopies': [],
        }
        call('/api/works/planning/save', {'workId': WORK_ID, 'creative': creative, 'markCreativeChecked': True})

        # 1. Importacao manual (sem rede, sem chave)
        ext_png = png('arte externa ficticia CI', 1080, 1920)
        imp = call('/api/works/media/import', {
            'workId': WORK_ID, 'dataBase64': base64.b64encode(ext_png).decode(),
            'fileName': 'externa-ci.png', 'origin': 'external-tool',
            'originDetail': {'tool': 'Ferramenta externa ficticia'}, 'license': 'owned-synthetic',
        })
        assert imp['ok']

        # 2. Referencia visual (VisualAnchor v1)
        anchor = call('/api/works/media/anchor', {
            'workId': WORK_ID, 'title': 'Referencia CI',
            'assetId': imp['assetId'], 'versionId': imp['versionId'],
            'direction': 'Ilustracao ficticia clara com agenda em destaque',
            'mustInclude': ['agenda'], 'mustAvoid': ['dados pessoais'],
        })
        assert anchor['ok']

        # 3. Pedido visual derivado do descritor, com referencia enviada ao provedor
        req = call('/api/works/media/request/create', {
            'workId': WORK_ID, 'targetKind': 'video_scene', 'targetId': 'cena-abertura',
            'anchorId': anchor['anchorId'], 'sendAnchorToProvider': True,
        })
        assert req['ok']
        rid = req['requestId']
        entry = next(r for r in req['overview']['mediaLibrary']['requests'] if r['request']['id'] == rid)
        assert entry['request']['geometry'] == {'width': 1080, 'height': 1920}
        assert 'Direcao visual de referencia' in entry['providerTextPreview']

        # 4. Importar outra opcao e gerar candidato pelo simulador (uma chamada confirmada)
        imp2 = call('/api/works/media/import', {
            'workId': WORK_ID, 'dataBase64': base64.b64encode(png('opcao manual CI', 1080, 1920)).decode(),
            'fileName': 'opcao-ci.png', 'origin': 'imported-manual', 'requestId': rid,
        })
        assert imp2['ok'] and imp2['candidateId']
        gen = call('/api/works/media/generate', {
            'workId': WORK_ID, 'requestId': rid, 'provider': 'simulator', 'confirm': True,
        })
        assert gen['ok']
        lib = call('/api/works/media-library?id=' + WORK_ID)
        entry = next(r for r in lib['mediaLibrary']['requests'] if r['request']['id'] == rid)
        assert len(entry['candidates']) == 2
        assert all(not c['stale'] for c in entry['candidates'])

        # 5. Gemini sem chave: 503 com diagnostico, sem candidato
        try:
            call('/api/works/media/generate', {'workId': WORK_ID, 'requestId': rid, 'provider': 'google-gemini', 'confirm': True})
            raise AssertionError('Gemini sem chave deveria falhar')
        except RuntimeError as exc:
            assert 'HTTP 503' in str(exc) and 'IMAGE_PROVIDER_NO_CREDENTIAL' in str(exc), str(exc)

        # 6. Prompt revisado marca candidatos anteriores
        upd = call('/api/works/media/request/update', {'workId': WORK_ID, 'requestId': rid, 'prompt': 'Prompt CI revisado'})
        entry = next(r for r in upd['overview']['mediaLibrary']['requests'] if r['request']['id'] == rid)
        assert all(c['stale'] for c in entry['candidates'])

        # 7. Selecionar candidato e aplicar pela previa de diferencas
        sel = call('/api/works/media/select', {
            'workId': WORK_ID, 'assetId': gen['assetId'], 'versionId': gen['versionId'],
            'requestId': rid, 'candidateId': gen['candidateId'],
        })
        assert sel['ok'] and sel['targets'][0]['viaPlanning']
        diff = call('/api/works/planning/diff', {'workId': WORK_ID})
        assert diff['editorsDiff']['video']['readyToApply']
        applied = call('/api/works/planning/apply', {'workId': WORK_ID, 'applyVideo': True, 'applyCarousel': True})
        assert applied['applied']['video']['status'] == 'applied'
        assert applied['applied']['carousel']['status'] == 'applied'
        opened = applied['workData']
        vreq = opened['videoRequest']
        media = next(m for m in vreq['media'] if m['id'] == gen['assetId'])
        assert media['origin'] == 'generated-simulator' and media['license'] == 'owned-synthetic'

        # 8. Exportar video e carrossel; AssetManifest materializa a versao
        wait_export({'workId': WORK_ID, 'kind': 'video', 'profile': 'instagram-reels-video',
                     'request': vreq, 'outputDir': paths['videoDeliveryDir']})
        wait_export({'workId': WORK_ID, 'kind': 'carousel',
                     'request': opened['carouselRequest'], 'outputDir': paths['carouselDeliveryDir']})
        manifest = json.load(open(os.path.join(ROOT, paths['videoDeliveryDir'], 'instagram-reels-video', 'delivery-manifest.json'), encoding='utf-8'))
        am = manifest['artifacts']['assetManifest']
        inv = json.load(open(os.path.join(ROOT, am['path']), encoding='utf-8'))
        gen_assets = [a for a in inv['assets'] if a['origin'] == 'generated-simulator']
        assert gen_assets, inv['assets']
        lib = call('/api/works/media-library?id=' + WORK_ID)
        asset = next(a for a in lib['mediaLibrary']['assets'] if a['id'] == gen['assetId'])
        version = next(v for v in asset['versions'] if v['versionId'] == gen['versionId'])
        assert gen_assets[0]['sha256'] == version['sha256']

        # 9. FFprobe: zero faixas de audio
        mp4 = os.path.join(ROOT, manifest['artifacts']['video']['path'])
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json',
                                build_video._probe_path(render_local.fs_path(mp4))],
                               capture_output=True, text=True, timeout=60)
        streams = json.loads(probe.stdout)['streams']
        assert not any(s['codec_type'] == 'audio' for s in streams), streams

        # 10. Revisao localizada: trocar imagem de card afeta so o carrossel
        rev_before = call('/api/works/review?id=' + WORK_ID)
        st_before = {p['pieceKey']: p['status'] for p in rev_before['pieces']}
        assert st_before['video:instagram-reels-video'] == 'pending_review'
        imp3 = call('/api/works/media/import', {
            'workId': WORK_ID, 'dataBase64': base64.b64encode(png('nova capa CI', 1080, 1080)).decode(),
            'fileName': 'capa-ci.png', 'origin': 'imported-manual',
        })
        call('/api/works/media/select', {
            'workId': WORK_ID, 'assetId': imp3['assetId'], 'versionId': imp3['versionId'],
            'targetKind': 'carousel_card', 'targetId': 'capa',
        })
        call('/api/works/planning/apply', {'workId': WORK_ID, 'applyCarousel': True,
                                           'preserveSceneIds': ['cena-abertura', 'cena-prova']})
        rev_after = call('/api/works/review?id=' + WORK_ID)
        st_after = {p['pieceKey']: p['status'] for p in rev_after['pieces']}
        assert st_after['carousel:instagram-feed-image-square'] == 'draft_outdated'
        assert st_after['video:instagram-reels-video'] == 'pending_review'

        # 11. Falha de conteudo invalido preserva a biblioteca
        try:
            call('/api/works/media/import', {
                'workId': WORK_ID, 'dataBase64': base64.b64encode(b'nao e imagem').decode(),
                'fileName': 'invalida.png', 'origin': 'imported-manual',
            })
            raise AssertionError('import invalido deveria falhar')
        except RuntimeError as exc:
            assert 'HTTP 400' in str(exc), str(exc)

        # 12. Aprovar pecas atuais e gerar ZIP
        rev = call('/api/works/review?id=' + WORK_ID)
        approved = []
        for piece in rev['pieces']:
            if piece['status'] == 'pending_review':
                call('/api/works/review/decide', {
                    'workId': WORK_ID, 'targetType': 'piece', 'modality': piece['modality'],
                    'profileId': piece['profileId'], 'decision': 'approved_for_local_delivery',
                    'expectedVersionId': piece.get('deliveryVersionId'),
                })
                approved.append({'modality': piece['modality'], 'profileId': piece['profileId'],
                                 'expectedVersionId': piece.get('deliveryVersionId')})
        assert approved, 'nenhuma peca pendente para aprovar'
        pkg = call('/api/works/package', {'workId': WORK_ID, 'pieces': approved})
        assert pkg['packageDelivery']['available'], pkg
        zip_abs = os.path.join(ROOT, paths['packageDeliveryDir'], 'delivery-package.zip')
        zdata = open(zip_abs, 'rb').read()
        zsha = hashlib.sha256(zdata).hexdigest()
        assert zipfile.ZipFile(zip_abs).testzip() is None

        # 13. Midia compartilhada: atualizar vinculos identifica todas as pecas
        imp4 = call('/api/works/media/import', {
            'workId': WORK_ID, 'dataBase64': base64.b64encode(png('nova agenda CI', 540, 960)).decode(),
            'fileName': 'agenda-ci.png', 'origin': 'imported-manual', 'assetId': 'agenda',
        })
        shared = call('/api/works/media/select', {
            'workId': WORK_ID, 'assetId': 'agenda', 'versionId': imp4['versionId'],
            'updateLinkedTargets': True,
        })
        modalities = {c['modality'] for c in shared['consumers']}
        assert {'video', 'carousel'} <= modalities, shared['consumers']

        # 14. Reinicio do servidor restaura pedidos, arquivos, referencias e selecoes
        proc.terminate()
        proc.wait(timeout=30)
        proc = subprocess.Popen(
            [sys.executable, os.path.join(ROOT, 'tools', 'video_studio.py'), '--port', str(args.port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        wait_ready()
        lib2 = call('/api/works/media-library?id=' + WORK_ID)
        assert lib2['initializedOnDisk']
        entry2 = next(r for r in lib2['mediaLibrary']['requests'] if r['request']['id'] == rid)
        assert entry2['selectedCandidateId'] == gen['candidateId']
        assert len(entry2['candidates']) == 2
        assert any(a['anchor']['id'] == anchor['anchorId'] for a in lib2['mediaLibrary']['anchors'])
        assert lib2['mediaLibrary']['selections']
        pkg2 = call('/api/works/package?id=' + WORK_ID)
        assert pkg2['available']
        zdata2 = open(zip_abs, 'rb').read()
        assert hashlib.sha256(zdata2).hexdigest() == zsha, 'ZIP valido anterior deve ser preservado'

        print('media library CI HTTP proof ok: import, anchor, request, simulator, gemini-no-key, stale, select+apply, export, asset-manifest, ffprobe-no-audio, localized review, shared media, invalid file, zip, restart recovery')
        print(json.dumps({'workId': WORK_ID, 'zipSha256': zsha, 'zipBytes': len(zdata)}, ensure_ascii=False))
        return 0
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=30)
        except Exception:
            proc.kill()
        if not args.keep:
            shutil.rmtree(render_local.fs_path(os.path.join(ROOT, '.workspace', 'studio', 'works', WORK_ID), force=True), ignore_errors=True)


if __name__ == '__main__':
    raise SystemExit(main())