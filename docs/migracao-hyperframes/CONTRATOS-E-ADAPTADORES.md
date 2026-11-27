# Contratos e adaptadores — HF-001

Como o `CreativeExecutionPackage` existente chega ao motor HyperFrames sem quebrar o
núcleo neutro (`platform/`) nem a fábrica Python.

## Fronteira de contrato

O ponto único de acoplamento é o campo já previsto nos contratos:

```
Composition.renderer.adapter: "hyperframes"
```

`platform/src` **não é alterado** para esta migração: o tipo união já aceita o valor.
O que é novo é o **consumidor** dele — o adaptador em `renderers/hyperframes/`.

```
produce_video.py
   │  VideoRequest (JSON)
   ▼
compile-video-request.ts  ── platform neutra, intocada
   │  CreativeExecutionPackage:
   │    Composition · BeatPlan · OutputPlan · AssetManifest
   ▼
hf_adapter (novo)  ── renderers/hyperframes/
   │  1. valida schemas (platform/schemas)
   │  2. carrega frame.md (frontmatter) + brand-kit.json + guardrails.json
   │  3. valida claims dos textos contra guardrails (falha antes de render)
   │  4. materializa composição HTML (templates nativos por perfil)
   │  5. hyperframes check  →  hyperframes render (export -an)
   │  6. ffprobe: 0 streams de áudio · geometria · duração
   ▼
MP4 H.264 yuv420p (VIDEO CLEAN) → delivery_package.py → fila/Studio
```

## Mapeamento de contrato → composição

| Campo do contrato | Consumo no HyperFrames |
| --- | --- |
| `OutputPlan.profile` (12 perfis) | Geometria do projeto: 1080×1920 (9:16), 1920×1080 (16:9), 1080×1080 (1:1), 1080×1350 (4:5); 30 fps |
| `BeatPlan.beats[]` (kind, timing, textos) | Clipes HTML: `data-start`/`data-duration` por cena; trilhos por camada (mídia → headerOverlay → badge/headline/subline) |
| `Composition.scenes[].kind` (`hook-card`, `manager-agenda`, `cta-card`) | Template de cena correspondente (F9), com regras de design do `frame.md` |
| `Composition.scenes[].highlightId` | Destaque do elemento em foco na captura (borda/zoom no wrapper, nunca sobre cartão) |
| `AssetManifest` (capturas do produto) | `data-media-src` nos clipes de mídia; framework é dono do playback |
| `frame.md` frontmatter (colors/typography/components) | Tokens literais no CSS da composição: `#F5C107`, `#121620`, Arial bold, headerOverlay altura 170 |
| `guardrails.json` (alegações proibidas) | Filtro textual pré-render; violação aborta o job com log explícito |
| `audioPolicy` (allowAudioTrack:false, `-an`) | Composição sem nenhum elemento de áudio; export sem faixa |
| `captions.standard: "clean"` | Sem legenda queimada; `caption` das cenas alimenta o TXT de narração, não o MP4 |

## Padrão de ponte (processo filho + JSON)

O adaptador segue o padrão já provado do `render_bridge.mjs`: Python orquestra, Node
executa, comunicação por JSON em stdin/stdout com códigos de saída explícitos.

- **Entrada:** caminho do pacote (JSON) + perfil de saída + diretório de trabalho.
- **Saída:** JSON com `ok`, `outputPath`, `durationSeconds`, `checkFindings`,
  `ffprobe` (streams), e `error` estruturado em falha.
- **Confinamento:** todo processo filho herda o env de `config/env.sh` via wrappers
  (`hf.sh`/`hf-project.sh`) — caches npm/Chrome/TEMP dentro de
  `<RAIZ>/.workspace/tmp/hf001/`.
- **Determinismo:** a composição usa apenas lógica determinística (sem `Date.now()`,
  sem aleatoriedade); o mesmo pacote + mesma versão pinada (0.9.103) produzem o
  mesmo vídeo.

## Regras do adaptador (não negociáveis)

1. **Sem fallback silencioso.** `renderer.adapter` é escolha explícita registrada no
   manifest; falha do HyperFrames = item `failed` com log, nunca recaída automática
   em FFmpeg (MKT-VIDEO-003).
2. **Guardrails antes do render.** Texto com alegação proibida (whatsapp, 24h,
   automático, faturamento, "meu salão"…) aborta o job antes de gastar render.
3. **VIDEO CLEAN sempre.** Nenhum elemento de áudio na composição; export sem faixa;
   verificação `ffprobe` faz parte do contrato de saída do adaptador.
4. **Tenant isolado.** O adaptador só lê `frame.md`/`brand-kit.json`/`guardrails.json`
   do tenant declarado no manifest; nada de cross-tenant.
5. **Caminhos confinados.** Entradas do pacote validadas por resolução de caminho
   (sem `..`, sem symlink para fora de `<RAIZ>`); saída dentro do diretório de
   trabalho do job.
6. **Templates históricos intocados.** O adaptador usa apenas os templates nativos
   novos (F9); `templates/` de demonstração nunca é alvo de escrita.

## Avaliação — `@hyperframes/producer` (decidida em F6, 27/11/2026)

O pacote `@hyperframes/producer` (instalado em `renderers/hyperframes/`) expõe
`createRenderJob`/`executeRenderJob` com `ProgressCallback` — API programática de
render. **Decisão: o adaptador usa o CLI pinado** (spawn do módulo
`hyperframes/bin/hyperframes.mjs`), porque `check` e `render` ficam num único
caminho (a API não expõe o bundle de auditoria do `check`), o processo fica isolado
e os códigos de saída são estáveis. O producer permanece instalado como opção para
progresso fino da fila (F8); adoção não é compromisso.

## Templates nativos por cena (F9, 27/11/2026)

A biblioteca de templates vive **dentro do compositor** (`adapter/compose.mjs`),
não em projetos soltos: cada produção materializa a composição a partir das
variáveis do pedido (textos, mídia, paleta do tenant, geometria do perfil) — nunca
edição de código por produção. A seleção de template usa o campo neutro do
contrato `profile.beatPlan.beats[].narrativeFunction` (`hook|demonstration|cta`,
já resolvido pelo `compile-video-request` com default posicional); o `kind` legado
(`hook-card`/`manager-agenda`/`cta-card`) existia só na fábrica congelada
`ns002_pilot.py` e não entra no contrato. `platform/src` segue intocado.

| `narrativeFunction` | Template (frame.md, "Regras de composição por tipo de cena") | Tratamento |
| --- | --- | --- |
| `hook` | hook-card | Card de marca em fundo `background` cobrindo o quadro; bloco centrado (barra de acento + headline grande + subline). Pergunta/provocação da dor. |
| `demonstration` | manager-agenda | Captura é a estrela: mídia full-bleed + scrim suave inferior de legibilidade; texto ancorado na base (área segura), sem cartão sobre a UI. |
| `cta` | cta-card | Card de marca com convite centrado (headline + subline); sem aparência de botão/link clicável desenhado. |

Regras respeitadas: hierarquia barra → headline → subline; um acento `primary`
por cena; headerOverlay ancorando a marca no topo em todos os beats (trilho
acima dos cards); sem claims proibidas (guardrails rodam antes de compor);
tipografia Arial bold do frame.md, escalada por geometria (`fontSizeFor`/`px`
sobre a largura 1080 de referência) — cobre 1:1, 4:5, 9:16 e 16:9 sem código por
formato. `data-resolution` do `<html>` usa `square` no 1:1 (valores aceitos pelo
runtime: portrait/landscape/square e variantes 4k).

A biblioteca inicial pedida (reel produto/funcionalidade/institucional, motion,
horizontal, post, carrossel, CTA) é coberta pela combinação perfil × função
narrativa: o mesmo compositor serve reel 9:16, horizontal 16:9, stills de
post/carrossel (abaixo) e o CTA final é o beat `cta`.

## Estratégia técnica para imagens (F10, 27/11/2026)

**Vídeo e imagem estática não são equivalentes** — o still não passa por encode
H.264 nem por checagem de duração. Caminho oficial:

1. **Contrato de entrada:** o mesmo `CarouselRequest v1` do carrossel legado
   (cards com `title`/`body`/`mediaId`), validado pela ponte Node
   (`render_bridge.mjs --carousel-request`): catálogo + allowlist do projeto +
   geometria do perfil de imagem resolvem via `resolveOutputPlan` — 1:1
   `1080×1080`, 4:5 `1080×1350`, 9:16 `1080×1920` (stories). Um post é um
   conjunto de 1 card.
2. **Composição:** cada card vira uma composição HyperFrames de cena única
   (`tools/render_hyperframes_still.py` monta o perfil compilado; função
   narrativa posicional: primeiro `hook`, meios `demonstration`, último `cta`) —
   templates nativos do F9, tokens do tenant, guardrails do tenant validados
   pelo adaptador **antes** da captura.
3. **Captura de quadro:** `hyperframes snapshot --at <t>` (recurso oficial de
   captura/exportação de PNG) no instante com entradas concluídas (~1,2 s de uma
   composição de 2 s; o modo still desliga o fade-out do último beat). O
   adaptador (`hf_adapter.mjs --still`) exige exatamente 1 PNG e verifica
   `ffprobe`: codec `png` + geometria exata.
4. **Entrega:** mesmo contrato transacional do `produce_carousel` — PNGs
   numerados (`01-<id>.png`…), `stills.zip`, `still-manifest.json` (renderer
   hyperframes, SHA-256, dimensões) e `index.json` com
   lastAttempt/lastValidDelivery; promoção sob lock com backup.

**Fallback preservado:** `produce_carousel.py` (FFmpeg + `carousel_layout.py`)
segue intacto e continua sendo o caminho da modalidade `carousel` da fila; o
caminho HyperFrames é ferramenta explícita até ser validado visualmente (F13) —
sem troca silenciosa (MKT-VIDEO-003). A arte estática de feed gerada por IA
(ComfyUI08 + guard de proveniência) permanece sistema separado e intocado
(matriz #13).

