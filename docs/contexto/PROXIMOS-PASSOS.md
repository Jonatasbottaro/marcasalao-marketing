# Próximos passos

Antes de escolher uma tarefa, reconfira [ESTADO-ATUAL.md](ESTADO-ATUAL.md), a main remota e as PRs. A lista abaixo organiza trabalho possível; não autoriza produção, publicação ou a execução automática de todas as etapas.

## 1. Concluir a integração da correção dos contratos

Conferir a PR de correção indicada no estado atual, seu HEAD, os checks e eventuais mudanças posteriores à revisão. A integração é uma tarefa própria; esta atualização documental não a executa.

Critérios de conclusão:

- o GitHub registra a integração e a main contém o comportamento corrigido;
- o schema discrimina as cenas e o corpus estrutural é executado por um motor real;
- os casos de URL revisados concordam e o diagnóstico do gate funciona também em falha;
- a matriz do HEAD integrado passa;
- ESTADO-ATUAL.md é atualizado para retirar a distinção entre main anterior e correção pendente.

Se houver squash ou rebase, registre o commit que efetivamente entrou na main; não exija que os hashes originais continuem sendo ancestrais.

## 2. Reconciliar o BeatPlan existente

Inspecionar a branch de BeatPlan indicada no estado atual antes de escrever código novo. Comparar contratos, validação, relatórios, scripts e testes com a versão integrada da correção.

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

## Critério para encerrar uma tarefa

Entregar o comportamento ou documento alterado, a referência Git, as verificações realizadas e as limitações. Registrar a próxima ação concreta no contexto, preservando o histórico e o trabalho das outras branches.
