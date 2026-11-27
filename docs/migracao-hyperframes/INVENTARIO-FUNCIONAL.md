# Inventário funcional — migração HyperFrames (HF-001)

Verificado em 27/11/2026 na branch `codex/hyperframes-core-migration` (base `main`
`7f1c7ff` + op26). Cada linha cruza o que **existe em código** com o que a
**documentação afirma**, e marca a relação da funcionalidade com a migração.
Detalhe do destino por recurso: [MATRIZ-DE-MIGRACAO.md](MATRIZ-DE-MIGRACAO.md).

## 1. Núcleo de contratos (`platform/`)

| Funcionalidade (código) | Documentação | Migração |
| --- | --- | --- |
| Contratos TS neutros: `ProjectManifest`, `VideoRequest`, `Composition`, `BeatPlan`, `MotionPlan`, `OutputPlan`, `CarouselRequest`, `ImageRequest`, `AssetManifest`, `TenantPolicy`/`Guardrails`, `VisualAnchor` (`platform/src/`) | `platform/README.md` (desatualizado: "nenhum renderizador implementado") | **MANTER** — o adaptador HyperFrames consome exatamente estes contratos |
| Schemas JSON versionados (`platform/schemas/`) | `platform/README.md` | **MANTER** — validação de entrada do adaptador |
| `Composition.renderer.adapter` já aceita `'hyperframes'`; `ADAPTER_IDs` existentes: `local-proof-render`, `local-pipeline-render` | Contratos citam o campo; nenhum consumidor para `'hyperframes'` | **ADAPTAR** — novo adaptador registra ID próprio; sem fallback silencioso |
| `compile-video-request.ts` deriva `Composition`/`BeatPlan`/`OutputPlan`/`CreativeExecutionPackage` | `docs/arquitetura-fabrica.md` | **MANTER** — ponto único de derivação; o adaptador recebe o pacote pronto |
| Testes do núcleo (`npm test`, 807 testes) | `platform/README.md` | **MANTER** — estender com testes do adaptador (F14) |

## 2. Produção de vídeo (fábrica Python)

| Funcionalidade (código) | Documentação | Migração |
| --- | --- | --- |
| `tools/produce/produce_video.py` — monta `VideoRequest` e aciona a derivação TS | `docs/arquitetura-fabrica.md`, `WORKFLOW.md` | **MANTER** — continua sendo a orquestração editorial |
| `tools/produce/render_pipeline.py` / `render_local.py` — render FFmpeg com `--clean` (VIDEO CLEAN) | `docs/decisoes/MKT-VIDEO-002`, `tools/render/README.md` | **FALLBACK** — permanece íntegro; é o plano B do RUNBOOK |
| `tools/preset_runner.py` / `factory_cli.py` — fluxo legado (legenda queimada + SRT obrigatório) | `tenants/*/brand-kit.json` (`requireSrt: true` legado) | **LEGADO** — congelado; não alterar nem estender |
| Biblioteca de mídia, reservas de tema, filas de aprovação, entregas | `WORKFLOW.md`, `docs/arquitetura-fabrica.md` | **MANTER** — governança editorial intocada pela migração |
| Guard de proveniência ComfyUI (`marcas/marcasalao/comfyui/marcasalao_media_guard.py`) | `AGENTS.md` (regra de 23/10) | **MANTER** — arte de feed é sistema separado; a migração não a toca |

## 3. Video Studio e fila

| Funcionalidade (código) | Documentação | Migração |
| --- | --- | --- |
| `tools/video_studio.py` — servidor HTTP (stdlib, porta 8765, ~50 rotas) | `docs/guia-operacional-titular.md` | **ADAPTAR** — novas rotas para submeter job HyperFrames (F7) |
| `tools/studio_queue.py` — fila SQLite (`.workspace/studio/production-queue.sqlite`), estados `queued/running/completed/failed/cancelled/interrupted`, `recover_on_startup`, snapshots SHA-256 (schemaVersion 2) | Parcial: comportamento documentado em código, não em doc de operação | **ADAPTAR** — o job HyperFrames entra como novo tipo de item na mesma fila (F8) |
| `tools/delivery_package.py` — pacote transacional (ZIP) | `tools/produce/README.md` | **MANTER** — o MP4 do HyperFrames entra no mesmo pacote de entrega |
| `tools/render_bridge.mjs` — ponte Node↔platform (padrão de processo filho + JSON) | Padrão citado em comentários/código | **ADAPTAR** — o adaptador HyperFrames segue este mesmo padrão de ponte |

## 4. Identidade e design

| Funcionalidade (código) | Documentação | Migração |
| --- | --- | --- |
| `tenants/marca-salao/brand-kit.json` — paleta, `headerOverlay`, `subtitleStyle`, tipografia | `tenants/marca-salao/frame.md` (frontmatter deriva dele) | **MANTER** — fonte de tokens; o adaptador lê `frame.md` + `brand-kit.json` |
| `tenants/marca-salao/guardrails.json` — alegações proibidas, política de áudio | `AGENTS.md`, `frame.md` | **MANTER** — validação textual das composições antes do render |
| `tenants/marca-salao/frame.md` — design system de vídeo v2 (frontmatter normativo) | `frame.md` § Adoção: "adotar este arquivo como frame.md do projeto de vídeo" | **MIGRAR** — passa a ser consumido por máquina pelo adaptador (F5/F6) |
| Perfis de saída: 12 (6 imagem / 6 vídeo), geometrias 1080×1080, 1080×1350, 1080×1920, 1920×1080, 30 fps | `platform/src` + `docs/arquitetura-fabrica.md` | **MANTER** — o HyperFrames renderiza nestas geometrias (F9/F10) |

## 5. Templates e demonstrações

| Funcionalidade (código) | Documentação | Migração |
| --- | --- | --- |
| `templates/story_reel_vertical/`, `templates/youtube_horizontal/` — projetos HyperFrames 0.8.126 de demonstração | Citados como prova de conceito | **LEGADO** — não editar; referência técnica |
| `templates/reel_link_overlay/` + `edit_link_reel.py` — overlay 9:16 | Idem | **LEGADO** — prova viva da CLI; não editar |
| Skills HyperFrames vendadas (25) + `skills-lock.json` v2 (upstream `cfaefdc`) | `.agents/skills/` | **MANTER** — atualização só pelo procedimento oficial |

## 6. Testes e CI

| Funcionalidade (código) | Documentação | Migração |
| --- | --- | --- |
| `python tools/run_tests.py --smoke|--fast|--render|--all` (25/29/22/51 módulos) | `docs/governanca/CI-E-PRS.md` | **MANTER** — gates locais preservados |
| Workflows: `platform-validation.yml`, `local-render-validation.yml`, `studio-frontend-ci.yml`, `temporal-pilot-ci.yml` | `docs/governanca/CI-E-PRS.md` | **MANTER** — novo gate HyperFrames entra em adição (F14) |
| `video-preview.yml` — workflow morto | Registrado em auditoria | **REMOVER FUTURAMENTE** — fora do escopo imediato; decisão registrada na matriz |
| Smoke do runtime: `renderers/hyperframes/tests/smoke.sh` (init→check→render draft→ffprobe) | `renderers/hyperframes/README.md` | **NOVO** — base do gate de CI da migração |

## 7. Campanhas e histórico

| Funcionalidade (código/dados) | Documentação | Migração |
| --- | --- | --- |
| NS-001 v1…v2.8 + editorial-v2 + v3 (`02-reels-shorts/`) | `docs/contexto/*`, auditorias | **MANTER** — base da comparação visual v2/v3 × HyperFrames (F13) |
| Roteiros de narração TXT (`04-legendas/`) | MKT-VIDEO-002 | **MANTER** — padrão de entrega continua |
| Postiz: filas, aprovações, histórico por marca | `AGENTS.md` (regras de 31/10, 19/10) | **MANTER** — fora da migração; `autoPublish: false` |

## Lacunas funcionais identificadas

1. **Renderizador HyperFrames não existia** — contratos aceitavam `'hyperframes'`, mas
   nenhum adaptador consumia. Fase F6 preenche a lacuna.
2. **`frame.md` era apenas prosa para agentes** — nenhum código o parseava. F5/F6 o
   tornam entrada de máquina (frontmatter normativo).
3. **Fila do Studio sem tipo de job externo** — itens sempre apontavam para o render
   local FFmpeg; F8 introduz o job HyperFrames com os mesmos estados e garantias.
4. **CI sem gate HyperFrames** — nenhum workflow validava composições HyperFrames;
   F14 adiciona sem quebrar os gates legados.
5. **Documentação de operação do Studio desatualizada** — `docs/guia-operacional-titular.md`
   não descreve a fila nem recuperação pós-queda; o RUNBOOK da migração passa a cobrir
   o caminho HyperFrames e o fallback.
