"""Testes da fila local persistente de producao em lote no Video Studio."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
TOOLS = os.path.join(ROOT, 'tools')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import build_video
import make_agenda_media
import render_local
import studio_queue
import studio_review
import video_studio


REQUIRE_RENDER = os.environ.get('REQUIRE_RENDER') == '1'


def _tools_available():
    try:
        build_video.get_ffmpeg()
        build_video.get_ffprobe()
        return True
    except build_video.DeliveryError:
        return False


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


def _wait_batch_settled(queue, batch_id, timeout=180.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        batch = queue.get_batch(batch_id)
        counts = batch['counts']
        if counts['queued'] == 0 and counts['running'] == 0:
            return batch
        time.sleep(0.25)
    raise TimeoutError(f'batch {batch_id} did not settle within {timeout}s')


class TestStudioQueue(unittest.TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp(prefix='t_studio_queue_', dir=os.path.join(ROOT, '.workspace', 'tmp'))
        self.work_ids = []
        self.project_files = []
        self.studios = []

    def tearDown(self):
        for st in self.studios:
            try:
                st.close()
            except Exception:
                pass
        for wid in self.work_ids:
            shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', wid), ignore_errors=True)
        for pfile in self.project_files:
            if os.path.exists(pfile):
                try:
                    os.remove(pfile)
                except OSError:
                    pass
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def _make_studio(self, auto_start=True):
        db_path = os.path.join(self.tmp_root, 'queue.sqlite')
        st = video_studio.Studio(ROOT, 0, auto_start_queue=False)
        st.queue = studio_queue.StudioQueue(st, auto_start=auto_start, db_path=db_path)
        self.studios.append(st)
        return st

    def _seed_work(self, studio, work_id, template, suffix='v1'):
        self.work_ids.append(work_id)
        shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', work_id), ignore_errors=True)
        proj_id = f'tq-{work_id}'
        proj_res = studio.create_project({
            'schemaVersion': 1,
            'id': proj_id,
            'name': f'Projeto {work_id}',
            'locale': 'pt-BR',
            'timezone': 'America/Sao_Paulo',
            'brandTheme': 'marca-salao' if template == 'marca-salao' else 'multitrack-hub',
            'assetRoot': f'.workspace/studio/works/{work_id}/media',
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
        project = proj_res['path']
        self.project_files.append(studio.confine(project))
        opened = studio.create_work({
            'id': work_id,
            'name': f'Trabalho {work_id}',
            'project': project,
            'template': template,
        })
        work = opened['work']
        media_dir = studio.confine(work['paths']['mediaDir'])
        clip_rel = f"{work['paths']['mediaDir']}/clip-{suffix}.mp4"
        clip_abs = studio.confine(clip_rel)
        if _tools_available():
            _create_color_video(clip_abs, 'blue' if template == 'marca-salao' else 'green', duration_s=2.5)
        else:
            os.makedirs(media_dir, exist_ok=True)
            with open(clip_abs, 'wb') as f:
                f.write(b'fake-mp4-bytes-' + work_id.encode('utf-8'))

        vreq = json.loads(json.dumps(opened['videoRequest']))
        vreq['media'] = list(vreq.get('media') or []) + [
            {'id': 'clip-1', 'type': 'video', 'path': clip_rel, 'origin': 'synthetic-demo', 'license': 'owned-synthetic'}
        ]
        vreq['scenes'][0]['mediaId'] = 'clip-1'
        vreq['scenes'][0]['sourceStartMs'] = 300
        vreq['scenes'][0]['durationMs'] = 1200
        vreq['scenes'][0]['framingByProfile'] = {
            'instagram-reels-video': {'centerX': 0.75, 'centerY': 0.5, 'zoomPercent': 140},
            'youtube-video-horizontal': {'centerX': 0.5, 'centerY': 0.5, 'zoomPercent': 100},
        }
        vreq['profiles'] = ['instagram-reels-video', 'youtube-video-horizontal']

        creq = json.loads(json.dumps(opened['carouselRequest']))
        creq['profile'] = 'instagram-feed-image-portrait'

        mplan = json.loads(json.dumps(opened['motionPlan']))
        for eff in mplan.get('effects') or []:
            if eff.get('sceneId') == vreq['scenes'][0]['id']:
                eff['startMs'] = 0
                eff['endMs'] = min(int(eff.get('endMs') or 1000), 1000)
        studio.save_work({
            'workId': work_id,
            'videoRequest': vreq,
            'carouselRequest': creq,
            'motionPlan': mplan,
        })
        return studio.open_work(work_id)

    def test_01_schema_idempotency_and_unavailable_options(self):
        studio = self._make_studio(auto_start=False)
        self.assertEqual(studio.queue.schema_version(), studio_queue.QUEUE_SCHEMA_VERSION)
        w1 = f'tq-ms-{os.getpid()}'
        w2 = f'tq-mh-{os.getpid()}'
        self._seed_work(studio, w1, 'marca-salao')
        self._seed_work(studio, w2, 'multitrack-hub')

        plan = studio.queue.plan_batch([w1, w2])
        self.assertEqual(len(plan['works']), 2)
        # Motion em youtube-video-horizontal deve aparecer indisponivel com motivo claro
        ms_opts = plan['works'][0]['options']
        yt_motion = next(
            (o for o in ms_opts if o['modality'] == 'motion' and o['profileId'] == 'youtube-video-horizontal'),
            None,
        )
        self.assertIsNotNone(yt_motion)
        self.assertFalse(yt_motion['available'])
        self.assertIn('9:16', yt_motion['unavailableReason'])

        items = [
            {'workId': w1, 'modality': 'video', 'profileId': 'instagram-reels-video'},
            {'workId': w1, 'modality': 'carousel', 'profileId': 'instagram-feed-image-portrait'},
        ]
        b1 = studio.queue.enqueue_batch(items, idempotency_key='idem-test-01', label='Lote Idempotente')
        self.assertFalse(b1['deduplicated'])
        b2 = studio.queue.enqueue_batch(items, idempotency_key='idem-test-01', label='Lote Idempotente')
        self.assertTrue(b2['deduplicated'])
        self.assertEqual(b1['batchId'], b2['batchId'])
        self.assertEqual(len(b1['items']), len(b2['items']))

        # Cancelar item pendente exclui da execucao
        cancelled = studio.queue.cancel_item(b1['items'][1]['itemId'])
        self.assertEqual(cancelled['status'], 'cancelled')
        with self.assertRaises(ValueError):
            studio.queue.cancel_item(b1['items'][1]['itemId'])

    def test_02_atomic_claim_and_destination_lock(self):
        studio = self._make_studio(auto_start=False)
        w1 = f'tq-race-{os.getpid()}'
        self._seed_work(studio, w1, 'marca-salao')
        batch = studio.queue.enqueue_batch([
            {'workId': w1, 'modality': 'video', 'profileId': 'instagram-reels-video'},
        ])
        item_id = batch['items'][0]['itemId']

        # Duas tentativas concorrentes de assumir o mesmo item
        claimed = []
        barrier = threading.Barrier(2)

        def racer():
            barrier.wait()
            it, _ = studio.queue._claim_next_item()
            if it is not None:
                claimed.append(it['item_id'])

        t1 = threading.Thread(target=racer)
        t2 = threading.Thread(target=racer)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assertEqual(claimed, [item_id])

        # Concorrencia pelo mesmo destino bloqueia exportacao avulsa
        out_dir = batch['items'][0]['outputDir']
        studio.queue._set_active_destination(out_dir, item_id, 'att-fake')
        try:
            with self.assertRaises(ValueError):
                studio.start_export({}, out_dir, profile='instagram-reels-video', work_id=w1)
        finally:
            studio.queue._set_active_destination(None)

    def test_03_mixed_batch_render_ffprobe_review_zip_and_divergence(self):
        if not REQUIRE_RENDER and not _tools_available():
            self.skipTest('FFmpeg/FFprobe indisponivel')
        studio = self._make_studio(auto_start=True)
        w1 = f'tq-mix-ms-{os.getpid()}'
        w2 = f'tq-mix-mh-{os.getpid()}'
        self._seed_work(studio, w1, 'marca-salao')
        self._seed_work(studio, w2, 'multitrack-hub')

        batch = studio.queue.enqueue_batch([
            {'workId': w1, 'modality': 'video', 'profileId': 'instagram-reels-video'},
            {'workId': w1, 'modality': 'video', 'profileId': 'youtube-video-horizontal'},
            {'workId': w1, 'modality': 'carousel', 'profileId': 'instagram-feed-image-portrait'},
            {'workId': w1, 'modality': 'motion', 'profileId': 'instagram-reels-video'},
            {'workId': w2, 'modality': 'video', 'profileId': 'instagram-reels-video'},
            {'workId': w2, 'modality': 'video', 'profileId': 'youtube-video-horizontal'},
        ], idempotency_key=f'mix-{os.getpid()}')

        # Cancela o ultimo item antes de iniciar
        cancelled_id = batch['items'][-1]['itemId']
        studio.queue.cancel_item(cancelled_id)

        settled = _wait_batch_settled(studio.queue, batch['batchId'], timeout=240.0)
        failed_diag = [(i['modality'], i['profileId'], i['errorMessage']) for i in settled['items'] if i['status'] == 'failed']
        self.assertEqual(settled['counts']['failed'], 0, f'failed items: {failed_diag}')
        self.assertEqual(settled['counts']['completed'], 5, f'settled: {settled["counts"]}')
        self.assertEqual(settled['counts']['cancelled'], 1)

        # Confere FFprobe nos MP4s promovidos (geometria, 30 fps, 0 audio)
        ffprobe = build_video.get_ffprobe()
        for it in settled['items']:
            if it['status'] != 'completed':
                continue
            man_abs = studio.confine_workspace(it['deliveryManifestPath'])
            with open(man_abs, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            if it['modality'] == 'carousel':
                self.assertEqual(manifest['geometry'], {'width': 1080, 'height': 1350})
                for card in manifest['cards']:
                    cabs = studio.confine_workspace(card['path'])
                    self.assertEqual(render_local.sha256_file(cabs), card['sha256'])
            else:
                v_art = manifest['artifacts']['video']
                v_abs = studio.confine_workspace(v_art['path'])
                self.assertEqual(render_local.sha256_file(v_abs), v_art['sha256'])
                probe = subprocess.run(
                    [ffprobe, '-v', 'error', '-show_streams', '-of', 'json', v_abs],
                    capture_output=True, text=True, check=True,
                )
                streams = json.loads(probe.stdout)['streams']
                v_streams = [s for s in streams if s.get('codec_type') == 'video']
                a_streams = [s for s in streams if s.get('codec_type') == 'audio']
                self.assertEqual(len(v_streams), 1)
                self.assertEqual(len(a_streams), 0)
                self.assertEqual(v_streams[0]['r_frame_rate'], '30/1')
                if it['profileId'] == 'instagram-reels-video':
                    self.assertEqual((v_streams[0]['width'], v_streams[0]['height']), (1080, 1920))
                else:
                    self.assertEqual((v_streams[0]['width'], v_streams[0]['height']), (1920, 1080))

        # Aprovar uma peca na Revisao e gerar ZIP
        rev = studio.get_review_overview(w1)
        reels_piece = next(p for p in rev['pieces'] if p['pieceKey'] == 'video:instagram-reels-video')
        self.assertEqual(reels_piece['status'], 'pending_review')
        studio.decide_review({
            'workId': w1,
            'targetType': 'piece',
            'modality': 'video',
            'profileId': 'instagram-reels-video',
            'decision': 'approved_for_local_delivery',
            'expectedVersionId': reels_piece['deliveryVersionId'],
            'note': 'qa-queue',
        })
        pkg_res = studio.create_package({
            'workId': w1,
            'pieces': [{'modality': 'video', 'profileId': 'instagram-reels-video', 'expectedVersionId': reels_piece['deliveryVersionId']}],
        })
        self.assertTrue((pkg_res.get('packageDelivery') or {}).get('available') or (pkg_res.get('lastValidDelivery') or {}).get('zipSha256'))

        # Alterar apenas enquadramento do rascunho -> entrega pertence a versao anterior (draft_outdated)
        opened = studio.open_work(w1)
        vreq = opened['videoRequest']
        vreq['scenes'][0]['framingByProfile']['instagram-reels-video']['centerX'] = 0.2
        studio.save_work({'workId': w1, 'videoRequest': vreq})
        rev_after = studio.get_review_overview(w1)
        reels_after = next(p for p in rev_after['pieces'] if p['pieceKey'] == 'video:instagram-reels-video')
        self.assertEqual(reels_after['status'], 'draft_outdated')

    def test_04_crash_recovery_fence_and_media_divergence_retry(self):
        if not REQUIRE_RENDER and not _tools_available():
            self.skipTest('FFmpeg/FFprobe indisponivel')
        w1 = f'tq-rec-{os.getpid()}'
        studio1 = self._make_studio(auto_start=False)
        self._seed_work(studio1, w1, 'marca-salao')

        # 1. Enfileira 2 itens e simula queda durante render no item 1
        batch = studio1.queue.enqueue_batch([
            {'workId': w1, 'modality': 'video', 'profileId': 'instagram-reels-video'},
            {'workId': w1, 'modality': 'carousel', 'profileId': 'instagram-feed-image-portrait'},
        ])
        it1_id = batch['items'][0]['itemId']
        it2_id = batch['items'][1]['itemId']

        # Reivindica manualmente it1 como running com PID morto (simulando queda durante render)
        claimed, att1 = studio1.queue._claim_next_item()
        self.assertEqual(claimed['item_id'], it1_id)
        studio1.queue.release_executor_lease()

        # Reinicia novo Studio/Queue -> it1 vira interrupted, it2 retoma e conclui
        studio2 = self._make_studio(auto_start=True)
        settled = _wait_batch_settled(studio2.queue, batch['batchId'], timeout=120.0)
        it1_after = next(i for i in settled['items'] if i['itemId'] == it1_id)
        it2_after = next(i for i in settled['items'] if i['itemId'] == it2_id)
        self.assertEqual(it1_after['status'], 'interrupted')
        self.assertEqual(it2_after['status'], 'completed')
        studio2.close()

        # 2. Simula queda exatamente na janela entre promocao e registro de conclusao
        studio3 = self._make_studio(auto_start=False)
        hit_window = threading.Event()

        def stop_at_window(item_row, attempt_row):
            hit_window.set()
            raise RuntimeError('simulated crash after promotion')

        studio3.queue._test_before_record_completion = stop_at_window
        studio3.queue.retry_item(it1_id, use_current=False)
        try:
            studio3.queue.run_once()
        except RuntimeError:
            pass
        self.assertTrue(hit_window.is_set())
        studio3.queue.release_executor_lease()

        # Reinicia novo Studio -> comprova promocao pelo attemptId e reconcilia idempotentemente
        studio4 = self._make_studio(auto_start=True)
        it1_reconciled = studio4.queue.get_item(it1_id)
        self.assertEqual(it1_reconciled['status'], 'completed')
        self.assertIsNotNone(it1_reconciled['deliveryVersionId'])

        # Chamar record_export_lineage novamente com o mesmo attemptId nao duplica versao
        rev = studio4.get_review_overview(w1)
        reels_piece = next(p for p in rev['pieces'] if p['pieceKey'] == 'video:instagram-reels-video')
        vcount_before = reels_piece['versionsCount']
        with studio4.queue._connect() as c4:
            item_row_4 = c4.execute('SELECT * FROM queue_items WHERE item_id=?', (it1_id,)).fetchone()
        c4.close()
        studio4.queue._record_review_for_item(
            item_row_4,
            it1_reconciled['lastAttemptId'],
            {'status': 'completed', 'profiles': [{'profileId': 'instagram-reels-video', 'status': 'completed'}]},
        )
        rev2 = studio4.get_review_overview(w1)
        reels_piece2 = next(p for p in rev2['pieces'] if p['pieceKey'] == 'video:instagram-reels-video')
        self.assertEqual(reels_piece2['versionsCount'], vcount_before)
        studio4.close()

        # 3. Divergencia de midia apos enfileiramento + retry com versao atual
        studio5 = self._make_studio(auto_start=False)
        batch2 = studio5.queue.enqueue_batch([
            {'workId': w1, 'modality': 'video', 'profileId': 'youtube-video-horizontal'},
        ])
        yt_id = batch2['items'][0]['itemId']
        # Modifica os bytes da midia fonte no disco
        opened = studio5.open_work(w1)
        clip_abs = studio5.confine(opened['videoRequest']['media'][-1]['path'])
        _create_color_video(clip_abs, 'red', duration_s=2.5)
        studio5.queue.run_once()
        yt_failed = studio5.queue.get_item(yt_id)
        self.assertEqual(yt_failed['status'], 'failed')
        self.assertEqual(yt_failed['errorCode'], 'MEDIA_DIVERGENCE')
        self.assertTrue(yt_failed['canUseCurrent'])

        # Tentar novamente com snapshot anterior falha com canUseCurrent=True
        with self.assertRaises(studio_queue.QueueConflictError) as ctx:
            studio5.queue.retry_item(yt_id, use_current=False)
        self.assertTrue(ctx.exception.can_use_current)

        # Enfileirar versao atual conclui com sucesso
        studio5.queue.retry_item(yt_id, use_current=True)
        studio5.queue.start_executor()
        settled2 = _wait_batch_settled(studio5.queue, batch2['batchId'], timeout=120.0)
        self.assertEqual(settled2['items'][0]['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
