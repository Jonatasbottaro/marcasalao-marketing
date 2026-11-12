# Adaptador de render local de prova — CreativeExecutionPackage v1

Primeiro adaptador de renderização local do projeto, autorizado pelo titular em
12/11/2026 como **prova técnica com dados fictícios**. Consome o
`CreativeExecutionPackage` v1 versionado e uma associação explícita de assets
locais por beat, e produz uma entrega real e inspecionada:

- MP4 H.264 / yuv420p, **sem nenhuma faixa de áudio**;
- SRT em UTF-8 (LF, newline final única) derivado dos textos e tempos do pacote;
- narração em TXT separada, organizada por cena e tempos, sem geração de voz;
- relatório JSON do render real com IDs, caminhos relativos, medições FFprobe e
  SHA-256 dos artefatos.

Não é campanha, não é produção real da NS-001, nada aqui é publicado. O
adaptador é uma ferramenta de verificação da fronteira entre planejamento
(pacote) e execução (mídia local); o executor `simulation` da platform continua
intacto e segue sem produzir mídia.

## Arquitetura e fronteiras

```
CreativeExecutionPackage v1 ─┐
                             ├─ validateLocalRenderInput (platform, puro)
associação beats → assets ───┘        │  veredito JSON via tools/render_bridge.mjs
                                      ▼
                        tools/render_local.py (camada de ferramentas)
                          staging → render FFmpeg → inspeção FFprobe
                          → validação SRT/narração → promoção transacional
```

- A validação do pacote reutiliza `validateCreativeExecutionPackage` e o
  contrato de associação vive em
  `platform/src/local-render-input-contract.ts` /
  `platform/src/validate-local-render-input.ts` (núcleo puro, sem I/O).
  A ponte `tools/render_bridge.mjs` apenas serializa o veredito; **a execução
  do FFmpeg acontece somente em `tools/`**, fora do núcleo e fora do tarball.
- A API pública da platform permanece `["validateComposition"]`; nenhum
  subpath novo, nenhuma dependência runtime nova.
- Sem fornecedor, sem rede, sem upload, sem publicação, sem Postiz, sem
  Temporal, sem banco, sem deploy.

## Recorte inicial suportado

| Dimensão | Valores aceitos |
| --- | --- |
| Geometria | vertical `9:16`, dimensões pares (as fixtures: 1080×1920) |
| FPS | 30 |
| Container | `mp4` (ou ausente no pacote) |
| `motionIntent` | `none`, `slow-zoom` (zoom central de 1.00 a 1.10 via `scale` animado + `crop` fixo) |
| `transitionIn` | `none`, `cut` |
| `transitionOut` | `cut`, `fade` (fade de 0,5 s somente no último beat) |
| Assets | `.png`, `.jpg`, `.jpeg`, `.webp`, `.mp4`, `.mov` |

Fora do recorte, o núcleo devolve `RENDER_CONFIGURATION_UNSUPPORTED` com o
campo culpado (`subject`) e nada é renderizado. Associação ausente, duplicada,
desconhecida, com caminho absoluto/traversal ou extensão não suportada recebe
código estável próprio antes de qualquer render.

## Associação de assets

Arquivo JSON versionado por consumidor (`marca-salao.assets.json`,
`multitrack-hub.assets.json`): `schemaVersion`, `packageId` (eco do pacote) e
`assets[]` com exatamente uma ligação `beatId → path` por beat da timeline.
Caminhos são relativos à raiz do checkout; a contenção real (realpath) e a
existência física são verificadas pela camada de ferramentas antes do render.

Os assets das provas são **fictícios e determinísticos**, gerados por
`tools/make_proof_assets.py` (stdlib apenas) em `.workspace/` — não são
versionados e não reutilizam mídia de campanha.

## Comando reproduzível

Requisitos: Python 3 padrão, Node com o build da platform
(`npm run build` em `platform/`), FFmpeg e FFprobe no PATH **ou** em
`.workspace/tools/ffmpeg/` (o adaptador acrescenta esse diretório ao PATH
apenas do processo). Testado com FFmpeg 9.0.2.

A partir da raiz do checkout:

```bash
# 1. assets fictícios (uma vez por consumidor)
python tools/make_proof_assets.py \
  --package platform/examples/execution-packages/execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan.execution-package.json \
  --output-dir .workspace/tmp/local-render-adapter-v1/assets/marca-salao
python tools/make_proof_assets.py \
  --package platform/examples/execution-packages/execution-multitrack-hub-multitrack-social-reel-example-instagram-reels-video-multitrack-social-reel-beat-plan.execution-package.json \
  --output-dir .workspace/tmp/local-render-adapter-v1/assets/multitrack-hub

# 2. render real + inspeção + promoção transacional
python tools/render_local.py \
  --package platform/examples/execution-packages/execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan.execution-package.json \
  --assets tools/render/marca-salao.assets.json \
  --output-dir .workspace/archives/local-render-adapter-v1/marca-salao --json
python tools/render_local.py \
  --package platform/examples/execution-packages/execution-multitrack-hub-multitrack-social-reel-example-instagram-reels-video-multitrack-social-reel-beat-plan.execution-package.json \
  --assets tools/render/multitrack-hub.assets.json \
  --output-dir .workspace/archives/local-render-adapter-v1/multitrack-hub --json

# 3. inspeção independente
ffprobe -v error -show_streams -show_format -of json \
  .workspace/archives/local-render-adapter-v1/marca-salao/*-primary-output.mp4
```

As diferenças entre as duas marcas vêm exclusivamente dos pacotes e dos
assets: mesma CLI, mesmo código, zero regra por marca.

### Exit codes

| Código | Significado |
| --- | --- |
| 0 | entrega promovida e inspecionada |
| 1 | falha de render, inspeção, promoção ou asset físico ausente |
| 2 | uso, caminho fora da raiz ou JSON/arquivo de entrada inválido |
| 3 | pacote ou associação reprovados pelo núcleo (código estável em stderr) |

## Comportamento transacional

1. Todos os artefatos nascem em staging (`<output-dir>.staging` por padrão);
2. inspeção prévia de cada asset com FFprobe exigindo stream de vídeo
   decodificável com dimensões (um asset ilegível com `-loop 1` faria a
   ferramenta de vídeo girar sem falhar, e o exit code do ffprobe sozinho não
   prova legibilidade: pode ser 0 com streams vazios para lixo binário);
   inspeção FFprobe do MP4 (1 stream de vídeo, **0 de áudio**, codec,
   geometria, fps, pix_fmt, duração), validação do SRT e da narração; o render
   tem tempo limite de 300 s, convertido em falha controlada;
3. relatório JSON com hashes SHA-256 e medições;
4. promoção com backup: destinos anteriores são copiados para
   `.backup/` dentro do staging e só então substituídos; qualquer falha de
   promoção restaura a entrega anterior completa;
5. falha em qualquer etapa: exit ≠ 0, erro sanitizado em stderr, staging
   preservado para diagnóstico, nenhum destino parcial.

A prova reproduzível está em `tools/tests/test_render_local.py`
(`test_04` a `test_09`, incluindo `test_07b`): pacote inválido, asset ausente,
asset fora da raiz, asset ilegível, falha da ferramenta de video e falha de
promoção comparam SHA-256 de todos os arquivos da entrega anterior antes/depois.

## Evidências

- Saídas de render e relatórios: `.workspace/archives/local-render-adapter-v1/`
  (locais; MP4 não versionado, mesma política do R002);
- manifesto versionado com hashes, bytes, FFprobe e comando:
  `02-reels-shorts/prova-render-local/manifest.json`;
- logs, quadros de prova (legenda, zoom, fade) e FFprobe completo:
  `.workspace/logs/local-render-adapter-v1/`.

## Testes

```bash
python -m unittest discover -s tools/tests -v   # inclui R002 e o render real
cd platform && npm run typecheck && npm test    # núcleo, ponte e barreiras
```

Testes que exigem FFmpeg ou o build da platform são ignorados quando ausentes;
o resultado local com FFmpeg e o observado na matriz de CI são registrados
separadamente no contexto e no handoff.

## Limites

- prova técnica local com mídia fictícia; nenhuma aprovação editorial;
- nenhum áudio em nenhuma etapa; nenhum TTS, fornecedor ou serviço pago;
- recorte inicial fechado (tabela acima); sem crossfade entre beats, sem
  parallax, sem áudio, sem legendas estilizadas por marca;
- não altera `platform/` além da ponte interna de validação, não altera a API
  pública, não entra no Temporal, não publica nada;
- os MP4 existem apenas neste computador enquanto permanecerem em
  `.workspace/`; o manifesto versionado preserva hashes e comando.
