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
pipeline, para criar, revisar e exportar pelo navegador:

```bash
python tools/video_studio.py --port 8765   # abra http://127.0.0.1:8765
```

Fluxo no painel:
1. **Projeto e destinos** — selecione o `ProjectManifest`; os perfis vem do
   catalogo + allowlist, com resolucao, FPS e disponibilidade de exportacao local
   (9:16@30). Marque Instagram Reels, Facebook Reels e YouTube Shorts.
2. **Rascunho** — carregue um exemplo (Marca Salao / Multitrack Hub), salve e
   reabra o pedido (`VideoRequest v1`) em `.workspace/`.
3. **Midias** — escaneie uma pasta de trabalho dentro da raiz ou gere midia
   ficticia do rascunho; origem e licenca declarada ou `pending`; reutilize a
   mesma midia em varias cenas.
4. **Cenas** — adicione, edite, remova e reordene; duracao, legenda, titulo
   sobreposto e narracao em campos proprios.
5. **Previa** — `produce_video.py --plan-only --json`: linha do tempo, duracao
   total, avisos e erros por perfil, sem FFmpeg.
6. **Exportacao** — `produce_video.py` em segundo plano; resultado por perfil ao
   terminar.
7. **Entrega** — assista ao MP4 no painel e baixe MP4/SRT/TXT por referencias
   verificadas nos manifestos; reexporte somente um perfil.

Seguranca: escuta apenas `127.0.0.1`; valida Host e Origin nas escritas; confina
entradas/saidas a raiz (rascunhos e entregas em `.workspace/`); serve arquivos
apenas por referencias dos manifestos promovidos; processos com argumentos
estruturados. O indice separa `lastAttempt` (tentativa mais recente) de
`lastValidDelivery` (ultima entrega valida): uma reexportacao que falha mostra o
erro e continua permitindo abrir a entrega anterior, com hashes preservados.

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
- **Painel**: editor de cards (adicionar/reordenar/remover), previa, exportacao,
  imagens na ordem do manifesto com download individual e do ZIP.