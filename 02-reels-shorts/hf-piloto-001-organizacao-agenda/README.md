# HF-PILOTO-001 — Marca Salão — Organização da agenda e dos atendimentos

Campanha piloto da migração HyperFrames (HF-001, fase F12, 27/11/2026). Primeira
produção completa pelo novo motor: post 4:5, carrossel 1:1 de 4 cards e reel
9:16 de 24 s, todos a partir dos mesmos contratos versionados
(`CarouselRequest v1` / `VideoRequest v1`) e do compositor HyperFrames com
templates nativos por função narrativa (F9/F10).

**Natureza: material de revisão humana (F13). Nada publicado, agendado ou
aprovado.** A aprovação editorial vigente da NS-001
([REGISTRO-APROVACAO-2026-11-24.md](../../00-briefings/campanhas/NS-001/REGISTRO-APROVACAO-2026-11-24.md))
não é alterada por este piloto; entregas anteriores não foram sobrescritas.
O briefing desta campanha é a especificação F12 da operação HF-001
(`docs/migracao-hyperframes/PLANO-DE-EXECUCAO.md`).

## Entregas

| Peça | Pedido | Geometria | Render |
| --- | --- | --- | --- |
| Post | [pedido-post.carousel-request.json](pedido-post.carousel-request.json) | 1080×1350 (4:5) | `python tools/render_hyperframes_still.py --input <pedido> --output-dir <entrega>/post` |
| Carrossel (4 cards) | [pedido-carrossel.carousel-request.json](pedido-carrossel.carousel-request.json) | 1080×1080 (1:1) | idem, `--output-dir <entrega>/carrossel` |
| Reel (24 s) | [pedido-reel.video-request.json](pedido-reel.video-request.json) | 1080×1920 (9:16) | `python tools/render_hyperframes.py --input <pedido> --profile instagram-reels-video --quality delivery --out <entrega>/reel/hf-piloto-001-reel.mp4` |

- Direção de cenas do reel: [direcao-de-cenas.md](direcao-de-cenas.md).
- Narração pronta para gravação (VIDEO CLEAN, texto separado):
  [../../04-legendas/hf-piloto-001-narracao-reel.txt](../../04-legendas/hf-piloto-001-narracao-reel.txt).
- Renders e pacote de revisão ficam em `<RAIZ>/.workspace/tmp/hf-piloto-001/`
  (não versionados; MP4 é ignorado pelo Git).

## Fontes

`fontes/` — 5 capturas reais autorizadas do ambiente demonstrativo do Meu Salão
com dados fictícios do salão Studio Bella (MKT-BRAND-001), 1080×1920, usadas
pela peça editorial v2 da NS-001 (Operação Resultado 08) e aqui reutilizadas:

| Arquivo | Conteúdo | Uso no piloto |
| --- | --- | --- |
| CAP-01-painel-1080x1920.jpg | Painel do gestor | Carrossel card 1; mídia de contrato das cenas hook/cta do reel (coberta pelo card de marca) |
| CAP-02-semana-1080x1920.jpg | Agenda da semana | Post; reel cena 2 |
| CAP-03-dia-1080x1920.jpg | Agenda do dia | Carrossel card 2; reel cena 3 |
| CAP-08-detalhes-1080x1920.jpg | Detalhes do agendamento | Reel cena 4 |
| CAP-10-confirmado-1080x1920.jpg | Agendamento confirmado | Carrossel card 3; reel cena 5 |

Capturas versionadas aqui para o piloto ser reproduzível em qualquer estação;
as cópias de trabalho da Operação 08 permanecem em `.workspace/` do checkout
principal (locais por desenho).

## Convenções aplicadas

- VIDEO CLEAN (MKT-VIDEO-002): sem faixa de áudio, sem legenda narrativa
  queimada, sem SRT (não solicitado); textos em cena são gráficos editoriais.
- Guardrails do tenant `marca-salao` conferidos pelo adaptador em todos os
  textos (nenhuma claim proibida; CTA sem aparência de botão).
- Templates por função narrativa (F9): hook/cta = card de marca; demonstration
  = captura como estrela com texto na base sobre scrim.
- Stills (F10): card com captura → demonstration; card sem captura → card de
  marca (primeiro hook, demais cta). O post e os cards 1–3 do carrossel
  mostram a captura; o card 4 é o convite de marca.
