# Auditoria somente leitura do projeto — 2026-11-22

> Documento de auditoria. **Não implementa nada.** Registra o estado real reconstruído a
> partir do código, dos arquivos versionados e do histórico Git, confrontando a
> documentação com a implementação. Autorização desta tarefa: criar exclusivamente este
> arquivo (e a pasta `docs/auditorias/`, se necessária). Nenhum `git add`, commit ou push
> foi executado; nenhum outro arquivo foi modificado.

## Metadados da auditoria

- **Data da execução:** 2026-11-22, entre ~13:55 e 14:26 (horário local da estação, BRT).
- **Branch da base analisada:** `feat/etapa-14-tenant-scaffolder-capacity-planner`.
- **Commit completo no início da auditoria:** `6d9cd18c07d068210292b331a8b9d0b9e1cd12c6`.
- **Commit completo no fechamento da auditoria:** `01074c8dbf28e6cb51f5a494bfb79cc3c8113163`
  ("fix(etapa-14): corrige testes de scaffold_tenant", criado por **outra sessão** na mesma
  estação às 14:06:59, durante a auditoria).
- **Referência `origin/main` disponível localmente:** `276ee415a171f3bac11687343265a5c704dce067`.
- **Raiz:** `<RAIZ>` = valor de `git rev-parse --show-toplevel` do checkout principal desta
  estação (Windows 10.0.26200). O documento não fixa caminho de máquina; todos os caminhos
  de evidência são relativos a `<RAIZ>`.
- **Método:** leitura integral ou dirigida de código, documentos e blobs Git; inspeção visual
  de 2 imagens; quatro levantamentos profundos delegados a subagentes somente leitura
  (núcleo TypeScript/Temporal; faixas de teste/gates/lentes/tenants/scaffolder/CI;
  Studio/render/mídia/manifests/ZIP/aprovação/contenção; analytics/A-B/fadiga/portal/adaptadores).
- **Proibições cumpridas:** nenhum teste, gate, render, build, instalação, bootstrap, deploy,
  seed ou CLI do projeto foi executado; nenhuma chamada de rede ou provedor; nenhum fetch,
  pull, checkout, commit, push, stash ou add; nenhum valor de credencial, `.env`, token ou
  cookie foi lido ou exibido; instruções operacionais de documentos históricos foram
  tratadas como dado, não como comando.
- **Classificação dos achados:** `C` = confirmado por leitura de código/blob/documento;
  `H` = hipótese (raciocínio estático, não executado); `NV` = não verificado.
- **Contagem de testes:** módulos por tupla/`listdir` (exato); funções por grep de
  `def test` (aproximação, **não** equivale a `testsRun`). Nenhum número de "testes
  aprovados" foi produzido por execução nesta auditoria.

---

## A. Identidade da base analisada

| Item | Valor observado |
| --- | --- |
| `<RAIZ>` (`git rev-parse --show-toplevel`) | checkout principal desta estação; `--git-common-dir` = `.git` (não é worktree) |
| Branch | `feat/etapa-14-tenant-scaffolder-capacity-planner` |
| HEAD no início | `6d9cd18c07d068210292b331a8b9d0b9e1cd12c6` |
| HEAD no fechamento (14:21 e 14:26) | `01074c8dbf28e6cb51f5a494bfb79cc3c8113163` (commit de outra sessão, 14:06:59) |
| `origin/main` local | `276ee415a171f3bac11687343265a5c704dce067` |
| Divergência HEAD × `origin/main` | 2 à frente (`6d9cd18`, `01074c8`), 0 atrás |
| Working tree no início | ` M tools/tests/test_tenant_scaffolder.py` |
| Working tree às 14:07 | limpo (modificação commitada por outra sessão em `01074c8`) |
| Working tree no fechamento | ` M tools/tests/test_run_tests.py` (mtime 14:09:33) e ` M tools/tests/test_tenant_scaffolder.py` (mtime 14:17:01) — edições em curso de **outra sessão**; nada descartado ou alterado pela auditoria |
| Worktrees | principal + `.workspace/worktrees/utm-ab-recommendations` (branch `codex/utm-ab-recommendations`, HEAD `533cc4ca929968a4aecf60cb34cb36c214fe3211`, limpa; **já integrada em `origin/main`**) |
| Remoto | `origin` = `https://github.com/Jonatasbottaro/marcasalao-marketing.git` |
| Frescor das refs | `.git/FETCH_HEAD` mtime 22/11 13:33; **fetch/pull proibidos nesta tarefa** — refs locais podem estar desatualizadas |
| Arquivos rastreados | 2307 |

**Alerta de concorrência (C):** a estação é compartilhada por várias sessões. Durante a
auditoria, outra sessão commitou `01074c8` e deixou duas edições não commitadas que corrigem
exatamente duas inconsistências apontadas aqui (contagens 28/24 → 29/25 em
`tools/tests/test_run_tests.py:428-429` e estilo de import em
`tools/tests/test_tenant_scaffolder.py`). Os achados de código referem-se a `01074c8` +
working tree observado; onde a edição não commitada muda o fato, isso está indicado.
Nenhuma alteração da auditoria foi misturada às alterações daquela sessão.

---

## B. Resumo executivo

1. **O projeto é real, grande e coerente no núcleo:** fábrica Python 100% stdlib (5 tenants,
   14 campanhas), núcleo TypeScript de contratos puros, Video Studio local em `127.0.0.1`,
   render FFmpeg sem áudio, empacotamento com SHA-256 e aprovação humana em duas camadas.
   Nada no fluxo da fábrica publica, agenda ou cria rascunho remoto.
2. **A documentação ativa está desatualizada em contagens e comandos.**
   `contexto_projeto_6.md` (v6, base `642f570`) é o documento mais fiel; `README.md`,
   `docs/arquitetura-fabrica.md` e comentários de CI carregam números das Etapas 4–5B
   (7 domínios, 5 lentes, 21 módulos, tabela de 19 campanhas).
3. **O gate de release provavelmente está vermelho no HEAD por duas asserções obsoletas**,
   não por defeito de produto: `test_run_tests.py` esperava 28/24 módulos (corrigido apenas
   no working tree por outra sessão) e o E2E espera 7 domínios desde antes de `cd2f8ed`
   introduzir o 8º. Conclusão estática; **não executado**.
4. **A Etapa 14 (`6d9cd18`) entregou código com defeitos semânticos e de contrato:**
   `tenant_scaffolder.py` grava antes de validar e retorna `ok: true` incondicional;
   `capacityStatus` mistura escopo por tenant com escopo global; o planejador de capacidade
   alimenta o bloco "current" com totais simulados.
5. **Não existe nenhum dado real de analytics no repositório.** `impressions`/`clicks`/`ctr`
   são sessões web renomeadas; o simulador é sintético com seed fixa; os CSVs de mensuração
   são ensaios fictícios. Qualquer leitura de "resultado de campanha" a partir desses
   números seria falsa.
6. **A regra de áudio é cumprida pelo pipeline atual, com uma exceção legada:**
   `edit_link_reel.py` adiciona faixa AAC silenciosa (`anullsrc`), além de `shell=True` e
   caminho de FFmpeg fora do projeto.
7. **A proibição geral de rascunhos e o fluxo Postiz autorizado coexistem em escopos
   distintos:** a fábrica é inerte; o guard de proveniência ComfyUI
   (`marcas/marcasalao/comfyui/`) regula DRAFTs criados por ferramenta MCP externa numa
   estação Linux que não existe neste checkout.
8. **Higiene e portabilidade têm lacunas reais:** teste novo usa `%TEMP%` e `os.chdir("/")`;
   dois testes reescrevem artefatos versionados (portal e calendário); `.git/info/exclude`
   não cobre `bundles/` e `snapshots/`; `.workspace/tmp` acumula 426 MB.
9. **Determinismo é parcial e bem delimitado no código:** ZIP bit-determinístico só no
   `publish_bundler`; ZIPs do Studio/carrossel/backup embutem mtime/`createdAt`; igualdade de
   bytes do MP4 entre execuções nunca é assertada nos testes.
10. **Integrações externas (Postiz, ComfyUI, Gemini, Hermes, Temporal remoto) não foram
    consultadas**; tudo o que se afirma sobre elas é leitura de código, não comportamento
    observado.

---

## C. Mapa dos subsistemas

| Subsistema | Entradas → saídas | Dependências | Fronteira de autorização |
| --- | --- | --- | --- |
| **Content Factory editorial** (`00-briefings/`, `02-hooks/`, `03-roteiros/`, `04-legendas/`, `marcas/*/posts/`) | briefing → hooks → roteiro → legendas → métricas | documentos; regras de veracidade | briefing aprovado não autoriza produção/publicação; NS-001 e NS-002 "em validação" |
| **Fábrica Python multi-tenant** (`tools/preset_runner.py`, `tools/factory_cli.py`, `tools/tenant_validator.py`, `tenants/`, `schemas/`) | contratos JSON → MP4 9:16 + SRT + narração TXT + storyboard + `manifest.json` + `derivatives.json` | FFmpeg/FFprobe portáteis; stdlib | `autoPublish:false`; áudio só `multitrack-hub`; versionamento apenas de texto/PNG/manifestos |
| **Núcleo TS `platform/`** (`platform/src/index.ts`, `platform/src/composition-validation-api.ts`) | ProjectManifest/Composition/OutputPlan/BeatPlan → relatórios puros, pacotes de execução, execução **simulada** textual | Node ≥22 <25; ajv só em teste | API pública = só `validateComposition`; sem mídia, sem rede; `index.ts` (5 funções) é agregado interno, não exportado pelo mapa `exports` |
| **Video Studio** (`tools/video_studio.py`, 3500 linhas) | JSON de pedido → rascunhos, prévias, entregas, ZIP; ~35 rotas GET + ~45 POST | platform via `tools/render_bridge.mjs`; FFmpeg | bind `127.0.0.1:8765` (`tools/video_studio.py:3444`); Host/Origin nas escritas (:2836-2843); preflight editorial bloqueia com 422/409; nada remoto |
| **Planejamento + biblioteca de mídias** (`tools/studio_planning.py`, `tools/studio_media.py`, `tools/llm_adapter.py`, `tools/image_adapters.py`) | ideia → PlanningSuggestion; importação/geração → versões imutáveis com SHA-256, origem, licença | LLM local desativado por padrão; Gemini opcional | `pending_media` bloqueia aplicação; simulador marcado `simulated:true`; chave nunca persistida |
| **Render / formatos / cortes / Motion** (`tools/render_local.py`, `tools/render_pipeline.py`, `tools/render_bridge.mjs`, `tools/build_video.py`, `tools/produce_video.py`, `tools/produce_carousel.py`, `tools/derivative_formats.py`, `tools/static_cards.py`) | pacote + AssetManifest → MP4 H.264 `-an`, SRT, TXT, `delivery-manifest.json`; JPEG 1:1/4:5; derivados 1x1/16x9/cover/thumb/grid | FFmpeg; ponte Node só valida/compila | staging exclusivo + lock `O_EXCL` + backup/rollback; Motion só 9:16; cortes `sourceStartMs` com `SOURCE_CUT_OUT_OF_RANGE` |
| **Aprovação / entrega / ZIP** (`tools/approval_cli.py`, `tools/review_dashboard.py`, `tools/studio_review.py`, `tools/delivery_package.py`, `tools/delivery_verify.py`, `tools/publish_bundler.py`, `tools/handoff_bundler.py`) | decisões do titular + fingerprints → handoff diário, bundle ZIP, ZIP de entrega | store `.workspace/tmp/aprovacoes-titular.json` (ausente nesta estação) | fail-closed: `ajuste` nunca entra; sem aprovação → `PREVIA_NAO_APROVADA` só com flag; ZIP só com `approved_for_local_delivery` |
| **Analytics / A/B / fadiga** (`tools/utm_simulator.py`, `tools/utm_report_importer.py`, `tools/campaign_calendar.py`, `tools/executive_summary.py`, `05-review-portal/`) | CSV exportado (inexistente) → rankings, teste z, fadiga, benchmarks, atribuição; calendário 56 slots | matriz UTM versionada | somente leitura; `promote-hook` dry-run por padrão, `--apply` gated por `editorial_qa --strict` |
| **Hermes / Postiz / ComfyUI** (`marcas/marcasalao/comfyui/marcasalao_media_guard.py`, `marcas/marcasalao/comfyui/postiz-cli-wrapper.py`, `marcas/marcasalao/comfyui/marcasalao_export.py`) | pacote ComfyUI + prompt_id → upload de mídia validada; DRAFT via MCP externa | ComfyUI `127.0.0.1:8188`, Postiz `127.0.0.1:4007`, paths Linux de servidor | guard fail-closed; `publication_authorized:false` obrigatório; um DRAFT por canal/mídia; **inalcançável nesta estação Windows** |
| **Orquestração Temporal** (`orchestration/temporal/`) | Composition → validação via Activity real; piloto | platform (nome público) | só local/`TestWorkflowEnvironment`; produção, namespace remoto e deploy bloqueados |
| **Terceiros / gerados (não código próprio)** | `.agents/skills/*` (1199 arquivos, bundles HyperFrames/etc.), `.agents/plugins/egm/` (Apache-2.0), `package-lock.json`, `platform/dist` (não rastreado), 57 `.woff2`, 1 PDF, 1 ZIP de identidade visual | — | EGM versionado de propósito; skills são catálogo externo |

Volumes de código próprio (linhas, `git ls-files` + `wc -l`): `tools/*.py` sem testes
48.934; `tools/tests/*.py` 27.329; `platform/src` 15.882; `platform/tests` 18.266;
`orchestration/temporal` src+tests 7.410; `tools/studio` JS/JSX 9.972; `marcas/*.py` 1.875.

---

## D. Matriz de inconsistências (documentação × código)

### D1. Contagens, gates e comandos

| # | Afirmação documental | Realidade no código | Cl. | Recomendação mínima |
| --- | --- | --- | --- | --- |
| 1 | `README.md:28` "21 módulos de testes"; `docs/arquitetura-fabrica.md:419,443` idem | 51 módulos em 4 faixas: fast 29 / render 22 / smoke 25 / all 51 (`tools/run_tests.py:61-134`) | C | atualizar para a partição real |
| 2 | `README.md:40-44` tabela 3/5/4/3/4 = **19** campanhas (header diz 14) | 14 JSON em `tenants/*/campaigns/` (marca-salao 2, multitrack-hub 4, meu-salao 3, estudio-flow 2, clinica-vital 3); `04-legendas/calendario-editorial.json` `totalCampaigns:14` | C | corrigir tabela; erro introduzido em `cce0d8c` |
| 3 | `docs/arquitetura-fabrica.md:93-97` mesma tabela de 19, contra :89 "14 campanhas" | idem #2 | C | idem |
| 4 | `README.md:65` e `docs/arquitetura-fabrica.md:350` "5 lentes" | 7 lentes (`tools/editorial_qa.py:76-82`) | C | atualizar |
| 5 | `README.md:60`; `docs/arquitetura-fabrica.md:51,374,419`; comentário `.github/workflows/local-render-validation.yml:107` "7 domínios" | 8 domínios (`tools/release_audit.py:82-91`); docstrings :1, :661, :794 também dizem 7 | C | atualizar docs e docstrings |
| 6 | `docs/arquitetura-fabrica.md:439` "10 campanhas, 5 lentes" | 14 campanhas / 7 lentes | C | atualizar |
| 7 | `contexto_projeto_6.md` §4.4, `docs/arquitetura-fabrica.md` §5.1, `docs/guia-operacional-titular.md` §4: smoke 24/354, fast 28/422, all 50 | HEAD: 25/29/51 módulos; 370/438/341/779 funções `def test` (grep, ≠ `testsRun`) | C | re-medir e republicar com data/SHA |
| 8 | `tools/tests/test_run_tests.py:428-429` em `01074c8` asserta 28/24 | tupla tem 29/25 → gate 8 falha; **edição não commitada de outra sessão corrige para 29/25** | C | commitar a correção pendente (autorização separada) |
| 9 | `tests/e2e/test_factory_e2e.py:185` e :366-368 esperam `{"ok":7,"warn":0,"fail":0}` | auditor emite 8 linhas; sandbox copia os 6 dirs versionados (`tests/e2e/_support.py:33-40`) e domínio 8 sem bundles = `ok` (`tools/release_audit.py:615-624`) → `{"ok":8}`; obsoleto desde `cd2f8ed` (21/11 19:43) | C (estático); falha real H | atualizar para 8; rodar gate 9 isolado |
| 10 | `docs/arquitetura-fabrica.md:167,218`: sem bundles → aviso `BUNDLES_AUSENTES` que reprova em `--strict` | código retorna `[]` → domínio `ok`; `BUNDLES_AUSENTES` não existe no código (só em doc e docstring de teste) | C | corrigir doc; `--strict` não exige bundles |
| 11 | `README.md:57` e `docs/arquitetura-fabrica.md:338`: `campaign_calendar.py --start-date 2026-11-23 --json` | `WEEKS_DEFAULT=4` (`tools/campaign_calendar.py:100`) < mínimo 7 para 14 campanhas (:924-931) → `SEMANAS_INSUFICIENTES`, exit 1 | C (estático) | documentar `--weeks 7` ou tornar default derivado |
| 12 | `docs/arquitetura-fabrica.md:289` `executive_summary.py --capacityStatus` | não é flag (flags em `tools/executive_summary.py:903-913`); é bloco de saída | C | corrigir exemplo |
| 13 | `docs/arquitetura-fabrica.md:287` `--dry-run`/`-apply` | flag real `--apply` (`tools/tenant_scaffolder.py:714`); CLI **exige** modo explícito (:722-723), contrário ao docstring "dry-run padrão" (:14) | C | corrigir |
| 14 | `contexto_projeto_6.md:402` "Nenhuma delas está implementada" (§7.1/7.2) | ambas entregues em `6d9cd18` | C | marcar como implementado com ressalvas (#21, #22, #36) |
| 15 | `contexto_projeto_6.md` §7.3 "hoje o CI roda fast sempre" | CI roda `release_check --skip-ts` **e** loop `REQUIRE_RENDER=1` sobre todos os `tools/tests/test*.py` (`.github/workflows/local-render-validation.yml:144-157`) | C | corrigir; proposta de 3 níveis segue não implementada |
| 16 | `.github/workflows/video-preview.yml` dispara em `02-reels-shorts/**/*.mp4` | `.mp4` nunca é rastreado (gate 1) → filtro de push jamais casa; só `release` o aciona | C | marcar como workflow de release ou remover |
| 17 | README/docstring de higiene "zero `.zip` rastreado" | gate só bloqueia zip com "snapshot" no caminho (`tools/release_check.py:136-143`); `marcas/multitrackhub/identidade-visual/multitrackhub-kit-logo.zip` é rastreado e permitido | C | esclarecer escopo do gate |
| 18 | `tenants/*/campaigns/README.md` | clinica-vital lista 2 de 3; multitrack-hub 3 de 4; marca-salao e meu-salao são placeholders "Etapa 2+" | C | regenerar índices |
| 19 | `contexto_projeto.md` §1: main em `babfc60`, "7/7 gates" | `origin/main` = `276ee41`; 9 gates | C | atualizar topo do devlog |
| 20 | `docs/contexto/ESTADO-ATUAL.md:11-13` "main consultada `2c40967` (18/11)" | `origin/main` = `276ee41`; seção de 21/11 (`9a800d1`) vale só para aquele SHA | C | atualizar bloco Referência |

### D2. Semântica, dados e comportamento

| # | Tema | Evidência | Cl. | Impacto / recomendação |
| --- | --- | --- | --- | --- |
| 21 | `capacityStatus` mistura escopos | `tools/executive_summary.py:529-546`: `current.campaigns`/`minRequiredWeeks`/`headroom` por tenant; `current.tenants` global; `simulated` global com extra=0 → `weekDelta` sempre 0; Markdown :626-632 imprime "2 campanhas … 2 semanas" ao lado de "14 → 7 (delta +0)" | C | relatório executivo enganoso; unificar escopo global ou rotular por tenant |
| 22 | Planejador: bloco "current" com totais simulados | `tools/campaign_calendar.py:576-577` alimenta `current.totalSlotsEstimate`/`slotsPerWeekAvg` (:618-619) com `simulated_total`; `extra_tenants` não afeta semanas | C (leitura delegada) | corrigir antes de usar em decisão de onboarding |
| 23 | `abWinRatePct` fração × percentual | `tools/utm_report_importer.py:862` `round(wins/total,4)`; `tools/executive_summary.py:250` `winRatePct` em %; portal mapeia para % (`tools/review_dashboard.py:578`) | C | armadilha 1 da v6 correta; manter fração e percentual lado a lado |
| 24 | `impressions`/`clicks`/`ctr` não são métricas de anúncio | `tools/utm_report_importer.py:1268-1273`: Σ sessões / Σ sessões engajadas / `_rate` (:208, %); `tools/tests/test_bundle_attribution.py:154-156` fixa 1000/600/60.0 | C | renomear ou documentar; **nenhum dado real existe** |
| 25 | Fadiga "por tenant" é global | `tools/utm_report_importer.py:855-888` passa Onda1/Onda2 globais e copia o mesmo resultado em todo benchmark, contra docstring :841-842 e invariante 3 da v6 | C | calcular por tenant ou rotular como global |
| 26 | Sinal do z de fadiga | docstring `tools/utm_report_importer.py:527` diz `z <= -1.96`; código :566 usa `z >= +1.96` (teste confirma) | C | corrigir docstring |
| 27 | Amostra mínima A/B | gate sobre **soma** das sessões (`tools/utm_report_importer.py:608`) com mensagem "por variante" (:613-616) | C | alinhar texto ou lógica |
| 28 | `manifest.json` × `delivery-manifest.json` | escritores distintos: `tools/preset_runner.py:1188-1269` × `tools/render_pipeline.py:875-914`; nenhum código cruza os dois; `index.json` pode atrasar (reconciliação em `tools/produce_video.py:498-541`) | C | armadilha 5 da v6 correta; documentar que hashes podem divergir entre pipelines |
| 29 | Determinismo de ZIP | `tools/publish_bundler.py:46-47,195-204,565-575` (data 1980, perms 0o600, ordem verificada) × `tools/delivery_package.py:240,422-425` (`zf.write` com mtime + `createdAt` now); carrossel e backup idem | C | declarar quais ZIPs são bit-determinísticos |
| 30 | Determinismo de render | SRT/TXT e manifesto byte-estáveis testados (`tools/tests/test_render_local.py:308-319`, `tools/tests/test_render_pipeline.py:536-537`); **igualdade de bytes do MP4 entre execuções nunca assertada**; sem `-bitexact`/`-threads 1` (armadilha 14 da v6) | C | manter reparo fail-closed; não prometer re-render byte-exato |
| 31 | Áudio legado | `tools/edit_link_reel.py:91-96` `anullsrc` + AAC 192k no reel final; :37 `shell=True`; :12 FFmpeg fora do projeto; :31 escreve `scratch/` | C | quarentena do script ou correção; viola regra de vídeo mudo |
| 32 | DRAFT Postiz × proibição geral | `marcas/marcasalao/comfyui/marcasalao_media_guard.py:76-90` regula só `type=='draft'` dos 2 canais; outros tipos passam (`continue` :82); upload real em :111; wrapper bloqueia CLI direto (`postiz-cli-wrapper.py:10-12`); fábrica inerte | C; efeito na estação Linux H | documentar os dois escopos; avaliar bloqueio de tipos não-draft |
| 33 | Portabilidade do guard | paths `/home/swn/.hermes`, `/dados/aplicacoes/...` (guard :7, :10; wrapper :4); testes do guard (`marcas/marcasalao/comfyui/guard_tests/`, `marcas/marcasalao/comfyui/tests/`) **fora de qualquer faixa do runner e de qualquer CI** | C | registrar requisito de estação; ligar testes a um gate |
| 34 | Núcleo TS "sem marca" | `AUDIO_PERMITTED_TENANTS=['multitrack-hub']` (`platform/src/tenant-policy-contract.ts:72`) + exceção cirúrgica no teste de independência (`platform/tests/beat-plan-validation.test.ts:1034-1039,1092-1103`) | C | decisão explícita: política por dado ou exceção documentada |
| 35 | Ponte TS↔Python de tenant policy | schema Python `audioPolicy` não tem `allowedCodecs` (`schemas/guardrails.schema.json:66-76`); validadores TS de tenant não têm consumidor fora de `platform/` | C; incompatibilidade prática H | criar adaptador ou marcar como contrato futuro |
| 36 | Scaffolder fail-open | grava em `tools/tenant_scaffolder.py:630-636` **antes** de validar (:642); `"ok": True` fixo (:677) mesmo com `tenantValidatorOk=False`; sem rollback; `import editorial_qa` (:49) nunca usado; docstring :5-8 promete SRT/narração/checklist que não são gravados; cenas somam 34 s contra `duration 30` (:391-444) | C | validar antes de gravar, fail-closed, remover código morto; corrigir timing |
| 37 | Scaffolder fora da raiz / CWD global | `tools/tests/test_tenant_scaffolder.py:38` `tempfile.mkdtemp()` sem `dir=` → `%TEMP%`; `shutil.copytree` do checkout inteiro (:51-59); `os.chdir("/")` (:63) | C | viola AGENTS.md e contamina outros testes no mesmo processo |
| 38 | Testes que escrevem na árvore versionada | `tools/tests/test_review_dashboard.py:335-340,457,834` (`build_portal` na raiz real → `05-review-portal/`); `tools/tests/test_campaign_calendar.py:180-182,435-437,544-546` (`generate_calendar` → `04-legendas/`) | C | redirecionar para sandbox; hoje sujariam o tree ao adicionar tenant |
| 39 | Import style do teste novo (em `01074c8`) | `from tools.tenant_scaffolder import …` sem `tools/__init__.py` e sem repo root no `sys.path` do worker → ImportError provável nas faixas fast/smoke; **edição não commitada de outra sessão troca para imports flat** | H (runtime); C (código) | confirmar com execução isolada após commit da correção |
| 40 | Ilustração × evidência | storyboards são desenho stdlib (inspeção visual de `02-reels-shorts/deliveries/marca-salao/camp-saas-demo-marca-salao-001/preview-storyboard.png`); capturas NS-001 são screenshots reais (inspeção visual de `00-briefings/campanhas/NS-001/capturas/2026-11-05/01-agenda-visao-dia.png`); `tools/campaign_proof.py` marca "PROVA FICTICIA" | C (visual) | manter distinção; ver #41 |
| 41 | Captura NS-001 mostra marca "Meu Salão" (instância E2E `e2e-1793884270981`, usuário "Gestor E2E") | inspeção visual da captura de 05/11 | C (visual); implicação editorial H | decidir se a captura serve à campanha Marca Salão antes de uso público |
| 42 | Mídia local × versionada | 84 arquivos em `.workspace/archives/` (42 mp4 + 42 png), 14 mp4 locais em deliveries; versionados: SRT/TXT/4 PNG/manifestos por campanha; pedidos NS-001/NS-002 e demos MTH apontam para PNGs **ausentes** em `.workspace/tmp/` | C | documentar quais exemplos exigem `make_request_media`/`--prepare` antes de exportar |
| 43 | Exclude local incompleto | `.git/info/exclude` cobre worktrees/tools/tmp/archives/logs/studio/reports, **não** `bundles/` nem `snapshots/` (armadilha 16 da v6); devlogs versionados de propósito (19 arquivos) | C | publicar bloco completo no guia de novo nicho |
| 44 | Resíduo local | `.workspace/tmp` = 426 MB com 219 mp4; `.workspace/studio/works` com 100+ trabalhos `demo-marca-salao-*`; relatórios executivos locais de 13:51Z têm `capacityStatus: null` (pré-Etapa 14) | C | limpeza autorizada + rebuild de portal/relatórios |
| 45 | Aprovações e bundles ausentes nesta estação | `.workspace/tmp/aprovacoes-titular.json` não existe; `.workspace/bundles/` não existe → tudo `aguardando`, domínio 8 `ok`, gate bundling sem itens | C | registrar que o estado de aprovação é por estação |

### D3. Verificações positivas confirmadas

- 569 links relativos em 209 `.md` (fora `.agents/`) resolvem; **0 quebrados** (varredura
  própria somente leitura).
- Partição de testes fechada: 51 `test_*.py` em `tools/tests` = 29 fast + 22 render, sem
  órfãos; módulo novo não classificado reprova com erro de uso (`tools/run_tests.py:241-245`).
- Calendário versionado coerente: 56 slots, 7 semanas, 14 campanhas, `autoPublish:false` e
  `statusEditorial:"aguardando_aprovacao_titular"` em todos os slots
  (`04-legendas/calendario-editorial.json`).
- Políticas de áudio dos 5 tenants coerentes com a documentação: 4× `allowAudioTrack:false`
  com `ffmpegFlag:"-an"` e `requireExternalNarration:true`; `multitrack-hub` permitido
  (`tenants/*/guardrails.json`).
- `release_check` = 9 gates na ordem documentada pela v6 (`tools/release_check.py:302-312`);
  todos fatais com `break` no primeiro erro; só `typescript` é pulável.
- Portal determinístico no build (`generatedAt: None`, `tools/review_dashboard.py:546`);
  único caminho de escrita é `POST /api/approvals`.
- `publish_bundler` bit-determinístico e `verify` rejeita entradas desordenadas
  (`tools/publish_bundler.py:565-575`).
- Contenção de caminhos e zip-slip: nenhum `extractall` em `tools/`; restore de backup com
  allowlist e re-hash (`tools/studio_work_backup.py:143-171,941-954`); lock `O_EXCL` e
  rollback (`tools/render_local.py:477-488,676-705`).

---

## E. Riscos classificados por prioridade

### P1 — bloqueiam gate ou violam regra permanente

1. **Gate 8 e gate 9 do `release_check` reprovam no HEAD por asserções obsoletas** (#8, #9).
   Evidência: `tools/run_tests.py:61-134` × `tools/tests/test_run_tests.py:428`;
   `tools/release_audit.py:82-91` × `tests/e2e/test_factory_e2e.py:185`. *Não executado;
   confirmar com execução isolada.* Recomendação: commitar a correção pendente e atualizar
   o E2E para 8 domínios.
2. **`tenant_scaffolder --apply` grava contratos na árvore versionada antes de validar e
   declara sucesso incondicional** (#36). Risco: tenant inválido persistido e reportado
   como ok. Recomendação: validar-antes-de-gravar + rollback + `ok` derivado.
3. **`test_tenant_scaffolder.py` cria sandbox em `%TEMP%` e faz `os.chdir("/")`** (#37) —
   viola a regra de armazenamento e pode contaminar a suíte inteira no mesmo processo.
   Recomendação: `dir=` sob `.workspace/tmp` e remoção dos `chdir`.
4. **Testes que reescrevem `05-review-portal/` e `04-legendas/` na raiz real** (#38):
   qualquer mudança no acervo suja o tree e quebra idempotência byte-a-byte entre
   estações. Recomendação: sandbox obrigatório.

### P2 — decisão de negócio baseada em número errado

5. `capacityStatus` com escopos misturados e `weekDelta` sempre 0 (#21, #22).
   Recomendação: unificar escopo e testar valores, não só presença de chave.
6. Fadiga e benchmarks globais apresentados como por tenant (#25);
   `impressions/clicks/ctr` rotulados como métricas de anúncio sem dado real (#24).
   Recomendação: rotular origem e escopo em todo output.
7. Comando de calendário documentado falha com o acervo atual (#11). Recomendação:
   default derivado ou doc com `--weeks`.
8. Drift de contagens em README/arquitetura/CI (#1–#7, #19–#20) induz operador e outro
   assistente a erro. Recomendação: uma fonte de contagens gerada do código.
9. `edit_link_reel.py` com áudio gerado, `shell=True` e ferramenta externa (#31).
   Recomendação: quarentena ou correção.
10. Guard Postiz não regula tipos não-draft e depende de estação Linux inexistente aqui
    (#32, #33). Recomendação: decisão explícita de escopo + teste do guard em algum gate.

### P3 — higiene, portabilidade e documentação

11. Exclude sem `bundles/`/`snapshots/` (#43); resíduo de 426 MB em tmp e 100+ works demo (#44).
12. READMEs de campanhas por tenant obsoletos (#18); `video-preview.yml` morto em push
    (#16); docstrings de 7 domínios (#5).
13. ZIPs do Studio não bit-determinísticos sem aviso (#29); MP4 sem garantia de bytes entre
    execuções (#30).
14. Captura NS-001 com marca de instância E2E (#41); exemplos NS-001/NS-002 com mídia
    ausente (#42).
15. Constante de marca no núcleo TS e ponte de tenant policy sem consumidor (#34, #35).

---

## F. Alterações relevantes e estado de integração

| Commit / ref | Conteúdo | Estado |
| --- | --- | --- |
| `01074c8dbf28e6cb51f5a494bfb79cc3c8113163` (22/11 14:06) | fix testes scaffold (domain sem protocolo, remove asserts de 14 campanhas por tenant) | **integrado no HEAD local; não push**; criado por outra sessão durante a auditoria |
| `6d9cd18c07d068210292b331a8b9d0b9e1cd12c6` (Etapa 14) | `tenant_scaffolder.py`, `--simulate-capacity`, `capacityStatus`, +1 módulo na faixa fast | integrado no HEAD; **fora de `origin/main`**; defeitos #21, #22, #36–#39 |
| `276ee41`, `82be3b9`, `b9d9b01` (13.1) | faixa `--smoke`, `--smoke-tests`, v6 | em `origin/main` |
| `642f570`…`8f40b79` (13) | runner particionado, ArchivesGuard, reparo, executive_summary | em `origin/main` |
| `54f3e53`, `7df20cc`, `5835005` (12) | atribuição closed-loop bundle→UTM | em `origin/main` |
| `1488a05`, `cd2f8ed` (11) | publish_bundler + **8º domínio** (origem da obsolescência do E2E) | em `origin/main` |
| `51b6842` (10); `f8bf2e9`…`27d14c9` (9) | promote-hook; fadiga/benchmarks | em `origin/main` |
| `cce0d8c`, `4ce5566` (21/11, "chore(wip)") | release_check.py, index.ts agregado, tenant-policy TS, E2E ampliado; **introduziu a tabela errada de 19 campanhas no README** | em `origin/main` (apesar da mensagem "sem push") |
| `899d36b` (21/11 11:19) | E2E da fábrica com expectativa de 7 domínios (correta então) | em `origin/main` |
| `9a800d1`, `08555ad`, `2439fb0` (21/11 manhã) | estabilização CI Etapa 6; **7 domínios, sem E2E** naquele SHA | em `origin/main`; CI verde alegado só para esse SHA |
| `533cc4c` / worktree `utm-ab-recommendations` | comparativo A/B + recomendações | **já em `origin/main`**; worktree leftover limpa |
| branches locais `feat/etapa-9`…`feat/etapa-13-1` | etapas já mescladas | refs locais apenas, trabalho integrado |
| `origin/codex/ai-memory-integration` (PR #1) | integração ai-memory | **NV ao vivo**; docs a registram como única PR aberta, 82 commits atrás |
| Propostas não implementadas | v6 §7.3 (CI 3 níveis, `-bitexact`, snapshot obrigatório, exclude portável, `--list` no runner); produção Temporal; `AudioPlan`/`RenderPlan` | proposta |

Integrações verificadas por ancestralidade Git local (`git merge-base --is-ancestor`), não
por consulta ao GitHub. Nenhuma PR foi declarada integrada sem essa evidência.

---

## G. Backlog recomendado (sem implementar)

1. Commitar (pela sessão dona, com autorização separada) as duas correções pendentes de
   teste; atualizar E2E para 8 domínios; rodar `release_check` isolado e registrar SHA/data.
2. Tornar o scaffolder fail-closed: validar antes de gravar, rollback, `ok` real, timing de
   cenas coerente, remover código morto e docstring exagerada; ligar a um gate ou
   marcá-lo experimental.
3. Confinar `test_tenant_scaffolder` a `.workspace/tmp` e eliminar `os.chdir`; redirecionar
   `test_review_dashboard`/`test_campaign_calendar` para sandbox.
4. Unificar escopo do `capacityStatus` e corrigir `current.totalSlotsEstimate`; adicionar
   asserts de valor.
5. Calcular fadiga/benchmarks por tenant ou rotular global; renomear/rotular
   `impressions/clicks/ctr`; corrigir docstring do z e mensagem de amostra.
6. Corrigir README/arquitetura/CI/docstrings para 14 campanhas, 7 lentes, 8 domínios,
   9 gates, 51 módulos; publicar contagens geradas do código com data/SHA.
7. Default de semanas do calendário derivado do acervo (ou doc com `--weeks 7`).
8. Quarentena/correção de `edit_link_reel.py` (áudio, shell, caminho externo).
9. Decidir escopo do guard Postiz (tipos não-draft) e destino dos testes órfãos do guard;
   documentar a estação Linux como requisito.
10. Completar `.git/info/exclude` portável no guia; limpeza autorizada de tmp/works demo;
    rebuild de portal e relatórios pós-Etapa 14.
11. Documentar determinismo por tipo de ZIP e limites do render; registrar que MP4 não é
    byte-reprodutível entre versões.
12. Decidir constante de marca no núcleo TS e o destino da ponte de tenant policy; revisar
    uso público da captura NS-001 com marca E2E.

---

## H. Arquivos adicionais que o outro assistente precisa receber

Além deste relatório: `AGENTS.md`, `contexto_projeto_6.md`,
`docs/contexto/ESTADO-ATUAL.md`, `docs/contexto/PROXIMOS-PASSOS.md`,
`docs/contexto/HANDOFF.md`, `docs/arquitetura-fabrica.md`,
`docs/guia-operacional-titular.md`, `tools/run_tests.py`, `tools/release_check.py`,
`tools/release_audit.py`, `tools/editorial_qa.py`, `tools/tenant_scaffolder.py`,
`tools/campaign_calendar.py`, `tools/executive_summary.py`, `tools/utm_report_importer.py`,
`tools/publish_bundler.py`, `tools/delivery_package.py`, `tools/render_pipeline.py`,
`tools/preset_runner.py`, `marcas/marcasalao/comfyui/marcasalao_media_guard.py`,
`tests/e2e/test_factory_e2e.py`, `tests/e2e/_support.py`,
`.github/workflows/local-render-validation.yml`, os 5 `tenants/*/guardrails.json`,
`04-legendas/calendario-editorial.json`, e o diff não commitado de
`tools/tests/test_run_tests.py` + `tools/tests/test_tenant_scaffolder.py` (estado de outra
sessão, não parte desta auditoria).

---

## I. Cobertura da leitura

### I.1 Lidos integralmente pela auditoria principal

- `README.md`; `WORKFLOW.md`; `CLAUDE.md` (topo); `AGENTS.md` (contexto carregado da sessão).
- `docs/contexto/README.md`; `docs/contexto/HANDOFF.md`; `docs/contexto/PROXIMOS-PASSOS.md`;
  `docs/contexto/ESTADO-ATUAL.md` (1172 linhas, em lotes, incluindo todas as seções de
  marco, NS-001, governança e "o que não verificou").
- `contexto_projeto_6.md` (476 linhas); `docs/arquitetura-fabrica.md` (477 linhas);
  `docs/guia-operacional-titular.md` (287 linhas); `00-briefings/README.md` (144 linhas).
- Cabeçalhos e estados de `00-briefings/campanhas/NS-001/briefing.md` e
  `00-briefings/campanhas/NS-002/briefing.md`; índice de seções de
  `00-briefings/TEMPLATE-BRIEFING.md`.
- `tests/e2e/_support.py` (196 linhas); `marcas/marcasalao/comfyui/postiz-cli-wrapper.py`
  (13 linhas); `marcas/marcasalao/comfyui/marcasalao_media_guard.py` (133 linhas).
- `.gitignore`; `.gitattributes`; `.git/info/exclude`.
- Trechos dirigidos com linhas verificadas: `tools/run_tests.py` (docstring, tuplas,
  partição, worker); `tools/release_check.py` (GATES, higiene, flags);
  `tools/release_audit.py` (DOMAIN_NAMES, `_domain`, domínio 8, summary);
  `tools/editorial_qa.py` (CHECK_IDS e nomes); `tools/campaign_calendar.py` (constantes,
  mínimo de semanas, CLI, `simulate_calendar_capacity`); `tools/executive_summary.py`
  (`_capacity_section`, Markdown, flags); `tools/utm_report_importer.py` (métricas,
  `ab_rate`, benchmarks); `tools/publish_bundler.py` (determinismo);
  `tools/delivery_package.py` (manifesto, escrita do ZIP); `tools/delivery_verify.py`
  (docstring); `tools/video_studio.py` (bind, Host/Origin, tamanho);
  `tools/studio_review.py` (estados); `tools/tenant_scaffolder.py` (flags);
  `tenants/*/guardrails.json` e `tenants/*/brand-kit.json` (política de áudio, preset,
  domínio, uiLabels); `04-legendas/calendario-editorial.json` e
  `05-review-portal/portal-data.json` (contagens e chaves);
  `.github/workflows/local-render-validation.yml` (gatilhos e passos 103-158);
  `contexto_projeto.md` (topo, seção 1); `docs/designs/SITEMAP.md` (topo);
  `.agents/plugins/marketplace.json`.

### I.2 Lidos integralmente por subagentes somente leitura (4 levantamentos)

- **Núcleo TS/Temporal:** `platform/package.json`, `tsconfig.json`, `index.ts`,
  `cli-input.ts`, `relative-path.ts`, `tenant-policy-contract.ts`,
  `validate-tenant-policy.ts`, `validate-execution-tenant-compatibility.ts`,
  `output-profiles/{catalog,geometry,rules,types,local-export}.ts`,
  `compile-video-request.ts`, `resolve-motion-plan.ts`, `resolve-output-profile.ts`,
  `resolve-content-pipeline-case.ts`, `simulated-execution-{runner,writer}.ts`,
  `create-simulated-execution-plan.ts`, `serialize-simulated-execution.ts`,
  `create-creative-execution-package.ts`, `serialize-creative-execution-package.ts`,
  `creative-execution-packages.ts`, `validate-composition.ts`,
  `validate-composition-output.ts`, `composition-validation-api.ts`,
  `asset-manifest-contract.ts`, `serialize-asset-manifest.ts`,
  `validate-asset-manifest.ts`, `validation-report.ts`, os 16 schemas (campos obrigatórios),
  `orchestration/temporal/README.md`, `package.json` e src de workflows/activities/
  pilot-core/composition-validation; testes de fronteira pública e de independência de marca.
- **Fábrica/testes/gates:** `tools/run_tests.py`, `tools/release_check.py`,
  `tools/release_audit.py`, `tools/editorial_qa.py`, `tools/tenant_validator.py`,
  `tools/tenant_scaffolder.py` (762 linhas), `tools/tests/test_run_tests.py`,
  `test_tenant_contracts.py`, `test_release_audit.py`, `test_editorial_qa.py`,
  `test_tenant_scaffolder.py`, `tests/e2e/test_factory_e2e.py`, `_support.py`,
  `schemas/*.json`, todos os `tenants/`, os 5 workflows de CI.
- **Studio/render/entrega:** `tools/video_studio.py` (3500 linhas, em lotes),
  `studio_planning.py`, `studio_media.py`, `studio_queue.py`, `studio_review.py`,
  `studio_templates.py`, `studio_preflight.py`, `studio_connections.py`,
  `studio_video_api.py`, `studio_work_backup.py`, `studio_mcp_server.py`,
  `render_local.py`, `render_pipeline.py`, `render_bridge.mjs`, `build_video.py`,
  `produce_video.py`, `produce_carousel.py`, `derivative_formats.py`,
  `carousel_layout.py`, `static_cards.py`, `edit_link_reel.py`, `delivery_package.py`,
  `delivery_verify.py`, `publish_bundler.py`, `handoff_bundler.py`,
  `prepare_asset_manifest.py`, `approval_cli.py`, `tools/render/README.md`,
  `tools/produce/README.md` e guias de preflight/backup/verificação,
  `tools/studio/planning.js`, `media.js`; componentes React em skim.
- **Analytics/adaptadores:** `utm_simulator.py`, `utm_report_importer.py`,
  `campaign_calendar.py`, `executive_summary.py`, `image_adapters.py`, `llm_adapter.py`,
  `audio_tts.py`, `archives_guard.py`, `marcasalao_media_guard.py`,
  `postiz-cli-wrapper.py`, `marcasalao_export.py`,
  `custom_nodes/servidor02_gemini/client.py`, `05-review-portal/README.md`,
  `test_bundle_attribution.py`; seções dirigidas de `review_dashboard.py`,
  `approval_cli.py`, `workspace_doctor.py`, `publish_bundler.py`, `devlog_sync.py`,
  `studio_connections.py`, `ns002_pilot.py`, `r002_pilot.py`, `campaign_proof.py`,
  `05-review-portal/index.html`, `portal-data.json`, `05-mensuracao/*`.

### I.3 Inspecionados visualmente (2 de 284 PNGs rastreados)

- `02-reels-shorts/deliveries/marca-salao/camp-saas-demo-marca-salao-001/preview-storyboard.png`
  — desenho sintético em fonte bitmap, dados fictícios; **não** é captura do produto.
- `00-briefings/campanhas/NS-001/capturas/2026-11-05/01-agenda-visao-dia.png` — captura real
  de instância E2E ("Meu Salão E2E e2e-1793884270981", usuário "Gestor E2E", 05/11/2026).

### I.4 Apenas inventariados (não lidos linha a linha)

- Demais 282 PNGs rastreados; 57 `.woff2`; `03-youtube-pdf/tutorial_marcasalao.pdf`;
  `marcas/multitrackhub/identidade-visual/multitrackhub-kit-logo.zip`.
- `.agents/` (1199 arquivos de terceiros: skills HyperFrames/video-use/etc. e bundle EGM).
- `tools/studio/app.js` legado e `tools/studio/frontend/src/*.jsx` (skim).
- `marcas/marcasalao/posts/` (76 arquivos) e `marcas/multitrackhub/posts/` (50).
- `.workspace/devlogs/` (19); `docs/hermes/*`, `docs/historico/*`, `docs/planejamento/*`,
  `docs/decisoes/*` (parciais/topo); `contexto_projeto.md` (3470 linhas; só topo e seções
  citadas); `platform/README.md` e `orchestration/temporal/README.md` via subagente.
- Binários de mídia local (`.workspace/archives`, deliveries `.mp4`): inventariados por
  contagem e SHA-256 declarado em manifesto; **não** reproduzidos nem inspecionados por
  FFprobe nesta auditoria.

### I.5 Não verificados / inacessíveis

- Estado remoto ao vivo do GitHub (PRs, runs de CI posteriores a `9a800d1`): **NV**.
- Postiz, ComfyUI, Hermes, Gemini, LLM local: comportamento real **NV** (só código lido).
- `platform/dist` (não rastreado) e comportamento de runtime dos CLIs compilados: **NV**.
- Credenciais, `.env`, tokens, cookies: nunca abidos nem exibidos (por proibição).
- `.workspace/` de outras estações; mídia local ausente noutras máquinas: **NV**.
- Execução de qualquer teste/gate/render: **não realizada** (por proibição).
- `tools/tests/ci_studio_astryx_browser.py` e provas `ci_*_proof.py`: inventariados e
  referenciados pelo CI; corpos não lidos integralmente.

---

## J. Limitações da análise

1. **Nenhum teste, gate, render ou build foi executado.** Todos os "deve falhar"/"tende a
   reprovar" são conclusões estáticas (`H` onde indicado). Resultados históricos citados
   (CI run 44904714554 em `9a800d1`, 21/11; suítes 354/422 da v6; 807/926/994 testes da
   platform em marcos anteriores) são **registros documentais com data e fonte**, não
   medições desta auditoria.
2. **Remoto não atualizado** (fetch/pull proibidos); `origin/main` local pode estar atrás;
   PRs citadas em docs não foram confirmadas ao vivo.
3. **Integrações não consultadas:** comportamento de Postiz/ComfyUI/Gemini/Hermes descrito
   apenas por código; a estação Linux do guard (`/home/swn/...`) não existe neste checkout.
4. **Mídia local é por estação:** os 84 arquivos de `.workspace/archives/` e os 14 mp4 de
   deliveries existem aqui; noutra estação os mesmos manifests valem sem os bytes. Pedidos
   NS-001/NS-002 e demos Multitrack Hub referenciam PNGs ausentes até `--prepare`/gerador.
5. **Concorrência:** HEAD e working tree mudaram durante a auditoria por outra sessão;
   achados podem ser superados por commits dessa sessão a qualquer momento. As duas
   edições não commitadas observadas no fechamento **não** são da auditoria.
6. **Contagens de funções de teste** por grep de `def test` não equivalem a `testsRun`
   (skips, subTestes e suítes dinâmicas podem diferir).
7. **Cobertura delegada:** linhas citadas de leituras delegadas foram conferidas por
   amostragem nos achados de cabeçalho; o restante confia na leitura integral declarada
   pelo subagente, sem reexecução.
8. **Escopo de autorização:** este documento não autoriza produção, publicação, mídia,
   deploy, nova fatia de TEMPORAL-02 nem qualquer implementação do backlog.

---

## K. Contenção e handoff desta tarefa de salvamento

- Destino resolvido: `<RAIZ>/docs/auditorias/AUDITORIA-PROJETO-2026-11-22.md`, com `<RAIZ>`
  confirmado por `git rev-parse --show-toplevel` antes da gravação; o caminho resolvido
  começa exatamente com `<RAIZ>/`. A pasta `docs/auditorias/` não existia e foi criada
  apenas para este arquivo.
- O arquivo não existia antes da gravação (verificado por `ls`); **nenhum relatório
  anterior foi sobrescrito**.
- Único conteúdo criado por esta tarefa: este relatório e, se necessária, sua pasta.
  Nenhum outro arquivo foi criado, alterado ou removido; nenhum `git add`, commit ou push
  foi executado (exigem autorização separada).
- Worktrees: nenhuma criada ou removida; as duas existentes foram apenas listadas.
  Ferramentas portáteis: nenhuma usada. Temporários: nenhum criado ou removido.
- `git status --short` após a gravação: ver retorno no chat desta tarefa (as duas
  modificações em `tools/tests/` são de outra sessão; o relatório aparece como untracked
  em `docs/auditorias/`).
- Confirmação: nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido
  fora de `<RAIZ>` (o checkout principal desta estação).