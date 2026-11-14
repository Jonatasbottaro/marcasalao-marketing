"""Ficha editorial, revisao humana vinculada a versao e rastreio de entregas do Studio.

Reaproveita a estrutura de trabalhos em ``work_paths``, grava ``editorial.json`` e
``review-state.json`` de forma atomica dentro de ``<RAIZ>`` e mantém estrita
separacao entre legendas queimadas/SRT, roteiro de narracao e textos por canal.
"""

import hashlib
import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone

import render_local

EDITORIAL_FIELDS = (
    'objective',
    'audience',
    'coreMessage',
    'supportEvidence',
    'hook',
    'scriptSummary',
    'cta',
)

CHANNEL_COPY_FIELDS = (
    'title',
    'postText',
    'cta',
    'destinationUrl',
    'hashtags',
)

MODALITIES = ('video', 'carousel', 'motion')

MODALITY_LABELS = {
    'video': 'Vídeo',
    'carousel': 'Carrossel',
    'motion': 'Motion',
}

DECISION_LABELS = {
    'approved_for_local_delivery': 'Aprovado para entrega local',
    'changes_requested': 'Ajuste solicitado',
}

ARTIFACT_TEXT_KINDS = {
    'srt': 'srt',
    'narration': 'narration',
}

_STATE_LOCK = threading.RLock()


class ReviewVersionConflictError(Exception):
    """Conflito otimista de versao ou texto alterado antes da confirmacao humana."""


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def atomic_write_json(target, value):
    """Grava JSON UTF-8 LF com flush/fsync e os.replace usando fs_path no Windows."""
    fs = render_local.fs_path
    parent = os.path.dirname(os.path.abspath(target))
    os.makedirs(fs(parent), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.tmp-rev-', suffix='.json', dir=fs(parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(tmp, fs(target))
    except OSError:
        if os.path.exists(fs(tmp)):
            os.remove(fs(tmp))
        raise


def canonical_json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def canonical_sha256(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def merged_work_paths(studio, work_id, work_doc=None):
    base = studio.work_paths(work_id)
    work_dir = base['workDir']
    defaults = {
        **base,
        'editorialFile': base.get('editorialFile') or f'{work_dir}/editorial.json',
        'reviewStateFile': base.get('reviewStateFile') or f'{work_dir}/review-state.json',
        'packageDeliveryDir': base.get('packageDeliveryDir') or f'{work_dir}/deliveries/package',
    }
    if isinstance(work_doc, dict) and isinstance(work_doc.get('paths'), dict):
        merged = dict(defaults)
        merged.update(work_doc['paths'])
        return merged
    return defaults


def _read_json_safe(path, default=None):
    fs = render_local.fs_path
    if not path or not os.path.isfile(fs(path)):
        return default
    with open(fs(path), 'r', encoding='utf-8') as handle:
        return json.load(handle)


def empty_briefing():
    return {field: '' for field in EDITORIAL_FIELDS}


def normalize_briefing(raw):
    src = raw if isinstance(raw, dict) else {}
    return {field: str(src.get(field) or '').strip() for field in EDITORIAL_FIELDS}


def normalize_channel_copy(profile_id, raw, updated_at=None):
    src = raw if isinstance(raw, dict) else {}
    normalized = {
        'profileId': profile_id,
        'title': str(src.get('title') or '').strip(),
        'postText': str(src.get('postText') or '').strip(),
        'cta': str(src.get('cta') or '').strip(),
        'destinationUrl': str(src.get('destinationUrl') or '').strip(),
        'hashtags': str(src.get('hashtags') or '').strip(),
    }
    copy_payload = {k: normalized[k] for k in ('profileId',) + CHANNEL_COPY_FIELDS}
    normalized['copySha256'] = canonical_sha256(copy_payload)
    normalized['isEmpty'] = not any(normalized[field] for field in CHANNEL_COPY_FIELDS)
    normalized['updatedAt'] = updated_at
    return normalized


def _hash_media_list(studio, media_items):
    entries = []
    if not isinstance(media_items, list):
        return entries
    for item in media_items:
        if not isinstance(item, dict):
            continue
        rel_path = str(item.get('path') or '').strip()
        sha = None
        size = None
        missing = True
        confined = True
        if rel_path:
            try:
                abs_path = studio.confine(rel_path)
                if os.path.isfile(render_local.fs_path(abs_path)):
                    sha = render_local.sha256_file(abs_path)
                    size = os.path.getsize(render_local.fs_path(abs_path))
                    missing = False
            except (ValueError, OSError):
                confined = False
        entries.append({
            'id': item.get('id'),
            'path': rel_path,
            'type': item.get('type'),
            'origin': item.get('origin'),
            'license': item.get('license'),
            'sha256': sha,
            'bytes': size,
            'missing': missing,
            'confined': confined,
        })
    return entries


def _effective_video_slice(video_req, profile_id=None):
    src = dict(video_req) if isinstance(video_req, dict) else {}
    profiles = src.pop('profiles', []) or []
    if profile_id is not None:
        src['profileSelected'] = profile_id in profiles
    else:
        src['profiles'] = list(profiles)
    return src


def _effective_carousel_slice(carousel_req, profile_id=None):
    src = dict(carousel_req) if isinstance(carousel_req, dict) else {}
    if profile_id is not None:
        src['profileSelected'] = src.get('profile') == profile_id
    return src


def compute_draft_snapshot(studio, modality, video_req, carousel_req, motion_plan, profile_id=None):
    if modality == 'carousel':
        req_slice = _effective_carousel_slice(carousel_req, profile_id=profile_id)
        media_items = (carousel_req or {}).get('media', [])
        payload = {
            'modality': 'carousel',
            'request': req_slice,
            'mediaFiles': _hash_media_list(studio, media_items),
        }
    else:
        req_slice = _effective_video_slice(video_req, profile_id=profile_id)
        media_items = (video_req or {}).get('media', [])
        payload = {
            'modality': modality,
            'request': req_slice,
            'mediaFiles': _hash_media_list(studio, media_items),
        }
        if modality == 'motion':
            payload['motionPlan'] = motion_plan if isinstance(motion_plan, dict) else {}
    return canonical_sha256(payload), payload


def _read_work_core(studio, work_id):
    base_paths = studio.work_paths(work_id)
    work_abs = studio.confine_workspace(base_paths['workFile'])
    work_doc = _read_json_safe(work_abs)
    if not isinstance(work_doc, dict):
        raise ValueError(f'trabalho nao encontrado: {work_id}')
    wpaths = merged_work_paths(studio, work_id, work_doc)
    video_req = _read_json_safe(studio.confine_workspace(wpaths['videoDraft'])) or {}
    carousel_req = _read_json_safe(studio.confine_workspace(wpaths['carouselDraft'])) or {}
    motion_plan = _read_json_safe(studio.confine_workspace(wpaths['motionPlan'])) or {}
    listing = studio.list_profiles(work_doc['project'])
    return work_doc, wpaths, video_req, carousel_req, motion_plan, listing


def _load_editorial_doc(studio, work_id, wpaths):
    path = studio.confine_workspace(wpaths['editorialFile'])
    raw = _read_json_safe(path)
    exists = isinstance(raw, dict)
    raw = raw if exists else {}
    channels = {}
    if isinstance(raw.get('channels'), dict):
        for pid, entry in raw['channels'].items():
            channels[pid] = normalize_channel_copy(
                pid,
                entry,
                updated_at=entry.get('updatedAt') if isinstance(entry, dict) else None,
            )
    return {
        'schemaVersion': 1,
        'workId': work_id,
        'updatedAt': raw.get('updatedAt'),
        'briefing': normalize_briefing(raw.get('briefing')),
        'channels': channels,
        'existsOnDisk': exists,
    }


def _load_review_state(studio, work_id, wpaths):
    path = studio.confine_workspace(wpaths['reviewStateFile'])
    raw = _read_json_safe(path)
    if not isinstance(raw, dict):
        raw = {}
    return {
        'schemaVersion': 1,
        'workId': work_id,
        'exportsSeq': int(raw.get('exportsSeq') or 0),
        'pieces': dict(raw.get('pieces') or {}),
        'channels': dict(raw.get('channels') or {}),
    }


def _save_review_state(studio, wpaths, state):
    path = studio.confine_workspace(wpaths['reviewStateFile'])
    atomic_write_json(path, state)


def _merge_media_origins(recorded_origins, report_doc, request_doc):
    by_id = {}
    if isinstance(request_doc, dict):
        for item in request_doc.get('media') or []:
            if isinstance(item, dict) and item.get('id'):
                by_id[item['id']] = {
                    'mediaId': item.get('id'),
                    'path': item.get('path'),
                    'type': item.get('type'),
                    'origin': item.get('origin'),
                    'license': item.get('license'),
                }
    merged = []
    seen = set()
    for src_list in (recorded_origins or [], (report_doc or {}).get('assets') or []):
        for item in src_list:
            if not isinstance(item, dict):
                continue
            mid = item.get('mediaId') or item.get('id') or item.get('beatId')
            path = item.get('path')
            key = (mid, path)
            if key in seen:
                continue
            seen.add(key)
            extra = by_id.get(mid) or {}
            entry = {
                'mediaId': mid,
                'path': path or extra.get('path'),
                'type': item.get('type') or extra.get('type'),
                'origin': item.get('origin') or extra.get('origin'),
                'license': item.get('license') or extra.get('license'),
                'sha256': item.get('sha256'),
            }
            if any(entry.get(k) for k in ('mediaId', 'path', 'origin', 'license', 'sha256')):
                merged.append(entry)
    if not merged and by_id:
        for mid, entry in by_id.items():
            merged.append(dict(entry))
    return merged


def _verify_manifest_file(studio, rel_path, expected_sha=None):
    fs = render_local.fs_path
    if not rel_path or not isinstance(rel_path, str):
        return False, None, 'caminho ausente no manifesto', None, None
    try:
        abs_path = studio.confine(rel_path)
    except ValueError as exc:
        return False, None, str(exc), None, None
    if not os.path.isfile(fs(abs_path)):
        return False, abs_path, f'arquivo ausente: {rel_path}', None, None
    actual_sha = render_local.sha256_file(abs_path)
    actual_bytes = os.path.getsize(fs(abs_path))
    if expected_sha and actual_sha != expected_sha:
        return False, abs_path, f'SHA-256 divergente em {rel_path}', actual_sha, actual_bytes
    return True, abs_path, None, actual_sha, actual_bytes


def record_export_lineage(studio, job):
    """Vincula cada entrega concluida no trabalho ao snapshot exato enviado ao exportador."""
    work_id = job.get('workId')
    lineage = job.get('exportLineage')
    if not work_id or not isinstance(lineage, dict):
        return None
    if job.get('status') != 'completed':
        return None

    with _STATE_LOCK:
        work_doc, wpaths, _, _, _, _ = _read_work_core(studio, work_id)
        state = _load_review_state(studio, work_id, wpaths)
        modality = lineage['modality']
        req_snapshot = lineage['request']
        motion_snapshot = lineage.get('motionPlan')
        media_origins = lineage.get('mediaOrigins') or []
        out_dir_abs = studio.confine_workspace(job['outputDir'])
        fs = render_local.fs_path
        updated_keys = []

        if modality == 'carousel':
            manifest_abs = os.path.join(out_dir_abs, 'carousel-manifest.json')
            manifest = _read_json_safe(manifest_abs)
            if isinstance(manifest, dict) and manifest.get('profileId'):
                profile_id = manifest['profileId']
                cards_meta = []
                for card in manifest.get('cards') or []:
                    cards_meta.append({
                        'order': card.get('order'),
                        'id': card.get('id'),
                        'file': card.get('file'),
                        'path': card.get('path'),
                        'sha256': card.get('sha256'),
                        'bytes': card.get('bytes'),
                    })
                zip_info = manifest.get('zip') or {}
                artifacts_fp = canonical_sha256({
                    'modality': 'carousel',
                    'profileId': profile_id,
                    'cards': cards_meta,
                    'zip': {'path': zip_info.get('path'), 'sha256': zip_info.get('sha256')},
                })
                draft_fp, _ = compute_draft_snapshot(
                    studio, 'carousel', None, req_snapshot, None, profile_id=profile_id
                )
                state['exportsSeq'] += 1
                seq = state['exportsSeq']
                delivery_version_id = f'carousel-{profile_id}-v{seq}-{artifacts_fp[:8]}'
                piece_key = f'carousel:{profile_id}'
                piece_state = state['pieces'].setdefault(piece_key, {
                    'modality': 'carousel',
                    'profileId': profile_id,
                    'versions': [],
                    'decisions': [],
                })
                piece_state['versions'].append({
                    'deliveryVersionId': delivery_version_id,
                    'seq': seq,
                    'exportedAt': now_iso(),
                    'jobId': job.get('jobId'),
                    'modality': 'carousel',
                    'profileId': profile_id,
                    'requestId': manifest.get('requestId'),
                    'manifestPath': studio.rel(manifest_abs),
                    'manifestSha256': render_local.sha256_file(manifest_abs),
                    'artifactsFingerprint': artifacts_fp,
                    'draftFingerprint': draft_fp,
                    'requestSha256': canonical_sha256(req_snapshot),
                    'motionPlanSha256': None,
                    'requestSnapshot': req_snapshot,
                    'motionPlanSnapshot': None,
                    'mediaOrigins': media_origins,
                    'cards': cards_meta,
                    'zip': zip_info,
                })
                updated_keys.append(piece_key)
        else:
            profiles_res = (job.get('result') or {}).get('profiles') or []
            completed_ids = [
                p.get('profileId')
                for p in profiles_res
                if isinstance(p, dict) and p.get('status') == 'completed' and p.get('profileId')
            ]
            if not completed_ids and job.get('profile'):
                completed_ids = [job['profile']]
            for profile_id in completed_ids:
                manifest_abs = os.path.join(out_dir_abs, profile_id, 'delivery-manifest.json')
                manifest = _read_json_safe(manifest_abs)
                if not isinstance(manifest, dict):
                    continue
                artifacts = manifest.get('artifacts') or {}
                core_artifacts = {}
                for art_key in ('video', 'srt', 'narration', 'motionPlan', 'report', 'package'):
                    art = artifacts.get(art_key)
                    if isinstance(art, dict) and art.get('path'):
                        core_artifacts[art_key] = {
                            'path': art.get('path'),
                            'sha256': art.get('sha256'),
                            'bytes': art.get('bytes'),
                        }
                artifacts_fp = canonical_sha256({
                    'modality': modality,
                    'profileId': profile_id,
                    'artifacts': core_artifacts,
                })
                draft_fp, _ = compute_draft_snapshot(
                    studio, modality, req_snapshot, None, motion_snapshot, profile_id=profile_id
                )
                state['exportsSeq'] += 1
                seq = state['exportsSeq']
                delivery_version_id = f'{modality}-{profile_id}-v{seq}-{artifacts_fp[:8]}'
                piece_key = f'{modality}:{profile_id}'
                piece_state = state['pieces'].setdefault(piece_key, {
                    'modality': modality,
                    'profileId': profile_id,
                    'versions': [],
                    'decisions': [],
                })
                piece_state['versions'].append({
                    'deliveryVersionId': delivery_version_id,
                    'seq': seq,
                    'exportedAt': now_iso(),
                    'jobId': job.get('jobId'),
                    'modality': modality,
                    'profileId': profile_id,
                    'caseId': manifest.get('caseId'),
                    'packageId': manifest.get('packageId'),
                    'manifestPath': studio.rel(manifest_abs),
                    'manifestSha256': render_local.sha256_file(manifest_abs),
                    'artifactsFingerprint': artifacts_fp,
                    'draftFingerprint': draft_fp,
                    'requestSha256': canonical_sha256(req_snapshot),
                    'motionPlanSha256': canonical_sha256(motion_snapshot) if motion_snapshot is not None else None,
                    'requestSnapshot': req_snapshot,
                    'motionPlanSnapshot': motion_snapshot,
                    'mediaOrigins': media_origins,
                    'artifacts': core_artifacts,
                })
                updated_keys.append(piece_key)

        _save_review_state(studio, wpaths, state)
        return {'workId': work_id, 'updatedPieces': updated_keys}


def _find_index_entry(index_doc, profile_id):
    if not isinstance(index_doc, dict):
        return None
    for entry in index_doc.get('profiles') or []:
        if isinstance(entry, dict) and entry.get('profileId') == profile_id:
            return entry
    return None


def _inspect_video_or_motion_piece(
    studio,
    modality,
    profile_id,
    profile_meta,
    delivery_dir_rel,
    delivery_data,
    piece_state,
    current_draft_fp,
    selected_in_draft,
    request_doc,
):
    fs = render_local.fs_path
    index_doc = (delivery_data or {}).get('index')
    last_export = (delivery_data or {}).get('lastExportStatus')
    index_entry = _find_index_entry(index_doc, profile_id)
    last_attempt = (index_entry or {}).get('lastAttempt')
    if not last_attempt and isinstance(last_export, dict):
        if last_export.get('profile') in (None, profile_id) and last_export.get('status') in ('failed', 'interrupted'):
            last_attempt = {
                'status': last_export.get('status'),
                'error': last_export.get('error'),
                'finishedAt': last_export.get('finishedAt') or last_export.get('interruptedAt'),
            }

    manifest = None
    for p in (delivery_data or {}).get('profiles') or []:
        if p.get('profileId') == profile_id:
            manifest = p.get('manifest')
            break

    versions = list((piece_state or {}).get('versions') or [])
    decisions = list((piece_state or {}).get('decisions') or [])
    latest_version = versions[-1] if versions else None
    latest_decision = decisions[-1] if decisions else None

    if not manifest:
        return {
            'pieceKey': f'{modality}:{profile_id}',
            'modality': modality,
            'modalityLabel': MODALITY_LABELS[modality],
            'profileId': profile_id,
            'profileLabel': (profile_meta or {}).get('label') or profile_id,
            'network': (profile_meta or {}).get('network'),
            'selectedInDraft': selected_in_draft,
            'deliveryDir': delivery_dir_rel,
            'status': 'no_delivery',
            'statusLabel': 'Sem entrega exportada',
            'readyForPackage': False,
            'readyReason': 'Nenhuma entrega promovida ainda.',
            'linked': False,
            'unlinkedReason': None,
            'integrityErrors': [],
            'deliveryVersionId': None,
            'currentDraftFingerprint': current_draft_fp,
            'exportedDraftFingerprint': None,
            'artifactsFingerprint': None,
            'lastAttempt': last_attempt,
            'lastValidDelivery': (index_entry or {}).get('lastValidDelivery'),
            'mediaOrigins': _merge_media_origins(None, None, request_doc),
            'metrics': {},
            'artifacts': {},
            'currentDecision': None,
            'decisionHistory': decisions,
            'versionsCount': len(versions),
        }

    artifacts = manifest.get('artifacts') or {}
    integrity_errors = []
    core_artifacts = {}
    verified_artifacts = {}
    for art_key in ('video', 'srt', 'narration', 'motionPlan', 'report', 'package'):
        art = artifacts.get(art_key)
        if not isinstance(art, dict) or not art.get('path'):
            if art_key in ('video', 'srt', 'narration'):
                integrity_errors.append(f'artefato obrigatorio ausente no manifesto: {art_key}')
            continue
        ok, abs_path, err, actual_sha, actual_bytes = _verify_manifest_file(
            studio, art.get('path'), expected_sha=art.get('sha256')
        )
        if not ok:
            integrity_errors.append(err)
        core_artifacts[art_key] = {
            'path': art.get('path'),
            'sha256': art.get('sha256'),
            'bytes': art.get('bytes'),
        }
        verified_artifacts[art_key] = {
            'path': art.get('path'),
            'sha256': actual_sha or art.get('sha256'),
            'manifestSha256': art.get('sha256'),
            'bytes': actual_bytes if actual_bytes is not None else art.get('bytes'),
            'ok': ok,
            'error': err,
            'url': (
                f'/media?dir={delivery_dir_rel}&profile={profile_id}&kind={art_key}'
                if art_key in ('video', 'srt', 'narration')
                else None
            ),
        }

    artifacts_fp = canonical_sha256({
        'modality': modality,
        'profileId': profile_id,
        'artifacts': core_artifacts,
    })

    report_rel = ((artifacts.get('report') or {}).get('path'))
    report_doc = None
    if report_rel:
        try:
            report_doc = _read_json_safe(studio.confine(report_rel))
        except (ValueError, OSError):
            report_doc = None

    ffprobe = (artifacts.get('video') or {}).get('ffprobe') or (report_doc or {}).get('inspection') or {}
    out_meta = (report_doc or {}).get('output') or {}
    metrics = {
        'width': ffprobe.get('width') or out_meta.get('width'),
        'height': ffprobe.get('height') or out_meta.get('height'),
        'fps': ffprobe.get('fps') or out_meta.get('fps'),
        'durationSec': ffprobe.get('duration'),
        'durationMs': out_meta.get('durationMs') or (
            round(float(ffprobe['duration']) * 1000) if ffprobe.get('duration') is not None else None
        ),
        'audioStreams': ffprobe.get('audioStreams'),
        'videoSha256': verified_artifacts.get('video', {}).get('sha256'),
        'videoBytes': verified_artifacts.get('video', {}).get('bytes'),
    }

    linked = (
        latest_version is not None
        and latest_version.get('artifactsFingerprint') == artifacts_fp
    )
    delivery_version_id = latest_version.get('deliveryVersionId') if linked else None
    exported_draft_fp = latest_version.get('draftFingerprint') if linked else None
    media_origins = _merge_media_origins(
        latest_version.get('mediaOrigins') if linked else None,
        report_doc,
        latest_version.get('requestSnapshot') if linked else request_doc,
    )

    version_decisions = [d for d in decisions if delivery_version_id and d.get('deliveryVersionId') == delivery_version_id]
    current_decision = version_decisions[-1] if version_decisions else None
    any_prior_decision = [d for d in decisions if d.get('deliveryVersionId') != delivery_version_id]

    unlinked_reason = None
    ready = False
    if integrity_errors:
        status = 'unavailable'
        status_label = 'Arquivo ausente ou corrompido'
        reason = '; '.join(integrity_errors)
    elif not linked:
        status = 'unlinked'
        status_label = 'Entrega anterior não vinculada (legado ou externa)'
        unlinked_reason = (
            'Manifesto no disco nao possui vinculo gravado com os rascunhos atuais '
            '(trabalho legado ou alteracao fora do Studio). Reexporte pelo Studio para vincular e aprovar.'
        )
        reason = unlinked_reason
    elif exported_draft_fp != current_draft_fp:
        status = 'draft_outdated'
        status_label = 'Rascunho ou mídia alterados — reexporte'
        reason = 'Rascunho, midia ou MotionPlan alterado apos esta exportacao.'
    elif current_decision:
        if current_decision.get('decision') == 'approved_for_local_delivery':
            status = 'approved'
            status_label = 'Aprovado para entrega local'
            reason = 'Pronto para empacotamento ZIP.'
            ready = True
        else:
            status = 'changes_requested'
            status_label = 'Ajuste solicitado'
            reason = current_decision.get('note') or 'Ajuste solicitado pelo operador.'
    elif any_prior_decision:
        status = 'reexported_pending'
        status_label = 'Nova exportação aguardando revisão'
        prev = any_prior_decision[-1]
        reason = f"Nova versao exportada ({delivery_version_id}); decisao anterior preservada em {prev.get('deliveryVersionId')}."
    else:
        status = 'pending_review'
        status_label = 'Render concluído — aguardando revisão'
        reason = 'Render tecnico valido; aguarda aprovacao humana.'

    return {
        'pieceKey': f'{modality}:{profile_id}',
        'modality': modality,
        'modalityLabel': MODALITY_LABELS[modality],
        'profileId': profile_id,
        'profileLabel': (profile_meta or {}).get('label') or profile_id,
        'network': (profile_meta or {}).get('network'),
        'selectedInDraft': selected_in_draft,
        'deliveryDir': delivery_dir_rel,
        'packageId': manifest.get('packageId'),
        'caseId': manifest.get('caseId'),
        'status': status,
        'statusLabel': status_label,
        'readyForPackage': ready,
        'readyReason': reason,
        'linked': linked,
        'unlinkedReason': unlinked_reason,
        'integrityErrors': integrity_errors,
        'deliveryVersionId': delivery_version_id,
        'currentDraftFingerprint': current_draft_fp,
        'exportedDraftFingerprint': exported_draft_fp,
        'artifactsFingerprint': artifacts_fp,
        'lastAttempt': last_attempt,
        'lastValidDelivery': (index_entry or {}).get('lastValidDelivery'),
        'mediaOrigins': media_origins,
        'metrics': metrics,
        'artifacts': verified_artifacts,
        'currentDecision': current_decision,
        'decisionHistory': decisions,
        'versionsCount': len(versions),
    }


def _inspect_carousel_piece(
    studio,
    profile_id,
    profile_meta,
    delivery_dir_rel,
    carousel_delivery,
    piece_state,
    current_draft_fp,
    selected_in_draft,
    carousel_req,
):
    index_doc = (carousel_delivery or {}).get('index')
    manifest = (carousel_delivery or {}).get('manifest')
    last_export = (carousel_delivery or {}).get('lastExportStatus')
    last_attempt = (index_doc or {}).get('lastAttempt')
    if not last_attempt and isinstance(last_export, dict) and last_export.get('status') in ('failed', 'interrupted'):
        last_attempt = {
            'status': last_export.get('status'),
            'error': last_export.get('error'),
            'finishedAt': last_export.get('finishedAt') or last_export.get('interruptedAt'),
        }

    versions = list((piece_state or {}).get('versions') or [])
    decisions = list((piece_state or {}).get('decisions') or [])
    latest_version = versions[-1] if versions else None

    if not isinstance(manifest, dict) or manifest.get('profileId') != profile_id:
        return {
            'pieceKey': f'carousel:{profile_id}',
            'modality': 'carousel',
            'modalityLabel': MODALITY_LABELS['carousel'],
            'profileId': profile_id,
            'profileLabel': (profile_meta or {}).get('label') or profile_id,
            'network': (profile_meta or {}).get('network'),
            'selectedInDraft': selected_in_draft,
            'deliveryDir': delivery_dir_rel,
            'status': 'no_delivery',
            'statusLabel': 'Sem entrega exportada',
            'readyForPackage': False,
            'readyReason': 'Nenhum carrossel promovido para este destino.',
            'linked': False,
            'unlinkedReason': None,
            'integrityErrors': [],
            'deliveryVersionId': None,
            'currentDraftFingerprint': current_draft_fp,
            'exportedDraftFingerprint': None,
            'artifactsFingerprint': None,
            'lastAttempt': last_attempt,
            'lastValidDelivery': (index_doc or {}).get('lastValidDelivery'),
            'mediaOrigins': _merge_media_origins(None, None, carousel_req),
            'metrics': {},
            'cards': [],
            'zip': None,
            'currentDecision': None,
            'decisionHistory': decisions,
            'versionsCount': len(versions),
        }

    cards_raw = manifest.get('cards') or []
    integrity_errors = []
    cards_meta = []
    verified_cards = []
    if not cards_raw:
        integrity_errors.append('carrossel sem cards no manifesto')
    for idx, card in enumerate(cards_raw):
        ok, _, err, actual_sha, actual_bytes = _verify_manifest_file(
            studio, card.get('path'), expected_sha=card.get('sha256')
        )
        if not ok:
            integrity_errors.append(err)
        cards_meta.append({
            'order': card.get('order'),
            'id': card.get('id'),
            'file': card.get('file'),
            'path': card.get('path'),
            'sha256': card.get('sha256'),
            'bytes': card.get('bytes'),
        })
        verified_cards.append({
            'order': card.get('order', idx + 1),
            'index': idx,
            'id': card.get('id'),
            'file': card.get('file'),
            'path': card.get('path'),
            'sha256': actual_sha or card.get('sha256'),
            'manifestSha256': card.get('sha256'),
            'bytes': actual_bytes if actual_bytes is not None else card.get('bytes'),
            'ok': ok,
            'error': err,
            'url': f'/media?dir={delivery_dir_rel}&kind=card&index={idx}',
        })

    zip_raw = manifest.get('zip') or {}
    verified_zip = None
    if zip_raw.get('path'):
        zok, _, zerr, zsha, zbytes = _verify_manifest_file(studio, zip_raw.get('path'), expected_sha=zip_raw.get('sha256'))
        if not zok:
            integrity_errors.append(zerr)
        verified_zip = {
            'file': zip_raw.get('file'),
            'path': zip_raw.get('path'),
            'sha256': zsha or zip_raw.get('sha256'),
            'bytes': zbytes if zbytes is not None else zip_raw.get('bytes'),
            'ok': zok,
            'error': zerr,
            'url': f'/media?dir={delivery_dir_rel}&kind=zip',
        }

    artifacts_fp = canonical_sha256({
        'modality': 'carousel',
        'profileId': profile_id,
        'cards': cards_meta,
        'zip': {'path': zip_raw.get('path'), 'sha256': zip_raw.get('sha256')},
    })

    geometry = manifest.get('geometry') or {}
    metrics = {
        'width': geometry.get('width'),
        'height': geometry.get('height'),
        'cardCount': len(verified_cards),
    }

    linked = (
        latest_version is not None
        and latest_version.get('artifactsFingerprint') == artifacts_fp
    )
    delivery_version_id = latest_version.get('deliveryVersionId') if linked else None
    exported_draft_fp = latest_version.get('draftFingerprint') if linked else None
    media_origins = _merge_media_origins(
        latest_version.get('mediaOrigins') if linked else None,
        None,
        latest_version.get('requestSnapshot') if linked else carousel_req,
    )

    version_decisions = [d for d in decisions if delivery_version_id and d.get('deliveryVersionId') == delivery_version_id]
    current_decision = version_decisions[-1] if version_decisions else None
    any_prior_decision = [d for d in decisions if d.get('deliveryVersionId') != delivery_version_id]

    unlinked_reason = None
    ready = False
    if integrity_errors:
        status = 'unavailable'
        status_label = 'Arquivo ausente ou corrompido'
        reason = '; '.join(integrity_errors)
    elif not linked:
        status = 'unlinked'
        status_label = 'Entrega anterior não vinculada (legado ou externa)'
        unlinked_reason = (
            'Manifesto de carrossel nao possui vinculo gravado com os rascunhos atuais '
            '(trabalho legado ou alteracao fora do Studio). Reexporte pelo Studio antes de aprovar.'
        )
        reason = unlinked_reason
    elif exported_draft_fp != current_draft_fp:
        status = 'draft_outdated'
        status_label = 'Carrossel editado após a exportação — reexporte'
        reason = 'CarouselRequest ou midia alterados apos esta exportacao.'
    elif current_decision:
        if current_decision.get('decision') == 'approved_for_local_delivery':
            status = 'approved'
            status_label = 'Aprovado para entrega local'
            reason = 'Pronto para empacotamento ZIP.'
            ready = True
        else:
            status = 'changes_requested'
            status_label = 'Ajuste solicitado'
            reason = current_decision.get('note') or 'Ajuste solicitado pelo operador.'
    elif any_prior_decision:
        status = 'reexported_pending'
        status_label = 'Nova exportação aguardando revisão'
        prev = any_prior_decision[-1]
        reason = f"Nova versao exportada ({delivery_version_id}); decisao anterior preservada em {prev.get('deliveryVersionId')}."
    else:
        status = 'pending_review'
        status_label = 'Render concluído — aguardando revisão'
        reason = 'Cards JPEG validos no manifesto; aguarda aprovacao humana.'

    return {
        'pieceKey': f'carousel:{profile_id}',
        'modality': 'carousel',
        'modalityLabel': MODALITY_LABELS['carousel'],
        'profileId': profile_id,
        'profileLabel': (profile_meta or {}).get('label') or profile_id,
        'network': (profile_meta or {}).get('network'),
        'selectedInDraft': selected_in_draft,
        'deliveryDir': delivery_dir_rel,
        'requestId': manifest.get('requestId'),
        'status': status,
        'statusLabel': status_label,
        'readyForPackage': ready,
        'readyReason': reason,
        'linked': linked,
        'unlinkedReason': unlinked_reason,
        'integrityErrors': integrity_errors,
        'deliveryVersionId': delivery_version_id,
        'currentDraftFingerprint': current_draft_fp,
        'exportedDraftFingerprint': exported_draft_fp,
        'artifactsFingerprint': artifacts_fp,
        'lastAttempt': last_attempt,
        'lastValidDelivery': (index_doc or {}).get('lastValidDelivery'),
        'mediaOrigins': media_origins,
        'metrics': metrics,
        'cards': verified_cards,
        'zip': verified_zip,
        'currentDecision': current_decision,
        'decisionHistory': decisions,
        'versionsCount': len(versions),
    }


def _evaluate_channel_review(profile_id, profile_meta, channel_copy, channel_state, selected_in_draft):
    decisions = list((channel_state or {}).get('decisions') or [])
    latest_decision = decisions[-1] if decisions else None
    copy_sha = channel_copy['copySha256']
    is_empty = channel_copy['isEmpty']
    ready = False

    if is_empty:
        status = 'empty_copy'
        status_label = 'Texto por canal ainda vazio'
        reason = 'Preencha texto de publicacao deste canal para revisar e liberar.'
    elif not latest_decision:
        status = 'pending_review'
        status_label = 'Texto preenchido — aguardando revisão'
        reason = 'Aguarda aprovacao humana do texto deste canal.'
    elif latest_decision.get('copySha256') != copy_sha:
        status = 'copy_outdated'
        status_label = 'Texto do canal alterado — pede nova revisão'
        reason = 'Somente este canal teve o texto alterado apos a revisao anterior.'
    elif latest_decision.get('decision') == 'approved_for_local_delivery':
        status = 'approved'
        status_label = 'Aprovado para entrega local'
        reason = 'Texto por canal aprovado e pronto para empacotamento ZIP.'
        ready = True
    else:
        status = 'changes_requested'
        status_label = 'Ajuste solicitado no texto'
        reason = latest_decision.get('note') or 'Ajuste solicitado pelo operador.'

    return {
        **channel_copy,
        'profileLabel': (profile_meta or {}).get('label') or profile_id,
        'network': (profile_meta or {}).get('network'),
        'format': (profile_meta or {}).get('format'),
        'mediaKind': (profile_meta or {}).get('mediaKind'),
        'selectedInDraft': selected_in_draft,
        'status': status,
        'statusLabel': status_label,
        'readyForPackage': ready,
        'readyReason': reason,
        'currentDecision': latest_decision if (latest_decision and latest_decision.get('copySha256') == copy_sha) else None,
        'decisionHistory': decisions,
    }


def _active_profiles_order(video_req, carousel_req, deliveries, editorial, state):
    selected = set()
    ordered = []

    def add(pid, is_selected=False):
        if not pid or not isinstance(pid, str):
            return
        if is_selected:
            selected.add(pid)
        if pid not in ordered:
            ordered.append(pid)

    for pid in (video_req.get('profiles') or []):
        add(pid, True)
    add(carousel_req.get('profile'), True)

    for mod in ('video', 'motion'):
        for entry in (deliveries.get(mod) or {}).get('profiles') or []:
            add(entry.get('profileId'), False)
    cm = (deliveries.get('carousel') or {}).get('manifest')
    if isinstance(cm, dict):
        add(cm.get('profileId'), False)

    for key in (state.get('pieces') or {}).keys():
        if ':' in key:
            add(key.split(':', 1)[1], False)
    for pid in (editorial.get('channels') or {}).keys():
        # Mantem apenas perfis salvos que tenham texto preenchido se nao estiverem mais selecionados
        entry = editorial['channels'].get(pid) or {}
        if not entry.get('isEmpty'):
            add(pid, False)

    return ordered, selected


def build_review_overview(studio, work_id):
    """Monta a visao completa da ficha editorial, textos por canal, pecas e pacote."""
    with _STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, motion_plan, listing = _read_work_core(studio, work_id)
        editorial = _load_editorial_doc(studio, work_id, wpaths)
        state = _load_review_state(studio, work_id, wpaths)

        deliveries = {
            'video': studio.read_delivery(wpaths['videoDeliveryDir']),
            'carousel': studio.read_carousel_delivery(wpaths['carouselDeliveryDir']),
            'motion': studio.read_delivery(wpaths['motionDeliveryDir']),
        }

        profile_meta_map = {
            p['id']: p for p in (listing.get('profiles') or []) if isinstance(p, dict) and p.get('id')
        }
        ordered_profiles, selected_profiles = _active_profiles_order(
            video_req, carousel_req, deliveries, editorial, state
        )

        channels = []
        for pid in ordered_profiles:
            copy_doc = editorial['channels'].get(pid) or normalize_channel_copy(pid, {})
            ch_state = (state.get('channels') or {}).get(pid)
            channels.append(_evaluate_channel_review(
                pid, profile_meta_map.get(pid), copy_doc, ch_state, pid in selected_profiles
            ))

        pieces = []

        video_selected = list(video_req.get('profiles') or [])
        video_delivered = [
            p.get('profileId')
            for p in (deliveries['video'].get('profiles') or [])
            if p.get('profileId')
        ]
        video_profiles = list(dict.fromkeys(video_selected + video_delivered))
        for pid in video_profiles:
            draft_fp, _ = compute_draft_snapshot(studio, 'video', video_req, None, None, profile_id=pid)
            pieces.append(_inspect_video_or_motion_piece(
                studio,
                'video',
                pid,
                profile_meta_map.get(pid),
                wpaths['videoDeliveryDir'],
                deliveries['video'],
                (state.get('pieces') or {}).get(f'video:{pid}'),
                draft_fp,
                pid in video_selected,
                video_req,
            ))

        carousel_selected_id = carousel_req.get('profile')
        carousel_manifest_id = ((deliveries['carousel'].get('manifest') or {}).get('profileId'))
        carousel_profiles = list(dict.fromkeys(
            [pid for pid in (carousel_selected_id, carousel_manifest_id) if pid]
        ))
        for pid in carousel_profiles:
            draft_fp, _ = compute_draft_snapshot(studio, 'carousel', None, carousel_req, None, profile_id=pid)
            pieces.append(_inspect_carousel_piece(
                studio,
                pid,
                profile_meta_map.get(pid),
                wpaths['carouselDeliveryDir'],
                deliveries['carousel'],
                (state.get('pieces') or {}).get(f'carousel:{pid}'),
                draft_fp,
                pid == carousel_selected_id,
                carousel_req,
            ))

        motion_delivered = [
            p.get('profileId')
            for p in (deliveries['motion'].get('profiles') or [])
            if p.get('profileId')
        ]
        motion_candidates = list(motion_delivered)
        last_motion = deliveries['motion'].get('lastExportStatus')
        if isinstance(last_motion, dict) and last_motion.get('status') in ('failed', 'interrupted'):
            prof = last_motion.get('profile') or (video_selected[0] if video_selected else None)
            if prof and prof not in motion_candidates:
                motion_candidates.append(prof)
        for pid in motion_candidates:
            draft_fp, _ = compute_draft_snapshot(studio, 'motion', video_req, None, motion_plan, profile_id=pid)
            pieces.append(_inspect_video_or_motion_piece(
                studio,
                'motion',
                pid,
                profile_meta_map.get(pid),
                wpaths['motionDeliveryDir'],
                deliveries['motion'],
                (state.get('pieces') or {}).get(f'motion:{pid}'),
                draft_fp,
                pid in video_selected,
                video_req,
            ))

        return {
            'work': work_doc,
            'paths': wpaths,
            'legacyWork': not editorial['existsOnDisk'] and not os.path.isfile(
                render_local.fs_path(studio.confine_workspace(wpaths['reviewStateFile']))
            ),
            'editorial': {
                'schemaVersion': 1,
                'workId': work_id,
                'updatedAt': editorial['updatedAt'],
                'briefing': editorial['briefing'],
                'briefingSha256': canonical_sha256(editorial['briefing']),
                'existsOnDisk': editorial['existsOnDisk'],
            },
            'channels': channels,
            'pieces': pieces,
        }


def save_editorial(studio, work_id, body):
    """Salva ficha editorial e textos por canal preservando canais nao editados."""
    if not isinstance(body, dict):
        raise ValueError('payload editorial invalido')
    with _STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, motion_plan, listing = _read_work_core(studio, work_id)
        existing = _load_editorial_doc(studio, work_id, wpaths)
        briefing = normalize_briefing(body.get('briefing') if 'briefing' in body else existing['briefing'])

        channels_out = dict(existing['channels'])
        ts = now_iso()
        incoming_channels = body.get('channels')
        if isinstance(incoming_channels, dict):
            for pid, raw_entry in incoming_channels.items():
                if not isinstance(pid, str) or not pid.strip():
                    continue
                prev = channels_out.get(pid)
                candidate = normalize_channel_copy(pid, raw_entry)
                if prev and prev.get('copySha256') == candidate['copySha256']:
                    candidate['updatedAt'] = prev.get('updatedAt')
                else:
                    candidate['updatedAt'] = ts
                channels_out[pid] = candidate
        elif isinstance(incoming_channels, list):
            for raw_entry in incoming_channels:
                if not isinstance(raw_entry, dict):
                    continue
                pid = str(raw_entry.get('profileId') or '').strip()
                if not pid:
                    continue
                prev = channels_out.get(pid)
                candidate = normalize_channel_copy(pid, raw_entry)
                if prev and prev.get('copySha256') == candidate['copySha256']:
                    candidate['updatedAt'] = prev.get('updatedAt')
                else:
                    candidate['updatedAt'] = ts
                channels_out[pid] = candidate

        doc_to_write = {
            'schemaVersion': 1,
            'workId': work_id,
            'updatedAt': ts,
            'briefing': briefing,
            'channels': {
                pid: {
                    'profileId': pid,
                    'title': entry['title'],
                    'postText': entry['postText'],
                    'cta': entry['cta'],
                    'destinationUrl': entry['destinationUrl'],
                    'hashtags': entry['hashtags'],
                    'updatedAt': entry.get('updatedAt'),
                    'copySha256': entry['copySha256'],
                }
                for pid, entry in sorted(channels_out.items())
            },
        }
        atomic_write_json(studio.confine_workspace(wpaths['editorialFile']), doc_to_write)
        return build_review_overview(studio, work_id)


def record_review_decision(studio, work_id, body):
    """Registra decisao humana vinculada exatamente a versao/copy conferida."""
    if not isinstance(body, dict):
        raise ValueError('payload de decisao invalido')
    decision = str(body.get('decision') or '').strip()
    if decision not in DECISION_LABELS:
        raise ValueError('decisao de revisao invalida')
    target_type = str(body.get('targetType') or '').strip()
    note = str(body.get('note') or '').strip()

    with _STATE_LOCK:
        overview = build_review_overview(studio, work_id)
        wpaths = overview['paths']
        state = _load_review_state(studio, work_id, wpaths)
        ts = now_iso()

        if target_type == 'piece':
            modality = str(body.get('modality') or '').strip()
            profile_id = str(body.get('profileId') or '').strip()
            piece = next(
                (p for p in overview['pieces'] if p['modality'] == modality and p['profileId'] == profile_id),
                None,
            )
            if not piece:
                raise ValueError(f'peca nao encontrada no trabalho: {modality}/{profile_id}')

            expected_ver = body.get('expectedVersionId')
            if expected_ver is not None and expected_ver != piece.get('deliveryVersionId'):
                raise ReviewVersionConflictError(
                    'A versao da entrega foi substituida durante a revisao; atualize e confira a nova versao antes de decidir.'
                )
            expected_draft = body.get('expectedDraftFingerprint')
            if expected_draft is not None and expected_draft != piece.get('currentDraftFingerprint'):
                raise ReviewVersionConflictError(
                    'O rascunho ou a midia foi alterado durante a revisao; atualize antes de decidir.'
                )

            if piece['status'] == 'no_delivery':
                raise ValueError('Nao ha entrega promovida para revisar nesta peca.')
            if piece['status'] == 'unavailable':
                raise ValueError('Entrega indisponivel ou corrompida: ' + '; '.join(piece['integrityErrors']))
            if piece['status'] == 'unlinked' and decision == 'approved_for_local_delivery':
                raise ValueError(
                    'Entrega anterior sem vinculo gravado ao rascunho atual (trabalho legado ou externo). '
                    'Reexporte pelo Studio antes de aprovar para entrega local.'
                )
            if piece['status'] == 'draft_outdated' and decision == 'approved_for_local_delivery':
                raise ReviewVersionConflictError(
                    'Rascunho, midia ou MotionPlan alterado apos esta exportacao; reexporte antes de aprovar.'
                )

            piece_key = piece['pieceKey']
            piece_state = state['pieces'].setdefault(piece_key, {
                'modality': modality,
                'profileId': profile_id,
                'versions': [],
                'decisions': [],
            })
            piece_state['decisions'].append({
                'decisionId': f'dec-{uuid.uuid4().hex[:10]}',
                'decision': decision,
                'decisionLabel': DECISION_LABELS[decision],
                'deliveryVersionId': piece.get('deliveryVersionId'),
                'draftFingerprint': piece.get('exportedDraftFingerprint'),
                'artifactsFingerprint': piece.get('artifactsFingerprint'),
                'decidedAt': ts,
                'note': note,
            })

        elif target_type == 'channel':
            profile_id = str(body.get('profileId') or '').strip()
            channel = next((c for c in overview['channels'] if c['profileId'] == profile_id), None)
            if not channel:
                raise ValueError(f'canal nao encontrado no trabalho: {profile_id}')

            expected_copy_sha = body.get('expectedCopySha256')
            if expected_copy_sha is not None and expected_copy_sha != channel.get('copySha256'):
                raise ReviewVersionConflictError(
                    'O texto deste canal foi alterado antes da confirmacao da decisao; recarregue e confira o texto atual.'
                )
            if channel['isEmpty'] and decision == 'approved_for_local_delivery':
                raise ValueError('Preencha ao menos um campo do texto de publicacao antes de aprovar este canal.')

            ch_state = state['channels'].setdefault(profile_id, {
                'profileId': profile_id,
                'decisions': [],
            })
            ch_state['decisions'].append({
                'decisionId': f'cdec-{uuid.uuid4().hex[:10]}',
                'decision': decision,
                'decisionLabel': DECISION_LABELS[decision],
                'copySha256': channel['copySha256'],
                'decidedAt': ts,
                'note': note,
            })
        else:
            raise ValueError('targetType de revisao invalido (use "piece" ou "channel")')

        _save_review_state(studio, wpaths, state)
        return build_review_overview(studio, work_id)


def read_verified_artifact_text(studio, work_id, modality, profile_id, kind):
    """Le .srt ou roteiro de narracao verificado por manifesto, confinamento e SHA-256."""
    if kind not in ARTIFACT_TEXT_KINDS:
        raise ValueError('tipo de texto de artefato invalido (use srt ou narration)')
    if modality not in ('video', 'motion'):
        raise ValueError('leitura de SRT/narracao aplica-se a video ou motion')
    overview = build_review_overview(studio, work_id)
    piece = next(
        (p for p in overview['pieces'] if p['modality'] == modality and p['profileId'] == profile_id),
        None,
    )
    if not piece or piece['status'] == 'no_delivery':
        raise ValueError('entrega nao encontrada para inspecao de texto')
    art = (piece.get('artifacts') or {}).get(kind)
    if not art or not art.get('path'):
        raise ValueError(f'artefato {kind} ausente no manifesto')
    ok, abs_path, err, sha, _ = _verify_manifest_file(
        studio, art['path'], expected_sha=art.get('manifestSha256')
    )
    if not ok:
        raise ValueError(err or 'falha ao verificar artefato de texto')
    with open(render_local.fs_path(abs_path), 'r', encoding='utf-8') as handle:
        content = handle.read()
    return {
        'workId': work_id,
        'modality': modality,
        'profileId': profile_id,
        'kind': kind,
        'path': art['path'],
        'sha256': sha,
        'content': content,
    }
