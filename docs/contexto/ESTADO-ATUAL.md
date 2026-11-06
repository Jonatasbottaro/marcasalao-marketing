# Estado atual do projeto

## Referências desta atualização

- Data da consulta: 06/11/2026, America/Sao_Paulo.
- Repositório: [Jonatasbottaro/marcasalao-marketing](https://github.com/Jonatasbottaro/marcasalao-marketing).
- Código da main consultado: [c2a8ca2f9a738f84b501b9590c8181697c55d61a](https://github.com/Jonatasbottaro/marcasalao-marketing/commit/c2a8ca2f9a738f84b501b9590c8181697c55d61a).
- Correções de contratos revisadas: [PR #6](https://github.com/Jonatasbottaro/marcasalao-marketing/pull/6), HEAD [b0988cb767a1420cb53de086a15968f173383183](https://github.com/Jonatasbottaro/marcasalao-marketing/commit/b0988cb767a1420cb53de086a15968f173383183).
- Na consulta, a PR #6 estava aberta e não integrada. A main não contém essas correções.

Os hashes identificam o código usado como referência, não uma promessa de que as branches permanecerão nesses pontos. Reconferir o remoto antes de trabalhar; um commit apenas documental posterior não muda a referência do código analisado.

## Núcleo reutilizável

| Área | Na main consultada | Na PR #6 revisada |
| --- | --- | --- |
| ProjectManifest | Contrato, schema, validador, relatório, CLI e exemplos | Regras lexicais de caminhos compartilhadas e regressões ampliadas |
| Composition v1 | Composição declarativa por cenas e vínculo com o projeto | Schema discriminado por tipo de cena e união discriminada no TypeScript |
| Validação | Funções puras, relatórios com códigos, erros e warnings | Corpus compartilhado e execução real dos schemas em motor draft-07 |
| URLs e caminhos | Implementação anterior às correções de paridade | Autoridade conferida antes da normalização; credenciais distintas de @ em caminho/query/fragmento |
| Exemplos | Marca Salão e fixture-project | Mesmos exemplos, testados contra schema e core |
| CI da platform | Ainda não existe na main consultada | Matriz Linux/Windows com Node 22/24 e prova do ramo de falha |
| Runtime | Node >=22 <25, TypeScript compilado para JavaScript | Faixa preservada; motor de schema apenas em desenvolvimento |

A PR #6 tem sete commits e 22 arquivos, restritos à platform e a .github/workflows/platform-validation.yml. O workflow anterior de previews não faz parte da alteração. A revisão desta sequência recomenda sua integração, mas isso não equivale a merge realizado.

## Evidência das correções

Execuções do HEAD revisado:

- [CI de pull_request: 42268435331](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42268435331): quatro jobs completed/success.
- [CI de push: 42268425001](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42268425001): quatro jobs completed/success.
- Matriz em cada execução: Ubuntu e Windows, Node 22 e Node 24.
- Log do job Ubuntu + Node 22 consultado: 308 testes aprovados, zero falhas e zero dispensados; prova do código 7 e da falha de tee confirmada.
- Revisão independente local em Linux + Node 24: typecheck aprovado; 307 testes aprovados, zero falhas e um dispensado porque a cópia de revisão não tinha metadados Git.
- Casos de @ fora da autoridade, autoridade vazia, barras extras e credenciais foram reexecutados no harness da PR e apresentaram os resultados esperados nos dois motores.
- O wrapper de diagnóstico foi ensaiado com saída 7, saída 0 e falha de tee: log, resumo e retorno preservados conforme o caso.

Limitação registrada: uma execução local antiga teve 286 testes aprovados e seis falhas sem nomes preservados. A causa não foi determinada; as correções de URL e de captura de logs não foram apresentadas como explicação dessa ocorrência. O histórico está no README da platform da PR.

## Trabalho existente fora da main

| Referência | Evidência consultada | Situação |
| --- | --- | --- |
| codex/core-beat-plan-v1, commit [68b93dc](https://github.com/Jonatasbottaro/marcasalao-marketing/commit/68b93dcb30b4c51c9f0ced9b7558fad9e22d5cf7) | Comparação com a main: um commit adiciona contrato, schema, validador, CLI, exemplos e testes de BeatPlan | Não integrado; a comparação usa como base o mesmo código anterior à PR #6 |
| [PR #1](https://github.com/Jonatasbottaro/marcasalao-marketing/pull/1) | Metadados: rascunho de integração de ai-memory | Fora da revisão de contratos; não considerar integrada por associação |

A comparação da branch de BeatPlan toca também package.json, README, validation-report e testes de portabilidade, arquivos que a PR #6 altera. Reconciliar esses trabalhos e revisar os testes antes de iniciar outra implementação de BeatPlan. A branch de BeatPlan não foi homologada nesta atualização de contexto.

## Limites do núcleo

- Composition é um contrato declarativo; não é execução do roteiro nem renderização.
- Renderer undecided é aceito e produz um warning; nenhum renderizador do novo núcleo foi implementado nas referências acima.
- Metadata approved é estado técnico. Não concede aprovação editorial, gravação ou publicação.
- Existência física de assets, licenças, inspeção final e prontidão para publicar não são comprovadas por valid: true.
- scenes vazio é aceito pela v1. Exigir uma cena mínima seria evolução de requisito.
- Os casos estruturais do corpus comparam os dois motores. Vínculos entre documentos, IDs de cena duplicados e overflow da soma permanecem verificações semânticas do core.
- Os planos completos de estilo, âncora visual, assets, áudio, renderização e os adaptadores não estão implementados na main consultada.
- A segunda configuração do núcleo ainda é uma fixture genérica. A Multitrack Hub já tem fluxos próprios no repositório, mas ainda não é um exemplo real do ProjectManifest nesse núcleo.

## NS-001: resumo do estado editorial

Fontes: [briefing](../../00-briefings/campanhas/NS-001/briefing.md), [hooks](../../02-hooks/campanhas/NS-001/hooks.md), [roteiro](../../03-roteiros/campanhas/NS-001/roteiro-001.md) e [execução autenticada de 05/11](../../00-briefings/campanhas/NS-001/VALIDACAO-EXECUCAO-2026-11-05.md).

- Versões editoriais: briefing, hooks e roteiro em 0.3.
- Briefing em validação; hooks e roteiro em rascunho. NS-001-H15 é uma seleção em rascunho.
- O registro de 05/11 relata E2E local aprovado, validação autenticada com emuladores, dados fictícios e viewport móvel emulado. Não é validação de produção nem de aparelho físico.
- A execução não tem identidade exata com um commit remoto, pois o diretório executado não tinha metadados Git verificáveis. A auditoria estática anterior aponta o commit 6342a33a36b0a4eadd0f5a62770f1eee485156ee do Salao02; são evidências distintas.
- As 12 capturas de 05/11 são evidência técnica, não frames finais aprovados.
- Permanecem pendentes as aprovações, o responsável, o CTA por canal, a revisão dos textos e da duração, a identidade de marca para uso público e as autorizações de gravação e publicação.
- A fixture editorial final ainda precisa ser preparada quando fizer parte da tarefa autorizada.

O resumo não substitui os registros de campanha nem amplia autorizações já existentes para outros fluxos de conteúdo. As regras vigentes de vídeo sem áudio, narração em texto separado, SRT e atuação dos bots continuam em AGENTS.md e WORKFLOW.md.

## O que esta atualização não verificou

Estado remoto de publicações/rascunhos no Postiz, execução de ComfyUI, implantação das integrações no servidor e novas jornadas do Salao02 não foram consultados ou executados nesta atualização. Consultá-los quando fizerem parte da tarefa solicitada.
