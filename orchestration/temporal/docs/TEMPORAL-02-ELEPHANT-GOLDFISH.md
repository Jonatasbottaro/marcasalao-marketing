# TEMPORAL-02 — Gate Elephant–Goldfish da execução local

Revisão executada na mesma entrega da execução local (branch
`codex/temporal-02-execucao-local`, 12/11/2026), sobre o código efetivamente
escrito, não sobre a proposta. Escopo revisado: cliente de aplicação, Workflow ID,
políticas, colisão, Worker local, lifecycle, CLI, execução local real, replay e
barreiras estáticas. Produção, deploy e servidor remoto permanecem fora.

## Elephant — revisão adversarial

| # | Ponto | Veredito | Evidência |
| --- | --- | --- | --- |
| 1 | Preflight antes do start | OK | `startCompositionValidation` passa por `startAfterCompositionPreflight`; o CLI roda `preflightCompositionValidationInput` antes de `Connection.connect`. Testes: preflight inválido/sensível/grande com zero chamadas de start e zero execuções no servidor. |
| 2 | Payload persistido na history | OK com limite documentado | O servidor persiste o argumento do Workflow no start; por isso o preflight é a fronteira que impede conteúdo sensível/grande de chegar à history. Documentos de exemplo são fictícios. |
| 3 | Sanitização | OK | Falhas de start devolvem só código fixo; CLI usa mensagens fixas em stderr e JSON sem payload em stdout; worker anuncia só Task Queue, namespace e endereço local; zero `console.*` na camada nova (barreira estática). |
| 4 | Workflow ID | OK | `composition-validation-<requestId>`, função pura no cliente; sem data, aleatoriedade, hash ou contentHash; barreira estática garante construtor único em `src/`. |
| 5 | Colisão | OK | `REJECT_DUPLICATE` + `FAIL`; `WorkflowExecutionAlreadyStartedError` → `TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT` (código canônico do PRD §23); sem nova execução, sem Activity, sem `CompositionValidationWorkflowResult`; medido com execução aberta e concluída. |
| 6 | Políticas de reuso/conflito | OK | Valores confirmados nos `.d.ts` e em runtime do SDK 1.25.0; iguais ao precedente TEMPORAL-01 e ao PRD §20. |
| 7 | invalid versus failed | OK | `invalid` é retorno de domínio com relatório intacto (exit 1); `failed` carrega `failureCode`, `validation: null`, `completedSteps: []` (exit 3); sem remapeamento. |
| 8 | Retries | OK | Retry Policy ratificada intacta (`maximumAttempts: 2`, `nonRetryableErrorTypes` só `TEMPORAL_COMPOSITION_ACTIVITY_FAILED`); colisão e preflight fora dela. |
| 9 | Timeout | OK | `startToCloseTimeout: '5 seconds'` intacto; esgotamento medido na suíte existente com time-skipping (`TEMPORAL_COMPOSITION_TIMEOUT`). |
| 10 | Replay | OK | `Worker.runReplayHistory` com fixture versionado normalizado (11 eventos, dados fictícios, sem timestamps/runIds de máquina); replay de history fresca também passa; sensibilidade comprovada: workflow divergente de mesmo nome rejeita com `[TMPRL1100] Nondeterminism error`. |
| 11 | Worker lifecycle | OK | Criação separada de execução; importar não abre handles (teste de processo); `Worker.create` falho fecha a conexão; sinais só no `run`. |
| 12 | Shutdown | OK | `worker.shutdown()` + `await run` + `connection.close()` em finally no runner, no script local e nos testes; dispose remove listeners de sinal. |
| 13 | Imports proibidos | OK | Barreiras estáticas ampliadas: platform sem `@temporalio`; Workflow sem cliente/worker/fs/rede/env/relógio/aleatoriedade/contentHash/OutputPlan/BeatPlan; camada nova sem import direto da platform e sem `console.*`. |
| 14 | Cliente cai | OK | `Connection.connect` falho → JSON sanitizado `TEMPORAL_COMPOSITION_CONNECTION_FAILED`, exit 5; erro de transporte no start classificado por código, sem mensagem variável. |
| 15 | Worker encerra | OK | `run()` resolve após shutdown; processo filho termina sem handle residual (teste de processo). |
| 16 | Compatibilidade da Retry Policy | OK | Colisão é conflito de start do cliente (via B), nunca falha da Activity; não entra em `nonRetryableErrorTypes`. |

Bloqueadores encontrados: nenhum remanescente. Dois defeitos reais foram
corrigidos durante a entrega: (a) normalização WKT do fixture de replay
(`{seconds,nanos}` → Timestamp ISO / Duration string, incluindo campos zerados
`{}` e `firstWorkflowTaskBackoff`); (b) o workflow divergente de teste precisava
exportar o mesmo nome do Workflow integrado para provar não-determinismo, e não
apenas falha de inicialização por tipo.

## Goldfish — simplicidade e removibilidade

- Seis módulos novos em `src/` (start, worker, lifecycle, três entrypoints), todos
  pequenos e com funções puras onde possível; nenhuma classe nova.
- Cliente fino: preflight + opções + start + classificação; Worker fino: fábrica +
  runner; lifecycle isolado em módulo próprio.
- Zero dependência nova: SDK 1.25.0 já instalado basta; `@temporalio/testing` já
  era devDependency.
- Contratos não duplicados: reusa `CompositionValidationWorkflowInput`,
  preflight, códigos da via A, `CompositionValidationWorkflowResult`, códigos da
  via D e a guarda `checkLocalAddress` de TEMPORAL-01.
- Removível sem tocar a platform: `platform/` não foi alterado nesta entrega
  (diff vazio), e a Activity continua consumindo só o entrypoint público.
- Sem framework genérico de animação/orquestração, sem configuração além de
  address/namespace locais.

Observações cosméticas (backlog, não bloqueiam):

1. Os parsers de flags dos dois CLIs são parecidos mas deliberadamente separados
   (conjuntos de flags diferentes); unificar só se um terceiro CLI surgir.
2. `COMPOSITION_VALIDATION_NAMESPACE` vive no módulo de start (cliente) e é
   importado pelo worker; o precedente TEMPORAL-01 guarda namespace no módulo de
   Workflow — manter como está evita tocar a fatia ratificada.
3. `printStartFailure` mapeia `startFailed` para o exit 5 (técnico); poderia ganhar
   exit próprio se o PRD definir código de start desconhecido no futuro.

## Veredito

Gate **aprovado** para a execução local: nenhum bloqueador funcional aberto.
A entrega segue para revisão e integração controlada; produção remota, deploy,
Worker persistente e namespace de produção permanecem não autorizados.