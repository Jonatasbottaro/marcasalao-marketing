"""CLI de backup e restauracao de um trabalho salvo do Video Studio.

Subcomandos:
  backup  <work-id> <saida.zip>  — empacota o trabalho num ZIP portátil
  inspect <arquivo.zip>          — lista conteúdo e verifica dependências
  restore <arquivo.zip>          — restaura o trabalho num workspace de destino

Uso:
  python -m studio_work_backup backup meu-trabalho backup.zip
  python -m studio_work_backup inspect backup.zip
  python -m studio_work_backup restore backup.zip --workspace /outro/checkout

Regras de escopo (v1):
  Inclui: work.json, editorial.json, review-state.json, planning.json,
          media-library.json, drafts/ (video, carousel, motion), media/ do trabalho.
  Exclui: credenciais, caches, fila, aprovações, entregas renderizadas, SQLite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 1
MANIFEST_ARCHIVE_PATH = "MANIFEST.json"
KEBAB_CASE_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

# Chaves de work_paths() que fazem parte do backup (apenas arquivos individuais)
_FILE_PATH_KEYS = (
    'workFile',
    'editorialFile',
    'reviewStateFile',
    'planningFile',
    'mediaLibraryFile',
    'videoDraft',
    'carouselDraft',
    'motionPlan',
)


# ---------------------------------------------------------------------------
# Utilitários de hashing
# ---------------------------------------------------------------------------

def sha256_file(path: str) -> str:
    """Retorna o SHA-256 hex de um arquivo em disco."""
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Resolução de raiz e caminhos
# ---------------------------------------------------------------------------

def _find_root(start: str | None = None) -> str:
    """Localiza a raiz do repositório via git rev-parse."""
    import subprocess
    cwd = start or os.getcwd()
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        capture_output=True, text=True, cwd=cwd,
    )
    if result.returncode != 0:
        raise RuntimeError('Nao foi possivel encontrar a raiz do repositório Git.')
    return result.stdout.strip().replace('/', os.sep)


def _contained(root: str, path: str) -> bool:
    root_real = os.path.realpath(root)
    path_real = os.path.realpath(path)
    return path_real == root_real or path_real.startswith(root_real + os.sep)


def _confine(root: str, rel_or_abs: str) -> str:
    """Resolve e confirma que o caminho está dentro de root."""
    candidate = rel_or_abs if os.path.isabs(rel_or_abs) else os.path.join(root, rel_or_abs)
    real = os.path.realpath(candidate)
    if not _contained(root, real):
        raise ValueError(f'Caminho fora da raiz do projeto: {rel_or_abs!r}')
    return real


def _work_paths(work_id: str) -> dict[str, str]:
    """Retorna o mapa de caminhos relativos de um trabalho (espelho de Studio.work_paths)."""
    if not isinstance(work_id, str) or not KEBAB_CASE_RE.match(work_id):
        raise ValueError('id do trabalho deve usar kebab-case (letras minúsculas, números e hifens)')
    base = f'.workspace/studio/works/{work_id}'
    return {
        'workDir': base,
        'workFile': f'{base}/work.json',
        'mediaDir': f'{base}/media',
        'videoDraft': f'{base}/drafts/video.request.json',
        'carouselDraft': f'{base}/drafts/carousel.request.json',
        'motionPlan': f'{base}/drafts/motion.plan.json',
        'editorialFile': f'{base}/editorial.json',
        'reviewStateFile': f'{base}/review-state.json',
        'planningFile': f'{base}/planning.json',
        'mediaLibraryFile': f'{base}/media-library.json',
        'videoRequestsFile': f'{base}/video-requests.json',
        'videoDeliveryDir': f'{base}/deliveries/video',
        'carouselDeliveryDir': f'{base}/deliveries/carousel',
        'motionDeliveryDir': f'{base}/deliveries/motion',
        'packageDeliveryDir': f'{base}/deliveries/package',
    }


# ---------------------------------------------------------------------------
# Coleta de arquivos de um trabalho
# ---------------------------------------------------------------------------

def _collect_work_files(root: str, work_id: str) -> list[tuple[str, str]]:
    """Retorna lista de (rel_path, abs_path) dos arquivos do trabalho que existem.

    Inclui: arquivos individuais definidos em _FILE_PATH_KEYS + toda a pasta media/
    Exclui: deliveries/, video-requests.json e production-queue.sqlite
    """
    paths = _work_paths(work_id)
    collected: list[tuple[str, str]] = []
    seen: set[str] = set()

    def _add(rel: str) -> None:
        rel_norm = rel.replace('\\', '/')
        if rel_norm in seen:
            return
        abs_path = _confine(root, rel)
        if os.path.isfile(abs_path):
            seen.add(rel_norm)
            collected.append((rel_norm, abs_path))

    # Arquivos individuais definidos
    for key in _FILE_PATH_KEYS:
        _add(paths[key])

    # Pasta media/ — adiciona todos os arquivos recursivamente
    media_rel = paths['mediaDir']
    media_abs = _confine(root, media_rel)
    if os.path.isdir(media_abs):
        for dirpath, _dirs, files in os.walk(media_abs):
            for fname in sorted(files):
                abs_f = os.path.join(dirpath, fname)
                rel_f = os.path.relpath(abs_f, root).replace(os.sep, '/')
                _add(rel_f)

    return sorted(collected, key=lambda x: x[0])


def _read_project_rel(root: str, work_id: str) -> str | None:
    """Lê o campo 'project' de work.json e retorna o caminho relativo."""
    paths = _work_paths(work_id)
    work_abs = _confine(root, paths['workFile'])
    if not os.path.isfile(work_abs):
        return None
    try:
        with open(work_abs, 'r', encoding='utf-8') as fh:
            work = json.load(fh)
        project_rel = (work.get('project') or '').strip()
        return project_rel or None
    except (json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# Manifesto
# ---------------------------------------------------------------------------

def _build_manifest(root: str, work_id: str, files: list[tuple[str, str]]) -> dict[str, Any]:
    """Constrói o manifesto JSON v1."""
    project_rel = _read_project_rel(root, work_id)
    dependency: dict[str, Any] = {}
    if project_rel:
        project_abs = _confine(root, project_rel)
        if os.path.isfile(project_abs):
            dependency = {
                'rel': project_rel,
                'sha256': sha256_file(project_abs),
            }

    file_entries = []
    for rel, abs_path in files:
        size = os.path.getsize(abs_path)
        digest = sha256_file(abs_path)
        file_entries.append({'rel': rel, 'size': size, 'sha256': digest})

    return {
        'schemaVersion': SCHEMA_VERSION,
        'workId': work_id,
        'exportedAt': datetime.now(timezone.utc).isoformat(),
        'files': file_entries,
        'dependencies': {
            'projectManifest': dependency,
        },
    }


# ---------------------------------------------------------------------------
# Subcomando: backup
# ---------------------------------------------------------------------------

def cmd_backup(args: argparse.Namespace) -> int:
    work_id: str = args.work_id
    output_path: str = os.path.abspath(args.output)
    root = _find_root()

    if not KEBAB_CASE_RE.match(work_id):
        print(f'ERRO: id "{work_id}" invalido; use kebab-case.', file=sys.stderr)
        return 1

    # Verificar que o trabalho existe
    paths = _work_paths(work_id)
    work_abs = _confine(root, paths['workFile'])
    if not os.path.isfile(work_abs):
        print(f'ERRO: Trabalho "{work_id}" nao encontrado em {paths["workFile"]!r}', file=sys.stderr)
        return 1

    # Verificar destino dentro da raiz
    if not _contained(root, output_path):
        print(f'ERRO: Destino fora da raiz do projeto: {output_path!r}', file=sys.stderr)
        return 1

    print(f'Coletando arquivos do trabalho "{work_id}"...')
    files = _collect_work_files(root, work_id)
    if not files:
        print('ERRO: Nenhum arquivo encontrado para o trabalho.', file=sys.stderr)
        return 1

    manifest = _build_manifest(root, work_id, files)
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8')

    # Escrever em arquivo temporário staging, depois mover atomicamente
    out_dir = os.path.dirname(output_path) or '.'
    fd, staging_path = tempfile.mkstemp(prefix='studio-backup-staging-', suffix='.zip', dir=out_dir)
    os.close(fd)
    try:
        with zipfile.ZipFile(staging_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(MANIFEST_ARCHIVE_PATH, manifest_bytes)
            for rel, abs_path in files:
                zf.write(abs_path, rel)
                print(f'  + {rel}')

        # Verificação de integridade do arquivo staging gerado
        _verify_zip_integrity(staging_path, manifest)

        # Promoção atômica
        if os.path.exists(output_path):
            os.remove(output_path)
        shutil.move(staging_path, output_path)
        staging_path = None  # não deletar no finally

    finally:
        if staging_path and os.path.exists(staging_path):
            os.remove(staging_path)

    print(f'\nBackup gerado: {output_path}')
    print(f'  Arquivos: {len(files)}')
    print(f'  Trabalho: {work_id}')
    print(f'  Exportado em: {manifest["exportedAt"]}')
    dep = manifest['dependencies'].get('projectManifest') or {}
    if dep.get('rel'):
        print(f'  ProjectManifest: {dep["rel"]}')
    return 0


def _verify_zip_integrity(zip_path: str, manifest: dict) -> None:
    """Verifica que todos os arquivos no ZIP correspondem ao manifesto."""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        names = set(zf.namelist())
        for entry in manifest['files']:
            rel = entry['rel']
            if rel not in names:
                raise RuntimeError(f'Arquivo ausente no ZIP: {rel!r}')
            data = zf.read(rel)
            actual = sha256_bytes(data)
            if actual != entry['sha256']:
                raise RuntimeError(f'SHA-256 divergente no ZIP para {rel!r}')


# ---------------------------------------------------------------------------
# Subcomando: inspect
# ---------------------------------------------------------------------------

def cmd_inspect(args: argparse.Namespace) -> int:
    zip_path = os.path.abspath(args.archive)
    if not os.path.isfile(zip_path):
        print(f'ERRO: Arquivo nao encontrado: {zip_path!r}', file=sys.stderr)
        return 1

    root = _find_root()

    manifest = _load_manifest_from_zip(zip_path)
    work_id = manifest.get('workId', '?')
    exported_at = manifest.get('exportedAt', '?')
    files = manifest.get('files', [])

    print(f'=== Inspecao do backup ===')
    print(f'Trabalho : {work_id}')
    print(f'Exportado: {exported_at}')
    print(f'Schema   : v{manifest.get("schemaVersion", "?")}')
    print(f'Arquivos : {len(files)}')
    print()

    # Verificar integridade do ZIP
    errors = 0
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zip_names = set(zf.namelist())
        for entry in files:
            rel = entry['rel']
            exp_sha = entry['sha256']
            exp_size = entry['size']
            if rel not in zip_names:
                print(f'  AUSENTE NO ZIP : {rel}')
                errors += 1
                continue
            data = zf.read(rel)
            actual_sha = sha256_bytes(data)
            actual_size = len(data)
            if actual_sha != exp_sha:
                print(f'  HASH_DIVERGENTE: {rel}  (esperado {exp_sha[:12]}… obtido {actual_sha[:12]}…)')
                errors += 1
            elif actual_size != exp_size:
                print(f'  TAMANHO_ERRADO : {rel}  ({actual_size} != {exp_size})')
                errors += 1
            else:
                print(f'  OK             : {rel}')

    # Verificar dependências no destino
    print()
    print('--- Dependências ---')
    dep = (manifest.get('dependencies') or {}).get('projectManifest') or {}
    if not dep.get('rel'):
        print('  Nenhuma dependência de ProjectManifest registrada.')
    else:
        dep_rel = dep['rel']
        dep_sha = dep.get('sha256', '')
        dep_abs = os.path.join(root, dep_rel.replace('/', os.sep))
        if not os.path.isfile(dep_abs):
            print(f'  AUSENTE       : {dep_rel}')
            errors += 1
        else:
            actual_dep_sha = sha256_file(dep_abs)
            if actual_dep_sha != dep_sha:
                print(f'  HASH_DIVERGENTE: {dep_rel}  (esperado {dep_sha[:12]}… obtido {actual_dep_sha[:12]}…)')
                errors += 1
            else:
                print(f'  OK            : {dep_rel}')

    print()
    if errors == 0:
        print('Resultado: OK — backup integro e dependências satisfeitas.')
        return 0
    else:
        print(f'Resultado: ERRO — {errors} problema(s) encontrado(s).')
        return 1


# ---------------------------------------------------------------------------
# Subcomando: restore
# ---------------------------------------------------------------------------

def cmd_restore(args: argparse.Namespace) -> int:
    zip_path = os.path.abspath(args.archive)
    if not os.path.isfile(zip_path):
        print(f'ERRO: Arquivo nao encontrado: {zip_path!r}', file=sys.stderr)
        return 1

    root = _find_root()

    # Destino do workspace pode ser sobrescrito via --workspace
    dest_root = os.path.realpath(args.workspace) if args.workspace else root
    if not _contained(root, dest_root):
        print(f'ERRO: Destino fora da raiz do projeto: {dest_root!r}', file=sys.stderr)
        return 1

    manifest = _load_manifest_from_zip(zip_path)
    work_id = manifest.get('workId', '')
    if not work_id or not KEBAB_CASE_RE.match(work_id):
        print(f'ERRO: Manifesto com workId invalido: {work_id!r}', file=sys.stderr)
        return 1

    # Verificar que o trabalho NÃO existe no destino
    dest_work_dir = os.path.join(dest_root, '.workspace', 'studio', 'works', work_id)
    dest_work_file = os.path.join(dest_work_dir, 'work.json')
    if os.path.exists(dest_work_file):
        print(
            f'ERRO: O trabalho "{work_id}" ja existe em {dest_work_file!r}.\n'
            f'      A restauracao so e permitida em destinos onde o trabalho nao existe.',
            file=sys.stderr,
        )
        return 1

    # Verificar integridade do ZIP antes de extrair
    print('Verificando integridade do arquivo...')
    files_in_manifest = manifest.get('files', [])
    errors_found = _check_zip_entries(zip_path, files_in_manifest)
    if errors_found:
        print(f'ERRO: {errors_found} arquivo(s) com problema(s) de integridade. Restauracao cancelada.', file=sys.stderr)
        return 1
    print(f'  {len(files_in_manifest)} arquivo(s) verificados — OK')

    # Staging: extrair em diretório temporário dentro de <RAIZ>/.workspace/tmp/
    tmp_base = os.path.join(root, '.workspace', 'tmp', 'studio-work-backup')
    os.makedirs(tmp_base, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    staging_dir = os.path.join(tmp_base, f'restore-{timestamp}')
    os.makedirs(staging_dir, exist_ok=True)

    try:
        print(f'Extraindo para staging: {staging_dir}')
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for entry in files_in_manifest:
                rel = entry['rel']
                dest_file = os.path.join(staging_dir, rel.replace('/', os.sep))
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                data = zf.read(rel)
                # Verificação dupla após leitura
                if sha256_bytes(data) != entry['sha256']:
                    raise RuntimeError(f'Falha de integridade ao extrair: {rel!r}')
                with open(dest_file, 'wb') as fh:
                    fh.write(data)

        # Verificar staging antes de promover
        print('Validando staging...')
        errors_staging = _check_staging_entries(staging_dir, files_in_manifest)
        if errors_staging:
            raise RuntimeError(f'{errors_staging} arquivo(s) com problema no staging')

        # Promover staging → destino final (atômico dentro do mesmo filesystem)
        print(f'Promovendo para: {dest_work_dir}')
        _promote_staging(staging_dir, dest_work_dir, work_id, files_in_manifest, dest_root)

    except Exception as exc:
        print(f'ERRO durante a restauracao: {exc}', file=sys.stderr)
        # Garantir que staging seja limpo
        shutil.rmtree(staging_dir, ignore_errors=True)
        return 1
    else:
        # Remover staging após promoção bem-sucedida
        shutil.rmtree(staging_dir, ignore_errors=True)

    print(f'\nRestauracao concluida!')
    print(f'  Trabalho: {work_id}')
    print(f'  Local   : {dest_work_dir}')
    print(f'  Arquivos: {len(files_in_manifest)}')
    return 0


def _check_zip_entries(zip_path: str, entries: list[dict]) -> int:
    """Retorna a quantidade de erros de integridade no ZIP."""
    errors = 0
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zip_names = set(zf.namelist())
        for entry in entries:
            rel = entry['rel']
            if rel not in zip_names:
                print(f'  AUSENTE: {rel}', file=sys.stderr)
                errors += 1
                continue
            data = zf.read(rel)
            if sha256_bytes(data) != entry['sha256']:
                print(f'  HASH_DIVERGENTE: {rel}', file=sys.stderr)
                errors += 1
    return errors


def _check_staging_entries(staging_dir: str, entries: list[dict]) -> int:
    """Verifica hashes dos arquivos extraídos no staging."""
    errors = 0
    for entry in entries:
        rel = entry['rel']
        staged_abs = os.path.join(staging_dir, rel.replace('/', os.sep))
        if not os.path.isfile(staged_abs):
            print(f'  STAGING AUSENTE: {rel}', file=sys.stderr)
            errors += 1
            continue
        if sha256_file(staged_abs) != entry['sha256']:
            print(f'  STAGING HASH_DIVERGENTE: {rel}', file=sys.stderr)
            errors += 1
    return errors


def _promote_staging(staging_dir: str, dest_work_dir: str, work_id: str,
                     entries: list[dict], dest_root: str) -> None:
    """Move os arquivos do staging para o destino final.

    Estratégia: copiar arquivo a arquivo para o destino garantindo que
    todos os trabalhos existentes permaneçam intactos.
    """
    paths = _work_paths(work_id)
    work_base_rel = paths['workDir']

    for entry in entries:
        rel = entry['rel']
        # rel é relativo à RAIZ do repositório (e.g. .workspace/studio/works/x/work.json)
        # Precisamos escrever no dest_root
        dest_file = os.path.join(dest_root, rel.replace('/', os.sep))

        # Garantir que o destino está dentro do dest_root
        if not _contained(dest_root, os.path.realpath(dest_file)):
            raise ValueError(f'Destino fora da raiz: {rel!r}')

        staged_abs = os.path.join(staging_dir, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
        shutil.copy2(staged_abs, dest_file)


# ---------------------------------------------------------------------------
# Utilitário compartilhado
# ---------------------------------------------------------------------------

def _load_manifest_from_zip(zip_path: str) -> dict[str, Any]:
    """Lê e valida o MANIFEST.json de dentro do ZIP."""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        if MANIFEST_ARCHIVE_PATH not in zf.namelist():
            raise ValueError(f'ZIP invalido: {MANIFEST_ARCHIVE_PATH!r} nao encontrado.')
        raw = zf.read(MANIFEST_ARCHIVE_PATH)
    try:
        manifest = json.loads(raw.decode('utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'MANIFEST.json invalido: {exc}') from exc
    if manifest.get('schemaVersion') != SCHEMA_VERSION:
        raise ValueError(
            f'Versao de schema incompativel: esperado {SCHEMA_VERSION}, '
            f'obtido {manifest.get("schemaVersion")!r}'
        )
    return manifest


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='studio_work_backup',
        description='Backup e restauracao de um trabalho salvo do Video Studio.',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    p_backup = sub.add_parser('backup', help='Empacota um trabalho num ZIP portátil')
    p_backup.add_argument('work_id', help='ID do trabalho (kebab-case)')
    p_backup.add_argument('output', help='Caminho do arquivo ZIP de saida')

    p_inspect = sub.add_parser('inspect', help='Inspeciona e verifica um arquivo de backup')
    p_inspect.add_argument('archive', help='Caminho do arquivo ZIP a inspecionar')

    p_restore = sub.add_parser('restore', help='Restaura um trabalho a partir de um backup')
    p_restore.add_argument('archive', help='Caminho do arquivo ZIP a restaurar')
    p_restore.add_argument(
        '--workspace', metavar='DIR',
        help='Raiz do workspace de destino (padrao: raiz do repositorio atual)',
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == 'backup':
            return cmd_backup(args)
        if args.command == 'inspect':
            return cmd_inspect(args)
        if args.command == 'restore':
            return cmd_restore(args)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
