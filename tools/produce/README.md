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