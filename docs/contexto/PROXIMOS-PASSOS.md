# Próximos passos

Antes de escolher uma tarefa, reconfira [ESTADO-ATUAL.md](ESTADO-ATUAL.md), a main remota e as PRs. A lista abaixo organiza trabalho possível; não autoriza produção, publicação ou a execução automática de todas as etapas.

A **regra permanente de armazenamento** em [AGENTS.md](../../AGENTS.md) é normativa para toda tarefa: raiz única `C:/Repos/marcasalao-marketing`, artefatos auxiliares somente em `.workspace/` por categoria e tarefa, validação de contenção antes de criar arquivo, limpeza ao final e handoff com confirmação textual. A orientação de segurança de worktrees (conferir sessão ativa, `git worktree move`/`remove`, nunca `rm -rf` em worktree registrada, autorização do titular para mover ou remover) faz parte dessa regra.

Para as próximas rodadas, o titular prefere agrupar código, integração, testes e documentação de um mesmo resultado em um prompt de entrega. Inclua os pontos de verificação dentro da execução e preserve o escopo de autorização de cada etapa.

## 1. Deliberar sobre a próxima fatia de TEMPORAL-02

> Manter o projeto bloqueado ou autorizar uma próxima fatia específica de TEMPORAL-02, com escopo delimitado pelo titular. A ratificação da fatia Workflow foi registrada em 11/11/2026 e não autoriza nenhuma fatia posterior.

A main conferida em 11/11/2026 está em `2c409676e58e4e118d865821b9a0cbdd93a22364`. O último commit técnico do núcleo é `d5761b1f37d1a5b5e55e2f1b7422c969e6194957`, com R001 e BeatPlan v1 integrados. Os seis commits posteriores atualizam documentação e governança. A limpeza de 14 branches remotas autorizada pelo titular ficou registrada em `3c44ae4`. A PR #1 (`codex/ai-memory-integration`) é a única aberta na leitura. Em 12/11/2026 o piloto técnico local R002 (vídeo sem áudio, fora do núcleo) foi integrado pelo merge `b7ed1d9bbf397f5e9f14bfddc62c67aa0d4f5cf9` com o corretivo `0ac4bde8e5096ecdf4913a48ad453e066346b213`; não altera `platform/`, `orchestration/` nem os bloqueios abaixo. Também em 12/11/2026 a **execução local de TEMPORAL-02** (cliente, Worker local, CLIs, replay formal e gate Elephant–Goldfish, em `orchestration/temporal/`) foi integrada pelo merge `5376890974d4baf49b341297a9b7b0071a680dc6` a partir de `codex/temporal-02-execucao-local` (`63d04d5`), por pedido explícito do titular; escopo estritamente local, sem alterar os bloqueios de produção abaixo.

- **TEMPORAL-02-01**: fronteira pública mínima da `platform`, integrada em `f202377fac721aff1d4143a2598f76c03062f0ac`;
- **TEMPORAL-02-02**: `CompositionValidationWorkflowInput` e preflight local, integrados em `29b40783320360350e59a13e39f49a60d2308507`;
- **TEMPORAL-02-03**: Activity real [`validateCompositionActivity`](../../orchestration/temporal/src/activities/composition-validation-activity.ts), integrada em `db84270ad3e51eecb0b562fcdf3a7e36941288ab`, com ratificação estrita registrada em `8f94e0205b470b46da918d78f8136fafa9a2286a`;
- **Fatia Workflow**: [`validateCompositionWorkflow`](../../orchestration/temporal/src/workflows/composition-validation-workflow.ts), [`CompositionValidationWorkflowResult`](../../orchestration/temporal/src/workflows/composition-validation-result.ts), [classificador de falhas](../../orchestration/temporal/src/workflows/composition-validation-failure-classifier.ts) e Retry Policy canônica do PRD integrados e homologados tecnicamente em `f5842107a0f307b4cc208c15fc4509c6d7d31f72`, com ratificação do titular registrada em 11/11/2026;
- **BeatPlan v1 interno**: [`beat-plan-contract.ts`](../../platform/src/beat-plan-contract.ts), [`beat-plan.schema.json`](../../platform/schemas/beat-plan.schema.json), `BeatPlanValidationReport` em [`validation-report.ts`](../../platform/src/validation-report.ts), [`validate-beat-plan.ts`](../../platform/src/validate-beat-plan.ts), [`validate-beat-plan-cli.ts`](../../platform/src/validate-beat-plan-cli.ts) e [dois exemplos](../../platform/examples/beat-plans/), reconciliados em `7d919fc208ac4dfeebe5b0b65a959171e5f093f2` e integrados pelo merge `d5761b1f37d1a5b5e55e2f1b7422c969e6194957`. Integração **técnica e interna**: não amplia a API pública, não se combina com OutputPlan e não entra no Temporal.

A evidência da fatia Workflow é de **17 testes novos, 162 testes aprovados, zero falhas, zero ignorados e repetibilidade 7/7**, exclusivamente em `f584210`. O CI da [branch técnica, run 42950735743](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42950735743), e da [main nesse SHA, run 42953193438](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42953193438), está verde em Ubuntu e Windows, Node 22. Não são testes dos HEADs posteriores `e86f3c9`, `d5761b1`, `c50dc86`, `9908f3b` e `79fd5da` nem foram repetidos nesta atualização documental. As evidências anteriores de cada fatia e os limites estão em [ESTADO-ATUAL.md](ESTADO-ATUAL.md) e no [README do Temporal](../../orchestration/temporal/README.md).

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

A revisão da branch de BeatPlan frente ao R001 **foi concluída e a integração também**: o R001 está integrado desde `e86f3c9ef939ac7536ecf39a65cf4f6ee97e4b52` (reconciliação `8e17785a5634167f8abdaebacb8388276b909cab`) e o BeatPlan v1 foi reconciliado em `7d919fc208ac4dfeebe5b0b65a959171e5f093f2` e integrado pelo merge `d5761b1f37d1a5b5e55e2f1b7422c969e6194957`. Não há branch de BeatPlan pendente de integração nem segunda implementação paralela a iniciar. `codex/reconcilia-beat-plan-v1` continua existindo apenas como histórico; `codex/core-beat-plan-v1` foi **excluída do remoto** na limpeza de 11/11/2026, por ser superseded, com o checkpoint preservado em ref local de arquivo.

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

## 6. Preparar a proposta de autorização para execução real em produção da validação de Composition no Temporal

> Próxima entrega recomendada após a integração da execução local de TEMPORAL-02 (12/11/2026, merge `5376890`): **preparar a proposta completa de autorização para execução real (produção/remota) da validação de Composition no Temporal, sem iniciar implementação automaticamente.**

A proposta deve delimitar escopo, componentes, riscos, evidências exigidas e critérios de ratificação, reaproveitando o que já está integrado e ratificado (fronteira pública, input/preflight, Activity, Workflow em escopo estrito, Retry Policy, execução local completa com replay e gate Elephant–Goldfish) e o precedente de gates do R002 e da execução local (reprodução limpa, inspeção técnica real, prova transacional, hashes e documentação no mesmo marco). É trabalho de proposta: Worker de produção, servidor remoto, namespace de produção e deploy continuam bloqueados; a execução real depende de decisão explícita e separada do titular.

## Tarefas secundárias permitidas

1. Reconferir a main e as PRs abertas antes de propor qualquer integração; R001, BeatPlan v1, a regra permanente de armazenamento, a orientação de segurança de worktrees e o contexto atualizado já estão integrados, e nenhuma combinação entre planos está autorizada.
2. Decidir se as cinco branches documentais já integradas podem ser arquivadas, sem exclusão automática: `atualiza-contexto-beat-plan-v1`, `atualiza-contexto-regra-armazenamento`, `reconcilia-beat-plan-v1`, `regra-armazenamento-workspace` e `seguranca-worktrees-workspace`. A limpeza de 11/11/2026 já removeu as 13 superseded e a obsoleta `.worktrees`; o detalhe e os SHA de recuperação estão em [ESTADO-ATUAL.md](ESTADO-ATUAL.md).
3. Decidir o destino da PR #1 (`ai-memory-integration`) como tarefa própria: é a única branch com trabalho real pendente (19 arquivos ausentes da main, incluindo um workflow de CI novo), conflita em `.ai-memory.toml`, `.gitignore` e `AGENTS.md` e está 82 commits atrás. Exige reconciliação com o `AGENTS.md` atual e autorização específica do CI.
4. Não reintroduzir a convenção `.worktrees/`: a branch que a propunha foi excluída por contradizer a regra permanente, e a orientação de segurança aproveitável já está integrada sob `.workspace/` por `79fd5da`.

Os limites do que não fazer agora estão em [ESTADO-ATUAL.md](ESTADO-ATUAL.md); não repeti-los aqui.

## Critério para encerrar uma tarefa

Entregar o comportamento ou documento alterado, a referência Git, as verificações realizadas e as limitações. Registrar a próxima ação concreta no contexto, preservando o histórico e o trabalho das outras branches. Cumprir o handoff obrigatório da regra de armazenamento em [AGENTS.md](../../AGENTS.md), incluindo a confirmação textual de que nada foi criado ou mantido fora de `C:/Repos/marcasalao-marketing` e a declaração de qualquer exceção como bloqueio.
