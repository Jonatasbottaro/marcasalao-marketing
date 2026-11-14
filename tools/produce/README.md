# Producao de video por entrada unica — demonstracao

Um operador descreve as cenas em um JSON (`VideoRequest v1`), confere a previa e
exporta o video para os perfis escolhidos. O mesmo pedido gera os tres destinos
(`instagram-reels-video`, `facebook-reels-video`, `youtube-shorts`) a partir da
mesma fonte de cenas e midia. Videos sem faixa de audio, com legenda queimada,
SRT e roteiro de narracao em TXT separado.

## Pre-requisitos

- Node >= 22 e Python 3.12.
- FFmpeg e FFprobe no PATH (no CI, a acao `FedericoCarboni/setup-ffmpeg`; localmente,
  um build portatil em `.workspace/tools/ffmpeg` exposto no PATH do processo).
- Build da platform: `cd platform && npm ci && npm run build && cd ..`.

Toda midia gerada, temporarios e evidencias ficam em `.workspace/` da raiz do
checkout. Nada e publicado nem aprovado editorialmente: os casos gerados sao
rascunhos editoriais (`metadata.status = draft`).

## Caminho mais curto (Marca Salao)

```bash
# 1. Midia ficticia deterministica (PNG por material cadastrado)
python tools/make_request_media.py \
  --input tools/produce/examples/marca-salao-social-reel.video-request.json

# 2. Previa: perfis resolvidos, duracao, tempos por cena, midias e avisos (sem FFmpeg, sem gravacao)
python tools/produce_video.py \
  --input tools/produce/examples/marca-salao-social-reel.video-request.json \
  --plan-only --json

# 3. Exportacao dos tres destinos a partir de um unico pedido
python tools/produce_video.py \
  --input tools/produce/examples/marca-salao-social-reel.video-request.json \
  --output-dir .workspace/archives/produce-video-demo/marca-salao --json
```

Cada perfil entrega um subdiretorio com MP4 (`*-primary-output.mp4`), SRT
(`*-captions.srt`), narracao (`*-narration-script.txt`), pacote canonico,
inventario de midia, relatorio de render e `delivery-manifest.json`. O indice
`index.json` na raiz da entrega reune os manifestos finais e o estado por perfil.

## Reexportar um perfil apos corrigir cena ou titulo

Edite o pedido (por exemplo, o `title` de uma cena) e reexporte apenas um perfil.
A midia nao muda: o `AssetManifest` e reutilizado com os mesmos hashes.

```bash
python tools/produce_video.py \
  --input tools/produce/examples/marca-salao-social-reel.video-request.json \
  --profile youtube-shorts \
  --output-dir .workspace/archives/produce-video-demo/marca-salao --json
```

Uma falha em um perfil preserva a entrega anterior daquele perfil e nao impede
os demais perfis validos. O codigo de saida e diferente de zero quando algum
perfil falha.

## Segundo pedido (Multitrack Hub), mesmo comando

```bash
python tools/make_request_media.py \
  --input tools/produce/examples/multitrack-hub-social-reel.video-request.json
python tools/produce_video.py \
  --input tools/produce/examples/multitrack-hub-social-reel.video-request.json \
  --output-dir .workspace/archives/produce-video-demo/multitrack-hub --json
```

## Inspecionar os MP4 finais

```bash
ffprobe -v error -show_streams -show_format -of json \
  .workspace/archives/produce-video-demo/marca-salao/youtube-shorts/*-primary-output.mp4
```

Esperado: 1 stream de video, 0 de audio, 1080x1920, 30 fps, H.264/yuv420p,
duracao igual a soma das cenas (14 s no exemplo).

## Contrato do pedido

`schemaVersion`, `id` (kebab-case), `project` (caminho relativo a raiz do
ProjectManifest), `title`, `profiles` (ids do catalogo, sujeitos a allowlist do
projeto), `visualStyle` opcional reutilizavel, `media` (cadastro unico por
material, com `origin` e `license` declarada ou `pending`) e `scenes` ordenadas
(`durationMs`, `mediaId`, `caption`, `narration`, `title` opcional,
`narrativeFunction` e `motionIntent` opcionais). Uma midia pode ser vinculada a
varias cenas. O recorte local e 9:16 a 30 fps, movimento `none|slow-zoom`,
transicoes `cut` e `fade` (fade apenas no ultimo beat).

## Painel local (Video Studio)

`tools/video_studio.py` serve um painel HTML/CSS/JS em `127.0.0.1` sobre o mesmo
pipeline, com cadastro de projetos, trabalhos persistentes, midias compartilhadas
e retomada apos fechar e reabrir o servidor:

```bash
python tools/video_studio.py --check --json   # diagnostica Python, Node, build, FFmpeg e FFprobe
python tools/video_studio.py --port 8765      # abra http://127.0.0.1:8765
```

Fluxo no painel:
1. **Prontidao e demonstracao guiada** — a barra superior consulta `/api/readiness`
   e aponta eventuais faltas com instrucao direta; em 1 clique, **Demonstracao
   guiada** cria um trabalho completo para Marca Salao ou Multitrack Hub.
2. **Projetos (`ProjectManifest` v1)** — cadastre novos projetos pelo formulario
   (`POST /api/projects/create`), validados pelo nucleo da `platform` e salvos
   em `.workspace/studio/projects/<id>.project.json`, com distincao visual entre
   projetos cadastrados e exemplos versionados.
3. **Trabalhos persistentes e retomada** — crie (`POST /api/works/create`) ou
   reabra (`GET /api/works/open`) trabalhos em `.workspace/studio/works/<id>/`.
   Rascunhos (`video.video-request.json`, `carousel.carousel-request.json`,
   `motion.motion-plan.json`), pasta `media/` compartilhada e `deliveries/` sao
   derivados automaticamente sem digitar caminhos (o modo avulso legado fica
   recolhido em detalhe opcional). Escritas usam substituicao atomica.
4. **Destinos filtrados por projeto e modulo** — `/api/profiles?project=...&module=video|carousel|motion`
   exibe apenas os destinos permitidos pela allowlist e compativeis com o editor
   aberto (9:16@30 para Video/Motion, 1:1 para Carrossel).
5. **Midias, Cenas, Carrossel e Motion multi-cena** — importe midias da pasta
   do trabalho para reutilizacao entre pecas, edite `VideoRequest`, `CarouselRequest`
   ou contornos `MotionPlan` em multiplas cenas sem zoom (alternando entre cenas
   sem perder alteracoes) e salve pelo botao **Salvar trabalho** (`/api/works/save`).
6. **Previa, exportacao e preservacao em falha/reinicio** — conferencia de previa
   sem FFmpeg (`/api/preview`), exportacao em segundo plano (`/api/export`) e
   registro persistente de status em `.workspace/studio/export-status/`. O painel
   separa `lastAttempt` (`failed`, ou `interrupted` quando um job ativo e
   encontrado orfao apos reiniciar o servidor) de `lastValidDelivery`: erros
   aparecem claramente sem apagar ou esconder a ultima entrega valida.

Seguranca: escuta apenas `127.0.0.1`; valida Host e Origin nas escritas; confina
entradas/saidas a raiz (`.workspace/`); serve arquivos verificados pelos
manifestos ou imagens da pasta autorizada de origem (`/source-media`); processos
com argumentos estruturados e caminhos longos do Windows tratados por
`render_local.fs_path`. O painel registra o historico em `.workspace/studio/export-status/`
e separa `lastAttempt` de `lastValidDelivery`: qualquer reexportacao que falha
ou e interrompida exibe aviso proprio e preserva a ultima entrega valida.

## Carrosséis (R003)

A aba **Carrosséis** do painel e a CLI `tools/produce_carousel.py` produzem
carrosséis de imagens a partir de `CarouselRequest v1`
(`platform/src/carousel-request-contract.ts`, `validate-carousel-request.ts`,
`platform/schemas/carousel-request.schema.json`). O perfil de imagem
(`instagram-feed-image-square`) e resolvido pelo catalogo + allowlist do projeto
via `resolveOutputPlan`; a geometria vem do perfil (1080×1080).

```bash
python tools/make_request_media.py --input tools/produce/examples/marca-salao-carousel.carousel-request.json
python tools/produce_carousel.py --input tools/produce/examples/marca-salao-carousel.carousel-request.json --plan-only --json
python tools/produce_carousel.py --input tools/produce/examples/marca-salao-carousel.carousel-request.json --output-dir .workspace/archives/carrossel --json
```

- **Pedido**: id, projeto, perfil de imagem, titulo, cadastro reutilizavel de
  midias (origem/licenca declarada ou `pending`) e cards ordenados (id, titulo,
  corpo opcional, referencia opcional a midia). Texto editavel no pedido.
- **Previa** (`--plan-only`): ordem, geometria e erros/overflow por card, sem
  FFmpeg e sem gravacao. Texto que excede a area indica o card a ajustar.
- **Render**: JPEGs 1080×1080 com layout reutilizavel (margens, contraste, quebra
  de linha); FFmpeg decodifica/escala a midia e converte PNG→JPEG. Nomes
  numerados (`01-capa.jpg`, `02-conteudo.jpg`, …).
- **Entrega**: `carousel.zip` na mesma ordem + `carousel-manifest.json` (id do
  pedido, dimensoes, caminhos relativos, tamanhos, SHA-256) + `index.json`
  (`lastAttempt`/`lastValidDelivery`). Promocao do conjunto sob lock com backup;
  falha preserva a ultima entrega valida; remover card e reexportar reflete a
  nova ordem no conjunto ativo e no ZIP.
- **Painel**: integrado ao trabalho ativo (caminhos e midias compartilhadas) ou
  em rascunho avulso; editor de cards, previa, exportacao, miniaturas na ordem e ZIP.

## Motion (aba e CLI)

Na aba **Motion**, selecione qualquer cena sem `slow-zoom` em `#m-scene-select`,
marque a regiao no canvas e gerencie efeitos em multiplas cenas no mesmo
`MotionPlan` (`effects[]`). Pela CLI:

```bash
python tools/produce_video.py --input tools/produce/examples/marca-salao-motion.video-request.json --motion-plan tools/produce/examples/marca-salao-motion.motion-plan.json --output-dir .workspace/archives/motion --json
```

## Revisão & Entrega e pacote ZIP final (`studio_review.py` + `delivery_package.py`)

Fluxo integrado no Studio local: **Criar trabalho → Preencher ficha → Exportar → Revisar → Baixar ZIP**.

1. **Ficha editorial e textos por canal (`editorial.json`)**:
   - Campos do briefing do trabalho (`objective`, `audience`, `coreMessage`, `supportEvidence`, `hook`, `scriptSummary`, `cta`) e textos específicos de publicação por canal (`title`, `postText`, `cta`, `destinationUrl`, `hashtags`).
   - Trabalhos legados sem `editorial.json` abrem normalmente com a ficha em branco.
   - **Separação editorial rigorosa**: os textos por canal alimentam apenas `textos-por-canal/<perfilId>/publicacao.{json,txt}` e **não** modificam a legenda queimada/SRT (`.srt`), o roteiro de narração (`.txt`) nem os hashes dos MP4s exportados. Alterar apenas o texto de um canal marca somente aquele canal como `copy_outdated`, preservando intactos os demais canais e as peças já aprovadas.

2. **Vínculo por versão, decisões humanas e histórico (`review-state.json`)**:
   - Cada exportação feita pelo Studio registra vínculo explícito entre a entrega promovida e o snapshot de entrada (`VideoRequest`, `CarouselRequest`, `MotionPlan` + origens/licenças das mídias).
   - Entregas anteriores ou criadas externamente sem vínculo aparecem como `unlinked` (**Entrega externa sem vínculo**): é possível pedir ajustes (`changes_requested`), enquanto a aprovação (`approved_for_local_delivery`) fica bloqueada até reexportação pelo Studio.
   - Decisões suportadas por peça e por texto de canal: `approved_for_local_delivery` e `changes_requested` com observação e histórico completo preservado entre reexportações e reinícios do servidor.
   - Edições no `MotionPlan` invalidam somente as peças de **Motion** (`draft_outdated`) sem invalidar os Vídeos do mesmo destino; edições no `VideoRequest` sinalizam Vídeo e Motion. Em caso de conflito concorrente ou versão desatualizada, a API responde `HTTP 409` (`conflict: true`).
   - Falhas de reexportação preservam avisos (`lastAttempt`), o histórico de decisões, a última entrega válida e o último pacote ZIP gerado.

3. **Pacote ZIP de entrega transacional (`Gerar ZIP de entrega`)**:
   - Checklist interativo de peças e textos por canal com indicação clara do motivo de prontidão ou bloqueio; apenas itens explicitamente aprovados e íntegros (confinação à raiz + existência + SHA-256) são aceitos no empacotamento.
   - Escrita em staging exclusivo sob lock de promoção (`render_local.acquire_promotion_lock`) e promoção atômica com backup/rollback (`render_local.promote_with_backup`) em `.workspace/studio/works/<id>/deliveries/package/` (`delivery-package.zip`, `package-manifest.json` e `index.json`), preservando o pacote ZIP anterior em falhas de empacotamento ou promoção (`GET /api/works/review`, `POST /api/works/editorial/save`, `POST /api/works/review/decide`, `GET /api/works/artifact-text`, `GET|POST /api/works/package` e `GET /api/works/package/download`).
   - Estrutura interna padronizada no ZIP:
     - `briefing/ficha-editorial.{json,txt}`
     - `textos-por-canal/<perfilId>/publicacao.{json,txt}`
     - `video/<perfilId>/{primary-output.mp4, subtitles.srt, narration.txt}`
     - `motion/<perfilId>/{primary-output.mp4, subtitles.srt, narration.txt, motion-plan.json}` (separado de `video/<perfilId>/` mesmo quando o perfil de destino é o mesmo)
     - `carousel/<perfilId>/<N-card.jpg>` na ordem exata do `carousel-manifest.json`
     - `package-manifest.json` com hashes SHA-256, tamanhos e metadados técnicos conferidos antes da criação e no download.
   - Aba **Planejamento** (`planning.json`, `tools/studio_planning.py` e `tools/llm_adapter.py`): fluxo em 3 etapas (**1. Ideia e briefing** -> **2. Hook, roteiro e cards** -> **3. Aplicação aos editores**) nos modos **Manual**, **Copiar e importar** (`PlanningSuggestion` v1 validado pelo núcleo via `--planning-suggestion`) e **Modelo local opcional** (`POST /v1/chat/completions`, `qwen3:8b`, desativado por padrão), preservando edições manuais, checando políticas por projeto e aplicando alterações sem invalidar MP4s existentes quando somente textos de canal mudam (`copy_outdated`).

## Biblioteca de midia por trabalho (`studio_media.py` + `image_adapters.py`)

Fluxo integrado ao Planejamento: **Planejamento -> Preparar imagem -> Comparar opcoes -> Aplicar -> Exportar -> Revisar -> ZIP**.

### Contratos e estado

- `VisualAnchor` v1 (`platform/src/visual-anchor-contract.ts`, `validate-visual-anchor.ts`, espelho draft-07 `visual-anchor.schema.json` com paridade Ajv): referencia visual reutilizavel dentro do trabalho, vinculada a uma versao de midia pelo ID da versao e pelo SHA-256, com direcao visual, `mustInclude` e `mustAvoid`. Validada pelo nucleo via `node tools/render_bridge.mjs --visual-anchor <doc.json>`.
- `ImageRequest` v1 (`platform/src/image-request-contract.ts`, `validate-image-request.ts`, espelho draft-07 `image-request.schema.json` com paridade Ajv): pedido visual revisavel derivado do `requiredMediaDescriptor` de uma cena (`video_scene`) ou card (`carousel_card`), com prompt editavel, finalidade, enquadramento, proporcao e geometria derivadas do perfil, vinculo opcional de ancora (`sendToProvider`) e snapshot de contexto (`descriptor` + `contextSha256`). Validado via `node tools/render_bridge.mjs --image-request <doc.json>`. O provedor e escolhido por acao, fora do contrato, para aceitar novos adaptadores sem alterar pedidos existentes.
- Estado local por trabalho em `.workspace/studio/works/<id>/media-library.json`: assets com versoes imutaveis (ID proprio, SHA-256, dimensoes, formato, origem, licenca, proveniencia), ancoras, pedidos com candidatos/tentativas e selecoes por alvo. Escrita atomica, concorrencia otimista por `expectedLibraryFingerprint` (`HTTP 409`), contencao a raiz e miniaturas servidas apenas por referencias validas da biblioteca (`GET /library-media?work=&asset=&version=`, com conferencia de hash).
- Trabalhos legados abrem com a biblioteca inicializada deterministicamente a partir das midias ja referenciadas nos rascunhos; arquivos soltos na pasta de midia podem ser cadastrados sem copia (`POST /api/works/media/register`).

### Selecao, proveniencia e revisao localizada

- Cada importacao ou geracao cria uma versao nova; o arquivo de origem e as versoes antigas continuam disponiveis para reabrir trabalhos e conferir entregas anteriores.
- A selecao alimenta o catalogo de midia do Planejamento (`_build_work_media_catalog`) e o fluxo de previa de diferencas existente; o vinculo chega ao rascunho pelos campos atuais (`mediaId` + `media[]`). O `AssetManifest` do render materializa caminho, origem, licenca e hash da versao selecionada.
- Ilustracoes geradas (`generated-simulator`, `generated-google-gemini`) ficam distinguiveis de capturas/evidencias (`screenshot`) e de importacoes manuais na biblioteca, na Revisao & Entrega e no manifesto. Materiais do simulador sao marcados como simulados em todos os registros.
- Mudanca no texto do pedido ou na referencia marca candidatos anteriores como `stale` (contexto anterior). Trocar a versao de uma midia usada por um card invalida somente o carrossel; o video que usa outra versao mantem seu estado. Com `updateLinkedTargets`, todas as pecas consumidoras sao identificadas e atualizadas juntas.
- Falha de copia, leitura, validacao de conteudo ou checksum divergente preserva a versao valida e os vinculos anteriores.

### Adaptadores de imagem (um por acao confirmada)

1. **Importacao manual** (`POST /api/works/media/import` com `dataBase64` ou `sourcePath` confinado): funciona com o provedor desligado, sem chave e sem rede. Serve para importar materiais gerados em ferramentas externas (ex.: Google Flow), com origem informada (`origin`, `originDetail.tool`) e licenca declarada ou `pending`. Validacao pelo conteudo (PNG/JPEG/WebP por magic bytes), limite de 20 MB e dimensoes ate 16384 px.
2. **Simulador** (`SimulatorImageAdapter`): PNG deterministico derivado de prompt + geometria + hash da referencia; usado nos testes e na demonstracao guiada. Proveniencia registra `provider: simulator`, `model: simulator-v1`.
3. **Google Gemini opcional** (`GeminiImageAdapter`): `POST {endpoint}/v1/models/{model}:generateContent` com header `x-goog-api-key`, `generationConfig.responseModalities: ["TEXT","IMAGE"]` e `imageConfig.aspectRatio`; a referencia e enviada como `inline_data` somente quando o pedido marcar `sendToProvider`. Configuracao apenas por ambiente do processo: `GEMINI_API_KEY` (obrigatoria para habilitar), `STUDIO_GEMINI_IMAGE_MODEL` (padrao `gemini-3.1-flash-image`), `STUDIO_GEMINI_IMAGE_ENDPOINT` (padrao `https://generativelanguage.googleapis.com`), `STUDIO_GEMINI_TIMEOUT_SEC` (padrao 120). O painel exibe somente o estado (`GET /api/image/config`), nunca a chave. Diagnosticos em portugues para timeout (`IMAGE_PROVIDER_TIMEOUT`, HTTP 504), falta de credencial (`IMAGE_PROVIDER_NO_CREDENTIAL`, 503), cota (`IMAGE_PROVIDER_QUOTA`), recusa (`IMAGE_PROVIDER_REFUSED`), resposta sem imagem (`IMAGE_PROVIDER_NO_IMAGE`) e arquivo invalido (`IMAGE_PROVIDER_INVALID_FILE`); sem retry automatico — o operador decide nova tentativa.

Para adicionar outro provedor, implemente `generate(...)` em `tools/image_adapters.py`, registre-o em `provider_status()` e acrescente o ramo em `studio_media.generate_candidate`; `VisualAnchor`, `ImageRequest` e os pedidos dos editores nao mudam. A regra vigente de arte do Marca Salao via ComfyUI08 e seu guard de proveniencia seguem valendo para producao oficial e publicacao; este fluxo atende aos candidatos do Studio no escopo autorizado.

### Rotas HTTP novas

- `GET /api/works/media-library?id=` — visao geral (assets/versoes, ancoras, pedidos com candidatos e `stale`, selecoes, arquivos nao cadastrados, provedores).
- `POST /api/works/media/import` | `POST /api/works/media/register` — importacao e cadastro.
- `POST /api/works/media/anchor` — criar/atualizar referencia visual.
- `POST /api/works/media/request/create` | `POST /api/works/media/request/update` — pedido visual.
- `POST /api/works/media/generate` — geracao confirmada (`confirm: true`, `provider`).
- `POST /api/works/media/select` — selecao de versao e vinculo (opcional `updateLinkedTargets`).
- `GET /api/image/config` — estado dos provedores (sem credenciais).
- `GET /library-media?work=&asset=&version=` — miniatura por referencia valida.

### Testes e prova

- `platform/tests/visual-anchor.test.ts`, `image-request.test.ts` e paridade Ajv em `platform/tests/contracts/{visual-anchor,image-request}-schema.test.ts`.
- `tools/tests/test_studio_media.py`: contratos via ponte, importacao validada, versoes, selecao, concorrencia, checksum, simulador deterministico, Gemini simulado (sem rede), falhas, reinicio, isolamento entre marcas, materializacao no AssetManifest e revisao localizada (render real com `REQUIRE_RENDER=1`).
- `python tools/ci_media_library_proof.py --port 8797`: prova HTTP completa (import -> ancora -> pedido -> simulador -> Gemini sem chave -> stale -> selecionar/aplicar -> exportar video/carrossel -> AssetManifest -> FFprobe sem audio -> revisao localizada -> midia compartilhada -> arquivo invalido -> ZIP -> reinicio), executada no CI em Ubuntu e Windows junto da suite Python.

## Exportacao multiformato (horizontal 16:9 e carrossel 4:5)

Fonte compartilhada de exportabilidade local: `platform/src/output-profiles/local-export.ts`
(`localExportCapabilities(profile)` por modulo `video`/`carousel`/`motion`, com motivos
estaveis `MEDIA_KIND_MISMATCH`, `GEOMETRY_UNSUPPORTED`, `FPS_UNSUPPORTED`,
`MOTION_VERTICAL_ONLY`). A CLI `content:profiles` expoe `localExport` por perfil;
`video_studio.list_profiles`, o Planejamento, a biblioteca de midia e os seletores do
painel consomem a mesma resposta — nenhum segundo dicionario de formatos.

### Video horizontal

- `youtube-video-horizontal`: 1920x1080, 16:9, 30 fps, MP4 H.264, zero faixas de audio.
  O `OutputPlan` existente resolve a geometria; o adaptador (`render_local.py` /
  `render_pipeline.py`) renderiza a partir da geometria resolvida do pacote.
- Enquadramento: `scale=W:H:force_original_aspect_ratio=decrease` + `pad=W:H:(ow-iw)/2:(oh-ih)/2`
  + `setsar=1` (bandas de preenchimento centralizadas, sem distorcao). No carrossel o pad
  usa o tom do layout (`0x10141A`).
- Titulos (`build_title_style`): PlayRes acompanha a geometria; fonte e margem superior
  escalam por `height/1920`, margens horizontais por `width/1080` — no 9:16 os valores
  permanecem identicos aos estilos existentes. Legendas (`SUBTITLE_STYLE`): PlayRes
  explicito 384x288 (espaco SRT do libass), escala uniforme pela altura; margem inferior
  proporcional, cabendo na base do 16:9 (medicao de quadros nos testes).
- `--profile youtube-video-horizontal` (CLI) ou seletor do painel exportam apenas aquele
  destino; falha nele preserva as entregas validas dos demais (lock/promocao por perfil).
- Motion: restrito a 9:16 nesta rodada. A ponte rejeita `MotionPlan` em destino horizontal
  com `MOTION_LOCAL_UNSUPPORTED_GEOMETRY` somente naquele perfil; o seletor e a nota da
  aba Motion explicam o recorte (coordenadas relativas ao quadro final).

### Carrossel 4:5

- `instagram-feed-image-portrait` / `facebook-feed-image-portrait`: 1080x1350.
  `carousel_layout.measure_card/render_card/_draw_text` recebem a geometria do perfil
  (sem altura quadrada fixa); `produce_carousel.build_preview` mede overflow por card na
  geometria resolvida e `_media_rgb` preserva a proporcao da midia (fit + pad).
- Manifesto (`carousel-manifest.json`) registra `geometry` do perfil; JPEGs numerados na
  ordem do pedido, ZIP na mesma ordem, hashes conferidos a partir dos bytes finais.
- Overflow: `--plan-only` lista `overflowCards`; exportar com overflow falha com
  `CAROUSEL_TEXT_OVERFLOW` indicando o card e preservando o ultimo conjunto valido.
- No Planejamento, `carouselProfileId` (seletor 1:1 vs 4:5 quando ambos na allowlist)
  decide o destino aplicado aos editores; pedidos de imagem derivam geometria do perfil
  (16:9 e 4:5 ja aceitos pelo contrato `ImageRequest` v1) e mostram o reenquadramento da
  midia atual ao mudar o destino.

### Revisao e ZIP multiformato

Cada entrega e identificada por modalidade + perfil + versao (`review-state.json`).
Alterar somente o texto de um canal (ex.: YouTube horizontal) marca apenas aquele canal
como `copy_outdated`, preservando hashes dos MP4s e artefatos dos outros perfis. O ZIP
reune pecas e textos aprovados de varios destinos com caminhos separados
(`video/<perfil>/`, `carousel/<perfil>/`, `textos-por-canal/<perfil>/`) e manifesto
conferido contra os bytes do pacote.

### Comandos reproduziveis

```bash
python tools/produce_video.py --input <pedido> --profile youtube-video-horizontal --plan-only --json
python tools/produce_video.py --input <pedido> --profile youtube-video-horizontal --output-dir <entrega> --json
python tools/produce_carousel.py --input <pedido> --profile instagram-feed-image-portrait --plan-only --json
python tools/produce_carousel.py --input <pedido> --profile instagram-feed-image-portrait --output-dir <entrega> --json
python tools/ci_multi_format_proof.py --port 8796   # prova HTTP completa (CI Ubuntu/Windows)
```

Testes: `platform/tests/local-export.test.ts` (matriz por modulo),
`platform/tests/local-render-input.test.ts` (geometria horizontal dentro do recorte),
`tools/tests/test_multi_format.py` (render real, enquadramento, overflow, promocao,
revisao localizada, ZIP, isolamento entre marcas) e a etapa dedicada no workflow
`.github/workflows/local-render-validation.yml`.
