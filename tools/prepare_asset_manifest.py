"""Monta um AssetManifest v1 a partir de um caso e uma associacao de assets.

Uso:
  python tools/prepare_asset_manifest.py --case <caso.pipeline.json> \
      --assets <associacao.json> --origin <origem> --output <inventario.json> \
      [--license <licenca>] [--root <raiz>] [--json]

Responsabilidades:
- Valida o caso e a associacao pelo nucleo da platform via tools/render_bridge.mjs;
- Verifica contencao real na raiz, existencia e leitura de cada arquivo de midia;
- Deduplica arquivos fisicos repetidos em uma unica entrada em `assets`;
- Calcula tamanho em bytes, SHA-256 em hexadecimal minusculo e tipo (image/video);
- Usa a licenca informada ou `pending` por padrao quando `--license` for omitido;
- Valida e serializa canonicamente o inventario resultante sem alterar midias ou
  arquivos de origem.

Exit codes: 0 sucesso; 1 erro de midia/escrita; 2 uso ou caminho fora da raiz;
3 falha de contrato do caso, pacote, associacao ou inventario.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import render_local

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp')
VIDEO_EXTENSIONS = ('.mp4', '.mov')
BRIDGE_ASSET_MANIFEST_MODULE = ('platform', 'dist', 'src', 'validate-asset-manifest.js')


def has_control_char(text: str) -> bool:
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in text)


def infer_media_type(asset_path: str) -> str:
    lower = asset_path.lower()
    if any(lower.endswith(ext) for ext in IMAGE_EXTENSIONS):
        return 'image'
    if any(lower.endswith(ext) for ext in VIDEO_EXTENSIONS):
        return 'video'
    raise render_local.RenderInputError('ASSET_EXTENSION_UNSUPPORTED', asset_path)


def make_unique_asset_id(rel_path: str, used_ids: set[str]) -> str:
    stem = os.path.splitext(os.path.basename(rel_path))[0].lower()
    slug = re.sub(r'[^a-z0-9]+', '-', stem).strip('-')
    if not slug:
        slug = 'media'
    base_id = f'asset-{slug}'
    candidate = base_id
    suffix = 2
    while candidate in used_ids:
        candidate = f'{base_id}-{suffix}'
        suffix += 1
    used_ids.add(candidate)
    return candidate


def run_bridge_prepare(root_real: str, case_abs: str, assets_abs: str | None = None,
                       asset_manifest_abs: str | None = None, plan_only: bool = False) -> dict:
    node = shutil.which('node')
    if not node:
        raise render_local.InputFileError('node nao encontrado no PATH')
    dist_module = os.path.join(root_real, *BRIDGE_ASSET_MANIFEST_MODULE)
    if not os.path.isfile(dist_module):
        raise render_local.InputFileError('build da platform ausente; execute npm run build em platform/')
    bridge = os.path.join(root_real, 'tools', 'render_bridge.mjs')
    cmd = [node, bridge, '--case', case_abs, '--root', root_real]
    if plan_only:
        cmd.append('--plan-only')
    if assets_abs:
        cmd.extend(['--assets', assets_abs])
    if asset_manifest_abs:
        cmd.extend(['--asset-manifest', asset_manifest_abs])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=render_local.BRIDGE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise build_video.DeliveryError('ponte de validacao excedeu o tempo limite')
    if res.returncode == 2:
        raise render_local.InputFileError('arquivo de entrada ilegivel ou JSON invalido')
    if res.returncode not in (0, 3):
        raise build_video.DeliveryError('ponte de validacao falhou de forma inesperada')
    try:
        verdict = json.loads(res.stdout)
    except ValueError:
        raise build_video.DeliveryError('veredito da ponte ilegivel')
    if not verdict.get('ok'):
        code = verdict.get('failureCode') or 'VALIDATION_FAILED'
        subject = verdict.get('subject')
        raise render_local.RenderInputError(code, subject)
    return verdict


def build_asset_manifest(root_real: str, case_abs: str, assets_abs: str,
                         origin: str, license_value: str) -> tuple[dict, str]:
    verdict = run_bridge_prepare(root_real, case_abs, assets_abs=assets_abs, plan_only=False)
    case_id = verdict['caseId']
    package_id = verdict['packageId']
    association = verdict['association']

    assets_by_real: dict[str, dict] = {}
    used_ids: set[str] = set()
    assets_list: list[dict] = []
    bindings_list: list[dict] = []

    for binding in association['assets']:
        beat_id = binding['beatId']
        declared_rel = binding['path']
        joined = os.path.join(root_real, declared_rel.replace('/', os.sep))
        real_path = os.path.realpath(joined)
        if not render_local.contained(root_real, real_path):
            raise render_local.InputFileError(f'asset fora da raiz do projeto: {declared_rel}')
        if not os.path.isfile(real_path):
            raise build_video.DeliveryError(f'asset nao encontrado: {declared_rel}')
        try:
            with open(real_path, 'rb') as check_handle:
                check_handle.read(1)
        except OSError:
            raise build_video.DeliveryError(f'asset ilegivel: {declared_rel}')

        if real_path in assets_by_real:
            asset_entry = assets_by_real[real_path]
        else:
            canonical_rel = render_local.rel(root_real, real_path)
            media_type = infer_media_type(canonical_rel)
            size_bytes = os.path.getsize(real_path)
            if size_bytes < 1:
                raise build_video.DeliveryError(f'asset vazio (0 bytes): {canonical_rel}')
            sha256_hex = render_local.sha256_file(real_path)
            asset_id = make_unique_asset_id(canonical_rel, used_ids)
            asset_entry = {
                'id': asset_id,
                'type': media_type,
                'path': canonical_rel,
                'bytes': size_bytes,
                'sha256': sha256_hex,
                'origin': origin,
                'license': license_value,
            }
            assets_by_real[real_path] = asset_entry
            assets_list.append(asset_entry)

        bindings_list.append({
            'beatId': beat_id,
            'assetId': asset_entry['id'],
        })

    manifest_candidate = {
        'schemaVersion': 1,
        'caseId': case_id,
        'packageId': package_id,
        'assets': assets_list,
        'bindings': bindings_list,
    }

    tmp_dir = os.path.join(root_real, '.workspace', 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)
    fd, tmp_manifest_path = tempfile.mkstemp(prefix='prepare-manifest-', suffix='.json', dir=tmp_dir)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(manifest_candidate, ensure_ascii=False, indent=2) + '\n')
        validated = run_bridge_prepare(
            root_real,
            case_abs,
            asset_manifest_abs=tmp_manifest_path,
            plan_only=True,
        )
    finally:
        if os.path.exists(tmp_manifest_path):
            os.remove(tmp_manifest_path)

    canonical_json = validated['canonicalAssetManifestJson']
    canonical_manifest = validated['assetManifest']
    return canonical_manifest, canonical_json


def prepare_manifest(case_path: str, assets_path: str, origin: str, output_path: str,
                     root: str, license_value: str | None = None) -> dict:
    root_real = os.path.realpath(root)
    if not os.path.isdir(root_real):
        raise render_local.InputFileError('raiz do projeto invalida')

    clean_origin = (origin or '').strip()
    if not clean_origin or has_control_char(clean_origin):
        raise render_local.InputFileError('--origin deve ser uma string nao vazia sem caracteres de controle')

    clean_license = (license_value if license_value is not None else 'pending').strip()
    if not clean_license or has_control_char(clean_license):
        raise render_local.InputFileError('--license deve ser uma string nao vazia sem caracteres de controle')

    case_abs = os.path.realpath(case_path)
    assets_abs = os.path.realpath(assets_path)
    output_abs = os.path.realpath(output_path)

    for label, path in (('case', case_abs), ('assets', assets_abs), ('output', output_abs)):
        if not render_local.contained(root_real, path):
            raise render_local.InputFileError(f'caminho {label} fora da raiz do projeto')

    if not os.path.isfile(case_abs):
        raise render_local.InputFileError(f'arquivo de caso ausente: {case_path}')
    if not os.path.isfile(assets_abs):
        raise render_local.InputFileError(f'arquivo de associacao ausente: {assets_path}')
    if os.path.isdir(output_abs):
        raise render_local.InputFileError(f'caminho de saida e um diretorio: {output_path}')
    if output_abs in (case_abs, assets_abs):
        raise render_local.InputFileError('arquivo de saida nao pode sobrescrever entrada')

    canonical_manifest, canonical_json = build_asset_manifest(
        root_real, case_abs, assets_abs, clean_origin, clean_license
    )

    output_parent = os.path.dirname(output_abs)
    os.makedirs(output_parent, exist_ok=True)
    fd, tmp_out = tempfile.mkstemp(prefix='.asset-manifest-', suffix='.tmp', dir=output_parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(canonical_json)
        os.replace(tmp_out, output_abs)
    except OSError as exc:
        if os.path.exists(tmp_out):
            os.remove(tmp_out)
        raise build_video.DeliveryError(f'falha ao gravar inventario: {exc}')

    asset_count = len(canonical_manifest['assets'])
    binding_count = len(canonical_manifest['bindings'])
    return {
        'ok': True,
        'caseId': canonical_manifest['caseId'],
        'packageId': canonical_manifest['packageId'],
        'output': render_local.rel(root_real, output_abs),
        'assetCount': asset_count,
        'bindingCount': binding_count,
        'deduplicatedCount': max(0, binding_count - asset_count),
        'manifest': canonical_manifest,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description='Monta AssetManifest v1 a partir de caso e associacao de assets')
    parser.add_argument('--case', required=True, help='Manifesto do caso (*.pipeline.json)')
    parser.add_argument('--assets', required=True, help='Associacao existente de assets (*.assets.json)')
    parser.add_argument('--origin', required=True, help='Origem declarada dos materiais')
    parser.add_argument('--output', required=True, help='Caminho de saida do inventario JSON')
    parser.add_argument('--license', default=None, help='Licenca declarada (padrao: pending)')
    parser.add_argument('--root', default=os.getcwd(), help='Raiz do projeto')
    parser.add_argument('--json', action='store_true', help='Emite resumo estruturado em JSON no stdout')
    args = parser.parse_args(argv)

    try:
        summary = prepare_manifest(
            case_path=args.case,
            assets_path=args.assets,
            origin=args.origin,
            output_path=args.output,
            root=args.root,
            license_value=args.license,
        )
    except render_local.RenderInputError as exc:
        detail = f'{exc.code}: {exc.subject}' if exc.subject else exc.code
        print(f'Erro: {detail}', file=sys.stderr)
        return 3
    except render_local.InputFileError as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 2
    except build_video.DeliveryError as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f'Erro: entrada invalida ({type(exc).__name__})', file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"Inventario gerado: {summary['output']} "
            f"({summary['assetCount']} assets, {summary['bindingCount']} vinculos)"
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
