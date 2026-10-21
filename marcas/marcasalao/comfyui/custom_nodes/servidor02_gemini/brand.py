"""Composição local Marca Salão. Nenhuma rede, credencial ou publicação."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid
from PIL import Image, ImageDraw, ImageFont, ImageOps

ASSETS = Path(__file__).parent / 'assets'
FONTS = Path('/usr/share/fonts/truetype/dejavu')
TEAL, MINT, PAPER = '#073f40', '#c8efe1', '#f6faf7'
FORMATS = {'quadrado': (1080, 1080), 'vertical': (1080, 1350), 'stories': (1080, 1920)}
INTEGRATIONS = {'facebook': 'cmvbegwql0001msbhvdpjy0in', 'instagram': 'cmvbeq3100003msbhihu2dm4z'}


def font(size, bold=False):
    return ImageFont.truetype(str(FONTS / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')), size)


def lines(text, face, width):
    result, current = [], ''
    for word in text.split():
        if face.getlength(word) > width:
            raise ValueError('Há uma palavra longa demais para a arte; reduza o texto.')
        candidate = (current + ' ' + word).strip()
        if face.getlength(candidate) > width:
            result.append(current)
            current = word
        else:
            current = candidate
    if current:
        result.append(current)
    return result


def fitted(text, maximum, minimum, count, bold=False):
    for size in range(maximum, minimum - 1, -2):
        face = font(size, bold)
        try:
            wrapped = lines(text, face, 936)
        except ValueError:
            continue
        if len(wrapped) <= count:
            return face, wrapped, size
    raise ValueError('O texto não cabe no template; reduza-o antes de gerar imagem.')


def prepare_brief(campanha, tema, titulo, texto, legenda_facebook, legenda_instagram,
                  direcao_visual, link_bio_confirmado=False):
    if not isinstance(campanha, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', campanha):
        raise ValueError('Campanha: use até 64 letras minúsculas, números e hífens.')
    values = {'tema': tema, 'titulo': titulo, 'texto': texto,
              'legenda_facebook': legenda_facebook, 'legenda_instagram': legenda_instagram,
              'direcao_visual': direcao_visual}
    limits = {'tema': 48, 'titulo': 88, 'texto': 160, 'legenda_facebook': 1800,
              'legenda_instagram': 1800, 'direcao_visual': 1800}
    for key, value in values.items():
        if not isinstance(value, str) or not value.strip() or len(value) > limits[key]:
            raise ValueError(f'Campo {key}: preencha até {limits[key]} caracteres.')
        if any(ord(c) < 32 and c not in '\n\t' for c in value):
            raise ValueError(f'Campo {key} contém caracteres de controle.')
        values[key] = ' '.join(value.split()) if key in ('tema', 'titulo', 'texto') else value.strip()
    fitted(values['tema'].upper(), 22, 20, 1, True)
    fitted(values['titulo'], 76, 56, 3, True)
    fitted(values['texto'], 31, 28, 3)
    if type(link_bio_confirmado) is not bool:
        raise ValueError('Confirmação do link na bio deve ser booleana.')
    if not link_bio_confirmado and 'link na bio' in values['legenda_instagram'].lower():
        raise ValueError('Confirme o link da bio antes de usar essa chamada na legenda.')
    fb_cta = 'Acesse o link da descrição'
    ig_cta = 'Acesse o link na bio' if link_bio_confirmado else 'Conheça o Marca Salão'
    return {'campanha': campanha, **values, 'link_bio_confirmado': link_bio_confirmado,
            'legendas': {'facebook': values['legenda_facebook'] + '\n\nAcesse pelo link da descrição: https://marcasalao.com.br',
                         'instagram': values['legenda_instagram'] + ('\n\nConheça o Marca Salão pelo link na bio.' if link_bio_confirmado else '\n\nConheça o Marca Salão: @marcasalao.')},
            'cta': {'facebook': fb_cta, 'instagram': ig_cta}}


def image_prompt(brief):
    return ('Crie apenas a imagem de apoio para uma composição editorial do Marca Salão, '
            'sistema de agendamento e gestão para salões de beleza. Tema: ' + brief['tema'] +
            '. Direção visual: ' + brief['direcao_visual'] +
            '. Paleta verde-petróleo profundo, menta claro e branco. Composição elegante, '
            'luz suave, assunto principal centralizado para recorte horizontal e vertical. '
            'Sem texto, letras, logotipos, marcas, números, telas de software ou interfaces inventadas. '
            'Não inclua a chamada comercial: textos e logo serão aplicados localmente depois.')


def render(brief, background, fmt, network):
    w, h = FORMATS[fmt]
    story = fmt == 'stories'
    image = Image.new('RGB', (w, h), PAPER)
    draw = ImageDraw.Draw(image)
    top = 170 if story else 60
    logo = Image.open(ASSETS / 'marcasalao-logo.png').convert('RGBA')
    logo.thumbnail((96, 96), Image.Resampling.LANCZOS)
    image.paste(logo, (72, top), logo)
    draw.text((192, top + 6), 'Marca Salão', font=font(36, True), fill=TEAL)
    draw.text((192, top + 54), 'Agendamento e gestão', font=font(22), fill=TEAL)
    y = top + 148
    face, wrapped, size = fitted(brief['tema'].upper(), 22, 20, 1, True)
    draw.text((72, y), wrapped[0], font=face, fill='#267469')
    y += 52
    face, wrapped, size = fitted(brief['titulo'], 76, 56, 3, True)
    for line in wrapped:
        draw.text((68, y), line, font=face, fill=TEAL)
        y += size + 14
    y += 28
    face, wrapped, size = fitted(brief['texto'], 31, 28, 3)
    for line in wrapped:
        draw.text((72, y), line, font=face, fill=TEAL)
        y += size + 11
    y += 52
    footer = h - (270 if story else 164)
    bottom = footer - 52
    if bottom - y < 120:
        raise ValueError('O conjunto título/texto não deixa espaço para a imagem; reduza o texto.')
    art = ImageOps.fit(background.convert('RGB'), (936, bottom - y), method=Image.Resampling.LANCZOS)
    mask = Image.new('L', art.size)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, art.width, art.height), radius=32, fill=255)
    image.paste(art, (72, y), mask)
    draw.rectangle((72, footer, 140, footer + 5), fill='#267469')
    draw.text((72, footer + 27), brief['cta'][network], font=font(30, True), fill=TEAL)
    draw.text((72, footer + 77), 'marcasalao.com.br' if network == 'facebook' else '@marcasalao', font=font(24), fill='#267469')
    return image


def export_bundle(brief, background, output_root, source):
    brief = prepare_brief(**{k: brief[k] for k in ('campanha', 'tema', 'titulo', 'texto', 'legenda_facebook', 'legenda_instagram', 'direcao_visual', 'link_bio_confirmado')})
    if source not in ('gemini', 'imagem_local'):
        raise ValueError('Origem de imagem inválida.')
    # Renderizar tudo antes de criar o pacote: entrada inválida não deixa pacote publicável.
    rendered = [(network, fmt, render(brief, background, fmt, network)) for network in INTEGRATIONS for fmt in FORMATS]
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    bundle = f'marcasalao/{brief["campanha"]}/{stamp}-{uuid.uuid4().hex[:10]}'
    directory = Path(output_root) / bundle
    directory.mkdir(parents=True, exist_ok=False)
    manifest = {'schema_version': 1, 'brand': 'marcasalao', 'campaign': brief['campanha'],
                'bundle': bundle, 'created_at': datetime.now(timezone.utc).isoformat(),
                'status': 'prepared', 'review_required': True, 'publication_authorized': False,
                'background_source': source, 'bio_link_confirmed': brief['link_bio_confirmado'],
                'brief': {k: brief[k] for k in ('tema', 'titulo', 'texto', 'direcao_visual')},
                'images': [], 'captions': {},
                'postiz': {'mode': 'draft_only', 'integrations': INTEGRATIONS.copy(),
                           'preferred_feed_format': 'vertical', 'media_uploaded': False,
                           'drafts_created': False, 'story_requires_separate_request': True},
                'sources': ['https://marcasalao.com.br', 'https://marcasalao.com.br/icons/icon-512x512.png']}
    for network, fmt, image in rendered:
        name = f'arte-{network}-{fmt}.png'
        path = directory / name
        image.save(path, format='PNG', optimize=True)
        manifest['images'].append({'network': network, 'format': fmt, 'file': name,
                                   'width': image.width, 'height': image.height,
                                   'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'cta': brief['cta'][network]})
    for network, caption in brief['legendas'].items():
        path = directory / f'legenda-{network}.txt'
        path.write_text(caption + '\n', encoding='utf-8')
        manifest['captions'][network] = {'file': path.name, 'text': caption,
                                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    (directory / 'README.md').write_text(
        '# Marca Salão — pacote preparado\n\nNão publicado, não agendado e sem rascunhos criados. '
        'Revisão humana obrigatória de imagem, alegações, legendas e link da bio.\n\n'
        'Escolha apenas UMA variante por rede para cada post; quadrado e vertical são alternativas. '
        'Stories requer pedido específico; não criar adesivo de link nem simular botão clicável.\n\n'
        'Hermes: consulte manifest.json e o guia HERMES-POSTIZ.md do workflow. Faça upload da imagem '
        'selecionada e consulte os schemas atuais dos canais antes de criar rascunho. '
        'Caminhos locais não são URLs públicas do Postiz. Publicação/agendamento exigem autorização específica.\n', encoding='utf-8')
    (directory / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest
