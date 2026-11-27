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
