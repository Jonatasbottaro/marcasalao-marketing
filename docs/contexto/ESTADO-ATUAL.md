# Estado atual do projeto

## Referência

- Data da atualização: 2026-11-12
- Branch de referência: main
- Commit da main consultada: [2c409676e58e4e118d865821b9a0cbdd93a22364](https://github.com/Jonatasbottaro/marcasalao-marketing/commit/2c409676e58e4e118d865821b9a0cbdd93a22364) — revisão de `AGENTS.md` que fixou a raiz oficial como o próprio checkout com `.workspace/` dentro dele; base sobre a qual a integração do R002 foi commitada. A redação portável de 12/11/2026 substituiu o caminho literal por `<RAIZ>` = `git rev-parse --show-toplevel`
- Merge de integração do piloto local R002: `b7ed1d9bbf397f5e9f14bfddc62c67aa0d4f5cf9`, a partir da branch técnica `codex/r002-video-local-agenda` (HEAD `b59076918eea6a2eaecda90bf2ec3c8cb4ac6c60`), com commit corretivo único `0ac4bde8e5096ecdf4913a48ad453e066346b213`
- Merge de integração da execução local de TEMPORAL-02: `5376890974d4baf49b341297a9b7b0071a680dc6`, a partir da branch `codex/temporal-02-execucao-local` (HEAD `63d04d5e4476e13a34f4636b19a08e642627b70b`), por pedido explícito do titular em 12/11/2026 de atualização completa do remoto
- Merge de integração da validação consolidada do pipeline criativo: `c461a3ca11e51ffe7082f7b11661632c0024def0`, a partir da branch técnica `codex/content-pipeline-validation` (HEAD `2fa8f04`), por autorização explícita do titular em 12/11/2026, com os três commits originais preservados (`3931993`, `3527a19`, `2fa8f04`)
- Integração do segundo consumidor real (Multitrack Hub) e dos casos de pipeline: fast-forward `f8ad1ea..36551ded3e34520a4e7da3c07ee413b19020956b`, a partir da branch técnica `codex/multitrack-pipeline-consumer`, por autorização explícita do titular em 12/11/2026 (entrega multiprojeto), com os três commits originais preservados (`54bfd6f`, `8d1b131`, `36551de`)
- Merge de integração do CreativeExecutionPackage v1: `dbf4d31c9f0882827f9fdf9bb79f18f00b3d092d` (merge commit, sem squash/rebase), a partir da branch técnica `codex/creative-execution-package-v1` (HEAD `d016218a52acbff33c50542e5f17fadd0a3910f9`), por autorização explícita do titular em 12/11/2026 (pacote técnico de execução v1), com os quatro commits originais preservados (`d43a9ec`, `b5bc7a0`, `df7fe90`, `d016218`)
- Merge de integração do executor local simulado v1: `2824728300f20c89fe02717e29130895996ae85b` (merge commit, sem squash/rebase), a partir da branch técnica `codex/simulated-execution-runner-v1` (HEAD `842322ff51f7fadf3d2702770f4bfb6b48800f88`), por autorização explícita do titular em 12/11/2026 (executor local simulado v1), com os quatro commits originais preservados (`87b1a33`, `1e17a71`, `d8cb07f`, `842322f`)
- Commit técnico da fatia Workflow: `f5842107a0f307b4cc208c15fc4509c6d7d31f72`
- Ratificação da fatia Workflow: registrada pelo titular em 2026-11-11, restrita ao escopo homologado de `f584210`
- Merge de integração do BeatPlan v1: `d5761b1f37d1a5b5e55e2f1b7422c969e6194957`
- HEAD técnico reconciliado do BeatPlan: `7d919fc208ac4dfeebe5b0b65a959171e5f093f2`, da branch `codex/reconcilia-beat-plan-v1`
- Regra permanente de armazenamento na raiz do projeto: [AGENTS.md](../../AGENTS.md), com a raiz vigente registrada em `2c409676e58e4e118d865821b9a0cbdd93a22364`
- Orientação de segurança de worktrees sob a convenção `.workspace/`: `79fd5dae1db5450960d4cebe922ea26b71d8b6c5`
- Limpeza de branches remotas: 14 branches excluídas em 11/11/2026 por autorização explícita do titular; 7 branches remotas restantes. Detalhe na seção Limpeza de branches remotas
- Fonte: Git e documentos da main consultada; evidências da homologação técnica e do GitHub Actions vinculadas aos respectivos commits, sem nova execução de gates nesta atualização documental

O último commit técnico da main e do núcleo `platform/` é o merge `2824728` do executor local simulado v1 (contratos `SimulatedExecutionPlan`/`SimulatedExecutionReport`, compilador puro, runner com falha/cancelamento/retomada, artefatos textuais simulados, hashes SHA-256, writer transacional, multicase, CLI `content:simulate-execution`, fixtures dos dois consumidores e suíte de 807 testes); o anterior é o merge `dbf4d31` do CreativeExecutionPackage v1 (contrato, schema draft-07, gerador puro, validador puro, serialização canônica, packageId determinístico, geração multicase, CLI transacional `content:build-execution-packages`, fixtures dos dois consumidores e suíte de 755 testes); o anterior a esse é o fast-forward `36551de` do segundo consumidor real (Multitrack Hub) e dos casos de pipeline (`ContentPipelineCaseManifest`, resolvedor seguro, CLI `content:validate-cases`, fixtures da Multitrack Hub e suíte de 709 testes); e o anterior a esse é o merge `c461a3c` da validação consolidada do pipeline criativo (`validateContentPipeline`, CLI `content:validate-pipeline`, fixtures e suíte de 651 testes); a execução local de TEMPORAL-02 permanece integrada pelo merge `5376890` e o piloto local R002 pelo merge `b7ed1d9`. A validação consolidada do pipeline é uma capacidade estritamente local e determinística interna à `platform`, sem alterar a API pública mínima (`composition-validation-api.ts`), sem subpaths públicos, sem entrar no Temporal e sem envolver renderização, mídia ou deploy. A Activity `validateCompositionActivity` permanece integrada e ratificada no escopo de **TEMPORAL-02-03**; o Workflow `validateCompositionWorkflow`, seu contrato de resultado, o classificador de falhas e a Retry Policy estão integrados e homologados tecnicamente em `f584210` e **ratificados pelo titular em 2026-11-11**, com escopo estrito detalhado na seção TEMPORAL-02 — Fatia Workflow. A ratificação não aprova o PRD completo nem autoriza qualquer fatia posterior. O cliente de validação, `workflow.start` da aplicação, Workflow ID determinístico, políticas de reuso e conflito, colisão sanitizada, Worker local, replay formal e o gate Elephant–Goldfish de TEMPORAL-02 estão **integrados em escopo estritamente local** pelo merge `5376890` (12/11/2026); Worker de produção, servidor Temporal remoto, namespace de produção, `contentHash` e deploy continuam ausentes e bloqueados. O R001 está integrado no núcleo e o **BeatPlan v1 está integrado tecnicamente como fatia interna da `platform`**, sem ampliar a API pública. A **regra permanente de armazenamento** é normativa em [AGENTS.md](../../AGENTS.md) e vale para qualquer clone; detalhe na seção Governança de armazenamento e áreas de trabalho. Após a auditoria, o titular autorizou e foi executada a **limpeza de 14 branches remotas**; a única pendência real de branch é a PR #1 (`codex/ai-memory-integration`).

Os marcos permanecem distintos e não se substituem:

- commit técnico final de TEMPORAL-01: `07e38f47df50fd6d8b264bc999fe4082be4b2bb6`;
- merge da estrutura `docs/contexto/` pela PR #7: `fbd222d996527f6cf226051a8526f932accd7e5e`;
- correção pós-merge do contexto: `3304e82aedf5db59d6507ece6ca20b4df46ac973`;
- integração documental do PRD de TEMPORAL-02: `33b46ce54649fc60340c2e85b15d0b39ad112cff`;
- atualização documental do contexto com o PRD de TEMPORAL-02: `d2ebab2cf773cefa24320d26921122d75b3eaa8e`;
- integração técnica de TEMPORAL-02-01 (fronteira pública mínima da `platform`): `f202377fac721aff1d4143a2598f76c03062f0ac`;
- fechamento documental e de higiene de TEMPORAL-02-01: `f1da1f9d0b62bf94be44779b8db4e00610dd7ee5`;
- integração técnica de TEMPORAL-02-02 (contrato de entrada versionado e preflight local em `orchestration/temporal/`): `29b40783320360350e59a13e39f49a60d2308507`;
- atualização documental do contexto pós-TEMPORAL-02-02: `285e5a7c7f956a9628bbbd6055d270844f195a8e` / `8a0a13250c38ee7512bd0bd85d4495179927e8fb`;
- integração técnica de TEMPORAL-02-03 (Activity real `validateCompositionActivity`): `db84270ad3e51eecb0b562fcdf3a7e36941288ab`;
- registro da ratificação e contexto de TEMPORAL-02-03: `8f94e0205b470b46da918d78f8136fafa9a2286a`;
- integração técnica da fatia Workflow de TEMPORAL-02: `f5842107a0f307b4cc208c15fc4509c6d7d31f72`;
- integração do R001: `e86f3c9ef939ac7536ecf39a65cf4f6ee97e4b52`, contendo a reconciliação `8e17785a5634167f8abdaebacb8388276b909cab`;
- reconciliação técnica do BeatPlan v1 sobre a main que já contém R001: `7d919fc208ac4dfeebe5b0b65a959171e5f093f2`, com cinco commits temáticos preservados (`9c872a6`, `d46ea5a`, `4230eba`, `559d22c`, `7d919fc`);
- merge de integração do BeatPlan v1 interno: `d5761b1f37d1a5b5e55e2f1b7422c969e6194957`;
- atualização documental do contexto com o BeatPlan v1 integrado: `c50dc86fb430861b3e8f3f4f89f0f95df54330fd`;
- registro da regra permanente de armazenamento na raiz do projeto: `9908f3b6424a196464ed0557294a8efb0445774a`;
- reforço da segurança de worktrees na regra de armazenamento: `79fd5dae1db5450960d4cebe922ea26b71d8b6c5`;
- atualização documental do contexto com a regra de armazenamento e a auditoria de branches: `ed7e8f1e7146b3c754b4c13b2d8ba87ebf316a0e`;
- limpeza de 14 branches remotas autorizada pelo titular em 11/11/2026, posterior a `ed7e8f1` e registrada por esta atualização (exclusão de refs remotas, sem commit de código).
- registro documental da limpeza de branches em `3c44ae4408cdc1a03dad61d659e0dde0c502f829`;
- atualização da raiz oficial de armazenamento no `AGENTS.md` em `2c409676e58e4e118d865821b9a0cbdd93a22364`;
- integração do piloto técnico local R002 (vídeo sem áudio): merge `b7ed1d9bbf397f5e9f14bfddc62c67aa0d4f5cf9` com os três commits originais `2e663e3`, `040e290`, `b590769` preservados, mais o corretivo `0ac4bde8e5096ecdf4913a48ad453e066346b213`; detalhe na seção R002 — piloto técnico local de vídeo sem áudio;
- integração da execução local de TEMPORAL-02: merge `5376890974d4baf49b341297a9b7b0071a680dc6` com os três commits da branch `codex/temporal-02-execucao-local` (`f69fb08`, `91721a3`, `63d04d5`) preservados; detalhe na seção TEMPORAL-02 — Execução local integrada;
- integração da validação consolidada do pipeline criativo: merge `c461a3ca11e51ffe7082f7b11661632c0024def0` com os três commits da branch técnica `codex/content-pipeline-validation` (`3931993`, `3527a19`, `2fa8f04`) preservados; detalhe na seção Validação consolidada do pipeline criativo.
- integração do segundo consumidor real (Multitrack Hub) e dos casos de pipeline: fast-forward `f8ad1ea..36551ded3e34520a4e7da3c07ee413b19020956b` com os três commits da branch técnica `codex/multitrack-pipeline-consumer` (`54bfd6f`, `8d1b131`, `36551de`) preservados; detalhe na seção Segundo consumidor real — Multitrack Hub e casos de pipeline.
- integração do CreativeExecutionPackage v1: merge commit `dbf4d31c9f0882827f9fdf9bb79f18f00b3d092d` com os quatro commits da branch técnica `codex/creative-execution-package-v1` (`d43a9ec`, `b5bc7a0`, `df7fe90`, `d016218`) preservados, sem squash/rebase; detalhe na seção CreativeExecutionPackage v1 — pacote técnico de execução.
- integração do executor local simulado v1: merge commit `2824728300f20c89fe02717e29130895996ae85b` com os quatro commits da branch técnica `codex/simulated-execution-runner-v1` (`87b1a33`, `1e17a71`, `d8cb07f`, `842322f`) preservados, sem squash/rebase; detalhe na seção Executor local simulado v1.
- integração do primeiro adaptador de render local de prova (autorizada em 12/11/2026, **integrada na main** pelo merge commit `5be61b8cb3c1894088aae950a81469633447c45f`): branch `codex/local-render-adapter-v1`, a partir de `fbaf2b76943771bbc1a45c1768f39edbfcf67008`; detalhe na seção Adaptador de render local de prova — integrado na main.
- integração da redação portável da raiz de armazenamento (autorizada pelo titular em 12/11/2026): merge commit `a9118752c593b8bcd7b4636ad948055b77cb5687`, a partir da branch documental `codex/corrige-contexto-raiz-portavel` (HEAD `83eb4e5b8563aaf0c21cdb4fe5cc964c55110557`, commits `1d731cf` e `83eb4e5` preservados). A raiz oficial passa a ser o próprio checkout principal de cada estação (`<RAIZ>` = `git rev-parse --show-toplevel`), com `.workspace/` dentro dele; o invariante são os arquivos versionados alinhados por Git, não o caminho literal. Substância da regra de armazenamento inalterada; nenhum repositório realocado.
- integração do histórico da sessão de governança e do checklist de alinhamento entre estações (autorizada pelo titular em 12/11/2026): merge commit `8c209677d556678c7ed597c2ce6ead6374980422`, a partir da branch documental `codex/historico-sessao-2026-11-12` (HEAD `3e6cda0ee2ca705ba1755bab9ca55617b69059d7`, commits `1878c3f` e `3e6cda0` preservados). Versiona em `docs/historico/` o registro da sessão de governança de armazenamento/auditoria/limpeza de branches (11–12/11/2026) e o checklist de alinhamento entre estações, para que a continuidade viaje pelo Git e não dependa de `.workspace/` local. Registros de consulta: não autorizam produção, publicação, mídia, deploy nem nova fatia de TEMPORAL-02.
- integração do pipeline local de renderização a partir de casos (autorizada pelo titular em 12/11/2026): CLI `tools/render_pipeline.py`, prévia (`--plan-only`), render e2e com pacote canônico gerado em memória, promoção atômica com manifesto de entrega versionado (`delivery-manifest.json`), testes e CI dedicados; detalhe na seção Pipeline local de renderização a partir de casos — integrado na main.

O hash identifica o ponto consultado. Reconferir `git rev-parse origin/main`, as PRs abertas e o conteúdo integrado antes de trabalhar. As evidências de 162 testes de Workflow se referem a `f584210`. As de 626 testes da platform com BeatPlan se referem a `7d919fc` e `d5761b1`. A conclusão integral de TEMPORAL-02 depende das etapas descritas na seção Próximo passo.

## Núcleo reutilizável

### Integrado à main

- **ProjectManifest**: contrato, schema, validador, relatório, CLI e exemplos em `platform/src/project-contract.ts`, `platform/src/validate-project.ts`, `platform/schemas/project.schema.json` e `platform/examples/projects/`.
- **Composition v1**: composição declarativa por cenas e vínculo com o projeto em `platform/src/composition-contract.ts`, `platform/src/validate-composition.ts` e `platform/schemas/composition.schema.json`. Schema discriminado por tipo de cena e união discriminada no TypeScript.
- **Contratos e validadores existentes**: funções puras com relatório de códigos, erros e warnings (`platform/src/validation-report.ts`), regra lexical de caminhos compartilhada (`platform/src/relative-path.ts`) e corpus de paridade entre tipos, schemas e validadores em `platform/tests/contracts/`, com execução real dos schemas em motor draft-07.
- **Fronteira pública mínima da `platform` (TEMPORAL-02-01)**: pacote `marcasalao-marketing-platform` (`0.1.0`) com entrypoint público [`platform/src/composition-validation-api.ts`](../../platform/src/composition-validation-api.ts), exportando em runtime exclusivamente `validateComposition(composition, project)` e em tipos `Composition`, `ProjectManifest` e `CompositionValidationReport`, com declarações TypeScript habilitadas em [`platform/tsconfig.json`](../../platform/tsconfig.json), subpaths internos bloqueados pelo mapa `exports` em [`platform/package.json`](../../platform/package.json) e suíte dedicada em [`platform/tests/composition-validation-api.test.ts`](../../platform/tests/composition-validation-api.test.ts).
- **R001 — OutputProfiles e OutputPlan interno**: catálogo de perfis em [`platform/src/output-profiles/`](../../platform/src/output-profiles/), contrato [`output-plan-contract.ts`](../../platform/src/output-plan-contract.ts), schema, resolvedor e validadores integrados em `e86f3c9`, após reconciliação em `8e17785`. Os cinco [exemplos de OutputPlan](../../platform/examples/output-plans/) estão versionados em LF, com regra explícita em [`platform/.gitattributes`](../../platform/.gitattributes). OutputPlan continua interno: não amplia o entrypoint público de validação nem integra esses planos ao Temporal.
- **BeatPlan v1 interno**: contrato [`beat-plan-contract.ts`](../../platform/src/beat-plan-contract.ts), espelho draft-07 [`beat-plan.schema.json`](../../platform/schemas/beat-plan.schema.json), relatório aditivo `BeatPlanValidationReport` em [`validation-report.ts`](../../platform/src/validation-report.ts), validador [`validate-beat-plan.ts`](../../platform/src/validate-beat-plan.ts), CLI [`validate-beat-plan-cli.ts`](../../platform/src/validate-beat-plan-cli.ts) e [dois exemplos versionados](../../platform/examples/beat-plans/), integrados pelo merge `d5761b1f37d1a5b5e55e2f1b7422c969e6194957` a partir da reconciliação `7d919fc208ac4dfeebe5b0b65a959171e5f093f2`. Fatia **interna ao pacote**: não amplia o entrypoint público, não ganha subpath, não se combina com OutputPlan e não entra no Temporal. Detalhe na seção **BeatPlan v1 interno**.
- **Validação consolidada do pipeline criativo (`validateContentPipeline`)**: função pura em [`validate-content-pipeline.ts`](../../platform/src/validate-content-pipeline.ts), contrato [`content-pipeline-validation-contract.ts`](../../platform/src/content-pipeline-validation-contract.ts), CLI `content:validate-pipeline` em [`content-pipeline-validation-cli.ts`](../../platform/src/content-pipeline-validation-cli.ts), fixtures integradas em [`platform/examples/pipelines/`](../../platform/examples/pipelines/) e suíte de 34 testes dedicados (totalizando 651 testes na suíte da platform), integrados pelo merge `c461a3ca11e51ffe7082f7b11661632c0024def0`. Capacidade **estritamente interna e local**: não altera o entrypoint público, não ganha subpath, não entra no Temporal e não envolve renderização ou mídia.
- **Casos de pipeline e segundo consumidor real (Multitrack Hub)**: contrato interno [`content-pipeline-case-contract.ts`](../../platform/src/content-pipeline-case-contract.ts) (`ContentPipelineCaseManifest`), resolvedor seguro com confinamento estrito em [`resolve-content-pipeline-case.ts`](../../platform/src/resolve-content-pipeline-case.ts), validação de um caso e agregação multiprojeto em [`validate-content-pipeline-case.ts`](../../platform/src/validate-content-pipeline-case.ts), carga/descoberta em [`content-pipeline-case-loader.ts`](../../platform/src/content-pipeline-case-loader.ts), CLI `content:validate-cases` em [`content-pipeline-cases-cli.ts`](../../platform/src/content-pipeline-cases-cli.ts) e fixtures técnicas da Multitrack Hub em `platform/examples/`, integrados pelo fast-forward `36551ded3e34520a4e7da3c07ee413b19020956b` (suíte de 709 testes). Capacidade **estritamente interna e local**: não altera o entrypoint público, não ganha subpath, não entra no Temporal e não envolve renderização ou mídia. Detalhe na seção **Segundo consumidor real — Multitrack Hub e casos de pipeline**.
- **CreativeExecutionPackage v1 (pacote técnico de execução)**: contrato [`creative-execution-package-contract.ts`](../../platform/src/creative-execution-package-contract.ts), espelho draft-07 [`creative-execution-package.schema.json`](../../platform/schemas/creative-execution-package.schema.json), gerador puro [`create-creative-execution-package.ts`](../../platform/src/create-creative-execution-package.ts), validador puro [`validate-creative-execution-package.ts`](../../platform/src/validate-creative-execution-package.ts), serialização canônica [`serialize-creative-execution-package.ts`](../../platform/src/serialize-creative-execution-package.ts), aplicação multicase [`creative-execution-packages.ts`](../../platform/src/creative-execution-packages.ts), CLI transacional `content:build-execution-packages` em [`creative-execution-package-cli.ts`](../../platform/src/creative-execution-package-cli.ts) e [fixtures canônicas dos dois consumidores](../../platform/examples/execution-packages/), integrados pelo merge commit `dbf4d31c9f0882827f9fdf9bb79f18f00b3d092d` (suíte de 755 testes). O pacote é gerado **somente depois de um pipeline válido** e é uma especificação técnica imutável da execução futura: **não executa nada** — sem renderizador, Worker ou adaptador implementado, sem mídia, sem Temporal, sem alteração da API pública. Detalhe na seção **CreativeExecutionPackage v1 — pacote técnico de execução**.
- **Executor local simulado v1**: contratos [`simulated-execution-plan-contract.ts`](../../platform/src/simulated-execution-plan-contract.ts) e [`simulated-execution-report-contract.ts`](../../platform/src/simulated-execution-report-contract.ts), compilador puro [`create-simulated-execution-plan.ts`](../../platform/src/create-simulated-execution-plan.ts), validadores puros com espelhos draft-07, runner [`simulated-execution-runner.ts`](../../platform/src/simulated-execution-runner.ts) (estados, eventos, falha/cancelamento controlados, retomada segura), serialização canônica [`serialize-simulated-execution.ts`](../../platform/src/serialize-simulated-execution.ts), writer transacional [`simulated-execution-writer.ts`](../../platform/src/simulated-execution-writer.ts), multicase [`simulated-execution-multicase.ts`](../../platform/src/simulated-execution-multicase.ts), CLI `content:simulate-execution` em [`simulated-execution-cli.ts`](../../platform/src/simulated-execution-cli.ts) e [fixtures canônicas dos dois consumidores](../../platform/examples/simulated-executions/), integrados pelo merge commit `2824728300f20c89fe02717e29130895996ae85b` (suíte de 807 testes). Consome o `CreativeExecutionPackage` e produz **somente** plano, eventos, relatório, artefatos textuais simulados e hashes: o adaptador `simulation` é verificação de contrato, **não é renderer**, e nenhuma mídia é produzida. API pública inalterada. Detalhe na seção **Executor local simulado v1**.
- **CLIs existentes**: `content:validate-project`, `content:validate-composition`, `content:profiles`, `content:plan-output`, `content:validate-beat-plan`, `content:validate-pipeline`, `content:validate-cases`, `content:build-execution-packages` e `content:simulate-execution`, além de `build`, `typecheck`, `test`, `test:contracts` e `clean` em [platform/package.json](../../platform/package.json).
- **CI da plataforma**: [`.github/workflows/platform-validation.yml`](../../.github/workflows/platform-validation.yml), `Validar contratos da platform`, matriz Ubuntu e Windows × Node 22 e 24.
- **Runtime do núcleo**: Node `>=22 <25`, TypeScript compilado para JavaScript, motor de schema apenas em desenvolvimento.
- **Correção de contratos da PR #6**: integrada em 06/11/2026 pelo merge commit `0c97c2a`. A distinção entre "main anterior" e "correção pendente" que esta página mantinha foi retirada porque a main já contém o comportamento corrigido.
- **TEMPORAL-01**: piloto de orquestração em [`orchestration/temporal/`](../../orchestration/temporal/README.md), planejado em [`docs/planejamento/TEMPORAL-01-piloto-de-orquestracao.md`](../planejamento/TEMPORAL-01-piloto-de-orquestracao.md) e protegido por CI específico em [`.github/workflows/temporal-pilot-ci.yml`](../../.github/workflows/temporal-pilot-ci.yml).
- **PR #7 — contexto integrado**: [PR #7](https://github.com/Jonatasbottaro/marcasalao-marketing/pull/7) integrada à main pelo merge `fbd222d996527f6cf226051a8526f932accd7e5e` em 08/11/2026. `docs/contexto/` (`README.md`, `ESTADO-ATUAL.md`, `PROXIMOS-PASSOS.md` e `HANDOFF.md`) passou a pertencer à main e é fato integrado, não proposta em revisão. A branch `codex/atualiza-contexto-projeto` pode continuar existindo sem representar trabalho pendente; a branch remota não foi excluída.

### Em branch pública

Registrar aqui apenas o que continua fora da main, conforme o Git real:

- **PR #1 — integração de ai-memory**: [PR #1](https://github.com/Jonatasbottaro/marcasalao-marketing/pull/1), aberta. Fora do escopo técnico deste estado; não considerá-la integrada por associação.

Nada acima está integrado, por mais que o trabalho exista e tenha evidência própria.

O BeatPlan **saiu desta lista**: a reconciliação `7d919fc208ac4dfeebe5b0b65a959171e5f093f2` foi integrada pelo merge `d5761b1f37d1a5b5e55e2f1b7422c969e6194957` e está na main. A branch histórica `codex/core-beat-plan-v1` (checkpoint `bade62e3a720a853e6f3d18b52aa46bf544979a4`) foi **excluída do remoto** na limpeza de 11/11/2026, por autorização do titular, depois de confirmada como superseded; o checkpoint permanece como registro da origem do trabalho e como ref local de arquivo. `codex/reconcilia-beat-plan-v1` continua existindo e não representa trabalho pendente.

### Planejado ou documentado

- **R002**: integrado na main como piloto técnico local de vídeo sem áudio (merge `b7ed1d9`); detalhe na seção R002 — piloto técnico local de vídeo sem áudio. **R003**: sem documento próprio no repositório; a única ocorrência na main é o §14 do planejamento do TEMPORAL-01, que o declara não iniciado e não integrado.
- **VisualStyle, VisualAnchor, AssetManifest, AudioPlan, RenderPlan e adaptadores**: conceitos registrados em [`docs/decisoes/`](../decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md). Nenhum tem implementação na main. O núcleo já contém projeto, composição, fronteira pública de validação, R001 (catálogo, OutputPlan interno, resolvedor, validadores e CLIs) e BeatPlan v1 interno; isso não implementa esses conceitos nem um renderizador. Os dois primeiros passos da ordem recomendada pela decisão (Composition → BeatPlan) estão cumpridos como contratos declarativos e não autorizam os seguintes.
- **Qwen3.8**: família indicada para um futuro executor de texto, registrada no §15 do planejamento do TEMPORAL-01. Nada instalado, baixado, inferido ou acoplado.
- **Higgsfield**: nenhuma ocorrência em código ou documentação da main. É referência externa de conversa, não ferramenta adotada.
- **TEMPORAL-02-01**, **TEMPORAL-02-02**, **TEMPORAL-02-03**, **fatia Workflow de TEMPORAL-02**, **TEMPORAL-02** e **TEMPORAL-04**: estados próprios nas seções abaixo. As seções das fatias iniciais preservam o recorte e as evidências de cada commit; ausências registradas nesses marcos não substituem o estado atual da fatia Workflow.

## Limites do núcleo

- Composition é um contrato declarativo; não é execução do roteiro nem renderização.
- Renderer undecided é aceito e produz um warning; nenhum renderizador do novo núcleo foi implementado.
- Metadata approved é estado técnico. Não concede aprovação editorial, gravação ou publicação.
- Existência física de assets, licenças, inspeção final e prontidão para publicar não são comprovadas por `valid: true`.
- `scenes` vazio é aceito pela v1. Exigir uma cena mínima seria evolução de requisito.
- Os casos estruturais do corpus comparam os dois motores. Vínculos entre documentos, IDs de cena duplicados e overflow da soma permanecem verificações semânticas do core.
- A segunda configuração genérica do núcleo continua existindo para testar variações de idioma e formato; desde `36551de` a **Multitrack Hub é um segundo consumidor real do ProjectManifest nesse núcleo**, com fixtures técnicas próprias validadas pelo mesmo agregador, sem condicionais de marca. As fixtures são técnicas e fictícias: não são campanha aprovada nem reutilizam conteúdo publicado.

## BeatPlan v1 interno

- Status: **integrado tecnicamente na main** pelo merge `d5761b1f37d1a5b5e55e2f1b7422c969e6194957`, a partir da reconciliação `7d919fc208ac4dfeebe5b0b65a959171e5f093f2` da branch `codex/reconcilia-beat-plan-v1`.
- Natureza: tradução **temporal** declarativa de uma Composition válida em beats ordenados. Não é roteiro, não é Composition e não é renderização; não gera beats automaticamente, não contém comando de ferramenta, não contém provider de mídia e não cria arquivos.
- Autorização editorial: **não concedida**. A integração é técnica; `validationStatus: "validated"` e `metadata.status: "validated"` registram apenas revisão técnica.
- Referência: [README da platform](../../platform/README.md), seção *BeatPlan v1 (fatia interna)*.

### Componentes integrados

| Peça | Onde |
| --- | --- |
| BeatPlan v1 e contrato TypeScript | [`platform/src/beat-plan-contract.ts`](../../platform/src/beat-plan-contract.ts) — `BeatPlan`, `Beat`, enums neutros e limites documentados de texto e tags |
| Schema JSON draft-07 | [`platform/schemas/beat-plan.schema.json`](../../platform/schemas/beat-plan.schema.json), `additionalProperties: false`, executado por `ajv` |
| Relatório | `BeatPlanValidationReport` em [`platform/src/validation-report.ts`](../../platform/src/validation-report.ts), aditivo e com a mesma política de determinismo dos demais |
| Validador | [`validateBeatPlan(beatPlan, composition, project)`](../../platform/src/validate-beat-plan.ts) |
| Delegação de projeto | chama `validateProjectManifest`; manifesto inválido produz `BEAT_PLAN_PROJECT_MANIFEST_INVALID` |
| Delegação de composição | chama `validateComposition(composition, project)`; composição inválida produz `BEAT_PLAN_COMPOSITION_INVALID` |
| CLI | [`platform/src/validate-beat-plan-cli.ts`](../../platform/src/validate-beat-plan-cli.ts), script `content:validate-beat-plan` |
| Dois exemplos técnicos | [`marca-salao-pilot.beat-plan.json`](../../platform/examples/beat-plans/marca-salao-pilot.beat-plan.json) (4 beats, 10000 ms) e [`fixture-project-pilot.beat-plan.json`](../../platform/examples/beat-plans/fixture-project-pilot.beat-plan.json) (2 beats, 5000 ms, `en-US`) |
| Teste AJV | [`platform/tests/contracts/beat-plan-schema.test.ts`](../../platform/tests/contracts/beat-plan-schema.test.ts) |
| Teste do validador | [`platform/tests/beat-plan-validation.test.ts`](../../platform/tests/beat-plan-validation.test.ts) |
| Teste da CLI | [`platform/tests/beat-plan-cli-process.test.ts`](../../platform/tests/beat-plan-cli-process.test.ts) |
| Teste dos exemplos e LF | [`platform/tests/beat-plan-examples.test.ts`](../../platform/tests/beat-plan-examples.test.ts) |

A CLI recebe `--project`, `--composition` e `--beat-plan`, com `--json` opcional, sobre o mesmo `cli-input.ts` das CLIs de saída: exit `0` quando os três documentos são válidos entre si, `1` quando o JSON é legível mas o plano, o projeto ou a composição são inválidos (relatório no stdout) e `2` em erro de uso, arquivo ausente ou JSON malformado (stderr, stdout vazio).

### Regras principais

- a timeline começa em zero: o primeiro beat tem `startMs: 0`;
- beats contíguos, sem lacuna (`BEAT_PLAN_TIMELINE_GAP`) e sem sobreposição (`BEAT_PLAN_TIMELINE_OVERLAP`);
- o término do último beat é igual à duração total da Composition (`BEAT_PLAN_TIMELINE_END_MISMATCH` fora disso);
- todo `sceneId` precisa existir na Composition (`BEAT_PLAN_SCENE_NOT_FOUND`); cena e beat não têm relação um para um — um beat pode atravessar duas cenas e uma cena pode aparecer em mais de um beat;
- cena não referenciada gera **warning** (`BEAT_PLAN_SCENE_UNREFERENCED`), não erro;
- `order` é único, contínuo a partir de 1 e igual à posição no array; `projectId`, `compositionId` e `locale` devem igualar os documentos informados;
- núcleo determinístico: ordem de emissão fixa (`project` → `composition` → estrutura do plano → vínculo entre os três → relação com as cenas → timeline), sem timestamp, sem caminho absoluto, sem identificador aleatório e sem stack trace;
- sem I/O no validador, sem rede, sem relógio, sem aleatoriedade e sem mutação das entradas;
- o validador não corrige o que recebe: não gera beats, não reordena o array, não preenche lacuna, não corta beat e não altera a Composition;
- `narration` é somente `{ text }`: sem voz, provider, arquivo ou configuração de TTS; `motionIntent` e as transições descrevem intenção e não executam movimento nem animação;
- os warnings de comprimento e de tempo de leitura são heurísticas técnicas: não tornam o plano inválido, não substituem leitura humana cronometrada e não concedem aprovação editorial.

### Fronteiras públicas

- BeatPlan permanece **interno** à `platform`;
- nenhum export no entrypoint raiz: [`composition-validation-api.ts`](../../platform/src/composition-validation-api.ts) continua exportando apenas `validateComposition`;
- nenhum subpath público: o mapa `exports` de [`platform/package.json`](../../platform/package.json) expõe somente `"."`, e `marcasalao-marketing-platform/dist/src/beat-plan-contract.js` responde `ERR_PACKAGE_PATH_NOT_EXPORTED`;
- a API runtime continua somente `validateComposition(composition, project)`, Composition primeiro;
- os tipos públicos permanecem `Composition`, `ProjectManifest` e `CompositionValidationReport`;
- a CLI fica fora do tarball: `files` é `["dist/src", "!dist/src/*-cli.*"]`;
- módulos internos podem existir fisicamente no pacote, mas permanecem bloqueados pelo mapa `exports`.

### Evidências

- **626 testes aprovados**, zero falhas e zero skips, conforme registrado no [README da platform](../../platform/README.md) integrado em `d5761b1`;
- matriz de quatro ambientes: Ubuntu Node 22, Ubuntu Node 24, Windows Node 22 e Windows Node 24;
- CI da branch `codex/reconcilia-beat-plan-v1`: run [43034990448](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43034990448), `headSha: 7d919fc208ac4dfeebe5b0b65a959171e5f093f2`, quatro jobs `completed/success`;
- CI da main: run [43099977731](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43099977731), `headSha: d5761b1f37d1a5b5e55e2f1b7422c969e6194957`, quatro jobs `completed/success`;
- exemplos em **LF**, zero CR e exatamente uma newline final, conferidos nos bytes dos blobs em `d5761b1`, com a regra `examples/beat-plans/*.json text eol=lf` em [`platform/.gitattributes`](../../platform/.gitattributes);
- tarball com 38 entradas, sem CLI, fonte TypeScript, teste, exemplo ou schema: contagem informada no pedido desta atualização e **não reexecutada** aqui; a fronteira de empacotamento observável é a declarada em `files` e exercitada pelo teste de consumo externo em [`platform/tests/composition-validation-api.test.ts`](../../platform/tests/composition-validation-api.test.ts);
- gate da platform: [`.github/workflows/platform-validation.yml`](../../.github/workflows/platform-validation.yml), inalterado por esta fatia.

Os 626 testes pertencem a `7d919fc` e `d5761b1` e não devem ser atribuídos a um commit documental posterior. Nesta atualização os quatro jobs de cada run foram observados como `completed/success` pela API pública do GitHub; os logs por job exigem autenticação e não foram relidos, e nenhum teste foi executado localmente.

### Limites

- BeatPlan **não se combina com OutputPlan**: nenhuma peça do catálogo de saída ou do resolvedor lê um plano de beats;
- BeatPlan **não se integra ao Temporal**: nada em `orchestration/temporal/` foi tocado e não existe import de `@temporalio/*` na `platform`;
- nenhuma renderização, nenhum áudio ou TTS, nenhuma mídia, nenhum fornecedor e nenhum deploy;
- `VisualStyle`, `VisualAnchor`, `AssetManifest`, `AudioPlan` e `RenderPlan` continuam fatias futuras;
- estado técnico não concede autorização editorial, de gravação ou de publicação;
- a integração técnica não autoriza produção, mídia, publicação nem nova fatia de TEMPORAL-02, e não antecipa TEMPORAL-04, que continua reservado.

## Validação consolidada do pipeline criativo

- Status: **integrado tecnicamente na main** pelo merge `c461a3ca11e51ffe7082f7b11661632c0024def0`, a partir da branch técnica `codex/content-pipeline-validation` (commits `3931993`, `3527a19` e `2fa8f04`), por autorização explícita do titular em 12/11/2026.
- Natureza: agregador puro, estático e determinístico que unifica, em uma única execução local, a validação de todo o pipeline criativo: `ProjectManifest` → `Composition` → `OutputPlan` → compatibilidade `Composition × OutputPlan` → `BeatPlan`.
- Escopo: **estritamente local e interno à `platform`**. Não altera o entrypoint público (`composition-validation-api.ts`), não expõe subpaths públicos no `package.json`, não cria Activities ou Workflows no Temporal, e não envolve renderização, mídia, áudio ou deploy.

### Componentes integrados

| Peça | Onde |
| --- | --- |
| Contrato e união discriminada | [`platform/src/content-pipeline-validation-contract.ts`](../../platform/src/content-pipeline-validation-contract.ts) — `ContentPipelineValidationReport`, `ContentPipelineStageResult`, `ContentPipelineIssue` |
| Agregador determinístico | [`platform/src/validate-content-pipeline.ts`](../../platform/src/validate-content-pipeline.ts) — `validateContentPipeline(input)` com DAG de dependências |
| CLI interna | [`platform/src/content-pipeline-validation-cli.ts`](../../platform/src/content-pipeline-validation-cli.ts), script `content:validate-pipeline` |
| Fixtures integradas | [`marca-salao-pipeline-pilot.pipeline.json`](../../platform/examples/pipelines/marca-salao-pipeline-pilot.pipeline.json) e [`marca-salao-social-reel.beat-plan.json`](../../platform/examples/pipelines/marca-salao-social-reel.beat-plan.json) |
| Testes unitários do agregador | [`platform/tests/content-pipeline-validation.test.ts`](../../platform/tests/content-pipeline-validation.test.ts) (10 testes) |
| Testes de processo da CLI | [`platform/tests/content-pipeline-cli-process.test.ts`](../../platform/tests/content-pipeline-cli-process.test.ts) (12 testes) |
| Testes de exemplos e fixtures | [`platform/tests/content-pipeline-examples.test.ts`](../../platform/tests/content-pipeline-examples.test.ts) (2 testes) |
| Testes de build e portabilidade | [`platform/tests/build-portability.test.ts`](../../platform/tests/build-portability.test.ts) e [`platform/tests/beat-plan-validation.test.ts`](../../platform/tests/beat-plan-validation.test.ts) |

### Regras do DAG e agregação

- **Execução condicional (DAG)**:
  - Se `project` for inválido: `project: invalid`; os estágios dependentes (`composition`, `output-plan`, `output-compatibility`, `beat-plan`) ficam `status: "blocked"` com `blockedBy: "project"`.
  - Se `composition` for inválida (com `project` válido): `composition: invalid`; `output-plan` é avaliado de forma independente (depende apenas do projeto); `output-compatibility` e `beat-plan` ficam `blocked` com `blockedBy: "composition"`.
  - Se `output-plan` for inválido: `output-plan: invalid`; `output-compatibility` fica `blocked` com `blockedBy: "output-plan"`; `beat-plan` é executado normalmente (depende apenas de `project` e `composition`).
  - Se `output-compatibility` for inválida: `output-compatibility: invalid`; `beat-plan` é executado normalmente; relatório geral é `valid: false`.
- **Validade global**: `valid: true` se, e somente se, todos os 5 estágios forem `status: "valid"` e `errors.length === 0`.
- **Tratamento de warnings**: avisos legítimos (como ausência de contexto de regra ou cena não referenciada no BeatPlan) são preservados nos estágios e no consolidado, sem invalidação do pipeline e sem rebaixamento para erro.
- **Pureza e determinismo**: função 100% síncrona, estática, sem I/O, sem rede, sem relógio (`Date.now`), sem números pseudoaleatórios, com congelamento profundo (`Object.freeze`) do relatório e ordenação estável de erros e warnings.
- **CLI `content:validate-pipeline`**: consome `--project`, `--composition`, `--output-plan` e `--beat-plan`, com `--json` opcional:
  - `0`: pipeline válido;
  - `1`: pipeline inválido de domínio (relatório estruturado em stdout);
  - `2`: erro de uso, flag inválida, arquivo ausente ou JSON malformado (diagnóstico em stderr, stdout vazio).

### Evidências e CI

- **651 testes na suíte da `platform`** (649 aprovados, 2 skipped de symlinks do Windows, 0 falhas);
- **CI da branch `codex/content-pipeline-validation`**: run [43236412808](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43236412808), quatro jobs da matriz `completed/success`;
- **CI da main pós-merge**: run [43237054530](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43237054530), `headSha: c461a3ca11e51ffe7082f7b11661632c0024def0`, quatro jobs da matriz `completed/success` (Ubuntu e Windows × Node 22 e 24);
- Tarball com 42 entradas, sem CLIs, fontes TypeScript, testes, schemas ou exemplos;
- Exemplo integrado em LF no `.gitattributes` (`platform/examples/pipelines/*.json text eol=lf`).

### Limites

- A validação consolidada **não é utilizada no Temporal**: nenhum Workflow, Activity ou Worker consome o pipeline completo;
- Nenhuma renderização, geração de vídeo, imagem, áudio ou TTS;
- Nenhuma API pública nova ou alteração no entrypoint `composition-validation-api.ts`.

## Segundo consumidor real — Multitrack Hub e casos de pipeline

- Status: **integrado tecnicamente na main** pelo fast-forward `f8ad1ea..36551ded3e34520a4e7da3c07ee413b19020956b` (12/11/2026), a partir da branch técnica `codex/multitrack-pipeline-consumer` (commits `54bfd6f`, `8d1b131`, `36551de` preservados), por autorização explícita do titular em entrega multiprojeto.
- Natureza: prova de que o núcleo da `platform` funciona para **duas marcas independentes** — Marca Salão e Multitrack Hub — sobre o mesmo pipeline `ProjectManifest → Composition → OutputPlan → compatibilidade Composition × OutputPlan → BeatPlan → ContentPipelineValidationReport`, sem nenhuma condicional de marca no núcleo.
- Escopo: **estritamente local e interno à `platform`**. Não altera o entrypoint público (`composition-validation-api.ts` continua exportando apenas `validateComposition`), não expõe subpaths públicos, não cria Activities ou Workflows no Temporal e não envolve renderização, mídia, áudio, publicação ou deploy.

### Componentes integrados

| Peça | Onde |
| --- | --- |
| Contrato de caso | [`content-pipeline-case-contract.ts`](../../platform/src/content-pipeline-case-contract.ts) — `ContentPipelineCaseManifest` (`schemaVersion`, `id`, `project`, `composition`, `outputPlan`, `beatPlan`), validação estrutural pura e códigos estáveis `CASE_*` |
| Resolvedor seguro | [`resolve-content-pipeline-case.ts`](../../platform/src/resolve-content-pipeline-case.ts) — caminhos relativos ao diretório do manifesto, confinamento estrito na raiz declarada inclusive após `realpath` (symlink externo rejeitado), mensagens sem caminho absoluto da máquina |
| Validação de um caso e agregação | [`validate-content-pipeline-case.ts`](../../platform/src/validate-content-pipeline-case.ts) — `validateContentPipelineCase` (estados `valid`/`invalid`/`manifest-invalid`/`unreadable`) e `aggregateContentPipelineCases` (ordem preservada, `CASE_DUPLICATE_ID`, `CASES_EMPTY`) |
| Carga e descoberta | [`content-pipeline-case-loader.ts`](../../platform/src/content-pipeline-case-loader.ts) — varredura determinística de `*.pipeline.json` com symlinks ignorados, leitura via `cli-input.ts` |
| CLI multiprojeto | [`content-pipeline-cases-cli.ts`](../../platform/src/content-pipeline-cases-cli.ts), script `content:validate-cases` — modos `--case [--root]` e `--cases-root`, exit `0` válido / `1` domínio ou manifesto inválido / `2` uso ou ilegível |
| Fixtures da Multitrack Hub | [`multitrack-hub-social.project.json`](../../platform/examples/projects/multitrack-hub-social.project.json), [`multitrack-hub-social-reel.composition.json`](../../platform/examples/compositions/multitrack-hub-social-reel.composition.json) (15 s, 4 cenas), [`multitrack-hub-instagram-reels-video.output-plan.json`](../../platform/examples/output-plans/multitrack-hub-instagram-reels-video.output-plan.json) (gerado pelo stdout do resolvedor), [`multitrack-hub-social-reel.beat-plan.json`](../../platform/examples/pipelines/multitrack-hub-social-reel.beat-plan.json) (4 beats, 15000 ms) e [`multitrack-hub-pipeline-pilot.pipeline.json`](../../platform/examples/pipelines/multitrack-hub-pipeline-pilot.pipeline.json) |
| Testes novos | [`content-pipeline-case.test.ts`](../../platform/tests/content-pipeline-case.test.ts) (unitários), [`content-pipeline-cases-cli-process.test.ts`](../../platform/tests/content-pipeline-cases-cli-process.test.ts) (processo) e [`content-pipeline-multiconsumer-examples.test.ts`](../../platform/tests/content-pipeline-multiconsumer-examples.test.ts) (integração, LF, schemas e fronteira pública) |
| Testes estendidos | [`beat-plan-validation.test.ts`](../../platform/tests/beat-plan-validation.test.ts) — inventário fechado de `src/` com os cinco arquivos novos e varredura de independência de marca agora proibindo também `multitrack` e `multitrackhub.com.br` no núcleo; [`build-portability.test.ts`](../../platform/tests/build-portability.test.ts) — script `content:validate-cases` sobre build silencioso |

### Regras e segurança

- O contrato de caso rejeita caminho absoluto, URL, caractere de controle e referência sensível pela mesma função lexical compartilhada (`relative-path.ts`); o segmento `..` é permitido no contrato porque os manifestos referenciam diretórios irmãos, e o **confinamento** no resolvedor decide: todo documento precisa resolver estritamente dentro da raiz declarada, symlink externo é `CASE_RESOLUTION_ESCAPE`, documento ausente é `CASE_DOCUMENT_MISSING`.
- A agregação multiprojeto preserva a ordem dos casos, rejeita ids duplicados e nunca considera válida uma lista vazia; relatórios individuais entram por inteiro, sem remapeamento.
- As fixtures da Multitrack Hub são **técnicas e fictícias**, coerentes com a identidade documentada da marca (turquesa/preto/branco, multitracks/playbacks/rateios, site oficial `multitrackhub.com.br`); não reutilizam campanha publicada, não copiam ids de integração, tokens, credenciais ou dados pessoais dos arquivos da marca, e não concedem autorização editorial.
- Os fluxos de produção existentes da Multitrack Hub em `marcas/multitrackhub/` (ComfyUI, Postiz) permanecem intactos e identificados como integrações separadas; nada em `marcas/` foi alterado.

### Evidências e CI

- **709 testes na suíte da `platform`** (705 aprovados, 0 falhas, 4 skipped de symlink no Windows local — 2 preexistentes e 2 novos), medidos nesta estação em Node 24.19.0 com build limpo (`npm run clean && npm run typecheck && npm test`); baseline anterior à fatia: 651 testes (649 pass, 2 skipped);
- **Execução dos dois consumidores**: `content:validate-cases --cases-root examples --json` com exit 0; ambos os casos `valid`, 5 estágios completos, zero erros, mesmos códigos de warning (`COMPOSITION_RENDERER_UNDECIDED`, `OUTPUT_PLAN_CONTEXT_NOT_DECLARED`), identificadores de projeto/composição/beat plan distintos e mesmo perfil de saída `instagram-reels-video`; comparação estrutural exercitada pelo teste de integração;
- **CI da branch `codex/multitrack-pipeline-consumer`**: run [43247641430](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43247641430), `headSha: 36551ded3e34520a4e7da3c07ee413b19020956b`, quatro jobs da matriz `completed/success` (Ubuntu e Windows × Node 22 e 24), observados pela API pública do GitHub;
- **CI da main pós-integração**: run [43248224589](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43248224589), mesmo `headSha`, quatro jobs da matriz `completed/success`, observados pela API pública do GitHub; logs por job exigem autenticação e não foram relidos;
- **Empacotamento**: tarball `marcasalao-marketing-platform-0.1.0.tgz` com 50 entradas (42 anteriores + 8 dos quatro módulos novos sem CLI), sem CLIs, fontes TypeScript, testes, exemplos ou schemas; o teste de consumidor externo da suite dedicada continua aprovado;
- Todos os 18 arquivos alterados/adicionados commitados com blobs em **LF puro** (CR=0 conferido por `git show HEAD:<arquivo>`); `git diff --check` limpo; varredura de segredos, caminhos de máquina e ids externos nos arquivos novos: limpa.

### Limites

- Nenhuma mídia, arte final, vídeo, áudio, TTS, publicação, Postiz, campanha real, credencial, rede no código, scraping, fornecedor externo, banco de dados, Temporal, renderização ou deploy;
- Nenhuma API pública nova, subpath público ou regra de negócio específica de marca dentro do núcleo genérico;
- `valid: true` dos casos continua sendo validação estrutural técnica: não comprova existência física de assets, não aprova conteúdo e não autoriza publicação;
- A integração não altera os bloqueios de TEMPORAL-02, não antecipa TEMPORAL-04 e não autoriza combinação de planos no Temporal.

## CreativeExecutionPackage v1 — pacote técnico de execução

- Status: **integrado tecnicamente na main** pelo merge commit `dbf4d31c9f0882827f9fdf9bb79f18f00b3d092d` (12/11/2026, sem squash/rebase/force push), a partir da branch técnica `codex/creative-execution-package-v1` (HEAD `d016218a52acbff33c50542e5f17fadd0a3910f9`, quatro commits preservados: `d43a9ec`, `b5bc7a0`, `df7fe90`, `d016218`), por autorização explícita do titular em entrega de pacote técnico de execução v1.
- Natureza: especificação técnica **imutável e determinística** da execução futura, gerada **somente depois de um `ContentPipelineValidationReport` válido**. Responde "qual é o pacote que um executor futuro deverá consumir?", complementando a validação consolidada ("os documentos são válidos e compatíveis?").
- Escopo: **estritamente interno à `platform`**. Nenhum renderizador, Worker ou adaptador foi implementado; o pacote não executa nada: sem renderização, vídeo, imagem, áudio, FFmpeg, TTS, IA generativa, download de assets, rede, publicação, Postiz, fornecedor, Temporal, Activity, deploy, banco de dados ou fila.

### Componentes integrados

| Peça | Onde |
| --- | --- |
| Contrato v1 e packageId | [`creative-execution-package-contract.ts`](../../platform/src/creative-execution-package-contract.ts) — `CreativeExecutionPackage`, output, timeline, artefatos esperados, source references, códigos de falha e `deriveExecutionPackageId` |
| Espelho draft-07 | [`creative-execution-package.schema.json`](../../platform/schemas/creative-execution-package.schema.json), `additionalProperties: false`, executado por `ajv` nos testes |
| Gerador puro | [`create-creative-execution-package.ts`](../../platform/src/create-creative-execution-package.ts) — `createCreativeExecutionPackage(input, report)`, resultado discriminado, sem revalidação duplicada, sem I/O, sem mutação |
| Validador puro | [`validate-creative-execution-package.ts`](../../platform/src/validate-creative-execution-package.ts) — estrutura, IDs, output, timeline (ordem, `startMs`, `endMs`, contiguidade), duração consolidada, artefatos, unicidade, source, rederivação do packageId |
| Serialização canônica | [`serialize-creative-execution-package.ts`](../../platform/src/serialize-creative-execution-package.ts) — ordem explícita de campos, 2 espaços, LF, uma newline final, UTF-8 sem BOM, round trip estável |
| Aplicação multicase | [`creative-execution-packages.ts`](../../platform/src/creative-execution-packages.ts) — geração por caso e `createCreativeExecutionPackagesFromCases` com falha isolada, ordem estável e agregação pura |
| CLI transacional | [`creative-execution-package-cli.ts`](../../platform/src/creative-execution-package-cli.ts), script `content:build-execution-packages` — manifesto de casos, output-dir confinado, staging + verificação de bytes + backup + rename + reversão |
| Fixtures canônicas | [dois pacotes versionados](../../platform/examples/execution-packages/) (Marca Salão 14000 ms / 3 etapas; Multitrack Hub 15000 ms / 4 etapas), gerados pela própria CLI, regra `examples/execution-packages/*.json text eol=lf` |
| Testes | [`creative-execution-package.test.ts`](../../platform/tests/creative-execution-package.test.ts) (unitários), [`creative-execution-package-serialization.test.ts`](../../platform/tests/creative-execution-package-serialization.test.ts) (serialização/multicase), [`creative-execution-package-cli-process.test.ts`](../../platform/tests/creative-execution-package-cli-process.test.ts) (processo), [`creative-execution-package-e2e.test.ts`](../../platform/tests/creative-execution-package-e2e.test.ts) (ponta a ponta) |
| Barreiras estendidas | inventário fechado de `src/`/`schemas/` e varredura de independência de marca em [`beat-plan-validation.test.ts`](../../platform/tests/beat-plan-validation.test.ts); script novo em [`build-portability.test.ts`](../../platform/tests/build-portability.test.ts); subpath bloqueado no teste de consumidor externo em [`composition-validation-api.test.ts`](../../platform/tests/composition-validation-api.test.ts) |

### Regras principais

- **packageId determinístico**: forma legível `execution-<projectId>-<compositionId>-<outputPlanId>-<beatPlanId>` até 128 caracteres; acima do limite, canonicalização JSON com chaves em ordem fixa + SHA-256 (`node:crypto`, somente no contrato) com prefixo versionado `execution-v1-`. Sem timestamp, sem aleatoriedade, sem caminho, sem dependência da ordem de propriedades original. **É o packageId do pacote, nunca um Workflow ID, e não reutiliza o `contentHash` do Temporal.**
- **Códigos de falha da geração**: `PIPELINE_INVALID`, `PIPELINE_STAGE_BLOCKED`, `REQUIRED_ID_UNAVAILABLE`, `UNSUPPORTED_OUTPUT_CONFIGURATION`, `DURATION_MISMATCH`, `INTERNAL_INVARIANT_FAILED`; nenhum pacote parcial em falha.
- **Output**: somente dados já validados (`profileId`, `mediaKind: video`, geometria, `aspectRatio`, `fps`, `rendererAdapter`, `durationMs`); `plannedContainer` apenas quando o perfil declara; codec, bitrate e fornecedor não existem no contrato.
- **Timeline**: tradução direta dos beats validados, contígua, começando em zero e terminando em `output.durationMs`; textos preservados sem alteração; nenhum asset, prompt ou mídia inferido.
- **Artefatos esperados**: somente lógicos (`primary-output`, `captions`, `narration-script`, `execution-report`), com `id`, `kind`, `required`, `logicalName` sem caminho absoluto e `contentType` lógico; nenhum arquivo físico de mídia criado.
- **CLI**: exit `0` todos gerados · `1` caso(s) inválido(s) · `2` uso/path/manifesto/arquivo/JSON · `3` falha de geração/validação do pacote · `4` falha de escrita/promoção; stdout somente relatório, stderr sanitizado, zero stack trace e zero caminho absoluto; output-dir relativo, confinamento lexical + realpath, symlink externo rejeitado, diretório criado somente após todas as validações; transação preserva a saída anterior (medido por hashes SHA-256 idênticos após falha).

### Evidências e CI

- **755 testes na suíte da `platform`** (750 aprovados, 0 falhas, 5 skipped de symlink no Windows local — 2 preexistentes e 3 novos, todos condicionais ao suporte de symlink do SO), medidos nesta estação em Node 24.19.0; baseline anterior à fatia: 709 testes;
- **Gate em worktree limpa** (`.workspace/worktrees/execution-package-v1-gate`, detach no HEAD da branch): `npm ci --offline` → `clean` → `build` → `typecheck` → testes focados (45 testes, 44 pass, 1 skip de symlink) → suíte completa (755/750/0/5) → `npm pack --dry-run --json` → `git diff --check`, tudo com exit 0; demonstração explícita da CLI multicase e da falha transacional com hashes idênticos;
- **Ressalva de runtime local**: Node 22 não disponível nesta estação; os gates locais rodaram em Node 24.19.0 e o CI nos dois runtimes é o gate definitivo;
- **CI da branch `codex/creative-execution-package-v1`**: run [43266343222](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43266343222), `headSha: d016218a52acbff33c50542e5f17fadd0a3910f9`, quatro jobs `completed/success` (Ubuntu e Windows × Node 22 e 24), observados pela API pública do GitHub;
- **CI da main pós-merge**: run [43267163382](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43267163382), `headSha: dbf4d31c9f0882827f9fdf9bb79f18f00b3d092d`, quatro jobs `completed/success`, observados pela API pública do GitHub; logs TAP por job exigem autenticação e não foram relidos — a contagem de skips dentro dos jobs de CI não foi verificada individualmente;
- **Suíte pós-merge** executada no checkout principal com instalação offline: 755 testes, 750 pass, 0 fail, 5 skips;
- **Empacotamento**: `npm pack --dry-run --json` com 60 entradas (50 anteriores + 10 dos cinco módulos novos sem CLI), sem CLIs, fixtures, schemas, testes ou fontes TypeScript; nenhuma dependência de runtime nova;
- **API pública preservada**: entrypoint continua exportando somente `validateComposition`; subpath `dist/src/creative-execution-package-contract.js` responde `ERR_PACKAGE_PATH_NOT_EXPORTED` no teste de consumidor externo;
- Merge simulado com `git merge-tree --write-tree` antes da integração (sem conflitos); 19 arquivos alterados/adicionados, todos os blobs em LF puro (CR=0); `git diff --check` limpo.

### Limites

- O pacote **não executa renderização** e não constitui job executado; as fixtures não são campanha aprovada nem autorizam publicação;
- nenhum Worker, Activity ou Workflow Temporal consome o pacote; `packageId` não é Workflow ID;
- nenhuma mídia, fornecedor, publicação ou deploy; nenhum dado pessoal, credencial ou id externo privado nas fixtures;
- a integração não altera os bloqueios de TEMPORAL-02, não antecipa TEMPORAL-04 e não aprova o PRD;
- executor local simulado (consumir o pacote e produzir somente relatório de execução, sem renderizar) é a **próxima entrega recomendada**, não autorizada por esta integração.

## Executor local simulado v1

- Status: **integrado tecnicamente na main** pelo merge commit `2824728300f20c89fe02717e29130895996ae85b` (12/11/2026, sem squash/rebase/force push), a partir da branch técnica `codex/simulated-execution-runner-v1` (HEAD `842322ff51f7fadf3d2702770f4bfb6b48800f88`, quatro commits preservados: `87b1a33`, `1e17a71`, `d8cb07f`, `842322f`), por autorização explícita do titular em entrega de executor local simulado v1.
- Natureza: verificação executável da fronteira entre planejamento e execução. Consome o `CreativeExecutionPackage` v1 e produz **somente** plano de execução, eventos determinísticos, relatório final, artefatos lógicos textuais simulados e manifesto de hashes SHA-256. O adaptador `simulation` **não é renderer**; nenhuma mídia, renderização real, fornecedor, rede, publicação ou Temporal.
- Escopo: **estritamente interno à `platform`**. API pública inalterada (`validateComposition` apenas); subpaths do executor simulado respondem `ERR_PACKAGE_PATH_NOT_EXPORTED` (teste de consumidor externo estendido); CLI fora do tarball.

### Componentes integrados

| Peça | Onde |
| --- | --- |
| Contrato do plano e executionId | [`simulated-execution-plan-contract.ts`](../../platform/src/simulated-execution-plan-contract.ts) — `SimulatedExecutionPlan`, quatro operações neutras por beat (`prepare-scene`, `apply-text`, `apply-motion`, `finalize-scene`), `executionId` determinístico |
| Contrato do relatório | [`simulated-execution-report-contract.ts`](../../platform/src/simulated-execution-report-contract.ts) — 5 estados (`pending/running/completed/failed/cancelled`), 8 tipos de evento, códigos de retomada |
| Compilador puro | [`create-simulated-execution-plan.ts`](../../platform/src/create-simulated-execution-plan.ts) — valida o pacote antes de compilar; códigos `PACKAGE_INVALID`, `PACKAGE_VERSION_UNSUPPORTED`, `TIMELINE_INVALID`, `ARTIFACT_REFERENCE_INVALID`, `EXECUTION_ID_INVALID`, `INTERNAL_INVARIANT_FAILED` |
| Validadores e schemas | [`validate-simulated-execution-plan.ts`](../../platform/src/validate-simulated-execution-plan.ts), [`validate-simulated-execution-report.ts`](../../platform/src/validate-simulated-execution-report.ts), [`simulated-execution-plan.schema.json`](../../platform/schemas/simulated-execution-plan.schema.json), [`simulated-execution-report.schema.json`](../../platform/schemas/simulated-execution-report.schema.json) (draft-07, executados por ajv) |
| Runner | [`simulated-execution-runner.ts`](../../platform/src/simulated-execution-runner.ts) — execução sequencial sem sleep/timer/paralelismo/subprocesso; `failAtStepId` e `cancelAfterSequence` como opções explícitas de teste; artefatos textuais derivados somente do plano; retomada com prefixo de steps concluídos e `resumedFromStatus` |
| Serialização canônica | [`serialize-simulated-execution.ts`](../../platform/src/serialize-simulated-execution.ts) — ordem fixa, 2 espaços, LF, uma newline final, UTF-8 sem BOM, round trip estável |
| Writer transacional | [`simulated-execution-writer.ts`](../../platform/src/simulated-execution-writer.ts) — confinamento lexical + realpath (rejeita absoluto, escape, symlink externo, arquivo no lugar de diretório); staging → releitura → hashes → backup → rename → reversão; staging preservado até o diagnóstico |
| Multicase | [`simulated-execution-multicase.ts`](../../platform/src/simulated-execution-multicase.ts) — agregação pura, ordem estável, contagens por estado, diretório por `executionId`, zero regra por marca |
| CLI | [`simulated-execution-cli.ts`](../../platform/src/simulated-execution-cli.ts), script `content:simulate-execution` — `--package` ou `--packages-dir`, `--output-dir`, `--root`, `--fail-step`, `--cancel-after`, `--resume-from`, `--json`; exit 0/1/2/3/4/5 |
| Fixtures canônicas | [marca-salao](../../platform/examples/simulated-executions/marca-salao/) e [multitrackhub](../../platform/examples/simulated-executions/multitrackhub/) (8 arquivos cada: plano, relatório, eventos, hashes e 4 artefatos textuais), produzidas pelo próprio executor, regra `examples/simulated-executions/** text eol=lf` |
| Testes | [`simulated-execution-plan.test.ts`](../../platform/tests/simulated-execution-plan.test.ts), [`simulated-execution-runner.test.ts`](../../platform/tests/simulated-execution-runner.test.ts), [`simulated-execution-cli-process.test.ts`](../../platform/tests/simulated-execution-cli-process.test.ts), [`simulated-execution-e2e.test.ts`](../../platform/tests/simulated-execution-e2e.test.ts); inventário fechado e build-portability estendidos |

### Regras principais

- **executionId determinístico**: `simulation-<packageId>` até 128 caracteres; acima, canonicalização JSON + SHA-256 com prefixo `simulation-v1-`. Sem timestamp, random, caminho, máquina, usuário, PID ou variável de ambiente. Não é Workflow ID.
- **Eventos sem tempo real**: somente `sequence` inteira, `type`, `executionId` e referências opcionais; o tempo lógico vem da timeline do pacote. `cancelled` não é `failed`; `failed` exige `failureCode`; `completed` exige todos os steps.
- **Artefatos somente textuais/JSON**: `primary-output.manifest.json` (com `simulated: true`, descreve mas não cria mídia), `captions.txt`, `narration-script.txt`, `execution-summary.txt`, mais plano/relatório/eventos/hashes. `hashes.json` cobre todos os arquivos gerados exceto ele próprio. Sem data, hostname, usuário ou caminho absoluto.
- **Retomada segura**: somente com mesmos `executionId`/`packageId`, relatório anterior válido, status `failed`/`cancelled`, steps concluídos como prefixo e hashes conferidos; preserva steps/eventos anteriores sem duplicação; rejeita pacote/plano alterado, hash divergente, `completed` ou relatório inválido.
- **Transação**: zero promoção parcial; destino anterior intacto em falha (provado por hashes SHA-256 idênticos após pacote inválido e após falha de promoção).

### Evidências e CI

- **807 testes na suíte da `platform`** (800 aprovados, 0 falhas, 7 skipped de symlink no Windows local — 5 preexistentes e 2 novos, condicionais ao suporte de symlink do SO), medidos nesta estação em Node 24.19.0; baseline anterior à fatia: 755 testes;
- **Gate em worktree limpa** (`.workspace/worktrees/simulated-executor-v1-gate`, detach no HEAD da branch): `npm ci --offline` → `clean` → `build` → `typecheck` → testes focados (51 testes, 49 pass, 2 skips) → suíte completa (807/800/0/7) → `npm pack --dry-run --json` → `git diff --check`, tudo com exit 0;
- **Cenários obrigatórios executados na worktree de gate**: completed exit 0; failed exit 1; cancelled exit 1; resume exit 0 (`resumedFromStatus: failed`, 12 steps); multicase exit 0 (dois diretórios por `executionId`); prova transacional com pacote inválido exit 3 e hashes da saída anterior idênticos;
- **CI da branch `codex/simulated-execution-runner-v1`**: run [43275113976](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43275113976), `headSha: 842322ff51f7fadf3d2702770f4bfb6b48800f88`, quatro jobs `completed/success` (Ubuntu e Windows × Node 22 e 24), observados pela API pública do GitHub;
- **CI da main pós-merge**: run [43275961417](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43275961417), `headSha: 2824728300f20c89fe02717e29130895996ae85b`, quatro jobs `completed/success`, observados pela API pública do GitHub; logs TAP por job exigem autenticação e não foram relidos — a contagem de skips dentro dos jobs de CI não foi verificada individualmente;
- **Suíte pós-merge** no checkout principal: primeira execução teve 1 falha transitória no teste e2e de reexecução multicase (exit 4 de escrita/promoção, compatível com contenção de arquivo do Windows); a reexecução do arquivo e2e deu 6/6 e a suíte completa repetida deu **807/800/0/7**. A ocorrência não foi reproduzida e permanece registrada como transitória, sem correção "por garantia";
- **Empacotamento**: `npm pack --dry-run --json` com 78 entradas (60 anteriores + 18 dos nove módulos novos sem CLI), sem CLIs, fixtures, schemas, testes ou fontes TypeScript; nenhuma dependência de runtime nova;
- Merge simulado com `git merge-tree --write-tree` antes da integração (sem conflitos); 38 arquivos alterados/adicionados, todos os blobs em LF puro (CR=0); `git diff --check` limpo.

### Limites

- O executor **não renderiza** e não produz mídia de nenhum tipo; o adaptador `simulation` é verificação de contrato e não deve ser apresentado como renderer;
- nenhum Worker, Activity ou Workflow Temporal; `executionId` não é Workflow ID; nenhuma fila externa, banco de dados ou deploy;
- as fixtures não constituem job executado real, campanha aprovada ou autorização de publicação;
- a integração não altera os bloqueios de TEMPORAL-02, não antecipa TEMPORAL-04 e não aprova o PRD;
- **próximo passo recomendado, não autorizado por esta integração**: deliberar sobre autorização específica para um primeiro adaptador de renderização local (renderer de prova, sem fornecedor, publicação, serviço externo ou Temporal).

## Adaptador de render local de prova — integrado na main

- Status: **integrado na main** pelo merge commit `5be61b8cb3c1894088aae950a81469633447c45f` (12/11/2026, `--no-ff`, sem squash/rebase/force push), a partir da branch técnica `codex/local-render-adapter-v1` (HEAD `e52c88df927a9dddbac09fb175e2ebe4329becd6`, base `fbaf2b76943771bbc1a45c1768f39edbfcf67008`). Duas autorizações explícitas do titular em 12/11/2026: (1) implementar, testar, documentar e publicar a branch para acompanhar o CI; (2) corrigir promoção/relatório, acrescentar validação com FFmpeg no GitHub Actions e **integrar à main depois dos critérios de aceite cumpridos**. Nada publicado em redes; prova técnica com dados fictícios.
- Natureza: primeiro adaptador de renderização local do projeto, **prova técnica com dados fictícios**. Consome o `CreativeExecutionPackage` v1 versionado e uma associação explícita `beatId → path` de assets locais; produz MP4 H.264/yuv420p **sem nenhuma faixa de áudio**, SRT UTF-8, narração TXT e relatório JSON do render real com IDs, **caminhos relativos finais** dos artefatos promovidos, medições FFprobe e SHA-256/tamanhos calculados pelos bytes de staging. Não é campanha nem produção real da NS-001; nada publicado.
- Fronteira: a validação vive no núcleo puro da platform (`validateLocalRenderInput`, reutilizando `validateCreativeExecutionPackage`); a ponte `tools/render_bridge.mjs` apenas serializa o veredito; **toda execução de FFmpeg/FFprobe fica em `tools/render_local.py`**, fora do núcleo e fora do tarball. API pública inalterada (`validateComposition` apenas); executor `simulation` intacto; nenhuma dependência runtime nova.

### Componentes da branch

| Peça | Onde |
| --- | --- |
| Contrato da associação e recorte | [`local-render-input-contract.ts`](../../platform/src/local-render-input-contract.ts) — uma ligação por beat, eco do `packageId`, extensões aceitas, recorte 9:16@30 com dimensões pares, `none`/`slow-zoom`, entrada `none`/`cut`, saída `cut`/`fade` (fade só no último beat) |
| Validador puro da entrada | [`validate-local-render-input.ts`](../../platform/src/validate-local-render-input.ts) — códigos estáveis `PACKAGE_INVALID`, `ASSOCIATION_INVALID`, `PACKAGE_ID_MISMATCH`, `BEAT_ASSET_MISSING`, `BEAT_ASSET_DUPLICATE`, `UNKNOWN_BEAT_REFERENCE`, `ASSET_PATH_INVALID`, `ASSET_EXTENSION_UNSUPPORTED`, `RENDER_CONFIGURATION_UNSUPPORTED`; caminho apenas léxico, contenção real na camada de ferramentas |
| Ponte Node | [`render_bridge.mjs`](../../tools/render_bridge.mjs) — veredito JSON em stdout; exit 0/2/3 |
| Adaptador/CLI | [`render_local.py`](../../tools/render_local.py) — staging, inspeção prévia dos assets por FFprobe, render com timeout de 300 s, inspeção FFprobe do MP4, SRT/narração derivados do pacote, relatório com hashes, promoção com backup e restauração; exit 0/1/2/3 |
| Assets fictícios | [`make_proof_assets.py`](../../tools/make_proof_assets.py) — PNG determinístico por beat (stdlib), somente em `.workspace/` |
| Associações versionadas | [`marca-salao.assets.json`](../../tools/render/marca-salao.assets.json), [`multitrack-hub.assets.json`](../../tools/render/multitrack-hub.assets.json) |
| Testes | [`local-render-input.test.ts`](../../platform/tests/local-render-input.test.ts) (11 testes da ponte) e [`test_render_local.py`](../../tools/tests/test_render_local.py) (puros, ponte, render real e falhas com preservação por SHA-256); inventário fechado estendido |
| Documentação e manifesto | [`tools/render/README.md`](../../tools/render/README.md), seção nova no [README da platform](../../platform/README.md), [`02-reels-shorts/prova-render-local/manifest.json`](../../02-reels-shorts/prova-render-local/manifest.json) |

### Evidências locais (estação Windows, Node 24.19.0, FFmpeg 9.0.2 portátil)

- **Render real dos dois pacotes versionados**: Marca Salão **14,0 s** e Multitrack Hub **15,0 s**, ambos **1080×1920 a 30 fps**, H.264, yuv420p, **1 stream de vídeo e 0 de áudio** (FFprobe completo em `.workspace/logs/local-render-adapter-v1/ffprobe-*.json`);
- **Quadros de prova** conferidos visualmente: legenda queimada legível na faixa inferior, `slow-zoom` visível entre 4,5 s e 9,5 s, fade final escurecendo em 13,8 s, e legenda correta do segundo consumidor em 10 s (`frame-*.png` no mesmo diretório de logs);
- **SRT e narração** derivados exclusivamente dos textos e tempos do pacote; SRT validado pelo validador do R002 (sequência, timestamps, ordem, duração, UTF-8, LF, newline final única); artefatos textuais byte idênticos entre duas execuções;
- **Preservação da entrega anterior** provada por SHA-256 idêntico de todos os arquivos após: pacote inválido (exit 3), asset ausente (exit 1), asset fora da raiz/traversal (exit 3), asset ilegível (exit 1, inspeção prévia), falha real da ferramenta de vídeo com preset inexistente (exit 1) e falha de promoção simulada no segundo `os.replace` (exit 1, staging preservado);
- **Suíte da platform na worktree**: 818 testes, 811 aprovados, 0 falhas, 7 skipped de symlink no Windows (807 anteriores + 11 da ponte); typecheck e build limpos;
- **Testes Python preexistentes** (`test_build_video`, `test_srt_validate`, `test_r002_pilot`): 21 testes, OK — o piloto R002 e o exportador sem áudio continuam passando;
- **Testes Python do adaptador** (`tools/tests/test_render_local.py`): 22 testes, OK, 191,6 s, exit 0 — inclui renders reais dos dois pacotes, determinismo textual e os seis cenários de falha com preservação por SHA-256 (log `tools-tests-render.tap`);
- **Empacotamento**: `npm pack --dry-run --json` com 82 entradas (78 anteriores + 4 dos dois módulos novos), sem CLIs, sem `dist/tests`, sem schemas/fixtures, sem fontes TypeScript;
- **CI da branch `codex/local-render-adapter-v1`**: run [43300204713](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43300204713), `headSha: a012423a7ebe9e888ec4032e45d33c1acf965d42`, quatro jobs `completed/success` (Ubuntu e Windows × Node 22 e 24), observados pela API pública do GitHub. A matriz executa typecheck e a suíte da platform (818 testes medidos localmente no mesmo HEAD); logs TAP por job exigem autenticação e não foram relidos. **Separação explícita**: os testes Python com FFmpeg/FFprobe (22 do adaptador + 21 preexistentes) rodaram **somente nesta estação** e não fazem parte da matriz de CI; o que o CI observou foi exclusivamente o gate da platform;
- **Ferramenta portátil**: FFmpeg/FFprobe 9.0.2 (build essentials de gyan.dev) em `.workspace/tools/ffmpeg/`, origem e versão registradas em `.workspace/logs/local-render-adapter-v1/ferramenta-ffmpeg.txt`; acrescentada ao PATH apenas do processo;
- **Correções de robustez encontradas pelos testes**: (1) com `-loop 1`, um asset ilegível fazia a ferramenta de vídeo girar sem falhar — o adaptador agora inspeciona cada asset com FFprobe antes do render, **exigindo stream de vídeo decodificável com dimensões** (o exit code do ffprobe sozinho não prova legibilidade: foi medido exit 0 com streams vazios para lixo binário), e impõe timeout de 300 s ao subprocesso, convertido em falha controlada; (2) o teste de asset ilegível passou a usar cópia corrompida por teste, nunca o asset compartilhado, para que uma rodada interrompida não contamine as demais; (3) o zoom central usa `scale` com `eval=frame` + `crop` fixo (válido e medido em segundos), após `zoompan` se mostrar caro (~4–5 min por render) e uma tentativa intermediária de `crop` com `w/h` animado ser inválida; renders completos medidos em 19 s (Marca Salão) e 18 s (Multitrack Hub).

### Rodada 2 — correções de promoção/relatório, CI de render real e integração (12/11/2026)

- **Relatório que comprova a entrega**: caminhos relativos **finais** do MP4/SRT/TXT no JSON; hashes e tamanhos calculados pelos bytes preparados em staging; teste (`test_01b`) abre cada arquivo apontado pelo relatório e confere caminho, tamanho e SHA-256;
- **Staging exclusivo e validado antes de qualquer escrita**: sem `--staging`, pasta única `local-render-staging-*` em `.workspace/tmp/`; com `--staging`, exige pasta nova ou vazia e rejeita sobreposição com a raiz, com os arquivos de entrada e com a pasta de entrega (exit 2, nada escrito); limpeza recursiva restrita à pasta criada pelo próprio render;
- **Promoção exclusiva por destino**: lock `.local-render-promotion.lock` criado com `O_EXCL`; disputa recebe diagnóstico claro (exit 1) e o lock é removido ao final, inclusive em falha; falha de promoção restaura a entrega anterior; **se a restauração falhar, o backup permanece intacto para diagnóstico** (`test_08b`);
- **Timeouts com diagnóstico curto**: ponte Node 60 s, sondagens FFprobe 30 s, coleta de versões 15 s, render 300 s; `build_video.probe_media`/`validate_mp4` ganham timeout opcional sem alterar o comportamento histórico do piloto R002; timeouts e erro de inspeção cobertos por mocks, sem espera real;
- **CI de render real dedicado**: `.github/workflows/local-render-validation.yml` em **Ubuntu e Windows**, com `REQUIRE_RENDER=1` (ferramenta/ponte ausente vira erro, nunca skip); compila a ponte TypeScript, prepara Python e FFmpeg/FFprobe de builds verificáveis (ação oficial `FedericoCarboni/setup-ffmpeg`, builds BtbN), registra versões, roda a suíte Python e a prova dos dois pacotes com fixtures dentro da raiz, e inspeciona os vídeos promovidos com FFprobe; a matriz Node 22/24 da platform permanece em `platform-validation.yml`;
- **Gate em worktree limpa** (`.workspace/worktrees/local-render-adapter-v1-gate`, detach `e52c88d`): `npm ci`/`clean`/`build`/`typecheck` OK; suíte da platform 818/811/0/7; `npm pack --dry-run` 82 entradas sem CLIs/tests/schemas; suíte Python com `REQUIRE_RENDER=1`: 54 testes OK (329,5 s), render real obrigatório sem skips;
- **CI da branch (rodada 2)**: run [43309423710](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43309423710), `headSha: e52c88df927a9dddbac09fb175e2ebe4329becd6`, workflow de render real com jobs `ubuntu-latest` e `windows-latest` `completed/success`. O workflow `platform-validation` não disparou neste push (nenhum arquivo de `platform/` alterado na rodada 2); a árvore de `platform/` é idêntica à de `a012423`, cuja matriz verde está no run [43300204713](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43300204713);
- **CI da main (merge `5be61b8`)**: ambos os workflows `completed/success`, confirmados pela API pública oficial após o reset do limite de taxa: run [43312098951](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43312098951) (`Validar render local de prova`, jobs `ubuntu-latest` e `windows-latest` de render real) e run [43312098544](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43312098544) (`Validar contratos da platform`, quatro jobs Ubuntu/Windows × Node 22/24). Registro completo em `.workspace/logs/local-render-adapter-v1/ci-main-2.txt`;
- **Integração**: merge simulado com `git merge-tree --write-tree` (exit 0, árvore `ae26172`); merge commit `5be61b8cb3c1894088aae950a81469633447c45f` (`--no-ff`, 17 arquivos, +2321/−12); pós-merge no checkout principal: build/typecheck OK, suíte da platform 818/811/0/7 e suíte Python com `REQUIRE_RENDER=1` 54 testes OK (322,1 s); push `fbaf2b7..5be61b8`;
- **Falha comprovada e corrigida dentro da entrega**: a primeira execução da suíte da rodada 2 teve 1 falha em `test_08c` — o helper de comparação de hashes incluía o lock de promoção (arquivo de controle) durante a disputa; os 4 hashes da entrega estavam idênticos; o helper passou a excluir o lock e a suíte reexecutada deu 54/54 OK.

### Limites

- recorte inicial fechado (tabela do README do adaptador); fora dele, diagnóstico estável e nenhum render;
- nenhum áudio, TTS, fornecedor, rede, upload, publicação, Postiz, Temporal, banco ou deploy; nenhuma regra por marca no código;
- os MP4 e demais saídas existem apenas neste computador enquanto permanecerem em `.workspace/`; o manifesto versionado preserva hashes, bytes, medições e comando reproduzível;
- a integração na main foi concluída nesta rodada por autorização explícita do titular; os bloqueios de TEMPORAL-02/04, de produção real, de campanha real, de mídia real, de fornecedores e de publicação permanecem intactos.

## Pipeline local de renderização a partir de casos — integrado na main

- Status: **implementado, testado e integrado**, entregando a CLI unificada `tools/render_pipeline.py` para consumo direto de casos (`*.pipeline.json`).
- Fronteiras e arquitetura:
  - O planejamento e os contratos vivem estritamente na `platform`: a ponte Node (`tools/render_bridge.mjs`) carrega os 4 documentos referenciados pelo caso (`project`, `composition`, `outputPlan`, `beatPlan`), roda a validação consolidada (`validateContentPipelineCase`), gera o `CreativeExecutionPackage` canônico via `createCreativeExecutionPackageFromCase` e `serializeCreativeExecutionPackage`, e verifica o recorte via `checkLocalRenderConfiguration` e `validateLocalRenderInput`;
  - A geração do pacote a partir do caso reproduz exatamente os mesmos bytes canônicos das fixtures versionadas (`6776c0ab...` para Marca Salão e `0c263f0e...` para Multitrack Hub);
  - Todo o I/O de disco e a orquestração transacional ficam em `tools/render_pipeline.py`;
  - O render FFmpeg permanece no adaptador `tools/render_local.py`, gerando vídeo H.264/yuv420p sem faixa de áudio (`-an`, 0 streams de áudio), com legendas visíveis no vídeo, arquivo `.srt` separado com validação de timestamps e formatação estrita (LF, UTF-8), e roteiro de narração em TXT por cena e tempos.
- Duas formas de uso da CLI:
  1. `python tools/render_pipeline.py --case <caso.pipeline.json> --plan-only [--json]`: prévia em milissegundos sem FFmpeg, sem assets e sem criar arquivos, informando `caseId`, `packageId`, `perfil`, `geometria`, `fps`, `duracao`, beats necessários e conformidade com o recorte do adaptador (`supported`, `cabeNoRecorte`, `unsupportedReason`);
  2. `python tools/render_pipeline.py --case <caso.pipeline.json> --assets <associacao.json> --output-dir <destino> [--json]`: execução completa com geração em memória do pacote canônico, validação de assets, render FFmpeg, validação FFprobe, promoção transacional e emissão de manifesto de entrega versionado (`delivery-manifest.json`).
- Garantias transacionais e rastreabilidade:
  - Promoção atômica via staging exclusivo e lock `.local-render-promotion.lock`;
  - Rollback automático restaurando a entrega anterior em caso de falha de promoção;
  - Preservação de backup para diagnóstico caso a própria restauração falhe;
  - Rejeição de colisão de entrega caso a pasta de destino pertença a outro caso (`DeliveryCollisionError`);
  - Reexecução idempotente do mesmo caso atualizando deterministicamente;
  - Limpeza de staging temporário após a promoção;
  - Em `--json`, stdout é estritamente reservado ao JSON de saída e mensagens de progresso/diagnóstico vão para stderr.
- Suíte de testes: `tools/tests/test_render_pipeline.py` (18 testes) cobrindo prévia (--plan-only), ponte Node, renders reais dos dois casos, manifesto com recalculação e conferência de hashes de cada arquivo publicado, reexecução idempotente, colisão de casos, associação incompatível, configuração fora do recorte, asset ausente, falha de promoção, falha de restauração com backup preservado, disputa de lock e sobreposição de staging.
- CI: atualizado em `.github/workflows/local-render-validation.yml` para testar os dois modos (`--plan-only` e render completo com inspeção FFprobe e validação do `delivery-manifest.json`).

## TEMPORAL-01

- Status: **integrado e aprovado**.
- Pacote: `orchestration/temporal/`.
- Planejamento: `docs/planejamento/TEMPORAL-01-piloto-de-orquestracao.md`.
- Commit final da integração: `07e38f47df50fd6d8b264bc999fe4082be4b2bb6`, que fecha a sequência de delimitação documental, piloto, correções do gate e ressalvas testadas. A última linha desse histórico é a correção final de whitespace.
- Runtime: Node 22 (faixa `>=22 <25`), medido em Node 22.23.2 com npm 10.9.8.
- SDK: Temporal TypeScript 1.25.0, dependências exatas e isoladas do núcleo.
- Workflow: `contentPilotWorkflow`, com `workflowId` derivado como `temporal-pilot-<requestId>`.
- Activities: `validatePilotRequest`, `preparePilotExecution`, `finalizePilotExecution`.
- Task Queue: `marketing-temporal-pilot-v1`.
- Namespace local: `default`.
- Testes: **120** — 104 sem servidor e 16 na camada de Workflow, zero falhas e zero testes ignorados.
- CI: Ubuntu e Windows, Node 22, `fail-fast: false`, `permissions: contents: read`, teto de 15 minutos, disparado por paths do próprio pacote.
- Run final: [42494941537](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42494941537), no push desse commit para a main.
- Status do CI: **success** nos dois runners, cada um com `# tests 120 / # pass 120 / # fail 0 / # skipped 0` no log.
- Replay: validado com `Worker.runReplayHistory` sobre a história produzida na execução do teste.
- Colisão de Workflow ID: validada na suíte de integração, contra execução em andamento e contra execução já concluída, por `WorkflowIdReusePolicy.REJECT_DUPLICATE` e `WorkflowIdConflictPolicy.FAIL`, com código de falha próprio.
- Retries: limitados a três tentativas (`maximumAttempts: 3`), intervalo inicial de 1 s, coeficiente 2 e teto de 5 s.
- Timeouts: `startToCloseTimeout` de cinco segundos.
- Dependências: isoladas do núcleo — `platform/` mantém `dependencies` vazio e a busca por `@temporalio`, `Temporal`, `Workflow`, `Activity` ou `Task Queue` em `platform/src` e `platform/schemas` não retorna nada.
- Platform: intacta neste trabalho.
- Mídia: nenhuma gerada.
- Produção: nenhuma; o piloto aceita apenas localhost.
- Deploy: nenhum.

A correção final de whitespace removeu uma linha em branco excedente no fim de `orchestration/temporal/tests/client/pilot-start.test.ts`: um arquivo alterado, zero inserções funcionais e `git diff --check` limpo antes e depois do commit.

## Limitações de TEMPORAL-01

1. `TestWorkflowEnvironment.createTimeSkipping()` usa o Test Server de pular-tempo, documentado pelo próprio SDK como menos fiel ao servidor completo. A fidelidade completa fica em `pilot:local` sobre `createLocal()`.
2. O replay cobre a história produzida nesta implementação, não histórias de versões futuras do Workflow.
3. As Activities são puras por contrato e não exercitam efeito real de negócio; a idempotência é estrutural, não uma promessa de execução.
4. Shutdown controlado pelo `finally` foi comprovado: `pilot:local` e a suíte de integração derrubam worker e ambiente no próprio fluxo.
5. Importar os pontos de entrada não deixa handles ativos — os testes de processo veem o processo filho terminar sozinho.
6. **Não resolvido:** shutdown por `SIGINT` ou `Ctrl+C` de um Worker autônomo (`npm run pilot:worker`) no Windows não foi comprovado. Nenhuma tentativa nova foi feita e nenhum contorno específico para o Windows foi criado; esta limitação não deve ser marcada como resolvida.
7. O CI não depende de sinal manual: cada processo fecha pelo próprio controle, sem segredo, sem serviço persistente e sem artefato.

## Gate Elephant–Goldfish

- Gate **executado** fora do pacote do piloto, entre TEMPORAL-01 e TEMPORAL-02.
- Revisão independente concluída, com leitura adversarial (Elephant) e leitura de simplicidade e removibilidade (Goldfish).
- Contradições documentais corrigidas nas fontes do pacote antes da integração.
- Fonte única dos códigos não retryable: `NON_RETRYABLE_PILOT_CODES` em `orchestration/temporal/src/pilot-core/failures.ts`, consumida tanto pela classificação do resultado quanto pela `nonRetryableErrorTypes` da Retry Policy, com teste que impede redeclaração literal em qualquer um dos dois lados.
- Teste de colisão de `workflowId` incluído na suíte de integração.
- `pilotStartOptions` testado diretamente no cliente: chaves declaradas, determinismo sem relógio nem aleatoriedade, ausência de namespace e código próprio da colisão.
- CI específico do pacote criado e observado verde em Ubuntu e Windows.
- Nenhuma ressalva obrigatória restante.
- TEMPORAL-01 classificado como **aprovado**.

O §15 do planejamento do TEMPORAL-01 preserva a redação histórica "Não é implementada aqui e não tem aprovação simulada": ela descreve o recorte daquele commit e a proibição de simular aprovação, não uma pendência atual. O gate Elephant–Goldfish foi executado depois, entre TEMPORAL-01 e TEMPORAL-02, e o estado posterior correto está neste contexto, na seção Gate Elephant–Goldfish acima, com as ressalvas fechadas nos commits integrados. O documento de planejamento permanece como registro histórico e não foi alterado por esta correção.

## TEMPORAL-02-01

- Status: integrado e aprovado tecnicamente;
- commit técnico: `f202377fac721aff1d4143a2598f76c03062f0ac`;
- escopo: fronteira pública mínima da `platform`;
- pacote: `marcasalao-marketing-platform`;
- versão: `0.1.0`;
- entrypoint: `composition-validation-api` ([`platform/src/composition-validation-api.ts`](../../platform/src/composition-validation-api.ts));
- export runtime: `validateComposition`;
- tipos públicos: `Composition`, `ProjectManifest`, `CompositionValidationReport`;
- ordem: `validateComposition(composition, project)`;
- declarações TypeScript: habilitadas (`declaration: true` em [`platform/tsconfig.json`](../../platform/tsconfig.json));
- consumo externo: validado por tarball temporário (`npm pack` e consumidor externo isolado em [`platform/tests/composition-validation-api.test.ts`](../../platform/tests/composition-validation-api.test.ts));
- subpaths internos: bloqueados pelo mapa `exports` (somente `"."` exposto; subpaths lançam `ERR_PACKAGE_PATH_NOT_EXPORTED`);
- dependências de runtime: zero;
- testes: 315 aprovados, zero falhas, zero ignorados;
- CI: Ubuntu e Windows, Node 22 e 24;
- run da main: [42738388930](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42738388930);
- platform: sem dependência Temporal;
- Activity: não iniciada;
- Workflow: não iniciado;
- deploy: nenhum.

A remoção da linha em branco excedente no EOF de [`platform/tests/composition-validation-api.test.ts`](../../platform/tests/composition-validation-api.test.ts) foi realizada posteriormente apenas como higiene (remoção de um byte de newline extra no fim do arquivo), sem alteração funcional.

## TEMPORAL-02-02

- Status: integrado e aprovado tecnicamente;
- commit técnico: `29b40783320360350e59a13e39f49a60d2308507`;
- escopo: contrato de entrada versionado e preflight local do cliente antes do `start`;
- contrato: `CompositionValidationWorkflowInput`;
- schemaVersion: `1`;
- campos: `schemaVersion`, `requestId`, `project`, `composition`;
- requestId: entre 1 e 64 caracteres, padrão `^[a-z0-9][a-z0-9._-]{0,63}$`;
- envelope: fechado, com exatamente quatro chaves;
- resultado: união discriminada por `ok`;
- módulos adicionados em [`orchestration/temporal/src/composition-validation/`](../../orchestration/temporal/src/composition-validation/):
  - [`composition-validation-failures.ts`](../../orchestration/temporal/src/composition-validation/composition-validation-failures.ts): fonte única e imutável dos três códigos de rejeição de preflight (Via A): `TEMPORAL_COMPOSITION_INPUT_INVALID`, `TEMPORAL_COMPOSITION_INPUT_TOO_LARGE` e `TEMPORAL_COMPOSITION_SENSITIVE_INPUT`;
  - [`composition-validation-input.ts`](../../orchestration/temporal/src/composition-validation/composition-validation-input.ts): envelope fechado (`schemaVersion: 1`, `requestId`, `project`, `composition`) e limites em bytes UTF-8 (`64 KiB` / `65.536` bytes para `project`, `256 KiB` / `262.144` bytes para `composition` e `384 KiB` / `393.216` bytes para o envelope completo);
  - [`composition-validation-preflight.ts`](../../orchestration/temporal/src/composition-validation/composition-validation-preflight.ts): `preflightCompositionValidationInput(input)` e fronteira local `startAfterCompositionPreflight(input, start)`;
- códigos de preflight:
  - `TEMPORAL_COMPOSITION_INPUT_INVALID`;
  - `TEMPORAL_COMPOSITION_INPUT_TOO_LARGE`;
  - `TEMPORAL_COMPOSITION_SENSITIVE_INPUT`;
- medição: bytes UTF-8 da serialização JSON (`Buffer.byteLength(JSON.stringify(value), "utf8")`);
- limites:
  - project: 64 KiB (`65.536` bytes);
  - composition: 256 KiB (`262.144` bytes);
  - envelope: 384 KiB (`393.216` bytes);
- serialização: rejeita perda estrutural silenciosa (inspeção por descritores próprios sem executar getters, rejeita tipos não serializáveis, `BigInt` e `undefined` isolado);
- curso esperado: rejeição ocorre localmente antes do start e antes de qualquer persistência no servidor Temporal;
- callback: zero chamadas a `start` nas rejeições; exatamente uma chamada com a mesma referência validada no caso válido;
- ferramentas Temporal: nenhuma conexão e nenhum start real nesta fatia;
- dependências: nenhuma nova;
- platform: intacta;
- Activity (`validateCompositionActivity`): ausente;
- Workflow (`validateCompositionWorkflow`): ausente;
- deploy: nenhum.

### Política de segurança

- ciclos rejeitados por detecção de identidade de objetos visitados;
- BigInt rejeitado;
- valores não serializáveis rejeitados;
- chaves sensíveis conhecidas rejeitadas (`password`, `passwd`, `secret`, `token`, `accessToken`, `refreshToken`, `apiKey`, `privateKey`, `clientSecret`, `authorization`, `cookie`, `serviceAccount`, sem diferenciar caixa ou separadores);
- URLs com credenciais rejeitadas (presença de `username` ou `password`);
- caminhos absolutos rejeitados (padrões Windows com letra de unidade, UNC com barras duplas, caminhos raiz POSIX e esquemas `file://`);
- arquivos sensíveis conhecidos rejeitados (`.env`, `.env.local`, PEM, P12/PFX, chaves privadas e arquivos `service-account` JSON);
- falsos positivos editoriais cobertos (termos legítimos em descrições, textos e roteiros permanecem aceitos);
- mensagens fixas e sanitizadas por código e caminho lógico (`$`, `$.schemaVersion`, `$.requestId`, `$.project`, `$.composition`, etc.);
- nenhum valor rejeitado é ecoado na mensagem de erro ou relatório.

> A política é estreita e testável; não é um scanner universal de segredos.

### Testes e CI

- 17 testes novos de TEMPORAL-02-02 distribuídos em:
  - [`composition-validation-preflight.test.ts`](../../orchestration/temporal/tests/composition-validation/composition-validation-preflight.test.ts);
  - [`composition-validation-boundary.test.ts`](../../orchestration/temporal/tests/composition-validation/composition-validation-boundary.test.ts);
  - [`composition-validation-process.test.ts`](../../orchestration/temporal/tests/composition-validation/composition-validation-process.test.ts);
- suíte integrada do pacote: 137 testes aprovados (120 de TEMPORAL-01 + 17 de TEMPORAL-02-02), zero falhas e zero testes ignorados;
- CI do pacote (`temporal-pilot-ci.yml`): matriz Ubuntu e Windows, Node 22, aprovado sem falhas;
- runs verificados:
  - run da branch: [42747565768](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42747565768);
  - run da main: [42748899305](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42748899305);
- evidência de rede:
  > Nos processos de teste exercitados, nenhuma chamada a `net.Socket.connect` ocorreu.

### Limitação local do core-bridge no Windows

- os 17 testes novos de TEMPORAL-02-02 passaram localmente em Node 22;
- os testes locais que não carregam o addon nativo passaram (114/114 testes puros);
- após `npm ci`, o Windows local bloqueou o addon `@temporalio/core-bridge` por Code Integrity (`ERR_DLOPEN_FAILED`);
- a suíte integral (137/137 testes) foi comprovada no CI de Ubuntu e Windows;
- nenhuma política de segurança do Windows foi desativada;
- nenhum binário alternativo foi copiado;
- a limitação não afeta os módulos locais de TEMPORAL-02-02, que são funções puras em TypeScript compilado.

## TEMPORAL-02-03

- Status: integrado tecnicamente na main em `db84270ad3e51eecb0b562fcdf3a7e36941288ab` e ratificado pelo titular exclusivamente para a Activity e suas fronteiras públicas;
- commit técnico: `db84270ad3e51eecb0b562fcdf3a7e36941288ab`;
- componente implementado: `validateCompositionActivity` em [`orchestration/temporal/src/activities/composition-validation-activity.ts`](../../orchestration/temporal/src/activities/composition-validation-activity.ts);
- pacote público consumido: `marcasalao-marketing-platform` (versão `0.1.0`) adicionado via dependência local `file:../../platform` em [`orchestration/temporal/package.json`](../../orchestration/temporal/package.json);
- contrato dedicado da Activity: `CompositionValidationActivityInput` contendo exclusivamente `project: unknown` e `composition: unknown` (desacoplado de `requestId` e do envelope de Workflow);
- ordem estrita dos argumentos: chama diretamente `validateComposition(composition, project)` (Composition primeiro, ProjectManifest depois);
- retorno de domínio: entrega diretamente o `CompositionValidationReport` emitido pela `platform` sem remapeamento;
- resultado inválido de domínio: relatórios com `valid: false` são retornos normais de domínio e **não lançam exceção**;
- tratamento de falhas inesperadas: exceções anômalas na fronteira são capturadas e convertidas em `ApplicationFailure` não-retryable com código `TEMPORAL_COMPOSITION_ACTIVITY_FAILED`, mensagem fixa sanitizada (`Composition validation activity failed unexpectedly.`), sem vazamento de stack trace, sem erro original e sem payload bruto;
- pureza e isolamento: zero I/O de disco, zero rede, zero subprocessos, zero mutação dos inputs e zero duplicação de regras do validador;
- coordenação no CI: [temporal-pilot-ci.yml](../../.github/workflows/temporal-pilot-ci.yml) compila a `platform` antes da instalação e build do pacote Temporal, eliminando dependência de `dist/` residual e comprovado em checkout limpo;
- suíte de testes dedicada: 8 novos testes em [`composition-validation-activity.test.ts`](../../orchestration/temporal/tests/activities/composition-validation-activity.test.ts) (paridade exata sobre corpus de 11 casos, ordem de argumentos, imutabilidade com `deepFreeze`, idempotência, erro inesperado e pureza);
- testes totais do pacote Temporal: **145 testes aprovados** (120 de TEMPORAL-01 + 17 de TEMPORAL-02-02 + 8 de TEMPORAL-02-03), zero falhas, zero ignorados;
- CI do commit: aprovado com sucesso no GitHub Actions em `ubuntu-latest · Node 22` e `windows-latest · Node 22` (run [42902255503](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42902255503) na branch e run [42902338737](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42902338737) na main);
- ratificação e governança: TEMPORAL-02-03 foi implementado e integrado tecnicamente antes de a autorização explícita correspondente ser registrada no fluxo de continuidade. O registro de ratificação está em `8f94e0205b470b46da918d78f8136fafa9a2286a`; abrange estritamente a Activity homologada e não aprova automaticamente o PRD completo nem autoriza qualquer fatia posterior;
- recorte histórico: esta fatia não incluiu Workflow, Worker, cliente de validação, `workflow.start`, retries ou timeouts reais. A integração posterior do Workflow e as evidências de retry/timeout estão na seção seguinte; Worker de produção e cliente continuam ausentes;
- deploy: nenhum.

## TEMPORAL-02 — Fatia Workflow

### Estado técnico e governança

A fatia Workflow de TEMPORAL-02 está tecnicamente integrada e homologada no commit `f5842107a0f307b4cc208c15fc4509c6d7d31f72` e **ratificada pelo titular em 2026-11-11**. A decisão não aprova automaticamente o PRD completo, não autoriza nova implementação e não abre qualquer fatia posterior.

A ratificação abrange exclusivamente:

- `validateCompositionWorkflow`;
- `CompositionValidationWorkflowResult`;
- `classifyCompositionActivityFailure`;
- a chamada tipada de `validateCompositionActivity`;
- os resultados `valid`, `invalid` e `failed`;
- a Retry Policy canônica do PRD;
- a classificação sanitizada de falhas;
- os testes puros, os testes de fronteira e os testes com `TestWorkflowEnvironment`;
- o Worker efêmero usado exclusivamente nos testes;
- o CI verde em Ubuntu e Windows, Node 22.

Nada fora dessa lista foi ratificado em 11/11/2026. Em 12/11/2026 o titular autorizou especificamente a **execução local** (cliente, `workflow.start`, Workflow ID, políticas, colisão, Worker local, CLIs, replay formal e gate Elephant–Goldfish), integrada pelo merge `5376890`; essa autorização não abrange produção. Permanecem bloqueados, sem autorização: Worker de produção dedicado à composição, servidor Temporal remoto, namespace de produção, `contentHash`, combinação de OutputPlan ou BeatPlan com Temporal, TEMPORAL-04, mídia, fornecedores e deploy.

- Commit técnico: `f5842107a0f307b4cc208c15fc4509c6d7d31f72`, ancestral da main e anterior a `e86f3c9` e a `d5761b1`.
- Workflow: [`validateCompositionWorkflow`](../../orchestration/temporal/src/workflows/composition-validation-workflow.ts), recebendo `CompositionValidationWorkflowInput` e chamando a Activity já integrada `validateCompositionActivity` por `proxyActivities` tipado.
- Resultado: [`CompositionValidationWorkflowResult`](../../orchestration/temporal/src/workflows/composition-validation-result.ts), com `schemaVersion: 1`, `requestId`, `projectId`, `compositionId`, `status`, `validation`, `completedSteps` e `failureCode`.
- Falhas: [`classifyCompositionActivityFailure`](../../orchestration/temporal/src/workflows/composition-validation-failure-classifier.ts), com classificação por tipo e cadeia de causas, sem copiar a exceção bruta para o resultado.
- Fronteira: Workflow sem import de runtime da platform ou da Activity, sem I/O e sem duplicar o validador; a Activity continua chamando `validateComposition(composition, project)` pelo pacote público.
- Referências: [PRD de TEMPORAL-02](../planejamento/TEMPORAL-02-validacao-de-composition.md) e [README do Temporal](../../orchestration/temporal/README.md). O PRD completo permanece em revisão, sem aprovação global; TEMPORAL-02 não está concluído integralmente.

### Resultados implementados

| Status | `validation` e identificadores | `completedSteps` | `failureCode` |
| --- | --- | --- | --- |
| `valid` | Relatório presente e preservado; `projectId` e `compositionId` vêm de `report.projectId` e `report.compositionId` | `["validate-composition"]` | `null` |
| `invalid` | Resultado normal de domínio; relatório com `valid: false` preservado, inclusive identificadores vindos do relatório; sem exceção e sem retry | `["validate-composition"]` | `null` |
| `failed` | `validation: null`, `projectId: null` e `compositionId: null` | `[]` | Código técnico sanitizado |

Os construtores e os testes exercitam essas invariantes; a interface TypeScript tem campos anuláveis e não é uma união discriminada que impeça toda combinação inválida. Sanitização do resultado não apaga argumentos já persistidos na history nem garante sanitização de todos os logs do SDK. O preflight local permanece separado do Workflow e precisa anteceder qualquer futuro start da aplicação.

### Retry Policy e códigos técnicos

Política canônica do PRD implementada em `COMPOSITION_VALIDATION_ACTIVITY_OPTIONS`:

| Parâmetro | Valor |
| --- | --- |
| `startToCloseTimeout` | 5 segundos |
| `initialInterval` | 1 segundo |
| `backoffCoefficient` | 2 |
| `maximumInterval` | 2 segundos |
| `maximumAttempts` | 2 |
| `nonRetryableErrorTypes` | Somente `TEMPORAL_COMPOSITION_ACTIVITY_FAILED` |

- `TEMPORAL_COMPOSITION_ACTIVITY_FAILED`: a falha inesperada capturada pela Activity real é convertida em `ApplicationFailure` não retryable, com mensagem fixa, e termina em uma tentativa.
- `TEMPORAL_COMPOSITION_ACTIVITY_TRANSIENT_FAILURE`: falha transitória simulada pode recuperar na segunda tentativa; persistente, termina como `failed` após duas.
- `TEMPORAL_COMPOSITION_TIMEOUT`: `StartToCloseTimeout` pode gerar a segunda tentativa; persistente, termina como `failed` com esse código. Timeout não entra em `nonRetryableErrorTypes`, que não controla `TimeoutFailure`.
- O caso adicional de `Error` desconhecido injetado por uma Activity de teste percorreu duas tentativas antes da classificação sanitizada. Ele não equivale à exceção capturada e convertida pela Activity real.
- `invalid` é retorno de domínio, não falha técnica. Rejeição de preflight e conflito de start ficam fora da Retry Policy da Activity; a implementação da colisão continua pendente.

### Evidências vinculadas a f584210

- 17 testes novos: 6 de resultado/classificação/política, 4 de fronteira e 7 de Workflow.
- Suíte total do pacote Temporal: **162 testes aprovados**, zero falhas, zero ignorados; testes unitários: 112/112.
- Repetibilidade: nova execução dos testes de Workflow com **7/7**, zero falhas e zero ignorados.
- Homologação local anterior: checkout isolado no commit técnico, Windows com Node 22.23.4; preparação limpa, build, typecheck e gates aprovados. Nenhum desses comandos foi repetido nesta atualização documental.
- CI da branch técnica `codex/temporal-02-workflow-composition`: run [42950735743](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42950735743), `completed/success`, Ubuntu e Windows, Node 22, cada job com 162 aprovados, zero falhas e zero ignorados.
- CI da main no mesmo commit técnico: run [42953193438](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42953193438), `completed/success`, Ubuntu e Windows, Node 22, cada job com 162 aprovados, zero falhas e zero ignorados.
- Ambos os runs têm `headSha: f5842107a0f307b4cc208c15fc4509c6d7d31f72`. Esses resultados não são medições do HEAD posterior `e86f3c9` nem uma nova homologação do R001.

Os sete testes de Workflow exercitaram `valid` e `invalid` com Activity real, falha inesperada não retryable, recuperação e esgotamento de falha transitória, timeout persistente e erro desconhecido. O ambiente usou `TestWorkflowEnvironment.createTimeSkipping()`; comprova os casos exercitados, não fidelidade universal ao servidor completo nem replay formal.

### Limites no recorte da fatia Workflow (`f584210`) — registro histórico

Os itens abaixo descrevem o estado **no recorte da fatia Workflow em `f584210`**, antes da execução local. Foram superados pelo merge `5376890` (12/11/2026) no que toca a cliente, `workflow.start`, Workflow ID, políticas, colisão, Worker local, replay formal e gate Elephant–Goldfish, que passaram a existir em escopo estritamente local. O estado corrente está na seção **TEMPORAL-02 — Execução local integrada**; o gate Elephant–Goldfish de TEMPORAL-02 foi **executado e aprovado** para a execução local, conforme [`orchestration/temporal/docs/TEMPORAL-02-ELEPHANT-GOLDFISH.md`](../../orchestration/temporal/docs/TEMPORAL-02-ELEPHANT-GOLDFISH.md). Produção, servidor remoto, namespace de produção, `contentHash` e deploy continuam bloqueados. Preserva-se o recorte histórico abaixo sem alteração de conteúdo:

- Worker efêmero, cliente do ambiente de teste, chamadas a `workflow.start` e IDs de execução existem **somente nos testes desta fatia**.
- Worker de produção dedicado à composição: **ausente**.
- Cliente Temporal de validação e `workflow.start` no código da aplicação: **ausentes**.
- Workflow ID canônico da aplicação, `WorkflowIdReusePolicy`, `WorkflowIdConflictPolicy` e tratamento/testes de colisão de composição: **ausentes**; não confundir com os IDs efêmeros dos testes nem com o piloto TEMPORAL-01.
- `contentHash`: **fora de TEMPORAL-02**; sem canonicalização adicionada.
- Replay formal desta fatia: **não executado nem aprovado**; repetibilidade 7/7 não é replay.
- Elephant–Goldfish de TEMPORAL-02: **pendente**; o gate aprovado de TEMPORAL-01 não o substitui.
- Nenhum deploy e nenhuma implementação posterior autorizada.

## TEMPORAL-02 — Execução local integrada

- Status: **integrado na main** pelo merge `5376890974d4baf49b341297a9b7b0071a680dc6` (12/11/2026), a partir da branch `codex/temporal-02-execucao-local` (HEAD `63d04d5e4476e13a34f4636b19a08e642627b70b`, commits `f69fb08`, `91721a3`, `63d04d5`), por pedido explícito do titular de atualização completa do remoto. Escopo **estritamente local**: sem deploy, sem servidor remoto, sem namespace de produção, sem Worker persistente.
- Cadeia conectada: preflight → cliente (`startCompositionValidation` / `executeCompositionValidation`) → `workflow.start` → Worker local (`composition-validation-v1`) → `validateCompositionWorkflow` → `validateCompositionActivity` → `CompositionValidationWorkflowResult`.
- Workflow ID `composition-validation-<requestId>` (função pura no cliente); políticas `REJECT_DUPLICATE` + `FAIL`; colisão sanitizada `TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT` sem nova execução e fora da Retry Policy; Retry Policy ratificada intacta.
- CLIs: `composition:worker`, `composition:validate` (exit 0 valid / 1 invalid / 2 uso-preflight / 3 failed / 4 colisão / 5 conexão), `composition:validate:local` (createLocal com valid, invalid e colisão medidos), `composition:replay`.
- Replay formal: `Worker.runReplayHistory` com fixture versionado normalizado (`tests/replay/fixtures/composition-validation-valid.history.json`, 11 eventos, sha256 `5895a2508cfb647ca66489e21f1dc31247acc1e11b48ec5099aba4ccc812b089`), replay de história fresca e gate de sensibilidade (`[TMPRL1100]` com workflow divergente de mesmo nome).
- Evidência: 198 testes do pacote (zero falhas/skips) e 626 da platform em Node 22.23.2, repetidos em worktree limpa com instalação offline; CI `temporal-pilot-ci.yml` verde em Ubuntu e Windows Node 22 no SHA da branch (run 43160048966).
- Gate Elephant–Goldfish de TEMPORAL-02 executado e registrado em [`orchestration/temporal/docs/TEMPORAL-02-ELEPHANT-GOLDFISH.md`](../../orchestration/temporal/docs/TEMPORAL-02-ELEPHANT-GOLDFISH.md); nenhum bloqueador aberto; backlog cosmético de 3 itens.
- Limitações: `createTimeSkipping` menos fiel que `createLocal`; replay não prova compatibilidade com versões futuras; entrega de SIGINT/SIGTERM pelo SO no Windows não comprovada (shutdown programático e finally medidos); binário do servidor de teste em cache de processo, não versionado.
- Referências: [README do Temporal](../../orchestration/temporal/README.md), seções TEMPORAL-02 — Execução local completa e Replay formal.

## TEMPORAL-02

- **PRD de TEMPORAL-02 integrado e formalmente em revisão; TEMPORAL-02-01, TEMPORAL-02-02, TEMPORAL-02-03, a fatia Workflow e a execução local estão integrados tecnicamente. A fatia Workflow foi ratificada pelo titular em 2026-11-11, em escopo estrito; a execução local foi autorizada e integrada em 12/11/2026 (`5376890`); a aprovação do PRD, produção remota e qualquer fatia posterior continuam não autorizadas.**
- Arquivo: [`docs/planejamento/TEMPORAL-02-validacao-de-composition.md`](../planejamento/TEMPORAL-02-validacao-de-composition.md), integrado à main em `33b46ce54649fc60340c2e85b15d0b39ad112cff`.
- Status do documento: **PRD em revisão**.
- Aprovação do PRD: **não concedida**.
- Implementação global de TEMPORAL-02: **não autorizada e não concluída**.
- Fatias executadas e integradas na main:
  - **TEMPORAL-02-01**: fronteira pública mínima da `platform` (`marcasalao-marketing-platform@0.1.0`, entrypoint `composition-validation-api`), integrada em `f202377fac721aff1d4143a2598f76c03062f0ac` (fechamento documental em `f1da1f9d0b62bf94be44779b8db4e00610dd7ee5`);
  - **TEMPORAL-02-02**: contrato de entrada versionado e preflight local anterior ao `start` em [`orchestration/temporal/src/composition-validation/`](../../orchestration/temporal/src/composition-validation/), integrado em `29b40783320360350e59a13e39f49a60d2308507`;
  - **TEMPORAL-02-03**: Activity real `validateCompositionActivity` em [`orchestration/temporal/src/activities/composition-validation-activity.ts`](../../orchestration/temporal/src/activities/composition-validation-activity.ts), integrada em `db84270ad3e51eecb0b562fcdf3a7e36941288ab`, com ratificação registrada em `8f94e02`;
  - **Fatia Workflow**: `validateCompositionWorkflow`, `CompositionValidationWorkflowResult`, classificador de falhas e Retry Policy integrados e homologados tecnicamente em `f584210`, com ratificação do titular registrada em 2026-11-11 restrita ao escopo dessa fatia.
- **Etapas posteriores**: Worker de produção, cliente de validação, start da aplicação, Workflow ID e colisão, replay formal e gate Elephant–Goldfish **não autorizados e bloqueados**.
- Temporal executado para esta fatia: **somente em testes com ambiente efêmero**, conforme evidências de `f584210`; não há execução de produção.
- Dependências externas novas da fatia Workflow: **nenhuma**; mantém o SDK isolado e a dependência local `marcasalao-marketing-platform` já integrada. Deploy: **nenhum**.

Integrar o PRD **não** é aprová-lo. A ratificação da Activity (TEMPORAL-02-03) e a ratificação da fatia Workflow são registros distintos, cada um restrito ao próprio escopo, e nenhuma delas aprova o PRD completo nem autoriza etapas posteriores. As descrições de implementação não iniciada no PRD preservam o recorte histórico de sua redação; o documento não foi alterado nesta atualização e sua aprovação global continua não concedida.

### Passo real implementado

- Operação: `validate-composition` — **um único** passo.
- Objetivo: validar uma Composition v1 contra um ProjectManifest, incluindo a validação do próprio projeto pelo núcleo.
- Função do núcleo: `validateComposition(composition, project)`, reexportada por `marcasalao-marketing-platform` (`0.1.0`, entrypoint [`platform/src/composition-validation-api.ts`](../../platform/src/composition-validation-api.ts)). A ordem permanece Composition primeiro, ProjectManifest depois.
- Componentes implementados: Activity `validateCompositionActivity`, Workflow `validateCompositionWorkflow` e resultado `CompositionValidationWorkflowResult`.
- Cliente de aplicação e Worker de produção de composição continuam ausentes; sua futura implementação depende de autorização específica.

### Quatro vias: desenho e implementação atual

- **A. Rejeição no preflight** — implementada localmente antes do start; sem Workflow e sem resultado de execução. Ainda não há cliente de aplicação conectando esse preflight a um start real.
- **B. Conflito no start** — planejado, não implementado para composição: `workflowId` já existente, sem nova execução, classificado pelo futuro cliente e sem `CompositionValidationWorkflowResult`.
- **C. Resultado do domínio** — implementado: `valid` ou `invalid`; relatório presente; `failureCode` nulo; `completedSteps` com `validate-composition`.
- **D. Falha da execução** — implementada: `failed`; relatório e identificadores nulos; `failureCode` sanitizado; `completedSteps` vazio.

O [PRD](../planejamento/TEMPORAL-02-validacao-de-composition.md) registra o desenho das quatro vias; o código e os testes do commit técnico sustentam as partes implementadas. A Retry Policy e os testes reais de retries e timeout estão descritos na seção **TEMPORAL-02 — Fatia Workflow**; não são mais apenas planejamento. Isso não comprova replay, colisão ou prontidão de produção.

### Gates obrigatórios de TEMPORAL-02

- **Gate de fronteira pública (`TEMPORAL-02-01`)** — **concluído e integrado** na main em `f202377fac721aff1d4143a2598f76c03062f0ac`: entrypoint público mínimo da `platform` (`composition-validation-api`), pacote compilado consumível (`marcasalao-marketing-platform@0.1.0`), tipos públicos (`Composition`, `ProjectManifest`, `CompositionValidationReport`), subpaths internos bloqueados por `exports`, zero dependências de runtime, 315 testes aprovados e CI verde em Ubuntu e Windows, Node 22 e 24 (run [42738388930](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42738388930)).
- **Fatia de contrato e preflight local (`TEMPORAL-02-02`)** — **concluída e integrada** na main em `29b40783320360350e59a13e39f49a60d2308507`: envelope fechado (`schemaVersion: 1`, `requestId`, `project`, `composition`), três códigos da Via A, inspeção JSON sem perda, política estreita contra conteúdo sensível, limites UTF-8 de 64/256/384 KiB, prova de zero invocação do callback de `start` nas rejeições, 17 novos testes locais verdes e suíte integral de 137 testes verde no CI Ubuntu e Windows, Node 22 (run [42748899305](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42748899305)).
- **Fatia de Activity real (`TEMPORAL-02-03`)** — **concluída, integrada e ratificada** na main em `db84270ad3e51eecb0b562fcdf3a7e36941288ab`: Activity pura `validateCompositionActivity`, consumo da dependência pública `marcasalao-marketing-platform`, contrato dedicado `CompositionValidationActivityInput`, chamada exata `validateComposition(composition, project)`, retorno de relatório sem remapeamento, `valid: false` normal, conversão sanitizada para `TEMPORAL_COMPOSITION_ACTIVITY_FAILED`, 8 novos testes dedicados, 145 testes integrais do pacote Temporal e CI verde em Ubuntu e Windows, Node 22 (run [42902338737](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42902338737)).
- **Fatia Workflow** — **integrada e homologada tecnicamente** em `f584210` e **ratificada pelo titular em 2026-11-11** no escopo dessa fatia: 17 testes novos, suíte de 162 aprovados e repetibilidade 7/7; CI Ubuntu e Windows, Node 22, no mesmo SHA. A ratificação não aprova o PRD completo nem autoriza a próxima fatia.
- **Replay formal de TEMPORAL-02** — **não executado nem aprovado**; os testes e sua repetição não o substituem.
- **Gate Elephant–Goldfish de TEMPORAL-02** — **não executado**; permanece pendente e obrigatório antes da integração final completa de TEMPORAL-02, distinta das fatias já integradas. Sua execução depende de autorização específica. Revisões mínimas: fronteira pública, ordem dos argumentos, paridade, history, payload, quatro vias, `invalid` versus `failed`, retries, replay, isolamento do núcleo e ausência de mídia e fornecedores.

O gate Elephant–Goldfish registrado na seção própria acima foi o de **TEMPORAL-01** e não cobre TEMPORAL-02.

### Limites preservados

- Sem Qwen, sem Higgsfield, sem mídia, sem prévia, sem exportação e sem combinar OutputPlan e BeatPlan.
- TEMPORAL-02 **não antecipa TEMPORAL-04**, que continua reservado.

## TEMPORAL-04

- Status: **reservado**.
- Finalidade: verificação conjunta de OutputPlan, BeatPlan, prévia e exportação.
- Não iniciado, não antecipado em TEMPORAL-02 e não tratado como integrado.

## R001 e BeatPlan: classificação pelo Git real

| Trabalho | Branch | Checkpoint | Evidência consultada | Classificação |
| --- | --- | --- | --- | --- |
| R001 | `codex/reconcilia-r001-formatos-sociais` | `8e17785a5634167f8abdaebacb8388276b909cab` | `merge-base --is-ancestor` contra `origin/main` com saída 0 em 11/11/2026; merge `e86f3c9ef939ac7536ecf39a65cf4f6ee97e4b52` | **integrado**: OutputProfiles, OutputPlan interno, CLIs e cinco exemplos de planos em LF |
| BeatPlan | `codex/reconcilia-beat-plan-v1` (origem histórica: `codex/core-beat-plan-v1`) | reconciliação `7d919fc208ac4dfeebe5b0b65a959171e5f093f2`; merge `d5761b1f37d1a5b5e55e2f1b7422c969e6194957` | `merge-base --is-ancestor` de `d5761b1` e de `7d919fc` contra `origin/main`, ambos com saída 0 em 11/11/2026; cinco commits temáticos preservados; CI da main run [43099977731](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43099977731), quatro jobs completed/success | **integrado**: BeatPlan v1 interno, contrato, schema, relatório, validador, CLI, dois exemplos e testes; API pública preservada |

O antigo checkpoint `55aeecccfa38da06dfada875e75d81b265626abc` da branch `codex/catalogo-formatos-sociais` permanece registro histórico, não a referência da integração atual do R001. Essa branch foi **excluída do remoto** na limpeza de 11/11/2026, por autorização do titular, depois de confirmada como superseded. A reconciliação integrada do R001 inclui catálogo, contrato interno, schema, resolvedor, validadores, CLIs `content:profiles` e `content:plan-output` e exemplos LF; não amplia o export público da platform.

O BeatPlan foi reconciliado sobre a main que já contém R001 e integrado pelo merge `d5761b1`, preservando os cinco commits temáticos da branch: `9c872a6` (contrato, schema e relatório), `d46ea5a` (validador vinculado a Composition e ProjectManifest), `4230eba` (CLI compartilhada), `559d22c` (exemplos e portabilidade) e `7d919fc` (README da platform). O checkpoint histórico `bade62e3a720a853e6f3d18b52aa46bf544979a4` de `codex/core-beat-plan-v1` e o run [42321831284](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42321831284) permanecem como registro da origem do trabalho, não como estado atual; a branch `codex/core-beat-plan-v1` foi **excluída do remoto** na limpeza de 11/11/2026, enquanto `codex/reconcilia-beat-plan-v1` continua existindo. A integração não amplia o export público da platform, não combina BeatPlan com OutputPlan e não o leva ao Temporal. Nenhum teste do R001 ou do BeatPlan foi executado nesta atualização documental. A presença do R001 e do BeatPlan na main não autoriza seu consumo por TEMPORAL-02.

## Auditoria das branches não integradas

Auditoria de consulta realizada em 11/11/2026 sobre as 15 branches remotas então não contidas em `origin/main`, sem mesclar, commitar ou excluir nada. **Registro histórico:** 14 dessas 15 branches foram excluídas do remoto na limpeza posterior, autorizada pelo titular (ver a seção Limpeza de branches remotas); apenas `ai-memory-integration` permanece. A classificação abaixo descreve o que foi apurado na auditoria e continua válida como justificativa da limpeza. Método: `git cherry` (equivalência de patch-id), `git merge-tree --write-tree` (dry-run do efeito líquido e dos conflitos, sem alterar refs nem working tree), comparação de conjuntos com `git ls-tree` (arquivos realmente ausentes da main) e comparação de conteúdo por arquivo-chave.

| Classificação | Qtd | Branches |
| --- | --- | --- |
| Superseded — conteúdo já na main | 13 | `alinha-regra-notificacoes-marketing`, `core-composition-v1`, `core-project-manifest`, `documenta-pipeline-criativo-modular`, `documenta-plataforma-modular-marketing`, `ns-001-consolida-validacao-executada`, `ns-001-hooks`, `ns-001-roteiro-001`, `ns-001-validacao-agenda`, `temporal-01-piloto-orquestracao`, `catalogo-formatos-sociais`, `core-beat-plan-v1`, `historico-apresentacoes-salao02` |
| Obsoleta e em contradição com a regra permanente | 1 | `registra-areas-de-trabalho-isoladas` |
| Trabalho real pendente, fora do escopo | 1 | `ai-memory-integration` (PR #1) |

Fatos determinantes:

- Quatro branches (`alinha-regra-notificacoes-marketing`, `documenta-pipeline-criativo-modular`, `documenta-plataforma-modular-marketing`, `ns-001-consolida-validacao-executada`) produzem merge **neutro**: o tree resultante é idêntico ao tree da main, ou seja, mesclar não alteraria arquivo algum. As demais superseded conflitam apenas porque a main tem versões mais novas dos mesmos arquivos.
- `catalogo-formatos-sociais` é o trabalho original do R001, superseded pela reconciliação `8e17785`. Todos os 25 arquivos que toca existem na main, com conteúdo idêntico nos arquivos-chave (`output-profiles/catalog.ts` 279 linhas nos dois, `resolve-output-profile.ts` 329, `R001-changelog.md` 28). Os patch-ids diferem porque a reconciliação reescreveu ajustes, não porque falte conteúdo.
- `core-beat-plan-v1` é o trabalho original do BeatPlan, superseded pela reconciliação `7d919fc`. Mesclar **regrediria** o projeto: a main tem a CLI refactorada (100 vs 145 linhas), os testes de validação refactorados (1050 vs 1187) e dois arquivos de teste que só existem na main (`beat-plan-examples.test.ts` e `contracts/beat-plan-schema.test.ts`).
- `historico-apresentacoes-salao02` traz o briefing NS-001 com 237 linhas; a main tem 327 linhas, versão editorial 0.3. Mesclar regrediria o editorial.
- `registra-areas-de-trabalho-isoladas` (`636e5c434c6bc0c990b4451946c56853b309a8b1`) tinha merge limpo, mas adicionaria `.worktrees/` ao `.gitignore` versionado e tornaria essa convenção normativa no `HANDOFF.md`, contradizendo a regra permanente de armazenamento. Registrava ainda fatos hoje falsos (afirmava que `main` seguia `616fd24` e que `7d919fc` não estava integrada) e descrevia áreas de trabalho de outro computador. **Não foi mesclada.** A orientação de segurança aproveitável foi reescrita sob a convenção `.workspace/` e integrada por `79fd5da`, sem mesclar a branch; ela foi **excluída do remoto** na limpeza de 11/11/2026.
- `ai-memory-integration` (`ed43716`, PR #1 aberta desde 01/11/2026) é a única com trabalho real: 19 arquivos ausentes da main, incluindo `tools/memory_sync.py`, `tools/tests/test_memory_sync.py`, seeds de memória das duas marcas e um workflow de CI novo (`memory-check.yml`). Conflita em `.ai-memory.toml`, `.gitignore` e `AGENTS.md`, está 82 commits atrás e não conhece R001, BeatPlan, TEMPORAL-02 nem a regra de armazenamento. Requer decisão própria do titular, reconciliação com o `AGENTS.md` atual e autorização específica do CI novo.

Nenhuma branch foi mesclada ou excluída **pela auditoria**, que foi somente de consulta. Ressalva de método: `git cat-file -e origin/main:<caminho iniciado por ponto>` falha por conversão de caminho do MSYS no Git Bash, gerando falsos "ausente"; todos os resultados de ausência foram reconferidos por comparação de conjuntos com `git ls-tree`. A validação de links também exige incluir diretórios (`git ls-tree -r -d`), pois links com barra final não aparecem na listagem só de arquivos.

## Limpeza de branches remotas — 11/11/2026

Por autorização explícita do titular ("exclui as 13 e a obsoleta .worktrees"), foram excluídas do remoto **14 branches**: as 13 classificadas como superseded e a obsoleta da convenção `.worktrees`. Nenhuma outra branch foi tocada.

Pré-condições verificadas antes da exclusão: classificação reconferida contra a main então em `ed7e8f1`; única PR aberta era a #1 (`ai-memory-integration`), fora do conjunto; nenhuma das 14 existia como branch local nem estava checked out no checkout principal, em worktree ou nos clones auxiliares; checkout limpo, sem travas nem operação pendente.

Rede de recuperação criada **antes** da exclusão:

- registro com SHA completo, data e subject de cada uma das 14, em `.workspace/archives/limpeza-branches-2026-11-11/registro-pre-exclusao.txt` (SHA-256 do registro `2ffff7be8af5e86116d09deb092f46f27ed3602772190fdf6e85e133902d559e`);
- 14 refs locais de arquivo em `refs/archive/limpeza-2026-11-11/<nome-da-branch>`, mantendo os commits alcançáveis e protegidos contra garbage collection. Restauração de uma branch no remoto: `git push origin refs/archive/limpeza-2026-11-11/<nome>:refs/heads/codex/<nome>`.

Esses dois artefatos são **locais e não versionados**: existem apenas neste computador. Em outro clone, a recuperação depende dos SHA registrados acima e da retenção de commits pelo GitHub.

Exclusão executada com `git push origin --delete` em comando único: 14 confirmações `- [deleted]`, exit 0. Nenhum reset, clean, stash ou rewrite de história; nenhum commit apagado do objeto Git local.

Branches excluídas (nome e SHA):

| Branch | SHA |
| --- | --- |
| `codex/alinha-regra-notificacoes-marketing` | `08a39698af55b1821837dce3dcdc5751a235e8f3` |
| `codex/core-composition-v1` | `1515b06e4a785d814b0a0116d942b09f19135065` |
| `codex/core-project-manifest` | `eda7c8e2c1a09ee1e008c8d8d233547a86489423` |
| `codex/documenta-pipeline-criativo-modular` | `a4f5de428a3a06951c69294607bebae6d782cf2c` |
| `codex/documenta-plataforma-modular-marketing` | `c6933d8c1e0d06b842e87d4ee4457356bf088ce4` |
| `codex/ns-001-consolida-validacao-executada` | `10cca3e1f2dc09b66d6568c59b87705a059d1ef5` |
| `codex/ns-001-hooks` | `c58c6e9f878c84c039cc317ac0846e6a866a2da4` |
| `codex/ns-001-roteiro-001` | `3df83f314447e823ef89525c92a5c2005c8d9b8d` |
| `codex/ns-001-validacao-agenda` | `2772da7ab1616ba4235e356b83df921e15578a8b` |
| `codex/temporal-01-piloto-orquestracao` | `a5a96f475fc34e410857952c6f7c3e0e4646ce59` |
| `codex/catalogo-formatos-sociais` | `061c2e5b5de980a1b7ff3b6da3d0e3f009aa3cf9` |
| `codex/core-beat-plan-v1` | `bade62e3a720a853e6f3d18b52aa46bf544979a4` |
| `codex/historico-apresentacoes-salao02` | `22a31ab7da56e8c35d9a27404e431a18680d75e6` |
| `codex/registra-areas-de-trabalho-isoladas` | `636e5c434c6bc0c990b4451946c56853b309a8b1` |

Estado remoto após a limpeza: **7 branches**, confirmadas por `git ls-remote --heads origin` (21 antes − 14 = 7), com cada exclusão reconferida individualmente:

| Branch restante | Situação |
| --- | --- |
| `main` | `ed7e8f1e7146b3c754b4c13b2d8ba87ebf316a0e` no momento da limpeza; inalterada pela exclusão |
| `codex/ai-memory-integration` | PR #1 aberta (draft), tip `ed43716fef011b3a16341ee2625e78dd6f5c1694`; **única pendência real de branch** |
| `codex/atualiza-contexto-beat-plan-v1` | já integrada na main |
| `codex/atualiza-contexto-regra-armazenamento` | já integrada na main |
| `codex/reconcilia-beat-plan-v1` | já integrada na main |
| `codex/regra-armazenamento-workspace` | já integrada na main |
| `codex/seguranca-worktrees-workspace` | já integrada na main |

As cinco branches documentais já integradas foram **preservadas**: a autorização de limpeza cobria somente as 14 listadas. A PR #1 não foi afetada. Nenhum conteúdo de trabalho foi perdido: as 13 superseded já tinham o conteúdo na main, e a obsoleta teve sua orientação aproveitável reescrita e integrada por `79fd5da` antes da exclusão.

## Histórico da correção de contratos

Preservado como evidência do que entrou na main pela PR #6:

- [CI de pull_request: 42268435331](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42268435331) e [CI de push: 42268425001](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42268425001), quatro jobs completed/success cada, matriz Ubuntu e Windows × Node 22 e 24.
- Log do job Ubuntu + Node 22: 308 testes aprovados, zero falhas e zero testes ignorados, com prova do código 7 e da falha de `tee`.
- Revisão independente local em Linux + Node 24: typecheck aprovado, 307 testes aprovados e um teste ignorado porque a cópia de revisão não tinha metadados Git.
- Casos de `@` fora da autoridade, autoridade vazia, barras extras e credenciais executados nos dois motores com os resultados esperados.
- Limitação não diagnosticada, registrada na época: uma execução local antiga teve 286 testes aprovados e seis falhas sem nomes preservados. As correções de URL e de captura de logs não foram apresentadas como explicação dessa ocorrência.

## R002 — piloto técnico local de vídeo sem áudio

- Status: **integrado na main** pelo merge `b7ed1d9bbf397f5e9f14bfddc62c67aa0d4f5cf9` (12/11/2026), a partir da branch técnica `codex/r002-video-local-agenda` (HEAD `b59076918eea6a2eaecda90bf2ec3c8cb4ac6c60`, commits `2e663e3`, `040e290`, `b590769` preservados sem squash), com commit corretivo único `0ac4bde8e5096ecdf4913a48ad453e066346b213` (derivação da raiz principal nos testes, portável entre checkout e worktree).
- Natureza: **demonstração técnica local reproduzível**, não campanha aprovada, não produção real da NS-001, nada publicado ou enviado a rede. Dados inteiramente fictícios (salão de teste E2E).
- Exportador sem áudio: [`tools/build_video.py`](../../tools/build_video.py) recusa entrada de áudio, nunca usa `anullsrc` nem AAC silencioso, mapeia somente vídeo com `-an`; exportação transacional com staging em `.workspace/tmp/`, validação antes de `os.replace` e preservação integral da entrega anterior em falha (exit ≠ 0, stderr sanitizado).
- Validador SRT puro: [`tools/srt_validate.py`](../../tools/srt_validate.py) — UTF-8, LF, uma newline final, sequência numérica, timestamps válidos, início < fim, ordem cronológica, sem sobreposição, dentro da duração, texto não vazio.
- Piloto: [`tools/r002_pilot.py`](../../tools/r002_pilot.py) com três cenas de 12 s (0–4, 4–9, 9–12) reutilizando a captura sanitizada já versionada `00-briefings/campanhas/NS-001/capturas/2026-11-05/01-agenda-visao-dia.png`; contorno editável sobre o horário ocupado 09:00–10:00 em camada PNG RGBA separada (stdlib), configurável por JSON ([`tools/r002/agenda-ficticia.pilot.json`](../../tools/r002/agenda-ficticia.pilot.json)); legenda visível queimada, SRT sincronizado ([`04-legendas/roteiro_r002_agenda_ficticia.srt`](../../04-legendas/roteiro_r002_agenda_ficticia.srt)) e narração em texto separado ([`04-legendas/roteiro_r002_agenda_ficticia_narracao.txt`](../../04-legendas/roteiro_r002_agenda_ficticia_narracao.txt)).
- Revisão localizada: [`tools/r002/agenda-ficticia-revisao.pilot.json`](../../tools/r002/agenda-ficticia-revisao.pilot.json) altera somente `outline.color` e `outline.thickness` (e `id`/`videoName`); prova por SHA-256 de captura/SRT/narração idênticos e MP4 diferente.
- Evidência medida na integração (12/11/2026, Python 3.14.7, FFmpeg/FFprobe 9.0.2): **21 testes unittest, zero falhas, zero skips**; reprodução v1 e revisão byte a byte idênticas à entrega original; FFprobe nos dois MP4: 1 stream de vídeo H.264 1080×1920@30 yuv420p, **0 streams de áudio**, duração 12.0 s; inspeção visual dos frames das três cenas e da cena revisada; caso de SRT inválido contra entrega existente com exit 1 e hashes anteriores idênticos.
- MP4 **não versionados** (`.gitignore` ignora `*.mp4`): existem apenas em `.workspace/archives/r002-video-local/` neste computador; o manifesto versionado [`02-reels-shorts/r002-agenda-ficticia/manifest.json`](../../02-reels-shorts/r002-agenda-ficticia/manifest.json) preserva SHA-256, bytes, FFprobe e comando reproduzível. Evidências da integração (logs, frames, manifesto de hashes) em `.workspace/logs/r002-integration/`, não versionadas.
- Comandos de reprodução (a partir da raiz do checkout; em worktree dentro de `.workspace/`, acrescentar `--project-root <raiz>`): `python tools/r002_pilot.py --config tools/r002/agenda-ficticia.pilot.json --staging .workspace/tmp/r002-video-local/v1 --archive .workspace/archives/r002-video-local --manifest 02-reels-shorts/r002-agenda-ficticia/manifest.json --tag v1` (e o análogo com `agenda-ficticia-revisao.pilot.json` / `--tag revisao`); testes: `python -m unittest discover -s tools/tests`. Detalhe em [`02-reels-shorts/r002-agenda-ficticia/README.md`](../../02-reels-shorts/r002-agenda-ficticia/README.md).
- Sem workflow de CI aplicável por path a `tools/`, `04-legendas/` ou `02-reels-shorts/` (os workflows existentes cobrem `platform/` e `orchestration/temporal/`); ausência registrada, nenhum workflow criado nesta entrega.
- Limites: demonstração técnica; sem aprovação editorial; sem produção real; sem publicação; sem fornecedor, TTS ou rede; sem deploy; nenhuma alteração em `platform/`, `orchestration/`, Temporal, R001, OutputPlan ou BeatPlan.

## NS-001

Registro de estado apenas; os arquivos da campanha não foram alterados.

- Versão editorial: 0.3 em briefing, hooks e roteiro.
- Estado: validação editorial — briefing em validação, hooks e roteiro em rascunho. NS-001-H15 continua seleção em rascunho.
- Execução técnica: concluída em 05/11/2026, com E2E local aprovado e validação autenticada em emuladores, dados fictícios e viewport móvel emulado. Não é validação de produção nem de aparelho físico.
- Gravação: não autorizada.
- Publicação: não autorizada.
- Capturas: 12 arquivos de 05/11/2026, evidência técnica — não são frames finais aprovados.
- Bloqueios: aprovação do briefing, do hook e do roteiro, responsável definido, CTA e destino por canal, revisão dos textos, duração cronometrada, identidade de marca para uso público e as autorizações de gravação e publicação.

Fontes: [briefing](../../00-briefings/campanhas/NS-001/briefing.md), [hooks](../../02-hooks/campanhas/NS-001/hooks.md), [roteiro](../../03-roteiros/campanhas/NS-001/roteiro-001.md) e [execução autenticada de 05/11](../../00-briefings/campanhas/NS-001/VALIDACAO-EXECUCAO-2026-11-05.md). A execução não tem identidade exata com um commit remoto verificável; a auditoria estática anterior aponta o commit `6342a33a36b0a4eadd0f5a62770f1eee485156ee` do Salao02 — são evidências distintas, e não se atribui commit retroativamente.

O resumo não substitui os registros de campanha nem amplia autorizações já existentes para outros fluxos de conteúdo. As regras vigentes de vídeo sem áudio, narração em texto separado, SRT e atuação dos bots continuam em [AGENTS.md](../../AGENTS.md) e [WORKFLOW.md](../../WORKFLOW.md).

## Governança de armazenamento e áreas de trabalho

Em 11/11/2026 o titular estabeleceu uma **regra permanente de armazenamento**, registrada em [AGENTS.md](../../AGENTS.md) pelo commit `9908f3b6424a196464ed0557294a8efb0445774a` e reforçada pelo commit `79fd5dae1db5450960d4cebe922ea26b71d8b6c5`. É normativa para qualquer clone e qualquer agente; este contexto apenas a registra e aponta para a fonte, que é o `AGENTS.md`.

- A raiz oficial do projeto é o **próprio checkout principal**, qualquer que seja o caminho nesta estação: `<RAIZ>` = `git rev-parse --show-toplevel`, com `.workspace/` dentro dele. **O invariante são os arquivos, não o caminho:** o repositório existe em mais de um computador e pode ser aberto por IDEs diferentes, cada um com sua pasta local; o que precisa estar idêntico e atualizado em todas as estações são os arquivos versionados, alinhados por Git. A revisão de `AGENTS.md` em `2c40967` fixou o caminho literal `C:/Repos/marcasalao-marketing`, que descreve o layout de uma estação; a redação portável de 12/11/2026 substituiu o literal por `<RAIZ>`, registra as instâncias conhecidas (`C:/Marketing`, `C:/Repos/marcasalao-marketing` e qualquer outra) como ilustrativas e não exaustivas, e acrescenta a seção Alinhamento entre estações. A substância da regra não mudou e nenhum repositório foi realocado. A realocação da worktree `r001-reconcilia` para `.workspace/worktrees/r001-reconcilia` registrada em `2c40967` ocorreu na estação daquela sessão; não é um fato deste checkout.
- Alinhamento entre estações: atualizar a estação com `fetch`/`pull --ff-only` antes de trabalhar; commitar e enviar o que for permanente ao terminar; nunca alinhar por cópia manual de pastas nem por sincronizador de nuvem sobre o checkout; não padronizar caminhos entre máquinas; `.workspace/` é local e não sincroniza, portanto evidência que precise viajar deve ser versionada. Divergência entre estações se resolve pelo Git, não realocando pastas.
- Isolamento e arquivos auxiliares usam exclusivamente `.workspace/`, com subdiretórios por tarefa: `worktrees/`, `clones/`, `archives/`, `logs/`, `tmp/` e `tools/`.
- `.workspace/` é ignorada localmente por `.git/info/exclude`; o `.gitignore` versionado **não** deve ser alterado para acomodar arquivos de tarefa.
- Arquivo necessário em outro computador não pode permanecer somente em `.workspace/`: precisa entrar na árvore versionada e ser commitado na branch autorizada.
- Worktrees e clones auxiliares só dentro de `.workspace/worktrees/` e `.workspace/clones/`. Antes de mover ou remover área existente, conferir `git worktree list --porcelain` e se há sessão ou agente ativo; usar `git worktree move` e `git worktree remove`, nunca `rm -rf` em worktree registrada, porque a branch e os commits vivem no `.git` do repositório principal. Mover ou remover exige autorização do titular.
- A regra inclui validação de contenção do caminho antes de criar arquivo, bloqueio obrigatório quando a ferramenta exigir caminho externo, limpeza ao final e handoff com confirmação textual.

Consolidação realizada em 11/11/2026: as pastas auxiliares externas `C:/Marketing-Docs`, `C:/Marketing-Integration` e `C:/Marketing-Reviews` foram auditadas; os dois clones independentes que continham foram realocados para `.workspace/clones/` com integridade conferida (HEAD, tree do HEAD, branch, refs locais e remotas, contagem de arquivos, soma de bytes e SHA-256 de `.git/config` idênticos antes e depois); as três raízes externas foram removidas por estarem vazias. Nenhuma branch, commit, arquivo não rastreado ou evidência foi perdido.

Exceção declarada e não resolvida: o aplicativo grava anexos do usuário e saídas grandes de ferramenta em diretório temporário próprio, fora da raiz, e outro processo deixou um dump de segurança de rebase em `/tmp`. Cópias desses arquivos foram preservadas dentro de `.workspace/archives/` com SHA-256 conferido idêntico ao original; os originais externos foram mantidos por decisão do titular. Eliminar essa exceção na origem exige configuração do aplicativo, não desta tarefa.

A convenção `.worktrees/` proposta pela branch `codex/registra-areas-de-trabalho-isoladas` **não está em vigor** e não deve ser seguida: contradizia a regra permanente. A branch foi excluída do remoto na limpeza de 11/11/2026 e sua orientação de segurança aproveitável já está integrada sob `.workspace/`. Ver as seções Auditoria das branches não integradas e Limpeza de branches remotas.

## Próximo passo

> Revisar e decidir a integração da branch técnica `codex/local-render-adapter-v1` (primeiro adaptador de render local de prova, autorizado em 12/11/2026 apenas para implementação, testes, documentação e CI da branch). O merge na main exige autorização separada do titular.
>
> Deliberar se o projeto permanece bloqueado ou se uma próxima fatia específica de TEMPORAL-02 será autorizada, com escopo delimitado pelo titular. A ratificação da fatia Workflow, registrada em 2026-11-11, não autoriza nenhuma fatia posterior.
>
> Deliberar separadamente, antes de qualquer nova implementação, se haverá uma futura combinação entre Composition, BeatPlan, OutputPlan ou Temporal. A integração técnica do BeatPlan v1 em `d5761b1` não autoriza essa combinação.

O Workflow já está integrado, homologado tecnicamente e ratificado no escopo dessa fatia; não deve ser reimplementado como próxima tarefa. O BeatPlan v1 já está integrado como fatia interna da `platform`; não deve ser reimplementado nem tratado como branch-only. Permanecem **bloqueados até autorização específica**:

- Worker de produção dedicado à composição;
- servidor Temporal remoto, namespace de produção e Worker persistente;
- `contentHash` e qualquer canonicalização de entrada;
- integração de TEMPORAL-02 em produção (a execução local já está integrada em `5376890`);
- combinação de BeatPlan × OutputPlan e BeatPlan no Temporal;
- TEMPORAL-04;
- renderização, adaptadores, `VisualStyle`, `VisualAnchor`, `AssetManifest` completo, `AudioPlan` e `RenderPlan`;
- mídia, fornecedores e deploy.

Pré-condições técnicas já cumpridas, sem abrir autorização futura:

- fronteira pública da platform integrada (`TEMPORAL-02-01`);
- contrato de entrada versionado e preflight local integrados (`TEMPORAL-02-02`);
- Activity real integrada e ratificada (`TEMPORAL-02-03`), com coordenação de build no CI;
- Workflow, contrato de resultado, classificador e Retry Policy integrados e homologados tecnicamente em `f584210` e ratificados em escopo estrito pelo titular;
- evidência de 162 testes e CI Ubuntu/Windows, Node 22, exclusivamente em `f584210`, detalhada na seção da fatia Workflow;
- execução local completa (cliente, Worker, CLIs, replay e gate Elephant–Goldfish) integrada em `5376890`, com 198 testes do pacote e CI Ubuntu/Windows, Node 22, no SHA `63d04d5`;
- núcleo sem dependência Temporal.

A ratificação da fatia Workflow foi registrada pelo titular em 2026-11-11 e encerra estritamente o escopo homologado de `f584210`, sem aprovar o PRD completo. Ela não autoriza a próxima fatia: qualquer implementação posterior exige decisão específica que delimite seu escopo, e o PRD permanece em revisão.

Tarefas secundárias de consulta:

1. decidir se as cinco branches documentais já integradas (`atualiza-contexto-beat-plan-v1`, `atualiza-contexto-regra-armazenamento`, `reconcilia-beat-plan-v1`, `regra-armazenamento-workspace`, `seguranca-worktrees-workspace`) podem ser arquivadas, sem exclusão automática — a limpeza de 11/11/2026 já removeu as 13 superseded e a obsoleta;
2. decidir o destino da PR #1 (`ai-memory-integration`) como tarefa própria de reconciliação com o `AGENTS.md` atual, com autorização específica para o workflow de CI novo — é a única branch com trabalho real pendente;
3. reconferir periodicamente o estado da main e as PRs abertas antes de planejar qualquer integração;
4. revisar a coerência entre o BeatPlan integrado e os conceitos futuros de [`docs/decisoes/`](../decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md), sem escrever código nem escolher renderizador.

## O que não fazer agora

- não reimplementar o Workflow já integrado nem criar Worker de produção sem autorização explícita;
- não criar cliente Temporal de validação, start da aplicação, Workflow ID ou suas políticas sem autorização específica;
- não tratar a ratificação da fatia Workflow como conclusão integral de TEMPORAL-02, aprovação do PRD ou autorização de próxima fatia;
- não tratar o PRD de TEMPORAL-02 como aprovado sem decisão explícita;
- não executar replay formal ou gate Elephant–Goldfish de TEMPORAL-02 sem autorização;
- não iniciar TEMPORAL-04;
- não combinar BeatPlan × OutputPlan nem levar BeatPlan ou o OutputPlan já integrado ao Temporal por consequência da integração;
- não gerar prévia;
- não exportar;
- não gerar mídia;
- não instalar Qwen3.8;
- não integrar Higgsfield;
- não alterar campanhas;
- não publicar conteúdo;
- não executar deploy.

Exceção estreita e vigente: o **render local de prova com dados fictícios** do
`CreativeExecutionPackage` v1 está autorizado pelo titular em 12/11/2026
somente no escopo da branch `codex/local-render-adapter-v1` (ferramenta local
em `tools/`, sem fornecedor, publicação, serviço externo ou Temporal). Essa
autorização não altera nenhum dos bloqueios acima para campanha real,
produção da NS-001, mídia real ou publicação, e não autoriza o merge na main.

## O que esta atualização não verificou

Esta atualização é exclusivamente documental e registra a **limpeza de 14 branches remotas** autorizada pelo titular em 11/11/2026: não executou instalação de dependências, build, typecheck ou testes e não alterou código, `platform/`, `orchestration/`, CI, PRDs, decisões arquiteturais, campanhas ou mídia. A exclusão foi conferida por `git ls-remote --heads origin` (7 branches restantes, 21 antes menos 14) e por verificação individual de ausência de cada uma das 14. A `main` não foi alterada pela exclusão: `origin/main` permaneceu em `ed7e8f1e7146b3c754b4c13b2d8ba87ebf316a0e` durante o processo, e esta atualização documental foi commitada sobre essa base. A PR #1 (`ai-memory-integration`) foi confirmada como ainda aberta e não afetada. Nenhum workflow foi disparado pela exclusão de branches nem por este commit documental — `docs/contexto/` não está nos filtros de path dos três workflows. Não foram executados replay formal, Elephant–Goldfish de TEMPORAL-02 ou deploy.

Preserva-se a evidência histórica da regra de armazenamento e da segurança de worktrees: os commits `9908f3b` e `79fd5da` alteram somente `AGENTS.md`, com 76 e 4 inserções, zero exclusões, blob em LF puro e `git diff --check` limpo; a API pública do GitHub confirmou zero runs para ambos. A auditoria que justificou a limpeza usou apenas dry-run (`git merge-tree --write-tree`) e consultas de leitura, sem mesclar, commitar ou excluir nada por si mesma.

Preserva-se a evidência histórica do BeatPlan v1: 626 testes, zero falhas e zero skips nos quatro ambientes, vinculados a `7d919fc` e `d5761b1` (runs [43034990448](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43034990448) e [43099977731](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43099977731)), conforme registrado no README da platform. Não são medições dos commits documentais posteriores nem foram repetidos nesta atualização; os logs por job exigem autenticação e não foram relidos. A contagem de 38 entradas do tarball permanece informada no pedido original, não reexecutada.

Preserva-se a evidência histórica da fatia Workflow: 162 testes e repetibilidade 7/7 obtidos na homologação de `f584210`, não nos HEADs posteriores. A ratificação da fatia Workflow registrada pelo titular em 2026-11-11 permanece restrita àquele escopo e não é ampliada pela integração do BeatPlan nem pelas mudanças de governança.

Preserva-se a evidência histórica de TEMPORAL-02-03: suíte local Windows com Node 22, 145 testes aprovados em 52s, e CI Ubuntu/Windows no commit `db84270ad3e51eecb0b562fcdf3a7e36941288ab` (runs [42902255503](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42902255503) e [42902338737](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42902338737)). Não é execução desta atualização.

Estado remoto de publicações e rascunhos no Postiz, execução de ComfyUI, implantação das integrações no servidor e novas jornadas do Salao02 não foram consultados nem executados.
