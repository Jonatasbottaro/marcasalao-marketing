# Operação Resultado 24 — Estabilização operacional e primeira campanha com imagens reais

Data: 2026-11-27
Branch de trabalho: `codex/operacao-resultado-24` (isolada; não integrada à `main`)
Base: `1efecbb` (fix editorial: fallback ASS quando o build FFmpeg não tem drawtext)
Escopo: resolver os impedimentos da Operação 23 e deixar o Video Studio pronto para uso rotineiro
(nova campanha → formato → criar/importar imagem → editar → visualizar → exportar → revisar).

> Regras respeitadas nesta operação: não modificar a `main`, não fazer merge nem deploy, não publicar,
> não executar chamadas pagas, não inserir chave no código, não imprimir credenciais, não sobrescrever
> a NS-001 v2.8, não descartar trabalhos existentes, não usar o simulador como imagem comercial final,
> não gerar mídia fictícia rotulada como real, não alterar o PWA Meu Salão, não guardar segredos nos
> arquivos exportados. As alterações preexistentes não commitadas no checkout principal foram preservadas
> (esta operação roda em worktree isolada, que não compartilha o working tree do checkout principal).

## Entregáveis desta operação

- Código (branch isolada, em revisão): ver "Mudanças de código" abaixo.
- Entrega de criativos v2: `.workspace/archives/operacao-resultado-24/delivery-v2/`
  - `01-post-45/01-capa.jpg` (1080×1350)
  - `02-carousel/01..04.jpg` + `carousel.zip` (1080×1080)
  - `03-reel/reel-instagram-9x16.mp4` (1080×1920, 19 s) + `03-reel/narracao-reel.txt`
  - `review/review.html` (página de revisão) + `review/board-carousel.png` + `review/storyboard-reel.png`
- Relatório e guia: este arquivo e [../guia-painel-video-studio.md](../guia-painel-video-studio.md).

## P1 — VIDEO CLEAN utilizável pelo painel (resolvido)

- **Causa raiz (Operação 23):** a flag `--clean` existia apenas na branch de recurso `feat/ns001-studio-bella-v2`
  (PR #33). No checkout principal ela é desconhecida, e nem o painel nem a fila a repassavam. Por isso a
  Operação 23 teve de renderizar de dentro da worktree.
- **Correção (mínima, sem recriar o VIDEO CLEAN):**
  - `tools/studio_queue.py`: modo de legenda no documento do trabalho (`CAPTIONS_MODES`), congelado no
    snapshot (`captionsMode`) e repassado como `--clean` ao `produce_video.py` quando `clean`.
  - `tools/video_studio.py`: normalização de `captionsMode` em `create_work` e `save_work`.
  - `tools/studio/index.html` + `tools/studio/app.js`: caixa "Vídeo limpo (sem legendas/SRT)" na barra do
    trabalho ativo, com leitura e gravação do estado.
  - `tools/tests/test_studio_queue.py`: teste `test_09_captions_mode_frozen_snapshot`.
- **Verificação:** pela API (create/save persistem `clean`/`burned`), pela UI real no navegador
  (reabrir trabalho mostra o estado salvo; marcar/desmarcar + Salvar grava `clean`/`burned` no `work.json`),
  e por render real: reel 1080×1920, 19 s, **1 stream de vídeo, 0 de áudio, sem SRT**, com roteiro de
  narração TXT separado.
- **Observação importante:** `--clean` só produz efeito onde o código do VIDEO CLEAN existe (a branch de
  recurso / o PR #33). Sem integrar o PR #33, o painel grava e tenta usar `clean`, mas o `--clean` só é
  aceito no ambiente que já tem esse código. A integração do PR #33 à `main` **não** foi feita e depende de
  autorização do titular.

## P1 — Imagem estática 4:5 nativa (resolvido)

- **Causa raiz:** o manifesto de projeto de exemplo (`platform/examples/projects/marca-salao-social.project.json`)
  não listava os perfis retrato; por isso `instagram-feed-image-portrait` (1080×1350) era rejeitado e a
  Operação 23 recorreu a redimensionar com FFmpeg.
- **Correção:** adicionados `instagram-feed-image-portrait` e `facebook-feed-image-portrait` ao allowlist do
  exemplo. Sem novo renderizador; reaproveita o pipeline de imagem existente.
- **Verificação:** geração nativa de um post 1080×1350 pelo pipeline, sem FFmpeg manual.

## Prontidão operacional — 14 itens

1. **Ambiente local.** `python tools/video_studio.py --port 8765` sobe em `127.0.0.1`; página inicial e
   `/static/app.js` servidos; servidor exige `Origin` local nas chamadas de escrita (proteção CSRF). OK.
2. **Fluxo do painel.** "Nova campanha/trabalho → formato → criar/importar imagem → editar → visualizar →
   exportar → revisar": verificável na barra lateral e nas abas de módulo. OK.
3. **VIDEO CLEAN no painel.** Caixa dedicada; estado persiste e é repassado à produção. OK (ver P1).
4. **Formato 4:5.** Perfis retrato disponíveis e render nativo 1080×1350. OK (ver P1).
5. **Carrossel 1:1.** 4 cards renderizados 1080×1080 + ZIP + manifest. OK.
6. **Reel vertical.** 1080×1920, 19 s, sem áudio e sem SRT; narração em TXT separado. OK.
7. **Provider Gemini.** **Indisponível** nesta estação: `GEMINI_API_KEY` ausente; provider
   `google-gemini` reporta `available: false`, modelo `gemini-3.1-flash-image`. Configurar a chave
   autorizada (fora do código) e reiniciar o Studio. Nenhuma chamada paga foi feita.
8. **Importação manual (sem IA).** `providerId: manual` disponível e sem credencial — copie o pedido visual,
   gere em ferramenta autorizada e importe o arquivo. É o caminho garantido quando não há chave de IA.
9. **Simulador.** Disponível, marcado como simulado; usar apenas para teste/demonstração, nunca como arte
   comercial final.
10. **Fluxo ComfyUI + proveniência.** Fluxo oficial em `marcas/marcasalao/comfyui/` com o validador
    versionado `marcasalao_media_guard.py` (bloqueia DRAFT com mídia não validada). Não fazer upload por
    outro cliente/caminho para contornar o gate.
11. **Revisão visual.** Página `review.html` com post ampliado, board do carrossel, storyboard, player do
    reel e rótulos de origem. **Aprovação estética final pendente de inspeção humana** — o modelo em uso
    não lê imagens; não substituir por métricas automáticas.
12. **Exportação/ZIP e armazenamento.** Carrossel gera `carousel.zip`; entregas por trabalho em
    `.workspace/studio/works/<id>/deliveries/...`; nada é publicado (tudo com `autoPublish: false`).
13. **Portabilidade.** Tudo dentro de `<RAIZ>`; auxiliares em `<RAIZ>/.workspace/`; sem caminho literal de
    máquina em documento versionado; alinhamento por Git.
14. **Testes e isolamento git.** Testes de fila executados (8 casos + novo caso de `captionsMode`); mudanças
    em branch isolada, sem tocar a `main`, sem merge/deploy/publish.

## Mudanças de código (branch isolada)

```
platform/examples/projects/marca-salao-social.project.json   + perfis retrato 4:5 no allowlist
tools/studio_queue.py                                        + CAPTIONS_MODES, snapshot e --clean
tools/video_studio.py                                        + normalização de captionsMode
tools/studio/index.html                                      + caixa "Vídeo limpo"
tools/studio/app.js                                          + leitura/gravação do captionsMode
tools/tests/test_studio_queue.py                             + test_09_captions_mode_frozen_snapshot
tools/tests/test_video_studio.py                             ~ test_profiles_local_export (4:5 passa de blocked para allowed)
```

Testes executados (todos OK): `test_studio_queue` (9 casos, incluindo o novo), `test_video_studio` +
`test_studio_video_api` (55 casos), `test_multi_format` (12 casos).

## Pendências deixadas para decisão do titular

- Integrar (ou não) o PR #33 à `main` para o `--clean` valer no ambiente principal.
- Configurar `GEMINI_API_KEY` fora do código se quiser geração por IA no painel.
- Inspeção visual humana da entrega v2 antes de qualquer publicação.
