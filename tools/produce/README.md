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
