"""Modelos reutilizaveis por projeto e criacao de variacoes em serie no Video Studio.

Armazenamento local versionado sob `.workspace/studio/templates/`: cada modelo
tem ID, nome, revisoes imutaveis e referencia ao trabalho de origem. A captura
congela rascunhos (video, carrossel e Motion), ficha editorial e midias com
SHA-256, origem e licenca. A instanciação (duplicacao ou variacao) cria um
trabalho novo de forma transacional, com IDs proprios, ficha propria, revisao
em aberto e entregas vazias.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import uuid

import render_local
import studio_review

TEMPLATE_SCHEMA_VERSION = 1
KEBAB_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


class TemplateConflictError(ValueError):
    """Conflito ou condicao recuperavel em modelos (HTTP 409)."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def _now():
    return studio_review.now_iso()


def _atomic_json(target, value):
    studio_review.atomic_write_json(target, value)


def templates_dir(studio):
    return os.path.join(studio.studio_workspace, 'templates')


def creations_dir(studio):
    return os.path.join(studio.studio_workspace, 'template-creations')


def _template_dir(studio, template_id):
    if not isinstance(template_id, str) or not KEBAB_RE.match(template_id):
        raise ValueError('id de modelo deve usar kebab-case')
    return os.path.join(templates_dir(studio), template_id)


def _read_json(path):
    with open(render_local.fs_path(path), 'r', encoding='utf-8') as handle:
        return json.load(handle)


def _slug(text, fallback):
    text = (text or '').strip().lower()
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    text = re.sub(r'-{2,}', '-', text)
    return text if KEBAB_RE.match(text or '') else fallback


# ---------------------------------------------------------------------------
# Captura de snapshot coerente do trabalho salvo
# ---------------------------------------------------------------------------

def _draft_fingerprint(studio, work_id):
    paths = studio.work_paths(work_id)
    payload = {}
    for key in ('workFile', 'videoDraft', 'carouselDraft', 'motionPlan', 'editorialFile'):
        abs_path = studio.confine_workspace(paths[key])
        if os.path.isfile(render_local.fs_path(abs_path)):
            payload[key] = render_local.sha256_file(abs_path)
        else:
            payload[key] = None
    return studio_review.canonical_sha256(payload)


def capture_work_snapshot(studio, work_id):
    """Captura a versao salva do trabalho com detecção de edicao concorrente."""
    opened = studio.open_work(work_id)
    work = opened['work']
    project_rel = work.get('project')
    if not project_rel:
        raise ValueError(f'trabalho {work_id} sem projeto configurado')
    fp_before = _draft_fingerprint(studio, work_id)

    video_req = opened.get('videoRequest')
    carousel_req = opened.get('carouselRequest')
    motion_plan = opened.get('motionPlan')
    if not isinstance(video_req, dict) or not video_req.get('scenes'):
        raise ValueError(f'trabalho {work_id} nao possui pedido de video salvo com cenas')

    wpaths = work.get('paths') or studio.work_paths(work_id)
    editorial = studio_review._load_editorial_doc(studio, work_id, wpaths)

    registry = {}
    for req in (video_req, carousel_req if isinstance(carousel_req, dict) else None):
        if not req:
            continue
        for item in req.get('media') or []:
            if not isinstance(item, dict) or not item.get('id'):
                continue
            mid = item['id']
            rel_path = str(item.get('path') or '')
            try:
                abs_path = studio.confine(rel_path)
            except ValueError:
                raise TemplateConflictError('TEMPLATE_MEDIA_OUT_OF_ROOT', f'midia {mid} fora da raiz: {rel_path}')
            if not os.path.isfile(render_local.fs_path(abs_path)):
                raise TemplateConflictError('TEMPLATE_MEDIA_MISSING', f'midia {mid} ausente: {rel_path}')
            sha = render_local.sha256_file(abs_path)
            entry = {
                'id': mid,
                'path': rel_path,
                'type': item.get('type') or 'image',
                'origin': item.get('origin'),
                'license': item.get('license'),
                'sha256': sha,
                'bytes': os.path.getsize(render_local.fs_path(abs_path)),
            }
            if mid in registry and registry[mid]['sha256'] != sha:
                raise TemplateConflictError(
                    'TEMPLATE_MEDIA_INCONSISTENT',
                    f'midia {mid} aparece com bytes diferentes entre as modalidades do trabalho',
                )
            registry[mid] = entry

    if _draft_fingerprint(studio, work_id) != fp_before:
        raise TemplateConflictError(
            'TEMPLATE_CAPTURE_CONFLICT',
            f'o trabalho {work_id} foi editado durante a captura; salve e tente novamente',
        )

    return {
        'schemaVersion': TEMPLATE_SCHEMA_VERSION,
        'sourceWorkId': work_id,
        'workName': work.get('name') or work_id,
        'project': project_rel,
        'projectId': work.get('projectId'),
        'capturedAt': _now(),
        'videoRequest': json.loads(json.dumps(video_req)),
        'carouselRequest': json.loads(json.dumps(carousel_req)) if isinstance(carousel_req, dict) else None,
        'motionPlan': json.loads(json.dumps(motion_plan)) if isinstance(motion_plan, dict) else None,
        'editorial': {
            'briefing': editorial.get('briefing') or studio_review.empty_briefing(),
            'channels': editorial.get('channels') or {},
        },
        'media': sorted(registry.values(), key=lambda m: m['id']),
    }


# ---------------------------------------------------------------------------
# Modelos: listar, salvar revisao, ler
# ---------------------------------------------------------------------------

def list_templates(studio, project=None):
    base = templates_dir(studio)
    out = []
    if not os.path.isdir(render_local.fs_path(base)):
        return out
    for entry in sorted(os.listdir(render_local.fs_path(base))):
        doc_path = os.path.join(base, entry, 'template.json')
        if not os.path.isfile(render_local.fs_path(doc_path)):
            continue
        try:
            doc = _read_json(doc_path)
        except (OSError, ValueError):
            continue
        if project and doc.get('project') != project:
            continue
        out.append(doc)
    out.sort(key=lambda t: t.get('updatedAt', ''), reverse=True)
    return out


def get_template(studio, template_id):
    doc_path = os.path.join(_template_dir(studio, template_id), 'template.json')
    if not os.path.isfile(render_local.fs_path(doc_path)):
        raise ValueError(f'modelo nao encontrado: {template_id}')
    return _read_json(doc_path)


def _revision_dir(studio, template_id, revision_id):
    if not isinstance(revision_id, str) or not re.match(r'^rev-[a-z0-9-]+$', revision_id):
        raise ValueError('id de revisao invalido')
    return os.path.join(_template_dir(studio, template_id), 'revisions', revision_id)


def load_revision_snapshot(studio, template_id, revision_id):
    rev_dir = _revision_dir(studio, template_id, revision_id)
    snap_path = os.path.join(rev_dir, 'snapshot.json')
    if not os.path.isfile(render_local.fs_path(snap_path)):
        raise ValueError(f'revisao nao encontrada: {template_id}/{revision_id}')
    return _read_json(snap_path), rev_dir


def save_as_template(studio, body):
    if not isinstance(body, dict):
        raise ValueError('payload de modelo invalido')
    work_id = (body.get('workId') or '').strip()
    name = (body.get('name') or '').strip()
    template_id = (body.get('templateId') or '').strip() or None
    label = (body.get('label') or '').strip() or None
    if not work_id:
        raise ValueError('informe o trabalho de origem')

    snapshot = capture_work_snapshot(studio, work_id)
    fp_after_capture = _draft_fingerprint(studio, work_id)

    if template_id:
        doc = get_template(studio, template_id)
        if doc.get('project') != snapshot['project']:
            raise TemplateConflictError(
                'TEMPLATE_PROJECT_MISMATCH',
                'modelos V1 sao restritos ao projeto de origem; crie um novo modelo para este projeto',
            )
    else:
        template_id = _slug(name, f'modelo-{uuid.uuid4().hex[:8]}')
        doc_path = os.path.join(_template_dir(studio, template_id), 'template.json')
        if os.path.isfile(render_local.fs_path(doc_path)):
            template_id = f'{template_id}-{uuid.uuid4().hex[:4]}'
        doc = {
            'schemaVersion': TEMPLATE_SCHEMA_VERSION,
            'id': template_id,
            'name': name or snapshot['workName'],
            'project': snapshot['project'],
            'projectId': snapshot['projectId'],
            'sourceWorkId': work_id,
            'createdAt': _now(),
            'updatedAt': _now(),
            'revisions': [],
        }

    if not name:
        name = doc.get('name') or snapshot['workName']
    doc['name'] = name

    revision_id = f'rev-{len(doc.get("revisions") or []) + 1}'
    final_rev_dir = _revision_dir(studio, template_id, revision_id)
    if os.path.isdir(render_local.fs_path(final_rev_dir)):
        raise TemplateConflictError('TEMPLATE_REVISION_COLLISION', f'revisao {revision_id} ja existe')

    staging_parent = os.path.join(studio.root, '.workspace', 'tmp')
    os.makedirs(staging_parent, exist_ok=True)
    staging = tempfile.mkdtemp(prefix='template-rev-', dir=staging_parent)
    try:
        media_stage = os.path.join(staging, 'media')
        os.makedirs(media_stage, exist_ok=True)
        by_sha = {}
        for entry in snapshot['media']:
            sha = entry['sha256']
            if sha in by_sha:
                entry['file'] = by_sha[sha]
                continue
            ext = os.path.splitext(entry['path'])[1] or '.bin'
            fname = f'{entry["id"]}--{sha[:12]}{ext}'
            src_abs = studio.confine(entry['path'])
            dst_abs = os.path.join(media_stage, fname)
            shutil.copyfile(render_local.fs_path(src_abs), render_local.fs_path(dst_abs))
            if render_local.sha256_file(dst_abs) != sha:
                raise TemplateConflictError(
                    'TEMPLATE_MEDIA_DIVERGENCE',
                    f'midia {entry["id"]} mudou durante a copia do modelo; capture novamente',
                )
            by_sha[sha] = fname
            entry['file'] = fname

        if _draft_fingerprint(studio, work_id) != fp_after_capture:
            raise TemplateConflictError(
                'TEMPLATE_CAPTURE_CONFLICT',
                f'o trabalho {work_id} foi editado durante a captura; salve e tente novamente',
            )

        _atomic_json(os.path.join(staging, 'snapshot.json'), snapshot)
        os.makedirs(render_local.fs_path(os.path.dirname(final_rev_dir)), exist_ok=True)
        os.replace(render_local.fs_path(staging), render_local.fs_path(final_rev_dir))
        staging = None
    finally:
        if staging and os.path.isdir(render_local.fs_path(staging)):
            shutil.rmtree(render_local.fs_path(staging), ignore_errors=True)

    vreq = snapshot['videoRequest']
    creq = snapshot.get('carouselRequest') or {}
    mplan = snapshot.get('motionPlan') or {}
    doc.setdefault('revisions', []).append({
        'revisionId': revision_id,
        'createdAt': _now(),
        'label': label or f'Revisao {len(doc["revisions"])}',
        'sourceWorkId': work_id,
        'sourceWorkUpdatedAt': snapshot['capturedAt'],
        'mediaCount': len(snapshot['media']),
        'videoScenes': len(vreq.get('scenes') or []),
        'carouselCards': len(creq.get('cards') or []),
        'motionEffects': len(mplan.get('effects') or []),
        'videoProfiles': list(vreq.get('profiles') or []),
        'carouselProfile': creq.get('profile'),
    })
    doc['updatedAt'] = _now()
    _atomic_json(os.path.join(_template_dir(studio, template_id), 'template.json'), doc)
    return {'template': doc, 'revisionId': revision_id}


# ---------------------------------------------------------------------------
# Revalidacao de projeto/catalogo e plano de variacoes
# ---------------------------------------------------------------------------

def _profile_maps(studio, project_rel):
    listing = studio.list_profiles(project_rel)
    by_id = {p['id']: p for p in listing.get('profiles') or [] if isinstance(p, dict) and p.get('id')}
    return by_id


def _check_snapshot_profiles(studio, snapshot):
    """Revalida catalogo + allowlist + capacidade local; lista perfis que exigem ajuste."""
    project_rel = snapshot['project']
    try:
        project_abs = studio.confine(project_rel)
    except ValueError:
        raise TemplateConflictError('TEMPLATE_PROJECT_INVALID', f'projeto fora da raiz: {project_rel}')
    if not os.path.isfile(render_local.fs_path(project_abs)):
        raise TemplateConflictError('TEMPLATE_PROJECT_INVALID', f'ProjectManifest ausente: {project_rel}')
    with open(render_local.fs_path(project_abs), 'r', encoding='utf-8') as handle:
        project_doc = json.load(handle)
    studio._validate_project_with_core(project_doc)
    by_id = _profile_maps(studio, project_rel)

    adjustments = []
    vreq = snapshot.get('videoRequest') or {}
    for pid in vreq.get('profiles') or []:
        meta = by_id.get(pid)
        if meta is None:
            adjustments.append({'profileId': pid, 'modality': 'video', 'reason': 'perfil desconhecido no catalogo'})
        elif meta.get('availability') != 'allowed':
            adjustments.append({'profileId': pid, 'modality': 'video',
                                'reason': meta.get('blockReason') or 'fora da allowlist do projeto'})
        elif not meta.get('localExportVideo'):
            adjustments.append({'profileId': pid, 'modality': 'video',
                                'reason': 'sem render local de video compativel'})
    creq = snapshot.get('carouselRequest') or {}
    cpid = creq.get('profile')
    if cpid:
        meta = by_id.get(cpid)
        if meta is None:
            adjustments.append({'profileId': cpid, 'modality': 'carousel', 'reason': 'perfil desconhecido no catalogo'})
        elif meta.get('availability') != 'allowed':
            adjustments.append({'profileId': cpid, 'modality': 'carousel',
                                'reason': meta.get('blockReason') or 'fora da allowlist do projeto'})
        elif not meta.get('localExportCarousel'):
            adjustments.append({'profileId': cpid, 'modality': 'carousel',
                                'reason': 'sem render local de carrossel compativel'})
    mplan = snapshot.get('motionPlan') or {}
    if mplan.get('effects'):
        allowed_video = [
            pid for pid in vreq.get('profiles') or []
            if (by_id.get(pid) or {}).get('availability') == 'allowed'
        ]
        if allowed_video and not any((by_id.get(pid) or {}).get('localExportMotion') for pid in allowed_video):
            adjustments.append({
                'profileId': ', '.join(allowed_video), 'modality': 'motion',
                'reason': 'Motion local exige ao menos um perfil vertical 9:16 compativel',
            })
    return adjustments


def _row_overrides(snapshot, row):
    vreq = snapshot.get('videoRequest') or {}
    creq = snapshot.get('carouselRequest') or {}
    briefing = (snapshot.get('editorial') or {}).get('briefing') or {}
    fields = {
        'name': {'inherited': snapshot.get('workName'), 'value': (row.get('name') or '').strip() or None},
        'title': {'inherited': vreq.get('title'), 'value': (row.get('title') or '').strip() or None},
        'hook': {'inherited': briefing.get('hook'), 'value': (row.get('hook') or '').strip() or None},
        'cta': {'inherited': briefing.get('cta'), 'value': (row.get('cta') or '').strip() or None},
    }
    changes = {}
    for key, info in fields.items():
        effective = info['value'] if info['value'] is not None else info['inherited']
        changes[key] = {
            'inherited': info['inherited'],
            'override': info['value'],
            'effective': effective,
            'changed': info['value'] is not None and info['value'] != info['inherited'],
        }
    return changes


def _validate_rows(studio, snapshot, rows, rev_dir=None):
    if not isinstance(rows, list) or not rows:
        raise ValueError('informe pelo menos uma linha de variacao')
    plans = []
    seen_ids = set()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f'linha {idx + 1} invalida')
        new_id = (row.get('id') or '').strip()
        conflicts = []
        if not KEBAB_RE.match(new_id or ''):
            conflicts.append({'code': 'WORK_ID_INVALID', 'message': 'id deve usar kebab-case (letras minusculas, numeros e hifens)'})
        if new_id in seen_ids:
            conflicts.append({'code': 'WORK_ID_DUPLICATE_ROW', 'message': f'id {new_id} repetido nas linhas desta confirmacao'})
        seen_ids.add(new_id)
        if new_id and KEBAB_RE.match(new_id):
            existing = os.path.join(studio.works_dir, new_id, 'work.json')
            if os.path.isfile(render_local.fs_path(existing)):
                conflicts.append({
                    'code': 'WORK_ID_COLLISION',
                    'message': f'ja existe um trabalho com o id "{new_id}"; escolha outro id (o conteudo existente foi preservado)',
                })
        conditions = []
        for entry in snapshot.get('media') or []:
            if rev_dir is not None:
                src = os.path.join(rev_dir, 'media', entry.get('file') or '')
            else:
                src = studio.confine(entry['path'])
            if not os.path.isfile(render_local.fs_path(src)):
                conditions.append({'code': 'TEMPLATE_MEDIA_MISSING', 'mediaId': entry['id'],
                                   'message': f'midia {entry["id"]} ausente no modelo'})
            elif render_local.sha256_file(src) != entry['sha256']:
                conditions.append({'code': 'TEMPLATE_MEDIA_DIVERGENCE', 'mediaId': entry['id'],
                                   'message': f'midia {entry["id"]} divergente do hash registrado no modelo'})
        plans.append({
            'row': idx,
            'id': new_id,
            'name': (row.get('name') or '').strip() or None,
            'ok': not conflicts and not conditions,
            'conflicts': conflicts,
            'conditions': conditions,
            'changes': _row_overrides(snapshot, row),
        })
    return plans


def plan_variations(studio, body):
    template_id = (body.get('templateId') or '').strip()
    revision_id = (body.get('revisionId') or '').strip()
    doc = get_template(studio, template_id)
    snapshot, rev_dir = load_revision_snapshot(studio, template_id, revision_id)
    adjustments = _check_snapshot_profiles(studio, snapshot)
    plans = _validate_rows(studio, snapshot, body.get('rows') or [], rev_dir=rev_dir)
    for plan in plans:
        if adjustments:
            plan['ok'] = False
            plan['conditions'].extend(
                {'code': 'PROFILE_NEEDS_ADJUSTMENT', **adj} for adj in adjustments
            )
    return {
        'template': doc,
        'revisionId': revision_id,
        'project': snapshot['project'],
        'profileAdjustments': adjustments,
        'plans': plans,
    }


# ---------------------------------------------------------------------------
# Instanciacao transacional (duplicacao e variacoes)
# ---------------------------------------------------------------------------

def _instantiate_work(studio, snapshot, new_id, name, overrides, origin, media_source):
    if not KEBAB_RE.match(new_id or ''):
        raise TemplateConflictError('WORK_ID_INVALID', 'id deve usar kebab-case')
    paths = studio.work_paths(new_id)
    work_abs = studio.confine_workspace(paths['workFile'])
    if os.path.exists(render_local.fs_path(work_abs)):
        raise TemplateConflictError(
            'WORK_ID_COLLISION',
            f'ja existe um trabalho com o id "{new_id}"; escolha outro id (o conteudo existente foi preservado)',
        )
    adjustments = _check_snapshot_profiles(studio, snapshot)
    if adjustments:
        detail = '; '.join(f'{a["profileId"]} ({a["modality"]}): {a["reason"]}' for a in adjustments)
        raise TemplateConflictError('PROFILE_NEEDS_ADJUSTMENT', f'perfis exigem ajuste antes de criar: {detail}')

    staging_parent = os.path.join(studio.root, '.workspace', 'tmp')
    os.makedirs(staging_parent, exist_ok=True)
    staging = tempfile.mkdtemp(prefix='studio-work-create-', dir=staging_parent)
    try:
        media_rel = paths['mediaDir']
        media_stage = os.path.join(staging, 'media')
        os.makedirs(media_stage, exist_ok=True)
        path_map = {}
        used_names = set()
        for entry in snapshot.get('media') or []:
            src_abs = media_source(entry)
            if not os.path.isfile(render_local.fs_path(src_abs)):
                raise TemplateConflictError('TEMPLATE_MEDIA_MISSING', f'midia {entry["id"]} ausente: {entry["path"]}')
            base = os.path.basename(entry['path'])
            fname = base
            if fname in used_names:
                fname = f'{entry["id"]}-{base}'
            used_names.add(fname)
            dst_abs = os.path.join(media_stage, fname)
            shutil.copyfile(render_local.fs_path(src_abs), render_local.fs_path(dst_abs))
            if render_local.sha256_file(dst_abs) != entry['sha256']:
                raise TemplateConflictError(
                    'TEMPLATE_MEDIA_DIVERGENCE',
                    f'midia {entry["id"]} divergente do hash do modelo; a criacao foi abortada sem alterar outros trabalhos',
                )
            path_map[entry['path']] = f'{media_rel}/{fname}'

        def remap(req):
            if not isinstance(req, dict):
                return req
            req = json.loads(json.dumps(req))
            for item in req.get('media') or []:
                if isinstance(item, dict) and item.get('path') in path_map:
                    item['path'] = path_map[item['path']]
            return req

        title_override = overrides.get('title')
        vreq = remap(snapshot.get('videoRequest'))
        vreq['id'] = f'{new_id}-video'
        vreq['project'] = snapshot['project']
        if title_override:
            vreq['title'] = title_override
        if isinstance(vreq.get('visualStyle'), dict):
            vreq['visualStyle']['id'] = f'{new_id}-estilo'

        creq = remap(snapshot.get('carouselRequest'))
        if isinstance(creq, dict):
            creq['id'] = f'{new_id}-carrossel'
            creq['project'] = snapshot['project']
            if title_override:
                creq['title'] = title_override

        mplan = json.loads(json.dumps(snapshot.get('motionPlan'))) if isinstance(snapshot.get('motionPlan'), dict) else None
        if mplan is not None:
            mplan['requestId'] = vreq['id']

        briefing = json.loads(json.dumps((snapshot.get('editorial') or {}).get('briefing') or studio_review.empty_briefing()))
        if overrides.get('hook'):
            briefing['hook'] = overrides['hook']
        if overrides.get('cta'):
            briefing['cta'] = overrides['cta']
        editorial = {
            'schemaVersion': 1,
            'workId': new_id,
            'updatedAt': _now(),
            'briefing': briefing,
            'channels': json.loads(json.dumps((snapshot.get('editorial') or {}).get('channels') or {})),
        }

        ts = _now()
        work_doc = {
            'schemaVersion': 1,
            'id': new_id,
            'name': name or snapshot.get('workName') or new_id,
            'project': snapshot['project'],
            'projectId': snapshot.get('projectId'),
            'createdAt': ts,
            'updatedAt': ts,
            'paths': paths,
            'origin': origin,
        }

        os.makedirs(os.path.join(staging, 'drafts'), exist_ok=True)
        for sub in ('video', 'carousel', 'motion', 'package'):
            os.makedirs(os.path.join(staging, 'deliveries', sub), exist_ok=True)
        _atomic_json(os.path.join(staging, 'drafts', 'video.request.json'), vreq)
        if creq is not None:
            _atomic_json(os.path.join(staging, 'drafts', 'carousel.request.json'), creq)
        if mplan is not None:
            _atomic_json(os.path.join(staging, 'drafts', 'motion.plan.json'), mplan)
        _atomic_json(os.path.join(staging, 'editorial.json'), editorial)
        _atomic_json(os.path.join(staging, 'work.json'), work_doc)

        # Conferencia final de todos os arquivos necessarios antes da promocao
        required = ['work.json', 'editorial.json', 'drafts/video.request.json']
        if creq is not None:
            required.append('drafts/carousel.request.json')
        if mplan is not None:
            required.append('drafts/motion.plan.json')
        for rel in required:
            if not os.path.isfile(render_local.fs_path(os.path.join(staging, rel))):
                raise TemplateConflictError('TEMPLATE_STAGING_INCOMPLETE', f'arquivo ausente no staging: {rel}')
        for entry in snapshot.get('media') or []:
            fname = os.path.basename(path_map[entry['path']])
            fpath = os.path.join(media_stage, fname)
            if not os.path.isfile(render_local.fs_path(fpath)):
                raise TemplateConflictError('TEMPLATE_STAGING_INCOMPLETE', f'midia ausente no staging: {fname}')

        target_dir = studio.confine_workspace(paths['workDir'])
        if os.path.exists(render_local.fs_path(target_dir)):
            raise TemplateConflictError(
                'WORK_ID_COLLISION',
                f'ja existe um trabalho com o id "{new_id}"; escolha outro id (o conteudo existente foi preservado)',
            )
        os.replace(render_local.fs_path(staging), render_local.fs_path(target_dir))
        staging = None
        return work_doc
    finally:
        if staging and os.path.isdir(render_local.fs_path(staging)):
            shutil.rmtree(render_local.fs_path(staging), ignore_errors=True)


def duplicate_work(studio, body):
    if not isinstance(body, dict):
        raise ValueError('payload de duplicacao invalido')
    work_id = (body.get('workId') or '').strip()
    new_id = (body.get('newId') or body.get('id') or '').strip()
    name = (body.get('name') or '').strip()
    if not work_id or not new_id:
        raise ValueError('informe workId e newId')
    snapshot = capture_work_snapshot(studio, work_id)
    work_doc = _instantiate_work(
        studio, snapshot, new_id, name or f'{snapshot["workName"]} (copia)', {},
        origin={'kind': 'duplicate', 'sourceWorkId': work_id, 'capturedAt': snapshot['capturedAt']},
        media_source=lambda entry: studio.confine(entry['path']),
    )
    return {'work': work_doc}


def _creation_record_path(studio, key):
    if not isinstance(key, str) or not re.match(r'^[A-Za-z0-9._-]{1,120}$', key):
        raise ValueError('idempotencyKey invalida')
    return os.path.join(creations_dir(studio), f'{key}.json')


def create_variations(studio, body):
    if not isinstance(body, dict):
        raise ValueError('payload de criacao invalido')
    template_id = (body.get('templateId') or '').strip()
    revision_id = (body.get('revisionId') or '').strip()
    rows = body.get('rows') or []
    key = (body.get('idempotencyKey') or '').strip() or None

    doc = get_template(studio, template_id)
    snapshot, rev_dir = load_revision_snapshot(studio, template_id, revision_id)

    record = None
    record_path = _creation_record_path(studio, key) if key else None
    if record_path and os.path.isfile(render_local.fs_path(record_path)):
        record = _read_json(record_path)
        if record.get('templateId') != template_id or record.get('revisionId') != revision_id:
            raise TemplateConflictError(
                'CREATION_KEY_REUSE',
                'idempotencyKey ja usada para outro modelo/revisao; use uma nova chave',
            )
        if len(record.get('rows') or []) != len(rows):
            raise TemplateConflictError(
                'CREATION_KEY_REUSE',
                'idempotencyKey ja usada com outra quantidade de linhas; use uma nova chave',
            )
        for stored, row in zip(record['rows'], rows):
            if stored.get('input') != row:
                raise TemplateConflictError(
                    'CREATION_KEY_REUSE',
                    'idempotencyKey ja usada com linhas diferentes; use uma nova chave',
                )
        if all(r.get('status') == 'created' for r in record['rows']):
            return {'creations': record['rows'], 'deduplicated': True, 'template': doc, 'revisionId': revision_id}

    plans = _validate_rows(studio, snapshot, rows, rev_dir=rev_dir)
    adjustments = _check_snapshot_profiles(studio, snapshot)

    if record is None:
        record = {
            'schemaVersion': 1,
            'idempotencyKey': key,
            'templateId': template_id,
            'revisionId': revision_id,
            'createdAt': _now(),
            'rows': [],
        }

    def media_source(entry):
        return os.path.join(rev_dir, 'media', entry.get('file') or '')

    for idx, row in enumerate(rows):
        existing = next((r for r in record['rows'] if r.get('row') == idx), None)
        if existing and existing.get('status') == 'created':
            continue
        plan = plans[idx]
        entry_out = {'row': idx, 'input': row, 'id': (row.get('id') or '').strip(), 'status': 'failed', 'error': None}
        if adjustments:
            detail = '; '.join(f'{a["profileId"]} ({a["modality"]}): {a["reason"]}' for a in adjustments)
            entry_out['error'] = {'code': 'PROFILE_NEEDS_ADJUSTMENT', 'message': f'perfis exigem ajuste: {detail}'}
        elif not plan['ok']:
            first = (plan['conflicts'] or plan['conditions'])[0]
            entry_out['error'] = {'code': first['code'], 'message': first['message']}
        else:
            changes = plan['changes']
            overrides = {k: changes[k]['override'] for k in ('title', 'hook', 'cta') if changes[k]['override'] is not None}
            try:
                work_doc = _instantiate_work(
                    studio, snapshot, entry_out['id'],
                    (row.get('name') or '').strip() or None,
                    overrides,
                    origin={'kind': 'template', 'templateId': template_id, 'revisionId': revision_id,
                            'sourceWorkId': snapshot.get('sourceWorkId')},
                    media_source=media_source,
                )
                entry_out['status'] = 'created'
                entry_out['name'] = work_doc['name']
            except (TemplateConflictError, ValueError) as exc:
                entry_out['error'] = {
                    'code': getattr(exc, 'code', 'CREATION_FAILED'),
                    'message': str(exc),
                }
        record['rows'] = [r for r in record['rows'] if r.get('row') != idx] + [entry_out]
        record['rows'].sort(key=lambda r: r['row'])
        record['updatedAt'] = _now()
        if record_path:
            os.makedirs(render_local.fs_path(creations_dir(studio)), exist_ok=True)
            _atomic_json(record_path, record)

    return {'creations': record['rows'], 'deduplicated': False, 'template': doc, 'revisionId': revision_id}