# NS-001 — Revisão v2.1 (Studio Bella)

Correção audiovisual sobre a v2, preservando a v2 integralmente.
Rascunho de revisão — **não aprovado para publicação**.

## Problemas corrigidos

1. **Títulos redundantes removidos.** Os 12 `title` de cena do pedido v2
   (faixa superior) foram eliminados. O vídeo passa a ter **uma única
   camada narrativa**: a legenda queimada inferior (SRT/narração
   sincronizados). Confirmado no manifesto de composição: 14 bindings,
   zero overlay de título, `framing` ativo.
2. **Player sem duplicação.** O `review.html` v2.1 não usa `<track
   default>` nem cuebar (que no v2 era a terceira instância de legenda).
   O SRT continua disponível como link separado, sem ativação automática.
3. **Enquadramento.** `framingByProfile` fill/zoom 100 (centro 0.5/0.5)
   em todos os beats, reduzindo espaços vazios sem cortar a interface
   (1080×1920 preservado, áreas seguras de Reels/Shorts respeitadas).

## Pendências (não resolvidas nesta versão)

- **Indicadores de desenvolvimento nas capturas.** O selo vermelho
  "10 Issues" (Next.js Dev Tools) sobrepõe a última linha de conteúdo
  (y≈1024–1119) nas 10 capturas originais — não é removível por corte
  legítimo sem apagar conteúdo. A recaptura em viewport móvel 9:16
  (450×800 @2.4 DPR, ocultando `nextjs-portal`/TanStack/ícone de extensão
  via CDP) ficou **pendente** porque o ambiente demonstrativo (emuladores
  + app) e o conector de navegador foram encerrados antes da recaptura.
  Reutilização das capturas válidas autorizada pela missão; a eliminação
  dos indicadores depende de nova sessão de captura.

## Arquivos

- `pedido-editorial-v21.video-request.json` — pedido v2.1 (sem títulos).
- `04-legendas/ns001_roteiro_001_v21_studio_bella.srt` — legendas.
- `04-legendas/ns001_roteiro_001_v21_studio_bella_narracao.txt` — narração.

## Validação (resumo)

- 3 MP4 (Instagram/Facebook/YouTube Shorts): 1080×1920, 30 fps, 47 s,
  h264/yuv420p, **0 faixas de áudio** (ffprobe).
- SRT válido e idêntico entre perfis; caption corrigida presente.
- 7 frames QC extraídos; player e ZIP em `.workspace/` (local).