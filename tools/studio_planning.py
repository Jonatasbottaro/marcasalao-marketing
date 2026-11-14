"""Fluxo de Planejamento por etapas no Studio local (Ideia -> Briefing -> Roteiro/Cards -> Editores).

Integra-se com ``studio_review.py`` (reaproveitando ``editorial.json`` e o
vinculo de revisoes em ``review-state.json``) e com ``llm_adapter.py`` para
suportar tres modos de preenchimento sem perder estado nem sobrescrever edicoes
concorrentes:
  1. Manual
  2. Copiar e importar (prompt por etapa + validacao via nucleo + diff)
  3. Modelo local opcional (POST /v1/chat/completions com timeout e isolamento)
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
import uuid

import llm_adapter
import render_local
import studio_review

PLANNING_STAGES = ('briefing', 'creative', 'apply')
STAGE_LABELS = {
    'briefing': '1. Ideia e briefing',
    'creative': '2. Hook, roteiro e cards',
    'apply': '3. Aplicação aos editores',
}

QUESTION_DIMENSIONS = (
    ('product', 'Produto / servico'),
    ('audience', 'Publico-alvo'),
    ('objective', 'Objetivo da peca'),
    ('coreMessage', 'Mensagem principal'),
    ('supportEvidence', 'Evidencia ou prova de apoio'),
    ('cta', 'Chamada para acao (CTA)'),
    ('tone', 'Tom de voz'),
    ('channels', 'Canais e formatos permitidos'),
)

DEFAULT_QUESTION_PROMPTS = {
    'product': 'Qual produto, funcionalidade ou servico especifico esta em foco nesta peca?',
    'audience': 'Quem e o publico principal que deve assistir ou ler este conteudo?',
    'objective': 'Qual resultado pratico esta campanha busca gerar (ex.: clareza, visitas, pedidos)?',
    'coreMessage': 'Em uma frase direta, qual ideia central precisa ficar clara?',
    'supportEvidence': 'Qual evidencia real ou tela do trabalho comprova essa mensagem?',
    'cta': 'Qual chamada para acao e destino final devem orientar quem viu a peca?',
    'tone': 'Qual tom de voz combina com esta entrega (ex.: pratico, objetivo, didatico)?',
    'channels': 'Quais perfis permitidos pelo projeto receberao o video, o carrossel ou os textos?',
}

MARCA_SALAO_FORBIDDEN_PATTERNS = (
    ('mensagem automatica', 'Marca Salao nao realiza envio automatico de mensagens.'),
    ('mensagens automaticas', 'Marca Salao nao realiza envio automatico de mensagens.'),
    ('envio automatico', 'Evite prometer envio automatico nao comprovado no Marca Salao.'),
    ('lembrete', 'Marca Salao nao envia lembretes automaticos de agendamento.'),
    ('whatsapp', 'Nao atribuir envio automatico via WhatsApp ao Marca Salao sem funcao comprovada.'),
    ('sms', 'Nao atribuir envio automatico via SMS ao Marca Salao.'),
    ('confirmacao automatica', 'Marca Salao nao envia confirmacoes automaticas para clientes.'),
    ('reduz falta', 'Nao prometer reducao automatica ou garantida de faltas sem evidencia aprovada.'),
    ('sem faltas', 'Nao prometer eliminacao garantida de faltas.'),
    ('zero falta', 'Nao prometer eliminacao garantida de faltas.'),
)

COMMERCIAL_TERMS_RE = re.compile(
    r'(\bgratis\b|\bgratuito\b|\bdesconto\b|\bgarantid[oa]\b|\b100%\b|\bdobro\b|r\$\s*\d+|\d+\s*%)',
    re.IGNORECASE,
)
URL_RE = re.compile(r'(?:https?://\S+|www\.\S+|\b[a-z0-9-]+\.com(?:\.br)?\S*)', re.IGNORECASE)


class PlanningValidationError(ValueError):
    """Erro de validacao com codigo, alvo e diagnostico acionavel em portugues."""

    def __init__(self, message, failure_code=None, subject=None, stage=None):
        super().__init__(message)
        self.failure_code = failure_code or 'PLANNING_VALIDATION_ERROR'
        self.subject = subject
        self.stage = stage


def _strip_accents(text):
    norm = unicodedata.normalize('NFKD', str(text or ''))
    return ''.join(ch for ch in norm if not unicodedata.combining(ch)).lower()


def _slug_kebab(text, fallback='item'):
    cleaned = re.sub(r'[^a-z0-9]+', '-', _strip_accents(text)).strip('-')
    return cleaned or fallback


def _is_marca_salao_project(project_doc, project_rel=''):
    joined = f"{(project_doc or {}).get('id', '')} {(project_doc or {}).get('brandTheme', '')} {project_rel}".lower()
    return 'marca-salao' in joined


def _scan_text_warnings(text, is_marca_salao=False):
    warnings = []
    norm = _strip_accents(text)
    if is_marca_salao:
        for needle, reason in MARCA_SALAO_FORBIDDEN_PATTERNS:
            if needle in norm:
                warnings.append(f'Regra Marca Salao ({needle}): {reason}')
    if URL_RE.search(text or ''):
        warnings.append('Contem URL: confirmar se o destino e oficial e se o link na bio/descricao esta ativo.')
    if COMMERCIAL_TERMS_RE.search(text or ''):
        warnings.append('Contem afirmacao comercial ou numerica: depende de confirmacao editorial antes da aprovacao.')
    return list(dict.fromkeys(warnings))


def _allowed_profiles_from_listing(listing):
    out = []
    for p in (listing or {}).get('profiles') or []:
        if not isinstance(p, dict):
            continue
        if p.get('availability') != 'allowed':
            continue
        if not (p.get('localExportVideo') or p.get('localExportCarousel') or p.get('localExportMotion')):
            continue
        out.append(p)
    return out


def _build_work_media_catalog(studio, wpaths, video_req, carousel_req, use_library=True):
    scanned = []
    media_dir_abs = studio.confine_workspace(wpaths['mediaDir'])
    if os.path.isdir(render_local.fs_path(media_dir_abs)):
        scanned = studio.scan_media(wpaths['mediaDir'])

    by_path = {}
    used_ids = set()
    for req in (video_req or {}, carousel_req or {}):
        for item in req.get('media') or []:
            if not isinstance(item, dict) or not item.get('path'):
                continue
            by_path[item['path']] = {
                'id': item.get('id'),
                'path': item.get('path'),
                'type': item.get('type') or 'image',
                'origin': item.get('origin') or 'studio-work',
                'license': item.get('license') or 'pending',
            }
            if item.get('id'):
                used_ids.add(item['id'])

    catalog = []
    seen_paths = set()
    for entry in scanned:
        path = entry['path']
        seen_paths.add(path)
        existing = by_path.get(path)
        if existing and existing.get('id'):
            mid = existing['id']
        else:
            stem = os.path.splitext(entry['name'])[0]
            base_id = _slug_kebab(stem, fallback='midia')
            mid = base_id
            idx = 2
            while mid in used_ids:
                mid = f'{base_id}-{idx}'
                idx += 1
            used_ids.add(mid)
        catalog.append({
            'id': mid,
            'name': entry['name'],
            'path': path,
            'type': entry['type'],
            'bytes': entry.get('bytes', 0),
            'origin': (existing or {}).get('origin') or 'studio-work',
            'license': (existing or {}).get('license') or 'pending',
        })

    for path, existing in by_path.items():
        if path in seen_paths:
            continue
        try:
            abs_p = studio.confine(path)
            exists = os.path.isfile(render_local.fs_path(abs_p))
        except ValueError:
            exists = False
        if not exists:
            continue
        catalog.append({
            'id': existing.get('id') or _slug_kebab(os.path.basename(path)),
            'name': os.path.basename(path),
            'path': path,
            'type': existing.get('type') or 'image',
            'bytes': os.path.getsize(render_local.fs_path(abs_p)),
            'origin': existing.get('origin') or 'studio-work',
            'license': existing.get('license') or 'pending',
        })

    if use_library:
        import studio_media
        catalog = studio_media.apply_library_to_catalog(studio, wpaths, catalog)
    return catalog


def _default_recommended_profiles(allowed_profiles):
    ids = [p['id'] for p in allowed_profiles]
    preferred = [
        pid for pid in ('instagram-reels-video', 'instagram-feed-image-square')
        if pid in ids
    ]
    if preferred:
        return preferred
    video_first = next((p['id'] for p in allowed_profiles if p.get('localExportVideo')), None)
    carousel_first = next((p['id'] for p in allowed_profiles if p.get('localExportCarousel')), None)
    return [pid for pid in (video_first, carousel_first) if pid] or ids[:2]


def _normalize_questions(raw_questions):
    by_dim = {}
    extra = []
    seen_ids = set()
    for item in raw_questions or []:
        if not isinstance(item, dict):
            continue
        dim = str(item.get('dimension') or '').strip()
        qid = _slug_kebab(item.get('id') or f'q-{dim or len(seen_ids) + 1}')
        while qid in seen_ids:
            qid = f'{qid}-{len(seen_ids) + 1}'
        seen_ids.add(qid)
        entry = {
            'id': qid,
            'dimension': dim if dim in dict(QUESTION_DIMENSIONS) else 'objective',
            'question': str(item.get('question') or DEFAULT_QUESTION_PROMPTS.get(dim, '')).strip(),
            'suggestedAnswer': str(item.get('suggestedAnswer') or '').strip(),
            'answer': str(item.get('answer') or '').strip(),
        }
        if dim in dict(QUESTION_DIMENSIONS) and dim not in by_dim:
            by_dim[dim] = entry
        else:
            extra.append(entry)

    out = []
    for dim, _label in QUESTION_DIMENSIONS:
        if dim in by_dim:
            out.append(by_dim[dim])
        else:
            qid = f'q-{_slug_kebab(dim)}'
            while qid in seen_ids:
                qid = f'{qid}-{len(seen_ids) + 1}'
            seen_ids.add(qid)
            out.append({
                'id': qid,
                'dimension': dim,
                'question': DEFAULT_QUESTION_PROMPTS[dim],
                'suggestedAnswer': '',
                'answer': '',
            })
    out.extend(extra)
    return out


def _normalize_claims(raw_claims, work_media_ids, is_marca_salao):
    valid_statuses = ('confirmed', 'hypothesis', 'pending_validation')
    out = []
    seen = set()
    for idx, item in enumerate(raw_claims or [], start=1):
        if not isinstance(item, dict):
            continue
        statement = str(item.get('statement') or '').strip()
        if not statement:
            continue
        cid = _slug_kebab(item.get('id') or f'claim-{idx}')
        while cid in seen:
            cid = f'{cid}-{len(seen) + 1}'
        seen.add(cid)
        status = str(item.get('status') or 'pending_validation').strip()
        if status not in valid_statuses:
            status = 'pending_validation'
        evidence_id = str(item.get('evidenceMediaId') or '').strip()
        if evidence_id and evidence_id not in work_media_ids:
            evidence_id = ''
        auto_warnings = _scan_text_warnings(statement, is_marca_salao=is_marca_salao)
        explicit_warn = str(item.get('warning') or '').strip()
        if explicit_warn and explicit_warn not in auto_warnings:
            auto_warnings.insert(0, explicit_warn)
        requires_conf = bool(item.get('requiresConfirmation', status != 'confirmed' or bool(auto_warnings)))
        if status == 'confirmed' and not evidence_id and not auto_warnings:
            # Permite confirmacao editorial explicita sem midia apenas se operador marcou confirmed
            pass
        out.append({
            'id': cid,
            'statement': statement,
            'status': status,
            'requiresConfirmation': requires_conf,
            'evidenceMediaId': evidence_id,
            'warning': ' | '.join(auto_warnings),
        })
    return out


def _normalize_creative(raw_creative, allowed_profile_ids, is_marca_salao):
    src = raw_creative if isinstance(raw_creative, dict) else {}

    hooks = []
    seen_h = set()
    for idx, h in enumerate(src.get('hookOptions') or [], start=1):
        if not isinstance(h, dict):
            continue
        text = str(h.get('text') or '').strip()
        if not text:
            continue
        hid = _slug_kebab(h.get('id') or f'hook-{idx}')
        while hid in seen_h:
            hid = f'{hid}-{len(seen_h) + 1}'
        seen_h.add(hid)
        hooks.append({
            'id': hid,
            'text': text,
            'angle': str(h.get('angle') or '').strip(),
        })
    selected_hook = str(src.get('selectedHookId') or '').strip()
    if selected_hook not in seen_h:
        selected_hook = hooks[0]['id'] if hooks else ''

    scenes = []
    seen_s = set()
    for idx, s in enumerate(src.get('videoScenes') or [], start=1):
        if not isinstance(s, dict):
            continue
        sid = _slug_kebab(s.get('id') or f'cena-{idx}')
        while sid in seen_s:
            sid = f'{sid}-{len(seen_s) + 1}'
        seen_s.add(sid)
        try:
            duration = int(s.get('durationMs') or 4000)
        except (TypeError, ValueError):
            duration = 4000
        duration = max(1000, min(60000, duration))
        motion_intent = str(s.get('motionIntent') or 'none').strip()
        if motion_intent not in ('none', 'slow-zoom'):
            motion_intent = 'none'
        nf = str(s.get('narrativeFunction') or 'demonstration').strip()
        if nf not in ('hook', 'context', 'problem', 'demonstration', 'explanation', 'proof', 'transition', 'cta', 'closing'):
            nf = 'demonstration'
        scenes.append({
            'id': sid,
            'objective': str(s.get('objective') or '').strip(),
            'narrativeFunction': nf,
            'durationMs': duration,
            'titleOverlay': str(s.get('titleOverlay') or '').strip(),
            'caption': str(s.get('caption') or '').strip(),
            'narration': str(s.get('narration') or '').strip(),
            'requiredMediaDescriptor': str(s.get('requiredMediaDescriptor') or '').strip(),
            'mediaId': str(s.get('mediaId') or '').strip(),
            'motionIntent': motion_intent,
        })

    cards = []
    seen_c = set()
    for idx, c in enumerate(src.get('carouselCards') or [], start=1):
        if not isinstance(c, dict):
            continue
        cid = _slug_kebab(c.get('id') or f'card-{idx}')
        while cid in seen_c:
            cid = f'{cid}-{len(seen_c) + 1}'
        seen_c.add(cid)
        role = str(c.get('role') or ('cover' if idx == 1 else 'content')).strip()
        if role not in ('cover', 'content', 'cta'):
            role = 'content'
        cards.append({
            'id': cid,
            'role': role,
            'title': str(c.get('title') or '').strip(),
            'body': str(c.get('body') or '').strip(),
            'requiredMediaDescriptor': str(c.get('requiredMediaDescriptor') or '').strip(),
            'mediaId': str(c.get('mediaId') or '').strip(),
        })

    channels = {}
    raw_ch = src.get('channelCopies')
    ch_iter = []
    if isinstance(raw_ch, dict):
        for pid, entry in raw_ch.items():
            if isinstance(entry, dict):
                ch_iter.append({**entry, 'profileId': pid})
    elif isinstance(raw_ch, list):
        ch_iter = [e for e in raw_ch if isinstance(e, dict)]

    for entry in ch_iter:
        pid = str(entry.get('profileId') or '').strip()
        if not pid or pid not in allowed_profile_ids:
            continue
        flags = [str(f).strip() for f in (entry.get('flags') or []) if str(f).strip()]
        auto_flags = _scan_text_warnings(
            ' '.join([
                str(entry.get('title') or ''),
                str(entry.get('postText') or ''),
                str(entry.get('cta') or ''),
                str(entry.get('destinationUrl') or ''),
            ]),
            is_marca_salao=is_marca_salao,
        )
        for fl in auto_flags:
            if fl not in flags:
                flags.append(fl)
        channels[pid] = {
            'profileId': pid,
            'title': str(entry.get('title') or '').strip(),
            'postText': str(entry.get('postText') or '').strip(),
            'cta': str(entry.get('cta') or '').strip(),
            'destinationUrl': str(entry.get('destinationUrl') or '').strip(),
            'hashtags': str(entry.get('hashtags') or '').strip(),
            'flags': flags,
        }

    scene_map = {s['id']: s for s in scenes}
    motion_suggestions = []
    for ms in src.get('motionSuggestions') or []:
        if not isinstance(ms, dict):
            continue
        sid = str(ms.get('sceneId') or '').strip()
        target_el = str(ms.get('targetElement') or '').strip()
        if not sid or not target_el:
            continue
        if sid in scene_map and scene_map[sid]['motionIntent'] == 'slow-zoom':
            continue
        color = str(ms.get('suggestedColor') or '#FFD700').strip()
        if not re.match(r'^#[0-9a-fA-F]{6}$', color):
            color = '#FFD700'
        try:
            start_ms = int(ms.get('suggestedStartMs') if ms.get('suggestedStartMs') is not None else 400)
        except (TypeError, ValueError):
            start_ms = 400
        try:
            end_ms = int(ms.get('suggestedEndMs') if ms.get('suggestedEndMs') is not None else 2800)
        except (TypeError, ValueError):
            end_ms = 2800
        start_ms = max(0, start_ms)
        end_ms = max(start_ms + 200, end_ms)
        motion_suggestions.append({
            'sceneId': sid,
            'targetElement': target_el,
            'suggestedColor': color.upper(),
            'suggestedStartMs': start_ms,
            'suggestedEndMs': end_ms,
            'note': str(ms.get('note') or '').strip(),
        })

    return {
        'basedOnBriefingSha256': src.get('basedOnBriefingSha256') or None,
        'hookOptions': hooks,
        'selectedHookId': selected_hook,
        'scriptSummary': str(src.get('scriptSummary') or '').strip(),
        'videoScenes': scenes,
        'carouselCards': cards,
        'channelCopies': channels,
        'motionSuggestions': motion_suggestions,
    }


def _briefing_payload_hash(briefing, briefing_ext):
    return studio_review.canonical_sha256({
        'briefing': studio_review.normalize_briefing(briefing),
        'product': str((briefing_ext or {}).get('product') or '').strip(),
        'tone': str((briefing_ext or {}).get('tone') or '').strip(),
        'recommendedProfiles': sorted(list((briefing_ext or {}).get('recommendedProfiles') or [])),
    })


def _load_planning_doc(studio, work_id, work_doc, wpaths, editorial, listing, work_media):
    path = studio.confine_workspace(wpaths['planningFile'])
    raw = studio_review._read_json_safe(path)
    exists = isinstance(raw, dict)
    raw = raw if exists else {}

    allowed_profiles = _allowed_profiles_from_listing(listing)
    allowed_ids = [p['id'] for p in allowed_profiles]
    is_marca_salao = _is_marca_salao_project(
        {'id': work_doc.get('projectId')}, work_doc.get('project', '')
    )
    media_ids = {m['id'] for m in work_media}

    current_stage = str(raw.get('currentStage') or 'briefing').strip()
    if current_stage not in PLANNING_STAGES:
        current_stage = 'briefing'

    ed_brief = studio_review.normalize_briefing(editorial.get('briefing'))
    if exists and isinstance(raw.get('briefing'), dict):
        plan_brief = studio_review.normalize_briefing(raw.get('briefing'))
    else:
        plan_brief = dict(ed_brief)

    raw_ext = raw.get('briefingExtended') if isinstance(raw.get('briefingExtended'), dict) else {}
    rec_profiles = [
        pid for pid in (raw_ext.get('recommendedProfiles') or [])
        if isinstance(pid, str) and pid in allowed_ids
    ]
    if not rec_profiles:
        rec_profiles = _default_recommended_profiles(allowed_profiles)

    briefing_ext = {
        'product': str(raw_ext.get('product') or '').strip(),
        'tone': str(raw_ext.get('tone') or '').strip(),
        'recommendedProfiles': rec_profiles,
    }

    doc = {
        'schemaVersion': 1,
        'workId': work_id,
        'updatedAt': raw.get('updatedAt'),
        'currentStage': current_stage,
        'ideaText': str(raw.get('ideaText') or '').strip(),
        'briefing': plan_brief,
        'briefingExtended': briefing_ext,
        'gaps': [str(g).strip() for g in (raw.get('gaps') or []) if str(g).strip()],
        'questions': _normalize_questions(raw.get('questions')),
        'claims': _normalize_claims(raw.get('claims'), media_ids, is_marca_salao),
        'creative': _normalize_creative(raw.get('creative'), set(allowed_ids), is_marca_salao),
        'suggestionHistory': list(raw.get('suggestionHistory') or [])[-25:],
        'lastApplied': raw.get('lastApplied') if isinstance(raw.get('lastApplied'), dict) else None,
        'lastSyncedEditorialBriefingSha256': raw.get('lastSyncedEditorialBriefingSha256') or editorial_sha_default(ed_brief),
        'existsOnDisk': exists,
    }
    return doc, allowed_profiles, is_marca_salao


def editorial_sha_default(ed_brief):
    return studio_review.canonical_sha256(studio_review.normalize_briefing(ed_brief))


def _save_planning_doc(studio, wpaths, doc):
    to_write = {k: v for k, v in doc.items() if k != 'existsOnDisk'}
    to_write['updatedAt'] = studio_review.now_iso()
    studio_review.atomic_write_json(studio.confine_workspace(wpaths['planningFile']), to_write)
    doc['updatedAt'] = to_write['updatedAt']
    doc['existsOnDisk'] = True
    return doc


def _compute_context_fingerprints(planning_doc, editorial, video_req, carousel_req, motion_plan):
    plan_core = {
        'currentStage': planning_doc['currentStage'],
        'ideaText': planning_doc['ideaText'],
        'briefing': planning_doc['briefing'],
        'briefingExtended': planning_doc['briefingExtended'],
        'questions': planning_doc['questions'],
        'claims': planning_doc['claims'],
        'creative': planning_doc['creative'],
    }
    planning_sha = studio_review.canonical_sha256(plan_core)
    briefing_sha = _briefing_payload_hash(planning_doc['briefing'], planning_doc['briefingExtended'])
    ed_brief_sha = studio_review.canonical_sha256(editorial['briefing'])
    ed_channels_sha = studio_review.canonical_sha256({
        pid: ch.get('copySha256') for pid, ch in sorted((editorial.get('channels') or {}).items())
    })
    drafts_sha = studio_review.canonical_sha256({
        'video': video_req,
        'carousel': carousel_req,
        'motion': motion_plan,
    })
    context_sha = studio_review.canonical_sha256({
        'planningSha256': planning_sha,
        'editorialBriefingSha256': ed_brief_sha,
        'editorialChannelsSha256': ed_channels_sha,
        'draftsSha256': drafts_sha,
    })
    return {
        'planningSha256': planning_sha,
        'briefingSha256': briefing_sha,
        'editorialBriefingSha256': ed_brief_sha,
        'editorialChannelsSha256': ed_channels_sha,
        'draftsSha256': drafts_sha,
        'contextFingerprint': context_sha,
    }


def _analyze_planning_state(planning_doc, editorial, fps, work_media, is_marca_salao):
    b = planning_doc['briefing']
    ext = planning_doc['briefingExtended']
    dim_values = {
        'product': ext.get('product') or '',
        'audience': b.get('audience') or '',
        'objective': b.get('objective') or '',
        'coreMessage': b.get('coreMessage') or '',
        'supportEvidence': b.get('supportEvidence') or '',
        'cta': b.get('cta') or '',
        'tone': ext.get('tone') or '',
        'channels': ', '.join(ext.get('recommendedProfiles') or []),
    }
    filled = []
    auto_gaps = []
    for dim, label in QUESTION_DIMENSIONS:
        val = dim_values.get(dim, '').strip()
        if val:
            filled.append({'dimension': dim, 'label': label, 'value': val})
        else:
            auto_gaps.append(f'Falta definir: {label}')

    if not planning_doc['ideaText'].strip():
        auto_gaps.insert(0, 'Ideia original em texto livre ainda nao preenchida.')

    pending_claims = [
        c for c in planning_doc['claims']
        if c['status'] != 'confirmed' or c['requiresConfirmation']
    ]
    media_ids = {m['id'] for m in work_media}
    unlinked_claims = [c['id'] for c in planning_doc['claims'] if not c.get('evidenceMediaId')]
    if pending_claims:
        auto_gaps.append(f'{len(pending_claims)} afirmacao(oes) dependem de confirmacao antes da aprovacao.')

    combined_gaps = list(dict.fromkeys(auto_gaps + planning_doc['gaps']))

    # Reconferencia de roteiro/cards/textos quando briefing mudou
    based_sha = planning_doc['creative'].get('basedOnBriefingSha256')
    has_creative = bool(
        planning_doc['creative']['videoScenes']
        or planning_doc['creative']['carouselCards']
        or planning_doc['creative']['channelCopies']
    )
    creative_needs_recheck = bool(has_creative and based_sha and based_sha != fps['briefingSha256'])
    recheck_reason = (
        'O briefing mudou apos a preparacao do roteiro/cards/textos; confira a Etapa 2 antes de aplicar aos editores.'
        if creative_needs_recheck
        else ''
    )

    ed_brief_changed_externally = (
        fps['editorialBriefingSha256'] != planning_doc.get('lastSyncedEditorialBriefingSha256')
        and fps['editorialBriefingSha256'] != editorial_sha_default(b)
    )

    warnings = []
    for text in [
        planning_doc['ideaText'],
        b.get('objective'), b.get('audience'), b.get('coreMessage'),
        b.get('supportEvidence'), b.get('hook'), b.get('scriptSummary'), b.get('cta'),
    ]:
        for w in _scan_text_warnings(text or '', is_marca_salao=is_marca_salao):
            if w not in warnings:
                warnings.append(w)
    for c in planning_doc['claims']:
        if c.get('warning') and c['warning'] not in warnings:
            warnings.append(c['warning'])

    missing_media_scenes = [
        s['id'] for s in planning_doc['creative']['videoScenes']
        if not s.get('mediaId') or s['mediaId'] not in media_ids
    ]

    return {
        'filledFields': filled,
        'detectedGaps': combined_gaps,
        'creativeNeedsRecheck': creative_needs_recheck,
        'recheckReason': recheck_reason,
        'editorialBriefingDiverged': ed_brief_changed_externally,
        'pendingClaimsCount': len(pending_claims),
        'unlinkedClaimsCount': len(unlinked_claims),
        'missingMediaSceneIds': missing_media_scenes,
        'warnings': warnings,
        'mediaRequirements': llm_adapter.ImageProviderExtensionPoint.summarize_media_requirements(
            planning_doc['creative']['videoScenes'],
            planning_doc['creative']['carouselCards'],
            media_ids,
        ),
    }


def _ordered_project_media_list(planning_doc, existing_media_list, work_media_map, required_ids):
    by_id = {}
    for m in existing_media_list or []:
        if isinstance(m, dict) and m.get('id'):
            by_id[m['id']] = dict(m)

    out = []
    seen = set()
    for mid in required_ids:
        if mid in seen:
            continue
        seen.add(mid)
        wm = work_media_map.get(mid)
        prev = by_id.get(mid) or {}
        if wm:
            # Quando a versao selecionada na biblioteca muda o arquivo, a origem
            # e a licenca acompanham a nova versao (proveniencia do render).
            same_file = prev.get('path') == wm['path']
            out.append({
                'id': mid,
                'path': wm['path'],
                'type': wm['type'],
                'origin': (prev.get('origin') if same_file else None) or wm.get('origin') or 'studio-work',
                'license': (prev.get('license') if same_file else None) or wm.get('license') or 'pending',
            })
        elif prev.get('path'):
            out.append(prev)
    return out


def _build_target_drafts_from_planning(studio, work_doc, wpaths, planning_doc, editorial, video_req, carousel_req, motion_plan, work_media, allowed_profiles, selection=None):
    sel = selection if isinstance(selection, dict) else {}
    preserve_scenes = set(sel.get('preserveSceneIds') or [])
    preserve_cards = set(sel.get('preserveCardIds') or [])
    preserve_channels = set(sel.get('preserveChannelIds') or [])

    work_media_map = {m['id']: m for m in work_media}
    allowed_ids = [p['id'] for p in allowed_profiles]
    creative = planning_doc['creative']
    b = planning_doc['briefing']
    ext = planning_doc['briefingExtended']

    # --- 1. VideoRequest candidato ---
    existing_scenes_by_id = {
        s['id']: s for s in (video_req.get('scenes') or [])
        if isinstance(s, dict) and s.get('id')
    }
    candidate_scenes = []
    pending_video_scenes = []
    for s in creative['videoScenes']:
        sid = s['id']
        if sid in preserve_scenes and sid in existing_scenes_by_id:
            scene_obj = dict(existing_scenes_by_id[sid])
        else:
            scene_obj = {
                'id': sid,
                'durationMs': int(s['durationMs']),
                'mediaId': s.get('mediaId') or '',
                'caption': s['caption'] or s['titleOverlay'] or sid,
                'narration': s['narration'] or s['caption'] or s['titleOverlay'] or sid,
                **({'title': s['titleOverlay']} if s.get('titleOverlay') else {}),
                'narrativeFunction': s.get('narrativeFunction') or 'demonstration',
                'motionIntent': s.get('motionIntent') or 'none',
            }
        mid = scene_obj.get('mediaId') or ''
        if not mid or mid not in work_media_map:
            pending_video_scenes.append(sid)
        candidate_scenes.append(scene_obj)

    allowed_video_ids = [p['id'] for p in allowed_profiles if p.get('localExportVideo')]
    rec_video_profiles = [pid for pid in ext['recommendedProfiles'] if pid in allowed_video_ids]
    target_video_profiles = rec_video_profiles or (video_req.get('profiles') or []) or allowed_video_ids[:1]
    target_video_profiles = [pid for pid in target_video_profiles if pid in allowed_video_ids]

    candidate_video_req = None
    if candidate_scenes and not pending_video_scenes and target_video_profiles:
        req_media_ids = [s['mediaId'] for s in candidate_scenes]
        candidate_video_req = {
            'schemaVersion': 1,
            'id': video_req.get('id') or f"{work_doc['id']}-video",
            'project': work_doc['project'],
            'title': b.get('hook') or ext.get('product') or video_req.get('title') or work_doc['name'],
            'locale': video_req.get('locale') or 'pt-BR',
            'profiles': target_video_profiles,
            'visualStyle': video_req.get('visualStyle') or {
                'schemaVersion': 1,
                'id': f"{work_doc['id']}-estilo",
                'title': {
                    'textColor': '#FFFFFF', 'outlineColor': '#000000',
                    'fontSize': 44, 'marginTop': 170, 'marginHorizontal': 70,
                },
            },
            'media': _ordered_project_media_list(planning_doc, video_req.get('media'), work_media_map, req_media_ids),
            'scenes': candidate_scenes,
        }

    # --- 2. CarouselRequest candidato ---
    existing_cards_by_id = {
        c['id']: c for c in (carousel_req.get('cards') or [])
        if isinstance(c, dict) and c.get('id')
    }
    candidate_cards = []
    pending_carousel_cards = []
    for c in creative['carouselCards']:
        cid = c['id']
        if cid in preserve_cards and cid in existing_cards_by_id:
            card_obj = dict(existing_cards_by_id[cid])
        else:
            card_obj = {
                'id': cid,
                'title': c['title'] or cid,
                **({'body': c['body']} if c.get('body') else {}),
            }
            mid = c.get('mediaId') or ''
            if mid:
                if mid in work_media_map and work_media_map[mid].get('type') == 'image':
                    card_obj['mediaId'] = mid
                else:
                    pending_carousel_cards.append(cid)
        candidate_cards.append(card_obj)

    allowed_carousel_ids = [p['id'] for p in allowed_profiles if p.get('localExportCarousel')]
    rec_carousel_profile = next((pid for pid in ext['recommendedProfiles'] if pid in allowed_carousel_ids), None)
    target_carousel_profile = rec_carousel_profile or (
        carousel_req.get('profile') if carousel_req.get('profile') in allowed_carousel_ids else None
    ) or (allowed_carousel_ids[0] if allowed_carousel_ids else None)

    candidate_carousel_req = None
    if candidate_cards and not pending_carousel_cards and target_carousel_profile:
        card_media_ids = [c['mediaId'] for c in candidate_cards if c.get('mediaId')]
        candidate_carousel_req = {
            'schemaVersion': 1,
            'id': carousel_req.get('id') or f"{work_doc['id']}-carrossel",
            'project': work_doc['project'],
            'profile': target_carousel_profile,
            'title': b.get('hook') or ext.get('product') or carousel_req.get('title') or f"{work_doc['name']} — Carrossel",
            'media': _ordered_project_media_list(planning_doc, carousel_req.get('media'), work_media_map, card_media_ids),
            'cards': candidate_cards,
        }

    # --- 3. Motion sync ---
    scenes_source = candidate_scenes if candidate_scenes else (video_req.get('scenes') or [])
    none_scenes = {s['id'] for s in scenes_source if s.get('motionIntent', 'none') == 'none'}
    effects_before = list((motion_plan or {}).get('effects') or [])
    effects_kept = [e for e in effects_before if e.get('sceneId') in none_scenes]
    effects_removed = [e.get('sceneId') for e in effects_before if e.get('sceneId') not in none_scenes]
    candidate_motion_plan = {
        'schemaVersion': 1,
        'requestId': (candidate_video_req or video_req).get('id') or f"{work_doc['id']}-video",
        'effects': effects_kept,
    }

    # --- 4. Channels ---
    target_channels = {}
    for pid, ch in creative['channelCopies'].items():
        if pid not in allowed_ids:
            continue
        if pid in preserve_channels and pid in (editorial.get('channels') or {}):
            target_channels[pid] = dict(editorial['channels'][pid])
        else:
            target_channels[pid] = {
                'profileId': pid,
                'title': ch['title'],
                'postText': ch['postText'],
                'cta': ch['cta'],
                'destinationUrl': ch['destinationUrl'],
                'hashtags': ch['hashtags'],
            }

    return {
        'candidateVideoReq': candidate_video_req,
        'pendingVideoScenes': pending_video_scenes,
        'targetVideoProfiles': target_video_profiles,
        'candidateCarouselReq': candidate_carousel_req,
        'pendingCarouselCards': pending_carousel_cards,
        'targetCarouselProfile': target_carousel_profile,
        'candidateMotionPlan': candidate_motion_plan,
        'motionEffectsKept': [e.get('sceneId') for e in effects_kept],
        'motionEffectsRemoved': effects_removed,
        'motionSuggestions': list(creative.get('motionSuggestions') or []),
        'targetChannels': target_channels,
        'preserveScenes': list(preserve_scenes),
        'preserveCards': list(preserve_cards),
        'preserveChannels': list(preserve_channels),
    }


def compute_editors_diff(studio, work_id, planning_doc, editorial, video_req, carousel_req, motion_plan, work_media, allowed_profiles, review_overview=None, selection=None):
    work_doc, _, _, _, _, _ = studio_review._read_work_core(studio, work_id)
    built = _build_target_drafts_from_planning(
        studio, work_doc, None, planning_doc, editorial, video_req, carousel_req, motion_plan, work_media, allowed_profiles, selection=selection
    )

    ed_b = studio_review.normalize_briefing(editorial.get('briefing'))
    pl_b = studio_review.normalize_briefing(planning_doc['briefing'])
    brief_labels = {
        'objective': 'Objetivo',
        'audience': 'Publico-alvo',
        'coreMessage': 'Mensagem principal',
        'supportEvidence': 'Evidencia de apoio',
        'hook': 'Gancho (hook)',
        'scriptSummary': 'Resumo do roteiro',
        'cta': 'CTA geral',
    }
    briefing_changes = []
    for f in studio_review.EDITORIAL_FIELDS:
        if ed_b[f] != pl_b[f]:
            briefing_changes.append({
                'field': f,
                'label': brief_labels.get(f, f),
                'before': ed_b[f],
                'after': pl_b[f],
            })

    old_scenes = {s['id']: s for s in (video_req.get('scenes') or []) if isinstance(s, dict) and s.get('id')}
    new_scenes = planning_doc['creative']['videoScenes']
    scene_changes = []
    for s in new_scenes:
        sid = s['id']
        if sid in built['preserveScenes'] and sid in old_scenes:
            scene_changes.append({'sceneId': sid, 'action': 'preserved', 'title': old_scenes[sid].get('title') or sid})
        elif sid not in old_scenes:
            scene_changes.append({'sceneId': sid, 'action': 'added', 'title': s.get('titleOverlay') or sid})
        else:
            prev = old_scenes[sid]
            changed = (
                prev.get('caption') != s.get('caption')
                or prev.get('narration') != s.get('narration')
                or prev.get('title') != (s.get('titleOverlay') or None)
                or prev.get('durationMs') != int(s.get('durationMs') or 4000)
                or prev.get('mediaId') != (s.get('mediaId') or '')
                or prev.get('motionIntent', 'none') != s.get('motionIntent', 'none')
            )
            scene_changes.append({'sceneId': sid, 'action': 'modified' if changed else 'unchanged', 'title': s.get('titleOverlay') or sid})
    new_scene_ids = {s['id'] for s in new_scenes}
    for sid in old_scenes:
        if sid not in new_scene_ids and sid not in built['preserveScenes']:
            scene_changes.append({'sceneId': sid, 'action': 'removed', 'title': old_scenes[sid].get('title') or sid})

    old_cards = {c['id']: c for c in (carousel_req.get('cards') or []) if isinstance(c, dict) and c.get('id')}
    new_cards = planning_doc['creative']['carouselCards']
    card_changes = []
    for idx, c in enumerate(new_cards):
        cid = c['id']
        if cid in built['preserveCards'] and cid in old_cards:
            card_changes.append({'cardId': cid, 'order': idx + 1, 'action': 'preserved', 'title': old_cards[cid].get('title') or cid})
        elif cid not in old_cards:
            card_changes.append({'cardId': cid, 'order': idx + 1, 'action': 'added', 'title': c.get('title') or cid})
        else:
            prev = old_cards[cid]
            changed = (
                prev.get('title') != c.get('title')
                or (prev.get('body') or '') != (c.get('body') or '')
                or (prev.get('mediaId') or '') != (c.get('mediaId') or '')
            )
            card_changes.append({'cardId': cid, 'order': idx + 1, 'action': 'modified' if changed else 'unchanged', 'title': c.get('title') or cid})
    new_card_ids = {c['id'] for c in new_cards}
    for cid in old_cards:
        if cid not in new_card_ids and cid not in built['preserveCards']:
            card_changes.append({'cardId': cid, 'order': None, 'action': 'removed', 'title': old_cards[cid].get('title') or cid})

    review_ch_map = {
        c['profileId']: c for c in ((review_overview or {}).get('channels') or [])
    }
    channel_diffs = []
    for pid, next_copy in sorted(built['targetChannels'].items()):
        prev_copy = (editorial.get('channels') or {}).get(pid) or studio_review.normalize_channel_copy(pid, {})
        next_norm = studio_review.normalize_channel_copy(pid, next_copy)
        changed = prev_copy.get('copySha256') != next_norm.get('copySha256')
        rev_ch = review_ch_map.get(pid) or {}
        will_re_review = changed and rev_ch.get('status') in ('approved', 'changes_requested', 'copy_outdated')
        channel_diffs.append({
            'profileId': pid,
            'changed': changed,
            'preserved': pid in built['preserveChannels'],
            'currentReviewStatus': rev_ch.get('status') or 'none',
            'willRequestChannelReviewOnly': will_re_review,
            'before': {f: prev_copy.get(f, '') for f in studio_review.CHANNEL_COPY_FIELDS},
            'after': {f: next_norm.get(f, '') for f in studio_review.CHANNEL_COPY_FIELDS},
            'flags': (planning_doc['creative']['channelCopies'].get(pid) or {}).get('flags') or [],
        })

    return {
        'briefing': {
            'changed': bool(briefing_changes),
            'changes': briefing_changes,
        },
        'video': {
            'hasScenes': bool(new_scenes),
            'readyToApply': bool(new_scenes) and not built['pendingVideoScenes'] and bool(built['candidateVideoReq']),
            'pendingMediaScenes': built['pendingVideoScenes'],
            'targetProfiles': built['targetVideoProfiles'],
            'sceneCountBefore': len(video_req.get('scenes') or []),
            'sceneCountAfter': len(new_scenes),
            'sceneChanges': scene_changes,
        },
        'carousel': {
            'hasCards': bool(new_cards),
            'readyToApply': bool(new_cards) and not built['pendingCarouselCards'] and bool(built['candidateCarouselReq']),
            'pendingMediaCards': built['pendingCarouselCards'],
            'targetProfile': built['targetCarouselProfile'],
            'cardCountBefore': len(carousel_req.get('cards') or []),
            'cardCountAfter': len(new_cards),
            'cardChanges': card_changes,
        },
        'motion': {
            'sceneIdsForMotion': [s['id'] for s in new_scenes if s.get('motionIntent', 'none') == 'none'],
            'effectsKept': built['motionEffectsKept'],
            'effectsRemoved': built['motionEffectsRemoved'],
            'suggestionsCount': len(built['motionSuggestions']),
            'suggestions': built['motionSuggestions'],
        },
        'channels': channel_diffs,
    }


def _validate_suggestion_with_platform(studio, suggestion_obj, project_rel):
    """Executa validatePlanningSuggestion do nucleo platform via tools/render_bridge.mjs."""
    node = studio_review.render_local.shutil.which('node') if hasattr(studio_review.render_local, 'shutil') else None
    if not node:
        import shutil
        node = shutil.which('node')
    if not node:
        raise RuntimeError('Node.js nao encontrado no PATH para validar sugestao.')
    bridge = os.path.join(studio.root, 'tools', 'render_bridge.mjs')
    project_abs = studio.confine(project_rel)
    os.makedirs(studio.drafts_dir, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='planning-sug-', suffix='.json', dir=studio.drafts_dir)
    os.close(fd)
    try:
        studio_review.atomic_write_json(tmp, suggestion_obj)
        res = subprocess.run(
            [node, bridge, '--planning-suggestion', tmp, '--project', project_abs, '--root', studio.root],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60,
        )
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    raw_out = (res.stdout or '').strip()
    try:
        payload = json.loads(raw_out) if raw_out else None
    except ValueError:
        payload = None
    if not isinstance(payload, dict):
        raise PlanningValidationError(
            res.stderr.strip() or 'Validador do nucleo retornou resposta ilegivel.',
            failure_code='PLANNING_BRIDGE_ERROR',
        )
    if res.returncode != 0 or not payload.get('ok'):
        msg = payload.get('message') or 'Sugestao fora do contrato PlanningSuggestion v1.'
        subject = payload.get('subject')
        code = payload.get('failureCode') or 'PLANNING_SUGGESTION_INVALID'
        action_hint = f' Campo/alvo: "{subject}".' if subject else ''
        raise PlanningValidationError(
            f'{msg}{action_hint} Verifique o JSON retornado e corrija antes de aplicar.',
            failure_code=code,
            subject=subject,
            stage=suggestion_obj.get('stage') if isinstance(suggestion_obj, dict) else None,
        )
    return payload['suggestion']


def _validate_request_with_platform(studio, kind, req_obj):
    import shutil
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Node.js nao encontrado no PATH.')
    bridge = os.path.join(studio.root, 'tools', 'render_bridge.mjs')
    flag = '--carousel-request' if kind == 'carousel' else '--video-request'
    os.makedirs(studio.drafts_dir, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f'planning-apply-{kind}-', suffix='.json', dir=studio.drafts_dir)
    os.close(fd)
    try:
        studio_review.atomic_write_json(tmp, req_obj)
        res = subprocess.run(
            [node, bridge, flag, tmp, '--root', studio.root, '--plan-only'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60,
        )
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    try:
        payload = json.loads((res.stdout or '').strip() or '{}')
    except ValueError:
        payload = {}
    if res.returncode != 0 or not payload.get('ok'):
        err_code = payload.get('failureCode') or 'REQUEST_INVALID'
        subj = payload.get('subject') or ''
        raise PlanningValidationError(
            f'Falha ao validar {kind} gerado pelo planejamento ({err_code} {subj}).',
            failure_code=err_code,
            subject=subj,
        )
    return payload


def build_planning_overview(studio, work_id):
    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, motion_plan, listing = studio_review._read_work_core(studio, work_id)
        editorial = studio_review._load_editorial_doc(studio, work_id, wpaths)
        work_media = _build_work_media_catalog(studio, wpaths, video_req, carousel_req)
        planning_doc, allowed_profiles, is_marca_salao = _load_planning_doc(
            studio, work_id, work_doc, wpaths, editorial, listing, work_media
        )
        fps = _compute_context_fingerprints(planning_doc, editorial, video_req, carousel_req, motion_plan)
        analysis = _analyze_planning_state(planning_doc, editorial, fps, work_media, is_marca_salao)
        review_overview = studio_review.build_review_overview(studio, work_id)
        diff = compute_editors_diff(
            studio, work_id, planning_doc, editorial, video_req, carousel_req, motion_plan,
            work_media, allowed_profiles, review_overview=review_overview,
        )
        llm_cfg = llm_adapter.load_llm_config(studio)
        return {
            'work': work_doc,
            'stageLabels': STAGE_LABELS,
            'currentStageLabel': STAGE_LABELS.get(planning_doc['currentStage'], planning_doc['currentStage']),
            'planning': planning_doc,
            'editorialBriefing': editorial['briefing'],
            'allowedProfiles': allowed_profiles,
            'workMedia': work_media,
            'fingerprints': fps,
            'analysis': analysis,
            'editorsDiff': diff,
            'llmConfig': llm_cfg,
            'imageExtensionPoint': llm_adapter.ImageProviderExtensionPoint.status(),
            'isMarcaSalao': is_marca_salao,
        }


def save_planning(studio, work_id, body):
    if not isinstance(body, dict):
        raise ValueError('payload de planejamento invalido')
    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, motion_plan, listing = studio_review._read_work_core(studio, work_id)
        editorial = studio_review._load_editorial_doc(studio, work_id, wpaths)
        work_media = _build_work_media_catalog(studio, wpaths, video_req, carousel_req)
        planning_doc, allowed_profiles, is_marca_salao = _load_planning_doc(
            studio, work_id, work_doc, wpaths, editorial, listing, work_media
        )
        fps_before = _compute_context_fingerprints(planning_doc, editorial, video_req, carousel_req, motion_plan)

        expected_ctx = body.get('expectedContextFingerprint')
        if expected_ctx is not None and expected_ctx != fps_before['contextFingerprint']:
            raise studio_review.ReviewVersionConflictError(
                'O planejamento, o briefing ou um editor mudou enquanto voce editava. Atualize a aba Planejamento para ver as alteracoes mais recentes.'
            )

        if 'currentStage' in body and body['currentStage'] in PLANNING_STAGES:
            planning_doc['currentStage'] = body['currentStage']
        if 'ideaText' in body:
            planning_doc['ideaText'] = str(body['ideaText'] or '').strip()
        if isinstance(body.get('briefing'), dict):
            merged_b = dict(planning_doc['briefing'])
            for f in studio_review.EDITORIAL_FIELDS:
                if f in body['briefing']:
                    merged_b[f] = str(body['briefing'][f] or '').strip()
            planning_doc['briefing'] = studio_review.normalize_briefing(merged_b)
        if isinstance(body.get('briefingExtended'), dict):
            ext_in = body['briefingExtended']
            allowed_ids = {p['id'] for p in allowed_profiles}
            if 'product' in ext_in:
                planning_doc['briefingExtended']['product'] = str(ext_in.get('product') or '').strip()
            if 'tone' in ext_in:
                planning_doc['briefingExtended']['tone'] = str(ext_in.get('tone') or '').strip()
            if isinstance(ext_in.get('recommendedProfiles'), list):
                planning_doc['briefingExtended']['recommendedProfiles'] = [
                    pid for pid in ext_in['recommendedProfiles'] if isinstance(pid, str) and pid in allowed_ids
                ] or _default_recommended_profiles(allowed_profiles)
        if isinstance(body.get('gaps'), list):
            planning_doc['gaps'] = [str(g).strip() for g in body['gaps'] if str(g).strip()]
        if isinstance(body.get('questions'), list):
            planning_doc['questions'] = _normalize_questions(body['questions'])
        if isinstance(body.get('claims'), list):
            planning_doc['claims'] = _normalize_claims(
                body['claims'], {m['id'] for m in work_media}, is_marca_salao
            )
        if isinstance(body.get('creative'), dict):
            norm_c = _normalize_creative(
                body['creative'], {p['id'] for p in allowed_profiles}, is_marca_salao
            )
            if body.get('markCreativeChecked') or not norm_c.get('basedOnBriefingSha256'):
                norm_c['basedOnBriefingSha256'] = _briefing_payload_hash(
                    planning_doc['briefing'], planning_doc['briefingExtended']
                )
            else:
                norm_c['basedOnBriefingSha256'] = (
                    planning_doc['creative'].get('basedOnBriefingSha256')
                    or _briefing_payload_hash(planning_doc['briefing'], planning_doc['briefingExtended'])
                )
            planning_doc['creative'] = norm_c

        if body.get('syncFromEditorialBriefing'):
            planning_doc['briefing'] = dict(editorial['briefing'])
            planning_doc['lastSyncedEditorialBriefingSha256'] = editorial_sha_default(editorial['briefing'])

        _save_planning_doc(studio, wpaths, planning_doc)
        return build_planning_overview(studio, work_id)


def build_stage_prompt(studio, work_id, stage):
    if stage not in ('briefing', 'creative'):
        raise ValueError('etapa de prompt invalida (use "briefing" ou "creative")')
    overview = build_planning_overview(studio, work_id)
    work_doc = overview['work']
    planning = overview['planning']
    allowed_profiles = overview['allowedProfiles']
    allowed_ids = [p['id'] for p in allowed_profiles]
    is_marca_salao = overview['isMarcaSalao']
    work_media = overview['workMedia']

    rules = [
        'Responda EXCLUSIVAMENTE com um unico objeto JSON valido seguindo PlanningSuggestion v1.',
        'Video local tem ZERO faixas de audio (-an). Separe sempre: caption (legenda SRT), narration (texto para narracao externa) e postText (texto de publicacao do canal).',
        f'Use apenas perfis permitidos pelo projeto: {", ".join(allowed_ids)}.',
        'Nao invente metricas nao comprovadas. Sinalize promessas comerciais ou URLs em claims/flags.',
    ]
    if is_marca_salao:
        rules.extend([
            'RESTRICAO MARCA SALAO (TEMPLATE-BRIEFING.md): nunca atribuir envio automatico de mensagens, lembretes, WhatsApp/SMS ou reducao garantida de faltas ao Marca Salao.',
            'CTA padrao Marca Salao: Instagram orienta "link na bio" (com confirmacao de link ativo); Facebook orienta "URL completa https://marcasalao.com.br + link da descricao".',
        ])
    else:
        rules.append(
            f'Projeto ativo: {work_doc.get("projectId") or work_doc["id"]}. Respeite as afirmacoes comprovadas e o publico deste projeto sem misturar marcas.'
        )

    if stage == 'briefing':
        context = {
            'projectId': work_doc.get('projectId'),
            'allowedProfiles': [
                {'id': p['id'], 'network': p.get('network'), 'mediaKind': p.get('mediaKind'), 'format': p.get('format')}
                for p in allowed_profiles
            ],
            'ideaText': planning['ideaText'],
            'currentBriefing': planning['briefing'],
            'briefingExtended': planning['briefingExtended'],
            'answeredQuestions': [
                {'id': q['id'], 'dimension': q['dimension'], 'question': q['question'], 'answer': q['answer']}
                for q in planning['questions']
            ],
            'existingClaims': planning['claims'],
            'availableWorkMedia': [{'id': m['id'], 'type': m['type'], 'name': m['name']} for m in work_media],
        }
        schema_example = {
            'schemaVersion': 1,
            'stage': 'briefing',
            'product': 'Nome do produto ou funcionalidade',
            'objective': 'Objetivo claro da campanha',
            'audience': 'Publico especifico',
            'coreMessage': 'Mensagem central em uma frase',
            'supportEvidence': 'Evidencia visual ou prova disponivel',
            'cta': 'Chamada para acao principal',
            'tone': 'Tom de voz (ex.: objetivo e pratico)',
            'recommendedProfiles': allowed_ids[:2] if len(allowed_ids) >= 2 else allowed_ids,
            'gaps': ['Lista objetiva do que ainda falta confirmar'],
            'questions': [
                {'id': 'q-evidencia', 'dimension': 'supportEvidence', 'question': 'Qual tela do trabalho comprova o beneficio?', 'suggestedAnswer': 'Resposta sugerida curta'},
            ],
            'claims': [
                {'id': 'claim-1', 'statement': 'Afirmacao principal', 'status': 'pending_validation', 'requiresConfirmation': True, 'warning': 'Motivo se precisar confirmacao'},
            ],
        }
        system_prompt = (
            'Voce e um estrategista de conteudo aplicando o metodo Blank Page: esclareca lacunas, '
            'faca perguntas curtas e sinalize afirmacoes nao confirmadas antes de gerar roteiros. '
            + ' '.join(rules)
        )
        user_prompt = (
            'Analise a ideia livre e o contexto abaixo para consolidar a Etapa 1 (Briefing).\n\n'
            f'CONTEXTO DA ETAPA:\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n'
            f'FORMATO JSON EXATO ESPERADO:\n{json.dumps(schema_example, ensure_ascii=False, indent=2)}'
        )
    else:
        context = {
            'projectId': work_doc.get('projectId'),
            'allowedProfiles': [
                {'id': p['id'], 'network': p.get('network'), 'mediaKind': p.get('mediaKind'), 'format': p.get('format')}
                for p in allowed_profiles
            ],
            'briefing': planning['briefing'],
            'briefingExtended': planning['briefingExtended'],
            'claims': planning['claims'],
            'availableWorkMedia': [{'id': m['id'], 'type': m['type'], 'name': m['name']} for m in work_media],
        }
        rec_p = planning['briefingExtended']['recommendedProfiles'] or allowed_ids[:2]
        schema_example = {
            'schemaVersion': 1,
            'stage': 'creative',
            'hookOptions': [
                {'id': 'hook-1', 'text': 'Primeira opcao de gancho', 'angle': 'dor-pratica'},
                {'id': 'hook-2', 'text': 'Segunda opcao de gancho', 'angle': 'clareza'},
            ],
            'selectedHookId': 'hook-1',
            'scriptSummary': 'Resumo objetivo em 3 passos.',
            'videoScenes': [
                {
                    'id': 'cena-gancho',
                    'objective': 'Chamar atencao para o problema',
                    'narrativeFunction': 'hook',
                    'durationMs': 4000,
                    'titleOverlay': 'Titulo curto de tela',
                    'caption': 'Legenda curta para o SRT da cena 1.',
                    'narration': 'Texto falado separado para o locutor da cena 1.',
                    'requiredMediaDescriptor': 'Tela ou imagem de abertura correspondente ao gancho',
                    'motionIntent': 'none',
                },
                {
                    'id': 'cena-prova',
                    'objective': 'Demonstrar a solucao na pratica',
                    'narrativeFunction': 'demonstration',
                    'durationMs': 4000,
                    'titleOverlay': 'Demonstracao real',
                    'caption': 'Legenda SRT da segunda cena.',
                    'narration': 'Texto de narracao da segunda cena.',
                    'requiredMediaDescriptor': 'Captura da funcionalidade em foco',
                    'motionIntent': 'none',
                },
            ],
            'carouselCards': [
                {'id': 'capa', 'role': 'cover', 'title': 'Titulo de capa', 'body': 'Subtitulo direto', 'requiredMediaDescriptor': 'Imagem limpa de capa'},
                {'id': 'passo-1', 'role': 'content', 'title': 'Ponto central', 'body': 'Explicacao breve'},
                {'id': 'fechamento', 'role': 'cta', 'title': 'Conheca agora', 'body': 'Chamada alinhada ao canal'},
            ],
            'channelCopies': [
                {
                    'profileId': pid,
                    'title': 'Titulo do post',
                    'postText': f'Texto de publicacao adaptado para {pid}.',
                    'cta': 'Chamada para acao',
                    'destinationUrl': 'https://...',
                    'hashtags': '#exemplo',
                    'flags': ['Confirmar URL e CTA antes de aprovar'],
                }
                for pid in rec_p
            ],
            'motionSuggestions': [
                {
                    'sceneId': 'cena-prova',
                    'targetElement': 'Area ou bloco principal a destacar na cena sem zoom',
                    'suggestedColor': '#FFD700',
                    'suggestedStartMs': 500,
                    'suggestedEndMs': 3000,
                    'note': 'O operador marcara o retangulo exato no editor Motion.',
                },
            ],
        }
        system_prompt = (
            'Voce e um roteirista e editor social que prepara opcoes de hook, cenas de video sem audio, '
            'carrossel estruturado e textos de publicacao por canal usando apenas contratos estruturados. '
            + ' '.join(rules)
        )
        user_prompt = (
            'Com base no briefing consolidado abaixo, proponha a Etapa 2 (Hook, roteiro, carrossel e textos por canal).\n\n'
            f'CONTEXTO DA ETAPA:\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n'
            f'FORMATO JSON EXATO ESPERADO:\n{json.dumps(schema_example, ensure_ascii=False, indent=2)}'
        )

    full_prompt = f'[SISTEMA]\n{system_prompt}\n\n[INSTRUCAO DA ETAPA: {stage}]\n{user_prompt}'
    return {
        'workId': work_id,
        'stage': stage,
        'contextFingerprint': overview['fingerprints']['contextFingerprint'],
        'briefingSha256': overview['fingerprints']['briefingSha256'],
        'systemPrompt': system_prompt,
        'userPrompt': user_prompt,
        'promptText': full_prompt,
        'contextObject': context,
        'allowedProfiles': allowed_ids,
    }


def _compute_suggestion_diff(planning_doc, validated_suggestion, work_doc, allowed_profiles, is_marca_salao):
    stage = validated_suggestion['stage']
    if stage == 'briefing':
        cur_b = planning_doc['briefing']
        cur_ext = planning_doc['briefingExtended']
        fields = [
            ('product', 'Produto', cur_ext.get('product', ''), validated_suggestion['product']),
            ('objective', 'Objetivo', cur_b.get('objective', ''), validated_suggestion['objective']),
            ('audience', 'Publico-alvo', cur_b.get('audience', ''), validated_suggestion['audience']),
            ('coreMessage', 'Mensagem central', cur_b.get('coreMessage', ''), validated_suggestion['coreMessage']),
            ('supportEvidence', 'Evidencia de apoio', cur_b.get('supportEvidence', ''), validated_suggestion['supportEvidence']),
            ('cta', 'CTA geral', cur_b.get('cta', ''), validated_suggestion['cta']),
            ('tone', 'Tom', cur_ext.get('tone', ''), validated_suggestion['tone']),
            ('recommendedProfiles', 'Perfis recomendados', ', '.join(cur_ext.get('recommendedProfiles', [])), ', '.join(validated_suggestion['recommendedProfiles'])),
        ]
        changed_fields = [
            {'field': f, 'label': lbl, 'before': bef, 'after': aft}
            for f, lbl, bef, aft in fields if bef != aft
        ]
        return {
            'stage': 'briefing',
            'changedFields': changed_fields,
            'questionsCount': len(validated_suggestion['questions']),
            'claimsCount': len(validated_suggestion['claims']),
            'gapsCount': len(validated_suggestion['gaps']),
        }

    # stage == 'creative'
    old_scenes = {s['id'] for s in planning_doc['creative']['videoScenes']}
    new_scenes = [s['id'] for s in validated_suggestion['videoScenes']]
    old_cards = {c['id'] for c in planning_doc['creative']['carouselCards']}
    new_cards = [c['id'] for c in validated_suggestion['carouselCards']]
    old_channels = set(planning_doc['creative']['channelCopies'].keys())
    new_channels = [c['profileId'] for c in validated_suggestion['channelCopies']]
    return {
        'stage': 'creative',
        'hookOptionsCount': len(validated_suggestion['hookOptions']),
        'selectedHookId': validated_suggestion.get('selectedHookId') or validated_suggestion['hookOptions'][0]['id'],
        'videoScenesAdded': [sid for sid in new_scenes if sid not in old_scenes],
        'videoScenesUpdated': [sid for sid in new_scenes if sid in old_scenes],
        'carouselCardsAdded': [cid for cid in new_cards if cid not in old_cards],
        'carouselCardsUpdated': [cid for cid in new_cards if cid in old_cards],
        'channelsProposed': new_channels,
        'channelsAlreadyPresent': [pid for pid in new_channels if pid in old_channels],
        'motionSuggestionsCount': len(validated_suggestion.get('motionSuggestions') or []),
    }


def _collect_suggestion_warnings(validated_suggestion, is_marca_salao):
    warnings = []
    if validated_suggestion['stage'] == 'briefing':
        texts = [
            validated_suggestion['product'],
            validated_suggestion['objective'],
            validated_suggestion['audience'],
            validated_suggestion['coreMessage'],
            validated_suggestion['supportEvidence'],
            validated_suggestion['cta'],
        ] + [c['statement'] for c in validated_suggestion['claims']]
        for t in texts:
            for w in _scan_text_warnings(t, is_marca_salao=is_marca_salao):
                if w not in warnings:
                    warnings.append(w)
    else:
        texts = [validated_suggestion['scriptSummary']]
        for h in validated_suggestion['hookOptions']:
            texts.append(h['text'])
        for s in validated_suggestion['videoScenes']:
            texts.extend([s['titleOverlay'], s['caption'], s['narration']])
        for c in validated_suggestion['carouselCards']:
            texts.extend([c['title'], c.get('body') or ''])
        for ch in validated_suggestion['channelCopies']:
            texts.extend([ch['title'], ch['postText'], ch['cta'], ch['destinationUrl']])
        for t in texts:
            for w in _scan_text_warnings(t, is_marca_salao=is_marca_salao):
                if w not in warnings:
                    warnings.append(w)
    return warnings


def validate_and_stage_suggestion(studio, work_id, body, mode='import', model_name=None):
    if not isinstance(body, dict):
        raise ValueError('payload de importacao invalido')
    expected_stage = str(body.get('stage') or '').strip() or None
    if expected_stage and expected_stage not in ('briefing', 'creative'):
        raise ValueError('etapa esperada invalida (use "briefing" ou "creative")')

    overview = build_planning_overview(studio, work_id)
    fps = overview['fingerprints']
    expected_ctx = body.get('expectedContextFingerprint')
    if expected_ctx is not None and expected_ctx != fps['contextFingerprint']:
        raise studio_review.ReviewVersionConflictError(
            'O planejamento, o briefing ou os editores mudaram enquanto voce preparava a resposta; atualize o contexto antes de importar.'
        )

    if isinstance(body.get('suggestion'), dict):
        raw_obj = body['suggestion']
    else:
        raw_obj = llm_adapter.extract_json_object_from_text(body.get('rawText') or '')

    if expected_stage and raw_obj.get('stage') != expected_stage:
        raise PlanningValidationError(
            f'A resposta recebida pertence a etapa "{raw_obj.get("stage")}", mas voce selecionou "{expected_stage}". Corrija o campo "stage" ou selecione a etapa certa.',
            failure_code='PLANNING_STAGE_MISMATCH',
            subject='stage',
            stage=expected_stage,
        )

    validated = _validate_suggestion_with_platform(studio, raw_obj, overview['work']['project'])
    warnings = _collect_suggestion_warnings(validated, overview['isMarcaSalao'])
    diff_preview = _compute_suggestion_diff(
        overview['planning'], validated, overview['work'], overview['allowedProfiles'], overview['isMarcaSalao']
    )

    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, motion_plan, listing = studio_review._read_work_core(studio, work_id)
        editorial = studio_review._load_editorial_doc(studio, work_id, wpaths)
        work_media = _build_work_media_catalog(studio, wpaths, video_req, carousel_req)
        planning_doc, _, _ = _load_planning_doc(
            studio, work_id, work_doc, wpaths, editorial, listing, work_media
        )
        sug_id = f'sug-{uuid.uuid4().hex[:10]}'
        record = {
            'suggestionId': sug_id,
            'schemaVersion': 1,
            'stage': validated['stage'],
            'mode': mode,
            'model': model_name,
            'createdAt': studio_review.now_iso(),
            'baseContextFingerprint': fps['contextFingerprint'],
            'baseBriefingSha256': fps['briefingSha256'],
            'baseEditorialBriefingSha256': fps['editorialBriefingSha256'],
            'baseDraftsSha256': fps['draftsSha256'],
            'warnings': warnings,
            'diffPreview': diff_preview,
            'suggestion': validated,
        }
        planning_doc['suggestionHistory'].append(record)
        planning_doc['suggestionHistory'] = planning_doc['suggestionHistory'][-25:]
        _save_planning_doc(studio, wpaths, planning_doc)

    refreshed = build_planning_overview(studio, work_id)
    return {
        'suggestionRecord': record,
        'diffPreview': diff_preview,
        'warnings': warnings,
        'overview': refreshed,
    }


def generate_with_local_model(studio, work_id, body):
    if not isinstance(body, dict):
        raise ValueError('payload de geracao invalido')
    stage = str(body.get('stage') or 'briefing').strip()
    prompt_info = build_stage_prompt(studio, work_id, stage)
    expected_ctx = body.get('expectedContextFingerprint')
    if expected_ctx is not None and expected_ctx != prompt_info['contextFingerprint']:
        raise studio_review.ReviewVersionConflictError(
            'O briefing ou os editores mudaram antes de chamar o modelo local; atualize a tela e tente novamente.'
        )

    cfg = llm_adapter.load_llm_config(studio)
    if isinstance(body.get('llmConfig'), dict):
        cfg = llm_adapter.normalize_llm_config(body['llmConfig'], fallback=cfg)
    adapter = llm_adapter.TextModelAdapter(cfg)
    llm_res = adapter.request_stage_json(stage, prompt_info['systemPrompt'], prompt_info['userPrompt'])

    staged = validate_and_stage_suggestion(
        studio,
        work_id,
        {
            'stage': stage,
            'suggestion': llm_res['parsed'],
            'expectedContextFingerprint': prompt_info['contextFingerprint'],
        },
        mode='local-llm',
        model_name=llm_res['model'],
    )
    staged['llmResponseMeta'] = {
        'endpoint': llm_res['endpoint'],
        'model': llm_res['model'],
        'stage': stage,
    }
    return staged


def accept_suggestion(studio, work_id, body):
    """Incorpora uma sugestao validada no rascunho de planejamento preservando escolhas do operador."""
    if not isinstance(body, dict):
        raise ValueError('payload de aceite invalido')
    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, motion_plan, listing = studio_review._read_work_core(studio, work_id)
        editorial = studio_review._load_editorial_doc(studio, work_id, wpaths)
        work_media = _build_work_media_catalog(studio, wpaths, video_req, carousel_req)
        planning_doc, allowed_profiles, is_marca_salao = _load_planning_doc(
            studio, work_id, work_doc, wpaths, editorial, listing, work_media
        )
        fps = _compute_context_fingerprints(planning_doc, editorial, video_req, carousel_req, motion_plan)

        expected_ctx = body.get('expectedContextFingerprint')
        if expected_ctx is not None and expected_ctx != fps['contextFingerprint']:
            raise studio_review.ReviewVersionConflictError(
                'Conflito de versao: o briefing ou os editores mudaram antes da incorporacao da sugestao. Atualize e confira a diferenca.'
            )

        sug_id = str(body.get('suggestionId') or '').strip()
        record = next((r for r in planning_doc['suggestionHistory'] if r.get('suggestionId') == sug_id), None)
        if not record:
            raise ValueError(f'Sugestao "{sug_id}" nao encontrada no historico deste trabalho.')

        allow_outdated = bool(body.get('allowOutdated'))
        if not allow_outdated and record.get('baseContextFingerprint') != fps['contextFingerprint']:
            raise studio_review.ReviewVersionConflictError(
                'Esta sugestao ficou desatualizada porque o briefing, planejamento ou editor mudou apos ela ser gerada.'
            )

        sug = record['suggestion']
        allowed_ids = {p['id'] for p in allowed_profiles}
        media_ids = {m['id'] for m in work_media}

        if sug['stage'] == 'briefing':
            preserve_fields = set(body.get('preserveBriefingFields') or [])
            if 'product' not in preserve_fields:
                planning_doc['briefingExtended']['product'] = sug['product']
            if 'tone' not in preserve_fields:
                planning_doc['briefingExtended']['tone'] = sug['tone']
            if 'recommendedProfiles' not in preserve_fields:
                planning_doc['briefingExtended']['recommendedProfiles'] = [
                    pid for pid in sug['recommendedProfiles'] if pid in allowed_ids
                ] or _default_recommended_profiles(allowed_profiles)
            for f in ('objective', 'audience', 'coreMessage', 'supportEvidence', 'cta'):
                if f not in preserve_fields:
                    planning_doc['briefing'][f] = sug[f]
            planning_doc['gaps'] = list(sug.get('gaps') or [])

            if not body.get('preserveQuestions'):
                prev_answers = {q['dimension']: q.get('answer', '') for q in planning_doc['questions']}
                merged_qs = []
                for q in sug['questions']:
                    dim = q['dimension']
                    merged_qs.append({
                        **q,
                        'answer': prev_answers.get(dim) or '',
                    })
                planning_doc['questions'] = _normalize_questions(merged_qs)

            if not body.get('preserveClaims'):
                planning_doc['claims'] = _normalize_claims(sug['claims'], media_ids, is_marca_salao)
            if planning_doc['currentStage'] == 'briefing':
                planning_doc['currentStage'] = 'creative'
        else:
            cr = planning_doc['creative']
            if not body.get('preserveHook'):
                cr['hookOptions'] = list(sug['hookOptions'])
                cr['selectedHookId'] = sug.get('selectedHookId') or sug['hookOptions'][0]['id']
                sel_hook_obj = next((h for h in cr['hookOptions'] if h['id'] == cr['selectedHookId']), None)
                if sel_hook_obj and not body.get('preserveBriefingHook'):
                    planning_doc['briefing']['hook'] = sel_hook_obj['text']
            if not body.get('preserveScriptSummary'):
                cr['scriptSummary'] = sug['scriptSummary']
                planning_doc['briefing']['scriptSummary'] = sug['scriptSummary']

            preserve_scenes = set(body.get('preserveSceneIds') or [])
            if preserve_scenes:
                kept = {s['id']: s for s in cr['videoScenes'] if s['id'] in preserve_scenes}
                merged_scenes = []
                seen = set()
                for s in sug['videoScenes']:
                    sid = s['id']
                    seen.add(sid)
                    merged_scenes.append(kept[sid] if sid in kept else dict(s))
                for sid, s in kept.items():
                    if sid not in seen:
                        merged_scenes.append(s)
                cr['videoScenes'] = merged_scenes
            else:
                # Preserva midia ja escolhida pelo operador se ID coincidir
                old_media = {s['id']: s.get('mediaId', '') for s in cr['videoScenes']}
                cr['videoScenes'] = [
                    {**s, 'mediaId': s.get('mediaId') or old_media.get(s['id'], '')}
                    for s in sug['videoScenes']
                ]

            preserve_cards = set(body.get('preserveCardIds') or [])
            if preserve_cards:
                kept_c = {c['id']: c for c in cr['carouselCards'] if c['id'] in preserve_cards}
                merged_cards = []
                seen_c = set()
                for c in sug['carouselCards']:
                    cid = c['id']
                    seen_c.add(cid)
                    merged_cards.append(kept_c[cid] if cid in kept_c else dict(c))
                for cid, c in kept_c.items():
                    if cid not in seen_c:
                        merged_cards.append(c)
                cr['carouselCards'] = merged_cards
            else:
                cr['carouselCards'] = list(sug['carouselCards'])

            preserve_ch = set(body.get('preserveChannelIds') or [])
            next_ch = {}
            for pid, existing_copy in cr['channelCopies'].items():
                if pid in preserve_ch:
                    next_ch[pid] = dict(existing_copy)
            for ch in sug['channelCopies']:
                pid = ch['profileId']
                if pid in preserve_ch and pid in next_ch:
                    continue
                if pid in allowed_ids:
                    next_ch[pid] = dict(ch)
            cr['channelCopies'] = next_ch

            if not body.get('preserveMotionSuggestions'):
                cr['motionSuggestions'] = list(sug.get('motionSuggestions') or [])

            cr['basedOnBriefingSha256'] = fps['briefingSha256']
            planning_doc['creative'] = _normalize_creative(cr, allowed_ids, is_marca_salao)
            planning_doc['currentStage'] = 'apply'

        _save_planning_doc(studio, wpaths, planning_doc)
        return build_planning_overview(studio, work_id)


def apply_planning_to_editors(studio, work_id, body):
    if not isinstance(body, dict):
        raise ValueError('payload de aplicacao invalido')
    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, motion_plan, listing = studio_review._read_work_core(studio, work_id)
        editorial = studio_review._load_editorial_doc(studio, work_id, wpaths)
        work_media = _build_work_media_catalog(studio, wpaths, video_req, carousel_req)
        planning_doc, allowed_profiles, is_marca_salao = _load_planning_doc(
            studio, work_id, work_doc, wpaths, editorial, listing, work_media
        )
        fps = _compute_context_fingerprints(planning_doc, editorial, video_req, carousel_req, motion_plan)

        expected_ctx = body.get('expectedContextFingerprint')
        if expected_ctx is not None and expected_ctx != fps['contextFingerprint']:
            raise studio_review.ReviewVersionConflictError(
                'O briefing ou os rascunhos nos editores foram alterados por outra edicao. Atualize a diferenca antes de aplicar para nao sobrescrever alteracoes recentes.'
            )
        expected_ed = body.get('expectedEditorialBriefingSha256')
        if expected_ed is not None and expected_ed != fps['editorialBriefingSha256']:
            raise studio_review.ReviewVersionConflictError(
                'A ficha editorial foi alterada apos a leitura desta tela. Recarregue antes de aplicar.'
            )
        expected_drafts = body.get('expectedDraftsSha256')
        if expected_drafts is not None and expected_drafts != fps['draftsSha256']:
            raise studio_review.ReviewVersionConflictError(
                'Um editor (Video, Carrossel ou Motion) foi alterado enquanto voce revisava a aplicacao. Confira a diferenca atual.'
            )

        built = _build_target_drafts_from_planning(
            studio, work_doc, wpaths, planning_doc, editorial, video_req, carousel_req, motion_plan,
            work_media, allowed_profiles, selection=body
        )

        apply_briefing = bool(body.get('applyBriefing', False))
        apply_video = bool(body.get('applyVideo', False))
        apply_carousel = bool(body.get('applyCarousel', False))
        apply_motion_sync = bool(body.get('applyMotionSync', False))
        channels_to_apply = body.get('channelsToApply')
        if channels_to_apply is True:
            channels_to_apply = list(built['targetChannels'].keys())
        elif not isinstance(channels_to_apply, list):
            channels_to_apply = []
        channels_to_apply = [
            pid for pid in channels_to_apply
            if pid in built['targetChannels'] and pid not in built['preserveChannels']
        ]

        # Validacoes antecipadas no nucleo antes de qualquer escrita
        if apply_video and not built['pendingVideoScenes']:
            if not planning_doc['creative']['videoScenes']:
                raise PlanningValidationError('Nenhuma cena no roteiro de planejamento para aplicar ao editor de Video.')
            if not built['candidateVideoReq']:
                raise PlanningValidationError('Projeto nao possui perfil compativel com Video para aplicar este roteiro.')
            _validate_request_with_platform(studio, 'video', built['candidateVideoReq'])

        if apply_carousel and not built['pendingCarouselCards']:
            if len(planning_doc['creative']['carouselCards']) < 2:
                raise PlanningValidationError('Proponha ao menos 2 cards no planejamento antes de aplicar ao Carrossel.')
            if not built['candidateCarouselReq']:
                raise PlanningValidationError('Projeto nao possui perfil compativel com Carrossel 1:1 para aplicar estes cards.')
            _validate_request_with_platform(studio, 'carousel', built['candidateCarouselReq'])

        results = {
            'briefing': {'status': 'skipped'},
            'video': {'status': 'skipped'},
            'carousel': {'status': 'skipped'},
            'motion': {'status': 'skipped'},
            'channels': {},
        }

        # 1. Briefing e textos por canal -> studio_review.save_editorial (preserva canais/revisoes nao tocados)
        editorial_save_payload = {}
        if apply_briefing:
            editorial_save_payload['briefing'] = dict(planning_doc['briefing'])
        if channels_to_apply:
            editorial_save_payload['channels'] = {
                pid: built['targetChannels'][pid] for pid in channels_to_apply
            }
        if editorial_save_payload:
            studio_review.save_editorial(studio, work_id, editorial_save_payload)
            if apply_briefing:
                planning_doc['lastSyncedEditorialBriefingSha256'] = editorial_sha_default(planning_doc['briefing'])
                results['briefing'] = {'status': 'applied'}
            for pid in channels_to_apply:
                results['channels'][pid] = {'status': 'applied'}

        # 2. VideoRequest & Motion sync
        video_written = False
        if apply_video:
            if built['pendingVideoScenes']:
                results['video'] = {
                    'status': 'pending_media',
                    'pendingScenes': built['pendingVideoScenes'],
                    'message': 'Cenas sem arquivo de midia local selecionado ficaram pendentes: escolha um arquivo do trabalho para aplicar o VideoRequest.',
                }
            else:
                studio_review.atomic_write_json(
                    studio.confine_workspace(wpaths['videoDraft']),
                    built['candidateVideoReq'],
                )
                video_written = True
                results['video'] = {
                    'status': 'applied',
                    'profiles': built['candidateVideoReq']['profiles'],
                    'sceneIds': [s['id'] for s in built['candidateVideoReq']['scenes']],
                }

        if apply_motion_sync or video_written:
            active_vreq = built['candidateVideoReq'] if video_written else video_req
            none_ids = {s['id'] for s in (active_vreq.get('scenes') or []) if s.get('motionIntent', 'none') == 'none'}
            kept_effects = [e for e in (motion_plan.get('effects') or []) if e.get('sceneId') in none_ids]
            next_motion = {
                'schemaVersion': 1,
                'requestId': active_vreq.get('id') or f"{work_doc['id']}-video",
                'effects': kept_effects,
            }
            studio_review.atomic_write_json(studio.confine_workspace(wpaths['motionPlan']), next_motion)
            results['motion'] = {
                'status': 'synced',
                'requestId': next_motion['requestId'],
                'sceneIds': [s['id'] for s in (active_vreq.get('scenes') or [])],
                'effectsKept': len(kept_effects),
                'suggestionsCount': len(built['motionSuggestions']),
            }

        # 3. CarouselRequest
        if apply_carousel:
            if built['pendingCarouselCards']:
                results['carousel'] = {
                    'status': 'pending_media',
                    'pendingCards': built['pendingCarouselCards'],
                    'message': 'Cards com mediaId ausente/invalido ficaram pendentes ate selecionar imagem local do trabalho.',
                }
            else:
                studio_review.atomic_write_json(
                    studio.confine_workspace(wpaths['carouselDraft']),
                    built['candidateCarouselReq'],
                )
                results['carousel'] = {
                    'status': 'applied',
                    'profile': built['candidateCarouselReq']['profile'],
                    'cardIds': [c['id'] for c in built['candidateCarouselReq']['cards']],
                }

        planning_doc['currentStage'] = 'apply'
        planning_doc['lastApplied'] = {
            'appliedAt': studio_review.now_iso(),
            'briefingSha256': fps['briefingSha256'],
            'results': results,
        }
        _save_planning_doc(studio, wpaths, planning_doc)

        # Atualiza work.json updatedAt
        work_abs = studio.confine_workspace(wpaths['workFile'])
        work_doc['updatedAt'] = studio_review.now_iso()
        studio_review.atomic_write_json(work_abs, work_doc)

        return {
            'applied': results,
            'overview': build_planning_overview(studio, work_id),
            'workData': studio.open_work(work_id),
        }


def preview_editors_diff(studio, work_id, body=None):
    selection = body if isinstance(body, dict) else {}
    with studio_review._STATE_LOCK:
        work_doc, wpaths, video_req, carousel_req, motion_plan, listing = studio_review._read_work_core(studio, work_id)
        editorial = studio_review._load_editorial_doc(studio, work_id, wpaths)
        work_media = _build_work_media_catalog(studio, wpaths, video_req, carousel_req)
        planning_doc, allowed_profiles, _ = _load_planning_doc(
            studio, work_id, work_doc, wpaths, editorial, listing, work_media
        )
        review_overview = studio_review.build_review_overview(studio, work_id)
        diff = compute_editors_diff(
            studio, work_id, planning_doc, editorial, video_req, carousel_req, motion_plan,
            work_media, allowed_profiles, review_overview=review_overview, selection=selection,
        )
        return {'editorsDiff': diff}

