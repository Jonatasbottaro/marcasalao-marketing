"""Producao de video por entrada unica (VideoRequest v1).

Um operador descreve as cenas em um JSON, confere a previa e exporta o video
para os perfis escolhidos, reutilizando o pipeline local de renderizacao.

Uso (a partir da raiz do checkout):
  python tools/produce_video.py --input <pedido.json> --plan-only --json
  python tools/produce_video.py --input <pedido.json> --output-dir <entrega> --json
  python tools/produce_video.py --input <pedido.json> --profile youtube-shorts --output-dir <entrega> --json

Responsabilidades:
- Previa (--plan-only): compila o pedido pelo nucleo puro, mostra perfis
  resolvidos, duracao, tempos por cena (janela solicitada na fonte e posicao
  na montagem, distintas), midias e avisos. Sem FFmpeg, sem leitura de midias
  e sem gravacao; a conferencia do arquivo e da duracao disponivel pertence a
  etapa de inspecao de midia do pipeline.
- Exportacao: escreve os documentos derivados em staging interno, prepara e
  verifica o AssetManifest por perfil e chama o pipeline local existente.
  Entrega MP4 sem audio, legenda queimada, SRT e roteiro de narracao em TXT.
- Revisao e recuperacao: reexporta um perfil (--profile) apos corrigir cena ou
  titulo, com promocao transacional; falha de um perfil preserva a entrega
  anterior daquele perfil e nao impede os demais perfis validos.
- Entrega verificavel: indice (index.json) com manifestos finais e estado por
  perfil; caminhos validos apos a limpeza do staging.

Em --json: stdout reservado a um unico resultado JSON; erros sanitizados em
stderr. Exit codes: 0 sucesso; 1 falha de render/asset/promocao; 2 uso, caminho
fora da raiz ou JSON/arquivo ausente; 3 pedido, caso ou perfil invalidos.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import prepare_asset_manifest
import r002_pilot
import render_local
import render_pipeline


def write_json(path, value):
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def write_text(path, text):
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)


def rel(root, path):
    return render_local.rel(root, path)


def run_bridge_video_request(root, input_path, profile=None, motion_plan_path=None):
    node = shutil.which('node')
    if not node:
        raise render_local.InputFileError('node nao encontrado no PATH')
    dist_module = os.path.join(root, 'platform', 'dist', 'src', 'compile-video-request.js')
    if not os.path.isfile(dist_module):
        raise render_local.InputFileError('build da platform ausente; execute npm run build em platform/')
    bridge = os.path.join(root, 'tools', 'render_bridge.mjs')
    cmd = [node, bridge, '--video-request', input_path, '--root', root]
    if profile:
        cmd.extend(['--profile', profile])
    if motion_plan_path:
        cmd.extend(['--motion-plan', motion_plan_path])
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             encoding='utf-8', errors='replace',
                             timeout=render_local.BRIDGE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise build_video.DeliveryError('ponte de compilacao excedeu o tempo limite')
    if res.returncode == 2:
        raise render_local.InputFileError('arquivo de pedido ilegivel ou JSON invalido')
    if res.returncode not in (0, 3):
        raise build_video.DeliveryError('ponte de compilacao falhou de forma inesperada')
    try:
        verdict = json.loads(res.stdout)
    except ValueError:
        raise build_video.DeliveryError('veredito da ponte ilegivel')
    return verdict


def preview_profile(profile):
    plan = profile.get('plan')
    return {
        'profileId': profile['profileId'],
        'caseId': profile['caseId'],
        'status': profile['status'],
        'failureCode': profile.get('failureCode'),
        'errors': profile.get('errors', []),
        'geometry': plan['geometry'] if plan else None,
        'fps': plan['fps'] if plan else None,
        'durationMs': plan['durationMs'] if plan else None,
        'durationSeconds': plan['durationSeconds'] if plan else None,
        'beats': plan['beats'] if plan else [],
        'supported': plan['supported'] if plan else None,
        'warnings': profile.get('warnings', []),
        'motion': profile.get('motion'),
    }


def write_working_documents(run_dir, profile, project):
    os.makedirs(run_dir, exist_ok=True)
    paths = {
        'project': os.path.join(run_dir, 'project.json'),
        'composition': os.path.join(run_dir, 'composition.json'),
        'output_plan': os.path.join(run_dir, 'output-plan.json'),
        'beat_plan': os.path.join(run_dir, 'beat-plan.json'),
        'case': os.path.join(run_dir, 'case.pipeline.json'),
        'association': os.path.join(run_dir, 'association.assets.json'),
        'asset_manifest': os.path.join(run_dir, 'asset-manifest.json'),
    }
    write_json(paths['project'], project)
    write_json(paths['composition'], profile['composition'])
    write_json(paths['output_plan'], profile['outputPlan'])
    write_json(paths['beat_plan'], profile['beatPlan'])
    write_json(paths['case'], {
        'schemaVersion': 1,
        'id': profile['caseId'],
        'project': 'project.json',
        'composition': 'composition.json',
        'outputPlan': 'output-plan.json',
        'beatPlan': 'beat-plan.json',
    })
    write_json(paths['association'], profile['association'])
    overlays = profile.get('textOverlayPlan')
    if overlays and overlays.get('overlays'):
        paths['overlays'] = os.path.join(run_dir, 'text-overlays.json')
        write_json(paths['overlays'], overlays)
    style = profile.get('visualStyle')
    if style:
        paths['style'] = os.path.join(run_dir, 'visual-style.json')
        write_json(paths['style'], style)
    return paths


def _verify_attempt_fence(fence_file, attempt_id=None):
    if not fence_file:
        return
    try:
        with open(fence_file, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        raise build_video.DeliveryError('QUEUE_FENCE_REVOKED: tentativa perdeu a reserva antes da promocao')
    if not isinstance(data, dict) or data.get('revoked'):
        raise build_video.DeliveryError('QUEUE_FENCE_REVOKED: tentativa perdeu a reserva antes da promocao')
    if attempt_id and data.get('attemptId') != attempt_id:
        raise build_video.DeliveryError('QUEUE_FENCE_REVOKED: reserva pertence a outra tentativa')


def export_profile(root, profile, project, media, output_dir, run_root, preset, staging,
                   motion_plan=None, attempt_id=None, fence_file=None):
    profile_id = profile['profileId']
    run_dir = os.path.join(run_root, profile_id)
    paths = write_working_documents(run_dir, profile, project)
    _, canonical_json = prepare_asset_manifest.build_asset_manifest_from_registry(
        root, paths['case'], paths['association'], media)
    write_text(paths['asset_manifest'], canonical_json)
    profile_output = os.path.join(output_dir, profile_id)
    motion = None
    if motion_plan and profile.get('motion'):
        motion = {'plan': motion_plan, 'effects': profile['motion']['effects']}
    extra_fields = {'attemptId': attempt_id} if attempt_id else None
    pre_hook = (lambda: _verify_attempt_fence(fence_file, attempt_id)) if fence_file else None
    summary = render_pipeline.run_render_pipeline(
        paths['case'],
        None,
        profile_output,
        root,
        staging,
        preset=preset,
        text_overlays_path=paths.get('overlays'),
        visual_style_path=paths.get('style'),
        asset_manifest_path=paths['asset_manifest'],
        motion=motion,
        extra_manifest_fields=extra_fields,
        pre_promote_hook=pre_hook,
    )
    res = {
        'profileId': profile_id,
        'caseId': profile['caseId'],
        'packageId': summary['packageId'],
        'status': 'completed',
        'outputDir': summary['outputDir'],
        'deliveryManifest': summary['manifest'],
        'artifacts': summary['artifacts'],
        'inspection': summary['inspection'],
    }
    if attempt_id:
        res['attemptId'] = attempt_id
    return res


def render_assembly_preview(root, request_data, profile_id, output_mp4_path,
                            preset='veryfast', scale_factor=0.5, motion_plan=None):
    """Renderiza a previa da montagem para um perfil usando o mesmo grafo de composicao.

    Preserva cortes de fonte, enquadramento por cena/perfil, slow-zoom, titulos,
    legendas e contornos de Motion (em 9:16), escalando a saida com numeros pares
    e mantendo o arquivo estritamente fora do historico de entregas/ZIP.
    """
    root = os.path.realpath(root)
    out_real = os.path.realpath(output_mp4_path)
    if not render_local.contained(root, out_real):
        raise render_local.InputFileError('caminho da previa fora da raiz do projeto')
    render_local.ensure_video_tools(root)

    tmp_parent = os.path.join(root, '.workspace', 'tmp')
    os.makedirs(tmp_parent, exist_ok=True)
    run_root = tempfile.mkdtemp(prefix='preview-render-', dir=tmp_parent)
    try:
        req_path = os.path.join(run_root, 'request.video-request.json')
        write_json(req_path, request_data)

        motion_path = None
        if motion_plan and motion_plan.get('effects'):
            motion_path = os.path.join(run_root, 'motion.motion-plan.json')
            write_json(motion_path, motion_plan)

        verdict = run_bridge_video_request(root, req_path, profile=profile_id, motion_plan_path=motion_path)
        if not verdict.get('ok'):
            raise render_local.RenderInputError(
                verdict.get('failureCode', 'VIDEO_REQUEST_INVALID'),
                verdict.get('subject'),
            )
        profiles = verdict['profiles']
        if not profiles or profiles[0].get('status') != 'compiled':
            p_err = profiles[0] if profiles else {}
            # Se Motion falhou apenas por geometria horizontal (ex: YouTube 16:9), recompila sem Motion
            if p_err.get('failureCode') == 'MOTION_LOCAL_UNSUPPORTED_GEOMETRY' and motion_path is not None:
                verdict = run_bridge_video_request(root, req_path, profile=profile_id, motion_plan_path=None)
                if not verdict.get('ok'):
                    raise render_local.RenderInputError(
                        verdict.get('failureCode', 'VIDEO_REQUEST_INVALID'), verdict.get('subject')
                    )
                profiles = verdict['profiles']
                p_err = profiles[0] if profiles else {}
            if p_err.get('status') != 'compiled':
                raise render_local.RenderInputError(
                    p_err.get('failureCode', 'PROFILE_COMPILE_FAILED'),
                    p_err.get('profileId') or profile_id,
                )

        profile = profiles[0]
        project = verdict['project']
        media = verdict['media']
        work_dir = os.path.join(run_root, 'docs')
        paths = write_working_documents(work_dir, profile, project)

        _, canonical_manifest_json = prepare_asset_manifest.build_asset_manifest_from_registry(
            root, paths['case'], paths['association'], media
        )
        write_text(paths['asset_manifest'], canonical_manifest_json)
        asset_manifest = json.loads(canonical_manifest_json)

        # Obter resolvedAssetBindings via ponte do caso (mesmo contrato de render_pipeline)
        bridge_verdict = render_pipeline.run_bridge_case(
            root,
            paths['case'],
            asset_manifest_path=paths['asset_manifest'],
            text_overlays_path=paths.get('overlays'),
            visual_style_path=paths.get('style'),
            plan_only=False,
        )
        # Se --assets / --asset-manifest ja trouxe resolvedAssetBindings
        # Nota: run_bridge_case exige --assets OU --asset-manifest, com ambos OK quando --asset-manifest
        if not bridge_verdict.get('ok'):
            raise render_local.RenderInputError(
                bridge_verdict.get('failureCode', 'CASE_INVALID'),
                bridge_verdict.get('subject'),
            )
        resolved_bindings = bridge_verdict['resolvedAssetBindings']
        resolved_overlays = bridge_verdict.get('resolvedTextOverlays', [])
        visual_style = bridge_verdict.get('visualStyle')

        inspected_by_id, source_abs_by_id, _, _ = render_pipeline.verify_manifest_assets(
            root, asset_manifest, resolved_bindings
        )

        orig_pkg = bridge_verdict['package']
        orig_out = orig_pkg['output']
        orig_w, orig_h, fps = int(orig_out['width']), int(orig_out['height']), int(orig_out['fps'])
        ratio = float(scale_factor) if (0.1 <= float(scale_factor) <= 1.0) else 0.5
        preview_w = max(2, int(round(orig_w * ratio / 2.0)) * 2)
        preview_h = max(2, int(round(orig_h * ratio / 2.0)) * 2)

        preview_pkg = json.loads(json.dumps(orig_pkg))
        preview_pkg['output']['width'] = preview_w
        preview_pkg['output']['height'] = preview_h

        framings_by_beat = {}
        asset_paths = []
        source_cuts = []
        for binding in resolved_bindings:
            beat_id = binding['beatId']
            asset_id = binding['assetId']
            asset_info = inspected_by_id[asset_id]
            framings_by_beat[beat_id] = render_local.resolve_scene_framing(
                asset_info, preview_w, preview_h, binding.get('framing'), beat_id=beat_id
            )
            asset_paths.append(source_abs_by_id[asset_id])
            source_cuts.append(binding.get('sourceStartMs', 0))

        srt_path = os.path.join(run_root, 'preview.srt')
        write_text(srt_path, render_local.build_srt(preview_pkg))

        title_srt_path = None
        if resolved_overlays:
            title_srt_content = render_local.build_title_srt(resolved_overlays)
            if title_srt_content:
                title_srt_path = os.path.join(run_root, 'preview-titles.srt')
                write_text(title_srt_path, title_srt_content)

        fs = render_local.fs_path
        motion_render = []
        if profile.get('motion'):
            for i, eff in enumerate(profile['motion']['effects']):
                png = os.path.join(run_root, f'.preview-motion-{i}.png')
                rect = (eff['region']['x'] * preview_w, eff['region']['y'] * preview_h,
                        eff['region']['w'] * preview_w, eff['region']['h'] * preview_h)
                hexcolor = eff['color'].lstrip('#')
                rgba = (int(hexcolor[0:2], 16), int(hexcolor[2:4], 16), int(hexcolor[4:6], 16), 255)
                scaled_thickness = max(1, round(eff['thickness'] * (preview_w / float(orig_w))))
                r002_pilot.write_outline_png(fs(png), rect, scaled_thickness, rgba, 0, preview_w, preview_h)
                motion_render.append({
                    'png': png,
                    'start': eff['absoluteStartMs'] / 1000.0,
                    'end': eff['absoluteEndMs'] / 1000.0,
                    'fadeIn': eff['resolvedFadeInMs'] / 1000.0,
                    'fadeOut': eff['resolvedFadeOutMs'] / 1000.0,
                })

        title_style = render_local.build_title_style(visual_style, preview_w, preview_h)
        staged_mp4 = os.path.join(run_root, 'preview-output.mp4')
        cmd = render_local.build_render_command(
            preview_pkg, asset_paths, srt_path, staged_mp4, preset,
            title_srt_path=title_srt_path, title_style=title_style,
            motion=motion_render, source_cuts=source_cuts,
            framings_by_beat=framings_by_beat,
        )
        try:
            res = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=render_local.RENDER_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            raise build_video.DeliveryError('geracao de previa excedeu o tempo limite')
        if res.returncode != 0:
            raise build_video.DeliveryError(
                f'geracao de previa falhou no FFmpeg: {res.stderr[-240:] if res.stderr else "erro"}'
            )

        duration_s = preview_pkg['output']['durationMs'] / 1000.0
        inspection = build_video.validate_mp4(
            staged_mp4, preview_w, preview_h, fps, duration_s,
            timeout=render_local.PROBE_TIMEOUT_SECONDS
        )
        os.makedirs(os.path.dirname(out_real), exist_ok=True)
        os.replace(fs(staged_mp4), fs(out_real))
        return {
            'status': 'completed',
            'profileId': profile_id,
            'width': preview_w,
            'height': preview_h,
            'sourceOutputWidth': orig_w,
            'sourceOutputHeight': orig_h,
            'fps': fps,
            'durationMs': preview_pkg['output']['durationMs'],
            'bytes': os.path.getsize(fs(out_real)),
            'sha256': render_local.sha256_file(out_real),
            'inspection': inspection,
            'framings': framings_by_beat,
        }
    finally:
        shutil.rmtree(render_local.fs_path(run_root, force=True), ignore_errors=True)


def failed_result(profile, error=None):
    return {
        'profileId': profile['profileId'],
        'caseId': profile['caseId'],
        'status': 'failed',
        'failureCode': profile.get('failureCode'),
        'errors': profile.get('errors', []),
        'error': error,
    }


DELIVERY_FIELDS = ('profileId', 'caseId', 'packageId', 'outputDir', 'deliveryManifest', 'artifacts', 'inspection', 'attemptId')
EXPORT_LOCK_NAME = '.produce-video-export.lock'


def _delivery_from_entry(entry):
    """Extrai a ultima entrega valida de um registro (formato novo ou indice v1)."""
    if not isinstance(entry, dict):
        return None
    if 'lastValidDelivery' in entry:
        valid = entry['lastValidDelivery']
        return valid if isinstance(valid, dict) and valid.get('status') == 'completed' else None
    if entry.get('status') == 'completed':
        delivery = {key: entry[key] for key in DELIVERY_FIELDS if key in entry}
        delivery['status'] = 'completed'
        return delivery
    return None


def _write_index_atomic(index_path, index):
    parent = os.path.dirname(index_path)
    fd, tmp = tempfile.mkstemp(prefix='.index-', suffix='.tmp', dir=parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(index, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        # No Windows o destino pode estar temporariamente preso por outro processo
        # (antivirus/indexador); retry curto, mesmo padrao da promocao de diretorio
        # em studio_templates._replace_dir_with_retry.
        for attempt in range(6):
            try:
                os.replace(tmp, index_path)
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.2 * (attempt + 1))
    except OSError:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _build_index(request_id, profiles):
    completed = sum(1 for entry in profiles if entry.get('lastValidDelivery'))
    return {
        'schemaVersion': 1,
        'requestId': request_id,
        'profileCount': len(profiles),
        'completedCount': completed,
        'overallStatus': 'completed' if profiles and completed == len(profiles) else 'partial',
        'profiles': profiles,
    }


def merge_index(output_dir, request_id, results):
    """Atualiza o indice separando a tentativa mais recente da ultima entrega valida.

    Le indices v1 existentes, valida o dono do destino, preserva a entrega valida
    anterior quando uma reexportacao falha e grava por substituicao atomica.
    """
    index_path = os.path.join(output_dir, 'index.json')
    prior = {}
    if os.path.isfile(index_path):
        try:
            with open(index_path, 'r', encoding='utf-8') as handle:
                previous = json.load(handle)
        except (OSError, ValueError):
            previous = {}
        owner = previous.get('requestId')
        if owner and owner != request_id:
            raise render_pipeline.DeliveryCollisionError(
                f"colisao de entrega: destino pertence ao pedido '{owner}' (diferente de '{request_id}')")
        for entry in previous.get('profiles', []):
            if isinstance(entry, dict) and 'profileId' in entry:
                prior[entry['profileId']] = entry
    merged = dict(prior)
    for result in results:
        profile_id = result['profileId']
        last_valid = _delivery_from_entry(prior.get(profile_id))
        if result.get('status') == 'completed':
            last_valid = {key: result[key] for key in DELIVERY_FIELDS if key in result}
            last_valid['status'] = 'completed'
        entry = {
            'profileId': profile_id,
            'caseId': result.get('caseId') or (prior.get(profile_id) or {}).get('caseId'),
            'status': 'completed' if last_valid else result.get('status'),
            'lastAttempt': result,
            'lastValidDelivery': last_valid,
        }
        source = last_valid if last_valid else result
        for key in ('packageId', 'outputDir', 'deliveryManifest', 'artifacts', 'inspection'):
            if key in source:
                entry[key] = source[key]
        merged[profile_id] = entry
    profiles = [merged[key] for key in sorted(merged)]
    index = _build_index(request_id, profiles)
    _write_index_atomic(index_path, index)
    return index


def reconcile_index_from_manifests(output_dir, request_id):
    """Reconstroi o indice a partir dos manifestos promovidos (fonte de verdade).

    Usado quando a atualizacao do indice falha apos um render concluido: cada
    subdiretorio com delivery-manifest.json valido volta a ser uma entrega valida.
    """
    profiles = []
    if os.path.isdir(output_dir):
        for name in sorted(os.listdir(output_dir)):
            manifest_path = os.path.join(output_dir, name, 'delivery-manifest.json')
            if not os.path.isfile(manifest_path):
                continue
            try:
                with open(manifest_path, 'r', encoding='utf-8') as handle:
                    manifest = json.load(handle)
            except (OSError, ValueError):
                continue
            artifacts = manifest.get('artifacts', {})
            output_rel = manifest.get('outputDir')
            delivery = {
                'profileId': name,
                'caseId': manifest.get('caseId'),
                'packageId': manifest.get('packageId'),
                'status': 'completed',
                'outputDir': output_rel,
                'deliveryManifest': f'{output_rel}/delivery-manifest.json' if output_rel else None,
                'artifacts': artifacts,
                'inspection': (artifacts.get('video') or {}).get('ffprobe'),
            }
            if manifest.get('attemptId'):
                delivery['attemptId'] = manifest['attemptId']
            entry = {
                'profileId': name,
                'caseId': manifest.get('caseId'),
                'status': 'completed',
                'lastAttempt': delivery,
                'lastValidDelivery': delivery,
            }
            for key in ('packageId', 'outputDir', 'deliveryManifest', 'artifacts', 'inspection'):
                entry[key] = delivery[key]
            profiles.append(entry)
    index = _build_index(request_id, profiles)
    _write_index_atomic(os.path.join(output_dir, 'index.json'), index)
    return index


def acquire_export_lock(output_dir, timeout=300):
    """Serializa exportacoes concorrentes para o mesmo destino (lock O_EXCL)."""
    lock_path = os.path.join(output_dir, EXPORT_LOCK_NAME)
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            os.close(fd)
            return lock_path
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise build_video.DeliveryError('exportacao concorrente no destino; lock ocupado')
            time.sleep(0.2)


def main(argv=None):
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, 'reconfigure'):
            try:
                _stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
    parser = argparse.ArgumentParser(description='Producao de video por entrada unica (VideoRequest v1)')
    parser.add_argument('--input', required=True, help='Pedido de video (*.video-request.json)')
    parser.add_argument('--plan-only', action='store_true', help='Apenas compila e exibe a previa, sem render nem gravacao')
    parser.add_argument('--output-dir', default=None, help='Diretorio final de entrega (um subdiretorio por perfil)')
    parser.add_argument('--profile', default=None, help='Restringe a exportacao a um perfil pedido')
    parser.add_argument('--motion-plan', default=None, help='Plano de motion (MotionPlan v1) com contorno por cena')
    parser.add_argument('--root', default=os.getcwd(), help='Raiz do projeto')
    parser.add_argument('--staging', default=None, help='Diretorio de staging exclusivo (opcional)')
    parser.add_argument('--preset', default='veryfast', help='Preset do FFmpeg')
    parser.add_argument('--attempt-id', default=None, help='Identificador da tentativa da fila (interno)')
    parser.add_argument('--fence-file', default=None, help='Arquivo de cerca/reserva da fila (interno)')
    parser.add_argument('--json', action='store_true', help='Emite um unico resultado JSON no stdout')
    args = parser.parse_args(argv)

    root = os.path.realpath(args.root)
    input_path = os.path.realpath(args.input)
    if not render_local.contained(root, input_path):
        print('Erro: caminho de --input fora da raiz do projeto', file=sys.stderr)
        return 2
    if not os.path.isfile(input_path):
        print('Erro: arquivo de pedido ausente', file=sys.stderr)
        return 2
    try:
        with open(input_path, 'r', encoding='utf-8') as handle:
            request = json.load(handle)
    except (OSError, ValueError):
        print('Erro: pedido ilegivel ou JSON invalido', file=sys.stderr)
        return 2
    if not isinstance(request, dict) or not isinstance(request.get('project'), str):
        print('Erro: pedido invalido (project ausente)', file=sys.stderr)
        return 2
    project_path = os.path.realpath(os.path.join(root, request['project']))
    if not render_local.contained(root, project_path) or not os.path.isfile(project_path):
        print('Erro: ProjectManifest do pedido ausente ou fora da raiz', file=sys.stderr)
        return 2

    motion_plan_input = None
    if args.motion_plan:
        motion_path = os.path.realpath(args.motion_plan)
        if not render_local.contained(root, motion_path) or not os.path.isfile(motion_path):
            print('Erro: plano de motion ausente ou fora da raiz', file=sys.stderr)
            return 2
        try:
            with open(motion_path, 'r', encoding='utf-8') as handle:
                motion_plan_input = json.load(handle)
        except (OSError, ValueError):
            print('Erro: plano de motion ilegivel ou JSON invalido', file=sys.stderr)
            return 2

    if not args.plan_only and not args.output_dir:
        print('Erro: informe --output-dir para exportar, ou use --plan-only', file=sys.stderr)
        return 2

    try:
        verdict = run_bridge_video_request(root, input_path, args.profile, args.motion_plan)
        if not verdict.get('ok'):
            raise render_local.RenderInputError(verdict.get('failureCode', 'VIDEO_REQUEST_INVALID'),
                                                verdict.get('subject'))
        profiles = verdict['profiles']
        media = verdict['media']
        project = verdict['project']
        request_id = verdict['requestId']

        if args.plan_only:
            payload = {
                'status': 'preview',
                'requestId': request_id,
                'media': media,
                'profiles': [preview_profile(profile) for profile in profiles],
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"Previa do pedido {request_id}:")
                for entry in payload['profiles']:
                    if entry['status'] != 'compiled':
                        print(f"  - {entry['profileId']}: FALHOU ({entry['failureCode']})")
                        continue
                    print(f"  - {entry['profileId']}: {entry['geometry']['width']}x{entry['geometry']['height']} "
                          f"@ {entry['fps']}fps, {entry['durationSeconds']}s")
                    for beat in entry['beats']:
                        if beat.get('sourceStartMs') is not None:
                            fonte = (f"fonte [{beat['sourceStartMs']}ms -> {beat['sourceEndMs']}ms]")
                        else:
                            fonte = 'fonte [imagem estatica]'
                        fr = beat.get('framing') or {'mode': 'fit'}
                        if fr.get('mode') == 'fill':
                            enq = f"enquadramento=Preencher(cx={fr['centerX']:.2f},cy={fr['centerY']:.2f},zoom={fr['zoomPercent']}%)"
                        else:
                            enq = 'enquadramento=Ajustar'
                        print(f"      {beat['beatId']} montagem [{beat['startMs']}ms -> {beat['endMs']}ms] "
                              f"{fonte} {enq} midia={beat['mediaId']} titulo={beat['title']}")
                    for warning in entry['warnings']:
                        print(f"      aviso: {warning['code']} ({warning['path']})")
                print(f"  Midias: {', '.join(item['id'] for item in media)}")
            return 0 if all(p['status'] == 'compiled' for p in profiles) else 3

        output_dir = os.path.realpath(args.output_dir)
        if not render_local.contained(root, output_dir):
            raise render_local.InputFileError('caminho de --output-dir fora da raiz do projeto')
        if output_dir == root:
            raise render_local.InputFileError('destino nao pode ser a raiz do projeto')
        for label, path in (('input', input_path), ('project', project_path)):
            if render_local.overlaps(output_dir, path):
                raise render_local.InputFileError(f'destino sobrepoe {label} da execucao')
        os.makedirs(output_dir, exist_ok=True)
        lock_path = acquire_export_lock(output_dir)

        parent = os.path.join(root, '.workspace', 'tmp')
        os.makedirs(parent, exist_ok=True)
        run_root = tempfile.mkdtemp(prefix='produce-video-', dir=parent)
        results = []
        try:
            for profile in profiles:
                if profile['status'] != 'compiled':
                    results.append(failed_result(profile))
                    continue
                try:
                    results.append(export_profile(root, profile, project, media, output_dir,
                                                  run_root, args.preset, args.staging,
                                                  motion_plan=motion_plan_input,
                                                  attempt_id=args.attempt_id,
                                                  fence_file=args.fence_file))
                except (build_video.DeliveryError, render_local.RenderInputError,
                        render_local.InputFileError, OSError, ValueError) as exc:
                    results.append(failed_result(profile, error=str(exc)))
            try:
                index = merge_index(output_dir, request_id, results)
            except OSError:
                index = reconcile_index_from_manifests(output_dir, request_id)
        finally:
            shutil.rmtree(run_root, ignore_errors=True)
            if os.path.exists(lock_path):
                try:
                    os.remove(lock_path)
                except OSError:
                    pass

        all_completed = all(entry['status'] == 'completed' for entry in results) and bool(results)
        payload = {
            'status': 'completed' if all_completed else 'partial',
            'requestId': request_id,
            'outputDir': rel(root, output_dir),
            'index': rel(root, os.path.join(output_dir, 'index.json')),
            'overallStatus': index['overallStatus'],
            'profiles': results,
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Entrega do pedido {request_id}: {payload['outputDir']}")
            for entry in results:
                if entry['status'] == 'completed':
                    print(f"  - {entry['profileId']}: concluido ({entry['deliveryManifest']})")
                else:
                    print(f"  - {entry['profileId']}: FALHOU ({entry.get('failureCode') or entry.get('error')})")
        return 0 if all_completed else 1

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


if __name__ == '__main__':
    raise SystemExit(main())