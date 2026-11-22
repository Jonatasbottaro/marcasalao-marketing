"""Testes de unidade e integracao para studio_work_backup.

Cobre:
- Validacao compartilhada de integridade e dependencias (inspect e restore)
- ProjectManifest e midias compartilhadas por caminho relativo e SHA-256
- Restricao estrita de entradas aos arquivos permitidos do trabalho indicado
- Exclusao de review-state.json e aprovacoes
- Recusa expressa de diretorio de destino ja existente (no inicio e pre-promocao/TOCTOU)
- Montagem em staging exclusivo no mesmo sistema de arquivos e promocao atomica
- Regressao com injecao de falha comprovando que nenhum trabalho parcial aparece
- Validacao estrita de formato de MANIFEST.json (malformado, non-dict, campos obrigatorios)
- Exigencia de work.json e correspondencia 1:1 entre arquivos declarados e entradas do ZIP
- Rejeicao de entradas duplicadas (no ZIP, em files e em sharedMedia)
- Confinamento e prevencao de path traversal em dependencias e destino de restauracao
- Dependencia obrigatoria ausente na origem bloqueia backup
- Preservacao atomica de arquivo de backup anterior em caso de erro
- Aceite completo em dois workspaces com reabertura pelo Studio e comparacao de pre-voo real (ready == True, zero blockers, fila vazia)

Todos os workspaces de teste ficam sob <RAIZ>/.workspace/tmp/studio-work-backup/tests/.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

# Adiciona tools/ ao PYTHONPATH
_TOOLS_DIR = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.abspath(_TOOLS_DIR))

import build_video  # noqa: E402
import render_local  # noqa: E402
import studio_queue  # noqa: E402
import studio_work_backup as swb  # noqa: E402
import video_studio  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers de raiz e fixture
# ---------------------------------------------------------------------------

def _get_worktree_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def _get_main_root() -> str:
    root = _get_worktree_root()
    while not os.path.isdir(os.path.join(root, '.git')):
        parent = os.path.dirname(root)
        if parent == root:
            break
        root = parent
    return root


def _root_tmp() -> str:
    """Raiz para workspaces de teste — fica dentro de <RAIZ>/.workspace/tmp/."""
    main_root = _get_main_root()
    tmp = os.path.join(main_root, '.workspace', 'tmp', 'studio-work-backup', 'tests')
    os.makedirs(tmp, exist_ok=True)
    return tmp


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _write_bytes(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as fh:
        fh.write(data)


def _make_fake_project(root: str, project_rel: str) -> str:
    """Cria um ProjectManifest valido para Studio e preflight."""
    abs_path = os.path.join(root, project_rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    doc = {
        'schemaVersion': 1,
        'id': 'test-project',
        'name': 'Projeto de Teste',
        'locale': 'pt-BR',
        'timezone': 'America/Sao_Paulo',
        'brandTheme': 'marca-salao',
        'assetRoot': '.workspace/studio/media',
        'contentPolicies': {
            'requireApprovedBriefing': False,
            'requireApprovedScript': False,
            'prohibitPersonalData': True,
            'requireFunctionalEvidence': False,
        },
        'outputProfiles': [
            'instagram-reels-video',
            'youtube-video-horizontal',
            'instagram-feed-image-square',
        ],
    }
    _write_json(abs_path, doc)
    return abs_path


def _make_fake_work(root: str, work_id: str, project_rel: str, shared_media_rel: str | None = None) -> dict:
    """Cria a estrutura de um trabalho ficticio completo."""
    base = os.path.join(root, '.workspace', 'studio', 'works', work_id)
    drafts = os.path.join(base, 'drafts')
    media = os.path.join(base, 'media')
    for d in (base, drafts, media):
        os.makedirs(d, exist_ok=True)

    work_doc = {
        'id': work_id,
        'name': f'Trabalho {work_id}',
        'project': project_rel,
        'title': f'Titulo {work_id}',
    }
    _write_json(os.path.join(base, 'work.json'), work_doc)
    _write_json(os.path.join(base, 'editorial.json'), {
        'titulo': 'Arte Exemplo',
        'channels': {'instagram-reels-video': {'texto': 'Legenda Instagram'}},
    })
    # Arquivo de review-state: deve ser ignorado no backup
    _write_json(os.path.join(base, 'review-state.json'), {'channels': {'aprovado': True}})
    _write_json(os.path.join(base, 'planning.json'), {'etapas': []})

    # Midia interna do trabalho
    img_work_rel = f'.workspace/studio/works/{work_id}/media/imagem01.png'
    img_work_abs = os.path.join(root, img_work_rel.replace('/', os.sep))
    _write_bytes(img_work_abs, b'\x89PNG\r\n\x1a\n' + b'fake-image-work-bytes' * 30)

    media_list = [
        {'id': 'img-work', 'path': img_work_rel, 'type': 'image', 'origin': 'studio-work', 'license': 'owned'}
    ]
    if shared_media_rel:
        media_list.append(
            {'id': 'img-shared', 'path': shared_media_rel, 'type': 'image', 'origin': 'external-tool', 'license': 'owned'}
        )

    _write_json(os.path.join(drafts, 'video.request.json'), {
        'schemaVersion': 1,
        'id': f'{work_id}-video',
        'project': project_rel,
        'media': media_list,
        'scenes': [
            {'id': 'cena-1', 'durationMs': 3000, 'mediaId': 'img-work', 'title': 'Cena 1', 'caption': 'Abertura', 'narration': 'Texto 1'}
        ],
    })
    _write_json(os.path.join(drafts, 'carousel.request.json'), {
        'schemaVersion': 1,
        'id': f'{work_id}-carrossel',
        'project': project_rel,
        'media': media_list,
        'cards': [{'id': 'card-1', 'title': 'Card 1', 'mediaId': 'img-work'}],
    })
    _write_json(os.path.join(drafts, 'motion.plan.json'), {
        'schemaVersion': 1,
        'id': f'{work_id}-motion',
        'effects': [],
    })
    _write_json(os.path.join(base, 'media-library.json'), {
        'schemaVersion': 1,
        'assets': [
            {
                'id': 'asset-work',
                'versions': [{'versionId': 'v1', 'path': img_work_rel, 'sha256': swb.sha256_file(img_work_abs)}],
            }
        ],
    })
    return {'base': base, 'work': work_doc}


def _make_args(command: str, **kwargs):
    ns = argparse.Namespace(command=command, workspace=None)
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def _copy_repo_subdirs(worktree: str, target_ws: str) -> None:
    """Copia tools/, platform/, tenants/ e schemas/ para workspace isolado.

    tenants/ e schemas/ sao necessarios para que o preflight do Studio resolva
    o tenant do projeto (``_resolve_tenant_id``/``tenant_ids`` leem
    ``<root>/tenants/``) e para a validacao de contratos; sem eles o aceite
    falha com "nenhum tenant disponivel para o preflight" em qualquer estacao.
    """
    for sub in (
        'tools', 'platform', 'tenants', 'schemas',
        # Acervo versionado auditado pelas lentes do editorial_qa no preflight:
        # sem ele, um workspace isolado reprova com ENTREGA_AUSENTE etc.
        '02-reels-shorts', '01-insta-stories', '04-legendas',
    ):
        src = render_local.fs_path(os.path.join(worktree, sub), force=True)
        dst = render_local.fs_path(os.path.join(target_ws, sub), force=True)
        ignore_fn = (
            shutil.ignore_patterns('node_modules', '__pycache__')
            if sub == 'tools'
            else shutil.ignore_patterns('__pycache__', '*.mp4', '*.wav')
        )
        shutil.copytree(
            src,
            dst,
            ignore=ignore_fn,
            copy_function=lambda s, d: shutil.copy2(
                render_local.fs_path(s, force=True),
                render_local.fs_path(d, force=True),
            ),
        )


# ---------------------------------------------------------------------------
# Classe base para isolamento de workspace
# ---------------------------------------------------------------------------

class _WorkspaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base_tmp = _root_tmp()
        self.ws = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws1-')
        self._patcher = patch('studio_work_backup._find_root', return_value=self.ws)
        self._patcher.start()

    def tearDown(self) -> None:
        self._patcher.stop()
        shutil.rmtree(render_local.fs_path(self.ws, force=True), ignore_errors=True)

    def _zip_path(self, name: str = 'backup.zip') -> str:
        p = os.path.join(self.ws, '.workspace', 'tmp', name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        return p


# ---------------------------------------------------------------------------
# Testes de Funcionalidade e Regressoes
# ---------------------------------------------------------------------------

class TestBackupRoundTrip(_WorkspaceTest):
    """Backup + restore produz arquivos identicos com comparacao de hashes."""

    def test_backup_restore_hashes_match(self) -> None:
        work_id = 'meu-trabalho'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        zip_path = self._zip_path('rt.zip')
        rc = swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))
        self.assertEqual(rc, 0)

        ws2 = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws2-rt-')
        try:
            proj_dst = os.path.join(ws2, project_rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(proj_dst), exist_ok=True)
            shutil.copy2(os.path.join(self.ws, project_rel.replace('/', os.sep)), proj_dst)

            with patch('studio_work_backup._find_root', return_value=ws2):
                rc_rest = swb.cmd_restore(_make_args('restore', archive=zip_path, workspace=ws2))
            self.assertEqual(rc_rest, 0)

            orig_files = swb._collect_work_files(self.ws, work_id)
            for rel, orig_abs in orig_files:
                restored_abs = os.path.join(ws2, rel.replace('/', os.sep))
                self.assertTrue(os.path.isfile(restored_abs), f'Arquivo deve existir: {rel}')
                self.assertEqual(
                    swb.sha256_file(orig_abs),
                    swb.sha256_file(restored_abs),
                    f'Hash deve coincidir: {rel}',
                )
        finally:
            shutil.rmtree(render_local.fs_path(ws2, force=True), ignore_errors=True)


class TestReviewStateExcluded(_WorkspaceTest):
    """Garante que review-state.json e aprovacoes fiquem fora do backup."""

    def test_review_state_not_in_backup(self) -> None:
        work_id = 'sem-aprovacoes'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        orig_review_file = os.path.join(self.ws, '.workspace', 'studio', 'works', work_id, 'review-state.json')
        self.assertTrue(os.path.isfile(orig_review_file))

        zip_path = self._zip_path('sem-aprovacoes.zip')
        rc = swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))
        self.assertEqual(rc, 0)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            names = zf.namelist()
            self.assertNotIn(f'.workspace/studio/works/{work_id}/review-state.json', names)
            self.assertNotIn('review-state.json', names)

        ws2 = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws2-no-review-')
        try:
            proj_dst = os.path.join(ws2, project_rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(proj_dst), exist_ok=True)
            shutil.copy2(os.path.join(self.ws, project_rel.replace('/', os.sep)), proj_dst)

            with patch('studio_work_backup._find_root', return_value=ws2):
                rc = swb.cmd_restore(_make_args('restore', archive=zip_path, workspace=ws2))
            self.assertEqual(rc, 0)

            restored_review = os.path.join(ws2, '.workspace', 'studio', 'works', work_id, 'review-state.json')
            self.assertFalse(os.path.exists(restored_review), 'review-state.json nao deve ser restaurado')
        finally:
            shutil.rmtree(render_local.fs_path(ws2, force=True), ignore_errors=True)


class TestSharedMediaAndProjectDependencies(_WorkspaceTest):
    """Verifica deteccao, inspecao e restauracao com midias compartilhadas e ProjectManifest."""

    def test_shared_media_dependency_validation(self) -> None:
        work_id = 'com-midia-compartilhada'
        project_rel = 'platform/examples/projects/test.project.json'
        shared_rel = 'platform/examples/media/logo-compartilhado.png'

        _make_fake_project(self.ws, project_rel)
        shared_abs = os.path.join(self.ws, shared_rel.replace('/', os.sep))
        _write_bytes(shared_abs, b'\x89PNG\r\n\x1a\n' + b'fake-shared-media-bytes' * 20)

        _make_fake_work(self.ws, work_id, project_rel, shared_media_rel=shared_rel)

        zip_path = self._zip_path('shared.zip')
        rc = swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))
        self.assertEqual(rc, 0)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            manifest = json.loads(zf.read('MANIFEST.json').decode('utf-8'))
            names = set(zf.namelist())
            self.assertNotIn(shared_rel, names, 'Midia compartilhada nao deve estar dentro do ZIP do trabalho')

        deps = manifest.get('dependencies', {})
        self.assertEqual(deps['projectManifest']['rel'], project_rel)
        self.assertEqual(len(deps['sharedMedia']), 1)
        self.assertEqual(deps['sharedMedia'][0]['rel'], shared_rel)
        self.assertEqual(deps['sharedMedia'][0]['sha256'], swb.sha256_file(shared_abs))

        # Inspecao no workspace 1: deve dar OK
        rc = swb.cmd_inspect(_make_args('inspect', archive=zip_path))
        self.assertEqual(rc, 0)

        # No workspace 2 sem as dependencias: inspect e restore devem falhar apontando a falta
        ws2 = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws2-deps-')
        try:
            # 1. Sem nada: falha em projectManifest e sharedMedia
            rep = swb.validate_backup(zip_path, ws2)
            self.assertFalse(rep.is_valid)
            self.assertTrue(any('ProjectManifest ausente' in e for e in rep.errors))
            self.assertTrue(any('Midia compartilhada ausente' in e for e in rep.errors))

            # 2. Copia apenas o ProjectManifest: ainda falha na midia compartilhada
            proj_dst = os.path.join(ws2, project_rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(proj_dst), exist_ok=True)
            shutil.copy2(os.path.join(self.ws, project_rel.replace('/', os.sep)), proj_dst)

            rep2 = swb.validate_backup(zip_path, ws2)
            self.assertFalse(rep2.is_valid)
            self.assertTrue(any('Midia compartilhada ausente' in e for e in rep2.errors))

            # 3. Adiciona a midia compartilhada com hash divergente: falha com HASH_DIVERGENTE
            shared_dst = os.path.join(ws2, shared_rel.replace('/', os.sep))
            _write_bytes(shared_dst, b'bytes-adulterados-divergentes')
            rep3 = swb.validate_backup(zip_path, ws2)
            self.assertFalse(rep3.is_valid)
            self.assertTrue(any('Midia compartilhada com hash divergente' in e for e in rep3.errors))

            # 4. Corrige o hash da midia compartilhada: agora e valido
            shutil.copy2(shared_abs, shared_dst)
            rep4 = swb.validate_backup(zip_path, ws2)
            self.assertTrue(rep4.is_valid)

            # Restauracao agora funciona perfeitamente
            with patch('studio_work_backup._find_root', return_value=ws2):
                rc_rest = swb.cmd_restore(_make_args('restore', archive=zip_path, workspace=ws2))
            self.assertEqual(rc_rest, 0)

        finally:
            shutil.rmtree(render_local.fs_path(ws2, force=True), ignore_errors=True)


class TestRestrictedPackageEntries(_WorkspaceTest):
    """Restringe entradas do pacote aos arquivos permitidos do trabalho e valida caminhos."""

    def test_rejects_foreign_work_files(self) -> None:
        work_id = 'meu-trabalho'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        zip_path = self._zip_path('corrupt-foreign.zip')
        swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))

        tampered_path = zip_path + '.foreign.zip'
        with zipfile.ZipFile(zip_path, 'r') as zin, zipfile.ZipFile(tampered_path, 'w') as zout:
            for item in zin.infolist():
                zout.writestr(item, zin.read(item.filename))
            zout.writestr('.workspace/studio/works/outro-trabalho/work.json', b'{"id":"outro"}')

        rep = swb.validate_backup(tampered_path, self.ws)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any('Entrada nao permitida' in e for e in rep.errors))
        if os.path.exists(tampered_path):
            os.remove(tampered_path)

    def test_rejects_path_traversal(self) -> None:
        work_id = 'traversal-work'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        zip_path = self._zip_path('traversal.zip')
        swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))

        tampered_path = zip_path + '.badpath.zip'
        with zipfile.ZipFile(zip_path, 'r') as zin, zipfile.ZipFile(tampered_path, 'w') as zout:
            for item in zin.infolist():
                zout.writestr(item, zin.read(item.filename))
            zout.writestr(f'.workspace/studio/works/{work_id}/../../evil.json', b'evil')

        rep = swb.validate_backup(tampered_path, self.ws)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any('Entrada nao permitida ou caminho perigoso' in e for e in rep.errors))
        if os.path.exists(tampered_path):
            os.remove(tampered_path)


class TestRestoreDestinationAlreadyExists(_WorkspaceTest):
    """Recusa qualquer diretorio de destino ja existente, inclusive se criado durante o staging."""

    def test_refuse_existing_directory(self) -> None:
        work_id = 'ja-existe'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        zip_path = self._zip_path('exists.zip')
        swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))

        ws2 = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws2-occupied-')
        try:
            proj_dst = os.path.join(ws2, project_rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(proj_dst), exist_ok=True)
            shutil.copy2(os.path.join(self.ws, project_rel.replace('/', os.sep)), proj_dst)

            occupied_dir = os.path.join(ws2, '.workspace', 'studio', 'works', work_id)
            os.makedirs(occupied_dir, exist_ok=True)

            with patch('studio_work_backup._find_root', return_value=ws2):
                rc = swb.cmd_restore(_make_args('restore', archive=zip_path, workspace=ws2))
            self.assertEqual(rc, 1, 'Restore deve recusar diretorio existente')
            self.assertEqual(len(os.listdir(occupied_dir)), 0)
        finally:
            shutil.rmtree(render_local.fs_path(ws2, force=True), ignore_errors=True)

    def test_refuse_destination_created_during_staging(self) -> None:
        """TOCTOU: se o diretorio de destino (mesmo vazio) for criado durante o staging, restore cancela."""
        work_id = 'toctou-work'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        zip_path = self._zip_path('toctou.zip')
        swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))

        ws2 = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws2-toctou-')
        try:
            proj_dst = os.path.join(ws2, project_rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(proj_dst), exist_ok=True)
            shutil.copy2(os.path.join(self.ws, project_rel.replace('/', os.sep)), proj_dst)

            dest_work_dir = os.path.join(ws2, '.workspace', 'studio', 'works', work_id)
            works_parent = os.path.dirname(dest_work_dir)
            self.assertFalse(os.path.exists(dest_work_dir))

            # Simular criacao concorrente do diretorio de destino VAZIO durante a gravacao no staging
            created_flag = [False]
            orig_open = open

            def open_and_create_dest(path, mode='r', *args, **kwargs):
                if 'wb' in mode and '.backup-staging-' in str(path) and not created_flag[0]:
                    created_flag[0] = True
                    os.makedirs(dest_work_dir, exist_ok=True)
                return orig_open(path, mode, *args, **kwargs)

            with patch('builtins.open', side_effect=open_and_create_dest), patch('studio_work_backup._find_root', return_value=ws2):
                rc = swb.cmd_restore(_make_args('restore', archive=zip_path, workspace=ws2))

            self.assertEqual(rc, 1, 'Restore deve abortar quando destino vazio for criado durante staging')
            self.assertTrue(os.path.isdir(dest_work_dir), 'Diretorio vazio concorrente deve existir')
            self.assertEqual(len(os.listdir(dest_work_dir)), 0, 'Diretorio vazio de destino deve ser preservado vazio e intacto')

            staging_leftovers = [
                d for d in os.listdir(works_parent)
                if d.startswith(f'.backup-staging-{work_id}')
            ]
            self.assertEqual(len(staging_leftovers), 0, 'Staging deve ter sido limpo no finally')
        finally:
            shutil.rmtree(render_local.fs_path(ws2, force=True), ignore_errors=True)

    def test_publish_work_directory_refuses_empty_destination(self) -> None:
        """Operacao de publicacao recusa destino vazio ja existente, preservando-o intacto."""
        staging_dir = tempfile.mkdtemp(dir=self.base_tmp, prefix='stg-')
        dest_dir = tempfile.mkdtemp(dir=self.base_tmp, prefix='dst-empty-')
        try:
            with open(os.path.join(staging_dir, 'sample.txt'), 'w', encoding='utf-8') as f:
                f.write('conteudo de staging')
            self.assertEqual(len(os.listdir(dest_dir)), 0)

            with self.assertRaises(FileExistsError):
                swb._publish_work_directory(staging_dir, dest_dir)

            self.assertTrue(os.path.isdir(dest_dir), 'Destino deve ser preservado')
            self.assertEqual(len(os.listdir(dest_dir)), 0, 'Destino vazio deve continuar vazio')
            self.assertTrue(os.path.isdir(staging_dir), 'Staging deve ser preservado intacto pela funcao de publicacao')
            with open(os.path.join(staging_dir, 'sample.txt'), 'r', encoding='utf-8') as f:
                self.assertEqual(f.read(), 'conteudo de staging')
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)
            shutil.rmtree(dest_dir, ignore_errors=True)

    def test_publish_work_directory_success(self) -> None:
        """Operacao de publicacao promove atomicamente o staging quando destino nao existe."""
        staging_dir = tempfile.mkdtemp(dir=self.base_tmp, prefix='stg-ok-')
        dest_dir = os.path.join(self.base_tmp, 'dst-new')
        try:
            with open(os.path.join(staging_dir, 'sample.txt'), 'w', encoding='utf-8') as f:
                f.write('conteudo promovido')

            self.assertFalse(os.path.exists(dest_dir))
            swb._publish_work_directory(staging_dir, dest_dir)

            self.assertTrue(os.path.isdir(dest_dir))
            with open(os.path.join(dest_dir, 'sample.txt'), 'r', encoding='utf-8') as f:
                self.assertEqual(f.read(), 'conteudo promovido')
            self.assertFalse(os.path.exists(staging_dir), 'Staging original nao deve mais existir apos rename')
        finally:
            shutil.rmtree(dest_dir, ignore_errors=True)

    def test_rename_noreplace_linux_semantics(self) -> None:
        """Valida que _rename_noreplace_linux lida corretamente com sucesso, EEXIST e fallback."""
        from unittest.mock import MagicMock
        import errno

        mock_libc = MagicMock()
        mock_libc.renameat2.return_value = 0

        with patch('ctypes.CDLL', return_value=mock_libc), patch('ctypes.util.find_library', return_value='libc.so.6'):
            res = swb._rename_noreplace_linux('src', 'dst')
            self.assertTrue(res)

        mock_libc.renameat2.return_value = -1
        with patch('ctypes.CDLL', return_value=mock_libc), patch('ctypes.util.find_library', return_value='libc.so.6'), patch('ctypes.get_errno', return_value=errno.EEXIST):
            with self.assertRaises(FileExistsError):
                swb._rename_noreplace_linux('src', 'dst')

        with patch('ctypes.CDLL', return_value=mock_libc), patch('ctypes.util.find_library', return_value='libc.so.6'), patch('ctypes.get_errno', return_value=errno.ENOSYS):
            res = swb._rename_noreplace_linux('src', 'dst')
            self.assertFalse(res)

    def test_publish_work_directory_refuses_when_renameat2_unavailable(self) -> None:
        """Quando renameat2 for indisponivel no Linux/POSIX, recusa sem chamar os.rename e preserva destino."""
        staging_dir = tempfile.mkdtemp(dir=self.base_tmp, prefix='stg-nounavail-')
        dest_dir = tempfile.mkdtemp(dir=self.base_tmp, prefix='dst-nounavail-')
        try:
            with open(os.path.join(staging_dir, 'sample.txt'), 'w', encoding='utf-8') as f:
                f.write('conteudo de staging')
            with open(os.path.join(dest_dir, 'existente.txt'), 'w', encoding='utf-8') as f:
                f.write('arquivo destino preservado')

            # Simula race condition onde o destino nao foi detectado no lexists inicial,
            # mas renameat2 nao esta disponivel no sistema: deve abortar com RuntimeError
            # e JAMAIS chamar os.rename comum.
            with patch('studio_work_backup.os.path.lexists', return_value=False), \
                 patch('studio_work_backup.os.name', 'posix'), \
                 patch('studio_work_backup._rename_noreplace_linux', return_value=False), \
                 patch('studio_work_backup.os.rename') as mock_rename:
                with self.assertRaises(RuntimeError) as ctx:
                    swb._publish_work_directory(staging_dir, dest_dir)
                self.assertIn('renameat2(RENAME_NOREPLACE)', str(ctx.exception))
                mock_rename.assert_not_called()

            # Destino preservado
            self.assertTrue(os.path.isfile(os.path.join(dest_dir, 'existente.txt')))
            with open(os.path.join(dest_dir, 'existente.txt'), 'r', encoding='utf-8') as f:
                self.assertEqual(f.read(), 'arquivo destino preservado')
            # Staging preservado (limpeza e responsabilidade do chamador/CLI)
            self.assertTrue(os.path.isfile(os.path.join(staging_dir, 'sample.txt')))
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)
            shutil.rmtree(dest_dir, ignore_errors=True)

    def test_publish_work_directory_refuses_even_nonexistent_dest_when_renameat2_unavailable(self) -> None:
        """Mesmo com destino inexistente, recusa se renameat2 nao estiver disponivel no Linux/POSIX."""
        staging_dir = tempfile.mkdtemp(dir=self.base_tmp, prefix='stg-nonex-')
        dest_dir = os.path.join(self.base_tmp, 'dst-never-created')
        try:
            with open(os.path.join(staging_dir, 'sample.txt'), 'w', encoding='utf-8') as f:
                f.write('conteudo de staging')

            with patch('studio_work_backup.os.name', 'posix'), \
                 patch('studio_work_backup._rename_noreplace_linux', return_value=False), \
                 patch('studio_work_backup.os.rename') as mock_rename:
                with self.assertRaises(RuntimeError) as ctx:
                    swb._publish_work_directory(staging_dir, dest_dir)
                self.assertIn('renameat2(RENAME_NOREPLACE)', str(ctx.exception))
                mock_rename.assert_not_called()

            self.assertFalse(os.path.exists(dest_dir), 'Destino nao deve ter sido criado')
            self.assertTrue(os.path.isdir(staging_dir))
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

    def test_restore_cli_refuses_when_renameat2_unavailable(self) -> None:
        """CLI: simula renameat2 indisponivel no restore e confirma recusa com erro, ausencia de os.rename, destino preservado e limpeza do staging."""
        work_id = 'unavail-work'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        zip_path = self._zip_path('unavail.zip')
        swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))

        ws2 = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws2-unavail-')
        try:
            proj_dst = os.path.join(ws2, project_rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(proj_dst), exist_ok=True)
            shutil.copy2(os.path.join(self.ws, project_rel.replace('/', os.sep)), proj_dst)

            dest_work_dir = os.path.join(ws2, '.workspace', 'studio', 'works', work_id)
            works_parent = os.path.dirname(dest_work_dir)
            self.assertFalse(os.path.exists(dest_work_dir))

            # Simular criacao de um diretorio concorrente no destino durante o staging
            created_flag = [False]
            orig_open = open

            def open_and_create_dest(path, mode='r', *args, **kwargs):
                if 'wb' in mode and '.backup-staging-' in str(path) and not created_flag[0]:
                    created_flag[0] = True
                    os.makedirs(dest_work_dir, exist_ok=True)
                    with orig_open(os.path.join(dest_work_dir, 'concorrente.txt'), 'w', encoding='utf-8') as cf:
                        cf.write('destino existente intacto')
                return orig_open(path, mode, *args, **kwargs)

            stderr_buf = io.StringIO()
            with patch('builtins.open', side_effect=open_and_create_dest), \
                 patch('studio_work_backup._find_root', return_value=ws2), \
                 patch('studio_work_backup.os.name', 'posix'), \
                 patch('studio_work_backup._rename_noreplace_linux', return_value=False), \
                 patch('studio_work_backup.os.rename') as mock_rename, \
                 patch('sys.stderr', stderr_buf):
                rc = swb.cmd_restore(_make_args('restore', archive=zip_path, workspace=ws2))

            self.assertEqual(rc, 1, 'Restore deve retornar codigo diferente de zero quando recurso estiver indisponivel')
            mock_rename.assert_not_called()

            # Diagnostico claro no stderr
            stderr_text = stderr_buf.getvalue()
            self.assertTrue(
                'renameat2(RENAME_NOREPLACE)' in stderr_text or 'ja existe' in stderr_text,
                f'Diagnostico deve relatar erro/recurso indisponivel: {stderr_text}'
            )

            # Destino preservado intacto
            self.assertTrue(os.path.isdir(dest_work_dir))
            with open(os.path.join(dest_work_dir, 'concorrente.txt'), 'r', encoding='utf-8') as cf:
                self.assertEqual(cf.read(), 'destino existente intacto')

            # Staging completamente limpo pelo finally
            staging_leftovers = [
                d for d in os.listdir(works_parent)
                if d.startswith(f'.backup-staging-{work_id}')
            ]
            self.assertEqual(len(staging_leftovers), 0, 'Staging deve ter sido limpo no finally')
        finally:
            shutil.rmtree(render_local.fs_path(ws2, force=True), ignore_errors=True)

    def test_restore_cli_refuses_clean_destination_when_renameat2_unavailable(self) -> None:
        """CLI: mesmo com destino livre, restore aborta se renameat2 for indisponivel, sem chamar rename e limpando staging."""
        work_id = 'unavail-clean'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        zip_path = self._zip_path('unavail-clean.zip')
        swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))

        ws2 = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws2-unavail-clean-')
        try:
            proj_dst = os.path.join(ws2, project_rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(proj_dst), exist_ok=True)
            shutil.copy2(os.path.join(self.ws, project_rel.replace('/', os.sep)), proj_dst)

            dest_work_dir = os.path.join(ws2, '.workspace', 'studio', 'works', work_id)
            works_parent = os.path.dirname(dest_work_dir)
            self.assertFalse(os.path.exists(dest_work_dir))

            stderr_buf = io.StringIO()
            with patch('studio_work_backup._find_root', return_value=ws2), \
                 patch('studio_work_backup.os.name', 'posix'), \
                 patch('studio_work_backup._rename_noreplace_linux', return_value=False), \
                 patch('studio_work_backup.os.rename') as mock_rename, \
                 patch('sys.stderr', stderr_buf):
                rc = swb.cmd_restore(_make_args('restore', archive=zip_path, workspace=ws2))

            self.assertEqual(rc, 1, 'Restore deve abortar com codigo != 0')
            mock_rename.assert_not_called()
            self.assertIn('renameat2(RENAME_NOREPLACE)', stderr_buf.getvalue())
            self.assertFalse(os.path.exists(dest_work_dir), 'Destino nao deve ter sido criado')

            staging_leftovers = [
                d for d in os.listdir(works_parent)
                if d.startswith(f'.backup-staging-{work_id}')
            ]
            self.assertEqual(len(staging_leftovers), 0, 'Staging deve ter sido limpo no finally')
        finally:
            shutil.rmtree(render_local.fs_path(ws2, force=True), ignore_errors=True)


class TestRestoreFailureInjection(_WorkspaceTest):
    """Regressao: injeta falha no meio da copia e comprova que nenhum trabalho parcial apareceu."""

    def test_failure_injection_leaves_no_partial_work(self) -> None:
        work_id = 'injecao-falha'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        zip_path = self._zip_path('fail-injection.zip')
        swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))

        ws2 = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws2-fail-')
        try:
            proj_dst = os.path.join(ws2, project_rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(proj_dst), exist_ok=True)
            shutil.copy2(os.path.join(self.ws, project_rel.replace('/', os.sep)), proj_dst)

            pre_work_dir = os.path.join(ws2, '.workspace', 'studio', 'works', 'trabalho-preexistente')
            os.makedirs(pre_work_dir, exist_ok=True)
            pre_work_file = os.path.join(pre_work_dir, 'work.json')
            _write_json(pre_work_file, {'id': 'trabalho-preexistente', 'status': 'ok'})

            dest_work_dir = os.path.join(ws2, '.workspace', 'studio', 'works', work_id)
            works_parent = os.path.dirname(dest_work_dir)

            orig_open = open
            call_count = [0]

            def failing_open(path, mode='r', *args, **kwargs):
                if 'wb' in mode and ('.backup-staging-' in str(path) or '.workspace' in str(path)):
                    call_count[0] += 1
                    if call_count[0] >= 3:
                        raise IOError('Falha simulada de disco no meio da copia')
                return orig_open(path, mode, *args, **kwargs)

            with patch('builtins.open', side_effect=failing_open), patch('studio_work_backup._find_root', return_value=ws2):
                rc = swb.cmd_restore(_make_args('restore', archive=zip_path, workspace=ws2))

            self.assertEqual(rc, 1, 'Restore deve retornar 1 apos erro de copia')
            self.assertFalse(os.path.exists(dest_work_dir), 'Diretorio final nao deve ter sido criado')

            staging_leftovers = [
                d for d in os.listdir(works_parent)
                if d.startswith(f'.backup-staging-{work_id}')
            ]
            self.assertEqual(len(staging_leftovers), 0, 'Staging deve ter sido limpo no finally')

            self.assertTrue(os.path.isfile(pre_work_file))
            with open(pre_work_file, 'r', encoding='utf-8') as fh:
                pre_doc = json.load(fh)
            self.assertEqual(pre_doc['id'], 'trabalho-preexistente')

        finally:
            shutil.rmtree(render_local.fs_path(ws2, force=True), ignore_errors=True)


class TestRestoreTamperedZipFile(_WorkspaceTest):
    """Restore e cancelado se um arquivo do ZIP tiver SHA-256 adulterado."""

    def test_restore_tampered_zip(self) -> None:
        work_id = 'adulterado'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        zip_path = self._zip_path('tampered.zip')
        swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))

        tampered_path = zip_path + '.corrupt.zip'
        with zipfile.ZipFile(zip_path, 'r') as zin, zipfile.ZipFile(tampered_path, 'w') as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.endswith('work.json'):
                    data = b'ADULTERADO_' + data
                zout.writestr(item, data)

        ws2 = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws-tamper-')
        try:
            proj_dst = os.path.join(ws2, project_rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(proj_dst), exist_ok=True)
            shutil.copy2(os.path.join(self.ws, project_rel.replace('/', os.sep)), proj_dst)

            with patch('studio_work_backup._find_root', return_value=ws2):
                rc = swb.cmd_restore(_make_args('restore', archive=tampered_path, workspace=ws2))
            self.assertEqual(rc, 1, 'restore deve falhar com arquivo adulterado')

            dest_work_dir = os.path.join(ws2, '.workspace', 'studio', 'works', work_id)
            self.assertFalse(os.path.exists(dest_work_dir))
        finally:
            shutil.rmtree(render_local.fs_path(ws2, force=True), ignore_errors=True)
            if os.path.exists(tampered_path):
                os.remove(tampered_path)


class TestManifestStructure(_WorkspaceTest):
    """Verifica schemaVersion e campos do manifesto."""

    def test_manifest_fields(self) -> None:
        work_id = 'manifest-test'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        files = swb._collect_work_files(self.ws, work_id)
        manifest = swb._build_manifest(self.ws, work_id, files)

        self.assertEqual(manifest['schemaVersion'], 1)
        self.assertEqual(manifest['workId'], work_id)
        self.assertIn('exportedAt', manifest)
        self.assertIsInstance(manifest['files'], list)
        self.assertGreater(len(manifest['files']), 0)
        dep = manifest['dependencies']['projectManifest']
        self.assertEqual(dep['rel'], project_rel)
        self.assertRegex(dep['sha256'], r'^[0-9a-f]{64}$')


class TestKebabValidation(_WorkspaceTest):
    """Validacao de formato de identificador e trabalho inexistente."""

    def test_invalid_work_id(self) -> None:
        args = _make_args('backup', work_id='INVALIDO_ID', output=os.path.join(self.ws, 'out.zip'))
        rc = swb.cmd_backup(args)
        self.assertEqual(rc, 1)

    def test_nonexistent_work(self) -> None:
        args = _make_args('backup', work_id='nao-existe', output=os.path.join(self.ws, 'out.zip'))
        rc = swb.cmd_backup(args)
        self.assertEqual(rc, 1)


# ---------------------------------------------------------------------------
# Regressoes: Lacunas de validacao compartilhada (MANIFEST, duplicadas, etc.)
# ---------------------------------------------------------------------------

class TestManifestValidationGaps(_WorkspaceTest):
    """Validacao estrita de formato de MANIFEST.json, correspondencia 1:1 e duplicadas."""

    def setUp(self) -> None:
        super().setUp()
        self.work_id = 'val-work'
        self.project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, self.project_rel)
        _make_fake_work(self.ws, self.work_id, self.project_rel)
        self.zip_path = self._zip_path('base-valid.zip')
        rc = swb.cmd_backup(_make_args('backup', work_id=self.work_id, output=self.zip_path))
        self.assertEqual(rc, 0)

    def _tamper_zip(self, mutate_manifest=None, mutate_entries=None) -> str:
        tampered_path = self.zip_path + '.tampered.zip'
        with zipfile.ZipFile(self.zip_path, 'r') as zin, zipfile.ZipFile(tampered_path, 'w') as zout:
            manifest_bytes = zin.read('MANIFEST.json')
            manifest = json.loads(manifest_bytes.decode('utf-8'))
            if mutate_manifest:
                manifest_bytes = mutate_manifest(manifest)
            zout.writestr('MANIFEST.json', manifest_bytes)
            for item in zin.infolist():
                if item.filename == 'MANIFEST.json':
                    continue
                zout.writestr(item, zin.read(item.filename))
            if mutate_entries:
                mutate_entries(zout)
        return tampered_path

    def test_manifest_malformed_json(self) -> None:
        bad_zip = self._tamper_zip(mutate_manifest=lambda m: b'{ "not-valid-json": ')
        rep = swb.validate_backup(bad_zip, self.ws)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any('falha ao decodificar JSON' in e for e in rep.errors))
        rc_insp = swb.cmd_inspect(_make_args('inspect', archive=bad_zip))
        self.assertEqual(rc_insp, 1)
        rc_rest = swb.cmd_restore(_make_args('restore', archive=bad_zip, workspace=self.ws))
        self.assertEqual(rc_rest, 1)

    def test_manifest_non_dict_root(self) -> None:
        bad_zip = self._tamper_zip(mutate_manifest=lambda m: b'["lista", "nao-objeto"]')
        rep = swb.validate_backup(bad_zip, self.ws)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any('raiz deve ser um objeto JSON' in e for e in rep.errors))
        self.assertEqual(swb.cmd_inspect(_make_args('inspect', archive=bad_zip)), 1)
        self.assertEqual(swb.cmd_restore(_make_args('restore', archive=bad_zip, workspace=self.ws)), 1)

    def test_manifest_missing_work_json(self) -> None:
        def drop_work_json(manifest):
            manifest['files'] = [f for f in manifest['files'] if not f['rel'].endswith('work.json')]
            return json.dumps(manifest).encode('utf-8')

        bad_zip = self._tamper_zip(mutate_manifest=drop_work_json)
        rep = swb.validate_backup(bad_zip, self.ws)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any('work.json' in e and 'ausente' in e for e in rep.errors))

    def test_manifest_duplicate_zip_entries(self) -> None:
        # Cria ZIP com entrada duplicada
        dup_zip = self.zip_path + '.dup.zip'
        with zipfile.ZipFile(self.zip_path, 'r') as zin, zipfile.ZipFile(dup_zip, 'w') as zout:
            for item in zin.infolist():
                zout.writestr(item, zin.read(item.filename))
            # Adiciona entrada duplicada
            work_file_rel = f'.workspace/studio/works/{self.work_id}/work.json'
            zout.writestr(work_file_rel, b'{"id":"duplicado"}')

        rep = swb.validate_backup(dup_zip, self.ws)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any('entradas duplicadas no arquivo comprimido' in e for e in rep.errors))
        self.assertEqual(swb.cmd_inspect(_make_args('inspect', archive=dup_zip)), 1)

    def test_manifest_duplicate_files_entries(self) -> None:
        def duplicate_files(manifest):
            if manifest.get('files'):
                manifest['files'].append(manifest['files'][0])
            return json.dumps(manifest).encode('utf-8')

        bad_zip = self._tamper_zip(mutate_manifest=duplicate_files)
        rep = swb.validate_backup(bad_zip, self.ws)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any('entradas duplicadas na lista de arquivos' in e for e in rep.errors))

    def test_manifest_duplicate_shared_media_entries(self) -> None:
        def duplicate_shared_media(manifest):
            sm = {'rel': 'platform/examples/media/dummy.png', 'sha256': 'a' * 64}
            manifest.setdefault('dependencies', {})['sharedMedia'] = [sm, sm]
            return json.dumps(manifest).encode('utf-8')

        bad_zip = self._tamper_zip(mutate_manifest=duplicate_shared_media)
        rep = swb.validate_backup(bad_zip, self.ws)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any('entradas duplicadas em dependencies.sharedMedia' in e for e in rep.errors))

    def test_manifest_declared_file_missing_in_zip(self) -> None:
        def add_phantom_file(manifest):
            manifest['files'].append({
                'rel': f'.workspace/studio/works/{self.work_id}/drafts/phantom.json',
                'size': 10,
                'sha256': 'b' * 64,
            })
            return json.dumps(manifest).encode('utf-8')

        bad_zip = self._tamper_zip(mutate_manifest=add_phantom_file)
        rep = swb.validate_backup(bad_zip, self.ws)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any('declarado no manifesto ausente no ZIP' in e for e in rep.errors))

    def test_manifest_undeclared_file_in_zip(self) -> None:
        def add_zip_entry(zout):
            extra_rel = f'.workspace/studio/works/{self.work_id}/media/unlisted.png'
            zout.writestr(extra_rel, b'\x89PNGunlisted')

        bad_zip = self._tamper_zip(mutate_entries=add_zip_entry)
        rep = swb.validate_backup(bad_zip, self.ws)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any('presente no ZIP nao declarado no manifesto' in e for e in rep.errors))

    def test_invalid_sha_or_negative_size(self) -> None:
        def corrupt_entry_fields(manifest):
            for entry in manifest['files']:
                if entry['rel'].endswith('work.json'):
                    entry['sha256'] = 'invalido-curto'
                    entry['size'] = -10
            return json.dumps(manifest).encode('utf-8')

        bad_zip = self._tamper_zip(mutate_manifest=corrupt_entry_fields)
        rep = swb.validate_backup(bad_zip, self.ws)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any('SHA-256 invalido' in e for e in rep.errors))
        self.assertTrue(any('Tamanho invalido' in e for e in rep.errors))


# ---------------------------------------------------------------------------
# Regressoes: Confinamento de dependencias e validacao de caminhos
# ---------------------------------------------------------------------------

class TestDependencyPathConfinement(_WorkspaceTest):
    """Garante que dependencias com path traversal ou fora do workspace sejam rejeitadas."""

    def setUp(self) -> None:
        super().setUp()
        self.work_id = 'dep-confine-work'
        self.project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, self.project_rel)
        _make_fake_work(self.ws, self.work_id, self.project_rel)
        self.zip_path = self._zip_path('confine-base.zip')
        swb.cmd_backup(_make_args('backup', work_id=self.work_id, output=self.zip_path))

    def _tamper_dependencies(self, mutator) -> str:
        tampered_path = self.zip_path + '.deptamper.zip'
        with zipfile.ZipFile(self.zip_path, 'r') as zin, zipfile.ZipFile(tampered_path, 'w') as zout:
            manifest = json.loads(zin.read('MANIFEST.json').decode('utf-8'))
            mutator(manifest)
            zout.writestr('MANIFEST.json', json.dumps(manifest).encode('utf-8'))
            for item in zin.infolist():
                if item.filename != 'MANIFEST.json':
                    zout.writestr(item, zin.read(item.filename))
        return tampered_path

    def test_dependency_traversal_project_manifest(self) -> None:
        def set_traversal(m):
            m['dependencies']['projectManifest'] = {
                'rel': '../../fora/projeto.json',
                'sha256': 'a' * 64,
            }

        bad_zip = self._tamper_dependencies(set_traversal)
        rep = swb.validate_backup(bad_zip, self.ws)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any('path traversal' in e or 'fora do workspace' in e for e in rep.errors))
        self.assertEqual(swb.cmd_inspect(_make_args('inspect', archive=bad_zip)), 1)
        self.assertEqual(swb.cmd_restore(_make_args('restore', archive=bad_zip, workspace=self.ws)), 1)

    def test_dependency_traversal_shared_media(self) -> None:
        def set_traversal(m):
            m['dependencies']['sharedMedia'] = [
                {'rel': 'platform/../../../evil.png', 'sha256': 'b' * 64}
            ]

        bad_zip = self._tamper_dependencies(set_traversal)
        rep = swb.validate_backup(bad_zip, self.ws)
        self.assertFalse(rep.is_valid)
        self.assertTrue(any('path traversal' in e or 'fora do workspace' in e for e in rep.errors))
        self.assertEqual(swb.cmd_inspect(_make_args('inspect', archive=bad_zip)), 1)

    def test_workspace_outside_root_rejected(self) -> None:
        outside_ws = os.path.abspath(os.path.join(self.ws, '..', '..', '..', 'outro-lugar'))
        # cmd_inspect e cmd_restore devem recusar workspace fora da raiz
        rc_insp = swb.cmd_inspect(_make_args('inspect', archive=self.zip_path, workspace=outside_ws))
        self.assertEqual(rc_insp, 1)
        rc_rest = swb.cmd_restore(_make_args('restore', archive=self.zip_path, workspace=outside_ws))
        self.assertEqual(rc_rest, 1)


# ---------------------------------------------------------------------------
# Regressoes: Dependencias obrigatorias ausentes na origem impedem backup
# ---------------------------------------------------------------------------

class TestMissingSourceDependencyFailsBackup(_WorkspaceTest):
    """Dependencia obrigatoria ausente na origem impede criacao de backup anunciado como integro."""

    def test_missing_project_manifest_fails_backup(self) -> None:
        work_id = 'missing-pm'
        base = os.path.join(self.ws, '.workspace', 'studio', 'works', work_id)
        os.makedirs(base, exist_ok=True)
        # work.json referencia project que nao existe
        _write_json(os.path.join(base, 'work.json'), {
            'id': work_id,
            'project': 'platform/examples/projects/inexistente.project.json',
        })

        zip_out = self._zip_path('should-not-exist.zip')
        rc = swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_out))
        self.assertEqual(rc, 1, 'Backup deve falhar quando ProjectManifest estiver ausente na origem')
        self.assertFalse(os.path.exists(zip_out), 'Arquivo ZIP de saida nao deve ser criado')

    def test_missing_shared_media_fails_backup(self) -> None:
        work_id = 'missing-sm'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)

        # Trabalho referencia midia compartilhada que nao existe em disco
        base = os.path.join(self.ws, '.workspace', 'studio', 'works', work_id)
        drafts = os.path.join(base, 'drafts')
        os.makedirs(drafts, exist_ok=True)
        _write_json(os.path.join(base, 'work.json'), {'id': work_id, 'project': project_rel})
        _write_json(os.path.join(drafts, 'video.request.json'), {
            'schemaVersion': 1,
            'id': f'{work_id}-video',
            'project': project_rel,
            'media': [
                {'id': 'sm-missing', 'path': 'platform/examples/media/ausente.png', 'type': 'image'}
            ],
            'scenes': [],
        })

        zip_out = self._zip_path('sm-missing.zip')
        rc = swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_out))
        self.assertEqual(rc, 1, 'Backup deve falhar quando midia compartilhada estiver ausente na origem')
        self.assertFalse(os.path.exists(zip_out))


# ---------------------------------------------------------------------------
# Regressoes: Preservacao atomica do arquivo de backup anterior
# ---------------------------------------------------------------------------

class TestBackupAtomicOverwrite(_WorkspaceTest):
    """Garante preservacao do ZIP anterior ate a substituicao atomica via os.replace."""

    def test_backup_atomic_overwrite_preserves_old_zip(self) -> None:
        work_id = 'atomic-bkp'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        zip_path = self._zip_path('old-atomic.zip')
        _write_bytes(zip_path, b'conteudo-antigo-intacto-deve-ser-preservado')

        # Injetar falha durante a gravacao do staging
        orig_write = zipfile.ZipFile.write

        def failing_write(*args, **kwargs):
            raise IOError('Falha simulada durante gravacao do ZIP')

        with patch.object(zipfile.ZipFile, 'write', side_effect=failing_write):
            args = _make_args('backup', work_id=work_id, output=zip_path)
            rc = swb.cmd_backup(args)

        self.assertEqual(rc, 1, 'Backup com falha deve retornar 1')
        self.assertTrue(os.path.isfile(zip_path), 'Arquivo anterior deve continuar existindo')
        with open(zip_path, 'rb') as fh:
            self.assertEqual(fh.read(), b'conteudo-antigo-intacto-deve-ser-preservado')

    def test_backup_atomic_overwrite_replaces_on_success(self) -> None:
        work_id = 'atomic-success'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        zip_path = self._zip_path('success-atomic.zip')
        _write_bytes(zip_path, b'conteudo-antigo')

        args = _make_args('backup', work_id=work_id, output=zip_path)
        rc = swb.cmd_backup(args)
        self.assertEqual(rc, 0)
        self.assertTrue(zipfile.is_zipfile(zip_path))
        with open(zip_path, 'rb') as fh:
            self.assertNotEqual(fh.read(), b'conteudo-antigo')


# ---------------------------------------------------------------------------
# Aceite Completo: Dois Workspaces, Contrato Real do Studio e Pre-voo Real
# ---------------------------------------------------------------------------

class TestTwoWorkspaceAcceptanceAndPreflight(_WorkspaceTest):
    """Aceite completo: backup no ws1, restore no ws2, reabertura pelo Studio e comparacao de pre-voo real."""

    def test_full_acceptance_roundtrip_with_preflight(self) -> None:
        worktree = _get_worktree_root()
        main_root = _get_main_root()
        render_local.ensure_video_tools(main_root)

        # Preparar ferramentas em ws1
        _copy_repo_subdirs(worktree, self.ws)

        studio1 = video_studio.Studio(self.ws, port=0, auto_start_queue=False)
        work_id = 'aceite-prod-ready'

        # 1. Montar fixture usando o contrato real do Studio (template marca-salao)
        proj_res = studio1.create_project({
            'schemaVersion': 1,
            'id': f'tp-{work_id}',
            'name': f'Projeto {work_id}',
            'locale': 'pt-BR',
            'timezone': 'America/Sao_Paulo',
            'brandTheme': 'marca-salao',
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
        project_rel = proj_res['path']

        opened = studio1.create_work({
            'id': work_id,
            'name': f'Trabalho {work_id}',
            'project': project_rel,
            'template': 'marca-salao',
        })

        # Criar clipe sintético real com ffmpeg
        work = opened['work']
        clip_rel = f"{work['paths']['mediaDir']}/clip.mp4"
        clip_abs = studio1.confine(clip_rel)

        ffmpeg = build_video.get_ffmpeg()
        cmd = [
            ffmpeg, '-y', '-f', 'lavfi',
            '-i', 'color=c=blue:s=1280x720:r=30:d=2.5',
            '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-an', clip_abs,
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        vreq = json.loads(json.dumps(opened['videoRequest']))
        vreq['media'] = list(vreq.get('media') or []) + [
            {'id': 'clip-1', 'type': 'video', 'path': clip_rel, 'origin': 'synthetic-demo', 'license': 'owned-synthetic'}
        ]
        vreq['scenes'][0]['mediaId'] = 'clip-1'
        vreq['scenes'][0]['sourceStartMs'] = 300
        vreq['scenes'][0]['durationMs'] = 1200
        vreq['profiles'] = ['instagram-reels-video']

        creq = json.loads(json.dumps(opened['carouselRequest']))
        creq['profile'] = 'instagram-feed-image-portrait'

        mplan = json.loads(json.dumps(opened['motionPlan']))
        for eff in mplan.get('effects') or []:
            if eff.get('sceneId') == vreq['scenes'][0]['id']:
                eff['startMs'] = 0
                eff['endMs'] = min(int(eff.get('endMs') or 1000), 1000)

        studio1.save_work({
            'workId': work_id,
            'videoRequest': vreq,
            'carouselRequest': creq,
            'motionPlan': mplan,
        })

        # 2. Executar pre-voo real no workspace 1 (origem)
        preflight_items = [{'workId': work_id, 'modality': 'video', 'profileId': 'instagram-reels-video'}]
        pre1 = studio1.queue.preflight(preflight_items)
        self.assertTrue(pre1['ready'], f"Origem deve estar ready: {pre1}")
        item1 = pre1['items'][0]
        self.assertEqual(item1['status'], 'ready')
        self.assertEqual(len(item1['blockers']), 0, f"Origem nao pode ter bloqueios: {item1['blockers']}")
        warnings1 = [w['code'] for w in item1.get('warnings', [])]

        # Confirmar que a fila na origem nao recebeu novos itens
        q1 = studio1.queue.list_queue()['items']
        self.assertEqual(len(q1), 0, f"Fila na origem deve estar vazia: {q1}")

        opened1 = studio1.open_work(work_id)
        media_hashes1 = {
            m['name']: swb.sha256_file(os.path.join(self.ws, m['path'].replace('/', os.sep)))
            for m in opened1['workMedia']
        }
        self.assertGreater(len(media_hashes1), 0)

        # 3. Gerar backup a partir de ws1
        zip_path = self._zip_path(f'{work_id}.zip')
        args_bkp = argparse.Namespace(command='backup', work_id=work_id, output=zip_path)
        rc_bkp = swb.cmd_backup(args_bkp)
        self.assertEqual(rc_bkp, 0, 'Backup deve retornar 0')

        # 4. Configurar segundo workspace (ws2)
        ws2 = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws2-accept-')
        try:
            _copy_repo_subdirs(worktree, ws2)

            # Copiar ProjectManifest para ws2 (dependencia declarada)
            proj_abs1 = os.path.join(self.ws, project_rel.replace('/', os.sep))
            proj_abs2 = os.path.join(ws2, project_rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(proj_abs2), exist_ok=True)
            shutil.copy2(proj_abs1, proj_abs2)

            # Inspecao em ws2
            with patch('studio_work_backup._find_root', return_value=ws2):
                args_insp = argparse.Namespace(command='inspect', archive=zip_path, workspace=ws2)
                rc_insp = swb.cmd_inspect(args_insp)
                self.assertEqual(rc_insp, 0, 'Inspect deve retornar 0 no ws2')

            # Restauracao em ws2
            with patch('studio_work_backup._find_root', return_value=ws2):
                args_rest = argparse.Namespace(command='restore', archive=zip_path, workspace=ws2)
                rc_rest = swb.cmd_restore(args_rest)
                self.assertEqual(rc_rest, 0, 'Restore deve retornar 0 no ws2')

            # 5. Reabrir no fluxo normal do Studio em ws2
            studio2 = video_studio.Studio(ws2, port=0, auto_start_queue=False)
            try:
                opened2 = studio2.open_work(work_id)
                self.assertEqual(opened2['work']['id'], work_id)
                self.assertEqual(opened2['work']['project'], project_rel)
                self.assertEqual(
                    opened2['videoRequest']['scenes'][0]['title'],
                    opened1['videoRequest']['scenes'][0]['title'],
                )
                self.assertEqual(
                    opened2['carouselRequest']['cards'][0]['title'],
                    opened1['carouselRequest']['cards'][0]['title'],
                )

                # Hashes das midias internas conferem exatamente
                media_hashes2 = {
                    m['name']: swb.sha256_file(os.path.join(ws2, m['path'].replace('/', os.sep)))
                    for m in opened2['workMedia']
                }
                self.assertEqual(media_hashes1, media_hashes2)

                # 6. Executar pre-voo real no Studio2 e comparar
                pre2 = studio2.queue.preflight(preflight_items)
                self.assertTrue(pre2['ready'], f"Destino deve estar ready: {pre2}")
                item2 = pre2['items'][0]
                self.assertEqual(item2['status'], 'ready')
                self.assertEqual(len(item2['blockers']), 0, f"Destino nao pode ter bloqueios: {item2['blockers']}")
                warnings2 = [w['code'] for w in item2.get('warnings', [])]

                # Comparar avisos
                self.assertEqual(warnings1, warnings2, f"Codigos de avisos devem coincidir: {warnings1} != {warnings2}")

                # Confirmar que a fila no destino nao recebeu novos itens
                q2 = studio2.queue.list_queue()['items']
                self.assertEqual(len(q2), 0, f"Fila no destino deve estar vazia: {q2}")

            finally:
                studio2.close()

        finally:
            shutil.rmtree(render_local.fs_path(ws2, force=True), ignore_errors=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
