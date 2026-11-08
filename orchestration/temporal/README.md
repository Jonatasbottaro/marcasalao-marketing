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
um teste estático continua vigiando essa fronteira.

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
conteúdo de payload sai pelo registro.

## Execução do Workflow

```
validatePilotRequest → preparePilotExecution → finalizePilotExecution
```

- `startToCloseTimeout = 5 seconds`; retry `initialInterval 1s`, `backoffCoefficient 2`,
  `maximumInterval 5s`, `maximumAttempts 3`.
- Violação de contrato é **não retryable** (`nonRetryableErrorTypes` com os seis códigos
  de entrada + `TEMPORAL_PILOT_ACTIVITY_NON_RETRYABLE`) e encerra na primeira tentativa.
- Falha transitória é retryable; timeout é retryable até esgotar as três tentativas e aí
  vira `TEMPORAL_PILOT_TIMEOUT`.
- Task Queue `marketing-temporal-pilot-v1`, namespace `default`,
  `workflowId = temporal-pilot-<requestId>`.
- No `start`: `WorkflowIdReusePolicy.REJECT_DUPLICATE` + `WorkflowIdConflictPolicy.FAIL`.
  Repetir `requestId` devolve `TEMPORAL_PILOT_WORKFLOW_ID_CONFLICT` em vez de criar uma
  execução paralela silenciosa.
- O Workflow não toca disco, rede, relógio, aleatoriedade, ambiente, console nem timer
  nativo, e obtém as Activities por `proxyActivities` — nunca como função local.

## Comandos

Requer Node 22 (`engines: ">=22 <25"`). O `npm` do PATH desta máquina é Node 26, então
use o Node 22 instalado pelo WinGet antes de rodar qualquer gate.

| Comando | O que faz |
| --- | --- |
| `npm run build` | `tsc` para `dist/` (o bundle do Workflow é gerado pelo webpack na criação do worker) |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | as 108 telas (unidades, integração, estáticos e de processo) — 39 s |
| `npm run test:unit` | 93 telas que não precisam de servidor (núcleo, Activities, cliente, endereço, fronteira e processo) |
| `npm run test:integration` | 15 telas da camada de Workflow: 10 de integração com `TestWorkflowEnvironment` (inclui retry, timeout e replay) + 5 de classificação de falha |
| `npm run pilot:local` | servidor efêmero do SDK, `requestId` de demonstração, resultado impresso, tudo derrubado no `finally` |
| `npm run pilot:worker` | worker real contra `127.0.0.1:7233` (ou `--address <host:porta>` local) |
| `npm run pilot:run` | cliente real: inicia o Workflow e imprime o `TemporalPilotResult` |

Telas por arquivo: núcleo 52 (entrada 17, plano 12, resultado 11, falha 8, códigos 4),
Activities 9, cliente 10, endereço 8, fronteira estática 7, processo 7, sinal de falha 5,
integração do Workflow 10.

## Rodada local medida (dois processos)

Com um servidor local em `127.0.0.1:7233` e `npm run pilot:worker` rodando:

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
  `@types/node` 24.19.2 (MIT). O grafo transitivo instalado tem 148 pacotes, todos de
  licença permissiva (MIT, Apache-2.0, BSD-2/3, ISC, 0BSD, Unlicense), com uma exceção de
  **dados**: `caniuse-lite`, CC-BY-4.0, trazido pelo webpack embutido no SDK.
  `platform/` continua com zero dependência de runtime nova.
- `node_modules/`, `dist/` e `gate-logs/` são ignorados por este pacote.

## Limitações

- `createTimeSkipping` usa o Test Server de pular-tempo, documentado pelo SDK como menos
  fiel ao servidor completo; a fidelidade completa é o `pilot:local` sobre `createLocal`.
- O replay cobre a história gravada nesta execução e não prova compatibilidade com
  histórias de versões futuras do Workflow.
- As Activities não produzem efeito real de negócio: são puras por contrato, e é isso que
  torna a idempotência estrutural e não uma promessa.

## Próximo gate

Entre TEMPORAL-01 e TEMPORAL-02 está a revisão **Elephant–Goldfish**, que não é
implementada aqui nem tem aprovação simulada. Menor passo seguinte: revisar este pacote
e, aprovado, orquestrar um passo real do núcleo em TEMPORAL-02.
