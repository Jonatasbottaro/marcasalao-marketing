# Orquestração — piloto TEMPORAL-01

Pacote isolado que prova, com execução de verdade, a separação entre **núcleo
modular** e **orquestração**: um Workflow determinístico, Activities idempotentes,
entradas e saídas pequenas e versionadas, retries e timeouts explícitos, erros
estruturados, execução local e nenhum fornecedor de IA ou mídia no caminho.

Especificação canônica: [`docs/planejamento/TEMPORAL-01-piloto-de-orquestracao.md`](../../docs/planejamento/TEMPORAL-01-piloto-de-orquestracao.md).

**Este pacote não orquestra** OutputPlan, BeatPlan, prévia, exportação, renderização,
imagem, áudio, vídeo ou campanha. A verificação conjunta desses componentes é
TEMPORAL-04. O piloto é agnóstico ao tipo de mídia.

## Camadas

| Pasta | O que é | Conhece Temporal? |
| --- | --- | --- |
| `src/pilot-core/` | contratos, parse da entrada, plano, resultado, classificação de falha | **Não** — só `node:` e tipos próprios |
| `src/workflows/` | `contentPilotWorkflow` e a leitura da causa de falha dentro do sandbox | Sim |
| `src/activities/` | as três Activities puras do piloto | Sim (lança `ApplicationFailure`) |
| `src/client/` | argumentos, `workflowId`, Task Queue, políticas de reuso/colisão | Sim |
| `src/worker/`, `src/local/` | pontos de entrada de processo | Sim |
| `src/local-address.ts` | única guarda de endereço local, compartilhada por cliente e worker | Não |

`platform/` não importa nada de `@temporalio` e não foi tocado por este incremento;
um teste estático deste pacote vigia essa fronteira quando a suíte do piloto é
executada. O gate automático é
[`.github/workflows/temporal-pilot-ci.yml`](../../.github/workflows/temporal-pilot-ci.yml),
que dispara em `orchestration/temporal/**`, no planejamento de TEMPORAL-01 e no
próprio arquivo — nada de campanha ou da platform aciona este job, e
`.github/workflows/platform-validation.yml` continua sendo o gate do núcleo.

## Contratos

`TemporalPilotInput` (`schemaVersion: 1`, `requestId`, `projectId`,
`operation: validate-pilot-request`, `payload`) — cinco campos, nenhum extra.
Identificadores casa com `^[a-z0-9][a-z0-9._-]{0,63}$`; `payload` aceita só
`label` (≤ 40, sem caminho/URL/aparência de credencial), `count` (0–1000) e `flag`.

`TemporalPilotResult` — `schemaVersion`, `requestId`, `projectId`, `status`
(`completed` | `rejected` | `failed`), `completedSteps` (ordem estável),
`failureCode` (`null` só em `completed`) e `output` (`null` quando não concluiu).

A mensagem de falha é fixa por código e caminho e **nunca repete o valor recebido**:
o mesmo par de argumentos produz o mesmo resultado, e nada de absoluto, credencial ou
conteúdo de payload sai pela mensagem de falha nem pelo `TemporalPilotResult`. Essa
garantia **não cobre a história do Temporal**: o servidor persiste o argumento cru do
Workflow antes de a primeira Activity validar, então a pré-validação no cliente é a
fronteira que impede conteúdo sensível de chegar à história (§10 da spec).

## Execução do Workflow

```
validatePilotRequest → preparePilotExecution → finalizePilotExecution
```

- `startToCloseTimeout = 5 seconds`; retry `initialInterval 1s`, `backoffCoefficient 2`,
  `maximumInterval 5s`, `maximumAttempts 3`.
- Violação de contrato é **não retryable** e encerra na primeira tentativa. A lista
  `nonRetryableErrorTypes` da Retry Policy e o conjunto que classifica o resultado como
  `rejected` derivam da mesma constante, `NON_RETRYABLE_PILOT_CODES`
  (`src/pilot-core/failures.ts`): os seis códigos de entrada + `TEMPORAL_PILOT_ACTIVITY_NON_RETRYABLE`.
  Um teste estático impede que as duas representações divergam ou que um código seja
  escrito à mão em um dos dois consumidores.
- Falha transitória é retryable; timeout é retryable até esgotar as três tentativas e aí
  vira `TEMPORAL_PILOT_TIMEOUT`.
- Task Queue `marketing-temporal-pilot-v1`, namespace `default`,
  `workflowId = temporal-pilot-<requestId>`.
- No `start`: `WorkflowIdReusePolicy.REJECT_DUPLICATE` + `WorkflowIdConflictPolicy.FAIL`.
  Repetir `requestId` devolve `TEMPORAL_PILOT_WORKFLOW_ID_CONFLICT` em vez de criar uma
  execução paralela silenciosa. Além da rodada manual abaixo, a colisão é medida na
  suíte de integração: um segundo `start` é recusado com a execução aberta e depois de
  fechada, sem segunda chamada de Activity.
- O Workflow não toca disco, rede, relógio, aleatoriedade, ambiente, console nem timer
  nativo, e obtém as Activities por `proxyActivities` — nunca como função local.

## Comandos

Requer Node na faixa de `engines: ">=22 <25"`. Confira com `node --version` antes de
qualquer gate: se o `npm` do PATH apontar para outra major, troque para um Node da faixa
(nesta máquina o PATH traz Node 26 e os gates foram rodados com o Node 22 do WinGet).
Os números abaixo foram medidos em Node 22.23.2 / npm 10.9.8.

```bash
# a partir de orchestration/temporal/
npm ci                    # instala as versões exatas do lockfile (148 pacotes)
npm run clean             # apaga dist/ (script Node portátil)
npm run build             # compila src/ e tests/ para dist/ (tsc, NodeNext)
npm run typecheck         # tsc --noEmit
npm test                  # build + node --test "dist/tests/**/*.test.js"
```

`npm run clean` não é chamado por `test`: renomear ou apagar um teste deixa o `.js`
antigo em `dist/`, e o glob continua executando-o. Rode `clean` antes de medir contagens.

| Comando | O que faz |
| --- | --- |
| `npm run build` | `tsc` para `dist/` (o bundle do Workflow é gerado pelo webpack na criação do worker) |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | os 198 testes (unidades, integração, estáticos, processo, execução local e replay) — 47 s medidos em Node 22.23.2 |
| `npm run test:unit` | 135 testes que não precisam de servidor (núcleo, Activities, cliente, worker, endereço, fronteira e processo) |
| `npm run test:integration` | 29 testes da camada de Workflow com `TestWorkflowEnvironment` (retry, timeout, replay e colisão do piloto; colisão aberta/concluída, preflight zero-execução, espera de resultado e shutdown de TEMPORAL-02) |
| `npm run pilot:local` | servidor efêmero do SDK, `requestId` de demonstração, resultado impresso, tudo derrubado no `finally` |
| `npm run pilot:worker` | worker real contra `127.0.0.1:7233` (ou `--address <host:porta>` local) |
| `npm run pilot:run` | cliente real: inicia o Workflow e imprime o `TemporalPilotResult` |
| `npm run composition:worker` | Worker local dedicado à validação de Composition (Task Queue `composition-validation-v1`) |
| `npm run composition:validate` | cliente real de validação: preflight → start → resultado JSON; exit codes na seção TEMPORAL-02 |
| `npm run composition:validate:local` | execução local real completa (`createLocal`): valid, invalid e colisão medidos, tudo derrubado no `finally` |
| `npm run composition:replay` | replay formal da história versionada + gate de não-determinismo + replay de história fresca (3 testes) |
| `npm run test:local` | somente os testes de execução local real (`createLocal`, 3 testes) |

Testes por grupo (medidos em Node 22.23.2): `test:unit` 135; `test:integration` 29;
`test:local` 3; `composition:replay` 3; suíte de `tests/composition-validation/`
(contrato, preflight, processo, resultado e fronteiras) 28; total `npm test` 198,
zero falhas e zero skips.

## Rodada local medida (dois processos)

Registro de uma rodada medida, não um comando do pacote. Nenhum script daqui sobe o
servidor de `7233`: `pilot:local` cria um servidor efêmero em porta aleatória que morre
no `finally`. Para reproduzir os dois processos, suba um servidor local com o CLI que o
próprio SDK deixa em cache (`%TEMP%\temporal-sdk-typescript-1.25.0.exe` no Windows,
`$TMPDIR` em Unix) usando `server start-dev --headless --ip 127.0.0.1 --port 7233
--namespace default`, e rode `npm run pilot:worker` em outro processo.

Com esse servidor no ar e o worker rodando:

```
$ npm run pilot:run -- --request-id req-2001     # status completed,  exit 0
$ npm run pilot:run -- --request-id req-2001     # WORKFLOW_ID_CONFLICT, exit 1
$ npm run pilot:run -- --request-id req-2002 --project-id multitrack-hub --label fila
```

`completed` traz `completedSteps: ["validate","prepare","finalize"]` e o `output` com
`executionKey: "req-2001::validate-pilot-request"` e `workflowId: "temporal-pilot-req-2001"`.
Para uma execução nova, use um `requestId` novo — a colisão é o comportamento desejado.

Códigos de saída: `0` somente em `completed`; `1` em `rejected`, `failed`, colisão ou
recusa de argumento. A recusa acontece antes de qualquer conexão, e os testes de processo
rodam offline justamente por isso.

## Segurança e higiene

- Só localhost (`127.0.0.1`, `localhost`, `::1`); endereço remoto é recusado com o host
  nomeado. Sem Temporal Cloud, sem namespace remoto, sem produção, sem staging.
- Nenhum `.env` aberto ou impresso; nenhuma credencial, token, cookie, dado pessoal ou
  texto de campanha no código, nos testes, no diff ou na saída.
- O binário do servidor de teste fica no cache do usuário (`%TEMP%`), nunca no checkout;
  nada é baixado para dentro do repositório e o servidor local usado na verificação roda
  com persistência em memória.
- Dependências diretas exatas: `@temporalio/client`, `@temporalio/common`,
  `@temporalio/worker` e `@temporalio/workflow` em `1.25.0` (todos MIT) e
  `@temporalio/testing` como devDependency (MIT), com `typescript` 5.9.3 (Apache-2.0) e
  `@types/node` 24.19.2 (MIT). O grafo transitivo **instalado** nesta máquina tem 148
  pacotes (`npm ls --all --parseable` devolve 149 linhas, contando a raiz), enquanto o
  `package-lock.json` tem 159 entradas: 12 são binários `optional` e 11 deles são de outras
  plataformas, então não são instalados — só `@swc/core-win32-x64-msvc` entra aqui.
  Nenhuma licença copyleft no grafo. As licenças são permissivas (MIT, Apache-2.0,
  BSD-2/3, ISC, 0BSD, Unlicense), com uma exceção de **dados**: `caniuse-lite`, CC-BY-4.0,
  trazido pelo webpack embutido no SDK — é base de dados de compatibilidade de navegador,
  não código de runtime do projeto. Há ainda um registro incompleto: `unionfs@4.6.0` não
  declara `license` nem no lockfile nem no próprio `package.json`, mas distribui um texto
  `LICENSE` de domínio público (Unlicense); não é copyleft, só não está registrado nos
  metadados.
  `platform/` continua com zero dependência de runtime nova.
- `node_modules/`, `dist/` e `gate-logs/` são ignorados por este pacote.

## CI

`.github/workflows/temporal-pilot-ci.yml` roda este pacote em Node 22, na matriz
`ubuntu-latest` + `windows-latest`, com `fail-fast: false`, `permissions: contents: read`
e `timeout-minutes: 15`. Os gatilhos são `push`, `pull_request` e `workflow_dispatch`
restritos a `orchestration/temporal/**`, a
`docs/planejamento/TEMPORAL-01-piloto-de-orquestracao.md` e ao próprio arquivo, então
campanha, mídia e `platform/` não acionam este job. Os passos são
`npm ci --no-audit --no-fund`, `npm run clean`, `npm run build`, `npm run typecheck`
e `npm test`.

Nenhum passo usa segredo, sobe serviço persistente, publica artefato ou faz deploy: a
suíte inteira usa o servidor efêmero do SDK, que morre com o processo do teste. Por isso
o CI não depende de sinal manual — nem de `Ctrl+C` no Windows, que segue como limitação
abaixo.

## Limitações

- `createTimeSkipping` usa o Test Server de pular-tempo, documentado pelo SDK como menos
  fiel ao servidor completo; a fidelidade completa é o `pilot:local` sobre `createLocal`.
- O replay cobre a história gravada nesta execução e não prova compatibilidade com
  histórias de versões futuras do Workflow.
- As Activities não produzem efeito real de negócio: são puras por contrato, e é isso que
  torna a idempotência estrutural e não uma promessa.
- **Não resolvido:** entregar `SIGINT`/`Ctrl+C` a um `npm run pilot:worker` ou
  `npm run composition:worker` rodando solto no Windows. O que está medido é outro
  caminho: `pilot:local`, `composition:validate:local` e a suíte de integração
  derrubam worker e ambiente no próprio `finally`; os handlers de SIGINT/SIGTERM do
  lifecycle são exercitados em processo filho isolado (emit), e importar os pontos
  de entrada não deixa handle ativo (os testes de processo veem o filho terminar
  sozinho). Nenhum teste nem o CI dependem de sinal de sistema operacional.

## TEMPORAL-02-02 — contrato de solicitação e preflight local

Esta fatia implementa **exclusivamente** o contrato de entrada versionado e o preflight local do cliente para `TEMPORAL-02`, confinados em `src/composition-validation/`:

- `src/composition-validation/composition-validation-failures.ts`: fonte única e imutável para os três códigos da Via A (rejeição de preflight antes do `start`): `TEMPORAL_COMPOSITION_INPUT_INVALID`, `TEMPORAL_COMPOSITION_INPUT_TOO_LARGE` e `TEMPORAL_COMPOSITION_SENSITIVE_INPUT`.
- `src/composition-validation/composition-validation-input.ts`: contrato fechado `CompositionValidationWorkflowInput` (`schemaVersion: 1`, `requestId` no padrão `^[a-z0-9][a-z0-9._-]{0,63}$`, `project` e `composition`) e limites em bytes UTF-8.
- `src/composition-validation/composition-validation-preflight.ts`: `preflightCompositionValidationInput(input)` e a fronteira local `startAfterCompositionPreflight(input, start)`.

Regras e garantias desta fatia:

- **Nenhum Workflow ou Activity de TEMPORAL-02 existe ainda**: `validateCompositionActivity`, `validateCompositionWorkflow`, Worker dedicado, cliente Temporal de validação e replay ainda não foram implementados.
- **Pacote público da `platform` ainda não é consumido nesta fatia**: `project` e `composition` são verificados aqui apenas quanto a envelope, compatibilidade JSON sem perda, política estreita de conteúdo sensível e limites de bytes UTF-8. A validação semântica pelo núcleo (`validateComposition(composition, project)`) pertence à etapa futura da Activity.
- **Limites exatos em bytes UTF-8** medidos sobre a representação JSON serializada (`Buffer.byteLength(JSON.stringify(value), "utf8")`):
  - `project`: máximo de `64 KiB` (`65.536` bytes);
  - `composition`: máximo de `256 KiB` (`262.144` bytes);
  - envelope completo (`schemaVersion`, `requestId`, `project`, `composition`): máximo de `384 KiB` (`393.216` bytes).
- **Proteção da history antes do `start`**: caso `workflow.start` fosse chamado, o servidor Temporal persistiria os argumentos brutos do Workflow na history antes da execução da Activity, e um relatório sanitizado posterior não apagaria o que já entrou na history. Por isso o preflight ocorre localmente **antes do `start`** e antes de qualquer conexão: entradas inválidas, acima do limite ou com conteúdo proibido são rejeitadas sem criar execução, sem tocar em `127.0.0.1:7233` e sem invocar o callback de start.
- **Política estreita e testável (não é scanner universal de segredos)**: recusa chaves proibidas conhecidas (`password`, `passwd`, `secret`, `token`, `accessToken`, `refreshToken`, `apiKey`, `privateKey`, `clientSecret`, `authorization`, `cookie`, `serviceAccount`, sem diferenciar caixa ou separadores), URLs com `username`/`password`, caminhos absolutos (Windows, UNC, POSIX e `file://`) e referências evidentes a arquivos sensíveis (`.env`, `.env.local`, PEM, P12/PFX, chaves privadas e `service-account` JSON), preservando textos editoriais legítimos que mencionem termos como "token", "senha" ou "credenciais".
- **Mensagens sanitizadas e imutabilidade**: as mensagens são fixas por código, `path` indica apenas o local lógico (`$`, `$.schemaVersion`, `$.requestId`, `$.project`, `$.composition`, `$.project.<prohibited>`, `$.composition.<prohibited>`), **nenhum valor ou chave rejeitada é ecoado**, e o objeto de entrada jamais é mutado (quando `ok: true`, a mesma referência validada é devolvida).

## TEMPORAL-02-03 — Activity real de validação de composição

Esta fatia implementa **exclusivamente** a Activity `validateCompositionActivity`, confinada em `src/activities/composition-validation-activity.ts`:

- **Dependência local**: consome o pacote compilado `marcasalao-marketing-platform` (`file:../../platform`) exclusivamente pelo entrypoint público `composition-validation-api` (sem imports relativos de `platform/src`).
- **Contrato dedicado**: aceita `CompositionValidationActivityInput` contendo exclusivamente `project` e `composition` (desacoplado de `requestId` e do contrato de Workflow).
- **Ordem dos parâmetros**: chama estritamente `validateComposition(composition, project)` (Composition primeiro, ProjectManifest depois).
- **Sem remapeamento**: retorna diretamente o `CompositionValidationReport` emitido pela `platform`.
- **Relatórios inválidos**: relatórios com `valid: false` são retornos normais de domínio e **não lançam exceção**.
- **Erros inesperados**: falhas inesperadas na fronteira são capturadas e convertidas em `ApplicationFailure` não-retryable (`TEMPORAL_COMPOSITION_ACTIVITY_FAILED`), com mensagem sanitizada e fixa (`Composition validation activity failed unexpectedly.`), sem stack trace e sem payload bruto.
- **Pureza e isolamento**: zero rede, zero I/O de disco, zero subprocessos, zero mutação dos inputs e zero duplicação do validador.
- **Continuação do escopo restrito**: Workflow, Worker, cliente Temporal de validação, retries reais, timeouts reais e replay continuam não implementados e não autorizados.

## TEMPORAL-02 — Fatia Workflow (`validateCompositionWorkflow`)

Esta fatia implementa **exclusivamente** o Workflow determinístico e o contrato de resultado estruturado de `TEMPORAL-02` (consumindo a Activity `validateCompositionActivity` já integrada em `TEMPORAL-02-03`), confinados em `src/workflows/`:

- `src/workflows/composition-validation-result.ts`: contrato `CompositionValidationWorkflowResult`, construtores puros e constantes dos códigos de falha de execução (`TEMPORAL_COMPOSITION_ACTIVITY_FAILED`, `TEMPORAL_COMPOSITION_TIMEOUT` e `TEMPORAL_COMPOSITION_ACTIVITY_TRANSIENT_FAILURE`).
- `src/workflows/composition-validation-failure-classifier.ts`: `classifyCompositionActivityFailure(error)`, percorrendo defensivamente a cadeia de `cause` (com proteção contra ciclos) para classificar `TimeoutFailure`, `ApplicationFailure` e mapear falhas desconhecidas de forma sanitizada para `TEMPORAL_COMPOSITION_ACTIVITY_FAILED`.
- `src/workflows/composition-validation-workflow.ts`: `validateCompositionWorkflow(input)`, que chama `validateCompositionActivity` exclusivamente por `proxyActivities` tipado com a Retry Policy canônica do PRD (`startToCloseTimeout: '5 seconds'`, `initialInterval: '1 second'`, `backoffCoefficient: 2`, `maximumInterval: '2 seconds'`, `maximumAttempts: 2`, `nonRetryableErrorTypes: ['TEMPORAL_COMPOSITION_ACTIVITY_FAILED']`).

Regras e limites preservados nesta fatia (TEMPORAL-02 completo **não** está concluído):

- `valid` e `invalid` são retornos normais de domínio com `CompositionValidationReport` intacto, `projectId` e `compositionId` vindos do relatório e `completedSteps: ['validate-composition']`.
- `failed` retorna resultado sanitizado com `validation: null`, `projectId: null`, `compositionId: null`, `completedSteps: []` e `failureCode` obrigatório.
- `workflow.start`, o cliente Temporal de validação e o Worker local de validação
  **foram implementados na fatia de execução local** (seção TEMPORAL-02 — Execução
  local completa); continuam locais, sem produção e sem deploy.
- `Workflow ID` determinístico e políticas de reuso/conflito pertencem ao cliente
  (`composition-validation-<requestId>`); `contentHash` permanece fora de TEMPORAL-02.
- O replay formal de TEMPORAL-02 **foi executado e aprovado** na fatia de execução
  local, e o gate **Elephant–Goldfish de TEMPORAL-02 foi executado** nesta entrega
  (registro em `docs/TEMPORAL-02-ELEPHANT-GOLDFISH.md`), distinto do gate já
  concluído para TEMPORAL-01 abaixo.

## TEMPORAL-02 — Execução local completa (cliente, Worker, CLI e replay)

Esta fatia conecta os componentes já integrados (preflight → cliente →
`workflow.start` → Worker local → `validateCompositionWorkflow` →
`validateCompositionActivity` → `CompositionValidationWorkflowResult`) em uma
experiência **local, reproduzível e encerrável**. Não é produção: sem deploy, sem
servidor remoto, sem namespace de produção, sem Worker persistente.

Módulos novos:

| Peça | Onde |
| --- | --- |
| Workflow ID, opções de start, políticas, colisão, start e execute | [`src/client/composition-validation-start.ts`](src/client/composition-validation-start.ts) |
| CLI de validação (`--project`, `--composition`, `--request-id`, `--address`, `--namespace`, `--json`) | [`src/client/composition-validation-main.ts`](src/client/composition-validation-main.ts) |
| Fábrica e runner do Worker local (localhost-only) | [`src/worker/composition-validation-worker.ts`](src/worker/composition-validation-worker.ts) |
| Lifecycle de sinais (SIGINT/SIGTERM) com dispose | [`src/worker/composition-validation-worker-lifecycle.ts`](src/worker/composition-validation-worker-lifecycle.ts) |
| CLI do Worker | [`src/worker/composition-validation-main.ts`](src/worker/composition-validation-main.ts) |
| Execução local real (`createLocal`, três caminhos medidos) | [`src/local/composition-validation-main.ts`](src/local/composition-validation-main.ts) |
| Captura do fixture de replay (método abaixo) | [`scripts/capture-composition-replay-history.mjs`](scripts/capture-composition-replay-history.mjs) |
| Replay formal e gate de determinismo | [`tests/replay/composition-validation-replay.test.ts`](tests/replay/composition-validation-replay.test.ts) |

Contratos de execução:

- **Workflow ID**: `composition-validation-<requestId>` — função pura no cliente,
  determinística, sem data, aleatoriedade, hash ou `contentHash`; o `requestId`
  já vem validado pelo preflight. Barreira estática garante construtor único.
- **Task Queue**: `composition-validation-v1` (dedicada; não reutiliza
  `marketing-temporal-pilot-v1`). **Workflow Type**: `validateCompositionWorkflow`.
  **Namespace**: `default` configurável por `--namespace`.
- **Políticas**: `WorkflowIdReusePolicy.REJECT_DUPLICATE` +
  `WorkflowIdConflictPolicy.FAIL` (PRD §20 e precedente TEMPORAL-01). Colisão
  (execução aberta ou concluída) devolve `TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT`,
  sem nova execução, sem Activity e sem `CompositionValidationWorkflowResult`.
- **Preflight obrigatório**: nenhum start público acontece antes de
  `startAfterCompositionPreflight`; o CLI ainda roda o preflight antes de
  `Connection.connect`. Entrada inválida/sensível/grande = zero execução.
- **Endereço**: somente localhost, pela guarda compartilhada `checkLocalAddress`;
  endereço remoto é recusado antes de conectar.
- **Retry/timeout**: os valores ratificados da fatia Workflow permanecem intactos
  (`maximumAttempts: 2`, `startToCloseTimeout: '5 seconds'`); colisão e preflight
  ficam fora da Retry Policy da Activity.

Exit codes do `composition:validate` (stdout só resultado JSON, stderr só
mensagens operacionais fixas, zero stack e zero payload):

| Exit | Significado |
| --- | --- |
| 0 | `valid` |
| 1 | `invalid` (domínio; decisão documentada: domínio inválido não é erro técnico) |
| 2 | uso/argumento/arquivo/preflight (antes de qualquer conexão) |
| 3 | `failed` (execução esgotada ou não retryable) |
| 4 | colisão de Workflow ID |
| 5 | conexão ou falha técnica de start sanitizada |

O `composition:worker` usa exit 2 para uso inválido e exit 1 para falha técnica;
anuncia somente Task Queue, namespace e endereço local.

### Replay formal

Método: `node scripts/capture-composition-replay-history.mjs` (após `npm run build`)
sobe `createLocal`, executa o Workflow integrado com Worker e cliente reais sobre
os exemplos fictícios da platform, grava a history e **normaliza apenas campos
dependentes da máquina**: timestamps (`eventTime`) viram `2026-01-01T00:00:00.000Z`,
runIds viram um UUID fixo e WKT de duração viram string (`"5s"`, inclusive campos
zerados `{}` e `firstWorkflowTaskBackoff`). O fixture versionado
[`tests/replay/fixtures/composition-validation-valid.history.json`](tests/replay/fixtures/composition-validation-valid.history.json)
(11 eventos) não contém documentos sensíveis, caminhos locais nem relógio de
computador. O teste replaya o fixture com `Worker.runReplayHistory`, replaya uma
história fresca gerada na própria execução e prova sensibilidade: um Workflow de
teste com o mesmo nome e duas chamadas de Activity rejeita o fixture com
`[TMPRL1100] Nondeterminism error`. Não há alegação de compatibilidade com
histórias de versões futuras do Workflow.

### Gate Elephant–Goldfish

Executado nesta entrega e registrado em
[`docs/TEMPORAL-02-ELEPHANT-GOLDFISH.md`](docs/TEMPORAL-02-ELEPHANT-GOLDFISH.md):
16 pontos adversariais verificados com evidência de teste, revisão de
simplicidade/removibilidade e backlog cosmético. Nenhum bloqueador aberto.

## Próximo gate

A revisão **Elephant–Goldfish** de TEMPORAL-01 foi executada fora deste pacote e as três
ressalvas prioritárias dela estão fechadas aqui: colisão de `workflowId` medida na suíte
de integração, conjunto não retryable com fonte única e CI específico do pacote. Entre
TEMPORAL-01 e TEMPORAL-02 não há aprovação simulada. A revisão **Elephant–Goldfish de
TEMPORAL-02** foi executada nesta entrega sobre a execução local (registro em
[`docs/TEMPORAL-02-ELEPHANT-GOLDFISH.md`](docs/TEMPORAL-02-ELEPHANT-GOLDFISH.md)).
Menor passo seguinte: revisão e integração controlada desta execução local; produção
remota e deploy continuam não autorizados.
