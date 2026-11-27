# Arquitetura-alvo — HF-001

Fórmula da operação:

**MARCA SALÃO MARKETING = ORQUESTRAÇÃO + INTELIGÊNCIA EDITORIAL + GOVERNANÇA + HYPERFRAMES COMO MOTOR AUDIOVISUAL PRINCIPAL**

## Diagrama de camadas

```
┌─────────────────────────────────────────────────────────────────┐
│ GOVERNANÇA (intocada)                                            │
│ AGENTS.md · guardrails por tenant · aprovações Postiz ·          │
│ autoPublish:false · auditoria · índices documentais              │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│ ORQUESTRAÇÃO + INTELIGÊNCIA EDITORIAL (Python/TS existentes)     │
│ produce_video.py → compile-video-request.ts →                   │
│ VideoRequest → Composition/BeatPlan/OutputPlan                  │
│ (CreativeExecutionPackage)                                       │
│ Video Studio (video_studio.py) · fila (studio_queue.py) ·       │
│ pacote de entrega (delivery_package.py)                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │ renderer.adapter = "hyperframes"
                               │ (seleção EXPLÍCITA no manifest)
┌──────────────────────────────▼──────────────────────────────────┐
│ MOTOR AUDIOVISUAL PRINCIPAL — HyperFrames 0.9.103                │
│ renderers/hyperframes/ (runtime Node confinado em <RAIZ>)         │
│ adaptador: pacote → composição HTML (data-*) → check → render    │
│ templates nativos por perfil de saída (9:16, 16:9, 1:1, 4:5)     │
│ frame.md (frontmatter) + brand-kit.json = verdade de marca        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                    MP4 H.264 · yuv420p · SEM áudio (-an)
                    textos gráficos preservados · áreas seguras
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│ FALLBACK (permanece instalado e testado)                         │
│ render_pipeline.py / render_local.py (FFmpeg, --clean)           │
│ fábrica legada preset_runner/factory_cli (LEGADO, congelada)     │
└─────────────────────────────────────────────────────────────────┘
```

## Fluxo ponta a ponta (produção nova)

1. **Brief editorial** → agente/Studio monta `VideoRequest` (cenas `kind`, textos,
   `highlightId`, destino). Guardrails validam claims antes de qualquer render.
2. **Derivação** → `compile-video-request.ts` produz `Composition` + `BeatPlan` +
   `OutputPlan` (`CreativeExecutionPackage`). Nada muda aqui.
3. **Seleção de renderer** → o manifest registra `renderer.adapter: "hyperframes"`.
   Sem fallback silencioso: se o adaptador falhar, o item de fila vai a `failed`
   com log — não recai em FFmpeg por conta própria.
4. **Adaptador** (`renderers/hyperframes/`):
   - lê `frame.md` (frontmatter: cores, tipografia, headerOverlay, política de
     áudio/legendas) e `brand-kit.json` do tenant;
   - traduz o `BeatPlan` em composição HTML HyperFrames (`data-*`, GSAP seekable,
     `window.__timelines`, sem lógica não determinística);
   - aplica geometria do `OutputPlan` (1080×1920, 1920×1080, 1080×1080, 1080×1350);
   - roda `check` (lint + auditoria de browser) e então `render` com export **sem
     faixa de áudio** (VIDEO CLEAN).
5. **Verificação** → `ffprobe`: 0 streams de áudio, duração/geometria batem com o
   plano; snapshots das cenas para revisão humana.
6. **Fila/Studio** → item `hyperframes` na mesma fila SQLite (estados e recovery
   existentes); progresso e logs visíveis no Studio.
7. **Entrega** → `delivery_package.py` empacota MP4 + roteiro de narração TXT
   (`04-legendas/`) no mesmo pacote transacional. SRT somente sob pedido expresso.
8. **Aprovação/publicação** → fluxo Postiz existente, `autoPublish: false`.
   A migração não publica nada.

## Princípios que a arquitetura preserva

- **Um motor, não dois.** Nenhuma funcionalidade nova de animação/tipografia/timeline
  é desenvolvida em casa; o que o HyperFrames não cobrir, cai no fallback FFmpeg —
  e a escolha é sempre registrada.
- **O núcleo permanece neutro** (MKT-PLATFORM-001): o adaptador HyperFrames vive em
  `renderers/hyperframes/`, atrás do contrato `renderer.adapter`; `platform/` não
  conhece marca nem vendor.
- **Portabilidade primeiro**: runtime Node, caches npm/Chrome/FFmpeg e temporários
  confinados em `<RAIZ>/.workspace/tmp/hf001/` via wrappers (`hf.sh`, `hf-project.sh`,
  `config/env.sh`). Nenhum artefato fora de `<RAIZ>`.
- **VIDEO CLEAN é inegociável** (MKT-VIDEO-002): MP4 mudo, sem legenda queimada,
   narração TXT separada; textos gráficos editoriais permanecem como arte.
- **Governança editorial intacta**: temas, reservas, aprovações, histórico e
  guardrails continuam sendo a última palavra antes de qualquer render.

## O que a arquitetura NÃO é

- Não é substituição da fábrica: `produce_video.py`, Studio, fila e entrega seguem
  sendo o caminho canônico de produção.
- Não é nuvem: render é local (Chrome headless pinado + FFmpeg portável). Cloud
  render, `publish`, Lambda/CloudRun e serviços pagos estão fora de escopo.
- Não é retroativa: campanhas históricas (NS-001 v1…v3) não são re-renderizadas.
