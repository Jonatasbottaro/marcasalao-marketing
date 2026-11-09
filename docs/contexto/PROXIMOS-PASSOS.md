# Próximos passos

Antes de escolher uma tarefa, reconfira [ESTADO-ATUAL.md](ESTADO-ATUAL.md), a main remota e as PRs. A lista abaixo organiza trabalho possível; não autoriza produção, publicação ou a execução automática de todas as etapas.

## 1. Revisar e decidir sobre a aprovação do PRD de TEMPORAL-02

O PRD de TEMPORAL-02 está integrado à main em `33b46ce54649fc60340c2e85b15d0b39ad112cff`, no arquivo [`docs/planejamento/TEMPORAL-02-validacao-de-composition.md`](../planejamento/TEMPORAL-02-validacao-de-composition.md). A elaboração do PRD — que ocupava esta posição — foi concluída documentalmente. A implementação **não** foi iniciada.

O PRD planeja um único passo real, `validate-composition`: validar uma Composition v1 contra um ProjectManifest válido. A Activity real ainda não existe; a função `validateComposition(composition, project)` é exportada por módulo interno, sem fronteira pública estável entre `platform` e `orchestration/temporal`.

Três estados permanecem distintos e não se deduzem um do outro:

- integração do PRD **não** equivale à aprovação;
- aprovação do PRD **não** equivale à autorização de implementação;
- a implementação depende de nova decisão explícita do titular.

Critérios da decisão:

1. aceitar ou rejeitar o passo `validate-composition`;
2. aceitar ou ajustar os limites 64/256/384 KiB;
3. escolher a estratégia da fronteira pública;
4. aceitar ou ajustar duas tentativas;
5. confirmar o gate Elephant–Goldfish obrigatório;
6. manter TEMPORAL-04 fora;
7. manter R001, OutputPlan e BeatPlan fora.

Pré-condições:

- TEMPORAL-01 integrado — **cumprido**;
- contexto atualizado e integrado pela PR #7 — **cumprido**;
- PRD de TEMPORAL-02 integrado à main — **cumprido** em `33b46ce`;
- escolha explícita do passo real — **registrada no PRD**, sujeita a aprovação;
- contrato de entrada e saída pequeno — **documentado no PRD**, sujeito a aprovação;
- nenhuma dependência de fornecedor — **requisito**;
- aprovação do PRD — **pendente**;
- autorização do titular — **pendente**.

Não iniciar implementação nesta tarefa: aprovar o PRD, se acontecer, ainda não autoriza código.

### Decisões ainda pendentes

- forma do entrypoint público;
- pacote local, workspace ou artefato compilado;
- limites finais após medição dos exemplos;
- `contentHash` fora desta fatia;
- formato final do resultado;
- estratégia de logs;
- aprovação do PRD;
- autorização da implementação.

São recomendações e alternativas registradas no PRD, não decisões aprovadas. A fronteira pública é gate obrigatório **antes** de qualquer Activity; o gate Elephant–Goldfish é obrigatório **depois** da futura implementação e **antes** da integração na main. Nenhum dos dois foi executado.

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
