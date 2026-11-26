# MKT-VIDEO-002 — VIDEO CLEAN / NARRAÇÃO SEPARADA

- Status: decisão de produção vigente
- Data: 26/11/2026
- Autoridade: pedido explícito do titular (atualização do padrão audiovisual)
- Implementação: `tools/render_local.py`, `tools/render_pipeline.py`, `tools/produce_video.py` (opção `--clean`); primeiro caso: NS-001 v2.8 (`02-reels-shorts/ns-001-reels-organizacao-agenda/editorial-v28/`)

## Contexto

A política anterior ("vídeo sem áudio", 24/11/2026 e anteriores) exigia legendas
narrativas queimadas no MP4 e SRT sincronizado em toda entrega. Na prática, as
legendas queimadas competiam com o conteúdo editorial por espaço vertical,
reduziam a legibilidade em telas pequenas e antecipavam um texto que o titular
prefere ajustar depois, em ferramentas externas (CapCut/Canva).

## Decisão

O padrão de produção de vídeo do projeto passa a ser **VIDEO CLEAN / NARRAÇÃO
SEPARADA**:

1. Vídeos sem nenhuma faixa de áudio, música ou narração (inalterado).
2. Sem legendas narrativas queimadas nos MP4.
3. SRT não é gerado por padrão; legendas só por solicitação expressa.
4. Roteiro de narração em TXT separado continua obrigatório, organizado por cena
   e tempo (`04-legendas/`).
5. Textos gráficos editoriais que fazem parte da composição visual (títulos,
   destaques, chips de status, CTA de endcard) são preservados — não são
   "legendas narrativas".
6. Novas composições não reservam faixas/áreas exclusivas para legendas
   queimadas (ex.: `captionBand` do compositor editorial).
7. O espaço liberado é reaproveitado para enquadramento, tamanho, legibilidade,
   movimento e hierarquia visual do conteúdo.
8. Elementos essenciais permanecem dentro das áreas seguras de cada plataforma,
   considerando que legendas poderão ser adicionadas posteriormente no
   CapCut/Canva.
9. Campanhas antigas com legendas e SRT permanecem válidas e reproduzíveis.
10. Vídeos, roteiros e documentos anteriores não são excluídos.

## Implementação retrocompatível

O contrato VideoRequest v1 (TypeScript) não mudou: `caption` continua sendo
campo obrigatório por cena e o validador continua rejeitando campos desconhecidos.
O modo clean é uma **opção de renderização no adaptador Python**, não um novo
contrato:

- `python tools/produce_video.py --input <pedido> --output-dir <destino> --clean`
- `python tools/render_pipeline.py --case <caso> ... --clean`
- `python tools/render_local.py --package <pacote> --assets <assoc> --output-dir <destino> --clean`

Com `--clean`: o filtro `subtitles` das legendas não entra no grafo FFmpeg, o
SRT não é escrito/validado/promovido, e o manifesto de entrega registra
`captionsMode: "clean"` (relatório: `captions.mode: "clean"`, `burned: false`).
A narração TXT e os demais artefatos (pacote, relatório, manifesto, inventário)
permanecem. Títulos editoriais via `--text-overlays`/`--visual-style`, quando
presentes, continuam sendo compostos (são conteúdo visual, não legenda narrativa).

Sem `--clean`, o comportamento legado é byte a byte o mesmo: legenda queimada +
SRT validado + quatro artefatos. A suíte de testes cobre ambos os caminhos
(`test_build_video.CleanModeContractTest`,
`test_render_pipeline.test_20_clean_render_sem_srt_e_sem_legendas_queimadas`).

O caminho legado da fábrica (`tools/preset_runner.py` / `factory_cli.py`,
guardrails de tenant com `requireSrt`) não foi alterado nesta decisão; campanhas
antigas por esse caminho continuam produzindo legendas + SRT.

## Pacote padrão de entrega (modo clean)

- MP4 dos perfis solicitados (sem áudio, sem legendas queimadas);
- roteiro de narração TXT;
- player de revisão;
- verificações técnicas (ffprobe, checksums, áreas seguras, correlação de
  conteúdo, ausência de texto na antiga banda de legendas);
- ZIP portátil.

SRT e arquivos de legenda **não** são condição para concluir uma produção no
modo clean. Publicação e merge continuam sujeitos à autorização do titular.

## Referências

- Política anterior: seção "Regra de produção: vídeo sem áudio" em
  [../../AGENTS.md](../../AGENTS.md) e [../../WORKFLOW.md](../../WORKFLOW.md)
  (atualizadas nesta data, com histórico preservado).
- Primeiro caso: NS-001 v2.8, `editorial-v28/` (composição v2.7 sem
  `captionBand`, tipografia ampliada dentro das áreas seguras).
- Estado e continuidade: [../contexto/ESTADO-ATUAL.md](../contexto/ESTADO-ATUAL.md).