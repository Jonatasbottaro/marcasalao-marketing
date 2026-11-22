# Política de manutenção documental

Regras obrigatórias para criar, editar e aposentar documentação neste repositório.
Aplicam-se a qualquer agente ou pessoa, em qualquer estação. O contrato operacional geral
continua em [AGENTS.md](../../AGENTS.md); esta política trata apenas de documentação.

## 1. Fontes de verdade por assunto

| Assunto | Fonte de verdade | Documentos derivados |
| --- | --- | --- |
| Regras de operação, autorização, armazenamento | `AGENTS.md` | resumos em `README.md`, `WORKFLOW.md`, `CLAUDE.md`, templates |
| Comportamento executável | código + schemas + testes do commit consultado | guias e READMEs técnicos |
| Estado técnico consolidado | `docs/contexto/ESTADO-ATUAL.md` | `contexto_projeto*.md`, devlogs, aceites |
| Prioridades e aceite | `docs/contexto/PROXIMOS-PASSOS.md` | checklists operacionais |
| Arquitetura da fábrica | `docs/arquitetura-fabrica.md` | `README.md` raiz, guia do titular |
| Operação do Studio | `tools/produce/README.md` | `README.md` raiz |
| Conteúdo editorial de campanha | documentos da própria campanha (`00-briefings/`, `02-hooks/`, `03-roteiros/`, `04-legendas/`) | nenhum resumo externo substitui o registro da campanha |
| Métricas e resultados | execução identificada por data + SHA + comando + fonte | relatórios e portal |

Um documento derivado **nunca** contradiz a fonte de verdade silenciosamente: ou reflete o
valor verificado, ou marca explicitamente a divergência como pendência.

## 2. Antes de escrever

1. Conferir base: branch, HEAD completo, `git status --short`, worktrees e sessões
   concorrentes. Se outra sessão estiver editando o mesmo documento, interromper e pedir
   coordenação — não sobrescrever.
2. Identificar quais documentos a mudança afeta (use
   [MAPA-DOCUMENTAL.md](MAPA-DOCUMENTAL.md) e busca por links/referências em código, testes,
   workflows e templates).
3. Registrar a base de verificação (SHA + data) no cabeçalho do documento alterado.

## 3. Durante a mudança

- Separar rigorosamente: **confirmado por código** · **descrito por documentação** ·
  **resultado histórico de execução** · **hipótese** · **não verificado**.
- Não declarar testes aprovados sem execução; não tratar contagem de `def test` como
  `testsRun`; não assumir que uma ferramenta cumpre um invariante só porque ele está escrito
  em `AGENTS.md`.
- Toda informação dinâmica importante (contagens, gates, lentes, flags, geometrias,
  políticas) carrega: fonte, data de verificação, commit/referência, método de confirmação e
  limitações.
- Preservar evidências: hashes, logs, capturas e manifestos não são reescritos para
  "consertar" um resultado antigo.
- Se a implementação contrariar uma regra: registrar a divergência no backlog
  (`docs/contexto/PROXIMOS-PASSOS.md`), **manter a regra vigente** e não reescrevê-la para
  legitimar o defeito.
- Se houver contradição de autorização entre documentos: documentar os escopos conhecidos,
  não ampliar permissões e pedir decisão ao titular.

## 4. Ao terminar

1. Atualizar `ESTADO-ATUAL.md` e `PROXIMOS-PASSOS.md` quando o estado ou a próxima tarefa
   mudarem; atualizar o guia específico afetado.
2. Registrar testes **executados** e **não executados**, com data/SHA/comando/fonte.
3. Produzir handoff em `docs/contexto/HANDOFF.md` (base, mudanças, validações reais,
   pendências, próxima ação segura).
4. Conferir links relativos e contagens dos documentos tocados; conferir que nenhum caminho
   absoluto de máquina foi introduzido (usar `<RAIZ>` ou formulação estrutural).
5. Não afirmar integração de PR/branch antes de verificá-la no Git (ancestralidade ou merge
   observado); referência local de `origin/main` pode estar desatualizada.
6. Cumprir o handoff de armazenamento de `AGENTS.md`, incluindo a confirmação textual de
   contenção em `<RAIZ>`.

## 5. Histórico, duplicação e aposentadoria

- **Não apagar** documentos históricos. Marcar como histórico no cabeçalho, indicar período
  / branch / commit a que se referem e apontar para a fonte vigente.
- Resultados históricos (contagens de testes, runs de CI, aceites) permanecem com sua data
  e SHA originais; correções vão em nota aditiva, nunca por reescrita retroativa.
- Duplicação desnecessária vira **resumo + link** para a fonte canônica; decisões e contexto
  exclusivos são preservados no documento original ou movidos com rastreabilidade.
- Antes de mover um documento: localizar links Markdown, referências em código/testes/
  workflows/templates, links relativos internos e âncoras. **Se houver consumidor de código
  dependente do caminho, manter o arquivo no caminho atual** e documentar a dependência;
  não editar o consumidor sem autorização própria.
- Não mover evidências nem materiais de campanha apenas para limpeza visual.
- Arquivos gerados (`05-review-portal/*`, `04-legendas/calendario-editorial.*`,
  `04-legendas/matriz-utm-consolidada.csv`, `02-reels-shorts/deliveries/factory-report.json`,
  manifests de entrega) só mudam pelo seu gerador; editar à mão cria divergência de hash.
- Bundles de terceiros em `.agents/` não são reorganizados por tarefas de documentação.

## 6. Verificação documental contínua (proposta, não implementada)

Proposta para decisão futura do titular: um gate de CI somente leitura que verifique links
relativos dos documentos próprios, ausência de caminhos de máquina e de segredos, e
coerência das contagens publicadas (tenants, campanhas, módulos por faixa, gates, domínios,
lentes) contra o código. **Nenhum script ou workflow foi criado nesta consolidação.**
Enquanto não existir, a verificação é manual, conforme a seção 4.

## 7. Estações e sincronização

- Alinhamento entre estações exclusivamente por Git (fetch/pull autorizados por tarefa;
  commit/push exigem autorização própria).
- `.workspace/`, aprovações (`aprovacoes-titular.json`), bundles e mídia local são **por
  estação**; documentos que dependem deles devem declarar essa limitação.
- Não prometer sincronização automática de nada que viva fora da árvore versionada.