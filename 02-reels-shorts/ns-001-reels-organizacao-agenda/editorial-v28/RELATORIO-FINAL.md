# NS-001 — Studio Bella — v2.8 — Relatório final (VIDEO CLEAN)

Pedido: `NS-001-P001-Studio-Bella-v2.8` · branch `feat/ns001-studio-bella-v2` · PR #33 (rascunho, sem merge) · publicação não autorizada.

Motivo: decisão do titular de 26/11/2026 — **VIDEO CLEAN / narração separada**
(`docs/decisoes/MKT-VIDEO-002-video-clean-narracao-separada.md`): sem legendas
narrativas queimadas, sem SRT por padrão, narração TXT separada, textos editoriais
preservados, espaço da antiga banda de legendas reaproveitado.

## A. O que mudou em relação à v2.7

- Composição sem `captionBand`: a antiga faixa y 1500–1700 (banda de legendas +
  faixa de contraste) deixa de existir; o fundo é limpo até a base.
- Tipografia ampliada com o espaço liberado: hora 170→200 px, serviço 68→76 px,
  chip 56→60 px (cena 1); status 130→144 px, linha 46→52 px (cena 2); heading 72→80 px.
- Conteúdo distribuído mais baixo (microcopy da cena 1 em y 1170, fundo ≈ 1204),
  ainda dentro da área segura mais restritiva (Reels, base 1247).
- Render pelo caminho VideoRequest com `--clean`: sem filtro `subtitles`, sem SRT
  gerado/validado/promovido, narração TXT preservada, manifesto com
  `captionsMode: "clean"`.
- Cenas, tempos, narração, valores editoriais, fontes e enquadramento idênticos aos
  da v2.7; cenas 3/4 (artes aprovadas v2.4) byte-idênticas.

## B. Implementação retrocompatível (sem reconstruir a fábrica)

- Contrato TS VideoRequest v1 inalterado (`caption` continua obrigatório por cena;
  a queima de legendas era opção do adaptador Python, não do contrato).
- `tools/render_local.py`, `tools/render_pipeline.py`, `tools/produce_video.py`:
  opção `--clean` (default `False`); sem a flag, comportamento legado byte-idêntico
  (legenda queimada + SRT validado) para campanhas antigas.
- Caminho legado da fábrica (`preset_runner`/`factory_cli`, guardrails `requireSrt`)
  não foi alterado por esta decisão.
- Nenhum áudio em nenhum caminho; `-an` preservado.

## C. Composição v2.8

- Manifesto versionado `campanha-v28.editorial.json` + pedido
  `pedido-editorial-v28.video-request.json`; fontes reutilizadas de
  `editorial-v27/fontes/` (sem recaptura, sem nova chamada de imagem).
- Motor reutilizável `tools/editorial_compose.py` sem alteração de contrato
  (`captionBand` já era opcional).
- Mesma proveniência verificada da v2.7: captura real
  `CAP-02-inapp-semana-scroll.png` (SHA-256 `52424a3d…`), valores conferidos por
  snapshot de acessibilidade + OCR pt-BR; artes aprovadas v2.4 (`455505b4…`,
  `a08bbe4d…`).

## D. Validação audiovisual (objetiva, sem visão)

- Master e 3 perfis: 1080×1920, 30 fps, 22 s, h264, yuv420p, **0 faixas de áudio** (FFprobe).
- Antiga banda de legendas (y 1500–1700): **100% cor única de fundo** nas 4 cenas
  (`#EBF9F5`/`#EAFBF6`/`#ECFAF6`) — sem texto queimado, sem faixa reservada.
- Correlação de conteúdo (canal R, y < 1500) frame final × fonte editorial:
  c1 0,9995 · c2 0,9990 · c3 0,9977 · c4 0,9999.
- OCR pt-BR em 360×640 recuperou os textos essenciais: "09:00", "Mechas e
  Iluminação", "Confirmado" (c1); "Concluído", "16:30 · Coloração Completa" (c2);
  "Conheça o Marca Salão" (c4).
- Áreas seguras: 0 violações de geometria nos 3 perfis; fundo máximo do conteúdo
  y ≈ 1203,6 < 1247 (Reels); limite horizontal Shorts (direita 992) respeitado.
- MP4 dos 3 perfis byte-idênticos: SHA-256
  `8e2406f761b28eb40da82780292b6621a4ba5ae10a9fe31f110df12d481962fc`.
- PNGs das cenas 3/4 byte-idênticos aos da v2.7 (`298de79f…`, `48bb51d4…`).

## E. Testes

- `CleanModeContractTest` (tools/tests/test_build_video.py, 6 testes fast): grafo
  clean sem `subtitles`, grafo legado preservado, comando `-an`, assinaturas
  retrocompatíveis (`clean=False`), CLI `--clean`, campo `captionsMode`.
- `test_20_clean_render_sem_srt_e_sem_legendas_queimadas`
  (tools/tests/test_render_pipeline.py, render real): clean sem SRT/legenda,
  narração preservada, hashes do manifesto reconfere, FFprobe 0 áudio; legado do
  mesmo caso continua com SRT válido; comparação de frames confirma conteúdo
  idêntico (MAE < 1,0) e banda diferenciada.
- `TestVideoCleanV28` (tools/tests/test_editorial_compose.py, 3 testes fast):
  manifesto v2.8 válido sem `captionBand`, pedido mapeia 1:1, v2.7 preservada.
- Gate smoke: 415/416; única falha pré-existente de ambiente
  (`test_publish_pack.test_08_resolve_workspace_root`, documentada desde a v2.7).
- Suíte render completa (test_render_pipeline, test_render_local,
  test_produce_video, test_editorial_compose_render): **93/93 OK, 0 falhas,
  0 erros, 0 skips** (960 s, render real com ffmpeg portátil + bridge da platform);
  evidência em `<RAIZ>/.workspace/tmp/ns001-studio-bella-v28/qc/testes-render.json` (local).

## F. Entrega (pacote portátil, fora do Git)

Em `<RAIZ>/.workspace/tmp/ns001-studio-bella-v28/entrega/`:

- `NS-001-Studio-Bella-v2.8-{instagram,facebook,youtube}.mp4`
- `review.html` (player com abas por perfil, marcadores de cena e nota clean)
- `ns001_roteiro_001_v28_studio_bella_narracao.txt` — **sem SRT** (modo clean)
- `NS-001-Studio-Bella-v2.8-final.zip`
- `qc/relatorio-qc.json`, `qc/composition-report.json` (sanitizado),
  `qc/checksums.txt`, `qc/frames/` (360×640 + OCR), `qc/banda-legendas/`,
  `qc/verificacao-banda-legendas.json`, `qc/correlacao-conteudo.json`,
  `qc/verificacao-areas-seguras.{json,md}`, `qc/areas-seguras/` (overlays),
  `qc/comparacao-v27-v28.md`, `qc/gate-smoke.json`
- Pastas por perfil com manifestos de entrega do pipeline (`captionsMode: clean`).

Versionados: manifesto e pedido neste diretório, este relatório, narração em
`04-legendas/`, decisão em `docs/decisoes/`, regras em `AGENTS.md`/`WORKFLOW.md`.
A v2.7 e todo o histórico permanecem intactos.

## G. Limitações e pendências

- Áreas seguras são aproximações (Meta Reels / Shorts); validar na interface real
  antes de publicar. Legendas futuras (CapCut/Canva) devem respeitar as margens.
- Aprovação editorial do titular pendente; publicação e merge não autorizados.
- Áudio/narração serão gerados pelo titular fora do editor, a partir do TXT.
