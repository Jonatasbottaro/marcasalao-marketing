# Próximos passos

Antes de escolher uma tarefa, reconfira [ESTADO-ATUAL.md](ESTADO-ATUAL.md), a main remota e as PRs. A lista abaixo organiza trabalho possível; não autoriza produção, publicação ou a execução automática de todas as etapas.

## 1. Deliberar sobre próxima fatia de TEMPORAL-02 após ratificação de TEMPORAL-02-03

> Deliberação do titular sobre manter o projeto bloqueado ou autorizar uma próxima fatia de TEMPORAL-02.

As três fatias técnicas iniciais de validação de composição estão integradas na `main`:

- **TEMPORAL-02-01** (fronteira pública mínima da `platform`, pacote `marcasalao-marketing-platform@0.1.0`, entrypoint [`platform/src/composition-validation-api.ts`](../../platform/src/composition-validation-api.ts)), integrada em `f202377fac721aff1d4143a2598f76c03062f0ac` (fechamento documental em `f1da1f9d0b62bf94be44779b8db4e00610dd7ee5`), com 315 testes aprovados e CI verde em Ubuntu e Windows, Node 22 e 24 ([run 42738388930](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42738388930));
- **TEMPORAL-02-02** (contrato de solicitação versionado `CompositionValidationWorkflowInput`, códigos de falha da Via A e preflight local `preflightCompositionValidationInput` / `startAfterCompositionPreflight` em [`orchestration/temporal/src/composition-validation/`](../../orchestration/temporal/src/composition-validation/)), integrada em `29b40783320360350e59a13e39f49a60d2308507`, com 17 novos testes locais verdes e suíte integral de 137 testes aprovada no CI em Ubuntu e Windows, Node 22 ([run 42748899305](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42748899305));
- **TEMPORAL-02-03** (Activity real `validateCompositionActivity` em [`orchestration/temporal/src/activities/composition-validation-activity.ts`](../../orchestration/temporal/src/activities/composition-validation-activity.ts), consumo de `marcasalao-marketing-platform`, contrato dedicado `CompositionValidationActivityInput`, chamada direta `validateComposition(composition, project)`, retorno de `CompositionValidationReport`, `valid: false` como retorno normal de domínio, conversão sanitizada para `TEMPORAL_COMPOSITION_ACTIVITY_FAILED` e coordenação de build no CI), integrada em `db84270ad3e51eecb0b562fcdf3a7e36941288ab` e ratificada pelo titular exclusivamente para a Activity e suas fronteiras públicas, com 145 testes aprovados e CI verde em Ubuntu e Windows, Node 22 ([run 42902338737](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42902338737)).

O [PRD de TEMPORAL-02](../planejamento/TEMPORAL-02-validacao-de-composition.md) permanece formalmente em revisão (aprovação global não concedida), a implementação global de `TEMPORAL-02` não está autorizada e nenhuma nova fatia técnica posterior foi autorizada.

Continuam estritamente bloqueados:

- Workflow (`validateCompositionWorkflow`);
- Worker dedicado de composição;
- cliente Temporal real e `workflow.start`;
- retries reais e timeout real;
- colisão de Workflow ID;
- replay;
- gate Elephant–Goldfish de TEMPORAL-02;
- OutputPlan, BeatPlan e R001;
- TEMPORAL-04;
- mídia, fornecedores e deploy.

Pré-condições cumpridas:

- fronteira pública da platform integrada (`marcasalao-marketing-platform@0.1.0`, entrypoint [`platform/src/composition-validation-api.ts`](../../platform/src/composition-validation-api.ts));
- contrato de entrada versionado e preflight local integrados (`CompositionValidationWorkflowInput`);
- Activity real integrada e ratificada no escopo estrito (`validateCompositionActivity`);
- coordenação de build no CI Temporal validada;
- CI Ubuntu e Windows verde na `platform` (run [42738388930](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42738388930)) e em `orchestration/temporal/` (run [42902338737](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42902338737), 145 testes aprovados);
- zero dependência Temporal na `platform`.

Pré-condição ainda necessária:

- nova autorização explícita do titular delimitando se e quando uma próxima fatia (como o Workflow puro) deve ser iniciada. A ratificação de TEMPORAL-02-03 foi restrita à Activity e não abre automaticamente fatias futuras.

## 2. Revisar as branches públicas de R001 e BeatPlan

Inspecionar a branch do R001 (catálogo de perfis, OutputPlan e as CLIs `content:profiles` e `content:plan-output`) e a branch de BeatPlan antes de escrever código novo. Comparar contratos, validação, relatórios, scripts e testes com os contratos de projeto e composição já integrados na main.

Critérios de conclusão:

- identificar o que já existe e sua relação com Composition;
- preservar as correções e o CI ao resolver sobreposições;
- validar o schema em motor real e separar estrutura de semântica;
- manter os exemplos dos projetos e os relatórios determinísticos;
- apresentar uma mudança revisável, sem escolher ferramenta de geração ou renderização por consequência.

Não iniciar uma segunda implementação paralela só porque o BeatPlan ainda não aparece na main.

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

Não é necessário implementar todos os planos conceituais antes dessa prova.

## 5. Separar as decisões editoriais da execução técnica

Para a NS-001, tratar as pendências apontadas nos documentos da própria campanha. Uma evidência técnica aprovada não aprova o briefing, o hook, o roteiro ou a publicação.

Na próxima validação funcional, registrar o commit executado, alterações locais, ambiente, fixture, comandos, resultados e evidências. Não atribuir retroativamente um commit à execução antiga.

## Tarefas secundárias permitidas

1. Confirmar no Git se R001 e BeatPlan continuam branch-only antes de tratar qualquer um deles como integrado.
2. Decidir se branches já integradas podem ser arquivadas. Esta lista não autoriza exclusão de branch nem de conteúdo.

Os limites do que não fazer agora estão em [ESTADO-ATUAL.md](ESTADO-ATUAL.md); não repeti-los aqui.

## Critério para encerrar uma tarefa

Entregar o comportamento ou documento alterado, a referência Git, as verificações realizadas e as limitações. Registrar a próxima ação concreta no contexto, preservando o histórico e o trabalho das outras branches.
