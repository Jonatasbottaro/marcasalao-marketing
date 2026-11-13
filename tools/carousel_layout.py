"""Layout reutilizavel de cards de carrossel (R003), stdlib apenas.

Renderiza texto com uma fonte bitmap 5x7 embutida (sem dependencia de fonte do
sistema), com margens, contraste e quebra de linha. Mede o texto para indicar
qual card excede a area disponivel. Compoe o card sobre fundo escuro ou sobre a
midia de origem (escurecida para contraste) e codifica PNG; a conversao para
JPEG fica a cargo do FFmpeg na camada de exportacao.
"""

import struct
import zlib

WIDTH = 1080
HEIGHT = 1080
MARGIN = 90
TITLE_SCALE = 8
BODY_SCALE = 5
LINE_GAP_FACTOR = 2

BG_TOP = (16, 20, 26)
BG_BOTTOM = (28, 34, 44)
TEXT_COLOR = (245, 247, 250)
ACCENT = (79, 140, 255)

# Fonte bitmap 5x7 (cada glifo = 7 linhas de 5 colunas).
_FONT = {
    'A': ('.###.', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'),
    'B': ('####.', '#...#', '#...#', '####.', '#...#', '#...#', '####.'),
    'C': ('.###.', '#...#', '#....', '#....', '#....', '#...#', '.###.'),
    'D': ('####.', '#...#', '#...#', '#...#', '#...#', '#...#', '####.'),
    'E': ('#####', '#....', '#....', '####.', '#....', '#....', '#####'),
    'F': ('#####', '#....', '#....', '####.', '#....', '#....', '#....'),
    'G': ('.###.', '#...#', '#....', '#.###', '#...#', '#...#', '.###.'),
    'H': ('#...#', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'),
    'I': ('#####', '..#..', '..#..', '..#..', '..#..', '..#..', '#####'),
    'J': ('#####', '...#.', '...#.', '...#.', '...#.', '#..#.', '.##..'),
    'K': ('#...#', '#..#.', '#.#..', '##...', '#.#..', '#..#.', '#...#'),
    'L': ('#....', '#....', '#....', '#....', '#....', '#....', '#####'),
    'M': ('#...#', '##.##', '#.#.#', '#.#.#', '#...#', '#...#', '#...#'),
    'N': ('#...#', '##..#', '#.#.#', '#..##', '#...#', '#...#', '#...#'),
    'O': ('.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'),
    'P': ('####.', '#...#', '#...#', '####.', '#....', '#....', '#....'),
    'Q': ('.###.', '#...#', '#...#', '#...#', '#.#.#', '#..#.', '.##.#'),
    'R': ('####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'),
    'S': ('.####', '#....', '#....', '.###.', '....#', '....#', '####.'),
    'T': ('#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'),
    'U': ('#...#', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'),
    'V': ('#...#', '#...#', '#...#', '#...#', '#...#', '.#.#.', '..#..'),
    'W': ('#...#', '#...#', '#...#', '#.#.#', '#.#.#', '##.##', '#...#'),
    'X': ('#...#', '#...#', '.#.#.', '..#..', '.#.#.', '#...#', '#...#'),
    'Y': ('#...#', '#...#', '.#.#.', '..#..', '..#..', '..#..', '..#..'),
    'Z': ('#####', '....#', '...#.', '..#..', '.#...', '#....', '#####'),
    '0': ('.###.', '#...#', '#..##', '#.#.#', '##..#', '#...#', '.###.'),
    '1': ('..#..', '.##..', '..#..', '..#..', '..#..', '..#..', '#####'),
    '2': ('.###.', '#...#', '....#', '...#.', '..#..', '.#...', '#####'),
    '3': ('#####', '...#.', '..#..', '...#.', '....#', '#...#', '.###.'),
    '4': ('...#.', '..##.', '.#.#.', '#..#.', '#####', '...#.', '...#.'),
    '5': ('#####', '#....', '####.', '....#', '....#', '#...#', '.###.'),
    '6': ('.###.', '#....', '#....', '####.', '#...#', '#...#', '.###.'),
    '7': ('#####', '....#', '...#.', '..#..', '.#...', '.#...', '.#...'),
    '8': ('.###.', '#...#', '#...#', '.###.', '#...#', '#...#', '.###.'),
    '9': ('.###.', '#...#', '#...#', '.####', '....#', '....#', '.###.'),
    ' ': ('.....', '.....', '.....', '.....', '.....', '.....', '.....'),
    '.': ('.....', '.....', '.....', '.....', '.....', '.##..', '.##..'),
    ',': ('.....', '.....', '.....', '.....', '.##..', '.##..', '.#...'),
    '-': ('.....', '.....', '.....', '#####', '.....', '.....', '.....'),
    ':': ('.....', '.##..', '.##..', '.....', '.##..', '.##..', '.....'),
    '!': ('..#..', '..#..', '..#..', '..#..', '..#..', '.....', '..#..'),
    '?': ('.###.', '#...#', '....#', '...#.', '..#..', '.....', '..#..'),
    "'": ('..#..', '..#..', '.....', '.....', '.....', '.....', '.....'),
    '/': ('....#', '....#', '...#.', '..#..', '.#...', '#....', '#....'),
    '(': ('...#.', '..#..', '.#...', '.#...', '.#...', '..#..', '...#.'),
    ')': ('.#...', '..#..', '...#.', '...#.', '...#.', '..#..', '.#...'),
    '&': ('.##..', '#..#.', '#.#..', '.#...', '#.#.#', '#..#.', '.##.#'),
    '+': ('.....', '..#..', '..#..', '#####', '..#..', '..#..', '.....'),
}
_TRANSLIT = str.maketrans({
    'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
    'é': 'e', 'ê': 'e', 'ë': 'e', 'í': 'i', 'ï': 'i',
    'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o', 'ú': 'u', 'ü': 'u',
    'ç': 'c', 'ñ': 'n',
})


def _norm(text):
    return text.translate(_TRANSLIT).upper()


def char_width(scale):
    return 6 * scale  # 5 colunas + 1 de espaco


def char_height(scale):
    return 7 * scale


def text_width(text, scale):
    return max(0, len(text) * char_width(scale) - scale)


def wrap_text(text, max_width, scale):
    words = _norm(text).split()
    lines = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if text_width(candidate, scale) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        # palavra longa demais: quebra rigida
        while text_width(word, scale) > max_width:
            cut = max(1, max_width // char_width(scale))
            lines.append(word[:cut])
            word = word[cut:]
        current = word
    if current:
        lines.append(current)
    return lines or ['']


def measure_card(card, width=WIDTH, height=HEIGHT, margin=MARGIN):
    """Mede titulo+corpo e indica se excede a area disponivel (sem render)."""
    avail_w = width - 2 * margin
    avail_h = height - 2 * margin
    title_lines = wrap_text(card.get('title', ''), avail_w, TITLE_SCALE)
    body_lines = wrap_text(card.get('body', ''), avail_w, BODY_SCALE) if card.get('body') else []
    total = 0
    for line in title_lines:
        total += char_height(TITLE_SCALE) + LINE_GAP_FACTOR * TITLE_SCALE
    if body_lines:
        total += char_height(TITLE_SCALE)  # espaco titulo->corpo
    for line in body_lines:
        total += char_height(BODY_SCALE) + LINE_GAP_FACTOR * BODY_SCALE
    return {
        'titleLines': title_lines,
        'bodyLines': body_lines,
        'totalHeight': total,
        'availableHeight': avail_h,
        'overflow': total > avail_h,
    }


def _draw_text(canvas, width, x, y, text, scale, color):
    cx = x
    for ch in _norm(text):
        glyph = _FONT.get(ch, _FONT['?'])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == '#':
                    for dy in range(scale):
                        for dx in range(scale):
                            px = cx + col * scale + dx
                            py = y + row * scale + dy
                            if 0 <= px < width and 0 <= py < HEIGHT:
                                idx = (py * width + px) * 3
                                canvas[idx:idx + 3] = bytes(color)
        cx += char_width(scale)


def render_card(card, media_rgb=None, width=WIDTH, height=HEIGHT, margin=MARGIN):
    """Compoe o card e devolve (rgb bytearray, overflow)."""
    measured = measure_card(card, width, height, margin)
    canvas = bytearray(width * height * 3)
    if media_rgb is not None and len(media_rgb) == width * height * 3:
        for i in range(0, len(canvas), 3):
            canvas[i] = media_rgb[i] * 45 // 100
            canvas[i + 1] = media_rgb[i + 1] * 45 // 100
            canvas[i + 2] = media_rgb[i + 2] * 45 // 100
    else:
        for y in range(height):
            ratio = y / (height - 1)
            row = bytes(tuple(int(BG_TOP[c] + (BG_BOTTOM[c] - BG_TOP[c]) * ratio) for c in range(3)))
            start = y * width * 3
            canvas[start:start + width * 3] = row * width
    # barra de acento no topo
    bar_y = margin // 2
    for y in range(bar_y, bar_y + 8):
        for x in range(margin, width - margin):
            idx = (y * width + x) * 3
            canvas[idx:idx + 3] = bytes(ACCENT)

    if not measured['overflow']:
        y = (height - measured['totalHeight']) // 2
        for line in measured['titleLines']:
            lw = text_width(line, TITLE_SCALE)
            _draw_text(canvas, width, (width - lw) // 2, y, line, TITLE_SCALE, TEXT_COLOR)
            y += char_height(TITLE_SCALE) + LINE_GAP_FACTOR * TITLE_SCALE
        if measured['bodyLines']:
            y += char_height(TITLE_SCALE)
            for line in measured['bodyLines']:
                lw = text_width(line, BODY_SCALE)
                _draw_text(canvas, width, (width - lw) // 2, y, line, BODY_SCALE, TEXT_COLOR)
                y += char_height(BODY_SCALE) + LINE_GAP_FACTOR * BODY_SCALE
    return canvas, measured['overflow']


def _png_chunk(tag, data):
    return (struct.pack('>I', len(data)) + tag + data
            + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))


def encode_png(width, height, rgb):
    raw = b''.join(b'\x00' + bytes(rgb[y * width * 3:(y + 1) * width * 3]) for y in range(height))
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + _png_chunk(b'IHDR', ihdr)
            + _png_chunk(b'IDAT', zlib.compress(raw, 9)) + _png_chunk(b'IEND', b''))