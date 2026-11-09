# Estado atual do projeto

## Referência

- Data da atualização: 2026-11-09
- Branch de referência: main
- Commit da main: [33b46ce54649fc60340c2e85b15d0b39ad112cff](https://github.com/Jonatasbottaro/marcasalao-marketing/commit/33b46ce54649fc60340c2e85b15d0b39ad112cff) — integração documental do PRD de TEMPORAL-02, integrado em 08/11/2026
- Fonte: Git, documentação integrada e GitHub Actions

`33b46ce` é a referência corrente da main e contém o PRD de TEMPORAL-02. O intervalo `3304e82..33b46ce` adiciona **somente** `docs/planejamento/TEMPORAL-02-validacao-de-composition.md`: é integração documental, não implementação de TEMPORAL-02.

Os marcos permanecem distintos e não se substituem:

- commit técnico final de TEMPORAL-01: `07e38f47df50fd6d8b264bc999fe4082be4b2bb6`;
- merge da estrutura `docs/contexto/` pela PR #7: `fbd222d996527f6cf226051a8526f932accd7e5e`;
- correção pós-merge do contexto: `3304e82aedf5db59d6507ece6ca20b4df46ac973`;
- integração documental do PRD de TEMPORAL-02: `33b46ce54649fc60340c2e85b15d0b39ad112cff`.

`33b46ce` **não** é implementação de TEMPORAL-02. Nenhum Workflow, Activity, código, dependência ou alteração em `platform/` e `orchestration/temporal/` entrou na main por esse commit.

O hash identifica o ponto consultado, não uma promessa de permanência. Reconferir `git rev-parse origin/main`, as PRs abertas e o conteúdo efetivamente integrado antes de trabalhar; um commit apenas documental posterior não muda a referência do código analisado. Esta correção é documental: não altera código, `platform/`, `orchestration/temporal/`, campanhas nem CI.

## Núcleo reutilizável

### Integrado à main

- **ProjectManifest**: contrato, schema, validador, relatório, CLI e exemplos em `platform/src/project-contract.ts`, `platform/src/validate-project.ts`, `platform/schemas/project.schema.json` e `platform/examples/projects/`.
- **Composition v1**: composição declarativa por cenas e vínculo com o projeto em `platform/src/composition-contract.ts`, `platform/src/validate-composition.ts` e `platform/schemas/composition.schema.json`. Schema discriminado por tipo de cena e união discriminada no TypeScript.
- **Contratos e validadores existentes**: funções puras com relatório de códigos, erros e warnings (`platform/src/validation-report.ts`), regra lexical de caminhos compartilhada (`platform/src/relative-path.ts`) e corpus de paridade entre tipos, schemas e validadores em `platform/tests/contracts/`, com execução real dos schemas em motor draft-07.
- **CLIs existentes**: `content:validate-project` e `content:validate-composition`, além de `build`, `typecheck`, `test`, `test:contracts` e `clean` em [platform/package.json](../../platform/package.json).
- **CI da plataforma**: [`.github/workflows/platform-validation.yml`](../../.github/workflows/platform-validation.yml), `Validar contratos da platform`, matriz Ubuntu e Windows × Node 22 e 24.
- **Runtime do núcleo**: Node `>=22 <25`, TypeScript compilado para JavaScript, motor de schema apenas em desenvolvimento.
- **Correção de contratos da PR #6**: integrada em 06/11/2026 pelo merge commit `0c97c2a`. A distinção entre "main anterior" e "correção pendente" que esta página mantinha foi retirada porque a main já contém o comportamento corrigido.
- **TEMPORAL-01**: piloto de orquestração em [`orchestration/temporal/`](../../orchestration/temporal/README.md), planejado em [`docs/planejamento/TEMPORAL-01-piloto-de-orquestracao.md`](../planejamento/TEMPORAL-01-piloto-de-orquestracao.md) e protegido por CI específico em [`.github/workflows/temporal-pilot-ci.yml`](../../.github/workflows/temporal-pilot-ci.yml).
- **PR #7 — contexto integrado**: [PR #7](https://github.com/Jonatasbottaro/marcasalao-marketing/pull/7) integrada à main pelo merge `fbd222d996527f6cf226051a8526f932accd7e5e` em 08/11/2026. `docs/contexto/` (`README.md`, `ESTADO-ATUAL.md`, `PROXIMOS-PASSOS.md` e `HANDOFF.md`) passou a pertencer à main e é fato integrado, não proposta em revisão. A branch `codex/atualiza-contexto-projeto` pode continuar existindo sem representar trabalho pendente; a branch remota não foi excluída.

### Em branch pública

Registrar aqui apenas o que continua fora da main, conforme o Git real:

- **R001 — catálogo de formatos sociais**: branch `codex/catalogo-formatos-sociais`, checkpoint `55aeecccfa38da06dfada875e75d81b265626abc`. O `git merge-base --is-ancestor` contra `origin/main` devolve saída 1: **branch-only**.
- **OutputPlan, perfis de conteúdo e as CLIs `content:profiles` e `content:plan-output`**: existem apenas dentro da branch do R001. Listar a main para `platform/src/output-plan-contract.ts`, `platform/schemas/output-plan.schema.json`, `platform/src/output-profiles` e `platform/examples/output-plans` devolve vazio.
- **BeatPlan**: branch `codex/core-beat-plan-v1`, checkpoint `bade62e3a720a853e6f3d18b52aa46bf544979a4`, **branch-only** pela mesma checagem. A branch toca `package.json`, README da platform, relatório de validação e testes de portabilidade — sobreposição que precisa de reconciliação antes de qualquer integração.
- **PR #1 — integração de ai-memory**: [PR #1](https://github.com/Jonatasbottaro/marcasalao-marketing/pull/1), aberta. Fora do escopo técnico deste estado; não considerá-la integrada por associação.

Nada acima está integrado, por mais que o trabalho exista e tenha evidência própria.

### Planejado ou documentado

- **R002 e R003**: sem documento próprio no repositório. A única ocorrência na main é o §14 do planejamento do TEMPORAL-01, que os declara não iniciados e não integrados.
- **VisualStyle, VisualAnchor, AssetManifest, AudioPlan, RenderPlan e adaptadores**: conceitos registrados em [`docs/decisoes/`](../decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md). Nenhum tem implementação na main: `platform/src` contém somente os contratos de projeto e composição, os validadores, os dois CLIs, o relatório e a regra de caminhos.
- **Qwen3.8**: família indicada para um futuro executor de texto, registrada no §15 do planejamento do TEMPORAL-01. Nada instalado, baixado, inferido ou acoplado.
- **Higgsfield**: nenhuma ocorrência em código ou documentação da main. É referência externa de conversa, não ferramenta adotada.
- **TEMPORAL-02** e **TEMPORAL-04**: estados próprios nas seções abaixo.

## Limites do núcleo

- Composition é um contrato declarativo; não é execução do roteiro nem renderização.
- Renderer undecided é aceito e produz um warning; nenhum renderizador do novo núcleo foi implementado.
- Metadata approved é estado técnico. Não concede aprovação editorial, gravação ou publicação.
- Existência física de assets, licenças, inspeção final e prontidão para publicar não são comprovadas por `valid: true`.
- `scenes` vazio é aceito pela v1. Exigir uma cena mínima seria evolução de requisito.
- Os casos estruturais do corpus comparam os dois motores. Vínculos entre documentos, IDs de cena duplicados e overflow da soma permanecem verificações semânticas do core.
- A segunda configuração do núcleo ainda é uma fixture genérica. A Multitrack Hub já tem fluxos próprios no repositório, mas ainda não é um exemplo real do ProjectManifest nesse núcleo.

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

## TEMPORAL-02

- **PRD de TEMPORAL-02 integrado; implementação não iniciada.**
- Arquivo: [`docs/planejamento/TEMPORAL-02-validacao-de-composition.md`](../planejamento/TEMPORAL-02-validacao-de-composition.md), integrado à main em `33b46ce54649fc60340c2e85b15d0b39ad112cff`.
- Status do documento: **PRD em revisão**.
- Aprovação do PRD: **não concedida**.
- Implementação: **não iniciada**.
- Autorização de implementação: **não concedida**.
- Código: **nenhum**. Dependências: **nenhuma nova**. Temporal executado: **nenhum**. Deploy: **nenhum**.
- `platform/` e `orchestration/temporal/` não foram alterados por essa integração.

Integrar o PRD **não** é aprová-lo, e aprovar o PRD **não** é autorizar a implementação: são decisões separadas e explícitas do titular.

### Passo real planejado

- Operação: `validate-composition` — **um único** passo.
- Objetivo: validar uma Composition v1 contra um ProjectManifest válido.
- Função existente do núcleo: `validateComposition(composition, project)` — exportada por módulo interno, **ainda sem fronteira pública estável** entre os pacotes `platform` e `orchestration/temporal`. A ordem é Composition primeiro, ProjectManifest depois.
- Componentes **conceituais**, não implementados: Workflow `validateCompositionWorkflow`, Activity `validateCompositionActivity`, resultado `CompositionValidationWorkflowResult` e relatório do núcleo `CompositionValidationReport`.
- Nenhum desses componentes existe em código na main.

### Quatro vias planejadas

- **A. Rejeição no preflight** — antes do start; sem Workflow; sem resultado de execução.
- **B. Conflito no start** — `workflowId` já existente; sem nova execução; classificado pelo cliente; sem `CompositionValidationWorkflowResult`.
- **C. Resultado do domínio** — `valid` ou `invalid`; relatório presente; `failureCode` nulo; `completedSteps` com `validate-composition`.
- **D. Falha da execução** — `failed`; relatório ausente; `failureCode` obrigatório; `completedSteps` vazio enquanto nenhum relatório for recebido.

A fonte canônica das quatro vias, dos códigos e dos contratos é o [PRD](../planejamento/TEMPORAL-02-validacao-de-composition.md); este resumo não o substitui.

### Retries e timeouts planejados

Política definida no PRD, **ainda não implementada**:

- `startToCloseTimeout`: cinco segundos;
- `maximumAttempts`: duas tentativas;
- falha transitória pode gerar a segunda tentativa;
- `StartToCloseTimeout` pode gerar a segunda tentativa;
- falha inesperada planejada como não retryable;
- `invalid` não sofre retry;
- preflight não entra na Retry Policy;
- conflito de start não entra na Retry Policy da Activity;
- timeout persistente termina como `failed`;
- `nonRetryableErrorTypes` não controla `TimeoutFailure`.

Nada disso foi executado: não há Activity, Worker nem execução de Temporal para TEMPORAL-02.

### Gates obrigatórios, nenhum executado

- **Gate de fronteira pública** — obrigatório **antes** de criar a Activity: entrypoint público mínimo da `platform`; consumo compilado pelo pacote Temporal; proibição de import relativo de `platform/src`; proibição de import de `dist` sem contrato de build; proibição de duplicar o validador; proibição de mover o validador para `orchestration/`; build em checkout limpo; portabilidade em Ubuntu e Windows. A estratégia — pacote local, workspace ou artefato compilado — continua **em aberto**.
- **Gate Elephant–Goldfish** — obrigatório **após** a futura implementação e **antes** da integração de TEMPORAL-02 na main. Revisões mínimas: fronteira pública, ordem dos argumentos, paridade, history, payload, quatro vias, `invalid` versus `failed`, retries, replay, isolamento do núcleo e ausência de mídia e fornecedores.

O gate Elephant–Goldfish registrado na seção própria acima foi o de **TEMPORAL-01** e não cobre TEMPORAL-02. Nenhum dos dois gates de TEMPORAL-02 foi executado.

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
| R001 | `codex/catalogo-formatos-sociais` | `55aeecccfa38da06dfada875e75d81b265626abc` | `git branch -r --contains` aponta só a branch; `merge-base --is-ancestor` contra `origin/main` com saída 1, reconferido em 09/11/2026 | **branch-only**, estágio R001-05 concluído em 07/11/2026 |
| BeatPlan | `codex/core-beat-plan-v1` | `bade62e3a720a853e6f3d18b52aa46bf544979a4` | mesmas checagens, saída 1 em 09/11/2026; run [42321831284](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42321831284) de `Validar contratos da platform` nesse HEAD: completed/success | **branch-only**, CI verde no HEAD medido |

O checkpoint informado do R001 é um commit documental posterior ao checkpoint de código da etapa R001-05. Nenhum dos dois HEADs está na main e nenhum foi substituído por trabalho equivalente: a main tem os contratos de projeto e composição, não o catálogo de perfis nem o BeatPlan. A branch de BeatPlan não foi homologada nesta atualização de contexto; o que foi consultado é o CI do HEAD medido.

## Histórico da correção de contratos

Preservado como evidência do que entrou na main pela PR #6:

- [CI de pull_request: 42268435331](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42268435331) e [CI de push: 42268425001](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42268425001), quatro jobs completed/success cada, matriz Ubuntu e Windows × Node 22 e 24.
- Log do job Ubuntu + Node 22: 308 testes aprovados, zero falhas e zero testes ignorados, com prova do código 7 e da falha de `tee`.
- Revisão independente local em Linux + Node 24: typecheck aprovado, 307 testes aprovados e um teste ignorado porque a cópia de revisão não tinha metadados Git.
- Casos de `@` fora da autoridade, autoridade vazia, barras extras e credenciais executados nos dois motores com os resultados esperados.
- Limitação não diagnosticada, registrada na época: uma execução local antiga teve 286 testes aprovados e seis falhas sem nomes preservados. As correções de URL e de captura de logs não foram apresentadas como explicação dessa ocorrência.

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

## Próximo passo

> Revisar e decidir sobre a aprovação do PRD de TEMPORAL-02.

O PRD está integrado à main; a decisão de aprová-lo é a próxima etapa e ainda não foi tomada.

- integração do PRD **não** equivale à aprovação;
- aprovação do PRD **não** equivale à autorização de implementação;
- a implementação depende de nova decisão explícita do titular.

Critérios da decisão:

1. aceitar ou rejeitar o passo `validate-composition`;
2. aceitar ou ajustar os limites 64/256/384 KiB;
3. escolher a estratégia da fronteira pública;
4. aceitar ou ajustar duas tentativas;
5. confirmar o gate Elephant–Goldfish obrigatório;
6. manter TEMPORAL-04 fora;
7. manter R001, OutputPlan e BeatPlan fora.

Pré-condições:

- TEMPORAL-01 integrado — **cumprido**, com evidência na seção acima;
- contexto atualizado e integrado à main pela PR #7 — **cumprido**;
- PRD de TEMPORAL-02 integrado à main — **cumprido** em `33b46ce`;
- escolha explícita do passo real — **cumprida no PRD** (`validate-composition`), sujeita a aprovação;
- contrato de entrada e saída pequeno — **documentado no PRD**, sujeito a aprovação;
- nenhuma dependência de fornecedor — **requisito**;
- aprovação do PRD — **pendente**;
- autorização do titular — **pendente**.

Nenhuma dessas condições concede autorização automática para implementar TEMPORAL-02: a autorização do titular continua necessária e separada da aprovação do PRD.

Tarefas secundárias permitidas:

1. revisar as branches públicas de R001 e BeatPlan;
2. decidir se branches já integradas podem ser arquivadas;
3. confirmar periodicamente se R001 e BeatPlan continuam branch-only antes de planejar qualquer integração.

## O que não fazer agora

- não implementar TEMPORAL-02 nesta tarefa;
- não aprovar o PRD de TEMPORAL-02 nesta tarefa;
- não autorizar a implementação de TEMPORAL-02 nesta tarefa;
- não iniciar TEMPORAL-04;
- não integrar OutputPlan e BeatPlan;
- não gerar prévia;
- não exportar;
- não gerar mídia;
- não instalar Qwen3.8;
- não integrar Higgsfield;
- não alterar campanhas;
- não publicar conteúdo;
- não executar deploy.

## O que esta atualização não verificou

Estado remoto de publicações e rascunhos no Postiz, execução de ComfyUI, implantação das integrações no servidor e novas jornadas do Salao02 não foram consultados nem executados. As CLIs e os testes do pacote temporal não foram reexecutados nesta tarefa: a contagem de 120 vem da documentação integrada na main e dos logs do run 42494941537, que é o portão automático do pacote. Consultar esses pontos quando fizerem parte da tarefa solicitada.

Esta atualização é documental. Nenhum teste de código, execução de Temporal, execução da `platform` ou geração de mídia foi executado, e nenhum gate de TEMPORAL-02 foi rodado.
