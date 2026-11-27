"""Entrada Python do adaptador HyperFrames (HF-001, F6/F8).

Compila um pedido VideoRequest v1 pelo render_bridge (mesma ponte do
produce_video), seleciona o perfil e delega ao adaptador Node
(renderers/hyperframes/adapter/hf_adapter.mjs) via wrapper com caches
confinados. O veredito JSON do adaptador e repassado; a verificacao ffprobe
(VIDEO CLEAN: 0 faixas de audio) acontece dentro do adaptador.

Com --output-dir, promove a entrega no mesmo contrato da fila do Studio:
<output-dir>/<perfil>/delivery-manifest.json com artefatos verificados
(video + narracao, captionsMode clean), cerca da fila conferida antes da
promocao, indice reconciliado e resultado JSON compativel com produce_video.

Uso (a partir da raiz do checkout):
    python tools/render_hyperframes.py --input <pedido.video-request.json> \
        [--profile <id>] [--tenant <id>] [--quality draft|looks|delivery] \
        [--workdir <dir>] [--out <mp4|png>] [--root <raiz>] [--skip-render] \
        [--still] [--output-dir <dir>] [--staging <dir>] [--attempt-id <id>] \
        [--fence-file <arquivo>] [--json]

Sem --workdir, usa <raiz>/.workspace/tmp/hf001/<pedido>/<perfil>/.
Sem --out, grava <workdir>/video-<perfil>.mp4.
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
import produce_video
import render_local

ADAPTER_TIMEOUT_SECONDS = 900
ADAPTER_ID = 'hyperframes'


def load_request(root, input_path):
    if not render_local.contained(root, input_path) or not os.path.isfile(input_path):
        raise render_local.InputFileError('pedido ausente ou fora da raiz do projeto')
    with open(input_path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def resolve_tenant(root, request, override):
    if override:
        return override
    project_path = os.path.realpath(os.path.join(root, request.get('project', '')))
    if not render_local.contained(root, project_path) or not os.path.isfile(project_path):
        raise render_local.InputFileError('ProjectManifest do pedido ausente ou fora da raiz')
    with open(project_path, 'r', encoding='utf-8') as handle:
        project = json.load(handle)
    tenant_id = project.get('id')
    if not tenant_id or not os.path.isdir(os.path.join(root, 'tenants', tenant_id)):
        raise render_local.InputFileError(f'tenant nao resolvido a partir do manifesto: {tenant_id!r}')
    return tenant_id


def select_profile(verdict, profile_id):
    profiles = verdict.get('profiles') or []
    if profile_id:
        for profile in profiles:
            if profile.get('profileId') == profile_id:
                return profile
        raise render_local.InputFileError(f'perfil nao compilado ou inexistente: {profile_id}')
    for profile in profiles:
        if profile.get('status') == 'compiled':
            return profile
    raise render_local.InputFileError('nenhum perfil compilado no veredito da ponte')


def run_adapter(root, args, profile_path, workdir, out_path, tenant):
    wrapper = os.path.join(root, 'renderers', 'hyperframes', 'scripts', 'hf-adapter.sh')
    if not os.path.isfile(wrapper):
        raise render_local.InputFileError('wrapper do adaptador ausente: renderers/hyperframes/scripts/hf-adapter.sh')
    cmd = [
        'bash', render_local.rel(root, wrapper),
        '--profile-json', profile_path,
        '--root', root,
        '--tenant', tenant,
        '--workdir', workdir,
        '--quality', args.quality,
    ]
    if getattr(args, 'still', False):
        cmd.append('--still')
    if out_path:
        cmd.extend(['--out', out_path])
    if args.skip_render:
        cmd.append('--skip-render')
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             encoding='utf-8', errors='replace',
                             timeout=ADAPTER_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise produce_video.build_video.DeliveryError('adaptador excedeu o tempo limite')
    return res


def verify_attempt_fence(fence_file, attempt_id=None):
    """Mesma semantica do produce_video: cerca revogada/ausente aborta a promocao."""
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


def export_delivery(root, request, profile, adapter_verdict, output_dir, staging_dir,
                    attempt_id=None, fence_file=None, input_path=None):
    """Promove a renderizacao do adaptador como entrega da fila do Studio.

    Espelha o contrato do render_pipeline: staging exclusivo, artefatos com
    SHA-256, delivery-manifest.json (captionsMode clean, renderer hyperframes),
    cerca conferida antes da promocao, backup/rollback atomico e indice
    reconciliado a partir dos manifestos.
    """
    profile_id = profile['profileId']
    plan = profile['plan']
    package = profile['package']
    package_id = package['packageId']
    profile_output = os.path.join(output_dir, profile_id)
    fs = render_local.fs_path
    backup_dir = None
    staging_created = False

    if staging_dir is None:
        parent = os.path.join(root, '.workspace', 'tmp')
        os.makedirs(fs(parent), exist_ok=True)
        staging_dir = tempfile.mkdtemp(prefix='hf-delivery-', dir=parent)
        staging_created = True
    else:
        os.makedirs(fs(staging_dir), exist_ok=True)
        staging_dir = tempfile.mkdtemp(prefix='hf-delivery-', dir=staging_dir)
        staging_created = False

    names = {
        'video': f'{package_id}-primary-output.mp4',
        'narration': f'{package_id}-narration-script.txt',
        'manifest': 'delivery-manifest.json',
    }
    staging_paths = {key: os.path.join(staging_dir, names[key]) for key in names}
    dests = {key: os.path.join(profile_output, names[key]) for key in names}
    try:
        rendered = adapter_verdict.get('outputPath')
        if not rendered or not os.path.isfile(fs(rendered)):
            raise build_video.DeliveryError('adaptador concluiu sem MP4 verificavel')
        narration_src = adapter_verdict.get('narrationFile')
        if not narration_src or not os.path.isfile(fs(narration_src)):
            raise build_video.DeliveryError('adaptador concluiu sem roteiro de narracao TXT')
        shutil.copyfile(fs(rendered), fs(staging_paths['video']))
        shutil.copyfile(fs(narration_src), fs(staging_paths['narration']))
        with open(fs(staging_paths['narration']), 'rb') as handle:
            narration_bytes = handle.read()
        if not narration_bytes.decode('utf-8').strip():
            raise build_video.DeliveryError('narracao vazia ou nao UTF-8')

        duration_s = plan['durationMs'] / 1000.0
        inspection = build_video.validate_mp4(
            staging_paths['video'], plan['geometry']['width'], plan['geometry']['height'],
            plan['fps'], duration_s, timeout=render_local.PROBE_TIMEOUT_SECONDS)
        if inspection.get('audioStreams'):
            raise build_video.DeliveryError('VIDEO CLEAN violado: MP4 com faixa de audio')

        command = (
            'python tools/render_hyperframes.py'
            + (f' --input {render_local.rel(root, input_path)}' if input_path else '')
            + f' --profile {profile_id} --output-dir {render_local.rel(root, output_dir)}'
        )
        manifest = {
            'schemaVersion': 1,
            'adapter': ADAPTER_ID,
            'renderer': {'adapter': ADAPTER_ID, 'engine': 'hyperframes'},
            'caseId': profile['caseId'],
            'packageId': package_id,
            'projectId': package['projectId'],
            'compositionId': package['compositionId'],
            'outputPlanId': package['outputPlanId'],
            'beatPlanId': package['beatPlanId'],
            'profileId': profile_id,
            'command': command,
            'outputDir': render_local.rel(root, profile_output),
            'captionsMode': 'clean',
            'artifacts': {
                'video': {
                    'id': 'video',
                    'path': render_local.rel(root, dests['video']),
                    'sha256': render_local.sha256_file(staging_paths['video']),
                    'bytes': os.path.getsize(fs(staging_paths['video'])),
                    'ffprobe': inspection,
                },
                'narration': {
                    'id': 'narration',
                    'path': render_local.rel(root, dests['narration']),
                    'sha256': render_local.sha256_file(staging_paths['narration']),
                    'bytes': os.path.getsize(fs(staging_paths['narration'])),
                },
            },
        }
        if attempt_id:
            manifest['attemptId'] = attempt_id
        with open(fs(staging_paths['manifest']), 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
            handle.write('\n')

        backup_dir = os.path.join(staging_dir, '.backup')
        os.makedirs(fs(backup_dir), exist_ok=True)
        lock = render_local.acquire_promotion_lock(profile_output)
        try:
            verify_attempt_fence(fence_file, attempt_id)
            os.makedirs(fs(profile_output), exist_ok=True)
            render_local.promote_with_backup(staging_paths, dests, backup_dir)
        finally:
            if os.path.exists(fs(lock)):
                try:
                    os.remove(fs(lock))
                except OSError:
                    pass

        index = produce_video.reconcile_index_from_manifests(output_dir, request.get('id', 'pedido'))
        result = {
            'profileId': profile_id,
            'caseId': profile['caseId'],
            'packageId': package_id,
            'status': 'completed',
            'outputDir': render_local.rel(root, profile_output),
            'deliveryManifest': render_local.rel(root, dests['manifest']),
            'artifacts': {key: render_local.rel(root, dests[key]) for key in names},
            'inspection': inspection,
            'captionsMode': 'clean',
            'renderer': {'adapter': ADAPTER_ID},
        }
        if attempt_id:
            result['attemptId'] = attempt_id
        return result, index
    finally:
        if backup_dir:
            shutil.rmtree(fs(backup_dir, force=True), ignore_errors=True)
        if staging_created:
            shutil.rmtree(fs(staging_dir, force=True), ignore_errors=True)


def main(argv=None):
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, 'reconfigure'):
            try:
                _stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
    parser = argparse.ArgumentParser(description='Render de video pelo motor HyperFrames (adaptador HF-001)')
    parser.add_argument('--input', required=True, help='Pedido VideoRequest v1 (*.video-request.json)')
    parser.add_argument('--root', default=os.getcwd(), help='Raiz do projeto')
    parser.add_argument('--profile', default=None, help='Perfil de saida (padrao: primeiro compilado)')
    parser.add_argument('--tenant', default=None, help='Tenant (padrao: id do ProjectManifest)')
    parser.add_argument('--quality', default='draft', choices=['draft', 'looks', 'delivery'])
    parser.add_argument('--workdir', default=None, help='Diretorio de trabalho do adaptador')
    parser.add_argument('--out', default=None, help='MP4 de saida')
    parser.add_argument('--skip-render', action='store_true', help='Compoe e roda o check sem renderizar')
    parser.add_argument('--still', action='store_true',
                        help='Captura um quadro PNG (F10) em vez de renderizar MP4; exige --out *.png')
    parser.add_argument('--output-dir', default=None,
                        help='Diretorio final de entrega da fila (um subdiretorio por perfil)')
    parser.add_argument('--staging', default=None, help='Diretorio de staging exclusivo (interno da fila)')
    parser.add_argument('--attempt-id', default=None, help='Identificador da tentativa da fila (interno)')
    parser.add_argument('--fence-file', default=None, help='Arquivo de cerca/reserva da fila (interno)')
    parser.add_argument('--clean', action='store_true',
                        help='Aceito por compatibilidade: o motor HyperFrames e sempre VIDEO CLEAN')
    parser.add_argument('--json', action='store_true', help='Emite um unico resultado JSON no stdout')
    args = parser.parse_args(argv)

    if args.skip_render and args.output_dir:
        print('Erro: --skip-render nao combina com --output-dir', file=sys.stderr)
        return 2
    if args.still and args.output_dir:
        print('Erro: --still nao combina com --output-dir; conjuntos de cards usam tools/render_hyperframes_still.py', file=sys.stderr)
        return 2

    root = os.path.realpath(args.root)
    input_path = os.path.realpath(args.input)
    try:
        request = load_request(root, input_path)
        tenant = resolve_tenant(root, request, args.tenant)
        verdict = produce_video.run_bridge_video_request(root, input_path, args.profile)
        if not verdict.get('ok'):
            payload = {
                'status': 'error',
                'failureCode': 'COMPILE_FAILED',
                'error': 'COMPILE_FAILED: pedido rejeitado pela ponte de compilacao',
                'profiles': [produce_video.preview_profile(p) for p in verdict.get('profiles', [])],
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 3
        profile = select_profile(verdict, args.profile)
        request_id = request.get('id', 'pedido')
        workdir = os.path.realpath(args.workdir or os.path.join(
            root, '.workspace', 'tmp', 'hf001', request_id, profile['profileId']))
        if not render_local.contained(root, workdir):
            raise render_local.InputFileError('workdir fora da raiz do projeto')
        os.makedirs(workdir, exist_ok=True)
        out_path = None
        if not args.skip_render:
            default_name = (f"still-{profile['profileId']}.png" if args.still
                            else f"video-{profile['profileId']}.mp4")
            out_path = os.path.realpath(args.out or os.path.join(workdir, default_name))
            if args.still and not out_path.endswith('.png'):
                raise render_local.InputFileError('saida --still deve ser um arquivo .png')
            if not render_local.contained(root, out_path):
                raise render_local.InputFileError('saida fora da raiz do projeto')
        profile_path = os.path.join(workdir, 'profile.compiled.json')
        with open(profile_path, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(profile, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        res = run_adapter(root, args, profile_path, workdir, out_path, tenant)
    except render_local.InputFileError as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 2
    except build_video.DeliveryError as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f'Erro: entrada invalida ({type(exc).__name__})', file=sys.stderr)
        return 2

    lines = [line for line in (res.stdout or '').strip().splitlines() if line.strip()]
    verdict_json = None
    if lines:
        try:
            verdict_json = json.loads(lines[-1])
        except ValueError:
            verdict_json = None
    if res.returncode != 0 or not verdict_json or not verdict_json.get('ok'):
        failure_code = (verdict_json or {}).get('failureCode', 'ADAPTER_FAILED')
        violations = (verdict_json or {}).get('violations') or []
        error_text = f'{failure_code}: adaptador HyperFrames falhou (codigo {res.returncode})'
        if violations:
            terms = ', '.join(
                str(v.get('term') or v) for v in violations if isinstance(v, dict)
            )
            if terms:
                error_text += f'; violacoes: {terms}'
        print(json.dumps({
            'ok': False,
            'status': 'error',
            'failureCode': failure_code,
            'error': error_text,
            'profiles': [{
                'profileId': profile['profileId'],
                'status': 'failed',
                'failureCode': failure_code,
                'error': error_text,
            }],
            'adapterExitCode': res.returncode,
            'adapterStderr': (res.stderr or '').strip()[-4000:],
            'adapterVerdict': verdict_json,
        }, ensure_ascii=False, indent=2))
        return 1

    if args.output_dir:
        output_dir = os.path.realpath(args.output_dir)
        if not render_local.contained(root, output_dir):
            print('Erro: caminho de --output-dir fora da raiz do projeto', file=sys.stderr)
            return 2
        if output_dir == root:
            print('Erro: destino nao pode ser a raiz do projeto', file=sys.stderr)
            return 2
        try:
            result, index = export_delivery(
                root, request, profile, verdict_json, output_dir, args.staging,
                attempt_id=args.attempt_id, fence_file=args.fence_file,
                input_path=input_path)
        except build_video.DeliveryError as exc:
            print(f'Erro: {exc}', file=sys.stderr)
            return 1
        payload = {
            'status': 'completed',
            'requestId': request_id,
            'outputDir': render_local.rel(root, output_dir),
            'index': render_local.rel(root, os.path.join(output_dir, 'index.json')),
            'overallStatus': index['overallStatus'],
            'profiles': [result],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(json.dumps(verdict_json, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
