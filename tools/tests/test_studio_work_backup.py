"""Testes de unidade e integracao para studio_work_backup.

Cobre:
- Validacao compartilhada de integridade e dependencias (inspect e restore)
- ProjectManifest e midias compartilhadas por caminho relativo e SHA-256
- Restricao estrita de entradas aos arquivos permitidos do trabalho indicado
- Exclusao de review-state.json e aprovacoes
- Recusa expressa de diretorio de destino ja existente
- Montagem em staging exclusivo no mesmo sistema de arquivos e promocao atomica
- Regressao com injecao de falha comprovando que nenhum trabalho parcial aparece
- Aceite completo em dois workspaces com reabertura pelo Studio e comparacao de pre-voo

Todos os workspaces de teste ficam sob <RAIZ>/.workspace/tmp/studio-work-backup/tests/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

# Adiciona tools/ ao PYTHONPATH
_TOOLS_DIR = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.abspath(_TOOLS_DIR))

import studio_work_backup as swb  # noqa: E402
import video_studio  # noqa: E402
import studio_queue  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

def _root_tmp() -> str:
    """Raiz para workspaces de teste — fica dentro de <RAIZ>/.workspace/tmp/."""
    here = os.path.dirname(os.path.abspath(__file__))
    raiz = os.path.abspath(os.path.join(here, '..', '..'))
    tmp = os.path.join(raiz, '.workspace', 'tmp', 'studio-work-backup', 'tests')
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
        shutil.rmtree(self.ws, ignore_errors=True)

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
            shutil.rmtree(ws2, ignore_errors=True)


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
            shutil.rmtree(ws2, ignore_errors=True)


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
            shutil.rmtree(ws2, ignore_errors=True)


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
    """Recusa qualquer diretorio de destino ja existente, mesmo que vazio."""

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
            shutil.rmtree(ws2, ignore_errors=True)


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
            shutil.rmtree(ws2, ignore_errors=True)


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
            shutil.rmtree(ws2, ignore_errors=True)
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


class TestTwoWorkspaceAcceptanceAndPreflight(_WorkspaceTest):
    """Aceite completo: backup no ws1, restore no ws2, reabertura pelo Studio e comparacao de pre-voo."""

    def test_full_acceptance_roundtrip_with_preflight(self) -> None:
        work_id = 'aceite-preflight'
        project_rel = 'platform/examples/projects/test.project.json'
        shared_rel = 'platform/examples/media/shared-logo.png'

        _make_fake_project(self.ws, project_rel)
        shared_abs1 = os.path.join(self.ws, shared_rel.replace('/', os.sep))
        _write_bytes(shared_abs1, b'\x89PNG\r\n\x1a\n' + b'shared-logo-bytes' * 25)

        _make_fake_work(self.ws, work_id, project_rel, shared_media_rel=shared_rel)

        fake_profiles = {
            'catalogVersion': '1',
            'profiles': [
                {'id': 'instagram-reels-video', 'name': 'Reels', 'compatibleModules': ['video']},
                {'id': 'instagram-feed-image-square', 'name': 'Square', 'compatibleModules': ['carousel']},
            ],
        }

        # 1. Abrir no Studio da origem (ws1) e executar pre-voo
        with patch.object(video_studio.Studio, 'list_profiles', return_value=fake_profiles):
            studio1 = video_studio.Studio(self.ws, port=0, auto_start_queue=False)
            try:
                opened_ws1 = studio1.open_work(work_id)
                self.assertEqual(opened_ws1['work']['id'], work_id)
                preflight_items = [{'workId': work_id, 'modality': 'video', 'profileId': 'instagram-reels-video'}]
                preflight_ws1 = studio1.queue.preflight(preflight_items)
                self.assertIn('ready', preflight_ws1)
                self.assertEqual(len(preflight_ws1['items']), 1)
            finally:
                studio1.close()

            # 2. Gerar backup a partir de ws1
            zip_path = self._zip_path('aceite-preflight.zip')
            rc_bkp = swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))
            self.assertEqual(rc_bkp, 0)

            # 3. Preparar segundo workspace (ws2) com dependencias
            ws2 = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws2-accept-')
            try:
                proj_abs2 = os.path.join(ws2, project_rel.replace('/', os.sep))
                os.makedirs(os.path.dirname(proj_abs2), exist_ok=True)
                shutil.copy2(os.path.join(self.ws, project_rel.replace('/', os.sep)), proj_abs2)

                shared_abs2 = os.path.join(ws2, shared_rel.replace('/', os.sep))
                os.makedirs(os.path.dirname(shared_abs2), exist_ok=True)
                shutil.copy2(shared_abs1, shared_abs2)

                # Inspecao no ws2 deve validar tudo como OK
                with patch('studio_work_backup._find_root', return_value=ws2):
                    rc_insp = swb.cmd_inspect(_make_args('inspect', archive=zip_path, workspace=ws2))
                self.assertEqual(rc_insp, 0)

                # Restauracao no ws2
                with patch('studio_work_backup._find_root', return_value=ws2):
                    rc_rest = swb.cmd_restore(_make_args('restore', archive=zip_path, workspace=ws2))
                self.assertEqual(rc_rest, 0)

                # 4. Reabrir no fluxo normal do Studio no ws2
                studio2 = video_studio.Studio(ws2, port=0, auto_start_queue=False)
                try:
                    opened_ws2 = studio2.open_work(work_id)

                    # Conferir integridade dos campos
                    self.assertEqual(opened_ws2['work']['id'], work_id)
                    self.assertEqual(opened_ws2['work']['project'], project_rel)
                    self.assertEqual(
                        opened_ws2['videoRequest']['scenes'][0]['title'],
                        opened_ws1['videoRequest']['scenes'][0]['title'],
                    )
                    self.assertEqual(
                        opened_ws2['carouselRequest']['cards'][0]['title'],
                        opened_ws1['carouselRequest']['cards'][0]['title'],
                    )
                    self.assertEqual(
                        opened_ws2['review']['editorial']['briefingSha256'],
                        opened_ws1['review']['editorial']['briefingSha256'],
                    )

                    # Hashes das midias internas conferem
                    self.assertEqual(len(opened_ws1['workMedia']), len(opened_ws2['workMedia']))
                    for m1, m2 in zip(opened_ws1['workMedia'], opened_ws2['workMedia']):
                        self.assertEqual(m1['name'], m2['name'])
                        self.assertEqual(m1['bytes'], m2['bytes'])

                    # 5. Executar pre-voo no Studio2 e comparar com ws1
                    preflight_ws2 = studio2.queue.preflight(preflight_items)

                    # Comparar resultado do pre-voo
                    self.assertEqual(preflight_ws1['ready'], preflight_ws2['ready'])
                    self.assertEqual(preflight_ws1['schemaVersion'], preflight_ws2['schemaVersion'])
                    item1 = preflight_ws1['items'][0]
                    item2 = preflight_ws2['items'][0]
                    self.assertEqual(item1['status'], item2['status'])
                    self.assertEqual(item1['modality'], item2['modality'])
                    self.assertEqual(item1['profileId'], item2['profileId'])
                    self.assertEqual(len(item1.get('blockers', [])), len(item2.get('blockers', [])))
                    self.assertEqual(len(item1.get('warnings', [])), len(item2.get('warnings', [])))

                finally:
                    studio2.close()

            finally:
                shutil.rmtree(ws2, ignore_errors=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
