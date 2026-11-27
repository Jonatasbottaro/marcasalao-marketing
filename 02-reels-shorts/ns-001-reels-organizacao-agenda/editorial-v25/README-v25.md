# NS-001 — Studio Bella — v2.5 (correção de mapeamento de mídia)

## Causa raiz
O pedido v2.4 apontava as quatro cenas para as três capturas erradas:
- Cena 1 → CAP-01 (agenda) — correto por acaso, mas via `ns001-c2-situacao`.
- Cena 2 → CAP-02 (close-status) — correto.
- Cena 3 → CAP-03 (filtro) — correto.
- Cena 4 → CAP-01 (agenda Studio Bella) — **sem endcard Marca Salão**.

A arte oficial `CAP-04-cta-marcasalao.jpg` existia mas não estava vinculada.
No MP4 v2.4 os frames 3s/9s/15s mostravam a tela Studio Bella e o 20s não tinha endcard.

## Correção
Mapeamento 1:1 com as quatro imagens reais:
- `ns001-c1-agenda` → CAP-01-v24-agenda.jpg (Cena 1)
- `ns001-c2-close-status` → CAP-02-v24-close-status.jpg (Cena 2)
- `ns001-c3-filtro` → CAP-03-v24-filtro.jpg (Cena 3)
- `ns001-c4-cta` → CAP-04-cta-marcasalao.jpg (Cena 4 — endcard)

Roteiro, duração (22s) e legendas inalterados. Sem áudio.

## Verificação (prévia + MP4 final)
4 frames extraídos (3/9/15/20s) e comparados por Hamming 64x64 contra as fontes:
- 3s → CAP-01 · 9s → CAP-02 · 15s → CAP-03 · 20s → CAP-04.

## Arquivos
- `pedido-editorial-v25.video-request.json` — pedido corrigido.
- `04-legendas/ns001_roteiro_001_v25_studio_bella.srt` — legendas.
- `04-legendas/ns001_roteiro_001_v25_studio_bella_narracao.txt` — narração (texto, sem áudio).

Branch `feat/ns001-studio-bella-v2` (PR #33, rascunho). Sem merge.