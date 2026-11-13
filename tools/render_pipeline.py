"""Pipeline local de renderizacao do CreativeExecutionPackage a partir de casos.

Suporta tres operacoes principais:
1. Previa do plano (sem render, sem FFmpeg, sem leitura de midias, sem pasta de entrega):
   python tools/render_pipeline.py --case <caso.pipeline.json> --plan-only [--asset-manifest <inventario.json>] --json

2. Verificacao de midias declaradas (contencao, bytes, SHA-256 e FFprobe, sem pasta de entrega):
   python tools/render_pipeline.py --case <caso.pipeline.json> --asset-manifest <inventario.json> --check-assets --json

3. Renderizacao e entrega rastreavel:
   python tools/render_pipeline.py --case <caso.pipeline.json> (--assets <associacao.json> | --asset-manifest <inventario.json>) --output-dir <destino> --json

Contratos e responsabilidades:
- Caso para pacote: carrega os 4 documentos referenciados, valida via pipeline consolidado,
  gera CreativeExecutionPackage e serializacao canonica atraves da ponte Node com a platform.
- Previa: devolve caseId, packageId, perfil, geometria, FPS, duracao, beatIds necessarios,
  e indica se cabe no recorte atual do adaptador; com --asset-manifest valida tambem as
  referencias e exibe os vinculos declarados.
- Verificacao (--check-assets): verifica existencia, contencao na raiz, tamanho, SHA-256 e
  inspecao FFprobe de cada asset unico uma unica vez, alem da duracao de clipes de video.
- Render: valida associacao ou inventario (copiando os bytes verificados para staging),
  executa video sem audio (MP4 H.264/yuv420p 9:16 a 30 fps), com legenda queimada,
  SRT separado e roteiro de narracao em TXT.
- Entrega rastreavel: promove em transacao pacote canonico, MP4, SRT, TXT, inventario canonico
  (quando usado), relatorio de render e manifesto JSON versionado (delivery-manifest.json).
- Falha e reexecucao: staging exclusivo, lock por destino, promocao com backup e restauracao.
  Rejeita colisao com entrega de outro caso. Se a restauracao falhar, preserva backup.
- Em --json: stdout reservado exclusivamente ao JSON; erros sanitizados em stderr.

Exit codes: 0 sucesso; 1 falha de render/inspecao/promocao/asset/colisao;
2 uso, caminho fora da raiz ou JSON/arquivo ausente; 3 caso, pacote, associacao, inventario ou recorte invalidos.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import r002_pilot
import render_local
import srt_validate

ADAPTER_ID = 'local-pipeline-render'


class DeliveryCollisionError(build_video.DeliveryError):
    """Colisao com entrega de outro caso no destino."""


def contained(root, path):
    return render_local.contained(root, path)


def sha256_file(path):
    return render_local.sha256_file(path)


def rel(root, path):
    return render_local.rel(root, path)


def overlaps(a, b):
    return render_local.overlaps(a, b)


def write_text(path, text):
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)


def run_bridge_case(root, case_path, assets_path=None, asset_manifest_path=None,
                    text_overlays_path=None, visual_style_path=None, plan_only=False):
    node = shutil.which('node')
    if not node:
        raise render_local.InputFileError('node nao encontrado no PATH')
    dist_module = os.path.join(root, 'platform', 'dist', 'src', 'validate-local-render-input.js')
    if not os.path.isfile(dist_module):
        raise render_local.InputFileError('build da platform ausente; execute npm run build em platform/')
    bridge = os.path.join(root, 'tools', 'render_bridge.mjs')
    cmd = [node, bridge, '--case', case_path, '--root', root]
    if plan_only:
        cmd.append('--plan-only')
    if assets_path:
        cmd.extend(['--assets', assets_path])
    if asset_manifest_path:
        cmd.extend(['--asset-manifest', asset_manifest_path])
    if text_overlays_path:
        cmd.extend(['--text-overlays', text_overlays_path])
    if visual_style_path:
        cmd.extend(['--visual-style', visual_style_path])
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
    return verdict


def check_destination_collision(output_dir, expected_case_id):
    """Rejeita colisao com entrega de outro caso no mesmo destino.

    Se o destino ja contem delivery-manifest.json do mesmo caso, permite a
    reexecucao idempotente (com backup/restauracao em caso de falha). Se o
    manifesto pertencer a outro caso ou o destino contiver arquivos
    desconhecidos, bloqueia antes de qualquer render.
    """
    if not os.path.exists(output_dir):
        return
    manifest_path = os.path.join(output_dir, 'delivery-manifest.json')
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, 'r', encoding='utf-8') as handle:
                existing = json.load(handle)
            existing_case = existing.get('caseId')
            if existing_case and existing_case != expected_case_id:
                raise DeliveryCollisionError(
                    f"colisao de entrega: destino ja contem entrega do caso '{existing_case}'"
                    f" (diferente de '{expected_case_id}')"
                )
        except (json.JSONDecodeError, OSError) as exc:
            if isinstance(exc, DeliveryCollisionError):
                raise
            raise DeliveryCollisionError('destino contem manifesto de entrega ilegivel ou invalido')
    else:
        entries = [
            name for name in os.listdir(output_dir)
            if name != render_local.PROMOTION_LOCK_NAME and not name.startswith('.')
        ]
        if entries:
            for name in entries:
                if name.endswith('.json'):
                    try:
                        with open(os.path.join(output_dir, name), 'r', encoding='utf-8') as handle:
                            data = json.load(handle)
                        other_case = data.get('caseId')
                        if other_case and other_case != expected_case_id:
                            raise DeliveryCollisionError(
                                f"colisao de entrega: destino contem arquivo do caso '{other_case}'"
                            )
                    except Exception as exc:
                        if isinstance(exc, DeliveryCollisionError):
                            raise
            raise DeliveryCollisionError('destino ja existe e contem arquivos desconhecidos')


def prepare_pipeline_staging(root, output_dir, case_path, assets_path, staging_arg,
                             asset_manifest_path=None,
                             text_overlays_path=None, visual_style_path=None):
    if staging_arg:
        staging = os.path.realpath(staging_arg)
        if not contained(root, staging):
            raise render_local.InputFileError('caminho de staging fora da raiz do projeto')
        if staging == os.path.realpath(root):
            raise render_local.InputFileError('staging nao pode ser a raiz do projeto')
        if os.path.realpath(root).startswith(staging + os.sep):
            raise render_local.InputFileError('staging nao pode conter a raiz do projeto')
        for label, path in (('case', case_path), ('assets', assets_path),
                            ('asset-manifest', asset_manifest_path), ('output', output_dir),
                            ('text-overlays', text_overlays_path), ('visual-style', visual_style_path)):
            if path and overlaps(staging, path):
                raise render_local.InputFileError(f'staging sobrepoe {label} da execucao')
        if os.path.exists(staging):
            if not os.path.isdir(staging) or os.listdir(staging):
                raise render_local.InputFileError('staging informado ja existe e nao esta vazio')
            return staging, False
        os.makedirs(staging)
        return staging, True
    parent = os.path.join(root, '.workspace', 'tmp')
    os.makedirs(parent, exist_ok=True)
    staging = tempfile.mkdtemp(prefix='local-pipeline-staging-', dir=parent)
    return staging, True


def _validate_optional_bridge_inputs(root, pairs):
    for label, path in pairs:
        if not path:
            continue
        if not contained(root, path):
            raise render_local.InputFileError(f'caminho de {label} fora da raiz do projeto')
        if not os.path.isfile(path):
            raise render_local.InputFileError(f'arquivo de {label} ausente')


def run_plan_only(case_path, root, asset_manifest_path=None,
                  text_overlays_path=None, visual_style_path=None):
    root = os.path.realpath(root)
    _validate_optional_bridge_inputs(root, [
        ('case', case_path),
        ('asset-manifest', asset_manifest_path),
        ('text-overlays', text_overlays_path),
        ('visual-style', visual_style_path),
    ])

    verdict = run_bridge_case(
        root,
        case_path,
        asset_manifest_path=asset_manifest_path,
        text_overlays_path=text_overlays_path,
        visual_style_path=visual_style_path,
        plan_only=True,
    )
    if not verdict.get('ok'):
        raise render_local.RenderInputError(verdict.get('failureCode', 'CASE_INVALID'),
                                            verdict.get('subject') or verdict.get('summary'))
    return verdict['plan']


def _probe_and_extract_media_metadata(root, asset_id, media_type, target_abs):
    """Sonda arquivo com FFprobe e valida dimensoes e duracao (quando video)."""
    try:
        info = render_local.probe_asset(root, target_abs)
    except build_video.DeliveryError as exc:
        raise build_video.DeliveryError(f'ASSET_CORRUPTED: {asset_id} ({exc})')

    video_streams = [s for s in info.get('streams', []) if s.get('codec_type') == 'video']
    stream = video_streams[0]
    width = int(stream['width'])
    height = int(stream['height'])
    if width <= 0 or height <= 0 or width % 2 != 0 or height % 2 != 0:
        raise build_video.DeliveryError(
            f'ASSET_DIMENSIONS_INVALID: {asset_id} ({width}x{height})'
        )

    duration_s = None
    if media_type == 'video':
        raw_dur = stream.get('duration') or info.get('format', {}).get('duration')
        try:
            duration_s = float(raw_dur)
        except (TypeError, ValueError):
            raise build_video.DeliveryError(f'ASSET_DURATION_INVALID: {asset_id}')
        if duration_s <= 0:
            raise build_video.DeliveryError(f'ASSET_DURATION_INVALID: {asset_id}')

    return {
        'width': width,
        'height': height,
        'codec': stream.get('codec_name'),
        'durationSeconds': round(duration_s, 3) if duration_s is not None else None,
        '_rawDurationSeconds': duration_s,
    }


def verify_manifest_assets(root, asset_manifest, resolved_bindings):
    """Verifica contencao, tamanho, SHA-256, FFprobe e duracao de cada asset unico uma unica vez."""
    try:
        render_local.ensure_video_tools(root)
    except build_video.DeliveryError as exc:
        raise build_video.DeliveryError(f'FFMPEG_UNAVAILABLE: {exc}')

    inspected_by_id = {}
    source_abs_by_id = {}

    for asset in asset_manifest['assets']:
        asset_id = asset['id']
        rel_path = asset['path']
        media_type = asset['type']
        expected_bytes = asset['bytes']
        expected_sha256 = asset['sha256']

        joined = os.path.join(root, rel_path.replace('/', os.sep))
        abs_path = os.path.realpath(joined)
        if not contained(root, abs_path):
            raise build_video.DeliveryError(f'ASSET_PATH_OUTSIDE_ROOT: {asset_id} ({rel_path})')
        if not os.path.isfile(abs_path):
            raise build_video.DeliveryError(f'ASSET_MISSING: {asset_id} ({rel_path})')
        try:
            with open(abs_path, 'rb') as check_handle:
                check_handle.read(1)
        except OSError:
            raise build_video.DeliveryError(f'ASSET_UNREADABLE: {asset_id} ({rel_path})')

        actual_bytes = os.path.getsize(abs_path)
        if actual_bytes != expected_bytes:
            raise build_video.DeliveryError(
                f'ASSET_SIZE_MISMATCH: {asset_id} (esperado {expected_bytes}, obtido {actual_bytes})'
            )

        actual_sha256 = sha256_file(abs_path)
        if actual_sha256 != expected_sha256:
            raise build_video.DeliveryError(
                f'ASSET_HASH_MISMATCH: {asset_id} (esperado {expected_sha256}, obtido {actual_sha256})'
            )

        probe_meta = _probe_and_extract_media_metadata(root, asset_id, media_type, abs_path)
        inspected_by_id[asset_id] = {
            'id': asset_id,
            'type': media_type,
            'path': rel_path,
            'bytes': actual_bytes,
            'sha256': actual_sha256,
            'origin': asset['origin'],
            'license': asset['license'],
            'width': probe_meta['width'],
            'height': probe_meta['height'],
            'codec': probe_meta['codec'],
            'durationSeconds': probe_meta['durationSeconds'],
            '_rawDurationSeconds': probe_meta['_rawDurationSeconds'],
        }
        source_abs_by_id[asset_id] = abs_path

    binding_reports = []
    for binding in resolved_bindings:
        beat_id = binding['beatId']
        asset_id = binding['assetId']
        asset_info = inspected_by_id[asset_id]
        beat_duration_s = binding['durationMs'] / 1000.0
        if binding['type'] == 'video':
            asset_dur_s = asset_info['_rawDurationSeconds']
            if asset_dur_s is None or (asset_dur_s + 0.05) < beat_duration_s:
                raise build_video.DeliveryError(
                    f"ASSET_VIDEO_TOO_SHORT: {beat_id} exige {beat_duration_s:.3f}s, "
                    f"asset '{asset_id}' tem {0.0 if asset_dur_s is None else asset_dur_s:.3f}s"
                )
        binding_reports.append({
            'beatId': beat_id,
            'assetId': asset_id,
            'type': binding['type'],
            'path': binding['path'],
            'bytes': asset_info['bytes'],
            'sha256': asset_info['sha256'],
            'durationMs': binding['durationMs'],
            'width': asset_info['width'],
            'height': asset_info['height'],
            'durationSeconds': asset_info['durationSeconds'],
        })

    public_assets = []
    for asset in asset_manifest['assets']:
        entry = dict(inspected_by_id[asset['id']])
        entry.pop('_rawDurationSeconds', None)
        public_assets.append(entry)

    return inspected_by_id, source_abs_by_id, public_assets, binding_reports


def run_check_assets(case_path, asset_manifest_path, root,
                     text_overlays_path=None, visual_style_path=None):
    root = os.path.realpath(root)
    _validate_optional_bridge_inputs(root, [
        ('case', case_path),
        ('asset-manifest', asset_manifest_path),
        ('text-overlays', text_overlays_path),
        ('visual-style', visual_style_path),
    ])

    verdict = run_bridge_case(
        root,
        case_path,
        asset_manifest_path=asset_manifest_path,
        text_overlays_path=text_overlays_path,
        visual_style_path=visual_style_path,
        plan_only=True,
    )
    if not verdict.get('ok'):
        raise render_local.RenderInputError(verdict.get('failureCode', 'CASE_INVALID'),
                                            verdict.get('subject') or verdict.get('summary'))

    asset_manifest = verdict['assetManifest']
    resolved_bindings = verdict['resolvedAssetBindings']
    _, _, public_assets, binding_reports = verify_manifest_assets(
        root, asset_manifest, resolved_bindings
    )

    return {
        'ok': True,
        'status': 'assets-verified',
        'caseId': verdict['caseId'],
        'packageId': verdict['packageId'],
        'assetCount': len(public_assets),
        'bindingCount': len(binding_reports),
        'checkedAssets': public_assets,
        'resolvedBindings': binding_reports,
    }


def run_render_pipeline(case_path, assets_path, output_dir, root, staging_dir, preset='veryfast',
                        text_overlays_path=None, visual_style_path=None, asset_manifest_path=None):
    root = os.path.realpath(root)
    if bool(assets_path) == bool(asset_manifest_path):
        raise render_local.InputFileError('informe exatamente um entre --assets e --asset-manifest')

    inputs_to_check = [('case', case_path)]
    if assets_path:
        inputs_to_check.append(('assets', assets_path))
    if asset_manifest_path:
        inputs_to_check.append(('asset-manifest', asset_manifest_path))
    if text_overlays_path:
        inputs_to_check.append(('text-overlays', text_overlays_path))
    if visual_style_path:
        inputs_to_check.append(('visual-style', visual_style_path))

    for label, path in inputs_to_check + [('output', output_dir)]:
        if not contained(root, path):
            raise render_local.InputFileError(f'caminho de {label} fora da raiz do projeto')
    for label, path in inputs_to_check:
        if not os.path.isfile(path):
            raise render_local.InputFileError(f'arquivo de {label} ausente')

    output_real = os.path.realpath(output_dir)
    if output_real == os.path.realpath(root):
        raise render_local.InputFileError('destino nao pode ser a raiz do projeto')
    for label, path in inputs_to_check:
        if overlaps(output_real, path):
            raise render_local.InputFileError(f'destino sobrepoe {label} da execucao')

    render_local.ensure_video_tools(root)

    staging, staging_created = prepare_pipeline_staging(
        root, output_dir, case_path, assets_path, staging_dir,
        asset_manifest_path=asset_manifest_path,
        text_overlays_path=text_overlays_path, visual_style_path=visual_style_path)

    verdict = run_bridge_case(
        root,
        case_path,
        assets_path=assets_path,
        asset_manifest_path=asset_manifest_path,
        text_overlays_path=text_overlays_path,
        visual_style_path=visual_style_path,
        plan_only=False,
    )
    if not verdict.get('ok'):
        raise render_local.RenderInputError(verdict.get('failureCode', 'CASE_INVALID'),
                                            verdict.get('subject') or verdict.get('summary'))

    case_id = verdict['caseId']
    package = verdict['package']
    association = verdict['association']
    canonical_package_json = verdict['canonicalJson']
    canonical_overlay_json = verdict.get('canonicalTextOverlayJson')
    resolved_text_overlays = verdict.get('resolvedTextOverlays', [])
    visual_style = verdict.get('visualStyle')
    canonical_visual_style_json = verdict.get('canonicalVisualStyleJson')
    asset_manifest = verdict.get('assetManifest')
    canonical_asset_manifest_json = verdict.get('canonicalAssetManifestJson')
    resolved_asset_bindings = verdict.get('resolvedAssetBindings', [])

    check_destination_collision(output_dir, case_id)

    binding_reports = []
    if asset_manifest_path and asset_manifest:
        _, source_abs_by_id, _, binding_reports = verify_manifest_assets(
            root, asset_manifest, resolved_asset_bindings
        )
        verified_dir = os.path.join(staging, 'verified-assets')
        os.makedirs(verified_dir, exist_ok=True)
        staged_by_id = {}
        for asset in asset_manifest['assets']:
            asset_id = asset['id']
            ext = os.path.splitext(asset['path'])[1].lower()
            staged_asset = os.path.join(verified_dir, f'{asset_id}{ext}')
            shutil.copyfile(source_abs_by_id[asset_id], staged_asset)
            if os.path.getsize(staged_asset) != asset['bytes'] or sha256_file(staged_asset) != asset['sha256']:
                raise build_video.DeliveryError(f'ASSET_HASH_MISMATCH: copia em staging divergiu para {asset_id}')
            staged_by_id[asset_id] = staged_asset
        asset_paths = [staged_by_id[binding['assetId']] for binding in resolved_asset_bindings]
    else:
        by_beat = {binding['beatId']: binding['path'] for binding in association['assets']}
        asset_paths = []
        for step in package['timeline']:
            relative = by_beat[step['beatId']]
            absolute = os.path.join(root, relative)
            if not contained(root, absolute) or not os.path.isfile(absolute):
                raise build_video.DeliveryError(f'asset ausente ou fora da raiz: {relative}')
            render_local.probe_asset(root, absolute)
            asset_paths.append(absolute)

    package_id = package['packageId']
    names = {
        'package': f'{package_id}.execution-package.json',
        'video': f'{package_id}-primary-output.mp4',
        'srt': f'{package_id}-captions.srt',
        'narration': f'{package_id}-narration-script.txt',
        'report': f'{package_id}-execution-report.json',
        'manifest': 'delivery-manifest.json',
    }
    if text_overlays_path and canonical_overlay_json:
        names['textOverlayPlan'] = f'{package_id}-text-overlay-plan.json'
    if visual_style_path and canonical_visual_style_json:
        names['visualStyle'] = f'{package_id}-visual-style.json'
    if asset_manifest_path and canonical_asset_manifest_json:
        names['assetManifest'] = f'{package_id}-asset-manifest.json'

    staging_paths = {key: os.path.join(staging, names[key]) for key in names}

    write_text(staging_paths['package'], canonical_package_json)
    write_text(staging_paths['srt'], render_local.build_srt(package))
    write_text(staging_paths['narration'], render_local.build_narration(package))

    title_srt_staging = None
    if text_overlays_path and canonical_overlay_json:
        write_text(staging_paths['textOverlayPlan'], canonical_overlay_json)
        if resolved_text_overlays:
            title_srt_content = render_local.build_title_srt(resolved_text_overlays)
            if title_srt_content:
                title_srt_staging = os.path.join(staging, f'{package_id}-titles.srt')
                write_text(title_srt_staging, title_srt_content)

    if visual_style_path and canonical_visual_style_json:
        write_text(staging_paths['visualStyle'], canonical_visual_style_json)

    if asset_manifest_path and canonical_asset_manifest_json:
        write_text(staging_paths['assetManifest'], canonical_asset_manifest_json)

    title_style = render_local.build_title_style(visual_style) if visual_style else None
    cmd = render_local.build_render_command(
        package, asset_paths, staging_paths['srt'], staging_paths['video'], preset,
        title_srt_path=title_srt_staging, title_style=title_style)
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=render_local.RENDER_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise build_video.DeliveryError(
            'renderizacao excedeu o tempo limite; entrega anterior preservada'
        )
    if res.returncode != 0:
        raise build_video.DeliveryError(
            'renderizacao da ferramenta de video falhou; entrega anterior preservada'
        )

    output = package['output']
    duration_s = output['durationMs'] / 1000.0
    inspection = build_video.validate_mp4(
        staging_paths['video'], output['width'], output['height'], output['fps'], duration_s,
        timeout=render_local.PROBE_TIMEOUT_SECONDS)
    srt_errors = srt_validate.validate_srt_file(staging_paths['srt'], duration_s)
    if srt_errors:
        raise build_video.DeliveryError('SRT invalido: ' + '; '.join(srt_errors))
    with open(staging_paths['narration'], 'rb') as handle:
        narration_bytes = handle.read()
    if not narration_bytes.decode('utf-8').strip():
        raise build_video.DeliveryError('narracao vazia ou nao UTF-8')

    dests = {key: os.path.join(output_dir, names[key]) for key in names}
    command = (
        'python tools/render_pipeline.py'
        f' --case {rel(root, case_path)}'
    )
    if asset_manifest_path:
        command += f' --asset-manifest {rel(root, asset_manifest_path)}'
    else:
        command += f' --assets {rel(root, assets_path)}'
    command += f' --output-dir {rel(root, output_dir)}'
    if text_overlays_path:
        command += f' --text-overlays {rel(root, text_overlays_path)}'
    if visual_style_path:
        command += f' --visual-style {rel(root, visual_style_path)}'

    report_artifacts = [
        {
            'id': 'package',
            'kind': 'execution-package',
            'path': rel(root, dests['package']),
            'sha256': sha256_file(staging_paths['package']),
            'bytes': os.path.getsize(staging_paths['package']),
        },
        {
            'id': 'video',
            'kind': 'primary-output',
            'path': rel(root, dests['video']),
            'sha256': sha256_file(staging_paths['video']),
            'bytes': os.path.getsize(staging_paths['video']),
        },
        {
            'id': 'srt',
            'kind': 'captions',
            'path': rel(root, dests['srt']),
            'sha256': sha256_file(staging_paths['srt']),
            'bytes': os.path.getsize(staging_paths['srt']),
        },
        {
            'id': 'narration',
            'kind': 'narration-script',
            'path': rel(root, dests['narration']),
            'sha256': sha256_file(staging_paths['narration']),
            'bytes': os.path.getsize(staging_paths['narration']),
        },
    ]
    if 'textOverlayPlan' in dests:
        report_artifacts.append({
            'id': 'textOverlayPlan',
            'kind': 'text-overlay-plan',
            'path': rel(root, dests['textOverlayPlan']),
            'sha256': sha256_file(staging_paths['textOverlayPlan']),
            'bytes': os.path.getsize(staging_paths['textOverlayPlan']),
        })
    if 'visualStyle' in dests:
        report_artifacts.append({
            'id': 'visualStyle',
            'styleId': visual_style['id'],
            'kind': 'visual-style',
            'path': rel(root, dests['visualStyle']),
            'sha256': sha256_file(staging_paths['visualStyle']),
            'bytes': os.path.getsize(staging_paths['visualStyle']),
        })
    if 'assetManifest' in dests and asset_manifest:
        report_artifacts.append({
            'id': 'assetManifest',
            'caseId': asset_manifest['caseId'],
            'packageId': asset_manifest['packageId'],
            'assetCount': len(asset_manifest['assets']),
            'kind': 'asset-manifest',
            'path': rel(root, dests['assetManifest']),
            'sha256': sha256_file(staging_paths['assetManifest']),
            'bytes': os.path.getsize(staging_paths['assetManifest']),
        })

    report_assets = binding_reports if (asset_manifest_path and binding_reports) else [
        {'beatId': step['beatId'], 'path': rel(root, path), 'sha256': sha256_file(path)}
        for step, path in zip(package['timeline'], asset_paths)
    ]

    report = {
        'schemaVersion': 1,
        'adapter': ADAPTER_ID,
        'status': 'completed',
        'caseId': case_id,
        'packageId': package_id,
        'projectId': package['projectId'],
        'compositionId': package['compositionId'],
        'outputPlanId': package['outputPlanId'],
        'beatPlanId': package['beatPlanId'],
        'output': {
            'width': output['width'],
            'height': output['height'],
            'aspectRatio': output['aspectRatio'],
            'fps': output['fps'],
            'durationMs': output['durationMs'],
        },
        'inspection': inspection,
        'captions': {
            'blocks': sum(1 for step in package['timeline'] if step.get('onScreenText')),
            'valid': True,
        },
        'assets': report_assets,
        'artifacts': report_artifacts,
        'tools': {
            'ffmpeg': render_local.tool_version(build_video.get_ffmpeg()),
            'ffprobe': render_local.tool_version(build_video.get_ffprobe()),
        },
        'command': command,
    }
    if visual_style:
        report['visualStyleId'] = visual_style['id']
    if text_overlays_path:
        report['textOverlays'] = [
            {'beatId': item['beatId'], 'text': item['text'], 'startMs': item['startMs'], 'endMs': item['endMs']}
            for item in resolved_text_overlays
        ]
    if 'assetManifest' in dests and asset_manifest:
        report['assetManifest'] = {
            'caseId': asset_manifest['caseId'],
            'packageId': asset_manifest['packageId'],
            'assetCount': len(asset_manifest['assets']),
            'bindingCount': len(asset_manifest['bindings']),
            'path': rel(root, dests['assetManifest']),
            'sha256': sha256_file(staging_paths['assetManifest']),
            'bytes': os.path.getsize(staging_paths['assetManifest']),
        }
    write_text(staging_paths['report'], json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    manifest_artifacts = {
        'package': {
            'id': 'package',
            'path': rel(root, dests['package']),
            'sha256': sha256_file(staging_paths['package']),
            'bytes': os.path.getsize(staging_paths['package']),
        },
        'video': {
            'id': 'video',
            'path': rel(root, dests['video']),
            'sha256': sha256_file(staging_paths['video']),
            'bytes': os.path.getsize(staging_paths['video']),
            'ffprobe': inspection,
        },
        'srt': {
            'id': 'srt',
            'path': rel(root, dests['srt']),
            'sha256': sha256_file(staging_paths['srt']),
            'bytes': os.path.getsize(staging_paths['srt']),
        },
        'narration': {
            'id': 'narration',
            'path': rel(root, dests['narration']),
            'sha256': sha256_file(staging_paths['narration']),
            'bytes': os.path.getsize(staging_paths['narration']),
        },
        'report': {
            'id': 'report',
            'path': rel(root, dests['report']),
            'sha256': sha256_file(staging_paths['report']),
            'bytes': os.path.getsize(staging_paths['report']),
        },
    }
    if 'textOverlayPlan' in dests:
        manifest_artifacts['textOverlayPlan'] = {
            'id': 'textOverlayPlan',
            'path': rel(root, dests['textOverlayPlan']),
            'sha256': sha256_file(staging_paths['textOverlayPlan']),
            'bytes': os.path.getsize(staging_paths['textOverlayPlan']),
        }
    if 'visualStyle' in dests:
        manifest_artifacts['visualStyle'] = {
            'id': visual_style['id'],
            'styleId': visual_style['id'],
            'path': rel(root, dests['visualStyle']),
            'sha256': sha256_file(staging_paths['visualStyle']),
            'bytes': os.path.getsize(staging_paths['visualStyle']),
        }
    if 'assetManifest' in dests and asset_manifest:
        manifest_artifacts['assetManifest'] = {
            'id': 'assetManifest',
            'caseId': asset_manifest['caseId'],
            'packageId': asset_manifest['packageId'],
            'assetCount': len(asset_manifest['assets']),
            'path': rel(root, dests['assetManifest']),
            'sha256': sha256_file(staging_paths['assetManifest']),
            'bytes': os.path.getsize(staging_paths['assetManifest']),
        }

    manifest = {
        'schemaVersion': 1,
        'adapter': ADAPTER_ID,
        'caseId': case_id,
        'packageId': package_id,
        'projectId': package['projectId'],
        'compositionId': package['compositionId'],
        'outputPlanId': package['outputPlanId'],
        'beatPlanId': package['beatPlanId'],
        'command': command,
        'outputDir': rel(root, output_dir),
        'artifacts': manifest_artifacts,
    }
    if assets_path:
        manifest['association'] = rel(root, assets_path)
    if asset_manifest_path and asset_manifest:
        manifest['assetManifest'] = rel(root, asset_manifest_path)
        manifest['assetManifestSummary'] = manifest_artifacts['assetManifest']
    if text_overlays_path:
        manifest['textOverlays'] = rel(root, text_overlays_path)
    if visual_style_path and visual_style:
        manifest['visualStyleId'] = visual_style['id']
        manifest['visualStyle'] = rel(root, visual_style_path)
    write_text(staging_paths['manifest'], json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')

    backup_dir = os.path.join(staging, '.backup')
    lock = render_local.acquire_promotion_lock(output_dir)
    try:
        check_destination_collision(output_dir, case_id)
        render_local.promote_with_backup(staging_paths, dests, backup_dir)
    finally:
        os.remove(lock)
    shutil.rmtree(backup_dir, ignore_errors=True)
    if staging_created:
        shutil.rmtree(staging, ignore_errors=True)

    summary = {
        'status': 'completed',
        'caseId': case_id,
        'packageId': package_id,
        'outputDir': rel(root, output_dir),
        'manifest': rel(root, dests['manifest']),
        'artifacts': {key: rel(root, dests[key]) for key in names},
        'inspection': inspection,
    }
    if visual_style:
        summary['visualStyleId'] = visual_style['id']
    if 'assetManifest' in manifest_artifacts:
        summary['assetManifest'] = manifest_artifacts['assetManifest']
        summary['assets'] = binding_reports
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Pipeline local de renderizacao do CreativeExecutionPackage a partir de casos')
    parser.add_argument('--case', required=True, help='Manifesto do caso (*.pipeline.json)')
    parser.add_argument('--plan-only', action='store_true', help='Apenas calcula e exibe a previa do plano')
    parser.add_argument('--check-assets', action='store_true',
                        help='Verifica integridade e inspecao previa dos assets declarados em --asset-manifest')
    parser.add_argument('--assets', default=None, help='Associacao explicita de assets (*.assets.json)')
    parser.add_argument('--asset-manifest', default=None, help='Inventario de midia versionado (*.asset-manifest.json)')
    parser.add_argument('--text-overlays', default=None, help='Plano declarativo de sobreposicao de titulos (*.json)')
    parser.add_argument('--visual-style', default=None, help='Direcao visual compartilhada (*.json)')
    parser.add_argument('--output-dir', default=None, help='Diretorio final de entrega')
    parser.add_argument('--root', default=os.getcwd(), help='Raiz do projeto')
    parser.add_argument('--staging', default=None, help='Diretorio de staging exclusivo')
    parser.add_argument('--preset', default='veryfast', help='Preset do FFmpeg')
    parser.add_argument('--json', action='store_true', help='Emite resultado estruturado em JSON no stdout')
    args = parser.parse_args(argv)

    if args.assets and args.asset_manifest:
        print('Erro: informe apenas um entre --assets e --asset-manifest', file=sys.stderr)
        return 2

    if args.check_assets and args.plan_only:
        print('Erro: nao combine --check-assets com --plan-only', file=sys.stderr)
        return 2

    if args.check_assets:
        if not args.asset_manifest or args.output_dir or args.assets:
            print('Erro: --check-assets exige --asset-manifest e nao aceita --assets nem --output-dir',
                  file=sys.stderr)
            return 2
    elif not args.plan_only:
        if not args.output_dir or (not args.assets and not args.asset_manifest):
            print('Erro: informe --output-dir e (--assets ou --asset-manifest), ou use --plan-only / --check-assets',
                  file=sys.stderr)
            return 2

    try:
        if args.plan_only:
            payload = run_plan_only(
                args.case,
                args.root,
                asset_manifest_path=args.asset_manifest,
                text_overlays_path=args.text_overlays,
                visual_style_path=args.visual_style,
            )
        elif args.check_assets:
            payload = run_check_assets(
                args.case,
                args.asset_manifest,
                args.root,
                text_overlays_path=args.text_overlays,
                visual_style_path=args.visual_style,
            )
        else:
            payload = run_render_pipeline(
                args.case,
                args.assets,
                args.output_dir,
                args.root,
                args.staging,
                preset=args.preset,
                text_overlays_path=args.text_overlays,
                visual_style_path=args.visual_style,
                asset_manifest_path=args.asset_manifest,
            )
    except render_local.RenderInputError as exc:
        subject = f': {exc.subject}' if exc.subject else ''
        print(f'Erro: entrada invalida ({exc.code}{subject})', file=sys.stderr)
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
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.plan_only:
        plan = payload
        recorte_txt = 'Sim' if plan.get('supported') else f"Nao ({plan.get('unsupportedReason')})"
        print('Plano de renderizacao:')
        print(f"  Caso: {plan['caseId']}")
        print(f"  Pacote: {plan['packageId']}")
        print(f"  Perfil: {plan['perfil']}")
        print(f"  Geometria: {plan['geometria']}")
        print(f"  FPS: {plan['fps']}")
        print(f"  Duracao: {plan['duracao']}")
        print(f"  Beats que precisam de assets: {', '.join(plan['beats'])}")
        print(f"  Cabe no recorte do adaptador: {recorte_txt}")
        if plan.get('assetManifest'):
            am = plan['assetManifest']
            print(f"  Inventario de midia: {am['assetCount']} asset(s), {len(am['bindings'])} vinculo(s)")
            for item in am.get('resolvedBindings', []):
                print(f"    - {item['beatId']} -> {item['assetId']} ({item['type']}, {item['path']})")
        if plan.get('textOverlays'):
            print('  Titulos sobrepostos:')
            for item in plan['textOverlays']:
                print(f"    - {item['beatId']} ({item['startMs']}ms -> {item['endMs']}ms): \"{item['text']}\"")
        if plan.get('visualStyle'):
            vs = plan['visualStyle']
            t_info = vs.get('title', {})
            print(f"  Estilo visual: {vs.get('id', 'desconhecido')}")
            print(f"    Cor do texto: {t_info.get('textColor')}")
            print(f"    Cor do contorno: {t_info.get('outlineColor')}")
            print(f"    Tamanho da fonte: {t_info.get('fontSize')}px")
            print(f"    Margem superior: {t_info.get('marginTop')}px")
            print(f"    Margem lateral: {t_info.get('marginHorizontal')}px")
            status_titulos = 'Sim' if plan.get('hasTitlesToApply') else 'Nao (sem titulos definidos)'
            print(f"    Aplicavel a titulos: {status_titulos}")
        return 0

    if args.check_assets:
        print(
            f"Inventario verificado: {payload['assetCount']} asset(s) unicos, "
            f"{payload['bindingCount']} vinculo(s)"
        )
        for item in payload['resolvedBindings']:
            dur_txt = f", {item['durationSeconds']}s" if item.get('durationSeconds') is not None else ''
            print(
                f"  - {item['beatId']} -> {item['assetId']} "
                f"({item['type']}, {item['width']}x{item['height']}{dur_txt})"
            )
        return 0

    print(f"Entrega promovida: {payload['outputDir']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
