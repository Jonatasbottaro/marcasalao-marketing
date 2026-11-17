"""CLI de backup e restauracao de um trabalho salvo do Video Studio.

Subcomandos:
  backup  <work-id> <saida.zip>  — empacota o trabalho num ZIP portatil
  inspect <arquivo.zip>          — lista conteudo e verifica dependencias
  restore <arquivo.zip>          — restaura o trabalho num workspace de destino

Uso:
  python tools/studio_work_backup.py backup meu-trabalho backup.zip
  python tools/studio_work_backup.py inspect backup.zip
  python tools/studio_work_backup.py restore backup.zip --workspace /outro/checkout

Regras de escopo (v1):
  Inclui: work.json, editorial.json, planning.json,
          media-library.json, drafts/ (video, carousel, motion), media/ do trabalho.
  Exclui: review-state.json (aprovacoes fora desta versao), credenciais,
          caches, fila, entregas renderizadas, SQLite.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 1
MANIFEST_ARCHIVE_PATH = "MANIFEST.json"
KEBAB_CASE_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

# Chaves de work_paths() que fazem parte do backup.
# reviewStateFile (review-state.json) foi explicitamente excluido para manter
# aprovacoes fora da versao v1.
_FILE_PATH_KEYS = (
    'workFile',
    'editorialFile',
    'planningFile',
    'mediaLibraryFile',
    'videoDraft',
    'carouselDraft',
    'motionPlan',
)

_ALLOWED_INDIVIDUAL_REL_FILES = {
    'work.json',
    'editorial.json',
    'planning.json',
    'media-library.json',
    'drafts/video.request.json',
    'drafts/carousel.request.json',
    'drafts/motion.plan.json',
}


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


def _is_allowed_package_entry(work_id: str, rel_path: str) -> bool:
    """Valida se uma entrada do ZIP pertence aos arquivos permitidos do trabalho."""
    norm = rel_path.replace('\\', '/')
    if norm == MANIFEST_ARCHIVE_PATH:
        return True
    base_prefix = f'.workspace/studio/works/{work_id}/'
    if not norm.startswith(base_prefix):
        return False

    rel_in_work = norm[len(base_prefix):]
    if not rel_in_work or rel_in_work.startswith('/'):
        return False

    # Prevenir path traversal e streams/letras de drive
    parts = rel_in_work.split('/')
    if any(p in ('..', '.', '') for p in parts) or ':' in rel_in_work:
        return False

    # Proibir expressamente review-state.json, deliveries, fila e banco
    if rel_in_work == 'review-state.json' or rel_in_work.startswith('deliveries/'):
        return False

    if rel_in_work in _ALLOWED_INDIVIDUAL_REL_FILES:
        return True

    if rel_in_work.startswith('media/'):
        return len(parts) >= 2

    return False


# ---------------------------------------------------------------------------
# Coleta de arquivos e dependências
# ---------------------------------------------------------------------------

def _collect_work_files(root: str, work_id: str) -> list[tuple[str, str]]:
    """Retorna lista de (rel_path, abs_path) dos arquivos do trabalho que existem."""
    paths = _work_paths(work_id)
    collected: list[tuple[str, str]] = []
    seen: set[str] = set()

    def _add(rel: str) -> None:
        rel_norm = rel.replace('\\', '/')
        if rel_norm in seen:
            return
        if not _is_allowed_package_entry(work_id, rel_norm):
            return
        abs_path = _confine(root, rel)
        if os.path.isfile(abs_path):
            seen.add(rel_norm)
            collected.append((rel_norm, abs_path))

    # Arquivos individuais permitidos
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


def _collect_dependencies(root: str, work_id: str) -> dict[str, Any]:
    """Coleta dependências verificáveis (ProjectManifest e mídias compartilhadas)."""
    paths = _work_paths(work_id)
    deps: dict[str, Any] = {
        'projectManifest': {},
        'sharedMedia': [],
    }

    # 1. ProjectManifest
    work_abs = _confine(root, paths['workFile'])
    if os.path.isfile(work_abs):
        try:
            with open(work_abs, 'r', encoding='utf-8') as fh:
                work_doc = json.load(fh)
            project_rel = (work_doc.get('project') or '').strip().replace('\\', '/')
            if project_rel:
                project_abs = _confine(root, project_rel)
                if os.path.isfile(project_abs):
                    deps['projectManifest'] = {
                        'rel': project_rel,
                        'sha256': sha256_file(project_abs),
                    }
        except (json.JSONDecodeError, OSError):
            pass

    # 2. Mídias compartilhadas (fora de .workspace/studio/works/{work_id}/)
    work_base_norm = paths['workDir'].replace('\\', '/') + '/'
    shared_media_map: dict[str, str] = {}

    def _consider_media_path(raw_path: Any) -> None:
        if not isinstance(raw_path, str):
            return
        rel = raw_path.strip().replace('\\', '/')
        if not rel or rel.startswith(work_base_norm):
            return
        if rel in shared_media_map:
            return
        try:
            abs_p = _confine(root, rel)
            if os.path.isfile(abs_p):
                shared_media_map[rel] = sha256_file(abs_p)
        except (ValueError, OSError):
            pass

    # Rascunho de vídeo
    video_abs = _confine(root, paths['videoDraft'])
    if os.path.isfile(video_abs):
        try:
            with open(video_abs, 'r', encoding='utf-8') as fh:
                vreq = json.load(fh)
            for m in vreq.get('media') or []:
                if isinstance(m, dict):
                    _consider_media_path(m.get('path'))
        except (json.JSONDecodeError, OSError):
            pass

    # Rascunho de carrossel
    carousel_abs = _confine(root, paths['carouselDraft'])
    if os.path.isfile(carousel_abs):
        try:
            with open(carousel_abs, 'r', encoding='utf-8') as fh:
                creq = json.load(fh)
            for m in creq.get('media') or []:
                if isinstance(m, dict):
                    _consider_media_path(m.get('path'))
        except (json.JSONDecodeError, OSError):
            pass

    # Biblioteca de mídia
    medialib_abs = _confine(root, paths['mediaLibraryFile'])
    if os.path.isfile(medialib_abs):
        try:
            with open(medialib_abs, 'r', encoding='utf-8') as fh:
                lib = json.load(fh)
            for asset in lib.get('assets') or []:
                if isinstance(asset, dict):
                    for ver in asset.get('versions') or []:
                        if isinstance(ver, dict):
                            _consider_media_path(ver.get('path'))
        except (json.JSONDecodeError, OSError):
            pass

    deps['sharedMedia'] = [
        {'rel': rel, 'sha256': digest}
        for rel, digest in sorted(shared_media_map.items())
    ]
    return deps


def _build_manifest(root: str, work_id: str, files: list[tuple[str, str]]) -> dict[str, Any]:
    """Constrói o manifesto JSON v1."""
    dependencies = _collect_dependencies(root, work_id)
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
        'dependencies': dependencies,
    }


# ---------------------------------------------------------------------------
# Validação compartilhada (inspect & restore)
# ---------------------------------------------------------------------------

@dataclass
class FileCheck:
    rel: str
    status: str  # 'OK', 'MISSING_IN_ZIP', 'HASH_MISMATCH', 'SIZE_MISMATCH', 'FORBIDDEN'
    expected_sha256: str = ''
    actual_sha256: str = ''
    expected_size: int = 0
    actual_size: int = 0
    message: str = ''


@dataclass
class DependencyCheck:
    dep_type: str  # 'projectManifest' ou 'sharedMedia'
    rel: str
    status: str    # 'OK', 'MISSING', 'HASH_MISMATCH'
    expected_sha256: str = ''
    actual_sha256: str = ''
    message: str = ''


@dataclass
class ValidationReport:
    is_valid: bool
    work_id: str
    manifest: dict
    file_checks: list[FileCheck] = field(default_factory=list)
    dependency_checks: list[DependencyCheck] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def validate_backup(zip_path: str, target_root: str) -> ValidationReport:
    """Validação compartilhada de integridade do arquivo e dependências no destino."""
    if not os.path.isfile(zip_path):
        return ValidationReport(
            is_valid=False, work_id='', manifest={},
            errors=[f'Arquivo de backup nao encontrado: {zip_path!r}']
        )

    # 1. Leitura e validação do ZIP e MANIFEST.json
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zip_names = set(zf.namelist())
            if MANIFEST_ARCHIVE_PATH not in zip_names:
                return ValidationReport(
                    is_valid=False, work_id='', manifest={},
                    errors=[f'Arquivo {MANIFEST_ARCHIVE_PATH!r} ausente no ZIP.']
                )
            manifest_bytes = zf.read(MANIFEST_ARCHIVE_PATH)
    except zipfile.BadZipFile as exc:
        return ValidationReport(
            is_valid=False, work_id='', manifest={},
            errors=[f'Arquivo ZIP corrompido ou invalido: {exc}']
        )

    try:
        manifest = json.loads(manifest_bytes.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return ValidationReport(
            is_valid=False, work_id='', manifest={},
            errors=[f'MANIFEST.json invalido: {exc}']
        )

    if manifest.get('schemaVersion') != SCHEMA_VERSION:
        return ValidationReport(
            is_valid=False, work_id='', manifest=manifest,
            errors=[
                f'Versao de schema incompativel: esperado {SCHEMA_VERSION}, '
                f'obtido {manifest.get("schemaVersion")!r}'
            ]
        )

    work_id = manifest.get('workId', '')
    if not isinstance(work_id, str) or not KEBAB_CASE_RE.match(work_id):
        return ValidationReport(
            is_valid=False, work_id=str(work_id), manifest=manifest,
            errors=[f'workId invalido no manifesto: {work_id!r}']
        )

    errors: list[str] = []
    file_checks: list[FileCheck] = []
    dependency_checks: list[DependencyCheck] = []

    # 2. Restringir entradas do pacote aos arquivos permitidos
    with zipfile.ZipFile(zip_path, 'r') as zf:
        all_zip_names = zf.namelist()
        manifest_files_set = {f['rel'] for f in manifest.get('files', []) if isinstance(f, dict)}

        for name in all_zip_names:
            if not _is_allowed_package_entry(work_id, name):
                msg = f'Entrada nao permitida ou caminho perigoso no ZIP: {name!r}'
                errors.append(msg)
                file_checks.append(FileCheck(rel=name, status='FORBIDDEN', message=msg))

        # 3. Conferir cada arquivo listado no manifesto contra o ZIP
        for entry in manifest.get('files', []):
            rel = entry.get('rel', '')
            exp_sha = entry.get('sha256', '')
            exp_size = entry.get('size', 0)

            if not _is_allowed_package_entry(work_id, rel):
                msg = f'Arquivo no manifesto fora do escopo permitido: {rel!r}'
                errors.append(msg)
                file_checks.append(FileCheck(rel=rel, status='FORBIDDEN', message=msg))
                continue

            if rel not in zip_names:
                msg = f'Arquivo do manifesto ausente no ZIP: {rel!r}'
                errors.append(msg)
                file_checks.append(FileCheck(rel=rel, status='MISSING_IN_ZIP', message=msg))
                continue

            try:
                data = zf.read(rel)
                act_sha = sha256_bytes(data)
                act_size = len(data)
                if act_sha != exp_sha:
                    msg = f'Hash divergente no ZIP para {rel}'
                    errors.append(msg)
                    file_checks.append(FileCheck(
                        rel=rel, status='HASH_MISMATCH',
                        expected_sha256=exp_sha, actual_sha256=act_sha,
                        expected_size=exp_size, actual_size=act_size,
                        message=msg
                    ))
                elif act_size != exp_size:
                    msg = f'Tamanho divergente no ZIP para {rel}'
                    errors.append(msg)
                    file_checks.append(FileCheck(
                        rel=rel, status='SIZE_MISMATCH',
                        expected_sha256=exp_sha, actual_sha256=act_sha,
                        expected_size=exp_size, actual_size=act_size,
                        message=msg
                    ))
                else:
                    file_checks.append(FileCheck(
                        rel=rel, status='OK',
                        expected_sha256=exp_sha, actual_sha256=act_sha,
                        expected_size=exp_size, actual_size=act_size
                    ))
            except Exception as exc:
                msg = f'Erro ao ler {rel} do ZIP: {exc}'
                errors.append(msg)
                file_checks.append(FileCheck(rel=rel, status='READ_ERROR', message=msg))

    # 4. Validar dependências no target_root (ProjectManifest e mídias compartilhadas)
    deps = manifest.get('dependencies') or {}

    # 4a. ProjectManifest
    pm_dep = deps.get('projectManifest') or {}
    pm_rel = pm_dep.get('rel')
    if pm_rel:
        exp_pm_sha = pm_dep.get('sha256', '')
        pm_abs = os.path.join(target_root, pm_rel.replace('/', os.sep))
        if not os.path.isfile(pm_abs):
            msg = f'ProjectManifest ausente no destino: {pm_rel}'
            errors.append(msg)
            dependency_checks.append(DependencyCheck(
                dep_type='projectManifest', rel=pm_rel, status='MISSING',
                expected_sha256=exp_pm_sha, message=msg
            ))
        else:
            act_pm_sha = sha256_file(pm_abs)
            if act_pm_sha != exp_pm_sha:
                msg = f'ProjectManifest com hash divergente no destino: {pm_rel}'
                errors.append(msg)
                dependency_checks.append(DependencyCheck(
                    dep_type='projectManifest', rel=pm_rel, status='HASH_MISMATCH',
                    expected_sha256=exp_pm_sha, actual_sha256=act_pm_sha, message=msg
                ))
            else:
                dependency_checks.append(DependencyCheck(
                    dep_type='projectManifest', rel=pm_rel, status='OK',
                    expected_sha256=exp_pm_sha, actual_sha256=act_pm_sha
                ))

    # 4b. Mídias compartilhadas
    shared_media_deps = deps.get('sharedMedia') or []
    for sm in shared_media_deps:
        sm_rel = sm.get('rel', '')
        exp_sm_sha = sm.get('sha256', '')
        if not sm_rel:
            continue
        sm_abs = os.path.join(target_root, sm_rel.replace('/', os.sep))
        if not os.path.isfile(sm_abs):
            msg = f'Midia compartilhada ausente no destino: {sm_rel}'
            errors.append(msg)
            dependency_checks.append(DependencyCheck(
                dep_type='sharedMedia', rel=sm_rel, status='MISSING',
                expected_sha256=exp_sm_sha, message=msg
            ))
        else:
            act_sm_sha = sha256_file(sm_abs)
            if act_sm_sha != exp_sm_sha:
                msg = f'Midia compartilhada com hash divergente no destino: {sm_rel}'
                errors.append(msg)
                dependency_checks.append(DependencyCheck(
                    dep_type='sharedMedia', rel=sm_rel, status='HASH_MISMATCH',
                    expected_sha256=exp_sm_sha, actual_sha256=act_sm_sha, message=msg
                ))
            else:
                dependency_checks.append(DependencyCheck(
                    dep_type='sharedMedia', rel=sm_rel, status='OK',
                    expected_sha256=exp_sm_sha, actual_sha256=act_sm_sha
                ))

    is_valid = len(errors) == 0
    return ValidationReport(
        is_valid=is_valid,
        work_id=work_id,
        manifest=manifest,
        file_checks=file_checks,
        dependency_checks=dependency_checks,
        errors=errors,
    )


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

    out_dir = os.path.dirname(output_path) or '.'
    os.makedirs(out_dir, exist_ok=True)
    fd, staging_path = tempfile.mkstemp(prefix='studio-backup-staging-', suffix='.zip', dir=out_dir)
    os.close(fd)
    try:
        with zipfile.ZipFile(staging_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(MANIFEST_ARCHIVE_PATH, manifest_bytes)
            for rel, abs_path in files:
                zf.write(abs_path, rel)
                print(f'  + {rel}')

        # Validar o arquivo gerado usando a validação compartilhada
        report = validate_backup(staging_path, root)
        if not report.is_valid:
            print('ERRO: Falha ao validar o backup recem-gerado:', file=sys.stderr)
            for err in report.errors:
                print(f'  - {err}', file=sys.stderr)
            return 1

        # Promover atomicamente
        if os.path.exists(output_path):
            os.remove(output_path)
        shutil.move(staging_path, output_path)
        staging_path = None
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
    shared = manifest['dependencies'].get('sharedMedia') or []
    if shared:
        print(f'  Midias compartilhadas: {len(shared)}')
    return 0


# ---------------------------------------------------------------------------
# Subcomando: inspect
# ---------------------------------------------------------------------------

def cmd_inspect(args: argparse.Namespace) -> int:
    zip_path = os.path.abspath(args.archive)
    if not os.path.isfile(zip_path):
        print(f'ERRO: Arquivo nao encontrado: {zip_path!r}', file=sys.stderr)
        return 1

    root = _find_root()
    dest_root = os.path.realpath(args.workspace) if getattr(args, 'workspace', None) else root

    report = validate_backup(zip_path, dest_root)

    print('=== Inspecao do backup ===')
    print(f'Trabalho : {report.work_id or "?"}')
    print(f'Exportado: {report.manifest.get("exportedAt", "?")}')
    print(f'Schema   : v{report.manifest.get("schemaVersion", "?")}')
    print(f'Arquivos : {len(report.manifest.get("files", []))}')
    print()

    print('--- Arquivos no pacote ---')
    for fc in report.file_checks:
        if fc.status == 'OK':
            print(f'  OK             : {fc.rel}')
        elif fc.status == 'HASH_MISMATCH':
            print(f'  HASH_DIVERGENTE: {fc.rel}  (esperado {fc.expected_sha256[:12]}… obtido {fc.actual_sha256[:12]}…)')
        elif fc.status == 'SIZE_MISMATCH':
            print(f'  TAMANHO_ERRADO : {fc.rel}  ({fc.actual_size} != {fc.expected_size})')
        elif fc.status == 'MISSING_IN_ZIP':
            print(f'  AUSENTE NO ZIP : {fc.rel}')
        elif fc.status == 'FORBIDDEN':
            print(f'  NAO PERMITIDO  : {fc.rel}')
        else:
            print(f'  ERRO ({fc.status}): {fc.rel}')

    print()
    print('--- Dependencias ---')
    if not report.dependency_checks:
        print('  Nenhuma dependencia registrada.')
    else:
        for dc in report.dependency_checks:
            tipo = 'Manifest' if dc.dep_type == 'projectManifest' else 'Midia'
            if dc.status == 'OK':
                print(f'  OK [{tipo}]       : {dc.rel}')
            elif dc.status == 'MISSING':
                print(f'  AUSENTE [{tipo}]  : {dc.rel}')
            elif dc.status == 'HASH_MISMATCH':
                print(f'  HASH_DIVERGENTE [{tipo}]: {dc.rel}')

    print()
    if report.is_valid:
        print('Resultado: OK — backup integro e dependencias satisfeitas.')
        return 0
    else:
        print(f'Resultado: ERRO — {len(report.errors)} problema(s) encontrado(s).')
        for err in report.errors:
            print(f'  - {err}', file=sys.stderr)
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
    dest_root = os.path.realpath(args.workspace) if args.workspace else root
    if not _contained(root, dest_root):
        print(f'ERRO: Destino fora da raiz do projeto: {dest_root!r}', file=sys.stderr)
        return 1

    # Validação compartilhada com inspect antes de qualquer modificação
    print('Validando integridade e dependencias do backup...')
    report = validate_backup(zip_path, dest_root)
    if not report.is_valid:
        print('ERRO: O backup nao passou na validacao de integridade e dependencias. Restauracao cancelada.', file=sys.stderr)
        for err in report.errors:
            print(f'  - {err}', file=sys.stderr)
        return 1

    work_id = report.work_id
    files_in_manifest = report.manifest.get('files', [])

    # Recusar expressamente qualquer diretório de destino já existente
    dest_work_dir = os.path.join(dest_root, '.workspace', 'studio', 'works', work_id)
    if os.path.exists(dest_work_dir):
        print(
            f'ERRO: O diretorio de destino ja existe: {dest_work_dir!r}.\n'
            f'      A restauracao so e permitida em destinos onde o trabalho nao existe.',
            file=sys.stderr,
        )
        return 1

    # Staging em diretório temporário exclusivo no MESMO sistema de arquivos do destino
    works_parent = os.path.dirname(dest_work_dir)
    os.makedirs(works_parent, exist_ok=True)
    staging_work_dir = tempfile.mkdtemp(prefix=f'.backup-staging-{work_id}-', dir=works_parent)

    base_prefix = f'.workspace/studio/works/{work_id}/'

    try:
        print(f'Extraindo para staging exclusivo: {staging_work_dir}')
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for entry in files_in_manifest:
                rel = entry['rel']
                if not rel.startswith(base_prefix):
                    raise ValueError(f'Entrada nao esperada para o trabalho: {rel!r}')
                rel_in_work = rel[len(base_prefix):]
                dest_file = os.path.join(staging_work_dir, rel_in_work.replace('/', os.sep))
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                data = zf.read(rel)
                if sha256_bytes(data) != entry['sha256']:
                    raise RuntimeError(f'Falha de integridade ao extrair: {rel!r}')
                with open(dest_file, 'wb') as fh:
                    fh.write(data)

        # Validação completa do staging antes da promoção
        print('Validando conteudo montado no staging...')
        for entry in files_in_manifest:
            rel = entry['rel']
            rel_in_work = rel[len(base_prefix):]
            staged_abs = os.path.join(staging_work_dir, rel_in_work.replace('/', os.sep))
            if not os.path.isfile(staged_abs):
                raise RuntimeError(f'Arquivo ausente no staging: {rel_in_work!r}')
            if sha256_file(staged_abs) != entry['sha256']:
                raise RuntimeError(f'Hash divergente no staging para: {rel_in_work!r}')

        # Publicar o diretório final em uma única operação
        print(f'Publicando trabalho em operacao atomica: {dest_work_dir}')
        os.replace(staging_work_dir, dest_work_dir)
        staging_work_dir = None  # Marcador de promoção bem-sucedida

    except Exception as exc:
        print(f'ERRO durante a restauracao: {exc}', file=sys.stderr)
        return 1
    finally:
        if staging_work_dir and os.path.exists(staging_work_dir):
            shutil.rmtree(staging_work_dir, ignore_errors=True)

    print('\nRestauracao concluida!')
    print(f'  Trabalho: {work_id}')
    print(f'  Local   : {dest_work_dir}')
    print(f'  Arquivos: {len(files_in_manifest)}')
    return 0


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
    p_inspect.add_argument(
        '--workspace', metavar='DIR',
        help='Raiz do workspace para checagem de dependencias (padrao: raiz atual)',
    )

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
