"""Entrada Python do adaptador HyperFrames (HF-001, F6).

Compila um pedido VideoRequest v1 pelo render_bridge (mesma ponte do
produce_video), seleciona o perfil e delega ao adaptador Node
(renderers/hyperframes/adapter/hf_adapter.mjs) via wrapper com caches
confinados. O veredito JSON do adaptador e repassado; a verificacao ffprobe
(VIDEO CLEAN: 0 faixas de audio) acontece dentro do adaptador.

Uso (a partir da raiz do checkout):
    python tools/render_hyperframes.py --input <pedido.video-request.json> \
        [--profile <id>] [--tenant <id>] [--quality draft|looks|delivery] \
        [--workdir <dir>] [--out <mp4>] [--root <raiz>] [--skip-render]

Sem --workdir, usa <raiz>/.workspace/tmp/hf001/<pedido>/<perfil>/.
Sem --out, grava <workdir>/video-<perfil>.mp4.
"""

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import produce_video
import render_local

ADAPTER_TIMEOUT_SECONDS = 900


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


def main(argv=None):
    parser = argparse.ArgumentParser(description='Render de video pelo motor HyperFrames (adaptador HF-001)')
    parser.add_argument('--input', required=True, help='Pedido VideoRequest v1 (*.video-request.json)')
    parser.add_argument('--root', default=os.getcwd(), help='Raiz do projeto')
    parser.add_argument('--profile', default=None, help='Perfil de saida (padrao: primeiro compilado)')
    parser.add_argument('--tenant', default=None, help='Tenant (padrao: id do ProjectManifest)')
    parser.add_argument('--quality', default='draft', choices=['draft', 'looks', 'delivery'])
    parser.add_argument('--workdir', default=None, help='Diretorio de trabalho do adaptador')
    parser.add_argument('--out', default=None, help='MP4 de saida')
    parser.add_argument('--skip-render', action='store_true', help='Compoe e roda o check sem renderizar')
    args = parser.parse_args(argv)

    root = os.path.realpath(args.root)
    input_path = os.path.realpath(args.input)
    try:
        request = load_request(root, input_path)
        tenant = resolve_tenant(root, request, args.tenant)
        verdict = produce_video.run_bridge_video_request(root, input_path, args.profile)
        if not verdict.get('ok'):
            print(json.dumps({
                'ok': False,
                'failureCode': 'COMPILE_FAILED',
                'profiles': [produce_video.preview_profile(p) for p in verdict.get('profiles', [])],
            }, ensure_ascii=False, indent=2))
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
            out_path = os.path.realpath(args.out or os.path.join(
                workdir, f"video-{profile['profileId']}.mp4"))
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
    except produce_video.build_video.DeliveryError as exc:
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
    if res.returncode == 0 and verdict_json and verdict_json.get('ok'):
        print(json.dumps(verdict_json, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        'ok': False,
        'failureCode': (verdict_json or {}).get('failureCode', 'ADAPTER_FAILED'),
        'adapterExitCode': res.returncode,
        'adapterStderr': (res.stderr or '').strip()[-4000:],
        'adapterVerdict': verdict_json,
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
