"""Arte integral Gemini, por rede/proporção, com retomada de saídas concluídas."""
import hashlib
import io
import json
import os
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from . import client
from .brand import ASSETS, FORMATS, INTEGRATIONS, prepare_brief

RATIOS = {'quadrado':'1:1', 'vertical':'4:5', 'stories':'9:16'}
FIELDS = ('campanha','tema','titulo','texto','legenda_facebook','legenda_instagram','direcao_visual','link_bio_confirmado')


def full_prompt(fields, network, fmt):
    brief = prepare_brief(**{k: fields[k] for k in FIELDS})
    if network not in (*INTEGRATIONS, 'compartilhado') or fmt not in RATIOS or (network == 'compartilhado' and fmt != 'quadrado'):
        raise ValueError('Rede ou formato inválido.')
    template = (ASSETS / 'padrao-arte-integral.txt').read_text()
    return template.format(proporcao=RATIOS[fmt], formato=fmt,
                           tema=brief['tema'], titulo=brief['titulo'],
                           beneficios=json.dumps(brief['beneficios'], ensure_ascii=False),
                           direcao_visual=brief['direcao_visual'], cta='Conheça o Marca Salão' if network == 'compartilhado' else brief['cta'][network],
                           endereco='marcasalao.com.br' if network in ('facebook','compartilhado') else '@marcasalao')


def prepare_image(image, fmt):
    if fmt not in FORMATS:
        raise ValueError('Formato inválido.')
    w,h = FORMATS[fmt]
    if abs((image.width/image.height)/(w/h)-1) > .02:
        raise ValueError('A IA devolveu proporção incorreta. Arte preservada; não recortar textos. Ajuste o pedido antes de tentar novamente.')
    # Somente escala; nunca refazer logo/tipografia nem recortar a peça completa.
    return image.convert('RGB').resize((w,h), Image.Resampling.LANCZOS)


def generate_artwork(fields, network, fmt, output_root, revision=1):
    if type(revision) is not int or not 1 <= revision <= 999:
        raise ValueError('Revisão deve ser um inteiro entre 1 e 999.')
    brief = prepare_brief(**{k:fields[k] for k in FIELDS})
    prompt = full_prompt(brief, network, fmt)
    reference = (ASSETS/'referencia-financeiro.png').read_bytes()
    model = os.environ.get('GEMINI_IMAGE_MODEL','gemini-3.1-flash-image')
    signature = hashlib.sha256(json.dumps({'prompt':prompt,'model':model,'reference':hashlib.sha256(reference).hexdigest(),'size':'2K','revision':revision},sort_keys=True).encode()).hexdigest()
    folder = Path(output_root)/'marcasalao'/'geracoes-ia'/brief['campanha']/signature
    image_path, meta_path = folder/'arte-original.png', folder/'geracao.json'
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get('status') != 'complete' or meta.get('signature') != signature or not image_path.is_file() or hashlib.sha256(image_path.read_bytes()).hexdigest() != meta.get('sha256'):
            raise ValueError('Geração anterior incompleta ou com hash inválido. Confira a saída preservada antes de repetir uma chamada paga.')
        with Image.open(image_path) as source:
            image = prepare_image(source, fmt)
        return image, {**meta,'reused':True}
    folder.mkdir(parents=True,exist_ok=True)
    # Reserva exclusiva impede duas requisições simultâneas para a mesma arte.
    with meta_path.open('x') as f:
        json.dump({'status':'submitting','signature':signature,'warning':'Não repetir antes de conferir o estado.'},f)
    (folder/'prompt.txt').write_text(prompt+'\n')
    text, data = client.generate(prompt,'imagem',
                                'Produza UMA arte publicitária completa com logo, título, benefícios e chamada exatamente especificados. Português brasileiro. Use a referência de identidade e acabamento. Não devolver apenas o cenário.',
                                reference=reference, aspect_ratio=RATIOS[fmt], image_size='2K')
    try:
        with Image.open(io.BytesIO(data)) as source:
            source.load()
            original = source.convert('RGB')
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError):
        raise RuntimeError('Imagem integral Gemini inválida; nenhuma repetição automática.') from None
    original.save(image_path,'PNG')
    meta = {'status':'received','signature':signature,'network':network,'format':fmt,
            'model':model,'revision':revision,'native_size':list(original.size),'sha256':hashlib.sha256(image_path.read_bytes()).hexdigest(),
            'file':str(image_path.relative_to(output_root)), 'reused':False}
    meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    image = prepare_image(original, fmt)
    meta['status']='complete'
    meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    return image, meta
