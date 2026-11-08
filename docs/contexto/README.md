# Contexto compartilhado do projeto

Este diretório é o ponto de entrada para continuar o trabalho entre computadores, Codex e outros agentes. O objetivo é recuperar fatos do repositório sem depender de uma conversa anterior.

## Ordem de leitura

1. [AGENTS.md](../../AGENTS.md): regras de operação, memória, dados e publicação.
2. [ESTADO-ATUAL.md](ESTADO-ATUAL.md): referência consultada, código integrado, alterações em revisão e pendências.
3. [PROXIMOS-PASSOS.md](PROXIMOS-PASSOS.md): ordem sugerida de trabalho e critérios de conclusão.
4. [HANDOFF.md](HANDOFF.md): procedimento para conferir a situação real e retomar uma tarefa.
5. [platform/README.md](../../platform/README.md): arquitetura, contratos, comandos e limites do núcleo.
6. [WORKFLOW.md](../../WORKFLOW.md): fluxo de produção e regra de vídeo sem áudio.
7. [orchestration/temporal/README.md](../../orchestration/temporal/README.md): piloto TEMPORAL-01, comandos, evidência medida e limitações.

## Qual fonte consultar

| Informação | Fonte principal |
| --- | --- |
| Regras de operação e autorização | AGENTS.md e pedido atual do titular |
| Contrato e comportamento executável | Código, schemas e testes do commit consultado |
| Conteúdo e estado editorial de uma campanha | Briefing, hooks, roteiro e registros de aprovação da própria campanha |
| Resultado de teste ou CI | Execução identificada por commit, ambiente e link/log |
| Estado técnico consolidado do projeto | ESTADO-ATUAL.md, reconferido no Git e no GitHub |
| Estado do piloto de orquestração | orchestration/temporal/README.md e docs/planejamento/TEMPORAL-01-piloto-de-orquestracao.md |
| Próxima tarefa | PROXIMOS-PASSOS.md, confrontado com as branches existentes |
| Publicações e rascunhos atuais | Estado remoto real, consultado quando a tarefa envolver conteúdo |

ESTADO-ATUAL.md concentra os fatos técnicos que mudam. Os outros arquivos apontam para ele, em vez de copiar hashes, contagens de testes e situações de PR. O resumo editorial aponta para os documentos da campanha; não é um registro de aprovação.

## Organização do projeto

O repositório reúne quatro frentes:

- fluxo editorial de campanhas: evidência funcional, briefing, hook, roteiro e revisão;
- produção e integrações específicas das marcas em marcas/ e ferramentas existentes;
- núcleo reutilizável em platform/, que recebe dados dos projetos e valida contratos;
- orquestração experimental em orchestration/temporal/, que roda o piloto TEMPORAL-01 sem alterar o núcleo.

A existência dos fluxos anteriores não significa que estejam integrados ao novo núcleo. Marca, domínio, tema e regras comerciais pertencem ao projeto consumidor; a implementação compartilhada deve continuar independente deles.

## Decisões arquiteturais

| Registro | Tema |
| --- | --- |
| [MKT-VIDEO-001](../decisoes/MKT-VIDEO-001-producao-modular.md) | Conteúdo separado da tecnologia de renderização |
| [MKT-PLATFORM-001](../decisoes/MKT-PLATFORM-001-plataforma-multiprojeto.md) | Núcleo reutilizável e configuração por projeto |
| [MKT-PIPELINE-001](../decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md) | Beats, direção visual, assets, áudio e adaptadores independentes |

Essas decisões registram o contexto e o escopo da sua criação. Expressões históricas como “Implementação: não iniciada” não descrevem sozinhas o estado do código hoje. Consulte ESTADO-ATUAL.md para saber quais partes já existem e em qual referência.

## Como manter este contexto

- Atualize o estado após uma integração, mudança de contrato ou validação relevante.
- Registre a data, a referência do código e a evidência; diferencie observado, relatado e ainda não verificado.
- Confira merged e o conteúdo efetivamente integrado antes de declarar uma PR concluída na main.
- Preserve registros históricos. Corrija um fato desatualizado no documento ativo sem inventar execução ou aprovação.
- Relatórios de testes comprovam casos exercitados, não equivalência universal nem autorização editorial.
- Credenciais, configurações privadas de dispositivo e transcrições completas não pertencem a este diretório.
