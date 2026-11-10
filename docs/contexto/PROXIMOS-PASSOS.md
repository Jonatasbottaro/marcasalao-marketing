# Próximos passos

Antes de escolher uma tarefa, reconfira [ESTADO-ATUAL.md](ESTADO-ATUAL.md), a main remota e as PRs. A lista abaixo organiza trabalho possível; não autoriza produção, publicação ou a execução automática de todas as etapas.

## 1. Decidir se TEMPORAL-02-02 está autorizado

> Decidir se TEMPORAL-02-02 está autorizado.

A primeira fatia técnica, **TEMPORAL-02-01** (fronteira pública mínima da `platform`, pacote `marcasalao-marketing-platform@0.1.0`, entrypoint [`platform/src/composition-validation-api.ts`](../../platform/src/composition-validation-api.ts)), foi integrada à main em `f202377fac721aff1d4143a2598f76c03062f0ac`, com 315 testes aprovados e CI verde em Ubuntu e Windows, Node 22 e 24 ([run 42738388930](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42738388930)).

O [PRD de TEMPORAL-02](../planejamento/TEMPORAL-02-validacao-de-composition.md) permanece em revisão (aprovação não concedida, salvo decisão explícita posterior), a implementação global de `TEMPORAL-02` não está autorizada e **TEMPORAL-02-02 ainda não está autorizado**.

`TEMPORAL-02-02` significa somente:

- contrato de entrada;
- preflight do cliente;
- medição de payload;
- rejeição antes do start;
- segurança da history.

Pré-condições cumpridas:

- PRD integrado (`33b46ce54649fc60340c2e85b15d0b39ad112cff`);
- TEMPORAL-02-01 integrado (`f202377fac721aff1d4143a2598f76c03062f0ac`);
- fronteira pública consumível (`marcasalao-marketing-platform@0.1.0`, entrypoint `composition-validation-api`);
- CI Ubuntu e Windows verde (Node 22 e 24, run `42738388930`);
- zero dependência Temporal na `platform`.

Itens ainda fora:

- Activity (`validateCompositionActivity`);
- Workflow (`validateCompositionWorkflow`);
- retries reais;
- timeout real;
- replay;
- Elephant–Goldfish de TEMPORAL-02;
- R001;
- OutputPlan;
- BeatPlan;
- TEMPORAL-04;
- mídia.

Não iniciar `TEMPORAL-02-02` nem elaborar plano de implementação sem decisão explícita do titular.

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
