# Próximos passos

Antes de escolher uma tarefa, reconfira [ESTADO-ATUAL.md](ESTADO-ATUAL.md), a main remota e as PRs. A lista abaixo organiza trabalho possível; não autoriza produção, publicação ou a execução automática de todas as etapas.

## 1. Elaborar o PRD de TEMPORAL-02

Este é o único próximo passo técnico registrado em [ESTADO-ATUAL.md](ESTADO-ATUAL.md): orquestrar um único passo real do núcleo, sem mídia e sem antecipar TEMPORAL-04. A integração da correção de contratos que ocupava esta posição foi concluída na main pelo merge commit `0c97c2a`, e TEMPORAL-01 está integrado, aprovado e com CI verde — nenhuma das duas segue trabalho pendente.

Pré-condições:

- TEMPORAL-01 integrado — **cumprido**;
- contexto atualizado e integrado pela PR #7 — **cumprido**;
- escolha explícita do passo real do núcleo — **pendente**;
- contrato de entrada e saída pequeno — **pendente**;
- nenhuma dependência de fornecedor — **requisito**;
- autorização do titular — **pendente**.

O cumprimento das duas primeiras pré-condições não concede autorização automática para TEMPORAL-02: a autorização do titular continua necessária.

Critérios de conclusão do PRD:

- um passo real, um contrato de entrada e um de saída, sem combinar OutputPlan e BeatPlan;
- política de retry, timeout e colisão de `workflowId` declarada antes de qualquer implementação;
- nada de prévia, exportação, mídia ou deploy no escopo;
- o documento não inicia implementação, não escolhe fornecedor e não instala modelo.

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
