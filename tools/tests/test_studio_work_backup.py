"""Testes de unidade e integração para studio_work_backup.

Todos os workspaces de teste ficam sob <RAIZ>/.workspace/tmp/studio-work-backup/tests/,
em conformidade com o AGENTS.md.

Execute:
  cd <RAIZ>
  python -m pytest tools/tests/test_studio_work_backup.py -v
  # ou
  python -m unittest tools/tests/test_studio_work_backup.py -v
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

# Adiciona tools/ ao PYTHONPATH para importar o módulo sem instalar
_TOOLS_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.abspath(_TOOLS_DIR) + '/tools')

import studio_work_backup as swb  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

def _root_tmp() -> str:
    """Raiz para workspaces de teste — fica dentro de <RAIZ>/.workspace/tmp/."""
    # __file__ é tools/tests/test_studio_work_backup.py
    # Subimos 3 níveis para chegar à RAIZ
    here = os.path.dirname(os.path.abspath(__file__))
    raiz = os.path.abspath(os.path.join(here, '..', '..'))
    tmp = os.path.join(raiz, '.workspace', 'tmp', 'studio-work-backup', 'tests')
    os.makedirs(tmp, exist_ok=True)
    return tmp


def _make_fake_work(root: str, work_id: str, project_rel: str = 'platform/examples/projects/test.project.json') -> dict:
    """Cria uma estrutura de trabalho fictícia dentro de root."""
    base = os.path.join(root, '.workspace', 'studio', 'works', work_id)
    drafts = os.path.join(base, 'drafts')
    media = os.path.join(base, 'media')
    for d in (base, drafts, media):
        os.makedirs(d, exist_ok=True)

    work_doc = {
        'id': work_id,
        'name': f'Trabalho {work_id}',
        'project': project_rel,
        'title': f'Título {work_id}',
    }
    _write_json(os.path.join(base, 'work.json'), work_doc)
    _write_json(os.path.join(base, 'editorial.json'), {
        'titulo': 'Arte Exemplo',
        'channels': {'fb': {'texto': 'Legenda Facebook'}},
    })
    _write_json(os.path.join(base, 'review-state.json'), {'channels': {}})
    _write_json(os.path.join(base, 'planning.json'), {'etapas': []})
    _write_json(os.path.join(base, 'media-library.json'), {'items': []})
    _write_json(os.path.join(drafts, 'video.request.json'), {
        'id': f'{work_id}-video', 'scenes': [{'titulo': 'Abertura', 'texto': 'Texto 1'}],
    })
    _write_json(os.path.join(drafts, 'carousel.request.json'), {
        'id': f'{work_id}-carrossel', 'cards': [{'titulo': 'Card 1'}],
    })
    _write_json(os.path.join(drafts, 'motion.plan.json'), {
        'id': f'{work_id}-motion', 'effects': [],
    })
    # Arquivo de mídia fictício
    img_path = os.path.join(media, 'imagem01.png')
    img_path2 = os.path.join(media, 'fundo.jpg')
    _write_bytes(img_path, b'\x89PNG\r\n\x1a\n' + b'fake-image-data' * 100)
    _write_bytes(img_path2, b'\xff\xd8\xff' + b'fake-jpg-data' * 50)
    return {'base': base, 'work': work_doc}


def _make_fake_project(root: str, project_rel: str) -> str:
    """Cria um ProjectManifest fictício."""
    abs_path = os.path.join(root, project_rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    _write_json(abs_path, {
        'id': 'test-project',
        'name': 'Projeto de Teste',
        'profiles': [],
    })
    return abs_path


def _write_json(path: str, data: dict) -> None:
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False)


def _write_bytes(path: str, data: bytes) -> None:
    with open(path, 'wb') as fh:
        fh.write(data)


def _sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Patch de _find_root para apontar para o workspace de teste
# ---------------------------------------------------------------------------

class _WorkspaceTest(unittest.TestCase):
    """Base que cria e limpa um workspace de teste isolado."""

    def setUp(self) -> None:
        self.base_tmp = _root_tmp()
        self.ws = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws-')
        # Patchamos _find_root para retornar nosso workspace de teste
        self._patcher = patch('studio_work_backup._find_root', return_value=self.ws)
        self._patcher.start()

    def tearDown(self) -> None:
        self._patcher.stop()
        shutil.rmtree(self.ws, ignore_errors=True)

    def _zip_path(self, name: str = 'backup.zip') -> str:
        return os.path.join(self.ws, '.workspace', 'tmp', name)

    def _ensure_zip_dir(self) -> None:
        os.makedirs(os.path.join(self.ws, '.workspace', 'tmp'), exist_ok=True)


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

class TestBackupRoundTrip(_WorkspaceTest):
    """Backup + restore produz arquivos idênticos."""

    def test_backup_restore_hashes_match(self) -> None:
        work_id = 'meu-trabalho'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        self._ensure_zip_dir()
        zip_path = self._zip_path()

        # Backup
        args_backup = _make_args('backup', work_id=work_id, output=zip_path)
        rc = swb.cmd_backup(args_backup)
        self.assertEqual(rc, 0, 'backup deve retornar 0')
        self.assertTrue(os.path.isfile(zip_path), 'ZIP deve existir')

        # Restaurar num segundo workspace
        ws2 = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws2-')
        try:
            # Copiar o project manifest para o ws2 (dependência)
            proj_abs2 = os.path.join(ws2, project_rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(proj_abs2), exist_ok=True)
            shutil.copy2(os.path.join(self.ws, project_rel.replace('/', os.sep)), proj_abs2)

            args_restore = _make_args('restore', archive=zip_path, workspace=ws2)
            with patch('studio_work_backup._find_root', return_value=ws2):
                rc = swb.cmd_restore(args_restore)
            self.assertEqual(rc, 0, 'restore deve retornar 0')

            # Comparar hashes de todos os arquivos restaurados
            orig_files = swb._collect_work_files(self.ws, work_id)
            for rel, orig_abs in orig_files:
                restored_abs = os.path.join(ws2, rel.replace('/', os.sep))
                self.assertTrue(os.path.isfile(restored_abs), f'Arquivo restaurado deve existir: {rel}')
                self.assertEqual(
                    swb.sha256_file(orig_abs),
                    swb.sha256_file(restored_abs),
                    f'Hash deve coincidir: {rel}',
                )
        finally:
            shutil.rmtree(ws2, ignore_errors=True)


class TestInspectOk(_WorkspaceTest):
    """inspect retorna 0 quando o backup está integro e as dependências existem."""

    def test_inspect_ok(self) -> None:
        work_id = 'insp-ok'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        self._ensure_zip_dir()
        zip_path = self._zip_path('inspect-ok.zip')
        rc = swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))
        self.assertEqual(rc, 0)

        rc = swb.cmd_inspect(_make_args('inspect', archive=zip_path))
        self.assertEqual(rc, 0, 'inspect deve ser OK')


class TestInspectMissingDependency(_WorkspaceTest):
    """inspect retorna 1 quando o ProjectManifest está ausente no destino."""

    def test_inspect_missing_project_manifest(self) -> None:
        work_id = 'insp-missing'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        self._ensure_zip_dir()
        zip_path = self._zip_path('inspect-missing.zip')
        rc = swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))
        self.assertEqual(rc, 0)

        # Remover o ProjectManifest
        proj_abs = os.path.join(self.ws, project_rel.replace('/', os.sep))
        os.remove(proj_abs)

        rc = swb.cmd_inspect(_make_args('inspect', archive=zip_path))
        self.assertEqual(rc, 1, 'inspect deve falhar com dependência ausente')


class TestInspectHashMismatchDependency(_WorkspaceTest):
    """inspect retorna 1 quando o ProjectManifest tem SHA-256 diferente."""

    def test_inspect_hash_mismatch(self) -> None:
        work_id = 'insp-mismatch'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        self._ensure_zip_dir()
        zip_path = self._zip_path('inspect-mismatch.zip')
        rc = swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))
        self.assertEqual(rc, 0)

        # Modificar o ProjectManifest no destino
        proj_abs = os.path.join(self.ws, project_rel.replace('/', os.sep))
        _write_json(proj_abs, {'id': 'modificado', 'name': 'Alterado'})

        rc = swb.cmd_inspect(_make_args('inspect', archive=zip_path))
        self.assertEqual(rc, 1, 'inspect deve falhar com hash divergente')


class TestRestoreAlreadyExists(_WorkspaceTest):
    """restore é bloqueado se o trabalho já existe no destino."""

    def test_restore_blocked_when_work_exists(self) -> None:
        work_id = 'existe-ja'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        self._ensure_zip_dir()
        zip_path = self._zip_path('restore-exists.zip')
        rc = swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))
        self.assertEqual(rc, 0)

        # Tentar restaurar no mesmo workspace (trabalho já existe)
        args_restore = _make_args('restore', archive=zip_path, workspace=self.ws)
        rc = swb.cmd_restore(args_restore)
        self.assertEqual(rc, 1, 'restore deve ser bloqueado')


class TestRestoreTamperedFile(_WorkspaceTest):
    """restore é cancelado se um arquivo do ZIP tem SHA-256 errado."""

    def test_restore_tampered_zip(self) -> None:
        work_id = 'adulterado'
        project_rel = 'platform/examples/projects/test.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        self._ensure_zip_dir()
        zip_path = self._zip_path('tampered.zip')
        rc = swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))
        self.assertEqual(rc, 0)

        # Adulterar um arquivo dentro do ZIP
        tampered_path = zip_path + '.tampered.zip'
        _tamper_zip_file(zip_path, tampered_path, '.workspace/studio/works/adulterado/work.json')

        ws2 = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws-restore-tamper-')
        try:
            proj_abs2 = os.path.join(ws2, project_rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(proj_abs2), exist_ok=True)
            shutil.copy2(os.path.join(self.ws, project_rel.replace('/', os.sep)), proj_abs2)

            args_restore = _make_args('restore', archive=tampered_path, workspace=ws2)
            with patch('studio_work_backup._find_root', return_value=ws2):
                rc = swb.cmd_restore(args_restore)
            self.assertEqual(rc, 1, 'restore deve falhar com arquivo adulterado')

            # Trabalho NÃO deve ter sido criado parcialmente
            dest_work_file = os.path.join(ws2, '.workspace', 'studio', 'works', work_id, 'work.json')
            self.assertFalse(os.path.exists(dest_work_file), 'Trabalho nao deve existir apos falha')
        finally:
            shutil.rmtree(ws2, ignore_errors=True)
            if os.path.exists(tampered_path):
                os.remove(tampered_path)


class TestTwoWorkspaceRoundTrip(_WorkspaceTest):
    """Fluxo completo: backup no ws1, restore no ws2, verificar conteúdo."""

    def test_full_roundtrip(self) -> None:
        work_id = 'roundtrip-work'
        project_rel = 'platform/examples/projects/marcasalao-social.project.json'
        _make_fake_project(self.ws, project_rel)
        _make_fake_work(self.ws, work_id, project_rel)

        self._ensure_zip_dir()
        zip_path = self._zip_path('roundtrip.zip')

        # --- Backup no ws1 ---
        rc = swb.cmd_backup(_make_args('backup', work_id=work_id, output=zip_path))
        self.assertEqual(rc, 0)

        # --- Inspect ---
        rc = swb.cmd_inspect(_make_args('inspect', archive=zip_path))
        self.assertEqual(rc, 0)

        # --- Restore no ws2 ---
        ws2 = tempfile.mkdtemp(dir=self.base_tmp, prefix='ws2-roundtrip-')
        try:
            proj_abs2 = os.path.join(ws2, project_rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(proj_abs2), exist_ok=True)
            shutil.copy2(os.path.join(self.ws, project_rel.replace('/', os.sep)), proj_abs2)

            args_restore = _make_args('restore', archive=zip_path, workspace=ws2)
            with patch('studio_work_backup._find_root', return_value=ws2):
                rc = swb.cmd_restore(args_restore)
            self.assertEqual(rc, 0)

            # Verificar work.json restaurado
            work_file = os.path.join(ws2, '.workspace', 'studio', 'works', work_id, 'work.json')
            self.assertTrue(os.path.isfile(work_file))
            with open(work_file, encoding='utf-8') as fh:
                restored_work = json.load(fh)
            self.assertEqual(restored_work['id'], work_id)
            self.assertEqual(restored_work['project'], project_rel)

            # Verificar editorial
            editorial_file = os.path.join(
                ws2, '.workspace', 'studio', 'works', work_id, 'editorial.json'
            )
            self.assertTrue(os.path.isfile(editorial_file))
            with open(editorial_file, encoding='utf-8') as fh:
                editorial = json.load(fh)
            self.assertEqual(editorial['channels']['fb']['texto'], 'Legenda Facebook')

            # Verificar draft de vídeo
            video_draft = os.path.join(
                ws2, '.workspace', 'studio', 'works', work_id, 'drafts', 'video.request.json'
            )
            self.assertTrue(os.path.isfile(video_draft))
            with open(video_draft, encoding='utf-8') as fh:
                vdraft = json.load(fh)
            self.assertEqual(vdraft['scenes'][0]['texto'], 'Texto 1')

            # Verificar hashes das mídias
            orig_files = swb._collect_work_files(self.ws, work_id)
            for rel, orig_abs in orig_files:
                restored_abs = os.path.join(ws2, rel.replace('/', os.sep))
                self.assertTrue(os.path.isfile(restored_abs), f'Deve existir: {rel}')
                self.assertEqual(
                    swb.sha256_file(orig_abs),
                    swb.sha256_file(restored_abs),
                    f'Hash deve coincidir: {rel}',
                )

        finally:
            shutil.rmtree(ws2, ignore_errors=True)


class TestManifestStructure(_WorkspaceTest):
    """Verifica estrutura do manifesto gerado."""

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

        for entry in manifest['files']:
            self.assertIn('rel', entry)
            self.assertIn('size', entry)
            self.assertRegex(entry['sha256'], r'^[0-9a-f]{64}$')
            self.assertGreaterEqual(entry['size'], 0)


class TestKebabValidation(_WorkspaceTest):
    """backup falha com work_id inválido."""

    def test_invalid_work_id(self) -> None:
        args = _make_args('backup', work_id='INVALIDO_ID', output=os.path.join(self.ws, 'out.zip'))
        rc = swb.cmd_backup(args)
        self.assertEqual(rc, 1)

    def test_nonexistent_work(self) -> None:
        self._ensure_zip_dir()
        args = _make_args('backup', work_id='nao-existe', output=self._zip_path())
        rc = swb.cmd_backup(args)
        self.assertEqual(rc, 1)


# ---------------------------------------------------------------------------
# Utilitários para testes
# ---------------------------------------------------------------------------

def _make_args(command: str, **kwargs):
    """Cria um namespace de args simulado."""
    import argparse
    ns = argparse.Namespace(command=command, workspace=None)
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def _tamper_zip_file(src_zip: str, dst_zip: str, target_entry: str) -> None:
    """Copia src_zip para dst_zip adulterando o conteúdo de target_entry."""
    with zipfile.ZipFile(src_zip, 'r') as zin, zipfile.ZipFile(dst_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == target_entry:
                data = b'ADULTERADO_' + data
            zout.writestr(item, data)


if __name__ == '__main__':
    unittest.main(verbosity=2)
