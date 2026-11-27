# Operação Resultado 25 — Consolidação do Video Studio e liberação para uso cotidiano

Data: 2026-11-27
Branch de trabalho: `codex/operacao-resultado-24` (worktree isolada `.workspace/worktrees/op24`)
Base do PR: `feat/ns001-studio-bella-v2` (head do PR #33)
Escopo: publicar e validar as correções da Operação 24, sem criar novos módulos.

> Regras respeitadas: não modificar a `main`, não fazer merge nem deploy, não publicar conteúdo,
> não executar chamadas pagas, não inserir chave no código, não imprimir credenciais, não alterar o
> PR #33, não usar force push. Alterações locais do checkout principal preservadas.

## 1. Estado do commit da Operação 24

- Commit `f01ed60` — "feat(studio): VIDEO CLEAN pelo painel + 4:5 nativo + guia operacional (Op 24)".
- Pai: `1efecbb` (topo de `feat/ns001-studio-bella-v2`, PR #33). Ou seja, a branch da Op 24 **contém**
  os commits do PR #33 abaixo de `f01ed60`.
- Antes desta operação o commit **não existia no GitHub** (branch sem upstream). Ver "Publicação".

## 2. Relação com o PR #33

- PR #33 (`feat/ns001-studio-bella-v2` → `main`) está **aberto e em rascunho**, não integrado.
- A branch da Op 24 **depende do PR #33**: o diff relevante é só `f01ed60`; por isso a base do novo PR
  é `feat/ns001-studio-bella-v2` (não `main`). O PR #33 não foi alterado.
- O modo VIDEO CLEAN (`--clean`) só tem efeito onde o código do PR #33 existe; a branch da Op 24 já o traz.

## 3. Publicação

- Branch `codex/operacao-resultado-24` publicada no GitHub (push normal, sem force push).
- Commits no GitHub:
  - `f01ed60` — correções da Op 24 (VIDEO CLEAN pelo painel + 4:5 nativo + guia).
  - `3077166` — guia de uso diário (Op 25) + este relatório + índice.
- Pull Request **#34 (rascunho)**: https://github.com/Jonatasbottaro/marcasalao-marketing/pull/34
  - base: `feat/ns001-studio-bella-v2` (head do PR #33); head: `codex/operacao-resultado-24`.
- PR #33 permanece aberto e em rascunho, base `main`, **inalterado**.
- `main` não foi tocada; nenhum merge, nenhum force push.

## 4. Testes executados

- `test_studio_queue` — 9/9 OK (inclui `test_09_captions_mode_frozen_snapshot`).
- `test_multi_format` — 12/12 OK.
- `test_video_studio` + `test_studio_video_api` — 56/56 OK (inclui `test_profiles_local_export`, do 4:5,
  e o novo `VideoCleanExportTest`: export legado gera SRT; export limpo no mesmo destino o remove).
- `test_render_pipeline` + `test_build_video` — 51/51 OK.
- Ambiente: worktree `.workspace/worktrees/op24`; FFmpeg/FFprobe portáteis do checkout principal
  alcançáveis pela worktree (junção em `.workspace/tools/ffmpeg`); Node do sistema.

## 4.1 Defeito P1 encontrado na validação do painel (§4)

A jornada real no navegador revelou que o botão **"Exportar vídeo"** não honrava o modo limpo:
`start_export` montava o comando de `produce_video.py` sem `--clean` e o `app.js` não enviava
`captionsMode`. Com "Vídeo limpo" marcado, o render saía legado (legenda queimada + `captions.srt`).

Correção aplicada (esta operação):

- `tools/video_studio.py::start_export` — aceita `captions_mode`, faz fallback para o `captionsMode`
  do trabalho salvo e acrescenta `--clean` (exceto carrossel); a rota `/api/export` repassa `captionsMode`.
- `tools/studio/app.js` — envia `captionsMode` nos exports de vídeo e motion.
- `tools/render_pipeline.py::run_render_pipeline` — ao renderizar em modo limpo, remove `captions.srt`
  estale deixado por uma exportação legada anterior no mesmo destino.
- `tools/tests/test_video_studio.py::VideoCleanExportTest` — regressão do caminho direto do painel.

Efeito verificado: reexport limpo → relatório com `captions: {mode: clean, burned: false}`, sem artefato
`srt`, MP4 1080×1920 com 1 stream de vídeo e 0 de áudio.

## 5. VIDEO CLEAN pelo painel

- `captionsMode` no documento do trabalho; congelado no snapshot da fila; repassado como `--clean`.
- Caixa "Vídeo limpo (sem legendas/SRT)" na barra do trabalho ativo, com leitura e gravação do estado.
- Render resultante: MP4 1080×1920, 1 stream de vídeo, **0 de áudio**, sem SRT, roteiro TXT separado.

## 6. Imagem 4:5 nativa

- Perfis `instagram-feed-image-portrait`/`facebook-feed-image-portrait` no allowlist do projeto de exemplo.
- Post 1080×1350 gerado pelo pipeline; entregas confirmadas por `ffprobe`.

## 7. Gemini / ComfyUI

- **Gemini: indisponível** nesta estação — `GEMINI_API_KEY` ausente; nenhuma chamada paga feita.
  Importação manual é o caminho garantido (sem credencial). Chave configura-se **fora do código**.
- **ComfyUI:** fluxo versionado em `marcas/marcasalao/comfyui/` com o validador `marcasalao_media_guard.py`.
- Imagem ilustrativa de teste ≠ arte comercial aprovada; simulador nunca é arte final.

## 8. Entregas preservadas

- `.workspace/archives/operacao-resultado-24/delivery-v2/` — post 4:5, carrossel + ZIP, reel + narração,
  página de revisão e `manifest.json` (15 arquivos; SHA-256 conferidos). Não versionada; local.

## 9. Guia de uso cotidiano

- `docs/guia-painel-video-studio.md` — 9 passos + seção "O que se repete em outro computador".

## 10. Riscos residuais e pendências

- Aprovação visual humana das peças v2 pendente (o agente não lê imagens).
- Integração do PR #33 e desta branch à `main` depende de autorização do titular.
- Gemini exige configuração de chave por estação.

## 11. Confirmação

- Sem merge, sem deploy, sem publicação. `main` intacta. PR #33 intacto.
