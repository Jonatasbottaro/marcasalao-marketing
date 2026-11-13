"""Gera uma agenda ficticia (PNG 540x960) como midia de prova do Motion.

Desenha um titulo e faixas de horarios (09:00..12:00) com a fonte bitmap do
layout de carrossel. Stdlib apenas. A midia e insumo de teste em .workspace/.
As faixas tem posicoes conhecidas para o plano de motion destacar um horario.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import carousel_layout

WIDTH = 540
HEIGHT = 960
ROW_START = 200
ROW_H = 140
ROW_GAP = 20
SLOTS = ['09:00', '10:00', '11:00', '12:00']


def slot_region(index):
    """Regiao relativa (0..1) da faixa do horario `index` no quadro 540x960."""
    y = ROW_START + index * (ROW_H + ROW_GAP)
    return {'x': 0.06, 'y': y / HEIGHT, 'w': 0.88, 'h': ROW_H / HEIGHT}


def write_agenda_png(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    rgb = bytearray(WIDTH * HEIGHT * 3)
    for y in range(HEIGHT):
        ratio = y / (HEIGHT - 1)
        row = bytes(tuple(int(carousel_layout.BG_TOP[c] + (carousel_layout.BG_BOTTOM[c] - carousel_layout.BG_TOP[c]) * ratio) for c in range(3)))
        rgb[y * WIDTH * 3:(y + 1) * WIDTH * 3] = row * WIDTH
    carousel_layout._draw_text(rgb, WIDTH, 60, 60, 'AGENDA DO DIA', 6, carousel_layout.TEXT_COLOR)
    for i, slot in enumerate(SLOTS):
        y = ROW_START + i * (ROW_H + ROW_GAP)
        # faixa de fundo levemente mais clara
        for yy in range(y, y + ROW_H):
            for xx in range(int(0.06 * WIDTH), int(0.94 * WIDTH)):
                idx = (yy * WIDTH + xx) * 3
                rgb[idx] = min(255, rgb[idx] + 18)
                rgb[idx + 1] = min(255, rgb[idx + 1] + 18)
                rgb[idx + 2] = min(255, rgb[idx + 2] + 22)
        carousel_layout._draw_text(rgb, WIDTH, 80, y + 40, slot + '  CLIENTE', 5, carousel_layout.TEXT_COLOR)
    with open(path, 'wb') as handle:
        handle.write(carousel_layout.encode_png(WIDTH, HEIGHT, rgb))
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description='Agenda ficticia para prova do Motion')
    parser.add_argument('--output', required=True, help='Caminho do PNG de agenda')
    parser.add_argument('--root', default=os.getcwd())
    args = parser.parse_args(argv)
    root = os.path.realpath(args.root)
    target = os.path.realpath(args.output)
    if not (target == root or target.startswith(root + os.sep)):
        print('Erro: saida fora da raiz do projeto', file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(target), exist_ok=True)
    write_agenda_png(target)
    print(os.path.relpath(target, root).replace(os.sep, '/'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())