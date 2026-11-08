# TEMPORAL-01 — piloto de orquestração com Temporal

- Status: especificação canônica do incremento; implementada nesta branch
- Branch: `codex/temporal-01-piloto-orquestracao`, base `0c97c2a` (= `origin/main`)
- Escopo: o piloto técnico mínimo descrito abaixo. Nada além disso.
- Dependências de decisão: `docs/decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md` (portabilidade e determinismo) e `docs/decisoes/MKT-PLATFORM-001-plataforma-multiprojeto.md` (núcleo multiprojeto sem fornecedor)

## 1. Por que esta spec existe

Não havia planejamento versionado de TEMPORAL-01 na `main` antes deste incremento. A
busca `git grep -niE 'TEMPORAL-01|TEMPORAL-02|TEMPORAL-04|@temporalio|orquestração'`
na base `0c97c2a` devolveu apenas uma ocorrência de "idempotência" em
`00-briefings/campanhas/NS-001/VALIDACAO-FUNCIONAL-AGENDA.md:197`, sem relação com
orquestração. Esta especificação curta é, portanto, o artefato de planejamento do
piloto, limitada ao que TEMPORAL-01 precisa provar.

## 2. Conflito de dependências registrado

A instrução permanente do projeto é "não adicionar dependências de runtime" e "se
surgir necessidade concreta de nova dependência: parar, explicar, não instalar
silenciosamente". O briefing de TEMPORAL-01 pede o SDK TypeScript do Temporal.

O conflito existe e a resolução registrada aqui é a mais restritiva que satisfaz os
dois:

- `platform/` permanece com **zero dependências de runtime** e sem qualquer import de
  `@temporalio`;
- todas as dependências novas ficam confinadas ao pacote isolado
  `orchestration/temporal/`, com `package-lock.json` próprio e versões exatas;
- `@temporalio/testing` é `devDependency` (só testes); o resto é runtime do piloto.

Ou seja: a dependência entra onde o pedido a colocou, e o núcleo continua exatamente
como estava.

## 3. Fronteira arquitetural

| Camada | Pasta | Conhece Temporal? |
| --- | --- | --- |
| Núcleo do piloto (contratos, validação, chave de idempotência, montagem do resultado) | `src/pilot-core/` | **Não.** Importa apenas `node:` e tipos próprios. |
| Orquestração | `src/workflows/`, `src/activities/`, `src/worker/`, `src/client/` | Sim. |

Regras verificadas por teste:

- nenhum arquivo de `src/pilot-core/` importa `@temporalio/*`;
- nenhum arquivo de `platform/` importa `@temporalio/*` ou conhece Workflow,
  Activity ou Task Queue;
- as Activities são funções puras: recebem entrada serializável, devolvem saída
  serializável, sem estado global mutável, sem I/O.

O Workflow chama Activities **por proxy** (`proxyActivities`), nunca como função
local direta.

## 4. Contratos do piloto

`TemporalPilotInput` — `schemaVersion`, `requestId`, `projectId`, `operation`,
`payload`.

- `schemaVersion`: fixo em `1`; outro valor é erro não retryable.
- `requestId` e `projectId`: obrigatórios, casa com `^[a-z0-9][a-z0-9._-]{0,63}$`.
- `operation`: restrito a `validate-pilot-request`.
- `payload`: no máximo 4 chaves de um conjunto nomeado, valores primitivos curtos,
  sem objeto aninhado, sem array, sem binário, sem caminho absoluto, sem segredo.

`TemporalPilotResult` — `schemaVersion`, `requestId`, `projectId`, `status`,
`completedSteps`, `failureCode`, `output`.

- `status`: `completed`, `rejected` ou `failed`.
- `completedSteps`: ordem estável, subconjunto de `validate`, `prepare`, `finalize`.
- `failureCode`: `null` em `completed`; sempre presente nos demais.
- Em `rejected`, `output` é `null` (a entrada não foi adiante).

Determinismo: o resultado é função apenas da entrada e do comportamento das
Activities. Nenhuma Activity lê relógio, aleatoriedade, ambiente ou disco.

## 5. Passos do Workflow

```
validatePilotRequest → preparePilotExecution → finalizePilotExecution
```

`contentPilotWorkflow` coordena os três, trata falha conhecida e devolve
`TemporalPilotResult`. Nome real escolhido pelas convenções do repositório
(camelo + sufixo `Workflow`, como os contratos existentes).

## 6. Idempotência

Chave: `requestId + operation`.

Como as Activities são puras, a idempotência é estrutural: a mesma chave produz a
mesma saída, sem contador, sem artefato novo, sem ID aleatório, sem versão nova, sem
reordenação. O `workflowId` derivado (`temporal-pilot-<requestId>`) impede duplicidade
no nível do servidor: um segundo `start` concorrente com o mesmo id falha de forma
explícita em vez de sobrescrever.

## 7. Task Queue, namespace e workflow id

- Task Queue: `marketing-temporal-pilot-v1`, exclusiva do piloto.
- Namespace: `default`, local.
- `workflowId`: `temporal-pilot-<requestId>` — derivado da entrada, não do relógio.
- Nenhum acesso a Temporal Cloud, a namespace remoto ou a Task Queue de produção.

## 8. Timeouts e retries

Por Activity: `startToCloseTimeout = '5 seconds'` — o menor valor da faixa pedida
(5–30 s), suficiente porque as Activities não fazem I/O. `scheduleToCloseTimeout` não
é definido: não há fila longa no piloto. Workflow Execution Timeout não é definido:
sem necessidade concreta.

Retry policy: `initialInterval 1s`, `backoffCoefficient 2`, `maximumInterval 5s`,
`maximumAttempts 3`. Sem retry infinito.

Diferença registrada: **timeout** é falha técnica retryable e consome tentativas;
**violação de contrato** é não retryable e encorre `rejected`/`failed` na primeira
tentativa. Retry não corrige entrada inválida.

## 9. Códigos de erro

| Código | Classe |
| --- | --- |
| `TEMPORAL_PILOT_SCHEMA_UNSUPPORTED` | não retryable |
| `TEMPORAL_PILOT_REQUEST_ID_REQUIRED` | não retryable |
| `TEMPORAL_PILOT_PROJECT_ID_REQUIRED` | não retryable |
| `TEMPORAL_PILOT_OPERATION_INVALID` | não retryable |
| `TEMPORAL_PILOT_PAYLOAD_INVALID` | não retryable |
| `TEMPORAL_PILOT_INPUT_INVALID` | não retryable (guarda-chuva) |
| `TEMPORAL_PILOT_ACTIVITY_TRANSIENT_FAILURE` | retryable |
| `TEMPORAL_PILOT_ACTIVITY_NON_RETRYABLE` | não retryable |
| `TEMPORAL_PILOT_TIMEOUT` | retryable até esgotar `maximumAttempts` |
| `TEMPORAL_PILOT_WORKFLOW_FAILED` | falha do próprio Workflow |
| `TEMPORAL_PILOT_WORKFLOW_ID_CONFLICT` | colisão de `workflowId`, não silenciosa |

Os dez primeiros são os sugeridos no briefing; `WORKFLOW_ID_CONFLICT` é necessário
para cumprir "não permitir colisão silenciosa".

Erros carregam `code` + mensagem sanitizada. A mensagem nunca inclui payload, valor
de campo, caminho absoluto, credencial ou stack trace.

## 10. Observabilidade

Campos permitidos: `workflowId`, `requestId`, `projectId`, `operation`, `status`,
`activity`, `attempt`, `failureCode`. Nada de conteúdo integral do payload, dado
pessoal, token ou texto de campanha. Sem stack de observabilidade, sem OpenTelemetry.

## 11. Execução local

- `src/worker/main.ts`: Worker mínimo nos três passos do piloto, shutdown gracioso,
  nenhum efeito colateral ao ser importado, não roda em build nem typecheck.
- `src/client/main.ts`: cliente que aponta para `127.0.0.1:7233` (ou `--address`),
  inicia com `workflowId` derivado e imprime o resultado estruturado.
- `npm run pilot:local`: sobe o servidor local efêmero do próprio SDK, roda um
  `requestId` de demonstração, imprime o resultado e derruba tudo no `finally`.

O binário do servidor de teste fica no cache do usuário (`%TEMP%` no Windows,
`$TMPDIR` em Unix), nunca no repositório. Nada é baixado para dentro do checkout.

## 12. Testes

Integração do Workflow com `TestWorkflowEnvironment`, serial por ambiente, com
`teardown` e `shutdown` em `finally`. Unidades para núcleo e Activities. Estáticos
para as proibições do Workflow (`fs`, rede, `Date.now`, `Math.random`, `console`) e
para a fronteira do núcleo. Replay com `Worker.runReplayHistory`.

## 13. Limitações

- `createTimeSkipping` usa o Test Server de pular-tempo (do SDK Java), que o próprio
  SDK documenta como menos fiel ao servidor completo. Ele existe aqui para que retry
  e timeout não esperem segundos reais; a fidelidade completa fica no `pilot:local`
  sobre `createLocal`.
- Replay cobre a história gravada nesta execução; não prova compatibilidade com
  histórias de versões futuras do Workflow.

## 14. Fora de escopo de TEMPORAL-01

Orquestrar OutputPlan, BeatPlan, prévia, exportação, renderização, imagem, áudio,
vídeo ou campanha. A verificação conjunta desses componentes é **TEMPORAL-04**.
R001, R002 e R003 não são iniciados nem integrados aqui. O piloto é agnóstico ao tipo
de mídia.

## 15. Gates posteriores

- **Elephant–Goldfish**: revisão independente entre TEMPORAL-01 e TEMPORAL-02. Não é
  implementada aqui e não tem aprovação simulada.
- **Qwen3.8**: segue como família indicada para futuro executor de texto. Nada de
  instalar, baixar modelo, criar adapter, inferir ou acoplar ao Workflow.

## 16. Segurança

Nenhum `.env` aberto ou impresso; nenhum token, chave, certificado, senha, cookie,
service account, credencial Temporal Cloud ou Firebase; nenhum dado pessoal. Config
local usa somente localhost e defaults. Sem produção, sem staging, sem serviço
externo.
