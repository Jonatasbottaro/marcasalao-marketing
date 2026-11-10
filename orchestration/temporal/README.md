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
| `npm test` | os 120 testes (unidades, integração, estáticos e de processo) — 44 s medidos |
| `npm run test:unit` | 104 testes que não precisam de servidor (núcleo, Activities, cliente, endereço, fronteira e processo) — 13 s medidos |
| `npm run test:integration` | 16 testes da camada de Workflow: 11 de integração com `TestWorkflowEnvironment` (inclui retry, timeout, replay e colisão de `workflowId`) + 5 de classificação de falha — 42 s medidos |
| `npm run pilot:local` | servidor efêmero do SDK, `requestId` de demonstração, resultado impresso, tudo derrubado no `finally` |
| `npm run pilot:worker` | worker real contra `127.0.0.1:7233` (ou `--address <host:porta>` local) |
| `npm run pilot:run` | cliente real: inicia o Workflow e imprime o `TemporalPilotResult` |

Testes por arquivo: núcleo 59 (`pilot-input` 17, `pilot-plan` 12, `pilot-result` 11,
`pilot-outcome` 8, `non-retryable-codes` 7, `failures` 4), `pilot-activities` 9,
`pilot-start` 14, `local-address` 8, `pilot-boundary` 7, `entrypoints` 7,
`pilot-failure-signal` 5, `content-pilot-workflow` 11.

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
- **Não resolvido:** entregar `SIGINT`/`Ctrl+C` a um `npm run pilot:worker` rodando solto
  no Windows. O que está medido é outro caminho: `pilot:local` e a suíte de integração
  derrubam worker e ambiente no próprio `finally`, e importar os pontos de entrada não
  deixa handle ativo (os testes de processo veem o filho terminar sozinho). Nenhum teste
  nem o CI dependem de sinal de sistema operacional.

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

## Próximo gate

A revisão **Elephant–Goldfish** de TEMPORAL-01 foi executada fora deste pacote e as três
ressalvas prioritárias dela estão fechadas aqui: colisão de `workflowId` medida na suíte
de integração, conjunto não retryable com fonte única e CI específico do pacote. Entre
TEMPORAL-01 e TEMPORAL-02 não há aprovação simulada. Menor passo seguinte: orquestrar um
passo real do núcleo em TEMPORAL-02, somente quando houver autorização.
