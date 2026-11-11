# Estado atual do projeto

## Referência

- Data da atualização: 2026-11-11
- Branch de referência: main
- Commit da main consultada: [e86f3c9ef939ac7536ecf39a65cf4f6ee97e4b52](https://github.com/Jonatasbottaro/marcasalao-marketing/commit/e86f3c9ef939ac7536ecf39a65cf4f6ee97e4b52) — integra o R001 e contém a fatia Workflow de TEMPORAL-02
- Commit técnico da fatia Workflow: `f5842107a0f307b4cc208c15fc4509c6d7d31f72`
- Ratificação da fatia Workflow: registrada pelo titular em 2026-11-11, restrita ao escopo homologado de `f584210`
- Fonte: Git e documentos da main consultada; evidências da homologação técnica e do GitHub Actions vinculadas aos respectivos commits, sem nova execução de gates nesta atualização documental

`e86f3c9` é o HEAD da main consultada, posterior à integração técnica do Workflow em `f584210`. A Activity `validateCompositionActivity` permanece integrada e ratificada no escopo de **TEMPORAL-02-03**; o Workflow `validateCompositionWorkflow`, seu contrato de resultado, o classificador de falhas e a Retry Policy estão integrados e homologados tecnicamente em `f584210` e **ratificados pelo titular em 2026-11-11**, com escopo estrito detalhado na seção TEMPORAL-02 — Fatia Workflow. A ratificação não aprova o PRD completo nem autoriza qualquer fatia posterior. Worker de produção, cliente de validação, `workflow.start` da aplicação, Workflow ID e suas políticas de reuso e conflito, colisão de Workflow ID, `contentHash`, replay formal e o gate Elephant–Goldfish de TEMPORAL-02 continuam ausentes, não executados ou pendentes, todos bloqueados. O R001 está integrado no núcleo; BeatPlan continua branch-only e nenhum deles passa a compor TEMPORAL-02 por consequência.

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
- integração do R001 e HEAD da main consultada: `e86f3c9ef939ac7536ecf39a65cf4f6ee97e4b52`, contendo a reconciliação `8e17785a5634167f8abdaebacb8388276b909cab`.

O hash identifica o ponto consultado, não uma promessa de permanência. Reconferir `git rev-parse origin/main`, as PRs abertas e o conteúdo efetivamente integrado antes de trabalhar; um commit apenas documental posterior não muda a referência do código analisado. Os 162 testes e os runs da fatia Workflow referem-se exclusivamente a `f584210`, não ao HEAD posterior `e86f3c9`. Nenhum desses marcos representa implementação completa de TEMPORAL-02.

## Núcleo reutilizável

### Integrado à main

- **ProjectManifest**: contrato, schema, validador, relatório, CLI e exemplos em `platform/src/project-contract.ts`, `platform/src/validate-project.ts`, `platform/schemas/project.schema.json` e `platform/examples/projects/`.
- **Composition v1**: composição declarativa por cenas e vínculo com o projeto em `platform/src/composition-contract.ts`, `platform/src/validate-composition.ts` e `platform/schemas/composition.schema.json`. Schema discriminado por tipo de cena e união discriminada no TypeScript.
- **Contratos e validadores existentes**: funções puras com relatório de códigos, erros e warnings (`platform/src/validation-report.ts`), regra lexical de caminhos compartilhada (`platform/src/relative-path.ts`) e corpus de paridade entre tipos, schemas e validadores em `platform/tests/contracts/`, com execução real dos schemas em motor draft-07.
- **Fronteira pública mínima da `platform` (TEMPORAL-02-01)**: pacote `marcasalao-marketing-platform` (`0.1.0`) com entrypoint público [`platform/src/composition-validation-api.ts`](../../platform/src/composition-validation-api.ts), exportando em runtime exclusivamente `validateComposition(composition, project)` e em tipos `Composition`, `ProjectManifest` e `CompositionValidationReport`, com declarações TypeScript habilitadas em [`platform/tsconfig.json`](../../platform/tsconfig.json), subpaths internos bloqueados pelo mapa `exports` em [`platform/package.json`](../../platform/package.json) e suíte dedicada em [`platform/tests/composition-validation-api.test.ts`](../../platform/tests/composition-validation-api.test.ts).
- **R001 — OutputProfiles e OutputPlan interno**: catálogo de perfis em [`platform/src/output-profiles/`](../../platform/src/output-profiles/), contrato [`output-plan-contract.ts`](../../platform/src/output-plan-contract.ts), schema, resolvedor e validadores integrados em `e86f3c9`, após reconciliação em `8e17785`. Os cinco [exemplos de OutputPlan](../../platform/examples/output-plans/) estão versionados em LF, com regra explícita em [`platform/.gitattributes`](../../platform/.gitattributes). OutputPlan continua interno: não amplia o entrypoint público de validação nem integra esses planos ao Temporal.
- **CLIs existentes**: `content:validate-project`, `content:validate-composition`, `content:profiles` e `content:plan-output`, além de `build`, `typecheck`, `test`, `test:contracts` e `clean` em [platform/package.json](../../platform/package.json).
- **CI da plataforma**: [`.github/workflows/platform-validation.yml`](../../.github/workflows/platform-validation.yml), `Validar contratos da platform`, matriz Ubuntu e Windows × Node 22 e 24.
- **Runtime do núcleo**: Node `>=22 <25`, TypeScript compilado para JavaScript, motor de schema apenas em desenvolvimento.
- **Correção de contratos da PR #6**: integrada em 06/11/2026 pelo merge commit `0c97c2a`. A distinção entre "main anterior" e "correção pendente" que esta página mantinha foi retirada porque a main já contém o comportamento corrigido.
- **TEMPORAL-01**: piloto de orquestração em [`orchestration/temporal/`](../../orchestration/temporal/README.md), planejado em [`docs/planejamento/TEMPORAL-01-piloto-de-orquestracao.md`](../planejamento/TEMPORAL-01-piloto-de-orquestracao.md) e protegido por CI específico em [`.github/workflows/temporal-pilot-ci.yml`](../../.github/workflows/temporal-pilot-ci.yml).
- **PR #7 — contexto integrado**: [PR #7](https://github.com/Jonatasbottaro/marcasalao-marketing/pull/7) integrada à main pelo merge `fbd222d996527f6cf226051a8526f932accd7e5e` em 08/11/2026. `docs/contexto/` (`README.md`, `ESTADO-ATUAL.md`, `PROXIMOS-PASSOS.md` e `HANDOFF.md`) passou a pertencer à main e é fato integrado, não proposta em revisão. A branch `codex/atualiza-contexto-projeto` pode continuar existindo sem representar trabalho pendente; a branch remota não foi excluída.

### Em branch pública

Registrar aqui apenas o que continua fora da main, conforme o Git real:

- **BeatPlan**: branch `codex/core-beat-plan-v1`, checkpoint `bade62e3a720a853e6f3d18b52aa46bf544979a4`, **branch-only**: `git merge-base --is-ancestor` contra `origin/main` em `e86f3c9` devolve saída 1. A branch toca `package.json`, README da platform, relatório de validação e testes de portabilidade — sobreposição que precisa de reconciliação com a main que já contém R001 antes de qualquer integração.
- **PR #1 — integração de ai-memory**: [PR #1](https://github.com/Jonatasbottaro/marcasalao-marketing/pull/1), aberta. Fora do escopo técnico deste estado; não considerá-la integrada por associação.

Nada acima está integrado, por mais que o trabalho exista e tenha evidência própria.

### Planejado ou documentado

- **R002 e R003**: sem documento próprio no repositório. A única ocorrência na main é o §14 do planejamento do TEMPORAL-01, que os declara não iniciados e não integrados.
- **VisualStyle, VisualAnchor, AssetManifest, AudioPlan, RenderPlan e adaptadores**: conceitos registrados em [`docs/decisoes/`](../decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md). Nenhum tem implementação na main. O núcleo já contém projeto, composição, fronteira pública de validação e R001 (catálogo, OutputPlan interno, resolvedor, validadores e CLIs); isso não implementa esses conceitos nem um renderizador.
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

Nada fora dessa lista está ratificado. Permanecem bloqueados, sem autorização: Worker de produção dedicado à composição, cliente Temporal de validação, `workflow.start` da aplicação, Workflow ID de composição, `WorkflowIdReusePolicy`, `WorkflowIdConflictPolicy`, colisão de Workflow ID, `contentHash`, replay formal, gate Elephant–Goldfish de TEMPORAL-02, integração final completa de TEMPORAL-02, combinação de OutputPlan ou BeatPlan com Temporal, TEMPORAL-04, mídia, fornecedores e deploy.

- Commit técnico: `f5842107a0f307b4cc208c15fc4509c6d7d31f72`, ancestral da main consultada em `e86f3c9`.
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

### Limites atuais

- Worker efêmero, cliente do ambiente de teste, chamadas a `workflow.start` e IDs de execução existem **somente nos testes desta fatia**.
- Worker de produção dedicado à composição: **ausente**.
- Cliente Temporal de validação e `workflow.start` no código da aplicação: **ausentes**.
- Workflow ID canônico da aplicação, `WorkflowIdReusePolicy`, `WorkflowIdConflictPolicy` e tratamento/testes de colisão de composição: **ausentes**; não confundir com os IDs efêmeros dos testes nem com o piloto TEMPORAL-01.
- `contentHash`: **fora de TEMPORAL-02**; sem canonicalização adicionada.
- Replay formal desta fatia: **não executado nem aprovado**; repetibilidade 7/7 não é replay.
- Elephant–Goldfish de TEMPORAL-02: **pendente**; o gate aprovado de TEMPORAL-01 não o substitui.
- Nenhum deploy e nenhuma implementação posterior autorizada.

## TEMPORAL-02

- **PRD de TEMPORAL-02 integrado e formalmente em revisão; TEMPORAL-02-01, TEMPORAL-02-02, TEMPORAL-02-03 e a fatia Workflow estão integrados tecnicamente. A fatia Workflow foi ratificada pelo titular em 2026-11-11, em escopo estrito; a implementação global, a aprovação do PRD e qualquer fatia posterior continuam não autorizadas.**
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
| BeatPlan | `codex/core-beat-plan-v1` | `bade62e3a720a853e6f3d18b52aa46bf544979a4` | `merge-base --is-ancestor` contra `origin/main` em `e86f3c9` com saída 1 em 11/11/2026; evidência histórica de CI: run [42321831284](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42321831284), completed/success nesse checkpoint | **branch-only**, sem nova homologação nesta atualização |

O antigo checkpoint `55aeecccfa38da06dfada875e75d81b265626abc` da branch `codex/catalogo-formatos-sociais` permanece registro histórico, não a referência da integração atual do R001. A reconciliação integrada inclui catálogo, contrato interno, schema, resolvedor, validadores, CLIs `content:profiles` e `content:plan-output` e exemplos LF; não amplia o export público da platform. Nenhuma branch foi integrada e nenhum teste do R001 ou BeatPlan foi executado nesta atualização documental. A presença do R001 na main não autoriza seu consumo por TEMPORAL-02 nem a integração de BeatPlan.

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

> Deliberar se o projeto permanece bloqueado ou se uma próxima fatia específica de TEMPORAL-02 será autorizada, com escopo delimitado pelo titular. A ratificação da fatia Workflow, registrada em 2026-11-11, não autoriza nenhuma fatia posterior.

O Workflow já está integrado, homologado tecnicamente e ratificado no escopo dessa fatia; não deve ser reimplementado como próxima tarefa. Permanecem **bloqueados até autorização específica**:

- Worker de produção dedicado à composição;
- cliente Temporal de validação e `workflow.start` da aplicação;
- Workflow ID, `WorkflowIdReusePolicy`, `WorkflowIdConflictPolicy` e colisão de Workflow ID de composição;
- `contentHash` e qualquer canonicalização de entrada;
- replay formal e gate Elephant–Goldfish de TEMPORAL-02;
- integração final completa de TEMPORAL-02;
- integração de BeatPlan e combinação de planos no Temporal;
- TEMPORAL-04;
- mídia, fornecedores e deploy.

Pré-condições técnicas já cumpridas, sem abrir autorização futura:

- fronteira pública da platform integrada (`TEMPORAL-02-01`);
- contrato de entrada versionado e preflight local integrados (`TEMPORAL-02-02`);
- Activity real integrada e ratificada (`TEMPORAL-02-03`), com coordenação de build no CI;
- Workflow, contrato de resultado, classificador e Retry Policy integrados e homologados tecnicamente em `f584210` e ratificados em escopo estrito pelo titular;
- evidência de 162 testes e CI Ubuntu/Windows, Node 22, exclusivamente em `f584210`, detalhada na seção da fatia Workflow;
- núcleo sem dependência Temporal.

A ratificação da fatia Workflow foi registrada pelo titular em 2026-11-11 e encerra estritamente o escopo homologado de `f584210`, sem aprovar o PRD completo. Ela não autoriza a próxima fatia: qualquer implementação posterior exige decisão específica que delimite seu escopo, e o PRD permanece em revisão.

Tarefas secundárias de consulta:

1. revisar a branch de BeatPlan frente à main que já contém R001, sem integrar ou escrever código;
2. decidir se branches já integradas podem ser arquivadas, sem exclusão automática;
3. reconferir periodicamente a ancestralidade de BeatPlan e o estado da main antes de planejar qualquer integração.

## O que não fazer agora

- não reimplementar o Workflow já integrado nem criar Worker de produção sem autorização explícita;
- não criar cliente Temporal de validação, start da aplicação, Workflow ID ou suas políticas sem autorização específica;
- não tratar a ratificação da fatia Workflow como conclusão integral de TEMPORAL-02, aprovação do PRD ou autorização de próxima fatia;
- não tratar o PRD de TEMPORAL-02 como aprovado sem decisão explícita;
- não executar replay formal ou gate Elephant–Goldfish de TEMPORAL-02 sem autorização;
- não iniciar TEMPORAL-04;
- não integrar BeatPlan nem combinar o OutputPlan já integrado com Temporal por consequência;
- não gerar prévia;
- não exportar;
- não gerar mídia;
- não instalar Qwen3.8;
- não integrar Higgsfield;
- não alterar campanhas;
- não publicar conteúdo;
- não executar deploy.

## O que esta atualização não verificou

Esta atualização é exclusivamente documental e registra a ratificação da fatia Workflow comunicada pelo titular em 2026-11-11: não executou instalação de dependências, build, typecheck ou testes e não alterou código, CI, campanhas ou mídia. As evidências de 162 testes e repetibilidade 7/7 foram obtidas na homologação anterior de `f584210`, não no HEAD posterior `e86f3c9`; a integração de R001 foi conferida por ancestralidade e conteúdo, sem nova homologação técnica. Não foram executados replay formal, Elephant–Goldfish de TEMPORAL-02 ou deploy.

Preserva-se a evidência histórica de TEMPORAL-02-03: suíte local Windows com Node 22, 145 testes aprovados em 52s, e CI Ubuntu/Windows no commit `db84270ad3e51eecb0b562fcdf3a7e36941288ab` (runs [42902255503](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42902255503) e [42902338737](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42902338737)). Não é execução desta atualização.

Estado remoto de publicações e rascunhos no Postiz, execução de ComfyUI, implantação das integrações no servidor e novas jornadas do Salao02 não foram consultados nem executados.
