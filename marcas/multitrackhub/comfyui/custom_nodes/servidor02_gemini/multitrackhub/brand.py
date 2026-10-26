"""Multitrack Hub: identidade, arte quadrada e pacote isolados; nenhuma chamada Postiz."""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import uuid
from PIL import Image, UnidentifiedImageError
from .. import client
ASSETS=Path(__file__).parent/'assets'
BRAND='multitrackhub'
STANDARD='multitrackhub-quadrado-ia-v1'
INTEGRATIONS={'facebook':'cmvbss5fn0005msbhhbdy6ing','instagram':'cmvbsudg50007msbh2j4734i4'}
FIELDS=('campanha','tema','titulo','texto','legenda_facebook','legenda_instagram','direcao_visual','link_bio_confirmado','destino')


def caption(body, network, bio, destination):
    tail=[];blocks=[v.strip() for v in body.splitlines()]
    while blocks:
        if not blocks[-1]:blocks.pop()
        elif blocks[-1].startswith('#') or blocks[-1].endswith('?'):tail.insert(0,blocks.pop())
        else:break
    url='https://multitrackhub.com.br'+('/rateios' if destination=='rateios' else '')
    cta=('Conheça a Multitrack Hub: '+url+'\nAcesse pelo link da descrição.' if network=='facebook' else
         ('Conheça a seção Rateios pelo link na bio do @multitrackhub.' if destination=='rateios' else 'Conheça a Multitrack Hub pelo link na bio do @multitrackhub.') if bio else 'Conheça a Multitrack Hub: @multitrackhub.')
    # Corpo que já contém a chamada não precisa recebê-la duas vezes.
    if (network=='facebook' and url in body) or (network=='instagram' and ((bio and 'link na bio' in body.lower()) or (not bio and '@multitrackhub' in body))):return body.strip()
    return '\n\n'.join(v for v in ['\n'.join(blocks).strip(),cta,*tail] if v)


def prepare_brief(campanha,tema,titulo,texto,legenda_facebook,legenda_instagram,direcao_visual,link_bio_confirmado=False,destino='site',brand=BRAND):
    if brand!=BRAND:raise ValueError('Brief de outra marca não pertence ao workflow Multitrack Hub.')
    if not isinstance(campanha,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',campanha):raise ValueError('Campanha: slug de até64 caracteres, sem caminhos.')
    values={'tema':tema,'titulo':titulo,'texto':texto,'legenda_facebook':legenda_facebook,'legenda_instagram':legenda_instagram,'direcao_visual':direcao_visual}
    limits={'tema':60,'titulo':88,'texto':190,'legenda_facebook':1800,'legenda_instagram':1800,'direcao_visual':1800}
    for k,v in values.items():
        if not isinstance(v,str) or not v.strip() or len(v)>limits[k] or any(ord(c)<32 and c not in '\n\t' for c in v):raise ValueError('Campo inválido: '+k)
        if any(x in v.casefold() for x in ['marca salão','marcasalao']):raise ValueError('Conteúdo de outra marca no brief Multitrack Hub.')
        values[k]=v.strip()
    if type(link_bio_confirmado) is not bool or destino not in ('site','rateios'):raise ValueError('Confirmação da bio ou destino inválido.')
    if not link_bio_confirmado and 'link na bio' in legenda_instagram.lower():raise ValueError('Confirme o link externo antes de prometer acesso pela bio.')
    benefits=[v.strip() for v in re.split(r'[|\n]',texto) if v.strip()]
    if not 1<=len(benefits)<=3 or any(len(v)>62 for v in benefits):raise ValueError('Informe até3 tópicos, cada um até62 caracteres.')
    return {'brand':BRAND,'campanha':campanha,**values,'link_bio_confirmado':link_bio_confirmado,'destino':destino,'beneficios':benefits,'legendas':{n:caption(values['legenda_'+n],n,link_bio_confirmado,destino) for n in INTEGRATIONS}}


def checked(fields):
    return prepare_brief(**{k:fields[k] for k in FIELDS if k in fields},brand=fields.get('brand',BRAND))


def full_prompt(fields):
    b=checked(fields)
    return (ASSETS/'padrao-arte-integral.txt').read_text().format(tema=b['tema'],titulo=b['titulo'],beneficios=json.dumps(b['beneficios'],ensure_ascii=False),direcao_visual=b['direcao_visual'])


def prepare_image(image):
    if abs(image.width/image.height-1)>.02:raise ValueError('A arte precisa ser quadrada; não recortar uma peça com textos.')
    return image.convert('RGB').resize((1080,1080),Image.Resampling.LANCZOS)


def generate_artwork(fields,output_root,revision=1):
    if type(revision) is not int or not 1<=revision<=999:raise ValueError('Revisão entre1 e999.')
    b=checked(fields);prompt=full_prompt(b);reference=(ASSETS/'referencia-apresentacao.png').read_bytes();model=os.environ.get('GEMINI_IMAGE_MODEL','gemini-3.1-flash-image')
    signature=hashlib.sha256(json.dumps({'brand':BRAND,'prompt':prompt,'model':model,'reference':hashlib.sha256(reference).hexdigest(),'size':'2K','revision':revision},sort_keys=True).encode()).hexdigest()
    root=Path(output_root);folder=root/BRAND/'geracoes-ia'/b['campanha']/signature;meta_path=folder/'geracao.json';image_path=folder/'arte-original.png'
    if meta_path.exists():
        meta=json.loads(meta_path.read_text())
        if meta.get('status')!='complete' or meta.get('brand')!=BRAND or meta.get('signature')!=signature or not image_path.is_file() or hashlib.sha256(image_path.read_bytes()).hexdigest()!=meta.get('sha256'):raise ValueError('Geração anterior incerta ou inválida; inspecione antes de repetir a chamada paga.')
        with Image.open(image_path) as src:image=prepare_image(src)
        return image,{**meta,'reused':True}
    folder.mkdir(parents=True,exist_ok=True)
    with meta_path.open('x') as f:json.dump({'status':'submitting','brand':BRAND,'signature':signature},f)
    (folder/'prompt.txt').write_text(prompt+'\n')
    _,data=client.generate(prompt,'imagem','Gere UMA arte publicitária completa da Multitrack Hub, incluindo logo, textos e tópicos exatos, em português brasileiro. Use a referência de identidade musical.',reference=reference,aspect_ratio='1:1',image_size='2K')
    try:
        with Image.open(io.BytesIO(data)) as src:src.load();original=src.convert('RGB')
    except (OSError,UnidentifiedImageError,Image.DecompressionBombError):raise RuntimeError('Imagem inválida; nenhuma repetição automática.') from None
    original.save(image_path,'PNG')
    meta={'status':'received','brand':BRAND,'signature':signature,'model':model,'revision':revision,'native_size':list(original.size),'sha256':hashlib.sha256(image_path.read_bytes()).hexdigest(),'file':str(image_path.relative_to(root)),'reused':False}
    meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n');image=prepare_image(original);meta['status']='complete';meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    return image,meta


def export_bundle(fields,image,output_root,source):
    b=checked(fields)
    if source not in ('gemini','imagem_local'):raise ValueError('Origem inválida.')
    image=prepare_image(image);stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');bundle=f'{BRAND}/{b["campanha"]}/{stamp}-{uuid.uuid4().hex[:10]}'
    folder=Path(output_root)/bundle;folder.mkdir(parents=True,exist_ok=False);name='arte-compartilhada-quadrado.png';image.save(folder/name,'PNG',optimize=True)
    m={'schema_version':1,'brand':BRAND,'visual_standard':STANDARD,'campaign':b['campanha'],'bundle':bundle,'created_at':datetime.now(timezone.utc).isoformat(),'status':'prepared','review_required':True,'publication_authorized':False,'background_source':source,'bio_link_confirmed':b['link_bio_confirmado'],'brief':{k:b[k] for k in ['tema','titulo','texto','direcao_visual','destino']},'images':[{'network':'compartilhado','format':'quadrado','file':name,'width':1080,'height':1080,'sha256':hashlib.sha256((folder/name).read_bytes()).hexdigest(),'cta':'Conheça a Multitrack Hub'}],'captions':{},'postiz':{'mode':'draft_only','integrations':INTEGRATIONS.copy(),'preferred_feed_format':'quadrado','media_by_network':{n:name for n in INTEGRATIONS},'media_uploaded':False,'drafts_created':False,'story_requires_separate_request':True},'sources':['https://github.com/swnsolucoes/Multitrack/blob/main/artifacts/multitrack-hub/src/index.css','https://github.com/swnsolucoes/Multitrack/blob/main/docs/contexto/LOGO-MULTITRACKHUB.md']}
    for n,text in b['legendas'].items():
        p=folder/f'legenda-{n}.txt';p.write_text(text+'\n');m['captions'][n]={'file':p.name,'text':text,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    (folder/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');(folder/'README.md').write_text('# Multitrack Hub — pacote para revisão\n\nUma imagem compartilhada, duas legendas. Não publicado, não agendado, sem uploads nem rascunhos criados. Revisão de logo, ortografia, fatos, canais, legendas e mídia antes de integrar ao Postiz. Não usar canais/arquivos Marca Salão.\n')
    return m
