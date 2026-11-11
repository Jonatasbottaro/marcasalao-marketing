# Próximos passos

Antes de escolher uma tarefa, reconfira [ESTADO-ATUAL.md](ESTADO-ATUAL.md), a main remota e as PRs. A lista abaixo organiza trabalho possível; não autoriza produção, publicação ou a execução automática de todas as etapas.

## 1. Deliberar sobre a próxima fatia de TEMPORAL-02

> Manter o projeto bloqueado ou autorizar uma próxima fatia específica de TEMPORAL-02, com escopo delimitado pelo titular. A ratificação da fatia Workflow foi registrada em 11/11/2026 e não autoriza nenhuma fatia posterior.

A main consultada em 11/11/2026 é `d5761b1f37d1a5b5e55e2f1b7422c969e6194957`, contendo as fatias técnicas de validação de composição, a integração do R001 e o BeatPlan v1 interno. Marcos preservados:

- **TEMPORAL-02-01**: fronteira pública mínima da `platform`, integrada em `f202377fac721aff1d4143a2598f76c03062f0ac`;
- **TEMPORAL-02-02**: `CompositionValidationWorkflowInput` e preflight local, integrados em `29b40783320360350e59a13e39f49a60d2308507`;
- **TEMPORAL-02-03**: Activity real [`validateCompositionActivity`](../../orchestration/temporal/src/activities/composition-validation-activity.ts), integrada em `db84270ad3e51eecb0b562fcdf3a7e36941288ab`, com ratificação estrita registrada em `8f94e0205b470b46da918d78f8136fafa9a2286a`;
- **Fatia Workflow**: [`validateCompositionWorkflow`](../../orchestration/temporal/src/workflows/composition-validation-workflow.ts), [`CompositionValidationWorkflowResult`](../../orchestration/temporal/src/workflows/composition-validation-result.ts), [classificador de falhas](../../orchestration/temporal/src/workflows/composition-validation-failure-classifier.ts) e Retry Policy canônica do PRD integrados e homologados tecnicamente em `f5842107a0f307b4cc208c15fc4509c6d7d31f72`, com ratificação do titular registrada em 11/11/2026;
- **BeatPlan v1 interno**: [`beat-plan-contract.ts`](../../platform/src/beat-plan-contract.ts), [`beat-plan.schema.json`](../../platform/schemas/beat-plan.schema.json), `BeatPlanValidationReport` em [`validation-report.ts`](../../platform/src/validation-report.ts), [`validate-beat-plan.ts`](../../platform/src/validate-beat-plan.ts), [`validate-beat-plan-cli.ts`](../../platform/src/validate-beat-plan-cli.ts) e [dois exemplos](../../platform/examples/beat-plans/), reconciliados em `7d919fc208ac4dfeebe5b0b65a959171e5f093f2` e integrados pelo merge `d5761b1f37d1a5b5e55e2f1b7422c969e6194957`. Integração **técnica e interna**: não amplia a API pública, não se combina com OutputPlan e não entra no Temporal.

A evidência da fatia Workflow é de **17 testes novos, 162 testes aprovados, zero falhas, zero ignorados e repetibilidade 7/7**, exclusivamente em `f584210`. O CI da [branch técnica, run 42950735743](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42950735743), e da [main nesse SHA, run 42953193438](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42953193438), está verde em Ubuntu e Windows, Node 22. Não são testes dos HEADs posteriores `e86f3c9` e `d5761b1` nem foram repetidos nesta atualização documental. As evidências anteriores de cada fatia e os limites estão em [ESTADO-ATUAL.md](ESTADO-ATUAL.md) e no [README do Temporal](../../orchestration/temporal/README.md).

A evidência do BeatPlan v1 é de **626 testes aprovados, zero falhas e zero skips** na matriz de quatro ambientes — Ubuntu Node 22, Ubuntu Node 24, Windows Node 22 e Windows Node 24 —, com CI da [branch reconciliada, run 43034990448](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43034990448), em `7d919fc`, e da [main, run 43099977731](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43099977731), em `d5761b1`. Esses números pertencem a esses commits e não devem ser atribuídos a um commit documental posterior. O detalhe por componente, as regras e as fronteiras estão em [ESTADO-ATUAL.md](ESTADO-ATUAL.md) e no [README da platform](../../platform/README.md).

A fatia Workflow de TEMPORAL-02 está tecnicamente integrada e homologada no commit `f584210` e **ratificada pelo titular em 11/11/2026**. A ratificação abrange exclusivamente `validateCompositionWorkflow`, `CompositionValidationWorkflowResult`, `classifyCompositionActivityFailure`, a chamada tipada de `validateCompositionActivity`, os resultados `valid`, `invalid` e `failed`, a Retry Policy canônica do PRD, a classificação sanitizada de falhas, os testes puros, os testes de fronteira e os testes com `TestWorkflowEnvironment`, o Worker efêmero usado exclusivamente nos testes e o CI verde em Ubuntu e Windows, Node 22.

A ratificação não aprova o PRD completo e não autoriza nova implementação. Nada fora dessa lista foi ratificado: cliente Temporal de validação, Worker de produção, `workflow.start` da aplicação, Workflow ID e suas políticas, colisão, `contentHash`, replay formal e o gate Elephant–Goldfish seguem bloqueados, como abaixo.

O [PRD de TEMPORAL-02](../planejamento/TEMPORAL-02-validacao-de-composition.md) permanece formalmente em revisão, sem aprovação global. TEMPORAL-02 não está concluído integralmente, e nenhuma implementação posterior foi autorizada. Não reimplementar o Workflow já integrado nem definir antecipadamente qual será a próxima fatia.

Continuam estritamente bloqueados até autorização específica:

- Worker de produção dedicado à composição;
- cliente Temporal de validação;
- `workflow.start` da aplicação;
- Workflow ID de composição;
- `WorkflowIdReusePolicy` e `WorkflowIdConflictPolicy` de composição;
- colisão de Workflow ID;
- replay formal;
- gate Elephant–Goldfish de TEMPORAL-02;
- integração final completa de TEMPORAL-02;
- combinação BeatPlan × OutputPlan;
- BeatPlan no Temporal e combinação de OutputPlan e outros planos no Temporal;
- renderização e adaptadores;
- `VisualStyle`, `VisualAnchor`, `AssetManifest` completo, `AudioPlan` e `RenderPlan`;
- mídia;
- fornecedores;
- TEMPORAL-04;
- deploy.

Worker efêmero, cliente, `workflow.start` e IDs usados nos testes desta fatia não são implementação desses componentes na aplicação. Replay formal não foi executado nem aprovado, e o gate Elephant–Goldfish de TEMPORAL-01 não vale como aprovação de TEMPORAL-02. `contentHash` continua fora de TEMPORAL-02.

As pré-condições técnicas já cumpridas — fronteira pública, input/preflight, Activity ratificada, Workflow ratificado em escopo estrito, Retry Policy exercitada e núcleo sem dependência Temporal — não substituem a decisão de governança. A ratificação da fatia Workflow não abre autorização automática: qualquer próxima implementação exige decisão separada do titular, com escopo explícito.

## 2. Deliberar sobre uma futura combinação entre Composition, BeatPlan, OutputPlan e Temporal

> Deliberar separadamente, antes de qualquer nova implementação, se haverá uma futura combinação entre Composition, BeatPlan, OutputPlan ou Temporal.

A revisão da branch de BeatPlan frente ao R001 **foi concluída e a integração também**: o R001 está integrado desde `e86f3c9ef939ac7536ecf39a65cf4f6ee97e4b52` (reconciliação `8e17785a5634167f8abdaebacb8388276b909cab`) e o BeatPlan v1 foi reconciliado em `7d919fc208ac4dfeebe5b0b65a959171e5f093f2` e integrado pelo merge `d5761b1f37d1a5b5e55e2f1b7422c969e6194957`. Não há branch de BeatPlan pendente de integração nem segunda implementação paralela a iniciar. As branches `codex/core-beat-plan-v1` e `codex/reconcilia-beat-plan-v1` permanecem apenas como histórico e não foram excluídas.

O que já está integrado e não deve ser refeito:

- OutputProfiles, OutputPlan interno, resolvedor, validadores e CLIs `content:profiles` e `content:plan-output`, com cinco exemplos de planos em LF;
- BeatPlan v1 interno: contrato, schema draft-07, `BeatPlanValidationReport`, `validateBeatPlan(beatPlan, composition, project)` com delegação a `validateProjectManifest` e `validateComposition`, CLI `content:validate-beat-plan`, dois exemplos em LF e testes de schema, validador, CLI e exemplos;
- a fronteira pública da `platform` continua restrita a `validateComposition` e aos tipos `Composition`, `ProjectManifest` e `CompositionValidationReport`; BeatPlan e OutputPlan não ganham export no entrypoint raiz nem subpath público.

Critérios para qualquer deliberação futura:

- tratar a combinação como decisão nova e explícita do titular, com escopo delimitado, e não como consequência da integração técnica;
- distinguir estrutura de semântica e apontar verificações de schema necessárias antes de qualquer trabalho autorizado;
- preservar exemplos de projetos, relatórios determinísticos e a política de LF;
- apresentar achados e dependências, sem escolher ferramenta de geração ou renderização por consequência;
- manter o núcleo sem dependência Temporal e sem regra de marca no core.

Permanecem bloqueados até autorização específica: combinação BeatPlan × OutputPlan; BeatPlan no Temporal; TEMPORAL-04; renderização; adaptadores; `VisualStyle`; `VisualAnchor`; `AssetManifest` completo; `AudioPlan`; `RenderPlan`; mídia; fornecedores; deploy. Os bloqueios de TEMPORAL-02 listados no passo 1 continuam integralmente válidos e não são aliviados pela integração do BeatPlan. Nenhuma próxima fatia é escolhida automaticamente por esta lista.

A integração técnica do BeatPlan não concede aprovação editorial, autorização de gravação nem de publicação, e não ratifica seu uso no Temporal.

## 3. Provar o segundo consumidor real

Preparar uma configuração da Multitrack Hub a partir das fontes existentes, mantendo a fixture genérica para testar variações de idioma e formato.

Critérios de conclusão:

- o mesmo núcleo valida os consumidores sem condicionais de marca;
- tema, domínio, assets, CTA e políticas são dados do projeto;
- configurações não inventam funcionalidades nem importam autorizações de outra marca;
- os fluxos de produção existentes continuam identificados como integrações separadas.

## 4. Preparar um piloto mínimo de composição

Definir uma cena com mídia e texto editável no mesmo intervalo, necessidade presente no roteiro da NS-001. Fazer primeiro um desenho pequeno do contrato e da compatibilidade com a v1.

Critérios de conclusão:

- corrigir texto não exige regenerar o visual;
- tempo, conteúdo e referências de assets têm uma única origem identificável;
- um adaptador de teste comprova entradas, saídas e falhas sem serviço pago;
- política de áudio e inspeção técnica são verificáveis;
- qualquer produção real do piloto respeita as aprovações específicas da campanha.

Não é necessário implementar todos os planos conceituais antes dessa prova. O piloto continua sendo trabalho possível, não autorizado: depende de decisão específica do titular, e os bloqueios de adaptadores, renderização e mídia registrados no passo 2 permanecem válidos.

## 5. Separar as decisões editoriais da execução técnica

Para a NS-001, tratar as pendências apontadas nos documentos da própria campanha. Uma evidência técnica aprovada não aprova o briefing, o hook, o roteiro ou a publicação.

Na próxima validação funcional, registrar o commit executado, alterações locais, ambiente, fixture, comandos, resultados e evidências. Não atribuir retroativamente um commit à execução antiga.

## Tarefas secundárias permitidas

1. Reconferir a main e as PRs abertas antes de propor qualquer integração; R001 e BeatPlan v1 já estão integrados na referência consultada `d5761b1`, e nenhuma combinação entre planos está autorizada.
2. Decidir se branches já integradas podem ser arquivadas. Esta lista não autoriza exclusão de branch nem de conteúdo.

Os limites do que não fazer agora estão em [ESTADO-ATUAL.md](ESTADO-ATUAL.md); não repeti-los aqui.

## Critério para encerrar uma tarefa

Entregar o comportamento ou documento alterado, a referência Git, as verificações realizadas e as limitações. Registrar a próxima ação concreta no contexto, preservando o histórico e o trabalho das outras branches.
