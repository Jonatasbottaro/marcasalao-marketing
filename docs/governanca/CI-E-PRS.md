# CI, gates locais e padrão de Pull Requests

Fonte canônica do mapa de verificação contínua e do fluxo de PRs deste repositório.
Base verificada: `main` @ `05ca7fa` e branch documental `7e3d710` (22/11/2026), por leitura
dos workflows e do código; **nada foi executado para produzir este mapa**. Política de
manutenção: [DOCUMENTACAO.md](DOCUMENTACAO.md). Índice: [../README.md](../README.md).

## 1. Workflows reais em `.github/workflows/`

| Workflow | Gatilhos (paths) | Jobs e comandos principais | Observações verificadas |
| --- | --- | --- | --- |
| `platform-validation.yml` | push/PR em `platform/**` e no próprio arquivo; `workflow_dispatch` | 1 job, matriz Ubuntu+Windows × Node 22/24, `fail-fast:false`, `permissions: contents: read`; `npm ci` → `clean` → `typecheck` → `npm test` via `platform/scripts/gate-step.sh` (preserva exit code), com auto-prova de falha (exit 7) e artifact em falha | Gate do núcleo TS; não toca fábrica Python |
| `local-render-validation.yml` | push/PR em `tools/**`, `platform/**`, `schemas/**`, `tenants/**`, deliveries, pacotes, calendário, matriz UTM, portal, `docs/**`, `tests/e2e/**` e no próprio arquivo; dispatch | Ubuntu+Windows, Node 22 + Python 3.12 + FFmpeg (ação oficial); `npm ci && build && test`; **`python tools/release_check.py --skip-ts --json`**; `tenant_validator --all`; `factory_cli list/pipeline --skip-render`; `utm_simulator`; lista explícita de módulos unittest; `release_audit --strict`; `discover -s tests/e2e`; laço `REQUIRE_RENDER=1` sobre **todos** `tools/tests/test*.py` em lotes (split antes de `test_studio_work_backup.py`); ~15 provas reais de render/HTTP (`ci_*_proof.py`, Studio, carrossel, Motion, cortes, multiformato, ZIP); invariante final: nenhum `.mp4`/`.wav` fora de `.workspace/` | É o gate mais pesado; o laço com `REQUIRE_RENDER=1` ignora as faixas do runner e roda os 51 módulos |
| `studio-frontend-ci.yml` | push/PR em `tools/studio/frontend/**`, `tools/studio/index.html`, `app.js`, `video_studio.py`, testes de frontend e no próprio arquivo; dispatch | Ubuntu+Windows; build da `platform`; `npm ci && npm run build` do frontend + presença de `dist/.vite/manifest.json`; `PYTHONPATH=tools python -m unittest tools/tests/test_studio_astryx_frontend.py`; Playwright + `tools/tests/ci_studio_astryx_browser.py` | Prova de navegador do painel |
| `temporal-pilot-ci.yml` | push/PR em `orchestration/temporal/**`, `docs/planejamento/TEMPORAL-01-piloto-de-orquestracao.md` e no próprio arquivo; dispatch | Ubuntu+Windows × Node 22, `timeout-minutes: 15`; build da `platform`; `npm ci/clean/build/typecheck/test` do pacote Temporal | Piloto local; não implica produção |
| `video-preview.yml` | push em `02-reels-shorts/*.mp4` e `02-reels-shorts/*/*.mp4`; `release: [created]` | Ubuntu; miniaturas FFmpeg em `previews/` + artifact | **Efetivamente morto em push**: o gate de higiene proíbe `.mp4` rastreado, então o filtro de path nunca casa; só dispara em release. Sem bloco `permissions:` |

## 2. Gates locais (antes de abrir PR)

| Comando | O que verifica | Custo/observação |
| --- | --- | --- |
| `python tools/release_check.py [--skip-ts] [--smoke-tests \| --full-tests] --json` | 9 gates em ordem: higiene Git + `autoPublish`, TypeScript, contratos (5 tenants), editorial `--strict` (14 campanhas/7 lentes), `workspace_doctor --check`, `release_audit --strict` (8 domínios), empacotamento, suíte particionada (`--fast` padrão) e E2E | Falha no primeiro gate com erro (não continua). `--skip-ts` quando `platform/` já compilado |
| `python tools/run_tests.py --smoke \| --fast \| --render \| --all --json` | Faixas mutuamente exclusivas: smoke 25 / fast 29 / render 22 / all 51 módulos, sempre sob `ArchivesGuard` | `--fast` é o gate oficial; `--render` exige FFmpeg portátil e **não** deve rodar junto de outros gates |
| `python tools/verify_egm_install.py` | Integridade offline do bundle EGM em `.agents/plugins/egm/` e o wiring em `AGENTS.md`/`CLAUDE.md`/`docs/designs/` | Inclui a diretiva `EGM artifact directory: .workspace/tmp/egm` |
| `python tools/tenant_validator.py --all --json` | Contratos dos 5 tenants (brand-kit, guardrails, fixture) | Fonte da lista de tenants |
| `python tools/workspace_doctor.py --check` | Saúde do checkout: FFmpeg, integridade SHA-256/FFprobe de `.workspace/archives`, worktrees, higiene de tmp | `--repair` é dry-run por padrão |
| `python tools/release_audit.py --strict --json` | 8 domínios de prontidão | Domínio 8 sem bundles = `ok` (informativo) |

## 3. Padrão de Pull Requests

1. **Toda mudança abre PR a partir de branch técnica isolada** (worktree em
   `<RAIZ>/.workspace/worktrees/<tarefa>`), com base sincronizada por
   `git fetch origin --prune` + fast-forward quando autorizado.
2. **O PR usa [.github/PULL_REQUEST_TEMPLATE.md](../../.github/PULL_REQUEST_TEMPLATE.md)**:
   frente afetada, conformidade com regras permanentes (`<RAIZ>`, `-an`, `autoPublish:false`,
   isolamento de tenant, sem caminhos de máquina, sem credenciais), sincronização documental,
   evidências literais de verificação e handoff.
3. **Documentação acompanha código no mesmo PR**: qualquer alteração de contrato, CLI,
   schema, workflow, contagem ou comando atualiza a fonte canônica correspondente
   ([MAPA-DOCUMENTAL.md](MAPA-DOCUMENTAL.md) §1) e o `docs/contexto/ESTADO-ATUAL.md` quando o
   estado técnico muda.
4. **CI verde no SHA do PR não substitui revisão humana** de regras editoriais e de
   autorização; e revisão humana não substitui os gates.
5. **Merge somente com autorização do titular** para frentes que a exigem (produção de
   mídia, integrações, Temporal de produção, deploy). Integração por merge commit que
   preserva os commits originais é o precedente do repositório.
6. **Resultados de teste citados em PR carregam SHA, ambiente, comando e data**; contagem de
   funções `def test` não é `testsRun`, e skip em faixa de render significa cobertura
   ausente, não aprovação.

## 4. Lacunas conhecidas do mapa

### Resolvidas em 23/11/2026 (branch `fix/release-check-portabilidade`, commit `de91076`)

- **Gate 8 (`unit_tests`) reprovava no CI (Ubuntu + Windows, run `45242091211`, SHA `1149a03`):**
  `tools/tests/test_workspace_doctor.py::test_09_ffmpeg_ausente` removia do PATH as entradas
  cujo nome continha "ffmpeg". Na estação isso isolava o binário portátil
  (`.workspace/tools/ffmpeg/`), mas no runner o FFmpeg é instalado por ação oficial
  (`FedericoCarboni/setup-ffmpeg`) num diretório de cache cujo basename é `bin` — o filtro
  não removia nada, o `workspace_doctor` enxergava o ffmpeg real do PATH e o teste falhava
  (`AssertionError: True is not false`). **Correção:** o teste passa a remover do PATH
  **somente a entrada que expõe o ffmpeg real** (`shutil.which`), preservando as demais
  entradas (git etc.); funciona no runner e na estação. Medido: `release_check.py
  --skip-ts --json` 9/9 gates, exit 0, `unit_tests` 456/456, 0 skips (Windows, PATH estilo
  runner). CI sobre `de91076` (runs `45257399186` e `45257382687`) — resultado pendente de
  consulta ao vivo.
- **Testes condicionados a acervo local convertidos em fixtures sintéticas:** `test_25`/`26`
  de `test_release_audit` e `test_17` de `test_run_tests` agora criam archives sintéticos em
  sandbox; `test_executive_summary.test_23` usa sandbox próprio em vez de apagar
  `.workspace/reports/<tenant>/` compartilhado. `test_25` do `workspace_doctor` usa a
  descoberta efetiva (PATH/portátil) e falha com `REQUIRE_RENDER=1` quando não há ffprobe.

### Resolvidas em 22/11/2026 (branch `fix/release-gates-p1-2026-11-22`, commit de código `7572c77`)

- **Gate 7 (`bundling`) do `release_check`:** `tools/release_check.py:229-234` invocava
  `publish_bundler.py verify` sem o `--bundle` obrigatório (erro de uso, exit 2), reprovando
  em qualquer estação e interrompendo os gates 8 e 9. Corrigido com
  `publish_bundler.verify_all_bundles()` + CLI `verify --all` (padrão) / `--bundle`
  (retrocompatível); o gate expõe `checkedCount`. Medido: gate `bundling` ok e
  `release_check --json` **exit 0, 9/9 gates** na worktree `fix-p1` (estação Windows).
- **E2E com 7 domínios:** `tests/e2e/test_factory_e2e.py:185,367` esperava
  `{"ok": 7, ...}` contra os 8 emitidos desde `cd2f8ed`. Atualizado para 8 com
  `strict=True`; medido `unittest discover -s tests/e2e` 5/5 com
  `release_audit:8/8 strict`. O sandbox passou a viver no `.workspace/tmp` do checkout
  principal (`tests/e2e/_support.py`), porque worktrees estouram MAX_PATH do Windows.
- **Acoplamentos de estação que derrubavam o gate 8 fora do CI** (corrigidos como
  isolamento de teste, sem mudar produto): workspace do aceite de backup sem
  `tenants/`/acervo (preflight editorial reprovava); snapshot do `test_video_studio`
  sensível a `-wal`/`-shm` do SQLite; `test_executive_summary` assumia relatórios na
  raiz própria em vez do `.workspace` compartilhado (invariante 5); `test_review_dashboard`
  proibia `..` sem distinguir referência interna ao workspace compartilhado de vazamento
  real; `test_tenant_scaffolder` usava `%TEMP%` e `os.chdir("/")`, contaminando módulos
  seguintes no mesmo processo; `build_video` não resolvia o FFmpeg portátil fora do PATH.

### Ainda abertas (registradas, não corrigidas aqui)

- Os testes de `marcas/marcasalao/comfyui/{guard_tests,tests}/` não são cobertos por nenhum
  workflow nem por nenhuma faixa do runner.
- `video-preview.yml` não dispara em push (seção 1) e não declara `permissions:`.
- Não há verificação documental automatizada no CI (proposta em
  [DOCUMENTACAO.md](DOCUMENTACAO.md) §6, pendente de decisão).
- `.workspace/devlogs/*.md` são **versionados de propósito** (consolidação via
  `tools/devlog_sync.py`), exceção documentada à regra de que `.workspace/` não sincroniza;
  o restante de `.workspace/` é ignorado por `.git/info/exclude`, local por estação.
- Escopo misto de `capacityStatus` em `tools/executive_summary.py` (bloco `current` por
  tenant × `simulated` global) permanece como P2 no backlog da consolidação documental.
- Os testes de `marcas/marcasalao/comfyui/{guard_tests,tests}/` não são cobertos por nenhum
  workflow nem por nenhuma faixa do runner.
- `video-preview.yml` não dispara em push (seção 1) e não declara `permissions:`.
- Não há verificação documental automatizada no CI (proposta em
  [DOCUMENTACAO.md](DOCUMENTACAO.md) §6, pendente de decisão).
- `.workspace/devlogs/*.md` são **versionados de propósito** (consolidação via
  `tools/devlog_sync.py`), exceção documentada à regra de que `.workspace/` não sincroniza;
  o restante de `.workspace/` é ignorado por `.git/info/exclude`, local por estação.