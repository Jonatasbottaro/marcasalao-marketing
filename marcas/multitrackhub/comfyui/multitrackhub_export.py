#!/usr/bin/env python3
"""Executa ComfyUI local e exporta pacote. Não acessa Gemini/Postiz diretamente."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from PIL import Image, UnidentifiedImageError

BASE = 'http://127.0.0.1:8188'
ROOT = Path(__file__).resolve().parent


def request(path, data=None, headers=None, binary=False):
    req = urllib.request.Request(BASE + path, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read(32 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'ComfyUI HTTP {exc.code}; confira a fila antes de repetir.') from None
    if len(raw) > 32 * 1024 * 1024:
        raise ValueError('Arquivo maior que 32 MiB.')
    return raw if binary else json.loads(raw)


def safe_relative(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9_./-]{1,240}', value):
        raise ValueError('Caminho inválido no manifesto.')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or str(path) != value:
        raise ValueError('Caminho fora do pacote.')
    return path


def download_bundle(manifest, output, fetch_image):
    if manifest.get('schema_version') != 1 or manifest.get('brand') != 'multitrackhub':
        raise ValueError('Manifesto não é Multitrack Hub v1.')
    integrations = {'facebook': 'cmvbss5fn0005msbhhbdy6ing', 'instagram': 'cmvbsudg50007msbh2j4734i4'}
    sizes = {'quadrado': (1080, 1080)}
    postiz = manifest.get('postiz', {})
    if (manifest.get('status') != 'prepared' or manifest.get('review_required') is not True
            or manifest.get('publication_authorized') is not False or postiz.get('mode') != 'draft_only'
            or postiz.get('media_uploaded') is not False or postiz.get('drafts_created') is not False
            or postiz.get('integrations') != integrations):
        raise ValueError('Pacote não está no estado preparado/revisão ou tem canais inválidos.')
    shared = manifest.get('visual_standard') == 'multitrackhub-quadrado-ia-v1'
    if not isinstance(manifest.get('images'), list) or len(manifest['images']) != (1 if shared else 6) or set(manifest.get('captions', {})) != set(integrations):
        raise ValueError('Pacote incompleto: confira imagens e duas legendas.')
    if shared:
        item = manifest['images'][0]
        if (item.get('network') != 'compartilhado' or item.get('format') != 'quadrado'
                or postiz.get('media_by_network') != {n: item.get('file') for n in integrations}):
            raise ValueError('Arte compartilhada ou destinos inválidos.')
    if not shared:
        raise ValueError('Padrão Multitrack Hub inválido.')
    seen = set()
    for item in manifest['images']:
        pair = item.get('network'), item.get('format')
        if pair in seen or pair[0] not in (('compartilhado',) if shared else integrations) or pair[1] not in sizes or (item.get('width'), item.get('height')) != sizes[pair[1]]:
            raise ValueError('Rede, formato ou dimensões inválidas no manifesto.')
        seen.add(pair)
    bundle = safe_relative(manifest['bundle'])
    if bundle.parts[0] != 'multitrackhub' or len(bundle.parts) != 3:
        raise ValueError('Pasta de pacote inválida.')
    target = Path(output).resolve() / str(bundle)
    if target.exists():
        raise FileExistsError('Pacote já exportado; não sobrescrever nem gerar novamente.')
    names = set()
    for item in list(manifest['images']) + list(manifest['captions'].values()):
        relative = safe_relative(item['file'])
        if len(relative.parts) != 1 or item['file'] in names or item['file'] in ('manifest.json', 'README.md'):
            raise ValueError('Nome inválido ou repetido no pacote.')
        names.add(item['file'])
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name('.partial-' + uuid.uuid4().hex)
    partial.mkdir()
    for item in manifest['images']:
        png = fetch_image(item)
        if hashlib.sha256(png).hexdigest() != item['sha256']:
            raise ValueError('Hash da imagem não confere; pacote não concluído.')
        if png[:8] != b'\x89PNG\r\n\x1a\n' or len(png) < 24 or struct.unpack('>II', png[16:24]) != (item['width'], item['height']):
            raise ValueError('Dimensões/PNG não conferem; pacote não concluído.')
        try:
            with Image.open(io.BytesIO(png)) as image:
                if image.format != 'PNG' or image.mode != 'RGB' or image.size != (item['width'], item['height']):
                    raise ValueError('Modo/formato da imagem não confere.')
                image.verify()
            with Image.open(io.BytesIO(png)) as image:
                image.load()
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
            raise ValueError('PNG inválido ou truncado; pacote não concluído.') from exc
        (partial / item['file']).write_bytes(png)
    for item in manifest['captions'].values():
        text = (item['text'] + '\n').encode('utf-8')
        if hashlib.sha256(text).hexdigest() != item['sha256']:
            raise ValueError('Hash da legenda não confere.')
        (partial / item['file']).write_bytes(text)
    (partial / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (partial / 'README.md').write_text('# Pacote Multitrack Hub\n\nPreparado para revisão. Não publicado, não agendado e sem rascunhos criados.\n\nConsulte HERMES-POSTIZ-MULTITRACKHUB.md junto ao exportador. Use a mesma imagem nas duas redes, com as legendas correspondentes. O manifesto não é payload de publicação.\n', encoding='utf-8')
    partial.rename(target)
    return target


def upload_background(path):
    raw = path.read_bytes()
    if len(raw) > 20 * 1024 * 1024 or path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
        raise ValueError('Imagem local: PNG/JPEG/WebP de até 20 MiB.')
    name = 'multitrackhub-' + uuid.uuid4().hex + path.suffix.lower()
    boundary = 'ms' + uuid.uuid4().hex
    payload = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + raw + f'\r\n--{boundary}--\r\n'.encode())
    response = request('/upload/image', payload, {'Content-Type': f'multipart/form-data; boundary={boundary}'})
    result = response['name']
    if response.get('subfolder'):
        result = response['subfolder'] + '/' + result
    safe_relative(result)
    return result


def main():
    parser=argparse.ArgumentParser(description='Multitrack Hub: uma arte quadrada e duas legendas, sem Postiz.')
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--brief',type=Path)
    group.add_argument('--resume',type=Path)
    parser.add_argument('--state',type=Path)
    parser.add_argument('--square-art',type=Path,help='Arte completa já existente; sem Gemini.')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.resume:
        state=json.loads(args.resume.read_text());ident=state.get('prompt_id')
        if not ident:raise RuntimeError('Estado sem prompt_id: consultar fila/histórico antes de repetir.')
    else:
        if not args.state:parser.error('--state obrigatório e deve ser novo.')
        brief=json.loads(args.brief.read_text())
        sys.path.insert(0,str(ROOT/'custom_nodes'))
        from servidor02_gemini.multitrackhub.brand import prepare_brief
        prepare_brief(**brief)
        args.state.parent.mkdir(parents=True,exist_ok=True)
        with args.state.open('x') as f:json.dump({'status':'submitting','brand':'multitrackhub','warning':'Não repetir antes de conferir fila/histórico.'},f)
        template='11-multitrackhub-reutilizar-arte.api.json' if args.square_art else '10-multitrackhub-criar-anuncio.api.json'
        prompt=json.loads((ROOT/'workflows'/template).read_text());prompt['1']['inputs']=brief
        if args.square_art:prompt['2']['inputs']['image']=upload_background(args.square_art)
        response=request('/prompt',json.dumps({'prompt':prompt}).encode(),{'Content-Type':'application/json'});ident=response['prompt_id']
        args.state.write_text(json.dumps({'prompt_id':ident,'status':'queued','brand':'multitrackhub'},indent=2)+'\n')
    if not isinstance(ident,str) or not re.fullmatch(r'[a-f0-9-]{36}',ident):raise ValueError('prompt_id inválido.')
    print(json.dumps({'prompt_id':ident,'status':'consultando','brand':'multitrackhub'}),flush=True)
    for attempt in range(900):
        history=request('/history/'+ident)
        if ident in history:break
        time.sleep(1)
    else:raise RuntimeError('Ainda sem conclusão. Usar --resume no mesmo estado; não repetir geração.')
    record=history[ident]
    if record['status']['status_str']!='success':
        errors=[d.get('exception_message','')[:500] for kind,d in record['status'].get('messages',[]) if kind=='execution_error']
        raise RuntimeError('Workflow Multitrack Hub falhou. '+' '.join(errors))
    manifest=json.loads(record['outputs']['3']['text'][0])
    def fetch(item):return request('/view?'+urllib.parse.urlencode({'filename':item['file'],'subfolder':manifest['bundle'],'type':'output'}),binary=True)
    package=download_bundle(manifest,args.output,fetch)
    print(json.dumps({'prompt_id':ident,'status':'prepared','brand':'multitrackhub','package':str(package),'postiz_modified':False},ensure_ascii=False),flush=True)


if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,OSError,KeyError) as exc:
        print(str(exc),file=sys.stderr);sys.exit(1)
