"""Verificador compartilhado do pacote ZIP de entrega do Video Studio.

A verificação é somente leitura e usa exclusivamente o manifesto
`package-manifest.json` já escrito pelo empacotador
(`tools/delivery_package.py`). Não cria um segundo manifesto nem altera o
pacote.

CLI::

    python tools/delivery_verify.py ENTREGA.zip
    python tools/delivery_verify.py ENTREGA.zip --json
    python tools/delivery_verify.py ENTREGA.zip --expected-sha256 <sha256>

O código de saída é 0 quando o pacote é válido e diferente de zero quando há
qualquer falha de verificação.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import zipfile

PACKAGE_MANIFEST_NAME = 'package-manifest.json'
SUPPORTED_SCHEMA_VERSION = 1
READ_CHUNK = 1024 * 1024

APPROVED_DECISION = 'approved_for_local_delivery'


def _sha256_stream(fileobj):
    digest = hashlib.sha256()
    while True:
        chunk = fileobj.read(READ_CHUNK)
        if not chunk:
            break
        digest.update(chunk)
    return digest.hexdigest()


def _normalize_sha(value):
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def _decision_value(value):
    if isinstance(value, dict):
        return value.get('decision')
    return value


def _empty_result():
    return {
        'ok': False,
        'packageId': None,
        'workId': None,
        'workName': None,
        'project': None,
        'createdAt': None,
        'modalities': [],
        'profiles': [],
        'pieces': [],
        'channels': [],
        'files': [],
        'checks': [],
        'errors': [],
        'limitations': [],
        'zipSha256': {'actual': None, 'expected': None, 'compared': False, 'match': None},
        'summary': '',
    }


def _add_check(result, name, ok, detail=''):
    result['checks'].append({'name': name, 'ok': bool(ok), 'detail': detail})


def _add_error(result, message, field=None, file=None):
    error = {'message': message}
    if field:
        error['field'] = field
    if file:
        error['file'] = file
    result['errors'].append(error)


def _populate_metadata(result, manifest):
    schema = manifest.get('schemaVersion')
    if schema != SUPPORTED_SCHEMA_VERSION:
        result['limitations'].append(
            f'schemaVersion {schema!r} não suportado (esperado {SUPPORTED_SCHEMA_VERSION}); '
            'lacunas são reportadas como limitação.'
        )
    result['packageId'] = manifest.get('packageId')
    result['workId'] = manifest.get('workId')
    result['workName'] = manifest.get('workName')
    result['project'] = manifest.get('project')
    result['createdAt'] = manifest.get('createdAt')
    result['modalities'] = [str(x) for x in (manifest.get('modalities') or [])]
    result['profiles'] = [str(x) for x in (manifest.get('profiles') or [])]

    pieces = []
    for piece in manifest.get('pieces') or []:
        if not isinstance(piece, dict):
            continue
        pieces.append({
            'modality': piece.get('modality'),
            'profileId': piece.get('profileId'),
            'deliveryVersionId': piece.get('deliveryVersionId'),
            'draftFingerprint': piece.get('draftFingerprint'),
            'reviewedDecision': _decision_value(piece.get('reviewedDecision')),
            'folderInZip': piece.get('folderInZip'),
            'fileCount': len(piece.get('files') or []),
        })
    result['pieces'] = pieces

    channels = []
    for channel in manifest.get('channels') or []:
        if not isinstance(channel, dict):
            continue
        channels.append({
            'profileId': channel.get('profileId'),
            'profileLabel': channel.get('profileLabel'),
            'network': channel.get('network'),
            'copySha256': channel.get('copySha256'),
            'reviewedDecision': _decision_value(channel.get('reviewedDecision')),
            'fileCount': len(channel.get('files') or []),
        })
    result['channels'] = channels

    _add_check(result, 'schemaVersion', schema == SUPPORTED_SCHEMA_VERSION, repr(schema))
    _add_check(
        result,
        'identificação do pacote',
        bool(result['packageId'] and result['workId']),
        f"packageId={result['packageId']!r}, workId={result['workId']!r}",
    )
    if not result['packageId'] or not result['workId']:
        _add_error(result, 'manifesto sem packageId/workId', field='packageId')


def _verify_manifest_files(result, zf, names, manifest):
    files = manifest.get('files')
    if not isinstance(files, list) or not files:
        _add_error(result, 'manifesto sem lista files', field='files')
        _add_check(result, 'arquivos do manifesto', False, 'lista files ausente')
        return

    ok_count = 0
    hashed_count = 0
    for item in files:
        if not isinstance(item, dict):
            _add_error(result, 'item inválido em files', field='files')
            continue
        arc = item.get('archivePath')
        declared_sha = _normalize_sha(item.get('sha256'))
        declared_bytes = item.get('bytes')
        entry = {
            'archivePath': arc,
            'kind': item.get('kind'),
            'sourcePath': item.get('sourcePath'),
            'bytes': None,
            'sha256': None,
            'ok': False,
            'error': None,
        }
        if not arc or arc not in names:
            entry['error'] = 'arquivo declarado ausente no ZIP'
            result['files'].append(entry)
            _add_error(result, 'arquivo declarado ausente no ZIP', field='files', file=arc)
            continue
        try:
            with zf.open(arc, 'r') as handle:
                actual_sha = _sha256_stream(handle)
            actual_bytes = zf.getinfo(arc).file_size
        except (KeyError, OSError, RuntimeError) as exc:
            entry['error'] = str(exc)
            result['files'].append(entry)
            _add_error(result, f'falha ao ler {arc}: {exc}', field='files', file=arc)
            continue

        entry['bytes'] = actual_bytes
        entry['sha256'] = actual_sha
        if declared_sha is None:
            entry['error'] = 'manifesto sem sha256; hash não comparado'
            result['limitations'].append(
                f'{arc}: manifesto sem sha256; integridade por hash não verificada.'
            )
        else:
            hashed_count += 1
            if actual_sha != declared_sha:
                entry['error'] = 'sha256 divergente'
                _add_error(result, 'SHA-256 divergente', field='files.sha256', file=arc)
                result['files'].append(entry)
                continue
            if declared_bytes is not None and declared_bytes != actual_bytes:
                entry['error'] = 'tamanho divergente'
                _add_error(result, 'tamanho divergente', field='files.bytes', file=arc)
                result['files'].append(entry)
                continue
        entry['ok'] = True
        ok_count += 1
        result['files'].append(entry)

    _add_check(
        result,
        'arquivos do manifesto',
        ok_count == len(files),
        f'{ok_count}/{len(files)} arquivos íntegros ({hashed_count} com sha256 no manifesto)',
    )


def _verify_nested_files(result, zf, names, manifest):
    """Confere as listas de arquivos por peça/canal contra o ZIP e o manifesto."""
    ok_count = 0
    total = 0
    for piece in manifest.get('pieces') or []:
        if not isinstance(piece, dict):
            continue
        label = f"{piece.get('modality')}/{piece.get('profileId')}"
        for item in piece.get('files') or []:
            if not isinstance(item, dict):
                continue
            total += 1
            arc = item.get('archivePath')
            declared_sha = _normalize_sha(item.get('sha256'))
            declared_bytes = item.get('bytes')
            if not arc or arc not in names:
                _add_error(result, 'arquivo declarado ausente no ZIP', field='pieces.files', file=arc)
                continue
            try:
                with zf.open(arc, 'r') as handle:
                    actual_sha = _sha256_stream(handle)
                actual_bytes = zf.getinfo(arc).file_size
            except (KeyError, OSError, RuntimeError) as exc:
                _add_error(result, f'falha ao ler {arc}: {exc}', field='pieces.files', file=arc)
                continue
            if declared_sha and actual_sha != declared_sha:
                _add_error(result, f'SHA-256 divergente na peça {label}', field='pieces.files.sha256', file=arc)
                continue
            if declared_bytes is not None and declared_bytes != actual_bytes:
                _add_error(result, f'tamanho divergente na peça {label}', field='pieces.files.bytes', file=arc)
                continue
            ok_count += 1
    for channel in manifest.get('channels') or []:
        if not isinstance(channel, dict):
            continue
        label = f"canal {channel.get('profileId')}"
        for item in channel.get('files') or []:
            if not isinstance(item, dict):
                continue
            total += 1
            arc = item.get('archivePath')
            declared_sha = _normalize_sha(item.get('sha256'))
            if not arc or arc not in names:
                _add_error(result, 'arquivo declarado ausente no ZIP', field='channels.files', file=arc)
                continue
            try:
                with zf.open(arc, 'r') as handle:
                    actual_sha = _sha256_stream(handle)
            except (KeyError, OSError, RuntimeError) as exc:
                _add_error(result, f'falha ao ler {arc}: {exc}', field='channels.files', file=arc)
                continue
            if declared_sha and actual_sha != declared_sha:
                _add_error(result, f'SHA-256 divergente em {label}', field='channels.files.sha256', file=arc)
                continue
            ok_count += 1
    if total:
        _add_check(result, 'arquivos por peça/canal', ok_count == total, f'{ok_count}/{total} arquivos íntegros')


def _verify_approved_versions(result, manifest):
    pieces = manifest.get('pieces') or []
    if not pieces:
        result['limitations'].append('manifesto sem peças; aprovação por versão não verificável.')
        return
    missing_decision = 0
    missing_version = 0
    approved = 0
    for piece in pieces:
        if not isinstance(piece, dict):
            continue
        decision = _decision_value(piece.get('reviewedDecision'))
        version = piece.get('deliveryVersionId')
        if not version:
            missing_version += 1
            result['limitations'].append(
                f"peça {piece.get('modality')}/{piece.get('profileId')}: manifesto sem deliveryVersionId; "
                'versão aprovada não verificável.'
            )
        if not decision:
            missing_decision += 1
            result['limitations'].append(
                f"peça {piece.get('modality')}/{piece.get('profileId')}: manifesto sem reviewedDecision; "
                'decisão editorial não verificável.'
            )
        elif decision == APPROVED_DECISION:
            approved += 1
        else:
            _add_error(
                result,
                f'peça {piece.get("modality")}/{piece.get("profileId")} não está aprovada para entrega local',
                field='pieces.reviewedDecision',
            )
    _add_check(
        result,
        'versões aprovadas',
        approved == len(pieces),
        f'{approved}/{len(pieces)} peças com reviewedDecision={APPROVED_DECISION}',
    )
    if missing_decision or missing_version:
        result['limitations'].append(
            'Pacote antigo ou incompleto: campos de versão/decisão ausentes limitam a verificação.'
        )


def _build_summary(result):
    if result['ok']:
        return (
            f"Pacote {result['packageId']} íntegro: "
            f"{len(result['pieces'])} peça(s), {len(result['channels'])} canal(is), "
            f"{len(result['files'])} arquivo(s) conferido(s)."
        )
    first = result['errors'][0] if result['errors'] else {'message': 'falha desconhecida'}
    location = f" em {first['file']}" if first.get('file') else ''
    return f"Pacote {result['packageId'] or '?'} inválido: {first['message']}{location}."


def verify_package_zip(zip_path, expected_zip_sha256=None):
    """Verifica um ZIP de entrega contra o seu próprio manifesto.

    Retorna um dicionário estruturado com `ok`, `summary`, `packageId`,
    `pieces`, `channels`, `files`, `checks`, `errors`, `limitations` e
    `zipSha256`. Não altera o ZIP.
    """
    result = _empty_result()
    expected = _normalize_sha(expected_zip_sha256)
    result['zipSha256']['expected'] = expected

    if not zip_path or not os.path.isfile(zip_path):
        _add_error(result, f'arquivo ZIP não encontrado: {zip_path}', field='zip')
        result['summary'] = 'Arquivo ZIP não encontrado.'
        return result

    try:
        with open(zip_path, 'rb') as handle:
            actual_zip_sha = _sha256_stream(handle)
    except OSError as exc:
        _add_error(result, f'falha ao ler o ZIP: {exc}', field='zip')
        result['summary'] = 'Falha ao ler o ZIP.'
        return result

    result['zipSha256']['actual'] = actual_zip_sha
    if expected:
        result['zipSha256']['compared'] = True
        result['zipSha256']['match'] = actual_zip_sha == expected
        _add_check(
            result,
            'sha256 do ZIP',
            actual_zip_sha == expected,
            f'calculado {actual_zip_sha}; esperado {expected}',
        )
        if actual_zip_sha != expected:
            _add_error(result, 'SHA-256 do ZIP diverge do valor esperado', field='zipSha256')
    else:
        result['limitations'].append(
            'SHA-256 externo do ZIP não informado; comparação opcional não realizada.'
        )

    try:
        archive = zipfile.ZipFile(zip_path, 'r')
    except (zipfile.BadZipFile, OSError) as exc:
        _add_error(result, f'ZIP inválido ou ilegível: {exc}', field='zip')
        result['summary'] = 'ZIP inválido ou ilegível.'
        return result

    with archive:
        names = set(archive.namelist())
        _add_check(result, 'abertura do ZIP', True, f'{len(names)} entradas')

        bad = archive.testzip()
        if bad is not None:
            _add_check(result, 'CRC do ZIP', False, f'falha em {bad}')
            _add_error(result, f'CRC inválido em {bad}', field='zip', file=bad)
        else:
            _add_check(result, 'CRC do ZIP', True, 'todas as entradas legíveis')

        if PACKAGE_MANIFEST_NAME not in names:
            _add_error(result, f'{PACKAGE_MANIFEST_NAME} ausente no ZIP', field=PACKAGE_MANIFEST_NAME)
            result['summary'] = 'Manifesto ausente no ZIP.'
            return result

        try:
            manifest = json.loads(archive.read(PACKAGE_MANIFEST_NAME).decode('utf-8'))
        except (ValueError, UnicodeDecodeError) as exc:
            _add_error(result, f'{PACKAGE_MANIFEST_NAME} inválido: {exc}', field=PACKAGE_MANIFEST_NAME)
            result['summary'] = 'Manifesto inválido.'
            return result

        if not isinstance(manifest, dict):
            _add_error(result, 'manifesto deve ser um objeto JSON', field=PACKAGE_MANIFEST_NAME)
            result['summary'] = 'Manifesto inválido.'
            return result

        _populate_metadata(result, manifest)
        _verify_manifest_files(result, archive, names, manifest)
        _verify_nested_files(result, archive, names, manifest)
        _verify_approved_versions(result, manifest)

    result['ok'] = not result['errors']
    result['summary'] = _build_summary(result)
    return result


def format_text(result):
    lines = []
    lines.append('Verificação do pacote ZIP de entrega')
    lines.append('=====================================')
    lines.append(f"Pacote: {result.get('packageId') or '-'}")
    lines.append(f"Trabalho: {result.get('workName') or '-'} ({result.get('workId') or '-'})")
    if result.get('project'):
        lines.append(f"Projeto: {result['project']}")
    if result.get('createdAt'):
        lines.append(f"Criado: {result['createdAt']}")
    lines.append(f"Modalidades: {', '.join(result.get('modalities') or []) or '-'}")
    lines.append(f"Destinos: {', '.join(result.get('profiles') or []) or '-'}")

    if result.get('pieces'):
        lines.append('')
        lines.append('Peças:')
        for piece in result['pieces']:
            lines.append(
                f"  - {piece.get('modality')}/{piece.get('profileId')} · "
                f"versão {piece.get('deliveryVersionId') or '-'} · "
                f"revisão {piece.get('reviewedDecision') or '-'} · "
                f"{piece.get('fileCount', 0)} arquivo(s)"
            )
    if result.get('channels'):
        lines.append('')
        lines.append('Canais:')
        for channel in result['channels']:
            lines.append(
                f"  - {channel.get('profileId')} · "
                f"revisão {channel.get('reviewedDecision') or '-'} · "
                f"{channel.get('fileCount', 0)} arquivo(s)"
            )

    if result.get('files'):
        lines.append('')
        lines.append('Arquivos:')
        for item in result['files']:
            status = 'OK' if item.get('ok') else 'FALHA'
            detail = item.get('error') or f"{item.get('bytes')} bytes · sha256 {item.get('sha256')}"
            lines.append(f"  [{status}] {item.get('archivePath') or '-'} · {detail}")

    lines.append('')
    lines.append('Checks:')
    for check in result.get('checks') or []:
        mark = 'ok' if check.get('ok') else 'falha'
        lines.append(f"  [{mark}] {check.get('name')}: {check.get('detail')}")

    zip_sha = result.get('zipSha256') or {}
    lines.append('')
    if zip_sha.get('compared'):
        match = 'confere' if zip_sha.get('match') else 'DIVERGE'
        lines.append(
            f"SHA-256 do ZIP: {zip_sha.get('actual')} (esperado {zip_sha.get('expected')}) → {match}"
        )
    else:
        lines.append(f"SHA-256 do ZIP: {zip_sha.get('actual') or '-'} (sem valor externo para comparar)")

    if result.get('errors'):
        lines.append('')
        lines.append('Problemas:')
        for error in result['errors']:
            location = f" [{error['file']}]" if error.get('file') else ''
            field = f" ({error['field']})" if error.get('field') else ''
            lines.append(f"  - {error.get('message')}{field}{location}")

    if result.get('limitations'):
        lines.append('')
        lines.append('Limitações:')
        for limitation in result['limitations']:
            lines.append(f"  - {limitation}")

    lines.append('')
    lines.append(f"Resultado: {'VÁLIDO' if result.get('ok') else 'INVÁLIDO'}")
    lines.append(result.get('summary') or '')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Verifica um pacote ZIP de entrega do Video Studio contra o seu manifesto.',
    )
    parser.add_argument('zip_path', help='caminho do ZIP de entrega')
    parser.add_argument('--json', action='store_true', help='imprime o resultado estruturado em JSON')
    parser.add_argument(
        '--expected-sha256',
        default=None,
        help='SHA-256 esperado do ZIP inteiro (valor mostrado pelo Studio)',
    )
    args = parser.parse_args(argv)

    result = verify_package_zip(args.zip_path, expected_zip_sha256=args.expected_sha256)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_text(result))
    return 0 if result.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main())