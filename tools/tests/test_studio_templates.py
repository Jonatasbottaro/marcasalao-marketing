"""Testes de modelos reutilizaveis, duplicacao e variacoes em serie no Video Studio."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
TOOLS = os.path.join(ROOT, 'tools')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import build_video
import render_local
import studio_queue
import studio_templates
import video_studio

REQUIRE_RENDER = os.environ.get('REQUIRE_RENDER') == '1'


def _tools_available():
    try:
        build_video.get_ffmpeg()
        build_video.get_ffprobe()
        return True
    except build_video.DeliveryError:
        return False


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


def _wait_batch_settled(queue, batch_id, timeout=240.0):
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        batch = queue.get_batch(batch_id)
        counts = batch['counts']
        if counts['queued'] == 0 and counts['running'] == 0:
            return batch
        time.sleep(0.25)
    raise TimeoutError(f'batch {batch_id} did not settle within {timeout}s')


class TestStudioTemplates(unittest.TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp(prefix='t_templates_', dir=os.path.join(ROOT, '.workspace', 'tmp'))
        self.work_ids = []
        self.template_ids = []
        self.project_files = []
        self.creation_keys = []
        self.studios = []

    def tearDown(self):
        for st in self.studios:
            try:
                st.close()
            except Exception:
                pass
        for wid in self.work_ids:
            shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'works', wid), ignore_errors=True)
        for tid in self.template_ids:
            shutil.rmtree(os.path.join(ROOT, '.workspace', 'studio', 'templates', tid), ignore_errors=True)
        for key in self.creation_keys:
            p = os.path.join(ROOT, '.workspace', 'studio', 'template-creations', f'{key}.json')
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        for pfile in self.project_files:
            if os.path.exists(pfile):
                try:
                    os.remove(pfile)
                except OSError:
                    pass
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def _make_studio(self, auto_start_queue=False):
        st = video_studio.Studio(ROOT, 0, auto_start_queue=False)
        if auto_start_queue:
            db_path = os.path.join(self.tmp_root, 'queue.sqlite')
            st.queue = studio_queue.StudioQueue(st, auto_start=True, db_path=db_path)
        self.studios.append(st)
        return st

    def _make_project(self, studio, suffix, profiles=None):
        proj_res = studio.create_project({
            'schemaVersion': 1,
            'id': f'tt-proj-{suffix}-{os.getpid()}',
            'name': f'Projeto {suffix}',
            'locale': 'pt-BR',
            'timezone': 'America/Sao_Paulo',
            'brandTheme': 'marca-salao',
            'assetRoot': f'.workspace/studio/works/tt-src-{suffix}-{os.getpid()}/media',
            'contentPolicies': {
                'requireApprovedBriefing': True,
                'requireApprovedScript': True,
                'prohibitPersonalData': True,
                'requireFunctionalEvidence': True,
            },
            'outputProfiles': profiles or [
                'instagram-reels-video',
                'youtube-video-horizontal',
                'instagram-feed-image-square',
                'instagram-feed-image-portrait',
            ],
        })
        self.project_files.append(studio.confine(proj_res['path']))
        return proj_res['path']

    def _seed_work(self, studio, suffix='a', with_clip=False):
        wid = f'tt-src-{suffix}-{os.getpid()}'
        self.work_ids.append(wid)
        project = self._make_project(studio, suffix)
        opened = studio.create_work({'id': wid, 'name': f'Origem {suffix}', 'project': project, 'template': 'marca-salao'})
        if with_clip and _tools_available():
            clip_rel = f"{opened['work']['paths']['mediaDir']}/clip.mp4"
            _create_color_video(studio.confine(clip_rel), 'blue', duration_s=2.5)
            vreq = json.loads(json.dumps(opened['videoRequest']))
            vreq['media'] = list(vreq.get('media') or []) + [
                {'id': 'clip-1', 'type': 'video', 'path': clip_rel, 'origin': 'synthetic-demo', 'license': 'owned-synthetic'}
            ]
            vreq['scenes'][0]['mediaId'] = 'clip-1'
            vreq['scenes'][0]['sourceStartMs'] = 200
            vreq['scenes'][0]['durationMs'] = 1200
            vreq['scenes'][0]['framingByProfile'] = {
                'instagram-reels-video': {'centerX': 0.7, 'centerY': 0.5, 'zoomPercent': 140},
            }
            studio.save_work({'workId': wid, 'videoRequest': vreq})
        studio.save_editorial({'workId': wid, 'briefing': {'hook': f'Gancho {suffix}', 'cta': f'CTA {suffix}'}})
        return wid

    def _save_template(self, studio, wid, name, template_id=None):
        res = studio.save_template({'workId': wid, 'name': name, 'templateId': template_id})
        tid = res['template']['id']
        if tid not in self.template_ids:
            self.template_ids.append(tid)
        return res

    def _rows(self, *ids):
        return [{'id': i, 'name': f'Variacao {i}'} for i in ids]

    def _track(self, *ids):
        for i in ids:
            if i not in self.work_ids:
                self.work_ids.append(i)

    def test_01_capture_revisions_immutability_and_instantiation(self):
        studio = self._make_studio()
        wid = self._seed_work(studio)
        saved = self._save_template(studio, wid, 'Modelo A')
        tid = saved['template']['id']
        self.assertEqual(saved['revisionId'], 'rev-1')
        rev1_snap, rev1_dir = studio_templates.load_revision_snapshot(studio, tid, 'rev-1')
        rev1_title = rev1_snap['videoRequest']['title']
        media_files = os.listdir(os.path.join(rev1_dir, 'media'))
        self.assertTrue(media_files)
        for entry in rev1_snap['media']:
            fpath = os.path.join(rev1_dir, 'media', entry['file'])
            self.assertEqual(render_local.sha256_file(fpath), entry['sha256'])
            self.assertIsNotNone(entry['origin'])
            self.assertIsNotNone(entry['license'])

        # Edita a origem e salva nova revisao; rev-1 permanece intacta
        vreq = studio.open_work(wid)['videoRequest']
        vreq['title'] = 'Titulo novo da origem'
        studio.save_work({'workId': wid, 'videoRequest': vreq})
        saved2 = self._save_template(studio, wid, 'Modelo A', template_id=tid)
        self.assertEqual(saved2['revisionId'], 'rev-2')
        rev1_snap_after, _ = studio_templates.load_revision_snapshot(studio, tid, 'rev-1')
        self.assertEqual(rev1_snap_after['videoRequest']['title'], rev1_title)
        self.assertEqual(rev1_snap_after, rev1_snap)

        # Instancia a revisao antiga mesmo com a origem alterada
        vid = f'tt-var-old-{os.getpid()}'
        self._track(vid)
        key = f'tt-key-01-{os.getpid()}'
        self.creation_keys.append(key)
        res = studio.create_template_variations({
            'templateId': tid, 'revisionId': 'rev-1',
            'rows': [{'id': vid, 'name': 'Da revisao antiga'}], 'idempotencyKey': key,
        })
        self.assertEqual(res['creations'][0]['status'], 'created')
        opened = studio.open_work(vid)
        self.assertEqual(opened['videoRequest']['title'], rev1_title)
        self.assertEqual(opened['videoRequest']['id'], f'{vid}-video')
        self.assertEqual(opened['motionPlan']['requestId'], f'{vid}-video')
        self.assertEqual(opened['work']['origin']['revisionId'], 'rev-1')
        for m in opened['videoRequest']['media']:
            self.assertTrue(m['path'].startswith(f'.workspace/studio/works/{vid}/media/'))
            self.assertTrue(os.path.isfile(studio.confine(m['path'])))
        # Ficha propria, revisao em aberto, entregas vazias
        self.assertTrue(all(p['versionsCount'] == 0 and p['status'] == 'no_delivery' for p in opened['review']['pieces']))
        self.assertFalse(opened['packageDelivery'].get('available'))
        self.assertEqual(opened['deliveries']['video'].get('profiles', []), [])
        self.assertEqual(opened['review']['editorial']['briefing']['hook'], f'Gancho a')

    def test_02_plan_no_files_overrides_idempotency_and_resume(self):
        studio = self._make_studio()
        wid = self._seed_work(studio)
        tid = self._save_template(studio, wid, 'Modelo B')['template']['id']
        va = f'tt-var-a-{os.getpid()}'
        vb = f'tt-var-b-{os.getpid()}'
        self._track(va, vb)
        rows = [
            {'id': va, 'name': 'Variacao A', 'title': 'Titulo A', 'hook': 'Gancho A'},
            {'id': vb, 'name': 'Variacao B'},
        ]
        plan = studio.plan_template_variations({'templateId': tid, 'revisionId': 'rev-1', 'rows': rows})
        self.assertTrue(all(p['ok'] for p in plan['plans']))
        self.assertEqual(plan['plans'][0]['changes']['title']['effective'], 'Titulo A')
        self.assertTrue(plan['plans'][0]['changes']['title']['changed'])
        self.assertFalse(plan['plans'][1]['changes']['title']['changed'])
        self.assertFalse(os.path.exists(os.path.join(ROOT, '.workspace', 'studio', 'works', va)))

        key = f'tt-key-02-{os.getpid()}'
        self.creation_keys.append(key)
        res = studio.create_template_variations({'templateId': tid, 'revisionId': 'rev-1', 'rows': rows, 'idempotencyKey': key})
        self.assertTrue(all(c['status'] == 'created' for c in res['creations']))
        res2 = studio.create_template_variations({'templateId': tid, 'revisionId': 'rev-1', 'rows': rows, 'idempotencyKey': key})
        self.assertTrue(res2['deduplicated'])
        self.assertEqual([c['id'] for c in res2['creations']], [va, vb])

        # Retomada: mesma chave e mesmas linhas, com condicao resolvida entre tentativas
        ve = f'tt-var-e-{os.getpid()}'
        vf = f'tt-var-f-{os.getpid()}'
        self._track(ve, vf)
        key_r = f'tt-key-02r-{os.getpid()}'
        self.creation_keys.append(key_r)
        rows_r = [{'id': ve, 'name': 'Variacao E'}, {'id': vf, 'name': 'Variacao F'}]
        snap, rev_dir = studio_templates.load_revision_snapshot(studio, tid, 'rev-1')
        victim = os.path.join(rev_dir, 'media', snap['media'][0]['file'])
        os.replace(victim, victim + '.bak')
        try:
            res_r1 = studio.create_template_variations({'templateId': tid, 'revisionId': 'rev-1', 'rows': rows_r, 'idempotencyKey': key_r})
            self.assertTrue(all(c['status'] == 'failed' for c in res_r1['creations']))
            self.assertEqual(res_r1['creations'][0]['error']['code'], 'TEMPLATE_MEDIA_MISSING')
        finally:
            os.replace(victim + '.bak', victim)
        res_r2 = studio.create_template_variations({'templateId': tid, 'revisionId': 'rev-1', 'rows': rows_r, 'idempotencyKey': key_r})
        self.assertFalse(res_r2['deduplicated'])
        self.assertTrue(all(c['status'] == 'created' for c in res_r2['creations']))
        res_r3 = studio.create_template_variations({'templateId': tid, 'revisionId': 'rev-1', 'rows': rows_r, 'idempotencyKey': key_r})
        self.assertTrue(res_r3['deduplicated'])

        # Chave reutilizada com linhas diferentes e rejeitada
        with self.assertRaises(studio_templates.TemplateConflictError) as ctx:
            studio.create_template_variations({
                'templateId': tid, 'revisionId': 'rev-1',
                'rows': [{'id': f'tt-x-{os.getpid()}'}], 'idempotencyKey': key,
            })
        self.assertEqual(ctx.exception.code, 'CREATION_KEY_REUSE')

        # Overrides de ficha e independencia entre variacoes e origem
        a = studio.open_work(va)
        self.assertEqual(a['review']['editorial']['briefing']['hook'], 'Gancho A')
        self.assertEqual(a['review']['editorial']['briefing']['cta'], 'CTA a')
        vreq = a['videoRequest']
        vreq['title'] = 'Editado so em A'
        studio.save_work({'workId': va, 'videoRequest': vreq})
        self.assertNotEqual(studio.open_work(vb)['videoRequest']['title'], 'Editado so em A')
        self.assertNotEqual(studio.open_work(wid)['videoRequest']['title'], 'Editado so em A')

    def test_03_collisions_missing_media_allowlist_and_project_scope(self):
        studio = self._make_studio()
        wid = self._seed_work(studio)
        tid = self._save_template(studio, wid, 'Modelo C')['template']['id']

        # Colisao com trabalho existente preserva o conteudo
        key = f'tt-key-03-{os.getpid()}'
        self.creation_keys.append(key)
        res = studio.create_template_variations({
            'templateId': tid, 'revisionId': 'rev-1',
            'rows': [{'id': wid, 'name': 'Colisao'}], 'idempotencyKey': key,
        })
        self.assertEqual(res['creations'][0]['status'], 'failed')
        self.assertEqual(res['creations'][0]['error']['code'], 'WORK_ID_COLLISION')
        self.assertEqual(studio.open_work(wid)['work']['name'], 'Origem a')

        # Midia do modelo removida -> condicao acionavel no plano e falha na criacao
        snap, rev_dir = studio_templates.load_revision_snapshot(studio, tid, 'rev-1')
        victim = os.path.join(rev_dir, 'media', snap['media'][0]['file'])
        backup = victim + '.bak'
        os.replace(victim, backup)
        try:
            plan = studio.plan_template_variations({
                'templateId': tid, 'revisionId': 'rev-1',
                'rows': [{'id': f'tt-miss-{os.getpid()}'}],
            })
            self.assertFalse(plan['plans'][0]['ok'])
            self.assertTrue(any(c['code'] == 'TEMPLATE_MEDIA_MISSING' for c in plan['plans'][0]['conditions']))
        finally:
            os.replace(backup, victim)

        # Allowlist mudou: perfil fora da allowlist exige ajuste antes de criar
        project_rel = studio.open_work(wid)['work']['project']
        project_abs = studio.confine(project_rel)
        with open(project_abs, 'r', encoding='utf-8') as f:
            pdoc = json.load(f)
        original_profiles = list(pdoc['outputProfiles'])
        pdoc['outputProfiles'] = ['instagram-feed-image-square']
        with open(project_abs, 'w', encoding='utf-8') as f:
            json.dump(pdoc, f, ensure_ascii=False, indent=2)
        try:
            plan = studio.plan_template_variations({
                'templateId': tid, 'revisionId': 'rev-1',
                'rows': [{'id': f'tt-allow-{os.getpid()}'}],
            })
            self.assertFalse(plan['plans'][0]['ok'])
            self.assertTrue(plan['profileAdjustments'])
            res = studio.create_template_variations({
                'templateId': tid, 'revisionId': 'rev-1',
                'rows': [{'id': f'tt-allow-{os.getpid()}'}], 'idempotencyKey': f'tt-key-allow-{os.getpid()}',
            })
            self.creation_keys.append(f'tt-key-allow-{os.getpid()}')
            self.assertEqual(res['creations'][0]['error']['code'], 'PROFILE_NEEDS_ADJUSTMENT')
        finally:
            pdoc['outputProfiles'] = original_profiles
            with open(project_abs, 'w', encoding='utf-8') as f:
                json.dump(pdoc, f, ensure_ascii=False, indent=2)

        # Modelo restrito ao projeto de origem
        other_project = self._make_project(studio, 'outro')
        wid2 = f'tt-other-{os.getpid()}'
        self.work_ids.append(wid2)
        studio.create_work({'id': wid2, 'name': 'Outro projeto', 'project': other_project, 'template': 'blank'})
        with self.assertRaises(studio_templates.TemplateConflictError) as ctx:
            studio.save_template({'workId': wid2, 'templateId': tid})
        self.assertEqual(ctx.exception.code, 'TEMPLATE_PROJECT_MISMATCH')

    def test_04_duplicate_and_restart_recovery(self):
        studio = self._make_studio()
        wid = self._seed_work(studio)
        tid = self._save_template(studio, wid, 'Modelo D')['template']['id']
        dup = f'tt-dup-{os.getpid()}'
        self._track(dup)
        res = studio.duplicate_work({'workId': wid, 'newId': dup, 'name': 'Copia direta'})
        self.assertEqual(res['work']['origin']['kind'], 'duplicate')
        self.assertEqual(res['work']['origin']['sourceWorkId'], wid)
        d = studio.open_work(dup)
        self.assertEqual(d['videoRequest']['id'], f'{dup}-video')
        for m in d['videoRequest']['media']:
            self.assertTrue(m['path'].startswith(f'.workspace/studio/works/{dup}/media/'))
        src = studio.open_work(wid)
        for sm, dm in zip(src['videoRequest']['media'], d['videoRequest']['media']):
            self.assertEqual(render_local.sha256_file(studio.confine(sm['path'])),
                             render_local.sha256_file(studio.confine(dm['path'])))
        self.assertTrue(all(p['versionsCount'] == 0 and p['status'] == 'no_delivery' for p in d['review']['pieces']))

        # Reinicio do Studio: modelos, revisoes e variacoes persistem
        studio.close()
        studio2 = self._make_studio()
        templates = studio2.get_templates()['templates']
        self.assertIn(tid, [t['id'] for t in templates])
        reopened = studio2.open_work(dup)
        self.assertEqual(reopened['videoRequest']['id'], f'{dup}-video')
        snap, _ = studio_templates.load_revision_snapshot(studio2, tid, 'rev-1')
        self.assertEqual(snap['sourceWorkId'], wid)

    def test_05_concurrent_edit_detection(self):
        studio = self._make_studio()
        wid = self._seed_work(studio)
        # Edicao concorrente durante a copia das midias: o fingerprint final
        # difere do conferido apos a captura e a revisao nao e promovida.
        original_copyfile = studio_templates.shutil.copyfile
        calls = {'n': 0}

        def copy_then_edit(src, dst):
            res = original_copyfile(src, dst)
            calls['n'] += 1
            if calls['n'] == 1:
                vreq = studio.open_work(wid)['videoRequest']
                vreq['title'] = 'Edicao concorrente'
                studio.save_work({'workId': wid, 'videoRequest': vreq})
            return res

        studio_templates.shutil.copyfile = copy_then_edit
        try:
            with self.assertRaises(studio_templates.TemplateConflictError) as ctx:
                studio.save_template({'workId': wid, 'name': 'Modelo conflito'})
            self.assertEqual(ctx.exception.code, 'TEMPLATE_CAPTURE_CONFLICT')
        finally:
            studio_templates.shutil.copyfile = original_copyfile
        self.assertEqual(studio.get_templates()['templates'], [])

    def test_06_variation_queue_export_review_and_zip(self):
        if not REQUIRE_RENDER and not _tools_available():
            self.skipTest('FFmpeg/FFprobe indisponivel')
        studio = self._make_studio(auto_start_queue=True)
        wid = self._seed_work(studio, suffix='q', with_clip=True)
        tid = self._save_template(studio, wid, 'Modelo fila')['template']['id']
        va = f'tt-qvar-{os.getpid()}'
        self._track(va)
        key = f'tt-key-06-{os.getpid()}'
        self.creation_keys.append(key)
        res = studio.create_template_variations({
            'templateId': tid, 'revisionId': 'rev-1',
            'rows': [{'id': va, 'name': 'Variacao fila', 'title': 'Titulo da variacao'}],
            'idempotencyKey': key,
        })
        self.assertEqual(res['creations'][0]['status'], 'created')

        batch = studio.queue.enqueue_batch([
            {'workId': va, 'modality': 'video', 'profileId': 'instagram-reels-video'},
            {'workId': va, 'modality': 'carousel', 'profileId': 'instagram-feed-image-portrait'},
        ], idempotency_key=f'tt-queue-{os.getpid()}')
        settled = _wait_batch_settled(studio.queue, batch['batchId'])
        self.assertEqual(settled['counts']['failed'], 0,
                           [(i['profileId'], i['errorMessage']) for i in settled['items'] if i['status'] == 'failed'])
        self.assertEqual(settled['counts']['completed'], 2)

        ffprobe = build_video.get_ffprobe()
        video_item = next(i for i in settled['items'] if i['modality'] == 'video')
        man_abs = studio.confine_workspace(video_item['deliveryManifestPath'])
        with open(man_abs, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        v_abs = studio.confine_workspace(manifest['artifacts']['video']['path'])
        probe = subprocess.run([ffprobe, '-v', 'error', '-show_streams', '-of', 'json', v_abs],
                               capture_output=True, text=True, check=True)
        streams = json.loads(probe.stdout)['streams']
        self.assertEqual(len([s for s in streams if s.get('codec_type') == 'audio']), 0)
        vs = next(s for s in streams if s.get('codec_type') == 'video')
        self.assertEqual((vs['width'], vs['height']), (1080, 1920))
        self.assertEqual(vs['r_frame_rate'], '30/1')
        # A versao promoted pertence ao snapshot da variacao (titulo override)
        rev = studio.get_review_overview(va)
        piece = next(p for p in rev['pieces'] if p['pieceKey'] == 'video:instagram-reels-video')
        state = studio_templates.studio_review._load_review_state(
            studio, va, studio_templates.studio_review.merged_work_paths(studio, va))
        stored = state['pieces']['video:instagram-reels-video']['versions'][-1]
        self.assertEqual(stored['requestSnapshot']['title'], 'Titulo da variacao')

        studio.decide_review({
            'workId': va, 'targetType': 'piece', 'modality': 'video',
            'profileId': 'instagram-reels-video', 'decision': 'approved_for_local_delivery',
            'expectedVersionId': piece['deliveryVersionId'], 'note': 'qa-templates',
        })
        pkg = studio.create_package({
            'workId': va,
            'pieces': [{'modality': 'video', 'profileId': 'instagram-reels-video',
                         'expectedVersionId': piece['deliveryVersionId']}],
        })
        pkg_info = pkg.get('packageDelivery') or pkg
        self.assertTrue(pkg_info.get('available'), pkg)
        self.assertTrue((pkg_info.get('lastValidDelivery') or {}).get('zipSha256'))


if __name__ == '__main__':
    unittest.main()