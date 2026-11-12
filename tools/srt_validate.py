"""Validacao de SRT para a entrega transacional de video (R002).

Funcoes puras: recebem texto/bytes e devolvem lista de erros com codigos
estaveis. Nenhum I/O de rede, nenhum efeito colateral.
"""

import re

TIMESTAMP_LINE_RE = re.compile(
    r"^(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})$"
)
TIMESTAMP_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})$")


def parse_timestamp(text):
    m = TIMESTAMP_RE.match(text)
    if not m:
        return None
    hh, mm, ss, ms = (int(g) for g in m.groups())
    if mm > 59 or ss > 59:
        return None
    return hh * 3600 + mm * 60 + ss + ms / 1000.0


def validate_srt_text(text, duration=None):
    """Devolve lista de strings 'CODIGO: mensagem'; lista vazia = SRT valido."""
    errors = []
    if not text.endswith("\n") or text.endswith("\n\n") or "\r" in text:
        errors.append("SRT_NEWLINE_INVALID: esperado LF com exatamente uma newline final")
    if not text.strip():
        errors.append("SRT_EMPTY: nenhum bloco de legenda")
        return errors

    blocks = re.split(r"\n\s*\n", text.strip("\n"))
    previous_end = None
    for position, block in enumerate(blocks, start=1):
        lines = block.split("\n")
        if not lines[0].strip().isdigit() or int(lines[0].strip()) != position:
            errors.append(
                f"SRT_BLOCK_INDEX: bloco {position} com indice '{lines[0].strip()}'"
            )
        if len(lines) < 2:
            errors.append(f"SRT_TIMESTAMP_INVALID: bloco {position} sem linha de tempo")
            continue
        m = TIMESTAMP_LINE_RE.match(lines[1].strip())
        if not m:
            errors.append(
                f"SRT_TIMESTAMP_INVALID: bloco {position} com tempo '{lines[1].strip()}'"
            )
            continue
        start = parse_timestamp(m.group(1))
        end = parse_timestamp(m.group(2))
        if start is None or end is None:
            errors.append(f"SRT_TIMESTAMP_INVALID: bloco {position} com campo de tempo fora do faixa")
            continue
        if start >= end:
            errors.append(f"SRT_INTERVAL_INVALID: bloco {position} com inicio >= fim")
        if previous_end is not None and start < previous_end:
            errors.append(f"SRT_OVERLAP: bloco {position} inicia antes do fim do anterior")
        if duration is not None and end > duration + 1e-6:
            errors.append(
                f"SRT_OUT_OF_DURATION: bloco {position} termina em {end:.3f}s > duracao {duration:.3f}s"
            )
        body = "\n".join(lines[2:]).strip()
        if not body:
            errors.append(f"SRT_TEXT_EMPTY: bloco {position} sem texto")
        previous_end = end
    return errors


def validate_srt_bytes(data, duration=None):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return ["SRT_ENCODING: arquivo nao e UTF-8 valido"]
    return validate_srt_text(text, duration)


def validate_srt_file(path, duration=None):
    with open(path, "rb") as handle:
        return validate_srt_bytes(handle.read(), duration)