"""Fila local persistente de producao em lote para o Video Studio.

Persiste lotes, itens (trabalho + modalidade + perfil) e tentativas em SQLite
sob `.workspace/studio/production-queue.sqlite`, com executor unico em serie por
workspace, cerca de promocao por tentativa, retomada segura apos reinicio e
integracao idempotente com a Revisao e o pacote ZIP.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone

import produce_carousel
import produce_video
import render_local
import studio_review


QUEUE_SCHEMA_VERSION = 1
VALID_STATUSES = ('queued', 'running', 'completed', 'failed', 'cancelled', 'interrupted')
VALID_MODALITIES = ('video', 'carousel', 'motion')
LEASE_STALE_SECONDS = 20.0
EXPORT_TIMEOUT_SECONDS = 300

MODALITY_LABELS = {
    'video': 'Video',
    'carousel': 'Carrossel',
    'motion': 'Motion',
}


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _pid_is_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == 'nt':
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return exit_code.value == STILL_ACTIVE
            return False
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


class QueueConflictError(ValueError):
    """Erro de conflito ou indisponibilidade recuperavel na fila."""

    def __init__(self, code, message, can_use_current=False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.can_use_current = can_use_current


class StudioQueue:
    """Gerenciador persistente da fila de producao em lote por workspace."""

    def __init__(self, studio, auto_start=True, db_path=None):
        self.studio = studio
        self.workspace_dir = studio.workspace_dir
        self.db_path = db_path or os.path.join(self.workspace_dir, 'production-queue.sqlite')
        self.fences_dir = os.path.join(self.workspace_dir, 'queue-fences')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.fences_dir, exist_ok=True)

        self._db_lock = threading.RLock()
        self._wake_event = threading.Event()
        self._stop_event = threading.Event()
        self._worker_thread = None
        self._executor_id = f'exec-{uuid.uuid4().hex[:10]}'
        self._has_lease = False

        self._active_lock = threading.Lock()
        self._active_output_dir = None
        self._active_attempt_id = None
        self._active_item_id = None

        # Hooks opcionais para sincronizacao deterministica em testes
        self._test_before_record_completion = None
        self._test_on_attempt_started = None

        self._init_db()
        if auto_start:
            self.start_executor()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA foreign_keys=ON')
        return conn

    def _init_db(self):
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute('BEGIN IMMEDIATE')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS schema_meta (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS executor_leases (
                        workspace_root TEXT PRIMARY KEY,
                        executor_id TEXT NOT NULL,
                        pid INTEGER NOT NULL,
                        acquired_at TEXT NOT NULL,
                        heartbeat_at TEXT NOT NULL
                    )
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS batches (
                        batch_id TEXT PRIMARY KEY,
                        idempotency_key TEXT UNIQUE,
                        label TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        summary_json TEXT
                    )
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS queue_items (
                        item_id TEXT PRIMARY KEY,
                        batch_id TEXT NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
                        position INTEGER NOT NULL,
                        work_id TEXT NOT NULL,
                        modality TEXT NOT NULL,
                        profile_id TEXT NOT NULL,
                        output_dir TEXT NOT NULL,
                        status TEXT NOT NULL,
                        snapshot_json TEXT NOT NULL,
                        snapshot_sha256 TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        started_at TEXT,
                        finished_at TEXT,
                        updated_at TEXT NOT NULL,
                        error_code TEXT,
                        error_message TEXT,
                        last_attempt_id TEXT,
                        delivery_version_id TEXT,
                        delivery_manifest_path TEXT,
                        delivery_manifest_sha256 TEXT
                    )
                ''')
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_queue_items_batch_pos
                    ON queue_items(batch_id, position)
                ''')
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_queue_items_status_created
                    ON queue_items(status, created_at, position)
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS queue_attempts (
                        attempt_id TEXT PRIMARY KEY,
                        item_id TEXT NOT NULL REFERENCES queue_items(item_id) ON DELETE CASCADE,
                        attempt_number INTEGER NOT NULL,
                        snapshot_sha256 TEXT NOT NULL,
                        snapshot_source TEXT NOT NULL,
                        status TEXT NOT NULL,
                        pid INTEGER,
                        fence_path TEXT,
                        staging_dir TEXT,
                        started_at TEXT NOT NULL,
                        finished_at TEXT,
                        error_code TEXT,
                        error_message TEXT,
                        promoted_manifest_path TEXT,
                        promoted_manifest_sha256 TEXT,
                        delivery_version_id TEXT
                    )
                ''')
                conn.execute('''
                    INSERT OR IGNORE INTO schema_meta (key, value) VALUES ('schema_version', ?)
                ''', (str(QUEUE_SCHEMA_VERSION),))
                conn.execute('COMMIT')
            except Exception:
                conn.execute('ROLLBACK')
                raise
            finally:
                conn.close()

    def schema_version(self):
        with self._db_lock:
            conn = self._connect()
            try:
                row = conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
                return int(row['value']) if row else 0
            finally:
                conn.close()

    # ---- Lease de executor unico por workspace ----
    def acquire_executor_lease(self):
        now = now_iso()
        now_ts = time.time()
        pid = os.getpid()
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute('BEGIN IMMEDIATE')
                row = conn.execute(
                    'SELECT * FROM executor_leases WHERE workspace_root=?',
                    (self.studio.root,),
                ).fetchone()
                if row is not None and row['executor_id'] != self._executor_id:
                    other_pid = int(row['pid'])
                    try:
                        hb_dt = datetime.strptime(row['heartbeat_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                        age = now_ts - hb_dt.timestamp()
                    except ValueError:
                        age = LEASE_STALE_SECONDS + 1
                    if _pid_is_alive(other_pid) and age < LEASE_STALE_SECONDS:
                        conn.execute('ROLLBACK')
                        self._has_lease = False
                        return False
                conn.execute('''
                    INSERT INTO executor_leases (workspace_root, executor_id, pid, acquired_at, heartbeat_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(workspace_root) DO UPDATE SET
                        executor_id=excluded.executor_id,
                        pid=excluded.pid,
                        acquired_at=excluded.acquired_at,
                        heartbeat_at=excluded.heartbeat_at
                ''', (self.studio.root, self._executor_id, pid, now, now))
                conn.execute('COMMIT')
                self._has_lease = True
                return True
            except Exception:
                conn.execute('ROLLBACK')
                raise
            finally:
                conn.close()

    def refresh_executor_lease(self):
        now = now_iso()
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute('BEGIN IMMEDIATE')
                cur = conn.execute(
                    'UPDATE executor_leases SET heartbeat_at=? WHERE workspace_root=? AND executor_id=?',
                    (now, self.studio.root, self._executor_id),
                )
                conn.execute('COMMIT')
                self._has_lease = cur.rowcount == 1
                return self._has_lease
            except Exception:
                conn.execute('ROLLBACK')
                raise
            finally:
                conn.close()

    def release_executor_lease(self):
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute('BEGIN IMMEDIATE')
                conn.execute(
                    'DELETE FROM executor_leases WHERE workspace_root=? AND executor_id=?',
                    (self.studio.root, self._executor_id),
                )
                conn.execute('COMMIT')
            except Exception:
                conn.execute('ROLLBACK')
            finally:
                conn.close()
        self._has_lease = False

    def start_executor(self):
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return
        self._stop_event.clear()
        if self.acquire_executor_lease():
            self.recover_on_startup()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name='studio-queue-worker')
        self._worker_thread.start()
        self._wake_event.set()

    def stop_executor(self, timeout=5.0):
        self._stop_event.set()
        self._wake_event.set()
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)
        self.release_executor_lease()

    def is_destination_active(self, output_dir_rel):
        norm = self.studio._normalize_rel(output_dir_rel)
        with self._active_lock:
            return self._active_output_dir == norm

    def _set_active_destination(self, output_dir_rel, item_id=None, attempt_id=None):
        norm = self.studio._normalize_rel(output_dir_rel) if output_dir_rel else None
        with self._active_lock:
            self._active_output_dir = norm
            self._active_item_id = item_id
            self._active_attempt_id = attempt_id

    # ---- Planejamento e validacao de destinos ----
    def _catalog_for_project(self, project_rel):
        listing = self.studio.list_profiles(project_rel or None)
        video_profiles = {p['id']: p for p in listing.get('videoProfiles') or []}
        image_profiles = {p['id']: p for p in listing.get('imageProfiles') or []}
        allowlist = listing.get('allowlist')
        return video_profiles, image_profiles, allowlist

    def _build_frozen_snapshot(self, work_id, modality, profile_id):
        if modality not in VALID_MODALITIES:
            raise ValueError(f'modalidade invalida: {modality}')
        work = self.studio.load_work(work_id)
        project_rel = work.get('project')
        if not project_rel:
            raise ValueError(f'trabalho {work_id} sem projeto configurado')
        video_profiles, image_profiles, allowlist = self._catalog_for_project(project_rel)
        wpaths = work.get('paths') or self.studio.work_paths(work_id)

        if modality == 'carousel':
            if profile_id not in image_profiles:
                raise ValueError(f'perfil de carrossel indisponivel no catalogo/allowlist: {profile_id}')
            req = work.get('carouselRequest')
            if not isinstance(req, dict) or not req.get('cards'):
                raise ValueError(f'trabalho {work_id} nao possui carrossel salvo com cards')
            req_snapshot = json.loads(json.dumps(req))
            req_snapshot['project'] = project_rel
            req_snapshot['profile'] = profile_id
            motion_snapshot = None
            output_dir = wpaths['carouselDeliveryDir']
            draft_fp, _ = studio_review.compute_draft_snapshot(
                self.studio, 'carousel', None, req_snapshot, None, profile_id=profile_id
            )
            media_origins = studio_review._hash_media_list(self.studio, req_snapshot.get('media', []))
        else:
            if profile_id not in video_profiles:
                raise ValueError(f'perfil de video indisponivel no catalogo/allowlist: {profile_id}')
            pmeta = video_profiles[profile_id]
            req = work.get('videoRequest')
            if not isinstance(req, dict) or not req.get('scenes'):
                raise ValueError(f'trabalho {work_id} nao possui pedido de video salvo com cenas')
            req_snapshot = json.loads(json.dumps(req))
            req_snapshot['project'] = project_rel
            profiles_list = list(req_snapshot.get('profiles') or [])
            if profile_id not in profiles_list:
                profiles_list.append(profile_id)
            req_snapshot['profiles'] = profiles_list

            motion_snapshot = None
            output_dir = wpaths['videoDeliveryDir']
            if modality == 'motion':
                if pmeta.get('aspectRatio') != '9:16':
                    raise ValueError(f'Motion local disponivel apenas para perfis verticais 9:16 ({profile_id} e {pmeta.get("aspectRatio")})')
                mplan = work.get('motionPlan')
                if not isinstance(mplan, dict) or not mplan.get('effects'):
                    raise ValueError(f'trabalho {work_id} nao possui MotionPlan salvo com efeitos')
                motion_snapshot = json.loads(json.dumps(mplan))
                if req_snapshot.get('id'):
                    motion_snapshot['requestId'] = req_snapshot['id']
                output_dir = wpaths['motionDeliveryDir']

            draft_fp, _ = studio_review.compute_draft_snapshot(
                self.studio, modality, req_snapshot, None, motion_snapshot, profile_id=profile_id
            )
            media_origins = studio_review._hash_media_list(self.studio, req_snapshot.get('media', []))

        snapshot = {
            'schemaVersion': 1,
            'workId': work_id,
            'workTitle': work.get('title') or work_id,
            'project': project_rel,
            'workUpdatedAt': work.get('updatedAt'),
            'modality': modality,
            'profileId': profile_id,
            'outputDir': output_dir,
            'request': req_snapshot,
            'motionPlan': motion_snapshot,
            'mediaOrigins': media_origins,
            'draftFingerprint': draft_fp,
        }
        snapshot_sha = studio_review.canonical_sha256(snapshot)
        return snapshot, snapshot_sha

    def plan_batch(self, work_ids):
        """Lista opcoes disponiveis e indisponiveis por trabalho antes da confirmacao."""
        if not isinstance(work_ids, list) or not work_ids:
            raise ValueError('selecione pelo menos um trabalho')
        works_out = []
        seen = set()
        for wid in work_ids:
            if not isinstance(wid, str) or wid in seen:
                continue
            seen.add(wid)
            work = self.studio.load_work(wid)
            project_rel = work.get('project')
            video_profiles, image_profiles, allowlist = self._catalog_for_project(project_rel)
            wpaths = work.get('paths') or self.studio.work_paths(wid)
            v_req = work.get('videoRequest')
            c_req = work.get('carouselRequest')
            m_plan = work.get('motionPlan')

            options = []
            # Videos
            v_check_ok = None
            v_check_err = None
            if isinstance(v_req, dict) and v_req.get('scenes'):
                try:
                    tmp_req = json.loads(json.dumps(v_req))
                    tmp_req['project'] = project_rel
                    verdict = self.studio.check_video(tmp_req)
                    v_check_ok = bool(verdict.get('ok'))
                    if not v_check_ok:
                        v_check_err = verdict.get('failureCode') or 'VIDEO_REQUEST_INVALID'
                except Exception as exc:
                    v_check_ok = False
                    v_check_err = str(exc)
            else:
                v_check_ok = False
                v_check_err = 'Rascunho de video ausente ou sem cenas salvas.'

            for pid, pmeta in video_profiles.items():
                selected_in_req = isinstance(v_req, dict) and pid in (v_req.get('profiles') or [])
                avail = bool(v_check_ok)
                reason = None if avail else v_check_err
                options.append({
                    'workId': wid,
                    'workTitle': work.get('title') or wid,
                    'project': project_rel,
                    'modality': 'video',
                    'modalityLabel': 'Video',
                    'profileId': pid,
                    'profileLabel': pmeta.get('label') or pid,
                    'aspectRatio': pmeta.get('aspectRatio'),
                    'outputDir': wpaths['videoDeliveryDir'],
                    'selectedByDefault': selected_in_req and avail,
                    'available': avail,
                    'unavailableReason': reason,
                })

            # Carrosseis
            c_check_ok = None
            c_check_err = None
            if isinstance(c_req, dict) and c_req.get('cards'):
                try:
                    tmp_creq = json.loads(json.dumps(c_req))
                    tmp_creq['project'] = project_rel
                    verdict = self.studio.check_carousel(tmp_creq)
                    c_check_ok = bool(verdict.get('ok'))
                    if not c_check_ok:
                        c_check_err = verdict.get('failureCode') or 'CAROUSEL_REQUEST_INVALID'
                except Exception as exc:
                    c_check_ok = False
                    c_check_err = str(exc)
            else:
                c_check_ok = False
                c_check_err = 'Rascunho de carrossel ausente ou sem cards salvos.'

            for pid, pmeta in image_profiles.items():
                selected_in_req = isinstance(c_req, dict) and c_req.get('profile') == pid
                avail = bool(c_check_ok)
                reason = None if avail else c_check_err
                options.append({
                    'workId': wid,
                    'workTitle': work.get('title') or wid,
                    'project': project_rel,
                    'modality': 'carousel',
                    'modalityLabel': 'Carrossel',
                    'profileId': pid,
                    'profileLabel': pmeta.get('label') or pid,
                    'aspectRatio': pmeta.get('aspectRatio'),
                    'outputDir': wpaths['carouselDeliveryDir'],
                    'selectedByDefault': selected_in_req and avail,
                    'available': avail,
                    'unavailableReason': reason,
                })

            # Motion (somente 9:16 quando permitido)
            has_motion = isinstance(m_plan, dict) and bool(m_plan.get('effects'))
            for pid, pmeta in video_profiles.items():
                is_vertical = pmeta.get('aspectRatio') == '9:16'
                if not is_vertical and not has_motion:
                    continue
                avail = bool(v_check_ok and has_motion and is_vertical)
                if not is_vertical:
                    reason = f'Motion local exige perfil vertical 9:16 ({pid} e {pmeta.get("aspectRatio")}).'
                elif not has_motion:
                    reason = 'Plano de Motion sem efeitos salvos.'
                elif not v_check_ok:
                    reason = v_check_err
                else:
                    reason = None
                options.append({
                    'workId': wid,
                    'workTitle': work.get('title') or wid,
                    'project': project_rel,
                    'modality': 'motion',
                    'modalityLabel': 'Motion',
                    'profileId': pid,
                    'profileLabel': f'{pmeta.get("label") or pid} (Motion)',
                    'aspectRatio': pmeta.get('aspectRatio'),
                    'outputDir': wpaths['motionDeliveryDir'],
                    'selectedByDefault': bool(avail),
                    'available': avail,
                    'unavailableReason': reason,
                })

            works_out.append({
                'workId': wid,
                'title': work.get('title') or wid,
                'project': project_rel,
                'updatedAt': work.get('updatedAt'),
                'allowlist': allowlist,
                'options': options,
            })

        return {'works': works_out}

    # ---- Enfileiramento idempotente ----
    def enqueue_batch(self, items, idempotency_key=None, label=None):
        if not isinstance(items, list) or not items:
            raise ValueError('selecione pelo menos uma peca para enfileirar')
        clean_key = idempotency_key.strip() if isinstance(idempotency_key, str) and idempotency_key.strip() else None

        if clean_key:
            with self._db_lock:
                conn = self._connect()
                try:
                    existing = conn.execute(
                        'SELECT batch_id FROM batches WHERE idempotency_key=?',
                        (clean_key,),
                    ).fetchone()
                    if existing is not None:
                        batch = self.get_batch(existing['batch_id'])
                        batch['deduplicated'] = True
                        return batch
                finally:
                    conn.close()

        prepared = []
        seen_tuples = set()
        for entry in items:
            if not isinstance(entry, dict):
                raise ValueError('item de lote invalido')
            wid = entry.get('workId')
            mod = entry.get('modality')
            pid = entry.get('profileId')
            key = (wid, mod, pid)
            if key in seen_tuples:
                continue
            seen_tuples.add(key)
            snapshot, snap_sha = self._build_frozen_snapshot(wid, mod, pid)
            prepared.append((wid, mod, pid, snapshot['outputDir'], snapshot, snap_sha))

        if not prepared:
            raise ValueError('nenhuma peca valida selecionada para o lote')

        batch_id = f'batch-{uuid.uuid4().hex[:10]}'
        now = now_iso()

        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute('BEGIN IMMEDIATE')
                if clean_key:
                    existing = conn.execute(
                        'SELECT batch_id FROM batches WHERE idempotency_key=?',
                        (clean_key,),
                    ).fetchone()
                    if existing is not None:
                        conn.execute('ROLLBACK')
                        batch = self.get_batch(existing['batch_id'])
                        batch['deduplicated'] = True
                        return batch

                conn.execute('''
                    INSERT INTO batches (batch_id, idempotency_key, label, created_at, updated_at, summary_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (batch_id, clean_key, label or f'Lote ({len(prepared)} pecas)', now, now, None))

                for pos, (wid, mod, pid, out_dir, snap, snap_sha) in enumerate(prepared, start=1):
                    item_id = f'item-{uuid.uuid4().hex[:10]}'
                    conn.execute('''
                        INSERT INTO queue_items (
                            item_id, batch_id, position, work_id, modality, profile_id, output_dir,
                            status, snapshot_json, snapshot_sha256, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?)
                    ''', (
                        item_id, batch_id, pos, wid, mod, pid, out_dir,
                        json.dumps(snap, ensure_ascii=False), snap_sha, now, now,
                    ))
                conn.execute('COMMIT')
            except Exception:
                conn.execute('ROLLBACK')
                raise
            finally:
                conn.close()

        self._wake_event.set()
        batch = self.get_batch(batch_id)
        batch['deduplicated'] = False
        return batch

    # ---- Consultas e resumo ----
    def _row_to_item_dict(self, row, attempts_by_item=None):
        snap = json.loads(row['snapshot_json'])
        attempts = list((attempts_by_item or {}).get(row['item_id'], []))
        can_use_current = row['error_code'] in ('MEDIA_DIVERGENCE', 'SNAPSHOT_UNAVAILABLE')
        return {
            'itemId': row['item_id'],
            'batchId': row['batch_id'],
            'position': row['position'],
            'workId': row['work_id'],
            'workTitle': snap.get('workTitle') or row['work_id'],
            'project': snap.get('project'),
            'modality': row['modality'],
            'modalityLabel': MODALITY_LABELS.get(row['modality'], row['modality']),
            'profileId': row['profile_id'],
            'outputDir': row['output_dir'],
            'status': row['status'],
            'snapshotSha256': row['snapshot_sha256'],
            'draftFingerprint': snap.get('draftFingerprint'),
            'createdAt': row['created_at'],
            'startedAt': row['started_at'],
            'finishedAt': row['finished_at'],
            'updatedAt': row['updated_at'],
            'errorCode': row['error_code'],
            'errorMessage': row['error_message'],
            'canUseCurrent': can_use_current,
            'lastAttemptId': row['last_attempt_id'],
            'deliveryVersionId': row['delivery_version_id'],
            'deliveryManifestPath': row['delivery_manifest_path'],
            'deliveryManifestSha256': row['delivery_manifest_sha256'],
            'attempts': attempts,
        }

    @staticmethod
    def _derive_batch_counts(items):
        counts = {s: 0 for s in VALID_STATUSES}
        for it in items:
            st = it['status']
            if st in counts:
                counts[st] += 1
        total = len(items)
        if counts['running'] > 0:
            batch_status = 'running'
        elif counts['queued'] > 0:
            batch_status = 'queued'
        elif total > 0 and counts['completed'] == total:
            batch_status = 'completed'
        elif total > 0 and counts['cancelled'] == total:
            batch_status = 'cancelled'
        elif counts['completed'] > 0:
            batch_status = 'partial'
        elif counts['interrupted'] > 0:
            batch_status = 'interrupted'
        else:
            batch_status = 'failed'
        return {
            'total': total,
            **counts,
            'batchStatus': batch_status,
        }

    def _load_attempts_map(self, conn, item_ids):
        if not item_ids:
            return {}
        placeholders = ','.join('?' for _ in item_ids)
        rows = conn.execute(
            f'SELECT * FROM queue_attempts WHERE item_id IN ({placeholders}) ORDER BY attempt_number ASC',
            tuple(item_ids),
        ).fetchall()
        out = {}
        for r in rows:
            out.setdefault(r['item_id'], []).append({
                'attemptId': r['attempt_id'],
                'attemptNumber': r['attempt_number'],
                'snapshotSha256': r['snapshot_sha256'],
                'snapshotSource': r['snapshot_source'],
                'status': r['status'],
                'pid': r['pid'],
                'startedAt': r['started_at'],
                'finishedAt': r['finished_at'],
                'errorCode': r['error_code'],
                'errorMessage': r['error_message'],
                'promotedManifestPath': r['promoted_manifest_path'],
                'deliveryVersionId': r['delivery_version_id'],
            })
        return out

    def get_batch(self, batch_id):
        with self._db_lock:
            conn = self._connect()
            try:
                b = conn.execute('SELECT * FROM batches WHERE batch_id=?', (batch_id,)).fetchone()
                if b is None:
                    raise ValueError(f'lote desconhecido: {batch_id}')
                rows = conn.execute(
                    'SELECT * FROM queue_items WHERE batch_id=? ORDER BY position ASC',
                    (batch_id,),
                ).fetchall()
                attempts_map = self._load_attempts_map(conn, [r['item_id'] for r in rows])
                items = [self._row_to_item_dict(r, attempts_map) for r in rows]
                counts = self._derive_batch_counts(items)
                return {
                    'batchId': b['batch_id'],
                    'idempotencyKey': b['idempotency_key'],
                    'label': b['label'],
                    'createdAt': b['created_at'],
                    'updatedAt': b['updated_at'],
                    'counts': counts,
                    'batchStatus': counts['batchStatus'],
                    'items': items,
                }
            finally:
                conn.close()

    def get_item(self, item_id):
        with self._db_lock:
            conn = self._connect()
            try:
                r = conn.execute('SELECT * FROM queue_items WHERE item_id=?', (item_id,)).fetchone()
                if r is None:
                    raise ValueError(f'item desconhecido: {item_id}')
                attempts_map = self._load_attempts_map(conn, [item_id])
                return self._row_to_item_dict(r, attempts_map)
            finally:
                conn.close()

    def list_queue(self, status=None, work_id=None, batch_id=None):
        with self._db_lock:
            conn = self._connect()
            try:
                batch_rows = conn.execute('SELECT * FROM batches ORDER BY created_at DESC').fetchall()
                all_item_rows = conn.execute('SELECT * FROM queue_items ORDER BY created_at ASC, position ASC').fetchall()
                attempts_map = self._load_attempts_map(conn, [r['item_id'] for r in all_item_rows])
                all_items = [self._row_to_item_dict(r, attempts_map) for r in all_item_rows]
                by_batch = {}
                for it in all_items:
                    by_batch.setdefault(it['batchId'], []).append(it)

                batches = []
                for b in batch_rows:
                    b_items = by_batch.get(b['batch_id'], [])
                    counts = self._derive_batch_counts(b_items)
                    batches.append({
                        'batchId': b['batch_id'],
                        'idempotencyKey': b['idempotency_key'],
                        'label': b['label'],
                        'createdAt': b['created_at'],
                        'updatedAt': b['updated_at'],
                        'counts': counts,
                        'batchStatus': counts['batchStatus'],
                    })

                filtered = []
                for it in all_items:
                    if status and it['status'] != status:
                        continue
                    if work_id and it['workId'] != work_id:
                        continue
                    if batch_id and it['batchId'] != batch_id:
                        continue
                    filtered.append(it)

                global_counts = self._derive_batch_counts(all_items)
                return {
                    'schemaVersion': self.schema_version(),
                    'executorActive': self._has_lease,
                    'counts': global_counts,
                    'batches': batches,
                    'items': filtered,
                }
            finally:
                conn.close()

    def export_batch_summary(self, batch_id):
        batch = self.get_batch(batch_id)
        batch['exportedSummaryAt'] = now_iso()
        return batch

    # ---- Cancelamento e nova tentativa ----
    def cancel_item(self, item_id):
        now = now_iso()
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute('BEGIN IMMEDIATE')
                row = conn.execute('SELECT * FROM queue_items WHERE item_id=?', (item_id,)).fetchone()
                if row is None:
                    conn.execute('ROLLBACK')
                    raise ValueError(f'item desconhecido: {item_id}')
                if row['status'] != 'queued':
                    conn.execute('ROLLBACK')
                    raise ValueError(f'apenas itens na fila (queued) podem ser cancelados (estado atual: {row["status"]})')
                cur = conn.execute('''
                    UPDATE queue_items
                    SET status='cancelled', finished_at=?, updated_at=?, error_code='CANCELLED_BY_USER',
                        error_message='Cancelado pelo operador antes da execucao.'
                    WHERE item_id=? AND status='queued'
                ''', (now, now, item_id))
                if cur.rowcount != 1:
                    conn.execute('ROLLBACK')
                    raise ValueError('item nao estava mais pendente para cancelamento')
                conn.execute('UPDATE batches SET updated_at=? WHERE batch_id=?', (now, row['batch_id']))
                conn.execute('COMMIT')
            except Exception:
                conn.execute('ROLLBACK')
                raise
            finally:
                conn.close()
        return self.get_item(item_id)

    def _validate_snapshot_inputs(self, snapshot):
        work_id = snapshot.get('workId')
        modality = snapshot.get('modality')
        profile_id = snapshot.get('profileId')
        project_rel = snapshot.get('project')
        try:
            self.studio.load_work(work_id)
        except Exception as exc:
            raise QueueConflictError('SNAPSHOT_UNAVAILABLE', f'Trabalho {work_id} indisponivel: {exc}', can_use_current=False)

        video_profiles, image_profiles, _ = self._catalog_for_project(project_rel)
        if modality == 'carousel':
            if profile_id not in image_profiles:
                raise QueueConflictError('SNAPSHOT_UNAVAILABLE', f'Perfil de carrossel {profile_id} nao esta mais permitido no catalogo.', can_use_current=True)
        else:
            if profile_id not in video_profiles:
                raise QueueConflictError('SNAPSHOT_UNAVAILABLE', f'Perfil de video {profile_id} nao esta mais permitido no catalogo.', can_use_current=True)
            if modality == 'motion' and video_profiles[profile_id].get('aspectRatio') != '9:16':
                raise QueueConflictError('SNAPSHOT_UNAVAILABLE', f'Perfil {profile_id} nao suporta Motion 9:16.', can_use_current=True)

        for mo in snapshot.get('mediaOrigins') or []:
            rel_path = mo.get('path')
            expected_sha = mo.get('sha256')
            if not rel_path:
                continue
            try:
                abs_path = self.studio.confine(rel_path)
            except ValueError:
                raise QueueConflictError('MEDIA_DIVERGENCE', f'Caminho de midia fora da raiz: {rel_path}', can_use_current=True)
            if not os.path.isfile(render_local.fs_path(abs_path)):
                raise QueueConflictError(
                    'MEDIA_DIVERGENCE',
                    f'Midia ausente desde o enfileiramento ({mo.get("mediaId") or rel_path}). Enfileire a versao atual ou restaure o arquivo.',
                    can_use_current=True,
                )
            if expected_sha:
                actual_sha = render_local.sha256_file(abs_path)
                if actual_sha != expected_sha:
                    raise QueueConflictError(
                        'MEDIA_DIVERGENCE',
                        f'Midia modificada desde o enfileiramento ({mo.get("mediaId") or rel_path}). Enfileire a versao atual para usar os novos bytes.',
                        can_use_current=True,
                    )

    def retry_item(self, item_id, use_current=False):
        now = now_iso()
        with self._db_lock:
            conn = self._connect()
            try:
                row = conn.execute('SELECT * FROM queue_items WHERE item_id=?', (item_id,)).fetchone()
                if row is None:
                    raise ValueError(f'item desconhecido: {item_id}')
                if row['status'] not in ('failed', 'interrupted'):
                    raise ValueError(f'apenas itens falhos ou interrompidos podem ser reexecutados (estado atual: {row["status"]})')
                snap = json.loads(row['snapshot_json'])
                snap_sha = row['snapshot_sha256']
            finally:
                conn.close()

        if use_current:
            snap, snap_sha = self._build_frozen_snapshot(row['work_id'], row['modality'], row['profile_id'])
        else:
            self._validate_snapshot_inputs(snap)

        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute('BEGIN IMMEDIATE')
                cur = conn.execute('''
                    UPDATE queue_items
                    SET status='queued', snapshot_json=?, snapshot_sha256=?,
                        error_code=NULL, error_message=NULL, started_at=NULL, finished_at=NULL, updated_at=?
                    WHERE item_id=? AND status IN ('failed', 'interrupted')
                ''', (json.dumps(snap, ensure_ascii=False), snap_sha, now, item_id))
                if cur.rowcount != 1:
                    conn.execute('ROLLBACK')
                    raise ValueError('item mudou de estado antes da nova tentativa')
                conn.execute('UPDATE batches SET updated_at=? WHERE batch_id=?', (now, row['batch_id']))
                conn.execute('COMMIT')
            except Exception:
                conn.execute('ROLLBACK')
                raise
            finally:
                conn.close()

        self._wake_event.set()
        return self.get_item(item_id)

    # ---- Recuperacao apos reinicio / queda ----
    def _revoke_fence(self, fence_path):
        if not fence_path:
            return
        try:
            os.makedirs(os.path.dirname(fence_path), exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix='.fence-', suffix='.tmp', dir=os.path.dirname(fence_path))
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump({'revoked': True, 'revokedAt': now_iso()}, handle)
            os.replace(tmp, fence_path)
        except OSError:
            pass

    def _verify_attempt_promotion(self, item_row, attempt_row):
        """Comprova se o destino possui promocao valida pertencente exatamente a attempt_id."""
        attempt_id = attempt_row['attempt_id']
        output_rel = item_row['output_dir']
        modality = item_row['modality']
        profile_id = item_row['profile_id']
        fs = render_local.fs_path
        try:
            out_abs = self.studio.confine_workspace(output_rel)
        except ValueError:
            return None

        if modality == 'carousel':
            manifest_abs = os.path.join(out_abs, 'carousel-manifest.json')
            if not os.path.isfile(fs(manifest_abs)):
                return None
            try:
                with open(fs(manifest_abs), 'r', encoding='utf-8') as handle:
                    manifest = json.load(handle)
            except (OSError, ValueError):
                return None
            if manifest.get('attemptId') != attempt_id or manifest.get('profileId') != profile_id:
                return None
            for card in manifest.get('cards') or []:
                cpath = card.get('path')
                csha = card.get('sha256')
                if not cpath or not csha:
                    return None
                cabs = self.studio.confine_workspace(cpath)
                if not os.path.isfile(fs(cabs)) or render_local.sha256_file(cabs) != csha:
                    return None
            zinfo = manifest.get('zip') or {}
            if zinfo.get('path'):
                zabs = self.studio.confine_workspace(zinfo['path'])
                if not os.path.isfile(fs(zabs)) or render_local.sha256_file(zabs) != zinfo.get('sha256'):
                    return None
            # Reconcilia index.json caso a queda tenha ocorrido antes ou durante sua gravacao
            index_abs = os.path.join(out_abs, 'index.json')
            needs_index = True
            if os.path.isfile(fs(index_abs)):
                try:
                    with open(fs(index_abs), 'r', encoding='utf-8') as handle:
                        idx = json.load(handle)
                    if (idx.get('lastValidDelivery') or {}).get('attemptId') == attempt_id:
                        needs_index = False
                except (OSError, ValueError):
                    needs_index = True
            if needs_index:
                manifest_rel = self.studio.rel(manifest_abs)
                index_payload = {
                    'schemaVersion': 1,
                    'requestId': manifest.get('requestId'),
                    'lastAttempt': {'status': 'completed', 'manifest': manifest_rel, 'attemptId': attempt_id},
                    'lastValidDelivery': {'status': 'completed', 'manifest': manifest_rel, 'cardCount': len(manifest.get('cards') or []), 'attemptId': attempt_id},
                }
                fd, tmp = tempfile.mkstemp(prefix='.index-', suffix='.tmp', dir=out_abs)
                with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
                    json.dump(index_payload, handle, ensure_ascii=False, indent=2)
                    handle.write('\n')
                os.replace(tmp, index_abs)
            return {
                'manifestAbs': manifest_abs,
                'manifestRel': self.studio.rel(manifest_abs),
                'manifestSha256': render_local.sha256_file(manifest_abs),
                'result': {'status': 'completed', 'profileId': profile_id},
            }

        # Video ou Motion
        manifest_abs = os.path.join(out_abs, profile_id, 'delivery-manifest.json')
        if not os.path.isfile(fs(manifest_abs)):
            return None
        try:
            with open(fs(manifest_abs), 'r', encoding='utf-8') as handle:
                manifest = json.load(handle)
        except (OSError, ValueError):
            return None
        if manifest.get('attemptId') != attempt_id:
            return None
        artifacts = manifest.get('artifacts') or {}
        for key in ('video', 'srt', 'narration'):
            art = artifacts.get(key)
            if not isinstance(art, dict) or not art.get('path') or not art.get('sha256'):
                return None
            art_abs = self.studio.confine_workspace(art['path'])
            if not os.path.isfile(fs(art_abs)) or render_local.sha256_file(art_abs) != art['sha256']:
                return None
        # Reconcilia index.json a partir dos manifestos caso necessario
        index_abs = os.path.join(out_abs, 'index.json')
        needs_index = True
        if os.path.isfile(fs(index_abs)):
            try:
                with open(fs(index_abs), 'r', encoding='utf-8') as handle:
                    idx = json.load(handle)
                entry = next((p for p in (idx.get('profiles') or []) if p.get('profileId') == profile_id), None)
                if entry and (entry.get('lastValidDelivery') or {}).get('attemptId') == attempt_id:
                    needs_index = False
            except (OSError, ValueError):
                needs_index = True
        if needs_index:
            snap = json.loads(item_row['snapshot_json'])
            req_id = (snap.get('request') or {}).get('id') or item_row['work_id']
            produce_video.reconcile_index_from_manifests(out_abs, req_id)
        return {
            'manifestAbs': manifest_abs,
            'manifestRel': self.studio.rel(manifest_abs),
            'manifestSha256': render_local.sha256_file(manifest_abs),
            'result': {'status': 'completed', 'profiles': [{'profileId': profile_id, 'status': 'completed'}]},
        }

    def _record_review_for_item(self, item_row, attempt_id, result_payload):
        snap = json.loads(item_row['snapshot_json'])
        lineage_job = {
            'jobId': attempt_id,
            'workId': item_row['work_id'],
            'status': 'completed',
            'outputDir': item_row['output_dir'],
            'profile': item_row['profile_id'],
            'kind': 'carousel' if item_row['modality'] == 'carousel' else 'video',
            'result': result_payload,
            'exportLineage': {
                'modality': item_row['modality'],
                'request': snap.get('request'),
                'motionPlan': snap.get('motionPlan'),
                'mediaOrigins': snap.get('mediaOrigins') or [],
            },
        }
        res = studio_review.record_export_lineage(self.studio, lineage_job) or {}
        piece_key = f"{item_row['modality']}:{item_row['profile_id']}"
        return (res.get('versionIds') or {}).get(piece_key)

    def recover_on_startup(self):
        """Reconcilia itens em running encontrados apos reinicio ou queda do servidor."""
        with self._db_lock:
            conn = self._connect()
            try:
                running_rows = conn.execute(
                    "SELECT * FROM queue_items WHERE status='running' ORDER BY created_at ASC, position ASC"
                ).fetchall()
            finally:
                conn.close()

        for item_row in running_rows:
            attempt_id = item_row['last_attempt_id']
            attempt_row = None
            if attempt_id:
                with self._db_lock:
                    conn = self._connect()
                    try:
                        attempt_row = conn.execute(
                            'SELECT * FROM queue_attempts WHERE attempt_id=?', (attempt_id,)
                        ).fetchone()
                    finally:
                        conn.close()

            if attempt_row is not None and attempt_row['fence_path']:
                self._revoke_fence(attempt_row['fence_path'])
            if attempt_row is not None and attempt_row['pid'] and _pid_is_alive(int(attempt_row['pid'])):
                # Aguarda brevemente o processo orfao encerrar apos revogacao da cerca
                deadline = time.monotonic() + 2.0
                while time.monotonic() < deadline and _pid_is_alive(int(attempt_row['pid'])):
                    time.sleep(0.1)

            proven = self._verify_attempt_promotion(item_row, attempt_row) if attempt_row else None
            now = now_iso()
            if proven is not None:
                delivery_version_id = self._record_review_for_item(item_row, attempt_id, proven['result'])
                self.studio._write_export_status(item_row['output_dir'], {
                    'jobId': attempt_id,
                    'kind': 'carousel' if item_row['modality'] == 'carousel' else 'video',
                    'profile': item_row['profile_id'],
                    'outputDir': item_row['output_dir'],
                    'workId': item_row['work_id'],
                    'status': 'completed',
                    'returncode': 0,
                    'result': proven['result'],
                    'finishedAt': now,
                })
                with self._db_lock:
                    conn = self._connect()
                    try:
                        conn.execute('BEGIN IMMEDIATE')
                        conn.execute('''
                            UPDATE queue_attempts
                            SET status='completed', finished_at=?, promoted_manifest_path=?,
                                promoted_manifest_sha256=?, delivery_version_id=?
                            WHERE attempt_id=?
                        ''', (now, proven['manifestRel'], proven['manifestSha256'], delivery_version_id, attempt_id))
                        conn.execute('''
                            UPDATE queue_items
                            SET status='completed', finished_at=?, updated_at=?,
                                error_code=NULL, error_message=NULL,
                                delivery_version_id=?, delivery_manifest_path=?, delivery_manifest_sha256=?
                            WHERE item_id=?
                        ''', (now, now, delivery_version_id, proven['manifestRel'], proven['manifestSha256'], item_row['item_id']))
                        conn.execute('UPDATE batches SET updated_at=? WHERE batch_id=?', (now, item_row['batch_id']))
                        conn.execute('COMMIT')
                    except Exception:
                        conn.execute('ROLLBACK')
                        raise
                    finally:
                        conn.close()
            else:
                err_msg = 'Execucao interrompida antes da promocao comprovada; entrega anterior preservada.'
                self.studio._write_export_status(item_row['output_dir'], {
                    'jobId': attempt_id,
                    'kind': 'carousel' if item_row['modality'] == 'carousel' else 'video',
                    'profile': item_row['profile_id'],
                    'outputDir': item_row['output_dir'],
                    'workId': item_row['work_id'],
                    'status': 'interrupted',
                    'error': err_msg,
                    'interruptedAt': now,
                })
                with self._db_lock:
                    conn = self._connect()
                    try:
                        conn.execute('BEGIN IMMEDIATE')
                        if attempt_id:
                            conn.execute('''
                                UPDATE queue_attempts
                                SET status='interrupted', finished_at=?, error_code='INTERRUPTED_INCONCLUSIVE',
                                    error_message=?
                                WHERE attempt_id=?
                            ''', (now, err_msg, attempt_id))
                        conn.execute('''
                            UPDATE queue_items
                            SET status='interrupted', finished_at=?, updated_at=?,
                                error_code='INTERRUPTED_INCONCLUSIVE', error_message=?
                            WHERE item_id=?
                        ''', (now, now, err_msg, item_row['item_id']))
                        conn.execute('UPDATE batches SET updated_at=? WHERE batch_id=?', (now, item_row['batch_id']))
                        conn.execute('COMMIT')
                    except Exception:
                        conn.execute('ROLLBACK')
                        raise
                    finally:
                        conn.close()

    # ---- Execucao em serie ----
    def _claim_next_item(self):
        now = now_iso()
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute('BEGIN IMMEDIATE')
                candidates = conn.execute(
                    "SELECT * FROM queue_items WHERE status='queued' ORDER BY created_at ASC, position ASC"
                ).fetchall()
                for row in candidates:
                    if self.studio.is_single_export_active(row['output_dir']):
                        continue
                    attempt_num = conn.execute(
                        'SELECT COALESCE(MAX(attempt_number), 0) + 1 FROM queue_attempts WHERE item_id=?',
                        (row['item_id'],),
                    ).fetchone()[0]
                    attempt_id = f'att-{uuid.uuid4().hex[:12]}'
                    staging_dir = os.path.join(self.studio.root, '.workspace', 'tmp', f'queue-{attempt_id}')
                    fence_path = os.path.join(self.fences_dir, f'{attempt_id}.fence')
                    cur = conn.execute('''
                        UPDATE queue_items
                        SET status='running', started_at=?, finished_at=NULL, updated_at=?,
                            error_code=NULL, error_message=NULL, last_attempt_id=?
                        WHERE item_id=? AND status='queued'
                    ''', (now, now, attempt_id, row['item_id']))
                    if cur.rowcount != 1:
                        continue
                    conn.execute('''
                        INSERT INTO queue_attempts (
                            attempt_id, item_id, attempt_number, snapshot_sha256, snapshot_source,
                            status, fence_path, staging_dir, started_at
                        ) VALUES (?, ?, ?, ?, 'frozen', 'running', ?, ?, ?)
                    ''', (attempt_id, row['item_id'], attempt_num, row['snapshot_sha256'], fence_path, staging_dir, now))
                    conn.execute('UPDATE batches SET updated_at=? WHERE batch_id=?', (now, row['batch_id']))
                    conn.execute('COMMIT')
                    claimed = conn.execute('SELECT * FROM queue_items WHERE item_id=?', (row['item_id'],)).fetchone()
                    attempt = conn.execute('SELECT * FROM queue_attempts WHERE attempt_id=?', (attempt_id,)).fetchone()
                    return claimed, attempt
                conn.execute('COMMIT')
                return None, None
            except Exception:
                conn.execute('ROLLBACK')
                raise
            finally:
                conn.close()

    def _finish_failed_item(self, item_row, attempt_row, status, error_code, error_message):
        now = now_iso()
        self.studio._write_export_status(item_row['output_dir'], {
            'jobId': attempt_row['attempt_id'],
            'kind': 'carousel' if item_row['modality'] == 'carousel' else 'video',
            'profile': item_row['profile_id'],
            'outputDir': item_row['output_dir'],
            'workId': item_row['work_id'],
            'status': status,
            'error': error_message,
            'finishedAt': now,
        })
        with self._db_lock:
            conn = self._connect()
            try:
                conn.execute('BEGIN IMMEDIATE')
                conn.execute('''
                    UPDATE queue_attempts
                    SET status=?, finished_at=?, error_code=?, error_message=?
                    WHERE attempt_id=?
                ''', (status, now, error_code, error_message, attempt_row['attempt_id']))
                conn.execute('''
                    UPDATE queue_items
                    SET status=?, finished_at=?, updated_at=?, error_code=?, error_message=?
                    WHERE item_id=?
                ''', (status, now, now, error_code, error_message, item_row['item_id']))
                conn.execute('UPDATE batches SET updated_at=? WHERE batch_id=?', (now, item_row['batch_id']))
                conn.execute('COMMIT')
            except Exception:
                conn.execute('ROLLBACK')
                raise
            finally:
                conn.close()

    def _execute_item(self, item_row, attempt_row):
        attempt_id = attempt_row['attempt_id']
        staging_dir = attempt_row['staging_dir']
        fence_path = attempt_row['fence_path']
        snap = json.loads(item_row['snapshot_json'])

        self._set_active_destination(item_row['output_dir'], item_row['item_id'], attempt_id)
        try:
            # 1. Revalidacao dos insumos congelados antes de rodar FFmpeg
            try:
                self._validate_snapshot_inputs(snap)
            except QueueConflictError as exc:
                self._finish_failed_item(item_row, attempt_row, 'failed', exc.code, exc.message)
                return

            os.makedirs(staging_dir, exist_ok=True)
            with open(fence_path, 'w', encoding='utf-8') as handle:
                json.dump({'attemptId': attempt_id, 'itemId': item_row['item_id'], 'revoked': False}, handle)

            req_path = os.path.join(staging_dir, 'request.json')
            with open(req_path, 'w', encoding='utf-8', newline='\n') as handle:
                json.dump(snap['request'], handle, ensure_ascii=False, indent=2)

            output_abs = self.studio.confine_workspace(item_row['output_dir'])
            tool_name = 'produce_carousel.py' if item_row['modality'] == 'carousel' else 'produce_video.py'
            cmd = [
                sys.executable,
                os.path.join(self.studio.tools, tool_name),
                '--input', req_path,
                '--root', self.studio.root,
                '--output-dir', output_abs,
                '--profile', item_row['profile_id'],
                '--attempt-id', attempt_id,
                '--fence-file', fence_path,
                '--json',
            ]
            if item_row['modality'] != 'carousel':
                cmd.extend(['--staging', os.path.join(staging_dir, 'render')])
                if item_row['modality'] == 'motion' and snap.get('motionPlan'):
                    plan_path = os.path.join(staging_dir, 'motion.plan.json')
                    with open(plan_path, 'w', encoding='utf-8', newline='\n') as handle:
                        json.dump(snap['motionPlan'], handle, ensure_ascii=False, indent=2)
                    cmd.extend(['--motion-plan', plan_path])

            out_log = os.path.join(staging_dir, 'stdout.json')
            err_log = os.path.join(staging_dir, 'stderr.log')
            with open(out_log, 'w', encoding='utf-8') as out_h, open(err_log, 'w', encoding='utf-8') as err_h:
                proc = subprocess.Popen(
                    cmd, stdout=out_h, stderr=err_h, stdin=subprocess.DEVNULL,
                    text=True, encoding='utf-8', errors='replace',
                )
                with self._db_lock:
                    conn = self._connect()
                    try:
                        conn.execute('BEGIN IMMEDIATE')
                        conn.execute('UPDATE queue_attempts SET pid=? WHERE attempt_id=?', (proc.pid, attempt_id))
                        conn.execute('COMMIT')
                    finally:
                        conn.close()
                if self._test_on_attempt_started is not None:
                    self._test_on_attempt_started(item_row, attempt_row, proc)
                try:
                    code = proc.wait(timeout=EXPORT_TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                    self._finish_failed_item(
                        item_row, attempt_row, 'failed', 'EXPORT_TIMEOUT',
                        f'Tempo limite ({EXPORT_TIMEOUT_SECONDS}s) excedido ao exportar {item_row["profile_id"]}.',
                    )
                    return

            try:
                with open(out_log, 'r', encoding='utf-8') as handle:
                    result = json.load(handle)
            except (OSError, ValueError):
                result = {}
            try:
                with open(err_log, 'r', encoding='utf-8') as handle:
                    err_text = handle.read().strip()
            except OSError:
                err_text = ''

            if code != 0:
                err_summary = (
                    result.get('error')
                    or next(
                        (p.get('failureCode') or p.get('error')
                         for p in (result.get('profiles') or [])
                         if isinstance(p, dict) and p.get('status') != 'completed'),
                        None,
                    )
                    or err_text
                    or f'exportacao falhou (codigo {code})'
                )
                err_code = 'QUEUE_FENCE_REVOKED' if 'QUEUE_FENCE_REVOKED' in err_summary else 'EXPORT_FAILED'
                st = 'interrupted' if err_code == 'QUEUE_FENCE_REVOKED' else 'failed'
                self._finish_failed_item(item_row, attempt_row, st, err_code, err_summary)
                return

            if self._test_before_record_completion is not None:
                self._test_before_record_completion(item_row, attempt_row)

            proven = self._verify_attempt_promotion(item_row, attempt_row)
            if proven is None:
                self._finish_failed_item(
                    item_row, attempt_row, 'failed', 'MANIFEST_VERIFICATION_FAILED',
                    'Promocao concluida sem manifesto ou artefatos verificaveis para esta tentativa.',
                )
                return

            delivery_version_id = self._record_review_for_item(item_row, attempt_id, result or proven['result'])
            now = now_iso()
            self.studio._write_export_status(item_row['output_dir'], {
                'jobId': attempt_id,
                'kind': 'carousel' if item_row['modality'] == 'carousel' else 'video',
                'profile': item_row['profile_id'],
                'outputDir': item_row['output_dir'],
                'workId': item_row['work_id'],
                'status': 'completed',
                'returncode': 0,
                'result': result or proven['result'],
                'finishedAt': now,
            })
            with self._db_lock:
                conn = self._connect()
                try:
                    conn.execute('BEGIN IMMEDIATE')
                    conn.execute('''
                        UPDATE queue_attempts
                        SET status='completed', finished_at=?, promoted_manifest_path=?,
                            promoted_manifest_sha256=?, delivery_version_id=?
                        WHERE attempt_id=?
                    ''', (now, proven['manifestRel'], proven['manifestSha256'], delivery_version_id, attempt_id))
                    conn.execute('''
                        UPDATE queue_items
                        SET status='completed', finished_at=?, updated_at=?,
                            error_code=NULL, error_message=NULL,
                            delivery_version_id=?, delivery_manifest_path=?, delivery_manifest_sha256=?
                        WHERE item_id=?
                    ''', (now, now, delivery_version_id, proven['manifestRel'], proven['manifestSha256'], item_row['item_id']))
                    conn.execute('UPDATE batches SET updated_at=? WHERE batch_id=?', (now, item_row['batch_id']))
                    conn.execute('COMMIT')
                except Exception:
                    conn.execute('ROLLBACK')
                    raise
                finally:
                    conn.close()
        finally:
            self._set_active_destination(None)
            shutil.rmtree(staging_dir, ignore_errors=True)
            if fence_path and os.path.exists(fence_path):
                try:
                    os.remove(fence_path)
                except OSError:
                    pass

    def run_once(self):
        """Executa no maximo um item pendente se este executor detiver o lease."""
        if not self._has_lease and not self.acquire_executor_lease():
            return False
        self.refresh_executor_lease()
        item_row, attempt_row = self._claim_next_item()
        if item_row is None:
            return False
        self._execute_item(item_row, attempt_row)
        return True

    def _worker_loop(self):
        while not self._stop_event.is_set():
            try:
                did_work = self.run_once()
                if did_work:
                    continue
            except Exception:
                pass
            self._wake_event.wait(timeout=0.5)
            self._wake_event.clear()
