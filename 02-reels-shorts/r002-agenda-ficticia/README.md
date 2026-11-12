# R002 — Piloto técnico local: agenda fictícia em vídeo vertical sem áudio

Entrega técnica local autorizada pelo titular em 12/11/2026 (bloco "PROPOSTA DE DECISÃO DO TITULAR").
**Não é campanha aprovada, não é produção real da NS-001 e nada aqui foi publicado ou enviado a qualquer rede.**
Todos os dados mostrados são fictícios (salão de teste E2E).

## O que esta entrega prova

- o exportador local (`tools/build_video.py`) nunca cria faixa de áudio: sem `anullsrc`, sem AAC silencioso, sem mux de faixa vazia; entrada de áudio é recusada pela política do projeto;
- exportação transacional: staging em `.workspace/tmp/`, validação de SRT/captura/narração/MP4 e promoção atômica (`os.replace`); qualquer falha preserva integralmente a entrega anterior e retorna código ≠ 0;
- piloto de três cenas (12 s) reutilizando uma única captura sanitizada já versionada;
- primeiro motion: contorno editável sobre o horário ocupado, em camada PNG separada com entrada/saída suaves (fade de alpha), sem alterar a captura original;
- legenda visível queimada nos frames + `.srt` sincronizado + narração em `.txt` separado, sem geração de voz;
- revisão localizada por configuração, com prova por SHA-256 de que apenas o elemento alterado mudou;
- SRT inválido falha sem substituir nenhum artefato aprovado.

## Artefatos

| Artefato | Caminho | Versionado |
| --- | --- | --- |
| Vídeo v1 (12 s, 1080×1920@30, H.264, yuv420p, 0 áudio) | `.workspace/archives/r002-video-local/r002-agenda-ficticia.mp4` | não — `.gitignore` versionado ignora `*.mp4` |
| Vídeo revisão (mesmas cenas, contorno rosa mais espesso) | `.workspace/archives/r002-video-local/r002-agenda-ficticia-revisao.mp4` | não — mesma política |
| Manifesto com hashes, bytes, FFprobe e comando reproduzível | `02-reels-shorts/r002-agenda-ficticia/manifest.json` | sim |
| SRT (3 blocos, UTF-8, LF, newline final única) | `04-legendas/roteiro_r002_agenda_ficticia.srt` | sim |
| Narração por cena e tempos (pt-BR, sem áudio) | `04-legendas/roteiro_r002_agenda_ficticia_narracao.txt` | sim |
| Captura sanitizada reutilizada (1440×900 PNG) | `00-briefings/campanhas/NS-001/capturas/2026-11-05/01-agenda-visao-dia.png` | sim (já existia) |
| Configuração das cenas e do contorno | `tools/r002/agenda-ficticia.pilot.json` | sim |
| Configuração da revisão localizada | `tools/r002/agenda-ficticia-revisao.pilot.json` | sim |

Os MP4 existem apenas neste computador enquanto permanecerem somente em `.workspace/`; o manifesto
versionado preserva nome, SHA-256, tamanho, inspeção FFprobe e o comando que os reproduz. Não há Git LFS.

## Cenas e tempos

| Cena | Intervalo | Conteúdo visível |
| --- | --- | --- |
| `visao-inicial` | 0–4 s | captura da agenda do dia; legenda "Agenda do dia: todos os atendimentos em uma tela." |
| `horario-ocupado` | 4–9 s | mesma captura + contorno sobre o bloco 09:00–10:00 (fade in 0,5 s / fade out 0,5 s); legenda "Horário ocupado: 09:00 às 10:00, destacado na agenda." |
| `fechamento` | 9–12 s | mesma captura, contorno já saído; legenda "Demonstração técnica com dados fictícios." |

A legenda visível é queimada pelo filtro `subtitles` (libass) aplicado por último na cadeia, com estilo
próprio para a faixa segura inferior do frame vertical (`subtitleStyle` na configuração). O `.srt`
versionado tem os mesmos três textos e tempos; a narração em `.txt` existe para geração de áudio em
ferramenta externa, fora do editor — o vídeo entregue não contém áudio.

## Contorno editável (parâmetros de `outline` na configuração)

| Parâmetro | Significado |
| --- | --- |
| `x`, `y`, `w`, `h` | retângulo em pixels nativos da captura (1440×900); o renderer mapeia para o frame 1080×1920 com a mesma matemática scale/pad do exportador |
| `thickness` | espessura do traço em pixels do frame |
| `color` | RGBA do traço |
| `radius` | raio dos cantos arredondados |
| `start`, `end` | janela temporal de exibição |
| `fadeIn`, `fadeOut` | duração dos fades de alpha (entrada/saída suaves, sem piscar) |

O contorno é rasterizado como PNG RGBA separado (`tools/r002_pilot.py`, stdlib apenas) e sobreposto com
`overlay` + `fade=alpha=1`; a captura original nunca é modificada. Não há framework genérico de animação.

## Reprodução

Requisitos: Python 3 padrão (sem dependências externas), FFmpeg e FFprobe no PATH (testado com FFmpeg 9.0.2).
Executar a partir da raiz do checkout:

```bash
# entrega v1
python tools/r002_pilot.py --config tools/r002/agenda-ficticia.pilot.json \
  --staging .workspace/tmp/r002-video-local/v1 \
  --archive .workspace/archives/r002-video-local \
  --manifest 02-reels-shorts/r002-agenda-ficticia/manifest.json --tag v1

# revisão localizada (muda somente cor e espessura do contorno)
python tools/r002_pilot.py --config tools/r002/agenda-ficticia-revisao.pilot.json \
  --staging .workspace/tmp/r002-video-local/revisao \
  --archive .workspace/archives/r002-video-local \
  --manifest 02-reels-shorts/r002-agenda-ficticia/manifest.json --tag revisao

# inspeção técnica real
ffprobe -v error -show_streams -show_format -of json .workspace/archives/r002-video-local/r002-agenda-ficticia.mp4

# testes (unittest, inclui renders reais e FFprobe)
python -m unittest discover -s tools/tests -v
```

`--project-root` é opcional e só é necessário quando o checkout é uma worktree dentro de `.workspace/`:
nesse caso informe a raiz do projeto para a contenção de caminhos e para os caminhos relativos do manifesto.

## Comportamento transacional em falha

1. todos os artefatos nascem em `--staging` (dentro de `.workspace/tmp/`);
2. validação: SRT pelo validador (`tools/srt_validate.py`: sequência, timestamps, início < fim, ordem
   cronológica, sem sobreposição, dentro da duração, texto não vazio, UTF-8, newline final), narração não
   vazia, captura por FFprobe e MP4 por FFprobe (1 vídeo, 0 áudio, geometria, fps, pix_fmt, duração);
3. só então promoção arquivo a arquivo com `os.replace` (substituição atômica);
4. falha em qualquer etapa: nenhum destino é tocado, exit ≠ 0, erro sanitizado em stderr e staging
   preservado para diagnóstico. O teste `test_03_invalid_srt_preserves_previous_delivery` comprova por
   SHA-256 que a entrega anterior permanece idêntica.

## Revisão localizada e evidência de hashes

A revisão reutiliza exatamente a mesma captura e altera apenas `outline.color` e `outline.thickness`.
Comparação medida (manifesto, campo `unchanged`): captura, SRT e narração com SHA-256 idêntico entre as
duas execuções; MP4 diferente (`3870ef5e…` → `05bd7ee8…`). Não há edição incremental de codec: a prova é
de reutilização da fonte e alteração localizada na configuração/saída.

## Limites

- demonstração técnica local; nenhuma aprovação editorial, gravação ou publicação;
- nenhum áudio em nenhuma etapa; nenhum TTS, fornecedor, serviço pago ou rede;
- nenhuma alteração em `platform/`, `orchestration/`, Temporal, R001, BeatPlan ou OutputPlan;
- `docs/contexto/` não foi atualizado nesta execução, conforme o escopo autorizado;
- os MP4 não são portáteis entre computadores enquanto existirem apenas em `.workspace/`.