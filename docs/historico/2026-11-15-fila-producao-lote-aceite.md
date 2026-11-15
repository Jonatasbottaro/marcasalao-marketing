# Registro de aceite — Produção em lote com fila local persistente no Video Studio (2026-11-15)

## Escopo entregue

- **Branch técnica**: `codex/studio-production-queue-v1` (sobre `main` em `c2758f1f5a498c0dff6021fc5588ac2c29cbafa0`).
- **Módulo de fila persistente (`tools/studio_queue.py`)**:
  - Banco SQLite da biblioteca padrão em `.workspace/studio/production-queue.sqlite` (`QUEUE_SCHEMA_VERSION = 1`), com tabelas `schema_meta`, `executor_leases`, `batches`, `queue_items` e `queue_attempts`.
  - Planejamento de destinos por catálogo, allowlist do projeto e capacidade local (`plan_batch`), explicando opções indisponíveis (como `Motion` fora de `9:16`) antes da confirmação.
  - Enfileiramento idempotente por `idempotencyKey` (`enqueue_batch`), congelando snapshot do pedido salvo, cortes, enquadramento, `MotionPlan` aplicável, projeto e hashes SHA-256 das mídias.
  - Executor único em série por workspace com lease de PID, claim atômico (`_claim_next_item`), cerca por tentativa (`--attempt-id` e `--fence-file` em `tools/produce_video.py`, `tools/produce_carousel.py` e `tools/render_pipeline.py` sob `acquire_promotion_lock`), proteção compartilhada com `Studio.start_export` e idempotência de `record_export_lineage` em `tools/studio_review.py`.
  - Retomada em reinício (`recover_on_startup`) reconciliando promoções comprovadas pelo `attemptId` ou marcando `interrupted` sem apagar entregas válidas anteriores; cancelamento de pendentes (`cancel_item`), repetição com revalidação de snapshot (`retry_item`, oferecendo enfileirar versão atual em `MEDIA_DIVERGENCE`) e resumo JSON do lote (`export_batch_summary`).
- **API HTTP e interface (`tools/video_studio.py`, `tools/studio/{index.html,style.css,app.js}`)**:
  - Rotas `GET /api/queue`, `GET /api/queue/batch`, `GET /api/queue/batch/summary`, `POST /api/queue/plan`, `POST /api/queue/enqueue`, `POST /api/queue/cancel`, `POST /api/queue/retry` (incluindo HTTP `409` para `QueueConflictError`).
  - Seleção múltipla em **Trabalhos & Projetos** (`Exportar em lote`), modal `#batch-export-dialog` com alerta de alterações não salvas, aba **Fila de Produção** (`#mode-queue`) com contadores, filtros, cancelamento, repetição, download do resumo JSON e acesso direto à **Revisão & Entrega**.
- **Correção visual na Revisão (`tools/studio/style.css`)**:
  - `.review-card` com `min-width: 0; max-width: 100%; overflow-wrap: anywhere;` e `.review-card video` com `width: auto; max-width: 100%; max-height: 460px; height: auto;`.

## Evidências executadas após o último ajuste de código (`6172965`)

- **`platform` (`build`, `typecheck`, `test`, `test:contracts`)**: `324/324` testes aprovados (`fail 0`, `skipped 0`, exit `0`).
- **Suíte Python completa com `REQUIRE_RENDER=1` (`python -m unittest discover -s tools/tests -v`)**: `233/233` testes aprovados em `1958.266s` (`OK`, zero falhas, zero erros, zero skips; log em `.workspace/logs/studio-production-queue-v1/python-suite-full.log`), incluindo os 4 testes dedicados em `tools/tests/test_studio_queue.py` (esquema/idempotência/opções indisponíveis/cancelamento, disputa de claim atômico e lock de destino, lote misto Marca Salão + Multitrack Hub com FFprobe `1080x1920`/`1920x1080`/`30 fps`/0 áudios + carrossel `1080x1350` + Revisão/ZIP + `draft_outdated`, e recuperação após queda em render/pós-promoção + `MEDIA_DIVERGENCE`).
- **Prova HTTP de CI (`python tools/ci_studio_queue_proof.py --port 8803`)**: exit `0`, lote `batch-1d2564ccab` (`5/5` itens `completed`), deduplicação por `idempotencyKey` e pacote ZIP verificado (`zipSha256: 563a442094060a1a5cc8aabc173272b912b660c106953680c72c52671cd23da2`). Integrada em `.github/workflows/local-render-validation.yml`.
- **Prova E2E em Chrome headless via CDP** (capturas em `.workspace/logs/studio-production-queue-v1/browser/`):
  - Seleção de dois trabalhos (`e2e-lote-ms-work` e `e2e-lote-mh-work`), abertura de `#batch-export-dialog`, confirmação do lote, recarregamento da página e recuperação da **Fila de Produção** até `8/8` itens `Concluídos`, abertura direta na **Revisão & Entrega**.
  - Medição do player horizontal `1920x1080` na Revisão:
    - Desktop `1280x800`: `scrollWidth=1265 <= 1280`, player `817.77x460` (`rectLeft=130.5`, `rectRight=948.27 <= 1280`).
    - Mobile `390x844`: `scrollWidth=390 <= 390`, player `274x154.13` (`rectLeft=58`, `rectRight=332 <= 390`).
