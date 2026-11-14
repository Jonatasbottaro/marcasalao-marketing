"""Adaptador de render local de prova do CreativeExecutionPackage v1.

Consome o pacote tecnico validado e uma associacao explicita de assets
locais por beat, produz MP4 H.264/yuv420p SEM audio, SRT UTF-8, narracao em
TXT e relatorio JSON do render real, inspeciona com FFprobe antes de
concluir e promove a entrega de forma transacional: qualquer falha de
render, inspecao ou promocao preserva a entrega anterior completa.

O relatorio registra os caminhos relativos FINAIS dos artefatos promovidos,
com hashes e tamanhos calculados pelos bytes preparados em staging. O
staging e exclusivo por execucao, validado antes de qualquer escrita, e a
limpeza recursiva alcanca somente a pasta criada pelo proprio render. A
promocao para um mesmo destino e exclusiva por lock, com diagnostico claro
em disputa; se a restauracao falhar, o backup permanece para diagnostico.

A validacao do pacote e da associacao reutiliza o nucleo puro da platform
(validateLocalRenderInput) atraves da ponte tools/render_bridge.mjs; a
execucao da ferramenta de video acontece somente nesta camada de ferramentas.
Nenhum fornecedor, nenhuma rede, nenhuma publicacao, nenhum Temporal.

Recorte inicial: vertical 9:16 a 30 fps, dimensoes pares, movimento
'none'/'slow-zoom', transicao de entrada 'none'/'cut', saida 'cut'/'fade'
(fade somente no ultimo beat). Fora do recorte: diagnostico claro, sem render.

Exit codes: 0 entrega promovida; 1 falha de render/inspecao/promocao/asset;
2 uso, caminho ou JSON invalido; 3 pacote ou associacao invalidos.
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
import srt_validate

ADAPTER_ID = 'local-proof-render'
FADE_OUT_SECONDS = 0.5
RENDER_TIMEOUT_SECONDS = 300
BRIDGE_TIMEOUT_SECONDS = 60
PROBE_TIMEOUT_SECONDS = 30
VERSION_TIMEOUT_SECONDS = 15
PROMOTION_LOCK_NAME = '.local-render-promotion.lock'
SUBTITLE_STYLE = (
    'Fontname=Arial,Fontsize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,'
    'BackColour=&H80000000,Bold=1,Outline=2,Shadow=1,Alignment=2,MarginV=60'
)
TITLE_STYLE = (
    'PlayResX=1080,PlayResY=1920,Fontname=Arial,Fontsize=42,PrimaryColour=&H00FFFFFF,'
    'OutlineColour=&H00000000,BackColour=&H80000000,Bold=1,Outline=2,Shadow=1,'
    'Alignment=6,MarginV=160'
)
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp')


def hex_to_ass_color(hex_str: str) -> str:
    """Converte cor hexadecimal (#RRGGBB) para o formato ASS (&H00BBGGRR)."""
    cleaned = hex_str.strip().lstrip('#')
    if len(cleaned) == 6:
        r, g, b = cleaned[0:2], cleaned[2:4], cleaned[4:6]
        return f'&H00{b.upper()}{g.upper()}{r.upper()}'
    return '&H00FFFFFF'


def build_title_style(visual_style: dict | None = None) -> str:
    """Gera o estilo ASS para titulos superiores baseado em VisualStyle v1 ou padrao."""
    if not visual_style:
        return TITLE_STYLE
    title = visual_style.get('title', {})
    text_color = title.get('textColor', '#FFFFFF')
    outline_color = title.get('outlineColor', '#000000')
    font_size = title.get('fontSize', 42)
    margin_top = title.get('marginTop', 160)
    margin_h = title.get('marginHorizontal', 60)

    ass_primary = hex_to_ass_color(text_color)
    ass_outline = hex_to_ass_color(outline_color)

    return (
        'PlayResX=1080,PlayResY=1920,Fontname=Arial,'
        f'Fontsize={font_size},'
        f'PrimaryColour={ass_primary},'
        f'OutlineColour={ass_outline},'
        'BackColour=&H80000000,'
        'Bold=1,Outline=2,Shadow=1,Alignment=6,'
        f'MarginV={margin_top},'
        f'MarginL={margin_h},'
        f'MarginR={margin_h}'
    )


class RenderInputError(Exception):
    """Pacote ou associacao reprovados pelo nucleo; codigo estavel."""

    def __init__(self, code, subject=None):
        super().__init__(code)
        self.code = code
        self.subject = subject


class InputFileError(Exception):
    """Uso, caminho ou arquivo de entrada invalido."""


def fs_path(path, force=False):
    """Normaliza caminhos locais no Windows com \\\\?\\ acima de 247 chars (ou force=True)."""
    value = str(path)
    if os.name != 'nt' or value.startswith('\\\\?\\'):
        return value
    abs_path = os.path.abspath(value)
    if not force and len(abs_path) < 248:
        return value
    if abs_path.startswith('\\\\'):
        return '\\\\?\\UNC\\' + abs_path.lstrip('\\')
    return '\\\\?\\' + abs_path


def contained(root, path):
    return r002_pilot.contained(root, path)


def sha256_file(path):
    return r002_pilot.sha256_file(fs_path(path))


def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, '/')


def overlaps(a, b):
    """True quando um caminho e o outro ou esta dentro dele (realpath)."""
    a_real = os.path.realpath(a)
    b_real = os.path.realpath(b)
    return a_real == b_real or a_real.startswith(b_real + os.sep) or b_real.startswith(a_real + os.sep)


def ensure_video_tools(root):
    """PATH do processo apenas: usa o PATH atual ou .workspace/tools/ffmpeg."""
    if shutil.which('ffmpeg') and shutil.which('ffprobe'):
        return
    candidate = os.path.join(root, '.workspace', 'tools', 'ffmpeg')
    names = ('ffmpeg.exe', 'ffprobe.exe') if os.name == 'nt' else ('ffmpeg', 'ffprobe')
    if all(os.path.isfile(os.path.join(candidate, name)) for name in names):
        os.environ['PATH'] = candidate + os.pathsep + os.environ.get('PATH', '')
        return
    raise build_video.DeliveryError(
        'ffmpeg/ffprobe nao encontrados; exponha no PATH ou em .workspace/tools/ffmpeg'
    )


def tool_version(binary):
    try:
        res = subprocess.run([binary, '-version'], capture_output=True, text=True,
                             timeout=VERSION_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return 'desconhecida'
    if res.returncode != 0:
        return 'desconhecida'
    return res.stdout.splitlines()[0].strip()


def run_bridge(root, package_path, assets_path):
    node = shutil.which('node')
    if not node:
        raise InputFileError('node nao encontrado no PATH')
    dist_module = os.path.join(root, 'platform', 'dist', 'src', 'validate-local-render-input.js')
    if not os.path.isfile(dist_module):
        raise InputFileError('build da platform ausente; execute npm run build em platform/')
    bridge = os.path.join(root, 'tools', 'render_bridge.mjs')
    try:
        res = subprocess.run([node, bridge, package_path, assets_path],
                             capture_output=True, text=True,
                             timeout=BRIDGE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise build_video.DeliveryError('ponte de validacao excedeu o tempo limite')
    if res.returncode == 2:
        raise InputFileError('arquivo de entrada ilegivel ou JSON invalido')
    if res.returncode not in (0, 3):
        raise build_video.DeliveryError('ponte de validacao falhou de forma inesperada')
    try:
        return json.loads(res.stdout)
    except ValueError:
        raise build_video.DeliveryError('veredito da ponte ilegivel')


def probe_asset(root, path):
    """Sondagem FFprobe com timeout; exige stream de video decodificavel.

    O exit code do ffprobe nao prova legibilidade (pode ser 0 com streams
    vazios para lixo binario); com -loop 1 um asset ilegivel faria o render
    girar sem falhar.
    """
    try:
        res = subprocess.run(
            [build_video.get_ffprobe(), '-v', 'error', '-show_streams', '-show_format',
             '-of', 'json', str(path)],
            capture_output=True, text=True, timeout=PROBE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise build_video.DeliveryError(
            f'inspecao previa excedeu o tempo limite: {rel(root, path)}')
    if res.returncode != 0:
        raise build_video.DeliveryError(f'asset ilegivel pela inspecao previa: {rel(root, path)}')
    try:
        info = json.loads(res.stdout)
    except ValueError:
        raise build_video.DeliveryError(f'asset ilegivel pela inspecao previa: {rel(root, path)}')
    video_streams = [s for s in info.get('streams', []) if s.get('codec_type') == 'video']
    if not video_streams or not video_streams[0].get('width') or not video_streams[0].get('height'):
        raise build_video.DeliveryError(f'asset ilegivel pela inspecao previa: {rel(root, path)}')
    return info


def prepare_staging(root, output_dir, package_path, assets_path, staging_arg):
    """Staging exclusivo da execucao, validado antes de qualquer escrita.

    Devolve (staging_dir, created_by_us). Rejeita sobreposicao com a raiz,
    com os arquivos de entrada e com a pasta de entrega. Sem --staging, cria
    pasta unica em .workspace/tmp; com --staging, exige pasta nova ou vazia.
    """
    if staging_arg:
        staging = os.path.realpath(staging_arg)
        if not contained(root, staging):
            raise InputFileError('caminho de staging fora da raiz do projeto')
        if staging == os.path.realpath(root):
            raise InputFileError('staging nao pode ser a raiz do projeto')
        if os.path.realpath(root).startswith(staging + os.sep):
            raise InputFileError('staging nao pode conter a raiz do projeto')
        for label, path in (('package', package_path), ('assets', assets_path),
                            ('output', output_dir)):
            if overlaps(staging, path):
                raise InputFileError(f'staging sobrepoe {label} da execucao')
        if os.path.exists(staging):
            if not os.path.isdir(staging) or os.listdir(staging):
                raise InputFileError('staging informado ja existe e nao esta vazio')
            return staging, False
        os.makedirs(staging)
        return staging, True
    parent = os.path.join(root, '.workspace', 'tmp')
    os.makedirs(parent, exist_ok=True)
    staging = tempfile.mkdtemp(prefix='local-render-staging-', dir=parent)
    return staging, True


def acquire_promotion_lock(output_dir):
    """Exclusao de promocao por destino; disputa recebe diagnostico claro."""
    os.makedirs(fs_path(output_dir), exist_ok=True)
    lock = fs_path(os.path.join(output_dir, PROMOTION_LOCK_NAME))
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise build_video.DeliveryError(
            f'promocao concorrente para o mesmo destino; lock presente: {PROMOTION_LOCK_NAME}')
    with os.fdopen(handle, 'w') as stream:
        stream.write('local-render-promotion\n')
    return lock


def srt_timestamp(ms):
    seconds, millis = divmod(int(ms), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}'


def build_srt(package):
    blocks = []
    for step in package['timeline']:
        text = step.get('onScreenText')
        if not text:
            continue
        blocks.append(
            f"{len(blocks) + 1}\n"
            f"{srt_timestamp(step['startMs'])} --> {srt_timestamp(step['endMs'])}\n"
            f"{text}"
        )
    if not blocks:
        raise build_video.DeliveryError('pacote sem textos de tela; legenda vazia')
    return '\n\n'.join(blocks) + '\n'


def build_title_srt(resolved_overlays):
    blocks = []
    for item in resolved_overlays:
        text = item.get('text', '').strip()
        if not text:
            continue
        blocks.append(
            f"{len(blocks) + 1}\n"
            f"{srt_timestamp(item['startMs'])} --> {srt_timestamp(item['endMs'])}\n"
            f"{text}"
        )
    if not blocks:
        return ''
    return '\n\n'.join(blocks) + '\n'


def build_narration(package):
    lines = [
        f"Roteiro de narracao - {package['packageId']}",
        'Video sem audio; texto para ferramenta externa, organizado por cena e tempos.',
        '',
    ]
    found = False
    for step in package['timeline']:
        text = step.get('narrationText')
        if not text:
            continue
        found = True
        lines.append(
            f"[{srt_timestamp(step['startMs'])} --> {srt_timestamp(step['endMs'])}] {step['beatId']}"
        )
        lines.append(text)
        lines.append('')
    if not found:
        raise build_video.DeliveryError('pacote sem textos de narracao')
    return '\n'.join(lines).rstrip('\n') + '\n'


def build_filter_graph(package, srt_path, title_srt_path=None, title_style=None, motion_effects=None):
    output = package['output']
    width, height, fps = output['width'], output['height'], output['fps']
    total_s = output['durationMs'] / 1000.0
    chains = []
    labels = []
    for index, step in enumerate(package['timeline']):
        if step['motionIntent'] == 'slow-zoom':
            duration_s = step['durationMs'] / 1000.0
            # Zoom central 1.00 -> 1.10: scale animado (eval=frame) + crop fixo.
            # As expressoes w/h do crop nao aceitam t, e o zoompan custa minutos
            # em 1080x1920; esta forma e valida e rapida.
            chains.append(
                f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},"
                f"scale=w='{width}*(1+0.10*t/{duration_s:.3f})':"
                f"h='{height}*(1+0.10*t/{duration_s:.3f})':eval=frame,"
                f"crop={width}:{height}:(iw-{width})/2:(ih-{height})/2[v{index}]"
            )
        else:
            chains.append(
                f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}[v{index}]"
            )
        labels.append(f'[v{index}]')
    chains.append(''.join(labels) + f'concat=n={len(labels)}:v=1:a=0[cat]')
    last_label = '[cat]'
    if package['timeline'][-1]['transitionOut'] == 'fade':
        start = max(0.0, total_s - FADE_OUT_SECONDS)
        chains.append(f'[cat]fade=t=out:st={start:.3f}:d={FADE_OUT_SECONDS:.3f}[faded]')
        last_label = '[faded]'

    # Contorno de motion sobre o quadro enquadrado, ANTES de titulos e legenda,
    # com entrada/saida suaves (alpha) dentro da janela absoluta do efeito.
    for i, me in enumerate(motion_effects or []):
        ol = f'ol{i}'
        fade_out_start = max(0.0, me['end'] - me['fadeOut'])
        chains.append(
            f"[{me['input_index']}:v]format=rgba,"
            f"fade=t=in:st={me['start']:.3f}:d={me['fadeIn']:.3f}:alpha=1,"
            f"fade=t=out:st={fade_out_start:.3f}:d={me['fadeOut']:.3f}:alpha=1[{ol}]"
        )
        chains.append(
            f"{last_label}[{ol}]overlay=0:0:enable='between(t,{me['start']:.3f},{me['end']:.3f})'[vm{i}]"
        )
        last_label = f'[vm{i}]'

    if title_srt_path and os.path.exists(title_srt_path) and os.path.getsize(title_srt_path) > 0:
        style_to_use = title_style or TITLE_STYLE
        clean_title_srt = title_srt_path.replace('\\', '/').replace(':', '\\:')
        chains.append(f"{last_label}subtitles='{clean_title_srt}':force_style='{style_to_use}'[vtitles]")
        last_label = '[vtitles]'

    clean_srt = srt_path.replace('\\', '/').replace(':', '\\:')
    chains.append(f"{last_label}subtitles='{clean_srt}':force_style='{SUBTITLE_STYLE}'[vfinal]")
    return ';'.join(chains)


def build_render_command(package, asset_paths, srt_path, video_path, preset, title_srt_path=None, title_style=None, motion=None):
    output = package['output']
    fps = output['fps']
    total_s = output['durationMs'] / 1000.0
    cmd = [build_video.get_ffmpeg(), '-y']
    for step, asset_path in zip(package['timeline'], asset_paths):
        duration_s = step['durationMs'] / 1000.0
        extension = os.path.splitext(asset_path)[1].lower()
        if extension in IMAGE_EXTENSIONS:
            cmd += ['-loop', '1', '-framerate', str(fps), '-t', f'{duration_s:.3f}', '-i', asset_path]
        else:
            cmd += ['-t', f'{duration_s:.3f}', '-i', asset_path]
    motion_effects = []
    for i, m in enumerate(motion or []):
        input_index = len(package['timeline']) + i
        cmd += ['-loop', '1', '-framerate', str(fps), '-t', f'{total_s:.3f}', '-i', m['png']]
        motion_effects.append({
            'input_index': input_index, 'start': m['start'], 'end': m['end'],
            'fadeIn': m['fadeIn'], 'fadeOut': m['fadeOut'],
        })
    cmd += ['-filter_complex', build_filter_graph(package, srt_path, title_srt_path=title_srt_path, title_style=title_style, motion_effects=motion_effects), '-map', '[vfinal]']
    cmd += ['-an', '-c:v', 'libx264', '-preset', preset, '-pix_fmt', 'yuv420p',
            '-t', f'{total_s:.3f}', video_path]
    return cmd


def artifact_names(package):
    names = {}
    for artifact in package['expectedArtifacts']:
        if artifact['kind'] == 'primary-output':
            names['video'] = artifact['logicalName'] + '.mp4'
        elif artifact['kind'] == 'captions':
            names['srt'] = artifact['logicalName']
        elif artifact['kind'] == 'narration-script':
            names['narration'] = artifact['logicalName']
        elif artifact['kind'] == 'execution-report':
            names['report'] = artifact['logicalName']
    if len(names) != 4:
        raise build_video.DeliveryError('pacote sem os quatro artefatos esperados')
    return names


def write_text(path, text):
    with open(fs_path(path), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)


def promote_with_backup(staging_paths, dests, backup_dir):
    """Promove tudo ou restaura a entrega anterior completa em qualquer falha.

    Se a propria restauracao falhar, o backup permanece intacto para
    diagnostico e o erro informa onde ele esta.
    """
    os.makedirs(fs_path(backup_dir), exist_ok=True)
    backups = {}
    for name, dest in dests.items():
        if os.path.exists(fs_path(dest)):
            backup = os.path.join(backup_dir, os.path.basename(dest))
            shutil.copyfile(fs_path(dest), fs_path(backup))
            backups[name] = backup
    promoted = []
    try:
        for name, dest in dests.items():
            os.makedirs(fs_path(os.path.dirname(dest)), exist_ok=True)
            os.replace(fs_path(staging_paths[name]), fs_path(dest))
            promoted.append(name)
    except OSError:
        try:
            for name in promoted:
                if name in backups:
                    os.replace(fs_path(backups[name]), fs_path(dests[name]))
                else:
                    os.remove(fs_path(dests[name]))
        except OSError:
            raise build_video.DeliveryError(
                f'restauracao falhou; backup preservado para diagnostico em {backup_dir}')
        raise build_video.DeliveryError('promocao falhou; entrega anterior preservada')


def run_render(package_path, assets_path, output_dir, root, staging_dir, preset='veryfast'):
    root = os.path.realpath(root)
    for label, path in (('package', package_path), ('assets', assets_path),
                        ('output', output_dir)):
        if not contained(root, path):
            raise InputFileError(f'caminho de {label} fora da raiz do projeto')
    for label, path in (('package', package_path), ('assets', assets_path)):
        if not os.path.isfile(path):
            raise InputFileError(f'arquivo de {label} ausente')

    staging, staging_created = prepare_staging(
        root, output_dir, package_path, assets_path, staging_dir)

    ensure_video_tools(root)
    verdict = run_bridge(root, package_path, assets_path)
    if not verdict.get('ok'):
        raise RenderInputError(verdict.get('failureCode', 'ASSOCIATION_INVALID'),
                               verdict.get('subject'))
    package = verdict['package']
    association = verdict['association']

    by_beat = {binding['beatId']: binding['path'] for binding in association['assets']}
    asset_paths = []
    for step in package['timeline']:
        relative = by_beat[step['beatId']]
        absolute = os.path.join(root, relative)
        if not contained(root, absolute) or not os.path.isfile(absolute):
            raise build_video.DeliveryError(f'asset ausente ou fora da raiz: {relative}')
        probe_asset(root, absolute)
        asset_paths.append(absolute)

    names = artifact_names(package)
    staging_paths = {key: os.path.join(staging, names[key]) for key in names}

    write_text(staging_paths['srt'], build_srt(package))
    write_text(staging_paths['narration'], build_narration(package))

    cmd = build_render_command(package, asset_paths, staging_paths['srt'],
                               staging_paths['video'], preset)
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=RENDER_TIMEOUT_SECONDS)
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
        timeout=PROBE_TIMEOUT_SECONDS)
    srt_errors = srt_validate.validate_srt_file(fs_path(staging_paths['srt']), duration_s)
    if srt_errors:
        raise build_video.DeliveryError('SRT invalido: ' + '; '.join(srt_errors))
    with open(fs_path(staging_paths['narration']), 'rb') as handle:
        narration_bytes = handle.read()
    if not narration_bytes.decode('utf-8').strip():
        raise build_video.DeliveryError('narracao vazia ou nao UTF-8')

    dests = {key: os.path.join(output_dir, names[key]) for key in names}
    command = (
        'python tools/render_local.py'
        f' --package {rel(root, package_path)}'
        f' --assets {rel(root, assets_path)}'
        f' --output-dir {rel(root, output_dir)}'
    )
    report = {
        'schemaVersion': 1,
        'adapter': ADAPTER_ID,
        'status': 'completed',
        'packageId': package['packageId'],
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
        'assets': [
            {'beatId': step['beatId'], 'path': rel(root, path), 'sha256': sha256_file(path)}
            for step, path in zip(package['timeline'], asset_paths)
        ],
        'artifacts': [
            {
                'id': key,
                'kind': kind,
                'path': rel(root, dests[key]),
                'sha256': sha256_file(staging_paths[key]),
                'bytes': os.path.getsize(fs_path(staging_paths[key])),
            }
            for key, kind in (('video', 'primary-output'), ('srt', 'captions'),
                              ('narration', 'narration-script'))
        ],
        'tools': {
            'ffmpeg': tool_version(build_video.get_ffmpeg()),
            'ffprobe': tool_version(build_video.get_ffprobe()),
        },
        'command': command,
    }
    write_text(staging_paths['report'], json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    backup_dir = os.path.join(staging, '.backup')
    lock = acquire_promotion_lock(output_dir)
    try:
        promote_with_backup(staging_paths, dests, backup_dir)
    finally:
        os.remove(lock)
    shutil.rmtree(fs_path(backup_dir, force=True), ignore_errors=True)
    if staging_created:
        shutil.rmtree(fs_path(staging, force=True), ignore_errors=True)

    return {
        'adapter': ADAPTER_ID,
        'status': 'completed',
        'packageId': package['packageId'],
        'outputDir': rel(root, output_dir),
        'artifacts': {key: rel(root, dests[key]) for key in names},
        'inspection': inspection,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Render local de prova do CreativeExecutionPackage (video sem audio)')
    parser.add_argument('--package', required=True)
    parser.add_argument('--assets', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--root', default=os.getcwd())
    parser.add_argument('--staging', default=None)
    parser.add_argument('--preset', default='veryfast')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        summary = run_render(args.package, args.assets, args.output_dir, args.root,
                             args.staging, preset=args.preset)
    except RenderInputError as exc:
        subject = f': {exc.subject}' if exc.subject else ''
        print(f'Erro: entrada invalida ({exc.code}{subject})', file=sys.stderr)
        return 3
    except InputFileError as exc:
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
        print(f"Entrega promovida: {summary['outputDir']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
