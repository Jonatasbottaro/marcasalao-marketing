"""Composição local Marca Salão. Nenhuma rede, credencial ou publicação."""
from datetime import datetime, timezone
import hashlib
from itertools import combinations
import json
from pathlib import Path
import re
import uuid
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageChops

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
        values[key] = ' '.join(value.split()) if key in ('tema', 'titulo') else value.strip()
    fitted(values['tema'].upper(), 22, 20, 1, True)
    fitted(values['titulo'], 76, 56, 3, True)
    benefits = [v.strip() for v in re.split(r'[|\n]', values['texto']) if v.strip()]
    if not 1 <= len(benefits) <= 3:
        raise ValueError('Informe de um a três benefícios separados por | ou quebra de linha.')
    for benefit in benefits:
        if len(benefit) > 62:
            raise ValueError('Cada benefício deve ter até 62 caracteres.')
        benefit_layout(benefit)
    if type(link_bio_confirmado) is not bool:
        raise ValueError('Confirmação do link na bio deve ser booleana.')
    if not link_bio_confirmado and 'link na bio' in values['legenda_instagram'].lower():
        raise ValueError('Confirme o link da bio antes de usar essa chamada na legenda.')
    fb_cta = 'Acesse o link da descrição'
    ig_cta = 'Acesse o link na bio' if link_bio_confirmado else 'Conheça o Marca Salão'
    return {'campanha': campanha, **values, 'beneficios': benefits, 'link_bio_confirmado': link_bio_confirmado,
            'legendas': {network: caption(values['legenda_' + network], network, link_bio_confirmado) for network in INTEGRATIONS},
            'cta': {'facebook': fb_cta, 'instagram': ig_cta}}


def title_layout(text):
    face, wrapped, size = fitted(text, 80, 56, 3, True)
    words = text.split()
    count = len(wrapped)
    best, score = wrapped, float('inf')
    for cuts in combinations(range(1, len(words)), count - 1):
        bounds = (0,) + cuts + (len(words),)
        candidate = [' '.join(words[bounds[i]:bounds[i + 1]]) for i in range(count)]
        widths = [face.getlength(line) for line in candidate]
        if max(widths) > 936:
            continue
        penalty = sum((width - sum(widths) / count) ** 2 for width in widths)
        if penalty < score:
            best, score = candidate, penalty
    return face, best, size


def caption(body, network, bio):
    # Conservar o corpo editorial; inserir CTA antes da pergunta final/hashtags.
    if (network == 'facebook' and 'https://marcasalao.com.br' in body) or (network == 'instagram' and bio and 'link na bio' in body.lower()):
        return body.strip()
    blocks = [part.strip() for part in body.splitlines()]
    tail = []
    while blocks:
        if not blocks[-1]:
            blocks.pop()
        elif blocks[-1].startswith('#') or blocks[-1].endswith('?'):
            tail.insert(0, blocks.pop())
        else:
            break
    cta = ('Conheça os recursos e planos do Marca Salão:\nAcesse pelo link da descrição: https://marcasalao.com.br'
           if network == 'facebook' else
           'Conheça o sistema — link na bio do @marcasalao.' if bio else
           'Conheça o Marca Salão: @marcasalao.')
    return '\n\n'.join(['\n'.join(blocks).strip(), cta] + tail)


def benefit_layout(text):
    for size in range(32, 23, -2):
        face = font(size, True)
        try:
            wrapped = lines(text, face, 340)
        except ValueError:
            continue
        if len(wrapped) <= 2:
            return face, wrapped, size
    raise ValueError('Benefício longo demais para duas linhas; reduza-o.')


def image_prompt(brief):
    return ('Use a imagem anexada SOMENTE como referência de cenário, materiais, cores e iluminação '
            'do anúncio aprovado do Marca Salão. Gere UMA FOTOGRAFIA de fundo nova, sem a tipografia, '
            'sem logotipo, sem ícones, sem CTA e sem textos da referência. Não copie a arte pronta. '
            'Cenário de salão elegante e realista: parede verde-petróleo profunda, bancada de mármore '
            'branco na parte inferior, planta lateral, borda de espelho dourado e ferramentas de salão '
            'na extrema direita, luz natural suave. Tema: ' + brief['tema'] + '. Objetos da campanha: ' +
            brief['direcao_visual'] + '. Composição quadrada, topo e centro até 50% da altura como parede '
            'verde livre para título. Deixe o lado esquerdo livre até 80% da altura para três benefícios. '
            'Objetos principais pequenos no canto inferior direito entre 55% e 85% da altura, '
            'sem cobrir a parede livre. Use verde-petróleo, menta, branco e dourado discreto. '
            'Sem letras, números, marcas, gráficos de crescimento, interfaces ou telas de software. '
            'Calculadora pode ter visor desligado e teclas lisas. Papel sem inscrições. '
            'Os textos e a logo oficial serão compostos depois com precisão localmente.')


def render(brief, background, fmt, network):
    w, h = FORMATS[fmt]
    image = ImageOps.fit(background.convert('RGB'), (w, h), method=Image.Resampling.LANCZOS)
    # Escurecimento suave assegura contraste sem cobrir o cenário com um cartão.
    shade = Image.new('RGBA', (w, h))
    sh = ImageDraw.Draw(shade)
    for y in range(h):
        alpha = int(110 * max(0, 1 - y / (h * .85)))
        # Rodapé escurecido gradualmente para texto branco sobre mármore.
        lower = int(210 * max(0, (y - (h - 230)) / 230))
        sh.line((0, y, w, y), fill=(0, 35, 35, max(alpha, lower)))
    image = Image.alpha_composite(image.convert('RGBA'), shade)
    # Vinheta com transições nos dois eixos; sem bordas de cartão sobre a foto.
    horizontal = Image.new('L', (w, 1))
    horizontal.putdata([int(190 * min(1, max(0, (680 - x) / 190))) for x in range(w)])
    start, end = int(h * .47) - 55, h - (270 if fmt == 'stories' else 180)
    vertical = Image.new('L', (1, h))
    vertical.putdata([int(255 * min(1, max(0, (y - start) / 90), max(0, (end - y) / 90))) for y in range(h)])
    vignette = Image.new('RGBA', (w, h), (0, 45, 45, 0))
    vignette.putalpha(ImageChops.multiply(horizontal.resize((w, h)), vertical.resize((w, h))))
    image = Image.alpha_composite(image, vignette).convert('RGB')
    draw = ImageDraw.Draw(image)
    story = fmt == 'stories'
    top = 170 if story else 40
    logo = Image.open(ASSETS / 'marcasalao-logo.png').convert('RGBA')
    margin = logo.width // 64
    logo = logo.crop((margin, margin, logo.width - margin, logo.height - margin))
    logo.thumbnail((112, 112), Image.Resampling.LANCZOS)
    logo_mask = Image.new('L', logo.size)
    ImageDraw.Draw(logo_mask).rounded_rectangle((0, 0, logo.width - 1, logo.height - 1), radius=logo.width * .17, fill=255)
    logo.putalpha(ImageChops.multiply(logo.getchannel('A'), logo_mask))
    image.paste(logo, ((w - logo.width) // 2, top), logo)
    draw.text((w // 2, top + 130), 'Marca Salão', anchor='mt', font=font(34, True), fill='white', stroke_width=1, stroke_fill=TEAL)
    face, wrapped, size = title_layout(brief['titulo'])
    y = top + 194
    for index, line in enumerate(wrapped):
        draw.text((w // 2, y), line, anchor='mt', font=face,
                  fill=MINT if index == len(wrapped) - 1 else 'white', stroke_width=1, stroke_fill=TEAL)
        y += size + 7
    # Espaço reservado aos benefícios em todas as proporções, sem cortes de texto.
    footer = h - (260 if story else 120)
    first = max(y + 48, int(h * .49))
    step = min(112, (footer - first - 38) // len(brief['beneficios']))
    if step < 84:
        raise ValueError('O título e os benefícios não cabem no formato; reduza o texto.')
    for idx, benefit in enumerate(brief['beneficios']):
        cy = first + idx * step
        draw.ellipse((96, cy - 8, 168, cy + 64), fill=MINT, outline='#65bab1', width=2)
        # Símbolos vetoriais independentes de fontes de emoji.
        cx = 132
        if 'receita' in benefit.lower() or 'finance' in benefit.lower():
            draw.text((cx, cy + 27), '$', anchor='mm', font=font(42, True), fill=TEAL)
        elif 'médio' in benefit.lower():
            draw.rounded_rectangle((114, cy + 5, 150, cy + 50), radius=4, outline=TEAL, width=3)
            draw.rectangle((120, cy + 11, 144, cy + 21), outline=TEAL, width=2)
            for xx in (120, 130, 140):
                for yy in (30, 40):
                    draw.rectangle((xx, cy + yy, xx + 3, cy + yy + 3), fill=TEAL)
        else:
            for yy in (12, 28, 44):
                draw.ellipse((112, cy + yy - 3, 118, cy + yy + 3), fill=TEAL)
                draw.line((126, cy + yy, 151, cy + yy), fill=TEAL, width=4)
        face, wrapped, size = benefit_layout(benefit)
        for j, line in enumerate(wrapped):
            draw.text((190, cy + j * (size + 5)), line, font=face, fill='white', stroke_width=1, stroke_fill=TEAL)
        if idx < len(brief['beneficios']) - 1:
            draw.line((96, cy + step - 17, 505, cy + step - 17), fill='#6fbdb3', width=1)
    # Chamada textual, sem aparência de botão ou link clicável na imagem.
    draw.text((w // 2, footer), brief['cta'][network], anchor='mt', font=font(30, True), fill='white', stroke_width=1, stroke_fill=TEAL)
    draw.text((w // 2, footer + 46), 'marcasalao.com.br' if network == 'facebook' else '@marcasalao', anchor='mt', font=font(25, True), fill='white', stroke_width=1, stroke_fill=TEAL)
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
                'visual_standard': 'salao-realista-v2', 'reference_post': 'https://www.facebook.com/photo/?fbid=122109973515500502',
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
