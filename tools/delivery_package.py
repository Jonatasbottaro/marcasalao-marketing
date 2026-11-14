"""Empacotador transacional de entrega final em ZIP do Video Studio.

Valida aprovacao humana, versao esperada, confinamento na raiz e integridade
SHA-256 de todos os arquivos selecionados antes de montar em staging exclusivo e
promover sob lock com backup/rollback atomico.
"""

import hashlib
import json
import os
import shutil
import tempfile
import uuid
import zipfile

import render_local
import studio_review

PACKAGE_ZIP_NAME = 'delivery-package.zip'
PACKAGE_MANIFEST_NAME = 'package-manifest.json'
PACKAGE_INDEX_NAME = 'index.json'


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _format_briefing_txt(work_doc, editorial):
    b = editorial['briefing']
    lines = [
        f"Ficha editorial - {work_doc.get('name', work_doc.get('id', ''))}",
        f"Trabalho: {work_doc.get('id', '')}",
        f"Projeto: {work_doc.get('projectId') or work_doc.get('project', '')}",
        '',
        f"Objetivo: {b.get('objective') or '-'}",
        f"Publico-alvo: {b.get('audience') or '-'}",
        f"Mensagem principal: {b.get('coreMessage') or '-'}",
        f"Prova / argumento de apoio: {b.get('supportEvidence') or '-'}",
        f"Gancho (hook): {b.get('hook') or '-'}",
        f"Resumo do roteiro: {b.get('scriptSummary') or '-'}",
        f"Chamada para acao (CTA): {b.get('cta') or '-'}",
        '',
    ]
    return '\n'.join(lines).encode('utf-8')


def _format_channel_txt(channel):
    lines = [
        f"Texto de publicacao por canal - {channel.get('profileId', '')}",
        f"Perfil: {channel.get('profileLabel') or channel.get('profileId', '')}",
    ]
    if channel.get('network'):
        lines.append(f"Rede: {channel['network']}")
    lines.extend([
        '',
        f"Titulo: {channel.get('title') or '-'}",
        'Texto do post:',
        channel.get('postText') or '-',
        '',
        f"CTA: {channel.get('cta') or '-'}",
        f"URL de destino: {channel.get('destinationUrl') or '-'}",
        f"Hashtags: {channel.get('hashtags') or '-'}",
        '',
    ])
    return '\n'.join(lines).encode('utf-8')


def _read_existing_index(pkg_dir_abs):
    fs = render_local.fs_path
    idx_path = os.path.join(pkg_dir_abs, PACKAGE_INDEX_NAME)
    if not os.path.isfile(fs(idx_path)):
        return None
    try:
        with open(fs(idx_path), 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _record_failed_attempt(pkg_dir_abs, work_id, error_msg):
    fs = render_local.fs_path
    os.makedirs(fs(pkg_dir_abs), exist_ok=True)
    prev = _read_existing_index(pkg_dir_abs) or {}
    payload = {
        'schemaVersion': 1,
        'workId': work_id,
        'lastAttempt': {
            'status': 'failed',
            'error': str(error_msg),
            'attemptedAt': studio_review.now_iso(),
        },
        'lastValidDelivery': prev.get('lastValidDelivery'),
    }
    studio_review.atomic_write_json(os.path.join(pkg_dir_abs, PACKAGE_INDEX_NAME), payload)


def _normalize_selection(body):
    pieces_in = body.get('pieces') or []
    channels_in = body.get('channels') or []
    if not isinstance(pieces_in, list) or not isinstance(channels_in, list):
        raise ValueError('selecao de pecas e canais deve ser uma lista')

    pieces = []
    seen_pieces = set()
    for item in pieces_in:
        if not isinstance(item, dict):
            raise ValueError('item de peca invalido na selecao')
        modality = str(item.get('modality') or '').strip()
        profile_id = str(item.get('profileId') or '').strip()
        if not modality or not profile_id:
            raise ValueError('cada peca selecionada exige modality e profileId')
        key = (modality, profile_id)
        if key in seen_pieces:
            continue
        seen_pieces.add(key)
        pieces.append({
            'modality': modality,
            'profileId': profile_id,
            'expectedVersionId': item.get('expectedVersionId'),
            'expectedDraftFingerprint': item.get('expectedDraftFingerprint'),
        })

    channels = []
    seen_channels = set()
    for item in channels_in:
        if isinstance(item, str):
            pid = item.strip()
            exp_sha = None
        elif isinstance(item, dict):
            pid = str(item.get('profileId') or '').strip()
            exp_sha = item.get('expectedCopySha256')
        else:
            raise ValueError('item de canal invalido na selecao')
        if not pid or pid in seen_channels:
            continue
        seen_channels.add(pid)
        channels.append({'profileId': pid, 'expectedCopySha256': exp_sha})

    if not pieces and not channels:
        raise ValueError('Selecione ao menos uma peca ou texto de canal aprovado para gerar o ZIP.')
    return pieces, channels


def build_and_promote_package(studio, work_id, body):
    """Monta pacote ZIP verificado dos itens aprovados e promove atomicamente."""
    if not isinstance(body, dict):
        raise ValueError('payload de empacotamento invalido')
    sel_pieces, sel_channels = _normalize_selection(body)
    overview = studio_review.build_review_overview(studio, work_id)
    work_doc = overview['work']
    wpaths = overview['paths']
    pkg_dir_rel = wpaths['packageDeliveryDir']
    pkg_dir_abs = studio.confine_workspace(pkg_dir_rel)
    fs = render_local.fs_path

    piece_map = {(p['modality'], p['profileId']): p for p in overview['pieces']}
    channel_map = {c['profileId']: c for c in overview['channels']}

    validated_pieces = []
    validated_channels = []

    try:
        for req in sel_pieces:
            key = (req['modality'], req['profileId'])
            piece = piece_map.get(key)
            if not piece:
                raise ValueError(f"peca nao encontrada: {req['modality']}/{req['profileId']}")
            if req.get('expectedVersionId') is not None and req['expectedVersionId'] != piece.get('deliveryVersionId'):
                raise studio_review.ReviewVersionConflictError(
                    f"Versao da peca {req['modality']}/{req['profileId']} mudou antes do empacotamento."
                )
            if (
                req.get('expectedDraftFingerprint') is not None
                and req['expectedDraftFingerprint'] != piece.get('currentDraftFingerprint')
            ):
                raise studio_review.ReviewVersionConflictError(
                    f"Rascunho da peca {req['modality']}/{req['profileId']} mudou antes do empacotamento."
                )
            if not piece.get('readyForPackage'):
                raise ValueError(
                    f"Peca {piece['modalityLabel']} ({piece['profileId']}) bloqueada: {piece['readyReason']}"
                )
            validated_pieces.append(piece)

        for req in sel_channels:
            pid = req['profileId']
            channel = channel_map.get(pid)
            if not channel:
                raise ValueError(f'canal nao encontrado no trabalho: {pid}')
            if req.get('expectedCopySha256') is not None and req['expectedCopySha256'] != channel.get('copySha256'):
                raise studio_review.ReviewVersionConflictError(
                    f'Texto do canal {pid} alterado antes do empacotamento; confira e aprove novamente.'
                )
            if not channel.get('readyForPackage'):
                raise ValueError(f"Canal {pid} bloqueado: {channel['readyReason']}")
            validated_channels.append(channel)
    except (ValueError, studio_review.ReviewVersionConflictError) as exc:
        if _read_existing_index(pkg_dir_abs):
            _record_failed_attempt(pkg_dir_abs, work_id, str(exc))
        raise

    os.makedirs(fs(pkg_dir_abs), exist_ok=True)
    work_dir_abs = studio.confine_workspace(wpaths['workDir'])
    staging_dir = tempfile.mkdtemp(prefix='.tmp-pkg-', dir=fs(work_dir_abs))
    payload_dir = os.path.join(staging_dir, 'payload')
    backup_dir = os.path.join(staging_dir, '.backup')
    os.makedirs(fs(payload_dir), exist_ok=True)

    lock = None
    try:
        zip_entries = []  # (archivePath, stagedFileAbs, expectedSha256, kind, sourceRel)

        def write_payload_bytes(arc_path, raw_bytes, kind):
            dst_abs = os.path.join(payload_dir, *arc_path.split('/'))
            os.makedirs(fs(os.path.dirname(dst_abs)), exist_ok=True)
            with open(fs(dst_abs), 'wb') as handle:
                handle.write(raw_bytes)
            sha = _sha256_bytes(raw_bytes)
            zip_entries.append((arc_path, dst_abs, sha, len(raw_bytes), kind, None))
            return sha, len(raw_bytes)

        def copy_verified_artifact(arc_path, source_rel, expected_sha, kind):
            src_abs = studio.confine(source_rel)
            if not os.path.isfile(fs(src_abs)):
                raise ValueError(f'arquivo ausente antes do empacotamento: {source_rel}')
            actual_src_sha = render_local.sha256_file(src_abs)
            if expected_sha and actual_src_sha != expected_sha:
                raise ValueError(f'SHA-256 divergente em {source_rel}')
            dst_abs = os.path.join(payload_dir, *arc_path.split('/'))
            os.makedirs(fs(os.path.dirname(dst_abs)), exist_ok=True)
            shutil.copyfile(fs(src_abs), fs(dst_abs))
            copied_sha = render_local.sha256_file(dst_abs)
            if copied_sha != actual_src_sha:
                raise OSError(f'falha de integridade ao copiar para staging: {source_rel}')
            size = os.path.getsize(fs(dst_abs))
            zip_entries.append((arc_path, dst_abs, copied_sha, size, kind, source_rel))
            return copied_sha, size

        created_at = studio_review.now_iso()
        pkg_hash_seed = studio_review.canonical_sha256({
            'workId': work_id,
            'pieces': [(p['pieceKey'], p['deliveryVersionId']) for p in validated_pieces],
            'channels': [(c['profileId'], c['copySha256']) for c in validated_channels],
            'briefingSha256': overview['editorial']['briefingSha256'],
        })[:10]
        package_id = f'{work_id}-pkg-{pkg_hash_seed}'

        # Ficha editorial
        editorial_json_bytes = (
            json.dumps({
                'schemaVersion': 1,
                'packageId': package_id,
                'workId': work_id,
                'workName': work_doc.get('name'),
                'project': work_doc.get('project'),
                'projectId': work_doc.get('projectId'),
                'updatedAt': overview['editorial'].get('updatedAt'),
                'briefingSha256': overview['editorial']['briefingSha256'],
                'briefing': overview['editorial']['briefing'],
            }, ensure_ascii=False, indent=2) + '\n'
        ).encode('utf-8')
        write_payload_bytes('briefing/ficha-editorial.json', editorial_json_bytes, 'editorial-json')
        write_payload_bytes('briefing/ficha-editorial.txt', _format_briefing_txt(work_doc, overview['editorial']), 'editorial-txt')

        manifest_channels = []
        for ch in validated_channels:
            pid = ch['profileId']
            folder = f'textos-por-canal/{pid}'
            ch_json = {
                'schemaVersion': 1,
                'profileId': pid,
                'profileLabel': ch.get('profileLabel'),
                'network': ch.get('network'),
                'copySha256': ch['copySha256'],
                'reviewedDecision': ch.get('currentDecision'),
                'copy': {
                    'title': ch['title'],
                    'postText': ch['postText'],
                    'cta': ch['cta'],
                    'destinationUrl': ch['destinationUrl'],
                    'hashtags': ch['hashtags'],
                },
            }
            jbytes = (json.dumps(ch_json, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            jsha, jsize = write_payload_bytes(f'{folder}/publicacao.json', jbytes, 'channel-copy-json')
            tsha, tsize = write_payload_bytes(f'{folder}/publicacao.txt', _format_channel_txt(ch), 'channel-copy-txt')
            manifest_channels.append({
                'profileId': pid,
                'profileLabel': ch.get('profileLabel'),
                'network': ch.get('network'),
                'copySha256': ch['copySha256'],
                'reviewedDecision': ch.get('currentDecision'),
                'files': [
                    {'archivePath': f'{folder}/publicacao.json', 'bytes': jsize, 'sha256': jsha},
                    {'archivePath': f'{folder}/publicacao.txt', 'bytes': tsize, 'sha256': tsha},
                ],
            })

        manifest_pieces = []
        modalities_present = []
        profiles_present = []

        for piece in validated_pieces:
            mod = piece['modality']
            pid = piece['profileId']
            if mod not in modalities_present:
                modalities_present.append(mod)
            if pid not in profiles_present:
                profiles_present.append(pid)
            folder = f'{mod}/{pid}'
            piece_files = []
            card_order = []

            if mod in ('video', 'motion'):
                arts = piece.get('artifacts') or {}
                arc_names = {
                    'video': 'primary-output.mp4',
                    'srt': 'subtitles.srt',
                    'narration': 'narration.txt',
                    'motionPlan': 'motion-plan.json',
                }
                for art_key in ('video', 'srt', 'narration', 'motionPlan'):
                    art = arts.get(art_key)
                    if not isinstance(art, dict) or not art.get('path'):
                        continue
                    arc_path = f'{folder}/{arc_names[art_key]}'
                    sha, size = copy_verified_artifact(
                        arc_path, art['path'], art.get('manifestSha256') or art.get('sha256'), art_key
                    )
                    piece_files.append({
                        'archivePath': arc_path,
                        'kind': art_key,
                        'sourcePath': art['path'],
                        'bytes': size,
                        'sha256': sha,
                    })
            else:
                for card in piece.get('cards') or []:
                    fname = card.get('file') or os.path.basename((card.get('path') or '').replace('\\', '/'))
                    arc_path = f'{folder}/{fname}'
                    sha, size = copy_verified_artifact(
                        arc_path, card['path'], card.get('manifestSha256') or card.get('sha256'), 'carousel-card'
                    )
                    card_order.append(fname)
                    piece_files.append({
                        'archivePath': arc_path,
                        'kind': 'carousel-card',
                        'order': card.get('order'),
                        'id': card.get('id'),
                        'file': fname,
                        'sourcePath': card['path'],
                        'bytes': size,
                        'sha256': sha,
                    })

            manifest_pieces.append({
                'modality': mod,
                'profileId': pid,
                'deliveryVersionId': piece['deliveryVersionId'],
                'draftFingerprint': piece['exportedDraftFingerprint'],
                'artifactsFingerprint': piece['artifactsFingerprint'],
                'reviewedDecision': piece.get('currentDecision'),
                'folderInZip': folder,
                'cardOrder': card_order,
                'mediaOrigins': piece.get('mediaOrigins') or [],
                'metrics': piece.get('metrics') or {},
                'files': piece_files,
            })

        for ch in manifest_channels:
            if ch['profileId'] not in profiles_present:
                profiles_present.append(ch['profileId'])

        manifest_doc = {
            'schemaVersion': 1,
            'packageId': package_id,
            'workId': work_id,
            'workName': work_doc.get('name'),
            'project': work_doc.get('project'),
            'projectId': work_doc.get('projectId'),
            'createdAt': created_at,
            'modalities': modalities_present,
            'profiles': profiles_present,
            'briefingSha256': overview['editorial']['briefingSha256'],
            'briefing': overview['editorial']['briefing'],
            'pieces': manifest_pieces,
            'channels': manifest_channels,
            'files': [
                {
                    'archivePath': arc_path,
                    'kind': kind,
                    'sourcePath': src_rel,
                    'bytes': size,
                    'sha256': sha,
                }
                for arc_path, _, sha, size, kind, src_rel in zip_entries
            ],
        }

        manifest_staging = os.path.join(staging_dir, PACKAGE_MANIFEST_NAME)
        studio_review.atomic_write_json(manifest_staging, manifest_doc)
        manifest_sha = render_local.sha256_file(manifest_staging)
        manifest_bytes = os.path.getsize(fs(manifest_staging))

        zip_staging = os.path.join(staging_dir, PACKAGE_ZIP_NAME)
        with zipfile.ZipFile(fs(zip_staging), 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for arc_path, src_abs, _, _, _, _ in zip_entries:
                zf.write(fs(src_abs), arcname=arc_path)
            zf.write(fs(manifest_staging), arcname=PACKAGE_MANIFEST_NAME)

        # Verifica o ZIP em staging antes de promover
        with zipfile.ZipFile(fs(zip_staging), 'r') as zf:
            bad = zf.testzip()
            if bad is not None:
                raise OSError(f'arquivo corrompido no ZIP de staging: {bad}')
            names = set(zf.namelist())
            for arc_path, _, expected_sha, _, _, _ in zip_entries:
                if arc_path not in names:
                    raise OSError(f'entrada ausente no ZIP gerado: {arc_path}')
                if _sha256_bytes(zf.read(arc_path)) != expected_sha:
                    raise OSError(f'SHA-256 divergente dentro do ZIP para {arc_path}')
            if PACKAGE_MANIFEST_NAME not in names:
                raise OSError('package-manifest.json ausente dentro do ZIP')

        zip_sha = render_local.sha256_file(zip_staging)
        zip_bytes = os.path.getsize(fs(zip_staging))
        zip_dest = os.path.join(pkg_dir_abs, PACKAGE_ZIP_NAME)
        manifest_dest = os.path.join(pkg_dir_abs, PACKAGE_MANIFEST_NAME)
        index_dest = os.path.join(pkg_dir_abs, PACKAGE_INDEX_NAME)

        valid_delivery = {
            'status': 'completed',
            'packageId': package_id,
            'createdAt': created_at,
            'modalities': modalities_present,
            'profiles': profiles_present,
            'pieceCount': len(manifest_pieces),
            'channelCount': len(manifest_channels),
            'zipPath': studio.rel(zip_dest),
            'zipSha256': zip_sha,
            'zipBytes': zip_bytes,
            'manifestPath': studio.rel(manifest_dest),
            'manifestSha256': manifest_sha,
            'manifestBytes': manifest_bytes,
        }
        index_doc = {
            'schemaVersion': 1,
            'workId': work_id,
            'lastAttempt': {
                'status': 'completed',
                'packageId': package_id,
                'attemptedAt': created_at,
                'finishedAt': created_at,
                'zipSha256': zip_sha,
                'zipBytes': zip_bytes,
            },
            'lastValidDelivery': valid_delivery,
        }
        index_staging = os.path.join(staging_dir, PACKAGE_INDEX_NAME)
        studio_review.atomic_write_json(index_staging, index_doc)

        lock = render_local.acquire_promotion_lock(pkg_dir_abs)
        staging_paths = {
            'zip': zip_staging,
            'manifest': manifest_staging,
            'index': index_staging,
        }
        dests = {
            'zip': zip_dest,
            'manifest': manifest_dest,
            'index': index_dest,
        }
        try:
            render_local.promote_with_backup(staging_paths, dests, backup_dir)
        except Exception as exc:
            # Se falhou na promocao e ja existia entrega valida restaurada, registra apenas lastAttempt.
            if _read_existing_index(pkg_dir_abs):
                try:
                    _record_failed_attempt(pkg_dir_abs, work_id, str(exc))
                except OSError:
                    pass
            raise

        return read_package_delivery(studio, work_id)
    finally:
        if lock and os.path.exists(fs(lock)):
            try:
                os.remove(fs(lock))
            except OSError:
                pass
        shutil.rmtree(fs(backup_dir, force=True), ignore_errors=True)
        shutil.rmtree(fs(staging_dir, force=True), ignore_errors=True)


def read_package_delivery(studio, work_id):
    """Le o estado do pacote ZIP promovido e verifica integridade no disco."""
    base_paths = studio.work_paths(work_id)
    work_abs = studio.confine_workspace(base_paths['workFile'])
    fs = render_local.fs_path
    if not os.path.isfile(fs(work_abs)):
        raise ValueError(f'trabalho nao encontrado: {work_id}')
    with open(fs(work_abs), 'r', encoding='utf-8') as handle:
        work_doc = json.load(handle)
    wpaths = studio_review.merged_work_paths(studio, work_id, work_doc)
    pkg_dir_rel = wpaths['packageDeliveryDir']
    pkg_dir_abs = studio.confine_workspace(pkg_dir_rel)

    index_doc = _read_existing_index(pkg_dir_abs)
    manifest_abs = os.path.join(pkg_dir_abs, PACKAGE_MANIFEST_NAME)
    manifest_doc = None
    if os.path.isfile(fs(manifest_abs)):
        try:
            with open(fs(manifest_abs), 'r', encoding='utf-8') as handle:
                manifest_doc = json.load(handle)
        except (OSError, ValueError):
            manifest_doc = None

    last_valid = (index_doc or {}).get('lastValidDelivery')
    zip_ok = False
    zip_error = None
    zip_sha = None
    zip_bytes = None
    if isinstance(last_valid, dict) and last_valid.get('zipPath'):
        try:
            zip_abs = studio.confine(last_valid['zipPath'])
            if not os.path.isfile(fs(zip_abs)):
                zip_error = 'arquivo ZIP promovido ausente no disco'
            else:
                zip_sha = render_local.sha256_file(zip_abs)
                zip_bytes = os.path.getsize(fs(zip_abs))
                expected_sha = last_valid.get('zipSha256')
                if expected_sha and zip_sha != expected_sha:
                    zip_error = 'SHA-256 do pacote ZIP diverge do indice promovido'
                else:
                    zip_ok = True
        except (ValueError, OSError) as exc:
            zip_error = str(exc)

    return {
        'dir': pkg_dir_rel,
        'index': index_doc,
        'manifest': manifest_doc,
        'lastAttempt': (index_doc or {}).get('lastAttempt'),
        'lastValidDelivery': last_valid,
        'available': zip_ok,
        'zipError': zip_error,
        'zipSha256': zip_sha,
        'zipBytes': zip_bytes,
        'downloadUrl': f'/api/works/package/download?id={work_id}' if zip_ok else None,
    }


def verified_package_zip_path(studio, work_id):
    """Resolve e valida integridade + confinamento do pacote ZIP antes do download."""
    info = read_package_delivery(studio, work_id)
    last_valid = info.get('lastValidDelivery')
    if not last_valid or not last_valid.get('zipPath'):
        raise ValueError('nenhum pacote ZIP de entrega gerado para este trabalho')
    if not info.get('available'):
        raise ValueError(info.get('zipError') or 'pacote ZIP indisponivel ou corrompido')
    target = studio.confine(last_valid['zipPath'])
    if not os.path.isfile(render_local.fs_path(target)):
        raise ValueError('pacote ZIP ausente no disco')
    return target, f"{work_id}-{last_valid.get('packageId', 'entrega')}.zip"
