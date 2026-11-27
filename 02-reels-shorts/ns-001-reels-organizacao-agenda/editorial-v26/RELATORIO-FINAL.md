# NS-001 — Studio Bella — v2.6 — Relatório final

## A. Diagnóstico
- v2.4: mapeamento de mídia errado (4 cenas → 3 arquivos; endcard não vinculado).
- v2.5: mapeamento corrigido, mas cenas 1/2 em modo `fill` cortavam horário/serviço/status.
- Tentativas em modo `fit` (interface inteira) e recorte 1:1 centralizado: sem deformação, mas conteúdo ocupava ~9% do quadro (minúsculo no celular).
- Causa combinada: enquadramento (fill estreito / fit pequeno) + interface larga 665×605 incompatível com full-bleed 9:16.

## B. Implementação
- Pré-composição editorial 1080×1920 (#EDFCF7) das cenas 1 e 2: moldura branca + 2 cartões reais empilhados, recorte 1:1, escala única 1.4× (931×378), região y=360–1178.
- Cena 1: cartões (0,105)+(0,375). Cena 2: ordem invertida (0,375)+(0,105) — visualmente distinta.
- Cenas 3 (Mariana Silva) e 4 (endcard) preservadas em modo fit.
- `motionIntent: none` em todas as cenas (sem slow-zoom, sem corte).
- Arquivos: `.workspace/tmp/ns001-studio-bella-v26-final/{compose.py, cena1-4.png, pedido-editorial-v26.video-request.json}`.

## C. Validação audiovisual
- Master 1080×1920, 30fps, 22s, 0 áudio (FFprobe).
- Correlação frames×cenas: 3s→cena1 0.998 · 9s→cena2 0.998 · 15s→cena3 0.997 · 20s→cena4 1.000.
- Extremos (0.5/5.5/6.5/11.5/12.5/16.5/17.5/21.5s): mapeamento correto, sem cortes de animação.
- Previews 360×640 em `qc/frames/`.
- Limitação: agente sem inspeção visual humana; aprovação editorial pendente.

## D. Entrega
- MP4 principal: `.workspace/tmp/ns001-studio-bella-v26-final/entrega/NS-001-Studio-Bella-v2.6-instagram.mp4`
- Player: `.../entrega/review.html`
- ZIP: `.../entrega/NS-001-Studio-Bella-v2.6-final.zip`
- SRT: `.../entrega/ns001_roteiro_001_v26_studio_bella.srt`
- Narração: `.../entrega/ns001_roteiro_001_v26_studio_bella_narracao.txt`
- QC: `.../entrega/qc/frames/`
- 3 perfis: `.../entrega/{instagram,facebook,youtube}-*/`

## E. Git
- Branch `feat/ns001-studio-bella-v2` (PR #33, rascunho). Commit v2.6 registrado. Sem merge.

## F. Limitações
- Defeito corrigido e verificado objetivamente (mapeamento, proporção, conteúdo por correlação).
- Verificação visual humana do MP4 final pendente (titular).
- Publicação não autorizada.