# Matriz de migração — HF-001

Decisão por recurso, com evidência de compatibilidade, testes e risco. Legenda de
decisão: **MANTER** (intocado), **ADAPTAR** (ponto de integração novo), **MIGRAR**
(produção nova passa ao HyperFrames), **FALLBACK** (permanece como plano B operacional),
**LEGADO** (congelado, sem evolução), **REMOVER FUTURAMENTE** (decisão registrada,
execução fora do escopo imediato). Status: ✅ concluído · 🔶 em execução · ⬜ pendente.

| # | Recurso | Implementação atual | Contrato | Recurso HyperFrames | Decisão | Compatibilidade | Testes | Risco | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Contratos de produção | `platform/src/*.ts` + schemas | `VideoRequest`, `Composition`, `BeatPlan`, `OutputPlan` | Adaptador consome o `CreativeExecutionPackage` pronto | MANTER | Sem mudança de schema; `renderer.adapter='hyperframes'` já previsto | `npm test` (807) verde na base | Baixo | ✅ |
| 2 | Derivação de composição | `compile-video-request.ts` | `CreativeExecutionPackage` | Adaptador traduz beats → HTML `data-*` | MANTER | Nenhuma alteração na derivação | Testes de contrato existentes | Baixo | ✅ |
| 3 | Render de vídeo | `render_pipeline.py`/`render_local.py` (FFmpeg) | `Composition.renderer.adapter` | `renderers/hyperframes/` (CLI 0.9.103) | MIGRAR (novo) + FALLBACK | Novo ID de adaptador registrado no manifest; sem fallback silencioso | `smoke.sh` + `adapter-smoke.sh` verdes (0 áudio) | Médio: dependência de Chrome/FFmpeg | ✅ |
| 4 | Fábrica legada | `preset_runner.py`/`factory_cli.py` | `requireSrt: true` (legado) | Nenhum | LEGADO | Byte-idêntica; campanhas antigas re-renderizáveis | `run_tests.py --all` na base | Baixo | ✅ |
| 5 | VIDEO CLEAN | `--clean` nos renderizadores | MKT-VIDEO-002 | Export `-an`, sem legenda queimada, sem SRT padrão | MANTER | `ffprobe` 0 streams de áudio no smoke | `smoke.sh` + verificação de entrega | Baixo | ✅ |
| 6 | Design system de vídeo | `frame.md` (prosa + frontmatter) | `frame.md` frontmatter | Adaptador parseia frontmatter (cores/fontes/headerOverlay) | MIGRAR | Frontmatter é a verdade de marca; layout livre | Parser exercitado no adapter-smoke (check verde) | Baixo | ✅ |
| 7 | Guardrails por tenant | `guardrails.json` (claims, áudio) | `TenantPolicy` | Validação textual pré-render no adaptador | MANTER | Mesma lista de alegações proibidas | adapter-smoke negativo: "24h"/"agenda sempre cheia" abortam | Médio: validação duplicada | ✅ |
| 8 | Video Studio | `video_studio.py` (~50 rotas, porta 8765) | Interno HTTP | Rotas novas: submeter/consultar job HyperFrames | ADAPTAR | Rotas existentes intactas; novas rotas aditivas | Studio frontend CI + smoke manual | Médio: superfície HTTP | ⬜ F7 |
| 9 | Fila de produção | `studio_queue.py` (SQLite, 6 estados, recovery) | Estados + snapshots SHA-256 | Novo tipo de item `hyperframes` na mesma fila | ADAPTAR | `schemaVersion` preservado; estados reutilizados | Teste de fila: submit→running→completed + kill/recover (F14) | Médio: concorrência/recovery | ⬜ F8 |
| 10 | Pacote de entrega | `delivery_package.py` (ZIP transacional) | Pacote de entrega | MP4 HyperFrames entra no mesmo pacote | MANTER | Formato do pacote inalterado | Teste de empacotamento existente | Baixo | ⬜ F7 |
| 11 | Ponte Node↔Python | `render_bridge.mjs` | Padrão processo filho + JSON | Adaptador segue o mesmo padrão | ADAPTAR | Mesmo contrato de mensagem | Smoke do adaptador (F14) | Baixo | ⬜ F6 |
| 12 | Templates nativos | — (não existem) | `kind` de cena (`hook-card`, `manager-agenda`, `cta-card`) | Projetos HyperFrames por perfil de saída | MIGRAR (novo) | Geometrias dos 12 perfis respeitadas | `check` + snapshots por template (F14) | Médio: novo código de layout | ⬜ F9 |
| 13 | Formatos de imagem/feed | ComfyUI08 + guard de proveniência | `ImageRequest`/`CarouselRequest` | Fora do motor de vídeo | MANTER | Sistema separado (teal/menta) | Guard de proveniência existente | Baixo (não tocado) | ✅ |
| 14 | Templates históricos | `templates/*` (0.8.126, overlay) | — | Referência técnica | LEGADO | Não editar, não renderizar em produção | — | Baixo | ✅ |
| 15 | Skills HyperFrames | `.agents/skills/` (25) + lock v2 | `skills-lock.json` | Suporte à autoria das composições | MANTER | Upstream `cfaefdc` pinado | `verify` de hashes do lock | Baixo | ✅ |
| 16 | Testes locais | `run_tests.py` (smoke/fast/render/all) | Gates locais | Gate novo: `smoke.sh` HyperFrames | MANTER + ADAPTAR | Suítes longas seguem rodando separadas | Execução na base | Baixo | ✅ base · ⬜ F14 |
| 17 | CI | 4 workflows ativos + 1 morto | `CI-E-PRS.md` | Workflow novo `hyperframes-validation` (draft) | ADAPTAR + REMOVER FUTURAMENTE | Gates legados intocados; `video-preview.yml` morto registrado | CI verde nas branches técnicas | Médio: runners sem Chrome | ⬜ F14 |
| 18 | Campanhas históricas | NS-001 v1…v3 | `AssetManifest` | Base da comparação F13 | MANTER | Nenhum re-render retroativo | — | Baixo | ✅ |
| 19 | Publicação (Postiz) | Filas/aprovações externas | `autoPublish: false` | Nenhum | MANTER | Migração não publica | — | Baixo | ✅ |
| 20 | Documentação | `docs/` (índices, decisões) | `DOCUMENTACAO.md` | Seção `docs/migracao-hyperframes/` | ADAPTAR | Índices oficiais atualizados em adição | Revisão de links | Baixo | 🔶 |

## Notas de decisão

- **Regra 3 (render):** o HyperFrames é o caminho de produção **nova**; o render local
  FFmpeg permanece instalado, testado e documentado como FALLBACK no
  [RUNBOOK-OPERACIONAL.md](RUNBOOK-OPERACIONAL.md). Nenhuma produção nova cai
  silenciosamente no fallback: a escolha de renderer é registrada no manifest
  (MKT-VIDEO-003, regra da seleção explícita).
- **Regra 4 (legado):** o fluxo `requireSrt` não é removido nem "corrigido"; a
  divergência com VIDEO CLEAN está registrada em `frame.md` e em
  [DECISOES-E-CONFLITOS.md](DECISOES-E-CONFLITOS.md).
- **Regra 17 (CI):** a remoção do workflow morto `video-preview.yml` é registrada aqui,
  mas sua execução fica fora do escopo desta operação para não ampliar o diff de CI.
- **Regra 13 (imagem):** a migração é do **motor de vídeo**. Arte de feed/carrossel
  estática continua no ComfyUI08 com seu guard de proveniência; nada muda para ela.
